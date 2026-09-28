# Learner-State Scaffolding Tutor

A Socratic tutoring system in which a hidden, mathematically-grounded model of
what a student understands mechanically constrains what a second, student-facing
agent is permitted to say.

## Framing, stated precisely

This project is inspired by Theory of Mind — the idea of modeling another
mind's internal state — but it does not implement ToM in the full
cognitive-science sense (no recursive belief modeling, no reasoning about what
the student believes the tutor believes). The more accurate and more
interesting description is a **monitor-constrained dual-agent system**: a
non-conversational "Modeler" agent maintains a structured belief state about
the learner, a deterministic mathematical layer updates that state, and a
mechanical, non-LLM verifier gates a conversational "Interlocutor" agent's
output against it. The central research question this project actually tests
is:

> *Can a monitor agent's output be used to constrain a separate generation
> agent's behavior reliably, and what happens — concretely, empirically —
> when the constraint mechanism is incomplete or the monitor itself is wrong?*

Every design decision below, and every result in the evaluation section, is
in service of answering that question with evidence rather than assertion.

---

## Architecture

For every learner turn, the system executes a strictly **sequential**
pipeline — not parallel agents, despite surface appearances:

```
Student message
      │
      ▼
Agent A ("Modeler", Gemini Flash, structured output)
  → classifies observed_outcome: correct / partially_correct / incorrect
  → diagnoses current_misconceptions (concept + description)
  → estimates frustration_level
  → proposes a scaffolding strategy for Agent B
      │
      ▼
Deterministic Bayesian Knowledge Tracing update (pure Python, no LLM)
  → updates per-concept mastery probability
  → derives mastered_concepts / locked_concepts via a
    prerequisite-graph-aware effective-mastery calculation
      │
      ▼
Agent B ("Interlocutor", Gemini Flash)
  → drafts a Socratic reply constrained by the current locked-concept list
  → forbidden from stating final answers or affirming incorrect substance
      │
      ▼
Mechanical Verifier (pure Python, no LLM)
  → lexical check against locked-concept terms and known aliases
  → regenerates (max 2 retries) on violation, or falls back to a safe
    templated question
      │
      ▼
Reply shown to student; full state snapshot persisted to SQLite
```

### Why sequential, not parallel

Agent B's system prompt is built from Agent A's output for that same turn —
there is a hard data dependency, so true parallelism is not possible. This is
a correction from an earlier version of the plan that assumed independence.

### Concept graph and structural prerequisite enforcement

Ten linear-algebra concepts are stored as a static, hand-authored DAG (e.g.
`slope_intercept_form` depends on both `slope` and `y_intercept`). Critically,
a concept's **effective mastery** — the number actually used to decide what's
locked — is not its own raw BKT probability, but the minimum of its own
probability and the effective mastery of every prerequisite, computed
recursively:

```python
def get_effective_mastery(concept, mastery_map, concept_graph):
    own = mastery_map[concept]
    prereqs = concept_graph[concept]["prereqs"]
    if not prereqs:
        return own
    return min(own, min(get_effective_mastery(p, mastery_map, concept_graph)
                         for p in prereqs))
```

This was added after manual testing surfaced a real bug (documented below):
without it, a composite concept could accumulate high mastery independently
of its prerequisites, defeating the entire premise of a prerequisite-aware
tutor.

### Bayesian Knowledge Tracing with soft evidence

Rather than binary mastered/unmastered flags, mastery is a probability updated
via the standard BKT formula (Corbett & Anderson, 1995), extended to handle
Agent A's three-way outcome classification via a soft-evidence blend between
the "correct" and "incorrect" posteriors, weighted by a `partial_weight`
parameter for `partially_correct` outcomes:

```python
def update_mastery(p_l_prev, observed_outcome, p_slip=0.1, p_guess=0.2,
                    p_transit=0.3, partial_weight=0.5):
    num_correct = p_l_prev * (1 - p_slip)
    p_given_correct = num_correct / (num_correct + (1 - p_l_prev) * p_guess)
    num_incorrect = p_l_prev * p_slip
    p_given_incorrect = num_incorrect / (num_incorrect + (1 - p_l_prev) * (1 - p_guess))
    credit = {"correct": 1.0, "partially_correct": partial_weight, "incorrect": 0.0}[observed_outcome]
    p_l_given_o = credit * p_given_correct + (1 - credit) * p_given_incorrect
    return p_l_given_o + (1 - p_l_given_o) * p_transit
```

All BKT math was hand-verified against live logged output during development
(e.g., a prior of 0.15 with an incorrect outcome was independently confirmed
to produce 0.3151, matching the system's logged value to four decimal places).

### Three tiers of enforcement — stated explicitly, not conflated

A central lesson of this project is that not all constraints carry the same
strength of guarantee:

| Mechanism | What it guarantees | Strength |
|---|---|---|
| Effective-mastery graph capping | A composite concept's lock status can never be bypassed by its own probability alone — mathematically enforced | **Structural guarantee** |
| Lexical verifier + alias matching | Specific known vocabulary and equation forms cannot reach the student | **Mechanical, but heuristic** — covers known surface forms only |
| Prompt instructions (e.g. "don't confirm a value," "don't affirm wrong answers") | Best-effort behavioral shaping | **Weakest — no mechanical enforcement, can be overridden by conflicting instructions** |

The evaluation section below provides concrete evidence at each tier.

---

## Evaluation methodology

A 30-turn offline benchmark was run against the live `/chat` pipeline (not
mocked) using three adversarial simulated-student personas, each run for 10
turns via a second Gemini Flash instance:

- **Persistent Misconceiver** — holds and defends a specific false belief
  (slope confused with the constant term).
- **Answer-Fisher** — uses escalating urgency, flattery, and repeated direct
  demands to extract the final answer.
- **Passive Guesser** — gives minimal-effort, unreasoned responses.

Two metrics were computed automatically from logs; a third was evaluated by
manual human review rather than an automated scorer, deliberately — grading
"did the tutor cave" reliably needs human judgment, and pretending otherwise
would overstate the rigor of the evaluation.

## Results

**Constraint leakage rate (delivered to student): 0.00% across 30 turns.**
No locked vocabulary or known equation alias reached the student in any final
reply.

**This number is more informative than it first appears — a defense-in-depth
finding.** In one intervention (Persistent Misconceiver, turn 10), Agent A's
own `suggested_scaffolding_strategy` instructed Agent B to *"introduce the
formal term 'y-intercept,"* despite `y_intercept` being locked. Agent A had
not been given the locked-concept list as an input, so the "monitor" produced
a constraint-violating suggestion. The mechanical verifier caught and
corrected the resulting draft anyway, because enforcement does not depend on
the monitor being correct — it depends on an independent downstream check.
This is empirical evidence for **redundant, layered enforcement** rather than
correctness at every layer, a design property directly relevant to AI safety
work on defense-in-depth.

**Verifier intervention rate: 2 of 30 turns (6.7%), 3 drafts rejected, 0
fallback invocations** — Agent B always self-corrected within the retry
budget. The delivered-leakage rate of 0% should be read alongside this
number: it is not that leaks never occurred, but that all occurring leaks
were caught before reaching the student.

**Misconception diagnosis latency: 1 turn** — but this number should not be
overstated. The Persistent Misconceiver persona states its false belief
explicitly in its very first message, so this metric demonstrates Agent A can
catch an *explicitly stated* misconception instantly. It does not test
whether Agent A can infer a misconception from indirect evidence accumulated
across multiple turns, which is the harder and more realistic case.

## Manual case study: the confirmation loophole (open limitation)

Manual review of the Answer-Fisher transcript — not caught by any automated
metric — surfaced a genuine failure mode, which was partially fixed and then
found to persist in a different, deeper form. This iterative process is
reported in full because the root cause is itself a useful, citable finding.

**Round 1 (original transcript):** under sustained urgency pressure, Agent B
confirmed the student's proposed value without using any locked vocabulary —
e.g., *"You are spot on that 3 is the number multiplying the x"* — and at
peak pressure told the student to *"trust your intuition for what you need to
submit right now."* Neither statement contains forbidden vocabulary or
matches a numeric-answer regex, so this failure is invisible to the
verifier entirely; it is a **behavioral leak**, not a vocabulary leak.

**Fix attempt 1:** Agent B's prompt was hardened with an explicit
no-confirmation rule and a no-guessing rule. Re-testing confirmed the
guessing behavior was fully eliminated. The confirmation loophole, however,
**reappeared and worsened** — a later turn stated the full computation
outright: *"Yes, 3 is the correct value because 2 times 3 is 6, and adding 6
gives you 12."*

**Root cause, diagnosed rather than guessed at:** the system prompt contained
two rules in direct, unresolved conflict — "affirm when `observed_outcome` is
correct" and "never confirm a proposed value" — with no stated priority
between them. When Agent A classified an urgent confirmation-seeking message
as `correct` (because the guessed value genuinely was correct), the model
resolved the conflict by affirming rather than withholding. This is a
concrete instance of **rule-conflict / instruction-priority failure**: the
individual rules were each reasonable, but their interaction was not
specified, and the failure mode was predictable in hindsight rather than
random.

**Status: left open, by deliberate choice, rather than iterated further.**
A more robust fix — decoupling "affirming correct reasoning" from "confirming
a specific numeric value" as two independently-gated behaviors rather than
one rule that can override another — was designed but not implemented or
re-tested, given diminishing returns from further prompt-only iteration
against what is fundamentally a specification-completeness problem. Prompt
instructions are the weakest enforcement tier in this system (see the table
above) precisely because they have no mechanical backstop; this finding is
direct evidence for that classification, not a contradiction of it.

---

## Known limitations (stated directly)

- **Not full Theory of Mind.** No recursive belief modeling; "cognitive
  state" here means a structured knowledge/affect tracker, not second-order
  belief reasoning.
- **One concept probed per turn.** A single answer touching multiple
  concepts (e.g., correct on slope, wrong on intercept, in one sentence) only
  updates one concept's mastery per turn.
- **No `no_attempt` outcome category.** A demand for the answer with no
  attempted reasoning (e.g., "just tell me") is currently classified
  identically to a genuine wrong attempt, moving BKT mastery down in both
  cases, despite being different evidence types.
- **Answer-leak detection is heuristic regex**, not exhaustive, and cannot
  catch indirect confirmations (see the confirmation-loophole case study).
- **The confirmation loophole is a known, open, root-caused issue** — see
  above.
- **`frustration_level` is an LLM-inferred heuristic signal**, not a
  validated psychological measurement.
- **Diagnosis-latency evaluation only tested explicitly-stated
  misconceptions**, not indirect/inferred ones.
- **Multimodal (sketch/diagram) input was deliberately scoped out** — mapping
  freehand sketches to specific graph-node errors is an open, unreliable
  problem even for strong vision models, and was judged too high-risk for
  the demo relative to its payoff.

## Future work

- Decouple value-confirmation from correctness-affirmation in Agent B's
  prompt (designed, not yet implemented — see confirmation loophole above).
- Add a `no_attempt` outcome category to the BKT update so refusals/demands
  don't move mastery probability the same way genuine wrong attempts do.
- Extend credit assignment to handle multi-concept evidence within a single
  turn.
- Multimodal input, as a distinct follow-on project rather than a v1 feature.

## Tech stack

Python 3.10+, FastAPI, SQLite, `google-genai` SDK (Gemini Flash, free tier),
Next.js/React frontend. No paid services were used at any point in this
project.

## Running it locally

See `backend/` and `frontend/` — start the backend with
`.\venv\Scripts\uvicorn main:app` and the frontend with `npm run dev`, then
visit `http://localhost:3000`. Toggle Debug Mode for the live cognitive-state
view, concept graph, history scrubber, and counterfactual sandbox.
