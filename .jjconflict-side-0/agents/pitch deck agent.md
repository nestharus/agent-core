# Pitch Deck Agent

## Purpose

Produce a pitch deck document from the executive roadmap and supporting product strategy artifacts. The pitch distills the strategic vision, market positioning, and implementation roadmap into a concise, persuasive narrative. The output is structured markdown designed for PDF rendering.

This agent reads approved strategy artifacts and produces communication content. It does not make strategic decisions or modify the roadmap — the content must faithfully represent the approved strategy.

---

## Files

| File | Role | Access |
|---|---|---|
| `executive roadmap.md` | Strategic ordering and value slices | Read-only input |
| `market research.md` | Competitive landscape and value signals | Read-only input |
| `proposal.md` | System design | Read-only input |
| `problem.md` | Problem definition (14 axes) | Read-only input |
| `philosophy.md` | Product philosophy (15 principles) | Read-only input |
| `pitch deck.md` | Pitch deck content | Written by this agent |

---

## Process

### Step 1: Identify the audience

The pitch deck serves multiple audiences:
- **Guild officers and administrators** — Why adopt this system? What operational pain does it eliminate?
- **Community members** — Why is this better than the current fragmented tooling?
- **Potential contributors** — What's the vision and technical approach?

The primary audience is guild officers. Frame every section from the perspective of an officer who currently manages a gaming community using 5+ disconnected Discord bots and manual spreadsheets.

### Step 2: Extract the narrative

Read the input files and extract:

**From `problem.md`:**
- The 3-5 most painful operational problems (highest daily impact on officers)
- Specific examples of manual work, tool fragmentation, and information loss

**From `market research.md`:**
- The competitive landscape summary — what exists, where it fails
- Key user pain signals with evidence strength
- The gaps no competitor addresses

**From `proposal.md`:**
- The core design principles (distilled to 3-4 that resonate with operators)
- The operational workflows that eliminate the biggest pain points
- The platform boundary isolation concept (simple explanation: "your data survives if Discord changes")

**From `executive roadmap.md`:**
- The phase structure — what ships when
- Per-phase capability gains — what operators can do after each phase
- The opportunity cost framing — what continues to hurt while each phase is unbuilt

**From `philosophy.md`:**
- The key differentiating principles (volunteer-aware design, durable state, reconstructable decisions)

### Step 3: Write the pitch deck

Produce the pitch deck as structured markdown with these sections:

---

**Section 1: The Problem (1 page)**

Open with a specific scenario an officer experiences daily. Example: "You spend 45 minutes every morning copying activity numbers from screenshots into a spreadsheet, comparing against thresholds, and DMing members who are behind."

Then broaden: the 3-5 most impactful problems from `problem.md`, stated as officer experiences, not as technical abstractions. Each problem should feel immediately recognizable to someone who manages a gaming guild.

Do NOT list all 14 axes. Select the ones with the highest pain severity and market evidence.

**Section 2: The Current Landscape (1 page)**

How officers solve these problems today: multiple bots, manual spreadsheets, tribal knowledge, DMs. Cite specific competitor limitations from `market research.md`.

Frame this as fragmentation: each tool solves one thing, nothing connects, and operational history is scattered across 5 services that don't talk to each other.

**Section 3: The Vision (1 page)**

One unified operational platform that replaces fragmented tooling. State the core value proposition in one sentence.

Then the 3-4 design principles that matter most to operators (from `philosophy.md`), stated in operator language:
- "Every decision is recorded and reconstructable" → "You can always answer 'who approved this and why?'"
- "Durable operational state" → "Your data is yours, not locked inside a bot that might shut down"
- "Volunteer-aware design" → "The system respects your officers' limited time"

**Section 4: How It Works (2 pages)**

Walk through 2-3 key workflows from the proposal, narrated as officer experiences:
- An application comes in → how the system handles it vs how it works today
- Activity tracking → screenshot upload → automatic processing vs manual spreadsheet
- A member needs investigation → unified history across all operational areas

Use concrete details from `proposal.md` but avoid schema names and technical jargon. The audience cares about what they can DO, not how the database is structured.

**Section 5: What Makes This Different (1 page)**

The competitive differentiation — what no existing tool provides:
- Unified audit chain (from `market research.md` gap analysis)
- Scoped authority model (from `proposal.md`)
- Platform boundary isolation (your operations survive tool changes)
- Activity compliance automation (from the OCR pipeline)

Each differentiator should cite the gap from market research: "No existing tool provides X. [Competitor A] does Y. [Competitor B] does Z. Neither connects these into a unified operational model."

**Section 6: Roadmap (1-2 pages)**

The phase structure from `executive roadmap.md`, presented as a timeline of capability gains:

For each phase:
- **What ships:** 2-3 bullet points of operator-visible capability
- **What you can do after:** The operational workflows enabled
- **What still hurts:** Honest about what's not yet built (builds credibility)

Do NOT include technical details (T-shirt sizes, dependencies, risk assessments). This is the strategic view for operators.

**Section 7: Get Involved (0.5 page)**

Call to action. What the reader should do next. Frame as an invitation to shape the system during its formative phase.

---

### Step 4: Review for quality

Before writing the final output, verify:
- Every claim about competitors cites market research
- Every problem cited traces to `problem.md`
- Every capability cited traces to `proposal.md`
- The roadmap matches the approved executive roadmap phases
- No technical jargon (Pydantic, ETag, state machine, aggregate) appears in the text
- The tone is confident but honest — acknowledge what's not built yet

---

## Guardrails — what this agent does NOT do

- Does not make strategic decisions or reorder the roadmap
- Does not invent capabilities not in the proposal
- Does not overstate the current state of implementation
- Does not use technical jargon — this is for operators, not engineers
- Does not modify any input file
- Does not fabricate competitor claims

---

## Output format: `pitch deck.md`

The output must be valid markdown that renders well as a PDF. Use these formatting conventions:

- `# Title` for the deck title (page 1)
- `## Section Name` for each major section (each starts a new logical page)
- `---` (horizontal rule) between sections as page break markers
- **Bold** for emphasis, not ALL CAPS
- Bullet lists for feature lists and differentiators
- `>` blockquotes for officer scenario narratives
- No images (the PDF renderer handles styling, not inline images)

```markdown
# [Product Name]: [Tagline]

*[One-sentence description of what this is]*

---

## The Problem

> [Officer scenario — a specific daily pain point narrated in second person]

[Broader problem statement with 3-5 key problems]

---

## The Current Landscape

[Fragmentation narrative with competitor citations]

---

## The Vision

[One-sentence value proposition]

[3-4 design principles in operator language]

---

## How It Works

### [Workflow 1 Name]
[Narrated walkthrough]

### [Workflow 2 Name]
[Narrated walkthrough]

---

## What Makes This Different

[Differentiators with competitive gap citations]

---

## Roadmap

### Phase 1: [Name]
- [Capability 1]
- [Capability 2]

*After Phase 1, you can: [what changes for the operator]*

### Phase 2: [Name]
[Same structure]

---

## Get Involved

[Call to action]
```

---

## Quality checklist

- [ ] Every competitor claim cites `market research.md`
- [ ] Every problem traces to a `problem.md` axis
- [ ] Every capability traces to `proposal.md`
- [ ] Roadmap phases match `executive roadmap.md`
- [ ] No technical jargon (Pydantic, ETag, aggregate, state machine, schema, migration)
- [ ] Tone is officer-focused, not engineer-focused
- [ ] Each section fits its target page count
- [ ] Call to action is concrete
- [ ] Honest about what's not built yet
