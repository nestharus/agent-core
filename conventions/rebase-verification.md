# Rebase Verification Convention

When a branch is rebased onto a new base (typical case: an in-flight WU's branch is rebased onto an updated `main` after some other PR merged), the rebase by itself is a silent operation as far as the test suite is concerned. The branch may compile and look like the same diff but its **runtime behavior** can have shifted because the surrounding code changed. This convention defines the verification gate that every rebase must clear before the branch is considered re-aligned with `main`.

## Trigger

Any of the following events triggers the rebase-verification gate:

- `git rebase main` (or `git rebase origin/main`) on a WU branch.
- `git pull --rebase` on a WU branch.
- A force-push to a WU branch where the new base is not the old base.
- An orchestrator-internal Tier-1 rewind that re-bases the WU branch on a new commit.

The gate runs on the **rebased branch tip** before the orchestrator advances any phase.

## Required checks

All four must clear:

### 1. Test re-run

Re-run the full project test suite on the rebased branch. **Stale results from the pre-rebase suite do not count.** The check is binary: does the suite pass on the post-rebase tree? If anything fails that was passing pre-rebase, the rebase introduced a regression and the WU is not yet re-aligned.

Implementation: `cargo test --workspace` (Rust), `bun run test` + `bun run typecheck` + `bun run lint` (frontend), plus any project-specific suite the project's `AGENTS.md` names.

### 2. Coverage non-regression

Compute the coverage delta between the pre-rebase tip and the post-rebase tip on the same set of behaviors. Coverage must not drop. Coverage going UP on previously-uncovered code is fine; coverage DOWN means the rebase caused either tests to be skipped or product code to silently move outside test reach.

Implementation: project-specific. For Rust projects on agent-runner, this is `cargo llvm-cov` (or equivalent) snapshot before and after; the diff goes into `${planning_dir}/risk/<wu>-rebase-coverage.md`.

### 3. Behavior / contract verification

For every named contract / behavior in the WU's Phase 6a contract document, verify the post-rebase tree still matches the contract. This is not just "tests pass" — tests can pass while contracts have silently shifted (e.g., the test asserted a string equality that now happens to match a different code path).

Implementation: re-run the Phase 6b output index against the post-rebase tree. Each test in the index should report (a) it passes, (b) it exercises the same risk it claimed pre-rebase, (c) the contract section it cites is still present in the tree.

### 4. Drift check

Detect silent drift introduced by the rebase: any change in the merged-from-main code that affects a surface the WU touches. Drift can come from:

- A pre-existing test that was deleted, weakened, or relocated by the merged PR. The WU's invariants now run on a different test boundary.
- A pre-existing helper / abstraction that was deleted or refactored. The WU's product code may compile because the new abstraction has the same name but different semantics.
- A pre-existing comment, doc, or contract in the touched area that was edited or removed. The WU's understanding of "the contract" may now be stale.

Implementation: a `gpt-high` drift-check operator (TODO: write `~/ai/agents/rebase-drift-checker.md`) reads the merged-into-base diff (`git log --first-parent main..HEAD-pre-rebase` × the touched-surface enumeration from Phase 2.5 problem map) and reports any overlap between the merged changes and the WU's touched surface. Overlap is the signal; the operator surfaces what overlapped + verdict (`drift detected | no drift`).

## Outcomes

- **All four clear:** the rebase is verified. The orchestrator advances.
- **Any check fails:** the orchestrator HALTs the WU. Disposition is one of:
  - `repair on branch` — the WU agent reapplies the contract to the post-rebase tree (typically: re-run Phase 6b and Phase 6c against the new base to re-derive tests / fix broken product code).
  - `rewind` — drop the rebase, return to the pre-rebase commit, abandon the rebase attempt. Useful when the merged-from-main change made the WU's premise wrong.
  - `re-enter Phase 2.5` — the merged change invalidates the WU's problem map. Restart from problem-map.

The disposition is recorded in `${planning_dir}/audit-history.md` and, when it changes the WU's outcome, in `${repo_root}/DECISIONS.md`.

## Anti-pattern

Treating the rebase as "git plumbing" and not running any of the four checks. A rebase is a code change as much as any line edit; it shifts the surrounding context without showing in the diff. The test suite passing pre-rebase says nothing about its passing post-rebase. The cost of the verification is bounded; the cost of skipping it is hidden bugs that surface days later.

## TODO (open work)

- Write the `rebase-drift-checker` operator that automates check #4. Until that exists, the orchestrator surfaces a `NEEDS_INPUT` to the user citing the touched-surface enumeration and asks the user to verify drift manually. This is friction; the operator port closes that.
- Define the per-project coverage tooling adapter so check #2 is uniform across Rust / Python / TypeScript projects.
- Decide whether contract / behavior verification (check #3) should produce a verdict artifact (e.g., `${planning_dir}/risk/<wu>-rebase-contract-verify.md`) for downstream auditing.
