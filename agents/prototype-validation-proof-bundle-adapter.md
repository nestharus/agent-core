---
description: 'Map a prototype proof bundle into prototype PR writer inputs and dispatch the writer'
model: gpt-high
output_format: ''
---

# Prototype Validation Proof Bundle Adapter

## Role

Declared roles: `parser`, `orchestration`.

Parse `proof_bundle_path`, resolve it into the existing `prototype-pr-writer.md` input contract, write `pr_writer_input_bundle_path`, and dispatch the writer. This operator does not write PR prose itself.

## Use When

- The packager has produced a validator-approved proof bundle.
- The orchestrator needs to preserve `prototype-pr-writer.md`'s seven required input fields instead of adding a new proof-bundle input to that writer.
- A PR body needs to be created or refreshed after validation evidence changes.

## Do Not Use When

- The proof bundle is missing or has not passed validation.
- Screenshots need upload, packages need assembly, or cleanup needs execution.
- The PR is a production implementation PR. Use `pr-writer.md`.

## Inputs

- `proof_bundle_path`: validated proof bundle from `prototype-validation-packager.md`.
- `pr_writer_input_bundle_path`: adapter-owned output manifest path.
- Optional writer output path or existing PR body refresh target from the caller.

## Outputs

- `pr_writer_input_bundle_path` containing the resolved writer-input mapping and writer dispatch result.
- `prototype-pr-writer.md` title/body artifact paths or PR URL, as returned by the writer.

## Procedure

1. Read `proof_bundle_path` and parse proposal reference, behavior evidence, QA evidence, deliverable manifest, and PR context.
2. Resolve `truth_branch_ref` from proof bundle PR context.
3. Resolve `proposal_path` from proof bundle proposal reference.
4. Resolve `behavior_tests_paths` from behavior evidence.
5. Resolve `test_results` from behavior evidence.
6. Resolve `qa_walkthrough_report_path` from QA evidence.
7. Resolve `qa_screenshots_dir` from the uploaded screenshot URL manifest carried by QA evidence.
8. Resolve `deliverable_paths` from the deliverable manifest.
9. Write `pr_writer_input_bundle_path` with the seven resolved anchors: `truth_branch_ref`, `proposal_path`, `behavior_tests_paths`, `test_results`, `qa_walkthrough_report_path`, `qa_screenshots_dir`, and `deliverable_paths`.
10. Dispatch `prototype-pr-writer.md` through `agents -m claude-opus -f <prompt-file>` with those seven required inputs and any caller-provided output target.

## Stop Conditions

- Success - writer input bundle and writer output are produced.
- `BLOCKED:proof-bundle-unreadable` - `proof_bundle_path` is absent, unreadable, or malformed.
- `BLOCKED:missing-pr-writer-input` - one of the seven writer-input mapping anchors cannot be resolved.
- `BLOCKED:prototype-pr-writer-failed` - writer dispatch fails or produces no title/body material.

## NEEDS_INPUT Handling

Return `NEEDS_INPUT:<question_artifact>` only when multiple caller-owned PR targets, branch refs, or evidence sources are plausible and no supplied bundle field resolves the ambiguity.
