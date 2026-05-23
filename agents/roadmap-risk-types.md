# Roadmap Risk Types

Risk type definitions for the roadmap workflow. Each risk type is specific to the failure modes of its layer. The orchestrator constructs risk assessment prompts by combining a risk type definition from this file with the artifact being assessed and its cross-reference documents.

Risk assessments follow the per-risk model assignments in `workflows/roadmap.md` and use the same structure as implementation risk assessments in `plans/risk/`. Three risk agents run in parallel per layer. All must return LOW for the layer to pass.

---

## Risk Assessment Output Format

Risk assessment reports are written to `plans/risk/` with the naming convention `[layer]-[risk-type].md`:

| Layer | Risk Type | Output File |
|---|---|---|
| Executive | Market misread | `plans/risk/executive-market-misread.md` |
| Executive | Dependency trap | `plans/risk/executive-dependency-trap.md` |
| Executive | Completeness | `plans/risk/executive-completeness.md` |
| Engineering | Feasibility | `plans/risk/engineering-feasibility.md` |
| Engineering | Integration | `plans/risk/engineering-integration.md` |
| Engineering | Drift | `plans/risk/engineering-drift.md` |
| AI | Decomposition | `plans/risk/ai-decomposition.md` |
| AI | Coverage | `plans/risk/ai-coverage.md` |
| AI | Dependency | `plans/risk/ai-dependency.md` |

Every risk assessment must produce a report with this structure:

```
# [Layer] — [Risk Type] Risk Assessment

**Rating: [LOW / MEDIUM / HIGH]**

## Findings

### F-N. [Finding title]

**Severity: [LOW / MEDIUM / HIGH / NONE / INFO]**

[Description of the finding with specific evidence citations.]

**Recommendation:** [Concrete action to resolve, or "no action required."]

---

## Summary table

| ID | Finding | Severity |
|----|---------|----------|

## What LOW requires

[Conditions that must hold for the LOW rating to remain valid. Each condition is a concrete, verifiable statement.]
```

---

## Executive Roadmap Risks

These risks assess strategic ordering decisions. They catch failure modes in value assessment, dependency analysis, and subsystem coverage. The artifact being assessed is `executive-roadmap.md`.

### 1. Market Misread Risk

**What it catches:** Value assessments based on misinterpreted market data, inflated opportunity costs, unsupported competitive positioning claims, value-ordering decisions that don't follow from the evidence.

**Cross-references:**
- `market-research.md` (synthesized findings)
- `market-data/competitors.md` (raw competitor data)
- `market-data/user-reviews.md` (raw user feedback)
- `market-data/value-signals.md` (raw value signals)
- `problem.md` (problem axes)

**Assessment process:**

1. For each initiative in the executive roadmap, trace its pain severity score back to `market-research.md`. Verify:
   - The cited market finding exists in `market-research.md`
   - The evidence strength classification in `market-research.md` matches the raw data in `market-data/`
   - The pain severity score is proportionate to the evidence strength (a "strong" signal should not produce a low score; a "weak" signal should not produce a high score)

2. For each competitive position claim (gap / parity / table-stakes), verify:
   - The competitor comparison cites specific competitors from `market-data/competitors.md`
   - The feature comparison is accurate (the competitor actually lacks/has the claimed capability)
   - The position classification follows from the comparison (if three competitors offer this, it is not a "gap")

3. For each opportunity cost statement, verify:
   - The stated operational consequence traces to a specific problem axis in `problem.md`
   - The consequence is specific, not vague ("officers spend 2 hours daily on manual tracking" not "this is a pain point")
   - The severity assessment is proportionate to the evidence

4. Check for ordering distortion: would a different reading of the same market data produce a materially different ordering? If yes, identify which claims are load-bearing and whether they are well-supported.

**Severity criteria:**
- **LOW:** All value claims trace to evidence. Strength classifications match raw data. Opportunity costs cite specific consequences. No ordering distortion from alternative readings.
- **MEDIUM:** Some value claims lack evidence or overstate market signal strength. Some opportunity costs are vague. Alternative reading of data could change ordering of 1-2 initiatives.
- **HIGH:** Ordering depends on value claims contradicted by market data, or multiple initiatives have unsupported competitive claims.

**Resolution when not LOW:**
1. Identify the specific claims that are unsupported or overstated
2. If the issue is insufficient market data: orchestrator commissions targeted web research on the specific area, re-runs market research synthesis with the new data
3. If the issue is misinterpretation: re-run the executive proposer with the risk findings appended to the prompt, instructing it to revise the specific claims
4. Re-run the full executive risk gate (all three types)

---

### 2. Dependency Trap Risk

**What it catches:** Ordering that creates fragile critical paths, single points of failure in the dependency graph, value-dependency inversions where high-value items are blocked by low-value foundations without justification.

**Cross-references:**
- `executive-roadmap.md` (being assessed)
- `proposal.md` (architectural dependencies between subsystems)
- `problem.md` (which problems are most urgent)

**Assessment process:**

1. Extract the dependency graph from the executive roadmap. For each initiative, list its declared upstream dependencies.

2. Compute the critical path — the longest dependency chain from the first initiative to the last. Assess:
   - Is the critical path length reasonable relative to the total number of initiatives?
   - Are there single-point-of-failure nodes where one delayed initiative blocks 3+ downstream initiatives?
   - Could the critical path be shortened by reordering or redrawing slice boundaries?

3. Identify value-dependency inversions: cases where a high-value initiative (top third of pain severity scores) is blocked by a low-value initiative (bottom third). For each inversion:
   - Is the dependency genuine (the high-value item truly cannot function without the low-value one)?
   - Could the high-value item be partially delivered without the blocker?
   - Is the inversion acknowledged in the roadmap with rationale?

4. Check for hidden dependencies: cases where two initiatives share proposal schema objects or workflow state but the dependency is not declared.

5. Verify that phases group logically — initiatives within a phase should not have ordering dependencies on each other. If initiative A within Phase 2 depends on initiative B within Phase 2, one should be in an earlier phase or the dependency should be removed.

**Severity criteria:**
- **LOW:** Critical path is reasonable. No single initiative blocks more than 2 downstream. Value-dependency inversions are acknowledged with rationale or can be justified by genuine architectural dependency. No hidden dependencies detected. Phases group correctly.
- **MEDIUM:** Critical path has a fragile bottleneck (one initiative blocking 3+ downstream). Value-dependency inversions exist without justification. A hidden dependency is detected.
- **HIGH:** Dependency graph contains cycles. An initiative depends on itself (circular). Or the ordering is physically impossible (A requires B which requires A).

**Resolution when not LOW:**
1. Present the dependency analysis to the executive proposer as additional input
2. The proposer revises: may redraw slice boundaries to break bottlenecks, reorder phases to eliminate inversions, or declare hidden dependencies explicitly
3. Re-run the full executive risk gate

---

### 3. Completeness Risk

**What it catches:** Proposal subsystems silently missing from the roadmap, value slices that don't deliver standalone operator capability, scope dropped without rationale.

**Cross-references:**
- `executive-roadmap.md` (being assessed)
- `proposal.md` (all 7 subsystems + 4 cross-cutting concerns)
- `problem.md` (all 14 problem axes)

**Assessment process:**

1. List the 7 proposal subsystems: Identity/Trust, Intake/Adjudication, Case Management, Sub-community Lifecycle (chapters), Activity/Compliance, Permission Management, Governance. Plus the 4 cross-cutting concerns: Cross-workflow State Coherence, Platform Boundary, Graceful Degradation, Data Portability.

2. For each subsystem, verify it appears in at least one initiative in the executive roadmap. If missing, check whether the roadmap explicitly defers it with rationale.

3. For each cross-cutting concern, verify it is addressed — either as its own initiative, as a component of a foundation phase, or as a documented constraint that each initiative handles locally.

4. For each value slice, apply the standalone-value test: "After this slice ships, can an operator do something they could not do before?" If the answer is no (the slice is purely technical infrastructure with no operator-visible effect), it should be in a foundation phase, not presented as a value slice.

5. For deferred subsystems, verify the deferral rationale is specific — "deferred because [concrete reason]" not "deferred to a later phase."

6. Check that the problem axes are addressed: for each of the 14 axes in `problem.md`, verify that at least one initiative addresses it. An axis may be addressed indirectly (the initiative solves the problem even though it's named after a different subsystem).

**Severity criteria:**
- **LOW:** All 7 subsystems are covered or explicitly deferred with specific rationale. All value slices deliver standalone operator capability. All 14 problem axes are addressed by at least one initiative. Cross-cutting concerns are handled.
- **MEDIUM:** A subsystem is missing without rationale. A value slice doesn't deliver standalone operator capability. A problem axis is unaddressed. A cross-cutting concern is ignored.
- **HIGH:** Multiple subsystems are silently dropped. Multiple problem axes are unaddressed.

**Resolution when not LOW:**
1. Present the completeness analysis to the executive proposer
2. The proposer adds missing subsystems, redraws slice boundaries for standalone value, or provides explicit deferral rationale
3. Re-run the full executive risk gate

---

## Engineering Roadmap Risks

These risks assess STRATEGIC technical ordering at the roadmap level. They do NOT audit detailed engineering specs — those are produced per-slice by the AGENTS.md implementation pipeline (research → proposal → risk → hookpoints). The roadmap commits to magnitude and sequencing, not per-slice effort estimates or detailed ownership boundaries.

The workflow is iterative: strategic roadmap → prototyping (discovers surface area and refines magnitudes) → updated roadmap → implementation. Early-cycle roadmaps are expected to be magnitude-level, not spec-level. The artifact being assessed is `engineering-roadmap.md`.

### 1. Strategic Feasibility Risk

**What it catches:** Fundamentally infeasible sequencing, phase magnitudes that are wrong by an order of magnitude, technical approaches that conflict with locked decisions in `DECISIONS.md`.

**What it does NOT catch:** Per-slice T-shirt sizes being off by one tier (that is implementation-phase detail), specific ownership splits (implementation-phase detail), effort-buffer percentages (scheduling detail that belongs to operations).

**Cross-references:**
- `engineering-roadmap.md` (being assessed)
- `engineering-research.md` (codebase analysis)
- `DECISIONS.md` (locked decisions)
- `proposal.md` (design assumptions)

**Assessment process:**

1. **Phase-level magnitude check.** For each phase, is the overall magnitude roughly right?
   - Phase 0 should be substantial (foundation work across many domains)
   - Later phases deliver value slices; magnitude grows with slice count and dependency depth
   - A phase claimed as small but containing many XL items is magnitude-off
   - A phase claimed as large but containing only trivial work is also magnitude-off

2. **Sequencing feasibility.** Is the phase ordering technically possible?
   - Does each phase have access to the foundations it requires?
   - Do Phase N slices claim dependencies that can only be satisfied in Phase N+K?
   - Is Phase 0 foundation list sufficient to support Phase 1 without hidden gaps?

3. **Locked-decision consistency.** Do the roadmap's technical approaches conflict with anything in `DECISIONS.md`?
   - If DECISIONS.md is silent on a choice (e.g., hosting target), the roadmap can propose one, but not treat it as locked
   - If DECISIONS.md has a locked decision (e.g., no SQLite for the canonical data store), the roadmap must not contradict it

4. **Magnitude indicators expected.** The roadmap should include SOME magnitude signal — phase-level indicators are sufficient. Per-slice T-shirt sizes are NOT required at roadmap level; they are outputs of prototyping and implementation-phase proposals.

**Severity criteria:**
- **LOW:** Phase magnitudes are reasonable. Sequencing is technically possible. No conflicts with locked decisions. Roadmap includes at least phase-level magnitude signals.
- **MEDIUM:** A phase magnitude is off by an order of magnitude, OR sequencing has a significant hidden gap, OR a locked decision is contradicted.
- **HIGH:** The overall sequencing is technically impossible, OR multiple locked decisions are contradicted.

**What NOT to flag as MEDIUM or HIGH:**
- Per-slice T-shirt sizes that seem slightly small (magnitude-level review only)
- Missing per-slice effort estimates (not required at roadmap level)
- Absent per-slice ownership splits (implementation-phase detail)
- Schedule buffer percentages (operations detail)

**Resolution when not LOW:**
1. For sequencing gaps: the engineering proposer explicitly adds the missing foundation item or restructures the phase boundary
2. For locked-decision conflicts: the proposer removes the conflict OR the user adds a new locked decision via DECISIONS.md
3. For wrong phase magnitudes: the proposer adds a phase-level note acknowledging the actual magnitude
4. Re-run the full engineering risk gate

---

### 2. Strategic Integration Risk

**What it catches:** Unacknowledged cross-slice dependencies that would break sequencing, missing foundation ownership at the phase level, structurally impossible parallelization.

**What it does NOT catch:** Detailed contract signatures, per-table ownership splits between Phase 0 and a specific slice, Pydantic schema design (all implementation-phase detail).

**Cross-references:**
- `engineering-roadmap.md` (being assessed)
- `proposal.md` (architectural relationships)
- `engineering-research.md` (existing state)

**Assessment process:**

1. **Cross-slice dependency acknowledgment.** The proposal defines many aggregates and workflows that span slices. The roadmap does not need to specify contracts, but it must ACKNOWLEDGE known dependencies.
   - When slice A's proposal scope requires capability defined in slice B, is that dependency visible in the roadmap's sequencing or phase boundary?
   - Are known-high-fanout items (e.g., a subsystem consumed by many others) called out as strategic risks, not buried?

2. **Phase-level foundation completeness.** Does Phase 0 cover the capabilities that multiple later slices need?
   - If a capability is needed by 2+ later slices, the roadmap should either place it in Phase 0 foundation or explicitly assign it to an earlier slice that other slices depend on
   - The exact implementation split (table ownership vs service ownership) is an implementation-phase concern, NOT a roadmap-level concern

3. **Structural parallelization.** The roadmap may claim some within-phase parallelization. At the strategic level, check for obvious structural conflicts:
   - Two slices that BOTH own the same named capability (e.g., both own "chapter lifecycle") are not parallel
   - Slices at different phase depths cannot be parallel across that boundary
   - Detailed schema/fixture conflicts are implementation-phase concerns, NOT flagged here

**Severity criteria:**
- **LOW:** All major cross-slice dependencies from the proposal are acknowledged somewhere in the roadmap. Phase 0 covers known shared foundations. No structural parallelization impossibility.
- **MEDIUM:** A major cross-slice dependency is missing from the roadmap sequencing. Phase 0 lacks a foundation needed by 2+ slices without justification. One parallelization claim is structurally impossible.
- **HIGH:** Multiple major dependencies are unacknowledged, OR phase sequencing has an impossible ordering (slice B in Phase N requires slice A in Phase N+1).

**What NOT to flag as MEDIUM or HIGH:**
- Undefined contract signatures (implementation-phase detail)
- Undefined per-table ownership splits (implementation-phase detail)
- Test fixture collision risk (implementation-phase detail)
- Exact Pydantic model field sets (implementation-phase detail)

**Resolution when not LOW:**
1. For missing dependency acknowledgments: the proposer adds them to the sequencing or phase notes
2. For missing Phase 0 foundations: the proposer adds the capability to Phase 0 deliverables list
3. For impossible parallelization: the proposer reorders or removes the parallel claim
4. Re-run the full engineering risk gate

---

### 3. Drift Risk

**What it catches:** Engineering roadmap that adds features beyond the executive scope, drops executive priorities, or reinterprets scope beyond justified pushback.

**Cross-references:**
- `engineering-roadmap.md` (being assessed)
- `executive-roadmap.md` (the approved strategic ordering)

**Assessment process:**

1. Map every initiative in the executive roadmap to its counterpart in the engineering roadmap. For each executive initiative, one of:
   - **Present**: the initiative appears with the same scope
   - **Reordered**: the initiative appears but in a different position — classify as pushback
   - **Split**: the initiative is decomposed into smaller pieces — verify all pieces cover the original scope
   - **Merged**: the initiative is combined with another — verify the original scope is preserved
   - **Missing**: the initiative does not appear — flag as drift

2. For each engineering deviation from executive ordering (pushback), verify:
   - The pushback states the implementation cost of following executive ordering (in concrete terms: hours, complexity, technical risk)
   - The pushback states the value lost by engineering ordering (what users don't get as soon)
   - The tradeoff is framed as "executive ordering costs X because Y" — never as "executive ordering is wrong"

3. Check for scope additions: does the engineering roadmap include work not present in the executive roadmap?
   - Technical foundations (schema, infrastructure, test framework) are expected additions — they're not in the executive roadmap because they're not operator-visible
   - New features or capabilities not in the executive roadmap are drift

4. Check for scope reductions: does the engineering roadmap quietly reduce the scope of any initiative?
   - Reduced scope must be flagged as pushback with justification, not silently omitted

**Severity criteria:**
- **LOW:** Every executive initiative is present (possibly reordered/split/merged). Pushback items have cost/value justification. No unauthorized scope additions or reductions.
- **MEDIUM:** Some deviations lack cost/value justification. Scope additions exist that aren't technical foundations. An initiative is slightly narrowed without flagging.
- **HIGH:** Executive initiatives are silently dropped. New features are added without authorization. Multiple initiatives are substantially reinterpreted.

**Resolution when not LOW:**
1. Run the engineering proposer with the drift findings
2. The proposer restores missing initiatives, removes unauthorized additions, or provides proper pushback justification
3. Re-run the full engineering risk gate

---

## AI Roadmap Risks

These risks assess agent-executable decomposition quality. They catch failure modes in work unit boundaries, coverage completeness, and dependency graph structure. The artifact being assessed is `ai-roadmap.md`.

### 1. Decomposition Risk

**What it catches:** Work units that span multiple concerns, unclear contract boundaries, test/code agent separation that isn't achievable.

**Cross-references:**
- `ai-roadmap.md` (being assessed)
- `AGENTS.md` (implementation pipeline rules, especially test/code agent separation and PR review rules)
- `proposal.md` (for contract definitions — Pydantic schemas, endpoints)

**Assessment process:**

1. For each work unit, apply the single-concern test: "Can this work unit be described in one sentence as 'add [one thing]' or 'implement [one behavior]'?" If it requires "and" to describe, it spans multiple concerns.

2. For each work unit's contract definition, verify:
   - Contracts are concrete: Pydantic model names, endpoint path + method, or command signature
   - Contracts are not prose descriptions ("implement the trust system")
   - The test agent can write tests from the contract alone, without seeing the implementation

3. For each work unit, verify the test/code separation is achievable:
   - Test boundary includes only contracts, not service/repository/infrastructure code
   - Code boundary includes everything the code agent needs to make tests pass
   - No circular dependency between test boundary and code boundary

4. Check that work units follow the "single concern per PR" rule: if a work unit were submitted as a PR, would the PR review (multi-concern check from `AGENTS.md`) say it should be split?

**Severity criteria:**
- **LOW:** All work units have single concerns with concrete contracts. Test/code separation is clean. Each work unit maps to a single PR.
- **MEDIUM:** Some work units bundle 2 related concerns. Some contracts are vague. Test/code separation requires seeing implementation details.
- **HIGH:** Work units are broad enough to require multiple PRs. Contracts are prose. Test boundaries include implementation code.

**Resolution when not LOW:**
1. Run the AI proposer with the decomposition findings
2. The proposer splits multi-concern work units, concretizes vague contracts, redraws test/code boundaries
3. Re-run the full AI risk gate

---

### 2. Coverage Risk

**What it catches:** Engineering roadmap items not fully decomposed, missing work units, acceptance criteria that aren't binary.

**Cross-references:**
- `ai-roadmap.md` (being assessed)
- `engineering-roadmap.md` (the source that must be fully decomposed)

**Assessment process:**

1. Map every initiative and slice in the engineering roadmap to work units in the AI roadmap. For each engineering item:
   - Count the work units that reference it as parent
   - Verify the work units collectively cover the full scope of the engineering item
   - Identify any aspects of the engineering item not covered by any work unit

2. For each work unit's acceptance criteria, verify:
   - Each criterion is binary (pass/fail), not subjective ("the code is clean")
   - Criteria are testable — an automated test or manual verification can determine pass/fail
   - Criteria cover the work unit's contract (not just happy path)

3. Check for orphan work units: work units not traceable to any engineering roadmap item.

**Severity criteria:**
- **LOW:** Complete coverage. Every engineering item is fully decomposed. All criteria are binary and testable. No orphans.
- **MEDIUM:** Minor gaps — an aspect of an engineering item is uncovered. Some criteria are subjective.
- **HIGH:** Entire engineering slices are missing. Multiple work units lack testable criteria.

**Resolution when not LOW:**
1. Run the AI proposer with the coverage gap list
2. The proposer adds missing work units and rewrites subjective criteria as binary tests
3. Re-run the full AI risk gate

---

### 3. Dependency Risk

**What it catches:** Circular dependencies between work units, missing dependency edges, false parallelization claims, contract mismatches between connected work units.

**Cross-references:**
- `ai-roadmap.md` (being assessed)
- `engineering-roadmap.md` (for cross-checking dependency structure)

**Assessment process:**

1. Extract the work unit dependency graph. Perform a topological sort. If the sort fails, identify the cycle(s).

2. For each dependency edge (WU-A → WU-B, meaning B depends on A):
   - Verify A's output contract includes what B's input contract requires
   - Verify the contract types match (if A outputs a Pydantic model, B's input should reference the same model)
   - Verify A is in an earlier phase or the same phase but not parallelizable with B

3. For work units marked as parallelizable:
   - Verify no dependency edge exists between them (direct or transitive)
   - Verify they don't share output files (parallel writes to the same file are dangerous)
   - Verify their test suites don't share mutable fixtures

4. Compare the AI roadmap dependency structure against the engineering roadmap structure. Major structural differences should be justified (the AI decomposition may introduce internal dependencies within an engineering slice, but should not contradict cross-slice dependencies).

**Severity criteria:**
- **LOW:** Graph is acyclic. Contracts match across dependency edges. Parallelization claims are valid. Structure is consistent with engineering roadmap.
- **MEDIUM:** Missing dependency edges (B needs A but doesn't declare it). Contract types are compatible but not exact. A parallelization claim is questionable.
- **HIGH:** Dependency cycles exist. Contract mismatches would cause runtime failures. Parallelizable work units have direct dependencies.

**Resolution when not LOW:**
1. Run the AI proposer with the dependency analysis
2. The proposer adds missing edges, breaks cycles by restructuring work units, fixes contract mismatches, corrects parallelization claims
3. Re-run the full AI risk gate

---

## Executive Roadmap — Additional Risks

These supplementary risk types assess the executive roadmap from perspectives not covered by the primary three (market misread, dependency trap, completeness). They run as a second risk gate after the primary gate passes.

### 4. Opportunity Risk

**What it catches:** High-value opportunities the roadmap misses or defers without justification, market timing windows that close while prerequisites are built, competitive advantages that erode during long phase chains.

**Cross-references:**
- `executive-roadmap.md` (being assessed)
- `market-research.md` (competitive landscape, value signals)
- `problem.md` (problem axes with urgency indicators)

**Assessment process:**

1. For each subsystem area where `market-research.md` shows "strong" evidence strength, verify the executive roadmap addresses it in Phase 1 or Phase 2. If a strong-signal area is deferred to Phase 3+, assess whether the deferral risks losing the opportunity window.

2. Identify competitive timing risks: areas where competitors are weak NOW but could improve. If the roadmap defers a gap-position initiative to a late phase, assess whether the gap is durable or time-sensitive.

3. Check for value left on the table: are there low-dependency, high-value slices that could be pulled earlier without disrupting the dependency graph? The dependency trap risk checks that the graph is sound; opportunity risk checks that the graph isn't leaving easy value unrealized.

4. Assess whether the phase structure creates an MVP-viable product at the earliest reasonable point. Can an operator use the system productively after Phase 1, or is Phase 1 only foundations with no standalone value?

**Severity criteria:**
- **LOW:** Strong-signal areas are addressed early. Gap-position initiatives are not deferred past the point where gaps are likely durable. Phase 1 delivers standalone operator value. No obvious high-value, low-dependency slices are unnecessarily deferred.
- **MEDIUM:** A strong-signal area is deferred to Phase 3+ without timing justification. A gap-position initiative faces competitive erosion risk. A low-dependency slice with high value could be moved earlier.
- **HIGH:** Multiple strong-signal areas are deferred late. The roadmap builds foundations for 2+ phases before operators see value. Competitive gaps are likely to close before the roadmap addresses them.

**Resolution when not LOW:**
1. Present the opportunity findings to the executive proposer
2. The proposer revises phase assignments for flagged initiatives, potentially pulling high-value low-dependency slices forward
3. Re-run the full executive risk gate (all primary + supplementary risks)

---

## Pitch Deck Risks

These risks assess the pitch deck as a public-facing communication artifact. They catch failure modes in messaging, accuracy, and expectation setting. The artifact being assessed is `pitch deck.md`.

### 1. Communication Risk

**What it catches:** Unclear messaging, wrong audience framing, unconvincing narrative structure, jargon leakage, tone mismatches, sections that fail to land with the target reader (guild officers).

**Cross-references:**
- `pitch deck.md` (being assessed)
- `executive-roadmap.md` (the strategic source the pitch must represent)
- `proposal.md` (design details the pitch translates into operator language)
- `philosophy.md` (principles the pitch should embody in tone and framing)

**Assessment process:**

1. Read each section as a guild officer who manages a gaming community with 50-200 members, uses 3-5 Discord bots daily, and tracks activity in spreadsheets. For each section, assess:
   - Does the opening hook create recognition ("yes, this is my life")?
   - Is every sentence understandable without technical background?
   - Does the narrative build logically (problem → landscape → vision → how → different → roadmap → action)?
   - Is the tone confident without being salesy, honest without being self-deprecating?

2. Check for jargon leakage: any term a guild officer would not use in daily conversation. Examples of failures: "Pydantic," "ETag," "state machine," "aggregate," "append-only stream," "optimistic locking," "schema migration," "subsystem." Examples of acceptable terms: "application," "review," "waitlist," "chapter," "roster," "permission," "audit trail."

3. Assess section-by-section persuasiveness:
   - Problem: Does it create urgency? Would an officer forward this to another officer saying "this is exactly our problem"?
   - Landscape: Does it validate the reader's frustration with current tools without attacking competitors by name excessively?
   - Vision: Is the value proposition memorable? Can the reader restate it in one sentence?
   - How It Works: Do the workflow examples feel concrete and real, or abstract and hypothetical?
   - Differentiators: Are they stated as operator benefits, not engineering achievements?
   - Roadmap: Does it create confidence in execution without overpromising timelines?
   - Call to action: Is there a clear, low-friction next step?

4. Assess overall coherence: does each section flow into the next? Is there a single narrative arc from "here's your pain" to "here's how to solve it"?

**Severity criteria:**
- **LOW:** Messaging is clear and officer-focused throughout. No jargon leakage. Narrative arc is coherent. Each section lands with the target audience. Tone is appropriate.
- **MEDIUM:** Some sections drift into engineering framing. A few terms require technical background. Narrative has a gap or a section that doesn't serve the arc. Tone shifts between sections.
- **HIGH:** Multiple sections would confuse a non-technical officer. Heavy jargon throughout. No clear narrative arc. Tone is inconsistent or inappropriate for the audience.

**Resolution when not LOW:**
1. Present the communication findings to the pitch deck agent (gpt-xhigh)
2. The agent rewrites flagged sections for clarity, removes jargon, strengthens narrative arc
3. Re-run the full pitch deck risk gate

---

### 2. Accuracy Risk

**What it catches:** Claims that don't trace to verified strategy artifacts, overstatements about current or planned capabilities, competitor characterizations that are unfair or outdated, statistics or evidence cited without proper sourcing.

**Cross-references:**
- `pitch deck.md` (being assessed)
- `market-research.md` (competitor claims must trace here)
- `executive-roadmap.md` (roadmap claims must match)
- `proposal.md` (capability claims must trace here)
- `problem.md` (problem claims must trace here)

**Assessment process:**

1. For every factual claim in the pitch deck, trace it to a source artifact:
   - Problem claims → `problem.md` (which axis?)
   - Competitor claims → `market-research.md` (which finding? which source?)
   - Capability claims → `proposal.md` (which section? which workflow?)
   - Roadmap claims → `executive-roadmap.md` (which phase? which slice?)

2. For each claim, classify:
   - **Accurate**: The claim faithfully represents the source
   - **Overstated**: The claim goes beyond what the source supports (e.g., "the only platform that..." when the market research shows gaps, not uniqueness)
   - **Unsourced**: The claim doesn't trace to any artifact
   - **Outdated**: The claim references competitor state that may have changed

3. Check for implicit claims: statements that don't explicitly promise something but create an expectation. Example: "Your data is always yours" might imply export functionality that the proposal doesn't define yet.

**Severity criteria:**
- **LOW:** All claims trace to source artifacts. No overstatements. No unsourced claims. Implicit claims are consistent with the proposal.
- **MEDIUM:** 1-2 overstatements or unsourced claims. An implicit claim extends beyond current proposal scope.
- **HIGH:** Multiple overstatements. Claims contradict source artifacts. Competitor characterizations are unfair or fabricated.

**Resolution when not LOW:**
1. Present the accuracy findings with specific claim-to-source mappings
2. The pitch deck agent corrects overstatements, adds sources, removes unsourced claims
3. Re-run the full pitch deck risk gate

---

### 3. Promise Risk

**What it catches:** Expectations the pitch deck creates that the roadmap cannot deliver, timeline implications that don't match engineering reality, feature descriptions that imply more than what's scoped.

**Cross-references:**
- `pitch deck.md` (being assessed)
- `executive-roadmap.md` (what is actually committed)
- `proposal.md` (what is actually designed)

**Assessment process:**

1. For each capability described in the "How It Works" and "What Makes This Different" sections, verify:
   - Is this capability in the current roadmap (any phase)?
   - If yes, which phase? The pitch should not present Phase 3+ capabilities as if they ship immediately.
   - If no, the pitch is promising something that isn't planned.

2. For the roadmap section, verify:
   - Phase descriptions match `executive-roadmap.md` phase capabilities exactly
   - No capabilities are moved to earlier phases than the executive roadmap places them
   - "What still hurts" sections are honest and complete
   - No timeline promises are made (the executive roadmap is ordered but not time-bound)

3. Check for scope inflation: descriptions that make a feature sound larger or more complete than what the proposal actually defines. Example: describing the trust system as "AI-powered reputation scoring" when it's deterministic signal aggregation.

4. Assess the call to action: does it set appropriate expectations about the system's current state (not yet built) vs. future state?

**Severity criteria:**
- **LOW:** All described capabilities are in the roadmap. Phase assignments match. No timeline promises. Scope descriptions are faithful. Call to action accurately represents current state.
- **MEDIUM:** A capability is described as if it's earlier than its actual phase. Scope description inflates a feature. Timeline language implies commitment.
- **HIGH:** Capabilities are promised that aren't in the roadmap. Multiple features are scope-inflated. The pitch implies the system is further along than it is.

**Resolution when not LOW:**
1. Present the promise findings with specific pitch-to-roadmap mappings
2. The pitch deck agent corrects phase assignments, deflates scope descriptions, clarifies current state
3. Re-run the full pitch deck risk gate
