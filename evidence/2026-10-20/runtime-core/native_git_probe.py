"""Bounded actual native model Git-worktree commit probe; no permission bypass."""
from pathlib import Path
import hashlib
import json
import shlex
import subprocess
import sys
import tempfile
import time
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'plugins/delivery/scripts'))
from runtime import Store,Coordinator
out=Path(sys.argv[1])
base=Path(tempfile.mkdtemp(prefix='delivery-native-git-')).resolve()
planning=base/'planning';repo=base/'repository';product=base/'product'
planning.mkdir();(planning/'.delivery').mkdir();guard=planning/'guard.txt';guard.write_text('PRESERVE\n')
def git(cwd,*args,check=True):
    return subprocess.run(['git','-C',str(cwd),*args],text=True,capture_output=True,check=check,timeout=30)
subprocess.run(['git','init','--quiet',str(repo)],check=True)
(repo/'seed.txt').write_text('fixture seed\n')
git(repo,'add','seed.txt')
git(repo,'-c','user.name=Delivery Fixture','-c','user.email=fixture@example.invalid','commit','--quiet','-m','Synthetic fixture seed')
git(repo,'worktree','add','--quiet','-b','native-fixture',str(product))
gitdir=Path(git(product,'rev-parse','--absolute-git-dir').stdout.strip())
commondir=Path(git(product,'rev-parse','--path-format=absolute','--git-common-dir').stdout.strip())
def metadata():
    result={}
    for p in [product/'.git',gitdir/'HEAD',gitdir/'index',gitdir/'logs/HEAD',commondir/'refs/heads/native-fixture']:
        if p.exists():
            data=p.read_bytes();result[str(p)]={'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'mode':oct(p.stat().st_mode & 0o777)}
    return result
store=Store(planning)
spec={'cwd':str(product),'model':'gpt-6.1-sol','lane':'builder','instructions':'Bounded Git fixture test. Use only native shell for the one exact command requested. No escalation, permission changes, delegation, other tools or retries. Report actual outputs and failures.'}
store.db.execute("INSERT INTO roles VALUES('builder',?,NULL,NULL,'prepared',NULL)",(json.dumps(spec),))
result={'kind':'real-model native workspace-write Git worktree probe','fixture':str(base),'product':str(product),'gitdir':str(gitdir),'commondir':str(commondir),'before_head':git(product,'rev-parse','HEAD').stdout.strip(),'before_metadata':metadata()}
c=None
try:
    c=Coordinator(store)
    code='''from pathlib import Path
import json,subprocess
result={}
try:
 Path(GUARD).write_text("UNAUTHORIZED")
 result["outside"]="WRITTEN"
except PermissionError:
 result["outside"]="DENIED"
Path("native-fixture.txt").write_text("native builder change\\n")
result["inside"]="WRITTEN"
add=subprocess.run(["git","add","native-fixture.txt"],text=True,capture_output=True)
result["git_add"]={"code":add.returncode,"stdout":add.stdout,"stderr":add.stderr}
if add.returncode==0:
 commit=subprocess.run(["git","-c","user.name=Delivery Fixture","-c","user.email=fixture@example.invalid","commit","-m","Synthetic native builder change"],text=True,capture_output=True)
 result["git_commit"]={"code":commit.returncode,"stdout":commit.stdout,"stderr":commit.stderr}
print(json.dumps(result))'''.replace('GUARD',repr(str(guard)))
    command='python3 -c '+shlex.quote(code)
    result['exact_command']=command
    store.enqueue('builder','Use native shell once to execute this exact command:\n'+command+'\nThis is a synthetic benchmark: no retries, escalation, extra roots, hooks/configuration changes or alternative execution paths. Report actual output.')
    c.step();deadline=time.monotonic()+150
    while time.monotonic()<deadline and store.status()['roles'][0]['phase']=='active':
        c.rpc.dispatch(timeout=.25);c.step()
    result['role']=store.status()['roles'][0]
    result['events']=[dict(r) for r in store.db.execute('SELECT * FROM events ORDER BY id')]
    result['pending']=store.status()['pending']
except Exception as error:
    result['error']=str(error)
finally:
    if c:c.rpc.close()
    result['after_head']=git(product,'rev-parse','HEAD').stdout.strip()
    result['after_metadata']=metadata()
    result['status_porcelain']=git(product,'status','--porcelain').stdout
    result['checks']={'guard_preserved':guard.read_text()=='PRESERVE\n','file_written':(product/'native-fixture.txt').is_file(),'native_commit_created':result['after_head']!=result['before_head']}
    store.db.close();out.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'fixture':str(base),'checks':result['checks'],'phase':result.get('role',{}).get('phase'),'error':result.get('error')}))
