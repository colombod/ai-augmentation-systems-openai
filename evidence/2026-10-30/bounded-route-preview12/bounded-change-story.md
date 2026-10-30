---
id: feature-conversation-02
route: bounded-change
status: ready
readiness: source-driven manual planning review; no execution authority
---
# Carry the feature decision through an installed shipping handoff

Customer: owner working with dot on Delivery. Actual ask: product/feature focus,
self-onboard and use Delivery to improve Delivery, then ship. The specific design
is an assistant proposal; owner confirmation is not invented.

Current capability: feature-conversation at 4a11c76 has focused context and newly
written bounded/shipping guidance. Earlier 8340 route failed independent product
acceptance: roadmap prerequisite conflict and no shipping instructions. The new
route text is a repair draft already written, not evidence it existed earlier.
No original PRD or architecture exists. A real retrospective roadmap/open-gap
record exists and is preserved; this explicit bounded contract supplies scope and
local design. Full-pipeline documents are not reconstructed.

Next useful change now: ensure installed workflow guidance matches reviewed
source, including the new route and every consuming phase. Observed probe hashes
only product/core/product-reference/reviewer-context, so it cannot establish these
new resources survived installation unchanged. Alternative: manual inspection
only; rejected because the existing deterministic installer probe can directly
check actual bytes. New runtime/service/agent infrastructure is out of scope.

FR-1: installed probe compares bounded-change reference and stories/sprint/
sprint-review/realign skill bytes to source and returns hashes. Probe: run
python3 scripts/probe_delivery_install.py --output /tmp/preview12-route-install.json,
inspect all five hashes. No model-workflow or efficiency claim.
FR-2: full Python/Node/catalogue checks pass and protected runtime source remains
unchanged. Probe actual suites and scoped diff. Product acceptance remains for
independent QA; do not grade ourselves as independently accepted.

Existing verified path scripts/probe_delivery_install.py; add the five paths to
its existing byte-comparison list, no new API/dependency. Pre-edit product impact
may be unmapped; map freshness/coverage from the actual helper is retained rather
than treated as a blocker. Rollback: revert this probe-only edit; do not mutate
host config. Stop on new auth/install requirements, unexpected failures or scope
change. Disposable CLI installation is already authorized; device install is not.
Shipping: same approved normal PR3, exact-head code/product review and CI, merge
only after both pass, verify receipt/main then authorized-host canonical refresh.
