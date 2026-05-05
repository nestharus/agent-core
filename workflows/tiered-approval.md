---
workflow:
  id: tiered-approval
workflow_dispatch_contract:
  orchestrator: "root orchestrator before visible external actions"
  inputs:
    - "candidate action, current state, audience visibility, reversal path, and any pre-authorized runbook"
    - "project DECISIONS.md or equivalent when pre-authorization is claimed"
  expectations:
    - "classifies actions into read, confined-write, or visible-write tiers"
    - "requires explicit per-action approval before Tier 3 visible writes unless a runbook pre-authorizes the exact action"
    - "keeps approval questions root-owned when delegated agents need user input"
  outputs:
    - "approval request with state, reversal path, and concrete action for Tier 3 work"
    - "execution log details for approved or pre-authorized visible actions"
    - "clear Tier 2 treatment for routine draft PR creation and maintenance"
  non_goals:
    - "does not batch multiple visible actions into one approval"
    - "does not treat ambiguous user replies as approval"
    - "does not let one agent both propose and execute a Tier 3 action without human approval"
---
# Tiered Approval Safety

Every action an agent can take falls into one of three tiers.
Higher tiers require more human gating.
This file defines the tiers.
Implementation, roadmap, deployment, and live-server workflows
cite it rather than restating the policy.

Delegated questions about approval or visible actions follow `~/ai/conventions/agent-questions-and-session-graph.md`.

## The three tiers

| Tier | Examples | Authorization |
|---|---|---|
| 1 — Read | List channels, read messages, fetch member lists, inspect roles, query a database, read a file, enumerate a directory | Always allowed |
| 2 — Confined write | Edit files locally, commit to git, run tests, open a draft PR, write to `.tmp/`, modify a worktree | Always allowed |
| 3 — Visible write | Send messages to users, create channels, modify roles, kick or ban, change permissions, deploy, promote a draft PR to ready-for-review on a public-audience repo, publish to a landing page, send email-ready HTML | **Requires explicit per-action approval**, unless a runbook is pre-authorized in `DECISIONS.md` or the project equivalent |

Tier meanings:

- Tier 1 reads state.
- Tier 2 mutates confined project state.
- Tier 3 changes what users or external audiences can see,
  receive, or be affected by.

## Tier 3 rule

Before executing any action visible to end users or external
audiences, describe exactly what will happen and wait for explicit
confirmation.

1. **State** — describe the current state of what will change.
2. **Reversal path** — describe how to undo the change if it goes
   wrong.
3. **Ask** — present the action, current state, and reversal path in
   one message.
4. **Wait for explicit yes** — do not proceed on ambiguous responses
   such as "sure", "ok", or "I think so".
5. **Execute** — perform the action.
6. **Verify** — confirm the result is what you intended.
7. **No batching** — each visible action is its own cycle.

Operational rule:

- Do not bundle multiple Tier-3 actions into one approval request,
  even when the actions are related.
- A later Tier-3 action needs its own approval unless a pre-authorized
  runbook in `DECISIONS.md` covers it.
- If a delegated agent needs user input about a visible action or approval, it must return `NEEDS_INPUT:<question_artifact>` and stop. The root orchestrator surfaces the question, writes the answer artifact, and blocks the visible action until continuation evidence exists.

## Why per-action

Approval for one Tier-3 action does not imply approval for the next.
Actions with different blast radii must be approved individually.
"Yes to kick user A" is not "yes to kick users A, B, and C".

The only exception is a runbook that has been pre-authorized in
`DECISIONS.md` or the project equivalent.
Pre-authorization must be explicit.
A runbook does not self-authorize.

## Tier 2 clarification — draft PRs

Opening a **draft** PR is Tier 2, not Tier 3.
Draft PRs are routine output from the implementation pipeline.
They are not treated as audience-facing until promoted or otherwise
opened as a non-draft review artifact.

- Opening a draft PR -> **Tier 2**.
- Amending a commit on a draft PR -> **Tier 2**.
- Force-pushing with `--force-with-lease` to a draft PR during the
  CodeRabbit loop -> **Tier 2**.
- Promoting a draft to ready-for-review on an **internal** repo
  -> **Tier 2**.
- Promoting a draft to ready-for-review on a
  **public-audience** repo -> **Tier 3**.
- Opening a non-draft PR on any repo -> **Tier 3**.

Guardrails:

- Do not list draft PR creation anywhere as Tier 3.
- Do not treat routine draft-PR maintenance as a visible write.
- Promotion, non-draft opening, and other public-audience PR actions
  are the approval boundary.

## Tier 3 — audience-dependent examples

These are Tier 3 because they are visible outside the confined
implementation loop or directly affect users:

- Sending messages to users by Discord, email, Slack, SMS, or similar
  channels.
- Modifying user-facing permissions, roles, or access.
- Deploying to production or any audience-visible environment.
- Publishing to a public URL such as a landing page, blog, or docs
  site.
- Sending email-ready HTML or newsletter drafts.
- Promoting a PR to ready-for-review on a public-audience repo.
- Opening a non-draft PR on any repo.
- Posting to external services through hooks or APIs that reach
  third-party users.

## Pre-authorization via DECISIONS.md

Projects can pre-authorize specific Tier-3 runbooks by recording them
in `DECISIONS.md` or the project equivalent.
This is the only exception to explicit per-action approval.

A pre-authorized runbook:

- Names the exact action shape.
- States the conditions under which the pre-authorization applies.
- Includes a reversal path as part of the runbook.
- Is dated and signed by the human authorizing it.

Agents may execute a pre-authorized runbook without asking again for
that exact covered action, but must still log execution details for
audit: actor, time, and target.

Delegated questions about whether a runbook covers an action use the root-surfaced question envelope. Sub-agents must not treat a direct user answer inside their own transcript as Tier-3 approval evidence.

## Relation to other workflows

- `~/ai/workflows/implementation-pipeline.md` opens draft PRs as Tier 2;
  promotion to ready-for-review follows this file.
- `~/ai/workflows/deployment.md` treats production deployments as
  Tier 3 unless a specific runbook is pre-authorized.
- Live-server projects such as moderation tooling apply this file's
  Tier-3 rule to every user-visible action.

## Interaction with no-super-agents

See `~/ai/models/roles.md`.
No single agent both proposes and executes a Tier-3 action.
The proposer writes the action description.
A human approves.
The executor runs it.
