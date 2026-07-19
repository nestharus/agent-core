---
eval_id: acr-279-dispatcher-pre-dispatch-protocol
behavior_class: Dispatcher pre-dispatch contract read protocol rollout
lifecycle_state: WRITE
severity_when_fires: HIGH
evidence_source_kinds:
  - agents-trace-json
  - dispatch-prompt
  - agent-log
  - audit-bundle
  - process-tree-audit
  - workflow-report
  - markdown-file
suggested_action_class: add-dispatcher-pre-dispatch-protocol
---

# ACR-279 Dispatcher Pre-Dispatch Protocol

## Eval identity

This WRITE-state eval spec defines the future structural-verification contract for ACR-279 dispatcher rollout of the common pre-dispatch read protocol. Source authority is `/home/nes/ai/planning/acr-279-operator-contract-rollout/contracts/acr-279-operator-contract-rollout.md` sections 1, 3, 5, 6, 8, and 11, the proposal, the problem map, the hookpoint research, `/home/nes/ai/conventions/evals.md`, and `/home/nes/ai/agents/operator-file-format.md`.

Structural-verification claim: every dispatcher in scope explicitly performs the same contract-read protocol before invoking or handing off to a sub-operator, and dispatch prompt composition is limited to inputs, task variant, anti-scope, stop conditions, and evidence paths.

## Lifecycle state

WRITE.

This spec is not a runnable detector and does not define pytest tests, verifier scripts, CLI wiring, or enforcement rollout.

## Declared roles

`validator`, `mapper`

## Inputs the auditor reads

The future auditor reads these dispatcher procedure sections:

| Dispatcher file | Procedure surface |
|---|---|
| `/home/nes/ai/agents/implementation-pipeline-orchestrator.md` | Existing ACR-278 priority-0 pre-dispatch wording used as canonical comparison. |
| `/home/nes/ai/agents/feature-orchestrator.md` | Per-ticket implementation-pipeline and PR-writer dispatches. |
| `/home/nes/ai/agents/refactoring-orchestrator.md` | Bounded implementation-pipeline handoff. |
| `/home/nes/ai/agents/refactoring-commit-history-orchestrator.md` | Refactoring-orchestrator package handoff. |
| `/home/nes/ai/agents/release-orchestrator.md` | Cut, hotfix, promote, reconcile, and ticket evidence dispatches. |
| `/home/nes/ai/agents/release-cut-operator.md` | Ticket/runbook evidence handoff. |
| `/home/nes/ai/agents/release-hotfix-operator.md` | Release child/ticket handoff guard if present. |
| `/home/nes/ai/agents/release-promote-operator.md` | Promotion/tag child handoff guard if present. |
| `/home/nes/ai/agents/release-reconcile-operator.md` | Reconcile child handoff guard if present. |
| `/home/nes/ai/agents/pr-review-operator.md` | Risk, research, test-audit, decomposition, and justification child dispatches. |
| `/home/nes/ai/agents/pr-justification-gauntlet.md` | Interrogator, researcher, value-assessor, and adjudicator round dispatches. |
| `/home/nes/ai/agents/agentsmd-maintenance-orchestrator.md` | Curator, reviewer, risk, and process-audit dispatches. |
| `/home/nes/ai/agents/workflow-process-auditor.md` | Process-tree audit consumption or handoff surface. |
| `/home/nes/ai/agents/coverage-expansion-operator.md` | Coverage, risk, behavior, trace, test-writer, and wrapper publish/render handoffs. |
| `/home/nes/ai/agents/test-audit-gate.md` | Spec-alignment, coverage-auditor, and coverage-analyzer dispatches. |
| `/home/nes/ai/agents/roadmap-orchestrator.md` | Research, proposer, risk, prototype, and ticket-generation dispatches. |
| `/home/nes/ai/agents/alignment-cycle-orchestrator.md` | Bootstrap, alignment, classify, and integrate dispatches. |
| `/home/nes/ai/agents/prototype-orchestrator.md` | P1/P2/P3/P4 child dispatches and ticket handoff. |
| `/home/nes/ai/agents/prototype-validation-orchestrator.md` | Validator, uploader, packager, proof-bundle, PR writer, and RCA dispatches. |
| `/home/nes/ai/agents/rca-orchestrator.md` | Reproduction, root-cause, fix, application, critic, proof, and handoff dispatches. |
| `/home/nes/ai/agents/prototype-rca-orchestrator.md` | Behavior/root-cause and fix dispatches. |
| `/home/nes/ai/agents/regression-investigator.md` | Commit-history, pattern-auditor, A1, and ticket-operator handoffs. |
| `/home/nes/ai/agents/wu-session-resumer.md` | Drift-checker and ticket-operator cross-link dispatches. |

## Unwanted behavior

The unwanted behavior is dispatcher drift where a dispatcher invokes, prompts, or hands off to a sub-operator without first resolving the selected operator path, preferring a current-project wrapper when declared, reading the selected `## Contract`, applying only declared defaults and secret sources, validating required inputs, refusing direct operations covered by `must_delegate`, and composing the child prompt only from the allowed call-surface material.

## Positive evidence

Positive evidence may include:

- A dispatcher procedure names a child operator invocation with no preceding contract-read protocol.
- The protocol omits wrapper preference, required-input validation, declared-default limitation, or `must_delegate` refusal.
- The dispatcher uses session metadata, ambient environment, or project assumptions as defaults without a selected contract declaring that source.
- A dispatch prompt includes child procedure mechanics, phase order, command recipes, or verdict handling.
- A dispatcher uses wording that materially diverges from the canonical implementation-pipeline pre-dispatch wording without preserving the same obligations.

## Non-fire cases

The eval must not fire on:

- Dispatchers that use a shared canonical reference instead of duplicating the full algorithm, provided the reference is explicit and uniformly applied.
- Operators with no actual child dispatch using the protocol as a guard for future handoff while keeping local mechanics local.
- Prompt text that includes task variant, required inputs, anti-scope, stop conditions, and evidence paths without child mechanics.
- ACR-278 priority-0 wording being used as the comparison baseline rather than re-authored.

## Pass/fail criteria

Pass: each dispatcher procedure contains the common pre-dispatch protocol or a uniform explicit reference to it before sub-operator invocation, and the protocol includes all six pre-prompt obligations plus the prompt-composition boundary.

Fail: any listed dispatcher lacks the protocol at a child dispatch surface, changes the obligation order in a way that allows direct operation or undeclared defaults, or permits child mechanics in prompts. The finding is `blocking` for dispatcher rollout acceptance. The `advisory` trivial-operator carve-out does not apply to dispatcher pre-dispatch protocol surfaces.

## Required trace fields

| Field | Description |
|---|---|
| `dispatcher_file` | Absolute path of the dispatcher under review. |
| `procedure_section` | Section or anchor containing the child dispatch surface. |
| `child_operator_refs` | Operators or workflows invoked by the dispatcher. |
| `protocol_presence` | Whether the common protocol or canonical reference is present. |
| `protocol_steps_present` | Observed set of protocol steps. |
| `wrapper_preference_status` | Whether current-project wrapper preference is declared. |
| `default_source_status` | Whether only declared defaults/secrets are allowed. |
| `required_input_validation_status` | Whether task inputs are validated after defaults. |
| `must_delegate_refusal_status` | Whether direct operations covered by `must_delegate` are refused. |
| `prompt_boundary_status` | Whether prompt composition excludes child mechanics. |

## Finding schema

Findings preserve the minimum fields from `conventions/evals.md`:

- `eval_id`
- `severity`
- `evidence_paths`
- `summary`
- `suggested_action`
- `confidence`

The finding schema also includes `dispatcher_file`, `procedure_section`, `child_operator_refs`, `protocol_presence`, `protocol_steps_present`, `wrapper_preference_status`, `default_source_status`, `required_input_validation_status`, `must_delegate_refusal_status`, and `prompt_boundary_status`.

`severity` is `HIGH` for missing or weakened protocol obligations and is treated as rollout `blocking`; `MEDIUM` is for ambiguous insertion evidence; `LOW` is for trace-adapter uncertainty.

## Suggested action

Return `add-dispatcher-pre-dispatch-protocol`. The caller should add the uniform protocol before child dispatch and remove any prompt mechanics that override child operator procedure.

## Coverage

| Scenario ID | Scenario |
|---|---|
| ACR279-DP-001 | Detect missing protocol before child dispatch. |
| ACR279-DP-002 | Detect missing wrapper preference, defaults, validation, or delegation refusal. |
| ACR279-DP-003 | Detect prompt composition that includes child mechanics. |
| ACR279-DP-004 | Verify uniform wording or canonical-reference use across all dispatcher targets. |
