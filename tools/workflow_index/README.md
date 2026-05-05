# `workflow_index` — workflow metadata index generator

**Status: implemented.**

## One concern

Generate `workflows/index.json` from YAML frontmatter in `workflows/*.md`. Workflow Markdown frontmatter remains the source of truth; the JSON file is derived lookup data for humans, agents, and future tools that need stable workflow ids and dispatch-contract metadata without parsing every workflow body.

## Anti-scope

- The tool does NOT resolve aliases at runtime.
- The tool does NOT infer aliases from workflow prose.
- The tool does NOT edit workflow Markdown files.
- The tool does NOT replace `AGENTS.md`, workflow-routing rules, operator frontmatter, or workflow body procedures.
- The tool does NOT install a CI job, pre-commit hook, or dispatch interceptor.

## Inputs

- Python 3.
- PyYAML available to Python as `yaml`; this repository has no dependency file, so PyYAML is a developer dependency for running this tool.
- `workflows/*.md` files with YAML frontmatter containing `workflow.id` and `workflow_dispatch_contract`.
- Optional CLI paths:
  - `--repo-root <path>` defaults to the nearest current-directory ancestor containing `workflows/`.
  - `--workflows-dir <path>` defaults to `workflows`.
  - `--output <path>` defaults to `workflows/index.json`.

## Outputs

- `python3 -m tools.workflow_index generate` writes deterministic JSON to the output path.
- `python3 -m tools.workflow_index check` writes nothing; it exits zero when regenerated JSON matches the checked-in output and non-zero with a unified diff when stale.
- Parser and schema errors name the offending workflow file.

## Used by

- NES-143 workflow alias data-file work unit.
- Future workflow alias/index consumers that need the generated `workflows/index.json` lookup surface.

## TODO

- Add alias declarations only when there is concrete user-used alias evidence.
- Wire CI or pre-commit freshness checks in a later scoped workflow if the repository adopts enforcement.
