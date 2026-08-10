---
description: 'Thin wrapper for one generated CodeRabbit review, independent finding dialogues, and exact-current-head approval.'
model: gpt-medium
output_format: ''
---

# CodeRabbit Operator

This operator delegates CodeRabbit PR-mode review to
`~/ai/tools/coderabbit_review_driver.py review-loop`. The driver owns one trigger
generation baselines, exact-head review acceptance, authoritative rate-limit
and capacity evidence, normalized finding persistence, per-conversation fixer
dispatch, exact-comment replies, branch pushes, GraphQL thread resolution,
exact-current-head CodeRabbit approval, persisted PR completion, and final JSON.
It never requests a follow-up review after a completed review.

The repository-level `coderabbit` label is only an installation marker;
applying it to a PR suppresses CodeRabbit and is never a trigger path.

## Declared roles

- `orchestration`
- `parser`

## Use When

- Use only when a caller needs an LLM wrapper around the script for one PR.
- Prefer direct script calls from orchestrators and workflows.

## Required Inputs

- `repo`: GitHub repo in `owner/name` form.
- `pr_num`: GitHub pull request number.
- `worktree_path`: absolute path to the PR head-branch worktree.
- `trigger_mode`: optional; `incremental` by default, `full` only for a
  code-audit or mass-cleanup whose declared review target is whole files.
- `initial_trigger`: optional; `auto` by default. `skip` requires a persisted
  active generation; a completed generation remains authoritative after fixer
  pushes change the PR head. A persisted in-flight command is
  reconciled first; when observed, the returned generation records
  `supersession_deferred_reason=reconciled-inflight-trigger` and no duplicate
  command is posted.
- `fixer_agent`: optional; defaults to
  `~/ai/agents/coderabbit-comment-fixer.md`.

## Procedure

1. Check repository enablement:
   ```bash
   ~/ai/tools/coderabbit_review_driver.py is-enabled {repo}
   ```
   Exit `0` means enabled. Exit `1` is clean non-applicability.
2. Run the single review/application pass:
   ```bash
   ~/ai/tools/coderabbit_review_driver.py review-loop {repo} {pr_num} \
     --worktree-path {worktree_path} \
     --mode {trigger_mode} \
     --initial-trigger {initial_trigger} \
     --fixer-agent {fixer_agent}
   ```
3. Use `--mode full` only for a declared whole-file review target.
4. Use the generation-aware diagnostic commands when repairing a halted pass:
   ```bash
   ~/ai/tools/coderabbit_review_driver.py poll {repo} {pr_num}
   ~/ai/tools/coderabbit_review_driver.py capacity {repo} {pr_num}
   ~/ai/tools/coderabbit_review_driver.py open-findings {repo} {pr_num}
   ~/ai/tools/coderabbit_review_driver.py reply {repo} {pr_num} {comment_id} {body_file}
   ```
   `capacity --new-query` starts a new capacity-query generation after the
   provider's prior response or a bounded malformed/unavailable-response halt.
   It never derives capacity from elapsed time or a fair-usage table.
   A retry is permitted only when the prior request did not produce a review
   and authoritative capacity evidence allows it. A completed review is never
   superseded or requested again for the PR.

## Generation Contract

The driver snapshots CodeRabbit pull-request review IDs immediately before it
posts each review command. A generation is completed only by a CodeRabbit
pull-request review whose ID is outside that baseline and whose `commit_id`
equals the generation's `expected_head_oid`, with `submitted_at` no earlier
than the generation trigger.

The persisted generation object is written inside
`~/.cache/coderabbit/{owner}/{repo}/pr-{num}/state.json`. It contains:

- `schema`, `generation_id`, and exactly one `result` from
  `REVIEW_COMPLETED`, `RATE_LIMITED_NO_REVIEW`, `WAITING_FOR_REVIEW`, or
  `BLOCKED`;
- `baseline_review_ids`, `baseline_issue_comment_ids`, trigger comment ID,
  URL, timestamp, and mode;
- expected and current PR head OIDs;
- accepted review ID, state, commit ID, and submission timestamp when present;
- authoritative rate-limit comment and matching check identities when present;
- one exact active capacity-query generation, archived capacity-query history,
  and each bound response when present;
- `next_permitted_action`, `blocked_reason`, and `evidence_path`.

Starting a retry generation after a request that produced no review archives
the prior active generation in `review_generation_history`. A completed review
freezes the one generation and suppresses all later review requests even if the
branch head changes. It writes `single_review_completion` only after every
scoped conversation is resolved and CodeRabbit approves the exact final head.
Before each review-trigger or capacity-query POST, the driver persists an
in-flight command marker. After an interrupted POST it reconciles the exact
command body, timestamp, and pre-POST issue-comment baseline before continuing;
an ambiguous identity blocks instead of posting a duplicate. Explicit
`--new-query` capacity supersession archives an unobserved marker when provider
inspection confirms no identity. A PR-scoped non-blocking lock rejects a
concurrent provider-command invocation instead of allowing two POSTs.

Aggregate `reviewDecision`, summary comments, trigger acknowledgements,
completion acknowledgements, and a passing `Review rate limited` check cannot
produce `REVIEW_COMPLETED`; only the first exact trigger-bound pull-request
review completes the generation. Final PR completion separately requires an
exact CodeRabbit `APPROVED` review whose `commit_id` equals the current head.

## Rate Limits

- A CodeRabbit rate-limit PR comment outside the trigger's issue-comment
  baseline and no earlier than that trigger produces
  `RATE_LIMITED_NO_REVIEW`. The result binds the comment ID, URL, timestamp,
  trigger ID, expected head, and matching `Review rate limited` checks.
- A passing `Review rate limited` check without the bound comment remains
  `WAITING_FOR_REVIEW`.
- `capacity` posts `@coderabbitai rate limit` at most once per capacity-query
  generation and accepts exactly one newer CodeRabbit response outside that
  query's baseline. It persists the response ID, URL, body path, reported
  remaining capacity, retry guidance, and one-review-at-a-time status.
- Stale, ambiguous, or malformed responses produce `BLOCKED`; an unavailable
  response uses bounded backoff and then produces `BLOCKED`.
- The driver suppresses another review trigger while a request is outstanding,
  capacity is unavailable, one-review-at-a-time is active, the current
  generation is blocked, or `single_review_completion` exists. An authoritative
  `capacity_available=true` response permits a retry only when no review was
  completed.

## Open Findings

`open-findings` uses a read-only generation projection and returns unresolved
in-diff and outside-diff findings by default without rewriting poll deltas or
generation state. Every finding includes exact review and comment IDs, thread
ID when supported, URL, resolution state, persisted `body_path`, and a complete
ordered `conversation_path` for an in-diff review thread. In-diff
findings carry their provider review head; outside-diff findings use
`review_id=0` and `head_oid=null` because GitHub does not bind issue comments to
a pull-request review. Resolved findings, locally replied unchanged revisions
of outside-diff findings, and trigger/rate/capacity protocol comments are
excluded. An edited outside-diff comment reopens because the local disposition
is bound to the replied body hash and update timestamp.

## Exact Replies

`reply` verifies that the supplied comment ID exists on the specified PR and
was authored by CodeRabbit. Review comments use GitHub's exact review-comment
reply endpoint. Outside-diff issue comments use a top-level response that names
the exact source comment URL because GitHub exposes no issue-comment thread
endpoint. A missing review comment is never silently replaced by an unrelated
top-level comment. Exact duplicate replies are reused idempotently, and every
posted or reused result returns its read-back ID, URL, author, and parent ID
when supported. That readback is intermediate evidence only: the conversation
remains open until CodeRabbit responds and GitHub GraphQL reports the exact
thread `isResolved=true`.

## Conversation And Approval Gates

- Each root review comment is one independently tracked conversation. A
  separate fixer invocation receives only that thread's complete ordered
  history.
- After a fix push, the driver posts and reads back an exact-thread reply before
  the conversation becomes `awaiting_coderabbit`. A plain fix outcome gets a
  deterministic commit-and-rationale reply; a persisted action with a missing
  reply identity is recovered idempotently from its durable outcome artifact.
  It is not redispatched until CodeRabbit adds a newer reply or resolves the
  thread.
- A newer CodeRabbit reply on an unresolved thread is `pushback`; only that
  conversation is redispatched with its updated history. Multiple turns are
  allowed without creating another review generation.
- `isResolved=true` is the authoritative per-conversation completion signal.
  Outdated position, push, reply readback, body marker, or elapsed time cannot
  substitute for it.
- After all findings are resolved, the driver keeps polling until a CodeRabbit
  review with state `APPROVED` is bound to the exact current PR head OID.
- `single_review_completion` records resolved thread identities and the final
  approval review ID/state/commit only after both gates pass.

## Single-Review Contract

The pass:

- resumes a matching persisted generation or creates a new trigger generation;
- revalidates provider head identity before and after every poll;
- waits at least 300 seconds between loop-owned polls;
- dispatches one fixer per actionable conversation and preserves each
  structured outcome;
- pushes fixed commits, waits for provider head readback, posts exact replies,
  and then waits independently for each CodeRabbit response;
- continues a conversation after CodeRabbit pushback and never requests another
  review generation;
- succeeds only after every scoped finding is resolved and CodeRabbit approves
  the exact final head;
- persists `single_review_completion` with the reviewed head, final head,
  terminal result, and structured outcomes; later runs return this evidence
  without polling, dispatching, or triggering;
- surfaces `RATE_LIMITED_NO_REVIEW` as non-success after the bound capacity
  query reports no availability, and surfaces `BLOCKED` without retriggering.

## Per-Comment Outcome Shape

```json
{
  "comment_id": 0,
  "outcome": "fixed | replied | fixed_and_replied | deferred",
  "commit_sha": null,
  "reply_body_file": null,
  "rationale": "short text",
  "files_touched": []
}
```

The driver preserves this data in `iterations[].outcomes[]`; callers must not
collapse it into a boolean fixed/not-fixed result.

## Terminal States

- `COMPLETED:coderabbit-approved` requires
  `generation_result=REVIEW_COMPLETED`, `terminal_reason=approved`, no unresolved
  scoped findings, GraphQL-resolved review threads, and CodeRabbit `APPROVED`
  bound to the exact final head in persisted `single_review_completion`.
- `PENDING:coderabbit-rate-limited` is
  `generation_result=RATE_LIMITED_NO_REVIEW`; do not merge or re-trigger.
- `PENDING:coderabbit-caller-decision` is a driver exit `3` with
  `needs_caller_decision=true` after a `deferred` finding.
- `BLOCKED:coderabbit-generation` is `generation_result=BLOCKED`.
- `BLOCKED:coderabbit-script-failed` is any other unexpected nonzero exit.

## Anti-scope

- No inline GitHub polling or ad hoc review-loop composition.
- No PR label mutation.
- No aggregate `reviewDecision` or `statusCheckRollup` substitution for the
  exact bot-authored current-head approval review.
- No CodeRabbit CLI mode or dashboard credential.
- No inferred capacity, retry timestamp, or fair-usage-table calculation.
- No repeated trigger or capacity-query comments while authoritative evidence
  forbids them.
- No follow-up review request after `REVIEW_COMPLETED`, including after fixes,
  replies, later branch changes, or a rerun of the operator.
- No comment-body fan-in to the orchestrator context.
