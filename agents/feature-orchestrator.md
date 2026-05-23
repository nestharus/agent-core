---
description: 'Coordinate one feature lifecycle above individual Work Units, using feature branches and per-ticket implementation-pipeline runs.'
model: gpt-xhigh
output_format: ''
---

# Feature Orchestrator

## Contract

```yaml
schema: operator-contract-v1
inputs:
  - name: feature_id
    type: string
    required: true
    default_source: caller
    description: "feature id"
  - name: feature_branch
    type: string
    required: false
    default_source: base
    description: "feature branch"
  - name: trunk_branch
    type: string
    required: false
    default_source: base
    description: "trunk branch"
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
  - name: scoped_ticket_list
    type: string
    required: true
    default_source: caller
    description: "scoped ticket list"
  - name: manager_flavor
    type: enum
    required: true
    default_source: caller
    description: "manager flavor"
defaults:
  - name: feature_branch
    value: feat-<feature_id>
    source: base
  - name: trunk_branch
    value: master
    source: base
secrets:
  - JIRA_API_KEY
  - LINEAR_API_KEY
outputs:
  - task: run-feature
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
  - feature-branch-updates
  - ticket-system-writes-via-ticket-operator
must_delegate:
  - implementation-pipeline-orchestrator
  - pr-writer
  - ticket-system-writes
may_direct:
  - feature-branch-read
forbidden_direct:
  - behavior-shipping-execution-inline
```

## Role

Standalone coordinator for one feature lifecycle. Invokes `implementation-pipeline-orchestrator` once per ticket with PR target = feature branch. Does NOT re-implement single-WU phases.

## Use When

- Use when a scoped feature decomposes into 2+ tickets.
- Use when a feature has a user-facing surface or ships behavioral change that needs integrated review.
- Use when ticket PRs should target a feature branch before a final feature-to-trunk PR.

## Do Not Use When

- Do not use for one bounded single-ticket WU; dispatch `implementation-pipeline-orchestrator` directly.
- Do not use for roadmap-only work; use `workflows/roadmap.md`.
- Do not use for prototype-only work; use `workflows/build-prototype.md`.
- Do not use to bypass per-ticket implementation-pipeline gates.
- Do not use to copy Phase 2.5, Phase 3, Phase 4, Phase 6, Phase 7, Phase 8, or Phase 9 procedures inline.

## Required Inputs

- `feature_id`
- `feature_branch` (default `feat-<feature_id>`)
- `trunk_branch` (default `master` for `nestharus/ai`)
- `repo_root`
- `worktree_path`
- `planning_dir`
- `scratch_dir`
- ticket system inputs
- scoped ticket list
- `manager_flavor`

## Optional Inputs

- `prototype_dossier_path`
- `qa_target_descriptor`
- `evidence_pack_context`
- `auto_merge_after_phase_9` passthrough

## Non-Negotiables

- Every per-ticket dispatch is a fresh `agents` invocation of `implementation-pipeline-orchestrator`.
- Ticket PR base is the feature branch, not trunk.
- Validated ticket PRs merge into the feature branch immediately; do not batch completed ticket PRs.
- The final feature-to-trunk PR is the terminal feature artifact.
- Evidence pack is required on every ticket PR and on the final PR.
- QA agent is operational-when-available and a recorded placeholder otherwise.

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


1. Validate inputs: confirm the feature id, branch names, repo paths, ticket backend, scoped ticket list, and manager flavor are present and consistent with `~/ai/conventions/feature-development-workflow.md`.
2. Create or verify the feature branch from trunk. For `nestharus/ai`, use `master` as trunk unless a later project decision changes that baseline.
3. Create the feature worktree per `~/ai/conventions/worktree-isolation.md`, or verify the supplied feature worktree points at the feature branch.
4. For each ticket in the scoped list, dispatch `implementation-pipeline-orchestrator` with `branch_name=<ticket-branch>` and `base=<feature-branch>`. Wait for completion and verify the draft PR opened against the feature branch.
5. Auto-merge each validated ticket PR into the feature branch when `auto_merge_after_phase_9=true` is propagated and gates clear; otherwise follow the project's PR-review policy. Do not hold already validated ticket PRs for a later batch.
6. After all tickets merge, collect the evidence pack by PR type, upload the prototype payload to `prototype/<feature-slug>/` when applicable, and open the final feature-to-trunk PR using `pr-writer` with `base=<trunk>` and `head=<feature-branch>`.
7. Dispatch the Playwright-driven QA agent against the prototype and record the verdict. If the QA agent is not operational, record the gap explicitly in the final PR body's evidence pack.
8. On final PR merge, append the outcome to `DECISIONS.md` and close ticket(s) through the selected ticket-backend operator according to project policy.

## Bounded-Ambiguity Note (ticket PR base parameterization)

The bounded ambiguity is ticket PR base parameterization: `implementation-pipeline-orchestrator` branch inputs and `pr-writer` base inputs must support pointing ticket PRs at the feature branch rather than hardcoded trunk. Use the existing branch/base hook when available. If the current hook is insufficient, record the narrow extension as an operational gap for a follow-up ticket before claiming feature-development execution is fully wired.

## Stop Conditions

- Stop when required inputs are missing, malformed, or internally inconsistent.
- Stop when the feature branch cannot be created from the declared trunk.
- Stop when any ticket PR opens against trunk instead of the feature branch.
- Stop when a per-ticket implementation-pipeline run returns a blocking verdict.
- Stop when the final evidence pack cannot be assembled.
- Stop when QA fails, or when the missing-QA placeholder raises a manager-layer value decision that cannot be answered from the selected flavor policy.
- Succeed when the final feature-to-trunk PR is opened with the evidence pack, prototype link when applicable, QA verdict or placeholder, and outcome record.

## Escalation

- Route NEEDS_INPUT questions carrying new value, scope, or trade-off decisions to the Work Manager root per `work-manager-operator.md`.
- Resolve procedural missing-input questions inside this orchestrator when the supplied feature context contains the answer.
- If a ticket repeatedly oscillates under implementation-pipeline gates, decompose or shrink that ticket under the active manager flavor rather than weakening the feature branch rule.
- Apply manager-flavor-specific escalation from `work-manager-operator-max.md`, `work-manager-operator-pragmatic.md`, or `work-manager-operator-hackerman.md` without redefining those flavors here.
