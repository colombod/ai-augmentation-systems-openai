"""Synthetic fixture retirements only; decision references authenticate nobody."""
import copy
import json
import unittest
import test_product as fixtures
P = fixtures.P


class RetirementTests(unittest.TestCase):
    setUp = fixtures.ProductTests.setUp
    tearDown = fixtures.ProductTests.tearDown
    git = fixtures.ProductTests.git
    data = fixtures.ProductTests.data
    record = fixtures.ProductTests.record
    run_cli = fixtures.ProductTests.run_cli
    def outcome(self):
        return dict(commit=self.git('rev-parse','HEAD').strip(),
            decision_ref='SYNTHETIC OWNER REF fixture-04; not authenticated',
            usage_review='Fixture use only; Return remains Unknown.',
            replacement='Synthetic explicit none; fixture capability removed.',
            migration='Synthetic fixture has no user data; external consumers unknown.',
            rollback='Restore previous fixture commit; prior baseline retained.',
            consumer_review='Shared survivor preserved; external/dynamic consumers remain unknown.',
            evidence=[dict(path='outcome.md',note='Synthetic completion observation, not independent review or adoption.')])

    def complete_source(self, remove=('a.py',)):
        for path in remove:
            (self.repo/path).unlink()
        (self.repo/'outcome.md').write_text('Synthetic retirement outcome; no real feature retired.\n')
        self.git('add','-A');self.git('commit','-qm','Synthetic completed retirement')

    def test_cli_lifecycle_preserves_prior_anchors_history_and_queries(self):
        saved=self.record();before=P.map_path(self.project).read_bytes()
        old=json.loads(before);self.complete_source()
        outcome=self.outcome();source=self.root/'outcome.json';source.write_text(json.dumps(outcome))
        result=self.run_cli('retire-record','--feature','feature-a','--input',str(source),'--expected-sha256',saved['sha256'])
        self.assertEqual(result.returncode,0,result.stderr)
        receipt=json.loads(result.stdout)
        self.assertIn('no authentication',receipt['qualification'])
        value,sha=P.read_map(self.project,self.repo);feature=value['features'][0]
        self.assertEqual(feature['state'],'retired');self.assertEqual(feature['code'],[])
        self.assertEqual(feature['retirement']['prior_feature'],old['features'][0])
        self.assertEqual(feature['retirement']['prior_snapshot']['a.py'],old['snapshot']['a.py'])
        self.assertNotIn('a.py',value['snapshot'])
        self.assertEqual(value['features'][1],old['features'][1])
        self.assertEqual((P.map_path(self.project).parent/'product-map-history'/(saved['sha256']+'.json')).read_bytes(),before)
        for args in [('status',),('handoff','--feature','feature-a')]:
            query=self.run_cli(*args);self.assertIn(query.returncode,(0,1),query.stderr)
            shown=json.loads(query.stdout);self.assertEqual(shown['features'][0]['retirement'],feature['retirement'])
            self.assertEqual(shown['map_sha256'],sha)
        impact=json.loads(self.run_cli('impact','--path','shared.py','--transitive').stdout)
        self.assertEqual([f['id'] for f in impact['features']],['feature-b'])
        self.assertIn('unknown',impact['warning'])
        # Existing record input shape round-trips without a schema migration.
        P.save(self.project,self.repo,{k:value[k] for k in ('schema_version','mode','commit','features','product')},sha)

    def test_shipped_retirement_retains_removed_prior_evidence_and_writes_no_source(self):
        data=self.data();data['features'][0]['state']='shipped'
        data['features'][0]['evidence']=[dict(path='a.py',note='Synthetic prior implementation evidence only')]
        saved=P.save(self.project,self.repo,data,'new');self.complete_source()
        files_before={str(p.relative_to(self.repo)):p.read_bytes() for p in self.repo.rglob('*') if p.is_file()}
        P.record_retirement(self.project,self.repo,'feature-a',self.outcome(),saved['sha256'])
        files_after={str(p.relative_to(self.repo)):p.read_bytes() for p in self.repo.rglob('*') if p.is_file()}
        self.assertEqual(files_before,files_after)
        value,_=P.read_map(self.project,self.repo)
        context=value['features'][0]['retirement']
        self.assertEqual(context['prior_feature']['evidence'][0]['path'],'a.py')
        self.assertIn('a.py',context['prior_snapshot'])
        self.assertNotIn('a.py',value['snapshot'])

    def test_bad_completion_inputs_never_mutate_map(self):
        saved=self.record();before=P.map_path(self.project).read_bytes();self.complete_source()
        good=self.outcome()
        cases=[]
        for key in good:
            item=copy.deepcopy(good);del item[key];cases.append(item)
        for evidence in ([],[dict(path=None,note='Claim alone')],[dict(path='absent',note='Missing')]):
            item=copy.deepcopy(good);item['evidence']=evidence;cases.append(item)
        item=copy.deepcopy(good);item['commit']=self.head;cases.append(item)
        item=copy.deepcopy(good);item['replacement']='';cases.append(item)
        item=copy.deepcopy(good);item['features']=[];cases.append(item)
        for item in cases:
            with self.subTest(item=item),self.assertRaises((ValueError,TypeError)):
                P.record_retirement(self.project,self.repo,'feature-a',item,saved['sha256'])
            self.assertEqual(P.map_path(self.project).read_bytes(),before)
        for feature,sha in [('unknown',saved['sha256']),('feature-a','0'*64)]:
            with self.assertRaises(ValueError):P.record_retirement(self.project,self.repo,feature,good,sha)
            self.assertEqual(P.map_path(self.project).read_bytes(),before)
        (self.repo/'outcome.md').write_text('Uncommitted changed outcome')
        with self.assertRaisesRegex(ValueError,'stale'):
            P.record_retirement(self.project,self.repo,'feature-a',good,saved['sha256'])
        self.assertEqual(P.map_path(self.project).read_bytes(),before)

    def test_removed_direct_shared_survivor_refused(self):
        saved=self.record();before=P.map_path(self.project).read_bytes();self.complete_source(('a.py','shared.py'))
        with self.assertRaisesRegex(ValueError,'shared code'):
            P.record_retirement(self.project,self.repo,'feature-a',self.outcome(),saved['sha256'])
        self.assertEqual(P.map_path(self.project).read_bytes(),before)

    def test_removed_transitive_shared_survivor_refused(self):
        (self.repo/'a.py').write_text('import shared\n');(self.repo/'b.py').write_text('import shared\n')
        self.git('add','.');self.git('commit','-qm','Synthetic indirect shared consumer');self.head=self.git('rev-parse','HEAD').strip()
        data=self.data();data['features'][0]['code']=['a.py'];data['features'][1]['code']=['b.py']
        saved=P.save(self.project,self.repo,data,'new');before=P.map_path(self.project).read_bytes()
        self.complete_source(('a.py','shared.py'))
        with self.assertRaisesRegex(ValueError,'shared code'):
            P.record_retirement(self.project,self.repo,'feature-a',self.outcome(),saved['sha256'])
        self.assertEqual(P.map_path(self.project).read_bytes(),before)

    def test_context_cannot_be_forged_changed_or_discarded_by_generic_record(self):
        saved=self.record();self.complete_source()
        P.record_retirement(self.project,self.repo,'feature-a',self.outcome(),saved['sha256'])
        value,sha=P.read_map(self.project,self.repo)
        data={k:value[k] for k in ('schema_version','mode','commit','features','product')}
        for mutation in ('remove','decision','prior_anchor'):
            forged=copy.deepcopy(data)
            if mutation=='remove':del forged['features'][0]['retirement']
            elif mutation=='decision':forged['features'][0]['retirement']['outcome']['decision_ref']='Forged claim'
            else:forged['features'][0]['retirement']['prior_snapshot']['a.py']['blob']='0'*40
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):
                P.save(self.project,self.repo,forged,sha)
        with self.assertRaises(ValueError):P.record_retirement(self.project,self.repo,'feature-a',self.outcome(),sha)
