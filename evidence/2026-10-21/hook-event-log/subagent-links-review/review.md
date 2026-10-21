# Independent preview.3 subagent metadata review

Date: 2026-10-21. Reviewed the Delivery story03/sprint3, implementation, new packaged tests, README and changelog. This change explicitly extends the original event-types-only scope for the user's requested subagent identifiers and useful host-provided transcript path. Ordinary events retain the previous privacy boundary. No implementation, configuration, trust or installed-cache mutation was made by this reviewer.

**Verdict:** no runtime blocker found at the tested local package boundary. FR-13–FR-17 are met for source preview.3. Installed preview.1 does not acquire these features until refreshed through the supported installation flow; no preview.3 desktop-metadata acceptance is claimed.

## Verification

- `npm test`: **20/20** tests passed. This includes actual TypeScript-to-Rust process invocation, previous hook concurrency/path/privacy/timeout checks, all latest-log helper checks and new metadata cases.
- `PATH=/Users/colombod/.cargo/bin:$PATH cargo test --locked --offline --manifest-path plugins/hook-event-log/core/Cargo.toml`: **16/16** integration tests passed; zero unit/doc tests defined.
- Independent actual packaged-command probes: **27/27** passed; raw results in `observations.json`. Cases include exact allowed byte boundaries and one byte over for each field; multibyte UTF-8 byte limits; null, Boolean, number, array, object, empty, whitespace and control-bearing metadata; valid escaped strings; ordinary-event omission; start/stop field scoping; preserved historical bytes; unknown-field/prompt/tool/message sentinel exclusion; no child log-file invention; 32 concurrent maximum-sized records; unchanged latest-log behavior; source manifest and npm lock versions.
- A supplied FIFO transcript path was preserved as metadata and the command returned in approximately 35 ms without blocking to read it. Static review additionally confirms there is no transcript stat/open/read operation: the core only tests whether the supplied string represents an absolute path.
- `git diff --check` passed.

## Implementation assessment

Rust constructs a fresh output map and inserts only the event type, then event-scoped optional metadata. It never copies an arbitrary input object. `agent_id` and `agent_type` are allowed only on SubagentStart and SubagentStop. `agent_transcript_path` is allowed only on SubagentStop and must be absolute. Optional fields are string-only, nonempty, control-free and bounded in decoded UTF-8 bytes; malformed fields are omitted without dropping the event. JSON serialization provides escaping. The routing key remains the hashed host session identifier; an agent identifier is never treated as a child session identifier.

The existing pinned-directory/no-follow/private-file/locking write path remains in use. Large optional metadata is still inside the one-MiB input and bounded adapter lifetime. Normal event schema remains a single key. The existing latest-log utility enumerates metadata rather than reading records and therefore supports mixed historical/new lines without migration.

## Criteria

| Criterion | Verdict | Boundary/evidence |
|---|---|---|
| FR-13 scoped subagent ID and type | Met for source | Actual lifecycle examples; ordinary events omit those fields. |
| FR-14 absolute stop-only host transcript path; no transcript reads or inferred child log | Met for source | Stop/start contrast, FIFO probe, source inspection and single hashed-parent output file. |
| FR-15 bounded optional metadata, invalid omission, escaping | Met for source | Exact and over-limit ASCII/UTF-8 cases, invalid types/control bytes, JSON escaping; events preserved. |
| FR-16 excluded content and preserved history | Met for source | Synthetic excluded-field sentinels absent, historical prefix unchanged, mixed records and concurrent completeness. |
| FR-17 preview.3 docs/helper/update distinction | Met for source | Manifest/package/lock versions agree; latest-log tests pass; README explains native transcript versus plugin event log and installed preview.1 distinction. |

One package-description inconsistency was reported to the parent and **fixed, then independently rechecked**: hooks/hooks.json now describes lifecycle event types and allowlisted subagent identifiers/transcript paths. The README/root catalogue/changelog also accurately state the new boundary. The README links the bundled native dependency notices, and that packaged file exists. These documentation-only corrections require no runtime retest; no unresolved finding remains from this review.

Actual desktop callback evidence from installed preview.1 remains valid for its old one-key schema, not proof that installed preview.3 emits IDs or paths. All twelve host event kinds, exact desktop trust UI and fresh-chat installation procedure retain their previously stated validation limits. Source tests do not close those gaps or authorize a trust bypass.
