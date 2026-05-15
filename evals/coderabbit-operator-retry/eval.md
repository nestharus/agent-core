---
eval_id: coderabbit-operator-retry
behavior_class: CodeRabbit operator timeout/outage retry policy regression
lifecycle_state: WRITE
severity_when_fires: MEDIUM
evidence_source_kinds:
  - agents-trace-json
  - dispatch-prompt
  - agent-log
  - coderabbit-pass-output
  - operator-doc-snapshot
suggested_action_class: revise-proposal
---

# CodeRabbit Operator Retry

## Eval identity

This is a markdown behavior specification for `coderabbit-operator-retry`, not runnable eval code. It defines a future detector shaped as `trace -> finding | None` for CodeRabbit operator traces or operator-document revisions that mishandle transient CodeRabbit timeout/outage signals, deterministic non-transient failures, retry boundedness, terminal verdict vocabulary, pass-count semantics, rate-limit separation, or mirrored operator-doc text.

References: `~/ai/conventions/evals.md`, `~/ai/agents/coderabbit-operator.md`, and the ACR-207 CodeRabbit retry ticket and contract.

## Unwanted behavior

The unwanted behavior is any trace-backed CodeRabbit operator execution, dispatch prompt, agent log, CodeRabbit pass output, or operator-document snapshot that shows one of these retry-policy failures:

- (a) `premature-block-transient`: The operator returns `BLOCKED:<reason>`, `NEEDS_INPUT:<reason>`, or equivalent manager-facing halt on a transient CodeRabbit timeout/outage signal before entering the 30-minute retry loop and before the 48-attempt / 24h ceiling is exhausted.
- (b) `retry-non-transient`: The operator retries a deterministic non-transient failure instead of blocking immediately, including authentication or authorization failure, branch-missing, base-missing, diff-shape mismatch, invocation-shape error, dirty tree, stale `main`, base disagreement, malformed CLI arguments, missing `--cwd`, invalid working directory, or an unresolvable post-fix test failure.
- (c) `unbounded-or-orphan-sleep`: The retry uses an idle timeout, orphan/background sleep loop, polling worker, or per-invocation persistence such as `state.db` retry counts instead of a bounded 30-minute sleep owned by the active operator invocation.
- (d) `ceiling-new-terminal-token`: The sustained-outage ceiling surfaces as a new top-level terminal verdict token, such as `SUSTAINED_OUTAGE`, `OUTAGE_RETRY_EXHAUSTED`, or `TIMEOUT_RETRY_EXHAUSTED`, instead of the existing `BLOCKED:<reason>` prefix.
- (e) `retry-counts-as-pass`: A timeout/outage retry is treated as a value-bearing CodeRabbit pass by incrementing completed pass count, consuming `max_passes`, assigning finding IDs, triggering `MAX_PASSES_REACHED`, or participating in review-convergence semantics.
- (f) `rate-limit-flattened`: An explicit CodeRabbit rate-limit message with a concrete retry-after duration is folded into the fixed 30-minute outage loop instead of continuing to use the precise wait-until-clear behavior in `## Procedure: Rate-Limit Handling`.
- (g) `mirror-drift`: `~/ai/agents/coderabbit-operator.md` sections drift on the 30-minute interval, 48-attempt / 24h ceiling, transient/non-transient taxonomy, `BLOCKED:<reason>` terminal-prefix rule, or "retries are not passes" rule. Mirrored sections include `## Non-Negotiables`, `## Procedure: Single Pass`, `## Procedure: Timeout / Outage Retry Handling`, `## Decision Table`, `## Stop Conditions`, and `## Output Contract`.

## Positive evidence

The future eval implementation consumes evidence by semantic role from a saved trace bundle. Positive evidence may appear in saved `agents trace --json`, dispatch prompts, agent logs, CodeRabbit pass outputs, operator-doc snapshots, or review/audit bundles that include those artifacts.

Positive evidence includes one or more of these shapes:

- A dispatch prompt, agent log, or CodeRabbit pass output contains a transient outage signal such as `TIMEOUT ERROR: Review timed out`, service unavailable, upstream unavailable, temporary 5xx, gateway timeout, or retry-later outage wording without a concrete retry-after duration, followed by `BLOCKED:<reason>` or `NEEDS_INPUT:<reason>` before 48 retry attempts / 24h elapsed.
- Trace evidence shows a transient outage signal followed by a 30-minute bounded wait and a re-run of the same pass attempt. This is healthy evidence unless the same trace also shows pass-count, terminal-prefix, boundedness, or ceiling violations.
- Trace evidence shows a non-transient condition, such as auth failure, branch/base missing, malformed invocation, invalid working directory, dirty tree, stale `main`, base disagreement, diff-shape mismatch, or unresolvable post-fix test failure, followed by another CodeRabbit retry attempt.
- Process, transcript, or shell-log evidence shows a backgrounded sleep loop, idle timeout used as retry control, polling worker detached from the operator invocation, or persisted retry counter for the outage loop.
- Final stdout, summary, pass logs, or orchestrator-disposition evidence shows sustained outage represented by a new top-level terminal token instead of `BLOCKED:<reason>`.
- Pass logs, audit-history updates, `CODERABBIT_pass<N>.md`, `CODERABBIT_summary.md`, or final stdout show timeout/outage retries counted as completed review passes, `max_passes` consumption, review finding rounds, convergence evidence, or `MAX_PASSES_REACHED`.
- CodeRabbit output contains a concrete rate-limit retry-after duration, while the operator uses the fixed 30-minute outage loop instead of the precise wait-until-clear behavior.
- Operator-doc snapshot or diff evidence shows inconsistent policy text across the mirrored sections for interval, ceiling, taxonomy, terminal-prefix vocabulary, or pass-count semantics.

## Non-fire cases

- A transient CodeRabbit timeout or service outage without a concrete retry-after duration waits 30 minutes with a bounded in-dispatch sleep, re-runs the same pass attempt, and later succeeds with usable CodeRabbit review output.
- A non-transient failure, including auth failure, branch/base missing, malformed invocation, invalid `--cwd`, dirty tree, stale `main`, base disagreement, diff-shape mismatch, or unresolvable post-fix test failure, returns an immediate `BLOCKED:<reason>` or the existing pre-pass `NEEDS_INPUT:<reason>` without retrying.
- A sustained transient outage reaches the 48-attempt / 24h ceiling and surfaces as `BLOCKED:<reason>`, such as `BLOCKED:coderabbit-transient-outage-ceiling`.
- A CodeRabbit rate-limit message with a concrete retry-after duration continues to use the precise wait-until-clear behavior documented in `## Procedure: Rate-Limit Handling`, not the fixed 30-minute outage loop.
- Coordinated lockstep edits across `## Non-Negotiables`, `## Procedure: Single Pass`, `## Procedure: Timeout / Outage Retry Handling`, `## Decision Table`, `## Stop Conditions`, and `## Output Contract` leave no semantic drift on retry interval, ceiling, taxonomy, terminal prefix, or pass-count semantics.
- Retry sleeps are bounded, signal-driven, and owned by the active operator invocation, with no idle timeout substitution, background worker, orphan loop, or persisted per-invocation retry counter.
- Cosmetic markdown wording or ordering changes outside the retry interval, ceiling, taxonomy, terminal-prefix vocabulary, rate-limit boundary, boundedness rule, and pass-count semantics.

## Required trace fields

The future eval implementation must read evidence by semantic role, not by raw storage schema. Required roles are:

- WU or session scope, including WU ID, branch, base, worktree path, and whether the evidence comes from an implementation-pipeline Phase 7 run or standalone CodeRabbit operator dispatch.
- Root invocation UUID, operator invocation UUID, parent invocation ID, and session graph edges from saved `agents trace --json` when available.
- Dispatch prompt path and content for the CodeRabbit operator invocation, including `branch`, `base`, `worktree_path`, `max_passes`, `test_command`, and `audit_history_path` when supplied.
- Agent log or transcript path for the CodeRabbit operator invocation.
- Raw CodeRabbit command output path for each attempted pass or retry, including stdout/stderr text.
- CodeRabbit transient signal text and classification evidence, including whether a concrete retry-after duration is absent.
- CodeRabbit rate-limit text and parsed retry-after duration when present.
- Non-transient failure evidence, including auth, authorization, branch/base, invocation-shape, diff-shape, pre-pass sanity, or post-fix test failure details.
- Retry-attempt ordinal, retry wait duration, wait start/end evidence, and whether the retry re-ran the same pass attempt.
- Evidence that the sleep is bounded and owned by the active operator invocation, or evidence of idle timeout, orphan/background sleep, polling worker, or persisted retry count.
- Completed CodeRabbit pass count, configured `max_passes`, and evidence distinguishing usable review output from timeout/outage retry attempts.
- Finding IDs or audit-history round IDs emitted during the pass loop, if any, and whether retries created or advanced them.
- Final stdout line, terminal prefix, and terminal reason.
- `CODERABBIT_pass<N>.md` and `CODERABBIT_summary.md` paths and content snapshots when produced.
- Operator-doc snapshot or diff for `~/ai/agents/coderabbit-operator.md`, covering `## Non-Negotiables`, `## Procedure: Single Pass`, `## Procedure: Timeout / Outage Retry Handling`, `## Procedure: Rate-Limit Handling`, `## Decision Table`, `## Stop Conditions`, and `## Output Contract`.
- Lockstep-edit witnesses showing whether mirrored operator-doc sections agree on the 30-minute interval, 48-attempt / 24h ceiling, transient/non-transient taxonomy, `BLOCKED:<reason>` terminal-prefix rule, rate-limit boundary, boundedness rule, and "retries are not passes" rule.

The preferred boundary is saved `agents trace --json` plus pass-output and operator-doc snapshots, joined with prompt paths, log paths, invocation UUIDs, parent invocation IDs, and session graph evidence per `~/ai/conventions/evals.md` `## Trace bundle contract`.

## Finding shape

The finding preserves the minimum schema fields from `~/ai/conventions/evals.md`:

- `eval_id`
- `severity`
- `evidence_paths`
- `summary`
- `suggested_action`
- `confidence`

Allowed extension fields are:

- `wu_id`
- `session_id`
- `root_invocation_uuid`
- `operator_invocation_uuid`
- `branch`
- `base`
- `worktree_path`
- `phase`
- `unwanted_case`
- `transient_signal_text`
- `non_transient_signal_text`
- `rate_limit_retry_after`
- `retry_attempt_count`
- `retry_wait_duration_minutes`
- `ceiling_attempt_count`
- `terminal_prefix`
- `terminal_reason`
- `completed_pass_count`
- `max_passes`
- `pass_output_paths`
- `audit_history_path`
- `operator_doc_snapshot_path`
- `lockstep_edit_witnesses`

`unwanted_case` must be one of `premature-block-transient`, `retry-non-transient`, `unbounded-or-orphan-sleep`, `ceiling-new-terminal-token`, `retry-counts-as-pass`, `rate-limit-flattened`, or `mirror-drift`.

## Suggested action

Return `revise-proposal` when the future eval-runner returns a finding. The owning workflow should route the WU to remediation that revises the proposal, `~/ai/agents/coderabbit-operator.md`, or the retry-policy convention text that controlled the operator run, then reruns the relevant CodeRabbit operator evidence path. If the finding depends on repeated sustained-outage churn, terminal-prefix mismatch, or pass-count corruption, escalate to manager review before accepting the gate result.

## Lifecycle notes

This eval ships in `WRITE` state. No `eval.py` or `eval.rs` is required to exist in this WU.

Downstream implementation tickets own runnable detector code, fixtures, advisory rollout, false-positive review, and any CI or agent-runner runtime wiring. This WU must not create fixtures, create an advisory rollout, add a CI hook, edit `AGENTS.md` routing, edit `workflows/index.json`, wire Jira or Linear automation, wire agent-runner runtime behavior, revive structural markdown tests, or create `tools/<wu>-verify/`.
