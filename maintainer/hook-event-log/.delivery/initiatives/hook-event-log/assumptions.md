# Assumptions

| ID | Kind | Assumption | Status | Evidence / spike / affected criteria |
|---|---|---|---|---|
| A-1 | external-host | Desktop discovers, trusts and executes packaged hooks with PLUGIN_DATA. | assumed | Real desktop installation and callback spike; FR-3, FR-7. |
| A-2 | platform | Node and Rust build tools can produce a runnable macOS package. | verified for macOSarm64 | Build log and independent packaged execution in evidence/2026-10-21/hook-event-log/; desktop UI remains separate. |
| A-3 | external-host | Delivered events carry stable session_id and hook_event_name. | assumed | Official hooks docs establish contract; actual desktop callback still required for FR-7. |
