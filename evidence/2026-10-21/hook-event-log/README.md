# Hook Event Log preview validation

2026-10-21. New independent package: `plugins/hook-event-log`, version `0.1.0-preview.1`. User scope: local Codex desktop hook, SDK language entry point, Rust logic, event types only. Delivery's start/brief/architecture/sprint/sprint-review workflow was applied from the local package. Source skills were read directly; no installed qualified skill activation or persistent delivery team is claimed. Rust and transport implementations were delegated separately and independently reviewed.

## Implemented and observed

TypeScript transports opaque bounded input to a packaged executable backed by the Rust library. Rust owns JSON parsing, event validation, session routing and disk append. Records contain exactly `event_type`. Session identifiers are hashed into filenames; no raw identifiers, payloads, paths or timestamps are logged. Success is quiet; failures produce a fixed diagnostic and exit 1, never an approval decision. No runtime model call, MCP or network.

| Check | Observed result | Evidence |
|---|---|---|
| Actual host build | macOS arm64 compiled TypeScript + native release | `build.log` |
| Rust tests | 7 passed | `rust-tests.log` and independent review |
| Packaged integration tests | 11 passed, including 32 concurrent callbacks | `adapter-tests.log` and independent review |
| Independent direct boundary probes | 31 passed, with prior 27-check report retained | `independent-review/review.md` and probe results |
| Native isolated install | Installed preview.1, 12 hooks enabled/untrusted, no warnings/errors | `isolated-install-final.json` |
| Installed copy direct invocation | Correct one-key log, quiet success | `isolated-install-final.json`; direct call, not native event firing |
| Trust preservation | No hook bypass; untrusted thread startup generated no event logs | Same receipt |
| Marketplace validation | 2 plugins valid | Independent review and root direct Python invocation |
| Existing Delivery regressions | 121 Python and 22 Node tests pass | `delivery-regression-ready-env.log`, `judge-regression-unsandboxed.log` |
| Desktop UI/native callback | Unable to check; access explicitly refused | `desktop-access.json` |

The existing Delivery plugin files were not edited for this feature. Its isolated installation helper now filters its temporary catalogue to the one package it copies, preserving isolation when the marketplace has more than one entry. New build/test CI jobs are defined for macOS and Linux; hosted CI has not run. Windows logging is explicitly unimplemented.

## Failed observations retained

The first portable manifest installed but yielded zero discovered hooks (`isolated-install-initial-no-hooks.json`, `isolated-install-portable-diagnostic.json`). Keeping both portable and compatibility manifests also yielded zero (`isolated-install-compatibility-diagnostic.json`). Legacy-only discovery returned all twelve (`isolated-install-legacy-only-diagnostic.json`); the product now uses only `.codex-plugin/plugin.json`. The maintained install probe can reproduce temporary alternative layouts with `--manifest-mode portable|both` without modifying the product.

The Rust implementer reported an initial 32-process test failure from transient `openat` ENOENT; this observation is a delegated report rather than a retained raw transcript. Bounded retry of ENOENT/EINTR against the pinned directory corrected it. Fresh core and independent packaged concurrency runs passed. Rustfmt was absent; no formatter execution is claimed.

Default npm and Python package registries failed DNS; approved public-registry dependency retrieval succeeded. The first root Python validation lacked jsonschema, and a later offline resolver could not locate cached metadata. A ready isolated interpreter then passed validation and all 121 tests. The first judge regression run failed because the sandbox prohibited its loopback listener; the authorized loopback rerun passed all 22 tests. Original failed logs remain alongside successful reruns. Independent review preserves its own environment failures.

## Acceptance boundary

Implementation and direct installed-command behavior are verified. Actual trusted CLI hook firing, the host-supplied PLUGIN_DATA during a callback, and trusted desktop session behavior are not verified. FR-7 remains unmet/unable to check. No desktop-ready, complete auditing, universal binary, hosted CI, real-model, or publication claim follows from these checks. Nothing was committed, pushed, published or installed into the user's personal Codex configuration. Source manifests and working binaries are local; build before installing from a future checkout.

Canonical planning lives in `maintainer/hook-event-log/.delivery/`. Beads `oap-15v` remains the durable parent, with desktop acceptance tracked separately. Maintainer evidence and planning are outside the installable package.

Delivery's prose counter measured the brief at 262 words (cap900), architecture at513 (cap1600), scope package at236 (cap900), and sprint review at273 (cap1000). `package-sha256.json` identifies the current local package, including the built adapter and native artifact, without build caches.
