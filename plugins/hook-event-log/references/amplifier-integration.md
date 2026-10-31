# Conversation data and replies: reference for later Amplifier integration

Checked against the official [Codex Hooks reference](https://learn.chatgpt.com/docs/hooks) on 2026-10-21. This is integration documentation, not an implemented Amplifier adapter. The logger's current content exclusions remain unchanged.

## Four separate interfaces

| Interface | Direction | Meaning |
|---|---|---|
| Hook input | Codex to a hook's stdin | A lifecycle event, possibly containing a prompt, latest assistant message or tool result. |
| Hook reply | Hook stdout/exit status back to Codex | Optional context, warnings or event-specific control decisions. It is not an agent's conversational response. |
| Saved event record | This logger to its JSONL file | Event type, plus allowlisted metadata for subagent lifecycle events. No conversational content. |
| Future Amplifier adapter | A separately implemented translator to Amplifier | Must map the native evidence to the actual target Amplifier contract; no mapping or SDK integration is shipped here. |

The [input schema](../schemas/hook-input.schema.json) describes documented hook payload fields. The [saved record schema](../schemas/log-record.schema.json) describes the reduced logger output. Do not feed saved event records into a conversation importer and assume the omitted text can be recovered from them.

## Where user and agent messages are available

| Information wanted | Native callback | Field and type | Evidence boundary |
|---|---|---|---|
| Submitted user prompt | `UserPromptSubmit` | `prompt: string` | Prompt text for that callback; not a complete history or proof of human approval. |
| Latest main-agent answer | `Stop` | `last_assistant_message: string or null` | Latest message when supplied; not a stream of every assistant message or token. |
| Latest subagent answer | `SubagentStop` | `last_assistant_message: string or null` | Child's latest message when supplied; use `agent_id` to identify the child. |
| Requested tool call | `PreToolUse` | `tool_name: string`, `tool_use_id: string`, `tool_input: JSON` | Supported local tool paths only. JSON value shapes depend on the tool. |
| Returned tool result | `PostToolUse` | Above tool fields plus `tool_response: JSON` | Result is not necessarily a string or success. Nonzero shell exits also trigger this hook. |
| Approval request | `PermissionRequest` | `tool_name: string`, `tool_input: JSON` | This announces a request, not the user's answer. There is no dedicated permission-answer hook in this twelve-event set. |
| Main transcript location | Common fields | `transcript_path: string or null` | Metadata about a native transcript. Its file format is not a stable hook interface. |
| Child transcript location | `SubagentStop` | `agent_transcript_path: string or null` | Optional location; not the transcript contents and not a child event-log filename. |

The full common/event field list is in [hook-events.md](hook-events.md). In the input JSON Schema, the relevant definitions are `$defs.UserPromptSubmit`, `$defs.Stop`, `$defs.SubagentStop`, `$defs.PreToolUse` and `$defs.PostToolUse`.

Nullable text means the host can provide null. If a host version omits a field, retain its absence rather than inventing text or interpreting absence as a successful empty response. Do not claim reasoning traces, hidden prompts, streamed deltas, attachments or complete multimodal messages from these fields: this documented hook contract does not establish them. A latest-message snapshot cannot prove that earlier responses were captured.

### Prompt example: input to a future adapter

```json
{
  "hook_event_name": "UserPromptSubmit",
  "session_id": "parent-session",
  "transcript_path": null,
  "cwd": "/workspace/project",
  "model": "host-model",
  "permission_mode": "default",
  "turn_id": "turn-1",
  "prompt": "Review the parser and explain the edge cases."
}
```

### Main-agent response example

```json
{
  "hook_event_name": "Stop",
  "session_id": "parent-session",
  "transcript_path": null,
  "cwd": "/workspace/project",
  "model": "host-model",
  "permission_mode": "default",
  "turn_id": "turn-1",
  "stop_hook_active": false,
  "last_assistant_message": "The parser handles empty input, but malformed escapes need a check."
}
```

### Subagent response example

```json
{
  "hook_event_name": "SubagentStop",
  "session_id": "parent-session",
  "transcript_path": null,
  "cwd": "/workspace/project",
  "model": "host-model",
  "permission_mode": "default",
  "turn_id": "turn-1",
  "agent_id": "child-42",
  "agent_type": "reviewer",
  "agent_transcript_path": "/workspace/native/child-42.jsonl",
  "stop_hook_active": false,
  "last_assistant_message": "I found an unhandled malformed escape."
}
```

These are synthetic format examples, not captured conversations. This logger saves only `event_type` from the first two examples, and the allowlisted child metadata from the third. It does not save any `prompt` or `last_assistant_message` above.

## Correlation rules for an adapter

Preserve the native `hook_event_name` alongside any translated event type. Retain the host's `session_id`, available `turn_id`, child `agent_id` and tool `tool_use_id` as separate identifiers. Subagent lifecycle hooks use the parent session ID; do not relabel it as the child's session ID or assume `agent_id` is an event-file session key. Ordinary tool events do not document a child identifier in their event-specific field list, so child attribution must not be invented from nearby lifecycle events.

Pair tool-before/tool-after observations by the supplied IDs and scope, not merely file order. There is no universal event ID, timestamp, assistant-message ID or full parent/child tree documented in the common payload. A translator can add a clearly labelled observation ID/time for its own bookkeeping, but cannot claim those values are native emission identity/time or use them to prove exact-once capture. Matching hooks can run concurrently and background hooks can complete out of order.

`Stop` is turn-scoped, and `SubagentStop` can participate in continuation; neither proves session termination or disposal of a child. Only `SessionEnd` denotes main-session termination. `stop_hook_active` helps recognize continuation behavior; it is not a completion-success flag. A hook-generated continuation can act as a new user prompt, so a prompt-shaped observation is not independent evidence that a person typed or approved it.

Use the existing Amplifier event contract selected by the eventual implementation. This document does not assign Amplifier event names, claim SDK compatibility, or specify an emitter/writer topology. Those decisions need the target library version and actual adapter validation.

## Replies returned by hook scripts

These are **hook-to-Codex control/context replies**, separate from the assistant text in incoming events. The observing logger returns no stdout on success and makes none of these decisions. For supported behavior, use the event-specific contract rather than one universal response object.

| Event | Documented reply behavior relevant to integration |
|---|---|
| `SessionStart` | Can supply `systemMessage`, common output fields and `hookSpecificOutput.additionalContext`; plain text is developer context. |
| `UserPromptSubmit` | Can supply context/warnings, or `decision: "block"` with `reason` to reject the submitted prompt. Plain text becomes developer context. |
| `SubagentStart` | Can supply a warning or child developer context. `continue: false` does not stop the child from starting. |
| `PreToolUse` | Supported `permissionDecision` values are `allow` and `deny`. `additionalContext` can be supplied; `updatedInput` requires `allow`. `ask` and several legacy/common fields are parsed but unsupported. |
| `PermissionRequest` | `hookSpecificOutput.decision.behavior` can be `allow` or `deny`; declining to decide preserves normal approval. Do not return `updatedInput`, `updatedPermissions` or `interrupt`. |
| `PostToolUse` | Can add context/warnings or stop/redirect processing with supported output fields. A `block` decision supplies feedback after the call; it cannot undo side effects. |
| `PreCompact`, `PostCompact` | Support common output fields, including `continue: false`; plain text is ignored. |
| `Stop`, `SubagentStop` | A `decision: "block"` plus `reason` requests continuation. Here “block” means continue working, not deny a tool. `continue: false` takes precedence. Nonempty stdout must be JSON. |
| `SessionEnd` | Advisory finalization; cannot keep the conversation open or steer it. |
| `Interrupt` | Empty successful output or an optional JSON `systemMessage`; cannot prevent interruption or restart the turn. |

The common output keys are `continue: boolean`, `stopReason: string`, `systemMessage: string` and `suppressOutput: boolean`, but they are not supported uniformly. In particular, `suppressOutput` is parsed but unimplemented; PreToolUse and PermissionRequest do not support common `continue`/`stopReason` controls. Read the [official common and per-event output contract](https://learn.chatgpt.com/docs/hooks#common-output-fields) before choosing a reply. Legacy accepted shapes, exit-code effects and reserved fields must be checked against the host version; syntactically valid JSON alone does not establish supported behavior.

Example adding context to a submitted prompt:

```json
{
  "hookSpecificOutput": {
    "hookEventName": "UserPromptSubmit",
    "additionalContext": "Project instructions require a separate review before publication."
  }
}
```

Example requesting continuation at a stop hook:

```json
{
  "decision": "block",
  "reason": "Run the pending validation before finishing."
}
```

These are format examples for future implementers, not actions emitted by this plugin. Context injection or model classification cannot establish human authority. A hook that programmatically allows a request also does not prove a human approved it.

Background command hooks can return informational output at a later safe point, but cannot approve, block, rewrite or control the triggering operation. Their completion does not start a new user turn. Session end can cancel unfinished background hooks. Keep content collection independent of control decisions; a passive Amplifier observer normally needs neither approval grants nor continuation replies.

## Boundaries to verify before building

Run actual input probes on the intended CLI and desktop versions separately. Verify prompt text availability, null/missing response handling, main/child correlation, tool failures, continuation, interruption and compaction. Verify the selected Amplifier library's actual event schema and ordering/identity expectations before naming translations. Native transcript reads, if proposed, require an explicit content-capture scope and a version-specific parser; transcript paths alone do not establish a stable read API or full-history coverage.

Content capture would be a new feature with explicit scope, storage and retention behavior. This documentation does not turn it on. The minimal event logger remains suitable for observing which callbacks fire while an eventual integration is designed.
