---
name: product
description: Frame a greenfield idea or onboard a brownfield project into one evidence-bound product record. Connect customer promises to planned or observed code, check freshness and feature impact, carry owner choices forward, and prepare retirement proposals and record submitted completed outcomes.
---

# Product work at the depth needed

Read [the common contract](../../references/core.md), including its single source-
reuse rule. Do not assume a catalogue entry loads this full skill or its links.

## Focused read-only map question

For inventory, freshness or direct file impact, resolve the project/component and
canonical store with the common rules, then run the matching command:

```sh
python3 <plugin-root>/scripts/product.py --project <planning> --repo <product-git-root> status
python3 <plugin-root>/scripts/product.py --project <planning> --repo <product-git-root> impact --path <file>
```

`impact` already includes freshness; do not also emit a full status/handoff.
For a greenfield idea omit `--repo`; planned features have no code-freshness
verdict. Without tools read the identified snapshot and mark freshness unverified.
If no map exists, report that; do not invent one or initialize/interview/rewrite
merely to answer the query. Offer authoring only when wanted.

Report relevant promises/paths, snapshot/current commit, changed bytes, shared
consumers and unmapped uncertainty. This is curated direct file coverage, not a
complete dependency graph or proof of shipping/adoption. Preserve owner choices
and findings; consult relevant evidence/glossary entries only as needed. Do not
load authoring templates, budgets or coaching for this path.

If dependency reach is wanted, add `--transitive` and consult the product
contract's optional dependency-side guidance: possible Python imports/initializer
reach at the recorded commit, shortest evidence chains and explicit uncertainty.
Implicit initializer edges have no invented line. This is not a semantic graph.

## Create, assess, change choices, hand off, or plan retirement

Read [the product contract](../../references/product.md). Consult
[runtime](../../references/runtime.md) for the actual host/persistence/provider
boundary and [conventions](../../references/conventions.md) for the language and
writing sections needed by the artifact. Expanded guidance is action-dependent.

1. Read existing records, plans and accessible backlog first. Preserve unfinished
   work; initialize a named initiative through `project.py init` only when authorized.
   Apply owner intent, customer/proposition/cuts, usefulness and Right Shape from
   the contract; retain rejected choices and revisit reasons.
2. Greenfield: supplied notes become planned features, `code: []`, `commit: null`
   and explicit unknowns. Describe one first customer journey; no repository needed.
   Brownfield: run `inspect`, then read relevant README, entry points, manifests,
   tests, ADRs and release evidence. Reconcile accessible Git changes/PRs/backlog.
   The census finds candidate paths, not features. Curate promises at an exact
   commit and state gaps; source presence does not prove release. Keep stable IDs
   when an idea gains code rather than opening another ledger.
3. Start with `draft --outline <notes.json>` from compact feature/product notes as
   the product contract describes. It expands input without saving, confirming
   choices, grading usefulness or inferring shipped status; missing judgements
   stay Unknown and plain notes proposed. Inspect the result. Use
   [the full template](../../templates/product-input.json) when detailed control
   is needed. `record --input <file> --expected-sha256 new` creates it; use the returned
   digest for updates. Add `--repo` before the command for brownfield. Inspect
   `status` or `impact` before relying on code; do not hide stale/unknown coverage.
4. Use `handoff --feature <id>` to resume one exact capability with its full
   feature context and all global owner/product, shape, authority, unconfirmed
   choices and freshness context. Selection scopes display only; other features
   remain canonical and stale unselected evidence stays visible. Empty/unknown
   IDs fail; no permissions or confirmations are inferred. Omit `--repo` for a
   no-code greenfield selection. Use full `handoff` when passing all feature
   context: saved revision, observed versus proposed states, owner choices,
   usefulness gaps, shape/authority and one bounded next result. Carry it into the
   next relevant phase without forcing a full pipeline. For
   `retire-plan --feature <id>` (optionally `--transitive`), use the contract's
   shared-code, usage, replacement/migration/rollback and explicit-human-decision
   checks. After separately authorized actual work and outcome verification, use
   `retire-record --feature <id> --input <outcome.json> --expected-sha256 <digest>`
   as the contract specifies. Preserve prior anchors/history and unknown consumers;
   submitted decision references authenticate nobody. Resume the retired feature
   through selected handoff and realign actual state and evidence.

## Choose and deliver one useful next change

For onboarding gap disposition, evidence-led next-work selection and a small
change through authorized shipping, follow [the bounded-change route](../../references/bounded-change.md).
Keep observed, planned and deferred distinct with IDs, reasons and next actions;
agent judgment is permitted but owner confirmation must never be invented.
This route also applies to no-code greenfield work and does not force full-pipeline documents.
