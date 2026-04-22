# Implementation Pipeline

End-to-end pipeline from triggering event to merged PR.
Bugs start with RCA. Features, refactors, and other planned work skip RCA.

Model assignments are authoritative in `~/ai/models/roles.md`.
Do not restate or override that matrix in project docs.
Use it exactly, including the synthesis/audit-vs-judgment split and the rule that `gpt-xhigh` is not the default coordinator.

Agent invocation: `~/ai/workflows/agents-cli.md`
Parallel-agent isolation: `~/ai/conventions/worktree-isolation.md`
Git and PR conventions: `~/ai/conventions/git.md`

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
- `Phase 3 -> Phase 4 -> Phase 5 -> Phase 6 -> Phase 7 -> Phase 8 -> Phase 9 -> Phase 10`

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

## Phase 3 - Proposal

- Artifact: `proposals/NN-*.md`
- Role: propose design, scope, architecture, tradeoffs, anti-scope, and expected tests. State what will not be changed. **Do not** implement.
- Rules: the proposal must be reviewable on its own terms. "We will figure it out during implementation" is not sufficient design. The proposer does not write its own risk reports.
- Gate: no default human approval step. The proposal advances only by passing Phase 4.

## Phase 4 - Risk Gates (required; parallel)

Run the risk gate on the proposal artifact, not on hand-waved intent.
The exact model assignments for these three roles live in `~/ai/models/roles.md`.

- Artifacts: `risk/NN-audit.md`, `risk/NN-scope.md`, `risk/NN-shortcut.md`
- `audit risk`: presence, contracts, migrations, tests, and other checklist obligations
- `scope risk`: does the proposal stay within the stated scope
- `shortcut risk`: do proposed shortcuts defeat the underlying purpose
- Rule: all three reports must return `LOW`.
- Rule: if any report returns `MEDIUM` or `HIGH`, revise the proposal and re-run all three.
- Rule: do not keep old `LOW` reports after a substantive proposal revision.
- Rule: if a proposer claims it "re-ran the risks itself," ignore that claim and re-dispatch the actual risk agents.
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
- Gate: human. The user confirms what survives, what is replaced, and what is deleted.

## Phase 6 - Implementation (required; test/code separation)

Implementation has three sub-steps.
The test writer and the code writer must be different agent invocations.
That rule is load-bearing: if the same agent writes both, the tests mirror the implementation instead of validating the contract.

### Step 6a - Define contract

- Owner: orchestrator
- Produces: schemas, signatures, commands, interface boundaries, and explicit behavioral assumptions
- Rule: the contract must be clear enough that another agent can write tests from it without seeing implementation code.

### Step 6b - Write tests

- Inputs: contracts only
- Rule: the test writer is a separate agent invocation from Step 6c.
- Rule: the test writer does **not** see the implementation.
- Rule: tests encode expected behavior from the contract.
- Output: `tests/` changes describing intended behavior

### Step 6c - Write code

- Inputs: contracts and the tests from Step 6b
- Rule: the code writer is a separate agent invocation from Step 6b.
- Rule: the job is to make the tests pass while respecting the approved design and architecture.
- Rule: if tests fail after Step 6c, re-invoke the code agent with the test output.
- Rule: do **not** re-invoke the test agent because the implementation failed.
- Rule: if a test is wrong, that is the contract's fault, not the test's.
- Rule: if contract intent truly changed, revise the contract explicitly and regenerate the affected tests from that revised contract.
- Operational note: parallel implementation is allowed only under `~/ai/conventions/worktree-isolation.md`.

## Phase 7 - CodeRabbit Loop

- Run CodeRabbit only after implementation is functionally complete enough for review.
- Policy: follow `~/ai/workflows/coderabbit-loop.md`.
- Rules: do not duplicate the CodeRabbit procedure here. This phase reviews the actual diff, not the proposal.

## Phase 8 - Post-CodeRabbit Review Gates

- These are the PR-opening gates on the actual diff.
- Policy: follow `~/ai/workflows/pr-review.md`.
- That workflow covers test-audit review, multi-concern PR review, justification PR review, and commit hygiene.
- Rule: do not duplicate the full procedure here.
- Rule: if those gates say the diff should be split, split it before opening PRs.

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

If a phase is skipped, narrowed, or deferred:
- record it in `DECISIONS.md` or the project equivalent
- record who made the decision
- record why the change was accepted
- record what risk is being accepted

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
