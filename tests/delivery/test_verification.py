import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'plugins/delivery/scripts'))
import verification as V


class VerificationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.product = self.root/'product'
        self.product.mkdir()
        self.git('init','-q')
        self.git('config','user.email','fixture@example.invalid')
        self.git('config','user.name','Fixture')
        (self.product/'product.txt').write_text('committed')
        self.git('add','product.txt')
        self.git('commit','-qm','Synthetic fixture')
        self.head = self.git('rev-parse','HEAD').strip()

    def tearDown(self):
        self.temp.cleanup()

    def git(self, *args):
        return subprocess.check_output(['git','-C',str(self.product),*args], text=True)

    def python(self, code):
        return [sys.executable,'-B','-c',code]

    def test_exact_review_uses_fresh_committed_bytes_and_does_not_touch_builder(self):
        (self.product/'product.txt').write_text('uncommitted builder edit')
        result = V.review(self.product, self.head, self.python("from pathlib import Path; print(Path('product.txt').read_text())"))
        self.assertTrue(result['passed'])
        self.assertEqual(result['run']['stdout'], 'committed\n')
        self.assertEqual((self.product/'product.txt').read_text(), 'uncommitted builder edit')
        self.assertFalse(result['accepted'])

    def test_abbreviated_head_and_ref_name_are_refused(self):
        for head in (self.head[:12], 'HEAD', 'main', '-bad'):
            with self.subTest(head=head), self.assertRaises(ValueError):
                V.review(self.product, head, self.python('print(1)'))

    def test_nonzero_timeout_and_tracked_mutation_fail_with_actual_output(self):
        for code, timeout in [("import sys; print('failure'); print('err',file=sys.stderr); sys.exit(3)", 2),
                              ("import time; print('started',flush=True); time.sleep(10)", .05),
                              ("from pathlib import Path; Path('product.txt').write_text('mutated')", 2)]:
            with self.subTest(code=code):
                result = V.review(self.product,self.head,self.python(code),timeout)
                self.assertFalse(result['passed'])
                self.assertIn('run', result)
        result = V.capture(self.python("import sys; print('failure'); print('err',file=sys.stderr); sys.exit(3)"),self.product,2)
        self.assertEqual((result['exit_code'],result['stdout'],result['stderr']), (3,'failure\n','err\n'))

    def test_surface_revision_is_observed_and_change_fails(self):
        version = self.product/'version'
        version.write_text(self.head)
        query = self.python("from pathlib import Path; print(Path('version').read_text())")
        result = V.verify(self.product,self.head,'Criterion A',query,self.python("print('expected result')"),contains='expected')
        self.assertTrue(result['passed'])
        result = V.verify(self.product,self.head,'Criterion A',query,self.python("from pathlib import Path; Path('version').write_text('b'*40); print('expected result')"))
        self.assertFalse(result['passed'])
        result = V.verify(self.product,self.head,'Criterion A',query,self.python("raise Exception('must not run')"))
        self.assertNotIn('run',result)
        self.assertFalse(result['passed'])

    def test_matching_output_is_required_and_does_not_override_nonzero(self):
        query = self.python('print('+repr(self.head)+')')
        for code, contains in [("print('other')",'expected'), ("import sys; print('expected'); sys.exit(2)",'expected')]:
            result = V.verify(self.product,self.head,'Criterion A',query,self.python(code),contains=contains)
            self.assertFalse(result['passed'])

    def test_truncation_missing_executable_and_invalid_timeout_fail_closed(self):
        result = V.capture(self.python("print('x'*300000)"),self.product,2)
        self.assertTrue(result['truncated'])
        self.assertFalse(V.successful(result))
        result = V.capture(['/nonexistent-delivery-fixture'],self.product,2)
        self.assertTrue(result['launch_failed'])
        self.assertFalse(V.successful(result))
        for timeout in (0, -1, float('nan'), float('inf'), True):
            with self.subTest(timeout=timeout), self.assertRaises(ValueError):
                V.capture(self.python('print(1)'),self.product,timeout)

    def test_evidence_is_exclusive_and_retains_hash(self):
        output = self.root/'evidence.json'
        result = V.save_record(output, {'passed':False,'stdout':'failure'})
        self.assertEqual(result['sha256'], hashlib.sha256(output.read_bytes()).hexdigest())
        with self.assertRaises(FileExistsError):
            V.save_record(output, {'passed':True})
        self.assertFalse(json.loads(output.read_text())['passed'])

    def test_index_flags_cannot_hide_reviewed_byte_changes(self):
        for flag in ('--assume-unchanged','--skip-worktree'):
            command = self.python("import subprocess; from pathlib import Path; subprocess.run(['git','update-index',"+repr(flag)+",'product.txt'],check=True); Path('product.txt').write_text('different bytes')")
            result = V.review(self.product,self.head,command)
            self.assertFalse(result['passed'])
            self.assertIn('hides tracked bytes',result['tracked_changes']['error'])

    def test_inherited_role_and_git_redirection_are_cleared(self):
        with patch.dict(os.environ, {'GIT_DIR':'/wrong','GIT_CONFIG_COUNT':'1','DELIVERY_ROLE':'operator','BD_ACTOR':'operator','BEADS_DIR':'/wrong'}):
            result = V.capture(self.python("import os; print([k for k in os.environ if k.startswith(('GIT_', 'DELIVERY_', 'BEADS_')) or k == 'BD_ACTOR'])"), self.product,2)
        self.assertEqual(result['stdout'], '[]\n')


if __name__ == '__main__':
    unittest.main()
