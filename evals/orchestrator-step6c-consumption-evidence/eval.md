---
eval_id: orchestrator-step6c-consumption-evidence
behavior_class: ACR-247 side-file Step 6c consumption evidence
lifecycle_state: WRITE
severity_when_fires: HIGH
evidence_source_kinds:
  - agents-trace-json
  - expected-process-manifest
  - step6c-side-file
  - step6b-output-index
  - process-tree-audit
  - dispatch-prompt
  - audit-bundle
suggested_action_class: revise_phase6_consumption_evidence
---

# ACR-247 Orchestrator Step 6c Consumption Evidence

## Purpose

This WRITE-state behavior specification defines the ACR-247 side-file proof model for Phase 6 Step 6c consumption evidence. The runnable sibling `eval.py` and fixtures exercise the same behavior contract locally.

The eval verifies that Step 6c consumption evidence is enforceable without relying on the model agent under audit to reproduce or attest the proof rows. The load-bearing carrier is the expected-process manifest entry produced by the orchestrator/helper before Step 6c dispatch, plus the manifest-declared side-file projected from the current Step 6b output index.

## Lifecycle State

WRITE.

Per `~/ai/conventions/evals.md`, this file remains the behavior contract. The sibling runner is allowed in this directory and is used by ACR-247 Step 6c to prove the side-file projection and Audit #2 predicates.

## Inputs

The runnable eval or a future detector consumes these canonical inputs by semantic role:

- Phase 6 expected-process manifest with `side_channel_evidence_bundle:`.
- Manifest-declared Step 6c side-file path.
- Step 6b output-index path.
- Recursive `level_id` scope from the expected-process manifest.
- Step 6c invocation UUID, prompt path, log path, and invocation start time for topology and dispatch-time ordering.
- Projection helper identity `~/ai/workflows/step6c-consumption-side-file.md`.

Optional companion evidence may include the Phase 6 process-tree report, Step 6b prompt/log, Step 6c prompt, and saved `agents trace --json` evidence. The detector joins evidence by invocation UUID, parent invocation ID, prompt path, log path, side-file path, source-index path, and level scope when those fields are available.

## Expected Proof Model

For ACR-247 side-channel runs, the orchestrator calls:

```bash
step6c-consumption-side-file project --index <step6b-output-index> --out <side-file> --level-id <level-id> [--expected-process <manifest-path>]
```

before dispatching Step 6c. The helper projects the current Step 6b output index into canonical side-file rows:

- `consumed: <absolute-step6b-output-index-path>`
- `consumed: <absolute-step6b-output-path-or-level-scoped-id>` for every Step 6b output-index row Step 6c implements.

The side-file is load-bearing only when the expected-process manifest names it and pins the source index, source hash, side-file hash, row count, projection helper identity, `level_id`, `projected_at`, and Step 6c topology fields. Audit #2 re-projects the current index and byte-compares the result to the manifest-declared side-file.

The Step 6c log may contain `consumed:` rows, `CONSUMED_EVIDENCE_EMITTED`, read confirmations, or narrative claims. Those model-authored tokens are informational only. They cannot satisfy a missing side-file, repair stale projection evidence, replace the manifest, or prove currentness.

## Behavior Cases

### Case 1 - Positive current side-file bundle

**Name.** Positive - valid manifest-declared side-file evidence.

**Fixture source.** `fixtures/happy-path/`.

**Expected eval signal.** `pass`.

**Reasoning.** A current source index, matching side-file hash, byte-stable re-projection, correct row count, correct scope, and `projected_at` before Step 6c start prove that consumption evidence existed before dispatch.

### Case 2 - Negative tampered side-file

**Name.** Negative - post-projection side-file mutation.

**Fixture source.** `fixtures/tampered-side-file/`.

**Expected eval signal.** `block-side-file-sha-mismatch`.

**Reasoning.** The manifest hash must match the current side-file bytes. A side-file changed after projection is not reliable audit evidence.

### Case 3 - Negative missing side-file

**Name.** Negative - manifest-declared side-file missing.

**Fixture source.** `fixtures/missing-side-file/`.

**Expected eval signal.** `block-side-file-missing`.

**Reasoning.** Audit #2 must stat the manifest-declared side-file and block when it is absent rather than falling back to model narrative.

### Case 4 - Negative stale source index

**Name.** Negative - source Step 6b output index changed after projection.

**Fixture source.** `fixtures/stale-source-index/`.

**Expected eval signal.** `block-source-index-sha-mismatch`.

**Reasoning.** The side-file proves consumption of the index bytes it was projected from. If the current source index hash differs, the evidence is stale.

### Case 5 - Negative row mismatch

**Name.** Negative - side-file row differs from deterministic re-projection.

**Fixture source.** `fixtures/row-mismatch/`.

**Expected eval signal.** `block-reprojection-mismatch`.

**Reasoning.** Row count alone is insufficient; the side-file bytes must match fresh projection from the current Step 6b output index.

### Case 6 - Negative wrong level scope

**Name.** Negative - parent rows supplied under child `level_id`.

**Fixture source.** `fixtures/wrong-scope/`.

**Expected eval signal.** `block-level-scope-mismatch`.

**Reasoning.** Recursive Phase 6 rows must be scoped to the manifest `level_id` when the index uses string artifact identifiers; parent and child evidence cannot substitute for each other.

### Case 7 - Negative model attestation only

**Name.** Negative - model-authored proof tokens without valid side-file.

**Fixture source.** `fixtures/model-attestation-only-fail/`.

**Expected eval signal.** `block-side-file-missing`.

**Reasoning.** A Step 6c log full of model-authored `consumed:` rows or read confirmations cannot satisfy Audit #2 when the manifest side-file is missing.

### Case 8 - Negative late projection

**Name.** Negative - side-file projected after Step 6c start.

**Fixture source.** `fixtures/dispatch-time-too-late/`.

**Expected eval signal.** `block-dispatch-time-ordering`.

**Reasoning.** The side-file must exist before Step 6c dispatch. Projection after invocation start cannot prove pre-code-change consumption evidence.

### Case 9 - Prompt contract

**Name.** Positive/negative - Step 6c prompts may pass side-file context but must not require model-authored load-bearing proof.

**Fixture source.** `fixtures/prompt-contract/`.

**Expected eval signal.** `pass-if-prompt-clean | block-if-prompt-requests-load-bearing-attestation`.

**Reasoning.** The prompt may point at the Step 6b output index and side-file. It must not make `consumed:` echoes, read confirmations, or model attestations the audit authority.

### Case 10 - Direct dispatch hygiene

**Name.** Positive/negative - direct `agents ... 2>&1 | tee` dispatch preserved.

**Fixture source.** `fixtures/direct-dispatch-hygiene/`.

**Expected eval signal.** `pass-if-dispatch-shape-clean | block-if-wrapper-or-shell-fanout-or-truncating-filter`.

**Reasoning.** ACR-247 uses a pre-dispatch helper and does not introduce an `agents-with-evidence` wrapper, heredoc, shell fanout, or truncating filter in the Step 6c command.

### Case 11 - Convention rule present

**Name.** Positive - load-bearing audit evidence authorship convention present.

**Fixture source.** `fixtures/convention-rule-present/`.

**Expected eval signal.** `pass-if-convention-rule-present`.

**Reasoning.** The convention must state that load-bearing audit evidence is produced outside the audited model response and verified from the orchestrator/runner-authored artifact.

## Terminal Verdict Tokens

An automated detector aligned with this WRITE-state eval may emit exactly these terminal verdict tokens:

- `LOW`
- `MEDIUM`
- `HIGH`
- `NEEDS_INPUT:<absolute_artifact_path>`
- `BLOCKED:<reason>`

`LOW`, `MEDIUM`, and `HIGH` are eval finding severities. `NEEDS_INPUT:<absolute_artifact_path>` is reserved for cases where a current exception or question artifact is required before downstream consumption. `BLOCKED:<reason>` is reserved for cases where the detector cannot honestly classify the evidence bundle or a downstream gate must stop before accepting firstness or consumption-evidence claims.

## Out Of Scope / Anti-Scope

- No Rust runner changes.
- No `agents` CLI flag, stdout prepend flag, or wrapper command.
- No pytest placement, CI scheduler wiring, or `tests/test_*.py` production test.
- No permanent acceptance of unmanifested historical bridge files.
- No broad changes to unrelated first-line, report-first-line, final-stdout, `WROTE:`, or line-anchor operator contracts.
- No product-code edits outside the ACR-247 supported `~/ai` workflow, operator, convention, and eval surfaces.

## Cross-References

- Step 6a contract: `/home/nes/projects/agent-runner/planning/acr-247-runtime-consumed-side-channel/contracts/acr-247-runtime-consumed-side-channel.md`
- Approved proposal: `/home/nes/projects/agent-runner/planning/acr-247-runtime-consumed-side-channel/proposals/acr-247-ACR-247.md`
- Problem map: `/home/nes/projects/agent-runner/planning/acr-247-runtime-consumed-side-channel/research/acr-247-problem-map.md`
- Projection workflow: `~/ai/workflows/step6c-consumption-side-file.md`
- Eval convention: `~/ai/conventions/evals.md`
