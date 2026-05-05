---
workflow:
  id: alignment-cycle
workflow_dispatch_contract:
  orchestrator: "alignment-cycle-orchestrator"
  inputs:
    - "project problem.md, philosophy.md, proposal.md, and axis reference table"
    - "scratch directory for problem, philosophy, classification, and run-report artifacts"
  expectations:
    - "reviews proposal alignment against the problem definition and product philosophy"
    - "splits judgement from synthesis through classify and integrate stages"
    - "halts only when philosophy decisions require root-surfaced user input"
  outputs:
    - "problem-review.md and optional problem-surfaces.md or problem-classification.md artifacts"
    - "updated problem.md and project axis reference table when Stage 1b-integrate runs"
    - "philosophy-review.md and optional philosophy-surfaces.md, philosophy-classification.md, or philosophy-decisions.md artifacts"
    - "updated philosophy.md when Stage 2b-integrate runs"
    - "run-report.md describing completed stages, skips, and open NEEDS_INPUT artifacts"
  non_goals:
    - "does not author or update proposal.md as the proposer"
    - "does not re-run alignment stages inside the same cycle after integrations"
---
# Alignment Cycle

End-to-end procedure for the proposal alignment review loop that runs against any project's `problem.md` ↔ `philosophy.md` ↔ `proposal.md` triangle.

Model assignments are authoritative in [`~/ai/models/roles.md`](../models/roles.md).
Operator routing is in [`~/ai/AGENTS.md`](../AGENTS.md) under "Strategic planning / proposal alignment cycle".
Agent invocation: [`~/ai/workflows/agents-cli.md`](agents-cli.md).
Agent Q&A and session graph convention: [`~/ai/conventions/agent-questions-and-session-graph.md`](../conventions/agent-questions-and-session-graph.md).

## Purpose

Verify that a project's current proposal still aligns with its problem definition and product philosophy. When alignment surfaces new problem axes or philosophical concerns, integrate the absorbable ones and surface the user-input ones.

This is **not** the proposer. The user (or a separate proposer dispatch) updates `proposal.md` externally; the alignment cycle reviews whatever proposal currently exists.

## Principles

- **Separate agents for separate concerns.** Alignment (judge) ≠ expansion (synthesis). Both expansion stages are split: classify (judge) and integrate (synthesis).
- **Opus never synthesizes** (per `~/ai/models/roles.md`). Alignment + classify run on `claude-opus`. Integrate runs on `gpt-high`.
- **Conditional skipping.** Stage 1b only runs if Stage 1 produced surfaces. Stage 2b only runs if Stage 2 produced surfaces. Stage 1b-integrate only runs if Stage 1b-classify emitted at least one non-discard verdict. Stage 2b-integrate only runs if Stage 2b-classify emitted at least one A or B verdict and did not write `philosophy-decisions.md`.
- **User-input gate is owned by classify.** Stage 2b-classify writes `philosophy-decisions.md` when concerns require user input (C-tension, D-new-axis, E-contradiction). The orchestrator surfaces it to the root as a NEEDS_INPUT new-value-question.
- **The expansion stages do not re-run Stage 1 / Stage 2 in the same cycle.** Updated `problem.md` / `philosophy.md` content is evaluated in the next full cycle.

## Phase Map

```
Stage 1                — problem-alignment       (claude-opus)  → problem-review.md (always), problem-surfaces.md (conditional)
  Stage 1b-classify    — problem-expansion-classify  (claude-opus)  → problem-classification.md
    Stage 1b-integrate — problem-expansion-integrate (gpt-high)     → updates problem.md + axis table
Stage 2                — philosophy-alignment    (claude-opus)  → philosophy-review.md (always), philosophy-surfaces.md (conditional)
  Stage 2b-classify    — philosophy-expansion-classify (claude-opus) → philosophy-classification.md, philosophy-decisions.md (conditional)
    Stage 2b-integrate — philosophy-expansion-integrate (gpt-high)   → updates philosophy.md
Run report
```

## Stage details

### Stage 1 — Problem alignment review

- Operator: [`~/ai/agents/problem-alignment.md`](../agents/problem-alignment.md)
- Model: `claude-opus`
- Inputs: project's `problem.md`, `proposal.md`, project axis reference table (`<project>/product-strategy/problem-axis-table.md` or equivalent — passed as runtime input).
- Outputs: `problem-review.md` (always); `problem-surfaces.md` (only if the proposal reveals new problem surfaces).

### Stage 1b-classify — Problem expansion (judge)

- Skip if Stage 1 did not produce `problem-surfaces.md`.
- Operator: [`~/ai/agents/problem-expansion-classify.md`](../agents/problem-expansion-classify.md)
- Model: `claude-opus`
- Outputs: `problem-classification.md` (per-surface verdict: `discard / already-covered`, `discard / proposal-specific`, `discard / out-of-scope`, `new-axis`, or `axis-expansion`).
- Does NOT modify `problem.md` or the axis table.

### Stage 1b-integrate — Problem expansion (synthesis)

- Skip if every verdict in `problem-classification.md` is `discard`.
- Operator: [`~/ai/agents/problem-expansion-integrate.md`](../agents/problem-expansion-integrate.md)
- Model: `gpt-high`
- Inputs: `problem-classification.md` (authoritative), `problem-surfaces.md`, `problem.md`, project axis table.
- Outputs: updated `problem.md` (new sections + expanded sections); updated project axis table (new rows for `new-axis` verdicts).
- Does NOT re-judge.

### Stage 2 — Philosophy alignment review

- Skip if `problem-review.md` reports zero axes-aligned (nothing to review for philosophy alignment).
- Operator: [`~/ai/agents/philosophy-alignment.md`](../agents/philosophy-alignment.md)
- Model: `claude-opus`
- Inputs: project's `philosophy.md`, `proposal.md`, `problem-review.md`.
- Outputs: `philosophy-review.md` (always); `philosophy-surfaces.md` (only if the proposal reveals new philosophical concerns).

### Stage 2b-classify — Philosophy expansion (judge)

- Skip if Stage 2 did not produce `philosophy-surfaces.md`.
- Operator: [`~/ai/agents/philosophy-expansion-classify.md`](../agents/philosophy-expansion-classify.md)
- Model: `claude-opus`
- Outputs: `philosophy-classification.md` (per-concern verdict: A absorbable, B compatible-addition, C tension, D new-axis, E contradiction); `philosophy-decisions.md` (only when any C/D/E exists; user-input gate).
- If `philosophy-decisions.md` is written, the orchestrator halts after this sub-stage and surfaces the artifact to the root as a NEEDS_INPUT new-value-question.

### Stage 2b-integrate — Philosophy expansion (synthesis)

- Skip if Stage 2b-classify wrote `philosophy-decisions.md`.
- Skip if `philosophy-classification.md` contains no A or B verdicts.
- Operator: [`~/ai/agents/philosophy-expansion-integrate.md`](../agents/philosophy-expansion-integrate.md)
- Model: `gpt-high`
- Inputs: `philosophy-classification.md` (authoritative), `philosophy-surfaces.md`, `philosophy.md`.
- Outputs: updated `philosophy.md` (clarifications/extensions for A; provisional new principles for B, marked `(provisional, pending user confirmation)`).
- Does NOT integrate C/D/E. Does NOT modify `philosophy-decisions.md`.

### Run report

After all stages complete (or halt at the user-input gate), the orchestrator writes a run report at `<scratch_dir>/run-report.md` describing per-stage outcomes, conditional-skip reasoning, and any open NEEDS_INPUT artifacts.

## Gate ownership

- Each Stage's "did the proposal align?" question is a **model gate** owned by the alignment operator (claude-opus). No human gate within the cycle.
- The **only human gate** in the cycle is `philosophy-decisions.md` when Stage 2b-classify writes it (NEEDS_INPUT new-value-question to root).

## Cycle re-run policy

- Updated `problem.md` / `philosophy.md` from Stage 1b-integrate / Stage 2b-integrate do NOT trigger a re-run of Stage 1 / Stage 2 within the same cycle. Next full cycle picks them up.
- A new `proposal.md` (after the user / proposer updates it) DOES trigger a fresh cycle.

## Decision recording

If a phase is skipped beyond the conditional-skip rules, narrowed, or accepted with a residual concern, record it in the project's `DECISIONS.md` (or equivalent) with who decided, why, what risk is being accepted, and what evidence justified the deviation. The conditional-skip rules above do NOT require DECISIONS.md entries — they are normal cycle behavior.

## Adjacent references

- [`~/ai/agents/alignment-cycle-orchestrator.md`](../agents/alignment-cycle-orchestrator.md)
- [`~/ai/agents/problem-alignment.md`](../agents/problem-alignment.md)
- [`~/ai/agents/problem-expansion-classify.md`](../agents/problem-expansion-classify.md)
- [`~/ai/agents/problem-expansion-integrate.md`](../agents/problem-expansion-integrate.md)
- [`~/ai/agents/philosophy-alignment.md`](../agents/philosophy-alignment.md)
- [`~/ai/agents/philosophy-expansion-classify.md`](../agents/philosophy-expansion-classify.md)
- [`~/ai/agents/philosophy-expansion-integrate.md`](../agents/philosophy-expansion-integrate.md)
- [`~/ai/agents/proposer.md`](../agents/proposer.md) (proposal authoring; not invoked by the alignment cycle)
- [`~/ai/models/roles.md`](../models/roles.md)
- [`~/ai/workflows/agents-cli.md`](agents-cli.md)
- [`~/ai/conventions/agent-questions-and-session-graph.md`](../conventions/agent-questions-and-session-graph.md)
