# Product brief: translator-handover

> Written using the brief skill. Owner: benchmark requester.
> Status: draft · Last updated: 2026-10-20

**Mode:** Frame · **Word count:** 547 words (cap 900).

## Coverage

**Single-session review:** sequential value, precision and absence passes used the same raw input, [idea.md](../../../idea.md). Independent convergence is unavailable; agreement within this session is not independent evidence. Each lens surfaced distinct material, so the space is **not exhausted**. These are framing findings, not observed customer defects.

| Lens | Ran | Distinct finding |
| :-- | :-- | :-- |
| Value — product-owner | Yes | V: The benefit of a separate checklist is unverified; maintaining it could add effort without preventing omissions. |
| Precision — business-analyst | Yes | P: Changed or conflicting client requirements have no stated completion rule; a checked item could describe an outdated request. |
| Absence — feature-critic | Yes | A: A requirement omitted from the checklist cannot be caught by checking it; a perfect recorded-requirements score could conceal an incomplete handover. |

**Findings by independent convergence:** unavailable. V, P and A are single-lens findings, retained despite the lack of independent corroboration. V needs evidence of useful prevention; P needs a worked change example; A needs comparison with original client requests. None is resolved by the input.

## Problem

**Synthetic hypothesis:** solo freelance translators keep client handover requirements in scattered notes and may omit requested files when preparing a handover. This describes the proposed present-day problem, not a verified pattern. The source supplies no customer observations or examples of actual omissions. [Source: idea.md](../../../idea.md).

## Who has it

Solo freelance translators responsible for preparing their own client handovers. The size of this segment and the frequency of the hypothesized problem are unknown. No interviews establish how translators currently check their work.

## Cost of the status quo

An omitted requested file could require another exchange with the client and rework by the translator. Those consequences are plausible inferences, not supplied evidence. Error rates, time savings and willingness to pay are absent. Scattered notes are the only source-described workaround; their format and actual use remain unknown.

## What changes if we solve it

**Proposed outcome:** before sending files, a translator can see the recorded client requirements for a handover and identify anything still unchecked. For example, if a client requests a translated file and an accompanying file, the translator can check each separately. This example is illustrative, not a customer case. Sending remains the translator's separate action.

## Success signals

| Signal | How measured | Current | Target |
| :-- | :-- | :-- | :-- |
| Proportion of handovers meeting recorded client requirements | Handovers whose prepared files meet every recorded requirement divided by handovers reviewed; retain the underlying requirement and file comparison. Define review period and treatment of changed requirements before measurement. | Unknown; no handover data supplied or collected here | Open, benchmark requester |
| Completeness of recorded client requirements — proposed safeguard for A | Compare the checklist with original client requests and report missing requirements separately. Checking boxes alone does not establish completeness. | Unknown; original client requests unavailable | Open, benchmark requester |

The candidate signal comes from the input. Neither signal can currently be calculated. A successful demonstration of a checklist would verify behavior, not establish customer benefit.

## MVP boundary

**Proposed, awaiting validation:** a local checklist tied to a handover, with client requirements entered by the translator, editable wording, and a visible checked or unchecked state. The translator reviews the prepared files against the checklist before sending. A changed requirement must remain visible for review; its effect on prior checks is open in P.

Start with the omission hypothesis. Do not expand into translation production or client management to compensate for missing evidence. The brief does not select a platform, storage design or delivery estimate.

## Explicitly out of scope

- Integrations, billing and automatic sending, as stated in the input.
- Translation generation or translation-quality assessment, proposed exclusions to keep this about handover requirements.
- Shared team coordination, a proposed exclusion for the solo segment.

## Current-state workflow

**Hypothesis reconstruction, not observation:** a client specifies requirements; the translator retains scattered notes, prepares the files, checks what to send and sends the handover. Only scattered notes and possible omitted requested files are supplied. The ordering, checking method and handling of later requests need validation. No application code exists in the supplied project to establish current behavior.

## Open questions

All questions remain **open**, owned by **benchmark requester**. Per the bounded-test instruction, they are recorded together without waiting for replies.

| ID | Question, with an illustrative example | Owner | Blocks |
| :-- | :-- | :-- | :-- |
| V | What real handover shows this problem, and what did the omission cost? For example, did a missing accompanying file cause another exchange? | benchmark requester | Evidence of value and priority |
| P | If the client replaces a requested file format after it was checked, should the translator check it again? What if requests conflict? | benchmark requester | Requirement-change and completion rules |
| A | How will the translator notice a request missing from the checklist? For example, will they compare it with the original client message? | benchmark requester | Confidence in requirement completeness |
| S | What improvement would justify using this checklist, over what review period? For example, what proportion of complete handovers would count as useful? | benchmark requester | Success target and baseline plan |
| L | What does local mean here? For example, must a saved checklist remain usable without an internet connection, and on which device? | benchmark requester | Product boundary and persistence expectations |
| H | What counts as a handover? For example, is a later corrected file part of the original handover or a separate one? | benchmark requester | Measurement denominator and checklist grouping |
