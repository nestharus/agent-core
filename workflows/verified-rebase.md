---
workflow:
  id: verified-rebase
workflow_dispatch_contract:
  orchestrator: "jj-operator"
  inputs:
    - "BRANCH and TARGET refs for the rebase"
    - "optional SOURCE and PARENT_BUNDLE for scoped or stacked rebases"
  expectations:
    - "produces a deterministic bundle for rebase review"
    - "computes mechanical provenance from predicted tree, actual tree, conflicts, and range-diff output"
    - "does not push and does not resolve conflicts"
  outputs:
    - "bundle under .tmp/verified-rebase/<branch-slug>/<timestamp>/"
    - "stdout verdict CLEAN, DIRTY-EXPLAINED, DIRTY-UNPROVENANCED, or BLOCKED"
    - "local refs/pre-rebase/<branch> rollback anchor and rollback.sh helper"
  non_goals:
    - "does not provide a plain rebase fallback"
    - "does not decide whether the caller should push"
    - "does not judge semantic correctness of conflict resolutions"
---
# Verified Rebase

Produce a deterministic artifact bundle for every rebase so a reviewer inspects O(residual) content instead of O(full-diff), with a cheap local rollback when the bundle shows unacceptable residuals.

This is the single rebase path. The plain `jj rebase` procedure is retired — see [`~/ai/agents/jj-operator.md`](../agents/jj-operator.md) `Procedure: Verified Rebase`.

Model assignments: [`~/ai/models/roles.md`](../models/roles.md). CLI: [`~/ai/workflows/agents-cli.md`](agents-cli.md). Conventions: [`~/ai/conventions/no-backwards-compatibility.md`](../conventions/no-backwards-compatibility.md).

## Workflow Dispatch Surface

### Orchestrator

jj-operator

### Inputs

- BRANCH and TARGET refs for the rebase
- optional SOURCE and PARENT_BUNDLE for scoped or stacked rebases

### Expectations

- produces a deterministic bundle for rebase review
- computes mechanical provenance from predicted tree, actual tree, conflicts, and range-diff output
- does not push and does not resolve conflicts

### Outputs

- bundle under .tmp/verified-rebase/<branch-slug>/<timestamp>/
- stdout verdict CLEAN, DIRTY-EXPLAINED, DIRTY-UNPROVENANCED, or BLOCKED
- local refs/pre-rebase/<branch> rollback anchor and rollback.sh helper

### Non-goals

- does not provide a plain rebase fallback
- does not decide whether the caller should push
- does not judge semantic correctness of conflict resolutions

## Inputs

- `BRANCH` — branch to rebase (e.g. `feat/p2-version-parsing-unification`).
- `TARGET` — ref to rebase onto. Either `origin/main` (main-target case) or a parent branch ref (stacked case, e.g. `feat/p2-version-parsing-unification`).
- `PARENT_BUNDLE` — *only in stacked case* — path to the parent's already-produced bundle directory.
- `SOURCE` (optional) — git SHA or jj revset marking the first commit in `BRANCH`'s unique contribution. When set, the rebase is scoped to `SOURCE` and its descendants instead of the full `merge-base(BRANCH, TARGET)..BRANCH` range. Use this when `BRANCH` carries stale copies of `TARGET`'s commits because the parent was rewritten without `BRANCH` being rebased at the same time. See "Stale parent history" below.

## Outputs

- A bundle directory at `<repo_root>/.tmp/verified-rebase/<branch-slug>/<ISO-timestamp>/`.
- A verdict on stdout: `CLEAN` | `DIRTY-EXPLAINED` | `DIRTY-UNPROVENANCED` | `BLOCKED:<reason>`.
- A local git ref `refs/pre-rebase/<branch>` pointing at the pre-rebase tip (durable until manually deleted).

## Non-negotiables

- **All jj commands run in `${repo_root}`** — never in a worktree. Same rule as [`jj-operator`](../agents/jj-operator.md).
- **The workflow never pushes.** `git push` is the caller's decision, after inspecting the bundle.
- **The workflow never resolves conflicts.** Residuals and `conflict-artifacts/` are output for human/AI review.
- **Single rebase path.** No `mode=` flag. No plain-rebase fallback except the explicit legacy-git escape hatch in [`jj-operator`](../agents/jj-operator.md) `Fallback: Legacy Git Rebase`.
- **Bundle is always produced** — for `CLEAN` verdicts too. The point of the workflow is the bundle.

## Reference anchors

All commands use `$BRANCH` and `$TARGET` from Inputs.

| Ref | Meaning | Capture |
|-----|---------|---------|
| `PRE_BASE` | default: `merge-base(branch, target)` **before** fetch. With `SOURCE` set: `parent(SOURCE)`. | default: `git merge-base "$BRANCH" "$TARGET"` (pre-fetch); SHA. With `SOURCE`: `git rev-parse "${SOURCE}^"`. |
| `PRE_TIP` | branch tip **before** rebase | `git update-ref "refs/pre-rebase/$BRANCH" "$BRANCH"` then `git rev-parse "refs/pre-rebase/$BRANCH"`; SHA |
| `NEW_TARGET` | target ref **after** fetch | `jj git fetch` then `git rev-parse "$TARGET"`; SHA. `jj git fetch` is a no-op for local `$TARGET` but still runs for `origin/*` updates. |
| `POST_TIP` | branch tip **after** rebase | `git rev-parse "$BRANCH"`; SHA |
| `POST_CHANGE_ID` | jj change id of branch tip **after** rebase | `jj log -r "$BRANCH" --no-graph --no-pager --limit 1 --template 'change_id'`. Addresses post-rebase revision for `jj file show` / `jj resolve --list`. |
| `PREDICTED_TREE` | tree a clean 3-way merge would produce (merge-ort) | `git merge-tree --write-tree --merge-base="$PRE_BASE" "$PRE_TIP" "$NEW_TARGET"`; tree oid |

`PREDICTED_TREE` is a tree object, not a commit. Downstream diffs use it as a tree-ish alongside `$POST_TIP^{tree}`.

`POST_CHANGE_ID` is jj's stable change id, distinct from `POST_TIP` (git SHA). Change ids survive rebases; git SHAs don't.

## Bundle schema

Path: `<repo_root>/.tmp/verified-rebase/<branch-slug>/<ISO-timestamp>/`

Slugging: replace `/` with `__`. Example: `feat/p2-version-parsing-unification` → `feat__p2-version-parsing-unification`. Deterministic and reversible.

| File | Producer | Required content |
|------|----------|------------------|
| `summary.md` | workflow | Branch, target, all SHAs/oids incl. `POST_CHANGE_ID`, verdict, hunk counts, rename-present flag, `parent-pointer-check` line for stacked, one-liner rollback instruction |
| `refs.json` | workflow | `{branch, target, PRE_BASE, PRE_TIP, NEW_TARGET, POST_TIP, POST_CHANGE_ID, PREDICTED_TREE, timestamp, parent_bundle?, verdict}` |
| `target-delta.patch` (named `main-delta.patch` when `TARGET=origin/main`) | `git diff "$PRE_BASE" "$NEW_TARGET" --find-renames` | What the target introduced during the wait |
| `branch-intended.patch` | `git diff "$PRE_BASE" "$PRE_TIP" --find-renames` | What the branch intended to change |
| `branch-actual.patch` | `git diff "$NEW_TARGET" "$POST_TIP" --find-renames` | What the branch changes after rebase |
| `residual.patch` | `git diff "$PREDICTED_TREE" "$POST_TIP^{tree}" --find-renames` | **Provenance check.** See "Verdict" below. |
| `range-diff.txt` | `git range-diff "$PRE_BASE..$PRE_TIP" "$NEW_TARGET..$POST_TIP"` | Per-commit correspondence; catches drops/reorders |
| `conflict-artifacts/files.txt` | `jj resolve --list -r "$POST_CHANGE_ID" --no-pager` | One conflicted path per line; empty if no conflicts |
| `conflict-artifacts/<slug>.conflict` | `jj file show -r "$POST_CHANGE_ID" "$path"` | jj's first-class conflict representation, per conflicted path |
| `jj-op-log-before.txt` | `jj op log --limit 20 --no-pager` pre-rebase | Audit trail |
| `jj-op-log-after.txt` | `jj op log --limit 20 --no-pager` post-rebase | Audit trail |
| `jj-pre-op-id.txt` | `jj op log --limit 1 --no-graph --no-pager --template 'id'` (captured post-fetch, pre-rebase) | Rollback target |
| `rollback.sh` | workflow (template below) | Idempotent, precondition-checked rollback helper |
| `parent-delta.patch` *(stacked only)* | copy of `$PARENT_BUNDLE/branch-actual.patch` | Parent's shift — what the child inherits from its parent's rebase |

## Phases

Phases 1–11. All run in `${repo_root}`. `$BUNDLE` is the bundle directory created in phase 1.

### 1. Preflight

- Verify `@` has no working-copy changes *or* `@` is an empty change. `jj status` must not show `Working copy changes:` with tracked files, unless they're safely stashed on a throwaway bookmark.
- Verify `$BRANCH` exists locally: `jj log -r "$BRANCH" --no-pager --limit 1` succeeds.
- Verify `$TARGET` exists: `git rev-parse --verify "$TARGET"` succeeds.
- If `$SOURCE` is set: verify `git rev-parse --verify "$SOURCE"` succeeds **and** `git merge-base --is-ancestor "$SOURCE" "$BRANCH"` returns 0.
- Verify `.tmp/` is in repo-root `.gitignore`. If not, append a single line `.tmp/` and commit to a throwaway jj change (never directly to `main`).
- Create `$BUNDLE = <repo_root>/.tmp/verified-rebase/$(echo "$BRANCH" | tr '/' '__')/$(date -u -Iseconds)/`.

Stop: `BLOCKED:dirty-working-copy` | `BLOCKED:branch-not-found` | `BLOCKED:target-not-found` | `BLOCKED:source-not-found` | `BLOCKED:source-not-ancestor-of-branch`.

### 2. Capture PRE state

```bash
if [ -n "${SOURCE:-}" ]; then
  PRE_BASE=$(git rev-parse "${SOURCE}^")
else
  PRE_BASE=$(git merge-base "$BRANCH" "$TARGET")
fi
git update-ref "refs/pre-rebase/$BRANCH" "$BRANCH"
PRE_TIP=$(git rev-parse "refs/pre-rebase/$BRANCH")
jj op log --limit 20 --no-pager > "$BUNDLE/jj-op-log-before.txt"
```

The `refs/pre-rebase/$BRANCH` ref overwrites unconditionally. Stale refs from prior runs are replaced.

### 3. Fetch

```bash
jj git fetch
NEW_TARGET=$(git rev-parse "$TARGET")
JJ_PRE_OP_ID=$(jj op log --limit 1 --no-graph --no-pager --template 'id')
echo "$JJ_PRE_OP_ID" > "$BUNDLE/jj-pre-op-id.txt"
```

`jj git fetch` is a no-op for a local `$TARGET` ref but still pulls `origin/*` updates. `JJ_PRE_OP_ID` is captured *after* fetch (so fetch is part of the baseline) and *before* any rebase mutation — this is the rollback target.

Stop: `BLOCKED:fetch-failed`.

### 4. Predict

```bash
PREDICTED_TREE=$(git merge-tree --write-tree --merge-base="$PRE_BASE" "$PRE_TIP" "$NEW_TARGET")
```

`merge-tree` writes a tree object. If it returns non-zero or emits no tree oid (rare, e.g. unsupported binary operations), stop with `BLOCKED:merge-tree-failed`.

### 5. Rebase

Delegate to [`jj-operator`](../agents/jj-operator.md) `Procedure: Verified Rebase` (the single rebase path). The operator runs:

```bash
if [ -n "${SOURCE:-}" ]; then
  jj --config 'revset-aliases."immutable_heads()"="none()"' \
    rebase -s "$SOURCE" -d "$NEW_TARGET"
else
  jj --config 'revset-aliases."immutable_heads()"="none()"' \
    rebase -b "$BRANCH" -d "$NEW_TARGET"
fi
```

followed by divergent-revision cleanup per the operator. The operator **does not push**.

Stop: `BLOCKED:rebase-failed` (rare; jj accepts conflicts and stores them as first-class tree values).

### 6. Capture POST state

```bash
POST_TIP=$(git rev-parse "$BRANCH")
POST_CHANGE_ID=$(jj log -r "$BRANCH" --no-graph --no-pager --limit 1 --template 'change_id')
jj op log --limit 20 --no-pager > "$BUNDLE/jj-op-log-after.txt"

mkdir -p "$BUNDLE/conflict-artifacts"
jj resolve --list -r "$POST_CHANGE_ID" --no-pager \
  > "$BUNDLE/conflict-artifacts/files.txt" 2>/dev/null || true
while IFS= read -r P; do
  [ -z "$P" ] && continue
  SLUG=$(echo "$P" | tr '/' '__')
  jj file show -r "$POST_CHANGE_ID" "$P" \
    > "$BUNDLE/conflict-artifacts/${SLUG}.conflict"
done < "$BUNDLE/conflict-artifacts/files.txt"
```

If there are no conflicts, `files.txt` is empty and no `.conflict` files are written.

### 7. Compute diffs

```bash
# target-delta (named main-delta.patch when TARGET is origin/main)
if [ "$TARGET" = "origin/main" ]; then DELTA=main-delta.patch; else DELTA=target-delta.patch; fi
git diff "$PRE_BASE" "$NEW_TARGET" --find-renames > "$BUNDLE/$DELTA"
git diff "$PRE_BASE" "$PRE_TIP"    --find-renames > "$BUNDLE/branch-intended.patch"
git diff "$NEW_TARGET" "$POST_TIP" --find-renames > "$BUNDLE/branch-actual.patch"
git diff "$PREDICTED_TREE" "$POST_TIP^{tree}" --find-renames > "$BUNDLE/residual.patch"
git range-diff "$PRE_BASE..$PRE_TIP" "$NEW_TARGET..$POST_TIP" > "$BUNDLE/range-diff.txt"
```

### 8. Compute verdict

Mechanical gate — purely syntactic, based on path-set membership and range-diff markers:

```
Let RP = {path : path appears in residual.patch}.
Let CF = {path : path appears in conflict-artifacts/files.txt}.
Let DC = {commit : range-diff.txt row prefix is '<' (dropped) or shows unexpected drift without a '=' match}.

Verdict:
  CLEAN                if RP is empty AND DC is empty
  DIRTY-EXPLAINED      if RP ⊆ CF     AND DC is empty
  DIRTY-UNPROVENANCED  if RP ⊄ CF     OR  DC is non-empty
```

`DIRTY-EXPLAINED` proves mechanical provenance: every residual hunk sits in a file that had a conflict. The reviewer still has to judge each resolution's correctness semantically — the gate doesn't claim the resolution was *right*, only that it had a provenance.

`DIRTY-UNPROVENANCED` is the only blocking verdict. It means either (a) content changed in a file that had no conflict, or (b) a commit was dropped/reordered without explanation. Both require human review.

In the stacked case where `PREDICTED_TREE` collapses (see §3.4 of [the proposal](../.build/VR-01-verified-rebase-proposal.md)), `residual.patch` is often trivially empty — the load for the child's content check is carried by `conflict-artifacts`, `range-diff.txt`, and the parent-pointer invariant (§9 below), not `residual.patch` alone.

### 9. Stacked cross-check (only when `$PARENT_BUNDLE` is set)

```bash
PARENT_POST_TIP=$(jq -r '.POST_TIP' "$PARENT_BUNDLE/refs.json")
if [ "$PARENT_POST_TIP" = "$NEW_TARGET" ]; then
  echo "parent-pointer-check: PASS" >> "$BUNDLE/summary.md.fragment"
else
  echo "parent-pointer-check: FAIL (expected $NEW_TARGET got $PARENT_POST_TIP)" >> "$BUNDLE/summary.md.fragment"
fi
cp "$PARENT_BUNDLE/branch-actual.patch" "$BUNDLE/parent-delta.patch"
```

The pointer invariant `parent.POST_TIP == child.NEW_TARGET` is the only cross-bundle invariant. FAIL means the child was rebased onto the wrong commit.

### 10. Write bundle

Assemble `summary.md` and `refs.json` from the captured variables. Write `rollback.sh` from the template below. Ensure `rollback.sh` is executable (`chmod +x`).

**`rollback.sh` template:**

```bash
#!/bin/bash
set -e
BUNDLE="$(cd "$(dirname "$0")" && pwd)"
if [ -f "$BUNDLE/rolled-back.flag" ]; then
  echo "Already rolled back at $(cat "$BUNDLE/rolled-back.flag"). No-op."
  exit 0
fi
OP_ID=$(cat "$BUNDLE/jj-pre-op-id.txt")
if ! jj op log --no-graph --no-pager --limit 1000 --template 'id ++ "\n"' \
      | grep -qx "$OP_ID"; then
  echo "ERROR: op $OP_ID not in jj op log (likely GC'd). Manual recovery required." >&2
  exit 2
fi
jj op restore "$OP_ID"
date -Iseconds > "$BUNDLE/rolled-back.flag"
echo "Rolled back to $OP_ID."
```

Rollback limits:

- Rollback is **local-only**. If a push happened between the rebase and the rollback, the remote branch is not unpushed — caller must `git push --force-with-lease` after rollback if a push occurred.
- `jj op log` default TTL is ~30 days; the precondition check fails with exit 2 if the op id was GC'd.
- The flag file makes re-running the script a safe no-op.

### 11. Return verdict

Print one of:

- `CLEAN` — bundle produced; caller may push freely.
- `DIRTY-EXPLAINED` — bundle produced; residuals confined to files that had conflicts; caller reviews resolutions before deciding to push.
- `DIRTY-UNPROVENANCED` — bundle produced; residuals include paths without conflict provenance or range-diff anomalies; **caller reviews before any push**.
- `BLOCKED:<reason>` — see the stop conditions in phases 1–5.

Caller decides push/rollback. This workflow does neither.

## Stacked branches

Bottom-up recursion, using the workflow inputs:

1. Run for the parent — `BRANCH=<parent>`, `TARGET=origin/main`, no `PARENT_BUNDLE`. Bundle A produced.
2. jj auto-rebases the child when the parent moves. Run for the child — `BRANCH=<child>`, `TARGET=<parent>`, `PARENT_BUNDLE=<path-to-A>`. Bundle B produced with `parent-pointer-check` recorded.

`refs/pre-rebase/<child>` is overwritten unconditionally in phase 2, so a prior run's stale ref does not contaminate the child bundle's baseline.

## Stale parent history

When a stack's parent is rewritten without the child being rebased at the same time, the child's local history retains stale copies of the parent's pre-rewrite commits. Running the workflow with default (`-b`) scope on such a child replays those stale commits onto the new parent and conflicts with the parent's current versions of the same files.

Symptoms:

- `DIRTY-UNPROVENANCED` verdict.
- `conflict-artifacts/files.txt` concentrates in paths that `target-delta.patch` edits.
- `range-diff.txt` shows many `<` (left-only) entries with subjects matching commits in `target-delta.patch` — the branch carries near-duplicate copies of the new `TARGET`'s commits.
- Residual hunk count is misleadingly large because jj wrote first-class conflict trees (`.jjconflict-base-N/`, `.jjconflict-side-N/`) into `POST_TIP^{tree}`, so `residual.patch` includes those entire side trees.

Recovery:

1. Run the bundle's `rollback.sh`.
2. Identify the first commit in `BRANCH`'s unique contribution. After fetch, `git log --oneline TARGET..BRANCH` lists `BRANCH`'s commits chronologically; the first one whose subject doesn't match any commit in `git log --oneline PRE_BASE..NEW_TARGET` is your `SOURCE`.
3. Re-run the workflow with `SOURCE=<that-commit>`. The bundle then verifies only the branch's actual unique contribution; `branch-intended.patch` reflects the branch's real intent rather than its full carried history, and `range-diff.txt` shows a clean `SOURCE..PRE_TIP ↔ NEW_TARGET..POST_TIP` correspondence.

This case is structurally distinct from a content conflict — recovery is mechanical (re-scope the rebase), not manual conflict resolution. Detection is intentionally not automated: the symptoms above are deterministic enough that diagnosis stays in caller territory, and a heuristic precondition would either over-block or miss edge cases.

## Tests (contract)

Workflow files aren't unit-testable. The contract is:

| # | Scenario | Expected verdict / artifacts |
|---|----------|------------------------------|
| T1 | Conflict-free rebase; non-overlapping main changes | `CLEAN`. `residual.patch` empty. `range-diff.txt` shows `=` for every branch commit. |
| T2 | Text conflict on a line both sides edited | `DIRTY-EXPLAINED`. `residual.patch` touches only the conflicted file. `conflict-artifacts/<slug>.conflict` non-empty. |
| T3 | Stacked parent/child rebase | Two bundles. Bundle B's `summary.md` shows `parent-pointer-check: PASS`. |
| T4 | `rollback.sh` after a rebase | Branch ref back to `PRE_TIP`. `refs/pre-rebase/<branch>` intact. `rolled-back.flag` exists. Re-running is no-op. |
| T5 | Live exercise — production branches | Bundles produced; no push; verdicts reported; rollback available. |
| T6 | No-op rebase (branch already up-to-date with target) | `CLEAN`. `target-delta` empty. `branch-intended` == `branch-actual`. |
| T7 | Rename conflict (main renames a file the branch edited) | `DIRTY-EXPLAINED` with rename-present flag; OR `DIRTY-UNPROVENANCED` if ort/jj disagree (flagged as rename-detection divergence). |
| T8 | Delete conflict (main deletes, branch modifies) | `DIRTY-EXPLAINED`. `conflict-artifacts/<slug>.conflict` shows the deletion side. |
| T9 | Binary conflict | `DIRTY-EXPLAINED` or `BLOCKED:merge-tree-failed` depending on ort support. |
| T10 | Rebase leaves unresolved conflicts | `DIRTY-EXPLAINED`. `conflict-artifacts/` has content. Caller resolves or rolls back. |
| T11 | Multi-parent basis collapse (one parent merged; child rebases onto main directly) | Single bundle at child level; no `parent-pointer-check` (basis was never pushed as target). |
| T12 | Branch carries stale copies of parent's commits (parent rewritten without child rebase) | With default scope: `DIRTY-UNPROVENANCED`. With `SOURCE=<first-unique-commit>`: `CLEAN`; `branch-intended.patch` reflects only the branch's unique work. |

## Anti-scope

- Not a merge-conflict auto-resolver.
- Not a replacement for [`commit-hygiene-operator`](../agents/commit-hygiene-operator.md).
- Not a PR-level tool — local branches only. No GitHub state.
- Does not decide whether to push. Always stops after bundle.
- Does not sync worktrees. Caller invokes [`worktree-operator`](../agents/worktree-operator.md) if needed.
- Does not judge resolution correctness. Mechanical provenance only (residual ⊆ conflict paths).
- Does not normalize diffs across refactors. If main's refactor moves code and jj ports the branch's edit successfully, that appears in `residual.patch` — the workflow surfaces it, not judges it.
- Does not support multi-target rebase.
- Does not handle `jj op` TTL recovery — `rollback.sh` fails loudly if the op was GC'd.

## Gate ownership

Per [`~/ai/conventions/gate-ownership.md`](../conventions/gate-ownership.md):

- Verdict production is **model-owned** (the mechanical gate in phase 8).
- Pushing or rolling back is **human-owned**. The workflow never does either.
