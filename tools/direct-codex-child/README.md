# Direct Codex child launcher (temporary outage transport)

New contextual launches should normally use [`../direct-child/dispatch.py`](../direct-child/README.md). It resolves provider, model, effort, and profile from the seat and class, then delegates Codex routes to this launcher. This tool starts **one** child in the foreground while `agents` / `agent-runner` is down. It implements the [shared temporary dispatch rule](../../AGENTS.md#temporary-direct-codex-dispatch-during-agent-runner-outage). It does not select tasks, authorize effects, allocate worktrees, or replace the mandatory review and delivery lifecycle.

## One command per child

Prepare a nonempty prompt file containing the child's task, authority, exact workspace, and a pointer to the applicable project and shared `AGENTS.md` files. The shared outage rule is inherited through those files; its full text does not need to be copied into the prompt.

```bash
/home/nes/ai/tools/direct-codex-child/launch.sh \
  --profile .codex5 \
  --cwd /absolute/path/to/exact/worktree \
  --prompt /absolute/path/to/child-prompt.md \
  --runs-dir /absolute/path/to/durable/runs \
  --id child-name
```

`--profile` accepts only `.codex`, `.codex2`, `.codex3`, `.codex4`, or `.codex5`. Current automatic allocation in the dispatcher uses `.codex2`, `.codex4`, and `.codex5`; `.codex` and `.codex3` retain manual parser allowance outside that pool. These are session stores; launches take no profile lock (see [Profile concurrency](#profile-concurrency)). `--cwd`, `--prompt`, and `--runs-dir` must be absolute. `--id` is a short attempt label; repeated uses create distinct directories. Without `--model`/`--effort` the launcher uses `gpt-6.1-sol` at `high`. Give both flags to pass a native model id and effort literally, for example `--model gpt-6-luna --effort max`. `--route-json` is the dispatcher's resolution record; it is stored as `route.json` and referenced from state. The launcher discovers MCP server names from the effective `codex mcp list --json`, passes a disable flag for each, and verifies a second effective list reports exactly those servers disabled. It always supplies the URL and disable flag for `openaiDeveloperDocs`, because `codex exec` can inject that server even when `codex mcp list` omits it. It refuses the launch if discovery, parsing, or preflight fails, or if a new server appears in the second list. It does not check or pin the Codex version.

The launcher reserves `runs-dir/id.unique-suffix/` with private permissions and writes `prompt.md` (read-only snapshot), `log.txt` (live output), `final.md` (Codex `-o` output), and `state.txt` (start details and appended exit result). Paths are unique for each attempt and are never reused. A nonzero `log_capture_exit` in state flags an incomplete log while preserving the exact Codex exit code. Keep the runs directory outside a source diff when it is only machine-local evidence. Record task-specific base, owner, and expected handoff in the parent state or child prompt; the launcher records the exact canonical cwd and Git HEAD at start.

Launch this command through a **native persistent terminal** with a short initial yield. For a harness offering `exec_command` and `write_stdin`, record the returned `session_id` by appending `native_session_id=<id>` to the emitted `DIRECT_CODEX_STATE` path. Await that exact session with `write_stdin` until it returns `exit_code`; only then inspect `final.md`, `log.txt`, and `state.txt`. Keep at most one outstanding wait on a child. The launcher prints `DIRECT_CODEX_EXIT=<status>` and reads back `final.md` after Codex exits; an absent or empty final is marked explicitly. The native terminal exit code is the Codex exit code. A missing terminal exit or state exit entry means the attempt is incomplete, regardless of file contents.

Do not send the command to shell background or use `&`, `nohup`, shell `wait`, PID/file polling, repeated tail/status loops, or scrollback as completion evidence. Separate children get separate launcher commands, native terminal handles, attempts and writing workspaces. Do not restart an in-flight child only to apply this transport override; relay changes through a working session route and require acknowledgment.

<a id="profile-lease"></a>
<a id="local-launcher-profile-lock"></a>

## Profile concurrency

The launcher takes no profile lock: concurrent launches on one profile run side by side. ROOT's [U496 decision](/home/nes/projects/agent-runner/planning/context-routing-20260929/age353-next-operation-prep/per-root-runtime/e3-u496-remove-codex-profile-locks/root-decisions.md) retired the earlier whole-run local launcher profile lock, which serialized our own launches per profile as a precaution against concurrent Codex login refreshes and blocked later work. No refresh-caused outage was observed. Concurrent refresh or authentication conflicts on one profile are an accepted stress-testing risk, with no replacement lock, queue, copies or auth handling.

- `--lease-wait SECONDS` is a retired option, accepted and ignored. Nothing waits and the launcher has no exit 75.
- An existing `<profile>/.oulipoly-direct-child.lease` file, possibly still locked by a launcher from before the retirement, is neither read, locked, created nor removed.
- `state.txt` records `profile_lock=none`.
- Interactive Codex, editors, desktop apps, other machines, copies and external daemons can also write a profile, as before.

## Built-in delegation

After the MCP preflight and before creating the attempt, the launcher requests restrictions on Codex's delegation-like features. This step reads metadata only: it lists features with the selected profile, then requests false settings for every listed feature whose name matches `multi_agent`, `agent_message`, `collab` or `subagent`. Prior 0.159.2 metadata listed `multi_agent`, `multi_agent_v2`, `multi_agent_mode`, `agent_message_board` and `collaboration_modes`. It passes them as `-c features.NAME=false` (`--disable` rejected unknown names in that prior check), reads the list back with those flags, and passes surviving flags to `codex exec`.

This step never checks a version and never refuses a launch. State always records `delegation_capability=not-established` with a note: a completed ordinary Codex observation received collaboration schemas despite all five features reading back false. The cause was not investigated. Feature metadata does not establish model-facing absence, and older `withheld` records must be read only as metadata.

`delegation_features_listed`, `delegation_restriction_args` and `delegation_features` distinguish discovery, the settings passed and parsed readback. `delegation_feature_readback=all-listed-false` requires the same discovered membership with every state false; missing members or still-enabled states record `incomplete-or-enabled`. Failed/unparsed listing, no matching feature or failed/ambiguous readback records `unknown`; failed readback drops the flags. Duplicate rows and malformed matching rows cannot establish complete metadata. Each path still launches the sole task; none certifies tool absence.

After exit, `log_collab_lines` counts literal line-start `collab:` text in the log. It is a lead, not a child count: quoted command output has produced false positives, and Codex has rendered Wait there without rendering spawn. A zero count does not establish sole execution. Shell-launched processes, hooks, plugins and skills are outside the restriction. See [briefing the receiving seat](../direct-child/README.md#briefing-the-receiving-seat).

## Dry run and validation

Add `--dry-run` to validate local arguments and show the chosen profile/cwd without making directories, writing files, calling Codex, or running MCP preflight. It cannot certify that a live launch will pass MCP preflight. Add `--preflight-only` to run effective MCP discovery and the exact disable-flag check without creating an attempt or starting a child. Run `python3 -m unittest discover -s tools/direct-codex-child -p 'test_*.py'` from `~/ai` for isolated fake-CLI tests; they do not start a real child.

## Limits and consumers

The caller owns the native terminal handle and parent state entry; a shell program cannot discover the harness handle. This tool captures the Codex process exit and final, but it cannot prove the child satisfied its task or that review, effect authority, and worktree rules were met. Existing project `AGENTS.md` files must route readers to `~/ai/AGENTS.md` or the child needs a direct pointer. RFQ's umbrella `AGENTS.md` does route there, though its older `agents` CLI examples remain and are superseded for new outage launches by the shared override.

Used by: [`~/ai/AGENTS.md`](../../AGENTS.md) and project managers invoking new direct Codex children during the outage.
