# ACR-289 / ACR-285 Dependency Note: Verification-Plan-Review Inventory Drift

## Purpose

This note records the active ACR-285 dependency for verification-plan-review
inventory resolution while `apply-gate-set` serves RCA and implementation
caller modes. It updates the public semantic identity without settling
ACR-285's existing inventory-shape decision.

The behavioral-evidence boundary is defined by
`conventions/behavioral-proof.md`. The affected row assesses whether a proposed
experiment is direct and executable; it does not record that the experiment ran.

## Drift

- Tracker: `ACR-285`.
- Inventory name: `verification-plan-review`.
- Reviewer: `agents/verification-plan-reviewer.md`.
- Workflow-derived callers may represent the review as a distinct Phase 4 row.
- Orchestrator-derived callers may represent equivalent blocking review inside
  a code-quality aggregate.
- Until ACR-285 settles that shape, `apply-gate-set` must preserve both readings
  rather than silently selecting one.

## Canonical Inventory Resolution

Inventory-resolution rows use:

- `inventory_name`: `verification-plan-review` or `supported-surface`
- `tracker_ref`: `ACR-285` or `ACR-286`
- `selected_disposition`: `dual_score`, `folded_equivalent`, `standalone`,
  `non_applicable`, or `settled_canonical`
- `source_inventory_refs`, `available_readings`, `fold_target_gate`,
  `dual_scores`, `rationale`, and `expires_when`

Use `dual_score` where both readings affect blocking semantics. Use
`folded_equivalent` only when the cited child aggregate preserves the same
verification-plan inputs, reviewer authority, verdict, currentness, and
blocking behavior. A favorable review remains pre-execution assessment.

## Active Callers

- `agents/apply-gate-set.md` owns the inventory-resolution row schema and keeps
  `dual_score` and `folded_equivalent` behavior unchanged.
- `agents/implementation-pipeline-orchestrator.md` requires the
  `verification-plan-review` row or explicit ACR-285 inventory-resolution row
  before Phase 4 advances.
- `agents/rca-orchestrator.md` requires verification-plan review before
  application planning when a fix decision is missing, malformed, or proxy-only.
- Phase 8 transports `verification_plan_excerpt` and `behavior_claim`
  separately from post-change `runtime_claim` and executed evidence.

## Currentness

`conventions/apply-gate-set-currentness.md` applies the unchanged currentness
and stale-refusal contract to inventory-resolution rows. A change to the
verification plan, behavior claim, reviewer source, authority, scope, contract,
or cited aggregate invalidates reuse.

## Non-Goals

- Do not settle whether ACR-285 chooses standalone or folded representation.
- Do not weaken row hashing, currentness, active dispatch, blocking aggregation,
  or process-tree evidence.
- Do not use the inventory-resolution row as an experiment record.

## Expiry

This note remains active until ACR-285 ships a resolution document and the
`apply-gate-set` schema removes the temporary `dual_score` and
`folded_equivalent` alternatives for this inventory.

## Links

- ACR-285: <https://linear.app/oulipoly/issue/ACR-285>
- ACR-289: <https://linear.app/oulipoly/issue/ACR-289>
- Sibling supported-surface note:
  `notes/acr-290-acr-286-supported-surface-drift.md`
