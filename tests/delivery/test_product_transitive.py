import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

PACKAGE = Path(__file__).resolve().parents[2] / 'plugins/delivery'
sys.path.insert(0,str(PACKAGE/'scripts'))
import product as P
from project import initialize


class DependencyImpactTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.repo = self.root/'code';self.repo.mkdir()
        self.project = self.root/'planning';self.project.mkdir()
        initialize(self.project,'example')
        self.git('init','-q');self.git('config','user.email','fixture@example.invalid');self.git('config','user.name','Fixture')
        self.starter = json.loads((PACKAGE/'templates/product-input.json').read_text())

    def tearDown(self):
        self.temp.cleanup()

    def git(self,*args):
        return subprocess.check_output(['git','-C',str(self.repo),*args],text=True)

    def record(self, files, anchors):
        for path,content in files.items():
            target = self.repo/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_text(content)
        self.git('add','.');self.git('commit','-qm','Synthetic import fixture')
        data = copy.deepcopy(self.starter)
        data.update(mode='brownfield',commit=self.git('rev-parse','HEAD').strip())
        data['features'] = []
        for index,code in enumerate(anchors):
            feature = copy.deepcopy(self.starter['features'][0])
            feature.update(id='feature-'+str(index),name='Outcome '+str(index),code=code,
                           state='preview' if code else 'planned')
            data['features'].append(feature)
        P.save(self.project,self.repo,data,'new')
        return P.read_map(self.project,self.repo)[0]

    def cli(self,*args):
        return subprocess.run([sys.executable,str(PACKAGE/'scripts/product.py'),'--project',str(self.project),
                               '--repo',str(self.repo),*args],capture_output=True,text=True,timeout=30)

    def test_cli_adds_shortest_file_line_chain_without_changing_direct_matches(self):
        value = self.record({'app.py':'import adapter\nimport leaf\n', 'adapter.py':'import middle\n',
                             'middle.py':'import leaf\n','leaf.py':'import app\n'},[['app.py'],['adapter.py']])
        direct = P.impact(value,self.repo,['leaf.py'])
        self.assertEqual(direct['features'],[])
        self.assertNotIn('transitive',direct)
        run = self.cli('impact','--path','leaf.py','--transitive')
        self.assertEqual(run.returncode,0,run.stderr)
        result = json.loads(run.stdout)
        self.assertEqual(result['features'],direct['features'])
        graph = result['transitive']
        self.assertEqual(graph['snapshot_commit'],value['commit'])
        via = graph['features'][0]['via'][0]
        self.assertEqual(via['hops'],1)
        self.assertEqual(via['chain'],[{'from':'app.py','to':'leaf.py','line':2,'kind':'python-import'}])
        self.assertEqual(graph['features'][1]['via'][0]['hops'],2)
        self.assertEqual(graph['shared_files']['leaf.py'],['feature-0','feature-1'])
        self.assertEqual(graph['unreached_paths'],[])

    def test_relative_package_imports_reach_submodule_and_package_initializer(self):
        value = self.record({'pkg/__init__.py':'import init_dep\n','pkg/app.py':'from . import leaf\n',
                             'pkg/leaf.py':'from .deep import item\n', 'pkg/deep.py':'item = 1\n',
                             'init_dep.py':'# no dependencies\n'},[['pkg/app.py']])
        result = P.impact(value,self.repo,['pkg/deep.py','init_dep.py'],True)['transitive']
        self.assertEqual(result['unreached_paths'],[])
        chains = {v['path']:v['chain'] for v in result['features'][0]['via']}
        self.assertEqual([e['to'] for e in chains['pkg/deep.py']],['pkg/leaf.py','pkg/deep.py'])
        self.assertEqual([e['to'] for e in chains['init_dep.py']],['pkg/__init__.py','init_dep.py'])

    def test_comments_and_strings_do_not_create_imports_but_unknowns_are_reported(self):
        value = self.record({'app.py':'# import fake\ns = "import fake"\nimport missing\n__import__(s)\n',
                             'fake.py':'pass\n','bad.py':'not python !\n','other.rs':'mod hidden;\n'},
                            [['app.py','bad.py','other.rs'],[]])
        graph = P.impact(value,self.repo,['fake.py'],True)['transitive']
        self.assertEqual(graph['features'],[])
        self.assertEqual(graph['unreached_paths'],['fake.py'])
        coverage = graph['coverage']
        self.assertEqual(coverage['features_without_code'],['feature-1'])
        self.assertEqual(coverage['unresolved_references'][0]['reference'],'missing')
        self.assertEqual(coverage['dynamic_loaders_not_inferred'][0]['line'],4)
        self.assertEqual({x['path'] for x in coverage['unsupported_or_unparsed']},{'bad.py','other.rs'})

    def test_ambiguous_roots_and_symlink_targets_are_not_silently_selected(self):
        value = self.record({'pkg/app.py':'import same\nimport link\n','pkg/same.py':'pass\n',
                             'same.py':'pass\n','leaf.py':'pass\n'},[['pkg/app.py']])
        (self.repo/'pkg/link.py').symlink_to('../leaf.py')
        self.git('add','pkg/link.py');self.git('commit','-qm','Symlink dependency fixture')
        data = {k:value[k] for k in ('schema_version','mode','commit','features','product')}
        data['commit'] = self.git('rev-parse','HEAD').strip()
        sha = P.read_map(self.project,self.repo)[1]
        P.save(self.project,self.repo,data,sha)
        value = P.read_map(self.project,self.repo)[0]
        graph = P.impact(value,self.repo,['same.py','leaf.py'],True)['transitive']
        self.assertEqual(graph['features'],[])
        reasons = [r['reason'] for r in graph['coverage']['unresolved_references']]
        self.assertTrue(any('ambiguous' in r for r in reasons))
        self.assertTrue(any('symlink' in r for r in reasons))

    def test_from_import_does_not_hide_base_ambiguity_when_child_exists(self):
        value = self.record({'app.py':'from pkg import child\n','pkg/__init__.py':'pass\n',
                             'src/pkg/__init__.py':'pass\n','pkg/child.py':'pass\n'},[['app.py']])
        graph = P.impact(value,self.repo,['pkg/child.py'],True)['transitive']
        self.assertEqual(graph['features'],[])
        self.assertEqual(graph['coverage']['unresolved_references'][0]['reference'],'pkg')
        self.assertIn('ambiguous',graph['coverage']['unresolved_references'][0]['reason'])

    def test_relative_import_cannot_escape_known_package_or_invent_one(self):
        value = self.record({'pkg/__init__.py':'pass\n','pkg/app.py':'from .. import dep\n',
                             'app.py':'from . import dep\n','dep.py':'pass\n'},[['pkg/app.py','app.py']])
        graph = P.impact(value,self.repo,['dep.py'],True)['transitive']
        self.assertEqual(graph['features'],[])
        reasons = [row['reason'] for row in graph['coverage']['unresolved_references']]
        self.assertTrue(any('escapes known' in reason for reason in reasons))
        self.assertTrue(any('context unknown' in reason for reason in reasons))

    def test_src_root_initializer_is_excluded_and_unsupported_package_is_reported(self):
        value = self.record({'app.py':'import pkg.child\n','src/__init__.py':'pass\n',
                             'src/pkg/__init__.py':'pass\n','src/pkg/child.py':'pass\n'},[['app.py']])
        graph = P.impact(value,self.repo,['src/__init__.py','src/pkg/__init__.py'],True)['transitive']
        self.assertEqual(graph['unreached_paths'],['src/__init__.py'])
        self.assertEqual(graph['features'][0]['via'][0]['path'],'src/pkg/__init__.py')
        (self.repo/'src/pkg/__init__.py').unlink()
        (self.repo/'src/pkg/__init__.py').symlink_to('../__init__.py')
        self.git('add','src/pkg/__init__.py');self.git('commit','-qm','Unsupported package initializer')
        data = {k:value[k] for k in ('schema_version','mode','commit','features','product')}
        data['commit'] = self.git('rev-parse','HEAD').strip()
        P.save(self.project,self.repo,data,P.read_map(self.project,self.repo)[1])
        value = P.read_map(self.project,self.repo)[0]
        graph = P.impact(value,self.repo,['src/pkg/child.py'],True)['transitive']
        self.assertEqual(graph['features'],[])
        self.assertIn('initializer mode',graph['coverage']['unresolved_references'][0]['reason'])

    def test_absolute_namespace_and_shadowed_package_are_explicitly_unsupported(self):
        value = self.record({'app.py':'import ns.child\nimport shadow.child\n','ns/child.py':'pass\n',
                             'shadow.py':'pass\n','shadow/child.py':'pass\n'},[['app.py']])
        graph = P.impact(value,self.repo,['ns/child.py','shadow/child.py'],True)['transitive']
        self.assertEqual(graph['features'],[])
        self.assertEqual(len(graph['coverage']['unresolved_references']),2)
        self.assertTrue(all('namespace' in row['reason'] for row in graph['coverage']['unresolved_references']))

    def test_raw_dependency_change_is_stale_despite_hidden_index_flag(self):
        value = self.record({'app.py':'import dep\n','dep.py':'value = 1\n'},[['app.py']])
        self.git('update-index','--assume-unchanged','dep.py')
        before = (self.repo/'dep.py').stat()
        (self.repo/'dep.py').write_text('value = 2\n')
        os.utime(self.repo/'dep.py',ns=(before.st_atime_ns,before.st_mtime_ns))
        run = self.cli('impact','--path','dep.py','--transitive')
        self.assertEqual(run.returncode,1,run.stderr)
        graph = json.loads(run.stdout)['transitive']
        self.assertEqual(graph['snapshot_commit'],value['commit'])
        self.assertFalse(graph['freshness']['fresh'])
        self.assertEqual(graph['freshness']['changed_reached_files'],['dep.py'])
        self.assertEqual(graph['features'][0]['via'][0]['chain'][0]['from'],'app.py')

    def test_git_replacement_does_not_rewrite_dependency_edges(self):
        value = self.record({'app.py':'import dep\n','dep.py':'pass\n'},[['app.py']])
        (self.repo/'app.py').write_text('pass\n');self.git('add','app.py');self.git('commit','-qm','Replacement graph')
        self.git('replace',value['commit'],self.git('rev-parse','HEAD').strip())
        graph = P.impact(value,self.repo,['dep.py'],True)['transitive']
        self.assertEqual(graph['features'][0]['via'][0]['hops'],1)
        self.assertEqual(graph['snapshot_commit'],value['commit'])
        self.assertFalse(graph['freshness']['fresh'])

    def test_greenfield_and_optional_failure_do_not_gate_direct_information(self):
        value = P.validate(self.starter,None)
        graph = P.impact(value,None,['future.py'],True)['transitive']
        self.assertFalse(graph['available'])
        self.assertIn('Planned greenfield',graph['reason'])
        value = self.record({'app.py':'pass\n'},[['app.py']])
        with patch.object(P,'dependency_reach',side_effect=subprocess.TimeoutExpired('git',30)):
            report = P.impact(value,self.repo,['app.py'],True)
        self.assertEqual(report['features'][0]['id'],'feature-0')
        self.assertFalse(report['transitive']['available'])
        self.assertIn('unavailable',report['transitive']['reason'])

    def test_retirement_preserves_transitively_shared_dependency_without_writing(self):
        value = self.record({'a.py':'import shared\n','b.py':'import shared\n','shared.py':'pass\n'},[['a.py'],['b.py']])
        before = P.map_path(self.project).read_bytes()
        report = P.retirement(value,self.repo,'feature-0',True)
        graph = report['transitive']
        self.assertEqual(graph['shared_code_to_preserve'],{'shared.py':['feature-1']})
        self.assertEqual(graph['exclusive_candidates_not_deletion_permission'],['a.py'])
        self.assertIn('candidate only',graph['warning'])
        self.assertTrue(report['proposal_only'])
        self.assertEqual(report['required_owner_decision']['choice'],'unknown')
        self.assertEqual(P.map_path(self.project).read_bytes(),before)
        self.assertTrue((self.repo/'shared.py').exists())


if __name__=='__main__':
    unittest.main()
