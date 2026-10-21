---
name: status
description: Read a delivery workspace and report planning progress, unresolved findings and missing evidence. Use to understand the current initiative or next planning step; inventory is not runtime verification.
---

# Delivery planning status

Read [host capability guidance](../../references/runtime.md) and
[delivery conventions](../../references/conventions.md). Resolve the project and
initiative; never choose among several by modification time.

With a local workspace, shell and Python, run the read-only inventory:

```sh
python3 <plugin-root>/scripts/project.py status --project <project-directory>
```

Without those capabilities, read the selected initiative's available documents
through existing file/connection tools. Label the result manual and state the
snapshot revision or retrieval time. If no artifacts are accessible, report
status unavailable and request the source documents; never infer current state
from conversation recollection. Do not install a service to inspect a supplied plan.

If no workspace exists, report that and suggest the start skill; do not create
one during status. Read the actual artifacts for the selected initiative, shared
persona/glossary records, and its story, review and sprint files. File existence
alone does not establish completion.

Report:

- Current framing, latest completed planning phase and missing prerequisites.
- Stories by their recorded status, with `ready` labeled manually planning-ready.
- Open blocking/significant findings, their target and resolution owner.
- Persona grounding mix from frontmatter; identify missing or malformed fields.
- Terms or definitions conflicting with the glossary, based on actual reads.
- Evidence actually available and checks still unavailable, separated by surface.

Preserve findings and failed evidence. Do not infer live role status, invocation
counts, authenticated decisions, measured usage or deployed acceptance: this
preview has no observer or team runtime. Lead with any blocker, then the next
useful phase and why. Status is read-only.
