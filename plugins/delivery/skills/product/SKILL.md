---
name: product
description: Frame a greenfield idea or onboard a brownfield project into one evidence-bound product record. Connect customer promises to planned or observed code, check freshness and feature impact, carry owner choices forward, and prepare safe retirement proposals.
---

# Product first, for ideas and existing work

Read [host capabilities](../../references/runtime.md), [conventions](../../references/conventions.md)
and the [product contract](../../references/product.md). Use this before PRD or
roadmap work when the owner needs a product boundary, a baseline, or a feature-side
impact answer. Greenfield and brownfield are equal paths, not maturity scores.

Resolve the actual project/component and canonical record. Inspect existing
`.delivery/` records and source documents before writing. Reuse them; never reset
unfinished work or silently overwrite an owner's decisions. Initialize directories
through `project.py init` only when the user has authorized the named initiative.
Without local tools, provide a labelled unsaved record using the same contract.

## Start with the job and the owner's lens

From the user's own words, capture one primary customer, recurring job, current
cost (or unknown), proposition and before/after outcome. Reflect their examples
and reasons: what matters, what must survive and what may be cut. Keep stated
intent separate from your proposed interpretation; ask only what changes the next
decision. A delegated run may continue with proposed choices, but cannot call
them confirmed. Preserve the rejected alternative, reason and revisit condition.

Choose the smallest useful work form. Keep form, autonomy and engine separate.
Use the Right Shape scales/gates in the product contract; unknown critical gates
conservatively cap autonomy. A local deterministic command plus host instructions
often suffices; do not add an agent/service merely because the package supports one.
Record an observable next slice, its done-when check and what is deliberately cut.

## Greenfield: make a coherent first promise

No product repository is required. Read supplied notes and existing plans. Create
planned features with empty `code` arrays, `commit: null` and explicit unknowns.
Describe a first end-to-end customer journey before expanding the requirements.
Use `mode: greenfield`. Do not invent source paths, customer observations or a
deployed product. When code exists, transition the same stable feature IDs to a
brownfield snapshot; do not create a second product ledger.

## Brownfield: distinguish what exists from what is promised

Run the read-only source census:

```sh
python3 <plugin-root>/scripts/product.py --project <planning> --repo <product-git-root> inspect
```

Read project instructions, README, relevant entry points, manifests, tests,
architecture/ADRs and accessible release evidence. Reconcile current Git changes,
known branches/PRs and existing backlog with actual access; do not invent an
import or infer completion from task names. The census finds candidate paths,
not features. Curate customer-visible promises and distinguish shipped, preview,
planned and historical retired features. Source existence alone proves neither
installation nor deployment. Link regular tracked code/evidence files at the
exact named commit; explain the evidence boundary beside each claim. Shared
files may support several features. State what was not inspected.

## Record, use and hand over

Draft the input from [the packaged starter](../../templates/product-input.json).
The starter is schema guidance, not an observation or a task to build. Fill its
customer choices, paths, six usefulness judgements and shape reasons from actual
inputs. Save with an expected hash, then query:

```sh
python3 <plugin-root>/scripts/product.py --project <planning> record --input <curated-input.json> --expected-sha256 new
python3 <plugin-root>/scripts/product.py --project <planning> handoff
```

For brownfield add `--repo <product-git-root>` before the subcommand. Use the
reported SHA for updates. `record` preserves previous versions and feature IDs.
Read `status` before relying on the map and `impact --path <file>` before edits.
Report unknown/unmapped coverage, changed raw bytes and stale commits prominently.
Never describe this curated file index as a transitive dependency graph.

Keep Job, First value, Fit, Outcome, Trust and Return separate, each with rating,
evidence grade, source and next check. Never average them. Source inspection,
tests and our own walkthrough remain Claimed, not Seen outside-user evidence.
Unknown Return is a validation gap, never a retirement recommendation.

For subtraction run `retire-plan --feature <id>`. Inspect its shared-code warnings,
usage uncertainty and migration/rollback needs. Take the concrete proposal to the
user. No helper performs retirement or deletion; a proposal grants no authority.

Hand over the saved record/revision, observed vs proposed states, owner choices
and unconfirmed decisions, usefulness gaps, shape/engine/authority, and one bounded
next result. Pass this context into brief/PRD/architecture and sprint review;
do not force a complete planning pipeline when the next step is already clear.
