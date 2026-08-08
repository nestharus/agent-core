---
id: acr-254-workflow-wiring
slug: acr-254-workflow-wiring
lifecycle: WRITE
lifecycle_state: WRITE
created: 2026-05-18
risk_class: HIGH
scope: Active verification-plan-review and validation-integrity workflow wiring
behavior_class: Cross-workflow reviewer selection and evidence-role separation
severity_when_fires: HIGH
evidence_source_kinds:
  - workflow
  - operator
  - contract
  - dispatch-manifest
  - join-manifest
  - report
suggested_action_class: restore-current-reviewer-wiring-and-distinct-evidence-transport
supersedes: []
---

# ACR-254 Workflow Wiring Eval

## Purpose

This WRITE-state specification describes the active wiring contract for
`agents/verification-plan-reviewer.md` and
`agents/validation-integrity-auditor.md`. It is not executable and is not proof
that any scenario passed.

The plan reviewer assesses a pre-execution `## Verification plan`; the
validation-integrity auditor reviews an actual diff and supplied post-change
evidence. Neither review is the experiment that produced an observed result.

## Finding Contract

Future findings retain `eval_id`, `severity`, `evidence_paths`, `summary`,
`suggested_action`, and `confidence`, plus caller mode, phase, gate name,
operator path, report path, input refs/hashes, and blocking status.

## Scenarios

### ACR254-WW-001: Phase 3 requires the canonical verification plan

Expected source shape:

```text
## Verification plan
**Behavior claim**:
**Experiment command or action**:
**Expected observation**:
**Claim-experiment fit**:
```

Fire when implementation or RCA proposal production omits, duplicates, or
renames a field, or treats plan acceptance as an observed result.

### ACR254-WW-002: Phase 4 has an independent plan-review row

Expected row:

```text
gate_name=verification-plan-review
operator=agents/verification-plan-reviewer.md
report=risk/NN-verification-plan-review.md
model=gpt-xhigh
```

The row may use the temporary ACR-285 inventory-resolution representation only
when `dual_score` or `folded_equivalent` preserves equivalent current blocking
semantics.

### ACR254-WW-003: validation-integrity receives actual-diff evidence

Expected Phase 8 inputs include `diff_path`, `runtime_claim`, optional
`runtime_artifact_evidence_path`, and the exact `gpt-high` operator contract.
Fire when proposal review substitutes for actual-diff review or model reading
substitutes for executed evidence.

### ACR254-WW-004: code-quality selects plan review from plan context

Expected inputs include `proposal_path`, `verification_plan_excerpt`, and
`behavior_claim`. The manifest selects `verification-plan-reviewer` and writes
`reports/verification-plan-reviewer.md`.

Fire when the row is marked non-applicable despite current proposal or behavior
claim context, or when `runtime_claim` is used as an alias for all three fields.

### ACR254-WW-005: Phase 6 children receive the Step 6a contract

Both specialized reviewers receive absolute `worktree_path`, `contract_path`,
and `proposal_path` when Phase 6 context applies. An unreadable contract is
`BLOCKED:unreadable-contract-path`, not permission for generic judgment.

### ACR254-WW-006: RCA reviews before apply and verifies after apply

The fix-decision critic requires the canonical four fields and writes
`<failure-id>-verification-plan-review.md`. After application, RCA reruns the
original signal and records exact command, target, expected result, observed
result, output, and status before validation-integrity and post-apply gates can
advance.

### ACR254-WW-007: reports and findings use current identities

Verification-plan findings use `VPR-*`. Active paths and rows contain
`verification-plan-reviewer`, `verification-plan-review`,
`verification_plan_excerpt`, and `behavior_claim`. No old selectable operator,
gate, report, or field alias remains.

### ACR254-WW-008: favorable reviews do not claim execution

Fire when a `LOW`, aggregate `PASS`, validator acceptance, writer output, or
human approval is described as the experiment's observed result. Non-fire when
the review says only that a plan or evidence set is suitable, complete, or
supported at its stated scope.

## Required Cross-Surface Evidence

- `conventions/behavioral-proof.md`
- `agents/verification-plan-reviewer.md` and optimized sidecar
- `agents/validation-integrity-auditor.md` and optimized sidecar
- implementation-pipeline workflow/operator and sidecars
- code-quality workflow and sidecar
- RCA workflow/operator and sidecars
- apply-gate-set workflow/operator and sidecars
- current generated workflow index

## Lifecycle Notes

Lifecycle is `WRITE`. Runnable detectors, fixture execution, and enforcement
transitions are downstream work.
