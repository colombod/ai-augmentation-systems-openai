---
name: start
description: Initialize a delivery planning workspace and initiative without overwriting existing artifacts. Use to begin a planning effort; this preview does not start a shipping team.
---

# Start delivery planning

Read [host capability guidance](../../references/runtime.md) and
[delivery conventions](../../references/conventions.md).

When the user requests a persistent delivery team or the full shipping workflow,
read [local team runtime setup](../../references/team-runtime.md). Do not silently
substitute planning initialization for that request. Resolve the actual roster,
planning project, product worktrees, available models and execution capabilities.
Only report role startup from actual coordinator status and native session
results. Explicitly report any unimplemented protected workflow requirement; a
queue entry or a role name is not an operating shipping team.

Resolve the project/component and initiative from the user's request and existing
artifacts. Reuse the existing delivery root; honor project instructions specifying
another root by selecting that root's parent as the helper's project. For a
multi-component repository, resolve the component before initializing. Do not
guess a new initiative when several exist. A requested new named initiative is
authorization to create it; ask only for missing choices.

When a local workspace, shell and Python are actually available, run the helper
with the resolved package path:

```sh
python3 <plugin-root>/scripts/project.py init --project <project-directory> --initiative <kebab-case-slug>
```

It creates directories only, preserves all artifacts and reuses an ancestor
workspace. A nested workspace, symlink or conflicting file is reported as an
error; report it and resolve the path rather than working around the refusal.
The helper does not inspect project instructions or decide product boundaries;
those choices belong to this skill.

Without local execution, establish the project/initiative and canonical artifact
store from accessible documents and the user's request. Do not run or simulate
the helper. Return the chosen artifact namespace and persistence method; if no
write tool exists, explain that subsequent documents will be prepared for export.
Do not claim directories or remote records were created. Existing uploads are
snapshots, not live workspaces. Start can establish a workflow without creating
empty folders on a machine it cannot access.

Report the artifact store, initiative, and any actual directories created or
records saved; otherwise explicitly report planning context only. This starts
planning, with no persistent team, hooks or decision-provider calls. Continue
with `$delivery:brief` for a new framing, or the requested phase when its inputs
exist. Do not create generic placeholder briefs or change project configuration.
