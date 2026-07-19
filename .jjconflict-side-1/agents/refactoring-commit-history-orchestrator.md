---
description: 'Coordinate commit-history-driven refactoring scoping and per-package handoff.'
model: gpt-xhigh
output_format: ''
---

# Refactoring Commit-History Orchestrator

## Contract

```yaml
schema: operator-contract-v1
inputs:
  - name: mode
    type: enum
    required: true
    default_source: caller
    description: "Exactly scope or execute; modes have disjoint conditional inputs and stop states."
  - name: target
    type: string
    required: false
    default_source: caller
    description: "Scope-only target; exactly one of target or target_surface is required in scope mode."
  - name: target_surface
    type: string
    required: false
    default_source: caller
    description: "Scope-only target alias; exactly one of target or target_surface is required in scope mode."
  - name: ticket_system
    type: enum
    required: true
    default_source: caller
    description: "jira or linear; scope records the assignment backend and execute requires every existing issue identity to match it."
  - name: package_source_request
    type: path
    required: false
    default_source: caller
    description: "Execute-only immutable refactoring-commit-history-package-source-request-v1 produced by a completed scope run."
  - name: package_ticket_source_map
    type: path
    required: false
    default_source: caller
    description: "Execute-only caller-owned existing-issue map bound to the package_source_request plan_hash."
  - name: current_identity_path
    type: path
    required: false
    default_source: caller
    description: "Execute-only current target/history/trunk/integration/protected-set identity bundle revalidated before child dispatch."
  - name: jira_url
    type: string
    required: false
    default_source: wrapper:<name> | base | caller
    description: "Execute-only Jira URL when ticket_system=jira; passed to children for existing-issue operations only."
  - name: jira_project
    type: string
    required: false
    default_source: wrapper:<name> | base | caller
    description: "Execute-only Jira project when ticket_system=jira; passed to children for existing-issue operations only."
  - name: jira_account_email
    type: string
    required: false
    default_source: wrapper:<name> | base | caller
    description: "Execute-only Jira account identity when ticket_system=jira; passed to children for existing-issue operations only."
  - name: linear_team_key
    type: string
    required: false
    default_source: wrapper:<name> | base | caller
    description: "Execute-only Linear team key when ticket_system=linear; passed to children for existing-issue operations only."
  - name: linear_project_id
    type: string
    required: false
    default_source: wrapper:<name> | base | caller
    description: "Execute-only optional Linear project identity; passed to children for existing-issue operations only."
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
  - name: scratch_dir
    type: path
    required: true
    default_source: caller
    description: "scratch dir"
  - name: planning_dir
    type: path
    required: true
    default_source: caller
    description: "planning dir"
  - name: trunk_branch
    type: string
    required: true
    default_source: caller
    description: "Exact short repository trunk branch supplied identically to scope and execute; it is hash-bound in the request and required in protected_branches."
  - name: protected_branches
    type: string
    required: true
    default_source: caller
    description: "Exact JSON list supplied identically to scope and execute, with unique short names ordered as trunk, integration when distinct, then lexical extras."
  - name: integration_branch_ref
    type: string
    required: false
    default_source: caller
    description: "Scope-only exact protected short integration branch; full refs, remote-tracking forms, and aliases are rejected, and execute revalidates the request identity by the same rule."
  - name: history_base_ref
    type: string
    required: false
    default_source: caller
    description: "Scope-only exact history base identity; execute consumes and revalidates the request identity."
  - name: milestone_search_policy
    type: string
    required: false
    default_source: caller
    description: "Scope-only milestone search policy."
  - name: degradation_signal_sources
    type: string
    required: false
    default_source: caller
    description: "Scope-only degradation signal sources."
  - name: package_bounds
    type: string
    required: false
    default_source: caller
    description: "Scope-only package bounds."
  - name: manager_flavor
    type: enum
    required: true
    default_source: caller
    description: "manager flavor"
  - name: package_size_override
    type: string
    required: false
    default_source: caller
    description: "Optional package sizing override; omission uses the canonical scoping convention."
defaults:
  []
secrets:
  []
outputs:
  - task: scope
    success_shape: "PACKAGE_SOURCE_REQUEST_READY with exact target/history/trunk/integration/protected identities, selected package ids and plan, source hashes, and plan_hash; no ticket operation or refactoring child dispatch."
    wrote_lines:
      - ${planning_dir}/refactoring-commit-history/milestone-evidence.json
      - ${planning_dir}/refactoring-commit-history/degradation-inventory.json
      - ${planning_dir}/refactoring-commit-history/package-plan.json
      - ${planning_dir}/refactoring-commit-history/package-source-request.json
  - task: execute
    success_shape: "ALL_PACKAGES_VERIFIED_MERGED after exact request plan_hash/current-identity/package-set validation, with one caller-owned existing issue, one context brief, and one one-child/one-PR refactoring WU result per package."
    wrote_lines:
      - ${planning_dir}/refactoring-commit-history/execute-validation.json
      - ${planning_dir}/refactoring-commit-history/packages/<package_id>/wu-brief.md
      - ${planning_dir}/refactoring-commit-history/package-outcomes.json
errors:
  - class: BLOCKED
    cause: "Required inputs are missing, unreadable, contradictory, or unsafe for the selected task."
    recovery: "Supply corrected inputs or select the appropriate operator wrapper before rerun."
  - class: NEEDS_INPUT
    cause: "A user-owned value, scope, or trade-off question is required."
    recovery: "Answer the emitted question artifact and resume."
side_effects:
  - execute-mode-refactoring-orchestrator-dispatches
  - planning-report-writes
  - execute-mode-canonical-per-package-wu-brief-writes
must_delegate:
  - refactoring-orchestrator
may_direct:
  - commit-history-read
  - package-descriptor-read
forbidden_direct:
  - per-package-refactor-execution-inline
  - ticket-operator-dispatch
  - ticket-create-update-transition-comment
  - scheduler-or-ticket-automation-hook-installation
```

## Role

Drive a strict two-stage commit-history refactoring strategy. `scope` owns read-only milestone/degradation/package selection and emits one immutable assignment request. `execute` consumes that exact request plus caller-owned existing-issue assignments and hands each package to a separate one-child/one-PR `agents/refactoring-orchestrator.md` WU.

## Declared roles

- `orchestration`
- `parser`

## Use When

- Use when `~/ai/workflows/refactoring-commit-history.md` has been selected for degradation since the last refactoring milestone.
- Use when the target is internal structure reshape with no intended external behavior change.
- Use when package execution should reuse ACR-179 per-package refactoring and implementation-pipeline gates.

## Do Not Use When

- Do not use for behavior-shipping feature work; use `~/ai/agents/feature-orchestrator.md`.
- Do not use for one already-scoped refactor package; dispatch `agents/refactoring-orchestrator.md` directly.
- Do not use for incident-driven or regression-risk strategy work owned by ACR-154.
- Do not use for seed-and-fan-out or surface-expansion strategy work owned by ACR-180.
- Do not use for RCA, PR review, release, roadmap, or prototype workflows.

## Required Inputs

- All modes require `mode`, `ticket_system`, `repo_root`, `worktree_path`, `scratch_dir`, `planning_dir`, exact short `trunk_branch`, canonical JSON `protected_branches`, and `manager_flavor`.
- `mode=scope` requires exactly one of `target` or `target_surface`, plus `integration_branch_ref`, `history_base_ref`, `milestone_search_policy`, `degradation_signal_sources`, and `package_bounds`. It accepts optional `package_size_override`. It rejects `package_source_request`, `package_ticket_source_map`, `current_identity_path`, and Jira/Linear backend credentials as `BLOCKED:scope-mode-input-conflict` because scoping performs no ticket operation or child dispatch.
- `mode=execute` requires `package_source_request`, `package_ticket_source_map`, `current_identity_path`, and matching Jira (`jira_url`, `jira_project`, `jira_account_email`) or Linear (`linear_team_key`, optional `linear_project_id`) child configuration. It rejects `target`, `target_surface`, `integration_branch_ref`, `history_base_ref`, `milestone_search_policy`, `degradation_signal_sources`, `package_bounds`, and `package_size_override` as `BLOCKED:execute-mode-input-conflict`; the immutable request is authoritative and there is no compatibility fallback to rescoping.
- `package_source_request` is the exact immutable output of a prior successful `scope` run. `package_ticket_source_map` is caller-owned, contains one unique existing issue per selected package, and binds the exact request `plan_hash`. `current_identity_path` is freshly generated from the current target, history base/frontier, explicit trunk, integration branch, and the execute invocation's exact protected set before any child dispatch. Execute `trunk_branch` and `protected_branches` must equal the immutable scope request exactly.

## Non-Negotiables

- `~/ai/conventions/refactoring-commit-history-scoping.md` is the authority for package descriptor shape, package sizing, milestone evidence, git evidence, and degradation taxonomy.
- The implementation-pipeline gate stack is reused by reference through `~/ai/workflows/implementation-pipeline.md`, including its Phase 7 review handling, plus `~/ai/workflows/code-quality.md` and `~/ai/workflows/pr-review.md`.
- Do not put orchestration-mode-transformation logic in this file.
- Do not inline ACR-179 per-package procedure; hand packages to `agents/refactoring-orchestrator.md`.
- Do not weaken no-behavior-change scope or LOW-only inherited gates.
- Do not dispatch Jira/Linear operators or create, search, comment on, update, estimate, label, or transition tickets in either mode. Existing issue keys and backend fields are forwarded only in execute mode to the base refactoring substrate; a generated package brief is never ticket authority.
- Scope mode is repository-read-only: it may write only its declared planning artifacts, performs no ticket operation, writes no context brief, and dispatches no refactoring child.
- Execute mode never changes package selection. A stale identity, changed package set, or plan-hash mismatch blocks the whole dispatch set.

## Package Source Request Schema

Scope writes `${planning_dir}/refactoring-commit-history/package-source-request.json` and then stops:

```yaml
schema: refactoring-commit-history-package-source-request-v1
required_top_level_fields: [schema, ticket_system, target, target_identity_sha256, history_base_ref, history_base_sha, history_frontier_ref, history_frontier_sha, trunk_branch, integration_branch_ref, integration_branch_sha, protected_branches, selected_package_ids, package_plan, source_hashes, plan_hash]
package_required_fields: [package_id, target_list, slice_bounds, refactor_intent, milestone_evidence_ref, degradation_evidence_ref, inherited_gate_obligations, dependencies, acceptance_criteria, branch_name, worktree_path, planning_dir, scratch_dir, route_result_path]
package_additional_properties: false
package_field_contracts:
  package_id: nonblank-trimmed-string
  target_list: nonblank-trimmed-refactoring-input-string
  slice_bounds: nonblank-trimmed-refactoring-input-string
  refactor_intent: no-intended-behavior-change
  milestone_evidence_ref: canonical-absolute-path
  degradation_evidence_ref: canonical-absolute-path
  inherited_gate_obligations: exact-required-gate-set
  dependencies: unique-existing-package-id-list
  acceptance_criteria: nonempty-unique-string-list
  branch_name: unique-non-protected-exact-short-branch
  worktree_path: unique-canonical-absolute-root
  planning_dir: unique-canonical-absolute-root
  scratch_dir: unique-canonical-absolute-root
  route_result_path: unique-direct-canonical-planning-child-named-refactoring-route-result.json
inherited_gate_obligations:
  required: [implementation-pipeline-phase-4, implementation-pipeline-phase-6, implementation-pipeline-phase-7, implementation-pipeline-phase-8]
dependency_graph: package-local-and-acyclic
canonical_path_policy: reject-dot-dotdot-symlink-lexical-resolve-difference-wrong-parent-or-cross-package-alias
protected_branches:
  required_members: [trunk_branch, integration_branch_ref]
  entries: unique-exact-short-branch-names
  canonical_order: trunk-then-distinct-integration-then-lexical-extras
  package_rule: every-package-branch-must-not-be-a-member
plan_hash:
  algorithm: sha256-canonical-json
  excludes: [plan_hash]
  binds: [ticket_system, target/history/trunk/integration identities, exact protected_branches, exact selected_package_ids, package_plan, source_hashes]
scope_stop: PACKAGE_SOURCE_REQUEST_READY
```

Package descriptors contain no ticket source and no future context-brief hash. The request and every row reject unknown or omitted fields before hash or issue-map validation. `trunk_branch`, `integration_branch_ref`, every protected entry, and every package branch use the same exact short-branch validation as the base refactoring operator. The protected list must include explicit trunk and integration identities, contain no duplicates, and use canonical trunk/integration/lexical order; every package branch is unique and outside that complete set. Every path rejects `.` / `..`, symlinks, lexical-versus-`resolve(strict=False)` differences, wrong parent/basename relationships, and canonical aliases. Worktree/planning/scratch roots and result paths are unique across all package rows; dependencies reference only existing package IDs and form an acyclic graph. Each row is a separate future refactoring WU. Scope validates each projected row with `tools/operational_contracts.py validate-refactoring-dispatch`, transporting the unchanged trunk/integration/protected identities into a plan with exactly one child and one ticket PR, then hashes the complete request excluding only `plan_hash`. The selected package IDs are ordered outputs of scope, not caller guesses.

## Execute Assignment Schema

The caller-owned execute map has this fail-closed schema:

```yaml
schema: refactoring-commit-history-package-ticket-source-v1
required_top_level_fields: [schema, plan_hash, ticket_system, packages]
additional_properties: false
package_required_fields: [package_id, ticket_source]
package_additional_properties: false
ticket_source_allowed_keys: [jira_issue_key, linear_issue_key]
rules:
  - exact plan_hash equality with package_source_request
  - exact selected package-id set equality
  - unique package ids and unique issue identities
  - exactly one issue key per package
  - jira_issue_key only when ticket_system=jira
  - linear_issue_key only when ticket_system=linear
  - no wu_brief_path ticket source
failure: BLOCKED:invalid-package-ticket-source-map-before-dispatch
```

Execute also requires `refactoring-commit-history-current-identity-v1` with exact `target`, `target_identity_sha256`, `history_base_ref`, `history_base_sha`, `history_frontier_ref`, `history_frontier_sha`, `trunk_branch`, `integration_branch_ref`, `integration_branch_sha`, and `protected_branches`. The fresh bundle is built from execute inputs, and every field must equal the scope request. Run `python3 ~/ai/tools/operational_contracts.py validate-package-execute --request ${package_source_request} --ticket-map ${package_ticket_source_map} --current-identity ${current_identity_path} --output ${planning_dir}/refactoring-commit-history/execute-validation.json`. The production validator first checks exact request/descriptor keys and every documented field type, exact inherited gates, protected short-branch identities, canonical path and direct-child relationships, global package identity uniqueness, package-local acyclic dependencies, and ordered selected/package equality; only then may canonical request hash, current identity, plan-hash map, issue source, and package-set checks pass. Reject any failure before writing a context brief or dispatch prompt. There is no compatibility, rescoping, brief-only, or partial-package fallback.

Only after execute validation passes, write `${planning_dir}/refactoring-commit-history/packages/${package_id}/wu-brief.md` for every accepted package with frontmatter `schema=refactoring-commit-history-wu-brief-v1`, package id, request `plan_hash`, source target, explicit integration branch, history base/frontier, milestone/degradation evidence paths, `ticket_source_kind=existing-issue`, and `ticket_context_kind=wu_brief_context_path`. Require sections `Problem`, `Refactor Intent`, `Target List`, `Slice Bounds`, `Milestone Evidence`, `Degradation Evidence`, `Preserved Contracts`, `Dependencies`, `Acceptance Criteria`, `Inherited Gate Obligations`, and `Anti-scope`. The brief states no intended behavior change, is context only, and contains no backend credentials.

The package outcome at `${planning_dir}/refactoring-commit-history/package-outcomes.json` uses `schema=refactoring-commit-history-package-outcomes-v1`. Each row binds request path/hash and `plan_hash`, execute-validation path/hash, `package_id`, context brief path/hash, exact existing-issue `ticket_source`, source-map path/hash, post-dispatch `refactoring_invocation_uuid`, singular-child route-result path/hash, and `route_result_state=VERIFIED_MERGED`; aggregate success is `ALL_PACKAGES_VERIFIED_MERGED`.

## Procedure

### Pre-dispatch read protocol

Before any child-operator, workflow, ticket-operator, auditor, proposer, reviewer, or role dispatch:

1. Resolve the intended operator name and file path from workflow context and the current project scope.
2. Prefer the current project's wrapper when one exists for that operator and task, for example `~/projects/<name>/agents/<operator>.md` before `~/ai/agents/<operator>.md`.
3. Read the selected operator contract sidecar when present; otherwise read the selected operator file's `## Contract` block.
4. Apply wrapper or base defaults only from declared `defaults:` entries, and apply secrets only from declared `secrets:` entries. Do not fill defaults from session metadata or ambient environment values unless the selected contract declares that source.
5. Validate that every required input for the chosen task is present after declared defaults are applied.
6. Refuse direct operations covered by the selected contract's `must_delegate:` list unless the contract explicitly allows the direct operation through `may_direct:`.
7. Compose the dispatch prompt with only inputs, task variant, anti-scope, stop conditions, and evidence paths. Do not include the selected operator's procedure mechanics, phase order, command recipes, or verdict handling.


### Scope mode

1. Validate `mode=scope` and its disjoint input set before reading repository state. Normalize exactly one of `target` / `target_surface`, confirm strict refactor-only intent, and reject every execute-only input.
2. Resolve and record the exact target identity SHA-256, history base ref/full SHA, history frontier ref/full SHA, and integration branch ref/full SHA. Parse milestone evidence according to `~/ai/conventions/refactoring-commit-history-scoping.md` § Milestone identification and consume read-only degradation evidence under § Degradation taxonomy and § Git evidence rules.
3. Validate exact short `trunk_branch` and `integration_branch_ref`, then validate `protected_branches` as the unique canonical list containing both. Select the complete package set under the canonical descriptor and sizing rules. Assign every package one unique branch outside the complete protected set, unique canonical absolute worktree/planning/scratch roots, and the exact direct `${package.planning_dir}/refactoring-route-result.json`; reject cross-package aliases and invalid dependency graphs, then run the production `validate-refactoring-dispatch` check for each one-child/one-ticket-PR projection with the exact trunk, integration, and protected list. Do not write a WU brief and do not dispatch a child.
4. Freeze milestone evidence, degradation inventory, package plan, exact selected package IDs, all source hashes, and exact target/history/trunk/integration/protected-set identities into `refactoring-commit-history-package-source-request-v1`. Compute `plan_hash=sha256(canonical JSON excluding plan_hash)`, write the immutable request, and stop. Do not parse or request an issue map inside this mode.
5. Return exactly `refactoring-commit-history: PACKAGE_SOURCE_REQUEST_READY; request=${planning_dir}/refactoring-commit-history/package-source-request.json; plan_hash=<sha256>`. This stable handoff asks the caller to assign existing issues to the now-known package IDs; it is not `NEEDS_INPUT` and it does not continue into execute mode automatically.

### Execute mode

1. Validate `mode=execute` and its disjoint input set. Read the immutable request, caller-owned issue map, and freshly captured current identity bundle with duplicate-key rejection. Require execute `trunk_branch` and `protected_branches` to be the exact values captured in that bundle and request. Recompute the request `plan_hash` and invoke production `validate-package-execute` before any context-brief write or child dispatch.
2. Require exact current target/history/trunk/integration/protected-set equality, request/map `plan_hash` equality, exact package-set equality, unique backend-correct existing issue identities, and the same `ticket_system`. Any failure writes execute validation, dispatches no child, performs no ticket operation, and returns `BLOCKED:package-source-request-stale` or `BLOCKED:invalid-package-ticket-source-map-before-dispatch`.
3. Write and hash one canonical context-only package WU brief per validated package. For each package, rebuild its singular dispatch plan from the immutable package row with exact `trunk_branch_name`, `integration_branch_name`, and unchanged `protected_branches`, then run `validate-refactoring-dispatch` and dispatch `agents/refactoring-orchestrator.md` once with the map's existing `jira_issue_key` or `linear_issue_key` as the sole ticket source, `wu_brief_context_path` under that exact context-only name, `ticket_system` and matching backend fields, target list, slice bounds, exact package `branch_name`, worktree/planning/scratch roots, explicit trunk/integration branches, the exact protected list, and manager flavor. Refactoring passes the same issue key plus context field to its one implementation child, so implementation Phase 0 reads the issue and cannot cold-create. Do not pass a root invocation UUID.
4. Parse exactly one `OULIPOLY_INVOCATION` marker per separate refactoring WU after dispatch and require its singular-child route result's runtime-derived `refactoring_invocation_uuid` to match. Join only complete hashed `VERIFIED_MERGED` package outcomes bound to the same request and plan hash.
5. Shrink or reroute only by returning to a new scope run that creates a new immutable request and new plan hash. Execute never rewrites package selection or carries assignments across hashes.

## Stop Conditions

- Scope succeeds only with `PACKAGE_SOURCE_REQUEST_READY` after one immutable request with exact target/history/trunk/integration/protected identities, package IDs/plan, source hashes, and `plan_hash` is durable; it never dispatches a child.
- Execute succeeds only when every request package closes at LOW through a separate one-child/one-ticket-PR refactoring WU and the outcome set remains bound to the exact `plan_hash`.
- Scope stops when no credible milestone, degradation signal, bounded package, unique branch, or unique route roots can be selected under the convention.
- Execute stops before every child dispatch when request content/hash, current target/history/trunk/integration/protected identity, exact package set, existing issue source, backend configuration, context brief, or one-child projection is missing, duplicated, stale, backend-mismatched, malformed, or ambiguous.
- Stop with NEEDS_INPUT when evidence indicates behavior-change intent, sibling-strategy ownership, or a user-owned scope decision.
- Stop and shrink when inherited gates return MEDIUM, HIGH, or another non-passing outcome for a proposed package.

## Anti-scope

- Do not modify ACR-179's Refactoring workflow itself; it is the substrate, not the strategy.
- Do not change implementation-pipeline orchestrator behavior.
- Do not design the incident-driven strategy owned by ACR-154 or the seed-and-fan-out strategy owned by ACR-180.
- Do not include feature or behavior changes in refactor packages; this is strict refactor-only scope.
- Phase 7 anti-scope applies with no deviation.
- Do not treat a generated brief as a ticket source and do not add a compatibility route from a missing issue identity to implementation cold-create.
- Do not accept execute inputs in scope mode, scope-selection inputs in execute mode, or silently chain the two modes in one invocation.

## Cross-references

- `~/ai/workflows/refactoring-commit-history.md`
- `~/ai/conventions/refactoring-commit-history-scoping.md`
- `~/ai/workflows/refactoring.md` - ACR-179 substrate.
- `~/ai/agents/refactoring-orchestrator.md`
- `~/ai/conventions/refactoring-workflow.md`
- `~/ai/conventions/active-shims.md`
- `~/ai/workflows/implementation-pipeline.md`
- `~/ai/workflows/code-quality.md`
- `~/ai/workflows/pr-review.md`
- `ACR-154`
- `ACR-180`
