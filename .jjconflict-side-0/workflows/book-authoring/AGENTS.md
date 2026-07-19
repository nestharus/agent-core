# Execution Philosophy — Document Authoring

## Files

| Path | Purpose |
|------|---------|
| `problem-first-ai-engineering.md` | Book source (Markdown) |
| `problem-first-ai-engineering.pdf` | Generated PDF |
| `md_to_pdf.py` | Markdown → PDF converter (Python, weasyprint) |

### PDF Generation

```bash
cd /home/nes/projects/agent-implementation-skill/execution-philosophy
python3 md_to_pdf.py
```

Requires `markdown` and `weasyprint` Python packages. Uses `md_in_html` extension for term boxes. CSS is inline in the script.

### Term Boxes

University textbook-style definition boxes. Use for introducing new terms only.

```html
<div class="term-box">
<div class="term-header"><svg ...>...</svg> Term Name</div>
<p>Definition.</p>
<p class="term-history">Historical context.</p>
</div>
```

SVG icons go inline in the header. Keep them 24x24, stroke color `#5a4e3a`.

---

## Running Sub-Agents

Sub-agents are invoked via the `agents` binary (`~/.local/bin/agents`). The binary is the CLI mode of [Oulipoly Agent Runner](https://github.com/nestharus/agent-runner).

### CLI Syntax

```bash
agents [OPTIONS] [AGENT] [PROMPT...]
```

| Option | Description |
|--------|-------------|
| `-m, --model <MODEL>` | Execute a model directly (no agent file) |
| `-a, --agent-file <AGENT_FILE>` | Path to an agent `.md` file (any location) |
| `-f, --file <FILE>` | Read prompt from file |
| `-p, --project <PROJECT>` | Working directory for the subprocess |
| `--models-dir <MODELS_DIR>` | Override models directory |
| `--agents-dir <AGENTS_DIR>` | Override agents directory |

**Prompt resolution priority:** `--file` > positional arguments > stdin

### Common Invocation Patterns

```bash
# Model + prompt file (standard for audits)
agents --model gpt-xhigh --file /tmp/audit-prompt.md --project .

# Inline prompt
agents --model gpt-high "Summarize the key findings"

# Pipe prompt from stdin
cat spec.md | agents --model glm
```

### Model Configuration

Model configs are TOML files in `~/.config/oulipoly-agent-runner/models/` (one per model). The filename minus `.toml` is the model name used with `--model`.

```toml
# Single provider
command = "codex"
args = ["exec", "--model", "gpt-5"]
prompt_mode = "stdin"
```

```toml
# Multiple providers (load balanced)
prompt_mode = "arg"

[[providers]]
command = "codex"
args = ["exec", "--dangerously-bypass-approvals-and-sandbox", "-m", "gpt-5.4", "-c", "model_reasoning_effort=xhigh"]

[[providers]]
command = "codex2"
args = ["exec", "--dangerously-bypass-approvals-and-sandbox", "-m", "gpt-5.4", "-c", "model_reasoning_effort=xhigh"]
```

Load balancing is automatic: round-robin with error avoidance.

### Key Models for Document Work

| Model | Use for | Concurrency limit |
|-------|---------|-------------------|
| `gpt-xhigh` | Auditing (best at systematic cross-referencing) | 2 at a time |
| `gpt-high` | Research, outlining, concept extraction, general analysis | No hard limit |
| `gpt-xhigh` | Alignment checks, editing, tenet evaluation, Mermaid diagrams | As available |
| `gemini-high` | SVG visual planning, art direction (Gemini 3.1 Pro, HIGH thinking) | Rate limited |
| `gemini-medium` | SVG generation, visual tasks (Gemini 3.1 Pro, MEDIUM thinking) | Rate limited |
| `gemini-low` | Quick SVG drafts, iteration, visual review (Gemini 3.1 Pro, LOW thinking) | Rate limited |
| `seedream-t2i` | Text-to-image generation (Seedream 5.0 Lite via Atlas Cloud) | Async, polling |
| `seedream-i2i` | Image-to-image editing (Seedream 5.0 Lite Edit via Atlas Cloud) | Async, polling |
| `seedance-t2v` | Text-to-video generation (Seedance v1.5 Pro, 1080p, $0.052/s) | Async, polling |
| `seedance-i2v` | Image-to-video generation (Seedance v1.5 Pro, 1080p, $0.052/s) | Async, polling |
| `seedance-t2v-fast` | Text-to-video fast (Seedance v1.5 Pro Fast, 720p, $0.02/s) | Async, polling |
| `seedance-i2v-fast` | Image-to-video fast (Seedance v1.5 Pro Fast, 720p, $0.02/s) | Async, polling |
| `seedance-t2v-low` | Text-to-video cheapest (Seedance v1 Pro Fast) | Async, polling |
| `seedance-i2v-low` | Image-to-video cheapest (Seedance v1 Pro Fast) | Async, polling |

### Gemini Configuration

Gemini models use the Gemini CLI (`gemini`) with custom aliases defined in `~/.gemini/settings.json`. Reasoning levels are controlled via `thinkingConfig.thinkingLevel` (not model name suffixes). All `gemini-*` models point to `gemini-3.1-pro-preview`.

| agents model | Gemini CLI alias | Thinking level |
|--------------|-----------------|----------------|
| `gemini-low` | `gemini-3.1-pro-low` | LOW |
| `gemini-medium` | `gemini-3.1-pro-medium` | MEDIUM |
| `gemini-high` | `gemini-high` | HIGH |

### Atlas Cloud (Seedream / Seedance)

Image and video generation via Atlas Cloud API. No CLI — uses wrapper scripts in `~/.local/bin/` that handle API calls and async polling. Auth via `$ATLASCLOUD_API_KEY` environment variable (set in `~/.bashrc`).

**Text-to-image** — prompt goes directly as the text argument:
```bash
agents --model seedream-t2i "A detailed technical diagram of a feedback loop system"
```

**Image-to-image** — prompt is JSON with `prompt` and `image` fields:
```bash
agents --model seedream-i2i '{"prompt": "Refine colors and add depth", "image": "/path/to/visual-plan.png"}'
```

**SVG input** — the wrapper scripts auto-convert `.svg` files to PNG before sending to the API. Requires one of: `rsvg-convert` (`librsvg2-bin`), `inkscape`, or `imagemagick`. Install with:
```bash
sudo apt install librsvg2-bin   # recommended, lightweight
```

**Video** — same patterns as image, with `seedance-t2v` and `seedance-i2v`.

#### Agents Binary Capability Gaps

The current agents binary passes text prompts only. Image/video models work through wrapper scripts but have limitations:

1. **No native image I/O** — image-to-image requires JSON-formatted prompts with file paths, not a first-class file parameter. The agents binary treats all input/output as text.
2. **No output file handling** — models return image/video URLs as text on stdout. There is no built-in mechanism to download, store, or chain generated images into subsequent pipeline steps.
3. **No multi-modal prompt support** — cannot natively interleave text and image content in a single prompt the way multimodal LLM APIs support.

These gaps mean image generation works for standalone operations but cannot yet be composed into automated multi-step visual pipelines through the agents binary alone.

---

## Core Tenets

The book teaches 4 core tenets. Every concept, technique, and pattern in the book traces to one or more of these. They apply at every layer as different strategies implementing the same principles.

### 1. Problem Definition

Understand the domain before acting on it. A problem is the structural reality of a domain — its axes, interactions, constraints, stakeholders, and failure physics. Problems exist whether or not anyone solves them. Problem definition maps this terrain so that all downstream work has something real to align against.

NOT: finding existing solutions, identifying pain points, listing features, searching for answers. Pain and existing solutions are *evidence* used during exploration, not the object of exploration.

IS: mapping structural axes, discovering interactions, identifying constraints, understanding stakeholders, monotonically growing as new surfaces are discovered.

Output: a problem map organized by axes — the reference against which everything downstream is evaluated.

### 2. Values

Define the concrete character and governing principles of what you're building. Values describe what the thing should BE LIKE — its feel, its character, its qualities. "I want it to feel comfy." "Super AI-driven." "Fast generative UI." Values sit above proposals and constrain what approaches are acceptable. Values are owned by humans.

NOT: economic value (dollars — that's a separate concept in risk assessment), features, abstract slogans, implementation decisions.

IS: the feel/character/qualities the result should have, concrete enough to evaluate proposals against, sometimes in tension with each other (requiring user input on priorities).

Values imply constraints, and constraints imply proposals: a value ("fast generative UI") → AI searches the landscape to understand what "fast" means at scale → generates candidate proposals → checks proposals against ALL values → identifies conflicts → asks user for priorities when values compete.

Output: a philosophy — the artifact that records what the thing should be like and how to resolve tradeoffs when values compete.

### 3. Proposals

Generate and evaluate contestable candidate approaches. A proposal is a structured claim about how to address problems while honoring values. Always candidates — tested against problems and values, never treated as final truth. Proposals function as probes: proposing reveals new problem terrain.

NOT: plans (becomes a plan after alignment), specs (becomes an execution spec after alignment), problems, values (though values can imply proposals, those belong on the proposal side).

IS: structured (exposes addressed problems, approach, fit to values, tensions, unknowns), contestable, decomposable into one-to-one checks against individual problem axes, expansive (reveals new surfaces in the problem map).

Output: a proposal that, after alignment checking, can become a bounded execution spec.

### 4. Risk Assessment

Evaluate tradeoffs and scale process proportionally. Universal mechanism — applies wherever decisions about ordering, scoping, or tradeoffs exist. The loss function changes by context, but the mechanism is the same: evaluate what you stand to gain or lose, and scale your response proportionally.

NOT: binary (safe/unsafe), a one-time gate, limited to any single domain, a substitute for the other three tenets.

IS: proportional (scales to actual conditions), universal (applies at every layer where tradeoff decisions exist), interactive (assessments at different layers influence each other), continuous (reassessed as new information arrives).

Risk assessment operates on a conservative-to-greedy spectrum with three modes:

- **Risk assessment** (conservative) — What can fail? Identify dangers and scale process to avoid them.
- **Optimization** (conservative) — What can we get away with without failing? Find the efficient frontier — minimum process for acceptable risk.
- **Opportunity** (greedy) — What could improve things even though not doing it won't cause failure? Reach for gains beyond the safe path.

Opportunity is dangerous: it introduces new risk that didn't exist before you reached for it. Opportunity must be evaluated through risk assessment — it is not free. Effective in specific circumstances (e.g., visualization improves communication even though text alone won't fail), but each opportunity opens new risk surface.

Risk assessment drives sequencing: assess what you stand to lose or gain by each choice, order and scope accordingly. When assessments at different layers interact (e.g., two options close on one dimension but differ significantly on another), the interaction can reorder work.

### Tenet Interaction

```
Problem Definition → feeds → Values (domain reveals what qualities matter)
Values → constrain → Proposals (what approaches honor the character we want)
Proposals → probe → Problem Definition (reveal new terrain)
Risk Assessment → orders and scales all three
```

The convergent loop: define problems → establish values → propose → check alignment → discover new surfaces → update → repeat until new passes stop producing meaningful surprises.

### Supporting Discipline: Continuity

The outputs of all four tenets — problem maps, philosophies, proposals, and risk assessments — must be preserved in durable artifacts with reasons and invalidation conditions. This is not a 5th tenet. It has no optimization target of its own. It is infrastructure that keeps the 4 tenets intact across time, sessions, and agent boundaries.

Without continuity, systems re-derive resolved reasoning, cycle through invalidated approaches, and lose the justification chain that connects implementation to the problems and values it was meant to serve.

Continuity includes: traceability (artifacts trace upward to the layer that justifies them), generation-time citation (attach justification at creation, not after the fact), decision logs (record what was decided, why, and what would invalidate it), handoff contracts (self-contained enough for a fresh agent to continue), and history preservation (prevent cycling by remembering what was tried and why it was abandoned).

### Alignment Test

Every concept in the book should answer: "This is a strategy for implementing [tenet] at [layer]" or "This is continuity infrastructure for preserving [tenet] outputs across [time/sessions/boundaries]."

If a concept cannot be traced to a tenet or to continuity, it is either:
1. A candidate new tenet (evaluate carefully)
2. A misframed concept that needs alignment to an existing tenet
3. Content that doesn't belong in the book

---

## Content Authoring Workflow

The pattern: audit the current state, research what's missing, then edit via sub-agents.

### Phase 1: Audit (gpt-xhigh)

Use `gpt-xhigh` for audit tasks. **Max 2 xhigh agents at a time.**

Each audit targets **one specific concern** and searches the **entire document**. The audit prompt must be extremely detailed about what the concern is, what correct looks like, and what to report.

```bash
# Write the audit prompt to a file
cat > /tmp/audit-concern-name.md << 'EOF'
# Audit: [Concern Name]

## Your Task
Read the ENTIRE file at `execution-philosophy/problem-first-ai-engineering.md`.
Search for every instance where [specific concern] appears or is discussed.

## What Correct Looks Like
[Detailed description of the correct framing/definition/treatment]

## What Is Currently Wrong
[Detailed description of the known misalignment]

## What to Report
For EVERY instance:
- Exact quote (2-3 sentences of context)
- Line number
- Whether it is correct or incorrect
- What it SHOULD say (brief note)

Be exhaustive. Do not skip any section.
EOF

# Run it
agents --model gpt-xhigh --file /tmp/audit-concern-name.md --project .
```

Run audits in parallel pairs. Wait for both to complete before launching the next pair.

### Phase 2: Research (sub-agents)

Use `agents --model gpt-high` for research tasks: web search, paper lookup, competitive analysis. Research agents should return findings, not edit files.

### Phase 3: Context File

Write a shared context file summarizing audit findings + research results. Sub-agents in Phase 4 read this file instead of receiving everything in the prompt.

```bash
# Example
cat > /tmp/rework-context.md << 'EOF'
# Context for Section Rework

## Audit Findings
[Summarized findings from Phase 1]

## Research Findings
[Key data from Phase 2]

## Author's Intent
[What the section should communicate — the ideas, not the words]
EOF
```

### Phase 4: Edit (gpt-high sub-agents, one per chapter)

Use `agents --model gpt-high` to launch **one sub-agent per chapter/section**. Each agent reads the context file and its assigned section, then makes targeted edits.

Sub-agents can run in parallel since they edit non-overlapping sections of the same file (the Edit tool uses exact string matching, not line numbers).

Each sub-agent prompt must include:
- Path to the context file to read
- Which lines/chapter to read and edit
- Specific changes needed (from audit findings)
- Constraints: targeted edits only, match existing tone, no term boxes unless requested

### Phase 5: PDF Regeneration

```bash
cd /home/nes/projects/agent-implementation-skill/execution-philosophy
python3 md_to_pdf.py
```

### Principles

- **One concern per audit agent** — multi-concern audits lose accuracy. The audit itself is a many-to-many problem; keep it one-to-one.
- **gpt-xhigh for auditing, gpt-high for editing** — use the deeper model for systematic cross-referencing and the standard high model for targeted prose edits that match existing tone.
- **Audit prompts must be exhaustive** — the more detail about what correct looks like, the more accurate the audit. Vague prompts produce vague results.
- **Context files over mega-prompts** — sub-agents read context files rather than receiving all findings inline. Keeps prompts focused.
- **Rework, don't patch** — when a section has conceptual problems, rewrite the prose around the correct idea. Word-swapping ("difficulty" → "terrain") without reworking the surrounding sentences produces incoherent text.

---

## Communication Values

These govern writing decisions throughout the book. When two good writing choices conflict, the value picks the winner. Derived from research (see `.workspace/research-communication-values.md`).

| # | Value | Resolves |
|---|-------|----------|
| V1 | Concrete before abstract, then fade the scaffold | Whether to lead with example or formalism |
| V2 | One new idea at a time | Whether to combine or sequence concepts |
| V3 | Context before novelty; stress at closure | Where to put new information in a sentence/section |
| V4 | Stable terms and frames over stylistic variety | Whether to use synonyms for variety |
| V5 | Signal structure; don't make readers infer it | Whether to use a diagram/heading vs prose |
| V6 | Relevance over seductive detail | Whether to keep an interesting tangent |
| V7 | Calibrated claims over persuasive certainty | Whether to hedge or assert |

---

## Quality Workflows

These detect and fix problems across the full document. Run in order; later workflows depend on earlier outputs.

### QW1: Concept Registry

Build a canonical glossary of key concepts. Foundation for all other workflows.

**Output:** `.workspace/concept-registry.md`
**Agent:** `gpt-xhigh` — extract all key concepts, canonical terms, definitions, first-definition locations.
**Maintenance:** Update after any structural edit.

### QW2: Dependency Check

For each key term, verify first use comes after first definition. Flag violations.

**Input:** Concept registry
**Agent:** Programmatic or `gpt-xhigh`
**Fix:** Reorder, add inline previews, or move definitions earlier.

### QW3: Framing Consistency Audit

For each concept in the registry, find every passage that defines/describes/characterizes it. Compare pairwise for drift.

**Input:** Concept registry
**Agent:** `gpt-xhigh` — one concept per audit run (one-to-one, not many-to-many)
**Fix:** Pick canonical framing, update drifted passages, mark intentional lens changes.

### QW4: Repetition Audit

Find passage pairs that make the same point. Classify each as functional reinforcement vs harmful repetition.

**Agent:** `gpt-xhigh` — full document scan
**Fix:** Merge, compress, or give the recurrence a new pedagogical job.

### QW5: Values Alignment Audit

For each chapter, check prose against the 7 communication values. Flag specific violations.

**Agent:** `gpt-xhigh` — one chapter per audit, values document as context
**Fix:** Rework flagged passages per the violated value.

### QW6: Concept Extraction

Extract core ideas from each section of the book as terse lists. Foundation for stability and tenet alignment checks.

**Output:** `.workspace/concepts/partN-raw.md` per Part, compiled into `all-concepts-compiled.md`
**Agent:** `gpt-high` — one agent per Part, extracting core ideas as flat bulleted lists. No arguments, no explanations. Just the concepts.
**Maintenance:** Re-extract after structural edits or new content.

### QW7: Stability Analysis

Review extracted concept lists for meaning drift across chapters. Does the same concept mean the same thing everywhere?

**Input:** Compiled concept lists from QW6
**Agent:** `gpt-xhigh` — reads concept lists AND the full book, checks each concept that appears in multiple chapters for meaning consistency.
**Check for:** meaning shift, terminology drift, contradictions, framing compression in later chapters.
**Fix:** Use tenet definitions (Core Tenets section above) as the reference for what concepts SHOULD mean. Rework drifted passages to match.

### QW8: Tenet Alignment Check

For every concept in the book, verify it traces to one or more of the 4 core tenets. Identify orphans that don't trace. Evaluate orphans: truly a new tenet, or a misframed instance of an existing one?

**Input:** Compiled concept lists from QW6, Core Tenets definitions
**Agent:** `gpt-xhigh` — performs alignment checks. The prompt must include the full tenet definitions from the Core Tenets section.
**Process:**
1. For each extracted concept, determine which tenet(s) it implements and at what layer
2. Identify concepts that don't cleanly trace to any tenet
3. For each orphan: evaluate whether it represents a genuinely new tenet or is a manifestation of an existing one
4. If it's a manifestation: show the connection and propose how to expand the tenet definition to cover it
5. If it's genuinely new: flag for user evaluation
**When uncertain:** Request concrete examples from the book or from the user to clarify what the concept is meant to be. Do not guess.
**Fix:** Rework misframed concepts to show their tenet connection. Expand tenet definitions where the connection is real but not yet captured. Flag genuinely new candidates for user decision.
**Output:** `.workspace/concepts/tenet-alignment.md`

### QW9: Coverage Gap Detection

Compare the book's concept coverage against the system-synthesis and known AI problems. Identify gaps where the book should teach something it currently doesn't.

**Input:** Tenet alignment results from QW8, `system-synthesis.md`
**Agent:** `gpt-xhigh` — focus on AI problems the system encounters, not software engineering techniques.
**Check for:** AI problems the system solves that the book doesn't teach, tenet strategies the book doesn't cover, missing layers where tenets should apply but don't.
**Output:** `.workspace/concepts/coverage-gaps.md` — each gap with: what's missing, which tenet it serves, which Part/Chapter it belongs in, whether it needs a new section or can be woven into existing content.

### QW10: Visualization Opportunity Assessment

Identify opportunities to explain concepts visually. Humans are visual — minimize text, maximize visualization. Text explains the WHY; visualization explains the HOW and the WHAT. Visualize whenever possible.

**Agent:** `gpt-xhigh` — reads each section, identifies what is being explained (a process, a structure, a comparison, an interaction, a flow, a relationship) and whether a diagram would explain it better than prose.
**Framing:** This is opportunity-driven, not gap-driven. The question is not "what's missing?" but "what could be communicated visually?" Default to visualizing — only leave as text when the concept is purely about reasoning or motivation (the why).
**Criteria:** Any how or what being explained in prose is a visualization opportunity. Processes, flows, structures, comparisons, interactions, relationships, lifecycles, hierarchies, state changes.
**Fix:** Add diagrams (use `gemini-high` for SVG generation). Reduce surrounding prose to the why — remove prose that restates what the diagram shows.

### QW11: Visual-Text Duplication Audit

Detect near-duplication between visuals (diagrams, tables) and their surrounding text. Visuals and text should complement each other, not restate the same information.

**Agent:** `gpt-xhigh` — reads each diagram/table and its surrounding text context (2-3 paragraphs before and after).
**Check for three duplication modes:**
1. **Diagram-text duplication** — the text fully restates what the diagram shows. Text should explain the WHY; the diagram should show the HOW/WHAT. If the text says everything the diagram says, either reduce the text or remove the diagram.
2. **Diagram-table duplication** — a diagram and table present identical information. Keep whichever communicates better; if both add value, ensure they show different facets (e.g., diagram shows structure, table shows details).
3. **Diagram-diagram duplication** — two visuals covering the same concept from the same angle. Merge or differentiate.

**Evaluate each visual with:**
- Does the surrounding text complement or restate the visual?
- Does the visual add spatial/structural insight the text cannot convey?
- If you removed the visual, would the text lose information? If you removed the text, would the visual be sufficient?
- Risk level (LOW/MEDIUM/HIGH) that the duplication wastes reader attention or causes confusion.

**Fix:** For MEDIUM+: either reduce the text to the why (remove restated how/what), restructure the table to show different information than the diagram, or remove the weaker duplicate.

### QW12: Text Quality Review (per-chapter, convergent)

Systematic text editing review. Run 6 practice-category reviews per chapter in parallel, fix findings, rerun until the chapter passes all 6.

**Process:** One chapter at a time. For each chapter:
1. Run all 6 review agents in parallel (`gpt-high`, one per practice)
2. Collect findings into a context file
3. Run `gpt-xhigh` edit agent to fix findings
4. Rerun reviews for the chapter
5. Repeat until all 6 reviews return PASS

**Practice categories** (review prompt templates in `/tmp/review-*.md`):

| # | Practice | Template | What it checks |
|---|----------|----------|----------------|
| P1 | Em-dash & punctuation | `review-emdash.md` | Em-dash frequency/alternatives, slash forms, parenthetical clutter |
| P2 | Prose mechanics | `review-prose.md` | Sentence/paragraph length, voice, person, topic sentences |
| P3 | Anti-patterns | `review-antipatterns.md` | Filler phrases, hedges, intensifiers, weak openers, opinion markers |
| P4 | Transitions | `review-transitions.md` | Chapter/section openers and closers, connectivity, forward references |
| P5 | Figure presentation | `review-figures.md` | Figure numbering, captions, cross-references, self-containment |
| P6 | Format decisions | `review-format.md` | Table vs prose vs diagram appropriateness, duplication |

**Runner script:** `/tmp/run-chapter-reviews.sh <ch_num> <ch_name> <start_line> <end_line>`
- Creates 6 stamped prompts in `/tmp/reviews/chN/`
- Runs all 6 via `agents --model gpt-high` in parallel
- Output in `/tmp/reviews/chN/{emdash,prose,antipatterns,transitions,figures,format}.out`

**Fix agent prompt structure:**
```bash
# Context file with all findings
cat > /tmp/reviews/chN/fix-context.md << 'EOF'
# Fix Context for Chapter N

## Findings to fix
[Collated findings from all 6 reviews — only actionable items, skip PASSes]

## Rules
- Make targeted edits only — do not rewrite content that wasn't flagged
- Match existing voice and tone
- Preserve meaning — fixes are about form, not substance
- When replacing em-dashes, choose the correct alternative (colon/semicolon/comma/parentheses) based on function
- When splitting sentences, ensure both parts can stand alone
- When adding figure labels, use "Figure X.Y" format
EOF
```

**Key rules derived from research (`gpt-high`):**
- Em-dashes: max 1/sentence, 2/paragraph, 3/page; no adjacent em-dash paragraphs
- Sentences: avg 15-25 words/section; flag >35 words; no 2+ consecutive >30
- Paragraphs: 3-7 sentences, 60-180 words; split >200
- Voice: 70%+ active; no 3+ consecutive passive
- Filler ban: "it is important to note that", "note that", "the fact that", "in order to"
- Intensifier ban: "very", "really", "quite", "extremely", "fairly", "rather"
- Figures: numbered (Figure X.Y), captioned (8-40 words, object + takeaway), referenced in text
- Transitions: every chapter opens with link-back + new objective; every section answers "why now?"

### QW13: Structural Editing Review (per-chapter, convergent)

Deep structural review for content quality. Unlike QW12 (surface-level mechanics), QW13 catches logical problems, reader comprehension issues, and argument structure flaws.

**Process:** One chapter at a time. For each chapter:
1. Run structural review agent (`gpt-high`) with the 6-category detection template
2. Collect findings (MUST-FIX and SHOULD-FIX)
3. Apply fixes with editorial judgment (`gpt-xhigh`)
4. Rerun review for the chapter
5. Repeat until findings are resolved

**Review categories** (template at `/tmp/review-structural.md`, guide at `structural-editing-guide.md`):

| # | Category | What it catches |
|---|----------|-----------------|
| S1 | KNOWLEDGE | Terms used before defined, overloaded words without cues, acronyms before expansion |
| S2 | SELF-REF | "This chapter...", positional references, ordinal scaffolding, meta-narration |
| S3 | REDUNDANCY | Term boxes repeating body text, duplicate definitions, captions restating paragraphs |
| S4 | COHERENCE | Adjacent capability/incapacity claims, negation-first framing, scope confusion |
| S5 | FIGURE | Multi-purpose figures, missing cross-references, placement issues, overloaded alt text |
| S6 | ARGUMENT | Sections feeling like list items, missing hinge sentences, positional transitions |

**Fix rules:**
- Structural fixes require editorial judgment, not mechanical replacement
- Term introduction: use generic phrase first, then name it when mechanism is visible
- Self-references: replace with claims, reader problems, or surprising failure cases
- Redundancy: each supplement (box, sidebar, callout) must have a distinct job from body text
- Coherence: scope both sides of claims; present core argument first, limitation as boundary
- Figures: one reader question per figure; split multi-purpose figures
- Arguments: name sections by concept, not count; end each with a hinge to the next

**Runner:** `/tmp/run-structural-reviews.sh` generates stamped prompts in `/tmp/reviews-structural/`

---

## Visual Creation Workflow

The book uses three tiers of visual content, each produced by a different model pipeline.

### Figure Type Decision: Pictures vs Diagrams

**Pictures** (Tier 2c illustrated figures) demonstrate **concepts** — metaphors, relationships, mental models. They work when the reader needs to *feel* or *intuit* something as a whole.

**Diagrams** (Tier 2 SVG) show **algorithms** — step-by-step processes, numbered sequences, decision flows, named hierarchies. They work when the reader needs to *follow* a procedure or *compare* specific named items.

**Decision rule:** If the figure shows a specific sequence of steps, a loop with named stages, or a hierarchy of named items — use a diagram. If it shows a metaphor, a relationship, or a concept the reader grasps as a gestalt — use a picture. When evaluating, ask: "Is this showing *what something is like* (concept → picture) or *how something works step-by-step* (algorithm → diagram)?"

### Tier 1: Diagrams (gpt-high)

Mermaid diagrams for system flows, architecture, and process illustrations. `gpt-high` generates the Mermaid source. Rendered via the diagram site.

```bash
# gpt-high generates mermaid source in prose editing sub-agents
# Diagrams go in execution-philosophy/diagrams/
```

### Tier 2: SVG Generation (Gemini — self-correcting)

Gemini generates SVG diagrams with a built-in visual review loop. Gemini writes the SVG, converts it to PNG, reads the PNG to visually inspect its own output, and fixes issues — all within a single invocation.

**Self-correcting workflow:**
1. **Generate** — Gemini writes the SVG to `diagrams/<name>.svg`
2. **Convert** — Gemini runs `python3 diagrams/svg_to_png.py <name>.svg /tmp/<name>-review.png --width 800`
3. **Visual inspect** — Gemini reads the PNG and checks for: arrow alignment to edges, text overlap, layout cleanliness, color/contrast
4. **Fix** — If issues found, Gemini edits the SVG and repeats from step 2
5. **Done** — Gemini outputs the final SVG file path

This eliminates the most common SVG failure modes (misaligned arrows, overlapping text, broken layout) without requiring human review of each iteration.

**Prompt template** — every Gemini SVG prompt must include:
```markdown
## Self-correction workflow
1. Write the SVG to /path/to/diagrams/<name>.svg
2. Run: python3 /path/to/diagrams/svg_to_png.py /path/to/diagrams/<name>.svg /tmp/<name>-review.png --width 800
3. Read /tmp/<name>-review.png and visually inspect
4. If arrows are misaligned, text overlaps, or layout is off — fix the SVG and repeat from step 2
5. Keep iterating until the diagram is clean
```

**Model selection:**
- `gemini-high` — first-pass generation of complex diagrams (cycles, multi-element layouts)
- `gemini-medium` — standard diagrams (ladders, spectrums, axes)
- `gemini-low` — quick iteration and visual review

```bash
# Self-correcting diagram generation
agents --model gemini-high --file /tmp/diagram-prompt.md --project .
```

### Tier 2b: Communication Risk Review (gpt-xhigh)

After Gemini's self-correcting loop produces a clean SVG, `gpt-xhigh` evaluates the diagram against the communication axis. The question: "What are the odds a reader will not understand this diagram in context?"

**Workflow:**
1. `gpt-xhigh` reads the rendered PNG + the surrounding text from the book
2. Evaluates: Does the diagram clarify or confuse? Does it match what the text explains? Will a reader unfamiliar with the concept understand it?
3. If communication risk is HIGH: feed specific issues back to Gemini for another self-correcting round
4. If LOW: diagram is ready for integration

This is risk assessment on the communication axis — not aesthetic judgment.

### Tier 2c: Illustrated Figure Pipeline (Gemini → Seedream i2i)

For book figures that need hand-drawn editorial illustration (not SVG diagrams). Gemini does ALL visual planning; seedream i2i generates the final image; `gpt-xhigh` does communication risk review.

**Art Style**: Friendly hand-drawn editorial illustration — soft rounded shapes, characters/people, pastel colors, cartoon-like but professional. NOT abstract geometric, NOT boxes-and-arrows, NOT photorealistic, NOT anime. Reference: `diagrams/hand-drawn-essay-illustration_23-2150314529.avif`.

**Pipeline steps:**

1. **Interpret** (`gemini-high`): Read surrounding book text + figure caption. Produce: one-sentence teaching intent, visual metaphor (real-world scene, NOT abstract), composition (asymmetry, S-curves, focal point, quiet zone per best practices), specific illustrated scenes as illustrator brief, labels needed.

2. **Create + validate composition SVG** (`gemini-high`): Single self-correcting call. Gemini creates a labeled wireframe SVG (2848x1600) showing WHERE everything goes — placement, sizes, spatial relationships. Asymmetric layout, varying element sizes, clear focal point, quiet zone for labels. Write to `diagrams/concept-art/{name}-composition.svg`. Within the same call: render to PNG via cairosvg, review the PNG, fix SVG errors, re-render, repeat until correct.

3. **Create + validate concept art SVG** (`gemini-high`): Single self-correcting call. Gemini creates a low-fi illustration SVG showing WHAT things look like — shapes, scenes, visual metaphors, simple cartoon characters. Write to `diagrams/concept-art/{name}-concept.svg`. Same self-correcting loop: render → review → fix → repeat.

4. **Generate** (`seedream-i2i`): Combine validated composition + concept art PNGs into one compressed JPEG (resize to ~1424px wide, quality 60 to avoid ARG_MAX). Feed to seedream i2i with prompt describing how to use each half. ALWAYS i2i, NEVER t2i — the visual plans ARE the input. Style directives in every prompt:
   - "hand-drawn editorial textbook illustration, cartoon style, flat colors with ink outlines"
   - "NOT photorealistic, NOT 3D render, NOT anime"
   - "No text no words no labels no letters" (labels added in post)
   - Do NOT pass the style reference image to seedream — it copies characters literally

5. **Communication Risk Review** (`gpt-xhigh`): evaluates the generated image against the communication axis AND the engagement axis. Pass: the generated image, surrounding book text, figure caption, AND `research/figure-best-practices.md`. The reviewer must assess:
   - Communication: Could a reader misinterpret? What's confusing, broken, contradictory?
   - Engagement: Does the figure follow best practices (asymmetry, varying sizes, visual rhythm, depth cues)? Would a reader skip it because it's visually dead?
   - The risk assessor must understand that visual engagement rules (S-curves, asymmetry, winding paths) serve reader attention even when the text describes "linear" processes. Figures are not literal translations of text — they are visual communication with their own rules.
   - Rating: PASS or FAIL with specific issues.

6. **Fix/Iterate**: If FAIL — go back to step 2 and fix SVG inputs. Do NOT try to fix the raster image directly. Seedream output is not correctable; SVGs are. Re-run from step 4.

7. **Labels** (optional, `gemini-high`): Only add labels when they name **specific artifacts** in the image (e.g., "1. Requirements", "The Spec"). Do NOT add labels that narrate the situation or describe the concept — that's what the caption does. If the figure communicates clearly with just the caption and surrounding text, skip labels entirely. When labels are needed: SVG text overlay, cairosvg → RGBA PNG, PIL alpha_composite. Font: Nunito (`~/.local/share/fonts/Nunito-Variable.ttf`), white outline for readability.

8. **Verify labels** (if added, `gemini-high`): Gemini reviews composited image, confirms labels are readable and correctly positioned. Fix SVG overlay and re-composite if needed.

9. **Optimize PNG**: Reduce file size before embedding in the book. Raw seedream output is ~6-8 MB per figure; optimized output is ~300-700 KB (90%+ reduction) with no visible quality loss.

   ```python
   from PIL import Image
   img = Image.open("diagrams/fig-X-Y-name.png")
   # Resize to 1424w (4.75" at 300 DPI — sufficient for book pages)
   ratio = 1424 / img.width
   resized = img.resize((1424, int(img.height * ratio)), Image.LANCZOS)
   # Quantize to 256-color palette (like pngquant) with dithering
   quantized = resized.quantize(colors=256, method=2, dither=1)
   quantized.save("diagrams/fig-X-Y-name.png", optimize=True)
   ```

   - Skip files already under 1 MB (SVG-converted diagrams, already-optimized figures)
   - Keep raw originals in `-raw` files for full-resolution recovery
   - Apply to cover art and header images too (keep original dimensions, just quantize)
   - The hand-drawn editorial style with flat colors and ink outlines compresses exceptionally well to 256-color palette — dithering hides the reduction

**Key constraints:**
- Gemini does ALL visual work (interpretation, SVGs, labels). Text-first review models are not the visual art-direction authority.
- Gemini and seedream can both run in parallel.
- Validation happens at the SVG stage (steps 2, 3) — SVGs are correctable, seedream output is not.
- Best practices reference: `research/figure-best-practices.md` — asymmetry over symmetry, varying sizes, S-curves, labels near what they depict, no uniform repeated shapes.

**File locations:**
- `diagrams/concept-art/{name}-composition.svg` — Gemini composition layouts
- `diagrams/concept-art/{name}-concept.svg` — Gemini concept art
- `diagrams/fig-{chapter}-{number}-{name}.png` — Final generated figures

### Tier 3: Image Generation (Seedream)

**Text-to-image** — for cover art textures and standalone illustrations only (NOT for book figures — use Tier 2c pipeline):
```bash
agents --model seedream-t2i "A detailed pattern texture..."
```

**Image-to-image** — for the figure pipeline (Tier 2c step 4):
```bash
agents --model seedream-i2i \
  -i image=diagrams/concept-art/fig-combined.jpg \
  -i size=2848*1600 \
  "prompt describing what to generate..."  > diagrams/fig-output.png
```

### Tier 4: Video Generation (Seedance)

For animated explanations of processes, flows, and state changes. Takes text or image input.

```bash
# Animate a diagram
agents --model seedance-i2v '{"prompt": "Slowly animate the flow: highlight each node in sequence as data moves through the pipeline, smooth transitions", "image": "/path/to/diagram.png"}'
```

### Visual Pipeline Summary

```
Gemini (SVG, self-correcting) ─── generate → convert → inspect → fix → repeat
  ↓ clean SVG
gpt-xhigh (communication risk) ─ evaluate diagram + text context on communication axis
  ↓ approved or fed back to Gemini
Gemini (art direction) ──────── write Seedream prompts for image generation
Seedream (Image) ────────────── photorealistic / textured images from Gemini prompts
  ↓ raw PNG (~6-8 MB)
PIL (optimize) ──────────────── resize 1424w → quantize 256 colors → optimize (~300-700 KB)
Seedance (Video) ────────────── animated explanations from text or image
```

### Model Selection for Visual Tasks

| Visual need | Model | Reasoning |
|-------------|-------|-----------|
| Complex diagram (cycles, multi-element) | `gemini-high` (self-correcting) | Needs high reasoning for layout |
| Standard diagram (ladders, spectrums) | `gemini-medium` (self-correcting) | Balance of quality and speed |
| Quick SVG iteration / review | `gemini-low` | Speed over polish |
| Communication risk review | `gpt-xhigh` | Evaluates diagram clarity in context |
| Art direction for Seedream | `gemini-high` | Creative brief → image prompt |
| Photorealistic illustration | `seedream-t2i` | Text-to-image for standalone visuals |
| Polish an SVG into a final image | `seedream-i2i` | Image-to-image refinement |
| Animate a concept (quality) | `seedance-t2v` / `seedance-i2v` | 1080p, $0.052/s |
| Animate a concept (cheap) | `seedance-t2v-fast` / `seedance-i2v-fast` | v1.5 Pro Fast, 720p, $0.02/s |
| Animate a concept (cheapest) | `seedance-t2v-low` / `seedance-i2v-low` | v1 Pro Fast — use for drafts and iteration |

### Utility Scripts

| Script | Purpose |
|--------|---------|
| `diagrams/svg_to_png.py` | Convert SVG → PNG via cairosvg. Used by Gemini's self-correcting loop. |
| `diagrams/review_svg.sh` | Standalone visual review loop (alternative to embedding in Gemini prompt). |

---

## When to Ask the User

Only stop and ask the user when you need their input on a **concept definition** — what a concept means, how tenets interact, whether something is a new tenet. The user answers questions about concepts. Nothing else requires stopping.

Do not stop to:
- Show progress or ask for approval on edits
- Confirm before running workflows
- Present intermediate findings
- Ask permission to continue

Run the full workflow chain. Fix stability issues. Fill coverage gaps. Update prose. Regenerate PDF. Only pause if you genuinely cannot determine what a concept is supposed to mean and need the user to clarify.

---

## Workflow Ordering

Workflows build on each other. The recommended order:

1. **QW1** (Concept Registry) — foundation for all text-level checks
2. **QW6** (Concept Extraction) — foundation for stability and alignment checks
3. **QW7** (Stability Analysis) — identifies meaning drift
4. **QW8** (Tenet Alignment) — identifies orphan concepts and misframings
5. **QW9** (Coverage Gaps) — identifies missing content
6. **QW2-QW5** (Dependency, Framing, Repetition, Communication Values) — text-level quality
7. **QW10** (Visualization) — structural diagrams
8. **QW11** (Visual-Text Duplication) — catches diagram/text redundancy
9. **QW12** (Text Quality) — per-chapter prose polish (em-dashes, style, transitions, figures)
10. **QW13** (Structural Editing) — per-chapter deep review (knowledge management, coherence, argument structure)

After fixing stability (QW7) and alignment (QW8) issues, re-run QW6-QW8 to verify fixes didn't introduce new drift. QW12 and QW13 run last because they operate on final prose — running them before content changes wastes effort. QW13 should run before QW12 since structural changes may introduce new mechanical issues.

## Model Assignments

| Task Type | Model | Why |
|-----------|-------|-----|
| Auditing (systematic cross-referencing) | `gpt-xhigh` | Best at exhaustive search across large documents |
| Concept extraction | `gpt-high` | Fast, accurate summarization |
| Alignment checks | `gpt-xhigh` | Best at evaluating whether concepts trace to principles |
| Stability analysis | `gpt-xhigh` | Cross-referencing meaning across sections |
| Coverage gap detection | `gpt-xhigh` | Cross-referencing book against system |
| Text quality review (per-chapter) | `gpt-high` | Parallel practice reviews, mechanical rule checking |
| Structural editing review | `gpt-high` | Deep content review (knowledge, coherence, argument) |
| Text quality fixes | `gpt-xhigh` | Targeted edits matching existing tone |
| Structural editing fixes | `gpt-xhigh` | Editorial judgment for content-level rewrites |
| Editing prose | `gpt-xhigh` | Best at targeted edits matching existing tone |
| Mermaid diagrams | `gpt-xhigh` | Structural accuracy for system flows |
| SVG visual planning / art direction | `gemini-high` | Best SVG generation, high reasoning for visual design |
| SVG iteration | `gemini-low` / `gemini-medium` | Speed for refinement cycles |
| Visual risk review | `gpt-xhigh` | Communication + engagement risk (must receive best practices as context) |
| Figure interpretation / composition / concept art / labels | `gemini-high` | All visual planning — self-correcting SVG loops |
| Figure generation | `seedream-i2i` | Transform composition + concept art into illustrated figures |
| Cover art textures | `seedream-t2i` | Standalone texture/pattern generation only |
| Text-to-video (quality) | `seedance-t2v` | 1080p animated concept explanations ($0.052/s) |
| Text-to-video (cheap) | `seedance-t2v-fast` | 720p drafts and iteration ($0.02/s) |
| Image-to-video (quality) | `seedance-i2v` | 1080p animate existing diagrams/images ($0.052/s) |
| Image-to-video (cheap) | `seedance-i2v-fast` | 720p drafts and iteration ($0.02/s) |
| Text-to-video (cheapest) | `seedance-t2v-low` | Seedance v1 Pro Fast — lowest cost |
| Image-to-video (cheapest) | `seedance-i2v-low` | Seedance v1 Pro Fast — lowest cost |
| Research | `gpt-high` | Fast web search and synthesis |
