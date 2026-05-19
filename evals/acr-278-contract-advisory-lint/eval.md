---
eval_id: acr-278-contract-advisory-lint
behavior_class: Advisory contract-block lint for operator and AGENTS auditors
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
suggested_action_class: add-advisory-contract-lint
---

# ACR-278 Contract Advisory Lint

## Eval identity

This WRITE-state eval spec defines the future structural-verification contract for ACR-278 advisory contract-block lint in `agents/agent-design-auditor.md` and `agents/agentsmd-curator.md`. Source authority is the ACR-278 Step 6a contract, approved proposal R2 Test-Intent Track, problem map, coverage inventory, and `/home/nes/ai/conventions/evals.md`.

This spec covers UB-041, UB-042, UB-043, UB-044, UB-045, UB-046, UB-047, and UB-048.

## Lifecycle state

WRITE.

Per `conventions/evals.md`, this file defines the behavior contract only. It does not provide runnable detector code, fixtures, parser adapters, CLI wiring, pytest tests, verifier scripts, or enforcement rollout.

## Unwanted behavior

The unwanted behavior is markdown-file-detectable auditor or curator drift where ACR-278 advisory contract-block lint is absent, malformed, calibrated as blocking, omitted from output schemas, or fails to compare AGENTS routing rows against operator `## Contract` blocks.

The detector should fire when the design auditor does not inspect `## Contract` fenced YAML, does not emit the required advisory finding classes, or promotes ACR-278 contract lint to blocking; it should also fire when the AGENTS curator does not walk operator rows, check contract presence, detect input conflicts, or list the new catalog-contract finding classes.

The detector should also fire when a touched file lacks the file-local `## Declared roles` block required by the Step 6a contract or proposal Declared-roles plan, or when an existing file-local `## Declared roles` block was modified to a non-conforming role set during the WU edit.

## Positive evidence

Positive evidence may include:

- `agent-design-auditor.md` only checks frontmatter and never inspects `## Contract` sections.
- Contract-block findings lack advisory classes for missing contract, malformed YAML, schema mismatch, procedure-like contract fields, or body-contract inconsistency.
- Severity calibration treats ACR-278 contract findings as blocking rather than advisory.
- The auditor output contract has no contract-finding section.
- `agentsmd-curator.md` architecture rules still prefer AGENTS input summaries over contract pointers.
- Curator audit mode does not walk operator rows, inspect target operator contracts, or compare row input summaries against contract inputs.
- Curator common findings or output contract omit catalog-row contract finding classes.
- A Markdown parser detects that `agents/agent-design-auditor.md` or `agents/agentsmd-curator.md` lacks a file-local `## Declared roles` block, has a malformed role block, or has role-set drift relative to the expected role classifications from the Step 6a contract and proposal Declared-roles plan.

## Non-fire cases

The eval must not fire on:

- Advisory findings that clearly report contract issues without blocking the ACR-278 run.
- Existing mandatory frontmatter checks remaining mandatory while contract lint is added as advisory.
- Auditor or curator prose that delegates blocking enforcement to a later T2 work unit.
- A curator row that names an operator without a contract when the row is explicitly outside the ACR-278 priority-0 contract-backfill set, provided the finding remains advisory.
- Files outside this spec's touched-component set for ACR-278 declared-role verification.
- A touched file whose `## Declared roles` block matches the contract's expected role set exactly, allowing only ordering tolerance consistent with `~/ai/conventions/code-quality.md` cohesion rules.

## Required trace fields

The future detector must read markdown file snapshots and, when available, saved `agents trace --json`, dispatch prompts, agent logs, audit bundles, process-tree-audit reports, and workflow reports. It must extract:

| UB | Extension fields |
|---|---|
| UB-041 | `auditor_file`, `frontmatter_parse_rule`, `contract_parse_rule` |
| UB-042 | `auditor_file`, `severity_calibration`, `mandatory_contract_rule`, `advisory_body_rule` |
| UB-043 | `auditor_file`, `output_schema_sections`, `contract_section_present` |
| UB-044 | `auditor_file`, `missing_contract`, `yaml_malformed`, `procedure_like_fields`, `body_contract_inconsistency` |
| UB-045 | `curator_file`, `architecture_rules`, `operator_contract_required_status` |
| UB-046 | `curator_file`, `audit_mode_steps`, `row_contract_check`, `required_input_comparison` |
| UB-047 | `curator_file`, `common_findings`, `contract_finding_class` |
| UB-048 | `curator_file`, `operator_row`, `contract_block_status`, `input_conflict_evidence` |
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
| UB-041 | `auditor_file`, `frontmatter_parse_rule`, `contract_parse_rule` |
| UB-042 | `auditor_file`, `severity_calibration`, `mandatory_contract_rule`, `advisory_body_rule` |
| UB-043 | `auditor_file`, `output_schema_sections`, `contract_section_present` |
| UB-044 | `auditor_file`, `missing_contract`, `yaml_malformed`, `procedure_like_fields`, `body_contract_inconsistency` |
| UB-045 | `curator_file`, `architecture_rules`, `operator_contract_required_status` |
| UB-046 | `curator_file`, `audit_mode_steps`, `row_contract_check`, `required_input_comparison` |
| UB-047 | `curator_file`, `common_findings`, `contract_finding_class` |
| UB-048 | `curator_file`, `operator_row`, `contract_block_status`, `input_conflict_evidence` |
| Declared roles | `touched_file`, `declared_roles_block_present`, `declared_roles_observed`, `declared_roles_expected`, `declared_roles_match` |

`severity` is `MEDIUM` when advisory contract lint is absent or incomplete; `HIGH` only if a lint rule becomes blocking in ACR-278 or masks a dispatcher-critical contract conflict; and `LOW` for incomplete evidence or future trace-adapter uncertainty.

## Suggested action

Return `add-advisory-contract-lint`. The caller should update the agent-design auditor and AGENTS curator so they emit advisory contract-block and catalog-contract findings, include the new finding classes in their output contracts, and keep blocking enforcement out of ACR-278.

## Coverage

| UB | Scenario ID | Scenario |
|---|---|---|
| UB-041 | ACR278-CAL-001 | Extend auditor frontmatter parsing with contract parse status. |
| UB-042 | ACR278-CAL-002 | Calibrate contract lint as advisory, not blocking. |
| UB-043 | ACR278-CAL-003 | Ensure auditor reports expose contract findings. |
| UB-044 | ACR278-CAL-004 | Verify main agent-design-auditor advisory lint classes. |
| UB-045 | ACR278-CAL-005 | Update curator architecture rules for contract pointers. |
| UB-046 | ACR278-CAL-006 | Ensure curator audit mode checks rows against contracts. |
| UB-047 | ACR278-CAL-007 | Add contract-related common finding vocabulary. |
| UB-048 | ACR278-CAL-008 | Verify curator catalog-row contract status and input conflicts. |
| Declared roles | ACR278-CAL-DR-001 | Verify `agents/agent-design-auditor.md` declares `parser`, `validator`, and `formatter`. |
| Declared roles | ACR278-CAL-DR-002 | Verify `agents/agentsmd-curator.md` declares `parser`, `validator`, and `formatter`. |
