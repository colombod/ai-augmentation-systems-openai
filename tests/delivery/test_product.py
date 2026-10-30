import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

PACKAGE = Path(__file__).resolve().parents[2]/'plugins/delivery'
sys.path.insert(0,str(PACKAGE/'scripts'))
import product as P
from project import initialize


class ProductTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.project = self.root/'planning'; self.project.mkdir()
        initialize(self.project,'example')
        self.repo = self.root/'product'; self.repo.mkdir()
        self.git('init','-q'); self.git('config','user.email','fixture@example.invalid'); self.git('config','user.name','Fixture')
        for name in ('shared.py','a.py','b.py','README.md'):
            (self.repo/name).write_text('initial\n')
        self.git('add','.'); self.git('commit','-qm','Synthetic product')
        self.head = self.git('rev-parse','HEAD').strip()
        self.starter = json.loads((PACKAGE/'templates/product-input.json').read_text())

    def tearDown(self):
        self.temp.cleanup()

    def git(self,*args):
        return subprocess.check_output(['git','-C',str(self.repo),*args],text=True)

    def data(self):
        data = copy.deepcopy(self.starter)
        data.update(mode='brownfield',commit=self.head)
        feature = data['features'][0]
        feature.update(id='feature-a',name='Customer outcome A',state='preview',code=['a.py','shared.py'],evidence=[{'path':'README.md','note':'Source only, no observed outside use.'}])
        second = copy.deepcopy(feature)
        second.update(id='feature-b',name='Customer outcome B',code=['b.py','shared.py'])
        data['features'].append(second)
        return data

    def record(self):
        return P.save(self.project,self.repo,self.data(),'new')

    def run_cli(self,*args,repo=True):
        argv = [sys.executable,str(PACKAGE/'scripts/product.py'),'--project',str(self.project)]
        if repo:
            argv += ['--repo',str(self.repo)]
        return subprocess.run(argv+list(args),capture_output=True,text=True,timeout=15)

    def test_greenfield_records_and_hands_off_without_git_or_invented_code(self):
        saved = P.save(self.project,None,self.starter,'new')
        record,_ = P.read_map(self.project,None)
        self.assertIsNone(record['commit'])
        self.assertEqual(record['features'][0]['code'],[])
        result = self.run_cli('handoff',repo=False)
        self.assertEqual(result.returncode,1,result.stderr)
        handoff = json.loads(result.stdout)
        self.assertIsNone(handoff['freshness']['fresh'])
        self.assertIn('customer',handoff['unconfirmed_choices'])
        self.assertEqual(saved['sha256'],handoff['map_sha256'])

    def test_greenfield_cannot_claim_observed_code_and_can_transition_to_same_feature(self):
        bad = copy.deepcopy(self.starter);bad['features'][0]['state']='shipped'
        with self.assertRaises(ValueError):
            P.save(self.project,None,bad,'new')
        saved = P.save(self.project,None,self.starter,'new')
        next_value = copy.deepcopy(self.starter)
        next_value.update(mode='brownfield',commit=self.head)
        next_value['features'][0].update(state='preview',code=['a.py'])
        P.save(self.project,self.repo,next_value,saved['sha256'])
        value,_ = P.read_map(self.project,self.repo)
        self.assertEqual(value['features'][0]['id'],self.starter['features'][0]['id'])
        self.assertTrue(P.freshness(value,self.repo)['fresh'])

    def test_real_git_census_does_not_write_and_impact_reports_shared_code(self):
        before = sorted(str(p.relative_to(self.repo)) for p in self.repo.rglob('*'))
        report = P.inspect(self.repo)
        self.assertEqual(report['commit'],self.head)
        self.assertEqual(before,sorted(str(p.relative_to(self.repo)) for p in self.repo.rglob('*')))
        self.record()
        result = self.run_cli('impact','--path','shared.py','--path','unknown.py')
        self.assertEqual(result.returncode,0,result.stderr)
        impact = json.loads(result.stdout)
        self.assertEqual(impact['shared_files']['shared.py'],['feature-a','feature-b'])
        self.assertEqual(impact['unmapped_paths'],['unknown.py'])
        self.assertIn('unknown',impact['warning'])
        status=json.loads(self.run_cli('status').stdout)
        self.assertEqual(status['features'][0]['code'],['a.py','shared.py'])
        self.assertEqual(status['features'][0]['evidence'][0]['path'],'README.md')

    def test_hash_freshness_detects_same_length_mtime_and_hidden_index_changes(self):
        self.record();value,_=P.read_map(self.project,self.repo)
        path=self.repo/'shared.py'; prior=path.stat()
        self.git('update-index','--assume-unchanged','shared.py')
        path.write_text('changed\n');os.utime(path,ns=(prior.st_atime_ns,prior.st_mtime_ns))
        self.assertEqual(len(path.read_bytes()),prior.st_size)
        report=P.freshness(value,self.repo)
        self.assertFalse(report['fresh'])
        self.assertIn('shared.py',report['changed_mapped_files'])
        self.assertIn('shared.py',P.inspect(self.repo)['working_changes'])

    def test_commit_advancement_is_stale_even_when_linked_bytes_match(self):
        self.record();value,_=P.read_map(self.project,self.repo)
        (self.repo/'other.py').write_text('new')
        self.git('add','other.py');self.git('commit','-qm','Unmapped addition')
        report=P.freshness(value,self.repo)
        self.assertFalse(report['fresh']);self.assertFalse(report['commit_matches'])
        self.assertIn('other.py',report['unmapped_committed_changes'])
        self.assertEqual(report['changed_mapped_files'],[])

    def test_working_unmapped_and_untracked_files_remain_visible(self):
        data=self.data();data['features'][1]['code']=['shared.py']
        P.save(self.project,self.repo,data,'new');value,_=P.read_map(self.project,self.repo)
        (self.repo/'b.py').write_text('changed');(self.repo/'new.py').write_text('new')
        report=P.freshness(value,self.repo)
        self.assertIn('b.py',report['unmapped_working_changes'])
        self.assertIn('new.py',report['untracked_not_analyzed'])

    def test_cas_preserves_history_and_refuses_silent_removal(self):
        first=self.record();old=P.map_path(self.project).read_bytes()
        with self.assertRaisesRegex(ValueError,'expected SHA'):
            P.save(self.project,self.repo,self.data(),'new')
        update=self.data();update['features'][0]['summary']='A more precise promise'
        second=P.save(self.project,self.repo,update,first['sha256'])
        self.assertNotEqual(first['sha256'],second['sha256'])
        history=P.map_path(self.project).parent/'product-map-history'/(first['sha256']+'.json')
        self.assertEqual(history.read_bytes(),old)
        update['features'].pop()
        with self.assertRaisesRegex(ValueError,'Preserve old feature'):
            P.save(self.project,self.repo,update,second['sha256'])

    def test_retirement_only_proposes_and_preserves_shared_code(self):
        self.record();value,_=P.read_map(self.project,self.repo)
        before=P.map_path(self.project).read_bytes()
        report=P.retirement(value,self.repo,'feature-a')
        self.assertTrue(report['proposal_only'])
        self.assertEqual(report['shared_code_to_preserve'],{'shared.py':['feature-b']})
        self.assertEqual(report['exclusive_candidates_not_deletion_permission'],['a.py'])
        self.assertEqual(report['required_owner_decision']['choice'],'unknown')
        for key in ('replacement','migration','rollback','usage_review'):
            self.assertIn(key,report['required_owner_decision'])
        self.assertEqual(report['decision_context']['summary'],value['features'][0]['summary'])
        self.assertIn('Return',report['decision_context']['usefulness'])
        self.assertEqual(P.map_path(self.project).read_bytes(),before)
        self.assertTrue((self.repo/'a.py').exists())
        with self.assertRaises(ValueError):
            changed=self.data();changed['features'][0]['state']='retired'
            P.save(self.project,self.repo,changed,hashlib.sha256(before).hexdigest())

    def test_invalid_mapping_never_resolves_refs_paths_or_symlinks(self):
        for commit,path in [('HEAD','a.py'),(self.head[:8],'a.py'),(self.head,'../outside'),(self.head,'missing.py')]:
            value=self.data();value['commit']=commit;value['features'][0]['code']=[path]
            with self.subTest(commit=commit,path=path),self.assertRaises(ValueError):
                P.validate(value,self.repo)
        (self.repo/'link').symlink_to('a.py');self.git('add','link');self.git('commit','-qm','Symlink')
        value=self.data();value['commit']=self.git('rev-parse','HEAD').strip();value['features'][0]['code']=['link']
        with self.assertRaisesRegex(ValueError,'regular tracked'):
            P.validate(value,self.repo)

    def test_historical_retirement_still_protects_a_surviving_shared_consumer(self):
        data=self.data();data['features'][0]['state']='retired'
        P.save(self.project,self.repo,data,'new');value,_=P.read_map(self.project,self.repo)
        report=P.retirement(value,self.repo,'feature-a')
        self.assertEqual(report['shared_code_to_preserve'],{'shared.py':['feature-b']})
        self.assertNotIn('shared.py',report['exclusive_candidates_not_deletion_permission'])

    def test_forged_snapshot_and_aggregate_usefulness_are_refused(self):
        self.record();path=P.map_path(self.project);value=json.loads(path.read_text())
        value['snapshot']['shared.py']['blob']='0'*40;path.write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError,'snapshot'):
            P.read_map(self.project,self.repo)
        value=self.data();value['features'][0]['usefulness']['total']=100
        with self.assertRaisesRegex(ValueError,'Usefulness card'):
            P.validate(value,self.repo)

    def test_unknown_safety_gates_cap_need_without_granting_authority(self):
        shape=copy.deepcopy(self.starter['product']['right_shape'])
        shape['need']={k:3 for k in shape['need']}
        calculated=P.placement(shape)
        self.assertEqual(calculated['need_rung'],8)
        self.assertEqual(calculated['maximum_rung'],5)
        self.assertEqual(len(calculated['capped_by']),6)
        self.assertIn('arithmetic only',calculated['qualification'])
        shape['autonomy_rung']=8
        with self.assertRaisesRegex(ValueError,'conservative gate ceiling'):
            P.placement(shape)

    def test_staged_addition_delete_and_rename_are_visible(self):
        self.record();value,_=P.read_map(self.project,self.repo)
        (self.repo/'consumer.py').write_text('new consumer');self.git('add','consumer.py')
        self.git('mv','b.py','renamed.py');self.git('rm','a.py')
        census=P.inspect(self.repo);fresh=P.freshness(value,self.repo)
        for path in ('consumer.py','a.py','b.py','renamed.py'):
            self.assertIn(path,census['working_changes'])
            self.assertIn(path,fresh['staged_changes'])
        self.assertFalse(fresh['fresh'])

    def test_oversized_new_and_updated_maps_do_not_create_unreadable_records(self):
        data=self.data();large=copy.deepcopy(data['features'][0])
        for card in large['usefulness'].values():
            card['evidence']='x'*16000
        data['features'] += [{**copy.deepcopy(large),'id':'large-'+str(i)} for i in range(45)]
        with self.assertRaisesRegex(ValueError,'four megabytes'):
            P.save(self.project,self.repo,data,'new')
        self.assertFalse(P.map_path(self.project).exists())
        first=self.record();original=P.map_path(self.project).read_bytes()
        with self.assertRaisesRegex(ValueError,'four megabytes'):
            P.save(self.project,self.repo,data,first['sha256'])
        self.assertEqual(P.map_path(self.project).read_bytes(),original)

    def test_corrupted_history_cannot_be_accepted_as_preserved_prior_bytes(self):
        first=self.record();path=P.map_path(self.project);original=path.read_bytes()
        history=path.parent/'product-map-history';history.mkdir()
        (history/(first['sha256']+'.json')).write_text('truncated')
        with self.assertRaisesRegex(ValueError,'History conflicts'):
            P.save(self.project,self.repo,self.data(),first['sha256'])
        self.assertEqual(path.read_bytes(),original)

    def test_git_replacement_cannot_rewrite_the_named_snapshot(self):
        self.record();(self.repo/'a.py').write_text('replacement')
        self.git('add','a.py');self.git('commit','-qm','Replacement content')
        replacement=self.git('rev-parse','HEAD').strip()
        self.git('replace',self.head,replacement)
        value,_=P.read_map(self.project,self.repo)
        original_blob=self.git('--no-replace-objects','rev-parse',self.head+':a.py').strip()
        self.assertEqual(value['snapshot']['a.py']['blob'],original_blob)

    def test_handoff_preserves_feature_promise_alongside_paths(self):
        self.record();value,_=P.read_map(self.project,self.repo)
        result=P.handoff(value,self.repo)
        self.assertEqual(result['features'][0]['summary'],value['features'][0]['summary'])

    def test_greenfield_planning_contract_labels_paths_without_requiring_implementation(self):
        # Regression for the independently reproduced instruction contradiction:
        # the old imperative prevented no-repo designs and new-file stories.
        architecture=(PACKAGE/'skills/architecture/SKILL.md').read_text()
        stories=(PACKAGE/'skills/stories/SKILL.md').read_text()
        self.assertNotIn('Read the codebase before designing.** This is not optional',architecture)
        self.assertNotIn('**3. Verify the file paths exist.**',stories)
        for name in ('architecture','story'):
            template=(PACKAGE/'templates'/(name+'.md')).read_text()
            self.assertIn('proposed new',template)
            self.assertIn('greenfield',template)
        self.assertIn('Source absence is a starting',architecture)
        self.assertIn('Do not\nrequire a file that the story is meant to create',stories)


if __name__=='__main__':
    unittest.main()
