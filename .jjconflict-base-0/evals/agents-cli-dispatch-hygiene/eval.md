---
eval_id: agents-cli-dispatch-hygiene
behavior_class: Agents CLI dispatch-hygiene anti-pattern
lifecycle_state: WRITE
severity_when_fires: HIGH
evidence_source_kinds:
  - agents-trace-json
  - dispatch-prompt
  - agent-log
  - audit-bundle
  - process-tree-audit
suggested_action_class: revise_dispatch_shape
---

# Agents CLI Dispatch Hygiene

## Eval identity

This is a markdown behavior specification for `agents-cli-dispatch-hygiene`, not runnable eval code. It defines a future detector shaped as `trace -> finding | None` for dispatch-hygiene anti-patterns around the `agents` CLI. The behavior class is trace-detectable child dispatch that relies on shell job control, wrapper scripts, or trace polling as the waiting primitive.

## Unwanted behavior

The unwanted behavior is any trace-backed dispatch shape that contradicts the canonical model: one direct `agents ... 2>&1 | tee ...` command per child, background execution delegated to the host Bash tool's `run_in_background=True`, and `agents trace --json` reserved for post-run inspection or audit evidence.

Pattern classes:

- (a) An `agents` invocation followed by trailing shell `&` or `disown`.
- (b) A bundled shell script wrapping N `agents` dispatches with one shared poll watcher.
- (c) An `until` or `while` loop over `agents trace --json` status output as a waiting primitive.
- (d) A bare `wait` after multiple `agents ... &` lines.
- (e) PID-capture (`$!`) plus `wait $PID` patterns over `agents` invocations.

## Positive evidence

The future eval implementation consumes evidence by role from a saved trace bundle. Positive evidence may appear in saved `agents trace --json`, dispatch prompt content, agent-run logs, audit-bundle findings, or process-tree-audit reports. A finding requires a concrete artifact showing one of the unwanted pattern classes, joined where available by invocation UUID, parent invocation ID, root invocation UUID, prompt file path, or session graph semantics.

## Non-fire cases

The eval must not fire on positive `Bash(..., run_in_background=True, ...)` dispatch examples where the host tool owns background execution and task notification. It must also not fire on foreground synchronous `agents ... 2>&1 | tee ...` dispatch when the parent intentionally waits for that command to finish.

Legitimate `agents trace --json` uses are non-fire cases when the trace is used for post-run inspection, audit evidence, session identity, process-tree topology, or eval input. The distinction is the waiting primitive: trace output can be evidence after or beside a run, but an `until` or `while` loop polling trace status to wake the parent is the unwanted behavior.

## Required trace fields

The future eval implementation must read saved `agents trace --json` as the preferred stable boundary. It must also read dispatch prompt content, agent-run logs, audit-bundle findings, and process-tree-audit reports by semantic role. Raw `state.db` evidence, if later exposed, is best-effort resolver evidence and must not become the only stable contract.

The detector must preserve the general `OULIPOLY_*` marker class and must name and consume `OULIPOLY_INVOCATION` and `OULIPOLY_SESSION` verbatim. These markers are required join evidence for process-tree and forensic audits, read from saved trace JSON and agent-run logs.

## Finding shape

Findings preserve the minimum schema fields from `conventions/evals.md`: `eval_id`, `severity`, `evidence_paths`, `summary`, `suggested_action`, and `confidence`. `severity` is `HIGH` when the matched pattern risks missed wakeups, hung poll watchers, or ambiguous child completion.

Allowed extensions include `wu_id`, `session_id`, `root_invocation_uuid`, `phase`, and `detected_pattern_class`. `detected_pattern_class` must identify one of the five unwanted behavior classes: `(a)`, `(b)`, `(c)`, `(d)`, or `(e)`.

## Suggested action

Return `revise_dispatch_shape` when the trace shows one of the forbidden dispatch patterns. The owning workflow should rerun the affected child dispatch with canonical `Bash(run_in_background=True)` and a stable `2>&1 | tee` log, or halt for manager-owned disposition.

## Lifecycle notes

This eval ships in `WRITE` state. The behavior specification exists for review, but no runnable detector is required or provided in this WU.

Runnable detector code, fixtures, advisory rollout, false-positive review, and `ENFORCE` readiness are deferred to a future ticket shaped like the ACR-175 lifecycle precedent. The ACR-174 deletion contract applies: no pytest revival, no structural Markdown tests, and no `tests/` directory.
