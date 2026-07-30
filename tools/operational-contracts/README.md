# Operational Contracts

`tools/operational_contracts.py` provides fail-closed executable validators for workflow authorization boundaries. Its commands cover:

- reviewed/immediate PR identity, fresh base/head equality, draft restoration, and non-replayable merge-attempt state;
- canonical process-tree reports and recursive nested test-audit fanout;
- direct and refactoring feature-route process proofs, attempt envelopes, acceptance lineage, and serialized dependency gates;
- refactoring dispatch, package execution, child PR identity, and auditor-index evidence;
- caller-owned ticket-operation context joined to producer-owned Jira or Linear comment/readback evidence;
- provider-payload extraction and invocation-owned PR-review lifecycle state.

Route validation is split between common `validate-route-process-proof --feature-branch`, direct-only `validate-route-artifact-lineage`, and dependency-gating `validate-route-attempts`. Ticket evidence validation requires `validate-ticket-operation-result --expected-context`.

## Used By

- `agents/apply-gate-set.md`
- `agents/feature-orchestrator.md`
- `agents/implementation-pipeline-orchestrator.md`
- `agents/pr-review-operator.md`
- `agents/refactoring-commit-history-orchestrator.md`
- `agents/refactoring-orchestrator.md`
- `agents/test-audit-gate.md`
- `workflows/agents-cli.md`
- `workflows/implementation-pipeline.md`
- `workflows/pr-review.md`

## Anti-Scope

The module validates caller-supplied artifacts and writes validation results. It also allocates immutable PR-review run roots, writes their manifest and ownership records, and safely removes clean, owned PR-review worktrees after terminal evidence exists. It does not dispatch agents, query providers, mutate pull requests or tickets, or perform merges.
