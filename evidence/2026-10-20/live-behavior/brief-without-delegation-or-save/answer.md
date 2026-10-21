# Product brief: checkout-redesign

> Written using $delivery:brief. Ownership: Product Owner and Business Analyst; individuals unassigned.
> Status: draft · Last updated: 2026-10-20

**Mode:** Frame · **Word count:** unverified (cap 900).

**Intended filename:** `.delivery/initiatives/checkout-redesign/brief.md`  
**Delivery status:** prepared, not saved to the canonical store.  
**Source revision:** user request supplied in this conversation; unversioned.  
**Changes:** initial initiative framing. No prior artifacts were supplied; existing briefs, glossary, blocking reviews, and namespace collisions could not be checked.

## Coverage

**Single-session review:** sequential value, precision, and absence passes using the supplied reviewer lenses. Independent convergence is unavailable; agreement within this session is not independent evidence.

| Lens | Ran | Material unique to this lens |
| :-- | :-- | :-- |
| Value | Yes | Wasted checkout effort and lost completed orders |
| Precision | Yes | Meaning of “too late,” delivery-cost rules, measurement gaps |
| Absence | Yes | Affordability as an alternative explanation; unavailable or changing quotes |

Each lens surfaced distinct material. The space is **not exhausted**.

| Finding | Lens | Grounding and consequence | What resolves it |
| :-- | :-- | :-- | :-- |
| F-V | Value only | User-reported abandonment implies lost purchasing opportunities; scale and commercial cost are unknown. | Establish affected journeys and baseline outcomes. |
| F-P | Precision only | “Too late” names no checkout step. A redesign could move costs earlier without meeting shoppers’ decision needs. | Identify first cost exposure and when shoppers need it. |
| F-A | Absence only | Earlier disclosure helps informed choice, but conversion improvement is unverified. Shoppers might reject the price regardless; inaccurate estimates could add another surprise. | Investigate reasons for leaving and quote reliability. |

## Problem

Phone shoppers abandon checkout after discovering delivery costs too late, according to the user request. The timing prevents them from assessing the purchase’s affordability before investing effort.

This is a reported problem, not an observed funnel or verified causal explanation. No codebase, analytics, shopper research, or checkout captures were supplied.

## Who has it

Phone shoppers who enter checkout and discover delivery costs later than they expected. Their number, markets, purchase types, and guest or returning status are unknown.

## Cost of the status quo

Affected shoppers spend effort on purchases they subsequently abandon. The business loses potential orders. Revenue impact, time spent, and any loss of trust are unmeasured. Current workarounds are unknown.

## What changes if we solve it

A phone shopper can understand the applicable delivery cost early enough to decide whether to continue. If essential information is missing, the shopper understands what remains unknown and what is needed to obtain a reliable cost.

The proposed value is an informed purchase decision. Increased completed orders remains a hypothesis.

## Success signals

No evidence of existing measurement was supplied. Establish baselines and agree targets before evaluating impact.

| Signal | How measured | Current | Target |
| :-- | :-- | :-- | :-- |
| Phone checkout completion | Completed orders divided by phone checkout starts, using an agreed completion window | Unknown; collection unverified | Improvement against an agreed comparison |
| Delivery-cost surprise | Consistent shopper question or usability observation about whether costs appeared when expected | Unknown; collection unverified | Fewer reports of unexpected late costs |
| Delivery-cost accuracy | Compare the earlier displayed cost with the final charge, accounting for shopper changes | Unknown; collection unverified | Agreed acceptable discrepancy level |
| Checkout effort | Time and exits before shoppers can establish delivery cost | Unknown; collection unverified | Less effort without harming completion |

Earlier disclosure may move exits earlier without increasing orders. Interpret completion and shopper understanding together.

## MVP boundary

**Proposed scope:** let phone shoppers establish delivery costs before substantial checkout effort. The precise disclosure point depends on current behavior and the information needed to calculate costs.

Cover the observable states: cost known, information needed, quote unavailable, and cost changed after a shopper changes their purchase or delivery details. Distinguish estimates from confirmed amounts. Preserve entered information when shoppers correct details or retry.

Select the initial market and purchase coverage after confirming delivery rules; neither is assumed here.

## Explicitly out of scope

- Changing delivery prices, subsidies, or free-delivery policy.
- Rebuilding unrelated payment, account, or checkout features.
- A general desktop redesign.
- Carrier or fulfilment replacement.
- Guaranteed conversion uplift.

## Current-state workflow

The supplied request establishes this partial sequence:

1. A phone shopper enters checkout.
2. They discover delivery costs late in that journey.
3. They abandon checkout.

The intervening screens, information entered, exact disclosure point, and subsequent actions are unknown. No workaround is established.

## Open questions

These remain unanswered because the user cannot provide more information now. Owners are proposed roles.

| ID | Question | Owner | Blocks |
| :-- | :-- | :-- | :-- |
| Q-A | Where do shoppers first see delivery costs, and what have they already entered? | Product Owner | Disclosure-point decision |
| Q-B | What evidence distinguishes unexpected timing from an unaffordable delivery price? | Research lead | Causal confidence and value claim |
| Q-C | What determines the charge—for example, destination, purchase contents, or delivery option—and when can it be confirmed? | Delivery operations owner | Reliable MVP boundary |
| Q-D | Which markets and purchases belong in the initial release? | Product Owner | Release scope |
| Q-E | Which journey events are collected, and what comparison, targets, and completion window should determine success? | Analytics lead and Product Owner | Outcome evaluation |
| Q-F | When a quote fails or changes, what can shoppers reliably be told? | Delivery operations owner | Failure-state behavior |

## Proposed glossary additions

No existing glossary was supplied. These definitions await Product Owner agreement.

| Term | Proposed definition | Concrete referent |
| :-- | :-- | :-- |
| Phone shopper | A person shopping on a phone | The shopper named in the request |
| Delivery cost | The amount charged to deliver the purchase | The charge discovered late in checkout |
| Checkout abandonment | Starting checkout without completing an order within an agreed window | The reported exit; measurement window unresolved |

“Too late” remains an unresolved timing decision, not a defined checkout step. No synonyms were resolved.

## Handoff

Framing criteria are addressed: named segment, reported current problem and cost, measurable signals, scope exclusions, and owned unknowns. Exact word count, independent convergence, persistence, and external artifact checks remain unverified.

All findings are single-lens findings. Coverage remains incomplete; revisit the lenses with journey evidence before treating the framing as settled.

Next: `$delivery:challenge .delivery/initiatives/checkout-redesign/brief.md`, using this prepared document, then `$delivery:research`.