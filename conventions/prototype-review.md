# Prototype Review

## Prototype-review rule

Prototype review is a review of E2E proof tests, demonstrated outcomes, and dossier verdict support. The reviewer checks what the prototype proves, what it cost, what worked, what broke, and whether the dossier evidence supports the recommended next decision. It is not prototype source-code review.

## Production-review rule

Production implementation review belongs to `~/ai/workflows/pr-review.md` and the implementation-pipeline post-merge review surface in `~/ai/workflows/implementation-pipeline.md`. Prototype review may decide whether a prototype branch should be merged, cherry-picked, kept, or discarded, but it does not replace production branch review.

## Human-vs-model-gate ownership

The human gate owns dossier-verdict and outcomes acceptance: whether `answer.md`, `branch-disposition.md`, `spawned-tickets.md`, and any original-ticket disposition are supportable by the evidence and worth carrying forward.

Model gates own the proof-test audit, one-question check, answer-trace check, and commit hygiene. Those gates establish whether the dossier is coherent and evidence-backed before the human accepts or revises it.

## Cross-links

- [`~/ai/workflows/build-prototype.md`](../workflows/build-prototype.md)
- [`~/ai/agents/prototype-orchestrator.md`](../agents/prototype-orchestrator.md)
- [`~/ai/workflows/pr-review.md`](../workflows/pr-review.md)
- [`~/ai/workflows/implementation-pipeline.md`](../workflows/implementation-pipeline.md)
