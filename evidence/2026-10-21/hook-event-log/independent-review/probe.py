"""Independent actual packaged-command checks; synthetic payloads only."""
import concurrent.futures
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile
import time

PACKAGE = Path(__file__).resolve().parents[4] / 'plugins/hook-event-log'
BASE = Path(tempfile.mkdtemp(prefix='event-independent-')).resolve()
SENTINEL = 'PRIVATE_CONTENT_MUST_NEVER_APPEAR_6f10ea'
EVENTS = ['SessionStart','SessionEnd','UserPromptSubmit','PreToolUse','PostToolUse',
          'PermissionRequest','SubagentStart','SubagentStop','PreCompact','PostCompact','Stop','Interrupt']
checks = []

def check(name, condition, details=None):
    checks.append(dict(name=name, passed=bool(condition), details=details))

def invoke(payload, root, package=PACKAGE, timeout=5):
    env = dict(os.environ)
    env.pop('PLUGIN_DATA', None)
    if root is not None:
        env['PLUGIN_DATA'] = str(root)
    start = time.monotonic()
    result = subprocess.run(['node',str(package/'dist/hook.js')], input=payload,
                            capture_output=True, env=env, timeout=timeout)
    result.elapsed = time.monotonic()-start
    return result

def data(event='PreToolUse', session='synthetic-session', **fields):
    return json.dumps(dict(hook_event_name=event,session_id=session,**fields)).encode()

def records(root):
    return [json.loads(line) for p in root.rglob('*.jsonl') for line in p.read_text().splitlines()]

def quiet_success(result):
    return result.returncode == 0 and result.stdout == b'' and result.stderr == b''

def private_failure(result):
    return result.returncode == 1 and result.stdout == b'' and result.stderr == b'hook-event-log: event could not be recorded\n'

root = BASE/'events'
results = [invoke(data(event, prompt=SENTINEL, tool_response=SENTINEL), root) for event in EVENTS]
check('all twelve actual adapter invocations quiet',all(map(quiet_success,results)))
check('one-key event-only records',records(root)==[{'event_type':event} for event in EVENTS])
files = list(root.rglob('*.jsonl'))
check('hashed session routing',len(files)==1 and files[0].name==hashlib.sha256(b'synthetic-session').hexdigest()+'.jsonl')
check('owner-only file and event directory',stat.S_IMODE(files[0].stat().st_mode)==0o600 and stat.S_IMODE(files[0].parent.stat().st_mode)==0o700)
check('payload sentinel excluded from persisted data',all(SENTINEL.encode() not in p.read_bytes() for p in root.rglob('*') if p.is_file()))
check('normal adapter max latency under one second',max(r.elapsed for r in results)<1,max(r.elapsed for r in results))

concurrent_root=BASE/'concurrent'
with concurrent.futures.ThreadPoolExecutor(max_workers=32) as pool:
    parallel=list(pool.map(lambda _:invoke(data(),concurrent_root),range(32)))
check('32 concurrent adapter processes succeed',all(map(quiet_success,parallel)))
check('32 concurrent records complete exactly once',records(concurrent_root)==[{'event_type':'PreToolUse'}]*32)

separate_root=BASE/'separate'
check('distinct sessions succeed',all(quiet_success(invoke(data(session=s),separate_root)) for s in ['first','second']))
check('distinct sessions have separate files',len(list(separate_root.rglob('*.jsonl')))==2)

for name,payload in [('malformed',b'{'+SENTINEL.encode()),('array',b'[]'),('missing-session',b'{"hook_event_name":"Stop"}'),('unknown-event',data(SENTINEL)),('blank-session',data(session=' ')),('oversize',b'x'*1048577)]:
    invalid_root=BASE/name
    result=invoke(payload,invalid_root)
    check(name+' rejected privately without disk writes',private_failure(result) and not invalid_root.exists())

exact=data(padding='')
exact=data(padding='x'*(1048576-len(exact)))
check('exact one MiB accepted',len(exact)==1048576 and quiet_success(invoke(exact,BASE/'exact-limit')))
check('missing data root fixed failure',private_failure(invoke(data(),None)))
check('relative data root fixed failure',private_failure(invoke(data(),'relative-do-not-create')))

target=BASE/'target';target.mkdir()
link=BASE/'root-link';link.symlink_to(target,target_is_directory=True)
check('root symlink refused',private_failure(invoke(data(),link)) and list(target.iterdir())==[])
ancestor=BASE/'ancestor';ancestor.symlink_to(target,target_is_directory=True)
check('ancestor symlink refused',private_failure(invoke(data(),ancestor/'sub')) and list(target.iterdir())==[])

for kind in ['symlink','hardlink','fifo','public-file','public-directory']:
    hostile=BASE/kind;directory=hostile/'event-types';directory.mkdir(parents=True,mode=0o700)
    filename=directory/(hashlib.sha256(b'synthetic-session').hexdigest()+'.jsonl')
    guard=BASE/(kind+'-guard');guard.write_text(SENTINEL);guard.chmod(0o600)
    if kind=='symlink': filename.symlink_to(guard)
    if kind=='hardlink':os.link(guard,filename)
    if kind=='fifo':os.mkfifo(filename,0o600)
    if kind=='public-file':filename.write_text('');filename.chmod(0o644)
    if kind=='public-directory':directory.chmod(0o755)
    result=invoke(data(),hostile)
    check(kind+' refused without guard mutation',private_failure(result) and guard.read_text()==SENTINEL)

env=dict(os.environ,PLUGIN_DATA=str(BASE/'idle'))
start=time.monotonic()
idle=subprocess.Popen(['node',str(PACKAGE/'dist/hook.js')],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env)
idle.wait(timeout=4)
elapsed=time.monotonic()-start
check('idle stdin deadline quiet payload-free failure',idle.returncode==1 and idle.stdout.read()==b'' and idle.stderr.read()==b'hook-event-log: event could not be recorded\n' and elapsed<3,elapsed)
idle.stdin.close()

lock_root=BASE/'lock-contention'
invoke(data(),lock_root)
lock_file=next(lock_root.rglob('*.jsonl'))
with lock_file.open('rb') as held:
    fcntl.flock(held,fcntl.LOCK_EX)
    result=invoke(data(),lock_root)
    check('held lock times out without duplicate append',private_failure(result) and result.elapsed<1 and len(records(lock_root))==1,result.elapsed)

# Exercise transport failure contracts in an isolated package copy; never mutate source.
fake=BASE/'transport-fixture';(fake/'dist').mkdir(parents=True)
shutil.copyfile(PACKAGE/'dist/hook.js',fake/'dist/hook.js')
(fake/'package.json').write_text('{"type":"module"}')
check('missing native executable fixed failure',private_failure(invoke(data(),BASE/'missing-native',fake)))
native_path=next((PACKAGE/'bin').glob('*/event-log-core')).relative_to(PACKAGE)
fake_native=fake/native_path;fake_native.parent.mkdir(parents=True)
fake_native.write_text('#!/bin/sh\necho '+SENTINEL+'\necho '+SENTINEL+' >&2\nexit 1\n');fake_native.chmod(0o755)
check('native stdout stderr payloads suppressed',private_failure(invoke(data(),BASE/'native-error',fake)))
fake_native.write_text('#!/bin/sh\nexec sleep 10\n')
result=invoke(data(),BASE/'native-hang',fake)
check('native child deadline bounded and fixed',private_failure(result) and result.elapsed<3,result.elapsed)

report=dict(package=str(PACKAGE),temporary_root=str(BASE),checks=checks,passed=sum(c['passed'] for c in checks),total=len(checks))
print(json.dumps(report,indent=2))
raise SystemExit(0 if all(c['passed'] for c in checks) else 1)
