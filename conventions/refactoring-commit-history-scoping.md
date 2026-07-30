# Refactoring strategy: commit-history-driven scoping

## Declared roles

- `parser`
- `validator`
- `classifier`

This convention owns degradation classification for commit-history-driven refactoring scope selection.

## Purpose

This convention defines milestone identification, degradation taxonomy, evidence-from-git rules, package-sizing rules, and sibling-strategy boundaries for ACR-182 commit-history-driven refactoring over the ACR-179 substrate.

## Milestone identification

The parser role identifies the most recent credible refactoring milestone for the target by searching git history for explicit `refactor:` commit prefixes, `ACR-*` ticket references, merge commits from prior refactoring WUs, ACR-179 dispatch evidence, integration-buffer commits, and PR titles or bodies that record refactoring gate passage. Prefer explicit refactor markers, then ticket or PR evidence, then merge or buffer evidence, then fallback confidence scoring from commit messages and touched-file sets. Record the selected commit or range, evidence class, confidence, and any weaker candidate milestones that were rejected.

## Degradation taxonomy

1. Cohesion erosion. Detect with the existing cohesion-auditor path in `~/ai/workflows/code-quality.md` § Per-Concern Auditor Routing and the related implementation-pipeline references in `~/ai/workflows/implementation-pipeline.md` § Phase 4 and § Phase 6.
2. Coupling growth. Detect with the existing coupling-auditor path in `~/ai/workflows/code-quality.md` § Per-Concern Auditor Routing and the package review gates referenced by `~/ai/workflows/pr-review.md`.
3. Function-classification mixing. Detect with the existing function-classification-auditor path in `~/ai/workflows/code-quality.md` § Per-Concern Auditor Routing.
4. Push-pull violations. Detect with the existing push-pull-auditor path in `~/ai/workflows/code-quality.md` § Per-Concern Auditor Routing and the A1 coupling references consumed by PR review.
5. Code-quality drift. Detect with the aggregate gate in `~/ai/workflows/code-quality.md` and inherited gate references in `~/ai/workflows/implementation-pipeline.md` § Phase 4, § Phase 6, § Phase 7, and § Phase 8.

## Git evidence rules

Walk commits from the selected milestone to HEAD or the caller-supplied history frontier. Evidence can include changed-file lists, function-classification diffs, churn grouped by target surface, auditor scores or findings at HEAD versus at the milestone, PR review findings, CodeRabbit findings, and records showing when a contract or responsibility was added. The validator role checks that evidence is tied to the selected target, that milestone-to-HEAD comparisons use the same target boundary, that dynamic or emitted contract edges are included when relevant, and that no behavior-change requirement is smuggled into a refactor package.

## Package descriptor

Scope output uses `schema=refactoring-commit-history-package-source-request-v1`. It pins exact target identity SHA-256, history base/frontier refs and full SHAs, explicit exact short repository trunk, protected exact short integration branch/full SHA, and one canonical protected-branch list. That list contains unique validated exact short names ordered as trunk, integration when distinct, then lexical extras; it must include both explicit identities. The request also pins ordered selected package IDs, package plan, source hashes, and `plan_hash=sha256(canonical JSON excluding plan_hash)`, so the entire protected list participates in the hash. The request and each descriptor reject unknown or omitted fields. Each package descriptor contains exactly `package_id`, nonblank string `target_list` and `slice_bounds`, `refactor_intent=no-intended-behavior-change`, canonical absolute milestone and degradation evidence refs, the exact inherited gate set, unique package-local dependencies, nonempty acceptance criteria, a unique exact short `branch_name` outside the complete protected set, unique canonical absolute `worktree_path` / `planning_dir` / `scratch_dir`, and a unique direct `${planning_dir}/refactoring-route-result.json`. It contains no issue assignment and no future brief hash. Inherited obligations are exactly implementation-pipeline Phases 4, 6, 7, and 8.

Every package is a separate refactoring WU with exactly one implementation child and one ticket PR. All package IDs, branches, canonical roots, and result paths are unique, dependencies reference only package IDs in the same request and are acyclic, and canonical paths reject `.` / `..`, symlinks, lexical-versus-`resolve(strict=False)` differences, wrong direct-child names, and cross-root/cross-package aliases. Execute traverses this graph in topological order and dispatches a package only after every prerequisite has a complete hash-bound `VERIFIED_MERGED` outcome; independent ready packages may run in parallel, while a failed or blocked prerequisite blocks its transitive dependents. Validate each branch/root projection with `tools/operational_contracts.py validate-refactoring-dispatch` during scope and again immediately before execute dispatch, transporting the exact request trunk, integration branch, and protected list both times. Execute runs `validate-package-execute`, which validates the complete descriptor schema and every package's exclusion from the protected set before request hash or issue-map acceptance. A package that needs another PR must split into additional package IDs in a new scope request; refactoring never loops internally.

## Canonical per-package WU brief

Execute writes each brief at `${planning_dir}/refactoring-commit-history/packages/${package_id}/wu-brief.md` only after request/current/map validation passes. Frontmatter uses `schema=refactoring-commit-history-wu-brief-v1` and records package id, request `plan_hash`, source target, explicit integration branch, history base/frontier, milestone and degradation evidence paths, `ticket_source_kind=existing-issue`, and `ticket_context_kind=wu_brief_context_path`. Required sections are Problem, Refactor Intent, Target List, Slice Bounds, Milestone Evidence, Degradation Evidence, Preserved Contracts, Dependencies, Acceptance Criteria, Inherited Gate Obligations, and Anti-scope. The brief states no intended behavior change, is context only, and contains no ticket-backend credentials. Scope writes no brief.

## Ticket-automation boundary

The commit-history strategy has strict `scope` and `execute` modes. Scope selects packages without an issue map, writes the immutable package-source request, returns `PACKAGE_SOURCE_REQUEST_READY`, and performs no ticket operation or child dispatch. Execute requires that request plus a caller-owned `refactoring-commit-history-package-ticket-source-v1` map carrying the exact `plan_hash`. The map's package ids must exactly equal the selected request package set, and each row contains exactly one unique existing `jira_issue_key` or `linear_issue_key` matching `ticket_system`; missing, duplicate, extra, opposite-backend, stale-hash, or brief-only identities block the entire dispatch set. There is no compatibility fallback or execute-time rescoping.

Execute requires the caller to repeat the exact `trunk_branch` and `protected_branches` inputs from scope. It builds a fresh `refactoring-commit-history-current-identity-v1` bundle and compares the request's exact target/history/trunk/integration/protected identities before running `tools/operational_contracts.py validate-package-execute`. Any protected-set drift blocks every package before a brief or child dispatch. The strategy accepts backend configuration only in execute mode to pass the validated existing issue identity into the base refactoring/implementation substrate. It never dispatches a ticket operator or creates, updates, estimates, labels, comments on, transitions, or searches tickets itself. Refactoring and implementation receive the issue key as sole ticket source and the generated brief separately as `wu_brief_context_path`; implementation Phase 0 therefore takes the existing-issue read path and cannot cold-create from the brief. Runtime route UUIDs are captured from runner markers after dispatch and compared with the returned singular-child route result; they are not caller-selected prompt inputs.

## Package sizing rule

Package size is driven by review-gate passability: a package is the largest scope that can pass the implementation-pipeline gate stack in exactly one PR, not an arbitrary line-count target. Default to one bounded contract concern per package unless evidence shows multiple findings are inseparable. Split when a proposed package spans independent contract boundaries, combines unrelated degradation kinds, requires behavior change, cannot name clear acceptance, or would need a second child/PR. Shrinking requires a new scope request and `plan_hash`; execute never edits the active package plan. Shrink when `~/ai/workflows/implementation-pipeline.md` § Phase 4, § Phase 6, or § Phase 8 returns MEDIUM or HIGH, or when `~/ai/workflows/implementation-pipeline.md` § Phase 7 returns a non-passing outcome such as BLOCKED or MAX_PASSES_REACHED; the package must then re-scope instead of carrying the verdict forward.

## Sibling boundaries

ACR-154 owns incident-driven and regression-risk refactoring. ACR-180 owns seed-and-fan-out and surface-expansion refactoring. ACR-182 owns commit-history-driven scope selection based on degradation since the last refactoring milestone. These strategies can share the ACR-179 substrate, but they must not share workflow ids, orchestrator names, trigger ownership, or package-selection rules.

## Worked example

Input: `billing/statement_builder.py` was last refactored at commit `abc1234` under an ACR-179 buffer merge. Four later commits added tax formatting, invoice attachment lookup, and retry-state recording to one class, while coupling evidence shows new reads from a generated artifact path. The milestone-to-HEAD history shows cohesion erosion, function-classification mixing, and coupling growth, but the public statement output contract is still stable.

1. Scope selects `statement-tax-formatting`, `statement-attachment-lookup`, and `statement-retry-state`, assigns each a unique branch/root set, freezes exact history/integration identities and source hashes, writes one request, and stops at `PACKAGE_SOURCE_REQUEST_READY`.
2. The caller maps `statement-tax-formatting` to existing issue `ACR-501` and the other exact package IDs to two different existing issues in a source map carrying the request `plan_hash`.
3. Execute revalidates identities/hash/package equality, writes each distinct context brief, and dispatches three separate refactoring WUs. Each WU owns exactly one child and one ticket PR while preserving the existing statement contract through Phases 4, 6, 7, and 8.

Together, the package descriptor list lets the strategy reach holistic LOW by reducing each degradation kind through an independently reviewable ACR-179 package instead of one sweeping PR.

## Cross-references

- `~/ai/workflows/refactoring.md` - ACR-179 substrate.
- `~/ai/agents/refactoring-orchestrator.md`
- `~/ai/conventions/refactoring-workflow.md`
- `~/ai/conventions/active-shims.md`
- `~/ai/workflows/implementation-pipeline.md`
- `~/ai/workflows/code-quality.md`
- `~/ai/workflows/pr-review.md`
- `ACR-154`
- `ACR-180`
