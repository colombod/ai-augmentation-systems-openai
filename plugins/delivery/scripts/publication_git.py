#!/usr/bin/env python3
"""Reviewed local root bundles. Trusted control and filesystem isolation are prerequisites.

This is not a sandbox, recipient authentication or a semantic content classifier.
Existing publication ledgers and historical release semantics are not modified.
"""
import argparse
import contextlib
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import selectors
import signal
import sqlite3
import stat
import subprocess
import sys
import tempfile
import time
import zlib

MAX_FRAME = 1048576
MAX_PROPOSAL = 1015808
MAX_BUNDLE = 4194304
BINDING = {'destination', 'owner', 'audience', 'visibility', 'revision',
           'authority_revision', 'policy_revision'}
IDENTIFIER = re.compile(r'[a-z][a-z0-9-]{0,63}')
HEX = re.compile(r'[a-f0-9]{64}')
STOPPED = False
TRUSTED_OWNERS = {os.getuid(), os.stat("/").st_uid}


class Refused(ValueError):
    pass


class Busy(Refused):
    pass


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True,
                      allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode('ascii')).hexdigest()


def exact(value, keys):
    if type(value) is not dict or set(value) != set(keys):
        raise Refused()


def identifier(value):
    if type(value) is not str or not IDENTIFIER.fullmatch(value):
        raise Refused()
    return value


def text(value, minimum, maximum):
    if type(value) is not str or not minimum <= len(value.encode('utf-8')) <= maximum:
        raise Refused()
    return value


def decode(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise Refused()
            result[key] = value
        return result
    if len(raw) > MAX_FRAME:
        raise Refused()
    return json.loads(raw.decode('utf-8'), object_pairs_hook=pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(Refused()))


def proposal(value, operation_id):
    exact(value, {'schema_version', 'operation', 'destination', 'output_name', 'files', 'commit'})
    if type(value['schema_version']) is not int or value['schema_version'] != 1 \
            or value['operation'] != 'git-root-bundle' \
            or value['output_name'] != identifier(operation_id) + '.bundle':
        raise Refused()
    identifier(value['destination'])
    files = value['files']
    if type(files) is not list or not 1 <= len(files) <= 128:
        raise Refused()
    names = set()
    spellings = {}
    total = 0
    for item in files:
        exact(item, {'name', 'content', 'mode'})
        name = text(item['name'], 1, 256)
        parts = name.split('/')
        if '\\' in name or len(parts) > 32 or any(ord(c) < 32 or ord(c) == 127 for c in name) \
                or any(x in ('', '.', '..') or x.casefold() == '.git' or x.endswith((' ', '.')) for x in parts):
            raise Refused()
        for length in range(1, len(parts)+1):
            prefix = '/'.join(parts[:length])
            folded_prefix = prefix.casefold()
            if folded_prefix in spellings and spellings[folded_prefix] != prefix:
                raise Refused()
            spellings[folded_prefix] = prefix
        folded = name.casefold()
        if folded in names or any(folded.startswith(n+'/') or n.startswith(folded+'/') for n in names):
            raise Refused()
        names.add(folded)
        content = text(item['content'], 0, MAX_PROPOSAL)
        total += len(content.encode('utf-8'))
        if '\0' in content or total > MAX_PROPOSAL or item['mode'] not in ('100644', '100755'):
            raise Refused()
    commit = value['commit']
    exact(commit, {'ref', 'message', 'author', 'committer'})
    if commit['ref'] != 'refs/heads/main' or '\0' in text(commit['message'], 1, 16384):
        raise Refused()
    for field in ('author', 'committer'):
        who = commit[field]
        exact(who, {'name', 'email', 'timestamp'})
        name = text(who['name'], 1, 256)
        email = text(who['email'], 3, 254)
        if name != name.strip() or any(ord(c) < 32 or ord(c) == 127 or c in '<>' for c in name):
            raise Refused()
        if any(not 33 <= ord(c) <= 126 or c in '<>' for c in email) \
                or email.count('@') != 1 or not all(email.split('@')):
            raise Refused()
        stamp = text(who['timestamp'], 7, 32)
        matched = re.fullmatch(r'(0|[1-9][0-9]*) ([+-])([0-9]{2})([0-9]{2})', stamp)
        if not matched or int(matched[1]) > 4102444799:
            raise Refused()
        hour, minute = int(matched[3]), int(matched[4])
        if hour > 14 or minute > 59 or (hour == 14 and minute) or stamp.endswith(' -0000'):
            raise Refused()
    encoded = canonical(value)
    if len(encoded.encode('ascii')) > MAX_PROPOSAL:
        raise Refused()
    return encoded


def directory(path):
    """Pin a canonical directory through no-follow ancestry; trust its owner."""
    path = os.fspath(path)
    if not os.path.isabs(path) or os.path.normpath(path) != path:
        raise Refused()
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        for part in path.split('/')[1:]:
            if not part:
                continue
            parent = os.fstat(fd)
            # Sticky shared temporary roots protect the next owner's entry.
            if parent.st_uid not in TRUSTED_OWNERS or (parent.st_mode & 0o022 and not parent.st_mode & stat.S_ISVTX):
                raise Refused()
            next_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                              dir_fd=fd)
            os.close(fd)
            fd = next_fd
        info = os.fstat(fd)
        if info.st_uid != os.getuid() or info.st_mode & 0o022:
            raise Refused()
        return fd
    except OSError as error:
        os.close(fd)
        raise Refused() from error
    except BaseException:
        os.close(fd)
        raise


def regular(fd, private=False):
    info = os.fstat(fd)
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() \
            or (private and info.st_mode & 0o077):
        raise Refused()
    return info


def fsync_dir(path):
    fd = directory(path)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def git(repo, args, deadline, limit=MAX_BUNDLE):
    """No inherited Git settings, transports, optional locks or unbounded output."""
    env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
    env.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull,
               GIT_NO_LAZY_FETCH='1', GIT_ALLOW_PROTOCOL='', GIT_TERMINAL_PROMPT='0')
    command = ['git', '--no-replace-objects', '--no-optional-locks', '-c',
               'core.hooksPath='+os.devnull, '-C', str(repo), *args]
    with subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                          stderr=subprocess.DEVNULL, env=env, close_fds=True) as process:
        try:
            result = bytearray()
            with selectors.DefaultSelector() as selector:
                selector.register(process.stdout, selectors.EVENT_READ)
                while True:
                    remaining = deadline - time.monotonic()
                    if STOPPED or remaining <= 0 or not selector.select(remaining):
                        raise Refused()
                    chunk = os.read(process.stdout.fileno(), min(65536, limit+1-len(result)))
                    if not chunk:
                        break
                    result.extend(chunk)
                    if len(result) > limit:
                        raise Refused()
            if process.wait(timeout=max(.001, deadline-time.monotonic())) != 0:
                raise Refused()
            return bytes(result)
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()


def build_bundle(parent, value, deadline):
    """Fresh object database contains only the complete reviewed root graph."""
    stage = Path(tempfile.mkdtemp(prefix='root-', dir=parent))
    repo = stage / 'objects.git'
    git(stage, ['init', '--bare', '--object-format=sha1', '--template=', str(repo)], deadline, 4096)
    expected = {}
    def store(kind, raw):
        payload = kind.encode()+b' '+str(len(raw)).encode()+b'\0'+raw
        oid = hashlib.sha1(payload).hexdigest()
        object_path = repo/'objects'/oid[:2]/oid[2:]
        object_path.parent.mkdir(exist_ok=True)
        if object_path.exists():
            if zlib.decompress(object_path.read_bytes()) != payload:
                raise Refused()
        else:
            with object_path.open('xb') as target:
                target.write(zlib.compress(payload))
        expected[oid] = (kind, raw)
        return oid
    tree = {}
    for item in value['files']:
        current = tree
        pieces = item['name'].split('/')
        for piece in pieces[:-1]:
            current = current.setdefault(piece, {})
        current[pieces[-1]] = (item['mode'], store('blob', item['content'].encode('utf-8')))
    def tree_object(entries):
        result = bytearray()
        for name, child in sorted(entries.items(), key=lambda pair:
                                  (pair[0]+('/' if isinstance(pair[1], dict) else '')).encode('utf-8')):
            mode, oid = ('40000', tree_object(child)) if isinstance(child, dict) else child
            result.extend(mode.encode()+b' '+name.encode('utf-8')+b'\0'+bytes.fromhex(oid))
        return store('tree', bytes(result))
    tree_id = tree_object(tree)
    commit = value['commit']
    lines = ['tree '+tree_id]
    for role in ('author', 'committer'):
        who = commit[role]
        lines.append(f"{role} {who['name']} <{who['email']}> {who['timestamp']}")
    root = store('commit', ('\n'.join(lines)+'\n\n'+commit['message']).encode('utf-8'))
    (repo/'refs/heads/main').write_text(root+'\n', encoding='ascii')
    for oid, (kind, raw) in expected.items():
        if git(repo, ['cat-file', kind, oid], deadline, len(raw)) != raw:
            raise Refused()
    git(repo, ['fsck', '--strict', '--full', '--no-reflogs'], deadline, 65536)
    raw_bundle = git(repo, ['bundle', 'create', '-', 'refs/heads/main'], deadline)
    bundle = stage/'output.bundle'
    with bundle.open('xb') as out:
        out.write(raw_bundle)
        out.flush()
        os.fsync(out.fileno())
        os.fchmod(out.fileno(), 0o444)
        os.fsync(out.fileno())
    fsync_dir(stage)
    info = bundle.stat()
    return {'stage': str(bundle), 'stage_device': info.st_dev, 'stage_inode': info.st_ino,
            'bundle_sha256': hashlib.sha256(raw_bundle).hexdigest(), 'root_commit': root, 'tree': tree_id}


SCHEMA = '''
CREATE TABLE format(version INTEGER NOT NULL CHECK(version=1));
INSERT INTO format VALUES(1);
CREATE TABLE routes(destination TEXT PRIMARY KEY,binding TEXT NOT NULL,path TEXT NOT NULL);
CREATE TABLE drafts(operation_id TEXT PRIMARY KEY,proposal TEXT NOT NULL,digest TEXT NOT NULL,cancelled INTEGER NOT NULL);
CREATE TABLE reservations(device INTEGER,inode INTEGER,name TEXT,operation_id TEXT,digest TEXT,PRIMARY KEY(device,inode,name));
CREATE TABLE reviews(sequence INTEGER PRIMARY KEY,operation_id TEXT,proposal_sha256 TEXT,binding TEXT,approved INTEGER,issued REAL,expires REAL);
CREATE TABLE attempts(sequence INTEGER PRIMARY KEY,operation_id TEXT,review_sequence INTEGER,details TEXT,state TEXT);
CREATE TABLE outcomes(sequence INTEGER PRIMARY KEY,attempt INTEGER,result TEXT);
CREATE TABLE control_history(control_id TEXT PRIMARY KEY,request_sha256 TEXT,result TEXT);
'''
TABLES = {'format', 'routes', 'drafts', 'reservations', 'reviews', 'attempts', 'outcomes', 'control_history'}


class Store:
    def __init__(self, path):
        self.path = Path(path)
        if not self.path.is_absolute() or str(self.path) != os.path.normpath(str(self.path)):
            raise Refused()
        self.lock_path = self.path.with_name(self.path.name+'.lock')
        self.staging = self.path.with_name(self.path.name+'.staging')
        self.db = None

    @contextlib.contextmanager
    def locked(self, deadline, initialize=False):
        parent = directory(self.path.parent)
        lock = None
        try:
            if os.fstat(parent).st_mode & 0o077:
                raise Refused()
            lock = os.open(self.lock_path.name, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_CLOEXEC,
                           0o600, dir_fd=parent)
            info = regular(lock, private=True)
            until = min(deadline, time.monotonic()+1)
            while True:
                try:
                    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if time.monotonic() >= until:
                        raise Busy()
                    time.sleep(min(.01, max(0, until-time.monotonic())))
            current = os.stat(self.lock_path.name, dir_fd=parent, follow_symlinks=False)
            if (info.st_dev, info.st_ino) != (current.st_dev, current.st_ino):
                raise Refused()
            if initialize:
                file_fd = os.open(self.path.name, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW,
                                  0o600, dir_fd=parent)
                os.close(file_fd)
            check_fd = os.open(self.path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=parent)
            try:
                regular(check_fd, private=True)
            finally:
                os.close(check_fd)
            self.db = sqlite3.connect(self.path.as_uri()+'?mode=rw', uri=True, isolation_level=None)
            self.db.row_factory = sqlite3.Row
            self.db.execute('PRAGMA synchronous=FULL')
            self.db.execute('PRAGMA busy_timeout=0')
            if initialize:
                self.db.executescript('BEGIN IMMEDIATE;'+SCHEMA+'COMMIT;')
                os.mkdir(self.staging, 0o700)
                os.fsync(parent)
            if self.db.execute('PRAGMA quick_check').fetchone()[0] != 'ok' \
                    or [tuple(r) for r in self.db.execute('SELECT version FROM format')] != [(1,)] \
                    or {r[0] for r in self.db.execute("SELECT name FROM sqlite_master WHERE type='table'")} != TABLES \
                    or self.db.execute("SELECT 1 FROM sqlite_master WHERE type='trigger'").fetchone():
                raise Refused()
            stage_fd = directory(self.staging)
            try:
                if os.fstat(stage_fd).st_mode & 0o077:
                    raise Refused()
            finally:
                os.close(stage_fd)
            yield
        finally:
            if self.db is not None:
                self.db.close()
                self.db = None
            if lock is not None:
                os.close(lock)
            os.close(parent)

    def initialize(self):
        try:
            with self.locked(time.monotonic()+30, initialize=True):
                return {'status': 'initialized'}
        except Busy:
            return {'status': 'busy'}
        except Exception:
            return {'status': 'blocked'}

    @contextlib.contextmanager
    def transaction(self):
        self.db.execute('BEGIN IMMEDIATE')
        try:
            yield
            self.db.execute('COMMIT')
        except BaseException:
            if self.db.in_transaction:
                self.db.execute('ROLLBACK')
            raise

    def binding(self, destination):
        row = self.db.execute('SELECT * FROM routes WHERE destination=?', (destination,)).fetchone()
        if not row:
            raise Refused()
        return json.loads(row['binding']), row['path']

    def fenced(self, device, inode):
        for row in self.db.execute("SELECT details FROM attempts WHERE state IN ('intent','unknown','conflict')"):
            value = json.loads(row['details'])
            if (value['binding']['directory_device'], value['binding']['directory_inode']) == (device, inode):
                return True
        return False

    def outcome(self, row, state, result):
        with self.transaction():
            self.db.execute('UPDATE attempts SET state=? WHERE sequence=?', (state, row['sequence']))
            self.db.execute('INSERT INTO outcomes(attempt,result) VALUES(?,?)', (row['sequence'], canonical(result)))

    def completed(self, details, ident):
        return {'status': 'completed', 'operation_id': ident, 'proposal_sha256': details['proposal_sha256'],
                **{k: details[k] for k in ('bundle_sha256', 'root_commit', 'tree', 'output_name')},
                'binding_generation': details['binding']['generation']}

    def artifact(self, fd, details):
        info = regular(fd)
        if (info.st_dev, info.st_ino) != (details['stage_device'], details['stage_inode']) \
                or info.st_mode & 0o222 or not 0 < info.st_size <= MAX_BUNDLE:
            raise Refused()
        h = hashlib.sha256()
        size = 0
        while True:
            chunk = os.read(fd, min(65536, MAX_BUNDLE+1-size))
            if not chunk:
                break
            size += len(chunk)
            if size > MAX_BUNDLE:
                raise Refused()
            h.update(chunk)
        if size != info.st_size or h.hexdigest() != details['bundle_sha256']:
            raise Refused()

    def cleanup(self, details):
        try:
            fd = os.open(details['stage'], os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW | os.O_CLOEXEC)
            try:
                self.artifact(fd, details)
            finally:
                os.close(fd)
            os.unlink(details['stage'])
            fsync_dir(Path(details['stage']).parent)
        except (OSError, Refused):
            # A private retained link is cleanup debt, never permission to publish again.
            pass

    def recover(self):
        rows = self.db.execute("SELECT * FROM attempts WHERE state IN ('intent','unknown','conflict') ORDER BY sequence").fetchall()
        for row in rows:
            details = json.loads(row['details'])
            base = {'operation_id': row['operation_id'], 'proposal_sha256': details['proposal_sha256']}
            fd = None
            try:
                fd = directory(details['directory'])
                info = os.fstat(fd)
                expected = details['binding']
                if (info.st_dev, info.st_ino) != (expected['directory_device'], expected['directory_inode']):
                    raise Refused()
                try:
                    target = os.open(details['output_name'], os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=fd)
                except FileNotFoundError:
                    self.outcome(row, 'absent-needs-review', {'status': 'needs-review', **base})
                    continue
                try:
                    self.artifact(target, details)
                finally:
                    os.close(target)
                os.fsync(fd)
                self.outcome(row, 'completed', self.completed(details, row['operation_id']))
                self.cleanup(details)
            except Refused:
                self.outcome(row, 'conflict', {'status': 'conflict', **base})
            except OSError:
                self.outcome(row, 'unknown', {'status': 'unknown', **base})
            finally:
                if fd is not None:
                    os.close(fd)

    def request(self, request, control=False):
        deadline = time.monotonic()+30
        available = False
        try:
            with self.locked(deadline):
                self.recover()
                available = True
                return self.control(request) if control else self.data(request, deadline)
        except Busy:
            return {'status': 'busy'}
        except Refused:
            return {'status': 'blocked' if available else 'unknown'}
        except Exception:
            # Unavailable/corrupt state is never evidence that an effect did not occur.
            return {'status': 'unknown'}

    def control(self, request):
        if type(request) is not dict:
            raise Refused()
        action = request.get('action')
        if action == 'binding':
            exact(request, {'action', 'destination'})
            binding, _ = self.binding(identifier(request['destination']))
            return {'status': 'recorded', 'binding': binding}
        if action == 'control-receipt':
            exact(request, {'action', 'control_id', 'request_sha256'})
            identifier(request['control_id'])
            if type(request['request_sha256']) is not str or not HEX.fullmatch(request['request_sha256']):
                raise Refused()
            row = self.db.execute('SELECT * FROM control_history WHERE control_id=?', (request['control_id'],)).fetchone()
            if not row:
                return {'status': 'not-found'}
            if row['request_sha256'] != request['request_sha256']:
                return {'status': 'conflict'}
            return {'status': 'recorded', 'result': json.loads(row['result'])}
        identifier(request.get('control_id'))
        request_hash = digest(request)
        prior = self.db.execute('SELECT * FROM control_history WHERE control_id=?', (request['control_id'],)).fetchone()
        if prior:
            return json.loads(prior['result']) if prior['request_sha256'] == request_hash else {'status': 'conflict'}
        with self.transaction():
            self.db.execute('SAVEPOINT mutation')
            try:
                result = self.mutate_control(request)
            except Refused:
                self.db.execute('ROLLBACK TO mutation')
                result = {'status': 'blocked'}
            self.db.execute('RELEASE mutation')
            self.db.execute('INSERT INTO control_history VALUES(?,?,?)',
                            (request['control_id'], request_hash, canonical(result)))
        return result

    def mutate_control(self, request):
        action = request['action']
        if action == 'register':
            exact(request, {'action', 'control_id', 'output_directory'} | BINDING)
            identifier(request['destination'])
            for key in BINDING:
                if not text(request[key], 1, 256).strip():
                    raise Refused()
            if request['visibility'] not in ('private', 'public'):
                raise Refused()
            fd = directory(request['output_directory'])
            try:
                info = os.fstat(fd)
            finally:
                os.close(fd)
            previous = self.db.execute('SELECT * FROM routes WHERE destination=?', (request['destination'],)).fetchone()
            old = json.loads(previous['binding']) if previous else None
            if self.fenced(info.st_dev, info.st_ino) or (old and self.fenced(old['directory_device'], old['directory_inode'])):
                return {'status': 'unknown'}
            binding = {k: request[k] for k in BINDING}
            binding.update(directory_device=info.st_dev, directory_inode=info.st_ino,
                           generation=old['generation'] if old else 1)
            if old and (binding != old or previous['path'] != request['output_directory']):
                binding['generation'] += 1
            self.db.execute('INSERT OR REPLACE INTO routes VALUES(?,?,?)',
                            (request['destination'], canonical(binding), request['output_directory']))
            return {'status': 'recorded', 'binding': binding}
        if action == 'revoke':
            exact(request, {'action', 'control_id', 'destination', 'expected_generation'})
            binding, path = self.binding(identifier(request['destination']))
            if type(request['expected_generation']) is not int or request['expected_generation'] != binding['generation']:
                raise Refused()
            binding['generation'] += 1
            self.db.execute('UPDATE routes SET binding=? WHERE destination=?', (canonical(binding), request['destination']))
            return {'status': 'recorded', 'binding': binding}
        if action == 'review':
            exact(request, {'action', 'control_id', 'operation_id', 'proposal', 'expected_binding', 'decision', 'ttl_seconds'})
            encoded = proposal(request['proposal'], request['operation_id'])
            row = self.db.execute('SELECT * FROM drafts WHERE operation_id=?', (request['operation_id'],)).fetchone()
            if not row or row['proposal'] != encoded or row['cancelled']:
                raise Refused()
            binding, _ = self.binding(request['proposal']['destination'])
            if request['expected_binding'] != binding or request['decision'] not in ('approve', 'reject'):
                raise Refused()
            ttl = request['ttl_seconds']
            if type(ttl) not in (int, float) or not math.isfinite(ttl) or not 0 < ttl <= 300:
                raise Refused()
            now = time.time()
            cursor = self.db.execute('INSERT INTO reviews(operation_id,proposal_sha256,binding,approved,issued,expires) VALUES(?,?,?,?,?,?)',
                                    (request['operation_id'], row['digest'], canonical(binding), request['decision'] == 'approve', now, now+ttl))
            return {'status': 'recorded', 'review_sequence': cursor.lastrowid, 'issued': now, 'expires': now+ttl,
                    'decision': request['decision'], 'binding_generation': binding['generation']}
        if action == 'cancel':
            exact(request, {'action', 'control_id', 'operation_id', 'proposal_sha256'})
            row = self.db.execute('SELECT * FROM drafts WHERE operation_id=?', (identifier(request['operation_id']),)).fetchone()
            if not row or row['digest'] != request['proposal_sha256']:
                raise Refused()
            last = self.db.execute('SELECT * FROM attempts WHERE operation_id=? ORDER BY sequence DESC LIMIT 1', (request['operation_id'],)).fetchone()
            if last and last['state'] == 'completed':
                return self.completed(json.loads(last['details']), request['operation_id'])
            if last and last['state'] in ('intent', 'unknown', 'conflict'):
                return {'status': 'unknown'}
            self.db.execute('UPDATE drafts SET cancelled=1 WHERE operation_id=?', (request['operation_id'],))
            return {'status': 'cancelled', 'operation_id': request['operation_id'], 'proposal_sha256': row['digest']}
        raise Refused()

    def data(self, request, deadline):
        exact(request, {'action', 'operation_id', 'proposal'})
        if request['action'] not in ('submit', 'publish', 'receipt'):
            raise Refused()
        ident, value = request['operation_id'], request['proposal']
        encoded = proposal(value, ident)
        proposal_hash = hashlib.sha256(encoded.encode('ascii')).hexdigest()
        base = {'operation_id': ident, 'proposal_sha256': proposal_hash}
        row = self.db.execute('SELECT * FROM drafts WHERE operation_id=?', (ident,)).fetchone()
        if row and row['proposal'] != encoded:
            return {'status': 'conflict', **base}
        if request['action'] == 'submit':
            if not row:
                binding, _ = self.binding(value['destination'])
                if self.fenced(binding['directory_device'], binding['directory_inode']):
                    return {'status': 'unknown', **base}
                with self.transaction():
                    self.db.execute('INSERT INTO reservations VALUES(?,?,?,?,?)',
                                    (binding['directory_device'], binding['directory_inode'], value['output_name'], ident, proposal_hash))
                    self.db.execute('INSERT INTO drafts VALUES(?,?,?,0)', (ident, encoded, proposal_hash))
            return {'status': 'cancelled' if row and row['cancelled'] else 'submitted', **base}
        if not row:
            return {'status': 'blocked', **base}
        last = self.db.execute('SELECT * FROM attempts WHERE operation_id=? ORDER BY sequence DESC LIMIT 1', (ident,)).fetchone()
        if last and last['state'] == 'completed':
            return self.completed(json.loads(last['details']), ident)
        if last and last['state'] in ('intent', 'unknown', 'conflict'):
            return {'status': 'conflict' if last['state'] == 'conflict' else 'unknown', **base}
        if row['cancelled']:
            return {'status': 'cancelled', **base}
        if request['action'] == 'receipt':
            return {'status': 'needs-review' if last else 'submitted', **base}
        return self.publish(ident, value, proposal_hash, deadline)

    def approved(self, ident, value, proposal_hash):
        binding, path = self.binding(value['destination'])
        if self.fenced(binding['directory_device'], binding['directory_inode']):
            raise Refused()
        reservation = self.db.execute('SELECT operation_id,digest FROM reservations WHERE device=? AND inode=? AND name=?',
                                      (binding['directory_device'], binding['directory_inode'], value['output_name'])).fetchone()
        if not reservation or tuple(reservation) != (ident, proposal_hash):
            raise Refused()
        review = self.db.execute('SELECT * FROM reviews WHERE operation_id=? ORDER BY sequence DESC LIMIT 1', (ident,)).fetchone()
        prior = self.db.execute('SELECT max(review_sequence) FROM attempts WHERE operation_id=?', (ident,)).fetchone()[0]
        now = time.time()
        if not review or not review['approved'] or review['proposal_sha256'] != proposal_hash \
                or review['binding'] != canonical(binding) or not review['issued'] <= now < review['expires'] \
                or (prior is not None and review['sequence'] <= prior):
            raise Refused()
        if self.db.execute('SELECT cancelled FROM drafts WHERE operation_id=?', (ident,)).fetchone()[0]:
            raise Refused()
        return binding, path, review

    def publish(self, ident, value, proposal_hash, deadline):
        base = {'operation_id': ident, 'proposal_sha256': proposal_hash}
        try:
            binding, path, review = self.approved(ident, value, proposal_hash)
        except Refused:
            return {'status': 'needs-review', **base}
        fd = directory(path)
        attempt = None
        effect_started = False
        try:
            info = os.fstat(fd)
            if (info.st_dev, info.st_ino) != (binding['directory_device'], binding['directory_inode']):
                raise Refused()
            try:
                os.stat(value['output_name'], dir_fd=fd, follow_symlinks=False)
            except FileNotFoundError:
                pass
            else:
                return {'status': 'conflict', **base}
            details = build_bundle(self.staging, value, deadline)
            if details['stage_device'] != info.st_dev:
                raise Refused()
            details.update(proposal_sha256=proposal_hash, output_name=value['output_name'], binding=binding,
                           directory=path)
            with self.transaction():
                cursor = self.db.execute('INSERT INTO attempts(operation_id,review_sequence,details,state) VALUES(?,?,?,?)',
                                        (ident, review['sequence'], canonical(details), 'intent'))
                attempt = cursor.lastrowid
            # The durable intent is deliberately outside the following transaction.
            with self.transaction():
                current_binding, _ = self.binding(value['destination'])
                current = self.db.execute('SELECT * FROM reviews WHERE operation_id=? ORDER BY sequence DESC LIMIT 1', (ident,)).fetchone()
                now = time.time()
                check = directory(path)
                try:
                    checked = os.fstat(check)
                    if (checked.st_dev, checked.st_ino) != (info.st_dev, info.st_ino):
                        raise Refused()
                finally:
                    os.close(check)
                if current_binding != binding or current['sequence'] != review['sequence'] or not current['approved'] \
                        or not current['issued'] <= now < current['expires'] \
                        or self.db.execute('SELECT cancelled FROM drafts WHERE operation_id=?', (ident,)).fetchone()[0]:
                    raise Refused()
                stage_fd = os.open(details['stage'], os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW | os.O_CLOEXEC)
                try:
                    self.artifact(stage_fd, details)
                finally:
                    os.close(stage_fd)
                if STOPPED or time.monotonic() >= deadline:
                    raise Refused()
                effect_started = True
                os.link(details['stage'], value['output_name'], dst_dir_fd=fd, follow_symlinks=False)
                os.fsync(fd)
                result = self.completed(details, ident)
                self.db.execute("UPDATE attempts SET state='completed' WHERE sequence=?", (attempt,))
                self.db.execute('INSERT INTO outcomes(attempt,result) VALUES(?,?)', (attempt, canonical(result)))
            self.cleanup(details)
            return result
        except BaseException as error:
            if not isinstance(error, Exception):
                raise
            if attempt is not None:
                if not effect_started:
                    result = {'status': 'cancelled' if STOPPED else 'blocked', **base}
                    try:
                        self.outcome({'sequence': attempt}, 'absent-needs-review', result)
                        return result
                    except Exception:
                        return {'status': 'unknown', **base}
                return {'status': 'unknown', **base}
            if isinstance(error, Refused):
                return {'status': 'blocked', **base}
            return {'status': 'unknown', **base}
        finally:
            os.close(fd)


def stopped(_signum, _frame):
    global STOPPED
    STOPPED = True


def frame(result):
    raw = canonical(result).encode('ascii')
    if len(raw) > MAX_FRAME:
        raise Refused()
    return raw+b'\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', required=True)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--initialize', action='store_true')
    mode.add_argument('--control', action='store_true')
    args = parser.parse_args()
    signal.signal(signal.SIGINT, stopped)
    signal.signal(signal.SIGTERM, stopped)
    try:
        store = Store(args.db)
        if args.initialize:
            result = store.initialize()
            sys.stdout.buffer.write(frame(result))
            return 0 if result['status'] == 'initialized' else 2
        if args.control:
            raw = sys.stdin.buffer.read(MAX_FRAME+1)
            try:
                request = decode(raw)
                result = store.request(request, control=True)
            except Exception:
                result = {'status': 'blocked'}
            sys.stdout.buffer.write(frame(result))
            return 0 if result['status'] in ('recorded', 'cancelled', 'completed', 'not-found') else 2
        while not STOPPED:
            raw = sys.stdin.buffer.readline(MAX_FRAME+2)
            if not raw:
                return 0
            if not raw.endswith(b'\n') or len(raw)-1 > MAX_FRAME:
                sys.stdout.buffer.write(frame({'status': 'blocked'}))
                sys.stdout.buffer.flush()
                return 2
            try:
                request = decode(raw[:-1])
                result = store.request(request)
            except Exception:
                result = {'status': 'blocked'}
            sys.stdout.buffer.write(frame(result))
            sys.stdout.buffer.flush()
        return 2
    except (BrokenPipeError, OSError, ValueError):
        return 2


if __name__ == '__main__':
    sys.exit(main())
