# Direct Codex child launcher (temporary outage transport)

This tool starts **one** child in the foreground while `agents` / `agent-runner` is down. It implements the [shared temporary dispatch rule](../../AGENTS.md#temporary-direct-codex-dispatch-during-agent-runner-outage). It does not select tasks, authorize effects, allocate worktrees, or replace the mandatory review and delivery lifecycle.

## One command per child

Prepare a nonempty prompt file containing the child's task, authority, exact workspace, and a pointer to the applicable project and shared `AGENTS.md` files. The shared outage rule is inherited through those files; its full text does not need to be copied into the prompt.

```bash
/home/nes/ai/tools/direct-codex-child/launch.sh \
  --profile .codex3 \
  --cwd /absolute/path/to/exact/worktree \
  --prompt /absolute/path/to/child-prompt.md \
  --runs-dir /absolute/path/to/durable/runs \
  --id child-name
```

`--profile` accepts only `.codex`, `.codex2`, `.codex3`, or `.codex4`; these are session stores, **not a concurrency cap**. `--cwd`, `--prompt`, and `--runs-dir` must be absolute. `--id` is a short attempt label; repeated uses create distinct directories. The launcher uses `gpt-6-sol` at `xhigh`, reads configured MCP server names from the selected profile, passes a disable flag for each, and verifies the effective `codex mcp list` reports all disabled. It refuses the launch if that check fails. The `.codex` docs server receives a disable flag only when configured; this avoids the installed CLI error for the other three profiles. If Codex gains servers through an unrecognized configuration source, the preflight refuses unexpected rows.

The launcher reserves `runs-dir/id.unique-suffix/` with private permissions and writes `prompt.md` (read-only snapshot), `log.txt` (live output), `final.md` (Codex `-o` output), and `state.txt` (start details and appended exit result). Paths are unique for each attempt and are never reused. A nonzero `log_capture_exit` in state flags an incomplete log while preserving the exact Codex exit code. Keep the runs directory outside a source diff when it is only machine-local evidence. Record task-specific base, owner, and expected handoff in the parent state or child prompt; the launcher records the exact canonical cwd and Git HEAD at start.

Launch this command through a **native persistent terminal** with a short initial yield. For a harness offering `exec_command` and `write_stdin`, record the returned `session_id` by appending `native_session_id=<id>` to the emitted `DIRECT_CODEX_STATE` path. Await that exact session with `write_stdin` until it returns `exit_code`; only then inspect `final.md`, `log.txt`, and `state.txt`. Keep at most one outstanding wait on a child. The launcher prints `DIRECT_CODEX_EXIT=<status>` and reads back `final.md` after Codex exits; an absent or empty final is marked explicitly. The native terminal exit code is the Codex exit code. A missing terminal exit or state exit entry means the attempt is incomplete, regardless of file contents.

Do not send the command to shell background or use `&`, `nohup`, shell `wait`, PID/file polling, repeated tail/status loops, or scrollback as completion evidence. Separate children get separate launcher commands and native terminal handles. Several independent children may use one profile concurrently if their attempts and writing workspaces are distinct. Do not restart an in-flight child only to apply this transport override; relay changes through a working session route and require acknowledgment.

## Dry run and validation

Add `--dry-run` to validate local arguments and show the chosen profile/cwd without making directories, writing files, calling Codex, or running MCP preflight. It cannot certify that a live launch will pass MCP preflight. Run `python3 -m unittest discover -s tools/direct-codex-child -p 'test_*.py'` from `~/ai` for isolated fake-CLI tests; they do not start a real child.

## Limits and consumers

The caller owns the native terminal handle and parent state entry; a shell program cannot discover the harness handle. This tool captures the Codex process exit and final, but it cannot prove the child satisfied its task or that review, effect authority, and worktree rules were met. Existing project `AGENTS.md` files must route readers to `~/ai/AGENTS.md` or the child needs a direct pointer. RFQ's umbrella `AGENTS.md` does route there, though its older `agents` CLI examples remain and are superseded for new outage launches by the shared override.

Used by: [`~/ai/AGENTS.md`](../../AGENTS.md) and project managers invoking new direct Codex children during the outage.
