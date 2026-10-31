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


def require(ok, message):
    if not ok:
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
        self.inbox = queue.Queue()
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
                self.inbox.put(json.loads(line))
        except Exception as exc:
            self.inbox.put({'local_error': str(exc)})
        finally:
            self.inbox.put({'local_error': 'EOF'})

    def send(self, value):
        self.log.append({'sent': value})
        self.process.stdin.write(json.dumps(value) + '\n')
        self.process.stdin.flush()

    def receive(self, deadline):
        value = self.inbox.get(timeout=max(.01, deadline-time.monotonic()))
        self.log.append({'received': value})
        require('local_error' not in value, str(value))
        if 'id' in value and 'method' in value:
            self.send({'id': value['id'], 'error': {'code': -32601,
                'message': 'Fixture refuses client action'}})
            raise RuntimeError('unexpected client request')
        return value

    def call(self, method, params):
        self.serial += 1
        ident = self.serial
        self.send({'id': ident, 'method': method, 'params': params})
        deadline = time.monotonic()+45
        while time.monotonic() < deadline:
            value = self.receive(deadline)
            if value.get('id') == ident and 'method' not in value:
                require('error' not in value, json.dumps(value))
                return value['result']
        raise RuntimeError('RPC timeout: outcome unknown, no automatic retry')

    def finish_turn(self):
        deadline = time.monotonic()+45
        while time.monotonic() < deadline:
            value = self.receive(deadline)
            if value.get('method') == 'turn/completed':
                require(value['params']['turn']['status'] == 'completed', json.dumps(value))
                return
        raise RuntimeError('turn timeout: outcome unknown')

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
    require(isinstance(schema, dict), 'invalid parameter schema')
    allowed = {'type', 'properties', 'required', 'additionalProperties', 'items',
               'const', 'enum', 'maxLength', 'maxItems', 'maxProperties'}
    require(set(schema) <= allowed, 'unhandled schema keyword')
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


def discovered_tools(result, expected):
    require(result.get('type') == 'tool_search_output' and result.get('call_id') == 'discover'
            and result.get('status') == 'completed' and result.get('execution') == 'client',
            'invalid discovery continuation')
    rows = schemas({'tools': result.get('tools', [])})
    require(len(rows) == 3, 'unexpected deferred tool count')
    found = {}
    for ns, name, spec in rows:
        require(ns == 'mcp__delivery_publication' and name in TOOLS and name not in found,
                'unexpected deferred identity')
        require(spec.get('type') == 'function' and spec.get('parameters') == normalized_parameters(expected[name]),
                'deferred parameters differ from live inventory')
        found[name] = (ns, name)
    require(set(found) == TOOLS, 'incomplete discovery')
    return found


def result_status(result, expected):
    require(result.get('type') == 'function_call_output', 'unexpected continuation type')
    value = result.get('output')
    require(isinstance(value, list) and len(value) == 2, 'unexpected MCP content')
    require(all(v.get('type') == 'input_text' for v in value), 'unexpected content type')
    require(re.fullmatch(r'Wall time: [0-9]+\.[0-9]{4} seconds\nOutput:', value[0]['text'])
            is not None, 'missing native MCP output header')
    state = json.loads(value[1]['text'])
    require(isinstance(state, dict) and state.get('status') == expected,
            'unexpected handler status')


def normal_config(root, port, service):
    q = lambda v: json.dumps(str(v), ensure_ascii=False)
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
args = ["-B", {q(service)}, "--db", {q(root / 'ledger.sqlite')}]
enabled_tools = {json.dumps(sorted(TOOLS))}
'''


def ledger(root):
    with sqlite3.connect('file:' + str(root / 'ledger.sqlite') + '?mode=ro', uri=True) as db:
        return {t: db.execute('SELECT count(*) FROM ' + t).fetchone()[0]
                for t in ('drafts', 'reviews', 'releases')}


def run_case(rpc, script, thread, item):
    script.arm([item, None])
    rpc.call('turn/start', {'threadId': thread, 'input': [
        {'type': 'text', 'text': 'Run the canned synthetic protocol step.', 'text_elements': []}]})
    rpc.finish_turn()
    require(not script.steps and not script.errors and not script.contacts, 'script failed')
    require(len(script.requests) == 2, 'missing native continuation')
    results = output_for(script.requests[1], item['call_id'])
    require(len(results) == 1, 'missing unique matching call output')
    return results[0]


def execute(codex, package, out, opt_in):
    global ROOT
    check_host(opt_in)  # Refuse nested/cloud or previously configured invocation.
    require(os.geteuid() != 0, 'ordinary runner required')
    require(not Path('/etc/codex').exists(), 'system configuration present')
    require(not out.exists(), 'new evidence directory required')
    out.mkdir(parents=True)
    with tempfile.TemporaryDirectory(prefix='delivery-protocol-') as tmp:
        ROOT = Path(tmp)
        for name in ('home', 'worker'):
            (ROOT / name).mkdir(mode=0o700)
        env = {'PATH': '/usr/bin:/bin', 'HOME': str(ROOT / 'home'),
               'CODEX_HOME': str(ROOT / 'home'), 'LANG': 'C.UTF-8'}
        binary = resolve_native_codex(codex, env, ROOT)
        version = subprocess.run([str(binary), '--version'], env=env, capture_output=True,
                                 text=True, timeout=10, check=True)
        require(version.stdout.strip() == 'codex-cli 0.163.0', 'pinned version required')
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
        (ROOT / 'home/config.toml').write_text(normal_config(ROOT, server.server_port, service))
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        rpc = None
        try:
            rpc = RPC([str(binary), 'app-server', '--stdio'], env, out)
            rpc.call('initialize', {'clientInfo':{'name':'synthetic_compatibility', 'version':'1'},
                                   'capabilities':{'experimentalApi':True}})
            rpc.send({'method':'initialized'})
            inventory = rpc.call('mcpServerStatus/list', {'cursor':None, 'limit':100, 'detail':'full'})
            require_publication_inventory(inventory)
            write_json(out / 'inventory.json', inventory)
            expected = {n:t['inputSchema'] for n,t in inventory['data'][0]['tools'].items()}
            thread = rpc.call('thread/start', {'cwd':str(ROOT / 'worker')})['thread']['id']
            discovery = {'type':'tool_search_call', 'call_id':'discover', 'execution':'client',
                         'arguments':{'query':'delivery_publication submit publish receipt', 'limit':10}}
            result = run_case(rpc, server.script, thread, discovery)
            identities = discovered_tools(result, expected)
            write_json(out / 'discovery.json', server.script.requests)
            for suffix, status in [('submit','submitted'), ('publish','blocked'), ('receipt','not-released')]:
                ns, name = identities['delivery_publication_' + suffix]
                result = run_case(rpc, server.script, thread, call_item(name, ARGS, suffix, ns))
                result_status(result, status)
                write_json(out / (suffix + '.json'), server.script.requests)
            counts = ledger(ROOT)
            require(counts == {'drafts':1, 'reviews':0, 'releases':0}, 'unexpected ledger effects')
            consume = subprocess.run(command + ['--consume','synthetic-one'], env=env,
                                     capture_output=True, text=True, timeout=10)
            require(consume.returncode == 2 and not consume.stdout.strip(), 'consumer released bundle')
            print(json.dumps({'status':'canned-protocol-compatible', 'model_inference':False,
                              'managed_enforcement':False, 'real_actor_acceptance':False}))
            write_json(out / 'result.json', {'status':'canned-protocol-compatible', 'ledger':counts,
                'model_inference':False, 'managed_enforcement':False, 'host_egress_isolation':False,
                'real_actor_acceptance':False, 'binary_sha256':sha(binary), 'service_sha256':sha(service)})
        finally:
            if rpc:
                rpc.close()
            server.shutdown()
            server.server_close()
            worker.join(timeout=2)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--clean-runner', action='store_true')
    parser.add_argument('--codex', required=True)
    parser.add_argument('--package-root', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    args = parser.parse_args()
    execute(args.codex, args.package_root, args.evidence, args.clean_runner)
