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

A confirmed bug with verified intended behavior must be represented in pytest as:

```python
@pytest.mark.xfail(
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

## Upload Contract

The default upload mechanism is a GitHub Actions workflow artifact uploaded with `actions/upload-artifact`.

The PR pointer comment links to the artifact URL or workflow run artifact list. The artifact bundle must contain the PDFs and supporting screenshots/evidence.

Retention horizon is not defined by this convention. Use the repository or organization default unless a project-specific workflow sets `retention-days`.

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
