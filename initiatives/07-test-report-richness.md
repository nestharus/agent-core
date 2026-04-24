# Initiative 07 — Test report richness + coverage-expansion workflow formalization

**Status:** landed (this commit — coverage-expansion-operator + test-reports convention + existing-operator updates + pr-review Test Audit + violation-taxonomy examples + audit-history artifact field)
**Depends on:** 02a, 03, 05 (all landed)
**Blocks:** —

## Problem (user framing, verbatim)

> I think we need to improve our test workflow as well as our next initiative. We currently write reports but the reports are a little hard to understand. We should capture screenshots of the pages and upload actual pdf documents to be downloaded rather than just posting github comments. We can highlight the specific areas and behaviors we're talking about and point out where it lives in code and show the specific code blocks.

## Firm constraints

1. **Report richness is a first-class deliverable, not optional enhancement.** Text-only GitHub comments do not count as a report deliverable by themselves.
2. **UI-touching tests produce screenshots of the pages involved.** Screenshots are linked from the report and uploaded as PR artifacts, not just embedded inline.
3. **Reports are delivered as downloadable PDFs**, not only as GitHub-comment Markdown. The PDF is the canonical artifact; the PR comment is a pointer.
4. **Every behavior and area the report discusses is highlighted visually** in a screenshot and textually in the code block.
5. **Every claim about code cites `file_path:line_number`** plus the exact code block quoted in-report.
6. **The existing coverage-expansion pattern must be formalized** as a proper operator — not left as an ad-hoc sequence of three agents run by hand. See the gap below.

## The coverage-expansion gap (from current session context)

Today's coverage-expansion workflow (used for RFQ PRs #439, #444, #445, #446) is an ad-hoc pattern:

1. `risk-assessor` picks a P0 module.
2. `behavior-investigator` produces a behavior spec at `planning/coverage/spec-*.md` from commits, PRs, and callers (NOT from current code).
3. `test-writer` writes tests from the spec, classifying each as `VERIFIED` / `SUSPICIOUS` / `AMBIGUOUS`.
4. Discovered bugs become `@pytest.mark.xfail(strict=True)` with commit-hash citations.
5. Output: three reports — product / engineering / investigative.

The sequence isn't codified. It lives in operator memory. An operator file — `coverage-expansion-operator.md` or similar — would capture: P0-pick policy, spec-first rule (no code-snapshotting), three-class test classification, xfail-strict-with-commit-hash rule, 3-report contract.

## Scope

**In scope:**
- Formalize coverage-expansion as an operator under `~/ai/agents/`. Either a new `coverage-expansion-operator.md` or a documented orchestrator wrapping `risk-assessor` + `behavior-investigator` + `test-writer`. Cite the spec-first rule and the xfail-strict convention explicitly.
- Add a report-artifact convention under `~/ai/conventions/` covering:
  - Screenshot capture policy (when required; tool used; storage path).
  - PDF generation policy (tooling; embed screenshots; embed code blocks).
  - Code-reference format (file_path:line_number + fenced code block in every claim).
  - Highlight policy (screenshot boxes / arrows; code-block line ranges).
  - PR-comment-vs-PDF contract: PR comment is a pointer; PDF is canonical.
- Update the existing test-workflow operators (`test-writer`, `test-audit-gate`, `coverage-auditor`, `coverage-analyzer`, the PR-review test-audit path) to emit reports per the new convention, not just Markdown text.
- Update `~/ai/workflows/pr-review.md` Test Audit step to consume and surface the PDF artifact.
- Integration with Init 03's `process-tree-auditor` — if a test-report emission gap surfaces, the tree-review mechanism references the PDF artifact (or its absence) as evidence.
- Integration with Init 05's `audit-history.md` — a round that produced a report records the report artifact path + PDF link in `User Q&A Inputs` or a new `Report artifacts` subsection.

**Out of scope:**
- Changing what gets tested (behavior vs coverage choice stays with existing operators).
- Building a new report-format server or hosting service. Artifacts live as GitHub PR file attachments or similar existing storage.
- PDF layout design beyond "screenshots embedded, code blocks embedded, titles + file:line refs legible."

## Reference material (study during research phase)

Existing RFQ PRs that exercise the current informal pattern:

- Coverage expansion: https://github.com/lama-ai-RFQ/RFQautomation/pull/446
- Coverage expansion: https://github.com/lama-ai-RFQ/RFQautomation/pull/445
- Coverage expansion: https://github.com/lama-ai-RFQ/RFQautomation/pull/444
- Coverage expansion: https://github.com/lama-ai-RFQ/RFQautomation/pull/439
- Coverage expansion: https://github.com/lama-ai-RFQ/RFQautomation/pull/419
- Coverage expansion: https://github.com/lama-ai-RFQ/RFQautomation/pull/418
- Related: https://github.com/lama-ai-RFQ/RFQautomation/pull/521
- Related: https://github.com/lama-ai-RFQ/RFQautomation/pull/522

Bugs discovered via this pattern (cited in current session for context):
`re_convert_prices_to_base_currency`, `_jobs_data_df` cache, `_multiply_price_by_quantity`, `normalize_part_number`, `determine_primary_result_index`.

Adjacent `~/ai/` assets this initiative builds on:
- `~/ai/conventions/audit-history.md` (Init 05) — for recording report artifact paths.
- `~/ai/conventions/workflow-execution-violations.md` (Init 03) — for classifying report-emission gaps as violations.
- `~/ai/workflows/implementation-pipeline.md` Step 6b (Init 02a) — tests-first baseline.
- `~/ai/workflows/pr-review.md` Test Audit section (Init 02a + Init 04) — current consumer of test reports.

## Expected research tracks (sketch — to open when initiative starts)

- **R1 — Current-state audit** of the three agents (`risk-assessor`, `behavior-investigator`, `test-writer`) to extract the ad-hoc protocol into its explicit contract.
- **R2 — Report-format study** of the reference RFQ PRs: what's in each PR's current report, what's missing, what visually-better reports in comparable projects look like.
- **R3 — Tooling audit** for screenshot + PDF generation that can run in the RFQ project's existing CI / local-dev environment (Playwright is already in RFQ for E2E).
- **R4 — Artifact-upload mechanics** for GitHub PRs: what's idiomatic (PR attachments? Actions artifact uploads? release-asset link-in-comment?).

## Artifacts (empty until unblocked)

- `.build/A<NN>-test-reports-*-prompt.md`
- `.build/A<NN>-test-reports-*-findings.md`
- Proposal target: new operator file + new convention file + updates to test-workflow operators + updates to `pr-review.md` Test Audit step.

## Log

- **2026-04-24** — Initiative queued. Captured the user's verbatim framing + the coverage-expansion formalization gap from the prior session's notes + the 8 reference RFQ PRs.
- **2026-04-24** — 4-track research fan-out: R1 operator audit, R2 RFQ PR report-format study (all 8 PRs), R3 tooling audit, R4 artifact-upload mechanics.
- **2026-04-24** — Synthesis produced 14 RG-gaps + 10 options. All accepted except J (retention horizon) deferred.
- **2026-04-24** — Proposal cycle: v0 (2 blocking + 5 non-blocking Y-findings) → v2 (1 non-blocking Z1, apply-phase fold-in). Convergence in one revision round. Blocking issues were a violation-class taxonomy break (tried to add class 12; collapsed to examples under existing classes 2/6/9) and a code-fence typo in a nested report-index block.
- **2026-04-24** — Applied: new `~/ai/agents/coverage-expansion-operator.md` (codifies P0-pick + spec-first + VERIFIED/SUSPICIOUS/AMBIGUOUS + xfail-strict-with-commit-hash + 3-report output), new `~/ai/conventions/test-reports.md` (canonical PDF + screenshots + file:line + code-block rules, tool-neutral), updates to `test-writer` / `test-audit-gate` / `coverage-analyzer` / `coverage-auditor` for report emission, pr-review Test Audit consumes PDF artifact, workflow-execution-violations examples added under classes 2/6/9, audit-history gains artifact-path field, AGENTS.md routing entry. Z1 (behavior-investigation report mover) folded inline at apply.
- **2026-04-24** — Closed RG12 (retention horizon): adopted RFQ's existing E2E unified-report S3 pattern for canonical report PDF retention. `test-reports.md` now makes S3 the default long-term store through project GitHub-CI IAM, keeps `actions/upload-artifact` as a short-term debug fallback, and requires PR pointer comments to prefer the S3-backed PDF URL.
