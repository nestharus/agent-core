---
workflow:
  id: feature-development
workflow_aliases:
  - alias: feature
    target:
      workflow_id: feature-development
      path: workflows/feature-development.md
  - alias: multi-ticket-feature
    target:
      workflow_id: feature-development
      path: workflows/feature-development.md
workflow_dispatch_contract:
  orchestrator: "feature-orchestrator"
  inputs:
    - "feature brief or approved roadmap, scoped ticket list, repo root, trunk branch, feature branch name, worktrees root, planning root, scratch root, ticket-backend inputs, and selected manager flavor"
    - "optional prototype dossier path, QA target descriptor, and evidence-pack context"
  expectations:
    - "coordinates a feature lifecycle above individual WUs while dispatching implementation-pipeline-orchestrator once per scoped ticket"
    - "keeps ticket PRs targeted to the feature branch and assembles evidence packs for ticket PRs and the final feature PR"
  outputs:
    - "feature branch pushed to origin"
    - "per-ticket implementation-pipeline runs and ticket PR list"
    - "final feature-to-trunk PR with evidence pack, QA verdict or placeholder, prototype payload when applicable, and outcome record"
  non_goals:
    - "does not replace roadmap, prototype, implementation-pipeline, PR-review, or CodeRabbit workflows"
    - "does not inline ticket decomposition or implementation-pipeline phases"
---
# Feature-development workflow

## Role

Coordinate one feature lifecycle above individual WUs.

## Use When

- Use when the work decomposes into 2+ tickets.
- Use when the work has a user-facing surface.
- Use when the work ships behavioral change that needs integrated review before trunk.
- Use when roadmap, prototype, scope, ticket decomposition, ticket PRs, final feature PR, and evidence pack need one coordinated lifecycle.

## Do Not Use When

- Do not use for bounded single-ticket markdown, convention, or auditor refinement work with no user-facing prototype.
- Do not use for standalone roadmap generation; use `workflows/roadmap.md`.
- Do not use for standalone prototype work; use `workflows/build-prototype.md`.
- Do not use for one already-scoped WU; use `workflows/implementation-pipeline.md`.
- Do not use for PR review on an existing diff; use `workflows/pr-review.md` and the PR-review operators.

## Required inputs

- Feature brief or approved roadmap.
- Scoped ticket list.
- Repo root.
- Trunk branch.
- Feature branch name.
- Worktrees root.
- Planning root.
- Scratch root.
- Ticket-backend inputs.
- Selected manager flavor.

## Optional inputs

- Prototype dossier path.
- QA target descriptor.
- Evidence-pack context.

## Outputs

- Feature branch pushed to origin.
- Per-ticket implementation-pipeline runs.
- Ticket PR list with each PR targeting the feature branch, each carrying an appropriately-scoped PR-body evidence pack per the universal evidence-pack rule in `~/ai/conventions/feature-development-workflow.md`.
- Final feature-to-trunk PR with evidence pack.
- Prototype payload under `prototype/<feature-slug>/` when applicable, containing `docker-compose.yml` plus `README.md` per `~/ai/conventions/feature-development-workflow.md` (prerequisites, environment, bring-up commands, smoke test, expected output).
- QA verdict, or a recorded placeholder when the QA agent is not operational.
- Outcome record.

## Dispatch shape

The operator is `agents/feature-orchestrator.md`. It dispatches `implementation-pipeline-orchestrator` once per scoped ticket, with the ticket PR target set to the feature branch. The implementation pipeline remains the single-WU engine; this workflow only declares the feature-level contract around those WUs. It does not re-implement implementation-pipeline phases, inline ticket-decomposition logic, or replace the roadmap, prototype, PR-review, or CodeRabbit workflows.

## Procedure

Follow `agents/feature-orchestrator.md`. This workflow doc declares the dispatch contract, inputs, outputs, and stop conditions; the orchestrator doc declares the procedure. Do not re-implement implementation-pipeline phases here.

## Stop conditions

- Stop when the prototype answers "do not pursue".
- Stop when scope explodes beyond the current feature and must split.
- Stop when required PR-body evidence cannot be assembled for the ticket PRs or final PR.
- Stop when the QA verdict fails, or when the QA placeholder exposes a value or release decision the active manager flavor cannot answer.

## Cross-references

- `~/ai/conventions/feature-development-workflow.md`
- `~/ai/agents/feature-orchestrator.md`
- `~/ai/workflows/implementation-pipeline.md`
- `~/ai/workflows/roadmap.md`
- `~/ai/workflows/build-prototype.md`
- `~/ai/workflows/pr-review.md`
- `~/ai/workflows/coderabbit-loop.md`
