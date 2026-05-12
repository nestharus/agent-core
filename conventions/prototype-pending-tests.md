# Prototype-Pending Tests

## Purpose

Prototype-pending tests are production-tree proof tests created by a prototype to describe behavior that spawned implementation tickets must make real. They are allowed only when each marker is traceable to a real implementation ticket and the prototype dossier records the PR, branch, test paths, and ticket mapping.

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

## Reviewer Guidance

Prototype-test PR review follows `~/ai/conventions/prototype-review.md`. Reviewers should check test design, outcome alignment, pending-marker traceability, and whether the tests support the dossier verdict. Reviewers should not treat this convention as permission to approve broad untraceable skips.

## Implementation-Ticket Carry-Forward

Spawned implementation tickets must carry the prototype-test PR URL, branch, test paths/node IDs, marker reason, ticket mapping, and this acceptance criterion:

Remove the `prototype-pending:` markers in the listed test files and make these tests pass.
