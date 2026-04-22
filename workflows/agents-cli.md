# `agents` CLI — Workflow Conventions

CLI reference: `/home/nes/projects/agent-runner/README.md`.
That is the authoritative source for flags, options, named-agent resolution, TOML model config, and invocation shapes. This doc only covers the conventions layered on top for pipeline work.

## Standard invocation shape

```bash
agents -m <model> -p <worktree-path> -f <prompt-file> 2>&1 | tee <log-path>
```

- `-m <model>`: one of `gpt-high`, `gpt-xhigh`, `claude-opus`, `claude-sonnet`, `claude-haiku`, or similar. See `~/ai/models/roles.md` for selection guidance.
- `-p <worktree-path>`: the agent's working directory. For parallel writers, this MUST be a git worktree. See `~/ai/conventions/worktree-isolation.md`.
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

- Claude models are invoked as `claude-opus`, `claude-sonnet`, or `claude-haiku` through the CLI.
- Pipeline docs should describe model choice, prompt shape, working directory, and log capture.
- CLI reference details stay in `/home/nes/projects/agent-runner/README.md`, not in `~/ai/`.

## Parallel writers

When multiple agents run concurrently and at least one writes tracked files, each agent MUST operate on its own git worktree.

- Use one worktree per writing agent.
- Read-only agents can share the project root.
- Single-writer runs can use the main checkout.
- See `~/ai/conventions/worktree-isolation.md` for the rule and setup.

## Long-running agents

For agents expected to run longer than about 30 seconds:

- Dispatch with the orchestrator's background-execution mode.
- Do not poll continuously; wait for the completion notification.
- Capture the task or process id so the output can be retrieved afterward.
- Keep the `tee` log path stable so post-mortem inspection does not depend on terminal scrollback.

For parallel risk gates, dispatch all rounds in parallel, then collect outputs sequentially.
