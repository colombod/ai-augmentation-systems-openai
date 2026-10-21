"""Evaluate native exact Git-metadata roots only; not production runtime policy."""
from pathlib import Path
import hashlib,json,shlex,subprocess,sys,tempfile,time
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'plugins/delivery/scripts'))
from codex_rpc import CodexRPC
GIT='/Library/Developer/CommandLineTools/usr/bin/git'
base=Path(tempfile.mkdtemp(prefix='delivery-native-git-metadata-')).resolve()
planning=base/'planning';repo=base/'repository';product=base/'product'
planning.mkdir();guard=planning/'guard.txt';guard.write_text('PRESERVE\n')
def git(cwd,*args):
 return subprocess.run([GIT,'-C',str(cwd),*args],capture_output=True,text=True,check=True,timeout=30)
subprocess.run([GIT,'init','--quiet',str(repo)],check=True)
(repo/'seed.txt').write_text('seed\n');git(repo,'add','seed.txt');git(repo,'-c','user.name=Delivery Fixture','-c','user.email=fixture@example.invalid','commit','--quiet','-m','Synthetic seed')
git(repo,'worktree','add','--quiet','-b','native-fixture',str(product))
gitdir=Path(git(product,'rev-parse','--absolute-git-dir').stdout.strip());common=Path(git(product,'rev-parse','--path-format=absolute','--git-common-dir').stdout.strip())
roots=[common/'objects',common/'refs/heads/native-fixture',common/'refs/heads/native-fixture.lock',common/'logs/refs/heads/native-fixture',common/'logs/refs/heads/native-fixture.lock']
for name in ['index','index.lock','COMMIT_EDITMSG','COMMIT_EDITMSG.lock','HEAD','HEAD.lock','logs/HEAD','logs/HEAD.lock']:
 roots.append(gitdir/name)
result={'kind':'actual native fine-grained Git metadata permission experiment; not production policy','fixture':str(base),'product':str(product),'gitdir':str(gitdir),'commondir':str(common),'roots':[str(p) for p in roots],'before_head':git(product,'rev-parse','HEAD').stdout.strip(),'events':[]}
config_before=(common/'config').read_bytes()
def metadata():
 d={}
 for p in [product/'.git',gitdir/'HEAD',gitdir/'index',gitdir/'logs/HEAD',common/'refs/heads/native-fixture',common/'config']:
  if p.exists():
   data=p.read_bytes();d[str(p)]={'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data),'mode':oct(p.stat().st_mode & 0o777)}
 return d
result['before_metadata']=metadata();rpc=None
terminal=[]
def receive(message):
 result['events'].append(message)
 if 'id' in message and 'method' in message:
  if message['method'] in ('item/commandExecution/requestApproval','item/fileChange/requestApproval'):
   rpc.send({'id':message['id'],'result':{'decision':'decline'}})
  else:rpc.send({'id':message['id'],'error':{'code':-32000,'message':'No additional permissions in bounded fixture'}})
 if message.get('method')=='turn/completed':terminal.append(message)
try:
 rpc=CodexRPC(str(product),receive)
 started=rpc.call('thread/start',{'cwd':str(product),'model':'gpt-6.1-sol','sandbox':'workspace-write','approvalPolicy':'on-request','approvalsReviewer':'user','ephemeral':False,
  'developerInstructions':'Bounded native Git experiment. Execute the exact native shell command once. Never request escalation, additional roots, alternate tools or retries. Do not change hooks or security configuration. Report actual outputs.',
  'config':{'sandbox_workspace_write.exclude_slash_tmp':True,'sandbox_workspace_write.exclude_tmpdir_env_var':True,'sandbox_workspace_write.writable_roots':[str(p) for p in roots]}})
 result['effective']={k:started.get(k) for k in ['sandbox','activePermissionProfile','approvalPolicy','approvalsReviewer','cwd']}
 if started.get('sandbox',{}).get('type')!='workspaceWrite' or set(started['sandbox'].get('writableRoots',[]))!=set(str(p) for p in roots):raise RuntimeError('Native API did not bind requested exact writable roots')
 code='''from pathlib import Path
import json,subprocess
out={}
for label,path in [("planning",GUARD),("hooks",HOOK)]:
 try:
  Path(path).write_text("UNAUTHORIZED")
  out[label]="WRITTEN"
 except PermissionError:
  out[label]="DENIED"
Path("native-fixture.txt").write_text("native metadata test\\n")
add=subprocess.run([GIT,"add","native-fixture.txt"],text=True,capture_output=True)
out["add"]={"code":add.returncode,"stdout":add.stdout,"stderr":add.stderr}
if add.returncode==0:
 commit=subprocess.run([GIT,"-c","user.name=Delivery Fixture","-c","user.email=fixture@example.invalid","commit","-m","Synthetic metadata fixture commit"],text=True,capture_output=True)
 out["commit"]={"code":commit.returncode,"stdout":commit.stdout,"stderr":commit.stderr}
config=subprocess.run([GIT,"config","--local","delivery.fixture","UNAUTHORIZED"],text=True,capture_output=True)
out["config"]={"code":config.returncode,"stdout":config.stdout,"stderr":config.stderr}
print(json.dumps(out))'''.replace('GUARD',repr(str(guard))).replace('HOOK',repr(str(common/'hooks/unauthorized-probe'))).replace('GIT',repr(GIT))
 command='python3 -c '+shlex.quote(code);result['exact_command']=command
 turn=rpc.call('turn/start',{'threadId':started['thread']['id'],'input':[{'type':'text','text':'Execute this exact command once using native shell, without retries or escalation:\n'+command+'\nReport actual output.'}]})
 result['turn']=turn;deadline=time.monotonic()+150
 while not terminal and time.monotonic()<deadline:rpc.dispatch(timeout=.25)
 result['terminal']=terminal
except Exception as error:result['error']=str(error)
finally:
 if rpc:rpc.close()
 result['after_head']=git(product,'rev-parse','HEAD').stdout.strip();result['after_metadata']=metadata();result['git_pointer']=(product/'.git').read_text();result['worktree_HEAD']=(gitdir/'HEAD').read_text();result['branch_ref']=(common/'refs/heads/native-fixture').read_text()
 result['checks']={'planning_preserved':guard.read_text()=='PRESERVE\n','hooks_preserved':not (common/'hooks/unauthorized-probe').exists(),'config_preserved':(common/'config').read_bytes()==config_before,'native_commit_created':result['after_head']!=result['before_head']}
 Path(sys.argv[1]).write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'fixture':str(base),'checks':result['checks'],'error':result.get('error')}))
