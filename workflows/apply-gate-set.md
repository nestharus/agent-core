---
description: 'Companion workflow contract for the apply-gate-set operator. Discoverable via workflows/index.json.'
workflow:
  id: apply-gate-set
workflow_dispatch_contract:
  orchestrator: apply-gate-set
  inputs:
    - "caller_mode rca-post-apply, implementation-phase-4, implementation-phase-6, or implementation-phase-8 with repo_root, worktree_path, planning_dir, scratch_dir, audit_history_path, trace/currentness inputs, runtime_claim, scope, and mode-specific artifacts including Phase 4 estimate-writeback disposition"
    - "child gate context including actual diff or proposal/component evidence, process-tree trace path, root invocation UUID, and currentness key fields"
    - "implementation modes carry exact base/head branch, freshly fetched ref, and full SHA; implementation-phase-8 also requires local_coverage_command"
  expectations:
    - "dispatches or consumes active child gate evidence for the selected caller mode and writes a canonical join manifest"
    - "writes expected-process before fanout, joins actual child UUIDs afterward, captures raw trace, and independently audits/hashes every consumed output before aggregate acceptance; Phase 8 additionally production-validates the nested test-audit proof"
    - "projects manifest rows into expected-process evidence and blocks stale, missing, malformed, non-LOW, or unsupported convention-only gate rows"
    - "preserves skip, bootstrap-exception, and inventory-resolution rows without rewriting raw child verdicts"
    - "requires phase-3-estimate-writeback as verified success or policy-disabled non-applicability and rejects forbidden update-estimate children"
  outputs:
    - "apply-gate-set-result-v1 plus mode-scoped dispatch/join/aggregate/expected-process/raw-trace/process-audit artifacts and hashes"
    - "file-first evidence suitable for RCA or implementation-pipeline caller consumption"
  non_goals:
    - "does not wire RCA or implementation-pipeline callers"
    - "does not replace PR-review, code-quality, process-tree, proof-risk, validation-integrity, readiness, or supported-surface gates"
    - "does not author eval specs, pytest tests, verifier scripts, hotfix-skip convention detail, or currentness invalidation rules"
---

# Apply Gate Set Workflow

## Declared roles

`mapper`, `validator`, `orchestration`, `parser`, `formatter`, `accessor`

This workflow's procedural Markdown maps caller modes to the apply-gate-set operator dispatch contract (`mapper`). It validates dispatch evidence presence/currentness against the operator + currentness convention (`validator`). It covers caller-mode dispatch sequencing (`orchestration`). It consumes manifest/report structures (`parser`). It defines caller-facing summary lines (`formatter`). It requires cited canonical-path stat/read evidence (`accessor`).

## Adapter declarations

```yaml
adapter_declarations:
  - component: workflows/apply-gate-set.md
    role: adapter
    Translates:
      - apply-gate-set-discoverability-surface
      - caller-mode-dispatch-contract-surface
      - currentness-policy-citation-surface
```

The three translated surfaces are the complete adapter declaration. The new currentness-policy-citation-surface subordinates all `~/ai/conventions/apply-gate-set-currentness.md` section citations (`Currentness key schema`, `Invalidation trigger matrix`, `Row-level re-verification`, `Full re-dispatch`, `Stale-refusal records`, `Row-kind coverage`) to one translated contract.

## Purpose

Coordinate existing gates after a caller reaches a gate-set boundary. The workflow is the caller-facing contract and discoverability surface for `agents/apply-gate-set.md`, which remains the active procedural owner.

Use this workflow for RCA post-apply, implementation Phase 4, implementation Phase 6, and implementation Phase 8 gate-set boundaries. It requires file-first evidence, active child dispatch or current canonical output evidence, currentness rows, explicit exception rows, expected-process projection, and audit-history records.

Declared roles: `orchestration`, `validator`, `mapper`, `parser`, `formatter`, `accessor`.

## Workflow Dispatch Surface

### Orchestrator

apply-gate-set

### Inputs

- caller_mode rca-post-apply, implementation-phase-4, implementation-phase-6, or implementation-phase-8 with repo_root, worktree_path, planning_dir, scratch_dir, audit_history_path, trace/currentness inputs, runtime_claim, scope, and mode-specific artifacts including Phase 4 estimate-writeback disposition
- child gate context including actual diff or proposal/component evidence, process-tree trace path, root invocation UUID, and currentness key fields
- implementation modes carry exact base/head branch, freshly fetched ref, and full SHA; implementation-phase-8 also requires local_coverage_command

### Expectations

- dispatches or consumes active child gate evidence for the selected caller mode and writes a canonical join manifest
- writes expected-process before fanout, joins actual child UUIDs afterward, captures raw trace, and independently audits/hashes every consumed output before aggregate acceptance; Phase 8 additionally production-validates the nested test-audit proof
- projects manifest rows into expected-process evidence and blocks stale, missing, malformed, non-LOW, or unsupported convention-only gate rows
- preserves skip, bootstrap-exception, and inventory-resolution rows without rewriting raw child verdicts
- requires `phase-3-estimate-writeback` as verified success or policy-disabled non-applicability and rejects forbidden `update-estimate` children

### Outputs

- apply-gate-set-result-v1 plus mode-scoped dispatch/join/aggregate/expected-process/raw-trace/process-audit artifacts and hashes
- file-first evidence suitable for RCA or implementation-pipeline caller consumption

### Non-goals

- does not wire RCA or implementation-pipeline callers
- does not replace PR-review, code-quality, process-tree, proof-risk, validation-integrity, readiness, or supported-surface gates
- does not author eval specs, pytest tests, verifier scripts, hotfix-skip convention detail, or currentness invalidation rules

## Required Inputs

- `caller_mode`: `rca-post-apply`, `implementation-phase-4`, `implementation-phase-6`, or `implementation-phase-8`.
- `repo_root`, `worktree_path`, `planning_dir`, `scratch_dir`, and `audit_history_path`.
- Trace/currentness inputs: runtime-derived root invocation UUID, `cycle_id`, full `head_sha`, diff/scope/runtime/contract/report hashes, producing invocation UUIDs, and verified-at timestamps. Implementation modes also require exact `base_branch`, `base_ref`, `base_sha`, `head_branch`, and `head_ref`; Phase 8 requires non-blank `local_coverage_command`.
- Mode-specific artifacts:
  - `rca-post-apply`: root-cause, fix-decision, application-plan, applied-artifact, original-signal verification, verification critic, actual diff, runtime claim, scope, and cycle id.
  - `implementation-phase-4`: proposal, problem map, risk profile, supported-surface context, complete estimate delta flag, estimate-writeback disposition ref, cold-start disposition ref when inherited is null, touched-surface evidence, and bootstrap-exception refs when claimed.
  - `implementation-phase-6`: Step 6b output index, Step 6a `contract_path`, approved `proposal_path`, `code_quality_dispatch_dir`, Step 6b/6c prompts and logs, component diff, component scope, runtime claim, and side-channel or derivation evidence when applicable.
  - `implementation-phase-8`: actual branch or PR diff, proposal/proof-plan refs, prior join refs when present, runtime claim, supported-surface inventory context, and base/head identity.

## Outputs

- Dispatch manifest.
- Canonical join manifest.
- Aggregate report.
- Expected-process manifest for `~/ai/agents/process-tree-auditor.md`.
- Required independent process-tree report.
- Raw process-tree trace and stable `apply-gate-set-result-v1` with artifact SHA-256 map.
- Audit-history records following `~/ai/conventions/audit-history.md`.
- Optional caller-owned ticket or PR comment payload that mirrors canonical file-backed evidence.

## Expectations

- The operator actively dispatches or verifies child gate evidence. Passive convention-only inheritance is not accepted.
- Every required row carries currentness fields and file-backed proof unless the row is an explicit non-applicability, skip, bootstrap-exception, or inventory-resolution row.
- Child verdicts remain raw and visible. Skip and ratification rows explain advancement rules without rewriting non-LOW outputs.
- Runtime claims and actual diffs are transported into code-quality, proof-risk, and validation-integrity children where applicable.
- Inventory-resolution rows dual-score or fold ACR-285 and ACR-286 readings until those trackers settle.

## Non-goals

- This workflow does not edit RCA or implementation-pipeline caller files.
- This workflow does not replace child gate logic or implement child auditors.
- This workflow does not make ticket comments canonical.
- This workflow does not author eval specs, pytest tests, verifier scripts, final hotfix-skip convention detail, or ACR-294 currentness invalidation rules.

## Caller modes

`rca-post-apply` runs after RCA applies the fix and has current original-signal verification and verification-critic evidence. It requires actual-diff PR-review-style rows, code-quality, proof/runtime rows where applicable, process-tree evidence, skip/ratification/currentness rows, and inventory-resolution rows.

`implementation-phase-4` runs after Phase 3 proposal and estimate write/no-write disposition. It requires a `phase-3-estimate-writeback` row plus proposal-risk rows, supported-surface evidence, proof-risk inventory representation, Phase 4 code-quality, valid bootstrap-exception ratification when claimed, join manifest, process-tree evidence, and audit-history records. The row accepts only verified mutation success or contract-bound `no_write_policy_disabled`; null inherited estimates retain `over_2x: unknown` and require the recorded cold-start disposition.

For `no_write_policy_disabled`, the expected-process manifest contains a selected-ticket-operator `task=update-estimate` pattern with `required: false`, `blocking_if_missing: false`, and `blocking_if_present: true`. A matching child is blocking. For `write_verified`, the manifest requires the producing update invocation, or current exact issue/field/value readback when a migration record proves an earlier verified mutation was reused without a duplicate write.

`implementation-phase-6` runs after Step 6c component evidence exists. It requires Step 6b/6c provenance, tests-contract alignment refs, per-component code-quality, applicable prototype/derivation/halt/swap/non-applicability records, join evidence, process-tree audit #2 projection, and audit-history records. Per-component code-quality child auditors run with `-p ${code_quality_dispatch_dir}`, where `code_quality_dispatch_dir` is the nearest existing common ancestor of absolute `worktree_path` and `planning_dir`; their prompts include absolute `worktree_path`, `contract_path`, and `proposal_path` so the outside-worktree Step 6a contract is read before scoring.

`implementation-phase-8` runs on the already-open exact Phase 7 PR after readiness. It transports the same freshly fetched base/head branch/ref/full SHA bundle and `local_coverage_command` through PR review to test audit, and requires current provider identity plus process-tree audit #3.

## Procedure

1. Validate required inputs and resolve `caller_mode`.
2. Select mode-scoped required gates and row contracts; Phase 4 validates the estimate disposition and its currentness before other gate rows.
3. Build child prompts, dispatch manifest, expected-process skeleton, and expected output paths before fanout.
4. Dispatch required children through the active operator or verify current caller-supplied canonical outputs.
5. Stat, hash, parse, and normalize every canonical output.
6. Write join-manifest rows for gates, applicability, skips, bootstrap exceptions, inventory resolution, stale refusals, and aggregate result.
7. Join actual child UUIDs/output hashes to stable expected nodes and freeze manifests, including forbidden-child evidence for policy-disabled estimate non-applicability.
8. Capture raw trace, run the independent process-tree audit, and require current PASS for every caller mode.
9. Append audit history and write the stable result envelope with all artifact hashes before returning status.

## Manifest schema reference

The canonical schema lives in `agents/apply-gate-set.md` § `Join manifest schema`.

Required row families include required gates, optional gates, applicability, non-applicability, skip, bootstrap-exception, inventory-resolution, stale-refusal, and aggregate rows. Currentness fields cite `~/ai/conventions/apply-gate-set-currentness.md` as canonical policy. Skip rows cite `~/ai/conventions/hotfix-skip-with-followup.md`. Bootstrap-exception rows cite `~/ai/conventions/code-quality.md` § `Bootstrap exception`.

## Currentness

Apply-gate-set currentness rules live in `~/ai/conventions/apply-gate-set-currentness.md`. Caller surfaces cite that convention for `Currentness key schema`, `Invalidation trigger matrix`, `Row-level re-verification`, `Full re-dispatch`, `Stale-refusal records`, and `Row-kind coverage`; this workflow remains the discoverability and dispatch contract, not the invalidation algorithm owner.

## Audit-history reference

Audit-history writes must follow `~/ai/conventions/audit-history.md` § `File Structure` and § `Required Schema`, plus `agents/apply-gate-set.md` § `Audit-history append schema`.

The canonical evidence remains the file set under `planning_dir` and `scratch_dir`. Ticket-system comments are mirrors only.
