# Fresh host qualification

Plugin source revision: `f817ab6d1af5b8eabcd76687d0c28446136e15f9`.
The updated installation probe is maintainer-only; the package helper/skill used
here is unchanged from that commit. Codex CLI: `0.163.0`.

## What passed

`python3 scripts/probe_delivery_install.py --output <new-evidence.json>` installs
the actual package into a new disposable `CODEX_HOME`, registers its marketplace,
starts a fresh native app server and calls `skills/list`. All 16 skills are found,
including `delivery:product`. The installed package includes its scripts, starter
input, references and attribution. The installed product helper saves the
illustrative greenfield starter and returns a handoff retaining unconfirmed
choices and absent source commit. See `install-discovery.json`.

This is actual supported CLI plugin installation/discovery and installed-resource
execution. It is **not** model invocation, outside-user behaviour, desktop or
ChatGPT product acceptance. The separate disposable home receives no copied
credentials or personal config. Zero model turns were started.

## Native invocation attempts and exact blocker

The existing native `codex login status` reports `Logged in using ChatGPT`.
No credential contents were read, printed or copied. The intended probe creates
new planning directories, loads the installed skill through the native protocol's
explicit `skill` input, and uses the existing sign-in in its normal home.

1. The default app server failed to initialize SQLite runtime state under
   `/home/agent/.codex`, before any model turn. `initial-native-failure.json`
   retains the exact failure.
2. Local generated protocol/schema and installed CLI binary expose `sqliteHome`
   and `CODEX_SQLITE_HOME`. Redirecting runtime SQLite state to the writable
   test directory and logs to a writable test directory preserved sign-in in
   its normal home. The retained result records `server_disconnected` before a
   turn. See `state-override-native-failure.json`; that JSON does not establish
   the exact remaining write path or errno.
3. A bounded fresh `codex exec --ignore-user-config --ephemeral --sandbox
   workspace-write` attempt used the exact package files as a project-local skill
   and the same separate writable SQLite/log locations. It failed before inference:
   `failed to initialize in-process app-server client: Read-only file system`.
   See `ephemeral-cli-attempt.json` and `ephemeral-cli-stderr.txt`. Its qualification
   field describes the attempted route; it does not assert a completed session.

No model session reached the skill; no canonical product record was created by
a model. Greenfield native invocation was not repeated after this shared startup
failure. No approval/hook/sandbox setting was weakened, and no user business task,
external service, credential generation or further authentication attempt ran.

The minimal environment requirement is a supported writable native runtime
bootstrap with the existing authentication—either the authenticated home can hold
its required state, or the host supports separating **all** startup state from
the read-only sign-in location. The first failure names the home; the later generic
errors do not name the remaining write path. A fresh empty home solves discovery
but has no demonstrated model sign-in. Copying credentials is not an acceptable
substitute. These attempts do not establish a product skill defect or a successful
native workflow.

## Required next product proof versus optional machinery

The required acceptance run is a fresh supported native session on both equal
paths: discover/select the actual skill, curate a small baseline without a pre-made
map, preserve proposed owner decisions and missing usage evidence, answer one real
impact question for brownfield, and save an idea-only greenfield handoff. Measure
time/effort to first result and inspect all failed commands. An independent
maintainer's own task and unprompted return are separate usefulness evidence.

Curating features and reading their code/evidence is still real work. The census
only supplies candidate files; the existing actual-repo command demonstration
uses an authored map. It has not proved a fresh model or stranger can perform
that curation easily. If that first run stalls on JSON/template burden, a bounded
drafting aid or narrower input contract may earn its place. Do not declare the
onboarding problem solved from helper tests alone.

Automatic symbol graphs, transitive/dynamic impact, auto-imported backlogs, a
Decisioncraft canvas and authenticated dot adapter are optional additions until
the concrete first-value task requires them. They do not fix the present native
startup block. Actual retirement/migration remains a separately user-authorized
action; unknown Return never authorizes removal.
