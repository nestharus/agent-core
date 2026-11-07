# Explicit managed service wake

The existing service can opt into identity-only postcommit datagram hints. The
hint sets its dispatcher's coalesced event and runs ordinary guarded intake.
Source/configuration/capability, role, prospective cursor and admission checks
still decide acquisition; collected fresh Luna-low classification plus durable
queue responsibility still precede the delegated receipt. A hint is never an
ACK, native pickup, semantic response, task authority or processing completion.

## Selection and lifetime

Genuine Work can include `wake` in its normal `processing-select` service policy:

```json
{
  "protocol": "managed-hint-v1",
  "roles": ["Work", "Branch", "Reviews", "QA"],
  "until": 1060.0
}
```

The timestamp above is fictional. Supply the **same actual finite timestamp** as
`service.admission.until`, within one hour at selection. Each role must already
belong to the exact selected processing basis and unchanged configuration. The
ordinary processing selection authenticates the existing Work grantor. Each
recipient must still have active managed membership and its original bound
software grant. No wake policy means no endpoint binding, including after code
adoption. This policy grants no new intake, role, pool membership or lifecycle.

The original service binds one exclusive Linux abstract datagram address per
selected board inode and managed recipient, in `message-board-managed-v1`.
This is separate from native `message-board-watch-v1` addresses. A conflicting
binding refuses startup; no unlink, socket takeover, new ManagedOwner, journal
registration, migration or durable subscription is attempted. The kernel handles
belong to this service incarnation; closing only those handles ends the binding.
All endpoints bind before the initial finite scan. Revoked/currentness failures
close the bridge at its next guarded intake check; the finite deadline closes it
via a software timer. Existing admission guards stop new acquisition at that
same deadline, retaining original work and collection/recovery duties.

`active_listener.signal_post` sends the existing board-identity packet to native
watchers and, only for notice rows whose recorded route is `managed`, the separate
managed address for that exact recipient. No subscription lookup is necessary.
Sends are nonblocking; absent/full endpoints lose only the hint. Directed plain
posts, lost hints, previously owed work and native/queue replies addressed to the
service actor retain finite timer recovery through `recheck_seconds`.

The dispatcher clears the coalesced event **before** scanning, retaining a hint
that races with the scan. A full 100-input page requests another fair phase pass;
other roles, delivery and event-loop readers receive their normal turns. Model
completion also wakes the dispatcher. Idle waiting and recovery scans are
software only. Existing synchronous phase work still bounds response latency;
there is no semantic-response deadline guarantee here.

## Compatible release paths

Adopt `coordinator_runtime/service.py`, `service_wake.py`, `dispatcher.py` and
`tools/message-board/active_listener.py` together from this commit. Select the
current configuration/release through the existing validation path; preserve
all existing tasks, four roles, point bindings, duties, holds and collectors.
The release mechanism already pins `active_listener.py` and all runtime modules.
It does not install an optional wake policy automatically.

The investigated producer path `/home/nes/ai/tools/message-board` and configured
consumer library
`/home/nes/projects/ai/worktrees/WORK-48847-runtime-cutover-repair324/tools/message-board`
are different installations. Their original `active_listener.py` bytes match the
released base. Both need the exact new helper bytes if those paths remain
selected. Preserve unrelated `board_store.py`, `queue_transport.py` and
`active_transport.py` changes: the producer has newer versions than the base.
Only changing the inactive helper in a release checkout does not qualify actual
producer wake. Alternatively, owners may genuinely select a coherent release
library for both producers and consumers. Neither operation occurs in this patch.

`service` status reports bounded protocol/state/roles/deadline/observed-hint
scalars. Existing phase diagnostics and receipt/processing records retain their
separate meanings. A positive hint count does not prove end-to-end delivery.

## Isolated checks

Run only `tests/test_managed_wake658.py` with fresh retained `/fixtures`, the
coordinator-runtime and message-board trees plus the exact public execution-pool
module mounted read-only under `/source/tools`, and no host profile, board,
journal, native connection or network mounted. The external compatibility check
additionally mounts the three explicitly selected public producer files at
`/public`: `board_store.py`, `queue_transport.py`, `active_transport.py`. It uses
the patched listener and a declared no-op retention-metadata callback, without
reading installed retention code. This qualifies the postcommit hint call
contract, not retention or producer/native transport operation.

Tests use production Work selection, board APIs, intake, attempts, queue and
receipts. Consent comes from fictional fixture principals and model outcomes
are deterministic doubles. The complete service-loop test excludes task
execution, cleanup and external custodian phases, retaining original lifecycle
records. Fixture exits are not a live service release or semantic response.
