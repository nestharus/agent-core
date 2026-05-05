---
description: 'Stage 2b-integrate of the alignment cycle (synthesis). Run only when philosophy-classification.md was produced by Stage 2b-classify AND it contains at least one A (absorbable) or B (compatible-addition) verdict. Read philosophy-classification.md + philosophy-surfaces.md + philosophy.md and synthesize the integrated text: clarify existing principles for A verdicts, draft new provisional principles for B verdicts, update philosophy.md. Does NOT modify philosophy-decisions.md (that is Stage 2b-classify''s job; user-input concerns are not integrated).'
model: gpt-high
output_format: ''
---

# Philosophy Expansion — Integrate

## Purpose

Take the verdicts emitted by Stage 2b-classify (`philosophy-classification.md`) and apply the **safe** changes to the philosophy:

- A (absorbable) → clarify or extend the existing principle.
- B (compatible addition) → draft a new principle, marked provisional.

Concerns classified C (tension), D (new-axis), or E (contradiction) require user input. They are captured in `philosophy-decisions.md` (written by Stage 2b-classify) and are NOT integrated by this operator. The orchestrator surfaces `philosophy-decisions.md` to the root as a NEEDS_INPUT new-value-question.

Per `~/ai/models/roles.md`, synthesis is `gpt-high`'s role: builder, not judge. The classifier already decided which concerns are absorbable, compatible, or require user input.

---

## Inputs

- **`philosophy-classification.md`** — per-concern verdicts from Stage 2b-classify (authoritative; do not re-judge).
- **`philosophy-surfaces.md`** — original concern text (so you can quote it when drafting).
- **`philosophy.md`** — current product philosophy (target of integration).

## Outputs

- **`philosophy.md`** — updated with absorbable clarifications/extensions (A verdicts) and provisional new principles (B verdicts).

You do **not** modify `philosophy-classification.md`. You do **not** modify `philosophy-decisions.md` (that file, if present, was written by Stage 2b-classify and the orchestrator surfaces it directly to the root). You do **not** re-judge concerns. If a verdict in `philosophy-classification.md` looks wrong, emit `NEEDS_INPUT:<scratch_dir>/questions/<question-id>.question.json` per `~/ai/conventions/agent-questions-and-session-graph.md` and stop.

---

## Procedure

### Step 1: Read the classification

Open `philosophy-classification.md`. Build two work-lists:

- **Absorbable (A)** — every row whose verdict is `A`. Each row cites the existing principle by number and includes a one-sentence handoff describing what clarification or extension belongs there.
- **Compatible additions (B)** — every row whose verdict is `B`. Each row proposes the next available principle number and a one-sentence handoff describing the new principle.

Skip every row whose verdict is C, D, or E. Those are user-input cases captured in `philosophy-decisions.md`. They are not yours to integrate.

### Step 2: Apply absorbable clarifications

For each A verdict:

1. Open the cited principle in `philosophy.md`.
2. Draft a clarification or extension that captures the implicit principle the classifier identified.
3. Keep the change minimal — add precision, do not rewrite.
4. The new wording must remain consistent with the principle's existing direction. Absorbable means absorbing into existing direction, not redirecting.

### Step 3: Draft provisional compatible additions

For each B verdict:

1. Read the surface text in `philosophy-surfaces.md`.
2. Draft a new principle following the style of existing principles (numbered, voiced consistently).
3. Use the principle number proposed by the classifier.
4. Draft principle interactions with existing principles where relevant.
5. Mark the new principle **provisional** in the text — the user should confirm it belongs in the philosophy and that the articulation is correct. Use a clear marker (e.g. an inline `(provisional, pending user confirmation)` tag at the end of the principle's first sentence).

---

## Anti-scope (load-bearing)

- **Do NOT re-judge concerns.** The classifier already decided. If a verdict looks wrong, emit `NEEDS_INPUT:<scratch_dir>/questions/<question-id>.question.json` and stop.
- **Do NOT integrate C, D, or E verdicts.** Those concerns require user input; they live in `philosophy-decisions.md` (which you do not modify).
- **Do NOT modify `philosophy-decisions.md`.** That file, if present, was written by Stage 2b-classify. The orchestrator owns the user-input handoff.
- **Do NOT force-resolve tensions or contradictions.** They were intentionally left to the user.
- **Do NOT modify the proposal.** The proposal prompted the discovery; you only update the philosophy.
- **Do NOT modify the problem definition.** Problem-side concerns are Stage 1b territory.
- **Do NOT remove existing principles.** The philosophy may need revision, but removing principles is a user decision, not an integration action.
- **Do NOT invent principles.** Every drafted clarification or new principle must trace back to a concern in `philosophy-surfaces.md` whose verdict in `philosophy-classification.md` authorizes integration as A or B.

---

## Quality checks

Before declaring the stage complete:

- [ ] Every A verdict has a corresponding clarification/extension in the cited principle.
- [ ] Every B verdict has a corresponding new principle in `philosophy.md` with the proposed number and a `(provisional, pending user confirmation)` marker.
- [ ] No C, D, or E verdict was integrated.
- [ ] No existing principle was removed or directionally rewritten.
- [ ] Every absorbable change is genuinely a clarification, not a direction change disguised as clarification.
- [ ] Every compatible addition is genuinely independent — it does not implicitly override or reinterpret existing principles.
- [ ] `philosophy-decisions.md` (if present) was untouched.
