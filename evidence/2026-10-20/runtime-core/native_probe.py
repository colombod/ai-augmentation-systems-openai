"""Actual native protocol probe: no model calls, no configuration copying."""
import json
from pathlib import Path
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'plugins/delivery/scripts'))
from codex_rpc import CodexRPC
from runtime import native_options,verify_native
result={}
with tempfile.TemporaryDirectory(prefix='delivery-native-core-') as tmp:
    cwd=str(Path(tmp).resolve())
    spec={'cwd':cwd,'model':'gpt-5.4','lane':'read-only'}
    rpc=CodexRPC(cwd,lambda m:None)
    try:
        started=rpc.call('thread/start',{**native_options(spec),'ephemeral':False})
        thread=verify_native(started,spec)
        result['started']={'thread':thread,'sandbox':started.get('sandbox'),'cwd_bound':started.get('cwd')==cwd,'reviewer':started.get('approvalsReviewer')}
        result['profile']=started.get('activePermissionProfile')
        resumed=rpc.call('thread/resume',{'threadId':thread,**native_options(spec),'excludeTurns':True})
        verify_native(resumed,spec,thread)
        result['resume_verified']=True
        result['compatibility']=rpc.compatibility
    except Exception as error:
        result['error']=str(error)
    finally:
        rpc.close()
Path(sys.argv[1]).write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
