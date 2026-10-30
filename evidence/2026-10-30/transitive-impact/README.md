# Optional dependency-side feature impact

Base merged main: `a46dc827826c9d641f5e745101f4cc14fcf1a21b` (preview.7).
Exact source: `d1d9176d99c67a0de84234d00ebe02122a90b2ea`.
Branch `delivery/transitive-impact`, candidate `0.1.0-preview.10`.
The preview.8 drafting and preview.9 loading branches are not included or modified.
Version/changelog order needs reconciliation if multiple candidates are accepted.
No merge, release or deployment is performed. No publication retry is included.

## Actual user-value proof

Question: which recorded feature promises may a proposed change to
`plugins/delivery/scripts/operator_capture.py` affect?

At the named commit, two real Delivery capabilities were curated in the existing
product record using their actual entry modules: native coordination (`runtime.py`)
and controlled task workflow (`delivery_gates.py`). These are source-preview
capabilities; this exercise does not infer deployment or outside-user use.

The unchanged direct command finds **zero** matches, because neither curated
anchor explicitly names `operator_capture.py`. Adding `--transitive` finds both:

| Feature | Shortest possible-import evidence chain |
|---|---|
| Native coordination | `plugins/delivery/scripts/runtime.py:657` → `plugins/delivery/scripts/operator_capture.py` |
| Controlled task workflow | `plugins/delivery/scripts/delivery_gates.py:22` → `plugins/delivery/scripts/operator_capture.py` |

The optional retirement proposal also preserves that dependency for the surviving
controlled-work feature. Its derived exclusive paths are labelled candidates only;
no source file, record state or acceptance authority is changed. All missing user
choices stay proposed/unknown. The equally first-class illustrative greenfield
concept has planned code absent and reports graph unavailable with a reason.

Reproduce the **eight public helper commands** and their assertions with:

```
python3 scripts/probe_product_dependencies.py --repo <this-checkout> --output <new-output-directory>
```

`real-repository/commands.json` retains commands, actual stdout/stderr/exit codes;
`summary.json` names the exact source commit. Product inputs and canonical records
are retained there too. Only explicit packaged helper commands run; dependency
extraction parses immutable Git blobs rather than importing them for discovery.
The source modules are not run as business tasks. This is deterministic CLI/source
evidence, not a model-driven skill, native runtime, deployment or adoption test.

## Implemented source and limits

- Existing `product.py impact --path FILE --transitive` and
  `retire-plan --feature ID --transitive`; one existing product record, no graph
  database/service, discovery registry, state migration or extra dependency.
- Existing direct fields and default behavior remain unchanged. Separate optional
  results name the recorded commit, shortest BFS file/line/kind chains, shared
  consumers, direct-unmapped meaning, unreached unknowns and analysis limitations.
- Python AST imports only, with conventional sibling/repository/src roots and
  regular package initializers. Conditional/local imports are possible reach,
  never an actual runtime trace. No semantic call graph, deployed inventory,
  installed packages, namespace/custom package context, custom sys.path or other
  language inference. Other languages keep direct coverage.
- Unresolved/external/ambiguous imports, unsupported files/initializer modes,
  parse/size failures and recognized dynamic loaders remain explicit even inside
  analyzed files. Files outside curated anchor reach are not inspected. An empty
  diagnostic list does not establish completeness.
- Source is pinned to full commit and safe existing Git helpers: environment
  isolation, replace-object refusal, no optional locks/fsmonitor, timeout retained.
  Reached dependency raw bytes/modes get separate freshness checks, including
  hidden-index/same-size/mtime cases. Staleness returns exit 1. Unsupported or
  unavailable optional analysis is informational and never establishes/blocks
  story readiness; direct results remain available.
- Retirement exclusivity is candidate-only. Preserve known shared consumers,
  inspect unknown/transitive/external use and require the existing exact human
  decision, migration/replacement/rollback and retained history before separately
  authorized work. No deletion or automated feature-state change exists here.

## Source provenance and checks

Selective traversal design adapted from Anthropic Delivery **0.40.2**, pinned
`369ecaffc564fc4ece470eb229d3034e81912f75`: `scripts/lib/codemap.js`,
`scripts/lib/features.js`, and `scripts/map.test.js`. Read those sources and the
MIT licence; did not execute upstream code. Native AST extraction intentionally
replaces the broader upstream regex rules. Exact source hashes/adaptation scope
are in packaged `upstream.json`; identical full Copyright (c) 2026 Diego Colombo
MIT notice remains in `LICENSE`, with the additional source notice in `NOTICE`.
No upstream hook/permission/registry or “deletable” claim was copied.

- **152 Python tests passed**, including **12** new graph regressions and the
  original **18** product cases. **22 Node tests passed**; marketplace validation
  and `git diff --check` pass. See `checks/`.
- Independent read-only review identified and reproduced package-base ambiguity,
  relative-package escape, source-root initializer inclusion, unsupported parent
  initializers, namespace/module-shadow resolution and an altered warning that
  broke an existing direct-impact regression. Each confirmed issue was fixed;
  new cases exercise them. The original warning was restored verbatim. Independent
  reviewer then reran all 152 Python tests and catalogue validation successfully
  and found no remaining concrete source blocker. This is source/correctness
  review, not a model-quality evaluation.
- Isolated Codex CLI **0.163.0** installation/discovery: all **16** skills;
  installed greenfield record/handoff and optional-impact-unavailable check pass.
  **Zero model calls**. No user credentials/config were copied.

Model-driven output quality, actual token/time use, desktop/ChatGPT/native-runtime
and authenticated-dot integration remain unproven. This adds a bounded deterministic
capability with actual repository evidence; QA can now evaluate how a model uses
it. Fewer bytes, a parser pass or a source graph alone would not establish product
quality or a performance improvement.
