# Targeted live behavior tests

Three scenarios from `tests/delivery/scenarios/behavior.json` were run through
Codex CLI 0.159.3 with real model inference, after the user explicitly authorized
transmitting revised private skill/reference text and synthetic scenario inputs
to the Codex model service. No credentials or personal configuration were copied.

| Scenario | Initial result | Final result |
|---|---|---|
| Status without project access/artifacts | Pass | Pass |
| Brief without delegation, computation or saving | Pass | Pass |
| Synthetic interview without workers | Partial: one follow-up suggested a remedy | Pass after a narrow guidance correction and one rerun |

`assessment.json` records each criterion and its supporting observation.
`runs.json` and each scenario's `run.json` record exit codes, resource hashes,
event/item types, elapsed time and the CLI's reported token usage. `answer.md`,
`prompt.txt`, `events.ndjson` and `stderr.txt` retain the actual inputs/results.
The corrected interview is under `simulation-rerun/`; the first result is intact.

The preserved `runner.py` files show the exact execution. They are evidence
scripts with this checkout's absolute paths, not portable test commands. Running
them incurs model calls and can overwrite that run's artifacts; use a new output
directory when reproducing. Earlier sandbox/approval failures remain in the
separate `plugin-creator-fixes` evidence directory.

The runs used ephemeral native CLI sessions, ignored user configuration and used
read-only temporary workspaces. All observed items were agent messages; no tool
invocation was observed. The CLI default model was used without a model override.
Exact model identity was not emitted in the retained CLI event stream.

This is a manual assessment by the implementation session, not independent
grading. Missing tools were simulated through instructions; tools were not
physically removed from the native client. Sources were supplied inline rather
than activated through the installed plugin loader. These results do not prove
full-pipeline quality, actual desktop/ChatGPT behavior, provider judging or the
persistent-role runtime. Package installation/discovery remains a separate probe.
