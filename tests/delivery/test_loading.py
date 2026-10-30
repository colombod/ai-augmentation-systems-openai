"""Static source/loading contracts; these do not evaluate model compliance."""
import importlib.util
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / 'plugins/delivery'
spec = importlib.util.spec_from_file_location('loading_measure', ROOT / 'scripts/measure_delivery_loading.py')
loading = importlib.util.module_from_spec(spec)
spec.loader.exec_module(loading)


class LoadingTests(unittest.TestCase):
    def test_counts_are_actual_utf8_bytes_and_whitespace_words(self):
        result = loading.counts('é one\n two'.encode())
        self.assertEqual(result['bytes'], 11)
        self.assertEqual(result['whitespace_words'], 3)
        self.assertEqual(len(result['sha256']), 64)

    def test_resources_survive_packaging_and_link_resolution(self):
        paths = set(loading.AUTHOR)
        paths.update('references/reviewers/' + name + '.md' for name in
                     ('solution-architect', 'delivery-lead', 'qa-strategist', 'feature-critic'))
        paths.add('references/reviewer-context.md')
        for relative in paths:
            path = PACKAGE / relative
            self.assertTrue(path.is_file(), relative)
            for link in re.findall(r'\]\(([^)#]+)(?:#[^)]*)?\)', path.read_text()):
                if '://' in link:
                    continue
                target = (path.parent / link).resolve()
                self.assertTrue(target.is_relative_to(PACKAGE), link)
                self.assertTrue(target.is_file(), (relative, link))

    def test_focused_route_retains_constraints_without_authoring_payload(self):
        skill = (PACKAGE / 'skills/product/SKILL.md').read_text()
        focused = skill.split('## Focused read-only map question')[1].split('## Create, assess')[0]
        self.assertIn('references/core.md', skill)
        self.assertIn('impact --path', focused)
        self.assertNotIn('references/conventions.md', focused)
        self.assertNotIn('templates/product-input.json', focused)
        self.assertIn('product-workflow.md', skill)
        core = (PACKAGE / 'references/core.md').read_text()
        for necessary in ('AGENTS.md', 'nearest existing ancestor', 'multi-component',
                          'canonical store', 'blocking findings', 'owner',
                          'expected revisions/hashes', 'compaction', 'content hash',
                          'Greenfield and brownfield', 'not Seen', 'Retirement',
                          'merge or deploy', 'unmapped'):
            self.assertIn(necessary, core)
        self.assertIn('not the\nworkflow', core)
        self.assertIn('after compaction', skill)

    def test_relevant_lenses_use_common_context_and_allow_absent_code(self):
        for name in ('solution-architect', 'delivery-lead', 'qa-strategist', 'feature-critic'):
            lens = (PACKAGE / 'references/reviewers' / (name + '.md')).read_text()
            self.assertIn('../reviewer-context.md', lens)
            self.assertNotIn('Your system prompt survives compaction', lens)
        architect = (PACKAGE / 'references/reviewers/solution-architect.md').read_text()
        stories = (PACKAGE / 'references/reviewers/delivery-lead.md').read_text()
        self.assertIn('no code or repository', architect)
        self.assertIn('no repository', stories)
        self.assertIn('New files need not already exist', stories)
        self.assertIn('command\navailability unverified', stories)
        self.assertNotIn('the real files that will change', stories)

    def test_measurement_does_not_count_unread_refs_as_free_or_invent_tokens(self):
        repeated = loading.footprint(loading.AUTHOR * 2, None)
        reused = loading.footprint(loading.AUTHOR * 2, None, reuse=True)
        self.assertEqual(repeated['bytes'], 2 * reused['bytes'])
        self.assertEqual(reused['loads'], len(set(loading.AUTHOR)))
        self.assertEqual(set(reused['resources'][0]), {'path', 'bytes', 'whitespace_words', 'sha256'})
        with self.assertRaises(ValueError):
            loading.read('skills/product/SKILL.md', '--arbitrary-option')


if __name__ == '__main__':
    unittest.main()
