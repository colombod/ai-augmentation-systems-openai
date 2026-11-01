# Hook Event Log

Record local Codex lifecycle events using Node.js 22 or later. The package has no runtime npm dependencies and needs no compiler or native executable. It makes no model or network calls.

Each successful callback publishes one JSONL record, for example:

```json
{"event_type":"PreToolUse"}
```

Only SubagentStart/Stop may also contain valid `agent_id` and `agent_type`; SubagentStop may include an absolute `agent_transcript_path`. The path is metadata: the logger never opens the transcript. Prompts, tool arguments/results, messages, raw session IDs and timestamps are not recorded. Invalid optional metadata is omitted. Repeated events remain visible.

## Prepare and install

From this plugin directory:

```sh
node scripts/build.mjs
node --test tests/*.test.mjs
```

Preparation copies the packaged JavaScript sources into `dist`; no dependency installation is needed. Package only this plugin directory, including the manifest, generated files, schemas, references and notices. The runtime Node executable must be visible to the host; desktop apps may not inherit a terminal version-manager environment.

From the marketplace repository root:

```sh
codex plugin marketplace add .
codex plugin add hook-event-log@ai-augmentation-systems-openai
```

Use the installed CLI's help for version-specific syntax. Inspect `/hooks` and use the ordinary host review/trust controls. Installation does not grant hook trust. Do not bypass disabled/managed-only hooks or alter approval and sandbox policy. Refresh/reinstall the plugin and open a fresh local chat when updating; editing source does not refresh an installed cache.

This preview targets local Unix CLI and desktop environments. Actual Node22, macOS and desktop acceptance for this version remains unverified; Linux Node24 command tests do not qualify those surfaces. Windows, ChatGPT and remote/cloud hook activation are not qualified. Prior desktop observations apply to prior versions only.

Registered events: SessionStart, SessionEnd, UserPromptSubmit, PreToolUse, PostToolUse, PermissionRequest, SubagentStart, SubagentStop, PreCompact, PostCompact, Stop and Interrupt. Only callbacks emitted by the host can be captured. Stop ends a turn, not a session.

## New storage and upgrade behavior

Preview.5 preserves the JSONL record schema but changes storage layout. New records are published under:

```text
<PLUGIN_DATA>/event-types-v2/<SHA-256 of session_id>/<unique-event-id>/record.jsonl
```

A private staging file named `pending` is not a published record. Interrupted staging directories remain and are ignored. The package introduces no automatic cleanup, retention or data migration.

Earlier versions continue writing their original files:

```text
<PLUGIN_DATA>/event-types/<session-hash>.jsonl
```

New and old versions never share a writable record file. Existing files are not renamed, rewritten or deleted. **A legacy `tail -f` command will not show new-version events.** Use the combined viewer below for a session with either or both layouts. Restoring an older plugin leaves newer records intact, but the older helper cannot display them; retain this viewer to read both generations.

`PLUGIN_DATA` is supplied by the host and must be absolute for hook callbacks. Find the selected session hash by listing directory names under `event-types-v2`, or from an existing legacy filename. Hashing provides routing, not anonymization of predictable IDs.

## View a session

Pass the selected 64-character lowercase hexadecimal session hash explicitly:

```sh
node dist/view-log.js --session '<session-hash>'
node dist/view-log.js --session '<session-hash>' --follow
```

The viewer uses `PLUGIN_DATA`, otherwise `CODEX_HOME`, otherwise `HOME/.codex`, with the default suffix `plugins/data/hook-event-log-ai-augmentation-systems-openai`. A present but empty/relative override fails without fallback. It reads only logger records, never transcripts. Export prints complete legacy rows in byte order, then published new rows in lexical event-ID order. IDs do not encode chronology. Follow reports subsequent observations; restart replays history. There is no persistent cursor, global causal order or cross-run exactly-once promise. A snapshot racing a writer is not an atomic cross-generation snapshot.

The viewer fails visibly instead of silently truncating. Limits per selected session: 10,000 event directories/seen IDs, 64 MiB initial legacy input, 64 KiB per fragment or incomplete legacy tail, and at most 256 rows or 4 MiB queued output (the implementation may use a smaller queue). Export has a 30-second deadline; follow scans have 2.4 seconds and poll sequentially about once per second. Slow consumers count against the deadline. If a limit or malformed published record is encountered, stderr is `hook-event-log: session view incomplete` and exit is 1. Already emitted rows form a partial view; do not treat them as a complete export.

The legacy locator remains available:

```sh
node dist/latest-log.js
```

It prints the newest regular legacy hashed JSONL file by nanosecond mtime, then filename on ties. It does not read contents or create paths. It does not locate new fragment records. No legacy log or unsafe path produces `hook-event-log: no readable session log found` and exit 1.

## Safety and limits

Input is limited to 1 MiB; session IDs to 1024 UTF-8 bytes. Subagent ID/type/path limits are 1024/256/4096 UTF-8 bytes, rejecting empty/control-character values; transcript paths must be absolute. Unknown input fields are not copied. See the [event reference](references/hook-events.md), [input schema](schemas/hook-input.schema.json) and [saved-record schema](schemas/log-record.schema.json).

Hook success is quiet with exit 0. Failure emits only `hook-event-log: event could not be recorded` and exits 1, never blocking exit 2. The supervisor applies a 2.4-second deadline under the registered 3-second hook timeout. Host scheduling and process startup consume that budget. Path traversal rejects symlinks and verifies directory identity before writing; storage is private and owned on supported Unix systems. Filesystem failures, timeout or shutdown can lose callbacks. If a process dies after publication but before acknowledgement, completion is uncertain; do not automatically retry it. This is diagnostic logging, not tamper-proof auditing or a guaranteed delivery service.

Disable through host plugin/hooks controls or use `codex plugin remove hook-event-log@ai-augmentation-systems-openai`. The package never deletes historical logs; the host's own uninstall data behavior requires separate verification.

MIT licensed. [Third-party notices](THIRD_PARTY_NOTICES.md) retain earlier dependency attribution. [Amplifier integration notes](references/amplifier-integration.md) describe a separate future integration; no content capture is enabled.
