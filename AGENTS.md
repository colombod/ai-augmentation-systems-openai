# Repository instructions

This repository hosts multiple OpenAI plugins. Follow any plugin-specific
`plugins/<name>/AGENTS.md` before changing that plugin.

- Use Beads (`bd`) for all durable task tracking; run `bd prime` when context is missing.
- Read the global Beads skill at `~/.agents/skills/beads/SKILL.md` when available.
- Do not create Markdown TODO lists or ad hoc memory files.
- Keep every installable plugin self-contained under `plugins/<name>/`.
- Keep diagnostic fixtures outside the marketplace catalogue.
- Preserve source attribution and the upstream revision for imported material.
- Never alter the existing Claude marketplace as a side effect of this port.
- Do not confuse persistent delivery roles with temporary reviewer subagents.
- Preserve failed observations. Distinguish documentation, source checks, protocol
  probes, stub-backed runtime tests, real-model acceptance and desktop UI acceptance.
- Codex CLI and desktop are independent required acceptance targets. ChatGPT has
  separate runtime/distribution constraints and requires separate validation.
- Judge providers must be explicitly selected. Never silently switch providers or
  treat model classification as evidence that a human granted authority.
- Never copy credentials or personal Codex configuration into this repository.
- Do not weaken hook trust, sandbox or approval settings to make a release work.
- Run `python3 scripts/validate_marketplace.py` before publishing catalogue changes.
- Do not commit, push or publish unless the current user request authorizes it.
