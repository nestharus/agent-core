# Bounded alert conservation

The runtime retains each newly observed due alert before trying to allocate its
outbox. Full outboxes leave the exact original alert ID, timestamp and payload
pending; bounded passes allocate those deliveries later. Unchanged violations
continue to produce distinct occurrences at the configured interval. Cadence is
journaled across process reconstruction. This does not replay historical alerts.

If a whole current cohort cannot fit the existing alert or byte limit, it rolls
back and `alert_service` records an explicit unmet interval, observed scope hash,
count and actual enrolled alert-role custodian. Later success does not clear that
gap. Unobserved intervals have unknown historical populations; current observations
cannot reconstruct them. This is an unmet obligation, not successful reporting.
`status` includes this record and the pending alert-delivery count, but its existing
execution-pool status operation still has its documented effects. The journal
record itself can be queried by an authorized existing owner without that probe.

Dispatcher phases retain their own failures and continue independent already-owed
receipt, reconciliation and delivery paths. This is not permission for new native
delegation, transport retries of accepted/unknown/inflight intents, or model
launch without existing authorization. Ordinary admission withholds 4096 bytes
within the current byte limit for the small pressure record. Sampled accounting
and this reserve are not a physical filesystem quota, write reservation or disk
failure guarantee.

## Continuing-service notification consumption

A current continuing processing selection groups up to 32 exact pending
occurrences per addressed notification, normally within 32 KiB. A single larger
occurrence uses its full envelope up to 192 KiB. Larger sources stay exact and
pending with an explicit service gap; nothing is clipped. Original occurrence
IDs/times/payloads and debt remain separate, linked by `alert_delivery_members`.
Only occurrences recorded at birth under the current processing capability and
within the current configuration boundary enter new notifications. Historical
alerts and exact debt have no backfilled origin or new-capability reattribution;
they retain their original custody;
new due occurrences of their still-real causes continue normally. No cause,
including a delayed notification's own ACK/backlog, is exempt from observation.
Zero violations produce no new occurrence or notification.

The actual receiving intent still authenticates source/delivery/recipient/grants,
managed transport and uncertainty. The received notification has control routes,
not business-task authority. One fresh Luna LOW classification and durable queue
precede ACK. A separately collected actual control worker can return
`mode=notification` only after reading every full occurrence; its evidence binds
the full occurrence digest. That receipt finishes only this notification queue,
without reclassification or another Work proposer child. Underlying causes,
original native/collector ownership, effects, uncertainty and holds remain open
with their original custodians. An interpretation that needs an actual decision
retains the ordinary control/Work-return path, with its complete obligations.
PARTIAL, missing coverage, unknown worker/tool/END, stale source or transport
uncertainty cannot become processing. The whole consumer frontier still gates
all represented notification processing timestamps and addressed settlement.

Notification events, attempts, decisions, bytes and outboxes remain charged to
the finite current source allocation. Upstream pause does not exempt these owed
controls from those limits. No refill, counter refund or live throughput promise
is implied. Grouped notification retirement is not covered by the existing
standalone-alert or disposable-episode APIs: they refuse rather than detach a
member's source/consumer custody. Such cohorts remain held pending a separately
qualified whole-cohort retirement capability and all original holds. The finite
operating envelope must include this retained growth.

## Narrow alert retirement

Automatic cleanup retains alerts: processing timestamps alone cannot qualify all
holds. `alert-retirement-basis OCCURRENCE` returns an exact current source digest,
not eligibility. `retire-alert ROLE OCCURRENCE --receipt /absolute/owned/receipt.json`
is an explicit genuine-owner operation. It permits only standalone alert outboxes
whose source owner and addressed consumer are the same actual enrolled identity.
Other deliveries, job/event outboxes and another custodian's duties remain held.

The receipt has `basis`, `qualified_at`, `evidence`, and `holds`. `qualified_at` is
the finite current qualification time, at most 60 seconds old. `evidence` is a
bounded substantive explanation of actual custodian qualification. `holds` must
explicitly contain exactly these keys, each an empty list: source, consumer,
control, transport, publication, resource, recovery, effect, privacy. Missing or
nonempty categories refuse. The actual owner must obtain every applicable
custodian's evidence; an empty object or this format is not such evidence.

The existing Board membership/current runtime and outgoing grant must still
match. The exact posted immutable source and current recipient/processing/
settlement/control/transport receipt must match the runtime. Queue transport needs
exact processing correlation. Every processing frontier must be no earlier than
creation and at least 24 hours old. A stale basis, newer hold, active scoped
error, changed receipt, foreign actor, ACK, model DONE or process END refuses.

Retirement removes only the exact runtime alert, its linked outbox and scheduling
hint in one SQLite transaction. Underlying causes, original duties, Board/native
records and platform stores remain. The caller retains its exact input receipt
and returned retirement record under all evidence and consumer holds. Lost CLI
output after a committed retirement is an unknown publication outcome, not a
reason to replay it. This is cooperative Board fencing and a runtime transaction,
not multi-store atomicity or noncooperating-writer CAS. SQLite page reuse is not
physical platform-store reclamation.

## Operating envelope and unsupported capability

Continuing notification groups use the existing `retirement-basis EVENT` and
`retire-episode EVENT --receipt PATH` path. The root is the original linked
consumer event. Its transitive event/job/delivery cohort now includes every
`alert_delivery_members` occurrence, full stored payload/hash, exact represented
debt and consumer frontier. A grouped receipt additionally supplies `occurrences`,
using the same exact hash/custodian/evidence/disposition format as `sources` and
`results`. Every member needs conservation at its original source or actual
producer-owned disposability. Partial membership, another delivery sharing an
occurrence, unknown origin, changed source, stale qualification or any hold
refuses the whole transaction. Standalone alert retirement still refuses groups.

This path requires the same continuing issuer/capability, genuine original
receiving/processing/control/settlement evidence, retired queue/artifact material,
whole downstream completion plus 24 hours, and separately completed shared
custody conservation. It removes only qualified local rows, including represented
debt and membership. It does not settle the violation subjects. The external
custodians still own the truth of their all-hold/conservation qualification;
no ACK, DONE, enqueue time or numeric END supplies it.

Exact debt materializes atomically by observed time and original capability.
Ambiguous same-time legacy debt is conservatively joined; no history is invented.
When the alert representation cannot fit the entire cohort, its exact debt stays
pending while existing deliveries can progress. Exhaustion of both admitted
representations raises Backpressure after committing the owner-held coverage
gap. The notification delivery page remains bounded. A constant-size alert row
high-water mark survives reclamation, retaining configuration frontiers without
reclassifying old alerts/debt. Event and job logical sequences also survive;
retirement refunds no original input/window/attempt/allocation charges.

These source paths cover grouped notifications and their linked control/task/
response queues, existing disposable job/event episodes, and separately qualified
standalone alerts with represented debt. Canonical role-owned artifacts, unresolved
ordinary resources/effects, recovery, foreign/shared stores and unqualified old
episodes remain held. There is no universal queued-item cleanup or autonomous
all-custodian qualification claim. Source fixtures with synthetic shared-custody
qualification cannot establish actual shared retirement or real elapsed 24 hours.

Any service commitment needs a bounded due population, all competing producers,
processing/hold duration, retirement throughput, outage length and observation
horizon. Required runtime outbox count is retained history plus new outgoing
duties minus only eligible completed retirements. Alert, byte and file bounds
apply simultaneously. No finite store supports unlimited arrivals or indefinitely
held distinct recurrences.

This capability supplies durable pending alerts, explicit unmet reporting,
independent progress, and a narrow genuine-owner retirement interface. It does
not supply complete downstream-obligation reservation for arbitrary task graphs,
automatic qualification from every external custodian, a background owner acting
for the consumer, general outbox retirement, or a lifecycle for foreign Board/
native storage. A sustained whole-coordinator guarantee therefore still requires
those actual bounded operands and any necessary separately authorized capability.
An explicit owner-qualified retirement loop used in a software fixture does not
establish that a real autonomous owner/consumer service exists.

No journal/config/grant migration or installed-service operation follows from
these source interfaces. Historical missing traces, prior unknown effects and
all pending duties remain with their actual custodians. Independent Source,
different Frame and actual Work must receive the source consequences before any
adoption.
