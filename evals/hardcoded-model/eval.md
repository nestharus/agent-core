---
eval_id: hardcoded-model
behavior_class: Hardcoded model
lifecycle_state: WRITE
severity_when_fires: LOW
evidence_source_kinds:
  - agents-trace-json
  - dispatch-prompt
  - agent-log
  - audit-bundle
  - process-tree-audit
suggested_action_class: file-followup-ticket
---

# Hardcoded Model

## Eval identity

This is a markdown behavior specification for `hardcoded-model`, not runnable eval code. It detects agent/workflow docs that hardcode concrete model names where role indirection is required.

References: `conventions/evals.md`, relevant operator/workflow format conventions, `agents/eval-runner.md`, and the ACR-174 deletion contract.

## Unwanted behavior

The unwanted behavior is trace-detectable model indirection drift: a changed operator or workflow document pins a concrete model string in prose or routing where the local convention requires a role, flavor, or configurable model indirection.

## Positive evidence

- A changed artifact path is an agent, workflow, convention, or routing doc covered by model-indirection rules.
- The diff or final file content includes a concrete model string.
- The applicable local convention requires role/model indirection for that location.
- No explicit exception, catalog role, or user-specified override authorizes the concrete value.

## Non-fire cases

- Reference-only model catalogs or historical examples quoted as evidence.
- User-specified model overrides in a dispatch prompt.
- Files whose frontmatter contract explicitly requires a concrete `model:` field.
- Compatibility documentation explaining past model names without routing current execution.

## Required trace fields

The future eval implementation must read changed file content or diff, path/category, applicable operator/workflow format rule, dispatch prompt context, exception evidence, and model string location by semantic role. It should prefer saved `agents trace --json` plus diff artifacts over raw `state.db` schema assumptions.

## Finding shape

The finding preserves `eval_id`, `severity`, `evidence_paths`, `summary`, `suggested_action`, and `confidence`. Extensions may include `model_string`, `path`, `rule_source`, `exception_path`, and `line_reference`.

## Suggested action

Return `file-followup-ticket` when this eval fires. The owner should replace the concrete model with the required role indirection or record a valid exception. Scope-local remediation details can be carried in finding extensions.

## Lifecycle notes

ACR-175 seeds this eval in `WRITE`. Downstream implementation tickets own runnable detector code, fixtures, rollout in advisory mode, false-positive review, and enforcement readiness. This spec must not become a structural markdown test or wire itself into `AGENTS.md`, `workflows/index.json`, CI, cron, Jira, Linear, or agent-runner runtime code.
