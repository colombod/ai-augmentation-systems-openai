# Session event log requirements

Source: user requests on2026-10-21. The initial “logs event types only” boundary was explicitly extended by the later request for subagent identifiers and useful log-file links. Status: implementation scope, not human acceptance.

| ID | Observable requirement |
|---|---|
| FR-1 | Register all currently documented Codex lifecycle events: SessionStart, SessionEnd, UserPromptSubmit, PreToolUse, PostToolUse, PermissionRequest, SubagentStart, SubagentStop, PreCompact, PostCompact, Stop, Interrupt. |
| FR-2 | Every successful invocation appends one JSON line with `event_type`; ordinary events contain only that field. Subagent lifecycle metadata is limited by FR-13–16. All content and unknown fields are discarded, including in diagnostics. |
| FR-3 | Route sessions to `PLUGIN_DATA/event-types/<sha256(session_id)>.jsonl`, without raw identifiers in filenames or records. Reject absent session identifiers. |
| FR-4 | Use a TypeScript transport adapter and a Rust library implementing all parsing, validation, routing and file writes. Ship a runnable compiled adapter and a native executable for the build host. |
| FR-5 | Success emits no stdout and exits 0. Failure emits a fixed content-free diagnostic on stderr and exits 1, never a blocking exit 2 or an approval decision. |
| FR-6 | Document dependencies, build, installation, trust, live viewing, data location, removal and known host coverage limitations. |
| FR-7 | A real local Codex desktop event reaches the installed and explicitly trusted plugin and produces its log. CLI/protocol checks cannot satisfy this criterion. |
| FR-8–12 | Read-only latest-log discovery, root precedence, safe failure and source/installed-version distinction, specified in `../../stories/hook-event-log-02-latest-log.md`. |
| FR-13–17 | Allowlisted subagent IDs/types and host-provided Stop transcript path, field bounds, no content reads, backwards-compatible records and preview3 docs, specified in `../../stories/hook-event-log-03-subagent-links.md`. |

| ID | Engineering acceptance bound, selected by implementer |
|---|---|
| NFR-1 | Bound a hook input to 1 MiB; oversized and malformed inputs produce no log entry. Bound the adapter's full runtime to less than the hook's 3-second configured timeout. |
| NFR-2 | 32 simultaneous successful invocations yield 32 complete records; reject symlink log targets and avoid interleaved writes. Log files use owner-only permissions on supported Unix systems. |
| NFR-3 | macOS is the required first build/desktop target. Other operating systems need their own build and acceptance; never imply a universal binary. |
| NFR-4 | No network, model calls, credential reads, transcript reads or configuration/trust changes in the hook. Logs grow until removed manually; no silent deletion. |
