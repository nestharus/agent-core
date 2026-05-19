---
name: ACR-281 FC Auditor Finding Origin Eval
description: WRITE-state structural-verification spec for Function Classification auditor finding_origin and domain_relation hint fields, code-quality normalized propagation, and preserved non-fire boundaries.
lifecycle: WRITE
lifecycle_state: WRITE
slug: acr-281-fc-auditor-finding-origin
eval_id: acr-281-fc-auditor-finding-origin
owner_wu: ACR-281
operator_under_test: agents/function-classification-auditor.md
workflow_under_test: workflows/code-quality.md
read_only_referents:
  - agents/implementation-pipeline-orchestrator.md
  - conventions/code-quality.md
  - conventions/decomposition-strategies.md
  - conventions/evals.md
risk_class: HIGH
behavior_class: Structural verification of FC auditor origin/domain hint fields and normalized propagation
severity_when_fires: HIGH
evidence_source_kinds:
  - synthetic-fixture-inline
  - markdown-contract-review
suggested_action_class: revise-fc-origin-domain-hint-contract
---

# ACR-281 FC Auditor Finding Origin Eval

## Declared roles

`validator`, `mapper`

This eval spec validates that ACR-281 adds advisory FC finding-origin and domain-relation hints without changing A1 semantics, residual policy, strategy ownership, or the orchestrator scope boundary. It maps the FC-local hint fields into the normalized code-quality finding shape only as optional pass-through evidence.

## Lifecycle state

WRITE

This is a WRITE-state eval-spec authoring artifact under `~/ai/conventions/evals.md`. It defines the behavior contract for future detector or review work; it does not provide runnable detector code, fixtures, CI wiring, pytest tests, or verifier scripts.

## Identity

- `eval_id`: `acr-281-fc-auditor-finding-origin`
- `slug`: `acr-281-fc-auditor-finding-origin`
- `owner_wu`: `ACR-281`
- `artifact`: `evals/acr-281-fc-auditor-finding-origin/eval.md`
- `primary_surface`: `agents/function-classification-auditor.md`
- `normalization_surface`: `workflows/code-quality.md`
- `read_only_referents`: `agents/implementation-pipeline-orchestrator.md`, `conventions/code-quality.md`, `conventions/decomposition-strategies.md`, `conventions/evals.md`
- `contract`: `/home/nes/ai/planning/acr-281-fc-auditor-finding-origin/contracts/acr-281-fc-auditor-finding-origin.md`
- `proposal`: `/home/nes/ai/planning/acr-281-fc-auditor-finding-origin/proposals/acr-281-acr-281.md`
- `problem_map`: `/home/nes/ai/planning/acr-281-fc-auditor-finding-origin/research/acr-281-problem-map.md`
- `risk_profile`: `/home/nes/ai/planning/acr-281-fc-auditor-finding-origin/risk/acr-281-risk-profile.md`
- `hookpoints`: `/home/nes/ai/planning/acr-281-fc-auditor-finding-origin/research/acr-281-hookpoints.md`

## Behavior contract

The Step 6a contract text names twelve scenarios, but the authoritative scenario table contains thirteen scenario rows. This WRITE spec preserves every scenario row from `/home/nes/ai/planning/acr-281-fc-auditor-finding-origin/contracts/acr-281-fc-auditor-finding-origin.md`.

- `FC-ORIGIN-CHANGED-SAME-DOMAIN`: Synthetic mixed-origin diff scenario in eval spec; FC finding YAML carries `finding_origin: changed_function` and `domain_relation: same_domain`. Normalized finding mirrors them. Source: `/home/nes/ai/planning/acr-281-fc-auditor-finding-origin/contracts/acr-281-fc-auditor-finding-origin.md`.
- `FC-ORIGIN-CHANGED-UNRELATED-DOMAIN`: Synthetic mixed-origin diff scenario; FC finding YAML carries `finding_origin: changed_function` and `domain_relation: unrelated_domain`. Strategy selection remains orchestrator-owned. Source: `/home/nes/ai/planning/acr-281-fc-auditor-finding-origin/contracts/acr-281-fc-auditor-finding-origin.md`.
- `FC-ORIGIN-PREEXISTING-SAME-DOMAIN`: Synthetic touched-file scenario with unchanged function body evidence; FC finding YAML carries `finding_origin: pre_existing_in_touched_file` and `domain_relation: same_domain`. Finding still blocking, not residual. Source: `/home/nes/ai/planning/acr-281-fc-auditor-finding-origin/contracts/acr-281-fc-auditor-finding-origin.md`.
- `FC-ORIGIN-PREEXISTING-UNRELATED-DOMAIN`: Synthetic touched-file scenario; FC finding YAML carries `finding_origin: pre_existing_in_touched_file` and `domain_relation: unrelated_domain`. No automatic residual acceptance. Source: `/home/nes/ai/planning/acr-281-fc-auditor-finding-origin/contracts/acr-281-fc-auditor-finding-origin.md`.
- `FC-ORIGIN-WU-AUTHORED-UNKNOWN`: Synthetic added-function scenario with incomplete origin evidence; FC finding YAML carries `finding_origin: wu_authored_unknown`. Finding remains current and blocking if HIGH. Source: `/home/nes/ai/planning/acr-281-fc-auditor-finding-origin/contracts/acr-281-fc-auditor-finding-origin.md`.
- `FC-DOMAIN-UNKNOWN-INSUFFICIENT-EVIDENCE`: Synthetic ambiguous-domain scenario; FC finding YAML carries `domain_relation: unknown`. No fabricated same/unrelated classification. Documented safe fallback per AC1. Source: `/home/nes/ai/planning/acr-281-fc-auditor-finding-origin/contracts/acr-281-fc-auditor-finding-origin.md`.
- `FC-PRESERVE-SPLIT-CONVERGENCE`: Existing FC finding shape plus ACR-246 eval as fixture reference; all existing `suggested_split.convergence_proof.{current_blocking_finding,why_split_reduces_blocking_set,helper_overlay_handling}` fields preserved beside the new hints. Source: `/home/nes/ai/planning/acr-281-fc-auditor-finding-origin/contracts/acr-281-fc-auditor-finding-origin.md`.
- `CQ-NORMALIZED-HINT-PROPAGATION`: `workflows/code-quality.md` `## Finding Normalization`; `findings.json` / `findings.md` records preserve `finding_origin` / `domain_relation` when child report provides them; required fields unchanged. Source: `/home/nes/ai/planning/acr-281-fc-auditor-finding-origin/contracts/acr-281-fc-auditor-finding-origin.md`.
- `PHASE8-HINT-CONSUME-FALLBACK`: `agents/implementation-pipeline-orchestrator.md` Phase 8 existing aggregate-parsing path; implicit consumption non-fire: orchestrator's existing ACR-280 selector reads normalized aggregate; new fields flow through without orchestrator file edits; absent / `unknown` values fall back to existing inference. Source: `/home/nes/ai/planning/acr-281-fc-auditor-finding-origin/contracts/acr-281-fc-auditor-finding-origin.md`.
- `NONFIRE-AUDITOR-DOES-NOT-SELECT-STRATEGY`: `agents/function-classification-auditor.md` output contract plus `~/ai/conventions/decomposition-strategies.md` referent; non-fire: FC auditor does not choose MOVE-and-import, file decomposition, in-WU remediation, follow-up tickets, `DECOMPOSED`, or any strategy label. Source: `/home/nes/ai/planning/acr-281-fc-auditor-finding-origin/contracts/acr-281-fc-auditor-finding-origin.md`.
- `NONFIRE-A1-NOT-REDEFINED`: `~/ai/conventions/code-quality.md` A1 reference plus FC operator text; non-fire: new fields must not add, remove, rename, merge, or reinterpret A1 categories or thresholds. Source: `/home/nes/ai/planning/acr-281-fc-auditor-finding-origin/contracts/acr-281-fc-auditor-finding-origin.md`.
- `NONFIRE-NO-RESIDUAL-ACCEPTANCE`: `~/ai/conventions/code-quality.md` touched-file ownership plus `~/ai/conventions/decomposition-strategies.md` preserved anti-scope; non-fire: new fields must not permit pre-existing touched-file findings to advance as residuals or follow-up-only pass states. Source: `/home/nes/ai/planning/acr-281-fc-auditor-finding-origin/contracts/acr-281-fc-auditor-finding-origin.md`.
- `NONFIRE-ORCHESTRATOR-PHASE-8-NOT-TOUCHED`: `agents/implementation-pipeline-orchestrator.md` entire file; non-fire: ACR-281 does NOT modify the orchestrator file. Its existing Phase 8 wording remains unchanged and continues to reference the normalized aggregate-parsing path without depending on `finding_origin` / `domain_relation` being present. Explicit Phase 8 wording deferred to ACR-281b. Source: `/home/nes/ai/planning/acr-281-fc-auditor-finding-origin/contracts/acr-281-fc-auditor-finding-origin.md`.

## Scenarios

### FC-ORIGIN-CHANGED-SAME-DOMAIN

- Fixture/source/application point: Synthetic mixed-origin diff scenario in eval spec. Source: `/home/nes/ai/planning/acr-281-fc-auditor-finding-origin/contracts/acr-281-fc-auditor-finding-origin.md`.
- Expected observable signal: FC finding YAML carries `finding_origin: changed_function` and `domain_relation: same_domain`. Normalized finding mirrors them. Source: `/home/nes/ai/planning/acr-281-fc-auditor-finding-origin/contracts/acr-281-fc-auditor-finding-origin.md`.

### FC-ORIGIN-CHANGED-UNRELATED-DOMAIN

- Fixture/source/application point: Synthetic mixed-origin diff scenario. Source: `/home/nes/ai/planning/acr-281-fc-auditor-finding-origin/contracts/acr-281-fc-auditor-finding-origin.md`.
- Expected observable signal: FC finding YAML carries `finding_origin: changed_function` and `domain_relation: unrelated_domain`. Strategy selection remains orchestrator-owned. Source: `/home/nes/ai/planning/acr-281-fc-auditor-finding-origin/contracts/acr-281-fc-auditor-finding-origin.md`.

### FC-ORIGIN-PREEXISTING-SAME-DOMAIN

- Fixture/source/application point: Synthetic touched-file scenario with unchanged function body evidence. Source: `/home/nes/ai/planning/acr-281-fc-auditor-finding-origin/contracts/acr-281-fc-auditor-finding-origin.md`.
- Expected observable signal: FC finding YAML carries `finding_origin: pre_existing_in_touched_file` and `domain_relation: same_domain`. Finding still blocking, not residual. Source: `/home/nes/ai/planning/acr-281-fc-auditor-finding-origin/contracts/acr-281-fc-auditor-finding-origin.md`.

### FC-ORIGIN-PREEXISTING-UNRELATED-DOMAIN

- Fixture/source/application point: Synthetic touched-file scenario. Source: `/home/nes/ai/planning/acr-281-fc-auditor-finding-origin/contracts/acr-281-fc-auditor-finding-origin.md`.
- Expected observable signal: FC finding YAML carries `finding_origin: pre_existing_in_touched_file` and `domain_relation: unrelated_domain`. No automatic residual acceptance. Source: `/home/nes/ai/planning/acr-281-fc-auditor-finding-origin/contracts/acr-281-fc-auditor-finding-origin.md`.

### FC-ORIGIN-WU-AUTHORED-UNKNOWN

- Fixture/source/application point: Synthetic added-function scenario with incomplete origin evidence. Source: `/home/nes/ai/planning/acr-281-fc-auditor-finding-origin/contracts/acr-281-fc-auditor-finding-origin.md`.
- Expected observable signal: FC finding YAML carries `finding_origin: wu_authored_unknown`. Finding remains current and blocking if HIGH. Source: `/home/nes/ai/planning/acr-281-fc-auditor-finding-origin/contracts/acr-281-fc-auditor-finding-origin.md`.

### FC-DOMAIN-UNKNOWN-INSUFFICIENT-EVIDENCE

- Fixture/source/application point: Synthetic ambiguous-domain scenario. Source: `/home/nes/ai/planning/acr-281-fc-auditor-finding-origin/contracts/acr-281-fc-auditor-finding-origin.md`.
- Expected observable signal: FC finding YAML carries `domain_relation: unknown`. No fabricated same/unrelated classification. Documented safe fallback per AC1. Source: `/home/nes/ai/planning/acr-281-fc-auditor-finding-origin/contracts/acr-281-fc-auditor-finding-origin.md`.

### FC-PRESERVE-SPLIT-CONVERGENCE

- Fixture/source/application point: Existing FC finding shape plus ACR-246 eval as fixture reference. Source: `/home/nes/ai/planning/acr-281-fc-auditor-finding-origin/contracts/acr-281-fc-auditor-finding-origin.md`.
- Expected observable signal: All existing `suggested_split.convergence_proof.{current_blocking_finding,why_split_reduces_blocking_set,helper_overlay_handling}` fields preserved beside the new hints. Source: `/home/nes/ai/planning/acr-281-fc-auditor-finding-origin/contracts/acr-281-fc-auditor-finding-origin.md`.

### CQ-NORMALIZED-HINT-PROPAGATION

- Fixture/source/application point: `workflows/code-quality.md` `## Finding Normalization`. Source: `/home/nes/ai/planning/acr-281-fc-auditor-finding-origin/contracts/acr-281-fc-auditor-finding-origin.md`.
- Expected observable signal: `findings.json` / `findings.md` records preserve `finding_origin` / `domain_relation` when child report provides them; required fields unchanged. Source: `/home/nes/ai/planning/acr-281-fc-auditor-finding-origin/contracts/acr-281-fc-auditor-finding-origin.md`.

### PHASE8-HINT-CONSUME-FALLBACK

- Fixture/source/application point: `agents/implementation-pipeline-orchestrator.md` Phase 8 existing aggregate-parsing path. Source: `/home/nes/ai/planning/acr-281-fc-auditor-finding-origin/contracts/acr-281-fc-auditor-finding-origin.md`.
- Expected observable signal: Implicit consumption non-fire: orchestrator's existing ACR-280 selector reads normalized aggregate; new fields flow through without orchestrator file edits; absent / `unknown` values fall back to existing inference. Source: `/home/nes/ai/planning/acr-281-fc-auditor-finding-origin/contracts/acr-281-fc-auditor-finding-origin.md`.

### NONFIRE-AUDITOR-DOES-NOT-SELECT-STRATEGY

- Fixture/source/application point: `agents/function-classification-auditor.md` output contract plus `~/ai/conventions/decomposition-strategies.md` referent. Source: `/home/nes/ai/planning/acr-281-fc-auditor-finding-origin/contracts/acr-281-fc-auditor-finding-origin.md`.
- Expected observable signal: Non-fire: FC auditor does not choose MOVE-and-import, file decomposition, in-WU remediation, follow-up tickets, `DECOMPOSED`, or any strategy label. Source: `/home/nes/ai/planning/acr-281-fc-auditor-finding-origin/contracts/acr-281-fc-auditor-finding-origin.md`.

### NONFIRE-A1-NOT-REDEFINED

- Fixture/source/application point: `~/ai/conventions/code-quality.md` A1 reference plus FC operator text. Source: `/home/nes/ai/planning/acr-281-fc-auditor-finding-origin/contracts/acr-281-fc-auditor-finding-origin.md`.
- Expected observable signal: Non-fire: new fields must not add, remove, rename, merge, or reinterpret A1 categories or thresholds. Source: `/home/nes/ai/planning/acr-281-fc-auditor-finding-origin/contracts/acr-281-fc-auditor-finding-origin.md`.

### NONFIRE-NO-RESIDUAL-ACCEPTANCE

- Fixture/source/application point: `~/ai/conventions/code-quality.md` touched-file ownership plus `~/ai/conventions/decomposition-strategies.md` preserved anti-scope. Source: `/home/nes/ai/planning/acr-281-fc-auditor-finding-origin/contracts/acr-281-fc-auditor-finding-origin.md`.
- Expected observable signal: Non-fire: new fields must not permit pre-existing touched-file findings to advance as residuals or follow-up-only pass states. Source: `/home/nes/ai/planning/acr-281-fc-auditor-finding-origin/contracts/acr-281-fc-auditor-finding-origin.md`.

### NONFIRE-ORCHESTRATOR-PHASE-8-NOT-TOUCHED

- Fixture/source/application point: `agents/implementation-pipeline-orchestrator.md` (entire file). Source: `/home/nes/ai/planning/acr-281-fc-auditor-finding-origin/contracts/acr-281-fc-auditor-finding-origin.md`.
- Expected observable signal: Non-fire: ACR-281 does NOT modify the orchestrator file. Its existing Phase 8 wording remains unchanged and continues to reference the normalized aggregate-parsing path without depending on `finding_origin` / `domain_relation` being present. Explicit Phase 8 wording deferred to ACR-281b. Source: `/home/nes/ai/planning/acr-281-fc-auditor-finding-origin/contracts/acr-281-fc-auditor-finding-origin.md`.

## Minimum finding contract

Every future finding produced from this eval must preserve the minimum fields from `~/ai/conventions/evals.md`:

- `eval_id`
- `severity`
- `evidence_paths`
- `summary`
- `suggested_action`
- `confidence`

Recommended ACR-281 extensions:

- `scenario_id`
- `owner_wu`
- `operator_under_test`
- `workflow_under_test`
- `observed_finding_origin`
- `observed_domain_relation`
- `expected_finding_origin`
- `expected_domain_relation`
- `normalized_record_path`
- `strategy_boundary_failure`
- `a1_redefinition_signal`
- `residual_acceptance_signal`
- `orchestrator_edit_signal`

Severity guidance:

- `HIGH` when the observed behavior fabricates origin/domain evidence, drops required FC finding fields, changes A1 semantics, introduces residual acceptance, moves strategy selection into the FC auditor, modifies the orchestrator for ACR-281, or drops optional hint propagation when child findings provide the fields.
- `MEDIUM` when evidence is incomplete but suggests one of the protected boundaries may have regressed.
- `LOW` only for trace or artifact drift in a future detector where the protected behavior cannot be determined.

## Anti-scope

This WRITE-state spec does not define runnable eval code, parser code, adapters, fixtures, CLI integration, CI, cron, ticket automation, pytest files, pytest imports, pytest fixtures, pytest-shaped structural checks, or one-off verifier scripts.

## Suggested action

Revise `agents/function-classification-auditor.md` and `workflows/code-quality.md` so FC findings include advisory `finding_origin` and `domain_relation` values when evidence supports them, preserve safe fallbacks when evidence is incomplete, pass optional hint fields through normalized code-quality records when present, and keep A1 classification, residual policy, report provenance, and strategy selection ownership unchanged.

## Lifecycle notes

ACR-281 owns only this WRITE spec in Step 6b. It does not own a runnable harness, pytest file, pytest imports or fixtures, synthetic fixture files, verifier scripts, CLI wiring, or detector implementation. Step 6c separately owns the markdown product edits and must consume this spec without modifying `agents/implementation-pipeline-orchestrator.md`.

## Cross-references

- Step 6a contract: `/home/nes/ai/planning/acr-281-fc-auditor-finding-origin/contracts/acr-281-fc-auditor-finding-origin.md`
- R4 proposal: `/home/nes/ai/planning/acr-281-fc-auditor-finding-origin/proposals/acr-281-acr-281.md`
- Problem map: `/home/nes/ai/planning/acr-281-fc-auditor-finding-origin/research/acr-281-problem-map.md`
- Risk profile: `/home/nes/ai/planning/acr-281-fc-auditor-finding-origin/risk/acr-281-risk-profile.md`
- Hookpoints: `/home/nes/ai/planning/acr-281-fc-auditor-finding-origin/research/acr-281-hookpoints.md`
- Eval convention: `/home/nes/ai/conventions/evals.md`
