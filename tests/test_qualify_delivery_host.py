"""Source/preflight tests only. Never launch Codex, sandbox, installation or server."""
import importlib.util
import io
import queue
from pathlib import Path
import unittest
from unittest.mock import patch

PATH = Path(__file__).resolve().parents[1] / 'scripts/qualify_delivery_host.py'
spec = importlib.util.spec_from_file_location('qualification', PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ProfileTests(unittest.TestCase):
    def test_fixed_probe_identifies_each_unexpected_success_without_payload(self):
        import ast
        from contextlib import redirect_stdout, redirect_stderr
        tree = ast.parse(PATH.read_text())
        function = next(node for node in tree.body if isinstance(node,ast.FunctionDef)
                        and node.name == 'sandbox_checks')
        code = next(node.value.value for node in ast.walk(function)
                    if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name)
                    and t.id == 'code' for t in node.targets))
        labels = ('control-read','control-write','proc-read','network-connect')
        for allowed in (*labels, None):
            with self.subTest(allowed=allowed):
                def action(label):
                    if label != allowed:
                        raise PermissionError('SYNTHETIC PRIVATE DIAGNOSTIC')
                    return b'SYNTHETIC PRIVATE PAYLOAD'
                class FakePath:
                    def __init__(self,name): self.name = name
                    def read_bytes(self):
                        return action('proc-read' if self.name.startswith('/proc/') else 'control-read')
                    def write_text(self,value):
                        return None if self.name == '/synthetic/result' else action('control-write')
                stdout,stderr = io.StringIO(),io.StringIO()
                with patch('sys.argv',['probe','/synthetic/control','/synthetic/result','12345']), \
                     patch('pathlib.Path',FakePath), \
                     patch('socket.create_connection',side_effect=lambda *a,**k:action('network-connect')), \
                     redirect_stdout(stdout), redirect_stderr(stderr):
                    if allowed is None:
                        exec(code,{})
                    else:
                        with self.assertRaises(SystemExit) as raised:
                            exec(code,{})
                        self.assertEqual(raised.exception.code,9)
                self.assertEqual(stderr.getvalue(),'' if allowed is None else
                                 'unexpected-route-success:'+allowed+'\n')
                self.assertEqual(stdout.getvalue(),'restricted-routes-passed\n' if allowed is None else '')

    def test_native_grant_cannot_override_protected_or_worker_roots(self):
        worker,trusted,home = Path('/tmp/worker'),Path('/tmp/trusted'),Path('/home/example')
        for native in (worker/'codex',trusted/'codex',home/'.codex/codex',Path('/proc/native')):
            with self.subTest(native=native):
                with self.assertRaisesRegex(module.Unsupported,'overlaps-protected-root'):
                    module.sandbox_config(worker,trusted,home,native)

    def test_path_keys_are_toml_values_not_literal_dotted_override_segments(self):
        import tomllib
        worker = Path('/tmp/synthetic.worker/with space/🧪')
        trusted = Path('/tmp/synthetic.trusted')
        home = Path('/home/synthetic.user/😀')
        native = Path('/tmp/synthetic.npm/vendor/bin/codex')
        config = module.sandbox_config(worker, trusted, home, native)
        parsed = {}
        for flag, override in zip(config[::2], config[1::2]):
            self.assertEqual(flag, '-c')
            key, value = override.split('=', 1)
            node = parsed
            for segment in key.split('.')[:-1]:
                node = node.setdefault(segment, {})
            node[key.split('.')[-1]] = tomllib.loads('value=' + value)['value']
        self.assertEqual(parsed, {'default_permissions':'delivery-qualification',
            'permissions':{'delivery-qualification':{
                'filesystem':{':minimal':'read',str(worker):'write',str(trusted):'deny',
                              str(home / '.codex'):'deny','/proc':'deny',str(native):'read'},
                'network':{'enabled':False}}}})
        for key in parsed['permissions']['delivery-qualification']['filesystem']:
            self.assertTrue(key.startswith(('/', ':')))


class NativeResolverTests(unittest.TestCase):
    def fixture(self, base, alias_package=False):
        import json
        launcher = base / 'launcher/bin/codex.js'
        launcher.parent.mkdir(parents=True)
        launcher.write_text('#!/usr/bin/env node\n')
        launcher.chmod(0o700)
        dependency = 'npm:@openai/codex@0.163.0-linux-x64' if alias_package else '0.163.0'
        (launcher.parent.parent/'package.json').write_text(json.dumps({
            'name':'@openai/codex','version':'0.163.0','bin':{'codex':'bin/codex.js'},
            'optionalDependencies':{'@openai/codex-linux-x64':dependency}}))
        manifest = base / 'platform/package.json'
        manifest.parent.mkdir()
        manifest.write_text(json.dumps({'name':'@openai/codex' if alias_package else '@openai/codex-linux-x64',
            'version':'0.163.0-linux-x64' if alias_package else '0.163.0'}))
        native = manifest.parent/'vendor/x86_64-unknown-linux-musl/bin/codex'
        native.parent.mkdir(parents=True)
        native.write_bytes(b'\x7fELFsynthetic-fixture-not-executable-code')
        native.chmod(0o700)
        return launcher, manifest, native

    def test_pinned_npm_layout_resolves_only_exact_native_file_without_execution(self):
        import tempfile,json
        for alias_package in (False,True):
            with self.subTest(alias=alias_package), tempfile.TemporaryDirectory() as directory:
                base = Path(directory)
                launcher,manifest,native = self.fixture(base,alias_package)
                result = module.subprocess.CompletedProcess([],0,json.dumps(str(manifest)),'')
                with patch.object(module.subprocess,'run',return_value=result) as run, \
                     patch.object(module.platform,'machine',return_value='x86_64'):
                    self.assertEqual(module.resolve_native_codex(str(launcher),{'PATH':'/bin'},base),native)
                command = run.call_args.args[0]
                self.assertEqual(command[:2],['node','-e'])
                self.assertIn('createRequire',command[2])
                self.assertEqual(command[3:],[str(launcher),'@openai/codex-linux-x64'])
                self.assertEqual(run.call_count,1)

    def test_direct_elf_does_not_run_resolver(self):
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            native = Path(directory)/'codex'
            native.write_bytes(b'\x7fELFfixture')
            native.chmod(0o700)
            with patch.object(module.subprocess,'run') as run:
                self.assertEqual(module.resolve_native_codex(str(native),{},Path(directory)),native)
                run.assert_not_called()

    def test_wrong_platform_identity_and_missing_native_fail_without_fallback(self):
        import tempfile,json
        for missing in (False,True):
            with self.subTest(missing=missing), tempfile.TemporaryDirectory() as directory:
                base = Path(directory)
                launcher,manifest,native = self.fixture(base)
                if missing:
                    native.unlink()
                else:
                    manifest.write_text(json.dumps({'name':'untrusted','version':'0.163.0'}))
                result = module.subprocess.CompletedProcess([],0,json.dumps(str(manifest)),'')
                with patch.object(module.subprocess,'run',return_value=result) as run, \
                     patch.object(module.platform,'machine',return_value='x86_64'):
                    with self.assertRaises((module.Unsupported,FileNotFoundError)):
                        module.resolve_native_codex(str(launcher),{},base)
                self.assertEqual(run.call_count,1)


class ConsumerIsolationTests(unittest.TestCase):
    def test_consumer_keeps_sandbox_prefix_and_receives_released_bytes_only_on_stdin(self):
        import tempfile,json
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            db,control = base/'ledger',base/'control'
            db.write_text('SYNTHETIC ledger');control.write_text('SYNTHETIC control')
            prefix = ['codex','-c','fixed-profile','sandbox','--permission-profile','delivery-qualification','--']
            output = json.dumps({'files':[{'name':'counter.txt','content':'1'}]})
            env = {'HOME':'/actual','PATH':'/bin'}
            with patch.object(module,'run',return_value=module.subprocess.CompletedProcess([],0,'consumed\n','')) as run:
                module.consume_released_bundle(prefix,env,base,db,control,output)
            args = run.call_args.args
            self.assertEqual(args[0],prefix+['/usr/bin/python3','-c',module.CONSUMER_CODE,str(db),str(control)])
            self.assertIs(args[1],env)
            self.assertEqual(args[2:],(base,output))
            self.assertNotIn(output,args[0])

    def test_readable_fixture_fails_instead_of_claiming_consumer_isolation(self):
        import tempfile,json
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            db,control = base/'ledger',base/'control'
            db.write_text('SYNTHETIC ledger');control.write_text('SYNTHETIC control')
            # Ordinary Python negative control only, never Codex or sandbox.
            result = module.subprocess.run(['/usr/bin/python3','-c',module.CONSUMER_CODE,str(db),str(control)],
                input=json.dumps({'files':[{'name':'counter.txt','content':'1'}]}),
                text=True,capture_output=True,timeout=5,env=module.child_environment(module.os.environ))
            self.assertEqual(result.returncode,11)
            self.assertEqual(result.stdout,'')

    def test_expected_denial_errnos_require_stable_trusted_fixtures(self):
        import errno,tempfile,json,sys
        for number in (errno.EACCES,errno.EPERM,errno.ENOENT):
            with self.subTest(errno=number), tempfile.TemporaryDirectory() as directory:
                base = Path(directory)
                db,control = base/'ledger',base/'control'
                db.write_text('SYNTHETIC ledger');control.write_text('SYNTHETIC control')
                output=json.dumps({'files':[{'name':'counter.txt','content':'1'}]})
                def fake_run(argv,env,cwd,data):
                    with patch.object(sys,'argv',['consumer',str(db),str(control)]), \
                         patch.object(sys,'stdin',io.StringIO(data)), \
                         patch.object(sys,'stdout',io.StringIO()) as stdout, \
                         patch.object(Path,'read_bytes',side_effect=OSError(number,'synthetic denial')):
                        exec(module.CONSUMER_CODE,{})
                        return module.subprocess.CompletedProcess(argv,0,stdout.getvalue(),'')
                with patch.object(module,'run',side_effect=fake_run):
                    result=module.consume_released_bundle(['synthetic'],{},base,db,control,output)
                self.assertEqual(result.stdout,'consumed\n')

    def test_unrelated_io_error_is_not_denial(self):
        import errno,sys
        with patch.object(sys,'argv',['consumer','synthetic']), \
             patch.object(Path,'read_bytes',side_effect=OSError(errno.EIO,'synthetic I/O failure')):
            with self.assertRaises(OSError) as error:
                exec(module.CONSUMER_CODE,{})
        self.assertEqual(error.exception.errno,errno.EIO)

    def test_removed_or_replaced_fixture_invalidates_successful_child_result(self):
        import tempfile
        for replace in (False,True):
            with self.subTest(replace=replace), tempfile.TemporaryDirectory() as directory:
                base=Path(directory)
                db,control=base/'ledger',base/'control'
                db.write_text('SYNTHETIC ledger');control.write_text('SYNTHETIC control')
                def fake_run(*args):
                    db.rename(base/'old-ledger')
                    if replace:
                        db.write_text('SYNTHETIC replacement')
                    return module.subprocess.CompletedProcess([],0,'consumed\n','')
                with patch.object(module,'run',side_effect=fake_run):
                    with self.assertRaisesRegex(module.Unsupported,'consumer-denial-fixture-changed'):
                        module.consume_released_bundle(['synthetic'],{},base,db,control,'{}')

    def test_absent_denial_fixture_is_not_evidence_of_isolation(self):
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            with patch.object(module,'run') as run:
                with self.assertRaisesRegex(module.Unsupported,'consumer-denial-fixture-missing'):
                    module.consume_released_bundle(['codex'],{},base,base/'absent',base/'absent-control','{}')
                run.assert_not_called()


class SourceTests(unittest.TestCase):
    def test_opt_in_rejected_before_runtime(self):
        with patch.object(module.subprocess, 'run') as run:
            with self.assertRaisesRegex(module.Unsupported, 'explicit-clean-runner'):
                module.check_host(False)
            run.assert_not_called()

    def test_codex_environment_rejected_before_runtime(self):
        with patch.dict(module.os.environ, {'CODEX_THREAD_ID':'synthetic'}, clear=True):
            with patch.object(module.subprocess, 'run') as run:
                with self.assertRaisesRegex(module.Unsupported, 'codex-environment-refused'):
                    module.check_host(True)
                run.assert_not_called()

    def test_child_environment_drops_credentials_and_overrides(self):
        source = {'HOME':'/actual', 'PATH':'/bin','OPENAI_API_KEY':'synthetic',
                  'GITHUB_TOKEN':'synthetic','CODEX_HOME':'/alternate','LD_PRELOAD':'bad'}
        self.assertEqual(module.child_environment(source), {'HOME':'/actual','PATH':'/bin'})

    def test_no_model_method_or_credential_mutation(self):
        import ast
        tree = ast.parse(PATH.read_text())
        methods = [node.args[0].value for node in ast.walk(tree)
                   if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                   and node.func.attr == 'call' and node.args and isinstance(node.args[0], ast.Constant)]
        self.assertFalse({'thread/start','thread/resume','turn/start'} & set(methods))
        self.assertIn('skills/list', methods)
        self.assertIn('mcpServerStatus/list', methods)


class ReaderTests(unittest.TestCase):
    def read(self, text):
        messages = queue.Queue(maxsize=module.MAX_RPC_QUEUE)
        module.receive_messages(io.StringIO(text), messages)
        return list(messages.queue)

    def test_valid_reply_then_eof(self):
        self.assertEqual(self.read('{"id":1,"result":{}}\n'),
                         [{'id':1,'result':{}}, None])

    def test_frame_read_is_bounded_before_allocation(self):
        class Oversized:
            def readline(self, limit):
                self.limit = limit
                return 'x' * limit
        stream = Oversized()
        messages = queue.Queue(maxsize=module.MAX_RPC_QUEUE)
        module.receive_messages(stream, messages)
        self.assertEqual(stream.limit, module.MAX_RPC_FRAME + 1)
        self.assertEqual(list(messages.queue), [None])

    def test_overflow_fails_closed(self):
        self.assertEqual(self.read('{}\n' * (module.MAX_RPC_QUEUE + 1)), [None])

    def test_invalid_or_partial_frame_discards_earlier_replies(self):
        for bad in ('[]\n', 'invalid\n', '{}'):
            with self.subTest(frame=bad):
                self.assertEqual(self.read('{}\n' + bad), [None])

    def test_full_queue_at_eof_fails_closed(self):
        self.assertEqual(self.read('{}\n' * module.MAX_RPC_QUEUE), [None])


class DiagnosticTests(unittest.TestCase):
    def test_known_diagnostics_use_fixed_informative_labels(self):
        samples = {
            'configuration':'Error parsing configuration: TOML parse error',
            'namespace':'unshare failed',
            'seccomp-landlock':'Landlock initialization failed',
            'mount-bwrap':'bwrap: failed to mount target',
            'permission-denied':'Permission denied',
            'missing-resource':'No such file or directory',
            'unsupported-argument':'unexpected argument',
        }
        for category, sample in samples.items():
            with self.subTest(category=category):
                diagnosis = module.command_diagnosis(sample, 1)
                self.assertIn(':category='+category+':', diagnosis)
                self.assertLessEqual(len(diagnosis),240)

    def test_combined_bwrap_does_not_hide_permission_or_missing_resource(self):
        diagnosis = module.command_diagnosis(
            'bwrap: Permission denied; No such file or directory /synthetic/private',1)
        self.assertIn(':category=mount-bwrap,permission-denied,missing-resource:',diagnosis)
        self.assertNotIn('/synthetic',diagnosis)

    def test_at_most_four_categories_preserve_full_digest_within_limit(self):
        import hashlib
        raw = ' '.join(phrases[0] for _,phrases in module.DIAGNOSTIC_CATEGORIES)
        diagnosis = module.command_diagnosis(raw,-2147483648)
        self.assertIn(':category=configuration,namespace,seccomp-landlock,mount-bwrap:',diagnosis)
        self.assertLessEqual(len(diagnosis),240)
        self.assertTrue(diagnosis.endswith(hashlib.sha256(raw.encode()).hexdigest()))

    def test_unknown_and_known_errors_never_echo_secret_or_path(self):
        import hashlib
        for prefix in ('opaque failure', 'Permission denied'):
            raw = prefix + ' /private/secret-location token=SYNTHETIC_KEY_4321'
            diagnosis = module.command_diagnosis(raw, 1)
            expected_category = 'unclassified' if prefix == 'opaque failure' else 'permission-denied'
            self.assertEqual(diagnosis, 'command-failed:exit=1:category='+expected_category+
                ':scan-truncated=0:stderr-sha256='+hashlib.sha256(raw.encode()).hexdigest())
            self.assertNotIn('/private',diagnosis)
            self.assertNotIn('SYNTHETIC_KEY',diagnosis)

    def test_scan_is_bounded_and_classification_is_not_root_cause(self):
        raw = 'x' * 65536 + ' Permission denied /synthetic/private'
        diagnosis = module.command_diagnosis(raw, -9)
        self.assertIn('exit=-9:category=unclassified:scan-truncated=1:',diagnosis)

    def test_command_failure_keeps_fixed_sanitized_diagnosis(self):
        result = module.subprocess.CompletedProcess(['synthetic'],1,'',
            'unshare: Operation not permitted /synthetic/private token=fixture')
        with patch.object(module.subprocess,'run',return_value=result) as run:
            with self.assertRaisesRegex(module.Unsupported, 'category=namespace') as raised:
                module.run(['synthetic'],{'HOME':'/actual'},Path('/tmp'))
            run.assert_called_once()
            self.assertNotIn('/synthetic',str(raised.exception))
            self.assertNotIn('token=',str(raised.exception))


class DetailTests(unittest.TestCase):
    def test_preserves_actionable_wording_but_redacts_values(self):
        raw = ('bwrap: cannot create directory "/synthetic/private folder/name": '
               'Permission denied; token=FIXTURE_SECRET; bearer FIXTURE_BEARER '
               'https://example.invalid/path; C:\\synthetic\\private; sk-fixturekey')
        value = module.redact_synthetic_probe_stderr(raw)
        self.assertIn('cannot create directory',value)
        self.assertIn('Permission denied',value)
        for secret in ('synthetic','FIXTURE_SECRET','FIXTURE_BEARER','example.invalid','fixturekey'):
            self.assertNotIn(secret,value)
        self.assertIn('[PATH]',value)
        self.assertIn('[CREDENTIAL]',value)

    def test_detail_is_bounded_and_controls_removed(self):
        value = module.redact_synthetic_probe_stderr('\x00\x1b[31m'+'x'*10000)
        self.assertLessEqual(len(value),2048)
        self.assertNotIn('\x00',value)
        self.assertNotIn('\x1b',value)

    def test_only_exact_stage_and_error_type_can_emit_detail(self):
        error = module.SyntheticProbeFailure('bwrap: Permission denied',1)
        self.assertIn('synthetic_probe_stderr',module.failure_report('sandbox-command-boundary',error))
        for stage in ('host-preflight','install-discovery','installed-service-local-release'):
            self.assertNotIn('synthetic_probe_stderr',module.failure_report(stage,error))
        ordinary = module.Unsupported('fixed-code')
        self.assertNotIn('synthetic_probe_stderr',module.failure_report('sandbox-command-boundary',ordinary))

    def test_auth_headers_environment_keys_and_traceback_paths_are_redacted(self):
        raw = ('Authorization: Bearer SYNTHETIC_BEARER_VALUE\n'
               'OPENAI_API_KEY=SYNTHETIC_KEY_VALUE\n'
               'GITHUB_TOKEN=shortvalue github_pat_fixturetoken\n'
               'File "/synthetic/traceback.py", line 3\r\n'
               'failed to create namespace')
        value = module.redact_synthetic_probe_stderr(raw)
        self.assertNotIn('SYNTHETIC_',value)
        self.assertNotIn('shortvalue',value)
        self.assertNotIn('fixturetoken',value)
        self.assertNotIn('/synthetic',value)
        self.assertNotIn('\r',value)
        self.assertIn('failed to create namespace',value)

    def test_generic_command_failure_never_emits_detail_even_at_probe_stage(self):
        result = module.subprocess.CompletedProcess(['synthetic'],1,'','secret fixture diagnostic')
        with patch.object(module.subprocess,'run',return_value=result):
            with self.assertRaises(module.Unsupported) as raised:
                module.run(['synthetic'],{},Path('/tmp'))
        self.assertNotIn('synthetic_probe_stderr',
                         module.failure_report('sandbox-command-boundary',raised.exception))

    def test_detail_constructor_only_used_by_fixed_sandbox_probe(self):
        import ast
        tree = ast.parse(PATH.read_text())
        callers = []
        for function in tree.body:
            if isinstance(function,ast.FunctionDef):
                for node in ast.walk(function):
                    if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id == 'SyntheticProbeFailure':
                        callers.append(function.name)
        self.assertEqual(callers,['sandbox_checks'])
        import inspect
        self.assertEqual(tuple(inspect.signature(module.run).parameters),('argv','env','cwd','data','allowed'))


if __name__ == '__main__':
    unittest.main()
