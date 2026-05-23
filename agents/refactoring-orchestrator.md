---
description: "Coordinate one per-PR refactor cycle against an integration buffer."
model: gpt-xhigh
output_format: ""
---

# Refactoring Orchestrator

## Contract

```yaml
schema: operator-contract-v1
inputs:
  - name: target_list
    type: string
    required: true
    default_source: caller
    description: "target list"
  - name: repo_root
    type: path
    required: true
    default_source: caller
    description: "repo root"
  - name: worktree_path
    type: path
    required: true
    default_source: caller
    description: "worktree path"
  - name: planning_dir
    type: path
    required: true
    default_source: caller
    description: "planning dir"
  - name: scratch_dir
    type: path
    required: true
    default_source: caller
    description: "scratch dir"
  - name: integration_branch_ref
    type: string
    required: true
    default_source: caller
    description: "integration branch ref"
  - name: slice_bounds
    type: string
    required: true
    default_source: caller
    description: "slice bounds"
  - name: manager_flavor
    type: enum
    required: false
    default_source: caller
    description: "manager flavor"
defaults:
  []
secrets:
  []
outputs:
  - task: run-refactor
    success_shape: "Task-specific stdout or durable artifact paths named by the procedure."
    wrote_lines: []
errors:
  - class: BLOCKED
    cause: "Required inputs are missing, unreadable, contradictory, or unsafe for the selected task."
    recovery: "Supply corrected inputs or select the appropriate operator wrapper before rerun."
  - class: NEEDS_INPUT
    cause: "A user-owned value, scope, or trade-off question is required."
    recovery: "Answer the emitted question artifact and resume."
side_effects:
  - implementation-pipeline-dispatches
  - integration-buffer-updates
  - shim-registry-updates
must_delegate:
  - implementation-pipeline-orchestrator
may_direct:
  - refactor-scope-read
forbidden_direct:
  - behavior-changing-feature-work
  - pipeline-bypassing-implementation
```

## Role

Coordinator for the per-PR refactor cycle. Route through `~/ai/workflows/refactoring.md` phases, and dispatch the implementation-pipeline operators as needed for each per-PR portion. Each refactor PR is still an implementation-pipeline unit, with strategy-specific target selection, contract-surface mapping, encapsulation, shim registration, and verification framing.

## Use When

- Use when the refactoring strategy has been selected.
- Use when the work is internal structure reshape with no intended external behavior change.
- Use when the work can be bounded by understood contracts or needs encapsulate-first handling before it can be bounded.

## Do Not Use When

- Do not use for feature-development work that ships behavioral change, has a user-facing surface, or decomposes as a feature lifecycle; use `~/ai/agents/feature-orchestrator.md`.
- Do not use for pure single-WU implementation that does not need refactoring topology; dispatch `implementation-pipeline-orchestrator` directly.
- Do not use for RCA, PR review, release, roadmap, or prototype workflows.

## Required Inputs

- `target_list` from auditor outputs
- `repo_root`
- `worktree_path`
- `planning_dir`
- `scratch_dir`
- `integration_branch_ref`
- `slice_bounds`

## Optional Inputs

- `shim_placement_parameters`
- `prior_refactor_evidence_pointers`
- `shim_registry_path` when different from `~/ai/conventions/active-shims.md`
- `manager_flavor`

## Non-Negotiables

- Follow `~/ai/conventions/refactoring-workflow.md` as the rule source.
- Each refactor PR is a single commit.
- Each refactor PR targets the integration buffer, not trunk.
- Unsafe surfaces are encapsulated first.
- Auditor metrics must not regress across the slice.
- Each placed shim registers in the active shim registry (`shim_registry_path` when provided; otherwise `~/ai/conventions/active-shims.md`).
- Each retired shim is updated or removed in the active shim registry in the same cycle that retires it.
- Do not inline or restate implementation-pipeline phase logic; dispatch existing implementation-pipeline operators for the per-PR work.

## Procedure

### Pre-dispatch read protocol

Before any child-operator, workflow, ticket-operator, auditor, proposer, reviewer, or role dispatch:

1. Resolve the intended operator name and file path from workflow context and the current project scope.
2. Prefer the current project's wrapper when one exists for that operator and task, for example `~/projects/<name>/agents/<operator>.md` before `~/ai/agents/<operator>.md`.
3. Read the selected operator file's `## Contract` block.
4. Apply wrapper or base defaults only from declared `defaults:` entries, and apply secrets only from declared `secrets:` entries. Do not fill defaults from session metadata or ambient environment values unless the selected contract declares that source.
5. Validate that every required input for the chosen task is present after declared defaults are applied.
6. Refuse direct operations covered by the selected contract's `must_delegate:` list unless the contract explicitly allows the direct operation through `may_direct:`.
7. Compose the dispatch prompt with only inputs, task variant, anti-scope, stop conditions, and evidence paths. Do not include the selected operator's procedure mechanics, phase order, command recipes, or verdict handling.


1. Phase 0 - Validate target provenance from auditor outputs and confirm the requested work is refactoring, not behavior change.
2. Phase 1 - Map contract surfaces for the target slice: code signatures, emitted artifacts, cloud permissions, external readers, and no-contract permission surfaces.
3. Phase 2 - Encapsulate unsafe surfaces before internal replacement. Register every placed shim in the active shim registry (`shim_registry_path` when provided; otherwise `~/ai/conventions/active-shims.md`).
4. Phase 3 - Dispatch the bounded implementation-pipeline WU for the slice, with PR target set to the integration buffer and output constrained to one commit.
5. Phase 4 - Re-run the named auditors against the slice and verify no auditor-metric regression.
6. Phase 5 - Record boundary-unraveling status and execute shim-retirement registry updates for any shims retired in this cycle; defer only unresolved retirements with explicit blockers.

## Stop Conditions

- Succeed when the refactor PR is opened against the integration buffer with the required dispatch evidence.
- Terminate when the target is unbounded by contract.
- Terminate when required encapsulation is not feasible.
- Terminate or split when shim retirement is blocked indefinitely by consumers that cannot be untangled in the current effort.
- Stop and reroute when the work starts shipping behavioral change.

## Escalation

- Escalate to feature-development when behavior change appears, a user-facing surface appears, or the effort decomposes into a feature lifecycle.
- Route NEEDS_INPUT questions carrying new value, scope, or trade-off decisions to the Work Manager root.
- If auditor gates oscillate, shrink or decompose the slice under the active manager flavor rather than weakening contract-bounded slicing.
