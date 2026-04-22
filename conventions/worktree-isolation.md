# Worktree Isolation

**Rule**: any two agents running at the same time that both write files MUST operate on different git worktrees. No exceptions.

## Why

Concurrent writes to the same working tree corrupt state:

- Overlapping edits cause merge conflicts and lost changes.
- Partial writes from one agent appear as uncommitted changes to another.
- Git operations such as `git add`, `git commit`, and `git checkout` interleave unpredictably.

Worktree isolation gives each agent a clean, disjoint working directory backed by a dedicated branch. Merging the branches is the join step.

## Setup

```bash
# From the main repository checkout:
git worktree add worktrees/<branch-name> -b <branch-name> <base-branch>

# Point the agent at it:
agents -m <model> -p worktrees/<branch-name> -f <prompt>.md
```

Convention for worktree location: `worktrees/<branch-name>/` inside the repo root.

## Cleanup

After the agent branch has been merged:

```bash
git worktree remove worktrees/<branch-name>
# If the branch is still wanted elsewhere, keep it; otherwise:
git branch -d <branch-name>
```

## When worktrees are NOT required

- A single agent writing alone.
- Read-only agents.
- Agents writing only outside the repo.

## When they ARE required

- Any two agents writing concurrently, even if they touch different files.
- Parallel risk gates that may touch `plans/`, `.tmp/`, or other repo paths.
- PR decomposition or branch-construction experiments run in parallel.
