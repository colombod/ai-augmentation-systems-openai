# Delivery port assessment

## Source baseline

- Repository: [colombod/ai-augmentation-systems](https://github.com/colombod/ai-augmentation-systems).
- Revision: `df0c0a5b0dba1449b6cdfef421bfe1ebc4d658c0`.
- Package: `plugins/delivery`, version `0.30.0`.
- Inventory: 23 skill entry points including aliases, eight persistent role briefs,
  eleven reviewer personas, 25 templates and 56 test files.
- Unchanged-source test run: 932 passed, zero failed on Node 26.5.0. Upstream CI
  specifies Node 24. Local suite success is not live Claude or OpenAI acceptance.

## Operating model to preserve

Persistent Chief of Staff, Product Manager, Delivery Manager and builder sessions
coordinate through messages and Beads. Reviewer personas are temporary lenses;
they are not substitutes for those persistent sessions. Builders have product
worktrees; plans and operator records stay in the private project repository.

Role setup writes `.claude/settings.local.json`, native allow/deny rules,
environment identity, `.delivery-role.json` and `CLAUDE.local.md`. Session hooks
refresh instructions and liveness. These form one runtime system: copying only
skill prose or renaming tools does not preserve its guarantees.

## Port boundaries

| Component | Reuse candidate | Required adaptation |
|---|---|---|
| Templates, artifact conventions and planning workflow | Content and artifact structure | Skill metadata, invocation, file access and reviewer dispatch |
| Lanes and leak guard | Rules and parser tests | Canonical OpenAI tool payloads, patch targets, native permission backstops and new tool paths |
| Operator ledger | Chaining, verification and publication concepts | Human/peer/system capture, question-answer binding and runtime identity |
| Goal changes | Authority and single-use checks | Exact OpenAI question/answer provenance; never synthesize a human approval |
| Readiness/completion gates | Criteria hashes, evidence and surface comparison | Trusted role context and enforcement on all supported task mutations |
| PR review and merging | Head-bound independent review rules | Reviewer identities and guarded merge routes |
| Invocation ledger | Whitelisted events and artifact content hashes | Actual tool outcomes, multi-file patches and capture tool evidence |
| Usage, budgets and watchdog | Selection/reserve concepts | Provider usage units, quota signals, session listing/resume/fork and host jobs |
| Judge | Nine-question catalogue and normalized result contract | Explicit Jev/OpenAI/disabled selection, endpoint/key policy, schemas, refusals, latency and recalibration |

The source contains legacy warn-only paths. A never-ready legacy story does not
receive the same hard gate as a story with recorded criteria. Claims about the
port must distinguish actual enforcement, warnings and conventions.

## Reproduced compatibility differences

The unchanged lane function allowed a Claude `Write` to a permitted product
path, but rejected a representative Codex `apply_patch` for the same path with
an unrelated watchdog refusal. This was a pure function probe, not a live harness.

The invocation recorder filters exact `Skill`/`Agent` names and known capture
tools. `spawn_agent` was not recognized as a governed invocation. Matching an
OpenAI hook alias therefore does not normalize the input consumed by the code.

The transcript parser expects Claude records and origin stamps. Goal changes
additionally bind the answer to the exact question/options, reject expired or
reused answers and check revocation. OpenAI Decisions cannot replace this capture.

## Judge providers

Jev is optional. Its classifications can contribute to relay/message blocking,
while readiness/divergence questions are advisory or warn-only. Preserve each
question's actual mode. OpenAI predicates map to probability results and choices
map to declared options; response shapes differ. Existing Jev thresholds do not
establish equivalent OpenAI calibration. No silent cross-provider fallback.

## Repository decision

Develop the OpenAI port here, with independent packages, tests and releases.
Keep the Claude marketplace unchanged. Import only deliberate components with a
pinned upstream revision, licence and per-file attribution. Do not make the
OpenAI package depend at runtime on an unpinned Claude marketplace checkout.

Shared-library extraction is a later decision, requiring evidence and a separate
review of its effect on Claude. The cost of this isolation is deliberate upstream
change review and maintenance of provenance for copied/adapted files.

## Acceptance boundary

Before shipping the team, demonstrate independently in CLI and desktop:
role startup and recovery; allowed and forbidden actions; human-versus-peer
decision capture; exact question binding; decisions surviving restart; no
self-review/self-acceptance; review invalidation after new commits; and evidence
bound to the agreed criteria and deployed customer surface. ChatGPT requires its
own execution/distribution validation. The open work is tracked in Beads.
