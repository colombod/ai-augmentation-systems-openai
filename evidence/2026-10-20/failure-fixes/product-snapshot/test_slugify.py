"""Exercise the public CLI, including its output and exit status."""

from pathlib import Path
import subprocess
import sys
import unittest


CLI = Path(__file__).with_name("slugify.py")


class SlugifyCliTests(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run(
            [sys.executable, "-B", str(CLI), *args],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_slug_output(self):
        cases = [
            ("Hello, WORLD! 123", "hello-world-123\n"),
            ("--- A__B...C / 42 ---", "a-b-c-42\n"),
            ("", "\n"),
            (" --_!? \t\n", "\n"),
            ("雪☃é", "\n"),
            ("Café déjà VU", "caf-d-j-vu\n"),
            ("A雪☃B—C", "a-b-c\n"),
            ("AİBKC", "a-b-c\n"),
            ("AZaz09", "azaz09\n"),
            ("--help", "help\n"),
            ("---", "\n"),
        ]
        for original, expected in cases:
            with self.subTest(original=original):
                result = self.run_cli(original)
                self.assertEqual(result.returncode, 0)
                self.assertEqual(result.stdout, expected)
                self.assertEqual(result.stderr, "")

    def test_missing_argument_exits_two(self):
        result = self.run_cli()
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertIn("TEXT", result.stderr)

    def test_extra_argument_exits_two(self):
        result = self.run_cli("one", "two")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")


if __name__ == "__main__":
    unittest.main()
