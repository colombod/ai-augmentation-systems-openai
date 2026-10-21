# Convert a text argument to an ASCII slug with slugify.py

As a terminal script author, I want to run `python3 slugify.py TEXT` and capture a deterministic ASCII slug so that my scripts use consistent text labels. Deliver the CLI in the specified product root. Unicode outside ASCII is a separator, not transliteration.

## Acceptance criteria

Given exactly one text argument, python3 slugify.py TEXT lowercases ASCII A-Z, converts each maximal run of characters outside ASCII [A-Za-z0-9] to one hyphen, trims edge hyphens and prints one newline with exit 0; all-separator input prints an empty line, and missing TEXT exits 2.
