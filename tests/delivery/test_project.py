import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / 'plugins/delivery/scripts/project.py'
spec = importlib.util.spec_from_file_location('project', SCRIPT)
project = importlib.util.module_from_spec(spec)
spec.loader.exec_module(project)


class ProjectTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()

    def test_init_reuses_ancestor_and_preserves_existing_artifact(self):
        first = project.initialize(self.root, 'launch')
        artifact = self.root / '.delivery/initiatives/launch/brief.md'
        artifact.write_bytes(b'Human changes\n')
        child = self.root / 'component'
        child.mkdir()
        second = project.initialize(child, 'launch')
        self.assertTrue(first['created'])
        self.assertEqual(second['created'], [])
        self.assertEqual(artifact.read_bytes(), b'Human changes\n')
        self.assertFalse((child / '.delivery').exists())

    def test_status_never_creates_workspace_or_changes_content(self):
        self.assertFalse(project.inventory(self.root)['exists'])
        self.assertEqual(list(self.root.iterdir()), [])
        project.initialize(self.root, 'launch')
        artifact = self.root / '.delivery/stories/launch-01.md'
        artifact.write_text('status: done\nThis is a claim without evidence.\n')
        before = {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        result = project.inventory(self.root)
        self.assertIn('stories/launch-01.md', result['files'])
        self.assertIn('inventory-only', result['verification'])
        self.assertEqual(before, {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()})

    def test_nested_component_workspace_refuses_shadow_root(self):
        component = self.root / 'component'
        component.mkdir()
        project.initialize(component, 'launch')
        with self.assertRaisesRegex(project.ProjectError, 'Nested .delivery'):
            project.initialize(self.root, 'other')
        self.assertFalse((self.root / '.delivery').exists())

    def test_invalid_slug_and_conflict_leave_workspace_unmodified(self):
        for slug in ('../escape', 'a/b', '', 'Launch', '-launch'):
            with self.subTest(slug=slug), self.assertRaises(project.ProjectError):
                project.initialize(self.root, slug)
        self.assertEqual(list(self.root.iterdir()), [])
        root = self.root / '.delivery'
        root.mkdir()
        (root / 'stories').write_text('keep')
        with self.assertRaisesRegex(project.ProjectError, 'Not a directory'):
            project.initialize(self.root, 'launch')
        self.assertEqual([p.name for p in root.iterdir()], ['stories'])

    def test_symlink_directory_or_artifact_is_refused(self):
        outside = self.root / 'outside'
        outside.mkdir()
        (self.root / '.delivery').symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(project.ProjectError, 'Symlink'):
            project.initialize(self.root, 'launch')
        (self.root / '.delivery').unlink()
        project.initialize(self.root, 'launch')
        (self.root / '.delivery/stories/leak.md').symlink_to(outside / 'file')
        with self.assertRaisesRegex(project.ProjectError, 'Symlink'):
            project.inventory(self.root)
        self.assertEqual(list(outside.iterdir()), [])

    def test_prose_count_excludes_template_comment_yaml_code_and_tables(self):
        path = self.root / 'artifact.md'
        path.write_text('<!-- budget words -->\n\n---\nname: excluded words\n---\n'
                        '# Three prose words\n\n| table words |\n| :--- |\n'
                        '```python\nprint("excluded")\n```\n~~~\nexcluded\n~~~\n')
        self.assertEqual(project.prose_words(path), 3)

    def test_actual_cli_returns_json_and_failure_code(self):
        run = subprocess.run([sys.executable, str(SCRIPT), 'init', '--project', str(self.root),
                              '--initiative', 'launch'], text=True, capture_output=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(json.loads(run.stdout)['artifacts_overwritten'], 0)
        run = subprocess.run([sys.executable, str(SCRIPT), 'init', '--project', str(self.root),
                              '--initiative', '../escape'], text=True, capture_output=True)
        self.assertEqual(run.returncode, 2)
        self.assertIn('error', json.loads(run.stderr))


if __name__ == '__main__':
    unittest.main()
