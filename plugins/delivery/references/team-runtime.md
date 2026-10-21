# Local delivery team

The local runtime gives delivery roles durable Codex sessions, queues work between
them, saves canonical planning artifacts, and controls Beads workflow submissions.
The operator remains responsible for explicit acceptance. It does not merge, push,
publish or deploy. This is a local runtime preview; separate desktop and ChatGPT
installation/workflow acceptance remains pending.

## Dependencies

- Python 3.10+, Codex CLI with a compatible app-server protocol, existing native
  Codex sign-in, Git and an existing Beads planning project.
- A private planning project and separate product Git worktrees for builders.
  Builders must not contain the planning runtime, selected judge configuration,
  or the active plugin/coordinator implementation.
- Node.js 20+ and the explicitly selected provider's environment credential only
  when calling a separate judge. Basic planning and coordination do not require
  a separate judge. A Codex/ChatGPT subscription is not an API credential.

No inbound MCP server or hosting is required. CLI/desktop needs actual authorized
local execution. A ChatGPT host without it must report the runtime unavailable
and return a handoff/export; loading a skill does not launch a local team.

## Prepare and run

Create `.delivery/team.json` in the planning project. Paths must be absolute,
existing directories. Choose a model actually available to the Codex account:

```json
{
  "roles": {
    "coordinator": {"cwd": "/absolute/planning", "model": "MODEL_ID", "lane": "read-only", "instructions": "Coordinate the team. Keep unanswered questions and evidence gaps explicit."},
    "product-manager": {"cwd": "/absolute/planning", "model": "MODEL_ID", "lane": "read-only", "instructions": "Own outcomes, criteria and scope. Save draft plans through delivery_artifact_write."},
    "delivery-manager": {"cwd": "/absolute/planning", "model": "MODEL_ID", "lane": "read-only", "instructions": "Own dependencies, staffing, independent reviews and delivery risks. Use canonical Beads and controlled delivery tools."},
    "builder": {"cwd": "/absolute/independent-product-clone", "model": "MODEL_ID", "lane": "builder", "git_metadata_write": true, "instructions": "Implement assigned work here. Preserve actual commits and tests; use .delivery-evidence for evidence files. Implementation is not acceptance."},
    "reviewer": {"cwd": "/absolute/independent-product-clone", "model": "MODEL_ID", "lane": "read-only", "instructions": "Review independently. Save review/host-observation submissions through delivery_artifact_write under reviews/. Do not approve your own work."}
  }
}
```

For a builder that must stage and commit, use an independently prepared Git
clone, not linked worktrees sharing an object store. For a local source repository:

```sh
git clone --no-local --no-hardlinks /absolute/product-source /absolute/independent-product-clone
```

`git_metadata_write: true` is an explicit builder capability. The runtime requires
an independent Git store inside that builder root, a symbolic branch, no object
alternates or hardlinked objects, and no shared builder store. It permits only
specific native Git metadata paths for staging/commit; Git configuration, hooks,
planning state and the active coordinator implementation stay protected. The
current branch/store identity and exact native roots are pinned and rechecked.
Default builders can edit files but cannot commit; do not describe them as full
implementation workers. Unsupported linked-worktree writable Git fails closed.
Stage only explicit product files, inspect the staged diff, then commit the
staged index with `git commit -m "Message"`. Do not pass file paths to `git commit`:
that form creates temporary index locks outside the supported metadata profile.
Report unsupported operations instead of requesting sandbox expansion. Run Python
checks with `python3 -B` or `PYTHONDONTWRITEBYTECODE=1`; keep generated evidence
under `.delivery-evidence/` so untracked caches do not invalidate the clean commit.
Temporary build files use `.delivery-evidence/tmp` inside the builder root rather
than granting global `/tmp` access. Native Git hooks remain enabled and sandboxed.
Acceptance checks compare raw tracked file bytes and executable modes to the
commit independently of the builder index. Transformed clean-filter/CRLF
checkouts and submodules require a separately reviewed safe adapter; the current
checks refuse unsupported cases rather than running repository filters in the
coordinator.

Replace `<package>` and `<planning>` below with actual absolute directories:

```sh
python3 <package>/scripts/project.py init --project <planning> --initiative example
python3 <package>/scripts/runtime.py --project <planning> prepare --roster <planning>/.delivery/team.json
python3 <package>/scripts/runtime.py --project <planning> serve --operator-terminal
```

Keep `serve` running in an operator-owned terminal. The operator, rather than
a worker or an agent-controlled PTY, must own input to the capture terminal. Without `--operator-terminal`,
work can proceed but requests requiring operator capture cannot be accepted.
The supervisor runs one trusted terminal capture at a time asynchronously;
expiry, revocation, native events and controls continue while it waits.

In another authorized local session:

```sh
python3 <package>/scripts/runtime.py --project <planning> send --role product-manager --message-file /absolute/request.txt
python3 <package>/scripts/runtime.py --project <planning> status
```

Each role retains its native thread. Native model/configuration errors never
silently select another model. Connected tools and native computer/browser write
surfaces are excluded and their effective configuration is checked; startup
fails closed if the lane cannot be represented. Native command/file escalation requests receive an immediate decline or, when
that is the offered refusal, cancellation. They cannot be approved through an
operator response. Cancellation can end the native turn; inspect its actual
terminal state before using the exact recovery controls. Do separately authorized
setup outside the worker and resume afterward. Actual operator questions and
protected task acceptance still use explicit terminal capture.

Managers use read-only native shell sessions. `delivery_artifact_write` saves
permitted canonical planning paths through the coordinator with an expected
content hash. Reviewers can save review submissions only. Prior revisions and
write intents are kept in protected runtime storage; interrupted writes reconcile
against actual bytes instead of blindly replaying. These artifacts are draft
submissions, not authenticated decisions.

## Controlled work and review

The native tools support peer messaging, canonical Beads reads, draft story
materialisation, readiness, claiming, implementation/test submissions, independent
review, declared-surface observations, readiness renewal and operator acceptance.
Tool descriptions and schema expose exact fields. Role/thread/turn identity comes
from the native request, not model-supplied actor text.

Beads remains task/dependency authority. Readiness binds current canonical
criteria and declared host/app/mode/criterion. Changed criteria, dependencies,
tracked or untracked product changes, commits, assumptions or evidence invalidate
old submissions. Untracked product outputs belong only in `.delivery-evidence/`.
Reviewers must have a separate read-only role/thread from the author. A submitted
file is not an authenticated real-host observation.

`delivery_task_accept` prepares the exact current scope and evidence for the
operator. It requires quiescent builders and an explicit terminal response to a
bound `delivery/gateAcceptance` question. The operator attests that current CI,
conflicts, independent review and actual declared-surface evidence were checked.
Acceptance closes the canonical Beads task; it grants no merge/push/deploy right.
This is operator-attested verification, not automatic external CI/GUI verification.
Coordinator commands are serialized; unrelated user-run Beads/Git mutations are
outside its authority and no global atomicity guarantee is claimed.

Operator capture uses an in-memory signing capability unavailable to worker
tools. It binds exact question/options, request, native thread/turn/item, source
revision and scope. Responses expire, are one-use and can be revoked. Restart,
cleared requests, peer messages, timeouts and arbitrary JSON never grant authority.
The legacy `reply --answer-file` interface is deliberately unavailable.

## Recovery and controls

Stopping the supervisor with Ctrl-C exits cleanly with status `0`; operational
CLI errors exit `2`. A clean supervisor stop does not mark worker tasks complete.
Startup still reconciles persisted native state before work can continue.

Status distinguishes active, idle, stale/unknown and needs-reconciliation. An
interrupt acknowledgement is not completion. An uncertain external effect is
never automatically retried. Use exact IDs reported by status/native events:

```sh
python3 <package>/scripts/runtime.py --project <planning> interrupt --role builder --thread THREAD_ID --turn TURN_ID
python3 <package>/scripts/runtime.py --project <planning> steer --role builder --thread THREAD_ID --turn TURN_ID --message-file /absolute/update.txt
python3 <package>/scripts/runtime.py --project <planning> recover --role builder --thread THREAD_ID --turn TURN_ID
python3 <package>/scripts/runtime.py --project <planning> revoke --request REQUEST_ID
```

Controls expire and bind the exact current role/thread/turn. A tool-schema upgrade
requires an explicit new session after terminal-state verification:

```sh
python3 <package>/scripts/runtime.py --project <planning> migrate --role builder --thread THREAD_ID --turn TURN_ID --reason "Upgrade native tool schema"
```

Migration preserves the old history and never replays the previous assignment. Recovery checks
actual native terminal evidence before allowing new work; it does not replay the
old assignment. Role tool schemas are version-bound. A session created with an
older schema cannot silently acquire new native tools on resume; an explicit
new-session migration is required. Preserve the old native history.

## Explicit judge selection

Optionally add an absolute `judge_config` path to the roster. The runtime pins
its selected JSON and content hash in protected storage, rejects builder-writable
paths and refuses a changed source until explicit operator configuration. The
native `delivery_judge` tool uses that selection; no worker field selects another
provider. Example configuration:

```json
{"judge": {"provider": "openai", "model": "gpt-6-luna", "key_env": "OPENAI_API_KEY"}}
```

For Jev use `provider: "jev"`, a chosen Jev model and `TYPESAFE_API_KEY`.
`typesafe` is a compatibility alias. `disabled`/`none` makes no provider call.
Environment key names must belong to the selected provider. Never put credentials
in configuration or artifacts. Missing credentials, refusal, malformed answers
and timeout are unsuccessful results with no cross-provider fallback.

```sh
node <package>/scripts/judge.js questions
node <package>/scripts/judge.js ask divergence --config /absolute/judge.json --state /absolute/minimal-state.json
node <package>/scripts/judge.js evaluate relay_request --config /absolute/judge.json --state /absolute/minimal-state.json --protected
```

Only the question's declared fields are sent; a best-effort sensitive-state
filter can refuse the call locally. OpenAI predicates normalize to yes/no and
probability; choices retain declared options. All answers remain advisory and
carry no human authority. `evaluate` additionally reports policy eligibility.
Protected blocking requires a matching provider/model/question/version/hash and
reviewed calibration record. Historical Jev scores do not transfer to OpenAI or
a changed model; model aliases cannot qualify. Candidate synthetic evaluations
are maintainer evidence and are not installed as defaults. Warn-only/advisory
questions cannot become blocking gates. `orders_owner` still requires its
independent imperative guard; `goal_instruction` remains a second key.

Exit status: `0` for a successful answer/list/nonblocking evaluation, `3` for
skipped/failed or protected-unavailable/blocking evaluation, `2` for invalid CLI
input. Fixed provider endpoints are used; loopback overrides exist for tests.

## Acceptance boundaries

Native persistence, recovery plumbing, restricted shell writes and live provider
classifications have targeted tests. Automated PTY tests prove terminal-channel
plumbing, not a real human's identity or product acceptance. Real local Beads
roundtrips use synthetic Git/evidence fixtures. Desktop and ChatGPT require their
own actual installation and workflow tests. No hooks, automatic deployment,
independent cloud CI verifier or universal enforcement over unrelated clients is
installed by this package.
