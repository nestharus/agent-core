---
eval_id: acr-279-drift-disposition-cross-references
behavior_class: Drift disposition cross-reference encoding in operator contracts
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
suggested_action_class: add-drift-disposition-cross-reference
---

# ACR-279 Drift Disposition Cross-References

## Eval identity

This WRITE-state eval spec defines the future structural-verification contract for ACR-279 drift-disposition encoding. Source authority is `/home/nes/ai/planning/acr-279-operator-contract-rollout/contracts/acr-279-operator-contract-rollout.md` sections 2.4, 5, 6, and 8, the proposal drift-disposition section, the hookpoint research, `/home/nes/ai/conventions/evals.md`, and `/home/nes/ai/agents/operator-file-format.md`.

Structural-verification claim: release-family contract blocks preserve current RFQ-embedded release behavior by citing ACR-283 in `notes:`, and `prototype-orchestrator.md` documents its residual direct Jira issue-link API as an allowed direct operation with ACR-282 as the cleanup tracker instead of hiding or normalizing the exception.

## Lifecycle state

WRITE.

This spec is not executable and does not provide detector code, pytest tests, verifier scripts, or enforcement wiring.

## Declared roles

`validator`, `mapper`

## Inputs the auditor reads

The future auditor reads these files and sections:

| Surface | File and section |
|---|---|
| Release orchestrator drift note | `/home/nes/ai/agents/release-orchestrator.md` `## Contract` block `notes:` field |
| Release cut drift note | `/home/nes/ai/agents/release-cut-operator.md` `## Contract` block `notes:` field |
| Release hotfix drift note | `/home/nes/ai/agents/release-hotfix-operator.md` `## Contract` block `notes:` field |
| Release promote drift note | `/home/nes/ai/agents/release-promote-operator.md` `## Contract` block `notes:` field |
| Release reconcile drift note | `/home/nes/ai/agents/release-reconcile-operator.md` `## Contract` block `notes:` field |
| Prototype direct Jira exception | `/home/nes/ai/agents/prototype-orchestrator.md` `## Contract` block `may_direct:` field |
| Prose fallback if prototype contract is predecessor-owned | `/home/nes/ai/agents/prototype-orchestrator.md` handoff/procedure prose documenting ACR-282 |

## Unwanted behavior

The unwanted behavior is drift-disposition loss where release-family contract blocks either omit ACR-283, generalize RFQ-embedded release policy into a generic shared contract, or fail to keep the planned cleanup visible; or where `prototype-orchestrator.md` hides direct Jira `/issueLink` behavior, fails to declare it as a documented direct operation, or omits ACR-282 as the cleanup tracker.

## Positive evidence

Positive evidence may include:

- A release-family `## Contract` block has no `notes:` entry naming `ACR-283`.
- A release-family note mentions release cleanup generically but does not cite `https://linear.app/oulipoly/issue/ACR-283/` or `ACR-283`.
- A release-family contract rewrites RFQ-specific behavior into generic shared release policy without a cleanup note.
- `prototype-orchestrator.md` has a direct Jira issue-link path but no `may_direct:` entry, and no rationale naming `ACR-282`.
- The prototype direct-operation entry omits the direct Jira issue-link API, omits the planned `jira-operator task=link` cleanup direction, or fails to cite `https://linear.app/oulipoly/issue/ACR-282/` or `ACR-282`.
- If `prototype-orchestrator.md` is not contract-backfilled in this WU because it falls under existing ACR-278 priority surface, neither its existing contract nor its prose handoff contains the ACR-282 cross-reference.

## Non-fire cases

The eval must not fire on:

- Release contracts that cite ACR-283 in `notes:` while preserving current RFQ-specific behavior as residual debt.
- Prototype contracts that use the schema's `may_direct` field name while clearly documenting it as allowed-direct-operation semantics and naming ACR-282 in the rationale.
- A prototype prose fallback that cites ACR-282 when the contract block is explicitly predecessor-owned and not yet backfilled in this WU.
- Tracker references appearing in prose adjacent to the contract when the schema cannot carry `notes:` verbatim, provided the release-family contract block still points to the note.

## Pass/fail criteria

Pass: all five release-family contract blocks cite ACR-283 in `notes:` as the planned cleanup tracker, and `prototype-orchestrator.md` documents the direct Jira issue-link API as an allowed direct operation with rationale citing ACR-282 or, when predecessor-owned, contains an explicit prose handoff with the same cross-reference.

Fail: any release-family contract omits ACR-283 or erases RFQ drift; or the prototype direct Jira issue-link exception is absent, undocumented, or lacks ACR-282. The finding is `blocking` because this WU's drift disposition is part of acceptance. The trivial/minimum-body `advisory` carve-out does not apply to these named drift surfaces.

## Required trace fields

| Field | Description |
|---|---|
| `operator_file` | Absolute path under review. |
| `contract_block_status` | Presence and parse status for the contract block. |
| `notes_field` | Observed release-family `notes:` content. |
| `acr_283_reference_status` | Whether ACR-283 is cited in the release-family contract. |
| `rfq_generalization_evidence` | Evidence that RFQ-specific behavior was incorrectly generalized, if present. |
| `direct_operation_field` | Prototype direct-allowance field observed. |
| `direct_jira_link_status` | Whether direct Jira issue-link API is declared. |
| `acr_282_reference_status` | Whether ACR-282 is cited in the prototype direct-operation rationale or fallback prose. |
| `fallback_prose_status` | Whether predecessor-owned prose handoff is present when no contract exists. |

## Finding schema

Findings preserve the minimum fields from `conventions/evals.md`:

- `eval_id`
- `severity`
- `evidence_paths`
- `summary`
- `suggested_action`
- `confidence`

The finding schema also includes `operator_file`, `contract_block_status`, `notes_field`, `acr_283_reference_status`, `rfq_generalization_evidence`, `direct_operation_field`, `direct_jira_link_status`, `acr_282_reference_status`, and `fallback_prose_status`.

`severity` is `HIGH` for missing or incorrect tracker cross-references and is treated as rollout `blocking`; `MEDIUM` is for ambiguous predecessor ownership; `LOW` is for trace-adapter uncertainty.

## Suggested action

Return `add-drift-disposition-cross-reference`. The caller should add the missing ACR-283 release note or ACR-282 prototype direct-operation rationale without implementing those cleanup tickets.

## Coverage

| Scenario ID | Scenario |
|---|---|
| ACR279-DD-001 | Verify ACR-283 in release-orchestrator contract notes. |
| ACR279-DD-002 | Verify ACR-283 in release-cut, hotfix, promote, and reconcile contract notes. |
| ACR279-DD-003 | Detect RFQ policy generalization that hides ACR-283 cleanup. |
| ACR279-DD-004 | Verify prototype direct Jira issue-link allowance cites ACR-282. |
| ACR279-DD-005 | Accept explicit ACR-282 prose fallback only when prototype contract backfill is predecessor-owned. |
