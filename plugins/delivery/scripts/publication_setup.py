#!/usr/bin/env python3
"""Trusted opt-in configuration for an existing local ledger. Never an MCP tool.

No runtime launch, initialization, credentials, network or model calls. A dedicated
configuration home is not a complete host authority boundary.
"""
import argparse
import contextlib
import fcntl
import hashlib
import json
import os
import re
from pathlib import Path
import stat
import sys
import tempfile
import time
import uuid

LIMIT = 65536
LOCK_TIMEOUT = 2.0
MAX_IDENTITY = (1 << 64) - 1
RECEIPT = 'delivery-setup.json'
TOOLS = ['delivery_publication_' + name for name in ('submit', 'publish', 'receipt')]


class Refused(ValueError):
    pass


class UnsupportedPermissionPath(Refused):
    pass


class FreshHomePlanRequired(Refused):
    pass


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True,
                      allow_nan=False)


def decode(data):
    # Recovery must parse exactly without importing possibly damaged service code.
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise Refused()
            result[key] = value
        return result
    return json.loads(data.decode('utf-8'), object_pairs_hook=pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(Refused()))


def require(value):
    if not value:
        raise Refused()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def read(path):
    with path.open('rb') as stream:
        raw = stream.read(LIMIT + 1)
    require(len(raw) <= LIMIT)
    return raw


def path_checked(value, exists=True, directory=False):
    value.encode('utf-8')  # Undecodable filesystem bytes are unsupported.
    path = Path(value)
    require(path.is_absolute() and path == path.resolve(strict=False))
    require(not any(p.is_symlink() for p in (path, *path.parents)))
    if exists:
        info = path.stat()
        require(stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode))
    else:
        require(not path.exists())
        path_checked(str(path.parent), directory=True)
    return path


def identity(path):
    info = path.stat()
    value = [info.st_dev, info.st_ino]
    valid_identity(value)
    return value


def ancestors(path):
    return {str(p): identity(path_checked(str(p), directory=True)) for p in path.parents}


def installed_files():
    root = Path(__file__).resolve().parent
    return [root / name for name in ('publication_setup.py', 'publication_service.py', 'publication.py')]


def program_snapshot():
    sources, identities = {}, {}
    for file in installed_files():
        path = path_checked(str(file))
        before = identity(path)
        sources[str(path)] = read(path)
        require(identity(path) == before)
        identities[str(path)] = before
    python = path_checked(str(Path(sys.executable).resolve(strict=True)))
    before = identity(python)
    hasher = hashlib.sha256()
    with python.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            hasher.update(chunk)
    require(identity(python) == before)
    return {'python':str(python), 'python_identity':before,
            'python_sha256':hasher.hexdigest(), 'file_identities':identities,
            'files':{name:digest(raw) for name, raw in sources.items()}}, sources


def exact(value, fields):
    require(type(value) is dict and set(value) == set(fields))


def valid_path(value):
    # Structural only: recovery must not resolve or open recorded dependencies.
    require(type(value) is str and '\x00' not in value)
    value.encode('utf-8')  # Undecodable filesystem bytes are unsupported.
    path = Path(value)
    require(path.is_absolute() and '..' not in path.parts and str(path) == value
            and not value.startswith('//'))
    return path


def valid_identity(value):
    require(type(value) is list and len(value) == 2
            and all(type(item) is int and 0 <= item <= MAX_IDENTITY for item in value))


def valid_hash(value):
    require(type(value) is str and re.fullmatch(r'[0-9a-f]{64}', value) is not None)


def valid_binding(value):
    fields = {'destination', 'owner', 'audience', 'visibility', 'revision',
              'authority_revision', 'policy_revision'}
    exact(value, fields | {'generation'})
    require(type(value['generation']) is int and value['generation'] >= 1)
    require(all(type(value[k]) is str and value[k].strip() and len(value[k]) <= 256
                for k in fields))
    require(re.fullmatch(r'[a-z][a-z0-9-]{0,63}', value['destination']) is not None
            and value['visibility'] in ('private', 'public'))


def permission_rule_paths(home, ledger, worker, code_root):
    # Pinned POSIX permission parser treats these characters as glob syntax.
    # Ledger basenames are command arguments, not permission table keys.
    for value in (home, worker, str(Path(ledger).parent), code_root):
        require(type(value) is str)
        if value.startswith((':', '~')) or any(char in value for char in '*?[]'):
            raise UnsupportedPermissionPath()
        valid_path(value)


def bound_spec(home, ledger, worker, expected, recorded=None):
    valid_binding(expected)
    permission_rule_paths(home, ledger, worker, str(installed_files()[0].parent))
    programs, sources = program_snapshot()
    if recorded is not None:
        # No service import or ledger access precedes this comparison.
        require(all(recorded[key] == value for key, value in programs.items()))
    home = path_checked(home, directory=True) if Path(home).exists() else path_checked(home, exists=False)
    require(home != (Path.home() / '.codex').resolve(strict=False))
    ledger = path_checked(ledger)
    ledger_info = ledger.stat()
    require(ledger_info.st_uid == os.getuid() and not ledger_info.st_mode & 0o077)
    worker = path_checked(worker, directory=True)
    require(type(expected) is dict and type(expected.get('destination')) is str)
    files = installed_files()
    for root in (home, ledger.parent, files[0].parent):
        require(not worker.is_relative_to(root) and not root.is_relative_to(worker))
    require(not ledger.is_relative_to(home))
    before = identity(ledger)
    spec = {'home':str(home), 'ledger':str(ledger), 'worker':str(worker),
            'binding':expected, 'ledger_identity':before, 'ledger_ancestors':ancestors(ledger),
            'worker_identity':identity(worker), 'worker_ancestors':ancestors(worker),
            'home_identity':identity(home) if home.exists() else None,
            'home_ancestors':ancestors(home), **programs}
    if recorded is not None:
        require(spec == recorded)
    # Execute only the captured, checked bytes, never an unchecked .pyc cache or
    # a second import-time read. The operator still owns code/startup isolation.
    service = str(files[1])
    namespace = {'__name__':'delivery_setup_service', '__file__':service}
    exec(compile(sources[service], service, 'exec'), namespace)
    store = namespace['PublicationStore'](ledger)
    try:
        actual = store.control({'action':'binding', 'destination':expected['destination']})
        valid_binding(actual.get('binding'))
        require(actual.get('status') == 'verified' and actual.get('binding') == expected)
    finally:
        store.close()
    require(identity(ledger) == before)
    require(program_snapshot()[0] == programs)
    return spec


def toml_string(value):
    require(type(value) is str)
    value.encode('utf-8')  # TOML strings contain Unicode scalar values only.
    escaped = []
    for char in value:
        if char in ('"', '\\'):
            escaped.append('\\' + char)
        elif ord(char) < 0x20 or ord(char) == 0x7f:
            escaped.append('\\u%04X' % ord(char))
        else:
            escaped.append(char)
    return '"' + ''.join(escaped) + '"'


def toml_strings(values):
    return '[' + ', '.join(toml_string(value) for value in values) + ']'


def configuration(spec, enabled=True):
    value = toml_string
    root = str(Path(next(iter(spec['files']))).parent)
    filesystem = {':minimal':'read', spec['worker']:'write', spec['home']:'deny',
                  str(Path(spec['ledger']).parent):'deny', root:'deny'}
    table = '{' + ', '.join(value(k) + '=' + value(v) for k,v in filesystem.items()) + '}'
    # Known local controls are useful restrictions, not a universal tool ceiling.
    features = ('apps', 'plugins', 'browser_use', 'computer_use', 'image_generation',
                'multi_agent', 'multi_agent_v2', 'shell_tool', 'code_mode',
                'code_mode_host', 'hooks', 'view_image', 'request_permissions_tool')
    return ('approval_policy = "never"\nweb_search = "disabled"\n'
            'default_permissions = "delivery-local"\n'
            '[permissions.delivery-local]\nfilesystem = ' + table + '\n'
            '[permissions.delivery-local.network]\nenabled = false\n'
            '[features]\n' + ''.join(name + ' = false\n' for name in features)
            + '[mcp_servers.delivery_publication]\nenabled = ' + ('true' if enabled else 'false') + '\n'
            + 'command = ' + value(spec['python']) + '\nargs = '
            + toml_strings(['-B', str(Path(root) / 'publication_service.py'), '--db', spec['ledger']]) + '\n'
            + 'enabled_tools = ' + toml_strings(TOOLS) + '\n').encode()


def fresh_home(home):
    # Propose an unused sibling, never adopt, delete or copy interrupted state.
    original = path_checked(home, directory=True) if Path(home).exists() else path_checked(home, exists=False)
    for _ in range(8):
        candidate = original.parent / ('delivery-recovery-' + uuid.uuid4().hex)
        if not candidate.exists() and not candidate.is_symlink():
            return str(candidate)
    raise Refused()


def plan(home, ledger, worker, expected):
    spec = bound_spec(home, ledger, worker, expected)
    value = {'schema_version':1, 'spec':spec, 'sha256':digest(canonical(spec).encode()),
             'host_protected_ready':False}
    require(len((canonical(value) + '\n').encode()) <= LIMIT)
    return value


def validate_plan(value, expected_digest):
    require(type(value) is dict and set(value) == {'schema_version','spec','sha256','host_protected_ready'})
    require(type(value['schema_version']) is int and value['schema_version'] == 1
            and value['host_protected_ready'] is False)
    valid_hash(value['sha256'])
    valid_hash(expected_digest)
    require(value['sha256'] == expected_digest == digest(canonical(value['spec']).encode()))
    spec = value['spec']
    require(type(spec) is dict and set(spec) == {'home','ledger','worker','binding','ledger_identity','python','python_identity','files',
            'worker_identity','worker_ancestors','home_identity','home_ancestors','ledger_ancestors',
            'file_identities','python_sha256'})
    valid_binding(spec['binding'])
    for field in ('home', 'ledger', 'worker', 'python'):
        require(valid_path(spec[field]).name)
    for field in ('ledger_identity', 'worker_identity', 'python_identity'):
        valid_identity(spec[field])
    if spec['home_identity'] is not None:
        valid_identity(spec['home_identity'])
    for field in ('home', 'ledger', 'worker'):
        entries = spec[field + '_ancestors']
        exact(entries, {str(p) for p in Path(spec[field]).parents})
        for entry in entries.values():
            valid_identity(entry)
    # Installed script names stay bound, without loading service code for disable.
    paths = {str(p) for p in installed_files()}
    exact(spec['files'], paths)
    exact(spec['file_identities'], paths)
    for entry in spec['files'].values():
        valid_hash(entry)
    for entry in spec['file_identities'].values():
        valid_identity(entry)
    valid_hash(spec['python_sha256'])
    permission_rule_paths(spec['home'], spec['ledger'], spec['worker'],
                          str(installed_files()[0].parent))
    return spec


def private_home(home):
    home = path_checked(home, directory=True)
    info = home.stat()
    require(info.st_uid == os.getuid() and not info.st_mode & 0o077)
    return home


@contextlib.contextmanager
def locked(home):
    # Only cooperating trusted setup writers are serialized; this is not a
    # boundary against a malicious same-user host process.
    home_id = identity(private_home(str(home)))
    fd = os.open(home / '.delivery-setup.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        require(stat.S_ISREG(os.fstat(fd).st_mode))
        deadline = time.monotonic() + LOCK_TIMEOUT
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                remaining = deadline - time.monotonic()
                require(remaining > 0)
                time.sleep(min(0.05, remaining))
        require(identity(private_home(str(home))) == home_id)
        yield
        require(identity(private_home(str(home))) == home_id)
    finally:
        os.close(fd)


def create(path, raw):
    require(len(raw) <= LIMIT)
    # Publish complete bytes without overwriting an existing target.
    fd, temporary = tempfile.mkstemp(prefix='.delivery-write-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(raw); stream.flush(); os.fsync(stream.fileno())
        os.link(temporary, path)
    finally:
        os.unlink(temporary)


def read_config(home, spec):
    path = home / 'config.toml'
    if not path.exists():
        require(not path.is_symlink())
        return None
    raw = read(path_checked(str(path)))
    require(raw in (configuration(spec, True), configuration(spec, False)))
    return raw


def replace_config(home, old, new):
    require(len(new) <= LIMIT)
    path = home / 'config.toml'
    if old is None:
        create(path, new)
        return
    current_identity = identity(path_checked(str(path)))
    require(read(path) == old)
    fd, temporary = tempfile.mkstemp(prefix='.delivery-write-', dir=home)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(new); stream.flush(); os.fsync(stream.fileno())
        require(identity(path_checked(str(path))) == current_identity and read(path) == old)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def operate(action, value, expected_digest):
    spec = validate_plan(value, expected_digest)
    # Check both configurations before writing a receipt or either config.
    require(all(len(configuration(spec, enabled)) <= LIMIT for enabled in (True, False)))
    home = Path(spec['home'])
    require(ancestors(home) == spec['home_ancestors'])
    created = False
    if not home.exists():
        # Reserve bounded stat identity metadata before creating the final home.
        require(len((canonical({'plan':value, 'home_identity':[MAX_IDENTITY, MAX_IDENTITY]}) + '\n').encode()) <= LIMIT)
        require(action == 'enable' and spec['home_identity'] is None)
        require(bound_spec(spec['home'],spec['ledger'],spec['worker'],spec['binding'],spec) == spec)
        path_checked(str(home), exists=False)
        home.mkdir(mode=0o700)
        created = True
    home = private_home(str(home))
    home_id = identity(home)
    require(spec['home_identity'] in (None, home_id))
    raw_receipt = (canonical({'plan':value, 'home_identity':home_id}) + '\n').encode()
    require(len(raw_receipt) <= LIMIT)
    receipt = home / RECEIPT
    # A home created after planning must have our durable receipt, or have been
    # created in this invocation. Never adopt an arbitrary replacement, even if
    # empty. A crash before the receipt requires a new explicit plan for that home.
    if not receipt.exists():
        require(action == 'enable' and not receipt.is_symlink())
        if not (created or spec['home_identity'] == home_id) or not (
                set(p.name for p in home.iterdir()) <= {'.delivery-setup.lock'}):
            raise FreshHomePlanRequired()
    current_spec = {**spec, 'home_identity':home_id}
    with locked(home):
        require(identity(home) == home_id and ancestors(home) == spec['home_ancestors'])
        if receipt.exists():
            require(read(path_checked(str(receipt))) == raw_receipt)
        else:
            require(action == 'enable' and not receipt.is_symlink())
            if set(p.name for p in home.iterdir()) != {'.delivery-setup.lock'}:
                raise FreshHomePlanRequired()
            require(bound_spec(spec['home'],spec['ledger'],spec['worker'],spec['binding'],current_spec) == current_spec)
            create(receipt, raw_receipt)
            sync_directory(home)
            sync_directory(home.parent)
        current = read_config(home, spec)
        if action != 'disable':
            require(bound_spec(spec['home'],spec['ledger'],spec['worker'],spec['binding'],current_spec) == current_spec)
        if action in ('enable','disable'):
            desired = configuration(spec, action == 'enable')
            if current != desired:
                replace_config(home, current, desired)
                sync_directory(home)
            current = desired
        require(read(path_checked(str(receipt))) == raw_receipt)
        require(identity(home) == home_id and ancestors(home) == spec['home_ancestors'])
        if action != 'disable':
            require(bound_spec(spec['home'],spec['ledger'],spec['worker'],spec['binding'],current_spec) == current_spec)
        require(current is not None)
        if action in ('enable','disable'):
            # A prior invocation may have linked/replaced files and died before
            # directory sync. Matching bytes alone do not complete durability.
            sync_file(receipt, raw_receipt)
            sync_file(home / 'config.toml', current)
            sync_directory(home)
            sync_directory(home.parent)
            require(identity(home) == home_id and ancestors(home) == spec['home_ancestors'])
        return {'durability':'synced' if action in ('enable','disable') else 'not-checked',
                'status':'configured' if current == configuration(spec,True) else 'disabled',
                'host_protected_ready':False, 'plan_sha256':expected_digest}


def sync_file(path, expected):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        require(stat.S_ISREG(info.st_mode) and stream.read(LIMIT + 1) == expected)
        os.fsync(stream.fileno())
        require(identity(path_checked(str(path))) == [info.st_dev, info.st_ino])


def sync_directory(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='action', required=True)
    draft = commands.add_parser('plan')
    draft.add_argument('--fresh-home', action='store_true',
                       help='Plan an unused sibling home, preserving the selected home and all its files')
    for name in ('home','ledger','worker','binding'):
        draft.add_argument('--' + name, required=True)
    for action in ('enable','status','disable'):
        command = commands.add_parser(action)
        command.add_argument('--plan', required=True)
        command.add_argument('--expected-sha256', required=True)
    args = parser.parse_args()
    try:
        if args.action == 'plan':
            home = fresh_home(args.home) if args.fresh_home else args.home
            result = plan(home,args.ledger,args.worker,decode(read(Path(args.binding))))
        else:
            result = operate(args.action, decode(read(Path(args.plan))), args.expected_sha256)
        print(canonical(result))
        return 0
    except Exception as error:
        result = {'status':'unavailable-or-drifted', 'host_protected_ready':False,
                  'reconcile_required':args.action in ('enable','disable')}
        if isinstance(error, UnsupportedPermissionPath):
            result['reason'] = 'unsupported-permission-path-syntax'
        elif isinstance(error, FreshHomePlanRequired):
            result['reason'] = 'fresh-home-plan-required'
        print(canonical(result))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
