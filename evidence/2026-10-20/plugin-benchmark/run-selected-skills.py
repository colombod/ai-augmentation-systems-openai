"""Real-model benchmark of installed resources selected through native skill input.
Skills are exposed via temporary workspace aliases, not installed into the user's home.
"""
from pathlib import Path
import hashlib,json,os,queue,shutil,subprocess,tempfile,threading,time
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent/'selected-skills-run2';OUT.mkdir(exist_ok=True)
base=Path(tempfile.mkdtemp(prefix='delivery-selected-benchmark-')).resolve();home=base/'home';market=base/'market';project=base/'project'
for p in [home,project]:p.mkdir()
shutil.copytree(ROOT/'plugins/delivery',market/'plugins/delivery',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
catalog=market/'.agents/plugins/marketplace.json';catalog.parent.mkdir(parents=True);shutil.copy(ROOT/'.agents/plugins/marketplace.json',catalog)
env=dict(os.environ,CODEX_HOME=str(home))
for key in list(env):
 if key.endswith('_API_KEY') or key in ['OPENAI_ACCESS_TOKEN','CODEX_API_KEY']:env.pop(key)
for args in [['plugin','marketplace','add',str(market),'--json'],['plugin','add','delivery@ai-augmentation-systems-openai','--json']]:
 r=subprocess.run(['codex',*args],env=env,cwd=project,text=True,capture_output=True,timeout=45)
 if r.returncode:raise RuntimeError(r.stderr)
installed=next(p.parent for p in (home/'plugins/cache').rglob('plugin.json') if json.loads(p.read_text()).get('name')=='delivery')
aliases=project/'.agents/skills';aliases.mkdir(parents=True)
for name in ['start','brief','status']:(aliases/('delivery-'+name)).symlink_to(installed/'skills'/name,target_is_directory=True)
(project/'idea.md').write_text('Synthetic benchmark inputs, not real customer research. Idea: local checklist for solo freelance translators tracking client handover requirements. Problem hypothesis: scattered notes may cause omitted requested files. No error rates, willingness to pay, time savings or interviews supplied. Candidate success signal: proportion of handovers meeting recorded client requirements. Open-question owner: benchmark requester. No integrations, billing or automatic sending in scope.\n')
errors=(OUT/'server.stderr').open('w');p=subprocess.Popen(['codex','app-server','--stdio'],cwd=project,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=errors,text=True,bufsize=1)
q=queue.Queue();raw=(OUT/'protocol.ndjson').open('w')
def reader():
 for line in p.stdout:
  raw.write(line);raw.flush()
  try:q.put(json.loads(line))
  except ValueError:pass
 q.put(None)
threading.Thread(target=reader,daemon=True).start();serial=0
# Never automatically approve an escalation or ask an invented human answer.
def nextmsg(deadline):
 m=q.get(timeout=max(.01,deadline-time.monotonic()))
 if m is None:raise RuntimeError('server exited')
 if 'id' in m and 'method' in m:
  p.stdin.write(json.dumps({'id':m['id'],'error':{'code':-32000,'message':'Benchmark does not authorize interactive requests or escalations'}})+'\n');p.stdin.flush()
 return m

def call(method,params):
 global serial
 serial+=1;i=serial;p.stdin.write(json.dumps({'id':i,'method':method,'params':params})+'\n');p.stdin.flush();deadline=time.monotonic()+40
 while time.monotonic()<deadline:
  m=nextmsg(deadline)
  if m.get('id')==i:
   if 'error'in m:raise RuntimeError(m['error'])
   return m['result']

def snapshot():return {str(f.relative_to(project)):hashlib.sha256(f.read_bytes()).hexdigest() for f in project.rglob('*') if f.is_file() and '.agents' not in f.parts}
results=[]
try:
 call('initialize',{'clientInfo':{'name':'delivery_benchmark','version':'0.1.0'},'capabilities':{'experimentalApi':True}})
 p.stdin.write('{"method":"initialized"}\n');p.stdin.flush()
 discovery=call('skills/list',{'cwds':[str(project)],'forceReload':True});(OUT/'discovery.json').write_text(json.dumps(discovery,indent=2))
 cases=[('start','Initialize this project for a new initiative named translator-handover. Do not create a placeholder brief.'),('brief','Frame translator-handover using idea.md. Use single-session lenses; do not delegate or browse. Write the brief and required glossary locally. Leave unanswered questions explicitly open with benchmark requester as owner; this bounded test does not wait for replies. Do not invent evidence.'),('status','Inspect translator-handover. Report existing artifacts, missing prerequisites and unknown readiness honestly. This request is read-only.')]
 for name,prompt in cases:
  folder=OUT/name;folder.mkdir();before=snapshot();start=time.monotonic()
  prompt+=' Use only this temporary project and the selected installed skill resources. Do not search the user home, read credentials, change user configuration, start agents or browse.'
  skill=next(s for row in discovery['data'] for s in row['skills'] if s['name']==name and Path(s['path']).is_relative_to(installed))
  request={'cwd':str(project),'ephemeral':True,'sandbox':'workspace-write'}
  thread=call('thread/start',request);tid=thread['thread']['id']
  (folder/'thread-metadata.json').write_text(json.dumps({k:v for k,v in thread.items() if k!='thread'},indent=2))
  inputs=[{'type':'text','text':prompt},{'type':'skill','name':skill['name'],'path':skill['path']}]
  (folder/'input.json').write_text(json.dumps(inputs,indent=2));turn=call('turn/start',{'threadId':tid,'input':inputs});events=[];deadline=time.monotonic()+240
  while time.monotonic()<deadline:
   m=nextmsg(deadline);events.append(m)
   if m.get('method')=='turn/completed' and m.get('params',{}).get('threadId')==tid:break
  else:raise TimeoutError(name)
  completed=[e['params']['item'] for e in events if e.get('method')=='item/completed' and 'item'in e.get('params',{})]
  answers=[i.get('text','') for i in completed if i.get('type')=='agentMessage']
  (folder/'answer.md').write_text('\n\n'.join(answers))
  row={'case':name,'elapsed_seconds':round(time.monotonic()-start,2),'before_sha256':before,'after_sha256':snapshot(),'events':events,'turn':events[-1],'skill':skill,'thread_model':thread.get('model')}
  (folder/'run.json').write_text(json.dumps(row,indent=2));results.append(row);print(json.dumps({'case':name,'seconds':row['elapsed_seconds'],'turn':events[-1]}),flush=True)
finally:
 p.terminate()
 try:p.wait(timeout=5)
 except subprocess.TimeoutExpired:p.kill();p.wait()
 raw.close();errors.close()
 shutil.copytree(project,OUT/'artifacts',ignore=shutil.ignore_patterns('.agents'))
 (OUT/'runs.json').write_text(json.dumps({'codex':subprocess.run(['codex','--version'],capture_output=True,text=True).stdout.strip(),'installed_root':str(installed),'workspace':str(project),'provisioning':'installed isolated plugin; three temporary workspace aliases; native selected-skill turn input; existing default sign-in/config for model calls, no credentials or config copied','runs':results},indent=2))
