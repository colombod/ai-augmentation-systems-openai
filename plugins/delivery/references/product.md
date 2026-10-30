# Shared product contract

One `.delivery/product-map.json` records the customer promise and its features.
It works for an idea with no Git repository and for an existing codebase. Per-
initiative briefs/PRDs/stories remain where the conventions place them; this
project-wide baseline links the context they must preserve. Existing artifacts
and backlogs remain authoritative in their original stores. This is not an
automatic GitHub/Jira importer, authenticated decision service or deployment index.

## Commands and persistence

Use Python 3.10+ and the package's `scripts/product.py`. Global arguments precede
the command: `--project <planning>` is always required; `--repo <git-root>` is
required for brownfield code mapping and unnecessary for a greenfield idea.

| Command | Result |
|---|---|
| `inspect` | Read-only candidate docs/manifests/tests and current source commit, or existing concept artifacts without a repo |
| `draft --outline FILE` | Expand compact notes into complete input JSON on stdout; no canonical write or evidence upgrade |
| `record --input FILE --expected-sha256 new` | Validate curated JSON and save a new product record; use the reported digest for later updates |
| `status` | Feature states, exact source revision and raw-byte/mode freshness |
| `impact --path FILE [--path FILE] [--transitive]` | Direct curated links; optional possible Python import reach, shortest file/line chains and coverage limits |
| `handoff` | Product choices, separate usefulness cards, shape calculation and unconfirmed choices for next work |
| `retire-plan --feature ID [--transitive]` | Read-only proposal: shared code to preserve, exclusive candidates, unknown human decision and migration checks |

`project.py init` creates directories first. Record updates use a local file lock,
expected digest and atomic replacement. Prior complete bytes are retained in
`.delivery/product-map-history/<sha256>.json`. This is a local concurrency guard,
not a distributed transaction. Helpers never edit source, reset Git, install
hooks, select a model, contact a service or delete features. Exit codes: 0 for a
valid command, 1 for stale source or unconfirmed handoff choices, 2 for invalid
input/conflict. A concept has no code freshness verdict (`fresh: null`).

## Start with compact notes

You need not fill the full starter by hand. For a no-code idea, an outline can be:

```json
{
  "product": {
    "customer": "Maintainer considering a local change check",
    "proposition": "Get one useful result before adding an agent"
  },
  "features": [{"id": "first-result", "name": "One local result"}]
}
```

Run `product.py --project <planning> draft --outline notes.json` and save stdout
as a draft input file. For brownfield, add `--repo <git-root>` and supplied feature
`code` paths and `evidence` paths; the helper checks them at HEAD. For example:

```json
{"features": [
  {"id": "workspace", "name": "Initialize the planning workspace",
   "code": ["plugins/delivery/scripts/project.py"],
   "evidence": ["tests/delivery/test_project.py"]}
]}
```

Outline features require `id` and `name`; optional keys are `summary`, `state`,
`code`, `evidence` and `unknowns`. Evidence may be a path or a full path/note object.
Feature state defaults to planned even when code exists. All six usefulness
ratings and grades start Unknown. These conservative defaults are deliberate:
the author/agent must still inspect behaviour, releases and outside-user evidence.
Unknown keys are rejected rather than silently dropping a misspelled code field.

Optional `product` notes use the full contract's keys. Plain strings become
proposed decisions; attribution is not fabricated. Existing full decision objects
and a fully assessed `right_shape` may be supplied explicitly. Without a shape
assessment, draft uses an explicitly unassessed tool/None-engine placeholder at
autonomy zero, with unknown gates. This is not a recommendation for the eventual
product. Review it before architecture or execution.

Draft only prints a complete, recordable input. It never overwrites the map,
confirms an owner or bypasses expected-hash recording. Review and save that input
using `record`; previous product choices should be carried forward explicitly
when updating rather than replaced by a new sparse outline. The agent still
discovers feature promises and selects routes; draft removes repetitive JSON,
not the need to understand the project. No symbol graph or model service is added.

Saving requires an actually authorized writable host session. Native Delivery
manager roles remain read-only; they can read a prepared product record but do
not gain a new protected artifact target from this helper. Prepare/update it in
the authorized host session, or return an unsaved draft. Never expand a worker
lane or bypass the existing artifact policy to make this command write.

Use [product-input.json](../templates/product-input.json) as the complete input
shape. Feature IDs persist; no silent removal. `state` is a curated claim:
`shipped`, `preview`, `planned` or `retired`. A shipped label still needs actual
release/host evidence. A source inspection cannot upgrade it. Greenfield records
have `mode: greenfield`, `commit: null`, planned features, absent code and evidence
notes with `path: null`. Brownfield records require an exact full commit; every
code or evidence path must exist there as a regular file. Symlinks/submodules are
unsupported. An evidence note explains what its file establishes and what it does
not. Non-file evidence may retain `path: null` with its source/limitation in `note`.

Freshness compares raw bytes and executable modes, independent of Git index flags
and size/mtime shortcuts. Commit mismatch stays visible even if mapped bytes did
not change. Unmapped files, dynamic wiring and external consumers remain unknown;
a fresh curated map is not a complete graph. Impact is direct file-level coverage,
not transitive blast radius. Query results never authorize edits or removal.

## Optional dependency-side impact

Add `--transitive` to `impact` or `retire-plan`; no registry migration, extra
service or package is required. Direct fields keep their existing meaning. The
separate `transitive` result follows possible Python imports from the same curated
feature `code` anchors at the **recorded full commit**, using a shortest breadth-
first chain with `from`, `to`, `line` and `kind`. Multiple features reaching a file
are shared consumers. It reads Git blobs without importing/executing project code.

This first slice supports Python AST imports in conventional sibling/repository/
`src` roots and regular package initializers. It does not resolve installed
packages, namespace/custom import contexts, custom `sys.path`, dynamic loaders,
other languages or semantic calls. Conditional/function-local imports are possible
reach, not proof that a runtime path executes. Curated Python module anchors also
include possible enclosing regular-package initializer reach, even with no import
statements in the anchor. These `python-package-initializer` edges use `line: null`:
tracked ancestry is the evidence, not a fabricated import location. This assumes
a possible package-import context; standalone script execution may not run those
initializers. Missing/unsupported enclosing package context stays explicit in
`anchor_package_context_unknown`; namespace/custom contexts remain unsupported.
Ambiguous paths, unresolved/external
imports, unsupported source/initializer modes, parse/size failures and recognized
dynamic loaders are reported even inside otherwise analyzed files. Files outside
anchor reach are uninspected. A smaller unresolved list never proves completeness.

Graph freshness also checks raw bytes/modes of reached dependencies, including
files not directly anchored. Its commit and stale result remain separate from the
existing direct-map freshness. Stale graph results return exit 1; unavailable
optional analysis reports `available: false` and a reason while retaining direct
results. Greenfield planned code has no dependency graph. This is informational
reach: neither missing analysis nor a graph verdict sets or blocks story readiness.

Derived retirement exclusivity means **candidate only**, never deletable or proof
of no unknown consumers. Preserve shared reach, inspect unresolved/external and
unsupported consumers, retain history, and obtain the exact owner decision plus
replacement/migration/rollback review already required below. No command deletes
code, changes a feature's state or widens execution authority.

## Owner choice before expansion

Record one customer, job/problem, current cost or unknown, one proposition,
before/after, riskiest assumption, what must survive, explicit cuts and one next
slice with done-when checks. Every choice retains `text`, `basis`, `source` and
`revisit`. Basis is `owner-stated`, `proposed` or `unknown`. Attribute actual user
words; do not turn inferred preferences into human decisions. This ledger stores
submissions, not authenticated approval receipts. Product owners retain judgment.

Brief and PRD consume the record when present. Carry confirmed constraints and
cuts forward; unresolved customer/proposition/preservation choices stay explicit.
Gather only decisions needed for the next consequential step. Existing user
authorization takes precedence over generic confirmation advice. A small change
does not need an elaborate coaching session. At most two taste/refinement rounds
by default; repair unknown/failed correctness, accessibility, safety and feasibility
gates before adopting polish. Preserve the baseline and a rollback/revisit reason.

## Six usefulness judgements, no total

| Criterion | What to inspect |
|---|---|
| Job | Named user, setting, recurring problem and cost |
| First value | One real outcome with their own input, alone in their first session |
| Fit | Existing tools, inputs and habits; setup friction |
| Outcome | A changed result the user would name |
| Trust | Visible limits, failure and recovery |
| Return | Unprompted repeated use, or the next dated return check |

Each row independently records `rating` (Unknown, Missing, Partial, Solid),
`grade` (Unknown, Claimed, Seen, Repeated), `evidence` and `next_check`.
Claimed includes builder statements, source/test inspection and AI demonstrations.
Seen requires a specific observed/reported use by someone outside the team.
Repeated requires evidence of unprompted return. Never upgrade evidence from
confidence, source availability or our own test run. No aggregate score or automatic
readiness label is computed. Contradictory or missing evidence remains visible.

## Right Shape, separate from usefulness

The source method separates form, autonomy and engine. Need dimensions N1–N4 are
0–3: path (one step/fixed steps/listable branches/open-ended), context load
(tiny/fits main window/crowds it/needs isolation), duration (instant/minutes/hours/
ongoing), initiative (asked/scheduled/events/self-starting). The sum maps to the
source rungs: 0–1→1, 2–3→2, 4–5→3, 6–7→5, 8–9→7, 10–12→8.
This sum concerns autonomy need, never the six usefulness judgements.

G1 verifiability caps at 5; G2 irreversible effects without approval caps at 6;
G3 private-data/untrusted-input/outbound-channel trifecta not broken caps at 5;
G4 isolation caps at 6; G5 enforced time/token/money budget caps at 7; G6 accountable
ownership caps at 6. Record pass/fail/unknown with reasons. Unknown applies the cap
conservatively. Maximum rung is the lesser of need and lowest failed/unknown cap.
The helper checks arithmetic only: it cannot prove a safety gate or authorize an
autonomy level in the host. Choose a lower level whenever sufficient.

Record form (tool, smart-tool, skill, workflow, subagent, agent or harness), engine
(None for deterministic, LLM, Decision model, Both), reason, rejected/smaller
alternatives, selected `autonomy_rung` (0–9) and a benchmark/stop rule. The selected
rung must not exceed the computed maximum; it grants no permission in the host.
A package is distribution, not a reason to
create an agent. Prefer deterministic execution where adequate; taste remains
human judgment, not a decision model score. Include a planted trap, a leave-alone
case, a stopping check and real work. A benchmark is proposed until actually run.

## Retirement is a decision, not a low rating

`retire-plan` performs no deletion or status transition. It lists code directly
shared with surviving features, which must be preserved. Exclusive listed paths
remain candidates, not proof of no other consumers. Inspect external/transitive
consumers, present usefulness/usage unknowns, a replacement or explicit no-replacement
choice, migration, rollback and retention of history. Get an explicit user decision
on that exact proposal before separately authorized implementation. Unknown Return
and a model's preference are not permission. Historical retired features can be
recorded as facts with evidence; this command does not authenticate that history.

## Method sources and limits

Adapted compactly from [Worth Using](https://github.com/michaeljabbour/amplifier-skill-worth-using/tree/15760599596a5ceffb998a119174cd2ce84e42b6),
[Market Fit](https://github.com/michaeljabbour/amplifier-skill-market-fit/tree/1a16404f20babb1832cda117e162ebe6020b7e6d),
[Taste × Elegance](https://github.com/michaeljabbour/amplifier-skill-taste/tree/e13b717541a813a7e05fd2eb6868da1d66b6591a),
[Sizzle](https://github.com/michaeljabbour/amplifier-skill-sizzle/tree/d7aa28736f63de65aaac18dabc838533be103b40),
[Decisioncraft](https://github.com/michaeljabbour/amplifier-smart-tool-decisioncraft/tree/153342d5bac385f38fdf41c58e58cddb2a147df7),
[Right Shape](https://github.com/michaeljabbour/amplifier-skill-right-shape/tree/181fb2da453558935ae9da615442f08cb93f52ea),
and [Trail-Code](https://github.com/trailhq/Trail-Code/tree/a44da3dfb5894c8e316e320526041ef8e5ddbb8c).
Full source MIT notices are retained under `references/sources/`.

This adaptation carries customer/choice/evidence practices into Delivery; it does
not install these products or claim their complete coaching, film-production,
canvas, symbol graph or benchmark capabilities. Decisioncraft informs current vs
proposed states, evidence and proportionate gaps; Sizzle informs one proposition
and a clear journey before expensive production. Their runtime dependencies and
approval machinery are not copied. No independent-review claim comes from one
model adopting several perspectives. Source benchmarks and real adoption require
their own dated evidence; portable instructions do not establish host enforcement.
