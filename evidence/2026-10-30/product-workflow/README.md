# Product workflow: ideas and existing work

Base: `028edf7be69044e90f67f8899527a1728a575ce6`.
First implementation: `f2e2b1ffa76a5754b7ed0acc63e99878efd13d0d`.
Final helper implementation and demonstrated source snapshot:
`812d85e4297e316045edb44f230c6b09fb7ab092`.

This increment is independent of the optional supervision work in PR #1, which
remains open and unchanged. No Anthropic work, other plugin implementation or
user business workflow was changed. No external software, model or credentials
were installed. Beads/Dolt are unavailable, so contributor task tracking could
not run; no replacement task ledger was created.

## What a user can do now

The package adds `$delivery:product` and a standard-library `product.py` helper.
Greenfield and brownfield share the same product record and planning handoff.
Greenfield works without Git; its features remain planned with no code links.
Brownfield curates observed features at a full source commit and checks actual
file bytes/modes, including staged changes and index-hidden modifications.
Product choices and six separate usefulness/evidence judgements travel into
existing brief/PRD/design/architecture/review/status skills. There is no total
usefulness score, automatic owner confirmation or automatic deployment claim.

From an installed checkout, examples are in `plugins/delivery/README.md` and
the packaged `references/product.md`. Basic planning needs the host's existing
model access; helpers need Python and, for brownfield code, Git. No service,
Trail installation, Amplifier runtime or separate judge is necessary.

## Actual local acceptance

Reproduce using a new output directory:

```sh
python3 scripts/product_workflow_acceptance.py --repo /absolute/checkout --output /absolute/new-evidence-directory
```

The script drives the **public package commands**, not private library functions.
`final-case/` contains inputs, canonical records and every command's stdout,
stderr and exit code. The earlier successful `case/` run is retained separately
at its earlier implementation revision. Every run has 11 commands.

Brownfield uses this actual Delivery source, not a toy codebase. It records seven
curated **preview** features; it does not infer that source preview is shipped or
deployed. Hook-event-log is explicitly outside the selected component coverage.

Real impact question: **Before changing workspace resolution in
`plugins/delivery/scripts/project.py`, what capabilities need checking?**

The source-bound answer identifies six mapped capabilities:

| Capability | Why it is in this direct file map |
|---|---|
| Workspace initialization/inventory | The helper implements it |
| Existing planning/review workflows | Skills use the helper/canonical root |
| Product baseline/impact/handoff | New helper reuses canonical root resolution |
| Native team coordination | Runtime imports and uses project/root helpers |
| Canonical artifact saves | Artifact paths depend on project/root checks |
| Controlled workflow/review | Runtime's planning root binds the controlled operations |

The retirement proposal for the standalone workspace capability preserves the
shared file for the other five consumers and offers **no exclusive deletion**.
No feature is retired and no source is deleted. This is direct curated coverage,
not a complete call graph or proof of no additional consumers.

Greenfield uses an **illustrative**, explicitly unvalidated local-plugin idea.
It records one planned outcome with absent code, no Git repository and no invented
commit. Its handoff retains the same customer/promise/cuts/usefulness/shape contract.
This is command conformance, not proof that a real customer wants that idea.

Both records preserve the user's actual decision: "Brown field and green field
are equally important" and the instruction to drive to completion and value.
Inferred primary customers, propositions and cuts remain **proposed**. Handoff
exit `1` deliberately exposes those unconfirmed choices, rather than fabricating
approval. Our inspection/command runs remain **Claimed** usefulness evidence;
Return remains Unknown. No outside-user Seen/Repeated evidence is claimed.

These retained maps are snapshots at the named implementation commit. Adding
evidence commits advances HEAD; a later status correctly reports that difference.
Re-record against the intended current source revision, with the current map
digest, when refreshing a live workspace. Do not rewrite the historical outputs
to make them look current. Keeping the planning record outside the product Git
checkout avoids self-generated metadata commits invalidating the source pin;
the helper does not alter ignore rules or Git configuration automatically.

## Verification and independent review

`checks/python-tests.txt`: 138 Python tests passed, including 16 new product
behaviour tests and one source/licence packaging check. `checks/node-tests.txt`:
22 provider-fake tests passed. `checks/marketplace.txt`: both packages validated.
`git diff --check` passed. No new live judge or native model calls were made.

Independent read-only code/architecture review reproduced and verified fixes for:
historical retired features misclassifying surviving shared code; missing staged
add/delete/rename paths; writer/reader record-size mismatch; and acceptance of
corrupt prior history. Regression tests now cover each case. One first regression
run failed because Git rename detection omitted a removed path in name-only
output; explicit `--no-renames` fixed both census and freshness reporting. Failed
observations were not treated as passing evidence.

Final review independently reran all 138 Python tests, marketplace validation and
diff checks, then inspected the actual-repository/greenfield command outputs. No
remaining concrete blocker to PR review was found. The final documentation-only
changes connect status and clarify installed-version qualification.

## Deliberate boundaries and next proofs

This is a usable first increment, not completion of every named source product.
The adaptation records pinned methods and full MIT notices; it does not bundle
their complete coaching modes, film production, Decisioncraft canvas, Trail
symbol graph, model routing or Amplifier infrastructure.

Fresh isolated CLI 0.163.0 installation/discovery now qualifies all 16 skills and
the installed product helper's greenfield record/handoff (`fresh-host/`). No
model call was made. Fresh native model invocation failed during startup before
any skill turn: the authenticated managed Codex home is read-only. A supported
SQLite-state override still disconnected; the documented ephemeral CLI path returned EROFS.
The exact remaining write path is not identified by the generic startup error.
See the retained failed attempts, not a simulated substitute. Historical CLI
discovery of 15 skills does not qualify a fresh model workflow. Desktop and
ChatGPT workflow acceptance remain separate. An authenticated dot adapter is still
absent and does not block these local product workflows.

Next product proof is a maintainer's own first task through the installed skill,
with explicit owner customer/proposition choices and visible failure/recovery,
then an unprompted return check. Map coverage is curated and file-level; automatic
discovery, transitive/dynamic consumers and release/deployment inventory remain
unknown. Retirement implementation requires a concrete user decision plus actual
consumer/migration/rollback work; this command only prepares the safe proposal.
Native read-only team roles can consume the prepared record but have not acquired
a new write tool or wider lane. These limits remain visible in the package.
