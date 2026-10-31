---
sprint: 3
status: handed-off
task: oap-15v.3
runner: authorized Codex implementer and independent reviewer
---

# Delivery scope: follow subagents

Implement the ready story `../stories/hook-event-log-03-subagent-links.md`, FR-13–17, with Rust as the only record-format logic. No change to hook definitions, trust, privileges or content collection. Sourcepreview3 includes the independently reviewed latest-log utility. Preserve old evidence and log lines.

The prior event-type-only privacy boundary is deliberately extended by the actual user request only for subagent metadata. Add no general payload mode. A native transcript path comes from the host; a child event-file path cannot be inferred from agent_id. Optional malformed fields are omitted rather than losing the event.

Estimate: small serialization and tests change; actual usage budget unknown. Stop if implementation needs undocumented correlation or deployment requires trust bypass. Verify packaged lifecycle examples, missing/malformed/oversized metadata, non-subagent fields ignored, no content leakage, append behavior, concurrent writers and bounded failures. Run Rust and Node suites plus catalogue validation. Independent source/runtime review required; installed update must use a supported workflow and never be claimed from source tests.
