# `pr-batch-poller` - batched GitHub PR status query

Status: implemented.

## One concern

Given a list of GitHub PR identifiers, return merged status, last conversation-comment timestamp, and last-event timestamp for all of them in a small number of GitHub GraphQL calls. The caller decides what to do with the rows.

## CLI grammar

```text
python3 tools/pr-batch-poller --prs <owner>/<repo>#<num>[,<owner>/<repo>#<num>...] [--since <iso8601>] [--format jsonl|json|table]
python3 tools/pr-batch-poller --prs-file <path>                                      [--since <iso8601>] [--format jsonl|json|table]
```

`--prs` and `--prs-file` are mutually exclusive, and exactly one is required. `--format` defaults to `jsonl`.

## PR identifier grammar and input rules

Identifiers use this grammar:

```text
^(?P<owner>[A-Za-z0-9][A-Za-z0-9-]*)/(?P<repo>[A-Za-z0-9._-]+)#(?P<number>[1-9][0-9]*)$
```

Owner and repository spelling is case-preserving. The PR number is a positive integer with no leading zeros: `acme/widget#1` is accepted; `acme/widget#0` and `acme/widget#001` are rejected as invalid input.

`--prs` splits on commas, trims whitespace around each token, and rejects empty tokens. `--prs-file` strips each line, ignores blank lines, and has no comment syntax because `#` is part of the PR identifier. Duplicate identifiers are removed after canonicalization while preserving first-seen order.

## `--since` semantics

`--since` accepts only offset-aware ISO-8601 timestamps. `Z` is accepted as UTC. Naive timestamps are rejected before GitHub is called.

Filtering is client-side. The tool still fetches each requested PR by alias, then suppresses unchanged success rows whose `last_event_at <= since`. Error rows are always retained. Conversation-comment counts use fetched `PullRequest.comments.nodes[].updatedAt` values greater than `since`.

## Output formats and format stability

`jsonl` emits one JSON object per line with a trailing newline. `json` emits one JSON array containing the same row objects. These two formats are machine-readable contracts. `table` is human-only and does not promise fixed spacing or columns beyond showing PR identity and status.

## Schema version rule

Every row includes `schema_version: 1`. Future incompatible changes must increment the version. Additive field changes must be documented with the version they entered.

## Success row schema

A success row has `row_type: "pr_status"` and `error: null`. All fields are present:

| Field | Meaning |
|---|---|
| `schema_version` | Current integer schema version, `1`. |
| `row_type` | `"pr_status"`. |
| `pr` | Canonical `<owner>/<repo>#<num>`. |
| `owner` | Parsed owner. |
| `repo` | Parsed repository. |
| `number` | Positive PR number. |
| `pr_url` | GitHub PR URL. |
| `state` | GitHub PR state (`OPEN`, `CLOSED`, or `MERGED`). |
| `merged` | GitHub merged flag. |
| `merged_at` | Merge timestamp, or null. |
| `merge_sha` | Full merge commit OID, or null. |
| `head_sha` | Full PR head OID, or null. |
| `head_ref_name` | PR head branch name, or null. |
| `base_ref_name` | Base branch name, or null. |
| `base_ref_oid` | Base ref OID from GitHub, or null. |
| `updated_at` | GitHub `pullRequest.updatedAt`. |
| `last_event_at` | Same as `updated_at` for this tool. |
| `last_comment_at` | Latest fetched conversation-comment `updatedAt`, or null. |
| `new_comments_since` | Null when `--since` is omitted; otherwise a count of fetched conversation comments newer than `since`. |
| `error` | Null for success rows. |

Null means unavailable or not applicable. A missing field is a schema violation.

## Error row schema

An error row has `row_type: "error"` and the same identity fields: `schema_version`, `pr`, `owner`, `repo`, and `number`.

All success status fields are also present. They are null when no trusted GitHub value exists. For `comment_window_exceeded`, trusted PR status fields may be populated, while `new_comments_since` remains null because the exact count is not trustworthy.

`error` is an object with `code` and `message` strings.

## Error codes

- `repo_not_found_or_forbidden` - the repository alias is null in the GraphQL response.
- `pr_not_found_or_forbidden` - the PR alias is null under a present repository.
- `graphql_partial_error` - a GraphQL error path maps to one requested PR alias.
- `comment_window_exceeded` - `--since` was supplied, the fetched 100 conversation comments are all newer than `since`, and GitHub reports another comments page.

Unmapped GraphQL errors are fatal because the batch cannot be trusted.

## Chunk size and GraphQL batching strategy

The default chunk size is 50 PRs. Each chunk builds deterministic aliases around:

```graphql
repository(owner: "...", name: "...") {
  pullRequest(number: ...) {
    number
    url
    state
    merged
    mergedAt
    mergeCommit { oid }
    headRefName
    headRefOid
    baseRefName
    baseRefOid
    updatedAt
    comments(first: 100, orderBy: {field: UPDATED_AT, direction: DESC}) {
      nodes { updatedAt }
      pageInfo { hasNextPage }
    }
  }
}
```

The tool calls `gh api graphql -f query=<query>` through one subprocess boundary. Chunking happens at the GraphQL request boundary, not by making one request per PR.

## Resumer-handoff shape

A merged success row supplies the exact PR-derived fields needed by the `wu-session-wake` composition root: `pr_url`, `state`, `merged`, full `merge_sha`, full `head_sha`, `head_ref_name` as branch name, `base_ref_name`, `base_ref_oid`, and `merged_at`. That root must reject null or abbreviated head/merge identity for a merged row. The poller is status-only and never dispatches a resumer.

`wu-session-wake` reads only the exact `planning_root/sessions.active-wake.json` selected by its caller: direct composition supplies top-level project planning tree `P`, while feature composition supplies that feature's `F/routes`. It does not recursively discover or aggregate indexes. The wake root joins `pr_url` to session `draft_pr_url`, requires `head_ref_name == branch`, full `head_sha == draft_pr_head_sha`, and `base_ref_name == base_branch`, then dispatches one exact joined row containing `ticket_id`, `session_manifest_path`, and optional `pre_merge_base_sha` to one `wu-session-resumer`. Historical `sessions.index.json` rows are never poller input. `base_ref_oid` is current base-status evidence, not `pre_merge_base_sha`; specifically, it is the current base OID observed when the poll ran. It is not automatically the historical immediate pre-merge SHA and must never be copied into `pre_merge_base_sha`. When the session has no pre-merge value because the PR merged manually or externally, `wu-session-resumer` independently re-queries the exact PR and derives/validates the immediate pre-merge parent from trusted merge-method and commit-parent evidence.

The active handoff has no retired trunk-specific pre-merge field and no legacy alias fallback. OPEN persisted sessions legitimately carry `pre_merge_base_sha: null`; the value becomes required only immediately before an automated merge or while processing a merged wake.

## Exit codes and stderr/stdout contract

- `0` - usable batch response; per-PR failures, if any, are emitted as error rows.
- `1` - fatal runtime or query failure. No data rows are emitted.
- `2` - fatal CLI or input error. No data rows are emitted.

Fatal diagnostics are concise and written to stderr as `pr-batch-poller: <message>`. Machine rows are written only to stdout.

## Anti-scope

Not webhook-driven; not session-aware; not the merge-detection wake mechanism.

The tool does not schedule itself, decide actions, mutate PR state, discover WU sessions, read session manifests, or call the resumer.

## Used by

- A scheduler or manual caller invokes `wu-session-wake`; it does not route directly to this poller/resumer pair.
- `wu-session-wake` invokes the poller, inspects JSONL or JSON status rows, joins them to canonical sessions, and owns fanout/process proof.
- `wu-session-resumer` receives one exact already-joined merge row from `wu-session-wake`; it does not poll.
