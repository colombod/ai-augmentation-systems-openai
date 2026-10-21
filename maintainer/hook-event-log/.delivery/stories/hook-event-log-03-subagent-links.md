---
status: ready
surface: S1
task: oap-15v.3
---

# Follow a subagent

User request2026-10-21 explicitly extends the earlier event-types-only rule: subagent events should show the identifier and useful information for following the child and finding its log.

| ID | Acceptance |
|---|---|
| FR-13 | SubagentStart and SubagentStop retain event_type and add host-provided agent_id and agent_type when valid. Other records remain event_type-only even if those input fields appear. |
| FR-14 | SubagentStop additionally retains agent_transcript_path when the host supplies a valid absolute path. Never read that file, or invent a child event-log link from an agent identifier. |
| FR-15 | Missing/null/invalid optional metadata is omitted while preserving the event. Bound IDs1024bytes, type256bytes, path4096bytes; omit empty/control-character metadata and nonabsolute paths. Serialize through JSON escaping. |
| FR-16 | Prompts, arguments, results, last_assistant_message, transcript contents, parent identifiers and all unknown fields remain excluded. Historical lines are preserved; mixed old/new records remain readable. |
| FR-17 | Sourcepreview3 includes the helper frompreview2 and README explains parent event file versus host transcript path, optional metadata and installedpreview1 update requirement. |

Grounding: official Hooks docs list agent_id/type on both lifecycle events, agent_transcript_path onStop, and parent session_id on subagent callbacks. The host does not guarantee a distinct child event-log file. A transcript path is metadata about Codex's own transcript, not a promise that our plugin captured child tool events.
