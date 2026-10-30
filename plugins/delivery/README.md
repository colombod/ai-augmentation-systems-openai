# Delivery

**Product/feature preview.** This combines the previously separate source
into one installable version. Installation on your devices is a separate step.
The working unit is a product or feature outcome: who it serves, current versus
planned capability, value/evidence, owner intent and whether to build/change/retire.
The candidate supports owner-led framing, authorized host-saved product records,
curated direct/optional Python impact, handoffs, retirement proposals and completed
retirement records.
Code, tasks and agents support those decisions; the preview is an increment toward
the full user-and-dot delivery loop, not its completion.
Native coordination remains experimental and separately configured; authenticated
dot access, desktop/ChatGPT acceptance and measured token benefit are not established.
An authorized host can record a completed retirement with current evidence; the
helper performs no retirement and authenticates no approval.

Delivery helps turn a product idea into a plan someone can implement: a problem
brief, supporting research, customer personas, requirements, design, architecture,
roadmap, stories and a scoped implementation handoff. After implementation, it
helps review the evidence and update the plan with what was learned.

**Version `0.1.0-preview.14` — product and local runtime preview.** Sixteen skills use
21 templates and 10 review lenses. Greenfield ideas and brownfield projects share
one product contract: owner intent, customer promise, usefulness and planned or
observed features. The local coordinator adds persistent Codex
roles, canonical artifact saves, controlled Beads workflow, independent review
submissions and explicit operator acceptance. Jev/OpenAI judging is explicitly
selected. Desktop and ChatGPT workflow acceptance remain pending.

For an existing feature-map question, invoke `$delivery:product` with the question
and selected project/component. Its focused route reads the core contract and runs
`status` or `impact --path`, without loading the full authoring workflow or emitting
an owner-context handoff. Authoring, changing owner choices and retirement still
load the full product contract. The [common contract](references/core.md) owns
source reuse, including mutable-checkout content verification and compaction rules.
This is instruction routing; improvement remains unproven until model evaluation
shows quality is preserved alongside actual resource use.

For dependency-side impact, the existing helper accepts
`impact --path <file> --transitive`. Direct matches remain separate; optional
Python import reach adds shortest file/line chains, shared consumers, exact commit
and unresolved/unsupported coverage. It executes no project code and adds no
service or registry. Other languages retain direct coverage. Planned greenfield
features have no observed dependency graph; unavailable reach is informational,
not a story-readiness gate. See [the product contract](references/product.md).

## Dependencies

| Requirement | When it is needed |
|---|---|
| Host with plugin/skill support and model access | Required for planning. CLI installation was verified on Codex `0.159.3`; desktop and ChatGPT acceptance remain pending. |
| Project context or supplied documents | Provide the idea and relevant artifacts. Missing inputs remain unknown. |
| Authorized file/document tools | Needed to read and save the canonical record directly. Without write access, outputs are complete exports labeled unsaved. |
| Python 3.10+ and shell access | Optional, for the local helper. It uses only Python's standard library. |
| Browsing or connected source tools | Optional, for current research. Without them, uncovered claims are labeled unresearched. |
| Native delegation | Optional, for isolated reviewers. Otherwise lenses run sequentially and the result is labeled single-session review. |

The planning skills need **no custom server, MCP connection, Node.js, Beads installation
or separate Jev/OpenAI API key**. It uses your host's existing model access.
Review lenses are instructions for that model. The separate judge CLI is an
explicitly selected optional execution path and requires its own credentials.
The coordinator requires Codex CLI and Beads; the judge CLI requires Node.js 20+.
These are additional dependencies of those commands, not of basic planning.

Repository development uses `requirements-dev.txt` in a virtual environment.
Those packages are not plugin/helper runtime dependencies. Beads is used for
this repository's contributor tasks; the planning helper does not create
Beads tasks. The configured runtime can materialize canonical stories through its
controlled Beads operation. Follow any task-tracking rules of the project you are planning.

## Install in Codex CLI

Use a checkout containing `plugins/delivery/`. Source is available in this
repository; installed packages are separate snapshots. Check the installed
version and files before assuming they include product tools or the local runtime.

From the **marketplace repository root**, run in a terminal:

```sh
codex plugin marketplace add .
codex plugin add delivery@ai-augmentation-systems-openai
```

Start a fresh Codex session in the project to plan. Select a delivery skill from
the host's picker or use the `$delivery:…` prompts below. The portable Agent
Plugins 1.0.0 package was tested on CLI 0.159.3 without a compatibility overlay.

### Codex desktop and ChatGPT

Both are intended targets, but their installation and end-to-end workflows have
not been accepted yet. CLI registration is not a ChatGPT install. Once installed
through an available host-supported route, select the skills in that host's
picker (`@` where supported). This preview does not claim a verified desktop or
ChatGPT setup path.

### Existing cloud or remote sessions

If your existing cloud assistant has model access and authorized tools to read the
installed package, it can follow Delivery in that session. A local Mac or another
model launcher is not a prerequisite. Automatic discovery in the host's skill
picker is a separate capability: a CLI install does not register skills in a
cloud chat catalogue. This file-resource route does not establish a persistent
team, authenticated dot access or acceptance on other hosts.

Use the host's supported resource reader or filesystem tools to read the full
installed `skills/product/SKILL.md`, then its linked `references/core.md`,
`references/product.md`, `references/runtime.md` and, for choosing/delivering one
small change, `references/bounded-change.md`. Resolve links against that installed
package; a source checkout may be a different revision. Record the package
identity and loaded resources. Reading catalogue metadata alone is insufficient.

For a new idea, supply the customer goal and notes; no repository is required.
For an existing product, identify the repository/component and read its instructions,
current features, unfinished work and evidence. In either case, first reuse the
existing canonical `.delivery/` store (or identified document store) and initiative;
keep owner choices and history. Do not initialize a parallel map. The product
skill guides framing, onboarding gaps and selection of one useful next outcome.
Use its bounded-change route for a small story, sprint, independent review and
realignment; ordinary authorized shipping follows that route's shipping handoff.
Local coordinator setup is required only when persistent coordination is requested.

With shell/Python and filesystem access, invoke helpers from the installed package:

```sh
python3 <installed-package>/scripts/product.py --project <planning> --repo <product-git-root> inspect
python3 <installed-package>/scripts/product.py --project <planning> --repo <product-git-root> status
python3 <installed-package>/scripts/product.py --project <planning> --repo <product-git-root> handoff --feature <exact-feature-id>
```

These read-only queries reuse an existing record; `inspect` also works before a
map exists. Omit `--repo` for a greenfield idea. A missing map remains missing until
authorized authoring; a helper output or model judgment grants no write, acceptance,
merge or deployment authority. Follow the selected skill for authoring commands.

If resources cannot be read, report them as unavailable rather than inventing their
instructions. Without shell/Python, follow readable resources and accessible
artifacts manually. Without an authorized save tool, return a complete export
labelled **prepared, not saved to the canonical store**. Missing capabilities stay
explicit; do not add a service, copy credentials or weaken host controls to make
planning work. No remote operation or device installation follows from file access.

## How to use it

Send these examples in **Codex chat**, not your terminal. Replace the idea,
initiative and artifact names with your project's own.

### Start a planning effort

For either a new idea or an existing product, start with the customer outcome:

```text
$delivery:product Frame this new idea for one primary customer. Preserve my intent, make the first useful journey and explicit cuts clear, and keep missing evidence unknown. There is no code repository yet.
```

```text
$delivery:product Onboard this existing repository. Read its instructions, current features and unfinished work. Map the code and evidence at the current commit, then show which features a change to scripts/project.py could affect. Preserve existing artifacts.
```

The skill curates the record; its read-only census does not infer features or
import remote backlogs automatically. It carries one primary customer/proposition,
the owner's reasons and what must survive, six separate usefulness judgements and
the smallest sufficient work form into the next planning step. Proposed choices
remain proposed. No repository is required for a greenfield record.

The [product contract](references/product.md) gives complete local commands and
the input format. Its `draft --outline notes.json` command expands a few feature
names and optional code/evidence routes into full record input, with choices
proposed and usefulness Unknown. It does not save or infer shipped status. With
an initialized planning project, the helper supports:

```sh
python3 <package>/scripts/product.py --project <planning> --repo <git-root> inspect
python3 <package>/scripts/product.py --project <planning> --repo <git-root> impact --path scripts/project.py
python3 <package>/scripts/product.py --project <planning> handoff
python3 <package>/scripts/product.py --project <planning> handoff --feature <exact-feature-id>
```

The impact command requires a previously curated brownfield record. For its
handoff, also supply `--repo <git-root>`; omit it for a greenfield idea. Maps check
full commit and raw file bytes, reveal shared mapped code and keep unknown coverage
visible. They are file-level links, not a complete dependency graph or deployment
proof. `retire-plan` prepares subtraction with shared-code protection; it never
deletes code or supplies a human decision.

```text
$delivery:start Use the current project and initiative checkout-redesign.
```

With local execution, start creates planning directories without overwriting
artifacts and reuses an existing ancestor `.delivery/`. Otherwise it establishes
the project/initiative context and explains how documents will be returned.
It does not launch a team or create a placeholder brief.

```text
$delivery:brief Frame an improvement that shows phone shoppers delivery costs before they invest effort in checkout. Use initiative checkout-redesign.
```

The brief identifies the problem, affected segment, success signals, scope,
assumptions and unanswered questions. Existing artifacts are read before revision
and their history is preserved. You can invoke any phase whose inputs already
exist; you do not have to restart the pipeline.

For a small outcome, ask `$delivery:product` to choose one evidence-backed next
change, then `$delivery:stories` using `route: bounded-change`. The packaged
[bounded-change route](references/bounded-change.md) carries the compact contract
through sprint/review/realignment and an explicitly authorized shipping handoff.
It does not require boilerplate PRD/architecture/roadmap documents or grant runtime
actors publishing permissions.

### Choose a workflow

Invoke a table entry as `$delivery:<skill-name>`.

| Skill | What it produces or assesses |
|---|---|
| `start` | Planning workspace and initiative context |
| `product` | Equal greenfield/brownfield product framing, feature/code evidence, freshness, impact, usefulness and safe retirement proposals |
| `brief` | New feature framing or assessment of an existing product |
| `research` | Prior art, domain constraints, technical options and sourced gaps |
| `personas` | Shared customer personas with observed/reported/assumed grounding |
| `simulate` | Synthetic interviews or journeys; hypotheses, not customer research |
| `prd` | Scenarios, traceable requirements and MVP staging |
| `design` | Design-system rules, tokens and component states |
| `architecture` | Technical design, decisions, assumptions, spikes and customer surface |
| `roadmap` | Sequencing, dependencies, estimates and requirement coverage |
| `stories` | Self-contained implementation stories and manual readiness review |
| `sprint` | Scoped work package with a Codex or generic implementation handoff |
| `challenge` | Ranked findings against an artifact; the target stays read-only |
| `sprint-review` | Evidence-based assessment of a separately implemented wave |
| `realign` | Plan changes informed by the sprint review |
| `status` | Current planning record, missing inputs and unresolved findings |

Examples:

```text
$delivery:challenge .delivery/initiatives/checkout-redesign/brief.md
```

```text
$delivery:simulate --interview Explore delivery-cost objections using the existing checkout-redesign personas.
```

```text
$delivery:sprint Scope the next checkout-redesign wave --runner codex
```

```text
$delivery:status Review checkout-redesign and identify the next useful step.
```

The sprint skill prepares the work package; implementation happens in a
separately authorized coding session. Run `sprint-review` against its actual
results, then `realign`. Missing prerequisites and blocking findings are reported.

## Where the work is saved

In a local project, a typical record is:

```text
.delivery/
  initiatives/checkout-redesign/
    brief.md
    research.md
    prd.md
    architecture.md
    roadmap.md
  glossary.md
  personas/
  stories/
  reviews/
  sprints/
```

Directories/documents appear as needed. Shared personas and glossary are reused;
stories, reviews and sprints use initiative prefixes. Select the intended
component in a multi-component project, and name the initiative when several exist.

With connected documents, keep one canonical store and preserve artifact IDs.
Uploads are snapshots. Without a save tool, outputs say **prepared, not saved to
the canonical store**. Independent convergence is reported only for isolated
reviewers; persona simulations always remain synthetic. Story status `ready`
means manually planning-ready, not an enforced completion gate.

## Optional local helper

The skills normally invoke it for you. To run it directly, replace
`/path/to/delivery` with the package directory and `/path/to/project` with an
existing project directory:

```sh
python3 /path/to/delivery/scripts/project.py init --project /path/to/project --initiative checkout-redesign
python3 /path/to/delivery/scripts/project.py status --project /path/to/project
python3 /path/to/delivery/scripts/project.py words /path/to/project/.delivery/initiatives/checkout-redesign/brief.md
```

`init` creates directories only and preserves artifacts. `status` returns a
read-only inventory, not a verification verdict. `words` counts prose excluding
initial YAML, fenced code, pipe-prefixed tables and HTML comments. Results are
JSON. Path conflicts, ambiguous nested workspaces and symlink paths are refused;
select the correct workspace instead of creating a shadow copy.

## Current limits and planned capabilities

The coordinator records persistent roles, peer work, native controls, version-bound
tools, recoverable artifact saves and controlled workflow evidence. Canonical
Beads tasks are accepted only after exact current-scope operator attestation.
Changed criteria, commits or evidence invalidate previous submissions. Native
command/file escalation cannot widen a protected worker lane. No plugin hooks,
automatic merge, push or deployment are enabled. CI/host evidence is explicitly
operator-attested, not advertised as automatic external verification.

See [local runtime setup](references/team-runtime.md) for roster, dependencies,
operator terminal, recovery controls, explicit judge configuration and boundaries.
An optional [external supervision seam](references/supervision.md) lets a trusted
host submit scoped agent assignments to that same dispatcher. Its fake-transport
tests do not establish a supported dot/ChatGPT integration; host authentication
and actual host qualification remain prerequisites.
The [command evidence helper](references/verification.md) records exact-commit
review and revision-bound surface checks without granting task acceptance.
A bare JSON file cannot provide human approval. Protected judging needs matching
provider-specific calibration; sample evaluations are not installed as defaults.

The current planning workflow requires no MCP server. A future custom MCP
integration would need a running service: locally for Codex, or reachable from
ChatGPT through HTTPS or a supported tunnel. The local server/client must remain
available when using a tunnel. This package installs no server or tunnel. See
OpenAI's [skills guidance](https://developers.openai.com/plugins/build/skills)
and [MCP documentation](https://learn.chatgpt.com/docs/extend/mcp?surface=cli).

## Validation and provenance

CLI 0.159.3 passed isolated installation and discovery of the 15 skills. The
new product skill increases the current source to 16; that historical installed
snapshot does not include it. CLI 0.163.0 passed a fresh isolated installation and
discovery of all 16, plus the installed product helper's greenfield record/handoff
with unconfirmed choices retained. Those checks made no model calls. Fresh native
model invocation remains unqualified: startup failed in the managed test
environment before inference. Desktop and ChatGPT acceptance remain separate.
The
planning preview also passed three selected-skill real-model file workflows.
Runtime validation includes native thread persistence across coordinator restart,
a native shell test denying a planning-file write while allowing a worktree
write, and bounded live classifications from both Jev and OpenAI. Workflow and
operator tests include real local Beads/Git fixtures and synthetic terminal input.
These are targeted checks, not desktop/ChatGPT acceptance or a reliability claim.

Adapted under MIT from [Claude delivery](https://github.com/colombod/ai-augmentation-systems/tree/main/plugins/delivery).
The imported baseline is version `0.30.0`, pinned at
[`df0c0a5`](https://github.com/colombod/ai-augmentation-systems/tree/df0c0a5b0dba1449b6cdfef421bfe1ebc4d658c0/plugins/delivery).
See [CHANGELOG](CHANGELOG.md), [NOTICE](NOTICE), [upstream.json](upstream.json)
and [LICENSE](LICENSE). The source revision and per-file hashes support future
upstream comparisons; new Claude features are reviewed and adapted deliberately,
not automatically inherited. No Claude installation or checkout is required at runtime.

Completed retirement recording is an unshipped preview capability: use
`retire-record --feature ID --input outcome.json --expected-sha256 DIGEST` only
after separately authorized actual work. The [product contract](references/product.md#record-a-completed-retirement)
defines current tracked evidence, preserved prior anchors/history, survivor checks
and resumed handoffs. Submitted decision/review text authenticates no approval or
independent verification; the helper performs no retirement or deletion.
