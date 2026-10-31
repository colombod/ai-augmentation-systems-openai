---
name: research
description: "Research the feature space before specifying anything \u2014 how others solve this, what the domain requires, what users complain about today, and what the existing codebase already constrains. Use after the brief and before personas. Produces .delivery/initiatives/initiative/research.md."
---

# Feature research

Topic: **the user's request** (defaults to the feature named in the brief)

DEFINE stage, optional depth. Input: `.delivery/initiatives/<initiative>/brief.md`. Output: `.delivery/initiatives/<initiative>/research.md`.

## Conventions

Read [host capability guidance](../../references/runtime.md) and
[delivery conventions](../../references/conventions.md) before running this phase.

## Gate check

Read `.delivery/initiatives/<initiative>/brief.md`. If it is missing, stop and point at `$delivery:brief` — research without a framed problem produces a literature review nobody uses.

If `.delivery/initiatives/<initiative>/research.md` already exists, read it and ask whether
to **revise**, **replace**, or **start new version**. See
`../../templates/version-history.md` for what each means, the same-problem
test that chooses between revise and start new version, and the Version-history table and
Corrections log it writes. Never silently overwrite.

## Run

Research from evidence, not from recall. Use the current host's actual search
and page-reading tools when available; no particular tool name or MCP provider
is required. Without browsing, use supplied sources and mark uncovered market
claims **unresearched**. Do not infer current external facts from memory.

**0. Search through three different angles:** product category, the user's own
problem wording, and complaints about failures. With available, authorized native
delegation, give separate reviewers the raw brief and independent search tasks;
do not share their findings until synthesis. Otherwise run the angles sequentially
in this session and label agreement **single-session overlap**, not independent
convergence. If browsing is absent, list the searches still needed instead of
pretending they ran. Record the actual mode and sources retrieved.

Where each angle returned material the others missed, say so: the space is not exhausted,
and the document should not imply that it is.

**1. Prior art — how is this problem solved today?**
Find three to five products or projects that solve it, including at least one outside the obvious category. For each: the approach, what it gets right, what users complain about. Public reviews, forum threads and issue trackers are the highest-value source here, because complaints are unmet requirements stated by the people who have them.

**2. Domain constraints.**
What does this problem space impose regardless of implementation? Regulatory requirements, industry conventions, data standards, accessibility obligations, seasonal or geographic realities. Constraints found now are cheap; constraints found during implementation are not.

**3. The technical landscape.**
Available libraries, protocols, standard formats, integration surfaces. For each candidate: maturity, maintenance status, licence, and the reason it might not fit. Do not pick a winner — that is the Solution Architect's decision, made later with more information.

**4. What the codebase already decides.**
Read the existing project — its architecture, its stated non-goals, its conventions. Some options are already foreclosed by decisions made long ago, and knowing which saves the architect a wasted design. Cite real paths.

**5. What you could not find out.**
The gaps matter as much as the findings. List what you looked for and did not find, and what it would take to answer.

## Write

Write to `.delivery/initiatives/<initiative>/research.md` using `../../templates/research.md`.

Cite every external claim with a URL. Mark each finding as **verified** (you read the source), **reported** (a secondary source says so), or **assumed** (your inference). Keep those three visually distinct — the later phases will lean on this document, and an unmarked assumption becomes a fact by the time it reaches a story.

## Exit criteria

- At least three prior-art examples with named strengths and complaints
- Domain constraints listed, or explicitly stated as none found
- Technical options with maturity and licence, and no winner declared
- Existing-codebase constraints cited with real paths
- Every external claim carries a source
- Open gaps listed
- At least three search angles used; independence and convergence reported according to the actual review mode
- Within the template's budget, or the overrun declared in the document with its reason

## Writing, then revising

**Budget: 900 words target, 1400 hard cap** (excludes code, YAML and data tables). Compose, measure and revise as *Writing, then revising* in the conventions says.

## Hand off

Report what you found that would change the brief — prior art solving it better than planned, a constraint that invalidates an assumption, a foreclosed technical option. If the research undermines the premise of the effort, say so plainly; that is the most valuable outcome this phase can have, and the cheapest moment to have it.

Next step: `$delivery:personas`.
