---
description: 'Thin wrapper for the GitHub PR-mode CodeRabbit review loop in tools/coderabbit_review_driver.py.'
model: gpt-medium
output_format: ''
---

# CodeRabbit Operator

This operator delegates CodeRabbit PR-mode review to
`~/ai/tools/coderabbit_review_driver.py review-loop`. The driver owns
triggering, trigger-ack polling, 5-minute review polling cadence, GitHub
review-state interpretation, comment persistence, per-comment fixer dispatch,
outcome aggregation, branch push, reply posting, incremental re-triggering,
and terminal-state JSON.

The repository-level `coderabbit` label is only an installation marker;
applying it to a PR suppresses CodeRabbit and is never a trigger path.

Declared roles: `orchestration`, `adapter`.

## Use When

- Use only when a caller needs an LLM wrapper around the script for one PR.
- Prefer direct script calls from orchestrators and workflows.

## Required Inputs

- `repo`: GitHub repo in `owner/name` form.
- `pr_num`: GitHub pull request number.
- `worktree_path`: absolute path to the PR head-branch worktree.
- `trigger_mode`: optional; `incremental` by default, `full` only for
  code-audit or mass-cleanup callers whose review target is whole files rather
  than the latest diff.
- `initial_trigger`: optional; `auto` by default. Use `skip` only when the
  caller has just triggered CodeRabbit and wants the loop to begin at polling.
- `fixer_agent`: optional; defaults to
  `~/ai/agents/coderabbit-comment-fixer.md`.

## Procedure

1. For enablement-only diagnostics, run:
   ```bash
   ~/ai/tools/coderabbit_review_driver.py is-enabled {repo}
   ```
   Exit `0` means the repo has the CodeRabbit marker label and CodeRabbit is
   available. Exit `1` means skip CodeRabbit for this repo.
2. For the normal loop, run:
   ```bash
   ~/ai/tools/coderabbit_review_driver.py review-loop {repo} {pr_num} \
     --worktree-path {worktree_path} \
     --mode incremental
   ```
   The driver returns one final JSON object. It exits `0` for terminal loop
   states and exits `3` when a per-comment fixer produced a caller-decision
   outcome that must be surfaced.
3. Use full mode only when the caller's review target is whole files, not the
   latest diff:
   ```bash
   ~/ai/tools/coderabbit_review_driver.py review-loop {repo} {pr_num} \
     --worktree-path {worktree_path} \
     --mode full
   ```
4. The primitive `trigger`, `poll`, and `reply` subcommands remain available
   for diagnostics and repair, but orchestrators must not compose their own
   review loops from those primitives.

## Driver Loop Contract

The loop:

- auto-skips the initial trigger when a matching CodeRabbit trigger ack is
  newer than the latest CodeRabbit review; otherwise it triggers the selected
  mode and waits for ack.
- waits at least 300 seconds between successive loop-owned `poll` calls for
  the same PR.
- treats `APPROVED` as terminal with `terminal_reason: "approved"`.
- dispatches one fixer invocation per actionable in-diff comment, with a
  resolved prompt written under
  `~/.cache/coderabbit/{owner}/{repo}/pr-{num}/iter-{n}/`.
- honors frontmatter-declared fixer models by invoking agent files with
  `agents -a <agent-file> -p <worktree> -f <prompt>` and no `-m` override.
- aggregates the full per-comment structured outcome, pushes fixed commits,
  posts reply files, triggers an incremental review, and loops again.
- stops with `terminal_reason: "no_value_provided"` when every actionable
  in-diff comment in the iteration is assessed
  `review_provided_value: false`.

## Per-Comment Outcome Shape

Each fixer writes:

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

- `CONVERGED:coderabbit-approved` when final JSON has
  `terminal_reason=approved`.
- `CONVERGED:coderabbit-no-value-provided` when final JSON has
  `terminal_reason=no_value_provided`.
- `PENDING:coderabbit-caller-decision` when the driver exits `3` and the JSON
  has `needs_caller_decision=true`.
- `BLOCKED:coderabbit-script-failed` when a script command exits nonzero other
  than `is-enabled` exit `1` or review-loop exit `3`.

## Anti-scope

- No inline GitHub polling logic.
- No PR label mutation.
- No `gh pr view ... statusCheckRollup` calls.
- No CodeRabbit CLI mode.
- No CodeRabbit dashboard credential.
- No timeout, attempt ceiling, idle-timeout, bounded-silence, count-bound, or
  silence-as-success convergence.
- No comment-body fan-in to the orchestrator context.
