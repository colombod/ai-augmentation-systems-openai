---
name: brief
description: "Frame a feature idea, or assess an existing product, and produce a brief. Use at the very start \u2014 when the idea is still a sentence, or when you need an honest account of what a working product gets wrong today. Produces .delivery/initiatives/initiative/brief.md."
---

# Product brief

Subject: **the user's request**

DEFINE stage, the entry point. Output: `.delivery/initiatives/<initiative>/brief.md`.

## Conventions

Read [host capability guidance](../../references/runtime.md) and
[delivery conventions](../../references/conventions.md) before running this phase.

## Pick the mode first, and say which

The two jobs are different sizes and different documents. State the mode in the brief's header.

| Mode | When | Budget |
| :-- | :-- | :-- |
| **Frame** | A new feature or product. The problem is ahead of you. | target 600 words, cap 900 |
| **Assess** | An existing, working product. The problems are already in the code. | target 1200 words, cap 2000 |

If the target is an existing codebase and the request is to evaluate it, that is **assess**.
A new capability for an existing product is **frame** — the existing product is context,
not the subject.

## Gate check

Read [the shared product contract](../../references/product.md) and any existing
`.delivery/product-map.json`. Reuse its customer, job, proposition, explicit cuts,
owner intent and what must survive. Keep proposed/unknown choices distinct from
owner statements. For a new greenfield idea, `$delivery:product` can establish
these without a repository; for existing work it also maps observed features and
checks current source. Do not substitute a code inventory for a customer problem.
Carry the product choices and their revisit conditions into the brief; do not
silently broaden the customer or resurrect a deliberate cut.

No prerequisites — this is the entry point. If `.delivery/initiatives/<initiative>/brief.md`
already exists, read it and ask whether to **revise**, **replace**, or **start new version**.
See `../../templates/version-history.md` for what each means, the
same-problem test that chooses between revise and start new version, and the
Version-history table and Corrections log it writes. Never silently overwrite.

## Run

**1. Understand the ground truth.** If a codebase exists, read it before writing anything
about what should be. Note the current behavior, and how you would verify a claim about it.

**2. Find, convergently — this is the part that determines whether the brief is any good.**

A single analytical pass finds *some* of what is there, not the most important of it. Two
passes over the same code, prompted the same way, return overlapping-but-different sets, and
the difference is not correlated with severity. Running once and reporting the result as
"the problems" overstates what one pass knows.

Use at least three different lenses. When native delegation is available and
authorized, give separate read-only reviewers the same raw inputs and keep their
findings separate until synthesis. Otherwise use sequential passes in this
session, labeled single-session review. Do not require unavailable delegation.

| Lens | Review lens | Asks |
| :-- | :-- | :-- |
| Value | `product-owner` lens | Who has this problem, what does it cost them, what would success look like |
| Precision | `business-analyst` lens | What is ambiguous, what cases are unhandled, what numbers are missing |
| Absence | `feature-critic` lens | What is *not* here that should be — the unasked question, the missing state |

In **assess** mode add a fourth:

| Decay | `qa-strategist` lens | What was true when written and is not true now — dated data, expiring calendars, stale rates, assumptions with a shelf life |

That lens exists because temporal defects are invisible to structural review. A test suite
checks whether data has the right shape, never whether it is still true.

If independent reviewers are unavailable, use sequential lens passes and explicitly
label the result **single-session review**. Do not count agreement as independent convergence.

**3. Merge and report the actual review mode.** Deduplicate. For isolated native
reviewers, record how many found each issue independently. In single-session
mode, record which lens raised each issue but mark independent convergence
unavailable; repeated agreement is not independent evidence. Keep findings
raised by only one lens rather than hiding uncertainty.

Then state the coverage honestly: if each lens surfaced material the others did not, the
space is **not exhausted**, and the brief should say so rather than implying completeness.

**4. Verify before asserting.** Any finding with a number in it — a count, a price, a date —
gets checked against the source before it enters the brief. Specific, confident and wrong is
the worst thing this phase can produce, because precision reads as authority.

**5. Ask what you cannot determine.** Collect open questions, drop the ones the codebase
answers, put the rest to the user in one batch. Record what stays unanswered. Never invent
an answer, and never quietly drop a question because it is inconvenient.

**6. Write** to `.delivery/initiatives/<initiative>/brief.md` using `../../templates/brief.md`.

## Exit criteria

- Mode stated, and the document within that mode's cap — **or the overrun declared in the document with its reason**. Measure prose when computation is available; otherwise report word count unverified.
- Review mode stated, at least three lenses used, and independent convergence recorded only when reviewers were actually isolated
- Coverage stated: whether the finders agreed enough to call the space explored
- Every numeric claim verified against its source
- A named user segment, not "users"
- The problem stated as something happening today, with its cost
- At least one measurable success signal
- Explicit out-of-scope list
- Open questions with owners, where any remain

## Writing

Obey `../../templates/writing-standard.md`.

The budget above is a hard check, not an aspiration. Before finishing, measure prose excluding code, YAML and data tables with
an available computation tool. If none is available, state word count unverified;
do not invent a count or claim the budget check passed. Over the cap, cut restatement, process narration and
hedging — never findings, citations, grounding labels, open questions or IDs. If it still
does not fit, keep the substance and **write the overrun and its reason into the document**.
A declared overrun is a judgement; a silent one is a habit.

## Hand off

Report exit criteria status, the convergence picture, and anything found by only one lens.
If the finders disagreed enough that the space looks unexplored, say so — that is a reason
to run again, not to proceed.

Next step: `$delivery:challenge .delivery/initiatives/<initiative>/brief.md`, then `$delivery:research`.
