# Direct Codex child launcher (temporary outage transport)

New contextual launches should normally use [`../direct-child/dispatch.py`](../direct-child/README.md). It resolves provider, model, effort, and profile from the seat and class, then delegates Codex routes to this launcher. This tool starts **one** child in the foreground while `agents` / `agent-runner` is down. It implements the [shared temporary dispatch rule](../../AGENTS.md#temporary-direct-codex-dispatch-during-agent-runner-outage). It does not select tasks, authorize effects, allocate worktrees, or replace review and delivery duties applicable to RFQ code.

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

`--profile` accepts only `.codex`, `.codex2`, `.codex3`, `.codex4`, or `.codex5`. Current automatic allocation in the dispatcher uses `.codex2`, `.codex3`, and `.codex5`; `.codex` and `.codex4` retain manual parser allowance outside that pool. These are session stores; launches take no profile lock (see [Profile concurrency](#profile-concurrency)). `--cwd`, `--prompt`, and `--runs-dir` must be absolute. `--id` is a short attempt label; repeated uses create distinct directories. Without `--model`/`--effort` the launcher uses `gpt-6.1-sol` at `high`. Give both flags to pass a native model id and effort literally, for example `--model gpt-6-luna --effort max`. `--route-json` is the dispatcher's resolution record; it is stored as `route.json` and referenced from state. The launcher discovers MCP server names from the effective `codex mcp list --json`, passes a disable flag for each, and verifies a second effective list reports exactly those servers disabled. It always supplies the URL and disable flag for `openaiDeveloperDocs`, because `codex exec` can inject that server even when `codex mcp list` omits it. It refuses the launch if discovery, parsing, or preflight fails, or if a new server appears in the second list. It does not check or pin the Codex version.

The launcher reserves `runs-dir/id.unique-suffix/` with private permissions and writes `prompt.md` (read-only snapshot), `log.txt` (live output), `final.md` (Codex `-o` output), and `state.txt` (start details and appended exit result). Paths are unique for each attempt and are never reused. A nonzero `log_capture_exit` in state flags an incomplete log while preserving the exact Codex exit code. Keep the runs directory outside a source diff when it is only machine-local evidence. Record task-specific base, owner, and expected handoff in the parent state or child prompt; the launcher records the exact canonical cwd and Git HEAD at start.

Launch this command through a **native persistent terminal** with a short initial yield. For a harness offering `exec_command` and `write_stdin`, record the returned `session_id` by appending `native_session_id=<id>` to the emitted `DIRECT_CODEX_STATE` path. Await that exact session with `write_stdin` until it returns `exit_code`; only then inspect `final.md`, `log.txt`, and `state.txt`. Keep at most one outstanding wait on a child. The launcher prints `DIRECT_CODEX_EXIT=<status>` and reads back `final.md` after Codex exits; an absent or empty final is marked explicitly. The native terminal exit code is the Codex exit code. A missing terminal exit or state exit entry means the attempt is incomplete, regardless of file contents.

Do not send the command to shell background or use `&`, `nohup`, shell `wait`, PID/file polling, repeated tail/status loops, or scrollback as completion evidence. Separate children get separate launcher commands, native terminal handles, attempts and writing workspaces. Do not restart an in-flight child only to apply this transport override; relay changes through a working session route and require acknowledgment.

Automatic dispatch passes `--execution-pool-routes /absolute/public/routes.toml`.
After preflight, the launcher admits its already reserved profile immediately
before `codex exec`, under the shared pool control/counter lock. It records
`pool-admission.json`; a disabled reservation is known unstarted and returns 2
without selecting another account. No pool argument means explicit standalone
manual authorization, preserving existing behavior. Deploy this launcher with the
matching sibling `direct-child/execution_pool.py`; the short admission lock is
released at exec and does not serialize model execution or access profile stores.

## Storage for one-off investigations

For a one-off cleanup investigation, add `--ephemeral --log-max-bytes 33554432` to
the launcher command. `--ephemeral` is passed to Codex so that the run does not
persist session rollout files; the launcher's owned prompt, final and state
records remain. See the [official non-interactive mode documentation](https://learn.chatgpt.com/docs/non-interactive-mode#basic-usage).
Persistent roles retain their existing session behavior unless explicitly selected otherwise.

`--log-max-bytes` accepts a positive decimal byte count. It stores and mirrors at
most that many bytes of combined child output, drains the remaining output, and
writes `capture.json` with exact captured/dropped counts and any I/O error. A
truncated capture has `log_capture_exit=3`; an I/O failure has a nonzero capture
exit. Both mean incomplete evidence. The actual Codex exit is still recorded
separately and remains the native terminal exit; a zero Codex exit does not make
an incomplete capture complete. There is no automatic task replay or forced
child termination. The log is opaque bytes, including non-UTF-8 output.

The log budget covers child-output capture, not the separately retained prompt,
final, state, caller terminal storage or other tools' files. Omitting the flag
retains the existing full `tee` capture. Choose the required evidence and budget
before launching; required full evidence must not silently be treated as covered
by a capped prefix. Neither flag deletes existing sessions, logs or worktrees.

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

### Prospective persisted-session retirement (preparatory source)

Existing launches and opaque captures grant no retirement authority. A future direct
Codex invocation may opt in with `--session-lifecycle oneoff|reusable` and
`--session-owner-receipt /absolute/owner.json`. The dispatcher forwards these only
for direct Codex; it refuses them for other transports/providers before allocation.
The model, effort, MCP preflight, pool admission, capture quality and native END
collection contract remain in force. The optional machine-readable stdout is
intercepted before opaque capture limits. Missing, duplicate, invalid or oversized
typed metadata holds that invocation. No old capture is parsed.

The owner receipt has exactly these keys: `owner`, `custodian`, `collector`,
`caller_session_id` (canonical UUID), `account_binding` (original owner account
receipt reference), `context_ref`, `required_closures`, and `hold_owners`.
`required_closures` maps every actual processing/consumer/context obligation to
its original actor; `processing` and `context` must name `owner`.
`hold_owners` maps each of source, consumer, control, outbox, publication, resource,
recovery, effect, privacy and custody to its actual actor. No default empty holds
or inferred consumer set is supplied. An incomplete obligation inventory remains
held; owning a new directory alone proves no exclusive custody.

The attempt's immutable `session-retirement.json` captures a fresh invocation UUID,
original profile/home, absolute binary/hash, route reference/hash and original
account reference. `session-retirement.jsonl` is its fsynced, chained append-only
operation/lifecycle journal; required receipts survive logical deletion. This is
part of the existing attempt manifest, with no database or scheduler. Original
actors can call `session_retirement.edit()` or `record --attempt PATH --actor ACTOR
--generation N --event JSON`; the JSON has `kind` and `value`. The API docstrings
and source-only tests give exact receipt examples. `close` records each actual
closure once per generation, `hold` records actual references and their clearance,
`collect` records the original native terminal handle and collection receipt,
and `custody` records the exclusive complete descendant tree and actual evidence.
Process END supplies none of those actual work/context/consumer closures.

All owners of resume, fork, context, consumer, hold and descendant lifecycle writes
must cooperate on this same per-attempt lock. They must `reopen` **before** new
work, resumption, descendants or obligations; this preserves old immutable
closures in history and starts a new unqualified generation. Noncooperating or
unknown writers cannot satisfy this contract. Actor labels are local cooperative
custody assertions, not an authentication system or protection against hostile
filesystem writers. The immutable original owner controls directory permissions.

A `custody` receipt must bind the invocation, generation and exact binding digest;
attest exclusive complete coverage, no unknown descendants/active callers; and
supply a rooted tree of UUID members and actual edge receipts. Every member needs
the original custodian, inactive state, numeric END, collection/closure references,
actual processing time and actual context-close time. The root, every required
consumer and every descendant contribute to the latest required completion. Only
after that maximum plus 86400 seconds, all ten independent hold classes clear,
and original collection is complete, may the original owner invoke `retire()` or
`retire --attempt PATH --actor ACTOR --binding ORIGINAL_BINDING_JSON` from its
current `CODEX_SESSION_ID`. Current caller/ancestor/active children are refused.
Reusable builder/reviewer contexts require actual context lifecycle closure;
individual process END cannot close them. Unknown legacy sessions stay held.

A finite visit locks the cooperative lifecycle, persists intent/fence, initializes
a newly controlled stdio app-server on the exact original binary/home, verifies
`initialize.codexHome`, sends `initialized`, persists possible-send, then sends
only `thread/delete {threadId}`. The installed public 0.167.0 schema was qualified
offline; `session_retirement.py` pins its binary SHA256. Requalify source before
using a changed binary. No pool lookup, current-profile substitution, inventory,
thread read, model start/resume, private fallback or client attachment occurs.

Durable ACK suppresses duplicate requests. Timeout/crash after possible-send is
unknown and never blindly replayed. An unsent record may be requalified, or its
original owner may `release-unsent` with a real receipt before new lifecycle work.
An uncertain/acknowledged fence cannot be waived by this adapter; reconciliation
stays with the actual effect owner. ACK means supported logical deletion only;
it proves neither physical absence nor platform byte reclamation. SDK ephemeral
teardown and coordinator queue/artifact cleanup remain separate lifecycles.

This source is not installed or activated. No real thread was deleted during
qualification. Run the bounded source-only tests with `test_session_retirement.py`;
its clocks, CLI and stdio server are synthetic and require no credentials.
