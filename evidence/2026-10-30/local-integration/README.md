# Unshipped local compatibility integration

Tested combined source commit: `edd036fbd96b60f58a3936766a2e712cbf18f502`.
Local-only branch: `test/delivery-combined-20261030`.
Worktree: `/workspace/delivery-integration`.
Package label: `0.1.0-integration.20261030` (explicitly not released/approved).
No push, PR publication/retry, remote merge or user-host installation occurred.

## Exact inspected inputs

| Input | Source head |
|---|---|
| Merged main / product workflow | `a46dc827826c9d641f5e745101f4cc14fcf1a21b` |
| PR1 supervision / verification | `33146a95c2e1bd1ce0c1a0b6215a88be4cb44de4` |
| Compact drafting | `6c95dc4311b13b084f6b9a87e56c2e8aa128902e` |
| Selective loading | `e92b71a48b6ad417bef73bd38dd184784b163f12` |
| Transitive impact including initializer correction | `d02db2f5de2a39a721f59d3080c3f56abee61071` |

Fetched/inspected current remote state first. All five are ancestors of the local
integration commit. Original local/remote branch heads are preserved, and all
published catalogue bytes remain identical to main. This test branch is the only
combined source; passing here does not mean the pending increments are on main.

## Conflicts and local-only resolutions

- PR1 into main: four conflicts — CHANGELOG, NOTICE, README installation wording,
  upstream.json. Retained both feature histories/notices/provenance and explicitly
  separated source availability from installed snapshots.
- Compact drafting: clean automatic merge.
- Selective loading: five conflicts — repository/package README versions,
  CHANGELOG, plugin.json and product skill. Retained the focused query route and
  compact draft as an authoring operation; retained both unreleased histories.
- Transitive impact: eight conflicts — versions/readmes/changelog, NOTICE,
  upstream.json, product skill and installed-probe summary. Retained both provenance
  objects/notices, optional reach guidance alongside focused/direct routing,
  compact authoring, and both installed-draft/optional-impact checks.
- Used one local-only manifest/readme label instead of pretending preview.8/.9/.10
  are one published version. The source branches still need deliberate release/
  changelog/version reconciliation if accepted; no catalogue change was needed.

Raw merge failures and resolved combined diffs are retained in `merge-*.txt` and
`*-resolutions.diff`. No production semantic repair was needed: product.py merged
automatically; every top-level product function except its combined CLI dispatcher
matches the relevant original drafting/graph AST. The dispatcher was exercised
through both paths. runtime.py, delivery_gates.py, supervision.py and verification.py
are byte-identical to PR1 (hashes in `combined-journeys.json`).

## Actual completed checks

- **185 Python tests passed**, covering the union of planning/product/drafting,
  loading, graph/freshness/initializer-retirement, runtime/authority, supervision
  admission/retry/recovery and command verification regressions.
- **22 Node judge tests passed**; marketplace validation and final diff checks pass.
- PR1's actual `verification.py review` made a separate scratch clone at the exact
  integration SHA and ran the same **185 tests successfully**, with actual output,
  exit/revision/raw-byte checks. `passed: true`, `accepted: false`. This is a trusted
  source test clone, not a security sandbox or human task acceptance.
- Isolated Codex CLI **0.163.0** installation/discovery: **16 skills**, compact draft,
  record, handoff and planned-greenfield optional-impact checks passed. A separate
  test-only probe verified **12 installed resource hashes**, including product,
  runtime, supervision, verification, gates/artifacts/RPC helpers and common refs.
  No user credentials or personal configuration copied; **zero model calls**.
- **14 public-command interaction steps** test brownfield AND greenfield compact
  draft → record → direct/optional impact → retirement proposal → handoff. Plain
  owner notes remain proposed, all six usefulness ratings/grades remain Unknown,
  planned status is not auto-promoted by code, and handoff returns the expected
  unconfirmed-choice exit. Shared dependency preservation works after drafting.
- Existing actual-repository product workflow (**11** commands) and optional
  dependency proof (**8** commands) also pass on the combined SHA. Together these
  are **33 public helper process invocations**, not 33 independent user studies.
- A synthetic active native-manager actor is still **denied** writing
  `product-map.json` via the controlled artifact tool; canonical record bytes remain
  unchanged. This verifies preservation of the intended boundary, not live native
  role execution. It also exposes the remaining manual host-write integration step.

The standalone test harnesses and raw command receipts are retained here. The
extra installed-resource probe is test-only; it adds assertions to a copied probe,
not a source/permission change. No repeated blocked native inference was attempted.

## Environment limits versus product gaps

Environment: Python 3.12.14, Node 24.19.0 and Codex 0.163.0 exist; `bd` and `dolt`
executables do not. Thus real Beads-backed coordination cannot be qualified here.
Codex --version emitted the known read-only-home alias warning. Native model
inference was not retried, and no credentials/network policy/provider/host settings
were changed. Live judge credentials were not inspected or used.

Product/integration gaps (not environment excuses):

1. No authenticated dot-to-Delivery adapter exists. PR1 is a trusted in-process
   seam and fake-transport tests; cloud callbacks do not subscribe to its SQLite/
   Beads state. No actual dot/native completion receipt was obtained.
2. Product record writes remain authorized-host helper operations. Native managers'
   protected artifact lane excludes product-map.json; the combined source does not
   make an autonomous runtime product-record workflow. No lane was widened to hide
   that limit.
3. Feature curation still needs host judgment; optional import reach is Python-only
   and partial. It is not a complete feature/call/deployment inventory, nor evidence
   of unknown consumers being absent. Retirement is still an owner decision.
4. Instruction conflict resolution creates a new combined skill body. Standalone
   loading/model-eval claims cannot be transferred to this combined body without
   evaluating it. Multi-stage model quality, actual token/time use, real native role
   coordination, desktop/ChatGPT acceptance, human acceptance and outside-user value
   remain unproven by these deterministic checks. Parent's separate goal/scenario QA
   is not replaced by this exercise.

Conclusion: the increments can be packaged together after explicit local textual/
metadata reconciliation, and no code-level compatibility failure appeared in the
checks run. **This is not full coverage or a delivered/qualified unified plugin.**
Original branches remain pending review/publication decisions; the local integration
must not be silently merged or treated as shipped.
