# WU Session Lifecycle Convention

A **WU session** is the orchestrator-dispatched run that owns one Work Unit end-to-end. Each WU session has a stable identity (the root agent invocation UUID from `agents trace --json`), a planning footprint (`${planning_dir}/<branch>/`), a worktree footprint (`${worktree_path}`), and a ticket-system identity (`${ticket_id}`). The session is the unit of work for one PR.

This convention defines the session's lifecycle stages and the post-merge wake-up that closes the session cleanly.

## Stages

```
spawn → run-pipeline → draft-PR → (gate) → merged → post-merge-wake → close
```

### Stage 1 — `spawn`

Triggered by an orchestrator dispatch. The session's identity is established: root invocation UUID, ticket key (created if cold-starting), worktree, planning dir, scratch dir. Session manifest written to `${planning_dir}/session.json` capturing the IDs.

### Stage 2 — `run-pipeline`

The session walks the implementation pipeline (Phase 0 → Phase 9) per `~/ai/workflows/implementation-pipeline.md`. All phase artifacts land in the session's planning dir. Sub-agent dispatches are children of the session's root invocation.

Before the first active row exists, two stage-specific exclusive-writer transitions may update the open session manifest. After an inherited-estimate cold-start answer is accepted, `cold-start-disposition-bind` changes only `cold_start_disposition_ref`; it does not answer the separate terrain/risk/defer gate. After the Phase 3 estimate disposition and all currentness artifacts are complete, `phase3-bind` changes only `phase_3_estimate_writeback_ref`, `phase_3_estimate_writeback_sha256`, and appends exactly `{"phase":"3","status":"complete","ts":"<YYYY-MM-DDTHH:MM:SSZ>"}` to the complete history prefix. Both require `row_identity=null`, refuse diverted or duplicate semantics, write only `session.json`, and journal the complete active index plus operation artifacts as source-identity-bound read-only guards. Caller-owned readback must prove exact changed keys and unchanged active-index bytes/device/inode/mode/rows before the next gate. The first active-row insertion remains Phase 7 `phase7-upsert`.

### Stage 3 — `draft-PR`

Phase 7 produces or reuses one draft PR and records its URL, number, head SHA, `base_branch`, and `pr_open_base_sha`. After exact provider acquisition, it inserts one canonical row into the exact live runtime root `R` at `R/sessions.active-wake.json`; `R/sessions.index.json` remains historical/source inventory. A standalone direct session declares top-level project planning tree `P` as `R`. A feature direct or refactoring child declares normalized `F/routes` as `R`; its session directory is one immediate child of that root. No caller or consumer searches for a nearest root. The PR-open snapshot is not the pre-merge coverage baseline. Phase 8 freezes immutable `phase_8_reviewed_base_sha` and `phase_8_reviewed_head_sha`. Before its ticket dispatch, Phase 9 freezes and hashes caller-owned backend/site/ticket/route/attempt/PR/reviewed expected context, validates the producer result against that required artifact, and preserves both path/hash pairs plus current owned Phase 4/6/8 process-proof path-hashes in the implementation result. It freshly fetches both exact base/head refs and invokes the production currentness validator with both required fetched SHAs before ready and again after ready immediately before merge, preserving evidence that provider/fetched/reviewed base and head OIDs all agree. If `auto_merge_after_phase_9=false`, Phase 9 returns `VERIFIED_DRAFT_PR` with `pre_merge_base_sha=null`. If true, it assigns `pre_merge_base_sha` only after that complete equality, then returns `VERIFIED_MERGED` only after refreshed-base reachability proof. An inequality leaves the pre-merge field null, invalidates Phase 8, and performs no merge.

### Stage 4 — `gate` (manual or automated)

The PR sits until merge eligibility clears (CI green, branch protection requirements met, human review if the project requires it). The session is dormant during this stage; the orchestrator process may have exited but the session manifest persists.

### Stage 5 — `merged`

A merge event on the PR is the wake signal. Detection mechanism: a webhook from GitHub, a polling job, or a manual trigger. Poller evidence only selects a candidate row. Before any local-base or persisted-session mutation, the resumer independently re-reads the exact PR URL and requires `MERGED`, exact full head OID, exact base ref, exact merge commit OID, and merge containment on the freshly fetched recorded base. For externally/manual merged PRs, `pre_merge_base_sha` stays unresolved until the resumer derives the immediate pre-merge parent from trusted merge-method and commit-parent evidence. Supported two-parent merge and one-parent squash relationships are explicit; rebase or ambiguous history blocks. `pr_open_base_sha`, current poller `base_ref_oid`, and `branch_out_sha` are never substitutes.

### Stage 6 — `post-merge-wake`

The session **resumes** at this stage. The same orchestrator (or a successor matching the session manifest) dispatches the post-merge tasks:

1. **Pull the recorded base + verify rebase.** Update local `${base_branch}` to the merge SHA after verifying the PR reports that base. If any other in-flight WU sessions had branches rebased as part of (or after) this merge, dispatch the rebase-verification gate against their recorded parent per `~/ai/conventions/rebase-verification.md`. Their gate failures may halt them, but they do not halt the merging session because it has already merged.
2. **Re-run the test suite on the merged base.** Confirm the merged code passes its own suite under the new tree. A regression here means the merge introduced a bug that two-PR interaction created.
3. **Verify coverage did not regress.** Compare project-level coverage at the merge SHA against the validated immediate `pre_merge_base_sha`, captured by the automated merge path or safely derived at wake time. Any drop is a regression that needs disposition (in `${worktree_path}/DECISIONS.md` or a follow-up tracker ticket).
4. **Verify behaviors / contracts are the same.** For each contract document touched by the WU (i.e., `${planning_dir}/contracts/<wu>-*.md`), verify the merged tree still satisfies the contract. Same check as the rebase-verification gate but anchored at the merge SHA.
5. **Drift check.** Same as the rebase-verification drift check, but compared against `branch_out_sha`, resolved from the recorded `base_branch` at WU spawn time. Surface any drift between WU branch-out and final merge.
6. **Prep next WU.** If the session manifest declares a successor (e.g., next WU in the prerequisite chain), the orchestrator hands off the planning dir and any carried context (e.g., a labels / parent issue) to the next WU's spawn. If no successor declared, the post-merge wake closes the session without spawning anything.

### Stage 7 — `close`

The session's final manifest is written: closing audit-history entry, list of post-merge findings (test re-run result, coverage delta, drift report), the cross-link comment posted on the ticket, and the next-WU pointer if any. Only after verified close or successor-handoff completion, the resumer removes the exact row from the same declared `R/sessions.active-wake.json` in the same locked transaction as final manifest closure. The planning dir is sealed (no further writes) and the session enters the historical record.

## Manifest schema (rough)

```json
{
  "session_id": "<root-invocation-uuid>",
  "ticket_id": "NES-NN",
  "ticket_system": "linear",
  "branch": "wu-prereq-01-segmentation",
  "base_branch": "feature/example",
  "branch_out_sha": "<base-sha-at-spawn>",
  "pr_open_base_sha": "<base-sha-at-draft-acquisition>",
  "phase_8_reviewed_base_sha": "<immutable-phase-8-base-sha>",
  "phase_8_reviewed_head_sha": "<immutable-phase-8-head-sha>",
  "phase_9_currentness_result": "<PASS-or-null>",
  "phase_9_currentness_path": "<absolute-path-or-null>",
  "phase_9_currentness_sha256": "<sha256-or-null>",
  "pre_merge_base_sha": "<immediate-base-sha-before-merge-or-null-while-open>",
  "worktree_path": "/home/nes/projects/agent-runner/worktrees/wu-prereq-01-segmentation",
  "planning_dir": "/home/nes/projects/agent-runner/planning/wu-prereq-01-segmentation",
  "spawned_at": "<iso8601>",
  "phase_history": [{"phase": "0", "status": "complete", "ts": "..."}, ...],
  "draft_pr_url": "<url-or-null>",
  "draft_pr_number": "<number-or-null>",
  "draft_pr_head_sha": "<full-sha-or-null>",
  "merge_sha": "<sha-or-null>",
  "post_merge_base_sha": "<refreshed-base-sha-or-null>",
  "merged_at": "<iso8601-or-null>",
  "post_merge": {
    "test_rerun_status": "passed | failed | not-run",
    "coverage_delta": {"before": 0.812, "after": 0.812, "verdict": "no-regression"},
    "contract_verify": "ok | drift",
    "drift_report_path": "<path-or-null>"
  },
  "successor_session_brief": "<path-or-null>",
  "closed_at": "<iso8601-or-null>"
}
```

## Composition for the wake mechanism

Per `~/ai/VALUES.md` § Small specialized tools form an ecosystem and § Composition over flag-stuffing, the wake mechanism is composed from three single-concern components:

```
~/ai/tools/scheduler/  ──(periodic trigger)──>  wu-session-wake root  ──(batch status)──>  ~/ai/tools/pr-batch-poller/
                                                               └──(one exact row)──>  ~/ai/agents/wu-session-resumer.md
```

- `scheduler` schedules a recurring task (e.g. every 10 min). It does not know what GitHub or PRs are.
- The scheduler or a manual caller starts one `wu-session-wake` composition run with `run_id` and one explicit live runtime root `R`; direct composition passes `P`, while feature composition passes that feature's `F/routes`. It never recursively discovers or aggregates indexes and never guesses the current invocation UUID. The root derives `wake_invocation_uuid` from runner provenance and owns the run report, canonical expected-process manifest, post-dispatch marker/hash join, exactly-once resumer dispatch, canonical header-first process-tree-auditor report with one PASS verdict and producer-owned report/root/expected/trace/companion binding, and aggregate sentinel.
- `pr-batch-poller` fetches the status of N in-flight PRs in **one** GraphQL call. It does not know about scheduling or session lifecycle.
- `wu-session-resumer` wakes a single session from one exact row already joined by `wu-session-wake`. It does not know about polling or aggregate fanout.

This is intentionally NOT one binary that "polls hourly and wakes sessions" — that would entangle three concerns. The root caller cohort is scheduler-triggered or manual; both execute the same `wu-session-wake` dispatch surface and evidence contract.

## Persisted-data cutover

The strict wake path has no runtime legacy fallback. Before enabling it over pre-cutover planning data, disable wake dispatch, run `~/ai/tools/wu-session-migration/` in deterministic dry-run mode with the explicit reviewed inventory SHA-256, review the plan, trusted capture evidence, conflict resolutions, and accepted-breakage dispositions, then run apply separately. Apply creates one `sessions.active-wake.json` beside each of the seven reviewed source indexes and leaves every `sessions.index.json` unchanged as history. OPEN sessions may retain `pre_merge_base_sha=null`; no migration may freeze a current base OID, PR-open snapshot, or `branch_out_sha` as a future pre-merge baseline. Closed/post-merge-complete history, closed-unmerged PRs, non-PR local integrations, malformed placeholders, unresolved conflicts, and accepted-breakage rows do not enter the active index.

All session-manifest and active-index writers invoke the executable at `~/ai/tools/wu-session-migration` with a closed `wu-session-runtime-write-v1` request; historical `sessions.index.json` remains read-only inventory, and no operator reproduces the lock/journal algorithm or writes a target directly. Exact operations are `phase0-init --request <path>`, `cold-start-disposition-bind --request <path>`, `phase3-bind --request <path>`, `phase7-upsert --request <path>`, `phase9-update --request <path>`, `resumer-update --request <path>`, and `resumer-close --request <path>`. Every request binds exact `${planning_dir}/session.json`, manifest `planning_dir`, declared immediate parent live runtime root `R=${planning_dir}/..`, and exact `R/sessions.active-wake.json`. Direct mode requires `R=P`; feature direct/refactoring mode requires canonical `R=F/routes` strictly below the same top-level `P`. The separately normalized scratch directory may be outside `R` but must remain strictly below that `P`. All paths and active rows are normalized, no-symlink, descriptor-validated, immediate-child, and unique within their one owner index by PR/branch wake join, manifest, and ticket/branch. Each request also binds full row identity where applicable, source SHA-256/device/inode/mode, complete replacement projections, input-set digest, and payload digest. The shared primitive acquires the exclusive flock, durably writes a closed staging journal before any backup/replacement, recovers exact transaction-bound artifacts, holds no-follow parent descriptors, stages and fsyncs backups/replacements, rechecks every source and read-only guard after committing journal durability and again immediately before and after manifest replacement, performs descriptor-relative replacements/unlinks/fsyncs, and retains an actionable journal on unsafe rollback. Guards are never staged, backed up, replaced, unlinked, or fsynced as changed content. Individual file replacements are atomic; the cross-file operation is interruption-recoverable, not observer-atomic, so wake remains disabled for migration cutover/recovery.

After apply, every wakeable row uses canonical `draft_pr_url`, full `draft_pr_head_sha`, `base_branch`, `session_manifest_path`, and full identity OIDs. Active rows contain none of the retired index keys `pr_url`, `head_sha`, `pr_head_sha`, `manifest_path`, `manifest`, `base`, or `pre_merge_main_sha`. Historical excluded records may retain old fields because `sessions.index.json` is not a runtime input.

The wake mechanism does NOT live in any application-layer project (e.g. `agent-runner`). Per `~/ai/VALUES.md` § Lean clients, ecosystem-wide infrastructure belongs in `~/ai/`, not in any single client repo.

## Wiring Status

The lifecycle rule is split across concrete operators, tools, and one composition workflow:

- `~/ai/tools/scheduler/` — generic scheduled-task primitive. <!-- INTENTIONAL: scheduler runtime implementation is tool work, not an operator procedural sub-step; this convention only names the scheduling concern boundary. -->
- `~/ai/tools/pr-batch-poller/` — batched GitHub PR status query. Wired in `~/ai/tools/pr-batch-poller/README.md` § CLI grammar and § Resumer-handoff shape.
- `~/ai/agents/wu-session-resumer.md` — wakes a single session given a merge event. Wired in `~/ai/agents/wu-session-resumer.md` § Procedure.
- Wake composition across scheduler, poller, and resumer. Wired in `~/ai/workflows/wu-session-wake.md` § Workflow Dispatch Surface, § Composition Report, and § Process-Tree Relationship.
- `successor_session_brief` chaining. Wired in `~/ai/agents/wu-session-resumer.md` § Procedure steps 12-15 for handoff writing and `~/ai/agents/implementation-pipeline-orchestrator.md` § Phase 0 for predecessor manifest import during WU-N+1 spawn.
- Manifest storage. Wired in `~/ai/agents/implementation-pipeline-orchestrator.md` § Phase 0 through executable `phase0-init`, through pre-PR `cold-start-disposition-bind` and `phase3-bind` with caller-owned readback, then through `phase7-upsert` and `phase9-update`; the resumer uses `resumer-update` and `resumer-close` for exact active-row maintenance.
- Post-merge contract and drift checks. Wired in `~/ai/agents/wu-session-resumer.md` § Procedure steps 8-10. <!-- INTENTIONAL: the remaining overlap with `~/ai/conventions/rebase-verification.md` is design consolidation work, not a missing lifecycle dispatch step. -->

## Cross-references

- Implementation pipeline: `~/ai/workflows/implementation-pipeline.md`
- Implementation orchestrator: `~/ai/agents/implementation-pipeline-orchestrator.md`
- Rebase verification: `~/ai/conventions/rebase-verification.md`
- Process tree audits: `~/ai/agents/process-tree-auditor.md`
- Ticket-system pluggability: `~/ai/agents/implementation-pipeline-orchestrator.md` § Ticket System Pluggability
