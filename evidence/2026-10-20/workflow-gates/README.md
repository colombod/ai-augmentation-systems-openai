# Controlled workflow gates: 20 October 2026

Implemented package module: `plugins/delivery/scripts/delivery_gates.py`.
Deterministic checks use canonical Beads task status, assignee, criteria and
blocking dependencies. Runtime events contain append-only evidence and native
role/thread/turn bindings, not another mutable task-status database.

## Checks and actual observations

- `unit-tests.txt`: 35 deterministic tests pass against real temporary Git
  worktrees and the runtime event store. The Beads dependency/state adapter is
  explicitly a fake in these tests, supporting reproducible adversarial races.
- `beads-claim-probe.json`: an isolated actual Beads database confirms that
  `bd update --claim --actor <bound role>` assigns the canonical task to that role.
- `live-beads-roundtrip.json` and `live-roundtrip-output.txt`: the fixture runner
  uses actual Beads and Git plus a real operating-system PTY and CaptureAuthority
  to exercise protected story save, idempotent draft materialization, ready, claim, implementation, independent review, surface submission
  and non-forced Beads close. Source hashes identify the modules loaded at launch.
  Initial successful runs remain under the `initial` and `before-provenance` names.
- PTY input is automated synthetic text. This establishes client/receipt plumbing;
  it is not evidence of a physical person approving real product work. CI and
  surface text are synthetic fixtures. No native model, desktop or ChatGPT was
  invoked by these gate fixtures.

Tests reject changed criteria/dependencies, moved commits, tracked dirty files,
untracked product inputs, actor spoofing, stale turns, self-review, failed tests,
wrong host/stub observations, changed evidence, reassigned tasks, forged or declined
operator receipts and incomplete canonical criterion coverage. An explicit
`task_reready` with reconciliation reason can preserve a canonical claim only
when its original bound builder is quiescent; previous evidence becomes invalid.

Independent read-only reviewers can reference coordinator-protected
`.delivery/reviews/*.md` artifacts outside their worktree only when the latest
`artifact_saved` event binds the same native author role and persistent thread to
the exact file hash. Origin turn is preserved; a later resumed turn of that same
thread may submit it. Different author/thread and changed artifact provenance
are refused. Such notes remain submissions, not authenticated host observations.

## Operator-attested acceptance boundary

`delivery_task_accept` prepares a complete exact attestation question. All
builders must be confirmed idle/prepared. The question includes current head,
criteria, readiness, implementation/review and actual surface references, and
explicitly asks the operator to verify passing CI, conflicts and real host
observations. A trusted coordinator path, never a model signer tool, captures
`delivery/gateAcceptance` through CaptureAuthority and invokes
`GateService.accept_from_operator`. It rechecks state after the wait and consumes
one expiring, exact-binding receipt before non-forced `bd close`.

This is operator-attested CI/host evidence, not machine-authenticated CI or
external-person identity. It authorizes only canonical task close. It never
merges, pushes or publishes. Local coordinator transactions serialize controlled
commands; Beads atomically owns claim, but Git + dependency + close is not one
global transaction. Unrelated user-run Beads/Git clients remain outside that
boundary. Ignored dependencies and dedicated `.delivery-evidence/` outputs are
not claimed to be immutable committed product inputs. An external concurrent
edit or repository/tool bypass is not prevented by these checks.

## Preserved failed observation

The first expanded PTY unit-test attempt blocked while writing the full operator
question into the terminal output buffer. It was interrupted (exit 130). The
fixture now drains terminal output concurrently; all PTY tests then pass. This
was a test-harness plumbing failure, not operator acceptance or a native runtime
failure. The raw interrupted traceback is retained in the chat tool transcript;
this note records its diagnosis without inventing a separate raw capture.

## Durable Beads effects and story materialization

Claim and acceptance now persist an intent before invoking Beads. Claim records an
operation marker in canonical notes; acceptance records an exact operation marker
in canonical close_reason, plus the protected intent's full scope/question and
verified operator receipt hash. If local outcome recording rolls back after the
Beads effect, `GateService.reconcile_effects()` reads canonical status and exact
markers. It never replays a claim or close. Unknown outcomes require explicit
operator reconciliation and block automatic retries. Tests simulate successful
external claim/close followed by local event failure, restart the service, and
prove one effect call plus read-only recovery. These are operation journals, not
another mutable task-status database.

`delivery_task_materialize` lets only the bound delivery manager create a draft
Beads task from a coordinator-protected canonical `stories/<name>.md`. It reads
one concrete H1 and the Acceptance criteria section, preserves exact canonical
body bytes as the task description, and stores source path/hash metadata with a
stable external reference. Repeated calls reuse the same source mapping only while canonical title, acceptance criteria and description still match the parsed story; changed
sources require an explicit canonical task revision rather than duplicate tasks.
A durable creation intent prevents blind retry after an ambiguous response. No
readiness, ownership or consent is inferred from draft creation. Other roles,
raw/unprotected stories and template placeholders are refused.

Final fidelity review added explicit refusal when an existing canonical task title or acceptance criteria diverges from unchanged source bytes. This prevents silent reuse after external task edits and requires explicit realignment; it never creates a duplicate or overwrites those edits.

## Coordinator Git inspection hardening

`fsmonitor-probe.json` reproduces a repository-configured tracked fsmonitor
helper writing a safe marker during ordinary `git status`. Inspection with the
per-command `core.fsmonitor=false` setting does not execute it. GateService.head
now uses that setting plus `--no-optional-locks` for its Git read commands. The
regression exercises actual Git and proves the external safe marker stays absent
and repository configuration remains unchanged. No commit hook, native permission
or trust setting is modified. Gate inspection uses `rev-parse`, `ls-tree`, `ls-files` and cached
`diff-index` with external diff/textconv disabled; it uses no remote, checkout,
commit or worktree filter conversion command. Beads creation uses argv and stdin, never a shell-expanded body.

`final-source-sha256.json` identifies the final files tested by the unit suite.
The earlier full Beads/PTY roundtrip retains its own launch-time source hashes;
it is not presented as a rerun after this separate Git-inspection regression.

## Index-independent committed-byte integrity

`index-hiding-before.json` records actual dirty tracked bytes hidden by both
assume-unchanged and skip-worktree; the old gate returned the original head.
The final gate rejects these index flags and independently reads `ls-tree` blob
IDs from HEAD, comparing raw bytes with Python's Git-blob framing/hash. Reads use
at most 1 MiB chunks and exactly the file's initial length plus one growth check;
file type, executable mode, growth/shrink and metadata changes are checked.
Intermediate symlinks are refused; tracked leaf symlinks are compared by their
link-target bytes without following them. Transformed clean-filter/CRLF checkouts
and unverified submodules fail closed rather than running a repository adapter.

A first intermediate implementation retained Git status after raw hashing; its
safe-marker regression proved status itself could run a configured clean filter.
`index-filter-prefinal-observation.json` records that failed observation from the
tool transcript. Final inspection has no status command. Staged changes use only
cached `diff-index --quiet --no-ext-diff --no-textconv`; untracked inputs use
`ls-files --others --exclude-standard`. Per-command fsmonitor and untrackedCache
are disabled. Tests include same-size/old-mtime cache-stat concealment, staged
extra files, mode changes, parent symlinks and a configured clean/smudge helper
whose external safe marker must remain absent.
