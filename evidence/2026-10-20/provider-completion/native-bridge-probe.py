"""Two native coordinator-to-judge smoke calls; synthetic states, no auth copies."""
from pathlib import Path
import hashlib,json,sys,tempfile,time
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'plugins/delivery/scripts'))
from runtime import Store,Coordinator
OUT=Path(__file__).resolve().parent
STATE={'candidate':'Repair an existing checklist item that cannot be unchecked','linked_item':'Previously shipped checklist','context':'An existing control fails when a person tries to undo a completed item'}
report={'kind':'actual native read-only role -> controlled delivery_judge -> selected live provider','fixture':'Manually seeded temporary role and operator-pinned judge settings; not full roster prepare/Beads workflow acceptance. Native thread creation, lane verification, tool dispatch and provider invocation are production paths.','model':'gpt-6.1-sol','synthetic_state':STATE,'runs':[],'started':time.time()}
for provider,model in [('jev','jev-1.13.0'),('openai','gpt-6-luna')]:
 with tempfile.TemporaryDirectory(prefix='delivery-native-judge-') as tmp:
  project=Path(tmp).resolve();(project/'.delivery').mkdir()
  config=project/'operator-judge.json';document={'judge':{'provider':provider,'model':model}}
  raw=json.dumps(document,sort_keys=True).encode();config.write_bytes(raw)
  store=Store(project);spec={'cwd':str(project),'model':'gpt-6.1-sol','lane':'read-only','instructions':'Bounded synthetic integration test. Use only delivery_judge once with the exact question and state requested. Do not delegate, browse, run shell commands, change configuration or use other tools. Report the actual typed answer and provider. The judge provides no human authority.'}
  store.db.execute("INSERT INTO roles VALUES('coordinator',?,NULL,NULL,'prepared',NULL)",(json.dumps(spec),))
  for key,value in {'judge_config':str(config),'judge_config_source_sha256':hashlib.sha256(raw).hexdigest(),'judge_config_json':json.dumps(document,sort_keys=True)}.items():
   store.db.execute('INSERT INTO settings VALUES(?,?)',(key,value))
  coordinator=None;run={'provider':provider,'configured_model':model,'planning':str(project),'fixture_config_sha256':hashlib.sha256(raw).hexdigest()}
  try:
   coordinator=Coordinator(store)
   store.enqueue('coordinator','Call delivery_judge exactly once with this exact JSON argument: '+json.dumps({'question':'is_fix','state':STATE,'protected':False})+'. Do not call any other tool. Then report actual answer, provider and human_authority.')
   coordinator.step();deadline=time.monotonic()+150
   while time.monotonic()<deadline and store.status()['roles'][0]['phase']=='active':
    coordinator.rpc.dispatch(timeout=.5);coordinator.step()
   run['role']=store.status()['roles'][0]
   run['events']=[dict(row) for row in store.db.execute('SELECT * FROM events ORDER BY id')]
   tool_results=[]
   for row in run['events']:
    event=json.loads(row['data'])
    if row['kind']=='controlled_tool_result' and event.get('tool')=='delivery_judge':
     result=event['result'];tool_results.append({'success':result['success'],'payload':json.loads(result['contentItems'][0]['text']) if result['success'] else result['contentItems']})
   run['judge_tool_results']=tool_results
   response=tool_results[0]['payload'] if len(tool_results)==1 and tool_results[0]['success'] else {}
   pinned=store.db.execute("SELECT value FROM settings WHERE key='judge_config_json'").fetchone()['value'];snapshot=store.root/('judge-'+hashlib.sha256(pinned.encode()).hexdigest()+'.json')
   run['checks']={'native_turn_completed':run['role']['phase']=='idle','exactly_one_successful_judge_call':len(tool_results)==1 and tool_results[0]['success'],'selected_provider':response.get('provider')==provider,'pinned_model':response.get('model')==model,'real_typed_yes':response.get('answer')=='yes' and isinstance(response.get('p'),(float,int)),'human_authority_false':response.get('human_authority') is False,'advisory_true':response.get('advisory') is True,'source_config_unchanged':hashlib.sha256(config.read_bytes()).hexdigest()==run['fixture_config_sha256'],'snapshot_matches_operator_selection':snapshot.is_file() and snapshot.read_text()==pinned,'not_fallback':response.get('provider')==provider and response.get('model')==model}
   run['compatibility']=coordinator.rpc.compatibility
  except Exception as error:
   run['error']={'type':type(error).__name__,'message':str(error)}
  finally:
   if coordinator:coordinator.rpc.close()
   store.db.close()
  report['runs'].append(run);(OUT/'native-bridge-results.json').write_text(json.dumps(report,indent=2)+'\n')
  print(json.dumps({'provider':provider,'checks':run.get('checks'), 'error':run.get('error')}),flush=True)
report['finished']=time.time();(OUT/'native-bridge-results.json').write_text(json.dumps(report,indent=2)+'\n')
