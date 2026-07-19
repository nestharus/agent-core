---
eval_id: coupling-auditor-intrinsic-surface
behavior_class: Coupling-auditor intrinsic-surface A1 mis-application
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

# Coupling-Auditor Intrinsic-Surface A1

## Eval identity

This is a markdown behavior specification for `coupling-auditor-intrinsic-surface`, not runnable eval code. It defines a future detector shaped as `trace -> finding | None` for intrinsic-surface-aware A1 coupling verdicts that ignore explicit intrinsic-surface declarations, infer intrinsic-surface status without a declaration, weaken the existing undeclared coupling threshold, or use intrinsic-surface language as residual acceptance for a non-LOW coupling/code-quality gate.

References: `~/ai/conventions/evals.md`, `~/ai/agents/coupling-auditor.md`, `~/ai/conventions/code-quality.md`, the ACR-205 intrinsic-surface contract, and `~/ai/evals/coupling-auditor-adapter/eval.md` as the sister precedent.

## Unwanted behavior

The unwanted behavior is any trace-backed coupling-auditor verdict or convention/operator revision that shows one of these intrinsic-surface A1 mis-applications:

- (a) `ignore-declaration`: The verdict ignores an explicit valid `intrinsic_surface_declarations:` entry in the resolved declaration carrier, either `## Intrinsic-surface declarations` in `contract_path` or `## Intrinsic-surface declarations` in `proposal_path`, and scores the declared intrinsic-surface pair by raw distinct symbols/modules instead of the declared domain boundary.
- (b) `auto-declare`: The verdict auto-declares intrinsic-surface status without an explicit `## Intrinsic-surface declarations` entry naming the component. Intrinsic-surface status must be explicit; inferred status from component names, narrative claims, file paths, domain vocabulary, or raw-reference counts is unwanted behavior.
- (c) `weakened-non-declared-threshold`: The verdict scores undeclared sprawl LOW despite `>= 6` distinct external symbols/modules. The intrinsic-surface extension must not silently weaken the preserved raw A1 threshold rule for non-declared pairs.
- (d) `over-threshold-low`: The verdict scores a declared intrinsic surface LOW when it covers more than `N = 5` named `Domain:` entries, contradicting the intrinsic-surface threshold rule.
- (e) `non-subordinate-low`: The verdict scores a declared intrinsic surface LOW when references reach symbols, operations, contracts, or modules outside the declared `Owns:` set, allowing non-subordinate sprawl to masquerade as an intrinsic domain surface.
- (f) `mirror-drift`: `~/ai/conventions/code-quality.md` and `~/ai/agents/coupling-auditor.md` drift on intrinsic-surface carrier shape, role name, `Domain:`, `Owns:`, `N = 5`, subordinate-reference rule, malformed-declaration disposition, or preserved raw thresholds.
- (g) `non-low-residual-acceptance`: Intrinsic-surface language is used as residual acceptance for a Phase 4 / Phase 6 / Phase 8 coupling/code-quality non-LOW verdict instead of producing a real LOW metric result or blocking/remediating the gate.

## Positive evidence

The future eval implementation consumes evidence by role from a saved trace bundle. Positive evidence may appear in saved `agents trace --json`, dispatch prompts, agent logs, audit bundles, process-tree-audit reports, coupling-auditor reports, or code-quality aggregate reports.

Positive evidence includes one or more of these shapes:

- The dispatch prompt names `proposal_path` and/or `contract_path`, and the resolved declaration carrier contains `## Intrinsic-surface declarations` with the component, `role: intrinsic-surface`, exactly one `Domain:` value per entry, and a non-empty `Owns:` set.
- The auditor report's per-pair table omits or contradicts intrinsic-surface evidence columns for declaration artifact path, declared intrinsic component, `Domain:`, `Owns:` set, domain count, intrinsic-surface verdict, or final verdict.
- The auditor's per-pair scoring counts raw symbols/modules for a component that the resolved declaration carrier explicitly names as `role: intrinsic-surface`.
- The trace shows intrinsic-surface status assigned without any declaration carrier entry naming the component.
- The per-pair scoring gives LOW to an undeclared pair with `>= 6` distinct external symbols/modules.
- The per-pair scoring gives LOW to a declared intrinsic surface with more than 5 named `Domain:` entries, or to a declared intrinsic surface with external references outside the declared `Owns:` set.
- The parser or report evidence treats a malformed `intrinsic_surface_declarations:` entry as LOW, MEDIUM, HIGH, or implicit fallback instead of stopping as `BLOCKED:malformed-intrinsic-surface-declaration:<component>:<reason>` or `NEEDS_INPUT`.
- Convention revision evidence for `~/ai/conventions/code-quality.md`, such as a git diff or content snapshot, can be compared with auditor prompt/report evidence for `~/ai/agents/coupling-auditor.md` and any coupling-auditor report path to show mismatched intrinsic-surface carrier shape, role name, `Domain:` / `Owns:` fields, threshold, subordinate-reference requirement, malformed-declaration disposition, or preserved raw thresholds.
- Code-quality aggregate evidence plus process-tree or audit-bundle paths show which mirrored rule surfaces were consulted and whether the convention and auditor prompt/report evidence diverged during the same WU, review, or gate.
- A question artifact answers acceptance of a Phase 4 / Phase 6 / Phase 8 coupling-auditor non-LOW verdict, a join manifest includes a `bootstrap_exception=true` or `allow-advance` row for a non-LOW coupling/code-quality verdict outside the narrow convention-permitted path, or a matching DECISIONS entry cites intrinsic-surface language as the reason to advance without a real LOW metric result.

## Non-fire cases

- Valid `intrinsic_surface_declarations:` entry covering `<= 5` named domains with all references subordinate to `Owns:` scoring LOW.
- Undeclared sprawl scoring HIGH at `>= 6` distinct external symbols/modules.
- Non-declared pair scoring MEDIUM at `3-5` distinct references.
- Malformed `intrinsic_surface_declarations:` returning `BLOCKED:malformed-intrinsic-surface-declaration:<component>:<reason>` or `NEEDS_INPUT`. That is a healthy stop condition, not this eval's unwanted behavior.
- Coordinated lockstep edits to `~/ai/conventions/code-quality.md` and `~/ai/agents/coupling-auditor.md` with no semantic drift.
- Cosmetic markdown formatting changes outside the intrinsic-surface carrier, threshold, counting, subordinate-reference, malformed-disposition, and non-declared threshold rule sections.
- Adapter declarations continuing to use the adapter branch only, with `adapter_declarations:`, `role: adapter`, and `Translates:` remaining translation-only and not cross-contaminating intrinsic-surface behavior.
- A stable MEDIUM accepted under an active WU's approved risk disposition with cited audit-history evidence, where that acceptance is the convention-permitted narrow MEDIUM acceptance and not a coupling/code-quality pipeline gate bypass.

## Required trace fields

The future eval implementation must read evidence by semantic role, not by raw storage schema. Required roles are:

- WU scope, including WU ID, selected level when recursive, and whether the scope is markdown-only, prompt/convention, product-code, or deployment-level.
- Diff paths and changed file classifications.
- Dispatch prompt path and content for the coupling-auditor or code-quality invocation.
- Auditor report path, including per-pair finding IDs and intrinsic-surface scoring evidence.
- Finding IDs from the auditor report and any code-quality aggregate.
- Intrinsic-surface declaration carrier path, resolved from `contract_path` when present or `proposal_path` when no contract is supplied.
- Declared intrinsic-surface component path or component name for each declaration entry.
- Declared `Domain:` value for each component named by the intrinsic-surface declaration.
- Declared `Owns:` set for each component named by the intrinsic-surface declaration.
- Declared domain count for each component and whether that count is `<= 5` or `> 5`.
- Evidence that every scored external reference is subordinate to the declared `Owns:` set, or evidence naming the non-subordinate references.
- Raw distinct symbol/module count for non-declared pairs so preserved LOW `0-2`, MEDIUM `3-5`, and HIGH `>= 6` thresholds remain visible.
- Code-quality disposition and whether the auditor verdict controlled a LOW-only gate or was companion evidence.
- Manager authorization path for any residual acceptance, override, or non-LOW disposition.
- Convention revision evidence for `~/ai/conventions/code-quality.md`, including diff path or content snapshot path.
- Auditor prompt/report evidence for `~/ai/agents/coupling-auditor.md`, including prompt snapshot, report path, and any code-quality aggregate report that consumed the auditor result.
- Lockstep-edit witnesses showing whether the convention and auditor were edited together and whether the same intrinsic-surface clause changed in both files.
- Question artifact path, DECISIONS path, join manifest path, and process-tree audit findings for any non-LOW coupling/code-quality gate acceptance.
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
- `intrinsic_surface_declarations_path`
- `declared_intrinsic_component`
- `declared_domain`
- `declared_owns`
- `domain_count`
- `non_subordinate_references`
- `manager_authorization_path`
- `convention_revision_evidence_path`
- `auditor_prompt_report_evidence_path`
- `lockstep_edit_witnesses`
- `question_artifact_path`
- `decisions_path`
- `join_manifest_path`
- `process_tree_audit_findings`
- `unwanted_case`

`unwanted_case` must be one of `ignore-declaration`, `auto-declare`, `weakened-non-declared-threshold`, `over-threshold-low`, `non-subordinate-low`, `mirror-drift`, or `non-low-residual-acceptance`.

## Suggested action

Return `revise-proposal` when the future eval-runner returns a finding. The owning workflow should route the WU to remediation that revises the proposal, coupling-auditor prompt, or `~/ai/conventions/code-quality.md` intrinsic-surface declaration text, then reruns the relevant code-quality and eval evidence path. If the finding depends on a manager override, residual acceptance, or repeated churn, escalate to manager review before accepting the gate result.

## Lifecycle notes

This eval ships in `WRITE` state. No `eval.py` or `eval.rs` is required to exist in this WU.

Downstream implementation tickets own runnable detector code, fixtures, advisory rollout, false-positive review, and any CI or agent-runner runtime wiring. This spec must not create fixtures, create an advisory rollout, add a CI hook, edit `AGENTS.md` routing, edit `workflows/index.json`, wire Jira or Linear automation, wire agent-runner runtime behavior, revive structural markdown tests, or create `tools/<wu>-verify/` verification scripts.
