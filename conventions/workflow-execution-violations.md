# Workflow Execution Violations

Use this taxonomy when reviewing whether a workflow, operator, gate, or delegated process tree executed as required.

This convention classifies execution validity. It does not replace code review, design review, value review, human scope decisions, or Tier-3 approval.

## Evidence Sources

Classify each finding by evidence source:

- `tree`: proven directly from process-tree metadata such as node identity, parent/child relationship, model/source, status, timing, warnings, or session state.
- `companion`: proven from prompts, logs, reports, expected outputs, workflow-local state, or audit history.
- `inferred`: supported by combining tree and companion evidence.
- `missing`: required evidence is absent.

When a required review depends on missing evidence, fail closed with `NEEDS_INPUT` or a blocking violation. Do not convert missing evidence into a pass.

## Severity Defaults

Use these severities unless a workflow states a stricter rule:

- `blocking`: downstream workflow cannot trust, consume, post, open, promote, or hand off the output.
- `advisory`: record and continue; the output remains usable.
- `needs_input`: required evidence is missing or too vague to classify.

Human-owned gates remain human-owned. A model process reviewer can flag a human-gate or Tier-3 bypass, but it does not approve the human-owned action.

## Canonical Classes

### 1. Procedure-step violation

Required step skipped, unjustifiably omitted, performed out of order, or replaced by a summary.

Default severity: `blocking`.

Advisory only when the workflow documents a valid skip condition and the skip evidence is present.

### 2. Output/artifact violation

Required artifact, status, verdict, or required section is missing, malformed, stale, or not tied to the expected process node.

Default severity: `blocking`.

### 3. Gate/termination violation

Workflow advanced after a non-passing model or human gate, ignored a required return-to-research signal, or ignored a terminate/close signal.

Default severity: `blocking`.

### 4. Role/independence violation

Wrong role or model for a stage, self-review, same agent used where separation is required, or review performed by the executing agent.

Default severity: `blocking` when the workflow names the role/model/separation requirement; otherwise `needs_input`.

### 5. Routing/scope violation

Wrong workflow/operator selected for the cue, ambiguity not escalated, or work drifted outside the stated purpose or execution spec.

Default severity: `blocking` for material drift or wrong routing; `advisory` for incidental polish that the workflow permits.

### 6. Evidence/grounding violation

Required citations, primary-source evidence, evidence traces, grounding steps, inspected files, or research artifacts are absent.

Default severity: `blocking` when the claim affects a recommendation, gate, design, or handoff; otherwise `advisory`.

### 7. Parallelism/isolation violation

Concurrent writers used the same worktree or project root when isolation was required.

Default severity: `blocking` for concurrent tracked-file writers. Shared-root `.tmp/` or `.build/` only research runs follow the local workflow rule.

### 8. History/liveness violation

Required audit history was not maintained, stale work repeated, oscillation was not classified, a loop continued without convergence criteria, or a prior finding was weakened/regressed without triggering the required loop decision.

Default severity: `blocking` in a required multi-round loop; otherwise `needs_input`.

### 9. Silent-success / false-completion violation

An agent reports success, a trace node succeeds, or a workflow appears complete while required work, output, evidence, or verification is absent.

Default severity: `blocking`.

### 10. Forbidden partial-work violation

Unauthorized stubs, silent placeholders, partial migrations, backwards-compatibility shims, or other forbidden partial work were left in the repo or handoff.

Default severity: `blocking`.

## Reporting Requirements

Each finding records:

- violation class
- severity
- evidence source
- workflow location
- affected node UUID or artifact path when available
- one-sentence summary
- required next action

Reports should include only the evidence needed for downstream trust. Do not paste full process trees or long logs when node IDs and artifact paths are enough.
