---
workflow:
  id: writing pipeline orchestrator
workflow_dispatch_contract:
  orchestrator: "writing pipeline orchestrator"
  inputs:
    - "draft public-facing document, writing craft reference, communication research, and reviewer/fixer prompt files"
    - "human approval for content additions before mechanical and editorial phases proceed"
  expectations:
    - "runs content, analysis, mechanical-ban fixes, editorial fixes, rubric fixes, and quality gate as separate agent invocations"
    - "uses reviewers to verify fixes after each category rather than allowing agents to self-review"
  outputs:
    - "editing reports for each pipeline phase"
    - "review reports for each fix category"
    - "final quality gate report"
  non_goals:
    - "does not merge separate violation categories into one fixing agent"
    - "does not let reviewers mutate the document"
    - "does not bypass the human content gate"
---
# Writing Pipeline Orchestrator

## Purpose

Take a draft public-facing document and run it through a properly decomposed multi-agent quality pipeline. Every violation category, every structural concern, and every rubric sub-check is a separate agent invocation, followed by a reviewer that verifies the fix landed.

Each step is a separate agent invocation. Agents do not self-review. Reviewers do not fix.

---

## Reference Files

| File | Role |
|---|---|
| `WRITING_SKILL_MASTER.md` | Writing craft reference — rubrics, bans, tempo |
| `research/exec-roadmap-communication.md` | Executive roadmap communication research |
| `research/pitch-deck-communication.md` | Pitch deck communication research |
| `writing content agent.md` | Content revision agent instructions |
| `writing rubric agent.md` | Rubric fix agent template (parameterized per concern) |
| `writing rubric reviewer agent.md` | Reviewer template (verifies each fix) |
| `writing editorial agent.md` | Tempo and editorial agent instructions |
| `writing quality gate agent.md` | Final quality verification agent instructions |

---

## Pipeline

### Phase A: Content Revision

Adds sections the target audience needs from communication research.

**A1. Content revision** (`gpt-xhigh`) — adds missing sections. Writes editing report.
**Human gate** — user approves content additions.

### Phase B: Analysis (parallel, read-only)

**B1. Skeleton extraction** (`gpt-high`) — heading outline, first sentences, borders, structural issues.
**B2. Non-negotiable scan** (`gpt-high`) — full violation inventory by category with line references.

These run in parallel. Neither modifies the document.

### Phase C: Mechanical Ban Fixes (sequential, one category at a time)

Each category gets its own fix agent + reviewer. Running one category per agent keeps attention focused. Running sequentially (not parallel) avoids conflicting edits on the same file.

Per category, the fix pass: read violation report filtered to this category → fix every instance → report what was changed. Then the review pass: scan document fresh for the same category → report any remaining instances.

**C1. Em dash fixes** (`gpt-xhigh` fix → `gpt-high` reviewer)
**C2. Banned opener fixes** (`gpt-xhigh` fix → `gpt-high` reviewer)
**C3. Triad fixes** (`gpt-xhigh` fix → `gpt-high` reviewer)
**C4. Pseudo list fixes** (`gpt-xhigh` fix → `gpt-high` reviewer)
**C5. Repeated opener fixes** (`gpt-xhigh` fix → `gpt-high` reviewer)
**C6. Repeated frame fixes** (`gpt-xhigh` fix → `gpt-high` reviewer)
**C7. Cliche fixes** (`gpt-xhigh` fix → `gpt-high` reviewer)
**C8. Moralizing/status fixes** (`gpt-xhigh` fix → `gpt-high` reviewer)
**C9. Performative sentence fixes** (`gpt-xhigh` fix → `gpt-high` reviewer)
**C10. Hedging fixes** (`gpt-xhigh` fix → `gpt-high` reviewer) — only if B2 found any
**C11. Filler/throat-clearing fixes** (`gpt-xhigh` fix → `gpt-high` reviewer) — only if B2 found any

If a reviewer finds remaining violations in its category, the orchestrator re-runs the fix agent with the reviewer's findings. Iterate until the reviewer returns no remaining violations.

**C12. Full ban rescan** (`gpt-high`) — runs the full non-negotiable scan again on the document after all category fixes. If new violations appeared (the fix passes can introduce new ones), route them to the appropriate category fix agent.

### Phase D: Story Beats — Structural Fixes (sequential, one concern at a time)

Each structural concern from the skeleton analysis gets its own fix agent + reviewer.

**D1. Hook placement** (`gpt-xhigh` fix → `gpt-xhigh` reviewer) — does the opening create tension tied to the hypothesis?
**D2. Reframe consolidation** (`gpt-xhigh` fix → `gpt-xhigh` reviewer) — is the reframe stated once, crisply, early?
**D3. Container section framing** (`gpt-xhigh` fix → `gpt-xhigh` reviewer) — do container sections have framing prose?
**D4. Border bridges** (`gpt-xhigh` fix → `gpt-xhigh` reviewer) — per specific border flagged in skeleton analysis
**D5. Table framing** (`gpt-xhigh` fix → `gpt-xhigh` reviewer) — do tables have prose making their argument explicit?

Reviewers use `gpt-xhigh` because structural quality is judgment, not pattern-matching.

### Phase E: Flow and Cohesion (Rubric 3)

**E1. Paragraph cohesion pass** (`gpt-xhigh` fix → `gpt-xhigh` reviewer) — each paragraph develops one idea, known-to-new pattern.
**E2. Causality pass** (`gpt-xhigh` fix → `gpt-xhigh` reviewer) — every major claim has a concrete "because".
**E3. Cognitive load pass** (`gpt-xhigh` fix → `gpt-xhigh` reviewer) — concrete before abstract, cash out implications.

### Phase F: Adversarial Robustness (Rubric 4)

**F1. Intent alignment** (`gpt-xhigh`) — writes private sentences (not published), disciplines scope.
**F2. Pushback pass** (`gpt-xhigh` fix → `gpt-xhigh` reviewer) — strongest objection addressed.
**F3. Worst case reader test** (`gpt-xhigh` fix → `gpt-xhigh` reviewer) — hostile reader accusation preempted or contained.
**F4. Quote test** (`gpt-xhigh` fix → `gpt-xhigh` reviewer) — 3 random sentences, revise any usable against intent.
**F5. Evidence toggle** (`gpt-xhigh` fix → `gpt-xhigh` reviewer) — every empirical claim cited, labeled hypothesis, or labeled anecdote.

### Phase G: Editorial

**G1. Soft AI tells rescan** (`gpt-high`) — find remaining comma-heavy sentences, repeated structures, parallel overuse, default negative language, closure signals.
**G2. Soft tell fixes** (`gpt-xhigh` fix → `gpt-high` reviewer).
**G3. Tempo pass** (`gpt-xhigh` fix → `gpt-xhigh` reviewer) — metronomic cadence, rhythm device clusters, rationed pattern budgets.
**G4. Tightening pass** (`gpt-xhigh` fix → `gpt-xhigh` reviewer) — compression, tone consistency.

### Phase H: Restart Check

Orchestrator reads all editing reports from D-G. If any fix made major structural changes (moved sections, rewrote >30% of a section, changed narrative arc), restart from Phase C (ban rescan is cheap, structural fixes may have introduced violations).

Restart from Phase C as needed until no major structural changes are introduced; then proceed to Phase I.

### Phase I: Quality Gate

**I1. Independent quality gate** (`gpt-xhigh` — a fresh agent that did NOT participate in any earlier stage) — runs the Final Check from WRITING_SKILL_MASTER.md plus document-type-specific checks. Returns PASS or FAIL with specific findings.

If FAIL: orchestrator identifies which phase's concern failed, re-runs that phase's fix agent with the gate's findings, re-runs the gate.

### Phase J: PDF Render

Once gate passes, `python3 scripts/render-pitch-deck.py "product-strategy/[document].md"`.

---

## Model Selection

| Agent type | Model | Rationale |
|---|---|---|
| Content revision | `gpt-xhigh` | Strategic judgment, adding substantive content |
| Skeleton / scan agents | `gpt-high` | Pattern matching, high controllability |
| Mechanical ban fixes | `gpt-xhigh` | Creative rewriting to preserve meaning |
| Mechanical fix reviewers | `gpt-high` | Pattern detection, high controllability |
| Structural fixes (D/E/F) | `gpt-xhigh` | Writing judgment |
| Structural reviewers | `gpt-xhigh` | Judgment, not pattern matching |
| Editorial | `gpt-xhigh` | Voice and rhythm |
| Quality gate | `gpt-xhigh` | Independent judgment |

---

## Prompt Construction

Each agent runs from a prompt in `.tmp/` constructed by the orchestrator at runtime. The prompt combines:
1. The agent template (`writing rubric agent.md` or `writing rubric reviewer agent.md`)
2. The specific concern or category assigned
3. The style brief for the document type
4. References to the source documents the agent reads
5. Previous stage outputs (violation reports, skeleton analysis, prior fix reports)

Prompts named `[phase-stage]-[doctype].md` (e.g., `c1-fix-exec.md`, `c1-review-exec.md`).

---

## Why So Many Agents

Each sub-concern is genuinely distinct work:
- Fixing 118 em dashes is mechanical, repeatable, needs thoroughness
- Fixing a hook placement is a judgment call about narrative
- Fixing table framing is local rhetorical work
- Fixing cognitive load is paragraph-by-paragraph judgment

Bundling them into one agent produces: the agent runs out of attention after the first few categories, fixes some violations well and others poorly, declares victory before finishing. Separate agents with reviewers keeps each pass focused on one thing and catches what slipped through.

The cost is time and token usage. For a 635-line public-facing document reviewed by investors or executives, that cost is warranted.
