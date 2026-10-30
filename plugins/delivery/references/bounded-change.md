# Bounded change through shipping

Use this route for one small product/feature outcome in either a greenfield or
brownfield project. It replaces full-pipeline document prerequisites, not evidence,
review or authority gates. Use the full PRD/architecture/roadmap route when scope,
interfaces, risk or unresolved decisions cannot fit a self-contained story. If
uncertain, explain the missing decision and keep the story draft.

## Onboard and choose

Read existing owner statements, product map, plans, findings and available backlog.
Use `inspect` and source/evidence where available; an agent curates capabilities,
not the census. Distinguish observed capabilities, planned gaps and deferred gaps.
For each material gap record a stable ID, affected customer/feature, evidence or
unknown, disposition, reason, owner and next check/action in the existing initiative
roadmap/backlog. If neither exists (including fresh greenfield), embed this gap
table in the bounded story/sprint; no roadmap or new tracker is required. Use planned feature IDs in the product record for missing
capabilities; keep defects/debt linked to those IDs in the existing backlog rather
than inventing capabilities. Deferred means a reason and revisit trigger, not
forgotten. Do not create a second tracking system or imply inaccessible tickets
were reconciled. Preserve IDs and source/owner attribution.

Choose the next useful outcome from owner goals and evidence. State alternatives,
why this slice wins now, explicit cuts and decisions still proposed. An assistant
may recommend and perform already-authorized work; it must not fabricate owner
confirmation. No numerical priority formula or autonomous selection is required.

## One complete story and wave

Record `route: bounded-change` in the story and sprint. Reuse prior artifacts;
list full-pipeline documents as present or absent without manufacturing them.
The story itself must carry:

- customer goal and actual owner intent versus proposed choices;
- feature/gap IDs, current versus desired behavior, alternatives, scope and cuts;
- falsifiable acceptance criteria, one evidence probe per criterion and surface;
- current source/map revision, verified existing or proposed paths, interfaces,
  pre-edit impact/shared consumers and uncertainty (or why unavailable);
- local design/risk decision, dependencies/setup, test commands with verified or
  proposed status, stop conditions, rollback and permitted actions.

Check open blocking findings. A finding this change is explicitly repairing needs
its criterion and independent recheck before acceptance; unrelated open blockers
remain blockers. Apply ordinary story readiness and sprint report-back rules.
A roadmap/PRD/architecture is not mandatory on this route: the embedded scope and
design decisions substitute. Missing essential decisions still block readiness.
Implement with an authorized runner, independently review exact source and actual
outputs, then realign the story, existing backlog/product state and learning.
Never relabel a source test as deployed or outside-user evidence.

## Authorized shipping handoff

After sprint review, choose repair, another wave, or shipping this accepted unit.
An ordinary authorized host agent follows these steps; protected runtime actors
receive no new write, push, merge, approval or deployment permissions.

1. Record target repository/base, source scope, release surface and actual user
   authorization separately for push/normal PR, merge, release/deploy and device
   installation. Obtain any missing permission for the concrete reviewed payload.
   If tools/access are absent, return a prepared/unsent handoff and exact blocker.
2. Preserve concurrent work; check current remote/base and existing PR/branch
   state before writing. Align version, catalogue convention, changelog, licence
   and provenance. Open one normal PR when authorized, without duplicating an
   uncertain outcome. Record URL and exact head. Do not change repo visibility.
3. Require independent code **and product-workflow** review plus relevant CI on
   that exact head. Name untested host surfaces and partial acceptance. Fix real
   blockers, retain failure evidence and renew review/CI after changes. Never
   substitute a formal approval by the implementing agent or weaken checks.
4. Merge only with explicit applicable authorization and passing required gates,
   using the expected head to reject races. Verify merge receipt and remote main.
   Publication/merge do not imply installation or deployment; do those only when
   separately authorized, recording their actual surface/revision and outcome.
5. Through the authorized host save path, refresh canonical source/map freshness,
   feature state, gap disposition and release evidence. Preserve prior bytes and
   proposed owner choices. Branch-only stays branch-only until verified merged;
   source-shipped is distinct from installed, deployed and customer-observed.
   Report what the customer can now do, what remains unknown, and the next real-use
   or return check. A failed or partial shipment remains explicitly incomplete.
