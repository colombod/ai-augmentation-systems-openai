import concurrent.futures
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

repo = Path('/Users/colombod/workspaces/delivery-plugin-openai')
package = repo / 'plugins/delivery'
output = repo / 'evidence/2026-10-20/live-behavior/simulation-rerun'
output.mkdir(parents=True, exist_ok=True)
cases = [case for case in json.loads((repo / 'tests/delivery/scenarios/behavior.json').read_text())['cases'] if case['id'] == 'simulation-without-workers']
resources = {
 'status': [],
 'brief': ['templates/brief.md', 'templates/version-history.md', 'references/reviewers/product-owner.md', 'references/reviewers/business-analyst.md', 'references/reviewers/feature-critic.md'],
 'simulate': ['templates/interview.md', 'templates/simulation.md', 'references/reviewers/persona-simulator.md'],
}
base = ['references/runtime.md', 'references/conventions.md', 'templates/writing-standard.md', 'templates/glossary.md']

def run(case):
 folder = output / case['id']
 folder.mkdir(exist_ok=True)
 workspace = Path('/private/tmp/delivery-behavior-live') / case['id']
 workspace.mkdir(parents=True, exist_ok=True)
 files = ['skills/' + case['skill'] + '/SKILL.md'] + base + resources[case['skill']]
 prompt = '''Execute the supplied delivery skill for the user request below. This is a bounded behavior test using real model inference. The simulated host exposes no filesystem, shell, browsing, connection or delegation tools. Do not call tools, install anything, create files or start agents. All accessible inputs and packaged resources are supplied inline. Produce the actual user-facing artifact or answer, not an explanation of how you would perform the task. Missing information remains unknown.\n'''
 prompt += '\nUSER REQUEST\n' + case['user_request']
 prompt += '\nHOST CAPABILITIES\n' + json.dumps(case['capabilities'])
 prompt += '\nPROVIDED ARTIFACT SNAPSHOTS\n' + json.dumps(case['provided_artifacts'], ensure_ascii=False)
 hashes = {}
 for name in files:
  text = (package / name).read_text()
  hashes[name] = hashlib.sha256(text.encode()).hexdigest()
  prompt += '\n\nPACKAGED RESOURCE: ' + name + '\n' + text + '\nEND RESOURCE\n'
 (folder / 'prompt.txt').write_text(prompt)
 command = ['codex', 'exec', '--ignore-user-config', '--ephemeral', '--sandbox', 'read-only', '--skip-git-repo-check', '-C', str(workspace), '--json', '--output-last-message', str(folder / 'answer.md'), '-']
 start = time.monotonic()
 result = {'id': case['id'], 'resources_sha256': hashes, 'capability_restrictions': 'simulated in prompt; tool traces must also be inspected', 'model': 'CLI default, no model override', 'host_acceptance': 'native Codex model behavior only; not desktop or ChatGPT product acceptance'}
 with (folder / 'events.ndjson').open('w') as stdout, (folder / 'stderr.txt').open('w') as stderr:
  try:
   process = subprocess.run(command, input=prompt, text=True, stdout=stdout, stderr=stderr, timeout=180)
   result['exit_code'] = process.returncode
  except subprocess.TimeoutExpired:
   result['exit_code'] = None
   result['error'] = 'Timed out after 180 seconds; no automatic retry'
 result['elapsed_seconds'] = round(time.monotonic() - start, 2)
 result['answer_present'] = (folder / 'answer.md').is_file() and bool((folder / 'answer.md').read_text().strip())
 events = []
 for line in (folder / 'events.ndjson').read_text().splitlines():
  try: events.append(json.loads(line))
  except json.JSONDecodeError: pass
 result['event_types'] = sorted({str(event.get('type')) for event in events})
 result['items'] = [{'type': event['item'].get('type'), 'status': event['item'].get('status')} for event in events if isinstance(event.get('item'), dict)]
 result['usage'] = [event['usage'] for event in events if 'usage' in event]
 (folder / 'run.json').write_text(json.dumps(result, indent=2) + '\n')
 print(json.dumps({'id': case['id'], 'exit_code': result['exit_code'], 'answer_present': result['answer_present'], 'elapsed_seconds': result['elapsed_seconds']}), flush=True)
 return result

with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
 results = list(executor.map(run, cases))
(output / 'runs.json').write_text(json.dumps({'codex': subprocess.run(['codex','--version'], capture_output=True, text=True).stdout.strip(), 'runs': results}, indent=2) + '\n')
