# `pr-batch-poller` — batched GitHub PR status query

**Status: skeleton. Not yet implemented.**

## One concern

Given a list of GitHub PR identifiers (`<owner>/<repo>#<num>`), return the merged status, last-comment timestamp, and last-event timestamp for **all of them** in a small number of API calls (ideally one). The caller can then decide which PRs need action, without paying the cost of one polling call per PR.

## Anti-scope

- The poller does NOT decide what to do with the results. It returns data.
- The poller does NOT schedule itself. (`scheduler` does that.)
- The poller does NOT wake WU sessions. (`wu-session-resumer` does that.)
- The poller does NOT mutate PR state (no merging, no commenting, no labeling). It is read-only.
- The poller does NOT subscribe to webhooks. (Webhook-driven wakeup is a separate possibility, not a degradation of this tool.)

## Inputs (proposed)

- `--prs <list>` — comma-separated `<owner>/<repo>#<num>`. Or `--prs-file <path>` reading newline-separated entries.
- `--since <iso8601>` — only return events newer than this timestamp. Used to skip "no change since last poll" cases without re-emitting the full state.
- `--format <json|jsonl|table>` — output format.

## Outputs (proposed shape, JSONL)

```json
{"pr": "nestharus/agent-runner#123", "merged": true,  "merged_at": "2026-05-04T12:34:56Z", "last_event_at": "...", "new_comments_since": 0}
{"pr": "nestharus/agent-runner#124", "merged": false, "merged_at": null,                    "last_event_at": "...", "new_comments_since": 3}
{"pr": "nestharus/oulipoly-x#9",     "merged": false, "merged_at": null,                    "last_event_at": "...", "new_comments_since": 0}
```

## Batching strategy

GitHub's REST API does not have a "GET status of N PRs" endpoint. The batching is done via the GraphQL API: a single GraphQL query can fetch up to ~100 PRs in one request via aliased `repository(...) { pullRequest(number: ...) { ... } }` blocks or via a `search()` query with the issue list.

Implementation plan:

1. Group PRs by owner/repo. (One repo → one node block in the query.)
2. Build a single GraphQL query with one aliased PR field per PR.
3. Execute via `gh api graphql -f query=…` (no extra credentials beyond the user's gh token).
4. Parse the response and emit one JSONL line per PR.

A single query handles 50+ PRs comfortably. If the input exceeds GitHub's per-query limits, the poller chunks at the GraphQL boundary, not at the per-PR boundary.

## Used by

- (planned) `~/ai/agents/wu-session-resumer.md` — given a list of in-flight WU sessions' PR URLs, the resumer asks the poller for batched status, then wakes only the sessions whose PRs changed.
- Other workflows that need bulk PR status (e.g. release coordinators, multi-PR campaigns) are obvious future consumers.

## TODO

- Implement.
- Decide whether to use `gh api graphql` or directly hit the GraphQL endpoint with the user's token.
- Define a stable JSONL schema and version it.
- Decide error semantics: one PR returns 404 — does the whole batch fail or does that PR get a `{"pr":..., "error":"not_found"}` line?
- Decide if `--since` filtering happens server-side (via a `updated_at >= since` filter on the GraphQL search) or client-side (request all, filter locally).
