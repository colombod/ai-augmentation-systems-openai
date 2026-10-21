"""Independent read-only black-box grade of the declared synthetic CLI contract.

The builder does not receive this case list. No product source is modified.
This grader checks behavior, not human approval or production suitability.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('product', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    product = args.product.resolve()
    source = product / 'slugify.py'
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    cases = [
        ('Hello WORLD', 'hello-world'),
        ('  one...two___THREE  ', 'one-two-three'),
        ('', ''),
        ('---___!!!', ''),
        ('ABCxyz019', 'abcxyz019'),
        ('Été', 't'),
        ('東京', ''),
        ('foo東京BAR', 'foo-bar'),
        ('A\u0301b', 'a-b'),
        ('\tAlpha\nBeta\rGamma\t', 'alpha-beta-gamma'),
        ('0 00 007', '0-00-007'),
        ('a-b', 'a-b'),
        ('a---b', 'a-b'),
        ('UPPER lower MiXeD', 'upper-lower-mixed'),
        ('a/b\\c:d;e', 'a-b-c-d-e'),
        ('a💡b', 'a-b'),
        ('a\u00a0b', 'a-b'),
        ('Kelvin', 'elvin'),
        ('İSTANBUL', 'stanbul'),
        ('a' * 1024, 'a' * 1024),
    ]
    observations = []
    environment = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    for value, expected in cases:
        result = subprocess.run([sys.executable, '-B', str(source), value],
                                cwd=product, capture_output=True, text=True,
                                timeout=10, env=environment)
        observations.append({'input': value, 'expected': expected + '\n',
                             'code': result.returncode, 'stdout': result.stdout,
                             'stderr': result.stderr,
                             'passed': result.returncode == 0 and result.stdout == expected + '\n'})
    missing = subprocess.run([sys.executable, '-B', str(source)], cwd=product,
                             capture_output=True, text=True, timeout=10, env=environment)
    observations.append({'case': 'missing text', 'code': missing.returncode,
                         'stdout': missing.stdout, 'stderr': missing.stderr,
                         'passed': missing.returncode == 2 and missing.stdout == ''})
    after = hashlib.sha256(source.read_bytes()).hexdigest()
    output = {'kind': 'independent implementation-session black-box grade',
              'contract': 'ASCII alphanumeric slug CLI; Unicode separators; missing argument exit2',
              'product': str(product), 'source_sha256': before,
              'source_unchanged': before == after, 'cases': observations,
              'passed': sum(item['passed'] for item in observations),
              'total': len(observations),
              'acceptance': 'behavior only; no operator, CI, desktop or ChatGPT acceptance'}
    args.output.write_text(json.dumps(output, indent=2) + '\n')
    print(json.dumps({key: output[key] for key in ('passed', 'total', 'source_unchanged')}))
    return 0 if output['passed'] == output['total'] and output['source_unchanged'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
