# Delivery conventions

The [common contract](core.md) owns workspace resolution, preservation, evidence,
authority and source reuse. This file owns artifact language and writing rules.
Read the sections relevant to authoring; glossary curation applies when creating/
editing it, not to an unrelated map query. Referenced constraints remain active.

## Where `.delivery/` resolves to

Use the [common workspace rules](core.md#where-delivery-resolves-to).

## Which initiative

Use the [common initiative rules](core.md#which-initiative). The product map is
project-wide; do not create/select an initiative merely to query it.

## Open blocking findings

Apply the [common blocking-findings rule](core.md#open-blocking-findings).

## Language

Read `.delivery/glossary.md` first and use its terms exactly. If it does not exist, create
it as *Keeping the glossary* below says — or, for a small effort, collect terms as you go and
propose the file at the end. Do not coin synonyms for concepts it already names.

Any term you need that is missing gets **proposed explicitly**, with a definition in the
business's vocabulary and a concrete referent. Any term carrying two meanings gets raised as
a defect, not resolved silently.

**Questions go out in the vocabulary of whoever must answer them**, with a worked example in
their world. A question for the business owner written in engineering terms is a blocker
with a name on it, not a question. If a question is really an engineering call, decide it
here rather than routing it to them.

### Keeping the glossary

`.delivery/glossary.md`, one agreed term per concept, written from
`../templates/glossary.md` (budget: 500 words target, 900 hard cap). It is
project-wide and every skill reads it; any skill that coins or meets a new term adds it.
Every document is written by someone fluent in a different dialect — the analyst's *booking
window* is the architect's *date range* and the owner's *price list* — and the damage shows
at the edges: questions the owner cannot answer, requirements that drift into two concepts,
and a hand-off the runner has to guess at.

1. **Curate, never regenerate.** If the file exists, edit it. Terms are stable: changing a
   definition means saying what it was, what it is now, and which documents were written
   under the old meaning.
2. **Harvest the terms actually in use** — the originator's own words first (they outrank
   everything), then the brief, PRD, personas, architecture, and real identifiers in code
   and data.
3. **Resolve collisions.** Synonyms (several words, one concept): pick one, list the rest as
   *aliases, not to be used*, with the document each came from. Homonyms (one word, several
   concepts): split them and rename at least one.
4. **Let the business word win.** Where domain and code disagree, the domain term is the
   entry and the code identifier is recorded as its implementation name. Do not rename code
   as a side effect.
5. **Define in the owner's words**, plain sentence first, precise one after if needed, and
   **ground each term** in a worked example, a file path or a value from the data.
6. **A term nobody can define crisply** is an unresolved product decision wearing a noun:
   list it as an open question for the originator, never invent a definition.
7. **Sweep for completeness.** Every domain noun in the existing artifacts appears in the
   glossary or is deliberately excluded, and no synonym is left without one canonical term.

**Report what changed** when you hand off: new terms, resolved synonyms, and any term that could
not be defined. Those are product decisions, and they belong to the originator.

During `$delivery:status`, manually compare the active artifacts with the glossary; the inventory helper does not extract domain terms.

## Writing, then revising

The skill states the budget: a word target and a hard cap (both exclude code, YAML and data tables).

**Compose first. Do not try to hit the budget while writing.** Restraint during
composition trades substance for brevity in the wrong order — the findings get thinner
while the scaffolding survives. Write what the artifact needs, then cut what it does not.

**Then measure, do not estimate.** The budget counts **prose only**. Data tables, code
blocks and YAML are excluded, so measure with them stripped:

With local execution, use the helper below. On another surface, use available
computation tools with the same exclusions. If none are available, preserve the
substance and state **word count unverified**; an exact-count exit criterion
remains unverified. Do not invent a count or require a new server for counting.

```sh
python3 <resolved-plugin-root>/scripts/project.py words <artifact-path>
```

The helper strips HTML comments, initial YAML frontmatter, fenced code and
pipe-prefixed table rows before counting prose. Use pipe-prefixed data tables.
Inline code remains prose; this is a Markdown budget convention, not a full parser.

A plain `wc -w` counts the tables and will overstate the total, often by several times.
Measuring the wrong number leads to cutting the wrong thing.

**Rows in a data table can never help you meet the budget, because they are not counted.**
Deleting them is pure loss for zero benefit. The term table, the requirement table, the
findings table, the friction map — these *are* the artifact. If a revision pass is removing
rows, it has misunderstood the rule and should stop.

**If the count exceeds the hard cap, you are not finished.** Make a revision pass over the file and
delete, in this order, until it fits:

1. Preamble, recap, and any sentence describing what the document is about to say
2. **Restatement** — the same fact as prose *and* a table row *and* a summary bullet. Keep the form that carries it best; delete the others. This is almost always the biggest win.
3. Process narration — "I examined X and found Y" becomes Y
4. Hedging — either you know it, or it is labelled an assumption. Both are shorter.
5. Citations past the first for a given claim
6. Examples past the first, unless the next one shows a *different* failure mode

Then re-measure with the same command and confirm.

**Never delete** any row of a data table, findings and their failure scenarios, one citation per claim, grounding
and confidence labels, synthetic-output warnings, open questions, or IDs a later phase
reads. If the artifact cannot fit without losing those, keep them, exceed the cap, and
**write the final count and the reason into the document**. A declared overrun is a
judgement. A silent one is a habit.
