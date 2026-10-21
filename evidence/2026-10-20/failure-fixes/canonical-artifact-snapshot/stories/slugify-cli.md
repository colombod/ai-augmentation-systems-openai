# Convert one text argument to an ASCII slug with slugify.py

As a developer using a terminal, I want `python3 slugify.py TEXT` to produce a predictable ASCII slug so I can reuse the result in scripts. The intended file is `slugify.py` in the product root `/private/var/folders/2r/5gvkx5wx0g37m4grvjjdt88m0000gn/T/delivery-full-cli-8frrftqa/product`. Unicode outside ASCII acts as a separator, with no transliteration.

## Acceptance criteria

Given exactly one text argument, python3 slugify.py TEXT treats each maximal run of original characters outside ASCII [A-Za-z0-9] as one hyphen, lowercases retained ASCII A-Z, trims edge hyphens and prints one newline with exit 0; all-separator input prints an empty line, and missing TEXT exits 2.
