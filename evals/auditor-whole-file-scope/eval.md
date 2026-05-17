---
id: auditor-whole-file-scope
status: write_state
lifecycle_state: WRITE
risk_class: HIGH
scope: A1 auditor touched-file scope, Phase 2.5 decomposition, and manager/orchestrator anti-scope discipline for ACR-249
behavior_class: Whole touched-file audit ownership and work-narrowing anti-scope rejection
severity_when_fires: HIGH
evidence_source_kinds:
  - agents-trace-json
  - dispatch-prompt
  - agent-log
  - audit-bundle
  - process-tree-audit
  - audit-history
suggested_action_class: revise-proposal-or-decompose
supersedes:
  - acr-246-auditor-scope-convergence
---

# Auditor Whole-File Scope Eval

## Purpose

This WRITE-state eval specification defines the ACR-249 behavior contract for A1 auditor scope after reversing ACR-246's WU-diff-only boundary: auditors run only on files or components touched by the WU diff, but within that touched set they evaluate the whole file/component, and pre-existing A1 findings are current-WU work unless the orchestrator decomposes before dispatch. It also defines the related prompt-policy contract: behavior-forbidding anti-scope remains valid, while work-narrowing anti-scope is itself a finding.

## Scenarios

### Scenario 1: `whole-file-finding-from-single-function-touch`

Risk verified: A1 auditors may continue to inspect only diff lines, changed functions, or WU-owned symbols, preserving the old ACR-246 behavior that residualized true findings in a file the WU touched.

Fixture description: The trace bundle describes a Python source file or Markdown operator file with multiple pre-existing A1 defects before the current WU. The file contains cohesion, function-classification, and coupling or push-vs-pull defects in unchanged functions, declarations, sections, references, or adjacent file-local support code. The current diff touches only one function or one small Markdown section in that same file.

Expected signal: Cohesion, function-classification, coupling, and push-pull findings may cite any relevant part of the whole touched file/component, including unchanged functions, declarations, Markdown sections, or file-local references. The report treats those findings as blocking current-WU findings rather than residual rows merely because they predate the diff. The auditor verdict is `HIGH` or `MEDIUM` according to the relevant threshold regardless of diff size.

Residual risk not verified: This WRITE-state spec does not execute a detector against live traces, prove touched-file discovery for every diff representation, or validate exact threshold math for each A1 auditor.

### Scenario 2: `phase-2-5-decompose-or-own-touched-file`

Risk verified: The implementation pipeline may retain work-narrowing anti-scope or residualization at Phase 2.5 instead of estimating pre-existing touched-file debt and decomposing an oversized WU before the file is touched.

Fixture description: The trace bundle describes a Phase 2.5 run where the problem map, coverage inventory, risk profile, or touched-surface enumeration shows that one candidate touched file has substantial pre-existing A1 debt. The debt is too broad for one coherent WU if that WU also ships the requested behavior change, but the file is still part of the proposed diff surface.

Expected signal: The WU either owns and fixes all A1 findings for that touched file/component or the orchestrator decomposes at Phase 2.5 before dispatching implementation work. A valid decomposition record names the file/component, blocking A1 debt family, why one WU is too large, and the smaller WU boundary. The decision is recorded in audit history or an equivalent planning artifact. The orchestrator surfaces only genuine new-value `NEEDS_INPUT` questions to root; it does not ask the user to accept residual touched-file findings.

Residual risk not verified: This WRITE-state spec does not exercise ticket creation, verify backend write-back fields, or prove decomposed child WUs later reach LOW.

### Scenario 3: `work-narrowing-anti-scope-rejected`

Risk verified: Manager or orchestrator prompts may keep named-file exclusions, named-concern exclusions, `touched behavior only`, `smallest shippable`, or declared-surface language as excuses to leave whole touched-file findings unresolved.

Fixture description: The trace bundle includes a dispatch-prompt example with both behavior-forbidding clauses and work-narrowing clauses. Behavior-forbidding clauses include no residual acceptance, no precedent-citation, no idle timeouts, no sentinel polling, no watcher shortcuts, no pytest smuggling, and no unauthorized ticket or repo mutations. Work-narrowing clauses include "do not touch file X," "no scope expansion to concern Y," "only update the changed function," "leave adjacent cleanup out of scope," or "fix touched behavior only" when the excluded work is inside a touched file/component.

Expected signal: Behavior-forbidding clauses pass and remain part of a valid prompt. Work-narrowing clauses are findings when they exclude required A1 cleanup inside touched files/components or predeclare a narrower audit target than the diff will create. The valid response is prompt/proposal revision or Phase 2.5 decomposition, not residual acceptance, stable-MEDIUM acceptance, or post-merge cleanup without decomposition.

Residual risk not verified: This WRITE-state spec does not implement a prompt-corpus scanner, classify every possible work-narrowing phrase, or replace manager-flavor drift evals.

### Scenario 4: `acr-246-inverse-eval-superseded`

Risk verified: Future reviewers may cite the ACR-246 eval's old residual expectation as live policy and use it to downgrade pre-existing A1 findings inside touched files.

Fixture description: The trace bundle includes the old eval metadata for `acr-246-auditor-scope-convergence`, especially scenarios that expected broader old functions in a touched file to remain residual, and the new `auditor-whole-file-scope` lifecycle note or frontmatter that declares supersession for scope-boundary behavior.

Expected signal: `acr-246-auditor-scope-convergence` is explicitly marked superseded for scope-boundary behavior by `auditor-whole-file-scope`. Its historical scenarios remain readable but are not authoritative for touched-file ownership after ACR-249. Future reviewers and eval runners treat ACR-246's F1/S1/S5 residual expectation as reversed for files/components touched by the current WU.

Residual risk not verified: This WRITE-state spec does not implement a runtime eval registry, enforce supersession ordering, or update historical audit reports that already cited ACR-246.

## Cross-references

- ACR-249: Reverse anti-scope-as-WU-narrowing; audit whole files/systems; decompose WUs when too large.
- ACR-246: Inverse WU-diff-only auditor-scope behavior superseded by this eval for touched-file scope boundaries.
- AGE-103 / AGE-116 / AGE-122 / AGE-123: Empirical chain for auditor oscillation, ACR-246 tightening, downstream edge cases, and touched-file debt ownership.
- `conventions/code-quality.md`: Canonical source for touched-file ownership, auditor scope boundary, LOW-only disposition, bootstrap exception, and anti-scope discipline.
- `conventions/risk-profile.md`, `workflows/code-quality.md`, `workflows/implementation-pipeline.md`, and `agents/implementation-pipeline-orchestrator.md`: Process surfaces expected to apply this eval's Phase 2.5 and code-quality gate behavior.
- `agents/work-manager-operator.md` and manager flavor files: Prompt-authoring surfaces expected to preserve behavior-forbidding anti-scope while rejecting work-narrowing anti-scope.
