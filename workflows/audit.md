---
workflow:
  id: audit
workflow_dispatch_contract:
  orchestrator: "root audit coordinator or implementation-pipeline-orchestrator"
  inputs:
    - "target type, target paths or target manifest, target identity, repo/worktree context, scratch or audit work directory"
    - "design-pattern and operator-format references for design targets, runtime evidence for process targets, and merged-base/problem-map evidence for rebase-drift targets"
  expectations:
    - "dispatches applicable audit/checker operators for one current target set and writes a durable audit bundle"
    - "aggregates source reports without replacing their procedures or verdict vocabularies"
    - "preserves audit-history ownership and process-tree topology boundaries"
  outputs:
    - "dispatch manifest, child prompts/logs/reports, normalized findings, aggregate audit report"
    - "role outputs suitable for proposer revision or decision-encoder when the caller enters a revise/review loop"
  non_goals:
    - "does not replace Phase 4 risk gates, PR review gates, workflow-reviewer, or process-tree topology audit"
    - "does not implement fixes, revise target artifacts, or run historical audits unless explicitly invoked"
    - "does not own implementation-pipeline entry-mode policy"
---
# Audit Workflow

## Workflow Dispatch Surface

### Orchestrator

root audit coordinator or implementation-pipeline-orchestrator

### Inputs

- target type, target paths or target manifest, target identity, repo/worktree context, scratch or audit work directory
- design-pattern and operator-format references for design targets, runtime evidence for process targets, and merged-base/problem-map evidence for rebase-drift targets

### Expectations

- dispatches applicable audit/checker operators for one current target set and writes a durable audit bundle
- aggregates source reports without replacing their procedures or verdict vocabularies
- preserves audit-history ownership and process-tree topology boundaries

### Outputs

- dispatch manifest, child prompts/logs/reports, normalized findings, aggregate audit report
- role outputs suitable for proposer revision or decision-encoder when the caller enters a revise/review loop

### Non-goals

- does not replace Phase 4 risk gates, PR review gates, workflow-reviewer, or process-tree topology audit
- does not implement fixes, revise target artifacts, or run historical audits unless explicitly invoked
- does not own implementation-pipeline entry-mode policy; caller procedure lives in `~/ai/agents/implementation-pipeline-orchestrator.md`

## Purpose

Coordinate target-typed audit dispatch across existing design, runtime-process, and rebase-drift auditors. The workflow owns routing, manifest shape, artifact layout, finding normalization, aggregate verdicts, currentness semantics, audit-history handoff, and process-tree handoff.

It does not duplicate the child auditor procedures. It preserves each source operator's contract and verdict vocabulary, then writes a durable audit bundle for a standalone caller or a future pipeline caller.

## Target Typing

| `target_type` | Required target fields | Routed auditor/checker |
|---|---|---|
| `workflow` | `workflow_file` or `target_paths`, `target_ref?`, `repo_root`, `design_patterns_ref`, optional `workflow_index_ref`, optional context | `workflow-design-auditor` |
| `operator` | `operator_file` or `target_paths`, `target_ref?`, `repo_root`, `operator_format_ref`, `design_patterns_ref`, optional context | `agent-design-auditor` |
| `runtime` | `workflow_file`, `run_artifacts` or `runtime_artifacts_path`, `repo_root`, `target_ref`, `process_tree_report_path?`, `expected_process_path?`, `audit_history_path?` | `workflow-process-auditor` |
| `rebase-drift` | `merged_base_diff_path`, `problem_map_path`, `report_path`, optional `worktree_path` or `repo_root`, optional refs/bundle provenance | `rebase-drift-checker` |
| `mixed` | `target_manifest` listing each target item as `workflow`, `operator`, `runtime`, or `rebase-drift` with item-specific required fields | applicable per-item routed auditor/checker |

`process-tree-auditor` is not a target-type auditor in this table. It remains the topology authority for auditing the audit fanout itself before a downstream gated workflow consumes the aggregate.

## Required Inputs

- `target_type=<workflow|operator|runtime|rebase-drift|mixed>`.
- `target_paths=<paths>` or `target_manifest=<path>` for mixed targets.
- `target_ref=<commit|branch|PR|diff|invocation uuid|artifact id>` when available and always when downstream callers expect currentness certification.
- `repo_root=<path>`.
- `worktree_path=<path>` when the caller has a worktree context.
- `scratch_dir=<path>` for pipeline callers; pipeline-callable mode places prompts and logs under `${scratch_dir}/audit/${audit_slug}/`.
- `planning_dir=<path>` for pipeline callers; pipeline-callable mode places reports, manifest, findings, aggregate, and expected-process artifacts under `${planning_dir}/audit/${audit_slug}/`.
- `audit_work_dir=<path>` for standalone callers; standalone mode places every artifact under this single root.
- `design_patterns_ref=<path>`, default `~/ai/conventions/design-patterns.md`.
- `operator_format_ref=<path>` for operator targets, default `~/ai/agents/operator-file-format.md`.
- Runtime evidence fields for runtime targets.
- Drift evidence fields for rebase-drift targets.
- `audit_history_path?`, read-only for the audit workflow and child auditors.
- `mode=<blocking|advisory>`, default `blocking`.

## Output Paths

Default audit slug: `<target_slug>-<target_ref_slug>-audit`, unless caller supplies `audit_slug`.

Pipeline-callable mode splits observability from durable handoff:

- Pipeline-callable observability root: `${scratch_dir}/audit/${audit_slug}/`.
- Pipeline-callable durable root: `${planning_dir}/audit/${audit_slug}/`.
- Prompts and logs go under `${scratch_dir}/audit/${audit_slug}/`.
- Durable reports, manifest, findings, aggregate, and expected-process artifacts go under `${planning_dir}/audit/${audit_slug}/`.

Standalone mode uses one root:

- Standalone root: caller-supplied `${audit_work_dir}/`.
- Standalone mode has no scratch/planning split.

Durable files under `${planning_dir}/audit/${audit_slug}/` for pipeline callers, or under `${audit_work_dir}/` for standalone callers:

- `dispatch-manifest.md`
- `reports/workflow-design-audit.md`
- `reports/agent-design-audit.md`
- `reports/workflow-process-audit.md`
- `reports/rebase-drift.md`
- `findings.json`
- `findings.md`
- `aggregate-audit.md`
- `process-tree-expected.md` when a downstream gated workflow consumes the aggregate

Scratch files under `${scratch_dir}/audit/${audit_slug}/` for pipeline callers, or under `${audit_work_dir}/` for standalone callers:

- `prompts/<auditor>-<target_slug>.prompt.md`
- `logs/<auditor>-<target_slug>.log`

## Dispatch Manifest

Every run writes `dispatch-manifest.md` before child dispatch where possible. The manifest records target identity, target type, mode, selected auditor/checker rows, and output paths.

| Target item | Target type | Auditor/checker | Model | Prompt path | Log path | Report path | Required |
|---|---|---|---|---|---|---|---:|

The `Required` column defaults to `true`; every selected auditor/checker row defaults to `required: true`. A row may be `required: false` only when the target manifest explicitly opts that auditor/checker out for a target item and records a written reason, such as a mixed target where a target item type does not apply to that auditor.

Optionality is a target/evidence applicability statement, not a way to demote a relevant audit. If an auditor/checker applies to the target item under the routing table, the row remains required. An optional row returning `NEEDS_INPUT` or `BLOCKED` does not halt the aggregate and does not prevent required rows from determining `LOW`, `MEDIUM`, `HIGH`, or drift status. Optional row findings, drift signals, `NEEDS_INPUT`, and `BLOCKED` outcomes still flow into `findings.json`, `findings.md`, and `aggregate-audit.md` with `required=false`.

## Per-Target Auditor Routing

Route `workflow` targets to `workflow-design-auditor` with the workflow file, repo root, `design_patterns_ref`, optional context files, optional `audit_history_path`, optional report path, and selected mode.

Route `operator` targets to `agent-design-auditor` with the operator file, repo root, `operator_format_ref`, `design_patterns_ref`, optional context files, optional `audit_history_path`, optional report path, and selected mode.

Route `runtime` targets to `workflow-process-auditor` with the workflow file, run artifacts or runtime artifacts path, repo root, optional `process_tree_report_path`, optional `expected_process_path`, optional `audit_history_path`, report path, target reference, and selected mode.

Route `rebase-drift` targets to `rebase-drift-checker` with `merged_base_diff_path`, `problem_map_path`, `report_path`, optional `worktree_path` or `repo_root`, and optional refs or bundle provenance.

For `mixed` targets, expand `target_manifest` into item-specific dispatch rows. Each item uses the applicable per-item routed auditor/checker and records whether the row is required.

## Aggregate Verdict

The aggregate verdict uses exactly these outcomes:

- `NEEDS_INPUT:<absolute_artifact_path>` if target type, corpus/reference, runtime evidence, drift evidence, output path, target identity, or staleness decision is missing.
- `BLOCKED:<reason>` if required files are unreadable, unwritable, unparseable, or required auditor reports are malformed.
- `HIGH` if any required `LOW`/`MEDIUM`/`HIGH` auditor returns `HIGH`, or if a required `rebase-drift-checker` target returns `drift detected`.
- `MEDIUM` if no required target is `HIGH` or drift-detected and at least one required `LOW`/`MEDIUM`/`HIGH` auditor returns `MEDIUM`.
- `LOW` if every required `LOW`/`MEDIUM`/`HIGH` auditor returns `LOW` and every required rebase-drift target returns `no drift`.

When `rebase-drift-checker` returns `drift detected`, the aggregate rolls up as `HIGH` and preserves the native `drift detected` signal in `reports/rebase-drift.md`, `findings.json`, `findings.md`, and `aggregate-audit.md`.

Process-tree fanout review is recorded separately as `PASS|FAIL|NEEDS_INPUT|BLOCKED` before downstream gate consumption. `workflow-process-auditor` may consume a process-tree report as evidence, but it does not replace `process-tree-auditor`.

## Finding Normalization

`findings.json` and `findings.md` are both required for every dispatch.

`findings.json` is the canonical machine-readable artifact consumed by process-tree review, downstream gates, and any caller that needs stable normalized IDs. `findings.md` is the human-readable rendering of the same normalized finding records and must not contain findings absent from `findings.json`.

Standalone audit bundles use `AD-<round?>-F<NN>` IDs. Audit-history loops use the canonical `R<N>-F<NN>` finding ID convention from `conventions/audit-history.md`.

Each normalized finding records `id`, `source_auditor`, `source_id`, target item, target type, target identity, `required`, severity or drift signal, pattern/violation citation, target location, summary, closure expectation, report path, and whether it blocks pipeline consumption. Original per-auditor IDs remain in `source_id`.

## Audit-History Ownership

`audit.md` reads `audit_history_path` when supplied as read-only input and passes relevant role history to child auditors.

`audit.md` does not write canonical audit history and does not maintain separate per-critic history files.

`audit.md` emits role outputs and normalized findings. The caller or `decision-encoder` records the round in the canonical audit-history file when a revise/review loop continues.

## Rerun And Currentness Semantics

After substantive target artifact revision, all required auditors for affected target items rerun. Prior `LOW` or no-drift reports are stale unless target identity proves exact equality with the reviewed artifact.

In mixed targets, unchanged item `LOW`s may be cited as context, but the aggregate must distinguish current target items from contextual stale reports.

Equality predicates:

- Git source-file targets prove equality with `(target_paths, commit SHA)` when a commit is available, or `(target_paths, branch head SHA at audit time)` for branch-based dispatch. Branch name alone is insufficient.
- PR or diff targets prove equality with `(repo, base SHA, head SHA, file list)`.
- Runtime evidence bundles prove equality with `(workflow_file, runtime_artifacts_path, root invocation UUID when available, generated report timestamp)`.
- Non-git artifacts such as uploaded report PDFs or screenshots prove equality with `(path, content hash, mtime)`, with the dispatch manifest recording the content hash for every non-git artifact target so a later rerun can prove equality rather than trusting path stability.

## Process-Tree Relationship

`process-tree-auditor` is the topology authority. `workflow-process-auditor` may consume process-tree reports as evidence but does not replace topology review.

When an audit fanout is later consumed by a downstream gated workflow, the audit fanout itself is process-tree-audited before downstream gate consumption. The expected process should include child auditor prompts, logs, source reports, dispatch manifest, normalized findings, aggregate output, and any required question or blocked-state artifacts.

The topology review returns `PASS|FAIL|NEEDS_INPUT|BLOCKED` separately from the semantic aggregate.

## Standalone Mode

Standalone callers supply `audit_work_dir`, target fields, references/evidence, and `mode`.

All standalone artifacts are written under `${audit_work_dir}/` with a single root and no scratch/planning split.

The result is advisory or blocking according to `mode`. No automatic implementation phases run.

## Pipeline-Callable Mode

Pipeline-callable callers supply `planning_dir`, `scratch_dir`, WU identity, target fields, and `audit_history_path`.

Prompts and logs are written under `${scratch_dir}/audit/${audit_slug}/`; reports, dispatch manifest, `findings.json`, `findings.md`, aggregate, and expected-process artifacts are written under `${planning_dir}/audit/${audit_slug}/`.

Non-`LOW` aggregate or drift signal seeds proposer/revision work or blocks continuation according to the caller's mode. Wired in `~/ai/agents/implementation-pipeline-orchestrator.md` § Phase 2.5 entry-mode audit dispatch and § Entry-Mode Re-Audit, Audit History, And Termination.

## Stop Conditions And Escalation

- `LOW`: caller may consume the report if any required process-tree fanout audit also passes when applicable.
- `MEDIUM`: caller revises or accepts advisory risk according to its own gate policy; in blocking mode, it does not silently advance.
- `HIGH`: caller revises the target or stops according to the owning workflow.
- `NEEDS_INPUT:<absolute_artifact_path>`: halt until the caller supplies missing evidence or resolves a new value/scope/staleness question. Delegated questions follow `~/ai/conventions/agent-questions-and-session-graph.md`.
- `BLOCKED:<reason>`: halt because required files, reports, or output destinations are unreadable, malformed, or unavailable.
- `process-tree FAIL/NEEDS_INPUT/BLOCKED`: prevents downstream consumption of the audit aggregate until the audit fanout is rerun or repaired.

## Anti-Scope

- Does not replace Phase 4 risk gates.
- Does not replace PR-review gates.
- Does not replace `workflow-reviewer`.
- Does not replace `process-tree-auditor`.
- Does not include implementing fixes.
- Does not include revising target artifacts.
- Does not run historical audits unless explicitly invoked.
- Does not own implementation-pipeline entry-mode policy; `pipeline_entry_mode` caller procedure is wired in `~/ai/agents/implementation-pipeline-orchestrator.md`.
