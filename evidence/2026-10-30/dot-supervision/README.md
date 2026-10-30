# Scoped external supervision and command evidence

Base: `028edf7be69044e90f67f8899527a1728a575ce6` (remote main re-fetched before
implementation). Implementation: `32ecf46`.

No open PRs or other work branches were found before implementation. Only the
OpenAI Delivery package and its tests/evidence changed. The Claude source was
read at `3d7c69416dc7524130105c9bfe308aa01b2a26f0`; no changes were made there.

## Completed scope

The package now distinguishes source availability and installed snapshots, and
the status skill distinguishes planning inventory from actual runtime status.
Optional external supervision is a trusted in-process host seam with configured
principal/environment/task scope, binding generations, stable caller request IDs,
state/task revision checks, durable admission, exact native bindings and local
completion/evidence references. Native operation remains the default. Handover
and fallback require a stopped exclusive dispatcher and reconciled jobs.

Existing native peer recipient validation, durable queues, uncertain-effect
recovery, canonical artifact writes and independent review/acceptance gates are
reused. There is no new mailbox, automatic retry, publisher or dispatch service.
Unknown effects never become success or trigger replacement supervision; an
unknown-turn request blocks further supervisor dispatch, including prequeued work.

The separate local verification helper runs an explicit command against an exact
full SHA in a new independent clone, checks raw tracked bytes/modes, and records
actual outputs and computed results. Surface-command verification observes an
explicit version query before and after a criterion check. Evidence remains a
submission through the existing native gates; human acceptance is unchanged.

## Validation

| Check | Result | Evidence |
|---|---|---|
| Python Delivery suite | 142 passed | `python-tests.txt` |
| Node judge suites | 22 passed | `node-tests.txt` |
| Marketplace validation | Both catalogue packages valid | `marketplace.txt` |
| Whitespace/diff check | Passed | `git diff --check` |
| Bounded handoff | Admitted, restarted, retried once without duplicate dispatch, completed with exact native/evidence refs | `bounded-handoff.json` |

The bounded handoff uses fake native RPC and synthetic Beads, explicitly labelled
in its output. Verification tests execute real local Git/Python subprocesses on
synthetic products, including failure, timeout, version mismatch, mutation,
hidden-index flags and output truncation. Node tests use provider fakes; no live
judge call was made. No plugin installation or user business task was run.
Codex CLI `0.163.0` is present. Beads (`bd`) and Dolt are absent, so contributor
Beads tracking and a fresh real-Beads/native runtime proof could not run. No ad
hoc replacement task ledger was created.

## Independent review

A separate read-only reviewer inspected the runtime, supervision seam, helper,
tests and documentation, then independently reran all 142 Python tests, 22 Node
tests, marketplace validation and the diff check. Confirmed findings were fixed
and regression-tested before the final review passed:

- Unknown native starts cannot borrow a previous turn's terminal receipt.
- Known native failures reach an explicit failed outcome after reconciliation.
- Binding generations revoke old bridges and isolate old request receipts.
- Handover requires quiescence and the existing dispatcher lock; restarting
  serve refreshes bound native instructions.
- Native input carries authoritative request/task/initiative context.
- Raw-byte verification rejects changed files hidden by index flags.
- Prequeued work cannot dispatch past an unknown assignment outcome.

The final review found no concrete correctness blocker for a normal PR for this
documented scope. A final small receipt change includes native completed-item
references (final report text), covered by the completion test and full rerun.

## Qualification and deliberate follow-ups

There is no authenticated dot-to-runtime transport, installed dot integration,
cross-cloud event subscription or live dot completion receipt. The bridge
constructor trusts the embedding host's already-authenticated principal assertion;
it must never be exposed as a model-selected identity field. It is not a remote
authentication service. Task scope validates admission to the native coordinator;
the native runtime keeps its existing execution and controlled-tool capabilities.

The next smallest proof requires supported authenticated dot-to-local execution,
an explicitly selected project/environment, existing Beads and native Codex setup,
and a synthetic task. Exercise lost-response retry and disconnect, then retrieve
an actual native result. Desktop/ChatGPT installation and end-to-end acceptance
remain separately unproven. A scratch clone is not a hostile-code sandbox; surface
version-query correctness still depends on querying the actual intended surface.

Cross-worker record publication/availability, new retry policies, project experts,
Amplifier and feature-map runtime were not implemented. The existing canonical
artifact/evidence paths are reused. No push/merge/deploy capability was added.
