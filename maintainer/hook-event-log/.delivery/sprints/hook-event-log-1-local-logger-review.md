# Delivery sprint review: session event types

Verdict: **Not accepted for desktop use yet.** Implementation and direct command tests pass; FR-7 requires an actual trusted desktop callback and remains unable to check. A synthetic journey can build, manually invoke and read the logger, but the target desktop journey has not been observed end to end.

Independent reviewer: `/root/event_review`, separate from both Rust and TypeScript implementers. The reviewer inspected current code and ran its own command-boundary probes. No GUI evidence was substituted with CLI results. No design system exists or applies to this command-only component.

| Criteria | Status | Direct evidence |
|---|---|---|
| FR-1 | Met for discovery | Native CLI0.159.3 lists12 event hooks, enabled/untrusted. |
| FR-2 | Met at command boundary | All event types and payload sentinel checks, exact one-key records, content-free failures. |
| FR-3 | Met at command boundary | Separate SHA-256 filenames; absent/relative root rejection; host-supplied desktop root unverified. |
| FR-4 | Met | Compiled TypeScript and actual Rust library/executable, macOSarm64 release. |
| FR-5 | Met | Empty stdout success0; fixed failure1, child error/timeout bounded. |
| FR-6 | Met | README covers dependencies/build/trust/logs/removal and explicitly marks desktop unverified. |
| FR-7 | Unable to check | Computer-use tool refuses Codex desktop access for safety reasons. |
| NFR-1–NFR-2 | Met at tested boundary | Exact1MiB bound, idle/hung deadline,32 process records, private permissions, no-follow targets. |
| NFR-3 | Partially verified | Actual macOSarm64 build; actual desktop acceptance missing. |
| NFR-4 | Met at command boundary | Source review and sentinel tests; no runtime network/model/transcript reads or deletion. |

Observed output: Rust `7 passed; 0 failed`; Node integration `11 passed`; independent checks `31/31`; marketplace `2 published plugin(s)` valid; existing Delivery Python `Ran 121 tests ... OK`; judge regression `22 pass, 0 fail`. These are local test results, not published releases. Full reports and retained failures are in `evidence/2026-10-21/hook-event-log/` from the repository root.

Ship readiness is conditional: the package has a version, build artifacts and local catalogue entry. A fresh isolated installation discovers hooks and the installed adapter can be invoked manually. Nothing is merged, committed, pushed or published, so no branch ancestry or merged-version claim applies. The original working tree contained unrelated in-progress Delivery implementation and was preserved.

Learning: the portable root manifest was accepted by installation but hid hooks on0.159.3, including when paired with a compatibility manifest. Selecting legacy-only fixes discovery; source documentation alone did not establish runtime support. Native trust and actual callback delivery remain assumptions. Logs cannot prove completeness or causal ordering, and Stop is not SessionEnd. Desktop verification is carried in Beads; do not silently downgrade its acceptance criterion.
