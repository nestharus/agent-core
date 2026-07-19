---
eval_id: cohesion-auditor-over-application
behavior_class: Cohesion-auditor over-application
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

# Cohesion-Auditor Over-Application

## Eval identity

This is a markdown behavior specification for `cohesion-auditor-over-application`, not runnable eval code. It detects A1 cohesion-auditor over-application to intrinsically mixed-role orchestrator files where mixed concerns are required by the operator's role.

References: `conventions/evals.md`, `agents/cohesion-auditor.md`, `conventions/code-quality.md`, `conventions/audit-history.md`, relevant orchestrator/operator role docs, and the ACR-174 deletion contract.

## Unwanted behavior

The unwanted behavior is trace-detectable misuse of cohesion review: an intrinsically mixed-role orchestrator/operator file is flagged as incohesive solely because it coordinates multiple required phases, roles, or gates that are part of its documented contract.

## Positive evidence

- The touched file is an orchestrator or operator whose role contract requires mixed coordination responsibilities.
- A cohesion auditor dispatch/report produces a `HIGH` or blocking finding based on that expected role mixture.
- The finding drives a revise loop, decomposition pressure, or residual acceptance pressure.
- Role-contract evidence shows the mixed concerns are required by the operator's purpose rather than accidental file drift.

## Non-fire cases

- Ordinary product modules with avoidable mixed responsibilities.
- Orchestrator changes that truly exceed the documented role contract.
- Cohesion reports used as companion evidence without controlling the gate.
- Findings that identify separable concerns not required by the orchestrator role.

## Required trace fields

The future eval implementation must read touched files, file role/category, auditor prompt/report, finding IDs, phase/gate decision, round history, and role-contract evidence by semantic role. It should prefer saved `agents trace --json` plus auditor reports over raw `state.db` schema assumptions.

## Finding shape

The finding preserves `eval_id`, `severity`, `evidence_paths`, `summary`, `suggested_action`, and `confidence`. Extensions may include `auditor`, `file_role`, `finding_ids`, `role_contract_path`, `round_history_path`, and `selected_action`.

## Suggested action

Return `revise-proposal` when cohesion review is over-applied to required orchestrator role mixture. The owning workflow should revise the review target, cite the role contract, or split only concerns that are genuinely outside the role.

## Lifecycle notes

ACR-175 seeds this eval in `WRITE`. Downstream implementation tickets own runnable detector code, fixtures, rollout in advisory mode, false-positive review, and enforcement readiness. This spec must not become a structural markdown test or wire itself into `AGENTS.md`, `workflows/index.json`, CI, cron, Jira, Linear, or agent-runner runtime code.
