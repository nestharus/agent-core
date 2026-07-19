---
id: validation-integrity-auditor
slug: validation-integrity-auditor
lifecycle: WRITE
lifecycle_state: WRITE
operator_under_test: agents/validation-integrity-auditor.md
created: 2026-05-18
risk_class: HIGH
scope: ACR-254 validation-surface weakening detection for PR diffs and RCA dossier verification
behavior_class: Validation integrity, ratification, and runtime-artifact evidence matching
severity_when_fires: HIGH
evidence_source_kinds:
  - pr-diff
  - rca-dossier-diff
  - runtime-claim
  - decisions-record
  - runtime-artifact-evidence
suggested_action_class: revise-fix-or-supply-ratification-plus-runtime-artifact-proof
supersedes: []
---

# Validation Integrity Auditor Eval

## Purpose

This WRITE-state eval specification defines the required behavior contract for `agents/validation-integrity-auditor.md`. The future operator must detect when a PR diff or RCA dossier diff makes a validation surface easier to pass while the runtime claim says the underlying runtime behavior was fixed. It must also preserve the only allowed exception: explicit DECISIONS ratification plus independent runtime-artifact validation evidence.

The spec is not executable test code. Each fixture is a deterministic synthetic artifact fragment that a future eval runner can present to the operator or use to judge an operator report.

## Operator Under Test

`agents/validation-integrity-auditor.md` is a read-only critic with two modes:

- `pr-diff`: reads a PR diff and runtime claim.
- `rca-dossier`: reads an RCA dossier verification diff and runtime claim.

The operator writes only the caller-supplied report path and emits a terminal verdict from `LOW`, `MEDIUM`, `HIGH`, `NEEDS_INPUT:<absolute_artifact_path>`, or `BLOCKED:<reason>`.

## Finding Contract

Every finding produced by the future detector must preserve the eval convention minimum fields:

- `eval_id`
- `severity`
- `evidence_paths`
- `summary`
- `suggested_action`
- `confidence`

Validation-integrity findings also carry:

- `finding_ids`: `VI-<NNN>` report-local IDs, optionally `VI-<wu>-<NNN>` in report text.
- `pattern_id`: one of `VI-001` through `VI-007`, or `ratification`.
- `runtime_claim_ref`
- `diff_hunk_ref`
- `validation_surface_change`
- `ratification_status`
- `runtime_artifact_evidence_ref`
- `expected_terminal_verdict`

## Required Trace Fields

- `mode`
- `diff_path` or `dossier_diff_path`
- `runtime_claim`
- `report_path`
- `worktree_path`
- optional `decisions_path`
- optional `runtime_artifact_evidence_path`
- optional `wu_id`

Missing required inputs must produce `BLOCKED:<reason>`. Missing optional evidence that is needed for ratification keeps the original non-LOW verdict.

## Scenarios

### VIA-001: removed assertion for runtime repair claim

Fixture: Synthetic PR diff fragment removes a behavior check from a runtime validation test:

```text
runtime_claim: "The updater container now starts with the cryptography dependency available."
diff:
  - check: updater runtime imports cryptography from the built container
  - behavior check: dependency is available inside the updater runtime
  + check: updater command exits without raising
decisions_path: absent
runtime_artifact_evidence_path: absent
```

Expected operator verdict: `HIGH`.

Expected finding-id namespace: `VI-001`.

Rationale: Removing a previously asserted runtime condition is validation weakening. The runtime claim is artifact-bound, and neither ratification nor runtime-artifact proof is present.

### VIA-002: runtime-condition pytest skip

Fixture: Synthetic PR diff fragment adds a skip gate for a runtime dependency condition:

```text
runtime_claim: "The service image includes libcrypto at startup."
diff:
  + skip when "libcrypto is unavailable in this environment"
  + reason text: "runtime image dependency missing on CI"
decisions_path: absent
runtime_artifact_evidence_path: absent
```

Expected operator verdict: `HIGH`.

Expected finding-id namespace: `VI-002`.

Rationale: A skip added for a runtime dependency makes the validation gate avoid the condition the fix claims to repair.

### VIA-003: unittest skipIf for runtime service

Fixture: Synthetic PR diff fragment adds conditional skip logic:

```text
runtime_claim: "Production service startup succeeds when the cache sidecar is reachable."
diff:
  + skipIf cache sidecar is not reachable from test host
  + reason: "cache is optional in local test environment"
decisions_path: absent
runtime_artifact_evidence_path: absent
```

Expected operator verdict: `HIGH`.

Expected finding-id namespace: `VI-003`.

Rationale: Conditional skip for a runtime service dependency is validation weakening for a production-runtime claim.

### VIA-004: mock substitution for previously real dependency

Fixture: Synthetic PR diff fragment replaces a real dependency exercise with a mock path:

```text
runtime_claim: "The worker reaches the real payment gateway adapter with signed requests."
diff:
  - use real gateway adapter in integration validation
  + use mock gateway adapter returning signed=True
decisions_path: absent
runtime_artifact_evidence_path: absent
```

Expected operator verdict: `HIGH`.

Expected finding-id namespace: `VI-004`.

Rationale: The changed validation proves only the mock path while the claim is about the runtime adapter.

### VIA-005: fixture-to-stub replacement

Fixture: Synthetic PR diff fragment replaces a runtime fixture with a local sentinel:

```text
runtime_claim: "The migration runner applies the production schema to the real database endpoint."
diff:
  - database fixture provisions a real migration target
  + database fixture returns "stub-db-ok"
decisions_path: absent
runtime_artifact_evidence_path: absent
```

Expected operator verdict: `HIGH`.

Expected finding-id namespace: `VI-005`.

Rationale: A fixture that represented a runtime resource was replaced with a stub while the runtime claim stayed real-resource-bound.

### VIA-006: schema relaxation

Fixture: Synthetic PR diff fragment loosens a validator:

```text
runtime_claim: "The API still requires customer_id and validates it as a UUID in production requests."
diff:
  - schema field customer_id required=true format=uuid
  + schema field customer_id required=false format=any-string
decisions_path: absent
runtime_artifact_evidence_path: absent
```

Expected operator verdict: `MEDIUM`.

Expected finding-id namespace: `VI-006`.

Rationale: Schema relaxation weakens the validation surface. The contract classifies unratified schema relaxation as at least MEDIUM.

### VIA-007: test-environment-only validation for runtime artifact claim

Fixture: Synthetic PR diff and evidence fragment:

```text
mode: pr-diff
runtime_claim: "The container image imports module X at startup."
diff:
  + proof note: "import X passes in the test environment"
runtime_artifact_evidence_path: absent
decisions_path: absent
```

Expected operator verdict: `HIGH`.

Expected finding-id namespace: `VI-007`.

Rationale: A test-environment import cannot prove a container startup claim.

### VIA-008: ratified schema relaxation with runtime artifact evidence

Fixture: Synthetic PR diff plus DECISIONS and runtime artifact evidence:

```text
runtime_claim: "The API runtime accepts legacy payloads after a deliberate compatibility relaxation."
diff:
  - schema rejects legacy field alias
  + schema accepts legacy field alias
decisions snippet:
  ### ACR-254-demo - Validation-surface weakening ratification
  Ratifies the schema relaxation for legacy alias compatibility and cites this diff hunk.
runtime artifact evidence:
  /tmp/acr-254/evidence/container-api-legacy-payload.log
  content: built API image handles legacy payload through production request path
```

Expected operator verdict: `LOW`.

Expected finding-id namespace: `VI-001` with ratification status `ratified`.

Rationale: The pattern would fire as schema relaxation, but explicit ratification and runtime-artifact proof downgrade MEDIUM to LOW.

### VIA-009: ratification-only exception is not enough

Fixture: Synthetic PR diff plus DECISIONS but no runtime artifact:

```text
runtime_claim: "The updater runtime dependency is fixed in the built image."
diff:
  - behavior check: dependency available in built image
  + behavior check: dependency import skipped when unavailable
decisions snippet:
  ### ACR-254-demo - Validation-surface weakening ratification
  Ratifies the skip as temporary compatibility handling.
runtime_artifact_evidence_path: absent
```

Expected operator verdict: `HIGH`.

Expected finding-id namespace: `VI-001`.

Rationale: DECISIONS ratification without runtime-artifact evidence does not validate the runtime claim.

### VIA-010: runtime-artifact-only exception is not enough

Fixture: Synthetic PR diff plus runtime artifact but no DECISIONS ratification:

```text
runtime_claim: "The service image starts with the required native dependency."
diff:
  - behavior check: native dependency is imported during image startup
  + behavior check: startup path uses stub dependency when missing
runtime artifact evidence:
  /tmp/acr-254/evidence/service-container-start.log
  content: container starts successfully
decisions_path: absent
```

Expected operator verdict: `HIGH`.

Expected finding-id namespace: `VI-001`.

Rationale: Runtime-artifact evidence may support the fix, but unratified validation weakening remains a blocking integrity finding.

### VIA-011: tests-now-pass after validation changes is insufficient

Fixture: Synthetic RCA dossier verification fragment:

```text
mode: rca-dossier
runtime_claim: "The deployed updater no longer fails at runtime."
dossier diff:
  + verification: "tests now pass"
  + changed validation harness to skip missing dependency branch
runtime_artifact_evidence_path: absent
decisions_path: absent
```

Expected operator verdict: `HIGH`.

Expected finding-id namespace: `VI-001`.

Rationale: Green tests after changing skips, fixtures, mocks, schemas, or validation harnesses do not prove runtime repair.

### VIA-012: legitimate refactor with same runtime coverage

Fixture: Synthetic PR diff fragment renames a helper and preserves the same runtime validation:

```text
runtime_claim: "The updater container still verifies dependency availability during startup."
diff:
  - helper name: check_crypto_dependency
  + helper name: verify_crypto_dependency
  unchanged behavior: built updater image startup still validates dependency availability
decisions_path: absent
runtime_artifact_evidence_path: /tmp/acr-254/evidence/updater-container-start.log
```

Expected operator verdict: `LOW`.

Expected finding-id namespace: none.

Rationale: The validation surface was reorganized without removing the runtime condition or substituting proxy evidence.

### VIA-013: RCA verification critic blocks tests-only closure

Fixture: Synthetic RCA verification phase:

```text
mode: rca-dossier
runtime_claim: "Production task runner can connect to the real queue."
dossier diff:
  + verification cites only rerun unit results
  + queue fixture now returns sentinel "connected"
runtime_artifact_evidence_path: absent
decisions_path: absent
```

Expected operator verdict: `HIGH`.

Expected finding-id namespace: `VI-005`.

Rationale: RCA closure must be blocked when the verification phase changes a fixture to a stub and presents tests-only proof for a runtime claim.

### VIA-014: runtime and proxy evidence honestly scoped

Fixture: Synthetic PR diff and evidence:

```text
runtime_claim: "The worker container processes one production-path queue message."
diff:
  + validation note: unit proxy check covers formatting only
  + runtime validation note: built worker image consumed message from queue emulator via production command
runtime artifact evidence:
  /tmp/acr-254/evidence/worker-container-queue-run.log
decisions_path: absent
```

Expected operator verdict: `LOW`.

Expected finding-id namespace: none.

Rationale: Proxy evidence is scoped to proxy behavior and the runtime claim has separate runtime-artifact proof.

## Non-Fire Cases

- Pure naming, formatting, or helper extraction changes that preserve the same runtime condition.
- Proxy evidence used only for a proxy-layer claim.
- Runtime-artifact proof accompanying unchanged validation surfaces.

## Lifecycle Notes

Lifecycle is `WRITE`: this file defines the behavior contract before `agents/validation-integrity-auditor.md` exists. Runnable detector code, fixture files, CLI integration, and enforcement-state transitions are out of scope for this WU.

