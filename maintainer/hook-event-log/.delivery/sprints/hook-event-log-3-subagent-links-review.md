# Delivery sprint review: follow subagents

Verdict: **Accepted as a source update; installed update pending.** FR-13–17 met by current preview3 source and compiled macOSarm64 package. Independent reviewer event_review inspected code and exercised the actual TypeScript-to-Rust boundary, separate from the implementers.

| Criteria | Evidence |
|---|---|
| FR-13 | Event-specific allowlist; lifecycle ID/type included, ordinary records one-key. |
| FR-14 | Stop-only absolute transcript path retained; unreadable/FIFO/nonexistent transcript probes return without reading or creating it. No child event-file inference. |
| FR-15 | Missing, malformed, over-limit, multibyte and control-character fields omitted with the event preserved; JSON escaping verified. |
| FR-16 | Content sentinels/unknown fields excluded; old bytes preserved;32 concurrent maximal metadata records remain complete. |
| FR-17 | Source manifest/package/lock preview3; README explains updated format, native transcript distinction and installedpreview1. |

Observed:20 Node integration tests,16 Rust tests,27 independent checks pass. Existing Delivery121Python and22judge regressions pass; marketplace2 valid. Native isolated sourcepreview3 install discovers12 untrusted hooks; manual installed-adapter protocol passes. The package description finding was corrected to reflect subagent metadata. No native trust/configuration changes were made.

The synthetic user journey can read a parent lifecycle entry, match agent_id between start/stop, and use the optional native transcript path at stop. Actual preview1 desktop logs already prove lifecycle delivery, but do not prove preview3 metadata in desktop: refreshing the installed package is still required. Visual GUI installation and full event coverage remain separate unobserved checks. No design-system tokens apply to this command-only plugin.

Learning: an agent identifier is not sufficient evidence of a separate child event file. Host-provided transcript metadata is useful without inventing a relationship. The privacy boundary changed only because the user explicitly asked for it; old one-key entries remain valid. Complete criteria and direct evidence: `evidence/2026-10-21/hook-event-log/subagent-links-review/` from repository root.
