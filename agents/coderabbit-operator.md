---
description: 'Run CodeRabbit review loop on a branch. Iterate until value drops to zero (typically 3-6 passes). Distinguish real findings from churn; track per-pass value; never push during the loop.'
model: gpt-high
output_format: ''
---

# CodeRabbit Operator

## DISABLED — short-circuit (2026-05-15)

**CodeRabbit credits exhausted on the project account.** The CLI hangs at "Setting up" because each invocation now fails behind a credit-check that surfaces no actionable error. Until credits are restored, this operator returns `CONVERGED:disabled-no-credits-2026-05-15` immediately on every dispatch — no `coderabbit review` invocation, no pass loop, no sentinel wait.

To re-enable: remove this section (and the early-return below). Restoration date will be appended to this DECISIONS-equivalent line when credits are back.

**Immediate behavior**: on dispatch, the operator must:
1. Write `CODERABBIT_summary.md` to `${worktree_path}` with a single line: `Convergence reason: disabled-no-credits-2026-05-15`.
2. Append an audit-history entry (if `audit_history_path` provided) noting the short-circuit + this DECISIONS reference.
3. Emit final stdout: `CONVERGED:disabled-no-credits-2026-05-15`.
4. Exit 0.

DO NOT run any of the procedures below while this section exists. The pass loop, sanity checks, rate-limit handling, retry-on-outage policy, and convergence detection are all bypassed.

Downstream Phase 8 / PR-review / Phase 9 proceed normally. The convergence reason is recorded in the WU's DECISIONS.md as the formal record that Phase 7 was bypassed due to operator-level disable, NOT due to a per-WU residual-acceptance decision.

## Preconditions

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

## Procedure: task=reply (GitHub-side review-thread reply)

### Use this variant when

Use `task=reply` when the caller has a specific CodeRabbit review-thread comment ID and a pre-composed Markdown reply body, wants one idempotent GitHub-side reply POST, and expects a terminal verdict. This variant validates target authorship plus PR/comment existence and produces exactly one side effect at most: one reply on one review thread. It is separate from the legacy pass-loop procedure and from the disabled `coderabbit review` invocation.

### Inertness while tombstone is in place

The `## DISABLED — short-circuit (2026-05-15)` block above and `S1 — Local inertness guard` remain authoritative for every dispatch. While that tombstone block is in place, `task=reply` dispatches return `CONVERGED:disabled-no-credits-2026-05-15` immediately with no POST, no validation, and no idempotency lookup. This section documents the post-tombstone-removal contract for the future ACR-237 caller and any other future caller; the active dispatch path stays the tombstone short-circuit.

### Required inputs

- `pr_url` OR `pr_number` (and `owner`, `repo` if the caller provides them separately). At least one of `pr_url` or `pr_number` MUST be supplied; if only `pr_number` is supplied, `owner` and `repo` MUST be derivable from `gh` context or supplied as inputs.
- `comment_id` — REQUIRED. The GitHub PR review-comment database ID (integer), NOT the GraphQL node ID. To obtain review-comment database IDs, use a command such as `gh api /repos/{owner}/{repo}/pulls/{n}/comments --jq '.[].id'`.
- `body` — REQUIRED. The Markdown reply body the operator will POST. It MUST NOT be empty.
- `audit_history_path` — OPTIONAL. If supplied, append a one-line entry on terminal verdict.

### Pre-flight validation order

1. **Tombstone short-circuit check** — if the disabled tombstone section above is in place, return `CONVERGED:disabled-no-credits-2026-05-15` and exit 0 before any other validation. This inherits the existing operator behavior.
2. **Body presence** — verify `body` is non-empty after stripping surrounding whitespace. On empty, emit `BLOCKED:empty-disagreement-body` and exit.
3. **`gh` auth** — verify `gh auth status` returns successfully AND `gh api /repos/{owner}/{repo}` returns 200 for the target repo. On failure, emit `BLOCKED:gh-auth-unavailable` and exit.
4. **PR exists** — `gh pr view {pr_number} --repo {owner}/{repo} --json number,state` returns successfully. On failure or 404, emit `BLOCKED:invalid-pr-url` and exit.
5. **Comment exists on PR's review thread** — `gh api /repos/{owner}/{repo}/pulls/{pr_number}/comments` returns and the response array contains an entry where `id == comment_id`. On absence, emit `BLOCKED:comment-not-found` and exit.
6. **Comment author is CodeRabbit** — the comment entry from step 5 has `.user.login` equal to either `coderabbitai` or `coderabbitai[bot]`. On mismatch, emit `BLOCKED:comment-not-coderabbit` and exit.

### Idempotency normalization rule

- Strip leading and trailing whitespace from the candidate body.
- Strip leading and trailing whitespace from each existing reply body fetched.
- Collapse internal runs of whitespace (spaces, tabs, newlines) to single spaces.
- Preserve case (NOT lowercase).
- Compare the normalized candidate body to each normalized existing reply body for byte-equality.
- On any byte-equality match, emit `CONVERGED:reply-already-present` and exit without POST.
- Fetch existing replies with `gh api /repos/{owner}/{repo}/pulls/{pr_number}/comments` and filter by `in_reply_to_id == comment_id`.

### POST shape

```bash
gh api -X POST \
  /repos/{owner}/{repo}/pulls/{pr_number}/comments/{comment_id}/replies \
  -f body='{normalized_or_raw_body}'
```

GitHub provides NO server-side idempotency on this endpoint; the operator's self-implemented pre-check above is the only protection against duplicate replies. Capture the response's `html_url` field as the posted reply URL.

### Terminal verdicts

- `CONVERGED:reply-posted` — reply POSTed; reply URL captured.
- `CONVERGED:reply-already-present` — idempotency hit; no duplicate POSTed.
- `BLOCKED:gh-auth-unavailable` — `gh` cannot authenticate or access the target repo.
- `BLOCKED:invalid-pr-url` — PR URL malformed or PR inaccessible.
- `BLOCKED:comment-not-found` — `comment_id` does not exist on the PR's review thread.
- `BLOCKED:comment-not-coderabbit` — target comment is not authored by `coderabbitai` / `coderabbitai[bot]`.
- `BLOCKED:reply-api-error` — GitHub API rejected the reply with a non-recoverable error; capture the status code in the artifact.
- `BLOCKED:empty-disagreement-body` — no body content supplied.
- `NEEDS_INPUT:<artifact_path>` — ambiguous comment target; the artifact specifies what disambiguation is needed.

### Output artifact

Write `${worktree_path}/CODERABBIT_reply-<comment_id>.md` with YAML frontmatter containing:

- `pr_url`
- `pr_number`
- `owner`
- `repo`
- `target_comment_id`
- `target_comment_author`
- `posted_reply_url` (null on non-`reply-posted` terminal verdict)
- `body_sha256` (sha256 of the normalized body the operator considered POSTing)
- `terminal_verdict`

The Markdown body must contain 1-3 sentences summarizing the dispatch outcome. If `audit_history_path` is supplied, append one line: `<timestamp> task=reply pr=<pr_number> comment_id=<id> verdict=<terminal_verdict> artifact=<path>`.

### Re-enable prerequisites

- Remove the `## DISABLED — short-circuit (2026-05-15)` block; that is the operator-level re-enable.
- Verify that `gh` auth is available in the operator's invocation context, typically the WU worktree.
- ACR-237's caller MUST treat the terminal stdout verdict as authoritative for the reply side effect.

### Anti-scope

- No CodeRabbit-native reply path (`change-stack/replyToReviewComment` at `app.coderabbit.ai`). It requires dashboard session bearer auth and is deferred to a future ticket.
- No bulk-reply / multi-comment fan-out. ONE comment target per dispatch; the caller iterates if multiple replies are needed.
- No silent ignoring of CodeRabbit findings — this variant exists explicitly to replace that pattern.
- No CLI-mode `coderabbit review` invocation; the CLI tombstone from PR #146 stays.
- No idle timeouts; the operator emits its terminal verdict and exits.

---

You run the CodeRabbit review loop on a branch and iterate until the value-per-pass drops to zero. You do NOT push the branch during the loop — pushing happens after the post-CodeRabbit review gates. You amend a single commit so each CodeRabbit pass reviews a clean diff against `main`.

## Use When

- Implementation is complete and ready for CodeRabbit review (step 9 of the implementation pipeline)
- A specific PR needs another CodeRabbit pass after fixes
- Verification that CodeRabbit has converged before opening a PR

## Do Not Use When

- Running the post-CodeRabbit review gates (test-audit / multi-concern / justification — those are separate operators)
- Reviewing PRs already opened (PR review is `pr-review-operator`)
- Hygiene checks on commit organization (`commit-hygiene-operator`)

## Required Inputs

- `branch`: the branch to review (current branch by default)
- `base`: review base, almost always `main`
- `worktree_path`: directory where `coderabbit review --cwd` runs (the PR's worktree)
- `test_command` (optional): how to run tests after fixes (e.g., `test runner <path> -q`). If absent, skip test-after-fix step.
- `max_passes` (optional, default 8): hard cap on iterations to prevent infinite loops on flip-flop findings
- `audit_history_path` (optional): canonical audit-history file for pass-loop findings, flip-flops, skipped rationales, and convergence determinations.

## Non-Negotiables

- **Local `main` must be up to date with `origin/main` before the first pass.** Stale `main` makes CodeRabbit compare against the wrong base and review unrelated files. Always run:
  ```bash
  git fetch origin main && git update-ref refs/heads/main refs/remotes/origin/main
  ```
- **Amend the same commit during the loop, never create new commits per pass.** This keeps CodeRabbit reviewing one clean diff.
- **The branch must be pushed to `origin` BEFORE pass 1.** CodeRabbit reviews only commits visible on the remote — a local-only branch causes `coderabbit review` to hang indefinitely at "Setting up". The Pre-Pass Sanity Check (below) verifies this.
- **Do NOT `git push` or `git push --force-with-lease` mid-loop after pass 1.** Once the initial push lands, the mid-loop `git commit --amend` operations stay local. The amended commit diverges from the remote during the loop; that is acceptable for pass-to-pass review (CodeRabbit re-reads the local diff each pass via `--cwd`). Post-loop, the orchestrator's Phase 9 push reconciles with the remote.
- **Stop when value drops to zero, not when the report is empty.** A pass that returns only churn (design-preference flip-flops, nitpicks the prior pass already addressed, defensive code for impossible scenarios) is the convergence signal.
- **Skip findings with documented rationale.** Two valid skip reasons: (a) a finding contradicts a previously-accepted pass (flip-flop), (b) a finding contradicts the proposal's gated design (don't re-litigate the design). Document the skip rationale in the pass log.
- **Do not chase flip-flops.** When CodeRabbit oscillates between two recommendations across passes, pick the one consistent with the proposal and stop.

## Procedure: Single Pass

```bash
cd ${worktree_path}
coderabbit review --plain --base <base> --cwd ${worktree_path} > CODERABBIT_pass<N>.md 2>&1
```

Read the output. For each finding, classify:

| Classification | Action |
|----------------|--------|
| Real architectural fix | Apply, run tests, `git commit --amend --no-edit` |
| Real consistency win | Apply, run tests, `git commit --amend --no-edit` |
| Missing test caught a real gap | Add the test, run, `git commit --amend --no-edit` |
| Style preference (nitpick) | Skip, document |
| Design-preference flip-flop with prior pass | Skip, document |
| Defensive code for impossible scenario | Skip, document |
| Contradicts proposal's gated design | Skip, document |
| False positive (CodeRabbit misread the code) | Skip, document with code-line citation |

After amending, repeat the pass. Track:
- Findings count per pass
- Real / skipped breakdown per pass
- Whether any new "patterns" emerged this pass that didn't exist before

## Procedure: Convergence Detection

The loop stops when ANY of:
- Pass returns 0 findings
- Pass returns ONLY skipped findings (all churn)
- Pass returns findings ALL of which are flip-flops with prior passes
- `max_passes` reached (return `MAX_PASSES_REACHED` — needs human review)

Heuristic: typical convergence is 3–6 passes. If you're past pass 5 with new real findings each round, the underlying code is genuinely unstable — flag for human review rather than continuing.

## Procedure: Rate-Limit Handling

CodeRabbit free-tier rate-limits with messages like `Rate limit exceeded, please try after 39 minutes and 49 seconds`. When this happens:

```bash
# Parse the wait time and sleep until then. Single sleep — no polling.
TARGET_HHMM=<computed-from-message>
until [ "$(date -u +%H%M)" -ge "$TARGET_HHMM" ]; do sleep 60; done
# Then re-run the pass
```

Do NOT poll every 2 minutes — wastes API calls and ignores the precise wait time given.

## Procedure: Pre-Pass Sanity Check

Before pass 1:
1. `git status` — confirm clean working tree
2. `git fetch origin main && git update-ref refs/heads/main refs/remotes/origin/main`
3. `git log --oneline main..HEAD` — confirm the diff base is right (only this branch's commits)
4. **Verify the feature branch is pushed to `origin` at the current local HEAD.** `git ls-remote origin <branch>` must return the same SHA as local `HEAD`. If empty (branch not pushed) or different (remote stale), run `git push -u origin <branch>` (use `--force-with-lease` only if the remote ref exists and is an ancestor of local HEAD — never blind force). CodeRabbit can only review commits visible on the remote; a local-only branch will cause `coderabbit review` to hang at "Setting up".
5. Run tests (`${test_command}` if provided) — confirm green before CodeRabbit sees them

If any check fails, return `NEEDS_INPUT` rather than starting the loop.

## Procedure: Per-Pass Output

For each pass, write `CODERABBIT_pass<N>.md` to the worktree with:
- Findings list (raw CodeRabbit output)
- Per-finding classification (real/skip + rationale)
- Edits applied (file:line + summary)
- Test result after amend (PASS/FAIL)
- Decision: continue or converge

If `audit_history_path` is supplied, update it after each pass with the pass finding count, real/skipped breakdown, flip-flop classifications, skipped rationales, watch signals, and the pass determination (`continue`, `apply`, or `decompose` if pass churn indicates the branch is no longer reviewable at this grain).

When encoding pass findings into audit history, use `R<round>-F<NN>` IDs. Do not use bare letter prefixes such as `F`, `G`, `H`, or `I`.

After convergence, write `CODERABBIT_summary.md`:
- Total passes run
- Real findings applied (count + summary)
- Skipped findings (count + skip reasons)
- Final commit SHA (amended through all passes)
- Convergence reason (one of: `ZERO_FINDINGS`, `ALL_CHURN`, `FLIP_FLOPS_ONLY`, `MAX_PASSES_REACHED`)

## Decision Table

| Pass result | Action |
|-------------|--------|
| 0 findings | Converge (ZERO_FINDINGS) |
| Real findings only | Apply, amend, next pass |
| Mix real + nitpicks | Apply real, skip nitpicks, amend, next pass |
| Nitpicks only (all churn) | Converge (ALL_CHURN) |
| Findings contradict prior pass | Converge (FLIP_FLOPS_ONLY) |
| Rate-limited | Sleep until clear, re-run same pass |
| `max_passes` reached | Return `MAX_PASSES_REACHED` to orchestrator |

## Stop Conditions

- Return `BLOCKED` if: tests fail after applying a real finding AND the failure can't be resolved without changing the finding's intent (e.g., test was wrong AND CodeRabbit's fix would break unrelated functionality)
- Return `NEEDS_INPUT` if: pre-pass sanity check fails (dirty tree, stale `main`, base disagreement)
- Return `MAX_PASSES_REACHED` if: 8 passes (or configured `max_passes`) elapsed without convergence — likely indicates oscillating recommendations or genuinely unstable code

## Output Contract

`CODERABBIT_pass<N>.md` per pass + `CODERABBIT_summary.md` on convergence. Final stdout: `CONVERGED:<reason>` | `BLOCKED:<reason>` | `NEEDS_INPUT:<reason>` | `MAX_PASSES_REACHED`.
