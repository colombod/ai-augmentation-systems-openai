# Upstream alignment for maintainers

The installable product is each `plugins/<name>/` directory. Port assessments,
implementation reviews, validation evidence and this maintainer guide stay in
the repository outside that boundary. Archive the plugin directory, not this
marketplace's root. Package instructions must work without these documents.

Keep the original Claude marketplace unchanged. Delivery's packaged README,
CHANGELOG, NOTICE and `upstream.json` retain the source project, imported version
and baseline revision. The per-file SHA-256 values describe the **original
upstream content**, not the adapted OpenAI files. They establish lineage; they
are not proof that either runtime has equivalent behavior.

When reviewing new Claude features, compare upstream against the recorded
baseline and source-file map. Assess the intent, tests and host assumptions
before choosing what to adopt. Preserve Codex/ChatGPT adaptations rather than
overwriting local changes wholesale. Record adopted, adapted and deliberately
omitted behavior in the plugin changelog, with the relevant upstream commits.

Update source hashes/revisions only for material actually imported. If imports
span several commits, record a `source_revision` per affected file instead of
implying that all files came from one newer revision. Keep the original baseline
and historical release records. A commit merely inspected is not an adopted
baseline. Record actionable alignment work in Beads, not a Markdown task list.

Validate the resulting portable package and its actual supported behaviors.
Source comparison, CLI discovery, live model behavior and desktop/ChatGPT
acceptance remain distinct evidence. Independent releases and explicit provenance
let the two marketplaces evolve without silently changing the Claude plugin.
