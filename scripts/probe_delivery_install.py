#!/usr/bin/env python3
"""Install and discover delivery in an isolated Codex home. No model calls."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import queue
import shutil
import subprocess
import tempfile
import threading
import time

ROOT = Path(__file__).resolve().parents[1]


def probe():
    with tempfile.TemporaryDirectory(prefix='delivery-install-') as directory:
        base = Path(directory).resolve()
        home, market, project = (base / name for name in ('home', 'market', 'project'))
        for path in (home, market, project):
            path.mkdir()
        shutil.copytree(ROOT / 'plugins/delivery', market / 'plugins/delivery',
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        catalog = market / '.agents/plugins/marketplace.json'
        catalog.parent.mkdir(parents=True)
        data = json.loads((ROOT / '.agents/plugins/marketplace.json').read_text())
        data['plugins'] = [entry for entry in data['plugins'] if entry['name'] == 'delivery']
        catalog.write_text(json.dumps(data))
        env = dict(os.environ, CODEX_HOME=str(home))
        # Discovery needs neither the user's credentials nor model configuration.
        for key in list(env):
            if key.endswith('_API_KEY') or key in {'OPENAI_ACCESS_TOKEN', 'CODEX_API_KEY'}:
                env.pop(key)

        def command(*args):
            result = subprocess.run(['codex', *args], cwd=project, env=env,
                                    capture_output=True, text=True, timeout=45)
            if result.returncode:
                raise RuntimeError(f'codex {args[0]} failed: {result.stderr}')
            return result.stdout.strip()

        version = command('--version')
        command('plugin', 'marketplace', 'add', str(market), '--json')
        command('plugin', 'add', 'delivery@ai-augmentation-systems-openai', '--json')
        messages = queue.Queue()
        with (base / 'server.stderr').open('w') as errors:
            process = subprocess.Popen(['codex', 'app-server', '--stdio'], cwd=project, env=env,
                                       stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                       stderr=errors, text=True, bufsize=1)

            def receive():
                for line in process.stdout:
                    messages.put(json.loads(line))
                messages.put(None)

            reader = threading.Thread(target=receive, daemon=True)
            reader.start()
            serial = 0

            def call(method, params):
                nonlocal serial
                serial += 1
                process.stdin.write(json.dumps({'id': serial, 'method': method, 'params': params}) + '\n')
                process.stdin.flush()
                deadline = time.monotonic() + 30
                while time.monotonic() < deadline:
                    message = messages.get(timeout=max(.01, deadline - time.monotonic()))
                    if message is None:
                        raise RuntimeError('App server exited before reply')
                    if message.get('id') == serial:
                        if 'error' in message:
                            raise RuntimeError(message['error'])
                        return message['result']
                raise TimeoutError(method)

            try:
                call('initialize', {'clientInfo': {'name': 'delivery_install_probe', 'version': '0.1.0'},
                                    'capabilities': {'experimentalApi': True}})
                process.stdin.write('{"method":"initialized"}\n')
                process.stdin.flush()
                result = call('skills/list', {'cwds': [str(project)], 'forceReload': True})
                def from_package(skill):
                    path = Path(skill['path'])
                    manifest = path.parents[2] / 'plugin.json'
                    return (path.is_relative_to(home) and manifest.is_file()
                            and json.loads(manifest.read_text()).get('name') == 'delivery')

                skills = [s for row in result['data'] for s in row['skills'] if from_package(s)]
                failures = [e for row in result['data'] for e in row['errors']
                            if 'delivery' in str(e)]
                expected = {p.parent.name for p in (ROOT / 'plugins/delivery/skills').glob('*/SKILL.md')}
                actual = {s['name'].split(':')[-1] for s in skills}
                if actual != expected or failures:
                    raise AssertionError({'expected': sorted(expected), 'discovered': sorted(actual), 'errors': failures})
                # Confirm the installed package includes its non-skill resources.
                installed_root = Path(skills[0]['path']).parents[2]
                if any(installed_root.rglob('delivery-port-assessment.md')):
                    raise AssertionError('Internal port assessment was included in the installed package')
                lineage_files = ('CHANGELOG.md', 'NOTICE', 'LICENSE', 'upstream.json')
                if not all((installed_root / name).is_file() for name in lineage_files):
                    raise AssertionError('Installed package is missing release lineage or attribution')
                loading_resources = {}
                for relative in ('skills/product/SKILL.md', 'references/core.md',
                                 'references/product.md',
                                 'references/reviewer-context.md'):
                    data = (installed_root / relative).read_bytes()
                    if data != (ROOT / 'plugins/delivery' / relative).read_bytes():
                        raise AssertionError(f'Installed loading resource differs: {relative}')
                    loading_resources[relative] = hashlib.sha256(data).hexdigest()
                helper = installed_root / 'scripts/project.py'
                init = subprocess.run(['python3', str(helper), 'init', '--project', str(project),
                                       '--initiative', 'probe'], text=True, capture_output=True, timeout=10)
                if init.returncode:
                    raise RuntimeError(init.stderr)
                # Verify the new product contract/helper survives installation,
                # independently of any source checkout or model invocation.
                product_helper = installed_root / 'scripts/product.py'
                if not product_helper.is_file():
                    raise AssertionError('Installed package is missing product.py')
                outline = project/'outline.json'
                outline.write_text(json.dumps({'features':[{'id':'first-result','name':'Illustrative first result'}]}))
                drafted = subprocess.run(['python3','-B',str(product_helper),'--project',str(project),
                    'draft','--outline',str(outline)],text=True,capture_output=True,timeout=10)
                if drafted.returncode:
                    raise RuntimeError('Installed product draft failed: '+drafted.stderr)
                draft_input = project/'draft-input.json';draft_input.write_text(drafted.stdout)
                product_record = subprocess.run(['python3', '-B', str(product_helper), '--project', str(project),
                    'record', '--input', str(draft_input),
                    '--expected-sha256', 'new'], text=True, capture_output=True, timeout=10)
                if product_record.returncode:
                    raise RuntimeError('Installed product record failed: '+product_record.stderr)
                handoff = subprocess.run(['python3', '-B', str(product_helper), '--project', str(project),
                    'handoff'], text=True, capture_output=True, timeout=10)
                product = json.loads(handoff.stdout)
                if handoff.returncode != 1 or not product.get('unconfirmed_choices') or product['freshness']['snapshot_commit'] is not None:
                    raise AssertionError('Installed greenfield helper hid unknown choices or invented source')
                return {'codex': version, 'package_version': json.loads((installed_root / 'plugin.json').read_text())['version'],
                        'installed_loading_resources': loading_resources,
                        'installation': 'passed', 'skills_discovered': sorted(s['name'] for s in skills),
                        'installed_helper': 'passed', 'model_calls': 0,
                        'installed_product_helper': {'draft':'passed','record':'passed', 'handoff':'passed',
                            'qualification':'illustrative greenfield template; unconfirmed choices retained; no model or customer-use claim'},
                        'package_boundary': {'port_assessment': 'excluded', 'release_lineage': 'present'},
                        'acceptance': {'cli_install_and_discovery': 'passed', 'real_model_workflow': 'not-tested',
                                       'desktop_ui': 'not-tested', 'chatgpt': 'not-tested'}}
            finally:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                reader.join(timeout=2)
                process.stdin.close()
                process.stdout.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = probe()
    text = json.dumps(result, indent=2) + '\n'
    if args.output:
        args.output.write_text(text)
    print(text, end='')
