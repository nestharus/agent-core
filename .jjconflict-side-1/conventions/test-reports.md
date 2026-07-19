# Test Reports

Use this convention when test authoring, coverage expansion, PR review, or a gate produces a report that reviewers are expected to trust.

The report artifact is the source of review evidence. A PR comment is only a pointer.

## Applicability

This convention applies to:

- coverage-expansion reports
- bug-discovery reports from `test-writer.md`
- test-audit reports that are posted or consumed during PR review
- any report that makes claims about UI behavior, code behavior, coverage evidence, or discovered bugs

It does not change what gets tested. Risk selection, behavior verification, test level, and gate ownership remain governed by the existing operators and workflows.

## Canonical Report Artifact

The canonical report artifact is a downloadable PDF.

Each report bundle may include Markdown sources, screenshots, non-UI evidence, logs, traces, or generated files, but the PDF is the artifact reviewers should read first. A PR comment must point to the PDF bundle and must not duplicate the full report.

The standard bundle contains:

```text
reports/
  product-report.md
  product-report.pdf
  engineering-report.md
  engineering-report.pdf
  investigative-report.md
  investigative-report.pdf
  report-index.md
  screenshots/
  evidence/
```

Projects must declare or provide a report-generation chain that keeps this artifact contract. The convention does not require a specific screenshot tool or PDF library.

## PR Pointer Comment

The PR comment is a pointer, not the report.

The comment should include:

- overall result or gate verdict when applicable
- artifact URL or workflow run URL
- names of the PDF files in the bundle
- short list of blocking items when applicable

Do not paste the full Product, Engineering, or Investigative report into the PR comment.

## Retention And Storage

Canonical long-term storage is S3 using the project's GitHub-CI IAM. In RFQ, that means `$AWS_GITHUB_ACCESS_KEY_ID` and `$AWS_GITHUB_SECRET_ACCESS_KEY`; project wrappers define the bucket, signing or presign mechanism, and exact key format.

The default key shape mirrors the RFQ E2E unified-report pattern: upload the report bundle under a project-defined prefix derived from the sanitized branch or PR ref plus the GitHub run id, then store each PDF under that prefix. In RFQ E2E, the prefix is `<sanitized-branch>/<github-run-id>/`; a PDF report key using that shape is `<sanitized-branch>/<github-run-id>/<report-slug>.pdf`.

The PR pointer comment links to the S3-backed URL for the canonical PDF, or to a presigned or signed-front-door URL when the bucket is private. Project wrappers may use CloudFront signed URLs, S3 presigned URLs, or an equivalent project-approved access layer, but the target remains the S3-stored PDF.

`actions/upload-artifact` remains useful as a redundant short-term store for CI-job debugging, with GitHub's default 90-day retention unless the workflow overrides it. It is not the canonical long-term report store once the S3 URL exists.

S3 is the cross-project default. Alternative long-term stores such as GCS, Azure Blob, or an internal artifact service are project-wrapper overrides and must define their bucket/container, key format, IAM, URL shape, and retention policy.

## Screenshot Rule

A screenshot is required when a test, bug, or report claim touches UI behavior.

UI-touching means the behavior affects a page, component, visual state, user-visible table, card, filter, form, graph, toast, modal, generated screen, or browser workflow.

Screenshot requirements:

- capture the page or component state that demonstrates the behavior
- include the affected area with enough surrounding context for orientation
- visually highlight the affected area using an accepted form: a box or arrow annotation on the affected region, an adjacent annotated copy, or a tool-rendered highlight visible without zoom
- store the screenshot in the report bundle
- cite the screenshot path from the PDF and Markdown source

If the UI cannot be run, the report must say so and classify the missing screenshot under the applicable workflow-execution violation class. Do not silently replace the screenshot with prose.

### Question-bearing screenshots

When a screenshot accompanies a question for a human reviewer (a SUSPICIOUS, AMBIGUOUS, or `state`-typed question manifest), the annotation must visually mark the **specific element the question is about** — the badge, the field, the cell, the toast — not just the page. A page-level highlight that the reviewer must scan to find the element fails this rule.

Acceptable forms:

- a tight box around the element under question, with a label that names what the question is about (e.g., `"In Stock" badge — question: stock > 0 vs ≥ requested qty?`)
- an arrow pointing at the element from a clear margin
- a callout/zoom inset of the element next to the full-page screenshot

When the question is about transitions, sequences, timing, or interaction (a `behavior`-typed question manifest), one screenshot is not sufficient. Use a frame sequence with `narration.md` per the trace-recorder operator and store it under the question's directory. Cite the frames directory, not a single frame, from the PDF.

## Non-UI Evidence Rule

Backend-only, CLI-only, data-only, or pure business-logic tests do not need screenshots.

Use the relevant evidence artifact instead:

- assertion diff
- normalized JSON or text snapshot
- input/output fixture
- generated PDF plus extracted text or metadata
- log excerpt
- trace file
- deterministic table, chart, or image when the artifact itself is visual

The evidence artifact must be stored in the bundle and cited from the report.

## Code Claim Rule

Every code claim must include:

1. a `file_path:line_number` citation
2. the exact fenced code block that supports the claim

A code claim is any statement that says production code, test code, fixture code, workflow code, or configuration does something specific.

Acceptable shape:

````markdown
`backend/main/currency_service.py:636`

```python
if isinstance(price_data, dict):
    return re_convert_price_to_base_currency(price_data, new_currency, currency_service)
```
````

Do not cite only a file name, function name, broad line range, or prose summary when the report depends on the code.

## Bug-Discovery Story Rule

Each discovered bug must have one report entry containing:

1. the exact failing behavior
2. the strict-xfail test marker with commit-hash citation
3. a fenced code block of the failing test or assertion with `file_path:line_number`
4. a fenced code block of the relevant production code with `file_path:line_number`
5. a screenshot when the behavior touches UI, or non-UI evidence when it does not
6. a plain-English explanation of intended behavior versus actual behavior

Use the landed behavior verdicts without inventing new disposition tokens:

- `VERIFIED`
- `SUSPICIOUS`
- `AMBIGUOUS`
- `OBVIOUSLY_BROKEN`

A confirmed bug with verified intended behavior must be represented as an expected-failure test:

```python
@expected_failure(
    strict=True,
    reason="Confirmed bug: intended behavior from commit <hash>; see <spec path>#<section>",
)
```

If a behavior is `SUSPICIOUS` or `AMBIGUOUS`, report it as such. Do not present it as a confirmed bug unless a human or cited source resolves the intended behavior.

## Three-Report Split

Use three reports when coverage expansion or test writing discovers behavior that needs attention:

- Product report: user-visible behavior, business impact, screenshots or non-UI evidence, and product decisions needed.
- Engineering report: source locations, failing tests, expected vs actual behavior, strict xfails, and implementation risk.
- Investigative report: evidence trail, coverage/risk inputs, behavior sources, commit archaeology, commands run, and unresolved questions.

Only include items that need attention. Do not add positives for behavior that already works.

## Per-Finding PDF (canonical tracker-ticket attachment)

The three reports above are **per-run summaries**. They are the right shape for an S3 bundle linked from the PR pointer comment, but they are the **wrong granularity for a tracker ticket** — a ticket asks one question or describes one bug, and the answerer should not have to scroll through unrelated items.

For every finding (question, bug-frontend, or bug-backend) emitted by a coverage-expansion run, the workflow produces one **per-finding PDF** that is the canonical attachment on that finding's tracker ticket:

- exactly one finding per PDF — no batching
- self-contained: embeds the question/bug, the locator, the evidence (screenshot, frame sequence, or log/diff), and the source refs
- text-only or text+embedded-images — no external assets, no JavaScript, no HTML side-channel, no `trace.zip` requiring Playwright tooling
- portable: the PDF should remain answerable if the team migrates off the current tracker
- file size budget: ~150 KB per PDF for state/bug findings; up to ~1 MB for behavior findings with embedded frames

Tracker integrations attach the PDF directly to the ticket. Raw screenshots, frame directories, traces, and videos remain in the run bundle (S3 or local) but are **not** attached individually to the ticket — that defeats the portability purpose. If a power user wants the trace, the per-run bundle URL appears in the ticket body.

Do not also produce HTML versions of per-finding artifacts. PDFs are the canonical attachment; HTML is redundant.

## Upload Contract

The default canonical upload mechanism is a project-wrapper S3 upload using the project's GitHub-CI IAM and key format from Retention And Storage.

The PR pointer comment links to the S3 URL, signed URL, or presigned URL for the canonical PDF bundle. The artifact bundle must contain the PDFs and supporting screenshots/evidence.

GitHub Actions artifacts are secondary debug fallbacks. If S3 upload fails but an Actions artifact exists, the pointer may temporarily fall back to the Actions artifact URL or workflow run artifact list and must identify it as a fallback.

## Report-Emission Gaps

A report-emission gap exists when a required report artifact or required report evidence is missing.

Examples:

- canonical PDF missing when the workflow requires one
- screenshot missing for a UI-touching test or bug
- code claim lacks `file_path:line_number`
- code claim lacks the exact fenced code block
- non-UI evidence artifact missing for a backend-only behavior claim
- PR comment presents itself as the report rather than pointing to the PDF bundle

Workflow reviews classify these under existing classes in `~/ai/conventions/workflow-execution-violations.md`, usually class 2 for missing artifacts, class 6 for missing evidence or grounding, and class 9 for false completion when a pointer or comment claims success while the canonical report is absent.
