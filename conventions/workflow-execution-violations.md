# Workflow Execution Violations

Use this taxonomy when reviewing whether a workflow, operator, gate, or delegated process tree executed as required.

This convention classifies execution validity. It does not replace code review, design review, value review, human scope decisions, or Tier-3 approval.

## Evidence Sources

Classify each finding by evidence source:

- `tree`: proven directly from process-tree metadata such as node identity, parent/child relationship, model/source, status, timing, warnings, or session state.
- `companion`: proven from prompts, logs, reports, expected outputs, workflow-local state, or audit history.
- `inferred`: supported by combining tree and companion evidence.
- `missing`: required evidence is absent.

Audited-run narrative notes or rationale are not valid `tree`, `companion`, or `inferred` evidence for workflow-audit PASS.

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

Report-emission examples include: canonical PDF missing when a report bundle is required; Product, Engineering, or Investigative report missing from a coverage-expansion run; screenshot artifact missing for a UI-touching test, bug, or report claim; non-UI evidence artifact missing for a backend-only behavior claim; or `reports/report-index.md` missing, malformed, stale, or not tied to the expected process node.

### 3. Gate/termination violation

Workflow advanced after a non-passing model or human gate, ignored a required return-to-research signal, or ignored a terminate/close signal.

Default severity: `blocking`.

### 4. Role/independence violation

Wrong role or model for a stage, self-review, same agent used where separation is required, or review performed by the executing agent.

Default severity: `blocking` when the workflow names the role/model/separation requirement; otherwise `needs_input`.

### 5. Routing/scope violation

Wrong workflow/operator selected for the cue, ambiguity not escalated, or work drifted outside the stated purpose or execution spec.

Default severity: `blocking` for material drift or wrong routing; `advisory` for incidental polish that the workflow permits.

### 5b. Implicit manager-flavor drift

Manager-layer answer selection used flavor-specific behavior without declaring or loading the active manager flavor policy.

Default severity: `blocking`.

Canonical example: a manager session answers a Phase 4 code-quality HIGH halt with "accept residual + advance" as a speed shortcut without declaring `manager-hackerman`, loading `work-manager-operator-hackerman.md`, or recording active flavor evidence.

Resolution: declare the flavor explicitly (`manager-max | manager-pragmatic | manager-hackerman`); when no flavor is declared, default to `manager-max`; load the matching flavor file; re-answer the affected manager-layer question from that file's prescription table. Wrong or unapplied manager-layer NEEDS_INPUT answers may also trigger `### 11. Question/answer handling violation`.

### 6. Evidence/grounding violation

Required citations, primary-source evidence, evidence traces, grounding steps, inspected files, or research artifacts are absent.

Default severity: `blocking` when the claim affects a recommendation, gate, design, or handoff; otherwise `advisory`.

Report-emission grounding examples include: a code claim lacks `file_path:line_number`; a code claim lacks the exact fenced code block that supports it; a discovered-bug report lacks the strict-xfail marker, behavior-source commit hash, failing behavior, production-code excerpt, screenshot or non-UI evidence, or intended-versus-actual explanation required by `~/ai/conventions/test-reports.md`.

### 7. Parallelism/isolation violation

Concurrent writers used the same worktree or project root when isolation was required.

Default severity: `blocking` for concurrent tracked-file writers. Shared-root `.tmp/` or `.build/` only research runs follow the local workflow rule.

### 8. History/liveness violation

Required audit history was not maintained, stale work repeated, oscillation was not classified, a loop continued without convergence criteria, or a prior finding was weakened/regressed without triggering the required loop decision.

Default severity: `blocking` in a required multi-round loop; otherwise `needs_input`.

### 9. Silent-success / false-completion violation

An agent reports success, a trace node succeeds, or a workflow appears complete while required work, output, evidence, or verification is absent.

For Phase 6 firstness, this class includes a workflow that reports Step 6b complete, Step 6c consumable, Phase 6 complete, or PR-review-ready while required firstness work, output, evidence, or verification is absent or contradicted.

Examples include: missing Step 6b or Step 6c expected-process entries; the same invocation mapped to both Step 6b and Step 6c; Step 6c running before Step 6b outputs existed; missing, malformed, stale, or unmapped Step 6b output index; missing Step 6c consumption evidence; Step 6b prompt/log evidence that the test writer saw implementation context; or downstream advancement while required firstness evidence was absent without surfacing `NEEDS_INPUT:<question_artifact>`.

Report-emission false-completion examples include: a PR comment presents itself as the canonical report instead of linking to the PDF bundle; an agent reports report generation complete while a required PDF, screenshot, non-UI evidence artifact, or report-index entry is absent; or workflow synthesis advances while required report artifacts are missing without surfacing `NEEDS_INPUT`.

Default severity: `blocking`.

### 10. Forbidden partial-work violation

Unauthorized stubs, silent placeholders, partial migrations, backwards-compatibility shims, or other forbidden partial work were left in the repo or handoff.

Default severity: `blocking`.

### 11. Question/answer handling violation

A sub-agent emitted a question artifact that the root did not surface, the workflow advanced while a blocking question was unanswered, an answer artifact was received but not applied to the originating work, continuation used the wrong session/graph, or resume/fallback evidence is missing.

Default severity: `blocking` when the unanswered or unapplied question affects any downstream workflow input, gate, user-facing output, branch mutation, PR action, or approval. `needs_input` when required question, answer, or continuation evidence is absent. `advisory` only for non-blocking display metadata defects that do not affect the answer contract or continuation target.

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
