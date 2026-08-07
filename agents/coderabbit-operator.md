---
description: 'Thin wrapper for the generation-aware GitHub PR-mode CodeRabbit review loop in tools/coderabbit_review_driver.py.'
model: gpt-medium
output_format: ''
---

# CodeRabbit Operator

This operator delegates CodeRabbit PR-mode review to
`~/ai/tools/coderabbit_review_driver.py review-loop`. The driver owns trigger
generation baselines, exact-head review acceptance, authoritative rate-limit
and capacity evidence, normalized finding persistence, per-comment fixer
dispatch, exact-comment replies, branch pushes, re-triggers, and final JSON.

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
- `initial_trigger`: optional; `auto` by default. `always` explicitly supersedes
  the active generation and forces a new one. `skip` requires a persisted active
  generation for the current PR head. A persisted in-flight command is always
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
2. Run the normal loop:
   ```bash
   ~/ai/tools/coderabbit_review_driver.py review-loop {repo} {pr_num} \
     --worktree-path {worktree_path} \
     --mode {trigger_mode} \
     --initial-trigger {initial_trigger} \
     --fixer-agent {fixer_agent}
   ```
3. Use `--mode full` only for a declared whole-file review target.
4. Use the generation-aware diagnostic commands when repairing a halted loop:
   ```bash
   ~/ai/tools/coderabbit_review_driver.py poll {repo} {pr_num}
   ~/ai/tools/coderabbit_review_driver.py capacity {repo} {pr_num}
   ~/ai/tools/coderabbit_review_driver.py open-findings {repo} {pr_num}
   ~/ai/tools/coderabbit_review_driver.py reply {repo} {pr_num} {comment_id} {body_file}
   ```
   `capacity --new-query` starts a new capacity-query generation after the
   provider's prior response or a bounded malformed/unavailable-response halt.
   It never derives capacity from elapsed time or a fair-usage table.
   After inspecting ambiguous rate-limit comments, use `review-loop
   --initial-trigger always` to archive the blocked generation and start a new
   one. This is the explicit repair route; normal trigger calls remain
   suppressed while the generation is blocked.

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

Starting a later trigger generation archives the prior active generation in
`review_generation_history`. Prior approvals remain historical evidence only.
They do not approve a new head or a rate-limited new-head generation.
Before each review-trigger or capacity-query POST, the driver persists an
in-flight command marker. After an interrupted POST it reconciles the exact
command body, timestamp, and pre-POST issue-comment baseline before continuing;
an ambiguous identity blocks instead of posting a duplicate. Explicit `always`
/ `--new-query` supersession archives an unobserved marker when provider
inspection confirms no identity. A PR-scoped non-blocking lock rejects a
concurrent provider-command invocation instead of allowing two POSTs.

Aggregate `reviewDecision`, summary comments, trigger acknowledgements,
completion acknowledgements, and a passing `Review rate limited` check are
informational only. None can produce `REVIEW_COMPLETED`. This permits
back-to-back `CHANGES_REQUESTED` reviews and unchanged-head re-triggers because
the new review ID, not a state transition, distinguishes generations.

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
  capacity is unavailable, one-review-at-a-time is active, or the current
  generation is blocked. Only an authoritative response with
  `capacity_available=true` permits another trigger.

## Open Findings

`open-findings` uses a read-only generation projection and returns unresolved
in-diff and outside-diff findings by default without rewriting poll deltas or
generation state. Every finding includes exact review and comment IDs, thread
ID when supported, URL, resolution state, and persisted `body_path`. In-diff
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
when supported.

## Driver Loop Contract

The loop:

- resumes a matching persisted generation or creates a new trigger generation;
- revalidates provider head identity before and after every poll;
- waits at least 300 seconds between loop-owned polls;
- dispatches each unresolved current-head in-diff comment ID at most once per
  run and preserves each structured fixer outcome;
- pushes fixed commits, waits for provider head readback, posts exact replies,
  and starts a new incremental generation, including unchanged-head re-triggers;
- stops successfully only after a `REVIEW_COMPLETED` generation whose accepted
  review state is `APPROVED`, or with the existing no-value convergence after
  processing findings from a completed generation;
- surfaces `RATE_LIMITED_NO_REVIEW` as non-success after the bound capacity
  query reports no availability, and surfaces `BLOCKED` without retriggering.

## Per-Comment Outcome Shape

```json
{
  "comment_id": 0,
  "outcome": "fixed | replied | fixed_and_replied | rejected | deferred",
  "commit_sha": null,
  "reply_body_file": null,
  "rationale": "short text",
  "files_touched": [],
  "review_provided_value": true
}
```

The driver preserves this data in `iterations[].outcomes[]`; callers must not
collapse it into a boolean fixed/not-fixed result.

## Terminal States

- `CONVERGED:coderabbit-approved` requires
  `generation_result=REVIEW_COMPLETED` and `terminal_reason=approved`.
- `CONVERGED:coderabbit-no-value-provided` requires findings from a
  `REVIEW_COMPLETED` generation, `terminal_reason=no_value_provided`, and every
  actionable in-diff comment in the latest iteration assessed
  `review_provided_value: false`.
- `PENDING:coderabbit-rate-limited` is
  `generation_result=RATE_LIMITED_NO_REVIEW`; do not merge or re-trigger.
- `PENDING:coderabbit-caller-decision` is a driver exit `3` with
  `needs_caller_decision=true`.
- `BLOCKED:coderabbit-generation` is `generation_result=BLOCKED`.
- `BLOCKED:coderabbit-script-failed` is any other unexpected nonzero exit.

## Anti-scope

- No inline GitHub polling or ad hoc review-loop composition.
- No PR label mutation.
- No aggregate `reviewDecision` or `statusCheckRollup` completion inference.
- No CodeRabbit CLI mode or dashboard credential.
- No inferred capacity, retry timestamp, or fair-usage-table calculation.
- No repeated trigger or capacity-query comments while authoritative evidence
  forbids them.
- No comment-body fan-in to the orchestrator context.
