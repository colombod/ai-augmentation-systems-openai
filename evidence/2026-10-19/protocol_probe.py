import subprocess,os,json,selectors,time
from pathlib import Path
b=Path(os.environ.get('DELIVERY_PROBE_ROOT', '/private/tmp/openai-marketplace-validation'))
e=dict(os.environ,CODEX_HOME=str(b/'home'),PROBE_LOG=str(b/'hook-events.ndjson'))
mode=os.environ.get('PROBE_MODE','untrusted')
args=['codex']
if mode=='vetted':args+=['--dangerously-bypass-hook-trust']
args+=['app-server','--stdio']
err=(b/(mode+'-stderr.log')).open('w')
p=subprocess.Popen(args,env=e,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=err,text=True,bufsize=1)
s=selectors.DefaultSelector();s.register(p.stdout,selectors.EVENT_READ)
seq=0;results=[]
def call(method,params):
 global seq
 seq+=1;i=seq;p.stdin.write(json.dumps({'id':i,'method':method,'params':params})+'\n');p.stdin.flush();deadline=time.monotonic()+25
 while time.monotonic()<deadline:
  if not s.select(timeout=1):continue
  line=p.stdout.readline()
  if not line:raise RuntimeError('server exited')
  r=json.loads(line)
  if r.get('id')==i:
   results.append({'method':method,'response':r})
   if 'error' in r:return {'probeError':r['error']}
   return r['result']
 raise TimeoutError(method)
try:
 call('initialize',{'clientInfo':{'name':'delivery_mechanism_probe','version':'0.1.0'},'capabilities':{'experimentalApi':True}})
 p.stdin.write(json.dumps({'method':'initialized'})+'\n');p.stdin.flush()
 call('skills/list',{'cwds':[str(b/'fixture')],'forceReload':True})
 call('hooks/list',{'cwds':[str(b/'fixture')]})
 a=call('thread/start',{'cwd':str(b/'fixture'),'approvalPolicy':'never','sandbox':'read-only','model':'gpt-6.1-sol','ephemeral':False})
 tid=os.environ.get('PROBE_RESUME_ID') or a['thread']['id']
 call('thread/read',{'threadId':tid,'includeTurns':False})
 call('thread/resume',{'threadId':tid,'excludeTurns':True})
 call('thread/fork',{'threadId':tid,'excludeTurns':True,'ephemeral':True})
 print(json.dumps({'mode':mode,'methods':[x['method'] for x in results],'threadId':tid}))
finally:
 (b/(mode+'-protocol.json')).write_text(json.dumps(results,indent=2))
 p.terminate()
 try:p.wait(timeout=5)
 except subprocess.TimeoutExpired:p.kill();p.wait()
