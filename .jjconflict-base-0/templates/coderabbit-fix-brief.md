# CodeRabbit Comment Fix Brief

You are addressing exactly one CodeRabbit in-diff review comment.

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
2. Read `${comment_file_path}` and inspect the referenced code.
3. Decide whether the CodeRabbit comment provided real review value.
4. If the comment is valid and a code change is appropriate, make the smallest correct fix, run the focused verification that fits the touched surface, and commit the change.
5. If the comment is better answered with a reply, write the reply body to a sibling Markdown file near `${outcome_file_path}` and reference that path in the JSON outcome.
6. If the comment is noise, intentional, redundant, or not worth acting on, do not edit files. Mark `review_provided_value: false` and use `outcome: "rejected"` with a concise rationale.
7. Do not push, trigger CodeRabbit, post GitHub replies, or process any other CodeRabbit comment.

## Required Output

Write exactly one JSON object to `${outcome_file_path}` with this shape:

```json
{
  "comment_id": ${comment_id},
  "outcome": "fixed | replied | fixed_and_replied | rejected | deferred",
  "commit_sha": "sha-or-null",
  "reply_body_file": "path-or-null",
  "rationale": "short justification",
  "files_touched": ["path"],
  "review_provided_value": true
}
```

Use JSON `null`, not the string `"null"`, when `commit_sha` or `reply_body_file` is absent.
