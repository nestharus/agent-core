---
workflow:
  id: refactoring
workflow_aliases:
  - refactor
workflow_dispatch_contract:
  orchestrator: refactoring-orchestrator
  inputs:
    - target_list
    - repo_root
    - worktree_path
    - planning_dir
    - scratch_dir
    - integration_branch_ref
    - slice_bounds
  expectations:
    - per-PR cycle output lands on the integration buffer
  outputs:
    - per-PR cycle dispatch evidence
    - integration-buffer commit
  non_goals:
    - does not implement cross-file auditor analysis
    - does not manage integration-branch lifecycle cadence
    - does not enumerate existing shims
---
# Refactoring workflow

## Role

Coordinate one refactoring lifecycle above individual per-PR implementation-pipeline WUs.

## Use When

- Use when the work is internal structure reshape with no intended external behavior change.
- Use when the work needs integration-buffer staging, contract-bounded slicing, encapsulate-first handling, or shim lifecycle tracking.
- Use when refactoring targets come from auditor outputs and need one coordinated target-map, encapsulation, verify, and buffer-PR cycle.

## Do Not Use When

- Do not use for work that ships behavioral change, has a user-facing surface, or decomposes as a feature lifecycle; use `~/ai/workflows/feature-development.md`.
- Do not use for one already-scoped implementation WU that does not need refactoring topology; use `~/ai/workflows/implementation-pipeline.md`.
- Do not use for standalone roadmap, prototype, RCA, release, or PR review work.

## Required Inputs

- `target_list` from auditor outputs.
- `repo_root`.
- `worktree_path`.
- `planning_dir`.
- `scratch_dir`.
- `integration_branch_ref`.
- `slice_bounds`.

## Optional Inputs

- `shim_placement_parameters`.
- `prior_refactor_evidence_pointers`.
- `shim_registry_path` (defaults to `~/ai/conventions/active-shims.md`).
- `manager_flavor`.

## Outputs

- Per-PR cycle dispatch evidence.
- Refactor PR targeting the integration buffer.
- Integration-buffer commit.
- Shim registry updates when shims are placed or retired.
- Boundary-unraveling status for follow-up slices.

## Workflow Dispatch Surface

The operator is `agents/refactoring-orchestrator.md`. It coordinates target selection, contract-surface mapping, encapsulation when needed, bounded-slice refactoring, auditor non-regression verification, and PR output to the integration buffer.

The implementation pipeline remains the per-PR engine. This workflow declares the refactoring-level contract around those WUs; it does not re-implement implementation-pipeline phases, author auditor analysis logic, or set buffer lifecycle cadence.

## Phases

0. Phase 0 - Identify refactoring targets via implementation-workflow auditor outputs. Sources include cohesion findings, coupling findings, function-classification findings, push-pull findings, and existing cross-file pattern-analysis outputs (this workflow does not implement cross-file analysis). Use `~/ai/conventions/code-quality.md` as the code-quality and auditor reference.
1. Phase 1 - Map contract surfaces. Use signature grep for Python-style dynamic contracts, artifact-landing grep for emitted artifacts, and cloud-permission maps for IAM, lambda triggers, lifecycle hooks, and other external readers. Follow `~/ai/conventions/refactoring-workflow.md` sections "Dynamic languages and emitted-artifact contracts" and "When there is no contract".
2. Phase 2 - Encapsulate unsafe surfaces. Apply `~/ai/conventions/refactoring-workflow.md` sections "Encapsulate first" and "Encapsulation strategy when external access is uncontrolled". Each placed shim registers in `~/ai/conventions/active-shims.md`.
3. Phase 3 - Refactor within a bounded slice. Each per-PR cycle produces a single commit and targets the integration buffer.
4. Phase 4 - Verify auditor metrics did not regress. Re-run the auditors named in Phase 0 against the slice and verify no regression in the relevant metrics or findings.
5. Phase 5 - Unravel boundaries as slices stabilize. Retire shims when consumers are moved and derisked according to the shim-lifecycle rules in `~/ai/conventions/active-shims.md`.

## Procedure

Follow `agents/refactoring-orchestrator.md`. This workflow doc declares the dispatch contract, inputs, outputs, phases, and stop conditions; the orchestrator doc declares the procedure. Do not re-implement implementation-pipeline phases here.

## Stop Conditions

- Stop when the target is not bounded by an understood contract.
- Stop when an unsafe surface cannot be encapsulated with the supplied authority or evidence.
- Stop when the refactor would ship behavioral change; route to feature-development instead.
- Stop when auditor metrics regress and the regression cannot be resolved inside the current slice.
- Succeed for a per-PR cycle when the refactor PR is opened against the integration buffer with dispatch evidence and the integration-buffer commit identified.

## Escalation

- Route NEEDS_INPUT questions carrying new value, scope, or trade-off decisions to the Work Manager root per `work-manager-operator.md`.
- Escalate behavior-changing work to `~/ai/workflows/feature-development.md` and `~/ai/agents/feature-orchestrator.md`.
- If a slice repeatedly oscillates under auditor or implementation-pipeline gates, shrink or decompose the slice under the active manager flavor instead of weakening the contract-boundary rule.
- If shim retirement is blocked by uncontrolled external consumers, record the blocker in `~/ai/conventions/active-shims.md` and split the consumer-untangling work.

## Cross-references

- `~/ai/conventions/refactoring-workflow.md`
- `~/ai/conventions/active-shims.md`
- `~/ai/agents/refactoring-orchestrator.md`
- `~/ai/conventions/code-quality.md`
- `~/ai/conventions/no-backwards-compatibility.md`
- `~/ai/workflows/feature-development.md`
