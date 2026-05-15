---
workflow:
  id: code-quality
workflow_dispatch_contract:
  orchestrator: "implementation-pipeline-orchestrator Phase 4 caller, ad-hoc developer, or PR-review caller"
  inputs:
    - "repo_root, diff_path, touched_surfaces_path, scratch_dir, and planning_dir for pipeline-callable artifact layout"
    - "optional Phase 4 evidence: proposal_path, problem_map_path, risk_profile_path, and wu_id"
    - "optional refs and inventories: base_ref, head_ref, changed_files_path, changed_functions_path, code_trace_paths, and code_quality_ref"
  expectations:
    - "dispatches each auditor named in conventions/code-quality.md ## Auditor Set and writes a durable code-quality bundle"
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
- optional Phase 4 evidence: proposal_path, problem_map_path, risk_profile_path, and wu_id
- optional refs and inventories: base_ref, head_ref, changed_files_path, changed_functions_path, code_trace_paths, and code_quality_ref

### Expectations

- dispatches each auditor named in `conventions/code-quality.md` `## Auditor Set` and writes a durable code-quality bundle
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

Coordinate a composite gate over the A1 code-quality surface by treating `~/ai/conventions/code-quality.md` as the rule reference and the existing child auditors as the executable procedures. The workflow applies `conventions/code-quality.md` `## Auditor Scope Boundary` and dispatches each auditor named in `conventions/code-quality.md` `## Auditor Set`. The workflow owns dispatch, artifact layout, finding normalization, aggregate verdicts, currentness semantics, audit-history handoff, and process-tree handoff for callers that need one code-quality result.

## Declared roles

`orchestration`, `validator`, `mapper`

## Declared roles (mirror)

`~/ai/conventions/code-quality.md` remains the canonical rule source for declared-role cohesion scoring.

- LOW when actual classifications are a subset of the declared role set.
- HIGH when actual classifications exceed the declared role set or include classifications outside the declared role set.

## Use When

- An implementation-pipeline Phase 4 caller has proposal, touched-surface, and diff or equivalent change evidence and needs one composite code-quality gate.
- A PR-review caller has branch or PR diff evidence and wants normalized A1 findings from the supported auditor fanout.
- An ad-hoc developer wants to run the same composite review over a local diff and touched-surface package without entering the implementation pipeline.

## Do Not Use When

- The target is workflow design, operator design, runtime procedure adherence, or rebase drift; use `~/ai/workflows/audit.md` for those surfaces.
- The caller needs PR-review's distinct multi-concern, justification, or commit-hygiene gates.
- The caller needs topology verification of an agent run; `process-tree-auditor` remains the topology authority.

## Required Inputs

- `repo_root=<path>`: required for Phase 4, PR-review, and ad-hoc invocations; points to the repository being reviewed.
- `diff_path=<path>`: required for PR-review and ad-hoc invocations, and required in Phase 4 when A4/A5 are selected; contains a unified diff or equivalent text change artifact.
- `touched_surfaces_path=<path>`: required for Phase 4, PR-review, and ad-hoc invocations; lists changed files, module/package/component labels, and known component boundaries.
- `scratch_dir=<path>`: required for Phase 4 pipeline-callable invocations; stores prompts and logs.
- `planning_dir=<path>`: required for Phase 4 pipeline-callable invocations; stores durable reports, findings, manifest, and aggregate output.
- `proposal_path=<path>`: optional Phase 4 evidence unless A6 children are selected before implementation, then required.
- `problem_map_path=<path>`: optional Phase 4 evidence unless A6 children are selected before implementation, then required.
- `risk_profile_path=<path>`: optional Phase 4 evidence unless A6 children are selected before implementation, then required.
- `wu_id=<id>`: required for Phase 4 pipeline-callable invocations; optional provenance for PR-review and ad-hoc invocations.
- `base_ref=<ref>`: optional for Phase 4, PR-review, and ad-hoc invocations; records diff provenance.
- `head_ref=<ref>`: optional for Phase 4, PR-review, and ad-hoc invocations; records diff provenance.
- `changed_files_path=<path>`: optional inventory for Phase 4, PR-review, and ad-hoc invocations.
- `changed_functions_path=<path>`: optional inventory for A5 and any caller that can provide function-level change evidence.
- `code_trace_paths=<paths>`: optional evidence for coupling review when traces or symbol maps exist.
- `code_quality_ref=<path>`: optional reference override; defaults to `~/ai/conventions/code-quality.md`.

Dispatch prompts separate target evidence from context evidence under `conventions/code-quality.md` `## Auditor Scope Boundary`: `diff_path` or equivalent WU-owned change evidence is target evidence for implemented-work review, while proposal, problem-map, risk-profile, touched-surface, trace, and inventory paths are context evidence.

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

When code-quality runs in pipeline-callable fanout mode and a downstream gated workflow consumes its aggregate, child dispatch and completion inherit `~/ai/workflows/agents-cli.md` § `Long-running agents`, including the ACR-203 sentinel, bounded-timeout, and cleanup-trap backstop.

Dispatch each auditor named in `conventions/code-quality.md` `## Auditor Set`; the table below is the operational manifest for the current canonical set.

| Concern | Auditor | Model | Prompt path | Log path | Report path | Required |
|---|---|---|---|---|---|---:|
| A4 | push-pull-auditor | gpt-high | `${scratch_dir}/code-quality/${slug}/prompts/push-pull-auditor.prompt.md` | `${scratch_dir}/code-quality/${slug}/logs/push-pull-auditor.log` | `${planning_dir}/code-quality/${slug}/reports/push-pull-auditor.md` | true |
| A5 | function-classification-auditor | gpt-high | `${scratch_dir}/code-quality/${slug}/prompts/function-classification-auditor.prompt.md` | `${scratch_dir}/code-quality/${slug}/logs/function-classification-auditor.log` | `${planning_dir}/code-quality/${slug}/reports/function-classification-auditor.md` | true |
| A6 | cohesion-auditor | gpt-high | `${scratch_dir}/code-quality/${slug}/prompts/cohesion-auditor.prompt.md` | `${scratch_dir}/code-quality/${slug}/logs/cohesion-auditor.log` | `${planning_dir}/code-quality/${slug}/reports/cohesion-auditor.md` | true |
| A6 | coupling-auditor | gpt-high | `${scratch_dir}/code-quality/${slug}/prompts/coupling-auditor.prompt.md` | `${scratch_dir}/code-quality/${slug}/logs/coupling-auditor.log` | `${planning_dir}/code-quality/${slug}/reports/coupling-auditor.md` | true |

`Required=false` is allowed only with a written applicability reason in the manifest. Optionality records evidence applicability; it is not a way to demote relevant A1 review.

## Per-Concern Auditor Routing

### A4 - Push-vs-pull system coupling

Auditor path: `~/ai/agents/push-pull-auditor.md`. Model: `gpt-high`.

- Required inputs: `repo_root`, `diff_path`, `output_path`.
- Optional inputs: `base_ref`, `head_ref`, `changed_files_path`, `proposal_path`, `problem_map_path`, `risk_profile_path`, `code_quality_ref`.

### A5 - Function classification

Auditor path: `~/ai/agents/function-classification-auditor.md`. Model: `gpt-high`.

- Required inputs: `repo_root`, `diff_path`, `output_path`.
- Optional inputs: `changed_functions_path`, `proposal_path`, `problem_map_path`, `risk_profile_path`, `code_quality_ref`.

### A6 - Cohesion

Auditor path: `~/ai/agents/cohesion-auditor.md`. Model: `gpt-high`.

- Required inputs: `repo_root`, `planning_dir`, `wu_id`, `touched_surfaces_path`, and `diff_path` or equivalent WU-owned change evidence.
- Context inputs: `proposal_path`, `problem_map_path`, `risk_profile_path`, `output_path`.

### A6 - Coupling

Auditor path: `~/ai/agents/coupling-auditor.md`. Model: `gpt-high`.

- Required inputs: `repo_root`, `planning_dir`, `wu_id`, `touched_surfaces_path`, and `diff_path` or equivalent WU-owned change evidence.
- Context inputs: `proposal_path`, `problem_map_path`, `risk_profile_path`, `code_trace_paths`, `output_path`.

## Aggregate Verdict

The aggregate verdict uses these outcomes:

- `NEEDS_INPUT:<absolute_artifact_path>` when any required child returns `NEEDS_INPUT`.
- `BLOCKED:<reason>` when required files are unreadable, unwritable, malformed, or required child auditor reports are malformed.
- `HIGH` when any required child returns `HIGH`.
- `MEDIUM` when coupling returns `MEDIUM` and no child returns `HIGH`.
- `LOW` when every required child returns `LOW`.

Completed severity rollup is worst-case: `HIGH > MEDIUM > LOW`. Coupling is the only child whose native vocabulary currently includes MEDIUM. `NEEDS_INPUT` and `BLOCKED` are stop states, not severity values, and native child report paths and source verdicts remain visible in the aggregate report.

Under `conventions/code-quality.md` `## Auditor Scope Boundary`, current severity is raised by diff-owned findings; residuals are preserved separately and do not change the current severity rollup.

Process-tree fanout review is recorded separately as `PASS|FAIL|NEEDS_INPUT|BLOCKED` before downstream gate consumption.

Downstream consumption also depends on the pipeline-callable fanout completion contract in `~/ai/workflows/agents-cli.md` § `Long-running agents`; the semantic aggregate is not consumable while completion evidence or required child artifacts are missing or stale.

## Finding Normalization

`findings.json` and `findings.md` are both required. `findings.json` is the canonical machine-readable artifact; `findings.md` is the human-readable rendering of the same normalized records.

Each normalized finding records `id`, `source_auditor`, `source_id`, `severity` or stop-state, `metric` / `failure_mode`, `path`, optional location anchors (`function`, `component`, `source_component`, `target_component`, `line_span_or_diff_hunk`), `evidence`, `closure_expectation`, `report_path`, and `blocks_pipeline`.

Residual normalization cites the residual-output schema in `conventions/code-quality.md` `## Auditor Scope Boundary`; record residuals by reference to that schema without duplicating it here.

Stable IDs use `CQ-<round?>-F<NN>` for canonical pipeline use and `CQ-F<NN>` for standalone bundles. Original child IDs remain in `source_id`.

## Audit-History Ownership

`code-quality.md` reads `audit_history_path` when supplied and may pass relevant history to child auditors as context.

`code-quality.md` does not write canonical audit history. It emits role outputs and normalized findings for the caller or `decision-encoder` to record the round when a revise/review loop continues.

## Rerun And Currentness Semantics

After substantive proposal, touched-surface, or diff revision, all required children rerun. Prior `LOW` reports are stale unless target identity proves exact equality.

Equality predicates include commit SHA, diff base plus head, file list, `touched_surfaces_path` content hash, proposal-path content hash, optional context-path content hashes, child operator file content hashes, and `code_quality_ref` content hash.

## Process-Tree Relationship

`process-tree-auditor` audits the four-child fanout before downstream gate consumption when applicable.

That downstream fanout handoff uses `~/ai/workflows/agents-cli.md` § `Long-running agents` for completion evidence; this workflow owns the semantic aggregate, while the canonical agents-cli contract owns the gated-fanout completion backstop.

The topology result is separate from the semantic aggregate. Topology review returns `PASS|FAIL|NEEDS_INPUT|BLOCKED`; semantic code-quality aggregation returns `LOW`, `MEDIUM`, `HIGH`, `NEEDS_INPUT:<absolute_artifact_path>`, or `BLOCKED:<reason>`.

## Standalone Mode

Standalone callers supply `code_quality_work_dir`, `repo_root`, `diff_path`, `touched_surfaces_path`, optional refs, and optional `code_quality_ref`.

All standalone artifacts are written under `${code_quality_work_dir}/`. The result is advisory or blocking according to the caller's mode; no implementation phases run automatically.

## Pipeline-Callable Mode

Pipeline-callable callers supply `planning_dir`, `scratch_dir`, `wu_id`, `repo_root`, `touched_surfaces_path`, optional Phase 4 evidence, and diff or equivalent change evidence for selected diff-first children.

Prompts and logs are written under `${scratch_dir}/code-quality/${slug}/`; reports, dispatch manifest, `findings.json`, `findings.md`, aggregate output, and optional expected-process artifacts are written under `${planning_dir}/code-quality/${slug}/`.

Missing required evidence becomes `BLOCKED:<reason>` instead of an inferred pass.

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
- Does not edit child auditor operators; NES-235 captures cleanup of stale bundled A6 references.
- Does not include nesting/inline/duplicate auditors; no such child auditors exist in the current operator catalog, so this workflow cannot dispatch them. <!-- INTENTIONAL: this workflow coordinates existing child auditors only; new auditor creation belongs to a separate operator-design change before workflow fanout can include it. -->
- Implementation-pipeline Phase 4 entry is wired in `~/ai/agents/implementation-pipeline-orchestrator.md` § `#### Phase 4 code-quality gate`.
- Does not replace `audit.md`, PR-review gates, or `process-tree-auditor`.
