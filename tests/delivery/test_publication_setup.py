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

    def malformed_plans(self, original):
        import copy
        cases = []
        def change(path, value):
            item = copy.deepcopy(original); target = item
            for key in path[:-1]:target = target[key]
            target[path[-1]] = value
            cases.append(item)
        for value in (True, 1.0, '1', None, 2):change(['schema_version'], value)
        for value in (0, 0.0, None, 'false'):change(['host_protected_ready'], value)
        change(['spec','binding','visibility'], 'internal')
        change(['spec','binding','destination'], 'INVALID')
        change(['spec','binding','owner'], ' '*3)
        change(['spec','binding','revision'], 'x'*257)
        for value in (True, 1.0, 0, -1, '1', None):change(['spec','binding','generation'], value)
        for field in original['spec']['binding']:
            if field != 'generation':
                change(['spec','binding',field], True)
                change(['spec','binding',field], '')
        for field in ('ledger_identity','worker_identity','python_identity','home_identity'):
            identity = original['spec'][field]
            for value in ([float(identity[0]),identity[1]], [True,identity[1]], [-1,0], [0], '01'):
                change(['spec',field], value)
        for field in ('home_ancestors','ledger_ancestors','worker_ancestors','file_identities'):
            key = next(iter(original['spec'][field])); identity=original['spec'][field][key]
            change(['spec',field,key],[identity[0],float(identity[1])])
            change(['spec',field], {})
        for field in ('python_sha256',):
            for value in ('A'*64, '0'*63, True):change(['spec',field], value)
        key=next(iter(original['spec']['files']))
        for value in ('z'*64, None, 1):change(['spec','files',key],value)
        for field in ('home','ledger','worker','python'):
            change(['spec',field], True)
            change(['spec',field], '/tmp/../invalid')
        for path in ([], ['spec'], ['spec','binding']):
            for extra in (True, False):
                item=copy.deepcopy(original);target=item
                for key in path:target=target[key]
                if extra:target['unexpected']=1
                else:del target[next(iter(target))]
                cases.append(item)
        for item in cases:
            item['sha256']=hashlib.sha256(json.dumps(item['spec'],sort_keys=True,
                separators=(',',':'),ensure_ascii=True).encode()).hexdigest()
        for field in ('sha256',):
            for value in (True, None, 'A'*64, '0'*63):
                item=copy.deepcopy(original);item[field]=value;cases.append(item)
        return cases

    def test_strict_plan_schema_rejects_before_service_and_state_effects(self):
        marker=self.trusted/'service-effect'
        self.service.write_text(self.service.read_text()+
            '\nfrom pathlib import Path as FixturePath\nFixturePath('+repr(str(marker))+').write_text("SYNTHETIC")\n')
        self.home.mkdir(mode=0o700)
        original=self.make_plan();marker.unlink()
        for value in self.malformed_plans(original):
            with self.subTest(value=value):
                self.plan_path.write_text(json.dumps(value))
                self.action('enable',ok=False,digest=str(value['sha256']))
                self.assertEqual(list(self.home.iterdir()),[])
                self.assertFalse(marker.exists());self.assertEqual(self.db.read_bytes(),self.original)
        self.plan_path.write_text(json.dumps(original));self.action('enable');marker.unlink()
        config=(self.home/'config.toml').read_bytes()
        receipt_path=self.home/'delivery-setup.json'
        receipt=json.loads(receipt_path.read_text())
        for value in self.malformed_plans(original):
            # Match the malformed receipt so rejection cannot rely on byte mismatch.
            receipt['plan']=value
            raw=(json.dumps(receipt,sort_keys=True,separators=(',',':'),ensure_ascii=True)+'\n').encode()
            receipt_path.write_bytes(raw);self.plan_path.write_text(json.dumps(value))
            for action in ('enable','status','disable'):
                self.action(action,ok=False,digest=str(value['sha256']))
                self.assertEqual((self.home/'config.toml').read_bytes(),config)
                self.assertEqual(receipt_path.read_bytes(),raw)
                self.assertFalse(marker.exists());self.assertEqual(self.db.read_bytes(),self.original)

    def test_preflight_strict_binding_rejects_before_service_loading(self):
        marker=self.trusted/'service-effect'
        self.service.write_text(self.service.read_text()+
            '\nfrom pathlib import Path as FixturePath\nFixturePath('+repr(str(marker))+').write_text("SYNTHETIC")\n')
        original=dict(self.binding)
        changes=[{**original,'generation':v} for v in (True,1.0,0,-1,'1',None)]
        changes += [{**original,k:True} for k in original if k!='generation']
        changes += [{**original,'extra':1},{k:v for k,v in original.items() if k!='owner'}]
        for value in changes:
            self.binding_path.write_text(json.dumps(value));self.make_plan(ok=False)
            self.assertFalse(marker.exists());self.assertFalse(self.home.exists())
            self.assertEqual(self.db.read_bytes(),self.original)

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
        saved_service=self.package/'saved-service.py';self.service.rename(saved_service)
        for action in ('enable','status'):self.action(action,ok=False)
        self.assertEqual(self.action('disable')['status'],'disabled')
        self.assertEqual(self.action('disable')['status'],'disabled')
        saved_service.rename(self.service)
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

    def test_changed_service_cannot_execute_before_drift_refusal(self):
        self.make_plan();self.action('enable')
        marker=self.trusted/'import-side-effect'
        config=(self.home/'config.toml').read_bytes();receipt=(self.home/'delivery-setup.json').read_bytes()
        self.service.write_text(self.service.read_text()+
            '\nfrom pathlib import Path as FixturePath\nFixturePath('+repr(str(marker))+').write_text("SYNTHETIC")\n'+
            'import sqlite3 as fixture_sqlite\nfixture_db=fixture_sqlite.connect('+repr(str(self.db))+')\n'+
            'fixture_db.execute("DELETE FROM routes")\nfixture_db.commit()\nfixture_db.close()\n')
        for action in ('enable','status'):
            self.action(action,ok=False)
            self.assertFalse(marker.exists())
            self.assertEqual(self.db.read_bytes(),self.original)
            self.assertEqual((self.home/'config.toml').read_bytes(),config)
            self.assertEqual((self.home/'delivery-setup.json').read_bytes(),receipt)
        self.action('disable');self.assertFalse(marker.exists())
        self.assertEqual(self.db.read_bytes(),self.original)

    def test_preflight_checks_program_fields_before_any_service_execution(self):
        marker=self.trusted/'import-side-effect'
        self.service.write_text(self.service.read_text()+
            '\nfrom pathlib import Path as FixturePath\nFixturePath('+repr(str(marker))+').write_text("SYNTHETIC")\n')
        value=self.make_plan();self.assertTrue(marker.exists());marker.unlink()
        # Digest-bound plans are edited only as fabricated invalid fixtures.
        # With no home, refusal must happen before creation and before service execution.
        for field in ('python_identity','python_sha256','file_identities','files'):
            changed=json.loads(json.dumps(value))
            if field=='python_identity':changed['spec'][field][1]+=1
            elif field=='python_sha256':changed['spec'][field]='0'*64
            elif field=='file_identities':changed['spec'][field][str(self.service)][1]+=1
            else:changed['spec'][field][str(self.service)]='0'*64
            changed['sha256']=hashlib.sha256(json.dumps(changed['spec'],sort_keys=True,
                separators=(',',':'),ensure_ascii=True).encode()).hexdigest()
            self.plan_path.write_text(json.dumps(changed))
            self.action('enable',ok=False,digest=changed['sha256'])
            self.assertFalse(marker.exists());self.assertFalse(self.home.exists())
            self.assertEqual(self.db.read_bytes(),self.original)

    def test_identical_source_replacement_refuses_before_home_creation(self):
        self.make_plan()
        original=self.package/'publication.py'
        replacement=self.package/'replacement.py';replacement.write_bytes(original.read_bytes())
        replacement.replace(original)
        self.action('enable',ok=False)
        self.assertFalse(self.home.exists());self.assertEqual(self.db.read_bytes(),self.original)

    def test_unchecked_bytecode_cache_cannot_replace_verified_source(self):
        import py_compile
        self.make_plan();self.action('enable')
        original=self.service.read_bytes();marker=self.trusted/'cache-side-effect'
        self.service.write_text('from pathlib import Path\nPath('+repr(str(marker))+').write_text("SYNTHETIC")\n')
        py_compile.compile(str(self.service),doraise=True,invalidation_mode=py_compile.PycInvalidationMode.UNCHECKED_HASH)
        self.service.write_bytes(original)
        baseline=subprocess.run([sys.executable,'-B','-c','import publication_service'],cwd=self.package,
                                capture_output=True,text=True,timeout=5)
        self.assertEqual(baseline.returncode,0);self.assertTrue(marker.exists());marker.unlink()
        for action in ('enable','status'):
            self.action(action);self.assertFalse(marker.exists())
            self.assertEqual(self.db.read_bytes(),self.original)

    def test_canonical_default_home_is_refused_for_home_aliases(self):
        actual=self.base/'fabricated-home';actual.mkdir(mode=0o700)
        alias=self.base/'fabricated-alias';alias.symlink_to(actual,target_is_directory=True)
        default=actual/'.codex'
        for preexisting in (False,True):
            if preexisting:default.mkdir(mode=0o700)
            for environment_home in (actual,alias):
                for chosen in (str(default),str(alias/'.codex'),str(default)+'/../.codex',
                               str(actual)+'/./.codex'):
                    result=subprocess.run([sys.executable,'-B',str(self.helper),'plan','--home',chosen,
                        '--ledger',str(self.db),'--worker',str(self.worker),'--binding',str(self.binding_path)],
                        env={**os.environ,'HOME':str(environment_home)},capture_output=True,text=True,timeout=5)
                    self.assertEqual(result.returncode,2,(chosen,result.stdout,result.stderr))
                    self.assertEqual(json.loads(result.stdout)['status'],'unavailable-or-drifted')
                    self.assertFalse((default/'config.toml').exists())
            self.assertEqual(default.exists(),preexisting)
        self.assertEqual(list(default.iterdir()),[])
        self.assertEqual(self.db.read_bytes(),self.original)

    def large_plan(self, receipt_bytes):
        if not self.home.exists():self.home.mkdir(mode=0o700)
        value=self.make_plan();worker=self.base/'deep';worker.mkdir()
        canonical=lambda x:json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=True)
        home_id=[self.home.stat().st_dev,self.home.stat().st_ino]
        while True:
            value['spec'].update(worker=str(worker),worker_identity=[worker.stat().st_dev,worker.stat().st_ino],
                worker_ancestors={str(p):[p.stat().st_dev,p.stat().st_ino] for p in worker.parents})
            value['sha256']=hashlib.sha256(canonical(value['spec']).encode()).hexdigest()
            size=len((canonical({'plan':value,'home_identity':home_id})+'\n').encode())
            if size>=64800:break
            worker=worker/'a';worker.mkdir()
        self.worker=worker
        request={k:v for k,v in self.binding.items() if k!='generation'};request['action']='register'
        remaining=receipt_bytes-size
        self.assertGreaterEqual(remaining,0)
        for field in ('owner','audience','revision','authority_revision','policy_revision'):
            growth=min(256-len(request[field]),remaining);request[field]+='x'*growth;remaining-=growth
        self.assertEqual(remaining,0)
        self.binding=json.loads(self.run_service('--control',request=request).stdout)['binding']
        self.binding_path.write_text(json.dumps(self.binding));value=self.make_plan()
        self.plan_path.write_text(canonical(value)+'\n')
        self.assertEqual(len((canonical({'plan':value,'home_identity':home_id})+'\n').encode()),receipt_bytes)
        self.assertLessEqual(self.plan_path.stat().st_size,65536)
        return self.db.read_bytes()

    def test_exact_limit_receipt_remains_readable_and_reversible(self):
        ledger=self.large_plan(65536)
        self.action('enable');self.assertEqual((self.home/'delivery-setup.json').stat().st_size,65536)
        self.action('status');self.action('disable');self.action('disable')
        self.assertEqual(self.db.read_bytes(),ledger)

    def test_plan_does_not_emit_an_unreadable_serialized_result(self):
        self.large_plan(65536)
        request={k:v for k,v in self.binding.items() if k!='generation'};request['action']='register'
        field=next(k for k in ('owner','audience','revision','authority_revision','policy_revision') if len(request[k])<=156)
        request[field]+='x'*100
        self.binding=json.loads(self.run_service('--control',request=request).stdout)['binding']
        self.binding_path.write_text(json.dumps(self.binding));before=self.db.read_bytes()
        self.make_plan(ok=False)
        self.assertFalse((self.home/'config.toml').exists())
        self.assertFalse((self.home/'delivery-setup.json').exists())
        self.assertEqual(self.db.read_bytes(),before)

    def test_over_limit_receipt_never_publishes_receipt_or_config(self):
        ledger=self.large_plan(65537)
        self.action('enable',ok=False)
        self.assertFalse((self.home/'config.toml').exists())
        self.assertFalse((self.home/'delivery-setup.json').exists())
        self.assertEqual(list(self.home.iterdir()),[])
        self.assertEqual(self.db.read_bytes(),ledger)

    def test_over_limit_candidate_preserves_disabled_recovery_state(self):
        self.make_plan();self.action('enable');self.action('disable')
        saved={name:(self.home/name).read_bytes() for name in ('config.toml','delivery-setup.json')}
        ledger=self.large_plan(65537);self.action('enable',ok=False)
        self.assertEqual({name:(self.home/name).read_bytes() for name in saved},saved)
        self.assertEqual(self.db.read_bytes(),ledger)

    def test_disable_after_disposable_interpreter_retarget_and_removal(self):
        import shutil
        original=self.base/'python-original';shutil.copy2(Path(sys.executable).resolve(),original)
        alias=self.base/'python-alias';alias.symlink_to(original)
        def invoke(python,action):
            args=['plan','--home',str(self.home),'--ledger',str(self.db),'--worker',str(self.worker),
                  '--binding',str(self.binding_path)] if action=='plan' else [action,'--plan',str(self.plan_path),'--expected-sha256',self.digest]
            return subprocess.run([str(python),'-B',str(self.helper),*args],
                env={**os.environ,'PYTHONHOME':sys.base_prefix},capture_output=True,text=True,timeout=5)
        planned=invoke(alias,'plan');self.assertEqual(planned.returncode,0,planned.stderr)
        self.plan_path.write_text(planned.stdout);self.digest=json.loads(planned.stdout)['sha256']
        self.assertEqual(invoke(alias,'enable').returncode,0)
        receipt=(self.home/'delivery-setup.json').read_bytes()
        alias.unlink();alias.symlink_to(Path(sys.executable).resolve())
        for action in ('enable','status'):
            self.assertEqual(invoke(alias,action).returncode,2)
        self.assertEqual(json.loads(invoke(alias,'disable').stdout)['status'],'disabled')
        # Reenable with the still-original executable, then remove only that copy.
        self.assertEqual(invoke(original,'enable').returncode,0)
        original.unlink();self.service.unlink()
        self.assertEqual(json.loads(invoke(alias,'disable').stdout)['status'],'disabled')
        self.assertEqual(invoke(alias,'disable').returncode,0)
        self.assertEqual((self.home/'delivery-setup.json').read_bytes(),receipt)
        self.assertEqual(self.db.read_bytes(),self.original)

    def test_recorded_interpreter_must_be_structurally_valid(self):
        value=self.make_plan();self.action('enable');self.service.unlink()
        before=(self.home/'config.toml').read_bytes()
        for path in ('python3','/tmp/../python','/tmp/./python','/tmp//python','/', '/tmp/python\x00', None):
            changed=json.loads(json.dumps(value));changed['spec']['python']=path
            changed['sha256']=hashlib.sha256(json.dumps(changed['spec'],sort_keys=True,
                separators=(',',':'),ensure_ascii=True).encode()).hexdigest()
            self.plan_path.write_text(json.dumps(changed));self.action('disable',ok=False,digest=changed['sha256'])
            self.assertEqual((self.home/'config.toml').read_bytes(),before)

    def test_write_helpers_reject_unreadable_outputs_before_mutation(self):
        import runpy
        helper=runpy.run_path(str(self.helper));target=self.trusted/'bounded-file'
        with self.assertRaises(helper['Refused']):helper['create'](target,b'x'*65537)
        self.assertFalse(target.exists())
        helper['create'](target,b'x'*65536);self.assertEqual(len(helper['read'](target)),65536)
        self.home.mkdir(mode=0o700);config=self.home/'config.toml';config.write_bytes(b'SYNTHETIC disabled')
        with self.assertRaises(helper['Refused']):helper['replace_config'](self.home,b'SYNTHETIC disabled',b'x'*65537)
        self.assertEqual(config.read_bytes(),b'SYNTHETIC disabled')

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

    def test_toml_strings_roundtrip_unicode_scalars_and_controls(self):
        import importlib.util
        import tomllib
        spec=importlib.util.spec_from_file_location('fixture_setup',self.helper)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        values=[chr(i) for i in range(128)]+['é','🚀','\U0010ffff','quotes " and \\','\n\r\t']
        for value in values:
            with self.subTest(value=repr(value)):
                encoded=module.toml_string(value)
                parsed=tomllib.loads(encoded+' = '+encoded+'\narray = '+module.toml_strings([value]))
                self.assertEqual(parsed[value],value);self.assertEqual(parsed['array'],[value])
        for value in ('\ud800','\udfff',os.fsdecode(b'\xff')):
            with self.assertRaises(UnicodeError):module.toml_string(value)

    def test_control_and_unicode_paths_roundtrip_in_all_config_positions(self):
        import tomllib
        suffix=''.join(chr(i) for i in range(1,32))+'\x7f " \\ 🚀'
        old=self.package;self.package=self.base/('package'+suffix);old.rename(self.package)
        self.service=self.package/'publication_service.py';self.helper=self.package/'publication_setup.py'
        old=self.db;self.db=self.trusted/('ledger'+suffix);old.rename(self.db)
        old=self.worker;self.worker=self.base/('worker'+suffix);old.rename(self.worker)
        self.home=self.trusted/('home'+suffix)
        value=self.make_plan()
        for action,enabled in (('enable',True),('status',True),('disable',False)):
            self.action(action)
            d=tomllib.loads((self.home/'config.toml').read_text())
            fs=d['permissions']['delivery-local']['filesystem']
            self.assertEqual(fs[str(self.home)],'deny');self.assertEqual(fs[str(self.worker)],'write')
            self.assertEqual(fs[str(self.package)],'deny');self.assertEqual(fs[str(self.db.parent)],'deny')
            server=d['mcp_servers']['delivery_publication']
            self.assertEqual(server['args'],['-B',str(self.service),'--db',str(self.db)])
            self.assertEqual(server['command'],value['spec']['python'])
            self.assertIs(server['enabled'],enabled)
            self.assertEqual(self.db.read_bytes(),self.original)

    def test_unsupported_byte_and_surrogate_paths_refuse_before_state_changes(self):
        unsupported=self.base/os.fsdecode(b'worker-\xff');unsupported.mkdir()
        worker=self.worker;self.worker=unsupported
        self.make_plan(ok=False);self.assertFalse(self.home.exists())
        self.assertEqual(self.db.read_bytes(),self.original);self.worker=worker
        value=self.make_plan();self.action('enable')
        saved={name:(self.home/name).read_bytes() for name in ('config.toml','delivery-setup.json')}
        for bad in ('\ud800','\udfff',os.fsdecode(b'\xff')):
            for field in ('home','ledger','worker','python'):
                changed=json.loads(json.dumps(value));changed['spec'][field]+=bad
                changed['sha256']=hashlib.sha256(json.dumps(changed['spec'],sort_keys=True,
                    separators=(',',':'),ensure_ascii=True).encode()).hexdigest()
                self.plan_path.write_text(json.dumps(changed))
                for action in ('enable','status','disable'):
                    self.action(action,ok=False,digest=changed['sha256'])
                    self.assertEqual({name:(self.home/name).read_bytes() for name in saved},saved)
                    self.assertEqual(self.db.read_bytes(),self.original)

    def test_special_home_paths_roundtrip_without_manual_editing(self):
        import tomllib
        self.home=self.trusted/'spaces " quote \\ rocket 🚀'
        self.make_plan();self.action('enable')
        d=tomllib.loads((self.home/'config.toml').read_text())
        self.assertEqual(d['permissions']['delivery-local']['filesystem'][str(self.home)],'deny')
        self.assertEqual(self.action('disable')['status'],'disabled')

    def test_held_setup_lock_refuses_within_deadline_without_state_changes(self):
        import fcntl
        import time
        self.make_plan();self.action('enable')
        saved={name:(self.home/name).read_bytes() for name in ('config.toml','delivery-setup.json')}
        lock_path=self.home/'.delivery-setup.lock'
        original_identity=(lock_path.stat().st_dev,lock_path.stat().st_ino)
        with lock_path.open('rb') as holder:
            fcntl.flock(holder,fcntl.LOCK_EX)
            for action in ('enable','status','disable'):
                start=time.monotonic();self.action(action,ok=False);elapsed=time.monotonic()-start
                self.assertGreaterEqual(elapsed,1.8);self.assertLess(elapsed,4.0)
                self.assertEqual({name:(self.home/name).read_bytes() for name in saved},saved)
                self.assertEqual(self.db.read_bytes(),self.original)
                self.assertEqual((lock_path.stat().st_dev,lock_path.stat().st_ino),original_identity)
                # The refusing child must not break or replace the holder's lock.
                with lock_path.open('rb') as contender:
                    with self.assertRaises(BlockingIOError):
                        fcntl.flock(contender,fcntl.LOCK_EX | fcntl.LOCK_NB)
        self.assertEqual(self.action('disable')['status'],'disabled')
        self.assertEqual(self.db.read_bytes(),self.original)

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
        # Unknown/removed pinned0.163.0 keys cannot serve as restrictions.
        self.assertTrue(set(d['features']).isdisjoint({
            'codex_hooks','js_repl','plugin_hooks','remote_control','multi_agent_mode'}))


if __name__ == '__main__':
    unittest.main()
