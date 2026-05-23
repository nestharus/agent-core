---
description: 'Run the lightweight PR/implementation test-audit gate using existing specs, locally-generated coverage, and existing specialist agents.'
model: gpt-high
output_format: ''
---

# Test Audit Gate

## Contract

```yaml
schema: operator-contract-v1
inputs:
  - name: mode
    type: enum
    required: true
    default_source: caller
    description: "mode"
  - name: repo_root
    type: path
    required: true
    default_source: caller
    description: "repo root"
  - name: scratch_dir
    type: path
    required: true
    default_source: caller
    description: "scratch dir"
  - name: planning_root
    type: path
    required: false
    default_source: base
    description: "planning root"
  - name: spec_dir
    type: path
    required: false
    default_source: derived
    description: "spec dir"
  - name: agents_dir
    type: path
    required: false
    default_source: base
    description: "agents dir"
  - name: repo
    type: string
    required: false
    default_source: caller
    description: "repo"
  - name: local_coverage_command
    type: string
    required: false
    default_source: caller
    description: "shell command run from repo_root that produces coverage-summary.json and lcov.info under the current working directory's ./coverage/ subdir"
  - name: pr_number
    type: int
    required: false
    default_source: caller
    description: "pr number (used only for synthesis labeling)"
defaults:
  - name: planning_root
    value: ${repo_root}/planning
    source: base
  - name: agents_dir
    value: ~/ai/agents
    source: base
secrets:
  []
outputs:
  - task: audit-tests
    success_shape: "Task-specific stdout or durable artifact paths named by the procedure."
    wrote_lines: []
errors:
  - class: BLOCKED
    cause: "Required inputs are missing, unreadable, contradictory, or unsafe for the selected task."
    recovery: "Supply corrected inputs or select the appropriate operator wrapper before rerun."
  - class: NEEDS_INPUT
    cause: "A user-owned value, scope, or trade-off question is required."
    recovery: "Answer the emitted question artifact and resume."
side_effects:
  - test-audit-report-writes
must_delegate:
  - coverage-analyzer
  - coverage-auditor
may_direct:
  - local-coverage-generation
  - git-diff-read
  - git-worktree-baseline-checkout
forbidden_direct:
  - fetching-ci-coverage-artifacts
```

You orchestrate a lightweight blocking gate over a code diff. You do not add
infrastructure. You only synthesize three audits from existing inputs:
spec alignment, test quality, and coverage delta.

## Use When

- After CodeRabbit converges and before opening a PR
- During PR review on the actual PR diff
- When a diff needs a blocking `PASS | PARTIAL | FAIL` decision from existing evidence

## Do Not Use When

- Editing specs in the same PR as product code
- Fetching coverage from GitHub Actions / CI workflow artifacts
- Replacing `coverage-auditor.md`, `coverage-analyzer.md`, or `behavior-investigator.md`
- Proving semantic correctness beyond the evidence available in specs, changed tests, and locally-generated coverage

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
- Coverage-delta uses locally-generated coverage runs against the PR HEAD and the merge base. Do not fetch CI workflow artifacts. Do not call `gh api .../actions/workflows/...` or `aws s3 cp` for coverage.
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

## Inputs

- `--input mode=implementation|pr-review` (required) — gate mode.
- `--input repo_root=<path>` (required) — target repository root.
- `--input scratch_dir=<path>` (required) — writable directory for prompt files and reports.
- `--input planning_root=<path>` (optional, default `${repo_root}/planning`) — planning docs root used to derive the default coverage spec directory.
- `--input spec_dir=<path>` (optional, default `${planning_root}/coverage`) — directory containing `spec-*.md`.
- `--input agents_dir=<path>` (optional, default `~/ai/agents`) — shared operator prompt directory for delegated coverage audits.
- `--input repo=<owner/name>` (optional) — GitHub repository slug, used only for report labeling.
- `--input local_coverage_command=<command>` (required in `pr-review` mode) — shell command run from a checkout of either the PR HEAD or the merge base that produces `coverage/coverage-summary.json` and `coverage/lcov.info` relative to the checkout root. Example for a Rust workspace: `cargo llvm-cov --workspace --no-report && cargo llvm-cov report --json --summary-only --output-path coverage/coverage-summary.json && cargo llvm-cov report --lcov --output-path coverage/lcov.info`.
- `--input pr_number=<number>` (optional in `pr-review` mode) — PR number for synthesis labeling only; no GitHub API calls are made with it.
- `--input report_artifact_path=<path>` (optional) — local path to a generated report bundle or downloaded artifact bundle.
- `--input report_pdf_path=<path>` (optional) — canonical PDF path for the test report when a report bundle is required.
- `--input report_artifact_url=<url>` (optional) — uploaded artifact URL for PR-review synthesis.

## Procedure

### Pre-dispatch read protocol

Before any child-operator, workflow, ticket-operator, auditor, proposer, reviewer, or role dispatch:

1. Resolve the intended operator name and file path from workflow context and the current project scope.
2. Prefer the current project's wrapper when one exists for that operator and task, for example `~/projects/<name>/agents/<operator>.md` before `~/ai/agents/<operator>.md`.
3. Read the selected operator contract sidecar when present; otherwise read the selected operator file's `## Contract` block.
4. Apply wrapper or base defaults only from declared `defaults:` entries, and apply secrets only from declared `secrets:` entries. Do not fill defaults from session metadata or ambient environment values unless the selected contract declares that source.
5. Validate that every required input for the chosen task is present after declared defaults are applied.
6. Refuse direct operations covered by the selected contract's `must_delegate:` list unless the contract explicitly allows the direct operation through `may_direct:`.
7. Compose the dispatch prompt with only inputs, task variant, anti-scope, stop conditions, and evidence paths. Do not include the selected operator's procedure mechanics, phase order, command recipes, or verdict handling.


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
- When report artifacts are present or required, ask `coverage-auditor.md` to verify `~/ai/conventions/test-reports.md`: canonical PDF, UI screenshots, non-UI evidence, `file_path:line_number` citations, and exact fenced code blocks for code claims
- Ask `coverage-auditor.md` to apply `~/ai/conventions/testing.md` when auditing new tests
- Require `PASS | PARTIAL | FAIL` using this mapping:
  - `PASS`: changed tests are `VERIFIED_BEHAVIOR` and cited against changed behavior
  - `PARTIAL`: missing changed tests, only `STRUCTURAL` / `DEAD`, or insufficient evidence
  - `FAIL`: any changed test is `CAPTURED_BEHAVIOR` or `HARMFUL`

`TEST_AUDIT_COVERAGE.prompt.md` must:

- In `implementation` mode, instruct `coverage-analyzer.md` to return `PARTIAL` immediately because no CI baseline exists
- In `pr-review` mode, include the resolved artifact paths if they exist
- Require `PASS | PARTIAL | FAIL` using changed-file coverage evidence only

### 6. Generate Coverage Locally in `pr-review` Mode Only

Do not generate coverage in implementation mode.

In `pr-review` mode, run `local_coverage_command` twice: once against the PR
HEAD (the current working tree at `repo_root`) and once against the merge-base
commit via a detached worktree. Persist both result sets into `scratch_dir`
under deterministic filenames so the coverage prompt can cite them. There are
no GitHub API calls and no remote artifact fetches in this step.

```bash
cd "$repo_root"
base_ref=$(git merge-base HEAD origin/main) || {
  printf 'Verdict: BLOCKED\n\nFailed to compute git merge-base against origin/main.\n'
  exit 0
}

# PR HEAD coverage
mkdir -p coverage
bash -c "$local_coverage_command" || {
  printf 'Verdict: PARTIAL\n\nLocal coverage command failed against PR HEAD.\n'
  exit 0
}
cp coverage/coverage-summary.json "$scratch_dir/pr-coverage-summary.json"
cp coverage/lcov.info             "$scratch_dir/pr-lcov.info"

# Merge-base coverage via detached worktree (does not disturb repo_root)
base_worktree="$scratch_dir/baseline-worktree"
git worktree add --detach "$base_worktree" "$base_ref"
(
  cd "$base_worktree"
  mkdir -p coverage
  bash -c "$local_coverage_command"
)
cp "$base_worktree/coverage/coverage-summary.json" "$scratch_dir/main-coverage-summary.json"
cp "$base_worktree/coverage/lcov.info"             "$scratch_dir/main-lcov.info"
git worktree remove --force "$base_worktree"
```

If either run cannot produce the required `coverage/coverage-summary.json` +
`coverage/lcov.info` pair, coverage-delta returns `PARTIAL` with a named error
string. Do not fall back to fetching CI artifacts. Do not invent a synthetic
baseline.

### 7. Launch Three Parallel Sub-Agent Invocations

`~/ai/workflows/agents-cli.md` is the canonical dispatch/wait rule. Run exactly these as three separate Bash-background tool invocations, then collect the result files after all task notifications arrive:

```python
Bash(command='agents -m gpt-high -p "$repo_root" -f "$scratch_dir/TEST_AUDIT_SPEC.prompt.md" 2>&1 | tee "$scratch_dir/TEST_AUDIT_SPEC.md"', run_in_background=True, description="Run test-audit spec review")
Bash(command='agents -a ${agents_dir}/coverage-auditor.md -p "$repo_root" -f "$scratch_dir/TEST_AUDIT_QUALITY.prompt.md" 2>&1 | tee "$scratch_dir/TEST_AUDIT_QUALITY.md"', run_in_background=True, description="Run test-audit quality review")
Bash(command='agents -a ${agents_dir}/coverage-analyzer.md -p "$repo_root" -f "$scratch_dir/TEST_AUDIT_COVERAGE.prompt.md" 2>&1 | tee "$scratch_dir/TEST_AUDIT_COVERAGE.md"', run_in_background=True, description="Run test-audit coverage review")
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

## Report Artifacts
- Canonical PDF: `<report_pdf_path or none>`
- Bundle: `<report_artifact_path or none>`
- Artifact URL: `<report_artifact_url or none>`

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
