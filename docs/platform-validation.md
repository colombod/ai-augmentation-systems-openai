# Platform validation — 19 October 2026

## Scope

Codex CLI and the Codex desktop app are required targets. ChatGPT remains a
separate target from the original request. This record validates selected
mechanisms, not delivery implementation or feature parity.

## Observed results

| Mechanism | Evidence | Result |
|---|---|---|
| Marketplace registration and plugin installation | Installed isolated fixture with CLI 0.159.3 | Passed |
| Skill discovery | `skills/list` returned `mechanism-probe:probe` with plugin identity | Passed |
| Root portable manifest hooks | Initial installed fixture yielded no hooks in `hooks/list` | Unresolved; preserve observation, do not assume platform defect |
| Compatibility manifest hooks | Clean reinstall using `.codex-plugin/plugin.json` returned four hooks with source `plugin` and untrusted status | Discovery passed |
| Bundled hook execution | Stub-backed CLI run did not append lifecycle events for its thread | Not confirmed; release blocker |
| User configuration hook execution | Isolated `hooks.json`; vetted per-invocation trust bypass; loopback SSE stub | SessionStart, UserPromptSubmit, Stop and SessionEnd observed |
| Persistent session creation | `thread/start` and `thread/read` | Passed |
| Resume/fork before a first turn | No persisted rollout yet | Rejected with `no rollout found`; do not treat an unused thread as recoverable |
| Resume/fork after a completed stub turn | App-server calls against persisted CLI thread | Passed |
| Desktop installation and UI | App 26.1013.40934, build 20770; tool rejects `com.openai.codex` for safety reasons | Blocked; not accepted |
| Real model and multi-role behaviour | No live model invoked | Not tested |
| Tool denial, question provenance and independent evidence | Requires port adapters and live tests | Not tested |

The loopback stub proves transport/lifecycle plumbing only. It supplies a fixed
answer and synthetic usage. It does not establish model quality, real spending,
role autonomy, operator provenance or recovery after actual model/tool failure.

All probe installations and configuration writes used a temporary Codex data
directory. Personal Codex settings and credentials were not copied or modified.
The per-invocation hook bypass was limited to reviewed fixture scripts; it is not
a proposed user installation method or evidence of persisted trust review.

## Distribution boundaries

The official packaging guide describes repository catalogues for supported local
clients, including CLI and desktop. The migration guide requires removing lifecycle
hooks for public directory submissions and points hook-dependent plugins toward
manual local installation. Cloud orchestration restricts local/plugin hooks.
Local Codex acceptance does not establish ChatGPT web or cloud acceptance.

## Evidence and reproduction

Machine-readable results and retained fixture scripts are under
[`evidence/2026-10-19`](../evidence/2026-10-19/). The reproduction scripts describe
the experiment, not a turnkey acceptance suite: they assume a disposable fixture,
isolated configuration and, for protocol resume, an existing probe thread.
No real-model acceptance test was run.

The bundled hook discovery/execution difference and desktop access restriction
remain tracked in Beads. Neither is waived by creating this marketplace.

## Sources checked

- [Plugin packaging](https://developers.openai.com/plugins/build/plugins)
- [Claude plugin migration](https://developers.openai.com/plugins/guides/submit-claude-plugin)
- [Codex hooks](https://learn.chatgpt.com/docs/hooks)
- [Codex app-server](https://learn.chatgpt.com/docs/app-server)
- [CLI reference](https://learn.chatgpt.com/docs/cli/reference)

These are documentation claims as checked on this date, not a guarantee that
every installed client release implements every documented behaviour.
