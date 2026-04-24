# CodeRabbit Loop

Step 7 of the implementation pipeline. Run until per-pass value drops to zero; do not push during the loop.

## Preconditions

- Run the loop from the branch under review, not from `main`.
- Use the branch worktree or checkout path as `--cwd`.
- Start from the current review commit. The loop assumes one reviewable commit per concern.

## Invocation

```bash
coderabbit review --plain --base main --cwd <project-dir>
```

- `--plain` strips formatting so agents can parse findings reliably.
- `--base main` compares against the base branch. Adjust it only when the branch is stacked on something other than `main`.
- `--cwd <project-dir>` runs against the target working directory. Use the worktree path for the branch under review.

## Loop

```text
1. Run `coderabbit review`.
2. Read the findings. Fix everything useful in-place.
3. `git commit --amend --no-edit` to fold the fix into the single branch commit.
4. Re-run CodeRabbit.
5. Stop when per-pass value drops to zero.
```

When pass findings are copied into audit history, assign collision-safe IDs as `R<round>-F<NN>`. Preserve CodeRabbit's original text in the finding summary, not as the canonical ID.

Typical convergence: 3-6 passes.

When an agent-driven `coderabbit-operator` runs this loop, run `process-tree-auditor` after convergence and before returning to Phase 8. The expected process includes the operator prompt/log, pass outputs, amend-only evidence, latest CodeRabbit output, and audit-history role output when the loop reached a second pass. A blocking process violation prevents handoff to PR review gates.

## Rules

- **Never push during the loop.** The branch stays local. Pushing between passes breaks the amend-only pattern and creates force-push noise in review history.
- **Amend, do not stack.** All fixes fold into one commit per concern. If the branch already contains a review-ready stack, each stacked commit runs its own independent CodeRabbit loop.
- **Stop on value, not on emptiness.** "Per-pass value drops to zero" means the remaining findings are nitpicks, out-of-scope suggestions, or duplicates. It does not mean the report is literally empty.
- **Do not pre-commit around CodeRabbit.** Fix findings in the working tree, amend, re-run. Do not create a new commit per pass.
- **Run tests as needed, not as a loop ritual.** Validate when a finding changes behavior, contracts, or risk. The loop contract itself is amend-and-rerun, not "new commit plus full push cycle."
- **Do not weaken tests to converge.** A CodeRabbit finding is not a reason to relax assertions, regenerate baselines, delete coverage, narrow input space, or remove risk annotations.
- **Treat tests as ground truth.** If a review finding shows a test is wrong, route that through changed intent, corrected fixture truth, explicit invalidation, or documented test bug evidence; otherwise fix product code.
- **Stale re-posts are ignorable.** CodeRabbit sometimes re-posts prior-pass findings against a new HEAD after the fix has landed. Verify against the current file; if the fix is present, move on.
- **Track pass-loop oscillation.** When a CodeRabbit loop reaches a second pass, use the audit-history schema to distinguish progress from same-family churn, duplicate reposts, and flip-flops.
- **Local branch hygiene matters.** Because the branch stays local, rebases and fixups stay cheap until the loop converges.
- **Use the latest pass output.** Do not keep fixing against stale comments after a fresh amend and rerun.

## Who Runs The Loop

- In agent-driven pipelines, a CodeRabbit operator agent using `gpt-high` runs the loop.
- In human-driven work, the human runs it interactively.

See `~/ai/models/roles.md` for the model-role rationale.

## Relation To PR Review

CodeRabbit is step 7. The post-CodeRabbit review gates run afterward:

- test audit
- multi-concern review
- justification review
- commit-hygiene check
- synthesize and post

See `~/ai/workflows/pr-review.md`.
