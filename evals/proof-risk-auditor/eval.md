---
id: proof-risk-auditor
slug: proof-risk-auditor
lifecycle: WRITE
lifecycle_state: WRITE
operator_under_test: agents/proof-risk-auditor.md
created: 2026-05-18
risk_class: HIGH
scope: ACR-254 proof-plan evidence-class validation for proposals and RCA fix decisions
behavior_class: Runtime claim to proof method evidence-class matching
severity_when_fires: HIGH
evidence_source_kinds:
  - proposal
  - rca-fix-decision
  - proof-plan
  - runtime-claim
  - proof-method
suggested_action_class: revise-proof-plan-or-supply-runtime-artifact-proof
supersedes: []
---

# Proof Risk Auditor Eval

## Purpose

This WRITE-state eval specification defines the required behavior contract for `agents/proof-risk-auditor.md`. The future operator must judge whether a Phase 3 proposal or RCA fix-decision proof plan exercises the runtime claim directly, instead of accepting tests, mocks, stubs, fixture-only paths, relaxed schemas, or self-certification as proof for artifact-bound behavior.

The spec is not executable test code. Each fixture is a deterministic synthetic proposal or fix-decision fragment, and the expected verdict is the assertion surface.

## Operator Under Test

`agents/proof-risk-auditor.md` is a read-only critic with two modes:

- `phase-3-proposal`
- `rca-fix-decision`

The operator writes only the caller-supplied report path and emits a terminal verdict from `LOW`, `MEDIUM`, `HIGH`, `NEEDS_INPUT:<absolute_artifact_path>`, or `BLOCKED:<reason>`.

## Finding Contract

Every finding produced by the future detector must preserve the eval convention minimum fields:

- `eval_id`
- `severity`
- `evidence_paths`
- `summary`
- `suggested_action`
- `confidence`

Proof-risk findings also carry:

- `finding_ids`: `PR-<NNN>` report-local IDs.
- `runtime_claim`
- `proof_plan_ref`
- `proof_method`
- `proxy_class`
- `required_runtime_artifact`
- `evidence_refs`
- `expected_terminal_verdict`

## Required Trace Fields

- `mode`
- `proposal_path`
- `report_path`
- `worktree_path`

Missing required inputs must produce `BLOCKED:<reason>`.

## Scenarios

### PRA-001: missing proof plan for runtime behavior proposal

Fixture: Synthetic Phase 3 proposal fragment:

```text
mode: phase-3-proposal
proposal:
  # Runtime dependency fix
  The worker image will include the native dependency at startup.
  ## Implementation
  Add the dependency to the image build.
  ## Verification
  Run the existing tests.
```

Expected operator verdict: `HIGH`.

Expected finding-id namespace: `PR-001`.

Rationale: A proposal asserting runtime behavior must include `## Proof plan`.

### PRA-002: proof plan missing runtime claim

Fixture: Synthetic Phase 3 proposal fragment:

```text
mode: phase-3-proposal
proposal:
  ## Proof plan
  **Proof method**: Run container startup and smoke validation.
  **Evidence-class match**: The proof method uses runtime artifact evidence.
```

Expected operator verdict: `HIGH`.

Expected finding-id namespace: `PR-001`.

Rationale: The schema requires a runtime claim sentence so the proof method can be matched to it.

### PRA-003: proof plan missing proof method

Fixture: Synthetic Phase 3 proposal fragment:

```text
mode: phase-3-proposal
proposal:
  ## Proof plan
  **Runtime claim**: The API container accepts production-path login requests.
  **Evidence-class match**: Runtime artifact evidence is needed for this claim.
```

Expected operator verdict: `HIGH`.

Expected finding-id namespace: `PR-001`.

Rationale: Without a proof method, the proposal does not name what evidence will exercise the runtime claim.

### PRA-004: proof plan missing evidence-class match

Fixture: Synthetic Phase 3 proposal fragment:

```text
mode: phase-3-proposal
proposal:
  ## Proof plan
  **Runtime claim**: The migration applies cleanly to the production schema.
  **Proof method**: Run the migration command against a production-shaped database clone.
```

Expected operator verdict: `HIGH`.

Expected finding-id namespace: `PR-001`.

Rationale: The proof plan must explicitly state why the evidence class matches the claim.

### PRA-005: proxy-only proof for runtime-artifact-bound claim

Fixture: Synthetic Phase 3 proposal fragment:

```text
mode: phase-3-proposal
proposal:
  ## Proof plan
  **Runtime claim**: The container runtime imports module X during startup.
  **Proof method**: Confirm module X imports in the test environment.
  **Evidence-class match**: Tests pass, so the runtime is fixed.
```

Expected operator verdict: `HIGH`.

Expected finding-id namespace: `PR-001`.

Rationale: Test-environment import proof is proxy-only for a container startup claim.

### PRA-006: proxy-only proof for genuine proxy-layer claim

Fixture: Synthetic Phase 3 proposal fragment:

```text
mode: phase-3-proposal
proposal:
  ## Proof plan
  **Runtime claim**: The test harness marks missing optional local services as skipped with a clear local-only reason.
  **Proof method**: Exercise the test-harness skip path in the test environment.
  **Evidence-class match**: The claim is about test-harness behavior, so test-environment evidence directly exercises the claimed layer.
```

Expected operator verdict: `LOW`.

Expected finding-id namespace: none.

Rationale: Proxy evidence is valid when the claim is genuinely about the proxy layer.

### PRA-007: direct runtime-artifact proof matches claim

Fixture: Synthetic Phase 3 proposal fragment:

```text
mode: phase-3-proposal
proposal:
  ## Proof plan
  **Runtime claim**: The built updater container starts and imports cryptography before running the update command.
  **Proof method**: Build the updater image, run the production entrypoint, and capture the container exec log showing the import and command success.
  **Evidence-class match**: The claim is about the built runtime container, and the proof method executes that same artifact and entrypoint.
```

Expected operator verdict: `LOW`.

Expected finding-id namespace: none.

Rationale: The proof method directly exercises the artifact named by the runtime claim.

### PRA-008: self-certification masquerades as proof

Fixture: Synthetic Phase 3 proposal fragment:

```text
mode: phase-3-proposal
proposal:
  ## Proof plan
  **Runtime claim**: The deployed job runner no longer crashes when loading native dependency Y.
  **Proof method**: The proof plan itself is the validation; no separate evidence is needed.
  **Evidence-class match**: The implementation is straightforward and tests pass.
```

Expected operator verdict: `HIGH`.

Expected finding-id namespace: `PR-001`.

Rationale: A proposal cannot certify its own proof without naming a validation surface.

### PRA-009: RCA fix-decision missing proof plan

Fixture: Synthetic RCA fix-decision fragment:

```text
mode: rca-fix-decision
fix decision:
  # Fix decision
  Patch the image build so the runtime dependency is installed.
  Verification will happen later.
```

Expected operator verdict: `HIGH`.

Expected finding-id namespace: `PR-001`.

Rationale: RCA fix decisions require the same proof-plan shape before application planning can proceed.

### PRA-010: RCA fix-decision proxy-only proof

Fixture: Synthetic RCA fix-decision fragment:

```text
mode: rca-fix-decision
fix decision:
  ## Proof plan
  **Runtime claim**: The production updater container no longer fails on cryptography import.
  **Proof method**: Run a host-environment import check and rerun unit validations.
  **Evidence-class match**: The host import check covers the dependency.
```

Expected operator verdict: `HIGH`.

Expected finding-id namespace: `PR-001`.

Rationale: Host-environment import and unit validation do not prove production container behavior.

### PRA-011: mixed proxy and runtime proof with explicit class match

Fixture: Synthetic Phase 3 proposal fragment:

```text
mode: phase-3-proposal
proposal:
  ## Proof plan
  **Runtime claim**: The API runtime applies the new request validator in the production entrypoint.
  **Proof method**: Run validator unit checks for edge cases, then build the API image and send a production-path request through the running container.
  **Evidence-class match**: Unit checks cover validator logic only; the runtime claim is matched by the built-image production-path request evidence.
```

Expected operator verdict: `LOW`.

Expected finding-id namespace: none.

Rationale: Proxy evidence is explicitly scoped and the runtime claim receives matching runtime-artifact proof.

## Non-Fire Cases

- Proof plans for non-runtime claims that use the same non-runtime evidence class.
- Mixed proof plans where proxy evidence is scoped and runtime claims receive matching runtime-artifact evidence.
- Proposals that name runtime claim, proof method, and evidence-class match with coherent artifact binding.

## Lifecycle Notes

Lifecycle is `WRITE`: this file defines the behavior contract before `agents/proof-risk-auditor.md` exists. Runnable detector code, fixture files, CLI integration, and enforcement-state transitions are out of scope for this WU.

