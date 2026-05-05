# Tickets-First Review Workflow

Alternative review topology where the tracker ticket — not a draft PR — is the unit of review. The branch is reviewed locally on the reviewer's machine; a PR is only opened **after** review passes.

## When to use

Projects opt into this variant when:

- The PR list is a signal of *review-ready work* and shouldn't be polluted by pre-review or work-in-progress branches.
- Reviewers prefer pulling and exercising branches locally over reading diffs in the GitHub UI.
- The tracker (Jira, Linear, GitHub Issues) is already the canonical place where work is described, and a parallel PR description duplicates the ticket.
- Branch ownership is clear — the author drafts a PR themselves once review passes, so the orchestrator never opens one speculatively.

The default — draft PRs as a routine pipeline step — is documented in `~/ai/conventions/git.md` under "Pull Requests". This file describes the variant; projects declare opt-in in their own `AGENTS.md`.

## Branch and commit naming (required)

Projects on this workflow inherit the ticket-prefixed naming rule from `~/ai/conventions/git.md` § Naming and § Commits, and treat both as **mandatory** rather than recommended:

- **Branches** must be named `<TICKET-ID>-<short-description>` (e.g. `INFA-118-download-status-surface-script-error`). The branch name is the primary index between the ticket, the worktree on disk, and the eventual PR — there is no draft PR open during review to disambiguate, so the branch name itself has to be unambiguous.
- **Commits** must reference the ticket via a leading scope (`INFA-118: <subject>`) or a `Refs: INFA-118` trailer. A branch's head commit must always carry the ticket reference; per-commit references are preferred.
- Drop the `fix/` / `feat/` kind prefixes — the ticket conveys work type.
- The rule applies to branches **created from the opt-in date forward**. Pre-policy branches already on origin do not need to be renamed — instead, the ticket that ticketizes them cites the existing branch name in its `Branch:` line. Renaming live branches has high churn (push new, delete old, rewrite tickets, re-point any worktrees and stacked dependents) for low value once the ticket is the unit of review. Apply the rule to all *new* branches and let the legacy ones age out as they merge or get abandoned.

## Lifecycle

```
ticket created (status: To Do)
    ↓
branch pushed to origin, ticket cites the branch name (status: In Progress)
    ↓
reviewer pulls origin/<branch>, exercises locally (status: In Review)
    ↓
review passes → branch owner drafts PR (status: stays In Review until merge)
    ↓
PR merges → ticket closes (status: Done)
```

The tracker board's columns mirror this — projects using this workflow add an `In Review` column to their default `To Do / In Progress / Done` flow.

## Ticket body shape

Each ticket carries a fixed shape so the reviewer doesn't have to chase context across surfaces. At minimum:

```
## Source
- Branch: <branch-name> (origin push state confirmed)
- Author: <github-handle>
- (If ticketizing an existing PR) Origin PR: <url> (closed in favor of ticket-first review)
- Routing rationale: <why this board / parent epic>

## Key paths touched
- <top file paths from the diff>

## What this branch does
<short summary — 2-4 lines>

## Acceptance criteria for local review
- Reviewer pulls origin/<branch> and reviews diff vs origin/<base>
- Tests on the branch pass — name the suite the reviewer runs
- Reviewer signs off → THEN a fresh draft PR is opened by the branch owner
```

Boards with stricter documentation requirements (e.g. frontend-bug boards needing reproduction context, or product-question boards needing intended-behavior framing) extend this shape per the project's own conventions.

## Transitioning existing draft PRs to this workflow

When a project switches mid-stream and has a backlog of pre-review draft PRs, transition each one:

1. File a tracker ticket with the body shape above. Use a label that pairs the ticket to the PR — e.g. `<author>-transition-<pr-number>` — and avoid colliding with any label already in use by other operators (notably `from-pr-<N>`, which `~/ai/agents/coverage-finding-publisher.md` already claims for coverage-expansion artifacts).
2. Cross-link the ticket to any existing tracking artifacts via `Relates`.
3. Comment on the PR pointing at the new ticket key, then close the PR.
4. The branch stays on origin; the ticket now references it.

The branch is not deleted on PR close — it lives on origin until either the new draft PR merges or the work is abandoned.

## Retrofits over `~/ai/`

- `~/ai/conventions/git.md` "Pull Requests" defaults to draft-PRs-are-routine. That default still holds for projects that haven't opted into this workflow. Projects that opt in declare so in their `AGENTS.md`; the default no longer applies to them.
- `~/ai/workflows/pr-review.md` describes the review *gates*. Those gates run **after** review starts in this workflow — local on the reviewer's machine for the diff/multi-concern/justification gates, and on the eventually-drafted PR for any gate that requires CI signal.
- The gate-ownership rules in `~/ai/conventions/gate-ownership.md` still apply. The "Draft PR open" row moves later in the lifecycle for this variant; everything else is unchanged.
- `~/ai/workflows/implementation-pipeline.md` Phase 8.5 is the orchestrator-side hook for this workflow. Projects on this variant set `tickets_first_variant=true` in the `implementation-pipeline-orchestrator` brief; the orchestrator inserts the Phase 8.5 human-local-review gate between Phase 8 and Phase 9. Without that flag, the orchestrator's default Phase 9 opens a draft PR after only the automated gates pass — which is the wrong sequence for this variant.
