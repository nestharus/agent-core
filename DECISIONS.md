# DECISIONS — `~/ai/`

Decisions taken at the `~/ai/` (workflow + operator + client) layer. Distinct from per-project `DECISIONS.md` which records per-project narrowings, terminations, and accepted residuals.

## D-2026-05-04 — Linear-backed pipeline bootstrap exception

**Context.** The implementation-pipeline-orchestrator (`~/ai/agents/implementation-pipeline-orchestrator.md`) was originally JIRA-only. The `agent-runner` project chose Linear as its ticket system, not JIRA. Adding Linear support is itself meaningful work, and the orchestrator-compliant path requires a working ticket source — but no Linear-backed orchestrator exists yet, so there is no compliant way to track the work that creates the Linear-backed orchestrator. Chicken-and-egg.

**Decision.** Bootstrap the Linear path manually as a one-time documented exception. The boot work consists of:

1. **BOOT-01** — Port the Linear Python client from `nestharus/ai-workflow` `init` branch (`scripts/clients/linear_client.py`, `scripts/clients/linear_cli.py`, plus tests + usage doc) to `~/ai/clients/linear/`. Imports rewritten to `from clients.linear.client import …` (consumed with `PYTHONPATH=$HOME/ai`). Stdlib-only; no pypi deps for the client itself; test deps `pytest`, `pytest-mock`.
2. **BOOT-02** — Author `~/ai/agents/linear-operator.md` (claude-haiku) parallel to `jira-operator.md`. Tasks: `read`, `comment`, `create`, `search`. No `transition` task — Linear status changes are user-owned per `linear-operator.md` § Do Not Use When. Invocations shell out to `python3 -m clients.linear.cli` with `PYTHONPATH=$HOME/ai`.
3. **BOOT-03** — Patch `~/ai/agents/implementation-pipeline-orchestrator.md` and `~/ai/workflows/implementation-pipeline.md` to add a Ticket System Pluggability table. The orchestrator now accepts either `jira_issue_key` or `linear_issue_key` and routes ticket dispatches to the matching operator (`jira-operator` or `linear-operator`). Format substitution is explicit: JIRA path renders ADF, Linear path passes Markdown verbatim.

**Anti-scope.** This bootstrap does NOT include:

- A pluggable status-transition path (Linear's transition is intentionally absent).
- A unified abstraction layer that hides the format difference inside the orchestrator (deferred to a future orchestrator-driven WU once Linear-backed work is flowing).
- Github-client port and `nestharus/ai` repo creation — tracked separately and intended to run through the orchestrator after BOOT is complete.
- Per-project private ai repos — tracked separately, deferred to first project that needs them.

**Justifying evidence.**

- User-stated direction: "Port Linear client first, then bootstrap operator" (chosen Bootstrap path).
- User-stated source repo: `nestharus/ai-workflow` `init` branch.
- User-stated client preference: client over MCP for operator/workflow use.
- Live verification: `clients.linear.client.LinearClient` lists team `NES` (Neshq) successfully against `https://api.linear.app/graphql` with `$LINEAR_API_KEY`.

**Compliance posture going forward.** All subsequent Work Units (BOOT-06 github-client port, BOOT-07 `nestharus/ai` repo creation, BOOT-08 Linear label/view setup, BOOT-09 per-project ai repos, and the entire `agent-runner` refactor backlog WU-PREREQ-01..05 + WU-PREREQ-AGENT-BIN) MUST go through `implementation-pipeline-orchestrator` via `agents -m claude-opus -a ~/ai/agents/implementation-pipeline-orchestrator.md …`. No further inline orchestration. Each WU produces a real `agents trace --json` audit tree that `process-tree-auditor` can audit per-phase.

**Re-evaluation trigger.** This exception is one-time. If a similar bootstrap need surfaces in the future (e.g. adding a third ticket system, or replacing the orchestrator wholesale), the answer is to execute it via the orchestrator itself — split the bootstrap into the smallest sub-WU that the existing infrastructure can handle, then escalate per the violation-escalation policy if it cannot.

---

## D-2026-05-04b — Linear client label CRUD extension (bootstrap continuation)

**Context.** WU-PREREQ-01 (segmentation) shipped successfully through the orchestrator but the Phase 0 cold-start surfaced a `NEEDS_INPUT` because the ported Linear client lacked label CRUD. The user resolved that question with the explicit instruction "I'm not setting up linear team/project/labels. You are." This decision records the manual extension that closed the gap.

**Decision.** Extend `~/ai/clients/linear/client.py` and `~/ai/clients/linear/cli.py` with label management:

1. `LinearClient.list_labels(team)` — workspace + team-scoped labels.
2. `LinearClient.create_label(team, name, color?, description?)` — `issueLabelCreate` mutation.
3. `LinearClient.resolve_label_ids(team, label_names, create_missing=False)` — name → UUID resolver, optionally creating missing.
4. `LinearClient.apply_labels(issue_id, team, label_names, create_missing=False, replace=False)` — merges by default; queries the issue's current labels via direct GraphQL because `get_issue` does not include them in its return shape.
5. CLI subcommands: `list-labels`, `create-label`, `apply-labels`.
6. CLI flags on `create-issue`: `--labels NAME1,NAME2,...` and `--create-missing-labels`.

`linear-operator.md` updated to document the new commands and the merge-vs-replace semantics.

**Anti-scope.** This decision does NOT include:

- Status transitions on labels (Linear has no such concept).
- A view / board CRUD path (Linear `customViewCreate`). Tracked separately as BOOT-08.
- A unified label-conventions doc; per-project label conventions live in each project's `AGENTS.md`.
- Fixing `get_issue` to include labels in its return shape. The pre-existing port-level deficiency remains; `apply_labels` works around it. A future orchestrator-driven WU on the Linear client can fix it properly.

**Labels created on team `NES`.** With colors and descriptions:

| Name | Color | Description |
|---|---|---|
| `agent-runner` | `#5e6ad2` | (pre-existing on Linear UI) |
| `segmentation` | `#26b5ce` | (pre-existing on Linear UI) |
| `prereq` | `#3dc1f0` | Prerequisite work that unblocks downstream work units |
| `workspace-split` | `#ffa500` | Cargo workspace split / multi-crate restructuring |
| `~/ai` | `#8b5cf6` | `~/ai` ecosystem-level work (workflows / operators / clients / tools) |
| `bootstrap` | `#f59e0b` | One-time bootstrap / scaffolding work; documented exception |
| `hardening` | `#dc2626` | Risk-reduction / robustness work per `~/ai/conventions/risk-profile.md` |

NES-128 (the WU-PREREQ-01 ticket) was retroactively labeled `agent-runner`, `segmentation`, `prereq`. NES-129 (the drift follow-up) was retroactively labeled `agent-runner`, `segmentation`.

**Justifying evidence.** The first orchestrator dispatch was forced to drop labels because the client could not apply them; user has been clear that label setup is an automation responsibility, not a user responsibility. Closing the capability gap unblocks all downstream WUs (PREREQ-02..05, BOOT-06..09) from surfacing the same NEEDS_INPUT.

**Re-evaluation trigger.** Same as the parent D-2026-05-04: any further client extension goes through the orchestrator. The only justification for this manual extension is that it directly closes a NEEDS_INPUT raised by the very bootstrap pipeline that the user authorized to be a one-time exception.

---

## D-2026-05-05 — NES-137 scope expansion: delete NES-142 branch-diff scope-guard test

**Context.** During NES-137 (A1 — code-quality convention) Phase 7 → Phase 8 handoff, the orchestrator rebased the `nes-137-code-quality-convention` branch onto current `origin/master` (`05757d7`, the NES-142 workflow-aliases merge). After rebase, `pytest -q tests/` failed on `tests/test_workflow_aliases_convention.py::test_branch_diff_only_contains_convention_and_tests` — a test introduced by NES-142 that hard-codes `ALLOWED_DIFF_PATHS = {conventions/workflow-aliases.md, tests/test_workflow_aliases_convention.py}` and runs `git diff --name-only master...HEAD`, asserting equality. That assertion was correct on the NES-142 branch (single-convention scope-guard) but was not generalized at merge; on `master` it fails on every other branch by construction.

The orchestrator surfaced this as a new-value scope question to the root per `~/ai/agents/implementation-pipeline-orchestrator.md` § NEEDS_INPUT handling.

**Decision.** Expand NES-137's scope just enough to delete that one function (`test_branch_diff_only_contains_convention_and_tests`), the now-unused `ALLOWED_DIFF_PATHS` constant, and the now-unused `import subprocess` at the top of `tests/test_workflow_aliases_convention.py`. The other tests in that file (covering required sections, dispatch contract, schema keys, anti-pattern callouts, relative-link resolution) remain intact.

**Justifying evidence.** Linear NES-163 (`https://linear.app/neshq/issue/NES-163/nes-142-follow-up-branch-diff-structural-test-asserts-only-convention`) tracks the structural fix on the NES-142 surface (generalize the assertion, move it to a PR template, or scope it to a deselected directory). Until that lands, the test is a strict pre-merge blocker for every WU branch. The minimum scope expansion that unblocks NES-137 and every future WU is to remove the assertion from the test suite on this branch; the NES-163 ticket carries the task forward.

**Anti-scope.** This decision does NOT:

- Modify any other test in `tests/test_workflow_aliases_convention.py`.
- Modify `conventions/workflow-aliases.md` (the convention itself stays as merged).
- Backport this fix to NES-142's branch retroactively.
- Generalize the assertion or migrate it to a PR template — that's NES-163's job.

**Re-evaluation trigger.** When NES-163 lands, NES-137's scope expansion documented here is closed. Future WUs should NOT remove `test_workflow_aliases_convention.py` tests as a matter of course; the deletion here is targeted, evidenced, and tracker-backed. If NES-163 reintroduces the test in a generalized form (option 1 in the brief), no further action on this WU is needed; the deletion here is forward-compatible with that fix.

---
