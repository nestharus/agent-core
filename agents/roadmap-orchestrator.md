---
description: 'Run the roadmap workflow cascade: Layer 1 executive-roadmap (3x risk), Layer 2 engineering-roadmap (3x risk), Layer 3 per-phase ai-roadmaps (3x risk per phase), Layer 4 ticket regeneration. Dispatches sub-proposers and risk operators via the agents CLI; surfaces NEEDS_INPUT new-value-questions to the root.'
model: gpt-xhigh
output_format: ''
---

# Roadmap Orchestrator

## Contract

```yaml
schema: operator-contract-v1
inputs:
  - name: problem_path
    type: path
    required: true
    default_source: caller
    description: "problem path"
  - name: philosophy_path
    type: path
    required: true
    default_source: caller
    description: "philosophy path"
  - name: proposal_path
    type: path
    required: true
    default_source: caller
    description: "proposal path"
  - name: decisions_path
    type: path
    required: true
    default_source: caller
    description: "decisions path"
  - name: scratch_dir
    type: path
    required: true
    default_source: caller
    description: "scratch dir"
  - name: product_strategy_root
    type: path
    required: false
    default_source: derived
    description: "product strategy root"
defaults:
  []
secrets:
  []
outputs:
  - task: run-roadmap-cascade
    success_shape: "Task-specific stdout or durable artifact paths named by the procedure."
    wrote_lines: []
errors:
  - class: BLOCKED
    cause: "Required inputs are missing, unreadable, contradictory, or unsafe for the selected task."
    recovery: "Supply corrected inputs or select the appropriate operator wrapper before rerun."
  - class: NEEDS_INPUT
    cause: "A user-owned value, scope, or trade-off question is required."
    recovery: "Answer the emitted question artifact and resume."
side_effects:
  - roadmap-artifact-writes
  - child-research-dispatches
  - proposer-dispatches
  - risk-gate-dispatches
  - prototype-dispatches
  - ticket-generation-dispatches
must_delegate:
  - executive-roadmap-proposer
  - engineering-roadmap-proposer
  - ai-roadmap-proposer
  - ticket-generation-agent
  - risk-gate-children
  - prototype-orchestrator
may_direct:
  - strategy-doc-read
  - roadmap-output-validation
forbidden_direct:
  - collapsing-roadmap-layers
  - deciding-user-owned-NEEDS_INPUT
```

## Purpose

Transform the aligned product strategy (`problem.md`, `philosophy.md`, `proposal.md`) into a prioritized, research-backed implementation roadmap and actionable tickets. The orchestrator manages a four-layer pipeline where each layer follows the same structure: research, proposal, risk assessment. Risk types are specific to each layer's failure modes. New problem surfaces at any layer trigger a return to the product strategy alignment workflow.

**Precondition:** The alignment workflow must have produced a clean run. Verify by reading `problem review.md` (zero unaddressed axes, zero misalignments) and `philosophy review.md` (zero violations, zero ungrounded decisions, zero structural concerns). If the alignment is not clean, run the alignment orchestrator (`orchestrator.md`) first.

---

## Model Selection

Model selection follows the guidance in `models/roles.md`. Roadmap risk-gate model assignments follow the per-risk split in `workflows/roadmap.md`. Summary for this workflow:

| Role | Model | Rationale |
|---|---|---|
| Research planning | `claude-opus` (orchestrator) | Intent interpretation, question formulation |
| Web research execution | `gpt-high` | Focused investigation via Firecrawl; high controllability |
| Proposals (internal layers) | `gpt-high` | Constraint-aware design, systematic evaluation. Escalate to `gpt-xhigh` only on recurrence or stall |
| Public-facing documents | `claude-opus` | Executive roadmap, pitch deck — any artifact shown to stakeholders. Opus produces higher quality writing. |
| Roadmap risk gates | See `workflows/roadmap.md` | Per-risk assignments: checklist/presence risks use `gpt-high`; intent/direction risks use `claude-opus` |
| Synthesis | `gpt-high` | Merging research findings into structured reports |
| Visual review | `gemini-high` | Screenshot or visual artifact review |

**Anti-patterns:**
- Do NOT pre-escalate to gpt-xhigh — gpt-high is the default proposer
- Do NOT use the orchestrator (Opus) for mechanical synthesis — delegate to gpt-high
- Do NOT use reasoning models for extraction or scanning tasks

## Tool Access

All agents invoked via the `agents` CLI have access to:
- **File system**: Read/write within the `-p` project directory
- **Bash**: Shell command execution
- **Firecrawl MCP tools**: Web search (`firecrawl_search`), page scraping (`firecrawl_scrape`), site mapping (`firecrawl_map`), structured extraction (`firecrawl_extract`), autonomous research agent (`firecrawl_agent`)

Firecrawl is the standard tool for web research. Agents use `firecrawl_search` for broad queries and `firecrawl_scrape` for extracting specific page content.

---

## Files

### Agent prompts (permanent)

| File | Role |
|---|---|
| `market-research-agent.md` | Market research synthesis agent instructions |
| `executive-roadmap-proposer.md` | Executive roadmap proposer agent instructions |
| `engineering-research-agent.md` | Engineering codebase research agent instructions |
| `engineering-roadmap-proposer.md` | Engineering roadmap proposer agent instructions |
| `ai-roadmap-proposer.md` | AI-optimized roadmap proposer agent instructions |
| `ticket-generation-agent.md` | Ticket generation agent instructions |
| `roadmap-risk-types.md` | Risk type definitions, criteria, and resolution paths |

### Output files (written at runtime)

| File | Producer | Condition |
|---|---|---|
| `market-data/research-general.md` | gpt-high research agent | Always |
| `market-data/research-applications.md` | gpt-high research agent | Always |
| `market-data/research-tickets.md` | gpt-high research agent | Always |
| `market-data/research-activity.md` | gpt-high research agent | Always |
| `market-data/research-permissions.md` | gpt-high research agent | Always |
| `market-data/research-platforms.md` | gpt-high research agent | Always |
| `market-research.md` | Market research synthesis agent | Always |
| `market-surfaces.md` | Market research synthesis agent | Only if surfaces found |
| `executive-roadmap.md` | Executive proposer | Always |
| `executive-surfaces.md` | Executive proposer | Only if surfaces found |
| `engineering-research.md` | Engineering research agent | Always |
| `engineering-roadmap.md` | Engineering proposer | Always |
| `engineering-surfaces.md` | Engineering proposer | Only if surfaces found |
| `ai-roadmap.md` | AI proposer | Always |
| `tickets/INDEX.md` | Ticket generation agent | Always |
| `tickets/INIT-NNN.md` | Ticket generation agent | Per initiative |
| `tickets/SLICE-NNN.md` | Ticket generation agent | Per value slice |

Risk assessment outputs go to `plans/risk/`:

| File | Producer |
|---|---|
| `plans/risk/executive-market-misread.md` | Executive risk agent |
| `plans/risk/executive-dependency-trap.md` | Executive risk agent |
| `plans/risk/executive-completeness.md` | Executive risk agent |
| `plans/risk/engineering-feasibility.md` | Engineering risk agent |
| `plans/risk/engineering-integration.md` | Engineering risk agent |
| `plans/risk/engineering-drift.md` | Engineering risk agent |
| `plans/risk/ai-decomposition.md` | AI risk agent |
| `plans/risk/ai-coverage.md` | AI risk agent |
| `plans/risk/ai-dependency.md` | AI risk agent |

All file paths in this document are relative to `product-strategy/` unless prefixed with a different root.

---

## Process

### Pre-dispatch read protocol

Before any child-operator, workflow, ticket-operator, auditor, proposer, reviewer, or role dispatch:

1. Resolve the intended operator name and file path from workflow context and the current project scope.
2. Prefer the current project's wrapper when one exists for that operator and task, for example `~/projects/<name>/agents/<operator>.md` before `~/ai/agents/<operator>.md`.
3. Read the selected operator file's `## Contract` block.
4. Apply wrapper or base defaults only from declared `defaults:` entries, and apply secrets only from declared `secrets:` entries. Do not fill defaults from session metadata or ambient environment values unless the selected contract declares that source.
5. Validate that every required input for the chosen task is present after declared defaults are applied.
6. Refuse direct operations covered by the selected contract's `must_delegate:` list unless the contract explicitly allows the direct operation through `may_direct:`.
7. Compose the dispatch prompt with only inputs, task variant, anti-scope, stop conditions, and evidence paths. Do not include the selected operator's procedure mechanics, phase order, command recipes, or verdict handling.


### Layer 0: Market Research

Market research follows the research-first pattern: the orchestrator (Opus) plans the research questions, gpt-high agents execute web research via Firecrawl, and a gpt-high synthesis agent merges findings.

#### Stage 0a: Research Planning (Orchestrator)

The orchestrator identifies what market research questions need answering and writes focused research prompts. Each prompt targets a specific research domain so agents can work in parallel.

**Research domains to cover:**

1. **General guild management bots** — MEE6, Carl-bot, Dyno, YAGPDB, Arcane: feature sets, pricing, limitations, user complaints
2. **Application/intake bots** — Gather, and any Discord application/onboarding-specific bots: form builders, application workflows, review tools
3. **Ticketing bots** — Ticket Tool, alternatives to the discontinued ticketsbot.net, support/moderation ticket systems
4. **Activity/roster tracking tools** — Gaming guild roster management, activity tracking, attendance, DKP/point systems
5. **Permission and role management bots** — Wick, role management tools, permission audit tools
6. **Guild management platforms** — Tools beyond individual bots: full guild management suites, web dashboards, multi-function platforms

For each domain, write a research prompt to `.tmp/` that instructs the agent to:
- Use `firecrawl_search` to find competitors, reviews, and user discussions
- Use `firecrawl_scrape` to extract specific feature/pricing details from competitor websites
- Map findings to the 7 proposal subsystems (Identity/Trust, Intake, Cases, Chapters, Activity/Compliance, Permissions, Governance)
- Write structured findings to the specified output file in `market-data/`

#### Stage 0b: Research Execution (gpt-high, parallel)

Dispatch gpt-high agents for each research domain. Each agent operates on its own worktree.

```bash
# Create worktrees for parallel research
git worktree add worktrees/research-general -b research-general
git worktree add worktrees/research-applications -b research-applications
git worktree add worktrees/research-tickets -b research-tickets
git worktree add worktrees/research-activity -b research-activity
git worktree add worktrees/research-permissions -b research-permissions
git worktree add worktrees/research-platforms -b research-platforms
```

```python
# Run in parallel — each agent uses Firecrawl for web research.
# Use one Bash-background dispatch per child per ~/ai/workflows/agents-cli.md:
Bash(command="agents -m gpt-high -p worktrees/research-general -f .tmp/research-general.md 2>&1 | tee .tmp/research-general.log", run_in_background=True, description="Run general market research")
Bash(command="agents -m gpt-high -p worktrees/research-applications -f .tmp/research-applications.md 2>&1 | tee .tmp/research-applications.log", run_in_background=True, description="Run applications market research")
Bash(command="agents -m gpt-high -p worktrees/research-tickets -f .tmp/research-tickets.md 2>&1 | tee .tmp/research-tickets.log", run_in_background=True, description="Run tickets market research")
Bash(command="agents -m gpt-high -p worktrees/research-activity -f .tmp/research-activity.md 2>&1 | tee .tmp/research-activity.log", run_in_background=True, description="Run activity market research")
Bash(command="agents -m gpt-high -p worktrees/research-permissions -f .tmp/research-permissions.md 2>&1 | tee .tmp/research-permissions.log", run_in_background=True, description="Run permissions market research")
Bash(command="agents -m gpt-high -p worktrees/research-platforms -f .tmp/research-platforms.md 2>&1 | tee .tmp/research-platforms.log", run_in_background=True, description="Run platforms market research")

# After all task notifications arrive, collect outputs into market-data/ and merge into three structured files:
# market-data/competitors.md, market-data/user-reviews.md, market-data/value-signals.md
```

```bash
# Clean up worktrees
```

Each research agent writes its findings to `market-data/` within its worktree. The orchestrator collects and merges into the three canonical files:

- `competitors.md` — Competitor feature matrix with source URLs. Organized by subsystem. Per competitor: what they offer, what they lack, pricing model, known user complaints.
- `user-reviews.md` — Categorized user feedback with provenance. Each entry: source URL, date, community type, pain point, subsystem mapping.
- `value-signals.md` — Ranked signal list. Each signal: what users want, evidence count, subsystem mapping, signal strength (strong/moderate/weak).

**Gate: Human.** Present the gathered data to the user. The user confirms completeness or directs additional research on specific competitors or topics.

#### Stage 0c: Market Research Synthesis (gpt-high)

Run the market research synthesis agent:

```bash
agents -m gpt-high -p <worktree> -f product-strategy/market\ research\ agent.md
```

**Inputs provided to agent:**
- `market-data/competitors.md`
- `market-data/user-reviews.md`
- `market-data/value-signals.md`
- `proposal.md` (for subsystem structure reference)
- `problem.md` (for problem axis alignment)

**Outputs:**
- `market-research.md` (always written)
- `market-surfaces.md` (only if surfaces found)

#### Stage 0d: Surface Check

Check whether `market-surfaces.md` was produced.

If produced: **pause the roadmap pipeline.** Feed the surfaces into the product strategy alignment workflow:
1. Run the problem alignment review with the surfaces as additional input
2. Follow through expansion, philosophy review, philosophy expansion as needed
3. If the proposer must update `proposal.md`, run the proposer
4. Run alignment to convergence (clean run)
5. Resume the roadmap pipeline at Layer 1 (executive roadmap)

If not produced: proceed to Layer 1.

---

### Layer 1: Executive Roadmap

#### Stage 1a: Executive Roadmap Proposal (gpt-high)

Run the executive roadmap proposer:

```bash
agents -m gpt-high -p <worktree> -f product-strategy/executive\ roadmap\ proposer.md
```

If the proposer fails or produces a roadmap that cannot pass risk after 2 revision cycles, escalate to gpt-xhigh for the next attempt.

**Inputs provided to agent:**
- `proposal.md`
- `problem.md`
- `philosophy.md`
- `market-research.md`

**Outputs:**
- `executive-roadmap.md` (always written)
- `executive-surfaces.md` (only if surfaces found)

#### Stage 1b: Executive Risk Assessment (3x parallel)

Construct three risk assessment prompts from `roadmap-risk-types.md`, section "Executive Roadmap Risks." Each prompt includes:
- The risk type definition, severity criteria, and assessment checklist from `roadmap-risk-types.md`
- The artifact being assessed: `executive-roadmap.md`
- The cross-reference documents specified for that risk type
- The output format from `roadmap-risk-types.md`

Write the constructed prompts to `.tmp/` and run all three in parallel:

```bash
# Create worktrees for parallel execution
git worktree add worktrees/exec-risk-market -b exec-risk-market
git worktree add worktrees/exec-risk-dependency -b exec-risk-dependency
git worktree add worktrees/exec-risk-completeness -b exec-risk-completeness
```

```python
# Run in parallel with one Bash-background dispatch per child per ~/ai/workflows/agents-cli.md
Bash(command="agents -m claude-opus -p worktrees/exec-risk-market -f .tmp/executive-risk-market-misread.md 2>&1 | tee .tmp/executive-risk-market-misread.log", run_in_background=True, description="Run executive market risk review")
Bash(command="agents -m claude-opus -p worktrees/exec-risk-dependency -f .tmp/executive-risk-dependency-trap.md 2>&1 | tee .tmp/executive-risk-dependency-trap.log", run_in_background=True, description="Run executive dependency risk review")
Bash(command="agents -m gpt-high -p worktrees/exec-risk-completeness -f .tmp/executive-risk-completeness.md 2>&1 | tee .tmp/executive-risk-completeness.log", run_in_background=True, description="Run executive completeness risk review")

# After all task notifications arrive, collect outputs to plans/risk/
```

```bash
# Clean up worktrees
```

**Risk types:**
1. **Market misread** (`claude-opus`) — Are value assessments evidence-based?
2. **Dependency trap** (`claude-opus`) — Does the ordering create fragile critical paths?
3. **Completeness** (`gpt-high`) — Are all proposal subsystems covered?

See `roadmap-risk-types.md` for full definitions.

**All three must return LOW.** If any returns MEDIUM or HIGH:

1. Read the findings from all three risk reports
2. Identify the resolution path from `roadmap-risk-types.md` for each non-LOW finding
3. Execute the resolution (may involve additional research, proposer revision, or both)
4. Re-run the **full risk gate** (all three risk types) — do not cherry-pick

#### Stage 1c: Surface Check

Check whether `executive-surfaces.md` was produced by stage 1a.

If produced: pause, run product strategy alignment cycle, resume based on impact (see Resume Rules below).

#### Stage 1d: Human Gate

Present the executive roadmap to the user. Include:
- The initiative ordering with value justification
- The phase structure
- Opportunity cost statements
- Risk assessment verdicts (all LOW)

The user may: approve, reorder initiatives, merge/split slices, reject competitive analysis, or request changes. If changes are substantial, re-run the risk gate on the revised roadmap.

---

### Layer 2: Engineering Roadmap

#### Stage 2a: Engineering Research (gpt-high)

Run the engineering codebase research agent:

```bash
agents -m gpt-high -p <worktree> -f product-strategy/engineering\ research\ agent.md
```

**Inputs provided to agent:**
- `executive-roadmap.md`
- `proposal.md`
- The full codebase (agent reads service code, daemon code, test trees, migrations, etc.)
- `DECISIONS.md`
- Existing research in `plans/research/`

**Outputs:**
- `engineering-research.md` (always written) — Technical landscape report: what exists, what is draft-state, what is production-ready, shared infrastructure needs, technical constraints

#### Stage 2b: Engineering Roadmap Proposal (gpt-high)

Run the engineering roadmap proposer:

```bash
agents -m gpt-high -p <worktree> -f product-strategy/engineering\ roadmap\ proposer.md
```

**Inputs provided to agent:**
- `executive-roadmap.md`
- `engineering-research.md`
- `proposal.md`
- `DECISIONS.md`

**Outputs:**
- `engineering-roadmap.md` (always written)
- `engineering-surfaces.md` (only if surfaces found)

#### Stage 2c: Engineering Risk Assessment (3x parallel)

Same pattern as Stage 1b. Construct three prompts from `roadmap-risk-types.md`, section "Engineering Roadmap Risks."

**Risk types:**
1. **Integration** (`claude-opus`) — Will independently-built slices integrate?
2. **Drift** (`claude-opus`) — Does engineering add/drop/reinterpret executive priorities?
3. **Feasibility** (`gpt-high`) — Are effort estimates realistic?

**Prototype escape hatch for substrate feasibility.** Before accepting a non-LOW feasibility risk as a normal revision loop, check whether the engineering-feasibility report says the foundation substrate cannot be validated by document/code reading alone and needs running-code evidence. Treat either an explicit `PROTOTYPE_NEEDED` line or a HIGH/MEDIUM finding whose resolution path says "validate by building/running/integrating the substrate" as a prototype trigger.

When the trigger fires:

1. Set `roadmap_layer_slug=layer-2-engineering-${short_slug}` from the substrate or foundation-phase name and set `prototype_planning_dir=${planning_dir}/prototypes/${roadmap_layer_slug}`.
2. Compose `${scratch_dir}/prompts/roadmap-${roadmap_layer_slug}-prototype.md` instructing `prototype-orchestrator` to answer the specific feasibility question. Inputs: `prototype_id=${roadmap_layer_slug}`, `question` from the engineering-feasibility risk finding, `repo_root`, `worktree_path=${repo_root}/worktrees/prototype-${roadmap_layer_slug}` or the umbrella equivalent, `planning_dir=${prototype_planning_dir}`, `scratch_dir=${prototype_planning_dir}/.scratch/`, and `roadmap_layer=Layer 2:${planning_dir}/engineering-roadmap.md`.
3. Dispatch exactly one prototype sub-flow invocation: `agents -m claude-opus -a prototype-orchestrator -p ${repo_root}/worktrees/prototype-${roadmap_layer_slug} -f ${scratch_dir}/prompts/roadmap-${roadmap_layer_slug}-prototype.md 2>&1 | tee ${scratch_dir}/logs/roadmap-${roadmap_layer_slug}-prototype.log`.
4. Refuse to pass Stage 2c until `${prototype_planning_dir}/dossier/answer.md` and `${prototype_planning_dir}/dossier/spawned-tickets.md` exist and are non-empty. If the dispatch fails or either dossier artifact is missing, write `${scratch_dir}/questions/q-<uuidv4>.question.json` and halt with `NEEDS_INPUT:<absolute_question_artifact_path>` naming the failed prototype handoff.
5. Compose `${scratch_dir}/prompts/roadmap-${roadmap_layer_slug}-engineering-revision-from-prototype.md` instructing `engineering-roadmap-proposer` to revise `${planning_dir}/engineering-roadmap.md` using `${prototype_planning_dir}/dossier/answer.md`, `${prototype_planning_dir}/dossier/risk-profile.md`, and `${prototype_planning_dir}/dossier/spawned-tickets.md` as validation evidence. Dispatch `agents -m gpt-high -a engineering-roadmap-proposer -p ${worktree} -f ${scratch_dir}/prompts/roadmap-${roadmap_layer_slug}-engineering-revision-from-prototype.md 2>&1 | tee ${scratch_dir}/logs/roadmap-${roadmap_layer_slug}-engineering-revision-from-prototype.log`, then re-run the full Stage 2c risk gate.

**All three must return LOW.** If any is not LOW, follow the resolution path in `roadmap-risk-types.md` and re-run the full gate.

#### Stage 2d: Surface Check

Check whether `engineering-surfaces.md` was produced by stage 2b.

If produced: pause, run product strategy alignment cycle, resume based on impact.

#### Stage 2e: Human Gate

Present the engineering roadmap to the user. Highlight:
- Any pushback on executive ordering (with cost/value tradeoff stated)
- Foundation phase contents (if extracted)
- Effort estimates and risk flags
- Parallelization opportunities

The user resolves any ordering disagreements between executive and engineering perspectives.

---

### Layer 3: AI-Optimized Roadmap

#### Stage 3a: AI Roadmap Proposal (gpt-high)

Run the AI roadmap proposer:

```bash
agents -m gpt-high -p <worktree> -f product-strategy/ai\ roadmap\ proposer.md
```

**Inputs provided to agent:**
- `engineering-roadmap.md`
- `proposal.md`
- The full codebase
- `AGENTS.md` (for implementation workflow patterns)

**Outputs:**
- `ai-roadmap.md` (always written)

#### Stage 3b: AI Risk Assessment (3x parallel)

Same pattern. Construct three prompts from `roadmap-risk-types.md`, section "AI Roadmap Risks."

**Risk types:**
1. **Decomposition** (`claude-opus`) — Are work unit boundaries clean?
2. **Dependency** (`claude-opus`) — Is the dependency graph acyclic?
3. **Coverage** (`gpt-high`) — Is every engineering item decomposed?

**Prototype escape hatch for WU decomposition.** Before accepting a non-LOW decomposition or dependency risk as a normal revision loop, check whether the report says a Work Unit contract, schema, hookpoint, or parallelization boundary cannot be named without trying the implementation. Treat either an explicit `PROTOTYPE_NEEDED` line or a HIGH/MEDIUM finding whose resolution path says "build a prototype to clarify decomposition" as a prototype trigger.

When the trigger fires:

1. Set `roadmap_layer_slug=layer-3-ai-${short_slug}` from the phase or WU name and set `prototype_planning_dir=${planning_dir}/prototypes/${roadmap_layer_slug}`.
2. Compose `${scratch_dir}/prompts/roadmap-${roadmap_layer_slug}-prototype.md` instructing `prototype-orchestrator` to answer the decomposition question. Inputs: `prototype_id=${roadmap_layer_slug}`, `question` from the AI decomposition/dependency risk finding, `repo_root`, `worktree_path=${repo_root}/worktrees/prototype-${roadmap_layer_slug}` or the umbrella equivalent, `planning_dir=${prototype_planning_dir}`, `scratch_dir=${prototype_planning_dir}/.scratch/`, and `roadmap_layer=Layer 3:${planning_dir}/ai-roadmap.md`.
3. Dispatch exactly one prototype sub-flow invocation: `agents -m claude-opus -a prototype-orchestrator -p ${repo_root}/worktrees/prototype-${roadmap_layer_slug} -f ${scratch_dir}/prompts/roadmap-${roadmap_layer_slug}-prototype.md 2>&1 | tee ${scratch_dir}/logs/roadmap-${roadmap_layer_slug}-prototype.log`.
4. Refuse to pass Stage 3b until `${prototype_planning_dir}/dossier/answer.md` and `${prototype_planning_dir}/dossier/spawned-tickets.md` exist and are non-empty. If the dispatch fails or either dossier artifact is missing, write `${scratch_dir}/questions/q-<uuidv4>.question.json` and halt with `NEEDS_INPUT:<absolute_question_artifact_path>` naming the failed prototype handoff.
5. Compose `${scratch_dir}/prompts/roadmap-${roadmap_layer_slug}-ai-revision-from-prototype.md` instructing `ai-roadmap-proposer` to revise `${planning_dir}/ai-roadmap.md` using `${prototype_planning_dir}/dossier/answer.md`, `${prototype_planning_dir}/dossier/risk-profile.md`, and `${prototype_planning_dir}/dossier/spawned-tickets.md` as validation evidence. Dispatch `agents -m gpt-high -a ai-roadmap-proposer -p ${worktree} -f ${scratch_dir}/prompts/roadmap-${roadmap_layer_slug}-ai-revision-from-prototype.md 2>&1 | tee ${scratch_dir}/logs/roadmap-${roadmap_layer_slug}-ai-revision-from-prototype.log`, then re-run the full Stage 3b risk gate.

**All three must return LOW.** If any is not LOW, follow the resolution path and re-run the full gate.

### Stage 3c: Validate AI Roadmap

The orchestrator validates:
- Every engineering roadmap slice appears in the AI roadmap
- The dependency graph is acyclic (topological sort succeeds)
- Model assignments follow `models/roles.md`

No human gate — this is a formatting transformation of the already-approved engineering roadmap.

---

### Layer 4: Ticket Generation

#### Stage 4a: Ticket Generation (gpt-high)

Run the ticket generation agent:

```bash
agents -m gpt-high -p <worktree> -f product-strategy/ticket\ generation\ agent.md
```

**Inputs provided to agent:**
- `ai-roadmap.md`
- `proposal.md`
- `problem.md`
- `philosophy.md`
- `market-research.md`
- `executive-roadmap.md`

**Outputs:**
- `tickets/INDEX.md` (always written)
- `tickets/INIT-NNN.md` (one per initiative)
- `tickets/SLICE-NNN.md` (one per value slice)

#### Stage 4b: Human Gate

Present the generated tickets to the user. Tickets are the final deliverable that feeds into the Implementation & Bug-Fix Workflow from `AGENTS.md`.

---

## Surface Handling

When any proposer agent produces a surfaces file (`market-surfaces.md`, `executive-surfaces.md`, or `engineering-surfaces.md`):

1. **Pause** the roadmap pipeline at the current layer. Record which layer paused and what surfaces triggered the pause.

2. **Run** the product strategy alignment cycle:
   - Feed surfaces into the problem alignment review as additional input
   - Follow through problem expansion, philosophy alignment, philosophy expansion as the alignment orchestrator dictates
   - If the alignment cycle produces changes that require a proposal update, run the proposer
   - Run alignment to convergence (clean run)

3. **Assess impact and resume:**
   - If `proposal.md` was not changed: resume from the paused layer with updated `problem.md`/`philosophy.md`
   - If `proposal.md` was changed: restart from Layer 1 (executive roadmap). Market data does not re-gather unless the problem space fundamentally changed (new subsystems, removed subsystems).
   - If the problem space fundamentally changed (new subsystems added to the proposal, or existing subsystems substantially redesigned): restart from Layer 0 (market research).

4. **User decides** restart scope when the impact is ambiguous. Present the changes and ask: "The problem definition was expanded with [new axes]. The proposal was [changed/unchanged]. Which layer should we restart from?"

5. **Delete** the surfaces file after processing.

---

## Resume Rules After Product Strategy Detour

| Change scope | Resume point | Rationale |
|---|---|---|
| New problem axes, proposal unchanged | Paused layer | The strategic ordering is still valid |
| Proposal updated (minor) | Layer 1 (executive) | Strategic value assessment may change |
| Proposal updated (new subsystem) | Layer 0 (market research) | Need competitive data for new scope |
| Philosophy updated, proposal unchanged | Paused layer | Ordering is strategic, not philosophical |

Layers prior to the resume point do NOT re-run automatically. The user confirms whether earlier outputs need revision.

---

## Risk Resolution Protocol

When a risk assessment returns MEDIUM or HIGH at any layer:

1. **Read all three risk reports** for that layer, not just the non-LOW one.
2. **Identify the resolution path** for each non-LOW finding from `roadmap-risk-types.md`.
3. **Execute resolutions** in order:
   - If resolution requires additional research: dispatch a gpt-high research agent with a focused prompt (the agent uses Firecrawl for web research or reads the codebase as appropriate)
   - If resolution requires proposal revision: run the proposer with the risk findings as additional input (append risk findings to the prompt)
4. **Re-run the full risk gate** — all three risk types, not just the ones that were non-LOW. Revisions can introduce new issues.
5. **Iterate until risk is all-LOW or the operator halts.** The loop is not count-bounded. If the operator wants to accept residual risk, provide additional direction, or abandon the layer, that decision is surfaced via `NEEDS_INPUT`, not forced by an iteration count.

---

## NEEDS_INPUT Handling

For roadmap human gates, unresolved risk-direction questions, and other human-owned value/scope/trade-off questions, direct `AskUserQuestion` permission-denial follows `~/ai/conventions/agent-questions-and-session-graph.md` § `AskUserQuestion Permission-Denial`: return `NEEDS_INPUT:<absolute_artifact_path>` with the question artifact and halt before dependent roadmap work. Procedural permission-denial or procedural NEEDS_INPUT that the roadmap orchestrator can resolve from supplied inputs stays inline.

---

## Run Report

After each layer completes (all risk gates LOW, human/model gate passed), produce a brief status report:

```
Layer N: [name]
  Proposer: [model] — [output file]
  Risk gate: [all LOW / required N revision cycles]
  Surfaces: [none / found and processed]
  Human gate: [approved / approved with changes]
  Next: Layer N+1
```

After all layers complete, produce a final summary listing all output files and the dependency path from market research through tickets.
