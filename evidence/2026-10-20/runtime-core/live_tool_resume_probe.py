"""Real model: bounded persisted role, restart, same-thread continuation."""
import json
from pathlib import Path
import sys
import tempfile
import time
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'plugins/delivery/scripts'))
from runtime import Store,Coordinator
output={'kind':'real-model persistent session; not desktop UI acceptance'}
with tempfile.TemporaryDirectory(prefix='delivery-core-live-') as tmp:
    project=Path(tmp).resolve();(project/'.delivery').mkdir()
    store=Store(project)
    spec={'cwd':str(project),'model':'gpt-6.1-sol','lane':'read-only','instructions':'Bounded persistence test. Use only delivery_send when explicitly requested. No other tools, delegation, browsing or filesystem changes. Reply exactly as requested.'}
    store.db.execute("INSERT INTO roles VALUES('coordinator',?,NULL,NULL,'prepared',NULL)",(json.dumps(spec),))
    store.db.execute("INSERT INTO roles VALUES('product-manager',?,NULL,NULL,'needs-reconciliation',NULL)",(json.dumps(spec),))
    c=None
    try:
        c=Coordinator(store)
        output['compatibility']=c.rpc.compatibility
        store.enqueue('coordinator','Call delivery_send to recipient product-manager with message TOOL_ONE, then reply exactly CORE_ONE')
        c.step()
        deadline=time.monotonic()+100
        while store.status()['roles'][0]['phase']=='active' and time.monotonic()<deadline:
            c.rpc.dispatch(timeout=.25);c.step()
        first=store.status()['roles'][0]
        output['first']={k:first[k] for k in ['thread','turn','phase']}
        c.rpc.close(); c=None
        c=Coordinator(store);c.reconcile()
        recovered=store.status()['roles'][0]
        output['recovered']={k:recovered[k] for k in ['thread','turn','phase']}
        if recovered['phase']!='idle': raise RuntimeError('Recovery did not verify idle thread')
        store.enqueue('coordinator','Call delivery_send to recipient product-manager with message TOOL_TWO, then reply exactly CORE_TWO')
        c.step()
        deadline=time.monotonic()+100
        while store.status()['roles'][0]['phase']=='active' and time.monotonic()<deadline:
            c.rpc.dispatch(timeout=.25);c.step()
        second=store.status()['roles'][0]
        output['second']={k:second[k] for k in ['thread','turn','phase']}
        output['same_thread']=first['thread']==second['thread']
        output['native_dynamic_tools']=[json.loads(row['data']) for row in store.db.execute("SELECT data FROM events WHERE kind='controlled_tool_result'")]
        output['successful_send_count']=sum(e['result']['success'] and e['tool']=='delivery_send' for e in output['native_dynamic_tools'])
        output['items']=[json.loads(row['data']) for row in store.db.execute("SELECT data FROM events WHERE kind='item/completed'")]
    except Exception as error:
        output['error']=str(error)
    finally:
        if c:c.rpc.close()
        store.db.close()
Path(sys.argv[1]).write_text(json.dumps(output,indent=2)+'\n')
print(json.dumps({k:v for k,v in output.items() if k!='items'}))
