# Explicit command evidence

`scripts/verification.py` creates a new JSON evidence file containing the command
argument array, stdout/stderr, exit code, timeout, duration and computed result.
Outputs above 256 KiB per stream are marked truncated and fail closed. Missing
executables and nonzero exits are unsuccessful observations. Existing files are
never overwritten. Supply the actual project test command; no language runner
or test success is guessed.

Run commands only with existing authorization and inside the caller's permitted
lane. This helper adds no runtime tool or permission. A scratch clone is process
and workspace separation, not a security sandbox for untrusted code. Commands
inherit the caller's environment except role/Beads and Git redirection variables;
they can still access anything the existing execution environment permits.

## Independent exact-commit review

```sh
python3 <package>/scripts/verification.py review --directory <authorized-local-product> --head <full-commit-sha> --command-json '["python3","-B","-m","unittest","discover"]' --output <reviewer-evidence>/review-unique.json
```

Review makes a fresh independent local clone without hardlinks, checks out the
exact full SHA and runs the explicit command. It never resets or cleans the
builder checkout and performs no remote fetch. Full SHA and raw tracked bytes
and executable modes are checked before and after; index hiding flags, staged
changes and unsupported submodules fail closed. Untracked test outputs are
allowed in the temporary clone. The clone is deleted after the run. There is no
reuse of a previous scratch workspace or destructive clean operation.

Use a separately bound reviewer role and submit this file through the existing
review evidence path. A successful command is evidence of that command, not an
independent review judgment or proof that every acceptance criterion is met.

## Revision-bound command surface verification

```sh
python3 <package>/scripts/verification.py verify --directory <authorized-surface-directory> --head <expected-deployed-full-sha> --criterion "Criterion A" --revision-command-json '["path-to-authorized-version-query"]' --command-json '["path-to-authorized-surface-check"]' --contains 'expected output' --output <reviewer-evidence>/surface-unique.json
```

The explicit version query must return exactly the observed deployed full SHA.
The helper runs it before and after the criterion command. A mismatch refuses
or fails the check; the agent does not supply a passed flag. Exit zero, no timeout
or truncation, matching observed revision, and the optional literal stdout match
are all required. The query must actually observe the intended deployed surface;
querying a local checkout only proves a local checkout revision. This helper
cannot authenticate a deployment, browser observation or operator assertion.

Attach the saved file to the existing controlled review/surface submission. Those
gates retain exact task/head/evidence hashes, independent native identities and
operator-owned acceptance. These files are submissions, not signed operator
receipts; this helper does not turn CI/host attestation into automatic acceptance.
Preserve failed runs alongside later evidence. CLI exits 0 for computed pass,
1 for a recorded failed check, and 2 for invalid invocation/storage failure.
