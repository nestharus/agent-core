---
workflow:
  id: agents-cli
workflow_dispatch_contract:
  orchestrator: "root orchestrator or workflow operator invoking agents CLI"
  inputs:
    - "model name, worktree path, prompt file, and log path for an agent dispatch"
    - "sub-agent delegation, question-handling, or parallel-writer context"
  expectations:
    - "standardizes agents CLI invocation and tee-based log capture for pipeline work"
    - "routes delegated user questions through the root-owned question artifact convention"
    - "requires branch work and tracked-file mutation to run from git worktrees; central checkout use is read-state / branch-tracking only"
  outputs:
    - "consistent agents command shape for prompts, logs, and long-running background work"
    - "stable prompt and log naming conventions for post-run review"
  non_goals:
    - "does not replace the agent-runner README as the authoritative CLI reference"
    - "does not define model role selection beyond pointing to the model-role matrix"
---
# `agents` CLI — Workflow Conventions

## Declared roles

`orchestration`, `validator`, `formatter`.

This file-local declaration reflects this workflow's ownership of dispatch sequencing, pre-dispatch contract validation, and canonical prompt/log command formatting.

CLI reference: `/home/nes/projects/agent-runner/README.md`.
That is the authoritative source for flags, options, named-agent resolution, TOML model config, and invocation shapes. This doc only covers the conventions layered on top for pipeline work.

## Workflow Dispatch Surface

### Orchestrator

root orchestrator or workflow operator invoking agents CLI

### Inputs

- model name, worktree path, prompt file, and log path for an agent dispatch
- sub-agent delegation, question-handling, or parallel-writer context

### Expectations

- standardizes agents CLI invocation and tee-based log capture for pipeline work
- routes delegated user questions through the root-owned question artifact convention
- requires branch work and tracked-file mutation to run from git worktrees; central checkout use is read-state / branch-tracking only

### Outputs

- consistent agents command shape for prompts, logs, and long-running background work
- stable prompt and log naming conventions for post-run review

### Non-goals

- does not replace the agent-runner README as the authoritative CLI reference
- does not define model role selection beyond pointing to the model-role matrix

## Pre-dispatch contract resolution

1. Resolve the selected operator path: use the project wrapper when execution is in project scope and the wrapper is current; otherwise use the base operator.
2. Read the operator contract sidecar when present at `contracts/operators/<operator-name>.yaml`; otherwise read the operator's `## Contract` block. Parse the YAML and validate `schema: operator-contract-v1`.
3. Apply `defaults:` to the input set and verify all required inputs are present from defaults or caller-supplied values.
4. Honor the `must_delegate:` and `forbidden_direct:` boundaries when constructing the dispatch prompt; do not inline procedure that belongs to the operator.
5. Then invoke `agents -a <agent.md> -p <worktree-path> -f <prompt-file> 2>&1 | tee <log>` per the canonical command shape. The agent file's `model:` frontmatter drives model selection; do not pass `-m` alongside `-a`.

The workflow sidecar at `contracts/workflows/<workflow-id>.yaml`, when present, is the optimized workflow dispatch surface. Otherwise use the `workflow_dispatch_contract` frontmatter. The operator contract sidecar is the analogous optimized surface for operator dispatch.

## Standard invocation shape

Two shapes, selected by whether you are dispatching a defined agent or an ad-hoc prompt:

```bash
# Defined agent: frontmatter drives the model. No -m.
agents -a <agent.md> -p <worktree-path> -f <prompt-file> 2>&1 | tee <log-path>

# Ad-hoc / undefined agent: no agent file to read frontmatter from, so -m is required.
agents -m <model> -p <worktree-path> -f <prompt-file> 2>&1 | tee <log-path>
```

- `-a <agent.md>`: path or named-agent reference; the `model:` value in the agent's frontmatter selects the model. **Do not** combine with `-m` — `-m` shadows the frontmatter and silently defeats any model rebalancing.
- `-m <model>`: one of `gpt-high`, `gpt-xhigh`, `gpt-medium`, or another configured model id. Only used when there is no `-a`. See `~/ai/models/roles.md` for selection guidance.
- `-p <worktree-path>`: the agent's working directory; for branch work or tracked-file mutation, this MUST be a git worktree per `~/ai/conventions/worktree-isolation.md`.
- `-f <prompt-file>`: the prompt as a Markdown file, usually in `.tmp/` or `.build/`.
- `2>&1 | tee <log-path>`: capture stdout and stderr into a log file for review.

Use the README for other invocation forms. In `~/ai/`, the patterns above are the default pipeline entry point.

## Prompt / log file conventions

- Prompts live in the project's `.tmp/` directory.
- Prompts for `~/ai/` authoring work live in `~/ai/.build/`.
- Name prompts by phase: `<task>-<phase>.md`.
- Example: `slice-007-research.md`, `slice-007-proposal.md`, `slice-007-risk-audit.md`.
- Logs pair one-to-one with prompts: `<task>-<phase>.log`.
- For revisions, suffix by round: `slice-007-proposal-revise.md`, `slice-007-proposal-revise2.md`.
- For parallel risk rounds, log per round: `slice-007-risk-audit.log`, `slice-007-risk-audit2.log`, `slice-007-risk-audit3.log`.

## Sub-agent delegation

All sub-agent invocation goes through the `agents` CLI.

- Pipeline docs should describe model choice, prompt shape, working directory, and log capture.
- CLI reference details stay in `/home/nes/projects/agent-runner/README.md`, not in `~/ai/`.

## Sub-agent questions

Sub-agents do not talk to the user directly. When a sub-agent needs user input, it writes a question artifact under `~/ai/conventions/agent-questions-and-session-graph.md`, returns `NEEDS_INPUT:<question_artifact_path>`, and stops.

The root orchestrator reads the artifact, presents the question and structured options to the user, writes the paired answer artifact, and continues the originating work through the feature-detected resume path or the session-files fallback from that convention. Downstream workflow steps that depend on the answer are blocked until continuation evidence exists.

## Worktree Isolation

Every branch-work or tracked-file-mutating agent runs in a worktree, regardless of concurrency. Read-state operations may inspect the central checkout; single-writer branch work must not use the main checkout.

- Use one worktree per branch-work or tracked-file-mutating agent.
- Read-state agents can inspect the central checkout without tracked-file edits.
- See `~/ai/conventions/worktree-isolation.md` for the rule, central-checkout limits, and setup.

## Long-running agents

For agents expected to run longer than about 30 seconds:

- Dispatch with the orchestrator's background-execution mode, one Bash tool call per child.
- Canonical long-running shape (defined agent; frontmatter drives model):
  ```python
  Bash(
      command="agents -a <agent.md> -p <worktree-path> -f <prompt-file> 2>&1 | tee <log-path>",
      run_in_background=True,
      description="Run <child role>"
  )
  ```
  Use `-m <model>` instead of `-a <agent.md>` only when the dispatch has no agent file (ad-hoc prompt). Never combine `-m` with `-a`.
- Do not use shell job control or custom watcher machinery for `agents` dispatches. Forbidden patterns: trailing shell `&`, `disown`, bundled wrapper scripts around multiple `agents` calls, shell `wait` after `agents` fanout, PID-capture plus PID waits around `agents` invocations, trace polling loops as the waiting primitive, and piping live `agents` stdout through truncating filters such as `head -N` or `grep -m1`.
- The forbidden trace-loop class includes repeated `agents trace --json` inspection used to decide when a child is complete.
- Do not poll continuously; use the Bash task completion notification.
- Capture the Bash tool task id so the output can be retrieved afterward; do not capture shell `$!` PIDs around `agents` invocations.
- Keep the `tee` log path stable so post-mortem inspection does not depend on terminal scrollback.
- `agents trace --json` is for post-run inspection, audit evidence, session topology, and eval input. It is not the active completion-wait primitive for a running child.

For parallel risk gates, dispatch all rounds as separate Bash-background tool calls, then collect outputs sequentially after their task notifications arrive.

## Long-running / parallel agents on runtimes WITHOUT native background (opencode)

The mechanism above (`run_in_background=True` + a Bash task-completion notification) only exists when the dispatching orchestrator runs inside the Claude Code harness or the `claude` CLI. When the orchestrator itself runs on a runtime whose bash tool has **no background flag and no completion callback** — notably **opencode** (gpt-*), which additionally kills a foreground bash command at a timeout — that mechanism is unavailable, and a long foreground `agents … | tee` child dispatch is KILLED mid-run. On such runtimes the orchestrator MUST use the tmux-backed dispatch helpers instead:

```bash
# Launch — non-blocking, detached; the child runs OUTSIDE opencode's bash timeout, unbounded:
agents-bg <handle> -a <agent.md> -p <worktree> -f <prompt>      # or  -m <model>  for ad-hoc
# Poll — instant, safe in a loop; prints RUNNING, or DONE rc=<n> + the child's captured output:
agents-bg-poll <handle>
# Sequential convenience (blocks via short polls): agents-bg-wait <handle>
```

Parallel fan-out: launch every child with `agents-bg` (each returns immediately), then loop — `agents-bg-poll <handle>` for each, with a short `sleep` between rounds — until all are `DONE`, then read each handle's captured log. The helpers live at `~/.local/bin/agents-bg{,-poll,-wait}` and write per-handle log/done/rc files under `${AGENTS_BG_DIR:-~/.agents-bg}`.

**Scope of the prohibitions above:** the "do not poll / no wrapper script / no shell `&`/`disown`/`wait` / no trace-loop" rules govern runtimes that PROVIDE the Bash task-completion notification (harness, `claude`). On a no-native-background runtime (opencode) the `agents-bg` helpers — which use **tmux-detached** sessions, NOT shell `&`/`disown`, and a bounded `agents-bg-poll` loop, NOT trace-polling — are the REQUIRED mechanism, not a forbidden one. They preserve full `2>&1` capture (each child's stdout/stderr is teed to its handle log) and parent-visible `OULIPOLY_*` markers in that log. Do NOT fall back to foreground `agents … | tee` on opencode for any child expected to exceed the bash timeout, and do NOT use raw `&`/`nohup` (those are session-tied and orphan the child).
