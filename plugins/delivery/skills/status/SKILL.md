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

If `.delivery/product-map.json` exists, read the
[shared product contract](../../references/product.md) and inspect its `status`
and `handoff` through the authorized local helper, or read it manually. Report
planned vs preview/shipped claims, commit/raw-byte freshness, mapped evidence,
unknown coverage, unconfirmed owner choices and the six separate usefulness
judgements. A greenfield record needs no code repository and has no code-freshness
verdict. Do not upgrade source availability or our own walkthrough into deployment
or outside-user evidence.

Report:

- Current framing, latest completed planning phase and missing prerequisites.
- Stories by their recorded status, with `ready` labeled manually planning-ready.
- Open blocking/significant findings, their target and resolution owner.
- Persona grounding mix from frontmatter; identify missing or malformed fields.
- Terms or definitions conflicting with the glossary, based on actual reads.
- Evidence actually available and checks still unavailable, separated by surface.

Preserve findings and failed evidence. Planning inventory does not establish live
role status, invocation counts, authenticated decisions, measured usage or deployed
acceptance. When the selected project has an authorized local runtime, read its
actual status separately using `runtime.py --project <project-directory> status`
and [runtime guidance](../../references/team-runtime.md). Report its observed
bindings, pending requests and stale/unknown states with retrieval time. If the
runtime is unavailable, say so; do not infer its state from planning files.
Desktop and ChatGPT workflow acceptance remain pending. Lead with any blocker,
then the next useful phase and why. Status is read-only.
