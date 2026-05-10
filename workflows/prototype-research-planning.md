---
workflow:
  id: prototype-research-planning
workflow_dispatch_contract:
  orchestrator: "prototype-research-planner"
  inputs:
    - "originating context (bug report, feature ambiguity, architectural unknown, stakeholder request, defer dossier)"
    - "project repo_root, worktree_path, planning_dir, scratch_dir"
    - "optional user preferences"
    - "optional defer dossier from implementation-pipeline Phase 2.5 defer-to-prototype branch"
    - "downstream consumer target (normally prototype-orchestrator.md Phase P0)"
  expectations:
    - "produces a research-plan bundle (behaviors / UX / contracts / expectations / fluid avenues / anti-scope) and a prototype-proposal that captures behaviors, UX flows, contracts, and approved fluid avenues without making implementation commitments"
    - "halts at the proposal-approval gate until durable approval evidence exists"
    - "post-approval, ships behavior tests only -- never procedural / lifecycle / race / retry / internal-invariant tests"
  outputs:
    - "behaviors.md, ux.md, contracts.md, expectations.md, avenues.md, anti-scope.md, prototype-proposal.md, approval evidence, behavior tests at appropriate E2E/integration/component levels"
    - "Phase 7 handoff summary feeding prototype input context to prototype-orchestrator.md Phase P0 (which then proceeds into build-prototype.md Phase P1)"
  non_goals:
    - "does not perform market research, comparable-product analysis, or philosophy/values capture"
    - "does not run a 4-layer roadmap cascade or generate sub-tickets"
    - "does not run risk-gate cycles inside the prototype workflow"
    - "does not pick implementation details, libraries, or architecture for the prototype"
    - "does not specify final UI design"
    - "does not introduce machine-enforcement framing"
    - "does not declare itself as the merge gate; the prototype branch's disposition is owned downstream"
---
# Prototype Research Planning Workflow

This is the lighter prototype path, not the full product-strategy roadmap. It prepares a prototype by naming the behaviors, UX expectations, contracts, fluid avenues, anti-scope, approval evidence, and behavior tests needed before downstream prototype work begins, without copying the full roadmap cascade.

## Workflow Dispatch Surface

### Orchestrator

prototype-research-planner

### Inputs

- originating context (bug report, feature ambiguity, architectural unknown, stakeholder request, defer dossier)
- project repo_root, worktree_path, planning_dir, scratch_dir
- optional user preferences
- optional defer dossier from implementation-pipeline Phase 2.5 defer-to-prototype branch
- downstream consumer target (normally prototype-orchestrator.md Phase P0)

### Expectations

- produces a research-plan bundle (behaviors / UX / contracts / expectations / fluid avenues / anti-scope) and a prototype-proposal that captures behaviors, UX flows, contracts, and approved fluid avenues without making implementation commitments
- halts at the proposal-approval gate until durable approval evidence exists
- post-approval, ships behavior tests only -- never procedural / lifecycle / race / retry / internal-invariant tests

### Outputs

- behaviors.md, ux.md, contracts.md, expectations.md, avenues.md, anti-scope.md, prototype-proposal.md, approval evidence, behavior tests at appropriate E2E/integration/component levels
- Phase 7 handoff summary feeding prototype input context to prototype-orchestrator.md Phase P0 (which then proceeds into build-prototype.md Phase P1)

### Non-goals

- does not perform market research, comparable-product analysis, or philosophy/values capture
- does not run a 4-layer roadmap cascade or generate sub-tickets
- does not run risk-gate cycles inside the prototype workflow
- does not pick implementation details, libraries, or architecture for the prototype
- does not specify final UI design
- does not introduce machine-enforcement framing
- does not declare itself as the merge gate; the prototype branch's disposition is owned downstream

## Use When

- Use this when the originating context is a bug report, feature ambiguity, architectural unknown, stakeholder request, or defer dossier that needs a prototype-ready research plan before build work.
- Use this when the user has preferences about behavior, UX, contracts, dependencies, or scope, but the prototype should still remain free to choose its implementation.
- Use this when the downstream consumer is the prototype execution path and the next artifact should be prototype input context rather than a production roadmap.
- Use this when the work is too fluid for a full roadmap but specific enough to name observable behavior and approval criteria.

## Do Not Use When

- Use `~/ai/workflows/roadmap.md` when the task needs the heavier product-strategy roadmap, market research, layered planning, risk gates, or ticket generation.
- Use `~/ai/workflows/research.md` when the task is only factual investigation and should not produce a prototype proposal, approval evidence, or behavior tests.
- Use the implementation pipeline when the work is already scoped tightly enough for normal ticket execution.

## Inputs

- `originating context`: bug report, feature ambiguity, architectural unknown, stakeholder request, defer dossier, or other source that explains the prototype question.
- `repo_root`, `worktree_path`, `planning_dir`, and `scratch_dir` for project files, planning artifacts, and temporary logs.
- Optional `user preferences` that should shape behaviors, UX, contracts, avenues, or anti-scope.
- Optional defer dossier from an implementation-pipeline decision that chose prototype planning as the next step.
- `downstream consumer`: usually `prototype-orchestrator.md` via the Phase 7 handoff.

## Outputs

- `${planning_dir}/research-plan/behaviors.md`
- `${planning_dir}/research-plan/ux.md`
- `${planning_dir}/research-plan/contracts.md`
- `${planning_dir}/research-plan/expectations.md`
- `${planning_dir}/research-plan/avenues.md`
- `${planning_dir}/research-plan/anti-scope.md`
- `${planning_dir}/proposals/prototype-proposal.md`
- `approval evidence` for the proposal gate.
- `behavior tests` at the appropriate E2E, integration, or component level.
- A Phase 7 handoff summary for downstream prototype execution.

## Phases

### Phase 1 — Behaviors + UX framing

Capture the behaviors the prototype should demonstrate from a user-facing perspective and the UX signals that make those behaviors understandable. `behaviors.md` names what the system should do; `ux.md` names what the user sees, how flows feel, what ambiguities matter, and which stated user preferences should shape the prototype.

### Phase 2 — Contracts + expectations framing

Write `contracts.md` for input/output expectations, API shapes, data formats, observable signals, and other externally visible contracts. Write `expectations.md` so every behavior has an observable verification approach and evidence expectation that a later behavior test can cite.

### Phase 3 — Initial avenues (fluid)

Write `avenues.md` with a few fluid candidate avenues worth trying first. These avenues are not commitments and not specifications; they are starting points the prototype may abandon, split, replace, or ignore when implementation evidence points elsewhere.

### Phase 4 — Anti-scope framing

Write `anti-scope.md` to state what the prototype is not trying to answer. The anti-scope keeps the prototype from becoming production planning in disguise and protects the fluid prototype from roadmap, hardening, and final-design drift.

### Phase 5 — Proposal

Write `prototype-proposal.md` to summarize the selected behaviors, UX flows, contracts, expectations, fluid avenues, and anti-scope. The proposal is the approval artifact; it must be clear enough that approval means the user accepts the behavior scope and the explicit exclusions.

### Approval gate

Phase 6 cannot start until durable approval evidence exists. Approval may be root-owned in-session approval or an explicit ticket comment, but it must be recorded before any behavior-test authoring starts.

### Phase 6 — Behavior tests (post-approval)

Post-approval, author behavior tests at the appropriate level for each approved behavior: E2E for user-facing flows, integration for cross-module behavior, and component for individual capability boundaries. Tests are behavior-only and check observable behavior; they never include implementation assertions and never include implementation details such as specific functions called, internal data structures, library choices, or file layouts.

No procedural tests are produced here. Forbid procedural assertions about races, retry semantics, lifecycle quirks, internal invariants, internal ordering, or disposable prototype mechanics. The prototype may brute-force or replace internals as long as approved behavior remains true.

### Behavior-test annotation rule

Every behavior test must include a `Covers:` annotation that links the test back to stable source IDs from the plan, for example `Covers: B-001, UX-003, C-002, E-001`. Use `B-` for behavior, `UX-` for UX, `C-` for contract, and `E-` for expectation IDs so each test traces to behavior, UX, contract, and expectation sources as applicable.

### Phase 7 — Output handoff

Write a handoff summary that packages the research-plan bundle, proposal, approval evidence, and behavior test paths as prototype input context. The handoff target is `prototype-orchestrator.md` Phase P0, and the downstream build then proceeds into `build-prototype.md` Phase P1 with the approved scope and behavior tests available.

## Anti-scope

- no market research
- no comparable-product analysis
- no philosophy
- no 4-layer cascade
- no ticket regeneration
- no risk-gate cycles
- no implementation-detail decisions
- no design specification
- no machine enforcement
- no procedural tests

## Cross-references

- `~/ai/workflows/roadmap.md` -- heavier product-strategy roadmap; use it for market, philosophy, layered planning, risk gates, and ticket regeneration.
- `~/ai/workflows/research.md` -- sibling factual research workflow; use it when there is no prototype proposal or approval gate.
- `~/ai/workflows/build-prototype.md` -- downstream prototype execution workflow that starts its build work at Phase P1.
- `~/ai/agents/prototype-orchestrator.md` -- downstream operator that consumes prototype input context at Phase P0.
