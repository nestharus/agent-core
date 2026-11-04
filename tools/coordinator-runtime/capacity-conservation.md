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
