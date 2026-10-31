"""Synthetic contract tests; no real destination, private input or model calls."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import importlib.util
from pathlib import Path
import sys
import unittest

SCRIPTS = Path(__file__).resolve().parents[2] / 'plugins/delivery/scripts'
spec = importlib.util.spec_from_file_location('publication', SCRIPTS / 'publication.py')
publication = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = publication
spec.loader.exec_module(publication)
Publisher, Destination, Blocked = publication.Publisher, publication.Destination, publication.Blocked

SAFE = b'SYNTHETIC: Fixed the sample counter. Usage: increment once.'
PROTECTED = b'SYNTHETIC PRIVATE: Violet robots launch on moon seven.'


class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.now = 10.0
        self.dest = Destination('fixture-product', 'fixture-owner', 'fixture-users', 'public', 'v1', 'auth1', 'policy1')
        self.allowed = True
        self.policy = lambda payload, operation, dest: payload == SAFE
        self.observed = []
        self.verify = lambda operation, identity: self.dest
        self.authorize = lambda payload, operation, dest: self.allowed and operation == 'comment'
        self.sender = self.send
        self.gate = self.make_gate()

    def send(self, payload, operation, destination):
        # Synthetic atomic compare-and-effect: no callback/yield between these steps.
        # Real adapters need a transaction with equivalent whole-binding semantics.
        if destination != self.dest:
            return False
        self.observed.append((payload, operation, destination))
        return True

    def make_gate(self, **options):
        return Publisher(routes=frozenset({('comment', 'fixture-product')}),
                         verify=lambda *a: self.verify(*a),
                         authorize=lambda *a: self.authorize(*a),
                         classify=lambda *a: self.policy(*a),
                         send=lambda *a: self.sender(*a), clock=lambda: self.now, **options)

    def prepare(self, gate=None):
        return (gate or self.gate).prepare(SAFE, 'comment', self.dest.identity)

    def dispatch(self, ticket, gate=None, **changes):
        args = dict(payload=SAFE, operation='comment', destination_id=self.dest.identity)
        args.update(changes)
        return (gate or self.gate).dispatch(ticket, **args).status

    def test_safe_correction_after_all_synthetic_private_forms(self):
        corpus = [PROTECTED, b'renamed.txt\n' + PROTECTED, b'log: ' + PROTECTED,
                  b'SYNTHETIC: Purple automatons debut on the seventh moon.',
                  b'VmlvbGV0IHJvYm90cw==', SAFE + b'\n' + PROTECTED]
        # Exact allowlist tests enforcement wiring, not general semantic detection.
        for payload in corpus:
            with self.subTest(payload=payload), self.assertRaisesRegex(Blocked, '^Publication blocked$'):
                self.gate.prepare(payload, 'comment', self.dest.identity)
        self.assertEqual(self.observed, [])
        self.assertEqual(self.dispatch(self.prepare()), 'completed')
        self.assertEqual(self.observed, [(SAFE, 'comment', self.dest)])

    def test_all_payload_surfaces_are_bytes_not_safe_filenames(self):
        for surface in ('code', 'code-comment', 'commit-message', 'pr-description',
                        'issue-description', 'review-comment', 'log', 'artifact',
                        'documentation', 'support-reply'):
            with self.subTest(surface=surface), self.assertRaises(Blocked):
                self.gate.prepare(surface.encode() + b'\n' + PROTECTED, 'comment', self.dest.identity)
        self.assertEqual(self.observed, [])

    def test_safe_usage_fix_and_support_policy(self):
        allowed = [SAFE, b'SYNTHETIC usage: run sample --help.',
                   b'SYNTHETIC support: the counter requires an integer.']
        self.policy = lambda p, o, d: p in allowed
        for payload in allowed:
            t = self.gate.prepare(payload, 'comment', self.dest.identity)
            self.assertEqual(self.dispatch(t, payload=payload), 'completed')
        self.assertEqual([r[0] for r in self.observed], allowed)

    def test_changed_candidate_operation_and_destination(self):
        for change in ({'payload': SAFE+b'!'}, {'operation': 'commit'}, {'destination_id': 'other'}):
            ticket = self.prepare()
            self.assertEqual(self.dispatch(ticket, **change), 'blocked')
            self.assertEqual(self.dispatch(ticket), 'blocked')
        self.assertEqual(self.observed, [])

    def test_every_destination_field_is_bound(self):
        original = self.dest
        for field, value in [('owner','other'), ('audience','others'), ('visibility','private'),
                             ('revision','v2'), ('identity','other'),
                             ('authority_revision','auth2'), ('policy_revision','policy2')]:
            self.dest = original
            ticket = self.prepare()
            self.dest = replace(original, **{field:value})
            self.assertEqual(self.dispatch(ticket), 'blocked')
        self.assertEqual(self.observed, [])

    def test_private_but_wrong_audience(self):
        self.dest = replace(self.dest, visibility='private', audience='unrelated-users')
        self.authorize = lambda p, o, d: d.audience == 'fixture-users'
        with self.assertRaises(Blocked): self.prepare()
        self.assertEqual(self.observed, [])

    def test_permission_and_policy_rechecked(self):
        ticket = self.prepare()
        self.allowed = False
        self.assertEqual(self.dispatch(ticket), 'blocked')
        self.allowed = True
        ticket = self.prepare()
        self.policy = lambda *a: False
        self.assertEqual(self.dispatch(ticket), 'blocked')
        self.assertEqual(self.observed, [])

    def test_checks_fail_closed_and_do_not_echo_diagnostics(self):
        def failure(*a): raise TimeoutError(PROTECTED.decode())
        for callback in ('verify', 'authorize', 'policy'):
            original = getattr(self, callback)
            for value in (None, False, 1, 'true', {}, failure):
                setattr(self, callback, value if callable(value) else lambda *a, v=value: v)
                with self.subTest(callback=callback, value=value), self.assertRaises(Blocked) as caught:
                    self.prepare()
                self.assertEqual(str(caught.exception), 'Publication blocked')
                setattr(self, callback, original)
                ticket = self.prepare()
                setattr(self, callback, value if callable(value) else lambda *a, v=value: v)
                self.assertEqual(self.dispatch(ticket), 'blocked')
            setattr(self, callback, original)
        self.assertEqual(self.observed, [])

    def test_invalid_destination_evidence(self):
        for change in ({'audience':''}, {'visibility':'unknown'}, {'revision':None}, {'owner':True}):
            dest = replace(self.dest, **change)
            self.verify = lambda *a: dest
            with self.assertRaises(Blocked): self.prepare()
        self.assertEqual(self.observed, [])

    def test_ticket_lifetime_and_bad_clock(self):
        for after in (40.0, 41.0, 9.0, float('nan'), float('inf'), True):
            self.now = 10.0
            ticket = self.prepare()
            self.now = after
            self.assertEqual(self.dispatch(ticket), 'blocked')
        self.assertEqual(self.observed, [])

    def test_checks_cannot_outlive_ticket(self):
        ticket = self.prepare()
        def delayed(*a):
            self.now += 31
            return True
        self.policy = delayed
        self.assertEqual(self.dispatch(ticket), 'blocked')
        with self.assertRaises(Blocked): self.prepare()
        self.assertEqual(self.observed, [])

    def test_foreign_forged_and_duplicate_tickets(self):
        ticket = self.prepare()
        other = self.make_gate()
        for invalid in (object(), 'approved', {}, None):
            self.assertEqual(self.dispatch(invalid), 'blocked')
        self.assertEqual(self.dispatch(ticket, gate=other), 'blocked')
        self.assertEqual(self.dispatch(ticket), 'completed')
        self.assertEqual(self.dispatch(ticket), 'blocked')
        self.assertEqual(len(self.observed), 1)

    def test_concurrent_duplicate_dispatch_sends_once(self):
        ticket = self.prepare()
        with ThreadPoolExecutor(max_workers=8) as pool:
            states = list(pool.map(lambda _: self.dispatch(ticket), range(16)))
        self.assertEqual(states.count('completed'), 1)
        self.assertEqual(states.count('blocked'), 15)
        self.assertEqual(len(self.observed), 1)

    def test_unknown_completion_quarantines_new_and_existing_tickets(self):
        def uncertain(*args):
            self.observed.append(args)
            raise TimeoutError(PROTECTED.decode())
        self.sender = uncertain
        first, second = self.prepare(), self.prepare()
        self.assertEqual(self.dispatch(first), 'unknown')
        self.assertEqual(self.dispatch(first), 'blocked')
        self.assertEqual(self.dispatch(second), 'blocked')
        with self.assertRaises(Blocked): self.prepare()
        self.assertEqual(len(self.observed), 1)

    def test_sink_malformed_receipts_are_unknown(self):
        for value in (None, False, 'completed', 1, {}):
            gate = self.make_gate()
            self.sender = lambda *a: value
            self.assertEqual(self.dispatch(self.prepare(gate), gate=gate), 'unknown')
            with self.assertRaises(Blocked): self.prepare(gate)

    def test_adapter_enforces_destination_race_at_effect(self):
        def racing_send(payload, operation, destination):
            self.dest = replace(self.dest, revision='changed-after-check')
            return self.send(payload, operation, destination)
        self.sender = racing_send
        self.assertEqual(self.dispatch(self.prepare()), 'unknown')
        self.assertEqual(self.observed, [])

    def test_authority_revoked_during_classification_cannot_send(self):
        ticket = self.prepare()
        def revoke(*args):
            self.allowed = False
            self.dest = replace(self.dest, authority_revision='auth2')
            return True
        self.policy = revoke
        self.assertEqual(self.dispatch(ticket), 'unknown')
        self.assertFalse(self.allowed)
        self.assertEqual(self.observed, [])

    def test_authority_and_policy_race_after_all_prechecks(self):
        for field in ('authority_revision', 'policy_revision'):
            self.setUp()
            def racing_send(payload, operation, binding):
                self.dest = replace(self.dest, **{field:'revoked'})
                return self.send(payload, operation, binding)
            self.sender = racing_send
            self.assertEqual(self.dispatch(self.prepare()), 'unknown')
            self.assertEqual(self.observed, [])

    def test_exact_limit_and_input_types(self):
        self.policy = lambda *a: True
        payload = b'x' * 1_048_576
        t = self.gate.prepare(payload, 'comment', self.dest.identity)
        self.assertEqual(self.dispatch(t, payload=payload), 'completed')
        for bad in (b'', payload+b'x', bytearray(SAFE), SAFE.decode(), None):
            with self.assertRaises(Blocked): self.gate.prepare(bad, 'comment', self.dest.identity)
        self.assertEqual(len(self.observed), 1)

    def test_required_callbacks_and_limits(self):
        for opts in ({'ttl':float('nan')}, {'ttl':0}, {'ttl':True}, {'max_bytes':0}, {'max_bytes':True}):
            with self.assertRaises(ValueError): self.make_gate(**opts)
        with self.assertRaises(ValueError):
            Publisher(routes=frozenset({('comment','fixture-product')}), verify=None,
                      authorize=lambda *a:True, classify=lambda *a:True, send=lambda *a:True)

    def test_unregistered_identifiers_never_reach_resolver(self):
        observed = []
        self.verify = lambda *args: observed.append(args)
        for operation, destination in [('comment', 'synthetic-private-fact'),
                                        ('synthetic-private-fact', 'fixture-product'),
                                        ('comment', 'https://example.invalid/private'),
                                        ('comment', 'fixture-product?secret=synthetic')]:
            with self.assertRaises(Blocked): self.gate.prepare(SAFE, operation, destination)
        self.assertEqual(observed, [])

    def test_pending_grants_bounded_and_expired_entries_retired(self):
        tickets = [self.prepare() for _ in range(64)]
        with self.assertRaises(Blocked): self.prepare()
        self.now += 31
        self.assertEqual(self.dispatch(tickets[0]), 'blocked')
        self.assertEqual(self.dispatch(self.prepare()), 'completed')


if __name__ == '__main__':
    unittest.main()
