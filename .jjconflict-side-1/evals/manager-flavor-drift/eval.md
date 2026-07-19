---
eval_id: manager-flavor-drift
behavior_class: Manager-flavor drift
lifecycle_state: WRITE
severity_when_fires: HIGH
evidence_source_kinds:
  - agents-trace-json
  - dispatch-prompt
  - agent-log
  - audit-bundle
  - process-tree-audit
suggested_action_class: halt-pipeline
---

# Manager-Flavor Drift

## Eval identity

This is a markdown behavior specification for `manager-flavor-drift`, not runnable eval code. It detects dispatched orchestration or child prompts using a manager flavor other than the WU's declared active flavor.

References: `conventions/evals.md`, `workflows/eval-runtime.md`, `agents/work-manager-operator.md`, manager flavor files, `conventions/agent-questions-and-session-graph.md`, and the ACR-174 deletion contract.

## Unwanted behavior

The unwanted behavior is trace-detectable flavor mismatch: the WU/session declares one active flavor, but a child dispatch, orchestration prompt, NEEDS_INPUT answer, or policy citation applies a different flavor without manager authorization.

## Positive evidence

- The root session, ticket brief, dispatch prompt, or manager context declares `manager-max`, `manager-pragmatic`, or `manager-hackerman`.
- A child invocation prompt, operator input, policy citation, or answer artifact uses a different flavor.
- The mismatch is tied to a prompt file path, invocation UUID, or session graph edge.
- No manager authorization artifact records an intentional flavor change.

## Non-fire cases

- No flavor is declared and the trace correctly defaults to `manager-max`.
- A manager-authorized flavor change is recorded before dependent dispatches.
- A child task is flavor-neutral and does not apply flavor-specific policy.
- Historical examples quote another flavor only as evidence and do not control the run.

## Required trace fields

The future eval implementation must read WU/session identity, root flavor declaration, child dispatch prompt, invocation UUID, prompt file path, session graph edges, and manager authorization artifacts by semantic role. It should prefer saved `agents trace --json` plus prompt/report paths over raw `state.db` schema assumptions.

## Finding shape

The finding preserves `eval_id`, `severity`, `evidence_paths`, `summary`, `suggested_action`, and `confidence`. Extensions may include `declared_flavor`, `actual_flavor`, `invocation_uuid`, `prompt_path`, and `authorization_path`.

## Suggested action

Return `halt-pipeline` when a live decision path used the wrong flavor. The owning workflow should rewind or re-dispatch the affected work under the declared flavor unless the manager records an intentional change.

## Lifecycle notes

ACR-175 seeds this eval in `WRITE`. Downstream implementation tickets own runnable detector code, fixtures, rollout in advisory mode, false-positive review, and enforcement readiness. This spec must not become a structural markdown test or wire itself into `AGENTS.md`, `workflows/index.json`, CI, cron, Jira, Linear, or agent-runner runtime code.
