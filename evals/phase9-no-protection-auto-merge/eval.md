---
eval_id: phase9-no-protection-auto-merge
behavior_class: Phase 9 direct squash auto-merge override drift
lifecycle_state: WRITE
severity_when_fires: HIGH
---

# Phase 9 Direct Squash Auto-Merge Override

## Eval identity

This is a markdown behavior specification for `phase9-no-protection-auto-merge`, not runnable eval code. It defines a future detector shaped as `trace -> finding | None` over the implementation-pipeline orchestrator text and related review evidence for the Phase 9 `Auto-merge override` behavior.

The policy-source authority is `agents/implementation-pipeline-orchestrator.md`, specifically the optional input description for `auto_merge_after_phase_9` and the Phase 9 `Auto-merge override` block at lines 600-606 (`nl -ba agents/implementation-pipeline-orchestrator.md | sed -n '600,606p'`). This eval is WRITE-state under `/home/nes/ai/conventions/evals.md`; it must not revive pytest, structural Markdown tests, runtime wiring, fixtures, or enforcement hooks.

## Unwanted behavior

The unwanted behavior is Phase 9 auto-merge text that reintroduces auto-wait, branch-protection detection, diagnostic-text fallback, or an underspecified halt contract instead of the D1 direct-squash contract.

Fire conditions:

- The `auto_merge_after_phase_9` input description does not say the override runs direct squash unconditionally after readying the PR.
- The Phase 9 `Auto-merge override` block does not list `gh pr ready ${pr_url}` exactly once as the first command.
- The Phase 9 `Auto-merge override` block does not list `gh pr merge --squash ${pr_url}` exactly once as the second command.
- The Phase 9 `Auto-merge override` block contains any of these forbidden protection-detection or fallback surfaces: `--auto`, `gh api`, `/protection`, `baseRefName`, `nameWithOwner`, branch-protection detection, or `Protected branch rules not configured`.
- The Phase 9 `Auto-merge override` block omits the requirement that either command failure surfaces a NEEDS_INPUT halt with `path=auto-merge-direct`, `selected_command=<the failing command>`, and `captured_output=<command stdout+stderr>`.
- The Phase 9 `Auto-merge override` block retries, falls back, classifies branch protection, parses command diagnostics, or otherwise makes a second merge decision after a command failure.
- The eval or implementation attempts to satisfy this behavior by adding pytest, structural Markdown tests, runtime wiring, fixtures, or additional eval indices instead of this WRITE-state spec.

## Positive evidence

The future eval implementation fires when evidence from the orchestrator document or review bundle shows the unwanted behavior above.

Positive evidence examples:

- The override block still invokes auto-wait instead of direct squash.
- The override block queries GitHub PR, repository, or branch-protection metadata before choosing the merge command.
- The override block matches a GitHub CLI diagnostic string to decide whether direct squash is allowed.
- The ready command is missing, duplicated, or appears after the merge command.
- The direct squash command is missing, duplicated, or guarded behind a protection-classification branch.
- The failure text does not expose the failing command and combined stdout/stderr to the root-facing NEEDS_INPUT halt.
- The trace or diff introduces pytest, structural Markdown assertions, runnable eval code, fixtures, or index wiring for this behavior rather than the WRITE-state eval-spec path.

## Non-fire cases

The eval must not fire when `auto_merge_after_phase_9=false` remains the default and the normal draft-PR path does not attempt auto-merge.

The eval must not fire when the existing ready-for-review step remains unchanged before merge handling.

The eval must not fire when the Phase 9 `Auto-merge override` block is the D1 direct-squash contract:

- first command is exactly `gh pr ready ${pr_url}`;
- second command is exactly `gh pr merge --squash ${pr_url}`;
- the block contains none of the forbidden auto-wait, protection-detection, or diagnostic-fallback surfaces listed above;
- either command failure emits NEEDS_INPUT with `path`, `selected_command`, and `captured_output`, and does not retry.

The eval must not fire merely because no runnable eval adapter, fixture, parser, CI hook, or pytest test exists; WRITE-state eval specs are reviewable behavior specifications.

## Required trace and policy fields

The future eval implementation must read evidence by semantic role, not by one raw storage schema. Required inputs:

- policy source path: `agents/implementation-pipeline-orchestrator.md`;
- the Phase 9 `Auto-merge override` block;
- the optional input description for `auto_merge_after_phase_9`;
- the ordered command list inside the override block;
- the root-facing NEEDS_INPUT halt fields for override command failure;
- the WRITE-state eval convention: `/home/nes/ai/conventions/evals.md`.

The detector should prefer saved `agents trace --json`, dispatch prompts, agent logs, review/audit bundles, and the orchestrator markdown diff over raw state database assumptions. Evidence joins may use invocation UUID, parent invocation ID, root invocation UUID, prompt file path, session graph semantics, artifact paths, and review bundle paths.

## Finding shape

Findings preserve the minimum schema fields from `/home/nes/ai/conventions/evals.md`: `eval_id`, `severity`, `evidence_paths`, `summary`, `suggested_action`, and `confidence`.

Allowed extensions include `wu_id`, `session_id`, `root_invocation_uuid`, `phase`, `policy_source`, `phase9_block_locator`, `input_description_locator`, `command_order`, `forbidden_surface`, `halt_field`, `trace_locator`, and `report_paths`.

Severity is `HIGH` when the missing or unsafe behavior can reintroduce the no-protection auto-wait failure, branch-protection detection coupling, diagnostic-text fallback coupling, or an unstructured halt on merge failure.

## Suggested action

Return `revise_phase9_auto_merge_override` when the future detector finds this behavior. The owning workflow should revise the Phase 9 `Auto-merge override` and `auto_merge_after_phase_9` input description back to the D1 direct-squash contract.

## Lifecycle notes

This eval ships in `WRITE` state. No runnable detector, fixture, parser, CLI integration, CI hook, pytest file, structural Markdown test, or project-level eval index is created by this WU.

Runnable detector code, fixtures, rollout, false-positive review, trace adapters, and enforcement readiness belong to downstream eval-runtime work. This spec is the only test-layer artifact for the D1 prototype vector.

## References

- Prototype dossier answer: `/home/nes/projects/ai/planning/prototype-acr-193-clarify/dossier/answer.md`
- Prior round-6 aggregate code-quality report: `/home/nes/projects/ai/planning/acr-193-phase9-no-protection-fallback/code-quality/acr-193-phase-4/aggregate-code-quality.md`
- Prior coupling-auditor report: `/home/nes/projects/ai/planning/acr-193-phase9-no-protection-fallback/code-quality/acr-193-phase-4/reports/coupling-auditor.md`
- Prior push-pull-auditor report: `/home/nes/projects/ai/planning/acr-193-phase9-no-protection-fallback/code-quality/acr-193-phase-4/reports/push-pull-auditor.md`
- Evals convention: `/home/nes/ai/conventions/evals.md`
