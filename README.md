# `~/ai/` — Shared AI Workflow Library

Cross-project home for workflow definitions, model-role references, agent operator prompt specs, and reusable project-document patterns.

Use this index to find the authoritative file. The linked documents carry the actual rules and procedures.

What lives here:
- **Workflows** — reusable process docs for implementation, research, review, roadmap, approval, and CLI usage.
- **Models** — the shared role matrix for choosing which model does which kind of work.
- **Conventions** — repeated repo and workflow rules used across projects.
- **Agents** — format docs for operator prompt files stored under `~/ai/agents/`.
- **Patterns** — templates for project-specific sections that should keep a consistent shape.

What does not live here:
- Project identity, domain scope, stakeholder context, and repository-specific rules.
- Infrastructure details that only apply to one repository or one live system.
- Project-only overrides that do not generalize across repositories.

External reference:
- `/home/nes/projects/agent-runner/README.md` — authoritative `agents` CLI reference for installation, invocation shapes, flags, model config, named-agent resolution, and app-level behavior.
- [`workflows/agents-cli.md`](workflows/agents-cli.md) — local workflow conventions layered on top of that CLI reference.

Folder map:
- `agents/` — operator prompt format and related agent-facing prompt specs.
- `conventions/` — shared rules that apply across workflows and repositories.
- `models/` — model-selection references shared by multiple workflows.
- `patterns/` — templates for project-local sections that should keep a common shape.
- `workflows/` — reusable end-to-end process documents.

## Index

Descriptions below are intentionally one line each.

### Models

Shared role references.

- [`models/roles.md`](models/roles.md) — Shared model-role matrix for proposal, build, audit, and judgment work.

### Workflows

Reusable process docs.

- [`workflows/agents-cli.md`](workflows/agents-cli.md) — Default invocation shape, prompt/log conventions, and workflow-specific `agents` CLI usage rules.

- [`workflows/adversarial-qa-stage.md`](workflows/adversarial-qa-stage.md) — Stage-only normal-regression plus adversarial QA with complete bug reports.

- [`workflows/code-quality.md`](workflows/code-quality.md) — Composite A1 code-quality auditor fanout, normalized findings, and aggregate verdict.

- [`workflows/coderabbit-loop.md`](workflows/coderabbit-loop.md) — Step-7 review loop for running CodeRabbit passes until findings stop paying off.

- [`workflows/implementation-pipeline.md`](workflows/implementation-pipeline.md) — End-to-end delivery pipeline from trigger through merge, including RCA routing for bugs.

- [`workflows/linter-bootstrap.md`](workflows/linter-bootstrap.md) - Identify A1 linter coverage gaps, research ecosystem lint rules, and propose a setup PR.

- [`workflows/pr-review.md`](workflows/pr-review.md) — Post-CodeRabbit PR gates for tests, concern-splitting, justification, and commit hygiene.

- [`workflows/project-bootstrap.md`](workflows/project-bootstrap.md) — Open-path, wrapper-emission, closed-path, and re-bootstrap workflow for project-specific operator wrappers.

- [`workflows/rca.md`](workflows/rca.md) — Full reproduction-first RCA workflow with split root-cause, fix-decision, application-plan, and apply phases, a verify-or-return gate, and downstream incident lifecycle handoff.

- [`workflows/research.md`](workflows/research.md) — Research process for open-ended investigation, option analysis, and externally sourced scoping.

- [`workflows/roadmap.md`](workflows/roadmap.md) — Strategic roadmap pipeline for turning product direction into scoped shippable work.

- [`workflows/tiered-approval.md`](workflows/tiered-approval.md) — Three-tier safety model for read actions, confined writes, and visible writes.

### Conventions

Cross-project rules.

- [`conventions/code-quality.md`](conventions/code-quality.md) - Cross-project code-shape rules for generated and reviewed code: function classification, max nesting depth, inline mini-function extraction, duplicate responsibility handling, and push-vs-pull system coupling.

- [`conventions/gate-ownership.md`](conventions/gate-ownership.md) — Rule for which workflow phase gates are user-owned versus model-owned.

- [`conventions/git.md`](conventions/git.md) — Branch, worktree, commit, and PR conventions for repository work.

- [`conventions/no-backwards-compatibility.md`](conventions/no-backwards-compatibility.md) — Clean-change rule that forbids compatibility shims and dual-path transitions.

- [`conventions/no-deferred-stubs.md`](conventions/no-deferred-stubs.md) — Rule against placeholder implementations, silent stand-ins, and untracked future work.

- [`conventions/workflow-routing.md`](conventions/workflow-routing.md) — Cue-to-workflow routing rules for project `AGENTS.md` tables.

- [`conventions/worktree-isolation.md`](conventions/worktree-isolation.md) — Requirement to isolate concurrent writers in separate git worktrees.

### Agents

Agent prompt format references.

- [`agents/operator-file-format.md`](agents/operator-file-format.md) — Required frontmatter keys and body structure for operator prompt files.

- Individual operator prompt files should follow that contract and live under `~/ai/agents/` or the project-local equivalent.

### Patterns

Project-local section templates.

- [`patterns/global-constraints-template.md`](patterns/global-constraints-template.md) — Template for a project-level list of non-negotiable constraints.

- [`patterns/infrastructure-reference.md`](patterns/infrastructure-reference.md) — Template for the infrastructure or ops appendix in a project `AGENTS.md`.

- [`patterns/repo-structure-map.md`](patterns/repo-structure-map.md) — Template for the annotated repo-tree section near the top of a project `AGENTS.md`.

## How Projects Use `~/ai/`

A project `AGENTS.md` should stay thin and point here for shared process and policy docs.

Recommended shape:

1. Project identity — name, scope, and domain-specific context.
2. Live-system rules — project-local interpretation of visible-write safety where needed.
3. Repo structure map — use [`patterns/repo-structure-map.md`](patterns/repo-structure-map.md).
4. Global constraints — use [`patterns/global-constraints-template.md`](patterns/global-constraints-template.md) when the project has true non-negotiables.
5. Infrastructure reference — use [`patterns/infrastructure-reference.md`](patterns/infrastructure-reference.md) for named systems, hosts, IDs, and endpoints.
6. Workflow pointers — keep a short routing table that points into [`workflows/`](workflows/) and follows [`conventions/workflow-routing.md`](conventions/workflow-routing.md).
7. Project-specific overrides — record only the exceptions or additions that do not belong in `~/ai/`.

Everything else should either point to an existing doc in `~/ai/` or become a new shared doc here.

## Update Rules

- Treat `~/ai/` as the shared source for cross-project workflow and policy docs.
- Keep descriptions here short; put full guidance in the linked file, not in this index.
- When a change is project-specific, keep it in that project's `AGENTS.md` instead of adding it here.
- When `~/ai/` changes, check project `AGENTS.md` files that point here and update their pointers if needed.
