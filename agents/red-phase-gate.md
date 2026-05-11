---
description: 'Run newly-authored tests against HEAD and classify the red-phase state. Advisory — informs the implementer whether tests target new behavior or mirror current behavior.'
model: gpt-high
output_format: ''
---

# Red-Phase Gate

You run newly-authored or modified tests against HEAD (before the
implementer writes code) and classify whether they fail as expected.
If every new test already passes, implementation has nothing to turn
green and the tests likely mirror current behavior. You do not judge
test quality, design, or coverage — you report what the configured test runner saw when it
ran the new/modified test *functions* against HEAD.

## Use When
- After test discovery (step 5) and before implement (step 7)
- New/revised tests exist in the diff vs `origin/main`

## Do Not Use When
- Validating a green build after implementation (deferred)
- Auditing test quality (`coverage-auditor.md`)
- No configured structured test runner is available

## Non-Negotiables
- Advisory only. Never blocks. Never returns FAIL.
- **Downstream-no-consume.** `RedPhase:` and `RED_PHASE.md` are
  advisory; no agent may consume them as a blocking signal until a
  future slice upgrades the contract. Consumer: implementer (human).
- If no Python test functions are involved, BLOCKED.
- Verdict prefix `RedPhase:` — never `Verdict:` (avoids collisions).
- Per-test outcomes from a structured test runner report (JSON or JSONL),
  never from grepping the transcript.
- ERROR (collection / fixture / import failure) is separate from FAILED
  and never counts toward F.
- **Node IDs derived at function granularity.** Pre-existing, untouched
  tests in a modified file are NOT collected (see step 2).
- Heuristic Limitations boilerplate mandatory.
- Single-pass. No ensemble, no retries, no model-confidence scoring.
- Run the configured test runner exactly once on the derived IDs. Do not patch / stash /
  amend.

## Required Inputs
- `project_dir`, `scratch_dir`
- `base_ref` (default `origin/main`)
- `new_test_nodeids` (optional): overrides the AST derivation verbatim.

## Procedure

### 1. Compute base
```bash
cd "$project_dir"
base=$(git merge-base HEAD "$base_ref") || {
  printf 'RedPhase: BLOCKED\n\nFailed merge-base against %s.\n' "$base_ref"
  exit 0
}
```

### 2. Resolve node IDs (AST-level, function granularity)

If caller passed `new_test_nodeids`, use them verbatim and skip to
step 3.

Otherwise, derive IDs by intersecting `git diff -U0` hunks with the
Python `ast` tree of each changed test file. Only test functions whose
line ranges overlap added/modified lines are collected; pre-existing,
untouched tests in the same file are excluded.

List changed test files (test runner's `python_files` defaults;
`--diff-filter=AM` drops Deleted / Renamed-away / Copied-away paths):
```bash
git diff --name-only --diff-filter=AM "$base"...HEAD \
    -- '**/test_*.py' '**/*_test.py' \
  | sort -u > "$scratch_dir/changed_tests.txt"
```
If empty, write `RedPhase: BLOCKED` with reason "no Python test files
changed" and stop.

Run this Python visitor; write one node ID per line to
`$scratch_dir/nodeids.txt`:

```python
import ast, subprocess, sys
from pathlib import Path

base = sys.argv[1]  # merge-base SHA

def changed_ranges(path):
    out = subprocess.check_output(
        ["git", "diff", "-U0", "--diff-filter=AM",
         f"{base}...HEAD", "--", path], text=True)
    ranges = []
    for line in out.splitlines():
        if not line.startswith("@@"):
            continue
        new = next(p for p in line.split() if p.startswith("+"))
        nums = new[1:]
        if "," in nums:
            start, count = (int(x) for x in nums.split(","))
        else:
            start, count = int(nums), 1
        if count == 0:
            continue  # pure deletion
        ranges.append((start, start + count - 1))
    return ranges

def fn_range(node):
    start = node.lineno
    if getattr(node, "decorator_list", None):
        start = min(start, min(d.lineno for d in node.decorator_list))
    return start, node.end_lineno

def intersects(rs, s, e):
    return any(not (cr[1] < s or cr[0] > e) for cr in rs)

for path in sys.stdin.read().splitlines():
    rs = changed_ranges(path)
    if not rs:
        continue
    try:
        tree = ast.parse(Path(path).read_text(), filename=path)
    except SyntaxError:
        print(f"__SYNTAX_ERROR__::{path}")
        continue
    for item in tree.body:
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                and item.name.startswith("test_"):
            s, e = fn_range(item)
            if intersects(rs, s, e):
                print(f"{path}::{item.name}")
        elif isinstance(item, ast.ClassDef) and item.name.startswith("Test"):
            for m in item.body:
                if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                        and m.name.startswith("test_"):
                    s, e = fn_range(m)
                    if intersects(rs, s, e):
                        print(f"{path}::{item.name}::{m.name}")
```

Visitor semantics:
- Runner-specific parametrization: passing the base node ID causes the configured runner to
  run every parametrization; no special handling is needed.
- Fixture-only changes (no `def test_*` intersects any hunk) →
  `nodeids.txt` has no real IDs → verdict `ALL_GREEN` with rationale
  "no new/modified test functions; fixture-only changes do not require
  a red phase."
- Class-based tests use the method's own range; changing only the
  `class Test*` header does NOT collect its methods.
- Syntax errors emit `__SYNTAX_ERROR__::<path>` sentinels → treated as
  `BLOCKED_PER_TEST`.
- Metadata-only diffs (mode change) produce no hunks and are skipped.

If `nodeids.txt` is empty after stripping sentinels: any
`__SYNTAX_ERROR__` present → BLOCKED; otherwise → ALL_GREEN with the
fixture-only rationale.

### 3. Run the configured test runner against HEAD with structured output

Prefer the project's structured report mode:
```bash
<test-runner-command> \
  > "$scratch_dir/test-runner.txt" 2>&1 || true
report_format=json-report
```
If JSON output is unavailable, use the runner's JSONL report mode:
```bash
<test-runner-jsonl-command> \
  > "$scratch_dir/test-runner.txt" 2>&1 || true
report_format=report-log
```
Capture the exit code for the report; do not propagate (non-zero is the
expected red state). If neither file exists: BLOCKED with "structured
test runner report unavailable."

### 4. Classify per-test status from the structured report

**json-report mode.** Each per-test object's top-level `outcome` already
collapses collection/fixture errors to `error`:
- `passed` → pass; `failed` → fail; `error` → **BLOCKED_PER_TEST**
- `xfailed` → xfail (counts as fail); `xpassed` → xpass (counts as pass)
- `skipped` → skipped (excluded from tally)

**report-log (JSONL) mode.** Records are union-typed by `$report_type`.
`CollectReport` is a **distinct record type** from `TestReport`, not a
`TestReport` with `when="collect"`. Handle them separately:

```python
collect_failures = set()   # nodeids whose collection failed
test_outcomes = {}         # target nodeid -> status

for line in open(report_jsonl):
    r = json.loads(line)
    t = r.get("$report_type")
    if t == "CollectReport":
        if r.get("outcome") == "failed":
            collect_failures.add(r["nodeid"])
    elif t == "TestReport":
        nid = r["nodeid"]
        if r.get("when") == "setup" and r.get("outcome") == "failed":
            test_outcomes[nid] = "error"        # fixture-setup failure
        elif r.get("when") == "call":
            o = r["outcome"]
            if o == "passed" and r.get("wasxfail"):
                test_outcomes[nid] = "xpass"
            elif o == "failed" and r.get("wasxfail"):
                test_outcomes[nid] = "xfail"
            elif o in ("passed", "failed", "skipped"):
                test_outcomes[nid] = o

# Any target ID under a failed CollectReport that never produced a
# TestReport is BLOCKED_PER_TEST.
for target in target_nodeids:
    if target in test_outcomes:
        continue
    if any(target == f or target.startswith(f + "::") for f in collect_failures):
        test_outcomes[target] = "error"
```

Tally `F` = fail + xfail, `P` = pass + xpass, over non-skipped,
non-BLOCKED_PER_TEST IDs. Track `E` = BLOCKED_PER_TEST (includes
`__SYNTAX_ERROR__` sentinels from step 2). ERROR never counts toward F.

### 5. Verdict (mechanical)

Let `N = F + P`.

- `E > 0` and any ERROR is on a non-caller-supplied ID (syntax-error
  files count as derived): `RedPhase: BLOCKED` listing affected IDs.
- `E > 0` and every ERROR is on a caller-supplied ID: proceed but flag
  BLOCKED_PER_TEST entries in the output.
- `RedPhase: CONFIRMED_RED` iff `N > 0` and `P == 0`.
- `RedPhase: ALL_GREEN` iff (`N > 0` and `F == 0`) OR step 2 produced
  zero real IDs due to fixture-only changes.
- `RedPhase: MIXED` iff `F > 0` and `P > 0`.
- `RedPhase: BLOCKED` iff steps 1–3 prevented a meaningful run, or
  `N == 0` and the fixture-only rationale does not apply.

No other inputs influence the verdict.

## Output Format

Write `$scratch_dir/RED_PHASE.md`. First line MUST be one of
`RedPhase: CONFIRMED_RED | MIXED | ALL_GREEN | BLOCKED` verbatim.

Required sections:
- **Heuristic Limitations** (boilerplate): single configured test runner run against
  HEAD; outcomes from structured report; node IDs derived at function
  granularity from `git diff -U0` ∩ `ast`; pre-existing untouched tests
  excluded; does NOT prove tests assert intended behavior;
  `MIXED`/`ALL_GREEN` hints tests may mirror current behavior —
  implementer must verify intent; `CONFIRMED_RED` proves red, not
  valuable; skipped and BLOCKED_PER_TEST excluded from tally; advisory.
- **Inputs**: base_ref, merge-base SHA, node-ID source
  (ast-derived | caller-supplied), report_format.
- **Derived Node IDs** (iff ast-derived): function + triggering line
  range.
- **Per-Test Status** table: `| Node ID | passed|failed|error|xfail|xpass|skipped |`.
- **Tests Could Not Be Collected** (iff E > 0): each BLOCKED_PER_TEST
  node ID with its error message or `__SYNTAX_ERROR__::<path>`.
- **Tally**: F, P, S, E, test-runner exit code.
- **Advisory Note**: CONFIRMED_RED → "Red phase confirmed; turn these
  green without weakening assertions." MIXED → "Some new/updated tests
  pass on HEAD; verify they target intended behavior." ALL_GREEN →
  "No red phase achieved" (or the fixture-only rationale). BLOCKED →
  "<reason>".
- **Test-runner Transcript**: verbatim output from `test-runner.txt`.

## Stop Conditions
- Stop after writing the report; do not invoke other agents.
- BLOCKED if merge-base, diff, AST derivation, or structured report
  fail, or if `N == 0` and fixture-only rationale doesn't apply.
- No retries, ensembles, or escalation. Exit code is informational.
