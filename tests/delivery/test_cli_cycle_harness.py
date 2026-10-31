"""Adversarial evidence-driver tests. No Codex process or model is launched."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[2]/'scripts'
sys.path.insert(0, str(SCRIPTS))
from cli_cycle_harness import (HarnessFailure, message_completion, peer_handoff,
                               successful_tool, answered_judge, judge_fixture, new_attempt, planned_stop)


def event(ident, kind, data):
    return {'id': ident, 'kind': kind, 'data': data}


def user(ident, role, message, thread='persistent-thread', turn='new-turn'):
    return event(ident, 'item/completed', {'role': role, 'native': {'threadId': thread, 'turnId': turn,
                 'item': {'type': 'userMessage', 'content': [{'type': 'text', 'text':
                    '[Operator-assigned work; queued message '+message+']\nWork request'}]}}})


def terminal(ident, role, thread='persistent-thread', turn='new-turn', status='completed'):
    return event(ident, 'turn_terminal', {'role': role, 'native': {'threadId': thread,
                 'turn': {'id': turn, 'status': status}}})


def tool(ident, name, value, role='manager', thread='persistent-thread', turn='new-turn', success=True):
    return event(ident, 'controlled_tool_result', {'role': role, 'thread': thread, 'turn': turn,
                 'tool': name, 'result': {'success': success, 'contentItems': [
                    {'type': 'inputText', 'text': json.dumps(value)}]}})


class HarnessTests(unittest.TestCase):
    def setUp(self):
        self.roles = [{'name': 'manager', 'phase': 'idle', 'thread': 'persistent-thread'}]
        self.queues = [{'id': 'current-message', 'role': 'manager', 'state': 'idle', 'source': 'operator'}]
        self.events = [event(2, 'turn_intent', {'role': 'manager', 'message_id': 'current-message'}),
                       user(3, 'manager', 'current-message'), terminal(5, 'manager')]
        self.proof = message_completion(self.roles, self.queues, self.events, 'manager', 'current-message')

    def test_idle_old_thread_does_not_complete_new_queued_work(self):
        self.queues[0]['state'] = 'queued'
        old = [user(1, 'manager', 'previous-message', turn='old-turn'), terminal(2, 'manager', turn='old-turn')]
        self.assertIsNone(message_completion(self.roles, self.queues, old, 'manager', 'current-message'))
        self.assertIsNotNone(message_completion(self.roles, [dict(self.queues[0], state='idle')], self.events,
                                               'manager', 'current-message'))

    def test_first_terminal_from_previous_turn_cannot_mask_missing_or_failed_new_terminal(self):
        mixed = self.events[:2]+[terminal(4, 'manager', turn='old-turn')]
        self.assertIsNone(message_completion(self.roles, self.queues, mixed, 'manager', 'current-message'))
        with self.assertRaisesRegex(HarnessFailure, 'did not complete'):
            message_completion(self.roles, self.queues, mixed+[terminal(5, 'manager', status='failed')],
                               'manager', 'current-message')
        result = message_completion(self.roles, self.queues, mixed+[terminal(6, 'manager')],
                                    'manager', 'current-message')
        self.assertEqual(result['terminal_event'], 6)

    def test_wrong_thread_terminal_or_quoted_queue_marker_never_completes(self):
        wrong = self.events[:2]+[terminal(5, 'manager', thread='unrelated-thread')]
        self.assertIsNone(message_completion(self.roles, self.queues, wrong, 'manager', 'current-message'))
        quoted = copy.deepcopy(self.events)
        quoted[1]['data']['native']['item']['content'][0]['text'] = 'Quoted old instructions: '+quoted[1]['data']['native']['item']['content'][0]['text']
        self.assertIsNone(message_completion(self.roles, self.queues, quoted, 'manager', 'current-message'))

    def test_same_queue_replayed_in_two_native_turns_is_ambiguous(self):
        with self.assertRaisesRegex(HarnessFailure, 'multiple native turns'):
            message_completion(self.roles, self.queues, self.events+[user(8, 'manager', 'current-message', turn='replayed')],
                               'manager', 'current-message')

    def test_failed_queue_or_changed_bound_thread_fails_closed(self):
        with self.assertRaisesRegex(HarnessFailure, 'failed or requires'):
            message_completion(self.roles, [dict(self.queues[0], state='unknown')], self.events, 'manager', 'current-message')
        with self.assertRaisesRegex(HarnessFailure, 'another native thread'):
            message_completion([dict(self.roles[0], thread='replacement-thread')], self.queues, self.events, 'manager', 'current-message')

    def test_required_peer_handoff_is_bound_to_current_sender_turn_and_actual_recipient(self):
        messages = [user(2, 'coordinator', 'operator-task'),
                    tool(3, 'delivery_send', {'queued_message_id': 'peer-task'}, role='coordinator', turn='old-turn')]
        queues = [{'id': 'peer-task', 'role': 'product-manager', 'source': 'peer:coordinator'}]
        self.assertIsNone(peer_handoff(queues, messages, 'coordinator', 'operator-task', 'product-manager'))
        with self.assertRaisesRegex(HarnessFailure, 'never handed off'):
            peer_handoff(queues, messages, 'coordinator', 'operator-task', 'product-manager', sender_complete=True)
        messages.append(tool(4, 'delivery_send', {'queued_message_id': 'peer-task'}, role='coordinator'))
        self.assertEqual(peer_handoff(queues, messages, 'coordinator', 'operator-task', 'product-manager', True), 'peer-task')
        with self.assertRaisesRegex(HarnessFailure, 'never handed off'):
            peer_handoff([dict(queues[0], role='reviewer')], messages, 'coordinator', 'operator-task', 'product-manager', True)

    def test_prior_stage_tool_success_does_not_satisfy_current_role_turn(self):
        old = tool(6, 'delivery_task_gate_status', {'accepted': True}, turn='old-turn')
        with self.assertRaisesRegex(HarnessFailure, 'exact-turn'):
            successful_tool(self.events+[old], 'delivery_task_gate_status', self.proof)
        current = tool(7, 'delivery_task_gate_status', {'accepted': False})
        self.assertFalse(successful_tool(self.events+[old,current], 'delivery_task_gate_status', self.proof)['accepted'])

    def test_judge_tool_success_with_skip_error_or_wrong_provider_is_not_a_provider_answer(self):
        good = {'question': 'is_fix', 'type': 'noul', 'answer': 'no', 'p': 0,
                'provider': 'openai', 'model': 'gpt-6-luna', 'advisory': True, 'human_authority': False}
        for changes in ({'skipped': True}, {'error': True}, {'provider': 'jev'}, {'answer': 'maybe'}, {'human_authority': True}, {'p': float('nan')}):
            with self.subTest(changes=changes), self.assertRaises(HarnessFailure):
                answered_judge(self.events+[tool(6,'delivery_judge',dict(good,**changes))], self.proof, 'openai','gpt-6-luna')
        self.assertEqual(answered_judge(self.events+[tool(6,'delivery_judge',good)], self.proof,'openai','gpt-6-luna')['answer'], 'no')
        with self.assertRaisesRegex(HarnessFailure, 'corrective retries'):
            answered_judge(self.events+[tool(6,'delivery_judge',dict(good,skipped=True)),tool(7,'delivery_judge',good)], self.proof,'openai','gpt-6-luna')

    def test_judge_fixture_is_checked_against_real_catalogue_not_invented_fields(self):
        catalogue = SCRIPTS.parent/'plugins/delivery/judge/questions.json'
        state = judge_fixture(catalogue)
        self.assertEqual(set(state), {'candidate','linked_item','context'})
        with tempfile.TemporaryDirectory() as tmp:
            altered = Path(tmp)/'catalogue.json'
            altered.write_text(json.dumps({'questions': {'is_fix': {'state': ['candidate','new-required-field']}}}))
            with self.assertRaisesRegex(HarnessFailure, 'actual is_fix catalogue'):
                judge_fixture(altered)

    def test_attempts_are_unique_and_do_not_replace_existing_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); original=root/'result.json'; original.write_text('prior failed observation')
            first, second = new_attempt(root), new_attempt(root)
            (first/'result.json').write_text('first attempt')
            self.assertNotEqual(first,second)
            self.assertEqual(original.read_text(),'prior failed observation')
            self.assertEqual((first/'result.json').read_text(),'first attempt')
            self.assertFalse((second/'result.json').exists())

    def child(self, ignore_interrupt=False):
        code=('import signal,time,sys;signal.signal(signal.SIGINT,signal.SIG_IGN);print("ready",flush=True);time.sleep(60)' if ignore_interrupt else
              'import signal,time,sys;signal.signal(signal.SIGINT,lambda *_:sys.exit(0));print("ready",flush=True);time.sleep(60)')
        process=subprocess.Popen([sys.executable,'-c',code],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        self.assertEqual(process.stdout.readline().strip(),'ready')
        self.addCleanup(process.stdout.close);self.addCleanup(process.stderr.close)
        def cleanup():
            if process.poll() is None:
                process.kill();process.wait()
        self.addCleanup(cleanup)
        return process

    def test_planned_supervisor_stop_rejects_prior_crash_and_forced_cleanup(self):
        crashed=subprocess.Popen([sys.executable,'-c','raise SystemExit(7)'])
        crashed.wait(timeout=3)
        with self.assertRaisesRegex(HarnessFailure,'before planned stop'):
            planned_stop(crashed)
        normal=self.child()
        result=planned_stop(normal,timeout=2)
        self.assertEqual(result['signal_requested'],'SIGINT')
        self.assertEqual(result['exit_code'],0)
        stubborn=self.child(ignore_interrupt=True)
        with self.assertRaisesRegex(HarnessFailure,'forced cleanup'):
            planned_stop(stubborn,timeout=0.05)
        self.assertIsNotNone(stubborn.poll())

    def test_real_process_exit_code_requires_all_semantic_checks_and_no_cleanup_error(self):
        script = 'import sys,json;sys.path.insert(0,sys.argv[1]);from cli_cycle_harness import exit_code;sys.exit(exit_code(json.load(sys.stdin)))'
        good={'stage':'finished-through-human-barrier','checks':{'actual_queue_completed':True,'honest_refusal':True}}
        for value,expected in [(good,0),(dict(good,checks={'actual_queue_completed':False}),1),
                               (dict(good,checks={}),1),(dict(good,error='actual provider error'),1),
                               (dict(good,snapshot_error='missing evidence'),1),(dict(good,cleanup_error='supervisor alive'),1),
                               (dict(good,stage='failed'),1)]:
            process=subprocess.run([sys.executable,'-c',script,str(SCRIPTS)],input=json.dumps(value),text=True,capture_output=True)
            self.assertEqual(process.returncode,expected,process.stderr)


if __name__=='__main__':
    unittest.main()
