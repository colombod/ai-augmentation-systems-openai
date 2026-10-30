# Compact first product record

Base/main: `a46dc827826c9d641f5e745101f4cc14fcf1a21b` (merged PR #2,
Delivery `0.1.0-preview.7`). New helper source:
`8e01b536b2ba7ebf47f4c61a3cc42a8904b94aec`, preview `0.1.0-preview.8`.

The previous walkthrough required a complete schema including repeated Unknown
cards and choice metadata. `draft --outline` now expands compact customer/feature
notes into a complete record input on stdout. It does not save, confirm an owner,
infer shipped status or assign usefulness evidence. A separate `record` preserves
the existing expected-hash/history boundary. This is an initial-record aid; sparse
notes must not silently replace an existing record's owner decisions.

Actual public-command results are retained beside this file. Brownfield uses two
real Delivery capabilities and their code/test routes, then answers the shared
`project.py` impact question. Greenfield is a labelled illustrative idea with no
Git or code. Draft creates no canonical record; record/handoff work normally.
Both retain proposed customer choices, planned default states and all six
usefulness judgements Unknown. A source file's existence is not user evidence.

| Case | Authored outline bytes | Expanded input bytes | Public commands |
|---|---:|---:|---|
| Actual Delivery source, two mapped features | 722 | 8118 | draft, record, handoff, impact |
| Illustrative no-code idea, one feature | 290 | 5748 | draft, record, handoff |

These are actual serialized input sizes, **not** measured time savings, stranger
usability or adoption. The input must still name meaningful features and routes;
automatic feature discovery or graph completeness is not claimed. Existing code
and evidence routes are checked at HEAD; invalid paths/typos and oversized
expansion fail before any record is written. Explicit attributed decisions may be
carried in the outline; ordinary strings remain proposed. Shape defaults are
explicitly unassessed at autonomy zero, not an architecture recommendation.

`checks/`: 145 Python tests, 22 Node tests and marketplace validation passed.
The updated isolated CLI 0.163.0 installation probe discovered 16 skills from
preview.8 and executed the installed helper's draft→record→handoff path, with
unconfirmed choices retained and zero model calls. Independent read-only review
reran 23 focused product tests and all 145 Python tests and found no source,
provenance, compatibility or recordability blocker. Diff checks passed.

An initial size-limit regression fixture expanded to 3,992,641 bytes, below the
4,000,000-byte limit, so its expected failure was incorrect. The retained review
observation was resolved by using an actually oversized fixture; source behaviour
was not weakened to satisfy it. Existing native model startup limitations remain
unchanged and were not retried here. No credential, outside-user, dot, desktop or
ChatGPT workflow proof is claimed. PR #1 remains separate and unmerged.
