# Real CLI delivery cycle — 20 October 2026

**The attended test passed through the operator acceptance barrier.** Five real persistent `gpt-6.1-sol` roles used the public `prepare`, `send`, `status` and `serve` commands, real Beads and an independently prepared Git clone. They produced a working ASCII slugify CLI, committed it, independently tested/reviewed it and submitted the declared terminal-surface evidence. Protected acceptance was refused because no real operator terminal receipt was supplied. The canonical Beads task remains **in progress**, not accepted.

This is staged integration with recorded operator corrections, not one-prompt autonomy, hosted CI, desktop UI or ChatGPT acceptance. No marketplace commit, push, merge or deployment occurred; only disposable fixture commits were created.

## Actual outcome

| Check | Observed result |
|---|---|
| Public CLI preparation | Full coordinator, product-manager, delivery-manager, builder and independent reviewer roster; no manual role/task database seeding |
| Persistent peer handoff | Coordinator actually called `delivery_send` to assign PM drafting |
| Canonical drafting | Plan, brief and story saved through the controlled artifact tool; actual bytes match actor-bound save hashes |
| Restart | Public supervisor stopped/restarted; exact PM queued follow-up completed on the same native thread |
| Canonical task | Real DM story materialization and readiness created `fullcycle-6m8` |
| Actual implementation | Builder claimed, implemented, ran **7 tests**, committed `32746b7d72bbbb4263c2ecf8a737c1c1613f9bbe` and submitted matching evidence |
| Independent native review | Separate read-only reviewer ran the **7 tests and 9 CLI cases**, saved protected review evidence and submitted review/surface results at the same SHA |
| Separate root holdout | **21/21** black-box cases passed; source unchanged; this is separate implementation-session grading, not the bound reviewer or human acceptance |
| Selected OpenAI advisory | Native coordinator called the configured `gpt-6-luna` judge; actual advisory answer returned, explicitly without human authority or blocking eligibility |
| Protected acceptance | Actual DM gate status reports submissions complete and accepted false; actual accept call refused without operator-terminal capture; task remains in progress |

The fixture remains at `/private/var/folders/2r/5gvkx5wx0g37m4grvjjdt88m0000gn/T/delivery-full-cli-3b8pu1g_`. Durable copies of committed product files and canonical artifacts are in `product-snapshot/` and `canonical-artifact-snapshot/`. The [structured summary](summary.json) checks actual Git/files/Beads/native event evidence and has all 15 checks passing.

## Observed failures and interventions

1. The initial optional judge request supplied the wrong state fields and was skipped as `state_incomplete`. A new explicitly assigned coordinator turn used the catalogue's correct fields and returned a real OpenAI advisory. Both native results remain recorded.
2. The builder used a pathspec/partial commit form, which needs an unsupported temporary index lock. The command failed in the native sandbox and the model requested an outside-sandbox retry. That request was **revoked, never approved**. A public exact-turn steer instructed the supported staged-index commit form and legitimate generated cache cleanup. The same builder turn then committed normally. Raw native failure evidence is retained under `independent-audit/`; `operator-builder-correction-commands.json` records the denied request and public correction. This intervention prevents any claim of unassisted execution. Production guidance was corrected only after all actual-run supervisors stopped, with hashes recorded separately by root.
3. The initial harness waiter could mistake an existing idle role for completion of newly queued work. It failed at the final DM stage before that queued message executed. The original `result.json`, logs and exact executed `runner-initial.py` are retained. `continuation.py` restarted the **public CLI** on the same fixture and consumed the already queued message, without resending it or changing database state. The exact message → native user-message/turn → terminal chain is independently recorded in `continuation/queue-proof.json`. The continuation's actual gate/refusal/task checks pass.

No failure was hidden by widening native permissions, changing hooks/trust, executing Git writes in a privileged parent process, fabricating a human receipt or marking the Beads task closed.

## Benchmark context

Total observed wall time including fixture setup, the attended correction and continuation was **580.8 seconds**. Native cumulative counters reported **1,477,357 input tokens**, including **1,263,872 cached input tokens**, and **10,482 output tokens** across the five roles. No counter resets were observed. Per-role counters and native completed-turn durations are in `summary.json`; complete usage events are in `native-token-usage-events.json`.

These counts cover the full host context and repeated model/tool turns. They do not isolate plugin overhead, establish a no-plugin comparison, imply a monetary price or demonstrate statistical reliability. Local test evidence is not hosted CI. Worker-submitted surface observations remain unauthenticated; no human attestation was invented.

## Execution and evidence boundaries

- `runner-initial.py` and `continuation.py` were the actual executed drivers. Public CLI command receipts, supervisor logs and completed native item/command journals are retained. `execution-provenance.json` names the interventions and boundaries.
- `runner.py` is the corrected **future** driver, not a retroactive account of this run. It binds waits to exact queue/user-message/native terminal proof, creates a unique attempt directory and returns a failing exit code on recorded failure. It was syntax-checked and its waiter was checked against actual completed evidence plus a synthetic premature-idle case; the whole corrected driver was not rerun. `future-waiter-check.json` records that limited validation.
- `actual-run-production-source-hashes.json` pins the production source before the later instruction-only guidance correction. Root's `root-acceptance/post-guidance-package-hashes.json` identifies the later package separately.
- `continuation/events.json`, `controlled-tool-results.json`, `canonical-task.json`, `pm-restart-actual-queue-proof.json` and `continuation/queue-proof.json` provide actual-state checks. Root's holdout and peer audits are separately labelled under `root-acceptance/` and `independent-audit/`.

For a future full run, invoke `python3 evidence/2026-10-20/full-cli-cycle/runner.py`; it prints its new evidence directory under `attempts/`. Do not redirect output over the retained initial logs. This evidence is maintainer-only and must not be included in the installable plugin archive.
