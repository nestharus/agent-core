# Finite prospective software role routes

These routes are selected by genuine Work through the existing processing and
prospective APIs. They do not reactivate native coordinators, change the selected
review method, reconcile historical holds, or accept an execution by model DONE.
All ordinary grants, current source clocks, exclusions and consumer frontiers
still apply. An attributed account is evidence, not an authority source.

## QA packages and initial software admission

`service.legacy_resources.QA` retains its original four fields, including
`unbounded: true` and the exact `original_hold`. It may additionally select
`qa_operations`, a list of one to seven distinct package accounts. Seven permits
five executing packages, one accepted package in cleanup, and one waiting
execution; it does not increase the execution or cleanup slot limits. The older
singular `qa_operation` remains supported; select exactly one representation.
Each list member uses the existing `statement`, `binding`, and `policy` contract.
All source/ref/tree/ordered-parent, resource-owner, procedure, executable, input,
expiry, current-grant and cross-role unresolved-job/lease checks remain in force.

A binding may retain the native-admission form
`{task, package, admission_sha256}`, or use the software form:

```json
{
  "task": "qa-execution",
  "package": "future-qa-1",
  "topic": "topic-future-qa-1",
  "scope_sha256": "<canonical digest of selected software_admission.scopes[topic]>"
}
```

Select the actual finite `software_admission` topic, submitters, package prefix,
task scopes and procedure before intake. No message supplies operation operands.
After the genuine future source is admitted, the runtime freezes the exact whole
applied admission with its actual generated capability, source identity and scope
in `processing_admission_resolutions`. It never edits either the capability or
admission to resolve a guessed ID. This route is sufficient for first bootstrap;
the native original-owner route remains a distinct alternative.

For separately selected same-package consolidation, a package account also has:

```json
{
  "cleanup": {
    "task": "qa-cleanup",
    "scope": "<exact admitted narrowed cleanup scope object>",
    "procedure_sha256": "<exact cleanup procedure bytes>"
  }
}
```

The cleanup task must retain `package_narrowing`, `owned-artifacts`, no network
and no ordinary effects. Its scope only narrows the configured report rights;
owned output still uses the runtime's fresh attempt directory. Select both
execution and cleanup task scopes in that topic. Keep five execution slots and
one cleanup slot. For the exact finite Work-selected operation route validated
against the retained hold, those slots are independent: accepted cleanup A may
reserve while disjoint execution B is active, and execution may reserve while
another package holds cleanup. The legacy global phase barrier remains for
routes without that operation-relative qualification. Same-package outstanding
responsibility, actual overlapping or unknown resources, and all current source,
admission, report, acceptance and authority fences still apply.

Cleanup requires exactly this package's independently accepted, successful,
reconciled execution and authentic complete original service response. Fresh
source/tool/procedure/retained candidate-byte verification remains required.
Execution/model DONE alone, another package's acceptance, altered reports,
changed source or revoked authority cannot admit cleanup. Qualification still
uses the existing separate `ordinary.qualification` and receiving checks.

## Collected Reviews reports

The existing `processing-report` API accepts Work's actual whole collected report
receipt. Its original reports, history, method pin, coverage, collector and numeric
END remain attributed testimony; it supplies no native-context or owner proof.
The runtime now freezes that public receipt and event hash before it is eligible
for the retained-hold exception. Interrupted intake without the freeze stays
ineligible; no unknown external effect is replayed.

Select `service.report_tasks: ["reviews-integrator"]` and retain the original
Reviews account with `unbounded: true`. Its optional `reviews_report` is:

```json
{
  "version": "reviews-report-v1",
  "authority": "<actual finite Work selection>",
  "expires": 1234567890,
  "task": "reviews-integrator",
  "task_sha256": "<exact current configured task digest>",
  "reports": [{"reference": "<actual owned collection>", "sha256": "<whole receipt digest>"}]
}
```

At most 32 distinct exact reports are selected. The sole integrator retains its
configured input/output ceiling, `owned-artifacts`, no network, and only report
operations. It requires current no-effect prospective authority. This is not a
native Source launcher, replacement review, legacy-resource clearance or grant
from report text. Existing owner-execution and HIGH reviewer method are unchanged.

Both this Reviews route and the QA cleanup exception require a finding containing
`{"collected_reports": [{"event": "...", "sha256": "...", "original": {}}]}`,
with every exact original input body in frozen-member order. The runtime supplies
this shape as `TASK_CONTEXT.collected_reports` after revalidating the current
route, before prompt artifact acquisition. Integration may add analysis,
but cannot omit or rewrite dissent, original qualification, source, context,
collector, failures, partial/unread coverage or history. The ordinary response
routes carry this full envelope downstream to Work or Branch. Source collection,
semantic acceptance, integration and downstream processing remain separate.

## Prospective Branch local refs

`qualify-ref-scope` still accepts the original retained-custodian receipt. A
separate `authority_kind: "work-selected-local-ref-v1"` receipt may instead be
issued by the actual Work capability issuer for an actually applied software
topic admission. It binds the whole fresh `ref-scope-basis`, current prospective
`admitted-v1` authority and exact accepted association/acceptor rights. The
existing activity scope must truthfully describe the exact operation and current
writers; a historical account saying no positively recorded own writer is not
that fact. Work must not derive such an assertion from account49998.

This alternative does not require native-owner impersonation or a gratuitous old
original receipt when no relevant original exists. Original frozen/executed maps,
collected-original duties, accepted association, source/destination/CAS, actual
common repository, current writer turns and unmapped/conflicting leases remain
fenced. Current cross-role unmapped or overlapping unresolved writers also block.
If a current exact activity fact is unavailable, retain that operation and report
that fact. Do not obtain a global/private inventory or clear historical debt.

No route changes Work's seven catalog/log consumer obligations, original receiving
clocks, source birth, retention, publication, effect recovery or old custodians.
Retain all input, output and interrupted-intent records under whole processing
completion plus 24 hours AND all applicable holds. The new immutable resolution
and report records are retained, with no new reclamation claim.


## Current reservation outcomes (Work50103)

`processing-source CAPABILITY EVENT --reservation-only` is the finite read-only
procedure for the genuine owning Work/custodian after normal source adoption.
Use the existing authorized configuration selection (`--config PATH` at the
ordinary CLI position). It opens an existing journal read-only and does not
initialize/migrate it, attempt a reservation, restart service, replay a source,
change grants/admission/capability, or acquire source/error/model/capture bodies.
This procedure was tested only in new fiction; it was not run on the actual
journal or original380. Actual future selection must retain original380 through
`retained_events` and a fresh mapping if needed; Work owns that transition.

The `reservation` object uses schema_version1 for admitted observations, with
exact event/source_hash, task, phase, capability, original controller,
mapping_version (0 means no owner mapping), and observed timestamp. `current`
means that this complete attribution matches current stored metadata. It never
means a fresh attempt or service liveness. `outcome` is `false`, `refusal`, or
`reserved` only for an actual reached candidate evaluation. The fixed `predicate`
(and compatibility `reason` alias) comes from `reservation.PREDICATES`; no raw
Refusal string is parsed. Examples are `role-enabled`, `processing-task`,
`legacy-hold`, `execution-capacity`, `integration-window`, `members`,
`local-capacity`, `local-unknown-material`, and `local-scope-conflict`.
`reserved` is emitted only after the actual job/member reservation completes.

Unvisited candidates/absent observations project `not-evaluated` with null
predicate/reason; skipped later guards are never diagnosed. Different task,
phase, queue, hash, controller, capability or mapping version projects `stale`
without old identities or reason. Malformed/unrecognized stored observations
project `unknown`. Legacy raw operational errors never become current typed
observations. Existing broader `--diagnostics` also returns this typed reservation
field while retaining its existing source-authentication path; the narrower
reservation-only procedure avoids that path's source-body reconstruction.

Normal guard order, short circuit, exactly-once evaluations, Refusal semantics,
admission/launch/effect rights, all consumer obligations and original unknowns
remain. The last observation is not a historical clearance or retention clock.
