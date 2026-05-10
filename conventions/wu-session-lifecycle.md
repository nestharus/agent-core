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

### Stage 3 — `draft-PR`

Phase 9 produces a draft PR. The PR URL + head SHA are appended to the session manifest. If `auto_merge_after_phase_9=true`, the PR is also marked ready and `--auto`-merge enabled.

### Stage 4 — `gate` (manual or automated)

The PR sits until merge eligibility clears (CI green, branch protection requirements met, human review if the project requires it). The session is dormant during this stage; the orchestrator process may have exited but the session manifest persists.

### Stage 5 — `merged`

A merge event on the PR is the wake signal. Detection mechanism: a webhook from GitHub, a polling job, or a manual trigger. The session manifest is updated with the merge SHA + timestamp.

### Stage 6 — `post-merge-wake`

The session **resumes** at this stage. The same orchestrator (or a successor matching the session manifest) dispatches the post-merge tasks:

1. **Pull main + verify rebase.** Update the local `main` to the merge SHA. If any other in-flight WU sessions had branches rebased as part of (or after) this merge, dispatch the rebase-verification gate per `~/ai/conventions/rebase-verification.md` for each affected branch. Their gate failures may halt them, but they do not halt the merging session — it has already merged.
2. **Re-run the test suite on the merged main.** Confirm the merged code passes its own suite under the new tree. A regression here means the merge introduced a bug that two-PR interaction created (the WU's tests passed pre-merge against an older `main`; the merge tree may behave differently).
3. **Verify coverage did not regress.** Compare project-level coverage at the merge SHA against the pre-merge `main` SHA. Any drop is a regression that needs disposition (in `${worktree_path}/DECISIONS.md` or a follow-up tracker ticket).
4. **Verify behaviors / contracts are the same.** For each contract document touched by the WU (i.e., `${planning_dir}/contracts/<wu>-*.md`), verify the merged tree still satisfies the contract. Same check as the rebase-verification gate but anchored at the merge SHA.
5. **Drift check.** Same as the rebase-verification drift check, but compared against the SHA from which this WU branched (i.e., the original `main` at WU spawn time). Surface any drift between WU branch-out and final merge.
6. **Prep next WU.** If the session manifest declares a successor (e.g., next WU in the prerequisite chain), the orchestrator hands off the planning dir and any carried context (e.g., a labels / parent issue) to the next WU's spawn. If no successor declared, the post-merge wake closes the session without spawning anything.

### Stage 7 — `close`

The session's final manifest is written: closing audit-history entry, list of post-merge findings (test re-run result, coverage delta, drift report), the cross-link comment posted on the ticket, and the next-WU pointer if any. The planning dir is sealed (no further writes) and the session enters the historical record.

## Manifest schema (rough)

```json
{
  "session_id": "<root-invocation-uuid>",
  "ticket_id": "NES-NN",
  "ticket_system": "linear",
  "branch": "wu-prereq-01-segmentation",
  "worktree_path": "/home/nes/projects/agent-runner/worktrees/wu-prereq-01-segmentation",
  "planning_dir": "/home/nes/projects/agent-runner/planning/wu-prereq-01-segmentation",
  "spawned_at": "<iso8601>",
  "phase_history": [{"phase": "0", "status": "complete", "ts": "..."}, ...],
  "draft_pr_url": "<url-or-null>",
  "merge_sha": "<sha-or-null>",
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
~/ai/tools/scheduler/  ──(periodic trigger)──>  ~/ai/tools/pr-batch-poller/  ──(per merged PR)──>  ~/ai/agents/wu-session-resumer.md
```

- `scheduler` schedules a recurring task (e.g. every 10 min). It does not know what GitHub or PRs are.
- `pr-batch-poller` fetches the status of N in-flight PRs in **one** GraphQL call. It does not know about scheduling or session lifecycle.
- `wu-session-resumer` agent wakes a single session given a merge event. It does not know about polling.

This is intentionally NOT one binary that "polls hourly and wakes sessions" — that would entangle three concerns. Wired in `~/ai/workflows/wu-session-wake.md` § Procedure.

The wake mechanism does NOT live in any application-layer project (e.g. `agent-runner`). Per `~/ai/VALUES.md` § Lean clients, ecosystem-wide infrastructure belongs in `~/ai/`, not in any single client repo.

## Wiring Status

The lifecycle rule is split across concrete operators, tools, and one composition workflow:

- `~/ai/tools/scheduler/` — generic scheduled-task primitive. <!-- INTENTIONAL: scheduler runtime implementation is tool work, not an operator procedural sub-step; this convention only names the scheduling concern boundary. -->
- `~/ai/tools/pr-batch-poller/` — batched GitHub PR status query. Wired in `~/ai/tools/pr-batch-poller/README.md` § CLI grammar and § Resumer-handoff shape.
- `~/ai/agents/wu-session-resumer.md` — wakes a single session given a merge event. Wired in `~/ai/agents/wu-session-resumer.md` § Procedure.
- Wake composition across scheduler, poller, and resumer. Wired in `~/ai/workflows/wu-session-wake.md` § Procedure.
- `successor_session_brief` chaining. Wired in `~/ai/agents/wu-session-resumer.md` § Procedure steps 10-13 for handoff writing and `~/ai/agents/implementation-pipeline-orchestrator.md` § Phase 0 for predecessor manifest import during WU-N+1 spawn.
- Manifest storage. Wired in `~/ai/agents/implementation-pipeline-orchestrator.md` § Phase 0 for `${planning_dir}/session.json` and `${planning_dir}/../sessions.index.json`, and updated in § Phase 9 before dormancy.
- Post-merge contract and drift checks. Wired in `~/ai/agents/wu-session-resumer.md` § Procedure steps 7-8. <!-- INTENTIONAL: the remaining overlap with `~/ai/conventions/rebase-verification.md` is design consolidation work, not a missing lifecycle dispatch step. -->

## Cross-references

- Implementation pipeline: `~/ai/workflows/implementation-pipeline.md`
- Implementation orchestrator: `~/ai/agents/implementation-pipeline-orchestrator.md`
- Rebase verification: `~/ai/conventions/rebase-verification.md`
- Process tree audits: `~/ai/agents/process-tree-auditor.md`
- Ticket-system pluggability: `~/ai/agents/implementation-pipeline-orchestrator.md` § Ticket System Pluggability
