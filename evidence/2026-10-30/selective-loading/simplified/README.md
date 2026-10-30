# Simplified candidate — improvement not yet established

Base/main: `a46dc827826c9d641f5e745101f4cc14fcf1a21b`.
Candidate source for model evaluation: `74d9e6a9a3401e4811d524a9be0cc4688335e6ac`.
Branch `delivery/selective-loading`, candidate version `0.1.0-preview.9`.
This supersedes the initial `5abd567` candidate; its original evidence is retained
one directory above. Nothing is merged or deployed. Product-drafting preview.8
and PR1 are untouched.

Independent QA correctly identified avoidable cold-authoring growth in the first
candidate. The simplification removes the moved product-workflow copy and replaces
it with a short checklist in the selected skill. Workspace, initiative and blocking
rules move from conventions to the common contract; runtime and conventions point
to those authoritative rules instead of adding duplicate mandatory paragraphs.
The existing detailed product contract (owner choices, separate usefulness cards,
shape, evidence grading, history, retirement) remains unchanged and required for
authoring. Expanded writing/host guidance remains conditional on the action.

The single reuse rule now explicitly requires exact text visible AND either a
matching current content hash or verified immutable package-snapshot identity.
Unchanged HEAD/version/path/mtime in a mutable checkout does not prove unchanged
files. Compaction/lost text/change requires rereading; no cache framework added.

## Partial instruction-route accounting

Reproduce with:

```
python3 scripts/measure_delivery_loading.py --before a46dc827826c9d641f5e745101f4cc14fcf1a21b --after 74d9e6a9a3401e4811d524a9be0cc4688335e6ac
```

`loading.json` contains exact resource hashes, UTF-8 bytes and whitespace words.
These are **partial declared instruction routes**, not full prompts. Project
artifacts, templates, tool I/O, output, catalogue metadata and lenses are excluded
from the first three routes. Cold authoring conservatively counts full runtime/
conventions files even though guidance is conditional. Real loading may differ.

| Partial route | Before bytes / words | Candidate bytes / words |
|---|---:|---:|
| Focused map question | 30,146 / 4,234 | 11,072 / 1,438 |
| Cold product authoring | 30,146 / 4,234 | 30,031 / 4,106 |
| Three phases: old repeated reads versus eligible shared-text reuse | 96,634 / 13,713 | 46,675 / 6,535 |
| Same three phases: unique-source floor | 46,790 / 6,663 | 46,675 / 6,535 |
| Same three phases: rereads after context loss | 96,634 / 13,713 | 99,461 / 13,821 |
| Four edited lens bodies plus candidate common context/core | 25,378 / 4,133 | 28,799 / 4,246 |

Cold authoring no longer grows relative to baseline; its 115-byte difference is
not a meaningful performance claim. Focused inputs are smaller, but context-loss
and the four-lens bundle still grow. Reuse requires the stated visibility/content
conditions and is not guaranteed by the host. No tokenizer, actual model token/
time receipt, output-quality evaluation or quality-preserving improvement is
established here. **The user's model-evaluation quality gate remains pending;
cutting bytes while losing quality would not be a win.**

## Completed checks and their limits

- Full Python suite: **145 passed**, including five loading contracts, eighteen
  product tests and seven package tests; marketplace validation passes.
- Node judge suites: **22 passed**. No judge provider or model called.
- Isolated Codex CLI 0.163.0 installation: all **16 skills**, installed references
  byte-identical to source, illustrative greenfield record/handoff pass; zero model
  calls. The removed workflow file is no longer required by probe or skill.
- At exact source SHA, **11 public commands** pass on the actual Delivery repo
  (seven curated preview capabilities, shared project.py impact) and an equally
  first-class illustrative no-Git concept (planned code absent, proposed design/
  story setup). Outputs/exits and prepared artifacts are under `journeys/`.
  This is command/artifact evidence, not model-driven skill execution or adoption.
- Independent source review caught two lost obligations while extracting rules:
  explicit project-instruction/AGENTS reads and the no-repository planning-store
  fallback. Both were restored with regression guards. The reviewer rechecked
  them, found no further substantive source blocker, and independently passed all
  145 Python tests and catalogue validation. A trailing blank line found by the
  formatting check was removed; final `git diff --check` passes.

Actual owner priority is preserved; inferred customer/cuts stay proposed, author
runs stay Claimed and Return remains Unknown. No real user, authenticated dot,
model/desktop/ChatGPT or deployment claim is made. Parent's separate baseline/
candidate eval will determine quality/resource impact; no model-host configuration,
credentials, permissions, services or multi-agent infrastructure were changed.

Publication remains blocked by the earlier automatic approval-review rejection
for opening this branch's PR without exact publication authorization. No retry,
formal PR approval or merge is part of this simplification.
