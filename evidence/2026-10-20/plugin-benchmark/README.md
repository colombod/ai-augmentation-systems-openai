# Delivery preview review and benchmark — 20 October 2026

## Judgment and scope

The package is a credible server-free **planning preview**, not yet the full
Claude delivery system. Its portable manifest, resources and local helper pass
structural checks. All 15 skills install and are discovered on Codex CLI 0.159.3.
Persistent roles, configurable Jev/OpenAI Decisions adapters, enforced delivery
gates and automatic execution remain unimplemented. Desktop and ChatGPT product
acceptance remain pending; CLI protocol results cannot establish their behavior.

This evaluation uses the local, uncommitted `0.1.0-preview.4` package. It neither
publishes the plugin nor modifies the original Claude marketplace. This report,
fixtures and raw evidence remain outside the installable package.

## Deterministic checks

- Marketplace validation against the vendored Agent Plugins 1.0.0 schema: passed.
- All 13 package/helper tests: passed. These cover invalid portable manifests,
  provenance coverage, resource containment, package boundaries, helper CLI,
  ancestor reuse, preservation, read-only inventory, path conflicts, nested
  components, symlinks and prose counting.
- Fresh isolated installation and discovery: all 15 qualified `delivery:*`
  skills, installed helper execution, assessment exclusion and lineage presence
  passed; see [install-probe.json](install-probe.json).
- `git diff --check`: passed.

## Static Plugin Eval results

Used the installed Plugin Eval plugin (`0.1.2`, internal analyzer `0.1.0`). Its
plugin detector recognizes `.codex-plugin/plugin.json` only. Our portable root
`plugin.json` is misclassified as a generic directory. Consequently the root
72/C output in [static.json](static.json) is **not a valid overall plugin score**.
The starter benchmark command rejects that target. No compatibility overlay was
added to the package to satisfy the evaluator.

Direct analysis of all 15 skills succeeds. Static scores range from 67 to 91:

| Skill group | Static score | Interpretation |
|---|---:|---|
| start, status | 91/B | Strongest under this heuristic; shorter instructions |
| stories | 86/B | Clear trigger recognized, larger instruction budget |
| architecture, brief, challenge, design, personas, realign, research, roadmap, sprint-review | 81/C | Primarily instruction-budget and trigger phrasing warnings |
| prd, sprint | 77/C | Additional discovery-description budget warning |
| simulate | 67/D | Largest estimated instruction and discovery-description costs |

These are formatting and estimated-context heuristics, **not success rates or
quality grades**. For example, descriptions saying “Use to …” or “Use at …” are
flagged despite describing a trigger. Start/status are estimated at 578/518
instruction tokens; simulate at 3,024 plus 152 discovery-description tokens.
The per-skill scan reports no support files because shared references/templates
live outside each skill folder. Its estimate therefore omits that additional
context. Repository tests also live outside the package, so a generic “tests
missing” warning does not establish missing tests.

See [static-summary.json](static-summary.json) and [raw per-skill reports](static-skills/).
The practical follow-up is tracked as Beads `oap-5if.12`: reduce context where
useful while preserving safeguards, then compare behavior and actual usage.

The bundled live runner was not used: its `seedCodexHome` copies `auth.json` and
personal `config.toml`, contrary to this repository's credential/configuration
rule. The custom bounded harness below uses existing native sign-in in place.
No credentials or personal configuration are copied into this repository or
into an isolated home.

## Native benchmark method and failed attempts

The initial [CLI harness](run-native.py) supplied per-call marketplace source and
enabled-plugin configuration, but did not install a plugin into the active home.
The start run could not initially discover the skill. It searched broadly,
then located the adjacent temporary package and executed its helper successfully.
This is file-based fallback, **not clean registered-plugin activation**. It used
211,184 cumulative input tokens and 661 output tokens in 30.84 seconds, including
169,472 cached input tokens. Those high totals include repeated context and the
broad search. Do not attribute them to normal skill overhead. The dependent brief
run was interrupted. Both are retained in [native/](native/).

The selected-skill harness first installed the package in a clean temporary Codex
home without credentials, then exposed three installed skills through temporary
project `.agents/skills` aliases. The model-backed app-server uses the existing
native sign-in and host configuration, with ephemeral threads, workspace-write
sandbox and native approval policy. It receives structured `type: skill` input
whose path resolves to the installed package. No skill source is pasted inline.
Requests prohibit delegation, browsing, home searches or configuration changes.
Interactive escalation/input requests are refused, never auto-approved.

The first selected-skill harness stopped before inference because its path filter
expected the alias path; Codex correctly returned the canonical installed path.
That discovery-only attempt is preserved in [selected-skills/](selected-skills/).
The corrected run is [selected-skills-run2/](selected-skills-run2/), reproduced by
[run-selected-skills.py](run-selected-skills.py).

This tests native selection and real file behavior of installed skill resources.
Because the aliases are repository-scoped (`pluginId: null`), it does **not**
establish end-to-end qualified plugin selection in a normal installed user
session. The separate install probe establishes qualified plugin discovery.
The host configuration also exposes unrelated capabilities and warnings; these
runs are not a clean with/without-plugin comparison. The traces and metadata
retain those conditions rather than claiming isolation from them.

The measured model is `gpt-6.1-sol`, OpenAI provider, default service tier,
medium reasoning. Each case uses a fresh ephemeral thread against the same
synthetic project, so later cases consume earlier artifacts but not earlier
conversation history. No customer data is supplied. Token totals include host
instructions, tool definitions, repeated inputs and tool outputs. Cached tokens
are a subset of input, not an additional category. Latency includes host setup,
tool execution and hooks. One sample per case cannot establish reliability,
statistical superiority or incremental plugin cost. No dollar estimate is made.

## Measured selected-skill results

All three cases completed and passed the stated checks. The implementation
session reviewed the answers; this was not independent grading.

| Case | Result | Seconds | Cumulative input tokens | Cached input subset | Output tokens |
|---|---|---:|---:|---:|---:|
| start | Installed helper created the expected directories; no placeholder brief or source overwrite | 26.01 | 125,130 | 104,064 | 672 |
| brief | Saved a 547-prose-word brief and 119-prose-word glossary; synthetic inputs and owned unknowns retained | 121.36 | 228,158 | 196,864 | 4,407 |
| status | Reported draft framing and missing evidence; readiness unestablished; file hashes unchanged | 42.00 | 126,107 | 103,040 | 1,111 |

Total time for these measured cases: 189.37 seconds. Counts are cumulative over
the model's multiple tool steps, **not context-window size** and not the plugin's
incremental charge. The large repeated-input totals make context cost a useful
optimization target, but this experiment cannot assign those costs between the
host and plugin. The selected model, medium reasoning and host settings were
observed in thread metadata, not explicitly pinned by the harness.

The brief preserved the synthetic hypothesis, used the three specified review
lenses, stated that independent convergence was unavailable and coverage was not
exhausted, and kept baselines/targets unknown. It identified the difference
between satisfying recorded requirements and recording all client requirements.
The status answer noticed a terminology alias inconsistency while keeping
missing customer and implementation evidence explicit. The actual word counter
confirmed both reported prose counts. No input file was changed or deleted.

See [assessment.json](assessment.json), the
[generated brief](selected-skills-run2/artifacts/.delivery/initiatives/translator-handover/brief.md),
[glossary](selected-skills-run2/artifacts/.delivery/glossary.md), and retained
per-case native requests, raw protocol, answers and hashes.

## Release decision and next validation

Suitable for further local planning trials. Do not yet claim full delivery
parity, desktop/ChatGPT acceptance or production reliability. The remaining
acceptance work belongs to existing Beads `oap-5if.4`; full-runtime and provider
implementation remain separately tracked.

A useful next benchmark should test a normal registered-plugin session end to
end, revision/history preservation, prerequisite refusal, challenge findings,
research citations, story readiness and sprint handoff. Repeat representative
cases with predefined assertions and assess outputs independently. For efficiency
claims, use matched tasks with and without the plugin, pin the same model and
settings, repeat trials and compare completed artifact quality alongside time
and tokens. Desktop and ChatGPT need their own actual installation and workflow
tests; prompt-simulated capability tests do not substitute for those.

The preserved failed runs are harness/setup observations, not hidden passes or
proof of a defect in the delivery package. Fresh reproduction should choose a
new output directory: the scripts and files in this dated evidence directory
are the retained record of this run.
