---
eval_id: acr-260
slug: acr-260
lifecycle: WRITE
lifecycle_state: WRITE
surface_under_test: workflows/verified-rebase.md
created: 2026-05-18
risk_class: HIGH
scope: ACR-260 merge-tree predicted-tree capture contract
behavior_class: Verified-rebase prediction capture and downstream residual-diff tolerance
severity_when_fires: HIGH
evidence_source_kinds:
  - workflow-markdown
  - verified-rebase-bundle
  - saved-trace-json
  - agent-run-log
suggested_action_class: revise-verified-rebase-predict-contract
---

# Eval: acr-260

## Identity & Lifecycle Metadata

- `eval_id`: `acr-260`
- `lifecycle`: `WRITE`
- `owner`: `implementation-pipeline-orchestrator Phase 6b / ACR-260`
- `created_at`: `2026-05-18`
- `version`: `1.0.0`

This file is a WRITE-state behavior specification for the ACR-260 verified-rebase `merge-tree --write-tree` capture contract. It defines future trace-backed findings only; it is not executable detector code.

## Surface Under Test

The target surface is `workflows/verified-rebase.md`, especially these post-fix documentation anchors:

- `workflows/verified-rebase.md:85-119`: reference-anchor table and bundle schema for `PREDICTED_TREE`, `merge-tree.out`, `merge-tree.err`, and `merge-tree.status`.
- `workflows/verified-rebase.md:164-170`: `### 4. Predict`, where stdout, stderr, status, first-line oid parsing, and stop/continue classification are documented.
- `workflows/verified-rebase.md:210-219`: `### 7. Compute diffs`, where `git diff "$PREDICTED_TREE" "$POST_TIP^{tree}" --find-renames > "$BUNDLE/residual.patch"` consumes the accepted predicted tree.
- `workflows/verified-rebase.md:226-241`: verdict rules, where prediction-command status is not a direct verdict input.
- `workflows/verified-rebase.md:327-344`: workflow contract rows for text conflicts and binary or unsupported cases.

## Unwanted Behavior

The unwanted behavior is a verified-rebase contract that discards or blocks a usable first-line `PREDICTED_TREE` oid because `git merge-tree --write-tree` exited `1` for an ordinary content conflict, or that weakens the real-failure boundary by continuing when `merge-tree` exits `>=2` or emits no valid first-line tree oid.

This eval also fires when the workflow fails to make prediction command metadata reviewable in the bundle, accepts an invalid first stdout line as `PREDICTED_TREE`, or documents downstream residual diff computation in a way that is undefined for a tree oid produced by the conflict-exit path.

## Positive Evidence

Future detectors should report a finding when workflow text, bundle evidence, or trace evidence shows any of these states:

- The success path does not record `merge-tree.status=0`, preserve stdout and stderr sidecars, set `PREDICTED_TREE` from a valid first stdout line, and continue.
- The content-conflict path treats `merge-tree.status=1` with a valid first stdout line as `BLOCKED:merge-tree-failed`, drops the first-line oid, truncates conflict descriptors from `merge-tree.out`, or halts before rebase.
- The real-failure path continues when status is `>=2`, or when the first stdout line is missing, empty, or not a valid SHA-1 or SHA-256 tree oid.
- `merge-tree.out`, `merge-tree.err`, or `merge-tree.status` is missing from the documented bundle artifacts, or these files are documented as conditional on a continued workflow only.
- The documented oid validity rule accepts arbitrary non-empty stdout instead of requiring a 40-hex or 64-hex first line that resolves as a tree object.
- The residual diff section no longer consumes the accepted `PREDICTED_TREE`, or it implies the conflict-exit tree oid is not a valid tree input for the residual-patch comparison.

## Non-Fire Cases

This eval must not fire when the workflow distinguishes the three prediction statuses correctly:

- `rc=0` with a valid first-line tree oid sets `PREDICTED_TREE`, records status `0`, and continues.
- `rc=1` with a valid first-line tree oid sets `PREDICTED_TREE`, records status `1`, preserves the full stdout stream, and continues to the rebase and residual-diff phases.
- `rc>=2`, missing stdout, empty first line, or invalid first-line oid stops with `BLOCKED:merge-tree-failed`.
- Historical bundles that predate ACR-260 are missing `merge-tree.status`; old bundles are not evidence of a post-fix workflow defect by themselves.
- Binary or unsupported cases still block when ort cannot produce a valid first-line tree oid or when the prediction command status is `>=2`.

## Required Trace Fields

Future runnable detectors must consume evidence by semantic role, not by one raw storage schema. Required fields are:

| Required trace field | Evidence role | Purpose |
|---|---|---|
| `wu_id` | root dispatch or planning metadata | Identifies the Work Unit under review. |
| `root_invocation_uuid` | saved trace or run log | Joins workflow, bundle, and audit evidence. |
| `workflow_snapshot_path` | repository snapshot or diff | Locates `workflows/verified-rebase.md`. |
| `predict_section_locator` | workflow markdown range | Locates `### 4. Predict`. |
| `bundle_schema_locator` | workflow markdown range | Locates documented bundle artifacts. |
| `compute_diffs_locator` | workflow markdown range | Locates `### 7. Compute diffs`. |
| `prediction_command_shape` | workflow markdown or trace | Confirms the `merge-tree --write-tree --merge-base="$PRE_BASE" "$PRE_TIP" "$NEW_TARGET"` command shape. |
| `merge_tree_status` | `$BUNDLE/merge-tree.status` or synthetic trace role | Supplies the numeric prediction command status. |
| `merge_tree_out` | `$BUNDLE/merge-tree.out` or synthetic trace role | Supplies stdout, including first-line tree oid and later conflict descriptors. |
| `merge_tree_err` | `$BUNDLE/merge-tree.err` or synthetic trace role | Supplies stderr sidecar evidence. |
| `merge_tree_first_line` | parsed stdout role | Supplies the candidate `PREDICTED_TREE` value. |
| `predicted_tree_oid_validity` | tree validation role | Records whether the first line is 40-hex or 64-hex and resolves as a tree. |
| `predicted_tree` | `refs.json` or trace role | Supplies the accepted predicted tree. |
| `post_tip_tree` | `POST_TIP^{tree}` trace role | Supplies the downstream comparison tree. |
| `residual_patch_path` | `$BUNDLE/residual.patch` | Shows residual diff production. |
| `conflict_artifacts_path` | `$BUNDLE/conflict-artifacts/` | Shows post-rebase conflict provenance. |
| `verdict_source_path` | `summary.md` or workflow verdict section | Shows whether the workflow halted or produced a reviewable verdict. |
| `trace_locator` | saved trace node ids, invocation UUIDs, paths | Lets reviewers locate the evidence chain. |

## Finding Contract By Behavior

Each behavior-level finding must preserve the minimum fields `eval_id`, `severity`, `evidence_paths`, `summary`, `suggested_action`, and `confidence`. The `behavior_id`, `wu_id`, `phase`, `gate`, and `trace_locator` fields are required extensions for this eval.

### B1

- `behavior_id`: `B1`
- `target`: `workflows/verified-rebase.md:164-170` (`### 4. Predict`) and `workflows/verified-rebase.md:85-119` (`PREDICTED_TREE` reference and bundle schema)
- `acceptance_signal`: The workflow documents that `rc=0` with a valid first-line stdout tree oid writes `merge-tree.status` containing `0`, preserves `merge-tree.out` and `merge-tree.err`, sets `PREDICTED_TREE` to the stripped first-line oid, and continues to `### 5. Rebase`.
- `negation_signal`: The workflow still treats any non-empty stdout or status `0` without first-line tree validation as sufficient, omits `merge-tree.status=0`, drops sidecar output, or fails to continue after a valid success prediction.
- `lifecycle`: `WRITE`
- `eval_id`: `acr-260`
- `severity`: `MEDIUM`
- `evidence_paths`: `[workflow_snapshot_path, predict_section_locator, bundle_schema_locator, merge_tree_status, merge_tree_out, merge_tree_err]`
- `summary`: Success-path prediction capture is incomplete or ambiguous for status `0` with a valid first-line tree oid.
- `suggested_action`: Revise `### 4. Predict` and the bundle schema so success capture records status, stdout, stderr, validated `PREDICTED_TREE`, and continuation.
- `confidence`: `HIGH` when the workflow text or bundle evidence omits one of the required status, stdout, stderr, validation, or continuation signals; `MEDIUM` when only locator evidence is partial.

### B2

- `behavior_id`: `B2`
- `target`: `workflows/verified-rebase.md:164-170` (`### 4. Predict`), `workflows/verified-rebase.md:210-241` (`### 7. Compute diffs` and verdict rules), and `workflows/verified-rebase.md:327-344` (T2 text-conflict contract)
- `acceptance_signal`: The workflow documents that `rc=1` with a valid first-line stdout tree oid writes `merge-tree.status` containing `1`, preserves full multi-line `merge-tree.out`, sets `PREDICTED_TREE` to the stripped first-line oid, does not halt, and proceeds to rebase, conflict-artifact capture, and residual diff computation.
- `negation_signal`: The workflow stops with `BLOCKED:merge-tree-failed` solely because status is `1`, discards the first-line oid, truncates conflict descriptors, or treats `merge-tree.status=1` as a direct dirty or blocked verdict input.
- `lifecycle`: `WRITE`
- `eval_id`: `acr-260`
- `severity`: `HIGH`
- `evidence_paths`: `[workflow_snapshot_path, predict_section_locator, compute_diffs_locator, verdict_source_path, merge_tree_status, merge_tree_out, conflict_artifacts_path, residual_patch_path]`
- `summary`: Content-conflict prediction capture blocks or loses a usable first-line tree oid when `merge-tree` exits `1`.
- `suggested_action`: Revise the prediction contract so status `1` plus a valid first-line tree oid is a continued content-conflict path, not `BLOCKED:merge-tree-failed`.
- `confidence`: `HIGH` when status `1` with a valid tree oid is documented or observed as blocked; `MEDIUM` when continuation evidence is incomplete but the stop rule is ambiguous.

### B3

- `behavior_id`: `B3`
- `target`: `workflows/verified-rebase.md:164-170` (`### 4. Predict`) and `workflows/verified-rebase.md:327-344` (binary or unsupported contract row)
- `acceptance_signal`: The workflow documents that status `>=2`, missing stdout, empty first line, or invalid first-line oid halts with the literal token `BLOCKED:merge-tree-failed`.
- `negation_signal`: The workflow continues after status `>=2`, continues without a valid first-line oid, silently downgrades an unexpected status above `1` into a content-conflict path, or renames/removes the literal `BLOCKED:merge-tree-failed` token.
- `lifecycle`: `WRITE`
- `eval_id`: `acr-260`
- `severity`: `HIGH`
- `evidence_paths`: `[workflow_snapshot_path, predict_section_locator, merge_tree_status, merge_tree_out, predicted_tree_oid_validity, verdict_source_path]`
- `summary`: Real prediction failures are not halted with `BLOCKED:merge-tree-failed`.
- `suggested_action`: Restore the real-failure boundary: status outside `0` or `1`, empty stdout, or invalid first-line tree oid must halt with the documented token.
- `confidence`: `HIGH` when continuation is documented or observed for status `>=2` or invalid first-line oid; `MEDIUM` when status or oid evidence is incomplete.

### B4

- `behavior_id`: `B4`
- `target`: `workflows/verified-rebase.md:104-119` (bundle schema) and `workflows/verified-rebase.md:164-170` (`### 4. Predict`)
- `acceptance_signal`: The workflow documents that `$BUNDLE/merge-tree.out`, `$BUNDLE/merge-tree.err`, and `$BUNDLE/merge-tree.status` are written before classification, so they exist whether the workflow later halts or continues.
- `negation_signal`: The workflow documents these artifacts only for the continued path, omits any of the three artifacts, writes status after a possible halt, or records the status under a different prediction metadata name.
- `lifecycle`: `WRITE`
- `eval_id`: `acr-260`
- `severity`: `MEDIUM`
- `evidence_paths`: `[workflow_snapshot_path, bundle_schema_locator, predict_section_locator, merge_tree_status, merge_tree_out, merge_tree_err]`
- `summary`: Prediction command sidecar artifacts are missing or not guaranteed on halt and continue paths.
- `suggested_action`: Document sidecar capture before classification and add the three bundle rows with stable names.
- `confidence`: `HIGH` when one or more sidecar names is absent or conditional; `MEDIUM` when the schema and predict prose disagree.

### B5

- `behavior_id`: `B5`
- `target`: `workflows/verified-rebase.md:164-170` (`### 4. Predict`) and `workflows/verified-rebase.md:85-94` (`PREDICTED_TREE` reference)
- `acceptance_signal`: The workflow documents that the first line of `merge-tree.out` is stripped and accepted only when it is a 40-hex SHA-1 or 64-hex SHA-256 oid that resolves as a tree; empty or non-conforming first lines force the B3 path.
- `negation_signal`: The workflow accepts arbitrary non-empty stdout, accepts a non-tree object, falls back to `POST_TIP^{tree}` or another substitute, or lets status `0` or `1` override missing or invalid first-line oid evidence.
- `lifecycle`: `WRITE`
- `eval_id`: `acr-260`
- `severity`: `HIGH`
- `evidence_paths`: `[workflow_snapshot_path, predict_section_locator, merge_tree_out, merge_tree_first_line, predicted_tree_oid_validity, predicted_tree]`
- `summary`: `PREDICTED_TREE` oid validation is absent or too weak.
- `suggested_action`: Require first-line SHA-1 or SHA-256 tree-oid validation before classifying success or content conflict.
- `confidence`: `HIGH` when the workflow accepts unvalidated stdout or fallback trees; `MEDIUM` when validation is named but not tied to the first stdout line.

### B6

- `behavior_id`: `B6`
- `target`: `workflows/verified-rebase.md:210-219` (`### 7. Compute diffs`) and `workflows/verified-rebase.md:226-241` (verdict rules)
- `acceptance_signal`: The workflow keeps `git diff "$PREDICTED_TREE" "$POST_TIP^{tree}" --find-renames > "$BUNDLE/residual.patch"` defined for any accepted tree oid written by `merge-tree --write-tree`, including the `rc=1` content-conflict path, and keeps verdict classification based on residual, conflict-artifact, and range-diff evidence rather than prediction status alone.
- `negation_signal`: The workflow removes `PREDICTED_TREE` from residual diff computation, documents status `1` as incompatible with residual diff, uses `POST_TIP^{tree}` as a fallback prediction tree, or turns `merge-tree.status=1` into a direct dirty or blocked verdict.
- `lifecycle`: `WRITE`
- `eval_id`: `acr-260`
- `severity`: `HIGH`
- `evidence_paths`: `[workflow_snapshot_path, compute_diffs_locator, predicted_tree, post_tip_tree, residual_patch_path, conflict_artifacts_path, verdict_source_path]`
- `summary`: Downstream residual diff no longer tolerates the accepted conflict-exit predicted tree.
- `suggested_action`: Preserve residual diff consumption of the accepted `PREDICTED_TREE` and keep prediction status out of direct verdict classification.
- `confidence`: `HIGH` when the residual-diff command or verdict rules contradict this contract; `MEDIUM` when bundle evidence proves prediction capture but residual production is missing.

## Lifecycle Notes

Current state is `WRITE`. This file defines the expected post-fix behavior and finding schema only. Future detector work owns runnable adapters, rollout evidence, false-positive review, and enforcement readiness.

## Anti-Scope

This WU must not produce runnable eval code, parser code, verifier scripts, shell proof runners, CLI integration, scheduler wiring, CI wiring, ticket automation, or new client/runtime wrappers for ACR-260. The only structural-verification artifact in this WU is this markdown eval specification.

## Cross-References

- `/home/nes/ai/conventions/evals.md`
- `/home/nes/ai/planning/acr-260-merge-tree-predicted-tree-oid/contracts/acr-260-merge-tree-capture.md`
- `/home/nes/ai/planning/acr-260-merge-tree-predicted-tree-oid/proposals/acr-260-acr-260.md`
- `/home/nes/ai/planning/acr-260-merge-tree-predicted-tree-oid/research/acr-260-problem-map.md`
- `/home/nes/ai/planning/acr-260-merge-tree-predicted-tree-oid/research/acr-260-hookpoints.md`
- `/home/nes/ai/planning/acr-260-merge-tree-predicted-tree-oid/research/acr-260-lifecycle-map.md`
