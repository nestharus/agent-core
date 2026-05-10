# Proposer / Critic Pattern

## What this convention is

This convention names the proposer/critic meta-pattern for workflow authors, orchestrator authors, and operator authors. It is a shared rule document, not an orchestrator, and it does not subsume the existing instantiations. Per `~/ai/VALUES.md` § Composition over flag-stuffing, workflows compose their own proposers, critics, dispatch rules, and acceptance vocabulary.

## Two sides

A proposer authors or revises a reviewable artifact: a proposal, plan, roadmap, diff, or another work product named by the workflow. A critic evaluates that artifact and returns a verdict or findings under the workflow's dialect. The proposer and critic are different agents in different invocations.

## The cycle

The pattern is a revise/review loop:

1. The proposer authors the artifact from the workflow inputs.
2. Critics run against the artifact and the relevant problem/context.
3. Critics return a verdict.
4. Any non-accept verdict triggers a fresh proposer dispatch with the failing critic outputs as input.
5. After revision, every critic that belongs to the pass re-runs against the revised artifact.

Old accepts are discarded after a substantive proposal revision because they reviewed a superseded artifact. They cannot be carried forward as acceptance for the same pass.

## Acceptance

Acceptance requires all required critics return LOW, or the workflow's accept equivalent, for the same current artifact. A workflow may use a different accept equivalent, but it must apply that equivalent to the required critics for the current artifact.

Cherry-picking favorable critic outputs is not acceptance. Narrative override is not acceptance. A proposer-claimed self-rerun is not acceptance; the workflow must dispatch the actual critics.

## Critic independence

Critics in a pass are independent. Each critic sees the artifact and the relevant problem/context, but does not see other critics' current-pass outputs while producing its verdict. Current-pass independence is load-bearing because it keeps the critic outputs from collapsing into a shared consensus before the workflow has separate judgments.

## Proposers do not also critique

A dispatch where the same agent creates and judges the artifact is not running the proposer/critic pattern. It may still be normal author diligence or a checklist pass, but it does not satisfy a required critic gate. This rule is normative, not syntactically enforced.
<!-- INTENTIONAL: This convention states the review semantics only. Workflow-local operators own their own dispatch steps, and the no-machine-enforcement convention keeps this out of runtime/syntactic enforcement. -->

## What this pattern is NOT

This pattern is not an orchestrator and is not a replacement for workflow-local procedure. One-shot read-only audits are not proposer/critic because they lack a proposer revision side and re-review after revision. Read-only audits can still be useful; they are just outside this convention.

## What this convention does NOT own

This convention does not own loop memory, prior-finding closure, oscillation tracking, or the decision register; those belong to `~/ai/conventions/audit-history.md`.

This convention does not own non-convergence or decomposition policy; those belong to `~/ai/conventions/review-convergence.md`.

This convention does not own human vs. model gate ownership; that belongs to `~/ai/conventions/gate-ownership.md`.

This convention does not own model-role selection; that belongs to `~/ai/models/roles.md`.

Workflow-local verdict vocabulary, critic count, escalation rules, and oscillation termination remain in the workflow or operator that instantiates the pattern.

## Existing instantiations

`~/ai/workflows/implementation-pipeline.md` Phase 4 is a LOW/MEDIUM/HIGH risk-gate dialect. All four reports must return LOW for the same current proposal; any non-LOW finding sends the proposal back for revision, and the full gate re-runs.

`~/ai/workflows/roadmap.md` layer risk gates use LOW/MEDIUM/HIGH per layer. All risks must be LOW before a layer advances, and a revised layer artifact gets a full re-gate after revision.

`~/ai/workflows/coderabbit-loop.md` is a proposer/critic loop with different vocabulary. Its accept equivalent is value-zero / useful-finding convergence, not LOW/MEDIUM/HIGH.

These citations are read-only references to existing workflow authority. The convention names the shared meta-pattern; it does not rewrite any local workflow rule.

## Cascade is out of scope

NES-149 codifies the meta-pattern only. It does not require cascade or consolidation across all instantiations.
<!-- INTENTIONAL: There is no orchestrator step to wire here; this is an explicit boundary on NES-149 scope, not deferred procedure. -->
