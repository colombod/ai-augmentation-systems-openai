#!/usr/bin/env python3
"""Opt-in local reviewed-bundle MCP handler. No network or model calls.

The launcher owns the database path and optional inherited control socket. Model
tools cannot register destinations or approve content. This protects the data API,
not a host where callers have arbitrary same-UID shell or database access.
"""
import argparse
import json
import math
import os
from pathlib import Path
import re
import selectors
import sqlite3
import stat
import sys

MAX_FRAME = 1_048_576
MAX_ENVELOPE = MAX_FRAME - 32768  # Reserve worst-case escaped control-binding overhead.
MAX_OPERATIONS = 256
NOW = "((julianday('now') - 2440587.5) * 86400.0)"
IDENTIFIER = re.compile(r'[a-z][a-z0-9-]{0,63}')
BINDING_FIELDS = {'destination', 'owner', 'audience', 'visibility', 'revision',
                  'authority_revision', 'policy_revision'}


class Refused(ValueError):
    pass


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True)


def identifier(value):
    return type(value) is str and IDENTIFIER.fullmatch(value) is not None


def exact(value, fields):
    if type(value) is not dict or set(value) != set(fields):
        raise Refused()


def envelope(value):
    exact(value, {'operation', 'destination', 'body', 'files', 'metadata'})
    if value['operation'] != 'local-release' or not identifier(value['destination']):
        raise Refused()
    if type(value['body']) is not str or type(value['files']) is not list or len(value['files']) > 64:
        raise Refused()
    names = set()
    for item in value['files']:
        exact(item, {'name', 'content'})
        if type(item['name']) is not str or not 0 < len(item['name']) <= 256 \
                or type(item['content']) is not str or item['name'] in names:
            raise Refused()
        names.add(item['name'])
    if type(value['metadata']) is not dict or len(value['metadata']) > 64 or any(
            type(k) is not str or not 0 < len(k) <= 64 or type(v) is not str
            for k, v in value['metadata'].items()):
        raise Refused()
    encoded = canonical(value)
    if len(encoded.encode()) > MAX_ENVELOPE:
        raise Refused()
    return encoded


def decode(data):
    def pairs(items):
        result = {}
        for k, v in items:
            if k in result:
                raise Refused()
            result[k] = v
        return result
    return json.loads(data.decode('utf-8'), object_pairs_hook=pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(Refused()))


class PublicationStore:
    """Private local ledger and release sink; methods perform no external writes.

    control() is launcher-only, never registered as an MCP tool. release rows are
    the local effect and durable receipt in the same transaction. No remote send
    is implied. Lost responses are reconciled by exact operation ID/envelope.
    """

    def __init__(self, path, initialize=False):
        self.path = Path(path).absolute()
        if any(p.is_symlink() for p in (self.path, *self.path.parents)):
            raise Refused()
        if initialize:
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.close(fd)
        info = self.path.stat()
        if not stat.S_ISREG(info.st_mode):
            raise Refused()
        self.identity = (info.st_dev, info.st_ino)
        self._closed = False
        self.db = sqlite3.connect(self.path.as_uri() + '?mode=rw', uri=True, isolation_level=None)
        self.db.execute('PRAGMA busy_timeout=1000')
        self.db.execute('PRAGMA synchronous=FULL')
        if initialize:
            self.db.executescript('''BEGIN IMMEDIATE;
                CREATE TABLE format(version INTEGER NOT NULL CHECK(version=1));
                INSERT INTO format VALUES(1);
                CREATE TABLE routes(destination TEXT PRIMARY KEY, binding TEXT NOT NULL, generation INTEGER NOT NULL);
                CREATE TABLE drafts(operation_id TEXT PRIMARY KEY, envelope TEXT NOT NULL);
                CREATE TABLE reviews(operation_id TEXT PRIMARY KEY, envelope TEXT NOT NULL,
                    binding TEXT NOT NULL, generation INTEGER NOT NULL, approved INTEGER NOT NULL,
                    issued REAL NOT NULL, expires REAL NOT NULL);
                CREATE TABLE releases(operation_id TEXT PRIMARY KEY, envelope TEXT NOT NULL,
                    binding TEXT NOT NULL, generation INTEGER NOT NULL, released REAL NOT NULL);
                COMMIT;''')
        try:
            self._health(full=True)
        except Exception:
            self.close()
            raise

    def close(self):
        if self._closed:
            return
        self._closed = True
        try:
            self.db.close()
        except Exception:
            # Quarantine remains permanent even if the driver cannot close.
            pass

    def _rollback_or_quarantine(self):
        if self._closed:
            return
        try:
            if self.db.in_transaction:
                self.db.execute('ROLLBACK')
        except Exception:
            # Never reuse a connection whose transaction state is uncertain.
            self.close()

    def _health(self, full=False):
        if self._closed:
            raise Refused()
        info = self.path.stat()
        if self.path.is_symlink() or (info.st_dev, info.st_ino) != self.identity:
            raise Refused()
        # The launcher owns ledger files. Full page integrity is checked on open;
        # requests retain identity/schema checks and SQLite errors fail closed.
        if full and self.db.execute('PRAGMA quick_check').fetchone() != ('ok',):
            raise Refused()
        if self.db.execute('SELECT version FROM format').fetchall() != [(1,)]:
            raise Refused()
        expected = {'format', 'routes', 'drafts', 'reviews', 'releases'}
        tables = {r[0] for r in self.db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if tables != expected or self.db.execute("SELECT 1 FROM sqlite_master WHERE type='trigger'").fetchone():
            raise Refused()

    def _begin(self):
        self._health()
        self.db.execute('BEGIN IMMEDIATE')

    def control(self, request):
        try:
            self._begin()
            result = {'status':'recorded'}
            action = request.get('action') if type(request) is dict else None
            if action == 'register':
                exact(request, BINDING_FIELDS | {'action'})
                if not identifier(request['destination']) or request['visibility'] not in ('private', 'public'):
                    raise Refused()
                if any(type(request[k]) is not str or not request[k].strip()
                       or len(request[k]) > 256 for k in BINDING_FIELDS):
                    raise Refused()
                binding = canonical({k:request[k] for k in BINDING_FIELDS})
                current = self.db.execute('SELECT binding,generation FROM routes WHERE destination=?',
                                          (request['destination'],)).fetchone()
                if not current and self.db.execute('SELECT count(*) FROM routes').fetchone()[0] >= 64:
                    raise Refused()
                if not current or current[0] != binding:
                    generation = current[1] + 1 if current else 1
                    self.db.execute('INSERT OR REPLACE INTO routes VALUES(?,?,?)',
                                    (request['destination'], binding, generation))
                result['binding'] = {**json.loads(binding), 'generation':generation if not current or current[0] != binding else current[1]}
            elif action == 'binding':
                exact(request, {'action', 'destination'})
                if not identifier(request['destination']):
                    raise Refused()
                current = self.db.execute('SELECT binding,generation FROM routes WHERE destination=?',
                                          (request['destination'],)).fetchone()
                if not current:
                    raise Refused()
                result = {'status':'verified', 'binding':{**json.loads(current[0]), 'generation':current[1]}}
            elif action == 'review':
                exact(request, {'action', 'operation_id', 'envelope', 'decision', 'ttl_seconds', 'expected_binding'})
                expected = request['expected_binding']
                exact(expected, BINDING_FIELDS | {'generation'})
                if type(expected['generation']) is not int or expected['generation'] < 1:
                    raise Refused()
                encoded = envelope(request['envelope'])
                ident = request['operation_id']
                if not identifier(ident) or request['decision'] not in ('approve', 'reject') \
                        or type(request['ttl_seconds']) not in (int, float) \
                        or not math.isfinite(request['ttl_seconds']) or not 0 < request['ttl_seconds'] <= 300:
                    raise Refused()
                if self.db.execute('SELECT envelope FROM drafts WHERE operation_id=?', (ident,)).fetchone() != (encoded,) \
                        or self.db.execute('SELECT 1 FROM releases WHERE operation_id=?', (ident,)).fetchone():
                    raise Refused()
                binding = self.db.execute('SELECT binding,generation FROM routes WHERE destination=?',
                                          (request['envelope']['destination'],)).fetchone()
                if not binding or binding != (canonical({k:expected[k] for k in BINDING_FIELDS}), expected['generation']):
                    raise Refused()
                self.db.execute('INSERT OR REPLACE INTO reviews VALUES(?,?,?,?,?,' + NOW + ',' + NOW + '+?)',
                                (ident, encoded, *binding, request['decision'] == 'approve', request['ttl_seconds']))
            else:
                raise Refused()
            self.db.execute('COMMIT')
            return result
        except Exception:
            self._rollback_or_quarantine()
            return {'status':'blocked'}

    def call(self, name, args):
        committing = False
        try:
            exact(args, {'operation_id', 'envelope'})
            ident = args['operation_id']
            if not identifier(ident) or name not in TOOL_NAMES:
                raise Refused()
            encoded = envelope(args['envelope'])
            self._begin()
            released = self.db.execute('SELECT envelope FROM releases WHERE operation_id=?', (ident,)).fetchone()
            if released:
                if released != (encoded,):
                    raise Refused()
                result = 'completed'
            elif name == 'delivery_publication_receipt':
                result = 'not-released'
            else:
                route = self.db.execute('SELECT binding,generation FROM routes WHERE destination=?',
                                        (args['envelope']['destination'],)).fetchone()
                if not route:
                    raise Refused()
                draft = self.db.execute('SELECT envelope FROM drafts WHERE operation_id=?', (ident,)).fetchone()
                if draft and draft != (encoded,):
                    raise Refused()
                if name == 'delivery_publication_submit':
                    if not draft:
                        if self.db.execute('SELECT count(*) FROM drafts').fetchone()[0] >= MAX_OPERATIONS:
                            raise Refused()
                        self.db.execute('INSERT INTO drafts VALUES(?,?)', (ident, encoded))
                    result = 'submitted'
                else:
                    # Review, complete binding, expiry, local effect and receipt share
                    # this transaction. The predicate uses SQL time at insertion.
                    self.db.execute('''INSERT INTO releases
                        SELECT d.operation_id,d.envelope,r.binding,r.generation,''' + NOW + '''
                        FROM drafts d JOIN reviews r ON r.operation_id=d.operation_id
                        JOIN routes t ON t.destination=?
                        WHERE d.operation_id=? AND d.envelope=? AND r.envelope=d.envelope
                        AND r.approved=1 AND r.issued<=''' + NOW + ''' AND r.expires>''' + NOW + '''
                        AND r.binding=t.binding AND r.generation=t.generation''',
                        (args['envelope']['destination'], ident, encoded))
                    result = 'completed' if self.db.execute('SELECT changes()').fetchone()[0] == 1 else 'blocked'
            committing = True
            self.db.execute('COMMIT')
            return {'status':result}
        except Exception:
            # A commit error is conservatively unknown for publish. The caller must
            # query/retry the same immutable operation; never allocate a replacement ID.
            self._rollback_or_quarantine()
            return {'status':'unknown' if committing and name == 'delivery_publication_publish' else 'blocked'}

    def consume(self, ident):
        if not identifier(ident):
            raise Refused()
        self._health()
        row = self.db.execute('SELECT envelope FROM releases WHERE operation_id=?', (ident,)).fetchone()
        if not row:
            raise Refused()
        value = decode(row[0].encode())
        if envelope(value) != row[0]:
            raise Refused()
        return value


TOOL_NAMES = ('delivery_publication_submit', 'delivery_publication_publish', 'delivery_publication_receipt')
ENVELOPE_SCHEMA = {'type':'object', 'additionalProperties':False,
    'required':['operation','destination','body','files','metadata'],
    'properties':{'operation':{'const':'local-release'}, 'destination':{'type':'string'},
        'body':{'type':'string'}, 'metadata':{'type':'object','maxProperties':64,
                                          'additionalProperties':{'type':'string'}},
        'files':{'type':'array','maxItems':64,'items':{'type':'object','additionalProperties':False,
            'required':['name','content'],'properties':{'name':{'type':'string','maxLength':256},
                                                     'content':{'type':'string'}}}}}}
TOOLS = [{'name':name, 'description':'Local reviewed bundle '+name.rsplit('_',1)[1]+'. No remote publication.',
          'inputSchema':{'type':'object','required':['operation_id','envelope'], 'additionalProperties':False,
                         'properties':{'operation_id':{'type':'string'}, 'envelope':ENVELOPE_SCHEMA}}}
         for name in TOOL_NAMES]


def mcp(store, request):
    ident = request.get('id') if type(request) is dict else None
    # MCP correlation IDs are opaque strings or integers, bounded by the wire
    # frame. They stay on the private transport, never in release metadata.
    ident = ident if type(ident) in (int, str) else None
    try:
        if type(request) is not dict or request.get('jsonrpc') != '2.0':
            raise Refused()
        method = request.get('method')
        if type(method) is not str or ('params' in request and type(request['params']) not in (dict, list)):
            raise Refused()
        # Notifications never receive replies, including unknown methods. Ignore
        # them without invoking publication operations or treating them as review.
        if 'id' not in request:
            return None
        if ident is None:
            raise Refused()
        if method == 'initialize':
            result = {'protocolVersion':'2024-11-05', 'capabilities':{'tools':{}},
                      'serverInfo':{'name':'delivery-local-publication','version':'0.1.0'}}
        elif method == 'ping':
            result = {}
        elif method == 'tools/list':
            result = {'tools':TOOLS}
        elif method == 'tools/call':
            params = request.get('params')
            if type(params) is not dict or type(params.get('name')) is not str or 'arguments' not in params:
                raise Refused()
            if '_meta' in params:
                metadata = params['_meta']
                if type(metadata) is not dict or ('progressToken' in metadata and
                        type(metadata['progressToken']) not in (str, int)):
                    raise Refused()
            # Protocol metadata stays on the private transport. Only candidate
            # arguments reach the ledger; extensions grant no content authority.
            state = store.call(params['name'], params['arguments'])
            result = {'content':[{'type':'text','text':canonical(state)}],
                      'isError':state['status'] in ('blocked','unknown')}
        else:
            raise Refused()
        return {'jsonrpc':'2.0','id':ident,'result':result}
    except Exception:
        return {'jsonrpc':'2.0','id':ident,'error':{'code':-32600,'message':'Request blocked'}}


def serve(store, control_fd=None):
    selector = selectors.DefaultSelector()
    selector.register(0, selectors.EVENT_READ, 'candidate')
    if control_fd is not None:
        if control_fd < 3 or not stat.S_ISSOCK(os.fstat(control_fd).st_mode):
            raise Refused()
        selector.register(control_fd, selectors.EVENT_READ, 'control')
    buffers = {key.fd:b'' for key in selector.get_map().values()}
    while selector.get_map():
        for key, _ in selector.select():
            chunk = os.read(key.fd, 65536)
            if not chunk:
                if buffers[key.fd]:
                    raise Refused()
                selector.unregister(key.fd)
                continue
            buffers[key.fd] += chunk
            while b'\n' in buffers[key.fd]:
                line, buffers[key.fd] = buffers[key.fd].split(b'\n', 1)
                if len(line) > MAX_FRAME:
                    raise Refused()
                try:
                    request = decode(line)
                    result = store.control(request) if key.data == 'control' else mcp(store, request)
                except Exception:
                    result = {'status':'blocked'} if key.data == 'control' else mcp(store, None)
                if result is not None:
                    output = (canonical(result)+'\n').encode()
                    fd = key.fd if key.data == 'control' else 1
                    while output:
                        output = output[os.write(fd, output):]
            if len(buffers[key.fd]) > MAX_FRAME:
                raise Refused()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', required=True)
    parser.add_argument('--initialize', action='store_true')
    parser.add_argument('--control-fd', type=int)
    parser.add_argument('--control', action='store_true', help='Trusted single JSON control request on stdin; not an MCP tool')
    parser.add_argument('--consume')
    args = parser.parse_args()
    store = None
    try:
        if args.consume and (args.initialize or args.control_fd is not None or args.control) \
                or args.control and args.control_fd is not None:
            raise Refused()
        store = PublicationStore(args.db, args.initialize)
        if args.consume:
            print(canonical(store.consume(args.consume)))
        elif args.control:
            raw = sys.stdin.buffer.read(MAX_FRAME + 1)
            if len(raw) > MAX_FRAME:
                raise Refused()
            result = store.control(decode(raw))
            print(canonical(result))
            return 0 if result['status'] in ('recorded', 'verified') else 2
        elif args.initialize and args.control_fd is None:
            # One-shot initialization does not register stdin with a selector.
            # This supports ordinary redirection from /dev/null or a regular file.
            print('{"status":"initialized"}')
        else:
            serve(store, args.control_fd)
        return 0
    except Exception:
        print('{"status":"unavailable"}', file=sys.stderr)
        return 2
    finally:
        if store:
            store.close()


if __name__ == '__main__':
    raise SystemExit(main())
