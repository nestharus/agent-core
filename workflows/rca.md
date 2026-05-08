---
workflow:
  id: rca
workflow_dispatch_contract:
  orchestrator: "Work Manager or root RCA coordinator"
  inputs:
    - "incident handle or incident context, incident brief path or enough framing to create one, evidence directory, repo_root, scratch_dir, and planning_dir"
    - "ticket_system linear or jira with existing incident issue key or create context, plus Linear or Jira operator inputs for tracker filing and comments"
    - "action_item_policy file-only, file-and-handoff, or file-and-dispatch, plus action-item worktree/planning/scratch path policy when implementation WUs are dispatched"
  expectations:
    - "runs the full RCA lifecycle from incident framing through evidence, tracker filing, investigation, post-mortem, action-item tickets, runbooks, tracker comments, and close-or-pending decision"
    - "dispatches incident-investigator and post-mortem-author as separate operator invocations and uses ticket operators for tracker side effects"
    - "wraps implementation-pipeline action-item WUs without replacing implementation review or PR review gates"
  outputs:
    - "incident brief, evidence pack, findings, post-mortem, action-item index, runbooks, tracker comment/link evidence, and RCA close or pending record"
    - "created or identified incident tracker key and action-item ticket keys"
    - "NEEDS_INPUT question artifacts or BLOCKED stop-state evidence when RCA cannot proceed"
  non_goals:
    - "does not mutate source code, git state, applications, production, or external systems except documented tracker create/comment operations"
    - "does not edit incident-investigator, post-mortem-author, ticket operators, or implementation-pipeline-orchestrator"
    - "does not replace implementation-pipeline Phase 4, Phase 7, Phase 8, CodeRabbit, or PR-review gates"
---
# RCA Workflow

## Purpose

Coordinate a full incident-to-close root-cause analysis lifecycle. The workflow turns an incident handle or brief into a durable evidence pack, tracker record, investigation findings, post-mortem, action-item ticket index, runbook outputs, tracker comments, and a final close-or-pending record.

RCA is an outer workflow. It dispatches existing operators for investigation, post-mortem authoring, and tracker side effects, then records enough manifest state for resume and process review without mutating source code or replacing implementation delivery gates.

## Workflow Dispatch Surface

### Orchestrator

Work Manager or root RCA coordinator

### Inputs

- incident handle or incident context, incident brief path or enough framing to create one, evidence directory, repo_root, scratch_dir, and planning_dir
- ticket_system linear or jira with existing incident issue key or create context, plus Linear or Jira operator inputs for tracker filing and comments
- action_item_policy file-only, file-and-handoff, or file-and-dispatch, plus action-item worktree/planning/scratch path policy when implementation WUs are dispatched

### Expectations

- runs the full RCA lifecycle from incident framing through evidence, tracker filing, investigation, post-mortem, action-item tickets, runbooks, tracker comments, and close-or-pending decision
- dispatches incident-investigator and post-mortem-author as separate operator invocations and uses ticket operators for tracker side effects
- wraps implementation-pipeline action-item WUs without replacing implementation review or PR review gates

### Outputs

- incident brief, evidence pack, findings, post-mortem, action-item index, runbooks, tracker comment/link evidence, and RCA close or pending record
- created or identified incident tracker key and action-item ticket keys
- NEEDS_INPUT question artifacts or BLOCKED stop-state evidence when RCA cannot proceed

### Non-goals

- does not mutate source code, git state, applications, production, or external systems except documented tracker create/comment operations
- does not edit incident-investigator, post-mortem-author, ticket operators, or implementation-pipeline-orchestrator
- does not replace implementation-pipeline Phase 4, Phase 7, Phase 8, CodeRabbit, or PR-review gates


## Use When

- A caller needs the complete RCA path: incident framing, evidence pack assembly, tracker filing, investigation, post-mortem synthesis, severity-ordered action-item tickets, runbooks for unverifiable or customer-side factors, tracker comments, and a close-or-pending decision.
- An incident already has a tracker key but lacks durable RCA artifacts and action-item follow-through.
- Findings or a post-mortem already exist and the run needs a later-phase entry with explicit provenance and currentness checks.
- Implementation-worthy fix actions need to become normal implementation Work Units while staying visible inside the incident RCA record.

## Do Not Use When

- The caller only needs an implementation bug fix with reproduction tests; use `~/ai/workflows/implementation-pipeline.md` and its bug-only RCA Phase 0.
- The caller only needs an evidence-backed findings artifact; use `~/ai/agents/incident-investigator.md`.
- The caller only needs one post-mortem from already-produced findings; use `~/ai/agents/post-mortem-author.md` now, and future `~/ai/workflows/post-mortem.md` after NES-283 lands.
- The caller is asking for production mutation, source edits, deployment, direct status-transition ownership, or ticket-system protocol redesign.

## Required Inputs

- `incident_handle?`: tracker key, URL, title, customer/environment handle, or stable incident slug.
- `incident_brief_path?`: existing incident brief. If absent, Phase 1 writes `${planning_dir}/incident-brief.md`.
- `incident_context?`: free-form incident context sufficient to draft a brief when no brief exists.
- `evidence_dir?`: existing evidence directory. If absent, Phase 2 assembles `${planning_dir}/evidence/`.
- `repo_root`: repository root for read-only investigation.
- `scratch_dir`: transient prompts, logs, questions, and tracker comment drafts.
- `planning_dir`: durable RCA artifact root; in project-layout runs this lives outside the source diff.
- `ticket_system`: `linear` or `jira`.
- `incident_issue_key?`: existing incident tracker key. If absent, Phase 3 creates or identifies one.
- `linear_team_key`: required when `ticket_system=linear`.
- `linear_project_id?`: optional Linear project binding for incident or action-item tickets.
- `jira_url`: required when `ticket_system=jira`.
- `jira_project`: required when `ticket_system=jira`.
- `jira_account_email`: required when `ticket_system=jira`.
- `action_item_policy?`: `file-only`, `file-and-handoff`, or `file-and-dispatch`; default is `file-and-dispatch` for implementation-worthy fix actions.
- `action_item_worktrees_root?`: root used to derive disjoint `worktree_path` values for child implementation WUs.
- `action_item_planning_root?`: root used to derive disjoint `planning_dir` and `scratch_dir` values for child implementation WUs.
- `runbook_output_dir?`: optional project-owned runbook destination; default is `${planning_dir}/runbooks/`.
- `close_policy?`: currently supported value is `hybrid-pending`; default is `hybrid-pending`, allowing RCA artifacts to complete while the incident stays pending for severe implementation or runbook follow-through.

## Output Paths

- `${planning_dir}/incident-brief.md`: canonical incident brief consumed by investigation and post-mortem phases.
- `${planning_dir}/evidence/`: collected evidence directory, including copied or referenced logs, screenshots, tickets, traces, and provenance notes.
- `${planning_dir}/findings.md`: Phase 4 investigation findings.
- `${planning_dir}/post-mortem.md`: Phase 5 post-mortem.
- `${planning_dir}/action-items.md`: severity-ordered action-item index with ticket keys, dispositions, implementation handoff state, and runbook-only flags.
- `${planning_dir}/runbooks/`: default runbook directory.
- `${planning_dir}/runbooks/<slug>.md`: one runbook output for each unverifiable, operational, or customer-side follow-through item.
- `${planning_dir}/tracker-comments/phase-8.md`: final tracker comment body or comment evidence for findings, post-mortem, action-item, and runbook links.
- `${planning_dir}/rca-close.md`: close-or-pending decision record.
- `${planning_dir}/rca-run-manifest.md`: phase manifest with artifact identity, tracker keys, comment IDs when available, size/mtime/sha256 for local files, and last verified timestamp.
- `${scratch_dir}/prompts/`: child operator prompts and dispatch prompt material.
- `${scratch_dir}/logs/`: child operator logs, tracker command logs, and generator or dispatch logs.
- `${scratch_dir}/questions/`: `NEEDS_INPUT:<absolute_artifact_path>` question artifacts.

## Phase Map

| Phase | Name | Primary owner | Durable output | Transition |
|---|---|---|---|---|
| 1 | Incident Framing | RCA coordinator | `${planning_dir}/incident-brief.md` | Phase 2 or abort if no incident exists |
| 2 | Evidence Pack Assembly | RCA coordinator | `${planning_dir}/evidence/` | Phase 3 |
| 3 | File Incident Tracker | `linear-operator` or `jira-operator` | tracker key plus manifest entry | Phase 4 |
| 4 | Dispatch Incident Investigator | `incident-investigator` | `${planning_dir}/findings.md` | Phase 5 |
| 5 | Dispatch Post-Mortem Author | `post-mortem-author` | `${planning_dir}/post-mortem.md` | Phase 6 |
| 6 | File Action-Item Tickets | ticket operator plus optional implementation orchestrator | `${planning_dir}/action-items.md` | Phase 7 |
| 7 | Author Runbooks For Unverifiable Factors | RCA coordinator or project runbook writer | `${planning_dir}/runbooks/<slug>.md` | Phase 8 |
| 8 | Comment Findings And Post-Mortem Links | ticket operator | `${planning_dir}/tracker-comments/phase-8.md` | Phase 9 |
| 9 | Close Or Stay Open | RCA coordinator with tracker operator when allowed | `${planning_dir}/rca-close.md` | incident closes or stays pending |

## Phase 1 - Incident Framing

### Entry Conditions

The caller supplies `incident_handle`, `incident_context`, `incident_brief_path`, or enough tracker context to identify the incident. `planning_dir` and `scratch_dir` are writable, and `repo_root` is readable if later investigation is expected.

### Actions

If `incident_brief_path` already exists, read it and record its path and file identity in `${planning_dir}/rca-run-manifest.md`. If no brief exists, synthesize `${planning_dir}/incident-brief.md` from `incident_handle` and `incident_context`, preserving unknowns as explicit questions rather than inferred facts. Normalize the brief to include incident summary, impact, time window, affected systems, known evidence, current mitigation, open questions, and tracker context.

### Outputs

- `${planning_dir}/incident-brief.md` when a new brief is created.
- Manifest row for the accepted brief path, source context, and any missing fields.
- Optional `${scratch_dir}/questions/q-<uuid>.question.json` when human-owned incident framing is incomplete.

### Stop Or Transition

Transition to Phase 2 when a readable incident brief exists. Abort at Phase 1 with `BLOCKED:no-incident-to-investigate` when the request does not identify an incident and there is no context to frame one. Emit `NEEDS_INPUT:<absolute_artifact_path>` when the missing framing is a user-owned scope or value question.

## Phase 2 - Evidence Pack Assembly

### Entry Conditions

Phase 1 produced or accepted `incident_brief_path`, and the run has either an existing `evidence_dir` or enough local evidence references to assemble `${planning_dir}/evidence/`.

### Actions

Create or verify `${planning_dir}/evidence/`. Copy durable local artifacts when copying is appropriate, otherwise write pointer notes that name external tickets, logs, dashboards, traces, screenshots, or customer reports without pretending they are local. Record evidence provenance and freshness in `${planning_dir}/rca-run-manifest.md`, and keep credentials, production systems, and external APIs untouched except for documented tracker operations in later phases.

### Outputs

- `${planning_dir}/evidence/` with evidence files or provenance notes.
- Manifest entries for evidence path, observed freshness, and unresolved evidence gaps.
- Optional question artifacts under `${scratch_dir}/questions/` for inaccessible or user-owned evidence.

### Stop Or Transition

Transition to Phase 3 when the evidence directory is readable and has enough provenance for investigation. Stop with `BLOCKED:missing-evidence` for unreadable required evidence or unwritable output paths. Emit `NEEDS_INPUT:<absolute_artifact_path>` for credentials, customer-owned evidence, or scope decisions the model cannot own.

## Phase 3 - File Incident Tracker

### Entry Conditions

The incident brief and evidence pack exist. `ticket_system` is `linear` or `jira`; the corresponding operator inputs are present; and either `incident_issue_key` is supplied or the caller authorizes incident tracker creation.

### Actions

Use `~/ai/agents/linear-operator.md` when `ticket_system=linear` and `~/ai/agents/jira-operator.md` when `ticket_system=jira`. If `incident_issue_key` exists, read or verify the issue and record it in the manifest. If no issue exists, dispatch the selected ticket operator with a create task carrying the incident title, brief summary, evidence pointers, and RCA artifact destination. Linear descriptions and comments stay Markdown-native through the Linear operator; Jira content is passed through the Jira operator so it can render REST/ADF details and preserve failure envelopes.

### Outputs

- Created or verified `incident_issue_key`.
- Tracker URL or key recorded in `${planning_dir}/rca-run-manifest.md`.
- Prompt and log artifacts under `${scratch_dir}/prompts/` and `${scratch_dir}/logs/`.

### Stop Or Transition

Transition to Phase 4 when the incident tracker key is known or the run is explicitly file-only without tracker side effects. Stop with `BLOCKED:tracker-filing-failed` when the selected operator cannot create, read, or verify the issue. Emit `NEEDS_INPUT:<absolute_artifact_path>` when ticket-system selection, project/team key, or tracker creation authority is user-owned.

## Phase 4 - Dispatch Incident Investigator

### Entry Conditions

The incident brief, evidence directory, repository root, and findings destination are known. Later-phase entry may skip Phase 4 only when an existing `findings_path` is supplied with brief and evidence provenance.

### Actions

Dispatch `~/ai/agents/incident-investigator.md` as a separate read-only operator invocation. Pass `incident_brief_path`, `evidence_dir`, `repo_root`, and `findings_path=${planning_dir}/findings.md` unless the caller supplied a different durable findings destination. The RCA coordinator stores the child prompt under `${scratch_dir}/prompts/`, captures the child log under `${scratch_dir}/logs/`, and records the child `WROTE: <path>` sentinel in `${planning_dir}/rca-run-manifest.md`.

### Outputs

- `${planning_dir}/findings.md` or caller-supplied `findings_path`.
- Child dispatch prompt and log artifacts.
- Manifest entry with findings path, content identity, and investigation completion state.

### Stop Or Transition

Transition to Phase 5 when findings are written and readable. For Already-produced-findings resume or later-phase entry, transition only after the manifest records why Phase 4 was skipped. Stop with `BLOCKED:investigation-failed` if the child cannot read required inputs or produce findings. Preserve `NEEDS_INPUT:<absolute_artifact_path>` if the child raises a user-owned investigation question.

## Phase 5 - Dispatch Post-Mortem Author

### Entry Conditions

Readable findings and incident brief artifacts exist. The post-mortem destination is `${planning_dir}/post-mortem.md` unless the caller supplied a durable override.

### Actions

Dispatch `~/ai/agents/post-mortem-author.md` as a separate synthesis-only operator invocation. Pass `findings_path`, the same `incident_brief_path`, `output_path=${planning_dir}/post-mortem.md`, and optional `reference_paths` only for already-captured local references. The RCA coordinator captures prompt/log artifacts and records the post-mortem path, needs-input sidecar if any, and content identity in the run manifest.

### Outputs

- `${planning_dir}/post-mortem.md`.
- Optional `${planning_dir}/post-mortem.md.needs-input.md` or question artifact when post-mortem synthesis cannot resolve a human-owned gap.
- Child prompt/log artifacts and manifest row.

### Stop Or Transition

Transition to Phase 6 when the post-mortem exists and is readable. Stop with `BLOCKED:post-mortem-failed` for malformed or missing findings, unreadable brief, or unwritable `output_path`. Emit or preserve `NEEDS_INPUT:<absolute_artifact_path>` for questions that require incident owner judgment.

## Phase 6 - File Action-Item Tickets

### Entry Conditions

Findings and post-mortem exist. `ticket_system` operator inputs are available. `action_item_policy` is known, and dispatch policies have disjoint path roots when implementation WUs will be started.

### Actions

Extract remediation, verification, monitoring, customer-side, and runbook-only action items from `${planning_dir}/findings.md` and `${planning_dir}/post-mortem.md`. Write `${planning_dir}/action-items.md` in severity order with each item assigned a disposition: no-ticket, runbook-only, filed-ticket, implementation handoff, or implementation dispatched. Use `~/ai/agents/linear-operator.md` or `~/ai/agents/jira-operator.md` to create or identify action-item tickets and to include the incident key or parent reference in the body when true parent linking is unavailable.

For implementation-worthy fix items, default `action_item_policy=file-and-dispatch` dispatches `~/ai/agents/implementation-pipeline-orchestrator.md` serially in severity order. `file-only` records the ticket without implementation handoff. `file-and-handoff` records the exact handoff input bundle without starting the child. Parallel dispatch is allowed only when `${planning_dir}/action-items.md` records independence plus disjoint `worktree_path`, `scratch_dir`, and `planning_dir` for every concurrent child.

### Outputs

- `${planning_dir}/action-items.md` with ticket keys, dispositions, severity order, child WU handoff inputs, and implementation dispatch state.
- Created or verified action-item ticket keys.
- Prompt/log artifacts under `${scratch_dir}/prompts/` and `${scratch_dir}/logs/`.
- Updated `${planning_dir}/rca-run-manifest.md` with child dispatch or handoff state.

### Stop Or Transition

Transition to Phase 7 when every action item has a ticket key, no-ticket disposition, runbook-only disposition, or explicit implementation handoff state. Stop with `BLOCKED:action-item-filing-failed` for tracker failures or unsafe requested mutation. Emit `NEEDS_INPUT:<absolute_artifact_path>` when action severity, ticket ownership, parent-link requirement, or implementation dispatch policy is user-owned.

## Phase 7 - Author Runbooks For Unverifiable Factors

### Entry Conditions

`${planning_dir}/action-items.md` identifies runbook-only, customer-side, operational, or unverifiable factors, and `runbook_output_dir` is known or defaults to `${planning_dir}/runbooks/`. If no runbook-needed items exist in `${planning_dir}/action-items.md`, Phase 7 is a pass-through and transitions immediately to Phase 8.

### Actions

For each runbook-needed item, create or route production of a runbook artifact under `runbook_output_dir`. The RCA workflow specifies the required runbook handling: name the factor, owner, observable trigger, manual verification steps, rollback or escalation path, and evidence link back to the incident. It records whether the runbook was authored in `${planning_dir}/runbooks/<slug>.md`, delegated to a project-owned docs destination, or blocked on customer/project input.

### Outputs

- `${planning_dir}/runbooks/<slug>.md` for RCA-local runbooks, or manifest links to explicit `runbook_output_dir` artifacts.
- Updated `${planning_dir}/action-items.md` with runbook dispositions.
- Updated `${planning_dir}/rca-run-manifest.md`.

### Stop Or Transition

Transition to Phase 8 when each runbook-needed item has a written runbook, an explicit project-owned destination, or a pending state captured in the action-item index. Stop with `BLOCKED:runbook-output-unwritable` for unwritable runbook destinations. Emit `NEEDS_INPUT:<absolute_artifact_path>` for customer-owned or project-owned runbook content decisions.

## Phase 8 - Comment Findings And Post-Mortem Links

### Entry Conditions

The post-mortem exists, Phase 6 action items each have a filed ticket, no-ticket disposition, or runbook-only disposition, and Phase 7 runbook obligations are written or explicitly pending.

### Actions

Draft `${planning_dir}/tracker-comments/phase-8.md` with links or path references to the incident brief, evidence pack, findings, post-mortem, action-item index, action-item tickets, runbooks, and close-policy expectations. Use `~/ai/agents/linear-operator.md` for Linear comments or `~/ai/agents/jira-operator.md` for Jira comments. The comment is posted after RCA explanation and follow-through inventory exist; it does not wait for all implementation PRs unless Phase 9 policy requires that state before closure.

### Outputs

- `${planning_dir}/tracker-comments/phase-8.md`.
- Tracker comment ID, URL, or operator output evidence in `${planning_dir}/rca-run-manifest.md`.
- Prompt/log artifacts for the ticket comment operation.

### Stop Or Transition

Transition to Phase 9 when tracker comment evidence is recorded or the caller explicitly selected file-only tracker behavior. Stop with `BLOCKED:tracker-comment-failed` if the selected operator cannot comment. Emit `NEEDS_INPUT:<absolute_artifact_path>` when comment authority, audience, or publication timing is user-owned.

## Phase 9 - Close Or Stay Open

### Entry Conditions

The RCA artifacts exist: brief, evidence, findings, post-mortem, action-item index, required runbooks, tracker comment evidence, and manifest state. `close_policy` is known.

### Actions

Evaluate closure under the selected policy. With default `hybrid-pending`, write `${planning_dir}/rca-close.md` declaring either that the incident closes or that RCA artifacts are complete while the incident stays open/pending for severe implementation or runbook follow-through. Use the selected ticket operator only for documented comments or status actions the project authorized; otherwise record the recommended status and leave transitions to the human/project owner.

### Outputs

- `${planning_dir}/rca-close.md`.
- Final `${planning_dir}/rca-run-manifest.md` currentness row.
- Optional tracker comment or transition evidence when explicitly authorized.

### Stop Or Transition

Success / incident closes when artifacts are complete, tracker links are recorded, no P0/P1 implementation or runbook item is awaiting a required completion state, and the project authorizes closure. Success / RCA complete but incident stays open or pending when severe action-item WUs, runbooks, customer actions, or project-owned transitions remain unresolved. Stop with `BLOCKED:close-policy-unresolved` or `NEEDS_INPUT:<absolute_artifact_path>` when closure authority or pending-state policy is not model-owned.

## Wrap Relationship To Implementation Pipeline

RCA wraps the implementation workflow at Phase 6. Phase 6 files or identifies severity-ordered action-item tickets from the findings and post-mortem, then each implementation-worthy fix action item enters `~/ai/agents/implementation-pipeline-orchestrator.md` as a normal Work Unit. Those child implementation WUs are inside the RCA workflow's wrap because their ticket keys, status, and links are tracked in `${planning_dir}/action-items.md` and on the incident tracker. RCA does not inline or replace their implementation-pipeline phases.

For a Linear action-item WU, Phase 6 passes `linear_issue_key=<created-or-existing-action-key>`, `ticket_system=linear`, `linear_team_key`, optional `linear_project_id`, `repo_root`, `worktree_path`, `scratch_dir`, `planning_dir`, optional `branch_name`, and any project-level `tickets_first_variant` or `auto_merge_after_phase_9` inputs that the caller explicitly supplied. For a Jira action-item WU, Phase 6 passes `jira_issue_key=<created-or-existing-action-key>`, `ticket_system=jira`, `jira_url`, `jira_project`, `jira_account_email`, `repo_root`, `worktree_path`, `scratch_dir`, `planning_dir`, optional `branch_name`, and any project-level implementation-pipeline variant inputs explicitly supplied by the caller.

Implementation review and PR review remain distinct concern surfaces. Implementation review happens inside the child implementation WU: proposal/risk review is `~/ai/workflows/implementation-pipeline.md` Phase 4, and actual-diff review before PR gates is Phase 7 CodeRabbit. PR review is `~/ai/workflows/implementation-pipeline.md` Phase 8 through `~/ai/workflows/pr-review.md`, after CodeRabbit and against the actual diff. RCA Phase 6 tracks and may dispatch those child WUs, but RCA does not adjudicate their Phase 4, Phase 7, or Phase 8 verdicts.

## Resume And Currentness

`${planning_dir}/rca-run-manifest.md` is the durable resume surface. Each phase records phase id, output path, ticket key or comment id when relevant, local file size, mtime, sha256, source operator, child log path, and last verified timestamp. Resume starts by re-verifying completed local artifacts and tracker references where possible, then continues at the first incomplete or stale phase.

Already-produced-findings and other later-phase entry modes are explicit, not silent shortcuts. The caller must supply the existing artifact path and enough provenance for the manifest to record why earlier phases are skipped. If freshness cannot be proven and rerun would be unsafe or value-losing, the workflow emits `NEEDS_INPUT:<absolute_artifact_path>`.

## Stop Conditions

- Success / incident closes: all RCA artifacts are complete, tracker links are recorded, close criteria are met, and the project authorizes incident closure.
- Success / RCA complete but incident stays open or pending: RCA explanation and follow-through records are complete, but severe action-item WUs, runbooks, customer actions, or project-owned transitions remain open.
- Abort at Phase 1 / no incident to investigate: the caller supplied no actionable incident handle, brief, or context.
- Already-produced-findings resume or later-phase entry: existing findings, post-mortem, or tracker artifacts can be consumed only when provenance and manifest entries prove the skipped phases.
- `BLOCKED:<reason>`: emitted for missing or unreadable inputs, unwritable outputs, tracker operator failures, malformed child outputs, unsafe requested mutation, or unavailable required evidence.
- `NEEDS_INPUT:<absolute_artifact_path>`: emitted for user-owned scope, ticket-system, action-item, runbook, close/pending, credential, access, or value questions; artifacts live under `${scratch_dir}/questions/`.
- Downstream implementation handoff pending: severe action-item WUs may keep the incident open or pending until the selected completion state is reached.

## Anti-Scope

- Workflow doc + structural test only; this workflow does not modify `incident-investigator`, `post-mortem-author`, ticket operators, or `implementation-pipeline-orchestrator`.
- It does not edit `~/ai/agents/incident-investigator.md`, `~/ai/agents/post-mortem-author.md`, `~/ai/agents/linear-operator.md`, `~/ai/agents/jira-operator.md`, or `~/ai/agents/implementation-pipeline-orchestrator.md`.
- It does not redesign the incident-tracker filing protocol; it uses existing operator patterns through the Linear and Jira ticket operators.
- It does not replace implementation-pipeline Phase 4, Phase 7, Phase 8, CodeRabbit, or PR-review gates.
- Phase 7 anti-scope: workflow specifies HOW runbooks are produced; it does not author runbook documents.
- It does not mutate source code, git state, production systems, applications, deployment infrastructure, credentials, or external systems except documented tracker create/comment operations.

## Distinction From Post-Mortem-Only Workflow

`workflows/rca.md` owns the outer incident lifecycle: framing, evidence, tracker filing, investigation, post-mortem, action-item tickets, runbooks, tracker links, and close-or-pending decision. Future `workflows/post-mortem.md` is queued under NES-283 and should own only post-mortem synthesis from existing `findings_path` and `incident_brief_path`.

Until NES-283 exists, callers that only need one post-mortem from existing findings should use `~/ai/agents/post-mortem-author.md` directly. Callers that need full incident-to-close RCA should use this workflow.

## Cross-References

- `~/ai/agents/incident-investigator.md`: Phase 4 evidence-backed read-only investigation.
- `~/ai/agents/post-mortem-author.md`: Phase 5 synthesis-only post-mortem authoring.
- `~/ai/agents/linear-operator.md`: Linear incident filing, action-item filing, and comments.
- `~/ai/agents/jira-operator.md`: Jira incident filing, action-item filing, and comments.
- `~/ai/agents/implementation-pipeline-orchestrator.md`: Phase 6 child implementation WU dispatch target.
- `~/ai/workflows/implementation-pipeline.md`: downstream implementation lifecycle and review gates.
- `~/ai/workflows/pr-review.md`: downstream PR review surface reached by implementation-pipeline Phase 8.
- `~/ai/workflows/post-mortem.md`: queued future NES-283 post-mortem-only workflow, not a NES-278 dependency.
- `~/ai/conventions/workflow-routing.md`: routing precedence and project-specific cue table boundaries.
- `~/ai/conventions/worktree-isolation.md`: disjoint worktree rule for any parallel action-item implementation WUs.
- `~/ai/conventions/agent-questions-and-session-graph.md`: `NEEDS_INPUT:<absolute_artifact_path>` question envelope and surfacing convention.
