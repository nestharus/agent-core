---
workflow:
  id: tickets-first-review
  status: retired
retired_workflow:
  retired_by: ACR-275
  active_dispatch_contract: removed
  replacement: "routine draft PR creation plus ticket-prefixed branch naming"
---
# Tickets-First Review Workflow

This workflow is retired. It no longer inserts a human local-review gate before draft PR creation.

## Declared roles

This file's classifications under `~/ai/conventions/code-quality.md` § Declared roles:

- `orchestration` — Records that the former tickets-first lifecycle no longer sequences active review work.
- `validator` — Documents removed signoff semantics so they are not reintroduced as an implementation-pipeline gate.
- `formatter` — Points naming and branch-reference conventions back to their active home.

## Retirement Note

Branch and ticket naming lives in `~/ai/conventions/git.md`.

Routine draft PR creation plus ticket-prefixed branch naming replace the former pre-draft local review.

The active dispatch contract is REMOVED.

The active branch-as-review-unit lifecycle is REMOVED.

The reviewer signoff before PR creation is REMOVED.

The retrofit references are REMOVED.
