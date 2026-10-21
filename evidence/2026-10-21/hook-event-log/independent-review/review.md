# Independent Delivery review

Reviewed 2026-10-21 using Delivery's QA Strategist and Feature Critic lenses, beginning with the user's request and the scoped brief/PRD/architecture/story before reading implementation. Implementation was not modified by this reviewer. Review base is working tree at git HEAD `b2155d78f0362ed0a648ec8cad1bec258ae1c0f6`; new plugin files are local/uncommitted.

The strongest case for this design is narrow responsibility: TypeScript transports opaque bytes, while Rust validates and records only an allowlisted event type. A short-lived local executable avoids a hosted service, model session, and Node native-module ABI dependency. The implementation matches that design.

## Findings and limits

1. **Required desktop criterion remains unable to be checked.** `../desktop-access.json` records the desktop computer-use restriction. `../isolated-install.json` demonstrates CLI installation and twelve enabled **untrusted** hook definitions, not execution. A real trusted desktop callback must still establish that the host supplies a usable `PLUGIN_DATA`, the expected event fields, and a log entry. Without that observation the requested desktop behavior cannot be accepted.
2. **Distribution is build-host-specific.** The tested executable is macOS arm64. A source checkout needs the documented build before installation. Linux is not runtime-validated; the current non-Unix Rust branch always returns failure, so Windows logging is unsupported, rather than merely awaiting validation. This documentation finding was sent to the adapter owner, corrected, and rechecked by this reviewer.
3. **Known thin coverage is explicit.** No crash/power-loss durability, disk-full injection, malicious same-user directory-rename stress, nonlocal filesystem, actual host terminal-event timing, or GUI rendering test was performed. Directory descriptors and no-follow opens prevent symlink redirection in the reviewed path, but logs are not tamper-proof. Manual retention and potential callback loss are documented. No visual design rubric applies to this command-only plugin.

No implementation correctness or payload-leakage blocker was found in the tested local command boundary. The unresolved desktop criterion prevents describing this as desktop-accepted.

## Actual verification

- `npm test`: initially ten and finally eleven tests passed after the compatibility-manifest correction. This invokes the real packaged TypeScript adapter/native executable.
- Rust: bare `cargo` failed because the review shell PATH omitted the toolchain; rerunning with `/Users/colombod/.cargo/bin` on PATH passed seven Rust integration tests. Zero unit/doc tests are defined.
- Independent `probe.py`: initial 27/27 and extended 31/31 checks passed, with both observations preserved. The latter includes twelve real adapter invocations, exact one-key records, payload sentinel exclusion from disk/stdout/stderr, SHA-256 routing, separate sessions, owner permissions, 32 concurrent processes, malformed/missing/unknown input, exact 1 MiB and oversized boundary, absent/relative roots, ancestor/root/target symlinks, hardlinks, FIFO, public modes, idle stdin deadline, held-lock failure, missing executable, native-output suppression, and hanging native subprocess deadline.
- First independent normal-event max latency was about 49 ms; bounded failure paths were below three seconds. This does not prove terminal host timing or performance under desktop load.
- `git diff --check` passed.
- Bare system-Python marketplace validation failed because `jsonschema` is absent. The root-suggested offline UV cache command also failed to resolve it. Using the ready interpreter directly at `/private/tmp/hook-log-uv-cache/archive-v0/wYQzblBauy7unvqY/bin/python scripts/validate_marketplace.py` then passed: `Marketplace valid: 2 published plugin(s)`. Initial environment failures are retained.
- Native discovery and desktop access evidence were inspected as other agent observations; this reviewer did not independently operate the desktop or change trust/configuration.

## Criterion matrix

| Criterion | Verdict | Evidence and boundary |
|---|---|---|
| FR-1 all twelve events registered | Met for source/native discovery | Exact registration integration check and inspected native discovery receipt; not proof all host events fire. |
| FR-2 event types only | Met at packaged-command boundary | Exact JSON schema and synthetic sentinels; malformed input and child diagnostics never exposed. |
| FR-3 hashed session routing | Met at packaged-command boundary | Exact hash filename, separate sessions, absent identifier rejected. Actual desktop PLUGIN_DATA remains unverified. |
| FR-4 TypeScript adapter and Rust logic | Met locally | Built macOS arm64 executable, source review and real subprocess invocations. |
| FR-5 quiet success/fixed advisory failure | Met at packaged-command boundary | Actual stdout/stderr/exit observations, including invalid inputs, contention and native failures. |
| FR-6 dependencies/build/install/trust/view/removal docs | Met | README covers required flows and host uncertainty; Windows statement corrected and independently rechecked. |
| FR-7 real trusted desktop callback | Unable to be checked | Actual desktop access refused; untrusted CLI discovery is insufficient. |
| NFR-1 input and execution bounds | Met at local adapter boundary | Exact byte limit, one over, idle stdin/native hang deadlines; host timing is separate. |
| NFR-2 concurrency/private files/symlinks | Met for tested local macOS filesystem | 32 actual processes, exact records, mode/type/link tests; no claim of tamper-proof audit. |
| NFR-3 macOS first target/platform honesty | Met for build/process validation | Actual macOS arm64 native executable; desktop portion still open under FR-7. |
| NFR-4 no runtime network/models/secrets/transcript/config changes | Met by bounded static review and process observations | Node built-ins and local native execution only; no network tracing or hostile environment instrumentation. |

Evidence is not human acceptance and no approval decision was fabricated. Nothing was committed, pushed or published by this reviewer.
