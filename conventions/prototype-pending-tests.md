# Prototype-Pending Tests

## Declared Roles

`validator`, `formatter`, `mapper`, `parser`

## Purpose

Prototype-pending tests are pending production behavior-test contracts created
from prototype findings. They describe behavior that spawned implementation
tickets must make real. They are allowed only when every marker is traceable to
a real implementation ticket and the prototype dossier records the PR, branch,
test paths, and ticket mapping.

An executed prototype behavior test may record an observed prototype result. A
pending production test does not record passing production behavior. Follow
`conventions/behavioral-proof.md` for that distinction.

## Marker Reason Format

```text
prototype-pending: implementation pending in <ticket-key-or-url>; remove marker and make this test pass
```

The reason cites a real spawned ticket key or URL before the branch is pushed.
Placeholder text is allowed only before P4 ticket creation and must not be
published in the draft PR.

## Preferred Runner Mapping

- Pytest: use `@pytest.mark.xfail(strict=True, reason='prototype-pending: implementation pending in <ticket-key-or-url>; remove marker and make this test pass')` when the test executes and is expected to fail before implementation.
- Playwright: use `test.fixme(..., 'prototype-pending: implementation pending in <ticket-key-or-url>; remove marker and make this test pass')` or the closest project-standard fail-expected marker.
- Other runners: use `skip` or `fixme` only when no strict expected-failure
  primitive exists, with the exact `prototype-pending:` reason prefix and a real
  implementation ticket key or URL.

## Boundary vs. Other Marker Conventions

- This convention does NOT change `~/ai/conventions/test-reports.md`
  strict-xfail-for-confirmed-bug semantics.
- This convention does NOT change `~/ai/agents/red-phase-gate.md` or
  `~/ai/agents/green-phase-gate.md` xfail/skip interpretation.
- This convention does NOT make generic untraceable skip/xfail acceptable.
- A traceable `prototype-pending:` marker is intentional implementation handoff
  debt; a stale or generic skip, fixme, or xfail remains brittleness or
  dead-coverage evidence.
- A pending marker never counts as passing production behavior.

## Carry-Forward To Implementation

The pending production behavior-test contract is initially inherited verbatim.
Any refinement preserves its assertions or replaces it with a traceable strictly
stronger equivalent. Record the original-to-successor mapping in the
test-publication manifest, spawned-ticket payload, or Phase 6 Step 6b output
index.

The carry-forward payload includes:

- `prototype_test_pr_url`
- `prototype_test_branch`
- `test_paths_or_node_ids` as a YAML sequence
- `marker_reason`
- `ticket_mapping`
- `implementation_acceptance_criterion`

Dropping an inherited test without an accepted stronger-successor entry is a
workflow violation. Phase 6 process-tree audit and Phase 7 readiness refuse
advance. If the implementation cannot pass the inherited contract, either the
implementation is wrong or the prototype verdict requires explicit
re-evaluation; silent assertion rewriting is forbidden.

## Supersession-Entry Schema

The inherited-prototype gate accepts supersession entries from predecessor
session manifests, spawned-ticket payloads, and Step 6b output indexes.

```markdown
original_evidence_ref: Path or node ID of the inherited pending production behavior-test contract; must match test_paths_or_node_ids.
successor_evidence_ref: Path or node ID of the passing production test or strictly stronger executed-evidence record replacing the original.
assertion_preservation_or_strengthening_rationale: Why the successor preserves the original assertions or is strictly stronger.
producer: One of prototype-pr-writer, implementation-phase-6b-test-writer, manifest-author, ticket-payload-author.
currentness_evidence: Commit, PR, branch, dispatch, or other currentness reference specific enough for the active gate.
```

### Parse Semantics

- A predecessor session manifest uses `supersession_entries`, a sequence of
  records with the exact keys above.
- A spawned-ticket description or comment uses a `Supersession entries` heading
  or labeled block.
- A Step 6b output-index row may contain or point to a record. It still maps the
  original evidence ref to the successor evidence ref; a superseded inherited
  test is never merely marked non-applicable.

### Validation

Reject a record when a required field is absent, the original does not match an
inherited test, the successor is untraceable, the rationale does not preserve or
strengthen assertions, the producer is outside the allowed set, or currentness
evidence is absent or stale.

The successor becomes canonical only when its passing production experiment
evidence is traceable and current for the gate being evaluated. A model review,
bundle path, or pending marker cannot satisfy that requirement.

## Reviewer Guidance

Prototype-test PR review follows `~/ai/conventions/prototype-review.md`. Reviewers
check test design, outcome alignment, marker traceability, and dossier support.
This convention does not permit broad untraceable skips.

## Implementation-Ticket Carry-Forward

The spawned implementation ticket carries the payload from `Carry-Forward To
Implementation` and uses this acceptance criterion:

Remove the `prototype-pending:` markers in the listed test files and make these tests pass.
Preserve the original assertions unless the manifest, spawned ticket
payload, or Phase 6 Step 6b output index records a strictly stronger equivalent
supersession.
