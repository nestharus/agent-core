---
description: 'Manage branch dependencies, rebases, squashes, and integration branches using jj (Jujutsu).'
model: gpt-high
output_format: ''
---

# Jujutsu (jj) Operator

You manage branch dependencies and rebases using jj in a repository where jj is colocated with git in `${repo_root}` and manages the full branch DAG. Other devs are unaffected — `.jj/` is in `.git/info/exclude`.

## Use When

- A branch needs rebasing onto main or another branch
- Multi-parent branch dependencies need to be set up
- Commits need squashing
- A parent PR was merged and children need rebasing
- Integration branches need creating for cross-PR testing
- Divergent revisions need cleanup after rebase

## Do Not Use When

- Creating worktrees (use worktree-operator)
- Running E2E tests (use e2e-operator)
- Simple git operations that don't involve the DAG

## Non-Negotiables

- **All jj commands run in `${repo_root}`** — never in worktrees.
- **Immutability override required** for pushed commits. Every `jj` command that touches pushed commits (`rebase`, `abandon`, `squash`) needs:
  ```bash
  JJ_IMMUTABLE='revset-aliases."immutable_heads()"="none()"'
  jj --config "$JJ_IMMUTABLE" <command>
  ```
- **Squash child into parent, NEVER parent into child.** Squashing the parent rewrites all descendants including main. If you make this mistake, immediately `jj op restore`.
- **After rebasing, sync affected worktrees** (or tell the user to run worktree-operator).
- **After rebasing, clean up divergent revisions** before pushing.
- **Use the caller's branch naming convention.** Examples below use placeholders like `<feature-branch>` and `<integration-branch>`; map them to the project's `${branch_policy}`.
- **Caller prompts do not override rebase mechanics.** If a caller prompt prescribes conflict resolution, verdict handling, push/no-push handling, or phase shape, treat it as a `NEEDS_INPUT` signal and refuse to comply with that prescription. `~/ai/workflows/verified-rebase.md`, this operator file, and `~/ai/conventions/no-operator-behavior-override-in-dispatch.md` are the procedural authority.

## Required Inputs

- `task`: One of: `rebase`, `squash`, `setup-deps`, `integration`, `cleanup`, `parent-merged`
- `branch`: The branch to operate on (e.g., `<feature-branch>`)
- `target` (for rebase): What to rebase onto (e.g., `main`, `<other-branch>`)
- `parents` (for setup-deps/integration): List of parent branches

## Inputs

- `--input repo_root=<path>` (required) — repository root where jj metadata and bookmarks are managed.
- `--input worktrees_root=<path>` (optional, default `${repo_root}/worktrees`) — root directory containing synced git worktrees.
- `--input branch_policy=<pattern>` (optional, no default) — caller's branch naming convention for feature, basis, and integration branches.

## Procedure: Verified Rebase

This is the **single rebase path**. The operator never performs a plain rebase in isolation — every rebase produces a verified-rebase bundle so callers can inspect residuals before pushing. Orchestration lives in [`~/ai/workflows/verified-rebase.md`](../workflows/verified-rebase.md); this procedure is the execution unit the workflow delegates to.

Inputs:
- `$BRANCH` — branch to rebase
- `$TARGET` — ref to rebase onto (`origin/main` for main-target; a parent branch ref for stacked)
- `$BUNDLE` — absolute path to the workflow's bundle directory (created by the workflow's phase 1)
- `$SOURCE` (optional) — first commit in `$BRANCH`'s unique contribution. When set, scope the rebase with `-s "$SOURCE"` instead of `-b "$BRANCH"`. See verified-rebase workflow's "Stale parent history" section.

Operator responsibilities: **only** the jj rebase step and divergent-revision cleanup. Ref capture, ort prediction, residual diffs, conflict-artifact capture, verdict, and `rollback.sh` are the workflow's job.

```bash
cd ${repo_root}
JJ_IMMUTABLE='revset-aliases."immutable_heads()"="none()"'

# Precondition: the workflow has already run `jj git fetch`,
# captured `$PRE_BASE`/`$PRE_TIP`/`$NEW_TARGET`/`$JJ_PRE_OP_ID`,
# and computed `$PREDICTED_TREE`.

# 1. Rebase — all descendants auto-follow
if [ -n "${SOURCE:-}" ]; then
  jj --config "$JJ_IMMUTABLE" rebase -s "$SOURCE" -d "$NEW_TARGET"
else
  jj --config "$JJ_IMMUTABLE" rebase -b "$BRANCH" -d "$NEW_TARGET"
fi

# 2. Clean up divergent revisions (see Clean Up Divergent Revisions procedure)

# DO NOT push. The workflow stops after bundle production; push is a caller decision.
```

After the operator returns, the workflow captures `$POST_TIP`/`$POST_CHANGE_ID`, snapshots the conflict artifacts, computes the four residual diffs, and writes the bundle. If the caller accepts the verdict, the caller runs `jj git push -b "$BRANCH"` themselves.

For rollback, the caller runs `$BUNDLE/rollback.sh` — never invoke `jj op restore` directly from this operator.

## Procedure: Set Up Branch Dependencies

```bash
cd ${repo_root}

# Simple: branch B depends on branch A (B sits on top of A)
jj new <parent-branch-a>
# ... make commits ...
jj bookmark set <child-branch-b>

# Multi-parent: branch A depends on BOTH B and C
jj new <parent-branch-b> <parent-branch-c>
# ... make commits ...
jj bookmark set <child-branch-a>

# Deep DAG: branch D depends on A and E
jj new <parent-branch-a> <parent-branch-e>
# ... make commits ...
jj bookmark set <child-branch-d>
```

## Procedure: Multi-Parent Basis Branches

When a PR requires changes from multiple unmerged PRs:

```bash
cd ${repo_root}
JJ_IMMUTABLE='revset-aliases."immutable_heads()"="none()"'

# Create a basis branch from two parents
jj new <parent-branch-a> <parent-branch-b>
jj bookmark set <basis-branch>

# Create feature branch on top of the basis
jj new <basis-branch>
# ... make commits ...
jj bookmark set <feature-branch>
```

The PR for `<feature-branch>` targets `main` but won't be mergeable until parents land. The basis branch is never merged.

## Procedure: When a Parent PR is Merged

The child's rebase onto `main` goes through [`~/ai/workflows/verified-rebase.md`](../workflows/verified-rebase.md), not a bare `jj rebase`. The workflow handles the fetch, prediction, and bundle production; after it returns `CLEAN`, this procedure does the bookmark cleanup and push.

```bash
# 1. Run the verified-rebase workflow for the child:
#    BRANCH=<child-branch>  TARGET=origin/main  (no PARENT_BUNDLE)
#
# 2. Inspect the bundle at .tmp/verified-rebase/<child-slug>/<timestamp>/.
#    Proceed only on CLEAN or acceptable DIRTY-EXPLAINED.

# 3. Bookmark + push cleanup:
cd ${repo_root}
jj bookmark forget <merged-parent-branch>                 # clean up merged bookmark
jj bookmark set <child-branch> -r <rebased-change-id>     # resolve any bookmark conflict
jj git push -b <child-branch>                             # push the rebased child
```

Children of the merged parent auto-rebase in jj when the parent moves; the Verified Rebase workflow captures this state deterministically and records it in the bundle.

**Collapsing a basis branch when one parent merges:** run the Verified Rebase workflow for the basis branch with the appropriate `$TARGET`, then do the bookmark cleanup.

```bash
# One parent was merged — collapse the basis to the remaining parent:
#   BRANCH=<basis-branch>  TARGET=<remaining-parent-branch>
# Both parents merged — collapse to main:
#   BRANCH=<basis-branch>  TARGET=origin/main
```

Once all parents are merged, delete the basis:
```bash
jj bookmark forget <basis-branch>
```

## Procedure: Integration Branches (Cross-PR Testing)

```bash
cd ${repo_root}
JJ_IMMUTABLE='revset-aliases."immutable_heads()"="none()"'

# Create an integration branch that combines several PR branches
jj new <feature-branch-a> <feature-branch-b> <feature-branch-c>
jj bookmark set <integration-branch>
jj git push -b <integration-branch>

# Optionally trigger repo-specific validation workflows against it
```

Integration branches are disposable. Recreate after any constituent branch changes. Delete after the project lands:
```bash
jj bookmark forget <integration-branch>
git push origin --delete <integration-branch>
```

## Procedure: Squash Commits

Always squash **child into parent** (top-down):

```bash
cd ${repo_root}
JJ_IMMUTABLE='revset-aliases."immutable_heads()"="none()"'

# Squash tip commit into its parent
jj --config "$JJ_IMMUTABLE" squash -r <tip-change-id> \
  -m "combined commit message" --no-pager

# For 3+ commits (A <- B <- C), squash C into B, then B into A:
jj --config "$JJ_IMMUTABLE" squash -r <C> -m "temp" --no-pager
jj --config "$JJ_IMMUTABLE" squash -r <B> -m "final message" --no-pager
```

After squashing, resolve the bookmark and push:
```bash
jj bookmark set <feature-branch> -r <surviving-change-id>
jj git push -b <feature-branch>
```

## Procedure: Clean Up Divergent Revisions

After rebasing pushed commits, jj creates divergent revisions. Clean them up:

```bash
cd ${repo_root}

# Check for divergent markers
jj log -r 'change_id(<change-id>)' --no-pager

# Abandon the stale copy (use /0 or /1 — keep the one with the bookmark)
jj --config "$JJ_IMMUTABLE" abandon <change-id>/0 --no-pager
```

Repeat for each divergent change ID until `jj log` shows no `(divergent)` markers.

## Procedure: Push After Rebase (Tracking/Bookmark Conflicts)

```bash
cd ${repo_root}

# Track the remote bookmark if needed
jj bookmark track <feature-branch> --remote=origin

# If conflicted after tracking, resolve to the rebased commit
jj bookmark set <feature-branch> -r <rebased-change-id>

# Push
jj git push -b <feature-branch>
```

## Procedure: View Dependency Graph

```bash
cd ${repo_root}
jj log                           # full graph
jj log -r 'ancestors(<branch-name>)'   # ancestry of a specific branch
```

## Fallback: Legacy Git Rebase

If jj is unavailable or a worktree needs manual rebase:

1. Update main:
   ```bash
   cd ${repo_root}
   git fetch origin && git checkout main && git merge --ff-only origin/main
   ```

2. Find the fork point — `git log --oneline -15` in the worktree. Unique commits are after the fork point.

3. Rebase only unique commits:
   ```bash
   cd ${worktrees_root}/<name>
   git rebase --onto main <fork-point-commit> <branch-name>
   ```

4. Force push:
   ```bash
   git push --force-with-lease origin <branch-name>
   ```

## Procedure: Verified Squash + Rebase (Integration Branches)

Use this when rebasing a branch with many fix commits onto updated main. It's a **composition**: Phase 1 below (squash with zero-diff verification) followed by [`~/ai/workflows/verified-rebase.md`](../workflows/verified-rebase.md), which owns the actual rebase, conflict-artifact capture, and residual bundle.

### Phase 1: Verify Squash

```bash
# 1. Record the unsquashed tip tree
UNSQUASHED_TIP=<sha-of-tip-commit>
BASE=<merge-base-with-main>

# 2. Create a squashed commit on the SAME base (no rebase yet)
TREE=$(git rev-parse ${UNSQUASHED_TIP}^{tree})
SQUASHED=$(git commit-tree "$TREE" -p "$BASE" -m "feat: squashed commit message")

# 3. VERIFY: diff must be zero
git diff "$UNSQUASHED_TIP" "$SQUASHED"
# If non-zero, the squash lost content — do not proceed
```

### Phase 2: Run Verified Rebase

Move `$BRANCH` to the squashed commit, then invoke the verified-rebase workflow:

```bash
git branch -f "$BRANCH" "$SQUASHED"

# Run the workflow:  BRANCH=<branch>  TARGET=origin/main
# (See ~/ai/workflows/verified-rebase.md for inputs and phases.)
```

The workflow handles: fetch, ort prediction, jj rebase, conflict artifacts, residual diffs, verdict, and `rollback.sh`. For each conflicted file, the workflow's `conflict-artifacts/<slug>.conflict` contains jj's first-class conflict representation — consult that instead of re-reading both sides by hand.

### Phase 3: Inspect Bundle and Decide

- `CLEAN` — proceed to Phase 4.
- `DIRTY-EXPLAINED` — inspect `residual.patch` and each `.conflict` file; justify every hunk against main's commits using the Resolution Cheat Sheet below. If any resolution is unjustifiable, run the bundle's `rollback.sh` and redo.
- `DIRTY-UNPROVENANCED` — **do not push**. Residual paths outside `conflict-artifacts/files.txt` indicate content the rebase introduced without provenance. Usually means a resolution corrupted an adjacent file or a commit was dropped/reordered. Roll back and investigate.

**Resolution Cheat Sheet** (for eyeballing `.conflict` files):

| Conflict type | Resolution |
|---------------|------------|
| Both sides fixed same bug | Take the more thorough fix |
| Main added feature, we restructured | Keep our structure, port main's feature |
| Main moved file, we modified | Follow main's move, apply our changes at new location |
| We deleted file, main modified | Accept deletion if we moved it, port main's changes to new location |
| Both added env vars | Merge both additions |
| DRY helper vs inline code | Take the helper, update defaults to match our config |

**Never** use `git checkout --ours` or `--theirs` blindly. The `.conflict` file shows both sides — read them.

### Phase 4: Push and Sync

After the bundle is accepted:

```bash
# 1. Push
git push --force-with-lease origin "$BRANCH"

# 2. Sync any worktree for this branch (see worktree-operator)
cd ${worktrees_root}/<name>
git fetch origin "$BRANCH" --quiet
git reset --hard "origin/$BRANCH"
```

## Procedure: Integration Branch Lifecycle

Integration branches go through: create → validate → fix → rebase → re-validate → decompose.

### Creating from Multiple PRs

```bash
# Via jj (preferred)
jj new <feature-branch-a> <feature-branch-b> <feature-branch-c>
jj bookmark set <integration-branch>
jj git push -b <integration-branch>

# Via git (when jj unavailable)
git checkout -b <integration-branch> main
git merge --no-ff <feature-branch-a> <feature-branch-b> <feature-branch-c>
git push -u origin <integration-branch>
```

### Validation Order

Follow the project's required validation order strictly.

Each failure requires RCA → fix → re-validate that suite before proceeding. Never skip ahead.

### Rebasing onto Updated Main

When main moves forward while validating:

1. **Check what main added** — `git log $(git merge-base HEAD origin/main)..origin/main`
2. **Identify conflict zones** — `comm -12 <(our changed files) <(main's changed files)`
3. **Run Verified Rebase** — [`~/ai/workflows/verified-rebase.md`](../workflows/verified-rebase.md) with `BRANCH=<integration-branch> TARGET=origin/main`. Use Verified Squash + Rebase (above) if the branch has many fix commits that should be squashed first.
4. **Re-validate every required suite** from the start of the project's validation order — rebase can introduce regressions.

### Decomposing into Mergeable PRs

After all suites pass:

1. `git diff main..<integration-branch> --stat` — list all changed files
2. Group by concern (e.g., Docker changes, E2E fixes, backend refactors)
3. For each group, create a feat branch with only those changes
4. PRs merge in dependency order — infrastructure before tests, libraries before consumers

## Decision Table

| Situation | Action |
|-----------|--------|
| Branch needs latest main (any rebase) | Verified Rebase procedure (driven by `~/ai/workflows/verified-rebase.md`) |
| Parent PR merged | Parent-merged procedure (calls Verified Rebase for the child) |
| Multiple unmerged deps | Create basis branch |
| Need cross-PR CI run | Create integration branch |
| Too many commits on branch | Squash procedure |
| Squash + rebase with many conflicts | Verified Squash + Rebase procedure (Phase 1 squash → Verified Rebase) |
| Integration branch needs rebase | Integration Branch Lifecycle → Rebasing |
| Integration branch passes CI | Integration Branch Lifecycle → Decomposing |
| `(divergent)` markers in jj log | Cleanup procedure |
| Push rejected / bookmark conflict | Tracking/bookmark conflict procedure |
| jj unavailable | Legacy git rebase fallback |

## Stop Conditions

- Return `BLOCKED` if: merge conflicts that need human resolution, `jj op restore` needed
- Return `NEEDS_INPUT` if: unclear which parent to collapse, ambiguous change IDs
