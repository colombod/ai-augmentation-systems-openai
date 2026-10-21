"""Actual idle native public-CLI lifecycle; no role assignments/model calls."""
from pathlib import Path
import json, signal, sqlite3, subprocess, sys, tempfile, time
ROOT=Path(__file__).resolve().parents[4]
OUT=Path(__file__).resolve().parent
fixture=Path(tempfile.mkdtemp(prefix='delivery-idle-interrupt-')).resolve()
(fixture/'.delivery').mkdir()
script=ROOT/'plugins/delivery/scripts/runtime.py'
result={'kind':'actual public CLI idle native serve signal test, no model calls','fixture':str(fixture),'model_calls_requested':0,'started_at':time.time()}
process=None
try:
 with (OUT/'cli-interrupt.stdout.txt').open('w') as stdout,(OUT/'cli-interrupt.stderr.txt').open('w') as stderr:
  process=subprocess.Popen([sys.executable,str(script),'--project',str(fixture),'serve'],stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr,start_new_session=True)
 deadline=time.monotonic()+45
 while time.monotonic()<deadline:
  if process.poll() is not None:raise RuntimeError('serve exited before native startup completed')
  dbpath=fixture/'.delivery/runtime/coordinator.sqlite'
  if dbpath.exists():
   db=sqlite3.connect('file:'+str(dbpath)+'?mode=ro',uri=True)
   try:
    if db.execute("SELECT count(*) FROM events WHERE kind='gate_recovery_scan'").fetchone()[0]:break
   except sqlite3.OperationalError:pass
   finally:db.close()
  time.sleep(.2)
 else:raise RuntimeError('native idle startup deadline')
 result['native_startup_completed']=True
 process.send_signal(signal.SIGINT)
 result['serve_exit_code']=process.wait(timeout=20)
 stderr=(OUT/'cli-interrupt.stderr.txt').read_text()
 result['shutdown_record']=json.loads(stderr.strip().splitlines()[-1])
 status=subprocess.run([sys.executable,str(script),'--project',str(fixture),'status'],capture_output=True,text=True,timeout=10)
 result['status_exit_code']=status.returncode
 result['status']=json.loads(status.stdout)
 db=sqlite3.connect('file:'+str(dbpath)+'?mode=ro',uri=True)
 try:result['queue_count']=db.execute('SELECT count(*) FROM queue').fetchone()[0]
 finally:db.close()
 result['checks']={'native_started':True,'clean_sigint_exit':process.returncode==0,'explicit_interrupted_status':result['shutdown_record']=={'status':'interrupted'},'no_roles_or_work_claimed':not result['status']['roles'] and result['queue_count']==0,'status_readable_after_shutdown':status.returncode==0}
 result['all_pass']=all(result['checks'].values())
except Exception as error:result['error']=str(error)
finally:
 if process and process.poll() is None:
  process.terminate()
  try:process.wait(timeout=10)
  except subprocess.TimeoutExpired:process.kill();process.wait()
 result['finished_at']=time.time()
 (OUT/'cli-interrupt-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
sys.exit(0 if result.get('all_pass') else 1)
