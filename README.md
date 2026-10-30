# AI Augmentation Systems for OpenAI

A marketplace for reusable workflows in Codex CLI, Codex desktop and supported
ChatGPT plugin surfaces. Each plugin has its own package, dependencies and usage
guide. Maintained separately from the
[Claude marketplace](https://github.com/colombod/ai-augmentation-systems).

## Plugins

| Plugin | What it does | Current status |
|---|---|---|
| [Delivery](plugins/delivery/README.md) | Frames new ideas and existing products, maps feature/code evidence and change impact, then carries owner choices through planning and review | Product/local runtime preview `0.1.0-preview.7`; desktop and ChatGPT acceptance pending |
| [Hook Event Log](plugins/hook-event-log/README.md) | Writes lifecycle types and minimal subagent identifiers/transcript links to local session files, using TypeScript and Rust | Source `0.1.0-preview.4`, with packaged event/schema reference; real desktop callbacks observed with preview.1; refresh installed copies for updates |

Delivery provides 16 skills, 21 templates and 10 review lenses. The autonomous
shipping workflow remains unfinished. Local persistent-session coordination and
explicit Jev/OpenAI judge adapters now have implementation and targeted tests;
protected workflow transitions and independent host acceptance remain open.
Desktop and ChatGPT installation/workflow acceptance remain pending.

## Requirements

To use Delivery, you need a Codex client with model access and the plugin
installed. CLI installation was verified on version `0.159.3`. The planning
workflow needs no custom server, MCP connection or separate provider API key.
Python 3.10+ is optional for its local initialization, inventory and word-count
helper. Files, browsing and delegation are used only when available and authorized.

See [Delivery's dependencies and usage](plugins/delivery/README.md) for complete
requirements and workflows. `requirements-dev.txt` is for repository development,
not ordinary plugin use. Contributors use Beads (`bd`) for task tracking.

## Install and start Delivery

Use the **working checkout containing `plugins/delivery/`**. Build Hook Event Log
before installing it; native binaries support only the platform they were built for.

From this repository's root, run in a terminal:

```sh
codex plugin marketplace add .
codex plugin add delivery@ai-augmentation-systems-openai
```

Start a fresh Codex session in the project you want to plan. Send these as
**chat prompts**, not terminal commands:

```text
$delivery:start Use the current project and initiative checkout-redesign.
```

```text
$delivery:brief Frame an improvement that shows phone shoppers delivery costs before they invest effort in checkout. Use initiative checkout-redesign.
```

Use `$delivery:status` to review the planning record or `$delivery:challenge` to
critique an artifact. See the [full usage guide](plugins/delivery/README.md#how-to-use-it).
CLI registration does not install the plugin into ChatGPT.

## Develop and validate

In a Python development environment (CI uses Python 3.12):

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-dev.txt
python scripts/validate_marketplace.py
python -m unittest discover -s tests/delivery -v
```

With Codex CLI installed, also run:

```sh
python scripts/probe_delivery_install.py
```

That probe installs into a temporary Codex home and checks skill discovery and
the installed helper without model calls or personal configuration changes.
Live behavior tests invoke models separately; their outputs, initial partial
result and limits are in the [evidence record](evidence/2026-10-20/live-behavior/README.md).

Use `bd ready` and `bd show <id>` for work tracking. Keep installable packages
under `plugins/<name>/`, catalogue entries in `.agents/plugins/marketplace.json`,
and diagnostic packages under `tests/fixtures/`. Preserve attribution and the
existing Claude marketplace.

## Changelog and upstream alignment

- [Delivery changelog](plugins/delivery/CHANGELOG.md)
- [Maintainer alignment guidance](docs/upstream-alignment.md)
- [Platform validation](docs/platform-validation.md)
- [Live planning behavior checks](evidence/2026-10-20/live-behavior/README.md)

The Claude source reference and pinned import hashes are retained for deliberate
comparison when upstream features change. Port assessments and validation evidence
are repository maintainer material, outside the installable plugin directories.

MIT. Copyright 2026 Diego Colombo.
