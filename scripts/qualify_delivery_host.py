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
            line = stream.readline(MAX_RPC_FRAME + 1)
            if not line:
                break
            if len(line) > MAX_RPC_FRAME or not line.endswith('\n'):
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
        self.process = subprocess.Popen(argv, env=env, cwd=cwd, text=True,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        self.messages = queue.Queue(maxsize=MAX_RPC_QUEUE)
        self.serial = 0
        threading.Thread(target=receive_messages,
                         args=(self.process.stdout, self.messages), daemon=True).start()

    def send(self, value):
        self.process.stdin.write(json.dumps(value) + '\n')
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
    config = ['-c', 'default_permissions="delivery-qualification"',
              '-c', 'permissions.delivery-qualification.filesystem.' + json.dumps(':minimal') + '="read"',
              '-c', 'permissions.delivery-qualification.filesystem.' + json.dumps(str(worker)) + '="write"',
              '-c', 'permissions.delivery-qualification.filesystem.' + json.dumps(str(trusted)) + '="deny"',
              '-c', 'permissions.delivery-qualification.filesystem.' + json.dumps(str(actual_home / '.codex')) + '="deny"',
              '-c', 'permissions.delivery-qualification.filesystem.' + json.dumps('/proc') + '="deny"',
              '-c', 'permissions.delivery-qualification.network.enabled=false']
    code = '''import pathlib,socket,sys
p=pathlib.Path(sys.argv[1]); out=pathlib.Path(sys.argv[2]); port=int(sys.argv[3])
out.write_text('synthetic worker write')
for action in (lambda:p.read_bytes(),lambda:p.write_text('changed'),lambda:pathlib.Path('/proc/self/environ').read_bytes(),lambda:socket.create_connection(('127.0.0.1',port),timeout=2)):
 try: action()
 except (OSError,PermissionError): continue
 raise SystemExit(9)
print('restricted-routes-passed')
'''
    try:
        # Detail mode is internal to this exact fixed synthetic invocation. There
        # is deliberately no CLI flag or generic run() option to enable it elsewhere.
        result = subprocess.run([codex, *config, 'sandbox', '--permission-profile', 'delivery-qualification',
            '--', '/usr/bin/python3', '-c', code, str(secret), str(worker / 'result'), str(port)],
            input=None, text=True, capture_output=True, timeout=45, env=env, cwd=worker)
        if result.returncode != 0:
            raise SyntheticProbeFailure(result.stderr, result.returncode)
        require(result.stdout.strip() == 'restricted-routes-passed', 'sandbox-probe-result-invalid')
        require(secret.read_text() == 'SYNTHETIC CONTROL ONLY', 'control-fixture-mutated')
    finally:
        listener.close()
    prefix = [codex, *config, 'sandbox', '--permission-profile', 'delivery-qualification', '--']
    return trusted, prefix, worker


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
    candidate_code = r"""import json,sys,pathlib,subprocess
value=json.loads(sys.argv[1]); ledger=pathlib.Path(sys.argv[2]); service=sys.argv[3]
for action in (lambda:ledger.read_bytes(),lambda:ledger.open('ab')):
 try: action()
 except OSError: continue
 raise SystemExit(10)
forged=subprocess.run(['/usr/bin/python3',service,'--db',str(ledger),'--control'],input='{}',text=True,capture_output=True,timeout=5)
assert forged.returncode != 0

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
    finally:
        candidate.close()
        rpc.close()
    output = run([*argv, '--consume', 'synthetic-one'], env, base).stdout
    # Clean recipient receives only bytes on stdin, not private ledger access/path.
    consumer = run(['/usr/bin/python3', '-c',
        'import json,sys;x=json.load(sys.stdin);assert x["files"]==[{"name":"counter.txt","content":"1"}];print("consumed")'],
        env, base, output)
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
