# Initiative 02b — Tests first-ness evidence mechanism

**Status:** deferred (decompose spawn from Initiative 02)
**Depends on:** Initiative 01 (landed) **plus** an explicit disposition vocabulary for "partial firstness evidence"
**Blocks:** —
**Spawned from:** Initiative 02 round-2 review (`L-01` two-generation oscillation in the firstness-artifact chain `J-05 → K-02 → L-01`). See `~/ai/.build/A18-tests-proposal-review-v3.md §6`.

## Problem

Initiative 02 set out to add, among other things, **diff-time evidence that tests were encoded before implementation** (constraint 1: tests first). Every attempt to pin a mechanism spawned a sibling-site gap in the same rule-block area:

- **J-05** (round 0): firstness cannot be verified from a PR diff alone; partial mitigation requested.
- **K-02** (round 1): v2 added a Step 6b output (`tests/NN-behavior-*.md` / `Step-6b-tests-before-code:` commit marker) and a Test Audit cross-check, but v2 did not specify what happens when both are absent.
- **L-01** (round 2): v3 added the absence-handling sentence, but it routes the firstness gap into a "ship-with-residual disposition" and an implicit "revise-and-rerun" — neither of which exists in landed `~/ai/` files (verified via grep). The K-02 fix produced the very wording that v3 had to resolve in a routing vocabulary the proposal did not formally introduce and Init-01 did not land.

The two-generation oscillation is **area-based**: three consecutive rounds, same rule-block area, each fix opens a sibling-site gap. Per the project methodology ("keep revising until low; decompose on oscillation"), this is the canonical decompose signal.

## Precondition for opening this initiative

Before restarting review, settle the disposition vocabulary that the firstness mechanism depends on. Concretely:

1. **Partial-firstness disposition.** What does the workflow do when a firstness artifact is partially present (e.g., the commit marker exists but `tests/NN-behavior-*.md` is absent, or vice versa)? The valid dispositions are:
   - `revise and re-run` — firstness gap triggers the writer to re-author tests before implementation, then re-run Test Audit.
   - `ship with named residual` — firstness gap is accepted on the Init-01 value-termination path, recorded in the ship-with-residual disposition register.
   - `terminate` — firstness gap alone stops the PR per Init-01's non-positive-value termination.

2. **Test-Audit routing.** The disposition decides whether Test Audit classifies the gap as a soft finding (synthesized into the PR comment) or a hard stop (blocks the PR). This has to be explicit in `pr-review.md`, not inferred.

3. **Location.** Which file owns the disposition — `pr-review.md` Synthesize And Post, `implementation-pipeline.md` Decision Recording, or both? Byte-exact text either way.

Only when those three are settled — either by a separate micro-initiative on Init-01's disposition register or by user decision — can this firstness-evidence initiative open cleanly.

## Scope (when opened)

**In scope:**
- Step 6b firstness-evidence artifact/marker shape.
- Test Audit cross-check mechanism.
- Absence-handling routing (tied to the settled disposition).
- Edit additions to `pr-review.md` Synthesize And Post and possibly `implementation-pipeline.md` Decision Recording.

**Out of scope:**
- Everything else in Initiative 02 (those landed in Initiative 02a).

## What Initiative 02a leaves for this initiative

After Init 02a applies, the following are explicitly unresolved and recorded as honest disclaimers in the workflow text:

- Firstness cannot be verified from a PR diff alone.
- Workflow ordering (Phase 3 → Step 6b → Step 6c with separate writers) gives process-level firstness but not diff-time evidence.
- TG1 closure is via workflow ordering only, not diff-time proof.

This initiative resumes work from that baseline.

## Log

- **2026-04-23** — Initiative spawned by decompose trigger on Initiative 02's round-2 review. Captured the disposition precondition. Blocked on disposition vocabulary being settled.
