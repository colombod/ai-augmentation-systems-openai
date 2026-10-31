---
sprint: 1
slug: hook-event-log
status: handed-off
runner: authorized Codex implementation agents
task: oap-15v
---

# Scope package: event-type logging

Stage promise: a separate local plugin that shows the requesting user's session event types without content. Story `../stories/hook-event-log-01-local-logger.md` is ready and has no unfinished external dependencies or open blocking findings. Criteria map directly to FR-1–FR-7 and NFR-1–NFR-4 in the PRD.

Build under `plugins/hook-event-log/`. Keep Delivery unchanged. TypeScript is transport; Rust is all logging logic. Follow `../initiatives/hook-event-log/architecture.md`. UI design tokens are inapplicable. No MCP, model calls, full-payload mode, automatic deletion or publication.

Engineering estimate: one bounded implementation wave. Model/token budget unknown; report actual test evidence rather than an invented cost. Stop if a criterion conflicts with the supported host, native build fails after bounded investigation, or success requires bypassing trust or permissions. Record honestly blocked work. Keep changes local in the current working tree: the user's request authorizes implementation, not commits/pushes.

Verification contract: `npm run build` and `npm test` inside the package, `cargo test --locked --manifest-path plugins/hook-event-log/core/Cargo.toml`, and `python3 scripts/validate_marketplace.py`. Exercise 32 concurrent packaged hooks, both malformed and over-limit input, payload sentinels, absent data root, symlink refusal and a fresh session log. Native desktop inspection must separately satisfy FR-7.

Report each criterion with met/not met/unable to check, actual commands/output, changed files, branch/revision, deviations and remaining host assumptions. Return to Delivery sprint-review using an independent reviewer for implementation and package readiness; preserve failed observations.
