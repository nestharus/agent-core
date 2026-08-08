---
workflow:
  id: refactoring
workflow_aliases:
  - alias: refactor
    target:
      workflow_id: refactoring
      path: workflows/refactoring.md
workflow_dispatch_contract:
  orchestrator: refactoring-orchestrator
  inputs:
    - "exactly one ticket source: jira_issue_key, linear_issue_key, or canonical wu_brief_path"
    - "required backend selection/configuration: ticket_system plus jira_url, jira_project, and jira_account_email for Jira, or linear_team_key and optional linear_project_id for Linear"
    - "required coordination inputs: target_list, repo_root, unique branch_name and canonical absolute worktree_path/planning_dir/scratch_dir for the sole child, exact short trunk_branch and integration_branch_ref, canonical JSON protected_branches including both, and slice_bounds; invocation UUID is derived from runner provenance"
    - "optional inputs: local_coverage_command required and non-blank for feature-routed calls, wu_brief_context_path valid only with an existing issue key, shim_placement_parameters, prior_refactor_evidence_pointers, manager_flavor, shim_registry_path defaulting to ~/ai/conventions/active-shims.md, and audit_history_path defaulting to planning_dir/refactoring-audit-history.md"
  expectations:
    - "dispatches exactly one implementation child and one ticket PR after executable exact protected-short-branch, canonical root, and cardinality validation; larger refactors decompose into separate refactoring WUs before this workflow"
    - "for feature-routed calls, the sole implementation child receives exact ticket/backend/branch/root inputs, base_branch equal to the validated short integration branch name, byte-identical local_coverage_command with dispatch-validation SHA-256 binding, and auto_merge_after_phase_9=false"
    - "refactoring-orchestrator solely merges the child PR after exact nested implementation versus child PR/head/base/expected-head-guard identity validation, required caller expected-context versus producer ticket-result validation, current implementation Phase 4/6/8 proof hashes, a closed route/feature/attempt-bound auditor index with exact five pre-merge and five post-merge current LOW reports, and an immutable pre-merge process projection whose canonical header-first unique-PASS audit has a producer-owned machine binding"
    - "binds implementation, test, review, and auditor evidence to reviewed base/head SHAs and requires provider/fetched/reviewed equality for both OIDs immediately before merge; every post-ready pre-merge refusal restores exact OPEN draft identity before returning to implementation Phase 8, while merge invocation is explicitly non-replayable"
    - "success requires matching MERGED provider identity/merge OID, refreshed ancestry/immediate parent from reviewed_base_sha, and exact current refactoring-owned pre-merge/final process-proof path-hashes"
    - "feature-orchestrator consumes VERIFIED_MERGED route evidence, binds implementation/refactoring-owned process proofs without re-auditing their internals, and never merges refactoring-owned PRs"
    - "feature-routed success returns refactoring-route-result-v1 with exact route invocation identity, singular merged child, child and nested implementation PR/head/guard equality, integration/dispatched/open/pre-merge/merged/nested-implementation base name and reviewed/pre-merge/merged base SHA equality, plus a current closed auditor index whose route arrays and ten re-hashed exact-LOW reports are semantically validated without rerunning auditors"
  outputs:
    - "${planning_dir}/refactoring-route-result.json, ${planning_dir}/refactoring-auditor-index.json, ${planning_dir}/refactoring-currentness/<slice_identity>.json, ${planning_dir}/refactoring-ready-restoration/<slice_identity>.json, ${planning_dir}/refactoring-process-tree-audit-pre-merge.md, and ${planning_dir}/refactoring-process-tree-audit.md"
    - "${scratch_dir}/refactoring-dispatch-plan.json and ${planning_dir}/refactoring-dispatch-validation.json"
    - "${scratch_dir}/refactoring-expected-process-pre-merge.json, ${scratch_dir}/refactoring-dispatch-evidence-pre-merge.json, and ${scratch_dir}/refactoring-process-tree-pre-merge.json"
    - "${scratch_dir}/refactoring-dispatch-evidence.json, ${scratch_dir}/refactoring-expected-process.json, and ${scratch_dir}/refactoring-process-tree.json"
    - "${planning_dir}/refactoring-audit-history.md from revise/review round two onward"
  non_goals:
    - does not implement cross-file auditor analysis
    - does not manage integration-branch lifecycle cadence
    - does not enumerate existing shims
---
# Refactoring workflow

## Role

Coordinate one refactoring WU above exactly one per-PR implementation-pipeline child.

## Use When

- Use when the work is internal structure reshape with no intended external behavior change.
- Use when the work needs integration-buffer staging, contract-bounded slicing, encapsulate-first handling, or shim lifecycle tracking.
- Use when refactoring targets come from auditor outputs and need one coordinated target-map, encapsulation, verify, and buffer-PR cycle.
- Receiver-side intake follows `conventions/feature-development-workflow.md` `## Refactoring out of scope`: separate existing-code structural refactor tickets are valid intake only when behavior does not ship.

## Do Not Use When

- Do not use as the top-level owner for work that ships behavioral change or has a user-facing surface; use `~/ai/workflows/feature-development.md`. Feature-development may dispatch this workflow for an explicitly `refactoring`-owned ticket whose own scope preserves behavior.
- Do not use for one already-scoped implementation WU that does not need refactoring topology; use `~/ai/workflows/implementation-pipeline.md`.
- Do not use for standalone roadmap, prototype, RCA, release, or PR review work.

## Workflow Dispatch Surface

```yaml
orchestrator: refactoring-orchestrator
inputs:
  - "exactly one ticket source: jira_issue_key, linear_issue_key, or canonical wu_brief_path"
  - "required backend selection/configuration: ticket_system plus jira_url, jira_project, and jira_account_email for Jira, or linear_team_key and optional linear_project_id for Linear"
  - "required coordination inputs: target_list, repo_root, unique branch_name and canonical absolute worktree_path/planning_dir/scratch_dir for the sole child, exact short trunk_branch and integration_branch_ref, canonical JSON protected_branches including both, and slice_bounds; invocation UUID is derived from runner provenance"
  - "optional inputs: local_coverage_command required and non-blank for feature-routed calls, wu_brief_context_path valid only with an existing issue key, shim_placement_parameters, prior_refactor_evidence_pointers, manager_flavor, shim_registry_path defaulting to ~/ai/conventions/active-shims.md, and audit_history_path defaulting to planning_dir/refactoring-audit-history.md"
expectations:
  - "dispatches exactly one implementation child and one ticket PR after executable exact protected-short-branch, canonical root, and cardinality validation; larger refactors decompose into separate refactoring WUs before this workflow"
  - "for feature-routed calls, the sole implementation child receives exact ticket/backend/branch/root inputs, base_branch equal to the validated short integration branch name, byte-identical local_coverage_command with dispatch-validation SHA-256 binding, and auto_merge_after_phase_9=false"
  - "refactoring-orchestrator solely merges the child PR after exact nested implementation versus child PR/head/base/expected-head-guard identity validation, required caller expected-context versus producer ticket-result validation, current implementation Phase 4/6/8 proof hashes, a closed route/feature/attempt-bound auditor index with exact five pre-merge and five post-merge current LOW reports, and an immutable pre-merge process projection whose canonical header-first unique-PASS audit has a producer-owned machine binding"
  - "binds implementation, test, review, and auditor evidence to reviewed base/head SHAs and requires provider/fetched/reviewed equality for both OIDs immediately before merge; every post-ready pre-merge refusal restores exact OPEN draft identity before returning to implementation Phase 8, while merge invocation is explicitly non-replayable"
  - "success requires matching MERGED provider identity/merge OID, refreshed ancestry/immediate parent from reviewed_base_sha, and exact current refactoring-owned pre-merge/final process-proof path-hashes"
  - "feature-orchestrator consumes VERIFIED_MERGED route evidence, binds implementation/refactoring-owned process proofs without re-auditing their internals, and never merges refactoring-owned PRs"
  - "feature-routed success returns refactoring-route-result-v1 with exact route invocation identity, singular merged child, child and nested implementation PR/head/guard equality, integration/dispatched/open/pre-merge/merged/nested-implementation base name and reviewed/pre-merge/merged base SHA equality, plus a current closed auditor index whose route arrays and ten re-hashed exact-LOW reports are semantically validated without rerunning auditors"
outputs:
  - "${planning_dir}/refactoring-route-result.json, ${planning_dir}/refactoring-auditor-index.json, ${planning_dir}/refactoring-currentness/<slice_identity>.json, ${planning_dir}/refactoring-ready-restoration/<slice_identity>.json, ${planning_dir}/refactoring-process-tree-audit-pre-merge.md, and ${planning_dir}/refactoring-process-tree-audit.md"
  - "${scratch_dir}/refactoring-dispatch-plan.json and ${planning_dir}/refactoring-dispatch-validation.json"
  - "${scratch_dir}/refactoring-expected-process-pre-merge.json, ${scratch_dir}/refactoring-dispatch-evidence-pre-merge.json, and ${scratch_dir}/refactoring-process-tree-pre-merge.json"
  - "${scratch_dir}/refactoring-dispatch-evidence.json, ${scratch_dir}/refactoring-expected-process.json, and ${scratch_dir}/refactoring-process-tree.json"
  - "${planning_dir}/refactoring-audit-history.md from revise/review round two onward"
non_goals:
  - does not implement cross-file auditor analysis
  - does not manage integration-branch lifecycle cadence
  - does not enumerate existing shims
```

## Canonical Inputs

- Exactly one of `jira_issue_key`, `linear_issue_key`, or `wu_brief_path`.
- Optional `wu_brief_context_path` only with an existing backend-matching issue key; it is never a ticket source.
- `ticket_system` plus matching Jira or Linear configuration.
- `target_list` from auditor outputs.
- `repo_root`.
- `branch_name`.
- `worktree_path`.
- `planning_dir`.
- `scratch_dir`.
- `trunk_branch`.
- `integration_branch_ref`.
- `protected_branches`.
- `slice_bounds`.

The operator derives its invocation UUID from runner provenance. Callers cannot select it; child UUIDs are joined from markers after dispatch.

`trunk_branch`, `integration_branch_ref`, `branch_name`, and every protected-list entry accept only exact short GitHub branch names. `protected_branches` is unique and ordered as trunk, integration when distinct, then lexical extras, and must contain both explicit identities. Full refs, remote-tracking forms, protected child names, duplicates, and normalized or semantic aliases are rejected before membership or `baseRefName` comparison. Worktree/planning/scratch paths must be pairwise distinct canonical absolute identities; reject `.` / `..`, symlinks, and lexical-versus-`resolve(strict=False)` differences. Feature-routed calls map the route record's sole existing backend issue key to the same-named input, pass the already-normalized route `branch_name`, and pass `trunk_branch`, `integration_branch_ref=${feature_branch}`, and `protected_branches=[trunk_branch, feature_branch]`; standalone calls may still use the refactoring contract's `wu_brief_path` cold-start source.

## Optional Inputs

- `shim_placement_parameters`.
- `prior_refactor_evidence_pointers`.
- `shim_registry_path` (defaults to `~/ai/conventions/active-shims.md`).
- `audit_history_path` (defaults to `${planning_dir}/refactoring-audit-history.md`; created only from revise/review round two).
- `manager_flavor`.
- `wu_brief_context_path` (existing-issue context only).
- `local_coverage_command` (required and non-blank for feature-routed calls).

## Durable Outputs

- `${planning_dir}/refactoring-route-result.json`: `refactoring-route-result-v1` success envelope with one singular complete implementation child; exact child/nested implementation PR URL/number, reviewed head branch/SHA, every open/pre-merge/merged observed head name/SHA, and expected-head guard; exact `integration_branch_name`; matching child dispatched and observed provider base names; nested implementation `base_branch` and fetched `base_ref`; reviewed/pre-merge/merged base SHA equality; immutable caller expected-context and validated producer ticket-result path/hashes; exact implementation Phase 4/6/8 proof rows; exact refactoring-owned pre-merge/final proof rows; and route-child auditor arrays exactly equal to the closed current auditor index. Equal OIDs never waive PR, branch, ref, guard, or base identity.
- `${scratch_dir}/refactoring-dispatch-plan.json` and `${planning_dir}/refactoring-dispatch-validation.json`: executable proof that one normalized non-protected branch and one unique route root set project to exactly one child and one ticket PR.
- `${planning_dir}/refactoring-auditor-index.json`: closed `refactoring-auditor-index-v1` with exact route invocation UUID, feature branch, ticket, attempt, baseline SHA, pre/post current heads, and exact canonical five-role pre-merge and post-merge arrays. Every closed row contains only role, stage, report path/SHA-256, verdict, round, baseline SHA, and current-head SHA; every report is re-hashed and parsed for exactly one canonical `Verdict: LOW`.
- `${planning_dir}/refactoring-currentness/<slice_identity>.json`: exact reviewed/fetched/provider base and head transition, required fetched base/head SHA fields, invalidated artifact hashes, and `READY` or non-mergeable `STALE_CURRENTNESS` state.
- `${planning_dir}/refactoring-ready-restoration/<slice_identity>.json`: conditional executable proof that a post-ready pre-merge refusal returned the same URL/number/base/head identity to OPEN draft state, or an explicit non-replayable blocker.
- `${planning_dir}/refactoring-process-tree-audit-pre-merge.md`: immutable independent canonical header-first pre-merge verdict with a producer-owned report/root/expected/trace/companion machine binding.
- `${planning_dir}/refactoring-process-tree-audit.md`: full post-merge independent canonical header-first blocking join verdict and producer-owned machine binding tied to the immutable pre-merge lineage.
- `${scratch_dir}/refactoring-expected-process-pre-merge.json`, `${scratch_dir}/refactoring-dispatch-evidence-pre-merge.json`, and `${scratch_dir}/refactoring-process-tree-pre-merge.json`: only implementation, baseline, and pre-merge nodes that can already exist.
- `${scratch_dir}/refactoring-dispatch-evidence.json`: child and auditor invocation/session/prompt/log evidence.
- `${scratch_dir}/refactoring-expected-process.json`: expected implementation-child and applicable-auditor topology.
- `${scratch_dir}/refactoring-process-tree.json`: full current trace for the runtime-derived invocation UUID.
- `${planning_dir}/refactoring-audit-history.md`: canonical revise/review history from round two onward.
- Shim registry updates when shims are placed or retired.
- Boundary-unraveling status for follow-up slices.

## Phases

0. Phase 0 - Identify refactoring targets via implementation-workflow auditor outputs. Sources include cohesion findings, coupling findings, function-classification findings, push-pull findings, and existing cross-file pattern-analysis outputs (this workflow does not implement cross-file analysis). Use `~/ai/conventions/code-quality.md` as the code-quality and auditor reference.
1. Phase 1 - Map contract surfaces. Use signature grep for Python-style dynamic contracts, artifact-landing grep for emitted artifacts, and cloud-permission maps for IAM, lambda triggers, lifecycle hooks, and other external readers. Follow `~/ai/conventions/refactoring-workflow.md` sections "Dynamic languages and emitted-artifact contracts" and "When there is no contract".
2. Phase 2 - Encapsulate unsafe surfaces. Apply `~/ai/conventions/refactoring-workflow.md` sections "Encapsulate first" and "Encapsulation strategy when external access is uncontrolled". Each placed shim registers in `~/ai/conventions/active-shims.md`.
3. Phase 3 - Refactor within one bounded slice. The sole implementation child receives the exact ticket/backend fields, normalized `branch_name`, unique route roots, optional same-name context-only `wu_brief_context_path`, `base_branch=${integration_branch_ref}`, feature-route-required exact unchanged `local_coverage_command=${local_coverage_command}` when supplied, and `auto_merge_after_phase_9=false`; the implementation pipeline remains the one-PR engine and an existing issue key prevents cold-create.
4. Phase 4 - Require the child's PR URL/number, declared and observed head names/SHAs, expected-head guard, and reviewed base to equal the nested implementation result exactly. Require the child's immutable expected context and producer result to pass `validate-ticket-operation-result --expected-context` for this exact ticket/backend/site/attempt/PR/reviewed identity, re-hash its exact Phase 4/6/8 owned proof rows without re-auditing them, then run the exact implementation, test, review, auditor set and immutable pre-merge process projection against one `reviewed_base_sha` and reviewed full head OID. Freeze the closed auditor index and exact-equal route arrays, re-hash all ten reports, and parse each exact LOW verdict. A correction or base movement invalidates old accepts and reruns through the implementation owner. Round two and later use decision-encoded canonical audit history.
5. Phase 5 - The refactoring owner alone promotes, re-fetches both exact branches, passes both resolved remote SHAs to production currentness, and requires provider/fetched/reviewed equality for both OIDs. Every refusal before merge runs exact-repository ready undo and production restoration validation; only OPEN draft identity unchanged across undo may return to implementation Phase 8, while restoration failure is `BLOCKED:ready-state-restoration-failed`. Guarded merge invocation is the irreversible boundary: no undo/replay follows it, and failure is `BLOCKED:merge-attempt-started`. Matching provider MERGED/merge OID plus refreshed ancestry/immediate parent, post-merge auditors, and the full process projection are required before `VERIFIED_MERGED`.

## Procedure

Follow `agents/refactoring-orchestrator.md`. This workflow doc declares the dispatch contract, inputs, outputs, phases, and stop conditions; the orchestrator doc declares the procedure. Do not re-implement implementation-pipeline phases here.

## Stop Conditions

- Stop when the target is not bounded by an understood contract.
- Stop when an unsafe surface cannot be encapsulated with the supplied authority or evidence.
- Stop when the refactor would ship behavioral change; route to feature-development instead.
- Stop when auditor metrics regress and the regression cannot be resolved inside the current slice.
- Stop before promotion when child dispatch/base/auto-merge evidence, expected caller context, validated producer ticket result, implementation-owned proof hashes, open PR base/head, ticket-scoped evidence, auditor currentness, or process topology fails. After promotion but before merge, restore and prove exact OPEN draft identity or stop `BLOCKED:ready-state-restoration-failed` without replay.
- Stop without replay after merge invocation when merged PR identity changes, merge SHA is null, integration refresh/ancestry fails, or post-merge auditor/process evidence is stale or non-accepting; perform no ready undo and return `BLOCKED:merge-attempt-started`.
- Stop with `BLOCKED:refactor-wu-decomposition-required` before dispatch when another child or ticket PR is required; create separate refactoring WUs instead of looping internally.
- Succeed only when the singular child is complete and non-null and `${planning_dir}/refactoring-route-result.json` has `state=VERIFIED_MERGED`. PR-open alone is not success.

## Escalation

- Route NEEDS_INPUT questions carrying new value, scope, or trade-off decisions to the Work Manager root per `work-manager-operator.md`.
- Escalate behavior-changing work to `~/ai/workflows/feature-development.md` and `~/ai/agents/feature-orchestrator.md`.
- If a slice repeatedly oscillates under auditor or implementation-pipeline gates, shrink or decompose the slice under the active manager flavor instead of weakening the contract-boundary rule.
- If shim retirement is blocked by uncontrolled external consumers, record the blocker in `~/ai/conventions/active-shims.md` and split the consumer-untangling work.

## Cross-references

- `~/ai/conventions/refactoring-workflow.md`
- `~/ai/conventions/active-shims.md`
- `~/ai/agents/refactoring-orchestrator.md`
- `~/ai/conventions/code-quality.md`
- `~/ai/conventions/no-backwards-compatibility.md`
- `~/ai/workflows/feature-development.md`
