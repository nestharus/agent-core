---
workflow:
  id: refactoring-commit-history
workflow_dispatch_contract:
  orchestrator: "refactoring-commit-history-orchestrator"
  inputs:
    - "target surface (accepts either target or target_surface), repo_root, worktree_path, planning_dir, scratch_dir, integration_branch_ref, history_base_ref"
    - "milestone_search_policy, degradation_signal_sources, package_bounds, manager_flavor, and optional package_size_override"
  expectations:
    - "finds the last refactor milestone for the target surface"
    - "analyzes commits since that milestone for structural degradation"
    - "packages corrective refactors into independently reviewable PR plans that inherit the base refactoring and implementation-pipeline gates"
  outputs:
    - "last-refactor milestone evidence"
    - "history degradation inventory"
    - "bounded package plan with gate obligations"
    - "handoff inputs for ACR-179 per-package execution"
  non_goals:
    - "does not modify the base ACR-179 refactoring substrate"
    - "does not design incident-driven or seed-and-fan-out sibling strategies"
    - "does not introduce behavior or feature changes"
    - "does not add scheduler or ticket-automation hooks"
---
# Refactoring commit-history workflow

## Workflow Dispatch Surface

The operator is `refactoring-commit-history-orchestrator`. It accepts a target surface plus repository, worktree, planning, scratch, integration-branch, history-base, milestone-search, degradation-signal, package-bound, and manager-flavor inputs. It is expected to find the last refactor milestone, analyze commits since that milestone for structural degradation, and produce independently reviewable package plans that inherit the base refactoring and implementation-pipeline gates. Its outputs are last-refactor milestone evidence, a history degradation inventory, a bounded package plan with gate obligations, and handoff inputs for ACR-179 per-package execution. Its non-goals are modifying the base ACR-179 substrate, designing ACR-154 or ACR-180 sibling strategies, introducing behavior or feature changes, or adding scheduler or ticket-automation hooks.

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

- `target`: file, module, package, or other bounded code surface to inspect.
- `target_surface`: alias accepted when the caller uses the workflow-level input name.
- `repo_root`.
- `worktree_path`.
- `planning_dir`.
- `scratch_dir`.
- `integration_branch_ref`.
- `history_base_ref`.
- `milestone_search_policy`: commit-message, ticket, PR, merge, dispatch-evidence, and fallback confidence rules for selecting and recording the last refactor milestone.
- `degradation_signal_sources`: cohesion, coupling, function-classification, push-pull, and code-quality references.
- `package_bounds`.
- `manager_flavor`.
- Optional `package_size_override`, defaulting to `~/ai/conventions/refactoring-commit-history-scoping.md` § Package sizing rule.

## Gate Stack

The orchestrator reuses the implementation-pipeline gate stack by reference:

- `~/ai/workflows/implementation-pipeline.md` § Phase 4.
- `~/ai/workflows/implementation-pipeline.md` § Phase 6 code-quality fanout.
- `~/ai/workflows/implementation-pipeline.md` § Phase 7.
- `~/ai/workflows/implementation-pipeline.md` § Phase 8.
- `~/ai/workflows/code-quality.md`.
- `~/ai/workflows/coderabbit-loop.md`.
- `~/ai/workflows/pr-review.md`.

## Phases

1. Target identification: confirm the target surface is internal refactor-only scope and record the caller-provided target boundary.
2. Last-refactor-milestone discovery: follow `~/ai/conventions/refactoring-commit-history-scoping.md` § Milestone identification and record the selected milestone evidence.
3. Degradation analysis: run or consume the implementation-pipeline auditor stack by reference, including `~/ai/workflows/implementation-pipeline.md` § Phase 4, `~/ai/workflows/implementation-pipeline.md` § Phase 6 code-quality fanout, `~/ai/workflows/code-quality.md`, `~/ai/workflows/coderabbit-loop.md`, and `~/ai/workflows/pr-review.md`; do not copy or redefine their gate procedures.
4. Package decomposition: apply `~/ai/conventions/refactoring-commit-history-scoping.md` § Package descriptor and § Package sizing rule.
5. Per-package execution: dispatch each accepted package through `~/ai/workflows/refactoring.md` and `~/ai/agents/refactoring-orchestrator.md`; `~/ai/workflows/implementation-pipeline.md` § Phase 7 and `~/ai/workflows/implementation-pipeline.md` § Phase 8 remain package gates by file-path reference.
6. Stop-condition evaluation: stop when the package set ships at LOW, when scoping cannot produce bounded packages, or when a NEEDS_INPUT condition changes value, scope, or strategy ownership.

## Stop Conditions

- Succeed when all packages ship independently and finish at LOW through their inherited gates.
- Stop when scoping is aborted with a note explaining why the target, milestone, evidence, or package boundary is invalid.
- Stop with NEEDS_INPUT when the next decision changes user-owned value, scope, sibling-strategy routing, or behavior-change intent.
- Stop and shrink when a proposed package returns MEDIUM, HIGH, or another non-passing outcome from an inherited gate.

## Anti-scope

- Do not modify ACR-179's Refactoring workflow itself; it is the substrate, not the strategy.
- Do not change implementation-pipeline orchestrator behavior.
- Do not design the incident-driven strategy owned by ACR-154 or the seed-and-fan-out strategy owned by ACR-180.
- Do not include feature or behavior changes in refactor packages; this is strict refactor-only scope.
- Phase 7 anti-scope applies with no deviation.

## Cross-references

- `~/ai/workflows/refactoring.md` - ACR-179 substrate.
- `~/ai/agents/refactoring-orchestrator.md`
- `~/ai/conventions/refactoring-workflow.md`
- `~/ai/conventions/refactoring-commit-history-scoping.md` - ACR-182 strategy convention (rule source for milestone identification, degradation taxonomy, package descriptor shape, sizing rule, sibling boundaries, worked example).
- `~/ai/conventions/active-shims.md`
- `~/ai/workflows/implementation-pipeline.md`
- `~/ai/workflows/code-quality.md`
- `~/ai/workflows/coderabbit-loop.md`
- `~/ai/workflows/pr-review.md`
- `ACR-154`
- `ACR-180`
