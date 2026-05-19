---
eval_id: acr-278-ticket-operator-contract-resolution
behavior_class: Ticket operator contract resolution and dispatch boundary
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
suggested_action_class: revise-dispatcher-procedure
---

# ACR-278 Ticket Operator Contract Resolution

## Eval identity

This WRITE-state eval spec defines the future structural-verification contract for ACR-278 ticket-operator contract resolution, Jira credential default source handling, caller-prompt boundaries, implementation-pipeline ticket dispatches, the new no-override convention, and agents-cli pre-dispatch resolution. Source authority is the ACR-278 Step 6a contract, approved proposal R2 Test-Intent Track, problem map, coverage inventory, and `/home/nes/ai/conventions/evals.md`.

This spec covers UB-004, UB-007, UB-015, UB-020, UB-021, UB-022, UB-023, UB-024, UB-025, UB-026, UB-027, UB-028, UB-038, UB-039, and UB-040.

## Lifecycle state

WRITE.

Per `conventions/evals.md`, this file defines the behavior contract only. It does not provide runnable detector code, fixtures, parser adapters, CLI wiring, pytest tests, verifier scripts, or enforcement rollout.

## Unwanted behavior

The unwanted behavior is trace-detectable dispatcher or caller drift where ticket work bypasses contract resolution, starts with the base Jira operator when an in-scope project wrapper exists, fills Jira credential identity from session metadata, copies or overrides operator procedure in caller prompts, omits the canonical no-override convention, or constructs agents-cli dispatches before resolving and validating the selected operator contract.

The detector should fire when Phase 0, Phase 3 estimate update, Phase 8.5 or Phase 9 cross-link comments, final close comments, or agents-cli dispatch evidence show a resolution order other than project wrapper contract, then base operator contract, then `BLOCKED` or `NEEDS_INPUT`, with no session-metadata fallback for Jira credential identity.

The detector should also fire when a touched file lacks the file-local `## Declared roles` block required by the Step 6a contract or proposal Declared-roles plan, or when an existing file-local `## Declared roles` block was modified to a non-conforming role set during the WU edit. For `agents/implementation-pipeline-orchestrator.md`, the existing declared roles must be preserved as `orchestration`, `parser`, `validator`, and `formatter`.

## Positive evidence

Positive evidence may include:

- A caller prompt passes procedure text, alternative verdict thresholds, alternate error envelopes, or step ordering to an operator instead of contract-shaped inputs and evidence.
- Jira auth fields, especially `jira_account_email`, are read from session metadata or ambient caller state when a wrapper or base contract supplies or requires them.
- The RFQ wrapper defaults for `jira_url`, `jira_project`, or `jira_account_email` are ignored.
- Implementation-pipeline ticket-system selection accepts dual backends or fails to preserve the selected operator and resolved contract path.
- Ticket read/create, bug handoff, update-estimate, close-comment, or cross-link dispatches do not reference the resolved operator contract.
- `conventions/no-operator-behavior-override-in-dispatch.md` is absent or lacks the read-protocol and caller-prompt boundary.
- `workflows/agents-cli.md` lacks pre-dispatch contract resolution before canonical command construction.
- A Markdown parser detects that `conventions/no-operator-behavior-override-in-dispatch.md` or `workflows/agents-cli.md` lacks a file-local `## Declared roles` block, has a malformed role block, or has role-set drift relative to the expected role classifications from the Step 6a contract and proposal Declared-roles plan.
- A Markdown parser detects that `agents/implementation-pipeline-orchestrator.md` no longer preserves its existing file-local declared role set.

## Non-fire cases

The eval must not fire on:

- Caller prompts that provide only contract `inputs:`, evidence paths, task scope, anti-scope, stop conditions, or what-to-verify guidance.
- Dispatches that correctly choose an in-scope project wrapper and apply wrapper defaults before base defaults and caller inputs.
- `BLOCKED:missing-required-input` or `NEEDS_INPUT:<artifact>` when required inputs are absent after wrapper and base contract resolution.
- Non-credential session metadata used for bookkeeping fields outside the credential identity chain when the contract permits or does not name the field.
- Historical examples, tickets, or eval specs quoting bad prompt patterns without using them as live caller instruction.
- Files outside this spec's touched-component set for ACR-278 declared-role verification.
- A touched file whose `## Declared roles` block matches the contract's expected role set exactly, allowing only ordering tolerance consistent with `~/ai/conventions/code-quality.md` cohesion rules.

## Required trace fields

The future detector must read saved `agents trace --json` as the preferred boundary plus dispatch prompts, prompt paths, agent logs, markdown file snapshots, workflow reports, process-tree-audit reports, and audit bundles. It must extract:

| UB | Extension fields |
|---|---|
| UB-004 | `caller_prompt_path`, `operator_file`, `override_class`, `needs_input_evidence` |
| UB-007 | `operator_file`, `secret_refs`, `default_sources`, `account_email_source` |
| UB-015 | `wrapper_file`, `defaults`, `account_email_source`, `jira_url_source` |
| UB-020 | `orchestrator_file`, `ticket_system_inputs`, `selected_operator`, `dual_system_rejection` |
| UB-021 | `orchestrator_file`, `jira_input_source`, `session_metadata_used` |
| UB-022 | `phase`, `prompt_path`, `ticket_read_output`, `session_manifest_path` |
| UB-023 | `phase`, `bug_signal`, `ticket_payload`, `blocks_link` |
| UB-024 | `phase`, `update_estimate_prompt`, `estimate_fields`, `operator_contract_ref` |
| UB-025 | `phase`, `close_comment_prompt`, `calibration_line`, `status_transition_attempted` |
| UB-026 | `phase`, `project_scope`, `wrapper_contract_ref`, `base_contract_ref`, `resolution_order`, `session_metadata_used` |
| UB-027 | `convention_path`, `presence`, `read_protocol_paragraph_status` |
| UB-028 | `convention_path`, `allowed_dispatch_context_fields`, `procedure_prompt_leakage` |
| UB-038 | `agents_cli_path`, `prompt_log_conventions`, `contract_resolution_step_order` |
| UB-039 | `agents_cli_path`, `question_artifact_protocol`, `contract_validation_needs_input` |
| UB-040 | `agents_cli_path`, `selected_operator_path`, `contract_ref`, `default_application`, `delegation_boundary` |
| Declared roles | `touched_file`, `declared_roles_block_present`, `declared_roles_observed`, `declared_roles_expected`, `declared_roles_match` |

## Finding schema

Findings preserve the minimum fields from `conventions/evals.md`:

- `eval_id`
- `severity`
- `evidence_paths`
- `summary`
- `suggested_action`
- `confidence`

The finding schema also includes these exact per-behavior extension field sets:

| UB | Extension fields |
|---|---|
| UB-004 | `caller_prompt_path`, `operator_file`, `override_class`, `needs_input_evidence` |
| UB-007 | `operator_file`, `secret_refs`, `default_sources`, `account_email_source` |
| UB-015 | `wrapper_file`, `defaults`, `account_email_source`, `jira_url_source` |
| UB-020 | `orchestrator_file`, `ticket_system_inputs`, `selected_operator`, `dual_system_rejection` |
| UB-021 | `orchestrator_file`, `jira_input_source`, `session_metadata_used` |
| UB-022 | `phase`, `prompt_path`, `ticket_read_output`, `session_manifest_path` |
| UB-023 | `phase`, `bug_signal`, `ticket_payload`, `blocks_link` |
| UB-024 | `phase`, `update_estimate_prompt`, `estimate_fields`, `operator_contract_ref` |
| UB-025 | `phase`, `close_comment_prompt`, `calibration_line`, `status_transition_attempted` |
| UB-026 | `phase`, `project_scope`, `wrapper_contract_ref`, `base_contract_ref`, `resolution_order`, `session_metadata_used` |
| UB-027 | `convention_path`, `presence`, `read_protocol_paragraph_status` |
| UB-028 | `convention_path`, `allowed_dispatch_context_fields`, `procedure_prompt_leakage` |
| UB-038 | `agents_cli_path`, `prompt_log_conventions`, `contract_resolution_step_order` |
| UB-039 | `agents_cli_path`, `question_artifact_protocol`, `contract_validation_needs_input` |
| UB-040 | `agents_cli_path`, `selected_operator_path`, `contract_ref`, `default_application`, `delegation_boundary` |
| Declared roles | `touched_file`, `declared_roles_block_present`, `declared_roles_observed`, `declared_roles_expected`, `declared_roles_match` |

`severity` is `HIGH` when dispatch uses the wrong operator, uses session metadata for Jira credential identity, or follows caller-supplied procedure overrides; `MEDIUM` when contract resolution is incomplete but no credential or live procedure override evidence appears; and `LOW` only for incomplete evidence or future trace-adapter uncertainty.

## Suggested action

Return `revise-dispatcher-procedure`. The caller should update the implementation-pipeline orchestrator, no-override convention, or agents-cli workflow so every ticket dispatch resolves the selected operator contract first, applies wrapper then base defaults, refuses missing inputs with `BLOCKED` or `NEEDS_INPUT`, and keeps operator procedure out of caller prompts.

## Coverage

| UB | Scenario ID | Scenario |
|---|---|---|
| UB-004 | ACR278-TOCR-001 | Detect caller-prompt procedure override instead of `NEEDS_INPUT` or operator update. |
| UB-007 | ACR278-TOCR-002 | Verify Jira auth inputs and secrets are contract-sourced. |
| UB-015 | ACR278-TOCR-003 | Verify RFQ wrapper defaults protect Jira URL and account email. |
| UB-020 | ACR278-TOCR-004 | Preserve exactly-one ticket backend selection. |
| UB-021 | ACR278-TOCR-005 | Detect old caller/session-supplied Jira identity behavior. |
| UB-022 | ACR278-TOCR-006 | Preserve Phase 0 ticket read/create bootstrap artifacts. |
| UB-023 | ACR278-TOCR-007 | Preserve Phase 2.5.1 bug-discovery ticket handoff. |
| UB-024 | ACR278-TOCR-008 | Verify Phase 3 estimate writeback uses selected operator contract. |
| UB-025 | ACR278-TOCR-009 | Verify final close comment is contract-bound and status-neutral. |
| UB-026 | ACR278-TOCR-010 | Verify project wrapper > base operator > blocked/input resolution order. |
| UB-027 | ACR278-TOCR-011 | Verify no-override convention exists with read protocol. |
| UB-028 | ACR278-TOCR-012 | Verify dispatch prompts contain contract inputs, not procedure leakage. |
| UB-038 | ACR278-TOCR-013 | Verify agents-cli prompt/log convention survives contract resolution. |
| UB-039 | ACR278-TOCR-014 | Verify contract-validation questions use question artifacts. |
| UB-040 | ACR278-TOCR-015 | Verify agents-cli pre-dispatch contract resolution and delegation boundary. |
| Declared roles | ACR278-TOCR-DR-001 | Verify `conventions/no-operator-behavior-override-in-dispatch.md` declares `orchestration` and `validator`. |
| Declared roles | ACR278-TOCR-DR-002 | Verify `workflows/agents-cli.md` declares `orchestration`, `validator`, and `formatter`. |
| Declared roles | ACR278-TOCR-DR-003 | Verify `agents/implementation-pipeline-orchestrator.md` preserves `orchestration`, `parser`, `validator`, and `formatter`. |
