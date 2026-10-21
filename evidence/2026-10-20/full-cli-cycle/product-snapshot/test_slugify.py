"""Exercise the public CLI, including its output and exit status."""

from pathlib import Path
import subprocess
import sys
import unittest


SCRIPT = Path(__file__).with_name("slugify.py")


class SlugifyCLITests(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            capture_output=True,
            text=True,
            check=False,
        )

    def assert_slug(self, text, expected):
        result = self.run_cli(text)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, expected + "\n")
        self.assertEqual(result.stderr, "")

    def test_punctuation_case_and_digits(self):
        self.assert_slug("Hello, WORLD! Version 42", "hello-world-version-42")

    def test_separator_runs_and_trimming(self):
        self.assert_slug(" --Alpha__ /\t\nBeta---99!!! ", "alpha-beta-99")

    def test_empty_and_no_alphanumeric_input(self):
        for text in ("", "!!!", " --_ /\t\n"):
            with self.subTest(text=text):
                self.assert_slug(text, "")

    def test_unicode_is_separator_without_transliteration(self):
        for text, expected in (
            ("CAFÉ déjà—VU", "caf-d-j-vu"),
            ("AİKſıB", "a-b"),
            ("東京😀", ""),
            ("A１２٣B", "a-b"),
        ):
            with self.subTest(text=text):
                self.assert_slug(text, expected)

    def test_text_starting_with_hyphens(self):
        self.assert_slug("--HELLO", "hello")

    def test_missing_argument_exits_two(self):
        result = self.run_cli()
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertIn("usage:", result.stderr)

    def test_extra_argument_exits_two(self):
        result = self.run_cli("hello", "world")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertIn("usage:", result.stderr)


if __name__ == "__main__":
    unittest.main()
