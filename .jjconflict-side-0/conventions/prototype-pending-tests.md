# Prototype-Pending Tests

## Declared roles

`validator`, `formatter`, `mapper`, `parser`.

This file-local declaration overrides the documented path default per `~/ai/conventions/code-quality.md` § Declared roles. The declared role set covers existing whole-file classifications (marker validity rules → `validator`; marker reason format + per-runner marker forms → `formatter`; carry-forward payload mapping → `mapper`) plus the new `## Supersession-entry schema` parser/validator content (`parser`, `validator`).

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

## Supersession-entry schema

This section declares the supersession-entry record shape consumed by the inherited-prototype gate from three accepted source types: predecessor session manifest, spawned-ticket payload, and Step 6b output index. It extends `## Carry-forward to implementation`; it does not replace the carry-forward payload or the no-silent-drop rule.

### Required fields

```markdown
original_proof_ref: Path or node ID of the inherited prototype proof test being superseded; must match an entry in the inherited test_paths_or_node_ids sequence.
successor_proof_ref: Path or node ID of the production proof, existing passing production test, or stronger proof artifact replacing the original.
assertion_preservation_or_strengthening_rationale: Why the successor preserves the original assertions or is strictly stronger, composing with the no-silent-drop rule in ## Carry-forward to implementation.
producer: One of prototype-pr-writer, implementation-phase-6b-test-writer, manifest-author, ticket-payload-author.
currentness_evidence: Commit, PR, branch, dispatch, or other currentness reference the entry was current against, specific enough for merge, rerun, or handoff drift checks.
```

### Parse semantics

#### Predecessor session manifest

The canonical semantic field is `supersession_entries`, shaped as a YAML sequence of supersession-entry records with the required keys above. A concrete predecessor session manifest may be JSON; this convention names the semantic field and record keys, not a runtime parser implementation.

#### Spawned-ticket payload

A spawned-ticket payload carries a Markdown heading or labeled block named `Supersession entries` in the ticket description or comment, with one entry per inherited proof test. Linear/Jira backend-specific rendering is out of scope for this schema.

#### Step 6b output index

A Step 6b output-index row may carry or point to a supersession-entry record. The row must still map the original inherited proof ref to the successor proof ref; a superseded inherited proof must not be marked non-applicable.

### Validation rules

Reject a supersession entry as malformed canonical evidence when any required field is missing; `original_proof_ref` does not match an inherited test path or node ID; `successor_proof_ref` is absent or untraceable; the rationale does not state assertion preservation or strengthening; `producer` is outside the allowed set; `currentness_evidence` is absent; or `currentness_evidence` is stale relative to the merge, branch, or dispatch being gated. These are auditor-readable Markdown criteria for the inherited-prototype gate's canonical evidence, not an executable validator mandate.

### Canonical evidence acceptance

A supersession entry becomes canonical evidence the inherited-prototype gate may consume only when all required fields are present, refs match, the successor proof is traceable to passing production evidence or an accepted stronger equivalent, and currentness evidence applies to the gate being evaluated. Acceptance is the terminal evidence state; malformed-entry rejection remains the validation filter before that state.

## Reviewer Guidance

Prototype-test PR review follows `~/ai/conventions/prototype-review.md`. Reviewers should check test design, outcome alignment, pending-marker traceability, and whether the tests support the dossier verdict. Reviewers should not treat this convention as permission to approve broad untraceable skips.

## Implementation-Ticket Carry-Forward

Spawned implementation tickets must carry the canonical fields from `## Carry-forward to implementation`: `prototype_test_pr_url`, `prototype_test_branch`, `test_paths_or_node_ids`, `marker_reason`, `ticket_mapping`, and `implementation_acceptance_criterion`.

The implementation acceptance criterion is: remove the `prototype-pending:` markers in the listed test files, make these tests pass, and preserve the original assertions unless the manifest, spawned ticket payload, or Phase 6 Step 6b output index records a strictly stronger equivalent supersession.
