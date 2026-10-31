# Codex hook events and schemas

Reference checked on 2026-10-21 against the official [Codex Hooks documentation](https://learn.chatgpt.com/docs/hooks). This package registers all twelve events below in [hooks.json](../hooks/hooks.json).

## Host input versus saved records

Codex sends one JSON object on standard input to a command hook. That object can contain session content. This logger saves a smaller allowlisted record; adding this reference does not enable recording of prompts, tool content or transcripts.

- [Hook input schema](../schemas/hook-input.schema.json): a maintained, permissive JSON Schema profile of the documented input fields, with a definition for every event.
- [Saved record schema](../schemas/log-record.schema.json): the logger's JSONL record shapes, including optional subagent metadata. Each line is one independent JSON object, not a JSON array.

These schemas are package-maintained references, not official generated wire schemas or runtime validators. The input profile requires only the routing fields `session_id` and `hook_event_name`, types known fields when present, and permits unknown fields for host evolution. Optional in this profile does not prove a field is optional in Codex's own protocol. Null and absent are different. The linked official guide warns that development-branch schemas can describe unreleased fields. Use the exact host version when strict wire validation is required; source checks do not prove every desktop callback is emitted.

See [the future Amplifier integration reference](amplifier-integration.md) for user prompt text, main/subagent response snapshots, tool results and the distinct hook-reply contract. Incoming content fields are documented here but are not saved by this logger.

## Common input fields

| Field | Type | Meaning |
|---|---|---|
| `session_id` | string | Session receiving the callback; subagent lifecycle hooks use the parent session. |
| `hook_event_name` | string | One of the twelve names below. |
| `transcript_path` | string or null | Native session transcript location, when provided. |
| `cwd` | string | Session working directory. |
| `model` | string | Active model identifier; Codex extension. |

The `permission_mode` string accompanies SessionStart, UserPromptSubmit, PreToolUse, PostToolUse, PermissionRequest, SubagentStart, SubagentStop, Stop and Interrupt. Documented values: `default`, `acceptEdits`, `plan`, `dontAsk`, `bypassPermissions`.

`turn_id` is a string identifying the active turn on the events that list it below. `JSON` means any JSON value, including null, arrays, objects and scalar values. Fields in the next table supplement the common fields and applicable permission mode.

## Complete event catalogue

| Event | Trigger | Additional input fields |
|---|---|---|
| `SessionStart` | Session begins, resumes or restarts after compaction/fork. | `source`: `startup`, `resume`, `clear`, `compact` or `fork`. |
| `SessionEnd` | Main session terminates; does not run for subagents. | `reason`: currently `other`. |
| `UserPromptSubmit` | User submits a prompt. | `turn_id`: string; `prompt`: string. |
| `PreToolUse` | Before a supported local tool call. | `turn_id`, `tool_name`, `tool_use_id`: strings; `tool_input`: JSON. |
| `PostToolUse` | After a supported tool returns, including nonzero shell exit. | `turn_id`, `tool_name`, `tool_use_id`: strings; `tool_input`, `tool_response`: JSON. |
| `PermissionRequest` | Before Codex asks for approval. | `turn_id`, `tool_name`: strings; `tool_input`: JSON. `tool_input.description` can be a string or null for approval context; do not assume it is present. |
| `SubagentStart` | A child starts. | `turn_id`, `agent_id`, `agent_type`: strings. |
| `SubagentStop` | A child reaches its stop hook. | `turn_id`, `agent_id`, `agent_type`: strings; `agent_transcript_path`: string or null; `stop_hook_active`: boolean; `last_assistant_message`: string or null. |
| `PreCompact` | Before context compaction. | `turn_id`: string; `trigger`: `manual` or `auto`. |
| `PostCompact` | After context compaction. | `turn_id`: string; `trigger`: `manual` or `auto`. |
| `Stop` | Main agent finishes a turn; not session termination. | `turn_id`: string; `stop_hook_active`: boolean; `last_assistant_message`: string or null. |
| `Interrupt` | User interrupts an active main-thread turn; not subagents. | `turn_id`: string. |

Tool names can be `Bash`, `apply_patch` or MCP/function names. Tool input/output shapes depend on the tool. Hosted tools and specialized paths can have different coverage. A lifecycle callback is not evidence that the child thread was destroyed; stop hooks can continue work. Only SessionEnd denotes main-session termination.

## Subagent correlation

The parent log contains SubagentStart/Stop. Match those entries using `agent_id`. A host-provided `agent_transcript_path` at stop identifies Codex's native child transcript, not a separate event file created by this plugin. The logger never opens that transcript or infers a child event filename from `agent_id`. Other events are routed using the `session_id` the host actually supplies.

Example host input:

```json
{
  "session_id": "parent-session",
  "hook_event_name": "SubagentStop",
  "transcript_path": null,
  "cwd": "/workspace/project",
  "model": "host-model",
  "permission_mode": "default",
  "turn_id": "turn-1",
  "agent_id": "child-42",
  "agent_type": "reviewer",
  "agent_transcript_path": "/workspace/native/child-42.jsonl",
  "stop_hook_active": false,
  "last_assistant_message": "This content is not copied to the event log."
}
```

Saved record:

```json
{"event_type":"SubagentStop","agent_id":"child-42","agent_type":"reviewer","agent_transcript_path":"/workspace/native/child-42.jsonl"}
```

Ordinary saved record:

```json
{"event_type":"PreToolUse"}
```

Metadata is optional in saved records because invalid/missing values are omitted while the event survives. Rust additionally enforces nonempty fields without control characters and UTF-8 byte limits: agent ID 1024 bytes, agent type 256 bytes, transcript path 4096 bytes. Transcript paths must be absolute for the supported Unix platform. The saved-record schema documents character bounds and these byte limits as annotations; standard JSON Schema counts characters, not UTF-8 bytes, so the Rust implementation remains authoritative for byte-length and platform-path checks. Historical one-key subagent records remain valid.

## Hook responses

Input fields are separate from hook responses on stdout. Codex's response shapes and permitted decisions differ by event; consult the [official output contract](https://learn.chatgpt.com/docs/hooks#common-output-fields). This plugin is observational: successful callbacks emit no stdout and exit0; failures use a fixed content-free diagnostic and exit1. It never grants approvals, blocks actions, rewrites inputs or requests continuation. The schemas above are not schemas for hook registration configuration or hook responses.
