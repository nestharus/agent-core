---
eval_id: acr-278-operator-contract-format
behavior_class: Operator contract format and base Jira contract backfill
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
suggested_action_class: add-contract-block
---

# ACR-278 Operator Contract Format

## Eval identity

This WRITE-state eval spec defines the future structural-verification contract for ACR-278 operator-contract-v1 formatting, the base Jira operator contract backfill, Jira per-task contract details, and the central eval-spec seed. Source authority is the ACR-278 Step 6a contract at `/home/nes/ai/planning/acr-278-operator-contract-format/contracts/acr-278-operator-contract-format.md`, the approved proposal R2 at `/home/nes/ai/planning/acr-278-operator-contract-format/proposals/acr-278-ACR-278.md`, the problem map, the coverage inventory, and `/home/nes/ai/conventions/evals.md`.

This spec covers UB-001, UB-002, UB-003, UB-005, UB-006, UB-008, UB-009, UB-010, UB-011, UB-012, UB-013, and UB-052.

## Lifecycle state

WRITE.

Per `conventions/evals.md`, this file defines the behavior contract only. It does not provide runnable detector code, fixtures, parser adapters, CLI wiring, pytest tests, verifier scripts, or enforcement rollout.

## Declared roles

`validator`, `mapper`

This file-local declaration follows `~/ai/conventions/code-quality.md` `## Declared roles`: this WRITE eval spec validates ACR-278 contract-format behavior and maps trace or markdown evidence into future findings.

## Unwanted behavior

The unwanted behavior is trace-detectable or markdown-file-detectable drift where the operator contract format remains frontmatter-only, changes filename-stem identity, treats the old body skeleton as mandatory, omits or malforms the required `## Contract` fenced YAML block, fails to represent base Jira tasks and envelopes in operator-contract-v1, loses Jira per-task constraints, or fails to preserve this central WRITE eval spec as the reviewable verification artifact.

A future detector should fire when ACR-278 implementation evidence shows any covered surface missing the required operator-contract-v1 contract shape or weakening the preserved base Jira procedural contracts that the structured contract must mirror.

The detector should also fire when a touched file lacks the file-local `## Declared roles` block required by the Step 6a contract or proposal Declared-roles plan, or when an existing file-local `## Declared roles` block is modified to a non-conforming role set during the WU edit.

## Positive evidence

Positive evidence may include:

- `agents/operator-file-format.md` still defines the callable contract as only frontmatter keys or omits the required `## Contract` block rules, wrapper inheritance rule, procedure-vs-contract boundary, or worked examples.
- An operator file introduces a frontmatter `name:` identity or otherwise conflicts with filename-stem identity.
- A detector or auditor treats the old recommended body skeleton as mandatory rather than advisory.
- A `## Contract` section is absent, has no fenced YAML block, fails YAML parsing, omits `schema: operator-contract-v1`, or omits ticket-named fields.
- `agents/jira-operator.md` lacks structured contract entries for `read`, `comment`, `transition`, `search`, `create`, or `update-estimate`.
- Jira per-task output, error, endpoint, estimate, ADF, dedupe, side-effect, `BLOCKED`, or `NEEDS_INPUT` details are absent from the structured contract.
- The central eval spec is missing, not lifecycle `WRITE`, lacks unwanted behavior or non-fire cases, or is replaced by executable tests in this WU.
- A Markdown parser detects that `agents/operator-file-format.md`, `agents/jira-operator.md`, or this central eval spec lacks a file-local `## Declared roles` block, has a malformed role block, or has role-set drift relative to the expected role classifications from the Step 6a contract and proposal Declared-roles plan.

## Non-fire cases

The eval must not fire on:

- Operator files that preserve frontmatter identity rules while adding a valid `## Contract` block.
- The existing body skeleton remaining advisory while the contract block becomes the required call interface.
- Jira procedural prose remaining as the procedural authority when the structured contract mirrors it.
- Additional explanatory prose outside the contract block, provided the fenced contract YAML itself stays declarative and schema-bounded.
- Future detector implementation work outside ACR-278 that adds runnable eval code in a later lifecycle transition.
- Documentation examples of malformed contracts that are clearly examples, not live operator contract blocks.
- Files outside this spec's touched-component set for ACR-278 declared-role verification.
- A touched file whose `## Declared roles` block matches the contract's expected role set exactly, allowing only ordering tolerance consistent with `~/ai/conventions/code-quality.md` cohesion rules.

## Required trace fields

The future detector must read markdown file snapshots and, when available, saved `agents trace --json`, dispatch prompts, agent logs, audit bundles, process-tree-audit reports, and workflow reports. It must extract the following fields, preserving missing or ambiguous values explicitly:

| UB | Extension fields |
|---|---|
| UB-001 | `operator_file`, `frontmatter_keys`, `contract_block_status` |
| UB-002 | `operator_file`, `filename_stem`, `frontmatter_name_key_present` |
| UB-003 | `operator_file`, `section_presence`, `mandatory_vs_advisory_disposition` |
| UB-005 | `operator_file`, `contract_version`, `yaml_parse_status`, `missing_fields`, `example_refs` |
| UB-006 | `operator_file`, `task_names`, `contract_task_inputs`, `missing_task_contracts` |
| UB-008 | `operator_file`, `error_envelope`, `diagnosis_probe_evidence` |
| UB-009 | `operator_file`, `task_read`, `output_fields`, `adf_markdown_render_contract` |
| UB-010 | `operator_file`, `task_update_estimate`, `allowed_estimates`, `side_effects` |
| UB-011 | `operator_file`, `comment_endpoint`, `fallback_endpoint`, `forbidden_endpoint` |
| UB-012 | `operator_file`, `task_create`, `dedupe_probe`, `story_point_validation` |
| UB-013 | `operator_file`, `output_contract_by_task`, `blocked_conditions`, `needs_input_conditions` |
| UB-052 | `eval_spec_path`, `lifecycle_state`, `unwanted_behaviors`, `non_fire_cases` |
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
| UB-001 | `operator_file`, `frontmatter_keys`, `contract_block_status` |
| UB-002 | `operator_file`, `filename_stem`, `frontmatter_name_key_present` |
| UB-003 | `operator_file`, `section_presence`, `mandatory_vs_advisory_disposition` |
| UB-005 | `operator_file`, `contract_version`, `yaml_parse_status`, `missing_fields`, `example_refs` |
| UB-006 | `operator_file`, `task_names`, `contract_task_inputs`, `missing_task_contracts` |
| UB-008 | `operator_file`, `error_envelope`, `diagnosis_probe_evidence` |
| UB-009 | `operator_file`, `task_read`, `output_fields`, `adf_markdown_render_contract` |
| UB-010 | `operator_file`, `task_update_estimate`, `allowed_estimates`, `side_effects` |
| UB-011 | `operator_file`, `comment_endpoint`, `fallback_endpoint`, `forbidden_endpoint` |
| UB-012 | `operator_file`, `task_create`, `dedupe_probe`, `story_point_validation` |
| UB-013 | `operator_file`, `output_contract_by_task`, `blocked_conditions`, `needs_input_conditions` |
| UB-052 | `eval_spec_path`, `lifecycle_state`, `unwanted_behaviors`, `non_fire_cases` |
| Declared roles | `touched_file`, `declared_roles_block_present`, `declared_roles_observed`, `declared_roles_expected`, `declared_roles_match` |

`severity` is `HIGH` when the required operator-contract-v1 call interface or base Jira contract backfill is missing or malformed; `MEDIUM` when evidence shows partial contract drift without immediate dispatcher ambiguity; and `LOW` only for incomplete evidence or future trace-adapter uncertainty.

## Suggested action

Return `add-contract-block` or `revise-operator-contract-format` as appropriate. The caller should update `agents/operator-file-format.md` or `agents/jira-operator.md` so the contract block is valid operator-contract-v1 YAML, mirrors the base Jira procedure, preserves filename-stem identity, and keeps the old body skeleton advisory.

## Coverage

| UB | Scenario ID | Scenario |
|---|---|---|
| UB-001 | ACR278-OCF-001 | Detect stale frontmatter-only callable contract semantics. |
| UB-002 | ACR278-OCF-002 | Preserve filename-stem identity and absence of frontmatter `name:`. |
| UB-003 | ACR278-OCF-003 | Keep the old operator body skeleton advisory. |
| UB-005 | ACR278-OCF-004 | Verify required operator-contract-v1 block, fields, and examples. |
| UB-006 | ACR278-OCF-005 | Verify base Jira task vocabulary in the structured contract. |
| UB-008 | ACR278-OCF-006 | Preserve raw Jira 4xx envelope and confirmatory-probe rule. |
| UB-009 | ACR278-OCF-007 | Verify Phase 0 Jira read output and ADF-to-Markdown shape. |
| UB-010 | ACR278-OCF-008 | Verify update-estimate validation, field, side effects, and no transition. |
| UB-011 | ACR278-OCF-009 | Verify Jira comment endpoint, fallback, and forbidden plural endpoint. |
| UB-012 | ACR278-OCF-010 | Verify Jira create dedupe, ADF rendering, and story-point validation. |
| UB-013 | ACR278-OCF-011 | Verify per-task success and failure envelopes. |
| UB-052 | ACR278-OCF-012 | Verify this central WRITE eval spec exists with required sections. |
| Declared roles | ACR278-OCF-DR-001 | Verify `agents/operator-file-format.md` declares `validator`, `parser`, and `formatter`. |
| Declared roles | ACR278-OCF-DR-002 | Verify `agents/jira-operator.md` declares `validator`, `parser`, `formatter`, and `orchestration`. |
| Declared roles | ACR278-OCF-DR-003 | Verify this central eval spec declares `validator` and `mapper`. |
