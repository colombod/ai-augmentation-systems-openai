"""Pinned local Git fixtures; preparation never grants publication authority."""
import copy
import importlib.util
import json
import os
import signal
from pathlib import Path
import subprocess
import shutil
import sys
import tempfile
import time
import unittest

SCRIPTS = Path(__file__).resolve().parents[2]/'plugins/delivery/scripts'
SCRIPT = SCRIPTS/'publication_prepare.py'
ENV = {**os.environ, 'PYTHONDONTWRITEBYTECODE':'1'}


class PreparationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.repo = self.root/'repo'; self.repo.mkdir()
        self.git('init', '-q')
        (self.repo/'pkg').mkdir()
        (self.repo/'pkg/a.txt').write_bytes('SYNTHETIC café\r\n'.encode())
        (self.repo/'pkg/run.sh').write_text('echo synthetic\n')
        (self.repo/'pkg/run.sh').chmod(0o755)
        self.commit()
        self.request = {'commit':self.head, 'source':'pkg', 'prefix':'package',
                        'destination':'sample-product', 'body':'Synthetic bundle', 'metadata':{},
                        'extras':[{'name':'wrapper.json','content':'{}\n','mode':'0600'}]}

    def tearDown(self):
        self.temp.cleanup()

    def git(self, *args):
        result = subprocess.run(['git', '-c','user.name=Synthetic', '-c','user.email=synthetic@example.invalid',
                                 '-C',str(self.repo),*args],capture_output=True,env=ENV,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr)
        return result.stdout.decode().strip()

    def commit(self):
        self.git('add','-A'); self.git('commit','-qm','Synthetic fixture')
        self.head = self.git('rev-parse','HEAD')

    def run_prepare(self, value=None, raw=None, extra_env=None):
        return subprocess.run([sys.executable,str(SCRIPT),'--repo',str(self.repo)],
            input=json.dumps(self.request if value is None else value) if raw is None else raw,
            capture_output=True,text=True,env={**ENV,**(extra_env or {})},timeout=35)

    def refused(self, result):
        self.assertEqual(result.returncode,2,result.stdout)
        self.assertEqual(result.stdout,'')
        self.assertEqual(result.stderr,'{"status":"unavailable"}\n')

    def test_complete_pinned_tree_preserves_bytes_modes_and_excludes_worktree(self):
        first = self.run_prepare(); self.assertEqual(first.returncode,0,first.stderr)
        (self.repo/'pkg/a.txt').write_text('SYNTHETIC changed live file')
        (self.repo/'pkg/private.txt').write_text('SYNTHETIC_PRIVATE_NOTE')
        second = self.run_prepare(extra_env={'GIT_DIR':str(self.root/'wrong'), 'GIT_WORK_TREE':str(self.root)})
        self.assertEqual(second.returncode,0,second.stderr); self.assertEqual(first.stdout,second.stdout)
        value = json.loads(first.stdout)
        self.assertEqual(value['files'], [
            {'name':'package/a.txt','content':'SYNTHETIC café\r\n'},
            {'name':'package/run.sh','content':'echo synthetic\n'},
            {'name':'wrapper.json','content':'{}\n'}])
        self.assertEqual(json.loads(value['metadata']['modes']),
                         {'package/a.txt':'0644','package/run.sh':'0755','wrapper.json':'0600'})
        self.assertNotIn('SYNTHETIC_PRIVATE_NOTE',first.stdout)
        self.assertNotIn(str(self.repo),first.stdout)
        self.assertNotIn(self.head,first.stdout)
        # A newly selected commit explicitly captures changed tracked content.
        self.git('add','pkg/a.txt'); self.git('commit','-qm','Synthetic changed version')
        changed={**self.request,'commit':self.git('rev-parse','HEAD')}
        result=self.run_prepare(changed);self.assertEqual(result.returncode,0)
        self.assertNotEqual(result.stdout,first.stdout)
        self.assertNotIn('SYNTHETIC_PRIVATE_NOTE',result.stdout)

    def test_mutable_refs_missing_objects_wrong_roots_and_unsafe_names_refuse(self):
        for commit in ['HEAD',self.head[:12],self.head.upper(),'0'*40]:
            self.refused(self.run_prepare({**self.request,'commit':commit}))
        for field in ['source','prefix']:
            for path in ['.','..','/pkg','pkg/../pkg','pkg//x','pkg/','pkg\\x']:
                self.refused(self.run_prepare({**self.request,field:path}))
        for source in ['missing','pkg/a.txt',':(glob)*']:
            self.refused(self.run_prepare({**self.request,'source':source}))
        for name in ['package/a.txt','package','package/a.txt/child','../outside','/outside']:
            value=copy.deepcopy(self.request);value['extras'][0]['name']=name
            self.refused(self.run_prepare(value))

    def test_commit_and_blob_replacements_cannot_redirect_preparation(self):
        original = self.run_prepare()
        self.assertEqual(original.returncode, 0, original.stderr)
        old = self.head
        blob = self.git('rev-parse', old+':pkg/a.txt')
        (self.repo/'pkg/a.txt').write_text('SYNTHETIC replacement')
        self.commit()
        replacement_blob = self.git('rev-parse', self.head+':pkg/a.txt')
        self.git('replace', old, self.head)
        self.assertEqual(self.git('show', old+':pkg/a.txt'), 'SYNTHETIC replacement')
        result = self.run_prepare()
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, original.stdout, ''))
        self.git('replace', '-d', old)
        self.git('replace', blob, replacement_blob)
        self.assertEqual(self.git('show', old+':pkg/a.txt'), 'SYNTHETIC replacement')
        result = self.run_prepare()
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, original.stdout, ''))

    def test_sha256_repository_preserves_bytes_modes_and_long_unicode_paths(self):
        self.repo = self.root/'sha256'; self.repo.mkdir()
        self.git('init', '-q', '--object-format=sha256')
        (self.repo/'pkg').mkdir()
        (self.repo/'pkg/a.txt').write_bytes('SYNTHETIC café\r\n'.encode())
        (self.repo/'pkg/run.sh').write_text('echo synthetic\n')
        (self.repo/'pkg/run.sh').chmod(0o755)
        self.commit(); self.assertEqual(len(self.head), 64)
        request = {**self.request, 'commit': self.head}
        first = self.run_prepare(request); second = self.run_prepare(request)
        self.assertEqual((first.returncode, second.returncode), (0, 0))
        self.assertEqual(first.stdout, second.stdout)
        value = json.loads(first.stdout)
        self.assertEqual(value['files'][0]['content'].encode(), 'SYNTHETIC café\r\n'.encode())
        self.assertEqual(json.loads(value['metadata']['modes']),
                         {'package/a.txt':'0644', 'package/run.sh':'0755', 'wrapper.json':'0600'})
        self.test_unicode_listing_fits_supported_file_path_and_envelope_limits()
        self.assertEqual(len(self.head), 64)

    def test_running_git_stall_refuses_at_cli_deadline(self):
        real_git = str(Path(shutil.which('git')).resolve())
        fifo = self.root/'unwritten'; os.mkfifo(fifo)
        marker = self.root/'pid'
        shim_dir = self.root/'bin'; shim_dir.mkdir()
        shim = shim_dir/'git'
        shim.write_text('#!'+sys.executable+'\nimport os\n'
                        +'with open('+repr(str(marker))+', "w") as stream: stream.write(str(os.getpid()))\n'
                        +'os.execv('+repr(real_git)+', ["git", "hash-object", '+repr(str(fifo))+'])\n')
        shim.chmod(0o755)
        env = {**ENV, 'PATH':str(shim_dir)+os.pathsep+os.environ['PATH']}
        child = None; started = time.monotonic()
        process = subprocess.Popen([sys.executable, str(SCRIPT), '--repo', str(self.repo)],
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   text=True, env=env)
        try:
            process.stdin.write(json.dumps(self.request)); process.stdin.close(); process.stdin = None
            observed = False
            while time.monotonic()-started < 5:
                if marker.exists() and marker.read_text():
                    child = int(marker.read_text())
                    status = subprocess.run(['ps','-p',str(child),'-o','comm=','-o','args='],
                                            capture_output=True,text=True,timeout=2)
                    if status.returncode == 0 and 'git' in status.stdout.split()[0] and 'hash-object' in status.stdout and str(fifo) in status.stdout:
                        observed = True; break
                time.sleep(.02)
            self.assertTrue(observed, 'Real Git must be running on the unwritten FIFO')
            stdout, stderr = process.communicate(timeout=40)
            elapsed = time.monotonic()-started
            self.assertEqual((process.returncode, stdout, stderr), (2, '', '{"status":"unavailable"}\n'))
            self.assertGreaterEqual(elapsed, 29)
            self.assertLess(elapsed, 40)
            with self.assertRaises(ProcessLookupError): os.kill(child, 0)
        finally:
            if process.poll() is None: process.kill()
            process.communicate(timeout=5)
            if child is not None:
                status = subprocess.run(['ps','-p',str(child),'-o','args='],capture_output=True,text=True,timeout=2)
                if status.returncode == 0 and str(fifo) in status.stdout:
                    try: os.kill(child, signal.SIGKILL)
                    except ProcessLookupError: pass

    def test_unsupported_tree_entries_and_invalid_utf8_refuse(self):
        (self.repo/'pkg/link').symlink_to('../outside')
        self.commit();self.refused(self.run_prepare({**self.request,'commit':self.head}))
        (self.repo/'pkg/link').unlink();(self.repo/'pkg/binary').write_bytes(b'\xff')
        self.commit();self.refused(self.run_prepare({**self.request,'commit':self.head}))
        (self.repo/'pkg/binary').unlink();self.git('add','-A')
        self.git('update-index','--add','--cacheinfo','160000',self.head,'pkg/submodule')
        self.git('commit','-qm','Synthetic gitlink')
        self.refused(self.run_prepare({**self.request,'commit':self.git('rev-parse','HEAD')}))

    def test_limits_malformed_input_and_reserved_metadata_refuse(self):
        self.refused(self.run_prepare(raw=' ' * 1048577))
        self.refused(self.run_prepare(raw=json.dumps(self.request)[:-1]+',"body":"duplicate"}'))
        self.refused(self.run_prepare({**self.request,'metadata':{'modes':'{}'}}))
        self.refused(self.run_prepare({**self.request,'body':'x'*1015808}))
        for mode in ['0777','644',644,None]:
            value=copy.deepcopy(self.request);value['extras'][0]['mode']=mode
            self.refused(self.run_prepare(value))
        for n in range(126): (self.repo/f'pkg/file-{n}').write_text('x')
        self.commit()
        allowed=self.run_prepare({**self.request,'commit':self.head,'extras':[]})
        self.assertEqual(allowed.returncode,0,allowed.stderr)
        self.assertEqual(len(json.loads(allowed.stdout)['files']),128)
        (self.repo/'pkg/extra').write_text('x')
        self.commit();self.refused(self.run_prepare({**self.request,'commit':self.head,'extras':[]}))

    def test_oversized_blob_and_missing_promisor_object_do_not_fetch(self):
        (self.repo/'pkg/large').write_bytes(b'x'*1015809)
        self.commit();self.refused(self.run_prepare({**self.request,'commit':self.head}))
        bare=self.root/'remote.git'
        subprocess.run(['git','clone','--bare','--no-hardlinks',str(self.repo),str(bare)],
                       capture_output=True,check=True,timeout=10,env=ENV)
        oid=self.git('rev-parse',self.request['commit']+':pkg/a.txt')
        obj=self.repo/'.git/objects'/oid[:2]/oid[2:];obj.unlink()
        self.git('config','remote.origin.url',str(bare))
        self.git('config','remote.origin.promisor','true')
        self.git('config','extensions.partialClone','origin')
        self.refused(self.run_prepare())
        self.assertFalse(obj.exists())

    def test_unicode_listing_fits_supported_file_path_and_envelope_limits(self):
        shutil.rmtree(self.repo/'pkg')  # Disposable fixture source only.
        directory=self.repo/'pkg'
        for _ in range(4): directory=directory/('😀'*61)
        directory.mkdir(parents=True)
        for n in range(128): (directory/f'f{n:03}').write_text('x')
        self.commit()
        request={**self.request,'commit':self.head,'prefix':'x','extras':[]}
        result=self.run_prepare(request)
        self.assertEqual(result.returncode,0,result.stderr)
        value=json.loads(result.stdout)
        self.assertEqual(len(value['files']),128)
        self.assertTrue(all(len(f['name'])==254 and f['content']=='x' for f in value['files']))
        self.assertLessEqual(len(result.stdout.rstrip('\n').encode()),1015808)

    def test_git_output_and_deadline_are_bounded(self):
        sys.path.insert(0,str(SCRIPTS))
        try:
            spec=importlib.util.spec_from_file_location('prepare_bounds',SCRIPT)
            module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
            with self.assertRaises(module.Refused):
                module.git_read(self.repo,['ls-tree','-r',self.head],1,time.monotonic()+5)
            with self.assertRaises(module.Refused):
                module.git_read(self.repo,['ls-tree','-r',self.head],1024,time.monotonic()-1)
        finally:
            sys.path.remove(str(SCRIPTS))


if __name__ == '__main__':
    unittest.main()
