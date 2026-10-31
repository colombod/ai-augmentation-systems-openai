#!/usr/bin/env python3
"""Check isolated hook-plugin installation/discovery without models or trust bypass."""
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


def probe(manifest_mode='package'):
    with tempfile.TemporaryDirectory(prefix='hook-event-log-install-') as temporary:
        base = Path(temporary).resolve()
        home, market, project = (base / name for name in ('home', 'market', 'project'))
        for path in (home, market, project):
            path.mkdir()
        package = market / 'plugins/hook-event-log'
        shutil.copytree(ROOT / 'plugins/hook-event-log', package,
                        ignore=shutil.ignore_patterns('node_modules', 'target', '__pycache__'))
        if manifest_mode in {'portable', 'both'}:
            legacy = package / '.codex-plugin/plugin.json'
            manifest = json.loads(legacy.read_text())
            portable = {key: manifest[key] for key in ('name', 'version', 'description')}
            portable.update({'$schema': 'https://agent-plugins.org/schemas/1.0.0/plugin.schema.json',
                             'extensions': {'com.openai': {'hooks': './hooks/hooks.json'}}})
            (package / 'plugin.json').write_text(json.dumps(portable))
            if manifest_mode == 'portable':
                legacy.unlink()
        catalog = json.loads((ROOT / '.agents/plugins/marketplace.json').read_text())
        catalog['plugins'] = [entry for entry in catalog['plugins']
                              if entry['name'] == 'hook-event-log']
        target = market / '.agents/plugins/marketplace.json'
        target.parent.mkdir(parents=True)
        target.write_text(json.dumps(catalog))
        env = {key: value for key, value in os.environ.items()
               if not key.endswith('_API_KEY') and key not in
               {'CODEX_API_KEY', 'OPENAI_ACCESS_TOKEN', 'PLUGIN_ROOT', 'PLUGIN_DATA'}}
        env['CODEX_HOME'] = str(home)

        def command(*args):
            result = subprocess.run(['codex', *args], env=env, cwd=project,
                                    capture_output=True, text=True, timeout=45)
            if result.returncode:
                raise RuntimeError(f'Command failed: {args[0]}: {result.stderr}')
            return result.stdout.strip()

        version = command('--version')
        registered = json.loads(command('plugin', 'marketplace', 'add', str(market), '--json'))
        installed = json.loads(command('plugin', 'add',
                                       'hook-event-log@ai-augmentation-systems-openai', '--json'))
        listed = json.loads(command('plugin', 'list', '--json'))
        messages = queue.Queue()
        with (base / 'server.stderr').open('w') as errors:
            process = subprocess.Popen(['codex', 'app-server', '--stdio'], env=env,
                                       cwd=project, stdin=subprocess.PIPE,
                                       stdout=subprocess.PIPE, stderr=errors,
                                       text=True, bufsize=1)

            def receive():
                for line in process.stdout:
                    messages.put(json.loads(line))
                messages.put(None)

            threading.Thread(target=receive, daemon=True).start()
            serial = 0

            def call(method, params):
                nonlocal serial
                serial += 1
                process.stdin.write(json.dumps({'id': serial, 'method': method,
                                                'params': params}) + '\n')
                process.stdin.flush()
                deadline = time.monotonic() + 30
                while time.monotonic() < deadline:
                    message = messages.get(timeout=max(.01, deadline - time.monotonic()))
                    if message is None:
                        raise RuntimeError('Native app server exited before response')
                    if message.get('id') == serial:
                        if 'error' in message:
                            raise RuntimeError(message['error'])
                        return message['result']
                raise TimeoutError(method)

            try:
                call('initialize', {'clientInfo': {'name': 'hook_event_log_install_probe',
                                                 'version': '0.1.0'},
                                    'capabilities': {'experimentalApi': True}})
                process.stdin.write('{"method":"initialized"}\n')
                process.stdin.flush()
                hooks = call('hooks/list', {'cwds': [str(project)]})
                discovered = [hook for entry in hooks['data'] for hook in entry['hooks']
                              if hook.get('pluginId') == 'hook-event-log@ai-augmentation-systems-openai']
                expected_names = {name[0].lower() + name[1:] for name in
                                  json.loads((package / 'hooks/hooks.json').read_text())['hooks']}
                if manifest_mode == 'package':
                    assert {hook['eventName'] for hook in discovered} == expected_names
                    assert len(discovered) == 12
                    assert all(hook['enabled'] and hook['trustStatus'] == 'untrusted'
                               for hook in discovered)
                    assert not any(entry['warnings'] or entry['errors'] for entry in hooks['data'])
                # No turn/model call and no trust mutation. This also tests that
                # merely installing a package does not execute unreviewed hooks.
                thread = call('thread/start', {'cwd': str(project),
                                              'approvalPolicy': 'never',
                                              'sandbox': 'read-only', 'ephemeral': True})
                time.sleep(.2)
                logs = list(home.rglob('*.jsonl'))
                event_logs = [str(p.relative_to(home)) for p in logs
                              if p.parent.name == 'event-types']
                assert not event_logs, 'Untrusted hooks must not create event logs'
                installed_root = Path(installed['installedPath'])
                data_root = base / 'manual-protocol-data'
                callback = subprocess.run(['node', str(installed_root / 'dist/hook.js')],
                                          input=json.dumps({'hook_event_name': 'Stop',
                                                            'session_id': 'install-probe',
                                                            'prompt': 'MUST_NOT_BE_LOGGED'}),
                                          env=dict(env, PLUGIN_DATA=str(data_root)),
                                          capture_output=True, text=True, timeout=4)
                assert callback.returncode == 0 and not callback.stdout and not callback.stderr
                filename = hashlib.sha256(b'install-probe').hexdigest() + '.jsonl'
                assert (data_root / 'event-types' / filename).read_text() == '{"event_type":"Stop"}\n'
                return {'codex': version, 'registration': registered, 'install': installed,
                        'listed': listed, 'manifest_mode': manifest_mode,
                        'isolated_config': (home / 'config.toml').read_text(),
                        'hooks': hooks, 'thread_started': bool(thread.get('thread')),
                        'event_logs_before_trust': event_logs,
                        'installed_adapter_direct_protocol': 'passed; direct invocation, not host-fired hook',
                        'discovered_hooks': len(discovered),
                        'model_calls': 0, 'trust_bypass': False,
                        'desktop_acceptance': 'unable-to-check; independent required surface'}
            finally:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--manifest-mode', choices=['package', 'portable', 'both'], default='package',
                        help='Compare temporary manifest layouts without changing the package')
    args = parser.parse_args()
    result = probe(args.manifest_mode)
    rendered = json.dumps(result, indent=2)
    if args.output:
        args.output.write_text(rendered + '\n')
    print(json.dumps({key: result[key] for key in
                      ('codex', 'manifest_mode', 'discovered_hooks',
                       'installed_adapter_direct_protocol', 'trust_bypass', 'model_calls')}))
