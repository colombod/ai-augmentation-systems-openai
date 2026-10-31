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
from pathlib import Path
import stat
import sys
import tempfile

LIMIT = 65536
RECEIPT = 'delivery-setup.json'
TOOLS = ['delivery_publication_' + name for name in ('submit', 'publish', 'receipt')]


class Refused(ValueError):
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
    return [info.st_dev, info.st_ino]


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


def bound_spec(home, ledger, worker, expected, recorded=None):
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
        require(actual.get('status') == 'verified' and actual.get('binding') == expected)
    finally:
        store.close()
    require(identity(ledger) == before)
    require(program_snapshot()[0] == programs)
    return spec


def configuration(spec, enabled=True):
    value = lambda x: json.dumps(x, ensure_ascii=False)
    root = str(Path(next(iter(spec['files']))).parent)
    filesystem = {':minimal':'read', spec['worker']:'write', spec['home']:'deny',
                  str(Path(spec['ledger']).parent):'deny', root:'deny'}
    table = '{' + ', '.join(value(k) + '=' + value(v) for k,v in filesystem.items()) + '}'
    # Known local controls are useful restrictions, not a universal tool ceiling.
    features = ('apps', 'plugins', 'browser_use', 'computer_use', 'image_generation',
                'multi_agent', 'multi_agent_v2', 'multi_agent_mode', 'shell_tool',
                'js_repl', 'code_mode', 'code_mode_host', 'remote_control', 'hooks',
                'codex_hooks', 'plugin_hooks', 'view_image', 'request_permissions_tool')
    return ('approval_policy = "never"\nweb_search = "disabled"\n'
            'default_permissions = "delivery-local"\n'
            '[permissions.delivery-local]\nfilesystem = ' + table + '\n'
            '[permissions.delivery-local.network]\nenabled = false\n'
            '[features]\n' + ''.join(name + ' = false\n' for name in features)
            + '[mcp_servers.delivery_publication]\nenabled = ' + ('true' if enabled else 'false') + '\n'
            + 'command = ' + value(spec['python']) + '\nargs = '
            + value(['-B', str(Path(root) / 'publication_service.py'), '--db', spec['ledger']]) + '\n'
            + 'enabled_tools = ' + value(TOOLS) + '\n').encode()


def plan(home, ledger, worker, expected):
    spec = bound_spec(home, ledger, worker, expected)
    value = {'schema_version':1, 'spec':spec, 'sha256':digest(canonical(spec).encode()),
             'host_protected_ready':False}
    require(len((canonical(value) + '\n').encode()) <= LIMIT)
    return value


def validate_plan(value, expected_digest):
    require(type(value) is dict and set(value) == {'schema_version','spec','sha256','host_protected_ready'})
    require(value['schema_version'] == 1 and value['host_protected_ready'] is False)
    require(value['sha256'] == expected_digest == digest(canonical(value['spec']).encode()))
    spec = value['spec']
    require(type(spec) is dict and set(spec) == {'home','ledger','worker','binding','ledger_identity','python','python_identity','files',
            'worker_identity','worker_ancestors','home_identity','home_ancestors','ledger_ancestors',
            'file_identities','python_sha256'})
    # Script paths stay bound to this installed helper. Receipt validation alone
    # grants no publication authority.
    require(set(spec['files']) == set(spec['file_identities']) == {str(p) for p in installed_files()})
    # Disable does not execute this command or require the old interpreter to
    # exist. Enable/status enforce the live identity and hash in bound_spec.
    recorded_python = spec['python']
    require(type(recorded_python) is str and '\x00' not in recorded_python)
    python_path = Path(recorded_python)
    require(python_path.is_absolute() and python_path.name and '..' not in python_path.parts
            and str(python_path) == recorded_python)
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
        fcntl.flock(fd, fcntl.LOCK_EX)
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
        require(created or spec['home_identity'] == home_id)
        require(set(p.name for p in home.iterdir()) <= {'.delivery-setup.lock'})
    current_spec = {**spec, 'home_identity':home_id}
    with locked(home):
        require(identity(home) == home_id and ancestors(home) == spec['home_ancestors'])
        if receipt.exists():
            require(read(path_checked(str(receipt))) == raw_receipt)
        else:
            require(action == 'enable' and not receipt.is_symlink())
            require(set(p.name for p in home.iterdir()) == {'.delivery-setup.lock'})
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
        return {'status':'configured' if current == configuration(spec,True) else 'disabled',
                'host_protected_ready':False, 'plan_sha256':expected_digest}


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
    for name in ('home','ledger','worker','binding'):
        draft.add_argument('--' + name, required=True)
    for action in ('enable','status','disable'):
        command = commands.add_parser(action)
        command.add_argument('--plan', required=True)
        command.add_argument('--expected-sha256', required=True)
    args = parser.parse_args()
    try:
        if args.action == 'plan':
            result = plan(args.home,args.ledger,args.worker,decode(read(Path(args.binding))))
        else:
            result = operate(args.action, decode(read(Path(args.plan))), args.expected_sha256)
        print(canonical(result))
        return 0
    except Exception:
        print(canonical({'status':'unavailable-or-drifted', 'host_protected_ready':False,
                         'reconcile_required':args.action in ('enable','disable')}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
