# Active shims

This is the registry doc for currently-active refactoring shims. `~/ai/conventions/refactoring-workflow.md` section "Shim labeling" is the source convention; `~/ai/conventions/no-backwards-compatibility.md` defines the carve-out boundary this registry must not expand.

## Schema

- `shim_id` - unique identifier for the shim. Recommended format: `shim:<slice-id>`.
- `surface_description` - what the shim encapsulates, such as a function, file, artifact-landing location, cloud-permission surface, or external reader surface.
- `external_consumers` - list of known external consumers reaching through the shim.
- `dependency_chain_to_remove` - what must be untangled before the shim can retire.
- `target_removal_milestone` - milestone, ticket, or quarter when retirement is expected.

## Active shims

| shim_id | surface_description | external_consumers | dependency_chain_to_remove | target_removal_milestone |
|---|---|---|---|---|
| _(none yet)_ |  |  |  |  |

## Lifecycle rules

Entries are added when a shim is placed. Entries are updated when consumers move off the shim or when the dependency chain changes. Entries are deleted only when the shim is retired and the new contract surface is canonical.

## Boundary with no-backwards-compatibility.md

Only labeled, registry-tracked, milestone-bound refactoring shims are authorized by this registry. Silent compatibility code remains forbidden under `~/ai/conventions/no-backwards-compatibility.md`.

This registry does not authorize convenience aliases, fallback paths, old-shape feature flags, re-exports, transitional adapters, dual implementations, or partial migrations outside a deliberate refactoring-shim entry.
