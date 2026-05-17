---
eval_id: acr-246-auditor-scope-convergence
behavior_class: Auditor scope-tightening + convergence guarantee
lifecycle_state: WRITE
severity_when_fires: HIGH
evidence_source_kinds:
  - agents-trace-json
  - dispatch-prompt
  - agent-log
  - audit-bundle
  - process-tree-audit
suggested_action_class: revise-proposal
---

# ACR-246 Auditor Scope-Tightening + Convergence Eval

## Eval identity

This is a markdown behavior specification for `acr-246-auditor-scope-convergence`, not runnable eval code. It defines future trace-backed detection for ACR-246's auditor scope boundary and convergence guarantee across S1-S6: the canonical scope clause in `/home/nes/ai/conventions/code-quality.md` `## Auditor Scope Boundary`, the cohesion/function-classification/coupling auditor report contracts, the WU-scope-only risk-profile clause, and this WRITE-state eval spec.

The frontmatter `severity_when_fires: HIGH` records the maximum severity because any scenario that inflates a LOW-only code-quality gate or hides a real WU-owned blocker can halt implementation work. Scenario bodies document narrower severity expectations: F1 and F4 are HIGH when they control a gate; F2 and F3 are MEDIUM when advisory and HIGH when they produce a blocking gate verdict.

## Unwanted behavior

The unwanted behavior is an A1 auditor or code-quality aggregate treating context-only, pre-existing, or helper-overlay evidence as a current WU blocking finding without ownership proof, or prescribing remediation that cannot converge because each fix opens a same-family finding on the helper, declaration, or adjacent context surface introduced to satisfy the prior finding.

This eval is anchored to the canonical scope clause in `/home/nes/ai/conventions/code-quality.md` `## Auditor Scope Boundary`: only the current unified diff or equivalent WU-owned corpus is the blocking target; broader files, traces, proposals, risks, callers, callees, adjacent declarations, and sampled stable functions are context or fixture evidence unless the current WU introduced, worsened, or made the finding gate-relevant.

## Positive evidence

Positive evidence includes a dispatch prompt, trace, auditor report, or aggregate audit bundle showing at least one of these patterns: a pre-existing or context-only concern raises the current WU gate verdict; a non-LOW finding lacks `blocking_or_residual` or equivalent ownership proof; a stable healthy sample trips the single-classification rule above the documented false-positive threshold; a healthy single-classification target returns non-LOW; or a real WU-owned multi-classifier HIGH omits a convergence proof or converts helper-overlay findings into new blockers.

The future detector may consume saved `agents trace --json`, prompt files, agent logs, code-quality reports, process-tree-auditor reports, normalized findings, and audit-history bundles. Evidence should cite S1 for the canonical boundary, S2-S4 for auditor-specific report contracts, S5 for WU-scope-only scoring, and S6 for these scenario expectations.

## Non-fire cases

This eval does not fire when a WU-owned target truly introduces, worsens, or makes gate-relevant an A1 finding and the report includes ownership proof. It also does not fire when context-only evidence is preserved as residual, when a helper or adjacent declaration introduces independent behavior outside the previous remediation overlay, or when a malformed or ambiguous evidence bundle returns `NEEDS_INPUT` / `BLOCKED` instead of manufacturing a LOW or non-LOW verdict.

This eval does not weaken existing A1 categories, numerical thresholds, LOW-only disposition policy, adapter thresholds, intrinsic-surface thresholds, malformed-declaration stop states, or subordination semantics. Those remain outside ACR-246's eval scope.

## Required trace fields

The future eval implementation must read evidence by semantic role: WU ID, phase/gate, root invocation UUID, child invocation UUIDs, dispatch prompt path, auditor name, auditor report path, code-quality aggregate path, normalized findings path, diff path or equivalent WU-owned corpus path, changed-file/function inventory when present, context evidence paths, `blocking_or_residual` classification, ownership-proof text, residual rows, suggested split/remediation text, convergence-proof fields, false-positive sample manifest, and final gate verdict.

For S1/S5 text-contract checks, the trace bundle should include the convention snapshot or diff path. For S2-S4 auditor checks, it should include the prompt/report pair and any aggregate that consumed the report. For S6 scenario checks, it should include the scenario identifier that the reviewer or future runner applied.

## Finding shape

The finding preserves `eval_id`, `severity`, `evidence_paths`, `summary`, `suggested_action`, and `confidence`. Allowed extensions include `scenario_id`, `wu_id`, `phase`, `gate`, `auditor`, `surface_id`, `finding_ids`, `blocking_or_residual`, `ownership_proof`, `residual_rows`, `aggregate_verdict`, `sample_size`, `false_positive_count`, `false_positive_rate`, `threshold`, `suggested_split`, `convergence_proof`, and `helper_overlay_handling`.

Scenario-specific findings must name whether the defect is `scope-boundary-inflation`, `stable-function-false-positive`, `healthy-target-non-low`, or `non-converging-split`. When a finding is about a non-LOW gate, the summary must say whether the non-LOW row was blocking or residual and whether that classification matched the canonical S1 boundary.

## Suggested action

Return `revise-proposal` when this eval fires. The owning workflow should revise the ACR-246 text contract, auditor report contract, or eval scenario before implementation proceeds, then rerun the relevant Phase 4 or Phase 6 code-quality evidence path.

If the finding is a true WU-owned A1 defect, the action is ordinary remediation until the gate is LOW. If the finding is context-only, pre-existing, or helper-overlay evidence misclassified as blocking, the action is to correct the scope/residual classification rather than accept a non-LOW gate.

## Lifecycle notes

This eval ships in `WRITE` state. No `eval.py`, `eval.rs`, pytest, CLI, CI, scheduler, or workflow wiring is required or introduced by ACR-246.

Downstream runnable eval work owns fixtures, detector code, advisory rollout, false-positive review, and enforcement readiness. Until then, this file is a reviewable behavior contract consumed by Phase 6b/6c handoff and by future audits that need to compare trace evidence against ACR-246's expected scope and convergence shape.

Lifecycle note: ACR-249 supersedes this eval for scope-boundary behavior via `evals/auditor-whole-file-scope/eval.md`. The scenarios below remain historical ACR-246 evidence, but F1/S1/S5 residual expectations are reversed for files/components touched by a current WU: pre-existing A1 findings inside touched files/components are current-WU work after ACR-249.

## Scenarios

### F1 scope-boundary-pre-existing-residual

Positive evidence: The trace shows an auditor inspecting broader context, such as old functions in a touched file, adjacent declarations, old Markdown operator references, or historical audit evidence, and the report classifies the concern as `blocking_or_residual=residual` because the current WU did not introduce, worsen, or make the concern gate-relevant. S1 supplies the canonical boundary; S2-S4 supply the auditor-specific output field or residual-row requirement; S5 supplies the matching WU-scope-only scoring rule.

Non-fire cases: This scenario does not fire when the current WU changed the target surface in a way that introduced, worsened, or made the concern gate-relevant and the report includes ownership proof. It also does not fire when the report records context-only concerns as residual rows while keeping the active aggregate LOW.

Required trace fields: The evidence bundle must include the WU-owned corpus or diff path, the context evidence path that exposed the concern, the auditor report path, the `blocking_or_residual` classification, ownership-proof text when present, residual-row text, and the aggregate verdict path.

Finding shape: A defect finding uses `scenario_id=scope-boundary-pre-existing-residual`, `severity=HIGH` when the misclassified row controls a gate, `auditor`, `surface_id`, `finding_ids`, `blocking_or_residual`, `ownership_proof`, `residual_rows`, `aggregate_verdict`, and evidence paths for the diff/corpus, context source, report, and aggregate.

Expected outcome: `blocking_or_residual=residual` on the non-LOW finding; aggregate stays LOW.

### F2 rule-audit-stable-functions

Positive evidence: The trace or audit bundle names a sample of stable healthy functions from main, sourced from shipped and audited code paths that did not previously trigger function-classification findings, including AGE-103 and AGE-116 report evidence where many changed functions scored LOW and historical recurrence evidence identified over-strictness on pre-existing functions. The expected behavior is LOW for each sampled stable single-classification function. The false-positive threshold is more than 5 percent of sampled stable functions returning a blocking multi-classifier finding, with a minimum sample size of 20 functions for a future runnable detector; in WRITE state, the sample-source description and threshold are the required observable.

Non-fire cases: This scenario does not fire when a sampled function is not stable, is not from main or an equivalent accepted baseline, lacks enough source context to classify, or genuinely contains two or more A1 categories and is marked as outside the healthy sample. It also does not fire when false positives are recorded below or equal to the 5 percent threshold and do not control a gate.

Required trace fields: The evidence bundle must include a sample manifest or sample-source description, baseline/source reference, function identifiers, auditor report path, per-function classification result, false-positive count, sample size, false-positive rate, threshold, and whether any finding became gate-controlling.

Finding shape: A defect finding uses `scenario_id=rule-audit-stable-functions`, `severity=MEDIUM` for advisory threshold breach and `severity=HIGH` when the breach controls a LOW-only gate, `auditor=function-classification-auditor`, `sample_size`, `false_positive_count`, `false_positive_rate`, `threshold=0.05`, `finding_ids`, and evidence paths for the sample manifest and report.

Expected outcome: Stable healthy functions sampled from main return LOW; the reviewable eval records the sample source and the false-positive threshold, and future runnable evidence must stay at or below a 5 percent false-positive rate.

### F3 healthy-single-classification-low

Positive evidence: The trace shows a healthy single-classification target, either a function with one A1 category or a Markdown-owned auditor/convention target that is inapplicable to function-only scoring, receiving LOW with no blocking finding rows. S1 supplies the target/context boundary, S3 supplies the single-classification rule surface, and S6 supplies this expected LOW behavior.

Non-fire cases: This scenario does not fire when the target genuinely has two or more A1 categories, when the evidence bundle is missing the target body or classification basis and returns `NEEDS_INPUT`, or when the report preserves advisory context as residual without raising the active verdict.

Required trace fields: The evidence bundle must include target identifier, target source or Markdown surface, WU-owned corpus/diff evidence, auditor report path, classification result, final verdict, findings table, and residual table if any context was inspected.

Finding shape: A defect finding uses `scenario_id=healthy-single-classification-low`, `severity=MEDIUM` when advisory and `severity=HIGH` when gate-controlling, `auditor`, `surface_id`, `target_identifier`, `aggregate_verdict`, `finding_ids`, `blocking_or_residual`, and evidence paths for the target and report.

Expected outcome: LOW, no findings table rows.

### F4 real-multi-classifier-high-converging-split

Positive evidence: The trace shows a real WU-owned changed function or equivalent changed target with two A1 categories. The auditor returns HIGH on that WU-owned target and the `suggested_split` includes a `convergence_proof` block naming `current_blocking_finding`, `why_split_reduces_blocking_set`, and `helper_overlay_handling`. Any helper, declaration, or adjacent Markdown support surface introduced solely to satisfy the current finding is recorded as residual overlay evidence unless it introduces independent behavior, cross-component reach, or a changed target outside the previous fix overlay. S3 owns the function-classification schema field; S2 and S4 own sibling convergence-overlay language for cohesion and coupling; S1 owns the blocking/residual boundary.

Non-fire cases: This scenario does not fire when the target is not WU-owned, when the target has only one A1 category, when the auditor returns HIGH with complete ownership proof and convergence proof, or when a helper/declaration introduces an independent WU-owned defect outside the previous remediation overlay and is therefore legitimately blocking.

Required trace fields: The evidence bundle must include changed target identifier, diff or WU-owned corpus path, category evidence showing two A1 categories, auditor report path, finding ID, `blocking_or_residual=blocking` for the original WU-owned target, `suggested_split`, `convergence_proof.current_blocking_finding`, `convergence_proof.why_split_reduces_blocking_set`, `convergence_proof.helper_overlay_handling`, helper/declaration overlay rows, residual classifications, and aggregate verdict.

Finding shape: A defect finding uses `scenario_id=real-multi-classifier-high-converging-split`, `severity=HIGH`, `auditor`, `surface_id`, `finding_ids`, `blocking_or_residual`, `ownership_proof`, `suggested_split`, `convergence_proof`, `helper_overlay_handling`, `residual_rows`, `aggregate_verdict`, and evidence paths for the diff/corpus, report, and aggregate.

Expected outcome: HIGH on the WU-owned target with the expected blocking-finding shape carrying a `suggested_split` block and `convergence_proof` sub-block, alongside helper-overlay residual rows. The `convergence_proof` names `current_blocking_finding`, `why_split_reduces_blocking_set`, and `helper_overlay_handling` per S3; S2 and S4 provide the sibling convergence-overlay expectations for cohesion and coupling surfaces.
