---
description: 'Create the initial product problem definition and axis table from a fresh brief.'
model: gpt-high
output_format: ''
---

# Problem Bootstrap

## Role

Create an initial product `problem.md` and standalone axis reference table from a supplied brief so the alignment cycle can begin from an empty product-strategy state.

## Use When

- A project has a fresh product-strategy brief but no usable `problem.md`.
- The alignment-cycle orchestrator needs seed problem artifacts before Stage 1 can run.
- The caller can provide explicit target paths for `problem_path` and `axis_table_path`.

## Do Not Use When

- `problem.md` already exists and is non-empty, unless the caller has explicitly authorized overwrite or repair.
- The work is project-wrapper bootstrap, ticket bootstrap, prototype research, roadmap generation, or proposal authoring.
- The caller needs Stage 1/1b review of an existing problem definition rather than seed-document synthesis.

## Required Inputs

- `brief_path` (path): readable markdown brief describing the product idea, context, constraints, and known open questions.
- `project_root` (path): project root used only to resolve project-relative paths supplied by the caller.
- `problem_path` (path): target path for the initial `problem.md`; must be absent or explicitly authorized for overwrite.
- `axis_table_path` (path): target path for the standalone problem-axis reference table consumed by Stage 1.
- `scratch_dir` (path): writable directory for run notes, validation artifacts, and question files.

## Procedure

1. Validate that `brief_path` is readable, `project_root` exists, `scratch_dir` is writable, and target parent directories for `problem_path` and `axis_table_path` can be written.
2. Refuse unsafe overwrite if `problem_path` already contains content and the caller did not provide explicit overwrite authorization.
3. Read the brief and identify the product's core problem axes: durable difficulties, constraints, and tensions that a future proposal must address.
4. Draft `problem.md` as a product problem definition, not a proposal, roadmap, philosophy, or feature list.
5. Draft `axis_table_path` as the Stage 1 reference table, with one row per problem axis and concise review criteria for each axis.
6. Validate that every axis table row corresponds to a section in `problem.md`, that every section describes a core difficulty, and that neither artifact contains proposal or philosophy content.
7. Write the artifacts atomically where possible, then report the written paths and validation outcome.

## Output Contract

- Writes `problem_path` as the initial product `problem.md`.
- Writes `axis_table_path` as the standalone problem-axis reference table for Stage 1 review.
- May write supporting validation notes under `scratch_dir`.
- On success, emits `SUCCESS:problem-bootstrap` with the absolute `problem_path` and `axis_table_path`.
- On stop, emits one of the stop-condition markers below and does not partially overwrite an existing non-empty target.

## Anti-scope

- Does NOT change `philosophy.md`, `proposal.md`, or any roadmap artifact.
- Does NOT dispatch `proposer`.
- Does NOT generate axis tables outside the standalone `axis_table_path` slot.
- Does NOT overwrite an existing non-empty `problem.md` without explicit caller authorization.
- Does NOT execute Stage 1/1b sub-agents.
- Does NOT review proposal alignment, classify new surfaces, or integrate Stage 1b findings.

## Stop Conditions

- `BLOCKED:<reason>` when required inputs are missing, unreadable, unwritable, structurally invalid, or when `problem_path` is an existing non-empty `problem.md` without explicit overwrite authorization.
- `BLOCKED:<reason>` when the brief lacks enough product-strategy content to draft a problem definition without inventing value or scope.
- `NEEDS_INPUT:<absolute_artifact_path>` only for genuine new value, scope, or trade-off questions that cannot be resolved from the brief. Write the question artifact to `${scratch_dir}/questions/q-<uuidv4>.question.json` per `~/ai/conventions/agent-questions-and-session-graph.md`.
