import copy
import io
import hashlib
import os
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import select
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'plugins/delivery/scripts'))
from delivery_gates import GateError, GateService
from runtime import Store
from operator_capture import CaptureAuthority, CaptureError, question_digest


class CanonicalBeads:
    """Explicit fake authority for deterministic failure tests, not live Beads proof."""
    def __init__(self):
        self.tasks = {'task-1': {'id': 'task-1', 'status': 'open', 'assignee': '',
                                'acceptance_criteria': 'Criterion A', 'dependencies': []}}
        self.claim_race = None
        self.close_calls = 0
        self.create_calls = 0

    def show(self, issue):
        return copy.deepcopy(self.tasks[issue])

    def close(self, issue, actor, reason):
        self.close_calls += 1
        self.tasks[issue].update(status='closed', close_reason=reason)

    def claim(self, issue, actor, operation):
        self.tasks[issue].update(status='in_progress', assignee=actor, notes='delivery-claim-op:'+operation)
        if self.claim_race:
            self.claim_race(self.tasks[issue])

    def find_source(self, key):
        return [copy.deepcopy(t) for t in self.tasks.values() if t.get('metadata', {}).get('delivery_source_key') == key]

    def create_story(self, title, body, criteria, metadata, actor):
        self.create_calls += 1
        task = {'id': 'created-1', 'title': title, 'description': body, 'acceptance_criteria': criteria,
                'metadata': metadata, 'status': 'open', 'assignee': ''}
        self.tasks[task['id']] = task
        return copy.deepcopy(task)


class DeliveryGatesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.planning = self.root/'planning'
        (self.planning/'.delivery').mkdir(parents=True)
        self.product = self.root/'product'
        self.product.mkdir()
        self.git('init', '-q')
        self.git('config', 'user.email', 'fixture@example.invalid')
        self.git('config', 'user.name', 'Fixture')
        (self.product/'code').write_text('first')
        self.git('add', 'code')
        self.git('commit', '-qm', 'fixture')
        self.store = Store(self.planning)
        self.actors = {}
        for name, lane, cwd in [('delivery-manager', 'read-only', self.planning),
                                ('builder', 'builder', self.product), ('reviewer', 'read-only', self.product)]:
            spec = json.dumps({'lane': lane, 'cwd': str(cwd)})
            self.store.db.execute("INSERT INTO roles VALUES(?,?,?,?,'active',0)", (name, spec, 'thread-'+name, 'turn-'+name))
            self.actors[name] = {'role': name, 'thread': 'thread-'+name, 'turn': 'turn-'+name, 'lane': lane}
        self.beads = CanonicalBeads()
        self.service = GateService(self.store, self.beads)
        self.surface = {'host': 'Codex', 'app': 'CLI', 'mode': 'local', 'criterion': 'Criterion A'}
        (self.product/'.delivery-evidence').mkdir(exist_ok=True)
        (self.product/'.delivery-evidence/test-output').write_text('fixture test output; exit code 0')
        (self.product/'.delivery-evidence/review-output').write_text('fixture independent inspection')
        (self.product/'.delivery-evidence/host-output').write_text('fixture observed host output')

    def tearDown(self):
        self.store.db.close()
        self.temp.cleanup()

    def git(self, *args):
        return subprocess.run(['git', '-C', str(self.product), *args], text=True, capture_output=True, check=True).stdout.strip()

    def call(self, action, who='delivery-manager', **args):
        return self.service.call('delivery_task_'+action, {'issue': 'task-1', **args}, self.actors[who])

    def ready(self, assumptions=None):
        return self.call('ready', surfaces=[self.surface], assumptions=assumptions or [])

    def claimed(self):
        self.ready()
        self.call('claim', 'builder')

    def implemented(self):
        self.claimed()
        self.call('implemented', 'builder', head=self.git('rev-parse', 'HEAD'), evidence=['.delivery-evidence/test-output'], passed=True)

    def reviewed(self):
        self.implemented()
        self.call('review', 'reviewer', head=self.git('rev-parse', 'HEAD'), evidence=['.delivery-evidence/review-output'], approved=True)

    def test_complete_submissions_never_grant_human_authority_or_close(self):
        self.reviewed()
        self.call('surface', 'reviewer', head=self.git('rev-parse', 'HEAD'), surface=self.surface,
                  evidence=['.delivery-evidence/host-output'], kind='real-host-observation')
        result = self.call('gate_status')
        self.assertTrue(result['submissions_complete'])
        self.assertFalse(result['accepted'])
        with self.assertRaisesRegex(GateError, 'Quiesce'):
            self.call('accept')
        self.store.db.execute("UPDATE roles SET phase='idle' WHERE name='builder'")
        prepared = self.call('accept')
        self.assertTrue(prepared['operator_capture_required'])
        with self.assertRaisesRegex(GateError, 'binding'):
            self.service.accept_from_operator('task-1', self.actors['delivery-manager'], {}, {}, CaptureAuthority())
        self.assertEqual(self.beads.tasks['task-1']['status'], 'in_progress')

    def acceptance_binding(self):
        self.reviewed()
        self.call('surface', 'reviewer', head=self.git('rev-parse', 'HEAD'), surface=self.surface,
                  evidence=['.delivery-evidence/host-output'], kind='real-host-observation')
        self.store.db.execute("UPDATE roles SET phase='idle',turn=NULL WHERE name='builder'")
        prepared = self.call('accept')
        actor = self.actors['delivery-manager']
        binding = {'request_id': 'gate-request', 'native_request_id': 'gate-1', 'thread_id': actor['thread'],
                   'turn_id': actor['turn'], 'method': 'delivery/gateAcceptance', 'item_id': 'gate-item',
                   'source_revision': prepared['scope']['head'], 'scope': prepared['scope'],
                   'question': prepared['question'], 'question_digest': question_digest(prepared['question'])}
        return binding

    def receipt(self, authority, binding, line='accept\n'):
        challenge = authority.challenge(binding)
        master, slave = os.openpty()
        terminal = io.TextIOWrapper(io.FileIO(slave, 'r+', closefd=True), encoding='utf-8', write_through=True)
        stop = threading.Event()
        def drain():
            while not stop.is_set():
                if select.select([master], [], [], 0.01)[0]:
                    try:
                        os.read(master, 65536)
                    except OSError:
                        return
        reader = threading.Thread(target=drain, daemon=True)
        reader.start()
        try:
            os.write(master, line.encode())
            return authority.capture_from_terminal(challenge, terminal=terminal)
        finally:
            stop.set()
            reader.join(1)
            terminal.close()
            os.close(master)

    def test_synthetic_pty_attestation_can_close_canonical_task_but_not_merge(self):
        binding = self.acceptance_binding()
        authority = CaptureAuthority()
        receipt = self.receipt(authority, binding)
        result = self.service.accept_from_operator('task-1', self.actors['delivery-manager'], binding, receipt, authority)
        self.assertTrue(result['accepted'])
        self.assertFalse(result['merge_authorized'])
        self.assertEqual(self.beads.tasks['task-1']['status'], 'closed')
        self.assertEqual(self.service.events('task-1')[-1]['operator_channel'], 'operator-terminal')
        with self.assertRaises(GateError):
            self.service.accept_from_operator('task-1', self.actors['delivery-manager'], binding, receipt, authority)

    def test_criteria_or_evidence_changes_while_operator_reads_refuse_close(self):
        binding = self.acceptance_binding()
        authority = CaptureAuthority()
        receipt = self.receipt(authority, binding)
        (self.product/'.delivery-evidence/host-output').write_text('changed during operator wait')
        with self.assertRaisesRegex(GateError, 'Evidence changed'):
            self.service.accept_from_operator('task-1', self.actors['delivery-manager'], binding, receipt, authority)
        self.assertEqual(self.beads.tasks['task-1']['status'], 'in_progress')

    def test_declined_or_forged_operator_receipt_never_closes(self):
        binding = self.acceptance_binding()
        authority = CaptureAuthority()
        with self.assertRaises(CaptureError):
            self.service.accept_from_operator('task-1', self.actors['delivery-manager'], binding,
                                            {'response': {'decision': 'accept'}}, authority)
        receipt = self.receipt(authority, binding, 'decline\n')
        with self.assertRaisesRegex(GateError, 'declined'):
            self.service.accept_from_operator('task-1', self.actors['delivery-manager'], binding, receipt, authority)
        self.assertEqual(self.beads.tasks['task-1']['status'], 'in_progress')

    def test_changed_criteria_invalidates_readiness_and_all_evidence(self):
        self.reviewed()
        self.beads.tasks['task-1']['acceptance_criteria'] = 'Criterion B'
        with self.assertRaisesRegex(GateError, 'Readiness missing or stale'):
            self.call('gate_status')

    def test_new_commit_invalidates_old_implementation_and_review(self):
        self.reviewed()
        (self.product/'code').write_text('second')
        self.git('commit', '-am', 'second', '-q')
        with self.assertRaisesRegex(GateError, 'implementation'):
            self.call('gate_status')

    def test_dirty_tracked_product_cannot_reuse_head_evidence(self):
        self.implemented()
        (self.product/'code').write_text('uncommitted')
        with self.assertRaisesRegex(GateError, 'not committed'):
            self.call('review', 'reviewer', head=self.git('rev-parse', 'HEAD'), evidence=['.delivery-evidence/review-output'], approved=True)

    def test_self_review_and_thread_alias_are_refused(self):
        self.implemented()
        with self.assertRaisesRegex(GateError, 'Independent'):
            self.call('review', 'builder', head=self.git('rev-parse', 'HEAD'), evidence=['.delivery-evidence/review-output'], approved=True)

    def test_wrong_surface_and_stub_observations_are_refused(self):
        self.reviewed()
        for surface, kind in [(dict(self.surface, app='desktop'), 'real-host-observation'), (self.surface, 'stub')]:
            with self.assertRaisesRegex(GateError, 'Wrong declared surface'):
                self.call('surface', 'reviewer', head=self.git('rev-parse', 'HEAD'), surface=surface, evidence=['.delivery-evidence/host-output'], kind=kind)

    def test_changed_or_deleted_evidence_invalidates_review(self):
        self.reviewed()
        (self.product/'.delivery-evidence/test-output').write_text('tampered')
        with self.assertRaisesRegex(GateError, 'Evidence changed'):
            self.call('gate_status')

    def test_bound_actor_cannot_spoof_model_actor_or_stale_turn(self):
        self.ready()
        with self.assertRaisesRegex(GateError, 'Unexpected'):
            self.call('claim', 'builder', actor='delivery-manager')
        self.actors['builder']['turn'] = 'old-turn'
        with self.assertRaisesRegex(GateError, 'binding mismatch'):
            self.call('claim', 'builder')

    def test_manager_cannot_claim_and_existing_claim_cannot_be_overwritten(self):
        self.ready()
        with self.assertRaisesRegex(GateError, 'builder lane'):
            self.call('claim')
        self.call('claim', 'builder')
        with self.assertRaisesRegex(GateError, 'unclaimed builder lane'):
            self.call('claim', 'builder')

    def test_closed_or_reassigned_beads_task_invalidates_bound_claim(self):
        self.claimed()
        self.beads.tasks['task-1']['assignee'] = 'somebody-else'
        with self.assertRaisesRegex(GateError, 'canonical bound claim'):
            self.call('implemented', 'builder', head=self.git('rev-parse', 'HEAD'), evidence=['.delivery-evidence/test-output'], passed=True)

    def test_dependency_status_is_live_not_cached(self):
        self.ready()
        self.beads.tasks['dep-1'] = {'id': 'dep-1', 'status': 'open'}
        self.beads.tasks['task-1']['dependencies'] = [{'id': 'dep-1', 'dependency_type': 'blocks'}]
        with self.assertRaisesRegex(GateError, 'Unresolved blocking'):
            self.call('claim', 'builder')

    def test_claim_race_is_detected_without_inventing_rollback_or_seal(self):
        self.ready()
        self.beads.claim_race = lambda task: task.update(acceptance_criteria='raced criteria')
        with self.assertRaisesRegex(GateError, 'claim raced'):
            self.call('claim', 'builder')
        self.assertFalse(any(e['action'] == 'claim' for e in self.service.events('task-1')))
        self.assertEqual(self.beads.tasks['task-1']['status'], 'in_progress')

    def test_failed_implementation_and_review_are_preserved_and_block(self):
        self.claimed()
        self.call('implemented', 'builder', head=self.git('rev-parse', 'HEAD'), evidence=['.delivery-evidence/test-output'], passed=False)
        with self.assertRaisesRegex(GateError, 'passing implementation'):
            self.call('review', 'reviewer', head=self.git('rev-parse', 'HEAD'), evidence=['.delivery-evidence/review-output'], approved=True)
        self.assertFalse(self.service.events('task-1')[-1]['passed'])

    def test_assumption_evidence_cannot_be_changed_after_ready(self):
        evidence = self.planning/'assumption'
        evidence.write_text('real-host spike transcript fixture')
        self.ready([{'statement': 'Host supports mode', 'evidence': [str(evidence)]}])
        evidence.write_text('changed')
        with self.assertRaisesRegex(GateError, 'Evidence changed'):
            self.call('claim', 'builder')

    def test_same_head_reimplementation_invalidates_previous_review(self):
        self.reviewed()
        self.call('implemented', 'builder', head=self.git('rev-parse', 'HEAD'), evidence=['.delivery-evidence/test-output'], passed=True)
        with self.assertRaisesRegex(GateError, 'independent approval'):
            self.call('gate_status')

    def test_rereadiness_preserves_claim_only_with_explicit_reason_and_quiescent_builder(self):
        self.implemented()
        self.beads.tasks['task-1']['acceptance_criteria'] = 'Changed criterion'
        with self.assertRaisesRegex(GateError, 'Quiesce'):
            self.call('reready', surfaces=[dict(self.surface, criterion='Changed criterion')], assumptions=[], reason='Criteria corrected')
        self.store.db.execute("UPDATE roles SET phase='idle',turn=NULL WHERE name='builder'")
        self.call('reready', surfaces=[dict(self.surface, criterion='Changed criterion')], assumptions=[], reason='Criteria corrected')
        with self.assertRaisesRegex(GateError, 'implementation'):
            self.call('gate_status')
        self.store.db.execute("UPDATE roles SET phase='active',turn='turn-builder' WHERE name='builder'")
        result = self.call('implemented', 'builder', head=self.git('rev-parse', 'HEAD'),
                           evidence=['.delivery-evidence/test-output'], passed=True)
        self.assertEqual(result['actor']['role'], 'builder')
        self.assertEqual(self.beads.tasks['task-1']['assignee'], 'builder')

    def test_untracked_product_input_cannot_reuse_commit_seal(self):
        self.implemented()
        (self.product/'untracked-code.py').write_text('print("uncommitted executable")')
        with self.assertRaisesRegex(GateError, 'not committed'):
            self.call('review', 'reviewer', head=self.git('rev-parse', 'HEAD'),
                      evidence=['.delivery-evidence/review-output'], approved=True)

    def test_readiness_cannot_drop_a_canonical_criterion(self):
        self.beads.tasks['task-1']['acceptance_criteria'] = '- Criterion A\n- Criterion B'
        with self.assertRaisesRegex(GateError, 'every exact canonical criterion'):
            self.ready()

    def test_read_only_reviewer_uses_only_exact_actor_protected_artifact(self):
        self.implemented()
        reviews = self.store.root.parent/'reviews'
        reviews.mkdir()
        note = reviews/'independent.md'
        note.write_text('Independent fixture inspection')
        sha = hashlib.sha256(note.read_bytes()).hexdigest()
        args = {'head': self.git('rev-parse', 'HEAD'), 'evidence': [str(note)], 'approved': True}
        with self.assertRaisesRegex(GateError, 'author/thread'):
            self.call('review', 'reviewer', **args)
        self.store.event('artifact_saved', {'path': str(note), 'sha256': sha,
                                          'actor': dict(self.actors['reviewer'], thread='other-thread')})
        with self.assertRaisesRegex(GateError, 'author/thread'):
            self.call('review', 'reviewer', **args)
        self.store.event('artifact_saved', {'path': str(note), 'sha256': sha, 'actor': self.actors['reviewer']})
        self.store.db.execute("UPDATE roles SET turn='resumed-review-turn' WHERE name='reviewer'")
        self.actors['reviewer']['turn'] = 'resumed-review-turn'
        result = self.call('review', 'reviewer', **args)
        self.assertIn('artifact_event_id', result['evidence'][0])
        self.assertEqual(result['evidence'][0]['artifact_origin']['turn'], 'turn-reviewer')
        self.store.event('artifact_saved', {'path': str(note), 'sha256': sha, 'actor': self.actors['reviewer']})
        with self.assertRaisesRegex(GateError, 'provenance changed'):
            self.call('gate_status')

    def story(self):
        directory = self.store.root.parent/'stories'
        directory.mkdir(exist_ok=True)
        path = directory/'fixture.md'
        body = '# Make a fixture useful\n\n## Goal\nVisible outcome.\n\n## Acceptance criteria\nCriterion A\n\n## Out of scope\nNothing extra.\n'
        path.write_text(body)
        self.store.event('artifact_saved', {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                                          'actor': self.actors['delivery-manager']})
        return path, body

    def test_materialize_creates_only_one_draft_from_exact_canonical_bytes(self):
        path, body = self.story()
        args = {'path': 'stories/fixture.md'}
        result = self.service.call('delivery_task_materialize', args, self.actors['delivery-manager'])
        self.assertFalse(result['readiness_granted'])
        self.assertEqual(self.beads.tasks[result['issue']]['description'], body)
        self.assertEqual(self.beads.tasks[result['issue']]['acceptance_criteria'], 'Criterion A')
        again = self.service.call('delivery_task_materialize', args, self.actors['delivery-manager'])
        self.assertTrue(again['reused'])
        self.assertEqual(self.beads.create_calls, 1)
        with self.assertRaisesRegex(GateError, 'delivery manager'):
            self.service.call('delivery_task_materialize', args, self.actors['reviewer'])
        path.write_text(body+'Changed')
        with self.assertRaisesRegex(GateError, 'provenance'):
            self.service.call('delivery_task_materialize', args, self.actors['delivery-manager'])

    def test_ambiguous_create_is_not_blindly_replayed(self):
        self.story()
        def ambiguous(*args):
            self.beads.create_calls += 1
            raise TimeoutError('Synthetic unknown external create')
        self.beads.create_story = ambiguous
        args = {'path': 'stories/fixture.md'}
        result = self.service.call('delivery_task_materialize', args, self.actors['delivery-manager'])
        self.assertIn('unknown', result['outcome'])
        again = GateService(self.store, self.beads).call('delivery_task_materialize', args, self.actors['delivery-manager'])
        self.assertIn('unknown', again['outcome'])
        self.assertEqual(self.beads.create_calls, 1)

    def test_close_success_then_event_failure_leaves_durable_authorized_intent(self):
        binding = self.acceptance_binding()
        authority = CaptureAuthority()
        receipt = self.receipt(authority, binding)
        original = self.store.event
        def fail(kind, data):
            if data.get('action') == 'accepted':
                raise ValueError('Synthetic SQLite outcome write failure')
            return original(kind, data)
        self.store.event = fail
        with self.assertRaisesRegex(ValueError, 'Synthetic SQLite'):
            self.service.accept_from_operator('task-1', self.actors['delivery-manager'], binding, receipt, authority)
        self.store.event = original
        self.assertEqual(self.beads.tasks['task-1']['status'], 'closed')
        self.assertTrue(any(e['action'] == 'accept_intent' and e['receipt_sha256'] for e in self.service.events('task-1')))
        result = GateService(self.store, self.beads).reconcile_effects()
        self.assertEqual(result[0]['outcome'], 'confirmed-applied')
        self.assertFalse(result[0]['replayed'])
        self.assertEqual(self.beads.close_calls, 1)

    def test_claim_success_then_event_failure_can_reconcile_without_reclaim(self):
        self.ready()
        original = self.store.event
        def fail(kind, data):
            if data.get('action') == 'claim':
                raise ValueError('Synthetic claim outcome write failure')
            return original(kind, data)
        self.store.event = fail
        with self.assertRaisesRegex(ValueError, 'Synthetic claim'):
            self.call('claim', 'builder')
        self.store.event = original
        result = GateService(self.store, self.beads).reconcile_effects()
        self.assertEqual(result[0]['outcome'], 'confirmed-applied')
        self.assertTrue(self.service.events('task-1')[-2]['recovered'])
        self.call('implemented', 'builder', head=self.git('rev-parse', 'HEAD'),
                  evidence=['.delivery-evidence/test-output'], passed=True)

    def test_unknown_claim_outcome_does_not_allow_automatic_effect_retry(self):
        self.ready()
        calls = []
        def unknown(*args):
            calls.append(args)
            raise TimeoutError('Synthetic unobservable claim outcome')
        self.beads.claim = unknown
        with self.assertRaises(TimeoutError):
            self.call('claim', 'builder')
        with self.assertRaisesRegex(GateError, 'do not retry'):
            self.call('claim', 'builder')
        self.assertEqual(len(calls), 1)
        self.assertEqual(self.service.reconcile_effects()[0]['outcome'], 'unknown-requires-operator-reconcile')

    def test_materialize_reuse_refuses_canonical_title_or_criteria_drift(self):
        self.story()
        args = {'path': 'stories/fixture.md'}
        result = self.service.call('delivery_task_materialize', args, self.actors['delivery-manager'])
        task = self.beads.tasks[result['issue']]
        original_title, original_criteria = task['title'], task['acceptance_criteria']
        for field, value in [('title', 'Externally changed title'), ('acceptance_criteria', 'Externally changed criterion')]:
            task.update(title=original_title, acceptance_criteria=original_criteria)
            task[field] = value
            with self.assertRaisesRegex(GateError, 'explicitly realign'):
                self.service.call('delivery_task_materialize', args, self.actors['delivery-manager'])
        self.assertEqual(self.beads.create_calls, 1)

    def test_head_inspection_does_not_execute_repository_fsmonitor_helper(self):
        marker = self.root/'coordinator-safe-marker'
        helper = self.product/'monitor-helper'
        helper.write_text('#!/bin/sh\nprintf safe-marker > "'+str(marker)+'"\nprintf "token\\0"\n')
        helper.chmod(0o700)
        self.git('add', 'monitor-helper')
        self.git('commit', '-qm', 'Tracked fixture helper')
        expected = self.git('rev-parse', 'HEAD')
        self.git('config', 'core.fsmonitor', str(helper))
        self.assertEqual(self.service.head(str(self.product)), expected)
        self.assertFalse(marker.exists(), 'Coordinator inspection executed repository-configured code')
        self.assertEqual(self.git('config', 'core.fsmonitor'), str(helper), 'Inspection changed repository config')

    def test_assume_unchanged_and_skip_worktree_cannot_hide_dirty_product_bytes(self):
        for enable, disable in [('--assume-unchanged', '--no-assume-unchanged'), ('--skip-worktree', '--no-skip-worktree')]:
            self.git('update-index', enable, 'code')
            (self.product/'code').write_text('other')
            self.assertEqual(self.git('status', '--porcelain', '--untracked-files=no'), '')
            with self.assertRaisesRegex(GateError, 'index hides tracked bytes'):
                self.service.head(str(self.product))
            self.git('update-index', disable, 'code')
            (self.product/'code').write_text('first')

    def test_tracked_byte_hashing_ignores_clean_index_stat_cache(self):
        self.git('config', 'core.trustctime', 'false')
        self.git('config', 'core.checkStat', 'minimal')
        old = 1_600_000_000_000_000_000
        os.utime(self.product/'code', ns=(old, old))
        self.git('update-index', '--refresh')
        (self.product/'code').write_text('other')
        os.utime(self.product/'code', ns=(old, old))
        self.assertEqual(self.git('status', '--porcelain', '--untracked-files=no'), '')
        with self.assertRaisesRegex(GateError, 'raw bytes differ'):
            self.service.head(str(self.product))

    def test_raw_hash_inspection_never_executes_repository_clean_filter(self):
        marker = self.root/'filter-safe-marker'
        helper = self.product/'clean-helper'
        helper.write_text('#!/bin/sh\nprintf touched > "'+str(marker)+'"\ncat\n')
        helper.chmod(0o700)
        (self.product/'.gitattributes').write_text('code filter=fixture\n')
        self.git('add', 'clean-helper', '.gitattributes')
        self.git('commit', '-qm', 'Fixture attributes')
        expected = self.git('rev-parse', 'HEAD')
        self.git('config', 'filter.fixture.clean', str(helper))
        self.git('config', 'filter.fixture.smudge', str(helper))
        # Same bytes, changed stat cache: ordinary status may clean-filter this
        # to refresh its index. Coordinator inspection must not convert bytes.
        (self.product/'code').write_text('first')
        self.assertEqual(self.service.head(str(self.product)), expected)
        self.assertFalse(marker.exists(), 'Coordinator executed repository clean/smudge filter')

    def test_committed_file_executable_mode_or_parent_symlink_is_refused(self):
        (self.product/'code').chmod(0o755)
        with self.assertRaisesRegex(GateError, 'executable mode'):
            self.service.head(str(self.product))
        (self.product/'code').chmod(0o644)
        directory = self.product/'nested'
        directory.mkdir()
        (directory/'data').write_text('fixture')
        self.git('add', 'nested/data')
        self.git('commit', '-qm', 'Nested fixture')
        other = self.root/'outside'
        other.mkdir()
        (other/'data').write_text('fixture')
        (directory/'data').unlink()
        directory.rmdir()
        directory.symlink_to(other, target_is_directory=True)
        with self.assertRaisesRegex(GateError, 'parent became a symlink'):
            self.service.head(str(self.product))

    def test_staged_extra_product_file_cannot_hide_behind_raw_head_check(self):
        (self.product/'staged-extra').write_text('fixture')
        self.git('add', 'staged-extra')
        with self.assertRaisesRegex(GateError, 'Staged product changes'):
            self.service.head(str(self.product))

    def test_unknown_dependency_type_fails_closed(self):
        self.beads.tasks['task-1']['dependencies'] = [{'id': 'x', 'dependency_type': 'mystery'}]
        with self.assertRaisesRegex(GateError, 'Unknown dependency'):
            self.ready()


if __name__ == '__main__':
    unittest.main()
