"""Bounded real CLI benchmark; no copied auth/config, no personal install commands."""
from pathlib import Path
import hashlib, json, os, shutil, subprocess, tempfile, time
ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent/'native';OUT.mkdir(exist_ok=True)
base=Path(tempfile.mkdtemp(prefix='delivery-native-benchmark-')).resolve()
market=base/'market';project=base/'project';project.mkdir()
shutil.copytree(ROOT/'plugins/delivery',market/'plugins/delivery',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
catalog=market/'.agents/plugins/marketplace.json';catalog.parent.mkdir(parents=True);shutil.copy(ROOT/'.agents/plugins/marketplace.json',catalog)
(project/'idea.md').write_text('''Synthetic benchmark inputs; no real customer research. New idea: a local checklist for freelance translators to track client handover requirements. Current problem hypothesis: translators assemble requirements from scattered notes and may omit a requested file. Target segment: solo freelance translators. No measured error rate, willingness to pay, time saving or real interviews are supplied. Candidate success signal: proportion of handovers satisfying an explicitly recorded client checklist. Owner for unanswered product questions: benchmark requester. No integration, billing or automatic sending in scope.\n''')
config=['-c','marketplaces.ai-augmentation-systems-openai.source_type="local"','-c','marketplaces.ai-augmentation-systems-openai.source='+json.dumps(str(market)),'-c','plugins."delivery@ai-augmentation-systems-openai".enabled=true']
cases=[('start','$delivery:start\nInitialize this project for a new initiative named translator-handover. Use the packaged skill. Do not create a placeholder brief. Do not delegate or browse.'),('brief','$delivery:brief\nFrame translator-handover using idea.md. Use the packaged skill and its actual resources. Use single-session review without delegation or browsing. Write the brief and any required shared glossary to this local workspace. Leave unanswered questions explicitly open with benchmark requester as owner; do not wait for answers in this bounded test. Do not invent measurements or interviews.'),('status','$delivery:status\nInspect this project and translator-handover. Use the packaged skill. Report existing artifacts, missing prerequisites, and unknown readiness honestly. This is a read-only status request. Do not delegate or browse.')]
def snapshot():
 return {str(p.relative_to(project)):hashlib.sha256(p.read_bytes()).hexdigest() for p in project.rglob('*') if p.is_file()}
results=[]
for name,prompt in cases:
 folder=OUT/name;folder.mkdir();(folder/'prompt.txt').write_text(prompt)
 before=snapshot();start=time.monotonic()
 command=['codex','exec','--ignore-user-config','--ephemeral',*config,'--sandbox','workspace-write','--skip-git-repo-check','-C',str(project),'--json','--output-last-message',str(folder/'answer.md'),'-']
 with (folder/'events.ndjson').open('w') as stdout,(folder/'stderr.txt').open('w') as stderr:
  try:
   proc=subprocess.run(command,input=prompt,text=True,stdout=stdout,stderr=stderr,timeout=240)
   code=proc.returncode;error=None
  except subprocess.TimeoutExpired:code=None;error='240-second timeout; no retry'
 after=snapshot();events=[]
 for line in (folder/'events.ndjson').read_text().splitlines():
  try:events.append(json.loads(line))
  except ValueError:pass
 row={'case':name,'exit_code':code,'error':error,'elapsed_seconds':round(time.monotonic()-start,2),'before_sha256':before,'after_sha256':after,'usage':[e['usage'] for e in events if 'usage' in e],'items':[e['item'] for e in events if isinstance(e.get('item'),dict)],'answer_present':(folder/'answer.md').exists()}
 (folder/'run.json').write_text(json.dumps(row,indent=2));results.append(row)
 print(json.dumps({k:row[k] for k in ['case','exit_code','elapsed_seconds','answer_present','usage']}),flush=True)
 # Stop dependent workflow on infrastructure failure; preserve its evidence.
 if code != 0:break
shutil.copytree(project,OUT/'artifacts')
(OUT/'runs.json').write_text(json.dumps({'codex':subprocess.run(['codex','--version'],text=True,capture_output=True).stdout.strip(),'model':'CLI default; no model override','workspace':str(project),'marketplace':str(market),'activation':'qualified skill mention and command-line marketplace configuration; no inline source injection','runs':results},indent=2))
