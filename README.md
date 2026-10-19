# AI Augmentation Systems for OpenAI

A marketplace for reusable plugins targeting Codex CLI, the Codex desktop app,
and supported ChatGPT surfaces. Maintained independently of the
[Claude marketplace](https://github.com/colombod/ai-augmentation-systems).

**Status: repository foundation and compatibility research. No plugins are
published in this catalogue yet.** Delivery is the first planned port; its
shipping team is not implemented or accepted on OpenAI surfaces.

## Repository layout

- `.agents/plugins/marketplace.json`: catalogue, with one entry per released plugin.
- `plugins/<name>/`: self-contained installable packages, each versioned separately.
- `docs/`: platform findings and port assessments.
- `evidence/`: dated observations with explicit evidence limits.
- `tests/fixtures/`: diagnostic packages, excluded from the marketplace.
- `.beads/`: project tracking configuration. Beads/Dolt holds task state.

The catalogue can be registered with:

```sh
codex plugin marketplace add colombod/ai-augmentation-systems-openai
```

Registration does not install a delivery plugin: the catalogue is intentionally
empty. Install and trust instructions will accompany each accepted release.

## Current evidence

Read [platform validation](docs/platform-validation.md) and the
[delivery assessment](docs/delivery-port-assessment.md) before implementing the port.

Codex CLI 0.159.3 installed an isolated diagnostic plugin and discovered its skill.
Local configuration hooks executed against a loopback model stub. Compatibility
plugin hooks were listed, but execution was not confirmed. Desktop UI access was
rejected by the computer-use tool. These are not full delivery acceptance results.

## Contributing

Run `python3 scripts/validate_marketplace.py`. Use `bd ready` and `bd show <id>`
for work tracking. Keep plugins self-contained and test CLI and desktop separately.
Do not change the Claude marketplace as a side effect of this project.

MIT. Copyright 2026 Diego Colombo.
