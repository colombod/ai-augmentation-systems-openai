import json
from pathlib import Path
import re
import unittest
import importlib.util
import tempfile
from jsonschema import ValidationError

validator_path = Path(__file__).resolve().parents[2] / 'scripts/validate_marketplace.py'
spec = importlib.util.spec_from_file_location('marketplace', validator_path)
marketplace = importlib.util.module_from_spec(spec)
spec.loader.exec_module(marketplace)

PACKAGE = Path(__file__).resolve().parents[2] / 'plugins/delivery'


class PackageTests(unittest.TestCase):
    def test_skill_resources_are_contained_and_present(self):
        skills = list((PACKAGE / 'skills').glob('*/SKILL.md'))
        self.assertEqual(len(skills), 16)
        for path in skills:
            text = path.read_text()
            self.assertTrue(text.startswith('---\nname: ' + path.parent.name + '\n'))
            # Markdown links and literal package-relative template/script paths.
            for relative in re.findall(r'(?:\.\./)+(?:references|templates|scripts)/[\w./-]+', text):
                resource = (path.parent / relative).resolve()
                self.assertTrue(resource.is_relative_to(PACKAGE), str(resource))
                self.assertTrue(resource.exists(), str(resource))
            for obsolete in ('${CLAUDE_PLUGIN_ROOT}', '~/.claude/', 'Agent tool',
                             'Skill tool', 'AskUserQuestion', '$ARGUMENTS'):
                self.assertNotIn(obsolete, text, str(path))

    def test_bounded_route_is_reachable_across_delivery_and_shipping(self):
        route = PACKAGE/'references/bounded-change.md'
        text = route.read_text()
        for phase in ('product', 'stories', 'sprint', 'sprint-review', 'realign'):
            skill = (PACKAGE/'skills'/phase/'SKILL.md').read_text()
            self.assertIn('../../references/bounded-change.md', skill, phase)
        # Retain the two routes and explicit release authority after future edits.
        stories = (PACKAGE/'skills/stories/SKILL.md').read_text()
        self.assertIn('Roadmap missing on the full-pipeline route', stories)
        for name in ('story.md', 'sprint.md', 'sprint-review.md'):
            self.assertIn('bounded', (PACKAGE/'templates'/name).read_text())
        for required in ('planned gaps and deferred gaps', 'alternatives',
                         'product-workflow', 'expected head', 'canonical source/map',
                         'receive no new write, push, merge'):
            self.assertIn(required, text)

    def test_import_provenance_covers_all_derived_material(self):
        provenance = json.loads((PACKAGE / 'upstream.json').read_text())
        self.assertRegex(provenance['revision'], r'^[a-f0-9]{40}$')
        targets = set()
        for item in provenance['files']:
            target = (PACKAGE / item['target']).resolve()
            self.assertTrue(target.is_relative_to(PACKAGE))
            self.assertTrue(target.is_file(), str(target))
            self.assertRegex(item['sha256'], r'^[a-f0-9]{64}$')
            self.assertTrue(item['adaptation'])
            self.assertNotIn(item['target'], targets)
            targets.add(item['target'])
        for folder in ('templates', 'references/reviewers'):
            for path in (PACKAGE / folder).iterdir():
                if path.name == 'product-input.json':
                    continue  # New native contract, not a claimed Claude import.
                self.assertIn(str(path.relative_to(PACKAGE)), targets)

    def test_preview_loads_no_unimplemented_runtime(self):
        manifest = json.loads((PACKAGE / 'plugin.json').read_text())
        marketplace.validate_manifest(manifest)
        self.assertTrue(any((PACKAGE / 'skills').glob('*/SKILL.md')))
        self.assertNotIn('hooks', manifest)
        self.assertNotIn('mcpServers', manifest)
        self.assertFalse((PACKAGE / 'hooks').exists())

    def test_product_methods_retain_source_pins_and_full_license_notices(self):
        provenance=json.loads((PACKAGE/'upstream.json').read_text())
        self.assertEqual(len(provenance['product_methods']),7)
        for method in provenance['product_methods']:
            self.assertRegex(method['revision'],r'^[a-f0-9]{40}$')
            notice=(PACKAGE/method['notice']).resolve()
            self.assertTrue(notice.is_relative_to(PACKAGE))
            self.assertIn('Permission is hereby granted',notice.read_text())
            self.assertIn('THE SOFTWARE IS PROVIDED "AS IS"',notice.read_text())

    def test_shipped_boundary_excludes_port_assessment_and_retains_lineage(self):
        self.assertFalse(any(PACKAGE.rglob('delivery-port-assessment.md')))
        self.assertFalse((PACKAGE / 'evidence').exists())
        for document in PACKAGE.rglob('*.md'):
            self.assertNotIn('delivery-port-assessment.md', document.read_text(), str(document))
        for name in ('CHANGELOG.md', 'NOTICE', 'LICENSE', 'upstream.json'):
            self.assertTrue((PACKAGE / name).is_file(), name)

    def test_portable_schema_rejects_legacy_root_and_nested_mistakes(self):
        good = json.loads((PACKAGE / 'plugin.json').read_text())
        cases = []
        missing_schema = dict(good)
        missing_schema.pop('$schema')
        cases.append(missing_schema)
        cases.extend(({**good, 'skills': './skills/'},
                      {**good, 'author': {'name': 'Author', 'unexpected': True}},
                      {**good, 'extensions': {'com.openai': 'not-an-object'}},
                      {**good, 'keywords': [1]}))
        for invalid in cases:
            with self.subTest(manifest=invalid), self.assertRaises(ValidationError):
                marketplace.validate_manifest(invalid)

    def test_catalogue_validation_cannot_pass_a_nonportable_root_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            package = root / 'plugins/delivery'
            package.mkdir(parents=True)
            catalogue = root / '.agents/plugins/marketplace.json'
            catalogue.parent.mkdir(parents=True)
            catalogue.write_text(json.dumps({
                'name': 'fixture', 'interface': {'displayName': 'Fixture'},
                'plugins': [{'name': 'delivery', 'source': {'source': 'local', 'path': './plugins/delivery'},
                             'category': 'Productivity',
                             'policy': {'installation': 'AVAILABLE', 'authentication': 'ON_USE'}}]}))
            manifest = json.loads((PACKAGE / 'plugin.json').read_text())
            target = package / 'plugin.json'
            target.write_text(json.dumps(manifest))
            self.assertEqual(marketplace.validate(root), 1)
            manifest['skills'] = './skills/'
            target.write_text(json.dumps(manifest))
            with self.assertRaises(ValidationError):
                marketplace.validate(root)


if __name__ == '__main__':
    unittest.main()
