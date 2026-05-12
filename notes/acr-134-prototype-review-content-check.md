# ACR-134 Prototype Review Content Check

This is the Step 6b inspectable content-check spec for ACR-134. It records the assertions Step 6c must satisfy without writing the product convention page, workflow wording, operator wording, or AGENTS pointer text.

## Assertions

### A1 - Convention file exists with required shape

Fixture path: `conventions/prototype-review.md`

- [ ] Required heading shape: the file exists and contains a top-level `# Prototype Review` heading, or an H1/H2 heading whose text includes `Prototype Review`.
- [ ] Required clause: the convention states the prototype-review rule: prototype review means E2E / proof tests, outcomes, and dossier verdict support; it is not prototype source-code review.
- [ ] Required clause: the convention states the production-review rule: production-implementation review belongs to `~/ai/workflows/pr-review.md` and the implementation-pipeline post-merge review surface.
- [ ] Required clause: the convention distinguishes human vs model gate ownership for prototype review. The human gate is the dossier-verdict plus outcomes acceptance gate; model gates run proof-test audit, one-question check, answer-trace, and commit hygiene.
- [ ] Required cross-link path: the convention links to `~/ai/workflows/build-prototype.md`.
- [ ] Required cross-link path: the convention links to `~/ai/agents/prototype-orchestrator.md`.
- [ ] Required cross-link path: the convention links to `~/ai/workflows/pr-review.md`.
- [ ] Required cross-link path: the convention links to `~/ai/workflows/implementation-pipeline.md`.
- [ ] Observable signal: a reviewer can open `conventions/prototype-review.md` on disk and find the required heading, clauses, and cross-links in that file.

### A2 - Build-prototype P3 gate cites the convention and uses proof-test / outcome / verdict language

Fixture path: `workflows/build-prototype.md` section `#### P3 gate`

- [ ] Required clause: the `#### P3 gate` section points to `conventions/prototype-review.md`, cited as either `~/ai/conventions/prototype-review.md` or a relative link.
- [ ] Required clause: the `#### P3 gate` section directs the human reviewer to proof tests, either by naming `dossier/evidence/` or using the phrase `proof tests`.
- [ ] Required clause: the `#### P3 gate` section directs the human reviewer to outcomes, including what the prototype demonstrates, cost, what broke, and what worked.
- [ ] Required clause: the `#### P3 gate` section directs the human reviewer to dossier verdict support, including whether `answer.md`, `branch-disposition.md`, and `spawned-tickets.md` are supportable by the evidence.
- [ ] Required negative clause: the `#### P3 gate` section does not present prototype source-code review as the human task.
- [ ] Required preservation clause: existing P3 sub-step descriptions `P3.1` through `P3.7` remain untouched in wording, order, and numbering.
- [ ] Observable signal: a reviewer can inspect only the `#### P3 gate` section and confirm the convention citation plus proof-test, outcome, and verdict-support review focus without seeing a source-review instruction.

### A3 - Prototype-orchestrator cites the convention and the role plus P3 gate payload direct reviewers to outcomes

Fixture path: `agents/prototype-orchestrator.md` sections `## Role` and the P3 verify + human gate procedure

- [ ] Required clause: the role description or non-negotiables block cites `~/ai/conventions/prototype-review.md` exactly once.
- [ ] Required clause: the P3 verify + human gate procedure names `~/ai/conventions/prototype-review.md` as the source of the review-focus rule when the operator packages `NEEDS_INPUT` for the user.
- [ ] Required clause: the P3 verify + human gate payload directs the reviewer toward proof-test evidence, demonstrated outcomes, cost, breakage, analog-gate verdicts, and support for `answer.md`, `spawned-tickets.md`, branch disposition, and original-ticket disposition when present.
- [ ] Required preservation clause: the orchestrator YAML frontmatter remains unchanged, including `description`, `model`, and `output_format`.
- [ ] Required preservation clause: no P3 sub-step procedure is renumbered or reordered; only the citation and packaging wording change.
- [ ] Observable signal: a reviewer can inspect `## Role`, non-negotiables if used, and the P3 verify + human gate procedure and confirm the convention citation plus outcome-focused gate packaging while the frontmatter and step structure remain stable.

### A4 - Cross-links resolve

Fixture path: every relative or `~/ai/`-rooted link introduced by A1, A2, and A3

- [ ] Required cross-link path: any introduced link to `~/ai/conventions/prototype-review.md` resolves to `conventions/prototype-review.md` in the worktree.
- [ ] Required cross-link path: any introduced link to `~/ai/workflows/build-prototype.md` resolves to `workflows/build-prototype.md` in the worktree.
- [ ] Required cross-link path: any introduced link to `~/ai/agents/prototype-orchestrator.md` resolves to `agents/prototype-orchestrator.md` in the worktree.
- [ ] Required cross-link path: any introduced link to `~/ai/workflows/pr-review.md` resolves to `workflows/pr-review.md` in the worktree.
- [ ] Required cross-link path: any introduced link to `~/ai/workflows/implementation-pipeline.md` resolves to `workflows/implementation-pipeline.md` in the worktree.
- [ ] Required clause: the new convention page is the only new link target introduced by this WU; all other targets already exist.
- [ ] Observable signal: a reviewer can map each introduced relative or `~/ai/` path to an existing file under the worktree root.

### A5 - AGENTS.md Conventions index contains a one-line pointer

Fixture path: `AGENTS.md` section `## Conventions`, or the conventions index block if the exact heading differs

- [ ] Required clause: one new line appears under the Conventions index pointing at `conventions/prototype-review.md`.
- [ ] Required heading/placement shape: the pointer is located in the Conventions index area, not in workflow routing, operator routing, or a procedure section.
- [ ] Required clause: the line has a short label for the prototype-vs-production review boundary.
- [ ] Required negative clause: the line is pointer-only and does not restate P3 procedure.
- [ ] Required negative clause: the line does not reroute spawned implementation review.
- [ ] Required preservation clause: no other `AGENTS.md` sections change.
- [ ] Observable signal: a reviewer can diff `AGENTS.md` and see exactly one Conventions-index pointer line for `conventions/prototype-review.md`, with no unrelated AGENTS edits.

## Anti-Assertions

### A6 - No P3 sub-step renumbering

Fixture path: `workflows/build-prototype.md` and `agents/prototype-orchestrator.md`

- [ ] Forbidden change: `workflows/build-prototype.md` must not renumber or reorder its current P3 sub-steps; it still names `P3.1` through `P3.7`, or `P3.8` if that already exists, in their current order.
- [ ] Forbidden change: `agents/prototype-orchestrator.md` must not renumber or reorder its current P3 procedure references or step-by-name references.
- [ ] Observable signal: a reviewer can compare the P3 step sequence before and after Step 6c and confirm the existing order and numbering were preserved.

### A7 - No production-review procedure edits

Fixture path: `workflows/pr-review.md` and `workflows/implementation-pipeline.md`

- [ ] Forbidden change: `workflows/pr-review.md` must not change.
- [ ] Forbidden change: `workflows/implementation-pipeline.md` Phase 8 procedure must not change.
- [ ] Forbidden change: `workflows/implementation-pipeline.md` Phase 8.5 procedure must not change.
- [ ] Observable signal: a reviewer can run or inspect a diff and confirm no content changes were made to `workflows/pr-review.md` or `workflows/implementation-pipeline.md`.

### A8 - No change to spawned-implementation-ticket review path

Fixture path: `workflows/build-prototype.md`, `agents/prototype-orchestrator.md`, `AGENTS.md`, and any file Step 6c touches

- [ ] Forbidden change: Step 6c must not alter the review path for spawned implementation tickets.
- [ ] Forbidden change: Step 6c must not reroute spawned implementation tickets away from `~/ai/workflows/implementation-pipeline.md` or `~/ai/workflows/pr-review.md`.
- [ ] Forbidden change: Step 6c must not add AGENTS routing criteria, operator-routing entries, or workflow procedure text that changes spawned implementation review.
- [ ] Observable signal: a reviewer can inspect the diff and find only prototype-review focus wording, cross-links, the new convention page, and the pointer-only AGENTS entry, with no spawned-ticket review path changes.

### A9 - No fix to pre-existing git diff drift

Fixture path: `agents/prototype-orchestrator.md`

- [ ] Forbidden change: Step 6c must not change the pre-existing `git diff main..HEAD` vs `git diff main...HEAD` drift in `prototype-orchestrator.md`.
- [ ] Forbidden change: Step 6c must not introduce new diff-base guidance or normalize existing diff-base guidance as part of ACR-134.
- [ ] Observable signal: a reviewer can inspect the relevant `prototype-orchestrator.md` diff-base references and confirm they are unchanged except for unrelated context if lines moved without content changes.
