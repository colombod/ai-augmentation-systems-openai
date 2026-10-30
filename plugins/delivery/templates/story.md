<!--
BUDGET — target 700 words, hard cap 1200 words. Excludes code, YAML and data tables.
Stories carry full context deliberately — cut restatement, never context an implementer needs.
Obey ../templates/writing-standard.md. Cut restatement, narration
and hedging first; never cut findings, citations, grounding labels, open questions, or
IDs a later phase reads. Over the cap? Say so in the document, and why.
-->

---
id: <epic>-<nn>
title: <short imperative title>
status: draft | ready | in-progress | done | superseded
epic: <epic name>
supersedes: []          # story IDs this replaces, if any
superseded_by: []       # story IDs that replace this, if any
superseded_reason:      # one line — WHY the design changed, not just what replaced it
route: full-pipeline | bounded-change
phase: <roadmap phase, or bounded outcome>
requirements: [FR-1]
depends_on: []
size: S
surface: <surface id from surface.json, or explicitly declared embedded surface, e.g. S1>
area: <product area, planning grouping; defaults to the epic>
wave: 1                 # the wave of this area this story belongs to (the roadmap's Waves table)
reuses: []              # existing code, evals or decision records this builds on, for selection
# fixes: <existing story, decision citation or failed check>  # a bug: the shipped story, decision citation or failed check record it repairs
# finding: <id or path>   # a security fix: the review record, threat-model entry or challenge finding
---

# <title>

> This file is the complete context. Someone opening only this file — a teammate
> who missed the planning, or an agent with no memory of it — must be able to
> finish the work. Extract what is needed from available PRD/architecture into
> this document rather than linking out. For route: bounded-change, embed the
> compact goal/scope/design/acceptance contract and list absent artifacts; do not
> fabricate them or require full-pipeline documents.

## Owner's ask

> "<the owner's words, verbatim>" (<citation to the actual user decision, if available>)

## Goal

The user-facing outcome, in one or two sentences. What becomes possible.

## Customer surface

<surface id>: <host, app, mode, install artifact> from the initiative's `surface.json` when present, otherwise explicitly declared
here with availability/unknowns. A new surface ID is not deployment proof. Evidence
from any other host, app or mode does not count for this story.

## Context

Why this story exists and where it sits in the feature. Enough that the
implementer understands the intent, not just the instruction.

## Files and modules

Starting state: brownfield / greenfield. Verify existing paths when source is
available. Label future paths **proposed new**, with a create action. If no
repository exists, state the proposed root and setup dependency; do not claim
the files or test command already exist. Proposed paths are not observed map links.

| Path | Path state | What to do |
| :-- | :-- | :-- |
| `src/...` | verified existing | modify — |
| `src/new...` | proposed new | create — |
| `tests/new...` | proposed new | add tests for — |

## Interfaces and contracts to honor

Reproduced here from available architecture, not linked; on the bounded route
state the local interface decision and its evidence/proposed status here.

```
<signatures, schemas, shapes>
```

## Relevant design decisions

Which existing architecture decisions apply, or the bounded local design/risk
decision and why it is sufficient. Absence of an ADR is explicit, not invented.

- **ADR-00n** — decision, and what it means for this story

## Acceptance criteria

Outcomes the customer observes on the surface, traced to the PRD or bounded outcome, each falsifiable by someone who
did not write it: "<persona> in <surface> does X and sees Y", never a tool, endpoint, test, link or
ticket. One probe per criterion: what is observed, where, and by whom (`test` on a scriptable
surface, `reality-check` on one that is not). A size S story needs one criterion and one probe.

1. <persona> in <surface> does <X> and sees <Y>. `FR-1`
   - Probe: <what is observed>; where: <surface id>; by: <test | reality-check>

## Measurement plan

At most three signals, preferably production log lines carrying the caller's client and surface,
in place before the first reality check.

| Criterion | Signal | Threshold | Where | When | Who |
| :-- | :-- | :-- | :-- | :-- | :-- |
| 1 | <log line or metric> | <a number> | <surface id> | <pre-merge on a preview, or within N h of deploy> | <role> |

## Shippable unit

What a person on the customer surface can do or see after this story alone ships, and the probe
that shows it. A horizontal story (backend only, scaffold, migration) names the vertical story that
ships it.

## Test approach

**Level:** unit / integration / e2e, and why that level for this risk
**Cases:**

| Case | Expected |
| :-- | :-- |
| happy path | |
| empty / zero | |
| boundary / max | |
| invalid input | |
| permission denied | |
| concurrent | |

**Run with:** `<established command, or explicitly proposed command after setup>`
**Availability:** verified / proposed, not yet executable. Name the setup or probe
needed before execution; a planned command is not a test result.

## Ship readiness

**Only applies when this story changes the plugin's own skills, hooks, agents, or
templates** — code/config other sessions load, not an ordinary product feature. Delete this
section entirely if it doesn't apply; do not leave it blank.

- [ ] Branch was fetched and compared against the real current `main` immediately before
      merge — not assumed current after time has passed. State the check, not just the result:
      fetch the real target branch, then `git merge-base --is-ancestor origin/main HEAD`
      on the reviewed branch (substitute its actual target); record both SHAs.
- [ ] The plugin's version is bumped, if the host tool needs a version change to pick this up
      (check this project's own convention/history rather than assuming).
- [ ] If full behavioral verification needs an environment this session doesn't have (a fresh
      session, a reinstalled plugin, a hot-reload this harness doesn't support mid-session) —
      that gap is named explicitly as a real open item, never silently claimed as passing.

## Out of scope

Deliberate boundaries. These were decided, not forgotten.

- 

## Dependencies

Stories that must be `done` first, and why.

- 

## Implementation notes

Filled in during and after implementation. Record surprises, deviations from the
plan and the reason, and follow-up work — anything a future reader would want.

