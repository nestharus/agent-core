# ACR-247 Step 6c Consumption Evidence Eval

This eval exercises the Audit #2 verification predicate for ACR-247's Phase 6 Step 6c side-channel. The canonical proof is the manifest-declared side-file generated from the Step 6b output index before Step 6c dispatch. Model-authored `consumed:` rows in the Step 6c log are informational only and cannot repair a missing, stale, mismatched, wrong-scope, or late side-file.

## Run Locally

Run every fixture:

```bash
python3 eval.py
```

Use this default mode during Step 6b authoring. `SKIP` results are informational
while Step 6c is in progress, the projection helper may not exist yet, or the
AC5 convention rule is still awaiting Step 6c; only fixture verdict mismatches
fail the run.

Run one fixture:

```bash
python3 eval.py --fixture fixtures/happy-path
```

After Step 6c completes, run strict mode:

```bash
python3 eval.py --strict
```

In `--strict` mode, any `SKIP` is a failure, projection-dependent fixtures must
successfully invoke the projection helper, and `convention-rule-present/` must
return `pass-if-convention-rule-present`. Any `SKIP` or convention-rule-absent
result is a Step 6c failure that blocks Phase 6 close. The Phase 6 process-tree
audit (Audit #2) must verify the strict-mode run passes.

The runner first invokes the Step 6a canonical projection helper shape:

```bash
step6c-consumption-side-file project --index <index> --out <out> --level-id <level-id>
```

If `step6c-consumption-side-file` is not on `PATH`, the runner falls back to
`STEP6C_PROJECTION_CMD` when that environment variable is set. If neither the
canonical executable nor `STEP6C_PROJECTION_CMD` resolves, projection-dependent
fixtures are reported as `SKIP` in default mode and `FAIL` in `--strict` mode.

In default mode, if the helper does not exist yet, fixtures are reported as
`SKIP` rather than hard failures. In `--strict` mode, those same `SKIP` results
fail the run. Step 6c is expected to wire the projection helper to the command
shape defined by `/home/nes/projects/agent-runner/planning/acr-247-runtime-consumed-side-channel/contracts/acr-247-runtime-consumed-side-channel.md`.

## Fixture Summary

| Fixture | Expected verdict | Predicate focus |
|---|---|---|
| `happy-path/` | `pass` | Valid manifest, current source index, current side-file, byte-stable projection, correct scope, and pre-dispatch ordering. |
| `tampered-side-file/` | `block-side-file-sha-mismatch` | Detects side-file mutation after projection. |
| `missing-side-file/` | `block-side-file-missing` | Detects a manifest-declared side-file that is absent on disk. |
| `stale-source-index/` | `block-source-index-sha-mismatch` | Detects an index edited after the side-file was projected. |
| `row-mismatch/` | `block-reprojection-mismatch` | Detects side-file bytes that no longer match deterministic projection from the current index. |
| `wrong-scope/` | `block-level-scope-mismatch` | Detects parent rows supplied under a child `level_id` manifest. |
| `model-attestation-only-fail/` | `block-side-file-missing` | Proves a log stuffed with model-authored `consumed:` rows cannot satisfy Audit #2 when the side-file is missing. |
| `dispatch-time-too-late/` | `block-dispatch-time-ordering` | Detects a side-file projected after the Step 6c invocation start time. |
| `prompt-contract/` | `pass-if-prompt-clean \| block-if-prompt-requests-load-bearing-attestation` | Accepts context-only Step 6c prompts and blocks prompts that require model-authored attestations as load-bearing proof. |
| `direct-dispatch-hygiene/` | `pass-if-dispatch-shape-clean \| block-if-wrapper-or-shell-fanout-or-truncating-filter` | Accepts direct `agents -m ... -p ... -f ... 2>&1 \| tee ...` dispatch and blocks wrappers, fanout, heredocs, and truncating filters. |
| `convention-rule-present/` | `pass-if-convention-rule-present` | Checks that a declared convention target contains the AC5 load-bearing audit evidence authorship rule. Step 6b local runs skip with `awaiting-step6c-ac5` when the rule is absent before Step 6c adds it; the post-Step-6c `--strict` run must pass. |
