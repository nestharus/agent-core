---
eval_id: decomposition-refusal
behavior_class: Decomposition refusal
lifecycle_state: WRITE
severity_when_fires: HIGH
evidence_source_kinds:
  - agents-trace-json
  - dispatch-prompt
  - agent-log
  - audit-bundle
  - process-tree-audit
suggested_action_class: decompose
---

# Decomposition Refusal

## Eval identity

This is a markdown behavior specification for `decomposition-refusal`, not runnable eval code. It detects oscillation criteria, including two non-converging revise rounds, followed by a third round or residual acceptance instead of decomposition.

References: `conventions/evals.md`, `conventions/audit-history.md`, `conventions/code-quality.md`, `agents/implementation-pipeline-orchestrator.md`, active manager flavor files, and the ACR-174 deletion contract.

## Unwanted behavior

The unwanted behavior is trace-detectable refusal to decompose: repeated unresolved findings meet the workflow's oscillation threshold, but the run continues into another revise loop or accepts residual risk rather than decomposing, shrinking, or stopping.

## Positive evidence

- Audit history records round numbers, repeated finding IDs, stable unresolved risk, or non-convergence classification.
- Prior finding counters show the threshold has been met.
- The selected next action is a third revise round, acceptance, merge, or continue decision.
- No valid decomposition artifact, scope shrink, or manager-authorized alternative exists.

## Non-fire cases

- Findings converge within the allowed rounds.
- Autonomous decomposition or scope shrink is performed when the threshold is met.
- The manager authorizes a specific exception before the threshold action.
- Repeated text is historical context and not a current unresolved finding.

## Required trace fields

The future eval implementation must read audit history, round numbers, prior finding counters, role outputs, decision register entries, selected next action, decomposition artifacts, scope-shrink artifacts, and manager authorization by semantic role. It should prefer saved `agents trace --json` plus audit-history artifacts over raw `state.db` schema assumptions.

## Finding shape

The finding preserves `eval_id`, `severity`, `evidence_paths`, `summary`, `suggested_action`, and `confidence`. Extensions may include `round_count`, `repeated_finding_ids`, `oscillation_classification`, `selected_action`, and `decomposition_artifact_path`.

## Suggested action

Return `decompose` when the trace shows a breached oscillation threshold without valid decomposition or shrink. The owning workflow should split the WU, shrink the scope, or halt for manager-owned disposition.

## Lifecycle notes

ACR-175 seeds this eval in `WRITE`. Downstream implementation tickets own runnable detector code, fixtures, rollout in advisory mode, false-positive review, and enforcement readiness. This spec must not become a structural markdown test or wire itself into `AGENTS.md`, `workflows/index.json`, CI, cron, Jira, Linear, or agent-runner runtime code.
