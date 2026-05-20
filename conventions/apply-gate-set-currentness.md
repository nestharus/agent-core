# Apply Gate Set Currentness

This convention is the canonical rule home for `apply-gate-set` manifest currentness. Callers should cite `~/ai/conventions/apply-gate-set-currentness.md` plus the relevant section anchor instead of copying trigger logic into RCA, implementation-pipeline, or workflow files. It composes with `~/ai/conventions/audit-history.md` for append discipline, `~/ai/conventions/hotfix-skip-with-followup.md` for skip-row authority, `~/ai/conventions/code-quality.md` section `Bootstrap exception` for bootstrap authority, and `~/ai/conventions/rebase-verification.md` for the rebase gate that runs before post-rebase currentness is evaluated.

## Declared roles

`mapper`, `validator`, `formatter`

This convention is a `mapper` because it defines the canonical mapping from manifest-row state to the `currentness_key` schema and from runtime triggers to row-validity decisions. It is a `validator` because it specifies the row-level re-verification and full re-dispatch decision rules that any consumer applies to evaluate whether a row is current. It is a `formatter` because it specifies the stale-refusal record field schema and the audit-history append shape that consumers emit. Per `~/ai/conventions/code-quality.md` § `Declared roles`, the role-set tokens above are from the A1 vocabulary and bound the cohesion auditor's count-only fallback.

## Adapter declarations

```yaml
adapter_declarations:
  - component: conventions/apply-gate-set-currentness.md
    role: adapter
    Translates:
      - currentness-policy-rule-surface
      - currentness-key-schema-surface
      - invalidation-trigger-matrix-surface
      - stale-refusal-record-surface
      - row-kind-coverage-surface
```

The five translated surfaces are the complete adapter declaration. The cross-references to `~/ai/conventions/audit-history.md`, `~/ai/conventions/hotfix-skip-with-followup.md`, `~/ai/conventions/code-quality.md` § `Bootstrap exception`, `~/ai/conventions/rebase-verification.md`, the apply-gate-set operator/workflow, RCA, and implementation-pipeline are subordinate authority/caller surfaces, not additional translated contracts.

## Currentness key schema

Every manifest row that can authorize advancement carries a `currentness_key`. The key proves the row belongs to the active caller lifecycle, repository state, evidence contract, row producer, and policy version. `verified_at` is required but never sufficient by itself.

| Field | Required | Type | Identity class |
|---|---|---|---|
| `cycle_id` | yes | string | Runtime lifecycle identity: RCA `failure_id` plus cycle count, or implementation phase/session identity. |
| `caller_mode` | yes | enum: `rca-post-apply`, `implementation-phase-4`, `implementation-phase-6`, `implementation-phase-8` | Runtime caller identity. |
| `head_sha` | yes | git SHA string | Runtime repository identity. |
| `base_ref` | yes | git ref or SHA string | Runtime repository comparison identity. |
| `diff_hash` or `diff_sha256` | yes | SHA-256 string | Content-derived hash of the active diff. |
| `contract_artifact_hashes` | yes | object: `path -> SHA-256` | Content-derived hashes of proposal, root-cause, fix-decision, application plan, Step 6a contract, alignment, critic, or equivalent contract artifacts consumed by the row. |
| `report_path_hashes` | yes | object: `path -> SHA-256` | Content-derived hashes of child reports, gate reports, process-tree reports, aggregate reports, and indexes consumed by the row. |
| `scope_hash` | yes | SHA-256 string or stable scope-ref hash | Content-derived hash of approved scope, touched-path set, or application scope. |
| `runtime_claim_hash` | yes when applicable; otherwise explicit `n/a:<reason>` | SHA-256 string or non-applicability marker | Content-derived hash of runtime-claim text or referenced artifact. |
| `canonical_output_path_hashes` | yes for row-level reuse | object: `path -> { sha256, size, mtime }` | Content-derived canonical-output integrity bundle. |
| `producing_invocation_uuid` | yes | UUID string or `row_id -> UUID` map | Runtime-only producer identity joined through process-tree or canonical-output evidence. |
| `verified_at` | yes | ISO-8601 timestamp | Runtime verification moment. |
| `currentness_policy_ref` | yes | string `<path>#<section>` | Runtime policy identity, normally `~/ai/conventions/apply-gate-set-currentness.md#Currentness-key-schema`. |
| `authority_ref_hashes` | yes for exception rows | object: `path -> SHA-256` | Hotfix-skip authority, DECISIONS/bootstrap-exception authority, or inventory-resolution authority. |
| `refused_transition_record` | yes on stale-refusal rows; nullable otherwise | object or path ref | Runtime audit identity for a refused transition, shaped by `## Stale-refusal records`. |

Optional row-specific extensions may add evidence such as verified-rebase bundle hashes, Step 6b output-index hashes, side-channel hashes, prototype-supersession hashes, skip-followup status hashes, bootstrap four-condition record hashes, or inventory-resolution context hashes. Optional fields cannot waive the required core key.

## Invalidation trigger matrix

Any trigger below makes the prior matching row historical context unless `## Row-level re-verification` succeeds for the active identity. The convention names what changed, which fields lose match, and which row kinds are affected; callers delegate currentness decisions here.

| Trigger | What changes | Fields losing match | Affected row kinds |
|---|---|---|---|
| RCA Phase 2 root-cause re-entry | Root-cause artifact and downstream artifacts. | `cycle_id`, `contract_artifact_hashes`, often `scope_hash`. | All row kinds. |
| RCA Phase 3 fix-decision revision | Fix-decision artifact. | `contract_artifact_hashes`, possibly `scope_hash`. | All row kinds whose contract artifacts include the fix decision. |
| RCA Phase 4 application-plan revision | Application plan and possibly application scope. | `contract_artifact_hashes`, `scope_hash` when scope changes. | All row kinds whose contract artifacts include the application plan. |
| RCA Phase 5 apply re-run | Applied worktree content and child producer set. | `head_sha`, `diff_hash`, `producing_invocation_uuid`. | All row kinds; full re-dispatch is required. |
| RCA Phase 6 verify-or-return repair | Verification artifacts. | `report_path_hashes`, often `canonical_output_path_hashes`. | Rows that cite verification artifacts. |
| Cap-hit / scope expansion | RCA or implementation scope. | `scope_hash`, often `contract_artifact_hashes`. | All row kinds whose scope is affected. |
| Rebase | Base/head relation and active diff. | `head_sha`, `base_ref`, `diff_hash`. | All row kinds. Currentness applies after `~/ai/conventions/rebase-verification.md` clears. |
| Verification repair | Canonical output content, stat bundle, parsed verdict, or report set. | `canonical_output_path_hashes`, possibly `report_path_hashes`. | Rows that cite the affected canonical output. |
| Substantive contract/test revision per Entry-Mode Re-audit rule | Audited contract, test, runtime, corpus, or behavior artifact. | `contract_artifact_hashes`, possibly `report_path_hashes`. | Rows whose contract artifacts include the revised content. |

Stale evidence is not strategy-selection input. A stale row routes to row rerun, full re-dispatch, evidence repair, split, shrink, or `NEEDS_INPUT` before any semantic decomposition decision consumes it.

## Row-level re-verification

Row-level re-verification is acceptable only for same-identity reuse. It is permitted only when all conditions below hold:

1. `cycle_id`, `caller_mode`, `head_sha`, `base_ref`, `diff_hash`, `scope_hash`, and `runtime_claim_hash` or the explicit `n/a:<reason>` marker all match the manifest values.
2. Every `canonical_output_path` in the row's `canonical_output_path_hashes` exists on disk.
3. For each existing canonical path, current `size`, `mtime`, and `sha256` all match the manifest values.
4. For each existing canonical path, the current `verdict_line` re-parsed from disk matches the manifest's `verdict_line`.
5. Each `producing_invocation_uuid` still resolves to a succeeded invocation whose declared output matches the row's canonical output path.
6. For exception rows, every `authority_ref_hashes` entry matches the manifest values.
7. The row's `currentness_policy_ref` points at the still-current canonical policy file and section.

This extends the existing Canonical Join Manifest Re-Verification primitive with lifecycle keys, exception authority hashes, and policy identity. It does not rewrite raw child verdicts.

## Full re-dispatch

Full re-dispatch is required when any same-identity condition fails, including:

- Any of `cycle_id`, `head_sha`, `diff_hash`, `scope_hash`, `runtime_claim_hash`, any `contract_artifact_hashes` entry, or any `report_path_hashes` entry changes.
- Any canonical output is missing, renamed, moved, unreadable, stat-mismatched, hash-mismatched, or has a changed parsed `verdict_line`.
- Any `producing_invocation_uuid` is untraceable for the active identity.
- For an exception row, the referenced hotfix-skip authority, bootstrap-exception authority, or inventory-resolution authority has changed or gone stale.
- The `currentness_policy_ref` has been superseded by a newer canonical policy.

Full re-dispatch means rerunning the gate from clean state through the existing `apply-gate-set` dispatch contract. It is not a row-level patch.

## Stale-refusal records

When stale currentness blocks a transition, append an audit-history refusal record under the existing append discipline in `~/ai/conventions/audit-history.md`. Implementation-pipeline records append to `${planning_dir}/audit-history.md`; RCA records append to the equivalent RCA audit history, normally `${dossier_dir}/audit-history.md` or the caller-supplied `audit_history_path`.

Required fields:

- `actor`: agent or orchestrator emitting the refusal.
- `timestamp`: ISO-8601 timestamp.
- `manifest_path`: absolute path of the stale join manifest or row reference.
- `gate_name` or `row_kind`: gate identifier for gate-scoped refusals; one of `successful_gate`, `hotfix_skip`, `bootstrap_exception`, or `inventory_resolution` for row-scoped refusals.
- `canonical_output_path`: absolute path or paths of the row's canonical output.
- `expected_currentness_keys`: subset of the currentness key map that mismatched.
- `observed_currentness_keys`: corresponding observed values.
- `refused_transition`: named action that was refused, such as `Phase 4 join manifest publication`, `RCA Phase 6.5 -> Phase 7`, `impl-pipeline Phase 6 -> Phase 7`, or `Phase 8 -> Phase 9`.
- `disposition`: `row-level rerun`, `full re-dispatch`, `split`, `shrink`, or `NEEDS_INPUT:<question_artifact>`.
- `replacement_paths`: when applicable, canonical-output deletion or replacement entries linked by `replacement_path` and `replacement_sha256`.

Additive fields such as `caller_mode`, `cycle_id`, `row_id`, `aggregate_report_path`, `process_tree_report_path`, `failed_checks`, `producing_invocation_refs`, `old_sha256`, `replacement_sha256`, and `question_artifact_path` are allowed, but they do not replace the required fields.

## Row-kind coverage

The currentness overlay applies to all row kinds that can authorize advancement:

1. Successful gate rows apply the currentness key, trigger matrix, row-level re-verification, and full re-dispatch rules directly.
2. Hotfix-skip rows preserve the seven-field `hotfix-skip-with-followup` schema owned by `~/ai/conventions/hotfix-skip-with-followup.md`. ACR-294 adds only the currentness overlay: stale skip rows are invalidated when cycle, head, diff, scope, runtime claim, authority, or the skip's follow-up vehicle shifts or goes stale.
3. Bootstrap-exception rows preserve `~/ai/conventions/code-quality.md` section `Bootstrap exception` authority. They are invalidated when the convention citation goes stale, when the four-condition evidence is invalidated by a phase change, or when the DECISIONS ratification entry is removed or superseded.
4. Inventory-resolution rows preserve ACR-285/ACR-286 `dual_score` and `folded_equivalent` behavior. ACR-294 does not settle those trackers; it invalidates inventory-resolution rows when upstream proof-risk inventory, supported-surface inventory, authority, scope, or contract evidence shifts.
