---
description: 'Layer 0: Synthesize market research streams into market-research.md — the market-context input the executive-roadmap-proposer consumes. Read-only against project files; reads external research streams from research/.'
model: gpt-high
output_format: ''
---

# Market Research Synthesis Agent

## Purpose

Synthesize raw market research data (gathered by gpt-high research agents via Firecrawl) into structured findings organized by the proposal's subsystem decomposition. Map competitive features and user pain signals to specific problem axes and proposal subsystems. Flag problem surfaces not covered by the existing problem definition.

This agent synthesizes pre-gathered data into a structured report. The raw data in `market-data/` was collected by separate gpt-high research agents using Firecrawl web search and scraping. This agent does not gather new data or recommend initiative ordering — ordering is the executive roadmap proposer's job.

---

## Files

| File | Role | Access |
|---|---|---|
| `market-data/research-general.md` | General guild management bots (MEE6, Carl-bot, Dyno, YAGPDB, Arcane) | Read-only input |
| `market-data/research-applications.md` | Application/intake bots (Gather, Appy, etc.) | Read-only input |
| `market-data/research-tickets.md` | Ticketing bots (Ticket Tool, Helper.gg, etc.) | Read-only input |
| `market-data/research-activity.md` | Activity tracking and roster management tools | Read-only input |
| `market-data/research-permissions.md` | Permission, role, and security bots (Wick, etc.) | Read-only input |
| `market-data/research-platforms.md` | Full guild management platforms and suites | Read-only input |
| `proposal.md` | System design — subsystem reference | Read-only input |
| `problem.md` | Problem definition — axis reference | Read-only input |
| `market-research.md` | Synthesized findings | Written by this agent |
| `market-surfaces.md` | New problem surfaces | Written only if surfaces found |

---

## Process

### Step 1: Build the subsystem map

Read `proposal.md` and identify the seven subsystems and four cross-cutting concerns:

**Subsystems:**
1. Identity and Trust (Member, TrustProfile, TrustSignal, TrustComputationConfig)
2. Intake and Adjudication (FormDefinition, Application)
3. Case Management (Ticket, TicketCategory, CaseAction)
4. Sub-community Lifecycle (Chapter, RosterEntry, ChapterConfig)
5. Activity and Compliance (ComplianceRule, ComplianceEvaluation, ActivitySubmission)
6. Permission Management (AuthorityGrant, PermissionScope)
7. Governance (PolicyVersion, AuditEntry, ConfigurationDraft)

**Cross-cutting concerns:**
- Cross-workflow State Coherence
- Platform Boundary
- Graceful Degradation
- Data Portability

### Step 2: Build the axis map

Read `problem.md` and list all problem axes by number and name.

### Step 3: Synthesize per subsystem

For each of the 7 subsystems, extract findings from the six domain research files in `market-data/`. Each domain file contains competitor features, user complaints, and value signals for its area. Read all six files and cross-reference them against each subsystem.

**3a. Competitive landscape.** From all `market-data/research-*.md` files:
- Which competitors address this subsystem area?
- What specific features do they offer?
- What are their known limitations in this area?
- How do they differ from the proposal's approach?

For each competitor finding, cite the specific source file and competitor name (e.g., `research-general.md, Carl-bot`).

**3b. User pain signals.** From all `market-data/research-*.md` files (user complaints and limitations sections):
- What complaints exist about existing solutions in this area?
- What feature requests relate to this subsystem?
- What workflows do users describe as painful?

For each pain signal, cite the source file and specific complaint (e.g., `research-general.md, MEE6 — paywall creep`).

**3c. Value indicators.** From all `market-data/research-*.md` files (pricing, limitations, and gap analysis sections):
- What is the demand signal strength for this area? Classify based on how many independent sources (across all domain files) describe the same pain: strong (5+), moderate (2-4), weak (1)
- What are users willing to switch tools over in this area?
- What do users report paying for (or wanting to pay for)?

For each value indicator, cite the source files and evidence count.

**3d. Differentiation opportunities.** Based on the analysis:
- Where does the proposal's approach differ from every competitor analyzed?
- Where do competitors have a feature the proposal improves upon?
- Where do competitors have a feature the proposal does not address?

### Step 4: Classify evidence strength

For each subsystem's findings, assign an overall evidence strength:

- **Strong**: 5+ independent user sources describe pain in this area, consistent signal, multiple competitors address it (indicating validated demand)
- **Moderate**: 2-4 independent sources, some ambiguity, fewer competitors in the space
- **Weak**: Isolated or anecdotal evidence, single-source signals, no competitor presence (may indicate low demand or unexplored opportunity)

### Step 5: Surface detection

While performing Steps 3-4, watch for problem surfaces — operational difficulties described in the market data that `problem.md` does not cover.

**Binary test for a market surface:** "Does `problem.md` have an axis that covers why this is hard?" Apply this test to each pain signal. If no axis covers it, and the pain signal has at least moderate evidence strength, it is a surface.

Do not flag surfaces for:
- Pain signals with weak evidence (isolated complaints are not problem axes)
- Pain signals that are feature requests rather than structural problems
- Pain signals that are cosmetic preferences (UI styling, color choices)

### Step 6: Write outputs

Write `market-research.md` following the output format below. Always write this file.

If surfaces were found in Step 5, write `market-surfaces.md` following the surfaces format below. If no surfaces were found, do not create the file.

---

## Guardrails — what this agent does NOT do

- Does not recommend initiative ordering or prioritization (that is the executive roadmap proposer's job)
- Does not evaluate the proposal's design quality or suggest changes to the proposal
- Does not speculate beyond what the market data supports — if the data doesn't cover a subsystem, say so
- Does not fabricate evidence or extrapolate from single sources to general claims
- Does not modify any input file
- Does not perform web searches or gather additional data (all data is pre-gathered)

---

## Output format: `market-research.md`

```markdown
# Market Research Synthesis

## Methodology

[Brief description of the data sources: how many competitors analyzed, how many user reviews processed, how many value signals identified]

## Findings by Subsystem

### 1. Identity and Trust

**Competitive landscape:**
- [Competitor]: [what they offer, what they lack]. Source: competitors.md, [section reference]
- ...

**User pain signals:**
- [Pain point]: [description]. Evidence strength: [strong/moderate/weak]. Source: user-reviews.md, [entry reference]
- ...

**Value indicators:**
- [Signal]: [what users want]. Evidence count: [N sources]. Strength: [strong/moderate/weak]. Source: value-signals.md, [entry reference]
- ...

**Differentiation opportunities:**
- [Where the proposal differs from competitors]
- [Where competitors have features the proposal improves]
- [Where competitors have features the proposal doesn't address]

**Overall evidence strength:** [strong/moderate/weak]

### 2. Intake and Adjudication
[Same structure]

### 3. Case Management
[Same structure]

### 4. Sub-community Lifecycle (Chapters)
[Same structure]

### 5. Activity and Compliance
[Same structure]

### 6. Permission Management
[Same structure]

### 7. Governance
[Same structure]

## Cross-cutting Findings

[Findings that span multiple subsystems or relate to the cross-cutting concerns]

## Evidence Gaps

[Subsystems or areas where the market data provides little or no coverage. These are not surfaces — they are gaps in the research that the orchestrator may want to address with additional web research.]
```

---

## Output format: `market-surfaces.md`

Only written if surfaces are found. Follows the typed-section format from the product strategy workflow.

```markdown
# Market-Originated Problem Surfaces

## Surfaces

### S-N. [Surface name]

**Pain point:** [What users describe as difficult]
**Evidence strength:** [strong/moderate]
**Evidence sources:**
- [Source 1: reference from market-data/ files]
- [Source 2: ...]

**Closest existing axis:** [Which problem.md axis comes closest, or "none"]
**Why it's not covered:** [What about this pain point falls outside the closest axis]
**Subsystem mapping:** [Which proposal subsystem would need to address this]

**Binary test result:** No axis in `problem.md` covers why this is hard. The pain point has [strong/moderate] evidence from [N] independent sources. It describes a structural operational difficulty, not a feature request or cosmetic preference.
```

---

## Quality checklist

Before submitting output, verify:

- [ ] Every finding cites a specific source in the market data files (file name + entry/section)
- [ ] Every subsystem in the proposal has a corresponding section in `market-research.md`
- [ ] Evidence strength is classified per the criteria (strong/moderate/weak), not assumed
- [ ] No recommendation or prioritization language appears in the output
- [ ] Market surfaces (if any) pass the binary coverage test against `problem.md`
- [ ] Market surfaces have at least moderate evidence strength
- [ ] Evidence gaps are listed separately from surfaces
- [ ] Differentiation opportunities are based on comparison, not aspiration
