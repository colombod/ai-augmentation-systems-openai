# Product brief: Tiny ASCII slugifier

> Written using $delivery:brief. Owned by Product Manager.
> Status: draft · Last updated: 2026-10-20

**Mode:** frame · **Word count:** 468 (cap 900)

## Coverage

Single-session review used the value, precision and absence lenses sequentially. Independent convergence is unavailable. Each lens surfaced a different concern; the space is not exhausted. This draft bounds the requested CLI behavior without claiming validated customer demand.

| Lens | Ran | Finding unique to this lens |
| :-- | :-- | :-- |
| Value | Yes | The intended terminal user needs repeatable output; actual frequency and time savings are unverified. |
| Precision | Yes | Unicode case conversion before ASCII filtering can retain unintended characters; the rule applies to original characters. |
| Absence | Yes | All-separator text must produce an empty line; missing text must be distinguishable through exit status. |

**Findings by independent convergence:** unavailable.

## Problem

A terminal user converting text to an ASCII slug needs a predictable rule for punctuation, spacing and Unicode. Inconsistent conversion can produce different identifiers for the same text. This is the supplied problem framing, not an observed customer incident.

The product currently contains a README requesting an ASCII-only terminal slugifier, with no implementation visible in the inspected product files. Sources: product `README.md` and planning `initiatives/slugify/delivery-plan.md`.

## Who has it

Developers and script authors invoking Python from a terminal to convert a single text value. This segment is inferred from the requested interface; audience size and actual usage are unknown.

## Cost of the status quo

Manual conversion or ad hoc commands require the caller to remember consistent character rules. That workaround and its error cost are hypotheses; no usage, timing or defect measurements were supplied.

## What changes if we solve it

The caller invokes `python3 slugify.py TEXT` and receives a deterministic slug followed by a newline. For example, `"  Café / MIX 42! "` yields `caf-mix-42`. Unicode outside ASCII separates retained characters; it is never transliterated.

## Success signals

| Signal | How measured | Current | Target |
| :-- | :-- | :-- | :-- |
| Contract correctness | Future local CLI checks compare exact stdout and exit status with the story | Not measured; no tests run | Every specified behavior matches |
| Boundary correctness | Future checks include original Unicode, separator runs, edge trimming, all-separator input and missing TEXT | Not measured | All checks match the contract |

Hosted CI is not present. Draft persistence does not demonstrate executable behavior.

## MVP boundary

One Python CLI file, `slugify.py`, in product root `/private/var/folders/2r/5gvkx5wx0g37m4grvjjdt88m0000gn/T/delivery-full-cli-8frrftqa/product`. The executable contract is recorded in the single story, `stories/slugify-cli.md`: retain ASCII letters and digits, lowercase retained uppercase letters, collapse runs of all other original characters to hyphens, and trim edge hyphens. Successful conversion prints one newline and exits 0; missing TEXT exits 2.

## Explicitly out of scope

- Unicode transliteration or locale-specific conversion.
- Batch input, stdin, file processing, packaging and hosted services.
- Additional product features or extra acceptance criteria.
- Implementation, test execution, tracker changes and approval in this drafting stage.

## Current-state workflow

The supplied workflow starts with a caller holding text and wanting a terminal conversion. Existing manual steps are unobserved. The product README records the requested capability; no existing conversion workflow was available to inspect.

## Open questions

No unresolved question blocks this narrowly specified draft. Audience demand and quantified savings remain unverified; Product Manager owns validation before broader investment. Behavior beyond the supplied invocation contract is outside this slice.

## Proposed vocabulary

No glossary exists. Proposed term: **ASCII slug** means the output formed by the stated retained-character and separator rules; `caf-mix-42` is a concrete example. This definition adds no transliteration requirement.
