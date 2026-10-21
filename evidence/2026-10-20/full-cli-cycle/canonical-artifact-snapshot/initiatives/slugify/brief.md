# Product brief: Tiny ASCII slugifier

> Written using delivery:brief. Owned by Product Manager.
> Status: draft · Last updated: 2026-10-20

**Mode:** frame · **Word count:** 433 (cap 900)

## Coverage

Single-session review using sequential value, precision and absence lenses. Independent convergence is unavailable. Each lens surfaced a distinct concern; the space is not exhausted. This draft frames only the bounded CLI contract.

| Lens | Ran | Distinct finding |
| :-- | :-- | :-- |
| Value | Yes | Shell users need predictable text conversion; user demand and time savings are unverified. |
| Precision | Yes | Unicode-aware character classes or lowercasing could violate the ASCII-only contract. |
| Absence | Yes | Empty results and missing arguments need observable outcomes so scripts can distinguish them. |

Source: the supplied drafting request and existing `delivery-plan.md` in this initiative. Product inspection found only `README.md`, which describes the intended fixture; no CLI implementation was observed. No product tests have run. Hosted CI is not present.

## Problem

The fixture currently provides no executable text-to-slug command. A shell user needing a consistent ASCII label must supply their own conversion. Inconsistent handling of punctuation and Unicode can produce different labels for the same text.

The user need and workaround are product assumptions, not findings from interviews.

## Who has it

Developers and script authors working in a terminal who need a deterministic ASCII slug from a text argument. Audience size and usage frequency are unknown.

## Cost of the status quo

Assumed costs are repeated manual editing or ad hoc scripts, plus errors from differing separator rules. No time, financial cost or error-rate baseline has been collected.

## What changes if we solve it

A terminal user invokes `python3 slugify.py TEXT` in the product root and receives a predictable line suitable for capture by a shell script. For example, `" Hello, WORLD! "` becomes `hello-world` followed by a newline.

## Success signals

| Signal | How measured | Current | Target |
| :-- | :-- | :-- | :-- |
| Contract correctness | Observe stdout and process exit status for ordinary text, separator runs, edge separators, Unicode, all-separator text and missing TEXT | Unverified; no execution evidence | Every specified behavior matches the story |
| Repeatability | Invoke the same text repeatedly and compare output | Unverified | Identical output |

## MVP boundary

Deliver `slugify.py` in product root `/private/var/folders/2r/5gvkx5wx0g37m4grvjjdt88m0000gn/T/delivery-full-cli-3b8pu1g_/product`.

Accept exactly one text argument. Lowercase ASCII A-Z, replace each maximal run outside ASCII [A-Za-z0-9] with a hyphen, trim edge hyphens, and print the result followed by a newline with exit 0. Unicode outside ASCII acts as a separator. All-separator text prints an empty line. Missing TEXT exits 2.

## Explicitly out of scope

- Transliteration, Unicode alphanumeric retention and locale-specific conversion.
- Batch processing, stdin input, file output and packaging.
- Collision avoidance, uniqueness guarantees and URL validation.
- Additional acceptance requirements for extra arguments or diagnostic wording.

## Current-state workflow

The observed product README asks for an ASCII-only terminal slugifier. The assumed current user workflow is to edit text manually or write a conversion script, then inspect its output. That workflow has not been observed with real users.

## Open questions

No blocking question remains for the specified contract.

| Question | Owner | Blocks |
| :-- | :-- | :-- |
| How often do terminal script authors need this conversion, and what errors occur today? | Product Manager | Value validation; does not block this fixture draft |

Proposed glossary term: **slug** means the resulting lowercase ASCII alphanumeric text with internal separator hyphens; for example, `hello-world`. No separate glossary artifact is created in this bounded drafting stage.
