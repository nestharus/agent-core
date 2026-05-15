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

## Standard invocation shape

```bash
agents -m <model> -p <worktree-path> -f <prompt-file> 2>&1 | tee <log-path>
```

- `-m <model>`: one of `gpt-high`, `gpt-xhigh`, `claude-opus`, `claude-sonnet`, or similar. See `~/ai/models/roles.md` for selection guidance.
- `-p <worktree-path>`: the agent's working directory; for branch work or tracked-file mutation, this MUST be a git worktree per `~/ai/conventions/worktree-isolation.md`.
- `-f <prompt-file>`: the prompt as a Markdown file, usually in `.tmp/` or `.build/`.
- `2>&1 | tee <log-path>`: capture stdout and stderr into a log file for review.

Use the README for other invocation forms. In `~/ai/`, the pattern above is the default pipeline entry point.

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

- Claude models are invoked as `claude-opus` or `claude-sonnet` through the CLI.
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
- Canonical long-running shape:
  ```python
  Bash(
      command="agents -m <model> -p <worktree-path> -f <prompt-file> 2>&1 | tee <log-path>",
      run_in_background=True,
      description="Run <child role>"
  )
  ```
- Do not use shell job control or custom watcher machinery for `agents` dispatches. Forbidden patterns: trailing shell `&`, `disown`, bundled wrapper scripts around multiple `agents` calls, shell `wait` after `agents` fanout, PID-capture plus PID waits around `agents` invocations, trace polling loops as the waiting primitive, and piping live `agents` stdout through truncating filters such as `head -N` or `grep -m1`.
- The forbidden trace-loop class includes repeated `agents trace --json` inspection used to decide when a child is complete.
- Do not poll continuously; use the Bash task completion notification.
- Capture the Bash tool task id so the output can be retrieved afterward; do not capture shell `$!` PIDs around `agents` invocations.
- Keep the `tee` log path stable so post-mortem inspection does not depend on terminal scrollback.
- `agents trace --json` is for post-run inspection, audit evidence, session topology, and eval input. It is not the active completion-wait primitive for a running child.

### sentinel completion markers for gated fanout

This is a narrow ACR-203 carve-out for gated fanouts inside the implementation pipeline: Phase 2.5 audit dispatch, Phase 4 risk and code-quality fanouts, Phase 6 per-component code-quality fanouts, and Phase 8 PR-review gates. The Bash tool task completion notification remains the primary completion signal; sentinel files are defense-in-depth and a backstop, not a replacement for task notifications.

Each child prompt in this carve-out instructs the child to `touch <log>.done` as its terminal action after the canonical report is written. Sentinel names must be unique per child and live under the stable log root. Before dispatch, the orchestrator must remove any stale `<log>.done` file so a prior run cannot satisfy the current completion check.

Fallback reconciliation is bounded: use the Bash builtin `$SECONDS` with `[ $SECONDS -gt 1800 ] && break` inside the until-loop body, or an equivalent harness timeout. Incomplete sentinel set after the bounded wait returns `BLOCKED:fanout-completion-timeout` with cited missing sentinel paths; the orchestrator refuses join-manifest write and phase advance, and no partial-verdict residual advance is allowed.

When the orchestrator owns backgrounded Bash tasks for such fanout, install `trap 'kill $(jobs -p) 2>/dev/null' EXIT INT TERM` or an equivalent harness-appropriate cleanup in the orchestrator's shell session before the first `Bash(run_in_background=True)` agents dispatch. This trap is current-shell-only: it kills jobs owned by that shell; grandchildren that escaped host CLI propagation remain ACR-203 anti-scope.

Sentinel files are completion evidence only. Canonical report paths, size, mtime, sha256, verdict_line, producing invocation UUID, process-tree audits, and join manifests remain the verdict evidence boundary. The rationale for this carve-out is that a watcher cannot run when Bash tool task notifications themselves have been lost, so a signal-driven filesystem sentinel is the orchestrator's last-line guarantee against orphan-sleep leakage.

The forbidden patterns above remain forbidden outside this carve-out and remain forbidden as primary completion mechanisms inside it: generic `until grep` log-scrapes, custom shell watcher machinery, trace polling loops, PID waits, bundled multi-`agents` shell scripts, and `head -N`-style truncation on live `agents` stdout.

For parallel risk gates, dispatch all rounds as separate Bash-background tool calls, then collect outputs sequentially after their task notifications arrive.
