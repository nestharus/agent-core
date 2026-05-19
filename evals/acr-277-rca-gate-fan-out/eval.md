---
id: acr-277-rca-gate-fan-out
slug: acr-277-rca-gate-fan-out
eval_id: acr-277-rca-gate-fan-out
lifecycle: WRITE
lifecycle_state: WRITE
class: structural-verification
behavior_class: rca-orchestrator-post-apply-gate-fan-out
created: 2026-05-19
owner: ACR-292
ticket: ACR-292
ticket_mapping:
  - ACR-292
severity_when_fires: HIGH
evidence_source_kinds:
  - agents-trace-json
  - planning-directory-artifacts
  - process-tree-auditor-report
  - join-manifest
  - aggregate-code-quality-report
  - pr-review-gate-reports
  - audit-history-decisions-record
suggested_action_class: route-rca-post-apply-through-shared-apply-gate-set-operator
description: Structural verification for ACR-277 RCA post-apply apply-gate-set fan-out, superseding inherited prototype scenarios with stricter RCA-mode detectors.
---

# ACR-277 RCA Gate Fan-Out Eval

## Purpose

This WRITE-state structural-verification eval specifies the RCA caller boundary for the shared `apply-gate-set` fan-out. It preserves the ACR-277 prototype scenarios and supersedes them with stricter `ACR277-RCA-*` observations that consume RCA-mode trace, manifest, audit-history, currentness, and gate-report evidence. It is a Markdown eval specification only; runnable detector work is downstream.

## Scope

This eval covers the RCA post-apply boundary after applied fix evidence is available and before any PR, push, close, tracker, post-mortem, runbook, or other downstream lifecycle handoff can consume the RCA output. It verifies that the shared `apply-gate-set` fan-out is represented by current process-tree evidence, PR-review gate evidence against the actual applied diff, composite code-quality evidence with runtime-claim transport, readiness rows, hotfix skip and bootstrap-exception rows, decomposition handling, audit-history/DECISIONS currentness, and RCA/implementation inventory equivalence.

ACR-287 overlap is resolved by Option A - Absorb. The RCA caller-boundary discharge in `evals/acr-287-rca-post-apply-gate-set/eval.md` is treated as predecessor supersession evidence; the scenarios below are the strictly stronger successor detectors for the same inherited prototype rows.

Out of scope: editing `agents/apply-gate-set.md`, `workflows/apply-gate-set.md`, RCA caller files, implementation-pipeline caller files, workflow indexes, runnable detector code, pytest files, verifier scripts, currentness-invalidation algorithms owned by ACR-294, and topology-mode selection algorithms owned by ACR-295.

## Evidence Rules

Evidence is the resolved `agents trace --json` bundle for one RCA cycle plus planning-directory artifacts produced or consumed by the shared gate-set surface. A future detector may consume saved traces, prompt files, agent logs, process-tree expected-process manifests and reports, join manifests, aggregate code-quality reports, PR-review gate reports, readiness records, audit-history records, and DECISIONS entries.

Evidence joins across child invocations by root invocation UUID, parent invocation UUID, child invocation UUID, prompt file path, canonical artifact path, currentness identity, and report hashes. Missing evidence is not a non-fire condition unless the scenario explicitly allows a current non-applicability, skip-with-followup, stale-refusal, split, or ratified exception row.

## Required trace fields

- `wu_id`, `failure_id`, RCA cycle id, caller mode, root invocation UUID, and active manager/session identity.
- Current `base_ref`, `head_sha`, applied diff hash/path, scope reference/hash, runtime-claim reference/hash, and currentness identity keys.
- Child invocation UUIDs and prompt paths for `apply-gate-set`, PR-review gates, composite code-quality, readiness gates, decomposition review, and process-tree audit.
- Canonical RCA artifacts: root-cause record, fix-decision record, application plan, applied artifact, original-signal verification, verification-critic report, and downstream handoff artifacts.
- Gate artifacts: join manifest, dispatch manifest, aggregate report, process-tree expected-process manifest/report, PR-review reports, code-quality aggregate/findings, readiness rows, skip rows, exception rows, inventory-resolution rows, stale-refusal rows, and audit-history records.
- Per-row manifest fields: `gate_name`, `caller_mode`, `cycle_id`, `producing_invocation_uuid`, `canonical_output_path`, `size`, `mtime`, `sha256`, `verdict_line`, `verified_at`, `currentness_key`, `repair_route`, and `blocking_status`.

## Finding schema

Every future finding from this spec preserves the minimum fields from `~/ai/conventions/evals.md` section Finding schema:

- `eval_id`
- `severity`
- `evidence_paths`
- `summary`
- `suggested_action`
- `confidence`

ACR-277 RCA findings also carry:

- `scenario_id`: one of `ACR277-RCA-001` through `ACR277-RCA-011`.
- `wu_id`
- `root_invocation_uuid`
- `phase`
- `gate`
- `report_paths`
- `trace_locator`: invocation UUIDs, prompt paths, and artifact paths for the evidence subtree.

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

The ACR-287 eval at `evals/acr-287-rca-post-apply-gate-set/eval.md` is the absorbed RCA caller-boundary predecessor. These ACR-292 scenarios retain independent `eval_id`, `scenario_id`, positive evidence, non-fire cases, and suggested actions, and are therefore stricter successor detectors.

## Drift inheritance

- ACR-285 - Proof-risk row drift between workflow doc and orchestrator doc. Disposition: dual-score. Both proof-risk rows must remain present in the join manifest and both verdicts must be emitted unless an inventory-resolution row records source row, fold target, rationale, and equivalent blocking semantics.
- ACR-286 - Supported-surface row drift around PR-review/Phase 8. Disposition: dual-score. Both supported-surface rows must remain present in the join manifest and both verdicts must be emitted unless an inventory-resolution row records source row, fold target, rationale, and equivalent blocking semantics.

## Scenarios

### ACR277-RCA-001: Process-tree topology evidence covers the post-apply gate subtree

Scenario id: `ACR277-RCA-001`

Intended observation: RCA post-apply handoff must consume current process-tree/topology-mode evidence for the shared `apply-gate-set` subtree, including the expected-process manifest for the gate fan-out that was actually run.

Gate this scenario covers: `process-tree-audit`, `expected-process`, `topology-mode-evidence`.

Evidence fields: RCA cycle id, root invocation UUID, `apply-gate-set` invocation UUID, topology mode key, expected-process manifest path/hash, process-tree report path/verdict, join-manifest rows, and downstream handoff artifact path.

Positive evidence (eval should produce a finding when):

- Downstream RCA handoff exists for the active cycle, but no current process-tree report is present.
- The expected-process manifest omits the post-apply gate subtree, required gate rows, or documented topology mode.
- The process-tree report is non-PASS, stale, malformed, or bound to a different root invocation/cycle.
- Join-manifest rows cite invocations not covered by the process-tree evidence consumed for handoff.

Non-fire cases:

- Current expected-process and process-tree PASS evidence bind to the active RCA cycle, root invocation, applied diff, and gate fan-out.
- A current topology non-applicability or ratified exception row blocks handoff and names the repair route.

Finding schema: common schema plus `scenario_id=ACR277-RCA-001`, `gate=process-tree-audit`, `phase=rca-post-apply-before-handoff`, `report_paths`, and `trace_locator`.

Suggested action: re-route the RCA cycle through shared `apply-gate-set` process-tree evidence and block handoff until current topology evidence passes or a ratified blocking exception is recorded.

Supersession linkage: Strengthens `APPLY-GATE-SET-003` and absorbs the ACR-287 RCA PASS boundary from `evals/acr-287-rca-post-apply-gate-set/eval.md`.

### ACR277-RCA-002: PR-review test-audit gate runs against the actual applied diff

Scenario id: `ACR277-RCA-002`

Intended observation: RCA post-apply must run the PR-review test-audit gate against the actual RCA-applied diff before any downstream handoff consumes the fix.

Gate this scenario covers: `pr-review-test-audit`.

Evidence fields: applied diff ref/hash, child invocation UUID and prompt path for test-audit, test-audit report path/verdict, join-manifest row, changed-test evidence, original-signal evidence, residual references, and handoff artifact path.

Positive evidence (eval should produce a finding when):

- Handoff exists but no test-audit row/report exists for the active RCA applied diff.
- The report exists but its prompt references a stale, planned, or unrelated diff rather than the actual applied diff.
- The report is non-PASS/non-LOW, malformed, or missing changed-test/original-signal/residual inputs while handoff still proceeds.

Non-fire cases:

- The test-audit report is current, resolves to the active applied diff, consumes changed-test/original-signal/residual evidence, and passes or blocks handoff.
- A valid skip-with-followup row explicitly names the test-audit gate and prevents silent waiver.

Finding schema: common schema plus `scenario_id=ACR277-RCA-002`, `gate=pr-review-test-audit`, `phase=rca-post-apply-before-handoff`, `report_paths`, and `trace_locator`.

Suggested action: dispatch or rerun PR-review test-audit through `apply-gate-set` with the actual diff and block downstream movement until the row is current.

Supersession linkage: Strengthens the test-audit subset of `APPLY-GATE-SET-001` and absorbs ACR-287 RCA placement/blocking discharge.

### ACR277-RCA-003: PR-review multi-concern gate runs against the actual applied diff

Scenario id: `ACR277-RCA-003`

Intended observation: RCA post-apply must run the PR-review multi-concern gate against the actual applied diff and honor non-LOW concern findings before handoff.

Gate this scenario covers: `pr-review-multi-concern`.

Evidence fields: applied diff ref/hash, multi-concern child invocation UUID/prompt path, report path/verdict, scope/dossier refs, split/revise disposition, join-manifest row, and handoff artifact path.

Positive evidence (eval should produce a finding when):

- Handoff exists with no current multi-concern report for the active applied diff.
- The report references a stale or unrelated diff/scope.
- The report emits non-LOW multi-concern, scope, shortcut, or decomposition findings but no current split, revise, accepted-risk, or blocking disposition is recorded.

Non-fire cases:

- The multi-concern report is current for the actual applied diff and is LOW/PASS.
- Non-LOW findings trigger repair, accepted disposition, split, or RCA re-entry before handoff.

Finding schema: common schema plus `scenario_id=ACR277-RCA-003`, `gate=pr-review-multi-concern`, `phase=rca-post-apply-before-handoff`, `report_paths`, and `trace_locator`.

Suggested action: rerun multi-concern review through `apply-gate-set` and route non-LOW findings to repair, split, or RCA re-entry before closure.

Supersession linkage: Strengthens the multi-concern subset of `APPLY-GATE-SET-001`.

### ACR277-RCA-004: PR-review justification gate runs against the actual applied diff

Scenario id: `ACR277-RCA-004`

Intended observation: RCA post-apply must run the PR-review justification gate against the actual applied diff so unexplained changes cannot ride through handoff.

Gate this scenario covers: `pr-review-justification`.

Evidence fields: applied diff ref/hash, justification child invocation UUID/prompt path, report path/verdict, change-to-rationale thread inventory, residual/disposition rows, join-manifest row, and handoff artifact path.

Positive evidence (eval should produce a finding when):

- Handoff exists with no current justification report for the active RCA applied diff.
- The report references stale PR metadata, stale threads, or a planned diff instead of actual applied changes.
- Open justification threads remain unresolved while downstream handoff proceeds.

Non-fire cases:

- The justification report is current for the active applied diff and all challenged changes are `keep`, `drop`, `backlog`, or otherwise dispositioned before handoff.
- A valid blocking row prevents handoff until justification evidence is current.

Finding schema: common schema plus `scenario_id=ACR277-RCA-004`, `gate=pr-review-justification`, `phase=rca-post-apply-before-handoff`, `report_paths`, and `trace_locator`.

Suggested action: rerun the justification gate against the active applied diff and resolve or block all open threads before downstream movement.

Supersession linkage: Strengthens the justification subset of `APPLY-GATE-SET-001`.

### ACR277-RCA-005: Composite code-quality fan-out preserves runtime claim and bootstrap-exception evidence

Scenario id: `ACR277-RCA-005`

Intended observation: RCA post-apply must run composite code-quality fan-out with `dossier_diff_path` and `runtime_claim` transport, and must verify bootstrap-exception ratification inventory before non-LOW evidence authorizes handoff.

Gate this scenario covers: `code-quality-composite`, `runtime-claim-transport`, `bootstrap-exception-ratification`, `proof-risk`.

Evidence fields: aggregate code-quality report, child A1 auditor reports, proof-risk and validation-integrity rows, `dossier_diff_path`, `runtime_claim` ref/hash, bootstrap-exception row, DECISIONS entry path, join-manifest row, and handoff artifact path.

Positive evidence (eval should produce a finding when):

- Handoff exists without a current aggregate code-quality row for the actual applied diff.
- Child prompts or aggregate rows omit `dossier_diff_path` or `runtime_claim`, or resolve those inputs to stale/missing paths.
- Aggregate verdict is non-LOW, NEEDS_INPUT, or BLOCKED, and no ratified bootstrap-exception row blocks or authorizes the path.
- A bootstrap-exception row exists without DECISIONS authority or without the four-condition ratification record.

Non-fire cases:

- Composite code-quality rows are current, LOW/PASS, and preserve `dossier_diff_path` plus `runtime_claim` into child prompts.
- Non-LOW aggregate evidence is paired with a current ratified bootstrap-exception row and DECISIONS entry, or blocks handoff with repair route.

Finding schema: common schema plus `scenario_id=ACR277-RCA-005`, `gate=code-quality-composite`, `phase=rca-post-apply-before-handoff`, `report_paths`, and `trace_locator`.

Suggested action: rerun composite code-quality through `apply-gate-set`, preserve runtime-claim transport, and repair or ratify bootstrap-exception evidence before handoff.

Supersession linkage: Strengthens `APPLY-GATE-SET-002` and `APPLY-GATE-SET-006`; cites ACR-288 implementation-pipeline `APPLY-GATE-SET-006` discharge as peer evidence where the implementation caller boundary is relevant.

### ACR277-RCA-006: Readiness gates run before any caller-mode-equivalent handoff

Scenario id: `ACR277-RCA-006`

Intended observation: RCA post-apply handoff must wait for inherited prototype proof applicability, integration readiness, and prototype-swap readiness rows, or explicit current non-applicability rows, before any caller-mode-equivalent handoff.

Gate this scenario covers: `inherited-prototype-tests-readiness`, `integration-tests-readiness`, `prototype-swap-record-readiness`.

Evidence fields: inherited prototype proof applicability row, integration test or `LevelComponentSet` evidence, `PrototypeSwapRecord` path or non-applicability statement, readiness manifest rows, caller mode, currentness keys, and handoff artifact path.

Positive evidence (eval should produce a finding when):

- Handoff exists without readiness rows for inherited prototype proof, integration tests, or swap-record applicability.
- A readiness row is stale, malformed, or bound to a different component inventory/caller mode.
- A non-applicability claim lacks a current artifact and rationale.

Non-fire cases:

- All readiness rows exist before handoff and either pass or block.
- Explicit non-applicability artifacts are current, path-backed, and tied to the active RCA cycle and caller-mode equivalence claim.

Finding schema: common schema plus `scenario_id=ACR277-RCA-006`, `gate=readiness`, `phase=pre-handoff-readiness`, `report_paths`, and `trace_locator`.

Suggested action: emit and consume readiness rows before handoff, or block until the inherited proof, integration, and swap-record obligations are current or explicitly non-applicable.

Supersession linkage: Strengthens the handoff-readiness portion of `APPLY-GATE-SET-001` while preserving the prototype no-silent-drop rule.

### ACR277-RCA-007: PR-review commit-hygiene gate runs against the actual applied diff

Scenario id: `ACR277-RCA-007`

Intended observation: RCA post-apply must run the PR-review commit-hygiene gate against the actual applied diff or record current non-applicability before push, PR creation, or closure.

Gate this scenario covers: `pr-review-commit-hygiene`.

Evidence fields: branch/ref evidence, commit range, applied diff ref/hash, commit-hygiene child invocation UUID/prompt path, report path/verdict, join-manifest row, and push/PR/closure timing.

Positive evidence (eval should produce a finding when):

- Push, PR creation, or closure exists with commit evidence but no current commit-hygiene report.
- The report references a stale branch, stale commit range, planned diff, or unrelated output.
- The report is non-PASS/non-LOW and no repair, split, or blocking disposition is recorded.

Non-fire cases:

- Commit-hygiene runs against the current applied diff/commit range before movement and passes or blocks.
- There is no commit output to review and a current non-applicability row records that fact.

Finding schema: common schema plus `scenario_id=ACR277-RCA-007`, `gate=pr-review-commit-hygiene`, `phase=rca-post-apply-before-push-or-pr`, `report_paths`, and `trace_locator`.

Suggested action: run commit-hygiene through `apply-gate-set` against the active applied diff and block movement on non-LOW evidence.

Supersession linkage: Strengthens the commit-hygiene subset of `APPLY-GATE-SET-001`.

### ACR277-RCA-008: Hotfix skip rows and currentness re-verification survive Phase 2 root-cause re-entry

Scenario id: `ACR277-RCA-008`

Intended observation: Hotfix skip-with-followup rows, manifest currentness, stale-refusal rows, and bootstrap-exception rows must be re-verified after Phase 2 root-cause re-entry before downstream handoff.

Gate this scenario covers: `hotfix-skip`, `manifest-currentness`, `stale-refusal`, `bootstrap-exception`, `root-cause-re-entry`.

Evidence fields: prior and current RCA cycle ids, Phase 2 re-entry marker, prior/current applied diff hashes, join-manifest paths/hashes, `verified_at` values, skip rows, follow-up refs, stale-refusal rows, bootstrap-exception rows, DECISIONS entry, and handoff artifact path.

Positive evidence (eval should produce a finding when):

- Handoff exists after Phase 2 re-entry while prior-cycle manifest rows are reused without currentness re-verification.
- Hotfix skip rows lack owner, accepted risk, evidence already run, follow-up ticket/PR, due date, or post-push/pre-merge obligation.
- A required follow-up or post-push gate is missing after a skip row claims it is required.
- Bootstrap-exception or skip rows cite stale DECISIONS/follow-up/currentness evidence.

Non-fire cases:

- All reused rows are reissued or re-verified against active cycle, head, diff, scope, runtime claim, and artifact hashes.
- Stale rows are explicitly refused and block handoff until repaired.
- Skip and exception rows are current, complete, and tied to valid follow-up/DECISIONS evidence.

Finding schema: common schema plus `scenario_id=ACR277-RCA-008`, `gate=currentness-and-skip-exception`, `phase=phase-2-re-entry-to-handoff`, `report_paths`, and `trace_locator`.

Suggested action: invalidate stale manifest rows, re-run or re-verify gate evidence, and repair skip/exception rows before handoff.

Supersession linkage: Strengthens `APPLY-GATE-SET-003`, `APPLY-GATE-SET-004`, `APPLY-GATE-SET-005`, and `APPLY-GATE-SET-006`.

### ACR277-RCA-009: Decomposition signal fires after repeated non-LOW rounds

Scenario id: `ACR277-RCA-009`

Intended observation: Repeated non-LOW gate rounds on the same finding class must produce a decomposition signal or multi-concern split disposition per `~/ai/conventions/decomposition-strategies.md` before RCA handoff.

Gate this scenario covers: `decomposition-signal`, `multi-concern-split`, `non-low-oscillation`.

Evidence fields: repeated gate reports by finding class, round history, decomposition-strategy evidence, split/no-split disposition, RCA re-entry marker, join-manifest rows, audit-history entries, and handoff artifact path.

Positive evidence (eval should produce a finding when):

- Two or more non-LOW rounds occur on the same concern class and handoff proceeds without decomposition signal, split, shrink, or documented no-split rationale.
- Split is recommended but no child WU, RCA re-entry, or blocking disposition is recorded.
- Audit-history records omit the repeated-round evidence or final decomposition disposition.

Non-fire cases:

- Repeated non-LOW rounds trigger split/shrink/re-entry before handoff.
- A current no-split rationale records why the repeated concern remains single-concern and names the blocking or accepted path.

Finding schema: common schema plus `scenario_id=ACR277-RCA-009`, `gate=decomposition-signal`, `phase=post-apply-gate-rounds`, `report_paths`, and `trace_locator`.

Suggested action: route through decomposition strategy selection, split or shrink the work, or record a current no-split disposition before downstream movement.

Supersession linkage: Strengthens the oscillation and decomposition handling carried by `APPLY-GATE-SET-001` and the audit/currentness cross-cuts from `APPLY-GATE-SET-003`.

### ACR277-RCA-010: Audit-history and DECISIONS currentness is recorded for every RCA cycle gate handoff

Scenario id: `ACR277-RCA-010`

Intended observation: Every RCA gate-set handoff must leave current audit-history and DECISIONS evidence naming manifests, reports, verdicts, currentness keys, skip/exception rows, and repair routes.

Gate this scenario covers: `audit-history-record`, `decisions-currentness`, `handoff-reviewability`.

Evidence fields: audit-history record path, DECISIONS entry path when applicable, dispatch manifest, join manifest, aggregate report, process-tree report, PR-review reports, currentness key, blocking rows, exception rows, inventory-resolution rows, decision, repair route, and handoff artifact path.

Positive evidence (eval should produce a finding when):

- Handoff exists without an audit-history record for the active RCA cycle gate-set decision.
- The audit record omits manifest/report paths, blocking rows, exception rows, inventory-resolution rows, currentness key, decision, or repair route.
- DECISIONS authority is cited by a skip, exception, ratification, or inventory-resolution row but the cited entry is absent or stale.
- Audit-history points away from the canonical RCA gate-set output root.

Non-fire cases:

- Audit-history and DECISIONS entries are current, path-backed, and resolve to the active cycle, diff, scope, runtime claim, manifest hashes, and handoff decision.
- No DECISIONS authority is claimed and the audit record explicitly says none was needed.

Finding schema: common schema plus `scenario_id=ACR277-RCA-010`, `gate=audit-history-decisions`, `phase=handoff-recording`, `report_paths`, and `trace_locator`.

Suggested action: append or repair the audit-history and DECISIONS records before handoff, then re-verify currentness against the active manifest.

Supersession linkage: Strengthens the audit trail portion of `APPLY-GATE-SET-001` and composes with ACR-287 gate-set evidence-field precedent.

### ACR277-RCA-011: Shared active inventory equivalence holds between RCA-mode and implementation-mode adapters

Scenario id: `ACR277-RCA-011`

Intended observation: RCA-mode and implementation-mode adapters must expose equivalent active inventory rows for proof-risk, supported-surface, runtime-claim transport, process-tree mode, currentness keys, skip rows, and exception rows, or record explicit inventory-resolution evidence with equivalent blocking semantics.

Gate this scenario covers: `caller-mode-inventory-equivalence`, `proof-risk`, `supported-surface`, `runtime-claim`, `topology-mode`, `currentness`, `skip-exception`.

Evidence fields: RCA-mode manifest rows, implementation-mode manifest rows, caller-mode ids, proof-risk rows, supported-surface rows, runtime-claim keys, process-tree topology-mode keys, currentness keys, skip/exception rows, inventory-resolution rows, DECISIONS entries, and peer ACR-288 implementation-mode evidence when available.

Positive evidence (eval should produce a finding when):

- RCA and implementation caller inventories diverge on required active rows without dual-score or fold rationale.
- Proof-risk or supported-surface rows are dropped in either caller mode without equivalent blocking semantics.
- Runtime-claim, topology-mode, currentness, skip, or exception rows exist in one caller mode but not the other with no resolution record.
- Inventory-resolution evidence is stale, missing source/fold target/rationale, or does not preserve blocking behavior.

Non-fire cases:

- Both caller modes emit equivalent active rows for the named inventory families.
- Differences carry inventory-resolution rows naming source, disposition, fold target or dual-score treatment, rationale, and equivalent blocking evidence.

Finding schema: common schema plus `scenario_id=ACR277-RCA-011`, `gate=caller-mode-inventory-equivalence`, `phase=adapter-inventory-review`, `report_paths`, and `trace_locator`.

Suggested action: repair the shared `apply-gate-set` inventory contract or adapter manifests so both caller modes preserve the same active gate obligations or explicit equivalent-resolution evidence.

Supersession linkage: Strengthens `APPLY-GATE-SET-003` and `APPLY-GATE-SET-007`; absorbs ACR-287 RCA adapter subset and cites ACR-288 implementation-pipeline `APPLY-GATE-SET-007` discharge as peer evidence where relevant.

## Residuals

No structural-coverage residual is expected at WRITE state. This eval owns the Markdown behavior specification for the RCA post-apply fan-out; downstream runnable detector, fixture, CLI, CI, and enforcement work owns any future ROLL_OUT transition.

## Lifecycle state: WRITE

Current state: `WRITE`. The behavior specification exists, but no runnable detector is required to exist per `~/ai/conventions/evals.md` section Lifecycle states. Transition to `ROLL_OUT` requires downstream runnable detector evidence, false-positive review, wiring readiness, and durable lifecycle notes.

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
- `~/ai/conventions/decomposition-strategies.md`
- ACR-277 dossier evidence vectors A, B, and C named by the prototype source eval.
