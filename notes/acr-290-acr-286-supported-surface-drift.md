# ACR-290 / ACR-286 Dependency Note - Supported-surface inventory drift

## Purpose

This note records the ACR-286 dependency for Drift-2 supported-surface inventory resolution while `apply-gate-set` remains active across RCA and implementation-pipeline caller modes. ACR-290 owns this durable pointer and backlink evidence; ACR-286 remains the authority for settling whether supported-surface is standalone, folded into another row, or explicitly non-applicable by caller mode until settlement.

The source-tree canonical reference lives at `/home/nes/ai/worktrees/acr-290-drift-2-supported-surface-note/notes/acr-290-acr-286-supported-surface-drift.md`. The planning-tree mirror lives at `/home/nes/ai/planning/acr-290-drift-2-supported-surface-note/risk/acr-290-acr-286-dependency-note.md` for WU evidence. These files do not change product code, dispatch gates, operator schema, eval-spec scenarios, or supported-surface semantics.

## Drift-2 source

Source: `/home/nes/ai/planning/acr-277-clarify/dossier/evidence/vector-b-structural-blockers.md:39-43`.

```markdown
- [x] **supported-surface-row-drift**
  - **Shape(s) blocked**: 2 and 4 partial; 3 blocked; 1 survives only if it resolves or dual-scores the inventory.
  - **What the shape cannot do**: PR-review names supported-surface verification, while implementation Phase 8 workflow/orchestrator surfaces disagree about whether it is a standalone Phase 8 row. A shared workflow or direct-copy approach can drift silently.
  - **Evidence anchor**: ACR-277 Drift 2 brief; ACR-260/ACR-261 Phase 4 supported-surface reports.
  - **Refinement that would address it**: Shape 1 must define supported-surface treatment per invocation: standalone row, folded row, or explicit non-applicability with source-reading noted.
```

The donor-reading mismatch is that PR-review names supported-surface verification, while implementation Phase 8 workflow and orchestrator surfaces disagree about whether supported-surface is a standalone Phase 8 row. Until ACR-286 settles the supported-surface inventory model, `apply-gate-set` must preserve compatibility instead of silently selecting one donor reading.

## Canonical reference for supported-surface inventory-resolution

Canonical row schema: `/home/nes/ai/agents/apply-gate-set.md:258-277`.

Required fields:

- `inventory_name`: `proof-risk` or `supported-surface`
- `tracker_ref`: `ACR-285` or `ACR-286`
- `source_inventory_refs`
- `caller_mode`
- `available_readings`
- `selected_disposition`: `dual_score`, `folded_equivalent`, `standalone`, `non_applicable`, or `settled_canonical`
- `fold_target_gate`
- `dual_scores`
- `rationale`
- `expires_when`

Line 277 specifically preserves ACR-286 supported-surface drift until ACR-286 settles: represent both PR-review and implementation-pipeline readings, use `non_applicable` only with caller-mode evidence, and record why the omitted reading cannot affect the selected mode.

## Caller-mode preservation requirements

ACR-290 preserves these caller modes and line-range references without redefining them:

- `rca-post-apply`: `/home/nes/ai/agents/rca-orchestrator.md:86-137` dispatches `apply-gate-set(caller_mode=rca-post-apply)`, requires a `PASS` before downstream RCA lifecycle movement, and delegates currentness to `apply-gate-set` rather than redefining gate-set triggers locally.
- `implementation-phase-4`: `/home/nes/ai/agents/implementation-pipeline-orchestrator.md:510-516` requires Phase 4 prompts and returned contracts to carry supported-surface context, `supported-surface-risk`, manifest currentness fields, and supported-surface repair routing before downstream movement.
- `implementation-phase-6`: `/home/nes/ai/agents/implementation-pipeline-orchestrator.md:577-578` requires separate Step 6b and Step 6c invocation evidence and side-channel evidence; `/home/nes/ai/agents/implementation-pipeline-orchestrator.md:608-614` keeps post-Step-6c component evidence behind `apply-gate-set(caller_mode=implementation-phase-6)`.
- `implementation-phase-8`: `/home/nes/ai/agents/implementation-pipeline-orchestrator.md:684-690` requires Phase 8 `apply-gate-set(caller_mode=implementation-phase-8)`, supported-surface inventory-resolution while ACR-286 remains open, join manifest currentness fields, and blocking behavior for malformed or stale gate evidence.

Shared preservation references:

- `/home/nes/ai/workflows/apply-gate-set.md:102-125` requires inventory-resolution rows to dual-score or fold ACR-285 and ACR-286 readings until those trackers settle, names supported-surface evidence in `implementation-phase-4`, and names supported-surface inventory-resolution in `implementation-phase-8` while ACR-286 remains open.
- `/home/nes/ai/workflows/apply-gate-set.md:139-153` points canonical manifest schema ownership to `agents/apply-gate-set.md`, points currentness to `/home/nes/ai/conventions/apply-gate-set-currentness.md`, and states that ticket-system comments are mirrors only.
- `/home/nes/ai/conventions/apply-gate-set-currentness.md:121` preserves ACR-285/ACR-286 `dual_score` and `folded_equivalent` behavior and invalidates inventory-resolution rows when upstream supported-surface inventory, authority, scope, or contract evidence shifts.

## ACR-286 settlement options recorded for traceability

ACR-290 records these ACR-286 settlement options neutrally and does not pre-select among them:

- `standalone Phase 8 row`
- `folded into another PR-review/risk row`
- `only Phase 4 with explicit non-applicability in later modes`

ACR-286 is the authority for choosing one of these. Until then, `apply-gate-set` callers preserve the unresolved Drift-2 readings through the `inventory_resolution` row's selected disposition, fold target, dual-score, rationale, and expiry fields.

## Anti-scope

- Do NOT redefine supported-surface semantics - ACR-286 owns that decision.
- Do NOT redefine `apply-gate-set` operator/workflow surface - ACR-291 owns.
- Do NOT author eval-spec scenarios beyond the supported-surface scope - ACR-292 owns broader.
- Do NOT smuggle pytest tests (`tests/test_*.py`, pytest imports/fixtures, pytest-shaped assertion code) into Step 6b.
- Do NOT introduce verifier scripts under `tools/<wu>-verify/`.
- Do NOT use `| tail -N` or other truncating filters on agents dispatches.
- Do NOT treat Linear comments as canonical proof; file-backed source and planning artifacts remain canonical, and ticket comments are mirrors.
- Do NOT settle Drift-2; this note records the dependency until ACR-286 settles it.

## Lifecycle / supersession

Supersession schema reference: `/home/nes/ai/conventions/prototype-pending-tests.md` section `Supersession-entry schema`.

This artifact remains active until ACR-286 ships its resolution document and the `apply-gate-set` operator schema removes the `dual_score` / `folded_equivalent` placeholders for supported-surface inventory resolution. At that point, ACR-286's resolution document supersedes this dependency note, and future callers should cite the settled ACR-286 supported-surface inventory contract instead of this compatibility record.

## Cross-links

- ACR-277 Linear: <https://linear.app/oulipoly/issue/ACR-277/>
- ACR-286 Linear: <https://linear.app/oulipoly/issue/ACR-286/>
- ACR-290 Linear: <https://linear.app/oulipoly/issue/ACR-290/drift-2-resolution-dependency-note-for-supported-surface-inventory>
- Prototype dossier path: `/home/nes/ai/planning/acr-277-clarify/dossier/`
- Drift-2 source: `/home/nes/ai/planning/acr-277-clarify/dossier/evidence/vector-b-structural-blockers.md:39-43`
- Inherited eval-spec scenario `APPLY-GATE-SET-007`: `/home/nes/ai/evals/acr-277-apply-gate-set-survives/eval.md:526-567`
- Inherited eval-spec scenario `APPLY-GATE-SET-007-IMPL-PIPELINE`: `/home/nes/ai/evals/acr-277-apply-gate-set-survives/eval.md:569-624`
- Inherited eval-spec scenario `ACR-288-IMPL-004`: `/home/nes/ai/evals/acr-277-apply-gate-set-survives/eval.md:637`
- Operator schema: `/home/nes/ai/agents/apply-gate-set.md:258-277`
- Workflow inventory-resolution language: `/home/nes/ai/workflows/apply-gate-set.md:102-125`, `/home/nes/ai/workflows/apply-gate-set.md:139-153`
- Currentness convention: `/home/nes/ai/conventions/apply-gate-set-currentness.md:121`
- Implementation caller references: `/home/nes/ai/agents/implementation-pipeline-orchestrator.md:510-516`, `/home/nes/ai/agents/implementation-pipeline-orchestrator.md:577-578`, `/home/nes/ai/agents/implementation-pipeline-orchestrator.md:608-614`, `/home/nes/ai/agents/implementation-pipeline-orchestrator.md:684-690`
- RCA caller references: `/home/nes/ai/agents/rca-orchestrator.md:86-137`
- Sibling ACR-289 note: `notes/acr-289-acr-285-proof-risk-drift.md`
- Sibling ACR-289 source path: `/home/nes/ai/notes/acr-289-acr-285-proof-risk-drift.md`
