---
eval_id: acr-278-project-wrapper-contract-bootstrap
behavior_class: Project wrapper contract bootstrap and RFQ wrapper inheritance
lifecycle_state: WRITE
severity_when_fires: HIGH
evidence_source_kinds:
  - agents-trace-json
  - dispatch-prompt
  - agent-log
  - audit-bundle
  - process-tree-audit
  - workflow-report
  - markdown-file
suggested_action_class: update-wrapper-bootstrap-contract
---

# ACR-278 Project Wrapper Contract Bootstrap

## Eval identity

This WRITE-state eval spec defines the future structural-verification contract for ACR-278 RFQ wrapper inheritance, RFQ defaults and routing, bootstrap-pattern wrapper shape, closed-path contract read order, and project-bootstrap wrapper emission and validation. Source authority is the ACR-278 Step 6a contract, approved proposal R2 Test-Intent Track, problem map, coverage inventory, and `/home/nes/ai/conventions/evals.md`.

This spec covers UB-014, UB-016, UB-017, UB-018, UB-019, UB-029, UB-030, UB-031, UB-032, UB-049, UB-050, and UB-051.

## Lifecycle state

WRITE.

Per `conventions/evals.md`, this file defines the behavior contract only. It does not provide runnable detector code, fixtures, parser adapters, CLI wiring, pytest tests, verifier scripts, or enforcement rollout.

## Unwanted behavior

The unwanted behavior is markdown-file-detectable or trace-detectable wrapper bootstrap drift where the RFQ Jira wrapper does not expose base inheritance and local defaults through a machine-readable `## Contract`, wrapper routing and workflow facts disappear during contract backfill, closed-path dispatch bypasses the wrapper contract, wrappers re-inline base procedures, or project-bootstrap emits or validates wrappers without required contract blocks.

The detector should also fire when a touched file lacks the file-local `## Declared roles` block required by the Step 6a contract or proposal Declared-roles plan, or when an existing file-local `## Declared roles` block was modified to a non-conforming role set during the WU edit.

## Positive evidence

Positive evidence may include:

- `/home/nes/projects/rfq/agents/jira-operator.md` lacks `inherits:` or `base_procedure:` in its contract block.
- RFQ board routing, hierarchy/link rules, tickets-first status flow, branch naming, or label collision avoidance are lost or contradicted.
- The RFQ wrapper contract omits `schema: operator-contract-v1`, `must_delegate`, or `forbidden_direct`.
- `conventions/bootstrap-pattern.md` keeps only frontmatter/base/default wrapper shape and does not require contract-block defaults and closed-path contract read order.
- Closed-path dispatch rediscovers stable facts or uses a base operator before reading a current wrapper contract.
- A project wrapper re-inlines base procedure instead of carrying inheritance, defaults, overrides, and delegation boundaries.
- `workflows/project-bootstrap.md` emits or refreshes wrappers without valid `## Contract` blocks, or closed-path validation does not check the wrapper contract.
- A Markdown parser detects that `/home/nes/projects/rfq/agents/jira-operator.md`, `conventions/bootstrap-pattern.md`, or `workflows/project-bootstrap.md` lacks a file-local `## Declared roles` block, has a malformed role block, or has role-set drift relative to the expected role classifications from the Step 6a contract and proposal Declared-roles plan.

## Non-fire cases

The eval must not fire on:

- Thin wrappers that point to a base procedure and declare local defaults, inheritance, and delegation boundaries without copying base procedure steps.
- RFQ routing and hierarchy prose remaining below the contract as procedural or local context.
- Open-path bootstrap using the general operator first when no current wrapper exists, then emitting or refreshing a wrapper with a valid contract.
- Closed-path fallback to the shared operator after documented stale-wrapper or missing-wrapper handling.
- ACR-278 priority-0 RFQ wrapper migration while broader RFQ wrapper migration remains deferred to later work.
- Files outside this spec's touched-component set for ACR-278 declared-role verification.
- A touched file whose `## Declared roles` block matches the contract's expected role set exactly, allowing only ordering tolerance consistent with `~/ai/conventions/code-quality.md` cohesion rules.

## Required trace fields

The future detector must read markdown file snapshots and, when available, saved `agents trace --json`, dispatch prompts, agent logs, workflow reports, process-tree-audit reports, and audit bundles. It must extract:

| UB | Extension fields |
|---|---|
| UB-014 | `wrapper_file`, `base_procedure`, `inherits_status` |
| UB-016 | `wrapper_file`, `routing_rules`, `default_project` |
| UB-017 | `wrapper_file`, `hierarchy_rules`, `link_types`, `create_parent_rule` |
| UB-018 | `wrapper_file`, `tickets_first_status_flow`, `branch_naming`, `label_forbidden` |
| UB-019 | `wrapper_file`, `contract_version`, `inherits`, `must_delegate`, `forbidden_direct` |
| UB-029 | `bootstrap_convention_path`, `open_path_rule`, `wrapper_emission_rule` |
| UB-030 | `bootstrap_convention_path`, `closed_path_rule`, `wrapper_dispatch_first` |
| UB-031 | `bootstrap_convention_path`, `wrapper_shape`, `procedure_reinline_detected` |
| UB-032 | `bootstrap_convention_path`, `contract_block_required`, `closed_path_contract_read` |
| UB-049 | `project_bootstrap_workflow`, `emission_steps`, `wrapper_contract_emitted` |
| UB-050 | `project_bootstrap_workflow`, `closed_path_steps`, `wrapper_contract_validated` |
| UB-051 | `project_bootstrap_workflow`, `contract_block_required`, `base_contract_inheritance` |
| Declared roles | `touched_file`, `declared_roles_block_present`, `declared_roles_observed`, `declared_roles_expected`, `declared_roles_match` |

## Finding schema

Findings preserve the minimum fields from `conventions/evals.md`:

- `eval_id`
- `severity`
- `evidence_paths`
- `summary`
- `suggested_action`
- `confidence`

The finding schema also includes these exact per-behavior extension field sets:

| UB | Extension fields |
|---|---|
| UB-014 | `wrapper_file`, `base_procedure`, `inherits_status` |
| UB-016 | `wrapper_file`, `routing_rules`, `default_project` |
| UB-017 | `wrapper_file`, `hierarchy_rules`, `link_types`, `create_parent_rule` |
| UB-018 | `wrapper_file`, `tickets_first_status_flow`, `branch_naming`, `label_forbidden` |
| UB-019 | `wrapper_file`, `contract_version`, `inherits`, `must_delegate`, `forbidden_direct` |
| UB-029 | `bootstrap_convention_path`, `open_path_rule`, `wrapper_emission_rule` |
| UB-030 | `bootstrap_convention_path`, `closed_path_rule`, `wrapper_dispatch_first` |
| UB-031 | `bootstrap_convention_path`, `wrapper_shape`, `procedure_reinline_detected` |
| UB-032 | `bootstrap_convention_path`, `contract_block_required`, `closed_path_contract_read` |
| UB-049 | `project_bootstrap_workflow`, `emission_steps`, `wrapper_contract_emitted` |
| UB-050 | `project_bootstrap_workflow`, `closed_path_steps`, `wrapper_contract_validated` |
| UB-051 | `project_bootstrap_workflow`, `contract_block_required`, `base_contract_inheritance` |
| Declared roles | `touched_file`, `declared_roles_block_present`, `declared_roles_observed`, `declared_roles_expected`, `declared_roles_match` |

`severity` is `HIGH` when wrapper inheritance, RFQ defaults, closed-path wrapper-first behavior, or project-bootstrap contract emission is missing; `MEDIUM` when wrapper context is partially present but contract-read ordering is ambiguous; and `LOW` only for incomplete evidence or future trace-adapter uncertainty.

## Suggested action

Return `update-wrapper-bootstrap-contract`. The caller should update the RFQ wrapper, bootstrap convention, or project-bootstrap workflow so wrapper contracts declare inheritance, defaults, delegation boundaries, and closed-path read order without re-inlining base operator procedure.

## Coverage

| UB | Scenario ID | Scenario |
|---|---|---|
| UB-014 | ACR278-PWCB-001 | Verify RFQ wrapper base procedure and inheritance are machine-readable. |
| UB-016 | ACR278-PWCB-002 | Preserve RFQ board routing and default project context. |
| UB-017 | ACR278-PWCB-003 | Preserve RFQ hierarchy, link types, and create-parent rule. |
| UB-018 | ACR278-PWCB-004 | Preserve RFQ tickets-first flow, branch naming, and label rule. |
| UB-019 | ACR278-PWCB-005 | Verify RFQ wrapper operator-contract-v1 block and delegation boundaries. |
| UB-029 | ACR278-PWCB-006 | Verify bootstrap open path emits wrappers from stable facts. |
| UB-030 | ACR278-PWCB-007 | Verify bootstrap closed path dispatches the wrapper first. |
| UB-031 | ACR278-PWCB-008 | Verify wrapper shape stays thin and does not re-inline procedure. |
| UB-032 | ACR278-PWCB-009 | Verify bootstrap-pattern requires contract blocks and closed-path reads. |
| UB-049 | ACR278-PWCB-010 | Verify project-bootstrap wrapper emission includes contract blocks. |
| UB-050 | ACR278-PWCB-011 | Verify project-bootstrap closed path validates wrapper contracts. |
| UB-051 | ACR278-PWCB-012 | Verify project-bootstrap contract requirement and base inheritance. |
| Declared roles | ACR278-PWCB-DR-001 | Verify `/home/nes/projects/rfq/agents/jira-operator.md` declares `accessor`, `mapper`, and `validator`. |
| Declared roles | ACR278-PWCB-DR-002 | Verify `conventions/bootstrap-pattern.md` declares `orchestration`, `validator`, and `formatter`. |
| Declared roles | ACR278-PWCB-DR-003 | Verify `workflows/project-bootstrap.md` declares `orchestration`, `validator`, and `formatter`. |
