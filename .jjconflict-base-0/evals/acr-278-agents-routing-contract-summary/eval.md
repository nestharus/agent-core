---
eval_id: acr-278-agents-routing-contract-summary
behavior_class: AGENTS routing contract summary and priority backfill
lifecycle_state: WRITE
severity_when_fires: MEDIUM
evidence_source_kinds:
  - agents-trace-json
  - dispatch-prompt
  - agent-log
  - audit-bundle
  - process-tree-audit
  - workflow-report
  - markdown-file
suggested_action_class: revise-agents-routing-summary
---

# ACR-278 AGENTS Routing Contract Summary

## Eval identity

This WRITE-state eval spec defines the future structural-verification contract for ACR-278 `AGENTS.md` routing-row updates, priority-0 contract backfill status, project-wrapper guidance, and the ban on duplicating detailed operator schemas or procedures in the routing catalog. Source authority is the ACR-278 Step 6a contract, approved proposal R2 Test-Intent Track, problem map, coverage inventory, and `/home/nes/ai/conventions/evals.md`.

This spec covers UB-033, UB-034, UB-035, UB-036, and UB-037.

## Lifecycle state

WRITE.

Per `conventions/evals.md`, this file defines the behavior contract only. It does not provide runnable detector code, fixtures, parser adapters, CLI wiring, pytest tests, verifier scripts, or enforcement rollout.

## Unwanted behavior

The unwanted behavior is markdown-file-detectable routing catalog drift where `AGENTS.md` absorbs operator procedure detail, duplicates detailed input schemas already owned by operator `## Contract` blocks, omits priority-0 backfill status, preserves stale frontmatter-only project-wrapper guidance, or fails to point readers to contract blocks as the call-interface source.

The detector should also fire when `AGENTS.md` lacks the file-local `## Declared roles` block required by the Step 6a contract or proposal Declared-roles plan, or when the `AGENTS.md` file-local `## Declared roles` block was modified to a non-conforming role set during the WU edit.

## Positive evidence

Positive evidence may include:

- `AGENTS.md` contains detailed Jira or implementation-pipeline input schemas that conflict with or duplicate operator contracts.
- A Jira operator row does not point to `agents/jira-operator.md` `## Contract` for inputs, defaults, errors, and delegation.
- An implementation-pipeline row summarizes stale Jira input requirements instead of contract-resolution semantics.
- Project-wrapper guidance still says wrappers are only frontmatter, base pointer, and defaults.
- The catalog lacks a priority-0 contract backfill status line for `jira-operator`, `implementation-pipeline-orchestrator`, and `rfq/jira-operator`.
- Routing rows include procedural steps that belong in operator/workflow bodies.
- A Markdown parser detects that `AGENTS.md` lacks a file-local `## Declared roles` block, has a malformed role block, or has role-set drift relative to the expected role classifications from the Step 6a contract and proposal Declared-roles plan.

## Non-fire cases

The eval must not fire on:

- Brief routing rows that identify the operator, purpose, model, and a pointer to the operator `## Contract`.
- A short priority-backfill status line naming which priority-0 files have contracts.
- High-level routing topology, project-layout, or workflow precedence guidance that does not duplicate operator call schemas.
- References to `conventions/bootstrap-pattern.md` closed-path dispatch rather than restating the full wrapper procedure.
- Files outside this spec's touched-component set for ACR-278 declared-role verification.
- `AGENTS.md` having a `## Declared roles` block that matches the contract's expected role set exactly, allowing only ordering tolerance consistent with `~/ai/conventions/code-quality.md` cohesion rules.

## Required trace fields

The future detector must read markdown file snapshots and, when available, saved `agents trace --json`, dispatch prompts, agent logs, workflow reports, process-tree-audit reports, and audit bundles. It must extract:

| UB | Extension fields |
|---|---|
| UB-033 | `agents_md_path`, `procedure_bloat_evidence`, `routing_summary_section` |
| UB-034 | `agents_md_path`, `operator_row`, `contract_ref`, `input_summary_conflicts` |
| UB-035 | `agents_md_path`, `orchestrator_row`, `ticket_input_summary`, `contract_resolution_summary` |
| UB-036 | `agents_md_path`, `project_wrapper_guidance`, `stale_frontmatter_only_rule` |
| UB-037 | `agents_md_path`, `priority_backfill_status`, `operator_catalog_rows` |
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
| UB-033 | `agents_md_path`, `procedure_bloat_evidence`, `routing_summary_section` |
| UB-034 | `agents_md_path`, `operator_row`, `contract_ref`, `input_summary_conflicts` |
| UB-035 | `agents_md_path`, `orchestrator_row`, `ticket_input_summary`, `contract_resolution_summary` |
| UB-036 | `agents_md_path`, `project_wrapper_guidance`, `stale_frontmatter_only_rule` |
| UB-037 | `agents_md_path`, `priority_backfill_status`, `operator_catalog_rows` |
| Declared roles | `touched_file`, `declared_roles_block_present`, `declared_roles_observed`, `declared_roles_expected`, `declared_roles_match` |

`severity` is `MEDIUM` when AGENTS routing rows duplicate or conflict with structured contracts; `HIGH` only if the duplication would direct dispatchers to the wrong operator or credential source; and `LOW` for incomplete evidence or minor stale wording that does not affect routing.

## Suggested action

Return `revise-agents-routing-summary`. The caller should update `AGENTS.md` so it remains a pointer-heavy routing catalog, points operator rows to the owning `## Contract`, records priority-0 contract backfill status, and removes stale detailed input or procedure duplication.

## Coverage

| UB | Scenario ID | Scenario |
|---|---|---|
| UB-033 | ACR278-ARCS-001 | Keep AGENTS as routing/topology instead of procedure host. |
| UB-034 | ACR278-ARCS-002 | Verify Jira row points to contract and avoids stale input summaries. |
| UB-035 | ACR278-ARCS-003 | Verify orchestrator row reflects contract-resolution semantics. |
| UB-036 | ACR278-ARCS-004 | Remove stale frontmatter-only project-wrapper guidance. |
| UB-037 | ACR278-ARCS-005 | Record priority-0 backfill status without procedure duplication. |
| Declared roles | ACR278-ARCS-DR-001 | Verify `AGENTS.md` declares `orchestration`, `accessor`, and `formatter`. |
