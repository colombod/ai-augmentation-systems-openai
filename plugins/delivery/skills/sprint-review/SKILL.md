---
name: sprint-review
description: "Assess acceptance of a completed sprint \u2014 criteria actually met, design system conformance, persona journeys now possible, and what the wave taught. Use after $delivery:sprint. Produces an acceptance verdict and feeds the next planning cycle."
---

# Sprint acceptance review

Sprint: **the user's request** (defaults to the most recent sprint log)

The closing gate of an implementation wave. This decides whether the sprint is **accepted**, and it feeds what it learns back into planning.

## Conventions

Read [host capability guidance](../../references/runtime.md) and
[delivery conventions](../../references/conventions.md) before running this phase.

## Gate check

Read the sprint log in `.delivery/sprints/`, the stories it covered, `.delivery/initiatives/<initiative>/prd.md`, `.delivery/initiatives/<initiative>/prioritization.md`, `.delivery/initiatives/<initiative>/design-system.md` and `.delivery/personas/` where they exist.

For `route: bounded-change`, review the embedded story/sprint contract and
[bounded-change route](../../references/bounded-change.md); list unavailable full-pipeline
artifacts rather than requiring or inventing them. Repair findings stay open until
independently rechecked.

If no sprint log exists, stop — there is nothing to review.

## The rule this skill exists under

The implementation was run by something else — Codex, another authorized runner, or a human team — and it reported its own results. A process that only ever grades itself drifts toward optimism, and a runner optimises for finishing. State whether the reviewer is independent of the implementation; the review re-checks acceptance criteria **against the code as it now exists**, rather than trusting the runner's report-back.

Where the report and the code disagree, the code wins and the discrepancy is itself a finding — it means that runner's self-assessment cannot be relied on, which matters more than the individual story and should change how much of its next report you believe.

Where the runner used its own task IDs rather than `FR-n`, use the ID mapping recorded in the scope package to trace results back to requirements. A criterion nobody can trace to a task is a criterion nobody verified.

## Run

When a product record exists, read [the product contract](../../references/product.md).
Reconcile shipped/preview/planned claims against actual evidence at the reviewed
commit. Keep Job, First value, Fit, Outcome, Trust and Return separate from task
acceptance and from each other. A passing test or our own walkthrough remains
Claimed usefulness evidence, not Seen outside-user adoption. Carry unknowns and
the next real-use/return check forward; never infer retirement from missing use.

Check global assessment scope, not only the updated feature: inspect handoff's
assessment result and compare right_shape, riskiest_assumption, cuts and next_slice
with current intent and acceptance evidence. Flag obsolete or unscoped proposals
carried as current direction, even when source freshness is true. A matching scope
digest is only a declaration binding; semantic judgment remains this review's
responsibility. Carry contradictions into realign, preserving owner statements
and complete historical content rather than silently rewriting them.

**1. Verify criteria against direct evidence.** Use the `qa-strategist` lens. Read
criteria first, then inspect the actual current behavior. Record met / not-met / partial /
unable-to-check with the surface, revision, command or capture, result and reviewer.
Name whether the reviewer is independent of the implementation. This preview has no
invocation/deployment ledger: never fabricate ev- IDs, provenance or automated gate
results. Source or stub results cannot establish real-host or real-model acceptance.

For user-facing criteria, follow the `qa-strategist` lens's standing evidence rules:
GUI needs a real capture inspected here; CLI needs a real process invocation with
observed output and exit code; TUI layout needs a visual capture. Name the actual
channel, revision and artifact. An inaccessible surface stays unable to check.

**2. If this sprint touched the plugin's own skills, hooks, agents, or templates — verify
ship readiness independently, not from the sprint log's word.** This is a distinct failure
class from a functional acceptance criterion: a change can be functionally correct and still
fail to actually reach anyone. Re-check, yourself, against the real current state — do not
trust a story's own "Ship readiness" checkboxes as sufficient, the same "verify against
criteria, not the builder's report" rule this whole review runs under:
- Inspect the actual reviewed revision and recorded integration evidence. For a branch
  about to merge, fetch the current target when permitted, then use
  `git merge-base --is-ancestor origin/main HEAD` to check that it includes the current
  target (substitute the real target branch). Record the actual SHAs. A comparison
  between local `main` and `origin/main` alone says nothing about the reviewed branch.
- The plugin's version was actually bumped in the merged commit, if this project's own
  convention requires one (check its real history, don't assume).
- Any claim that a fix "works" is either backed by verification this session could actually
  perform, or explicitly flagged as unverified pending a fresh session/environment this one
  doesn't have — a claim resting on an environment nobody actually has access to is not
  evidence, and gets the same **not accepted** treatment as an untested functional claim.

**3. Run the test suite** and report the real output. A sprint that claimed green and is now red is the single most important thing this review can catch. Run on the actual commit under review and quote the observed output; a reported result without its output is not direct evidence.

**4. Check design system conformance.** Where a design system exists, use the `design-lead` lens: which tokens were used, which were bypassed with hardcoded values, which component states are missing, which contrast rules fail. Report file paths, not impressions.

**5. Check the persona journeys.** This is the question that matters most and the one story-level criteria cannot answer: *can a persona now complete a journey end to end and get value?* Use the `persona-simulator` lens for each persona whose journey this sprint was meant to enable, walking the **now-real** implementation. Label the output synthetic, as always.

A sprint where every story passed but no persona can complete a journey has delivered nothing usable, and only this check will tell you.

**6. Reconcile against the stage promise.** For bounded changes use the embedded customer promise/scope; otherwise `prioritization.md` said what this stage would deliver and which personas it would serve. Compare what was promised to what is now true. Name any silent scope drop.

**7. Challenge the result.** Use the `feature-critic` lens (read-only) with the question: *what would make this acceptance verdict wrong?* Missing evidence, criteria passing on a technicality, tests asserting implementation rather than behavior.

## Verdict

State one of:

- **Accepted** — all criteria met with evidence, tests green, persona journeys work
- **Accepted with debt** — criteria met, but named issues are being carried forward, each recorded as a finding
- **Not accepted** — criteria unmet, journeys broken, or ship-readiness failed (stale branch merged, a required version bump missing, a claim resting on unverifiable-from-here evidence); state exactly what and what it would take

Do not soften this. A sprint review that never returns "not accepted" is not a gate, and everything downstream will be planned on a false baseline.

## Learn

Then capture what the wave taught, which is the part that improves the next one:

- **Stories that were wrong** — where the spec conflicted with reality, and what the story was missing. This is feedback for `$delivery:stories`.
- **Estimates that were wrong**, and in which direction. Feedback for `$delivery:roadmap`.
- **Assumptions invalidated** — from the PRD, architecture or personas. Anything invalidated needs those documents updated, or the next phase inherits a known-false premise.
- **Friction found in the real thing** that simulation missed, and vice versa. This calibrates how much to trust simulated output next time — genuinely valuable, because it is the only feedback the persona phases ever get.

## Write

Write to `.delivery/sprints/<initiative>-<n>-<slug>-review.md` using `../../templates/sprint-review.md`. Record carried debt and invalidated assumptions as findings in `.delivery/reviews/` with status `open`, so `$delivery:status` keeps surfacing them until they are resolved or explicitly rejected.

## Writing, then revising

**Budget: 600 words target, 1000 hard cap** (excludes code, YAML and data tables). Compose, measure and revise as *Writing, then revising* in the conventions says.

## Hand off

Lead with the verdict and the persona-journey result. Then state what must be updated before the next sprint — invalidated assumptions in the PRD or architecture, stories that need rewriting, estimates that need recalibrating.

Next step: the specific repair if not accepted; otherwise choose another wave
or the [authorized shipping handoff](../../references/bounded-change.md#authorized-shipping-handoff).
Acceptance alone grants no publication/merge authority. Follow the handoff through
exact-head independent product/code review and CI, authorized merge, receipts and
canonical product-state refresh; report partial/unshipped states honestly.
