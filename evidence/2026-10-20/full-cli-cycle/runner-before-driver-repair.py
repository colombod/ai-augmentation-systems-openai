"""Real public-CLI delivery cycle, through the honest operator acceptance barrier.
No manual role/task SQLite seeding; fixture setup uses real Git and Beads.
"""
from pathlib import Path
import hashlib,json,os,signal,sqlite3,subprocess,sys,tempfile,threading,time,traceback,uuid
ROOT=Path(__file__).resolve().parents[3]
EVIDENCE_ROOT=Path(__file__).resolve().parent
ATTEMPT=time.strftime('%Y%m%dT%H%M%SZ',time.gmtime())+'-'+uuid.uuid4().hex[:8]
OUT=EVIDENCE_ROOT/'attempts'/ATTEMPT
OUT.mkdir(parents=True,exist_ok=False)
(OUT/'runner-source.py').write_bytes(Path(__file__).read_bytes())
print(json.dumps({'attempt_evidence':str(OUT)}),flush=True)
RUNTIME=ROOT/'plugins/delivery/scripts/runtime.py'
MODEL='gpt-6.1-sol'
CONTRACT=('Given exactly one text argument, python3 slugify.py TEXT lowercases ASCII A-Z, converts each maximal run of characters outside ASCII [A-Za-z0-9] to one hyphen, trims edge hyphens and prints one newline with exit 0; all-separator input prints an empty line, and missing TEXT exits 2.')
BASE=Path(tempfile.mkdtemp(prefix='delivery-full-cli-')).resolve()
PLANNING=BASE/'planning';SEED=BASE/'seed';PRODUCT=BASE/'product'
PLANNING.mkdir();SEED.mkdir()
STATE={'kind':'real model/public CLI cycle through operator acceptance barrier','started_at':time.time(),'fixture':str(BASE),'planning':str(PLANNING),'product':str(PRODUCT),'model':MODEL,'contract':CONTRACT,'stages':[],'accepted':False}
serve=None;serve_serial=0;command_serial=0;last_sent={}

def save():
 (OUT/'progress.json').write_text(json.dumps(STATE,indent=2)+'\n')

def phase(name,**details):
 STATE['stage']=name;STATE['stages'].append({'stage':name,'time':time.time(),**details});save();print(json.dumps({'stage':name,**details}),flush=True)

def command(argv,cwd=None,timeout=45,check=True):
 global command_serial
 command_serial+=1
 p=subprocess.run([str(a) for a in argv],cwd=cwd,text=True,capture_output=True,timeout=timeout)
 record={'argv':[str(a) for a in argv],'cwd':str(cwd) if cwd else None,'code':p.returncode,'stdout':p.stdout,'stderr':p.stderr}
 (OUT/('command-%03d.json'%command_serial)).write_text(json.dumps(record,indent=2)+'\n')
 if check and p.returncode:raise RuntimeError('Command failed: '+str(argv[:4])+': '+p.stderr[:700])
 return p

def cli(*args,check=True):return command([sys.executable,str(RUNTIME),'--project',str(PLANNING),*args],timeout=60,check=check)
def git(root,*args):return command(['git','-C',str(root),*args])
def status():return json.loads(cli('status').stdout)
def events():
 db=sqlite3.connect('file:'+str(PLANNING/'.delivery/runtime/coordinator.sqlite')+'?mode=ro',uri=True);db.row_factory=sqlite3.Row
 try:return [{**dict(row),'data':json.loads(row['data'])} for row in db.execute('SELECT * FROM events ORDER BY id')]
 finally:db.close()
def snapshot(label):
 (OUT/(label+'-status.json')).write_text(json.dumps(status(),indent=2)+'\n')
 (OUT/(label+'-events.json')).write_text(json.dumps(events(),indent=2)+'\n')

def start():
 global serve,serve_serial
 serve_serial+=1
 stdout=(OUT/('serve-%02d.stdout.txt'%serve_serial)).open('w');stderr=(OUT/('serve-%02d.stderr.txt'%serve_serial)).open('w')
 serve=subprocess.Popen([sys.executable,str(RUNTIME),'--project',str(PLANNING),'serve'],stdout=stdout,stderr=stderr,stdin=subprocess.DEVNULL,start_new_session=True,text=True)
 stdout.close();stderr.close();STATE.setdefault('serve_instances',[]).append({'pid':serve.pid,'started_at':time.time(),'mode':'normal CLI; no operator terminal or receipt capability'});save()
 time.sleep(2)
 if serve.poll() is not None:raise RuntimeError('Public serve exited during startup')
def stop():
 global serve
 if not serve:return
 if serve.poll() is None:
  serve.send_signal(signal.SIGINT)
  try:serve.wait(timeout=20)
  except subprocess.TimeoutExpired:serve.terminate();serve.wait(timeout=10)
 STATE['serve_instances'][-1].update({'exit_code':serve.returncode,'stopped_at':time.time(),'signal':'SIGINT, normal operator stop'})
 serve=None;save()

def send(role,text):
 filename=OUT/(str(len(STATE['stages'])).zfill(2)+'-'+role+'-assignment.txt');filename.write_text(text+'\n')
 ident=json.loads(cli('send','--role',role,'--message-file',str(filename)).stdout)['message_id']
 last_sent[role]=ident;STATE.setdefault('sent_messages',[]).append({'role':role,'message_id':ident,'assignment':str(filename)});save()
 return ident

def wait_idle(names,deadline_seconds=360):
 deadline=time.monotonic()+deadline_seconds
 while time.monotonic()<deadline:
  if serve.poll() is not None:raise RuntimeError('Public serve exited while waiting')
  current=status();roles={r['name']:r for r in current['roles']};journal=events();complete=[]
  db=sqlite3.connect('file:'+str(PLANNING/'.delivery/runtime/coordinator.sqlite')+'?mode=ro',uri=True);db.row_factory=sqlite3.Row
  try:
   for name in names:
    if roles[name]['phase'] in ('needs-reconciliation','unavailable'):raise RuntimeError('Native role failed: '+name+' '+roles[name]['phase'])
    ident=last_sent.get(name)
    row=db.execute('SELECT * FROM queue WHERE id=?',(ident,)).fetchone() if ident else db.execute('SELECT * FROM queue WHERE role=? ORDER BY created DESC LIMIT 1',(name,)).fetchone()
    if not row or row['state']!='idle' or roles[name]['phase']!='idle':continue
    intent=next((e for e in journal if e['kind']=='turn_intent' and e['data'].get('message_id')==row['id']),None)
    if not intent:continue
    terminal=next((e for e in journal if e['id']>intent['id'] and e['kind']=='turn_terminal' and e['data']['role']==name),None)
    if not terminal or terminal['data']['native']['turn']['status']!='completed':continue
    native=terminal['data']['native'];turn_id=native['turn']['id']
    messages=[e for e in journal if e['kind']=='item/completed' and e['data'].get('role')==name and e['data']['native'].get('turnId')==turn_id and e['data']['native'].get('item',{}).get('type')=='userMessage']
    if not any(row['id'] in json.dumps(e['data']['native']['item'].get('content',[])) for e in messages):continue
    STATE.setdefault('queue_completion_proofs',{})[row['id']]={'role':name,'intent_event':intent['id'],'terminal_event':terminal['id'],'native_thread':native['threadId'],'native_turn':turn_id,'queue_state':row['state']}
    complete.append(name)
  finally:db.close()
  if set(complete)==set(names):save();return roles
  time.sleep(2)
 raise RuntimeError('Exact queued-message/native-terminal deadline exceeded: '+','.join(names))

def tool_results(tool):
 result=[]
 for event in events():
  d=event['data']
  if event['kind']=='controlled_tool_result' and d.get('tool')==tool:
   raw=d.get('result',{});result.append((d,json.loads(raw['contentItems'][0]['text']) if raw.get('success') else None))
 return result

def must_tool(tool):
 matches=[(d,r) for d,r in tool_results(tool) if r is not None]
 if not matches:raise RuntimeError('No actual successful native controlled tool call: '+tool)
 return matches[-1][1]

def main():
 global serve
 phase('fixture-setup')
 for root in (PLANNING,SEED):
  command(['git','init','--quiet',str(root)])
  git(root,'config','user.name','Delivery Fixture');git(root,'config','user.email','fixture@example.invalid')
 (SEED/'README.md').write_text('# Slugify fixture\n\nImplement the operator-specified ASCII-only terminal slugifier.\n')
 git(SEED,'add','README.md');git(SEED,'commit','--quiet','-m','Synthetic delivery fixture seed')
 command(['git','clone','--no-hardlinks','--quiet',str(SEED),str(PRODUCT)])
 git(PRODUCT,'checkout','--quiet','-b','delivery-slugify')
 git(PRODUCT,'config','user.name','Delivery Fixture');git(PRODUCT,'config','user.email','fixture@example.invalid')
 command(['bd','init','--prefix','fullcycle','--non-interactive','--skip-agents'],cwd=PLANNING,timeout=120)
 command([sys.executable,str(ROOT/'plugins/delivery/scripts/project.py'),'init','--project',str(PLANNING),'--initiative','slugify'])
 common='Synthetic delivery acceptance fixture. Stay within your assigned role/stage. Use only bound delivery tools for canonical writes/Beads and native shell for actual observations. Do not delegate, browse, publish, merge, push, alter hooks/security settings or imply human consent. Preserve failures. Be precise about local tests versus hosted CI (not present). '
 specs={
  'coordinator':{'cwd':str(PLANNING),'lane':'read-only','instructions':common+'Coordinate this tiny delivery and hand the brief/story drafting assignment to product-manager via delivery_send.'},
  'product-manager':{'cwd':str(PLANNING),'lane':'read-only','instructions':common+'Own concrete product brief and acceptance criteria. Read the assigned phase skill and referenced templates. Save canonical drafts via delivery_artifact_write. Do not enqueue other roles unless explicitly requested.'},
  'delivery-manager':{'cwd':str(PLANNING),'lane':'read-only','instructions':common+'Own canonical story materialization, readiness surfaces and honest gate status. Use controlled task tools; never edit Beads directly.'},
  'builder':{'cwd':str(PRODUCT),'lane':'builder','git_metadata_write':True,'instructions':common+'Claim assigned task through delivery_task_claim. Implement only the tiny Python CLI and meaningful tests in product. Capture actual test output under .delivery-evidence, commit explicit code/test paths with normal Git, submit delivery_task_implemented only after successful local tests and exact committed HEAD. Do not git add .delivery-evidence or invent CI.'},
  'reviewer':{'cwd':str(PRODUCT),'lane':'read-only','instructions':common+'Independently inspect actual code and exact HEAD. Execute meaningful tests and user CLI cases using python3 -B / PYTHONDONTWRITEBYTECODE=1; avoid heredocs/tempfiles because this lane is read-only. Save exact command/output/head findings via delivery_artifact_write to reviews/*.md. Submit independent review and surface observations with protected review file evidence. Never claim authenticated human or hosted CI.'}}
 for spec in specs.values():spec['model']=MODEL
 roster={'roles':specs}
 judge_present=bool(os.environ.get('OPENAI_API_KEY'));STATE['judge_key_present']=judge_present
 if judge_present:
  cfg=PLANNING/'.delivery/judge-config.json';cfg.write_text(json.dumps({'judge':{'provider':'openai','model':'gpt-6-luna','key_env':'OPENAI_API_KEY'}},indent=2)+'\n');roster['judge_config']=str(cfg)
 roster_path=PLANNING/'.delivery/team.json';roster_path.write_text(json.dumps(roster,indent=2)+'\n')
 phase('public-prepare',roster=str(roster_path));prepared=json.loads(cli('prepare','--roster',str(roster_path)).stdout)
 if len(prepared['roles'])!=5:raise RuntimeError('Full roster was not prepared')
 STATE['initial_head']=git(PRODUCT,'rev-parse','HEAD').stdout.strip();save();start()
 pm_task=('Draft the actual tiny ASCII slugifier brief and one executable story. Read the brief skill/resources at the known package path. Save a coherent canonical brief as initiatives/slugify/brief.md and exactly one story as stories/slugify-cli.md via delivery_artifact_write, expected_sha256=null. Story must have one concrete H1 title, a short meaningful description and exactly one ## Acceptance criteria section containing this exact single-line paragraph (no bullets, wrapping or extra criteria):\n'+CONTRACT+'\nThe intended Python CLI file is slugify.py; product root '+str(PRODUCT)+'. Unicode outside ASCII is a separator, not transliteration. Do not implement code, modify task tracker, enqueue peers or claim approval. Stop after actual draft saves and report paths.')
 judge=('First call delivery_judge with question=is_fix, state={"task":"Build a new deterministic ASCII-only slugify CLI from requirements"}, protected=false; record it only as advisory, never authorization. ' if judge_present else 'No configured judge key was available; do not call or silently select another provider. ')
 phase('coordinator-and-product-manager')
 send('coordinator',judge+'Save a short delivery plan as initiatives/slugify/delivery-plan.md via delivery_artifact_write (new file). Then call delivery_send recipient product-manager with this drafting assignment verbatim:\n'+pm_task+'\nDo not start any other role yet. After the peer handoff stop and report actual tools used.')
 roles=wait_idle(['coordinator','product-manager'],480)
 for relative in ('initiatives/slugify/delivery-plan.md','initiatives/slugify/brief.md','stories/slugify-cli.md'):
  path=PLANNING/'.delivery'/relative
  if not path.is_file():raise RuntimeError('Missing actual canonical artifact '+relative)
 story=(PLANNING/'.delivery/stories/slugify-cli.md').read_text()
 if CONTRACT not in story:raise RuntimeError('Story omitted exact acceptance contract')
 snapshot('01-manager-drafts');STATE['pm_thread_before_restart']=roles['product-manager']['thread'];phase('supervisor-restart-after-manager')
 stop();start()
 send('product-manager','Bounded same-session continuity check: using the earlier brief/story context, state the product goal and exact canonical story path. Do not write files, invoke tools or enqueue peers. This does not grant acceptance.')
 roles=wait_idle(['product-manager'],180);STATE['pm_thread_after_restart']=roles['product-manager']['thread'];STATE['same_pm_thread']=STATE['pm_thread_before_restart']==STATE['pm_thread_after_restart']
 if not STATE['same_pm_thread']:raise RuntimeError('Persistent PM session changed on restart')
 snapshot('02-after-restart');phase('materialize-and-ready')
 surface={'host':'local macOS','app':'Python slugify CLI','mode':'terminal subprocess','criterion':CONTRACT};STATE['surface']=surface
 send('delivery-manager','Read canonical stories/slugify-cli.md. First use delivery_task_materialize path=stories/slugify-cli.md to create the actual canonical Beads task. Using its actual returned issue ID call delivery_task_ready with assumptions=[] and surfaces=['+json.dumps(surface)+']. Do not claim, implement, enqueue peers, change criteria, accept or close. Report actual issue and readiness result.')
 wait_idle(['delivery-manager'],300);issue=must_tool('delivery_task_materialize')['issue'];STATE['issue']=issue;must_tool('delivery_task_ready');snapshot('03-ready');phase('builder-implementation',issue=issue,product=str(PRODUCT))
 send('builder','Task '+issue+' is ready. Call delivery_task_claim for this issue before code changes, and stop if that fails. Implement the actual CLI contract:\n'+CONTRACT+'\nUse stdlib Python, a public slugify.py CLI and meaningful unittest tests covering normal punctuation/case, separator runs/trimming, empty/no-alphanumeric input, Unicode separators and missing argument exit2. Choose your implementation yourself. Execute the tests and actual CLI examples. Capture real command/exit/output in .delivery-evidence/builder-tests.txt (untracked evidence only). Commit only explicit product/code/test files through normal Git; no global/hook/trust/security changes. Do not stage .delivery-evidence. Resolve full exact HEAD after commit. Then call delivery_task_implemented issue='+issue+', head=actual full SHA, evidence=[absolute builder-tests.txt path], passed=true only if actual local tests passed. No hosted CI is present. Do not review/accept/close/enqueue peers. Stop and report actual outcome.')
 wait_idle(['builder'],600);implementation=must_tool('delivery_task_implemented');STATE['implementation']=implementation;STATE['product_head']=git(PRODUCT,'rev-parse','HEAD').stdout.strip()
 if STATE['product_head']==STATE['initial_head'] or implementation['head']!=STATE['product_head']:raise RuntimeError('No actual matching builder commit')
 snapshot('04-implemented');phase('independent-review',product=str(PRODUCT),head=STATE['product_head'])
 send('reviewer','Independently review actual task '+issue+' at exact product HEAD '+STATE['product_head']+'. Read code and tests. Execute real tests with PYTHONDONTWRITEBYTECODE=1 and python3 -B (no filesystem writes/tempfiles/heredocs) and independently exercise CLI behavior against this contract:\n'+CONTRACT+'\nRecord exact HEAD, actual native commands, full relevant stdout/stderr/exit codes and any findings as reviews/slugify-independent.md using delivery_artifact_write expected_sha256=null. This protected review is a worker submission, not human/CI authentication. If satisfied, call delivery_task_review issue='+issue+', head=that exact SHA, evidence=['+json.dumps(str(PLANNING/'.delivery/reviews/slugify-independent.md'))+'], approved=true; otherwise approved=false and stop. After successful independent review, call delivery_task_surface for the exact declared surface '+json.dumps(surface)+', kind=real-host-observation, evidence=[same absolute protected review path], issue='+issue+', head=same SHA. No hosted CI is present; do not fabricate it. Do not change product, claim human authorization, accept or close.')
 wait_idle(['reviewer'],480);STATE['review']=must_tool('delivery_task_review');STATE['surface_submission']=must_tool('delivery_task_surface');snapshot('05-reviewed');phase('operator-acceptance-barrier')
 send('delivery-manager','For task '+issue+' inspect current actual delivery_task_gate_status and report its blockers precisely. If all submissions complete, call delivery_task_accept once to demonstrate the honest operator barrier. The supervisor has NO operator-terminal capture capability. You have no human receipt and must not invent, relay or bypass one; any refusal is expected and must be reported. Do not close/merge/push. Local tests are not hosted CI.')
 wait_idle(['delivery-manager'],240);STATE['gate_status']=must_tool('delivery_task_gate_status');snapshot('06-acceptance-barrier')
 task=json.loads(command(['bd','show',issue,'--json','--readonly','--sandbox'],cwd=PLANNING).stdout)[0];STATE['canonical_task']=task
 STATE['accept_attempts']=[{'native':d,'returned':r} for d,r in tool_results('delivery_task_accept')]
 STATE['checks']={'full_roster':len(prepared['roles'])==5,'same_pm_thread_after_restart':STATE['same_pm_thread'],'real_commit':STATE['product_head']!=STATE['initial_head'],'exact_implemented_head':implementation['head']==STATE['product_head'],'independent_reviewer_thread':STATE['review']['actor']['thread']!=implementation['actor']['thread'],'surface_head_matches':STATE['surface_submission']['head']==STATE['product_head'],'submissions_complete':STATE['gate_status']['submissions_complete'],'canonical_task_still_in_progress':task['status']=='in_progress','accepted_false':STATE['gate_status']['accepted'] is False,'honest_acceptance_refusal':any(r is None for d,r in tool_results('delivery_task_accept'))}
 phase('finished-through-human-barrier',checks=STATE['checks'])

try:
 main()
except Exception as error:
 STATE['error']=str(error);STATE['traceback']=traceback.format_exc();phase('failed',error=str(error))
finally:
 try:
  if (PLANNING/'.delivery/runtime/coordinator.sqlite').exists():snapshot('final')
 except Exception as error:STATE['snapshot_error']=str(error)
 stop();STATE['finished_at']=time.time();save();(OUT/'result.json').write_text(json.dumps(STATE,indent=2)+'\n');(OUT/'manifest.json').write_text(json.dumps({'fixture':str(BASE),'planning':str(PLANNING),'product':str(PRODUCT),'database':str(PLANNING/'.delivery/runtime/coordinator.sqlite'),'evidence':str(OUT),'scope':'real native/public CLI through operator barrier; no real human acceptance'},indent=2)+'\n')
print(json.dumps({'stage':STATE['stage'],'error':STATE.get('error'),'fixture':str(BASE),'checks':STATE.get('checks')}),flush=True)

if STATE.get("error"):
 sys.exit(1)
