---
eval_id: acr-279-tier-1-contract-block-presence
behavior_class: Tier 1 operator contract-block presence and schema validity
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

# ACR-279 Tier 1 Contract Block Presence

## Eval identity

This WRITE-state eval spec defines the future structural-verification contract for ACR-279 Tier 1 operator contract backfill. Source authority is `/home/nes/ai/planning/acr-279-operator-contract-rollout/contracts/acr-279-operator-contract-rollout.md` sections 2.1, 5, 6, and 8, the proposal, the problem map, the hookpoint research, `/home/nes/ai/conventions/evals.md`, and `/home/nes/ai/agents/operator-file-format.md` section `Contract block (operator-contract-v1)`.

Structural-verification claim: every Tier 1 high-risk operator in scope has exactly one live `## Contract` block with a fenced YAML block whose first key is `schema: operator-contract-v1`, and the block declares the operator's task inputs, defaults, secrets, outputs, errors, side effects, delegation boundaries, and direct-operation permissions without replacing procedural body text.

## Lifecycle state

WRITE.

Per `conventions/evals.md`, this file defines the behavior contract only. It does not provide runnable detector code, parser adapters, CLI wiring, pytest tests, verifier scripts, or enforcement rollout.

## Declared roles

`validator`, `mapper`

This file-local declaration reflects this eval spec's ownership of Tier 1 contract-block validation rules and future mapping from markdown/audit evidence into findings.

## Inputs the auditor reads

The future auditor reads these Tier 1 operator files:

| Surface | Operator file |
|---|---|
| Linear ticket backend | `/home/nes/ai/agents/linear-operator.md` |
| Branch topology | `/home/nes/ai/agents/jj-operator.md` |
| Worktree topology | `/home/nes/ai/agents/worktree-operator.md` |
| Release lifecycle | `/home/nes/ai/agents/release-orchestrator.md` |
| Release cut | `/home/nes/ai/agents/release-cut-operator.md` |
| Release hotfix | `/home/nes/ai/agents/release-hotfix-operator.md` |
| Release promote | `/home/nes/ai/agents/release-promote-operator.md` |
| Release reconcile | `/home/nes/ai/agents/release-reconcile-operator.md` |
| Work manager base | `/home/nes/ai/agents/work-manager-operator.md` |
| Work manager max flavor | `/home/nes/ai/agents/work-manager-operator-max.md` |
| Work manager pragmatic flavor | `/home/nes/ai/agents/work-manager-operator-pragmatic.md` |
| Work manager hackerman flavor | `/home/nes/ai/agents/work-manager-operator-hackerman.md` |

The auditor also reads the ACR-278 priority-0 comparison files without re-authoring them: `/home/nes/ai/agents/jira-operator.md` and `/home/nes/ai/agents/implementation-pipeline-orchestrator.md`.

## Unwanted behavior

The unwanted behavior is markdown-file-detectable Tier 1 drift where any listed high-risk operator remains prose-only, omits `## Contract`, contains malformed YAML, omits `schema: operator-contract-v1`, lacks required call-interface fields, hides secrets/defaults/delegation in prose only, or encodes step-by-step procedure mechanics inside the contract block.

## Positive evidence

Positive evidence may include:

- A listed Tier 1 operator file has no exact `## Contract` H2.
- The `## Contract` section has no fenced YAML block or more than one live fenced YAML block.
- The first YAML key is not `schema: operator-contract-v1`.
- Required fields are absent: `inputs`, `defaults`, `secrets`, `outputs`, `errors`, `side_effects`, `must_delegate`, `may_direct`, and `forbidden_direct`.
- Wrapper/flavor files that inherit base behavior do not declare `inherits` or an equivalent explicit base-reference contract.
- External-service, branch, worktree, release, or Work Manager side effects remain only in prose and are absent from `side_effects`.
- The YAML block contains procedure mechanics, command recipes, phase order, or if-then exception handling that belongs in the operator body.
- ACR-278 priority-0 examples are treated as missing merely because they are comparison inputs rather than ACR-279 rewrite targets.

## Non-fire cases

The eval must not fire on:

- Additional explanatory prose outside the contract YAML, provided the live contract block is valid and declarative.
- Human-readable `## Required Inputs`, `## Inputs`, or `## Outputs` prose remaining as a pointer or explanation after the structured contract exists.
- ACR-278 priority-0 files being read as format references and not rewritten by ACR-279.
- Trivial/minimum-body operators outside the Tier 1 list retaining advisory-only missing-body findings. This carve-out does not apply to the Tier 1 files listed above because they are high-risk external, branch, worktree, release, or Work Manager surfaces.

## Pass/fail criteria

Pass: every listed Tier 1 operator exists and has a valid `operator-contract-v1` `## Contract` block that covers documented tasks and high-risk side effects.

Fail: any listed Tier 1 operator is missing, missing `## Contract`, malformed, schema-mismatched, or omits required high-risk contract fields. The finding severity is `blocking` for ACR-279 acceptance because these are edited high-risk operators. The trivial/minimum-body carve-out remains `advisory` only for operators outside this Tier 1 acceptance surface.

## Required trace fields

The future detector must read markdown file snapshots and, when available, saved `agents trace --json`, dispatch prompts, agent logs, audit bundles, process-tree-audit reports, and workflow reports. It must extract:

| Field | Description |
|---|---|
| `operator_file` | Absolute path of the Tier 1 operator under review. |
| `tier` | `tier-1`. |
| `contract_block_status` | `present`, `missing`, `duplicate`, or `malformed`. |
| `yaml_parse_status` | YAML parse result for the fenced block. |
| `schema_key` | Observed first YAML key and value. |
| `missing_fields` | Required contract fields absent from the live block. |
| `task_coverage_status` | Whether documented task variants are represented. |
| `high_risk_category` | External service, branch topology, worktree, release, or work manager. |
| `procedure_leak_evidence` | Contract fields containing procedural mechanics, if present. |
| `comparison_refs` | ACR-278 priority-0 files used as schema examples. |

## Finding schema

Findings preserve the minimum fields from `conventions/evals.md`:

- `eval_id`
- `severity`
- `evidence_paths`
- `summary`
- `suggested_action`
- `confidence`

The finding schema also includes `operator_file`, `tier`, `contract_block_status`, `yaml_parse_status`, `schema_key`, `missing_fields`, `task_coverage_status`, `high_risk_category`, `procedure_leak_evidence`, and `comparison_refs`.

`severity` is `HIGH` for a missing or malformed Tier 1 contract block, reported to the rollout as `blocking`. `MEDIUM` is reserved for partial evidence that cannot establish whether a live block is missing. `LOW` is reserved for future trace-adapter uncertainty.

## Suggested action

Return `add-or-repair-operator-contract-block`. The caller should update the named Tier 1 operator with a valid declarative `operator-contract-v1` block while preserving the operator body as procedural authority.

## Coverage

| Scenario ID | Scenario |
|---|---|
| ACR279-T1-001 | Detect missing contract block on each Tier 1 operator. |
| ACR279-T1-002 | Detect malformed or schema-mismatched Tier 1 contract YAML. |
| ACR279-T1-003 | Detect missing inputs, secrets, outputs, errors, side effects, or delegation fields on high-risk Tier 1 surfaces. |
| ACR279-T1-004 | Detect procedure mechanics placed inside the contract block. |
| ACR279-T1-005 | Verify ACR-278 priority-0 files are used as comparison references, not ACR-279 rewrite targets. |
