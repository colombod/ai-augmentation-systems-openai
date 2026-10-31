# ADR-001: TypeScript transport and Rust logging

Status: selected for implementation, 2026-10-21.

The user requires the Codex SDK language and Rust logic. Use TypeScript to transport the hook input to a small executable backed by a reusable Rust library. Rust exclusively owns parsing, validation, routing and disk writes. No model SDK call is needed.

Alternatives: Python does not match the requested language; direct N-API bindings add Node ABI packaging; pure Rust omits the requested SDK-language entry point. Revisit the executable bridge only if measured launch time misses the hook bound. Platform-specific binaries and Node remain explicit dependencies.
