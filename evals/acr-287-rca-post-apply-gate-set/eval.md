---
slug: acr-287-rca-post-apply-gate-set
lifecycle: WRITE
class: structural-verification
owner: ACR-287
ticket: ACR-287
description: Structural verification that RCA post-apply handoff is gated by apply-gate-set in rca-post-apply mode.
---

# RCA Post-Apply Gate-Set Wiring - Eval Spec

## Purpose

This WRITE-state structural-verification eval specifies that the RCA orchestrator wires the shared `apply-gate-set` operator in `mode=rca-post-apply` after Phase 6 original-signal GREEN and `VERIFICATION-CRITIC: PASS`, before any downstream lifecycle handoff. It verifies that downstream post-mortem, action-item, runbook, tracker, and close paths are blocked on missing, stale, non-LOW, malformed, unsupported, or unratified gate rows; that ACR-254 proof-risk, validation-integrity, and original-signal checks remain prerequisites rather than substitutes; and that `agents/rca-orchestrator.md`, `workflows/rca.md`, and the RCA `workflows/index.json` entry agree.

## Scope

This eval covers only the RCA caller wiring for `apply-gate-set(caller_mode=rca-post-apply)`: placement, blocking semantics, currentness handoff, audit-history field names, workflow/index parity, required RCA adapter inputs, ACR-254 preservation, and file-local declared-role coverage on the touched RCA files. It does not verify the internals of the shared `apply-gate-set` operator, its runnable detector, final currentness algorithm, process-tree topology internals, or implementation-pipeline caller modes; those surfaces are owned by ACR-292, ACR-294, ACR-295, and ACR-288 as applicable.

## Inherited prototype-pending discharge

| Inherited scenario | Disposition |
|---|---|
| `APPLY-GATE-SET-001` | Discharged for the RCA caller by `ACR287-RCA-GATE-001`, which requires the RCA downstream lifecycle to wait for `apply-gate-set(caller_mode=rca-post-apply)` PASS and thereby preserves the inherited actual-diff PR-review four-gate handoff blocker. |
| `APPLY-GATE-SET-002` | Discharged for the RCA caller by `ACR287-RCA-GATE-001` and `ACR287-RCA-GATE-002`, which require the gate-set PASS boundary and block downstream handoff when code-quality aggregate rows, runtime-claim transport, or dossier/actual-diff evidence is missing or non-PASS. |
| `APPLY-GATE-SET-003` | Discharged for the RCA caller by `ACR287-RCA-GATE-001`, which requires Phase 6.5 gate-set PASS before handoff, including expected-process and process-tree evidence produced by the consumed operator contract. |
| `APPLY-GATE-SET-004` | Discharged for the RCA caller by `ACR287-RCA-GATE-002`, which treats missing gate rows without explicit skip-with-followup or repair evidence as blocking before downstream lifecycle. |
| `APPLY-GATE-SET-005` | Discharged for the RCA caller by `ACR287-RCA-GATE-003`, which rejects stale manifest reuse after RCA re-entry unless the active cycle/head/diff/scope/runtime-claim keys match or `apply-gate-set` emits stale-refusal evidence. |
| `APPLY-GATE-SET-006` | Discharged for the RCA caller by `ACR287-RCA-GATE-002`, which prevents bootstrap-exception, skip, or ratification rows from authorizing downstream advance without valid evidence and repair routing. |
| `APPLY-GATE-SET-007` | Partially discharged for the RCA-mode adapter subset by `ACR287-RCA-GATE-006`, which requires RCA adapter inputs and inventory-resolution evidence for proof-risk and supported-surface coverage. Implementation-mode equivalence remains owned by ACR-288. |

## Scenarios

### ACR287-RCA-GATE-001

Scenario name: `ACR287-RCA-GATE-001`.

Behavior under verification: New post-apply gate dispatch is placed after Phase 6 original-signal green plus verification-critic PASS, and before any downstream lifecycle handoff. The eval fires when downstream handoff occurs without `apply-gate-set(caller_mode=rca-post-apply)` PASS.

Fixture source / evidence anchors: RCA trace bundle; `${planning_dir}/rca/<failure-id>-original-signal-verification.md` or equivalent Phase 6 verification artifact; `${planning_dir}/rca/<failure-id>-verification-critic.md`; `${planning_dir}/rca/gate-set/<failure-id>/aggregate-report.md`; `${planning_dir}/rca/gate-set/<failure-id>/join-manifest.json`; downstream lifecycle artifacts such as `${planning_dir}/post-mortem.md`, `${planning_dir}/action-items.md`, `${planning_dir}/runbooks/`, `${planning_dir}/tracker-comments/`, and `${planning_dir}/rca-close.md`.

Observable signal (assertion shape): A future detector reports a finding if a downstream lifecycle artifact or handoff event is present for the active RCA cycle and the trace/artifact bundle lacks a current Phase 6.5 `apply-gate-set` dispatch with `caller_mode=rca-post-apply`, terminal `PASS`, and no unresolved blocking rows.

Residual-risk note: This scenario consumes the shared operator contract and does not prove child gate logic correctness.

### ACR287-RCA-GATE-002

Scenario name: `ACR287-RCA-GATE-002`.

Behavior under verification: Blocking semantics prevent downstream post-mortem, action-items, runbooks, tracker close, or close-or-pending records when required gate rows are missing, stale, non-LOW, malformed, unsupported, skipped without valid follow-up, or unratified.

Fixture source / evidence anchors: `${planning_dir}/rca/gate-set/<failure-id>/join-manifest.json`; `${planning_dir}/rca/gate-set/<failure-id>/aggregate-report.md`; child report index; skip, bootstrap-exception, ratification, inventory-resolution, and stale-refusal rows; downstream lifecycle artifacts.

Observable signal (assertion shape): A future detector reports a finding if downstream lifecycle artifacts exist after an aggregate status other than `PASS`, or if `PASS` is claimed while the join manifest contains unresolved blocking, stale, missing, non-LOW, malformed, unsupported, unratified, or invalid skip/exception rows.

Residual-risk note: This scenario verifies the block boundary and does not judge the quality of the operator-returned repair route.

### ACR287-RCA-GATE-003

Scenario name: `ACR287-RCA-GATE-003`.

Behavior under verification: Currentness re-verification occurs when RCA Phase 6 returns to Phase 2, Phase 3 revises the fix decision, Phase 4 revises the application plan, or Phase 5 reapplies code. Old manifest rows reused without matching active cycle/head/diff/scope/runtime-claim keys must fire unless stale-refusal evidence blocks handoff.

Fixture source / evidence anchors: Multi-cycle RCA trace; prior and current `${planning_dir}/rca/gate-set/<failure-id>/join-manifest.json`; currentness keys containing `caller_mode`, `cycle_id`, `head_sha`, `base_ref`, diff hash, scope reference/hash, runtime-claim reference/hash, relevant contract/report hashes, producer UUID, and verification time; `STALE_REFUSAL` rows and `next_action` repair route.

Observable signal (assertion shape): A future detector reports a finding if a prior gate-set manifest is accepted for downstream handoff after RCA re-entry without matching the active currentness identity or a blocking `STALE_REFUSAL` / rerun record from `apply-gate-set`.

Residual-risk note: This scenario is bounded to ACR-291/ACR-294 currentness fields and stale-refusal semantics; it does not define the final invalidation algorithm.

### ACR287-RCA-GATE-004

Scenario name: `ACR287-RCA-GATE-004`.

Behavior under verification: Audit-history records include the gate-set evidence field names needed to make the RCA post-apply decision reviewable.

Fixture source / evidence anchors: `${planning_dir}/audit-history.md`; `${planning_dir}/rca/gate-set/<failure-id>/dispatch-manifest.md`; `join-manifest.json`; `aggregate-report.md`; `process-tree-report.md` or `process-tree-not-applicable.md`; operator audit-history append metadata.

Observable signal (assertion shape): A future detector reports a finding if audit history for the active RCA cycle lacks `manifest_path`, `aggregate_report_path`, `process_tree_report_path`, `blocking_rows`, `exception_rows`, `inventory_resolution_rows`, `currentness_key`, `decision`, and `repair_route`, or if those fields point away from the canonical RCA gate-set output root.

Residual-risk note: This scenario checks required metadata presence and path binding, not the final prose rendering of audit history.

### ACR287-RCA-GATE-005

Scenario name: `ACR287-RCA-GATE-005`.

Behavior under verification: `workflows/index.json` remains in parity with `workflows/rca.md` after the RCA workflow gains the post-apply gate boundary.

Fixture source / evidence anchors: `workflows/rca.md` frontmatter and body; the RCA entry in `workflows/index.json`; RCA workflow dispatch contract inputs, expectations, outputs, and non-goals.

Observable signal (assertion shape): A future detector reports a finding if the RCA index entry omits any post-apply gate boundary, required output, blocking semantic, audit-history/currentness expectation, or non-goal that is present in the updated RCA workflow, or if unrelated workflow entries are used to satisfy RCA parity.

Residual-risk note: This scenario is scoped to the RCA entry and does not validate unrelated index entries.

### ACR287-RCA-GATE-006

Scenario name: `ACR287-RCA-GATE-006`.

Behavior under verification: Required RCA adapter inputs are complete when `rca-orchestrator` composes the `apply-gate-set` prompt and dispatch.

Fixture source / evidence anchors: `${scratch_dir}/prompts/<failure-id>-apply-gate-set.md`; `${scratch_dir}/logs/<failure-id>-apply-gate-set.log`; `agents/rca-orchestrator.md` procedure text; canonical RCA artifacts under `${planning_dir}/rca/` and `${planning_dir}/rca/gate-set/<failure-id>/`.

Observable signal (assertion shape): A future detector reports a finding if the gate prompt/dispatch omits any of `caller_mode`, `repo_root`, `worktree_path`, `planning_dir`, `scratch_dir`, `audit_history_path`, `failure_id`, `root_cause_ref`, `fix_decision_ref`, `application_plan_ref`, `applied_artifact_ref`, `original_signal_verification_ref`, `verification_critic_ref`, `actual_diff_ref`, `runtime_claim_ref`, `scope_ref`, `cycle_id`, currentness identity, process-tree inputs when required, or canonical output paths.

Residual-risk note: This scenario assumes the shared operator validates deeper row semantics after the caller supplies the adapter inputs.

### ACR287-RCA-GATE-007

Scenario name: `ACR287-RCA-GATE-007`.

Behavior under verification: ACR-254 proof-risk, validation-integrity, and original-signal rerun wiring remain present and are not counted as the broader gate-set PASS.

Fixture source / evidence anchors: `agents/rca-orchestrator.md` text for Phase 3 fix-decision critic/proof-risk fallback, Phase 6 original-signal rerun, verification critic, and validation-integrity fallback; `${planning_dir}/rca/<failure-id>-proof-risk.md`; `${planning_dir}/rca/<failure-id>-validation-integrity.md`; gate-set manifest rows.

Observable signal (assertion shape): A future detector reports a finding if RCA removes or weakens the original-signal rerun, proof-risk, or validation-integrity critic wiring, or if the RCA gate-set status treats those local prerequisites as sufficient evidence for broader `apply-gate-set` PASS without the required Phase 6.5 manifest and aggregate.

Residual-risk note: This scenario preserves ACR-254 wiring but does not re-audit the ACR-254 child auditors.

### ACR287-RCA-GATE-008

Scenario name: `ACR287-RCA-GATE-008`.

Behavior under verification: File-local `## Declared roles` sections are present on both touched RCA files and list `orchestration`, `parser`, and `validator` with applicable override or justification wording.

Fixture source / evidence anchors: `agents/rca-orchestrator.md`; `workflows/rca.md`; `~/ai/conventions/code-quality.md` declared-role classification rules; Phase 4 code-quality remediation evidence.

Observable signal (assertion shape): A future detector reports a finding if either touched RCA file lacks a near-top `## Declared roles` section, omits any of `orchestration`, `parser`, or `validator`, or lacks wording explaining the file-local override/justification for those roles.

Residual-risk note: This is structural coverage for the two touched RCA files only and does not expand the eval surface beyond ACR-287.
