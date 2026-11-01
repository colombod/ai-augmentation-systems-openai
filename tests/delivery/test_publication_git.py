"""Synthetic root-bundle, control replay and crash/recovery observations."""
import contextlib
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[2]/'plugins/delivery/scripts/publication_git.py'
spec = importlib.util.spec_from_file_location('publication_git_test_subject', SCRIPT)
subject = importlib.util.module_from_spec(spec)
spec.loader.exec_module(subject)
ENV = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'}
IDENTITY = {'name': 'Synthetic Author', 'email': 'author@example.invalid', 'timestamp': '0 +0000'}


def candidate(ident='change-one', destination='sample'):
    return {'schema_version': 1, 'operation': 'git-root-bundle', 'destination': destination,
            'output_name': ident+'.bundle',
            'files': [{'name': 'counter.py', 'content': 'def increment(n): return n + 1\n', 'mode': '100644'},
                      {'name': 'run.sh', 'content': '#!/bin/sh\nprintf "synthetic\\n"\n', 'mode': '100755'}],
            'commit': {'ref': 'refs/heads/main', 'message': 'Synthetic counter\n',
                       'author': copy.deepcopy(IDENTITY), 'committer': copy.deepcopy(IDENTITY)}}


class BundleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.db = self.root/'ledger.sqlite'
        self.output = self.root/'output'
        self.output.mkdir(mode=0o700)
        self.store = subject.Store(self.db)
        self.assertEqual(self.store.initialize(), {'status': 'initialized'})
        self.sequence = 0
        self.binding = self.register()['binding']

    def tearDown(self):
        subject.STOPPED = False
        self.temp.cleanup()

    def control(self, value, store=None):
        return (store or self.store).request(value, control=True)

    def control_id(self):
        self.sequence += 1
        return f'control-{self.sequence}'

    def registration(self, destination='sample', output=None):
        return {'action': 'register', 'control_id': self.control_id(), 'destination': destination,
                'owner': 'synthetic-owner', 'audience': 'synthetic-users', 'visibility': 'private',
                'revision': 'r1', 'authority_revision': 'a1', 'policy_revision': 'p1',
                'output_directory': str(output or self.output)}

    def register(self, destination='sample', output=None):
        return self.control(self.registration(destination, output))

    def data(self, action, ident='change-one', value=None, store=None):
        return (store or self.store).request({'action': action, 'operation_id': ident,
                                             'proposal': value or candidate(ident)})

    def review_request(self, ident='change-one', value=None, binding=None, decision='approve', ttl=300):
        return {'action': 'review', 'control_id': self.control_id(), 'operation_id': ident,
                'proposal': value or candidate(ident), 'expected_binding': binding or self.binding,
                'decision': decision, 'ttl_seconds': ttl}

    def approve(self, ident='change-one', value=None, binding=None, ttl=300):
        self.assertEqual(self.data('submit', ident, value)['status'], 'submitted')
        result = self.control(self.review_request(ident, value, binding, ttl=ttl))
        self.assertEqual(result['status'], 'recorded', result)
        return result

    def query(self, sql, args=()):
        with sqlite3.connect(self.db) as db:
            return db.execute(sql, args).fetchall()

    def run_cli(self, request=None, control=False, db=None):
        command = [sys.executable, str(SCRIPT), '--db', str(db or self.db)]
        if control:
            command.append('--control')
        raw = json.dumps(request).encode()+b'\n' if request is not None else b''
        return subprocess.run(command, input=raw, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              env=ENV, timeout=15)

    def test_actual_cli_review_publish_clone_and_use(self):
        value = candidate()
        reply = self.run_cli({'action': 'submit', 'operation_id': 'change-one', 'proposal': value})
        self.assertEqual(json.loads(reply.stdout)['status'], 'submitted')
        review = self.run_cli(self.review_request(), control=True)
        self.assertEqual(json.loads(review.stdout)['status'], 'recorded')
        published = self.run_cli({'action': 'publish', 'operation_id': 'change-one', 'proposal': value})
        result = json.loads(published.stdout)
        self.assertEqual(result['status'], 'completed', published.stderr)
        bundle = self.output/'change-one.bundle'
        self.assertEqual(hashlib.sha256(bundle.read_bytes()).hexdigest(), result['bundle_sha256'])
        clone = self.root/'consumer'
        cloned = subprocess.run(['git', 'clone', '-b', 'main', str(bundle), str(clone)], capture_output=True, env=ENV, umask=0o022)
        self.assertEqual(cloned.returncode, 0, cloned.stderr)
        self.assertEqual((clone/'counter.py').read_bytes(), value['files'][0]['content'].encode())
        self.assertEqual((clone/'run.sh').stat().st_mode & 0o777, 0o755)
        used = subprocess.run([sys.executable, '-c', 'import counter; assert counter.increment(4) == 5'],
                              cwd=clone, capture_output=True, env=ENV)
        self.assertEqual(used.returncode, 0, used.stderr)
        history = subprocess.run(['git', '-C', str(clone), 'rev-list', '--parents', 'HEAD'], capture_output=True)
        self.assertEqual(history.stdout.decode().split(), [result['root_commit']])
        actual = subprocess.run(['git', '-C', str(clone), 'cat-file', 'commit', 'HEAD'], capture_output=True).stdout
        expected = ('tree '+result['tree']+'\nauthor Synthetic Author <author@example.invalid> 0 +0000\n'
                    'committer Synthetic Author <author@example.invalid> 0 +0000\n\nSynthetic counter\n').encode()
        self.assertEqual(actual, expected)
        objects = subprocess.run(['git', '-C', str(clone), 'cat-file', '--batch-all-objects', '--batch-check'], capture_output=True)
        self.assertEqual(len(objects.stdout.splitlines()), 4)
        self.assertEqual(self.data('receipt', store=subject.Store(self.db)), result)
        self.assertEqual(self.data('publish'), result)
        self.assertEqual(len(self.query('SELECT * FROM attempts')), 1)

    def test_reject_then_safe_correction_without_source_commit(self):
        bad = candidate('mixed'); bad['files'].append({'name': 'private.txt', 'content': 'SYNTHETIC private note', 'mode': '100644'})
        self.data('submit', 'mixed', bad)
        self.control(self.review_request('mixed', bad, decision='reject'))
        self.assertEqual(self.data('publish', 'mixed', bad)['status'], 'needs-review')
        self.assertEqual(list(self.output.iterdir()), [])
        self.assertIn('SYNTHETIC private note', self.query('SELECT proposal FROM drafts WHERE operation_id=?', ('mixed',))[0][0])
        safe = candidate('safe')
        self.approve('safe', safe)
        self.assertEqual(self.data('publish', 'safe', safe)['status'], 'completed')
        self.assertFalse((self.output/'mixed.bundle').exists())

    def test_unknown_fields_and_all_bound_changes_refuse(self):
        self.approve()
        changes = []
        for field, changed in [('destination', 'other'), ('output_name', 'other.bundle'), ('schema_version', 2), ('operation', 'other')]:
            value = candidate(); value[field] = changed; changes.append(value)
        for field, changed in [('name', 'other.py'), ('content', 'changed'), ('mode', '100755')]:
            value = candidate(); value['files'][0][field] = changed; changes.append(value)
        for field, changed in [('ref', 'refs/heads/other'), ('message', 'changed')]:
            value = candidate(); value['commit'][field] = changed; changes.append(value)
        for who in ('author', 'committer'):
            for field, changed in [('name', 'Other'), ('email', 'other@example.invalid'), ('timestamp', '1 +0000')]:
                value = candidate(); value['commit'][who][field] = changed; changes.append(value)
        for value in changes:
            with self.subTest(value=value):
                self.assertIn(self.data('publish', value=value)['status'], ('blocked', 'conflict'))
        value = candidate(); value['unreviewed'] = 'extra'
        self.assertEqual(self.data('submit', value=value)['status'], 'blocked')
        self.assertEqual(list(self.output.iterdir()), [])

    def test_parser_path_content_identity_boundaries(self):
        bad_names = ['/absolute', '../up', 'a/../b', './a', 'a//b', '.git/config', 'A/.GiT/x',
                     'back\\slash', 'tab\tx', 'x.', 'x ', 'x\ny', '/'.join(['a']*33), 'x'*257]
        for name in bad_names:
            value = candidate(); value['files'][0]['name'] = name
            with self.subTest(name=name):
                self.assertEqual(self.data('submit', value=value)['status'], 'blocked')
        for name in ('COUNTER.PY', 'counter.py/child'):
            value = candidate(); value['files'][1]['name'] = name
            self.assertEqual(self.data('submit', value=value)['status'], 'blocked')
        for stamp in ('1 +1267', '1 +1460', '1 +1401', '1 -0000', '01 +0000', '4102444800 +0000'):
            value = candidate(); value['commit']['author']['timestamp'] = stamp
            self.assertEqual(self.data('submit', value=value)['status'], 'blocked')
        for stamp in ('0 +0000', '4102444799 +1400', '1 -1359'):
            value = candidate(); value['commit']['author']['timestamp'] = stamp
            self.assertEqual(subject.proposal(value, 'change-one'), subject.canonical(value))
        for name in (' Bad', 'Bad ', 'Bad\nName', 'Bad<Name'):
            value = candidate(); value['commit']['author']['name'] = name
            self.assertEqual(self.data('submit', value=value)['status'], 'blocked')
        for email in ('a b@c', 'a@@c', '@c', 'a@', 'a<@c', 'é@c'):
            value = candidate(); value['commit']['committer']['email'] = email
            self.assertEqual(self.data('submit', value=value)['status'], 'blocked')
        value = candidate(); value['files'][0]['content'] = 'x\0y'
        self.assertEqual(self.data('submit', value=value)['status'], 'blocked')
        value = candidate(); value['files'][0]['mode'] = '120000'
        self.assertEqual(self.data('submit', value=value)['status'], 'blocked')

    def test_capacity_and_exact_unicode_and_message(self):
        value = candidate(); value['files'] = [{'name': f'f{i}.txt', 'content': '雪\r\n', 'mode': '100644'} for i in range(128)]
        value['commit']['message'] = 'Exact message without final newline'
        self.approve(value=value)
        self.assertEqual(self.data('publish', value=value)['status'], 'completed')
        too_many = copy.deepcopy(value); too_many['files'].append({'name': 'extra', 'content': '', 'mode': '100644'})
        self.assertEqual(self.data('submit', value=too_many)['status'], 'blocked')
        too_large = candidate('large'); too_large['files'][0]['content'] = 'x'*subject.MAX_PROPOSAL
        self.assertEqual(self.data('submit', 'large', too_large)['status'], 'blocked')

    def test_no_implicit_git_environment_or_private_ancestry(self):
        private = self.root/'source'; private.mkdir()
        subprocess.run(['git', 'init', str(private)], capture_output=True, check=True)
        (private/'secret').write_text('SYNTHETIC private ancestor')
        subprocess.run(['git', '-C', str(private), 'add', '.'], check=True)
        subprocess.run(['git', '-C', str(private), '-c', 'user.name=Private', '-c', 'user.email=p@example.invalid',
                        'commit', '-m', 'Synthetic private commit'], capture_output=True, check=True)
        before = subprocess.check_output(['git', '-C', str(private), 'rev-parse', 'HEAD'])
        self.approve()
        with mock.patch.dict(os.environ, {'GIT_DIR': str(private/'.git'), 'GIT_WORK_TREE': str(private),
                                          'GIT_CONFIG_COUNT': '1', 'GIT_CONFIG_KEY_0': 'user.name', 'GIT_CONFIG_VALUE_0': 'Leak'}):
            result = self.data('publish')
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(subprocess.check_output(['git', '-C', str(private), 'rev-parse', 'HEAD']), before)
        self.assertNotIn(b'SYNTHETIC private ancestor', (self.output/'change-one.bundle').read_bytes())

    def test_control_replay_and_receipt_never_renew(self):
        self.data('submit')
        requests = [self.registration(), self.review_request(),
                    {'action': 'revoke', 'control_id': self.control_id(), 'destination': 'sample', 'expected_generation': 1},
                    {'action': 'cancel', 'control_id': self.control_id(), 'operation_id': 'change-one', 'proposal_sha256': subject.digest(candidate())}]
        for request in requests:
            with self.subTest(action=request['action']):
                first = self.control(request)
                self.assertIn(first['status'], ('recorded', 'cancelled'))
                self.assertEqual(self.control(request), first)
                receipt = self.control({'action': 'control-receipt', 'control_id': request['control_id'], 'request_sha256': subject.digest(request)})
                self.assertEqual(receipt, {'status': 'recorded', 'result': first})
                changed = dict(request, ignored='different')
                self.assertEqual(self.control(changed)['status'], 'conflict')
        self.assertEqual(len(self.query('SELECT * FROM reviews')), 1)
        self.assertEqual(self.control({'action': 'binding', 'destination': 'sample'})['binding']['generation'], 2)

    def test_control_lost_response_after_each_commit(self):
        class Lost(subject.Store):
            def control(self, request):
                super().control(request)
                raise OSError('synthetic response loss')
        self.data('submit')
        requests = [self.registration(), self.review_request(),
                    {'action': 'revoke', 'control_id': self.control_id(), 'destination': 'sample', 'expected_generation': 1},
                    {'action': 'cancel', 'control_id': self.control_id(), 'operation_id': 'change-one', 'proposal_sha256': subject.digest(candidate())}]
        for request in requests:
            self.assertEqual(self.control(request, Lost(self.db))['status'], 'unknown')
            receipt = self.control({'action': 'control-receipt', 'control_id': request['control_id'], 'request_sha256': subject.digest(request)})
            self.assertEqual(receipt['status'], 'recorded')
            self.assertEqual(self.control(request), receipt['result'])
        self.assertEqual(len(self.query('SELECT * FROM reviews')), 1)

    def test_control_absent_lookup_and_corrupt_ledger(self):
        request = self.review_request()
        self.assertEqual(self.control({'action': 'control-receipt', 'control_id': request['control_id'], 'request_sha256': subject.digest(request)}), {'status': 'not-found'})
        self.data('submit')
        self.assertEqual(self.control(request)['status'], 'recorded')
        self.db.write_bytes(b'SYNTHETIC damaged database')
        self.assertEqual(self.control({'action': 'control-receipt', 'control_id': request['control_id'], 'request_sha256': subject.digest(request)})['status'], 'unknown')
        self.assertEqual(self.db.read_bytes(), b'SYNTHETIC damaged database')

    def test_binding_change_revoke_and_cancel_before_admission(self):
        self.approve()
        changed = self.registration(); changed['audience'] = 'other-users'
        self.control(changed)
        self.assertEqual(self.data('publish')['status'], 'needs-review')
        self.binding = self.control({'action': 'binding', 'destination': 'sample'})['binding']
        self.control(self.review_request())
        self.control({'action': 'revoke', 'control_id': self.control_id(), 'destination': 'sample', 'expected_generation': self.binding['generation']})
        self.assertEqual(self.data('publish')['status'], 'needs-review')
        self.control({'action': 'cancel', 'control_id': self.control_id(), 'operation_id': 'change-one', 'proposal_sha256': subject.digest(candidate())})
        self.assertEqual(self.data('publish')['status'], 'cancelled')
        self.assertEqual(list(self.output.iterdir()), [])

    def test_expiry_before_admission_and_after_live_dispatch(self):
        self.approve(ttl=.001)
        time.sleep(.01)
        self.assertEqual(self.data('publish')['status'], 'needs-review')
        self.control(self.review_request())
        original = subject.os.link
        def after_admission(*args, **kwargs):
            with sqlite3.connect(self.db, timeout=.01) as db:
                with self.assertRaises(sqlite3.OperationalError):
                    db.execute("UPDATE reviews SET approved=0")
            with mock.patch.object(subject.time, 'time', return_value=time.time()+1000):
                return original(*args, **kwargs)
        with mock.patch.object(subject.os, 'link', side_effect=after_admission):
            self.assertEqual(self.data('publish')['status'], 'completed')

    def test_occupied_destination_and_symlink_never_overwrite(self):
        self.approve()
        target = self.output/'change-one.bundle'
        target.write_bytes(b'keep')
        self.assertEqual(self.data('publish')['status'], 'conflict')
        self.assertEqual(target.read_bytes(), b'keep')
        target.unlink(); target.symlink_to(self.db)
        self.assertEqual(self.data('publish')['status'], 'conflict')
        self.assertTrue(target.is_symlink())

    def test_destination_replacement_and_symlink_ancestry(self):
        self.approve()
        self.output.rename(self.root/'old-output'); self.output.mkdir(mode=0o700)
        self.assertEqual(self.data('publish')['status'], 'blocked')
        alias = self.root/'alias'; alias.symlink_to(self.output, target_is_directory=True)
        self.assertEqual(self.register('alias', alias)['status'], 'blocked')
        self.assertEqual(list(self.output.iterdir()), [])

    def test_process_crash_before_or_after_link_needs_reconcile(self):
        wrapper = self.root/'crash.py'
        wrapper.write_text('''import importlib.util,json,os,sys
s=importlib.util.spec_from_file_location('subject',sys.argv[1]);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
original=m.os.link
def effect(*a,**kw):
 if sys.argv[3]=='after': original(*a,**kw)
 os._exit(73)
m.os.link=effect
m.Store(sys.argv[2]).request(json.loads(sys.stdin.read()))
''')
        for mode in ('before', 'after'):
            ident = 'crash-'+mode
            value = candidate(ident)
            self.approve(ident, value)
            process = subprocess.run([sys.executable, str(wrapper), str(SCRIPT), str(self.db), mode],
                                     input=json.dumps({'action': 'publish', 'operation_id': ident, 'proposal': value}),
                                     text=True, capture_output=True, env=ENV, timeout=15)
            self.assertEqual(process.returncode, 73)
            self.assertEqual(self.query('SELECT state FROM attempts WHERE operation_id=?', (ident,)), [('intent',)])
            result = self.data('receipt', ident, value, subject.Store(self.db))
            if mode == 'before':
                self.assertEqual(result['status'], 'needs-review')
                self.assertEqual(self.data('publish', ident, value)['status'], 'needs-review')
                self.control(self.review_request(ident, value))
                self.assertEqual(self.data('publish', ident, value)['status'], 'completed')
                self.assertEqual(len(self.query('SELECT * FROM attempts WHERE operation_id=?', (ident,))), 2)
            else:
                self.assertEqual(result['status'], 'completed')
                self.assertEqual(self.data('publish', ident, value), result)
                self.assertEqual(len(self.query('SELECT * FROM attempts WHERE operation_id=?', (ident,))), 1)

    def test_uncertainty_fences_aliases_and_blocks_registration_escape(self):
        self.approve()
        original = subject.os.link
        def uncertain(*args, **kwargs):
            original(*args, **kwargs)
            raise OSError('synthetic uncertain response')
        with mock.patch.object(subject.os, 'link', side_effect=uncertain):
            self.assertEqual(self.data('publish')['status'], 'unknown')
        target = self.output/'change-one.bundle'
        target.chmod(0o644); target.write_bytes(b'SYNTHETIC mismatch'); target.chmod(0o444)
        self.assertEqual(self.data('receipt')['status'], 'conflict')
        self.assertEqual(self.register('alias')['status'], 'unknown')
        new = self.root/'elsewhere'; new.mkdir(mode=0o700)
        self.assertEqual(self.register('sample', new)['status'], 'unknown')
        different = self.register('unrelated', new)['binding']
        value = candidate('other', 'unrelated')
        self.approve('other', value, different)
        self.assertEqual(self.data('publish', 'other', value)['status'], 'completed')
        self.assertEqual(target.read_bytes(), b'SYNTHETIC mismatch')

    def test_readonly_inode_and_cleanup_failure_do_not_republish(self):
        self.approve()
        original_unlink = subject.os.unlink
        def refuse_cleanup(path, *args, **kwargs):
            if str(path).endswith('output.bundle'):
                raise OSError('synthetic cleanup failure')
            return original_unlink(path, *args, **kwargs)
        with mock.patch.object(subject.os, 'unlink', side_effect=refuse_cleanup):
            result = self.data('publish')
        self.assertEqual(result['status'], 'completed')
        details = json.loads(self.query('SELECT details FROM attempts')[0][0])
        self.assertEqual(os.stat(details['stage']).st_ino, os.stat(self.output/'change-one.bundle').st_ino)
        self.assertEqual(os.stat(details['stage']).st_mode & 0o222, 0)
        self.assertEqual(self.data('publish'), result)
        self.assertEqual(len(self.query('SELECT * FROM attempts')), 1)

    def test_actual_busy_lock_and_control_not_applied(self):
        wrapper = self.root/'lock.py'
        marker = self.root/'held'
        wrapper.write_text('import fcntl,os,sys,time\nf=open(sys.argv[1],"r+");fcntl.flock(f,fcntl.LOCK_EX);open(sys.argv[2],"w").write("held");time.sleep(30)\n')
        process = subprocess.Popen([sys.executable, str(wrapper), str(self.store.lock_path), str(marker)], env=ENV)
        try:
            end = time.monotonic()+5
            while not marker.exists() and time.monotonic() < end:
                time.sleep(.01)
            self.assertTrue(marker.exists())
            request = self.registration()
            started = time.monotonic()
            self.assertEqual(self.control(request), {'status': 'busy'})
            self.assertLess(time.monotonic()-started, 2)
            self.assertEqual(self.query('SELECT count(*) FROM control_history')[0][0], 1)
        finally:
            process.terminate(); process.wait(timeout=5)
        self.assertEqual(self.control(request)['status'], 'recorded')

    def test_cancel_or_budget_observed_before_dispatch_no_effect(self):
        self.approve()
        original = subject.build_bundle
        def cancel(*args):
            result = original(*args)
            subject.STOPPED = True
            return result
        with mock.patch.object(subject, 'build_bundle', side_effect=cancel):
            self.assertEqual(self.data('publish')['status'], 'cancelled')
        self.assertEqual(list(self.output.iterdir()), [])
        subject.STOPPED = False
        self.assertEqual(self.data('publish')['status'], 'needs-review')

    def test_fsync_after_link_unknown_then_exact_recovery(self):
        self.approve()
        original = subject.os.fsync
        def fail_target(fd):
            info = os.fstat(fd)
            if info.st_ino == self.output.stat().st_ino and (self.output/'change-one.bundle').exists():
                raise OSError('synthetic durability failure')
            return original(fd)
        with mock.patch.object(subject.os, 'fsync', side_effect=fail_target):
            self.assertEqual(self.data('publish')['status'], 'unknown')
        self.assertEqual(self.data('receipt')['status'], 'completed')
        self.assertEqual(len(self.query('SELECT * FROM attempts')), 1)

    def test_cli_malformed_oversized_and_data_plane_control(self):
        for raw in (b'{"action":"submit","action":"publish"}\n', b'{"x":NaN}\n', b'\xff\n', b'x'*(subject.MAX_FRAME+1)+b'\n'):
            result = subprocess.run([sys.executable, str(SCRIPT), '--db', str(self.db)], input=raw,
                                    capture_output=True, env=ENV, timeout=5)
            self.assertEqual(json.loads(result.stdout)['status'], 'blocked')
            self.assertEqual(result.stderr, b'')
        self.assertEqual(json.loads(self.run_cli(self.registration()).stdout)['status'], 'blocked')
        existing = self.db.read_bytes()
        result = subprocess.run([sys.executable, str(SCRIPT), '--db', str(self.db), '--initialize'], capture_output=True, env=ENV)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(self.db.read_bytes(), existing)

    def test_unavailable_state_after_effect_never_reports_no_effect(self):
        self.approve()
        self.assertEqual(self.data('publish')['status'], 'completed')
        with sqlite3.connect(self.db) as db:
            db.execute('CREATE TABLE unexpected(value TEXT)')
        self.assertEqual(self.data('receipt')['status'], 'unknown')
        self.assertTrue((self.output/'change-one.bundle').exists())

    def test_blocked_control_is_terminal_even_after_precondition_changes(self):
        request = self.review_request()
        self.assertEqual(self.control(request)['status'], 'blocked')
        self.data('submit')
        self.assertEqual(self.control(request)['status'], 'blocked')
        self.assertEqual(self.query('SELECT count(*) FROM reviews')[0][0], 0)
        receipt = self.control({'action': 'control-receipt', 'control_id': request['control_id'],
                                'request_sha256': subject.digest(request)})
        self.assertEqual(receipt, {'status': 'recorded', 'result': {'status': 'blocked'}})
        self.assertEqual(self.control(self.review_request())['status'], 'recorded')

    def test_untrusted_ancestor_owner_refused_without_changing_ownership(self):
        original = subject.os.fstat
        ancestor = self.root.stat().st_ino
        def foreign(fd):
            info = original(fd)
            if info.st_ino == ancestor:
                values = list(info)
                values[4] = max(subject.TRUSTED_OWNERS)+1
                return os.stat_result(values)
            return info
        with mock.patch.object(subject.os, 'fstat', side_effect=foreign):
            with self.assertRaises(subject.Refused):
                subject.directory(self.output)

    def test_recovery_fifo_never_blocks_and_keeps_fence(self):
        self.approve()
        original = subject.os.link
        def uncertain(*args, **kwargs):
            original(*args, **kwargs)
            raise OSError('synthetic lost result')
        with mock.patch.object(subject.os, 'link', side_effect=uncertain):
            self.assertEqual(self.data('publish')['status'], 'unknown')
        target = self.output/'change-one.bundle'
        target.unlink(); os.mkfifo(target)
        started = time.monotonic()
        self.assertEqual(self.data('receipt')['status'], 'conflict')
        self.assertLess(time.monotonic()-started, 1)
        self.assertEqual(self.register('alias')['status'], 'unknown')

    def test_overlapping_control_cannot_acknowledge_cancellation(self):
        self.approve()
        original = subject.os.link
        cancel = {'action': 'cancel', 'control_id': self.control_id(), 'operation_id': 'change-one',
                  'proposal_sha256': subject.digest(candidate())}
        observed = []
        def concurrent_control(*args, **kwargs):
            reply = self.run_cli(cancel, control=True)
            observed.append(json.loads(reply.stdout))
            return original(*args, **kwargs)
        with mock.patch.object(subject.os, 'link', side_effect=concurrent_control):
            published = self.data('publish')
        self.assertEqual(observed, [{'status': 'busy'}])
        self.assertEqual(published['status'], 'completed')
        self.assertEqual(self.control(cancel), published)

    def test_all_writable_handles_closed_at_effect_and_no_mutation_api(self):
        self.approve()
        original = subject.os.link
        checked = []
        def inspect_handles(source, *args, **kwargs):
            info = os.stat(source)
            self.assertEqual(info.st_mode & 0o222, 0)
            # Linux process evidence is supplemental to the portable actual open refusal.
            if Path('/proc/self/fd').exists():
                for name in Path('/proc/self/fd').iterdir():
                    try:
                        fd = int(name.name)
                        handle = os.fstat(fd)
                    except OSError:
                        continue
                    if (handle.st_dev, handle.st_ino) == (info.st_dev, info.st_ino):
                        self.assertEqual(subject.fcntl.fcntl(fd, subject.fcntl.F_GETFL) & os.O_ACCMODE, os.O_RDONLY)
            if os.geteuid() != 0:
                with self.assertRaises(PermissionError):
                    os.open(source, os.O_WRONLY)
            checked.append(True)
            return original(source, *args, **kwargs)
        with mock.patch.object(subject.os, 'link', side_effect=inspect_handles):
            published = self.data('publish')
        self.assertEqual(published['status'], 'completed')
        self.assertEqual(checked, [True])
        before = (self.output/'change-one.bundle').read_bytes()
        changed = candidate(); changed['files'][0]['content'] = 'mutated'
        self.assertEqual(self.data('publish', value=changed)['status'], 'conflict')
        self.assertEqual((self.output/'change-one.bundle').read_bytes(), before)

    def test_staging_tamper_before_effect_refuses(self):
        self.approve()
        original = subject.build_bundle
        def tamper(*args):
            details = original(*args)
            stage = Path(details['stage'])
            stage.chmod(0o600); stage.write_bytes(b'SYNTHETIC altered staged artifact'); stage.chmod(0o444)
            return details
        with mock.patch.object(subject, 'build_bundle', side_effect=tamper):
            self.assertEqual(self.data('publish')['status'], 'blocked')
        self.assertEqual(list(self.output.iterdir()), [])

    def test_two_actual_callers_share_one_effect(self):
        self.approve()
        raw = (json.dumps({'action': 'publish', 'operation_id': 'change-one', 'proposal': candidate()})+'\n').encode()
        command = [sys.executable, str(SCRIPT), '--db', str(self.db)]
        first = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=ENV)
        second = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=ENV)
        first.stdin.write(raw); first.stdin.close(); first.stdin = None
        second.stdin.write(raw); second.stdin.close(); second.stdin = None
        one = json.loads(first.communicate(timeout=15)[0])
        two = json.loads(second.communicate(timeout=15)[0])
        self.assertEqual(one['status'], 'completed')
        self.assertEqual(two, one)
        self.assertEqual(len(self.query('SELECT * FROM attempts')), 1)

    def test_intermediate_directory_case_collisions_refuse(self):
        for first, second in [('Dir/a.txt', 'dir/b.txt'), ('top/Dir/a', 'top/dir/b'),
                              ('Straße/a', 'STRASSE/b')]:
            value = candidate()
            value['files'][0]['name'] = first
            value['files'][1]['name'] = second
            with self.subTest(first=first, second=second):
                self.assertEqual(self.data('submit', value=value)['status'], 'blocked')
        good = candidate('same-dir')
        good['files'][0]['name'] = 'Dir/a'
        good['files'][1]['name'] = 'Dir/b'
        self.assertEqual(self.data('submit', 'same-dir', good)['status'], 'submitted')

    def test_actual_sigint_sigterm_before_dispatch_preserve_no_effect(self):
        wrapper = self.root/'signal-wrapper.py'
        wrapper.write_text("import importlib.util,os,sys,time\nspec=importlib.util.spec_from_file_location('subject',sys.argv[1]);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)\nmarker,resume,db=sys.argv[2:]\noriginal=m.build_bundle\ndef build(*args):\n result=original(*args)\n open(marker,'w').write('prepared')\n deadline=time.monotonic()+10\n while not os.path.exists(resume):\n  if time.monotonic()>deadline: raise RuntimeError('synthetic barrier timeout')\n  time.sleep(.01)\n return result\nm.build_bundle=build\nsys.argv=[sys.argv[1],'--db',db]\nsys.exit(m.main())\n")
        for number, sig in enumerate((signal.SIGINT, signal.SIGTERM)):
            ident = f'signal-{number}'
            value = candidate(ident)
            self.approve(ident, value)
            marker, resume = self.root/f'marker-{number}', self.root/f'resume-{number}'
            process = subprocess.Popen([sys.executable, str(wrapper), str(SCRIPT), str(marker), str(resume), str(self.db)],
                                       stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=ENV)
            try:
                request = {'action': 'publish', 'operation_id': ident, 'proposal': value}
                process.stdin.write((json.dumps(request)+'\n').encode()); process.stdin.flush()
                deadline = time.monotonic()+10
                while not marker.exists() and time.monotonic()<deadline:
                    time.sleep(.01)
                self.assertTrue(marker.exists())
                process.send_signal(sig)
                # The real registered handler observes the signal while the test-only
                # barrier holds preparation before effect admission.
                time.sleep(.05)
                resume.write_text('continue')
                output, error = process.communicate(timeout=10)
                self.assertEqual(json.loads(output)['status'], 'cancelled', error)
                self.assertFalse((self.output/(ident+'.bundle')).exists())
                self.assertEqual(self.data('receipt', ident, value)['status'], 'needs-review')
                self.assertEqual(self.data('publish', ident, value)['status'], 'needs-review')
            finally:
                if process.poll() is None:
                    process.kill(); process.communicate(timeout=5)

    def test_actual_caller_output_pipe_loss_reconciles_completed(self):
        self.approve()
        process = subprocess.Popen([sys.executable, str(SCRIPT), '--db', str(self.db)],
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=ENV)
        process.stdout.close()
        process.stdout = None
        request = {'action': 'publish', 'operation_id': 'change-one', 'proposal': candidate()}
        try:
            process.communicate(input=(json.dumps(request)+'\n').encode(), timeout=15)
            self.assertNotEqual(process.returncode, 0)
            self.assertTrue((self.output/'change-one.bundle').exists())
            result = self.data('receipt', store=subject.Store(self.db))
            self.assertEqual(result['status'], 'completed')
            self.assertEqual(self.data('publish'), result)
            self.assertEqual(len(self.query('SELECT * FROM attempts')), 1)
        finally:
            if process.poll() is None:
                process.kill(); process.communicate(timeout=5)

    def test_git_output_bound_and_real_stalled_process(self):
        with tempfile.TemporaryDirectory(dir=self.root) as tools:
            git = Path(tools)/'git'
            git.write_text('#!'+sys.executable+'\nimport time\ntime.sleep(30)\n')
            git.chmod(0o700)
            started = time.monotonic()
            with mock.patch.dict(os.environ, {'PATH': tools+os.pathsep+os.environ['PATH']}):
                with self.assertRaises(subject.Refused):
                    subject.git(self.root, ['status'], time.monotonic()+.1, 32)
            self.assertLess(time.monotonic()-started, 2)
            git.write_text('#!'+sys.executable+'\nimport os\nos.write(1,b"x"*1024)\n')
            with mock.patch.dict(os.environ, {'PATH': tools+os.pathsep+os.environ['PATH']}):
                with self.assertRaises(subject.Refused):
                    subject.git(self.root, ['status'], time.monotonic()+5, 32)


if __name__ == '__main__':
    unittest.main()
