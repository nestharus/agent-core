---
workflow:
  id: release-management
workflow_dispatch_contract:
  orchestrator: "release-orchestrator"
  inputs:
    - "repo_root, worktree_path, scratch_dir, and planning_dir for repository context and artifact layout"
    - "release_id, develop_branch_name, main_branch_name, release_branch_name, and optional hotfix_branch_name for branch topology"
    - "release_manifest_path, freeze_window, qa_evidence_path, required_checks_policy, settings_state_or_runbook_ticket, hotfix_policy, promotion_approval, and reconcile_obligations"
  expectations:
    - "runs the release lifecycle in phase order: cut, freeze, hotfix-cherry-pick, promote, tag, reconcile"
    - "keeps settings and Tier-3 approvals human-owned while model-owned release operators handle documented release mechanics"
    - "records release evidence, hotfix exceptions, tags, and reconciliation closure state without project-specific configuration"
  outputs:
    - "release branch, hotfix branch when used, promotion evidence, version tag, and updated release manifest"
    - "settings runbook tickets, QA evidence records, exception records, and reconcile closure evidence"
    - "NEEDS_INPUT question artifacts or BLOCKED stop-state evidence when a human-owned gate or unresolved release risk halts the lifecycle"
  non_goals:
    - "does not author release-orchestrator or release sub-operator files"
    - "does not edit AGENTS.md, project wrappers, conventions, repository settings, or live release infrastructure"
    - "does not replace implementation, PR review, audit, CodeRabbit, or tiered-approval workflows"
---
# Release Management Workflow

## Purpose

Define the project-agnostic release lifecycle for staged releases that flow from `develop` through `release/*`, optional `hotfix/*`, `main`, and a customer-visible `tag`. The workflow gives future release operators a shared phase language, gate-ownership table, evidence surface, philosophy mapping, and forward-reference set before project wrappers bind local branch names or settings runbooks.

The workflow composes specialized release operators. It describes what the lifecycle must prove and where evidence lives; the future `release-orchestrator` dispatches the mechanics and project-local wrappers provide configuration.

## Use When

- A project needs a staged release path with a real freeze window, QA evidence, promotion approval, version tagging, and post-release reconciliation.
- A future release orchestrator needs one workflow contract for cutting `release/*`, handling `hotfix/*` cherry-picks, promoting to `main`, creating the release `tag`, and closing reconcile obligations.
- A project wrapper wants to bind shared inputs such as `develop_branch_name` and `main_branch_name` to local branch names without changing the shared release lifecycle.
- A review or audit needs to verify release gate ownership, human settings boundaries, hotfix override handling, and closure criteria against a single workflow document.

## Do Not Use When

- The work is ordinary implementation, RCA, proposal, test writing, CodeRabbit, PR review, or commit hygiene; use `~/ai/workflows/implementation-pipeline.md`, `~/ai/workflows/coderabbit-loop.md`, or PR-review workflows.
- The target is workflow, operator, runtime, or rebase-drift audit; use `~/ai/workflows/audit.md`.
- The request is only branch/worktree setup for a Work Unit; use the worktree and git conventions, not release-management.
- The request requires live repository settings, branch protection, required checks mutation, customer-visible deployment, or publication approval before the human-owned gate in `~/ai/workflows/tiered-approval.md` clears.
- The request is to author project-specific release wrappers or RFQ-specific configuration; those live in the consuming project.

## Required Inputs

- `repo_root=<path>`: repository root whose release branches, checks, manifests, and evidence are being coordinated.
- `worktree_path=<path>`: checkout or worktree where release validation and operator commands run.
- `scratch_dir=<path>`: transient prompts, logs, question artifacts, and run scratch area.
- `planning_dir=<path>`: durable release planning, reports, evidence records, and closure artifacts.
- `release_id=<id>`: stable identifier for this release lifecycle.
- `develop_branch_name=<branch>`: shared input for the fast integration branch. The project-agnostic default language is `develop`; an RFQ or other project wrapper may bind this to a local name such as `dev`.
- `main_branch_name=<branch>`: shared input for the customer-release source branch, normally `main`.
- `release_branch_name=<branch>`: target `release/*` branch for the frozen release line.
- `hotfix_branch_name?=<branch>`: optional `hotfix/*` branch when the lifecycle needs an emergency branch outside the release branch.
- `release_manifest_path=<path>`: manifest or equivalent evidence ledger for release state, versions, overrides, counters, and closure.
- `freeze_window=<window>`: declared start/end or policy for the slow QA/freeze track.
- `qa_evidence_path=<path>`: evidence bundle showing required checks, QA status, and non-author runnability.
- `required_checks_policy=<path|name>`: expected required checks and branch protection policy for the release branch and promotion path.
- `settings_state_or_runbook_ticket=<path|ticket>`: current settings evidence or the human runbook-shaped ticket needed to change settings.
- `hotfix_policy=<path|name>`: rules for cherry-pick eligibility, blast-radius classification, rehearsal evidence, and override records.
- `promotion_approval=<path|ticket|record>`: approval evidence required before customer-visible promotion, tag, or other Tier-3 action.
- `reconcile_obligations=<path|record>`: list of hotfix, release-line, manifest, and branch-divergence obligations that must close before final closure.

## Phase Map

| Phase | Entry conditions | Exit / transition | Output destination | Phase mechanic owner | Principles |
|---|---|---|---|---|---|
| cut | `release_id`, branch names, manifest, required-checks policy, and settings state are known; `develop_branch_name` is ready to cut. | `release/*` exists, release scope and version readiness are recorded, and settings gaps are either satisfied or represented by a human runbook. Transition to freeze. | `release_branch_name` under `release/*`, `release_manifest_path`, and settings runbook evidence when needed. | `release-orchestrator` dispatches `release-cut-operator`. | Principles: P1, P5, P8, P9, P10 |
| freeze | Cut branch exists, freeze window is active, QA evidence location is ready, and required checks are enforceable or explicitly runbooked. | QA/check evidence passes and promotion approval is ready; failures loop in freeze, route to hotfix-cherry-pick, or block on human-owned settings. | `qa_evidence_path`, updated manifest counters, and optional second-lane runbook artifact. | `release-orchestrator` coordinates freeze evidence and settings boundaries. | Principles: P2, P3, P5, P7, P12, P15, P16 |
| hotfix-cherry-pick | A release-blocking defect or customer-blocking issue appears during freeze or after promotion; `hotfix_policy` allows a cherry-pick path. | Low-blast-radius fixes land with recorded exception evidence; high-blast-radius fixes require rehearsal evidence or `NEEDS_INPUT`; unresolved risk blocks promotion or closure. | `release/*` or `hotfix/*` branch, hotfix exception record, rehearsal evidence, and manifest update. | `release-orchestrator` dispatches `release-hotfix-operator`. | Principles: P6, P11, P12, P13, P15, T1 |
| promote | Freeze evidence is complete, release candidate is approved, hotfix records are reconciled enough for promotion, and Tier-3/customer-visible approval is present when required. | Candidate is merged or otherwise promoted to `main`; failures return to freeze or hotfix-cherry-pick, or stop at human approval. | `main_branch_name`, promotion record, manifest promotion state, and customer-visible approval evidence. | `release-orchestrator` dispatches `release-promote-operator`. | Principles: P2, P4, P8, P10, P11, T5 |
| tag | Promotion to `main` is verified, version identity is final, and manifest finalization has no unresolved customer-visible discrepancy. | Version `tag` is created or recorded; tag failures block release completion until corrected or explicitly escalated. Transition to reconcile. | Release `tag`, final version entry in `release_manifest_path`, and tag evidence. | `release-promote-operator` owns tag mechanics under orchestrator control. | Principles: P2, P4, P10, P11, P16 |
| reconcile | Release is tagged or hotfix work has landed on a release line; `reconcile_obligations` names every divergence and manifest obligation. | Hotfixes are carried back to `develop`, active `release/*` lines are aligned under named invariants, residual exceptions are recorded, and final closure becomes available. | `develop_branch_name`, any active `release/*` line, manifest closure fields, and reconciliation evidence. | `release-orchestrator` dispatches `release-reconcile-operator`. | Principles: P6, P11, P12, P14, P16, T1 |

## Gate Ownership Table

This table cascades from `~/ai/conventions/gate-ownership.md`: model-owned gates validate release design, evidence, and mechanics; human gates own settings, Tier-3 actions, and new value, scope, or trade-off questions. Tier-3 action approval rules live in `~/ai/workflows/tiered-approval.md`.

| Phase | Gate | Owner | Who resolves failure / NEEDS_INPUT | Evidence artifact | Runbook-shaped human ticket? | Philosophy principles |
|---|---|---|---|---|---|---|
| cut | Release-scope and version readiness before `release/*` cut | `release-orchestrator` plus `release-cut-operator` | Orchestrator resolves evidence gaps; settings failures route to the human settings owner with a runbook | `release_manifest_path` cut record and scope/version checklist | Y when settings are missing | P1, P5, P8, P9, P10 |
| cut | Branch protection / required-checks settings for release branch | Human settings owner | Human resolves settings; orchestrator records `NEEDS_INPUT` or blocks until runbook evidence exists | `settings_state_or_runbook_ticket` | Y | P9, P11 |
| freeze | QA, required-checks, and release evidence gate | `release-orchestrator` | Orchestrator loops in freeze, routes to hotfix-cherry-pick, or blocks when evidence is malformed | `qa_evidence_path` and manifest counters | N | P2, P3, P5, P7, P12, P16 |
| freeze | Capacity overflow / second-lane gate | Human settings owner where settings are involved; orchestrator for non-settings evidence | Human resolves settings runbook; orchestrator records expiry and capacity-review trigger | second-lane runbook or capacity-overflow record | Y for settings changes | P9, P13, P15, P16 |
| hotfix-cherry-pick | Hotfix blast-radius classification, rehearsal, override, and cherry-pick gate | `release-hotfix-operator` plus `release-orchestrator` | High-blast-radius failures are `NEEDS_INPUT` or `BLOCKED` until rehearsal and approval evidence exist | hotfix record, rehearsal evidence, override record, and manifest update | Y only when settings or Tier-3 approval is required | P6, P11, P12, P13, P15, T1 |
| promote | QA-approved promotion to customer-release branch | `release-orchestrator` plus `release-promote-operator` | Orchestrator resolves release evidence; human resolves Tier-3 or customer-visible approval | promotion approval, merge/promotion evidence, and manifest state | Y for human approval or settings | P2, P4, P8, P10, P11, T5 |
| tag | Version tag and manifest finalization | `release-promote-operator` plus `release-orchestrator` | Orchestrator resolves version/manifest mismatch; human resolves customer-visible approval if required | version tag, final manifest entry, and tag evidence | Y only for Tier-3 approval gaps | P2, P4, P10, P11, P16 |
| reconcile | Hotfix/release-line reconciliation | `release-reconcile-operator` plus `release-orchestrator` | High-blast-radius unresolved divergence blocks closure until reconciled or explicitly escalated | reconcile report, branch-diff evidence, and manifest closure record | N unless a human-owned exception is required | P6, P11, P12, P14, P16, T1 |
| final closure | Residual-risk and exception-record gate | `release-orchestrator` | Human only for new value, scope, trade-off, or Tier-3 approval; otherwise orchestrator closes or blocks | final release closure record and residual-risk ledger | Y only for human-owned unresolved questions | P7, P11, P13, P16 |

## Cross-references

Forward-referenced release operators:

- `~/ai/agents/release-orchestrator.md` (forward reference; NES-243)
- `~/ai/agents/release-cut-operator.md` (forward reference; NES-244)
- `~/ai/agents/release-hotfix-operator.md` (forward reference; NES-245)
- `~/ai/agents/release-promote-operator.md` (forward reference; NES-246)
- `~/ai/agents/release-reconcile-operator.md` (forward reference; NES-247)

Existing sibling references:

- `~/ai/workflows/implementation-pipeline.md` for phase/gate lifecycle and Phase 6b/6c separation.
- `~/ai/workflows/code-quality.md` for workflow boundary shape.
- `~/ai/workflows/audit.md` for workflow-design and process audit handoff.
- `~/ai/workflows/coderabbit-loop.md` for review-loop convergence boundaries.
- `~/ai/conventions/gate-ownership.md` for human/model gate ownership.
- `~/ai/workflows/tiered-approval.md` for Tier-3 action approval.

## Philosophy Mapping

Source philosophy: `/home/nes/work/rfqautomation-linux/tmp/scratch/release-pipeline/philosophy.md`. Companion decisions: `/home/nes/work/rfqautomation-linux/tmp/scratch/release-pipeline/philosophy-decisions-resolved.md`. The table cites principle IDs and short application statements rather than copying the source prose.

| Workflow surface | Phase / gate / operator | Source principle ids | Source path | How the workflow applies it |
|---|---|---|---|---|
| cut | phase | P1, P5, P8, P9, P10 | `/home/nes/work/rfqautomation-linux/tmp/scratch/release-pipeline/philosophy.md` | Starts a staged release from the integration branch, records the freeze-ready artifact path, and routes settings gaps to a human runbook. |
| freeze | phase | P2, P3, P5, P7, P12, P15, P16 | `/home/nes/work/rfqautomation-linux/tmp/scratch/release-pipeline/philosophy.md` | Makes the slow QA track explicit, requires evidence another engineer can exercise, and records capacity or stress signals in the manifest surface. |
| hotfix-cherry-pick | phase | P6, P11, P12, P13, P15, T1 | `/home/nes/work/rfqautomation-linux/tmp/scratch/release-pipeline/philosophy.md` | Uses cherry-pick discipline for frozen releases, classifies override blast-radius, and requires rehearsal or explicit exception records. |
| promote | phase | P2, P4, P8, P10, P11, T5 | `/home/nes/work/rfqautomation-linux/tmp/scratch/release-pipeline/philosophy.md` | Promotes only the approved staged candidate to the customer-release branch and preserves customer-facing stability. |
| tag | phase | P2, P4, P10, P11, P16 | `/home/nes/work/rfqautomation-linux/tmp/scratch/release-pipeline/philosophy.md` | Finalizes version identity as evidence, not an implicit side effect, and records observable release metadata. |
| reconcile | phase | P6, P11, P12, P14, P16, T1 | `/home/nes/work/rfqautomation-linux/tmp/scratch/release-pipeline/philosophy.md` | Treats hotfix divergence and release-line drift as closure blockers until named invariants and evidence are satisfied. |
| release-orchestrator | operator | P7, P9, P11, P13, P16 | `/home/nes/work/rfqautomation-linux/tmp/scratch/release-pipeline/philosophy.md` | Coordinates gates, records evidence, surfaces only human-owned questions, and keeps observable release stress signals. |
| release-cut-operator | operator | P1, P5, P8, P9, P10 | `/home/nes/work/rfqautomation-linux/tmp/scratch/release-pipeline/philosophy.md` | Owns release branch cut mechanics while preserving settings and documentation boundaries. |
| release-hotfix-operator | operator | P6, P11, P12, P13, P15, T1 | `/home/nes/work/rfqautomation-linux/tmp/scratch/release-pipeline/philosophy.md` | Owns hotfix cherry-pick mechanics, override records, and rehearsal evidence for high-blast-radius paths. |
| release-promote-operator | operator | P2, P4, P8, P10, P11, T5 | `/home/nes/work/rfqautomation-linux/tmp/scratch/release-pipeline/philosophy.md` | Owns approved promotion and tag mechanics without making customer-facing changes collateral cleanup. |
| release-reconcile-operator | operator | P6, P11, P12, P14, P16 | `/home/nes/work/rfqautomation-linux/tmp/scratch/release-pipeline/philosophy.md` | Owns merge-back, branch-divergence, and manifest reconciliation under named invariants. |

## Stop Conditions And Escalation

- `BLOCKED:missing-required-input` when any required input is absent, unreadable, malformed, or contradictory.
- `BLOCKED:settings-runbook-required` when branch protection, required checks, default branch, staging-lane, or other settings state cannot be proven and no human runbook-shaped ticket exists.
- `BLOCKED:freeze-evidence-incomplete` when QA evidence, required checks, non-author runnability, or manifest state does not satisfy freeze exit criteria.
- `BLOCKED:hotfix-rehearsal-missing` when a high-blast-radius hotfix, override, cherry-pick, or reconciliation waiver lacks rehearsal evidence.
- `BLOCKED:promotion-approval-missing` when customer-visible promotion, tag creation, publication, or Tier-3 action lacks approval evidence.
- `BLOCKED:reconcile-open` when unresolved hotfix divergence, release-line mismatch, or manifest discrepancy remains; reconcile blocks closure until obligations close or a human-owned exception is recorded.

`NEEDS_INPUT:<absolute_artifact_path>` is emitted only for human-owned gates: settings, Tier-3 action approval, credentials or access only the user controls, or a new value, scope, or trade-off question. The question artifact is written as `${scratch_dir}/questions/q-<uuidv4>.question.json` and surfaced using the `NEEDS_INPUT:<absolute_artifact_path>` envelope per `~/ai/conventions/agent-questions-and-session-graph.md`.

A release lifecycle is done when promotion and tag evidence are durable, manifest closure fields are current, every hotfix or release-line reconciliation obligation is closed or explicitly excepted, human-owned approvals are recorded, and the final closure gate records residual risk.

## Anti-Scope

- No orchestrator authoring: `release-orchestrator.md` is owned by NES-243, not by this workflow.
- No sub-operator authoring: `release-cut-operator.md`, `release-hotfix-operator.md`, `release-promote-operator.md`, and `release-reconcile-operator.md` are owned by NES-244 through NES-247.
- No `AGENTS.md` routing edits: release operator routing and topology updates are deferred to NES-243.
- No project-specific wrapper, project-local configuration, RFQ-specific manifest schema, or worked example wrapper is authored here.
- No `conventions/*` primary deliverable: this workflow cites existing conventions and keeps release-specific rows local until a later convention WU exists.
- No settings mutation or live release execution: the workflow describes gates and evidence; human runbooks, project wrappers, and future operators execute approved changes.
