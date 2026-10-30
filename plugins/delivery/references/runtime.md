# Delivery on Codex and ChatGPT

The planning workflow uses packaged skills, templates, reviewer lenses and tools
the current host actually exposes. It requires no delivery server or MCP
connection. Loading a planning skill alone does not launch persistent roles or
provide execution authority. The separately configured [local team runtime](team-runtime.md)
adds durable native roles, controlled artifact/Beads operations and explicit
operator acceptance. It does not merge, push or deploy. Project instructions and
permissions apply; an invoked skill does not grant unrelated authority.

## Establish available capabilities

Before each phase, identify the actual accessible project/artifacts, read and
write tools, shell/Python availability, search tools and authorized delegation.
Use available capabilities; do not assume them from a product name. Codex CLI,
Codex desktop, ChatGPT Chat and ChatGPT Work can expose different tools. Loading
a plugin cannot supply missing local filesystem access or install a service.

Resolve resources from the skill that the host loaded. From
`skills/<phase>/SKILL.md`, `../..` is this package's root when represented as files.
Use the host's resource reader when resources are exposed another way. A path
the host cannot open is unavailable, not permission to invent its contents.
Read the full selected skill, then its action-relevant references and named inputs;
catalogue metadata alone is not the workflow. The [core contract](core.md) governs
focused queries. Shared text already exactly visible may be reused only with an
established unchanged path/revision or content hash. If that cannot be checked,
read it again. After compaction, source/package changes or lost context, reload
the selected skill and needed references/artifacts. References to "the user's request" mean actual conversation
context, not a literal argument variable. Use the host's skill picker; Codex
invocation examples use `$delivery:brief`, while ChatGPT can expose `@` selection.

## Artifacts and persistence

Choose one canonical artifact store for the initiative. In a local Codex project,
use its existing `.delivery/` and native file tools. With connected documents,
use only existing authorized read/write operations and preserve the same IDs,
initiative namespaces and history. Local file paths in phases are logical
artifact names in a document-backed workflow; they do not imply local access.

If the user provides uploaded files, treat them as identified snapshots. When
direct persistence is unavailable, return a complete document/export with its
intended filename, source revision and changes; say **prepared, not saved to the
canonical store**. A Markdown answer must not be reported as a repository update.
Do not silently establish a second canonical store. Missing source artifacts or
access keep their prerequisites unsatisfied; obtain the inputs instead of
fabricating current state. Status cannot infer a remote project's live state
from an old upload.

The Python helper is optional. Run it only with an actual shell, Python and
access to the selected workspace. Without those capabilities, inspect available
artifacts directly and label the result manual. For prose budgets, use an
available computation tool; if exact counting is unavailable, report the count
unverified instead of inventing a number. Never claim a command was run when
its result was inferred. Do not install an MCP server to make a planning phase
work.

## Review and coordination

Names such as `product-owner` identify documents in
`references/reviewers/<name>.md`, not registered tools or automatically running
team members. Read the applicable lens. Use native delegation only when exposed
and authorized by the project/session. Give reviewers the raw inputs and
read-only assignments without each other's findings; coordinate the result.

If delegation is unavailable or prohibited, use sequential passes labeled
**single-session review**. Do not call their agreement independent convergence.
Parallel-review steps and exit criteria are conditional on actual capability;
name missing independence in the handoff. A required independent release review
remains incomplete. Simulated personas always remain synthetic. Persistent
coordination uses the explicitly configured local runtime; assigning a role name
in a prompt alone does not create its durable native session.

## Evidence and authority

Separate source inspection, stub checks, real commands, real-model results and
UI observations. GUI claims need an inspected capture; CLI claims need actual
output and exit code; TUI layout needs a visual terminal capture. A sandbox test
does not establish behavior on an inaccessible customer host. Missing execution
or capture access means unable to check; prepare an explicit Codex/test handoff.

Planning `ready` is a manual assessment, not an enforced gate. Cite actual
decisions/evidence; do not invent `dec-`/`ev-` records, live role status or
authenticated consent. No plugin hooks or judge provider are enabled merely by loading a skill. The
[local runtime and judge commands](team-runtime.md) require explicit setup and a
real credentialed execution path on that surface. Judge selection is explicitly
disabled/Jev/OpenAI. Missing provider access never silently changes provider
or delegates the selected classification to host-model intuition. The host
model can still do ordinary planning without a separate judge. Neither model
classification nor a procedural phase check grants execution authority.
