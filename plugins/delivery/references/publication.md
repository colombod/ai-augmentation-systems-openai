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

A clean consumer receives only the successful stdout of a trusted export command,
never the ledger, which also contains unreleased drafts. Export returns a full
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
enabled_tools = ["delivery_publication_submit", "delivery_publication_publish", "delivery_publication_receipt"]
```

Use the actual installed package path in this configuration. Codex starts the stdio
process on connection; you do not need to launch it manually. Restart/reconnect
uses the same existing ledger. Missing or corrupt state stays unavailable; never
add `--initialize`, `--control`, `--consume`, or `--handoff` to server arguments. Remove the
server configuration to opt out; retain the private ledger for reconciliation.

This explicit opt-in avoids starting an unconfigured service for every plugin
installation. Agent Plugins use package-root `mcp.json` for automatic registration,
but this package does not bundle one. `${PLUGIN_DATA}` is writable storage, not
a security boundary. Configuration enables tool discovery only; a trusted host
must separately deny candidate access to the ledger, control command and code.

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

A control commit error returns `unknown` and quarantines that connection. Reopen
only the original ledger. An uncertain approval may already authorize the exact
bundle; an uncertain rejection does not prove revocation. Do not automatically
repeat a review or renew its expiry. Any subsequent decision must be explicit
and bound to the current recipient snapshot. A publication receipt identifies a
completed release; it does not report an unreleased review's durable state.

The optional inherited `--control-fd` socket shares the candidate process and
event loop. If candidate stdout is not drained, that control socket can stall.
Use the separate `--control` invocation when trusted control availability must
be independent of candidate output.

To admit an export against an independently selected local recipient, supply its
complete expected binding (including generation) as JSON on stdin:

```sh
python3 /absolute/plugin/scripts/publication_service.py --db /private/bundles.sqlite --handoff example-operation < /private/expected-binding.json
```

The expected binding must match both the completed release and current registration
in one transaction. Every binding field and generation participates. Changed or
restored registrations refuse old releases; a new reviewed operation is required.
Malformed expectations, unknown or unreleased IDs, unavailable state and transaction
failure produce no bundle on stdout. Successful stdout is the canonical reviewed
envelope with unchanged file contents. No drafts, reviews or receipts are changed.
Select the expected recipient independently; copying the current registration is
not proof that it is the intended recipient. Labels do not authenticate remote accounts.

This checks local export admission. Registration may change after commit and before
stdout delivery. Review expiry governs initial release insertion; this command does
not renew review or grant fresh transmission authority. Any later transmission needs
its own current authorization and verification at the point of effect.

For historical recovery without a current-recipient check, use the existing command:

```sh
python3 /absolute/plugin/scripts/publication_service.py --db /private/bundles.sqlite --consume example-operation
```

Historical consume remains available after registration changes, and completed
receipts remain completed. It is trusted retrieval, not recipient verification.
Unknown or unreleased IDs produce no bundle. Envelopes contain at most 128 files; the aggregate byte limit still applies.
No files are truncated or split into separate releases automatically. Older
packages supporting fewer files may refuse these larger envelopes on retrieval;
retain the ledger and use a compatible package rather than reset history.
The ledger has a fixed capacity of 256 operation IDs and 64
registered destinations; it refuses additional entries when full. Wire frames are
at most 1 MiB; canonical envelopes are at most 1,015,808 bytes, reserving control
message overhead. SQLite uses the trusted host wall clock; rollback before review
issuance blocks, but this is not an independent secure-time source. Preserve the
ledger for recovery. Do not replace it to retry an uncertain operation. This
bounded local component does not provide automated archive rotation.


### Setup for a dedicated configuration home

On a POSIX host with Python 3.10+, the trusted operator can use
`scripts/publication_setup.py` instead of hand-editing the MCP configuration.
Paths must contain valid Unicode scalar values; undecodable filesystem byte paths
are refused. Permission-rule paths (worker, dedicated home, ledger parent and
installed code directory) must be absolute literal paths without `*`, `?`, `[`
or `]`; symbolic and home-relative spellings are not accepted. Setup reports
`unsupported-permission-path-syntax` without echoing the path. The glob-character
restriction does not apply to a ledger filename used only as a command argument. Supported path
characters are escaped without changing their values.
A busy setup lock is refused after a two-second acquisition deadline; the holder
keeps its lock and saved configuration and receipts remain unchanged.
It operates only on a dedicated home, not your default `~/.codex`. Keep the
planning receipt and destination binding private. The ledger must already be owner-only readable/writable,
initialized and registered through the trusted control interface above; setup
never initializes, resets, registers or approves a release.

Save the verified binding object from the trusted `binding` control response,
including its generation, in a private JSON file. Then plan the exact change:

```sh
python3 /absolute/plugin/scripts/publication_setup.py plan --home /private/dedicated-codex --ledger /private/bundles.sqlite --worker /absolute/workspace --binding /private/binding.json > /private/setup-plan.json
```

After reviewing that plan and authorizing the specific configuration change,
use its `sha256` value for each operation:

```sh
python3 /absolute/plugin/scripts/publication_setup.py enable --plan /private/setup-plan.json --expected-sha256 PLAN_SHA256
python3 /absolute/plugin/scripts/publication_setup.py status --plan /private/setup-plan.json --expected-sha256 PLAN_SHA256
python3 /absolute/plugin/scripts/publication_setup.py disable --plan /private/setup-plan.json --expected-sha256 PLAN_SHA256
```

Enable writes the managed receipt and configuration, starts no runtime and copies
no credentials. Select that home explicitly in your separately authorized local
Codex invocation. Repeated enable is idempotent; after interruption, use status
and the same exact plan. A failed mutation reports `reconcile_required: true`;
it does not promise that no configuration changed. Successful enable/disable
results report `durability: synced` only after syncing the validated receipt and
configuration files, home directory and parent directory, including matching-byte
retries. Sync failure requires reconciliation; retry completes these barriers.
Status reports `durability: not-checked`: it observes configuration without
certifying or completing those barriers. This is not a physical power-loss test. Disable changes this registration
for a fresh runtime start while preserving ledger, receipt and unrelated data.
It does not revoke an already-running MCP process; stop that runtime separately
before relying on the disabled configuration. Unknown existing configuration or
changed code, destination, ledger/worker/home identity, ancestor directories, receipt or configuration refuses
rather than overwriting or silently rebinding. Disable remains available after
ledger/code drift when the managed receipt and configuration are intact. If a
receipt-less home contains interrupted staging or other unknown files, setup
reports `fresh-home-plan-required`. Repeat the `plan` command with `--fresh-home`
and the same inputs to propose an unused sibling home, then review and use the
new plan and digest. This leaves the old home and every file untouched; nothing
is trusted or deleted based on a staging filename. An empty interrupted home
can also be replanned explicitly. Once a complete receipt exists, retry verifies
its recorded identity and bytes; unrelated staging leftovers remain preserved.
New-home capacity checks reserve bounded identity metadata before creating the
directory; oversized requests refuse without creating that home.
Source upgrades or destination changes need a new explicitly reviewed plan and
a new dedicated home. An existing receipt is immutable and cannot be rebound
by a new plan. Retain the old home and ledger; never delete data to force reuse.

Every result says `host_protected_ready: false`. The generated ordinary settings
reduce known capabilities but are not managed security policy and do not exclude
all host-injected tools or higher-priority configuration. A dedicated directory
and cooperative setup lock do not isolate malicious same-user host processes.
Actual protected actor use requires a separately established host boundary;
configuration success or three discovered tools does not establish it. Do not
use setup to change real settings without specific action-time consent.


### Prepare a committed subtree for review

With a trusted local Git executable and repository, `scripts/publication_prepare.py`
prepares an **unapproved** envelope. It does not submit, register, review, publish,
materialize files or modify the source. It reads committed objects, not working-tree
files; untracked files and later working changes do not alter a selected historical
commit. Tracked sensitive content remains included and requires independent review.
No source identity, manifest or hash establishes semantic safety or disclosure authority.

```sh
python3 /absolute/plugin/scripts/publication_prepare.py --repo /absolute/source < /private/request.json > /private/candidate.json
```

The request contains exactly `commit` (full lowercase commit ID), `source` (one
explicit repository-relative subtree), `prefix` (its output directory), `destination`,
`body`, `metadata`, and `extras`. Source and prefix must be canonical nonempty relative
paths, not `.` or traversal. Each explicit companion in `extras` has `name`, `content`
and `mode`; this can supply a local marketplace wrapper without including siblings.
An empty extras list is valid. No repository or subtree is selected by default.

Preparation includes the complete subtree, sorting output names. Git regular-file
modes become `0644` or `0755`; companion modes may also be `0600` or `0700`. These are
source modes, not a promise about a later installer's permissions. Generated mode
information is a JSON string in envelope metadata `modes`; that key is reserved and
cannot be supplied by the caller. No repository URL, absolute path or source revision
is automatically added to the envelope. Review every output field before release.

Strict UTF-8 preserves original content bytes, including CRLF. Symlinks, gitlinks,
unsupported modes/encodings, duplicate or file-parent paths, missing objects, mutable
refs and count/byte overflow refuse with empty stdout and a fixed error on stderr.
The existing 128-file and aggregate-byte limits include companions and mode metadata.
Git output and object reads are bounded; preparation uses a 30-second Git inspection
budget and disables lazy fetching and transports per process. It executes no source
filters or hooks. Trusted Git/repository metadata remain prerequisites; this is not
an untrusted-repository sandbox or a host-wide network policy.

The canonical candidate can be saved and separately reviewed through the existing
local-release workflow. Later source changes do not rewrite that saved artifact;
preparing another commit produces another candidate needing its own review. Use a
clean recipient and inspect its actual installed bytes/modes and useful behavior;
preparation itself supplies no installation or remote-publication guarantee.

Preparation requires an already existing local commit. It does not prevent that
commit or its history from being created or distributed. A private source snapshot
still requires separate review before any content crosses to a distributable
repository or artifact. Tracked sensitive content inside the selected subtree is
included, not classified or removed; reject that candidate before release.

## First distributable Git history

`scripts/publication_git.py` creates one reviewed, parentless Git bundle from
explicit UTF-8 files and commit metadata. It requires POSIX, Python 3.10+, a
trusted Git executable, and staging/output on one filesystem. It owns local artifact creation and
recovery; no prior source commit is required. It neither reads source history nor
publishes remotely. Existing local-release ledgers and their approvals are not
migrated or reused. Use a separate action ledger.

The application separates candidate data from trusted control. Protected use
requires trusted code, state and control access, and output ancestry protected
from untrusted movement or permission changes. The host coordinator described
below is cooperative: it cannot authenticate an independent reviewer against an
unrestricted same-user host. Review matching is not semantic classification or
recipient authentication. Other shell, connector, delegation and response routes
remain outside this action. Do not claim whole-host protection.

### Installed role and command sequence

Start from the installed product skill's bounded-change route. The builder
prepares the complete proposal in the authorized private store without creating
a distributable commit. Include every file, file mode, public commit field and
output destination. The authorized coordinator submits it, then dispatches the
same immutable proposal, independently selected destination binding and authorized
private review context to a separate native reviewer. If native delegation is
unavailable, name the missing independence; never invent a reviewer.

The reviewer returns a private object with exactly `schema_version: 1`,
`operation_id`, `proposal_sha256`, `destination_binding_sha256`, `decision`
(`approve` or `reject`) and `findings` (strings). Compute digests from canonical
JSON: sorted keys, compact separators and ASCII escaping, encoded as UTF-8.
The coordinator checks actual task provenance, both digests and the complete
returned decision against the dispatched proposal and independently selected
binding. A claimed reviewer name or candidate-provided approval is insufficient.
A missing, mismatched, ambiguous or rejected verdict stops publication.

The trusted coordinator records the matched decision through `--control`; the
builder and reviewer do not receive control authority from this workflow.
Keep proposals, review context, bindings and receipts private. For a correction,
submit a new immutable proposal/operation and review it independently. Never
change the contents of an existing operation. Unknown results require recovery
before any new attempt; a new ID is not a recovery mechanism.

The packaged commands are:

```sh
python3 "$PLUGIN/scripts/publication_git.py" --db "$PRIVATE_DB" --initialize
python3 "$PLUGIN/scripts/publication_git.py" --db "$PRIVATE_DB" --control < "$PRIVATE_CONTROL"
python3 "$PLUGIN/scripts/publication_git.py" --db "$PRIVATE_DB" < "$PRIVATE_REQUEST"
```

`PLUGIN` identifies the actual installed package. Use independently authorized
private absolute paths. Initialization refuses an existing ledger; never reset
state to make a retry work. Default mode accepts newline-delimited JSON data
requests synchronously. Control accepts a trusted JSON request. Neither starts
another model, installs a service or changes host permissions.

The owner supplies the intended outcome, not a sequence of file transfers or
account changes. The coordinator uses normal private structured-file tools and
these fixed commands; do not substitute a newly written transport or recovery
script. After a fresh session, recover the saved exact operation, proposal,
binding and receipts and resume through the installed commands.

### Proposal and control

Each data request has exactly `action` (`submit`, `publish` or `receipt`),
`operation_id` and `proposal`. A proposal has exactly:

- `schema_version: 1`, `operation: "git-root-bundle"`, `destination` and
  `output_name`, which must equal the operation ID followed by `.bundle`;
- `files`, each with `name`, UTF-8 `content` without NUL, and `mode` equal to
  `100644` or `100755`;
- `commit`, with `ref: "refs/heads/main"`, `message`, `author` and `committer`.
  Each identity has `name`, `email` and explicit `timestamp`.

All fields participate in review. There are no implicit identities, source
ancestors, signing, trailers, filters or copied Git configuration. Only a
parentless commit and its exact tree/blobs belong in the resulting bundle.

Trusted registration supplies `action: "register"`, `control_id`, `destination`,
`owner`, `audience`, `visibility`, `revision`, `authority_revision`,
`policy_revision` and `output_directory`. The action captures the existing
output directory identity as `directory_device` and `directory_inode`, and
assigns a `generation`. Include these in the complete binding and its digest.
A `binding` request has
`action` and `destination`; its returned binding must still be compared with
independently established recipient intent. Labels do not authenticate an account.

A review supplies `action: "review"`, `control_id`, `operation_id`, complete
`proposal`, complete `expected_binding`, `decision` and `ttl_seconds` greater
than zero and at most 300. `revoke` supplies `control_id`, `destination` and
`expected_generation`. `cancel` supplies `control_id`, `operation_id` and
`proposal_sha256`. Unknown fields and changed bindings refuse.

Every mutating control request has a unique ID. Mutation and its canonical
request digest/result are committed together. Same ID and digest returns the
original result without repeating a mutation, extending expiry or changing the
review sequence. Different content with that ID conflicts.

After a lost or uncertain control response, query through `--control` with
`action: "control-receipt"`, `control_id` and `request_sha256`. `recorded` returns
the original result; `not-found` permits resubmission of the identical request
and ID. `unknown` does not. Never automatically issue a new review to recover a
lost response. Historical review sequence/expiry describes the original control
operation, not current authorization. Publication still checks current authority.

### Refusal and recovery

Data statuses distinguish `submitted`, `busy`, `blocked`, `needs-review`,
`completed`, `unknown`, `conflict` and `cancelled`. Completed receipts identify
proposal/bundle digests, root/tree object IDs, output basename and binding
generation. They do not include private content or absolute paths.

One persistent global lock serializes data and control. A busy result means the
operation was not applied, not that cancellation or revocation succeeded. Never
remove a lock file to resolve contention. Before another effect, startup checks
durable unfinished intents; their original directory identities are fenced,
including aliases. The action never resolves uncertainty by changing IDs,
replacing output or moving a registration.

Preparation finishes and closes writers before recording durable intent in its
own transaction. Intent is evidence, not authority. Fresh exact review and
binding are checked at live admission. An uninterrupted admitted operation may
complete after review TTL; this is not expiry checked at the filesystem instant.
The action creates one bundle by a relative atomic no-replace hard link through
a verified directory descriptor, then confirms durability and records outcome.
Read-only staging and closed handles constrain the application, not the file's
owner or privileged host. Cleanup failure never permits another publication.

An exact existing artifact can be reconciled as completed. Confirmed absence in
the original verified directory requires a new review sequence before retry;
it is not proof that no historical exposure occurred. Changed/unobservable
destination or mismatched artifact remains unknown/conflict. Reservations and
private history are retained. Query `receipt` with the same full operation and
proposal; recovery never publishes on its own.

A 30-second monotonic budget limits preparation and effect dispatch. Lock waits
are bounded to one second and the remaining budget. Observed termination or
expired deadline before dispatch stops the effect. After the effect may have
occurred, an error or interruption is completed/unknown, not a false no-effect
receipt. The budget cannot guarantee the duration of an entered filesystem call.
Synchronous input cannot instantly observe a lost caller or a queued cancellation;
a disconnect is not a cancellation acknowledgement. No detached worker retries.

### Limits and useful verification

Frames are at most 1,048,576 bytes; canonical proposal and aggregate content are
at most 1,015,808 bytes. Accept 1–128 files and a generated bundle no larger than
4,194,304 bytes. Refuse overflow without truncation. IDs use lowercase ASCII
letters, digits and hyphens, begin with a letter and are at most 64 characters.
Paths are canonical relative POSIX names, 1–256 UTF-8 bytes and at most 32
components. Reject traversal, `.git`, control characters, backslashes, trailing
spaces/dots, case-fold collisions and file/parent collisions. Binary files,
symlinks and gitlinks are not supported.

Messages are 1–16,384 UTF-8 bytes without NUL; names are 1–256 bytes without
controls, angle brackets or edge whitespace. Email fields are 3–254 printable
ASCII bytes with one `@` and nonempty sides, no whitespace or angle brackets.
Timestamps are canonical decimal seconds from 0 through 4102444799, followed
by a space and `±HHMM`: hours 00–14, minutes 00–59, hour 14 permits only 00;
`-0000` is refused. These are bounded Git fields, not general email validation.

Acceptance needs a real delivered change: independently reject a mixed proposal,
separately review its safe correction, inspect every object and metadata field,
clone/install into a clean recipient and use the newly delivered behavior.
Exercise greenfield without a source commit and brownfield without copying
private ancestry, plus fresh-session receipt/recovery. Tests alone do not prove
the host boundary or customer adoption. On the next genuine product change,
reuse this installed route and record what that use establishes; do not invent
a second feature to satisfy a release checklist.
