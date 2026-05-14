---
eval_id: phase9-no-protection-auto-merge
behavior_class: Phase 9 no-protection auto-merge fallback missing or unsafe
lifecycle_state: WRITE
severity_when_fires: HIGH
---

# Phase 9 No-Protection Auto-Merge Fallback

## Eval identity

This is a markdown behavior specification for `phase9-no-protection-auto-merge`, not runnable eval code. It defines a future detector shaped as `trace -> finding | None` over the implementation-pipeline orchestrator text and related review evidence for the Phase 9 `Auto-merge override` behavior.

The policy-source authority is `agents/implementation-pipeline-orchestrator.md`, specifically the optional input description for `auto_merge_after_phase_9` and the Phase 9 `Auto-merge override` block. This eval is WRITE-state under `/home/nes/ai/conventions/evals.md` and `D-2026-05-13-acr193-test-format-eval-spec`; it must not revive pytest or structural Markdown tests.

## Unwanted behavior

The unwanted behavior is Phase 9 auto-merge text that can still halt on an unprotected base branch because it lacks protection-aware merge selection or uses an unsafe fallback.

Fire conditions:

- The Phase 9 `Auto-merge override` does not build the workflow-owned `phase9-protection-decision` contract before choosing a merge command.
- Step 9-Auto.B merge selection is missing, is not keyed only by contract `kind`, or consumes detection details beyond `kind` for command selection.
- The protected path no longer selects `gh pr merge --auto --squash ${pr_url}`.
- The unprotected path no longer selects `gh pr merge --squash ${pr_url}`.
- The detection-failed path retries direct squash without the first-exit-status-gated narrow fallback.
- The detection-failed fallback becomes unbounded, loops, retries unrelated failures, or treats detection failure as permission to skip the root-facing halt path.
- Per-`kind` merge command outputs are not declared as grouped evidence for downstream halt/reporting.
- Step 9-Auto.C does not emit the grouped `NEEDS_INPUT:phase9-auto-merge-failed` halt contract when selected merge handling fails.
- The `auto_merge_after_phase_9` input description still promises unconditional `gh pr merge --auto --squash ${pr_url}` behavior instead of protected/unprotected/detection-failed selection.
- The eval or implementation attempts to satisfy this WU by adding pytest, structural Markdown tests, runtime wiring, fixtures, or extra evals instead of this WRITE-state spec.

## Positive evidence

The future eval implementation fires when evidence from the orchestrator document or review bundle shows the unwanted behavior above.

Positive evidence examples:

- The Phase 9 `Auto-merge override` text lacks a named `phase9-protection-decision` section before merge selection.
- The Phase 9 text lacks a Step 9-Auto.B rule that selects the merge command from contract `kind`.
- The Step 9-Auto.B text does not preserve the protected, unprotected, and detection-failed selection cases with their required command outcomes.
- The detection-failed case does not gate the narrow fallback on the first auto-merge command's nonzero exit and the specific no-protection diagnostic.
- The Phase 9 text lacks grouped per-`kind` merge command outputs for failure reporting.
- The Phase 9 text lacks the Step 9-Auto.C root-facing halt contract.
- The optional input description still describes a single unconditional auto-merge command instead of protection-aware selection.
- The trace or diff introduces a pytest/structural-test artifact for this behavior rather than the WRITE-state eval-spec path.

## Non-fire cases

The eval must not fire when `auto_merge_after_phase_9=false` remains the default and the normal draft-PR path does not attempt auto-merge.

The eval must not fire when the existing ready-for-review step remains unchanged before merge handling.

The eval must not fire when the orchestrator text includes the grouped `phase9-protection-decision` contract, Step 9-Auto.B selects only from `kind`, and all three selection cases are present:

- protected kind selects `gh pr merge --auto --squash ${pr_url}`;
- unprotected kind selects `gh pr merge --squash ${pr_url}`;
- detection-failed kind first tries auto-squash and only uses the narrow no-protection direct-squash fallback when the first command failed with the specific diagnostic.

The eval must not fire on policy text that mentions protection detection generally without enumerating Step 9-Auto.A command flags or sub-commands, as long as the grouped contract and selection symbols remain present.

The eval must not fire merely because no runnable eval adapter, fixture, parser, CI hook, or pytest test exists; WRITE-state eval specs are reviewable behavior specifications.

## Required trace and policy fields

The future eval implementation must read evidence by semantic role, not by one raw storage schema. Required inputs:

- policy source path: `/home/nes/projects/ai/worktrees/acr-193-phase9-no-protection-fallback/agents/implementation-pipeline-orchestrator.md`;
- the Phase 9 `Auto-merge override` block;
- the optional input description for `auto_merge_after_phase_9`;
- the grouped `phase9-protection-decision` contract;
- the Step 9-Auto.B selection rule;
- grouped per-`kind` merge command outputs;
- the grouped Step 9-Auto.C halt contract;
- the WRITE-state eval convention and decision citation: `/home/nes/ai/conventions/evals.md` and `D-2026-05-13-acr193-test-format-eval-spec`.

The detector should prefer saved `agents trace --json`, dispatch prompts, agent logs, review/audit bundles, and the orchestrator markdown diff over raw state database assumptions. Evidence joins may use invocation UUID, parent invocation ID, root invocation UUID, prompt file path, session graph semantics, artifact paths, and review bundle paths.

## Finding shape

Findings preserve the minimum schema fields from `/home/nes/ai/conventions/evals.md`: `eval_id`, `severity`, `evidence_paths`, `summary`, `suggested_action`, and `confidence`.

Allowed extensions include `wu_id`, `session_id`, `root_invocation_uuid`, `phase`, `policy_source`, `phase9_block_locator`, `input_description_locator`, `missing_grouped_symbol`, `unsafe_fallback_shape`, `selected_case`, `trace_locator`, and `report_paths`.

Severity is `HIGH` when the missing or unsafe behavior can cause Phase 9 to halt on unprotected branches, retry direct squash too broadly, or omit the root-facing halt contract on merge failure.

## Suggested action

Return `revise_phase9_auto_merge_override` when the future detector finds this behavior. The owning workflow should revise the Phase 9 `Auto-merge override` and `auto_merge_after_phase_9` input description so the grouped contract, Step 9-Auto.B selection rule, grouped per-`kind` command outputs, and Step 9-Auto.C halt contract are all present and consistent.

## Lifecycle notes

This eval ships in `WRITE` state. No runnable detector, fixture, parser, CLI integration, CI hook, pytest file, or structural Markdown test is created by this WU.

Runnable detector code, fixtures, rollout, false-positive review, trace adapters, and enforcement readiness belong to downstream eval-runtime work. This spec is the only Step 6b test-layer artifact for ACR-193.

## References

- Step 6a contract: `/home/nes/projects/ai/planning/acr-193-phase9-no-protection-fallback/contracts/acr-193-phase9-no-protection-fallback.md`
- Round-6 proposal: `/home/nes/projects/ai/planning/acr-193-phase9-no-protection-fallback/proposals/acr-193-ACR-193.md`
- Problem map: `/home/nes/projects/ai/planning/acr-193-phase9-no-protection-fallback/research/acr-193-problem-map.md`
- Evals convention: `/home/nes/ai/conventions/evals.md`
- Decision: `D-2026-05-13-acr193-test-format-eval-spec`
