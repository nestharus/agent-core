---
workflow:
  id: adversarial-qa-stage
  title: Adversarial QA Stage
  description: Stage-only normal-regression and adversarial QA workflow with complete evidence-backed bug reports.
workflow_dispatch_contract:
  orchestrator: "adversarial-qa-driver"
  inputs:
    - "stage_url, health_check_url, use_case_dossier_path, run_id, planning_dir, ticket_system, browser identity, credentials or roles, feature_flags, local_log_paths, and selected ticket-operator routing inputs"
    - "manual or scheduled dispatch context for a staged application surface only"
  expectations:
    - "runs setup, normal-usage regression sweep, adversarial probing, bug report filing, and summary report as separate phases"
    - "files complete evidence-backed bugs and hands their trigger evidence to RCA consumers without fixing stage bugs inside this workflow"
    - "keeps production and prototype branches outside scope"
  outputs:
    - "planning_dir/adversarial-qa/run-id/summary.md"
    - "planning_dir/adversarial-qa/run-id/evidence/ run bundle with screenshots, videos, logs, bug drafts, and per-finding PDFs"
    - "tracker bug URLs or BLOCKED and NEEDS_INPUT artifacts"
  non_goals:
    - "does not run against production"
    - "does not run against prototype branches"
    - "does not fix bugs in stage"
    - "does not add CI jobs, release gates, or ticket-backend API behavior"
---
# Adversarial QA Stage Workflow

## Purpose

Define the stage-only QA pass that walks documented use cases, probes adversarial user behavior, and files complete bugs for downstream RCA. The dispatched operator is `agents/adversarial-qa-driver`.

## Declared roles

- `orchestration`
- `validator`
- `formatter`

## Workflow Dispatch Surface

Dispatch `agents/adversarial-qa-driver` manually or from an explicit schedule against a staged application surface. The workflow requires a stage URL, readiness URL, use-case dossier, run id, planning directory, browser and credential context, feature flags, local log paths when available, and one selected `${ticket_operator}` backend.

This is stage-only. Production is outside scope and must not be targeted. Prototype branches are outside scope and must use their own prototype validation or prototype RCA paths.

## Required Inputs

- `stage_url`
- `health_check_url`
- `use_case_dossier_path`
- `run_id`
- `planning_dir`
- `ticket_system`
- `${ticket_operator}` routing inputs for Linear or JIRA
- Browser identity, credentials or roles, feature flags, and local log paths when available

## Output Paths

- `${planning_dir}/adversarial-qa/${run_id}/summary.md`
- `${planning_dir}/adversarial-qa/${run_id}/evidence/`
- `${planning_dir}/adversarial-qa/${run_id}/bugs/`
- Filed tracker bug URLs, or durable `BLOCKED:` / `NEEDS_INPUT:` artifacts

## Phase Map

The lifecycle has exactly five runtime phases.

## setup

Validate inputs, check `health_check_url`, create the run bundle, record stage environment, browser or agent identity, credentials or role set, feature flags, local log sources, and run metadata.

## normal-usage regression sweep

Walk every documented use case from `use_case_dossier_path` before adversarial work begins. Record pass, fail, blocked, and untested surfaces with evidence links.

## adversarial probing

Probe edge cases, invalid inputs, unexpected navigation, permission boundaries, state transitions, retry behavior, and stress paths that a realistic user could attempt on stage.

## bug report filing

For each finding, file one bug containing expected behavior, actual behavior, deterministic steps to reproduce, UTC timestamp, screenshot or video, local logs when available, environment, labels, severity/priority, run-bundle links, and RCA handoff notes. Use `~/ai/conventions/test-reports.md` for evidence/report convention, including the portable per-finding PDF, and `~/ai/conventions/risk-profile.md` only as the Phase 2.5 bug-ticket minimum that stage QA exceeds.

## summary report

Write the run summary with tested surfaces, untested surfaces, filed bug links, blockers, evidence bundle paths, and release/RCA handoff notes.

## Stop Conditions

- Stop with `BLOCKED:stage-unreachable` when readiness fails for `5xx`, connection-refused, or timeout.
- Stop with `BLOCKED:stage-misconfigured` when readiness returns `4xx`.
- Stop with `NEEDS_INPUT` when credentials, role coverage, use-case dossier, ticket routing, or evidence destination is missing.
- Stop after bug filing and summary writing; fixing defects belongs to downstream implementation or RCA work.

## Anti-Scope

- No production runs.
- No prototype-branch runs.
- No CI, release-gate, cron, or deployment wiring.
- No edits to RCA workflows, RCA operators, `linear-operator.md`, or `jira-operator.md`.
- No bug fixing inside this workflow.

## Handoff Boundary

Filed stage bugs and their evidence bundles are trigger evidence for RCA. The workflow creates deterministic reproduction steps and evidence links; RCA chooses root cause, fix strategy, application plan, and verification.

Release management may consume the summary path as QA evidence, but this workflow does not cut, freeze, promote, tag, or reconcile releases.

## Cross-References

- `agents/adversarial-qa-driver`
- `~/ai/conventions/test-reports.md`
- `~/ai/conventions/risk-profile.md`
- `~/ai/workflows/rca.md`
- `~/ai/workflows/release-management.md`
