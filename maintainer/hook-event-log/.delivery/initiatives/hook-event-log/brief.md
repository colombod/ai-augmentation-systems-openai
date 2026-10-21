# Product brief: session event types

Written using Delivery's brief workflow. Mode: frame. Status: scoped from the user's request, 2026-10-21.

## Coverage

Single-session review using product-owner, business-analyst and feature-critic lenses. Independent convergence unavailable at framing; implementation receives a separate reviewer. Coverage is bounded to a small local logger, not a complete observability system.

| Lens | Finding | Resolution |
|---|---|---|
| Value | A desktop user wants to see what happens during a session without recording its content. | One readable session log of event types. |
| Precision | Concurrent hooks, malformed events and session separation need explicit behavior. | Serialize appends; validate names; hash the session identifier for the filename. |
| Absence | Installation is not hook trust, and a shell test is not desktop acceptance. | Document review/trust and validate the desktop separately. |

## Problem and audience

The requesting Codex desktop user cannot readily inspect the sequence of lifecycle events in a session. Debugging currently relies on visible chat activity or larger transcripts. The cost is unclear behavior and unnecessary exposure of session content; time cost is unknown.

## Outcome and success

A trusted local plugin records each delivered event as a JSON line with exactly one key, `event_type`. The log excludes timestamps, raw identifiers, paths, prompts, tool arguments and outputs. Different sessions have separate files named by a hash of the session identifier. File order is append order, not a causal ordering guarantee across concurrent events.

| Signal | Measure | Current | Target |
|---|---|---|---|
| Content exclusion | Send sentinel-bearing hook input and inspect every file | No logger | Only event names persist |
| Concurrent completeness | Concurrent process probe | Unknown | Every successful invocation appears once |
| Desktop behavior | Trusted plugin in an actual desktop session | Unverified | Native events produce a session log |

## Boundary

Build a self-contained local plugin with a TypeScript adapter, matching the Codex SDK language, and a Rust library plus executable. No model call, server, MCP, payload option, timeline UI, transcript reader, automatic retention, release publication or modification of Delivery itself. No completeness claim for events the host does not expose or deliver.

## Workflow and unknowns

Build, install, review/trust hooks, open a local desktop chat, then follow the session log. Disable the plugin to stop collection; remove its data to delete logs. Desktop hook execution and GUI acceptance remain host assumptions until tested. The implementer owns that verification; no further product choice is required for this bounded scope.
