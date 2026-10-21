---
name: simulate
description: "Put end-user personas in front of the product before building it, in one of two modes. --interview runs non-leading simulated interviews to surface unmet needs and objections (writes .delivery/interviews/). --journey (the default) walks personas step by step through a journey \u2014 an existing product, a specified or proposed flow, or a live site \u2014 to find where they get stuck or leave, producing a friction map and per-step value data for MVP staging (writes .delivery/simulations/). Use after personas exist. Output is labelled synthetic \u2014 hypotheses to test, never research findings."
---

# Persona simulation: interviews and journeys

Arguments: **the user's request**

Optional depth in DEFINE, between `$delivery:personas` and `$delivery:prd`. Pick the mode from the arguments:

| Mode | Use when | Inputs | Output |
| :-- | :-- | :-- | :-- |
| `--interview` | You need the problem, needs and objections in the personas' own terms. Topic defaults to the feature in the brief. | `.delivery/personas/`, `.delivery/initiatives/<initiative>/brief.md` | `.delivery/interviews/` |
| `--journey` (default) | You need to know where a flow loses people, and which steps an MVP stage must contain. Journey defaults to the primary scenario in the brief or PRD. | `.delivery/personas/`, plus the PRD, the running product, or the codebase | `.delivery/simulations/` |

With no mode given, run `--journey`; if no journey can be described yet (no PRD, no product, no proposed flow in the brief), run `--interview` and say so. Both modes may run in one session, interview first.

## Conventions

Read [host capability guidance](../../references/runtime.md) and
[delivery conventions](../../references/conventions.md) before running this phase.

## The rule this skill exists under

Everything produced here is **synthetic**. A simulated persona's answer is a prediction generated from a persona file, not something a user said. It is worth what the persona's grounding is worth and no more. Simulated friction is a **hypothesis about where real friction lives**, not a usability finding: good at generating candidates cheaply, bad at telling you which are real.

Every artifact this skill writes carries that label at the top, and you repeat it when reporting. If simulated output ever gets cited as "users told us", or a simulated abandonment rate becomes a number in a business case, the plugin has done harm rather than good — so be pedantic about this even when it is tedious.

What it is genuinely good at: catching the step nobody thought about, the assumed knowledge, the missing state, and the objection nobody wanted to hear.

## Gate check

Read `.delivery/personas/`.

- **Missing** — stop, run `$delivery:personas` first. Interviewing or walking a persona you invent on the spot to answer a question you are holding is a machine for confirming what you already believe.
- Note each persona's grounding grade; it determines how the output should be read, and you will report it.

For `--journey`, also establish what is being walked through, in this order of preference:

1. **A real running product** — use actual accessible code/pages/copy. Browser or
   desktop interaction requires the host's real tools and existing authorization;
   no Reality Checker process is presumed. Without that access, use a supplied
   capture or the specified/proposed flow below and state its limits.
2. **A specified flow** — the scenarios in `.delivery/initiatives/<initiative>/prd.md`.
3. **A proposed flow** — described in the brief.

Say which you used. A simulation against intent rather than implementation finds different problems, and the reader needs to know which they are getting.

---

## Mode `--interview`

### Run

**1. Write the interview guide first, before talking to anyone.** Questions must be non-leading. "Would this feature be useful?" invites a yes; "walk me through the last time you had this problem — what did you do?" produces information. Ask about past behavior rather than future intent, since predicted intent is close to worthless even from real people.

Cover: the problem in their own words, what they do today and what it costs them, what they have tried and abandoned, what would have to be true for them to switch, and what would make them stop using it.

Do not describe your solution until the end. Once you do, the persona starts responding to your framing instead of their situation.

**2. Interview each persona with the `persona-simulator` lens.** With available,
authorized native delegation, use isolated reviewers with the full persona file
and guide, keeping their answers separate. Otherwise simulate each persona
sequentially in this session and label that mode prominently. Do not claim
independent agreement from sequential personas; all results remain synthetic.

**3. Probe the objections rather than resolving them.** When a persona raises a concern, follow it — how much does that matter, what would it take to overcome, what would you do instead. The instinct is to argue back or design a fix mid-interview. Don't. The objection is the finding.

Follow-up questions must also be non-leading: ask what information is missing,
what would have to change, or what the persona would do next. Do not offer an
explanation, discount, earlier disclosure or other candidate fix and ask whether
it would overcome the concern. That tests agreement with your suggestion rather
than eliciting the persona's objection. If the snapshot cannot support an answer,
record it as unknown instead of supplying a hypothetical history.

**4. Interview the skeptic properly.** The persona who is served badly gets the same care as the enthusiast, not a token pass. That transcript is usually the most useful one.

### Synthesize

Do not just concatenate transcripts.

- **Needs across personas** — cite the persona IDs and grounding grades. Call
  agreement independently convergent only for isolated runs; sequential overlap
  is explicitly single-session and still a hypothesis.
- **Divergent needs** — where personas want incompatible things. These are the real product decisions; surface them for the Product Owner rather than splitting the difference yourself.
- **Objections**, ranked by how many personas hold them and how fatal each is.
- **Unmet needs** nobody had planned for.
- **Confidence** per finding: derived from `observed` persona attributes, or extrapolated from `assumed` ones.
- **What this cannot tell you** — the questions that genuinely need real people, added to the research backlog.

### Write

Every interview file opens with this banner, verbatim — reproduced here because the
template may not be readable:

```markdown
> ⚠ **SIMULATED PERSONA OUTPUT — a hypothesis to test, not a research finding.**
> Generated from `.delivery/personas/<slug>.md`, grounding: **<grade>**.
> Nothing here is something a real user said. Do not cite as "users told us".
```

Write per-persona transcripts to `.delivery/interviews/<persona-slug>-<topic>.md` and the synthesis to `.delivery/interviews/README.md`, using `../../templates/interview.md`. The synthetic-output label goes at the top of every file.

### Exit criteria

- Within the budget, or the overrun declared in the document with its reason — measure prose when computation is available; otherwise report word count unverified
- Interview guide written before the interviews, questions non-leading
- Every persona interviewed; actual isolated or single-session mode stated, with no independent-convergence claim for sequential passes
- Synthesis separates convergent from divergent, with confidence tied to grounding
- The research backlog names what simulation cannot settle

**Budget: 500 words target, 800 hard cap** (excludes code, YAML and data tables). Compose, measure and revise as *Writing, then revising* in the conventions says.

---

## Mode `--journey`

### Run

**1. Break the journey into concrete steps.** Every step a real person takes, including the ones teams forget: arriving from search with the wrong expectation, the language or currency being wrong, the loading state, the empty state, the error, the moment of deciding whether to trust the site, the point of entering personal data, and what happens after they act.

**2. Walk each persona through using the `persona-simulator` lens.** Use isolated
native reviewers only when available and authorized. Otherwise run sequential
passes in this session, label them single-session simulation, and do not claim
independence or independent convergence.

Each persona carries its own constraints through every step: device, connection, language, time available, budget, expertise, and whether someone else must approve. Most friction comes from constraints, not preferences.

At each step the persona reports: what they understood, what they expected next, what they actually noticed, how they felt, and whether they would continue. **Abandonment gets recorded at the exact step**, with what they would do instead.

**3. Simulate the unhappy paths too**, not just the intended route. Arriving mid-journey from a deep link. Making a mistake and needing to correct it. Coming back two days later. Being interrupted. These are where products lose people.

### Build the friction map

Aggregate into a step-by-step map:

| Step | Personas reaching it | Friction | Abandoned here | Severity |
| :-- | :-- | :-- | :-- | :-- |

**Severity** = how many personas hit it × whether it blocks or merely annoys. Rank the map by it.

Then, and this is the output that feeds MVP staging, produce **per-step value data**:

- **Which steps are load-bearing** — remove them and the journey fails for someone. These are MVP candidates.
- **Which steps are enhancements** — their absence causes annoyance, not abandonment. These are staging candidates.
- **Which personas are fully served** by the current step set, and which are not served at all. A stage that serves nobody end to end is not a stage, and this is how you detect that.

### Write

Every simulation file opens with this banner, verbatim — it is reproduced here because
the template may not be readable:

```markdown
> ⚠ **SIMULATED OUTPUT — hypotheses about where friction lives, not usability findings.**
> Personas walked: <list, with grounding grades>. Nobody was observed.
> Never turn a simulated abandonment count into a number in a business case.
```

Write to `.delivery/simulations/<journey-slug>.md` using `../../templates/simulation.md`, with the synthetic label at the top. Note which basis you walked — real product, specified flow, or proposed flow.

### Exit criteria

- Within the budget, or the overrun declared in the document with its reason — measure prose when computation is available; otherwise report word count unverified
- Journey broken into concrete steps including empty, error and return states
- Every persona walked; actual isolated or single-session mode stated, with no independent-convergence claim for sequential passes
- Abandonment recorded at specific steps with the alternative they would choose
- Friction map ranked by severity
- Load-bearing versus enhancement steps separated, and per-persona end-to-end coverage stated
- Basis of the simulation stated

**Budget: 900 words target, 1500 hard cap** (excludes code, YAML and data tables). Compose, measure and revise as *Writing, then revising* in the conventions says.

---

## Hand off

Report with the synthetic label attached.

- **`--interview`**: lead with the divergences and the fatal objections — the comfortable findings are not what this mode is for. Next: `$delivery:simulate --journey` to walk personas through the actual journey.
- **`--journey`**: report the ranked friction map and the load-bearing step set. Flag any persona that cannot complete the journey at all — that is either a scope decision or a segment you are choosing not to serve, and it should be a choice rather than an accident. Next: `$delivery:prd` — it writes the scenarios if they are not yet written, and its MVP-staging step reads the friction map directly.
