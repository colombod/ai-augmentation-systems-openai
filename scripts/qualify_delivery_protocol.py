#!/usr/bin/env python3
"""Canned loopback protocol compatibility; no model or enforced-host claim."""
import argparse
import hashlib
import http.server
import json
import os
from pathlib import Path
import queue
import re
import sqlite3
import shutil
import subprocess
import threading
import time
import tempfile
import sys
from qualify_delivery_host import check_host, resolve_native_codex, require_publication_inventory

ROOT = None
TOOLS = {'delivery_publication_submit', 'delivery_publication_publish', 'delivery_publication_receipt'}
ARGS = {'operation_id': 'synthetic-one', 'envelope': {
    'operation': 'local-release', 'destination': 'synthetic-sink',
    'body': 'Synthetic public sample', 'files': [], 'metadata': {}}}
MAX_BODY = 2 * 1024 * 1024
MAX_RPC_ITEMS = 256
MAX_RPC_BYTES = 8 * 1024 * 1024


REASON_CODES = frozenset({
    'rpc-capacity', 'result-type', 'result-content', 'result-header', 'result-json',
    'result-status', 'result-approval-required', 'result-tool-unavailable',
    'result-tool-call-error', 'result-argument-error', 'result-cancelled', 'consumer-refusal', 'handler-arguments', 'stored-draft', 'ledger-counts',
    'bootstrap-node-missing', 'bootstrap-node-version',
    'stage-failed', 'rpc-stream-failed', 'rpc-error', 'rpc-timeout', 'turn-failed',
    'turn-reply-invalid', 'fixture-incomplete', 'continuation-count', 'call-output-count',
    'discovery-type', 'discovery-call-id', 'discovery-status', 'discovery-execution',
    'discovery-tools-shape', 'discovery-tool-count', 'discovery-namespace',
    'discovery-name', 'discovery-duplicate', 'discovery-tool-kind',
    'discovery-parameters', 'discovery-incomplete', 'expected-schema-invalid'})


class ProbeFailure(RuntimeError):
    def __init__(self, code):
        self.code = code if isinstance(code, str) and code in REASON_CODES else 'stage-failed'
        super().__init__(self.code)


def require(ok, message, code=None):
    if not ok:
        if code is not None:
            raise ProbeFailure(code)
        raise RuntimeError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def call_item(name, arguments, call_id, namespace=None, custom=False):
    item = {'type': 'custom_tool_call' if custom else 'function_call',
            'name': name, 'call_id': call_id}
    item['input' if custom else 'arguments'] = arguments if custom else json.dumps(arguments)
    if namespace:
        item['namespace'] = namespace
    return item


def sse(item, ident='synthetic-response'):
    events = [{'type': 'response.created', 'response': {'id': ident}}]
    if item:
        events.append({'type': 'response.output_item.done', 'item': item})
    events.append({'type': 'response.completed', 'response': {'id': ident,
        'usage': {'input_tokens': 0, 'output_tokens': 0, 'total_tokens': 0}}})
    return ''.join('event: ' + e['type'] + '\ndata: ' + json.dumps(e) + '\n\n' for e in events).encode()


def schemas(body):
    """Preserve namespaces and deferred tools; never assume three total tools."""
    found = []
    for tool in body.get('tools', []):
        if tool.get('type') == 'namespace':
            for child in tool.get('tools', []):
                found.append((tool['name'], child['name'], child))
        elif 'name' in tool:
            found.append((None, tool['name'], tool))
    return found


def output_for(body, call_id):
    return [i for i in body.get('input', []) if i.get('call_id') == call_id
            and i.get('type') in ('function_call_output', 'custom_tool_call_output', 'tool_search_output')]


class Script:
    """In-process finite Responses script; no outbound HTTP client or forwarding."""
    def __init__(self):
        self.steps = []
        self.requests = []
        self.errors = []
        self.contacts = []
        self.lock = threading.Lock()

    def arm(self, steps):
        with self.lock:
            require(not self.steps, 'previous script not consumed')
            self.steps = list(steps)
            self.requests = []

    def respond(self, body):
        with self.lock:
            require(len(self.requests) < 12, 'request bound exceeded')
            self.requests.append(body)
            require(self.steps, 'unexpected request after script exhausted')
            step = self.steps.pop(0)
            return sse(step(body) if callable(step) else step, 'response-' + str(len(self.requests)))


class Handler(http.server.BaseHTTPRequestHandler):
    def setup(self):
        self.request.settimeout(10)  # Bound request-line/header reads as well as body reads.
        super().setup()

    def log_message(self, *_):
        pass

    def do_GET(self):
        self.server.script.contacts.append({'method': self.command, 'path': self.path})
        self.send_error(404, 'No synthetic route')

    do_PUT = do_GET
    do_DELETE = do_GET
    do_CONNECT = do_GET

    def do_POST(self):
        try:
            if self.path != '/v1/responses':
                self.server.script.contacts.append({'method':self.command,'path':self.path})
            require(self.path == '/v1/responses', 'unexpected path')
            require(not self.headers.get('Authorization'), 'credential unexpectedly supplied')
            require(not self.headers.get('Transfer-Encoding'), 'chunked input unsupported')
            require(not self.headers.get('Content-Encoding'), 'encoded input unsupported')
            length = int(self.headers.get('Content-Length', '0'))
            require(0 < length <= MAX_BODY, 'body bound')
            self.connection.settimeout(10)
            data = self.rfile.read(length)
            require(len(data) == length, 'short request')
            payload = self.server.script.respond(json.loads(data))
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream')
            self.send_header('Content-Length', str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        except Exception as exc:
            self.server.script.errors.append(str(exc))
            self.send_error(400, 'synthetic fixture refused request')


class RPC:
    def __init__(self, command, env, evidence):
        self.log = []
        self.serial = 0
        self.completed = {}
        self.inbox = queue.Queue(maxsize=MAX_RPC_ITEMS)
        self.overflow = threading.Event()
        self.log_bytes = 0
        self.inbox_bytes = 0
        self.inbox_lock = threading.Lock()
        self.evidence = evidence
        self.stderr = (evidence / 'stderr.txt').open('w')
        self.process = subprocess.Popen(command, cwd=ROOT / 'worker', env=env,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.stderr,
            text=True, bufsize=1)
        self.reader = threading.Thread(target=self._read, daemon=True)
        self.reader.start()

    def _read(self):
        try:
            while line := self.process.stdout.readline(MAX_BODY + 1):
                require(len(line) <= MAX_BODY and line.endswith("\n"), 'RPC frame bound')
                value = json.loads(line)
                size = len(line.encode('utf-8'))
                with self.inbox_lock:
                    if self.inbox_bytes + size > MAX_RPC_BYTES:
                        self.overflow.set()
                        return
                    self.inbox_bytes += size
                self.inbox.put_nowait((value, size))
        except Exception as exc:
            self.overflow.set() if isinstance(exc, queue.Full) else self._reader_end(str(exc))
        finally:
            self._reader_end('EOF')

    def _reader_end(self, message):
        try:
            self.inbox.put_nowait(({'local_error': message}, 0))
        except queue.Full:
            self.overflow.set()

    def retain(self, value):
        size = len(json.dumps(value).encode('utf-8'))
        require(len(self.log) < MAX_RPC_ITEMS and self.log_bytes + size <= MAX_RPC_BYTES,
                'RPC log capacity', 'rpc-capacity')
        self.log_bytes += size
        self.log.append(value)

    def send(self, value):
        self.retain({'sent': value})
        self.process.stdin.write(json.dumps(value) + '\n')
        self.process.stdin.flush()

    def receive(self, deadline):
        require(not self.overflow.is_set(), 'RPC inbox capacity', 'rpc-capacity')
        value, size = self.inbox.get(timeout=max(.01, deadline-time.monotonic()))
        with self.inbox_lock:
            self.inbox_bytes -= size
        require(not self.overflow.is_set(), 'RPC inbox capacity', 'rpc-capacity')
        self.retain({'received': value})
        require('local_error' not in value, str(value), 'rpc-stream-failed')
        if 'id' in value and 'method' in value:
            self.send({'id': value['id'], 'error': {'code': -32601,
                'message': 'Fixture refuses client action'}})
            raise RuntimeError('unexpected client request')
        if value.get('method') == 'turn/completed':
            params = value['params']
            key = (params['threadId'], params['turn']['id'])
            require(key not in self.completed and len(self.completed) < 64, 'terminal buffer invalid')
            self.completed[key] = params['turn']
        return value

    def call(self, method, params):
        self.serial += 1
        ident = self.serial
        self.send({'id': ident, 'method': method, 'params': params})
        deadline = time.monotonic()+45
        while time.monotonic() < deadline:
            value = self.receive(deadline)
            if value.get('id') == ident and 'method' not in value:
                require('error' not in value, json.dumps(value), 'rpc-error')
                return value['result']
        raise ProbeFailure('rpc-timeout')

    def finish_turn(self, thread, turn):
        deadline = time.monotonic()+45
        key = (thread, turn)
        while time.monotonic() < deadline:
            if key in self.completed:
                result = self.completed.pop(key)
                require(result['status'] == 'completed', 'turn failed', 'turn-failed')
                return
            self.receive(deadline)
        raise ProbeFailure('rpc-timeout')

    def close(self):
        self.process.terminate()
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=5)
        self.reader.join(timeout=2)
        self.stderr.close()
        self.process.stdin.close()
        self.process.stdout.close()
        write_json(self.evidence / 'rpc.json', self.log)
        write_json(self.evidence / 'process.json', {'returncode': self.process.returncode})


def normalized_parameters(schema):
    """Pinned 0.163.0 lowering for this service's schema subset only.

    Native tools omit maxLength/maxItems/maxProperties; the handler still enforces
    its own limits. This comparison is not evidence of model-side validation.
    """
    require(isinstance(schema, dict), 'invalid parameter schema', 'expected-schema-invalid')
    allowed = {'type', 'properties', 'required', 'additionalProperties', 'items',
               'const', 'enum', 'maxLength', 'maxItems', 'maxProperties'}
    require(set(schema) <= allowed, 'unhandled schema keyword', 'expected-schema-invalid')
    result = {k:v for k,v in schema.items() if k not in {'maxLength','maxItems','maxProperties'}}
    if 'const' in result:
        result['enum'] = [result.pop('const')]
        result.setdefault('type', 'string')
    if result.get('type') == 'object':
        result['properties'] = {k:normalized_parameters(v) for k,v in result.get('properties', {}).items()}
    for key in ('items', 'additionalProperties'):
        if isinstance(result.get(key), dict):
            result[key] = normalized_parameters(result[key])
    return result


def discovered_tools(result, expected, call_id='discover', wanted=None):
    wanted = TOOLS if wanted is None else wanted
    require(isinstance(result, dict) and result.get('type') == 'tool_search_output',
            'invalid discovery type', 'discovery-type')
    require(result.get('call_id') == call_id, 'invalid discovery call', 'discovery-call-id')
    require(result.get('status') == 'completed', 'invalid discovery status', 'discovery-status')
    require(result.get('execution') == 'client', 'invalid discovery execution', 'discovery-execution')
    tools = result.get('tools')
    require(isinstance(tools, list), 'invalid tool list', 'discovery-tools-shape')
    for tool in tools:
        require(isinstance(tool, dict) and tool.get('type') == 'namespace',
                'invalid tool', 'discovery-tools-shape')
        if tool.get('type') == 'namespace':
            require(tool.get('name') == 'mcp__delivery_publication',
                    'unexpected namespace', 'discovery-namespace')
            require(isinstance(tool.get('tools'), list) and bool(tool['tools']),
                    'invalid namespace', 'discovery-tools-shape')
            require(all(isinstance(child, dict) and isinstance(child.get('name'), str)
                        for child in tool['tools']), 'invalid child tools', 'discovery-tools-shape')
    rows = schemas({'tools': tools})
    require(len(rows) == len(wanted), 'unexpected deferred tool count', 'discovery-tool-count')
    found = {}
    for ns, name, spec in rows:
        require(ns == 'mcp__delivery_publication', 'unexpected namespace', 'discovery-namespace')
        require(name in wanted, 'unexpected tool name', 'discovery-name')
        require(name not in found, 'duplicate tool', 'discovery-duplicate')
        require(spec.get('type') == 'function', 'unexpected tool kind', 'discovery-tool-kind')
        require(json.dumps(spec.get('parameters'), sort_keys=True) ==
                json.dumps(normalized_parameters(expected[name]), sort_keys=True),
                'deferred parameters differ from live inventory', 'discovery-parameters')
        found[name] = (ns, name)
    require(set(found) == wanted, 'incomplete discovery', 'discovery-incomplete')
    return found


def result_status(result, expected):
    require(result.get('type') == 'function_call_output', 'unexpected continuation type', 'result-type')
    value = result.get('output')
    require(isinstance(value, list) and len(value) == 2, 'unexpected MCP content', 'result-content')
    require(all(isinstance(v, dict) and v.get('type') == 'input_text' for v in value), 'unexpected content type', 'result-content')
    require(all(isinstance(v.get('text'), str) for v in value), 'invalid text', 'result-content')
    require(re.fullmatch(r'Wall time: [0-9]+\.[0-9]{4} seconds\nOutput:', value[0]['text'])
            is not None, 'missing native MCP output header', 'result-header')
    try:
        state = json.loads(value[1]['text'])
    except ValueError:
        # Pinned native failures are text, not handler JSON. Classify only fixed
        # source-defined forms; never print the text or reinterpret it as success.
        text = value[1]['text']
        if text == 'MCP tool call requires approval, but approval policy is never':
            code = 'result-approval-required'
        elif text in {'MCP tool `delivery_publication/' + name + '` is not available to the model'
                      for name in TOOLS}:
            code = 'result-tool-unavailable'
        elif text == 'user cancelled MCP tool call':
            code = 'result-cancelled'
        elif text.startswith('tool call error: '):
            code = 'result-tool-call-error'
        elif text.startswith('err: '):
            code = 'result-argument-error'
        else:
            code = 'result-json'
        raise ProbeFailure(code) from None
    require(isinstance(state, dict) and state.get('status') == expected,
            'unexpected handler status', 'result-status')


def normal_config(root, port, service, observer=None):
    q = lambda v: json.dumps(str(v), ensure_ascii=False)
    arguments = ['-B', str(service), '--db', str(root / 'ledger.sqlite')]
    if observer is not None:
        arguments = ['-B', str(observer), str(service), str(root / 'handler.jsonl'),
                     '--db', str(root / 'ledger.sqlite')]
    return f'''model = "gpt-6-sol"
model_provider = "synthetic-loopback"
approval_policy = "never"
web_search = "disabled"
default_permissions = "synthetic-local"
[permissions.synthetic-local]
filesystem = {{ ":minimal" = "read", {q(root / 'worker')} = "write" }}
network.enabled = false
[features]
apps = false
plugins = false
shell_tool = false
multi_agent = false
multi_agent_v2 = false
code_mode = false
[model_providers.synthetic-loopback]
name = "Finite canned protocol fixture"
base_url = "http://127.0.0.1:{port}/v1"
wire_api = "responses"
requires_openai_auth = false
supports_websockets = false
request_max_retries = 0
stream_max_retries = 0
[mcp_servers.delivery_publication]
command = "/usr/bin/python3"
args = {json.dumps(arguments, ensure_ascii=False)}
enabled_tools = {json.dumps(sorted(TOOLS))}
'''


def ledger(root):
    with sqlite3.connect((root / 'ledger.sqlite').resolve().as_uri() + '?mode=ro', uri=True) as db:
        return {t: db.execute('SELECT count(*) FROM ' + t).fetchone()[0]
                for t in ('drafts', 'reviews', 'releases')}


def run_case(rpc, script, thread, item):
    script.arm([item, None])
    try:
        started = rpc.call('turn/start', {'threadId': thread, 'input': [
            {'type': 'text', 'text': 'Run the canned synthetic protocol step.', 'text_elements': []}]})
        require(isinstance(started, dict) and isinstance(started.get('turn'), dict)
                and isinstance(started['turn'].get('id'), str), 'invalid turn reply', 'turn-reply-invalid')
        rpc.finish_turn(thread, started['turn']['id'])
        require(not script.steps and not script.errors and not script.contacts, 'script failed', 'fixture-incomplete')
        require(len(script.requests) == 2, 'missing native continuation', 'continuation-count')
        results = output_for(script.requests[1], item['call_id'])
        require(len(results) == 1, 'missing unique matching call output', 'call-output-count')
        return results[0]
    finally:
        if getattr(rpc, 'evidence', None) is not None:
            # Filename is a fixed canned call ID, never a provider-supplied value.
            require(item['call_id'] in {'discover','discover-submit','discover-publish','discover-receipt',
                                        'submit','publish','receipt'}, 'unknown case')
            write_json(rpc.evidence / (item['call_id'] + '.json'), {
                'requests':script.requests, 'errors':script.errors, 'contacts':script.contacts})


def discover_exact_tools(rpc, script, thread, expected):
    # Pinned tool_search ranks matches; it is not an exhaustive inventory.
    # Query each exact name and require its exact identity/schema. The separate
    # full inventory and this aggregate must still contain all three tools.
    found = {}
    for name in sorted(TOOLS):
        ident = 'discover-' + name.rsplit('_', 1)[1]
        item = {'type':'tool_search_call', 'call_id':ident, 'execution':'client',
                'arguments':{'query':name, 'limit':1}}
        result = run_case(rpc, script, thread, item)
        found.update(discovered_tools(result, expected, ident, {name}))
    require(set(found) == TOOLS, 'incomplete discovery', 'discovery-incomplete')
    return found


def verify_handler_effects(root):
    expected = [{'name':'delivery_publication_' + suffix, 'arguments':ARGS}
                for suffix in ('submit','publish','receipt')]
    with (root / 'handler.jsonl').open() as capture:
        raw = capture.read(MAX_BODY + 1)
    require(len(raw) <= MAX_BODY, 'handler capture over limit')
    require([json.loads(line) for line in raw.splitlines()] == expected, 'handler arguments differ', 'handler-arguments')
    with sqlite3.connect((root / 'ledger.sqlite').resolve().as_uri() + '?mode=ro', uri=True) as db:
        rows = db.execute('SELECT operation_id,envelope FROM drafts').fetchall()
    canonical = json.dumps(ARGS['envelope'], sort_keys=True, separators=(',', ':'), ensure_ascii=True)
    require(rows == [(ARGS['operation_id'], canonical)], 'stored draft differs', 'stored-draft')


def snapshot_ledger(root, out):
    with sqlite3.connect((root / 'ledger.sqlite').resolve().as_uri() + '?mode=ro', uri=True) as source:
        with sqlite3.connect(out / 'ledger.sqlite') as target:
            source.backup(target)


def verify_consumer(result, out):
    write_json(out / 'consumer.json', {'returncode':result.returncode,
        'stdout':result.stdout[:MAX_BODY], 'stderr':result.stderr[:MAX_BODY]})
    require(result.returncode == 2 and result.stdout == '' and
            result.stderr.strip() == '{"status":"unavailable"}',
            'consumer refusal differs', 'consumer-refusal')


STAGES = ('preflight','bootstrap','trusted-setup','initialize','inventory','discovery',
          'submit','publish','receipt','effects','consume','complete')


def diagnostic_summary(stage, passed, script=None, reason=None):
    # Only fixed labels and saturated counts leave the runner. Never serialize
    # exceptions, request values, prompts, paths, headers or arbitrary hashes.
    stage = stage if stage in STAGES else 'preflight'
    reason = reason if isinstance(reason, str) and reason in REASON_CODES else 'stage-failed'
    kinds = ('function_call_output','tool_search_output','custom_tool_call_output')
    counts = {k:0 for k in kinds}
    requests = getattr(script, 'requests', [])
    for request in requests[:12]:
        if isinstance(request, dict) and isinstance(request.get('input'), list):
            for item in request['input'][:128]:
                if isinstance(item, dict) and isinstance(item.get('type'), str) and item['type'] in counts:
                    kind = item['type']; counts[kind] = min(128, counts[kind] + 1)
    return {'status':'canned-protocol-compatible' if passed else 'canned-protocol-failed',
        'stage':stage, 'reason':'checks-passed' if passed else reason,
        'requests':min(12,len(requests)), 'output_types':counts,
        'fixture_errors':min(12,len(getattr(script,'errors',[]))),
        'unexpected_contacts':min(12,len(getattr(script,'contacts',[]))),
        'raw_trace_retention':'local-files-not-uploaded', 'model_inference':False,
        'managed_enforcement':False, 'host_egress_isolation':False, 'real_actor_acceptance':False}


def resolve_bootstrap(codex, runtime_env, cwd, bootstrap_path):
    # Only Node's selected installation directory enters the trusted resolver.
    # The native runtime keeps its separate credential-free environment.
    selected = shutil.which('node', path=bootstrap_path)
    require(selected is not None and Path(selected).is_absolute(), 'bootstrap Node unavailable', 'bootstrap-node-missing')
    node = Path(selected)
    bootstrap_env = dict(runtime_env, PATH=str(node.parent) + os.pathsep + runtime_env['PATH'])
    version = subprocess.run([str(node), '--version'], env=bootstrap_env, cwd=cwd,
                             capture_output=True, text=True, timeout=10, check=True)
    require(version.stdout.strip() == 'v22.14.0', 'pinned bootstrap Node required', 'bootstrap-node-version')
    return resolve_native_codex(codex, bootstrap_env, cwd)


def _execute(codex, package, out, opt_in, progress):
    global ROOT
    check_host(opt_in)  # Refuse nested/cloud or previously configured invocation.
    require(os.geteuid() != 0, 'ordinary runner required')
    require(not Path('/etc/codex').exists(), 'system configuration present')
    require(not out.exists(), 'new evidence directory required')
    out.mkdir(parents=True, mode=0o700)
    progress['evidence'] = out
    with tempfile.TemporaryDirectory(prefix='delivery-protocol-') as tmp:
        ROOT = Path(tmp)
        for name in ('home', 'worker'):
            (ROOT / name).mkdir(mode=0o700)
        env = {'PATH': '/usr/bin:/bin', 'HOME': str(ROOT / 'home'),
               'CODEX_HOME': str(ROOT / 'home'), 'LANG': 'C.UTF-8'}
        progress['stage'] = 'bootstrap'
        binary = resolve_bootstrap(codex, env, ROOT, os.environ.get('PATH', ''))
        version = subprocess.run([str(binary), '--version'], env=env, capture_output=True,
                                 text=True, timeout=10, check=True)
        require(version.stdout.strip() == 'codex-cli 0.163.0', 'pinned version required')
        progress['stage'] = 'trusted-setup'
        service = package.resolve() / 'plugins/delivery/scripts/publication_service.py'
        command = ['/usr/bin/python3', '-B', str(service), '--db', str(ROOT / 'ledger.sqlite')]
        subprocess.run(command + ['--initialize'], env=env, capture_output=True, timeout=10, check=True)
        binding = {'action':'register', 'destination':'synthetic-sink', 'owner':'synthetic-owner',
                   'audience':'synthetic-consumer', 'visibility':'private', 'revision':'one',
                   'authority_revision':'one', 'policy_revision':'one'}
        registered = subprocess.run(command + ['--control'], input=json.dumps(binding), env=env,
                                    capture_output=True, text=True, timeout=10, check=True)
        require(json.loads(registered.stdout)['status'] == 'recorded', 'registration failed')
        require(ledger(ROOT) == {'drafts':0, 'reviews':0, 'releases':0}, 'initial ledger mismatch')
        server = http.server.HTTPServer(('127.0.0.1', 0), Handler)
        server.script = Script()
        progress['script'] = server.script
        (ROOT / 'home/config.toml').write_text(normal_config(ROOT, server.server_port, service,
            package.resolve() / 'scripts/observe_publication_protocol.py'))
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        rpc = None
        try:
            progress['stage'] = 'initialize'
            rpc = RPC([str(binary), 'app-server', '--stdio'], env, out)
            rpc.call('initialize', {'clientInfo':{'name':'synthetic_compatibility', 'version':'1'},
                                   'capabilities':{'experimentalApi':True}})
            rpc.send({'method':'initialized'})
            progress['stage'] = 'inventory'
            inventory = rpc.call('mcpServerStatus/list', {'cursor':None, 'limit':100, 'detail':'full'})
            write_json(out / 'inventory.json', inventory)
            require_publication_inventory(inventory)
            expected = {n:t['inputSchema'] for n,t in inventory['data'][0]['tools'].items()}
            thread = rpc.call('thread/start', {'cwd':str(ROOT / 'worker')})['thread']['id']
            progress['stage'] = 'discovery'
            identities = discover_exact_tools(rpc, server.script, thread, expected)
            for suffix, status in [('submit','submitted'), ('publish','blocked'), ('receipt','not-released')]:
                progress['stage'] = suffix
                ns, name = identities['delivery_publication_' + suffix]
                result = run_case(rpc, server.script, thread, call_item(name, ARGS, suffix, ns))
                result_status(result, status)
            progress['stage'] = 'effects'
            snapshot_ledger(ROOT, out)
            verify_handler_effects(ROOT)
            counts = ledger(ROOT)
            require(counts == {'drafts':1, 'reviews':0, 'releases':0}, 'unexpected ledger effects', 'ledger-counts')
            progress['stage'] = 'consume'
            consume = subprocess.run(command + ['--consume','synthetic-one'], env=env,
                                     capture_output=True, text=True, timeout=10)
            verify_consumer(consume, out)
            progress['result'] = {'status':'canned-protocol-compatible', 'ledger':counts,
                'model_inference':False, 'managed_enforcement':False, 'host_egress_isolation':False,
                'real_actor_acceptance':False, 'binary_sha256':sha(binary), 'service_sha256':sha(service)}
        finally:
            try:
                write_json(out / 'last-fixture.json', {'requests':server.script.requests,
                    'errors':server.script.errors, 'contacts':server.script.contacts})
                if (ROOT / 'handler.jsonl').exists():
                    shutil.copyfile(ROOT / 'handler.jsonl', out / 'handler.jsonl')
            finally:
                try:
                    if rpc:
                        rpc.close()
                finally:
                    server.shutdown()
                    server.server_close()
                    worker.join(timeout=2)


def execute(codex, package, out, opt_in):
    progress = {'stage':'preflight'}
    passed = False
    try:
        _execute(codex, package, out, opt_in, progress)
        write_json(out / 'result.json', progress['result'])
        progress['stage'] = 'complete'
        passed = True
    except Exception as error:
        progress['reason'] = error.code if isinstance(error, ProbeFailure) else (
            'rpc-timeout' if isinstance(error, queue.Empty) else 'stage-failed')
        if 'evidence' in progress:
            try:
                write_json(progress['evidence'] / 'failure.json', {
                    'type':type(error).__name__, 'detail':str(error)[:MAX_BODY],
                    'stdout':str(getattr(error, 'stdout', ''))[:MAX_BODY],
                    'stderr':str(getattr(error, 'stderr', ''))[:MAX_BODY]})
            except Exception:
                pass  # A failed local save never becomes a claim of preservation.
        # Detailed files remain at the selected local path; disposable CI storage
        # is ephemeral. No transfer is configured and raw traces never enter CI output.
        pass
    print(json.dumps(diagnostic_summary(progress['stage'], passed, progress.get('script'), progress.get('reason'))))
    return 0 if passed else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--clean-runner', action='store_true')
    parser.add_argument('--codex', required=True)
    parser.add_argument('--package-root', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(execute(args.codex, args.package_root, args.evidence, args.clean_runner))
