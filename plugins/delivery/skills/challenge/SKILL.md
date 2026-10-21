---
name: challenge
description: "Run an adversarial review panel against any pipeline artifact \u2014 brief, research, personas, PRD, prioritisation, design, architecture, roadmap or stories \u2014 and record ranked findings with tracked status. Use before committing to any artifact. Target stays read-only; findings must be resolved or explicitly rejected, not silently dropped."
---

# Adversarial challenge

Target: **the user's request** (an artifact path, or a phase name; defaults to the most recently written artifact)

This is the pipeline's review mechanism, usable at any gate. The target stays read-only: it writes a separate findings document and never edits the review target.

## Conventions

Read [host capability guidance](../../references/runtime.md) and
[delivery conventions](../../references/conventions.md) before running this phase.

## Why findings are tracked

An adversarial review that produces a list nobody acts on is theatre, and it is worse than no review because it manufactures the feeling of rigor. So every finding here is written to `.delivery/reviews/` with a status, and `$delivery:status` reports any that are still **open**. A finding leaves the list by being **fixed** or **rejected with a stated reason** — never by being ignored.

## Gate check

Resolve the target. If given a phase name, map it to its artifact. If nothing is given, take the most recently modified artifact under `.delivery/`. If the target does not exist, say so and stop.

If the target carries a Version-history table (per
`../../templates/version-history.md`), record which version is current and
its Status cell — this review is against that version specifically, not the whole
document's history. A target with no table has no version to record.

## Choose the panel

Reviewer lenses are chosen by artifact type. Diversity of lens matters more than number of reviewers — three reviewers asking different questions beat five asking the same one.

| Target | Panel |
| :-- | :-- |
| `brief.md` | `product-owner`, `business-analyst`, `feature-critic` |
| `research.md` | `business-analyst`, `solution-architect`, `feature-critic` |
| `personas/` | `user-researcher`, `product-owner`, `feature-critic` |
| `prd.md` | `product-owner`, `business-analyst`, `qa-strategist`, `feature-critic` |
| `prioritization.md` | `product-owner`, `program-manager`, `user-researcher`, `feature-critic` |
| `design-system.md` | `design-lead`, `user-researcher`, `qa-strategist`, `feature-critic` |
| `architecture.md` | `solution-architect`, `qa-strategist`, `program-manager`, `feature-critic` |
| `roadmap.md` | `program-manager`, `product-owner`, `qa-strategist`, `feature-critic` |
| `stories/` | `delivery-lead`, `qa-strategist`, `solution-architect`, `feature-critic` |

`feature-critic` is on every panel — it is the only reviewer with no stake in the artifact moving forward.

Where personas exist and the artifact touches user-facing behavior, add one `persona-simulator` running the **skeptic** persona. A challenge from the user's side catches things no internal role will.

## Run

Read the target fully yourself before dispatching anyone — you need to judge the findings, not just relay them.

When native delegation is available and authorized, run separate read-only
reviewers without sharing their findings until synthesis. Request findings only.
Otherwise use sequential lens passes, explicitly labeled single-session review.

If independent reviewers are unavailable, use sequential lens passes and explicitly
label the result **single-session review**. Do not count agreement as independent convergence.

## Synthesize

Judge the findings; do not concatenate them.

1. **Deduplicate**. Record independent agreement only for genuinely isolated
   reviewers. For single-session passes, report lens overlap and mark independent
   convergence unavailable.
2. **Rank by expected cost** = likelihood it bites × cost of fixing it later, not by reviewer order or severity label.
3. **Classify**: **blocking** (resolve before the next phase), **significant** (resolve before implementation), **minor** (note and move on).
4. **Drop preferences.** Anything without a concrete failure scenario is not a finding. Report how many you dropped — that number is a quality signal about the panel.
5. **Check the reviewers.** A reviewer that returned nothing but praise, or nothing but style notes, did not do its job; say so rather than padding its output into the list.

For each surviving finding: the specific claim or omission, the concrete failure scenario, and what would resolve it.

## Write

Append to `.delivery/reviews/<initiative>-<artifact>-<nn>.md` using `../../templates/findings.md` — or `.delivery/reviews/<initiative>-<artifact>-v<N>-<nn>.md` (e.g. `launch-prd-v2-01.md`) when the target carries a Version-history table at review time, recording which version the review actually covered. Unversioned targets (`stories/`, tableless documents) keep the `<initiative>-<artifact>-<nn>.md` form; pre-existing review files are not renamed retroactively. Every finding gets an ID (`R-<artifact>-<n>`) and status `open`.

Do not edit the target artifact in this skill. Present the findings and let the user decide; apply any agreed target changes in a separate, explicitly requested editing task before marking the findings `fixed`. A finding the user declines is marked `rejected` **with their stated reason recorded** — the reason is the valuable part, because it is the assumption you will want to revisit when something goes wrong.

## Writing, then revising

**Budget: 120 words target, 200 hard cap** (excludes code, YAML and data tables). Compose, measure and revise as *Writing, then revising* in the conventions says.

## Report

Lead with blocking findings and with anything multiple reviewers found independently.

If the artifact is genuinely sound, say so and name the two or three assumptions worth watching. Do not pad — a padded critique teaches people to skim the next one, which costs more than the finding you invented was worth.
