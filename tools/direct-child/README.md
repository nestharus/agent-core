# Contextual direct dispatcher (temporary outage transport)

`dispatch.py` picks a route for **one** child from its run context, then runs a native Codex or Claude session in the foreground. It implements the [shared temporary dispatch rule](../../AGENTS.md#temporary-direct-codex-dispatch-during-agent-runner-outage) while `agents` / `agent-runner` is down. The same seat can take a different model depending on its class. [`routes.toml`](routes.toml) is the single place to change providers, models, efforts, seat mappings, class mappings, and profile pools.

It does not decide seat authority or context boundaries, and it does not check that a class claim is true. The caller asserts both and owns them. It does not select tasks, allocate worktrees, authorize effects, or replace the review and delivery lifecycle.

## Observe, Frame, Decide and Act

At this consumer dispatch point, root applies the existing [separation of contexts](/mnt/c/Users/xteam/OneDrive/Documents/projects/oulipoly/agents/README.md#separation-of-contexts) through the full loop. The recipients are root at briefing and the agents root dispatches. Read the linked seat contracts with the [Core entry point](/mnt/c/Users/xteam/OneDrive/Documents/projects/oulipoly/AGENTS.md); the [route resolution below](#resolution) supplies this transport's model defaults, and the [launcher README](../direct-codex-child/README.md) supplies native launch and collection.

1. **Observe:** observers return evidence from realized work; they do not choose corrections or admit it. Root's own source observations also enter as evidence, rather than becoming class, scope or direction from root's own look.
2. **Frame:** an independent [Framer](/mnt/c/Users/xteam/OneDrive/Documents/projects/oulipoly/agents/README.md#framer) reads the person's words verbatim before any reading of them, then integrates the literal returns in hand. It interprets evidence; it does not inspect the work or select implementation.
3. **Decide:** an authorized [Decider](/mnt/c/Users/xteam/OneDrive/Documents/projects/oulipoly/agents/README.md#decider) sets the goal and direction, resolves consequential choices and authority, and carries target, why, necessary bounds and freedom in means into Act. Decide does not write the implementation specification. An unchanged valid Decision may be reaffirmed against the current Frame; a new decision item returns to authorized Decide.
4. **Act:** a separately dispatched [Maker](/mnt/c/Users/xteam/OneDrive/Documents/projects/oulipoly/agents/README.md#maker) chooses and makes the means within those decisions, then returns editable work, a construction witness and known gaps to root. Independent consequence observation returns through Frame and Decide; the producer does not validate or admit its own work.

**Every observer return goes through independent Frame and then authorized Decide before anything is corrected**, including clean checks of root's own briefs and findings described as small local defects. Root does not repair a checked brief directly from its observer's return. No Act launch comes between an observer return and its Frame. Where the current authorized Decision already permits dispatch after a Frame with no new decision item, root cites that Frame and the continuing Decision; the clean check itself supplies no correction authority.

This is a stricter local selection of [Core return routing](/mnt/c/Users/xteam/OneDrive/Documents/projects/oulipoly/agents/README.md#the-loop), which also permits a direct observation settling its requested use to go straight to Decide. It does not change Core. [Finding integration](/mnt/c/Users/xteam/OneDrive/Documents/projects/oulipoly/core/DISCOVERY.md#integrating-a-finding) and [ownership](/mnt/c/Users/xteam/OneDrive/Documents/projects/oulipoly/core/KERNEL.md#ownership) remain with their existing seats.

Act may use read-only Luna locators within its inherited authority and budget to find files, understand wiring and investigate implementation areas. They cannot independently validate or admit their parent's work. Negative or surprising findings, and findings that change target, scope, constraints or acceptance, return to root for independent Frame and authorized Decide before correction.

### Before briefing corrective Act

Every corrective Act brief cites the actual Frame return integrating the observations it acts on and the current authorized Decision. Each class, scope and direction item traces to that Frame or recorded Decide, never solely to root's own look. A located-correction class selects the model; it supplies neither readiness nor permission to skip Frame. Root supplies the [Runtime dispatch contract and observer packet](/mnt/c/Users/xteam/OneDrive/Documents/projects/oulipoly/agents/README.md#runtime), including verbatim words, declared use and recipient, material and method versions, map region, owned open questions or recorded Frame waivers, and the reading-check-first return with the Maker's construction witness.

The brief receives its independent cold check before dispatch. That check's literal return goes to Frame, then to authorized Decide for any decision item; a Decision already permitting continuation after a clean Frame remains the authority for that continuation. After making, anything a person or recipient will meet receives the Runtime first look in a cold context with only the person's words and goal, and the method change receives the independent alignment check at admission. Root collects the actual returns and preserves missing work and review debt.

Keep the actual observation → Frame → Decision → brief → cold check → Frame → Act trail, with any reopened Decision and subsequent consequence returns. Flags, native route records, producer verification and revised prose do not establish framing, admission or efficacy; the witness is the actual return under the existing [guarantee chain](/mnt/c/Users/xteam/OneDrive/Documents/projects/oulipoly/core/KERNEL.md#the-guarantee-chain). This binds the full loop within the [shared selected method and delivery lifecycle](../../AGENTS.md#selected-reasoning-and-change-support); it adds no runtime enforcement or replacement review procedure.

### Current campaign selection

For the `context-routing-20260929` minimal prose/entry closure, the [actual Decision](/home/nes/projects/agent-runner/planning/context-routing-20260929/development-return-decider-return.md) selects **no per-prompt cold check**, accepting its cost tradeoff and remaining debts for fast closure. This campaign selection takes precedence over the per-brief cold-check requirement and trail above; it does not replace independent consequence Observe → Frame → Decide after making. The [actual Frame](/home/nes/projects/agent-runner/planning/context-routing-20260929/development-return-frame-return.md) diagnoses the earlier observer → Act bypass as root treating small local defects as exempt and carrying its own interpretation into dispatch. The Decision accepts that diagnosis without establishing cold-agent compliance. Full Core adoption, efficacy and `.claude5` / `.codex2`–`.codex5` import loading remain debt; the wider inherited observation obligations remain explicit gaps, not completed work. This bounded selection changes neither Core nor other campaigns' obligations.

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
| `default` | Codex | `gpt-6.1-sol`, `high` | round-robin over `.codex2`, `.codex3`, `.codex4`, `.codex5` |
| `refine` | Codex | `gpt-6.1-sol`, `high` | round-robin over `.codex2`, `.codex3`, `.codex4`, `.codex5` |
| `explore` | Codex | `gpt-6-luna`, `max` | round-robin over `.codex2`, `.codex3`, `.codex4`, `.codex5` |
| `direction` | Claude | `claude-opus-5-5`, `medium` | `claude5` wrapper only |

**Moving `refine` to Sonnet** later is one edit: set its binding in `routes.toml` to `claude` / `claude-sonnet-5-5` / `high`.

**Model aliases.** `gpt` resolves to Sol 6.1 at `high`. `gpt-medium`, `gpt-high`, and `gpt-xhigh` keep their literal effort. The provider-neutral default is the `default` route, not the Codex `gpt` alias.

## Profiles

- Sol and Luna share one Codex counter. Each real launch takes the next profile under an exclusive `flock`, so allocation is atomic and cycles evenly. The counter lives at `~/.local/state/direct-child/codex.counter`.
- Configured Codex profiles must be `.codex`, `.codex2`, `.codex3`, `.codex4`, or `.codex5`; unsupported names are refused before dry-run or allocation.
- Allocation happens before the MCP preflight, so a refused preflight still uses its turn.
- Rotation spreads starts across accounts. It does not prevent concurrent calls on one account, and it knows nothing about rate limits.
- To pick a profile yourself, pass `--profile` with `--override-reason`. Explicit profiles never advance the counter. `.codex` is manual-only; the automatic pool is `.codex2`, `.codex3`, `.codex4`, `.codex5`.
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
- `--seat maker --class correction --basis /abs/frame-return.md#F3` for a Sol refinement under the cited Frame and current Decision in its brief.
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
