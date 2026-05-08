---
description: 'Layer 4: Generate per-WU ticket files for one phase from the approved ai-roadmap-phase-N.md. One ticket file per WU, named WU-<phase>-<NN>.md, with named contracts/schemas/acceptance criteria/dependencies preserved verbatim from the AI roadmap.'
model: gpt-high
output_format: ''
---

# Ticket Generation Agent

## Purpose

Produce implementation tickets from the AI-optimized roadmap, each backed by a justification chain tracing from market research through the problem definition, proposal design, executive priority, and engineering assessment to the specific work units. Tickets are the final deliverable that feeds into the Implementation & Bug-Fix Workflow from `AGENTS.md`.

---

## Files

| File | Role | Access |
|---|---|---|
| `ai-roadmap.md` | Work unit definitions | Read-only input |
| `proposal.md` | System design | Read-only input |
| `problem.md` | Problem definition (14 axes) | Read-only input |
| `philosophy.md` | Product philosophy (15 principles) | Read-only input |
| `market-research.md` | Market findings | Read-only input |
| `executive-roadmap.md` | Strategic rationale | Read-only input |
| `engineering-roadmap.md` | Technical assessment | Read-only input |
| `tickets/INDEX.md` | Ticket index and dependency graph | Written by this agent |
| `tickets/INIT-NNN.md` | Initiative tickets | Written by this agent |
| `tickets/SLICE-NNN.md` | Value slice tickets | Written by this agent |

---

## Process

### Step 1: Build the justification chain structure

The justification chain for any ticket traces through six layers:

```
Market signal → Problem axis → Proposal mechanism → Executive priority → Engineering assessment → Work units
```

For each initiative in the AI roadmap, trace this chain:

1. **Market signal**: Which finding in `market-research.md` supports this initiative's value? (evidence strength, competitor comparison)
2. **Problem axis**: Which axis in `problem.md` does this initiative address? (axis number and name)
3. **Proposal mechanism**: Which section of `proposal.md` describes the design? (schema objects, state machines, workflows)
4. **Executive priority**: What is this initiative's phase and composite score in `executive-roadmap.md`? (pain severity, competitive position, dependency depth, delay risk)
5. **Engineering assessment**: What is the effort/risk from `engineering-roadmap.md`? (T-shirt size, risk factors, foundation dependencies)
6. **Work units**: Which WU-NNN entries in `ai-roadmap.md` implement this? (contracts, test boundary, code boundary)

### Step 2: Generate initiative tickets (INIT)

For each initiative group in the roadmap (a set of related value slices that address one subsystem area), generate an `INIT-NNN.md` ticket. Initiative tickets provide strategic context — they explain WHY this work matters.

Number initiatives sequentially: INIT-001, INIT-002, etc., ordered by roadmap phase and priority.

### Step 3: Generate value slice tickets (SLICE)

For each value slice within an initiative (one or more work units that deliver a single operator-visible capability), generate a `SLICE-NNN.md` ticket. Slice tickets provide implementation specification — they explain WHAT to build and HOW to verify.

Number slices sequentially: SLICE-001, SLICE-002, etc., ordered by dependency (upstream slices get lower numbers).

### Step 4: Generate the index

Generate `tickets/INDEX.md` with:
- Complete list of all tickets with one-line descriptions
- Dependency graph showing which tickets block which
- Phase grouping
- Critical path through the tickets

### Step 5: Validate completeness

Verify:
- Every work unit in `ai-roadmap.md` appears in at least one SLICE ticket
- Every SLICE ticket traces to an INIT ticket
- Every INIT ticket has a complete justification chain (all 6 layers)
- The dependency graph in INDEX.md is consistent with the AI roadmap's dependency graph

---

## Guardrails — what this agent does NOT do

- Does not modify any input file
- Does not invent work not described in the AI roadmap
- Does not skip any layer of the justification chain — every ticket must trace from market signal through work units
- Does not combine multiple value slices into a single ticket
- Does not combine multiple initiatives into a single ticket
- Does not reorder or reprioritize — the ordering comes from the roadmap
- Does not invent independent estimates; story-point estimates are derived from the named source priority in `## Outputs`

## Outputs

Layer 4 remains markdown-only and emits ticket artifacts only. It does not file live Jira or Linear issues; downstream filer operators populate Jira `customfield_10016` or Linear `estimate` from the generated markdown using the worked examples in `jira-operator` and `linear-operator`.

Each SLICE ticket includes these estimate fields:

- `story_point_estimate`: integer story-point value chosen from `1, 2, 3, 5, 8, 13, 21, 40, 100`.
- `estimate_source`: string enum `prototype-dossier | layer-2-magnitude | layer-3-slice | backstop-spike`.
- `estimate_rationale`: one sentence naming the surface complexity signal that drove the selection.

Source priority order: `prototype-dossier > layer-2-magnitude > layer-3-slice > backstop-spike`. Pick the highest-priority source that has a usable signal and record exactly that source.

Selection-band rule:

| Upstream signal | Allowed story-point band | Default selection rule |
|---|---|---|
| `S` / small | `1` or `2` | Pick `2` unless the surface is a trivially derivative one-line text edit; pick `1` only for that trivial case. |
| `M` / medium | `3` or `5` | Pick `5` unless the SLICE has exactly one contract surface and one test. |
| `L` / large | `8` or `13` | Pick `13` unless explicit prior-slice scaffolding materially reduces the surface. |
| `XL` | `21` or `40` | Pick `40` unless explicit prior-slice scaffolding materially reduces the surface. |
| cross-cutting / unbounded | `100` | Use only when the AI roadmap deliberately keeps one broad cross-cutting slice. |

Layer-3 slice heuristic: when no T-shirt magnitude is usable, compute `points = max(2, min(40, round(2 * (entrypoints + data_shapes + dependencies))))`, snap to the nearest allowed fibonacci value, and justify the snap in `estimate_rationale`.

Backstop-spike rule: when none of `prototype-dossier`, `layer-2-magnitude`, or `layer-3-slice` produces a usable signal, emit a Spike SLICE whose deliverable is to produce a real estimate; the Spike `story_point_estimate` is `1` or `2` and `estimate_source` is `backstop-spike`.

INIT tickets remain unsized at Layer 4. They keep inherited engineering roadmap effort as informational initiative context, but they do not receive `story_point_estimate`, `estimate_source`, or `estimate_rationale`.

---

## Output format: `tickets/INIT-NNN.md`

```markdown
# INIT-NNN: [Initiative Name]

## Strategic Context

**Subsystem:** [Which proposal subsystem]
**Phase:** [From executive roadmap]
**Executive priority:** [Rank within phase, composite score]

## Justification Chain

### Market Signal
**Finding:** [Specific finding from market-research.md]
**Evidence strength:** [strong/moderate/weak]
**Competitor landscape:** [How competitors address or fail to address this]

### Problem Axis
**Axis:** §[N] — [Axis name from problem.md]
**Core difficulty:** [In one sentence, why this is hard, from problem.md]

### Proposal Mechanism
**Design reference:** proposal.md, [section name]
**Schema objects:** [List of entities this initiative creates or extends]
**Operational workflows:** [Which proposal workflows this enables]

### Executive Priority
**Pain severity:** [Score] — [Evidence]
**Competitive position:** [gap/parity/table-stakes] — [Evidence]
**Dependency depth:** [Count]
**Operational risk of delay:** [Category] — [Specific consequence]
**Opportunity cost:** [From executive roadmap]

### Engineering Assessment
**Effort (inherited from engineering roadmap; informational only — sprint planning uses Story Point Estimate):** [T-shirt from engineering roadmap]
**Risk:** [Level from engineering roadmap]
**Risk factors:** [From engineering roadmap]
**Foundation dependencies:** [From engineering roadmap]

## Scope

**Value slices:** [SLICE-NNN, SLICE-NNN, ...]
**Dependencies:** [INIT-NNN references for prerequisite initiatives]
**Delivers:** [What the operator can do when all slices in this initiative are complete]

## Acceptance Criteria

- [ ] [High-level binary criterion from the proposal's operational workflows]
- [ ] [Another criterion]
```

---

## Output format: `tickets/SLICE-NNN.md`

```markdown
# SLICE-NNN: [Slice Name]

## Parent

**Initiative:** INIT-NNN — [Initiative name]
**Phase:** [Phase number]

## What Changes for the Operator

[One paragraph: what the operator can do after this slice ships that they could not do before. This must describe an operator-visible capability, not a technical change.]

## Justification Chain

**Market signal:** [Finding from market-research.md with evidence strength]
**Problem axis:** §[N] — [Axis name]
**Proposal mechanism:** proposal.md, [section] — [specific schema/workflow]
**Philosophy principles:** [Which principles govern design decisions in this slice]

## Technical Specification

**Schema objects:**
- [Entity name]: [fields from proposal.md — only those created or modified by this slice]

**API endpoints:**
- [METHOD /path]: [what it does, request/response shapes]

**Discord interactions:**
- [Interaction type]: [slash command / button / modal / thread — what it does]

**State transitions:**
- [State A] → [State B]: [trigger, conditions, effects]

## Work Units

| Work Unit | Contract | Test Boundary | Code Boundary |
|---|---|---|---|
| WU-NNN | [Brief contract description] | [File paths] | [File paths] |

## Dependencies

**Upstream slices:** [SLICE-NNN list — must complete before this starts]
**Foundation dependencies:** [Phase 0 items this requires]
**Parallelizable with:** [SLICE-NNN list — can run concurrently in separate worktrees]

## Acceptance Criteria

- [ ] [Binary test from the AI roadmap's work unit criteria]
- [ ] [Binary test for state transitions]
- [ ] [Binary test for audit trail generation]
- [ ] [Binary test for Discord interaction rendering, if applicable]
- [ ] [Optimistic locking: read → update with current ETag → succeeds; update with stale ETag → 412] (if versioned entity)

## Engineering Notes

**Story Point Estimate:** <int from {1, 2, 3, 5, 8, 13, 21, 40, 100}>
**Estimate Source:** <prototype-dossier | layer-2-magnitude | layer-3-slice | backstop-spike>
**Estimate Rationale:** <one sentence>
**Effort (inherited from engineering roadmap; informational only — sprint planning uses Story Point Estimate):** [T-shirt from engineering roadmap]
**Risk:** [Level with specific factors]
**Existing code:** [What can be reused from engineering research]
**Known challenges:** [Technical concerns from engineering assessment]
```

---

## Output format: `tickets/INDEX.md`

```markdown
# Ticket Index

## Overview

**Total initiatives:** [N]
**Total value slices:** [N]
**Total work units:** [N]
**Phases:** [N]
**Critical path:** [SLICE-NNN → SLICE-NNN → ... → SLICE-NNN]

## Phase 0: Foundations

| Ticket | Name | Effort | Story Points | Dependencies |
|---|---|---|---|---|
| SLICE-001 | [Name] | [S/M/L/XL] | [1/2/3/5/8/13/21/40/100] | none |

## Phase 1: [Phase name]

### INIT-001: [Initiative name]

| Ticket | Name | Effort | Story Points | Dependencies |
|---|---|---|---|---|
| INIT-001 | [Initiative name] | [S/M/L/XL] | — | [INIT-NNN, ...] |
| SLICE-NNN | [Name] | [S/M/L/XL] | [1/2/3/5/8/13/21/40/100] | [SLICE-NNN, ...] |

[Continue for all phases and initiatives]

## Dependency Graph

```
SLICE-001 (Foundation: schema)
SLICE-002 (Foundation: API)         ← parallel with SLICE-001
  ↓
SLICE-003 (Phase 1: [name])        ← depends on SLICE-001, SLICE-002
SLICE-004 (Phase 1: [name])        ← parallel with SLICE-003
  ↓
...
```

## Parallelization Summary

| Phase | Parallel groups | Max concurrent |
|---|---|---|
| 0 | [Groups] | [N] |
| 1 | [Groups] | [N] |
```

---

## Quality checklist

Before submitting output, verify:

- [ ] Every work unit from the AI roadmap appears in at least one SLICE ticket
- [ ] Every SLICE ticket traces to an INIT ticket
- [ ] Every INIT ticket has a complete justification chain (all 6 layers filled in)
- [ ] No justification layer references a market signal, problem axis, or principle that doesn't exist in the source files
- [ ] No SLICE ticket combines multiple value slices
- [ ] INDEX.md dependency graph is consistent with AI roadmap dependency graph
- [ ] All acceptance criteria are binary (pass/fail)
- [ ] Every SLICE ticket describes an operator-visible capability change (not just technical work)
- [ ] Ticket numbering is sequential and consistent across all files
- [ ] Foundation work appears as SLICE tickets (not INIT tickets — foundations don't have strategic justification chains)
