# Fixture AGENTS Routing

## Declared roles

`orchestration`, `accessor`, `formatter`.

## Operator Routing Table

- `high-risk-operator-missing-contract` - Fixture operator that touches Jira credentials, ticket writes, branch topology, and worktrees while intentionally lacking a `## Contract` block.
  File: [high-risk-operator-missing-contract.md](high-risk-operator-missing-contract.md) | Inputs: `jira_url`, `jira_project`, `jira_account_email`, `branch_name`, `worktree_path` | Model: `gpt-high`
