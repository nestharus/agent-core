---
description: 'Author draft PR title/body files for fail-expected prototype-test contract PRs.'
model: claude-opus
inputs:
  - prototype_test_branch_ref
  - base
  - repo_root
  - dossier_answer_path
  - proof_test_audit_path
  - spawned_tickets_path
  - test_manifest_path
  - pending_marker_convention_path
  - implementation_ticket_urls
  - output_path
outputs:
  - ${output_path}.title
  - ${output_path}
base_procedure: ~/ai/agents/pr-writer.md
output_format: ''
---

# Prototype-Test PR Writer

## Base Procedure

Base procedure: `~/ai/agents/pr-writer.md`

This operator constrains that base flow to prototype-test PRs: fail-expected or pending tests published as a reviewable contract, not a production implementation PR.

## Use When

Use this operator when a prototype has produced reviewable production-tree proof tests that are intentionally fail-expected or pending until spawned implementation tickets complete. The PR is a prototype-test PR: a commentable test contract linked to the dossier and implementation tickets, not a production-ready implementation branch. It publishes durable implementation coverage for the spawned tickets, not throwaway prototype artifacts.

## Do Not Use When

- The PR is a production implementation PR. Use `~/ai/agents/pr-writer.md`.
- The PR ships a validated shippable prototype proof bundle with QA screenshots, deliverables, and passing behavior evidence. Use `~/ai/agents/prototype-pr-writer.md`.
- The caller lacks the test manifest, spawned implementation tickets, pending-marker convention, dossier answer, or proof-test audit.

## Required Inputs

- `prototype_test_branch_ref` - branch/ref containing the pending prototype tests.
- `base` - target branch for the draft PR; caller supplies the repository default branch or an explicit review target, but this must not be hard-coded to `main`.
- `repo_root` - absolute path to the repository.
- `dossier_answer_path` - path to the prototype dossier `answer.md`.
- `proof_test_audit_path` - path to the proof-test audit evidence.
- `spawned_tickets_path` - path to `dossier/spawned-tickets.md`.
- `test_manifest_path` - path to `dossier/test-publication-manifest.md`.
- `pending_marker_convention_path` - path to `~/ai/conventions/prototype-pending-tests.md`.
- `implementation_ticket_urls` - JSON array of spawned implementation ticket keys/URLs.
- `output_path` - body output path; the title is written to `${output_path}.title`.

## Inputs

Read every required input before drafting. Treat dossier-local paths as valid citations because this PR exists to review the prototype outcome and carry its implementation obligations forward.

If `base` is missing or empty, halt with `NEEDS_INPUT:missing-prototype-test-pr-base`. Do not infer or assume a hard-coded `main` target when the project declares a different default.

## Procedure

1. Validate every required input exists and is readable. Validate `implementation_ticket_urls` is a non-empty JSON array.
2. Read `test_manifest_path` and extract the test files, node IDs, expected fail-if-unmasked command when present, prototype-test branch/ref, and marker reason format.
3. Read `dossier_answer_path`, `proof_test_audit_path`, and `spawned_tickets_path` to determine the dossier verdict and spawned implementation ticket mapping.
4. Read `pending_marker_convention_path` and use its `prototype-pending:` reason format exactly.
5. Write the title file at `${output_path}.title`. The title must be a single line and < 70 chars.
6. Write the body file at `${output_path}` using the Output Contract section order below.
7. Self-check that `${output_path}.title` and `${output_path}` exist, are non-empty, and do not claim the implementation is production-ready.

## Output Contract

The body at `${output_path}` must contain these reviewer-facing sections in this order:

### Verdict

One paragraph naming the dossier verdict (`CONFIRM`, `DECOMPOSE`, `HALT`, or `RE-FRAME`) and the evidence-backed rationale.

### Reviewer focus

State that review follows `~/ai/conventions/prototype-review.md`: reviewers should comment on test design, outcome alignment, pending-marker traceability, and whether the tests support the dossier verdict. State that this is not review of disposable prototype source quality.

### Test manifest

List each published test identifier from `test_manifest_path` (test file path and/or node ID), copied exactly. Include the prototype-test branch/ref, the expected fail-if-unmasked command when the manifest provides one, and the spawned ticket each test maps to.

### Pending markers

Point to `~/ai/conventions/prototype-pending-tests.md`. Include the marker reason format from that convention and explain that the markers are traceable implementation handoff debt, not generic skip/xfail permission. The implementation must remove the marker or supersede the test with a traceable strictly stronger equivalent; the marker is not permission to discard the original assertions.

### Dossier link

Link or name the dossier evidence, including `answer.md`, `risk-profile.md`, and `evidence/`. Include `proof_test_audit_path` when it is separate from those paths.

### Spawned implementation tickets

List the implementation ticket URLs/keys from `implementation_ticket_urls` and the mapping from `spawned_tickets_path`. For each ticket, include this acceptance line exactly:

Remove the `prototype-pending:` markers in the listed test files, make these tests pass, and preserve the original assertions unless the manifest, spawned ticket payload, or Phase 6 Step 6b output index records a strictly stronger equivalent supersession.

Do not omit the marker token colon; wording such as "Remove the prototype-pending markers in the listed test files and make these tests pass." is invalid.

### Anti-scope

State that this PR is not a production implementation PR, reviewers should not request prototype-source quality changes, CodeRabbit is not run by default, and production PR-review gates are not applied by default.

## Stop Conditions

Return `BLOCKED` and do not write partial PR prose when any of these are true:

- Missing or unreadable `test_manifest_path`.
- Missing or unreadable `spawned_tickets_path`.
- Missing or unreadable `pending_marker_convention_path`.
- Empty `implementation_ticket_urls`.
- Missing dossier `answer.md` at `dossier_answer_path`.
- Missing proof-test audit at `proof_test_audit_path`.
- The test manifest does not name test paths or node IDs.
