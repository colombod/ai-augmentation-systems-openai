# Optional external supervision boundary

This is a local, in-process host adapter seam, tested with fake native transport.
It does not install a dot integration or authenticate a ChatGPT account. There
is no new agent tool, public endpoint, socket, service or implicit event subscription.
Default native operation stays unchanged when the roster has no `supervision`.

The intended dot role owns goals, priorities, delegation requests, status synthesis
and escalation. Delivery owns the canonical record, execution and review gates;
Beads owns task/dependency state. Human acceptance stays in the operator terminal.
Neither conversation memory nor an agent's claim is the ledger.

## Trusted setup and handover

An operator may add this optional field to the existing team roster:

```json
{
  "supervision": {
    "principal": "my-dot",
    "environment": "my-planning-environment",
    "tasks": {"project-123": "checkout-redesign"}
  }
}
```

The task-to-initiative allowlist is operator configuration, not model-supplied
authorization. Only the bound native `coordinator` receives these assignments.
Stop `serve`, reconcile previous work, then run the normal `prepare --roster`.
Prepare takes the same exclusive workspace lock as serve. A new binding requires
all roles idle/prepared and all jobs terminal or cancelled. Restart serve so
existing native threads resume with the supervision instructions. The native
coordinator remains the one dispatcher and executor/fallback; silence never
starts another supervisor. The serve lock prevents a second native supervisor.
Bindings get unique generations; fallback and reconfiguration revoke old bridges.

A trusted embedding host must authenticate its caller and bind its canonical
environment before constructing `supervision.Bridge(store,
authenticated_principal=..., environment=...)`. These arguments are assertions
by trusted host code, not authentication performed by this package. Never expose
the constructor or local operator CLI as model-selectable tools. Code with
coordinator Python/file access is already inside the trusted local boundary.
An untrusted remote caller cannot safely use this seam until a supported host
adapter authenticates and scopes requests. No credentials are stored here.

Use the bridge on the coordinator's serialized owning event loop; its SQLite
connection is not a cross-thread transport. The host owns callbacks/polling and
must explicitly retrieve receipts; cloud task callbacks do not subscribe to
SQLite or Beads events.

## Admission and receipts

`snapshot(task)` returns the project/environment, configured initiative, current
runtime revision and canonical task seal. A request to `submit` contains exactly:

```json
{
  "request_id": "stable-caller-request-123",
  "task": "project-123",
  "initiative": "checkout-redesign",
  "recipient": "coordinator",
  "message": "Carry out the agreed bounded assignment and report evidence.",
  "expected_revision": "VALUE_FROM_SNAPSHOT",
  "task_revision": "VALUE_FROM_SNAPSHOT"
}
```

Keep the original complete request for retry after a lost response. The same key
and payload returns the original durable assignment; a changed payload under the
same key is rejected. Keys cannot cross binding generations. Unknown recipients,
out-of-scope tasks/initiatives, changed canonical criteria/dependencies and stale
runtime revisions are refused. Canonical state is rechecked before dispatch;
changed work becomes blocked, not automatically resubmitted. New admission after
an uncertain assignment is refused. External user-run Beads/Git writes remain
outside coordinator atomicity, as in the native runtime.

The native input includes authoritative request/task/initiative scope and labels
the source `agent:<configured-principal>`, never `operator`. Receipt lookup returns
assignment ID, queue state, role phase, bound native thread/turn and terminal event
and evidence event references, scoped to this binding. `idle` means the native
turn completed; it does not mean the task was accepted. Evidence references are
local ledger IDs, not published cross-host URLs. The host must retrieve/verify
the referenced canonical records before using them elsewhere; file absence or
transfer failure must remain visible. The package claims no cross-cloud publisher.

Duplicate admission never repeats dispatch. Started/uncertain work is not retried
on disconnect or restart. Recovery uses exact native IDs and terminal evidence.
If turn/start timed out without returning a turn ID, even a previous terminal
turn cannot prove assignment completion: its outcome stays `unknown`, with no
terminal receipt. There is no automatic force-clear for that uncertainty.

## Explicit return to native supervision

With serve stopped, cancel only undispatched queued/blocked requests:

```sh
python3 <package>/scripts/runtime.py --project <planning> supervision-cancel --request REQUEST_ID --reason "Discard stale undispatched request"
python3 <package>/scripts/runtime.py --project <planning> supervision-native --reason "Operator returns supervision to native after reconciliation"
```

Fallback refuses outstanding or uncertain work. Reconciled known failures stay
failures. Restart serve to refresh native instructions. Existing requests/history
remain durable; changing the roster does not silently replace a supervisor.
The bridge cannot accept tasks, forge operator receipts, self-review, change
approval policy, widen lanes, merge, push or deploy. Existing native identity and
human acceptance checks remain authoritative.

The next host proof needs a supported authenticated dot-to-local execution path,
a configured project/environment and an existing native Codex/Beads runtime.
Use a synthetic task, test a lost admission reply and disconnect, then fetch an
actual native completion receipt. Until that succeeds, describe this as an
adapter seam with offline tests, not supported dot integration.
