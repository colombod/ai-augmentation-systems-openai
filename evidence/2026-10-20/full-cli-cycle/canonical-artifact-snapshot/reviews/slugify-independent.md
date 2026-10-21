# Independent slugify review

Task: fullcycle-6m8
Product: /private/var/folders/2r/5gvkx5wx0g37m4grvjjdt88m0000gn/T/delivery-full-cli-3b8pu1g_/product
Exact HEAD before and after tests: 32746b7d72bbbb4263c2ecf8a737c1c1613f9bbe
Reviewer verdict: approved; no contract defects found.

Contract: Given exactly one text argument, python3 slugify.py TEXT lowercases ASCII A-Z, converts each maximal run of characters outside ASCII [A-Za-z0-9] to one hyphen, trims edge hyphens and prints one newline with exit 0; all-separator input prints an empty line, and missing TEXT exits 2.

This is an independent worker submission and local macOS terminal subprocess observation. It is not authenticated human approval. No hosted CI is present or claimed. No product edits, acceptance, closure, publishing, pushing, or merging were performed.

## Code inspection

Read actual slugify.py, test_slugify.py and README.md with native command `cat slugify.py test_slugify.py README.md` (exit 0). Full inspected committed source is included in the final verification transcript below. The ASCII-explicit negated character class replaces maximal separator runs before lowercasing, so Unicode casing cannot introduce ASCII letters. Trimming removes boundary separators. print adds exactly one newline. Argument count check emits usage to stderr and exits 2 for missing or extra arguments. Tests exercise subprocess stdout, stderr and exit codes, including Unicode confusables and non-ASCII digits.

Native command `git diff HEAD -- slugify.py test_slugify.py README.md` returned no diff (exit 0). `git ls-tree -r HEAD` returned:
```
100644 blob 4da18c02877fe0bc1e4ca22c76d98be4e14b6425	README.md
100644 blob 48762e6f86335556b75e46d06528128b95b08421	slugify.py
100644 blob 17dfbf0a56598ac3e3d25f9295e664ef811758b3	test_slugify.py
```
Both git commands emitted sandbox cache diagnostics, preserved here in command order:
```
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-IaiYKwG7' (errno=Operation not permitted)
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-UkcJ62Qi' (errno=Operation not permitted)
```
Initial native commands `git rev-parse HEAD`, `git status --short`, `rg --files -g '!**/.git/**' -g '!**/.beads/**'` returned the required SHA, `?? .delivery-evidence/`, and README.md/slugify.py/test_slugify.py respectively; overall exit 0. Initial git diagnostics:
```
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-LKPDZ0hq' (errno=Operation not permitted)
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-NrPTTYoF' (errno=Operation not permitted)
```
The untracked evidence directory was left untouched. Git's denied cache attempts are environmental observations, not hidden or waived failures; all git observations returned exit 0. Independent byte comparisons below establish that the tested source and tests equal the exact committed versions.

## Native tests and independent CLI cases

No heredocs, temporary files or product writes were used. PYTHONDONTWRITEBYTECODE=1 was inherited by all subprocesses; the test runner and independent CLI subprocesses also use python3 -B. JSON strings below preserve complete stdout/stderr including newlines and empty strings; argv arrays preserve exact subprocess arguments.

Exact native command:
```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B -c 'import json, os, platform, subprocess
print("host=" + platform.system() + " " + platform.release())
commands = [["git", "rev-parse", "HEAD"], ["git", "status", "--short"], ["python3", "-B", "-m", "unittest", "-v"]]
cases = [("ASCII", ["ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"], "abcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyz0123456789\n", 0), ("runs", [" --Hello___WORLD! 42--- "], "hello-world-42\n", 0), ("Unicode", ["AİKſıB CAFÉ 東京😀１２٣"], "a-b-caf\n", 0), ("separators", [" --_ /\t\n😀"], "\n", 0), ("empty", [""], "\n", 0), ("controls", ["A\t\n\rB"], "a-b\n", 0), ("hyphen text", ["--HELLO"], "hello\n", 0), ("missing", [], "", 2), ("extra", ["a", "b"], "", 2)]
for argv in commands:
    p = subprocess.run(argv, capture_output=True, text=True)
    print(json.dumps({"argv": argv, "stdout": p.stdout, "stderr": p.stderr, "exit": p.returncode}, ensure_ascii=True))
    assert p.returncode == 0
for label, args, expected, code in cases:
    argv = ["python3", "-B", "slugify.py"] + args
    p = subprocess.run(argv, capture_output=True, text=True)
    print(json.dumps({"case": label, "argv": argv, "stdout": p.stdout, "stderr": p.stderr, "exit": p.returncode}, ensure_ascii=True))
    assert (p.stdout, p.returncode) == (expected, code), label
    assert p.stderr == ("" if code == 0 else "usage: python3 slugify.py TEXT\n"), label
print("Independent CLI assertions: 9 passed")
'
```

Complete captured output (stdout/stderr as returned by native shell tool):
```text
host=Darwin 27.0.0
{"argv": ["git", "rev-parse", "HEAD"], "stdout": "32746b7d72bbbb4263c2ecf8a737c1c1613f9bbe\n", "stderr": "git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead\ngit: error: couldn't create cache file '/tmp/xcrun_db-YWP3XiKd' (errno=Operation not permitted)\n", "exit": 0}
{"argv": ["git", "status", "--short"], "stdout": "?? .delivery-evidence/\n", "stderr": "git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead\ngit: error: couldn't create cache file '/tmp/xcrun_db-dzlYteRj' (errno=Operation not permitted)\n", "exit": 0}
{"argv": ["python3", "-B", "-m", "unittest", "-v"], "stdout": "", "stderr": "test_empty_and_no_alphanumeric_input (test_slugify.SlugifyCLITests.test_empty_and_no_alphanumeric_input) ... ok\ntest_extra_argument_exits_two (test_slugify.SlugifyCLITests.test_extra_argument_exits_two) ... ok\ntest_missing_argument_exits_two (test_slugify.SlugifyCLITests.test_missing_argument_exits_two) ... ok\ntest_punctuation_case_and_digits (test_slugify.SlugifyCLITests.test_punctuation_case_and_digits) ... ok\ntest_separator_runs_and_trimming (test_slugify.SlugifyCLITests.test_separator_runs_and_trimming) ... ok\ntest_text_starting_with_hyphens (test_slugify.SlugifyCLITests.test_text_starting_with_hyphens) ... ok\ntest_unicode_is_separator_without_transliteration (test_slugify.SlugifyCLITests.test_unicode_is_separator_without_transliteration) ... ok\n\n----------------------------------------------------------------------\nRan 7 tests in 0.213s\n\nOK\n", "exit": 0}
{"case": "ASCII", "argv": ["python3", "-B", "slugify.py", "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"], "stdout": "abcdefghijklmnopqrstuvwxyzabcdefghijklmnopqrstuvwxyz0123456789\n", "stderr": "", "exit": 0}
{"case": "runs", "argv": ["python3", "-B", "slugify.py", " --Hello___WORLD! 42--- "], "stdout": "hello-world-42\n", "stderr": "", "exit": 0}
{"case": "Unicode", "argv": ["python3", "-B", "slugify.py", "A\u0130\u212a\u017f\u0131B CAF\u00c9 \u6771\u4eac\ud83d\ude00\uff11\uff12\u0663"], "stdout": "a-b-caf\n", "stderr": "", "exit": 0}
{"case": "separators", "argv": ["python3", "-B", "slugify.py", " --_ /\t\n\ud83d\ude00"], "stdout": "\n", "stderr": "", "exit": 0}
{"case": "empty", "argv": ["python3", "-B", "slugify.py", ""], "stdout": "\n", "stderr": "", "exit": 0}
{"case": "controls", "argv": ["python3", "-B", "slugify.py", "A\t\n\rB"], "stdout": "a-b\n", "stderr": "", "exit": 0}
{"case": "hyphen text", "argv": ["python3", "-B", "slugify.py", "--HELLO"], "stdout": "hello\n", "stderr": "", "exit": 0}
{"case": "missing", "argv": ["python3", "-B", "slugify.py"], "stdout": "", "stderr": "usage: python3 slugify.py TEXT\n", "exit": 2}
{"case": "extra", "argv": ["python3", "-B", "slugify.py", "a", "b"], "stdout": "", "stderr": "usage: python3 slugify.py TEXT\n", "exit": 2}
Independent CLI assertions: 9 passed
```
Native command exit: 0.

Result: 7 existing tests passed; 9 independently asserted CLI cases passed. Missing and extra arguments produced expected exit 2, not test failures.

## Exact HEAD and file verification after tests

Exact native command:
```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B -c 'import hashlib, json, pathlib, subprocess
head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True)
print(json.dumps({"argv": ["git", "rev-parse", "HEAD"], "stdout": head.stdout, "stderr": head.stderr, "exit": head.returncode}))
assert head.returncode == 0 and head.stdout.strip() == "32746b7d72bbbb4263c2ecf8a737c1c1613f9bbe"
for name in ["slugify.py", "test_slugify.py", "README.md"]:
    argv = ["git", "show", "32746b7d72bbbb4263c2ecf8a737c1c1613f9bbe:" + name]
    p = subprocess.run(argv, capture_output=True)
    actual = pathlib.Path(name).read_bytes()
    print(json.dumps({"argv": argv, "stdout": p.stdout.decode(), "stderr": p.stderr.decode(), "exit": p.returncode, "working_file_matches_HEAD": actual == p.stdout, "sha256": hashlib.sha256(actual).hexdigest()}))
    assert p.returncode == 0 and actual == p.stdout
'
```

Complete captured output:
```text
{"argv": ["git", "rev-parse", "HEAD"], "stdout": "32746b7d72bbbb4263c2ecf8a737c1c1613f9bbe\n", "stderr": "git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead\ngit: error: couldn't create cache file '/tmp/xcrun_db-BcdNnKjo' (errno=Operation not permitted)\n", "exit": 0}
{"argv": ["git", "show", "32746b7d72bbbb4263c2ecf8a737c1c1613f9bbe:slugify.py"], "stdout": "\"\"\"Convert one text argument to an ASCII slug.\"\"\"\n\nimport re\nimport sys\n\n\ndef slugify(text):\n    \"\"\"Replace non-ASCII-alphanumeric runs with hyphens.\"\"\"\n    return re.sub(r\"[^A-Za-z0-9]+\", \"-\", text).strip(\"-\").lower()\n\n\ndef main():\n    if len(sys.argv) != 2:\n        print(\"usage: python3 slugify.py TEXT\", file=sys.stderr)\n        return 2\n    print(slugify(sys.argv[1]))\n    return 0\n\n\nif __name__ == \"__main__\":\n    sys.exit(main())\n", "stderr": "git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead\ngit: error: couldn't create cache file '/tmp/xcrun_db-mMhUnSGj' (errno=Operation not permitted)\n", "exit": 0, "working_file_matches_HEAD": true, "sha256": "93123e73e2362ca8b1f60cb26d71294164e0da629cee29e77b6290b10336d57a"}
{"argv": ["git", "show", "32746b7d72bbbb4263c2ecf8a737c1c1613f9bbe:test_slugify.py"], "stdout": "\"\"\"Exercise the public CLI, including its output and exit status.\"\"\"\n\nfrom pathlib import Path\nimport subprocess\nimport sys\nimport unittest\n\n\nSCRIPT = Path(__file__).with_name(\"slugify.py\")\n\n\nclass SlugifyCLITests(unittest.TestCase):\n    def run_cli(self, *args):\n        return subprocess.run(\n            [sys.executable, str(SCRIPT), *args],\n            capture_output=True,\n            text=True,\n            check=False,\n        )\n\n    def assert_slug(self, text, expected):\n        result = self.run_cli(text)\n        self.assertEqual(result.returncode, 0, result.stderr)\n        self.assertEqual(result.stdout, expected + \"\\n\")\n        self.assertEqual(result.stderr, \"\")\n\n    def test_punctuation_case_and_digits(self):\n        self.assert_slug(\"Hello, WORLD! Version 42\", \"hello-world-version-42\")\n\n    def test_separator_runs_and_trimming(self):\n        self.assert_slug(\" --Alpha__ /\\t\\nBeta---99!!! \", \"alpha-beta-99\")\n\n    def test_empty_and_no_alphanumeric_input(self):\n        for text in (\"\", \"!!!\", \" --_ /\\t\\n\"):\n            with self.subTest(text=text):\n                self.assert_slug(text, \"\")\n\n    def test_unicode_is_separator_without_transliteration(self):\n        for text, expected in (\n            (\"CAF\u00c9 d\u00e9j\u00e0\u2014VU\", \"caf-d-j-vu\"),\n            (\"A\u0130\u212a\u017f\u0131B\", \"a-b\"),\n            (\"\u6771\u4eac\ud83d\ude00\", \"\"),\n            (\"A\uff11\uff12\u0663B\", \"a-b\"),\n        ):\n            with self.subTest(text=text):\n                self.assert_slug(text, expected)\n\n    def test_text_starting_with_hyphens(self):\n        self.assert_slug(\"--HELLO\", \"hello\")\n\n    def test_missing_argument_exits_two(self):\n        result = self.run_cli()\n        self.assertEqual(result.returncode, 2)\n        self.assertEqual(result.stdout, \"\")\n        self.assertIn(\"usage:\", result.stderr)\n\n    def test_extra_argument_exits_two(self):\n        result = self.run_cli(\"hello\", \"world\")\n        self.assertEqual(result.returncode, 2)\n        self.assertEqual(result.stdout, \"\")\n        self.assertIn(\"usage:\", result.stderr)\n\n\nif __name__ == \"__main__\":\n    unittest.main()\n", "stderr": "git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead\ngit: error: couldn't create cache file '/tmp/xcrun_db-Jcfklrno' (errno=Operation not permitted)\n", "exit": 0, "working_file_matches_HEAD": true, "sha256": "96a2e2143961da2b747d781e71ddfecd4fdb2f360f4876a3529bb83bc4bd9741"}
{"argv": ["git", "show", "32746b7d72bbbb4263c2ecf8a737c1c1613f9bbe:README.md"], "stdout": "# Slugify fixture\n\nImplement the operator-specified ASCII-only terminal slugifier.\n", "stderr": "git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead\ngit: error: couldn't create cache file '/tmp/xcrun_db-iTVzKw6t' (errno=Operation not permitted)\n", "exit": 0, "working_file_matches_HEAD": true, "sha256": "b33aa73a2daf1630bf8f7bef216161966c77f1b4f2e73ba8c698cfa2e2203d5b"}
```
Native command exit: 0.

## Surface observation

Host: local macOS (observed Darwin 27.0.0).
App: Python slugify CLI.
Mode: terminal subprocess.
Criterion: Given exactly one text argument, python3 slugify.py TEXT lowercases ASCII A-Z, converts each maximal run of characters outside ASCII [A-Za-z0-9] to one hyphen, trims edge hyphens and prints one newline with exit 0; all-separator input prints an empty line, and missing TEXT exits 2.

Observed criterion satisfied on this local host at the stated HEAD. Evidence does not establish hosted CI or human acceptance.
