# Delivery port assessment

## Release checklist — 30 October 2026

**Verdict: a scoped product/feature preview candidate is locally viable; full original-goal coverage is partial, not complete. Publication, merge and customer-host acceptance are not approved.**
This is the single current release checkpoint; the older design, observations and
contracts below remain history/context, not a newer readiness claim. The user
explicitly requested a repo-based checklist. Beads is unavailable here; this
updates the existing assessment rather than creating another task database.
Owners below are roles: **Maintainer** = implementing assistant; **QA** = independent
goal/scenario reviewer; **Owner** = user/release owner. No new service or remote action is commissioned by listing a next action.

**Priority and product unit.** Delivery is a top-priority enabling product for the
user to work with dot delivering projects. Start with customer, capability, current
versus planned state, value/evidence, owner intent and build/change/retire choices.
Code, tasks, skills and agents are supporting implementation detail. The preview
is an increment toward that full loop, not permission to stop at a skill collection.

**Delivery state.** Main remains preview.7. Branch-only drafting/loading/impact
and PR1 are combined locally, not delivered on main. The frozen unreleased
`0.1.0-preview.11` candidate is `f84a502fd57389b4c01bd4a20175d8448733c9ef`, on local
`delivery/coherent-preview` (intended same branch in the **private** remote).
The original integration at `edd036fbd96b60f58a3936766a2e712cbf18f502` passed
**185 Python / 22 Node / 16 discovered skills / 33 public helper commands**; this
is unshipped integration evidence, attributed to the implementation session.
[Input pins and raw integration checks](../evidence/2026-10-30/local-integration/README.md).
[Candidate instruction/resource smoke](../evidence/2026-10-30/preview11-smoke/summary.json)
adds 5 loading + 7 package checks, conditional greenfield reviewer/architecture/
story clauses, 16 installed skills, 12 resource hashes, version/provenance checks
and zero model calls. Old unconditional existing-file reviewer language is removed
in the selected integrated resources. No manager write permission was widened.

**Independent QA, separately attributed.** Parent supplied completed QA findings
at QA-local commit `db428b3e1f24a583110cd97f72f47f077e602c42` (not an object available
in this checkout). Both disposable greenfield/brownfield builds traversed product
framing → PRD/design → story/sprint → fresh-context implementation → independent
verification → realignment. Owner clarifications reached code; **8 green tests,
22 brown tests and 29 captured processes** passed. These are source-driven
builds, not delivered main features or native runtime acceptance. QA did **not**
independently access this combined artifact; its results do not substitute for
integrated installed-host qualification or measured token/latency evidence.

| Original goal | Main source versus branch-only | Local evidence / remaining gap | Owner → next useful action |
|---|---|---|---|
| Equal greenfield and brownfield entry | Main: shared product record and planned/no-code mode; compact drafting and remaining reviewer corrections branch-only. | Separate QA completed both source-driven journeys and fresh handoffs/resumption; combined helper paths pass. Not native autonomy. | Maintainer → preserve both paths in the self-development milestone and qualified preview. |
| Feature promises connected to code; freshness and pre-edit impact | Main: curated full-commit file anchors/raw-byte checks. Branch: optional Python import/initializer reach and shortest evidence chains. | Actual operator_capture.py change: zero direct matches, two dependency matches. Curated anchors, unresolved imports and unsupported consumers remain explicit; no complete semantic/deployed inventory. | Maintainer → consolidate tested direct/optional reach with honest coverage; do not promise automatic discovery. |
| Owner taste and what must survive | Main: attributed owner/proposed/unknown choices and preservation intent. | **Partial:** clarifications reached QA code, but historical baseline attribution failed and an architecture contradiction needed correction during that journey. Integrated conditional reviewer text now passes targeted smoke. | Maintainer + Owner → preserve exact statements versus interpretations in the Delivery-on-Delivery decision/handoff. |
| One customer, one proposition and explicit cuts before expansion | Main: product framing/brief/PRD contract; branch draft reduces repetitive input. | QA traversed framing to implementation; contract is not universal runtime enforcement. Draft cannot confirm choices or infer shipping. | Maintainer → make one customer/capability/value choice explicit before implementation, rather than completing documents for their own sake. |
| Job, First value, Fit, Outcome, Trust, Return; no total | Main: separate grade/evidence/next-check cards; draft preserves Unknown. | Grade/learning mechanics work; customer **Fit/Outcome/Return remain unknown**, and disposable builds are not outside-user adoption. | Owner + Maintainer → record a real first-use outcome and dated return check; no aggregate or promoted demo evidence. |
| Deliberate retirement; shared-code protection and user decision | Main: proposal-only direct analysis; branch adds partial dependency/initializer reach. | Proposals/shared retention work. Helper rejects active → retired: **complete retirement lifecycle is not implemented**. No absent-consumer or deletion proof. | Maintainer → advertise proposal-only scope; Owner decides a concrete retirement. A safe authorized transition is later work, not a bypass of the current guard. |
| Right Shape: smallest sufficient form, autonomy and engine | Main: separate form/engine/need/gates with conservative unknown caps. | Deterministic Right Shape worked locally in QA; no autonomous-agent or measured token-efficiency proof. | Maintainer → justify the smallest form for one real feature outcome; no new agent framework. |
| Guarded execution, evidence and durable handoff/recovery | Main: native mechanisms/gates; PR1: durable request receipts and exact-SHA command evidence. | Fresh-context handoffs/resumption worked in source-driven QA. **Persistent native coordinated execution remains unproved** on this candidate; fake transport is not human acceptance. | Maintainer + QA → qualify real bounded native execution only before advertising it; never infer merge/deploy authority. |
| Dot as optional chief of staff, retaining Delivery execution/state and human acceptance | Main: native runtime/gates. PR1 only: trusted in-process supervision, durable requests/receipts and verification helpers. | Combined regressions and exact-SHA scratch review pass, but no authenticated dot adapter or real dot completion. Native managers cannot write product-map.json; authorized host save remains required. | Maintainer + Owner → later choose one supported authenticated host boundary and prove one bounded handoff/receipt; do not block core preview on an unbuilt adapter. |
| Quality-preserving efficiency and reliable review | Branch: focused loading/common source rules; PR1 exact-SHA verification. | Combined deterministic checks pass. **Native-host acceptance and measured token efficiency are blocked/unproved**; no quality/performance win claimed from bytes. | QA + Maintainer → require actual host/usage receipts before those claims; source-driven success is not installed native execution. |
| One usable installable OpenAI Delivery version | Frozen local preview.11; original source branches/main unchanged. | Manifest/resources/provenance and targeted installed CLI smoke pass. No customer-host update, desktop/ChatGPT acceptance or delivered unified release. | Maintainer + Owner → complete the self-development milestone, then seek exact private publication authorization and CI/review. |

### Preview gate and shortest shipping route

A useful **explicitly scoped preview** can deliver both product journeys, owner/
customer/cut context, curated mapping with optional Python reach, separate usefulness
and safe retirement proposals. Optional native/dot features stay off/experimental
unless independently accepted. Dot completion, a complete graph and long-term Return
are **full-vision gaps**, not automatic blockers for that honestly scoped preview.

| Gate | Current state | Accountable owner / done when |
|---|---|---|
| Independent goal/scenario review | Complete with the partial/blocked findings above; did not inspect the combined RC. | Maintainer retains attribution and limitations; source-driven tests do not become native/model usage proof. |
| One reviewable combined candidate | Frozen local preview.11 at f84a502; version/resources/instructions/provenance smoke passed. | Maintainer preserves this identity for dogfooding; code/functions remain those tested at edd036f. Any subsequent feature gets its own source/review. |
| Delivery develops Delivery | **Next acceptance milestone, not yet claimed done.** | Maintainer onboards this actual candidate, chooses one feature-level gap, then traces owner intent → criteria → pre-edit impact → fresh implementation → independent verification → map/learning/resumption. |
| Quality before optimization | Static/source checks pass; model quality/resource benefit unproven. | QA checks the combined body on equal greenfield/brownfield tasks. If loading changes lose quality, retain conservative guidance; do not call smaller byte counts a win. |
| Exact candidate publication and checks | No new PR/retry/merge authorized by this record. Prior branch-publication rejections remain respected. | Owner resolves applicable publication/merge authorization for the concrete diff. Maintainer opens a normal review PR only when allowed, runs/reviews exact-head CI and fixes confirmed failures; no automatic merge/release. |
| Supported installation and first useful journey | Isolated CLI discovery passed; customer-host acceptance pending. | Owner supplies/authorizes an available supported host and writable test project. Verify fresh installed invocation and a useful result. CLI-scoped preview needs explicit restricted scope; full CLI/desktop/ChatGPT claims need their separate acceptance. |
| Value follow-up | Unknown outside-user usefulness/Return, retained honestly. | Owner + Maintainer record one pilot's actual outcome and next return check after preview; this does not require an analytics platform or fabricated adoption score. |

**External prerequisites/decisions:** preview surface/scope accepted by Owner; applicable permission for the concrete PR/merge and later
user-host update; an available authorized model host for missing behavior tests.
Basic planning needs no new server or provider key. Beads/Dolt are absent here,
so real Beads-backed runtime qualification needs an already authorized suitable
environment. No credentials, network policy or host permissions are changed to
make a test pass. Authenticated dot access needs an actual adapter/host trust proof,
not an agent-supplied role string or a model response.

**Authorized product-map save path.** Dot/native managers may prepare/read feature
context; an actually authorized writable host runs `product.py --project <canonical>
[--repo <product-root>] record --input <reviewed-input> --expected-sha256 <new-or-current-digest>`.
The host returns the actual path, saved digest and source commit. Preserve IDs/history,
owner-stated versus proposed choices and CAS conflicts. Without writes return
prepared/unsaved. Protected managers still cannot write product-map.json; an input
field is not human consent. Active → retired remains refused, not silently edited.

**Next smallest product workflow.** Prove a focused **feature decision/resumption
loop**: user + dot discuss one capability/customer, current/planned state, evidence,
what must survive, and build/change/retire options; retain the decision and one
bounded handoff against the canonical product revision; resume fresh, verify the
outcome and return learning. Current handoff is whole-product, so first onboard
Delivery and observe whether feature-scoped context is the concrete missing piece.
Reuse the record/initiative artifacts; no second ledger, autonomous agent platform
or new authentication service. Return the chosen gap/evidence before large changes.

**Exact first-proof setup.** Use the frozen installed CLI package on an already
working signed-in Codex host with writable normal host state, Python 3.10+, Git and
an explicitly authorized Delivery checkout/planning directory. Select Delivery as
the component and one canonical store outside the installable plugin. Fresh skill
invocation must load actual candidate files. This proves a supported assistant/
helper loop, not authenticated ChatGPT-dot runtime access. For actual dot work,
use an existing authorized private-repo connection plus that execution host; an
explicit artifact-assisted host-save handoff is acceptable if labelled manual.
If either is unavailable, prepare the packet and report the missing boundary.
Seamless dot execution still needs a supported authenticated adapter and its own
one-assignment/receipt proof. No credentials or new service are prerequisites for
basic local planning; no Beads requirement is imposed on this narrow preview.

**Publication gate remains unanswered.** Intended private remote branch is
`delivery/coherent-preview` in `colombod/ai-augmentation-systems-openai`, normal PR
into main, at an explicitly frozen reviewed head. Permission is still needed to
push/publish that concrete candidate; earlier branch PR rejections are not retried.
Publication alone does not authorize merge (including PR1 source), release or a
user-host update. No remote action is performed by this checklist.

**Do not build yet:** a graph service/database or second registry; a new agent/
authentication framework; broad language/semantic-graph parity; Amplifier runtime/
mandatory storyboard machinery; automatic retirement/merge/approval; or another
large roadmap/token-cache system. Consolidate existing value, resolve the actual
QA blockers, prove installation and one useful journey, then extend from observed
need. Keep this checkpoint current after each accepted result; do not add parallel
release lists.

## Design contract: OpenAI capabilities first

The delivery outcomes are the product: a grounded plan, traceable requirements,
review findings, an implementation handoff and an honest acceptance record.
The Claude role launcher and hook topology are source-audit findings, not the
architecture to reproduce. A plugin must use capabilities exposed by its current
host; packaging cannot create missing tools, local access or authority.

The default is one self-contained, skills-only delivery package. OpenAI documents
skills as usable without MCP when packaged guidance and existing tools suffice.
This makes instructions, templates and review lenses the common foundation;
it does not imply every host can run the helper or access the same files.
[Official skill guidance](https://developers.openai.com/plugins/build/skills).

| User outcome | Codex CLI / desktop local project | ChatGPT with the plugin available |
|---|---|---|
| Brief through roadmap and stories | Skills read/write authorized project artifacts | Skills use provided files or available connected documents; return artifacts when direct saving is unavailable |
| Canonical planning record | Existing project `.delivery/` and native file tools | Explicit accessible document store, or identified source snapshots with export; never imply a local repo was updated |
| Deterministic initialization / inventory | Packaged Python helper when Python and shell access are present | Optional execution only in an actually available environment; otherwise inspect supplied artifacts without claiming helper results |
| Critical review | Read-only native reviewers when delegation is available and authorized | Same rule; otherwise clearly labeled single-session lens passes |
| Implementation and acceptance | Native coding/test tools on the real target, subject to permissions | Handoff to Codex or an existing authorized tool; unavailable execution remains unverified |
| Long-running coordination | Native sessions/subagents where exposed; a separate local app-server client only if later justified | No assumption a plugin can spawn persistent role chats or run a watchdog |
| Guarded actions | Host approvals/sandbox plus tested operation-specific checks | Host/tool authorization; no assumed local hook enforcement |

These are design contracts, not cross-surface acceptance results. Plain ChatGPT
Chat, Work cloud, Work with local access, and Codex desktop are distinct execution
contexts. Detect actual tools and workspace access before acting. The universal
directory shares distribution, not runtime powers; cloud-orchestrated Work does
not support plugin lifecycle hooks.
[Supported plugin surfaces and limits](https://learn.chatgpt.com/docs/plugins).

### Deployment: MCP is optional

No server, tunnel, background process or new cloud account is required for the
default planning workflow. Prefer tools the user already connected before adding
a custom service. A GitHub connection, for example, is useful only for operations
its installed tools actually expose and the user authorized; it is not a general
shell or automatic local-worktree access.

| Optional integration | What has to run | Deployment consequence |
|---|---|---|
| Codex local MCP | A local stdio process, or a reachable HTTP service | Can stay on the user's machine; no public hosting required |
| Custom ChatGPT MCP over HTTPS | Our service at a reachable authenticated endpoint | Someone must operate the service; a GitHub plugin repo does not host it |
| Custom ChatGPT MCP through Secure MCP Tunnel | A private/local MCP process plus the tunnel client | No public inbound endpoint required, but both processes and connectivity must remain available |
| Existing connected provider | The provider's service | No new delivery server to operate; access and supported actions still depend on that connection |

Codex documents local stdio and HTTP MCP transports in its
[MCP guide](https://learn.chatgpt.com/docs/extend/mcp?surface=cli).
ChatGPT's direct custom-server flow uses an HTTPS MCP URL from a deployment or
development tunnel; see the [MCP quickstart](https://developers.openai.com/plugins/build/app-quickstart).
Secure MCP Tunnel also supports private/local servers without exposing them
publicly. It requires a running client/server, tunnel permissions, correct
workspace associations and custom-MCP access; it is an optional deployment to
validate, not an installed feature of this plugin.
[Tunnel requirements](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels).

### Coordination, hooks and judging

Role names in the planning preview are responsibilities and review instructions.
Persistent coordination, protected transitions and recovery remain required
outcomes of the full Codex delivery runtime. They are not waived by releasing a
planning preview. Their execution interface is surface-specific: a ChatGPT
planning session without execution access can prepare a handoff, but cannot be
advertised as a running shipping team. The contract below defines that boundary.

The portable workflow uses explicit phase checks and records their evidence.
These are procedural checks, not security enforcement. Optional Codex hooks can
add checks only after execution/trust and actual supported events/tool payloads
are accepted on that client. A custom tool can enforce its own writes; neither
a skill nor an MCP server governs every unrelated tool the host exposes.
The hook probe remains open for that optional capability; it no longer blocks
the skills-only release.

Judge selection remains `disabled`, `jev` or `openai`, explicitly configured.
It is optional classification, separate from the host model that follows the
skills. The default planning flow works without a judge. In local Codex a future
adapter can use a local helper and provider credentials without an inbound server.
ChatGPT needs an actual supported credentialed execution path or an optional
connected tool before invoking either provider; a local environment variable or
the user's ChatGPT subscription must not be assumed to provide that path.
Without it, report judging unavailable/disabled; do not silently switch provider
or replace an opted-in judge with host-model intuition. No judge establishes
human consent or grants execution authority.

Distribution also has separate acceptance: CLI local/Git catalogue installation,
desktop installation, and an actually available ChatGPT directory/workspace
installation route. A private Git repo and CLI discovery do not establish
ChatGPT installability. The current Python-backed preview has only CLI package
checks; the host-aware instructions need real scenario acceptance on each
surface. No hosted service or tunnel has been created.

## Implementation started: planning preview

The initial `0.1.0-preview.1` slice, now revised as `0.1.0-preview.4`, contains:
15 native skills, 20 adapted templates, ten reviewer lenses and non-destructive
Python initialization/inventory helpers. Source attribution and per-import
upstream hashes are in the package. It is self-contained and imports no Claude
runtime code. See its README for installation and capability limits.

Codex CLI 0.159.3 installed it in a temporary home, discovered all 15 namespaced
skills and executed the installed helper. This was an installation/protocol check
with zero model calls. It does not establish planning quality, desktop acceptance
or shipping-team parity. No judge provider is called; provider selection and the
guarded runtime remain separate implementation work.

Three targeted live Codex CLI model scenarios have since passed manual review:
status with no source artifacts, a frame brief with no delegation or persistence,
and synthetic interviews with no workers. The interview's initial leading
follow-up was corrected in the skill and its rerun passed. All four executions
are retained under `evidence/2026-10-20/live-behavior`; no tool calls were observed.
These tests supplied resources inline and simulated absent capabilities. They
do not establish installed-plugin activation, real missing-tool surfaces,
full-pipeline quality, desktop UI or ChatGPT acceptance.

## Full Codex runtime contract

The local `0.1.0-preview.6` runtime now implements persistent native roles,
controlled canonical artifact saves, Beads workflow gates, bound operator-terminal
receipts and explicitly selected Jev/OpenAI judging. Real Codex probes establish
same-thread restart, controlled peer messaging, both provider bridges, and an
opt-in independent-clone builder that stages and commits while protected paths
remain denied. Combined automated checks pass 121 Python regression tests; the
unchanged judge adapters previously passed 22 Node tests.

The contract below remains the required product scope. These targeted results do
not establish a complete autonomous delivery cycle, authenticated desktop UI or
ChatGPT operation. Protected acceptance currently closes a Beads task after an
operator attests CI/conflicts/surface evidence; automatic merge, push and deployment
are not implemented. See the [fresh CLI fixes and results](../evidence/2026-10-20/failure-fixes/README.md)
and [earlier integration evidence](../evidence/2026-10-20/delegated-integration/README.md).

The earlier preview included only planning and the project helper. The tables
below distinguish the current local implementation from remaining acceptance.

### Execution boundary and native interfaces

The proposed full runtime is a local coordinator owned by the operator, using
Codex rather than a hosted delivery service. CLI and desktop can invoke its
bounded local command interface through their authorized execution tools. The
coordinator owns its worker sessions; this does not mean it can create or control
the desktop app's visible chats. A shell-less ChatGPT session receives status or
a handoff through available tools; no local team is silently launched there.

The current app-server exposes `thread/start`, `thread/read`, `thread/resume`,
`thread/fork`, `turn/start`, `turn/steer` and `turn/interrupt`, plus item/turn
notifications and approval requests. The installed 0.159.3 generated schema
confirms these interfaces, but our probes only establish selected plumbing.
Official documentation currently labels app-server experimental and unsupported
for production workloads. Consequently an app-server-backed coordinator is a
prototype until the deployment accepts that limitation or a supported interface
replaces it; it cannot be sold as production-ready parity.
[Native protocol and maturity](https://learn.chatgpt.com/docs/app-server).

| Delivery operation | Native mechanism / local implementation | Failure behavior |
|---|---|---|
| Prepare team | Resolve private planning repo, existing Beads DB, product repo and role worktrees; inspect available model/configuration capabilities | Reject conflicting identity/root/worktree assignments before starting workers |
| Start persistent role | Coordinator creates a non-ephemeral thread with role instructions, actual cwd and supported permissions | Store a role-to-thread binding only after a valid response; a thread with no persisted turn is not recoverable |
| Send work / inter-role message | Local coordinator validates sender, recipient, initiative and scope; queues input for `turn/start` or bound `turn/steer` | Never inject peer text as authenticated human instruction; do not steer a stale turn ID |
| Observe progress | Consume actual `item/started`, `item/completed` and `turn/completed` events | Record incomplete/failed/declined distinctly; a tool-start event is not success |
| Stop / recovery | Interrupt the exact active turn; after reconnect read/resume the recorded thread and reconcile terminal state | Never restart work from missing events by assuming success; escalate uncertain external effects |
| Human interaction | Forward native question/approval requests to an operator-controlled client; correlate responses to the pending request | Timeout, cleared request, disconnect, refusal or peer response grants no authority |
| Status / watchdog | Read coordinator bindings, last received events and Beads; distinguish active, idle, stale, stopped and unknown | No heartbeat means unknown/stale, never task completion; do not kill unrelated processes |

Do not use app-server `process/*` or `thread/shellCommand` as a worker execution
shortcut: those APIs operate outside the thread sandbox. The coordinator must
use the actual supported permission model and refuse startup if a required
restriction cannot be represented. There is no dangerous approval/trust bypass
in the design. The 0.159.3 protocol schema is the adapter input; changes in a
client build require compatibility checks, not field guessing.

### Persistent roles and temporary reviewers

The operator-facing coordinator, Product Manager and Delivery Manager retain
their own durable sessions. Builders receive separate product worktrees.
Staffing, observation, spike research and real-surface checking remain explicit
responsibilities; a deployment may combine or separate their sessions only if
its roster states that choice and preserves independent author/reviewer checks.
A temporary review lens cannot impersonate any of these durable roles.

Each role binding records team, instance, permitted roots, thread ID, configured
model, effective capabilities and source revision. These are coordinator records,
not model-writable identity claims. Store bindings and append-only runtime events
in the private planning project under `.delivery/runtime/`; Beads remains the
task/dependency authority. Do not duplicate mutable task status in a second task
database. Respect project instructions when choosing the canonical root.

Model presets use explicitly available Codex models; never translate Opus,
Sonnet or Haiku names into an assumed equivalent. An unavailable configured
model pauses the role or asks for an explicit configuration change. Usage records
retain provider/model/unit data; unknown usage stays unknown, not Sonnet-weighted
cost or invented remaining budget.

### Controlled transitions, authority and evidence

The proposed transition path is draft → ready → claimed → implemented → reviewed
→ surface-verified → accepted. Preview `ready` remains manually planning-ready;
it is not a full-runtime readiness seal.

| Transition | Required binding / check | Invalidation or refusal |
|---|---|---|
| Ready | Delivery owner records current criteria hash, declared surface, assumptions and dependencies | Changed criteria, refuted assumptions, missing real-host spike or unresolved blocking dependency require renewed readiness |
| Claim | Coordinator validates the bound worker identity and Beads dependency/current-state transaction | Concurrent/stale claim, unready work or wrong lane cannot proceed through this command |
| Implemented | Builder supplies actual commit SHA and test output; records failed checks too | A textual "done" message alone does not change acceptance state |
| Reviewed | Separate reviewer is bound to exact head SHA and criteria hash | Author cannot approve their own work; a new commit or criteria change invalidates the review |
| Surface verified | Record actual target host/app/mode, deployed SHA, criterion, actor, observation time and capture/command/result references | Stub, source-only, wrong-host, wrong-version or unobservable evidence is not real-surface acceptance |
| Accepted / merge | Authorized delivery owner checks current review, criteria, CI, conflicts and required real-surface evidence | No delegated classification can grant consent; mismatched head/version or missing authority refuses the operation |

These transitions must run through a deterministic local API/CLI with atomic
checks against current state. Tests must also exercise attempted direct mutations
using the actual worker permissions. Hooks may add checks after their acceptance,
but a hook name, skill guideline or MCP wrapper is not global enforcement.
Describe any remaining bypass paths honestly. The coordinator's authority covers
its workers and controlled commands, not unrelated user-run clients or shell
sessions. If claimed lane/evidence protection cannot survive a supported worker
tool path, the full-runtime release is blocked rather than relabeled protected.

An operator decision records the exact question/options, answer, pending request
ID, thread/turn/item binding, source revision, scope, expiry and revocation state.
Only a response captured by the operator-facing client can be a candidate human
decision. `serverRequest/resolved` alone is insufficient: it can also signal
cleanup without an answer. No automatic timeout selection counts as consent.
Replay, expired, revoked, unmatched or already-consumed authority is rejected.
The client/provenance adapter must be tested; transcript text, JSON actor fields
and hash chains alone do not authenticate a person. A deployment without a
verified capture path keeps the protected transition unavailable.

Jev/OpenAI classification uses the separately selected adapter, minimal declared
inputs and explicit error/refusal results. It may inform the named question's
advisory or blocking policy only after provider-specific calibration. It cannot
author an operator response, override native approval or silently select another
provider. CLI direct outbound calls require no inbound MCP server. A later MCP
interface can expose the same controlled operations without changing their rules.

### Required acceptance scenarios and current disposition

| Scenario | Expected observable result | Current evidence |
|---|---|---|
| Portable package ingest and native CLI install | Schema validation, all expected skills and resources found | Schema/CLI probes; not account ingestion |
| No shell / no connections | Prepare an export or report missing inputs; do not claim saved files or helper execution | Explicit instruction branches; real-model acceptance still required |
| No delegation | Sequential review is usable and labeled; independent convergence unavailable | Explicit phase branches; actual behavior still needs testing |
| Persistent worker restart | Resume the correct worker after a real completed turn without duplicate external effects | Real same-thread Codex restart and controlled peer-tool dispatch; unknown effects are not replayed |
| Manager writes product / worker spoofs identity | Native permissions and controlled operations refuse; no fabricated identity admitted | Implemented; automated denial tests and targeted native sandbox probes, not full-host acceptance |
| Peer answer / timeout / replay / revoked decision | Protected action stays denied with a bound reason | Implemented; OS-terminal synthetic capture and denial/replay/revocation tests, not real human identity acceptance |
| Criteria change / new commit / wrong deployed surface | Old readiness, review or evidence no longer authorizes acceptance | Implemented current-head/criteria/evidence binding and invalidation tests; surface evidence remains operator-attested |
| Provider missing / refuses / times out | Report disabled/unavailable/error without provider switch or consent inference | Both adapters implemented; malformed/refusal tests, synthetic benchmarks and real native bridge calls; no fallback |
| Desktop or ChatGPT installation and real task | Verify the actual host and artifact persistence path; report unsupported runtime capabilities | Pending, separately from CLI protocol checks |

The buildable sequence is tracked in Beads: portable package/phase corrections,
real workflow acceptance, then local runtime implementation against this contract
and its denial/recovery tests. The full runtime remains part of the intended
delivery product, not an optional feature discarded to fit the shared preview.

## Source baseline

- Repository: [colombod/ai-augmentation-systems](https://github.com/colombod/ai-augmentation-systems).
- Revision: `df0c0a5b0dba1449b6cdfef421bfe1ebc4d658c0`.
- Package: `plugins/delivery`, version `0.30.0`.
- Inventory: 23 skill entry points including aliases, eight persistent role briefs,
  eleven reviewer personas, 25 templates and 56 test files.
- Unchanged-source test run: 932 passed, zero failed on Node 26.5.0. Upstream CI
  specifies Node 24. Local suite success is not live Claude or OpenAI acceptance.

## Claude operating model: source audit, not a mandatory blueprint

Persistent Chief of Staff, Product Manager, Delivery Manager and builder sessions
coordinate through messages and Beads. Reviewer personas are temporary lenses;
they are not substitutes for those persistent sessions. Builders have product
worktrees; plans and operator records stay in the private project repository.

Role setup writes `.claude/settings.local.json`, native allow/deny rules,
environment identity, `.delivery-role.json` and `CLAUDE.local.md`. Session hooks
refresh instructions and liveness. These form one runtime system: copying only
skill prose or renaming tools does not preserve its guarantees.

## Source components to reassess against the native design

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

Accept the server-free workflow independently on CLI, desktop and an actual
ChatGPT installation: resolve accessible artifacts, preserve prior revisions,
handle absent shell/delegation/connections, export when direct persistence is
unavailable, and report source/runtime/UI evidence honestly. Judge absence and
hook absence must not prevent core planning.

Accept optional native coordination, guarded tool actions, hooks, judge adapters
and any custom MCP deployment separately before advertising them. Require real
allowed/denied operations, restart and review invalidation tests for capabilities
that claim those guarantees. A missing approval binding means the action remains
unavailable; it does not justify inventing a Claude-style transcript origin.
The evolving work and dependencies are tracked in Beads.
