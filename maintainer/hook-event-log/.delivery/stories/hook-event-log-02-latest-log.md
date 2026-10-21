---
status: ready
surface: S1
task: oap-15v.2
---

# Find the session log

As the requesting desktop user, I want a command that prints the newest session log path, so I do not need to discover PLUGIN_DATA manually.

| ID | Acceptance |
|---|---|
| FR-8 | `node dist/latest-log.js` prints the absolute path of the newest regular hashed JSONL session log, selected by modification time with a deterministic filename tie break. |
| FR-9 | Rust resolves explicit PLUGIN_DATA first, otherwise CODEX_HOME/plugins/data/hook-event-log-ai-augmentation-systems-openai, otherwise HOME/.codex/plugins/data/hook-event-log-ai-augmentation-systems-openai. Reject empty/relative overrides without silently selecting another root. |
| FR-10 | The helper is read-only: no input reading, directory creation, log content reading or writes. Missing logs and invalid roots fail with a fixed message and exit1. Reject symlink directories and entries. |
| FR-11 | Existing hook records remain event-type-only and normal hook invocation still requires host PLUGIN_DATA. TypeScript is transport; Rust owns helper logic. |
| FR-12 | Bump source to preview.2; README gives the new command and verified default local location. Installed preview.1 remains distinct until the user refreshes/reinstalls. |

No dependencies on incomplete desktop UI inspection. This command is a local read-only utility; it does not change the hook definition or trust state. Test missing/empty roots, precedence, latest selection, symlinks, existing contents unchanged, normal callback regression and actual current user session selection.
