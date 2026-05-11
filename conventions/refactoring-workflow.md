# Refactoring workflow

Canonical convention for internal structure reshaping with no intended external behavior change. Refactoring is a strategy layer above manager flavors; max, pragmatic, and hackerman still decide risk posture inside the selected strategy.

## Use When

Use this strategy when the work is primarily internal structure reshape, the intended external behavior is unchanged, and the work needs refactoring-specific safety topology: integration-buffer staging, contract-bounded slicing, encapsulate-first handling for unsafe surfaces, or shim lifecycle tracking.

Use it for refactors that benefit from many small PRs against a shared buffer, for slices identified from auditor outputs, and for cleanup where the hard problem is preserving contracts while changing the implementation behind them.

## Do Not Use When

Do not use refactoring for work that ships behavioral change, adds a user-facing surface, or decomposes as a feature lifecycle. Route that work through `~/ai/conventions/feature-development-workflow.md`, `~/ai/workflows/feature-development.md`, and `~/ai/agents/feature-orchestrator.md`.

Do not use refactoring for an ordinary single-WU implementation or bugfix that does not need integration-buffer staging, contract-boundary analysis, encapsulation, or shim lifecycle tracking. Route that work through the implementation pipeline.

Do not use refactoring as a substitute for RCA, PR review, release, roadmap, or prototype workflows.

## Output shape

Refactoring output is a series of small targeted PRs. Each PR is single-commit, bounded to a named slice, and targeted at an integration-branch buffer based off the repository default branch (for `~/ai`, `master`). The buffer accumulates many small refactors before a periodic feature-style PR moves the buffer to trunk.

PRs pull from the current buffer frontier so parallel refactor PRs can proceed on disjoint, non-overlapping slices. When slices overlap, serialize them through the buffer rather than relying on ad hoc rebases.

This convention names the buffer shape only. Cadence, naming, and merge timing are per-effort decisions.

## Contract-bounded slicing

Refactoring is safe only when the slice is bounded by understood contracts. Inside an understood contract boundary, internal components may be replaced, moved, split, or simplified as long as the boundary contract is preserved.

Multi-slice replacement can eventually unravel larger boundaries, but each PR still needs a contract-bounded slice. If the contract boundary is not understood, the slice cannot be refactored safely.

## Encapsulate first

When a slice is unsafe because callers, readers, artifacts, or external systems reach through implementation details, encapsulate first. Move the unsafe surface behind an explicit interface, route known access through it, and only then refactor the implementation behind that interface.

Encapsulation is not a license to preserve old behavior silently. It is a deliberate safety step that creates an explicit contract before internal structure changes.

## Dynamic languages and emitted-artifact contracts

For Python and similar dynamic languages, use signature grep, call-site enumeration, import lookup, and representative runtime evidence to find contract edges that static types do not expose.

For emitted artifacts, grep where the artifact lands, identify every reader, and treat the artifact shape and location as part of the contract. Generated files, local caches, exported reports, queue payloads, and other emitted records can be the real integration point.

For cloud artifacts such as AWS S3 locations, identify what reads from the location. Check IAM policy, lambda triggers, lifecycle hooks, event subscriptions, scheduled jobs, and operational runbooks. Not every consumer is visible in code.

For external readers, understand their constraints before changing the internal implementation. If they depend on filenames, schemas, timing, permissions, or partial side effects, those constraints are contract facts.

## When there is no contract

If uncontrolled external reach-through exists, the permission surface is the contract. A database, bucket, queue, directory, or service account that broad consumers can read directly is an exposed contract even when no one wrote one down.

Entire-database surfaces are effectively frozen until access is narrowed or encapsulated. Surface this condition explicitly instead of treating it as ordinary internal code.

## Encapsulation strategy when external access is uncontrolled

Use the existing uncontrolled surface as a view. Create a new backing store internally, give external consumers their bespoke version of the old surface, and use ETL to keep that version in sync while consumers are untangled.

Once external consumers depend on their explicit view instead of the internal implementation, the internal implementation can change freely behind the new boundary.

This pattern adds operational complexity: synchronization, monitoring, ownership, and removal planning. Use it only when uncontrolled access prevents a safe direct refactor.

## Auditor reuse

The refactoring strategy reuses the implementation pipeline's auditors and code-quality gates ACROSS FILES to identify refactoring targets. `~/ai/conventions/code-quality.md` is the canonical auditor-list and code-quality reference.

Examples:

- Cohesion and coupling auditor findings can become slice candidates.
- Function classification auditor findings can become multi-classifier split candidates.
- Push/pull auditor findings can become uncontrolled-source coupling encapsulation candidates.
- Cross-file pattern analysis can provide contract-surface and contract-violation evidence.

This workflow does not implement cross-file analysis logic itself. That logic is downstream operational work once auditors exist as composable analysis tools.

## Gate discipline inheritance

Refactoring slices inherit the ACR-156 LOW-only / decompose-on-oscillation discipline from `~/ai/conventions/code-quality.md`. Do not advance a slice with unresolved MEDIUM or HIGH risk outcomes. If review or auditor findings oscillate without converging to LOW, decompose or shrink the slice rather than accepting residuals.

## Shim labeling

Encapsulation shims, especially view plus ETL surfaces for uncontrolled external access, are explicit technical debt. Label each shim in code with a stable tag such as `shim:<slice-id>` and track it in `~/ai/conventions/active-shims.md`.

Each registry entry needs a target removal milestone. A shim retires only after every consumer is untangled and derisked, and after the new contract surface is canonical.

## Boundary with `no-backwards-compatibility.md`

Authorized refactoring shims are the narrow carve-out from `~/ai/conventions/no-backwards-compatibility.md`: they are labeled, registry-tracked in `~/ai/conventions/active-shims.md`, milestone-bound, and placed deliberately to encapsulate unsafe surfaces during refactoring.

Silent backwards-compatibility shims remain forbidden under `~/ai/conventions/no-backwards-compatibility.md`. This convention does not legalize deprecated aliases, re-exports, dual implementations, transitional adapters, fallback paths, or partial migrations outside the authorized refactoring-shim registry.

## Cross-references

- `~/ai/conventions/no-backwards-compatibility.md`
- `~/ai/conventions/risk-profile.md`
- `~/ai/conventions/code-quality.md`
- `~/ai/conventions/feature-development-workflow.md`
- `~/ai/workflows/refactoring.md`
- `~/ai/agents/refactoring-orchestrator.md`
- `~/ai/conventions/active-shims.md`
- ACR-176: sibling feature-development strategy.
- ACR-157: manager flavor system.
- ACR-156 chain: LOW-only / decompose-on-oscillation discipline.
- ACR-175: future eval-driven detection.
- AGE-58: ETL-style encapsulation example.
