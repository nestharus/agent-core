---
id: workspace-rust-gates-hard-stop
slug: workspace-rust-gates-hard-stop
eval_id: workspace-rust-gates-hard-stop
lifecycle: WRITE
lifecycle_state: WRITE
class: structural-verification
behavior_class: implementation-pipeline-workspace-rust-gate-hard-stop
created: 2026-05-24
owner: ACR-299
ticket: ACR-299
ticket_mapping:
  - ACR-299
severity_when_fires: HIGH
evidence_source_kinds:
  - repository-file-content
  - planning-directory-artifacts
  - agents-trace-json
  - process-tree-auditor-report
  - workflow-process-auditor-report
suggested_action_class: repair-implementation-pipeline-step-6c-gate-recipe
description: WRITE-state structural verification for the implementation-pipeline Step 6c workspace-scoped Rust gate recipe and hard-stop-on-red merge disposition.
---

# Workspace Rust Gates Hard Stop Eval

## Eval identity

This is a markdown behavior specification for `workspace-rust-gates-hard-stop`, not runnable eval code. It detects drift in the implementation-pipeline operator's Step 6c gate recipe when the recipe fails to require workspace-scoped Rust gates, weakens the merge-gate hard stop on a red workspace baseline, misuses rebase-verification as merge authorization, drops frontend gates, or allows sibling live merge/gate recipes to keep crate-scoped Rust commands.

The policy-source authority is the ACR-299 contract for `workspace-rust-gates-hard-stop`, the ACR-299 proposal test-intent track, and `conventions/evals.md`. The primary repository source under review is `agents/implementation-pipeline-orchestrator.md` Step 6c step 7.

Lifecycle: `WRITE`.

## Unwanted behavior

The unwanted behavior is an implementation-pipeline Step 6c gate recipe that lets a future Work Unit appear merge-ready without running workspace-scoped Rust gates and without treating any red workspace gate as a merge-gate hard stop.

The violation applies to the live Step 6c gate recipe in `agents/implementation-pipeline-orchestrator.md` and to future live merge/gate recipes under `agents/*.md` or `workflows/*.md` that hardcode crate-scoped Rust verification commands. Historical examples, non-merge prototype notes, and the distinct rebase-attribution convention are not violations by themselves.

## Positive evidence

The future detector should produce a finding when any of these scenario-specific signals appear in the evidence bundle.

### E1: Recipe text is not workspace-scoped

Flag when `agents/implementation-pipeline-orchestrator.md` Step 6c step 7 lacks `cargo clippy --workspace --all-targets -- -D warnings`, lacks `cargo test --workspace`, fails to preserve `cargo fmt --check`, changes the fmt command to include `--all`, or keeps a standalone crate-scoped `cargo clippy -- -D warnings` / `cargo test` gate as the live recipe.

### E2: Hard stop on red is weakened

Flag when the Step 6c recipe allows any non-green-restoring WU to proceed to merge while the workspace gate is red, treats a pre-existing red workspace baseline as mergeable for an unrelated WU, or introduces a baseline-disposition, residual-acceptance, intent-reading, user-discretion, or bootstrap escape at the merge gate.

### E3: Rebase verification is treated as merge authorization

Flag when the Step 6c recipe cites or implies `conventions/rebase-verification.md` as authorization to merge onto a red tree, or fails to distinguish rebase-attribution from the Step 6c merge-gate hard stop.

### E4: Frontend gates are dropped

Flag when the Step 6c recipe omits any of the existing frontend gates: `bun run lint`, `bun run typecheck`, or `bun run test`.

### E5: Sibling live gate recipe keeps crate-scoped Rust commands

Flag when any live merge/gate recipe under `agents/*.md` or `workflows/*.md` hardcodes crate-scoped `cargo test` or `cargo clippy -- -D warnings` instead of the workspace-scoped recipe.

### E6: Step 6c retry semantics are changed

Flag when the Step 6c recipe no longer says failed gates re-dispatch the **code agent** with the failure output, or no longer says a wrong test requires revising the contract first and regenerating tests from the revised contract.

### E7: Edit scope expands beyond the Step 6c recipe

Flag when the ACR-299 product edit changes unrelated lines or sections of `agents/implementation-pipeline-orchestrator.md`, or broadens into an implementation-pipeline refactor instead of replacing the single Step 6c step 7 recipe line.

## Non-fire cases

- `agents/implementation-pipeline-orchestrator.md` Step 6c step 7 contains `cargo fmt --check`, `cargo clippy --workspace --all-targets -- -D warnings`, `cargo test --workspace`, `bun run lint`, `bun run typecheck`, and `bun run test`, with no `cargo fmt --all`.
- The Step 6c recipe states that any failing gate, including a pre-existing red workspace baseline, is a hard stop at the merge gate; only the green-restoring fix may proceed while the workspace gate is red.
- The Step 6c recipe cites `conventions/rebase-verification.md` only to state that rebase-attribution is distinct and does not authorize merging onto a red tree.
- The Step 6c recipe preserves the existing retry semantics: failed gates re-dispatch the **code agent**, and wrong tests require contract revision before regenerated tests.
- `agents/prototype-orchestrator.md:163` says prototype P1 work has no mid-flight gates. This is not a live merge/gate recipe and does not mention the crate-scoped clippy gate.
- `conventions/rebase-verification.md:24` uses `cargo test --workspace` for the distinct rebase verification branch. This is not Step 6c merge authorization and is already workspace-scoped.
- Historical quotes, research notes, proposal text, contracts, and eval specs may mention pre-edit crate-scoped commands as examples of unwanted behavior, provided they are not the active live recipe.

## Required trace fields

The future runnable detector must read these semantic evidence fields:

- `agents/implementation-pipeline-orchestrator.md` path, content hash, Step 6c heading locator, step 7 text, and surrounding retry-semantics text.
- Extracted command tokens from the Step 6c gate recipe, including Rust, fmt, and frontend commands.
- Evidence of hard-stop disposition text, including whether the recipe permits a non-green-restoring WU, baseline disposition, residual acceptance, intent-reading, user discretion, or bootstrap exception at merge.
- Cross-reference usage for `conventions/rebase-verification.md`, including whether the citation is framed as distinct rebase-attribution or merge authorization.
- Sibling sweep results for `agents/*.md` and `workflows/*.md`, with path, line, heading context, and whether each hit is a live merge/gate recipe, historical/example text, prototype no-gate text, or rebase-attribution text.
- Diff-scope evidence for ACR-299 product edits to `agents/implementation-pipeline-orchestrator.md`, including changed-line count and changed-section locator when available.
- Planning artifacts that identify this WU, including the ACR-299 contract, proposal test-intent track, Step 6b output index, process-tree reports, workflow-process reports, and audit-history references when present.

The preferred evidence boundary is saved repository content plus saved `agents trace --json` or planning-directory artifacts. Raw state database evidence is best-effort only and must be resolved behind trace or artifact semantic roles.

## Finding shape

Every future finding from this spec preserves these required keys from `conventions/evals.md`:

- `eval_id`
- `severity`
- `evidence_paths`
- `summary`
- `suggested_action`
- `confidence`

Allowed extensions include `scenario_id`, `wu_id`, `phase`, `gate`, `policy_source`, `recipe_path`, `recipe_locator`, `sibling_path`, `sibling_locator`, `missing_commands`, `forbidden_commands`, `escape_text`, `rebase_reference_text`, `frontend_commands_missing`, `diff_scope_summary`, `root_invocation_uuid`, `trace_locator`, and `report_paths`.

Scenario ids are `E1`, `E2`, `E3`, `E4`, `E5`, `E6`, and `E7`. Findings for this eval should use `severity=HIGH` when the live Step 6c merge gate can produce a false green or permit merge over a red workspace gate, and `severity=MEDIUM` only for sibling drift that is not yet reachable from the implementation-pipeline Step 6c merge path.

## Suggested action

Return `repair-implementation-pipeline-step-6c-gate-recipe` for Step 6c recipe drift. The owner should restore the exact workspace-scoped Rust gate commands, preserve `cargo fmt --check` without `--all`, preserve the frontend gates, re-establish hard-stop-on-red language with no baseline or bootstrap escape, keep rebase-verification distinct from merge authorization, and preserve the existing code-agent retry and contract-regeneration semantics.

Return `repair-sibling-live-gate-recipe` for sibling live merge/gate recipes that hardcode crate-scoped Rust commands, unless the sibling evidence is a non-fire case listed above.

## Lifecycle notes

ACR-299 seeds this eval in `WRITE`. Downstream work owns runnable detector code, fixtures, rollout, false-positive review, trace-field adapters, and any transition to `ROLL_OUT`, `ENFORCE`, or `MAINTAIN`.

This spec must not create pytest files, pytest imports, pytest fixtures, pytest-shaped assertion code, `tools/<wu>-verify/*.py`, CI wiring, scheduler wiring, ticket-backend automation, or direct edits to implementation-pipeline runtime code. It is a behavior specification only.

## References

- `agents/implementation-pipeline-orchestrator.md`
- `conventions/evals.md`
- `conventions/rebase-verification.md`
- `agents/prototype-orchestrator.md`
- ACR-299 contract: `contracts/acr-299-workspace-rust-gates-hard-stop.md`
- ACR-299 proposal: `proposals/acr-299-ACR-299.md`
