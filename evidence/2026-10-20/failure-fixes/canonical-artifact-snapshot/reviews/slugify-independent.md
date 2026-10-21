# Independent slugify review

Issue: fullcycle-8f7
Reviewer lane: reviewer
Product root: /private/var/folders/2r/5gvkx5wx0g37m4grvjjdt88m0000gn/T/delivery-full-cli-8frrftqa/product
Exact HEAD (before and after execution): b87785b9a8f2f3fc3cd532f683a8228619245b08
Decision: approve. No contract violations found.

This protected review is a worker submission. It is not authenticated human approval, task acceptance, or hosted CI evidence. No hosted CI is present. All observations below are native local macOS shell/Python observations. No product changes, temporary files, heredocs, or intentional filesystem writes were used in test execution; Python bytecode generation was disabled. Git attempted macOS cache creation and was denied; these diagnostics are preserved below.

## Code and test assessment

Read slugify.py, test_slugify.py, README.md directly. The ASCII allowlist replaces maximal runs before lowercasing, so Unicode characters with ASCII lowercase mappings (such as Kelvin sign) remain separators. Edge hyphens are stripped and print emits exactly one newline. main checks exactly one argument and returns 2 otherwise. Repository tests check CLI stdout, stderr, and status, including original-character Unicode behavior. Independent subprocess checks additionally cover combining marks, zero-width joiner, emoji and control whitespace. Exhaustive in-memory checking tested A + each of 1,114,112 Unicode code points + B against a separately implemented character-scanning oracle; this is function coverage, not 1,114,112 CLI launches.

## Initial native observations

Shell tool exposes combined terminal output for direct commands, so stdout/stderr are not independently attributed for those commands. Child CLI stdout and stderr are captured separately and printed as JSON below, preserving exact newlines.

Command: `git rev-parse HEAD`
Exit: 0
Combined output:
```text
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-jiKOs3xU' (errno=Operation not permitted)
b87785b9a8f2f3fc3cd532f683a8228619245b08
```

Command: `git status --short`
Exit: 0
Combined output:
```text
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-bNh7Ofap' (errno=Operation not permitted)
?? .delivery-evidence/
```
The existing untracked .delivery-evidence/ was left untouched. No tracked changes in the reviewed product files were reported by git diff.

Command: `rg --files -g '!**/.git/**' -g '!*lock*'`
Exit: 0
Combined output:
```text
README.md
slugify.py
test_slugify.py
```

## Captured native command evidence

Command:
```sh
cat slugify.py test_slugify.py README.md
```
Exit: 0
Full combined output:
```text
"""Convert one text argument into an ASCII slug."""

import re
import sys


def slugify(text):
    """Replace runs of original non-ASCII-alphanumeric characters with hyphens."""
    return re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-").lower()


def main():
    if len(sys.argv) != 2:
        print("usage: slugify.py TEXT", file=sys.stderr)
        return 2
    print(slugify(sys.argv[1]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
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
# Slugify fixture

Implement the operator-specified ASCII-only terminal slugifier.
```

Command:
```sh
git diff HEAD -- slugify.py test_slugify.py README.md
```
Exit: 0
Full combined output:
```text
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-HmMdZG9G' (errno=Operation not permitted)
```

Command:
```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest -v
```
Exit: 0
Full combined output:
```text
test_extra_argument_exits_two (test_slugify.SlugifyCliTests.test_extra_argument_exits_two) ... ok
test_missing_argument_exits_two (test_slugify.SlugifyCliTests.test_missing_argument_exits_two) ... ok
test_slug_output (test_slugify.SlugifyCliTests.test_slug_output) ... ok

----------------------------------------------------------------------
Ran 3 tests in 0.242s

OK
```

Independent native command (each child inherits PYTHONDONTWRITEBYTECODE=1 and uses -B):
```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B -c 'import json, os, subprocess, sys
cases = [
([], "", "usage: slugify.py TEXT\n", 2),
(["Hello, WORLD! 123"], "hello-world-123\n", "", 0),
(["--- A__B...C / 42 ---"], "a-b-c-42\n", "", 0),
([""], "\n", "", 0),
(["雪☃é --_!?\t\n"], "\n", "", 0),
(["AİBKC"], "a-b-c\n", "", 0),
(["Café déjà VU"], "caf-d-j-vu\n", "", 0),
(["A\r\n\tB"], "a-b\n", "", 0),
(["AZaz09"], "azaz09\n", "", 0),
(["--help"], "help\n", "", 0),
(["one", "two"], "", "usage: slugify.py TEXT\n", 2),
(["a\u0301b\u200dc😀d"], "a-b-c-d\n", "", 0)]
for args, out, err, code in cases:
    command = [sys.executable, "-B", "slugify.py", *args]
    result = subprocess.run(command, capture_output=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
    observed = dict(command=command, stdout=result.stdout.decode(), stderr=result.stderr.decode(), exit_code=result.returncode)
    print(json.dumps(observed, ensure_ascii=True))
    assert (result.stdout, result.stderr, result.returncode) == (out.encode(), err.encode(), code), observed
from slugify import slugify
def reference(text):
    result = []
    separator = False
    for char in text:
        if "A" <= char <= "Z" or "a" <= char <= "z" or "0" <= char <= "9":
            if separator and result:
                result.append("-")
            result.append(chr(ord(char) + 32) if "A" <= char <= "Z" else char)
            separator = False
        else:
            separator = True
    return "".join(result)
for value in range(0x110000):
    sample = "A" + chr(value) + "B"
    assert slugify(sample) == reference(sample), value
print("PASS: 12 CLI subprocess cases; exhaustive 1114112 Unicode code points checked in memory against independent character-scanning oracle.")
'
```
Exit: 0
Full combined output (JSON fields distinguish child stdout/stderr/status):
```text
{"command": ["/opt/homebrew/opt/python@3.14/bin/python3.14", "-B", "slugify.py"], "stdout": "", "stderr": "usage: slugify.py TEXT\n", "exit_code": 2}
{"command": ["/opt/homebrew/opt/python@3.14/bin/python3.14", "-B", "slugify.py", "Hello, WORLD! 123"], "stdout": "hello-world-123\n", "stderr": "", "exit_code": 0}
{"command": ["/opt/homebrew/opt/python@3.14/bin/python3.14", "-B", "slugify.py", "--- A__B...C / 42 ---"], "stdout": "a-b-c-42\n", "stderr": "", "exit_code": 0}
{"command": ["/opt/homebrew/opt/python@3.14/bin/python3.14", "-B", "slugify.py", ""], "stdout": "\n", "stderr": "", "exit_code": 0}
{"command": ["/opt/homebrew/opt/python@3.14/bin/python3.14", "-B", "slugify.py", "\u96ea\u2603\u00e9 --_!?\t\n"], "stdout": "\n", "stderr": "", "exit_code": 0}
{"command": ["/opt/homebrew/opt/python@3.14/bin/python3.14", "-B", "slugify.py", "A\u0130B\u212aC"], "stdout": "a-b-c\n", "stderr": "", "exit_code": 0}
{"command": ["/opt/homebrew/opt/python@3.14/bin/python3.14", "-B", "slugify.py", "Caf\u00e9 d\u00e9j\u00e0 VU"], "stdout": "caf-d-j-vu\n", "stderr": "", "exit_code": 0}
{"command": ["/opt/homebrew/opt/python@3.14/bin/python3.14", "-B", "slugify.py", "A\r\n\tB"], "stdout": "a-b\n", "stderr": "", "exit_code": 0}
{"command": ["/opt/homebrew/opt/python@3.14/bin/python3.14", "-B", "slugify.py", "AZaz09"], "stdout": "azaz09\n", "stderr": "", "exit_code": 0}
{"command": ["/opt/homebrew/opt/python@3.14/bin/python3.14", "-B", "slugify.py", "--help"], "stdout": "help\n", "stderr": "", "exit_code": 0}
{"command": ["/opt/homebrew/opt/python@3.14/bin/python3.14", "-B", "slugify.py", "one", "two"], "stdout": "", "stderr": "usage: slugify.py TEXT\n", "exit_code": 2}
{"command": ["/opt/homebrew/opt/python@3.14/bin/python3.14", "-B", "slugify.py", "a\u0301b\u200dc\ud83d\ude00d"], "stdout": "a-b-c-d\n", "stderr": "", "exit_code": 0}
PASS: 12 CLI subprocess cases; exhaustive 1114112 Unicode code points checked in memory against independent character-scanning oracle.
```

Final command: `git rev-parse HEAD`
Exit: 0
Full combined output:
```text
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-KLpfWhtK' (errno=Operation not permitted)
b87785b9a8f2f3fc3cd532f683a8228619245b08
```
