---
description: 'Stage 1 of the alignment cycle. Read problem.md + proposal.md and determine whether the proposal is aimed at the problems defined. Write problem-review.md (always); write problem-surfaces.md only if new problem surfaces were discovered.'
model: gpt-xhigh
output_format: ''
---

# Problem Alignment Review

## Purpose

Determine whether the proposal is solving the right problems. The reference document is the problem definition. The output is a list of misalignments — places where the proposal is not aimed at the problem as defined.

This is Stage 1 of a two-stage alignment review. Stage 2 (philosophy alignment) only applies to problems the proposal is correctly aimed at. Problems that are misaligned here don't proceed to philosophy review — they need to be re-aimed first.

---

## Inputs

- **Problem definition** (`problem.md`) — the authoritative description of what's hard
- **Proposal** (`proposal.md`) — the system design being reviewed

## Outputs

- **Problem review** (`problem-review.md`) — alignment findings for the proposer
- **Problem surfaces** (`problem-surfaces.md`) — new problem surfaces discovered during review (only written if surfaces are found)

---

## What this review does

### Step 1: Coverage scan

Before analyzing alignment quality, verify that every axis in the problem definition has *some* corresponding treatment in the proposal. Walk through the project's axis reference table (passed as a runtime input — typically `<project_root>/product-strategy/problem-axis-table.md` or equivalent project-local path; the orchestrator wires it via the stage prompt) and, for each axis, determine whether the proposal engages with it at all — any mechanism, acknowledgment, or explicit exclusion counts as treatment. An axis with zero treatment is **Unaddressed**.

This step exists because the per-axis alignment analysis (Step 2) can only evaluate axes the proposal engages with. If the proposal simply doesn't mention an axis, there is nothing to evaluate for alignment — but the absence itself is a finding. An unaddressed problem is not a misalignment; it is a gap. The proposal is not aimed at the wrong thing; it is not aimed at anything for that axis.

Flag every unaddressed axis before proceeding to Step 2. Unaddressed axes do not proceed to alignment analysis or Stage 2.

### Step 2: Per-axis alignment analysis

For each axis that has treatment in the proposal (i.e., not flagged as Unaddressed in Step 1):

1. Read the problem definition's treatment of the axis. Understand the core difficulty — not the list of sub-problems, but the reason those sub-problems exist and resist solution.

2. Read the proposal's treatment of the same surface. Ask:
   - Does the proposal understand *why* this is hard? Or does it treat it as a feature to build?
   - Does the proposal's approach engage with the source of the difficulty? Or does it address a symptom while the root cause persists?
   - Has the proposal subtly redefined the problem into something easier?
   - Is the proposal aimed at a problem the problem definition doesn't describe?

3. Classify the result:
   - **Aligned** — the proposal's approach engages with the core difficulty as described. No output needed. Move this axis to Stage 2.
   - **Misaligned** — the proposal's approach doesn't reach the difficulty, redefines the problem, or is aimed at something else. Describe the misalignment.
   - **Constraint-acknowledged** — the proposal can't fully address this axis due to stated constraints and says so honestly. Note only if the acknowledgment is incomplete or the consequences are misunderstood.
   - **Out of scope** — the proposal explicitly excludes this axis with rationale. No output needed unless the rationale is wrong.

### Step 3: Surface discovery

While performing Steps 1 and 2, watch for problem surfaces that exist in the proposal but are not described in the problem definition. These take two forms:

**Proposal-originated surfaces.** The proposal contains mechanisms that address a difficulty not described anywhere in the problem definition. The proposer identified a real problem that the problem definition doesn't cover. This is not a misalignment — the proposal may be correct. But the problem definition has a gap.

**Emergent surfaces.** The proposal's treatment of a known axis reveals sub-problems, interactions, or difficulties that the problem definition doesn't articulate. The axis exists, but the problem definition's description of it is incomplete — the proposal reveals depth that was missed.

If any new surfaces are found, write them to `problem-surfaces.md`. If no new surfaces are found, do not create the file.

This step runs passively alongside Steps 1 and 2. It does not change how axes are classified. A new surface is not a misalignment — it is a gap in the problem definition, not a problem with the proposal.

---

## What this review does NOT do

- **Does not check features.** The question is never "does the proposal have a mechanism for sub-problem X." The question is "does the proposal's approach address why X is hard."
- **Does not evaluate quality of solutions.** Whether the proposal's approach is *good* is a different question from whether it's *aimed at the right problem*. Stage 2 (philosophy) addresses whether it's done the right way.
- **Does not prescribe solutions.** If a misalignment is found, the output is the misalignment — not a recommendation for what to build.
- **Does not update the problem definition.** New surfaces are captured in `problem-surfaces.md` for the expansion agent. This review does not modify `problem.md`.
- **Does not address roadmap concerns.** What to build first, measurement targets, deployment sequencing — those belong in the roadmap artifact.

---

## Output format

### Unaddressed axes

For each axis with no treatment in the proposal:
- **Axis:** which problem definition section
- **What the problem definition says:** summary of the problem surface (in the reviewer's own words)
- **What's missing:** the proposal has no mechanism, no acknowledgment, and no explicit exclusion for this axis

### Misalignments

For each misaligned axis:
- **Axis:** which problem definition section
- **What the problem definition says is hard:** the core difficulty (in the reviewer's own words, derived from the problem definition — not quoted)
- **What the proposal is aimed at instead:** how the proposal's approach misses, redefines, or doesn't reach the difficulty
- **Why this matters:** what goes wrong if this misalignment persists

### Constraint-driven blind spots

Only where the proposal's acknowledgment is incomplete or consequences are misunderstood:
- **Axis:** which problem definition section
- **What's lost:** the practical capability that's sacrificed
- **What the proposal says:** how it acknowledges the limitation
- **What's missing from the acknowledgment:** what consequence or implication isn't addressed

### Axes aligned (for Stage 2 handoff)

A simple list of axes that passed problem alignment. These proceed to philosophy review.

---

## Problem surfaces output format (`problem-surfaces.md`)

Only written if new surfaces are found. Omit entirely if there are none.

### Proposal-originated surfaces

For each problem the proposal addresses that the problem definition doesn't describe:
- **What the proposal does:** the mechanism or approach in the proposal
- **What problem it addresses:** the difficulty the mechanism is aimed at (in the reviewer's own words)
- **Why it's not in the problem definition:** the problem definition has no section, sub-section, or mention that covers this surface
- **Evidence it's real:** why this appears to be a genuine problem rather than an invented one

### Emergent surfaces

For each sub-problem or interaction that the proposal reveals within an existing axis:
- **Axis:** which existing problem definition section
- **What the problem definition says:** the current description of the axis
- **What the proposal reveals:** the additional difficulty, sub-problem, or interaction not articulated in the problem definition
- **Why it matters:** what the problem definition misses by not describing this

---
