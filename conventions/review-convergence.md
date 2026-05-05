# Review Loop Convergence — Decomposition as a Hard Signal

When a multi-round review loop (Phase 4 risk gates, Phase 7 CodeRabbit
loop, Phase 8 PR review gates) keeps surfacing new findings each
round rather than closing prior findings to a stable terminal verdict,
that is **not** a sign to push through more rounds. It is a hard
signal that the artifact under review is too large for the review
process to reliably converge.

The correct response is **decomposition**, not iteration.

## Why this happens

Review-time LLM agents have a bounded effective reasoning surface.
When a diff (or proposal) exceeds that surface, the reviewer
"skim-misses": each round catches some findings the prior round
missed, while missing new ones the prior round caught. The result is
a non-terminating fix loop where the round count grows but no round
ever returns LOW with zero new findings.

This is observable as:

- Round N closes M findings; Round N+1 introduces M' previously-unseen
  findings on the unchanged-or-shrunk surface.
- The classification of findings changes between rounds (a hunk that
  was LOW in round 1 returns as MEDIUM in round 3).
- Each fix dispatch introduces small new drift the prior dispatches
  did not.

It is **not** an artifact of agent quality, prompt quality, or
contract tightness. It is a function of diff size relative to the
reviewer's reasoning surface.

## When the convergence trigger fires

Treat any of these as a hard decomposition trigger:

1. **Three consecutive rounds with new findings** that were not
   present in any prior round on the same artifact.
2. **A round whose new-findings count exceeds the prior round's
   closures count** (more findings opened than closed).
3. **A round that re-classifies a prior LOW item as MEDIUM/HIGH**
   without a substantive change to that item.
4. **A `MAX_PASSES_REACHED` outcome** from `coderabbit-operator` or
   any equivalent loop operator with non-empty residual findings.

## Action when the trigger fires

1. **Stop the current round of fixes.** Do not dispatch another
   revert or remediation against the same diff.
2. **Run the Multi-Concern review explicitly** per
   `~/ai/workflows/pr-review.md`. Even if a prior multi-concern
   round returned `SINGLE_CONCERN`, re-run it against the post-fix
   diff: convergence failure is itself evidence that the diff is
   multi-concern in practice.
3. **Decompose the work**. Split by:
   - Vertical seams (e.g., per-trait, per-module, per-feature).
   - Behavior-preserving refactor vs. behavior-changing fix
     (always two PRs minimum).
   - Test additions vs. product changes (if the project's
     workflow allows).
4. **Land each piece as its own PR** with its own complete review
   cycle (Phase 4 → 7 → 8 → merge). Each smaller PR converges
   reliably; the cumulative result is the same as the original
   umbrella, delivered in pieces.
5. **Update audit history** to record the decomposition trigger,
   the trigger evidence, and the chosen decomposition shape.

## Relation to existing conventions

This rule is the operational consequence of two existing rules:

- `~/ai/workflows/implementation-pipeline.md` Phase 4: "Risk drives
  decomposition. Do not decompose because something looks complex;
  decompose when audit or alignment risk exceeds what one agent can
  reliably handle."
- `~/ai/workflows/pr-review.md` Multi-Concern Review:
  "MULTI_CONCERN_RECOMMEND_SPLIT — the diff should be decomposed.
  Identify each concern, the files or lines involved, and the
  dependency order."

This convention adds the *operational signal* that authorizes the
trigger: the loop's own non-convergence is the evidence that the
risk has exceeded the single-agent reasoning surface. The split is
not a courtesy; it is required.

## Anti-pattern

The opposite of this convention — "keep grinding rounds, eventually
LOW will appear" — is **not** authorized. The cost of additional
rounds is unbounded; the marginal close-rate per round is
demonstrably below 100% by the time the trigger fires. Every
additional round risks introducing new drift through the very
fix dispatches meant to close prior drift.

If you find yourself dispatching round 4+ on the same artifact, the
correct mental model is "I have already failed to close this in 3
rounds; the artifact is too large; further iteration is more
expensive than the split."
