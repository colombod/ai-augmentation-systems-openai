---
name: product
description: Frame a greenfield idea or onboard a brownfield project into one evidence-bound product record. Connect customer promises to planned or observed code, check freshness and feature impact, carry owner choices forward, and prepare safe retirement proposals.
---

# Product work at the depth needed

Read [the core contract](../../references/core.md) before this action. If the host
showed only catalogue metadata, open this full selected skill first; do not assume
that any linked body is already loaded. Reuse a reference only with its exact text
still visible and an established unchanged path/revision or content hash. Re-read
after compaction, changed source/package, lost context or unverifiable revision.
Never substitute remembered summaries for source or rules.

## Focused read-only map question

For existing feature/code inventory, freshness or a proposed file's direct impact,
stay on this path. Resolve the actual project/component and canonical store using
the core rules. Do not initialize a workspace, start an owner interview, rewrite
plans or create a glossary merely to answer a read-only question.

```sh
python3 <plugin-root>/scripts/product.py --project <planning> --repo <product-git-root> status
python3 <plugin-root>/scripts/product.py --project <planning> --repo <product-git-root> impact --path <file>
```

Run the one command matching the question; `impact` already includes freshness,
so a separate full status/handoff is unnecessary. Without tools, inspect the
identified map as a snapshot and state current code freshness unverified. For a
greenfield idea, omit `--repo` for status; planned features have no observed code
or code-freshness verdict. If the map/store is absent, say so and offer the
authoring path only when wanted. Do not invent a feature map from memory.

Report relevant feature promises/paths, snapshot/current commit, changed bytes,
shared consumers and unmapped uncertainty. A curated file map is not complete or
transitive; unmapped is unknown, never permission to remove. Source availability
is not proof of shipping, deployment or outside-user use. Preserve owner choices
and findings; read relevant source/evidence or glossary entries only when needed
to resolve the question. A query does not need a new initiative for a project-wide
map. Do not load authoring budgets, scoring/coaching or templates for this path.

## Create, assess, change choices, hand off, or plan retirement

Read [the product workflow](../../references/product-workflow.md),
[product contract](../../references/product.md), and the relevant host/persistence
and writing sections of [runtime](../../references/runtime.md) and
[conventions](../../references/conventions.md). Their constraints remain active;
unchanged visible resources need not be fetched repeatedly. The workflow covers
equal greenfield/brownfield entry, owner intent, customer/proposition/cuts,
separate usefulness judgements, Right Shape, safe recording and retirement
proposals. Load its template only when producing that input.

Use the full `handoff` only for a requested planning/owner-context handoff. For
retirement, preserve shared-code/value evidence and pending replacement,
migration, rollback and usage decisions. A proposal never authorizes deletion.
Native read-only roles gain no write lane from loading instructions. Missing
host execution or authentication remains unavailable, never simulated success.
