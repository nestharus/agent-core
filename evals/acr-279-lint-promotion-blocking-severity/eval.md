---
eval_id: acr-279-lint-promotion-blocking-severity
behavior_class: Contract lint promotion to blocking severity for high-risk operators
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
suggested_action_class: promote-contract-lint-severity
---

# ACR-279 Lint Promotion Blocking Severity

## Eval identity

This WRITE-state eval spec defines the future structural-verification contract for ACR-279 promotion of contract-block lint from advisory to blocking for high-risk operator categories. Source authority is `/home/nes/ai/planning/acr-279-operator-contract-rollout/contracts/acr-279-operator-contract-rollout.md` sections 4, 5, 6, and 8, the proposal, the hookpoint research, `/home/nes/ai/conventions/evals.md`, and `/home/nes/ai/agents/operator-file-format.md` `Minimum Body`.

Structural-verification claim: `agent-design-auditor.md` and `agentsmd-curator.md` classify missing or malformed `## Contract` blocks as blocking for new operators, project wrappers, and edited high-risk operators touching external services, credentials, branch topology, releases, PRs, tickets, or worktrees, while preserving advisory treatment for trivial/minimum-body operators outside those categories.

## Lifecycle state

WRITE.

This spec is not runnable detector code and does not define pytest tests, verifier scripts, or CI wiring.

## Declared roles

`validator`, `mapper`

## Inputs the auditor reads

The future auditor reads:

| Lint surface | File and section |
|---|---|
| Agent design contract lint | `/home/nes/ai/agents/agent-design-auditor.md` procedure and severity calibration for contract findings |
| AGENTS curator contract lint | `/home/nes/ai/agents/agentsmd-curator.md` audit-mode cross-reference checks and common findings catalog |
| Schema/carve-out reference | `/home/nes/ai/agents/operator-file-format.md` `Contract block (operator-contract-v1)` and `Minimum Body` sections |

## Unwanted behavior

The unwanted behavior is lint-promotion drift where missing or malformed contract blocks remain advisory for promoted high-risk categories, where severity vocabulary is inconsistent or non-blocking, where the promoted rule becomes global and blocks trivial/minimum-body operators outside the high-risk categories, or where the two lint operators diverge on high-risk classification.

## Positive evidence

Positive evidence may include:

- `agent-design-auditor.md` still says missing or malformed `## Contract` findings are advisory for new operators or edited high-risk operators.
- `agentsmd-curator.md` still reports `catalog-row-missing-contract` as advisory for new operators, project wrappers, or edited high-risk operators.
- Either lint surface omits the promoted categories: new operators, project wrappers, external services, credentials, branch topology, releases, PRs, tickets, or worktrees.
- Either lint surface blocks trivial/minimum-body operators solely for lacking rich recommended body sections.
- The two lint surfaces use incompatible severity semantics that let a high-risk missing contract pass without `HIGH` or `BLOCKING` status.
- The rule treats AGENTS row input conflicts as contract-block failures rather than separately calibrated catalog/contract conflicts.

## Non-fire cases

The eval must not fire on:

- `agent-design-auditor` using `HIGH` as its blocking verdict vocabulary while `agentsmd-curator` uses `BLOCKING`, provided both mean the run must not pass.
- Trivial/minimum-body operators outside the promoted categories receiving `LOW`, `MINOR`, `advisory`, or other non-blocking findings.
- Missing rich recommended body sections remaining advisory when the `## Contract` block is valid or the operator is outside the high-risk/new-wrapper categories.
- Additional lint classes for malformed YAML, schema mismatch, procedure-like fields, or body/contract inconsistency, provided missing/malformed contract severity is promoted correctly.

## Pass/fail criteria

Pass: both lint operators explicitly promote missing/malformed `operator-contract-v1` contract-block findings to blocking severity for new operators, project wrappers, and edited high-risk operators; both retain an `advisory` carve-out for trivial/minimum-body operators outside those categories.

Fail: either lint operator leaves promoted high-risk missing/malformed contract findings advisory, omits a promoted category, or blocks trivial/minimum-body operators solely for missing richer body skeleton sections. The acceptance finding is `blocking` when the high-risk rule is absent or weakened, and `blocking` when the advisory carve-out is erased because that would violate `operator-file-format.md` minimum-body calibration.

## Required trace fields

| Field | Description |
|---|---|
| `lint_file` | Absolute path of `agent-design-auditor.md` or `agentsmd-curator.md`. |
| `lint_surface` | `agent-design-auditor` or `agentsmd-curator`. |
| `contract_parse_rule_status` | Whether missing/malformed contract checks are present. |
| `promoted_categories` | Observed categories that receive blocking severity. |
| `high_risk_classifier_status` | Whether external services, credentials, branch topology, releases, PRs, tickets, and worktrees are named. |
| `blocking_severity_vocabulary` | `HIGH`, `BLOCKING`, or equivalent run-blocking status. |
| `trivial_carveout_status` | Whether minimum-body/trivial operators remain advisory outside promoted categories. |
| `finding_identifier_examples` | Finding class names emitted by the lint rule. |

## Finding schema

Findings preserve the minimum fields from `conventions/evals.md`:

- `eval_id`
- `severity`
- `evidence_paths`
- `summary`
- `suggested_action`
- `confidence`

The finding schema also includes `lint_file`, `lint_surface`, `contract_parse_rule_status`, `promoted_categories`, `high_risk_classifier_status`, `blocking_severity_vocabulary`, `trivial_carveout_status`, and `finding_identifier_examples`.

`severity` is `HIGH` for missing promoted blocking behavior or lost advisory carve-out; `MEDIUM` is for ambiguous wording that still appears run-blocking; `LOW` is for future trace-adapter uncertainty.

## Suggested action

Return `promote-contract-lint-severity`. The caller should update the lint operator's severity rules and finding catalog so high-risk missing/malformed contracts block while trivial/minimum-body operators keep non-blocking treatment.

## Coverage

| Scenario ID | Scenario |
|---|---|
| ACR279-LP-001 | Verify agent-design-auditor promotes high-risk missing/malformed contracts to blocking/HIGH. |
| ACR279-LP-002 | Verify agentsmd-curator promotes high-risk missing/malformed contracts to BLOCKING. |
| ACR279-LP-003 | Verify both surfaces name the same promoted high-risk categories. |
| ACR279-LP-004 | Verify trivial/minimum-body operators retain advisory carve-out. |
| ACR279-LP-005 | Verify body-skeleton gaps are not reclassified as contract-block failures. |
