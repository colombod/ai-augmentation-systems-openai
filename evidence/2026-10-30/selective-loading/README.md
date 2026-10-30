# Selective loading and greenfield reviewer correction

Base/main: `a46dc827826c9d641f5e745101f4cc14fcf1a21b` (merged PR2, preview.7).
Exact reviewed source: `0ab84d132c5c5d4a1b2555aab08003a66fefa1a1`, candidate
`0.1.0-preview.9`, branch `delivery/selective-loading`. The separate pending
`delivery/product-drafting` preview.8 branch is not included or modified; reconcile
version/changelog order if both are later accepted. No further merge or deployment
is part of this increment.

## User-visible change

An existing-map question can use `$delivery:product` and one `status` or
`impact --path` invocation. It reads the selected full skill and a short mandatory
core, rather than loading authoring budgets, full product input and glossary
curation. Workspace selection, canonical state, blocking findings, owner choices,
shared code, evidence boundaries and host authority still apply. Absent maps and
unavailable tools are explicit; no map is fabricated. Authoring, handoff and
retirement continue into the full workflow/product contract and applicable
runtime/writing guidance.

The solution-architect and delivery-lead lenses no longer require a repository,
existing source paths or a working test runner for no-code greenfield design and
stories. New paths/commands are proposed, setup remains explicit and unverified,
and planning readiness never establishes passed tests or execution authority.
Only their directly related QA/critic lenses share the new common language and
source-integrity reference. Original source pins and MIT notices remain intact.

Exact shared text can be reused only while visible with an established unchanged
source revision/hash. Compaction, missing text, changed or unverifiable sources
require rereads. This is an instruction contract, not a host cache, automatic
loader, persistent memory system or assumption that all skill bodies are visible.

## Actual measurements, with costs retained

Reproduce using:

```
python3 scripts/measure_delivery_loading.py --before a46dc827826c9d641f5e745101f4cc14fcf1a21b --after 0ab84d132c5c5d4a1b2555aab08003a66fefa1a1
```

`loading.json` records UTF-8 bytes, whitespace words and SHA-256 per resource.
These are declared source-loading footprints, not observed model prompts/tokens,
latency, cost, adherence or product quality. No tokenizer or model run is used.
Project inputs, tool I/O, output, templates, catalogue metadata and reviewer lenses
are excluded from the first three route comparisons. Authoring includes whole
references as a conservative bound despite the instructions permitting relevant
sections. Actual host/model selection could differ in either direction.

| Declared route | Before bytes / words | After bytes / words |
|---|---:|---:|
| Focused product query | 30,146 / 4,234 | 7,508 / 1,015 |
| Cold product authoring | 30,146 / 4,234 | 38,240 / 5,328 |
| Product → architecture → stories, prescribed repeated shared reads vs eligible reuse | 96,634 / 13,713 | 54,884 / 7,757 |
| Same three phases, unique-source floor | 46,790 / 6,663 | 54,884 / 7,757 |
| Same three phases if context loss requires rereads | 96,634 / 13,713 | 114,552 / 16,151 |
| Four edited lens bodies, including new shared context/core after | 25,378 / 4,133 | 25,765 / 3,893 |

The focused path is materially smaller. Cold authoring and context-loss rereads
are larger because the new core and routing are additional inputs. The three-phase
reduction depends on eligible reuse; it is not a reduction against the old unique
source floor. Lens consolidation reduces repeated language but is not a measured
byte reduction when the new core/context are included. No token-saving or quality-
equivalence claim follows from this source accounting.

## Verification actually completed

- `python3 -m unittest discover -s tests/delivery -v`: **145 passed**, including five
  new static loading/resource/greenfield contracts. These catch source regressions;
  they do not prove a model follows the skill.
- `node --test tests/delivery/judge.test.js tests/delivery/openai-judge.test.js`:
  **22 passed**. Marketplace validates two existing catalogue packages.
- Isolated Codex CLI **0.163.0** installation/discovery: all **16 skills**, installed
  new references byte-identical to source, installed greenfield record/handoff
  passed, **zero model calls**. See `installed-discovery.json`.
- `scripts/product_workflow_acceptance.py`: **11 public command invocations** at
  the exact source SHA. The actual Delivery repository supplied seven curated
  preview features and a real shared-file impact answer. The equal no-Git idea
  remained explicitly illustrative, planned and code-free, with proposed design/
  story setup. Author-prepared artifacts are not a model-driven phase evaluation.
  Owner priority is retained; customer/cuts remain proposed; Return remains Unknown.
  Raw outputs/exits, records and limitations are retained under `journeys/`.
- Separate read-only reviewer examined source and addendum, found no remaining
  blocker/lost obligation, independently ran focused/full Python checks and
  reproduced footprints. This is source/correctness review, not user adoption.
- `git diff --check` passed.

A first measurement CLI invocation used an abbreviated after-SHA and was refused
with `ValueError: Use an immutable full 40-character Git SHA`; the full immutable
SHA invocation above then passed. No failed source/host observation is promoted
to success.

Native model-driven evaluation remains unavailable: the prior local native-session
probes failed before a model turn due to read-only host state / app-server startup,
retained in the earlier product-workflow fresh-host evidence. No credentials,
model/sandbox configuration, hooks or permissions were changed. This increment
has no fresh native-model, desktop, ChatGPT, authenticated-dot or outside-user proof.
The next meaningful performance/quality proof is the same focused query and no-code
journey in a working authorized model host, with actual loaded inputs/usage and
criterion-level output review. No new service or software install is needed here.
