"""Bounded synthetic persistent-session probe, not a real delivery assignment."""
from pathlib import Path
import json,sys,tempfile,time
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'plugins/delivery/scripts'))
from runtime import Store,Coordinator
OUT=Path(__file__).resolve().parent
base=Path(tempfile.mkdtemp(prefix='delivery-runtime-native-')).resolve();(base/'.delivery').mkdir();store=Store(base)
spec={'cwd':str(base),'model':'gpt-6.1-sol','lane':'read-only','instructions':'Bounded synthetic persistence check. Do not use tools or delegate. Return exactly the text requested.'}
store.db.execute("INSERT INTO roles VALUES('coordinator',?,NULL,NULL,'prepared',NULL)",(json.dumps(spec),))
result={'workspace':str(base),'checks':{}}
c=None
try:
 c=Coordinator(store);store.enqueue('coordinator','Return exactly DELIVERY_PERSISTENCE_FIRST');c.step();deadline=time.monotonic()+150
 while time.monotonic()<deadline and store.status()['roles'][0]['phase']=='active':c.rpc.dispatch(timeout=.5)
 first=store.status()['roles'][0];result['first']=first;result['checks']['first_completed']=first['phase']=='idle'
 c.rpc.close();c=None
 c=Coordinator(store);c.reconcile();resumed=store.status()['roles'][0];result['checks']['same_thread_resumed']=resumed['thread']==first['thread'] and resumed['phase']=='idle'
 store.enqueue('coordinator','Return exactly DELIVERY_PERSISTENCE_SECOND');c.step();deadline=time.monotonic()+150
 while time.monotonic()<deadline and store.status()['roles'][0]['phase']=='active':c.rpc.dispatch(timeout=.5)
 second=store.status()['roles'][0];result['second']=second;result['checks']['second_completed']=second['phase']=='idle';result['checks']['same_thread_after_second']=second['thread']==first['thread']
 result['events']=[dict(r) for r in store.db.execute('SELECT * FROM events ORDER BY id')]
except BaseException as e:
 result['error']=str(e);raise
finally:
 if c:c.rpc.close()
 (OUT/'native-session-probe.json').write_text(json.dumps(result,indent=2));store.db.close()
print(json.dumps(result['checks']),flush=True)
