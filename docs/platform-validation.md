# Platform validation — 19 October 2026

## Scope

Codex CLI and the Codex desktop app are required targets. ChatGPT remains a
separate target from the original request. This record validates selected
mechanisms, not delivery implementation or feature parity.

The revised native design separates server-free planning from optional runtime
extensions. The historical hook findings below remain unchanged; they block
claims about hook enforcement, not the skills-only workflow. ChatGPT's packaged
instruction path and its optional custom MCP service path need separate tests.
See [the canonical design](delivery-port-assessment.md) for deployment choices.

## Observed results

| Mechanism | Evidence | Result |
|---|---|---|
| Marketplace registration and plugin installation | Installed isolated fixture with CLI 0.159.3 | Passed |
| Skill discovery | `skills/list` returned `mechanism-probe:probe` with plugin identity | Passed |
| Root portable manifest hooks | Initial installed fixture yielded no hooks in `hooks/list` | Unresolved; preserve observation, do not assume platform defect |
| Compatibility manifest hooks | Clean reinstall using `.codex-plugin/plugin.json` returned four hooks with source `plugin` and untrusted status | Discovery passed |
| Bundled hook execution | Stub-backed CLI run did not append lifecycle events for its thread | Not confirmed; blocks advertising hook-dependent enforcement |
| User configuration hook execution | Isolated `hooks.json`; vetted per-invocation trust bypass; loopback SSE stub | SessionStart, UserPromptSubmit, Stop and SessionEnd observed |
| Persistent session creation | `thread/start` and `thread/read` | Passed |
| Resume/fork before a first turn | No persisted rollout yet | Rejected with `no rollout found`; do not treat an unused thread as recoverable |
| Resume/fork after a completed stub turn | App-server calls against persisted CLI thread | Passed |
| Desktop installation and UI | App 26.1013.40934, build 20770; tool rejects `com.openai.codex` for safety reasons | Blocked; not accepted |
| Real model and multi-role behaviour | Initial mechanism probes invoked no live model; separate live planning tests are recorded below | Multi-role runtime not tested |
| Tool denial, question provenance and independent evidence | Requires port adapters and live tests | Not tested |

The loopback stub proves transport/lifecycle plumbing only. It supplies a fixed
answer and synthetic usage. It does not establish model quality, real spending,
role autonomy, operator provenance or recovery after actual model/tool failure.

All probe installations and configuration writes used a temporary Codex data
directory. Personal Codex settings and credentials were not copied or modified.
The per-invocation hook bypass was limited to reviewed fixture scripts; it is not
a proposed user installation method or evidence of persisted trust review.

## Distribution boundaries

The official packaging guide describes repository catalogues for supported local
clients, including CLI and desktop. The migration guide requires removing lifecycle
hooks for public directory submissions and points hook-dependent plugins toward
manual local installation. Cloud orchestration restricts local/plugin hooks.
Local Codex acceptance does not establish ChatGPT web or cloud acceptance.

## Evidence and reproduction

Machine-readable results and retained fixture scripts are under
[`evidence/2026-10-19`](../evidence/2026-10-19/). The reproduction scripts describe
the experiment, not a turnkey acceptance suite: they assume a disposable fixture,
isolated configuration and, for protocol resume, an existing probe thread.
The initial mechanism probes ran no real-model acceptance tests. The later
targeted planning tests below are separate evidence.

## Targeted live planning behavior — 20 October 2026

On CLI 0.159.3, three live model scenarios passed manual criterion review:
status with no artifacts/access, a brief without delegation/save access, and
simulated interviews without workers. The first interview was partially
successful but suggested a remedy in a follow-up; the skill was corrected and
that scenario alone was rerun successfully. Initial outputs, event traces,
source hashes and the assessment are retained in
[`live-behavior`](../evidence/2026-10-20/live-behavior/README.md).

The runs were ephemeral, ignored user configuration and used read-only temporary
workspaces. Capabilities were restricted in the prompt, and traces showed only
agent messages. Skill resources were supplied inline. This is real model behavior
evidence, not installed-plugin activation or desktop/ChatGPT acceptance. The
implementation session graded the outcomes; no independent grader was used.

The bundled hook discovery/execution difference and desktop access restriction
remain tracked in Beads. Neither is waived by creating this marketplace.

## Sources checked

- [Plugin packaging](https://developers.openai.com/plugins/build/plugins)
- [Claude plugin migration](https://developers.openai.com/plugins/guides/submit-claude-plugin)
- [Codex hooks](https://learn.chatgpt.com/docs/hooks)
- [Codex app-server](https://learn.chatgpt.com/docs/app-server)
- [CLI reference](https://learn.chatgpt.com/docs/cli/reference)

These are documentation claims as checked on this date, not a guarantee that
every installed client release implements every documented behaviour.

## Package review and native selected-skill benchmark — 20 October 2026

The `0.1.0-preview.4` package passed portable schema/catalogue validation, all 13
package/helper tests, and a fresh isolated install/discovery probe of all 15
qualified skills on CLI 0.159.3. Plugin Eval analyzed each skill; its root plugin
detector does not recognize the portable manifest, so its generic root score is
not a plugin acceptance result.

Three real-model cases used structured native skill inputs pointing to an
isolated installed package, exposed through temporary workspace skill aliases.
Start created planning directories in 26.01 seconds; brief saved a verified
547-prose-word document and glossary in 121.36 seconds; status reported missing
evidence in 42.00 seconds with file hashes unchanged. All passed the stated
checks, assessed by the implementation session. Model metadata identifies
`gpt-6.1-sol`, default service tier, medium reasoning. No credentials or personal
configuration were copied; native model calls used existing host configuration
and sign-in. No sandbox or approval bypass was used.

These tests establish selected installed-resource behavior, not end-to-end
qualified plugin selection in an ordinary user session: the aliases have
repository scope and `pluginId: null`. A separate probe establishes qualified
plugin discovery. The initial CLI setup lacked active-home installation and
fell back to finding package files; it is retained rather than counted as clean
activation. Desktop, ChatGPT and the full autonomous runtime remain unaccepted.
See the [review, usage measurements and limitations](../evidence/2026-10-20/plugin-benchmark/README.md).

## Runtime implementation probes — 20 October 2026

The local coordinator now implements durable role/thread bindings, queued work,
native session start/resume, conservative interruption/recovery, expiring native
operator requests, bound peer messaging and read-only Beads access. A real
read-only Codex thread completed a synthetic turn, survived coordinator restart,
and completed another turn under the same thread ID. A real builder shell write
probe preserved a planning file while successfully writing inside its product
worktree. An earlier here-document setup failure is retained and not counted as
a permission pass. These are targeted prototype observations, not whole-team
or protected-workflow acceptance.

Explicit Jev/OpenAI judge adapters are implemented. One synthetic `is_fix` smoke
call per selected provider succeeded with `jev-1.13.0` and `gpt-6-luna`. All
classification results remain advisory and carry no human authority. These calls
are not provider calibration or authorization tests. See
[runtime implementation evidence](../evidence/2026-10-20/runtime-implementation/README.md).

## Delegated integration — 20 October 2026

Three monitored workstreams completed provider integration, workflow gates and
native runtime hardening. Root integration independently passed 102 Python tests,
22 Node judge tests, portable marketplace validation and isolated installation
with all 15 qualified skills on Codex CLI 0.159.3 for `0.1.0-preview.5`.

Real model probes establish persistent native tool use across restart, explicit
Jev/OpenAI judge bridges, and default-Git staging/commit in an opted-in independent
builder clone. Protected planning/config/hooks/coordinator paths remained denied.
Failed probes and native warnings remain in their original evidence folders.

Terminal receipt tests use actual OS PTYs with synthetic input. Beads acceptance
uses operator-attested CI/conflict/surface observations. Neither proves a real
human identity, desktop UI acceptance, ChatGPT acceptance or a full autonomous
release cycle. No marketplace changes were committed, pushed or published.
See [integrated results](../evidence/2026-10-20/delegated-integration/README.md).

## Full public-CLI runtime cycle — 20 October 2026

An attended synthetic product scenario exercised public `prepare`, `send`,
`status`, `serve`, `revoke` and exact-turn `steer`, with five real `gpt-6.1-sol`
roles, a coordinator-to-product-manager peer handoff, canonical plan/story saves,
real Beads materialization/readiness/claim, a native builder commit, independent
read-only review and actual local CLI surface observations. A coordinator restart
resumed the original product-manager thread and completed a new queued turn.
Explicit OpenAI judging succeeded after an incomplete test-input refusal; no
fallback or authority grant occurred.

The product commit is `32746b7d72bbbb4263c2ecf8a737c1c1613f9bbe`. Seven builder
tests, seven reviewer tests and nine reviewer CLI cases passed. Root's separate,
prewritten black-box grader passed 21 cases against the committed source without
modifying product files. Reviewer output blocks match native command outputs.

This was an attended run with preserved interventions. A pathspec commit was
blocked by an unsupported temporary index lock; its escalation request was
revoked and the builder was steered to the supported staged-index commit. The
original harness then failed a reused-role idle-state race at its final step. A
public-CLI continuation consumed the existing never-started queued message with
exact queue/turn completion proof; it did not resend work or edit the database.
Final gate submissions were complete, acceptance was refused without an operator
capture channel, and the canonical task remained in progress. All supervisors
were stopped. Builder instructions/documentation were clarified afterward,
without broadening permissions.

This proves an attended local runtime cycle through the human barrier, not
autonomous one-prompt delivery, ordinary qualified-plugin activation, hosted CI,
real human acceptance, desktop UI, ChatGPT or merge/deployment. The initial
harness failure remains a failed observation rather than being rewritten as a
pass. See [full evidence](../evidence/2026-10-20/full-cli-cycle/README.md).

## Failure remediation and clean CLI rerun — 20 October 2026

Local preview `0.1.0-preview.6` corrects judge fixture fields, exact native-message
completion checks, immediate forbidden-approval denial and clean shutdown/error
reporting. All 121 Python regressions passed; isolated CLI discovery again found
15 skills. Actual denial and idle-shutdown probes passed without human input.

A fresh five-role real public-CLI cycle completed with all 16 checks true and
exit 0, without corrective steering, permission requests, revocation, forced
cleanup or continuation. The planned restart resumed the original PM context.
First-call OpenAI judging succeeded; actual implementation commit
`b87785b9a8f2f3fc3cd532f683a8228619245b08` passed independent read-only native
review and 21 separate black-box checks. Final acceptance remained blocked
without an operator receipt; the canonical task stayed in progress. Source
fingerprints stayed unchanged during the run. The original failed run is retained.

This is a scripted-phase CLI runtime test through the operator barrier, with
390.8 seconds observed wall time. Ordinary qualified-plugin activation, autonomous
one-prompt delivery, hosted CI, real human acceptance, desktop, ChatGPT and
merge/deployment remain separate. See [fixes and evidence](../evidence/2026-10-20/failure-fixes/README.md).
