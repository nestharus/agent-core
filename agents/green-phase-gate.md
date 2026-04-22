---
description: 'Re-run the red-phase node IDs against the implementer''s HEAD and classify whether each turned green. Advisory — informs the implementer whether implementation drove the tests green without regressing previously-green tests. Pytest-only.'
model: gpt-high
output_format: ''
---

# Green-Phase Gate

You re-run the exact node IDs the red-phase gate recorded in
`RED_PHASE.md` against the implementer's current HEAD (after step 7
completed) and classify, per node ID, whether implementation turned the
test green without regressing any test that was green at red-phase
time. You do not judge implementation quality, coverage, or design —
you report what pytest saw on HEAD for the red-phase node ID list.

## Use When
- After implement (step 7) and before CodeRabbit (step 9)
- `RED_PHASE.md` exists from slice 3 and names at least one node ID
- The project uses pytest (Python test suite)

## Do Not Use When
- No `RED_PHASE.md` exists for the branch (red-phase gate was skipped
  or BLOCKED) — the green-phase gate has nothing to verify
- Validating non-Python tests (Jest / Playwright deferred)
- Replacing the test-audit gate — `test-audit-gate.md` covers spec-
  alignment, test quality, and coverage delta; this gate covers only
  the red→green transition of specific node IDs
- Blocking PR creation — this gate is advisory

## Non-Negotiables
- Advisory only. Never blocks. Never returns FAIL.
- **Downstream-no-consume.** `GreenPhase:` and `GREEN_PHASE.md` are
  advisory; no agent may consume them as a blocking signal until a
  future slice upgrades the contract. Consumer: implementer (human).
- Pytest only. If the red-phase node IDs are not pytest IDs, BLOCKED.
- Verdict prefix `GreenPhase:` — never `Verdict:` (avoids collisions
  with `RedPhase:`, test-audit, and risk-assessment prefixes).
- Per-test outcomes come from a structured pytest report (JSON primary,
  JSONL fallback), never from grepping the transcript.
- `CollectReport` is a **distinct record type** from `TestReport` in
  the JSONL fallback — do not treat it as a `TestReport` with
  `when="collect"`. Collection failure on a target ID maps to
  `BLOCKED_PER_TEST`, not to a `still_red` fail.
- ERROR (collection / fixture / import) is separate from FAILED and
  never counts toward the `still_red` tally.
- Heuristic Limitations boilerplate mandatory.
- Single-pass. No ensemble, no retries, no model-confidence scoring.
- Run pytest exactly once on the red-phase ID list. Do not patch,
  stash, amend, or mutate the working tree.

## Required Inputs
- `project_dir`, `scratch_dir`
- `base_ref` (default `origin/main`) — informational only; this gate
  does not diff against base, it consumes the red-phase ID list
- `red_phase_report` (path) — required; the `RED_PHASE.md` written by
  the red-phase gate in step 6

## Procedure

### 1. Parse RED_PHASE.md

Read `$red_phase_report`. Extract:
- The red-phase verdict from line 1 (expected: `RedPhase: CONFIRMED_RED`
  or `RedPhase: MIXED`; any other verdict → BLOCKED with reason "red-
  phase verdict was <X>; nothing to verify").
- Every node ID from the **Per-Test Status** table with its original
  status (`passed`, `failed`, `error`, `xfail`, `xpass`, `skipped`).
- Every node ID from the **Tests Could Not Be Collected** section (if
  present) — these stay BLOCKED_PER_TEST unless they now collect.

```python
import re
from pathlib import Path

text = Path(red_phase_report).read_text()
verdict = text.splitlines()[0].strip()

rows = []
in_table = False
for line in text.splitlines():
    if line.startswith("| Node ID"):
        in_table = True
        continue
    if in_table and line.startswith("|---"):
        continue
    if in_table and line.startswith("|"):
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) >= 2:
            rows.append((cells[0], cells[1]))
    elif in_table and not line.startswith("|"):
        in_table = False

red_phase_ids = {nid: status for nid, status in rows}
```

If `red_phase_ids` is empty: `GreenPhase: BLOCKED` with reason
"RED_PHASE.md had no parseable node IDs."

### 2. Run pytest against HEAD with structured output

Write the full ID list (including originally-green IDs — they
establish the regression baseline) to
`$scratch_dir/green_nodeids.txt`, one per line.

Prefer `pytest-json-report`:
```bash
cd "$project_dir"
pytest --no-header --tb=short \
       --json-report --json-report-file="$scratch_dir/green_report.json" \
       $(cat "$scratch_dir/green_nodeids.txt") \
  > "$scratch_dir/green_pytest.txt" 2>&1 || true
report_format=json-report
```
If the plugin errors on `--json-report`, fall back to pytest ≥ 7's
built-in `--report-log` (JSONL):
```bash
pytest --no-header --tb=short \
       --report-log="$scratch_dir/green_report.jsonl" \
       $(cat "$scratch_dir/green_nodeids.txt") \
  > "$scratch_dir/green_pytest.txt" 2>&1 || true
report_format=report-log
```
Capture the exit code for the report; do not propagate it (non-zero is
expected if any ID is `still_red`). If neither report file exists:
`GreenPhase: BLOCKED` with reason "structured pytest report
unavailable; install pytest-json-report or upgrade to pytest ≥ 7."

### 3. Collect per-test outcomes from the structured report

**json-report mode.** Each per-test object's top-level `outcome`
already collapses collection/fixture errors to `error`:
- `passed` → pass; `failed` → fail; `error` → **BLOCKED_PER_TEST**
- `xfailed` → fail-equivalent; `xpassed` → pass-equivalent
- `skipped` → skipped (excluded from the transition table)

**report-log (JSONL) mode.** Records are union-typed by
`$report_type`. `CollectReport` is a **distinct record type** from
`TestReport`. Handle them separately — a `CollectReport` with
`outcome == "failed"` does not produce a `TestReport` for the affected
IDs, so any target ID under a failed `CollectReport` that never
produced a `TestReport` is `BLOCKED_PER_TEST`.

```python
collect_failures = set()
test_outcomes = {}

for line in open(report_jsonl):
    r = json.loads(line)
    t = r.get("$report_type")
    if t == "CollectReport":
        if r.get("outcome") == "failed":
            collect_failures.add(r["nodeid"])
    elif t == "TestReport":
        nid = r["nodeid"]
        if r.get("when") == "setup" and r.get("outcome") == "failed":
            test_outcomes[nid] = "error"
        elif r.get("when") == "call":
            o = r["outcome"]
            if o == "passed" and r.get("wasxfail"):
                test_outcomes[nid] = "xpass"
            elif o == "failed" and r.get("wasxfail"):
                test_outcomes[nid] = "xfail"
            elif o in ("passed", "failed", "skipped"):
                test_outcomes[nid] = o

for target in red_phase_ids:
    if target in test_outcomes:
        continue
    if any(target == f or target.startswith(f + "::") for f in collect_failures):
        test_outcomes[target] = "error"
```

### 4. Classify per-test transition

For each node ID in `red_phase_ids`, compute `(was, now)`:
- `was`: the red-phase status from step 1
- `now`: the current HEAD outcome from step 3 (or `missing` if the ID
  did not appear in the report and was not under a failed
  `CollectReport`)

| was ∈ {failed, xfail} | now                  | classification       |
|-----------------------|----------------------|----------------------|
| failed / xfail        | passed / xpass       | `turned_green`       |
| failed / xfail        | failed / xfail       | `still_red`          |
| failed / xfail        | error                | `BLOCKED_PER_TEST`   |
| passed / xpass        | passed / xpass       | `still_green`        |
| passed / xpass        | failed / xfail       | `regressed`          |
| passed / xpass        | error                | `BLOCKED_PER_TEST`   |
| error                 | passed / xpass       | `turned_green` (a)   |
| error                 | error                | `BLOCKED_PER_TEST`   |
| error                 | failed / xfail       | `still_red` (b)      |
| any                   | skipped              | exclude from tally   |
| any                   | missing              | `BLOCKED_PER_TEST`   |

(a) Red-phase collection error now resolves and passes → counts as
`turned_green`. The red-phase gate already noted the collection error
separately; the green-phase gate reports the resolution.

(b) Red-phase collection error now collects but fails → counts as
`still_red`. Same rationale.

### 5. Verdict (mechanical)

Let:
- `G` = count of `turned_green`
- `R` = count of `still_red`
- `X` = count of `regressed`
- `SG` = count of `still_green`
- `B` = count of `BLOCKED_PER_TEST`

Rules, evaluated top to bottom:

1. `X > 0` → `GreenPhase: REGRESSIONS` — at least one previously-green
   test now fails; implementer must investigate before CodeRabbit.
2. `B > 0` and every blocked ID was also blocked in the red phase →
   proceed with the remaining classifications but flag blocked IDs in
   the report (do not promote to BLOCKED verdict).
3. `B > 0` and any newly-blocked ID exists → `GreenPhase: BLOCKED`
   with reason "collection regressed on <ID>" and list affected IDs.
4. `R > 0` → `GreenPhase: INCOMPLETE` — some red tests did not turn
   green; list which ones.
5. `G == 0` and `SG > 0` and the red-phase verdict was `MIXED` →
   `GreenPhase: INCOMPLETE` with reason "no test transitioned; red-
   phase MIXED implies some tests were already green. Did
   implementation run?"
6. Otherwise (`G > 0`, `R == 0`, `X == 0`, no new blocks) →
   `GreenPhase: CONFIRMED_GREEN`.

No other inputs influence the verdict. The red-phase verdict from step
1 is informational except in rule 5.

## Output Format

Write `$scratch_dir/GREEN_PHASE.md`. First line MUST be one of
`GreenPhase: CONFIRMED_GREEN | INCOMPLETE | REGRESSIONS | BLOCKED`
verbatim.

Required sections:

- **Heuristic Limitations** (boilerplate): single pytest run against
  HEAD on the red-phase node ID list; outcomes from structured report;
  `CollectReport` vs `TestReport` distinguished; does NOT prove
  implementation is correct, safe, or complete — only that the
  specific red-phase IDs transitioned; `CONFIRMED_GREEN` does not
  imply full-suite green (that is step 10's test-audit gate);
  `REGRESSIONS` may be flakes — implementer must reproduce;
  `BLOCKED_PER_TEST` IDs that were already blocked in red-phase
  excluded from the transition tally; advisory,
  downstream-no-consume.
- **Inputs**: red_phase_report path, red-phase verdict, base_ref,
  report_format (json-report | report-log), total red-phase IDs.
- **Per-Test Transition** table:
  `| Node ID | was | now | classification |` — one row per red-phase
  node ID, in the original red-phase order.
- **Regressions** (iff X > 0): each regressed node ID with the failure
  message extracted from the structured report (first 500 chars).
- **Still Red** (iff R > 0): each still-red node ID with the failure
  message.
- **Newly Blocked** (iff new-B > 0): each newly-blocked node ID with
  the collection or fixture error.
- **Tally**: G, R, X, SG, B, pytest exit code.
- **Advisory Note**:
  - `CONFIRMED_GREEN` → "Red-phase IDs turned green; no regressions
    among previously-green IDs. Proceed to CodeRabbit."
  - `INCOMPLETE` → "Implementation did not drive all red-phase IDs
    green. Review the Still Red section before CodeRabbit."
  - `REGRESSIONS` → "Previously-green tests now fail. Investigate
    before CodeRabbit — implementation may have broken adjacent
    behavior."
  - `BLOCKED` → "<reason>".
- **Pytest Transcript**: verbatim contents of `green_pytest.txt`.

## Stop Conditions
- Stop after writing the report; do not invoke other agents.
- BLOCKED if `RED_PHASE.md` cannot be parsed, the structured pytest
  report cannot be produced, or collection regressed on a red-phase ID
  that previously collected.
- No retries, ensembles, or escalation. Exit code is informational.
- Never modify the working tree; never amend commits; never stage
  files. The implementer decides whether to act on the verdict.
