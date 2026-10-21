# ASCII slugifier delivery plan

Create a new deterministic Python CLI at `/private/var/folders/2r/5gvkx5wx0g37m4grvjjdt88m0000gn/T/delivery-full-cli-8frrftqa/product/slugify.py`.

Product-manager will draft the actual brief at `initiatives/slugify/brief.md` and exactly one executable story at `stories/slugify-cli.md`, using the supplied acceptance paragraph unchanged. ASCII slugifier means retaining only ASCII letters and digits, lowercasing retained uppercase letters, replacing each maximal run of other original characters with one hyphen and trimming edge hyphens. Unicode is a separator, with no transliteration.

This stage ends after the drafting handoff. No other role starts yet. Implementation and review remain future work; eventual local CLI verification must cover separator runs, Unicode, edge trimming, all-separator input, newline output and missing-argument exit status. Hosted CI is not present, and no implementation or tests have run in this stage.

The single advisory `is_fix` provider call returned `no` (OpenAI, advisory only). This is classification evidence, not authorization or human acceptance. Preserve any failures and use canonical Beads operations for later task tracking; this handoff creates no task or acceptance decision.
