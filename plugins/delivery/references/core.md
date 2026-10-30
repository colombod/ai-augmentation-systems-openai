# Core contract for every Delivery action

Read this and the selected skill's actual body. Catalogue metadata is not the
workflow. Load only resources needed for this action; reuse a resource only while
its exact text is still visible and its path plus content hash or immutable
package revision is established unchanged. Re-read after compaction, a source/
package change, missing context, or inability to verify the revision. A remembered
summary or an old filename is not a loaded rule. Keep the source/revision with
the current handoff; do not create a separate memory ledger for this purpose.

- Use actual host capabilities and permissions. A skill/role name does not launch
  an agent, connect a service or grant write, acceptance, merge or deploy authority.
  Missing access means unavailable/manual/unsaved, never simulated success.
- Read project instructions. Reuse the nearest existing ancestor `.delivery/`;
  select a nested component explicitly. Otherwise honor an AGENTS.md root override. In a
  multi-component project, resolve the component; never guess a sibling or shadow
  store. For initiative artifacts select the named initiative or the only existing
  one; otherwise clarify. Project-wide map queries need not create an initiative.
  Creating a new named initiative needs user authorization and no name collision.
  With no existing workspace/override and just one component, default to the
  repository root's `.delivery/`; without a repository use the explicit store.
- Keep one canonical store and stable IDs/history. Preserve existing artifacts,
  unfinished work, owner choices, evidence and failures. Resolve concurrent changes
  with expected revisions/hashes; never silently overwrite or resurrect a cut.
  Source uploads are snapshots. Without save access say prepared, not saved.
- Before progressing planning, inspect relevant open blocking findings against
  consumed artifacts. Resolve/reject with reasons or obtain the user's explicit
  decision to proceed. Read-only queries can report blockers without changing them.
- Cite current source/evidence. Distinguish code inspection, command output,
  model tests, actual host observations and outside-user use. Source presence is
  not deployed/shipped proof; stale or unmapped coverage is unknown, never safe.
  Re-read cited artifacts if their exact content/revision is no longer in context.
- Preserve the owner's stated intent and what must survive. Separate statements,
  proposals and unknowns. Ask only what changes the next decision. Neither model
  opinion nor an attributed JSON field authenticates human consent. Retirement
  proposals do not authorize deletion; preserve shared consumers and obtain a
  concrete human decision before separately authorized implementation.
- Greenfield and brownfield are equal paths. Existing code/routes need actual
  verification. With no code, keep features planned, code absent and future paths/
  commands explicitly proposed; do not block drafting on files yet to be created.
- Keep Job, First value, Fit, Outcome, Trust and Return separate from evidence
  strength; no total. Our source/tests/demo are not Seen outside-user use. Unknown
  Return does not justify retirement. Simulations remain labelled synthetic.
- Use existing domain terms; clarify ambiguity that affects the answer. A focused
  map query does not require creating/editing a glossary or writing planning docs.
  Load the language/writing conventions when authoring or revising those artifacts.
- Reviewer lenses are instructions, not automatic agents. Claim independence only
  for actually isolated reviewers. No model/provider fallback, approval-policy
  change, hook bypass or worker-lane expansion follows from a missing capability.

For full host boundaries read [runtime](runtime.md); for artifact authoring read
[conventions](conventions.md) and the selected templates. Those expanded rules
remain authoritative for their actions; this core does not override project or
user instructions. Do not load unrelated writing sections for a focused query.
