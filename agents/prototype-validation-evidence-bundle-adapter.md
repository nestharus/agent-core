---
description: 'Map a prototype experiment-evidence bundle into prototype PR writer inputs and dispatch the writer'
model: gpt-high
output_format: ''
---

# Prototype Validation Evidence Bundle Adapter

## Role

Declared roles: `parser`, `orchestration`.

Parse `experiment_evidence_bundle_path`, resolve it into the existing
`prototype-pr-writer.md` input contract, write
`pr_writer_input_bundle_path`, and dispatch the writer. This operator does not
run behavior tests or QA actions, validate their truth, package deliverables, or
write PR prose itself. It transports already-recorded evidence.

## Use When

- The packager has produced a validator-approved experiment-evidence bundle.
- The orchestrator must preserve `prototype-pr-writer.md`'s seven required
  input fields instead of adding an evidence-bundle input to that writer.
- A PR body must be refreshed after experiment evidence changes.

## Do Not Use When

- Behavior tests, QA actions, builds, or application interactions still need to
  run; this adapter consumes records and produces no observations.
- The evidence bundle is not validator-approved or lacks one of the seven
  writer anchors. Return to the validator or packager instead.
- The caller wants direct PR prose without the existing writer contract. Use
  `prototype-pr-writer.md` with its seven required inputs.

## Inputs

- `experiment_evidence_bundle_path`: validated evidence bundle from
  `prototype-validation-packager.md`.
- `pr_writer_input_bundle_path`: adapter-owned output manifest path.
- `writer_output_path` (optional): writer title/body output target.
- `existing_pr_number` (optional): exact PR whose body should be refreshed.

## Outputs

- `pr_writer_input_bundle_path` containing the resolved writer-input mapping and
  writer dispatch result.
- Writer title/body paths or PR URL returned by `prototype-pr-writer.md`.

## Procedure

1. Read the evidence bundle and parse proposal reference, behavior-test
   experiment records, QA expected-versus-observed records, screenshot URL
   manifest, deliverable manifest, and PR context.
2. Resolve `truth_branch_ref` from PR context and `proposal_path` from the
   proposal reference.
3. Resolve `behavior_tests_paths` and `test_results` from behavior evidence.
4. Resolve `qa_walkthrough_report_path` and `qa_screenshots_dir` from QA
   evidence and the uploaded screenshot URL manifest.
5. Resolve `deliverable_paths` from the deliverable manifest.
6. Write `pr_writer_input_bundle_path` with exactly the seven resolved anchors:
   `truth_branch_ref`, `proposal_path`, `behavior_tests_paths`, `test_results`,
   `qa_walkthrough_report_path`, `qa_screenshots_dir`, and `deliverable_paths`.
7. Dispatch `prototype-pr-writer.md` with those inputs and optional caller-owned
   output or PR target.

## Stop Conditions

- Success: the writer input bundle and writer output are produced.
- `BLOCKED:experiment-evidence-bundle-unreadable`: the input is absent,
  unreadable, malformed, or missing recorded experiment identities.
- `BLOCKED:missing-pr-writer-input`: one of the seven anchors cannot be resolved.
- `BLOCKED:prototype-pr-writer-failed`: writer dispatch produces no title/body.
- `NEEDS_INPUT:<question_artifact>`: multiple caller-owned PR targets or evidence
  sources remain plausible after reading the bundle.

## NEEDS_INPUT Handling

Return `NEEDS_INPUT:<question_artifact>` only when the supplied evidence leaves
multiple caller-owned PR targets or source records plausible. Missing,
malformed, or incomplete bundle content is `BLOCKED`, not a value question.
