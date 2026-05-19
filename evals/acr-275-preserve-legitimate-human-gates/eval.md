# ACR-275 Preserve Legitimate Human Gates

## Lifecycle

WRITE

## Unwanted behavior

ACR-275 cleanup deletes or bypasses legitimate human-owned decision gates while removing local review, including Phase 2.5 problem-map review, real new-value `NEEDS_INPUT`, RCA cap-hit review, prototype dossier approval, ticket disposition approval, backend `BLOCKED` handling, or prototype-test PR publication after dossier approval.

## Structural anchors covered

- `/home/nes/ai/worktrees/acr-275-remove-local-review-steps/workflows/implementation-pipeline.md` — Phase 2.5 problem-map gate and Gate Ownership — snippets `Phase 2.5` and `problem-map review`.
- `/home/nes/ai/worktrees/acr-275-remove-local-review-steps/conventions/gate-ownership.md` — human gate table rows `Draft PR open` and `NEEDS_INPUT new-value question` — snippets `Draft PR open` and `new-value`.
- `/home/nes/ai/worktrees/acr-275-remove-local-review-steps/conventions/agent-questions-and-session-graph.md` — question envelope / new-value questions — snippets `NEEDS_INPUT:<question_artifact_path>`, `scope`, `trade-off`, and `evidence-access`.
- `/home/nes/ai/worktrees/acr-275-remove-local-review-steps/agents/rca-orchestrator.md` — `## NEEDS_INPUT Handling` — snippets `cap-hit`, `human-owned decisions`, `tracker authority`, and `close-policy`.
- `/home/nes/ai/worktrees/acr-275-remove-local-review-steps/workflows/rca.md` — verify-or-return and tracker-close decisions — snippets `cap-hit human review`, `close/stay-open`, and `BLOCKED`.
- `/home/nes/ai/worktrees/acr-275-remove-local-review-steps/agents/prototype-orchestrator.md` — P3 dossier review and P4 prototype-test publication — snippets `approve/revise/reject the dossier` and `prototype-test PR publication`.
- `/home/nes/ai/worktrees/acr-275-remove-local-review-steps/workflows/build-prototype.md` — P3 proof/dossier gate and P4 mechanical publication — snippets `not prototype source-code review` and `draft PR as a transfer mechanism`.
- `/home/nes/ai/worktrees/acr-275-remove-local-review-steps/agents/jira-operator.md` and `/home/nes/ai/worktrees/acr-275-remove-local-review-steps/agents/linear-operator.md` — ticket-create disposition and backend authority / `BLOCKED` handling — snippets `status-transition`, `workflow-guard`, and `BLOCKED`.
- `/home/nes/ai/worktrees/acr-275-remove-local-review-steps/workflows/pr-review.md` — Phase 8 question-dependent model gate blocks — snippets `dependent gate outputs need user-owned answers`.
- `/home/nes/ai/worktrees/acr-275-remove-local-review-steps/workflows/index.json` — generated catalog mirror — snippets `tickets-first-review` and preserved workflow catalog entries.

## Non-fire cases

- Deleting Phase 8.5 local-review text.
- Retiring `tickets_first_variant`.
- Removing tickets-first branch-as-review-unit lifecycle text.
- Opening a draft PR routinely after Phase 8/8.X.

## Finding contract

Findings must include the required fields `eval_id`, `severity`, `evidence_paths`, `summary`, `suggested_action`, and `confidence`.

Recommended extension fields are `surface`, `preserved_gate`, `removed_anchor`, `policy_source`, `trace_locator`, and `phase`.

`severity` should use `blocking` when the evidence removes or bypasses a preserved human-owned gate or ticket/backend authority stop, and `residual` when the evidence weakens preservation wording without proving execution would bypass the gate.

## Deterministic Inspected-Surface Enumeration

| Preserved gate | File | Section | Line range | Stable text snippet |
|---|---|---|---:|---|
| Phase 2.5 problem-map gate | `/home/nes/ai/worktrees/acr-275-remove-local-review-steps/workflows/implementation-pipeline.md`; `/home/nes/ai/worktrees/acr-275-remove-local-review-steps/conventions/gate-ownership.md` | Phase 2.5 problem-map review; human gate table | Hookpoint lines 105-108; 47-50 | `Phase 2.5 problem-map gate ownership`; `Leave as a legitimate human gate` |
| Legitimate new-value `NEEDS_INPUT` | `/home/nes/ai/worktrees/acr-275-remove-local-review-steps/conventions/agent-questions-and-session-graph.md` | `NEEDS_INPUT` question envelope / new-value questions | Coverage-inventory lines 19-37; 43-51; 163-169; 301-305 | `value, scope, trade-off, evidence-access, backend-authority`; `continuation evidence` |
| RCA cap-hit review | `/home/nes/ai/worktrees/acr-275-remove-local-review-steps/agents/rca-orchestrator.md`; `/home/nes/ai/worktrees/acr-275-remove-local-review-steps/workflows/rca.md` | `## NEEDS_INPUT Handling`; RCA verify-or-return / tracker-close decisions | Coverage-inventory lines 47, 102-111; 13, 47, 172, 180-184, 192-202, 210-221 | `cap-hit`; `human-owned decisions`; `close/stay-open decisions` |
| Prototype P3 dossier review | `/home/nes/ai/worktrees/acr-275-remove-local-review-steps/agents/prototype-orchestrator.md`; `/home/nes/ai/worktrees/acr-275-remove-local-review-steps/workflows/build-prototype.md` | P3 dossier review; P3 proof/dossier gate | Coverage-inventory lines 13-15, 197-204; 23-29, 205-207 | `approve/revise/reject the dossier`; `not prototype source-code review` |
| Original-ticket disposition approval | `/home/nes/ai/worktrees/acr-275-remove-local-review-steps/agents/prototype-orchestrator.md`; `/home/nes/ai/worktrees/acr-275-remove-local-review-steps/workflows/build-prototype.md` | P3 spawned-ticket / branch-disposition support | Coverage-inventory lines 197-204; 205-207 | `spawned-ticket/branch-disposition support`; `downstream decisions` |
| Ticket-create disposition approval | `/home/nes/ai/worktrees/acr-275-remove-local-review-steps/agents/jira-operator.md`; `/home/nes/ai/worktrees/acr-275-remove-local-review-steps/agents/linear-operator.md` | backend task contracts / ticket-create disposition | Hookpoint lines 56-70, 300-305; 259-272, 308-315 | `backend authority`; `status-transition`; `auth`; `ambiguous label/project` |
| Ticket backend `BLOCKED` state handling | `/home/nes/ai/worktrees/acr-275-remove-local-review-steps/agents/jira-operator.md`; `/home/nes/ai/worktrees/acr-275-remove-local-review-steps/agents/linear-operator.md`; `/home/nes/ai/worktrees/acr-275-remove-local-review-steps/workflows/rca.md` | R1-F04 backend authority / workflow guard | Hookpoint lines 56-70, 300-305; 259-272, 308-315; coverage-inventory lines 210-221 | `BLOCKED`; `workflow-guard stop states`; `backend authority questions` |
| Prototype-test PR publication after dossier approval | `/home/nes/ai/worktrees/acr-275-remove-local-review-steps/agents/prototype-orchestrator.md`; `/home/nes/ai/worktrees/acr-275-remove-local-review-steps/workflows/build-prototype.md` | P4 prototype-test publication; P4 mechanical publication | Coverage-inventory lines 216-225; 209-230 | `prototype-test PR publication`; `opens a draft PR as a transfer mechanism` |
| Phase 8 question-dependent model gate blocks | `/home/nes/ai/worktrees/acr-275-remove-local-review-steps/workflows/pr-review.md`; `/home/nes/ai/worktrees/acr-275-remove-local-review-steps/agents/implementation-pipeline-orchestrator.md` | Phase 8 question handling / process-tree Audit #3 | Coverage-inventory lines 24-28, 225-233, 243, 261-265; problem-map lines 538-555 | `dependent gate outputs need user-owned answers`; `blocking process-tree verdict halts draft PR` |
| Catalog synchronization preserves legitimate workflows | `/home/nes/ai/worktrees/acr-275-remove-local-review-steps/workflows/index.json` | generated catalog mirror | Coverage-inventory search hits around lines 294, 720-744 | remove local-review metadata without deleting legitimate workflow visibility |
