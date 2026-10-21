# Hook Event Log

See which lifecycle event types Codex emits during a local session. Each successful callback appends exactly one line such as:

```json
{"event_type":"PreToolUse"}
```

The logger stores no prompts, tool arguments/results, message text, timestamps, transcript contents or raw parent session identifiers. In preview.3, subagent lifecycle records additionally include the host-provided subagent identifier/type, and the native transcript path on stop when available. It makes no model or network calls and emits no approval decisions. Repeated events remain visible.

For example, a subagent stop can appear as:

```json
{"event_type":"SubagentStop","agent_id":"child-identifier","agent_type":"reviewer","agent_transcript_path":"/absolute/path/to/codex/child-transcript.jsonl"}
```

Only these allowlisted metadata fields are copied. Missing or invalid metadata is omitted while preserving the event; empty, control-character and oversized values are rejected. Transcript paths must be absolute. The logger records the path without opening or copying the transcript. SubagentStart can include the ID and type; Codex documents the optional transcript path on SubagentStop. Ordinary events still contain only `event_type`. Earlier one-key records remain unchanged.

This is a local preview for Codex desktop and CLI. After the user installed preview.1, actual desktop-session logs contained `UserPromptSubmit`, tool events, `SubagentStart` and `SubagentStop`. Visual inspection of desktop installation and the full event catalogue remain separate checks. ChatGPT and remotely executed/cloud sessions are outside this package's validated scope.

## Dependencies and design

Runtime: Node.js 22 or later, available to the desktop app's command environment, and the native executable built for the same OS and processor. A desktop app may not inherit a terminal's Node version-manager environment. This package does not change your PATH or Codex configuration.

Build: Node.js/npm and a current Rust toolchain (`cargo` and `rustc`) available on PATH. The lockfiles pin the npm and Rust dependencies. npm and Cargo may use the network during dependency installation; runtime does not. Rust is required to build, but not to run the resulting package.

The TypeScript adapter uses the Codex SDK's language, but does not import or call the session SDK: hooks receive events over standard input and must not create another model session. It forwards bounded opaque input to a packaged native executable without a shell. All JSON interpretation, event validation, session hashing and disk logging are implemented in the Rust library. The executable bridge avoids Node native-addon ABI dependencies.

## Build and test

From this plugin's directory:

```sh
npm ci --ignore-scripts --registry=https://registry.npmjs.org
npm run build
npm test
cargo test --locked --manifest-path core/Cargo.toml
```

The build produces `dist/hook.js` and `bin/<platform>-<architecture>/event-log-core`. A source checkout needs this build before installation. The included native artifact supports only its build host; this is not a universal prebuilt distribution. macOS is the first acceptance target; Linux requires its own build and host validation. Windows disk logging is not implemented: the Rust core refuses non-Unix writes. Build/install again when changing supported hosts or source. Do not package `node_modules` or `core/target`.

## Install and trust

From the marketplace repository root, after building:

```sh
codex plugin marketplace add .
codex plugin add hook-event-log@ai-augmentation-systems-openai
```

These commands match Codex CLI 0.159.3. This version discovers this package through `.codex-plugin/plugin.json`; the portable root `plugin.json` route did not expose its hooks in our native discovery probe, so the package deliberately uses only the compatibility manifest. Discovery found all twelve hooks as untrusted; that is not execution or desktop acceptance. Use your installed CLI's help if its interface differs. Installation uses Codex's local marketplace and cache; editing the source later does not automatically rebuild or refresh the installed copy. Reload/reinstall through the supported host flow after rebuilding.

Use `/hooks` in Codex CLI to inspect the plugin's current command definitions and explicitly trust them using Codex's review flow. Installation alone does not grant hook trust. For desktop, use the supported local plugin and hook-review controls in your version, then open a fresh local chat. Desktop installation and trust sharing with the CLI have not been verified here; the CLI commands above alone do not prove desktop activation. If command hooks are disabled, unavailable in that host, restricted to managed hooks, or left untrusted, this plugin cannot record events. Do not bypass that policy or weaken sandbox/approval settings. The package does not install a global user hook as a workaround.

Registered events: `SessionStart`, `SessionEnd`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `PermissionRequest`, `SubagentStart`, `SubagentStop`, `PreCompact`, `PostCompact`, `Stop`, and `Interrupt`. Only callbacks actually emitted by the host can appear; event coverage can differ by host/version. `Stop` ends a turn; only `SessionEnd` denotes session termination.

See the packaged [event catalogue and schema reference](references/hook-events.md) for every event's trigger, common and event-specific input fields, subagent correlation and examples. Machine-readable references are included for [host inputs](schemas/hook-input.schema.json) and [saved JSONL records](schemas/log-record.schema.json); these are distinct formats.

For future Amplifier work, see [conversation data, agent responses and hook replies](references/amplifier-integration.md). It documents user prompts, latest main/subagent messages, tool results, correlation limits and the separate hook-to-Codex response contract. It is reference material; no Amplifier adapter or content capture is enabled.

## Find and view logs

Codex supplies the installed plugin's writable directory as `PLUGIN_DATA`. Logs live at:

```text
<PLUGIN_DATA>/event-types/<SHA-256 of session_id>.jsonl
```

Find that plugin data directory through your host's installed-plugin details/environment; its absolute location is host-dependent and is not hardcoded here. Files separate sessions without storing their identifiers. Hashing is routing, not anonymization of predictable identifiers. To watch a selected file:

```sh
tail -f '/absolute/plugin/data/event-types/selected-session-hash.jsonl'
```

Find the newest log without reading or changing its contents (introduced in preview.2):

```sh
node dist/latest-log.js
```

The Rust helper uses `PLUGIN_DATA` when explicitly supplied. Otherwise it uses `CODEX_HOME`, or `~/.codex` if that is unset. The default directory is:

```text
~/.codex/plugins/data/hook-event-log-ai-augmentation-systems-openai/event-types/
```

This location was checked with the local Codex installation. An empty or relative override fails instead of silently selecting another directory. The helper prints the newest regular hashed JSONL file by modification time; ties use the filename. It refuses symlink paths/entries and does not create directories. No logs available means a fixed error and exit code 1. Modification time identifies the most recently changed file, which can belong to another active chat.

`SubagentStart` and `SubagentStop` were observed in the parent chat's session file. Match the new lifecycle entries using `agent_id`; when supplied at stop, `agent_transcript_path` points to Codex's own child transcript. It is separate from this plugin's event log and is not a newly created child event-log file. The plugin does not infer a child's session filename from its agent identifier, or claim to capture child tool events the host did not deliver. Other callbacks are routed by the session identifier the host supplies; ordinary tool-event records do not carry agent attribution.

The source helper can inspect logs written by installed preview.1. Source preview.4 does not automatically update an installed copy; use the supported plugin refresh/reinstall flow to update it. New metadata appears only after updating; historical records are never rewritten.

For a standalone check, create a data directory and use its canonical absolute path (resolve symlinks, including macOS `/tmp`/`/var` aliases):

```sh
mkdir -p /private/tmp/hook-event-log-demo
printf '%s' '{"hook_event_name":"SessionStart","session_id":"local-demo"}' | PLUGIN_DATA=/private/tmp/hook-event-log-demo node dist/hook.js
```

Successful execution is quiet with exit code 0. On failure the adapter prints only `hook-event-log: event could not be recorded` to stderr and exits 1; it never returns blocking exit code 2. Fixed errors deliberately omit payloads and filesystem details.

## Limits and removal

The adapter accepts at most 1 MiB and sets a 2.4-second execution deadline under the configured 3-second hook timeout. Scheduling and process startup count against the host's budget; terminal-event caps may differ by installed host version. Disk errors, contention, timeout, abrupt app shutdown or missing host events can lose callbacks. Test the actual target host before relying on capture. Concurrent records are locked; observed append order is not a global causal trace. Files are owner-only on supported Unix hosts, and symlink data paths/targets are rejected. This is diagnostic logging, not tamper-proof auditing.

Logs grow until removed manually; there is no automatic retention, rotation or deletion. Disable/revoke the plugin in the host's plugin/hooks controls or run `codex plugin remove hook-event-log@ai-augmentation-systems-openai`. Remove saved logs separately only when you want to delete them. Rebuilding or disabling does not intentionally delete logs; verify your host's own uninstall data-retention behavior.

See [Codex hooks](https://learn.chatgpt.com/docs/hooks) and [plugin packaging](https://developers.openai.com/plugins/build/plugins) for the host contract. Licensed under [MIT](LICENSE); the bundled native executable's dependency licences are in [third-party notices](THIRD_PARTY_NOTICES.md).
