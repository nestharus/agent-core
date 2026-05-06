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

## D-2026-05-06 — NES-138 Phase 6 Tier-1 rewind (Step 6c log evidence)

**Context.** While running the implementation pipeline orchestrator on NES-138 (linter-bootstrap workflow), Phase 6's process-tree audit returned `FAIL` with one blocking finding `P6-F01`: the Step 6c R1 log (`logs/nes-138-phase-6c.log`, invocation UUID `12d2bf35-3c85-4dc2-9811-068c1b9c4f14`) succeeded with passing tests but did not echo `step6b-output-index.md` or otherwise prove it consumed the Step 6b output index. The agent had read the index (you can verify by the test pass rate against the contract), but its final summary message did not include explicit per-file-read lines.

**Decision.** Tier-1 rewind per the implementation-pipeline orchestrator's violation-escalation policy:

1. Restore worktree to pre-Step-6c state (`git restore --staged --worktree AGENTS.md README.md workflows/index.json` + `rm workflows/linter-bootstrap.md`). Step 6b's test file at `tests/test_linter_bootstrap_workflow.py` retained because the contract did not change.
2. Edit the Step 6c prompt (`prompts/nes-138-phase-6c.md`) to require an explicit `## Step 6b consumption evidence` section near the top of the response, listing all six absolute paths consumed before authoring product code. The previous Step 6c attempt was failed by the audit specifically because the log did not echo `step6b-output-index.md` even though the agent did read it.
3. Re-dispatch Step 6c (R2 invocation UUID `b2b47590-01cc-4097-8e82-1f6da500507c`); R2 log includes the consumption-evidence section.
4. Re-capture trace, re-synthesize Phase 6 R2 tree (`audits/phase6-r2-synthesized-tree.json`), re-run process-tree audit (`audits/phase6-r2-process-tree-audit.report.md`). R2 verdict: PASS, P6-F01 closed.

**Anti-scope.** Step 6b was NOT re-dispatched — the contract did not change between R1 and R2, so the test writer's prior output remains valid. Re-running Step 6b would have wasted compute and would have made R2 less faithful as a "rewind of just the failing phase."

**Justifying evidence.**

- R1 audit report (failed): `/home/nes/projects/ai/planning/nes-138-linter-bootstrap-workflow/.scratch/audits/phase6-process-tree-audit.report.md` (verdict FAIL; finding P6-F01).
- R2 audit report (passed): `/home/nes/projects/ai/planning/nes-138-linter-bootstrap-workflow/.scratch/audits/phase6-r2-process-tree-audit.report.md` (verdict PASS; P6-F01 closed).
- R1 Step 6c log lacking echo: `/home/nes/projects/ai/planning/nes-138-linter-bootstrap-workflow/.scratch/logs/nes-138-phase-6c.log`.
- R2 Step 6c log with echo: `/home/nes/projects/ai/planning/nes-138-linter-bootstrap-workflow/.scratch/logs/nes-138-phase-6c-r2.log`.
- Tests pass under R2 (`68 passed in 0.13s`); index regen idempotent.

**Re-evaluation trigger.** Revisit this rewind pattern if subsequent WUs see Step 6c logs that ALSO lack consumption-evidence echo. If the failure recurs, propose updating either `~/ai/agents/implementation-pipeline-orchestrator.md` § Phase 6 step 6c or a shared agent-prompt convention to make the consumption-evidence echo a default contract for all Phase 6 code-writer dispatches, rather than re-stating it in every WU's per-WU prompt.

## D-2026-05-06b - NES-222 / NES-219B workflow-process-auditor boundaries

**Context.** NES-222 implements the NES-219B child WU from the NES-219 audit proposer framework split. The child lands `workflow-process-auditor` as a runtime procedure-adherence auditor for completed workflow runs, plus its routing row and the durable boundary record required by the parent NES-219 proposal.

**Decision.** Accept divergence between the adjacent runtime-review operators with explicit boundaries. `workflow-reviewer` remains the narrow single-operator step-log reviewer; `workflow-process-auditor` audits multi-artifact workflow runs; step logs are supporting evidence in a broader runtime bundle.

`process-tree-auditor` remains topology / expected-process authority for trace topology, expected-process manifests, child invocations, model mapping, and companion artifact verification. `workflow-process-auditor` consumes process-tree reports as evidence and does NOT emit a substitute `PASS | FAIL` topology verdict.

**Anti-scope.** NES-222 does not modify `process-tree-auditor`, does not modify `workflow-reviewer`, does not add `audit.md`, does not wire implementation-pipeline entry modes, and does not regenerate workflow indexes. NES-219C / NES-223 owns audit sub-workflow composition; NES-219D owns implementation-pipeline entry modes and orchestrator wiring.

**Justifying evidence.**

- NES-222 proposal: `/home/nes/projects/ai/planning/nes-222-workflow-process-auditor/proposals/nes-222-NES-222.md`
- NES-222 problem map: `/home/nes/projects/ai/planning/nes-222-workflow-process-auditor/research/nes-222-problem-map.md`
- Parent NES-219 proposal: `/home/nes/projects/ai/planning/nes-219-audit-proposer-framework/proposals/nes-219-audit-proposer-framework.md`

**Re-evaluation trigger.** Revisit this boundary only if a later WU intentionally consolidates runtime review responsibilities, changes `process-tree-auditor` topology ownership, or changes `workflow-reviewer` from a narrow step-log reviewer into a multi-artifact workflow-run auditor.

## D-2026-05-06c — NES-228 Phase 6c Tier-1 rewinds for log-evidence visibility

**WU**: NES-228. **Phase**: 6c (code writer). **Decision**: `Tier-1 rewind ×2 to satisfy process-tree audit #2 invariant 4 (Step 6c log echoes Step 6b output paths)`.

**Context.** Phase 6c's first dispatch (UUID not retained) and second dispatch (UUID `3f962136-5134-4675-ad6f-de95322a69f5`) both produced correct edits to `~/ai/agents/jira-operator.md` that made all 17 Phase 6b contract tests pass. However, neither agent included the consumed-input echo block in its final assistant response — the first attempt omitted it entirely; the second attempt ran a shell `echo` that did not appear in the harness-captured `tee` log (the agents CLI logs the assistant's final response, not intermediate tool stdout). Process-tree audit #2 invariant 4 explicitly requires the Step 6c log to echo `step6b-output-index.md` as evidence of consumption.

**Decision.** Per the orchestrator's autonomous-on-destructive-git-ops policy and Tier-1 rewind rule, run `git checkout -- agents/jira-operator.md` to discard the prior attempt's product changes and re-dispatch Phase 6c with stricter prompt wording requiring the consumed-input lines in the agent's final response message text (not via shell echo). Step 6b was never rewound — its output index, residual artifact, and pytest file are unchanged across all three Step 6c attempts. The third Step 6c invocation (UUID `1308f997-d5ec-404e-8866-b2dd56e57b66`) produced both the correct operator edits AND the required echo block in its log; process-tree audit #2 returned `PASS` against this final tree.

**Anti-scope.** This rewind does NOT change the Step 6b output index, the contract, the proposal, or the audit-history's Round 1–3 records (those settled on Phase 4 R3 LOW). It does not change the test file produced in Phase 6b. It does not modify the Phase 6c prompt's substantive contract requirements — only the echo-block formatting guidance was tightened.

**Justifying evidence.**

- Process-tree audit #2 report: `/home/nes/projects/ai/planning/nes-228-jira-operator-surface-http-error/.scratch/audits/phase6-process-tree-audit.report.md` (verdict `PASS`).
- Final Step 6c log (with echo block): `/home/nes/projects/ai/planning/nes-228-jira-operator-surface-http-error/.scratch/logs/nes-228-phase-6c.log` lines 16-21.
- Phase 6b output index: `/home/nes/projects/ai/planning/nes-228-jira-operator-surface-http-error/.scratch/phase6/step6b-output-index.md` (unchanged across all three Step 6c attempts).
- Synthesized tree: `/home/nes/projects/ai/planning/nes-228-jira-operator-surface-http-error/.scratch/audits/phase6-synthesized-tree.json`.
- Expected-process manifest with Tier-1 rewind context: `/home/nes/projects/ai/planning/nes-228-jira-operator-surface-http-error/.scratch/audits/phase6-expected-process.md` § Tier-1 rewind context.

**Re-evaluation trigger.** Same as the NES-138 rewind entry above — if the Step-6c-log-echo friction recurs, canonicalize the echo-block requirement at the orchestrator/operator level rather than per-WU.

## D-2026-05-06d — NES-234 Phase 2.5.1 scope expansion to fix stale operator-name references

**WU**: NES-234. **Phase**: 2.5.1 (coverage inventory). **Decision**: `Expand scope to fix four stale operator-name references in alignment-cycle-orchestrator.md as part of the Phase 6c orchestrator-extension edit`.

**Context.** Phase 2.5.1 (coverage inventory) surfaced that `~/ai/agents/alignment-cycle-orchestrator.md` references operator files that do not exist: `problem-expansion.md` (lines 24, 75) and `philosophy-expansion.md` (lines 25, 135). The actual files in `~/ai/agents/` are `problem-expansion-integrate.md` and `philosophy-expansion-integrate.md`. The workflow doc `~/ai/workflows/alignment-cycle.md` and `~/ai/AGENTS.md` already reference the `*-integrate.md` names; the orchestrator doc is the only stale source. NES-234 will edit this same file to add the empty-state bootstrap prelude.

**Decision.** Per the bug-disposition contract in `~/ai/agents/implementation-pipeline-orchestrator.md` § Phase 2.5.1 step 4, the user (via root-orchestrator-question artifact `q-ddbaaa93-ab20-454d-9add-e776903410e4`) selected option A: expand scope to fix the four stale references in the same Phase 6c orchestrator-extension edit. The extension touches the same four-line region (Stage 1b/2b dispatch lines + the dispatch-targets table at the top of the file), so the typo fix sits next to the new empty-state prelude rather than in a separate edit.

**Anti-scope.** This expansion does NOT change the Stage 1/1b/2/2b sub-agent files themselves (`problem-expansion-integrate.md`, `philosophy-expansion-integrate.md`, etc. are untouched). It does NOT change `~/ai/workflows/alignment-cycle.md` or `~/ai/AGENTS.md` (already correct). It is a name-substitution-only change in the orchestrator doc. No separate tracker ticket is filed because the fix lands in this WU.

**Justifying evidence.**

- Question artifact: `/home/nes/projects/ai/planning/nes-234-bootstrap-operators/.scratch/questions/q-ddbaaa93-ab20-454d-9add-e776903410e4.question.json`.
- Answer artifact: `/home/nes/projects/ai/planning/nes-234-bootstrap-operators/.scratch/questions/q-ddbaaa93-ab20-454d-9add-e776903410e4.answer.json`.
- Coverage inventory: `/home/nes/projects/ai/planning/nes-234-bootstrap-operators/research/nes-234-coverage-inventory.md` § 5 Bug Discovery.
- Stale references confirmed via `grep -n 'problem-expansion\|philosophy-expansion' /home/nes/ai/agents/alignment-cycle-orchestrator.md` → lines 24, 25, 75, 135.
- Actual files confirmed via `ls /home/nes/ai/agents/ | grep -E '(problem|philosophy)-(expansion)'` → only `*-classify.md` and `*-integrate.md` exist.

**Re-evaluation trigger.** Revisit this scope expansion only if Phase 4 risk gates flag the typo fix as out-of-scope (which would require splitting the WU). Otherwise the fix lands in Phase 6c alongside the bootstrap prelude.

## D-2026-05-06e — NES-207 Phase 2.5 drift-discovery accepted with residual

**WU**: NES-207 (`code-quality workflow`). **Phase**: 2.5.4 (duplicate-systems inventory). **Decision**: `Accept drift residual; file tracker NES-235; do not modify auditor operators in NES-207 per brief anti-scope.`

**Context.** Phase 2.5 duplicate-systems inventory at `/home/nes/projects/ai/planning/nes-207-code-quality-workflow/research/nes-207-duplicates.md § Drift discoveries` surfaced stale `cohesion-coupling-auditor.md` references in `agents/push-pull-auditor.md:138,147`, `agents/function-classification-auditor.md:148,157`, `agents/workflow-design-auditor.md:29`, `agents/agent-design-auditor.md:27`, `conventions/design-patterns.md:32,50,80`, and `tests/test_push_pull_auditor_operator.py:487`. The bundled file was removed by NES-209's split into single-concern `cohesion-auditor.md` + `coupling-auditor.md`; NES-209 missed updating these references. Verified `tests/test_push_pull_auditor_operator.py::test_b31_cross_references_targets` and `tests/test_function_classification_auditor_operator.py::test_t11_sibling_boundaries_exclude_adjacent_scopes` still pass (string-tolerant assertions); no test currently fails against HEAD.

**Decision.** Per NES-207's brief anti-scope ("Do NOT modify any auditor operator. They're complete."), drift cleanup is out of scope for this WU. Filed Linear tracker `NES-235` ("Cleanup: stale cohesion-coupling-auditor.md references after NES-209 split") to capture the work. The new `workflows/code-quality.md` will reference the split single-concern auditors directly and will not depend on the missing bundled operator. NEEDS_INPUT to root not surfaced because the brief's anti-scope already supplies the disposition; per the orchestrator NEEDS_INPUT classification, a question the brief already answers is procedural.

**Anti-scope.** This decision does not commit NES-207 to fixing any of the listed stale references. It does not update tests, conventions, or auditor docs. NES-235 is the cleanup vehicle.

**Justifying evidence.**

- Duplicate-systems inventory drift section: `/home/nes/projects/ai/planning/nes-207-code-quality-workflow/research/nes-207-duplicates.md` lines 183-250.
- Coverage inventory bug-discovery (verified false; tests pass): `/home/nes/projects/ai/planning/nes-207-code-quality-workflow/research/nes-207-coverage-inventory.md` line 5; pytest run shown in NES-207 Phase 2.5 orchestrator log.
- Tracker ticket: `NES-235` (https://linear.app/neshq/issue/NES-235/cleanup-stale-cohesion-coupling-auditormd-references-after-nes-209).
- NES-207 brief anti-scope: dispatcher message body for NES-207 implementation pipeline run.

**Re-evaluation trigger.** If a future test added against `agents/cohesion-auditor.md` / `agents/coupling-auditor.md` cross-references catches the stale text and starts failing on HEAD, NES-235 is bumped from "discovered drift" to "blocking" priority and a separate Tier-1 rewind on the failing surface is taken.

## D-2026-05-06f — NES-207 Phase 4 Tier-1 redispatch (shared claude-opus session)

**WU**: NES-207. **Phase**: 4 (process-tree audit #1). **Decision**: `Tier-1 redispatch of phase4-supported-surface gate to break shared session/chain with phase4-scope.`

**Context.** Phase 4 risk gates returned LOW × 4. Process-tree audit #1 (`/home/nes/projects/ai/planning/nes-207-code-quality-workflow/.scratch/audits/phase4-process-tree-audit.report.md`) returned BLOCKING with one violation: `phase4-scope` (UUID `6f60f218-d85b-4641-ad0f-f437fa6628f1`) and `phase4-supported-surface` (UUID `245535d0-750c-4a6d-ada9-b911b77abca4`) share session `cce04028-b488-4c07-ad2f-b8ab564cf3b6` and chain `778ca4c7-edab-4b04-99c5-6cf4ca026239`. Both ran on `claude-opus` within ~8 s of each other; `phase4-shortcut` (also claude-opus, ~4 s after scope) got a distinct session, so the claude-opus provider does not deterministically reuse sessions — the collision is incidental rather than systemic. The expected-process manifest's independence invariant treats shared sessions as a blocking integrity violation regardless of report content.

**Decision.** Per the orchestrator's autonomous-on-process-tree-violations rule, re-dispatch only `phase4-supported-surface` as a fresh `agents` invocation; keep the existing scope/audit/shortcut reports (all LOW × 3 are unchanged). The supported-surface report file is overwritten in place. After redispatch, re-fetch `agents trace --json` and re-run process-tree audit #1.

**Anti-scope.** This redispatch does NOT change the Phase 3 proposal, the risk profile, the supported-surface gate's substantive prompt, or the other three Phase 4 gates. It only re-runs the one invocation that collided on session/chain.

**Justifying evidence.**

- Process-tree audit #1 BLOCKING report: `/home/nes/projects/ai/planning/nes-207-code-quality-workflow/.scratch/audits/phase4-process-tree-audit.report.md` lines 23, 25, 55.
- Phase 4 expected-process manifest invariant 1: `/home/nes/projects/ai/planning/nes-207-code-quality-workflow/.scratch/audits/phase4-expected-process.md` § Required invariants.
- Trace JSON (pre-redispatch): `/home/nes/projects/ai/planning/nes-207-code-quality-workflow/.scratch/audits/trace-full.json`.

**Re-evaluation trigger.** If `claude-opus` provider sessions collide across re-dispatch attempts more than twice on the same WU, the manifest invariant should be relaxed at the convention level (or session-isolation guarantees added to the agents CLI), not reapplied per-WU.

## D-2026-05-06g — NES-207 Phase 6c BLOCKED reclassified as not-blocking

**WU**: NES-207. **Phase**: 6c (code writer). **Decision**: `Reclassify Step 6c agent's BLOCKED return as a misclassification of pre-existing repo state; proceed without re-dispatch.`

**Context.** The Step 6c gpt-high agent (UUID `b891eb51-04e7-4c86-967d-092a5b7c9be0`) returned `BLOCKED:full pytest fails in existing Linear CLI tests outside the allowed NES-207 edit scope` after producing all five product files and confirming the four NES-207-relevant gate suites pass:

- `pytest tests/test_code_quality_workflow_shape.py` — 23 passed
- `pytest tests/test_workflow_metadata.py tests/test_workflow_index.py` — pass with user-owned `TMPDIR`
- `pytest tests/test_agentsmd_structure.py tests/test_code_quality_convention.py` — 16 passed
- `pytest` (full suite) — 19 failed, 422 passed; failures are in `clients/linear/tests/test_cli_unit.py` with `ModuleNotFoundError: No module named 'scripts'`.

The orchestrator verified the failures are pre-existing on `origin/master @ d3d627e`: stashing the NES-207 worktree changes and running the same Linear CLI suite reproduced `13 failed, 6 errors`. The failures are independent of NES-207's deliverable and outside its anti-scope ("Do NOT modify any auditor operator. They're complete." plus the brief's restriction to the workflow file + cross-references).

**Decision.** The orchestrator (judge) overrules the Step 6c agent's BLOCKED return: NES-207's product code is correct, all WU-relevant gates pass, and the pre-existing CLI suite failure is unrelated to this WU. No Tier-1 redispatch. The pipeline proceeds to process-tree audit #2 with the existing Step 6c invocation as the authoritative product.

**Anti-scope.** This decision does NOT fix the Linear CLI test failures. Those are tracked separately (or should be — if no tracker exists, a future hardening WU can file one). It does not weaken any test, modify any product code, or change any other Phase 6 artifact.

**Justifying evidence.**

- Pre-existing failure verification: `git stash` on the NES-207 worktree, `python3 -m pytest clients/linear/tests/test_cli_unit.py` returns `13 failed, 6 errors` with the same `ModuleNotFoundError`. Reproduction shown in the orchestrator's Phase 6c diagnostic Bash run.
- NES-207 product gates pass: 62 passed in `pytest tests/test_code_quality_workflow_shape.py tests/test_workflow_metadata.py tests/test_workflow_index.py tests/test_agentsmd_structure.py tests/test_code_quality_convention.py` with `TMPDIR=/home/nes/tmp`.
- Step 6c log: `/home/nes/projects/ai/planning/nes-207-code-quality-workflow/.scratch/logs/nes-207-phase-6c.log` includes the verbatim "Step 6c consumed:" block and the gate-result block.
- Brief anti-scope: NES-207 dispatch text "Do NOT modify any auditor operator" and "Workflow file at `~/ai/workflows/code-quality.md` plus minor cross-references in `~/ai/conventions/code-quality.md` and `~/ai/AGENTS.md` Workflow Topologies index."

**Re-evaluation trigger.** If a future ~/ai-layer WU touches the Linear CLI client surface and the same test failures persist, file a hardening tracker for the `ModuleNotFoundError: No module named 'scripts'` import path and treat this DECISIONS entry as evidence that the failure precedes that WU.
