---
description: 'Stage 1b-integrate of the alignment cycle (synthesis). Run only when problem-classification.md was produced by Stage 1b-classify. Read problem-classification.md + problem-surfaces.md + problem.md + problem-alignment.md and synthesize the integrated text: draft expansions for new-axis and axis-expansion verdicts, update problem.md, and update the axis reference table in problem-alignment.md if new axes were added. Does NOT make classification judgments (that is Stage 1b-classify''s job).'
model: gpt-high
output_format: ''
---

# Problem Expansion — Integrate

## Purpose

Take the verdicts emitted by Stage 1b-classify (`problem-classification.md`) and synthesize the integrated text into the problem definition. This is the second half of expansion: pure synthesis, no judgment. The classification was already done.

Per `~/ai/models/roles.md`, synthesis is `gpt-high`'s role: builder, not judge. The classifier already discarded covered/proposal-specific/out-of-scope surfaces; you only see what survived.

---

## Inputs

- **`problem-classification.md`** — per-surface verdicts from Stage 1b-classify (authoritative; do not re-judge).
- **`problem-surfaces.md`** — original surface text (so you can quote it when drafting).
- **`problem.md`** — current problem definition (target of integration).
- **`problem-alignment.md`** — Stage 1 operator instructions, contains the axis reference table (target of integration).

## Outputs

- **`problem.md`** — updated with new sections (one per `new-axis` verdict) and expanded sections (one per `axis-expansion` verdict).
- **`problem-alignment.md`** — axis reference table updated with new rows when `new-axis` verdicts were emitted.

You do **not** modify `problem-classification.md`. You do **not** re-judge surfaces. If a verdict in `problem-classification.md` looks wrong, raise it as a NEEDS_INPUT to the orchestrator and stop — do not silently override.

---

## Procedure

### Step 1: Read the classification

Open `problem-classification.md`. Build two work-lists:

- **New axes** — every row whose verdict is `new-axis`. Each row already has a proposed section number and a one-sentence handoff.
- **Axis expansions** — every row whose verdict is `axis-expansion`. Each row already has a target axis number and a one-sentence handoff.

Skip every row whose verdict starts with `discard` — you are not allowed to integrate a discarded surface.

### Step 2: Draft new-axis sections

For each `new-axis` verdict:

1. Read the corresponding surface text in `problem-surfaces.md`.
2. Write a new section for `problem.md` following the style and structure of existing sections.
3. The section must describe the **core difficulty** — why this problem is hard and resists solution — not a feature wish list and not a solution sketch.
4. Use the section number proposed by the classifier.

### Step 3: Draft axis expansions

For each `axis-expansion` verdict:

1. Read the corresponding surface text in `problem-surfaces.md`.
2. Read the target axis section in the current `problem.md`.
3. Draft additional content for that section, in the section's existing voice and structure.
4. The expansion must describe the newly revealed difficulty in the context of the existing section's treatment.
5. Do **not** rewrite the existing section. Add to it. Existing descriptions are not wrong; they are insufficient.

### Step 4: Update the axis reference table

For each `new-axis` verdict integrated in Step 2:

1. Open `problem-alignment.md`.
2. Add a row to the axis reference table at the bottom.
3. Use the same axis number you assigned to the section.
4. Mirror the column shape of existing rows.

---

## Anti-scope (load-bearing)

- **Do NOT re-judge surfaces.** The classifier already decided. If a verdict looks wrong, emit `NEEDS_INPUT:<scratch_dir>/questions/<question-id>.question.json` per `~/ai/conventions/agent-questions-and-session-graph.md` and stop.
- **Do NOT integrate discarded surfaces.** Rows whose verdict starts with `discard` are off-limits.
- **Do NOT modify the proposal.** The proposal may have prompted the discovery; you only update the problem definition.
- **Do NOT modify the philosophy.** Philosophical implications are Stage 2b territory.
- **Do NOT remove or rewrite existing problem.md content.** The problem definition grows; it does not shrink. Add depth, do not replace.
- **Do NOT invent surfaces.** Every drafted section or expansion must trace back to a surface in `problem-surfaces.md` whose verdict in `problem-classification.md` authorizes integration.

---

## Quality checks

Before declaring the stage complete:

- [ ] Every `new-axis` verdict has a corresponding new section in `problem.md` with the assigned section number.
- [ ] Every `axis-expansion` verdict has corresponding additional content in the target axis section.
- [ ] Every `new-axis` integration has a corresponding new row in the axis reference table in `problem-alignment.md`.
- [ ] Every drafted section describes a core difficulty, not a feature or solution.
- [ ] No `discard` verdicts were integrated.
- [ ] No existing `problem.md` content was removed or rewritten.
- [ ] The axis reference table in `problem-alignment.md` is consistent with `problem.md`'s sections.
