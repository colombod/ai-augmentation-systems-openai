---
id: new-plugin-idea-01
status: draft
requirements: [FR-1]
---
# Illustrative first outcome
Owner ask: specific business ask not supplied; this scenario is proposed, not an owner quote.
Goal: a maintainer sees a local change explanation before proceeding.
Files: src/change_check.py and tests/test_change_check.py — proposed new, create.
No product repository or implementation exists; do not report these paths verified.
Acceptance: given the maintainer's proposed change, the local CLI explains it without outbound calls (FR-1).
Run with: proposed `python3 -B -m unittest discover -s tests` after setup; not executed, not yet available.
Execution prerequisite: establish repository, files and test runner; this story remains draft.
Out of scope: agents, graph service and automatic product edits.
