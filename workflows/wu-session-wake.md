---
workflow:
  id: wu-session-wake
workflow_dispatch_contract:
  orchestrator: "root wu-session-wake invocation (scheduler-triggered or manual)"
  inputs:
    - "sessions.active-wake.json path"
    - "poller output from tools/pr-batch-poller"
    - "per-project worktree and planning roots"
    - "caller-owned unique run_id; wake_invocation_uuid is derived inside the root from runner-provided OULIPOLY_PARENT_INVOCATION"
    - "session rows carrying base_branch, pr_open_base_sha, and optional pre_merge_base_sha"
  expectations:
    - "joins merged PR rows to one persisted WU session manifest"
    - "dispatches wu-session-resumer once per merged session"
    - "does not batch post-merge session work inside the poller or scheduler"
    - "verifies the merged PR base against base_branch and runs post-merge evidence against that base without defaulting to main"
    - "verifies the multi-row expected process and process tree before aggregate completion"
    - "joins each actual resumer UUID only from its completed log marker and accepts only a canonical header-first process-tree-auditor report with one PASS verdict, a producer-owned machine binding, and final stdout PASS"
    - "blocks every excluded or accepted-breakage classification found in sessions.active-wake.json; only a canonical OPEN row that currently polls non-merged may remain pending"
    - "validates run_id and ticket_id as canonical safe tokens and proves every generated wake, prompt, and log path remains under the canonical planning root"
    - "treats a batch containing only valid non-merged skipped rows as a successful audited no-op"
    - "uses active-index pre_merge_base_sha as the single dispatch source and blocks any manifest mismatch before dispatch"
  outputs:
    - "${planning_root}/wake-runs/${run_id}/composition-report.json"
    - "${planning_root}/wake-runs/${run_id}/expected-process.json"
    - "${planning_root}/wake-runs/${run_id}/dispatch-evidence.json"
    - "${planning_root}/wake-runs/${run_id}/process-tree.json"
    - "${planning_root}/wake-runs/${run_id}/process-tree-audit.md"
    - "${planning_root}/wake-runs/${run_id}/process-tree-audit.log"
    - "one current-invocation prompt and log per dispatched merged session"
  non_goals:
    - "does not implement the scheduler runtime"
    - "does not change pr-batch-poller schema"
    - "does not inline post-merge checks or spawn successor WUs"
---
# WU Session Wake

This workflow wires `~/ai/conventions/wu-session-lifecycle.md` Stage 5 through Stage 7 without merging scheduler, polling, and post-merge session closure into one binary.

## Workflow Dispatch Surface

```yaml
orchestrator: "root wu-session-wake invocation (scheduler-triggered or manual)"
inputs:
  - "sessions.active-wake.json path"
  - "poller output from tools/pr-batch-poller"
  - "per-project worktree and planning roots"
  - "caller-owned unique run_id; wake_invocation_uuid is derived inside the root from runner-provided OULIPOLY_PARENT_INVOCATION"
  - "session rows carrying base_branch, pr_open_base_sha, and optional pre_merge_base_sha"
expectations:
  - "joins merged PR rows to one persisted WU session manifest"
  - "dispatches wu-session-resumer once per merged session"
  - "does not batch post-merge session work inside the poller or scheduler"
  - "verifies the merged PR base against base_branch and runs post-merge evidence against that base without defaulting to main"
  - "verifies the multi-row expected process and process tree before aggregate completion"
  - "joins each actual resumer UUID only from its completed log marker and accepts only a canonical header-first process-tree-auditor report with one PASS verdict, a producer-owned machine binding, and final stdout PASS"
  - "blocks every excluded or accepted-breakage classification found in sessions.active-wake.json; only a canonical OPEN row that currently polls non-merged may remain pending"
  - "validates run_id and ticket_id as canonical safe tokens and proves every generated wake, prompt, and log path remains under the canonical planning root"
  - "treats a batch containing only valid non-merged skipped rows as a successful audited no-op"
  - "uses active-index pre_merge_base_sha as the single dispatch source and blocks any manifest mismatch before dispatch"
outputs:
  - "${planning_root}/wake-runs/${run_id}/composition-report.json"
  - "${planning_root}/wake-runs/${run_id}/expected-process.json"
  - "${planning_root}/wake-runs/${run_id}/dispatch-evidence.json"
  - "${planning_root}/wake-runs/${run_id}/process-tree.json"
  - "${planning_root}/wake-runs/${run_id}/process-tree-audit.md"
  - "${planning_root}/wake-runs/${run_id}/process-tree-audit.log"
  - "one current-invocation prompt and log per dispatched merged session"
non_goals:
  - "does not implement the scheduler runtime"
  - "does not change pr-batch-poller schema"
  - "does not inline post-merge checks or spawn successor WUs"
```

## Procedure

1. Start one root `wu-session-wake` invocation with caller-owned unique `run_id`. Require `run_id` to match the canonical safe-token regex `^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$` exactly; do not trim, slugify, or normalize an invalid value. Canonicalize the absolute no-symlink `planning_root`, derive `wake_run_root=${planning_root}/wake-runs/${run_id}`, and require `realpath -m -- "${wake_run_root}"` to remain strictly below `realpath -- "${planning_root}"` before creating anything. A token or containment failure is `BLOCKED:unsafe-wake-path`. Do not accept a caller-provided current invocation UUID. Inside the root, parse the runner-provided `OULIPOLY_PARENT_INVOCATION` JSON with duplicate-key rejection and require exactly one non-blank UUID `id`; set `wake_invocation_uuid` to that value. Missing, malformed, duplicate-keyed, non-UUID, or later trace-root mismatch is `BLOCKED:wake-runtime-invocation-identity-unavailable`. Create `${wake_run_root}/composition-report.json` before row dispatch and update it atomically after each classification or child result.
2. Read only the canonical project wake index at `${planning_root}/sessions.active-wake.json`; `${planning_root}/sessions.index.json` is historical/source inventory and is never a wake input. Require `schema=wu-sessions-active-wake-v1`, take the shared cutover lock at `~/.local/state/ai/wu-session-migration/cutover.lock` while reading one stable index snapshot, and reject a stale migration journal before polling. Each row must use only canonical fields and name `ticket_id`, `ticket_system`, `branch`, `base_branch`, `draft_pr_url`, full `draft_pr_head_sha`, `pr_open_base_sha`, `session_manifest_path`, full `branch_out_sha`, `worktree_path`, and `planning_dir`. Require every `ticket_id` to match `^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$` exactly. Canonicalize each row's `planning_dir`, generated prompt path, and generated log path without following a symlinked component; require all three to remain strictly below the canonical `planning_root` before output or dispatch. `pre_merge_base_sha` is optional: automated merges persist it immediately before merge; OPEN manual/external sessions leave it null for trusted wake-time derivation. Accepted-breakage, closed, pre-PR, malformed-placeholder, conflict-refused, unsafe-token, or escaping-path rows are invalid in this index rather than runtime skip candidates. Missing identity fields block dispatch, but a null pre-merge SHA does not.
3. For each indexed `draft_pr_url`, require the canonical `https://github.com/<owner>/<repo>/pull/<number>` shape and derive the poller's `<owner>/<repo>#<number>` identifier without replacing the stored URL. Block malformed or non-GitHub URLs, then run `~/ai/tools/pr-batch-poller/` with the derived identifiers. The poller returns PR status rows only; it does not read session manifests or dispatch agents.
4. Join each poller row to exactly one active-index row by poller `pr_url == draft_pr_url` and poller `head_ref_name == branch`, then read that row's exact `session_manifest_path`. Require poller full `head_sha == draft_pr_head_sha` and `base_ref_name == base_branch`; `base_ref_oid` is current PR/base status evidence and is not `pre_merge_base_sha`. Require the manifest identity fields to equal the active row and require manifest `pre_merge_base_sha` to equal active-index `pre_merge_base_sha`, including null equality; `BLOCKED:pre-merge-base-source-mismatch` is returned before prompt creation on any difference. The active index is the sole source passed to the resumer. Record non-merged rows as legitimately skipped. A batch with one or more such skipped rows, zero merged rows, and no blocked inputs is a successful no-op: continue through the empty expected-process/dispatch/trace audit with zero resumer nodes and report success rather than blocking for lack of a child. Ambiguous, missing, error, or mismatched joins are blocked and must be reported rather than guessed.
5. For every uniquely joined `merged=true` row, compose `${planning_dir}/prompts/${ticket_id}-wu-session-resume-${run_id}.md` instructing `wu-session-resumer` to consume:
   - `pr_url` from the poller row
   - `merge_sha` from the poller row
   - `head_sha` from the poller row, matching manifest `draft_pr_head_sha`
   - `base_branch` from the session index and manifest, matching poller `base_ref_name`
   - optional `pre_merge_base_sha` from the active index after exact manifest equality validation; omit/null means the resumer must derive it from trusted merge evidence
   - `branch_name` from `head_ref_name`
   - `ticket_id` from the session index
   - exact `session_manifest_path`
   - optional `test_command` and `coverage_command` only from explicit project policy or manifest values
6. Before dispatch, write immutable `${planning_root}/wake-runs/${run_id}/expected-process.json` using `wu-session-wake-expected-process-v1` below. It identifies `run_id` and derived `wake_invocation_uuid` and contains exactly one canonical expected `wu-session-resumer` node for each dispatchable row. Build the stable row identity from canonical JSON `{draft_pr_url,branch,ticket_id,session_manifest_path}`, store its SHA-256, and derive `id=wake-resumer-<first-16-hex>`. Block duplicate ids, duplicate full row hashes, a prior child for the same row, or any expected node for a blocked/skipped/excluded row. Hash the complete manifest before dispatch.
7. Dispatch each expected resumer exactly once, using run-scoped paths:

```bash
agents -a wu-session-resumer -p "${worktree_path}" -f "${planning_dir}/prompts/${ticket_id}-wu-session-resume-${run_id}.md" 2>&1 | tee "${planning_dir}/logs/${ticket_id}-wu-session-resume-${run_id}.log"
```

8. For each completed child log, parse exactly one valid `OULIPOLY_INVOCATION` marker and capture its actual child UUID only after dispatch. Reject missing, duplicate, malformed, repeated-across-rows, or root-equal UUIDs. Parse only the same current log's final sentinel. Accept exactly `wu-session-resumer: closed; manifest=<path>` or `wu-session-resumer: handoff-prepared; manifest=<path>; brief=<path>`. Require returned manifest equals the joined row's exact `session_manifest_path`; for handoff, require the returned brief equals the manifest's current `successor_session_brief` and exists. A stale, shorthand, wrong-row, duplicate, `BLOCKED:`, or `NEEDS_INPUT:` result cannot close the row.
9. After all expected children return, freeze `${planning_root}/wake-runs/${run_id}/dispatch-evidence.json` with `schema=wu-session-wake-dispatch-evidence-v1`. Each row joins expected `id` and `row_identity_sha256` to the actual child UUID, prompt/log/output paths, final sentinel, and SHA-256 of every current prompt, complete log, session-manifest output, and successor brief when any. Hash this file; never rewrite the expected manifest to add UUIDs.
10. Capture `agents trace --json ${wake_invocation_uuid}` as `${planning_root}/wake-runs/${run_id}/process-tree.json`. Dispatch `process-tree-auditor` in blocking mode against `operator_file=${repo_root}/workflows/wu-session-wake.md`, that exact root/trace, expected-process manifest, and report path `${planning_root}/wake-runs/${run_id}/process-tree-audit.md`; supply dispatch evidence and every current prompt/log/output as the exact companion set, then capture complete auditor stdout at `${planning_root}/wake-runs/${run_id}/process-tree-audit.log`. Require the report to start with `# Process Tree Audit`, carry the five canonical identity lines including exact root and expected/trace paths, and contain exactly one `Verdict:` line whose complete value is `Verdict: PASS`. Require its one producer-owned `PROCESS_TREE_AUDIT_BINDING_JSON` to record exact `mode=blocking`, name the canonical absolute `${repo_root}/workflows/wu-session-wake.md` equal to `operator_artifact.path`, and name the report path without a self hash; bind the same root/null subtree and expected/trace path/hashes, and contain sorted path/hash rows for exactly dispatch evidence and every prompt/log/output. Require the audit log's final stdout line to equal `PASS`. Reject `FAIL:*`, `NEEDS_INPUT:*`, `BLOCKED:*`, `compliant`, missing/multiple verdicts, custom binding layouts, stale hashes, or any other canonical outcome.
11. Finalize the composition report. Every row records `joined`, `skipped`, or `blocked`, PR/branch/ticket identity, stable expected-node id/hash, exact manifest path, exact successor brief path when any, prompt path/hash, log path/hash, actual child invocation UUID, output hashes, current child sentinel, and reason. The report also records `run_id`, derived `wake_invocation_uuid`, expected-process/dispatch-evidence/process-tree/audit/audit-log paths and hashes, counts, and aggregate status.

## Expected Process Schema

```yaml
schema: wu-session-wake-expected-process-v1
required_top_level_fields: [schema, run_id, wake_invocation_uuid, nodes]
node_required_fields:
  - id
  - required
  - operator_or_role
  - model
  - parent
  - prompt
  - log
  - expected_outputs
  - questions_allowed
  - question_artifacts
  - answer_artifacts
  - continuation_evidence
  - blocking_if_missing
  - notes
  - row_identity
  - row_identity_sha256
  - prompt_sha256
fixed_node_values:
  required: true
  operator_or_role: wu-session-resumer
  model: gpt-high
  parent: root
  questions_allowed: true
  blocking_if_missing: true
stable_id: wake-resumer-<first-16-hex-of-row_identity_sha256>
post_dispatch_identity_source: dispatch-evidence.json OULIPOLY_INVOCATION marker only
```

## Composition Report

The durable report is one JSON object with stable row identity and no embedded source manifests:

```json
{
  "schema": "wu-session-wake-composition-v1",
  "run_id": "<run-id>",
  "wake_invocation_uuid": "<runner-derived-uuid>",
  "rows": [{
    "status": "joined | skipped | blocked",
    "pr_url": "<trusted-poller-url>",
    "branch": "<head-ref>",
    "ticket_id": "<ticket>",
    "session_manifest_path": "<absolute-path>",
    "successor_brief_path": "<absolute-path-or-null>",
    "prompt_path": "<absolute-path-or-null>",
    "log_path": "<absolute-path-or-null>",
    "expected_node_id": "<stable-id-or-null>",
    "row_identity_sha256": "<sha256-or-null>",
    "child_invocation_uuid": "<uuid-or-null>",
    "child_sentinel": "<exact-current-sentinel-or-null>",
    "reason": "<classification-or-block-reason>"
  }],
  "expected_process_path": "<absolute-path>",
  "expected_process_sha256": "<sha256>",
  "dispatch_evidence_path": "<absolute-path>",
  "dispatch_evidence_sha256": "<sha256>",
  "process_tree_path": "<absolute-path>",
  "process_tree_sha256": "<sha256>",
  "process_tree_audit_path": "<absolute-path>",
  "process_tree_audit_sha256": "<sha256>",
  "process_tree_audit_log_path": "<absolute-path>",
  "process_tree_audit_log_sha256": "<sha256>",
  "aggregate": "success | partial | blocked"
}
```

## Process-Tree Relationship

This is a root-delegated fanout/join workflow. The aggregate consumes multiple resumer results, so row logs alone are insufficient. The canonical expected-process manifest is written before dispatch without guessed child UUIDs; post-dispatch evidence joins actual marker UUIDs and artifact hashes. The trace rooted at derived `wake_invocation_uuid` must show exactly one direct resumer child per expected row and no child for skipped/blocked rows. Independent `process-tree-auditor` proof in blocking mode is mandatory. Aggregate success or partial completion requires the current canonical header-first report's one exact `Verdict: PASS`, its producer-owned exact-blocking-mode report/root/expected/trace/complete companion machine binding, and the auditor log's final exact `PASS`, all bound to the same `run_id`, wake UUID, expected/dispatch/trace manifests, prompts, logs, outputs, and hashes.

## Stop Conditions

- `wu-session-wake: success; report=<absolute-path>`: all dispatchable rows returned an exact current success sentinel, all row identities matched, and exact process-tree report/stdout PASS is current. A batch containing only legitimately skipped non-merged rows and no blocked input is a successful audited no-op with zero resumer nodes. Only a valid canonical OPEN row that currently polls non-merged may remain pending without blocking; every excluded or accepted-breakage classification present in the active index blocks aggregate correctness.
- `wu-session-wake: partial; report=<absolute-path>`: at least one row completed and at least one row is blocked or needs input; exact process-tree report/stdout PASS must still account for every expected dispatch.
- `wu-session-wake: blocked; report=<absolute-path>`: global input/report/expected-process/process-tree validation failed, a dispatchable merged row did not complete, or exactly-once topology could not be proven. The legitimate skipped-only no-op is not blocked.

## Anti-scope

- Does not implement the scheduler runtime.
- Does not change `pr-batch-poller` schema; it consumes the existing `base_ref_name` and `base_ref_oid` fields without treating the latter as pre-merge evidence.
- Does not inline post-merge checks; those belong to `wu-session-resumer`.
- Does not spawn successor WUs; the resumer writes the successor brief and the implementation orchestrator reads it during a later Phase 0 spawn.
