---
workflow:
  id: feature-development
workflow_aliases:
  - alias: feature
    target:
      workflow_id: feature-development
      path: workflows/feature-development.md
  - alias: multi-ticket-feature
    target:
      workflow_id: feature-development
      path: workflows/feature-development.md
workflow_dispatch_contract:
  orchestrator: feature-orchestrator
  inputs:
    - "required canonical inputs: feature_id, feature_scope_path, repo_root, explicit trunk_branch, explicit feature_branch, feature_worktree_path, child_worktrees_root, planning_dir, scratch_dir, non-blank local_coverage_command, JSON scoped_ticket_list, ticket_system, matching jira_url, jira_project, and jira_account_email or linear_team_key and optional linear_project_id, manager_flavor, JSON acceptance_evidence_paths, and post_merge_owner; runtime invocation identity is runner-derived"
    - "exactly one route source: ticket_route_map, represented by --ticket-route-map-json with closed feature-inline-route-map-v2 records, or successor_manifest_path, represented by --successor-manifest naming the strict feature-successor-envelope-v1; the CLI rejects both/neither before parsing, every record requires one existing backend issue key equal to ticket_id, and both paths emit the same closed feature-route-manifest-v2 record graph"
    - "optional context: prototype_dossier_path, qa_operator, qa_target_descriptor, evidence_pack_context, and audit_history_path derived as planning_dir/feature-audit-history.md"
  expectations:
    - "validates explicit trunk_branch and feature_branch as distinct short GitHub branch names with git check-ref-format --branch exact-output semantics before route derivation or output"
    - "validates the complete raw route set through one shared production ticket-source/backend/branch/protected-ref/canonical-path/payload/dependency/cycle/wave/output contract that rejects wu_brief_path before output, directory creation, dispatch, or any ticket side effect; treats topological waves only as eligibility sets and serializes merge-owning attempts so each ticket has one accepted result across one or more immutable numbered owning-workflow attempts"
    - "forces the one implementation child per route to auto_merge_after_phase_9=false; feature-orchestrator consumes VERIFIED_DRAFT_PR, promotes the exact direct PR only after pre-ready gates, and merges it only after fresh non-draft currentness and lineage authorization, while refactoring-orchestrator alone merges its one child PR"
    - "validates local_coverage_command before feature worktree creation or route side effects, passes its exact bytes unchanged to direct implementation children and through refactoring to nested implementation, and binds its exact SHA-256 in the normalized manifest plus every route expected/dispatch/proof chain so changed-command replay fails closed"
    - "maps each refactoring route's existing backend issue key and normalized branch to same-named child inputs and accepts only one singular VERIFIED_MERGED child whose PR/head/guard/base identity exactly matches the nested implementation result and whose closed route/feature/attempt-bound auditor index exactly enumerates five pre-merge and five post-merge current LOW reports"
    - "requires the implementation result's immutable caller expected-context and producer ticket-result path/hashes, revalidates exact caller/producer/site/ticket identity, and hash-checks child-owned process proofs instead of trusting a feature-authored PASS wrapper or re-auditing child internals"
    - "derives implementation-pipeline-orchestrator/implementation-pipeline-result-v1 or refactoring-orchestrator/refactoring-route-result-v1 from the manifest; passes the exact normalized feature_branch into production route-process validation; requires proof-envelope/common-result/attempt-index/route-result feature-branch agreement, exact route PR/head/guard/base identity even when OIDs coincide, and refactoring auditor-index/report re-hash plus exact-LOW semantic validation without auditor reruns before acceptance or dependency release"
    - "produces QA first, pins trunk/feature/diff second, then freezes feature-evidence-index and feature-integrated-review-input; reviewer, verdict, final evidence, handoff, and outcome bind the same non-self-referential input hash"
    - "after route/process/evidence pre-ready PASS, runs gh pr ready on the exact repository/PR, freshly fetches both exact base/head refs and re-queries OPEN non-draft identity, requires provider/fetched/reviewed equality for both OIDs through production currentness, restores exact OPEN draft identity on every pre-merge refusal, then uses the expected-head guarded merge with no replay after merge invocation"
    - "stops at a queried and verified final feature PR-open handoff; post_merge_owner resumes final merge, ticket closure, and post-merge outcome work"
  outputs:
    - "${planning_dir}/route-manifest.json, ${planning_dir}/route-attempt-index.json, ${scratch_dir}/route-dispatch-evidence.json, ${planning_dir}/ticket-pr-merge-index.json, and ${planning_dir}/feature-process-index.json"
    - "unique ${scratch_dir}/feature-process/prompts/<ticket_slug>-attempt-<NNNN>.prompt.md, logs/<ticket_slug>-attempt-<NNNN>.log, outputs/<ticket_slug>-attempt-<NNNN>.output.json, expected/<ticket_slug>-attempt-<NNNN>.pre-audit.expected.json, dispatch/<ticket_slug>-attempt-<NNNN>.pre-audit.dispatch.json, traces/<ticket_slug>-attempt-<NNNN>.pre-audit.trace.json, auditors/<ticket_slug>-attempt-<NNNN>.prompt.md, auditors/<ticket_slug>-attempt-<NNNN>.log, auditors/<ticket_slug>-attempt-<NNNN>.output.md, expected/<ticket_slug>-attempt-<NNNN>.final.expected.json, dispatch/<ticket_slug>-attempt-<NNNN>.final.dispatch.json, traces/<ticket_slug>-attempt-<NNNN>.final.trace.json, ${planning_dir}/route-evidence/<ticket_slug>-attempt-<NNNN>.evidence.json, feature-process/<ticket_slug>-attempt-<NNNN>.audit.md, feature-process/<ticket_slug>-attempt-<NNNN>.binding.json, route-process-validation/<ticket_slug>-attempt-<NNNN>.json, route-attempt-outcomes/<ticket_slug>-attempt-<NNNN>.json, route-attempt-proofs/<ticket_slug>-attempt-<NNNN>.proof.json, and direct-only route-acceptance/<ticket_slug>-attempt-<NNNN>.acceptance.json"
    - "${scratch_dir}/feature-expected-process.json, ${scratch_dir}/feature-process-tree.json, and ${planning_dir}/feature-process-tree-audit.md"
    - "${planning_dir}/route-currentness/<ticket_slug>-attempt-<NNNN>-pre-ready.json, ${planning_dir}/route-currentness/<ticket_slug>-attempt-<NNNN>-post-ready.json, ${planning_dir}/route-ready-restoration/<ticket_slug>-attempt-<NNNN>.json, ${planning_dir}/route-authorization/<ticket_slug>-attempt-<NNNN>.json, ${planning_dir}/qa-verdict.md, ${planning_dir}/feature-evidence-index.json, ${planning_dir}/feature-integrated-review-input.json, ${planning_dir}/integrated-scope-verdict.md, ${planning_dir}/feature-final-evidence.json, and ${planning_dir}/feature-audit-history.md when review reaches round two"
    - "${planning_dir}/final-pr-handoff.json and ${planning_dir}/feature-outcome.json with state FINAL_PR_OPEN_HANDOFF and verified final PR base/head/head SHA"
  non_goals:
    - "does not reproduce implementation-pipeline or refactoring phases, self-certify process or scope gates, or let a route implementation child auto-merge"
    - "does not merge refactoring-owned PRs, wait for the final feature PR merge, close tickets, or write a post-merge final outcome"
---
# Feature-development workflow

## Role

Coordinate one scoped feature across heterogeneous ticket owners, integrate all verified route results on an explicit feature branch, and stop at a verified final feature PR-open handoff.

## Use When

- Use when work decomposes into two or more tickets, has a user-facing surface, or ships behavior that needs integrated review.
- Use when tickets have explicit `implementation-pipeline` or `refactoring` owners and target one feature branch before trunk.

## Do Not Use When

- Do not use for one bounded WU, standalone roadmap/prototype work, existing-PR review, or top-level behavior-preserving refactoring.
- Do not use to inline child procedures or own post-final-PR-merge lifecycle work.

## Workflow Dispatch Surface

```yaml
orchestrator: feature-orchestrator
inputs:
  - "required canonical inputs: feature_id, feature_scope_path, repo_root, explicit trunk_branch, explicit feature_branch, feature_worktree_path, child_worktrees_root, planning_dir, scratch_dir, non-blank local_coverage_command, JSON scoped_ticket_list, ticket_system, matching jira_url, jira_project, and jira_account_email or linear_team_key and optional linear_project_id, manager_flavor, JSON acceptance_evidence_paths, and post_merge_owner; runtime invocation identity is runner-derived"
  - "exactly one route source: ticket_route_map, represented by --ticket-route-map-json with closed feature-inline-route-map-v2 records, or successor_manifest_path, represented by --successor-manifest naming the strict feature-successor-envelope-v1; the CLI rejects both/neither before parsing, every record requires one existing backend issue key equal to ticket_id, and both paths emit the same closed feature-route-manifest-v2 record graph"
  - "optional context: prototype_dossier_path, qa_operator, qa_target_descriptor, evidence_pack_context, and audit_history_path derived as planning_dir/feature-audit-history.md"
expectations:
  - "validates explicit trunk_branch and feature_branch as distinct short GitHub branch names with git check-ref-format --branch exact-output semantics before route derivation or output"
  - "validates the complete raw route set through one shared production ticket-source/backend/branch/protected-ref/canonical-path/payload/dependency/cycle/wave/output contract that rejects wu_brief_path before output, directory creation, dispatch, or any ticket side effect; treats topological waves only as eligibility sets and serializes merge-owning attempts so each ticket has one accepted result across one or more immutable numbered owning-workflow attempts"
  - "forces the one implementation child per route to auto_merge_after_phase_9=false; feature-orchestrator consumes VERIFIED_DRAFT_PR, promotes the exact direct PR only after pre-ready gates, and merges it only after fresh non-draft currentness and lineage authorization, while refactoring-orchestrator alone merges its one child PR"
  - "validates local_coverage_command before feature worktree creation or route side effects, passes its exact bytes unchanged to direct implementation children and through refactoring to nested implementation, and binds its exact SHA-256 in the normalized manifest plus every route expected/dispatch/proof chain so changed-command replay fails closed"
  - "maps each refactoring route's existing backend issue key and normalized branch to same-named child inputs and accepts only one singular VERIFIED_MERGED child whose PR/head/guard/base identity exactly matches the nested implementation result and whose closed route/feature/attempt-bound auditor index exactly enumerates five pre-merge and five post-merge current LOW reports"
  - "requires the implementation result's immutable caller expected-context and producer ticket-result path/hashes, revalidates exact caller/producer/site/ticket identity, and hash-checks child-owned process proofs instead of trusting a feature-authored PASS wrapper or re-auditing child internals"
  - "derives implementation-pipeline-orchestrator/implementation-pipeline-result-v1 or refactoring-orchestrator/refactoring-route-result-v1 from the manifest; passes the exact normalized feature_branch into production route-process validation; requires proof-envelope/common-result/attempt-index/route-result feature-branch agreement, exact route PR/head/guard/base identity even when OIDs coincide, and refactoring auditor-index/report re-hash plus exact-LOW semantic validation without auditor reruns before acceptance or dependency release"
  - "produces QA first, pins trunk/feature/diff second, then freezes feature-evidence-index and feature-integrated-review-input; reviewer, verdict, final evidence, handoff, and outcome bind the same non-self-referential input hash"
  - "after route/process/evidence pre-ready PASS, runs gh pr ready on the exact repository/PR, freshly fetches both exact base/head refs and re-queries OPEN non-draft identity, requires provider/fetched/reviewed equality for both OIDs through production currentness, restores exact OPEN draft identity on every pre-merge refusal, then uses the expected-head guarded merge with no replay after merge invocation"
  - "stops at a queried and verified final feature PR-open handoff; post_merge_owner resumes final merge, ticket closure, and post-merge outcome work"
outputs:
  - "${planning_dir}/route-manifest.json, ${planning_dir}/route-attempt-index.json, ${scratch_dir}/route-dispatch-evidence.json, ${planning_dir}/ticket-pr-merge-index.json, and ${planning_dir}/feature-process-index.json"
  - "unique ${scratch_dir}/feature-process/prompts/<ticket_slug>-attempt-<NNNN>.prompt.md, logs/<ticket_slug>-attempt-<NNNN>.log, outputs/<ticket_slug>-attempt-<NNNN>.output.json, expected/<ticket_slug>-attempt-<NNNN>.pre-audit.expected.json, dispatch/<ticket_slug>-attempt-<NNNN>.pre-audit.dispatch.json, traces/<ticket_slug>-attempt-<NNNN>.pre-audit.trace.json, auditors/<ticket_slug>-attempt-<NNNN>.prompt.md, auditors/<ticket_slug>-attempt-<NNNN>.log, auditors/<ticket_slug>-attempt-<NNNN>.output.md, expected/<ticket_slug>-attempt-<NNNN>.final.expected.json, dispatch/<ticket_slug>-attempt-<NNNN>.final.dispatch.json, traces/<ticket_slug>-attempt-<NNNN>.final.trace.json, ${planning_dir}/route-evidence/<ticket_slug>-attempt-<NNNN>.evidence.json, feature-process/<ticket_slug>-attempt-<NNNN>.audit.md, feature-process/<ticket_slug>-attempt-<NNNN>.binding.json, route-process-validation/<ticket_slug>-attempt-<NNNN>.json, route-attempt-outcomes/<ticket_slug>-attempt-<NNNN>.json, route-attempt-proofs/<ticket_slug>-attempt-<NNNN>.proof.json, and direct-only route-acceptance/<ticket_slug>-attempt-<NNNN>.acceptance.json"
  - "${scratch_dir}/feature-expected-process.json, ${scratch_dir}/feature-process-tree.json, and ${planning_dir}/feature-process-tree-audit.md"
  - "${planning_dir}/route-currentness/<ticket_slug>-attempt-<NNNN>-pre-ready.json, ${planning_dir}/route-currentness/<ticket_slug>-attempt-<NNNN>-post-ready.json, ${planning_dir}/route-ready-restoration/<ticket_slug>-attempt-<NNNN>.json, ${planning_dir}/route-authorization/<ticket_slug>-attempt-<NNNN>.json, ${planning_dir}/qa-verdict.md, ${planning_dir}/feature-evidence-index.json, ${planning_dir}/feature-integrated-review-input.json, ${planning_dir}/integrated-scope-verdict.md, ${planning_dir}/feature-final-evidence.json, and ${planning_dir}/feature-audit-history.md when review reaches round two"
  - "${planning_dir}/final-pr-handoff.json and ${planning_dir}/feature-outcome.json with state FINAL_PR_OPEN_HANDOFF and verified final PR base/head/head SHA"
non_goals:
  - "does not reproduce implementation-pipeline or refactoring phases, self-certify process or scope gates, or let a route implementation child auto-merge"
  - "does not merge refactoring-owned PRs, wait for the final feature PR merge, close tickets, or write a post-merge final outcome"
```

## Canonical Inputs

The workflow and `agents/feature-orchestrator.md` use the same names. The caller provides explicit `trunk_branch` and `feature_branch`; no cross-project branch default exists. `feature_scope_path` is the scope and acceptance anchor, `feature_worktree_path` is the feature integration worktree, and `child_worktrees_root` is the deterministic root for route-owned worktrees.

The caller also supplies `ticket_system` plus the matching Jira or Linear configuration, JSON arrays for exact scoped tickets and acceptance evidence, exactly one route source, manager flavor, and the downstream `post_merge_owner`. `tools/feature_route_manifest.py` represents that xor mechanically as `--ticket-route-map-json` versus `--successor-manifest`, rejects both/neither before source parsing, and supplies the same explicit feature/trunk/scope/backend/root identities to either normalization path. The operator derives its invocation UUID from runner provenance and joins child UUIDs after dispatch. Prototype, QA, evidence-pack, and second-round audit-history context use the optional names in the dispatch surface.

The feature owner validates non-blank `local_coverage_command` before feature worktree creation or route side effects, passes the exact value unchanged to direct implementation children and through refactoring to its nested implementation child, and binds only its exact SHA-256 in route manifest/dispatch/proof evidence. The command never enters route payload, evidence-pack context, ambient configuration, or free-form anti-scope prose.

## Invocation Example

```yaml
orchestrator: feature-orchestrator
inputs:
  feature_id: AGE-255
  feature_scope_path: /project/planning/age-255/feature-scope.md
  repo_root: /project/trunk
  trunk_branch: main
  feature_branch: feature/hourly-suspicious-process-investigator
  feature_worktree_path: /project/worktrees/hourly-suspicious-process-investigator
  child_worktrees_root: /project/worktrees/routes
  planning_dir: /project/planning/hourly-suspicious-process-investigator
  scratch_dir: /project/planning/hourly-suspicious-process-investigator/scratch
  local_coverage_command: cargo llvm-cov --workspace --no-report && cargo llvm-cov report --json --summary-only --output-path coverage/coverage-summary.json && cargo llvm-cov report --lcov --output-path coverage/lcov.info
  scoped_ticket_list: '["AGE-259"]'
  ticket_route_map: '[{"ticket_id":"AGE-259","successor_id":"AGE255-S04","title":"Integrate","brief_path":"/project/planning/age-255/AGE255-S04.md","surfaces":["S1"],"owning_route":"implementation-pipeline","depends_on":[],"branch_name":"route/age-259","ticket_source":{"linear_issue_key":"AGE-259"},"route_payload":{}}]'
  ticket_system: linear
  linear_team_key: AGE
  manager_flavor: manager-max
  acceptance_evidence_paths: '["/project/planning/age-255/acceptance.md"]'
  post_merge_owner: work-manager
```

The implementation record keeps `route_payload` exactly `{}`. A refactoring record also receives the declared coverage command through the feature invocation, not through its route payload.

## Route And Ownership Contract

The owning operator's `feature-route-source-v2` is authoritative. It discriminates already-canonical inline records from the real `successors` envelope. Every route record must contain exactly one existing backend issue key selected by `ticket_system`, and that key must equal immutable graph `ticket_id`; `wu_brief_path` is rejected before normalized output, directory creation, dispatch, or any ticket side effect. The exact AGE-255 source kind is Linear-bound, and every present source backend indicator and recognized ticket URL host must equal `ticket_system`; a Jira selection or unknown/mismatched URL host fails before output or route side effects. The successor adapter then strictly validates the envelope, records, brief paths, surfaces, handoff, scope equality, source-id dependency graph, branches, slugs, and derived paths, maps dependencies to ticket keys, and derives brief-plus-surfaces refactoring target/slice contracts. All failures are `BLOCKED:invalid-ticket-route-manifest`. Standalone implementation-pipeline and refactoring calls retain their own `wu_brief_path` cold-start support outside feature routing.

Every route attempt derives its direct operator and result schema from the manifest, freezes route-bound pre-audit/final expected and dispatch evidence, and runs `validate-route-process-proof --feature-branch ${feature_branch}` over current traces, auditor log/output/report/binding, result, route evidence, and child-owned companions. Both route kinds then freeze one `feature-route-attempt-proof-v1` carrying that exact branch; `validate-route-attempts` must re-hash and semantically revalidate it and reject any manifest/index/proof/common/outcome/route-result branch disagreement before selection or dependency release. Direct implementation additionally requires its exact existing backend issue key equal to `ticket_id`, `base_branch=${feature_branch}`, `base_ref=refs/remotes/origin/${feature_branch}`, matching reviewed/current provider base names, `route_attempt_number`, `auto_merge_after_phase_9=false`, caller-bound ticket evidence, draft currentness, branch-bound acceptance, fresh non-draft currentness, and artifact-lineage `MERGE_AUTHORIZED` before expected-head merge. Refactoring requires exact child/nested implementation PR URL/number; exact declared, reviewed, open, pre-merge, merged, and expected-guard head identity; all integration/dispatched/observed/nested base names/ref equal to the feature branch/ref; and merged/reviewed/pre-merge/nested base SHA equality. It also requires a current closed auditor index bound to route UUID/feature/ticket/attempt, route arrays exactly equal to its canonical five-role pre/post arrays, every indexed report re-hashed and parsed as exact LOW, pre-merge report heads equal to the reviewed child head, and post-merge report heads equal final/refreshed integration SHA. The feature owner performs that re-hash and semantic validation without rerunning child auditors, then composes the common proof with `VERIFIED_MERGED` identity/ancestry and never merges the PR again. Equal OIDs never substitute for PR, branch/ref-name, base, or guard equality.

Every refactoring dispatch maps the route record's sole existing backend issue key and already-normalized `branch_name` to same-named inputs and passes matching backend configuration plus the validated brief/surface target contract, title/surface slice contract, unique route roots, `trunk_branch=${trunk_branch}`, `integration_branch_ref=${feature_branch}`, and canonical `protected_branches=[trunk_branch, feature_branch]`. Runtime UUIDs are joined after dispatch, never selected by callers. The refactoring owner validates and dispatches exactly one implementation child with one ticket PR, forces it to the feature base with auto-merge false, solely owns that merge, and returns exact guarded provider identities plus immutable pre-merge and full post-merge process evidence. The feature owner consumes that route-level `VERIFIED_MERGED` result and never performs a second merge. A route needing another PR must be decomposed into another refactoring WU before dispatch.

Topological waves are eligibility sets, never fanout execution batches. The owner dispatches one merge-owning attempt at a time and does not dispatch another eligible route until the prior route has one accepted verified-merged attempt on the refreshed feature branch. Dependency completion is only the route-attempt index's unique selected `PASS` / `VERIFIED_MERGED` attempt whose base is the feature branch and whose merge commit is an ancestor of the refreshed feature branch. The real AGE-255 wave-zero refactoring routes therefore integrate serially against successively refreshed feature bases before AGE-259 becomes eligible.

## Evidence And Final Gate

The feature owner freezes one direct-child-only pre-audit expected/dispatch/trace and one final direct route-plus-auditor expected/dispatch/trace per numbered attempt. The independent report binds only pre-audit expected/trace plus route evidence/output, pre-audit dispatch, its prompt, and the route result's current implementation/refactoring-owned proof path/hashes; it does not inspect route descendants or re-audit child proof contents. Its complete runner log and provider-only extracted report copy are bound later by acceptance, which also binds final topology. A direct attempt adds pre-ready currentness and that separate acyclic envelope only after both production direct-child topology validations and report/output equality pass, then adds fresh post-ready currentness, lineage authorization, and conditional ready-restoration evidence without mutating earlier artifacts. Stale and replay-required attempts remain immutable. After every ticket is accepted, the owner runs one cumulative join over all attempts; child phases remain outside this parent topology.

Route-scoped evidence exists before direct merge. After all verified results are on the feature branch, produce executable QA or its explicit unavailable placeholder first, freshly fetch/pin trunk and feature plus the current diff/hash second, and only then freeze `feature-evidence-index.json` and the separate immutable `feature-integrated-review-input.json` (`feature-integrated-review-input-v1`). A concrete ad-hoc `gpt-xhigh` child consumes that manifest. The verdict, `feature-final-evidence.json`, handoff, and outcome all bind its exact path/hash without putting a future result or self hash into the manifest. Substantive trunk or feature changes invalidate the input and all consumers and force a rerun; round two and later use canonical audit history.

The final PR is created only after current process, evidence, QA/placeholder, and integrated-scope gates pass. Pass explicit feature worktree, `branch=${feature_branch}`, and `base=${trunk_branch}` plus pinned refs/OIDs to `pr-writer`, then create with explicit `--base/--head`. Query it back and require OPEN draft state plus the reviewed full base/head OIDs before the `FINAL_PR_OPEN_HANDOFF`.

## Procedure

Follow `agents/feature-orchestrator.md`. This workflow declares the shared dispatch boundary and outputs; the operator owns parsing, dispatch, evidence, merge, and handoff procedure.

## Stop Conditions

- Stop before dispatch on invalid invocation, backend configuration, route source, route record, scoped set, or dependency graph.
- Stop before dependent dispatch unless every prerequisite has a verified merged route result on the refreshed feature branch.
- Stop before direct ready without exact immutable expected caller context, semantically valid producer ticket-operation evidence, current child-owned process-proof path/hashes, exact pre-audit direct route-child topology, independent auditor log/output/report equality, exact final direct route-plus-auditor topology, draft pre-ready currentness PASS, and an acyclic acceptance envelope. Route descendants do not block unless reparented directly to the feature root. Stop before merge without a fresh OPEN/non-draft provider capture, production currentness PASS, and artifact-lineage `MERGE_AUTHORIZED`.
- Stop before final synthesis on incomplete cumulative process review, evidence, or QA state.
- Stop before final PR creation on a failed or stale integrated-scope verdict or missing second-round canonical audit history.
- Succeed only at the durable `FINAL_PR_OPEN_HANDOFF`; post-merge work is out of this invocation.

## Cross-References

- `~/ai/conventions/feature-development-workflow.md`
- `~/ai/conventions/audit-history.md`
- `~/ai/agents/feature-orchestrator.md`
- `~/ai/agents/process-tree-auditor.md`
- `~/ai/workflows/implementation-pipeline.md`
- `~/ai/workflows/refactoring.md`
