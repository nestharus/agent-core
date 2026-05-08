---
workflow:
  id: roadmap
workflow_dispatch_contract:
  orchestrator: "roadmap-orchestrator"
  inputs:
    - "problem, philosophy, proposal, DECISIONS, market research, and engineering research artifacts"
    - "current roadmap layer to expand or revise and scratch path for risk-gate outputs"
  expectations:
    - "cascades from market framing through executive, engineering, AI, and ticket-generation layers"
    - "runs three fresh risk gates per roadmap layer and requires all LOW verdicts before advancing"
    - "routes prototype escape hatches when feasibility or decomposition cannot be proven by research alone"
  outputs:
    - "market-research.md, executive-roadmap.md, engineering-roadmap.md, and phase ai-roadmap files"
    - "generated implementation tickets for approved AI roadmap slices, including story-point estimate/source/rationale per SLICE and unsized INIT tickets"
    - "risk-gate reports and process-tree-auditor evidence at each gated layer"
  non_goals:
    - "does not bootstrap a first product pipeline from nothing"
    - "does not handle small features inside an existing product area"
    - "does not continue when product framing must reset through alignment"
---
# Roadmap Workflow

Strategic pipeline that decomposes a multi-quarter product direction into
shippable work.
Use this to expand or revise a product pipeline over time, not to bootstrap
the first pipeline.
Initial pipeline creation belongs to the implementation pipeline, not here.

Model assignments follow `~/ai/models/roles.md`.
This doc cites layer-specific routing but does not restate the model matrix.

Agent invocation: `~/ai/workflows/agents-cli.md`
Agent Q&A and session graph convention: `~/ai/conventions/agent-questions-and-session-graph.md`
Market-research rules: `~/ai/workflows/research.md`
Ticket handoff: `~/ai/workflows/implementation-pipeline.md`
Proposer/critic pattern for layer proposal/risk loops: ~/ai/conventions/proposer-critic-pattern.md

## Workflow Dispatch Surface

### Orchestrator

roadmap-orchestrator

### Inputs

- problem, philosophy, proposal, DECISIONS, market research, and engineering research artifacts
- current roadmap layer to expand or revise and scratch path for risk-gate outputs

### Expectations

- cascades from market framing through executive, engineering, AI, and ticket-generation layers
- runs three fresh risk gates per roadmap layer and requires all LOW verdicts before advancing
- routes prototype escape hatches when feasibility or decomposition cannot be proven by research alone

### Outputs

- market-research.md, executive-roadmap.md, engineering-roadmap.md, and phase ai-roadmap files
- generated implementation tickets for approved AI roadmap slices, including story-point estimate/source/rationale per SLICE and unsized INIT tickets
- risk-gate reports and process-tree-auditor evidence at each gated layer

### Non-goals

- does not bootstrap a first product pipeline from nothing
- does not handle small features inside an existing product area
- does not continue when product framing must reset through alignment

## When to use

- The current ticket backlog is empty or will be within one cycle.
- Strategy has shifted and existing tickets need to be re-scoped.
- A new product surface is opening that the current roadmap does not cover.
- You need to revise a downstream layer after a higher-layer change.

Do not use this workflow for:

- Small features inside an existing product area.
- Exploratory investigation without a commitment to ship.
- Initial pipeline creation for a product with no first roadmap yet.

## Principles

- **Separate agents for separate concerns.** Research, proposal, risk, and
  synthesis are distinct invocations.
- **Synthesis stays with `gpt-high`.** `claude-opus` judges; it does not
  integrate.
- **The risk gate is the review.** Do not add a redundant human proposal review
  on top of model risk gates.
- **All risks must return `LOW`.** If any report returns `MEDIUM` or `HIGH`,
  revise and re-run the full gate.
- **No cherry-picking risk feedback.** A revised proposal invalidates earlier
  `LOW` reports for that layer.
- **Fresh risk agents only.** If a proposer claims it re-ran risk checks, still
  dispatch new risk agents.
- **Start at the right layer.** Revision begins where misalignment surfaced and
  then propagates downward.
- **Reset upstream when framing changed.** If the problem framing changed, leave
  this workflow and re-enter product-strategy alignment first.

## Layers

### Layer 0 - Market research

- **Orchestrator** (`gpt-high`): identifies which research questions need
  answering for the planned expansion or revision.
- **Web research execution**: `gpt-high` researchers in parallel via Firecrawl
  MCP or equivalent.
- **Research rule**: primary-source citations required. Follow
  `~/ai/workflows/research.md`.
- **Synthesis** (`gpt-high`): market-research summary with evidence,
  assumptions, tradeoffs, and open risks.
- **Surface check**: if research reveals a product-strategy shift that changes
  the framing of the problem, re-enter the product-strategy alignment loop
  instead of continuing downward here.
- **Question handling**: delegated questions are allowed only for framing choices that block market research or downstream ordering. The root handles `NEEDS_INPUT:<question_artifact>` through `~/ai/conventions/agent-questions-and-session-graph.md`.
- **Gate**: human approves the market framing before roadmap work begins.

### Layer 1 - Executive roadmap

- **Proposer** (`gpt-high`): strategic ordering of product moves with rationale,
  dependencies, anti-goals, and intended outcomes.
- **Risk gates** (parallel, 3x):
  - Market misread (`claude-opus`): does the ordering still hold if the market
    reads differ from the current assumptions?
  - Dependency trap (`claude-opus`): are we sequencing moves that hide a
    downstream blocker or unscheduled prerequisite?
  - Completeness (`gpt-high`): is every promised outcome traceable to a planned
    item in the ordering?
- **Revision rule**: all three must return `LOW`; otherwise revise and re-run
  the full Layer 1 gate.
- **Process-tree review**: after the parallel risk gates join and before the layer advances, run `process-tree-auditor` on the layer risk-gate subtree. The expected process includes the three risk reports, required model/role assignments, prompts/logs, and verdict artifacts. A blocking process violation prevents the layer gate from advancing.
- **Question handling**: delegated questions are allowed only for ordering disagreements that require human strategic input. The root must answer and apply them before engineering-layer decomposition begins.
- **Gate**: human approves the strategic ordering before engineering-layer
  decomposition begins.

### Layer 2 - Engineering roadmap

- **Engineering codebase research** (`gpt-high`): map the executive ordering
  onto the current system.
- **Research focus**: prerequisite infrastructure, existing patterns, migration
  paths, coupling constraints, and major technical unknowns.
- **Proposer** (`gpt-high`): engineering roadmap with ordered milestones,
  dependencies on the existing system, and estimated magnitude.
- **Risk gates** (parallel, 3x):
  - Feasibility (`gpt-high`): does the ordering match what the codebase can
    actually support without hidden rewrites not on the plan?
  - Integration (`claude-opus`): do the milestones fit together coherently, or
    does each milestone assume a different system?
  - Drift (`claude-opus`): does the engineering roadmap still implement the
    executive roadmap it claims to serve?
- **Revision rule**: all three must return `LOW`; otherwise revise and re-run
  the full Layer 2 gate.
- **Process-tree review**: after the parallel risk gates join and before the layer advances, run `process-tree-auditor` on the layer risk-gate subtree. The expected process includes the three risk reports, required model/role assignments, prompts/logs, and verdict artifacts. A blocking process violation prevents the layer gate from advancing.
- **Question handling**: delegated questions are allowed only for engineering-vs-executive divergence or ordering decisions owned by the user. The root blocks Layer 3 until continuation evidence exists.
- **Gate**: human resolves engineering-vs-executive ordering disagreements.
- **Prototype escape hatch**: when feasibility risk cannot be assessed from research alone (the proposed substrate's behavior under load, the third-party integration's actual contract, etc.), dispatch `~/ai/agents/prototype-orchestrator.md` per `~/ai/workflows/build-prototype.md` with `roadmap_layer=engineering-roadmap` and the unanswered feasibility question. The prototype's dossier supplies the evidence the feasibility risk gate is waiting on. Roadmap revision incorporates the dossier's findings before the layer's gates re-run.

### Layer 3 - AI-optimized roadmap

- **Proposer** (`gpt-high`): decomposes the engineering roadmap into slices
  small enough for the implementation pipeline to execute reliably.
- **Output shape**: slices should be coherent, schedulable, and explicit about
  prior-slice dependencies.
- **Risk gates** (parallel, 3x):
  - Decomposition (`claude-opus`): is each slice cohesive and self-contained,
    or does it require mid-slice context handoff?
  - Coverage (`gpt-high`): does every engineering-roadmap item map to at least
    one AI slice? Require a crosswalk.
  - Dependency (`claude-opus`): do the slices linearize cleanly, or do they
    depend on parallel-agent coordination the pipeline cannot model well?
- **Revision rule**: all three must return `LOW`; otherwise revise and re-run
  the full Layer 3 gate.
- **Process-tree review**: after the parallel risk gates join and before the layer advances, run `process-tree-auditor` on the layer risk-gate subtree. The expected process includes the three risk reports, required model/role assignments, prompts/logs, and verdict artifacts. A blocking process violation prevents the layer gate from advancing.
- **Question handling**: delegated questions are allowed only for divergence from Layer 2 that the orchestrator flags as human-reviewable. Model-owned decomposition and coverage gates do not become user Q&A.
- **Gate**: model. The orchestrator validates completeness against Layer 2.
  Human review is required only if the orchestrator flags divergence.
- **Prototype escape hatch**: when a slice's contract / parallelizability / schema cannot be named without trying it, dispatch `~/ai/agents/prototype-orchestrator.md` with `roadmap_layer=ai-roadmap-phase-N` and the slice's unknowns as the prototype's question. The dossier's spawned-tickets.md becomes the slice's eventual implementation tickets at Layer 4; the dossier's risk-profile becomes the slice's pre-Phase-2.5 baseline.

### Layer 4 - Ticket generation

- **Generator** (`gpt-high`): writes one ticket per AI slice.
- **Each ticket includes**: scope, acceptance criteria, dependencies on earlier
  slices, revision rationale from the roadmap stage above it, and story-point estimate,
  estimate source, and estimate rationale per SLICE ticket; INIT tickets remain unsized
  at Layer 4.
- **Constraint**: tickets are handoff artifacts, not mini-roadmaps. Keep them
  implementation-ready.
- **Process-tree review**: when ticket generation used delegated operators, run `process-tree-auditor` on the delegated ticket-generation subtree before implementation handoff. The expected process includes each delegated operator prompt/log, generated ticket output, and handoff status. A blocking process violation prevents tickets from entering the implementation pipeline.
- **Question handling**: delegated questions are allowed only for ticket-review decisions owned by the user. The implementation pipeline cannot consume tickets that depend on an unanswered question.
- **Gate**: human reviews tickets before they enter the implementation
  pipeline.

## Risk-Type Reference

Risk-type routing in this workflow is layer-specific.
Presence and checklist-style risks go to `gpt-high`.
Intent and direction-style risks go to `claude-opus`.
See `~/ai/models/roles.md`.

| Layer | Risk type | Model | What it checks |
|---|---|---|---|
| Executive | Market misread | `claude-opus` | Does the ordering hold if the market signals differ from our read? |
| Executive | Dependency trap | `claude-opus` | Does a later item secretly depend on something not scheduled? |
| Executive | Completeness | `gpt-high` | Is every promised outcome traceable to a scheduled item? |
| Engineering | Feasibility | `gpt-high` | Does the ordering match what the codebase can support? |
| Engineering | Integration | `claude-opus` | Do the milestones fit coherently, or does each assume a different system? |
| Engineering | Drift | `claude-opus` | Does this roadmap still implement the executive roadmap it claims to? |
| AI | Decomposition | `claude-opus` | Is each slice cohesive and self-contained? |
| AI | Coverage | `gpt-high` | Does every engineering item map to at least one AI slice? |
| AI | Dependency | `claude-opus` | Do the slices linearize cleanly? |

## Rules

- **Do not default all risks to `claude-opus`.** Follow the layer-specific
  presence-vs-intent split above.
- **Proposers do not write their own risk reports.** They propose and revise.
  Separate agents judge.
- **Opus never synthesizes.** This applies to market-research synthesis,
  roadmap coordination, and ticket integration.
- **Human checkpoints exist at each strategic boundary.** Use them to approve
  framing, ordering, and ticket handoff.
- **Layer 4 feeds the implementation pipeline.** Once tickets are approved,
  execution moves to `~/ai/workflows/implementation-pipeline.md`.
- **Roadmap work is strategic, not exploratory.** If the goal is only to learn,
  use `~/ai/workflows/research.md`.
- **This workflow expands or revises over time.** It is not the bootstrap path
  for a product with no initial roadmap.
- **Question handling stays root-owned.** Delegated `NEEDS_INPUT:<question_artifact>` returns are allowed only at layer framing, disagreement, divergence, and ticket-review gates. The root surfaces the question and blocks dependent layers until answer and continuation evidence exist.

## Expansion vs Revision

Use the same pipeline for both, but start at the right layer.

- **Expansion**: adding a new product surface or extending the strategic
  horizon. Usually runs Layer 0 through Layer 4 in order.
- **Revision**: existing roadmap is stale or misaligned. Start at the layer
  where the misalignment surfaced, then propagate downward.

Examples:

- Market assumption changed: start at Layer 0 or exit to product-strategy
  alignment if the framing itself changed.
- Executive ordering changed but product framing did not: start at Layer 1.
- Codebase constraints invalidate the plan: start at Layer 2.
- Milestones are valid but too coarse for implementation: start at Layer 3.

If strategy itself shifted, the roadmap workflow cannot recover from that
upstream framing error.
Reset to product-strategy alignment first, then return here only after the
framing is stable again.

## References

- Canonical layered roadmap loop:
  `/home/nes/projects/server-manager/AGENTS.md`
- Per-layer risk-type split and expansion caveat:
  `/home/nes/projects/videos/AGENTS.md`
- Model-role authority: `~/ai/models/roles.md`
- Research rules: `~/ai/workflows/research.md`
- Ticket handoff target: `~/ai/workflows/implementation-pipeline.md`
