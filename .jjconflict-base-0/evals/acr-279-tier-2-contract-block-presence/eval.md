---
eval_id: acr-279-tier-2-contract-block-presence
behavior_class: Tier 2 operator contract-block presence and schema validity
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

# ACR-279 Tier 2 Contract Block Presence

## Eval identity

This WRITE-state eval spec defines the future structural-verification contract for ACR-279 Tier 2 operator contract backfill. Source authority is `/home/nes/ai/planning/acr-279-operator-contract-rollout/contracts/acr-279-operator-contract-rollout.md` sections 2.2, 5, 6, and 8, the proposal, the problem map, the hookpoint research, `/home/nes/ai/conventions/evals.md`, and `/home/nes/ai/agents/operator-file-format.md` section `Contract block (operator-contract-v1)`.

Structural-verification claim: every Tier 2 audit, review, test, coverage, maintenance, and pipeline-artifact operator in scope has a valid `## Contract` block matching `operator-contract-v1`, with call-interface fields that preserve its documented task variants, output envelopes, error conditions, and delegation boundaries.

## Lifecycle state

WRITE.

This spec is not executable and does not define pytest, fixtures, verifier scripts, or enforcement wiring.

## Declared roles

`validator`, `mapper`

## Inputs the auditor reads

The future auditor reads these Tier 2 operator files:

| Surface | Operator file |
|---|---|
| PR review pipeline | `/home/nes/ai/agents/pr-review-operator.md` |
| PR justification gauntlet | `/home/nes/ai/agents/pr-justification-gauntlet.md` |
| Test audit gate | `/home/nes/ai/agents/test-audit-gate.md` |
| Coverage expansion | `/home/nes/ai/agents/coverage-expansion-operator.md` |
| AGENTS maintenance | `/home/nes/ai/agents/agentsmd-maintenance-orchestrator.md` |
| Pipeline artifact hygiene | `/home/nes/ai/agents/pipeline-artifacts-operator.md` |

The auditor reads `/home/nes/ai/agents/operator-file-format.md` for the schema and `/home/nes/ai/conventions/evals.md` for finding fields and lifecycle.

## Unwanted behavior

The unwanted behavior is Tier 2 drift where any listed file remains prose-only, has no exact `## Contract` H2, has invalid or schema-mismatched YAML, omits call-interface fields, fails to declare mode/task variants, or blurs audit/test/review delegation boundaries into inline procedure.

## Positive evidence

Positive evidence may include:

- Missing `## Contract` or missing fenced YAML under that heading.
- `schema: operator-contract-v1` is absent or not the first YAML key.
- PR review or PR justification contracts omit required PR metadata, diff, threads, report, or role-output inputs.
- Test/coverage contracts omit PASS/PARTIAL/FAIL/BLOCKED outputs, behavior-spec evidence, report paths, or mode distinctions.
- AGENTS maintenance or pipeline-artifact contracts omit artifact paths, report outputs, or child delegation boundaries.
- The contract block contains child operator mechanics rather than only inputs, outputs, errors, side effects, and delegation boundaries.

## Non-fire cases

The eval must not fire on:

- Existing human-readable procedure, stop-condition, or output-contract prose remaining outside the YAML block.
- Additional task descriptions outside the contract when the structured block contains the callable surface.
- Trivial/minimum-body operators outside the Tier 2 list receiving only advisory body-skeleton findings. This carve-out does not reduce the `blocking` severity for the listed Tier 2 high-risk audit/review/test surfaces.

## Pass/fail criteria

Pass: all listed Tier 2 operator files exist and have valid declarative `operator-contract-v1` blocks that cover their documented modes, output envelopes, errors, side effects, and child delegation boundaries.

Fail: any listed file is missing, missing `## Contract`, malformed, schema-mismatched, or incomplete for documented modes. The acceptance finding is `blocking` for new or edited high-risk Tier 2 operators. Missing rich recommended body sections on unrelated trivial operators remain `advisory` per the minimum-body carve-out.

## Required trace fields

| Field | Description |
|---|---|
| `operator_file` | Absolute path of the Tier 2 operator under review. |
| `tier` | `tier-2`. |
| `contract_block_status` | `present`, `missing`, `duplicate`, or `malformed`. |
| `yaml_parse_status` | YAML parse result for the fenced block. |
| `schema_key` | Observed first YAML key and value. |
| `missing_fields` | Required contract fields absent from the live block. |
| `mode_or_task_coverage_status` | Whether documented modes/tasks are represented. |
| `delegation_boundary_status` | Whether child/audit/test delegation boundaries are declared. |
| `procedure_leak_evidence` | Contract fields containing procedure mechanics, if present. |

## Finding schema

Findings preserve the minimum fields from `conventions/evals.md`:

- `eval_id`
- `severity`
- `evidence_paths`
- `summary`
- `suggested_action`
- `confidence`

The finding schema also includes `operator_file`, `tier`, `contract_block_status`, `yaml_parse_status`, `schema_key`, `missing_fields`, `mode_or_task_coverage_status`, `delegation_boundary_status`, and `procedure_leak_evidence`.

`severity` is `HIGH` for missing or malformed Tier 2 contracts and is treated as rollout `blocking`; `MEDIUM` is for partial evidence; `LOW` is for detector uncertainty.

## Suggested action

Return `add-or-repair-operator-contract-block`. The caller should add or repair the Tier 2 contract block without changing the operator's procedural authority.

## Coverage

| Scenario ID | Scenario |
|---|---|
| ACR279-T2-001 | Detect missing contract block on each Tier 2 operator. |
| ACR279-T2-002 | Detect malformed or schema-mismatched Tier 2 contract YAML. |
| ACR279-T2-003 | Detect missing mode/task and output/error coverage. |
| ACR279-T2-004 | Detect missing child delegation boundaries. |
| ACR279-T2-005 | Preserve advisory minimum-body carve-out outside the listed high-risk surfaces. |
