<!--
The assumption register (R-14): every claim the design rests on that nobody has yet seen hold, one row
each. $delivery:architecture writes it from its spike list; $delivery:challenge and $delivery:realign
read it. This preview edits the register as a planning artifact, preserving prior
status and cited evidence. It has no assumption CLI, lane enforcement or claim gates.
An external host is observed only through an actual probe in that host; reading
documentation or using a twin does not establish its real behavior.
-->

# Assumptions: <initiative>

**Kinds.** `external-host` (how a host we do not control behaves: what the ChatGPT app passes a tool,
how many tools it shows, what a manifest accepts), `platform` (our runtime, framework or store),
`data` (the shape or volume of real data), `customer` (what the customer will do or want),
`internal` (a design choice we can settle locally).

**Criteria.** `<story id>#<criterion number>`, space separated; a bare story id means every criterion.
A story depending on an untested external-host assumption remains planning-blocked
until its spike has an actual real-host result and the decision owner acknowledges
it. A refuted assumption requires redesign and renewed readiness review of affected
stories. These are review requirements, not automatically enforced holds.

**Decision owner.** `DM`, `PM`, or `owner` when the answer decides scope.

## Register

| Id | Statement | Kind | Criteria | Status | Evidence | Decision owner |
| :-- | :-- | :-- | :-- | :-- | :-- | :-- |
