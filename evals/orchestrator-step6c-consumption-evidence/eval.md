---
eval_id: orchestrator-step6c-consumption-evidence
behavior_class: ACR-206 relaxed-position Step 6c consumption evidence
lifecycle_state: WRITE
severity_when_fires: HIGH
evidence_source_kinds:
  - agents-trace-json
  - step6c-log
  - step6b-output-index
  - process-tree-audit
  - dispatch-prompt
  - audit-bundle
suggested_action_class: revise_phase6_consumption_evidence
---

# ACR-206 Orchestrator Step 6c Consumption Evidence

## Purpose

This is a WRITE-state Markdown behavior specification for ACR-206. It is not runnable detector code.

The eval's purpose is to verify that the orchestrator's Phase 6 Step 6c consumption-evidence contract is enforceable by every agent in the current `agents` runner pool under the relaxed-position rule. The rule preserves runner-owned envelope lines while requiring Step 6c to prove, in its captured log, that it consumed the Step 6b output index and each Step 6b output row it implements.

## Lifecycle state

WRITE.

Per `~/ai/conventions/evals.md`, this file defines the behavior contract for a future detector shaped as `trace -> finding | None`. Runnable detector code, fixtures, adapters, CLI wiring, and enforcement rollout are deferred.

## Inputs

A future eval runner or detector consumes these canonical inputs by semantic role:

- Step 6c log file path.
- Step 6b output-index path.
- ACR-206 Step 6a contract path.
- ACR-206 approved proposal path.
- Recursive `level_id` scope from the calling expected-process manifest, when the evaluated Step 6c belongs to recursive Phase 6 work.

Optional companion evidence may include the Phase 6 expected-process manifest, process-tree-auditor report, Step 6b prompt/log, Step 6c prompt, and saved `agents trace --json` evidence. The detector must join evidence by invocation UUID, parent invocation ID, prompt path, log path, and level scope when those fields are available.

## Expected agent behavior

Under ACR-206's relaxed-position rule, the Step 6c agent must emit canonical consumption rows in the Step 6c captured log:

- `consumed: <absolute-step6b-output-index-path>`
- `consumed: <absolute-step6b-output-path-or-level-scoped-id>` for every Step 6b output-index row that Step 6c implements.

The `consumed:` rows may appear anywhere after runner-owned envelope lines such as `OULIPOLY_INVOCATION` and `OULIPOLY_SESSION`. The eval must preserve the runner envelope as valid trace and join evidence. It must not impose a first-non-empty-line constraint and must not require provider-authored text to precede runner-owned stderr markers in the merged `2>&1 | tee` log.

For recursive Phase 6, the detector must evaluate consumption evidence inside the recursive child scope supplied by the expected-process manifest. Child-level rows must include the matching `level_id` or scoped artifact identifier, using `<level_id>:<local_artifact_id>` where the Step 6b output index uses string artifact identifiers. Parent-level rows do not satisfy child-level consumption evidence, and child rows cannot satisfy parent scope unless the expected-process manifest explicitly maps that scope.

Evidence is invalid when it is missing, malformed, contradicted by the Step 6b output index, stale or unmapped, scoped to the wrong child level, or supplied only through a historical bridge file without a current exception artifact.

## Behavior cases

### Case 1 - Positive valid relaxed-position consumption evidence

**Name.** Positive - valid relaxed-position consumption evidence.

**Fixture source.** AGE-93-style log ordering from the duplicates inventory plus ACR-154 minimal `consumed:` rows converted into Step 6c log rows, not a sentinel file.

**Expected eval signal.** No finding.

**Reasoning.** This case proves the contract is enforceable without first-line control: runner-owned `OULIPOLY_INVOCATION` and `OULIPOLY_SESSION` may lead the merged log, and later canonical `consumed:` rows still prove Step 6c read the Step 6b output index and implemented Step 6b outputs.

**Residual risk.** The WRITE-state seed cannot prove a future detector adapter parses every real log layout correctly.

### Case 2 - Negative missing consumption evidence

**Name.** Negative - consumption evidence missing.

**Fixture source.** AGE-93 two-run zero-`consumed:` precedent and ACR-149 documented missing-log-echo residual.

**Expected eval signal.** HIGH finding.

**Reasoning.** This case proves Process-tree audit #2 must not allow Phase 6 to continue when Step 6b and Step 6c artifacts exist but the Step 6c log contains no matching `consumed:` rows.

**Residual risk.** Missing evidence proves only that the audit contract was not satisfied; it cannot prove the agent did or did not read the files privately.

### Case 3 - Negative malformed consumption evidence

**Name.** Negative - consumption evidence malformed.

**Fixture source.** Duplicate-inventory alternate-token examples from ACR-88, NES-270, and other bridge variants, including `READ:`, `CONSUMED_FROM_STEP6B`, and `PHASE6C_CONSUMING_STEP6B_OUTPUTS:`.

**Expected eval signal.** HIGH finding.

**Reasoning.** This case proves the replacement contract is a small canonical grammar, not a vague attestation. Non-canonical tokens, truncated `consumed` rows, relative paths where absolute paths are required, and omitted recursive scope are not auditable evidence.

**Residual risk.** A future detector still needs careful grammar boundaries to avoid false positives on explanatory prose that mentions bad tokens.

### Case 4 - Negative unmapped Step 6b output reference

**Name.** Negative - evidence references a Step 6b output the index does not contain.

**Fixture source.** ACR-154/ACR-198 minimal rows with one `consumed:` path mutated away from the Step 6b output-index row.

**Expected eval signal.** HIGH finding.

**Reasoning.** This case proves the eval checks correspondence, not just token presence. A Step 6c log row naming an unrelated, stale, or absent path cannot prove consumption of the Step 6b output that Step 6c implemented.

**Residual risk.** Future runnable code must parse the Step 6b output index by semantic columns, not by one brittle Markdown table layout.

### Case 5 - Recursive Phase 6 level_id scoping

**Name.** Recursive Phase 6 - child-level `<level_id>:<local_artifact_id>` scoping.

**Fixture source.** Implementation-pipeline recursive Phase 6 contract plus NES-270 recursion-control attestation as historical fixture context, rewritten to ACR-206 `consumed:` grammar.

**Expected eval signal.** No finding when scoped correctly; HIGH finding when scope is missing or wrong.

**Reasoning.** This case proves parent and child Step 6b outputs cannot collide. The detector must accept rows scoped to the child `level_id` and reject unscoped rows, parent-level substitutions, or rows mapped to the wrong child expected-process manifest.

**Residual risk.** Recursive fixture construction is likely to need future runnable fixtures to exercise nested trace joins across real child invocations.

### Case 6 - Negative bridge substitute after ACR-206

**Name.** Negative - bridge file used as permanent substitute after ACR-206.

**Fixture source.** ACR-154/ACR-198 minimal bridge files and the ACR-149 accepted bridge report.

**Expected eval signal.** HIGH finding, or no finding only when an explicit current exception artifact exists.

**Reasoning.** This case proves the synthetic bridge family is historical evidence, not the future standard path. A future WU cannot satisfy Step 6c consumption solely with `step6c-consumed-evidence.md` when the Step 6c log lacks valid relaxed-position `consumed:` rows, unless a current `NEEDS_INPUT` or residual decision explicitly authorizes a one-off exception before downstream consumption.

**Residual risk.** The eval must distinguish future-WU misuse from read-only review of completed historical planning artifacts.

### Case 7 - Positive runner envelope preservation

**Name.** Positive - runner envelope preservation.

**Fixture source.** `agents-cli-dispatch-hygiene` eval marker-class notes plus ACR-206 lifecycle-map ordering.

**Expected eval signal.** No finding.

**Reasoning.** This case proves ACR-206 does not weaken trace integrity. `OULIPOLY_INVOCATION` and `OULIPOLY_SESSION` may precede provider-authored consumption rows, and their presence must not be flagged as bad evidence.

**Residual risk.** This eval does not test Rust marker emission or runner ordering; it only specifies how Step 6c evidence consumers interpret those marker lines.

### Case 8 - PR-review Test Audit consumer

**Name.** Positive/Negative - PR-review Test Audit consumer.

**Fixture source.** Phase 6 process-tree report plus Step 6c log bundle variants with valid, missing, and contradicted relaxed-position `consumed:` rows, derived from the supported-surface PR-review contract and Process-tree audit #2 companion-evidence shape.

**Expected eval signal.** No finding for valid new-style evidence; BLOCKED when evidence is missing or contradicted before PR-review accepts tests as intent-first.

**Reasoning.** This case proves downstream consumers move with the producer contract. PR-review Test Audit may accept intent-first tests only when the Phase 6 process-tree report and Step 6c log bundle show valid relaxed-position evidence tied to the Step 6b output index and implemented Step 6b outputs.

**Residual risk.** PR review still depends on reviewer judgment for evidence relevance beyond mechanical presence, correspondence, and contradiction checks.

### Case 9 - Positive declared-roles override

**Name.** Positive - declared-roles override.

**Fixture source.** The orchestrator file-local `## Declared roles` section with `orchestration`, `parser`, and `validator`.

**Expected eval signal.** LOW.

**Reasoning.** This case proves the cohesion-auditor subset check uses the file-local override for `/home/nes/ai/agents/implementation-pipeline-orchestrator.md` instead of the path default. Step 6c's Process-tree audit composition, violation detection, and gate evaluation are validator work, and `orchestration, parser, validator` covers that work under `~/ai/conventions/code-quality.md` `## Declared roles`.

**Residual risk.** If a future WU adds work outside `orchestration`, `parser`, and `validator`, that WU must re-evaluate declared roles instead of relying on this ACR-206 case.

## Terminal verdict tokens

An automated detector aligned with this WRITE-state eval may emit exactly these terminal verdict tokens:

- `LOW`
- `MEDIUM`
- `HIGH`
- `NEEDS_INPUT:<absolute_artifact_path>`
- `BLOCKED:<reason>`

`LOW`, `MEDIUM`, and `HIGH` are eval finding severities. `NEEDS_INPUT:<absolute_artifact_path>` is reserved for cases where a current exception or question artifact is required before downstream consumption. `BLOCKED:<reason>` is reserved for cases where the detector cannot honestly classify the evidence bundle or a downstream gate must stop before accepting intent-first or consumption-evidence claims.

## Out of scope / anti-scope

- No runnable detector code, Python scrapers, pytest revival, structural Markdown tests, fixtures, CLI integration, scheduler, or CI wiring.
- No Rust runner changes to `agent-runner/trunk/src-tauri/src/main.rs` or `crates/oulipoly-state/src/db.rs`.
- No `agents-cli.md` dispatch-shape changes and no weakening of `2>&1 | tee` marker capture.
- No deletion or modification of historical synthetic-bridge files in planning directories.
- No permanent acceptance of `step6c-consumed-evidence.md` bridge files as the normal future path after ACR-206.
- No broad changes to unrelated first-line, report-first-line, final-stdout, `WROTE:`, or line-anchor operator contracts.
- No product-code edits to the implementation-pipeline orchestrator, workflow doc, process-tree-auditor, workflow-execution-violations convention, PR-review workflow, or `DECISIONS.md` from this eval seed.

## Cross-references

- Approved proposal: `/home/nes/projects/ai/planning/acr-206-firstline-unenforceable/proposals/acr-206-ACR-206.md`
- Problem map: `/home/nes/projects/ai/planning/acr-206-firstline-unenforceable/research/acr-206-problem-map.md`
- Risk profile: `/home/nes/projects/ai/planning/acr-206-firstline-unenforceable/risk/acr-206-risk-profile.md`
- Step 6a contract: `/home/nes/projects/ai/planning/acr-206-firstline-unenforceable/contracts/acr-206-firstline-unenforceable.md`
- Eval convention: `/home/nes/ai/conventions/evals.md`
- Intrinsic-surface convention: `/home/nes/ai/conventions/code-quality.md` `## Intrinsic-surface declarations`
- Declared-roles convention: `/home/nes/ai/conventions/code-quality.md` `## Declared roles`
- Closest WRITE-state precedent: `/home/nes/ai/evals/agents-cli-dispatch-hygiene/eval.md`
