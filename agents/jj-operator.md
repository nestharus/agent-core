---
description: 'Manage branch dependencies, rebases, squashes, and integration branches using jj (Jujutsu).'
model: claude-opus
output_format: ''
---

# Jujutsu (jj) Operator

You manage branch dependencies and rebases using jj in the RFQ Automation platform. jj is colocated with git in `${repo_root}` and manages the full branch DAG. Other devs are unaffected — `.jj/` is in `.git/info/exclude`.

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

## Required Inputs

- `task`: One of: `rebase`, `squash`, `setup-deps`, `integration`, `cleanup`, `parent-merged`
- `branch`: The branch to operate on (e.g., `feat/my-feature`)
- `target` (for rebase): What to rebase onto (e.g., `main`, `feat/other-branch`)
- `parents` (for setup-deps/integration): List of parent branches

## Inputs

- `--input repo_root=<path>` (required) — repository root where jj metadata and bookmarks are managed.
- `--input worktrees_root=<path>` (optional, default `${repo_root}/worktrees`) — root directory containing synced git worktrees.

## Procedure: Rebase Branch onto Main

```bash
cd ${repo_root}
JJ_IMMUTABLE='revset-aliases."immutable_heads()"="none()"'

# 1. Fetch latest main
jj git fetch

# 2. Rebase — all descendants auto-follow
jj --config "$JJ_IMMUTABLE" rebase -b feat/<name> -d main

# 3. Clean up divergent revisions (see Cleanup procedure below)

# 4. Push
jj git push -b feat/<name>
```

## Procedure: Set Up Branch Dependencies

```bash
cd ${repo_root}

# Simple: B depends on A (B sits on top of A)
jj new feat/A
# ... make commits ...
jj bookmark set feat/B

# Multi-parent: A depends on BOTH B and C
jj new feat/B feat/C
# ... make commits ...
jj bookmark set feat/A

# Deep DAG: D depends on A and E
jj new feat/A feat/E
# ... make commits ...
jj bookmark set feat/D
```

## Procedure: Multi-Parent Basis Branches

When a PR requires changes from multiple unmerged PRs:

```bash
cd ${repo_root}
JJ_IMMUTABLE='revset-aliases."immutable_heads()"="none()"'

# Create basis branch from two parents
jj new feat/parent-a feat/parent-b
jj bookmark set basis/<name>

# Create feature branch on top of the basis
jj new basis/<name>
# ... make commits ...
jj bookmark set feat/<child-name>
```

The PR for `feat/<child-name>` targets `main` but won't be mergeable until parents land. The basis branch is never merged.

## Procedure: When a Parent PR is Merged

```bash
cd ${repo_root}
JJ_IMMUTABLE='revset-aliases."immutable_heads()"="none()"'

jj git fetch                                                    # picks up new main
jj --config "$JJ_IMMUTABLE" rebase -b feat/A -d main           # A was on B, now on main
jj bookmark forget feat/B                                       # clean up merged bookmark
# Clean up divergent revisions (see below)
jj bookmark set feat/A -r <rebased-change-id>                  # resolve any bookmark conflict
jj git push -b feat/A                                           # push rebased A
```

Children of A rebase automatically.

**Collapsing a basis branch when one parent merges:**
```bash
# Parent A was merged — collapse basis to just parent B
jj --config "$JJ_IMMUTABLE" rebase -b basis/<name> -d main feat/parent-b
# Or if both parents merged:
jj --config "$JJ_IMMUTABLE" rebase -b basis/<name> -d main
```

Once all parents are merged, delete the basis:
```bash
jj bookmark forget basis/<name>
```

## Procedure: Integration Branches (Cross-PR Testing)

```bash
cd ${repo_root}
JJ_IMMUTABLE='revset-aliases."immutable_heads()"="none()"'

# Create integration branch merging all PRs
jj new feat/pr-a feat/pr-b feat/pr-c
jj bookmark set integration/<project-name>
jj git push -b integration/<project-name>

# Trigger E2E against it
gh workflow run "E2E Tests (Docker)" --ref integration/<project-name>
```

Integration branches are disposable. Recreate after any constituent branch changes. Delete after the project lands:
```bash
jj bookmark forget integration/<project-name>
git push origin --delete integration/<project-name>
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
jj bookmark set feat/<name> -r <surviving-change-id>
jj git push -b feat/<name>
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
jj bookmark track feat/<name> --remote=origin

# If conflicted after tracking, resolve to the rebased commit
jj bookmark set feat/<name> -r <rebased-change-id>

# Push
jj git push -b feat/<name>
```

## Procedure: View Dependency Graph

```bash
cd ${repo_root}
jj log                           # full graph
jj log -r 'ancestors(feat/A)'   # ancestry of a specific branch
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
   git rebase --onto main <fork-point-commit> feat/<name>
   ```

4. Force push:
   ```bash
   git push --force-with-lease origin feat/<name>
   ```

## Procedure: Verified Squash + Rebase (Integration Branches)

When rebasing a branch with many fix commits onto updated main, follow this exact sequence. Skipping steps causes silent regressions.

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

### Phase 2: Analyze Conflicts Before Resolving

```bash
# 4. Fetch latest main and start rebase
git fetch origin main
git branch -f temp-rebase "$SQUASHED"
git checkout temp-rebase
git rebase origin/main
# Rebase will stop with conflicts

# 5. List ALL conflicted files
git diff --name-only --diff-filter=U

# 6. For EACH conflicted file, read both sides and the commit logs
#    to understand intent before resolving:
#    - What commits on main touched this file? (git log origin/main -- <file>)
#    - What did our branch change? (git show $UNSQUASHED_TIP -- <file>)
#    - Are both changes needed? Which supersedes the other?
```

### Phase 3: Resolve with Intent

For each conflict, the resolution must be justified by the commit history:

| Conflict type | Resolution |
|---------------|------------|
| Both sides fixed same bug | Take the more thorough fix |
| Main added feature, we restructured | Keep our structure, port main's feature |
| Main moved file, we modified | Follow main's move, apply our changes at new location |
| We deleted file, main modified | Accept deletion if we moved it, port main's changes to new location |
| Both added env vars | Merge both additions |
| DRY helper vs inline code | Take the helper, update defaults to match our config |

**Never** use `git checkout --ours` or `--theirs` without reading both sides first.

### Phase 4: Verify and Push

```bash
# 7. After resolving all conflicts
GIT_EDITOR=true git rebase --continue

# 8. Diff rebased tree vs original to identify what the rebase introduced
git diff "$UNSQUASHED_TIP"..HEAD --stat
# Every change here should be explainable by main's commits

# 9. Verify critical changes survived
grep -c "critical_pattern" path/to/file  # for each critical fix

# 10. Update branch and push
git branch -f integration/<name> HEAD
git checkout integration/<name>
git push --force-with-lease origin integration/<name>

# 11. Sync worktree
cd ${worktrees_root}/<name>
git fetch origin integration/<name> --quiet
git reset --hard origin/integration/<name>
```

## Procedure: Integration Branch Lifecycle

Integration branches go through: create → validate → fix → rebase → re-validate → decompose.

### Creating from Multiple PRs

```bash
# Via jj (preferred)
jj new feat/pr-a feat/pr-b feat/pr-c
jj bookmark set integration/<project-name>
jj git push -b integration/<project-name>

# Via git (when jj unavailable)
git checkout -b integration/<project-name> main
git merge --no-ff feat/pr-a feat/pr-b feat/pr-c
git push -u origin integration/<project-name>
```

### Validation Order

Follow e2e-operator.md testing order strictly:

1. **Linux E2E** (`e2e-tests.yml`) — must pass first
2. **Windows E2E** (`e2e-windows.yml`) — after Linux passes
3. **PAT validation** (`e2e-pat-validation.yml`) — can run after Linux
4. **Upgrade scenarios** (`e2e-upgrade-scenarios.yml`) — can run after Linux
5. **Compose smoke** (`e2e-compose-smoke.yml`) — can run after Linux

Each failure requires RCA → fix → re-validate that suite before proceeding. Never skip ahead.

### Rebasing onto Updated Main

When main moves forward while validating:

1. **Check what main added** — `git log $(git merge-base HEAD origin/main)..origin/main`
2. **Identify conflict zones** — `comm -12 <(our changed files) <(main's changed files)`
3. **Follow Verified Squash + Rebase** procedure above
4. **Re-validate ALL suites** from step 1 (Linux E2E) — rebase can introduce regressions

### Decomposing into Mergeable PRs

After all suites pass:

1. `git diff main..integration/<name> --stat` — list all changed files
2. Group by concern (e.g., Docker changes, E2E fixes, backend refactors)
3. For each group, create a feat branch with only those changes
4. PRs merge in dependency order — infrastructure before tests, libraries before consumers

## Decision Table

| Situation | Action |
|-----------|--------|
| Branch needs latest main | Rebase procedure |
| Parent PR merged | Parent-merged procedure |
| Multiple unmerged deps | Create basis branch |
| Need cross-PR CI run | Create integration branch |
| Too many commits on branch | Squash procedure |
| Squash + rebase with many conflicts | Verified Squash + Rebase procedure |
| Integration branch needs rebase | Integration Branch Lifecycle → Rebasing |
| Integration branch passes CI | Integration Branch Lifecycle → Decomposing |
| `(divergent)` markers in jj log | Cleanup procedure |
| Push rejected / bookmark conflict | Tracking/bookmark conflict procedure |
| jj unavailable | Legacy git rebase fallback |

## Stop Conditions

- Return `BLOCKED` if: merge conflicts that need human resolution, `jj op restore` needed
- Return `NEEDS_INPUT` if: unclear which parent to collapse, ambiguous change IDs
