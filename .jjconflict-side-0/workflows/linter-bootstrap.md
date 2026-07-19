---
workflow:
  id: linter-bootstrap
workflow_dispatch_contract:
  orchestrator: "root orchestrator or workflow operator invoking linter-bootstrap"
  inputs:
    - "target project root or worktree path plus planning directory for linter-bootstrap artifacts"
    - "A1 code-quality convention path or pinned revision and optional per-language scope"
  expectations:
    - "inventories existing target-project CI/linter coverage against A1 code-quality rules"
    - "researches existing ecosystem linters or rule packages for uncovered lint-enforceable A1 rules"
    - "writes a setup-PR proposal mapping proposed lint additions to A1 coverage and residual gaps"
  outputs:
    - "linter coverage inventory artifact under ${planning_dir}/research/linter-bootstrap-inventory.md"
    - "per-rule ecosystem research artifact under ${planning_dir}/research/linter-bootstrap-research.md"
    - "setup-PR proposal artifact under ${planning_dir}/proposals/linter-bootstrap-setup-pr.md"
  non_goals:
    - "does not bootstrap a concrete project's linters while running only the workflow definition"
    - "does not create or define a linter-inventory-agent operator; inventory runs inline unless caller supplies an external artifact"
    - "does not enforce A1 rules that lack existing linter ecosystem coverage"
---
# Linter Bootstrap Workflow

## Workflow Dispatch Surface

### Orchestrator

root orchestrator or workflow operator invoking linter-bootstrap

### Inputs

- target project root or worktree path plus planning directory for linter-bootstrap artifacts
- A1 code-quality convention path or pinned revision and optional per-language scope

### Expectations

- inventories existing target-project CI/linter coverage against A1 code-quality rules
- researches existing ecosystem linters or rule packages for uncovered lint-enforceable A1 rules
- writes a setup-PR proposal mapping proposed lint additions to A1 coverage and residual gaps

### Outputs

- linter coverage inventory artifact under ${planning_dir}/research/linter-bootstrap-inventory.md
- per-rule ecosystem research artifact under ${planning_dir}/research/linter-bootstrap-research.md
- setup-PR proposal artifact under ${planning_dir}/proposals/linter-bootstrap-setup-pr.md

### Non-goals

- does not bootstrap a concrete project's linters while running only the workflow definition
- does not create or define a linter-inventory-agent operator; inventory runs inline unless caller supplies an external artifact
- does not enforce A1 rules that lack existing linter ecosystem coverage

## Purpose

Use this workflow to turn A1 code-quality policy into a project-specific linter setup proposal. The workflow inventories what a target project already enforces, researches existing ecosystem tooling for uncovered lintable A1 rules, and writes a setup-PR proposal for a future implementation unit.

It is a planning workflow. It does not bootstrap linters, change CI, or claim coverage for A1 rules that still require specialized-agent or human judgment.

## When To Use

- A project wants cheaper and more consistent enforcement of lintable A1 code-shape rules before or between implementation work.
- The caller has a target project root, trunk, or worktree path and a planning directory for artifacts.
- Existing linter, typecheck, formatter, CI, or pre-commit coverage is unclear or not mapped back to A1.
- The next useful output is a setup-PR proposal, not immediate package/config edits.

Do not use this workflow when the caller already approved a concrete linter setup PR for implementation, when the task is behavior-test coverage, or when the only uncovered concerns are not linter-enforceable.

## Required Inputs

- `project_root`: target project root, trunk, or worktree path.
- `planning_dir`: artifact destination for the inventory, research, and setup-PR proposal.
- `a1_convention`: path or pinned revision for `~/ai/conventions/code-quality.md`.
- Optional `language_scope`: explicit language, package, workspace, or app slice when the target project is mixed-language.
- Optional `ci_entrypoints_hint`: known lint/check command names when project AGENTS, manifests, or CI files do not make them obvious.

## Outputs

- `${planning_dir}/research/linter-bootstrap-inventory.md`: inventory of target-project languages, existing verification entrypoints, current linter coverage, A1 coverage status, and residual judgment-only gaps.
- `${planning_dir}/research/linter-bootstrap-research.md`: per-rule ecosystem research for uncovered or partially covered lint-enforceable A1 rules.
- `${planning_dir}/proposals/linter-bootstrap-setup-pr.md`: setup-PR proposal mapping proposed dependency, config, and CI additions to A1 coverage and residual gaps.

## Procedure

Run the stages in order. Keep evidence links close to every coverage claim, and carry residual gaps forward rather than smoothing them into success language.

### Stage 1 - Identify

Read the target project `AGENTS.md`, manifests, CI workflow files, task runners, linter configs, formatter configs, pre-commit configs, and existing structural tests. Read the A1 source policy sections for function classification, nesting depth, inline functions, duplicate responsibility, push-vs-pull coupling, numerical thresholds, and failure modes.

<!-- INTENTIONAL: linter-bootstrap is a planning workflow; Stage 1 performs inventory inline and may consume externally supplied `linter-inventory-agent` output, but this workflow must not define or dispatch that optional operator. -->
If the caller provides `linter-inventory-agent` output, consume it as supporting evidence.

Write `${planning_dir}/research/linter-bootstrap-inventory.md` with:

- Project languages, package ecosystems, and workspaces discovered.
- Existing lint, format, typecheck, static-analysis, test, and CI entrypoints with evidence files.
- A per-A1-rule table using statuses `covered`, `partially covered`, `uncovered but lint-enforceable`, `not linter-enforceable`, and `unknown`.
- Evidence links for every covered or partially covered claim.
- Residual A1 judgment rules that remain specialized-agent or human-review territory.

Advance when current verification entrypoints and A1 coverage gaps are named with evidence. Stop as `BLOCKED` if the project root or planning destination is missing, or if no verification entrypoints can be discovered and the caller cannot provide them. Return `NEEDS_INPUT:<artifact_path>` only when a project policy or scope decision blocks classification.

### Stage 2 - Research

Read the Stage 1 inventory, A1 rows marked `uncovered but lint-enforceable`, `partially covered`, or `unknown`, and `~/ai/workflows/research.md` for evidence discipline. Use primary sources for candidate ecosystem tooling: official docs, source repositories, rule catalogs, release notes, and project-local tool conventions.

Write `${planning_dir}/research/linter-bootstrap-research.md` with:

- For each uncovered enforceable A1 rule: candidate linter, rule, package, language support, configuration hook, CI integration surface, expected coverage, limitations, and primary-source citation.
- For each non-covered rule: why existing ecosystem tooling does not cover it.
- A residual-gap table that Stage 3 must carry into the setup-PR proposal.

Advance when each gap has either a cited candidate or a cited no-coverage reason. Stop as `BLOCKED` if evidence is inconclusive for a material setup choice, or if the only viable path is bespoke tooling outside the language ecosystem. Return `NEEDS_INPUT:<artifact_path>` only when choosing a tool requires a user-owned project value decision, such as adopting a new package manager or resolving incompatible style regimes.

### Stage 3 - Setup-PR Proposal

Read the Stage 1 inventory, Stage 2 research, target project AGENTS policy, and `~/ai/workflows/implementation-pipeline.md` for downstream implementation handoff expectations.

Write `${planning_dir}/proposals/linter-bootstrap-setup-pr.md` with:

- Proposed dependency, configuration, command, and CI additions for a future setup PR.
- Mapping from each proposed linter addition to the A1 rules or failure modes it would cover.
- Acceptance criteria for the future implementation unit: configured linter command passes, CI runs it, targeted rules are active, and residual gaps are disclosed.
- Explicit A1 rules that remain specialized-agent or human-review territory.

Success is `SUCCESS_SETUP_PR_PROPOSED` when the setup-PR proposal artifact is written and maps candidate lint additions to A1 coverage and residual gaps. Partial success is acceptable only when explicit as `PARTIAL_SETUP_PR_PROPOSED_WITH_RESIDUAL_GAPS`. A no-op outcome is acceptable as `NO_OP_ALREADY_COVERED_OR_NOT_LINTABLE` when Identify and Research show no useful linter setup work.

## Stop Conditions

- `BLOCKED`: required input missing; target project verification entrypoints cannot be identified; primary evidence for a material tool candidate is inconclusive; only viable path is bespoke tooling outside scope.
- `NEEDS_INPUT:<artifact_path>`: user-owned value or scope decision, such as changing project toolchain policy, choosing between incompatible lint ecosystems, accepting partial enforcement, or resolving conflict between project-local policy and A1.
- `SUCCESS_SETUP_PR_PROPOSED`: setup-PR proposal artifact is complete and maps proposed lint additions to A1 coverage plus residual gaps.
- `PARTIAL_SETUP_PR_PROPOSED_WITH_RESIDUAL_GAPS`: proposal covers some enforceable gaps and names the rest.
- `NO_OP_ALREADY_COVERED_OR_NOT_LINTABLE`: no setup PR is useful because enforceable lint coverage already exists or uncovered rules are not lintable.

## Anti-Scope

- This workflow does NOT enforce A1 rules without existing linter coverage.
- This workflow does NOT invent new linter tooling outside the language ecosystem.
- This workflow does NOT modify a target project's CI / package configs while running only the workflow definition.
- This workflow does NOT create, define, or dispatch the optional `linter-inventory-agent` operator; inventory is performed inline unless the caller supplies an external artifact.
- This workflow does not replace behavior tests, implementation-pipeline gates, specialized A1 auditors, or human review for judgment-heavy rules.

## Adjacent References

- `~/ai/conventions/code-quality.md` - A1 source policy.
- `~/ai/workflows/implementation-pipeline.md` - downstream planning artifact and setup-PR implementation expectations.
- `~/ai/workflows/research.md` - primary-source research discipline for Stage 2.
- `~/ai/workflows/risk-reduction.md` - adjacent workflow for project risk paydown after evidence exists.
- `~/ai/workflows/agents-cli.md` - shared invocation and log conventions when running via the agents CLI.
