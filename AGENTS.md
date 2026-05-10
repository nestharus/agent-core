# `~/ai/` Master Routing & Topology

Purpose: shared routing and workflow topology for any project that uses `~/ai/` as its workflow library.

Project `AGENTS.md` files should reference this file for the generic routing layer, then add only repo-specific overrides, operators, infrastructure, and exceptions.

Routing precedence and conflict resolution live in [`~/ai/conventions/workflow-routing.md`](conventions/workflow-routing.md). This file stays lean and pointer-heavy.

## Quick Activation: Work Manager Mode

When the user says **"you are work manager"** (or any equivalent designation), or otherwise places you in a long-running session managing a backlog of work units across multiple repos / dispatching orchestrators / surfacing frictions to the user — **operate as the Work Manager** per [`~/ai/agents/work-manager-operator.md`](agents/work-manager-operator.md). Read that file in full and follow its filing discipline, dispatch discipline, delegation patterns, and anti-scope. The default rule once activated: keep the user's context clean by delegating execution; do not perform multi-WU work inline.

## Project Setup Pattern

Projects organized for agent-driven workflows follow the umbrella layout `~/projects/<name>/{trunk,planning,worktrees}/`: the git repository sits at `trunk/`, machine-local planning artifacts live in `planning/<branch>/`, and per-WU worktrees live in `worktrees/<branch>/`.

- Full layout rule (single-repo and multi-repo umbrella variants): [`~/ai/conventions/project-layout.md`](conventions/project-layout.md).
- `worktree_path`, `scratch_dir`, `planning_dir` semantics for an orchestrator-driven WU: [`~/ai/agents/implementation-pipeline-orchestrator.md`](agents/implementation-pipeline-orchestrator.md) § Required Inputs.
- Machine-local planning artifacts live outside the worktree/repo diff; do not add new `.gitignore` rules for this WU's machine-local planning artifacts; upload durable outputs to the ticket when they need to survive.

## Operator Routing Table

### AGENTS maintenance

- `agentsmd-curator` - Audit or edit `AGENTS.md` and the operator directory when routing, frontmatter, or topology may have drifted.
  File: [~/ai/agents/agentsmd-curator.md](agents/agentsmd-curator.md) | Inputs: `mode`, `repo_root`, `agents_md?`, `agents_dir?`, `findings_to_fix?`, `operator_file?`, `routing_entry?` | Model: `gpt-high`

- `agentsmd-maintenance-orchestrator` - Run the full AGENTS maintenance loop when the shared operator catalog or routing layer needs audit, triage, risk-gating, and verification.
  File: [~/ai/agents/agentsmd-maintenance-orchestrator.md](agents/agentsmd-maintenance-orchestrator.md) | Inputs: `repo_root`, `agents_md?`, `agents_dir?`, `triage_policy?`, `risk_gate_required?` | Model: `gpt-high`

- `workflow-design-auditor` - Audit workflow document design against the shared design-pattern corpus; does not audit runtime execution.
  File: [~/ai/agents/workflow-design-auditor.md](agents/workflow-design-auditor.md) | Inputs: `workflow_file`, `repo_root`, `design_patterns_ref?`, `context_files?`, `audit_history_path?`, `report_path?`, `mode?` | Model: `gpt-high`

- `agent-design-auditor` - Audit operator prompt design, operator-file-format conformance, and single-concern shape; does not maintain AGENTS routing.
  File: [~/ai/agents/agent-design-auditor.md](agents/agent-design-auditor.md) | Inputs: `operator_file`, `repo_root`, `operator_format_ref?`, `design_patterns_ref?`, `context_files?`, `audit_history_path?`, `report_path?`, `mode?` | Model: `gpt-high`

- `workflow-reviewer` - Verify that a multi-step operator run actually followed its required procedure and produced the expected outputs.
  File: [~/ai/agents/workflow-reviewer.md](agents/workflow-reviewer.md) | Inputs: `operator_file`, `step_log`, `expected_outputs?`, `mode?` | Model: `claude-opus`

- `process-tree-auditor` - Audit an `agents trace --json` process tree plus companion artifacts to verify root-delegated workflow execution.
  File: [~/ai/agents/process-tree-auditor.md](agents/process-tree-auditor.md) | Inputs: `operator_file`, `process_tree_path`, `root_invocation_uuid`, `subtree_root_uuid?`, `expected_process`, `companion_artifacts`, `audit_history_path?`, `mode?`, `report_path?` | Model: `gpt-high`

- `workflow-process-auditor` - Audit workflow run artifacts for procedure adherence; consumes process-tree reports as evidence but does not replace `process-tree-auditor`.
  File: [~/ai/agents/workflow-process-auditor.md](agents/workflow-process-auditor.md) | Inputs: `workflow_file`, `run_artifacts`, `repo_root`, `process_tree_report_path?`, `expected_process_path?`, `audit_history_path?`, `report_path?`, `mode?` | Model: `gpt-high`

### Coverage / behavior / test authoring

- `coverage-analyzer` - Build a coverage inventory when you need covered vs. uncovered code, dead tests, or regression-baseline data.
  File: [~/ai/agents/coverage-analyzer.md](agents/coverage-analyzer.md) | Inputs: `task`, `worktree_path`, `scope?` | Model: `gpt-high`

- `coverage-auditor` - Judge test quality after coverage analysis or new test work, especially for captured behavior, dead tests, or low-value assertions.
  File: [~/ai/agents/coverage-auditor.md](agents/coverage-auditor.md) | Inputs: `task`, `worktree_path`, `test_files?`, `behavior_specs?` | Model: `claude-opus`

- `coverage-expansion-operator` - Orchestrate coverage expansion from uncovered code through P0 selection, behavior investigation, test writing, strict xfails, and report artifacts.
  File: [~/ai/agents/coverage-expansion-operator.md](agents/coverage-expansion-operator.md) | Inputs: `repo_root`, `worktree_path`, `scratch_dir`, `planning_root?`, `spec_dir?`, `scope?`, `coverage_report?`, `agents_dir?`, `report_slug?` | Model: `gpt-high`

- `risk-assessor` - Rank uncovered code by outage potential, blast radius, and business value before choosing what to test first.
  File: [~/ai/agents/risk-assessor.md](agents/risk-assessor.md) | Inputs: `uncovered_areas`, `worktree_path`, `coverage_data?` | Model: `claude-opus`

- `behavior-investigator` - Research intended behavior for suspicious or uncovered code before any test is written.
  File: [~/ai/agents/behavior-investigator.md](agents/behavior-investigator.md) | Inputs: `target`, `repo_root`, `planning_root?`, `context?` | Model: `gpt-high`

- `test-discovery` - Mechanically map changed product files to existing test files that mention them.
  File: [~/ai/agents/test-discovery.md](agents/test-discovery.md) | Inputs: `repo_root`, `scratch_dir`, `base_ref?`, `planning_root?`, `spec_dir?`, `product_globs?`, `test_roots?` | Model: `gpt-high`

- `test-audit-gate` - Produce a blocking `PASS | PARTIAL | FAIL` from existing spec, test, and CI coverage evidence.
  File: [~/ai/agents/test-audit-gate.md](agents/test-audit-gate.md) | Inputs: `mode`, `repo_root`, `scratch_dir`, `planning_root?`, `spec_dir?`, `agents_dir?`, `repo?`, `ci_workflow_name?`, `coverage_reports_root?`, `pr_number?` | Model: `gpt-high`

- `red-phase-gate` - Run newly authored pytest tests against pre-implementation `HEAD` to confirm whether they are genuinely red.
  File: [~/ai/agents/red-phase-gate.md](agents/red-phase-gate.md) | Inputs: `project_dir`, `scratch_dir`, `base_ref?`, `new_test_nodeids?` | Model: `gpt-high`

- `green-phase-gate` - Re-run the red-phase node IDs after implementation to classify what turned green and what stayed blocked or red.
  File: [~/ai/agents/green-phase-gate.md](agents/green-phase-gate.md) | Inputs: `project_dir`, `scratch_dir`, `base_ref?`, `red_phase_report` | Model: `gpt-high`

- `test-writer` - Write tests only from verified intended behavior, never by snapshotting the current implementation.
  File: [~/ai/agents/test-writer.md](agents/test-writer.md) | Inputs: `behavior_spec`, `worktree_path`, `test_type`, `target` | Model: `gpt-high`

- `trace-recorder` - Capture Playwright traces and frame-by-frame workflow evidence when behavior is ambiguous and needs human review.
  File: [~/ai/agents/trace-recorder.md](agents/trace-recorder.md) | Inputs: `workflow`, `worktree_path`, `app_url`, `ambiguity`, `questions` | Model: `gpt-high`

- `push-pull-auditor` - Audit changed code-level and deployment-level pull sites for A1 push-vs-pull system coupling and report `uncontrolled-source coupler` findings with decoupling direction.
  File: [~/ai/agents/push-pull-auditor.md](agents/push-pull-auditor.md) | Inputs: `repo_root`, `diff_path`, `output_path`, `base_ref?`, `head_ref?`, `changed_files_path?`, `proposal_path?`, `problem_map_path?`, `risk_profile_path?`, `code_quality_ref?` | Model: `gpt-high`

### Incident / RCA

- `incident-investigator` - Investigate an incident from a brief, evidence directory, and read-only repository, then write evidence-backed findings without mutating code or external systems.
  File: [~/ai/agents/incident-investigator.md](agents/incident-investigator.md) | Inputs: `incident_brief_path`, `evidence_dir`, `repo_root`, `findings_path?` | Model: `gpt-high`

- `post-mortem-author` — Synthesizes a post-mortem from incident-investigator findings and the incident brief, then writes one Markdown document
  File: [~/ai/agents/post-mortem-author.md](agents/post-mortem-author.md)
  Inputs: findings_path, incident_brief_path, output_path
  Model: claude-opus

- `prototype-rca-orchestrator` - Run the light two-agent prototype RCA loop for one failed behavior test or QA walkthrough observation, then hand back after targeted verification.
  File: [~/ai/agents/prototype-rca-orchestrator.md](agents/prototype-rca-orchestrator.md) | Inputs: `failure_id`, `trigger_type`, `trigger_evidence_path`, `repo_root`, `worktree_path`, `planning_dir`, `scratch_dir`, `handback_callback`, `trigger_command?`, `qa_use_case_id?`, `hard_cap?` | Model: `claude-opus`

### PR review / justification

- `pr-writer` - Author the title and body of a draft pull request for an external reviewer who has no project context — enforces the audience and content rules (no internal jargon, no commit-history sections, no closed-PR or planning-artifact references).
  File: [~/ai/agents/pr-writer.md](agents/pr-writer.md) | Inputs: `branch`, `base`, `repo_root`, `output_path`, `context_files?`, `stack_parent_pr?`, `merged_refs?`, `linear_issue_keys?` | Model: `claude-opus`

- `coderabbit-operator` - Run iterative CodeRabbit passes on one branch until the remaining comments stop paying for another loop.
  File: [~/ai/agents/coderabbit-operator.md](agents/coderabbit-operator.md) | Inputs: `branch`, `base`, `worktree_path`, `test_command?`, `max_passes?`, `audit_history_path?` | Model: `gpt-high`

- `commit-hygiene-operator` - Audit or rewrite a branch's commits into small, testable, reviewable history without changing the cumulative diff.
  File: [~/ai/agents/commit-hygiene-operator.md](agents/commit-hygiene-operator.md) | Inputs: `branch`, `base`, `mode`, `target_commit_plan?`, `repo_root`, `worktrees_root?`, `worktree_path?`, `python_bin?` | Model: `gpt-high`

- `pr-review-operator` - Run the full PR review pipeline across risk, research, test-audit, decomposition, and posted review comments.
  File: [~/ai/agents/pr-review-operator.md](agents/pr-review-operator.md) | Inputs: `pr_number`, `repo_root`, `repo?`, `planning_root?`, `agents_dir?`, `audit_history_path?` | Model: `gpt-high`

- `pr-justification-gauntlet` - Orchestrate the multi-round justification loop across interrogator, researcher, value assessment, and adjudication.
  File: [~/ai/agents/pr-justification-gauntlet.md](agents/pr-justification-gauntlet.md) | Inputs: `pr_number`, `work_dir`, `repo_root`, `repo?`, `planning_root?`, `agents_dir?`, `pr_meta_path?`, `diff_path?`, `audit_history_path?` | Model: `gpt-high`

- `pr-justification-interrogator` - Read only the PR and open or press threads for any change that is not obviously justified in this PR.
  File: [~/ai/agents/pr-justification-interrogator.md](agents/pr-justification-interrogator.md) | Inputs: `pr metadata`, `diff`, `threads.json?`, `audit_history_path?` | Model: `claude-opus`

- `pr-justification-researcher` - Gather evidence from planning docs, Jira, related PRs, and git history for each open justification thread.
  File: [~/ai/agents/pr-justification-researcher.md](agents/pr-justification-researcher.md) | Inputs: `repo_root`, `planning_root?`, `jira_url`, `jira_project`, `jira_account_email`, `threads.json`, `prior_history?`, `audit_history_path?` | Model: `gpt-high`

- `pr-justification-value-assessor` - Score the benefit and cost of keeping each challenged change in the current PR.
  File: [~/ai/agents/pr-justification-value-assessor.md](agents/pr-justification-value-assessor.md) | Inputs: `threads.json`, `prior_history?`, `audit_history_path?` | Model: `claude-opus`

- `pr-justification-adjudicator` - Decide when a justification thread is settled and cull it as `drop`, `backlog`, `keep`, or continue to another round.
  File: [~/ai/agents/pr-justification-adjudicator.md](agents/pr-justification-adjudicator.md) | Inputs: `threads.json`, `round history`, `audit_history_path?` | Model: `claude-opus`

- `decision-encoder` - Maintain canonical audit history after revise/review rounds by encoding findings, role determinations, watch signals, and summarization tail.
  File: [~/ai/agents/decision-encoder.md](agents/decision-encoder.md) | Inputs: `audit_history_path`, `round_number`, `artifact_under_review`, `round_artifacts`, `role_outputs`, `mode?` | Model: `gpt-high`

- `fastapi-review-operator` - Run the secondary FastAPI-specific PR review once the primary review pipeline has already passed its risk gate.
  File: [~/ai/agents/fastapi-review-operator.md](agents/fastapi-review-operator.md) | Inputs: `pr_number`, `repo_root`, `repo?`, `agents_dir?`, `reference_doc?` | Model: `gpt-high`

- `fastapi-best-practices` - Use as the FastAPI reviewer reference for architecture, contracts, state, and testing judgments in the secondary review.
  File: [~/ai/agents/fastapi-best-practices.md](agents/fastapi-best-practices.md) | Inputs: `reference doc only` | Model: `n/a`

### Implementation pipeline orchestration

- `implementation-pipeline-orchestrator` - Orchestrate one Work Unit through the full implementation pipeline (Phase 2.5 → 3 → 4 → audit → 5 → 6a/6b/6c → audit → 7 → 8 → audit → 9). Dispatches every phase via the `agents` CLI, runs the three required `process-tree-auditor` audits, performs inherited estimate read from the selected ticket backend, requires Phase 3 estimate refinement, performs ticket write-back for the refined estimate, and enforces the violation-escalation policy (rewind → split → shrink) autonomously. Default human gates are Phase 2.5 problem-map review and NEEDS_INPUT new-value questions; status transitions remain user-owned, and `tickets_first_variant=true` also surfaces the Phase 8.5 human local-review gate before Phase 9.
  File: [~/ai/agents/implementation-pipeline-orchestrator.md](agents/implementation-pipeline-orchestrator.md) | Inputs: `jira_issue_key?`, `linear_issue_key?`, `wu_brief_path?`, `ticket_system?`, `jira_url?`, `jira_project?`, `jira_account_email?`, `linear_team_key?`, `linear_project_id?`, `repo_root`, `worktree_path`, `scratch_dir`, `planning_dir`, `audit_history_path?`, `pipeline_entry_mode?`, `audit_target_*?`, `existing_review_bundle_path?`, `review_staleness_policy?`, `tickets_first_variant?` | Model: `claude-opus`

- `wu-session-resumer` - Wake one merged Work Unit session, run post-merge checks, cross-link the ticket, and close or prepare handoff.
  File: [~/ai/agents/wu-session-resumer.md](agents/wu-session-resumer.md) | Inputs: `pr_url`, `merge_sha`, `head_sha`, `pre_merge_main_sha`, `branch_name`, `ticket_id`, `session_manifest_path`, `test_command?`, `coverage_command?` | Model: `gpt-high`

### Release management

- `release-orchestrator` - Orchestrate a staged release lifecycle across cut, freeze, hotfix, promote, tag, and reconcile phases.
  File: [~/ai/agents/release-orchestrator.md](agents/release-orchestrator.md) | Inputs: `repo_root`, `worktree_path`, `scratch_dir`, `planning_dir`, `release_id`, `develop_branch_name`, `main_branch_name`, `release_branch_name`, `tag_pattern`, `qa_lane_id`, `manifest_path?`, `release_manifest_path?`, `freeze_window`, `qa_evidence_path`, `required_checks_policy`, `settings_state_or_runbook_ticket`, `hotfix_policy`, `promotion_approval`, `reconcile_obligations`, `ticket_system`, `jira_url?`, `jira_project?`, `jira_account_email?`, `jira_issue_key?`, `jira_release_key?`, `linear_team_key?`, `linear_project_id?`, `linear_issue_key?`, `linear_release_key?`, `release_ticket_key?` | Model: `claude-opus`

- `release-cut-operator` - Forward-referenced NES-244 operator for release branch cut mechanics.
  File: [~/ai/agents/release-cut-operator.md](agents/release-cut-operator.md) | Inputs: `repo_root`, `worktree_path`, `scratch_dir`, `release_id`, `develop_branch_name`, `release_branch_name`, `manifest_path?`, `release_manifest_path?`, `required_checks_policy`, `settings_state_or_runbook_ticket` | Model: `gpt-high`

- `release-hotfix-operator` - Forward-referenced NES-245 operator for release hotfix and cherry-pick mechanics.
  File: [~/ai/agents/release-hotfix-operator.md](agents/release-hotfix-operator.md) | Inputs: `repo_root`, `worktree_path`, `scratch_dir`, `release_id`, `release_branch_name`, `hotfix_branch_name?`, `manifest_path?`, `release_manifest_path?`, `hotfix_policy`, `qa_evidence_path`, `promotion_approval` | Model: `gpt-high`

- `release-promote-operator` - Forward-referenced NES-246 operator for promotion and tag mechanics.
  File: [~/ai/agents/release-promote-operator.md](agents/release-promote-operator.md) | Inputs: `repo_root`, `worktree_path`, `scratch_dir`, `release_id`, `release_branch_name`, `main_branch_name`, `tag_pattern`, `manifest_path?`, `release_manifest_path?`, `qa_evidence_path`, `promotion_approval` | Model: `gpt-high`

- `release-reconcile-operator` - Forward-referenced NES-247 operator for post-release reconciliation mechanics.
  File: [~/ai/agents/release-reconcile-operator.md](agents/release-reconcile-operator.md) | Inputs: `repo_root`, `worktree_path`, `scratch_dir`, `release_id`, `develop_branch_name`, `main_branch_name`, `release_branch_name`, `manifest_path?`, `release_manifest_path?`, `reconcile_obligations` | Model: `gpt-high`

### Strategic planning / proposal alignment cycle

The alignment cycle drives a project's `problem.md` ↔ `philosophy.md` ↔ `proposal.md` review loop. The orchestrator dispatches Stage 1 / 1b-classify / 1b-integrate / 2 / 2b-classify / 2b-integrate; the proposer is user-driven (the orchestrator does NOT run the proposer).

- `problem-bootstrap` - Create an initial product `problem.md` and standalone axis reference table from a fresh brief when the alignment cycle starts from an empty product-strategy state.
  File: [~/ai/agents/problem-bootstrap.md](agents/problem-bootstrap.md) | Inputs: `brief_path`, `project_root`, `problem_path`, `axis_table_path`, `scratch_dir` | Model: `gpt-high`

- `philosophy-bootstrap` - Create an initial product `philosophy.md` from a fresh brief plus an existing readable `problem.md` when the alignment cycle lacks philosophy seed content.
  File: [~/ai/agents/philosophy-bootstrap.md](agents/philosophy-bootstrap.md) | Inputs: `brief_path`, `problem_path`, `philosophy_path`, `scratch_dir` | Model: `gpt-high`

- `alignment-cycle-orchestrator` - Run the proposal alignment review cycle: Stage 1 problem-alignment, Stage 1b-classify + 1b-integrate (problem expansion), Stage 2 philosophy-alignment, Stage 2b-classify + 2b-integrate (philosophy expansion). Halts at 2b-classify if `philosophy-decisions.md` is written (user-input gate). Produces a run report.
  File: [~/ai/agents/alignment-cycle-orchestrator.md](agents/alignment-cycle-orchestrator.md) | Inputs: project paths to `problem.md`, `philosophy.md`, `proposal.md`, axis tables, scratch dir | Model: `claude-opus`

- `proposer` - Write or update `proposal.md` as a system-design document grounded in `problem.md` + `philosophy.md`. Brownfield revisions consume `problem-review.md` + `philosophy-review.md`. Stack/build-order content is roadmap-/DECISIONS-layer concern, not proposal content.
  File: [~/ai/agents/proposer.md](agents/proposer.md) | Inputs: project paths to `problem.md`, `philosophy.md`, `proposal.md`, optional review files | Model: `gpt-high`

- `problem-alignment` - Stage 1 alignment review: read `problem.md` + `proposal.md` + project's axis reference table; produce `problem-review.md` (always) and `problem-surfaces.md` (when new surfaces are discovered).
  File: [~/ai/agents/problem-alignment.md](agents/problem-alignment.md) | Inputs: `problem.md`, `proposal.md`, project axis table | Model: `claude-opus`

- `problem-expansion-classify` - Stage 1b-classify (judge): read `problem-surfaces.md` and judge each surface as `discard / already-covered`, `discard / proposal-specific`, `discard / out-of-scope`, `new-axis`, or `axis-expansion`. Writes `problem-classification.md`. Does NOT modify `problem.md`.
  File: [~/ai/agents/problem-expansion-classify.md](agents/problem-expansion-classify.md) | Inputs: `problem-surfaces.md`, `problem.md`, project axis table | Model: `claude-opus`

- `problem-expansion-integrate` - Stage 1b-integrate (synthesis): read `problem-classification.md` and synthesize integrated text into `problem.md` + the axis reference table for `new-axis` and `axis-expansion` verdicts. Skips `discard` verdicts. Does NOT re-judge.
  File: [~/ai/agents/problem-expansion-integrate.md](agents/problem-expansion-integrate.md) | Inputs: `problem-classification.md`, `problem-surfaces.md`, `problem.md`, project axis table | Model: `gpt-high`

- `philosophy-alignment` - Stage 2 alignment review: read `philosophy.md` + `proposal.md` + `problem-review.md`; produce `philosophy-review.md` (always) and `philosophy-surfaces.md` (when new philosophical concerns are discovered).
  File: [~/ai/agents/philosophy-alignment.md](agents/philosophy-alignment.md) | Inputs: `philosophy.md`, `proposal.md`, `problem-review.md` | Model: `claude-opus`

- `philosophy-expansion-classify` - Stage 2b-classify (judge): classify each concern as A absorbable, B compatible-addition, C tension, D new-axis, or E contradiction. Writes `philosophy-classification.md` (always) and `philosophy-decisions.md` (only when any C/D/E surface user-input concerns). Does NOT modify `philosophy.md`.
  File: [~/ai/agents/philosophy-expansion-classify.md](agents/philosophy-expansion-classify.md) | Inputs: `philosophy-surfaces.md`, `philosophy.md`, `philosophy-alignment.md` | Model: `claude-opus`

- `philosophy-expansion-integrate` - Stage 2b-integrate (synthesis): apply absorbable clarifications (A) and provisional new principles (B) to `philosophy.md`. Skips C/D/E (those live in `philosophy-decisions.md` and are user-owned). Does NOT modify `philosophy-decisions.md`.
  File: [~/ai/agents/philosophy-expansion-integrate.md](agents/philosophy-expansion-integrate.md) | Inputs: `philosophy-classification.md`, `philosophy-surfaces.md`, `philosophy.md` | Model: `gpt-high`

### Roadmap cascade

The roadmap workflow cascades from market research (Layer 0) through ticket regeneration (Layer 4). Each layer has 3x risk gates (per-risk model assignment per `workflows/roadmap.md`, all-LOW required) before advancing.

- `roadmap-orchestrator` - Run the roadmap workflow cascade: Layer 1 executive-roadmap (3x risk), Layer 2 engineering-roadmap (3x risk), Layer 3 per-phase ai-roadmaps (3x risk per phase), Layer 4 ticket regeneration. Dispatches sub-proposers and risk operators via the agents CLI; surfaces NEEDS_INPUT new-value-questions to the root.
  File: [~/ai/agents/roadmap-orchestrator.md](agents/roadmap-orchestrator.md) | Inputs: project paths to `problem.md`, `philosophy.md`, `proposal.md`, `DECISIONS.md`, scratch dir | Model: `claude-opus`

- `executive-roadmap-proposer` - Layer 1: write/update `executive-roadmap.md` from problem + philosophy + proposal + market research. Strategic ordering of value slices and milestones.
  File: [~/ai/agents/executive-roadmap-proposer.md](agents/executive-roadmap-proposer.md) | Inputs: `problem.md`, `philosophy.md`, `proposal.md`, `market-research.md`, optional risk reports | Model: `gpt-high`

- `engineering-roadmap-proposer` - Layer 2: write/update `engineering-roadmap.md` from approved executive-roadmap + DECISIONS.md + engineering-research. Names foundation-phase substrate and per-VS engineering effort.
  File: [~/ai/agents/engineering-roadmap-proposer.md](agents/engineering-roadmap-proposer.md) | Inputs: `executive-roadmap.md`, `DECISIONS.md`, `engineering-research.md`, optional risk reports | Model: `gpt-high`

- `ai-roadmap-proposer` - Layer 3: write/update `ai-roadmap-phase-N.md` from approved engineering-roadmap + per-phase scope. Decomposes a phase into AI-implementable Work Units with named contracts/schemas/parallelization.
  File: [~/ai/agents/ai-roadmap-proposer.md](agents/ai-roadmap-proposer.md) | Inputs: `engineering-roadmap.md`, phase scope, optional risk reports | Model: `gpt-high`

- `ticket-generation-agent` - Layer 4: generate phase ticket artifacts (`tickets/INDEX.md`, `tickets/INIT-NNN.md`, `tickets/SLICE-NNN.md`) from the approved `ai-roadmap-phase-N.md`, preserving named contracts/schemas/acceptance criteria/dependencies verbatim and including SLICE story-point estimate/source/rationale fields while INIT remains unsized.
  File: [~/ai/agents/ticket-generation-agent.md](agents/ticket-generation-agent.md) | Inputs: `ai-roadmap-phase-N.md`, phase id | Model: `gpt-high`

- `engineering-research-agent` - Layer 2 Stage 2a: survey the existing codebase + adjacent reference projects to produce `engineering-research.md`. Read-only against project files.
  File: [~/ai/agents/engineering-research-agent.md](agents/engineering-research-agent.md) | Inputs: `repo_root`, optional reference repos | Model: `gpt-high`

- `market-research-agent` - Layer 0: synthesize market research streams into `market-research.md`. Reads research streams from `research/`.
  File: [~/ai/agents/market-research-agent.md](agents/market-research-agent.md) | Inputs: `research/` directory, optional prior synthesis | Model: `gpt-high`

- `roadmap-risk-types` - Reference catalog of risk types per roadmap layer. Not a callable operator; the roadmap-orchestrator reads this to construct risk-assessment prompts.
  File: [~/ai/agents/roadmap-risk-types.md](agents/roadmap-risk-types.md) | Inputs: `reference doc only` | Model: `n/a`

### Worktree / branch execution

- `worktree-operator` - Create, list, sync, or remove git worktrees for feature branches.
  File: [~/ai/agents/worktree-operator.md](agents/worktree-operator.md) | Inputs: `task`, `name?`, `branch_name?`, `base_branch?`, `repo_root`, `worktrees_root?`, `branch_policy?` | Model: `gpt-high`

- `jj-operator` - Manage stacked-branch dependencies, rebases, squashes, integration branches, and cleanup with `jj`.
  File: [~/ai/agents/jj-operator.md](agents/jj-operator.md) | Inputs: `task`, `branch`, `target?`, `parents?`, `repo_root`, `worktrees_root?` | Model: `gpt-high`

- `pipeline-artifacts-operator` - Standardize scratch artifact naming and `.gitignore` handling inside a worktree so pipeline outputs do not collide.
  File: [~/ai/agents/pipeline-artifacts-operator.md](agents/pipeline-artifacts-operator.md) | Inputs: `worktree_path`, `mode`, `repo_root`, `worktrees_root?`, `agents_bin?` | Model: `gpt-high`

### External integration

- `jira-operator` - Read, comment on, transition, search, or create Jira issues through the Atlassian REST API.
  File: [~/ai/agents/jira-operator.md](agents/jira-operator.md) | Inputs: `task`, `issue_key?`, `body?`, `target_status?`, `jql?`, `fields?`, `jira_url`, `jira_project`, `jira_account_email` | Model: `claude-opus`

## Ecosystem Map

The `~/ai/` ecosystem composes operators, clients, tools, workflows, and conventions. The discoverability map:

- [`~/ai/VALUES.md`](VALUES.md) — ecosystem composition principles and lean-client posture.
- [`~/ai/clients/`](clients/) — first-party client libraries (currently the Linear GraphQL client).
- [`~/ai/tools/README.md`](tools/README.md) — ecosystem-wide tools (scheduler, PR-batch poller).
- [`~/ai/DECISIONS.md`](DECISIONS.md) — `~/ai/`-layer decisions, exceptions, and bootstrap context.
- [`~/ai/agents/linear-operator.md`](agents/linear-operator.md) — Linear ticket operator (Markdown-native).
- [`~/ai/agents/jira-operator.md`](agents/jira-operator.md) — Jira ticket operator (ADF).

Ecosystem-wide infrastructure (scheduler, PR-batch poller, ticket integration clients) lives in `~/ai/`, not in any application-layer project, per [`~/ai/VALUES.md`](VALUES.md) § Lean clients.

Source-of-truth repository: <https://github.com/nestharus/ai>.

## How to Invoke

Use the shared wrapper conventions in [`~/ai/workflows/agents-cli.md`](workflows/agents-cli.md).

Default shape: `agents -m <model> -p <worktree-path> -f <prompt-file> 2>&1 | tee <log-path>`.

Use [`/home/nes/projects/agent-runner/README.md`](/home/nes/projects/agent-runner/README.md) as the authoritative CLI reference for flags, named-agent resolution, config, and alternate invocation forms.

All branch work runs in a git worktree; the central checkout is read-only / branch-tracking only; see [`~/ai/conventions/worktree-isolation.md`](conventions/worktree-isolation.md).

## Workflow Topologies

- Implementation pipeline (10-phase): [`~/ai/workflows/implementation-pipeline.md`](workflows/implementation-pipeline.md)
- RCA workflow (full incident-to-close root-cause analysis): [`~/ai/workflows/rca.md`](workflows/rca.md)
- Prototype RCA workflow (light two-agent root-cause/fix loop for one failed prototype trigger): [`~/ai/workflows/rca-prototype.md`](workflows/rca-prototype.md)
- Release management (staged cut/freeze/hotfix/promote/tag/reconcile lifecycle): [`~/ai/workflows/release-management.md`](workflows/release-management.md)
- Project bootstrap (project-specific operator wrapper open/closed path): [`~/ai/workflows/project-bootstrap.md`](workflows/project-bootstrap.md)
- Alignment cycle (problem ↔ philosophy ↔ proposal review loop with classify/integrate split): [`~/ai/workflows/alignment-cycle.md`](workflows/alignment-cycle.md)
- PR review gates (test-audit, multi-concern, justification, commit-hygiene): [`~/ai/workflows/pr-review.md`](workflows/pr-review.md)
- Audit sub-workflow (target-typed design/process/drift audit coordination): [`~/ai/workflows/audit.md`](workflows/audit.md)
- Tickets-first review (variant: ticket is the unit of review; PR drafted only after review passes): [`~/ai/workflows/tickets-first-review.md`](workflows/tickets-first-review.md)
- CodeRabbit loop (CLI-only, amend-only, stop at value-zero): [`~/ai/workflows/coderabbit-loop.md`](workflows/coderabbit-loop.md)
- Research (single-agent, parallel-fanout, deep-reasoning escalation): [`~/ai/workflows/research.md`](workflows/research.md)
- Linter bootstrap (A1 linter coverage inventory, ecosystem research, and setup-PR proposal): [`~/ai/workflows/linter-bootstrap.md`](workflows/linter-bootstrap.md)
- Code quality (A1 composite auditor fanout and aggregate verdict): [`~/ai/workflows/code-quality.md`](workflows/code-quality.md)
- Roadmap (4-layer strategic pipeline): [`~/ai/workflows/roadmap.md`](workflows/roadmap.md)
- Tiered approval (3-tier action safety): [`~/ai/workflows/tiered-approval.md`](workflows/tiered-approval.md)
- Verified rebase (deterministic residual bundle + rollback; single rebase path): [`~/ai/workflows/verified-rebase.md`](workflows/verified-rebase.md)

## Conventions

- [`~/ai/conventions/code-quality.md`](conventions/code-quality.md) - shared code-quality rules for function classification, max nesting depth, inline mini-function extraction, duplicate responsibility handling, and push-vs-pull system coupling
- [`~/ai/conventions/design-patterns.md`](conventions/design-patterns.md) - shared design-pattern corpus consumed by workflow/agent design auditors
- [`~/ai/conventions/git.md`](conventions/git.md) - branches, GPG, draft PR routine, no-attribution
- [`~/ai/conventions/worktree-isolation.md`](conventions/worktree-isolation.md) - unconditional branch-work isolation and central-checkout read-state rule
- [`~/ai/conventions/no-backwards-compatibility.md`](conventions/no-backwards-compatibility.md)
- [`~/ai/conventions/no-deferred-stubs.md`](conventions/no-deferred-stubs.md)
- [`~/ai/conventions/gate-ownership.md`](conventions/gate-ownership.md) - human vs. model gate owners
- [`~/ai/conventions/proposer-critic-pattern.md`](conventions/proposer-critic-pattern.md) - proposer/critic decomposition for risk-gated implementation
- [`~/ai/conventions/workflow-routing.md`](conventions/workflow-routing.md) - cue routing precedence
- [`~/ai/conventions/agent-questions-and-session-graph.md`](conventions/agent-questions-and-session-graph.md) - sub-agent question envelope, root surfacing, session graph, and resume/fallback convention
- [`~/ai/conventions/audit-history.md`](conventions/audit-history.md) - audit history schema, revise/review loop rules, decision-agent dispatch, and finding ID convention
- [`~/ai/conventions/workflow-execution-violations.md`](conventions/workflow-execution-violations.md) - process-review violation taxonomy and blocking/advisory defaults
- [`~/ai/conventions/review-convergence.md`](conventions/review-convergence.md) - non-converging review loops are a hard decomposition trigger; stop iterating and split the work
- [`~/ai/conventions/project-layout.md`](conventions/project-layout.md) - `~/projects/<name>/{trunk,planning,worktrees}/` umbrella layout for agent-driven projects
- [`~/ai/conventions/bootstrap-pattern.md`](conventions/bootstrap-pattern.md) - lifecycle for converting a general operator into a project-specific wrapper (open path / closed path / re-bootstrap triggers)
- [`~/ai/conventions/rebase-verification.md`](conventions/rebase-verification.md) - deterministic rebase verification, residual bundle, and rollback convention
- [`~/ai/conventions/wu-session-lifecycle.md`](conventions/wu-session-lifecycle.md) - WU spawn, run, merge, and post-merge wake lifecycle

## Model Roles

See [`~/ai/models/roles.md`](models/roles.md) for the authoritative matrix. Default is `gpt-high`; `claude-opus` is for intent/alignment judgements only.

## Operator File Format

See [`~/ai/agents/operator-file-format.md`](agents/operator-file-format.md) for the frontmatter contract and body skeleton.

## How Projects Extend This

A project's own `AGENTS.md` should reference this file for the generic routing layer, then add only project-local overrides and extensions.

Projects organized for agent-driven workflows use the
`~/projects/<name>/{trunk,planning,worktrees}/` umbrella layout per
[`~/ai/conventions/project-layout.md`](conventions/project-layout.md).
The git repository sits at `trunk/`; the project's own `AGENTS.md`
lives at `<project>/trunk/AGENTS.md`.

Project-specific operator wrappers live in `<project>/trunk/agents/` and reference `~/ai/agents/<name>.md` as their base procedure.

See [`~/ai/agents/operator-file-format.md`](agents/operator-file-format.md) for the shared contract; once a `Project wrappers` section exists there, use it. Until then, follow the current convention: frontmatter, `Base procedure: ~/ai/agents/<name>.md`, and repo-specific defaults only.

### Per-Project Policy

A project's own `AGENTS.md` declares the per-project policy knobs the orchestrator and ticket operator read at dispatch time:

- `ticket_system`: `jira` or `linear` — selects the ticket backend per [`~/ai/agents/implementation-pipeline-orchestrator.md`](agents/implementation-pipeline-orchestrator.md) § Ticket System Pluggability.
- Linear projects declare `linear_team_key` (and optionally `linear_project_id`).
- Jira projects declare `jira_url`, `jira_project`, and `jira_account_email`.
- `skip_problem_map_gate` (boolean, default `false`) — see the orchestrator file's Optional Inputs.
- `auto_merge_after_phase_9` (boolean, default `false`) — see the orchestrator file's Optional Inputs.
- `tickets_first_variant` (boolean, default `false`) — see the orchestrator file's Optional Inputs.

Semantics for each knob live on the orchestrator's input contract; the project `AGENTS.md` only declares the chosen values.
