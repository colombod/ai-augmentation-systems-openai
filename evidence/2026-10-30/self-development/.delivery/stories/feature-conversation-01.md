---
id: feature-conversation-01
title: Resume one feature decision without losing product or evidence context
status: done
release_state: unshipped-source
verification: independent-local-cli; not human/native acceptance
size: S
requirements: [FR-1, FR-2, FR-3, FR-4]
surface: S1
---

# One feature conversation handoff

## Owner's ask and goal

User: “And the focus will really be at product and feature level”; “I want to see
you reaching the point to onboard this plugin itself and then using the plugin
to develop the plugin further.” These are actual owner statements, not approvals
of this particular design or native acceptance. Local reversible implementation
is authorized by the delegated user request; publication/merge are not.

The project owner working with dot can focus/resume one capability decision with
its current/planned status, value evidence and what must survive. Code/tasks are
supporting detail. This feature is a read-only context view, not an action decision.

## Surface and observed starting state

S1: local Python CLI helper on the actual Delivery source checkout, invoked by an
authorized host. No installed native model autonomy, ChatGPT-dot authentication,
customer adoption or token-saving claim. Source-driven agent implementation only.

Baseline product source: 9ed005a1ab1da54ad7f944622e347b0d28847284.
Canonical planning store: /workspace/delivery-self-plan/.delivery.
The reused/updated product map has 14 features: 12 source preview capabilities,
feature-conversation planned/code absent, authenticated-dot planned/code absent.
Fresh baseline map SHA: b8eb451a3e819a6aa83c46797b6305819ba598e432e1a17b288a612bfe7a5b5c.
Actual baseline `handoff` emits all14 capabilities (43791 bytes); `handoff --feature
feature-conversation` exits2, unrecognized arguments. This is a workflow gap,
not proof that fewer output bytes necessarily improve model quality.
Pre-edit impact identifies product-baseline, compact-framing, dependency-impact
and retirement-proposal sharing product.py. Preserve those consumers/defaults.

## Interfaces and minimal design

Existing verified files: plugins/delivery/scripts/product.py;
tests/delivery/test_product.py; plugins/delivery/references/product.md;
plugins/delivery/skills/product/SKILL.md; plugins/delivery/CHANGELOG.md.
No new service, registry, database, dependency or writable runtime tool.

Add optional exact-ID selection to existing `handoff --feature ID` and optional
`feature_id=None` to its Python function. Default output stays unchanged. A selected
view includes exactly that feature plus existing whole-product owner/customer/
shape/authority/unconfirmed context and unchanged global freshness. Clearly mark
selection as display/context scope; other features remain in canonical state.
CLI continues attaching the actual map_sha256. Empty/unknown IDs fail clearly,
never fall back to all features. Do not mutate records/history or infer permissions.

## Acceptance criteria

FR-1: Owner can request one existing current or planned capability and receives
only that feature's full summary/state/code/evidence/unknowns/six usefulness cards,
with all global owner/product/authority context retained and explicit selection.
FR-2: Owner can use the original full handoff unchanged; selection neither edits
nor drops canonical feature IDs/history, grades or attributed decisions.
FR-3: Unknown/empty IDs exit2 with a clear error. Existing handoff exit1 for
unconfirmed choices remains meaningful; do not fabricate confirmation to get0.
FR-4: No-code greenfield selection works without Git/code. Stale evidence in an
unselected feature remains globally visible and returns the existing stale exit.
No invocation grants implementation, retirement, approval or native write rights.

## Verification and stop conditions

Use real public CLI process checks for acceptance, plus focused Python regression
cases for default compatibility, full context/read-only preservation, invalid ID,
concept-only mode and unselected stale evidence. Established full command:
`python3 -m unittest discover -s tests/delivery -v`; Node baseline22 and marketplace
validation remain applicable. Add no model calls or installs. Current baseline
185 Python tests already passed; preserve useful tests rather than weakening them.
Stop if this needs a schema migration or a new authority/retirement mechanism.
Return changed files, exact commit, actual outputs and unmet criteria. Commit only
local allowed source files; do not push/PR/merge. Do not edit the planning map or
this packet; planner owns recording/review/realignment. Keep manifest version.11
on this separate local development branch pending later release reconciliation.
