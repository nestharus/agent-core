# Public phase and boundary observations

This source adds diagnostics for a later separately authorized Work-owned run.
It establishes no service restoration, historical cause or rollout qualification.
The current configuration/release must still pass its original checks; changing
source does not update a capability or authorize a provider retry.

Normal `processing-service-control` output includes `client_observations`. Its
owner is `control-client`: config loading, read-only Store opening, current
configuration/release/source checks and Board/actor preparation, socket connection, send/drain, reply read
and socket close. A failure before connection has no connection/reply entry.
These observations belong to the client invocation. They are not service timing.

An authorized reply from the existing original endpoint also includes
`service_observations`, with owner `service` and the original's `controller` in
the enclosing reply. Final original-return emission carries the same service
record alongside its existing collector. The service records startup authority,
all nine existing tick phases including success-error clearing, capacity, delivery
and alerts, plus nested Board,
retained-source and current configuration/release/implementation checks. It
records control read, selected operation and write/drain. Failed-phase error
reporting has a separate span whose parent is the failed phase. Dispatcher/alert
error accounting also has fixed spans. A reply's snapshot
precedes its own write/drain; a later snapshot can include that write. Direct
control callers without an owning record receive no invented client record.

Each record has at most 64 recent completions and 64 active entries, plus totals
for a fixed source-defined label set. Sequence and parent numbers relate nested
observations within that one record; a parent can have expired or been evicted.
They identify an observed execution relationship, not a durable job/capability.
Existing controller and attempt attribution remains authoritative. Active entries
mean inflight, not successful. Totals count calls, failures, cancellations and
inclusive elapsed/max milliseconds. Nested durations overlap and must not be
summed as independent elapsed time. Source-file and retained-event/outbox counts
come only from lists the existing checks already acquire. Failed checks may not
reach those counts. No additional body, SQL or filesystem inventory is acquired.

Visibility uses a 300-second tumbling window, expired lazily on observation or
snapshot without a background task. Expiry clears summaries/recent/active entries;
overlapping active entries become omitted, not completed. `dropped` counts omitted
active observations. The most recent 64 completions evict oldest entries. All
numbers saturate at 2^53-1; sequence exhaustion omits subsequent observations.
The record ends with its owning invocation; nothing is persisted in a new table
or file. Lazy expiry is not a physical reclamation claim. Snapshots may be absent
on failure before a reply/final emission; a blocked loop cannot emit a snapshot
until it resumes. No watchdog, thread, executor or second Store owner is added.

Each owned Peer retains at most 64 method-progress entries until its existing
owned lifecycle ends. Unknown method names project to `other`. `sequence` is
local to that Peer and remains enclosed by the existing attempt detail. When a
record admits the method span, `observation_sequence` joins that attempt-local
progress to the owning record's method sequence. An absent join is unobserved;
parents/method entries can expire or be evicted before collection.
`protocol_progress_dropped` counts history evictions;
`protocol_correlation_dropped` counts omitted timing joins above 64 concurrent
calls. Those telemetry bounds do not change pending RPCs, admission or effects.

RPC progress distinguishes:

- `budget_ms`: unchanged local budget for send/drain plus response.
- `exchange_entered_ms`: task entry relative to budget setup.
- `send_drain_ms`: successful send/drain completion relative to setup. Its absence
  leaves that boundary incomplete; it does not establish that no bytes were sent.
- `correlated_reply_ms`: reader decoded a matching live response, relative to
  setup. It does not measure remote processing or arrival at the kernel socket.
- `cancellation_delivered_ms`: cancellation reached the exchange. External
  cancellation request time is unknown unless the caller separately observes it.
- `boundary`: last sending/awaiting-response/response state before failure.
- `budget_overrun_ms`: excess elapsed when TimeoutError is collected. Timer
  scheduling, synchronous blocking and cancellation/unwind may contribute; this
  number alone establishes none of their causes.

Final RPC state retains success, timeout or failure; cancellation remains a
failed call with constant `CancelledError`. Pending correlations are removed on
all returns. A late unmatched reply cannot turn a timeout into success. Sent
requests remain effect-uncertain, with no replay or rejected-root inference.
Public labels, enumerated states and bounded numbers are the complete additional
projection. Arguments, error text/types outside fixed enums, responses, prompts,
SQL values, stacks, locals, paths and account data are excluded.

Focused checks run `test_observability375.Observability`,
`test_coordination366.Coordination` and selected startup/control346 checks in a
positive mount namespace: tracked public source read-only, fictional fixture
files writable, network off, no actual Git/profile/runtime/capture mounts. The
fixture uses actual retained/current guards, fictional SQLite source populations,
explicit acquisition delays, the real tick with substituted phase bodies, fake
stdio pipes and the existing Unix endpoint. CLI fixtures substitute config and
actor/membership authority and use an independent read-only control client.
These seams do not prove real authority, production load, provider behavior or
actual371's cause. Known unrelated QA/Reviews errors and destructor warnings
remain inherited, not repaired or made green by these checks.
