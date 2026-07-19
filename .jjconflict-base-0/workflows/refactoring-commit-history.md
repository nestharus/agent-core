---
workflow:
  id: refactoring-commit-history
workflow_dispatch_contract:
  orchestrator: "refactoring-commit-history-orchestrator"
  inputs:
    - "required in both scope and execute: mode, ticket_system, repo_root, worktree_path, planning_dir, scratch_dir, exact short trunk_branch, canonical JSON protected_branches, and manager_flavor"
    - "scope mode also requires target or target_surface, integration_branch_ref, history_base_ref, milestone_search_policy, degradation_signal_sources, package_bounds, and optional package_size_override; it rejects execute inputs"
    - "execute mode also requires immutable package_source_request, caller-owned package_ticket_source_map, current_identity_path, and matching Jira or Linear existing-issue child configuration; it rejects scope-selection inputs and requires trunk/protected equality with scope"
  expectations:
    - "scope is repository-read-only, selects milestone/degradation/packages, writes exact target/history/trunk/integration identities plus the canonical protected set, package plan, source hashes, and plan_hash to one immutable package-source request, performs no ticket operation, and dispatches no child"
    - "execute validates exact complete package descriptors, immutable trunk/integration/protected short-branch equality, every package branch outside that set, canonical unique roots/results, exact inherited gates, and a package-local acyclic dependency graph before plan_hash, current identity, package-map acceptance, context brief, or child dispatch"
    - "every package maps to one unique caller-owned backend-matching existing issue and one separate one-child/one-ticket-PR refactoring WU; generated WU briefs are context only"
    - "passes each existing issue key, normalized branch and unique roots, plus wu_brief_context_path through refactoring to implementation so Phase 0 cannot cold-create; captures each route UUID and accepts only a matching singular-child hashed VERIFIED_MERGED result"
  outputs:
    - "scope: last-refactor milestone evidence, degradation inventory, bounded package plan, and immutable package-source request with plan_hash"
    - "execute: currentness/package-map validation, canonical per-package context briefs, exact existing-issue handoffs bound to plan_hash, and package outcomes with runtime route identities"
  non_goals:
    - "does not modify the base ACR-179 refactoring substrate"
    - "does not design incident-driven or seed-and-fan-out sibling strategies"
    - "does not introduce behavior or feature changes"
    - "does not add scheduler or ticket-automation hooks"
    - "does not create, search, comment on, update, estimate, label, or transition tickets in either mode"
---
# Refactoring commit-history workflow

## Workflow Dispatch Surface

The operator is `refactoring-commit-history-orchestrator`. Its exact dispatch contract is the frontmatter above. A `scope` invocation selects and freezes the package IDs before any issue assignment exists, emits `PACKAGE_SOURCE_REQUEST_READY`, and stops. A later `execute` invocation requires that exact request plus a caller-owned existing-issue map bound to its `plan_hash`, revalidates current identities and package equality, then passes each issue key plus context-only `wu_brief_context_path` to one separate refactoring WU. The root performs no ticket operation in either mode.

## Use When

- Use manually when a user selects commit-history-driven refactoring for a target file, module, or package.
- Use after an implementation lands when the user wants a follow-up refactor WU on touched files, with no automatic scheduler behavior implied.
- Use on a periodic cadence only when a caller explicitly supplies the target and evidence inputs for hot areas.
- Use when the question is degradation since the last refactoring milestone, not feature delivery or incident recurrence.

## Do Not Use When

- Do not use when the scope is one already-bounded refactor PR; use the ACR-179 base refactoring workflow at `~/ai/workflows/refactoring.md` directly.
- Do not use for incident-driven or regression-risk refactoring; ACR-154 owns that sibling strategy.
- Do not use for seed-and-fan-out or surface-expansion refactoring; ACR-180 owns that sibling strategy.
- Do not use for work that ships behavior, feature, or user-facing change; route to `~/ai/workflows/feature-development.md`.

## Required Inputs

- Common to scope and execute: `mode`, `ticket_system`, `repo_root`, `worktree_path`, `planning_dir`, `scratch_dir`, exact short `trunk_branch`, canonical JSON `protected_branches`, and `manager_flavor`.
- Scope only: exactly one of `target` or `target_surface`, `integration_branch_ref`, `history_base_ref`, `milestone_search_policy`, `degradation_signal_sources`, `package_bounds`, and optional `package_size_override`.
- Execute only: immutable `package_source_request`, caller-owned `package_ticket_source_map` bound to the exact request `plan_hash`, `current_identity_path`, and matching Jira (`jira_url`, `jira_project`, `jira_account_email`) or Linear (`linear_team_key`, optional `linear_project_id`) child configuration.
- The mode-specific sets are disjoint. Scope rejects execute inputs, execute rejects scope-selection inputs, and execute never reruns or replaces scoping.

## Gate Stack

The orchestrator reuses the implementation-pipeline gate stack by reference:

- `~/ai/workflows/implementation-pipeline.md` § Phase 4.
- `~/ai/workflows/implementation-pipeline.md` § Phase 6 code-quality fanout.
- `~/ai/workflows/implementation-pipeline.md` § Phase 7.
- `~/ai/workflows/implementation-pipeline.md` § Phase 8.
- `~/ai/workflows/code-quality.md`.
- `~/ai/workflows/pr-review.md`.

## Phases

1. Scope target and identity capture: confirm refactor-only intent; pin target identity plus exact history base/frontier, explicit trunk, integration ref/full-SHA, and canonical protected-set identity.
2. Scope milestone/degradation/package selection: follow the convention, select exact package IDs, assign unique branches outside the protected set plus unique root projections, and validate each with the unchanged trunk/integration/protected set as a future one-child/one-ticket-PR refactoring WU.
3. Scope handoff: write/hash milestone evidence, degradation inventory, package plan, source hashes, and immutable package-source request; return `PACKAGE_SOURCE_REQUEST_READY` without ticket or child operations.
4. Execute validation: reject unknown/omitted request or descriptor fields; validate every documented descriptor type, exact inherited gates, canonical protected short refs, package exclusion from that set, canonical unique roots/result paths, direct-child relationships, and package-local acyclic dependencies; then recompute request `plan_hash`, compare a fresh target/history/trunk/integration/protected current identity bundle, require map hash/backend/exact package-set equality, and write executable validation before any brief or dispatch.
5. Execute per-package WUs: write context-only briefs and dispatch each package as a separate refactoring WU with its exact existing issue, normalized branch, unique roots, explicit trunk/integration branches, and the unchanged protected set. Every refactoring invocation owns one implementation child and one ticket PR.
6. Execute outcome: join runtime route identities and complete singular-child `VERIFIED_MERGED` results to the same plan hash; never mutate tickets from this root.

## Stop Conditions

- Scope succeeds only at `PACKAGE_SOURCE_REQUEST_READY`; this is a stable assignment handoff, not an invitation to guess issue mappings before package selection.
- Execute succeeds when all exact request packages ship independently and finish at LOW through their inherited gates.
- Scope stops when the target, identity, milestone, evidence, package boundary, explicit trunk/integration/protected set, package branch exclusion, canonical route roots/result path, or dependency graph is invalid.
- Stop with NEEDS_INPUT when the next decision changes user-owned value, scope, sibling-strategy routing, or behavior-change intent.
- Stop and shrink when a proposed package returns MEDIUM, HIGH, or another non-passing outcome from an inherited gate.
- Execute stops before every dispatch when request/current target/history/trunk/integration/protected identity, plan hash, source map, exact package set, issue uniqueness/backend, context brief, or one-child projection is stale, missing, duplicate-keyed, incomplete/extra, malformed, or ambiguous.

## Anti-scope

- Do not modify ACR-179's Refactoring workflow itself; it is the substrate, not the strategy.
- Do not change implementation-pipeline orchestrator behavior.
- Do not design the incident-driven strategy owned by ACR-154 or the seed-and-fan-out strategy owned by ACR-180.
- Do not include feature or behavior changes in refactor packages; this is strict refactor-only scope.
- Phase 7 anti-scope applies with no deviation.
- The workflow root performs no ticket automation in either mode and generated briefs never become implementation ticket sources.
- There is no compatibility fallback between modes, no automatic scope-to-execute continuation, and no execute-time package reselection.

## Cross-references

- `~/ai/workflows/refactoring.md` - ACR-179 substrate.
- `~/ai/agents/refactoring-orchestrator.md`
- `~/ai/conventions/refactoring-workflow.md`
- `~/ai/conventions/refactoring-commit-history-scoping.md` - ACR-182 strategy convention (rule source for milestone identification, degradation taxonomy, package descriptor shape, sizing rule, sibling boundaries, worked example).
- `~/ai/conventions/active-shims.md`
- `~/ai/workflows/implementation-pipeline.md`
- `~/ai/workflows/code-quality.md`
- `~/ai/workflows/pr-review.md`
- `ACR-154`
- `ACR-180`
