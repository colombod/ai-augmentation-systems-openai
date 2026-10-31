# Local publication component

`scripts/publication.py` provides a Python contract for a trusted host. It has no
network transport, CLI, model provider or credentials. It is a local prototype,
not protection for the surrounding host or an enabled publication integration.

Construct `Publisher` in trusted host code with a `routes` registry and `verify`, `authorize`, `classify`
and `send` callbacks. Candidate callers use `prepare(bytes, operation, destination_id)`
and `dispatch(ticket, bytes, operation, destination_id)`. Treat the complete output
as the candidate, including accompanying messages and metadata. Only exact bytes
are accepted; there is no truncation, encoding conversion or implicit safe suffix.
The default maximum is 1 MiB and the default ticket lifetime is 30 seconds.
`routes` is a frozenset of at most 64 fixed `(operation, destination_id)` pairs,
using lowercase ASCII identifiers. Unknown pairs are rejected before verification;
candidate identifiers cannot become resolver URLs or outbound request parameters.
The host owns the registry and must not populate it from candidate text. At most
64 pending tickets are retained; expired entries are retired on the next prepare.

`verify` supplies a coherent
`Destination(identity, owner, audience, visibility, revision, authority_revision, policy_revision)`.
Visibility alone is insufficient. Both authority and content-policy callbacks must
return the boolean `True`; false, malformed results and exceptions block. The host
must distinguish scoped permission to send from permission for the content itself.
Authority and policy checks evaluate that bound snapshot. Every permission or
policy change must advance its revision; revision values cannot be reused.
Safe usage documentation, implementation facts, fixes and support replies may be
allowed by that policy. Candidate text cannot confer its own authorization.

Dispatch rechecks the destination, permission, policy and finite lifetime. Changed
bytes, operation, owner, audience, visibility or any revision require a fresh ticket.
Tickets cannot be serialized or transferred between instances. Each attempt
consumes its ticket. Sink success must return exactly `True`; exceptions and other
results produce `unknown`, quarantine the instance and prevent automatic retry.
Receipts contain only a fixed status, not content or callback errors.

The sink must atomically compare the complete binding, including authority and
policy revisions, with current state at the point of effect. Destination-only CAS
does not prevent revoked authority or policy from racing a send. The atomic check
and effect belong to one trusted transaction. A separate lookup followed by an unconditional send cannot satisfy
this contract. No remote adapter is supplied or qualified. Only trusted callbacks
may access the underlying send capability. Python object privacy is not a sandbox:
hostile code in the process can bypass this component. A blocked callback may stall
the instance; this component has no callback cancellation or availability guarantee.

Shell, Git, HTTP, connectors, uploads and delegated execution remain outside this
module. A host with those independent send capabilities is not protected by loading
it. Hooks, role names and this document do not remove those capabilities. There is
no durable ticket/receipt store, restart reconciliation, general semantic classifier,
remote publication, user installation or whole-host acceptance demonstrated here.
Ticket expiry is checked at dispatch admission, not atomically by a real external
transport. This component does not establish expiry at an external effect; such a
transport remains unqualified until its actual guarantees are demonstrated.


## Reviewed local handoff bundles

`scripts/publication_service.py` is an opt-in stdio MCP handler for the
`local-release` operation. It writes a reviewed bundle to a local SQLite ledger.
A trusted consumer can retrieve a completed bundle for a clean recipient. It
makes no network requests and does not publish to a repository or install a plugin.
It does not start another model session or use the native-role coordinator.

The candidate tools are `delivery_publication_submit`,
`delivery_publication_publish` and `delivery_publication_receipt`. Each takes an
`operation_id` and the same complete `envelope`: `operation: "local-release"`,
`destination`, `body`, `files` (each with `name` and `content`) and `metadata`
(string keys and values). Identifiers use lowercase ASCII letters, digits and
hyphens, beginning with a letter, at most 64 characters. All file names, file
contents and metadata are part of review. Nothing is implicitly appended to the
released envelope. A changed envelope needs a new operation and review.

The trusted operator owns destination registration and review. Review must cover
content meaning, all accompanying metadata and the exact destination binding;
mechanical matching cannot decide whether a paraphrase discloses protected
information. There is no model-callable approval tool. A missing, rejected,
expired or stale review blocks release. Review decisions and unreleased drafts
remain in the private ledger; MCP results contain fixed statuses only.

The local transaction checks the stored review, destination, audience, authority
and policy generation and its expiry predicate when inserting the release. The
release row is both effect and durable receipt. Repeating the same ID and exact
envelope returns its existing result after restart; a different envelope cannot
reuse that ID. This guarantee concerns the local SQLite operation only. It is not
a claim that a remote GET followed by a send is atomic. A missing or corrupt ledger
is unavailable, never automatically replaced. Keep recovery copies private.

A clean consumer receives only the stdout of the trusted `--consume` command,
never the ledger, which also contains unreleased drafts. Consume returns a full
reviewed JSON envelope and does not interpret file names as filesystem paths.
Any later remote transmission is a separate operation requiring its own authority
and verification. Retrying an unknown result must use the original ID/envelope.

The application boundary separates candidate requests from trusted control. It
is not an OS sandbox. A caller with arbitrary shell access to the ledger or
control command can bypass it. The host must separately protect handler code,
state and control access and remove independent outbound routes before claiming
exclusive mediation. Current broad-tool hosts do not meet that requirement merely
by loading this handler. The service is not enabled by the package manifest.

### Local setup and use

Use an operator-owned private directory for the ledger. From a trusted terminal,
initialize it once (the command refuses an existing file):

```sh
python3 /absolute/plugin/scripts/publication_service.py --db /private/bundles.sqlite --initialize < /dev/null
```

On a supported local Codex host, configure the top-level MCP server with the
existing ledger. This is an opt-in configuration example, not an installed setting:

```toml
[mcp_servers.delivery_publication]
command = "python3"
args = ["/absolute/plugin/scripts/publication_service.py", "--db", "/private/bundles.sqlite"]
```

The stdio server is a Python tool process, not another Codex session. Follow the
host's [MCP configuration guidance](https://learn.chatgpt.com/docs/extend/mcp).
Cloud ChatGPT MCP connections require their supported remote registration flow;
this local script is not a registered remote endpoint.

The trusted operator uses the separate control command:

```sh
python3 /absolute/plugin/scripts/publication_service.py --db /private/bundles.sqlite --control < /private/control.json
```

A `register` request contains `action: "register"`, `destination`, `owner`,
`audience`, `visibility` (`public` or `private`), `revision`, `authority_revision`
and `policy_revision`. Registration returns the complete binding and its server
controlled `generation`. An `action: "binding"` request with `destination` reads
that binding on the trusted channel. These labels describe the local recipient;
they do not verify a remote account. Every changed registration advances generation,
including changing a value back. Only a trusted operator may supply the registry.

After candidate submission, the reviewer prepares a private control request with
`action: "review"`, the exact `operation_id` and `envelope`, `expected_binding`
(including generation), `decision: "approve"` or `"reject"`, and `ttl_seconds`
greater than zero and at most 300. A mismatched binding refuses the review.
Publish then inserts only the approved exact bundle. Query receipt after a lost
response instead of inventing another operation ID. Review is an explicit trusted
decision, not a classification service or a candidate-provided boolean.

To obtain the released bundle for a recipient:

```sh
python3 /absolute/plugin/scripts/publication_service.py --db /private/bundles.sqlite --consume example-operation
```

Only this command's successful stdout is the handoff. Unknown or unreleased IDs
produce no bundle. The ledger has a fixed capacity of 256 operation IDs and 64
registered destinations; it refuses additional entries when full. Wire frames are
at most 1 MiB; canonical envelopes are at most 1,015,808 bytes, reserving control
message overhead. SQLite uses the trusted host wall clock; rollback before review
issuance blocks, but this is not an independent secure-time source. Preserve the
ledger for recovery. Do not replace it to retry an uncertain operation. This
bounded local component does not provide automated archive rotation.
