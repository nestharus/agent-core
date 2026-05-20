---
description: 'Thin wrapper for GitHub PR-mode CodeRabbit review through tools/coderabbit_review_driver.py.'
model: gpt-high
output_format: ''
---

# CodeRabbit Operator

This operator is intentionally thin. CodeRabbit trigger comments, trigger-ack
polling, GitHub review-state interpretation, comment persistence, reply
posting, and state tracking are owned by
`~/ai/tools/coderabbit_review_driver.py`. The repository-level `coderabbit`
label is only an installation marker; applying it to a PR suppresses
CodeRabbit and is never a trigger path.

Declared roles: `orchestration`, `adapter`.

## Use When

- Use only when a caller needs an LLM wrapper around the script for one PR.
- Prefer direct script calls from orchestrators and workflows.

## Required Inputs

- `repo`: GitHub repo in `owner/name` form.
- `pr_num`: GitHub pull request number.
- `mode`: one of `is-enabled`, `trigger`, `poll`, or `reply`.
- `trigger_mode`: optional for `mode=trigger`; `incremental` by default,
  `full` only for code-audit or mass-cleanup callers whose target is whole
  files rather than the latest diff.
- `body_file`: required only for `mode=reply`.
- `comment_id`: required only for `mode=reply`.

## Procedure

1. For enablement checks, run:
   ```bash
   ~/ai/tools/coderabbit_review_driver.py is-enabled {repo}
   ```
   Exit `0` means the repo has the CodeRabbit marker label and CodeRabbit is
   available. Exit `1` means skip CodeRabbit for this repo.
2. For review triggering, run:
   ```bash
   ~/ai/tools/coderabbit_review_driver.py trigger {repo} {pr_num} --mode incremental
   ```
   This posts `@coderabbitai review` and waits until the CodeRabbit bot posts
   the trigger acknowledgement. It does not return before the ack arrives.
3. Use full mode only when the caller's review target is whole files, not the
   latest diff:
   ```bash
   ~/ai/tools/coderabbit_review_driver.py trigger {repo} {pr_num} --mode full
   ```
   Full mode posts `@coderabbitai full review` and waits for the full-review
   acknowledgement. Normal implementation-pipeline PR review uses
   `incremental`, including re-runs after child fix commits.
4. For review state, run:
   ```bash
   ~/ai/tools/coderabbit_review_driver.py poll {repo} {pr_num}
   ```
   The script persists each CodeRabbit in-diff and out-of-diff comment under
   `~/.cache/coderabbit/{owner}/{repo}/pr-{num}/...` and returns JSON metadata
   with file paths. `APPROVED` and `CHANGES_REQUESTED` are terminal pass
   states. Only `APPROVED` is pipeline success; `CHANGES_REQUESTED` means fix
   the returned comments, push, trigger another incremental pass, and poll
   again.
5. For a reply, run:
   ```bash
   ~/ai/tools/coderabbit_review_driver.py reply {repo} {pr_num} {comment_id} {body_file}
   ```

## Comment Handling

When `poll` returns `new_comments`, dispatch one independent child agent per
`new_comments[i].file_path`. Each child receives exactly one file path and acts
on that one CodeRabbit item. Do not batch comment bodies into a single prompt.

Child dispatches must use non-interactive `agents -m <model> -f <prompt-file>`
shape. Do not run bare `agents`.

## Stop Conditions

- `CONVERGED:coderabbit-approved` when the script returns
  `review_decision=APPROVED`.
- `PENDING:coderabbit-changes-requested` when the script returns
  `review_decision=CHANGES_REQUESTED` and comments were dispatched for fixes.
- `PENDING:coderabbit-awaiting-review` when `terminal: false` and
  `new_comments` is empty.
- `PENDING:coderabbit-comments-dispatched` when `terminal: false` and
  `new_comments` were handed to child agents.
- `BLOCKED:coderabbit-script-failed` when a script command exits nonzero other
  than `is-enabled` exit `1`.

## Anti-scope

- No inline GitHub polling logic.
- No PR label mutation.
- No `gh pr view ... statusCheckRollup` calls.
- No CodeRabbit CLI mode.
- No CodeRabbit dashboard credential.
- No timeout, max-attempt, idle-timeout, bounded-silence, or silence-as-success
  convergence.
- No comment-body fan-in to the orchestrator context.
