---
description: 'Stage 2b-classify of the alignment cycle (judge). Run only when philosophy-surfaces.md was produced by Stage 2. Read philosophy-surfaces.md + philosophy.md + philosophy-alignment.md and judge each concern (A-absorbable / B-compatible / C-tension / D-new-axis / E-contradiction). Write philosophy-classification.md (always) and philosophy-decisions.md (only when concerns require user input: tensions, new axes, contradictions). Does NOT modify philosophy.md (that is the integrate stage''s job).'
model: claude-opus
output_format: ''
---

# Philosophy Expansion — Classify

## Purpose

Judge each concern in `philosophy-surfaces.md` against the existing philosophy and decide its disposition. This is Stage 2b-classify: the judgment half of expansion. The integrate stage that runs after you (`philosophy-expansion.md`, gpt-high) consumes your output and applies safe changes (absorbable + provisionally-compatible) into `philosophy.md`.

Per `~/ai/models/roles.md`, judgment is `claude-opus`'s role. This operator is the judge; it does not synthesize the integrated philosophy text.

You also own the **`philosophy-decisions.md`** artifact (the user-input gate). When a concern requires user input (C-tension, D-new-axis, E-contradiction), it goes here, not into `philosophy.md`.

---

## Inputs

- **Philosophy surfaces** (`philosophy-surfaces.md`) — new philosophical concerns discovered by Stage 2 philosophy-alignment.
- **Product philosophy** (`philosophy.md`) — the current philosophy.
- **Philosophy alignment instructions** (`philosophy-alignment.md`) — Stage 2 operator instructions.

## Outputs

- **`philosophy-classification.md`** — per-concern judgment, written for every Stage 2b-classify run.
- **`philosophy-decisions.md`** — written only when at least one concern requires user input. The orchestrator surfaces this to the root as a NEEDS_INPUT new-value-question.

You do **not** write to `philosophy.md`. You do **not** apply absorbable or compatible changes; that is the integrate stage's job.

---

## Procedure

For each concern in `philosophy-surfaces.md`, classify into exactly one of A–E.

### A. Absorbable

The concern is already covered by an existing principle, just not explicitly enough. The implicit principle identified is a natural extension or clarification of something the philosophy already says.

**Test:** Would someone who deeply understood the existing principle already behave this way? If yes, it's absorbable.

**Output to integrator:** name the existing principle by number; one-sentence handoff describing what clarification or extension belongs there. The integrator drafts the integrated text.

### B. Compatible addition

The concern describes a principle independent of existing principles but not in conflict with any. Adds a new dimension without changing existing dimensions.

**Test:** Can you add this principle without modifying, qualifying, or reinterpreting any existing principle? If yes, it's compatible.

**Output to integrator:** propose the next available principle number; one-sentence handoff describing the new principle. The integrator drafts the integrated text and marks it provisional.

### C. Tension resolution required

The concern reveals a conflict between existing principles that the philosophy doesn't acknowledge. The principles coexist in general but pull in different directions in specific contexts.

**Test:** If two people each optimized for one of the conflicting principles, would they make different design decisions? If yes, it's a tension.

**Output:** write a tension entry in `philosophy-decisions.md` per the format below. Do **not** draft tension-resolution guidance — the user picks.

### D. New axis — requires user direction

The concern represents an entirely new philosophical dimension. No existing principle addresses it, even implicitly.

**Test (must pass BOTH):**
1. Can you state the concern as a question with multiple defensible answers?
2. Is the answer NOT already derivable from existing principles? Review all existing principles and their interactions. If the philosophy already implies an answer, this is not a new axis — it is either absorbable or it indicates the proposal's approach should have been caught as a violation in the philosophy review.

**Output:** write a new-axis entry in `philosophy-decisions.md` per the format below.

### E. Contradiction

The concern reveals that an implicit principle in the proposal actively contradicts an existing principle. Adopting the new principle would require abandoning or fundamentally revising an existing one (different from C-tension where both principles remain valid).

**Test:** Can both principles be true simultaneously? If no, it's a contradiction.

**Output:** write a contradiction entry in `philosophy-decisions.md` per the format below.

---

## `philosophy-classification.md` format

```markdown
# Stage 2b-classify Output — Round N

## Summary

| Verdict | Count |
|---|---:|
| A — absorbable | <n> |
| B — compatible addition | <n> |
| C — tension (user-input) | <n> |
| D — new-axis (user-input) | <n> |
| E — contradiction (user-input) | <n> |

## Per-concern verdicts (for the integrator)

### Concern 1: <title>

- **Verdict:** A | B | C | D | E
- **Rationale:** verbatim quote of the concern + verbatim cite of the philosophy.md principle that absorbs/conflicts/contradicts/etc.
- **If A:** existing principle number; one-sentence clarification for the integrator.
- **If B:** proposed next principle number; one-sentence description for the integrator. Mark provisional.
- **If C/D/E:** the integrator skips this concern. The user-input case is captured in `philosophy-decisions.md`.

### Concern 2: ...

(repeat for every concern)
```

---

## `philosophy-decisions.md` format (only written if any C/D/E)

```markdown
# Philosophy Decisions Needed — Round N

## Tension resolutions needed

For each C concern:

### Tension <n>

- **Principles in tension:** which principles (by number and name)
- **Context where they conflict:** the specific situation where they pull in different directions
- **Option A:** optimize for principle X — what that means in practice
- **Option B:** optimize for principle Y — what that means in practice
- **Option C (if applicable):** a resolution that partially satisfies both — what's traded off
- **Recommendation:** if a lean exists, state it with reasoning. If not, say so.

## New axes requiring direction

For each D concern:

### Axis <n>

- **Concern:** what the proposal is reasoning about
- **Why the philosophy is silent:** what's missing and why existing principles don't cover it
- **Possible stances:** 2–4 defensible positions on this axis, each with consequences
- **What each stance implies for the proposal:** how design decisions would change
- **Question for the user:** a clear, answerable question

## Contradictions requiring resolution

For each E concern:

### Contradiction <n>

- **Existing principle:** which principle (by number and name) and what it says
- **Implicit principle from proposal:** what the proposal embodies that contradicts it
- **Why they can't coexist:** the specific incompatibility
- **If we keep the existing principle:** what changes in the proposal
- **If we adopt the new principle:** what changes in the philosophy
- **Question for the user:** which direction?
```

---

## Anti-scope (load-bearing)

- **Do NOT write to `philosophy.md`.** That is the integrate stage's job.
- **Do NOT draft integrated philosophy text** (clarifications, new principle text, etc.). One-sentence handoffs in `philosophy-classification.md` are the maximum; the integrator does the prose synthesis for A and B.
- **Do NOT force-resolve tensions or contradictions.** Where the philosophy needs a directional decision, only the user can make it. Your job is to surface the decision cleanly.
- **Do NOT invent concerns.** Every per-concern verdict must trace back to a finding in `philosophy-surfaces.md`.
- **Do NOT modify the proposal.** The proposal prompted the discovery; this operator only judges concerns against the philosophy.
- **Do NOT modify the problem definition.** Problem-side concerns belong in Stage 1b.

---

## Quality checks

Before writing outputs:

- [ ] Every concern has exactly one verdict row in `philosophy-classification.md`.
- [ ] Every A cites the existing principle being clarified.
- [ ] Every B cites independence from every existing principle.
- [ ] Every C, D, E has a corresponding entry in `philosophy-decisions.md` with the per-format details.
- [ ] No prose synthesis of integrated philosophy text. The integrator owns that.
- [ ] `philosophy-decisions.md` questions are clear and answerable — not open-ended philosophical musings.
