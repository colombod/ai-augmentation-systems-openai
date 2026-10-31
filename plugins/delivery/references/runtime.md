# Delivery on Codex and ChatGPT

Apply the [common contract](core.md) for capabilities, workspace/persistence,
evidence, authority, independent-review limits and source loading/reuse.

The planning workflow uses packaged skills, templates, reviewer lenses and actual
host tools. It needs no Delivery server or MCP connection. The separately
configured [local team runtime](team-runtime.md) adds durable native roles,
controlled artifact/Beads operations and explicit operator acceptance, without
merge, push or deploy authority. A planning skill does not start that runtime.

## Resource and host access

Codex CLI, desktop, ChatGPT Chat and ChatGPT Work can expose different tools.
Resolve resources from the selected loaded skill: from `skills/<phase>/SKILL.md`,
`../..` is the package root when represented as files. Otherwise use the host's
resource reader. An unreadable path is unavailable, not permission to invent it.
References to “the user's request” mean actual conversation context, not an
argument variable. Use the host's skill picker; Codex examples use
`$delivery:brief`, while ChatGPT may expose `@` selection.

In document-backed workflows, local phase paths are logical artifact names; they
do not imply filesystem access. Use existing authorized document operations with
one canonical store and the same IDs, namespaces and history. When saving is
unavailable, return a complete export with intended filename, source revision and
changes, labelled **prepared, not saved to the canonical store**. An answer is not
a repository update; old uploads cannot establish a remote project's live state.

The Python helper is optional: run it only with actual shell/Python and workspace
access. Otherwise inspect supplied artifacts manually and label limitations.
Measure prose through available computation; without it report word count
unverified. Never infer that a command ran. See conventions for budget details.

## Review and configured providers

Read the selected lens in `references/reviewers/`; apply the common review/evidence
rules, keep independent reviewers unaware of each other's findings, and name
unavailable observations in the test handoff.

No hooks or judge provider are enabled by loading a skill. The local runtime/judge
needs explicit setup and a real credentialed path on the claimed surface. Judge
selection is disabled/Jev/OpenAI; missing access never silently changes provider
or assigns that classification to host-model intuition. Ordinary host planning
can proceed without a separate judge. Neither model classification nor a phase
check authenticates human authority or enforces a release gate.
