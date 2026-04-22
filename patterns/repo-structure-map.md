# Pattern: Repo Structure Map

A **repo structure map** is a short annotated directory tree near the top of a project's `AGENTS.md`. It tells a new agent or contributor where things live without them having to inventory the whole repo first.

## When to include one

- Every project `AGENTS.md` should include a structure map.
- Size it to navigation needs, not literal repo completeness.
- Refresh it when directory meaning changes, not on every incidental file move.
- Put it near the top, before workflow detail.

## Shape

A fenced code block showing the tree with brief annotations:

```text
services/
  api/          # FastAPI mutation gateway
  discord/      # discord.py daemon
apps/
  web/          # TanStack Start frontend
packages/
  shared-types/ # generated TypeScript contracts
migrations/     # Alembic
docs/           # planning and decisions
plans/          # research + proposals
```

Rules:

- Show directories and only the top ~2 levels that matter.
- Annotate with a short description, usually 7 words or fewer.
- Group related dirs under their shared parent.
- Omit noise (`node_modules`, `target`, `.venv`, generated artifacts).
- Include planning, research, decisions, and governance dirs.
- If the repo has two distinct topologies, keep them together in one compact section rather than scattering multiple maps.

## What readers use it for

- Orienting before search or edits.
- Finding planning artifacts and decision logs quickly.
- Seeing service boundaries before changing code.
- Understanding whether the repo is code-first, docs-first, or pipeline-first.

## Anti-patterns

- Listing every single file.
- Writing annotations longer than the directory names.
- Letting the map drift after a re-org.
- Splitting the authoritative map across unrelated sections.

## Exemplars

- `/home/nes/work/AGENTS.md` — worktrees + planning + external coordinator layout.
- `/home/nes/projects/agent-implementation-skill/AGENTS.md` — governance-docs-first layout.
- `/home/nes/projects/agent-runner/AGENTS.md` — frontend component tree plus backend Rust module tree.
- `/home/nes/projects/server-manager/AGENTS.md` — service-boundary layout (`api/`, `daemon/`, `web/`).
- `/home/nes/projects/visual-code-editor/AGENTS.md` — narrow asset-pipeline tree.

Each exemplar fits the pattern but uses a different shape. Copy the variant that matches your project's layering, then trim it to the directories a contributor actually needs.
