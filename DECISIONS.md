# DECISIONS — `~/ai/`

Decisions taken at the `~/ai/` (workflow + operator + client) layer. Distinct from per-project `DECISIONS.md` which records per-project narrowings, terminations, and accepted residuals.

## D-2026-05-05 — NES-219 Phase 2.5 defer-to-prototype gate disposition

**Context.** Phase 2.5 risk profile for NES-219 (`audit + proposer framework`) rolled up `HIGH` with `defer-signals-fired=2`:

1. Risk profile rolls up HIGH on a majority of touched surfaces (6 of 8 surfaces are HIGH).
2. Cross-language trace shows implicit contracts in so many sites that change-path entropy is HIGH on its own.

Per `~/ai/workflows/implementation-pipeline.md` § Defer to prototype, two or more fired signals trigger the orchestrator's defer-to-prototype gate (`proceed in exhaustive mode`, `defer to prototype`, or `terminate WU`). Per the orchestrator spec, `skip_problem_map_gate=true` does not suppress this defer-detection; it only suppresses the routine problem-map approval.

**Decision.** Proceed in exhaustive mode without a separate human round-trip. The dispatching user already evaluated the defer/proceed/terminate trade-off in the dispatch text (NES-219 framed as urgent / "highest priority" / "this unblocks ALL subsequent workflow / agent design work"; explicit Tier-2 split shapes A–E pre-described; "Tier-2 split is EXPECTED and ENCOURAGED"; explicit `NEEDS_INPUT` contract restricts root escalation to "genuine value/scope questions only — e.g., the corpus shape choice"). The defer/terminate options are implicitly declined; the corpus-shape question is the only genuine value question reserved for root escalation, and it is deferred to Phase 3 per the dispatch.

**Mode propagation.** Phase 3 / 4 / 5 / 6b run in **exhaustive mode** for the six HIGH surfaces (`workflow-design-auditor`, `agent-design-auditor`, `workflow-process-auditor`, `audit.md`, `implementation-pipeline.md`, corpus-surface candidates), **lean with MEDIUM callouts** for `~/ai/AGENTS.md`, and **lean** for the `workflows/index.json` regeneration. Phase 3 is asked to evaluate single-WU vs Tier-2 split as a packaging decision and to surface that recommendation in the proposal.

**Project-level aggregation.** The MEDIUM/HIGH surfaces from `risk/nes-219-risk-profile.md` are appended to `/home/nes/projects/ai/planning/risk-profile.md` per `~/ai/conventions/risk-profile.md` § Project-level profile.

**Evidence.**

- Risk profile: `/home/nes/projects/ai/planning/nes-219-audit-proposer-framework/risk/nes-219-risk-profile.md`
- Problem map: `/home/nes/projects/ai/planning/nes-219-audit-proposer-framework/research/nes-219-problem-map.md`
- Phase 2.5 sub-step inventories: `/home/nes/projects/ai/planning/nes-219-audit-proposer-framework/research/nes-219-{coverage-inventory,lifecycle-map,entrypoints,duplicates,cross-language-trace}.md`

## D-2026-05-05 — NES-219 Tier-2 split into NES-219A–E

**Context.** NES-219 is a meta/planning WU for the audit proposer framework. Phase 4 cleared the proposal, but the approved proposal and Step 6a contract both require a Tier-2 split because the work rolls up HIGH across distinct review contracts: corpus/design-auditor substrate, runtime procedure auditing, audit workflow composition, implementation-pipeline entry modes, and mechanical routing/index closure. Filing the child WUs keeps NES-219's parent PR limited to the durable decision record while the framework files land in separately reviewable implementation WUs.

**Decision.** NES-219 is split under parent NES-219 into these child WUs, filed in dependency order:

1. `NES-219A` / Linear `NES-221` — no dependency — Corpus and design-auditor substrate: add `~/ai/conventions/design-patterns.md`, `~/ai/agents/workflow-design-auditor.md`, `~/ai/agents/agent-design-auditor.md`, and only the AGENTS.md rows needed for those operators.
2. `NES-219B` / Linear `NES-222` — depends on `NES-219A` — Workflow process auditor: add `~/ai/agents/workflow-process-auditor.md` with runtime evidence bundle, `process-tree-auditor` boundary, `workflow-reviewer` boundary, and its AGENTS.md row.
3. `NES-219C` / Linear `NES-223` — depends on `NES-219A` and `NES-219B` — Audit sub-workflow: add `~/ai/workflows/audit.md`, target typing, dispatch manifest, auditor routing, aggregate verdict schema, finding normalization, audit-history ownership, rerun semantics, process-tree relationship, standalone/pipeline-callable modes, index regeneration, and Workflow Topologies routing.
4. `NES-219D` / Linear `NES-224` — depends on `NES-219C` — Implementation-pipeline entry modes plus orchestrator wiring plus proposer-research integration: add `review_first` and `plug_existing_review`, dispatch/validation/staleness handling in `implementation-pipeline-orchestrator.md`, audit-bundle consumption, Phase 3 finding handoff, current re-audit after substantive revision, and conditional AGENTS routing updates.
5. `NES-219E` / Linear `NES-225` — depends on `NES-219A-D` — Cross-reference and structural verification closure: perform final AGENTS.md reachability audit, `workflows/index.json` check, targeted workflow metadata/index tests, and any follow-up structural tests chosen during child-WU Phase 6b.

The parent NES-219 worktree must not add the operator, workflow, corpus, AGENTS, or generated-index files for these child WUs; those changes belong to NES-221 through NES-225.

**Cross-references.**

- Proposal artifact: `/home/nes/projects/ai/planning/nes-219-audit-proposer-framework/proposals/nes-219-audit-proposer-framework.md`
- Audit history: `/home/nes/projects/ai/planning/nes-219-audit-proposer-framework/audit-history.md`
- Hookpoints: `/home/nes/projects/ai/planning/nes-219-audit-proposer-framework/research/nes-219-hookpoints.md`
- Contract: `/home/nes/projects/ai/planning/nes-219-audit-proposer-framework/contracts/nes-219-meta-deliverable.md`

**Evidence.**

The Linear filing map is recorded in `/home/nes/projects/ai/planning/nes-219-audit-proposer-framework/.scratch/phase6/sub-wu-tickets.txt`; NES-221 through NES-225 were parent-linked to NES-219 with the saved NES-219 UUID.

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

---

## D-2026-05-05d - NES-154 brenner_bot and research-team coexist

**WU**: NES-154. **Phase**: 6c implementation of the Phase 3 decision-only proposal. **Decision**: `coexist`.

**Context.** NES-154 compared upstream `brenner_bot` with the planned NES-151 `research-team` workflow. Upstream `brenner_bot` is a scientific-method research system: its method centers on problem selection, parallel hypotheses, discriminative tests, Bayesian update, and iteration; its operator set is 17 scientific-method moves; its repo describes a product/runtime with Agent Mail, ntm, Bun CLI, Next.js web app, and lab-like artifacts. The closest landed `/home/nes/ai/` research workflow is a markdown/operator workflow for open-ended investigation, option analysis, external-source review, feasibility assessment, comparable-product study, and evidence-backed synthesis. NES-151 `research-team` has not yet landed a concrete workflow artifact under `/home/nes/ai/workflows/`.

**Decision.** Keep `brenner_bot` and `research-team` as separate research mechanisms. Route literature-shaped, scientific, hypothesis-evidence, methodology-driven questions to `brenner_bot` or a future explicitly chartered successor. Route design-pattern, best-practice, library, tool, implementation-approach, and comparable-product questions to `research-team` once NES-151 lands, with `/home/nes/ai/workflows/research.md` remaining the landed generic precursor until then. Do not treat `research-team` as replacing `brenner_bot`, and do not import or invoke `brenner_bot` from `research-team` without a later integration WU.

**Anti-scope.** This decision does NOT include code changes to `/home/nes/ai/` workflows, operators, conventions, tests, or clients; upstream `brenner_bot` modifications; a fork or upstream PR; implementation of an integration; Linear status transitions; or resurrection of structural tests for `/home/nes/ai/DECISIONS.md` or `/home/nes/ai/AGENTS.md`.

**Justifying evidence.**

- NES-154 problem map: `/home/nes/projects/ai/planning/nes-154-brenner-bot-disposition/research/nes-154-problem-map.md`
- Upstream method scrape: `/home/nes/projects/ai/planning/nes-154-brenner-bot-disposition/research/upstream/brennerbot-method.md` from `https://brennerbot.org/method` scraped 2026-05-05.
- Upstream operators scrape: `/home/nes/projects/ai/planning/nes-154-brenner-bot-disposition/research/upstream/brennerbot-operators.md` from `https://brennerbot.org/operators` scraped 2026-05-05.
- Upstream repo clone: `/tmp/brenner_bot_clone/README.md`, `/tmp/brenner_bot_clone/AGENTS.md`, and `/tmp/brenner_bot_clone/LICENSE`.
- Duplicate inventory: `/home/nes/projects/ai/planning/nes-154-brenner-bot-disposition/research/nes-154-duplicates.md` found no prior `brenner_bot` decision and no landed NES-151 `research-team` workflow artifact.
- Risk profile: `/home/nes/projects/ai/planning/nes-154-brenner-bot-disposition/risk/nes-154-risk-profile.md` scored both touched docs surfaces LOW.

**Re-evaluation trigger.** Revisit this decision if NES-151 lands a `research-team` workflow with a stable downstream-researcher extension point, if a future WU is chartered to create a license-safe `brenner_bot` integration or successor, if upstream `brenner_bot` materially changes its method/runtime/licensing, or if a future scientific-literature WU demonstrates that the coexist boundary misroutes real work.
