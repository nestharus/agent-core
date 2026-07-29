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
  - name: base_ref
    type: string
    required: false
    default_source: derived
    description: "Parent ref used for the reviewed diff and baseline coverage worktree; derived only as refs/remotes/origin/${base_branch} from the required caller-owned base branch when omitted."
  - name: base_branch
    type: string
    required: true
    default_source: caller
    description: "Caller-owned short provider base name; missing or blank values block and no default branch is inferred."
  - name: base_sha
    type: string
    required: false
    default_source: caller
    description: "Full expected commit resolved from base_ref."
  - name: head_branch
    type: string
    required: false
    default_source: caller
    description: "Short provider head name; required with pinned PR-review composition."
  - name: head_ref
    type: string
    required: false
    default_source: caller
    description: "Exact reviewed head ref."
  - name: head_sha
    type: string
    required: false
    default_source: caller
    description: "Full expected commit resolved from head_ref."
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
    description: "Required and non-blank in pr-review mode; optional and unused for coverage generation in implementation mode. When present, it is hashed into the result."
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
    success_shape: "test-audit-result-v2 plus TEST_AUDIT_GATE.md, with a top-line PASS, PARTIAL, or FAIL verdict and an independently audited, hash-current three-child nested process proof whose process-auditor report uses the canonical header-first report and producer-owned exact-blocking-mode machine binding."
    wrote_lines:
      - ${scratch_dir}/TEST_AUDIT_EXPECTED_PROCESS.json
      - ${scratch_dir}/TEST_AUDIT_DISPATCH_EVIDENCE.json
      - ${scratch_dir}/TEST_AUDIT_SPEC.log
      - ${scratch_dir}/TEST_AUDIT_SPEC.md
      - ${scratch_dir}/TEST_AUDIT_SPEC.extraction.json
      - ${scratch_dir}/TEST_AUDIT_QUALITY.log
      - ${scratch_dir}/TEST_AUDIT_QUALITY.md
      - ${scratch_dir}/TEST_AUDIT_QUALITY.extraction.json
      - ${scratch_dir}/TEST_AUDIT_COVERAGE.log
      - ${scratch_dir}/TEST_AUDIT_COVERAGE.md
      - ${scratch_dir}/TEST_AUDIT_COVERAGE.extraction.json
      - ${scratch_dir}/TEST_AUDIT_PROCESS_TREE.json
      - ${scratch_dir}/TEST_AUDIT_PROCESS_AUDIT.prompt.md
      - ${scratch_dir}/TEST_AUDIT_PROCESS_AUDIT.log
      - ${scratch_dir}/TEST_AUDIT_PROCESS_AUDIT.md
      - ${scratch_dir}/TEST_AUDIT_NESTED_PROOF.json
      - ${scratch_dir}/TEST_AUDIT_NESTED_PROOF_VALIDATION.json
      - ${scratch_dir}/TEST_AUDIT_GATE.md
      - ${scratch_dir}/TEST_AUDIT_RESULT.json
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
  - process-tree-auditor
may_direct:
  - local-coverage-generation
  - git-diff-read
  - git-worktree-baseline-checkout
  - git-worktree-head-checkout
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
- Require non-blank caller-owned `base_branch`. When `base_ref` is omitted, derive only `refs/remotes/origin/${base_branch}` after fetching that exact branch; never infer `main`, `origin/main`, or the repository default branch. An explicitly supplied empty, mismatched, or unresolvable ref is `BLOCKED:invalid-base-ref` without fallback.
- PR-review composition supplies the full base/head branch/ref/SHA identity. Resolve both refs, require exact full-SHA equality, and never use ambient `HEAD`; any mismatch is `BLOCKED:pinned-review-identity-mismatch`.
- In `pr-review` mode, blank or absent `local_coverage_command` is `BLOCKED:missing-local-coverage-command` before coverage work.
- Every `agents` invocation tees its complete merged runner stream to a dedicated `.log` containing exactly one valid `OULIPOLY_INVOCATION` marker and one terminal successful `OULIPOLY_RESULT` sentinel. A `.log` path never aliases a canonical `.md` report.
- These three children produce their canonical verdicts on stdout. Extract each provider payload only with `tools/operational_contracts.py extract-provider-payload`; never parse, trim, copy, or synthesize a verdict directly from the runner log.
- Derive the current test-audit invocation UUID only from runner provenance in `OULIPOLY_PARENT_INVOCATION`. The expected manifest declares all three children with `parent=root`; post-dispatch evidence must show each actual child parent equals that exact root UUID.
- The three-child fanout is not accepted from file presence or this operator's synthesis. Capture the root trace, dispatch `process-tree-auditor` in blocking mode, and require the hash-bound nested proof to pass `tools/operational_contracts.py validate-test-audit-proof` before writing `TEST_AUDIT_GATE.md`.
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
- `--input base_branch=<short-branch>` (required) — caller-owned parent/trunk policy for every mode; omission or blank input blocks without fallback.
- `--input base_ref=<ref>` (optional, derived only as `refs/remotes/origin/${base_branch}`) — actual parent ref for the reviewed diff and baseline coverage worktree. An explicit empty, invalid, or differently named value blocks without fallback.
- `--input base_sha/head_branch/head_ref/head_sha` (required together for PR-review composition) — pinned provider identity; explicit mismatch blocks without fallback.
- `--input planning_root=<path>` (optional, default `${repo_root}/planning`) — planning docs root used to derive the default coverage spec directory.
- `--input spec_dir=<path>` (optional, default `${planning_root}/coverage`) — directory containing `spec-*.md`.
- `--input agents_dir=<path>` (optional, default `~/ai/agents`) — shared operator prompt directory for delegated coverage audits.
- `--input repo=<owner/name>` (optional) — GitHub repository slug, used only for report labeling.
- `--input local_coverage_command=<command>` (required in `pr-review` mode; optional and unused for coverage generation in `implementation` mode) — shell command run from a checkout of either the PR HEAD or the merge base that produces `coverage/coverage-summary.json` and `coverage/lcov.info` relative to the checkout root. Example for a Rust workspace: `cargo llvm-cov --workspace --no-report && cargo llvm-cov report --json --summary-only --output-path coverage/coverage-summary.json && cargo llvm-cov report --lcov --output-path coverage/lcov.info`.
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

Freshly fetch the required caller-owned `refs/heads/${base_branch}:refs/remotes/origin/${base_branch}`. Derive an omitted `base_ref` only from that exact branch, resolve both pinned refs, and diff only the full commit pair. Standalone implementation mode may derive `head_ref=HEAD`; PR-review mode may not.

```bash
cd "$repo_root"
if [ -z "${base_branch+x}" ] || [ -z "${base_branch//[[:space:]]/}" ]; then
  printf 'Verdict: BLOCKED\n\nBLOCKED:invalid-base-branch\n'
  exit 0
fi
derived_base_ref="refs/remotes/origin/${base_branch}"
git fetch origin "refs/heads/${base_branch}:${derived_base_ref}" || {
  printf 'Verdict: BLOCKED\n\nBLOCKED:invalid-base-ref: %s\n' "$base_branch"
  exit 0
}
if [ "${base_ref+x}" = x ] && { [ -z "$base_ref" ] || [ "$base_ref" != "$derived_base_ref" ]; }; then
  printf 'Verdict: BLOCKED\n\nBLOCKED:invalid-base-ref: %s\n' "$base_ref"
  exit 0
fi
base_ref="${base_ref:-$derived_base_ref}"
resolved_base_ref=$(git rev-parse --verify "${base_ref}^{commit}") || {
  printf 'Verdict: BLOCKED\n\nBLOCKED:invalid-base-ref: %s\n' "$base_ref"
  exit 0
}
if [ -n "${base_sha:-}" ] && [ "$resolved_base_ref" != "$base_sha" ]; then
  printf 'Verdict: BLOCKED\n\nBLOCKED:pinned-review-identity-mismatch: base\n'
  exit 0
fi
if [ "$mode" = "pr-review" ] && { [ -z "${head_ref+x}" ] || [ -z "${head_ref//[[:space:]]/}" ]; }; then
  printf 'Verdict: BLOCKED\n\nBLOCKED:missing-pinned-head-ref\n'
  exit 0
fi
resolved_head_ref=$(git rev-parse --verify "${head_ref:-HEAD}^{commit}") || {
  printf 'Verdict: BLOCKED\n\nBLOCKED:invalid-head-ref: %s\n' "${head_ref:-HEAD}"
  exit 0
}
if [ -n "${head_sha:-}" ] && [ "$resolved_head_ref" != "$head_sha" ]; then
  printf 'Verdict: BLOCKED\n\nBLOCKED:pinned-review-identity-mismatch: head\n'
  exit 0
fi
merge_base_sha=$(git merge-base "$resolved_head_ref" "$resolved_base_ref") || {
  printf 'Verdict: BLOCKED\n\nFailed to compute git merge-base against %s.\n' "$base_ref"
  exit 0
}

git diff "$merge_base_sha"..."$resolved_head_ref" > "$scratch_dir/diff.txt" || {
  printf 'Verdict: BLOCKED\n\nFailed to produce git diff against %s.\n' "$base_ref"
  exit 0
}

git diff --name-only "$merge_base_sha"..."$resolved_head_ref" | sort > "$scratch_dir/changed-files.txt"
git diff --name-only "$merge_base_sha"..."$resolved_head_ref" -- \
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
git diff --name-only "$merge_base_sha"..."$resolved_head_ref" | grep "$spec_dir/spec-.*\\.md$"
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

In `pr-review` mode, require non-blank `local_coverage_command` and run it twice: once in a detached worktree at exact `head_sha` and once in another detached worktree at the merge-base commit. Persist both result sets into `scratch_dir`
under deterministic filenames so the coverage prompt can cite them. There are
no GitHub API calls and no remote artifact fetches in this step.

```bash
cd "$repo_root"
git fetch origin "refs/heads/${base_branch}:refs/remotes/origin/${base_branch}" || {
  printf 'Verdict: BLOCKED\n\nBLOCKED:invalid-base-ref: %s\n' "$base_branch"
  exit 0
}
resolved_base_ref=$(git rev-parse --verify "${base_ref}^{commit}") || {
  printf 'Verdict: BLOCKED\n\nBLOCKED:invalid-base-ref: %s\n' "$base_ref"
  exit 0
}
resolved_head_ref=$(git rev-parse --verify "${head_ref}^{commit}") || {
  printf 'Verdict: BLOCKED\n\nBLOCKED:invalid-head-ref: %s\n' "$head_ref"
  exit 0
}
if [ "$resolved_base_ref" != "$base_sha" ] || [ "$resolved_head_ref" != "$head_sha" ]; then
  printf 'Verdict: BLOCKED\n\nBLOCKED:pinned-review-identity-mismatch\n'
  exit 0
fi
if [ -z "${local_coverage_command//[[:space:]]/}" ]; then
  printf 'Verdict: BLOCKED\n\nBLOCKED:missing-local-coverage-command\n'
  exit 0
fi
merge_base_sha=$(git merge-base "$resolved_head_ref" "$resolved_base_ref") || {
  printf 'Verdict: BLOCKED\n\nFailed to compute git merge-base against %s.\n' "$base_ref"
  exit 0
}

# Exact head and merge-base coverage via detached worktrees.
head_worktree="$scratch_dir/head-coverage-worktree"
base_worktree="$scratch_dir/baseline-worktree"
cleanup_coverage_worktrees() {
  git -C "$repo_root" worktree remove --force "$head_worktree" 2>/dev/null || true
  git -C "$repo_root" worktree remove --force "$base_worktree" 2>/dev/null || true
}
if [ -e "$head_worktree" ] || [ -L "$head_worktree" ] || [ -e "$base_worktree" ] || [ -L "$base_worktree" ]; then
  printf 'Verdict: BLOCKED\n\nBLOCKED:coverage-worktree-path-exists\n'
  exit 0
fi
trap cleanup_coverage_worktrees EXIT
git worktree add --detach "$head_worktree" "$head_sha" || {
  printf 'Verdict: BLOCKED\n\nBLOCKED:head-coverage-worktree-add-failed\n'
  exit 0
}
git worktree add --detach "$base_worktree" "$merge_base_sha" || {
  printf 'Verdict: BLOCKED\n\nBLOCKED:base-coverage-worktree-add-failed\n'
  exit 0
}
(
  cd "$head_worktree" &&
    mkdir -p coverage &&
    bash -c "$local_coverage_command"
) || {
  printf 'Verdict: BLOCKED\n\nBLOCKED:head-local-coverage-command-failed\n'
  exit 0
}
cp "$head_worktree/coverage/coverage-summary.json" "$scratch_dir/pr-coverage-summary.json" || {
  printf 'Verdict: BLOCKED\n\nBLOCKED:head-coverage-summary-copy-failed\n'
  exit 0
}
cp "$head_worktree/coverage/lcov.info" "$scratch_dir/pr-lcov.info" || {
  printf 'Verdict: BLOCKED\n\nBLOCKED:head-lcov-copy-failed\n'
  exit 0
}
(
  cd "$base_worktree" &&
    mkdir -p coverage &&
    bash -c "$local_coverage_command"
) || {
  printf 'Verdict: BLOCKED\n\nBLOCKED:base-local-coverage-command-failed\n'
  exit 0
}
cp "$base_worktree/coverage/coverage-summary.json" "$scratch_dir/base-coverage-summary.json" || {
  printf 'Verdict: BLOCKED\n\nBLOCKED:base-coverage-summary-copy-failed\n'
  exit 0
}
cp "$base_worktree/coverage/lcov.info" "$scratch_dir/base-lcov.info" || {
  printf 'Verdict: BLOCKED\n\nBLOCKED:base-lcov-copy-failed\n'
  exit 0
}
cleanup_coverage_worktrees
trap - EXIT
```

If either run cannot produce the required `coverage/coverage-summary.json` +
`coverage/lcov.info` pair, coverage-delta returns `PARTIAL` with a named error
string. Do not fall back to fetching CI artifacts. Do not invent a synthetic
baseline.

### 7. Launch Three Parallel Sub-Agent Invocations

`~/ai/workflows/agents-cli.md` is the canonical dispatch/wait rule. Derive `TEST_AUDIT_INVOCATION_UUID=$(printf '%s' "$OULIPOLY_PARENT_INVOCATION" | jq -er '.id')`; reject missing, multiple, non-canonical, or caller-supplied substitutes. Before dispatch, write immutable `$scratch_dir/TEST_AUDIT_EXPECTED_PROCESS.json` with `schema=test-audit-expected-process-v2`, that exact root UUID, exact pinned base/head SHAs, and stable nodes in this order: `spec-alignment`, `test-quality`, and `coverage-delta`. Each node records `required=true`, its exact operator/model, `parent=root`, prompt path and SHA-256, distinct `.log`, canonical `.md`, and extraction-metadata paths, `output_mode=stdout-extracted`, and named post-dispatch `log_sha256`, `canonical_output_sha256`, `extraction_metadata_sha256`, and `provider_source` join fields. The authoritative operator/model pairs are `ad-hoc-spec-alignment/gpt-high`, `coverage-auditor/gpt-xhigh`, and `coverage-analyzer/gpt-high`. No child UUID, provider source, or invented pre-dispatch log/output hash appears in this file.

Run exactly these as three separate Bash-background tool invocations, then wait for all task notifications. Each invocation's only shell sink is its dedicated complete log:

```python
Bash(command='agents -m gpt-high -p "$repo_root" -f "$scratch_dir/TEST_AUDIT_SPEC.prompt.md" 2>&1 | tee "$scratch_dir/TEST_AUDIT_SPEC.log"', run_in_background=True, description="Run test-audit spec review")
Bash(command='agents -a ${agents_dir}/coverage-auditor.md -p "$repo_root" -f "$scratch_dir/TEST_AUDIT_QUALITY.prompt.md" 2>&1 | tee "$scratch_dir/TEST_AUDIT_QUALITY.log"', run_in_background=True, description="Run test-audit quality review")
Bash(command='agents -a ${agents_dir}/coverage-analyzer.md -p "$repo_root" -f "$scratch_dir/TEST_AUDIT_COVERAGE.prompt.md" 2>&1 | tee "$scratch_dir/TEST_AUDIT_COVERAGE.log"', run_in_background=True, description="Run test-audit coverage review")
```

Every sub-audit prompt must explicitly say: the first line of your output must
be `Verdict: PASS` or `Verdict: PARTIAL` or `Verdict: FAIL`.

After all three notifications arrive, invoke the extraction helper separately for each completed log:

```bash
python3 ~/ai/tools/operational_contracts.py extract-provider-payload --log "$scratch_dir/TEST_AUDIT_SPEC.log" --output "$scratch_dir/TEST_AUDIT_SPEC.md" --metadata "$scratch_dir/TEST_AUDIT_SPEC.extraction.json"
python3 ~/ai/tools/operational_contracts.py extract-provider-payload --log "$scratch_dir/TEST_AUDIT_QUALITY.log" --output "$scratch_dir/TEST_AUDIT_QUALITY.md" --metadata "$scratch_dir/TEST_AUDIT_QUALITY.extraction.json"
python3 ~/ai/tools/operational_contracts.py extract-provider-payload --log "$scratch_dir/TEST_AUDIT_COVERAGE.log" --output "$scratch_dir/TEST_AUDIT_COVERAGE.md" --metadata "$scratch_dir/TEST_AUDIT_COVERAGE.extraction.json"
```

Fail on any missing, duplicate, malformed, out-of-order, non-success, or identity-mismatched envelope. Parse each actual child UUID and `provider_source` only from its complete `.log`; parse no UUID from a canonical report. Write immutable `$scratch_dir/TEST_AUDIT_DISPATCH_EVIDENCE.json` with `schema=test-audit-dispatch-evidence-v2`, the same root/base/head and expected-manifest path/hash, and each node's UUID, marker-derived provider source, declared operator/model, prompt path/hash, log path/hash, canonical output path/hash, extraction metadata path/hash, and output mode. The dispatch row is a role/artifact declaration, not authority for parent, model, source, status, or topology; those facts must be read from the saved trace and complete runner envelope. Every child artifact path is pairwise distinct.

Capture `agents trace --json "$TEST_AUDIT_INVOCATION_UUID"` at `$scratch_dir/TEST_AUDIT_PROCESS_TREE.json` only after all three children and dispatch evidence are final. Write `$scratch_dir/TEST_AUDIT_PROCESS_AUDIT.prompt.md` naming `operator_file=${repo_root}/agents/test-audit-gate.md`, `mode=blocking`, that exact root UUID, expected manifest, trace, and child-owned report `$scratch_dir/TEST_AUDIT_PROCESS_AUDIT.md`; list dispatch evidence, the audit prompt, and all three prompt/log/output/extraction artifacts as the exact hash-bound `companion_artifacts`. Dispatch the named auditor without a model override through one separate parent-visible Bash-background tool invocation:

```python
Bash(command='agents -a ${agents_dir}/process-tree-auditor.md -p "$repo_root" -f "$scratch_dir/TEST_AUDIT_PROCESS_AUDIT.prompt.md" 2>&1 | tee "$scratch_dir/TEST_AUDIT_PROCESS_AUDIT.log"', run_in_background=True, description="Audit test-audit process tree")
```

Wait for its task notification before validating or consuming the report and complete log.

Require the canonical header-first process report to start with `# Process Tree Audit`, followed by its canonical identity lines and exactly one canonical verdict whose complete value is `Verdict: PASS`. Require exactly one producer-owned `PROCESS_TREE_AUDIT_BINDING_JSON` row under `## Machine Binding`: `mode` equals exact `blocking`; `report_identity` names `${repo_root}/agents/test-audit-gate.md` and the report path without a self hash; `operator_artifact.path` names that same canonical absolute operator path; root equals `TEST_AUDIT_INVOCATION_UUID`; subtree is null; expected-process and trace path/hashes match; and the sorted companion rows exactly equal dispatch evidence, audit prompt, and every child prompt/log/output/extraction path/hash. Also require a complete successful process-auditor log whose provider payload final line is exact `PASS`. Then freeze `$scratch_dir/TEST_AUDIT_NESTED_PROOF.json` under `test-audit-nested-proof-v1` with those exact proof paths/hashes, all three child artifact rows, and `verdict=PASS`. Run:

```bash
python3 ~/ai/tools/operational_contracts.py validate-test-audit-proof \
  --proof "$scratch_dir/TEST_AUDIT_NESTED_PROOF.json" \
  --output "$scratch_dir/TEST_AUDIT_NESTED_PROOF_VALIDATION.json"
```

Only exact `status=VALID` for that current proof permits synthesis. The validator must traverse the actual saved trace, require exact requested/root invocation identity, and join each declared child UUID to exactly one trace node. It requires exactly three direct child nodes and no other descendants; each node's actual `parent_id`, `model_name`, `source`, successful terminal status, `success=true`, `exit_code=0`, and `finished_at` come from the trace, while source and successful identity are cross-checked against extraction metadata from the complete runner envelope. Fixed role/operator comes from the canonical node specification joined to that exact UUID, never from trace-free inference. Missing, duplicate, undeclared-role, wrong-parent/model/source/operator, failed, non-terminal, or extra nested nodes; stale prompt/log/output/extraction content; missing or hash-mismatched expected/dispatch/trace/audit artifacts; non-PASS report/stdout; or a stale validation artifact is `BLOCKED:test-audit-process-topology-failed`; do not write or return `TEST_AUDIT_GATE.md`.

### 7a. Test Audit Process Artifact Schema

```yaml
schema: test-audit-process-artifacts-v2
root_identity_source: OULIPOLY_PARENT_INVOCATION
required_nodes:
  spec-alignment: {operator_or_role: ad-hoc-spec-alignment, model: gpt-high, parent: root}
  test-quality: {operator_or_role: coverage-auditor, model: gpt-xhigh, parent: root}
  coverage-delta: {operator_or_role: coverage-analyzer, model: gpt-high, parent: root}
node_required_fields: [id, required, operator_or_role, model, parent, prompt_path, prompt_sha256, log_path, log_sha256_join_field, canonical_output_path, canonical_output_sha256_join_field, extraction_metadata_path, extraction_metadata_sha256_join_field, provider_source_join_field, output_mode]
node_output_mode: stdout-extracted
node_path_invariant: dedicated-log-distinct-from-canonical-output
identity_source: complete-log-only
verdict_source: canonical-output-only
required_proof_artifacts: [TEST_AUDIT_EXPECTED_PROCESS.json, TEST_AUDIT_DISPATCH_EVIDENCE.json, TEST_AUDIT_PROCESS_TREE.json, TEST_AUDIT_PROCESS_AUDIT.prompt.md, TEST_AUDIT_PROCESS_AUDIT.log, TEST_AUDIT_PROCESS_AUDIT.md, TEST_AUDIT_NESTED_PROOF.json, TEST_AUDIT_NESTED_PROOF_VALIDATION.json]
proof_acceptance: canonical-header-first-unique-report-PASS-producer-binding-current-final-stdout-PASS-and-production-validator-VALID
```

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
- Record `base_branch`, `base_ref`, full `base_sha`, `head_branch`, `head_ref`, full `head_sha`, merge-base SHA, and diff SHA-256 in `TEST_AUDIT_GATE.md` so callers can reject differently bound evidence. In `pr-review` mode, also record the required SHA-256 of `local_coverage_command`. In `implementation` mode, record that hash only when the caller actually supplied a non-blank command; omit it when the input is absent and never invent a hash.
- Record the expected-process and dispatch-evidence paths/hashes plus every distinct child log/output path/hash. Synthesis reads verdicts only from canonical `.md` outputs and process identity only from complete `.log` streams.
- Before synthesis, require the current `TEST_AUDIT_NESTED_PROOF_VALIDATION.json` to equal the production validator's `VALID` decision for the current nested proof. After writing `TEST_AUDIT_GATE.md`, write `$scratch_dir/TEST_AUDIT_RESULT.json` under the schema below; never return a bare gate report as sufficient PR-review evidence.

### 8a. Test Audit Result Schema

```yaml
schema: test-audit-result-v2
required_fields: [schema, status, mode, test_audit_invocation_uuid, base_branch, base_ref, base_sha, head_branch, head_ref, head_sha, merge_base_sha, diff_sha256, gate_report_path, gate_report_sha256, nested_proof_path, nested_proof_sha256, nested_proof_validation_path, nested_proof_validation_sha256, nested_process_proof]
conditional_fields:
  local_coverage_command_sha256:
    pr-review: required-lowercase-sha256-of-required-nonblank-command
    implementation: optional-lowercase-sha256-only-when-command-was-supplied
status_values: [PASS, PARTIAL, FAIL]
nested_process_proof_schema: test-audit-nested-proof-v1
nested_process_proof_required_fields: [schema, test_audit_invocation_uuid, base_sha, head_sha, expected_process_path, expected_process_sha256, dispatch_evidence_path, dispatch_evidence_sha256, process_tree_path, process_tree_sha256, process_tree_audit_prompt_path, process_tree_audit_prompt_sha256, process_tree_audit_path, process_tree_audit_sha256, process_tree_audit_log_path, process_tree_audit_log_sha256, child_artifacts, verdict]
child_artifact_required_fields: [id, invocation_uuid, parent_invocation_uuid, operator_or_role, model, provider_source, prompt_path, prompt_sha256, log_path, log_sha256, canonical_output_path, canonical_output_sha256, extraction_metadata_path, extraction_metadata_sha256, output_mode]
proof_validator: tools/operational_contracts.py validate-test-audit-result
proof_acceptance: nested-independent-PASS-and-current-hashes
```
