# Optimized Dispatch Contracts

This directory contains sidecar contracts for dispatch-time routing.

- `operators/*.yaml` mirrors an operator `## Contract` block when one exists. Files marked `contract_status: minimum-generated-from-operator-sections` are lightweight dispatch surfaces generated from the operator's existing frontmatter and input/output sections; the operator body remains the procedural authority.
- `workflows/*.yaml` mirrors workflow `workflow_dispatch_contract` frontmatter.

Workflow frontmatter remains authoritative for generated `workflows/index.json`
data. Sidecars are read-first mirrors, while the generated index is a
deterministic projection rather than an independent contract authority.

Contracts and WRITE eval specifications describe required inputs, behavior, and
acceptance intent. They are not execution records. Behavioral-proof claims must
follow `conventions/behavioral-proof.md` and cite the expected-versus-observed
record from an executed experiment.

Dispatchers should read these files before opening full operator or workflow bodies. If a sidecar is missing or marked too thin for the decision at hand, fall back to the source file named by `source`.
