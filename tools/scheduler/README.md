# `scheduler` — generic scheduled-task primitive

**Status: skeleton. Not yet implemented.**

## One concern

Schedule a task to run on a specified time pattern. The task can be a shell script, an agent dispatch (`agents -a … -f …`), or a workflow invocation. The scheduler stores the schedule definition, ensures the runner is up when work is due, and tears down idle runners.

## Anti-scope

- The scheduler does NOT know what its scheduled tasks do. It runs them.
- The scheduler does NOT batch external API calls. (That's `pr-batch-poller` or another batching tool.)
- The scheduler does NOT track WU sessions or merge events. (That's `wu-session-resumer`'s job; it's just *triggered by* a scheduled task.)
- The scheduler does NOT decide a script's exit-code semantics — the script does.

## Inputs (proposed)

- `task_id` — stable identifier (idempotent; re-adding the same `task_id` updates rather than duplicates).
- `schedule` — one of:
  - `cron: "<expression>"` (cron syntax; e.g. `"0 */1 * * *"` for hourly)
  - `interval: <seconds>`
  - `one_shot: <iso8601-timestamp>`
- `target` — one of:
  - `script: <path>` (executes via `bash <path>`)
  - `agent_dispatch: { agent_file, model, prompt_file, project? }` (executes the equivalent `agents` invocation)
  - `workflow: <name>` (TBD; tied to whatever workflow-invocation primitive emerges)
- `concurrency_policy` — one of `serial` (skip if previous run still active), `parallel`, `kill-and-restart` (default: `serial`).
- `enabled` — boolean; when false the schedule is retained but does not fire.

## Outputs

- A list of run records per `task_id`: start time, end time, exit code, log path.
- The scheduler is **passive** — it does not push notifications. Consumers (e.g. `wu-session-resumer`) that need to act on completion poll the run record or are woken by the scheduled task itself.

## Storage

The scheduler keeps its schedule definitions and run history in a small SQLite DB at `~/ai/state/scheduler.db` (path TBD). The DB is the source of truth; the scheduler binary is stateless beyond it.

## Runtime model

The scheduler is **not a daemon**. When `scheduler add …` is called and the schedule database had been empty, the scheduler ensures a runner is started (cron entry, systemd timer, or equivalent). When `scheduler remove …` empties the database, the scheduler tears the runner down. This means the system has zero scheduler footprint when there is nothing to schedule.

## CLI shape (proposed)

```
scheduler add <task_id> --cron "0 */1 * * *" --script /path/to/script.sh
scheduler add <task_id> --interval 600 --agent-dispatch operator.md --model gpt-high --prompt prompt.md
scheduler list
scheduler runs <task_id> [--last 10]
scheduler remove <task_id>
scheduler enable <task_id>
scheduler disable <task_id>
```

## Used by

- (planned) `~/ai/conventions/wu-session-lifecycle.md` Stage 6 — schedules `pr-batch-poller` runs to detect merges.
- (planned) future operator / workflow uses TBD.

## TODO

- Implement.
- Decide runtime backing: cron vs systemd timer vs in-process tick-loop.
- Define the SQLite schema.
- Decide whether agent dispatch outputs (logs) are stored by the scheduler or by the dispatched agent (probably the latter; scheduler just records the path).
