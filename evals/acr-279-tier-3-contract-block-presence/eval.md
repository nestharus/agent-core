---
eval_id: acr-279-tier-3-contract-block-presence
behavior_class: Tier 3 operator contract-block presence and schema validity
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
suggested_action_class: add-or-repair-operator-contract-block
---

# ACR-279 Tier 3 Contract Block Presence

## Eval identity

This WRITE-state eval spec defines the future structural-verification contract for ACR-279 Tier 3 operator contract backfill. Source authority is `/home/nes/ai/planning/acr-279-operator-contract-rollout/contracts/acr-279-operator-contract-rollout.md` sections 2.3, 5, 6, and 8, the proposal, the problem map, the hookpoint research, `/home/nes/ai/conventions/evals.md`, and `/home/nes/ai/agents/operator-file-format.md` section `Contract block (operator-contract-v1)`.

Structural-verification claim: every Tier 3 planning, feature, refactoring, roadmap, and alignment orchestrator in scope has a valid `## Contract` block matching `operator-contract-v1`, with required inputs, outputs, errors, side effects, user gates, and child-delegation boundaries represented as a call interface.

## Lifecycle state

WRITE.

This file defines a reviewable eval spec only. It does not provide runnable detector code, pytest tests, fixtures, parser adapters, or verifier scripts.

## Declared roles

`validator`, `mapper`

## Inputs the auditor reads

The future auditor reads these Tier 3 operator files:

| Surface | Operator file |
|---|---|
| Feature lifecycle | `/home/nes/ai/agents/feature-orchestrator.md` |
| Refactoring cycle | `/home/nes/ai/agents/refactoring-orchestrator.md` |
| Commit-history refactor scoping | `/home/nes/ai/agents/refactoring-commit-history-orchestrator.md` |
| Roadmap cascade | `/home/nes/ai/agents/roadmap-orchestrator.md` |
| Alignment cycle | `/home/nes/ai/agents/alignment-cycle-orchestrator.md` |

The auditor reads `/home/nes/ai/agents/operator-file-format.md` for schema rules and `/home/nes/ai/conventions/evals.md` for lifecycle and finding-contract fields.

## Unwanted behavior

The unwanted behavior is Tier 3 drift where a listed orchestrator lacks a structured `## Contract`, cannot be mechanically called by dispatchers, hides required planning paths or user gates in prose only, omits child-delegation boundaries, or places roadmap/refactoring/alignment procedure mechanics inside the contract YAML.

## Positive evidence

Positive evidence may include:

- Missing exact `## Contract` H2 or missing fenced YAML block.
- YAML parse failure or non-`operator-contract-v1` schema.
- Missing required inputs such as repo/worktree/planning/scratch paths, target scopes, phase scopes, decision artifacts, or strategy documents.
- Missing outputs such as run reports, package descriptors, roadmap documents, classification artifacts, or implementation-pipeline handoff artifacts.
- Missing `must_delegate` entries for implementation-pipeline, proposer, risk, bootstrap, alignment, classify, or integrate children where the operator body declares child dispatch.
- Missing explicit user-gate/error behavior for philosophy decisions, feature-ticket handoffs, or no-behavior-change refactor constraints.
- Procedure details or child mechanics embedded in the contract block.

## Non-fire cases

The eval must not fire on:

- Procedure sections remaining as the authoritative body after the structured call interface is added.
- Strategy or workflow prose that explains user gates, provided the contract block declares the callable inputs/outputs/errors.
- Trivial/minimum-body operators outside the Tier 3 list receiving advisory body-skeleton findings only.

## Pass/fail criteria

Pass: every listed Tier 3 operator exists and has a valid `operator-contract-v1` block that covers documented call inputs, outputs, errors, side effects, user gates, and child-delegation boundaries.

Fail: any listed Tier 3 operator is missing, missing `## Contract`, malformed, schema-mismatched, or incomplete for documented task/delegation surfaces. The finding is `blocking` for ACR-279 because these are edited orchestrators in the rollout surface. The trivial/minimum-body carve-out remains `advisory` only outside this surface.

## Required trace fields

| Field | Description |
|---|---|
| `operator_file` | Absolute path of the Tier 3 operator under review. |
| `tier` | `tier-3`. |
| `contract_block_status` | `present`, `missing`, `duplicate`, or `malformed`. |
| `yaml_parse_status` | YAML parse result for the fenced block. |
| `schema_key` | Observed first YAML key and value. |
| `missing_fields` | Required contract fields absent from the live block. |
| `planning_input_status` | Whether required planning/worktree/scratch inputs are declared. |
| `user_gate_status` | Whether user-owned gates and NEEDS_INPUT/BLOCKED conditions are declared. |
| `delegation_boundary_status` | Whether child dispatch boundaries are declared. |
| `procedure_leak_evidence` | Contract fields containing procedure mechanics, if present. |

## Finding schema

Findings preserve the minimum fields from `conventions/evals.md`:

- `eval_id`
- `severity`
- `evidence_paths`
- `summary`
- `suggested_action`
- `confidence`

The finding schema also includes `operator_file`, `tier`, `contract_block_status`, `yaml_parse_status`, `schema_key`, `missing_fields`, `planning_input_status`, `user_gate_status`, `delegation_boundary_status`, and `procedure_leak_evidence`.

`severity` is `HIGH` for missing or malformed Tier 3 contracts and is treated as rollout `blocking`; `MEDIUM` is for partial evidence; `LOW` is for future trace-adapter uncertainty.

## Suggested action

Return `add-or-repair-operator-contract-block`. The caller should add or repair the contract block while preserving planning/refactoring/roadmap/alignment procedure text outside the YAML block.

## Coverage

| Scenario ID | Scenario |
|---|---|
| ACR279-T3-001 | Detect missing contract block on each Tier 3 operator. |
| ACR279-T3-002 | Detect malformed or schema-mismatched Tier 3 contract YAML. |
| ACR279-T3-003 | Detect missing planning inputs, outputs, and user-gate/error fields. |
| ACR279-T3-004 | Detect missing child-delegation boundaries. |
| ACR279-T3-005 | Detect procedure mechanics placed inside the contract block. |
