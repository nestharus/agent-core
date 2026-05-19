# ACR-275 No Pre-Draft Local Review

## Lifecycle

WRITE

## Unwanted behavior

An implementation-pipeline, workflow, convention, routing, Work Manager, or project-policy trace creates or preserves a human branch-local approval/revisions/reject halt after Phase 8 model/evidence gates and before Phase 9 draft PR creation, including renamed Phase 8.5 equivalents, branch-citation ticket comments that replace draft PR publication, or `NEEDS_INPUT` questions that ask for local branch review approval before a draft PR opens.

## Structural anchors covered

- `/home/nes/ai/worktrees/acr-275-remove-local-review-steps/agents/implementation-pipeline-orchestrator.md` — Optional inputs / `tickets_first_variant` — snippet `Phase 8.5 human-local-review gate`.
- `/home/nes/ai/worktrees/acr-275-remove-local-review-steps/agents/implementation-pipeline-orchestrator.md` — Non-Negotiables human-gate restriction — snippet `Human gates are restricted`.
- `/home/nes/ai/worktrees/acr-275-remove-local-review-steps/agents/implementation-pipeline-orchestrator.md` — Phase 8, Phase 8.X, Phase 8.5, and Phase 9 sections — snippets `approval recorded`, `Human Local Review Gate`, and `gh pr create --draft`.
- `/home/nes/ai/worktrees/acr-275-remove-local-review-steps/workflows/implementation-pipeline.md` — Phase 8, Phase 8.5, Phase 9, and Gate Ownership sections — snippets `Post-CodeRabbit Review Gates`, `approve/revise/reject`, and `tickets_first_variant=true`.
- `/home/nes/ai/worktrees/acr-275-remove-local-review-steps/workflows/tickets-first-review.md` — frontmatter dispatch contract, title, When to use, Lifecycle, Acceptance criteria, and Retrofits — snippets `workflow_dispatch_contract`, `reviewed locally`, `reviewer pulls`, and `sign-off before a fresh draft PR`.
- `/home/nes/ai/worktrees/acr-275-remove-local-review-steps/conventions/git.md` — Pull Requests — snippet `Variant - tickets-first review`.
- `/home/nes/ai/worktrees/acr-275-remove-local-review-steps/workflows/pr-review.md` — Phase 8 pre-PR review responsibility — snippet `before a draft PR is opened`.
- `/home/nes/ai/worktrees/acr-275-remove-local-review-steps/conventions/agent-questions-and-session-graph.md` — `NEEDS_INPUT` envelope and dependent-step stop — snippets `NEEDS_INPUT:<question_artifact_path>` and `must not advance dependent workflow steps`.
- `/home/nes/ai/worktrees/acr-275-remove-local-review-steps/conventions/gate-ownership.md` — Human gate table rows `Draft PR open` and `NEEDS_INPUT new-value question` — snippets `Draft PR open` and `automated`.
- `/home/nes/ai/worktrees/acr-275-remove-local-review-steps/AGENTS.md` — implementation-pipeline / tickets-first routing catalog — snippets `tickets_first_variant` and `Phase 8.5`.
- `/home/nes/ai/worktrees/acr-275-remove-local-review-steps/agents/work-manager-operator.md` — Work Manager prompt composition — snippet `tickets_first_variant`.
- `/home/nes/ai/worktrees/acr-275-remove-local-review-steps/workflows/index.json` — generated workflow catalog mirror — snippets `tickets-first-review`, `human local-review gate`, and `eventual draft PR only after local review passes`.
- `/home/nes/ai/worktrees/acr-275-remove-local-review-steps/agents/implementation-pipeline-orchestrator.md` and `/home/nes/ai/worktrees/acr-275-remove-local-review-steps/workflows/implementation-pipeline.md` — Drift 1 stale Phase 7 CodeRabbit wording adjacent to local review — snippets `Phase 7 CodeRabbit`, `CodeRabbit was retired 2026-05-15`, and readiness passes directly to Phase 8.
- `/home/nes/ai/worktrees/acr-275-remove-local-review-steps/agents/implementation-pipeline-orchestrator.md` and ticket comments / audit trace evidence — Drift 2 branch-citation pre-PR ticket comments — snippets `branch-citation ticket comment` and `Phase 9 ticket cross-link always posts the PR URL after gh pr create --draft`.
- `/home/nes/ai/worktrees/acr-275-remove-local-review-steps/agents/implementation-pipeline-orchestrator.md` and orchestrator log / audit-history evidence — missing canonical migration message when stale `tickets_first_variant=true` is observed — snippet `tickets_first_variant=true` plus the exact `## Migration Message Anchor` string.

## Non-fire cases

- Phase 2.5 problem-map review.
- Legitimate new-value `NEEDS_INPUT`.
- RCA cap-hit review.
- Prototype P3 dossier review.
- Ticket backend `BLOCKED` state handling or authority questions.
- Prototype-test PR publication after dossier approval.
- Phase 8 gate `NEEDS_INPUT` for user-owned evidence.
- Process-tree blocking verdicts.
- Phase 8 code-quality non-LOW.

## Finding contract

Findings must include the required fields `eval_id`, `severity`, `evidence_paths`, `summary`, `suggested_action`, and `confidence`.

Recommended extension fields are `wu_id`, `phase`, `gate`, `policy_source`, `question_artifact_path`, `ticket_comment_path`, `prompt_path`, `trace_locator`, and `matched_anchor`.

`severity` should use `blocking` when the evidence preserves or recreates the pre-draft local-review halt, and `residual` when the evidence is stale wording that does not currently route or block execution but can mislead future prompt composition.

## Deterministic Inspected-Surface Enumeration

| Signal | File | Section | Line range | Stable text snippet |
|---|---|---|---:|---|
| 1 | `/home/nes/ai/worktrees/acr-275-remove-local-review-steps/agents/implementation-pipeline-orchestrator.md` | Optional inputs / `tickets_first_variant`; Phase 8.5 vicinity | Problem-map lines 112-117; 593-606 | `Phase 8.5 human-local-review gate`; `approval/revisions/reject`; `blocks Phase 9 until approval` |
| 2 | `/home/nes/ai/worktrees/acr-275-remove-local-review-steps/workflows/implementation-pipeline.md` | Optional phases, expectations, Phase 8.5, Gate Ownership | Coverage-inventory lines 512-524; 551-560; 581-585 | `Human Local Review Gate (tickets-first variant only)`; `tickets_first_variant=true adds Phase 8.5 before Phase 9` |
| 3 | `/home/nes/ai/worktrees/acr-275-remove-local-review-steps/workflows/tickets-first-review.md` | Frontmatter, title, When to use, Lifecycle, Acceptance criteria, Retrofits | Coverage-inventory lines 4-20; 24-25; 55-64; 75-87; 108-112; 127-132 | `human local-review gate between automated review gates and draft PR creation`; `reviewer sign-off before a fresh draft PR` |
| 4 | `/home/nes/ai/worktrees/acr-275-remove-local-review-steps/conventions/git.md` | Pull Requests | Coverage-inventory lines 66-72 | `Variant - tickets-first review`; `draft PR only after local review passes` |
| 5 | `/home/nes/ai/worktrees/acr-275-remove-local-review-steps/conventions/gate-ownership.md` | Human gate table | Coverage-inventory lines 40-53 | `Draft PR open`; `NEEDS_INPUT new-value question`; `automated` |
| 6 | `/home/nes/ai/worktrees/acr-275-remove-local-review-steps/conventions/agent-questions-and-session-graph.md` | `NEEDS_INPUT` envelope and dependent-step stop | Coverage-inventory lines 19-37; 43-51; 163-169; 301-305 | `NEEDS_INPUT:<question_artifact_path>`; `must not advance dependent workflow steps` |
| 7 | `/home/nes/ai/worktrees/acr-275-remove-local-review-steps/workflows/pr-review.md` | Phase 8 pre-PR review responsibility | Coverage-inventory lines 24-28; 225-233; 243; 261-265 | `before a draft PR is opened`; `human ownership starts at promotion` |
| 8 | `/home/nes/ai/worktrees/acr-275-remove-local-review-steps/AGENTS.md` | implementation-pipeline / tickets-first routing catalog | Supported-surface grep lines 176, 177, 421 | `tickets_first_variant`; `Phase 8.5` |
| 9 | `/home/nes/ai/worktrees/acr-275-remove-local-review-steps/agents/work-manager-operator.md` | Work Manager prompt composition | Supported-surface grep line 137; hookpoint line 146 | `tickets_first_variant` |
| 10 | `/home/nes/ai/worktrees/acr-275-remove-local-review-steps/workflows/index.json` | generated workflow catalog mirror | Coverage-inventory search hits around lines 294, 720-744 | `tickets-first-review`; `human local-review gate`; `eventual draft PR only after local review passes` |
| 11 | `/home/nes/ai/worktrees/acr-275-remove-local-review-steps/agents/implementation-pipeline-orchestrator.md`; `/home/nes/ai/worktrees/acr-275-remove-local-review-steps/workflows/implementation-pipeline.md` | Drift 1 CodeRabbit wording adjacent to local review | Proposal Drift 1 anchor | `Phase 7 CodeRabbit`; `CodeRabbit was retired 2026-05-15`; readiness passes directly to Phase 8 |
| 12 | `/home/nes/ai/worktrees/acr-275-remove-local-review-steps/agents/implementation-pipeline-orchestrator.md`; ticket comments / audit trace evidence | Drift 2 branch-citation pre-PR ticket comment | Problem-map lines 593-606; contract Drift 2 | `branch-citation ticket comment`; `Phase 9 ticket cross-link always posts the PR URL after gh pr create --draft` |
| 13 | `/home/nes/ai/worktrees/acr-275-remove-local-review-steps/agents/implementation-pipeline-orchestrator.md`; orchestrator log / audit-history evidence | Migration semantics for stale `tickets_first_variant=true` | Hookpoint insertion anchor lines 585-591; contract expected signal 13 | `tickets_first_variant=true`; migration message anchor below |

## Migration Message Anchor

`tickets_first_variant is removed by ACR-275; proceeding with default Phase 8 -> Phase 8.X -> Phase 9 draft PR flow; no Phase 8.5 local-review gate will run`
