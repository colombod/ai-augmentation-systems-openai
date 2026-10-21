# Delivery failure fixes — 20 October 2026

**The observed failures are fixed and a fresh real CLI scenario passed without
corrective steering, revocation, a continuation run or permission expansion.**
Local package version: `0.1.0-preview.6`, unreleased.

## Changes

- Judge test input now comes from the actual catalogue fields. The driver requires
  one real answer from the selected provider/model; a skipped/error response
  cannot count as provider success.
- Assignment completion requires the exact queued native user message, bound
  thread/turn and matching completed terminal. Prior idle states, old terminals
  and earlier tool results cannot satisfy a new assignment.
- Builders receive the supported staged-index Git workflow and Python cache
  guidance. Unsupported pathspec commits remain unsupported; permissions were
  not broadened.
- Forbidden native command/file approvals receive an immediate offered decline
  or cancel, with no pending terminal prompt or signing operation. Actual native
  cancellation remains an interrupted turn, not completed work.
- Intentional supervisor interruption exits cleanly with an explicit interrupted
  status. Operational errors retain failure status. The driver rejects crashes,
  forced cleanup, false checks and missing evidence instead of masking them.

## Verification

- [121/121 Python regression tests](python-tests.txt) passed. These include runtime
  protocol/entrypoint checks and adversarial driver synchronization, judge and
  shutdown tests.
- [Isolated CLI installation](install-probe.json) found all 15 skills, ran the
  helper, preserved attribution and excluded maintainer assessment material.
- [Real native denial probe](runtime/native-denial-result.json): all six checks
  passed, protected file preserved, no pending operator prompt/capture, actual
  interrupted terminal observed.
- [Actual idle CLI shutdown](runtime/cli-interrupt-result.json): all five checks
  passed, clean exit, no model calls or claimed work.
- [Fresh real delivery run](../full-cli-cycle/attempts/20261020T222729Z-f07ae57ef33c431694ddb9e16cf5d084/result.json):
  five real Codex roles used public CLI preparation, peer handoff, canonical
  artifact saves, real Beads materialization/readiness/claim, implementation,
  independent read-only review and CLI surface observations. A planned restart
  completed a new PM assignment on its original thread, retaining its goal/path
  context. The first configured OpenAI judge call succeeded. All **16** workflow
  checks passed; the driver and both supervisor stops exited **0**.
- [Root black-box checks](fresh-black-box-results.json): **21/21** passed against
  committed source without modifying it. Actual product commit:
  `b87785b9a8f2f3fc3cd532f683a8228619245b08`.
- [Root process/source verification](fresh-run-verification.json) confirms source
  fingerprints stayed unchanged through the run, the grade matches the committed
  file, and no forced cleanup occurred.

The fresh run took **390.8 seconds** including setup and its planned restart.
This is one observation, not a reliability estimate or controlled performance
comparison. The planned phase assignments are scripted; this does not establish
one-prompt autonomous delivery or ordinary qualified-plugin activation.

Separate read-only audits passed [18/18 evidence checks](fresh-independent-audit/README.md)
and [13/13 native gate checks](../full-cli-cycle/attempts/20261020T222729Z-f07ae57ef33c431694ddb9e16cf5d084/independent-native-gates-audit.json).
The fresh generated product used three parameterized unittest methods; counts
from the earlier seven-method fixture are not reused for this attempt.

## Approval and remaining scope

Final submissions were complete, but protected acceptance correctly refused
without an operator terminal receipt. The canonical fixture task remains
`in_progress`, `accepted=false`. No human approval or hosted CI result was
fabricated. Desktop, ChatGPT, real human acceptance and merge/deployment remain
separate required validation/work.

The [earlier failed/attended run](../full-cli-cycle/README.md), its raw failure
results, native lock-denial observations and continuation are preserved.
Fresh attempts use unique folders and retain their exact driver/helper snapshots.
These are maintainer-only records, outside the installable package. No credentials
or personal Codex configuration were copied. No marketplace commit, push or
publication occurred.

Committed product and canonical draft/review copies are retained in
`product-snapshot/` and `canonical-artifact-snapshot/`, bound by
[artifact hashes](artifact-snapshot-manifest.json); Git/Beads/native-home stores
were not copied.
