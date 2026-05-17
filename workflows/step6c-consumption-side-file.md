---
description: 'Project Phase 6 Step 6b output-index rows into orchestrator-authored Step 6c side-file consumption evidence.'
workflow_dispatch_contract:
  orchestrator: implementation-pipeline-orchestrator
  command: step6c-consumption-side-file project --index <step6b-output-index> --out <side-file> --level-id <level-id> [--expected-process <manifest-path>]
  outputs:
    - side-file with canonical consumed rows
    - optional side_channel_evidence_bundle manifest entry
---

# Step 6c Consumption Side File

## Declared roles

`parser`, `formatter`, `validator`.

## Purpose

This workflow owns the ACR-247 side-channel carrier for Phase 6 Step 6c consumption evidence. It converts the current Step 6b output index into a deterministic side-file before the Step 6c code writer is dispatched. The side-file and the manifest entry are orchestrator/helper-authored evidence; model-authored `consumed:` rows or read-confirmation claims are not load-bearing audit evidence for ACR-247 side-channel runs.

## Helper Command

Canonical invocation:

```bash
step6c-consumption-side-file project --index <step6b-output-index> --out <side-file> --level-id <level-id> [--expected-process <manifest-path>]
```

Repo implementation:

```bash
~/ai/workflows/step6c-consumption-side-file/step6c-consumption-side-file project --index <step6b-output-index> --out <side-file> --level-id <level-id> [--expected-process <manifest-path>]
```

Inputs:

- `--index`: absolute or relative path to `${scratch_dir}/phase6/step6b-output-index.md`.
- `--out`: absolute or relative path for the side-file. The parent directory is created when needed.
- `--level-id`: recursive Phase 6 `level_id`; use `none` for the parent non-recursive scope.
- `--expected-process`: optional path where the helper writes the `side_channel_evidence_bundle:` manifest entry.

Exit behavior:

- Exit `0` and print `WROTE:<side-file>` when projection succeeds.
- Also print `WROTE:<manifest-path>` when `--expected-process` is supplied.
- Exit non-zero on a missing index, missing `Step 6b output` column, blank output row, duplicate canonical row, or under-specified `level_id`.

## Canonical Projection

The helper parses the Markdown table column named `Step 6b output` in source order. It writes UTF-8 rows with this grammar:

```text
consumed: <absolute-step6b-output-index-path>
consumed: <absolute-step6b-output-row-id-or-scoped-string-id>
```

The first non-blank row is always the absolute resolved Step 6b output-index path. Each following row is one Step 6b output-index row in stable index order.

For `level_id: none`, output-row values are copied as canonical row identifiers after trimming surrounding cell whitespace and one enclosing backtick pair. For recursive child levels, string artifact identifiers are emitted as `<level_id>:<local_artifact_id>` unless already scoped; absolute paths remain absolute and are later rejected by Audit #2 if they appear under a child manifest that requires child-scoped identifiers. Duplicate canonical rows are invalid.

Projection is byte-stable for unchanged index bytes, output path, and level id. The side-file ends with a single trailing newline.

## Side-Channel Manifest Entry

When `--expected-process` is supplied, the helper writes a `side_channel_evidence_bundle:` block with schema version `1`, projection schema version `1`, the resolved side-file path, the resolved source Step 6b output-index path, the projection helper identity `~/ai/workflows/step6c-consumption-side-file.md`, canonical row count excluding the prefix index row, current SHA-256 digests for the source index and side-file, and `projected_at` in RFC3339 UTC form.

The helper may receive `STEP6C_INVOCATION_UUID`, `STEP6C_PROMPT_PATH`, and `STEP6C_LOG_PATH` from the orchestrator when those values are already known. If they are not known before dispatch, the helper writes syntactically well-formed placeholders; the orchestrator updates those topology-only fields after the direct Step 6c invocation returns. The projection-owned fields remain the helper's responsibility.

## Orchestrator Contract

Before dispatching Step 6c, the implementation-pipeline orchestrator calls this helper with the active Step 6b output index, canonical side-file path, current `level_id`, and expected-process side-channel manifest path. The orchestrator verifies that the side-file and manifest entry exist, that required field tokens are present, and that the manifest entry was modified after the helper invocation started and before Step 6c starts. The orchestrator does not enumerate, format, or recompute side-channel manifest fields.

Step 6c dispatch remains direct:

```bash
agents -m <model> -p <worktree> -f <prompt> 2>&1 | tee <log>
```

The helper is a pre-dispatch producer, not a wrapper around `agents`, not a tee filter, and not a replacement for `agents trace --json`.

## Audit Contract

Process-tree Audit #2 reads the expected-process manifest entry, stats the manifest-declared side-file and source index, recomputes SHA-256 digests, re-projects the current source index through this helper's deterministic projection operation, byte-compares that output with the side-file, checks row count and `level_id` scope, and verifies `projected_at` is before the Step 6c invocation start.

The Step 6c prompt and log may be read for topology only: prompt path, log path, and invocation UUID joins. Model-authored `consumed:` rows, read-confirmation rows, `CONSUMED_EVIDENCE_EMITTED`, or equivalent claims are informational and cannot satisfy or repair the side-channel evidence bundle.
