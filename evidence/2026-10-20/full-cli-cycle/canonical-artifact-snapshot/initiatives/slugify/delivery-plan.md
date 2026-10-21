# Slugify delivery plan

Deliver a deterministic ASCII-only Python CLI at `slugify.py` in product root `/private/var/folders/2r/5gvkx5wx0g37m4grvjjdt88m0000gn/T/delivery-full-cli-3b8pu1g_/product`.

The CLI lowercases ASCII letters, replaces maximal runs outside ASCII alphanumerics with one hyphen, trims edge hyphens and prints a newline. Unicode outside ASCII is a separator, not transliteration. All-separator input produces an empty line; missing TEXT exits 2.

Product-manager is assigned to save the actual canonical brief at `initiatives/slugify/brief.md` and exactly one executable story at `stories/slugify-cli.md`, preserving the operator's exact acceptance paragraph. This coordinator stage ends after that handoff. No other role starts at this stage; implementation and review remain future work.

Future validation should observe actual CLI output and exit codes for ordinary text, separator runs, edge separators, Unicode, all-separator input and missing TEXT. No tests have been run; hosted CI is not present. Preserve any subsequent failures as evidence.

The requested `is_fix` judge call returned advisory mode with `human_authority=false`, skipped for `state_incomplete`: missing `candidate`, `linked_item` and `context`; supplied `task` was dropped. Its policy status was unavailable and blocking eligibility false. This result is advisory only and grants no authorization or human acceptance.
