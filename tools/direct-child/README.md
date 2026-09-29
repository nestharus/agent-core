# Contextual direct dispatcher (temporary outage transport)

`dispatch.py` picks a route for **one** child from its run context, then runs a native Codex or Claude session in the foreground. It implements the [shared temporary dispatch rule](../../AGENTS.md#temporary-direct-codex-dispatch-during-agent-runner-outage) while `agents` / `agent-runner` is down. The same seat can take a different model depending on its class. [`routes.toml`](routes.toml) is the single place to change providers, models, efforts, seat mappings, class mappings, and profile pools.

It does not decide seat authority or context boundaries, and it does not check that a class claim is true. The caller asserts both and owns them. It does not select tasks, allocate worktrees, authorize effects, or replace the review and delivery lifecycle.

## Resolution

The first rule that applies decides the route:

1. **Explicit override.** `--route NAME`, or `--model ALIAS|NATIVE_ID`, wins. A native ID also needs `--provider` and `--effort`. `--effort` may override the effort of any resolved route. Every override, including `--profile`, requires `--override-reason`, and the reason is recorded.
2. **Seat with a fixed route.**
   - `framer` and `decider` use `direction`, whatever their class.
   - `scout` and `explorer` use `explore`.
   - `observer` uses `refine`.
3. **Seat with a per-class route.** `maker`, `method-steward`, and `investigator` use:
   - `direction` for `new-foundation`;
   - `refine` for `correction`;
   - `direction` for `unknown`. Missing evidence must not certify routine correction.
4. **Class alone.**
   - `new-foundation` uses `direction`.
   - `correction` uses `refine`.
   - `unknown` uses `default`.
5. **Plain legacy invocation** (no seat, no class) uses `default`, and records the class as `unknown`.

Rules for class:

- `--class` is `new-foundation`, `correction`, or `unknown`.
- `new-foundation` and `correction` require `--basis` with an evidence reference. The dispatcher refuses them without one.
- Class is never guessed from prompt text.
- `--pass generative|corrective` is recorded separately and never routes. A corrective pass that creates a new mechanism is `new-foundation`.
- Unknown seat or class names are refused.

Current bindings:

| Route | Provider | Model and effort | Profile |
|---|---|---|---|
| `default` | Codex | `gpt-6.1-sol`, `high` | round-robin over `.codex`, `.codex3`, `.codex4` |
| `refine` | Codex | `gpt-6.1-sol`, `high` | round-robin over `.codex`, `.codex3`, `.codex4` |
| `explore` | Codex | `gpt-6-luna`, `max` | round-robin over `.codex`, `.codex3`, `.codex4` |
| `direction` | Claude | `claude-opus-5-5`, `medium` | `claude5` wrapper only |

**Moving `refine` to Sonnet** later is one edit: set its binding in `routes.toml` to `claude` / `claude-sonnet-5-5` / `high`.

**Model aliases.** `gpt` resolves to Sol 6.1 at `high`. `gpt-medium`, `gpt-high`, and `gpt-xhigh` keep their literal effort. The provider-neutral default is the `default` route, not the Codex `gpt` alias.

## Profiles

- Sol and Luna share one Codex counter. Each real launch takes the next profile under an exclusive `flock`, so allocation is atomic and cycles evenly. The counter lives at `~/.local/state/direct-child/codex.counter`.
- Configured Codex profiles must be `.codex`, `.codex2`, `.codex3`, `.codex4`, or `.codex5`; unsupported names are refused before dry-run or allocation.
- Allocation happens before the MCP preflight, so a refused preflight still uses its turn.
- Rotation spreads starts across accounts. It does not prevent concurrent calls on one account, and it knows nothing about rate limits.
- To pick a profile yourself, pass `--profile` with `--override-reason`. Explicit profiles never advance the counter. `.codex2` and `.codex5` are manual-only.
- Claude runs only through the `claude5` wrapper, which sets `CLAUDE_CONFIG_DIR=~/.claude5`.

## Example

```bash
/home/nes/ai/tools/direct-child/dispatch.py \
  --seat maker --class new-foundation --basis /abs/facts.md#launcher-gap --pass generative \
  --cwd /absolute/worktree --prompt /absolute/prompt.md \
  --runs-dir /absolute/runs --id maker-routing
```

Other forms:

- `--seat scout` for a Luna explorer.
- `--seat maker --class correction --basis /abs/review.md#F3` for a Sol refinement.
- `--model gpt-xhigh --override-reason 'CRW contract names gpt-xhigh'` for a literal alias.

Add `--dry-run` to print:

- the resolution record;
- the exact quoted native command;
- the next pool profile, marked "not reserved".

A dry run writes no files, advances no counter, launches nothing, and does not check whether the Claude wrapper is installed.

## Execution and records

**Codex routes** hand off with `exec` to [`direct-codex-child/launch.sh`](../direct-codex-child/README.md), passing `--model`, `--effort`, and the resolution record. That launcher keeps its behavior:

- effective MCP discovery, per-server disable flags, and the injected docs-server disable;
- the preflight refusal;
- the attempt files `prompt.md`, `log.txt`, `final.md`, and `state.txt`;
- `DIRECT_CODEX_*` markers, with Codex's own exit as the process exit.

**Claude routes** run this command once in the worktree, with the prompt on stdin:

```bash
claude5 -p --model M --effort E --strict-mcp-config --mcp-config '{"mcpServers":{}}' \
  --settings '{"autoMemoryEnabled":false}' --no-session-persistence \
  --output-format stream-json --verbose
```

The attempt directory holds:

- `prompt.md`, read-only;
- `log.txt`, every stream event, written live;
- `stderr.txt`;
- `final.md`, available result text (invalid or ambiguous results remain diagnostic text);
- `route.json`;
- `state.txt`, which records the native command, raw `claude_exit`, result count and semantics, final/custody status, capture errors, and `dispatcher_exit`. The awaited native status is appended before final capture. Available raw stdout continues to the terminal even when log storage fails.

Claude exit codes:

- A nonzero native exit is propagated; a signal wait status `-SIG` becomes terminal status `128+SIG`, with the raw status retained.
- Success requires native exit 0, exactly one result event, boolean `is_error=false`, subtype `success`, and nonempty text with usable final capture. Missing, malformed, or multiple results remain unknown/failure; available text is preserved without a valid-final marker.
- Native exit 0 returns **3** for an unambiguous boolean error, **4** for missing/invalid results or failed final capture, and **1** for other incomplete custody.
- Final write/read/output or encoding errors report `final_capture_error` and `final_status=capture-error`. State errors report `state_capture_error` to the terminal. Failed storage cannot guarantee durable metadata: available terminal metadata preserves the observed native status, while custody is explicitly incomplete.

**Every attempt** has a `route.json` recording:

- the config path and its sha256;
- seat, class, class source, basis, and pass;
- the rule that fired and the route or alias;
- provider, model, and effort;
- overrides and their reason;
- profile and profile source.

Launch through a native persistent terminal, and record the terminal handle in the emitted `DIRECT_CHILD_STATE` or `DIRECT_CODEX_STATE`. Await that handle until it exits. Each seat is a fresh session, with no resume and no background runs. Collection works as in the [launcher README](../direct-codex-child/README.md).

## Limits

- **No health checks or recovery.** There is no health check, provider fallback, queue, scheduler, or Claude rotation. There is also no check that a native CLI version supports a flag. The Claude `--effort` values were read from the installed `claude --help`.
- **Routing is not validation.** Deterministic routing tests do not show that a class was right or that a model was effective. Records exist for a later benchmark.
- **Not yet in Runner.** This is not Runner or `agents` integration. Frontmatter still selects models inside `agents`.
- **CRW is unchanged.** Its opaque `gpt-xhigh` contract stays as it is; see [`models/roles.md`](../../models/roles.md).
- **Outcome is the caller's to judge.** Process custody proves that the process completed. It does not prove the task was done.

Tests use fake CLIs and never launch a model:

```bash
python3 -m unittest discover -s tools/direct-child -p 'test_*.py'
```
