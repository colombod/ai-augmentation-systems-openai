import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import tomllib
import unittest
from unittest.mock import patch

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
                def finish_turn(self):
                    pass
            with self.subTest(outputs=outputs), self.assertRaises(RuntimeError):
                probe.run_case(FakeRPC(), script, 'thread', probe.call_item('synthetic', {}, 'one'))

    def test_cloud_host_refusal_precedes_all_processes_and_writes(self):
        with patch.object(probe, 'check_host', side_effect=RuntimeError('refused')), \
                patch.object(probe.subprocess, 'run') as run, patch.object(probe.subprocess, 'Popen') as popen:
            with self.assertRaises(RuntimeError): probe.execute('/abs/codex', ROOT, Path('/tmp/not-created-protocol'), True)
            run.assert_not_called(); popen.assert_not_called()


if __name__ == '__main__':
    unittest.main()
