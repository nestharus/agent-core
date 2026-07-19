---
eval_id: acr-261
behavior_class: Verified-rebase jj resolve list row normalization and conflict path-set integrity
lifecycle_state: WRITE
severity_when_fires: HIGH
evidence_source_kinds:
  - workflow-markdown
  - verified-rebase-bundle
  - saved-trace-json
  - agent-run-log
  - fixture-evidence
suggested_action_class: revise-verified-rebase-conflict-path-normalization
---

## Declared roles

`validator`.

This file-local declaration is explicit per `~/ai/conventions/code-quality.md` § Declared roles. `validator` covers WRITE eval-spec authoring; this file declares unwanted behavior, non-fire cases, and minimum finding-contract schema per `~/ai/conventions/evals.md`.

## Intrinsic-surface declarations

These declarations are explicit per `~/ai/conventions/code-quality.md` § Intrinsic-surface declarations.

```yaml
intrinsic_surface_declarations:
  - component: evals/acr-261/eval.md
    role: intrinsic-surface
    Domain: acr_261_eval_contract_surfaces
    Owns:
      - conventions/evals.md
      - eval_id
      - severity
      - evidence_paths
      - summary
      - suggested_action
      - confidence
      - ACR-255 V3 fixture evidence
      - workflows/verified-rebase.md semantics
  - component: evals/acr-261/eval.md
    role: intrinsic-surface
    Domain: acr_261_verified_rebase_conflict_path_set_surfaces
    Owns:
      - jj resolve --list
      - conflict-artifacts/files.txt
      - jj file show
      - slug generation
      - §8 CF
      - raw sidecar diagnostics
```

The planned eval-spec component declares its surfaces forward so the coupling-auditor sees the planned declaration carrier and can verify completeness when the file is authored in Phase 6b.

# Eval: acr-261

## Eval identity

- `eval_id`: `acr-261`
- `lifecycle_state`: `WRITE`
- `owner`: `implementation-pipeline-orchestrator Phase 6b / ACR-261`
- `artifact`: `evals/acr-261/eval.md`
- `behavior_class`: verified-rebase `jj resolve --list` row normalization and conflict path-set integrity
- `severity_when_fires`: `HIGH`
- `suggested_action_class`: `revise-verified-rebase-conflict-path-normalization`

This is a WRITE-state behavior specification only. It defines future trace-backed findings for the ACR-261 verified-rebase conflict path normalization contract; it is not runnable detector code, pytest code, a fixture suite, or a verifier script.

The target implementation surfaces are `workflows/verified-rebase.md` and `agents/jj-operator.md`, with fixture motivation from `/home/nes/ai/planning/prototype-acr-255-clarify/dossier/evidence/v3/findings.md`, where `jj resolve --list` rendered `module.txt    2-sided conflict` instead of a bare path.

## Unwanted behavior

This eval covers exactly four unwanted behaviors:

- `B1-raw-row-canonical-files`: Raw `jj resolve --list` default-rendering rows, such as `path<TAB>N-sided conflict`, reach canonical `conflict-artifacts/files.txt` without being validated as bare paths first.
- `B2-raw-row-file-show`: `jj file show` is invoked with an unstripped raw row as the path argument, producing a `.conflict` artifact named from the unstripped string, such as `module.txt<TAB>2-sided conflict.conflict`.
- `B3-raw-row-cf-verdict`: The §8 verdict `CF` set is computed from raw display rows rather than from validated bare paths, leading to `RP ⊆ CF` misclassification.
- `B4-unsupported-row-silent-accept`: The workflow silently accepts an unsupported row shape, such as an embedded-whitespace path, without producing a `BLOCKED:unsupported-jj-resolve-list-row` halt signal.

## Positive evidence

Future detectors should report a finding when workflow text, verified-rebase bundle evidence, or trace evidence shows one or more of these states:

- `conflict-artifacts/files.txt` contains a row with tab-delimited or whitespace-delimited jj display metadata, including `N-sided conflict`, instead of one validated bare conflicted path per line.
- `conflict-artifacts/files.txt` is produced directly from `jj resolve --list` stdout with no raw sidecar and no row-validation adapter between raw output and the canonical file.
- `conflict-artifacts/jj-resolve-list-raw.txt` is absent in combination with evidence that `conflict-artifacts/files.txt` was produced directly from raw `jj resolve --list` display rows instead of from validated bare paths.
- `jj file show` path evidence, shell snippet evidence, or `.conflict` filenames show slugs derived from unstripped raw rows rather than from validated path-derived slugs.
- The `workflows/verified-rebase.md` `### 6. Capture POST state` block leaves raw jj display rows able to reach canonical outputs because it does not document the row-validation adapter: raw `jj resolve --list` stdout as diagnostic input, extraction of the first whitespace-delimited field, strict bare-path validation, and canonical append to `conflict-artifacts/files.txt`.
- The §8 verdict logic reads `CF` from raw `jj resolve --list` output or a raw sidecar instead of from canonical `conflict-artifacts/files.txt`.
- A row with unsupported shape, including an embedded-whitespace path that cannot satisfy the bare-path contract, produces canonical `files.txt` or `.conflict` artifacts instead of halting with `BLOCKED:unsupported-jj-resolve-list-row: <evidence>`.
- `agents/jj-operator.md` inspect-bundle prose treats `conflict-artifacts/files.txt` as an unvalidated jj CLI display dump rather than the normalized conflict path set consumed by verdict review.

## Non-fire cases

This eval must not fire for these trace shapes:

- The workflow produces both `conflict-artifacts/jj-resolve-list-raw.txt` as a raw diagnostic sidecar and `conflict-artifacts/files.txt` as validated bare paths; the verdict logic reads only the validated file.
- A verified-rebase run on a clean rebase produces empty `conflict-artifacts/files.txt` and no `.conflict` files.
- A verified-rebase run on a conflict-bearing branch with all-bare-path jj output produces validated `conflict-artifacts/files.txt` matching the bare-path contract.
- A verified-rebase run on a conflict-bearing branch where one row has unsupported shape exits with `BLOCKED:unsupported-jj-resolve-list-row: <evidence>` and does not publish a corrupt `conflict-artifacts/files.txt`.
- Historical verified-rebase bundles that predate ACR-261 contain no raw sidecar; old bundles are not evidence of a post-fix workflow defect by themselves unless the active workflow trace claims they were produced under the ACR-261 contract.

## Required trace fields

Future runnable detectors must consume evidence by semantic role, not by one raw storage schema. Required fields are:

| Required trace field | Evidence role | Purpose |
|---|---|---|
| `wu_id` | root dispatch or planning metadata | Identifies the Work Unit under review. |
| `root_invocation_uuid` | saved trace or run log | Joins workflow, bundle, and audit evidence. |
| `verified_rebase_bundle_path` | verified-rebase bundle | Locates the bundle being inspected. |
| `conflict_artifacts_files_txt_content` | `conflict-artifacts/files.txt` | Shows the canonical conflict path set consumed by later workflow phases. |
| `jj_resolve_list_raw_txt_content` | `conflict-artifacts/jj-resolve-list-raw.txt`, when present | Preserves raw `jj resolve --list` stdout for row-shape diagnosis. |
| `conflict_artifact_filenames` | `conflict-artifacts/*.conflict` | Verifies `.conflict` filenames correspond to validated path-derived slugs, not raw-row-derived slugs. |
| `file_show_path_arguments` | shell trace, run log, or workflow snippet | Confirms `jj file show` is called with validated bare paths only. |
| `capture_post_state_block` | `workflows/verified-rebase.md` `### 6. Capture POST state` block | Verifies the documented row-validation step exists and owns raw-to-canonical normalization. |
| `artifact_table_rows` | `workflows/verified-rebase.md` artifact table | Verifies `files.txt` and `jj-resolve-list-raw.txt` have the post-ACR-261 producer and content semantics. |
| `verdict_cf_source` | §8 verdict logic or summary evidence | Confirms `CF` is computed from validated `files.txt`, not raw display rows. |
| `blocked_exit_token` | optional halt evidence | Captures `BLOCKED:unsupported-jj-resolve-list-row: <evidence>` when the run halts. |
| `jj_operator_inspect_bundle_text` | `agents/jj-operator.md` inspect-bundle prose | Confirms the operator treats `files.txt` as the normalized conflict path set. |
| `trace_locator` | saved trace node ids, invocation UUIDs, paths | Lets reviewers locate the evidence chain. |

## Finding contract

Every future finding produced from this eval must preserve the minimum fields from `~/ai/conventions/evals.md`:

- `eval_id`
- `severity`
- `evidence_paths`
- `summary`
- `suggested_action`
- `confidence`

Allowed extension fields include:

- `behavior_id`
- `wu_id`
- `root_invocation_uuid`
- `verified_rebase_bundle_path`
- `workflow_snapshot_path`
- `operator_snapshot_path`
- `raw_row_sample`
- `validated_path_sample`
- `conflict_artifact_filename`
- `blocked_exit_token`
- `trace_locator`

Severity guidance:

- `HIGH` when raw jj display rows reach canonical path-set inputs, drive `.conflict` artifact production, corrupt §8 `CF` computation, or unsupported row shapes are accepted silently.
- `MEDIUM` when the workflow or operator text is ambiguous enough to permit raw-row consumption but available bundle evidence is clean.
- `LOW` only for missing optional diagnostics or incomplete trace instrumentation in a future runnable detector.

### B1-raw-row-canonical-files

- `eval_id`: `acr-261`
- `severity`: `HIGH`
- `evidence_paths`: `[verified_rebase_bundle_path, conflict_artifacts_files_txt_content, jj_resolve_list_raw_txt_content, capture_post_state_block]`
- `summary`: Raw `jj resolve --list` display rows reached canonical `conflict-artifacts/files.txt` without bare-path validation.
- `suggested_action`: Revise `### 6. Capture POST state` so raw jj output is captured to `jj-resolve-list-raw.txt`, normalized through a row-validation adapter, and only validated bare paths are appended to `files.txt`.
- `confidence`: `HIGH` when `files.txt` contains display metadata such as `N-sided conflict`; `MEDIUM` when the workflow text lacks validation but observed bundle rows happen to be bare.

### B2-raw-row-file-show

- `eval_id`: `acr-261`
- `severity`: `HIGH`
- `evidence_paths`: `[verified_rebase_bundle_path, file_show_path_arguments, conflict_artifact_filenames, conflict_artifacts_files_txt_content]`
- `summary`: `jj file show` consumed an unstripped raw resolve-list row and produced a raw-row-derived `.conflict` artifact name.
- `suggested_action`: Make `.conflict` production read only canonical validated `files.txt`, and derive slugs from validated path values rather than raw jj display rows.
- `confidence`: `HIGH` when a `.conflict` filename or path argument contains `N-sided conflict`, tab-delimited metadata, or equivalent raw-row text; `MEDIUM` when slug provenance is ambiguous.

### B3-raw-row-cf-verdict

- `eval_id`: `acr-261`
- `severity`: `HIGH`
- `evidence_paths`: `[verdict_cf_source, conflict_artifacts_files_txt_content, jj_resolve_list_raw_txt_content, capture_post_state_block]`
- `summary`: The §8 `CF` set was computed from raw jj display rows instead of validated bare paths, risking false `RP ⊆ CF` classification.
- `suggested_action`: Revise §8 verdict computation so `CF` is derived only from canonical `conflict-artifacts/files.txt` after row validation.
- `confidence`: `HIGH` when verdict logic reads raw `jj resolve --list` output or raw sidecar content; `MEDIUM` when the source of `CF` is unclear.

### B4-unsupported-row-silent-accept

- `eval_id`: `acr-261`
- `severity`: `HIGH`
- `evidence_paths`: `[jj_resolve_list_raw_txt_content, blocked_exit_token, conflict_artifacts_files_txt_content, conflict_artifact_filenames, capture_post_state_block]`
- `summary`: Unsupported `jj resolve --list` row shape was accepted silently instead of halting with `BLOCKED:unsupported-jj-resolve-list-row`.
- `suggested_action`: Add or restore the strict row-validation halt path so unsupported rows stop the workflow with `BLOCKED:unsupported-jj-resolve-list-row: <evidence>` before publishing `files.txt` or `.conflict` artifacts.
- `confidence`: `HIGH` when unsupported raw rows produce canonical or `.conflict` artifacts without the halt token; `MEDIUM` when the halt path is documented but incomplete evidence prevents confirming whether artifacts were published.

## Lifecycle notes

Current state is `WRITE`. This file defines the behavior contract and finding schema only. Future detector work owns runnable adapters, fixture materialization, rollout evidence, false-positive review, and lifecycle advancement beyond `WRITE`.

## Anti-scope

This WU must not produce runnable eval code, parser code, pytest tests, pytest imports, pytest fixtures, pytest-shaped assertion code, `tools/<wu>-verify/` scripts, shell proof runners, CLI integration, scheduler wiring, CI wiring, ticket automation, or Step 6c product changes. The only structural-verification artifacts for Step 6b are this markdown eval specification and the Step 6b output index.

## Cross-references

- `/home/nes/ai/conventions/evals.md`
- `/home/nes/ai/conventions/code-quality.md`
- `/home/nes/ai/planning/acr-261-jj-resolve-list-normalize/contracts/acr-261-jj-resolve-list-normalize.md`
- `/home/nes/ai/planning/acr-261-jj-resolve-list-normalize/proposals/acr-261-acr-261.md`
- `/home/nes/ai/planning/prototype-acr-255-clarify/dossier/evidence/v3/findings.md`
- `workflows/verified-rebase.md`
- `agents/jj-operator.md`
