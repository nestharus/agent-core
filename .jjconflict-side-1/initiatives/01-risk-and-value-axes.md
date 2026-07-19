# Initiative 01 — Risk and value axes

**Status:** landed (commit `acf79cd`; axes A-D live; E deferred; H2 shipped as tradeoff; I1 dropped)
**Depends on:** —
**Blocks:** Initiative 02 (tests encode intent)

## Problem (user framing, verbatim)

> Right now our risk assessment is too aggressive. The risk assessment is fine. The problem is that we don't then take these risks and look at the context around them.
>
> We do look at implementation risk and reduce it. However, we don't look at the integration risk. What are the odds this causes an outage? For this we need risk profiles of the application in order to understand how an outage could potentially happen, even if we don't necessarily see it ahead of time. That's integration risk. We weigh that against the risk that the PR resolves/reduces to determine its value. Before we can weigh against the risk being resolved, we have to understand more of the context to gauge the real risk. We need to understand exposure. Where is this thing is exposed? Who is using it? Where? The risk surface. It may be a code risk. It may be a user risk. So we build up a risk profile of the existing state that is being touched. We then look at how the incoming requested change reduces and mitigates that risk. So assessing existing risk state is the problem definition. The incoming proposal is the proposal to reduce that risk state.
>
> So this actually adds another axis to how we conduct research (separate research track/researchers) and how we produce proposals (separate reviewers). We can then weigh the value that the PR brings against risk of something going wrong. For something going wrong, we can research those risks to see how to mitigate and reduce them. So we can continue to reduce our risks and increase our value.
>
> Of course, the value may not even be there. It could only be valuable under particular assumptions and research may reveal that those assumptions are incorrect, reducing actual value to near 0 and terminating the workflow early.
>
> We keep getting PRs that don't add real value. [...] User keeps needing to assess the value themselves, but the workflows could automate and do this more effectively.

Referenced evidence of the pattern:
- PR #519 — F7+F8 safe frontend hardening (security boundary sub-init, backlog)
- PR #523 — F14 host_updater auth with auto-migration (security boundary sub-init, backlog)

## Scope

**In scope:**
- `~/ai/workflows/implementation-pipeline.md`
- `~/ai/workflows/pr-review.md`
- Operator files whose role changes as a result (`risk-assessor`, `behavior-investigator`, the `pr-justification-*` family, possibly new operators).
- Any new convention file(s) defining the axes and the value computation.

**Out of scope for this initiative:**
- Test-workflow integration — deferred to Initiative 02.
- Downstream project wrappers (RFQ) — they inherit after `~/ai/` lands.

## Reference framework

`/home/nes/projects/agent-implementation-skill/execution-philosophy/problem-first-ai-engineering.md` — the user cites this as the source for "problem definition" vocabulary and the loops involved.

## Research fan-out (in flight)

Parallel `gpt-high` researchers per `~/ai/workflows/research.md §Parallel-fanout`:

| ID | Topic | Prompt | Log | Output |
|----|-------|--------|-----|--------|
| R1 | Book extraction — framework, loops, vocabulary, termination, assumption handling | `.build/A17-risk-axes-r1-book-prompt.md` | `.build/A17-risk-axes-r1-book.log` | `.build/A17-risk-axes-r1-book-findings.md` |
| R2 | Workflow audit — coverage matrix for 7 candidate axes across workflows + operators | `.build/A17-risk-axes-r2-workflow-audit-prompt.md` | `.build/A17-risk-axes-r2-workflow-audit.log` | `.build/A17-risk-axes-r2-workflow-audit-findings.md` |
| R3 | PR forensics — characterize #519 + #523 along the axes; identify missing signal | `.build/A17-risk-axes-r3-pr-forensics-prompt.md` | `.build/A17-risk-axes-r3-pr-forensics.log` | `.build/A17-risk-axes-r3-pr-forensics-findings.md` |

Candidate axes (will be refined by R1):
- Implementation risk
- Integration risk
- Existing-state risk profile
- Exposure / risk surface
- Value computation
- Termination for low value
- Assumption tracking and invalidation-driven termination

## Synthesis

`gpt-high` coordinator integrates R1+R2+R3 → `~/ai/.build/problem-definition-risk-and-value-axes.md`:
- Problem statement
- Evidence per track
- Candidate axes / integration points
- No solution design

## Decision gate

User reads the synthesized problem definition and picks: accept → proposal phase; reframe; follow-up research.

## Log

- **2026-04-23** — Initiative opened. Scope confirmed. 3 parallel researchers dispatched: bg `bdcs1amik` (R1), `bdaj7dmc0` (R2), `b21eb9r8s` (R3).
- **2026-04-23** — R1, R2, R3 all landed (22 KB / 64 KB / 22 KB findings). Synthesis dispatched bg `b2cmjmp7m` → `.build/A17-risk-axes-problem-definition.md` (24 KB, 8 sections, 6 gaps `G1-G6`, 5 options `A-E`). Status: awaiting user Phase 4 decision.
- **2026-04-23** — User Phase 4 decision: accept A+B+C+D, defer E until those axes are specified. Moving to proposal phase.
- **2026-04-23** — Proposal cycle: v0 (10 F-findings) → v2 (4 G-findings, 3 single-gen oscillation) → v3 (2 H-findings, 1 single-gen oscillation) → v4 (1 cosmetic I-finding, 0 oscillation). Strict monotone convergence; decompose trigger never fired. Writer-perspective (`gpt-high`) and reviewer-perspective (`claude-opus`) decision agents independently picked `round 3 H1 only` at round 2 using audit history `.build/A17-risk-axes-audit-history.md`.
- **2026-04-23** — User accepted v4. Apply-phase writer landed 21 edits across 4 tracked files: `workflows/implementation-pipeline.md` (new Phase 2.5, rewrites of Phase 3/4, rules added to Phases 5/6/7, Decision Recording), `workflows/pr-review.md` (intro + Gates row + new Supported-Surface Verification section + Synthesize And Post rule), `workflows/research.md` (Phase 3 synthesis draft handoff + Phase 4 decision), `conventions/gate-ownership.md` (2 new gate rows). 0 blockers, 0 disagreements. Apply changelog at `.build/A17-risk-axes-apply-changelog.md`. Working tree dirty; awaiting user commit decision.
