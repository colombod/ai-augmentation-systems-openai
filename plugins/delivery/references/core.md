# Common workspace, authority and source rules

Read actual project instructions and AGENTS.md before resolving or operating on
artifacts, then the selected skill's full body, not just catalogue metadata.
User/project instructions take precedence; links are not granted capabilities.

## Source loading and reuse

Load references needed for the action. Reuse requires the exact body still visible
and either a matching current content hash or verified immutable package snapshot
identity. An unchanged Git HEAD, branch, version label,
path or mtime in a mutable checkout does **not** establish unchanged files. If you
cannot verify content/snapshot identity, reread. After compaction, missing text or
source changes, reread the selected skill and needed references/cited artifacts.
A summary is not their contents. Keep source identity in the handoff; no new cache
or memory ledger is required.

## Capabilities, preservation and evidence

- Identify the actual project/artifacts, authorized read/write tools, shell/Python,
  search and delegation. A role/skill name launches nothing and grants no write,
  acceptance, merge or deploy authority. Missing access means unavailable/manual/
  unsaved, never simulated success. Do not install a service to make planning work.
- Keep one canonical store and stable IDs/history. Preserve unfinished work, owner
  choices, evidence, failures and cuts. Resolve concurrent edits with expected
  revisions/hashes; never silently overwrite. Uploads are identified snapshots,
  not live state. Missing prerequisites remain unsatisfied; obtain actual inputs.
- Cite source/evidence at its observed revision. Distinguish inspection, stub
  tests, real commands, model tests, host captures and outside-user use. CLI proof
  needs actual output/exit; GUI/TUI claims need an inspected visual capture. A local
  test cannot prove an inaccessible host, deployment or adoption. Stale/unmapped
  coverage stays unknown. Do not fabricate evidence IDs, live roles or consent.
- Preserve owner intent and what must survive; separate owner statements, proposals
  and unknowns. Ask only what changes the decision. Neither a model nor attributed
  JSON authenticates permission. Retirement proposals grant no deletion authority;
  preserve shared consumers and require a concrete human decision before separately
  authorized implementation. Unknown Return does not justify retirement.
- Greenfield and brownfield are equal paths. Verify existing code where available;
  with no code keep planned features/code absence explicit and future paths/commands
  proposed. No requirement to create the files before designing their creation.
- Our own source/tests/demo are not Seen outside-user use; simulations are labelled
  synthetic. Use existing domain terms and clarify consequential ambiguity. A
  read-only map query need not create a glossary, plan or initiative.
- Lenses are instructions, not agents. Use isolated read-only reviewers with raw
  inputs only when delegation is available/authorized; otherwise label sequential
  passes single-session review. Missing required independence stays incomplete.
  No provider fallback, policy change, hook bypass or worker-lane expansion follows
  from missing capabilities. Planning readiness is no execution/acceptance gate.

## Where `.delivery/` resolves to

The filesystem rules apply only with actual local access; otherwise use the
explicit canonical document store/snapshot and preserve the same IDs/namespaces.
Without writes return a labelled unsaved export, never claim initialization.

Not necessarily the repository root. Resolve before reading or writing any artifact:

1. **Reuse.** Reuse the nearest existing ancestor `.delivery/`. If there is instead a nested component workspace, select that component explicitly; never create a second one beside it. The helper refuses ambiguity instead of picking a sibling.
2. **Explicit override.** Otherwise honor a delivery-root path stated in the nearest `AGENTS.md`.
3. **Ask, don't guess.** Otherwise, if this repository holds more than one independently-releasable component (multiple `package.json`/`plugin.json`/`pyproject.toml`, workspace members, or similar) stop and ask which component this work belongs to. Silently defaulting to the repo root in a multi-component repo is the failure this step exists to prevent.
4. **Default.** Otherwise, use `.delivery/` at the repository root. Without a
   repository, use the explicitly selected planning directory/store.

## Which initiative

Initiative planning artifacts live under `.delivery/initiatives/<slug>/`, never directly under
`.delivery/`. The shared `product-map.json` remains project-wide and querying it
does not require selecting or creating an initiative. Namespacing is what lets independent initiatives (epics, sprints, parallel
workstreams) be planned in parallel branches without colliding on the same shared file
(`ADR-004`; the incident that motivated it: two initiatives independently continued the same
`S-n`/`FR-n` sequence in one shared `prd.md`, discovered only at merge). Resolve which
initiative before reading or writing initiative artifacts:

1. **Explicit signal.** The user names an initiative, or one is already established for this
   conversation — use it.
2. **Exactly one exists.** If `.delivery/initiatives/` has exactly one subdirectory, use it
   without asking — this keeps single-initiative projects exactly as simple as before this
   convention existed.
3. **Ask, don't guess.** Otherwise (zero, or more than one, with no explicit signal) — ask
   which initiative this work belongs to, or whether to start a new one. Never silently
   default to the most recently modified one.
4. **Starting a new initiative.** Confirm its slug (kebab-case, derived from the brief
   subject or what the user names) before creating `.delivery/initiatives/<slug>/` — check it
   doesn't collide with an existing initiative slug or any other top-level `.delivery/` entry.
   A genuinely new initiative needs its own `$delivery:brief`, or an explicit
   `extends: <existing-slug>` note (in this new initiative's own first artifact) declaring it
   reuses an existing initiative's problem framing instead of running its own — state which,
   don't leave it implicit.

Cross-cutting, project-wide, never per-initiative: `.delivery/glossary.md`,
`.delivery/personas/`, `.delivery/interviews/`, `.delivery/simulations/`,
`.delivery/decisions/ADR-NNN-*.md`. This preview has no invocation ledger.
`.delivery/stories/`, `.delivery/reviews/`, `.delivery/sprints/` stay flat but are prefixed
by initiative slug, matching `stories/<slug>-NN-<name>.md`'s existing convention.

## Open blocking findings

Before progressing planning, read relevant `.delivery/reviews/` findings against
consumed artifacts. An `open`/`blocking` finding stops progress: report it. Resolve
as `fixed`, or `rejected` with recorded reasons, or obtain and record the user's
explicit choice to proceed. A read-only query may report blockers without changing
them. Never silently carry a known blocking defect into downstream plans.

For host-specific operation use [runtime](runtime.md); for artifact language,
glossary curation and prose budgets use [conventions](conventions.md). Product
choices, six separate usefulness judgements and shape/retirement details live in
[the product contract](product.md), loaded for authoring rather than a map query.
