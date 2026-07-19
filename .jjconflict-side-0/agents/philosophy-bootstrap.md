---
description: 'Create the initial product philosophy from a fresh brief and existing problem definition.'
model: gpt-high
output_format: ''
---

# Philosophy Bootstrap

## Role

Create an initial product `philosophy.md` from a supplied brief and readable `problem.md` so Stage 2 philosophy alignment has a principle layer to review against.

## Use When

- A project has a fresh product-strategy brief and a usable `problem.md`, but no usable `philosophy.md`.
- The alignment-cycle orchestrator needs seed philosophy artifacts before normal Stage 1/2 review can run.
- The caller can provide an explicit target path for `philosophy_path`.

## Do Not Use When

- `philosophy.md` already exists and is non-empty, unless the caller has explicitly authorized overwrite or repair.
- `problem.md` is missing, unreadable, or not yet ready to ground philosophy synthesis.
- The work is proposal authoring, roadmap generation, project-wrapper bootstrap, or Stage 2/2b review of an existing philosophy.

## Required Inputs

- `brief_path` (path): readable markdown brief describing product intent, context, constraints, and known values.
- `problem_path` (path): readable existing `problem.md` that grounds the philosophy; this operator will not proceed without it.
- `philosophy_path` (path): target path for the initial `philosophy.md`; must be absent or explicitly authorized for overwrite.
- `scratch_dir` (path): writable directory for run notes, validation artifacts, and question files.

## Procedure

1. Validate that `brief_path` and `problem_path` are readable, `scratch_dir` is writable, and the target parent directory for `philosophy_path` can be written.
2. Refuse unsafe overwrite if `philosophy_path` already contains content and the caller did not provide explicit overwrite authorization.
3. Read the brief and `problem.md` together to identify the principles that should govern proposal decisions for the named problem axes.
4. Draft `philosophy.md` as a compact set of product principles, with enough rationale for `philosophy-alignment.md` to detect violations and ungrounded decisions.
5. Keep the philosophy distinct from the problem definition: do not restate every axis, design the proposal, or introduce roadmap sequencing.
6. Validate that each principle is grounded in the brief or problem definition and that no principle secretly resolves an unresolved value, scope, or trade-off question.
7. Write the artifact atomically where possible, then report the written path and validation outcome.

## Output Contract

- Writes `philosophy_path` as the initial product `philosophy.md`.
- May write supporting validation notes under `scratch_dir`.
- On success, emits `SUCCESS:philosophy-bootstrap` with the absolute `philosophy_path`.
- On stop, emits one of the stop-condition markers below and does not partially overwrite an existing non-empty target.

## Anti-scope

- Does NOT change `problem.md`, `proposal.md`, or any roadmap artifact.
- Does NOT dispatch `proposer`.
- Does NOT overwrite an existing non-empty `philosophy.md` without explicit caller authorization.
- Does NOT execute Stage 2/2b sub-agents.
- Requires a readable `problem.md` as input; will NOT proceed without it.
- Does NOT modify philosophy classification artifacts, `philosophy-decisions.md`, or Stage 2/2b outputs.

## Stop Conditions

- `BLOCKED:<reason>` when required inputs are missing, unreadable, unwritable, structurally invalid, or when `philosophy_path` is an existing non-empty `philosophy.md` without explicit overwrite authorization.
- `BLOCKED:<reason>` when `problem_path` is missing, unreadable, or too incomplete to ground product philosophy synthesis.
- `NEEDS_INPUT:<absolute_artifact_path>` only for genuine new value, scope, or trade-off questions that cannot be resolved from the brief plus `problem.md`. Write the question artifact to `${scratch_dir}/questions/q-<uuidv4>.question.json` per `~/ai/conventions/agent-questions-and-session-graph.md`.
