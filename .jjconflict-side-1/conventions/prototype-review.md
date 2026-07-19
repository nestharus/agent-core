# Prototype Review

## Prototype-review rule

Prototype review is a review of E2E proof tests, demonstrated outcomes, and dossier verdict support. The reviewer checks what the prototype proves, what it cost, what worked, what broke, and whether the dossier evidence supports the recommended next decision. It is not prototype source-code review.

When a prototype-test PR exists, PR comments are in scope only for test design, outcome alignment, pending-marker traceability, and dossier verdict support. The reviewer checks whether the published tests express the behavior the dossier claims and whether the spawned implementation tickets inherit a clear obligation to unmark and pass them.

## Production-review rule

Production implementation review belongs to `~/ai/workflows/pr-review.md` and the implementation-pipeline post-merge review surface in `~/ai/workflows/implementation-pipeline.md`. Prototype review may decide whether a prototype branch should be merged, cherry-picked, kept, or discarded, but it does not replace production branch review.

Prototype-test PRs do not trigger production PR-review gates by default. CodeRabbit is not dispatched on prototype-test PRs by default because the branch is intentionally pending-marked until implementation tickets complete; tests may be strict xfail, fixme, or skip-marked rather than merged as production-ready behavior.

## Human-vs-model-gate ownership

The human gate owns dossier-verdict and outcomes acceptance: whether `answer.md`, `branch-disposition.md`, `spawned-tickets.md`, and any original-ticket disposition are supportable by the evidence and worth carrying forward.

Model gates own the proof-test audit, one-question check, answer-trace check, and commit hygiene. Those gates establish whether the dossier is coherent and evidence-backed before the human accepts or revises it.

## Cross-links

- [`~/ai/workflows/build-prototype.md`](../workflows/build-prototype.md)
- [`~/ai/agents/prototype-orchestrator.md`](../agents/prototype-orchestrator.md)
- [`~/ai/conventions/prototype-pending-tests.md`](prototype-pending-tests.md)
- [`~/ai/workflows/pr-review.md`](../workflows/pr-review.md)
- [`~/ai/workflows/implementation-pipeline.md`](../workflows/implementation-pipeline.md)
