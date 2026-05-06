# `~/ai/tools/` — Small Specialized Tools

Per `~/ai/VALUES.md` § Small specialized tools form an ecosystem, this directory hosts utilities that are small, single-concern, and composable. Each tool gets one subdirectory; each tool wraps one capability.

## Distinction vs. neighboring directories

| Directory | What lives there |
|---|---|
| `~/ai/agents/` | LLM operator definitions (markdown files with frontmatter; dispatched via `agents` CLI) |
| `~/ai/clients/` | Wrappers around one external service each (e.g. `clients/linear/`) |
| `~/ai/tools/` | **Code-level** utilities used by agents, scripts, or workflows; not service wrappers, not LLM operators |
| `~/ai/workflows/` | Multi-step procedures composing operators / clients / tools |
| `~/ai/conventions/` | Rules and policies; not capabilities |

## Current tools

- `scheduler/` — generic scheduled-task primitive. Bind a schedule (cron-style, interval, one-shot) to a script invocation, an agent dispatch, or a workflow run. **Status: skeleton only; see `scheduler/README.md`.**
- `pr-batch-poller/` — single-call GitHub PR status query for N PRs at once. Returns merged-status, new-comments, last-event-timestamp per PR. Used by the `wu-session-resumer` agent (per `~/ai/conventions/wu-session-lifecycle.md` Stage 6) to wake sessions in batches rather than one-poll-per-PR. **Status: implemented; see `pr-batch-poller/README.md`.**
- `workflow_index/` — deterministic generator for `workflows/index.json` from YAML frontmatter in `workflows/*.md`. **Status: implemented; see `workflow_index/README.md`.**

## Composition pattern

The motivating example for these two tools is post-merge wake of WU sessions:

```
scheduler  ──(every 10 min)──>  pr-batch-poller  ──(per merged PR)──>  wu-session-resumer agent
```

Each component does one thing:

- `scheduler` doesn't know about GitHub, PRs, or WU sessions. It schedules.
- `pr-batch-poller` doesn't know about scheduling or session lifecycle. It batch-queries.
- `wu-session-resumer` (in `~/ai/agents/`) doesn't know about polling. It wakes a single session given a merge event.

Adding all three concerns into one binary is an anti-pattern. The composition is a workflow, not a tool.

## Adding a new tool

1. Create a subdirectory: `~/ai/tools/<name>/`.
2. Add `README.md` describing the **one concern** the tool addresses, its inputs/outputs, and its anti-scope (what the tool will NOT grow into).
3. Add the implementation. Tools are typically a single Python module or shell script; small enough that a `git diff` from initial commit to current state is reviewable in one sitting.
4. Reference the tool from any agent / workflow / convention that consumes it. Add a "Used by" section to the tool's README listing those references.
