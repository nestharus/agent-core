---
eval_id: coupling-auditor-adapter
behavior_class: Coupling-auditor adapter-aware A1 mis-application
lifecycle_state: WRITE
severity_when_fires: HIGH
evidence_source_kinds:
  - agents-trace-json
  - dispatch-prompt
  - agent-log
  - audit-bundle
  - process-tree-audit
suggested_action_class: revise-proposal
---

# Coupling-Auditor Adapter-Aware A1

## Eval identity

This is a markdown behavior specification for `coupling-auditor-adapter`, not runnable eval code. It defines a future detector shaped as `trace -> finding | None` for adapter-aware A1 coupling verdicts that either ignore explicit adapter declarations or weaken the existing non-adapter coupling threshold.

References: `~/ai/conventions/evals.md`, `~/ai/agents/coupling-auditor.md`, `~/ai/conventions/code-quality.md`, the ACR-174 deletion contract, the ACR-175 eval framework, and ACR-199 as the cleanup ticket for `tools/<wu>-verify/` smuggling regressions.

## Unwanted behavior

The unwanted behavior is any trace-backed coupling-auditor verdict that shows one of these adapter-aware A1 mis-applications:

- (a) The verdict ignores an explicit `role: adapter` plus `Translates:` declaration when one is present in the resolved declaration carrier, either `## Adapter declarations` in `contract_path` or `## Adapter declarations` in `proposal_path`, and scores the declared adapter pair using raw distinct symbols/modules instead of distinct contracts. This is the ACR-142 false-positive pattern.
- (b) The verdict auto-declares a component as `role: adapter` without an explicit `## Adapter declarations` entry naming that component. Adapter status must be explicit; inferred adapter status is unwanted behavior.
- (c) The verdict fails to keep non-adapter pairs HIGH at `>= 6` distinct external symbols/modules. The adapter-aware extension must not silently weaken the existing non-adapter threshold rule.
- (d) The verdict scores a declared adapter LOW when it bridges more than 5 distinct named external contracts in `Translates:`, contradicting the `N=5` threshold rule.
- (e) The verdict scores a declared adapter LOW when the component reaches undeclared external contracts that are not subordinate to `Translates:`, allowing sprawl to masquerade as an adapter.
- (f) A coupling-auditor or convention/auditor revision introduces drift between `~/ai/conventions/code-quality.md` and `~/ai/agents/coupling-auditor.md` on adapter carrier shape (`adapter_declarations:`, `role: adapter`, `Translates:`), adapter threshold `N=5`, the distinct-contract counting rule, the subordinate-reference requirement, malformed-declaration disposition, or the preserved non-adapter thresholds (LOW `0-2` / MEDIUM `3-5` / HIGH `>= 6`).
- (g) A coupling-auditor pipeline re-introduces Non-LOW gate residual acceptance: an answered question artifact or DECISIONS entry converts a Phase 4 / Phase 6 / Phase 8 coupling-auditor HIGH or MEDIUM into an `allow-advance` path by labelling it `bootstrap_exception_recommended`, `intrinsic-structural-lockstep`, or any other residual rationale. The named anti-pattern is in `~/ai/conventions/workflow-execution-violations.md` § Non-LOW gate residual acceptance and `~/ai/conventions/code-quality.md` § Disposition policy, where only LOW passes pipeline-callable code-quality gates.

## Positive evidence

The future eval implementation consumes evidence by role from a saved trace bundle. Positive evidence may appear in saved `agents trace --json`, dispatch prompts, agent logs, audit bundles, process-tree-audit reports, coupling-auditor reports, or code-quality aggregate reports.

Positive evidence includes one or more of these shapes:

- The dispatch prompt names `proposal_path` and/or `contract_path`, and the resolved declaration carrier contains `## Adapter declarations` with the component, `role: adapter`, and a `Translates:` set.
- The auditor report's per-pair table omits or contradicts adapter evidence columns for declaration artifact path, component, `Translates:` contracts, contract count, or adapter verdict.
- The auditor's per-pair scoring counts raw symbols/modules for a component that the resolved declaration carrier explicitly names as `role: adapter`.
- The trace shows adapter status assigned without any declaration carrier entry naming the component.
- The per-pair scoring gives LOW to a non-adapter pair with `>= 6` distinct external symbols/modules.
- The per-pair scoring gives LOW to a declared adapter with more than 5 named `Translates:` contracts, or to a declared adapter with external references outside the declared translated surfaces.
- Convention revision evidence for `~/ai/conventions/code-quality.md`, such as a git diff or content snapshot, can be compared with auditor prompt/report evidence for `~/ai/agents/coupling-auditor.md` and any coupling-auditor report path to show mismatched adapter carrier shape, adapter threshold, distinct-contract counting, subordinate-reference requirements, or non-adapter thresholds.
- Code-quality aggregate evidence plus process-tree or audit-bundle paths show which mirrored rule surfaces were consulted and whether the convention and auditor prompt/report evidence diverged during the same WU, review, or gate.
- A question artifact answers acceptance of a Phase 4 / Phase 6 / Phase 8 coupling-auditor non-LOW verdict, a join manifest includes a `bootstrap_exception=true` or `allow-advance` row for a non-LOW coupling/code-quality verdict, or a matching DECISIONS entry cites the gate self-recommendation as the reason to advance.

## Non-fire cases

- A declared adapter bridging `<= 5` named contracts and keeping all external references subordinate to `Translates:` scores LOW.
- A sprawl component without a `## Adapter declarations` entry scores HIGH at `>= 6` distinct symbols.
- A non-adapter pair scores MEDIUM at `3-5` distinct symbols.
- The coupling-auditor returns `BLOCKED` or `NEEDS_INPUT` on malformed declarations. That is a healthy stop condition, not this eval's unwanted behavior.
- Coupling reports are used only as companion evidence without controlling a gate.
- Coordinated lockstep edits where both `~/ai/conventions/code-quality.md` and `~/ai/agents/coupling-auditor.md` update the same adapter clause without semantic divergence.
- Cosmetic markdown formatting changes outside the adapter carrier, adapter threshold, distinct-contract counting, subordinate-reference, and non-adapter threshold rule sections.
- Eval-runner outputs used only as companion evidence.
- A stable MEDIUM accepted under the active WU's approved risk disposition with cited audit-history evidence, where the acceptance is the convention-permitted narrow MEDIUM acceptance and not a coupling/code-quality pipeline gate bypass.
- Manager-flavor-specific MEDIUM acceptance that does not apply to coupling/code-quality pipeline gates.

## Required trace fields

The future eval implementation must read evidence by semantic role, not by raw storage schema. Required roles are:

- WU scope, including WU ID, selected level when recursive, and whether the scope is markdown-only, prompt/convention, product-code, or deployment-level.
- Diff paths and changed file classifications.
- Dispatch prompt path and content for the coupling-auditor or code-quality invocation.
- Auditor report path, including per-pair finding IDs and adapter-aware scoring evidence.
- Finding IDs from the auditor report and any code-quality aggregate.
- Adapter-declaration carrier path, resolved from `contract_path` when present or `proposal_path` when no contract is supplied.
- Declared `Translates:` set for each component named by the adapter declaration.
- Code-quality disposition and whether the auditor verdict controlled a LOW-only gate or was companion evidence.
- Manager authorization path for any residual acceptance, override, or non-LOW disposition.
- Convention revision evidence for `~/ai/conventions/code-quality.md`, including diff path or content snapshot path.
- Auditor prompt/report evidence for `~/ai/agents/coupling-auditor.md`, including prompt snapshot, report path, and any code-quality aggregate report that consumed the auditor result.
- Lockstep-edit witnesses showing whether the convention and auditor were edited together and whether the same adapter clause changed in both files.
- Question artifact path, DECISIONS path, join manifest path, and process-tree audit findings for any non-LOW coupling/code-quality gate acceptance, especially `P4-001` / `P4-002` shape.
- Churn-round count, including revise loops caused by the same finding or finding family.

The preferred boundary is saved `agents trace --json` plus audit bundles, joined with prompt paths, report paths, invocation UUIDs, parent invocation IDs, and process-tree-audit evidence per `~/ai/conventions/evals.md` `## Trace bundle contract`.

## Finding shape

The finding preserves the minimum schema fields from `~/ai/conventions/evals.md`:

- `eval_id`
- `severity`
- `evidence_paths`
- `summary`
- `suggested_action`
- `confidence`

Allowed extension fields are:

- `auditor`
- `finding_ids`
- `diff_paths`
- `churn_rounds`
- `scope_type`
- `adapter_declarations_path`
- `declared_translates`
- `manager_authorization_path`
- `convention_revision_evidence_path`
- `auditor_prompt_report_evidence_path`
- `lockstep_edit_witnesses`
- `question_artifact_path`
- `decisions_path`
- `join_manifest_path`
- `process_tree_audit_findings`
- `unwanted_case`

`unwanted_case` must be one of `ignore-declaration`, `auto-declare`, `weakened-non-adapter-threshold`, `over-threshold-low`, `sprawl-low`, `mirror-drift`, or `non-low-residual-acceptance`.

## Suggested action

Return `revise-proposal` when the future eval-runner returns a finding. The owning workflow should route the WU to remediation that revises the proposal, coupling-auditor prompt, or `~/ai/conventions/code-quality.md` adapter-declaration text, then reruns the relevant code-quality and eval evidence path. If the finding depends on a manager override, residual acceptance, or repeated churn, escalate to manager review before accepting the gate result.

## Lifecycle notes

This eval ships in `WRITE` state. No runnable detector is required to exist in this WU.

Downstream implementation tickets own `eval.py` or `eval.rs`, fixtures, advisory rollout in `ROLL_OUT`, false-positive review, and `ENFORCE` readiness. This spec must not become a structural markdown test or wire itself into `AGENTS.md`, `workflows/index.json`, CI, cron, Jira, Linear, or agent-runner runtime code.
