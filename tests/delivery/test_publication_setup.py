"""Actual trusted setup CLI with fabricated local state; never launches Codex."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[2] / 'plugins/delivery/scripts'


class SetupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.package = self.base / 'package'
        self.package.mkdir()
        for name in ('publication_setup.py','publication_service.py','publication.py'):
            (self.package/name).write_bytes((SOURCE/name).read_bytes())
        self.trusted = self.base / 'trusted'; self.trusted.mkdir(mode=0o700)
        self.worker = self.base / 'worker'; self.worker.mkdir()
        self.db = self.trusted/'ledger.sqlite'
        self.home = self.trusted/'dedicated-codex'
        self.service = self.package/'publication_service.py'
        self.helper = self.package/'publication_setup.py'
        self.run_service('--initialize')
        request={'action':'register','destination':'synthetic-product','owner':'synthetic-owner',
                 'audience':'synthetic-users','visibility':'private','revision':'r1',
                 'authority_revision':'a1','policy_revision':'p1'}
        self.binding=json.loads(self.run_service('--control',request=request).stdout)['binding']
        self.binding_path=self.trusted/'binding.json'; self.binding_path.write_text(json.dumps(self.binding))
        self.plan_path=self.trusted/'plan.json'
        self.original=self.db.read_bytes()

    def run_service(self,*args,request=None):
        result=subprocess.run([sys.executable,'-B',str(self.service),'--db',str(self.db),*args],
            input='' if request is None else json.dumps(request),text=True,capture_output=True,timeout=5)
        self.assertEqual(result.returncode,0,result.stderr)
        return result

    def cli(self,*args,ok=True):
        result=subprocess.run([sys.executable,'-B',str(self.helper),*map(str,args)],
                              capture_output=True,text=True,timeout=5)
        self.assertEqual(result.returncode,0 if ok else 2,(result.stdout,result.stderr))
        data=json.loads(result.stdout);self.assertIs(data['host_protected_ready'],False)
        return data

    def make_plan(self,ok=True):
        value=self.cli('plan','--home',self.home,'--ledger',self.db,'--worker',self.worker,
                       '--binding',self.binding_path,ok=ok)
        if ok:self.plan_path.write_text(json.dumps(value));self.digest=value['sha256']
        return value

    def action(self,name,ok=True,digest=None):
        return self.cli(name,'--plan',self.plan_path,'--expected-sha256',digest or self.digest,ok=ok)

    def test_plan_enable_reconnect_disable_preserves_user_config_and_ledger(self):
        user=self.base/'original-config.toml';user.write_text('model = "SYNTHETIC"\n')
        self.make_plan();self.assertFalse(self.home.exists())
        self.assertEqual(self.db.read_bytes(),self.original)
        self.assertEqual(self.action('enable')['status'],'configured')
        config=(self.home/'config.toml').read_bytes();receipt=(self.home/'delivery-setup.json').read_bytes()
        for _ in range(2):
            self.assertEqual(self.action('enable')['status'],'configured')
            self.assertEqual(self.action('status')['status'],'configured')
            self.assertEqual((self.home/'config.toml').read_bytes(),config)
        runtime=self.home/'runtime-file';runtime.write_bytes(b'SYNTHETIC')
        self.assertEqual(self.action('disable')['status'],'disabled')
        self.assertEqual(self.action('disable')['status'],'disabled')
        self.assertEqual(self.action('status')['status'],'disabled')
        self.assertEqual(self.action('enable')['status'],'configured')
        self.assertEqual((self.home/'config.toml').read_bytes(),config)
        self.assertEqual((self.home/'delivery-setup.json').read_bytes(),receipt)
        self.assertEqual(runtime.read_bytes(),b'SYNTHETIC')
        self.assertEqual(self.db.read_bytes(),self.original)
        self.assertEqual(user.read_text(),'model = "SYNTHETIC"\n')

    def test_interrupted_after_receipt_recovers_without_reset(self):
        self.make_plan();self.action('enable');(self.home/'config.toml').unlink()
        self.action('status',ok=False)
        self.assertEqual(self.action('enable')['status'],'configured')
        self.assertEqual(self.db.read_bytes(),self.original)

    def test_existing_unknown_home_is_untouched(self):
        self.make_plan();self.home.mkdir(mode=0o700);config=self.home/'config.toml';config.write_bytes(b'SYNTHETIC existing')
        self.action('enable',ok=False)
        self.assertEqual(set(p.name for p in self.home.iterdir()),{'config.toml'})
        self.assertEqual(config.read_bytes(),b'SYNTHETIC existing')

    def test_wrong_binding_or_missing_corrupt_ledger_never_initializes(self):
        self.binding['owner']='other';self.binding_path.write_text(json.dumps(self.binding));self.make_plan(ok=False)
        self.assertEqual(self.db.read_bytes(),self.original)
        self.db.unlink();self.make_plan(ok=False);self.assertFalse(self.db.exists())
        self.db.write_bytes(b'SYNTHETIC corrupt');self.make_plan(ok=False)
        self.assertEqual(self.db.read_bytes(),b'SYNTHETIC corrupt')

    def test_config_and_receipt_drift_are_preserved(self):
        self.make_plan();self.action('enable')
        config=self.home/'config.toml';old=config.read_bytes();config.write_bytes(old+b'# changed\n')
        for action in ('enable','disable','status'):self.action(action,ok=False)
        self.assertEqual(config.read_bytes(),old+b'# changed\n');config.write_bytes(old)
        receipt=self.home/'delivery-setup.json';receipt.write_bytes(b'{}')
        for action in ('enable','disable','status'):self.action(action,ok=False)
        self.assertEqual(receipt.read_bytes(),b'{}');self.assertEqual(config.read_bytes(),old)

    def test_source_binding_and_identity_drift_block_enable_but_allow_disable(self):
        self.make_plan();self.action('enable')
        service=self.package/'publication_service.py';service.write_bytes(service.read_bytes()+b'\n# SYNTHETIC change\n')
        self.action('enable',ok=False);self.action('status',ok=False)
        self.assertEqual(self.action('disable')['status'],'disabled')
        self.assertEqual(self.db.read_bytes(),self.original)

    def test_disable_survives_missing_or_invalid_service_without_reset(self):
        self.make_plan();self.action('enable')
        receipt=(self.home/'delivery-setup.json').read_bytes()
        self.service.unlink()
        for action in ('enable','status'):self.action(action,ok=False)
        self.assertEqual(self.action('disable')['status'],'disabled')
        self.assertEqual(self.action('disable')['status'],'disabled')
        self.service.write_bytes((SOURCE/'publication_service.py').read_bytes())
        self.action('enable')
        self.service.write_text('SYNTHETIC invalid Python !')
        for action in ('enable','status'):self.action(action,ok=False)
        self.assertEqual(self.action('disable')['status'],'disabled')
        self.assertEqual((self.home/'delivery-setup.json').read_bytes(),receipt)
        self.assertEqual(self.db.read_bytes(),self.original)

    def test_disable_strictly_validates_plan_without_service_import(self):
        self.make_plan();self.action('enable');self.service.unlink()
        original=self.plan_path.read_text();value=json.loads(original)
        config=(self.home/'config.toml').read_bytes()
        receipt=(self.home/'delivery-setup.json').read_bytes()
        malformed=['{', original[:-1]+', "sha256": "duplicate"}',
                   original.replace('"host_protected_ready": false', '"host_protected_ready": NaN'),
                   original.replace('"host_protected_ready": false', '"host_protected_ready": Infinity'),
                   original.replace('"host_protected_ready": false', '"host_protected_ready": -Infinity'),
                   original.replace('"ledger_identity":', '"worker": "duplicate", "ledger_identity":'),
                   json.dumps({**value,'extra':'SYNTHETIC'}),
                   json.dumps({**value,'sha256':'0'*64})]
        for raw in malformed:
            with self.subTest(raw=raw):
                self.plan_path.write_text(raw);self.action('disable',ok=False)
                self.assertEqual((self.home/'config.toml').read_bytes(),config)
                self.assertEqual((self.home/'delivery-setup.json').read_bytes(),receipt)
        self.plan_path.write_text(original)
        self.action('disable',ok=False,digest='0'*64)
        (self.home/'config.toml').write_bytes(config+b'# SYNTHETIC drift')
        self.action('disable',ok=False)
        self.assertEqual((self.home/'config.toml').read_bytes(),config+b'# SYNTHETIC drift')
        (self.home/'config.toml').write_bytes(config)
        (self.home/'delivery-setup.json').write_bytes(receipt+b' ')
        self.action('disable',ok=False)
        self.assertEqual((self.home/'delivery-setup.json').read_bytes(),receipt+b' ')
        self.assertEqual(self.db.read_bytes(),self.original)

    def test_separate_ledger_ancestor_replacement_refuses_stale_plan(self):
        ledger_root=self.base/'ledger-root';ledger_root.mkdir(mode=0o700)
        parent=ledger_root/'data';parent.mkdir(mode=0o700)
        self.db.rename(parent/'ledger.sqlite');self.db=parent/'ledger.sqlite'
        self.make_plan();self.action('enable')
        before=(self.db.stat().st_dev,self.db.stat().st_ino,self.db.read_bytes())
        config=(self.home/'config.toml').read_bytes()
        receipt=(self.home/'delivery-setup.json').read_bytes()
        for directory in (parent,ledger_root):
            with self.subTest(directory=directory):
                saved=directory.with_name(directory.name+'-saved');directory.rename(saved)
                directory.mkdir(mode=0o700)
                for item in saved.iterdir():item.rename(directory/item.name)
                for action in ('enable','status'):self.action(action,ok=False)
                self.assertEqual((self.db.stat().st_dev,self.db.stat().st_ino,self.db.read_bytes()),before)
                self.assertEqual((self.home/'config.toml').read_bytes(),config)
                self.assertEqual((self.home/'delivery-setup.json').read_bytes(),receipt)
                self.assertEqual(self.action('disable')['status'],'disabled')
                # Restore the original directory identity for the next case.
                for item in directory.iterdir():item.rename(saved/item.name)
                directory.rmdir();saved.rename(directory)
                self.action('enable')

    def test_replaced_ledger_and_stale_digest_refuse(self):
        self.make_plan();self.action('enable',ok=False,digest='0'*64)
        replacement=self.trusted/'replacement';replacement.write_bytes(self.original);replacement.replace(self.db)
        self.action('enable',ok=False);self.assertFalse(self.home.exists())

    def test_symlink_and_worker_overlap_refuse(self):
        self.home.symlink_to(self.worker,target_is_directory=True);self.make_plan(ok=False);self.home.unlink()
        self.worker=self.trusted;self.make_plan(ok=False)
        self.assertFalse(self.home.exists())

    def test_publicly_readable_ledger_refuses_without_changing_permissions(self):
        self.db.chmod(0o644)
        self.make_plan(ok=False)
        self.assertEqual(self.db.stat().st_mode & 0o777,0o644)
        self.assertFalse(self.home.exists())

    def test_binding_generation_drift_requires_new_plan(self):
        self.make_plan()
        request={k:v for k,v in self.binding.items() if k!='generation'}
        request.update(action='register',revision='r2')
        self.run_service('--control',request=request)
        changed=self.db.read_bytes()
        self.action('enable',ok=False)
        self.assertFalse(self.home.exists());self.assertEqual(self.db.read_bytes(),changed)

    def test_special_home_paths_roundtrip_without_manual_editing(self):
        import tomllib
        self.home=self.trusted/'spaces " quote \\ rocket 🚀'
        self.make_plan();self.action('enable')
        d=tomllib.loads((self.home/'config.toml').read_text())
        self.assertEqual(d['permissions']['delivery-local']['filesystem'][str(self.home)],'deny')
        self.assertEqual(self.action('disable')['status'],'disabled')

    def test_concurrent_enable_is_recoverable_without_overwriting(self):
        from concurrent.futures import ThreadPoolExecutor
        self.make_plan()
        argv=[sys.executable,'-B',str(self.helper),'enable','--plan',str(self.plan_path),
              '--expected-sha256',self.digest]
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(lambda _:subprocess.run(argv,capture_output=True,text=True,timeout=5),range(2)))
        self.assertIn(0,[r.returncode for r in results])
        self.assertTrue(all(r.returncode in (0,2) for r in results))
        self.assertEqual(self.action('enable')['status'],'configured')
        self.assertEqual(self.db.read_bytes(),self.original)

    def test_worker_replacement_and_worker_parent_replacement_refuse(self):
        self.make_plan()
        self.worker.rename(self.base/'old-worker');self.worker.mkdir()
        self.action('enable',ok=False);self.assertFalse(self.home.exists())
        self.worker=self.base/'container'/'worker';self.worker.parent.mkdir();self.worker.mkdir()
        self.make_plan()
        self.worker.parent.rename(self.base/'old-container')
        self.worker.parent.mkdir();(self.base/'old-container'/'worker').rename(self.worker)
        self.action('enable',ok=False);self.assertFalse(self.home.exists())

    def test_existing_home_and_parent_replacement_refuse(self):
        self.home.mkdir(mode=0o700);self.make_plan()
        self.home.rename(self.trusted/'old-home');self.home.mkdir(mode=0o700)
        self.action('enable',ok=False)
        self.assertEqual(list(self.home.iterdir()),[])
        self.make_plan()
        self.trusted.rename(self.base/'old-trusted');self.trusted.mkdir(mode=0o700)
        for item in (self.base/'old-trusted').iterdir():item.rename(self.trusted/item.name)
        self.action('enable',ok=False)
        self.assertEqual(list(self.home.iterdir()),[])

    def test_created_home_replacement_with_copied_receipt_refuses(self):
        import shutil
        self.make_plan();self.action('enable')
        self.home.rename(self.trusted/'old-home')
        shutil.copytree(self.trusted/'old-home',self.home)
        before={p.name:p.read_bytes() for p in self.home.iterdir()}
        for action in ('enable','status','disable'):self.action(action,ok=False)
        self.assertEqual({p.name:p.read_bytes() for p in self.home.iterdir()},before)

    def test_creation_interrupted_before_receipt_requires_new_plan(self):
        self.make_plan();self.home.mkdir(mode=0o700)
        self.action('enable',ok=False)
        self.assertEqual(list(self.home.iterdir()),[])
        self.make_plan();self.action('enable')
        self.assertEqual(self.db.read_bytes(),self.original)

    def test_config_has_only_candidate_service_and_no_initialization(self):
        import tomllib
        self.make_plan();self.action('enable');d=tomllib.loads((self.home/'config.toml').read_text())
        self.assertEqual(set(d['mcp_servers']),{'delivery_publication'})
        server=d['mcp_servers']['delivery_publication']
        self.assertEqual(server['args'],['-B',str(self.service),'--db',str(self.db)])
        self.assertEqual(set(server['enabled_tools']),{'delivery_publication_'+x for x in ('submit','publish','receipt')})
        self.assertEqual(d['approval_policy'],'never');self.assertEqual(d['web_search'],'disabled')
        self.assertFalse(d['permissions']['delivery-local']['network']['enabled'])
        self.assertTrue(all(value is False for value in d['features'].values()))


if __name__ == '__main__':
    unittest.main()
