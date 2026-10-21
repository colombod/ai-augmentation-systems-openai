# Glossary

Proposed terms for this initiative, grounded in the user's request:

| Term | Meaning | Concrete example |
|---|---|---|
| Event type | The name of a Codex lifecycle event; the only value in ordinary records. User-requested subagent metadata is recorded separately on lifecycle entries. | `PreToolUse` |
| Session log | A local file containing event types observed for one Codex session. | `event-types/<SHA-256 of session_id>.jsonl` |
| Hook | A trusted command Codex invokes for a supported lifecycle event. | `hooks/hooks.json` |
| Rust core | The library implementing validation, session routing and disk append. | `plugins/hook-event-log/core/src/lib.rs` |
| Subagent identifier | The host-provided identifier used to match a child's lifecycle entries; not assumed to be an event-log session identifier. | `agent_id` |
| Native transcript path | A host-provided location for Codex's own child transcript, recorded without reading it. | `agent_transcript_path` on SubagentStop |
| Latest session log | The most recently modified regular hashed JSONL file, which can belong to another active chat. | Output of `node dist/latest-log.js` |
