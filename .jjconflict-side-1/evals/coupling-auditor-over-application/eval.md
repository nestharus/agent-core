---
eval_id: coupling-auditor-over-application
behavior_class: Coupling-auditor over-application
lifecycle_state: WRITE
severity_when_fires: MEDIUM
evidence_source_kinds:
  - agents-trace-json
  - dispatch-prompt
  - agent-log
  - audit-bundle
  - process-tree-audit
suggested_action_class: revise-proposal
---

# Coupling-Auditor Over-Application

## Eval identity

This is a markdown behavior specification for `coupling-auditor-over-application`, not runnable eval code. It detects A1 coupling or push-pull auditor over-application to markdown-only WUs or doc cross-reference findings that create fixed-point churn.

References: `conventions/evals.md`, `agents/coupling-auditor.md`, `agents/push-pull-auditor.md`, `conventions/code-quality.md`, `conventions/audit-history.md`, and the ACR-174 deletion contract.

## Unwanted behavior

The unwanted behavior is trace-detectable misuse of coupling review: a coupling/push-pull auditor is applied as if documentation cross-references or markdown-only routing prose were code-level uncontrolled-source coupling, causing repeated revise loops without code-level coupling risk.

## Positive evidence

- The WU scope and diff paths are markdown-only or documentation-only.
- A coupling or push-pull auditor dispatch/report targets doc cross-reference structure rather than code-level or deployment-level coupling.
- The report creates a finding that drives repeated revise loops, fixed-point churn, or residual pressure.
- Companion evidence shows no product-code, deployment, or system-coupling risk within the auditor's stated scope.

## Non-fire cases

- Product-code WUs with actual module, dataflow, deployment, or uncontrolled-source coupling evidence.
- Markdown changes that document live system coupling and require companion review.
- Auditor outputs used only as companion evidence without controlling the gate.
- Auditor findings bounded to the auditor's stated scope and resolved without churn.

## Required trace fields

The future eval implementation must read WU scope, diff paths, auditor prompt/report, finding IDs, round history, code-quality disposition, manager authorization, and product-code/deployment evidence by semantic role. It should prefer saved `agents trace --json` plus audit bundles over raw `state.db` schema assumptions.

## Finding shape

The finding preserves `eval_id`, `severity`, `evidence_paths`, `summary`, `suggested_action`, and `confidence`. Extensions may include `auditor`, `finding_ids`, `diff_paths`, `churn_rounds`, `scope_type`, and `manager_authorization_path`.

## Suggested action

Return `revise-proposal` when over-application causes workflow churn. The owning workflow should revise the review scope, use the auditor only as companion evidence, or route code-level coupling work to a correctly scoped WU.

## Lifecycle notes

ACR-175 seeds this eval in `WRITE`. Downstream implementation tickets own runnable detector code, fixtures, rollout in advisory mode, false-positive review, and enforcement readiness. This spec must not become a structural markdown test or wire itself into `AGENTS.md`, `workflows/index.json`, CI, cron, Jira, Linear, or agent-runner runtime code.
