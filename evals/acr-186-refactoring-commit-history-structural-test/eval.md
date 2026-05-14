---
eval_id: acr-186-refactoring-commit-history-structural-test
behavior_class: ACR-182 refactoring-commit-history docs + routing structural conformance
lifecycle_state: WRITE
severity_when_fires: HIGH
evidence_source_kinds:
  - markdown-frontmatter
  - markdown-section-header
  - json-entry
  - cross-reference-token
suggested_action_class: revise-docs
---

# ACR-186 Refactoring-Commit-History Structural Test

## Eval identity

This is a markdown behavior specification for `acr-186-refactoring-commit-history-structural-test`, not runnable eval code. It names the Step 6c contract for seven standalone Python structural tests that verify ACR-182's refactoring-commit-history workflow, orchestrator, convention, routing, package-output wording, worked example, and sibling cross-reference coverage.

The parent behavior is ACR-182's refactoring-commit-history documentation strategy. This eval-spec is in `WRITE` state and is the binding Step 6c eval artifact for the implementation requirements specified below.

## Unwanted behavior

The unwanted behavior is silent drift in the ACR-182 refactoring-commit-history docs and routing surfaces: the workflow can lose its frontmatter or `## Use When` anchor, the orchestrator can lose its required-input section, the convention can lose declared roles, milestone identification, package-output, or worked-example commitments, the route/index entry can disappear or rename the workflow id, or the sibling strategy references to ACR-179, ACR-154, and ACR-180 can be deleted from one of the three docs.

The seven Step 6c tests must turn that drift into a local structural failure with direct process-status observability. The failing surface is the doc or routing file named by the failed assertion; the suggested fix is to revise that source surface, not to loosen the test.

## Assumptions

- A1: This eval-spec is a `WRITE`-state behavior specification. It names the future Step 6c test contract but does not ship executable test code in this WU.
- A2: Deep schema validation of `workflow_dispatch_contract` is out of scope. W3 asserts that the frontmatter exposes the mapping anchor, not that every nested field satisfies a full workflow metadata schema.
- A3: Tests are invoked as standalone scripts: `python3 <test-file>`. Exit code 0 = PASS, non-0 = FAIL. Stderr carries the failed-AC ID + evidence.
- A4: Assertion failures emit stderr lines of shape `FAIL <AC_ID>: <evidence>` and exit with code 1. Each test SHOULD emit exactly one FAIL line per failure; cascade behavior is Step 6c's call.
- A5: Assertion successes emit a single stdout line `PASS <test-id>: all ACs satisfied` and exit 0. The test-id is the test module name stem, for example `workflow_shape`.

## Positive evidence

### test_refactoring_commit_history_workflow_shape.py

- W1 (frontmatter present): file `/home/nes/ai/workflows/refactoring-commit-history.md` starts with an opening `---` line followed by YAML frontmatter terminated by a closing `---`.
  - Missing-token signal: target `/home/nes/ai/workflows/refactoring-commit-history.md`; structural anchor is opening `---` plus closing `---` frontmatter delimiter block.
  - Failure shape: `FAIL W1: <evidence>` where evidence names the path and the missing or malformed delimiter line.
- W2 (workflow.id == refactoring-commit-history): the frontmatter region contains a top-level `workflow:` key and, within that block before the next top-level key, an indented `id: refactoring-commit-history` entry. Step 6c may verify this with minimal inline frontmatter/block parsing; no third-party YAML parser is required.
  - Missing-token signal: target `/home/nes/ai/workflows/refactoring-commit-history.md`; structural anchor is `workflow:` plus nested `id: refactoring-commit-history` in the frontmatter region.
  - Failure shape: `FAIL W2: <evidence>` where evidence names the path, observed frontmatter value, missing key, or frontmatter/block parse failure.
- W3 (workflow_dispatch_contract present): the frontmatter region contains a top-level `workflow_dispatch_contract:` mapping anchor (existence only; deep schema validation is anti-scope per A2).
  - Missing-token signal: target `/home/nes/ai/workflows/refactoring-commit-history.md`; structural anchor is top-level `workflow_dispatch_contract:`.
  - Failure shape: `FAIL W3: <evidence>` where evidence names the path and missing mapping token or parse result.
- W4 (`## Use When` header): the file body contains a Markdown header with exact text `## Use When` (one of the canonical workflow section headers).
  - Missing-token signal: target `/home/nes/ai/workflows/refactoring-commit-history.md`; token is the exact Markdown header `## Use When`.
  - Failure shape: `FAIL W4: <evidence>` where evidence names the path and absent header.

Exit semantics: exit 0 only when all four assertions pass; exit non-0 with a stderr message naming the failed assertion ID (`W1` / `W2` / `W3` / `W4`) and the failing evidence (line ref or token observed).

### test_refactoring_commit_history_orchestrator_shape.py

- O1 (orchestrator file exists): `/home/nes/ai/agents/refactoring-commit-history-orchestrator.md` exists, is non-empty, and is readable.
  - Missing-token signal: target `/home/nes/ai/agents/refactoring-commit-history-orchestrator.md`; structural anchor is readable non-empty file presence.
  - Failure shape: `FAIL O1: <evidence>` where evidence names the missing, unreadable, or empty path.
- O2 (`## Required Inputs` header): the file body contains a Markdown header with exact text `## Required Inputs`.
  - Missing-token signal: target `/home/nes/ai/agents/refactoring-commit-history-orchestrator.md`; token is the exact Markdown header `## Required Inputs`.
  - Failure shape: `FAIL O2: <evidence>` where evidence names the path and absent header.

Exit semantics: same shape (exit non-0 with failed-AC name + evidence).

### test_refactoring_commit_history_convention_shape.py

- C1 (convention file exists): `/home/nes/ai/conventions/refactoring-commit-history-scoping.md` exists, is non-empty, and is readable.
  - Missing-token signal: target `/home/nes/ai/conventions/refactoring-commit-history-scoping.md`; structural anchor is readable non-empty file presence.
  - Failure shape: `FAIL C1: <evidence>` where evidence names the missing, unreadable, or empty path.
- C2 (`## Declared roles` header): the file body contains a Markdown header with exact text `## Declared roles`.
  - Missing-token signal: target `/home/nes/ai/conventions/refactoring-commit-history-scoping.md`; token is the exact Markdown header `## Declared roles`.
  - Failure shape: `FAIL C2: <evidence>` where evidence names the path and absent header.
- C3 (`## Milestone identification` header): the file body contains a Markdown header with exact text `## Milestone identification`.
  - Missing-token signal: target `/home/nes/ai/conventions/refactoring-commit-history-scoping.md`; token is the exact Markdown header `## Milestone identification`.
  - Failure shape: `FAIL C3: <evidence>` where evidence names the path and absent header.

Exit semantics: same shape.

### test_refactoring_commit_history_routing.py

- R1 (`/home/nes/ai/AGENTS.md` contains `refactoring-commit-history-orchestrator`): substring search.
  - Missing-token signal: target `/home/nes/ai/AGENTS.md`; token is `refactoring-commit-history-orchestrator`.
  - Failure shape: `FAIL R1: <evidence>` where evidence names the path and missing token.
- R2 (`/home/nes/ai/AGENTS.md` mentions the three role files in the same row/region): the routing region for `refactoring-commit-history-orchestrator` references all of `agents/refactoring-commit-history-orchestrator.md`, `workflows/refactoring-commit-history.md`, and `conventions/refactoring-commit-history-scoping.md`. Implementation may use a windowed substring search around the orchestrator-name match (±50 lines) -- exact strategy is Step 6c's call.
  - Missing-token signal: target `/home/nes/ai/AGENTS.md`; tokens are `agents/refactoring-commit-history-orchestrator.md`, `workflows/refactoring-commit-history.md`, and `conventions/refactoring-commit-history-scoping.md` in the `refactoring-commit-history-orchestrator` routing region.
  - Failure shape: `FAIL R2: <evidence>` where evidence names the path, route window, and missing role-file token.
- R3 (`/home/nes/ai/workflows/index.json` parses as JSON): `json.load(...)` succeeds without error.
  - Missing-token signal: target `/home/nes/ai/workflows/index.json`; structural anchor is parseable JSON.
  - Failure shape: `FAIL R3: <evidence>` where evidence names the path and JSON parse error.
- R4 (`workflow.id == refactoring-commit-history` entry exists): the parsed JSON contains an entry whose `workflow.id` (or equivalent path within the entry) is exactly the literal string `refactoring-commit-history`. Step 6c determines the structural path within the JSON via direct inspection of the live index (it is one of: top-level `workflows` array with object entries, OR nested under `workflow_dispatch.workflows`, etc.); whatever the actual shape, the assertion looks for the literal `refactoring-commit-history` at the appropriate `workflow.id` position. The test MUST fail if the entry is absent or under a different id key.
  - Missing-token signal: target `/home/nes/ai/workflows/index.json`; structural anchor is a parsed entry with `workflow.id` exactly `refactoring-commit-history`.
  - Failure shape: `FAIL R4: <evidence>` where evidence names the path, JSON path inspected, absent entry, wrong id key, or wrong observed id value.

Exit semantics: same shape, with the failing AC and evidence (raw line, JSON path, or parse error) named.

### test_refactoring_commit_history_package_output.py

- P1 (`## Package descriptor` header): convention contains a Markdown header with exact text `## Package descriptor`.
  - Missing-token signal: target `/home/nes/ai/conventions/refactoring-commit-history-scoping.md`; token is the exact Markdown header `## Package descriptor`.
  - Failure shape: `FAIL P1: <evidence>` where evidence names the path and absent header.
- P2 (package-output phrase): the body contains at least one of `list of packages`, `multiple packages`, or `package descriptor list` (case-insensitive substring).
  - Missing-token signal: target `/home/nes/ai/conventions/refactoring-commit-history-scoping.md`; token set is `list of packages`, `multiple packages`, or `package descriptor list`.
  - Failure shape: `FAIL P2: <evidence>` where evidence names the path and the missing package-output phrase set.
- P3 (anti-token absence within `## Package descriptor` section): the **`## Package descriptor` section body only** (from its header up to the next `## ` header, or EOF if no subsequent `## ` header exists) does NOT contain `single PR` or `sweeping refactor`. Critique-context occurrences of "one sweeping PR" elsewhere in the convention (e.g., inside `## Worked example`) are explicitly NOT relevant to P3 -- those argue against the anti-pattern and are legitimate. Step 6c implements P3 as section-scoped: read the convention, locate `## Package descriptor`, capture its body up to the next `## ` header or EOF, assert that body has no occurrence of `single PR` or `sweeping refactor`. Substring search; case-insensitive is acceptable.
  - Missing-token signal: target `/home/nes/ai/conventions/refactoring-commit-history-scoping.md`; structural anchor is `## Package descriptor` section body without anti-tokens `single PR` or `sweeping refactor`.
  - Failure shape: `FAIL P3: <evidence>` where evidence names the path, section range or excerpt, and forbidden token found.

Exit semantics: same shape.

### test_refactoring_commit_history_worked_example.py

- E1 (`## Worked example` header): convention contains a Markdown header with exact text `## Worked example`.
  - Missing-token signal: target `/home/nes/ai/conventions/refactoring-commit-history-scoping.md`; token is the exact Markdown header `## Worked example`.
  - Failure shape: `FAIL E1: <evidence>` where evidence names the path and absent header.
- E2 (≥ 2 numbered package descriptors): the worked-example section contains at least two numbered list items that name distinct package descriptors. A numbered package descriptor is a numbered list item that describes a separate refactoring package or slice, with non-empty descriptor text after the numeric marker. Implementation: regex for `^\s*\d+\.` within the `## Worked example` section, allowing optional leading whitespace, with ≥ 2 matches. Step 6c determines the section delimiter (next `## ` header or EOF).
  - Missing-token signal: target `/home/nes/ai/conventions/refactoring-commit-history-scoping.md`; structural anchor is at least two numbered-list lines in the `## Worked example` section that name distinct package descriptors.
  - Failure shape: `FAIL E2: <evidence>` where evidence names the path, section range or excerpt, and observed numbered descriptor count.
- E3 (holistic-LOW wording): the worked-example section contains the literal substring `holistic LOW` OR `holistic-LOW` OR `LOW holistic` (the convention's actual phrasing; substring-case-insensitive is acceptable).
  - Missing-token signal: target `/home/nes/ai/conventions/refactoring-commit-history-scoping.md`; token set is `holistic LOW`, `holistic-LOW`, or `LOW holistic` inside `## Worked example`.
  - Failure shape: `FAIL E3: <evidence>` where evidence names the path, section range or excerpt, and missing holistic-LOW token set.

Exit semantics: same shape.

### test_refactoring_commit_history_cross_references.py

- X1 (`ACR-179` present in workflow, orchestrator, AND convention): all three files must contain the literal `ACR-179`.
  - Missing-token signal: targets `/home/nes/ai/workflows/refactoring-commit-history.md`, `/home/nes/ai/agents/refactoring-commit-history-orchestrator.md`, and `/home/nes/ai/conventions/refactoring-commit-history-scoping.md`; token is `ACR-179` in each target.
  - Failure shape: `FAIL X1: <evidence>` where evidence names both the missing token `ACR-179` and the document path missing it.
- X2 (`ACR-154` present in all three): same.
  - Missing-token signal: targets `/home/nes/ai/workflows/refactoring-commit-history.md`, `/home/nes/ai/agents/refactoring-commit-history-orchestrator.md`, and `/home/nes/ai/conventions/refactoring-commit-history-scoping.md`; token is `ACR-154` in each target.
  - Failure shape: `FAIL X2: <evidence>` where evidence names both the missing token `ACR-154` and the document path missing it.
- X3 (`ACR-180` present in all three): same.
  - Missing-token signal: targets `/home/nes/ai/workflows/refactoring-commit-history.md`, `/home/nes/ai/agents/refactoring-commit-history-orchestrator.md`, and `/home/nes/ai/conventions/refactoring-commit-history-scoping.md`; token is `ACR-180` in each target.
  - Failure shape: `FAIL X3: <evidence>` where evidence names both the missing token `ACR-180` and the document path missing it.

Exit semantics: failure messages must name BOTH the missing token AND the document path that is missing it.

## Non-fire cases

A future runnable detector for these anchor sets returns no findings (exits 0 / reports clean) when:

- The W set: `/home/nes/ai/workflows/refactoring-commit-history.md` is readable, has delimiter-bounded frontmatter, has a top-level `workflow:` block containing nested `id: refactoring-commit-history`, has top-level `workflow_dispatch_contract:`, and contains `## Use When`.
- The O set: `/home/nes/ai/agents/refactoring-commit-history-orchestrator.md` is readable, non-empty, and contains `## Required Inputs`.
- The C set: `/home/nes/ai/conventions/refactoring-commit-history-scoping.md` is readable, non-empty, and contains `## Declared roles` and `## Milestone identification`.
- The R set: `/home/nes/ai/AGENTS.md` contains the refactoring-commit-history orchestrator route and role-file references, and `/home/nes/ai/workflows/index.json` parses as JSON with a `workflow.id == "refactoring-commit-history"` entry.
- The P set: the convention contains `## Package descriptor`, includes at least one approved package-output phrase, and that section body does not contain `single PR` or `sweeping refactor`.
- The E set: the convention contains `## Worked example`, at least two numbered package descriptors in that section, and holistic-LOW wording.
- The X set: all three target docs contain `ACR-179`, `ACR-154`, and `ACR-180`.
- Historical mentions, comments, or planning artifacts outside the named absolute target paths do not satisfy or fail these anchor checks.
- The known `tools.workflow_index check` failure on `/home/nes/ai/workflows/eval-runtime.md` is out of scope; the routing-anchor check reads `/home/nes/ai/workflows/index.json` directly.

## Future runnable-detector requirements

This eval ships in `WRITE` lifecycle state per `~/ai/conventions/evals.md`; no runnable detector is required to exist. The notes here are guidance for future runnable-detector tickets that may follow ACR-186, not a Step 6c implementation directive for this WU. ACR-186 itself ships the spec only, per `${worktree_path}/DECISIONS.md` § `D-2026-05-13-acr186-reject-pytest-on-markdown-scope-reduction`.

A future runnable detector for the seven anchor sets (W1-W4, O1-O2, C1-C3, R1-R4, P1-P3, E1-E3, X1-X3) must:

- Expose the trace fields by process behavior: invocation argv, exit code, stdout on success, stderr on failure, failed AC ID, evidence path, and evidence excerpt or observed value (governed by assumptions A3, A4, A5).
- Exit 0 when every assertion in `## Positive evidence` is satisfied; exit non-0 with stderr `FAIL <AC_ID>: <evidence>` when an assertion fails.
- Read targets via the absolute paths under `/home/nes/ai/` named in `## Positive evidence`.

The detector implementation strategy is open for the future ticket. The pytest-on-markdown variant (per-anchor `tests/test_*.py` scripts that regex-scrape Markdown headers / frontmatter / cross-reference tokens) is forbidden by ACR-174 (deletion of the entire pytest-on-markdown surface) and ACR-199 (anti-regression scope explicitly forbidding both `tests/test_*.py` and `tools/<wu>-verify/` variants). Likely-acceptable strategies include integration with `~/ai/workflows/eval-runtime.md` once it is wired, or another detector form a future ticket designs.

## Finding shape

The finding preserves these required keys:

- `test_id`
- `failed_ac`
- `evidence_path`
- `evidence_excerpt`

Allowed extensions include `observed_value`, `expected_token`, `json_path`, `section_header`, `section_range`, `parse_error`, `exit_code`, `stdout`, and `stderr`.

## Suggested action

Return `revise-docs`. The failing doc or routing surface is the one to fix: `/home/nes/ai/workflows/refactoring-commit-history.md`, `/home/nes/ai/agents/refactoring-commit-history-orchestrator.md`, `/home/nes/ai/conventions/refactoring-commit-history-scoping.md`, `/home/nes/ai/AGENTS.md`, or `/home/nes/ai/workflows/index.json`. Do not weaken the structural test to make a drifted source pass.

## Lifecycle notes

ACR-186 seeds this eval-spec in `WRITE` per `~/ai/conventions/evals.md`. No runnable detector is required to exist for `WRITE`; the regression-guard contract is this spec plus future runnable-detector tickets. ACR-186 itself does NOT ship a Step 6c runnable detector — the user-driven scope reduction recorded in `${worktree_path}/DECISIONS.md` § `D-2026-05-13-acr186-reject-pytest-on-markdown-scope-reduction` retracted the seven `tests/test_refactoring_commit_history_*.py` scripts originally drafted in Step 6c R3 (pytest-on-markdown anti-pattern per ACR-174).

A future runnable detector (when one is authored) should: avoid third-party YAML libraries, avoid pytest dependency, avoid shared `conftest.py`, avoid the repo-wide workflow-index check, and avoid the ACR-137 verifier. Likely-acceptable primitives if Python is the chosen detector language: direct file reads, `json`, `re`, `pathlib`, `sys`, and minimal inline frontmatter or Markdown-section parsing. If Python is chosen, the detector must NOT mutate `sys.path` and must NOT depend on a project-relative `sys.path` insertion. Targets are read via the absolute paths under `/home/nes/ai/` named in `## Positive evidence`. Other detector languages are equally acceptable provided they meet the trace-field and exit-semantics requirements above.

The target paths are absolute `/home/nes/ai/` paths because ACR-182's docs and routing files live in the canonical `~/ai` checkout. The worktree only owns the new eval-spec; future runnable-detector tickets may decide where the detector code lives, subject to the ACR-174/ACR-199 constraints (no `tests/test_*.py` pytest-on-markdown, no `tools/<wu>-verify/` scripts).

## References

- Ticket: `https://linear.app/neshq/issue/ACR-186/acr-182-follow-up-refactoring-commit-history-structural-test`
- ACR-186 Step 6a contract: `/home/nes/projects/ai/planning/acr-186-refactoring-commit-history-structural-test/contracts/acr-186-refactoring-commit-history-structural-test.md`
- ACR-186 proposal: `/home/nes/projects/ai/planning/acr-186-refactoring-commit-history-structural-test/proposals/acr-186-ACR-186.md`
- ACR-186 coverage inventory: `/home/nes/projects/ai/planning/acr-186-refactoring-commit-history-structural-test/research/acr-186-coverage-inventory.md`
- Workflow doc: `/home/nes/ai/workflows/refactoring-commit-history.md`
- Orchestrator doc: `/home/nes/ai/agents/refactoring-commit-history-orchestrator.md`
- Convention doc: `/home/nes/ai/conventions/refactoring-commit-history-scoping.md`
- AGENTS routing: `/home/nes/ai/AGENTS.md`
- Workflows index: `/home/nes/ai/workflows/index.json`
