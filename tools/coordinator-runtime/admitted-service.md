# Terminal admission and recurring custodian progress

This is a partial source capability for a finite service envelope. It does not
qualify a deployment, prove actual processing, or restore the routing service.

`finite_service={"tasks":[...],"max_admitted":N}` selects existing configured
Work, Branch, Reviews and QA terminal tasks. N is 1–1000, not an increased row
limit. Tasks must be non-batched, no-effect, non-owner execution, with no response
routes, software handoff routes, routine publication, ordinary effects or package
scope expansion. Other classes refuse before new intake/cursor advancement.
Existing responsibilities outside this prospective selection remain conserved.
An unaccounted pending original or active legacy job blocks prospective expansion;
its original rows and actual custodian remain available for owed progress.

Each external input reserves its whole conservative downstream **count** tail in
the same transaction as intake. With C equal to the existing owner-correction
limit (default 4), the plan reserves:

| Resource | Credits per admitted input |
| --- | --- |
| Task attempts | A = C + 2, including initial and bounded recovery/remaining work |
| Recovery diagnoses | C + 1 |
| Outboxes | O = 18A (16 handoffs, one owner question, one owner report per attempt) |
| Events | E = 1 + O, allowing each monotonic partial outgoing plan its own classification |
| Attempts total | (C + 2)E + A + C + 1, including classification and owner input decisions |
| Jobs | 1 (integrator batches excluded) |

At default C=4 these totals are 109 events, 665 attempts, 108 outboxes and one
job. Count admission requires current rows + all unspent credits + the new full
plan to fit the existing configured caps. Allocating an event, job, attempt or
outbox charges its original account atomically; rollback returns its credit.
Unowned producers cannot consume reserved count capacity. Already-owed duties
keep their account even when processed or old; there is no timestamp release.
The original configured slot, classification and correction fences still apply.

This is a finite lifetime admission population, not indefinite task throughput.
Accounts are retained. Alerts separately use the existing cadence/caps and
standalone same-owner lifecycle. A sustained operating premise must include N,
the complete tail above, all existing/competing rows, alert population/rate,
processing rate, retention + qualification delay, outage horizon and hold duration.
Indefinite arrivals/holds cannot fit finite storage. These operands are not
measured by this feature.

No byte/file reservation or complete physical-resource proof follows from count
credits. Existing byte/file fences still refuse effects. Model capture, artifacts,
SQLite/WAL amplification, external controls, consumer/transport storage and
qualification output need their actual bounded resources and custodians. A failed
resource operation retains the original source and remaining credits; credits do
not promise that every admitted duty is finishable through total storage failure.
This remains a concrete gap for a full D1 operating claim.

`Dispatcher(..., custodians={role: OwnerAlertCustodian(...)})` adds recurring
qualification/retirement visits to the existing dispatcher tick. Persistent
fixed-frontier pages visit at most 16 occurrences per pass; held prefixes do not
starve the rest of that frontier. Reconstruction resumes scheduling hints, never
infers processing. The ordinary delivery pump still owns delivery/consumer/control
progress. The custodian does not manufacture a processing receipt.

An actual same source/consumer owner supplies a qualifier and durable original
evidence sink. Before a possible retirement, the adapter retains the exact alert,
outbox, current basis and custodian assertion. It invokes the existing
`Board.retire_alert`, retaining its current identity/grant/recipient/transport
checks. Actual processing+24h, fresh source basis, and every source, consumer,
control, transport, publication, resource, recovery, effect and privacy hold remain
mandatory. The result goes to the original sink. A failed result publication
leaves the retained intent with its custodian; no blind replay, foreign deletion,
grant creation, identity substitution or global hold census is introduced.

The default service has no registered qualifier. It therefore conserves rows and
records the precise missing-custodian gap rather than retiring them. This feature
does not provide actual owner authority or an all-custodian qualifier, nor wire
one into the CLI. A genuine qualified operating capability remains required.
Tests inject explicitly fictional software custodians; they are not that
capability. Per-pass status is bounded, retains its first gap, and reports only
returned retirements; it is not a complete historical outcome journal. Original
intents/results stay with the supplied actual evidence custodian.

Under reporting pressure the inherited alert service preserves admitted exact
occurrences independently of outbox allocation. Count/byte refusal retains the
owned explicit unmet interval with observed timing, first scope and accumulated
unrepresented count. Later success does not erase it. Unobserved historical
populations remain unknown; the interval summary is not full population history,
delivered alerts, backfill, or fulfilled cadence. Complete storage failure can
prevent even that write. This feature preserves that limited representation and
does not widen its claim.

The source/consumer/control/transport/outbox/publication/resource/recovery/effect/
privacy duties of all old and new work remain. Work44 remains PARTIAL with
effects UNKNOWN. Independent Source → DIFFERENT Frame → actual Work precedes
adoption. No live operation or acceptance is selected by this source.
