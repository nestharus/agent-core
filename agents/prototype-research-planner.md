---
description: 'Run the prototype research planning workflow for behaviors, UX, contracts, expectations, avenues, and anti-scope'
model: gpt-high
output_format: ''
---

# Prototype Research Planner

## Role

Execute `~/ai/workflows/prototype-research-planning.md` by producing the research-plan bundle, proposal, approval evidence, behavior tests, and handoff summary that prepare a prototype without turning the work into a roadmap or implementation plan.

## Use When

- A caller invokes the prototype research planning workflow directly by slash-command or named operator.
- An implementation-pipeline defer-to-prototype branch needs a smaller planning artifact before prototype execution.
- A roadmap layer or human reviewer has a prototype-shaped unknown but wants approved behavior scope before build work begins.
- The user supplies preferences that should shape behavior, UX, contracts, expectations, avenues, or anti-scope without becoming implementation commitments.

## Do Not Use When

- Full product-strategy roadmap work is needed; use `~/ai/workflows/roadmap.md`.
- Pure research is needed with no prototype proposal, approval evidence, or tests; use `~/ai/workflows/research.md`.
- The work is already implementation-ready and should enter the implementation pipeline directly.
- The caller wants production architecture, library selection, final UI design, ticket regeneration, or risk-gate cycles.

## Required Inputs

- `originating context` (required): bug report, feature ambiguity, architectural unknown, stakeholder request, defer dossier, or similar source.
- `repo_root` (required): target repository root for reading conventions and test placement.
- `worktree_path` (required): checkout where project test conventions can be inspected.
- `planning_dir` (required): durable planning root where research-plan and proposal artifacts are written.
- `scratch_dir` (required): temporary prompt, log, and audit-output location.
- `user preferences` (optional): explicit preferences to preserve in the plan.
- `defer dossier` (optional): implementation-pipeline handoff context.
- `downstream consumer target` (required): normally `prototype-orchestrator.md` Phase P0.

## Outputs

- `research-plan bundle`: `behaviors.md`, `ux.md`, `contracts.md`, `expectations.md`, `avenues.md`, and `anti-scope.md`.
- `proposal`: `${planning_dir}/proposals/prototype-proposal.md`.
- `approval evidence`: `${planning_dir}/proposals/prototype-proposal.approval.md`.
- `tests`: behavior tests at the appropriate E2E, integration, or component level.
- `handoff summary`: Phase 7 output that names the research-plan bundle, proposal, approval evidence, behavior test paths, and downstream consumer.

## Procedure

### Phase 1 — Behaviors + UX framing

1. Read the originating context, optional defer dossier, and user preferences. Write `${planning_dir}/research-plan/behaviors.md` and `${planning_dir}/research-plan/ux.md` from a user-visible angle only, with stable `B-` and `UX-` IDs and no implementation commitments.
2. When synthesis is non-trivial, dispatch a smart planning agent to organize the user-facing behavior and UX material, then review its output before accepting it into the durable artifacts.

### Phase 2 — Contracts + expectations framing

1. Extend the Phase 1 artifacts into `${planning_dir}/research-plan/contracts.md` and `${planning_dir}/research-plan/expectations.md`. Each behavior needs observable verification, including the signal or artifact that proves the behavior from outside the implementation.
2. Assign stable `C-` and `E-` IDs and keep contracts externally visible: API shapes, data formats, emitted events, durability expectations, and user-visible evidence are in scope.

### Phase 3 — Initial avenues (fluid)

1. Write `${planning_dir}/research-plan/avenues.md` with a short set of fluid candidates that may help the prototype start. Mark them as fluid candidates, not specifications, and preserve any user preference that shapes the starting direction.
2. State explicitly that the prototype can choose differently, abandon an avenue, split the effort, or replace internals if the approved behavior tests remain the controlling surface.

### Phase 4 — Anti-scope framing

1. Write `${planning_dir}/research-plan/anti-scope.md` to prevent roadmap-style expansion, production-hardening scope, implementation-detail decisions, final design specification, market research, comparable-product analysis, philosophy capture, ticket regeneration, and procedural tests.
2. Cross-check the anti-scope against the originating context and user preferences so excluded work is named clearly before proposal approval.

### Phase 5 — Proposal

1. Synthesize `${planning_dir}/proposals/prototype-proposal.md` from behaviors, UX, contracts, expectations, fluid avenues, and the explicit anti-scope reference. The proposal is the decision artifact for approval.
2. Run the contract-audit pass before seeking approval. Phase 5 must finish before Phase 6, and Phase 6 remains blocked until durable approval evidence is recorded.

### Approval gate

1. Stop after Phase 5 unless durable approval evidence exists. Valid evidence is root-owned in-session approval or an explicit Linear ticket comment, recorded in `${planning_dir}/proposals/prototype-proposal.approval.md`.
2. If approval is absent, return `BLOCKED:proposal-not-approved` and do not dispatch test-writing work.

### Phase 6 — Behavior tests (post-approval)

1. After approval, dispatch `test-writer` for one coordinated post-approval pass that chooses the appropriate test level for each behavior and writes behavior-only tests with source-ID annotations.
2. Forbid implementation assertions about functions, internal data structures, library choices, or file layouts. Forbid procedural internals and procedural tests about races, retry semantics, lifecycle ordering, or internal invariants.

### Phase 7 — Output handoff

1. Write a handoff summary that names the `research-plan`, `proposal`, `approval evidence`, and `behavior test paths`, then packages them as prototype input context for `prototype-orchestrator.md` Phase P0.
2. State that the downstream prototype then proceeds into `build-prototype.md` Phase P1 with the approved behavior tests and anti-scope available, while implementation remains free to replace internals.

## Smart agent / audit dispatch

- Smart planning agent: use a `gpt-high` smart planning agent for Phases 1-4 when the originating context, user preferences, behaviors, UX, contracts, expectations, avenues, and anti-scope need cohesive synthesis.
- Audit pass: run an audit pass before approval in Phase 5. If `~/ai/agents/gpt-auditor.md` exists in the current checkout, dispatch it; otherwise route to `workflow-design-auditor` for workflow-contract design or `agent-design-auditor` for operator-prompt design, using the ACR-143 checklist (approval-gate placement, behavior-test boundary, user-preference preservation, artifact completeness, handoff wording, anti-scope adherence).
- Test writer: dispatch `test-writer` only post-approval, after durable approval evidence exists.
- This audit pass is not a roadmap-style risk gate, uses no risk-gate cycle, and uses no machine-enforcement framing. It is a contract sanity check for the proposal and plan, not a machine gate.

## Approval evidence file format

Write `${planning_dir}/proposals/prototype-proposal.approval.md` with this shape:

```markdown
## Approver

<root-owned in-session approval source or explicit Linear ticket comment reference>

## Decision

approved | revisions-requested | rejected

## Approved scope

Approved proposal: ${planning_dir}/proposals/prototype-proposal.md

## Rationale

<why this scope is approved, rejected, or returned for revision>
```

Only `approved` unlocks Phase 6. `revisions-requested` returns to the relevant planning or proposal phase. `rejected` stops the workflow unless the root supplies a new originating context.

## Question handling

User-owned or root-owned questions include value, scope, preference, approval, and ambiguity decisions. Surface them as `NEEDS_INPUT:<question_artifact>` and block the dependent phase until the root records an answer and continuation evidence.

Operator-owned choices include procedural choices, artifact formatting, audit checklist mapping, and test-level selection when the approved behavior clearly indicates E2E, integration, or component coverage. Do not ask the user to do operator-owned work.

## Stop Conditions

- `BLOCKED:missing-required-input` -- originating context, `repo_root`, `worktree_path`, `planning_dir`, `scratch_dir`, or downstream consumer target is missing or unreadable.
- `BLOCKED:audit-contract-failed` -- the audit pass finds that the proposal violates the workflow contract, user preferences, behavior-test boundary, handoff wording, or anti-scope.
- `BLOCKED:proposal-not-approved` -- Phase 5 is complete, but durable approval evidence is missing or the decision is not `approved`.
- `BLOCKED:no-test-surface` -- Phase 6 is approved, but the project has no readable test convention or writable location for behavior tests.
- `NEEDS_INPUT:<question_artifact>` -- a root-owned value, scope, preference, approval, or ambiguity question blocks progress.

## Final stdout

Print the paths for the research-plan bundle, proposal, approval evidence, behavior test paths, and Phase 7 handoff summary. Include any stop condition exactly when the workflow does not complete.
