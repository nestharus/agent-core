---
workflow:
  id: regression-investigation
workflow_aliases:
  - alias: "flavor: regression-investigation"
    target:
      workflow_id: regression-investigation
      path: "workflows/regression-investigation.md"
workflow_dispatch_contract:
  orchestrator: "regression-investigator"
  inputs:
    - "incident_artifact_path, incident_id, surface_scope_path, investigation_window, repo_root, worktree_path, planning_dir, scratch_dir, and ticket_system"
    - "Linear fields linear_team_key and linear_project_id or Jira fields jira_url, jira_project, and jira_account_email"
    - "optional regression_introduction_sha, fix_sha, evidence_dir, current_ref, historical_ref, and max_followup_tickets"
  expectations:
    - "investigates the codebase conditions around one known regression without replacing RCA, code-quality, audit, or risk-reduction workflows"
    - "dispatches read-only commit-history and pattern-audit children, compares A1 coupling/cohesion evidence at incident commit and trunk, and synthesizes findings"
    - "files or prepares remediation ticket payloads only after findings.json and findings.md are complete"
  outputs:
    - "regression-investigation artifacts under ${planning_dir}/regression-investigation/<incident_id>/"
    - "child prompt and log artifacts under ${scratch_dir}/prompts/ and ${scratch_dir}/logs/"
    - "NEEDS_INPUT question artifacts under ${scratch_dir}/questions/ or BLOCKED stop-state evidence when required inputs are absent"
  non_goals:
    - "does not run application code, mutate source under audit, redefine A1, replace RCA, replace code-quality, replace audit, or replace risk-reduction"
    - "does not implement remediation tickets inline"
---
# Regression Investigation Workflow

## Purpose

Investigate the codebase-risk shape around a known regression. This workflow starts from an incident artifact and asks why the surrounding history, coupling/cohesion, file patterns, implicit knowledge, or review path made the regression possible.

It is adjacent to RCA, code-quality, audit, and risk-reduction. RCA explains what broke; code-quality owns A1 verdicts; audit owns design/process/runtime review; risk-reduction owns aggregate paydown. Regression-investigation composes those signals for one incident and turns the result into durable findings and remediation tickets.

## Workflow Dispatch Surface

### Orchestrator

regression-investigator

### Inputs

- incident_artifact_path, incident_id, surface_scope_path, investigation_window, repo_root, worktree_path, planning_dir, scratch_dir, and ticket_system
- Linear fields linear_team_key and linear_project_id or Jira fields jira_url, jira_project, and jira_account_email
- optional regression_introduction_sha, fix_sha, evidence_dir, current_ref, historical_ref, and max_followup_tickets

### Expectations

- investigates the codebase conditions around one known regression without replacing RCA, code-quality, audit, or risk-reduction workflows
- dispatches read-only commit-history and pattern-audit children, compares A1 coupling/cohesion evidence at incident commit and trunk, and synthesizes findings
- files or prepares remediation ticket payloads only after findings.json and findings.md are complete

### Outputs

- regression-investigation artifacts under `${planning_dir}/regression-investigation/<incident_id>/`
- child prompt and log artifacts under `${scratch_dir}/prompts/` and `${scratch_dir}/logs/`
- NEEDS_INPUT question artifacts under `${scratch_dir}/questions/` or BLOCKED stop-state evidence when required inputs are absent

### Non-goals

- does not run application code, mutate source under audit, redefine A1, replace RCA, replace code-quality, replace audit, or replace risk-reduction
- does not implement remediation tickets inline

## Use When

- A regression is already known and the caller needs codebase-risk archaeology, not another incident narrative.
- RCA, incident-investigator, post-mortem-author, review logs, or fix evidence exists but does not explain the enabling code patterns.
- A future implementation WU needs evidence-backed remediation tickets rather than broad hardening guesses.

## Do Not Use When

- The caller needs the full incident lifecycle, tracker closure, or a post-mortem; use `~/ai/workflows/rca.md`.
- The caller needs a current A1 gate verdict over a proposal or diff; use `~/ai/workflows/code-quality.md`.
- The caller needs workflow, operator, process-tree, or design audit; use `~/ai/workflows/audit.md`.
- The caller needs aggregate project-risk paydown between implementation tickets; use `~/ai/workflows/risk-reduction.md`.

## Required Inputs

- `incident_artifact_path`: incident brief, RCA findings, post-mortem, QA observation, or equivalent artifact naming the regression.
- `incident_id`: stable slug used in output paths.
- `surface_scope_path`: file listing implicated files, components, commands, tickets, or surfaces.
- `investigation_window`: commit range, date range, or bounded history window.
- `repo_root`: repository root for read-only source and git inspection.
- `worktree_path`: worktree used for branch-scoped file reads; source mutation remains out of scope.
- `planning_dir`: durable artifact root.
- `scratch_dir`: prompt, log, and question artifact root.
- `ticket_system`: `linear`, `jira`, or `file-only`.
- `linear_team_key`: required when `ticket_system=linear`.
- `linear_project_id`: optional Linear project binding.
- `jira_url`: required when `ticket_system=jira`.
- `jira_project`: required when `ticket_system=jira`.
- `jira_account_email`: required when `ticket_system=jira`.
- `regression_introduction_sha`: optional suspected introduction commit.
- `fix_sha`: optional fix commit.
- `evidence_dir`: optional captured evidence directory.
- `current_ref`: optional current comparison ref, usually trunk.
- `historical_ref`: optional historical comparison ref, usually the incident commit.
- `max_followup_tickets`: optional cap on remediation ticket creation.

## Output Paths

- `${planning_dir}/regression-investigation/<incident_id>/findings.json`: machine-readable synthesis.
- `${planning_dir}/regression-investigation/<incident_id>/findings.md`: human-readable synthesis.
- `${planning_dir}/regression-investigation/<incident_id>/commit-history.md`: Phase 1 child report.
- `${planning_dir}/regression-investigation/<incident_id>/pattern-findings/`: Phase 3 per-file reports.
- `${planning_dir}/regression-investigation/<incident_id>/pattern-findings/<file-slug>.md`: one pattern-auditor report.
- `${planning_dir}/regression-investigation/<incident_id>/follow-up-tickets.md`: file-only remediation ticket payloads or created-ticket index.
- `${scratch_dir}/prompts/`: child prompt files.
- `${scratch_dir}/logs/`: child dispatch logs.
- `${scratch_dir}/questions/`: `NEEDS_INPUT:<absolute_artifact_path>` question artifacts.

## Phase Map

| Phase | Name | Primary owner | Durable output | Transition |
|---|---|---|---|---|
| 0 | Incident-read | regression-investigator | incident scope record | Phase 1 |
| 1 | commit-history dive | commit-history-analyzer | `${planning_dir}/regression-investigation/<incident_id>/commit-history.md` | Phase 2 |
| 2 | A1 coupling/cohesion at incident commit and trunk | code-quality/A1 auditors | historical/current A1 comparison notes | Phase 3 |
| 3 | pattern audit | pattern-auditor | `${planning_dir}/regression-investigation/<incident_id>/pattern-findings/` | Phase 4 |
| 4 | implicit-knowledge dive | regression-investigator | implicit invariant notes | Phase 5 |
| 5 | risk synthesis | regression-investigator | findings.json and findings.md | Phase 6 |
| 6 | remediation track | linear-operator, jira-operator, or file-only handoff | follow-up remediation ticket payloads | wrap |

The Phase Map covers commit-history dive, A1 coupling/cohesion comparison at incident commit and trunk, pattern audit, implicit-knowledge dive, risk synthesis, and remediation track ticket handoff.

## Phase 0 - Incident-read

### Entry Conditions

`incident_artifact_path`, `incident_id`, `surface_scope_path`, `repo_root`, `planning_dir`, and `scratch_dir` are present and readable or writable as appropriate.

### Actions

Read `incident_artifact_path` first. Extract symptom, affected surface, known or suspected `regression_introduction_sha`, known `fix_sha`, evidence pointers, and the bounded `investigation_window`. Read `surface_scope_path` and normalize each implicated file or surface into a slug for child artifacts.

### Outputs

- Incident scope summary under `${planning_dir}/regression-investigation/<incident_id>/`.
- Missing-evidence questions under `${scratch_dir}/questions/` when the artifact cannot name an answerable regression.

### Stop Or Transition

Transition to Phase 1 when the incident and surface scope are answerable. Stop with `BLOCKED:missing-incident-scope` or emit `NEEDS_INPUT:<absolute_artifact_path>` for user-owned incident ambiguity.

## Phase 1 - Commit-history dive

### Entry Conditions

Phase 0 identified `investigation_window`, surface scope, and the output path `${planning_dir}/regression-investigation/<incident_id>/commit-history.md`.

### Actions

Write `${scratch_dir}/prompts/regression-investigation-phase-1-commit-history.md` with `investigation_window`, `repo_root`, `surface_scope_path`, `regression_introduction_sha`, `fix_sha`, and `output_path=${planning_dir}/regression-investigation/<incident_id>/commit-history.md`.

`agents -a ~/ai/agents/commit-history-analyzer.md -p ${repo_root} -f ${scratch_dir}/prompts/regression-investigation-phase-1-commit-history.md 2>&1 | tee ${scratch_dir}/logs/regression-investigation-phase-1-commit-history.log`

Refuse to advance unless `${planning_dir}/regression-investigation/<incident_id>/commit-history.md` exists, is readable, and the log records `WROTE:`.

### Outputs

- `${planning_dir}/regression-investigation/<incident_id>/commit-history.md`
- Prompt and log artifacts in `${scratch_dir}/prompts/` and `${scratch_dir}/logs/`.

### Stop Or Transition

Transition to Phase 2 when the commit-history artifact is present. Preserve child `NEEDS_INPUT:` or stop with `BLOCKED:commit-history-missing` if the artifact is absent.

## Phase 2 - Coupling/cohesion at incident commit and trunk

### Entry Conditions

Phase 1 completed or supplied enough commit context to choose `historical_ref` and `current_ref`. The run can read `~/ai/workflows/code-quality.md` and A1 auditors without redefining them.

### Actions

Compare A1 evidence at the incident commit and trunk. This phase references `~/ai/workflows/code-quality.md`, `~/ai/agents/cohesion-auditor.md`, `~/ai/agents/coupling-auditor.md`, `~/ai/agents/function-classification-auditor.md`, and `~/ai/agents/push-pull-auditor.md`. Use read-only snapshots such as `git show <ref>:<path>` or prepared bundles; do not checkout or mutate the active worktree.

`agents -a ~/ai/agents/cohesion-auditor.md -p ${repo_root} -f ${scratch_dir}/prompts/regression-investigation-phase-2-cohesion.md 2>&1 | tee ${scratch_dir}/logs/regression-investigation-phase-2-cohesion.log`

### Outputs

- Historical/current A1 comparison notes under `${planning_dir}/regression-investigation/<incident_id>/`.
- Prompt and log artifacts under `${scratch_dir}/prompts/` and `${scratch_dir}/logs/`.

### Stop Or Transition

Transition to Phase 3 when A1 evidence is present or explicitly marked unavailable. Stop with `BLOCKED:a1-evidence-unreadable` when required snapshot inputs cannot be read.

## Phase 3 - Pattern audit

### Entry Conditions

Phase 0 supplied one or more implicated files or surfaces, and Phase 2 either produced A1 evidence or recorded why it is unavailable.

### Actions

For each scoped file, write `${scratch_dir}/prompts/regression-investigation-phase-3-pattern-audit-<file-slug>.md` with `surface_path`, `surface_context`, `repo_root`, `planning_dir`, `incident_id`, `incident_artifact_path`, A1 evidence pointers, and `output_path=${planning_dir}/regression-investigation/<incident_id>/pattern-findings/<file-slug>.md`.

`agents -a ~/ai/agents/pattern-auditor.md -p ${repo_root} -f ${scratch_dir}/prompts/regression-investigation-phase-3-pattern-audit-<file-slug>.md 2>&1 | tee ${scratch_dir}/logs/regression-investigation-phase-3-pattern-audit-<file-slug>.log`

Refuse to advance unless `${planning_dir}/regression-investigation/<incident_id>/pattern-findings/<file-slug>.md` exists for every required file or a `BLOCKED:`/`NEEDS_INPUT:` child result has been preserved.

### Outputs

- `${planning_dir}/regression-investigation/<incident_id>/pattern-findings/<file-slug>.md`
- One prompt and log pair per audited file.

### Stop Or Transition

Transition to Phase 4 when required pattern reports are present. Stop with `BLOCKED:pattern-findings-missing` if required reports are absent.

## Phase 4 - Implicit-knowledge dive

### Entry Conditions

Commit-history, A1 comparison, and pattern-finding artifacts are readable or have explicit caveats.

### Actions

The regression-investigator reads child outputs together and identifies unwritten invariants, developer-only assumptions, tribal knowledge, missing contracts, and historical review cues that explain the regression-enabling gap in understanding.

### Outputs

- Implicit-knowledge notes folded into the Phase 5 synthesis.
- Optional question artifacts under `${scratch_dir}/questions/` when a business rule or intended behavior cannot be inferred from evidence.

### Stop Or Transition

Transition to Phase 5 when each knowledge gap is either evidenced, caveated, or represented as `NEEDS_INPUT:<absolute_artifact_path>`.

## Phase 5 - Risk synthesis

### Entry Conditions

All prior phase outputs are readable or explicitly caveated.

### Actions

Synthesize `commit-history.md`, per-file `pattern-findings/`, A1 comparison notes, implicit-knowledge notes, and incident evidence into normalized findings. Each finding names `incident_id`, `surface_path`, `risk_category`, `severity`, `evidence_paths`, `gap_in_understanding`, `suggested_remediation`, and `disposition`.

### Outputs

- `${planning_dir}/regression-investigation/<incident_id>/findings.json`
- `${planning_dir}/regression-investigation/<incident_id>/findings.md`

### Stop Or Transition

Transition to Phase 6 when `findings.json` and `findings.md` exist. Stop at value-zero when no evidence-backed findings remain, writing empty findings with a clear no-action disposition.

## Phase 6 - Remediation track

### Entry Conditions

Phase 5 produced `findings.json` and `findings.md`, and `ticket_system` is `linear`, `jira`, or `file-only`.

### Actions

For `ticket_system=linear`, prepare a prompt for `~/ai/agents/linear-operator.md`. For `ticket_system=jira`, prepare a prompt for `~/ai/agents/jira-operator.md`. For `file-only`, write ticket payloads to `${planning_dir}/regression-investigation/<incident_id>/follow-up-tickets.md`.

`agents -a ~/ai/agents/linear-operator.md -p ${repo_root} -f ${scratch_dir}/prompts/regression-investigation-phase-6-linear-ticket.md 2>&1 | tee ${scratch_dir}/logs/regression-investigation-phase-6-linear-ticket.log`

`agents -a ~/ai/agents/jira-operator.md -p ${repo_root} -f ${scratch_dir}/prompts/regression-investigation-phase-6-jira-ticket.md 2>&1 | tee ${scratch_dir}/logs/regression-investigation-phase-6-jira-ticket.log`

### Outputs

- `${planning_dir}/regression-investigation/<incident_id>/follow-up-tickets.md`
- Created ticket keys or file-only payloads linked to finding ids.

### Stop Or Transition

Complete when all accepted findings are filed, capped by `max_followup_tickets`, or recorded as file-only. Stop with `BLOCKED:ticket-handoff-failed` when the selected ticket operator cannot file or record payloads.

## Wrap Relationship To Implementation Pipeline

Regression-investigation does not implement remediation. Any accepted follow-up tickets enter `~/ai/workflows/implementation-pipeline.md` as ordinary WUs with their own tests, proposal, risk gates, CodeRabbit, PR review, and ticket closure. This workflow supplies evidence and ticket payloads only.

## Stop Conditions

- Success: `findings.json`, `findings.md`, and any follow-up ticket payloads are written or explicitly skipped at value-zero.
- `BLOCKED:` when required inputs, child artifacts, or ticket handoff evidence are missing.
- `NEEDS_INPUT:` when a scope, intended-behavior, or ticketing decision is user-owned and cannot be resolved from artifacts.
- Value-zero termination is allowed when the investigation produces no evidence-backed findings; write the no-finding state rather than inventing remediation.

## Anti-Scope

- Regression-investigation does not replace `~/ai/workflows/rca.md`; RCA remains the incident lifecycle and post-mortem owner.
- Regression-investigation does not replace `~/ai/workflows/code-quality.md`; code-quality and A1 auditors remain the metric owners.
- Regression-investigation is distinct from `~/ai/workflows/audit.md`; audit remains responsible for workflow/operator/process review.
- Regression-investigation is distinct from `~/ai/workflows/risk-reduction.md`; risk-reduction remains aggregate between-WU paydown.
- No A1 redefinition and does not redefine A1 metrics.
- No application-code runs and no live application runs.
- No source mutation under audit and no source-code edits under audit.

## Cross-References

- `~/ai/workflows/rca.md`
- `~/ai/workflows/code-quality.md`
- `~/ai/workflows/audit.md`
- `~/ai/workflows/risk-reduction.md`
- `~/ai/workflows/implementation-pipeline.md`
- `~/ai/workflows/agents-cli.md`
- `~/ai/conventions/code-quality.md`
- `~/ai/conventions/risk-profile.md`
- `~/ai/conventions/workflow-aliases.md`
- `~/ai/agents/incident-investigator.md`
- `~/ai/agents/post-mortem-author.md`
- `~/ai/agents/linear-operator.md`
- `~/ai/agents/jira-operator.md`
