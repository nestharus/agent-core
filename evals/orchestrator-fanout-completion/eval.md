---
eval_id: orchestrator-fanout-completion
behavior_class: ACR-203 orchestrator fanout completion anti-pattern
lifecycle_state: WRITE
severity_when_fires: HIGH
evidence_source_kinds:
  - workflow-markdown
  - agent-markdown
  - dispatch-prompt
  - agents-trace-json
  - process-tree-audit
suggested_action_class: revise_fanout_completion_contract
prototype_pending_reason: "prototype-pending: implementation pending in ACR-232; remove marker and make this test pass"
---

# Orchestrator Fanout Completion

## Status: prototype-pending (carry-forward target)

prototype-pending: implementation pending in ACR-232; remove marker and make this test pass

This is a WRITE-state Markdown behavior specification for ACR-203. It is not runnable detector code. The actual orchestrator and workflow markdown changes are spawned-ticket work; this eval is the contract those tickets must satisfy.

## Eval identity

This eval defines a future detector shaped as `trace -> finding | None` for fanout-completion regressions in orchestrator and workflow markdown. It protects the re-framed ACR-203 answer: in the canonical `~/ai/workflows/agents-cli.md` dispatch shape, the parent waits on host Bash background task notification for each child `agents -m <model> -p <worktree-path> -f <prompt-file> 2>&1 | tee <log-path>` command. In-shell child-log watchers are not the completion primitive.

The recurrence guard explicitly covers these fanout sites:

- Phase 2.5 entry-mode audit dispatch.
- Phase 4 four-gate proposal-risk fanout.
- Phase 6 per-component code-quality fanout.
- Phase 8 PR-review fanout.
- Sibling-workflow internals in `workflows/audit.md`, `workflows/code-quality.md`, and `workflows/pr-review.md`.

## Unwanted behavior

The unwanted behavior is markdown that introduces, retains, or recommends an active wait primitive that competes with host Bash task completion for the canonical `agents` fanout shape.

Violation classes:

- `log-grep-watcher`: active waiting with `until grep ".*WROTE:.*" ...; do sleep ...; done`, `until grep '^WROTE:' ...`, or an equivalent loop over child logs.
- `unbounded-sentinel-watcher`: sentinel-file completion used as a sub-workflow backstop without a bounded `[ $SECONDS -gt N ] && break` or equivalent maximum duration.
- `trap-as-host-kill-cleanup`: markdown asserts `trap '...' EXIT` is sufficient for host-kill cleanup without acknowledging it is best-effort and unreliable under SIGKILL.
- `external-watchdog`: markdown introduces a daemon, external watchdog, inotify watcher, wrapper fanout process, or other persistent observer as the completion solution for this problem.

## Expected behavior

For the canonical agents-CLI fanout shape, orchestrator markdown must say completion is detected by host Bash background task notification: one host Bash background task per child, no shell `&`, no bundled child fanout wrapper, no PID wait, no trace polling, and no log scraping as the parent wakeup signal.

After host task completion, the parent may validate durable child artifacts: logs, reports, process-tree evidence, and expected output files. That validation is not the same as active waiting. It may fail the phase if a report is missing, stale, blank, malformed, or contradicted by the trace.

When a sibling workflow internally fans out and uses sentinel files as a backstop, the sentinel discipline must be report-first and sentinel-last. The gate writes and closes the report, verifies it is non-empty or parseable as required, and only then touches the sentinel as its final filesystem action. Any sentinel watcher must be bounded with `SECONDS`, `timeout`, or an equivalent hard cap.

The EXIT trap may remain as best-effort cleanup for normal exit and catchable signals. It must not be described as reliable cleanup for SIGKILL or host-kill behavior. The bounded timeout is the load-bearing cleanup for a sentinel watcher that does not observe completion.

## Positive evidence

A future eval should return no finding when the evidence shows all of these properties:

- Phase 2.5 entry-mode audit, Phase 4 proposal-risk gates, Phase 6 per-component code-quality checks, and Phase 8 PR-review dispatches use one host Bash background task per child and rely on host task notification for completion.
- The markdown has no active `until grep ... WROTE ...; sleep ...; done` watcher over child logs.
- Any sentinel-file backstop in `workflows/audit.md`, `workflows/code-quality.md`, or `workflows/pr-review.md` is sentinel-last and bounded.
- Any cleanup trap is described as best-effort; SIGKILL unreliability is named; the bounded watcher timeout is the load-bearing cleanup.
- `agents trace --json` is reserved for post-run inspection, audit evidence, session topology, and eval input, not active completion waiting.

## Negative cases

### Case 1 - WROTE log watcher retained

**Expected eval signal.** HIGH finding.

**Evidence.** Markdown contains an active wait loop shaped like `until grep ".*WROTE:.*" <child-log>; do sleep <N>; done`, `until grep '^WROTE:' ...`, or an equivalent repeated grep over child logs.

**Reasoning.** The current runner preserves line-start `WROTE:` in the observed merged tee log, but log scraping is still the wrong completion abstraction. The parent should wake on host Bash task completion and then validate artifacts.

### Case 2 - Unbounded sentinel watcher

**Expected eval signal.** HIGH finding.

**Evidence.** A sentinel-file wait loop has no visible maximum duration such as `[ $SECONDS -gt N ] && break`, `timeout <duration>`, or an equivalent bounded control path.

**Reasoning.** Sentinel-file completion can be appropriate only inside a sub-workflow backstop. Without a hard cap, a missing sentinel can leave the watcher stuck indefinitely.

### Case 3 - Trap claimed as sufficient host-kill cleanup

**Expected eval signal.** HIGH finding.

**Evidence.** Markdown says or implies `trap '...' EXIT` is enough to clean descendants after a host timeout or kill, without caveating SIGKILL and without making the bounded timeout the load-bearing cleanup.

**Reasoning.** EXIT traps are best-effort. They can run on normal exit and catchable signals; they cannot run under SIGKILL.

### Case 4 - Daemon or external watcher introduced

**Expected eval signal.** HIGH finding.

**Evidence.** Markdown adds a daemon, external watchdog, inotify watcher, persistent poller, or wrapper fanout process to solve canonical orchestrator fanout completion.

**Reasoning.** ACR-203's re-frame is to use the host task lifecycle already present in `agents-cli.md`, not add another orchestration layer.

### Case 5 - Sentinel-first backstop

**Expected eval signal.** HIGH finding when sentinel-file completion is recommended and the gate touches the sentinel before report write/verification.

**Evidence.** Workflow markdown, dispatch prompts, or sibling-workflow instructions order `touch <sentinel>` before report creation, flush, non-empty verification, or parseability checks.

**Reasoning.** Sentinel-first lets a watcher advance while the report is still missing. Sentinel-last is load-bearing.

## Non-fire cases

The eval must not fire on a foreground `agents ... 2>&1 | tee <log>` command where synchronous process exit is intentionally the wait. It must not fire on host-tool background dispatch examples where the backgrounding is outside the shell command, such as a host Bash task with `run_in_background=True`.

The eval must not fire on post-completion artifact validation that reads child logs or reports after the host task has completed. It must not fire on short local loops used inside deterministic proof-test scripts, provided those scripts are not being adopted as production orchestrator markdown.

The eval must not fire on bounded sentinel-last watchers used as internal sub-workflow backstops in `workflows/audit.md`, `workflows/code-quality.md`, or `workflows/pr-review.md`.

## Required trace fields

The future eval implementation should consume markdown and trace evidence by semantic role:

- Orchestrator markdown under evaluation.
- `workflows/agents-cli.md` dispatch-shape reference.
- Sibling workflow markdown for `workflows/audit.md`, `workflows/code-quality.md`, and `workflows/pr-review.md`.
- Dispatch prompts and logs for Phase 2.5, Phase 4, Phase 6, and Phase 8 fanout sites when available.
- Saved `agents trace --json` and process-tree-auditor reports when available.

Evidence joins should use invocation UUID, parent invocation ID, prompt path, log path, phase, gate name, component name, and session graph semantics when those fields are present. Missing trace evidence must not be treated as proof of correctness when the markdown itself contains a forbidden wait primitive.

## Finding shape

Findings preserve the minimum schema from `conventions/evals.md`: `eval_id`, `severity`, `evidence_paths`, `summary`, `suggested_action`, and `confidence`.

Allowed extensions include `phase`, `gate`, `workflow_path`, `detected_pattern_class`, `line_refs`, `root_invocation_uuid`, and `subtree_root_uuid`.

`detected_pattern_class` must be one of:

- `log-grep-watcher`
- `unbounded-sentinel-watcher`
- `trap-as-host-kill-cleanup`
- `external-watchdog`
- `sentinel-first-backstop`

## Suggested action

Return `revise_fanout_completion_contract`. The owning implementation ticket should remove active child-log watchers from canonical orchestrator fanout, state host Bash background task notification as the completion primitive, preserve post-completion artifact validation, and constrain any sub-workflow sentinel backstop to bounded sentinel-last discipline.

## Lifecycle notes

Lifecycle state is `WRITE`. Runnable detector code, fixtures, adapters, false-positive review, rollout, and enforcement are deferred to implementation tickets. Before this eval can move to `ROLL_OUT`, the `prototype-pending:` placeholder must be replaced with a real spawned-ticket key or URL, and a detector must prove it can distinguish active waiting from post-completion validation.

## Cross-references

- `/home/nes/ai/conventions/evals.md`
- `/home/nes/ai/conventions/prototype-pending-tests.md`
- `/home/nes/ai/workflows/agents-cli.md`
- `/home/nes/ai/workflows/audit.md`
- `/home/nes/ai/workflows/code-quality.md`
- `/home/nes/ai/workflows/pr-review.md`
- `/home/nes/projects/ai/planning/prototype-acr-203-clarify/dossier/evidence/p1-A-runner-envelope.md`
- `/home/nes/projects/ai/planning/prototype-acr-203-clarify/dossier/evidence/p1-B-sentinel-fanout.md`
- `/home/nes/projects/ai/planning/prototype-acr-203-clarify/dossier/evidence/p1-C-trap-cleanup.md`
- `/home/nes/projects/ai/planning/prototype-acr-203-clarify/dossier/evidence/p1-D-agents-native-completion.md`
