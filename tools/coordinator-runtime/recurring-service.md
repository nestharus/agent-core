# Recurring workflow windows

`window_service` is an explicit prospective mode for a **new journal**. Existing
configuration, grants, journals and service selection are never changed by this
source. It is separate from `finite_service` terminal lifetime reservations.

```json
{
  "window_service": {
    "tasks": ["work-proposer", "work-integrator", "branch-proposer", "branch-integrator", "reviews-proposer", "reviews-integrator", "qa-execution", "qa-cleanup"],
    "max_new_inputs": 40,
    "batch_size": 8,
    "max_decisions": 16
  },
  "alert_cadences": {
    "root-capacity": 300,
    "stale-branch-worktree": 3600,
    "acceptance-request": 86400
  }
}
```

These are fictional software sizing examples, not rollout quotas or observed
arrival rates. `tasks` must include every configured task. Role routes, including
Branch/Reviews/QA returns to Work, remain intact. Existing package admission,
scope narrowing, owner execution/return, response classification, artifact custody,
effect reconciliation, publication and consumer settlement still apply. This mode
does not assume the response graph becomes terminal within a fixed attempt count.

`limits.max_events/max_jobs/max_attempts/max_outboxes` bound **allocations in the
current window**, including internal response and owner-return allocations. They
do not bound historical retained rows in this mode. `max_new_inputs` separately
limits external intake. Input/recovery owner decisions use `max_decisions` per
window instead of exhausting a lifetime correction count. Automatic diagnosis
continues to be one bounded attempt; further choice belongs to the real owner.
All charges and source writes share the SQLite transaction, so failed allocation
or downstream insertion rolls the charge back. Outbox idempotency keys charge once.
Batch member records retain each original event, source owner and package; a batch
does not borrow a terminal account from its first member.

Integrators remain one per coordinator, proposers retain configured parallelism,
and QA uses at most five separate execution jobs, then one cleanup job. Batches
are capped by `batch_size`; remaining queue members stay pending for the next
window. QA executions and cleanup do not overlap in recurring mode. Advancing an
allocation window does not free any occupied execution slot.

At pressure the source/cursor/queue remains intact. Actual Work uses the existing
authenticated owner CLI to read `window-basis`, then `advance-window --receipt`.
The receipt has exactly `basis`, `target`, `reason`, `evidence`, and `custody`.
`custody` maps every enrolled role to `{owner,evidence}` attributing continuing
original responsibilities. Current Work ownership and Board authority are checked
by the CLI. The transaction rechecks a streaming digest of the **entire retained
journal**, including BLOB custody, all holds and prior windows. A stale decision
refuses. The new allocation window preserves every original and pending duty;
it supplies no processing, authority transfer, effect waiver or all-clear claim.
Work's custody statement is an accountable assertion, not authentication of other
owners or invention of their grants. There is no automatic ACK/age renewal.

Physical `max_bytes/max_files` remain cumulative, including journal/WAL, artifact
and reserved worker capture bytes. Existing custody and processing+24h/all-hold
retention rules still govern eligibility. Retained historical source eventually
needs lawful owner conservation/retention handling and adequate physical storage;
an allocation window does not reclaim a platform store or promise infinite service.
No historical journal retrofit or archive migration is implemented here.

## Recurring owner workers

The normal `serve` dispatcher constructs the process broker. Recurring mode uses
this broker instead of calling synchronous custodian callbacks inside a tick.
Register an existing genuinely authorized adapter per role with
`custodian_service: {ROLE: {argv:[ABSOLUTE_EXECUTABLE,...], authority:TEXT,
timeout_seconds:NUMBER}}`. The maximum visit is 30 seconds, with at most one
active owned worker per role in this dispatcher. Registration is source wiring,
not proof that an adapter or genuine authority exists. No worker is supplied or
activated by this example. Missing workers remain visible owner-qualified gaps.

Each worker receives one bounded JSON request on stdin: `visit`, `owner`, `role`,
`occurrence`, exact `basis`, alert/outbox beforeimages, declared `authority` and
`obligation`. Existing Board authority is checked before preparation and launch.
The broker retains the request before spawning, then its actual PID before any
wait/read. It reserves bounded capture space and collects the original numeric
END separately from pipe completion. Timeout/oversize/invalid output is UNKNOWN,
retains bounded original stdout/stderr and intent, and is never automatically
replayed, including after restart. A child-held pipe is separately UNKNOWN.
There is no foreign process wait or kill.

A successful protocol response has exactly `visit`, `owner`, `basis`, `status`,
`effect_state`, `intent_reference`, `result_reference`. References must name the
actual adapter's durable originals. Only `held/not-attempted` allows recurring
no-effect requalification after `recheck_seconds`; `progressed/completed` suppresses
repeat for the same source basis. Unknown earlier visits block automatic replay
for that occurrence even if its source subsequently changes. The actual owner
must independently reconcile original effects; this source adds no unknown-clearing
or retry command. Unrelated occurrences can continue. Each selected role has its own bounded
fixed-frontier sweep. A busy role does not consume its later entries; a launched
visit stops that role's page at the actual occurrence visited. Repeated eligible
held entries therefore yield attention to later entries in a stable finite
population. Different roles retain independent active visits. These in-memory
frontiers restart at the beginning after a controller restart; no infinite-arrival
or universal latency guarantee follows. A separate bounded audit preserves gap
reporting for originals with no delivery linked to a selected role.

The adapter retains responsibility for genuine owner/grants, substantive
processing, current all-hold qualification, source/consumer/control/transport
correlation and durable intent **before** any effect, followed by result custody.
Its protocol answer never stamps processing or deletes rows in the broker. An
adapter using `OwnerAlertCustodian` must use the genuine Board owner interface;
that interface checks processing+24h and every hold. Textual owner IDs and output
references do not authenticate these external facts.

## Alerts and limits

Only observed violations produce occurrences. Per-kind `alert_cadences` supports
the existing 5min/1h/24h monitor duties; map genuine monitor kinds explicitly.
The dispatcher sampling interval must be no slower than the smallest selected
cadence. No monitor/provider input is fabricated by these settings. An unchanged
violation at its due time produces a fresh ID. Under alert-row pressure, bounded
`alert_debt` retains exact IDs, times and payloads. Later representation keeps
those originals and cannot erase missed-cadence/gap evidence. No-violation scans
create no alert. Unobserved historical intervals remain UNKNOWN; the runtime does
not invent violations for them. When exact debt or physical evidence storage is
also exhausted, capture commits the newest observed time, gap/counter update
and a bounded `alert_service.latest` summary before raising `Backpressure`.
The exception carries the same `observation` for the caller's owned handling.
The summary names the custodian, sample time, exact observed due count and scope
digest, and distinguishes exact alerts, exact debt and unavailable due payloads.
It is the newest summary, not an occurrence archive, a missed-population census
or a delivery/processing receipt. `last_observed` is a sample attempt, including
refused representation; per-subject cadence advances only for exact retained
cohorts. Failed samples are throttled by the sampling interval. Repeated later
due attempts can contribute repeated unrepresented counts; the count does not
claim a unique missed population. Prior gap start/scope and all held rows remain.
Partial debt insertion rolls back as a whole. No-violation samples still produce
no alert and do not erase a prior gap. Summary writes use the existing bounded
pressure reserve; disk/SQLite/commit failure can still leave the newest fact
unrecorded and must be retained as a storage/observation uncertainty by the caller.
A successful separate operational-error write is not a substitute for this
committed observation. Summary counters do not discharge the missing duties.

The representative software controls run directly from `tests/test_windows76.py`
with an explicit fresh fixture directory. They use imported production classes,
own SQLite/files and bounded child handles; owners, grants, processing receipts,
model returns and the canonical lock are fictional. They do not exercise providers,
real Board delivery or operating rates. No source-only result establishes rollout
adoption or recovery of an installed service.

The separate lifecycle75 work owns stale prestart disposition and recovery
context. This branch preserves an unstarted reserved integrator and its held
sources across allocation boundaries. It does not add a safe cancellation or
reselection path, compose lifecycle75, or prove that combined service. Publication
remainder's existing one-successor policy also remains; an exhausted remainder
stays with its actual owner rather than becoming an assumed completed campaign.


Targeted custody/pressure controls in `tests/test_pressure78.py` require an
explicit fresh fictional fixture root. They import the affected production
capacity and broker methods and use literal production SQLite schemas, PERSIST
journals with synchronous FULL, fictional budget/authority inputs and tiny
no-effect adapters. The controlled broker retains each original child PID before
waiting and numeric END after collection. These controls retain SQL traces and
before/after images; they are not Store initialization/WAL/crash tests, actual
retirement or live service qualification. Run them in the supplied kernel read-only
`/src` namespace with isolated PID/network/dev/tmp and writable `/fixtures`.
