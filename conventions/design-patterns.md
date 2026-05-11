# Design Patterns

This file is a thin citation index for workflow and operator design auditors. It gives stable pattern IDs, concise statements, canonical authorities, exemplars, and auditor citation guidance while leaving detailed procedure ownership in the linked sources.

## Purpose

Use these entries as report citations for `workflow-design-auditor` and `agent-design-auditor`. When a design finding relies on a primary source outside this index, mark the finding as `unindexed-pattern` so later corpus maintenance can decide whether to add an entry.

## Pattern Index

### DP-001 - Proposer/critic revise-review loop
- Short statement: Proposers author or revise the artifact, independent critics review it, and accepts apply only to the same current artifact.
- Canonical authority: `~/ai/conventions/proposer-critic-pattern.md`
- Exemplars: `~/ai/workflows/implementation-pipeline.md` Phase 4; `~/ai/workflows/roadmap.md`; `~/ai/workflows/coderabbit-loop.md`
- Auditor use: Cite when a workflow allows stale accepts, lets a proposer self-certify, or fails to rerun required critics after substantive revision.

### DP-002 - All-current-artifact accept rule
- Short statement: An accept verdict is only meaningful for the current artifact version and cannot be carried across substantive revisions.
- Canonical authority: `~/ai/conventions/proposer-critic-pattern.md`
- Exemplars: `~/ai/workflows/implementation-pipeline.md` Phase 4; `~/ai/conventions/audit-history.md`
- Auditor use: Cite when a workflow reuses prior approval after a changed target or omits the rerun condition for acceptance.

### DP-003 - Per-role audit history through one canonical file
- Short statement: Repeated review loops keep role outputs, decisions, watch signals, and round summaries in one canonical audit-history file.
- Canonical authority: `~/ai/conventions/audit-history.md`
- Exemplars: `~/ai/agents/decision-encoder.md`; `~/ai/workflows/pr-review.md`; `~/ai/workflows/coderabbit-loop.md`
- Auditor use: Cite when a repeated loop scatters review memory, creates competing history files, or leaves no decision-encoder handoff.

### DP-004 - Single-concern operator/tool composition
- Short statement: Operators and tools should own one coherent concern and compose with adjacent specialists instead of accumulating unrelated modes.
- Canonical authority: `~/ai/VALUES.md`
- Exemplars: `~/ai/agents/operator-file-format.md`; `~/ai/conventions/code-quality.md`; `~/ai/agents/cohesion-auditor.md`; `~/ai/agents/coupling-auditor.md`
- Auditor use: Cite when an operator bundles unrelated responsibilities, hides a second system inside flags, or duplicates an adjacent specialist.

### DP-005 - Model-owned gates and no self-certification
- Short statement: Model-owned gates must be independent from the artifact author, while human-owned gates surface only genuine value or scope decisions.
- Canonical authority: `~/ai/conventions/gate-ownership.md`
- Exemplars: `~/ai/conventions/proposer-critic-pattern.md`; `~/ai/workflows/implementation-pipeline.md`
- Auditor use: Cite when a workflow lets the author certify its own work, hides a required human gate, or gives a model a user-owned decision.

### DP-006 - Workflow frontmatter and dispatch contract
- Short statement: Shared workflows need stable identity metadata and a dispatch contract that callers can inspect before invoking them.
- Canonical authority: `~/ai/conventions/workflow-aliases.md`
- Exemplars: `~/ai/workflows/implementation-pipeline.md`; `~/ai/workflows/pr-review.md`; `~/ai/workflows/coderabbit-loop.md`
- Auditor use: Cite when workflow identity, inputs, caller contract, or index expectations are missing or contradictory.

### DP-007 - Operator frontmatter and recommended body skeleton
- Short statement: Operator files require dispatchable frontmatter and should use explicit body sections that make routing, inputs, procedure, and stop behavior auditable.
- Canonical authority: `~/ai/agents/operator-file-format.md`
- Exemplars: `~/ai/agents/cohesion-auditor.md`; `~/ai/agents/coupling-auditor.md`; `~/ai/agents/process-tree-auditor.md`; `~/ai/agents/operator-file-format.md`
- Auditor use: Cite when an operator is malformed for CLI loading or when missing body sections create material routing or invocation ambiguity.

### DP-008 - Process-tree audits at fanout joins
- Short statement: Delegated fanout workflows need process-tree review before downstream synthesis consumes child outputs.
- Canonical authority: `~/ai/agents/process-tree-auditor.md`
- Exemplars: `~/ai/workflows/implementation-pipeline.md`; `~/ai/workflows/pr-review.md`; `~/ai/workflows/roadmap.md`
- Auditor use: Cite when a workflow with required delegation lacks a process-tree join, expected-process evidence, or companion-artifact verification.

### DP-009 - Tests/code separation and firstness evidence
- Short statement: Test authoring and product implementation are separate phases, and new tests need evidence that they preceded the code they validate.
- Canonical authority: `~/ai/workflows/implementation-pipeline.md`
- Exemplars: `~/ai/workflows/pr-review.md`; `~/ai/agents/red-phase-gate.md`; `~/ai/agents/green-phase-gate.md`
- Auditor use: Cite when a workflow collapses test and code authorship, omits red/green phase evidence, or treats unproven tests as acceptance.

### DP-010 - Sub-workflow composition with standalone and pipeline-callable modes
- Short statement: Reusable sub-workflows should define how direct invocation and pipeline invocation share one contract without absorbing caller-specific policy.
- Canonical authority: `~/ai/VALUES.md`
- Exemplars: `~/ai/workflows/research.md`; `~/ai/workflows/coderabbit-loop.md`; `~/ai/workflows/pr-review.md`
- Auditor use: Cite when a workflow cannot be called both directly and by an orchestrator without hidden assumptions or caller-specific procedure drift.

### DP-011 - AGENTS.md as routing and topology
- Short statement: AGENTS.md is the routing and topology catalog; detailed procedure belongs in the linked operator, workflow, or convention file.
- Canonical authority: `~/ai/AGENTS.md`
- Exemplars: `~/ai/agents/agentsmd-curator.md`; `~/ai/conventions/workflow-routing.md`
- Auditor use: Cite when routing rows contain procedure detail, linked operators are missing, or catalog changes trespass on operator design.

### DP-012 - Explicit anti-scope and stop conditions
- Short statement: Operators and workflows should name boundaries and stop conditions so callers know when to proceed, hand off, block, or ask for input.
- Canonical authority: `~/ai/agents/operator-file-format.md`
- Exemplars: `~/ai/agents/process-tree-auditor.md`; `~/ai/agents/cohesion-auditor.md`; `~/ai/agents/coupling-auditor.md`; `~/ai/conventions/agent-questions-and-session-graph.md`
- Auditor use: Cite when an artifact lacks out-of-scope routing, stop outcomes, escalation behavior, or question-handling boundaries.
