# `~/ai/` Master Routing & Topology

Purpose: shared routing and workflow topology for any project that uses `~/ai/` as its workflow library.

Project `AGENTS.md` files should reference this file for the generic routing layer, then add only repo-specific overrides, operators, infrastructure, and exceptions.

Routing precedence and conflict resolution live in [`~/ai/conventions/workflow-routing.md`](conventions/workflow-routing.md). This file stays lean and pointer-heavy.

## Operator Routing Table

### AGENTS maintenance

- `agentsmd-curator` - Audit or edit `AGENTS.md` and the operator directory when routing, frontmatter, or topology may have drifted.
  File: [~/ai/agents/agentsmd-curator.md](agents/agentsmd-curator.md) | Inputs: `mode`, `repo_root`, `agents_md?`, `agents_dir?`, `findings_to_fix?`, `operator_file?`, `routing_entry?` | Model: `gpt-high`

- `agentsmd-maintenance-orchestrator` - Run the full AGENTS maintenance loop when the shared operator catalog or routing layer needs audit, triage, risk-gating, and verification.
  File: [~/ai/agents/agentsmd-maintenance-orchestrator.md](agents/agentsmd-maintenance-orchestrator.md) | Inputs: `repo_root`, `agents_md?`, `agents_dir?`, `triage_policy?`, `risk_gate_required?` | Model: `gpt-high`

- `workflow-reviewer` - Verify that a multi-step operator run actually followed its required procedure and produced the expected outputs.
  File: [~/ai/agents/workflow-reviewer.md](agents/workflow-reviewer.md) | Inputs: `operator_file`, `step_log`, `expected_outputs?`, `mode?` | Model: `claude-opus`

### Coverage / behavior / test authoring

- `coverage-analyzer` - Build a coverage inventory when you need covered vs. uncovered code, dead tests, or regression-baseline data.
  File: [~/ai/agents/coverage-analyzer.md](agents/coverage-analyzer.md) | Inputs: `task`, `worktree_path`, `scope?` | Model: `gpt-high`

- `coverage-auditor` - Judge test quality after coverage analysis or new test work, especially for captured behavior, dead tests, or low-value assertions.
  File: [~/ai/agents/coverage-auditor.md](agents/coverage-auditor.md) | Inputs: `task`, `worktree_path`, `test_files?`, `behavior_specs?` | Model: `claude-opus`

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

### PR review / justification

- `coderabbit-operator` - Run iterative CodeRabbit passes on one branch until the remaining comments stop paying for another loop.
  File: [~/ai/agents/coderabbit-operator.md](agents/coderabbit-operator.md) | Inputs: `branch`, `base`, `worktree_path`, `test_command?`, `max_passes?` | Model: `gpt-high`

- `commit-hygiene-operator` - Audit or rewrite a branch's commits into small, testable, reviewable history without changing the cumulative diff.
  File: [~/ai/agents/commit-hygiene-operator.md](agents/commit-hygiene-operator.md) | Inputs: `branch`, `base`, `mode`, `target_commit_plan?`, `repo_root`, `worktrees_root?`, `worktree_path?`, `python_bin?` | Model: `gpt-high`

- `pr-review-operator` - Run the full PR review pipeline across risk, research, test-audit, decomposition, and posted review comments.
  File: [~/ai/agents/pr-review-operator.md](agents/pr-review-operator.md) | Inputs: `pr_number`, `repo_root`, `repo?`, `planning_root?`, `agents_dir?` | Model: `gpt-high`

- `pr-justification-gauntlet` - Orchestrate the multi-round justification loop across interrogator, researcher, value assessment, and adjudication.
  File: [~/ai/agents/pr-justification-gauntlet.md](agents/pr-justification-gauntlet.md) | Inputs: `pr_number`, `work_dir`, `repo_root`, `repo?`, `planning_root?`, `agents_dir?`, `pr_meta_path?`, `diff_path?` | Model: `gpt-high`

- `pr-justification-interrogator` - Read only the PR and open or press threads for any change that is not obviously justified in this PR.
  File: [~/ai/agents/pr-justification-interrogator.md](agents/pr-justification-interrogator.md) | Inputs: `pr metadata`, `diff`, `threads.json?` | Model: `claude-opus`

- `pr-justification-researcher` - Gather evidence from planning docs, Jira, related PRs, and git history for each open justification thread.
  File: [~/ai/agents/pr-justification-researcher.md](agents/pr-justification-researcher.md) | Inputs: `repo_root`, `planning_root?`, `jira_url`, `jira_project`, `jira_account_email`, `threads.json`, `prior_history?` | Model: `gpt-high`

- `pr-justification-value-assessor` - Score the benefit and cost of keeping each challenged change in the current PR.
  File: [~/ai/agents/pr-justification-value-assessor.md](agents/pr-justification-value-assessor.md) | Inputs: `threads.json`, `prior_history?` | Model: `claude-opus`

- `pr-justification-adjudicator` - Decide when a justification thread is settled and cull it as `drop`, `backlog`, `keep`, or continue to another round.
  File: [~/ai/agents/pr-justification-adjudicator.md](agents/pr-justification-adjudicator.md) | Inputs: `threads.json`, `round history` | Model: `claude-opus`

- `fastapi-review-operator` - Run the secondary FastAPI-specific PR review once the primary review pipeline has already passed its risk gate.
  File: [~/ai/agents/fastapi-review-operator.md](agents/fastapi-review-operator.md) | Inputs: `pr_number`, `repo_root`, `repo?`, `agents_dir?`, `reference_doc?` | Model: `gpt-high`

- `fastapi-best-practices` - Use as the FastAPI reviewer reference for architecture, contracts, state, and testing judgments in the secondary review.
  File: [~/ai/agents/fastapi-best-practices.md](agents/fastapi-best-practices.md) | Inputs: `reference doc only` | Model: `n/a`

### Worktree / branch execution

- `worktree-operator` - Create, list, sync, or remove git worktrees for feature branches.
  File: [~/ai/agents/worktree-operator.md](agents/worktree-operator.md) | Inputs: `task`, `name?`, `base_branch?`, `repo_root`, `worktrees_root?`, `e2e_settings_zip?` | Model: `gpt-high`

- `jj-operator` - Manage stacked-branch dependencies, rebases, squashes, integration branches, and cleanup with `jj`.
  File: [~/ai/agents/jj-operator.md](agents/jj-operator.md) | Inputs: `task`, `branch`, `target?`, `parents?`, `repo_root`, `worktrees_root?` | Model: `gpt-high`

- `pipeline-artifacts-operator` - Standardize scratch artifact naming and `.gitignore` handling inside a worktree so pipeline outputs do not collide.
  File: [~/ai/agents/pipeline-artifacts-operator.md](agents/pipeline-artifacts-operator.md) | Inputs: `worktree_path`, `mode`, `repo_root`, `worktrees_root?`, `agents_bin?` | Model: `gpt-high`

### External integration

- `jira-operator` - Read, comment on, transition, search, or create Jira issues through the Atlassian REST API.
  File: [~/ai/agents/jira-operator.md](agents/jira-operator.md) | Inputs: `task`, `issue_key?`, `body?`, `target_status?`, `jql?`, `fields?`, `jira_url`, `jira_project`, `jira_account_email` | Model: `claude-haiku`

## How to Invoke

Use the shared wrapper conventions in [`~/ai/workflows/agents-cli.md`](workflows/agents-cli.md).

Default shape: `agents -m <model> -p <worktree-path> -f <prompt-file> 2>&1 | tee <log-path>`.

Use [`/home/nes/projects/agent-runner/README.md`](/home/nes/projects/agent-runner/README.md) as the authoritative CLI reference for flags, named-agent resolution, config, and alternate invocation forms.

For concurrent writers, route each writer to its own git worktree; see [`~/ai/conventions/worktree-isolation.md`](conventions/worktree-isolation.md).

## Workflow Topologies

- Implementation pipeline (10-phase): [`~/ai/workflows/implementation-pipeline.md`](workflows/implementation-pipeline.md)
- PR review gates (test-audit, multi-concern, justification, commit-hygiene): [`~/ai/workflows/pr-review.md`](workflows/pr-review.md)
- CodeRabbit loop (CLI-only, amend-only, stop at value-zero): [`~/ai/workflows/coderabbit-loop.md`](workflows/coderabbit-loop.md)
- Research (single-agent, parallel-fanout, deep-reasoning escalation): [`~/ai/workflows/research.md`](workflows/research.md)
- Roadmap (4-layer strategic pipeline): [`~/ai/workflows/roadmap.md`](workflows/roadmap.md)
- Tiered approval (3-tier action safety): [`~/ai/workflows/tiered-approval.md`](workflows/tiered-approval.md)

## Conventions

- [`~/ai/conventions/git.md`](conventions/git.md) - branches, GPG, draft PR routine, no-attribution
- [`~/ai/conventions/worktree-isolation.md`](conventions/worktree-isolation.md) - parallel-agent rule
- [`~/ai/conventions/no-backwards-compatibility.md`](conventions/no-backwards-compatibility.md)
- [`~/ai/conventions/no-deferred-stubs.md`](conventions/no-deferred-stubs.md)
- [`~/ai/conventions/gate-ownership.md`](conventions/gate-ownership.md) - human vs. model gate owners
- [`~/ai/conventions/workflow-routing.md`](conventions/workflow-routing.md) - cue routing precedence

## Model Roles

See [`~/ai/models/roles.md`](models/roles.md) for the authoritative matrix. Default is `gpt-high`; `claude-opus` is for intent/alignment judgements only.

## Operator File Format

See [`~/ai/agents/operator-file-format.md`](agents/operator-file-format.md) for the frontmatter contract and body skeleton.

## How Projects Extend This

A project's own `AGENTS.md` should reference this file for the generic routing layer, then add only project-local overrides and extensions.

Project-specific operator wrappers live in `<project>/agents/` and reference `~/ai/agents/<name>.md` as their base procedure.

See [`~/ai/agents/operator-file-format.md`](agents/operator-file-format.md) for the shared contract; once a `Project wrappers` section exists there, use it. Until then, follow the current convention: frontmatter, `Base procedure: ~/ai/agents/<name>.md`, and repo-specific defaults only.
