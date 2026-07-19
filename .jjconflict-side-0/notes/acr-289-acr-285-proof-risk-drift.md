# ACR-289 / ACR-285 Dependency Note — Proof-risk inventory drift

## Purpose

This note records the ACR-285 dependency for Drift-1 proof-risk inventory resolution while `apply-gate-set` remains active across RCA and implementation-pipeline caller modes. ACR-289 owns this durable pointer and backlink evidence; ACR-285 remains the authority for settling whether proof-risk is standalone, folded into another row, or dual-scored until settlement.

The note is the source-tree canonical reference. It does not change product code, dispatch gates, operator schema, eval-spec scenarios, or proof-risk semantics. A planning-tree mirror lives at `${planning_dir}/risk/acr-289-acr-285-dependency-note.md` for WU evidence; this `notes/` copy is the public-facing canonical reference and the artifact downstream callers cite.

## Drift-1 source

Source: `~/ai/planning/acr-277-clarify/dossier/evidence/vector-b-structural-blockers.md:33-38`.

```markdown
- [x] **proof-risk-row-drift**
  - **Shape(s) blocked**: 2 and 4 partial; 3 blocked; 1 survives only if it resolves or dual-scores the inventory.
  - **What the shape cannot do**: A caller that copies the workflow reads proof-risk as a fifth Phase 4 proposal-risk row; a caller that copies the orchestrator omits it from the Phase 4 row list. The same jj WU could therefore produce different manifests depending on source.
  - **Evidence anchor**: ACR-277 Drift 1 brief; ACR-277 problem map; `workflows/code-quality.md` proof-risk applicability rules.
  - **Refinement that would address it**: Shape 1 must declare the canonical row inventory internally and record compatibility handling until ACR-285 resolves Drift 1.
```

The donor-reading mismatch is that workflow-derived callers can treat proof-risk as a fifth Phase 4 proposal-risk row, while orchestrator-derived callers can omit proof-risk from the Phase 4 row list. Until ACR-285 settles the proof-risk inventory model, `apply-gate-set` must preserve compatibility instead of silently choosing one donor reading.

## Canonical reference for proof-risk inventory-resolution

Canonical row schema: `~/ai/agents/apply-gate-set.md:258-276`.

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

The same canonical block states that ACR-285 proof-risk drift must represent both donor readings until ACR-285 settles, using `dual_score` where both readings affect blocking semantics and `folded_equivalent` only when cited child aggregate evidence preserves the same evidence class.

## Caller-mode preservation requirements

ACR-289 preserves these caller modes and line-range references without redefining them:

- `rca-post-apply`: `~/ai/agents/rca-orchestrator.md:86-137` dispatches `apply-gate-set(caller_mode=rca-post-apply)`, requires a `PASS` before downstream RCA lifecycle movement, and keeps RCA-local proof-risk / validation-integrity critics as prerequisites rather than substitutes for the broader gate-set result.
- `rca-post-apply`: `~/ai/agents/rca-orchestrator.md:156-168` preserves the existing proof-risk critic before RCA application planning when the proof plan is missing, malformed, proxy-only, or evidence-class mismatched.
- `implementation-phase-4`: `~/ai/agents/implementation-pipeline-orchestrator.md:507-514` requires the Phase 4 gate inventory to include `proof-risk` as a distinct row or an explicit ACR-285 `inventory-resolution` row, and blocks downstream movement on unresolved inventory-resolution rows.
- `implementation-phase-6`: `~/ai/agents/implementation-pipeline-orchestrator.md:577-578` requires distinct Step 6b and Step 6c invocation evidence and side-channel evidence before Step 6c dispatch; `~/ai/agents/implementation-pipeline-orchestrator.md:608-614` keeps post-Step-6c per-component code-quality and child-recursion decisions behind `apply-gate-set(caller_mode=implementation-phase-6)`.
- `implementation-phase-8`: `~/ai/agents/implementation-pipeline-orchestrator.md:684-690` requires `apply-gate-set(caller_mode=implementation-phase-8)`, carries proof-risk and validation-integrity runtime-claim transport where applicable, and blocks on stale or malformed gate evidence.

Shared preservation references:

- `~/ai/workflows/apply-gate-set.md:102-108` requires runtime claims and diffs to be transported into proof-risk children where applicable and requires inventory-resolution rows to dual-score or fold ACR-285 and ACR-286 readings until those trackers settle.
- `~/ai/workflows/apply-gate-set.md:139-153` points the canonical manifest schema to `agents/apply-gate-set.md`, points currentness to `~/ai/conventions/apply-gate-set-currentness.md`, and states that ticket-system comments are mirrors only.
- `~/ai/conventions/apply-gate-set-currentness.md` applies currentness to inventory-resolution rows and invalidates them when upstream proof-risk inventory, authority, scope, or contract evidence shifts.

## ACR-285 settlement options recorded for traceability

ACR-289 records these ACR-285 settlement options neutrally and does not pre-select among them:

- `standalone Phase 4 row`
- `folded into code-quality child row`
- `dual-scored / folded equivalent until further notice`

ACR-285 is the authority for choosing one of these. Until then, `apply-gate-set` callers preserve all three via the `inventory_resolution` row's `dual_scores` / `selected_disposition` fields.

## Anti-scope

- Do NOT redefine proof-risk semantics — ACR-285 owns that decision.
- Do NOT redefine `apply-gate-set` operator/workflow surface — ACR-291 owns.
- Do NOT author eval-spec scenarios beyond the proof-risk scope — ACR-292 owns broader.
- Do NOT smuggle pytest tests (`tests/test_*.py`, pytest imports/fixtures, pytest-shaped assertion code) into Step 6b.
- Do NOT introduce verifier scripts under `tools/<wu>-verify/`.
- Do NOT use `| tail -N` or other truncating filters on agents dispatches.

## Lifecycle / supersession

Supersession schema reference: `~/ai/conventions/prototype-pending-tests.md` § `Supersession-entry schema`.

This artifact remains active until ACR-285 ships its resolution document and the `apply-gate-set` operator schema removes the `dual_score` / `folded_equivalent` placeholders for proof-risk inventory resolution. At that point, ACR-285's resolution document supersedes this dependency note, and future callers should cite the settled ACR-285 proof-risk inventory contract instead of this compatibility record.

## Cross-links

- ACR-277 Linear: <https://linear.app/oulipoly/issue/ACR-277/>
- ACR-285 Linear: <https://linear.app/oulipoly/issue/ACR-285/phase-4-proof-risk-row-canonical-source-consolidation>
- ACR-289 Linear: <https://linear.app/oulipoly/issue/ACR-289/drift-1-resolution-dependency-note-for-proof-risk-inventory>
- Prototype dossier path: `~/ai/planning/acr-277-clarify/dossier/`
- Drift-1 source: `~/ai/planning/acr-277-clarify/dossier/evidence/vector-b-structural-blockers.md:33-38`
- Inherited eval-spec scenarios: `~/ai/evals/acr-277-apply-gate-set-survives/eval.md:526-637` (`APPLY-GATE-SET-007`, `APPLY-GATE-SET-007-IMPL-PIPELINE`, `ACR-288-IMPL-004`)
- Operator schema: `~/ai/agents/apply-gate-set.md:258-276`
- Workflow inventory-resolution language: `~/ai/workflows/apply-gate-set.md:102-108`, `~/ai/workflows/apply-gate-set.md:139-153`
- Currentness convention: `~/ai/conventions/apply-gate-set-currentness.md`
- Implementation caller references: `~/ai/agents/implementation-pipeline-orchestrator.md:507-514`, `~/ai/agents/implementation-pipeline-orchestrator.md:577-578`, `~/ai/agents/implementation-pipeline-orchestrator.md:608-614`, `~/ai/agents/implementation-pipeline-orchestrator.md:684-690`
- RCA caller references: `~/ai/agents/rca-orchestrator.md:86-137`, `~/ai/agents/rca-orchestrator.md:156-168`
