import copy
import contextlib
import io
import queue
import importlib.util
import json
import os
import subprocess
from pathlib import Path
import sys
import tempfile
import threading
import tomllib
import unittest
from unittest.mock import patch, MagicMock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import qualify_delivery_protocol as probe


class ProtocolTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location('fixture_service', ROOT / 'plugins/delivery/scripts/publication_service.py')
        service = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(service)
        self.service = service
        self.expected = {t['name']:t['inputSchema'] for t in service.TOOLS}
        self.result = {'type':'tool_search_output', 'call_id':'discover', 'status':'completed',
            'execution':'client', 'tools':[{'type':'namespace', 'name':'mcp__delivery_publication',
                'tools':[{'type':'function', 'name':n, 'parameters':probe.normalized_parameters(p)} for n,p in self.expected.items()]}]}

    def test_deferred_output_only_preserves_namespace_and_schema(self):
        found = probe.discovered_tools(self.result, self.expected)
        self.assertEqual(set(found), probe.TOOLS)
        for name, identity in found.items():
            self.assertEqual(identity, ('mcp__delivery_publication', name))
            item = probe.call_item(identity[1], probe.ARGS, name, identity[0])
            self.assertEqual(item['namespace'], identity[0])
        self.assertEqual(probe.output_for({'input':[self.result], 'tools':[]}, 'discover'), [self.result])

    def test_descriptions_and_next_request_tools_cannot_supply_discovery(self):
        bad = copy.deepcopy(self.result)
        bad['tools'] = [{'type':'function', 'name':'unrelated', 'description':' '.join(probe.TOOLS)}]
        with self.assertRaises(RuntimeError):
            probe.discovered_tools(bad, self.expected)
        self.assertEqual(probe.output_for({'input':[], 'tools':self.result['tools']}, 'discover'), [])

    def test_wrong_call_status_execution_namespace_duplicates_and_parameters_refused(self):
        for field, value in [('call_id','wrong'), ('status','failed'), ('execution','server'), ('type','function_call_output')]:
            bad = copy.deepcopy(self.result); bad[field] = value
            with self.subTest(field=field), self.assertRaises(RuntimeError):
                probe.discovered_tools(bad, self.expected)
        for mutate in [lambda b:b['tools'][0].update(name='other'),
                       lambda b:b['tools'][0]['tools'].append(b['tools'][0]['tools'][0]),
                       lambda b:b['tools'][0]['tools'][0].update(parameters={})]:
            bad = copy.deepcopy(self.result); mutate(bad)
            with self.assertRaises(RuntimeError): probe.discovered_tools(bad, self.expected)

    def test_discovery_invariants_have_distinct_fixed_reason_codes(self):
        cases = [
            ('discovery-type', lambda b:b.update(type='wrong')),
            ('discovery-call-id', lambda b:b.update(call_id='wrong')),
            ('discovery-status', lambda b:b.update(status='failed')),
            ('discovery-execution', lambda b:b.update(execution='server')),
            ('discovery-tools-shape', lambda b:b.update(tools={})),
            ('discovery-tool-count', lambda b:b.update(tools=[])),
            ('discovery-namespace', lambda b:b['tools'][0].update(name='other')),
            ('discovery-name', lambda b:b['tools'][0]['tools'][0].update(name='other')),
            ('discovery-duplicate', lambda b:b['tools'][0]['tools'].__setitem__(1,b['tools'][0]['tools'][0])),
            ('discovery-tool-kind', lambda b:b['tools'][0]['tools'][0].update(type='custom')),
            ('discovery-parameters', lambda b:b['tools'][0]['tools'][0].update(parameters={})),
        ]
        for reason, mutate in cases:
            bad = copy.deepcopy(self.result); mutate(bad)
            with self.subTest(reason=reason), self.assertRaises(probe.ProbeFailure) as caught:
                probe.discovered_tools(bad, self.expected)
            self.assertEqual(caught.exception.code, reason)
            output = io.StringIO()
            with patch.object(probe, '_execute', side_effect=caught.exception), \
                    contextlib.redirect_stdout(output):
                self.assertEqual(probe.execute('/unused', ROOT, ROOT, True), 1)
            self.assertEqual(json.loads(output.getvalue())['reason'], reason)
        self.assertEqual(set(probe.discovered_tools(self.result,self.expected)),probe.TOOLS)

    def test_untrusted_reason_text_cannot_escape_fixed_summary(self):
        sentinel = 'SYNTHETIC-PRIVATE-REASON'
        for value in [sentinel, [sentinel], {'code':sentinel}, None]:
            summary = probe.diagnostic_summary('discovery', False, reason=value)
            self.assertEqual(summary['reason'], 'stage-failed')
            self.assertNotIn(sentinel, json.dumps(summary))
        for error in [RuntimeError(sentinel), ValueError(sentinel), probe.ProbeFailure(sentinel)]:
            output = io.StringIO()
            with patch.object(probe, '_execute', side_effect=error), contextlib.redirect_stdout(output):
                self.assertEqual(probe.execute('/unused',ROOT,ROOT,True),1)
            self.assertEqual(json.loads(output.getvalue())['reason'],'stage-failed')
            self.assertNotIn(sentinel,output.getvalue())

    def test_exact_name_searches_require_all_three_strict_results(self):
        calls = []
        def search(rpc, script, thread, item):
            name = item['arguments']['query']
            self.assertEqual(item['arguments']['limit'], 1)
            self.assertEqual(item['call_id'], 'discover-' + name.rsplit('_',1)[1])
            calls.append(name)
            result = copy.deepcopy(self.result)
            result['call_id'] = item['call_id']
            result['tools'][0]['tools'] = [t for t in result['tools'][0]['tools'] if t['name'] == name]
            return result
        with patch.object(probe, 'run_case', side_effect=search):
            found = probe.discover_exact_tools(None,None,'thread',self.expected)
        self.assertEqual(calls, sorted(probe.TOOLS))
        self.assertEqual(set(found), probe.TOOLS)
        for name in probe.TOOLS:
            self.assertEqual(found[name], ('mcp__delivery_publication',name))

    def test_targeted_search_never_accepts_wrong_extra_or_changed_tool(self):
        name = sorted(probe.TOOLS)[0]; ident = 'discover-' + name.rsplit('_',1)[1]
        for fault in ('wrong-name','extra','changed-schema','wrong-call'):
            result = copy.deepcopy(self.result); result['call_id'] = ident
            result['tools'][0]['tools'] = [t for t in result['tools'][0]['tools'] if t['name'] == name]
            if fault == 'wrong-name': result['tools'][0]['tools'][0]['name'] = sorted(probe.TOOLS)[1]
            if fault == 'extra': result['tools'][0]['tools'].append(result['tools'][0]['tools'][0])
            if fault == 'changed-schema': result['tools'][0]['tools'][0]['parameters'] = {}
            if fault == 'wrong-call': result['call_id'] = 'discover-other'
            with self.subTest(fault=fault), self.assertRaises(probe.ProbeFailure):
                probe.discovered_tools(result,self.expected,ident,{name})
        with patch.object(probe,'run_case',return_value={
                'type':'tool_search_output','call_id':ident,'status':'completed','execution':'client','tools':[]}):
            with self.assertRaises(probe.ProbeFailure):
                probe.discover_exact_tools(None,None,'thread',self.expected)

    def test_actual_native_header_and_structural_status(self):
        value = {'type':'function_call_output', 'output':[
            {'type':'input_text','text':'Wall time: 0.0100 seconds\nOutput:'},
            {'type':'input_text','text':json.dumps({'status':'blocked'})}]}
        probe.result_status(value, 'blocked')
        for text in ['{"description":"blocked"}', '{"status":"not-blocked"}', 'blocked']:
            value['output'][1]['text'] = text
            with self.assertRaises((RuntimeError, ValueError)): probe.result_status(value, 'blocked')

    def test_self_contained_ordinary_config(self):
        root = Path('/tmp/synthetic-🚀')
        config = tomllib.loads(probe.normal_config(root, 12345, root / 'service.py'))
        self.assertIn(config['default_permissions'], config['permissions'])
        provider = config['model_providers'][config['model_provider']]
        self.assertEqual(provider['base_url'], 'http://127.0.0.1:12345/v1')
        self.assertFalse(provider['requires_openai_auth'])
        self.assertEqual(provider['request_max_retries'], 0)
        self.assertEqual(provider['stream_max_retries'], 0)
        self.assertEqual(set(config['mcp_servers']['delivery_publication']['enabled_tools']), probe.TOOLS)
        self.assertNotIn('--control', config['mcp_servers']['delivery_publication']['args'])

    def test_finite_sse_and_matching_continuations(self):
        script = probe.Script(); item = probe.call_item('synthetic', {}, 'one')
        script.arm([item, None])
        self.assertIn(b'response.output_item.done', script.respond({}))
        self.assertIn(b'response.completed', script.respond({}))
        with self.assertRaises(RuntimeError): script.respond({})
        self.assertEqual(probe.output_for({'input':[{'type':'function_call_output','call_id':'other'}]}, 'one'), [])

    def test_independent_ledger_effects_and_consumer_no_bundle(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store = self.service.PublicationStore(str(root / 'ledger.sqlite'), True)
            try:
                store.control({'action':'register', 'destination':'synthetic-sink',
                    'owner':'synthetic-owner', 'audience':'synthetic-consumer', 'visibility':'private',
                    'revision':'one', 'authority_revision':'one', 'policy_revision':'one'})
                for suffix, status in [('submit','submitted'),('publish','blocked'),('receipt','not-released')]:
                    value = store.call('delivery_publication_' + suffix, probe.ARGS)
                    self.assertEqual(value['status'], status)
                self.assertEqual(probe.ledger(root), {'drafts':1, 'reviews':0, 'releases':0})
                with self.assertRaises(self.service.Refused): store.consume('synthetic-one')
            finally:
                store.close()

    def test_sequence_refuses_missing_or_duplicate_call_outputs(self):
        for outputs in [[], [{'type':'function_call_output','call_id':'other'}],
                        [{'type':'function_call_output','call_id':'one'}] * 2]:
            script = probe.Script()
            class FakeRPC:
                def call(self, method, params):
                    script.respond({})
                    script.respond({'input':outputs})
                    return {'turn':{'id':'turn'}}
                def finish_turn(self, thread, turn):
                    pass
            with self.subTest(outputs=outputs), self.assertRaises(RuntimeError):
                probe.run_case(FakeRPC(), script, 'thread', probe.call_item('synthetic', {}, 'one'))

    def test_bootstrap_node_directory_is_separate_from_native_environment(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); node_dir = root / 'pinned-node'; node_dir.mkdir()
            node = node_dir / 'node'
            # Synthetic executable records the exact subprocess environment.
            recorded = root / 'environment.json'
            node.write_text('#!' + sys.executable + '\nimport os,json\n'
                + 'open(' + repr(str(recorded)) + ',"w").write(json.dumps(dict(os.environ)))\n'
                + 'print("v22.14.0")\n')
            node.chmod(0o700)
            native_env = {'PATH':'/usr/bin:/bin', 'HOME':str(root / 'home'),
                          'CODEX_HOME':str(root / 'home'), 'LANG':'C.UTF-8'}
            before = dict(native_env)
            def resolve(codex, env, cwd):
                self.assertEqual(probe.shutil.which('node', path=env['PATH']), str(node))
                self.assertEqual(env['PATH'], str(node_dir) + ':/usr/bin:/bin')
                self.assertEqual(set(env), set(native_env))
                return root / 'native-codex'
            with patch.dict(os.environ, {'OPENAI_API_KEY':'synthetic-no-credential',
                                         'NODE_OPTIONS':'synthetic-unused'}), \
                    patch.object(probe, 'resolve_native_codex', side_effect=resolve) as resolver:
                self.assertEqual(probe.resolve_bootstrap('/launcher', native_env, root,
                    str(node_dir) + ':/unrelated'), root / 'native-codex')
                resolver.assert_called_once()
            observed = json.loads(recorded.read_text())
            self.assertNotIn('OPENAI_API_KEY', observed)
            self.assertNotIn('NODE_OPTIONS', observed)
            self.assertEqual(native_env, before)
            self.assertNotIn(str(node_dir), native_env['PATH'])
            config = tomllib.loads(probe.normal_config(root, 12345, root / 'service.py'))
            provider = config['model_providers'][config['model_provider']]
            self.assertEqual(provider['base_url'], 'http://127.0.0.1:12345/v1')
            self.assertFalse(provider['requires_openai_auth'])

    def test_missing_or_wrong_bootstrap_node_refuses_before_resolver(self):
        env = {'PATH':'/usr/bin:/bin'}
        with patch.object(probe.shutil, 'which', return_value=None), \
                patch.object(probe, 'resolve_native_codex') as resolver:
            with self.assertRaises(RuntimeError): probe.resolve_bootstrap('/launcher', env, ROOT, '')
            resolver.assert_not_called()
        with patch.object(probe.shutil, 'which', return_value='/pinned/node'), \
                patch.object(probe.subprocess, 'run', return_value=subprocess.CompletedProcess([],0,'v20.0.0\n','')), \
                patch.object(probe, 'resolve_native_codex') as resolver:
            with self.assertRaises(RuntimeError): probe.resolve_bootstrap('/launcher', env, ROOT, '/pinned')
            resolver.assert_not_called()

    def test_early_terminal_notification_is_correlated_to_thread_and_turn(self):
        rpc = probe.RPC.__new__(probe.RPC)
        rpc.log = []; rpc.log_bytes = 0; rpc.serial = 0; rpc.inbox = queue.Queue(); rpc.completed = {}
        rpc.overflow = threading.Event(); rpc.inbox_bytes = 0; rpc.inbox_lock = threading.Lock()
        rpc.send = lambda value: None
        for thread, turn in [('other','turn'), ('thread','other'), ('thread','turn')]:
            rpc.inbox.put(({'method':'turn/completed', 'params':{'threadId':thread,
                'turn':{'id':turn,'status':'completed'}}}, 0))
        rpc.inbox.put(({'id':1, 'result':{'turn':{'id':'turn'}}}, 0))
        result = rpc.call('turn/start', {'threadId':'thread'})
        rpc.finish_turn('thread', result['turn']['id'])
        self.assertNotIn(('thread','turn'), rpc.completed)
        self.assertEqual(set(rpc.completed), {('other','turn'), ('thread','other')})
        with patch.object(rpc, 'receive', side_effect=queue.Empty):
            with self.assertRaises(queue.Empty): rpc.finish_turn('thread','missing')

    def test_failure_preserves_ephemeral_case_before_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            script = probe.Script()
            class FakeRPC:
                evidence = Path(tmp)
                def call(self, *args):
                    script.requests.append({'input':[{'type':'unknown','text':'synthetic raw'}]})
                    raise RuntimeError('synthetic failed')
            with self.assertRaises(RuntimeError):
                probe.run_case(FakeRPC(), script, 'thread',
                               probe.call_item('synthetic', {}, 'submit'))
            saved = json.loads((Path(tmp) / 'submit.json').read_text())
            self.assertEqual(saved['requests'], script.requests)
            self.assertEqual(saved['errors'], [])

    def test_observer_captures_actual_handler_arguments_and_exact_draft(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); db = root / 'ledger.sqlite'
            service = ROOT / 'plugins/delivery/scripts/publication_service.py'
            command = [sys.executable, '-B', str(service), '--db', str(db)]
            subprocess.run(command + ['--initialize'], capture_output=True, check=True)
            binding = {'action':'register','destination':'synthetic-sink','owner':'synthetic-owner',
                'audience':'synthetic-consumer','visibility':'private','revision':'one',
                'authority_revision':'one','policy_revision':'one'}
            subprocess.run(command + ['--control'], input=json.dumps(binding), text=True,
                           capture_output=True, check=True)
            requests = [{'jsonrpc':'2.0','id':i,'method':'tools/call','params':{
                'name':'delivery_publication_' + suffix,'arguments':probe.ARGS}}
                for i,suffix in enumerate(('submit','publish','receipt'),1)]
            observer = [sys.executable, '-B', str(ROOT / 'scripts/observe_publication_protocol.py'),
                        str(service), str(root / 'handler.jsonl'), '--db', str(db)]
            inventory = {'jsonrpc':'2.0','id':0,'method':'tools/list'}
            first = subprocess.run(observer, input=json.dumps(inventory)+'\n',
                text=True, capture_output=True, timeout=10, check=True)
            self.assertEqual(len(json.loads(first.stdout)['result']['tools']), 3)
            result = subprocess.run(observer, input=''.join(json.dumps(r)+'\n' for r in requests),
                                    text=True, capture_output=True, timeout=10, check=True)
            self.assertEqual(len(result.stdout.splitlines()), 3)
            probe.verify_handler_effects(root)
            original = (root / 'handler.jsonl').read_text()
            altered = [json.loads(line) for line in original.splitlines()]
            altered[1]['arguments']['operation_id'] = 'different'
            (root / 'handler.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in altered))
            with self.assertRaises(RuntimeError): probe.verify_handler_effects(root)
            (root / 'handler.jsonl').write_text(original)
            with probe.sqlite3.connect(db) as conn:
                conn.execute('UPDATE drafts SET envelope=?', ('{}',))
            with self.assertRaises(RuntimeError): probe.verify_handler_effects(root)

    def test_public_summary_cannot_echo_arbitrary_diagnostics(self):
        secret = 'SYNTHETIC-DO-NOT-ECHO'
        script = probe.Script(); script.requests = [{'input':[
            {'type':'function_call_output','output':secret}, {'type':secret,'text':secret}]}]
        script.errors = [secret]; script.contacts = [secret]
        summary = probe.diagnostic_summary(secret, False, script)
        self.assertNotIn(secret, json.dumps(summary))
        self.assertEqual(summary['stage'], 'preflight')
        self.assertEqual(summary['output_types']['function_call_output'], 1)
        output = io.StringIO()
        with patch.object(probe, '_execute', side_effect=RuntimeError(secret)), \
                contextlib.redirect_stdout(output):
            self.assertEqual(probe.execute('/unused', ROOT, ROOT, True), 1)
        self.assertNotIn(secret, output.getvalue())
        self.assertEqual(json.loads(output.getvalue())['reason'], 'stage-failed')
        script.requests *= 100
        self.assertEqual(probe.diagnostic_summary('effects',False,script)['requests'],12)

    def test_sqlite_uri_special_characters_and_private_evidence_directory(self):
        with tempfile.TemporaryDirectory(prefix='synthetic-?#-') as tmp:
            root = Path(tmp)
            store = self.service.PublicationStore(str(root / 'ledger.sqlite'), True)
            try:
                self.assertEqual(probe.ledger(root), {'drafts':0,'reviews':0,'releases':0})
            finally:
                store.close()
            out = root / 'evidence'
            original_exists = Path.exists
            old_umask = os.umask(0o022)
            try:
                with patch.object(probe, 'check_host'), patch.object(probe.os, 'geteuid', return_value=1000), \
                        patch.object(Path, 'exists', lambda p: False if str(p) == '/etc/codex' else original_exists(p)), \
                        patch.object(probe, 'resolve_bootstrap', side_effect=RuntimeError('stop-before-runtime')), \
                        contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(probe.execute('/unused',ROOT,out,True),1)
                self.assertEqual(out.stat().st_mode & 0o777, 0o700)
                self.assertFalse((out / 'result.json').exists())
            finally:
                os.umask(old_umask)

    def test_header_timeout_precedes_stream_creation(self):
        handler = probe.Handler.__new__(probe.Handler)
        handler.request = MagicMock()
        handler.setup()
        calls = handler.request.mock_calls
        self.assertEqual(calls[0][0], 'settimeout')
        self.assertEqual(calls[0][1], (10,))
        self.assertEqual(calls[1][0], 'makefile')

    def test_cleanup_failure_cannot_leave_success_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            def failed_cleanup(codex, package, evidence, opt_in, progress):
                progress['result'] = {'status':'canned-protocol-compatible'}
                progress['evidence'] = evidence
                raise OSError('synthetic cleanup failure')
            with patch.object(probe, '_execute', side_effect=failed_cleanup), \
                    contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(probe.execute('/unused',ROOT,out,True),1)
            self.assertFalse((out / 'result.json').exists())
            self.assertTrue((out / 'failure.json').exists())
            self.assertEqual(probe.diagnostic_summary('effects',False)['raw_trace_retention'],
                             'local-files-not-uploaded')

    def test_cloud_host_refusal_precedes_all_processes_and_writes(self):
        with patch.object(probe, 'check_host', side_effect=RuntimeError('refused')), \
                patch.object(probe.subprocess, 'run') as run, patch.object(probe.subprocess, 'Popen') as popen:
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(probe.execute('/abs/codex', ROOT, Path('/tmp/not-created-protocol'), True), 1)
            run.assert_not_called(); popen.assert_not_called()




class RepairTests(unittest.TestCase):
    def test_discovery_rejects_hidden_extra_entries_and_boolean_number_alias(self):
        fixture = ProtocolTests(); fixture.setUp()
        for extra in [{}, {'type':'unknown'}, {'type':'namespace','name':'foreign','tools':[]},
                      {'type':'namespace','name':'mcp__delivery_publication','tools':[]}]:
            bad = copy.deepcopy(fixture.result); bad['tools'].append(extra)
            with self.subTest(extra=extra), self.assertRaises(probe.ProbeFailure):
                probe.discovered_tools(bad, fixture.expected)
        bad = copy.deepcopy(fixture.result)
        bad['tools'][0]['tools'][0]['parameters']['additionalProperties'] = 0
        with self.assertRaises(probe.ProbeFailure) as caught:
            probe.discovered_tools(bad, fixture.expected)
        self.assertEqual(caught.exception.code, 'discovery-parameters')

    def test_rpc_queue_and_retention_fail_on_capacity(self):
        rpc = probe.RPC.__new__(probe.RPC)
        rpc.inbox = queue.Queue(maxsize=1); rpc.overflow = threading.Event()
        rpc.inbox_bytes = 0; rpc.inbox_lock = threading.Lock()
        rpc.process = MagicMock(); rpc.process.stdout = io.StringIO('{}\n{}\n')
        rpc._read()
        self.assertTrue(rpc.overflow.is_set())
        with self.assertRaises(probe.ProbeFailure) as caught:
            rpc.receive(0)
        self.assertEqual(caught.exception.code, 'rpc-capacity')
        rpc.log = []; rpc.log_bytes = probe.MAX_RPC_BYTES
        with self.assertRaises(probe.ProbeFailure): rpc.retain({'received':{}})
        self.assertEqual(rpc.log, [])
        rpc.log_bytes = 0; rpc.log = [{}] * probe.MAX_RPC_ITEMS
        with self.assertRaises(probe.ProbeFailure): rpc.retain({})
        rpc.inbox = queue.Queue(); rpc.overflow.clear(); rpc.inbox_bytes = probe.MAX_RPC_BYTES
        rpc.process.stdout = io.StringIO('{}\n')
        rpc._read()
        self.assertTrue(rpc.overflow.is_set())

    def test_consumer_refusal_is_structured_and_saved_before_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            for result in [subprocess.CompletedProcess([],2,'','usage: unknown argument'),
                           subprocess.CompletedProcess([],0,'','{"status":"unavailable"}'),
                           subprocess.CompletedProcess([],2,'bundle','{"status":"unavailable"}')]:
                with self.assertRaises(probe.ProbeFailure): probe.verify_consumer(result, out)
                self.assertEqual(json.loads((out / 'consumer.json').read_text())['stderr'],result.stderr)
            probe.verify_consumer(subprocess.CompletedProcess([],2,'','{"status":"unavailable"}\n'),out)

    def test_ledger_snapshot_survives_source_removal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); out = root / 'evidence'; out.mkdir()
            with probe.sqlite3.connect(root / 'ledger.sqlite') as db:
                db.execute('CREATE TABLE sample(value TEXT)')
                db.execute("INSERT INTO sample VALUES ('synthetic')")
                probe.snapshot_ledger(root, out)
            with probe.sqlite3.connect(out / 'ledger.sqlite') as db:
                # Snapshot is consistent and does not include an uncommitted transaction.
                self.assertEqual(db.execute('SELECT * FROM sample').fetchall(), [])
            probe.snapshot_ledger(root, out)
            (root / 'ledger.sqlite').unlink()
            with probe.sqlite3.connect(out / 'ledger.sqlite') as db:
                self.assertEqual(db.execute('SELECT * FROM sample').fetchall(), [('synthetic',)])


class NativeFailureTests(unittest.TestCase):
    def test_native_failure_classes_never_accept_or_echo_error_text(self):
        secret = 'SYNTHETIC-PRIVATE-TEXT'
        cases = [
            ('MCP tool call requires approval, but approval policy is never', 'result-approval-required'),
            ('user cancelled MCP tool call', 'result-cancelled'),
            ('tool call error: ' + secret, 'result-tool-call-error'),
            ('err: ' + secret, 'result-argument-error'), (secret, 'result-json')]
        cases += [('MCP tool `delivery_publication/' + name + '` is not available to the model',
                   'result-tool-unavailable') for name in probe.TOOLS]
        for text, reason in cases:
            output = {'type':'function_call_output','output':[
                {'type':'input_text','text':'Wall time: 0.0010 seconds\nOutput:'},
                {'type':'input_text','text':text}]}
            with self.subTest(reason=reason), self.assertRaises(probe.ProbeFailure) as caught:
                probe.result_status(output, 'submitted')
            self.assertEqual(caught.exception.code, reason)
            summary = probe.diagnostic_summary('submit', False, reason=caught.exception.code)
            self.assertNotIn(secret, json.dumps(summary))
        output['output'][1]['text'] = json.dumps({'status':'submitted'})
        probe.result_status(output, 'submitted')
        with self.assertRaises(probe.ProbeFailure): probe.result_status(output, 'blocked')


if __name__ == '__main__':
    unittest.main()
