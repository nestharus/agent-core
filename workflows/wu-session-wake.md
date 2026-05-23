---
workflow:
  id: wu-session-wake
workflow_dispatch_contract:
  orchestrator: "composition layer"
  inputs:
    - "sessions.index.json path"
    - "poller output from tools/pr-batch-poller"
    - "per-project worktree and planning roots"
  expectations:
    - "joins merged PR rows to one persisted WU session manifest"
    - "dispatches wu-session-resumer once per merged session"
    - "does not batch post-merge session work inside the poller or scheduler"
  outputs:
    - "one wu-session-resumer log per merged session"
  non_goals:
    - "does not implement the scheduler runtime"
    - "does not change pr-batch-poller schema"
    - "does not inline post-merge checks or spawn successor WUs"
---
# WU Session Wake

This workflow wires `~/ai/conventions/wu-session-lifecycle.md` Stage 5 through Stage 7 without merging scheduler, polling, and post-merge session closure into one binary.

## Procedure

1. Read the project session index at `${planning_root}/sessions.index.json`. Each row must name `ticket_id`, `branch`, `pr_url`, `draft_pr_head_sha`, `session_manifest_path`, `worktree_path`, `planning_dir`, and `pre_merge_main_sha` or an explicit source for it. Missing manifest path, branch, ticket id, PR URL, or pre-merge main SHA blocks dispatch for that row.
2. Run `~/ai/tools/pr-batch-poller/` for the indexed PRs. The poller returns PR status rows only; it does not read session manifests or dispatch agents.
3. For each row with `merged=true`, join the poller row to exactly one session-index row by PR URL and branch. Ambiguous, missing, or mismatched joins are blocking for that PR and must be reported as durable wake-composition evidence rather than guessed.
4. Compose `${planning_dir}/prompts/${ticket_id}-wu-session-resume.md` instructing `wu-session-resumer` to consume:
   - `pr_url` from the poller row
   - `merge_sha` from the poller row
   - `head_sha` from the poller row, matching manifest `draft_pr_head_sha`
   - `pre_merge_main_sha` from the session index or manifest
   - `branch_name` from `head_ref_name`
   - `ticket_id` from the session index
   - `session_manifest_path`
   - optional `test_command` and `coverage_command` only from explicit project policy or manifest values
5. Dispatch one resumer per merged session:

```bash
agents -a wu-session-resumer -p ${worktree_path} -f ${planning_dir}/prompts/${ticket_id}-wu-session-resume.md 2>&1 | tee ${planning_dir}/logs/${ticket_id}-wu-session-resume.log
```

6. Refuse to advance a row when the resumer returns `BLOCKED:` or `NEEDS_INPUT:`. Keep the prompt and log path as durable evidence for that row. A clean `closed` or `handoff-prepared` resumer status closes the wake item.

## Anti-scope

- Does not implement the scheduler runtime.
- Does not change `pr-batch-poller` schema.
- Does not inline post-merge checks; those belong to `wu-session-resumer`.
- Does not spawn successor WUs; the resumer writes the successor brief and the implementation orchestrator reads it during a later Phase 0 spawn.
