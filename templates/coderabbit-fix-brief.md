# CodeRabbit Comment Fix Brief

You are addressing exactly one CodeRabbit finding.

## Inputs

- `repo`: `${repo}`
- `pr_num`: `${pr_num}`
- `pr_branch`: `${pr_branch}`
- `worktree_path`: `${worktree_path}`
- `comment_id`: `${comment_id}`
- `comment_file_path`: `${comment_file_path}`
- `test_crate_hint`: `${test_crate_hint}`
- `outcome_file_path`: `${outcome_file_path}`

## Task

1. Work only in `${worktree_path}` on branch `${pr_branch}`.
2. Read `${comment_file_path}` as the complete ordered history for this one conversation, then inspect the referenced code. On a later turn, answer CodeRabbit's newest pushback rather than repeating an earlier response.
3. Resolve the finding. If a code change is appropriate, make the smallest correct fix, run the focused verification that fits the touched surface, and commit the change. Every fix receives an exact thread reply; write a tailored reply file when useful, otherwise the driver deterministically composes one from the commit and rationale.
4. If no code change is appropriate because the finding is incorrect, intentional, redundant, or contrary to repository conventions, write a concrete reply to a sibling Markdown file near `${outcome_file_path}` and use `outcome: "replied"`.
5. Use `fixed_and_replied` when both a committed fix and a tailored explanatory reply are required. A plain `fixed` outcome still causes the driver to post and read back a deterministic fix reply before waiting for CodeRabbit.
6. Use `deferred` only when a concrete caller-owned decision prevents safe resolution. Never ignore or silently reject a finding.
7. Do not push, trigger CodeRabbit, post GitHub replies, or process any other CodeRabbit conversation.

## Required Output

Write exactly one JSON object to `${outcome_file_path}` with this shape:

```json
{
  "comment_id": ${comment_id},
  "outcome": "fixed | replied | fixed_and_replied | deferred",
  "commit_sha": "sha-or-null",
  "reply_body_file": "path-or-null",
  "rationale": "short justification",
  "files_touched": ["path"]
}
```

Use JSON `null`, not the string `"null"`, when `commit_sha` or `reply_body_file` is absent.
