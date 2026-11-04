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
| Recovery diagnoses | D = C + 1 |
| Job outboxes | B = 18A + D (16 handoffs, one owner question and one owner report per task, plus one disposition question per diagnosis) |
| Events | E = 1 + B, allowing each monotonic partial job plan its own classification |
| Input-control questions | Q = (C + 1)E, initially and after each bounded owner input decision |
| Outboxes total | O = B + Q |
| Attempts total | (C + 2)E + A + C + 1, including classification and owner input decisions |
| Jobs | 1 (integrator batches excluded) |

At default C=4 these totals are 114 events, 695 attempts, 683 outboxes and one
job. At C=1 they are 57 events, 176 attempts, 170 outboxes and one job.
Input-control outboxes already carry their event; the outgoing-plan gate selects
only unbound job outboxes. They therefore add questions without recursively
adding outgoing-plan events. A failed classifier cannot commit a question; its
single recovery substitutes for that failed classifier. There are at most C+1
committed question-producing classifications and C+2 classification attempts per
event. A new partial job-plan event consumes at least one new unbound job outbox,
so B bounds their population. These are conservative joint maxima, not a claim
that every maximum is simultaneously feasible in one lawful recovery order.
 Count admission requires current rows + all unspent credits + the new full
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


## Selected configuration correspondence and remaining choice

`admitted.correspondence(config)` reports static task/role shapes without following
any configured path, reading identities/grants, or executing the configuration.
The same `task_exclusions` predicate drives admission policy; the report is not an
alternative admission gate. Complete role input choices must all be selected,
eligible and same-role before finite intake; one eligible terminal task alone
does not qualify a role's mixed routes. The mode and lifetime population are
explicit. A report supplies neither actual selection nor operating evidence.

The exact public RFQ rollout configuration selected for Work48606 has no
`finite_service`. Its current shapes correspond as follows (static mapping only):

| Task | Required behavior outside the terminal count envelope |
| --- | --- |
| work-proposer | response to work-integrator; consequential scope/blocker remains with Work |
| work-integrator | batching, owner-reconciled effects, routine canonical publication, response routes |
| branch-proposer | proposal response to branch-integrator and scope/blocker to Work |
| branch-integrator | batching, owner-reconciled effects, admitted package scope, responses to Work |
| reviews-proposer | actual owner review/return and report-integrator responses; no generic substitute review |
| reviews-integrator | batching, owned artifacts, response/internal-result publication to Work |
| qa-execution | owner-reconciled admitted package execution and response to cleanup/Work |
| qa-cleanup | owned artifacts, qualification to Branch/Work response and internal-result publication |

All eight remain outside this finite mechanism; the default source's existing
paths are distinct from finite-account support. No current rollout workflow proof
follows from a terminal example, a changed selection, or this table. Branch,
Reviews and QA input route lists additionally contain a Work task: current finite
intake requires same-role choices. No selected route or task is removed here.

The remaining source scope/choice belongs back with Work through Root: retain
this mechanism for separately selected terminal duties only, or select a bounded
population/horizon for the actual response graph, external owner returns,
integrator batching, package/effect/publication duties and their failure tails.
The actual graph contains cycles through Work and QA qualification to Branch;
counting it requires an authentic finite workload/transition bound or separately
admitted child responsibility, not an arbitrary recursion depth, ACK recycling,
or silent removal of owed routes. Mixed-owner batches need explicit account
attribution/conservation and all selected producer paths need charging. Existing
legacy populations cannot simply be retrofitted. This Act does not choose those
operating semantics or duplicate the separate general held-integrator lifecycle.
One integrator per coordinator and initial QA maximum five remain the supplied
constraints; source accounting does not demonstrate their actual operation.

## Genuine operating operands

Before an actual recurring owner arrangement can support a service claim, Work
must select the entitled operating owner/consumer and current grants; provide
exact source-to-delivery/transport/control correlation and substantive completed
processing/settlement receipts; freshly qualify every named hold; and supply a
durable original intent and result sink with a real custodian for failures after
an effect. No callback, text sink reference or static mapping provides these.
The existing Python constructor takes custodians; CLI `serve` supplies none.
Absent custodians remains a visible gap. A new generic plugin/loader is not
needed merely to rename that missing actual capability. A selected adapter must
also supply bounded callback duration and adequate recurring service rate so
receive/progress remain responsive; a page of 16 alone bounds count, not time.

Finite fit requires the selected lifetime N times the count tail, existing and
competing populations, alert arrival/burst rate times actual processing lag plus
24h retention, hold/qualification/outage horizon, and headroom in each relevant
count, byte, file, SQLite/WAL, control/transport, consumer and evidence sink.
Each repeated unchanged violation adds its own occurrence. Actual amplification,
rate and hold operands must come from their owners; no physical reservation or
universal foreign-store/infinite-arrival guarantee is inferred. A required
unsupported path remains an actual gap until Work selects its scope and means.
