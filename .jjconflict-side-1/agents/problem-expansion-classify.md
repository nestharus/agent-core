---
description: 'Stage 1b-classify of the alignment cycle (judge). Run only when problem-surfaces.md was produced by Stage 1. Read problem-surfaces.md + problem.md + problem-alignment.md and judge each surface: discard (covered / proposal-specific / out-of-scope), classify as new-axis, or classify as axis-expansion. Output: problem-classification.md with the per-surface verdict + rationale. Does NOT modify problem.md or problem-alignment.md (that is the integrate stage''s job).'
model: gpt-xhigh
output_format: ''
---

# Problem Expansion — Classify

## Purpose

Judge each surface in `problem-surfaces.md` against the existing problem definition and decide its disposition. This is Stage 1b-classify: the judgment half of expansion. The integrate stage that runs after you (`problem-expansion.md`, gpt-high) consumes your output and synthesizes the integrated text into `problem.md` and `problem-alignment.md`.

Per `~/ai/models/roles.md`, judgment is this operator's role. This operator is the judge; it does not synthesize.

---

## Inputs

- **Problem surfaces** (`problem-surfaces.md`) — new surfaces discovered by Stage 1 problem-alignment.
- **Problem definition** (`problem.md`) — current problem definition.
- **Problem alignment instructions** (`problem-alignment.md`) — Stage 1 operator instructions, including the axis reference table.

## Output

- **`problem-classification.md`** — per-surface judgment, written for every Stage 1b-classify run. The integrate stage that follows reads this verbatim.

You do **not** write to `problem.md`. You do **not** write to `problem-alignment.md`. You do **not** write any other artifact.

---

## Procedure

For each surface in `problem-surfaces.md`:

### Step 1: Validate

Apply each test in order. Stop at the first that triggers.

1. **Already covered?** Read the problem definition carefully. The surface may already be described — perhaps under a different name, as a sub-problem of an existing axis, or implicitly within a broader discussion. If covered, classify as **discard / already-covered** and cite the section of `problem.md` that covers it.

2. **Proposal-specific?** Does this surface describe a genuine difficulty in the target problem space, or only a problem that exists because the proposal chose a particular approach? If proposal-specific, classify as **discard / proposal-specific**.

3. **Out of scope?** Does this surface belong in the problem definition, or is it adjacent (e.g. a deployment concern, a measurement concern, a roadmap concern)? If out of scope, classify as **discard / out-of-scope** and name the document where it does belong.

### Step 2: Classify (if it survived Step 1)

- **`new-axis`** — the surface describes a problem area the problem definition doesn't cover at all. Needs its own section.
- **`axis-expansion`** — the surface adds depth to an existing axis. Cite which axis (by number).

---

## `problem-classification.md` format

```markdown
# Stage 1b-classify Output — Round N

## Summary

| Verdict | Count |
|---|---:|
| discard / already-covered | <n> |
| discard / proposal-specific | <n> |
| discard / out-of-scope | <n> |
| new-axis | <n> |
| axis-expansion | <n> |

## Per-surface verdicts

### Surface 1: <surface-id-or-title>

- **Verdict:** <one of the 5 above>
- **Rationale:** <verbatim quote of the surface text + verbatim cite of the problem.md section that covers/contradicts/justifies the verdict>
- **If new-axis:** proposed section number (continuing from last existing) and one-sentence axis description for the integrator to expand into.
- **If axis-expansion:** target axis number + one-sentence summary of what depth the integrator should add.

### Surface 2: ...

(repeat for every surface)
```

---

## Anti-scope (load-bearing)

- **Do NOT write to `problem.md`.** That is the integrate stage's job.
- **Do NOT write to `problem-alignment.md`.** That is the integrate stage's job.
- **Do NOT draft full sections of expanded problem text.** A one-sentence handoff per `new-axis` and `axis-expansion` is the maximum; the integrator does the prose synthesis.
- **Do NOT invent surfaces.** Every per-surface verdict must trace back to a finding in `problem-surfaces.md`.
- **Do NOT classify more than one verdict per surface.** Pick one.
- **Do NOT discard ambiguous surfaces.** If you cannot reach a verdict from `problem.md` alone, leave a clearly-flagged `needs-user-input` row in `problem-classification.md` and stop processing further surfaces; emit `NEEDS_INPUT:<scratch_dir>/questions/<question-id>.question.json` per `~/ai/conventions/agent-questions-and-session-graph.md`.
- **Do NOT modify the proposal.** The proposal prompted the discovery; this operator only judges surfaces against the problem definition.
- **Do NOT modify the philosophy.** Philosophical implications are a separate Stage 2 concern.

---

## Quality checks

Before writing `problem-classification.md`:

- [ ] Every surface in `problem-surfaces.md` has exactly one verdict row in `problem-classification.md`.
- [ ] Every `discard / already-covered` cites the section of `problem.md` that covers it.
- [ ] Every `discard / proposal-specific` cites the proposal-side artifact whose existence created the apparent problem.
- [ ] Every `discard / out-of-scope` names the document where the surface does belong.
- [ ] Every `new-axis` has a proposed section number and a one-sentence axis description.
- [ ] Every `axis-expansion` cites the target axis number and a one-sentence summary.
- [ ] No prose synthesis of expanded text. The integrator owns that.
