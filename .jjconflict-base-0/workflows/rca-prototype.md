---
workflow:
  id: rca-prototype
workflow_dispatch_contract:
  orchestrator: "prototype-rca-orchestrator"
  inputs:
    - "failure_id, trigger_type test or qa, trigger_evidence_path, repo_root, worktree_path, planning_dir, scratch_dir, handback_callback, and the trigger-specific rerun or QA selector"
  expectations:
    - "runs a light two-phase prototype RCA loop: root cause the already-observed failure, dispatch one narrow fix, verify only the same trigger, and hand back"
    - "treats the failing behavior test or QA observation/screenshot as the reproduction signal"
  outputs:
    - "per-iteration RCA and fix artifacts under ${planning_dir}/rca/, targeted rerun logs under ${scratch_dir}/logs/, and a handback envelope"
  non_goals:
    - "does not replace the full production RCA workflow and does not broaden the failing prototype trigger into unrelated validation work"
---
# RCA Prototype Workflow

## Purpose

Run a light root-cause and fix loop for one failed prototype signal. The workflow exists for a caller that already has a coarse reproduction: a failing behavior test or a QA observation/screenshot. That signal is enough to start; the loop identifies the root cause, applies one narrow fix attempt, verifies only the same signal, and returns control to the caller.

This workflow is deliberately separate from `~/ai/workflows/rca.md`, the full production RCA workflow. The light prototype workflow does not replace it. Use `~/ai/workflows/rca.md` when the situation needs incident framing, evidence-pack assembly, tracker follow-through, findings, post-mortem synthesis, and action-item management.

## Workflow Dispatch Surface

### Orchestrator

prototype-rca-orchestrator

### Inputs

- failure_id, trigger_type test or qa, trigger_evidence_path, repo_root, worktree_path, planning_dir, scratch_dir, handback_callback, and the trigger-specific rerun or QA selector

### Expectations

- runs a light two-phase prototype RCA loop: root cause the already-observed failure, dispatch one narrow fix, verify only the same trigger, and hand back
- treats the failing behavior test or QA observation/screenshot as the reproduction signal

### Outputs

- per-iteration RCA and fix artifacts under ${planning_dir}/rca/, targeted rerun logs under ${scratch_dir}/logs/, and a handback envelope

### Non-goals

- does not replace the full production RCA workflow and does not broaden the failing prototype trigger into unrelated validation work

## Use When

- `trigger_type: test` and `trigger_evidence_path` points to a failed behavior test log, assertion output, or equivalent failing test evidence.
- `trigger_type: qa` and `trigger_evidence_path` points to a QA observation/screenshot, trace, walkthrough note, or captured use-case failure.
- The caller has a single failing surface that should be fixed before returning to a prototype validation or prototype research workflow.
- The desired outcome is a targeted pass or a bounded handback, not a complete incident-to-close RCA.

## Do Not Use When

- The work is a production incident, customer incident, or operational outage. Use `~/ai/workflows/rca.md`.
- The caller needs broad implementation planning or a normal Work Unit lifecycle. Use the implementation pipeline.
- The observed signal is too vague to name one failing behavior test, route, component, workflow, or QA use case.
- The caller wants a general quality sweep instead of a fix intended to flip the original failing signal.

## Required Inputs

- `failure_id`: stable slug for artifact naming and handback.
- `trigger_type`: exactly `test` or `qa`.
- `trigger_evidence_path`: absolute path to the failing behavior test output or QA observation/screenshot evidence.
- `trigger_command?`: required for `trigger_type: test`; the smallest command that re-runs the failing signal. `test runner <node-id>` is the canonical Python shape.
- `qa_use_case_id?`: required for `trigger_type: qa`; a targeted selector for the single QA use case to re-walk.
- `repo_root`: absolute repository root for investigation context.
- `worktree_path`: absolute writable worktree where the Phase 2 fix dispatch may apply code changes.
- `planning_dir`: durable planning artifact root.
- `scratch_dir`: transient prompts, logs, and questions root.
- `handback_callback`: caller-owned resume target and enough context to return `fixed`, `blocked`, or `needs-input`.

## Output Paths

- `${planning_dir}/rca/<failure-id>.md`: latest root-cause artifact for ticket compatibility.
- `${planning_dir}/rca/<failure-id>-iter<N>.md`: root cause, failure surface, and evidence trail for iteration N.
- `${planning_dir}/rca/<failure-id>-iter<N>-fix.md`: Phase 2 fix attempt, changed files, rationale, and targeted verification result or QA handback result for iteration N.
- `${planning_dir}/rca/<failure-id>-fixed.md`: success artifact written only when the targeted signal passes.
- `${scratch_dir}/prompts/<failure-id>-iter<N>-root-cause.md`: child prompt for Phase 1 when materialized.
- `${scratch_dir}/prompts/<failure-id>-iter<N>-fix.md`: inline `gpt-high` fix dispatch prompt.
- `${scratch_dir}/logs/<failure-id>-iter<N>-rerun.log`: targeted test rerun log or QA re-walk result log.
- `${scratch_dir}/questions/<failure-id>-<slug>.question.md`: human-owned question artifact when the workflow returns `needs-input`.

## Phase Map

| Phase | Owner | Purpose | Durable output | Transition |
|---|---|---|---|---|
| 1 - Root Cause | `behavior-investigator` through the orchestrator | Identify the root cause, failure surface, and evidence trail for the supplied trigger | `${planning_dir}/rca/<failure-id>-iter<N>.md` and latest `${planning_dir}/rca/<failure-id>.md` | Phase 2, `blocked`, or `needs-input` |
| 2 - Fix And Targeted Re-Run | inline `gpt-high` fix dispatch | Read the RCA artifact, apply the narrow code change in `${worktree_path}`, and verify only the original trigger | `${planning_dir}/rca/<failure-id>-iter<N>-fix.md`; on pass, `${planning_dir}/rca/<failure-id>-fixed.md` | `fixed`, next Phase 1 iteration, `blocked`, or `needs-input` |

## Phase 1 - Root Cause

Phase 1 dispatches `~/ai/agents/behavior-investigator.md` with a constrained `target`, `repo_root`, `planning_root=${planning_dir}`, and `context` containing `failure_id`, `trigger_type`, `trigger_evidence_path`, the trigger command or QA selector, and prior iteration artifacts.

The Phase 1 deliverable is root cause only: it names the root cause, the failure surface, and the evidence trail that ties the failing behavior test or QA observation/screenshot to the suspected code or behavior contract. The primary durable path for the current iteration is `${planning_dir}/rca/<failure-id>-iter<N>.md`; the orchestrator also maintains `${planning_dir}/rca/<failure-id>.md` as the latest RCA path.

If intended behavior is ambiguous or the failing surface cannot be narrowed from the evidence, Phase 1 returns `needs-input` with a question artifact. If required evidence or paths are unreadable, Phase 1 returns `blocked`.

## Phase 2 - Fix And Targeted Re-Run

Phase 2 composes one inline `gpt-high` fix dispatch. The fix dispatch must read the RCA artifact, inspect only the necessary local surface, apply code changes in `${worktree_path}`, and record the changed files plus rationale in `${planning_dir}/rca/<failure-id>-iter<N>-fix.md`.

For a test trigger, Phase 2 re-runs only `trigger_command` or the supplied `test runner <node-id>` equivalent. For a QA trigger, Phase 2 re-walks only one use case through `qa_use_case_id` and `handback_callback`. Full regression remains the upstream caller responsibility after this workflow hands back.

`${planning_dir}/rca/<failure-id>-fixed.md` is written only on targeted pass. If the targeted signal still fails, the fix artifact records the failure and the loop returns to Phase 1 for the next iteration with the new evidence attached.

## Loop Semantics

One iteration is one Phase 1 root-cause pass followed by one Phase 2 fix and targeted re-run pass. The iteration counter starts at 1 and advances before the next Phase 1 dispatch after a still-failing targeted signal. The loop iterates until a stop state is reached.

Each iteration has named artifacts: `${planning_dir}/rca/<failure-id>-iter<N>.md`, `${planning_dir}/rca/<failure-id>-iter<N>-fix.md`, and `${scratch_dir}/logs/<failure-id>-iter<N>-rerun.log`. `${planning_dir}/rca/<failure-id>.md` always points to the latest root-cause content, while `${planning_dir}/rca/<failure-id>-fixed.md` exists only after the targeted signal passes.

Stop states are:

- `fixed`: targeted behavior test passes or the targeted QA re-walk returns pass.
- `blocked`: a required input, path, worktree edit, dispatch, or targeted verification path is unavailable.
- `needs-input`: a user-owned value, scope, intended-behavior, or handback question must be answered.

## Handback Contract

The workflow returns a parseable envelope to the caller:

```yaml
outcome: "fixed" | "blocked" | "needs-input"
failure_id: "<stable failure slug>"
iterations: <integer>
fix_artifact_path?: "${planning_dir}/rca/<failure-id>-fixed.md"
evidence_paths:
  - "${planning_dir}/rca/<failure-id>-iter1.md"
  - "${planning_dir}/rca/<failure-id>-iter1-fix.md"
  - "${scratch_dir}/logs/<failure-id>-iter1-rerun.log"
handback_callback:
  workflow_id: "prototype-validation-shipping" | "prototype-research-planning" | "direct"
  phase_to_resume: "<caller-owned resume point>"
  parent_run_id: "<optional caller session id>"
```

When `outcome: fixed`, `fix_artifact_path` must be present and point to `${planning_dir}/rca/<failure-id>-fixed.md`. For `blocked` and `needs-input`, omit `fix_artifact_path` and rely on `evidence_paths` for the artifacts needed for human review or caller-owned continuation.

## Stop Conditions

- Success returns `outcome: fixed` immediately after the targeted signal passes.
- `blocked` returns when required inputs are unreadable, the worktree cannot be edited, the child dispatch cannot produce an RCA artifact, the targeted command cannot run, or the QA handback cannot return a result.
- `needs-input` returns when expected behavior, scope, value judgment, or caller handback ownership is genuinely human-owned.

## Anti-Scope

This workflow does not modify, redefine, edit, narrow, rename, or replace `~/ai/workflows/rca.md`; that path remains the full production RCA workflow.

This workflow does not modify, redefine, edit, or broaden `~/ai/agents/behavior-investigator.md`; it reuses that operator for Phase 1 through orchestration.

This workflow does not modify, redefine, edit, or route the light loop through `~/ai/agents/incident-investigator.md`; that operator remains the production incident investigation surface for the full RCA workflow.

Do not modify, redefine, or edit the adjacent surfaces named above; they remain read-only and unchanged.

The loop does not introduce machine enforcement, machine-enforcement framing, runtime CodeRabbit, runtime risk-gate or risk gate cycles, process-tree audit or process tree audit steps, code review of the fix, implementation-pipeline review gates, or "tracked in a separate ticket" boilerplate.

The failing behavior test or QA observation/screenshot is the reproduction. Individualized reproduction-test creation is out of scope; the loop must not create, write, add, or author individual reproduction-test artifacts for the failing prototype signal.

The loop does not run full regression, full QA, post-mortem authoring, incident tracker filing, runbook authoring, or action-item fanout.

## Cross-References

- Full production RCA workflow: `~/ai/workflows/rca.md`.
- Phase 1 root-cause agent: `~/ai/agents/behavior-investigator.md`.
- Production incident investigator, intentionally separate: `~/ai/agents/incident-investigator.md`.
- Prototype-family sibling workflow: `~/ai/workflows/build-prototype.md`.
- Passive handback pointer: `~/ai/workflows/prototype-validation-shipping.md` may be a caller for one failing behavior-test or QA signal and consumes only the stable handback envelope; RCA internals remain private to this workflow.
- Forward-defined handback callers: future `~/ai/workflows/prototype-validation-shipping.md`, future `~/ai/workflows/prototype-research-planning.md`, or a direct caller.
