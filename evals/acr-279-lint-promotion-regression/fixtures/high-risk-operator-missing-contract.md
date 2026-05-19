---
description: 'Fixture high-risk operator that would touch Jira credentials and branch topology without a contract'
model: gpt-high
output_format: ''
---

# High Risk Operator Missing Contract Fixture

## Declared roles

`orchestration`, `accessor`.

## Role

This fixture intentionally looks like a high-risk operator for lint-promotion regression evidence. It references external tickets, credentials, branch topology, and worktrees, but it intentionally has no `## Contract` block.

## Required Inputs

- `jira_url`
- `jira_project`
- `jira_account_email`
- `branch_name`
- `worktree_path`

## Procedure

Read `JIRA_API_KEY`, inspect a ticket, create or update ticket comments, create a worktree branch, and coordinate a branch-topology handoff.

## Stop Conditions

- `BLOCKED` if credentials are missing.
- `NEEDS_INPUT` if branch or ticket inputs are absent.
