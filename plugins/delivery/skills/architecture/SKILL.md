---
name: architecture
description: "Turn an approved PRD into a technical design grounded in existing code or an explicit greenfield baseline, with decisions, spikes, migration plan and test strategy. Use before story decomposition. Produces .delivery/initiatives/initiative/architecture.md."
---

# Architecture and technical design

Focus note from user: **the user's request**

DEFINE stage, last step. Inputs: `.delivery/initiatives/<initiative>/prd.md`, plus `prioritization.md` and `design-system.md` where they exist. Output: `.delivery/initiatives/<initiative>/architecture.md` and ADRs in `.delivery/decisions/`.

## Conventions

Read [host capability guidance](../../references/runtime.md) and
[delivery conventions](../../references/conventions.md) before running this phase.

## Gate check

Read `.delivery/initiatives/<initiative>/prd.md`.

- **Missing** — stop. Designing against an unwritten specification produces a design for the wrong thing. Tell the user to run `$delivery:prd` and offer to run it now.
- **Non-functional requirements are vague or absent** — flag it. The architect needs numbers to design against; without them the design cannot be checked. Ask the user for the numbers or accept explicitly that the design is unvalidated on those axes.

If `.delivery/initiatives/<initiative>/architecture.md` already exists, read it and ask
whether to **revise**, **replace**, or **start new version**. See
`../../templates/version-history.md` for what each means, the same-problem
test that chooses between revise and start new version, and the Version-history table and
Corrections log it writes. Never silently overwrite.

**Open blocking findings.** Apply the conventions' *Open blocking findings* check to every artifact this phase consumes before going further.

## Run

If a product record exists, read the [product contract](../../references/product.md).
Use the smallest sufficient work form, autonomy and engine; do not assume that a
plugin needs a new service or persistent agent. Before changing mapped files,
run `product.py --project <planning> --repo <git-root> impact --path <file>` and
inspect stale/unknown coverage. Preserve shared consumers and the owner's stated
intent. Greenfield may start with planned features and no source repository;
label proposed file paths as new and link them only after actual code exists.

**1. Establish the starting state before designing.** For brownfield, read the
actual code first: affected modules, patterns, conventions and existing interfaces.
Verify those paths. For greenfield with no repository or implementation, state
that explicitly and read the supplied problem, PRD, owner choices and constraints.
Do not demand existing code or invent verified paths. Describe proposed new paths
under a proposed root, label interfaces and toolchain choices as proposed, and
put repository/toolchain setup in the Setup section. Source absence is a starting
state, not a failed prerequisite for creating the design.

**2. Solution Architect produces the design.** Use the `solution-architect` lens. It must deliver:
- Component structure with **verified existing paths or explicitly proposed new paths**, marking modified, extended, untouched and new components separately
- Interfaces and data contracts
- How each `NFR-n` from the PRD is met, addressed one by one
- Alternatives considered and why rejected, for every consequential decision
- The **spike list**: assumptions that must be proven before committing, each with a specific question, the decision it informs, a decision rule (which result means build, change the design, or stop), its decision owner (DM, PM, or the owner when it decides scope) and a time box
- The **assumption register**: every claim the design rests on that nobody has yet seen hold, each with its kind (`external-host` for how a host we do not control behaves, else `platform`, `data`, `customer` or `internal`) and the acceptance criteria it sits on
- Migration and rollback plan for any change to persisted data or public interfaces
- Risk register

**3. QA Strategist adds the test strategy.** Use the `qa-strategist` lens for the risk-based plan: what is tested at which level, where coverage is deliberately thin and why, and how the non-functional numbers get measured.

**4. Critic passes over it.** Use the `feature-critic` lens (read-only) to find the unstated assumption. Fold the blocking findings in before writing; report the rest.

**5. Write the design** to `.delivery/initiatives/<initiative>/architecture.md` using `../../templates/architecture.md`. Write each consequential decision as its own ADR in `.delivery/decisions/ADR-NNN-<slug>.md` using `../../templates/adr.md`.

**6. Write the assumption register** using `../../templates/assumptions.md`.
Keep new assumptions `assumed`; source-reading, mocks and twins do not establish
behavior in an external host. Give each external-host assumption a real-host spike,
a decision owner and affected story criteria. Link actual probe evidence before
changing its status. These are planning records; this preview does not enforce claim gates.

**7. Declare the customer surface** in the initiative's `surface.json` from
`../../templates/surface.json`: host, app, mode, install artifact, scriptability and
numeric size budgets. Cite the user's actual decision in `owner_record`, or mark it
unknown. One surface is normal; add another only when it belongs to the requested
scope. Every story names its surface. Read the JSON back and check its fields and
references; this preview has no upstream surface validator or done gate.

## Exit criteria

- Within the template's budget, or the overrun declared in the document with its reason — measure prose when computation is available; otherwise report word count unverified

- Existing component paths are verified where source is available; greenfield/new paths are explicitly proposed, with the absent repository/implementation stated
- Every `NFR-n` in the PRD is addressed explicitly, or listed as unmet with the reason
- Every consequential decision has stated alternatives
- The spike list exists — or the document states plainly that nothing needs proving, which is rare enough to justify — and every spike names its decision, decision rule and decision owner
- `assumptions.md` exists, every `external-host` assumption has a spike, and its criteria, statuses and evidence links have been manually checked
- Migration and rollback are covered, or explicitly not applicable
- Test strategy is present
- `surface.json` is valid JSON and its host/app/mode/install-artifact declarations and story references have been manually checked

## Writing, then revising

**Budget: 1000 words target, 1600 hard cap** (excludes code, YAML and data tables). Compose, measure and revise as *Writing, then revising* in the conventions says.

## Hand off

Report exit criteria status, and surface the spike list prominently — the Program Manager needs it to sequence the plan. If the design revealed that a requirement is disproportionately expensive, state the tradeoff for the Product Owner rather than quietly simplifying it. Next step: `$delivery:roadmap`.
