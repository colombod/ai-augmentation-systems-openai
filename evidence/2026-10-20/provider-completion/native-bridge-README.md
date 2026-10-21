# Actual native coordinator judge bridge — 20 October 2026

Two real `gpt-6.1-sol` read-only coordinator turns each invoked the native controlled `delivery_judge` tool exactly once, with the same bounded synthetic `is_fix` state.

Both completed successfully. Jev returned pinned model `jev-1.13.0`; OpenAI returned pinned model `gpt-6-luna`. Both returned a typed `yes`, `advisory:true`, `human_authority:false`, and the explicitly selected provider without fallback. Checks confirmed unchanged operator configuration, exact protected configuration snapshot, native read-only lane verification and completed native turn.

The fixture transparently seeds one role and pinned operator settings into a temporary planning database. It does not claim full roster preparation, task lifecycle, protected blocking calibration, desktop UI or ChatGPT acceptance. Production `Coordinator`, native Codex app-server configuration isolation, native thread creation, effective lane verification, dynamic tool dispatch, configuration pinning and selected real provider invocation are exercised. No worker shell, browsing, delegation, personal configuration mutation or credential copying was requested.

- `native-bridge-probe.py`: reproducible bounded fixture.
- `native-bridge-results.json`: all native events, actual controlled-tool results and checks.
- `native-bridge-summary.json`: actual provider/model/answer/usage/latency summary.
- `native-bridge.stdout` / `.stderr`: preserved execution output.

Temporary planning files are removed after each run. Native permission settings apply per thread; these persistent native thread records may remain in the normal Codex session store. Existing native sign-in and environment provider keys were used through production code. No credentials appear in the evidence. The selected judge received only synthetic declared fields and public question instructions.
