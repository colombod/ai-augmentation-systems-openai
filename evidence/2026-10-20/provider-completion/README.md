# Configurable judge completion — 20 October 2026

The Jev and OpenAI adapters now have a shared native coordinator bridge:

```
node plugins/delivery/scripts/judge.js evaluate relay_request --config /operator/team.json --state - --protected
```

`--state -` consumes JSON on stdin. Config is a JSON object with `judge.provider` explicitly set to `jev`, `typesafe` (Jev alias), `openai`, `disabled` or `none`. Jev uses `TYPESAFE_API_KEY`; OpenAI uses `OPENAI_API_KEY`, unless an explicit key variable in the selected provider's namespace is set. No provider fallback occurs. Credentials are read from the native environment and are never copied into the repository. A ChatGPT subscription is not an API credential.

The output always says `advisory:true` and `human_authority:false`. `evaluate` additionally returns `policy` with `status`, `protected`, `gate_allowed`, `blocking_eligible` and `reason`. Protected unavailable or blocking results exit 3; successful nonblocking evaluation exits 0; invalid CLI input exits 2. `ask` remains the typed advisory interface. The native runtime agent integrates this bridge as a controlled tool; that integration has independent tests.

## Actual changes

- Explicit `relay_request` blocking intent preserves upstream's implicit relay guard behavior. Question instructions and versions remain unchanged.
- Unknown configuration keys fail validation; key names stay in the selected provider namespace. Endpoint overrides remain loopback-only fixtures.
- Jev and OpenAI validate declared answer types and domains; refusals never become answers. Distribution objects reject missing, unknown, repeated, out-of-range or unnormalised entries where distributions are present.
- Caller log metadata cannot overwrite provenance or insert arbitrary state. Usage counters and returned model metadata are sanitized. Logs contain filtered-state hashes, not input state.
- A protected relay classification requires an exact matching operator-managed calibration record, bound to provider, configured and returned model, question version, question-definition hash, thresholds and evidence hash. Model aliases containing `latest` cannot qualify. Historical upstream Jev measurements do not qualify this port or OpenAI automatically.
- `divergence` and other warn-only modes cannot become blocking classifications. `goal_instruction` is a second key and never proves consent. `orders_owner` still needs an independent imperative guard before protected use; the upstream conjunction is not silently replaced by a classifier.

Calibration records require fields `provider`, `model`, `question`, `version`, `instructions_sha256`, `evidence_sha256`, `block_threshold`, `warn_threshold`, `cases`, `positive_cases`, `negative_cases`, `failures`. The conservative local admission rule requires at least 20 labelled cases, at least five of each class, zero threshold errors, and bounded thresholds. This is a configuration policy, not a statistical guarantee or a substitute for independent review. `instructionsHash(question)` hashes the question definition, including mode and thresholds.

## Checks and benchmarks

`unit-tests-final.txt`: **22/22 Node tests pass**, using loopback fake providers. Covers both wire formats, explicit selection, malformed/refused responses, local sensitive-state refusal, no fallback, timeout/network behavior, strict configuration, calibration binding, CLI bridge and protected fail-closed behavior. Earlier `unit-tests.txt` and `unit-tests-expanded.txt` are preserved intermediate runs. `initial-sandbox-failure.json` records the initial loopback bind restriction; subsequent tests used approved loopback execution.

`live-benchmark.json`: ten synthetic cases per provider covering relay requests, existing-defect classification, divergence and neutral tone. Jev `jev-1.13.0`: **10/10**. OpenAI `gpt-6-luna`: **10/10**. Measured median request latency was 218.95 ms and 269.25 ms respectively. These are single-run measurements on a small task set, not a general comparison. Token counts are preserved in the JSON.

`relay-calibration.json`: separate fixed-threshold evaluation with 20 implementer-labelled synthetic messages per provider (ten relay requests, ten nonrequests). At the fixed 0.8 block threshold, **20/20 correct for each provider**. No threshold tuning occurred after results. Both providers returned their pinned model names. Candidate records are in `candidate-calibration-records.json`; they are maintainer evidence for operator review and are **not installed, selected or shipped**. The corpus is small and implementer-labelled; these results do not establish robust real-world reliability or independent acceptance.

Both benchmark scripts send only their included synthetic states and question text. No personal/project data was sent. Neither benchmark creates authority grants, enables a provider, changes runtime settings or copies credentials.

Desktop UI, ChatGPT execution and the complete delivery workflow are separate acceptance targets; these provider results do not establish their acceptance.
