---
id: acr-277-apply-gate-set-wiring
slug: acr-277-apply-gate-set-wiring
eval_id: acr-277-apply-gate-set-wiring
lifecycle: WRITE
lifecycle_state: WRITE
class: structural-verification
behavior_class: apply-gate-set-wiring-surface-discoverability
created: 2026-05-19
owner: ACR-292
ticket: ACR-292
ticket_mapping:
  - ACR-292
severity_when_fires: MEDIUM
evidence_source_kinds:
  - agents-trace-json
  - planning-directory-artifacts
  - process-tree-auditor-report
  - join-manifest
  - aggregate-code-quality-report
  - pr-review-gate-reports
  - audit-history-decisions-record
suggested_action_class: repair-shared-apply-gate-set-wiring-and-caller-mode-inventory
description: Structural verification for apply-gate-set operator/workflow/index discoverability and RCA/implementation caller-mode inventory equivalence.
---

# ACR-277 Apply-Gate-Set Wiring Eval

## Purpose

This WRITE-state structural-verification eval specifies the companion wiring surface for the shared `apply-gate-set`: operator discoverability, workflow discoverability, workflow-index discoverability, and caller-mode inventory equivalence between RCA and implementation adapters. It does not implement or mutate those surfaces.

## Scope

This eval covers only repository-visible wiring and inventory evidence for `agents/apply-gate-set.md`, `workflows/apply-gate-set.md`, `workflows/index.json`, and the caller-mode manifests/adapters that should expose equivalent active row families. It verifies that proof-risk, supported-surface, runtime-claim transport, process-tree topology mode, currentness keys, skip-with-followup rows, and bootstrap-exception ratification rows are present or explicitly resolved for both RCA-mode and implementation-mode.

ACR-287 overlap is resolved by Option A - Absorb at the RCA caller boundary through the primary RCA eval. This companion eval keeps the shared wiring parity needed for `APPLY-GATE-SET-007` and cites the primary RCA eval as the stricter detector for inherited RCA-mode behavior.

Out of scope: editing `agents/`, `workflows/`, `conventions/`, `clients/`, `tools/`, or executable test surfaces; defining currentness-invalidation algorithms; defining topology-mode selection algorithms; or producing runnable detector code.

## Evidence Rules

Evidence is repository file content plus resolved manifests and trace artifacts from future `apply-gate-set` runs. A detector may inspect frontmatter/body text in the operator/workflow/index surfaces, saved `agents trace --json`, prompt/log paths, join manifests, inventory-resolution rows, audit-history entries, DECISIONS entries, and peer RCA/implementation gate-set reports.

Evidence must bind each caller-mode comparison to current manifest identity, not inferred intent. A row is equivalent only when it has the same active blocking semantics or an explicit inventory-resolution record naming the source row, fold/dual-score disposition, rationale, and currentness evidence.

## Required trace fields

- Repository paths and content hashes for `agents/apply-gate-set.md`, `workflows/apply-gate-set.md`, and `workflows/index.json`.
- Workflow/operator frontmatter fields, declared roles, dispatch contract fields, inputs, expectations, outputs, non-goals, caller-mode names, and row-family inventory text.
- RCA-mode and implementation-mode caller ids, root invocation UUIDs, prompt paths, manifests, currentness keys, and audit-history paths.
- Inventory rows for proof-risk, supported-surface, runtime-claim transport, process-tree topology mode, currentness keys, skip-with-followup, bootstrap-exception ratification, stale-refusal, and inventory-resolution.
- `report_paths` and `trace_locator` fields for each compared row family.

## Finding schema

Every future finding from this spec preserves the minimum fields from `~/ai/conventions/evals.md` section Finding schema:

- `eval_id`
- `severity`
- `evidence_paths`
- `summary`
- `suggested_action`
- `confidence`

Wiring findings also carry:

- `scenario_id`: one of `WIRING-001` through `WIRING-007`.
- `caller_modes`: compared caller modes, when applicable.
- `inventory_rows_compared`
- `gate`
- `report_paths`
- `trace_locator`

## Supersession mapping

| Inherited | ACR277-RCA-* mapping | Owning eval |
|---|---|---|
| `APPLY-GATE-SET-001` | `ACR277-RCA-002`, `ACR277-RCA-003`, `ACR277-RCA-004`, `ACR277-RCA-007`, `ACR277-RCA-010` | primary RCA eval |
| `APPLY-GATE-SET-002` | `ACR277-RCA-005` | primary RCA eval |
| `APPLY-GATE-SET-003` | `ACR277-RCA-001`, `ACR277-RCA-008`, `ACR277-RCA-011` | primary RCA eval |
| `APPLY-GATE-SET-004` | `ACR277-RCA-008` | primary RCA eval |
| `APPLY-GATE-SET-005` | `ACR277-RCA-008` | primary RCA eval |
| `APPLY-GATE-SET-006` | `ACR277-RCA-005`, `ACR277-RCA-008` | primary RCA eval, with ACR-288 implementation-pipeline caller-boundary discharge cited when applicable |
| `APPLY-GATE-SET-007` | `ACR277-RCA-011` | primary RCA eval plus companion wiring caller-mode equivalence |

This companion eval does not replace the primary RCA supersession rows. It verifies the shared surfaces and caller-mode equivalence that make the stricter RCA scenarios discoverable and comparable across adapters.

## Drift inheritance

- ACR-285 - Proof-risk row drift between workflow doc and orchestrator doc. Disposition: dual-score. Both proof-risk rows must remain present in RCA-mode and implementation-mode manifests unless a current inventory-resolution row records source row, fold target, rationale, and equivalent blocking semantics.
- ACR-286 - Supported-surface row drift around PR-review/Phase 8. Disposition: dual-score. Both supported-surface rows must remain present in RCA-mode and implementation-mode manifests unless a current inventory-resolution row records source row, fold target, rationale, and equivalent blocking semantics.

## Scenarios

### WIRING-001: Shared operator surface is present and actively dispatchable

Scenario id: `WIRING-001`

Intended observation: `agents/apply-gate-set.md` must be present as the shared active operator with frontmatter, declared roles, caller-mode inputs, output contracts, blocking semantics, row families, manifest/currentness schema, and dispatch shape.

Gate this scenario covers: `shared-operator-discoverability`.

Evidence fields: `agents/apply-gate-set.md` path/hash, frontmatter fields, `## Declared roles`, contract/inputs/outputs sections, caller-mode names, row-family inventory text, dispatch command/prompt-shape text, and anti-passive-inheritance language.

Positive evidence (eval should produce a finding when):

- The operator file is absent, not routable, passive-only, or lacks active dispatch/blocking semantics.
- Frontmatter, declared roles, caller modes, required inputs, outputs, row families, currentness keys, or stop conditions are missing.
- The file implies RCA callers should inherit implementation-pipeline gates passively instead of invoking the shared gate-set.

Non-fire cases:

- The operator surface exists and names active dispatch, supported caller modes, row families, stop conditions, manifests, currentness keys, and forbidden passive inheritance.
- A current owner note records a deliberate rename with equivalent discoverability and routing evidence.

Finding schema: common wiring schema plus `scenario_id=WIRING-001`, `gate=shared-operator-discoverability`, `report_paths`, and `trace_locator`.

Suggested action: repair the shared operator contract in its owning WU, preserving the active dispatch and blocking contract rather than duplicating caller logic.

Supersession linkage: Supports the wiring side of `APPLY-GATE-SET-003` and `APPLY-GATE-SET-007`; primary RCA supersession remains in `ACR277-RCA-001` and `ACR277-RCA-011`.

### WIRING-002: Companion workflow surface is present with dispatch contract

Scenario id: `WIRING-002`

Intended observation: `workflows/apply-gate-set.md` must be present as the companion workflow with frontmatter, dispatch contract, inputs, expectations, outputs, non-goals, caller modes, and manifest/audit-history references matching the operator.

Gate this scenario covers: `workflow-contract-discoverability`.

Evidence fields: `workflows/apply-gate-set.md` path/hash, frontmatter, dispatch contract block, inputs, expectations, outputs, non-goals, caller-mode text, manifest/currentness references, and parity notes to the operator file.

Positive evidence (eval should produce a finding when):

- The workflow file is absent or not routable as an active gate-set contract.
- Inputs, expectations, outputs, non-goals, caller modes, or manifest/audit-history references are missing.
- Workflow text conflicts with the operator contract on dispatch shape, stop conditions, currentness, or row families.

Non-fire cases:

- The workflow mirrors the operator contract and names caller modes, procedure, outputs, manifests, audit-history references, currentness keys, and non-goals.
- Any intentional difference has a current parity note with equivalent blocking semantics.

Finding schema: common wiring schema plus `scenario_id=WIRING-002`, `gate=workflow-contract-discoverability`, `report_paths`, and `trace_locator`.

Suggested action: repair workflow contract parity through the apply-gate-set owner and keep caller-specific logic out of the companion workflow.

Supersession linkage: Supports discoverability needed for `APPLY-GATE-SET-003` and `APPLY-GATE-SET-007`; stricter RCA detection remains in `ACR277-RCA-001` and `ACR277-RCA-011`.

### WIRING-003: Workflow index exposes apply-gate-set and caller modes

Scenario id: `WIRING-003`

Intended observation: `workflows/index.json` must include a discoverable `apply-gate-set` entry naming the workflow path and caller modes so orchestrators can route the shared gate-set workflow.

Gate this scenario covers: `workflow-index-discoverability`.

Evidence fields: `workflows/index.json` path/hash, `apply-gate-set` entry, workflow id/path, caller-mode list, inputs, expectations, outputs, non-goals, and parity with workflow frontmatter/body.

Positive evidence (eval should produce a finding when):

- The index lacks an `apply-gate-set` entry or routes to an unrelated workflow.
- The entry omits RCA or implementation caller modes.
- The entry conflicts with workflow frontmatter/body on inputs, outputs, expectations, or non-goals.

Non-fire cases:

- The index entry names the apply-gate-set workflow, path, caller modes, inputs, expectations, outputs, and non-goals in parity with the workflow.
- A current rename/migration entry preserves routability and caller-mode discoverability.

Finding schema: common wiring schema plus `scenario_id=WIRING-003`, `gate=workflow-index-discoverability`, `report_paths`, and `trace_locator`.

Suggested action: repair the index entry so routing discovers the shared workflow instead of relying on caller-local copies.

Supersession linkage: Supports the routing/discoverability side of `APPLY-GATE-SET-003`.

### WIRING-004: Proof-risk and supported-surface rows are present in both caller-mode manifests

Scenario id: `WIRING-004`

Intended observation: RCA-mode and implementation-mode manifests must both include proof-risk and supported-surface row families, or explicit inventory-resolution rows with equivalent blocking semantics.

Gate this scenario covers: `caller-mode-inventory-equivalence-proof-risk-supported-surface`.

Evidence fields: RCA-mode manifest, implementation-mode manifests for relevant phases, proof-risk rows, supported-surface rows, dual-score/fold rows, inventory-resolution artifacts, DECISIONS entries, verdicts, and currentness keys.

Positive evidence (eval should produce a finding when):

- Proof-risk row is present in one caller mode and absent in the other with no dual-score/fold resolution.
- Supported-surface row is present in one caller mode and absent in the other with no dual-score/fold resolution.
- A resolution row lacks source row, fold target, rationale, verdict, currentness evidence, or equivalent blocking semantics.

Non-fire cases:

- Both caller modes emit proof-risk and supported-surface rows.
- Drift is dual-scored, or folded with a current inventory-resolution row preserving blocking behavior.

Finding schema: common wiring schema plus `scenario_id=WIRING-004`, `caller_modes`, `inventory_rows_compared`, `gate=inventory-equivalence`, `report_paths`, and `trace_locator`.

Suggested action: preserve both row families in both adapters or record explicit inventory resolution in shared `apply-gate-set` evidence.

Supersession linkage: Supports `APPLY-GATE-SET-007` and composes with `ACR277-RCA-011`.

### WIRING-005: Runtime-claim transport and process-tree topology mode keys thread through both adapters

Scenario id: `WIRING-005`

Intended observation: RCA-mode and implementation-mode adapters must both thread runtime-claim transport keys and process-tree topology-mode keys into manifests, prompts, and reports.

Gate this scenario covers: `runtime-claim-transport`, `process-tree-topology-mode-key`.

Evidence fields: caller-mode manifests, adapter prompts, runtime-claim refs/hashes, topology-mode keys, process-tree expected-process manifests/reports, aggregate reports, join-manifest rows, and currentness keys.

Positive evidence (eval should produce a finding when):

- Runtime-claim ref/hash is present in one caller mode and missing or stale in the other.
- Topology-mode key is present in one caller mode and missing or stale in the other.
- Prompts or reports drop runtime-claim or topology-mode evidence before manifest aggregation.

Non-fire cases:

- Both adapters preserve runtime-claim and topology-mode keys from prompt through manifest/report output.
- A current non-applicability row explains why a key is not required for a specific caller mode and preserves blocking behavior.

Finding schema: common wiring schema plus `scenario_id=WIRING-005`, `caller_modes`, `inventory_rows_compared`, `gate=runtime-and-topology-key-transport`, `report_paths`, and `trace_locator`.

Suggested action: repair adapter input/output threading so runtime-claim and topology-mode keys are first-class manifest fields in both caller modes.

Supersession linkage: Supports `APPLY-GATE-SET-002`, `APPLY-GATE-SET-003`, and `APPLY-GATE-SET-007`; stricter RCA detectors are `ACR277-RCA-005`, `ACR277-RCA-001`, and `ACR277-RCA-011`.

### WIRING-006: Currentness keys re-verify after Phase 2 root-cause re-entry in both adapters

Scenario id: `WIRING-006`

Intended observation: Currentness keys must be represented for both RCA-mode and implementation-mode adapters, and RCA Phase 2 root-cause re-entry must force re-verification or stale-refusal evidence before handoff.

Gate this scenario covers: `currentness-key-equivalence`, `root-cause-re-entry-reverification`, `stale-refusal`.

Evidence fields: prior/current manifests, currentness identity keys, RCA Phase 2 re-entry marker, implementation phase rerun markers when applicable, stale-refusal rows, rerun rows, artifact hashes, `verified_at`, and handoff artifacts.

Positive evidence (eval should produce a finding when):

- Currentness keys are missing from either adapter manifest.
- RCA re-entry occurs and old rows are reused without rerun, re-verification, or stale-refusal.
- Implementation-mode currentness evidence cannot be compared because required identity fields are absent or stale.

Non-fire cases:

- Both adapters carry comparable currentness keys, and stale rows after re-entry are refused, rerun, or re-verified before handoff.
- Non-applicability is current and blocks silent reuse.

Finding schema: common wiring schema plus `scenario_id=WIRING-006`, `caller_modes`, `inventory_rows_compared`, `gate=currentness-key-equivalence`, `report_paths`, and `trace_locator`.

Suggested action: repair currentness-key rows and require re-verification/stale-refusal evidence after RCA re-entry before downstream movement.

Supersession linkage: Supports `APPLY-GATE-SET-005` and `APPLY-GATE-SET-003`; stricter RCA detector is `ACR277-RCA-008`.

### WIRING-007: Skip-with-followup and bootstrap-exception ratification rows are present when applicable

Scenario id: `WIRING-007`

Intended observation: Both caller-mode adapters must expose skip-with-followup rows and bootstrap-exception ratification rows when applicable, with current DECISIONS/follow-up evidence and equivalent blocking semantics.

Gate this scenario covers: `skip-with-followup`, `bootstrap-exception-ratification`, `exception-row-equivalence`.

Evidence fields: RCA-mode and implementation-mode manifests, skipped gate rows, accepted risk, owner, evidence already run, follow-up ticket/PR, due date, post-push/pre-merge flag, bootstrap-exception row, DECISIONS entry, four-condition record, and currentness keys.

Positive evidence (eval should produce a finding when):

- A gate is skipped in either caller mode without a complete skip-with-followup row.
- Bootstrap-exception ratification is claimed without DECISIONS authority or four-condition evidence.
- Skip or exception rows are present in one caller mode but unsupported or silently absent in the other without resolution.

Non-fire cases:

- Applicable skip and exception rows are complete, current, path-backed, and preserve blocking behavior in both caller modes.
- No skip or exception is claimed, and manifests explicitly show normal gate rows or current non-applicability.

Finding schema: common wiring schema plus `scenario_id=WIRING-007`, `caller_modes`, `inventory_rows_compared`, `gate=skip-exception-equivalence`, `report_paths`, and `trace_locator`.

Suggested action: repair skip/exception row support in the shared gate-set contract or adapter manifests, and block handoff until DECISIONS/follow-up evidence is current.

Supersession linkage: Supports `APPLY-GATE-SET-004`, `APPLY-GATE-SET-006`, and `APPLY-GATE-SET-007`; stricter RCA detectors are `ACR277-RCA-008`, `ACR277-RCA-005`, and `ACR277-RCA-011`.

## Residuals

No structural-coverage residual is expected at WRITE state. This eval records the wiring/discoverability and caller-mode-equivalence specification; downstream runnable detector and enforcement work owns future ROLL_OUT evidence.

## Lifecycle state: WRITE

Current state: `WRITE`. The behavior specification exists, but no runnable detector is required to exist per `~/ai/conventions/evals.md` section Lifecycle states. Transition to `ROLL_OUT` requires downstream detector evidence, false-positive review, wiring readiness, and durable lifecycle notes.

## Forbidden outputs

This WRITE-state structural-verification route must not author
`tools/<wu>-verify/<anything>.py`, `tests/test_*.py`, pytest imports,
pytest fixtures, or pytest-shaped assertion code (per
`~/ai/conventions/evals.md` § Anti-scope).

## Cross-references

- `/home/nes/ai/planning/acr-292-impl-eval-spec-authoring/contracts/acr-292-eval-spec-authoring.md`
- `/home/nes/ai/planning/acr-292-impl-eval-spec-authoring/proposals/acr-292-ACR-292.md`
- `/home/nes/ai/planning/acr-292-impl-eval-spec-authoring/research/acr-292-problem-map.md`
- `/home/nes/ai/planning/acr-292-impl-eval-spec-authoring/research/acr-292-hookpoints.md`
- `/home/nes/ai/planning/acr-292-impl-eval-spec-authoring/.scratch/predecessor-prototype-evidence.md`
- `/home/nes/ai/worktrees/acr-292-impl-eval-spec-authoring/evals/acr-287-rca-post-apply-gate-set/eval.md`
- `prototype-acr-277-clarify:evals/acr-277-apply-gate-set-survives/eval.md`
- `~/ai/conventions/evals.md`
- `~/ai/conventions/prototype-pending-tests.md`
- ACR-277 dossier evidence vectors A, B, and C named by the prototype source eval.
