# Implementation handoff

The sprint skill writes a scoped package; it does not start a runner.

For `generic`, make the package self-contained: requested outcome, story/FR IDs,
real paths, interfaces, dependencies, design tokens, exact test commands and
expected results, exclusions, budget estimate and stop condition. Require a
report mapping changes and actual evidence to every criterion, plus deviations,
failed checks and unresolved items. Do not imply estimates are measured usage.

For `codex`, prepare a prompt and artifact paths for an implementation session
on the actual project in Codex CLI or desktop. Include the intended working
directory, source revision, allowed scope, test commands, expected report and
stop conditions. Verify paths only when the current tools can access them;
otherwise mark them unverified and make checking them a handoff prerequisite.
Do not assume a plugin exposes a thread-creation tool or invoke a particular
app-server endpoint from prose. If an authorized native handoff tool is actually
available, use its current contract. Otherwise return the package and prompt
for the user to open in Codex. Preparing a handoff does not start execution.

Save handoff documents under the canonical store's logical `.delivery/sprints/`
location, with the initiative prefix. If no write tool is available, return the
complete package as an export and report that it is not saved. Existing files
and historical evidence remain in place.
Report the package path, coverage, unresolved inputs and what the human or an
authorized implementation session should run next. Execution, commit, merge
and deployment remain separate actions governed by project permissions.
