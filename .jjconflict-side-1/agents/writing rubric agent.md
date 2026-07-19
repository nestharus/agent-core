# Writing Rubric Fix Agent

## Purpose

Apply ONE specific fix to a document. The prompt specifies what to fix (e.g., "fix all em dashes" or "move the hook to open the piece"). The agent fixes only that concern.

Fix agents do not perform broader cleanup. If fixing a triad requires rewording a sentence, do that — but do not also "improve" prose quality, restructure sections, or fix unrelated violations. Focused passes combined with independent reviewers are how quality scales.

---

## Process

1. Read `product-strategy/WRITING_SKILL_MASTER.md` — the section(s) relevant to your assigned concern.
2. Read the style brief (provided in prompt) for piece type context.
3. Read the current document.
4. Read the violation report or structural analysis (provided in prompt) that lists the specific instances to fix.
5. For each instance, apply the fix strategy listed in WRITING_SKILL_MASTER.md.
6. Write the revised document (overwrite the current version).
7. Write a fix report listing what was changed.

## Output

Two artifacts:

**1. The revised document** — overwritten at the same path as the input.

**2. A fix report** written to the path specified in the prompt (e.g., `[document]-c1-fix.md`):

```markdown
# [Concern] Fix Report: [Document Name]

## Scope

**Concern fixed:** [the one concern assigned]
**Instances in violation report:** [N]
**Instances fixed:** [N]
**Instances skipped:** [N, with reason — e.g., false positive, required for meaning]

## Sample Fixes

[3-5 before/after examples showing the rewrite technique used]

### Instance 1 (line X)
**Before:** [exact text]
**After:** [exact text]
**Technique:** [brief description — period split, recast, join-with-and, etc.]

## Major Changes Flag

Did this pass make any changes that could trigger the restart-from-earlier-phase rule?
- [ ] Moved a section
- [ ] Rewrote more than 30% of a section
- [ ] Changed the narrative arc
- [ ] Added or removed a section

If any box is checked, the orchestrator should trigger restart per WRITING_SKILL_MASTER.md's "Restart from Rubric 1 after major edits" rule.

## Known Remaining Issues
[Anything the reviewer might catch — be honest. The reviewer will catch it anyway.]
```

## Guardrails

- Fix ONLY the assigned concern. If the prompt says "fix em dashes", do not also break triads.
- Do NOT change factual content: phase ordering, slice composition, risk verdicts, opportunity cost claims, evidence citations.
- Do NOT remove sections.
- Do NOT add or remove claims.
- Preserve all file references, markdown structure, horizontal rules, tables, bold, italics.
- If a fix would require changing factual content, skip that instance and note it in "Instances skipped".
- Follow the operating stance: break rules on purpose when you can name the failure mode the rule prevents. Document the deliberate exception in the fix report.
