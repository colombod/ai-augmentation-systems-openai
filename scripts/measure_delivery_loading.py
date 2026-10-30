#!/usr/bin/env python3
"""Measure declared Delivery source-loading footprints, not model tokens or quality.

A deliberately explicit input model: queries omit authoring references; cold
product authoring loads them; the three-phase example reuses exact shared text
only while still visible at an unchanged revision. Project inputs, tools, model
output, templates, catalogue metadata and reviews are excluded from these routes.
No automatic host loader or persistent cache is implemented by this script.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
PREFIX = 'plugins/delivery/'
SHARED = ['references/runtime.md', 'references/conventions.md']
PRODUCT = ['skills/product/SKILL.md', *SHARED, 'references/product.md']
PHASES = [PRODUCT, ['skills/architecture/SKILL.md', *SHARED, 'references/product.md'],
          ['skills/stories/SKILL.md', *SHARED, 'references/product.md']]
QUERY = ['skills/product/SKILL.md', 'references/core.md']
AUTHOR = [*QUERY, 'references/product-workflow.md', *SHARED, 'references/product.md']
AFTER_PHASES = [AUTHOR, ['skills/architecture/SKILL.md', *SHARED, 'references/core.md', 'references/product.md'],
                ['skills/stories/SKILL.md', *SHARED, 'references/core.md', 'references/product.md']]
LENSES = ['references/reviewers/' + name + '.md' for name in
          ('solution-architect', 'delivery-lead', 'qa-strategist', 'feature-critic')]


def counts(data):
    return {'bytes': len(data), 'whitespace_words': len(data.decode('utf-8').split()),
            'sha256': hashlib.sha256(data).hexdigest()}


def read(relative, revision=None):
    if revision is None:
        return (ROOT / PREFIX / relative).read_bytes()
    if not re.fullmatch(r'[a-f0-9]{40}', revision):
        raise ValueError('Use an immutable full 40-character Git SHA')
    return subprocess.check_output(['git', '--no-replace-objects', '-C', str(ROOT),
                                    'show', revision + ':' + PREFIX + relative])


def footprint(paths, revision, reuse=False):
    loads = list(dict.fromkeys(paths)) if reuse else list(paths)
    resources = [{'path': path, **counts(read(path, revision))} for path in loads]
    return {'bytes': sum(item['bytes'] for item in resources),
            'whitespace_words': sum(item['whitespace_words'] for item in resources),
            'loads': len(resources), 'resources': resources}


def measure(before, after=None):
    return {
        'qualification': 'Declared source bytes/whitespace words; not observed model context, tokens, latency, cost or quality. No tokenizer or model run.',
        'before_revision': before, 'after_revision': after or 'working-tree (per-resource hashes below)',
        'exclusions': 'Project inputs, tool I/O, model output, templates, catalogue metadata and reviewer lenses. Authoring uses full references as a conservative bound.',
        'reuse_condition': 'Exact text remains visible and unchanged source revision/hash is established. Compaction, lost text or changes require rereads.',
        'focused_product_query': {'before': footprint(PRODUCT, before), 'after': footprint(QUERY, after)},
        'cold_product_authoring': {'before': footprint(PRODUCT, before), 'after': footprint(AUTHOR, after)},
        'product_architecture_stories': {
            'before_repeated_shared_reads': footprint(sum(PHASES, []), before),
            'before_unique_source_floor': footprint(sum(PHASES, []), before, reuse=True),
            'after_reuse_eligible_shared_reads': footprint(sum(AFTER_PHASES, []), after, reuse=True),
            'after_rereads_if_context_lost': footprint(sum(AFTER_PHASES, []), after)},
        'four_reviewer_lenses_unique_source': {
            'qualification': 'Lens bodies plus new shared context/core; excludes artifacts and writing conventions in both snapshots. Not a total review prompt.',
            'before': footprint(LENSES, before, reuse=True),
            'after': footprint([*LENSES, 'references/reviewer-context.md', 'references/core.md'], after, reuse=True)},
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--before', required=True)
    parser.add_argument('--after')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = measure(args.before, args.after)
    text = json.dumps(result, indent=2) + '\n'
    if args.output:
        args.output.write_text(text)
    print(text, end='')
