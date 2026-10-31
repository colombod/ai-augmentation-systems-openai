# Session event logger design

Status: scoped implementation; Desktop acceptance pending. Design uses Delivery's solution-architect, QA and critic lenses, with single-session review before implementation.

## Components and contracts

New `plugins/hook-event-log/` is independent of `plugins/delivery/`. The root catalogue gains one entry; existing validation and schema remain authoritative. Planning and evidence stay outside the installable package.

| Path | Responsibility |
|---|---|
| `hooks/hooks.json` | Register twelve event names with a 3-second command timeout. |
| `src/hook.ts`, `dist/hook.js` | TypeScript adapter: bounded stdin collection; launch packaged native executable with raw bytes, no shell, bounded runtime; quiet success/fixed failure. |
| `core/src/lib.rs` | Parse a JSON object; require a supported event name and nonempty bounded session identifier; discard other fields; hash identifier; securely append one-key JSONL. |
| `core/src/main.rs` | Bounded stdin and environment adapter for Rust core; fixed error messages, never echo input. |
| `scripts/build.mjs` | Build TypeScript and Rust, copy native binary into platform-specific `bin/<platform>-<arch>/`; no runtime compilation. |
| `README.md` | Operator build/install/trust/log viewing instructions and limitations. |

Input is the host JSON event on stdin. Output location comes only from host `PLUGIN_DATA`; absent or relative data roots fail. Ordinary entries are exactly `{"event_type":"PreToolUse"}` plus newline. The later user-authorized subagent metadata extension also reads bounded agent_id/type on lifecycle entries and an absolute agent_transcript_path onStop. It never opens the transcript or infers a child event filename. No timestamp or content opt-in. Session hashing is routing, not anonymization of predictable identifiers. The adapter never interprets payload fields and never invokes a model SDK.

## Decisions and alternatives

TypeScript matches the documented Codex SDK language. The SDK starts threads and is unnecessary for event logging; adding it would introduce session behavior and dependencies without value. A Rust library with a small executable bridge avoids Node native-addon ABI packaging; a direct N-API binding remains an alternative only if measured startup cost demands it. Python was a separate earlier question, superseded by the SDK-language requirement.

One JSONL file per hashed session separates concurrent chats without logging identifiers. A single shared stream would need session metadata in each record, violating the event-types-only scope. File locking prevents partial/interleaved records but cannot reconstruct host causality. Preserve every observed callback, including repeated types; do not deduplicate genuine repeated events.

Use synchronous hooks for prompt visibility in the log. Bound the adapter below the 3-second timeout, and bound lock acquisition in Rust. Failure is advisory and observable through a fixed diagnostic, never a decision. Log files are owner-only, symlink targets refused, and writes are pinned to an opened directory where feasible. This is a local diagnostic tool, not tamper-proof auditing.

## Non-functional coverage and test strategy

NFR-1: test byte boundary, malformed input, idle stdin and child timeouts. NFR-2: spawn real processes concurrently and inspect record count, schema and filesystem modes; test hostile symlinks. NFR-3: build actual macOS artifact and record architecture; no untested cross-platform claims. NFR-4: static review plus payload sentinels and isolated filesystem snapshot; no automatic deletion or network dependencies at runtime.

Unit tests cover Rust parsing and routing; integration tests run the packaged TypeScript-to-Rust path. Catalogue schema validation checks distribution. Native CLI discovery/execution and desktop acceptance are separate evidence levels. GUI acceptance requires inspecting a real desktop state and log.

## Spikes and assumptions

| Spike | Decision / owner | Rule and timebox |
|---|---|---|
| Native build | Implementer: executable bridge | Build within this implementation; if unavailable, report toolchain blocker, do not substitute JS logging. |
| Trusted plugin execution | Implementer: deployment | Use supported install/trust; if host skips plugin hooks, retain failure and keep FR-7 open. Never bypass trust. |
| Desktop local hook callback | User's target surface | Inspect actual desktop session and new event log this session if available; otherwise explicitly unverified. |

No migration is needed for this new plugin. Rollback disables/removes it; log deletion is a separate explicit action. Keep old records during upgrades. Known risks are host event omissions, hook timeout/disk-full loss, build-host-specific binaries and manual retention. Do not infer session completion from Stop: only SessionEnd is session termination.

## Implementation alignment

Actual source uses `.codex-plugin/plugin.json` only. The portable root manifest and a dual-manifest variant installed but returned no hooks on CLI0.159.3; legacy-only discovers twelve. Direct installed-adapter execution passes; native trusted callback delivery remains unverified. macOSarm64 builds and command-boundary tests pass. Windows writes are explicitly unimplemented. See the sprint review and retained installation receipts outside the package.

Later observation: after the user reported installing preview1, the actual desktop session log recorded tool and subagent lifecycle events, including a paired SubagentStart/SubagentStop. The exact installation/trust UI was not inspected. Sourcepreview3 adds the independently reviewed latest-log utility and explicitly authorized lifecycle metadata. Installedpreview1 does not gain the new fields until refreshed. Historical validation receipts remain unchanged.
