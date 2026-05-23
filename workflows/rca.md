---
workflow:
  id: rca
workflow_dispatch_contract:
  orchestrator: "rca-orchestrator"
  inputs:
    - "incident_id or failure_id, trigger_type failing_test or incident, trigger_evidence_path, repo_root, worktree_path, scratch_dir, planning_dir, audit_history_path defaulting to ${planning_dir}/audit-history.md, ticket_system, and tracker operator inputs when downstream filing is needed"
    - "for incident triggers, enough incident context or incident brief material to author a real reproduction test in the worktree before root-cause analysis"
    - "for failing_test triggers, the existing failing test command or node id and evidence needed to enter root-cause analysis directly"
    - "post-apply gate currentness and trace inputs when available, including cycle_id, head_sha, base_ref, diff hash, scope/runtime-claim refs or hashes, process_tree_path, and root_invocation_uuid"
  expectations:
    - "runs a reproduction-first RCA loop: classify the trigger, author or accept the failing test, split root cause, fix choice, application plan, and application into separate fresh invocations, verify-or-return, then run apply-gate-set(caller_mode=rca-post-apply) before downstream lifecycle"
    - "uses rca-orchestrator as the procedural owner at agents/rca-orchestrator.md and preserves downstream post-mortem, action-item, runbook, tracker-comment, and close-or-pending work behind a current Phase 6.5 PASS"
    - "returns to root-cause analysis on every red verification; iterates until verification is green or the operator halts"
  outputs:
    - "reproduction artifact, root-cause artifact, fix-decision artifact, application-plan artifact, applied-fix artifact, and RCA-scoped gate-set artifacts"
    - "gate-set dispatch manifest, join manifest, aggregate report, child report index, expected-process manifest, process-tree report reference or non-applicability record, audit-history records, and optional ticket-comment payload"
    - "post-mortem, action-item ticket index, runbook outputs, tracker comments, and close-or-pending record when downstream lifecycle proceeds after current Phase 6.5 PASS"
    - "NEEDS_INPUT question artifacts or BLOCKED stop-state evidence when RCA cannot safely proceed"
  non_goals:
    - "does not edit rca-prototype, prototype-rca-orchestrator, incident-investigator, behavior-investigator, post-mortem-author, ticket operators, or implementation-pipeline-orchestrator"
    - "does not introduce machine-enforcement framing, replace implementation-pipeline, CodeRabbit, PR-review, proof-risk, validation-integrity, process-tree, or ticket-system gates, or wire implementation-pipeline callers; ACR-288 owns implementation-pipeline caller wiring"
    - "does not make ticket comments canonical; comments are mirrors of file-backed gate evidence"
    - "does not delete the downstream incident lifecycle; post-mortem authoring, action-item tickets, runbooks, tracker comments, and close-or-pending handling remain Phase 7+"
---
# RCA Workflow

## Purpose

Coordinate the full RCA path for an incident or already-failing test. The workflow first normalizes the trigger, establishes a real reproduction test when the trigger is an incident, isolates root cause from fix choice, isolates fix choice from application strategy, applies the approved plan, then verifies the original failing signal before downstream incident lifecycle work proceeds.

The procedural owner is `rca-orchestrator` at `agents/rca-orchestrator.md`. The workflow composes existing specialist operators where appropriate, but the RCA loop itself is owned by that orchestrator.

## Workflow Dispatch Surface

### Orchestrator

rca-orchestrator

### Inputs

- incident_id or failure_id, trigger_type failing_test or incident, trigger_evidence_path, repo_root, worktree_path, scratch_dir, planning_dir, audit_history_path defaulting to `${planning_dir}/audit-history.md`, ticket_system, and tracker operator inputs when downstream filing is needed
- for incident triggers, enough incident context or incident brief material to author a real reproduction test in the worktree before root-cause analysis
- for failing_test triggers, the existing failing test command or node id and evidence needed to enter root-cause analysis directly
- post-apply gate currentness and trace inputs when available, including cycle_id, head_sha, base_ref, diff hash, scope/runtime-claim refs or hashes, process_tree_path, and root_invocation_uuid

### Expectations

- runs a reproduction-first RCA loop: classify the trigger, author or accept the failing test, split root cause, fix choice, application plan, and application into separate fresh invocations, verify-or-return, then run apply-gate-set(caller_mode=rca-post-apply) before downstream lifecycle
- uses rca-orchestrator as the procedural owner at agents/rca-orchestrator.md and preserves downstream post-mortem, action-item, runbook, tracker-comment, and close-or-pending work behind a current Phase 6.5 PASS
- returns to root-cause analysis on every red verification; iterates until verification is green or the operator halts

### Outputs

- reproduction artifact, root-cause artifact, fix-decision artifact, application-plan artifact, applied-fix artifact, and RCA-scoped gate-set artifacts
- gate-set dispatch manifest, join manifest, aggregate report, child report index, expected-process manifest, process-tree report reference or non-applicability record, audit-history records, and optional ticket-comment payload
- post-mortem, action-item ticket index, runbook outputs, tracker comments, and close-or-pending record when downstream lifecycle proceeds after current Phase 6.5 PASS
- NEEDS_INPUT question artifacts or BLOCKED stop-state evidence when RCA cannot safely proceed

### Non-goals

- does not edit rca-prototype, prototype-rca-orchestrator, incident-investigator, behavior-investigator, post-mortem-author, ticket operators, or implementation-pipeline-orchestrator
- does not introduce machine-enforcement framing, replace implementation-pipeline, CodeRabbit, PR-review, proof-risk, validation-integrity, process-tree, or ticket-system gates, or wire implementation-pipeline callers; ACR-288 owns implementation-pipeline caller wiring
- does not make ticket comments canonical; comments are mirrors of file-backed gate evidence
- does not delete the downstream incident lifecycle; post-mortem authoring, action-item tickets, runbooks, tracker comments, and close-or-pending handling remain Phase 7+

## Declared roles

`orchestration`, `parser`, `validator`

`orchestration` covers RCA phase sequencing and transitions. `parser` covers dispatch-contract / frontmatter / input-output schema. `validator` covers trigger validation, phase-advancement gate, and stop-condition checks per the procedure body.

## Adapter declarations

```yaml
adapter_declarations:
  - component: workflows/rca.md
    role: adapter
    Translates:
      - rca-workflow-lifecycle-surface
      - rca-caller-mode-contract-surface
      - currentness-policy-citation-surface
```

The three translated surfaces are the complete adapter declaration. The new currentness-policy-citation-surface subordinates all `~/ai/conventions/apply-gate-set-currentness.md` section citations to one translated contract.

## Use When

- A production incident, customer incident, operational outage, or field failure needs reproduction, root-cause analysis, fix selection, application, verification, and downstream incident follow-through.
- A failing test already exists and the caller needs the RCA loop to start from root cause without inventing another reproduction path.
- The caller needs the downstream RCA lifecycle to remain visible after the fix verifies: post-mortem authoring, action-item tickets, runbooks, tracker comments, and close-or-pending state.

## Do Not Use When

- The caller only needs the light prototype loop for one failed prototype signal; use `~/ai/workflows/rca-prototype.md`.
- The caller only needs an evidence-backed incident findings artifact; use `~/ai/agents/incident-investigator.md`.
- The caller only needs one post-mortem from existing findings; use `~/ai/agents/post-mortem-author.md`.
- The caller wants broad implementation planning without an incident or failing behavior; use the implementation pipeline.

## Required Inputs

- `incident_id?`: stable tracker key, URL, incident slug, or incident handle.
- `failure_id`: stable slug used in reproduction and RCA artifact paths.
- `trigger_type`: exactly `failing_test` or `incident`.
- `trigger_evidence_path`: path to failing test output, incident brief, QA observation, log bundle, or other concrete trigger evidence.
- `trigger_command?`: required for `trigger_type=failing_test`; optional after Phase 1 authors the incident reproduction test.
- `repo_root`: repository root for read-only analysis.
- `worktree_path`: writable worktree where reproduction tests and Phase 5 application changes land.
- `scratch_dir`: transient prompts, logs, and question artifacts.
- `planning_dir`: durable RCA artifact root.
- `audit_history_path?`: audit-history path for gate-set evidence, defaulting to `${planning_dir}/audit-history.md`.
- `process_tree_path?`: RCA root invocation process-tree trace when process-tree verification is required.
- `root_invocation_uuid?`: RCA root invocation UUID when process-tree verification is required.
- `currentness inputs?`: `cycle_id`, `head_sha`, `base_ref`, diff hash, scope reference or hash, runtime-claim reference or hash, producing invocation refs, and verified-at data when available for Phase 6.5.
- `ticket_system?`: `linear` or `jira` when downstream tracker filing or comments are in scope.

## Output Paths

- `${planning_dir}/repro/<failure-id>.md`: reproduction-test artifact and red-run evidence.
- `${planning_dir}/rca/<failure-id>.md`: root-cause artifact.
- `${planning_dir}/rca/<failure-id>-fix-decision.md`: selected best appropriate fix.
- `${planning_dir}/rca/<failure-id>-application-plan.md`: best way to apply the fix.
- `${planning_dir}/rca/<failure-id>-applied.md`: applied change, changed paths, and verification notes.
- `${planning_dir}/rca/gate-set/<failure-id>/dispatch-manifest.md`: Phase 6.5 gate-set dispatch manifest.
- `${planning_dir}/rca/gate-set/<failure-id>/join-manifest.json`: Phase 6.5 canonical join manifest.
- `${planning_dir}/rca/gate-set/<failure-id>/aggregate-report.md`: Phase 6.5 aggregate report and terminal decision.
- `${planning_dir}/rca/gate-set/<failure-id>/child-report-index.md`: Phase 6.5 child report index.
- `${planning_dir}/rca/gate-set/<failure-id>/expected-process.json`: Phase 6.5 expected-process manifest.
- `${planning_dir}/rca/gate-set/<failure-id>/process-tree-report.md` or `${planning_dir}/rca/gate-set/<failure-id>/process-tree-not-applicable.md`: Phase 6.5 process-tree evidence or explicit mode-scoped non-applicability.
- `${planning_dir}/rca/gate-set/<failure-id>/ticket-comment-payload.md`: optional tracker mirror payload when requested.
- `${planning_dir}/post-mortem.md`: downstream post-mortem.
- `${planning_dir}/action-items.md`: downstream action-item ticket index.
- `${planning_dir}/runbooks/`: downstream runbook outputs.
- `${planning_dir}/tracker-comments/`: downstream tracker-comment drafts or evidence.
- `${planning_dir}/rca-close.md`: close-or-pending record.

## Phase Map

| Phase | Name | Primary owner | Durable output | Transition |
|---|---|---|---|---|
| 0 | Trigger Classification | `rca-orchestrator` (`agents/rca-orchestrator.md`) | normalized trigger envelope | Phase 1 for `incident`, Phase 2 for `failing_test` |
| 1 | Reproduction Test | fresh test-writer invocation through `rca-orchestrator` | `${planning_dir}/repro/<failure-id>.md` | Phase 2 after red on current HEAD |
| 2 | Root Cause | fresh `gpt-xhigh` RCA dispatch | `${planning_dir}/rca/<failure-id>.md` | Phase 3 |
| 3 | Best Appropriate Fix | fresh `gpt-xhigh` fix-decision dispatch | `${planning_dir}/rca/<failure-id>-fix-decision.md` | Phase 4 |
| 4 | Best Way To Apply | fresh `gpt-xhigh` application-plan dispatch | `${planning_dir}/rca/<failure-id>-application-plan.md` | Phase 5 |
| 5 | Apply | fresh `gpt-xhigh` apply dispatch | `${planning_dir}/rca/<failure-id>-applied.md` | Phase 6 |
| 6 | Verify-Or-Return Gate | `rca-orchestrator` | verification log | Phase 6.5 on green plus verification critic PASS, Phase 2 on red |
| 6.5 | Post-Apply Gate Set | apply-gate-set through rca-orchestrator | ${planning_dir}/rca/gate-set/<failure-id>/aggregate-report.md and join-manifest.json | downstream lifecycle only on PASS |
| 7+ | Downstream RCA lifecycle | existing specialist operators and ticket workflows | post-mortem, action items, runbooks, tracker comments, close record | complete or pending |

## Phase 0 - Trigger Classification

The orchestrator validates the input envelope and assigns the route. The `trigger_type` enum values are exactly `failing_test` and `incident`.

`incident` routes to Phase 1 because the workflow must create a concrete regression signal before root-cause work. `failing_test` routes to Phase 2 because the reproduction signal already exists and should not be replaced.

Phase 0 records `failure_id`, `trigger_evidence_path`, `repo_root`, `worktree_path`, `scratch_dir`, `planning_dir`, and any provided `trigger_command`. If the trigger cannot be classified as exactly one of the two enum values, stop with `BLOCKED:invalid-trigger-type`.

## Phase 1 - Reproduction Test

Phase 1 runs only for `incident`. It authors a real test under the worktree's `tests/` tree through a fresh test-writer invocation, then records the test path, node id, command, and incident evidence in `${planning_dir}/repro/<failure-id>.md`.

The reproduction test must be red on current `HEAD` before the fix and green after the fix. Red-run output is part of the Phase 1 artifact; a reproduction that cannot be made red is not silently accepted as root-cause evidence.

The orchestrator dispatches the test writer with `agents -m gpt-high -p ${worktree_path} -f <prompt-file>` or `agents -m gpt-xhigh -p ${worktree_path} -f <prompt-file>` as a fresh invocation. The prompt must not expose Phase 5 implementation details because no implementation exists yet.

If the incident description is too ambiguous to author a meaningful real test in the worktree, emit `NEEDS_INPUT:<absolute_artifact_path>` with the missing behavior question. If paths are unreadable or unwritable, stop with `BLOCKED:reproduction-test-unavailable`.

## Phase 2 - Root Cause

Phase 2 identifies the root cause only. Dispatch a fresh root-cause prompt with `agents -m gpt-xhigh -p ${worktree_path} -f <prompt-file>` and require it to read the failing test evidence or `${planning_dir}/repro/<failure-id>.md`, inspect the repository read-only, and write `${planning_dir}/rca/<failure-id>.md`.

The Phase 2 artifact names the failing signal, root cause, causal path, evidence references, and any ambiguity. It must NOT propose a fix; root cause and fix choice are separate decisions.

If the evidence cannot support a root-cause claim, stop with `NEEDS_INPUT:<absolute_artifact_path>` or `BLOCKED:root-cause-unproven` rather than inventing a cause.

## Phase 3 - Best Appropriate Fix

Phase 3 selects the best appropriate fix from the root-cause artifact. Dispatch a fresh fix-decision prompt with `agents -m gpt-xhigh -p ${worktree_path} -f <prompt-file>` and require it to read `${planning_dir}/rca/<failure-id>.md`, compare viable fixes, and write `${planning_dir}/rca/<failure-id>-fix-decision.md`.

The Phase 3 artifact explains why the selected fix addresses the root cause and why rejected options are worse. It must NOT determine the application strategy and must NOT apply code changes.

If the fix decision depends on product judgment or an unacceptable tradeoff, emit `NEEDS_INPUT:<absolute_artifact_path>`.

## Phase 4 - Best Way To Apply

Phase 4 plans how to apply the selected fix. Dispatch a fresh application-plan prompt with `agents -m gpt-xhigh -p ${worktree_path} -f <prompt-file>` and require it to read the root-cause and fix-decision artifacts, inspect local code as needed, and write `${planning_dir}/rca/<failure-id>-application-plan.md`.

The Phase 4 artifact names the files to change, order of edits, verification command, rollback or recovery notes when useful, and constraints for avoiding unrelated changes. It must NOT apply the change.

If the plan exposes a larger implementation scope than the RCA loop can safely own, emit `NEEDS_INPUT:<absolute_artifact_path>` or hand off to the implementation pipeline before Phase 5.

## Phase 5 - Apply

Phase 5 applies the Phase 4 plan through a fresh apply prompt with `agents -m gpt-xhigh -p ${worktree_path} -f <prompt-file>`. The apply invocation edits `${worktree_path}` only according to `${planning_dir}/rca/<failure-id>-application-plan.md` and writes `${planning_dir}/rca/<failure-id>-applied.md`.

After apply, the orchestrator runs an independent changed-path check such as `git -C ${worktree_path} diff --name-only` and fails with `BLOCKED:out-of-scope-apply-paths` if any path is outside the approved RCA application scope.

Phase 5 applies the Phase 4 plan and does not re-decide root cause or fix. If the plan proves impossible, Phase 5 records the failed application evidence and returns to Phase 4 or emits `NEEDS_INPUT:<absolute_artifact_path>`; it does not silently choose a new fix.

## Phase 6 - Verify-Or-Return Gate

Phase 6 re-runs the original failing or reproduction test from the trigger evidence or `${planning_dir}/repro/<failure-id>.md`. The rerun is targeted: it verifies the signal that justified the RCA loop before any broader downstream work.

If the rerun is red, return to Phase 2 with the new failure output attached to the RCA context.

If the rerun is green, preserve the passing command, output, applied artifact reference, and original-signal verification artifact, then run the Verification-phase critic. Only a current `VERIFICATION-CRITIC: PASS` advances to Phase 6.5; it does not advance directly to downstream lifecycle.

## Phase 6.5 — Post-Apply Gate Set

Phase 6.5 dispatches `apply-gate-set` through `rca-orchestrator` in `caller_mode=rca-post-apply` after Phase 5 changed-path check PASS, Phase 6 original-signal rerun GREEN, and Verification-phase critic PASS. The dispatch prompt lives at `${scratch_dir}/prompts/<failure-id>-apply-gate-set.md`, the durable log lives at `${scratch_dir}/logs/<failure-id>-apply-gate-set.log`, and the canonical output root is `${planning_dir}/rca/gate-set/<failure-id>/`.

The gate prompt supplies root-cause, fix-decision, application-plan, applied-artifact, original-signal verification, verification-critic, actual-diff, runtime-claim, scope, cycle id, audit-history, currentness, output-path, and process-tree inputs when required. Required output paths are `dispatch-manifest.md`, `join-manifest.json`, `aggregate-report.md`, `child-report-index.md`, `expected-process.json`, `process-tree-report.md` or `process-tree-not-applicable.md`, and optional `ticket-comment-payload.md` when a tracker mirror is requested.

Downstream lifecycle is blocked unless the returned gate-set status is `PASS` and the join manifest has no unresolved missing, stale, malformed, unsupported, non-LOW, unratified, invalid skip, bootstrap-exception, inventory-resolution, or process-tree blocking rows. Currentness decisions and stale-refusal records are delegated to `~/ai/conventions/apply-gate-set-currentness.md` § `Invalidation trigger matrix` and § `Stale-refusal records`. `BLOCKED`, `NEEDS_INPUT`, `MEDIUM`, `HIGH`, and `STALE_REFUSAL` all stop before Phase 7 and follow the operator-returned repair route. RCA records the returned manifest path, aggregate path, blocking rows, exception rows, inventory-resolution rows, currentness key, decision, and repair route in audit-history metadata.

## Phase 7 - Post-Mortem Authoring

Phase 7 starts the downstream RCA lifecycle only after current Phase 6.5 `PASS`, or after a human explicitly asks for downstream documentation from a halted state. Dispatch `~/ai/agents/post-mortem-author.md` when incident context, root-cause evidence, applied-fix evidence, and the gate-set aggregate are sufficient. The post-mortem output is `${planning_dir}/post-mortem.md`.

Post-mortem authoring remains a synthesis step; it does not reopen root cause, change the applied fix, replace the verification gate, or replace Phase 6.5 gate-set evidence.

## Phase 8 - Action-Item Tickets

Phase 8 files or indexes action-item tickets from the RCA, fix-decision, application-plan, applied artifact, Phase 6.5 gate-set aggregate, and post-mortem. It requires current Phase 6.5 `PASS`. Implementation-worthy action-item work hands off to `~/ai/agents/implementation-pipeline-orchestrator.md` and later PR review rather than being solved inside the RCA downstream phase.

Write `${planning_dir}/action-items.md` with severity, owner or ticket key, disposition, implementation-pipeline handoff bundle when applicable, and any audit or PR review expectations for child work.

## Phase 9 - Runbooks

Phase 9 produces or routes runbooks for unverifiable, operational, customer-side, or follow-up factors that cannot be closed by the applied code fix. It requires current Phase 6.5 `PASS`. Runbook outputs live under `${planning_dir}/runbooks/` unless a project-owned docs destination is supplied.

Runbooks name the factor, trigger, manual verification, rollback or escalation path, and link back to the RCA evidence.

## Phase 10 - Tracker Comments

Phase 10 posts or records tracker-comment evidence after findings, the Phase 6.5 gate-set aggregate, post-mortem, action-item tickets, runbooks, and implementation-pipeline handoffs are known. It requires current Phase 6.5 `PASS`. Use the existing Linear or Jira operator for tracker comments; file-only runs write the comment body under `${planning_dir}/tracker-comments/`.

The tracker comment summarizes the RCA, links the post-mortem, names action-item tickets and implementation-pipeline or PR review handoffs, and records pending runbook or customer-owned work.

## Phase 11 - Close Or Stay Open

Phase 11 writes `${planning_dir}/rca-close.md` with the close-or-pending decision. The incident can close only when RCA artifacts are complete, current Phase 6.5 `PASS` is recorded, the tracker-comment path is recorded, and no required severe action-item, runbook, or implementation-pipeline handoff is blocking closure.

If implementation, PR review, runbook, or tracker ownership remains pending, the RCA artifacts may be complete while the incident stays open or pending. Human-owned status transitions remain human-owned.

## Resume And Currentness

Resume verifies durable artifacts before skipping a phase. A supplied reproduction test can skip Phase 1 only when `trigger_type=failing_test` and the failing command or node id is known. Existing root-cause, fix-decision, application-plan, or applied artifacts may be reused only when the orchestrator records why they remain current for the active trigger.

Gate-set currentness is stricter than local RCA artifact reuse. Phase 6.5 currentness keys follow `~/ai/conventions/apply-gate-set-currentness.md` § `Currentness key schema`. When the convention's invalidation triggers fire, including Phase 2 re-entry, Phase 3 revision, Phase 4 revision, Phase 5 re-apply, Phase 6 verification repair, scope expansion, rebase, verification repair, or substantive contract/test revision, the prior `${planning_dir}/rca/gate-set/<failure-id>/join-manifest.json` is stale for downstream lifecycle until `apply-gate-set` reruns or re-verifies it for the active identity per § `Row-level re-verification` or § `Full re-dispatch`. A `STALE_REFUSAL` is a blocking state; RCA follows the returned `next_action` and may not decide currentness locally.

## Stop Conditions

- Success / verified: the original failing or reproduction test is green, Verification-phase critic is PASS, Phase 6.5 `apply-gate-set(caller_mode=rca-post-apply)` is PASS, and the workflow advances to Phase 7+ or completes downstream lifecycle work.
- `NEEDS_INPUT:<absolute_artifact_path>`: human-owned behavior, product tradeoff, tracker, close-policy, or evidence question is required.
- `BLOCKED:<reason>`: required inputs are missing or unreadable, artifact roots are unwritable, child invocations cannot produce required outputs, verification cannot run, or Phase 6.5 returns unresolved missing, stale, malformed, unsupported, non-LOW, unratified, invalid skip, process-tree, or gate-set blocking rows.
- `STALE_REFUSAL`: Phase 6.5 cannot prove currentness for the active cycle/head/diff/scope/runtime-claim identity; downstream lifecycle is blocked until the returned repair route is satisfied.

## Anti-Scope

- Do not edit `workflows/rca-prototype.md` or `agents/prototype-rca-orchestrator.md`.
- Do not edit `agents/incident-investigator.md`, `agents/behavior-investigator.md`, or `agents/post-mortem-author.md`.
- Do not introduce machine-enforcement framing.
- Do not delete the downstream lifecycle; it remains Phase 7+.
- Do not replace implementation-pipeline, CodeRabbit, PR-review, proof-risk, validation-integrity, process-tree, Linear, or Jira operator gates.
- Do not treat ticket comments as canonical gate evidence; comments are mirrors of file-backed Phase 6.5 artifacts.

## Cross-References

- `~/ai/agents/rca-orchestrator.md`: procedural owner for this workflow.
- `~/ai/workflows/rca-prototype.md`: separate light prototype RCA loop.
- `~/ai/agents/incident-investigator.md`: evidence-backed production incident investigation, composed when downstream findings are needed.
- `~/ai/agents/behavior-investigator.md`: behavior research operator, not redefined by this workflow.
- `~/ai/agents/post-mortem-author.md`: post-mortem synthesis for Phase 7.
- `~/ai/agents/implementation-pipeline-orchestrator.md`: action-item implementation handoff target.
- `~/ai/workflows/implementation-pipeline.md`: downstream implementation lifecycle.
- `~/ai/workflows/pr-review.md`: downstream PR review surface.
