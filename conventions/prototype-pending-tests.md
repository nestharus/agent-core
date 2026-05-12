# Prototype-Pending Tests

## Purpose

Prototype-pending tests are production-tree proof tests created by a prototype to describe behavior that spawned implementation tickets must make real. They are allowed only when each marker is traceable to a real implementation ticket and the prototype dossier records the PR, branch, test paths, and ticket mapping.

Prototype proof tests include E2E tests when the proved behavior is end-to-end, Pytest or integration tests when those are the right proof surface, and any project runner that can carry the same production behavior contract. They are durable handoff artifacts, not throwaway prototype evidence.

## Marker Reason Format

prototype-pending: implementation pending in <ticket-key-or-url>; remove marker and make this test pass

The marker reason must cite the real spawned ticket key or URL before the prototype-test branch is pushed. Placeholder ticket text is only allowed before P4 ticket creation and must not be published in the draft PR.

## Preferred Runner Mapping

- Pytest: use `@pytest.mark.xfail(strict=True, reason='prototype-pending: implementation pending in <ticket-key-or-url>; remove marker and make this test pass')` when the test can execute and is expected to fail before implementation.
- Playwright: use `test.fixme(..., 'prototype-pending: implementation pending in <ticket-key-or-url>; remove marker and make this test pass')` or the closest project-standard fail-expected marker.
- Fallback runners: when a framework has no strict expected-failure primitive, use `skip` or `fixme` only with the exact `prototype-pending:` reason prefix and a real implementation ticket key or URL.

## Boundary vs. Other Marker Conventions

- This convention does NOT change `~/ai/conventions/test-reports.md` strict-xfail-for-confirmed-bug semantics.
- This convention does NOT change `~/ai/agents/red-phase-gate.md` or `~/ai/agents/green-phase-gate.md` xfail/skip interpretation.
- This convention does NOT make generic untraceable skip/xfail acceptable.
- A traceable `prototype-pending:` marker is intentional prototype handoff debt; a stale or generic skip, fixme, or xfail remains brittleness/dead-coverage evidence.
- The convention does not make a pending test count as passing production behavior; implementation WUs must remove the marker and prove the test passes.

## Carry-forward to implementation

A prototype proof test is the production solution's behavior test for the proved behavior. When a prototype proves a behavior with a test, the spawned implementation ticket initially inherits that test verbatim; any refinement must preserve the original assertions or replace them with a strictly stronger equivalent, with the original-to-successor mapping recorded in the test-publication manifest, the spawned ticket payload, or the Phase 6 Step 6b output index.

The spawned implementation ticket carry-forward payload must include:

- `prototype_test_pr_url`
- `prototype_test_branch`
- `test_paths_or_node_ids` as a YAML sequence, one entry per inherited test file path or node ID:
  ```yaml
  test_paths_or_node_ids:
    - path/or/node-id
  ```
- `marker_reason`
- `ticket_mapping`
- `implementation_acceptance_criterion`

Dropping a prototype proof test from the implementation diff without a corresponding strictly stronger equivalent supersession entry in the manifest, ticket payload, or Step 6b output index is a workflow violation. Phase 6 process-tree audit and Phase 7 pre-dispatch readiness gates both refuse advance on this evidence.

If the implementation cannot pass an inherited prototype proof test, the implementation is wrong, or the prototype's verdict was wrong (the latter requires a separate re-evaluation, never a silent test rewrite).

## Reviewer Guidance

Prototype-test PR review follows `~/ai/conventions/prototype-review.md`. Reviewers should check test design, outcome alignment, pending-marker traceability, and whether the tests support the dossier verdict. Reviewers should not treat this convention as permission to approve broad untraceable skips.

## Implementation-Ticket Carry-Forward

Spawned implementation tickets must carry the canonical fields from `## Carry-forward to implementation`: `prototype_test_pr_url`, `prototype_test_branch`, `test_paths_or_node_ids`, `marker_reason`, `ticket_mapping`, and `implementation_acceptance_criterion`.

The implementation acceptance criterion is: remove the `prototype-pending:` markers in the listed test files, make these tests pass, and preserve the original assertions unless the manifest, spawned ticket payload, or Phase 6 Step 6b output index records a strictly stronger equivalent supersession.
