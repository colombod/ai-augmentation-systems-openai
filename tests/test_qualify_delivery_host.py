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


if __name__ == '__main__':
    unittest.main()
