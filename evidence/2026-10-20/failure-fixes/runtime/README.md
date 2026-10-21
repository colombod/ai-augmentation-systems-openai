# Immediate native escalation denial

The coordinator already forbids worker sandbox expansion. It now rejects new native command/file approval requests immediately, rather than presenting an impossible approval or leaving it pending for five minutes.

For a bound active native turn, the response is `{"decision":"decline"}` when the advertised choices allow decline or choices are unspecified. If decline is absent but cancel is offered, the response is `{"decision":"cancel"}`. If neither deny option is offered, the coordinator returns a protocol error; it never chooses an approval, session grant or policy amendment. Cancellation may interrupt the native turn and require explicit reconciliation; acknowledgement is not completion and no work is automatically replayed.

These requests create no pending operator record, terminal prompt, capture challenge or signing call, even when an operator capture authority exists. The event is explicitly labelled coordinator policy with `human_authority:false`. Existing stale/unbound checks and early-request turn binding run before the denial. Actual `item/tool/requestUserInput` questions and protected delivery acceptance remain on their existing capture paths. Old pending records still cannot approve worker escapes.

## Evidence

- `unit-tests.txt`: **41 runtime/protocol tests pass**, including authority on/off, offered-decision selection, stale/unbound/replayed requests, early requests, zero pending/capture and retained real question handling.
- `native-response-schema-validation.json`: decline and cancel response shapes validated for command/file methods against locally generated Codex CLI 0.159.3 schemas.
- `native-denial-result.json`: **actual model and public CLI** prepare/send/serve negative probe. It requests one forbidden escalation without a human terminal. The offered safe response is cancel; native execution is cancelled and the turn ends interrupted. The guard remains `PRESERVE`, pending operator records remain zero and no capture/signing/operator request event appears. All six checks pass. This is a deliberately failing command request, not a successful delivery or autonomous recovery claim.

The negative fixture used real Git/Beads initialization and public roster preparation. No role/task database seeding, credentials/configuration copying, sandbox expansion or hook/trust changes were used. There was no parent Git add/commit shortcut for worker execution. Native cancellation/reconciliation behavior is preserved. The normal delivery scenario is tested separately by the parent task.
