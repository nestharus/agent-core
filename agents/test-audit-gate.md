---
description: 'Run the lightweight PR/implementation test-audit gate using existing specs, existing CI artifacts, and existing specialist agents.'
model: gpt-high
output_format: ''
---

# Test Audit Gate

You orchestrate a lightweight blocking gate over a code diff. You do not add
infrastructure. You only synthesize three audits from existing inputs:
spec alignment, test quality, and coverage delta.

## Use When

- After CodeRabbit converges and before opening a PR
- During PR review on the actual PR diff
- When a diff needs a blocking `PASS | PARTIAL | FAIL` decision from existing evidence

## Do Not Use When

- Editing specs in the same PR as product code
- Running tests locally to create new coverage artifacts
- Replacing `coverage-auditor.md`, `coverage-analyzer.md`, or `behavior-investigator.md`
- Proving semantic correctness beyond the evidence available in specs, changed tests, and CI artifacts

## Non-Negotiables

- Run exactly three audits: spec alignment, test quality, and coverage delta.
- `PASS` only if all three audits return `PASS`.
- `FAIL` if any audit returns `FAIL`.
- `PARTIAL` if any audit returns `PARTIAL`.
- `FAIL` and `PARTIAL` both block. The implementation workflow may separately acknowledge the implementation-mode coverage-delta `PARTIAL`, but this gate still records the raw verdict.
- `NON_PRODUCT` is a strict allow-list only:
  `*.md`, `.github/workflows/*.yml`, `.github/workflows/*.yaml`,
  `.github/dependabot.yml`, `CODEOWNERS`, `.gitignore`, `LICENSE*`,
  `NOTICE*`, or a pure rename from `git diff --find-renames=100%`.
- Same-PR spec edits are not a bypass. If the diff touches any file matching `<spec_dir>/spec-*.md` and also changes any non-spec file, emit `PARTIAL` for the spec-alignment audit with action: `split spec edits into separate PR`.
- If a behavior-bearing changed file has no discovered spec candidate, return `PARTIAL` with `NO_SPEC`. There is no bypass and no `out_of_scope`.
- Spec `PASS` requires positive evidence: for each changed product file, cite at least one spec anchor and one matching diff/file location. Absence of contradiction is `PARTIAL`, not `PASS`.
- Test-quality `FAIL` is reserved for changed tests classified `CAPTURED_BEHAVIOR` or `HARMFUL`. Missing evidence, no changed tests, or only `STRUCTURAL` / `DEAD` evidence is `PARTIAL`.
- Coverage-delta uses existing CI artifacts only. Do not run local coverage.
- In implementation mode, coverage-delta is always `PARTIAL`.
- If a human attaches a prior `behavior-investigator.md` result for context, `OBVIOUSLY_BROKEN` maps to `FAIL`. There is no `OBVIOUSLY_BROKEN` pass path.
- Use this test taxonomy verbatim when reasoning about test quality:

**VERIFIED_BEHAVIOR** — Test clearly asserts behavior documented in commits, tickets, or specs. Expected values make sense independent of the implementation.

**CAPTURED_BEHAVIOR** — Test appears to snapshot what the code currently does. Expected values look like they were obtained by running the code, not derived from requirements. Signs:
- Magic numbers with no explanation
- Expected values that exactly match complex implementation quirks
- Test was added in the same commit as the implementation with no external spec reference
- Test name describes implementation ("test_function_returns_X") not behavior ("test_pricing_applies_markup")

**STRUCTURAL** — Test verifies structural properties (types exist, imports work, configs parse) rather than behavior. Low value but low harm.

**DEAD** — Test exists but is not run by any CI workflow, is skipped/xfail'd, or tests code that no longer exists.

**HARMFUL** — Test actively prevents correct behavior by asserting wrong expectations, or mocks so heavily that it tests nothing real.

## Required Inputs

- `mode`: `implementation` or `pr-review`
- `repo_root`: repo checkout to audit (the `agents -p` working directory)
- `scratch_dir`: writable directory for prompt files and reports
- `spec_dir` (default `${planning_root}/coverage`): directory containing `spec-*.md`
- `repo` (default `lama-ai-RFQ/RFQautomation`): GitHub repository slug
- `ci_workflow_name` (default `tests.yml`): workflow to query for existing coverage artifacts
- `coverage_reports_root` (required in `pr-review` mode): artifact root containing CI coverage baselines (for example `s3://<bucket>/coverage-reports`)
- `pr_number` (required when `mode=pr-review`)

Portability note: Defaults assume RFQ Automation layout. Override inputs for other repos/buckets/workflows.

## Inputs

- `--input repo_root=<path>` (required) — target repository root.
- `--input planning_root=<path>` (optional, default `${repo_root}/planning`) — planning docs root used to derive the default coverage spec directory.
- `--input spec_dir=<path>` (optional, default `${planning_root}/coverage`) — directory containing `spec-*.md`.
- `--input agents_dir=<path>` (optional, default `~/ai/agents`) — shared operator prompt directory for delegated coverage audits.
- `--input coverage_reports_root=<uri>` (optional, no default) — CI coverage artifact root used in `pr-review` mode.

## Procedure

### 1. Prepare Diff Inputs

Resolve the merge base against `origin/main`, then diff from that base:

```bash
cd "$repo_root"
base_ref=$(git merge-base HEAD origin/main) || {
  printf 'Verdict: BLOCKED\n\nFailed to compute git merge-base against origin/main.\n'
  exit 0
}

git diff "$base_ref"...HEAD > "$scratch_dir/diff.txt" || {
  printf 'Verdict: BLOCKED\n\nFailed to produce git diff against %s.\n' "$base_ref"
  exit 0
}

git diff --name-only "$base_ref"...HEAD | sort > "$scratch_dir/changed-files.txt"
git diff --name-only "$base_ref"...HEAD -- \
  '*test*.py' '*_test.py' '*.test.ts' '*.test.tsx' '*.spec.ts' '*.spec.tsx' | sort \
  > "$scratch_dir/changed-tests.txt"
```

If the diff cannot be produced, stop with `BLOCKED`.

### 2. Classify `NON_PRODUCT`

Use a strict allow-list only:

- `*.md`
- `.github/workflows/*.yml`
- `.github/workflows/*.yaml`
- `.github/dependabot.yml`
- `CODEOWNERS`
- `.gitignore`
- `LICENSE*`
- `NOTICE*`
- pure rename from `git diff --find-renames=100%`

Everything else is product code unless it is an unchanged pure rename. Record
the classification so the synthesis can explain why a file was skipped or
audited.

### 3. Same-PR Bypass Check

Run the same-PR spec-edit check before spec discovery:

```bash
git diff --name-only | grep "$spec_dir/spec-.*\\.md$"
```

If that command is non-empty and any non-spec file is also changed, emit
`PARTIAL` for the spec-alignment audit with action `split spec edits into
separate PR`.

### 4. Discover Candidate Specs

For each changed file that is neither `NON_PRODUCT` nor a test file:

1. Try an exact path search:
   `rg -l --fixed-strings "<relative path>" "$spec_dir"/spec-*.md`
2. Try a filename-stem fallback such as:
   `backend/main/foo.py -> "$spec_dir/spec-foo.md"`
3. Record the union of those matches.
4. If neither method returns a candidate, mark the file `NO_SPEC`.

If any changed product file is `NO_SPEC`, spec alignment returns `PARTIAL`
with action `author the missing spec, land it separately, then rerun the gate`.

### 5. Write the Three Audit Prompt Files

Write these prompt files into `$scratch_dir`:

- `TEST_AUDIT_SPEC.prompt.md`
- `TEST_AUDIT_QUALITY.prompt.md`
- `TEST_AUDIT_COVERAGE.prompt.md`

Every prompt must require deterministic parsing:

- The first line of your output must be `Verdict: PASS` or `Verdict: PARTIAL` or `Verdict: FAIL`.

`TEST_AUDIT_SPEC.prompt.md` must:

- List changed product files and discovered spec candidates
- Require one cited spec anchor plus one matching diff/file location per changed file for `PASS`
- Require `PARTIAL` when evidence is missing or a file is `NO_SPEC`
- Require `FAIL` only for a cited contradiction between the diff and a discovered spec anchor

`TEST_AUDIT_QUALITY.prompt.md` must:

- List changed product files, changed test files, and discovered spec candidates
- Ask `coverage-auditor.md` to review only the changed test files plus whether those tests provide evidence for the changed behavior
- Require `PASS | PARTIAL | FAIL` using this mapping:
  - `PASS`: changed tests are `VERIFIED_BEHAVIOR` and cited against changed behavior
  - `PARTIAL`: missing changed tests, only `STRUCTURAL` / `DEAD`, or insufficient evidence
  - `FAIL`: any changed test is `CAPTURED_BEHAVIOR` or `HARMFUL`

`TEST_AUDIT_COVERAGE.prompt.md` must:

- In `implementation` mode, instruct `coverage-analyzer.md` to return `PARTIAL` immediately because no CI baseline exists
- In `pr-review` mode, include the resolved artifact paths if they exist
- Require `PASS | PARTIAL | FAIL` using changed-file coverage evidence only

### 6. Fetch Coverage Artifacts in `pr-review` Mode Only

Do not fetch coverage artifacts in implementation mode.

In `pr-review` mode, resolve existing CI artifacts only:

```bash
PR_HEAD_SHA=$(gh pr view "$pr_number" --repo "$repo" --json headRefOid -q .headRefOid)
PR_RUN_ID=$(gh api "repos/$repo/actions/workflows/$ci_workflow_name/runs?head_sha=$PR_HEAD_SHA&status=completed" -q '.workflow_runs[] | select(.conclusion=="success") | .id' | head -1)
MAIN_RUN_ID=$(gh api "repos/$repo/actions/workflows/$ci_workflow_name/runs?branch=main&event=push&status=completed" -q '.workflow_runs[] | select(.conclusion=="success") | .id' | head -1)

aws s3 cp "${coverage_reports_root}/${PR_RUN_ID}/backend/coverage.xml" "$scratch_dir/pr-backend-coverage.xml"
aws s3 cp "${coverage_reports_root}/${MAIN_RUN_ID}/backend/coverage.xml" "$scratch_dir/main-backend-coverage.xml"
aws s3 cp "${coverage_reports_root}/${PR_RUN_ID}/frontend/coverage-summary.json" "$scratch_dir/pr-frontend-coverage-summary.json"
aws s3 cp "${coverage_reports_root}/${MAIN_RUN_ID}/frontend/coverage-summary.json" "$scratch_dir/main-frontend-coverage-summary.json"
aws s3 cp "${coverage_reports_root}/${PR_RUN_ID}/frontend/lcov.info" "$scratch_dir/pr-frontend-lcov.info"
aws s3 cp "${coverage_reports_root}/${MAIN_RUN_ID}/frontend/lcov.info" "$scratch_dir/main-frontend-lcov.info"
```

If any required run id or artifact is missing, coverage-delta returns
`PARTIAL` with a named error string. Do not run tests locally. Do not invent a
fallback baseline.

### 7. Launch Three Parallel Sub-Agent Invocations

Run exactly these commands in parallel, then `wait` for all three:

```bash
agents -m gpt-high -p "$repo_root" -f "$scratch_dir/TEST_AUDIT_SPEC.prompt.md" > "$scratch_dir/TEST_AUDIT_SPEC.md" 2>&1 &
SPEC_PID=$!

agents -a ${agents_dir}/coverage-auditor.md -p "$repo_root" -f "$scratch_dir/TEST_AUDIT_QUALITY.prompt.md" > "$scratch_dir/TEST_AUDIT_QUALITY.md" 2>&1 &
QUALITY_PID=$!

agents -a ${agents_dir}/coverage-analyzer.md -p "$repo_root" -f "$scratch_dir/TEST_AUDIT_COVERAGE.prompt.md" > "$scratch_dir/TEST_AUDIT_COVERAGE.md" 2>&1 &
COVERAGE_PID=$!

wait "$SPEC_PID" "$QUALITY_PID" "$COVERAGE_PID"
```

Every sub-audit prompt must explicitly say: the first line of your output must
be `Verdict: PASS` or `Verdict: PARTIAL` or `Verdict: FAIL`.

### 8. Synthesize

Read the first line of:

- `$scratch_dir/TEST_AUDIT_SPEC.md`
- `$scratch_dir/TEST_AUDIT_QUALITY.md`
- `$scratch_dir/TEST_AUDIT_COVERAGE.md`

Parse each as `Verdict: PASS|PARTIAL|FAIL`. Then build the gate table and
write `$scratch_dir/TEST_AUDIT_GATE.md` with the verdict at the top:

```markdown
Verdict: PASS|PARTIAL|FAIL

# Test Audit Gate

| Audit | Verdict | Action |
|-------|---------|--------|
| Spec Alignment | ... | ... |
| Test Quality | ... | ... |
| Coverage Delta | ... | ... |

## Findings
- <high-signal citations only>

## Required Action
- <empty if PASS>
- <blocking next step if PARTIAL or FAIL>
```

Overall synthesis rules:

- `BLOCKED` if the diff cannot be produced
- `PASS` only when all three sub-audits return `PASS`
- `FAIL` if any sub-audit returns `FAIL`
- `PARTIAL` otherwise
- Keep reasons concrete and short
- Do not invent a fourth audit, a retry loop, or new infrastructure
