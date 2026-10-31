"""Synthetic CLI cases: source freshness cannot establish assessment scope."""
import copy
import hashlib
import json
import unittest
import test_product as fixtures
P = fixtures.P


class AssessmentScopeTests(unittest.TestCase):
    setUp = fixtures.ProductTests.setUp
    tearDown = fixtures.ProductTests.tearDown
    git = fixtures.ProductTests.git
    data = fixtures.ProductTests.data
    run_cli = fixtures.ProductTests.run_cli

    def record_cli(self, data, expected='new', repo=True):
        path = self.root/'input.json'; path.write_text(json.dumps(data))
        return self.run_cli('record','--input',str(path),'--expected-sha256',expected,repo=repo)

    def handoff(self, *args, repo=True):
        result = self.run_cli('handoff',*args,repo=repo)
        self.assertIn(result.returncode,(0,1),result.stderr)
        self.assertFalse(result.stderr,result.stderr)
        return json.loads(result.stdout)

    def scope(self, data, applicability='current', repo=True):
        report = self.handoff(repo=repo)
        data['product']['assessment_scope'] = {'applicability':applicability,
            'context':'Synthetic bird-feeder reminder assessment', 'source':'Synthetic feeder schedule note',
            'reviewed_sha256':report['assessment']['review_sha256']}
        result = self.record_cli(data,report['map_sha256'],repo=repo)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_fresh_legacy_stale_direction_is_unscoped_without_rewriting(self):
        data=self.data();data['product']['right_shape']['benchmark']='Current: ring a chime when the bird-feeder tray is empty.'
        data['product']['customer']['basis']='owner-stated'
        self.assertEqual(self.record_cli(data).returncode,0)
        before=P.map_path(self.project).read_bytes()
        full=self.handoff();selected=self.handoff('--feature','feature-a')
        self.assertTrue(full['freshness']['fresh'])
        self.assertEqual(full['assessment']['applicability'],'unscoped')
        self.assertTrue(full['assessment']['reconcile_required'])
        self.assertEqual(full['assessment']['semantic_alignment'],'unverified')
        self.assertEqual(full['assessment'],selected['assessment'])
        self.assertEqual(full['product'],data['product'])
        self.assertEqual(P.map_path(self.project).read_bytes(),before)

    def test_explicit_current_preserves_owner_choices_history_and_global_output(self):
        data=self.data();data['product']['customer']['basis']='owner-stated'
        self.assertEqual(self.record_cli(data).returncode,0)
        before=P.map_path(self.project).read_bytes();original=copy.deepcopy(data['product'])
        self.scope(data)
        full=self.handoff();selected=self.handoff('--feature','feature-a')
        self.assertEqual(full['assessment'],selected['assessment'])
        self.assertEqual(full['assessment']['applicability'],'current')
        self.assertFalse(full['assessment']['reconcile_required'])
        self.assertEqual(full['assessment']['semantic_alignment'],'unverified')
        self.assertEqual({k:v for k,v in full['product'].items() if k!='assessment_scope'},original)
        history=P.map_path(self.project).parent/'product-map-history'/ (hashlib.sha256(before).hexdigest()+'.json')
        self.assertEqual(history.read_bytes(),before)
        self.assertEqual(full['features'][0]['usefulness'],data['features'][0]['usefulness'])

    def test_historical_and_unknown_do_not_become_current_from_keywords(self):
        for status in ('historical','unknown'):
            with self.subTest(status=status):
                data=self.data();data['product']['right_shape']['reason']='CURRENT approved bird-feeder chime schedule!'
                expected=self.handoff()['map_sha256'] if P.map_path(self.project).exists() else 'new'
                self.assertEqual(self.record_cli(data,expected).returncode,0)
                self.scope(data,status)
                result=self.handoff()['assessment']
                self.assertEqual(result['applicability'],status)
                self.assertTrue(result['reconcile_required'])

    def test_changed_direction_and_source_revision_invalidate_binding(self):
        data=self.data();self.assertEqual(self.record_cli(data).returncode,0);self.scope(data)
        for change in ('direction','source'):
            with self.subTest(change=change):
                self.scope(data)
                self.assertEqual(self.handoff()['assessment']['applicability'],'current')
                if change=='direction':data['product']['next_slice']['text']='Synthetic reminder to refill the bird feeder at noon'
                else:
                    (self.repo/'README.md').write_text('Synthetic newer source\n')
                    self.git('add','.');self.git('commit','-qm','Synthetic revision')
                    data['commit']=self.git('rev-parse','HEAD').strip()
                expected=self.handoff()['map_sha256']
                self.assertEqual(self.record_cli(data,expected).returncode,0)
                result=self.handoff()
                self.assertTrue(result['freshness']['fresh'])
                self.assertEqual(result['assessment']['applicability'],'stale')
                self.assertTrue(result['assessment']['reconcile_required'])

    def test_dirty_source_requires_reconciliation_even_with_matching_declaration(self):
        data=self.data();self.assertEqual(self.record_cli(data).returncode,0);self.scope(data)
        (self.repo/'a.py').write_text('changed mapped file')
        result=self.handoff()
        self.assertFalse(result['freshness']['fresh'])
        self.assertTrue(result['assessment']['binding_matches'])
        self.assertTrue(result['assessment']['reconcile_required'])

    def test_malformed_scope_refuses_before_record_or_history_changes(self):
        data=self.data();self.assertEqual(self.record_cli(data).returncode,0)
        before=P.map_path(self.project).read_bytes();expected=hashlib.sha256(before).hexdigest()
        good={'applicability':'current','context':'Synthetic','source':'Fixture','reviewed_sha256':'a'*64}
        bad=[None,{},dict(good,extra=True),dict(good,applicability=True),dict(good,context=''),
             dict(good,source=[]),dict(good,reviewed_sha256='A'*64),dict(good,reviewed_sha256=1)]
        for scope in bad:
            with self.subTest(scope=scope):
                data['product']['assessment_scope']=scope
                result=self.record_cli(data,expected)
                self.assertNotEqual(result.returncode,0)
                self.assertEqual(P.map_path(self.project).read_bytes(),before)
                self.assertFalse((P.map_path(self.project).parent/'product-map-history').exists())

    def test_greenfield_scope_has_no_invented_source_or_semantic_acceptance(self):
        data=copy.deepcopy(self.starter)
        self.assertEqual(self.record_cli(data,repo=False).returncode,0)
        self.scope(data,repo=False)
        result=self.handoff(repo=False)
        self.assertIsNone(result['freshness']['fresh'])
        self.assertEqual(result['assessment']['applicability'],'current')
        self.assertEqual(result['assessment']['semantic_alignment'],'unverified')
        self.assertIsNone(data['commit'])


if __name__=='__main__':unittest.main()
