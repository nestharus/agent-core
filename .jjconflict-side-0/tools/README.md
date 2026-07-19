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
- `pr-batch-poller/` — status-only single-call GitHub PR query for N PRs. A scheduler-triggered or manual `wu-session-wake` root invokes it, joins rows to sessions, and dispatches one exact joined row to each `wu-session-resumer`; the poller never wakes sessions itself. **Status: implemented; see `pr-batch-poller/README.md`.**
- `wu-session-migration/` — reviewed-inventory cutover plus the strict persisted-session writer. It captures hash-bound provider/git evidence and exposes closed-schema `phase0-init`, `phase7-upsert`, `phase9-update`, `resumer-update`, and `resumer-close` operations through one exclusive-lock, held-parent, durable-journal, interruption-recoverable transaction primitive while preserving historical `sessions.index.json`. **Status: implemented; see `wu-session-migration/README.md`.**
- `workflow_index/` — deterministic generator for `workflows/index.json` from YAML frontmatter in `workflows/*.md`. **Status: implemented; see `workflow_index/README.md`.**
- `feature_route_manifest.py` — strict duplicate-key route-source adapter with a pre-parse xor between inline `--ticket-route-map-json` and `--successor-manifest`. Both paths require each feature record's sole existing backend issue key to equal immutable `ticket_id`, reject `wu_brief_path` before output or side effects, share one closed backend/branch/protected-ref/canonical-path/payload/dependency/cycle/wave/output validator, and write only fully validated `feature-route-manifest-v2` records. **Status: implemented.**
- `operational_contracts.py` — fail-closed executable validation for immutable reviewed/immediate PR identity and draft state, including required freshly fetched base/head SHAs and provider/fetched/reviewed equality for both OIDs, post-ready draft restoration versus non-replayable merge-attempt state, canonical process-tree reports, exact recursive leaf validation for nested test-audit fanout, route-discriminated direct feature-root validation, exact refactoring child/nested implementation PR/head/guard/base joins even when OIDs coincide, closed `refactoring-auditor-index-v1` route/feature/attempt identity with exact five-role pre/post arrays and current re-hash plus exact-LOW report parsing, closed `feature-route-attempt-proof-v1` envelopes with current child-owned companions, acyclic direct acceptance lineage, required caller-owned `ticket-operation-expected-context-v1` versus producer-owned Jira/Linear `ticket-operation-result-v1` comment/readback evidence, backend URL site/ticket identity, replay-safe serialized feature route attempts, canonical/protected refactoring/package execution, production-order provider-payload extraction, and immutable invocation-owned PR-review lifecycle. `validate-ticket-operation-result` requires `--expected-context`; route commands include common `validate-route-process-proof --feature-branch`, direct-only `validate-route-artifact-lineage`, and dependency-gating `validate-route-attempts`. **Status: implemented.**

## Composition pattern

The motivating example for these two tools is post-merge wake of WU sessions:

```
scheduler/manual root  ──>  wu-session-wake  ──(status only)──>  pr-batch-poller
                                  └──(one exact joined row)──>  wu-session-resumer agent
```

Each component does one thing:

- `scheduler` doesn't know about GitHub, PRs, or WU sessions. It invokes `wu-session-wake` on schedule.
- `pr-batch-poller` doesn't know about scheduling or session lifecycle. It batch-queries.
- `wu-session-wake` owns status invocation, session joins, exactly-once fanout, and aggregate process proof.
- `wu-session-resumer` (in `~/ai/agents/`) doesn't know about polling. It consumes one exact joined row and wakes that single session.

Adding all three concerns into one binary is an anti-pattern. The composition is a workflow, not a tool.

## Adding a new tool

1. Create a subdirectory: `~/ai/tools/<name>/`.
2. Add `README.md` describing the **one concern** the tool addresses, its inputs/outputs, and its anti-scope (what the tool will NOT grow into).
3. Add the implementation. Tools are typically a single Python module or shell script; small enough that a `git diff` from initial commit to current state is reviewable in one sitting.
4. Reference the tool from any agent / workflow / convention that consumes it. Add a "Used by" section to the tool's README listing those references.
