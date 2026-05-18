---
id: acr-254-workflow-wiring
slug: acr-254-workflow-wiring
lifecycle: WRITE
lifecycle_state: WRITE
operator_under_test: workflows/implementation-pipeline.md; workflows/code-quality.md; agents/rca-orchestrator.md; conventions/code-quality.md
created: 2026-05-18
risk_class: HIGH
scope: ACR-254 workflow, RCA, and convention wiring for active validation-integrity and proof-risk enforcement
behavior_class: Structural workflow wiring and active-layer documentation
severity_when_fires: HIGH
evidence_source_kinds:
  - workflow-markdown
  - operator-markdown
  - convention-markdown
  - dispatch-manifest
  - join-manifest
suggested_action_class: revise-workflow-wiring-before-step6c-acceptance
supersedes: []
---

# ACR-254 Workflow Wiring Eval

## Purpose

This WRITE-state eval specification covers the MODIFY-surface behaviors added by ACR-254 R3 that are not purely operator-local. It tells Step 6c what workflow, RCA, and convention wiring must exist when the product files are authored.

The spec is not executable test code. Each fixture is a deterministic synthetic workflow or convention fragment, and the expected verdict is the assertion surface.

## Operator Under Test

This spec applies to the product surfaces that will dispatch or document the new active auditors:

- `workflows/implementation-pipeline.md`
- `workflows/code-quality.md`
- `agents/rca-orchestrator.md`
- `conventions/code-quality.md`

## Finding Contract

Every finding produced by a future detector must preserve the eval convention minimum fields:

- `eval_id`
- `severity`
- `evidence_paths`
- `summary`
- `suggested_action`
- `confidence`

Workflow-wiring findings also carry:

- `finding_ids`: `ACR254-WW-<NNN>`.
- `surface`
- `missing_or_invalid_wiring`
- `required_artifact_path`
- `expected_terminal_verdict`

## Required Trace Fields

- product surface path
- surface fragment or resolved markdown text
- when applicable, dispatch manifest or join manifest fragment
- caller phase (`Phase 3`, `Phase 4`, `Phase 6`, `Phase 8`, or `RCA`)

## Scenarios

### ACR254-WW-001: Phase 3 proposal template requires proof plan

Fixture: Synthetic `workflows/implementation-pipeline.md` Phase 3 required-output fragment:

```text
Phase 3 required proposal sections:
  - Problem statement
  - Supported-surface track
  - Test-intent track
  - Estimate refinement
No required "## Proof plan" section is named.
```

Expected operator verdict: `HIGH`.

Expected finding-id namespace: `ACR254-WW-001`.

Rationale: Phase 3 must require `## Proof plan` with runtime claim, proof method, and evidence-class match.

### ACR254-WW-002: Phase 4 proof-risk row is independent

Fixture: Synthetic Phase 4 risk-gate join manifest rule:

```text
phase-4 gates:
  - audit
  - scope
  - shortcut
  - supported-surface
  - code-quality
No gate_name=proof-risk row exists.
```

Expected operator verdict: `HIGH`.

Expected finding-id namespace: `ACR254-WW-002`.

Rationale: `proof-risk-auditor` must be a fifth direct proposal-risk gate with canonical output path, currentness, sha256, verdict line, and producing invocation UUID.

### ACR254-WW-003: code-quality fanout selects validation-integrity when diff evidence exists

Fixture: Synthetic `workflows/code-quality.md` dispatch manifest fragment:

```text
caller: Phase 8 actual PR diff
inputs: diff_path, proposal_path, proof_plan_excerpt, runtime_claim
children:
  - push-pull-auditor Required=true
  - function-classification-auditor Required=true
  - cohesion-auditor Required=true
  - coupling-auditor Required=true
  - validation-integrity-auditor Required=false reason="not part of standard A1 fanout"
```

Expected operator verdict: `HIGH`.

Expected finding-id namespace: `ACR254-WW-003`.

Rationale: Phase 8 actual PR diffs always have runtime-claim context under the new Phase 3 rule, so validation-integrity must be `Required=true`.

### ACR254-WW-004: code-quality fanout selects proof-risk when proof-plan context exists

Fixture: Synthetic `workflows/code-quality.md` dispatch manifest fragment:

```text
caller: Phase 8 actual PR diff
inputs: proposal_path with ## Proof plan, proof_plan_excerpt, runtime_claim
children:
  - proof-risk-auditor Required=false reason="proof already reviewed in Phase 4"
aggregate: LOW because other auditors were LOW
```

Expected operator verdict: `HIGH`.

Expected finding-id namespace: `ACR254-WW-004`.

Rationale: Phase 8 must compare the approved proof plan against the actual diff; stale Phase 4 proof-risk evidence cannot replace actual-diff review.

### ACR254-WW-005: Phase 8 code-quality aggregate join row

Fixture: Synthetic `workflows/implementation-pipeline.md` Phase 8 fragment:

```text
Phase 8 dispatch:
  dispatch four PR-review gates in parallel
  write phase-8-join-manifest.json with one row per PR-review gate
No code-quality fanout dispatch and no gate_name=code-quality row.
```

Expected operator verdict: `HIGH`.

Expected finding-id namespace: `ACR254-WW-005`.

Rationale: R3 requires implementation-pipeline-owned Phase 8 code-quality dispatch against the actual PR diff and a join row with `gate_name=code-quality`.

### ACR254-WW-006: RCA critic dimensions are all wired

Fixture: Synthetic `agents/rca-orchestrator.md` RCA phase fragment:

```text
RCA phases:
  investigator emits evidence
  fix-decision chooses fix
  apply fix
  verification reruns tests
Missing:
  investigator-critic.md
  fix-decision-critic.md
  verification-critic.md
```

Expected operator verdict: `HIGH`.

Expected finding-id namespace: `ACR254-WW-006`.

Rationale: ACR-254 requires investigator evidence-class criticism, fix-decision proof-risk criticism, and verification validation-integrity criticism, with non-LOW or stop-state verdicts blocking downstream RCA phases.

### ACR254-WW-007: code-quality convention documents active layer without re-encoding rules

Fixture: Synthetic `conventions/code-quality.md` fragment:

```text
ACR-254 rule:
  Never remove assertions, add skips, use mocks, replace fixtures, or relax schemas.
  The convention itself is the enforcement source.
Missing:
  agents/validation-integrity-auditor.md
  agents/proof-risk-auditor.md
  WRITE eval spec citations
```

Expected operator verdict: `HIGH`.

Expected finding-id namespace: `ACR254-WW-007`.

Rationale: The convention must cite the active enforcement operators and WRITE eval specs, and it must state that enforcement lives in operators and workflow dispatch rather than passive convention prose.

### ACR254-WW-008: aggregate preserves non-LOW and stop states

Fixture: Synthetic code-quality aggregate fragment:

```text
child reports:
  validation-integrity-auditor verdict: HIGH
  proof-risk-auditor verdict: LOW
  A1 auditors verdict: LOW
aggregate verdict: LOW
```

Expected operator verdict: `HIGH`.

Expected finding-id namespace: `ACR254-WW-008`.

Rationale: Aggregation must preserve worst-case severity and `NEEDS_INPUT` or `BLOCKED`; a non-LOW ACR-254 child cannot be hidden by LOW siblings.

## Positive Wiring Case

A LOW wiring result requires all of the following:

- Phase 3 proposal template requires `## Proof plan`.
- Phase 4 has an independent `gate_name=proof-risk` row.
- Code-quality dispatch manifest includes validation-integrity and proof-risk rows with applicability inputs, durable prompt/log/report paths, and written non-applicability reasons only when the context is genuinely absent.
- Phase 8 dispatches code-quality against the actual PR diff and writes `gate_name=code-quality`.
- RCA orchestrator writes investigator, fix-decision, and verification critic artifacts.
- Code-quality convention names the active operators and eval specs without turning the convention into the enforcement mechanism.

## Lifecycle Notes

Lifecycle is `WRITE`: this file defines Step 6c acceptance behavior for workflow and convention wiring. Runnable detector code, fixture files, CLI integration, and enforcement-state transitions are out of scope for this WU.

