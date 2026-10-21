# Maintainer CLI cycle driver repair

The repaired runner is outside the installable plugin. It writes each execution
into a new attempts/UTC-UUID directory, retaining its source, helper source and
production resource hashes. The executed runner-initial.py, initial failed
result.json and successful continuation evidence remain unchanged. The separate
runner-before-driver-repair.py preserves the intermediate maintainer source.

Twelve bounded tests pass without starting Codex or calling any model. They
exercise queued work still waiting behind an idle persistent role, wrong and
failed native terminals, wrong-thread completion, quoted/replayed queue markers,
missing actual peer handoff, scoped downstream tool evidence, first-call judge
skip/error/domain validation, attempt isolation and real subprocess exit/shutdown
semantics. Pre-exited supervisors and forced shutdown cannot be relabeled normal
stops or successful scenarios.

Completion requires the exact queued message's native userMessage and matching
persistent thread/turn completed terminal; each downstream controlled tool result
is restricted to that proof. The is_fix fixture uses candidate/linked_item/context
validated against the shipped catalogue, and a configured judge must return one
actual selected OpenAI advisory answer on its first call. Tool success with skipped
or error classification fails. An absent configured key is explicitly labelled
unavailable rather than model/provider success.

Fresh runs require all semantic checks, no unplanned operator messages or
lifecycle controls, and no native escape/request events. Unexpected pending human
questions fail with actual request IDs rather than selecting answers or waiting
indefinitely. The expected final capture refusal is matched exactly. False checks,
missing evidence, process cleanup failures and unexpected supervisor exit produce
nonzero process status. The planned PM supervisor restart remains part of the
scenario; no corrective steering/revocation/continuation is built into it.

No real model run was launched while implementing these repairs. Fresh real CLI
acceptance belongs to the parent task and must retain the actual human boundary.
