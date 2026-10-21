import importlib.util
import json
from pathlib import Path
import select
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[2] / 'plugins/delivery/scripts'
sys.path.insert(0, str(SCRIPTS))
import runtime as R


class FakeRPC:
    def __init__(self, cwd, receive):
        self.cwd = cwd
        self.receive = receive
        self.calls = []
        self.sent = []
        self.bad_lane = False
        self.fail_turn = False
        self.fast_finish = False

    def call(self, method, params):
        self.calls.append((method, params))
        if method in ('thread/start', 'thread/resume'):
            return {'thread': {'id': 'native-thread'}, 'sandbox': {'type': 'workspaceWrite' if self.bad_lane else 'readOnly','networkAccess':False}, 'model':'test-model', 'cwd':self.cwd,'approvalPolicy':'on-request','approvalsReviewer':'user'}
        if method == 'turn/start':
            if self.fail_turn:
                raise R.ProtocolError('rpc_timeout:turn/start')
            if self.fast_finish:
                self.receive({'method': 'turn/completed', 'params': {'threadId': 'native-thread', 'turn': {'id': 'native-turn', 'status': 'completed'}}})
            return {'turn': {'id': 'native-turn'}}
        if method in ('turn/interrupt', 'turn/steer'):
            return {}
        if method == 'thread/read':
            return {'thread':{'id':'native-thread','turns':[{'id':'native-turn','status':'completed'}]}}
        raise AssertionError(method)

    def send(self, message):
        self.sent.append(message)


class RuntimeTests(unittest.TestCase):
    def test_public_entrypoint_sigint_is_clean_and_closes_adapter(self):
        # Exercise the actual executable entrypoint and serve finally block;
        # only the native transport is stubbed, with no roles or model calls.
        launcher = self.project / 'entrypoint.py'
        cleanup = self.project / 'adapter-closed'
        launcher.write_text('''import runpy, sys, time
from pathlib import Path
sys.path.insert(0, sys.argv.pop(1))
import codex_rpc
class IdleRPC:
    def __init__(self, cwd, receive): pass
    def dispatch(self, timeout):
        print('IDLE_READY', flush=True)
        time.sleep(timeout)
    def close(self): Path(sys.argv.pop()).write_text('closed')
codex_rpc.CodexRPC = IdleRPC
runpy.run_path(sys.argv.pop(1), run_name='__main__')
''')
        # Keep cleanup out of argv while argparse processes the real CLI args.
        launcher.write_text(launcher.read_text().replace("Path(sys.argv.pop()).write_text('closed')", f"Path({str(cleanup)!r}).write_text('closed')"))
        process = subprocess.Popen([sys.executable, str(launcher), str(SCRIPTS), str(SCRIPTS/'runtime.py'), '--project', str(self.project), 'serve'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            readable, _, _ = select.select([process.stdout], [], [], 10)
            self.assertTrue(readable, 'serve never reached its idle dispatch loop')
            self.assertEqual(process.stdout.readline().strip(), 'IDLE_READY')
            process.send_signal(signal.SIGINT)
            _, stderr = process.communicate(timeout=10)
            self.assertEqual(process.returncode, 0, stderr)
            self.assertEqual(json.loads(stderr), {'status':'interrupted'})
            self.assertEqual(cleanup.read_text(), 'closed')
            self.assertEqual(self.store.status()['roles'][0]['phase'], 'prepared')
        finally:
            if process.poll() is None:
                process.kill()
                process.communicate()

    def test_public_entrypoint_operational_failure_still_exits_two(self):
        with tempfile.TemporaryDirectory() as missing:
            result = subprocess.run([sys.executable, str(SCRIPTS/'runtime.py'), '--project', str(Path(missing).resolve()), 'status'], capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 2)
            self.assertIn('Initialize the delivery workspace first', json.loads(result.stderr)['error'])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.project = Path(self.temp.name).resolve()
        (self.project/'.delivery').mkdir()
        self.store = R.Store(self.project)
        self.spec = {'cwd': str(self.project), 'model': 'test-model', 'lane': 'read-only', 'instructions': 'Bounded synthetic role'}
        self.store.db.execute("INSERT INTO roles VALUES('coordinator',?,NULL,NULL,'prepared',NULL)", (json.dumps(self.spec),))
        self.coordinator = R.Coordinator(self.store, FakeRPC)

    def tearDown(self):
        self.store.db.close()
        self.temp.cleanup()

    def active(self):
        self.store.enqueue('coordinator', 'Synthetic task')
        self.coordinator.step()

    def test_completed_turn_is_distinct_from_started_and_unknown_events(self):
        self.active()
        self.assertEqual(self.store.status()['roles'][0]['phase'], 'active')
        self.coordinator.receive({'method':'turn/completed','params':{'threadId':'peer-thread','turn':{'id':'native-turn','status':'completed'}}})
        self.assertEqual(self.store.status()['roles'][0]['phase'], 'active')
        self.coordinator.receive({'method':'turn/completed','params':{'threadId':'native-thread','turn':{'id':'stale-turn','status':'completed'}}})
        self.assertEqual(self.store.status()['roles'][0]['phase'], 'active')
        self.coordinator.receive({'method':'turn/completed','params':{'threadId':'native-thread','turn':{'id':'native-turn','status':'failed'}}})
        self.assertEqual(self.store.status()['roles'][0]['phase'], 'needs-reconciliation')

    def test_crash_recovery_resumes_binding_without_replaying_external_effects(self):
        self.active()
        self.coordinator.reconcile()
        self.assertEqual(self.store.status()['roles'][0]['phase'], 'needs-reconciliation')
        before = len(self.coordinator.rpc.calls)
        self.coordinator.step()
        self.assertEqual(len(self.coordinator.rpc.calls), before)
        self.assertEqual(self.coordinator.rpc.calls[-1][0], 'thread/resume')

    def test_unknown_effect_on_rpc_timeout_is_not_retried(self):
        self.coordinator.rpc.fail_turn = True
        self.active()
        self.coordinator.step()
        self.assertEqual(sum(m=='turn/start' for m,p in self.coordinator.rpc.calls),1)
        self.assertEqual(self.store.status()['roles'][0]['phase'], 'needs-reconciliation')

    def test_native_lane_mismatch_refuses_turn(self):
        self.coordinator.rpc.bad_lane = True
        self.active()
        self.assertFalse(any(m=='turn/start' for m,p in self.coordinator.rpc.calls))
        self.assertEqual(self.store.status()['roles'][0]['phase'], 'needs-reconciliation')

    def test_fast_terminal_notification_before_rpc_reply_is_not_lost(self):
        self.coordinator.rpc.fast_finish = True
        self.active()
        self.assertEqual(self.store.status()['roles'][0]['phase'], 'idle')

    def test_native_request_expiry_disconnect_and_unbound_identity_grant_nothing(self):
        self.active()
        msg={'id':19,'method':'item/tool/requestUserInput','params':{'threadId':'native-thread','turnId':'native-turn','itemId':'item1'}}
        self.coordinator.receive(msg)
        row=self.store.db.execute('SELECT * FROM pending').fetchone()
        self.assertEqual(row['state'],'pending')
        self.store.db.execute('UPDATE pending SET expires=?',(time.time()-1,))
        self.coordinator.step()
        self.assertIn('error',self.coordinator.rpc.sent[-1])
        self.coordinator.receive({**msg,'id':20,'params':{**msg['params'],'threadId':'spoofed'}})
        self.assertEqual(self.coordinator.rpc.sent[-1]['error']['message'],'Unbound request')
        self.coordinator.receive({**msg,'id':21})
        self.coordinator.reconcile()
        self.assertEqual(self.store.db.execute('SELECT state FROM pending WHERE native_id=?',('21',)).fetchone()[0],'disconnected')

    def test_only_bound_unexpired_answer_is_consumed_once(self):
        self.active()
        self.coordinator.receive({'id':4,'method':'item/tool/requestUserInput','params':{'threadId':'native-thread','turnId':'native-turn'}})
        self.store.db.execute("UPDATE pending SET state='answered',answer=?",(json.dumps({'answers':{'q':{'answers':['Continue with draft']}}}),))
        self.coordinator.step();count=len(self.coordinator.rpc.sent);self.coordinator.step()
        self.assertEqual(len(self.coordinator.rpc.sent),count)
        self.assertEqual(self.coordinator.rpc.sent[-1]['result'],{'answers':{'q':{'answers':['Continue with draft']}}})

    def test_team_preparation_rolls_back_conflicting_role_identity(self):
        spec={**self.spec,'instructions':'Conflicting replacement'}
        with patch.object(R.subprocess,'run') as proc:
            proc.return_value.returncode=0
            with self.assertRaises(R.RuntimeError_):
                self.store.prepare({'roles':{'new-role':self.spec,'coordinator':spec}})
        self.assertIsNone(self.store.db.execute("SELECT * FROM roles WHERE name='new-role'").fetchone())

    def test_status_never_calls_missing_activity_success(self):
        self.active()
        self.store.db.execute('UPDATE roles SET last_event=?',(time.time()-130,))
        self.assertEqual(self.store.status()['roles'][0]['observation'],'stale/unknown')

    def test_peer_routing_binds_sender_to_native_thread_and_never_human_authority(self):
        self.store.db.execute("INSERT INTO roles VALUES('product-manager',?,NULL,NULL,'prepared',NULL)",(json.dumps(self.spec),))
        self.active()
        msg={'id':7,'method':'item/tool/call','params':{'threadId':'native-thread','turnId':'native-turn','tool':'delivery_send','arguments':{'recipient':'product-manager','message':'A peer observation'}}}
        self.coordinator.receive(msg)
        self.assertTrue(self.coordinator.rpc.sent[-1]['result']['success'])
        row=self.store.db.execute("SELECT * FROM queue WHERE role='product-manager'").fetchone()
        self.assertEqual(row['source'],'peer:coordinator')
        result=json.loads(self.coordinator.rpc.sent[-1]['result']['contentItems'][0]['text'])
        self.assertFalse(result['human_authority'])
        forged={**msg,'id':8,'params':{**msg['params'],'arguments':{**msg['params']['arguments'],'actor':'owner'}}}
        self.coordinator.receive(forged)
        self.assertFalse(self.coordinator.rpc.sent[-1]['result']['success'])
        stale={**msg,'id':9,'params':{**msg['params'],'turnId':'stale'}}
        self.coordinator.receive(stale)
        self.assertFalse(self.coordinator.rpc.sent[-1]['result']['success'])

    def test_exact_steer_and_interrupt_ack_do_not_imply_completion(self):
        self.active()
        for action in ('steer', 'interrupt'):
            self.store.control('coordinator','native-thread','native-turn',action,'Correction' if action=='steer' else None)
            self.coordinator.step()
        calls=dict(self.coordinator.rpc.calls)
        self.assertEqual(calls['turn/steer']['expectedTurnId'],'native-turn')
        self.assertEqual(calls['turn/interrupt']['turnId'],'native-turn')
        self.assertEqual(self.store.status()['roles'][0]['phase'],'active')
        with self.assertRaises(R.RuntimeError_):
            self.store.control('coordinator','native-thread','other-turn','interrupt')

    def test_recovery_requires_exact_native_terminal_before_resuming_queue(self):
        self.active()
        self.store.db.execute("UPDATE roles SET phase='needs-reconciliation'")
        self.store.control('coordinator','native-thread','native-turn','recover')
        self.coordinator.step()
        self.assertEqual(self.store.status()['roles'][0]['phase'],'idle')
        self.assertIsNone(self.store.status()['roles'][0]['turn'])
        self.assertEqual(self.store.db.execute("SELECT state FROM queue").fetchone()[0],'idle')

    def test_control_unknown_result_never_replayed(self):
        self.active()
        self.store.control('coordinator','native-thread','native-turn','steer','Correction')
        original=self.coordinator.rpc.call
        def failure(method,params):
            if method=='turn/steer':
                raise R.ProtocolError('rpc_timeout:turn/steer')
            return original(method,params)
        self.coordinator.rpc.call=failure
        self.coordinator.step(); self.coordinator.step()
        self.assertEqual(self.store.db.execute('SELECT state FROM controls').fetchone()[0],'unknown')
        self.assertEqual(self.store.status()['roles'][0]['phase'],'needs-reconciliation')

    def test_watchdog_does_not_call_silent_active_work_complete(self):
        self.active()
        self.store.db.execute('UPDATE roles SET last_event=?',(time.time()-130,))
        self.coordinator.step()
        self.assertEqual(self.store.status()['roles'][0]['phase'],'needs-reconciliation')
        self.assertEqual(self.store.db.execute('SELECT state FROM queue').fetchone()[0],'started')

    def test_unknown_permission_requests_and_stale_approval_deny_without_capture(self):
        self.active()
        self.coordinator.receive({'id':27,'method':'item/permissions/requestApproval','params':{'threadId':'native-thread','turnId':'native-turn'}})
        self.assertIn('error',self.coordinator.rpc.sent[-1])
        self.coordinator.receive({'id':28,'method':'item/commandExecution/requestApproval','params':{'threadId':'native-thread','turnId':'old-turn'}})
        self.assertIn('error',self.coordinator.rpc.sent[-1])
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM pending').fetchone()[0],0)

    def test_revocation_before_forwarding_discards_answer(self):
        self.active()
        self.coordinator.receive({'id':29,'method':'item/tool/requestUserInput','params':{'threadId':'native-thread','turnId':'native-turn'}})
        row=self.store.db.execute('SELECT * FROM pending').fetchone()
        self.store.db.execute("UPDATE pending SET state='answered',answer=?",(json.dumps({'decision':'accept'}),))
        self.store.revoke(row['id']);self.coordinator.step()
        self.assertIn('error',self.coordinator.rpc.sent[-1])
        self.assertIsNone(self.store.db.execute('SELECT answer FROM pending').fetchone()[0])

    def test_pending_unicode_question_hash_matches_capture_validator(self):
        import operator_capture
        self.active()
        self.coordinator.receive({'id':30,'method':'item/tool/requestUserInput','params':{'threadId':'native-thread','turnId':'native-turn','questions':[{'id':'cafe','question':'Café?'}]}})
        binding=R.pending_binding(self.store,self.store.db.execute('SELECT * FROM pending').fetchone())
        operator_capture.validate_binding(binding)

    def test_resume_revalidates_effective_native_lane(self):
        self.active()
        self.coordinator.rpc.bad_lane=True
        self.coordinator.reconcile()
        self.assertEqual(self.store.status()['roles'][0]['phase'],'unavailable')

    def test_native_policy_requires_explicit_human_reviewer_and_bound_cwd(self):
        good={'model':'test-model','thread':{'id':'t'},'sandbox':{'type':'readOnly','networkAccess':False},'cwd':str(self.project),'approvalPolicy':'on-request','approvalsReviewer':'user'}
        for override in ({'approvalsReviewer':'guardian_subagent'},{'approvalPolicy':'never'},{'cwd':'/tmp'}):
            with self.assertRaises(R.ProtocolError):
                R.verify_native({**good,**override},self.spec)

    def test_judge_without_explicit_config_is_unavailable_not_fallback(self):
        self.active()
        self.coordinator.receive({'id':31,'method':'item/tool/call','params':{'threadId':'native-thread','turnId':'native-turn','tool':'delivery_judge','arguments':{'question':'relay_request','state':{}}}})
        self.assertFalse(self.coordinator.rpc.sent[-1]['result']['success'])
        self.assertIn('No explicitly selected',self.coordinator.rpc.sent[-1]['result']['contentItems'][0]['text'])

    def test_early_dynamic_request_is_bound_after_native_turn_response(self):
        self.store.db.execute("INSERT INTO roles VALUES('product-manager',?,NULL,NULL,'needs-reconciliation',NULL)",(json.dumps(self.spec),))
        original=self.coordinator.rpc.call
        def early(method,params):
            if method=='turn/start':
                self.coordinator.receive({'id':40,'method':'item/tool/call','params':{'threadId':'native-thread','turnId':'native-turn','tool':'delivery_send','arguments':{'recipient':'product-manager','message':'Fast peer message'}}})
            return original(method,params)
        self.coordinator.rpc.call=early
        self.active()
        self.assertTrue(self.coordinator.rpc.sent[-1]['result']['success'])
        self.assertEqual(self.store.db.execute("SELECT source FROM queue WHERE role='product-manager'").fetchone()[0],'peer:coordinator')

    def test_async_terminal_wait_keeps_revocation_responsive(self):
        import threading
        import operator_capture
        waiting=threading.Event(); release=threading.Event()
        authority=operator_capture.CaptureAuthority()
        def terminal(challenge):
            waiting.set();release.wait(2)
            raise operator_capture.CaptureError('Synthetic terminal closed')
        authority.capture_from_terminal=terminal
        self.coordinator.operator_authority=authority
        self.active()
        self.coordinator.receive({'id':41,'method':'item/tool/requestUserInput','params':{'threadId':'native-thread','turnId':'native-turn','questions':[{'id':'q','question':'Choose'}]}})
        start=time.monotonic();self.coordinator.step()
        self.assertLess(time.monotonic()-start,1)
        self.assertTrue(waiting.wait(1))
        row=self.store.db.execute('SELECT * FROM pending').fetchone()
        self.store.revoke(row['id']);self.coordinator.step()
        self.assertIn('error',self.coordinator.rpc.sent[-1])
        release.set()

    def test_legacy_pending_capture_cannot_approve_worker_sandbox_escape(self):
        class SyntheticAuthority:
            def verify_receipt(self,receipt,binding):return {'decision':'accept'}
        self.active()
        legacy={'id':42,'method':'item/commandExecution/requestApproval','params':{'threadId':'native-thread','turnId':'native-turn'}}
        self.store.db.execute("INSERT INTO pending VALUES('legacy','42','native-thread','native-turn',?,?,'pending',NULL)", (json.dumps(legacy),time.time()+60))
        row=self.store.db.execute('SELECT * FROM pending').fetchone()
        self.coordinator.operator_authority=SyntheticAuthority()
        self.coordinator.capture_results.put((row['id'],{'unit_fixture':True},None))
        self.coordinator.step()
        self.assertIn('error',self.coordinator.rpc.sent[-1])
        self.assertEqual(self.store.db.execute('SELECT state FROM pending').fetchone()[0],'expired')

    def test_builder_cannot_mutate_privileged_plugin_implementation(self):
        builder={**self.spec,'lane':'builder','cwd':str(SCRIPTS.parent)}
        with self.assertRaisesRegex(R.RuntimeError_,'overlaps'):
            R.validate_bound_spec(self.store,'builder',builder)
        self.store.db.execute("INSERT INTO roles VALUES('builder',?,NULL,NULL,'prepared',NULL)",(json.dumps(builder),))
        self.store.enqueue('builder','Attempt to run from plugin implementation')
        self.coordinator.step()
        self.assertFalse(any(method=='thread/start' for method,params in self.coordinator.rpc.calls))

    def test_changed_judge_config_fails_before_provider_invocation(self):
        import hashlib
        config=self.project/'judge.json';config.write_text('{"judge":{"provider":"openai","model":"m"}}')
        for key,value in {'judge_config':str(config),'judge_config_source_sha256':hashlib.sha256(config.read_bytes()).hexdigest(),'judge_config_json':config.read_text()}.items():
            self.store.db.execute('INSERT INTO settings VALUES(?,?)',(key,value))
        config.write_text('{"judge":{"provider":"jev","model":"m"}}')
        self.active()
        with patch.object(R.subprocess,'run') as process:
            self.coordinator.receive({'id':43,'method':'item/tool/call','params':{'threadId':'native-thread','turnId':'native-turn','tool':'delivery_judge','arguments':{'question':'relay_request','state':{}}}})
            process.assert_not_called()
        self.assertFalse(self.coordinator.rpc.sent[-1]['result']['success'])


    def test_resume_rejects_changed_native_tool_inventory(self):
        self.active()
        self.store.db.execute("UPDATE role_tools SET schema_hash='old-schema'")
        before=len(self.coordinator.rpc.calls)
        self.coordinator.reconcile()
        self.assertEqual(len(self.coordinator.rpc.calls),before)
        self.assertEqual(self.store.status()['roles'][0]['phase'],'unavailable')

    def test_explicit_session_migration_preserves_history_and_never_replays_work(self):
        self.active()
        result=self.coordinator.migrate('coordinator','native-thread','native-turn','Install current protected tools')
        row=self.store.status()['roles'][0]
        self.assertEqual(row['phase'],'prepared');self.assertIsNone(row['thread'])
        self.assertFalse(result['accepted'])
        self.assertEqual(self.store.db.execute('SELECT state FROM queue').fetchone()[0],'migration-unreconciled')
        self.assertTrue(self.store.db.execute("SELECT 1 FROM events WHERE kind='role_session_migration'").fetchone())
        self.assertFalse(any(method in ('thread/archive','thread/rollback') for method,params in self.coordinator.rpc.calls))

    def test_session_migration_refuses_wrong_or_nonterminal_native_turn(self):
        self.active()
        with self.assertRaises(R.RuntimeError_):
            self.coordinator.migrate('coordinator','native-thread','wrong-turn','Change tools')
        original=self.coordinator.rpc.call
        self.coordinator.rpc.call=lambda method,params: ({'thread':{'id':'native-thread','turns':[{'id':'native-turn','status':'inProgress'}]}} if method=='thread/read' else original(method,params))
        with self.assertRaises(R.RuntimeError_):
            self.coordinator.migrate('coordinator','native-thread','native-turn','Change tools')
        self.assertEqual(self.store.status()['roles'][0]['phase'],'active')


    def independent_git_repo(self):
        import subprocess
        product=self.project/'product'; product.mkdir()
        subprocess.run(['git','init','--quiet',str(product)],check=True)
        (product/'seed').write_text('seed')
        subprocess.run(['git','-C',str(product),'add','seed'],check=True)
        subprocess.run(['git','-C',str(product),'-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','--quiet','-m','Synthetic fixture'],check=True)
        return product

    def test_opt_in_git_metadata_profile_is_precise_and_pinned(self):
        product=self.independent_git_repo()
        profile=R.git_metadata_profile(product)
        roots=set(profile['writable_roots'])
        self.assertNotIn(str(product/'.git'),roots)
        self.assertNotIn(str(product/'.git/config'),roots)
        self.assertNotIn(str(product/'.git/hooks'),roots)
        self.assertIn(str(product/'.git/AUTO_MERGE.lock'),roots)
        self.assertIn(str(product/'.git/packed-refs.lock'),roots)
        self.assertNotIn(str(product/'.git/packed-refs'),roots)
        spec={**self.spec,'lane':'builder','cwd':str(product),'git_metadata_write':True}
        with self.assertRaisesRegex(R.RuntimeError_,'unprepared'):
            R.validate_bound_spec(self.store,'builder',spec)
        self.store.db.execute('INSERT INTO role_git_policy VALUES(?,?)',('builder',json.dumps(profile)))
        validated=R.validate_bound_spec(self.store,'builder',spec)
        options=R.native_options(validated)
        self.assertEqual(set(options['config']['sandbox_workspace_write.writable_roots']),roots)
        env=options['config']['shell_environment_policy.set']
        self.assertEqual(env['TMPDIR'],str(product/'.delivery-evidence/tmp'))
        self.assertEqual(env['TMPPREFIX'],str(product/'.delivery-evidence/tmp/zsh'))
        effective={'model':'test-model','thread':{'id':'builder-native'},'cwd':str(product),'approvalPolicy':'on-request','approvalsReviewer':'user','sandbox':{'type':'workspaceWrite','networkAccess':False,'excludeSlashTmp':True,'excludeTmpdirEnvVar':True,'writableRoots':list(roots)}}
        R.verify_native(effective,validated)
        effective['sandbox']['writableRoots'].append(str(product/'.git'))
        with self.assertRaises(R.ProtocolError):R.verify_native(effective,validated)

    def test_git_metadata_optin_rejects_shared_worktree_and_alternates(self):
        import subprocess
        product=self.independent_git_repo(); linked=self.project/'linked'
        subprocess.run(['git','-C',str(product),'worktree','add','--quiet','-b','linked',str(linked)],check=True)
        with self.assertRaisesRegex(R.RuntimeError_,'independent'):
            R.git_metadata_profile(linked)
        (product/'.git/objects/info/alternates').write_text(str(self.project))
        with self.assertRaisesRegex(R.RuntimeError_,'alternates'):
            R.git_metadata_profile(product)

    def test_git_metadata_optin_rejects_hardlinks_and_changed_branch(self):
        import os,subprocess
        product=self.independent_git_repo();profile=R.git_metadata_profile(product)
        objects=[path for path in (product/'.git/objects').rglob('*') if path.is_file()]
        alias=self.project/'object-hardlink';os.link(objects[0],alias)
        with self.assertRaisesRegex(R.RuntimeError_,'hardlinked'):
            R.git_metadata_profile(product)
        alias.unlink()
        spec={**self.spec,'lane':'builder','cwd':str(product),'git_metadata_write':True}
        self.store.db.execute('INSERT INTO role_git_policy VALUES(?,?)',('builder',json.dumps(profile)))
        subprocess.run(['git','-C',str(product),'symbolic-ref','HEAD','refs/heads/another'],check=True)
        with self.assertRaisesRegex(R.RuntimeError_,'changed'):
            R.validate_bound_spec(self.store,'builder',spec)

    def test_git_metadata_flag_requires_explicit_builder_boolean(self):
        with self.assertRaises(R.RuntimeError_):
            R.validate_bound_spec(self.store,'coordinator',{**self.spec,'git_metadata_write':True})
        with self.assertRaises(R.RuntimeError_):
            R.validate_bound_spec(self.store,'builder',{**self.spec,'lane':'builder','git_metadata_write':'true'})


    def test_native_roles_receive_canonical_package_and_peer_context(self):
        self.active()
        options=next(params for method,params in self.coordinator.rpc.calls if method=='thread/start')
        context=options['developerInstructions']
        self.assertIn(str(SCRIPTS.parent),context)
        self.assertIn(str(self.project/'.delivery'),context)
        self.assertIn(str(SCRIPTS.parent/'skills')+'/<phase>/SKILL.md',context)
        self.assertIn('coordinator',context);self.assertIn('read-only',context)
        self.assertIn('not permissions or human authority',context)
        self.coordinator.reconcile()
        resumed=next(params for method,params in self.coordinator.rpc.calls if method=='thread/resume')
        self.assertEqual(resumed['developerInstructions'],context)


    def test_reserved_profiles_cannot_inject_permissions_without_explicit_optin(self):
        product=self.independent_git_repo()
        raw={**self.spec,'cwd':str(product),'lane':'builder'}
        injected={'writable_roots':[str(self.project/'.delivery')]}
        for choice in ({},{'git_metadata_write':False}):
            spec={**raw,**choice,'_git_profile':injected}
            with self.assertRaises(R.RuntimeError_):
                R.validate_bound_spec(self.store,'builder',spec)
            with self.assertRaises(R.RuntimeError_):
                R.native_options({**spec,'_builder_tmpdir':str(product/'.delivery-evidence/tmp')})
            result={'model':'test-model','thread':{'id':'injected'},'cwd':str(product),'approvalPolicy':'on-request','approvalsReviewer':'user','sandbox':{'type':'workspaceWrite','networkAccess':False,'excludeSlashTmp':True,'excludeTmpdirEnvVar':True,'writableRoots':injected['writable_roots']}}
            with self.assertRaises(R.ProtocolError):
                R.verify_native(result,spec)
        for reserved in ('_git_profile','_builder_tmpdir'):
            with self.assertRaises(R.RuntimeError_):
                R.validate_bound_spec(self.store,'coordinator',{**self.spec,reserved:injected})


    def test_forbidden_worker_approvals_never_wait_or_capture_with_or_without_authority(self):
        from unittest.mock import Mock
        self.active()
        for authority in (None,Mock()):
            self.coordinator.operator_authority=authority
            for method in R.WORKER_ESCAPE_METHODS:
                message={'id':61,'method':method,'params':{'threadId':'native-thread','turnId':'native-turn','itemId':'blocked-item'}}
                self.coordinator.receive(message)
                self.assertEqual(self.coordinator.rpc.sent[-1],{'id':61,'result':{'decision':'decline'}})
                self.assertEqual(self.store.db.execute('SELECT count(*) FROM pending').fetchone()[0],0)
                self.assertEqual(self.coordinator.capture_challenges,{})
                self.assertIsNone(self.coordinator.capture_active)
            if authority:authority.assert_not_called();self.assertEqual(authority.method_calls,[])

    def test_worker_denial_respects_native_offered_decisions_and_never_grants(self):
        self.active()
        base={'id':62,'method':'item/commandExecution/requestApproval','params':{'threadId':'native-thread','turnId':'native-turn'}}
        for offered,expected in ((['accept','decline','cancel'],'decline'),(['accept',{'acceptWithExecpolicyAmendment':{}},'cancel'],'cancel'),([],None),(['accept'],None),('invalid',None)):
            self.coordinator.receive({**base,'params':{**base['params'],'availableDecisions':offered}})
            reply=self.coordinator.rpc.sent[-1]
            if expected:self.assertEqual(reply['result'],{'decision':expected})
            else:self.assertIn('error',reply)
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM pending').fetchone()[0],0)
        self.assertEqual(self.store.status()['roles'][0]['phase'],'active') # Native terminal, not reply, decides completion.

    def test_denial_replay_stale_and_unbound_requests_do_not_create_capture(self):
        self.active()
        message={'id':63,'method':'item/fileChange/requestApproval','params':{'threadId':'native-thread','turnId':'native-turn'}}
        self.coordinator.receive(message);self.coordinator.receive(message)
        self.assertEqual(self.coordinator.rpc.sent[-2:], [{'id':63,'result':{'decision':'decline'}}]*2)
        for change in ({'turnId':'old-turn'},{'threadId':'unbound'}):
            self.coordinator.receive({**message,'params':{**message['params'],**change}})
            self.assertIn('error',self.coordinator.rpc.sent[-1])
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM pending').fetchone()[0],0)

    def test_early_worker_approval_is_denied_only_after_exact_turn_binding(self):
        original=self.coordinator.rpc.call
        def early(method,params):
            if method=='turn/start':
                self.coordinator.receive({'id':64,'method':'item/commandExecution/requestApproval','params':{'threadId':'native-thread','turnId':'native-turn','availableDecisions':['accept','cancel']}})
                self.assertEqual(self.coordinator.rpc.sent,[])
            return original(method,params)
        self.coordinator.rpc.call=early;self.active()
        self.assertEqual(self.coordinator.rpc.sent[-1],{'id':64,'result':{'decision':'cancel'}})
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM pending').fetchone()[0],0)

    def test_real_question_requests_keep_operator_capture_path(self):
        from unittest.mock import Mock
        self.active();authority=Mock();self.coordinator.operator_authority=authority
        message={'id':65,'method':'item/tool/requestUserInput','params':{'threadId':'native-thread','turnId':'native-turn','questions':[{'id':'q','question':'Which scope?'}]}}
        self.coordinator.receive(message)
        row=self.store.db.execute('SELECT * FROM pending').fetchone()
        self.assertEqual(row['state'],'pending');self.assertEqual(json.loads(row['body']),message)
        self.assertEqual(self.coordinator.rpc.sent,[])


class RPCIsolationTests(unittest.TestCase):
    def test_merged_connectors_are_disabled_individually_and_inventory_checked(self):
        from unittest.mock import MagicMock
        from codex_rpc import CodexRPC
        commands=[]
        def spawn(command,**kwargs):
            commands.append(command)
            process=MagicMock();process.poll.return_value=None
            return process
        def call(rpc,method,params,timeout=40):
            if method=='initialize':return {'userAgent':'synthetic protocol fixture'}
            if method=='config/read':
                disabled=len(commands)>1
                return {'config':{'mcp_servers':{'safe-name':{'enabled':not disabled}},'plugins':{},'features':{'apps':False},'apps':{'_default':{'enabled':False}},'computer_use':{'default_app_access':'deny'},'browser_use':{'default_origin_policy':dict.fromkeys(('access','uploads','downloads','full_cdp_access'),'deny')}}}
            if method=='mcpServerStatus/list':return {'data':[{'tools':{}}],'nextCursor':None}
            raise AssertionError(method)
        with patch('codex_rpc.subprocess.Popen',side_effect=spawn),patch.object(CodexRPC,'_read',lambda self:None),patch.object(CodexRPC,'call',call):
            rpc=CodexRPC('.',lambda m:None)
            self.assertIn('mcp_servers.safe-name.enabled=false',commands[1])
            self.assertEqual(rpc.compatibility['connected_tool_inventory']['tools'],0)
            rpc.close()

    def test_native_connected_tool_inventory_prevents_startup(self):
        from unittest.mock import MagicMock
        from codex_rpc import CodexRPC
        def call(rpc,method,params,timeout=40):
            if method=='initialize':return {}
            if method=='config/read':return {'config':{'features':{'apps':False},'apps':{'_default':{'enabled':False}},'computer_use':{'default_app_access':'deny'},'browser_use':{'default_origin_policy':dict.fromkeys(('access','uploads','downloads','full_cdp_access'),'deny')}}}
            if method=='mcpServerStatus/list':return {'data':[{'tools':{'dangerous':{}}}]}
            raise AssertionError(method)
        process=MagicMock();process.poll.return_value=None
        with patch('codex_rpc.subprocess.Popen',return_value=process),patch.object(CodexRPC,'_read',lambda self:None),patch.object(CodexRPC,'call',call):
            with self.assertRaisesRegex(R.ProtocolError,'exposes connected tools'):
                CodexRPC('.',lambda m:None)
