# Implementation Pipeline

End-to-end pipeline from triggering event to merged PR.
Bugs start with RCA. Features, refactors, and other planned work skip RCA.

Model assignments are authoritative in `~/ai/models/roles.md`.
Do not restate or override that matrix in project docs.
Use it exactly, including the synthesis/audit-vs-judgment split and the rule that `gpt-xhigh` is not the default coordinator.

Agent invocation: `~/ai/workflows/agents-cli.md`
Parallel-agent isolation: `~/ai/conventions/worktree-isolation.md`
Git and PR conventions: `~/ai/conventions/git.md`
Audit-history convention for revise/review loops: `~/ai/conventions/audit-history.md`
Process-tree review operator: `~/ai/agents/process-tree-auditor.md`
Workflow-execution violation taxonomy: `~/ai/conventions/workflow-execution-violations.md`

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
- **Draft PRs are routine; promotion is not.** Opening draft PRs is automated. Promotion to ready-for-review is human-owned.

## Phase Map

Optional phases:
- `Phase 0` RCA for bugs only
- `Phase 1` problem research
- `Phase 2` synthesize user needs
- `Phase 4.5` alignment for governance-heavy projects

Core path:
- `Phase 2.5 -> Phase 3 -> Phase 4 -> Phase 5 -> Phase 6 -> Phase 7 -> Phase 8 -> Phase 9 -> Phase 10`

## Phase 0 - RCA (bugs only)

- Use when the work starts from a defect, regression, or unexplained behavior.
- Artifact: `research/NN-rca.md`
- Role: investigate root cause, trace the failure path, capture evidence, and **do not** propose fixes.
- Rules: RCA is investigative only. If the output starts designing solutions, re-run with a tighter brief.
- Gate: human. The user decides whether the bug is worth fixing at all.

## Phase 1 - Problem Research (optional; required when the problem is not pre-scoped)

- Use when the request is vague, symptoms are broad, or the actual problem is unclear.
- Artifact: `research/NN-*.md`
- Role: document the problem space with evidence, constraints, examples, and open questions. **Do not** design solutions.
- Gate: human. The user confirms that the framing is correct enough to continue.

## Phase 2 - Synthesize User Needs (optional; usually paired with Phase 1)

- Use when research exists but still needs to be mapped onto the project's real context.
- Artifact: `research/NN-*-needs.md`
- Role: map research to project-specific constraints, priorities, and anti-goals, and call out unanswered questions that block proposal work.
- Rules: follow `~/ai/models/roles.md`. This phase is synthesis, not judgment, and still does not implement.
- Gate: human. The user confirms the mapping and answers open questions.

## Phase 2.5 - Existing-State Risk Profile

- Run after scope is known and before proposal work starts.
- Artifact: `research/NN-problem-map.md`
- Role: build the approved `problem map` of the touched surface as it exists today. Inputs are the planned change surface: files, symbols, endpoints, commands, jobs, or workflows expected to change.
- Rule: if research already produced a draft `problem map`, use Phase 2.5 to validate and narrow that draft against the exact planned change surface into `research/NN-problem-map.md`. Do not keep a competing second map.
- Rule: if research already produced a draft assumption register for the touched surface, carry it into Phase 3 for validation and narrowing into the approved assumption register in `proposals/NN-*.md`. Do not keep a competing second register.
- Rule: capture what exists now, what is already risky or brittle, which adjacent surfaces sit inside the blast radius, and which supported or user-reachable paths exercise this surface today.
- Rule: keep the map bounded to the touched surface plus adjacent supported paths. Do not expand into a whole-system inventory.
- Rule: if the current supported path is unclear, return to research. Resume by updating the `problem map`, then re-enter Phase 2.5 before proposal work starts.
- Gate: human. The user confirms that the map names the right terrain before proposal work begins.

## Phase 3 - Proposal

- Artifact: `proposals/NN-*.md`
- Inputs: approved `problem map` from Phase 2.5 and any research from Phases 1-2.
- Role: propose design, scope, architecture, tradeoffs, anti-scope, a test-intent track, and the specific current-state risk the change reduces. State what will not be changed. **Do not** implement.
- Rules: the proposal must be reviewable on its own terms. "We will figure it out during implementation" is not sufficient design. The proposer does not write its own risk reports.
- Rules: include a supported-surface track covering deployment mode, customer cohort, adjacent public or user-reachable paths, blast-radius notes for unchanged adjacent paths, migration path, rollback path, and observability.
- Rules: include a qualitative net-value statement. State whether the proposal clearly reduces a concrete current-state risk on the current supported surface and whether that reduction clearly outweighs the added blast radius plus the migration and rollback burden.
- Rules: name those inputs from the artifact fields. Existing-state risk comes from `known risky or brittle behavior already present` plus `current supported and user-reachable paths through the surface`; change blast radius comes from `adjacent surfaces within the blast radius` plus `adjacent public or user-reachable paths`; migration cost comes from `migration path` plus `rollback path`.
- Rules: include a short assumption register. Each assumption must name the evidence it relies on and what source or observation would invalidate it. If research already drafted a register for this touched surface, Phase 3 validates and narrows it into the approved assumption register in `proposals/NN-*.md`. Do not keep a competing second register.
- Rules: include a test-intent track. For each expected test or test group, name the change risk or verification risk, intended behavior or acceptance condition, selected level (`unit`, `component`, `particular-integration`, or `end-to-end`), fixture source or fixture application point, assumption-register link if the behavior depends on an assumption, expected observable signal, and any residual risk the test will not verify.
- Gate: no default human approval step. The proposal advances only by passing Phase 4.

## Phase 4 - Risk Gates (required; parallel)

Run the risk gate on the proposal artifact, the `problem map`, and the supported-surface track, not on hand-waved intent.
The exact model assignments for these roles live in `~/ai/models/roles.md`.

- Artifacts: `risk/NN-audit.md`, `risk/NN-scope.md`, `risk/NN-shortcut.md`, `risk/NN-supported-surface.md`
- `audit risk`: presence, contracts, migrations, test-intent track, fixture source, residual-risk artifact, and other checklist obligations
- `scope risk`: does the proposal stay within the stated scope
- `shortcut risk`: do proposed shortcuts defeat the underlying purpose
- `supported-surface risk`: does the proposal reduce risk on the current supported surface it claims to target, using the approved `problem map`, supported-surface track, net-value statement, and assumption register, including adjacent public or user-reachable paths, deployment mode, migration, rollback, and observability
- Rule: all four reports must return `LOW` on the LOW/MEDIUM/HIGH verdict dimension.
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
- Rule: identify anything parallel that should be merged into or removed instead of re-created.
- Rule: if multiple implementation agents will work later, follow `~/ai/conventions/worktree-isolation.md`.
- Rule: if hookpoint research shows the approved `problem map` or assumption register is wrong, stop and return to research; resume at Phase 2.5 with an updated `problem map` before implementation continues.
- Gate: human. The user confirms what survives, what is replaced, and what is deleted.

## Phase 6 - Implementation (required; test/code separation)

Implementation has three sub-steps.
The test writer and the code writer must be different agent invocations.
That rule is load-bearing: if the same agent writes both, the tests mirror the implementation instead of validating the contract.

- Rule: Phase 6 consumes the approved `research/NN-problem-map.md`, approved `proposals/NN-*.md` including its test-intent track and assumption register, `risk/NN-supported-surface.md`, and `research/NN-hookpoints.md`.
- Rule: if Step 6a, 6b, or 6c uncovers evidence that invalidates an approved assumption or shows the touched surface differs materially from the approved `problem map`, stop implementation and return to research; resume at Phase 2.5 before more code or tests are written.

### Step 6a - Define contract

- Owner: orchestrator
- Produces: schemas, signatures, commands, interface boundaries, explicit behavioral assumptions, fixture application points, and test-intent handoff
- Rule: the contract must be clear enough that another agent can write tests from it without seeing implementation code.
- Rule: the contract must preserve every change risk or verification risk, selected test level, fixture source, assumption-register link, and expected observable signal from the approved proposal test-intent track.

### Step 6b - Encode tests first

- Inputs: contract, approved proposal test-intent track, approved `problem map`, `risk/NN-supported-surface.md`, and hookpoint research.
- Rule: the test writer is a separate agent invocation from Step 6c.
- Rule: the test writer does **not** see the implementation.
- Rule: tests encode intended behavior from the contract and proposal test-intent track before Step 6c writes product code.
- Rule: fixtures are applied from outside the test body. Durable or shared fixture state belongs in dedicated fixture modules, dedicated fixture files, factories, builders, test inputs or test data files, or runner configuration; the test body keeps only behavior-specific arrange/act/assert. Same-file fixture declarations, including `@pytest.fixture` declarations in the same file or class as the test, violate this rule unless the project's convention names that file pattern as the dedicated fixture file pattern.
- Rule: every test or test group carries a risk annotation naming the risk it reduces, the selected level, and the proposal or assumption-register source. If a test verifies an assumption, the annotation says so.
- Rule: when a named risk cannot be verified by the test set, produce `risk/NN-test-residuals.md` with the residual class (`combinatorial/path-state`, `bounded-model`, `integration-hidden`, `emergent-interaction`, `temporal/concurrency`, or `generator/search-budget`), technique attempted or considered (`property-based`, `fuzzing`, `mutation`, `symbolic`, `model-checking`, `chaos`, or `graph`), scope, budget or bound, result, remaining residual, invalidating inputs, and whether the residual changes the net-value case.
- Output: `risk/NN-test-residuals.md` when any named risk remains unverified.

### Step 6c - Write code

- Inputs: contracts and the tests from Step 6b
- Rule: the code writer is a separate agent invocation from Step 6b.
- Rule: the job is to make the tests pass while respecting the approved design and architecture.
- Rule: if tests fail after Step 6c, re-invoke the code agent with the test output.
- Rule: do **not** re-invoke the test agent because the implementation failed.
- Rule: if a test is wrong, that is the contract's fault, not the test's.
- Rule: if contract intent truly changed, revise the contract explicitly and regenerate the affected tests from that revised contract.
- Operational note: parallel implementation is allowed only under `~/ai/conventions/worktree-isolation.md`.
- Rule: Process-tree review: after Step 6c completes and before Phase 7, run `process-tree-auditor` on the Phase 6 subtree. The expected process must prove separate Step 6b and Step 6c invocations and verify the Step 6b outputs that Step 6c consumed. A blocking independence or silent-success violation prevents CodeRabbit.

## Phase 7 - CodeRabbit Loop

- Run CodeRabbit only after implementation is functionally complete enough for review.
- Policy: follow `~/ai/workflows/coderabbit-loop.md`.
- Rules: do not duplicate the CodeRabbit procedure here. This phase reviews the actual diff, not the proposal.
- Rule: if CodeRabbit or the fix pass surfaces evidence that invalidates an approved assumption or collapses the approved net-value case, return to research and resume at Phase 2.5 instead of treating it as an ordinary review fix.

## Phase 8 - Post-CodeRabbit Review Gates

- These are the PR-opening gates on the actual diff.
- Policy: follow `~/ai/workflows/pr-review.md`.
- That workflow covers test-audit review, multi-concern PR review, justification PR review, and commit hygiene.
- Rule: do not duplicate the full procedure here.
- Rule: if those gates say the diff should be split, split it before opening PRs.
- Rule: Process-tree review: after Phase 8 gates pass and before Phase 9, run `process-tree-auditor` on the delegated CodeRabbit and PR-review subtrees. A blocking process violation prevents draft PR creation until the affected subtree is rerun or repaired.

## Phase 9 - Draft PR

- Routine automation step after all prior gates pass.
- Rule: open one draft PR per concern identified by multi-concern review.
- Rule: respect dependency order for stacked work.
- Rule: follow `~/ai/conventions/git.md`.
- Rule: opening a **draft** PR is not Tier-3 by default.

## Phase 10 - Promote To Ready-For-Review

- Human-owned phase.
- Rule: promotion from draft to ready-for-review is not automated by this pipeline.

## Gate Ownership

See `~/ai/conventions/gate-ownership.md` for the phase-by-phase table.

Rule of thumb:
- phases that set scope belong to the user
- phases that validate design or code belong to agents
- the proposal is reviewed by the risk gate, not by an extra human approval pass

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

Without that record, the phase was not skipped correctly.

## Adjacent References

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
