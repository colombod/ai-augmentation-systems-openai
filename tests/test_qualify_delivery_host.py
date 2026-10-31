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
