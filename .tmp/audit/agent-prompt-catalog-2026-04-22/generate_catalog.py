from collections import OrderedDict
from pathlib import Path
import re


FILES_DIR = Path("/home/nes/work/agents")
OUT_PATH = Path("/home/nes/ai/.build/catalog-agent-prompts.md")


def line_count(path: Path) -> int:
    with path.open() as f:
        return sum(1 for _ in f)


CATALOG = OrderedDict(
    [
        (
            "agentsmd-curator.md",
            {
                "role": "Audits and optionally edits `AGENTS.md` plus the operator directory so routing, frontmatter, and workflow topology stay consistent.",
                "generality": "PROJECT_COUPLED_SOFT — tied to `AGENTS.md` conventions and hard-coded `~/work` agent paths, but the curation logic is portable.",
                "cross_refs": [],
                "external_deps": ["bash", "ls", "grep"],
                "paths": [
                    "~/work/agents/",
                    "~/work/agents/*.md",
                    "/home/nes/work/AGENTS.md",
                    "/home/nes/work/agents/",
                    "/home/nes/work/agents/foo.md",
                ],
                "staleness": [
                    "Relies on a specific `AGENTS.md` architecture contract that may have drifted.",
                ],
                "recommendation": "MOVE_WITH_PARAM",
                "recommendation_note": "Parameterize `AGENTS.md` and `agents/` roots before moving.",
            },
        ),
        (
            "agentsmd-maintenance-orchestrator.md",
            {
                "role": "Runs the full AGENTS maintenance workflow: audit, triage, risk-gate, delegate edits, re-audit, and process review.",
                "generality": "PROJECT_COUPLED_SOFT — workflow is reusable, but it assumes `~/work` paths and a local `agents` CLI runner.",
                "cross_refs": ["agentsmd-curator.md", "workflow-reviewer.md"],
                "external_deps": ["agents CLI", "bash"],
                "paths": [
                    "/home/nes/work/AGENTS.md",
                    "/home/nes/work/agents/",
                    "~/work/agents/agentsmd-curator.md",
                    "/home/nes/work",
                    "/home/nes/work/agents/agentsmd-maintenance-orchestrator.md",
                ],
                "staleness": [
                    "Assumes the external `agents` runner interface and flags remain stable.",
                ],
                "recommendation": "MOVE_WITH_PARAM",
                "recommendation_note": "Move the orchestrator with configurable project root and agent-file roots.",
            },
        ),
        (
            "behavior-investigator.md",
            {
                "role": "Researches intended behavior for suspicious code paths using git, PRs, tickets, and planning docs instead of assuming current behavior is correct.",
                "generality": "PROJECT_COUPLED_SOFT — core investigation method is generic, but it assumes a `~/work/planning` corpus and mentions repo-specific UI files like `ViewRenderer.js`.",
                "cross_refs": ["risk-assessor.md", "trace-recorder.md", "test-writer.md"],
                "external_deps": ["git", "gh", "Jira or ticket system", "Playwright"],
                "paths": ["~/work/planning"],
                "staleness": [
                    "Example file names like `ViewRenderer.js` and router-config references may be stale.",
                ],
                "recommendation": "MOVE_WITH_PARAM",
                "recommendation_note": "Keep the workflow, but parameterize the planning-doc root and strip repo-specific UI examples.",
            },
        ),
        (
            "coderabbit-operator.md",
            {
                "role": "Runs iterative CodeRabbit review passes on one branch until the tool stops producing useful feedback.",
                "generality": "GENERIC — no repo-specific paths or domain assumptions beyond a normal git branch and an available test command.",
                "cross_refs": ["pr-review-operator.md"],
                "external_deps": ["git", "CodeRabbit", "pytest or project test command"],
                "paths": [],
                "staleness": [
                    "Convergence logic assumes current CodeRabbit pass behavior and rate-limit patterns.",
                ],
                "recommendation": "MOVE_AS_IS",
                "recommendation_note": "Portable as written.",
            },
        ),
        (
            "commit-hygiene-operator.md",
            {
                "role": "Audits or rewrites a branch’s commit history so reviewers can step through small, testable commits without changing the final cumulative diff.",
                "generality": "PROJECT_COUPLED_SOFT — hygiene rules are generic, but the prompt hard-codes RFQ repo/worktree paths and a project Python interpreter.",
                "cross_refs": ["jj-operator.md"],
                "external_deps": ["git", "jj", "pytest", "python3", "CodeRabbit"],
                "paths": [
                    "~/work/rfqautomation-linux/",
                    "~/work/worktrees/<branch-suffix>",
                    "/home/nes/work/rfqautomation-linux/venv/bin/python3",
                ],
                "staleness": [
                    "Includes destructive recovery examples with `git reset --hard`; safe for cataloging, but the exact recovery advice may age.",
                    "Assumes `jj split` and related interactive flows still behave as described.",
                ],
                "recommendation": "MOVE_WITH_PARAM",
                "recommendation_note": "Move only after replacing hard-coded repo/worktree/interpreter paths with parameters.",
            },
        ),
        (
            "coverage-analyzer.md",
            {
                "role": "Builds a coverage baseline for backend and frontend code, identifies uncovered modules, and maps test-to-source gaps.",
                "generality": "GENERIC — uses standard Python/JS coverage workflows with only scratch paths under `/tmp`.",
                "cross_refs": [
                    "behavior-investigator.md",
                    "risk-assessor.md",
                    "test-writer.md",
                    "trace-recorder.md",
                ],
                "external_deps": ["git", "pytest", "coverage.py", "python3", "npx", "Playwright"],
                "paths": [],
                "staleness": [
                    "Coverage command assumptions may age if the repo standardizes on a different frontend test runner.",
                ],
                "recommendation": "MOVE_AS_IS",
                "recommendation_note": "Portable as written.",
            },
        ),
        (
            "coverage-auditor.md",
            {
                "role": "Reviews existing tests for quality, CI alignment, dead tests, and behavior-capture anti-patterns rather than just counting coverage.",
                "generality": "GENERIC — the audit taxonomy is reusable and has no hard project-path coupling.",
                "cross_refs": [
                    "behavior-investigator.md",
                    "coverage-analyzer.md",
                    "test-writer.md",
                ],
                "external_deps": ["git", "pytest"],
                "paths": [],
                "staleness": [
                    "Test anti-pattern taxonomy may need tuning as the team’s testing style evolves.",
                ],
                "recommendation": "MOVE_AS_IS",
                "recommendation_note": "Portable as written.",
            },
        ),
        (
            "e2e-operator.md",
            {
                "role": "Triggers, reproduces, fixes, and verifies RFQ platform E2E failures across Docker, Windows EXE, PAT validation, and upgrade scenarios.",
                "generality": "PROJECT_COUPLED_HARD — deeply bound to RFQ workflows, GHCR image names, S3 report buckets, Windows filesystem layout, and repo-specific E2E scripts.",
                "cross_refs": ["jj-operator.md", "release-operator.md", "worktree-operator.md"],
                "external_deps": [
                    "git",
                    "gh",
                    "aws",
                    "docker",
                    "docker-compose",
                    "npx",
                    "Playwright",
                    "rsync",
                    "bash",
                    "PowerShell",
                ],
                "paths": [
                    "/home/nes/work/worktrees/my-fix/",
                    "~/work/e2e-local-settings.zip",
                    "/mnt/c/Users/xteam/IdeaProjects/e2e-windows/",
                ],
                "staleness": [
                    "Workflow names, concurrency group `lama-server-e2e`, and run-watching guidance may have changed.",
                    "Seed image tag `ghcr.io/lama-ai-rfq/rfqautomation-rfq-app-e2e:v1.0.0-e2e` is likely perishable.",
                    "Disagrees with `release-operator.md` on whether `gh run watch` should be used directly.",
                ],
                "recommendation": "KEEP_IN_WORK",
                "recommendation_note": "This belongs with the RFQ project’s release/test infrastructure.",
            },
        ),
        (
            "fastapi-best-practices.md",
            {
                "role": "Serves as the opinionated FastAPI reference manual used by the secondary FastAPI review pipeline.",
                "generality": "GENERIC — framework guidance document with no meaningful `~/work` coupling.",
                "cross_refs": [],
                "external_deps": [],
                "paths": [],
                "staleness": [
                    "Framework guidance can age quickly around FastAPI, Pydantic, and SQLAlchemy version changes.",
                    "References a community guide (`zhanymkanov/fastapi-best-practices`) that may drift from current team standards.",
                ],
                "recommendation": "MOVE_AS_IS",
                "recommendation_note": "Portable reference doc.",
            },
        ),
        (
            "fastapi-review-operator.md",
            {
                "role": "Runs a secondary PR review focused on FastAPI idioms, service layering, Pydantic contracts, and backend testing patterns.",
                "generality": "PROJECT_COUPLED_SOFT — the review facets are reusable, but the prompt hard-codes repo defaults, project context, and the local reference-doc path.",
                "cross_refs": ["fastapi-best-practices.md", "pr-review-operator.md"],
                "external_deps": ["agents CLI", "gh", "bash"],
                "paths": [
                    "/home/nes/work/agents/fastapi-best-practices.md",
                    "~/work/rfqautomation-linux",
                ],
                "staleness": [
                    "Depends on the secondary-review gate ordering and comment format used by the current PR pipeline.",
                    "Assumes the checked-in `fastapi-best-practices.md` reference remains current.",
                ],
                "recommendation": "MOVE_WITH_PARAM",
                "recommendation_note": "Move with configurable repo root and reference-doc path.",
            },
        ),
        (
            "green-phase-gate.md",
            {
                "role": "Re-runs the red-phase node IDs against the implementation head to classify which tests have turned green.",
                "generality": "GENERIC — pytest-focused gate with no project-specific paths.",
                "cross_refs": ["test-audit-gate.md"],
                "external_deps": ["pytest", "python3"],
                "paths": [],
                "staleness": [
                    "Assumes the surrounding red/green gate workflow still uses the same node-ID handoff format.",
                ],
                "recommendation": "MOVE_AS_IS",
                "recommendation_note": "Portable as written for pytest repos.",
            },
        ),
        (
            "jira-operator.md",
            {
                "role": "Reads, comments on, searches, transitions, and optionally creates Jira issues through the Atlassian REST API using ADF payloads.",
                "generality": "PROJECT_COUPLED_SOFT — the Jira mechanics are generic, but the prompt is pinned to one Jira tenant, one user email, and specific project keys.",
                "cross_refs": [],
                "external_deps": ["curl", "python3", "JIRA_API_KEY"],
                "paths": [],
                "staleness": [
                    "Pinned to `lamaai.atlassian.net`, `aaron.solomon@scint.ai`, and `INFA`/`KAN` project codes.",
                    "Contains a dated auth note (`verified 2026-04-18 via /myself`) that can go stale quickly.",
                ],
                "recommendation": "MOVE_WITH_PARAM",
                "recommendation_note": "Move only after parameterizing tenant URL, account email, and project defaults.",
            },
        ),
        (
            "jj-operator.md",
            {
                "role": "Manages jj-based rebases, stacked-branch dependencies, squashes, and integration branches across the project DAG.",
                "generality": "PROJECT_COUPLED_SOFT — jj workflows are reusable, but the prompt is built around one RFQ repo root, its branch naming, and downstream E2E/release conventions.",
                "cross_refs": ["e2e-operator.md", "worktree-operator.md"],
                "external_deps": ["jj", "git", "gh"],
                "paths": [
                    "~/work/rfqautomation-linux/",
                    "~/work/rfqautomation-linux",
                    "~/work/worktrees/<name>",
                ],
                "staleness": [
                    "Relies on current `JJ_IMMUTABLE` config syntax and jj bookmark behavior.",
                    "Integration-branch examples assume the RFQ E2E workflow naming still matches reality.",
                ],
                "recommendation": "MOVE_WITH_PARAM",
                "recommendation_note": "Move with parameterized repo/worktree roots and branch-policy notes.",
            },
        ),
        (
            "pipeline-artifacts-operator.md",
            {
                "role": "Standardizes per-worktree scratch artifact naming and `.gitignore` patterns so pipeline outputs do not collide or leak into commits.",
                "generality": "PROJECT_COUPLED_SOFT — naming policy is generic, but it assumes a `~/work/worktrees` layout and a local `agents` CLI wrapper.",
                "cross_refs": [],
                "external_deps": ["agents CLI", "git", "uuidgen", "bash"],
                "paths": [
                    "~/work/worktrees/<name>/",
                    "~/work/worktrees/fix-windows-orchestrator",
                    "~/.local/bin/agents",
                ],
                "staleness": [
                    "File-catalog assumptions will drift if the pipeline adds or renames scratch artifact types.",
                ],
                "recommendation": "MOVE_WITH_PARAM",
                "recommendation_note": "Useful centrally, but only after parameterizing the worktree root and runner path.",
            },
        ),
        (
            "pr-justification-adjudicator.md",
            {
                "role": "Acts as the per-round judge in the PR justification gauntlet, culling threads with `drop`, `backlog`, `keep`, or `continue` decisions.",
                "generality": "GENERIC — rubric-driven thread adjudication with no project-specific paths.",
                "cross_refs": ["pr-justification-gauntlet.md"],
                "external_deps": [],
                "paths": [],
                "staleness": [
                    "Assumes the gauntlet’s JSON transcript schema and 5-round cap remain unchanged.",
                ],
                "recommendation": "MOVE_AS_IS",
                "recommendation_note": "Portable as written.",
            },
        ),
        (
            "pr-justification-gauntlet.md",
            {
                "role": "Runs the adversarial multi-round PR justification workflow by orchestrating interrogator, researcher, value-assessor, and adjudicator passes.",
                "generality": "PROJECT_COUPLED_SOFT — the gauntlet itself is reusable, but the prompt hard-codes repo/planning paths and local agent-file locations.",
                "cross_refs": [
                    "pr-justification-adjudicator.md",
                    "pr-justification-interrogator.md",
                    "pr-justification-researcher.md",
                    "pr-justification-value-assessor.md",
                    "pr-review-operator.md",
                ],
                "external_deps": ["agents CLI", "gh", "jq", "curl", "JIRA_API_KEY", "AZURE_EMAIL"],
                "paths": [
                    "~/work/rfqautomation-linux",
                    "~/work/planning",
                    "/home/nes/work/agents/pr-justification-interrogator.md",
                    "/home/nes/work/agents/pr-justification-researcher.md",
                    "/home/nes/work/agents/pr-justification-value-assessor.md",
                    "/home/nes/work/agents/pr-justification-adjudicator.md",
                ],
                "staleness": [
                    "Depends on the current `agents` CLI invocation contract and local prompt-file layout.",
                    "Environment variable name `AZURE_EMAIL` may reflect an older account setup.",
                ],
                "recommendation": "MOVE_WITH_PARAM",
                "recommendation_note": "Move the cluster together, with parameterized planning root and agent-file roots.",
            },
        ),
        (
            "pr-justification-interrogator.md",
            {
                "role": "Reads only the PR diff and opens conservative justification threads for any change that looks extraneous or insufficiently justified.",
                "generality": "GENERIC — diff-only interrogation logic with no project-path assumptions.",
                "cross_refs": ["pr-justification-gauntlet.md"],
                "external_deps": [],
                "paths": [],
                "staleness": [
                    "Assumes the gauntlet thread schema and verdict vocabulary remain stable.",
                ],
                "recommendation": "MOVE_AS_IS",
                "recommendation_note": "Portable as written.",
            },
        ),
        (
            "pr-justification-researcher.md",
            {
                "role": "Collects evidence from planning docs, Jira, related PRs, and git history for each open PR-justification thread without advocating for the PR.",
                "generality": "PROJECT_COUPLED_SOFT — the research role is reusable, but it assumes Jira access, a planning-doc corpus, and repo-specific artifacts like `WORK_LOG.md`.",
                "cross_refs": ["pr-justification-gauntlet.md"],
                "external_deps": ["git", "gh", "curl", "JIRA_API_KEY", "AZURE_EMAIL"],
                "paths": [],
                "staleness": [
                    "Environment variable name `AZURE_EMAIL` and the `WORK_LOG.md` convention may be outdated.",
                ],
                "recommendation": "MOVE_WITH_PARAM",
                "recommendation_note": "Move with environment and planning-source parameters.",
            },
        ),
        (
            "pr-justification-value-assessor.md",
            {
                "role": "Scores the benefit and cost of keeping each challenged change in the current PR so the adjudicator can decide what survives.",
                "generality": "GENERIC — rubric and thread-based reasoning are portable.",
                "cross_refs": ["pr-justification-gauntlet.md"],
                "external_deps": ["agents CLI for optional sub-questions"],
                "paths": [],
                "staleness": [
                    "Assumes optional sub-agent dispatch via `agents -m gpt-high` remains available.",
                ],
                "recommendation": "MOVE_AS_IS",
                "recommendation_note": "Portable as written.",
            },
        ),
        (
            "pr-review-operator.md",
            {
                "role": "Orchestrates the full PR review pipeline: risk assessment, research, test-audit, decomposition review, and GitHub review comments.",
                "generality": "PROJECT_COUPLED_SOFT — broadly reusable review pipeline, but it is wired to one repo default, one planning dir, and local operator-file paths.",
                "cross_refs": [
                    "jj-operator.md",
                    "pr-justification-gauntlet.md",
                    "test-audit-gate.md",
                    "worktree-operator.md",
                ],
                "external_deps": ["agents CLI", "gh", "bash"],
                "paths": [
                    "~/work/rfqautomation-linux",
                    "/home/nes/work/agents/test-audit-gate.md",
                    "$HOME/work/planning",
                    "/home/nes/work/agents/pr-justification-gauntlet.md",
                ],
                "staleness": [
                    "Encodes current `agents` runner limitations around typed inputs; that may already have changed.",
                    "Depends on GitHub review-comment flow and pipeline phase names staying stable.",
                ],
                "recommendation": "MOVE_WITH_PARAM",
                "recommendation_note": "Move only after parameterizing repo root, planning root, and agent-file paths.",
            },
        ),
        (
            "qa-operator.md",
            {
                "role": "Runs RFQ QA passes across unit tests, regenerated CI artifacts, Gemini-based visual checks, interactive browser QA, and report schema validation.",
                "generality": "PROJECT_COUPLED_HARD — anchored to RFQ report-generation scripts, patch-log conventions, CI artifact shapes, and Gemini-based visual QA workflow.",
                "cross_refs": ["e2e-operator.md", "jj-operator.md", "pr-review-operator.md"],
                "external_deps": [
                    "gh",
                    "python3",
                    "pytest",
                    "npm",
                    "npx",
                    "jq",
                    "agents CLI",
                    "Gemini model runner",
                ],
                "paths": [
                    "~/.local/bin/agents",
                    "~/work/worktrees/<name>/",
                ],
                "staleness": [
                    "Contains a dated note about PR #381 and a specific path-resolution fix.",
                    "Model guidance around `gemini-high` and `claude-opus` may be stale.",
                    "CLI workaround for `gh pr edit --body` GraphQL warnings may be obsolete.",
                ],
                "recommendation": "KEEP_IN_WORK",
                "recommendation_note": "This is tightly bound to the RFQ report QA stack.",
            },
        ),
        (
            "red-phase-gate.md",
            {
                "role": "Runs newly authored tests against HEAD and mechanically classifies whether they are genuinely red, already green, blocked, or otherwise mis-targeted.",
                "generality": "GENERIC — pytest-only gate with no project-path coupling.",
                "cross_refs": ["coverage-auditor.md", "test-discovery.md"],
                "external_deps": ["git", "pytest", "python3"],
                "paths": [],
                "staleness": [
                    "Assumes the surrounding red-phase artifact names (`RED_PHASE.md`, node-ID output) are still in use.",
                ],
                "recommendation": "MOVE_AS_IS",
                "recommendation_note": "Portable as written for pytest repos.",
            },
        ),
        (
            "release-operator.md",
            {
                "role": "Owns RFQ Docker and Windows release workflows, versioning, promotion, installer rebuilds, and post-release verification.",
                "generality": "PROJECT_COUPLED_HARD — inseparable from RFQ repos, release channels, GHCR/S3/CloudFront infrastructure, Windows installer internals, and named workflows.",
                "cross_refs": ["e2e-operator.md", "jj-operator.md", "worktree-operator.md"],
                "external_deps": [
                    "git",
                    "gh",
                    "python",
                    "docker",
                    "aws",
                    "curl",
                    "PowerShell",
                    "cmd",
                    "winget",
                    "Inno Setup ISCC",
                ],
                "paths": [
                    "~/work/rfqautomation-linux",
                    "~/work/rfqinstallation-linux/*",
                ],
                "staleness": [
                    "Workflow names, repo names, promotion steps, and deleted-workflow notes are all time-sensitive.",
                    "References specific bugs like `charset_normalizer.cd` and current release-gating rules that may have moved on.",
                    "Installer/test steps depend on one Windows user layout under `/mnt/c/Users/xteam/`.",
                ],
                "recommendation": "KEEP_IN_WORK",
                "recommendation_note": "Leave this with the RFQ release infrastructure.",
            },
        ),
        (
            "risk-assessor.md",
            {
                "role": "Scores uncovered code for risk and product value so teams can prioritize which branches need tests first.",
                "generality": "GENERIC — scoring rubric is portable and uses only general code/coverage inputs.",
                "cross_refs": [
                    "behavior-investigator.md",
                    "coverage-analyzer.md",
                    "test-writer.md",
                ],
                "external_deps": ["git"],
                "paths": [],
                "staleness": [
                    "Priority rubric may need recalibration if the team changes how it treats blast radius or business criticality.",
                ],
                "recommendation": "MOVE_AS_IS",
                "recommendation_note": "Portable as written.",
            },
        ),
        (
            "task-packager.md",
            {
                "role": "Builds self-contained `/tmp` task folders for external AI models, including task definitions, prompts, copied planning docs, and worktree context.",
                "generality": "PROJECT_COUPLED_HARD — depends on RFQ planning-directory taxonomy, worktree naming, and a project-specific `zip-worktree.sh` helper.",
                "cross_refs": [],
                "external_deps": ["cp", "zip", "bash"],
                "paths": [
                    "~/work/planning/e2e/tasks/15-cost-estimation-regression.md",
                    "/home/nes/work/worktrees/<name>/",
                    "/home/nes/work/rfqautomation-linux/",
                    "~/work/planning/cloud/complete-stack-architecture.md",
                    "~/work/planning/cloud/executive-roadmap.md",
                    "~/work/planning/e2e/tasks/20-identity-provider-abstraction.md",
                    "~/work/zip-worktree.sh",
                    "~/work/planning/e2e/tasks/NN-short-name.md",
                    "~/work/planning/cloud/",
                    "~/work/planning/product/PRODUCT-enhancement-<name>.md",
                    "~/work/planning/product/expansion/tasks/NN-short-name.md",
                ],
                "staleness": [
                    "Task taxonomy and planning-doc locations are likely to drift.",
                    "External-model packaging conventions may have changed since the prompt was written.",
                ],
                "recommendation": "KEEP_IN_WORK",
                "recommendation_note": "This belongs with the RFQ planning corpus unless it is redesigned around generic task-packaging inputs.",
            },
        ),
        (
            "test-audit-gate.md",
            {
                "role": "Runs the three-part PR/implementation test audit by delegating spec alignment, test quality, and coverage-delta checks, then synthesizing one verdict.",
                "generality": "PROJECT_COUPLED_SOFT — the gate design is reusable, but it assumes a planning coverage directory and local operator-file paths.",
                "cross_refs": [
                    "behavior-investigator.md",
                    "coverage-analyzer.md",
                    "coverage-auditor.md",
                ],
                "external_deps": ["agents CLI", "git", "gh", "rg", "grep", "bash"],
                "paths": [
                    "~/work/planning/coverage",
                    "/home/nes/work/agents/coverage-auditor.md",
                    "/home/nes/work/agents/coverage-analyzer.md",
                ],
                "staleness": [
                    "Depends on the current multi-agent file-naming convention and coverage-artifact layout.",
                ],
                "recommendation": "MOVE_WITH_PARAM",
                "recommendation_note": "Move with configurable planning and agent-file roots.",
            },
        ),
        (
            "test-discovery.md",
            {
                "role": "Mechanically finds existing tests that touch changed product files and reports direct or heuristic coverage hits without judging test quality.",
                "generality": "PROJECT_COUPLED_SOFT — core discovery logic is generic, but it points to a shared planning coverage area.",
                "cross_refs": [
                    "coverage-analyzer.md",
                    "coverage-auditor.md",
                    "test-audit-gate.md",
                ],
                "external_deps": ["git", "python3", "rg", "grep"],
                "paths": ["~/work/planning/coverage"],
                "staleness": [
                    "AST heuristics in Appendix A may drift as the team’s language mix or import patterns evolve.",
                ],
                "recommendation": "MOVE_WITH_PARAM",
                "recommendation_note": "Move after parameterizing the planning coverage root.",
            },
        ),
        (
            "test-writer.md",
            {
                "role": "Writes tests only from verified behavior specifications and explicitly rejects implementation-derived expected values.",
                "generality": "GENERIC — reusable testing discipline prompt with no project-path coupling.",
                "cross_refs": ["behavior-investigator.md"],
                "external_deps": ["pytest", "python3", "npx", "Playwright"],
                "paths": [],
                "staleness": [
                    "Assumes the repo still uses pytest/Playwright-style test entrypoints.",
                ],
                "recommendation": "MOVE_AS_IS",
                "recommendation_note": "Portable as written.",
            },
        ),
        (
            "trace-recorder.md",
            {
                "role": "Records Playwright traces and screenshots for ambiguous user-facing behavior so humans can answer focused workflow questions.",
                "generality": "GENERIC — trace-capture workflow is portable and uses only `/tmp` scratch paths.",
                "cross_refs": ["behavior-investigator.md", "e2e-operator.md", "test-writer.md"],
                "external_deps": ["git", "npx", "Playwright"],
                "paths": [],
                "staleness": [
                    "Relies on the current Playwright trace-viewer artifact structure and screenshot naming.",
                ],
                "recommendation": "MOVE_AS_IS",
                "recommendation_note": "Portable as written.",
            },
        ),
        (
            "workflow-reviewer.md",
            {
                "role": "Checks whether another operator actually followed its documented procedure by comparing a step log against the operator prompt.",
                "generality": "GENERIC — read-only workflow audit prompt with no project-path coupling.",
                "cross_refs": [
                    "agentsmd-curator.md",
                    "jj-operator.md",
                    "pr-review-operator.md",
                    "test-audit-gate.md",
                ],
                "external_deps": [],
                "paths": [],
                "staleness": [
                    "Assumes operator prompts continue to use explicit step-by-step procedures and stable output contracts.",
                ],
                "recommendation": "MOVE_AS_IS",
                "recommendation_note": "Portable as written.",
            },
        ),
        (
            "worktree-operator.md",
            {
                "role": "Creates, lists, syncs, removes, and opens draft PRs for git worktrees used in feature development.",
                "generality": "PROJECT_COUPLED_SOFT — generic worktree management wrapped around one RFQ repo root, worktree root, branch naming convention, and shared E2E secrets zip.",
                "cross_refs": ["e2e-operator.md", "jj-operator.md", "release-operator.md"],
                "external_deps": ["git", "gh", "unzip", "awk", "grep"],
                "paths": [
                    "~/work/worktrees/",
                    "~/work/worktrees/<name>/",
                    "~/work/rfqautomation-linux",
                    "~/work/e2e-local-settings.zip",
                    "../worktrees/<name>",
                ],
                "staleness": [
                    "Assumes `feat/<name>` branch policy and draft-PR workflow are still the standard.",
                ],
                "recommendation": "MOVE_WITH_PARAM",
                "recommendation_note": "Move with configurable repo root, worktree root, branch pattern, and secrets bundle path.",
            },
        ),
    ]
)


CLUSTERS = [
    (
        "AGENTS maintenance",
        [
            "agentsmd-curator.md",
            "agentsmd-maintenance-orchestrator.md",
            "workflow-reviewer.md",
        ],
        "These three prompts form a self-checking maintenance loop for `AGENTS.md` and operator procedures.",
    ),
    (
        "Coverage / behavior / test authoring",
        [
            "coverage-analyzer.md",
            "coverage-auditor.md",
            "risk-assessor.md",
            "behavior-investigator.md",
            "test-discovery.md",
            "test-audit-gate.md",
            "red-phase-gate.md",
            "green-phase-gate.md",
            "test-writer.md",
            "trace-recorder.md",
        ],
        "This cluster maps coverage, investigates intended behavior, gates red/green phases, and writes or audits tests.",
    ),
    (
        "PR review / justification",
        [
            "coderabbit-operator.md",
            "commit-hygiene-operator.md",
            "pr-review-operator.md",
            "pr-justification-gauntlet.md",
            "pr-justification-interrogator.md",
            "pr-justification-researcher.md",
            "pr-justification-value-assessor.md",
            "pr-justification-adjudicator.md",
            "fastapi-review-operator.md",
            "fastapi-best-practices.md",
        ],
        "These prompts stage PR review from automated feedback through adversarial justification and framework-specific follow-up.",
    ),
    (
        "Worktree / branch / release execution",
        [
            "worktree-operator.md",
            "jj-operator.md",
            "pipeline-artifacts-operator.md",
            "e2e-operator.md",
            "qa-operator.md",
            "release-operator.md",
            "task-packager.md",
        ],
        "These prompts share the same operational surface: worktrees, branch stacks, release artifacts, E2E, QA, and external packaging.",
    ),
    (
        "Standalone integration",
        ["jira-operator.md"],
        "Jira access sits mostly outside the internal prompt graph, but several review prompts assume it is available.",
    ),
]


GLOBAL_STALENESS = (
    "Most frontmatter model aliases are themselves speculative staleness candidates: "
    "`claude-opus`, `claude-haiku`, `gpt-high`, and `gemini-high` may need a later naming/model refresh. "
    "Per-file flags below focus on additional issues beyond that global risk."
)


def fmt_list(items):
    return ", ".join(f"`{item}`" for item in items) if items else "none"


def file_model(path: Path) -> str | None:
    text = path.read_text()
    if not text.startswith("---\n"):
        return None
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return None
    for line in m.group(1).splitlines():
        if line.startswith("model:"):
            return line.split(":", 1)[1].strip().strip("'\"")
    return None


def main():
    files = sorted(FILES_DIR.glob("*.md"))
    generality_counts = {"GENERIC": 0, "PROJECT_COUPLED_SOFT": 0, "PROJECT_COUPLED_HARD": 0}
    recommendation_counts = {"MOVE_AS_IS": 0, "MOVE_WITH_PARAM": 0, "KEEP_IN_WORK": 0}

    for name, meta in CATALOG.items():
        prefix = meta["generality"].split(" ", 1)[0]
        generality_counts[prefix] += 1
        recommendation_counts[meta["recommendation"]] += 1

    tool_surface = [
        "agents CLI",
        "git",
        "gh",
        "jj",
        "pytest",
        "python/python3",
        "coverage.py",
        "rg/grep",
        "npx/Playwright",
        "npm/jest",
        "docker/docker-compose",
        "aws CLI",
        "curl",
        "jq",
        "unzip/zip",
        "rsync",
        "PowerShell/cmd/winget",
        "Inno Setup ISCC",
        "CodeRabbit",
        "Jira REST + ADF",
        "env vars such as JIRA_API_KEY, AZURE_EMAIL, JJ_IMMUTABLE, E2E_CUSTOMER_GHCR_PAT, E2E_CUSTOMER_GHCR_USERNAME, AWS_KEY, AWS_SECRET, SQL_SUPER_USER",
    ]

    lines = []
    lines.append("# Agent Role Prompt Catalog — 2026-04-22")
    lines.append("")
    lines.append("## Summary")
    lines.append(f"- Files cataloged: {len(files)} (`/home/nes/work/agents` currently contains 31 `*.md` files; the brief says 29, so this catalog follows the directory contents)")
    lines.append(f"- GENERIC: {generality_counts['GENERIC']}")
    lines.append(f"- PROJECT_COUPLED_SOFT: {generality_counts['PROJECT_COUPLED_SOFT']}")
    lines.append(f"- PROJECT_COUPLED_HARD: {generality_counts['PROJECT_COUPLED_HARD']}")
    lines.append(
        "- Cross-reference clusters: "
        + "; ".join(
            f"`{name}` ({', '.join(f.rsplit('.md', 1)[0] for f in members)})"
            for name, members, _ in CLUSTERS
        )
    )
    lines.append("- External tool surface: " + ", ".join(f"`{tool}`" for tool in tool_surface))
    lines.append(f"- Global staleness note: {GLOBAL_STALENESS}")
    lines.append("")
    lines.append("## Catalog")
    lines.append("")

    for file in files:
        meta = CATALOG[file.name]
        lines.append(f"### {file.name}")
        lines.append(f"- **Lines**: {line_count(file)}")
        lines.append(f"- **Role**: {meta['role']}")
        lines.append(f"- **Generality**: {meta['generality']}")
        lines.append(f"- **Cross-refs**: {fmt_list(meta['cross_refs'])}")
        lines.append(f"- **External deps**: {fmt_list(meta['external_deps'])}")
        lines.append(f"- **Path strings to parameterize**: {fmt_list(meta['paths'])}")
        lines.append(f"- **Staleness flags**: {'; '.join(meta['staleness']) if meta['staleness'] else 'none'}")
        lines.append("")

    lines.append("## Clusters")
    lines.append("")
    for name, members, note in CLUSTERS:
        lines.append(f"### {name}")
        lines.append(f"- **Agents**: {fmt_list(members)}")
        lines.append(f"- **Why keep together**: {note}")
        lines.append("")

    lines.append("## Move recommendation")
    lines.append("")
    for name, meta in CATALOG.items():
        lines.append(f"- `{name}`: `{meta['recommendation']}` — {meta['recommendation_note']}")
    lines.append("")
    lines.append(f"- Aggregate `MOVE_AS_IS`: {recommendation_counts['MOVE_AS_IS']}")
    lines.append(f"- Aggregate `MOVE_WITH_PARAM`: {recommendation_counts['MOVE_WITH_PARAM']}")
    lines.append(f"- Aggregate `KEEP_IN_WORK`: {recommendation_counts['KEEP_IN_WORK']}")
    lines.append("- Ambiguous cases: `jira-operator.md`, `behavior-investigator.md`, `worktree-operator.md`, and `test-discovery.md` are operationally reusable, but they still carry enough environment assumptions that I would not move them without parameterization.")
    lines.append("- Cluster note: if the PR-justification or coverage/test clusters move, move the whole cluster together; splitting those clusters would strand hard-coded intra-agent references.")

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
