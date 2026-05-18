---
workflow:
  id: code-quality
workflow_dispatch_contract:
  orchestrator: "implementation-pipeline-orchestrator Phase 4 caller, ad-hoc developer, or PR-review caller"
  inputs:
    - "repo_root, diff_path, touched_surfaces_path, scratch_dir, and planning_dir for pipeline-callable artifact layout"
    - "optional Phase 4 evidence: proposal_path, problem_map_path, risk_profile_path, proof_plan_excerpt, runtime_claim, and wu_id"
    - "optional PR/RCA evidence: dossier_diff_path, decisions_path, runtime_artifact_evidence_path, and validation-surface context"
    - "optional refs and inventories: base_ref, head_ref, changed_files_path, changed_functions_path, code_trace_paths, and code_quality_ref"
  expectations:
    - "dispatches each auditor named in conventions/code-quality.md ## Auditor Set and writes a durable code-quality bundle"
    - "supports Phase 4 proposal-time, Phase 6 per-component, and Phase 8 actual-PR-diff callers"
    - "aggregates child verdicts to LOW/MEDIUM/HIGH worst-case while preserving NEEDS_INPUT/BLOCKED stop states"
    - "preserves the convention as the single rule reference; does not redefine A1"
  outputs:
    - "dispatch manifest, child prompts/logs/reports, normalized findings.json plus findings.md, and aggregate-code-quality.md"
    - "role outputs suitable for proposer revision, decision-encoder, or PR-review consumption"
  non_goals:
    - "does not implement fixes, edit child auditors, or replace child auditor procedures"
    - "does not redefine A1 or duplicate the convention's rule descriptions"
    - "does not replace the caller's owning gate policy; implementation-pipeline Phase 4 entry is wired in ~/ai/agents/implementation-pipeline-orchestrator.md § Phase 4 code-quality gate"
---
# Code-Quality Workflow

## Workflow Dispatch Surface

### Orchestrator

implementation-pipeline-orchestrator Phase 4 caller, ad-hoc developer, or PR-review caller

### Inputs

- repo_root, diff_path, touched_surfaces_path, scratch_dir, and planning_dir for pipeline-callable artifact layout
- optional Phase 4 evidence: proposal_path, problem_map_path, risk_profile_path, proof_plan_excerpt, runtime_claim, and wu_id
- optional PR/RCA evidence: dossier_diff_path, decisions_path, runtime_artifact_evidence_path, and validation-surface context
- optional refs and inventories: base_ref, head_ref, changed_files_path, changed_functions_path, code_trace_paths, and code_quality_ref

### Expectations

- dispatches each auditor named in `conventions/code-quality.md` `## Auditor Set` and writes a durable code-quality bundle
- supports Phase 4 proposal-time, Phase 6 per-component, and Phase 8 actual-PR-diff callers
- aggregates child verdicts to LOW/MEDIUM/HIGH worst-case while preserving NEEDS_INPUT/BLOCKED stop states
- preserves the convention as the single rule reference; does not redefine A1

### Outputs

- dispatch manifest, child prompts/logs/reports, normalized findings.json plus findings.md, and aggregate-code-quality.md
- role outputs suitable for proposer revision, decision-encoder, or PR-review consumption

### Non-goals

- does not implement fixes, edit child auditors, or replace child auditor procedures
- does not redefine A1 or duplicate the convention's rule descriptions
- does not replace the caller's owning gate policy; implementation-pipeline Phase 4 entry is wired in `~/ai/agents/implementation-pipeline-orchestrator.md` § `#### Phase 4 code-quality gate`

## Purpose

Coordinate a composite gate over the code-quality surface by treating `~/ai/conventions/code-quality.md` as the rule reference and the child auditors as the executable procedures. The workflow applies `conventions/code-quality.md` `## Auditor Scope Boundary` and dispatches each auditor named in `conventions/code-quality.md` `## Auditor Set`. The workflow owns dispatch, artifact layout, finding normalization, aggregate verdicts, currentness semantics, audit-history handoff, and process-tree handoff for callers that need one code-quality result.

## Declared roles

`orchestration`, `validator`, `mapper`

## Declared roles (mirror)

`~/ai/conventions/code-quality.md` remains the canonical rule source for declared-role cohesion scoring.

- LOW when actual classifications are a subset of the declared role set.
- HIGH when actual classifications exceed the declared role set or include classifications outside the declared role set.

## Use When

- An implementation-pipeline Phase 4 caller has proposal, touched-surface, and diff or equivalent change evidence and needs one composite code-quality gate.
- An implementation-pipeline Phase 6 per-component caller has component-local diff evidence and needs a component-scoped composite code-quality gate before component closure.
- An implementation-pipeline Phase 8 caller has the actual PR diff plus approved proposal/proof-plan context and needs a composite code-quality row in the Phase 8 join manifest.
- A PR-review caller has branch or PR diff evidence and wants normalized A1 findings from the supported auditor fanout.
- An ad-hoc developer wants to run the same composite review over a local diff and touched-surface package without entering the implementation pipeline.

## Do Not Use When

- The target is workflow design, operator design, runtime procedure adherence, or rebase drift; use `~/ai/workflows/audit.md` for those surfaces.
- The caller needs PR-review's distinct multi-concern, justification, or commit-hygiene gates.
- The caller needs topology verification of an agent run; `process-tree-auditor` remains the topology authority.

## Required Inputs

- `repo_root=<path>`: required for Phase 4, PR-review, and ad-hoc invocations; points to the repository being reviewed.
- `diff_path=<path>`: required for PR-review and ad-hoc invocations, and required in Phase 4 when A4/A5 are selected; contains a unified diff or equivalent text change artifact used to identify touched files/components and evidence anchors.
- `touched_surfaces_path=<path>`: required for Phase 4, PR-review, and ad-hoc invocations; lists changed files, module/package/component labels, and known component boundaries.
- `scratch_dir=<path>`: required for Phase 4 pipeline-callable invocations; stores prompts and logs.
- `planning_dir=<path>`: required for Phase 4 pipeline-callable invocations; stores durable reports, findings, manifest, and aggregate output.
- `proposal_path=<path>`: optional Phase 4 evidence unless A6 children are selected before implementation, then required.
- `proof_plan_excerpt=<text-or-path>`: required when proof-plan/runtime-claim context is selected, including Phase 8 actual-diff callers.
- `runtime_claim=<text>`: required when validation-integrity is selected, including Phase 8 actual-diff callers and RCA dossier contexts.
- `dossier_diff_path=<path>`: required when validation-integrity runs in RCA dossier mode.
- `decisions_path=<path>`: optional ratification evidence for validation-integrity findings.
- `runtime_artifact_evidence_path=<path>`: optional runtime-artifact validation evidence for validation-integrity ratification and proof context.
- `problem_map_path=<path>`: optional Phase 4 evidence unless A6 children are selected before implementation, then required.
- `risk_profile_path=<path>`: optional Phase 4 evidence unless A6 children are selected before implementation, then required.
- `wu_id=<id>`: required for Phase 4 pipeline-callable invocations; optional provenance for PR-review and ad-hoc invocations.
- `base_ref=<ref>`: optional for Phase 4, PR-review, and ad-hoc invocations; records diff provenance.
- `head_ref=<ref>`: optional for Phase 4, PR-review, and ad-hoc invocations; records diff provenance.
- `changed_files_path=<path>`: optional inventory for Phase 4, PR-review, and ad-hoc invocations.
- `changed_functions_path=<path>`: optional inventory for A5 and any caller that can provide function-level change evidence.
- `code_trace_paths=<paths>`: optional evidence for coupling review when traces or symbol maps exist.
- `code_quality_ref=<path>`: optional reference override; defaults to `~/ai/conventions/code-quality.md`.

Dispatch prompts apply `conventions/code-quality.md` `## Auditor Scope Boundary` and `## Touched-file ownership`: `diff_path`, changed-file inventories, changed-function inventories, proposal, problem-map, risk-profile, touched-surface, trace, and inventory paths identify the touched files/components and supply evidence. They do not narrow the blocking target below the whole touched file/component.

## Output Paths

Default slug: caller-supplied `${slug}` or `code-quality-workflow`.

Pipeline-callable mode splits observability from durable handoff:

- Prompts root: `${scratch_dir}/code-quality/${slug}/prompts`.
- Logs root: `${scratch_dir}/code-quality/${slug}/logs`.
- Durable reports root: `${planning_dir}/code-quality/${slug}/reports`.
- Normalized machine-readable findings: `${planning_dir}/code-quality/${slug}/findings.json`.
- Normalized human-readable findings: `${planning_dir}/code-quality/${slug}/findings.md`.
- Dispatch manifest: `${planning_dir}/code-quality/${slug}/dispatch-manifest.md`.
- Aggregate report: `${planning_dir}/code-quality/${slug}/aggregate-code-quality.md`.
- Optional expected process artifact: `${planning_dir}/code-quality/${slug}/process-tree-expected.md` when a downstream gated workflow consumes the fanout.

Standalone mode uses one root:

- Standalone artifact root: `${code_quality_work_dir}/`.

## Dispatch Manifest

Write `dispatch-manifest.md` before child dispatch where possible. Every selected child row defaults to required.

Dispatch each auditor named in `conventions/code-quality.md` `## Auditor Set`; the table below is the operational manifest for the current canonical set.

| Concern | Auditor | Model | Prompt path | Log path | Report path | Required | Applicability inputs |
|---|---|---|---|---|---|---:|---|
| A4 | push-pull-auditor | gpt-high | `${scratch_dir}/code-quality/${slug}/prompts/push-pull-auditor.prompt.md` | `${scratch_dir}/code-quality/${slug}/logs/push-pull-auditor.log` | `${planning_dir}/code-quality/${slug}/reports/push-pull-auditor.md` | true | `repo_root`, `diff_path`, touched surface evidence |
| A5 | function-classification-auditor | gpt-high | `${scratch_dir}/code-quality/${slug}/prompts/function-classification-auditor.prompt.md` | `${scratch_dir}/code-quality/${slug}/logs/function-classification-auditor.log` | `${planning_dir}/code-quality/${slug}/reports/function-classification-auditor.md` | true | `repo_root`, `diff_path`, touched surface evidence |
| A6 | cohesion-auditor | gpt-high | `${scratch_dir}/code-quality/${slug}/prompts/cohesion-auditor.prompt.md` | `${scratch_dir}/code-quality/${slug}/logs/cohesion-auditor.log` | `${planning_dir}/code-quality/${slug}/reports/cohesion-auditor.md` | true | `repo_root`, `planning_dir`, `wu_id`, `touched_surfaces_path`, `diff_path` |
| A6 | coupling-auditor | gpt-high | `${scratch_dir}/code-quality/${slug}/prompts/coupling-auditor.prompt.md` | `${scratch_dir}/code-quality/${slug}/logs/coupling-auditor.log` | `${planning_dir}/code-quality/${slug}/reports/coupling-auditor.md` | true | `repo_root`, `planning_dir`, `wu_id`, `touched_surfaces_path`, `diff_path` |
| ACR-254 | validation-integrity-auditor | gpt-high | `${scratch_dir}/code-quality/${slug}/prompts/validation-integrity-auditor.prompt.md` | `${scratch_dir}/code-quality/${slug}/logs/validation-integrity-auditor.log` | `${planning_dir}/code-quality/${slug}/reports/validation-integrity-auditor.md` | context-dependent | PR diff or RCA dossier diff context plus `runtime_claim`; optional `decisions_path`, `runtime_artifact_evidence_path` |
| ACR-254 | proof-risk-auditor | gpt-high | `${scratch_dir}/code-quality/${slug}/prompts/proof-risk-auditor.prompt.md` | `${scratch_dir}/code-quality/${slug}/logs/proof-risk-auditor.log` | `${planning_dir}/code-quality/${slug}/reports/proof-risk-auditor.md` | context-dependent | `proposal_path` or RCA fix-decision artifact with `## Proof plan`; `proof_plan_excerpt`, `runtime_claim` when supplied by caller |

`Required=false` is allowed only with a written applicability reason in the manifest. Optionality records evidence applicability; it is not a way to demote relevant A1 or ACR-254 review. `validation-integrity-auditor` is `Required=true` when PR/diff/RCA evidence exists with validation-surface change risk or runtime-claim context. `proof-risk-auditor` is `Required=true` when proposal, proof-plan, RCA fix-decision, or runtime-claim context exists. In Phase 8 actual-PR-diff callers, both ACR-254 rows are always `Required=true`: the Phase 3 `## Proof plan` requirement supplies runtime-claim context, and the proposal cited by the PR body's close-keyword footer is the proof-risk artifact under review.

## Per-Concern Auditor Routing

### A4 - Push-vs-pull system coupling

Auditor path: `~/ai/agents/push-pull-auditor.md`. Model: `gpt-high`.

- Required inputs: `repo_root`, `diff_path`, `output_path`; `diff_path` identifies touched files/components.
- Optional inputs: `base_ref`, `head_ref`, `changed_files_path`, `proposal_path`, `problem_map_path`, `risk_profile_path`, `code_quality_ref`.

### A5 - Function classification

Auditor path: `~/ai/agents/function-classification-auditor.md`. Model: `gpt-high`.

- Required inputs: `repo_root`, `diff_path`, `output_path`; A5 audits every function in touched files.
- Optional inputs: `changed_functions_path`, `proposal_path`, `problem_map_path`, `risk_profile_path`, `code_quality_ref`.

### A6 - Cohesion

Auditor path: `~/ai/agents/cohesion-auditor.md`. Model: `gpt-high`.

- Required inputs: `repo_root`, `planning_dir`, `wu_id`, `touched_surfaces_path`, and `diff_path` or equivalent changed-file evidence used to identify touched files/components.
- Context inputs: `proposal_path`, `problem_map_path`, `risk_profile_path`, `output_path`.

### A6 - Coupling

Auditor path: `~/ai/agents/coupling-auditor.md`. Model: `gpt-high`.

- Required inputs: `repo_root`, `planning_dir`, `wu_id`, `touched_surfaces_path`, and `diff_path` or equivalent changed-file evidence used to identify touched files/components.
- Context inputs: `proposal_path`, `problem_map_path`, `risk_profile_path`, `code_trace_paths`, `output_path`.

### ACR-254 - Validation integrity

Auditor path: `~/ai/agents/validation-integrity-auditor.md`. Model: `gpt-high`.

- Required in `pr-diff` mode when the invocation includes actual PR diff context, validation-surface change risk, or runtime-claim context. Required inputs: `mode=pr-diff`, `diff_path`, `runtime_claim`, `report_path`, and `worktree_path`.
- Required in `rca-dossier` mode when the invocation includes RCA verification evidence. Required inputs: `mode=rca-dossier`, `dossier_diff_path`, `runtime_claim`, `report_path`, and `worktree_path`.
- Optional ratification inputs: `decisions_path` and `runtime_artifact_evidence_path`.
- Phase 4 proposal-time callers usually record `Required=false` with a reason when no actual PR diff or RCA dossier evidence exists yet.
- Phase 6 per-component callers set `Required=true` when the component diff has validation-surface change risk or runtime-claim context; otherwise they record `Required=false` with a written reason.
- Phase 8 actual-PR-diff callers set `Required=true`.

### ACR-254 - Proof risk

Auditor path: `~/ai/agents/proof-risk-auditor.md`. Model: `gpt-high`.

- Required when the invocation includes `proposal_path`, RCA fix-decision artifact, `proof_plan_excerpt`, or runtime-claim/proof-plan context.
- Required inputs: `mode=phase-3-proposal` for implementation-pipeline proposals or `mode=rca-fix-decision` for RCA fix-decision artifacts, plus `proposal_path`, `report_path`, and `worktree_path`.
- Phase 4 proposal-time callers set `Required=true` for the approved Phase 3 proposal.
- Phase 6 per-component callers set `Required=true` only when component-local proof-plan/runtime-claim context exists; otherwise they record `Required=false` with a written reason.
- Phase 8 actual-PR-diff callers set `Required=true` and validate the proposal cited in the PR body's close-keyword footer against the actual shipped diff context.

## Aggregate Verdict

The aggregate verdict uses these outcomes:

- `NEEDS_INPUT:<absolute_artifact_path>` when any required child returns `NEEDS_INPUT`.
- `BLOCKED:<reason>` when required files are unreadable, unwritable, malformed, or required child auditor reports are malformed.
- `HIGH` when any required child returns `HIGH`.
- `MEDIUM` when any required child returns `MEDIUM` and no child returns `HIGH`.
- `LOW` when every required child returns `LOW`.

Completed severity rollup is worst-case: `HIGH > MEDIUM > LOW`. `NEEDS_INPUT` and `BLOCKED` are stop states, not severity values, and native child report paths and source verdicts remain visible in the aggregate report. A non-LOW validation-integrity or proof-risk child verdict cannot be hidden by LOW A1 siblings.

Under `conventions/code-quality.md` `## Auditor Scope Boundary` and `## Touched-file ownership`, current severity is raised by findings inside touched files/components, including pre-existing findings. Residuals are preserved separately only for genuinely context-only evidence outside the touched file/component set and do not change the current severity rollup.

Process-tree fanout review is recorded separately as `PASS|FAIL|NEEDS_INPUT|BLOCKED` before downstream gate consumption.

## Finding Normalization

`findings.json` and `findings.md` are both required. `findings.json` is the canonical machine-readable artifact; `findings.md` is the human-readable rendering of the same normalized records.

Each normalized finding records `id`, `source_auditor`, `source_id`, `severity` or stop-state, `metric` / `failure_mode`, `path`, optional location anchors (`function`, `component`, `source_component`, `target_component`, `line_span_or_diff_hunk`), `evidence`, `closure_expectation`, `report_path`, and `blocks_pipeline`.

Residual normalization cites the residual-output schema in `conventions/code-quality.md` `## Auditor Scope Boundary`; record residuals by reference to that schema without duplicating it here. Do not normalize a finding inside a touched file/component as residual merely because it predates the current diff.

Stable IDs use `CQ-<round?>-F<NN>` for canonical pipeline use and `CQ-F<NN>` for standalone bundles. Original child IDs remain in `source_id`.

## Audit-History Ownership

`code-quality.md` reads `audit_history_path` when supplied and may pass relevant history to child auditors as context.

`code-quality.md` does not write canonical audit history. It emits role outputs and normalized findings for the caller or `decision-encoder` to record the round when a revise/review loop continues.

## Rerun And Currentness Semantics

After substantive proposal, touched-surface, or diff revision, all required children rerun. Prior `LOW` reports are stale unless target identity proves exact equality.

Equality predicates include commit SHA, diff base plus head, file list, `touched_surfaces_path` content hash, proposal-path content hash, optional context-path content hashes, child operator file content hashes, and `code_quality_ref` content hash.

## Process-Tree Relationship

`process-tree-auditor` audits the required-child fanout before downstream gate consumption when applicable.

The topology result is separate from the semantic aggregate. Topology review returns `PASS|FAIL|NEEDS_INPUT|BLOCKED`; semantic code-quality aggregation returns `LOW`, `MEDIUM`, `HIGH`, `NEEDS_INPUT:<absolute_artifact_path>`, or `BLOCKED:<reason>`.

## Standalone Mode

Standalone callers supply `code_quality_work_dir`, `repo_root`, `diff_path`, `touched_surfaces_path`, optional refs, and optional `code_quality_ref`.

All standalone artifacts are written under `${code_quality_work_dir}/`. The result is advisory or blocking according to the caller's mode; no implementation phases run automatically.

## Pipeline-Callable Mode

Pipeline-callable callers supply `planning_dir`, `scratch_dir`, `wu_id`, `repo_root`, `touched_surfaces_path`, optional Phase 4 evidence, and diff or equivalent changed-file evidence for selected children. That evidence identifies touched files/components; selected auditors inspect the whole touched file/component required by their operator contract.

Prompts and logs are written under `${scratch_dir}/code-quality/${slug}/`; reports, dispatch manifest, `findings.json`, `findings.md`, aggregate output, and optional expected-process artifacts are written under `${planning_dir}/code-quality/${slug}/`.

Missing required evidence becomes `BLOCKED:<reason>` instead of an inferred pass.

Pipeline-callable mode is valid from Phase 4 proposal-time review, Phase 6 per-component review, and Phase 8 actual-PR-diff review. Phase 8 callers supply `slug=${wu_lower}-phase-8`, `diff_path=<PR-diff>`, `proposal_path=<proposal-cited-by-PR-footer>`, `proof_plan_excerpt=<excerpt>`, `runtime_claim=<claim>`, and any available runtime-artifact evidence. The Phase 8 aggregate path is `${planning_dir}/code-quality/${wu_lower}-phase-8/aggregate-code-quality.md`; its dispatch manifest must mark `validation-integrity-auditor` and `proof-risk-auditor` as `Required=true`.

## Stop Conditions And Escalation

### Standalone mode (advisory)

Standalone callers own whether the aggregate result is advisory or blocking for their local workflow. `LOW` means all required children completed at `LOW`. `MEDIUM` means no required child returned `HIGH` and coupling returned `MEDIUM`; standalone callers may record it as advisory risk or choose to block locally. `HIGH` means at least one required child returned `HIGH` and should drive local revision or escalation.

For standalone use, `NEEDS_INPUT:<absolute_artifact_path>` means the caller surfaces the artifact to the root user or owning gate, and `BLOCKED:<reason>` means the caller fixes unreadable, unwritable, malformed, or missing evidence/report conditions. In both stop states, preserve partial artifacts from children that already ran.

### Pipeline-callable mode (blocking)

Pipeline-callable callers use `~/ai/conventions/code-quality.md` § `Disposition policy` and § `Oscillation signals WU-too-large` as the disposition rule reference. Only LOW passes a pipeline-callable code-quality gate.

`MEDIUM` and `HIGH` block advance, trigger remediation/revise, and require rerun from current evidence. Neither severity is accepted as residual, converted into `NEEDS_INPUT`, or treated as stable allow-advance.

After two consecutive non-converging remediation rounds, the WU decomposes autonomously per `~/ai/conventions/code-quality.md` § `Oscillation signals WU-too-large` instead of attempting a third remediation pass.

`NEEDS_INPUT:<absolute_artifact_path>` and `BLOCKED:<reason>` are stop states the caller surfaces for evidence repair. The caller preserves partial artifacts from children that already ran, repairs the named evidence/report condition, and reruns the gate from current evidence before any advance decision.

## Anti-Scope

- Does not implement any auditor or replace any auditor's procedure.
- Does not redefine A1 or duplicate convention rule descriptions.
- Does not edit child auditor operators.
- Does not include nesting/inline/duplicate auditors; no such child auditors exist in the current operator catalog, so this workflow cannot dispatch them.
- Implementation-pipeline Phase 4 entry is wired in `~/ai/agents/implementation-pipeline-orchestrator.md` § `#### Phase 4 code-quality gate`.
- Does not replace `audit.md`, PR-review gates, or `process-tree-auditor`.
