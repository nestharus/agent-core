---
description: 'Create, list, sync, and manage git worktrees for feature branches.'
model: gpt-high
output_format: ''
---

# Worktree Operator

## Contract

When `contracts/operators/worktree-operator.yaml` is present, dispatchers use that sidecar as the optimized call interface and this embedded block only as its equivalent fallback. The full operator body remains the procedural authority.

```yaml
schema: operator-contract-v1
inputs:
  - name: task
    type: enum
    options: [create, list, sync, remove, bulk-cleanup, open-pr]
    required: true
    default_source: caller
    description: "task"
  - name: repo_root
    type: path
    required: true
    default_source: caller
    description: "repo root"
  - name: worktrees_root
    type: path
    required: false
    default_source: base
    description: "worktrees root"
  - name: name
    type: string
    required: false
    default_source: caller
    description: "Required for create, sync, remove, and open-pr; derives ${worktrees_root}/${name}. Must be one safe direct-child name without traversal, option-like values, or shell metacharacters."
  - name: branch_name
    type: string
    required: false
    default_source: caller | derived
    description: "Required or deterministically derived from name for create, sync, remove, and open-pr; must pass git check-ref-format --branch and the caller's branch policy."
  - name: base_branch
    type: string
    required: false
    default_source: base
    description: "Existing safe short branch name resolved to an exact commit before mutation."
  - name: branch_policy
    type: string
    required: false
    default_source: caller
    description: "branch policy"
defaults:
  - name: worktrees_root
    value: ${repo_root}/worktrees
    source: base
  - name: base_branch
    value: main
    source: base
secrets:
  []
outputs:
  - task: create
    success_shape: "worktree-operation-result-v1 with task=create, canonical repo/worktree paths, branch, base branch/SHA, head SHA, and clean=true."
    wrote_lines: []
  - task: list
    success_shape: "Task-specific stdout or durable artifact paths named by the procedure."
    wrote_lines: []
  - task: sync
    success_shape: "worktree-operation-result-v1 with task=sync, canonical path, branch, pre/post head SHA, and post-sync cleanliness."
    wrote_lines: []
  - task: remove
    success_shape: "worktree-operation-result-v1 with task=remove, pre-removal path/branch/base branch/base SHA/head SHA/cleanliness identity, and removed=true."
    wrote_lines: []
  - task: bulk-cleanup
    success_shape: "worktree-operation-result-v1 with task=bulk-cleanup and one path/branch/base SHA/head SHA/cleanliness/removal-status result per inspected target."
    wrote_lines: []
  - task: open-pr
    success_shape: "worktree-operation-result-v1 with task=open-pr, exact repository and PR URL/number, base/head branches, head SHA, and draft=true."
    wrote_lines: []
errors:
  - class: BLOCKED
    cause: "Required inputs are missing, unreadable, contradictory, or unsafe for the selected task."
    recovery: "Supply corrected inputs or select the appropriate operator wrapper before rerun."
  - class: NEEDS_INPUT
    cause: "A user-owned value, scope, or trade-off question is required."
    recovery: "Answer the emitted question artifact and resume."
side_effects:
  - git-worktree-create
  - git-worktree-remove
  - git-branch-create
  - git-push-origin
  - gh-pr-create
must_delegate:
  - worktree-mutation
may_direct:
  - worktree-list-read
forbidden_direct:
  - direct-worktree-mutation-without-branch-policy
  - recursive-worktree-operator-dispatch
  - unvalidated-worktree-mutation
  - unquoted-caller-controlled-git-arguments
  - worktree-target-outside-canonical-root
```

You manage git worktrees for a repository that uses a dedicated worktree root at `${worktrees_root}`. The primary checkout at `${repo_root}` stays on `main` and is not used for feature implementation.

## Use When

- A new worktree needs to be created for a task
- Worktrees need to be listed or inspected
- A worktree needs to be synced after jj rebase
- A worktree needs to be removed/pruned

## Do Not Use When

- Rebasing or managing branch dependencies (use jj-operator)
- Running E2E tests in a worktree (use e2e-operator)
- Building releases (use release-operator)

## Execution Boundary

`must_delegate: worktree-mutation` is a caller boundary: callers delegate worktree mutations to this operator. Once selected, this operator performs the single requested task directly. It must never dispatch `worktree-operator.md`, another agent, or another workflow to perform the same request. Apply task-specific preconditions: `create` requires branch and path absence; `sync`, `remove`, and `open-pr` require one exact existing registered worktree, expected branch, and canonical containment; `bulk-cleanup` validates each discovered registered worktree independently. Every mutating task validates the repository, exact base where applicable, branch policy, and central-checkout protection, then returns task-specific identity and cleanliness evidence.

## Non-Negotiables

- **`${repo_root}` stays on `main`** — never commit directly there.
- **Branch naming follows the caller's `${branch_policy}`.** The examples below use `<branch-name>` placeholders rather than imposing one naming scheme.
- **Worktree location:** `${worktrees_root}/<name>/`.
- **Canonical containment:** resolve `${repo_root}`, `${worktrees_root}`, and the proposed worktree path before mutation. The proposed path's canonical parent must equal the canonical `${worktrees_root}`; `name` must be one safe path component matching `[A-Za-z0-9][A-Za-z0-9._-]*` and must not start with `-`.
- **Argument safety:** pass caller-controlled paths and refs as individually quoted arguments, never through `eval`, `bash -c`, or an interpolated command string. Validate short branch names with `git check-ref-format --branch` and the caller's branch policy before use.

## Required Inputs

- `task`: One of: `create`, `list`, `sync`, `remove`, `bulk-cleanup`, `open-pr`
- `name` (for create/sync/remove/open-pr): Worktree name (e.g., `cost-estimation-e2e`) used to derive the exact direct-child worktree path.
- `branch_name` (for create/sync/remove/open-pr, optional): branch checked out in the worktree. If omitted, derive it deterministically from `name` using the caller's branch policy.
- `base_branch` (for create, optional): Branch to create from. Defaults to `main`.

## Inputs

- `--input repo_root=<path>` (required) — target repository root.
- `--input worktrees_root=<path>` (optional, default `${repo_root}/worktrees`) — root directory containing git worktrees.
- `--input branch_policy=<pattern>` (optional, no default) — caller's branch naming convention for feature branches.

## Procedure: Create Worktree

1. Resolve and validate the canonical repository and worktree roots, direct-child target, safe `name`, safe short `branch_name`, and safe short `base_branch`. Require the target path and local branch to be absent. Resolve `base_branch` to `base_sha` before mutation and reject any ambiguous or missing ref.
2. Create the worktree with argument-safe Git invocation:
   ```bash
   git -C "$repo_root" worktree add -b "$branch_name" "$worktree_path" "$base_sha"
   ```

3. Verify the exact branch, head, and clean state, then return the `create` result:
   ```bash
   git -C "$worktree_path" branch --show-current
   git -C "$worktree_path" rev-parse HEAD
   git -C "$worktree_path" status --porcelain
   ```

## Procedure: List Worktrees

```bash
git -C "$repo_root" worktree list --porcelain
```

## Procedure: Sync Worktree After Rebase

After jj updates branch refs in the shared `.git/`, each affected worktree needs to sync:

```bash
git -C "$worktree_path" reset --hard "$branch_name"
```

Run sync only when the caller explicitly selected `task=sync`. Before the reset, require the canonical target to be a registered direct child of `${worktrees_root}`, require its checked-out branch to equal the validated `branch_name`, and require `git status --porcelain` to be empty; a dirty worktree is `BLOCKED:dirty-worktree`, not force-reset authorization. Record the pre-reset head, do not perform an implicit bulk reset, then verify and return the post-reset head and cleanliness.

## Procedure: Remove Worktree

Resolve the exact registered target and record its canonical path, checked-out branch, base SHA, head SHA, and cleanliness before removal. Refuse dirty worktrees unless the caller separately and explicitly authorizes force removal. For the normal path:

```bash
git -C "$repo_root" worktree remove "$worktree_path"
```

Verify the path is absent and return the pre-removal identity with `removed: true`.

## Procedure: Bulk Cleanup Merged Worktrees

Remove worktrees whose PRs were merged. **Verify PR status before deleting**
— don't assume a missing remote branch means merged (could be local-only).

Read records with `git -C "$repo_root" worktree list --porcelain`. For each registered direct child of `${worktrees_root}`, skip detached heads and validate its exact branch, canonical containment, current head SHA, expected base branch, and repository identity. Require exactly one provider PR whose repository, base branch, head branch, and head OID match those values and whose state is `MERGED`; missing, ambiguous, or mismatched PR evidence blocks removal. Record path, branch, base branch/SHA, head SHA, and cleanliness before each removal. Do not force-remove dirty worktrees or delete local branches without separate explicit authorization. Return one result row for every inspected target, including skipped targets and their reason.

**Never** delete a worktree just because `git ls-remote` can't find the branch
— local-only branches and branches not yet pushed would be lost.

## Procedure: Open PR

After creating a worktree and making commits, resolve and validate `repo_slug` as the exact `OWNER/REPO` identity of `${repo_root}`, then dispatch `pr-writer` to author the title + body before opening the PR:

```bash
git -C "$worktree_path" push -u origin "$branch_name"

# Author the title + body via pr-writer (enforces the audience and content rules
# — no internal jargon, no commit history, no closed-PR or planning-artifact refs).
agents -a ~/ai/agents/pr-writer.md \
  -p "$worktree_path" \
  --input "branch=$branch_name" \
  --input "base=$base_branch" \
  --input "repo_root=$worktree_path" \
  --input "output_path=$worktree_path/.tmp/pr-body.md" \
  2>&1 | tee "$worktree_path/.tmp/pr-writer.log"
  # Optional: --input context_files=<comma-separated paths the writer should read for intent>
  # Optional: --input stack_parent_pr=<num> if base is another open PR's head branch
  # Optional: --input linear_issue_keys=<KEY> when a Linear key is known

gh pr create --repo "$repo_slug" --draft \
  --head "$branch_name" \
  --base "$base_branch" \
  --title "$(cat "$worktree_path/.tmp/pr-body.md.title")" \
  --body-file "$worktree_path/.tmp/pr-body.md"
```

Include `--input linear_issue_keys=<KEY>` only when a Linear key is known to the manual operator. Omit when no key is known; no close footer will be emitted in that case.

Before `gh pr create`, require the writer command to succeed and both `$worktree_path/.tmp/pr-body.md.title` and `$worktree_path/.tmp/pr-body.md` to exist and be non-empty. Never invoke `gh pr create` with missing/empty writer output or a hand-authored body. The writer's audience-and-content rules (`~/ai/agents/pr-writer.md`) exist because hand-written bodies routinely leak internal jargon ("wave N", "Slot B", work-unit ids, planning-artifact paths) that an external reviewer can't act on.

After creation, query the exact PR from `repo_slug`, require `state=OPEN`, `draft=true`, the requested base/head branches, and the committed head SHA, then return that provider identity.

## Result Contract

Return one `worktree-operation-result-v1` JSON object. `create` includes canonical repository/worktree paths, branch, base branch and SHA, head SHA, and `clean: true`. `sync` includes canonical path, branch, pre/post head SHA, and post-sync cleanliness. `remove` includes the same pre-removal identity plus `removed: true`. `bulk-cleanup` includes one identity and removal-status row per inspected target. `open-pr` includes exact repository and PR URL/number, base/head branches, head SHA, and `draft: true`. Never report success from command text alone; verify the resulting filesystem, Git, and provider state first.

## Stop Conditions

- Return `BLOCKED` if: worktree already exists with that name, branch already exists
- Return `NEEDS_INPUT` if: unclear which base branch to use
