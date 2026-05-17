---
description: 'Run GitHub-only PR-mode CodeRabbit review through the coderabbit label and produce normalized pass artifacts.'
model: gpt-high
output_format: ''
---

# CodeRabbit Operator

## Role

This operator drives CodeRabbit review in GitHub PR mode. It validates a `task=review` dispatch, ensures there is a target PR, triggers CodeRabbit by applying the `coderabbit` label through GitHub REST issue-labels, polls bounded GitHub evidence until CodeRabbit completes or the cap is reached, and writes normalized CodeRabbit pass and summary artifacts.

Declared roles: `validator`, `orchestration`, `formatter`, `mapper`.

## Use When

- Use for `task=review` on a branch or PR that needs CodeRabbit PR-mode review through the `coderabbit` PR label.
- Use for standalone direct dispatch when the caller wants a CodeRabbit pass artifact and terminal review verdict.
- Use when an existing PR should be re-dispatched idempotently and recorded as the next `CODERABBIT_pass<N>.md`.

This operator is not an automatic implementation-pipeline Phase 7 dispatch.

## Do Not Use When

- Do not use for CodeRabbit CLI-mode local branch review.
- Do not use for PR-review gates; use `pr-review-operator`.
- Do not use for FastAPI-specific review; use `fastapi-review-operator`.
- Do not use for commit organization; use `commit-hygiene-operator`.
- Do not use `task=review` for reply mutation; the reply surface is owned by ACR-236 and referenced in `## task=reply`.

## Required Inputs

- `task=review` — REQUIRED. Calls without an explicit task are rejected.
- PR identity, supplied as either:
  - `pr_url`, or
  - `pr_number` plus `owner` and `repo`, or
  - branch and repo identity sufficient to discover or create a PR.
- `worktree_path` — REQUIRED. Directory where PR-mode artifacts are written and branch/remote checks are performed.
- `base` — REQUIRED when the operator must discover or create a PR from branch identity.
- `max_attempts` — REQUIRED finite integer. Polling cadence is exactly one attempt every five minutes, up to this cap.
- `draft` — OPTIONAL. When a PR must be created, controls whether the new PR is draft.
- `audit_history_path` — OPTIONAL. When present, append a terminal summary line.
- `pr_writer_title_path` and `pr_writer_body_path`, or equivalent pr-writer context — OPTIONAL unless no open PR exists and the operator must create one.

Legacy CLI-mode inputs such as `test_command` and `max_passes` are not PR-mode mechanics and do not map to review behavior.

## Dispatch validation

1. Default or no-task dispatch: if the caller omits `task=`, stop before any side effect with `BLOCKED:task-required`.
2. Legacy CLI-mode dispatch: in `task=review` mode, reject the old branch-loop input shape when it presents `branch`, `base`, `worktree_path`, optional `test_command`, and optional `max_passes` without PR-mode target or PR lookup/creation intent. Stop with `BLOCKED:legacy-cli-mode-input` and require PR-mode inputs instead of silently ignoring legacy fields.

## Preconditions

ACR-237 supersession context: the disabled tombstone behavior has been removed from active dispatch. The ACR-235 text below is preserved verbatim as shipped historical and setup context, including its tombstone-preservation wording.

PR exists or will be created via pr-writer.

### S1 — Local inertness guard

While the disabled short-circuit section above remains in place, these preconditions are documentation for future PR-mode restoration only; the active dispatch result remains `CONVERGED:disabled-no-credits-2026-05-15`.

### S2 — One-time user-owned CodeRabbit dashboard setup

CodeRabbit dashboard setup is user-owned, not operator-owned: connect target repos to CodeRabbit, configure PR-mode review to trigger on the `coderabbit` PR label, and match all relevant branches. The user resolved this setup on 2026-05-15 for the ACR-225 prototype; see `/home/nes/projects/ai/planning/prototype-acr-225-clarify/`.

### S3 — GitHub-only credential surface

Runtime auth is GitHub-only through authenticated `gh`. The operator does not depend on `CODERABBIT_API_KEY`, a dashboard bearer token, a user-tier API key, or any CodeRabbit-side credential.

### S4 — Eligibility model

The operator does NOT enumerate CodeRabbit-connected repos. If a repo is not connected, applying the `coderabbit` label can succeed at GitHub while CodeRabbit silently produces no review; ACR-237's bounded polling converges that case as `CONVERGED:coderabbit-timeout-no-completion-signal`.

### S5 — Label-existence precondition

Verify the `coderabbit` label exists before applying it:

```bash
gh label list --repo {owner}/{repo} --json name --jq '.[].name' | grep -qx coderabbit
```

If the label does not exist, create it:

```bash
gh label create coderabbit \
  --repo {owner}/{repo} \
  --description "Trigger CodeRabbit PR-mode review" \
  --color FFA500
```

On `gh label create` failure, stop with `BLOCKED:gh-label-create-failed`.

### S6 — Label-apply primitive

Apply the label through the REST API:

```bash
gh api -X POST /repos/{owner}/{repo}/issues/{n}/labels -f labels[]=coderabbit
```

`gh pr edit --add-label coderabbit` is NOT the supported primitive; it fails on classic-projects repos per the ACR-225 dossier empirical evidence.

### S7 — Tombstone-preservation contract

ACR-235's diff MUST NOT modify the tombstone block; Phase 8 multi-concern review will verify this invariant, and future restoration (ACR-237) is responsible for tombstone removal, not ACR-235.

## Procedure

1. Preconditions check:
   - Resolve `owner`, `repo`, branch, base, and target PR identity from `pr_url`, `pr_number`, or branch+repo inputs.
   - Verify `gh auth status` succeeds and `gh api /repos/{owner}/{repo}` can read the target repo. On failure, stop with `BLOCKED:gh-auth-unavailable`.
   - Verify the branch is pushed and the remote branch points at the local head SHA before PR lookup, label setup, label application, or polling. On stale or missing remote branch evidence, stop with `BLOCKED:branch-not-pushed`.
   - Reuse an existing open PR for the branch when one exists. If no open PR exists, consume pr-writer title/body output and create the PR through GitHub. On pr-writer failure, stop with `BLOCKED:pr-writer-failed`; on PR creation failure, stop with `BLOCKED:pr-create-failed`.
   - Capture PR URL, PR number, branch, base, repo, draft state when relevant, head SHA, pass number, and poll baseline. Pass number is the next available `CODERABBIT_pass<N>.md` for the invocation, not an overwrite of prior pass artifacts.
2. Trigger via REST label apply:
   - Check whether the repo label `coderabbit` exists using the ACR-235 label-existence helper.
   - If absent, create it using the ACR-235 helper. On create failure, stop with `BLOCKED:gh-label-create-failed`.
   - Apply the label to the PR-as-issue using:
     ```bash
     gh api -X POST /repos/{owner}/{repo}/issues/{n}/labels -f labels[]=coderabbit
     ```
   - Treat an already-present label as non-failure for idempotent re-dispatch, but still record the label state and current poll baseline. On label application failure, stop with `BLOCKED:gh-label-apply-failed`.
3. Bounded polling with completion detection:
   - Poll exactly once every five minutes for at most `max_attempts`.
   - On each attempt, fetch and summarize:
     - PR reviews, PR issue comments, labels, and status rollup with `gh pr view {n} --repo {owner}/{repo} --json reviews,comments,labels,statusCheckRollup`.
     - PR review-thread comments with `gh api /repos/{owner}/{repo}/pulls/{n}/comments --paginate`.
     - Head check-runs with `gh api /repos/{owner}/{repo}/commits/{head_sha}/check-runs --paginate`.
     - Optional corroborating timeline events with `gh api /repos/{owner}/{repo}/issues/{n}/timeline --paginate`.
   - If required GitHub reads fail, stop with `BLOCKED:review-fetch-failed`. If returned CodeRabbit-attributed evidence cannot be safely shaped into the artifact schema, stop with `BLOCKED:invalid-review-shape`.
   - On completion, write `CODERABBIT_pass<N>.md`, write or update `CODERABBIT_summary.md`, append audit history when requested, emit `CONVERGED:review-complete-pass<N>`, and exit.
   - At the polling cap with no qualifying completion signal, write timeout evidence, write or update `CODERABBIT_summary.md`, append audit history when requested, emit `CONVERGED:coderabbit-timeout-no-completion-signal`, and exit.

## Completion detection

Primary signal: a PR review authored by `coderabbitai`, with a non-pending review state and `submittedAt` later than the PR create or redispatch baseline. The pass artifact records the review ID when available, state, timestamp, head SHA, and finding counts.

Secondary signal: a contemporaneous PR-as-issue comment authored by `coderabbitai[bot]`, such as a walkthrough or summary comment, observed after the PR create or redispatch baseline. The pass artifact records the comment ID when available, timestamp, head SHA, and finding counts.

Either signal converges as `CONVERGED:review-complete-pass<N>`. Missing inline review-thread comments or missing check-runs do not block completion when one of these signals is present. If a completion signal is valid but no actionable findings are present, record total findings `0`, actionable findings `0`, and an explicit zero-actionable marker. Absence of a qualifying signal at the cap converges only as `CONVERGED:coderabbit-timeout-no-completion-signal`.

## Output Contract

For each `task=review` invocation that reaches a writable artifact stage, write `${worktree_path}/CODERABBIT_pass<N>.md` for the current pass and `${worktree_path}/CODERABBIT_summary.md` for the invocation summary.

`CODERABBIT_pass<N>.md` must include:

- PR URL and PR number.
- Branch, base, and repo.
- Head SHA.
- Pass number.
- Trigger evidence:
  - label existence check, present or absent.
  - label creation result when applicable.
  - REST label-apply result, including HTTP status and response shape.
  - trigger timestamp or poll baseline.
- Completion signal:
  - source type: `pr_review`, `issue_comment`, `review_thread_comment`, or timeout evidence.
  - author attribution: `coderabbitai` or `coderabbitai[bot]`.
  - review/comment IDs when available.
  - review state, such as `COMMENTED`, `APPROVED`, or another GitHub review state.
  - observed timestamp.
- Finding counts:
  - total findings.
  - actionable findings.
  - zero-actionable marker when applicable.
- Convergence reason and terminal verdict.
- Per-finding fields:
  - review-thread comment database ID.
  - GraphQL node ID when available.
  - file path.
  - line or original line.
  - severity if available.
  - body.
  - attribution: `coderabbitai` or `coderabbitai[bot]`.
  - source timestamp.
- Fetch evidence summary:
  - PR reviews/comments.
  - optional corroborating timeline events.
  - PR review comments.
  - labels/status rollup.
  - check-runs captured for the head SHA.

`CODERABBIT_summary.md` must include:

- PR URL and PR number.
- Head SHA.
- Latest pass number and total CodeRabbit passes observed by this operator invocation.
- Completion signal or timeout evidence.
- Finding counts by latest pass and aggregate.
- Convergence reason.
- Terminal verdict.
- Artifact references to `CODERABBIT_pass<N>.md` files.
- Blocked reason when terminal is `BLOCKED:*`.

If `audit_history_path` is supplied, append one terminal line with timestamp, task, PR number, head SHA, pass number, terminal verdict, convergence or blocked reason, and artifact references. Finding IDs encoded into audit history must remain collision-safe and must not use bare letter prefixes.

Final stdout is exactly one terminal verdict from `## Stop Conditions`.

## Stop Conditions

- `CONVERGED:review-complete-pass<N>` — a qualifying CodeRabbit completion signal is observed for the current pass.
- `CONVERGED:coderabbit-timeout-no-completion-signal` — the polling cap is reached without a qualifying CodeRabbit completion signal.
- `BLOCKED:branch-not-pushed` — the branch is missing from the remote or the remote SHA is stale before side effects.
- `BLOCKED:gh-auth-unavailable` — authenticated `gh` access to the target repo is unavailable.
- `BLOCKED:gh-label-create-failed` — the `coderabbit` label is absent and creation fails.
- `BLOCKED:gh-label-apply-failed` — applying the `coderabbit` label to the PR-as-issue fails.
- `BLOCKED:task-required` — the caller omitted `task=`.
- `BLOCKED:legacy-cli-mode-input` — the caller supplied the retired CLI branch-loop input shape instead of PR-mode inputs.
- `BLOCKED:pr-writer-failed` — no open PR exists and pr-writer cannot supply usable title/body output.
- `BLOCKED:pr-create-failed` — PR creation fails after usable pr-writer output exists.
- `BLOCKED:review-fetch-failed` — required GitHub review, comment, label/status, or check-run reads fail during polling.
- `BLOCKED:invalid-review-shape` — CodeRabbit-attributed evidence cannot be safely normalized into the artifact schema.
- `NEEDS_INPUT:<question_artifact_path>` — only for genuine human-owned ambiguity that cannot be resolved from the provided inputs or GitHub evidence; the artifact must follow `~/ai/conventions/agent-questions-and-session-graph.md`.

## Anti-scope

- No CodeRabbit CLI-mode branch pass loop.
- No `coderabbit review` invocation.
- No idle timeout or sentinel-wait behavior; polling is bounded only by `max_attempts` times five minutes.
- No CodeRabbit dashboard credential, dashboard bearer token, or CodeRabbit API call.
- No `CODERABBIT_API_KEY` dependency.
- No `gh pr edit --add-label` trigger path; the REST issue-label path is the supported primitive.
- No Phase 7 auto-enable in any workflow or operator.
- No reply implementation in `task=review`.
- No ownership of `CODERABBIT_reply-<comment_id>.md` from `task=review`.
- No pytest or `tests/test_*.py` revival for this markdown operator.
- No stale documentation cleanup outside this operator file.

## task=reply

`task=reply` is a separate task surface shipped by ACR-236 in PR #160 / commit `ea85b1d` under the original `## Procedure: task=reply (GitHub-side review-thread reply)` contract. This ACR-237 rewrite does not re-implement that primitive.

Dispatches with `task=reply` must defer to the ACR-236 shipped reply procedure and its terminal verdict vocabulary. `task=review` must not post replies, must not mutate review comments, and must not write `CODERABBIT_reply-<comment_id>.md`.

## Adapter declarations

```yaml
adapter_declarations:
  - component: agents/coderabbit-operator.md
    role: adapter
    Translates:
      - github-pr-contract
      - github-pr-reviews-contract
      - github-issue-labels-contract
      - github-check-runs-contract
      - pr-writer-output-contract
```

## Subordination notes

- **`gh` CLI invocations**: the `gh` CLI is the implementation mechanism for the declared GitHub contract surfaces. Every `gh` invocation in the operator, such as `gh pr create`, `gh pr view`, `gh pr ready`, `gh api -X POST /repos/.../issues/{n}/labels`, `gh api .../pulls/{n}/comments`, `gh api .../commits/{sha}/check-runs`, `gh label list`, and `gh label create`, is a documented operation of one of the GitHub `Translates:` contracts. `gh` is not a separate contract surface; it is the CLI tool used to access those contracts.
- **`gh` auth/control precondition**: `gh` authentication and repo access are the precondition for invoking all five declared contracts: `github-pr-contract`, `github-pr-reviews-contract`, `github-issue-labels-contract`, `github-check-runs-contract`, and `pr-writer-output-contract`. Every API call those contracts imply requires authenticated repo access, including PR lookup/create, review/comment reads, label list/create/apply, check-run reads, and PR creation from `pr-writer` output.
- **`pr-writer-output-contract`**: the stable contract that `~/ai/agents/pr-writer.md` produces, consisting of PR title file path and PR body file path. The operator consumes these via title/body arguments to `gh pr create`. The operator does not own `pr-writer`'s internal contract; it owns the documented consumption surface.
- **Issue timeline/events**: timeline-event polling is subordinate to `github-pr-reviews-contract`. Timeline events on PR issues include CodeRabbit submission and comment events that corroborate review completion; the operator reads them only as part of detecting whether CodeRabbit review/comment completion occurred.

## Intrinsic-surface declarations

```yaml
intrinsic_surface_declarations:
  - component: agents/coderabbit-operator.md
    role: intrinsic-surface
    Domain: coderabbit-operator-output-artifacts
    Owns:
      - CODERABBIT_pass<N>.md
      - CODERABBIT_summary.md
      - audit_history_path (operator-append surface)
```
