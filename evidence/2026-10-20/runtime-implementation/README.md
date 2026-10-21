# Runtime implementation evidence — 20 October 2026

The previously missing implementation is now underway under Beads `oap-5if.8`
and `oap-5if.2`. Neither issue is closed by these observations.

## Implemented and checked

- Self-contained local `scripts/runtime.py` and `codex_rpc.py`: SQLite role/thread
  bindings and queued work, single-coordinator lock, native durable sessions,
  lane-response validation, native event tracking, expiry-bound operator request
  forwarding, peer routing bound to native sender/thread/turn, and read-only
  canonical Beads access. Peer text is never labelled human instruction.
- Crash/timeout uncertainty stops automatic replay. Resume uses the recorded
  native thread. Idle/active/stale/needs-reconciliation states are distinct.
- Adapted MIT upstream Jev adapter and question catalogue, plus an OpenAI
  Decisions adapter and explicit judge CLI. Source hashes are in upstream.json.
  Keys are environment references, not configuration values. Only declared
  filtered state is sent; no silent provider switching; no human authority.
- Python runtime/package tests and Node provider tests exercise denial, replay,
  filtering, invalid response domains, refusal, timeout and HTTP failure paths.
  The dated test output files retain the observed totals. CI now runs both suites.

## Actual native persistence

`native-session-probe.py` used existing Codex sign-in without copying credentials
or personal configuration. A real read-only `gpt-6.1-sol` thread completed a
synthetic fixed-response turn. The coordinator process was closed and recreated.
It resumed the same thread ID and completed a second synthetic turn.
All four explicit checks passed; see `native-session-probe.json`. No tools or
productive delegated work were requested. This is persistent-session evidence,
not a whole delivery team's acceptance.

## Actual provider smoke calls

`live-judge-smoke.js` made exactly one small synthetic `is_fix` classification
with each selected provider. Jev returned model `jev-1.13.0`, answer yes, p=0.95;
OpenAI returned `gpt-6-luna`, answer yes, p=1. No fallback occurred. Approximate
adapter latency was 248ms and 1,251ms, respectively. Token usage was Jev 335/21
input/output and OpenAI 207/0. These different single calls are not a performance
benchmark or calibration study. The question mode stayed advisory and neither
result granted human authority. No project files or personal data were sent.
See `live-judge-smoke.json`; credentials never appear in that evidence.

## Preserved failures and limits

- The first sandboxed Node test invocation could not bind loopback (`EPERM`).
  A normal approved test run with local fake providers then passed 14/15 tests;
  its single failure was an imported assertion expecting the old result envelope.
  The expectation was updated for the new explicit provider/mode/no-authority
  fields, and the rerun passed 15/15. The earlier failure log is retained.
- The first native builder-lane probe did not exercise either write: the shell
  could not create a here-document temporary file with temporary writable roots
  excluded. The protected file stayed unchanged, but the allowed worktree write
  was also absent, so that run is not an isolation pass. The exact-command rerun
  removes the here-document requirement without changing permission settings.
- Native model calls use the existing host configuration. Its unrelated MCP
  startup warnings are retained on stderr. A declared native sandbox alone does
  not establish that every connected tool obeys the same write boundary.

Controlled Beads workflow transitions, criteria/head/evidence invalidation,
verified human-decision capture, protected acceptance/merge/deploy, recovery of
uncertain external effects, complete team operation and separate desktop/ChatGPT
acceptance remain required work. No pending implementation is relabelled as
accepted. No hook trust or sandbox bypass was added. No deployment, commit,
push, account upload or change to the original Claude repository occurred.

The exact-command native builder rerun passed all three explicit checks: planning
file preserved, product-worktree file written, and turn completed. Actual output
was `OUTSIDE_DENIED` then `INSIDE_WRITTEN`. The effective sandbox retained both
temporary-root exclusions and no extra writable roots. This establishes the
specific native shell write boundary tested; it does not establish cross-tool
global enforcement. See `native-lane-probe-exact-command.json`.
