"""Explicit source scopes filter candidates, never project constraints or state."""
import json
import unittest
import test_product as fixtures
P = fixtures.P


class InspectScopeTests(unittest.TestCase):
    setUp = fixtures.ProductTests.setUp
    tearDown = fixtures.ProductTests.tearDown
    git = fixtures.ProductTests.git
    data = fixtures.ProductTests.data
    record = fixtures.ProductTests.record
    run_cli = fixtures.ProductTests.run_cli

    def monorepo(self):
        names = ['AGENTS.md', 'plugins/AGENTS.md',
            'plugins/delivery/README.md', 'plugins/delivery/plugin.json',
            'plugins/delivery/scripts/core.py', 'tests/delivery/test_core.py',
            'plugins/delivery-extra/package.json', 'tests/other/test_other.py',
            'evidence/prior/tests/test_old.py']
        for name in names:
            path = self.repo/name; path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('synthetic source census fixture\n')
        self.git('add','.'); self.git('commit','-qm','Synthetic monorepo candidates')

    def test_scoped_cli_retains_ancestor_context_and_global_dirty_state(self):
        self.monorepo();self.record();before=P.map_path(self.project).read_bytes()
        outside=self.repo/'plugins/delivery-extra/package.json'
        outside.write_text('staged outside selection\n');self.git('add',str(outside))
        (self.repo/'b.py').write_text('working outside selection\n')
        (self.repo/'untracked-notes').write_text('untracked outside selection\n')
        query=self.run_cli('inspect','--scope','plugins/delivery','--scope','tests/delivery')
        self.assertEqual(query.returncode,0,query.stderr)
        value=json.loads(query.stdout)
        self.assertEqual(value['manifests'],['plugins/delivery/plugin.json'])
        self.assertEqual(value['test_paths'],['tests/delivery/test_core.py'])
        self.assertEqual(value['instructions_and_docs'],['plugins/delivery/README.md'])
        self.assertEqual(value['scope']['repository_context'],['AGENTS.md','README.md','plugins/AGENTS.md'])
        self.assertEqual(value['scope']['selected_tracked_files'],4)
        self.assertIn('plugins/delivery-extra/package.json',value['staged_changes'])
        self.assertIn('b.py',value['working_changes'])
        self.assertIn('untracked-notes',value['untracked'])
        self.assertIn('unknown',value['scope']['qualification'])
        self.assertEqual(P.map_path(self.project).read_bytes(),before)
        self.assertEqual(self.git('rev-parse','HEAD').strip(),value['commit'])

    def test_default_census_stays_compatible_and_scope_is_deterministic(self):
        self.monorepo();full=P.inspect(self.repo)
        self.assertNotIn('scope',full)
        self.assertIn('plugins/delivery-extra/package.json',full['manifests'])
        self.assertIn('evidence/prior/tests/test_old.py',full['test_paths'])
        scoped=P.inspect(self.repo,['tests/delivery','plugins/delivery','plugins/delivery'])
        self.assertEqual(scoped,P.inspect(self.repo,['plugins/delivery','tests/delivery']))
        for key in ('repository','commit','tracked_files','working_changes','staged_changes','untracked','feature_discovery'):
            self.assertEqual(scoped[key],full[key],key)

    def test_file_scope_and_prefix_boundary_do_not_select_neighbor(self):
        self.monorepo()
        value=P.inspect(self.repo,['plugins/delivery/plugin.json'])
        self.assertEqual(value['scope']['selected_tracked_files'],1)
        self.assertEqual(value['manifests'],['plugins/delivery/plugin.json'])
        self.assertIn('plugins/delivery/README.md',value['scope']['repository_context'])
        self.assertNotIn('plugins/delivery-extra/package.json',P.inspect(self.repo,['plugins/delivery'])['manifests'])

    def test_bad_scopes_refuse_without_global_fallback_or_writes(self):
        self.monorepo();self.record();before=P.map_path(self.project).read_bytes()
        (self.repo/'linked-source').symlink_to('plugins/delivery')
        self.git('add','linked-source');self.git('commit','-qm','Synthetic unsupported symlink scope')
        for scope in ('','../plugins','/plugins','./plugins','plugins\\delivery','missing','linked-source'):
            with self.subTest(scope=scope):
                q=self.run_cli('inspect','--scope',scope)
                self.assertEqual(q.returncode,2,q.stderr)
                self.assertEqual(q.stdout,'')
                self.assertEqual(P.map_path(self.project).read_bytes(),before)
        for scopes in ([], 'plugins/delivery'):
            with self.assertRaises(ValueError):P.inspect(self.repo,scopes)

    def test_greenfield_inspection_has_no_source_requirement(self):
        q=self.run_cli('inspect',repo=False)
        self.assertEqual(q.returncode,0,q.stderr)
        self.assertEqual(json.loads(q.stdout)['mode'],'greenfield')
        q=self.run_cli('inspect','--scope','src',repo=False)
        self.assertEqual(q.returncode,2)
        self.assertIn('no-code',q.stderr)
        self.assertFalse(P.map_path(self.project).exists())
