# Changelog

## 0.1.0-preview.4

- Package a complete twelve-event catalogue, common/per-event field reference and examples.
- Include JSON Schema references for permissive documented host inputs and reduced saved records, linked from the README.
- Document prompt/agent/tool content availability, correlation limits and hook replies for future Amplifier integration, without enabling content capture.
- Documentation and schema assets only; hook execution and saved record behavior are unchanged.

## 0.1.0-preview.3

- Include host-provided subagent IDs and types on SubagentStart and SubagentStop records.
- Include the host-provided native transcript path on SubagentStop when available, without reading it.
- Preserve event-type-only records for other events, and exclude all prompt/tool/message content.
- Retain the read-only latest-log helper introduced in preview.2.

## 0.1.0-preview.2

- Add a read-only `latest-log` command, with path resolution and file selection in Rust.
- Document the default local data directory and observed desktop subagent lifecycle events.
- Keep hook records and command definitions unchanged; installed previews require a supported refresh to pick up the update.

## 0.1.0-preview.1

- Add TypeScript command-hook transport with a Rust event-type-only logger.
- Register twelve documented Codex lifecycle event types.
- Separate sessions by hashed identifier, with bounded input, execution and locked writes.
- Initial local preview; desktop UI acceptance remains unverified.
