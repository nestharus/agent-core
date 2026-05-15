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

Examples include: missing Step 6b or Step 6c expected-process entries; the same invocation mapped to both Step 6b and Step 6c; Step 6c running before Step 6b outputs existed; missing, malformed, stale, or unmapped Step 6b output index; missing or contradicted relaxed-position Step 6c `consumed:` evidence for the Step 6b output index and implemented Step 6b output-index rows; Step 6b prompt/log evidence that the test writer saw implementation context; or downstream advancement while required firstness evidence was absent without surfacing `NEEDS_INPUT:<question_artifact>`.

Report-emission false-completion examples include: a PR comment presents itself as the canonical report instead of linking to the PDF bundle; an agent reports report generation complete while a required PDF, screenshot, non-UI evidence artifact, or report-index entry is absent; or workflow synthesis advances while required report artifacts are missing without surfacing `NEEDS_INPUT`.

Default severity: `blocking`.

### 10. Forbidden partial-work violation

Unauthorized stubs, silent placeholders, partial migrations, backwards-compatibility shims, or other forbidden partial work were left in the repo or handoff.

Default severity: `blocking`.

### 11. Question/answer handling violation

A sub-agent emitted a question artifact that the root did not surface, the workflow advanced while a blocking question was unanswered, an answer artifact was received but not applied to the originating work, continuation used the wrong session/graph, or resume/fallback evidence is missing.

Default severity: `blocking` when the unanswered or unapplied question affects any downstream workflow input, gate, user-facing output, branch mutation, PR action, or approval. `needs_input` when required question, answer, or continuation evidence is absent. `advisory` only for non-blocking display metadata defects that do not affect the answer contract or continuation target.

### Named anti-pattern: Non-LOW gate residual acceptance

Pattern: a manager session, implementation-pipeline orchestrator, or review loop treats a pipeline-callable LOW-only gate result of `HIGH` or `MEDIUM` as an accepted `residual`, answers a `NEEDS_INPUT` halt with accept-and-advance language, records the answer as a `D-AGE-*`, `DECISIONS.md`, or similar policy decision, and advances downstream. Canonical example: the `D-AGE-*` decision family retracted or downgraded by ACR-156 in the ACR-162 retraction lane, including `D-AGE-54`, `D-AGE-61`, `D-AGE-62`, `D-AGE-59` / `D-019`, `D-AGE-28`, `D-AGE-15`, and `D-AGE-4`.

Classification: this is a blocking gate/termination violation under `### 3. Gate/termination violation`. It is also a history/liveness violation under `### 8. History/liveness violation` when oscillation or repeated non-convergence is converted into accepted residual risk, and a question/answer handling violation under `### 11. Question/answer handling violation` when a model-owned remediation/decomposition decision is turned into a manager or root question. It also triggers `### 5b. Implicit manager-flavor drift` when the answer relies on undeclared or unloaded manager flavor policy.

Why it is wrong: the LOW-only advance rule is the mechanism that forces decomposition when LLM evaluation capacity is exceeded. `HIGH` and `MEDIUM` verdicts from pipeline-callable gates are not residuals to accept; they require remediation/revise from current evidence and rerun, then `autonomous decompose` when the owning workflow's convergence rule fires. The manager never accepts a non-LOW pipeline-callable gate residual. Treating one as a residual undermines the LOW-only safety net and ships work that should have been split into smaller WUs.

What to do instead: follow `conventions/code-quality.md` § `Disposition policy` and § `Oscillation signals WU-too-large`, `workflows/code-quality.md` pipeline-callable mode, and `workflows/implementation-pipeline.md` Phase 4 / Phase 6 prototype-risk / per-component code-quality LOW-only rules. Use `conventions/review-convergence.md` for the hard decomposition signal after repeated non-convergence. Manager flavor rows from PR #108, PR #109, and PR #112 (`agents/work-manager-operator-max.md`, `agents/work-manager-operator-pragmatic.md`, `agents/work-manager-operator-hackerman.md`) may route valid manager-layer answers, but loading a flavor file does not override LOW-only pipeline-callable gate semantics; manager never accepts `HIGH` or `MEDIUM` from those gates as residual.

Permitted exception (narrow): the `~/ai/conventions/code-quality.md` § `Bootstrap exception` carve-out is distinct from this anti-pattern. A Phase 4 code-quality `MEDIUM` or `HIGH` aggregate may advance only when the FULL evidence trio is present: (a) the approved Phase 3 proposal contains a `## Bootstrap exception declaration` section enumerating the four conditions, (b) `${worktree_path}/DECISIONS.md` contains a `### <ticket-id> — Bootstrap exception ratification` entry that cites `~/ai/conventions/code-quality.md` § `Bootstrap exception`, and (c) the Phase 4 join manifest carries a `bootstrap-exception` row with `verdict_line=RATIFIED`, `ratifies_gate=code-quality`, and `allow_advance_basis=bootstrap-exception` alongside the actual non-LOW code-quality row. Manager-flavor language, root residual answers, and DECISIONS-only acceptance without the Phase 3 declaration and the Phase 4 manifest row remain blocking violations under this anti-pattern; silent advancement or residual-style acceptance does not become a bootstrap exception by being labelled one.

Recovery direction: work already shipped through this pattern requires a separate recovery audit ticket. The prior residual-acceptance decision is evidence of the violation, not current policy authority — treat the ACR-156 / ACR-162 retraction lane and the `D-AGE-*` family above as exemplars of decisions that must not be cited as authorization for non-LOW gate residual acceptance. Durable detection of this pattern is owned by the ACR-175 eval framework once shipped (see `~/ai/evals/bootstrap-exception/eval.md` for the WRITE-state behavior specification of the missing-or-malformed bootstrap-exception ratification class); until then, the manager flavor tables and process-tree-auditor enforce.

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
