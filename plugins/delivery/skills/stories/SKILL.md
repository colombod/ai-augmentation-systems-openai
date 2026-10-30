---
name: stories
description: "Decompose a roadmap phase into self-contained, implementation-ready story files that carry their full context. Use when a phase is about to start and the work needs to be broken into pickable units. Produces .delivery/stories/."
---

# Story decomposition

Phase or epic to decompose: **the user's request** (defaults to the first phase not yet decomposed)

CONTRACT stage. Inputs: `.delivery/initiatives/<initiative>/prd.md`, `.delivery/initiatives/<initiative>/architecture.md`, `.delivery/initiatives/<initiative>/roadmap.md`, plus `design-system.md` where it exists. Output: `.delivery/stories/`.

## Conventions

Read [host capability guidance](../../references/runtime.md) and
[delivery conventions](../../references/conventions.md) before running this phase.

## Gate check

Choose the full-pipeline route below or the explicit [bounded-change route](../../references/bounded-change.md).
For `route: bounded-change`, read available prior artifacts and list missing ones;
the self-contained story substitutes the compact goal/scope/design/acceptance
contract for PRD/architecture/roadmap prerequisites. Preserve all readiness,
open-finding and authority checks. Do not invent missing documents.
For the full-pipeline route, read all three inputs. List existing stories in both routes.

Read any shared product record and the [product contract](../../references/product.md).
Greenfield may have no repository or implementation. That does not prevent story
decomposition from the supplied PRD/design/roadmap: preserve planned features and
proposed new paths, never invent existing code or a working test command.

- **Roadmap missing on the full-pipeline route** — stop and run `$delivery:roadmap` first. Without it there is no defensible phase boundary to decompose along.
- **Architecture missing on the full-pipeline route** — warn hard. Stories written without a design either omit the technical context (making them un-pickable) or invent a design inline (which is the Solution Architect's job, done badly). Recommend running `$delivery:architecture` first.
- **Setup, not a feature** — if the item is pure environment/repo/framework/build-system setup (no persona completes a journey through it), refuse to write it as a story; point back to `architecture.md`'s Setup section, where it belongs as a Phase-1-gating prerequisite, not a phase deliverable.
- Never overwrite a story whose status is `in-progress` or `done` — supersede it instead, per the protocol below.

## When a ruling invalidates existing stories

A decision that lands mid-flight does not entitle you to rewrite history. What you do
depends on whether work has started, and **nothing is ever deleted** — a story is a record
of what was intended, and deleting it destroys the reason the code looks the way it does.

| Status | What to do |
| :-- | :-- |
| `draft` | Revise in place. No work is lost and nothing referenced it yet. |
| `ready` | Revise in place, and note in the story what changed and which ruling caused it. Someone may have read it. |
| `in-progress` | **Coordinate stopping active work with its owner first; do not terminate it unilaterally.** Mark `superseded`, record what was actually built, and say whether that partial work is kept, reverted, or left for the replacement to absorb. Then write the replacement. |
| `done` | Mark `superseded`. It shipped — the record stands as the explanation for code that exists. Write a new story for the change. |

**Link both directions.** The old story gets `superseded_by: [<new-id>]` and a one-line
reason. The new story gets `supersedes: [<old-id>]`. Without both, the next reader finds a
story describing behaviour the code does not have and cannot tell whether it is stale or
broken.

**Give the reason, not just the link.** "Superseded by p1-15" says nothing. "Superseded by
p1-15: the owner ruled that out of season the estimate is disabled rather than falling back
to a minimum rate" tells a future reader why the design changed, which is the part worth
keeping.

**A superseded story is not a failed story.** It records a decision that was correct given
what was known. Treat the supersession as information about how the understanding moved,
and say so in the sprint review's calibration section — a design that supersedes often is a
design being learned, and that is worth knowing.

Resolve the target phase from the request/roadmap, or the bounded-change outcome from its explicit compact contract. State the selected scope and route before starting.

**Open blocking findings.** Apply the conventions' *Open blocking findings* check to every artifact this phase consumes before going further.

## Run

**0. Decompose once, then choose an available drafting mode.**

Deciding *what the stories are* is one judgement over the whole phase and must happen once,
in sequence: the slice boundaries, the dependency order, what each story owns. That is fast.

**Writing** them is not one judgement — it is N independent ones. Each story is
self-contained by construction, so nothing in story 7 depends on the prose of story 3.
When native delegation is available and authorized, dispatch drafts in parallel, one
reviewer per story, passing the decomposition, slice and shared context. Reviewers
return drafts without writing files; reconcile and write centrally. Otherwise write
sequentially, explicitly naming the single-session mode.

Sequential drafting is the valid fallback when delegation is unavailable or
prohibited. Do not claim a speedup or independent review without observing it.

Then reconcile centrally: interfaces named in one story must match the others, dependency
IDs must resolve, and no two stories may claim the same file for the same change. That
check is cheap and it is the only part that genuinely needs the whole set in hand.

**1. Delivery Manager decides the decomposition.** Use the `delivery-lead` lens.

The governing rule: **the story file is the complete context.** Someone opening one story file — a teammate who missed the planning, or an agent with no memory of it — must have everything needed to finish it. Extract the relevant slices of the PRD and architecture *into* the story. Do not link out. A story requiring three other documents to be read has failed at its one job.

Each story carries: the owner's ask (quoted only when actually supplied), its
declared customer surface, falsifiable customer outcomes traced to `FR-n`, one
probe per criterion, measurement plan, shippable unit and user-facing goal. Embed
verified existing paths or explicitly proposed new paths, interfaces, relevant
architecture decisions, dependencies and cuts. Include the real test command
when established; otherwise label the proposed command and the setup/verification
needed before execution. Neither a proposed path nor a command is observed code
or a passing test. An unknown owner ask remains unknown, not a fabricated quote.

**2. Each writer carries the design system into its UI story.** Where `design-system.md` exists, each story touching UI names the **tokens by their real project name**, the component states it must implement (including error and empty), and the accessibility rules that apply. An implementer who cannot find the token reaches for a raw value, and the design system erodes one commit at a time — naming them in the story is what prevents that.

**3. Verify each path's state.** Existing paths must be checked against available
source. New files are labelled **proposed new** with a create action; check for
collisions when a repository exists. With no repository, state that path/root
availability is unverified and carry the architecture setup prerequisite, or
the explicitly embedded setup prerequisite on the bounded route. Do not
require a file that the story is meant to create to already exist. Keep proposed
routes separate from the product map's observed code links until code is present.

Where a product record and code are available, `product.py ... impact --path <file>
--transitive` can inform which feature promises the story may affect. Cite its
recorded commit, direct versus possible import reach and coverage/staleness. This
is informational, not a readiness gate: if absent, unsupported or unavailable,
record the reason and continue the existing planning-readiness assessment. No-code
greenfield paths remain proposed rather than invented observed graph links.

**4. QA Strategist sets the test approach** per story — the level, the negative and boundary cases, and how it is verified.

**5. Planning readiness check.** For each story, verify falsifiable customer outcomes,
path states, required sections, declared surface, dependencies and a concrete test
approach. Greenfield can produce a complete draft while setup or command
availability remains unverified; name the execution prerequisite rather than
blocking all planning on absent code. Record `ready` only as **planning-ready,
manually reviewed**, never execution authority. Missing planning inputs leave it
`draft`. The separately configured local runtime has controlled materialisation
and evidence gates; a story label alone does not satisfy those gates or start
builders. Changed criteria require renewed review and retained document history.

**6. Write the stories** to `.delivery/stories/<initiative>-<epic>-<nn>-<slug>.md` using `../../templates/story.md`, and update the story index at `.delivery/stories/README.md`.

## Exit criteria

- Within the template's budget, or the overrun declared in the document with its reason — measure prose when computation is available; otherwise report word count unverified

- Every story is a vertical slice delivering observable behavior, or states why it cannot be
- Every acceptance criterion in the target phase is covered by at least one story
- Every path is labelled verified existing or proposed new; unavailable source/setup and unverified test commands remain explicit
- Dependencies between stories are explicit
- Each story is finishable in one focused sitting, or is split

## Writing, then revising

**Budget: 700 words target, 1200 hard cap** (excludes code, YAML and data tables). Compose, measure and revise as *Writing, then revising* in the conventions says.

## Hand off

Report: stories written, how many are `ready` versus `draft`, and what each draft is missing. Flag any acceptance criterion in the phase that no story covers. Next step: `$delivery:sprint` to scope a wave for an implementation runner.
