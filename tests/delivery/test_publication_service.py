"""Actual non-model MCP subprocess and local consumer checks; synthetic inputs only."""
import copy
import json
import os
from pathlib import Path
import select
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest

SCRIPT = Path(__file__).resolve().parents[2] / 'plugins/delivery/scripts/publication_service.py'
SAFE = {'operation':'local-release','destination':'sample-product',
        'body':'SYNTHETIC: Counter implementation and usage.',
        'files':[{'name':'counter.py','content':'def increment(n): return n + 1\n'}],
        'metadata':{'title':'SYNTHETIC counter fix'}}
REGISTER = {'action':'register','destination':'sample-product','owner':'sample-owner',
            'audience':'sample-users','visibility':'private','revision':'r1',
            'authority_revision':'a1','policy_revision':'p1'}
ENV = {**os.environ, 'PYTHONDONTWRITEBYTECODE':'1'}


class Session:
    def __init__(self, db, initialize=False, control_socket=False):
        self.db = db
        self.control = None
        if initialize:
            initialized = subprocess.run([sys.executable,str(SCRIPT),'--db',str(db),'--initialize'],
                stdin=subprocess.DEVNULL,capture_output=True,text=True,timeout=5,env=ENV)
            if initialized.returncode != 0 or json.loads(initialized.stdout) != {'status':'initialized'}:
                raise AssertionError('One-shot initialization failed')
        extra = []
        inherited = ()
        child = None
        if control_socket:
            self.control, child = socket.socketpair()
            self.control.settimeout(5)
            extra += ['--control-fd',str(child.fileno())]
            inherited = (child.fileno(),)
        self.process = subprocess.Popen([sys.executable, str(SCRIPT),'--db',str(db),*extra],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            pass_fds=inherited, env=ENV)
        if child:
            child.close()
        self.sequence = 0
        self.rpc('initialize', {'protocolVersion':'2024-11-05','capabilities':{},'clientInfo':{'name':'synthetic','version':'1'}})

    def rpc(self, method, params=None, ident=None):
        self.sequence += 1
        request = {'jsonrpc':'2.0','id':self.sequence if ident is None else ident,'method':method}
        if params is not None:
            request['params'] = params
        self.process.stdin.write((json.dumps(request)+'\n').encode())
        self.process.stdin.flush()
        ready, _, _ = select.select([self.process.stdout], [], [], 5)
        if not ready:
            raise AssertionError('MCP response unavailable')
        line = self.process.stdout.readline()
        if not line:
            raise AssertionError('MCP process stopped')
        return json.loads(line)

    def call(self, suffix, ident='sample-one', value=None, **extra):
        args = {'operation_id':ident,'envelope':copy.deepcopy(SAFE if value is None else value),**extra}
        result = self.rpc('tools/call', {'name':'delivery_publication_'+suffix,'arguments':args})
        return json.loads(result['result']['content'][0]['text'])['status']

    def trusted(self, request):
        if self.control:
            self.control.sendall((json.dumps(request)+'\n').encode())
            line = b''
            while not line.endswith(b'\n'):
                chunk = self.control.recv(65536)
                if not chunk:
                    raise AssertionError('Control response unavailable')
                line += chunk
            return json.loads(line)
        result = subprocess.run([sys.executable,str(SCRIPT),'--db',str(self.db),'--control'],
                                input=json.dumps(request), text=True,capture_output=True,timeout=5,env=ENV)
        return json.loads(result.stdout) if result.stdout else {'status':'unavailable'}

    def review(self, binding, ident='sample-one', value=None, decision='approve', ttl=30):
        return self.trusted({'action':'review','operation_id':ident,
            'envelope':copy.deepcopy(SAFE if value is None else value),'decision':decision,
            'ttl_seconds':ttl,'expected_binding':binding})

    def stop(self):
        if self.control:
            self.control.close()
            self.control = None
        if self.process.poll() is None:
            self.process.stdin.close()
            self.process.stdin = None
        try:
            return self.process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            self.process.kill()
            return self.process.communicate(timeout=5)


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db = Path(self.temp.name)/'private-ledger.sqlite'
        self.session = Session(self.db, initialize=True)
        self.binding = self.session.trusted(REGISTER)['binding']

    def tearDown(self):
        self.session.stop()
        self.temp.cleanup()

    def approved(self, ident='sample-one', value=None, ttl=30):
        self.assertEqual(self.session.call('submit',ident,value), 'submitted')
        self.assertEqual(self.session.review(self.binding,ident,value,ttl=ttl)['status'], 'recorded')

    def count(self):
        with sqlite3.connect(self.db) as connection:
            return connection.execute('SELECT count(*) FROM releases').fetchone()[0]

    def test_actual_mcp_discovery_and_no_approval_tool(self):
        result = self.session.rpc('tools/list', ident='host-request-1')
        self.assertEqual(result['id'], 'host-request-1')
        names = {t['name'] for t in result['result']['tools']}
        self.assertEqual(names, {'delivery_publication_submit','delivery_publication_publish','delivery_publication_receipt'})
        self.assertEqual(self.session.call('approve'), 'blocked')
        self.assertEqual(self.session.call('submit', approved=True), 'blocked')
        self.assertEqual(self.session.call('publish'), 'blocked')
        self.assertEqual(self.count(),0)

    def test_opaque_protocol_ids_echo_without_becoming_application_authority(self):
        for ident in ('', 'request/1', ' space?!\n雪 ', 'x' * 4096, -1, 2147483648, 2**80):
            with self.subTest(ident_type=type(ident).__name__):
                reply = self.session.rpc('ping', ident=ident)
                self.assertEqual(reply, {'jsonrpc':'2.0','id':ident,'result':{}})
                reply = self.session.rpc('tools/call', {
                    'name':'delivery_publication_submit',
                    'arguments':{'operation_id':'sample-one','envelope':SAFE}}, ident=ident)
                self.assertEqual(reply['id'], ident)
                self.assertEqual(json.loads(reply['result']['content'][0]['text'])['status'], 'submitted')
        self.assertEqual(self.session.call('publish'), 'blocked')
        self.assertEqual(self.session.call('submit', ident='request/1'), 'blocked')
        wrong = copy.deepcopy(SAFE)
        wrong['destination'] = 'request/1'
        self.assertEqual(self.session.call('submit', value=wrong), 'blocked')
        self.assertEqual(self.count(), 0)

    def test_protocol_extensions_are_ignored_outside_candidate_arguments(self):
        request = {'jsonrpc':'2.0','id':'extension/request','method':'tools/call',
                   'syntheticExtension':'SYNTHETIC_PRIVATE_TRANSPORT',
                   'params':{'name':'delivery_publication_submit',
                             'approved':True,'syntheticExtension':'SYNTHETIC_PRIVATE_TRANSPORT',
                             'arguments':{'operation_id':'sample-one','envelope':SAFE}}}
        self.session.process.stdin.write((json.dumps(request)+'\n').encode())
        self.session.process.stdin.flush()
        ready, _, _ = select.select([self.session.process.stdout], [], [], 5)
        self.assertTrue(ready)
        reply = json.loads(self.session.process.stdout.readline())
        self.assertEqual(reply['id'], request['id'])
        self.assertEqual(json.loads(reply['result']['content'][0]['text'])['status'], 'submitted')
        self.assertEqual(self.session.call('publish'), 'blocked')
        self.assertEqual(self.session.call('submit', approved=True), 'blocked')
        with sqlite3.connect(self.db) as connection:
            self.assertNotIn('SYNTHETIC_PRIVATE_TRANSPORT', '\n'.join(connection.iterdump()))
        self.assertEqual(self.count(), 0)

    def test_invalid_protocol_id_types_fail_and_next_request_stays_aligned(self):
        for ident in (True, False, None, 1.5, [], {}):
            wire = {'jsonrpc':'2.0','id':ident,'method':'ping'}
            self.session.process.stdin.write((json.dumps(wire)+'\n').encode())
            self.session.process.stdin.flush()
            ready, _, _ = select.select([self.session.process.stdout], [], [], 5)
            self.assertTrue(ready)
            reply = json.loads(self.session.process.stdout.readline())
            self.assertIsNone(reply['id'])
            self.assertIn('error', reply)
            self.assertEqual(self.session.rpc('ping')['result'], {})

    def test_notifications_do_not_reply_or_publish_and_next_request_stays_aligned(self):
        self.approved()
        notifications = [
            {'method':'notifications/initialized'},
            {'method':'notifications/cancelled','params':{'requestId':9}},
            {'method':'notifications/progress','params':{'progressToken':'synthetic','progress':1}},
            {'method':'unknown/notification','params':[]},
            {'method':'unknown/notification','extension':{'synthetic':'ignored'}},
            {'method':'tools/call','params':{'name':'delivery_publication_publish',
                'arguments':{'operation_id':'sample-one','envelope':SAFE}}},
        ]
        for i, notice in enumerate(notifications):
            self.session.process.stdin.write((json.dumps({'jsonrpc':'2.0',**notice})+'\n').encode())
            self.session.process.stdin.flush()
            response = self.session.rpc('ping',ident='after-notice-'+str(i))
            self.assertEqual(response,{'jsonrpc':'2.0','id':'after-notice-'+str(i),'result':{}})
        self.assertEqual(self.count(),0)
        self.assertEqual(self.session.call('publish'),'completed')

    def test_protocol_metadata_is_accepted_but_never_stored_or_released(self):
        marker = 'SYNTHETIC_PRIVATE_TRANSPORT_ONLY'
        for method in ('submit','publish','receipt'):
            if method == 'publish':
                forged = self.session.rpc('tools/call',{
                    'name':'delivery_publication_publish',
                    'arguments':{'operation_id':'sample-one','envelope':SAFE},
                    '_meta':{'approved':True,'decision':'approve'}})
                self.assertEqual(json.loads(forged['result']['content'][0]['text']),{'status':'blocked'})
                self.assertEqual(self.session.review(self.binding)['status'],'recorded')
            result = self.session.rpc('tools/call',{
                'name':'delivery_publication_'+method,
                'arguments':{'operation_id':'sample-one','envelope':SAFE},
                '_meta':{'progressToken':'synthetic-progress','example/context':marker}})
            self.assertFalse(result['result']['isError'])
            self.assertNotIn(marker,json.dumps(result))
        self.session.stop()
        with sqlite3.connect(self.db) as connection:
            self.assertNotIn(marker,'\n'.join(connection.iterdump()))
        exported = subprocess.run([sys.executable,str(SCRIPT),'--db',str(self.db),
            '--consume','sample-one'],capture_output=True,text=True,env=ENV)
        self.assertEqual(exported.returncode,0)
        self.assertEqual(json.loads(exported.stdout),SAFE)
        self.assertNotIn(marker,exported.stdout+exported.stderr)
        self.session = Session(self.db)

    def test_invalid_protocol_forms_fail_without_echo_or_effect(self):
        for metadata in (None,[],True,'SYNTHETIC_PRIVATE',{'progressToken':{}},{'progressToken':True}):
            response = self.session.rpc('tools/call',{'name':'delivery_publication_submit',
                'arguments':{'operation_id':'sample-one','envelope':SAFE},'_meta':metadata})
            self.assertEqual(response['error']['message'],'Request blocked')
            self.assertNotIn('SYNTHETIC_PRIVATE',json.dumps(response))
        for invalid in ({'jsonrpc':'2.0','method':17},
                        {'jsonrpc':'2.0','method':'notifications/cancelled','params':'invalid'},
                        {'jsonrpc':'2.0','id':None,'method':'ping'}):
            self.session.process.stdin.write((json.dumps(invalid)+'\n').encode())
            self.session.process.stdin.flush()
            self.assertTrue(select.select([self.session.process.stdout],[],[],5)[0])
            self.assertIn('error',json.loads(self.session.process.stdout.readline()))
            self.assertEqual(self.session.rpc('ping')['result'],{})
        with sqlite3.connect(self.db) as connection:
            self.assertEqual(connection.execute('SELECT count(*) FROM drafts').fetchone()[0],0)
        self.assertEqual(self.count(),0)

    def test_oversized_protocol_metadata_is_refused_before_submission(self):
        request = {'jsonrpc':'2.0','id':'oversized','method':'tools/call','params':{
            'name':'delivery_publication_submit',
            'arguments':{'operation_id':'sample-one','envelope':SAFE},
            '_meta':{'context':'x'*1_048_576}}}
        self.session.process.stdin.write((json.dumps(request)+'\n').encode())
        self.session.process.stdin.flush()
        self.session.process.stdin.close();self.session.process.stdin=None
        out,err=self.session.process.communicate(timeout=5)
        self.assertEqual(self.session.process.returncode,2)
        self.assertEqual(out,b'');self.assertEqual(err,b'{"status":"unavailable"}\n')
        with sqlite3.connect(self.db) as connection:
            self.assertEqual(connection.execute('SELECT count(*) FROM drafts').fetchone()[0],0)

    def test_protected_forms_rejected_then_corrected_safe_release(self):
        corpus = ['SYNTHETIC PRIVATE: violet robots launch on moon seven.',
                  'SYNTHETIC: purple automatons debut on the seventh moon.',
                  'VmlvbGV0IHJvYm90cw==', 'Usage plus SYNTHETIC PRIVATE violet robots.']
        for i, text in enumerate(corpus):
            value = copy.deepcopy(SAFE);value['body'] = text
            ident = 'blocked-'+str(i)
            self.assertEqual(self.session.call('submit',ident,value), 'submitted')
            self.assertEqual(self.session.review(self.binding,ident,value,decision='reject')['status'], 'recorded')
            self.assertEqual(self.session.call('publish',ident,value), 'blocked')
        self.assertEqual(self.count(),0)
        self.approved()
        self.assertEqual(self.session.call('publish'), 'completed')
        self.assertEqual(self.count(),1)

    def test_entire_envelope_is_immutable_including_names_metadata_and_message(self):
        self.approved()
        for field in ('body','metadata','files','destination'):
            value = copy.deepcopy(SAFE)
            if field == 'files': value[field][0]['name'] = 'renamed-private-context.py'
            elif field == 'metadata': value[field]['title'] = 'SYNTHETIC PRIVATE title'
            else: value[field] = 'other-private' if field == 'destination' else 'SYNTHETIC PRIVATE message'
            self.assertEqual(self.session.call('publish',value=value), 'blocked')
        self.assertEqual(self.count(),0)
        self.assertEqual(self.session.call('publish'), 'completed')

    def test_private_wrong_destination_is_not_authorized(self):
        self.approved()
        self.session.trusted({**REGISTER,'destination':'other-private','audience':'other-users'})
        value = copy.deepcopy(SAFE);value['destination']='other-private'
        self.assertEqual(self.session.call('submit','another',value), 'submitted')
        self.assertEqual(self.session.call('publish','another',value), 'blocked')
        self.assertEqual(self.count(),0)

    def test_revocation_and_stale_operator_snapshot_and_aba(self):
        self.approved()
        changed = self.session.trusted({**REGISTER,'audience':'changed-users','authority_revision':'a2'})['binding']
        self.assertGreater(changed['generation'],self.binding['generation'])
        self.assertEqual(self.session.call('publish'), 'blocked')
        self.assertEqual(self.session.review(self.binding)['status'], 'blocked')
        restored = self.session.trusted(REGISTER)['binding']
        self.assertGreater(restored['generation'],changed['generation'])
        self.assertEqual(self.session.call('publish'), 'blocked')
        self.assertEqual(self.session.review(self.binding)['status'], 'blocked')
        self.assertEqual(self.session.review(restored)['status'], 'recorded')
        self.assertEqual(self.session.call('publish'), 'completed')

    def test_sql_expiry_and_clock_before_issuance_fail_closed(self):
        self.approved(ttl=.05)
        time.sleep(.1)
        self.assertEqual(self.session.call('publish'), 'blocked')
        self.assertEqual(self.session.review(self.binding)['status'],'recorded')
        with sqlite3.connect(self.db) as connection:
            connection.execute('UPDATE reviews SET issued=issued+1000, expires=expires+2000')
        self.assertEqual(self.session.call('publish'), 'blocked')
        self.assertEqual(self.count(),0)

    def _assert_commit_failure_reconciliation(self, after_effect):
        import importlib.util
        spec = importlib.util.spec_from_file_location('publication_commit_test', SCRIPT)
        service = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(service)
        self.approved()
        self.session.stop()
        store = service.PublicationStore(self.db)
        underlying = store.db

        class CommitFailure:
            def __init__(self):
                self.armed = True
                self.rollback_count = 0

            def __getattr__(self, name):
                return getattr(underlying, name)

            def execute(self, sql, *args):
                if sql == 'ROLLBACK':
                    self.rollback_count += 1
                if sql == 'COMMIT' and self.armed:
                    self.armed = False
                    if after_effect:
                        underlying.execute(sql, *args)
                    raise sqlite3.OperationalError('synthetic commit failure')
                return underlying.execute(sql, *args)

        connection = CommitFailure()
        store.db = connection
        args = {'operation_id':'sample-one','envelope':copy.deepcopy(SAFE)}
        try:
            self.assertEqual(store.call('delivery_publication_publish',args), {'status':'unknown'})
            self.assertFalse(underlying.in_transaction)
            self.assertEqual(connection.rollback_count, 0 if after_effect else 1)
            self.assertEqual(self.count(), 1 if after_effect else 0)
            expected_receipt = 'completed' if after_effect else 'not-released'
            self.assertEqual(store.call('delivery_publication_receipt',args), {'status':expected_receipt})
            # Receipt starts and commits another transaction on the same connection.
            self.assertFalse(underlying.in_transaction)
        finally:
            underlying.close()
        self.session = Session(self.db)
        self.assertEqual(self.session.call('receipt'), expected_receipt)
        self.assertEqual(self.session.call('publish'),'completed')
        self.assertEqual(self.session.call('receipt'),'completed')
        self.assertEqual(self.session.call('publish'),'completed')
        wrong = copy.deepcopy(SAFE)
        wrong['metadata']['title'] = 'SYNTHETIC unreviewed replacement'
        self.assertEqual(self.session.call('receipt',value=wrong),'blocked')
        self.assertEqual(self.session.call('publish',value=wrong),'blocked')
        self.assertEqual(self.session.call('publish','replacement-id'),'blocked')
        self.assertEqual(self.count(),1)

    def test_failure_before_commit_rolls_back_and_same_connection_reconciles(self):
        self._assert_commit_failure_reconciliation(after_effect=False)

    def test_exception_after_real_commit_is_unknown_and_restart_has_one_receipt(self):
        self._assert_commit_failure_reconciliation(after_effect=True)

    def test_restart_lost_response_idempotent_receipt_and_no_new_id_authority(self):
        self.approved()
        message = {'jsonrpc':'2.0','id':999,'method':'tools/call','params':{
            'name':'delivery_publication_publish','arguments':{'operation_id':'sample-one','envelope':SAFE}}}
        self.session.process.stdin.write((json.dumps(message)+'\n').encode());self.session.process.stdin.flush()
        ready,_,_ = select.select([self.session.process.stdout],[],[],5)
        self.assertTrue(ready)
        # Drop the response, then restart the actual process against the same ledger.
        self.session.stop()
        self.session = Session(self.db)
        self.assertEqual(self.session.call('receipt'),'completed')
        self.assertEqual(self.session.call('publish'),'completed')
        self.assertEqual(self.session.call('publish','replacement-id'),'blocked')
        self.assertEqual(self.count(),1)

    def test_trusted_export_and_clean_consumer_receives_only_released_envelope(self):
        self.assertEqual(self.session.call('submit'),'submitted')
        command=[sys.executable,str(SCRIPT),'--db',str(self.db),'--consume','sample-one']
        before=subprocess.run(command,capture_output=True,text=True,env=ENV)
        self.assertEqual(before.returncode,2);self.assertEqual(before.stdout,'')
        self.assertEqual(self.session.review(self.binding)['status'],'recorded')
        self.assertEqual(self.session.call('publish'),'completed')
        exported=subprocess.run(command,capture_output=True,text=True,env=ENV)
        self.assertEqual(exported.returncode,0);self.assertEqual(json.loads(exported.stdout),SAFE)
        # Recipient gets only released bytes, no private ledger argument/connection.
        consumer=subprocess.run([sys.executable,'-I','-c',
            'import json,sys; v=json.load(sys.stdin); n={}; exec(v["files"][0]["content"],n); assert n["increment"](4)==5; print("counter behavior verified")'],
            input=exported.stdout,capture_output=True,text=True,env=ENV)
        self.assertEqual(consumer.returncode,0);self.assertEqual(consumer.stdout.strip(),'counter behavior verified')

    def test_missing_corrupt_or_reinitialized_ledger_does_not_reset_history(self):
        self.approved();self.assertEqual(self.session.call('publish'),'completed')
        original=self.db.read_bytes()
        result=subprocess.run([sys.executable,str(SCRIPT),'--db',str(self.db),'--initialize'],
                              input=b'',capture_output=True,env=ENV)
        self.assertEqual(result.returncode,2);self.assertEqual(self.db.read_bytes(),original)
        for name, data in [('missing',None),('corrupt',b'not a sqlite database')]:
            path=Path(self.temp.name)/name
            if data is not None:path.write_bytes(data)
            r=subprocess.run([sys.executable,str(SCRIPT),'--db',str(path)],input=b'',capture_output=True,env=ENV)
            self.assertEqual(r.returncode,2);self.assertEqual(r.stdout,b'')
            self.assertEqual(path.exists(),data is not None)
            if data is not None:self.assertEqual(path.read_bytes(),data)

    def test_initialize_with_devnull_is_one_shot_and_cannot_replace_existing_ledger(self):
        path = Path(self.temp.name)/'one-shot.sqlite'
        command = [sys.executable,str(SCRIPT),'--db',str(path),'--initialize']
        initialized = subprocess.run(command,stdin=subprocess.DEVNULL,capture_output=True,text=True,timeout=5,env=ENV)
        self.assertEqual(initialized.returncode,0)
        self.assertEqual(json.loads(initialized.stdout),{'status':'initialized'})
        self.assertEqual(initialized.stderr,'')
        original = path.read_bytes()
        repeated = subprocess.run(command,stdin=subprocess.DEVNULL,capture_output=True,text=True,timeout=5,env=ENV)
        self.assertEqual(repeated.returncode,2)
        self.assertEqual(repeated.stdout,'')
        self.assertEqual(repeated.stderr,'{"status":"unavailable"}\n')
        self.assertEqual(path.read_bytes(),original)

    def test_inherited_control_channel_is_distinct_from_candidate_tools(self):
        self.session.stop();self.session=Session(self.db,control_socket=True)
        self.approved();self.assertEqual(self.session.call('publish'),'completed')
        self.assertEqual(self.session.call('review'),'blocked')

    def test_malformed_duplicate_keys_and_oversized_frame_do_not_echo_payload(self):
        self.session.process.stdin.write(b'{"jsonrpc":"2.0","id":1,"id":2,"method":"ping"}\n')
        self.session.process.stdin.flush()
        self.assertTrue(select.select([self.session.process.stdout],[],[],5)[0])
        response=json.loads(self.session.process.stdout.readline())
        self.assertEqual(response['error']['message'],'Request blocked')
        self.session.process.stdin.write(b'x' * (1_048_576+1)+b'\n');self.session.process.stdin.flush()
        self.session.process.stdin.close();self.session.process.stdin=None
        out,err=self.session.process.communicate(timeout=5)
        self.assertEqual(self.session.process.returncode,2);self.assertEqual(out,b'')
        self.assertEqual(err,b'{"status":"unavailable"}\n')

    def test_largest_accepted_envelope_remains_reviewable_with_large_binding(self):
        binding_request = {**REGISTER}
        for field in ('owner','audience','revision','authority_revision','policy_revision'):
            binding_request[field] = '\U0001f642' * 256
        self.binding = self.session.trusted(binding_request)['binding']
        value = copy.deepcopy(SAFE)
        value['body'] = ''
        size = len(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode())
        value['body'] = 'x' * (1_048_576 - 32768 - size)
        self.approved(value=value)
        self.assertEqual(self.session.call('publish',value=value), 'completed')
        value['body'] += 'x'
        self.assertEqual(self.session.call('submit','over-limit',value), 'blocked')
        self.assertEqual(self.count(),1)


if __name__ == '__main__':
    unittest.main()
