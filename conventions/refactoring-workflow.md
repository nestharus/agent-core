# Refactoring workflow

Canonical convention for internal structure reshaping with no intended external behavior change. Refactoring is a strategy layer above manager flavors; max, pragmatic, and hackerman still decide risk posture inside the selected strategy.

## Use When

Use this strategy when the work is primarily internal structure reshape, the intended external behavior is unchanged, and the work needs refactoring-specific safety topology: integration-buffer staging, contract-bounded slicing, encapsulate-first handling for unsafe surfaces, or shim lifecycle tracking.

Use it for refactors that benefit from separate one-PR WUs against a shared buffer, for slices identified from auditor outputs, and for cleanup where the hard problem is preserving contracts while changing the implementation behind them. Each orchestrator invocation owns exactly one child and one ticket PR; larger efforts decompose before dispatch.

The receiver-side boundary cites `conventions/feature-development-workflow.md` `## Refactoring out of scope`; feature-spawned refactor tickets are valid intake only under no-behavior-shipping.

## Do Not Use When

Do not use refactoring for work that ships behavioral change, adds a user-facing surface, or decomposes as a feature lifecycle. Route that work through `~/ai/conventions/feature-development-workflow.md`, `~/ai/workflows/feature-development.md`, and `~/ai/agents/feature-orchestrator.md`.

Do not use refactoring for an ordinary single-WU implementation or bugfix that does not need integration-buffer staging, contract-boundary analysis, encapsulation, or shim lifecycle tracking. Route that work through the implementation pipeline.

Do not use refactoring as a substitute for RCA, PR review, release, roadmap, or prototype workflows.

## Output shape

Refactoring output across multiple WUs can be a series of small targeted PRs. Each WU owns exactly one single-commit PR bounded to a named slice and targeted at the caller-provided `integration_branch_ref`; the caller-provided `trunk_branch` is the eventual buffer PR base. Never infer either identity from the repository default branch. The buffer can accumulate separately dispatched refactoring WUs before a periodic feature-style PR moves the buffer to trunk.

Separately dispatched WU PRs pull from the current buffer frontier so disjoint, non-overlapping slices can proceed independently. When slices overlap, serialize the WUs through the buffer rather than relying on ad hoc rebases.

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

## Runtime invocation identity

Runtime invocation UUIDs come from runner provenance, never caller input. A refactoring invocation derives its own identity from `OULIPOLY_PARENT_INVOCATION`; each child identity is joined only after the runner emits one valid `OULIPOLY_INVOCATION` marker into that child's complete log. Pre-dispatch manifests name stable roles, prompts, logs, and outputs rather than UUIDs that do not yet exist.

## Ready-state recovery

The refactoring owner promotes only the exact reviewed OPEN draft PR. Every failure after ready and before merge invokes exact-repository `gh pr ready --undo`, freshly fetches both base and head branches, and freshly re-queries that PR. `validate-ready-state-restoration` must prove OPEN `is_draft=true`, unchanged URL/number/state/base/head identity across undo, and provider OIDs equal to the fresh fetches before the owner may return to the implementation child's Phase 8. Undo, re-query, identity, or draft-state failure is `BLOCKED:ready-state-restoration-failed` and is not replayable.

Invocation of the guarded merge command is the irreversible attempt boundary. No ready undo occurs after that point; merge-command and post-attempt verification failures return `BLOCKED:merge-attempt-started` with `replay_permitted=false`.

## Canonical branch and path identity

The explicit repository trunk, integration branch, child branch, and every protected-list entry are independently validated exact short branches before protected membership checks. The canonical protected list contains trunk first, integration second when distinct, and any extra names in lexical order. Reject missing trunk/integration members, full refs, remote-tracking forms, invalid aliases, duplicates, and semantically disguised protected names; never normalize an invalid protected entry into authority. The child branch must differ from every protected branch.

Worktree, planning, and scratch roots are pairwise distinct canonical absolute identities. Reject `.` / `..` components, symlinks, lexical-versus-`resolve(strict=False)` differences, and cross-root canonical aliases before dispatch. A child projection repeats those exact strings unchanged.

## Acyclic process-review projections

The pre-merge projection is immutable and contains only the sole implementation child, baseline-auditor, and pre-merge-auditor nodes that can exist before merge. Its report uses the canonical header-first `# Process Tree Audit` envelope, exactly one `Verdict: PASS`, and one producer-owned `process-tree-audit-binding-v1` that binds report identity without a self hash, root/null subtree, expected manifest, trace, and sorted companion artifact rows by SHA-256. Post-merge auditor nodes are added only to a full post-merge projection that preserves the complete singular-child pre-merge lineage and records the pre-merge manifest hash. A process audit never requires its own invocation or a future route result as an input, and consumers never impose a caller-specific binding layout.

## Child evidence binding

Before promotion, the refactoring owner requires the implementation result's immutable `ticket-operation-expected-context-v1` path/hash and validated producer ticket-result path/hash. It reruns `validate-ticket-operation-result --expected-context` against the exact refactoring ticket/backend/site/attempt/PR/reviewed identity; a self-consistent result for another caller is not ticket evidence. The implementation result also carries exact current Phase 4/6/8 expected-process/raw-trace/process-audit path-hashes. Refactoring re-hashes those artifacts but does not re-audit implementation-owned internal nodes.

The `refactoring-route-result-v1` binds both the implementation-owned rows and exact refactoring-owned pre-merge/final proof rows. It also binds child PR URL/number to the nested implementation PR; declared/open/pre-merge/merged head names to the nested reviewed head branch; declared/observed/expected-guard head SHAs to nested `phase_8_reviewed_head_sha`; and open/pre-merge/merged/reviewed base SHAs to nested `phase_8_reviewed_base_sha`. `integration_branch_name`, child dispatched and open/pre-merge/merged observed base names, and nested implementation `base_branch` equal the caller's exact integration/feature branch plus nested `base_ref=refs/remotes/origin/${integration_branch_name}`. Equal OIDs never waive PR, name, ref, base, or guard joins.

The same route result binds one current `refactoring-auditor-index-v1` by path/SHA-256. The closed index names exact route invocation UUID, feature branch, ticket, attempt, baseline, pre-merge head, and post-merge head plus exactly five rows in canonical role order at each of `pre-merge` and `post-merge`. Each row contains only `role`, `stage`, `report_path`, `report_sha256`, `verdict`, `round`, `baseline_sha`, and `current_head_sha`; the route child arrays equal the index arrays exactly. Every report is distinct, re-hashed, and parsed for exactly one canonical `Verdict: LOW`; pre-merge heads equal the nested reviewed child head and post-merge heads equal final/refreshed integration SHA. Feature-level consumers perform this re-hash and semantic validation and verify both owners' process-proof hashes without rerunning auditors or recursively imposing feature topology on either orchestrator's descendants.

## Guarded child-PR merge identity

Every parent-sensitive implementation, behavior-test, coverage, test-audit, PR-review, refactoring-auditor, ticket-evidence, and pre-merge process result binds one exact `reviewed_base_sha` plus reviewed head SHA. The refactoring child must identify the same exact nested implementation PR URL/number and reviewed head branch/SHA before promotion. Immediately before the owner-controlled merge, freshly fetch the explicit integration and child head branches, resolve both full OIDs, re-query that exact PR, and invoke `tools/operational_contracts.py validate-pr-currentness` with required fetched base/head SHAs over frozen reviewed and immediate provider bundles. Require OPEN ready state, unchanged PR number/URL, exact base/head names, exact expected-head guard, and provider/fetched/reviewed equality for both full OIDs; record both fetched SHAs in currentness evidence. The merged observation's base SHA must still equal both `reviewed_base_sha` and `pre_merge_base_sha`; another PR, same-OID branch alias, or unrelated merged base OID fails.

If the integration branch advanced externally or through a sibling merge, write a `STALE_CURRENTNESS` result and perform no merge. Return the candidate through refresh/rebase and rerun every parent-sensitive implementation, test, review, refactoring-auditor, ticket-evidence, and process gate before establishing a new reviewed base/head. An unchanged head does not preserve evidence across parent movement. Only exact equality permits the provider's expected-head guard. Afterward require the same PR in MERGED state with unchanged identities and matching non-null merge OID, then prove refreshed integration ancestry and immediate parent equal to `reviewed_base_sha` before post-merge acceptance.

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
