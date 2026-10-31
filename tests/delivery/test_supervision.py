import json
import fcntl
from pathlib import Path
import sys
import tempfile
import subprocess
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'plugins/delivery/scripts'))
import runtime as R
import supervision as S
from delivery_gates import GateService
from test_runtime import FakeRPC
from test_delivery_gates import CanonicalBeads


class SupervisionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.project = Path(self.temp.name).resolve()
        (self.project/'.delivery').mkdir()
        self.store = R.Store(self.project)
        spec = {'cwd':str(self.project), 'model':'test-model', 'lane':'read-only', 'instructions':'Synthetic executor'}
        self.store.db.execute("INSERT INTO roles VALUES('coordinator',?,NULL,NULL,'prepared',NULL)", (json.dumps(spec),))
        self.binding = {'principal':'dot-proof', 'environment':'synthetic', 'tasks':{'task-1':'proof'}}
        with self.store.transaction():
            S.configure(self.store, self.binding)
        self.beads = CanonicalBeads()
        self.patch = patch('supervision.GateService', side_effect=lambda store, beads=None: GateService(store, beads or self.beads))
        self.patch.start()
        self.bridge = self.connect()
        self.coordinator = R.Coordinator(self.store, FakeRPC)

    def connect(self):
        return S.Bridge(self.store, authenticated_principal='dot-proof', environment='synthetic')

    def request(self, **changes):
        state = self.bridge.snapshot('task-1')
        return dict(request_id='request-1', task='task-1', initiative='proof', recipient='coordinator',
                    message='Report synthetic task evidence; no acceptance.',
                    expected_revision=state['expected_revision'], task_revision=state['task_revision'], **changes)

    def tearDown(self):
        self.patch.stop()
        self.store.db.close()
        self.temp.cleanup()

    def test_admission_restart_duplicate_completion_receipt(self):
        request = self.request()
        admitted = self.bridge.submit(request)
        self.store.db.close()
        self.store = R.Store(self.project)
        self.bridge = self.connect()
        self.coordinator = R.Coordinator(self.store, FakeRPC)
        self.coordinator.reconcile()
        self.assertEqual(self.bridge.submit(request)['assignment_id'], admitted['assignment_id'])
        self.coordinator.step()
        text = self.coordinator.rpc.calls[-1][1]['input'][0]['text']
        self.assertIn('agent:dot-proof', text)
        self.assertIn('"task": "task-1"', text)
        self.assertIn('"initiative": "proof"', text)
        self.assertNotIn('Operator-assigned', text)
        self.store.event('controlled_tool_result', {'thread':'native-thread', 'turn':'native-turn','artifact':'synthetic'})
        self.coordinator.receive({'method':'item/completed','params':{'threadId':'native-thread','turnId':'native-turn',
            'item':{'type':'agentMessage','text':'Synthetic completion report'}}})
        self.coordinator.receive({'method':'turn/completed','params':{'threadId':'native-thread','turn':{'id':'native-turn','status':'completed'}}})
        receipt = self.bridge.receipt('request-1')
        self.assertEqual((receipt['state'], receipt['thread'], receipt['turn']), ('idle','native-thread','native-turn'))
        self.assertIsNotNone(receipt['terminal_event'])
        self.assertIn('controlled_tool_result', [e['kind'] for e in receipt['evidence']])
        self.assertIn('item/completed', [e['kind'] for e in receipt['evidence']])
        self.assertFalse(receipt['accepted'])
        self.assertEqual(self.bridge.submit(request), receipt)
        self.assertEqual(sum(m == 'turn/start' for m, _ in self.coordinator.rpc.calls), 1)

    def test_conflicting_key_stale_runtime_scope_and_actor_fields_are_refused(self):
        request = self.request()
        self.bridge.submit(request)
        with self.assertRaisesRegex(S.SupervisionError, 'different payload'):
            self.bridge.submit({**request,'message':'changed'})
        with self.assertRaisesRegex(S.SupervisionError, 'Stale runtime'):
            self.bridge.submit({**request,'request_id':'new-request'})
        for changes in ({'recipient':'unknown'}, {'task':'outside'}, {'initiative':'other'}, {'actor':'operator'}, {'accept':True}):
            with self.subTest(changes=changes), self.assertRaises(S.SupervisionError):
                self.bridge.submit({**self.request(), **changes, 'request_id':'new-request'})
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM queue').fetchone()[0], 1)

    def test_host_identity_environment_and_disabled_binding_refuse(self):
        for principal, env in [('other','synthetic'), ('dot-proof','other')]:
            with self.assertRaises(S.SupervisionError):
                S.Bridge(self.store, authenticated_principal=principal, environment=env)
        with self.store.transaction(), self.assertRaises(S.SupervisionError):
            S.configure(self.store, {**self.binding, 'principal':'second-chief'})
        S.fallback(self.store, 'Operator explicitly returns supervision to native')
        with self.assertRaises(S.SupervisionError):
            self.bridge.submit(self.request())

    def test_task_change_before_admission_or_dispatch_cannot_run(self):
        request = self.request()
        self.beads.tasks['task-1']['acceptance_criteria'] = 'changed'
        with self.assertRaisesRegex(S.SupervisionError, 'Stale canonical'):
            self.bridge.submit(request)
        self.bridge.submit(self.request())
        self.beads.tasks['task-1']['acceptance_criteria'] = 'changed again'
        self.coordinator.step()
        self.assertFalse(self.coordinator.rpc.calls)
        self.assertEqual(self.bridge.receipt('request-1')['state'], 'blocked')
        with self.assertRaises(S.SupervisionError):
            S.fallback(self.store, 'not yet reconciled')
        S.cancel(self.store, 'request-1', 'Discard stale undispatched request')
        S.fallback(self.store, 'Reconciled cancelled request')
        self.assertIsNone(S.configuration(self.store))

    def test_unknown_effect_restart_does_not_replay_or_borrow_a_previous_terminal(self):
        request = self.request()
        self.bridge.submit(request)
        self.coordinator.rpc.fail_turn = True
        self.coordinator.step()
        self.coordinator.reconcile()
        self.bridge.submit(request)
        self.coordinator.step()
        self.assertEqual(sum(m == 'turn/start' for m, _ in self.coordinator.rpc.calls), 1)
        self.assertEqual(self.bridge.receipt('request-1')['role_phase'], 'needs-reconciliation')
        self.assertIsNone(self.bridge.receipt('request-1')['terminal_event'])
        with self.assertRaises(S.SupervisionError):
            S.cancel(self.store, 'request-1', 'cannot cancel unknown effect')
        self.store.control('coordinator','native-thread','native-turn','recover')
        self.coordinator.step()
        receipt = self.bridge.receipt('request-1')
        self.assertEqual((receipt['state'],receipt['turn']), ('unknown',None))
        self.assertIsNone(receipt['terminal_event'])

    def test_worker_disconnect_does_not_trigger_takeover_or_completion(self):
        self.bridge.submit(self.request())
        self.coordinator.step()
        self.coordinator.reconcile()
        self.coordinator.step()
        self.assertEqual(sum(m == 'turn/start' for m, _ in self.coordinator.rpc.calls), 1)
        self.assertEqual(self.bridge.receipt('request-1')['role_phase'], 'needs-reconciliation')
        self.assertIsNotNone(S.configuration(self.store))
        with self.assertRaises(S.SupervisionError):
            S.fallback(self.store, 'Silence is not reconciliation')

    def test_stale_terminal_event_is_not_a_completion_receipt(self):
        self.bridge.submit(self.request())
        self.coordinator.step()
        self.coordinator.receive({'method':'turn/completed','params':{'threadId':'native-thread','turn':{'id':'old-turn','status':'completed'}}})
        self.assertIsNone(self.bridge.receipt('request-1')['terminal_event'])

    def test_failed_assignment_has_exact_terminal_outcome_after_reconciliation(self):
        self.bridge.submit(self.request())
        self.coordinator.step()
        self.coordinator.receive({'method':'turn/completed','params':{'threadId':'native-thread','turn':{'id':'native-turn','status':'failed'}}})
        original = self.coordinator.rpc.call
        self.coordinator.rpc.call = lambda method, params: ({'thread':{'id':'native-thread','turns':[{'id':'native-turn','status':'failed'}]}}
            if method == 'thread/read' else original(method, params))
        self.store.control('coordinator','native-thread','native-turn','recover')
        self.coordinator.step()
        receipt = self.bridge.receipt('request-1')
        self.assertEqual(receipt['state'], 'failed')
        self.assertIsNotNone(receipt['terminal_event'])
        self.assertFalse(receipt['accepted'])
        S.fallback(self.store, 'Failure reconciled; no retry')

    def test_new_binding_cannot_revive_old_bridge_or_read_prior_receipts(self):
        request = self.request()
        self.bridge.submit(request)
        S.cancel(self.store,'request-1','Undispatched cancellation')
        S.fallback(self.store,'Return to native')
        with self.store.transaction():
            S.configure(self.store, self.binding)
        with self.assertRaises(S.SupervisionError):
            self.bridge.receipt('request-1')
        bridge = self.connect()
        with self.assertRaises(S.SupervisionError):
            bridge.receipt('request-1')
        with self.assertRaises(S.SupervisionError):
            bridge.submit(request)

    def test_handover_refuses_queued_native_work(self):
        S.fallback(self.store,'Native work next')
        self.store.enqueue('coordinator','Unfinished native work')
        with self.store.transaction(), self.assertRaises(S.SupervisionError):
            S.configure(self.store, self.binding)

    def test_serve_prepare_and_fallback_cannot_compete_with_dispatch_owner(self):
        with (self.store.root/'serve.lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX | fcntl.LOCK_NB)
            for command in (['serve'], ['prepare','--roster','/not-read'], ['supervision-native','--reason','competing chief']):
                result = subprocess.run([sys.executable,str(R.__file__),'--project',str(self.project),*command],
                    capture_output=True,text=True,timeout=10)
                self.assertEqual(result.returncode,2,result.stdout+result.stderr)
                self.assertTrue('coordinator' in json.loads(result.stderr)['error'].lower())

    def test_prequeued_work_cannot_dispatch_past_unknown_outcome(self):
        self.bridge.submit(self.request())
        self.bridge.submit({**self.request(), 'request_id':'request-2'})
        self.coordinator.rpc.fail_turn = True
        self.coordinator.step()
        self.store.control('coordinator','native-thread','native-turn','recover')
        self.coordinator.step()
        self.assertEqual(self.bridge.receipt('request-1')['state'],'unknown')
        self.assertEqual(self.bridge.receipt('request-2')['state'],'blocked')
        self.assertEqual(sum(m == 'turn/start' for m, _ in self.coordinator.rpc.calls), 1)


if __name__ == '__main__':
    unittest.main()
