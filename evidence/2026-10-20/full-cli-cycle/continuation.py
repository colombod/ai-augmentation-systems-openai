"""Resume the existing queued DM message after initial harness waiter race.
No resend, no DB mutations, no synthetic receipt, no new implementation.
"""
from pathlib import Path
import json,os,signal,sqlite3,subprocess,sys,time
ROOT=Path(__file__).resolve().parents[3];BASE=Path(__file__).resolve().parent
OUT=BASE/'continuation';OUT.mkdir(exist_ok=False)
initial=json.loads((BASE/'result.json').read_text());planning=Path(initial['planning']);runtime=ROOT/'plugins/delivery/scripts/runtime.py'
def rows():
 db=sqlite3.connect('file:'+str(planning/'.delivery/runtime/coordinator.sqlite')+'?mode=ro',uri=True);db.row_factory=sqlite3.Row
 try:
  return {'roles':[dict(r) for r in db.execute('SELECT * FROM roles')], 'queue':[dict(r) for r in db.execute('SELECT * FROM queue ORDER BY created')], 'events':[{**dict(r),'data':json.loads(r['data'])} for r in db.execute('SELECT * FROM events ORDER BY id')]}
 finally:db.close()
before=rows();target=next(r for r in reversed(before['queue']) if r['role']=='delivery-manager');role=next(r for r in before['roles'] if r['name']=='delivery-manager')
result={'kind':'public CLI continuation of existing never-started queued message after harness race','initial_error':initial['error'],'target_message_id':target['id'],'before_queue_state':target['state'],'before_role':role,'started_at':time.time(),'accepted':False}
if target['state']!='queued' or role['phase']!='idle':raise RuntimeError('This bounded continuation requires the observed queued/idle state; reconcile explicitly otherwise')
stdout=(OUT/'serve.stdout.txt').open('w');stderr=(OUT/'serve.stderr.txt').open('w')
serve=subprocess.Popen([sys.executable,str(runtime),'--project',str(planning),'serve'],stdout=stdout,stderr=stderr,stdin=subprocess.DEVNULL,text=True,start_new_session=True);stdout.close();stderr.close();result['serve_pid']=serve.pid
try:
 deadline=time.monotonic()+300
 while time.monotonic()<deadline:
  if serve.poll() is not None:raise RuntimeError('Public serve exited')
  current=rows();job=next(r for r in current['queue'] if r['id']==target['id'])
  if job['state']=='idle':
   intent=next(e for e in current['events'] if e['kind']=='turn_intent' and e['data'].get('message_id')==target['id'])
   terminal=next(e for e in current['events'] if e['id']>intent['id'] and e['kind']=='turn_terminal' and e['data']['role']=='delivery-manager')
   if terminal['data']['native']['turn']['status']!='completed':raise RuntimeError('DM native turn did not complete')
   result['actual_queue_terminal_proof']={'queue':job,'intent':intent,'terminal':terminal};break
  if job['state'] not in ('queued','started'):raise RuntimeError('Unexpected actual queue state '+job['state'])
  time.sleep(1)
 else:raise RuntimeError('Exact queued message completion deadline exceeded')
 current=rows();native=[]
 for event in current['events']:
  d=event['data']
  if event['kind']=='controlled_tool_result' and d.get('role')=='delivery-manager' and d.get('turn')==terminal['data']['native']['turn']['id']:
   native.append(d)
 result['native_controlled_results']=native
 gates=[json.loads(d['result']['contentItems'][0]['text']) for d in native if d['tool']=='delivery_task_gate_status' and d['result']['success']]
 declines=[d for d in native if d['tool']=='delivery_task_accept' and not d['result']['success']]
 if not gates or not declines:raise RuntimeError('Missing actual gate status or protected acceptance refusal')
 result['gate_status']=gates[-1];result['acceptance_refusals']=declines
 process=subprocess.run(['bd','show',initial['issue'],'--json','--readonly','--sandbox'],cwd=planning,text=True,capture_output=True,timeout=45)
 (OUT/'beads-show-command.json').write_text(json.dumps({'code':process.returncode,'stdout':process.stdout,'stderr':process.stderr},indent=2)+'\n')
 if process.returncode:raise RuntimeError('Canonical task read failed')
 task=json.loads(process.stdout)[0];result['canonical_task']=task
 result['checks']={'same_dm_thread':terminal['data']['native']['threadId']==role['thread'],'existing_queued_message_consumed_without_resend':job['id']==target['id'] and job['state']=='idle','actual_new_native_terminal':terminal['data']['native']['turn']['id']!=initial.get('gate_status',{}).get('turn'),'submissions_complete':gates[-1]['submissions_complete'],'accepted_false':gates[-1]['accepted'] is False,'canonical_task_in_progress':task['status']=='in_progress','actual_protected_accept_refusal':bool(declines)}
 result['all_pass']=all(result['checks'].values())
except Exception as error:result['error']=str(error)
finally:
 (OUT/'events.json').write_text(json.dumps(rows(),indent=2)+'\n')
 if serve.poll() is None:
  serve.send_signal(signal.SIGINT)
  try:serve.wait(timeout=20)
  except subprocess.TimeoutExpired:serve.terminate();serve.wait(timeout=10)
 result['serve_exit_code']=serve.returncode;result['finished_at']=time.time();(OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'all_pass':result.get('all_pass'),'error':result.get('error'),'checks':result.get('checks')}),flush=True)
