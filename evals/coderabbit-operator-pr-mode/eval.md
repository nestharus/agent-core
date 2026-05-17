# CodeRabbit Operator PR-mode Eval

## Identity

This WRITE-state eval specifies the behavior contract for `agents/coderabbit-operator.md` when dispatched as `task=review`. It asserts the GitHub-only PR-mode CodeRabbit review path: PR discovery or creation, label-trigger setup, bounded GitHub polling, completion or timeout classification, normalized `CODERABBIT_pass<N>.md` output, and final `CODERABBIT_summary.md` output.

This file is a reviewable behavior specification. It is not executable, has no detector implementation, and does not perform live GitHub or CodeRabbit operations.

## Declared roles

mapper, validator, formatter

Role mapping: mapper binds observed GitHub PR, review, issue-comment, review-thread-comment, label, timeline, and check-run evidence to scenario assertions. Validator defines the forbidden behaviors, blocked verdicts, convergence verdicts, and non-fire boundaries. Formatter defines the required pass, summary, finding, and trace-field shapes.

## Unwanted behavior

The eval fires when the operator's `task=review` contract drifts into any of these behaviors:

- Using CodeRabbit CLI mode or the retired local amend-loop review procedure.
- Requiring a CodeRabbit-side credential, dashboard bearer token, dashboard API route, or `CODERABBIT_API_KEY`.
- Using an idle-timeout loop instead of finite 5-minute polling cadence bounded by `max_attempts`.
- Using the PR-edit label path that ACR-225 showed can fail on classic-projects repositories, rather than the GitHub REST issue-label application path.
- Treating absence of CodeRabbit evidence before the polling cap as zero findings.
- Treating absence of CodeRabbit evidence at the polling cap as a clean completed review instead of `CONVERGED:coderabbit-timeout-no-completion-signal`.
- Normalizing CodeRabbit-attributed GitHub evidence without author, timestamp, PR identity, head SHA, or review/comment identity.
- Posting replies, owning `CODERABBIT_reply-<comment_id>.md`, or mutating review comments from `task=review`.
- Leaving the disabled tombstone as the active dispatch result for `task=review`.

## Positive evidence

The operator satisfies this eval when `task=review` produces observable evidence for:

- Explicit dispatch validation and terminal verdicts from the ACR-237 stop-condition set.
- Branch and GitHub-auth prechecks before PR creation, label application, or polling.
- PR reuse when an open PR exists, or `pr-writer`-backed PR creation when it does not.
- GitHub REST issue-label trigger evidence, including label existence, creation result when applicable, and label-apply result.
- Finite 5-minute polling attempts bounded by `max_attempts`, with captured PR reviews, issue comments, PR review-thread comments, labels/status rollup, optional issue timeline events, and check-runs for the head SHA.
- Completed-review convergence as `CONVERGED:review-complete-pass<N>` when a qualifying CodeRabbit review or accepted contemporaneous CodeRabbit issue-comment signal appears.
- Timeout convergence as `CONVERGED:coderabbit-timeout-no-completion-signal` when the polling cap is reached without a qualifying signal.
- Blocked terminal verdicts when prechecks, label setup/application, PR writer/creation, GitHub reads, or review-shape normalization cannot be trusted.
- Normalized `CODERABBIT_pass<N>.md` and `CODERABBIT_summary.md` artifacts with the fields listed in `## Artifact contract`.

## Non-fire cases

The eval must not fire on these cases:

- A bounded timeout after successful label application and no CodeRabbit completion signal, when the operator emits `CONVERGED:coderabbit-timeout-no-completion-signal` and records timeout evidence.
- A completed CodeRabbit review with zero actionable inline findings, when a qualifying completion signal exists and artifacts explicitly mark zero actionable findings.
- Empty check-runs for the head SHA, when completion is proven by PR review or issue-comment evidence.
- Empty PR review-thread comments, when completion is proven by a qualifying CodeRabbit PR review or issue-comment signal.
- Optional corroborating issue timeline evidence being absent, as long as required PR review, issue-comment, review-thread-comment, label/status, and check-run reads are handled according to the fetch contract.
- A shipped `task=reply` section being preserved or referenced as a separate task, provided `task=review` does not perform reply mutation.
- A historical note about the disabled tombstone or CLI mode, provided it is not active procedure text and cannot be the terminal result for `task=review`.

## Required trace fields

Any future detector or audit consuming this eval must be able to identify these trace fields from operator output, artifacts, dispatch logs, or saved run evidence:

- `task`: expected value `review`.
- PR identity: PR URL, PR number, repo, branch, base, and draft state when relevant.
- Local and remote branch evidence: local head SHA, remote head SHA, and pushed/stale determination.
- GitHub auth evidence: whether authenticated GitHub access to the target repo was available.
- `pr-writer` evidence when no open PR exists: title/body artifact references or failure reason.
- Label trigger evidence: label existence check, label creation result when applicable, REST issue-label apply result, HTTP status or API outcome shape when available, trigger timestamp, and poll baseline.
- Poll contract evidence: `max_attempts`, 5-minute cadence, attempt count, and per-attempt fetch summary.
- Fetch evidence summary: PR reviews/comments from PR state, PR-as-issue comments with author login and creation timestamp, PR review-thread comments with database ID, GraphQL node ID when available, path, line or original line, body, and author login, labels/status rollup, optional issue timeline events, and head-SHA check-runs with name/status/conclusion fields when available.
- Completion signal: source type, author attribution, review/comment IDs when available, review state, observed timestamp, and whether the signal is newer than the PR create or redispatch baseline. The primary completion signal is a non-pending `coderabbitai` PR review newer than that baseline; the accepted secondary signal is a contemporaneous `coderabbitai[bot]` PR-as-issue comment.
- Finding counts: total findings, actionable findings, zero-actionable marker when applicable, latest-pass counts, and aggregate counts.
- Terminal verdict and convergence or blocked reason.
- Artifact references: every `CODERABBIT_pass<N>.md` produced and final `CODERABBIT_summary.md`.

## Finding shape

Each normalized finding in `CODERABBIT_pass<N>.md` must include:

- Review-thread comment database ID.
- GraphQL node ID when available.
- File path.
- Line or original line.
- Severity if available.
- Body.
- Attribution: `coderabbitai` or `coderabbitai[bot]`.
- Source timestamp.

Findings are normalized from CodeRabbit-attributed PR review-thread comments. The expected source shape is a GitHub pull-request review comment carrying a stable database ID, an optional GraphQL node ID, file path, positional line data, body text, `user.login`, and creation or update timestamp. Missing optional severity is acceptable only when the finding still records that severity was unavailable.

When no actionable findings exist after a valid completion signal, the finding list may be empty only if the artifact records total findings `0`, actionable findings `0`, and an explicit zero-actionable marker.

## Suggested action

When a scenario fires, the implementing operator should be revised before use. The revision should either produce the expected terminal verdict and artifact evidence or deliberately document a new contract through the planning process before changing this eval.

For blocked scenarios, preserve the blocked reason in `CODERABBIT_summary.md` whenever the worktree is writable. For convergence scenarios, preserve enough evidence in `CODERABBIT_pass<N>.md` and `CODERABBIT_summary.md` for later PR-review and audit-history consumers to distinguish completed review, zero-actionable completion, and timeout convergence.

## Lifecycle notes

This eval is in WRITE state. It should be reread after any rewrite of `agents/coderabbit-operator.md`, after changes to GitHub PR/review/label fetch contracts, after changes to `pr-writer` output consumption, and before any future ticket attempts to restore automatic CodeRabbit dispatch in implementation-pipeline Phase 7.

Runnable detector code, fixtures, pytest tests, structural-markdown assertions, scheduler wiring, and live API probes are outside this eval. Later lifecycle promotion must keep this markdown file as the behavior contract and add implementation artifacts only through a separate eval-runtime ticket.

## Fixture source baseline

The eval is a WRITE-state behavior specification: it must stand alone without requiring consumers to know the author's filesystem layout. Fixture sources cite by stable identifier (ticket ID + conceptual descriptor) and by GitHub public docs URL. The evidence shape that grounds each scenario is distilled into this eval text, not pulled from machine-local path citations.

Predecessor empirical evidence from the ACR-225 PR-mode clarification prototype:

- **ACR-225 label-trigger probe**: established that the `coderabbit` PR label is the GitHub-only trigger primitive; that `gh pr edit --add-label coderabbit` can fail on classic-projects-deprecated repositories; that `gh api -X POST /repos/{owner}/{repo}/issues/{n}/labels -f labels[]=coderabbit` is the supported REST primitive; and that missing labels can be created with `gh label create coderabbit --repo {owner}/{repo}`.
- **ACR-225 PR-state probe**: established the PR state shape returned by `gh pr view --json reviews,comments,labels,statusCheckRollup`; this eval requires PR number, head SHA, label list, review list with author/state/submittedAt, and comment list with author/createdAt.
- **ACR-225 issue-comment probe**: established the PR-as-issue comment shape returned by `gh api /repos/{owner}/{repo}/issues/{n}/comments`; this eval uses author login, body, and created_at for `coderabbitai[bot]` walkthrough detection.
- **ACR-225 review-comment probe**: established the PR review-thread comment shape returned by `gh api /repos/{owner}/{repo}/pulls/{n}/comments`; this eval uses database ID, GraphQL node ID when available, path, line/original line, body, user.login, and timestamp.
- **ACR-225 timeline probe**: established the issue-timeline event shape returned by `gh api /repos/{owner}/{repo}/issues/{n}/timeline`; this eval treats timeline events as optional corroborating evidence subordinate to PR review and comment evidence.
- **ACR-225 check-runs probe**: established the check-runs shape returned by `gh api /repos/{owner}/{repo}/commits/{sha}/check-runs`; this eval records check-run name/status/conclusion evidence alongside review state when available.
- **ACR-225 completion-signal vector**: established that the primary signal is a `coderabbitai` PR review with `submittedAt` newer than the PR create or redispatch baseline; that the secondary signal is a contemporaneous `coderabbitai[bot]` issue comment; and that `gh pr view --json timelineItems` is unsupported and must not be used.
- **ACR-225 polling-cadence vector**: established that bounded polling at 5-minute cadence times finite `max_attempts` reaches `CONVERGED:coderabbit-timeout-no-completion-signal` when no signal arrives; absence at the cap is timeout convergence, not a zero-finding review.
- **ACR-225 API-credential vector**: established that no `CODERABBIT_API_KEY`, dashboard bearer token, or CodeRabbit-side credential is required; the credential surface is GitHub-only through authenticated `gh`.

Stable GitHub contract surfaces:

- `https://docs.github.com/en/rest/issues/labels`
- `https://docs.github.com/en/rest/pulls/comments`
- `https://docs.github.com/en/rest/issues/timeline`
- `https://docs.github.com/en/rest/checks/runs`
- `https://docs.github.com/en/rest/pulls/pulls`

ACR-237 specification references are cited by ticket ID plus section name, for example ACR-237 `## Operator-file structural sketch`, ACR-237 `## Stop Conditions`, and ACR-237 `## Output Contract`. This eval's `## Artifact contract` section duplicates the required artifact schema in full so future readers can use this file as the sole behavior spec.

## Scenario: PR discovery and pr-writer dependency

selected level: operator behavior spec

fixture source: ACR-237 `## Operator-file structural sketch`; ACR-237 `## Required Inputs`; ACR-237 `## Stop Conditions`; `https://docs.github.com/en/rest/pulls/pulls`

fixture application point: Apply to `task=review` dispatches that provide branch/repo identity with either an existing open PR or no open PR.

expected observable signal: If no open PR exists and `pr-writer` fails, terminal verdict is `BLOCKED:pr-writer-failed`; if PR creation fails after usable writer output, terminal verdict is `BLOCKED:pr-create-failed`; successful PR reuse or creation is reflected in `CODERABBIT_pass<N>.md` with PR URL, PR number, and trigger evidence, leading later to `CONVERGED:review-complete-pass<N>` or `CONVERGED:coderabbit-timeout-no-completion-signal`.

notes: The operator must not synthesize PR title/body itself when `pr-writer` is the declared dependency.

## Scenario: Branch and GitHub auth prechecks

selected level: operator behavior spec

fixture source: ACR-237 `## Preconditions`; ACR-237 `## Stop Conditions`; ACR-225 PR-state probe; ACR-225 API-credential vector; `https://docs.github.com/en/rest/pulls/pulls`

fixture application point: Apply before PR lookup/creation, label setup, label application, or polling.

expected observable signal: Stale or unpushed branch evidence terminates with `BLOCKED:branch-not-pushed`; unavailable or unreadable GitHub auth terminates with `BLOCKED:gh-auth-unavailable`; `CODERABBIT_summary.md` records the blocked reason when writable.

notes: These are preconditions, not poll-time failures.

## Scenario: Label missing and not creatable

selected level: operator behavior spec

fixture source: ACR-225 label-trigger probe; ACR-237 `## Preconditions`; ACR-237 `## Stop Conditions`; `https://docs.github.com/en/rest/issues/labels`

fixture application point: Apply when the repo lacks the `coderabbit` label and the documented label creation helper cannot create it.

expected observable signal: Terminal verdict is `BLOCKED:gh-label-create-failed`; `CODERABBIT_summary.md` records the label existence check and label creation failure.

notes: A missing label by itself is not a failure if creation succeeds.

## Scenario: REST-only label trigger

selected level: operator behavior spec

fixture source: ACR-225 label-trigger probe; ACR-237 `## Procedure`; ACR-237 `## Adapter declarations`; `https://docs.github.com/en/rest/issues/labels`

fixture application point: Apply at the PR trigger step after PR identity and label readiness are established.

expected observable signal: `CODERABBIT_pass<N>.md` trigger evidence names GitHub REST issue-label application; label application failure terminates as `BLOCKED:gh-label-apply-failed`; a PR-edit label primitive is non-compliant even if later polling would have reached `CONVERGED:review-complete-pass<N>`.

notes: This scenario carries the ACR-225 classic-projects failure evidence into the rewrite contract.

## Scenario: Bounded GitHub polling contract

selected level: operator behavior spec

fixture source: ACR-225 completion-signal vector; ACR-225 polling-cadence vector; ACR-225 PR-state probe; ACR-225 issue-comment probe; ACR-225 review-comment probe; ACR-225 timeline probe; ACR-225 check-runs probe; ACR-237 `## Completion detection`; ACR-237 `## Adapter declarations`; `https://docs.github.com/en/rest/pulls/comments`; `https://docs.github.com/en/rest/issues/timeline`; `https://docs.github.com/en/rest/checks/runs`

fixture application point: Apply after trigger evidence establishes a poll baseline and before completion, timeout, or blocked classification.

expected observable signal: Polling is bounded by finite `max_attempts` at 5-minute cadence, with no idle-timeout rule; required fetch evidence is summarized in `CODERABBIT_pass<N>.md` as PR reviews/comments, PR review-thread comments, optional timeline corroboration, labels/status rollup, and head-SHA check-runs; unavailable GitHub reads terminate as `BLOCKED:review-fetch-failed`; unsafe or unsupported response shape terminates as `BLOCKED:invalid-review-shape`; successful polling may later terminate as `CONVERGED:review-complete-pass<N>` or `CONVERGED:coderabbit-timeout-no-completion-signal`.

notes: Timeline evidence is optional corroboration and must not be modeled as an unsupported PR-view field.

## Scenario: Timeout without completion signal

selected level: operator behavior spec

fixture source: ACR-225 completion-signal vector; ACR-225 polling-cadence vector; ACR-237 `## Completion detection`; ACR-237 `## Stop Conditions`

fixture application point: Apply when the `coderabbit` label was applied but no qualifying CodeRabbit review, issue-comment, or review-thread completion signal appears by the polling cap.

expected observable signal: Terminal verdict is `CONVERGED:coderabbit-timeout-no-completion-signal`; artifacts record timeout evidence and do not normalize absence as zero findings or `CONVERGED:review-complete-pass<N>`.

notes: Timeout convergence means the operator loop completed, not that CodeRabbit reviewed the PR cleanly.

## Scenario: Review-complete convergence

selected level: operator behavior spec

fixture source: ACR-225 label-trigger probe; ACR-225 PR-state probe; ACR-225 issue-comment probe; ACR-225 review-comment probe; ACR-225 completion-signal vector; ACR-237 `## Completion detection`; `https://docs.github.com/en/rest/pulls/pulls`; `https://docs.github.com/en/rest/pulls/comments`

fixture application point: Apply when a non-pending `coderabbitai` PR review appears after the PR create or redispatch baseline, with optional contemporaneous `coderabbitai[bot]` issue-comment evidence.

expected observable signal: Terminal verdict is `CONVERGED:review-complete-pass<N>`; `CODERABBIT_pass<N>.md` records completion signal source, author attribution, review/comment IDs when available, head SHA, finding counts, convergence reason, and terminal verdict.

notes: The primary signal is a qualifying PR review; issue-comment evidence may corroborate the result or serve as accepted secondary evidence per the operator contract.

## Scenario: Zero-actionable completed review

selected level: operator behavior spec

fixture source: ACR-225 label-trigger probe; ACR-225 PR-state probe; ACR-225 review-comment probe; ACR-225 issue-comment probe; ACR-225 check-runs probe; ACR-225 completion-signal vector; ACR-237 `## Output Contract`

fixture application point: Apply when a valid CodeRabbit completion signal exists but the review body, inline review-thread comments, and check-runs contain no actionable findings.

expected observable signal: Terminal verdict is `CONVERGED:review-complete-pass<N>`; normalized artifacts record total findings `0`, actionable findings `0`, and an explicit zero-actionable marker; the state is not treated as pending and not converted to `CONVERGED:coderabbit-timeout-no-completion-signal`.

notes: Empty check-runs are non-fire evidence when completion is otherwise proven.

## Scenario: Idempotent re-dispatch

selected level: operator behavior spec

fixture source: ACR-237 `## Required Inputs`; ACR-237 `## Procedure`; ACR-237 `## Output Contract`; ACR-225 label-trigger probe; `https://docs.github.com/en/rest/issues/labels`; `https://docs.github.com/en/rest/pulls/pulls`

fixture application point: Apply when an existing open PR, existing `coderabbit` label, prior `CODERABBIT_pass<N>.md` and/or audit-history evidence, and newer CodeRabbit events are present.

expected observable signal: The operator reuses the open PR, treats an already-present label as non-failure, polls for events newer than the prior pass baseline, bumps the pass number, writes `CODERABBIT_pass<N+1>.md`, and terminates with `CONVERGED:review-complete-pass<N+1>` or `CONVERGED:coderabbit-timeout-no-completion-signal`; it does not perform reply work.

notes: The exact pass-number source may combine existing pass artifacts and audit-history evidence, but duplicate pass overwrite is non-compliant.

## Scenario: GitHub fetch and shape failures

selected level: operator behavior spec

fixture source: ACR-237 `## Procedure`; ACR-237 `## Completion detection`; ACR-237 `## Stop Conditions`; ACR-225 PR-state probe; ACR-225 issue-comment probe; ACR-225 review-comment probe; ACR-225 timeline probe; ACR-225 check-runs probe; `https://docs.github.com/en/rest/pulls/pulls`; `https://docs.github.com/en/rest/pulls/comments`; `https://docs.github.com/en/rest/issues/timeline`; `https://docs.github.com/en/rest/checks/runs`

fixture application point: Apply during poll reads, completion detection, and finding normalization when required reads fail or returned CodeRabbit-attributed objects cannot be safely normalized.

expected observable signal: Unavailable required reads terminate as `BLOCKED:review-fetch-failed`; unsafe or malformed CodeRabbit-attributed review/comment shape terminates as `BLOCKED:invalid-review-shape`; `CODERABBIT_summary.md` records the blocked reason when writable.

notes: Missing optional fields are not automatically invalid if the artifact can still satisfy the schema with explicit unavailable markers.

## Scenario: Reply task boundary

selected level: assertion-only

fixture source: ACR-237 `## task=reply`; ACR-237 `## Do Not Use When`; ACR-237 `## Anti-scope`; ACR-225 API-credential vector

fixture application point: Apply to the operator text and artifacts for `task=review`, and to the neighboring `task=reply` boundary after ACR-236 shipped.

expected observable signal: `task=review` does not post replies, does not mutate review comments, and does not own `CODERABBIT_reply-<comment_id>.md`; the operator preserves or references the shipped ACR-236 `task=reply` contract; review-mode terminal verdict remains one of `CONVERGED:review-complete-pass<N>`, `CONVERGED:coderabbit-timeout-no-completion-signal`, or a documented `BLOCKED:*`/`NEEDS_INPUT:<question_artifact_path>` stop condition.

notes: Live reply correctness remains outside ACR-237 and belongs to ACR-236.

## Scenario: Tombstone supersession

selected level: assertion-only

fixture source: ACR-237 `## Operator-file structural sketch`; ACR-237 `## Stop Conditions`; ACR-237 `## Preconditions`; ACR-225 label-trigger probe

fixture application point: Apply to post-rewrite `agents/coderabbit-operator.md` text.

expected observable signal: The active disabled short-circuit is removed or superseded; `CONVERGED:disabled-no-credits-2026-05-15` is not an active `task=review` result; ACR-235 Preconditions substance is preserved; valid review-mode dispatches proceed toward `CONVERGED:review-complete-pass<N>`, `CONVERGED:coderabbit-timeout-no-completion-signal`, or the documented blocked verdicts.

notes: Callers depending on the tombstone are intentionally moved to the new PR-mode contract.

## Scenario: GitHub-only credentials

selected level: assertion-only

fixture source: ACR-225 API-credential vector; ACR-237 `## Preconditions`; ACR-237 `## Anti-scope`; ACR-237 `## Stop Conditions`

fixture application point: Apply to operator preconditions, procedure, and blocked-verdict mapping.

expected observable signal: The active contract has no `CODERABBIT_API_KEY`, CodeRabbit dashboard bearer token, CodeRabbit API dependency, or CodeRabbit CLI review path; unavailable GitHub auth maps to `BLOCKED:gh-auth-unavailable`; successful GitHub label application with no CodeRabbit response can only converge as `CONVERGED:coderabbit-timeout-no-completion-signal`.

notes: CodeRabbit dashboard and repo eligibility remain user-owned setup and are not proven by the operator.

## Artifact contract

selected level: n/a

fixture source: ACR-237 `## Artifact schemas`; ACR-237 `## Output Contract`; ACR-225 PR-state probe; ACR-225 issue-comment probe; ACR-225 review-comment probe; ACR-225 check-runs probe; `https://docs.github.com/en/rest/pulls/pulls`; `https://docs.github.com/en/rest/pulls/comments`; `https://docs.github.com/en/rest/checks/runs`

fixture application point: Apply to every completed, timeout, and blocked `task=review` run that can write artifacts.

expected observable signal: `CODERABBIT_pass<N>.md` and `CODERABBIT_summary.md` contain every schema field listed below; blocked runs record blocked reason when writable; completed and timeout runs record the relevant terminal verdicts.

`CODERABBIT_pass<N>.md` required fields:

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

`CODERABBIT_summary.md` required fields:

- PR URL and PR number.
- Head SHA.
- Latest pass number and total CodeRabbit passes observed by this operator invocation.
- Completion signal or timeout evidence.
- Finding counts by latest pass and aggregate.
- Convergence reason.
- Terminal verdict.
- Artifact references to `CODERABBIT_pass<N>.md` files.
- Blocked reason when terminal is `BLOCKED:*`.
