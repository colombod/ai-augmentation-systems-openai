#!/usr/bin/env python3
"""Opt-in clean Linux runner conformance. No model turns or semantic acceptance.

CLI shapes are pinned to openai/codex tag rust-v0.163.0. This script changes
only a previously unconfigured runner account by installing the reviewed plugin.
Do not run inside a Codex task. Failures never trigger a fallback or retry.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import pwd
import platform
import stat
import queue
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading

VERSION = 'codex-cli 0.163.0'
ENV_KEYS = {'HOME', 'PATH', 'USER', 'LOGNAME', 'LANG', 'LC_ALL', 'TZ'}


class Unsupported(RuntimeError):
    pass


def require(value, diagnosis):
    if not value:
        raise Unsupported(diagnosis)


def child_environment(source):
    return {key: value for key, value in source.items() if key in ENV_KEYS}


def check_host(opt_in):
    require(opt_in, 'explicit-clean-runner-opt-in-required')
    require(sys.platform == 'linux', 'linux-required')
    require(not any(key.startswith('CODEX') for key in os.environ), 'codex-environment-refused')
    require(not Path('/.dockerenv').exists(), 'container-runner-refused')
    # Inspect executable identities, not command text containing our --codex option.
    pid = os.getppid()
    seen = set()
    while pid > 1:
        require(pid not in seen, 'ancestry-invalid')
        seen.add(pid)
        try:
            executable = Path(f'/proc/{pid}/exe').resolve(strict=True).name.lower()
            argv = Path(f'/proc/{pid}/cmdline').read_bytes().split(b'\0')
            status = Path(f'/proc/{pid}/status').read_text()
            pid = int(next(line.split()[1] for line in status.splitlines() if line.startswith('PPid:')))
        except (OSError, StopIteration, ValueError):
            raise Unsupported('ancestry-unavailable') from None
        require('codex' not in executable and not any(
            Path(arg.decode(errors='replace')).name in {'codex.js', 'codex-linux-sandbox'}
            for arg in argv[:2]), 'codex-ancestor-refused')
    actual_home = Path(pwd.getpwuid(os.getuid()).pw_dir).resolve()
    require(Path(os.environ.get('HOME', '')).resolve() == actual_home, 'default-home-required')
    require(os.access(actual_home, os.W_OK), 'home-not-writable')
    require(not (actual_home / '.codex').exists(), 'preexisting-codex-home-refused')
    return actual_home


# Labels are observations of diagnostic wording, not a verified root cause.
# Ordering is stable; report at most four matching observations.
DIAGNOSTIC_CATEGORIES = (
    ('configuration', ('failed to parse', 'error parsing', 'toml parse error',
                       'unknown permission profile', 'permission profile not found',
                       'unknown field', 'invalid configuration')),
    ('namespace', ('unshare', 'create user namespace', 'creating user namespace',
                   'namespace creation', 'user namespaces are not enabled')),
    ('seccomp-landlock', ('seccomp', 'landlock')),
    ('mount-bwrap', ('bwrap:', 'bubblewrap', 'failed to mount', 'mount failed')),
    ('permission-denied', ('permission denied', 'operation not permitted')),
    ('missing-resource', ('no such file or directory', 'executable not found',
                          'socket not found', 'file not found')),
    ('unsupported-argument', ('not supported', 'unsupported', 'invalid argument',
                              'unexpected argument')),
)


def command_diagnosis(stderr, returncode):
    # Scan bounded text, return only constants plus process-owned numeric status
    # and a digest. Never return matching substrings or surrounding context.
    sample = stderr[:65536].lower()
    matches = [label for label, phrases in DIAGNOSTIC_CATEGORIES
               if any(phrase in sample for phrase in phrases)]
    category = ','.join(matches[:4]) if matches else 'unclassified'
    digest = hashlib.sha256(stderr.encode()).hexdigest()
    return (f'command-failed:exit={returncode}:category={category}:'
            f'scan-truncated={int(len(stderr) > 65536)}:stderr-sha256={digest}')


class SyntheticProbeFailure(Unsupported):
    """Only the fixed, credential-free sandbox command probe supplies details."""
    def __init__(self, stderr, returncode):
        super().__init__(command_diagnosis(stderr, returncode))
        self.detail = redact_synthetic_probe_stderr(stderr)


def redact_synthetic_probe_stderr(stderr):
    # Defense in depth, NOT a sanitizer for arbitrary application/private output.
    # Provenance is the fixed source-generated probe, after clean-host preflight,
    # with fabricated input and whitelisted environment. Never use for services,
    # installation, model output, private fixtures or other run() commands.
    text = stderr[:8192]
    text = re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]', '', text)
    text = re.sub(r'(?i)\b(?:https?|ssh|file)://\S+', '[URL]', text)
    text = re.sub(r'(?i)\bbearer\s+\S+', '[CREDENTIAL]', text)
    text = re.sub(r'''(?i)\b[A-Za-z0-9_]*(?:authorization|password|passwd|secret|token|api[_-]?key|access[_-]?key)(?:\s*[:=]\s*|\s+)(?:"[^"\n]*"|'[^'\n]*'|[^\s,;]+)''', '[CREDENTIAL]', text)
    text = re.sub(r'\b(?:sk-|gh[pousr]_|github_pat_)[A-Za-z0-9_-]+', '[CREDENTIAL]', text)
    # Remove entire quoted paths, including spaces, before unquoted path tokens.
    text = re.sub(r'''["'](?:/|[A-Za-z]:\\)[^"'\n]*["']''', '[PATH]', text)
    text = re.sub(r'(?:[A-Za-z]:\\|/|\.\.?/|~/)[^\s,;:()\[\]"\']+', '[PATH]', text)
    text = re.sub(r'\b[A-Za-z0-9_+/-]{32,}={0,2}\b', '[OPAQUE]', text)
    text = ''.join(c if c in '\n\t' or 32 <= ord(c) < 127 else '?' for c in text)
    return text[:2048]


def failure_report(stage, error):
    diagnosis = str(error) if isinstance(error, Unsupported) else type(error).__name__
    report = {'status':'unsupported-or-failed','stage':stage,'diagnosis':diagnosis[:240],
              'acceptance':False,'fallback_attempted':False}
    if stage == 'sandbox-command-boundary' and isinstance(error, SyntheticProbeFailure):
        report['synthetic_probe_stderr'] = error.detail
        report['detail_scope'] = 'fixed-synthetic-command-only'
    return report


def run(argv, env, cwd, data=None, allowed=(0,)):
    result = subprocess.run(argv, input=data, text=True, capture_output=True,
                            timeout=45, env=env, cwd=cwd)
    if result.returncode not in allowed:
        # Never echo raw child payloads, personal paths, config or diagnostics.
        raise Unsupported(command_diagnosis(result.stderr, result.returncode))
    return result


MAX_RPC_FRAME = 1048576
MAX_RPC_QUEUE = 16


def receive_messages(stream, messages):
    """Bound allocation before parsing; overflow/corruption closes the channel."""
    try:
        while True:
            line = stream.readline(MAX_RPC_FRAME + 2)
            if not line:
                break
            if len(line) > MAX_RPC_FRAME + 1 or not line.endswith(b'\n'):
                raise ValueError('invalid-frame')
            message = json.loads(line)
            if not isinstance(message, dict):
                raise ValueError('invalid-message')
            messages.put_nowait(message)
    except (ValueError, OSError, queue.Full):
        # Drop queued replies after a framing failure: none remain trustworthy.
        while True:
            try:
                messages.get_nowait()
            except queue.Empty:
                break
    finally:
        try:
            messages.put_nowait(None)
        except queue.Full:
            # A full queue at EOF is also a closed, failed channel.
            while True:
                try:
                    messages.get_nowait()
                except queue.Empty:
                    break
            messages.put_nowait(None)


class RPC:
    def __init__(self, argv, env, cwd):
        self.process = subprocess.Popen(argv, env=env, cwd=cwd,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        self.messages = queue.Queue(maxsize=MAX_RPC_QUEUE)
        self.serial = 0
        threading.Thread(target=receive_messages,
                         args=(self.process.stdout, self.messages), daemon=True).start()

    def send(self, value):
        frame = (json.dumps(value) + '\n').encode('utf-8')
        require(len(frame) <= MAX_RPC_FRAME + 1, 'rpc-send-frame-too-large')
        self.process.stdin.write(frame)
        self.process.stdin.flush()

    def call(self, method, params, mcp=False):
        self.serial += 1
        request = {'id': self.serial, 'method': method, 'params': params}
        if mcp:
            request['jsonrpc'] = '2.0'
        self.send(request)
        for _ in range(128):
            try:
                reply = self.messages.get(timeout=15)
            except queue.Empty:
                raise Unsupported('rpc-timeout') from None
            require(isinstance(reply, dict), 'rpc-unavailable')
            if reply.get('id') == self.serial:
                require('error' not in reply and 'result' in reply, 'rpc-error')
                return reply['result']
        raise Unsupported('rpc-notification-limit')

    def close(self):
        self.process.terminate()
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait()
        self.process.stdin.close()
        self.process.stdout.close()


def install(codex, root, base, env, actual_home):
    market = base / 'market'
    shutil.copytree(root / 'plugins/delivery', market / 'plugins/delivery',
                    ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    catalog = json.loads((root / '.agents/plugins/marketplace.json').read_text())
    catalog['plugins'] = [p for p in catalog['plugins'] if p['name'] == 'delivery']
    require(len(catalog['plugins']) == 1, 'delivery-catalog-entry-required')
    target = market / '.agents/plugins/marketplace.json'
    target.parent.mkdir(parents=True)
    target.write_text(json.dumps(catalog))
    require(run([codex, '--version'], env, base).stdout.strip() == VERSION, 'cli-version-mismatch')
    help_text = run([codex, 'sandbox', '--help'], env, base).stdout
    require('--permission-profile' in help_text, 'permission-profile-unavailable')
    run([codex, 'plugin', 'marketplace', 'add', str(market), '--json'], env, base)
    run([codex, 'plugin', 'add', 'delivery@ai-augmentation-systems-openai', '--json'], env, base)
    server = RPC([codex, 'app-server', '--stdio'], env, base)
    try:
        server.call('initialize', {'clientInfo': {'name':'delivery_qualification','version':'1'},
                                  'capabilities': {'experimentalApi':True}})
        server.send({'method':'initialized'})
        result = server.call('skills/list', {'cwds':[str(base)], 'forceReload':True})
        installed = set()
        for row in result['data']:
            require(not row.get('errors'), 'skill-discovery-errors')
            for skill in row['skills']:
                path = Path(skill['path']).resolve()
                package = path.parents[2]
                manifest = package / 'plugin.json'
                if path.is_relative_to(actual_home / '.codex') and manifest.is_file():
                    if json.loads(manifest.read_text()).get('name') == 'delivery':
                        installed.add(package)
        require(len(installed) == 1, 'installed-package-identity-unresolved')
        package = installed.pop()
        for path in (root / 'plugins/delivery').rglob('*'):
            if path.is_file() and '__pycache__' not in path.parts and path.suffix != '.pyc':
                require((package / path.relative_to(root / 'plugins/delivery')).read_bytes()
                        == path.read_bytes(), 'installed-package-bytes-mismatch')
        inventory = []
        cursor = None
        for _ in range(32):
            page = server.call('mcpServerStatus/list', {'cursor':cursor, 'limit':100})
            inventory.extend(page['data'])
            cursor = page.get('nextCursor')
            if not cursor:
                break
        require(not cursor, 'mcp-inventory-pagination-limit')
        # Inventory is evidence of discovery, not authority or route removal.
        return package, len(inventory)
    finally:
        server.close()


PUBLICATION_TOOLS = frozenset('delivery_publication_' + name for name in ('submit', 'publish', 'receipt'))


def publication_mcp_config(service, db):
    # JSON strings are valid TOML basic strings when Unicode is emitted directly.
    require(service.is_absolute() and db.is_absolute(), 'mcp-absolute-paths-required')
    value = lambda item: json.dumps(str(item), ensure_ascii=False)
    return ('[mcp_servers.delivery_publication]\ncommand = "/usr/bin/python3"\n'
            + 'args = [' + ', '.join(value(x) for x in ('-B', service, '--db', db)) + ']\n'
            + 'enabled_tools = [' + ', '.join(value(x) for x in sorted(PUBLICATION_TOOLS)) + ']\n')


def require_publication_inventory(page):
    require(isinstance(page, dict) and page.get('nextCursor') is None,
            'mcp-discovery-incomplete')
    rows = page.get('data')
    require(isinstance(rows, list) and len(rows) == 1, 'mcp-server-set-mismatch')
    row = rows[0]
    require(isinstance(row, dict) and row.get('name') == 'delivery_publication',
            'mcp-server-identity-mismatch')
    require('toolsError' in row and row['toolsError'] is None, 'mcp-discovery-error')
    require(isinstance(row.get('serverInfo'), dict)
            and row['serverInfo'].get('name') == 'delivery-local-publication',
            'mcp-live-server-identity-missing')
    require(isinstance(row.get('tools'), dict) and set(row['tools']) == PUBLICATION_TOOLS
            and all(isinstance(tool, dict) and tool.get('name') == name
                    for name, tool in row['tools'].items()), 'mcp-tool-set-mismatch')
    require(row.get('runtimeStatus') in (None, 'connected'), 'mcp-not-connected')
    # Full inventory may suppress individual resource-list errors. Require the
    # live server to advertise only tools as well, so [] is not absence proof
    # for a server advertising resources whose listing failed.
    capabilities = row.get('serverCapabilities')
    require(isinstance(capabilities, dict) and set(capabilities) == {'tools'}
            and isinstance(capabilities['tools'], dict), 'mcp-unexpected-capabilities')
    require(row.get('resources') == [] and row.get('resourceTemplates') == [],
            'mcp-unexpected-resources')
    return len(rows)


def protected_snapshot(paths):
    # Every namespace-denial probe needs a live readable outside fixture first.
    result = []
    for path in paths:
        info = path.stat()
        require(stat.S_ISREG(info.st_mode), 'mcp-fixture-not-regular')
        data = path.read_bytes()
        # Match both probe operations outside before crediting sandbox denial.
        # Open without writing; even preexisting read-only fixtures must fail.
        with path.open('ab'):
            pass
        require((path.stat().st_dev, path.stat().st_ino) == (info.st_dev, info.st_ino),
                'mcp-fixture-changed')
        result.append((info.st_dev, info.st_ino, hashlib.sha256(data).hexdigest()))
    return result


MCP_RESOURCE_PROBE = """import errno,pathlib,sys
for name in sys.argv[1:]:
 for mode in ('rb','ab'):
  try:
   with pathlib.Path(name).open(mode) as stream:
    if mode=='rb': stream.read(1)
  except OSError as error:
   if error.errno in (errno.EACCES,errno.EPERM,errno.ENOENT): continue
   raise
  raise SystemExit(10)
print('resources-denied')
"""


def native_discovery_checks(codex, package, trusted, base, env, sandbox_prefix, worker):
    service = package / 'scripts/publication_service.py'
    db = trusted / 'mcp-ledger.sqlite'
    argv = ['/usr/bin/python3', '-B', str(service), '--db', str(db)]
    run([*argv, '--initialize'], env, base)
    registered = json.loads(run([*argv, '--control'], env, base, json.dumps({
        'action':'register', 'destination':'native-sample', 'owner':'synthetic-owner',
        'audience':'synthetic-users', 'visibility':'public', 'revision':'r1',
        'authority_revision':'a1', 'policy_revision':'p1'})).stdout)
    require(registered.get('status') == 'recorded', 'mcp-fixture-register-failed')
    config_homes = [trusted / ('mcp-codex-home-' + str(index)) for index in range(2)]
    configs = []
    for home in config_homes:
        home.mkdir()
        config = home / 'config.toml'
        config.write_text(publication_mcp_config(service, db))
        configs.append(config)
    # Each connection has a fresh cache: a stale tool catalog cannot masquerade
    # as a live reconnect. Only the protected ledger is intentionally reused.
    fixtures = (db, service, *configs)
    before = protected_snapshot(fixtures)
    for home in config_homes:
        native_env = dict(env, CODEX_HOME=str(home))
        server = RPC([codex, 'app-server', '--stdio'], native_env, base)
        try:
            server.call('initialize', {'clientInfo': {'name':'delivery_discovery','version':'1'},
                                      'capabilities': {'experimentalApi':True}})
            server.send({'method':'initialized'})
            count = require_publication_inventory(server.call('mcpServerStatus/list', {
                'cursor':None, 'limit':100, 'detail':'full'}))
        finally:
            server.close()
        require(protected_snapshot(fixtures) == before, 'mcp-fixture-changed')
    denied = run([*sandbox_prefix, '/usr/bin/python3', '-c', MCP_RESOURCE_PROBE,
                  *(str(path) for path in fixtures)], env, worker)
    require(denied.stdout.strip() == 'resources-denied', 'mcp-resource-probe-incomplete')
    require(protected_snapshot(fixtures) == before, 'mcp-fixture-changed')
    return count


def resolve_native_codex(codex, env, cwd):
    """Resolve the pinned npm launcher's native file without executing Codex.

    Match rust-v0.163.0 codex-cli/bin/codex.js's optional-package layout.
    Unsupported packaging fails closed; no vendor fallback or directory grant.
    Package metadata establishes expected layout, not independent authenticity.
    The existing CLI version check remains required before this resolver runs.
    """
    if os.path.dirname(codex):
        selected = Path(codex)
        if not selected.is_absolute():
            selected = cwd / selected
    else:
        # Match subprocess lookup using the supplied environment and child cwd,
        # including relative/empty PATH entries; never use the caller's PATH.
        search = os.pathsep.join(str(Path(entry) if Path(entry).is_absolute() else cwd / entry)
                                 for entry in os.get_exec_path(env))
        found = shutil.which(codex, path=search)
        require(found is not None, 'codex-launcher-not-found')
        selected = Path(found)
    launcher = selected.resolve(strict=True)
    require(launcher.is_file() and os.access(launcher, os.X_OK), 'codex-launcher-not-executable')
    with launcher.open('rb') as source:
        direct = source.read(4) == b'\x7fELF'
    if direct:
        return launcher
    package_root = launcher.parent.parent
    metadata = json.loads((package_root / 'package.json').read_text())
    require(type(metadata) is dict, 'codex-launcher-metadata-invalid')
    require(metadata.get('name') == '@openai/codex' and metadata.get('version') == '0.163.0',
            'codex-launcher-package-mismatch')
    require(type(metadata.get('bin')) is dict, 'codex-launcher-layout-mismatch')
    require(metadata.get('bin', {}).get('codex') == 'bin/codex.js'
            and launcher == (package_root / 'bin/codex.js').resolve(strict=True),
            'codex-launcher-layout-mismatch')
    targets = {'x86_64':('x64','x86_64-unknown-linux-musl'),
               'aarch64':('arm64','aarch64-unknown-linux-musl')}
    require(platform.machine() in targets, 'codex-native-architecture-unsupported')
    architecture, triple = targets[platform.machine()]
    alias = '@openai/codex-linux-' + architecture
    require(type(metadata.get('optionalDependencies')) is dict, 'codex-native-dependency-unpinned')
    dependency = metadata['optionalDependencies'].get(alias)
    expected_alias = 'npm:@openai/codex@0.163.0-linux-' + architecture
    require(dependency in ('0.163.0', expected_alias), 'codex-native-dependency-unpinned')
    resolver = ("const {createRequire}=require('node:module');"
                "const r=createRequire(process.argv[1]);"
                "process.stdout.write(JSON.stringify(r.resolve(process.argv[2]+'/package.json')));")
    result = run(['node', '-e', resolver, str(launcher), alias], env, cwd)
    manifest_path = json.loads(result.stdout)
    require(type(manifest_path) is str and Path(manifest_path).is_absolute(), 'codex-native-manifest-invalid')
    manifest = Path(manifest_path).resolve(strict=True)
    native_metadata = json.loads(manifest.read_text())
    require(type(native_metadata) is dict, 'codex-native-package-mismatch')
    expected_name = '@openai/codex' if dependency == expected_alias else alias
    expected_version = '0.163.0-linux-' + architecture if dependency == expected_alias else '0.163.0'
    require(native_metadata.get('name') == expected_name
            and native_metadata.get('version') == expected_version, 'codex-native-package-mismatch')
    native = (manifest.parent / 'vendor' / triple / 'bin/codex').resolve(strict=True)
    require(native.is_relative_to(manifest.parent) and stat.S_ISREG(native.stat().st_mode)
            and os.access(native, os.X_OK), 'codex-native-file-invalid')
    with native.open('rb') as source:
        require(source.read(4) == b'\x7fELF', 'codex-native-not-elf')
    return native


def sandbox_config(worker, trusted, actual_home, native_codex):
    require(native_codex.is_absolute() and not any(native_codex.is_relative_to(path)
            for path in (worker, trusted, actual_home / '.codex', Path('/proc'))),
            'codex-native-overlaps-protected-root')
    filesystem = {':minimal':'read', str(worker):'write', str(trusted):'deny',
                  str(actual_home / '.codex'):'deny', '/proc':'deny', str(native_codex):'read'}
    # CLI dotted keys are split literally. Put path keys inside the TOML value
    # so quotes and dots in paths are decoded by the TOML parser instead.
    table = '{' + ','.join(json.dumps(path, ensure_ascii=False) + '=' + json.dumps(access)
                           for path, access in filesystem.items()) + '}'
    return ['-c', 'default_permissions="delivery-qualification"',
            '-c', 'permissions.delivery-qualification.filesystem=' + table,
            '-c', 'permissions.delivery-qualification.network.enabled=false']


# Fabricated fixture only; no broker data or caller environment is inspected.
PARENT_HELPER = r'''import json,os,sys
f=open(sys.argv[1],'rb')
print(json.dumps({'pid':os.getpid(),'fd':f.fileno()}),flush=True)
sys.stdin.buffer.read(1)
'''

PARENT_PROBE = r'''import errno,json,os,pathlib,stat,sys
info=json.loads(sys.argv[1]); approved=json.loads(sys.argv[2])
def fail(label):
 print(label,file=sys.stderr); raise SystemExit(12)
def denied(action,label):
 try: action()
 except OSError as e:
  if e.errno in (errno.EACCES,errno.EPERM,errno.ENOENT): return
  fail('parent-route-error:'+label)
 # Even an empty/partial read is accessible, not proof of protection.
 fail('parent-route-readable:'+label)
def clean_environment(raw):
 if not raw or not raw.endswith(b'\0'): fail('worker-environment-incomplete')
 parts=raw[:-1].split(b'\0'); values={}
 for part in parts:
  key,sep,value=part.partition(b'=')
  if not sep or key in values: fail('worker-environment-invalid')
  values[key]=value
 expected={k.encode():v.encode() for k,v in approved.items()}
 optional={b'PWD':os.getcwd().encode(),b'CODEX_SANDBOX_NETWORK_DISABLED':b'1'}
 for key,value in values.items():
  if key in expected and value==expected[key]: continue
  if key in optional and value==optional[key]: continue
  fail('worker-environment-unsanitized')
 if any(values.get(k)!=v for k,v in expected.items()): fail('worker-environment-missing')
clean_environment(pathlib.Path('/proc/self/environ').read_bytes())
if os.getcwd()!=info['worker']: fail('worker-directory-changed')
own=os.readlink('/proc/self/ns/pid')
if own==info['namespace']: fail('parent-pid-namespace-visible')
proc=pathlib.Path('/proc')/str(info['pid'])
# A host numeric PID may name an unrelated process in this new namespace.
collision=False
try:
 target=os.readlink(proc/'ns/pid')
except OSError as e:
 if e.errno not in (errno.EACCES,errno.EPERM,errno.ENOENT): fail('parent-identity-error')
else:
 if target!=own: fail('parent-namespace-unexpected')
 collision=True
if collision:
 # Readable colliding metadata must itself be sanitized, never merely lack a marker.
 try: raw=(proc/'environ').read_bytes()
 except OSError as e:
  if e.errno not in (errno.EACCES,errno.EPERM,errno.ENOENT): fail('parent-environ-error')
 else: clean_environment(raw)
else:
 denied(lambda:(proc/'environ').read_bytes(),'environ')
for label,path in [('direct',pathlib.Path(info['file'])),
                   ('root',proc/'root'/info['file'].lstrip('/')),
                   ('cwd',proc/'cwd'/pathlib.Path(info['file']).name)]:
 denied(lambda:path.read_bytes(),label)
fdpath=proc/'fd'/str(info['fd'])
if collision:
 try: meta=fdpath.stat()
 except OSError as e:
  if e.errno not in (errno.EACCES,errno.EPERM,errno.ENOENT): fail('parent-fd-error')
 else:
  if [meta.st_dev,meta.st_ino]==info['file_identity']: fail('parent-fd-visible')
  # An unrelated descriptor is not the outside fixture. Do not read pipes/stdio.
else:
 denied(lambda:fdpath.read_bytes(),'fd')
# Inspect regular-file/directory capabilities only, never consume protocol pipes.
for entry in pathlib.Path('/proc/self/fd').iterdir():
 try: meta=entry.stat()
 except OSError as e:
  if e.errno==errno.ENOENT: continue # iterdir's closed directory descriptor
  fail('worker-fd-inspection-error')
 if [meta.st_dev,meta.st_ino]==info['file_identity']: fail('worker-inherited-file')
 if stat.S_ISDIR(meta.st_mode):
  fail('worker-inherited-directory')
print('trusted-parent-routes-passed')
'''


def parent_baseline(helper, info):
    """Verify the SAME live synthetic process and all aliases before/after launch."""
    require(helper.poll() is None, 'parent-fixture-dead')
    proc = Path('/proc') / str(info['pid'])
    require(os.readlink(proc / 'ns/pid') == info['namespace'], 'parent-fixture-namespace-changed')
    require((proc / 'stat').read_text().rsplit(')', 1)[1].split()[19] == info['start'],
            'parent-fixture-process-changed')
    require(b'DELIVERY_SYNTHETIC_PARENT=outside-only\0' in (proc / 'environ').read_bytes(),
            'parent-fixture-environment-missing')
    paths = (Path(info['file']), proc/'fd'/str(info['fd']),
             proc/'root'/info['file'].lstrip('/'), proc/'cwd'/Path(info['file']).name)
    for path in paths:
        meta = path.stat()
        require([meta.st_dev,meta.st_ino] == info['file_identity'], 'parent-fixture-identity-changed')
        require(path.read_bytes() == b'SYNTHETIC CONTROL ONLY', 'parent-fixture-content-changed')


def trusted_parent_checks(prefix, env, worker, secret):
    helper = subprocess.Popen(['/usr/bin/python3','-c',PARENT_HELPER,str(secret)],
        env={**env,'DELIVERY_SYNTHETIC_PARENT':'outside-only'}, cwd=secret.parent,
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        close_fds=True)
    try:
        import select
        require(select.select([helper.stdout], [], [], 5)[0], 'parent-fixture-timeout')
        line = helper.stdout.readline(1025)
        require(len(line) <= 1024 and line.endswith(b'\n'), 'parent-fixture-frame-invalid')
        info = json.loads(line)
        require(set(info) == {'pid','fd'} and info['pid'] == helper.pid
                and type(info['fd']) is int and info['fd'] >= 3, 'parent-fixture-invalid')
        proc = Path('/proc') / str(helper.pid)
        meta = secret.stat()
        info.update(file=str(secret), worker=str(worker), file_identity=[meta.st_dev,meta.st_ino],
                    namespace=os.readlink(proc/'ns/pid'),
                    start=(proc/'stat').read_text().rsplit(')',1)[1].split()[19])
        parent_baseline(helper, info)
        # Keep real synthetic file/directory capabilities open in the launcher;
        # Python's non-inheritable defaults and close_fds must exclude both.
        directory_fd = os.open(secret.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            with secret.open('rb') as sentinel:
                require(not os.get_inheritable(directory_fd)
                        and not os.get_inheritable(sentinel.fileno()), 'parent-fd-inheritable')
                require(sentinel.read() == b'SYNTHETIC CONTROL ONLY', 'parent-fd-baseline-failed')
                require(os.fstat(directory_fd).st_ino == secret.parent.stat().st_ino,
                        'parent-directory-baseline-failed')
                result = subprocess.run([*prefix, '/usr/bin/python3','-c',PARENT_PROBE,
                                         json.dumps(info),json.dumps(env)],
                    stdin=subprocess.DEVNULL, text=True,capture_output=True,timeout=45,
                    env=env,cwd=worker,close_fds=True)
        finally:
            os.close(directory_fd)
        # Recheck outside identity even when the restricted probe fails.
        parent_baseline(helper, info)
        if result.returncode:
            raise SyntheticProbeFailure(result.stderr, result.returncode)
        require(result.stdout.strip() == 'trusted-parent-routes-passed', 'parent-probe-result-invalid')
    finally:
        helper.terminate()
        try: helper.wait(timeout=5)
        except subprocess.TimeoutExpired:
            helper.kill(); helper.wait()
        helper.stdin.close(); helper.stdout.close()


def sandbox_checks(codex, base, env, actual_home):
    worker, trusted = base / 'worker', base / 'trusted'
    worker.mkdir()
    trusted.mkdir()
    secret = trusted / 'synthetic-control'
    secret.write_text('SYNTHETIC CONTROL ONLY')
    listener = socket.socket()
    listener.bind(('127.0.0.1', 0))
    listener.listen(8)
    listener.settimeout(3)
    port = listener.getsockname()[1]
    # Baseline same process can reach the live listener and read/write fixture.
    with socket.create_connection(('127.0.0.1', port), timeout=2):
        connection, _ = listener.accept()
        connection.close()
    require(secret.read_text() == 'SYNTHETIC CONTROL ONLY', 'fixture-baseline-failed')
    secret.write_text('SYNTHETIC CONTROL ONLY')
    before = secret.stat()
    native_codex = resolve_native_codex(codex, env, base)
    config = sandbox_config(worker, trusted, actual_home, native_codex)
    # Restore the approved PATH after native startup helpers; no broader grant.
    config += ['-c', 'shell_environment_policy.set=' + '{PATH=' + json.dumps(env['PATH'], ensure_ascii=False) + '}']
    prefix = [str(native_codex), *config, 'sandbox', '--permission-profile', 'delivery-qualification', '--']
    code = '''import errno,pathlib,socket,sys
p=pathlib.Path(sys.argv[1]); out=pathlib.Path(sys.argv[2]); port=int(sys.argv[3])
out.write_text('synthetic worker write')
for label,action in (('control-read',lambda:p.read_bytes()),('control-write',lambda:p.write_text('changed')),('network-connect',lambda:socket.create_connection(('127.0.0.1',port),timeout=2))):
 try: action()
 except OSError as error:
  expected = (errno.EACCES,errno.EPERM) if label == 'network-connect' else (errno.EACCES,errno.EPERM,errno.ENOENT)
  if error.errno in expected: continue
  print('unexpected-route-error:'+label,file=sys.stderr)
  raise SystemExit(10)
 print('unexpected-route-success:'+label,file=sys.stderr)
 raise SystemExit(9)
print('restricted-routes-passed')
'''
    try:
        # Detail mode is internal to this exact fixed synthetic invocation. There
        # is deliberately no CLI flag or generic run() option to enable it elsewhere.
        result = subprocess.run([*prefix, '/usr/bin/python3', '-c', code, str(secret), str(worker / 'result'), str(port)],
            input=None, text=True, capture_output=True, timeout=45, env=env, cwd=worker)
        if result.returncode != 0:
            raise SyntheticProbeFailure(result.stderr, result.returncode)
        require(result.stdout.strip() == 'restricted-routes-passed', 'sandbox-probe-result-invalid')
        trusted_parent_checks(prefix, env, worker, secret)
        after = secret.stat()
        require((before.st_dev,before.st_ino) == (after.st_dev,after.st_ino), 'control-fixture-changed')
        require(secret.read_text() == 'SYNTHETIC CONTROL ONLY', 'control-fixture-mutated')
        # A missing listener must not be mistaken for network isolation.
        with socket.create_connection(('127.0.0.1', port), timeout=2):
            connection, _ = listener.accept()
            connection.close()
    finally:
        listener.close()
    return trusted, prefix, worker


CONSUMER_CODE = """import errno,json,pathlib,sys
for name in sys.argv[1:]:
 try: pathlib.Path(name).read_bytes()
 except OSError as error:
  if error.errno in (errno.EACCES,errno.EPERM,errno.ENOENT): continue
  raise
 raise SystemExit(11)
x=json.load(sys.stdin)
assert x['files']==[{'name':'counter.txt','content':'1'}]
assert int(x['files'][0]['content'])+1==2
print('consumed')
"""


def consume_released_bundle(sandbox_prefix, env, worker, db, control, output):
    # The trusted exporter remains outside. This separate recipient inherits the
    # worker's restricted profile; synthetic paths are denial probes, not grants.
    require(db.is_file() and control.is_file(), 'consumer-denial-fixture-missing')
    fixtures = (db, control)
    before = [(info.st_dev, info.st_ino) for info in (path.stat() for path in fixtures)]
    for path in fixtures:
        path.read_bytes()
    result = run([*sandbox_prefix, '/usr/bin/python3', '-c', CONSUMER_CODE,
                  str(db), str(control)], env, worker, output)
    # ENOENT inside a namespace is evidence only while the trusted fixtures still
    # exist at the same identities outside it. Other I/O errors are not denial.
    try:
        after = [(info.st_dev, info.st_ino) for info in (path.stat() for path in fixtures)]
    except OSError:
        raise Unsupported('consumer-denial-fixture-changed') from None
    require(before == after, 'consumer-denial-fixture-changed')
    return result


def service_checks(package, trusted, base, env, sandbox_prefix, worker):
    service = package / 'scripts/publication_service.py'
    db = trusted / 'ledger.sqlite'
    argv = ['/usr/bin/python3', '-B', str(service), '--db', str(db)]
    run([*argv, '--initialize'], env, base)
    def control(value):
        return json.loads(run([*argv, '--control'], env, base, json.dumps(value)).stdout)
    binding = control({'action':'register','destination':'sample-product','owner':'sample-owner',
        'audience':'sample-users','visibility':'public','revision':'r1',
        'authority_revision':'a1','policy_revision':'p1'})['binding']
    envelope = {'operation':'local-release','destination':'sample-product',
        'body':'SYNTHETIC implemented counter','files':[{'name':'counter.txt','content':'1'}],
        'metadata':{'title':'SYNTHETIC usage'}}
    def start():
        rpc = RPC(argv, env, base)
        rpc.call('initialize', {'protocolVersion':'2024-11-05','capabilities':{},
                               'clientInfo':{'name':'qualification','version':'1'}}, True)
        return rpc
    def call(rpc, name):
        reply = rpc.call('tools/call', {'name':'delivery_publication_'+name,
            'arguments':{'operation_id':'synthetic-one','envelope':envelope}}, True)
        return json.loads(reply['content'][0]['text'])['status']
    # The restricted candidate has only its stdin/stdout data channel. The
    # trusted broker owns the ledger and the approval CLI, outside that worker.
    fixtures = (db, service)
    before = [(info.st_dev,info.st_ino) for info in (path.stat() for path in fixtures)]
    for path in fixtures:
        path.read_bytes()
    with db.open('ab'):
        pass
    candidate_code = r"""import errno,json,sys,pathlib
value=json.loads(sys.argv[1]); ledger=pathlib.Path(sys.argv[2]); service=pathlib.Path(sys.argv[3])
# These are resource-isolation checks, not handler authorization checks.
for action in (lambda:ledger.read_bytes(),lambda:ledger.open('ab'),lambda:service.read_bytes()):
 try: action()
 except OSError as error:
  if error.errno in (errno.EACCES,errno.EPERM,errno.ENOENT): continue
  raise SystemExit(11)
 raise SystemExit(10)

def call(i,method,params):
 print(json.dumps({'jsonrpc':'2.0','id':i,'method':method,'params':params}),flush=True)
 reply=json.loads(sys.stdin.readline()); assert reply['id']==i
 return reply['result']
call(1,'initialize',{'protocolVersion':'2024-11-05','capabilities':{},'clientInfo':{'name':'worker','version':'1'}})
names={x['name'] for x in call(2,'tools/list',{})['tools']}
assert names=={'delivery_publication_submit','delivery_publication_publish','delivery_publication_receipt'}
for i,name,status in [(3,'submit','submitted'),(4,'publish','blocked'),(5,'publish','completed'),(6,'receipt','completed')]:
 result=call(i,'tools/call',{'name':'delivery_publication_'+name,'arguments':{'operation_id':'synthetic-one','envelope':value}})
 assert json.loads(result['content'][0]['text'])['status']==status
print(json.dumps({'done':True}),flush=True)
"""
    rpc = start()
    candidate = RPC([*sandbox_prefix, '/usr/bin/python3', '-c', candidate_code,
                     json.dumps(envelope), str(db), str(service)], env, worker)
    seen = []
    try:
        while True:
            try:
                request = candidate.messages.get(timeout=20)
            except queue.Empty:
                raise Unsupported('sandbox-candidate-timeout') from None
            require(isinstance(request, dict), 'sandbox-candidate-unavailable')
            if request == {'done':True}:
                break
            require(set(request) == {'jsonrpc','id','method','params'}, 'candidate-frame-invalid')
            require(request['method'] in {'initialize','tools/list','tools/call'}, 'candidate-method-invalid')
            # No candidate frame can select argv, ledger or trusted control.
            reply = rpc.call(request['method'], request['params'], True)
            seen.append(request['id'])
            if request['id'] == 4:
                require(json.loads(reply['content'][0]['text'])['status'] == 'blocked', 'unreviewed-release-allowed')
                require(control({'action':'review','operation_id':'synthetic-one','envelope':envelope,
                    'decision':'approve','ttl_seconds':30,'expected_binding':binding})['status'] == 'recorded', 'review-failed')
            candidate.send({'jsonrpc':'2.0','id':request['id'],'result':reply})
            if request['id'] == 5:
                rpc.close()
                rpc = start()
        require(seen == [1,2,3,4,5,6], 'candidate-journey-incomplete')
        require(candidate.process.wait(timeout=5) == 0, 'candidate-assertion-failed')
        after = [(info.st_dev,info.st_ino) for info in (path.stat() for path in fixtures)]
        require(before == after, 'candidate-denial-fixture-changed')
    finally:
        candidate.close()
        rpc.close()
    output = run([*argv, '--consume', 'synthetic-one'], env, base).stdout
    consumer = consume_released_bundle(sandbox_prefix, env, worker, db,
                                       trusted / 'synthetic-control', output)
    require(json.loads(output) == envelope and consumer.stdout.strip() == 'consumed', 'consumer-envelope-mismatch')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--clean-runner', action='store_true')
    parser.add_argument('--check-host-only', action='store_true')
    parser.add_argument('--codex')
    parser.add_argument('--package-root', type=Path)
    args = parser.parse_args()
    stage = 'host-preflight'
    try:
        actual_home = check_host(args.clean_runner)
        if args.check_host_only:
            print(json.dumps({'status':'clean-host-preflight-passed','runtime':'not-run'}))
            return 0
        require(args.codex and args.package_root, 'codex-and-package-root-required')
        env = child_environment(os.environ)
        with tempfile.TemporaryDirectory(prefix='delivery-qualification-') as directory:
            base = Path(directory)
            stage = 'install-discovery'
            package, inventory_count = install(args.codex, args.package_root.resolve(), base, env, actual_home)
            stage = 'sandbox-command-boundary'
            trusted, sandbox_prefix, worker = sandbox_checks(args.codex, base, env, actual_home)
            stage = 'native-mcp-discovery'
            inventory_count = native_discovery_checks(args.codex, package, trusted, base, env, sandbox_prefix, worker)
            stage = 'installed-service-local-release'
            service_checks(package, trusted, base, env, sandbox_prefix, worker)
        print(json.dumps({'status':'deterministic-conformance-passed','mcp_servers_discovered':inventory_count,
            'model_calls':0,'whole_host_acceptance':False,'semantic_acceptance':False,
            'fresh_model_acceptance':False,'remote_publication':'not-tested'}))
        return 0
    except (Unsupported, OSError, ValueError, KeyError, subprocess.TimeoutExpired) as error:
        print(json.dumps(failure_report(stage, error)))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
