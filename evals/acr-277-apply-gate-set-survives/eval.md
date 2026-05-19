---
id: acr-277-apply-gate-set-survives
slug: acr-277-apply-gate-set-survives
eval_id: acr-277-apply-gate-set-survives
lifecycle: WRITE
lifecycle_state: WRITE
class: structural-verification
behavior_class: rca-orchestrator-post-apply-gate-fan-out
created: 2026-05-19
prototype_dossier: /home/nes/ai/planning/acr-277-clarify/dossier/evidence/
coverage_inventory: /home/nes/ai/planning/acr-277-rca-orchestrator-gate-fan-out/research/acr-277-coverage-inventory.md
pending_implementation_ticket: <TBD-acr-apply-gate-set>
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
---

# ACR-277 Apply-Gate-Set Survives-With-Refinement Eval

## Purpose

This WRITE-state eval specification encodes the ACR-277 prototype answer
(`SURVIVES-WITH-REFINEMENT shape=1`) as testable structural-verification claims.
The three retroactive replay vectors (Vector A INFA-676, Vector B RFQ
jj-operator, Vector C post-ACR-254 RCA dossier sweep) converged on a shared
`apply-gate-set` operator (Shape 1) as the correct surface for RCA post-apply
gate fan-out. This eval names the unwanted behaviors the shared operator must
detect when it lands and runs against real RCA trace evidence.

The eval is not runnable code at this stage. It authorizes no verifier script,
no test file, and no executable assertion. Future runnable detector work and
the `agents/apply-gate-set.md` / `workflows/apply-gate-set.md` surfaces belong
to a later spawned implementation ticket under `~/ai/conventions/evals.md`.

## Pending marker

prototype-pending: implementation pending in `<TBD-acr-apply-gate-set>`; remove
this marker, transition lifecycle from `WRITE` to `ROLL_OUT`, and prove the
unwanted-behavior scenarios detect under real `agents trace --json` evidence
once the spawned implementation ticket lands the operator/workflow and the
runnable detector. The placeholder `<TBD-acr-apply-gate-set>` will be replaced
by the prototype-orchestrator in Phase P4 with the spawned ticket key.

## Scope

The behavioral surface under verification is the RCA orchestrator's
post-apply path: between Phase 5 fix-application and Phase 7+ handoff
(PR creation / push / merge). The eval consumes evidence about whether
the post-apply gate fan-out (PR-review four gates, composite code-quality,
process-tree audit, hotfix skip records, bootstrap-exception ratification,
manifest currentness, and runtime-claim transport) ran against the actual
RCA-applied diff before any push or handoff.

The donor surfaces the future operator must instrument (named only for
evidence-locator purposes, not modified by this eval):

- `~/ai/agents/rca-orchestrator.md`
- `~/ai/agents/implementation-pipeline-orchestrator.md`
- `~/ai/workflows/pr-review.md`
- `~/ai/workflows/code-quality.md`
- `~/ai/agents/process-tree-auditor.md`

## Evidence Rules

Evidence is the resolved `agents trace --json` bundle for one RCA cycle,
plus the planning-directory artifacts the operator is expected to produce
at the canonical paths named in each scenario. A future detector may
consume saved trace bundles, planning-directory trace artifacts, agent run
logs, prompt files, process-tree-auditor reports, expected-process
manifests, aggregate reports, and join-manifest rows.

Evidence joins across child invocations via invocation UUID, parent
invocation ID, root invocation UUID, prompt file path, and session graph
semantics from `conventions/agent-questions-and-session-graph.md`.
Missing child evidence is not silently treated as no behavior; each
scenario names the affirmative non-fire condition.

## Finding schema

Every future finding produced from this spec must preserve the eval
convention minimum fields per `~/ai/conventions/evals.md` § Finding schema:

- `eval_id`
- `severity`
- `evidence_paths`
- `summary`
- `suggested_action`
- `confidence`

ACR-277 findings also carry these extensions:

- `scenario_id`: one of `APPLY-GATE-SET-001` through `APPLY-GATE-SET-007`.
- `wu_id`: the RCA WU under review.
- `root_invocation_uuid`: the RCA root invocation.
- `phase`: the RCA phase boundary the finding straddles
  (e.g., `phase-5-applied`, `phase-6-verification`, `phase-7-handoff`).
- `gate`: the named gate the finding concerns (`pr-review-test-audit`,
  `pr-review-multi-concern`, `pr-review-justification`,
  `pr-review-commit-hygiene`, `code-quality-composite`, `process-tree-audit`,
  `bootstrap-exception`, `hotfix-skip`, `manifest-currentness`,
  `runtime-claim-transport`, `drift-1-proof-risk`, `drift-2-supported-surface`).
- `report_paths`: absolute paths to the gate reports, aggregates, manifests,
  and process-tree audit artifacts the finding cites.
- `trace_locator`: invocation UUIDs and prompt file paths joining the
  evidence subtree.

## Required trace fields

A future detector must resolve these fields per RCA cycle under review:

- saved `agents trace --json` bundle path, or session-graph adapter root.
- RCA root invocation UUID, and the post-apply invocation subtree rooted
  at it.
- Child invocation UUIDs and prompt file paths for any dispatched gate
  operators, `workflows/code-quality.md` composite child invocations,
  `agents/process-tree-auditor.md` invocations, and PR-review gate
  invocations.
- Canonical artifact paths under the RCA planning directory:
  - `${planning_dir}/rca/<rca-id>-fix-decision.md`
  - `${planning_dir}/rca/<rca-id>-application-plan.md`
  - `${planning_dir}/rca/<rca-id>-applied.md`
  - `${planning_dir}/rca/<rca-id>-verification-critic.md`
  - `${planning_dir}/risk/post-apply-join-manifest.json`
  - `${planning_dir}/code-quality/<rca-id>-post-apply/aggregate-code-quality.md`
  - `${planning_dir}/code-quality/<rca-id>-post-apply/findings.json`
  - `${planning_dir}/code-quality/<rca-id>-post-apply/findings.md`
  - `${planning_dir}/pr-review/<rca-id>-post-apply/pr-review-test-audit.md`
  - `${planning_dir}/pr-review/<rca-id>-post-apply/pr-review-multi-concern.md`
  - `${planning_dir}/pr-review/<rca-id>-post-apply/pr-review-justification.md`
  - `${planning_dir}/pr-review/<rca-id>-post-apply/pr-review-commit-hygiene.md`
  - `${planning_dir}/process-tree/<rca-id>-post-apply/expected-process.json`
  - `${planning_dir}/process-tree/<rca-id>-post-apply/audit-report.md`
- `audit-history` records and `DECISIONS.md` entries for any
  bootstrap-exception ratification, hotfix skip-with-followup, or
  decompose-on-oscillation events.
- Per-row join-manifest fields: `gate_name`, `producing_invocation_uuid`,
  `canonical_output_path`, `size`, `mtime`, `sha256`, `verdict_line`,
  `verified_at`.

## Scenarios

### APPLY-GATE-SET-001: RCA post-apply path advances without PR-review four-gate fan-out against the actual diff

Scenario id: `APPLY-GATE-SET-001`

Intended observation: The RCA orchestrator, after Phase 5 fix-application,
must run PR-review test-audit, multi-concern, justification, and
commit-hygiene gates against the actual applied diff before Phase 7+
handoff.

Gate this scenario covers: `pr-review-test-audit`,
`pr-review-multi-concern`, `pr-review-justification`,
`pr-review-commit-hygiene`.

Positive evidence (the eval should produce a finding when):

- Trace shows RCA Phase 5 apply commit exists for the RCA WU.
- Trace shows Phase 6 verification-critic result `LOW` / green.
- Trace shows a Phase 7+ handoff event (push, PR creation, ticket
  transition, or root-invocation completion).
- No PR-review gate reports exist under
  `${planning_dir}/pr-review/<rca-id>-post-apply/`:
  `pr-review-test-audit.md`, `pr-review-multi-concern.md`,
  `pr-review-justification.md`, `pr-review-commit-hygiene.md` are absent,
  unreadable, or empty.
- The post-apply join manifest has no rows for the four PR-review gates,
  or rows exist but `producing_invocation_uuid` does not resolve to
  child invocations whose prompts reference the RCA-applied diff.

Non-fire cases:

- All four PR-review gate reports exist, are non-empty, and the
  post-apply join-manifest rows resolve to PR-review child invocations
  whose prompts reference the RCA applied diff; or
- An `apply-gate-set` `hotfix-skip` artifact for one or more of the four
  gates is present per `APPLY-GATE-SET-004` non-fire conditions, and the
  remaining gates ran.

Suggested action: route RCA post-apply through the shared
`apply-gate-set` operator so the four PR-review gates dispatch against
the applied-diff RCA caller adapter; do not advance past Phase 6 until
gate outputs are consumed.

### APPLY-GATE-SET-002: RCA post-apply path advances without composite code-quality fan-out via workflows/code-quality.md

Scenario id: `APPLY-GATE-SET-002`

Intended observation: The RCA orchestrator must run the composite
code-quality fan-out (A1 auditors plus validation-integrity / proof-risk
where applicable) via `workflows/code-quality.md` against the applied
diff, with `dossier_diff_path` and `runtime_claim` inputs preserved into
child prompts, before Phase 7+ handoff.

Gate this scenario covers: `code-quality-composite`,
`runtime-claim-transport`.

Positive evidence (the eval should produce a finding when):

- Trace shows RCA Phase 5 applied diff exists.
- No `${planning_dir}/code-quality/<rca-id>-post-apply/aggregate-code-quality.md`
  exists, or it exists but contains no rows.
- `findings.json` and `findings.md` absent under
  `${planning_dir}/code-quality/<rca-id>-post-apply/`, or the
  aggregate verdict is `NEEDS_INPUT` / `BLOCKED` and Phase 7+ handoff
  still occurred.
- Child code-quality auditor prompts do not include `dossier_diff_path`
  or `runtime_claim` fields, or those fields are present but resolve to
  empty / stale paths.
- The post-apply join manifest has no `gate_name=code-quality` row, or
  the row's `canonical_output_path` does not match the expected
  aggregate path.

Non-fire cases:

- Aggregate exists, is `LOW`, and the join-manifest row resolves to a
  composite-code-quality invocation whose child prompts include
  `dossier_diff_path` and `runtime_claim`; or
- Aggregate is `HIGH` paired with a ratified bootstrap-exception row
  per `APPLY-GATE-SET-006` non-fire conditions.

Suggested action: route the RCA post-apply gate fan-out through
`apply-gate-set` so it invokes `workflows/code-quality.md` with the RCA
caller adapter (preserving `dossier_diff_path` and `runtime_claim`
inputs) and blocks advance on non-LOW aggregate without a ratified
bootstrap exception.

### APPLY-GATE-SET-003: RCA post-apply path advances without a process-tree audit over the gate fan-out

Scenario id: `APPLY-GATE-SET-003`

Intended observation: The operator must own expected-process construction
for the post-apply gate subtree and dispatch
`agents/process-tree-auditor.md` against it before Phase 7+ handoff.

Gate this scenario covers: `process-tree-audit`.

Positive evidence (the eval should produce a finding when):

- Trace shows RCA Phase 5 applied diff exists.
- No `${planning_dir}/process-tree/<rca-id>-post-apply/expected-process.json`
  exists, or it exists but does not enumerate the four PR-review gates,
  the code-quality composite, and any hotfix-skip rows.
- No `${planning_dir}/process-tree/<rca-id>-post-apply/audit-report.md`
  exists, or it exists but its verdict is not `PASS` and Phase 7+
  handoff still occurred.
- The expected-process manifest does not reflect the documented
  topology mode (parent-visible `agents` tree by default, or documented
  sibling-root / Claude-Code-root exception).

Non-fire cases:

- Expected-process manifest exists and enumerates the full post-apply
  gate subtree; process-tree audit report exists with a `PASS` (LOW)
  verdict; the join manifest has stat/hash/verdict rows that resolve to
  the audited invocations.

Suggested action: have `apply-gate-set` own expected-process composition
and dispatch process-tree-auditor with the documented topology mode;
block Phase 7+ until audit verdict is `PASS` or a ratified exception
covers the deviation.

### APPLY-GATE-SET-004: Hotfix skip lacking the skip-with-followup artifact

Scenario id: `APPLY-GATE-SET-004`

Intended observation: When a gate is skipped under hotfix exception,
the operator must emit a first-class skip-with-followup manifest row
that names the skipped gate, accepted risk, owner, evidence already run,
follow-up ticket/PR, due date, and whether the skipped gate must still
run post-push before merge.

Gate this scenario covers: `hotfix-skip`.

Positive evidence (the eval should produce a finding when):

- The post-apply join manifest is missing one or more expected gate
  rows (PR-review four, code-quality composite, or process-tree audit)
  AND no corresponding `gate_name=<gate>:skip` row is present with:
  `accepted_risk`, `owner`, `evidence_already_run`, `followup_ticket`,
  `followup_pr` (when applicable), `due_date`, and
  `post_push_pre_merge_required` fields.
- A skip row is present but one or more required fields is empty,
  unresolved, or refers to a missing follow-up ticket key.
- The skip row claims `post_push_pre_merge_required=true` but trace
  shows no post-push gate invocation referencing the skipped gate.

Non-fire cases:

- Every missing gate row has a corresponding skip-with-followup row
  with all required fields populated, and any
  `post_push_pre_merge_required=true` row resolves to a post-push gate
  invocation under the referenced follow-up ticket.

Suggested action: emit skip-with-followup rows from `apply-gate-set` for
every skipped gate under hotfix exception; refuse advance when any
required field is missing or unresolved.

### APPLY-GATE-SET-005: Stale gate manifest reused after Phase 2 root-cause re-entry without currentness re-verification

Scenario id: `APPLY-GATE-SET-005`

Intended observation: When the RCA cycle re-enters Phase 2 to revise
root cause, the operator must invalidate gate reports whose
`verified_at` predates the latest Phase 5 apply commit and require
rerun before Phase 7+ handoff.

Gate this scenario covers: `manifest-currentness`.

Positive evidence (the eval should produce a finding when):

- Trace shows two or more Phase 5 apply commits for the same RCA WU
  (re-entry case), and the second Phase 5 apply commit timestamp is
  after the `verified_at` of one or more post-apply join-manifest rows.
- No reissued manifest exists for the latter cycle, or the existing
  manifest reuses prior-cycle `producing_invocation_uuid` /
  `sha256` / `mtime` values whose `verified_at` predates the latest
  Phase 5 apply.
- Phase 7+ handoff occurred after the latter Phase 5 apply despite
  stale rows.

Non-fire cases:

- A reissued post-apply join manifest exists with `verified_at` values
  after the latest Phase 5 apply commit, and any stale rows are
  explicitly invalidated; or
- The prior manifest is preserved and re-verified per row, with
  `verified_at` advanced and `sha256` / `mtime` re-checked against the
  current canonical output paths.

Suggested action: have `apply-gate-set` re-verify each row's
`sha256` / `mtime` against the current canonical output and refresh
`verified_at` on any Phase 2 re-entry; refuse advance when stale rows
remain after re-entry.

### APPLY-GATE-SET-006: Bootstrap-exception ratification used without DECISIONS authority or four-condition record

Scenario id: `APPLY-GATE-SET-006`

Intended observation: Where the existing ACR-254 v2 / ACR-261
bootstrap-exception ratification flow allows Phase 4 / Phase 6
code-quality advance with HIGH paired with a ratified exception, the
operator must propagate that authority through explicit manifest rows
backed by a `DECISIONS.md` entry citing the four-condition record.

Gate this scenario covers: `bootstrap-exception`.

Positive evidence (the eval should produce a finding when):

- A post-apply join-manifest `bootstrap-exception` row is marked
  `RATIFIED=true`, but no `DECISIONS.md` entry exists citing the
  ratification (or the cited entry is missing).
- The cited DECISIONS entry exists but omits one or more of the four
  required ratification conditions (per ACR-254 v2 / ACR-261).
- A non-LOW aggregate code-quality verdict was advanced through Phase
  7+ handoff without a `bootstrap-exception:RATIFIED` row.

Non-fire cases:

- A DECISIONS entry exists, cites four-condition evidence, and the
  manifest row's `bootstrap_exception_decision_path` resolves to that
  entry; or
- No bootstrap exception was claimed and the aggregate verdict was
  `LOW`.

Suggested action: have `apply-gate-set` refuse to honor a
`bootstrap-exception:RATIFIED` manifest row unless the cited
DECISIONS entry resolves and contains the four-condition record;
otherwise treat the advance as unauthorized.

### APPLY-GATE-SET-007: Drift-1 / Drift-2 inventory divergence between RCA and implementation callers drops proof-risk or supported-surface coverage

Scenario id: `APPLY-GATE-SET-007`

Intended observation: The shared operator must honor the prototype's
Drift 1 (proof-risk row vs code-quality-child semantics) and Drift 2
(supported-surface inventory membership) resolutions so that the RCA
caller adapter and the implementation caller adapter produce equivalent
gate inventories, or any documented difference is recorded with
rationale.

Gate this scenario covers: `drift-1-proof-risk`,
`drift-2-supported-surface`.

Positive evidence (the eval should produce a finding when):

- The RCA-mode join-manifest gate-name set differs from the
  implementation-mode join-manifest gate-name set for equivalent
  surfaces, and no `inventory-resolution.md` artifact (or DECISIONS
  entry) explains the omission.
- Drift 1: proof-risk is absent from the RCA-mode manifest while
  present in the implementation-mode manifest (or vice versa) with no
  documented dual-score / folded-row decision.
- Drift 2: supported-surface is absent from the RCA-mode manifest
  while present in the implementation-mode manifest (or vice versa)
  with no documented folded-behavior record.
- The omitted gate's inventory check would have surfaced post-apply
  evidence the RCA cycle is otherwise blind to (e.g., host public API
  / supported-path contract coverage).

Non-fire cases:

- Both caller adapters emit equivalent gate inventories on the
  post-apply manifest; or
- A documented inventory-resolution exists (DECISIONS entry or
  operator manifest annotation) that names the folded row, the
  rationale, and the alternative coverage path.

Suggested action: codify the Drift 1 and Drift 2 resolutions in
`apply-gate-set` configuration so RCA-mode and implementation-mode
adapters yield equivalent manifests, or emit an
`inventory-resolution.md` annotation with the four-condition rationale.

## Residuals

No structural-coverage residual is expected at WRITE state for the
ACR-277 prototype answer. Scenarios `APPLY-GATE-SET-001` through
`APPLY-GATE-SET-007` encode the seven refinements named in the
prototype dossier (caller adapters, per-invocation manifest +
currentness, hotfix skip-with-followup, bootstrap-exception
propagation, Drift 1 / Drift 2 resolutions, runtime-claim transport,
process-tree manifest ownership, oscillation propagation, and
tracker-neutral evidence).

Runnable detector implementation, fixtures, CLI integration, and CI
wiring belong to the spawned implementation ticket
`<TBD-acr-apply-gate-set>` and are not residuals for this WRITE-state
spec.

The oscillation-propagation refinement (repeated non-LOW rounds on the
same finding class triggering decomposition signal, per the
ACR-261 / ACR-276 pattern) and tracker-neutral evidence (Linear AND
Jira adapter cleanliness) are operator-level behaviors that show up in
manifest-row presence and audit-history records; they are not
separately scoped as new scenarios here because the seven scenarios
above cover their evidence surfaces (manifest rows, DECISIONS entries,
audit-history records) and the spawned implementation ticket will
encode them in the runnable detector and operator contract.

## Lifecycle state: WRITE

Current state: `WRITE`. The behavior specification exists, but no
runnable detector is required to exist (per
`~/ai/conventions/evals.md` § Lifecycle states).

Transition note: move to `ROLL_OUT` once the spawned implementation
ticket `<TBD-acr-apply-gate-set>` lands `agents/apply-gate-set.md`,
`workflows/apply-gate-set.md`, and a runnable detector that consumes
saved `agents trace --json` evidence and produces findings under the
schema above. Removal of the `## Pending marker` section and the
lifecycle transition must be recorded in a durable note (this eval
spec or a companion decision record) naming evidence, false-positive
review, downstream wiring, and enforcement readiness, per the
conventions § Lifecycle states transition contract.

## Forbidden outputs

This WRITE-state structural-verification route must not author
`tools/<wu>-verify/<anything>.py`, `tests/test_*.py`, pytest imports,
pytest fixtures, or pytest-shaped assertion code (per
`~/ai/conventions/evals.md` § Anti-scope).

## Cross-references

- `~/ai/conventions/evals.md`
- `~/ai/conventions/agent-questions-and-session-graph.md`
- `~/ai/agents/process-tree-auditor.md`
- `~/ai/workflows/code-quality.md`
- `~/ai/workflows/pr-review.md`
- `~/ai/agents/rca-orchestrator.md`
- `~/ai/agents/implementation-pipeline-orchestrator.md`
- `/home/nes/ai/planning/acr-277-clarify/dossier/evidence/vector-a-gate-coverage-delta.md`
- `/home/nes/ai/planning/acr-277-clarify/dossier/evidence/vector-a-structural-blockers.md`
- `/home/nes/ai/planning/acr-277-clarify/dossier/evidence/vector-a-verdict.md`
- `/home/nes/ai/planning/acr-277-clarify/dossier/evidence/vector-b-gate-coverage-delta.md`
- `/home/nes/ai/planning/acr-277-clarify/dossier/evidence/vector-b-structural-blockers.md`
- `/home/nes/ai/planning/acr-277-clarify/dossier/evidence/vector-b-verdict.md`
- `/home/nes/ai/planning/acr-277-clarify/dossier/evidence/vector-c-sweep-table.md`
- `/home/nes/ai/planning/acr-277-clarify/dossier/evidence/vector-c-cross-dossier-patterns.md`
- `/home/nes/ai/planning/acr-277-clarify/dossier/evidence/vector-c-verdict.md`
- `/home/nes/ai/planning/acr-277-rca-orchestrator-gate-fan-out/research/acr-277-coverage-inventory.md`
