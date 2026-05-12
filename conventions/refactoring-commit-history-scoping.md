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

The output of this strategy is a package descriptor list: a list of packages that can each become one independently reviewable refactor PR. Each descriptor must include target surface, refactor intent (NOT behavior change), milestone evidence reference, degradation evidence reference, inherited gate obligations by file path, dependencies on other packages, acceptance criteria, and ACR-179 handoff inputs. Inherited gate obligations must name `~/ai/workflows/implementation-pipeline.md` § Phase 4, `~/ai/workflows/implementation-pipeline.md` § Phase 6, `~/ai/workflows/implementation-pipeline.md` § Phase 7, and `~/ai/workflows/implementation-pipeline.md` § Phase 8.

## Package sizing rule

Package size is driven by review-gate passability: a package is the largest scope that can pass the implementation-pipeline gate stack in one PR, not an arbitrary line-count target. Default to one bounded contract concern per package unless evidence shows multiple findings are inseparable. Split when a proposed package spans independent contract boundaries, combines unrelated degradation kinds, requires behavior change, or cannot name clear acceptance. Shrink when `~/ai/workflows/implementation-pipeline.md` § Phase 4, § Phase 6, or § Phase 8 returns MEDIUM or HIGH, or when `~/ai/workflows/implementation-pipeline.md` § Phase 7 returns a non-passing outcome such as BLOCKED or MAX_PASSES_REACHED; the package must then shrink and re-scope instead of carrying the verdict forward.

## Sibling boundaries

ACR-154 owns incident-driven and regression-risk refactoring. ACR-180 owns seed-and-fan-out and surface-expansion refactoring. ACR-182 owns commit-history-driven scope selection based on degradation since the last refactoring milestone. These strategies can share the ACR-179 substrate, but they must not share workflow ids, orchestrator names, trigger ownership, or package-selection rules.

## Worked example

Input: `billing/statement_builder.py` was last refactored at commit `abc1234` under an ACR-179 buffer merge. Four later commits added tax formatting, invoice attachment lookup, and retry-state recording to one class, while coupling evidence shows new reads from a generated artifact path. The milestone-to-HEAD history shows cohesion erosion, function-classification mixing, and coupling growth, but the public statement output contract is still stable.

1. Package descriptor: target surface `billing/statement_builder.py::StatementBuilder` tax formatting methods; refactor intent split formatting responsibility behind the existing statement contract with no behavior change; inherited obligations `~/ai/workflows/implementation-pipeline.md` § Phase 4, § Phase 6, § Phase 7, and § Phase 8.
2. Package descriptor: target surface `billing/statement_builder.py` attachment lookup path; refactor intent encapsulate generated-artifact reads before moving lookup internals with no behavior change; inherited obligations `~/ai/workflows/implementation-pipeline.md` § Phase 4, § Phase 6, § Phase 7, and § Phase 8.
3. Package descriptor: target surface retry-state recording helpers; refactor intent separate retry state classification from statement assembly with no behavior change; inherited obligations `~/ai/workflows/implementation-pipeline.md` § Phase 4, § Phase 6, § Phase 7, and § Phase 8.

Together, the package descriptor list lets the strategy reach holistic LOW by reducing each degradation kind through an independently reviewable ACR-179 package instead of one sweeping PR.

## Cross-references

- `~/ai/workflows/refactoring.md` - ACR-179 substrate.
- `~/ai/agents/refactoring-orchestrator.md`
- `~/ai/conventions/refactoring-workflow.md`
- `~/ai/conventions/active-shims.md`
- `~/ai/workflows/implementation-pipeline.md`
- `~/ai/workflows/code-quality.md`
- `~/ai/workflows/coderabbit-loop.md`
- `~/ai/workflows/pr-review.md`
- `ACR-154`
- `ACR-180`
