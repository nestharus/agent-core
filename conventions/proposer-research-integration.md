# Proposer Research Integration

## Purpose

This convention adds a targeted research branch to proposer/critic revise/review loops governed by [proposer-critic-pattern.md](proposer-critic-pattern.md). It is a convention for using research inside a blocked proposal cycle, not a new orchestrator, critic, memory layer, or acceptance rule.

The branch exists for the case where a critic's non-accept verdict exposes a real knowledge gap. The proposer may need evidence about a design pattern, library, tool, best practice, implementation approach, or comparable product before it can revise responsibly. Research supplies that evidence and the proposer then revises the current artifact. The normal critic gate still decides whether the revised artifact is accepted.

## Scope

This convention applies only to B4-style proposer/critic loops that explicitly opt into this branch. It covers proposal-revision work where the proposer has already received a non-accept critic concern and cannot close the concern from the proposal, problem statement, repository context, or already-approved planning materials.

It does not silently rewrite every workflow that performs research. Roadmap Layer 0 market research, PR review research, PR justification research, CodeRabbit loops, tickets-first review, prototype dossiers, and one-shot Phase 1 problem research remain under their local workflow rules unless a later work unit deliberately opts them in.

The convention is additive to B4. It preserves B4's rule that workflows compose their own proposers, critics, dispatch rules, critic count, verdict vocabulary, and acceptance equivalents.

## When Proposer Dispatches Research

A proposer dispatches or requests targeted research only when both conditions are true:

1. A required critic has returned a non-accept verdict, such as MEDIUM, HIGH, not-accepted, value-positive findings, or the workflow's equivalent.
2. The blocking concern depends on knowledge the proposer cannot responsibly derive from current context.

Legitimate research questions include unknown design patterns, unknown best practices, library or tool selection, implementation-approach uncertainty, ecosystem compatibility, and comparable-product behavior. The research question should be narrow enough to answer the critic concern and broad enough to compare viable alternatives.

Ordinary critic feedback is not enough. If the concern can be resolved by reading the proposal, applying the critic's reasoning, checking repository context, or tightening a known design, the proposer revises directly. Research is not a detour around normal proposer accountability.

The proposer may identify that research is needed, but the workflow or orchestrator owns the actual dispatch mechanics, artifact paths, retry limits, and sequencing.

## Current and Future Research Target

Until C2 / NES-151 lands a concrete `research-team` workflow, the current landed precursor is [../workflows/research.md](../workflows/research.md). Use that workflow's evidence discipline, synthesis shape, and thin-data handling for targeted proposer research.

Once C2 lands, C2 owns the concrete `research-team` mechanics for this branch. This convention forward-references that target without claiming it exists today.

The brenner_bot / research-team disposition boundary lives in [../DECISIONS.md](../DECISIONS.md) D-2026-05-05d. Design-pattern, best-practice, library, tool, implementation-approach, and comparable-product questions are research-team-shaped questions. Do not route those proposer/critic questions to `brenner_bot` under this convention.

## Research Workflow Composition

Targeted proposer research reuses the research workflow for evidence production only. It may use focused research questions, source discipline, findings with citations, options with tradeoffs, recommendations when warranted, and explicit inconclusive results.

It does not import the research workflow's human Decision phase into the proposer/critic loop. Gate ownership remains where [gate-ownership.md](gate-ownership.md) puts it: proposal review gates are model-owned unless the governing workflow already says otherwise. Targeted research inside the loop adds no new human gate.

The research artifact feeds the next proposer revision. It is not a proposal, not a critic verdict, not an approval, and not a replacement for the workflow's required critic pass.

## What Research Returns

Research returns one or more ranked candidate solutions when the evidence supports them, or an explicit inconclusive result when it does not. Do not force a fake candidate count to satisfy the word "ranked." Thin evidence should remain visibly thin.

Each candidate should include:

- the candidate solution;
- the rationale for why it may close the critic concern;
- applicability bounds and known non-fits;
- tradeoffs, costs, and risks;
- source or evidence basis;
- confidence.

Research produces evidence and options, not final proposal design. The proposer still owns the revised artifact and must decide what to do with the research.

## Proposer Revision

After research returns, the proposer chooses one candidate, combines compatible candidates, rejects all candidates, or identifies that the evidence is inconclusive. The revised artifact must explain the choice enough for critics to review the reasoning against the same problem and workflow standard.

If the proposer rejects all candidates, it must still take a normal workflow path: revise directly from the remaining evidence, propose termination, decompose when the governing convergence rule requires it, return to research only for a genuinely new or narrower knowledge gap, or surface a NEEDS_INPUT new-value question when one exists under the workflow's existing rules.

The proposer may not present the research report as if it were the revised proposal. The proposer must integrate the evidence into the artifact under review.

## Cycle Re-Entry

A research-backed revision re-enters the normal B4 critic gate. Every required critic for the pass reviews the revised current artifact under the workflow's normal vocabulary.

Prior LOW, accept, value-zero, or equivalent verdicts do not carry forward after a substantive revision. Those verdicts applied to a superseded artifact. A still-blocking critic concern remains blocking until the responsible critic gate accepts the revised current artifact.

A later critic block may trigger another targeted research dispatch only when it exposes a new unresolved knowledge gap. Repeated research dispatches cannot be used to avoid the decomposition and non-convergence rules owned by [review-convergence.md](review-convergence.md).

## Anti-Pattern: Research as Justification Generator

Do not dispatch research to manufacture justification after the critic gate already approved the current artifact or returned LOW. Research after acceptance is not a way to decorate an accepted proposal with extra support.

Do not use research as narrative override for a still-blocking critic concern. A research report does not override, does not silence, and is not acceptance from the critic. The only acceptance is the workflow's required critic result for the same current artifact.

Do not ask research to produce the answer the proposer already wants. The research question should be framed around the critic concern and the unknowns that block responsible revision.

## Cross-References and Delegated Concerns

[proposer-critic-pattern.md](proposer-critic-pattern.md) owns the base proposer/critic semantics: fresh proposer dispatch after non-accept verdicts, fresh critic re-run after substantive revision, and acceptance only for the same current artifact.

[../workflows/research.md](../workflows/research.md) is the current landed research precursor. C2 / NES-151 owns the future concrete `research-team` workflow once it lands.

[../DECISIONS.md](../DECISIONS.md) D-2026-05-05d owns the brenner_bot / research-team routing boundary. C5 may later refine that disposition, but NES-150 does not.

[audit-history.md](audit-history.md) owns loop memory, round representation, prior-finding closure, role histories, and decision-register mechanics. When audit history is active, targeted research artifacts may be recorded as round artifacts, role outputs, or deciding inputs, but this convention defines no new memory schema.

[review-convergence.md](review-convergence.md) owns non-convergence and decomposition policy. Research dispatch is not a permission slip to keep iterating after a hard decomposition trigger fires.

[gate-ownership.md](gate-ownership.md) owns human versus model gate authority. This convention adds no new human gate and does not double-check model-owned proposal gates with the user.

[../models/roles.md](../models/roles.md) owns model selection. This convention does not assign models to proposers, critics, researchers, or future research-team roles.

C3 owns future critic-operator implementation changes. This convention does not change critic prompts, critic independence, verdict schemas, required critic counts, or acceptance equivalents.

## Non-Goals

This convention does not implement C2, C3, C4, or C5.

It does not create `research-team`, change `brenner_bot`, define audit-history schema, rewrite convergence policy, or alter gate ownership.

It does not amend workflow files, AGENTS indexes, DECISIONS entries, roadmap behavior, PR review behavior, CodeRabbit behavior, tickets-first review, prototype handling, or one-shot research lifecycles.

It does not make research a default step after every non-accept verdict. Research is reserved for critic-blocking knowledge gaps that the proposer cannot responsibly close from current context.
