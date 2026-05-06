---
workflow:
  id: implementation-pipeline
workflow_dispatch_contract:
  orchestrator: "implementation-pipeline-orchestrator"
  inputs:
    - "ticket id and branch, worktree, scratch, and planning paths"
    - "non-empty ticket description from the configured Jira or Linear ticket system"
    - "optional pipeline_entry_mode normal, review_first, or plug_existing_review with audit target or existing review bundle inputs when that mode requires them"
  expectations:
    - "runs research, proposal, risk, hookpoint, implementation, CodeRabbit, review, PR, and audit phases"
    - "defaults to normal mode; review_first runs audit after Phase 0 and before Phase 2.5, while plug_existing_review validates a current audit bundle before Phase 3 consumes it"
    - "uses model-owned gates; default flow exposes only Phase 2.5 review and NEEDS_INPUT new-value questions, with an additional Phase 8.5 human gate in the tickets-first variant"
    - "keeps tests and product code separated between Phase 6b and Phase 6c invocations"
  outputs:
    - "planning artifacts under the per-WU planning directory"
    - "tested repository diff and draft PR URL when the work proceeds"
    - "ticket comments and audit-history closure evidence at PR and finalization points"
  non_goals:
    - "does not use git-resident ticket files as the source of truth"
    - "does not skip phases implicitly"
    - "does not inline the orchestrator role into the root conversation"
---
# Implementation Pipeline

End-to-end pipeline from triggering event to merged PR.
Bugs start with RCA. Features, refactors, and other planned work skip RCA.

## Tickets live on the project's ticket system, not on disk

Every Work Unit is an issue on the project's configured ticket system — currently either **JIRA** (Atlassian) or **Linear**, selected per project. The orchestrator dispatches the matching ticket operator at Phase 0 bootstrap (`~/ai/agents/jira-operator.md` for JIRA, `~/ai/agents/linear-operator.md` for Linear) to read (or first-draft) the ticket and renders the description into the per-WU `${scratch_dir}/ticket.md`. The ticket only needs a non-empty description; scope, code and test boundaries, acceptance criteria, and anti-scope are **derived** during Phase 2.5 (problem map), Phase 3 (proposal), and Step 6a (contract) — not pre-declared on the ticket. Pre-declared boundaries are brittle: real surface and scope are discovered during research, and forcing them upfront either creates inaccurate inputs the pipeline then trusts or blocks tickets that could otherwise proceed. There is **no** `plans/tickets/<phase>/<wu_id>.md` file in git for this pipeline. The orchestrator does not read from such a path. If a project's `AGENTS.md` still references the old git-resident ticket convention, treat the orchestrator's input contract (`~/ai/agents/implementation-pipeline-orchestrator.md`) as authoritative and update the project doc.

**Ticket-system selection** is per-project: each project's `AGENTS.md` declares either `ticket_system: jira` (with `jira_url`, `jira_project`, `jira_account_email`) or `ticket_system: linear` (with `linear_team_key` and optional `linear_project_id`). The orchestrator's pluggability table (in `~/ai/agents/implementation-pipeline-orchestrator.md` § Ticket System Pluggability) is the authoritative input contract. JIRA descriptions and comments use ADF; Linear uses Markdown natively. The orchestrator routes operator dispatches accordingly, so phase procedures below speak generically about "the ticket" rather than calling out one system unless the difference matters.

The orchestrator comments back to the ticket on Phase 9 (PR URL) and on Final (audit-history close + decision tail). Status transitions remain user-owned regardless of ticket system; the JIRA `transition` task supports them for downstream workflows that need it, but the orchestrator itself does not transition status.

Model assignments are authoritative in `~/ai/models/roles.md`.
Do not restate or override that matrix in project docs.
Use it exactly, including the synthesis/audit-vs-judgment split and the rule that `gpt-xhigh` is not the default coordinator.

Agent invocation: `~/ai/workflows/agents-cli.md`
Agent Q&A and session graph convention: `~/ai/conventions/agent-questions-and-session-graph.md`
Parallel-agent isolation: `~/ai/conventions/worktree-isolation.md`
Git and PR conventions: `~/ai/conventions/git.md`
Audit-history convention for revise/review loops: `~/ai/conventions/audit-history.md`
Proposer/critic pattern for proposal risk gates: ~/ai/conventions/proposer-critic-pattern.md
Process-tree review operator: `~/ai/agents/process-tree-auditor.md`
Workflow-execution violation taxonomy: `~/ai/conventions/workflow-execution-violations.md`
Rebase verification gate: `~/ai/conventions/rebase-verification.md`
WU session lifecycle (spawn → run → merge → post-merge wake): `~/ai/conventions/wu-session-lifecycle.md`

## Principles

- **Separate agents for separate concerns.** RCA agents do not propose. Proposal agents do not implement. Review agents do not self-certify.
- **Avoid the solution-fixation trap.** An agent that just researched a problem is already biased toward the first solution it noticed.
- **Zero-risk gate.** Implementation does not begin until every required risk report returns `LOW`.
- **No cherry-picking risk feedback.** If any risk report returns `MEDIUM` or `HIGH`, revise the proposal and re-run the full risk gate.
- **Risk drives decomposition.** Do not decompose because something looks complex; decompose when audit or alignment risk exceeds what one agent can reliably handle.
- **Alignment is directional.** Alignment asks "is this going the right way?" Coverage remains the audit's job.
- **Research before implementation.** Hookpoint research finds reuse points, collisions, and deletion candidates before code is written.
- **Nothing is skipped implicitly.** Skip a phase only by explicit written decision in `DECISIONS.md` or the project equivalent.
- **No backwards-compatibility shims.** See `~/ai/conventions/no-backwards-compatibility.md`.
- **No deferred stubs.** See `~/ai/conventions/no-deferred-stubs.md`.
- **The risk gate is the proposal review.** Do not add a redundant human approval step on top of it.
- **Human gating is restricted.** The only two surviving human-gate triggers are (1) Phase 2.5 problem-map review and (2) any sub-agent NEEDS_INPUT that surfaces a new value, scope, or trade-off question the orchestrator cannot decide. Phase 0/1/2/5 and Phase 10 promotion are non-human-gated; the orchestrator advances them autonomously when their model gates clear.
- **Draft PRs are routine; promotion is automated.** Opening and promoting draft PRs are both automated by the orchestrator under the violation-escalation policy.
- **RCA-track verification.** On the RCA track, every reproduced hypothesis becomes a test that closes the coverage gap that allowed the bug to ship. The fix is not complete until each pre-fix red test runs green post-fix, and the before/after evidence travels in the PR. There is no separate "reproduction harness" or "regression harness" construct — bug-driven tests are tests, indistinguishable in form from coverage-expansion tests written outside the RCA track. The "regression" framing is just a consequence of where the test came from, not a different category of artifact.

## Phase Map

Optional phases:
- `Phase 0` RCA for bugs only
- `Phase 1` problem research
- `Phase 2` synthesize user needs
- `Phase 4.5` alignment for governance-heavy projects
- `Phase 8.5` human local review gate (tickets-first variant only)

Core path:
- `Phase 2.5 -> Phase 3 -> Phase 4 -> Phase 5 -> Phase 6 -> Phase 7 -> Phase 8 -> Phase 9 -> Phase 10`

## Entry Modes

Entry modes select how audit evidence enters the implementation pipeline. They do not change the phase ownership rules, do not add a new operator, and do not skip phases implicitly.

### `normal` (default)

`normal` is the default when `pipeline_entry_mode` is absent or explicitly `normal`. The orchestrator runs the existing Phase 0 ticket/worktree/bootstrap route and then continues through Phase 2.5, Phase 3, Phase 4, Phase 5, Phase 6, Phase 7, Phase 8, Phase 9, and Final/closure as before. It does not dispatch `~/ai/workflows/audit.md`, consume an audit bundle, import review findings, or switch modes based on stray fields.

Absent or `normal` mode rejects non-empty audit-only fields as `BLOCKED:entry-mode-input-conflict`. Audit-only fields include `audit_workflow_path`, `audit_target_type`, `audit_target_paths`, `audit_target_manifest`, `audit_target_ref`, `audit_report_bundle_path`, `existing_review_bundle_path`, `existing_review_bundle_schema`, `reviewed_target_paths`, `reviewed_target_ref`, `current_target_ref`, `review_staleness_policy`, `review_staleness_fallback`, and `proposer_fix_scope`. `audit_history_path` is not pollution because it is normal loop memory.

### `review_first`

`review_first` treats the audit bundle as evidence and not a substitute for implementation-pipeline research. It runs after Phase 0 bootstrap and before Phase 2.5 prompt composition. Phase 0 still initializes the ticket render, worktree, `${scratch_dir}`, `${planning_dir}`, and core conventions first. The orchestrator then dispatches `~/ai/workflows/audit.md` against the declared target identity and writes prompts/logs under `${scratch_dir}/audit/${audit_slug}/` and the durable bundle under `${planning_dir}/audit/${audit_slug}/`.

The durable bundle must contain `dispatch-manifest.md`, `aggregate-audit.md`, `findings.json`, `findings.md`, and every per-auditor report required by the manifest. Phase 2.5 consumes that bundle as evidence and not a substitute for its own required artifacts. Phase 2.5 still produces all seven artifacts: problem-map, coverage, lifecycle, entrypoints, duplicates, cross-language, and risk-profile.

Immediately after the audit fanout returns and before Phase 2.5 or Phase 3 consumes the aggregate, the orchestrator dispatches `process-tree-auditor` on the audit fanout. The later Phase 4 process-tree audit still runs and its expected process includes the entry-mode audit subtree when the proposal depended on audit evidence.

If the current aggregate LOW covers every current ticket acceptance/scope item and leaves no remaining non-audit implementation or verification ask, the orchestrator records a value-zero decision and halts before proposal work; otherwise the pipeline continues through Phase 2.5, and the resulting Phase 2.5 plus audit evidence seeds Phase 3. `NEEDS_INPUT` and `BLOCKED` audit outcomes halt before proposal work.

### `plug_existing_review`

`plug_existing_review` imports one existing audit bundle instead of running a fresh pre-Phase-2.5 audit. The only structured import schema is `nes-design-audit-v1`; unknown `pipeline_entry_mode` values are rejected as `BLOCKED:unknown-pipeline-entry-mode`.

Before Phase 3 prompt composition, the orchestrator validates `existing_review_bundle_path`, `existing_review_bundle_schema`, required files, target identity, currentness, and staleness policy. Required bundle files are `dispatch-manifest.md`, `aggregate-audit.md`, `findings.json`, `findings.md`, and per-auditor reports required by the manifest. A missing required bundle file is rejected before Phase 3 consumes any finding.

Staleness follows the audit workflow currentness predicates, not mtime cleanup heuristics. `review_staleness_policy=exact-match` requires the imported target identity and current target identity to match. `required` reruns audit before proposal work and treats the prior bundle as context. `allow-with-drift-report` requires a drift report mapping changed files or sections; stale non-LOW findings may seed still-existing target items, but stale LOW/no-drift reports are context only for changed targets and require current re-audit before closure.

Imported finding IDs preserve the original `source_id` and `origin_bundle_path`, assign WU-local seed IDs as `SEED-FNN`, and defer canonical `R<N>-F<NN>` mapping to `decision-encoder` or the caller once a revise/review loop begins.

### Shared Entry-Mode Inputs

The orchestrator owns the full input table. Shared entry-mode inputs include `pipeline_entry_mode`, `audit_workflow_path`, `audit_target_type`, `audit_target_paths`, `audit_target_manifest`, `audit_target_ref`, `design_patterns_ref`, `operator_format_ref`, `audit_slug`, `audit_report_bundle_path`, `existing_review_bundle_path`, `existing_review_bundle_schema`, `reviewed_target_paths`, `reviewed_target_ref`, `current_target_ref`, `review_staleness_policy`, `review_staleness_fallback`, `proposer_fix_scope`, and runtime evidence fields required by `audit.md`.

### Entry-Mode Audit History And Re-Audit

Initial `review_first` and imported findings are seed critic evidence, not a completed revise/review loop by themselves. Record bundle references in `${planning_dir}/audit-history.md` when a second round begins or when `decision-encoder` records finding closure or regression. The record includes bundle path, target identity, aggregate verdict, source IDs, WU-local IDs, canonical IDs when assigned, and a currentness flag.

A substantive revision is any change to audited target paths or target-manifest items; commit/head/ref, PR base/head/file list, runtime invocation UUID, runtime artifact bundle, or non-git content hash; proposal closure strategy; workflow/operator/runtime behavior contract; or corpus/reference path used to justify closure. Formatting-only or typo-only edits outside audited sections may be recorded as non-substantive with a reason. Uncertainty is substantive.

Before findings close after a substantive revision, the orchestrator requires rerunning `audit.md` against the current affected targets, process-tree-auditing that fanout before consumption, and updating the audit bundle reference. A stale LOW/no-drift report is context only for changed targets and cannot close them without current re-audit before closure.

### Entry-Mode Proposer Research Handoff

Phase 3 prompt composition includes the audit bundle as evidence. If the proposer cannot close audit findings from existing evidence, it emits `DESIGN_RESEARCH_REQUIRED` with source finding IDs, the missing pattern knowledge, a focused research question, and an output slug. The orchestrator then dispatches `~/ai/workflows/research.md` and writes design-fix research artifacts under `${planning_dir}/research/design-fixes/`, then re-dispatches Phase 3 with those artifacts.

## Where artifacts live

Phase artifacts (`research/NN-*`, `proposals/NN-*`, `risk/NN-*`, contracts, audit history, scratch logs) are **planning** content. They live under the project's **planning directory**, not inside the working repository or its worktrees.

- For projects on `~/ai/conventions/project-layout.md`'s umbrella layout, the planning directory is `~/projects/<name>/planning/<branch>/`.
- For legacy single-repo projects that have not migrated, planning may transitionally live under `${repo_root}/tmp/scratch/<wu>/` or similar — but the migration goal is to lift it out so the worktree only carries product code + tests.
- Tests authored in **Phase 6b** and product code authored in **Phase 6c** **are** committed in the working repository and therefore land in the worktree. The test/code boundary is the planning-vs-product boundary.

The `implementation-pipeline-orchestrator` exposes `planning_dir` as a required input. Path references like `research/NN-rca.md` below are relative to `${planning_dir}` unless the rule explicitly names the worktree.

## Phase 0 - RCA (bugs only)

- Use when the work starts from a defect, regression, or unexplained behavior.
- Artifacts: `research/NN-rca.md` and the reproduction tests it cites (one per named root cause).
- Role: investigate root cause, trace the failure path, capture evidence, **reproduce each hypothesized root cause with an automated test**, and **do not** propose fixes.
- Rule: RCA is investigative only. If the output starts designing solutions, re-run with a tighter brief.
- Rule: each named root cause must be reproduced **as a test**. The reproduction test lives in the project's test root, alongside coverage-expansion tests that come from non-RCA work — they are formally identical. It serves as the gap-closing coverage and the regression detector for this bug, both. Committed against pre-fix HEAD, it runs **red**. Record the red-run command and output in the `Reproduction` section of `research/NN-rca.md`. There is no separate "reproduction harness" abstraction.
- Rule: distinguish **behavior tests** from **structural shape-guards**. A behavior test exercises the affected code path with inputs and asserts outputs — it closes the coverage gap that allowed the bug. A structural shape-guard reads a config file (workflow YAML, schema, manifest) and asserts the file's shape — it catches deletion regressions but does not verify behavior; an attacker (or careless refactor) could write the YAML with the right shape and still break the runtime. Both are tests, but **shape-guards do not substitute for behavior tests** when behavior is the bug's domain. When the affected surface is a config file whose runtime semantics are not testable in the unit/component layer (e.g., GitHub workflow YAML asserting "step X exists between step Y and Z"), the closest available test may be a shape-guard. That is honest, not load-bearing — record the residual behavior-coverage gap in `risk/NN-test-residuals.md` with class `integration-hidden` so the gap is explicit rather than masked.
- Rule: when deterministic reproduction is not feasible (for example, races that need real infrastructure), produce a contract-level test that asserts the invariant the fix must establish (call ordering, post-condition check, blocking guard, etc.), and reproduce behaviorally on the appropriate runner when one is available. Document any unreproduced hypothesis as `Hypothesis (unreproduced)` with the specific evidence that would confirm or refute it; downstream phases must not assume an unreproduced hypothesis as cause.
- Rule: Phase 0 does not edit product source. Reproduction adds tests only.
- Gate: model. The orchestrator advances autonomously to Phase 2.5 once each named root cause is reproduced (or documented as `Hypothesis (unreproduced)` with the specific evidence that would confirm or refute it). Surface a NEEDS_INPUT new-value-question to the root only if the reproduced cause invalidates the framing of the original request.

## Phase 1 - Problem Research (optional; required when the problem is not pre-scoped)

- Use when the request is vague, symptoms are broad, or the actual problem is unclear.
- Artifact: `research/NN-*.md`
- Role: document the problem space with evidence, constraints, examples, and open questions. **Do not** design solutions.
- Rule: if a delegated agent returns `NEEDS_INPUT:<question_artifact>`, the orchestrator classifies it: procedural questions are answered by the orchestrator and the sub-agent is re-dispatched; only NEEDS_INPUT carrying a new-value question is surfaced to the root.
- Gate: model. The orchestrator advances autonomously to Phase 2 (or Phase 2.5 if Phase 2 is skipped) once the framing artifact is non-empty and free of unresolved new-value questions.

## Phase 2 - Synthesize User Needs (optional; usually paired with Phase 1)

- Use when research exists but still needs to be mapped onto the project's real context.
- Artifact: `research/NN-*-needs.md`
- Role: map research to project-specific constraints, priorities, and anti-goals, and call out unanswered questions that block proposal work.
- Rules: follow `~/ai/models/roles.md`. This phase is synthesis, not judgment, and still does not implement.
- Rule: if a delegated agent returns `NEEDS_INPUT:<question_artifact>`, the orchestrator classifies procedural vs new-value per the orchestrator's NEEDS_INPUT handling spec; only new-value questions reach the root.
- Gate: model. The orchestrator advances autonomously to Phase 2.5 once the synthesis artifact is non-empty and free of unresolved new-value questions.

## Phase 2.5 - Existing-State Risk Profile

- Run after scope is known and before proposal work starts.
- Artifacts (all required): `research/NN-problem-map.md`, `research/NN-coverage-inventory.md`, `research/NN-lifecycle-map.md`, `research/NN-entrypoints.md`, `research/NN-duplicates.md`, `research/NN-cross-language-trace.md`, `risk/NN-risk-profile.md`.
- Role: build the approved understanding of the touched surface as it exists today, **scored** for risk per `~/ai/conventions/risk-profile.md`. Inputs are the planned change surface: files, symbols, endpoints, commands, jobs, or workflows expected to change.

Phase 2.5 has six sub-steps. They run in dependency order; some can run in parallel after their preconditions are met. The risk profile in step 6 is computed from the outputs of 1–5.

### Step 2.5.1 - Coverage inventory (tests-first research)

Behavior is established by tests, not by code. Read tests before reading code.

- Artifact: `research/NN-coverage-inventory.md`
- Role: enumerate the tests that cover the touched surface today. For each named behavior the WU will change or depend on, identify the test that captures it.
- Rule: if a named behavior has no test, surface this in the artifact's "uncovered behaviors" section. Each uncovered behavior is a precondition for safe work.
- Rule: for each uncovered behavior on the touched surface, the orchestrator dispatches a `gpt-high` test-writer (via the test-coverage workflow) to produce **characterization tests** that capture the current behavior **before** Phase 3 designs any change. Characterization tests land on the WU branch (or a precursor branch). The behavior they capture becomes the contract Phase 3 works against.
- Rule: bugs found while writing characterization tests are filed as separate tracker tickets via the project's ticket operator (`jira-operator` or `linear-operator`) per `~/ai/conventions/risk-profile.md` § Discoveries during Phase 2.5. They `Blocks` (or, on Linear, parent-link) the current WU; the orchestrator halts and surfaces a `NEEDS_INPUT` for user disposition.
- Rule: ambiguities found are filed on the project's product-question board with a `Blocks` link. Same halt-and-surface rule.

### Step 2.5.2 - Lifecycle map

- Artifact: `research/NN-lifecycle-map.md`
- Role: name the full lifecycle of the process the touched surface participates in. Where does the process start? Where does it end? What state transitions does it go through? Where does each output go?
- Rule: the lifecycle map is bounded to the touched process plus immediately-adjacent producers and consumers. It is not a whole-system map.
- Rule: lifecycle visibility is one axis of the risk profile (`~/ai/conventions/risk-profile.md`). A lifecycle that cannot be drawn from the code alone is HIGH on that axis.

### Step 2.5.3 - Entrypoint enumeration

- Artifact: `research/NN-entrypoints.md`
- Role: enumerate every way a caller can enter the touched surface. CLI invocations, API endpoints, CI workflow triggers, queue messages, file-watch handlers, scheduled jobs, public functions, etc.
- Rule: every entrypoint has a contract — name the contract (parameters, expected output, side effects). Missing contracts are MEDIUM on `behavioral-ambiguity`.
- Rule: an entrypoint that is reachable but undocumented is HIGH on `blast-radius`.

### Step 2.5.4 - Duplicate-systems inventory

- Artifact: `research/NN-duplicates.md`
- Role: identify other code paths that do the same thing as the touched surface. They may be in different languages. They may be older or newer. They may have diverged.
- Rule: the inventory names each duplicate, its language, its current state (live, deprecated, dead), and how it differs from the touched surface (if at all). Diverged duplicates are HIGH on `duplicate-system-count`.
- Rule: when duplicates exist, Phase 3 must explicitly address whether the WU cascades the change to all duplicates, consolidates them, or accepts the divergence. "We'll deal with them later" is not addressed.
- Rule: this step uses the `code-tracer` operator (`~/ai/agents/code-tracer.md`) when the touched surface spans languages or when the duplicate inventory cannot be derived by simple grep.

### Step 2.5.5 - Cross-language trace

- Artifact: `research/NN-cross-language-trace.md`
- Role: trace the touched surface across language boundaries. Python → JSON → TypeScript. Shell env-var → PowerShell parser. File-write → file-read consumers in any language. API boundary → frontend consumer. Workflow YAML → script invocations.
- Rule: dispatch the `code-tracer` operator (`~/ai/agents/code-tracer.md`) when the surface crosses any language boundary. The operator produces a graph of readers/callers/contracts.
- Rule: implicit contracts across language boundaries are HIGH on `language-fragmentation`. Make them explicit, or score them HIGH and let Phase 3 narrow them.

### Step 2.5.6 - Risk profile (scored)

- Artifact: `risk/NN-risk-profile.md`
- Role: score each touched surface on the axes named in `~/ai/conventions/risk-profile.md` (coverage gap, behavioral ambiguity, blast radius, language fragmentation, duplicate-system count, brittleness markers, change-path entropy, lifecycle visibility). Compute a per-surface verdict (LOW / MEDIUM / HIGH) and the rolled-up WU-level verdict.
- Rule: every non-LOW score names evidence. A score without a path, symbol, or query a reader can verify is rejected.
- Rule: the WU-level verdict drives **pipeline mode** for downstream phases. HIGH → exhaustive mode. LOW → lean mode. MEDIUM → lean mode with the MEDIUM axes called out in Phase 3's proposal.
- Rule: per-surface mode lets one WU run lean for one surface and exhaustive for another in the same ticket. Phase 3 onward read the per-surface mode, not just the rolled-up verdict.
- Rule: the WU's risk profile is also aggregated into the project-level risk profile (`<project>/planning/risk-profile.md`) per the convention. This aggregation is what `~/ai/workflows/risk-reduction.md` consumes between tickets.

### Existing problem-map content

- Artifact: `research/NN-problem-map.md`
- Role: same as before — capture what exists now, what is already risky or brittle, which adjacent surfaces sit inside the blast radius, and which supported or user-reachable paths exercise this surface today.
- Rule: if research already produced a draft `problem map`, use Phase 2.5 to validate and narrow that draft against the exact planned change surface. Do not keep a competing second map.
- Rule: if research already produced a draft assumption register for the touched surface, carry it into Phase 3 for validation and narrowing into the approved assumption register in `proposals/NN-*.md`. Do not keep a competing second register.
- Rule: keep the map bounded to the touched surface plus adjacent supported paths. Do not expand into a whole-system inventory.
- Rule: if the current supported path is unclear, return to research. Resume by updating the `problem map`, then re-enter Phase 2.5 before proposal work starts.

### Phase 2.5 mode and gating

- Rule: if a delegated agent returns `NEEDS_INPUT:<question_artifact>`, the orchestrator classifies procedural vs new-value; only new-value questions reach the root.
- Rule: bugs / ambiguities / drift / test-gap discoveries are handled per `~/ai/conventions/risk-profile.md` § Discoveries during Phase 2.5. New tracker tickets (JIRA or Linear, per project) that block the current WU halt the orchestrator until user disposition is given.
- Rule: Phase 2.5 cannot run in lean mode itself — it is the input to mode selection for downstream phases. The artifacts must all be produced. The size of the artifact for a particular sub-step may be small (e.g. coverage inventory for a one-file change is short), but the artifact is required.
- Gate: human. **This remains the first of the two surviving human gates.** The user confirms (a) the problem map names the right terrain, (b) the risk profile's per-surface verdicts are accepted, (c) any blocking-ticket disposition is settled, and (d) the WU is workable in the implementation pipeline at all (vs. needs deferral to a prototype) before proposal work begins.

### Defer to prototype

Sometimes Phase 2.5 surfaces evidence that the WU is not workable in the implementation pipeline yet. Signals:

- The risk profile rolls up HIGH on **most** surfaces (not one or two — most). Exhaustive mode would expand the WU into multiple WUs.
- The duplicates inventory (sub-step 2.5.4) finds a sprawling parallel-systems landscape that the WU cannot navigate without architectural decisions outside the WU's scope.
- The lifecycle map (sub-step 2.5.2) cannot be drawn — too much of the touched process is operational knowledge the codebase doesn't capture.
- The coverage inventory (sub-step 2.5.1) finds the touched surface so under-specified that characterization tests would themselves be a multi-WU effort before the actual change can be designed.
- The cross-language trace (sub-step 2.5.5) reveals the surface crosses boundaries with implicit contracts in so many places that the change-path entropy alone scores HIGH.

When two or more of these fire, the Phase 2.5 human gate surfaces options: `proceed in exhaustive mode (the WU is just big)`, `defer to prototype (framing is too unclear; build a prototype to clarify, then re-ticket from its dossier)`, `terminate WU (the work is wrong-shaped; abandon)`. Choosing **defer to prototype** dispatches `~/ai/agents/prototype-orchestrator.md` per `~/ai/workflows/build-prototype.md` with the WU's question as the prototype's question and the WU's `${ticket_id}` (`jira_issue_key` or `linear_issue_key`, per project) as `defer_source`. The implementation orchestrator halts the deferred WU; the prototype's dossier later spawns new tickets that re-enter the implementation pipeline with clearer scope.

Deferring to prototype is not failure. It is the recognition that the implementation pipeline's gates exist to enforce known structure on a clear plan, and the work currently has neither.

## Phase 3 - Proposal

- Artifact: `proposals/NN-*.md`
- Inputs: approved `problem map`, coverage inventory, lifecycle map, entrypoints, duplicates, cross-language trace, and **risk profile** from Phase 2.5; any research from Phases 1-2.
- Role: propose design, scope, architecture, tradeoffs, anti-scope, a test-intent track, and the specific current-state risk the change reduces. State what will not be changed. **Do not** implement.
- Rules: the proposal must be reviewable on its own terms. "We will figure it out during implementation" is not sufficient design. The proposer does not write its own risk reports.
- Rule: **mode is per-surface, not per-ticket.** Read `risk/NN-risk-profile.md` and produce a per-surface mode list at the top of the proposal: which surfaces are HIGH (exhaustive content required), which are MEDIUM (lean with explicit MEDIUM-axis callouts), which are LOW (lean). Apply the artifact requirements named in `~/ai/conventions/risk-profile.md` § Pipeline mode.
- Rule: when the risk profile names duplicate systems on the touched surface, the proposal must explicitly address whether the WU cascades the change to all duplicates, consolidates them, or accepts the divergence. "Cascade later" is not addressed.
- Rules: include a supported-surface track covering deployment mode, customer cohort, adjacent public or user-reachable paths, blast-radius notes for unchanged adjacent paths, migration path, rollback path, and observability.
- Rules: include a qualitative net-value statement. State whether the proposal clearly reduces a concrete current-state risk on the current supported surface and whether that reduction clearly outweighs the added blast radius plus the migration and rollback burden.
- Rules: name those inputs from the artifact fields. Existing-state risk comes from `known risky or brittle behavior already present` plus `current supported and user-reachable paths through the surface`; change blast radius comes from `adjacent surfaces within the blast radius` plus `adjacent public or user-reachable paths`; migration cost comes from `migration path` plus `rollback path`.
- Rules: include a short assumption register. Each assumption must name the evidence it relies on and what source or observation would invalidate it. If research already drafted a register for this touched surface, Phase 3 validates and narrows it into the approved assumption register in `proposals/NN-*.md`. Do not keep a competing second register.
- Rules: include a test-intent track. For each expected test or test group, name the change risk or verification risk, intended behavior or acceptance condition, selected level (`unit`, `component`, `particular-integration`, or `end-to-end`), fixture source or fixture application point, assumption-register link if the behavior depends on an assumption, expected observable signal, and any residual risk the test will not verify.
- Gate: no default human approval step. The proposal advances only by passing Phase 4.

## Phase 4 - Risk Gates (required; parallel)

Run the risk gate on the proposal artifact, the `problem map`, the supported-surface track, and the Phase 2.5 risk profile, not on hand-waved intent.
The exact model assignments for these roles live in `~/ai/models/roles.md`.

- Artifacts: `risk/NN-audit.md`, `risk/NN-scope.md`, `risk/NN-shortcut.md`, `risk/NN-supported-surface.md`
- `audit risk`: presence, contracts, migrations, test-intent track, fixture source, residual-risk artifact, and other checklist obligations
- `scope risk`: does the proposal stay within the stated scope
- `shortcut risk`: do proposed shortcuts defeat the underlying purpose
- `supported-surface risk`: does the proposal reduce risk on the current supported surface it claims to target, using the approved `problem map`, supported-surface track, net-value statement, assumption register, and **risk profile**, including adjacent public or user-reachable paths, deployment mode, migration, rollback, and observability
- Rule: all four reports must return `LOW` on the LOW/MEDIUM/HIGH verdict dimension.
- Rule: in **lean mode** (per `~/ai/conventions/risk-profile.md` § Pipeline mode) the supported-surface gate may pass at LOW with a single-paragraph supported-surface track and the audit gate may pass at LOW without per-AC residual entries. In **exhaustive mode** the gates require full evidence per the rules below.
- Rule: supported-surface termination is an orthogonal dimension from the LOW/MEDIUM/HIGH verdict. Evaluate it first and in this order: invalidated assumption that breaks the current problem framing -> return to research and resume at Phase 2.5; otherwise non-positive value on the current supported surface -> terminate the work. A `LOW` supported-surface verdict with a non-positive value signal still terminates. Only when no termination signal fires does the LOW/MEDIUM/HIGH verdict control the next step.
- Rule: when no termination signal fires, any `MEDIUM` or `HIGH` report means revise the proposal and re-run all four.
- Rule: do not keep old `LOW` reports after a substantive proposal revision.
- Rule: if proposal revision and risk review enter a second round, create or update audit history under `~/ai/conventions/audit-history.md`. Track prior-finding closure/regression, new findings, oscillation classification, decompose-trigger status, watch signals, and the current `continue` / `apply` / `decompose` determination.
- Rule: if hard revise/review triggers do not decide `continue`, `apply`, or `decompose`, use the decision-agent dispatch pattern in `~/ai/conventions/audit-history.md` before the orchestrator calls the loop.
- Rule: if a proposer claims it "re-ran the risks itself," ignore that claim and re-dispatch the actual risk agents.
- Rule: Process-tree review: after the Phase 4 risk fanout joins, run `process-tree-auditor` on the root-delegated risk-gate subtree before Phase 5 consumes the reports. The expected process includes the four risk reports, their required model/role assignments, their logs, and their verdict artifacts. A blocking process violation prevents Phase 5.
- Gate: model. The risk gate is the proposal review.

## Phase 4.5 - Alignment (optional; governance layer only)

- Use only when the project explicitly has a governance or philosophy layer that needs a directional check.
- Artifact: `alignment/NN-*.md`
- Role: check the proposal against governance, patterns, and philosophy and return `ALIGNED`, `MISALIGNED`, or `NEEDS_REVISION`.
- Rules: alignment is directional, not exhaustive. It does not replace the audit gate. If the proposal changes materially after alignment feedback, re-run Phase 4 as well.
- Gate: model. `ALIGNED` is required when this phase is enabled.

## Phase 5 - Hookpoint Research

- Run only after the proposal has cleared risk, and alignment if alignment applies.
- Artifact: `research/NN-hookpoints.md`
- Role: map the approved proposal onto the existing codebase and find reusable pieces, extension points, conflicting systems, and deletion candidates.
- Rule: identify anything parallel that should be merged into or removed instead of re-created. The Phase 2.5 duplicates inventory (`research/NN-duplicates.md`) is the input — Phase 5 confirms whether the planned change cascades, consolidates, or diverges per the proposal's decision.
- Rule: in **exhaustive mode** for any surface scored HIGH on language-fragmentation or change-path-entropy, dispatch the `code-tracer` operator (`~/ai/agents/code-tracer.md`) to produce the cross-language readers/callers/contracts graph for that surface. Hookpoints derived from a single-language grep are insufficient when the surface crosses boundaries.
- Rule: in **lean mode**, the four required sections (reuse / extension / conflicting / deletion candidates) are required as headers; sections may be one line or "none observed" but must be present.
- Rule: if multiple implementation agents will work later, follow `~/ai/conventions/worktree-isolation.md`.
- Rule: if hookpoint research shows the approved `problem map` or assumption register is wrong, stop and return to research; resume at Phase 2.5 with an updated `problem map` before implementation continues. Returning to Phase 2.5 re-engages the problem-map human gate.
- Rule: if a delegated agent returns `NEEDS_INPUT:<question_artifact>`, the orchestrator classifies procedural vs new-value; only new-value questions reach the root.
- Gate: model. The orchestrator advances autonomously to Phase 6 once the hookpoints artifact is non-empty, contains the four required sections (reuse points / extension points / conflicting systems / deletion candidates), and does not invalidate the approved problem map or assumption register.

## Phase 6 - Implementation (required; test/code separation)

Implementation has three sub-steps.
The test writer and the code writer must be different agent invocations.
That rule is load-bearing: if the same agent writes both, the tests mirror the implementation instead of validating the contract.

- Rule: Phase 6 firstness evidence is the Phase 6 process-tree review plus companion artifacts. The companion artifacts are the expected-process manifest, Step 6b prompt/log, Step 6c prompt/log, Step 6b output index, Step 6b output paths, and evidence that Step 6c consumed those outputs. A commit marker is optional supporting evidence only. A PR-diff test file is not required firstness evidence.
- Convention: `${scratch_dir}/phase6/` resolves under the same per-run scratch directory supplied by the invoking workflow, matching the `scratch_dir` input pattern used by `agents/test-audit-gate.md` and `agents/red-phase-gate.md`.
- Rule: Phase 6 consumes the approved `research/NN-problem-map.md`, approved `proposals/NN-*.md` including its test-intent track and assumption register, `risk/NN-supported-surface.md`, and `research/NN-hookpoints.md`.
- Rule: RCA-track. The reproduction tests produced in Phase 0 are inputs to the Phase 3 test-intent track and to Phase 6b. Step 6b carries them forward (existing tests satisfy firstness when the Step 6b output index maps them to the named risk and source). Step 6c is not complete until each pre-fix red test from Phase 0 runs green against post-fix HEAD.
- Rule: RCA-track evidence is **verbatim output, not summary**. The red run is captured by reverting the planned-change product file(s) to the branch's base (`origin/main` or the stacked parent), running each reproduction test, and pasting the failure block into the Phase 9 evidence artifact. The green run is captured by restoring the fix and re-running the same test, pasting the pass block. "Tests passed" is not evidence; the actual `pytest` / Playwright / runner command output is.
- Rule: if Step 6a, 6b, or 6c uncovers evidence that invalidates an approved assumption or shows the touched surface differs materially from the approved `problem map`, stop implementation and return to research; resume at Phase 2.5 before more code or tests are written.
- Rule: if a delegated agent returns `NEEDS_INPUT:<question_artifact>`, the root handles it through `~/ai/conventions/agent-questions-and-session-graph.md`. Do not advance this phase, write code, post review output, or open a PR from work that depends on the unanswered question.

### Step 6a - Define contract

- Owner: orchestrator
- Produces: schemas, signatures, commands, interface boundaries, explicit behavioral assumptions, fixture application points, and test-intent handoff
- Rule: the contract must be clear enough that another agent can write tests from it without seeing implementation code.
- Rule: the contract must preserve every change risk or verification risk, selected test level, fixture source, assumption-register link, and expected observable signal from the approved proposal test-intent track.

### Step 6b - Encode tests first

- Inputs: contract, approved proposal test-intent track, approved `problem map`, **approved `risk/NN-risk-profile.md`**, characterization tests already produced in Phase 2.5 step 2.5.1 for any uncovered behaviors on the touched surface, `risk/NN-supported-surface.md`, and hookpoint research.
- Rule: the test writer is a separate agent invocation from Step 6c.
- Rule: the test writer does **not** see the implementation.
- Rule: in **lean mode**, smoke + AC coverage is sufficient; residuals are named but not blocking. In **exhaustive mode**, per-named-risk + per-AC + property-based / mutation / fuzz coverage is required for surfaces scored HIGH on `coverage-gap` or `behavioral-ambiguity`; residual tests are blocking unless explicitly accepted in `risk/NN-test-residuals.md`. Per-surface mode applies independently.
- Rule: characterization tests produced in Phase 2.5 step 2.5.1 are inputs, not duplicates. Step 6b adds tests for the **new** behavior the WU introduces; characterization tests stay in place to guard against regression of the existing behavior.
- Rule: tests encode intended behavior from the contract and proposal test-intent track before Step 6c writes product code.
- Rule: fixtures are applied from outside the test body. Durable or shared fixture state belongs in dedicated fixture modules, dedicated fixture files, factories, builders, test inputs or test data files, or runner configuration; the test body keeps only behavior-specific arrange/act/assert. Same-file fixture declarations, including `@pytest.fixture` declarations in the same file or class as the test, violate this rule unless the project's convention names that file pattern as the dedicated fixture file pattern.
- Rule: every test or test group carries a risk annotation naming the risk it reduces, the selected level, and the proposal or assumption-register source. If a test verifies an assumption, the annotation says so.
- Rule: firstness applies per named risk, selected level, and test group from the approved test-intent track. Existing tests satisfy this rule only when the Step 6b output index maps them to the named risk, selected level, and proposal or assumption-register source.
- Rule: pre-existing code without prior tests is not required to prove retroactive firstness. Current-work behavior changes and current-work risk reduction are not grandfathered.
- Rule: when a named risk cannot be verified by the test set, produce `risk/NN-test-residuals.md` with the residual class (`combinatorial/path-state`, `bounded-model`, `integration-hidden`, `emergent-interaction`, `temporal/concurrency`, or `generator/search-budget`), technique attempted or considered (`property-based`, `fuzzing`, `mutation`, `symbolic`, `model-checking`, `chaos`, or `graph`), scope, budget or bound, result, remaining residual, invalidating inputs, and whether the residual changes the net-value case.
- Output: test files in the project test roots, with risk annotations on every test or test group.
- Output: `${scratch_dir}/phase6/step6b-output-index.md`, listing every proposal test-intent item, named risk, selected level, source, emitted test file or test group, residual entry, or documented non-applicability reason.
- Output-index fields: approved proposal path, contract path, approved `problem map` path, `risk/NN-supported-surface.md` path, hookpoint research path, Step 6b prompt path, Step 6b log path, each test-intent item, named risk, selected level, proposal or assumption-register source, emitted test file path and test or test-group identifier, residual entry path when the item maps to `risk/NN-test-residuals.md`, documented non-applicability reason when no test is emitted, and declared fixture source or fixture application point.
- Output: `risk/NN-test-residuals.md` when any named risk remains unverified.

### Step 6c - Write code

- Inputs: contracts, `${scratch_dir}/phase6/step6b-output-index.md`, and the tests from Step 6b.
- Rule: the code writer is a separate agent invocation from Step 6b.
- Rule: the job is to make the tests pass while respecting the approved design and architecture.
- Rule: if tests fail after Step 6c, re-invoke the code agent with the test output.
- Rule: do **not** re-invoke the test agent because the implementation failed.
- Rule: if a test is wrong, that is the contract's fault, not the test's.
- Rule: if contract intent truly changed, revise the contract explicitly and regenerate the affected tests from that revised contract.
- Operational note: parallel implementation is allowed only under `~/ai/conventions/worktree-isolation.md`.
- Rule: Step 6c log output must echo which Step 6b test output paths and Step 6b output index paths it read before product-code changes.
- Rule: Process-tree review: after Step 6c completes and before Phase 7, run `process-tree-auditor` on the Phase 6 subtree. The expected process must prove separate Step 6b and Step 6c invocations, timing order, Step 6b output index presence, Step 6b output paths, and Step 6c consumption of those outputs. A `blocking` independence, output/artifact, or silent-success violation prevents CodeRabbit. Missing required evidence is `NEEDS_INPUT:<question_artifact>` when it can still be supplied, otherwise `blocking`; the affected subtree is `rerun or repaired` before downstream consumption.

## Phase 7 - CodeRabbit Loop

- Run CodeRabbit only after implementation is functionally complete enough for review.
- Policy: follow `~/ai/workflows/coderabbit-loop.md`.
- Rules: do not duplicate the CodeRabbit procedure here. This phase reviews the actual diff, not the proposal.
- Rule: if CodeRabbit or the fix pass surfaces evidence that invalidates an approved assumption or collapses the approved net-value case, return to research and resume at Phase 2.5 instead of treating it as an ordinary review fix.
- Rule: if a delegated agent returns `NEEDS_INPUT:<question_artifact>`, the root handles it through `~/ai/conventions/agent-questions-and-session-graph.md`. Do not advance this phase, write code, post review output, or open a PR from work that depends on the unanswered question.

## Phase 8 - Post-CodeRabbit Review Gates

- These are the PR-opening gates on the actual diff.
- Policy: follow `~/ai/workflows/pr-review.md`.
- That workflow covers test-audit review, multi-concern PR review, justification PR review, and commit hygiene.
- Rule: do not duplicate the full procedure here.
- Rule: if those gates say the diff should be split, split it before opening PRs.
- Rule: Process-tree review: after Phase 8 gates pass and before Phase 9, run `process-tree-auditor` on the delegated CodeRabbit and PR-review subtrees. A blocking process violation prevents draft PR creation until the affected subtree is rerun or repaired.
- Rule: if a delegated agent returns `NEEDS_INPUT:<question_artifact>`, the root handles it through `~/ai/conventions/agent-questions-and-session-graph.md`. Do not advance this phase, write code, post review output, or open a PR from work that depends on the unanswered question.

## Phase 8.5 - Human Local Review Gate (tickets-first variant only)

- Use when the project has opted into `~/ai/workflows/tickets-first-review.md`. Default-variant projects skip this phase and proceed straight to Phase 9.
- Role: a human reviewer pulls the branch and reviews it locally. The orchestrator's automated gates (Phase 7 CodeRabbit, Phase 8 review-gates, the three process-tree audits) do **not** count as the local review for this variant. Treating them as a substitute is a workflow violation.
- Procedure: push the branch to origin if not already pushed; comment on the tracker ticket citing the branch name + head SHA (not a PR URL — there is no PR yet); emit a NEEDS_INPUT to the root with options `approve` / `revisions` / `reject`; block until answered.
- Rule: while this gate is pending, the project's ticket (JIRA or Linear) is the unit of review and the **branch** is the artifact under review. No draft PR exists yet; the Phase 9 step that creates it does not run until this gate clears with `approve`.
- Rule: revisions requested at this gate are **post-Phase-8** revisions: re-enter from the appropriate phase (typically Phase 7 if review-comment-shaped, Phase 6 if it requires test/code changes), re-run Phase 8 audits, and re-enter this gate.
- Rule: rejection at this gate terminates the WU. Record in `DECISIONS.md`, comment closure on the ticket via the project's ticket operator, halt — do not open a PR.
- Gate: human. **This is the second of the two human gates** in the tickets-first variant of the orchestrator's flow (the first being Phase 2.5 problem-map review).

## Phase 9 - Draft PR

- Routine automation step after all prior gates pass.
- Rule: open one draft PR per concern identified by multi-concern review.
- Rule: respect dependency order for stacked work.
- Rule: follow `~/ai/conventions/git.md`.
- Rule: opening a **draft** PR is not Tier-3 by default.
- Rule: **the title and body MUST be authored by `~/ai/agents/pr-writer.md`** — never hand-written by the orchestrator and never inlined into the `gh pr create` invocation. The writer enforces audience-and-content rules (no internal jargon, no commit-history sections, no closed-PR or local-planning-artifact references) that hand-written or templated bodies routinely violate. Pass the relevant phase artifacts (`problem-map.md`, `proposal.md`, `contract.md`, RCA evidence) as `context_files` so the writer has intent grounding without citing them in the body. For stacked PRs, supply `stack_parent_pr=<num>`; for any reference to merged work, supply `merged_refs=<list>`; when the selected ticket backend is Linear and the Linear key is known, supply `linear_issue_keys=<KEY>` so `pr-writer` emits the close-keyword footer itself.
- Rule: RCA-track. The draft PR description includes before/after reproduction evidence: the Phase 0 red-run command and output for every reproduction test, paired with the matching post-fix green-run command and output recorded in Step 6c. Pass the evidence path(s) to `pr-writer` via `context_files` so they're folded into the body in audience-safe form.

## Phase 10 - Promote To Ready-For-Review

- Automated by the orchestrator once Phase 9 succeeds and the Phase 8 process-tree audit has cleared.
- Rule: the orchestrator runs `gh pr ready <pr_number>` and records the promotion in `${scratch_dir}/pr-promoted.txt`. No human gate.

## Gate Ownership

See `~/ai/conventions/gate-ownership.md` for the phase-by-phase table.

Rule of thumb:
- the default pipeline human gates are (1) the Phase 2.5 problem-map review and (2) NEEDS_INPUT new-value-question surfacing per `~/ai/agents/implementation-pipeline-orchestrator.md`; `tickets_first_variant=true` adds the Phase 8.5 human local-review gate before Phase 9
- every other phase belongs to a model gate or to automation
- the proposal is reviewed by the risk gate, not by an extra human approval pass
- Phase 9 (draft PR) and Phase 10 (promotion) are both automated by the orchestrator

## Tiered Approval

Anything with user-visible side effects follows `~/ai/workflows/tiered-approval.md`.

Practical default:
- drafting code is not Tier-3
- editing files is not Tier-3
- running tests is not Tier-3
- opening **draft** PRs is not Tier-3
- public promotion and other outward-facing actions follow the tiered-approval workflow

## Decision Recording

If a phase is skipped, narrowed, deferred, terminated for non-positive value, sent back to research on invalidated assumptions, or accepted with a named unverifiable residual risk that does not collapse the approved net-value case under the supported-surface termination rule:
- record it in `DECISIONS.md` or the project equivalent
- record who made the decision
- record why the change was accepted
- record what risk is being accepted
- record what evidence caused the termination or research re-entry

For Phase 6 firstness, do not create a new residual class. If a named test-verification risk remains unverified, record it in `risk/NN-test-residuals.md`. If only historical or process-provenance evidence is unverifiable and the approved net-value case still holds, record the decision only as `accepted with a named unverifiable residual risk` in `DECISIONS.md` or the project equivalent.

Without that record, the phase was not skipped correctly.

## Orchestrator

This pipeline is dispatched by the `implementation-pipeline-orchestrator` (`claude-opus`) operator at `~/ai/agents/implementation-pipeline-orchestrator.md`. The orchestrator is the only delegated actor that walks a Work Unit through every phase, dispatches each leaf operator via the `agents` CLI, runs the three required process-tree audits, and enforces the violation-escalation policy autonomously (including Tier-1 main-branch rewinds when a violation is detected). Inlining the orchestrator role into the root conversation is itself a workflow violation because it removes the orchestration decisions from `agents trace --json` and prevents process-tree-auditor from auditing the workflow as a whole.

## Adjacent References

- `~/ai/agents/implementation-pipeline-orchestrator.md`
- `~/ai/models/roles.md`
- `~/ai/workflows/agents-cli.md`
- `~/ai/conventions/worktree-isolation.md`
- `~/ai/conventions/git.md`
- `~/ai/workflows/coderabbit-loop.md`
- `~/ai/workflows/pr-review.md`
- `~/ai/workflows/tiered-approval.md`
- `~/ai/conventions/no-backwards-compatibility.md`
- `~/ai/conventions/no-deferred-stubs.md`
- `~/ai/conventions/gate-ownership.md`
- `~/ai/conventions/audit-history.md`
