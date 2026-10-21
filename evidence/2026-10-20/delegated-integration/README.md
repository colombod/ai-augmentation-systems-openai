# Delegated integration — 20 October 2026

Local package: `delivery` `0.1.0-preview.5`. No marketplace commit, push or
publication was performed. Package fingerprints are in `source-hashes.json`.

Three monitored agents owned runtime lifecycle, workflow gates and judge providers.
Root integrated operator capture and canonical artifact persistence, reviewed
agent changes, requested additional denial/recovery probes, and independently ran
the combined checks. Independent peer review exposed issues with approval
escalation, mutable judge configuration, writable coordinator source, lost
external-effect receipts, stale evidence and privileged Git fsmonitor execution;
the fixes and failed observations remain in the workstream evidence.
Final peer review additionally reproduced caller-supplied internal Git-policy
injection without launching a widened worker; raw roster/persisted specifications now reject reserved fields and independent
review confirms the reproduction is denied. Index-flag dirty-file hiding and
privileged clean-filter execution were also reproduced and fixed. Gate checks
now hash raw tracked bytes/modes against HEAD, compare only staged index data
and enumerate untracked files without `git status` or repository filters.
Transformed checkouts and submodules fail closed pending a safe adapter.
An independent final fixture confirmed both index flag bypasses are denied and a
configured clean-filter marker remains unexecuted during successful inspection;
see `../provider-completion/git-index-final-readonly-review.json`.

## Independently run checks

- `python-tests.txt`: **102/102** Python tests passed using declared development
  dependencies. Includes 36 core, 35 gates, 10 artifact and 8 capture tests plus
  package/helper checks. Stub/protocol tests do not prove host acceptance.
- `node-tests.txt`: **22/22** local fake-provider tests passed. Loopback sockets
  required normal sandbox escalation for this test fixture; no real provider
  requests are made by these unit tests.
- Marketplace validator passed for one published catalogue entry (validator
  terminology; this is not a new publication).
- `install-probe.json`: isolated Codex CLI 0.159.3 installation passed, all 15
  qualified skills discovered, helper ran, assessment excluded, lineage present;
  zero model calls. This does not prove ordinary end-to-end skill activation.
- `git diff --check` passed.

## Separate live observations

- [Runtime core](../runtime-core/README.md): actual native same-thread restart
  and peer tool use; production `native-git-production-v4.json` establishes
  opted-in independent-clone staging/commit, local temporary files and denied
  planning/config/hooks/packed-refs/coordinator writes. Earlier failures and
  native platform warnings remain preserved. No shared-worktree commit support.
- [Provider bridge](../provider-completion/native-bridge-README.md): real Codex
  `delivery_judge` invocation once per explicitly selected Jev/OpenAI provider;
  results remain advisory with no human authority. Manually seeded temporary
  fixture is declared; this is not full prepare/team acceptance.
- [Workflow gates](../workflow-gates/README.md): synthetic local Beads/Git and
  OS-terminal roundtrip, idempotent materialization and recovery, with failed
  fsmonitor reproduction retained and execution denied after the fix.

OS-terminal capture tests use synthetic input, not verified human identity.
Surface/CI/conflict assertions are operator-attested, not independently fetched
or GUI-authenticated. No complete autonomous delivery/release cycle, desktop UI,
ChatGPT runtime, automatic merge, push or deployment acceptance is established.
Those remain required scope tracked in Beads rather than silently discarded.
