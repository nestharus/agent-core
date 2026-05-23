---
description: 'Run the proposal alignment review cycle against problem.md + philosophy.md, expand problem/philosophy when new surfaces are discovered, write philosophy-decisions.md when philosophy concerns require user input, and produce a run report. The orchestrator dispatches Stage 1 (problem alignment), Stage 1b (problem expansion), Stage 2 (philosophy alignment), and Stage 2b (philosophy expansion). It does NOT run the proposer; that is user-driven.'
model: gpt-xhigh
output_format: ''
---

# Review Orchestrator

## Contract

```yaml
schema: operator-contract-v1
inputs:
  - name: problem_path
    type: path
    required: true
    default_source: caller
    description: "problem path"
  - name: philosophy_path
    type: path
    required: true
    default_source: caller
    description: "philosophy path"
  - name: proposal_path
    type: path
    required: true
    default_source: caller
    description: "proposal path"
  - name: axis_table_path
    type: path
    required: true
    default_source: caller
    description: "axis table path"
  - name: scratch_dir
    type: path
    required: true
    default_source: caller
    description: "scratch dir"
  - name: brief_path
    type: path
    required: false
    default_source: caller
    description: "brief path"
defaults:
  []
secrets:
  []
outputs:
  - task: run-alignment-cycle
    success_shape: "Task-specific stdout or durable artifact paths named by the procedure."
    wrote_lines: []
errors:
  - class: BLOCKED
    cause: "Required inputs are missing, unreadable, contradictory, or unsafe for the selected task."
    recovery: "Supply corrected inputs or select the appropriate operator wrapper before rerun."
  - class: NEEDS_INPUT
    cause: "A user-owned value, scope, or trade-off question is required."
    recovery: "Answer the emitted question artifact and resume."
side_effects:
  - strategy-doc-updates-via-integrators
  - alignment-review-dispatches
  - classification-dispatches
must_delegate:
  - problem-bootstrap
  - philosophy-bootstrap
  - problem-alignment
  - problem-expansion-classify
  - problem-expansion-integrate
  - philosophy-alignment
  - philosophy-expansion-classify
  - philosophy-expansion-integrate
may_direct:
  - strategy-doc-read
  - stage-output-validation
forbidden_direct:
  - proposer-execution
  - resolving-user-owned-philosophy-decisions
```

## Purpose

Run the alignment review process against the current proposal, expand the problem definition and philosophy when new surfaces are discovered, and report the result. The orchestrator does not run the proposer — the user handles proposal updates externally and signals the orchestrator when a new proposal is ready.

---

## Files

| File | Role | Managed by |
|---|---|---|
| `problem.md` | Problem definition | Problem expansion agent (expanded when surfaces found) |
| `philosophy.md` | Product philosophy | Philosophy expansion agent (expanded when surfaces found) |
| `proposal.md` | Current proposal | Proposer (user-driven) |
| `problem-alignment.md` | Stage 1 agent instructions | Problem expansion agent (axis table updated when new axes added) |
| `philosophy-alignment.md` | Stage 2 agent instructions | This orchestrator (read-only) |
| `problem-bootstrap.md` | Empty-state problem seed operator instructions | This orchestrator (read-only) |
| `philosophy-bootstrap.md` | Empty-state philosophy seed operator instructions | This orchestrator (read-only) |
| `problem-expansion-integrate.md` | Problem expansion integration agent instructions | This orchestrator (read-only) |
| `philosophy-expansion-integrate.md` | Philosophy expansion integration agent instructions | This orchestrator (read-only) |
| `proposer.md` | Proposer agent instructions | This orchestrator (read-only) |
| `problem-review.md` | Stage 1 output — alignment findings | Written each run by Stage 1 |
| `problem-surfaces.md` | Stage 1 output — new problem surfaces | Written by Stage 1 (only if surfaces found) |
| `philosophy-review.md` | Stage 2 output — alignment findings | Written each run by Stage 2 |
| `philosophy-surfaces.md` | Stage 2 output — new philosophical concerns | Written by Stage 2 (only if surfaces found) |
| `philosophy-decisions.md` | Stage 2b output — decisions needing user input | Written by Stage 2b (only if user input needed) |

---

## Process

### Pre-dispatch read protocol

Before any child-operator, workflow, ticket-operator, auditor, proposer, reviewer, or role dispatch:

1. Resolve the intended operator name and file path from workflow context and the current project scope.
2. Prefer the current project's wrapper when one exists for that operator and task, for example `~/projects/<name>/agents/<operator>.md` before `~/ai/agents/<operator>.md`.
3. Read the selected operator file's `## Contract` block.
4. Apply wrapper or base defaults only from declared `defaults:` entries, and apply secrets only from declared `secrets:` entries. Do not fill defaults from session metadata or ambient environment values unless the selected contract declares that source.
5. Validate that every required input for the chosen task is present after declared defaults are applied.
6. Refuse direct operations covered by the selected contract's `must_delegate:` list unless the contract explicitly allows the direct operation through `may_direct:`.
7. Compose the dispatch prompt with only inputs, task variant, anti-scope, stop conditions, and evidence paths. Do not include the selected operator's procedure mechanics, phase order, command recipes, or verdict handling.


### Empty-state Prelude

Before Stage 1, check whether the project's `problem.md` and `philosophy.md` seed artifacts exist. This prelude is additive: after both seed documents exist, continue to the existing Stage 1 / 1b / 2 / 2b dispatch logic unchanged.

1. If `problem.md` does not exist, dispatch `problem-bootstrap.md` (model: `gpt-high`) with the supplied `brief_path`, `project_root`, target `problem_path`, target `axis_table_path`, and `scratch_dir`. If `problem-bootstrap` returns `BLOCKED:<reason>` or `NEEDS_INPUT:<absolute_artifact_path>`, surface that same marker to the root and halt before philosophy bootstrap.
2. After `problem-bootstrap` completes, verify that `problem_path` now exists and is non-empty. If validation fails, surface `BLOCKED:<reason>` and halt.
3. If `philosophy.md` does not exist, dispatch `philosophy-bootstrap.md` (model: `gpt-high`) with the supplied `brief_path`, the now-present `problem_path`, target `philosophy_path`, and `scratch_dir`. If `philosophy-bootstrap` returns `BLOCKED:<reason>` or `NEEDS_INPUT:<absolute_artifact_path>`, surface that same marker to the root and halt.
4. After `philosophy-bootstrap` completes, verify that `philosophy_path` now exists and is non-empty. If validation fails, surface `BLOCKED:<reason>` and halt.
5. Record whether the empty-state prelude ran or was skipped in the run report, then proceed to Stage 1.

### Stage 1: Problem Alignment Review

Run a sub-agent with the instructions in `problem-alignment.md`.

Provide the agent with:
- `problem.md` (the problem definition)
- `proposal.md` (the current proposal)

The agent writes:
- `problem-review.md` (alignment findings — always written)
- `problem-surfaces.md` (new problem surfaces — only written if surfaces are found)

### Stage 1b: Problem Expansion (split: classify → integrate)

Check whether `problem-surfaces.md` was produced by Stage 1.

If it was not produced, skip this stage entirely — no new problem surfaces were discovered.

If it was produced, run two sub-agents in sequence: **Stage 1b-classify (judge)** then **Stage 1b-integrate (synthesis)**. The split enforces the `~/ai/models/roles.md` rule that opus never synthesizes; classification judgment runs on `claude-opus`, integrated text synthesis runs on `gpt-high`.

#### Stage 1b-classify

Run a sub-agent with the instructions in `problem-expansion-classify.md` (model: `claude-opus`).

Provide the agent with:
- `problem-surfaces.md` (the new surfaces)
- `problem.md` (the current problem definition)
- `problem-alignment.md` (the Stage 1 instructions with axis table)

The agent writes:
- `problem-classification.md` (per-surface verdict: `discard / already-covered`, `discard / proposal-specific`, `discard / out-of-scope`, `new-axis`, or `axis-expansion`)

#### Stage 1b-integrate

Check whether `problem-classification.md` contains at least one `new-axis` or `axis-expansion` verdict.

If every verdict is `discard`, skip the integrate sub-stage — there is nothing to synthesize.

Otherwise, run a sub-agent with the instructions in `problem-expansion-integrate.md` (model: `gpt-high`).

Provide the agent with:
- `problem-classification.md` (authoritative verdicts; the integrator must not re-judge)
- `problem-surfaces.md` (original surface text for quoting)
- `problem.md` (target of integration)
- `problem-alignment.md` (target for axis-table updates)

The agent updates:
- `problem.md` (new sections for `new-axis` verdicts; expanded sections for `axis-expansion` verdicts)
- `problem-alignment.md` (new rows in the axis reference table for `new-axis` verdicts)

**Important:** The updated problem definition does not trigger a re-run of Stage 1 in this cycle. The new axes will be evaluated in the next full cycle after the proposer has had a chance to address them.

### Stage 2: Philosophy Alignment Review

Read `problem-review.md` and extract the **Axes aligned** list.

If there are no aligned axes (every axis is unaddressed, misaligned, constraint-acknowledged, or out of scope), skip Stage 2 — there is nothing to review for philosophy alignment.

If there are aligned axes, run a sub-agent with the instructions in `philosophy-alignment.md`.

Provide the agent with:
- `philosophy.md` (the product philosophy)
- `proposal.md` (the current proposal)
- `problem-review.md` (so the agent knows which axes to review)

The agent writes:
- `philosophy-review.md` (alignment findings — always written)
- `philosophy-surfaces.md` (new philosophical concerns — only written if surfaces are found)

### Stage 2b: Philosophy Expansion (split: classify → integrate)

Check whether `philosophy-surfaces.md` was produced by Stage 2.

If it was not produced, skip this stage entirely — no new philosophical concerns were discovered.

If it was produced, run two sub-agents in sequence: **Stage 2b-classify (judge)** then **Stage 2b-integrate (synthesis)**. The split enforces the `~/ai/models/roles.md` rule that opus never synthesizes; classification judgment runs on `claude-opus`, integrated philosophy text synthesis runs on `gpt-high`. The user-input gate (`philosophy-decisions.md`) is owned by classify, not by integrate.

#### Stage 2b-classify

Run a sub-agent with the instructions in `philosophy-expansion-classify.md` (model: `claude-opus`).

Provide the agent with:
- `philosophy-surfaces.md` (the new concerns)
- `philosophy.md` (the current philosophy)
- `philosophy-alignment.md` (the Stage 2 instructions)

The agent writes:
- `philosophy-classification.md` (per-concern verdict: A — absorbable, B — compatible addition, C — tension, D — new-axis, E — contradiction)
- `philosophy-decisions.md` (only if any concern is C, D, or E — these require user input and the orchestrator surfaces this artifact to the root as a NEEDS_INPUT new-value-question per `~/ai/conventions/agent-questions-and-session-graph.md`)

The `philosophy-decisions.md` gate remains the domain artifact for C/D/E concerns. If a direct `AskUserQuestion` attempt for a human-owned value/scope/trade-off question is permission-denied, follow `~/ai/conventions/agent-questions-and-session-graph.md` § `AskUserQuestion Permission-Denial` and return `NEEDS_INPUT:<absolute_artifact_path>` with the question artifact; procedural permission-denial that the orchestrator can resolve from supplied inputs stays inline.

If `philosophy-decisions.md` was written, halt the cycle after this sub-stage and surface the artifact to the root. Stage 2b-integrate runs on the next cycle after the user has answered.

#### Stage 2b-integrate

Skip if `philosophy-decisions.md` was written by Stage 2b-classify (the user-input gate takes precedence; the cycle resumes on the next round).

Skip if `philosophy-classification.md` contains no A and no B verdicts (every concern requires user input or every concern was already absorbed elsewhere).

Otherwise, run a sub-agent with the instructions in `philosophy-expansion-integrate.md` (model: `gpt-high`).

Provide the agent with:
- `philosophy-classification.md` (authoritative verdicts; the integrator must not re-judge)
- `philosophy-surfaces.md` (original concern text for quoting)
- `philosophy.md` (target of integration)

The agent:
- Applies absorbable clarifications/extensions for each A verdict (modifies the cited principle in `philosophy.md`).
- Drafts new principles for each B verdict (adds to `philosophy.md`, marked provisional).
- Does NOT integrate C, D, or E verdicts — those live in `philosophy-decisions.md` and are user-owned.
- Does NOT modify `philosophy-decisions.md`.

---

## Run Report

After all stages complete, produce the run report.

### Alignment findings

Evaluate whether the alignment review is clean.

A **clean alignment** means ALL of the following:
- **Zero unaddressed axes** in the problem review — every problem in the problem definition is engaged with somehow
- **Zero misalignments** in the problem review — every engaged axis is aimed at the right problem
- **Zero incomplete constraint acknowledgments** in the problem review
- **Zero violations** in the philosophy review — every aligned axis embodies the philosophy
- **Zero ungrounded decisions** in the philosophy review — every design decision traces to a principle
- **Zero structural concerns** in the philosophy review

### Expansion activity

Report what the expansion agents did:

- **Problem definition expanded:** yes/no. If yes, list new axes added and existing axes expanded.
- **Philosophy expanded:** yes/no. If yes, list principles clarified, new principles added, and whether `philosophy-decisions.md` was produced.
- **Bootstrap prelude:** ran/skipped. If ran, list whether `problem-bootstrap.md` and/or `philosophy-bootstrap.md` produced seed artifacts.
- **User input required:** yes/no. If `philosophy-decisions.md` exists, the user must resolve the decisions before the next cycle can produce a clean run.

### Summary

If alignment is clean and no expansion occurred:
> **Clean run. All problems addressed. All aligned. All philosophy-consistent.**

If alignment is clean but expansion occurred:
> **Alignment clean, but problem definition and/or philosophy were expanded. Next cycle will review the proposal against the expanded definitions. Run the proposer to address any new axes, then signal for a new cycle.**

If alignment is not clean, report the findings:
1. Count of unaddressed axes (list them)
2. Count of misalignments (list the axes)
3. Count of constraint blind spots (list the axes)
4. Count of philosophy violations (list the axes and principles)
5. Count of ungrounded decisions (list the axes)
6. Count of structural concerns

If expansion also occurred, append the expansion report.

If `philosophy-decisions.md` was produced:
> **User input required before next cycle.** Review `philosophy-decisions.md` and resolve each decision. The philosophy expansion agent cannot proceed without your direction on [list the decisions].

---

## Iteration

After the run report:

1. **If user input is required** (`philosophy-decisions.md` exists): The user resolves the decisions. The philosophy expansion agent applies the resolutions to `philosophy.md`. Then proceed to step 2.

2. The user takes `problem-review.md` and `philosophy-review.md` to the proposer (manually or via the proposer agent using `proposer.md`). If the problem definition was expanded, the user should also inform the proposer of the new axes.

3. The proposer updates `proposal.md`.

4. The user signals the orchestrator that a new `proposal.md` is ready.

5. The orchestrator runs the full process again from Stage 1.

Repeat until clean run with no expansion.

---

## What this orchestrator does NOT do

- **Does not run the proposer.** The user manages proposal updates.
- **Does not make judgment calls about findings.** The orchestrator runs the review and expansion agents and reports their output. It does not filter, prioritize, or dismiss findings.
- **Does not skip Stage 1 on subsequent runs.** Every run re-evaluates from scratch. A previously aligned axis may become misaligned if the proposal changed.
- **Does not resolve philosophy decisions.** When the philosophy expansion agent identifies tensions, new axes, or contradictions, only the user can decide the direction. The orchestrator surfaces these decisions; it does not make them.
- **Does not re-run Stage 1 after problem expansion within the same cycle.** New problem axes are evaluated in the next cycle, after the proposer has addressed them.
