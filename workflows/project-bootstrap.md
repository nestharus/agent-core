---
workflow:
  id: project-bootstrap
workflow_dispatch_contract:
  orchestrator: "Work Manager or root coordinator"
  inputs:
    - "target project path, layout variant, bootstrap category, base operator or workflow, project facts, planning path, scratch path, and first-bootstrap or re-bootstrap trigger"
    - "evidence that a project-specific wrapper may be needed, missing, stale, or not worth emitting"
  expectations:
    - "runs the open path against shared operators before trusting a project-specific wrapper"
    - "emits or refreshes thin project-local wrappers only when stable project facts justify them"
    - "uses qualitative stale-wrapper signals to choose closed path or re-bootstrap"
  outputs:
    - "project-bootstrap run report with layout, category, decision, emitted paths, skipped paths, and residual questions"
    - "optional project-local wrapper and optional project AGENTS routing/policy update"
    - "NO_WRAPPER_NEEDED, NEEDS_INPUT, or BLOCKED outcome when emission is not correct"
  non_goals:
    - "does not redefine bootstrap-pattern lifecycle vocabulary"
    - "does not implement category-specific linter, ticket, code-quality, alias, or routing bootstraps"
    - "does not migrate existing project-local wrappers"
---
# Project Bootstrap Workflow

Operational workflow for converting stable project facts into a thin project-local operator wrapper, using `~/ai/conventions/bootstrap-pattern.md` as the lifecycle rule reference. This workflow is dispatched by Work Manager or the root coordinator when a project/category pair needs open-path analysis, wrapper emission, closed-path validation, or a re-bootstrap decision.

## Workflow Dispatch Surface

### Orchestrator

Work Manager or root coordinator

### Inputs

- target project path, layout variant, bootstrap category, base operator or workflow, project facts, planning path, scratch path, and first-bootstrap or re-bootstrap trigger
- evidence that a project-specific wrapper may be needed, missing, stale, or not worth emitting

### Expectations

- runs the open path against shared operators before trusting a project-specific wrapper
- emits or refreshes thin project-local wrappers only when stable project facts justify them
- uses qualitative stale-wrapper signals to choose closed path or re-bootstrap

### Outputs

- project-bootstrap run report with layout, category, decision, emitted paths, skipped paths, and residual questions
- optional project-local wrapper and optional project AGENTS routing/policy update
- NO_WRAPPER_NEEDED, NEEDS_INPUT, or BLOCKED outcome when emission is not correct

### Non-goals

- does not redefine bootstrap-pattern lifecycle vocabulary
- does not implement category-specific linter, ticket, code-quality, alias, or routing bootstraps
- does not migrate existing project-local wrappers

## Use When

- First project/category WU needs stable project facts captured for a shared base operator or workflow.
- A project-specific wrapper is missing, stale, incompatible with the current base procedure, or not yet proven worth keeping.
- A closed-path dispatch reports a re-bootstrap trigger such as changed project policy, changed base operator inputs, or a new category default.
- A root coordinator needs a run-report decision before later WUs can choose between the shared operator and a project wrapper.

## Do Not Use When

- The task is ordinary WU implementation; use `~/ai/workflows/implementation-pipeline.md`.
- The task is category-specific bootstrap implementation for linting, ticketing, code quality, aliases, or routing; use or file that category slice.
- The task is only AGENTS maintenance; use `agentsmd-curator` or `agentsmd-maintenance-orchestrator`.
- The task asks to migrate existing project-local wrappers across projects; this workflow only defines the bootstrap procedure and emission contract.

## Required Inputs

- Target project path.
- Layout variant, or evidence needed to determine whether the project uses the single-repo or multi-repo umbrella layout.
- Bootstrap category.
- Shared base operator or workflow being wrapped.
- Project facts known so far, including project policy knobs when they exist.
- Planning path and scratch path for the project-bootstrap run report and logs.
- Trigger type: first bootstrap or re-bootstrap.

## Optional Inputs

- Existing wrapper path.
- Known stale signal evidence from closed-path dispatch, `agentsmd-curator`, `agentsmd-maintenance-orchestrator`, or human review.
- Candidate project `AGENTS.md` routing entry.
- Category-specific defaults proposed for the wrapper.
- Prior project-bootstrap run report.

## Procedure

### Open Path

1. Read the project `AGENTS.md`, `~/ai/conventions/bootstrap-pattern.md`, `~/ai/conventions/project-layout.md`, the shared base operator or workflow, and any prior project-bootstrap run report.
2. Determine the project layout and category facts. If the target project path cannot be mapped to a supported layout, decide `BLOCKED` and write the missing evidence into the run report.
3. Dispatch existing general operators by name when they own the category evidence: `agentsmd-curator` for AGENTS/routing consistency, `linear-operator` or `jira-operator` for ticket-system facts, and the relevant project lint or code-quality operator when that category already exists.
4. Decide one of `OPEN_PATH_READY_FOR_EMISSION`, `NO_WRAPPER_NEEDED`, `NEEDS_INPUT`, or `BLOCKED`. Use `NO_WRAPPER_NEEDED` when stable facts are too small or too ad hoc to justify a wrapper; use `NEEDS_INPUT` when a new user-owned policy/default trade-off blocks emission.

### Emission

1. Read `~/ai/conventions/project-layout.md` and resolve the destination before writing. Use `<project>/trunk/agents/` for the single-repo umbrella layout and `<project>/agents/` for the multi-repo umbrella layout where project routing and wrappers live at the umbrella root.
2. Emit or refresh only a thin wrapper file. The wrapper shape is frontmatter, H1, `Base procedure: ~/ai/agents/<name>.md`, and local defaults, examples, and project-specific overrides only.
3. Do not re-inline the shared base procedure. The wrapper references the base procedure and carries only the stable project facts needed to avoid rediscovery.
4. Keep project-wide policy knobs in project `AGENTS.md`. Wrappers may reference those knobs and add category-specific defaults, but the precedence rule is that the project AGENTS.md owns global policy facts and the wrapper owns category-local execution defaults. Do not duplicate or override global policy facts inside the wrapper.
5. Validate the wrapper against `~/ai/agents/operator-file-format.md`: frontmatter exists, H1 exists, `Base procedure:` points at the shared base, destination matches the resolved layout, and the body contains local defaults rather than a copied base procedure.
6. When project `AGENTS.md` routing changes are part of the output, dispatch `agentsmd-curator` or cite its required edit/audit path before finalizing the optional AGENTS pointer.
7. Write a project-bootstrap run-report rationale naming emitted paths, skipped paths, and the decision. Report skipped emission as `NO_WRAPPER_NEEDED`, `NEEDS_INPUT`, or `BLOCKED`; report successful creation as `WRAPPER_EMITTED` and successful refresh as `WRAPPER_REFRESHED`.

### Closed Path Dispatch Contract

1. Read project `AGENTS.md`, the current wrapper, the wrapper's `Base procedure:` pointer, and the current shared base operator or workflow.
2. Dispatch the project wrapper first when it is present and current. Dispatch the shared general operator only after `NO_WRAPPER_NEEDED` or after the run report documents a fallback from the wrapper.
3. Route ordinary WU implementation through `~/ai/workflows/implementation-pipeline.md`; this workflow does not replace the implementation pipeline.
4. Decide `REBOOTSTRAP_OPENED` and route to the Re-Bootstrap Trigger when the wrapper is missing, stale, incompatible, or fails to propagate a material base input/subcommand. Otherwise keep the closed path active and record the wrapper used.

### Re-Bootstrap Trigger

1. Read the current wrapper, current base operator, project `AGENTS.md`, and stale signal report from closed-path dispatch, `agentsmd-curator`, `agentsmd-maintenance-orchestrator`, or human review.
2. Compare the wrapper's `Base procedure:` pointer, propagated inputs/subcommands, local defaults, and captured project facts against the current base operator and project policy.
3. Decide `REBOOTSTRAP_OPENED` when the signal is material, then reopen `### Open Path` with the stale signal as input. Decide `REBOOTSTRAP_NOT_NEEDED` when the signal is advisory-only and record the reason in the run report.
4. Report `NEEDS_INPUT` for a new user-owned policy/default trade-off. Report `BLOCKED` when the wrapper, base operator, project `AGENTS.md`, or layout evidence cannot be read.
5. If emission is skipped during re-bootstrap, include the skipped path and run-report rationale so later closed-path dispatch can distinguish `REBOOTSTRAP_NOT_NEEDED`, `NO_WRAPPER_NEEDED`, `NEEDS_INPUT`, and `BLOCKED`.

## Stop Conditions

- `WRAPPER_EMITTED` - a new project-local wrapper was written and validated.
- `WRAPPER_REFRESHED` - an existing wrapper was updated and validated.
- `NO_WRAPPER_NEEDED` - the open path found no stable project facts worth emitting; the run report explains why.
- `REBOOTSTRAP_NOT_NEEDED` - a re-bootstrap signal was advisory-only; the current closed path remains valid.
- `NEEDS_INPUT` - the workflow found a user-owned value, scope, or policy/default trade-off.
- `BLOCKED` - required project, layout, wrapper, base-operator, or AGENTS evidence could not be read or reconciled.

## References

- `~/ai/conventions/bootstrap-pattern.md`
- `~/ai/conventions/project-layout.md`
- `~/ai/agents/operator-file-format.md`
- `~/ai/agents/agentsmd-curator.md`
- `~/ai/workflows/implementation-pipeline.md`
