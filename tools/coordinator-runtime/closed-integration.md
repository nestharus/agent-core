# Closed Work integration execution

For a held nonwriting Work proposer whose historical bodies are outside the
selected authority, use the separate [metadata-only read fence](work-read-metadata.md).

An explicitly selected [local integration policy](local-integration.md) supersedes
legacy singleton/window and cross-package QA phase requirements for its future
anchored paths. All seven duties, actual contexts and applicable gates persist;
this source option supplies no adoption or historical replay authority.

This source capability separates execution exclusivity from enduring source,
effect, publication and delivery custody. A malformed or blocked held Work
integrator may have genuinely closed even when its effects remain UNKNOWN.
Retiring that execution fences it permanently. It does not complete its job,
process its frozen input, transfer custody, settle delivery, promote its result,
clear a hold, reconcile an effect or authorize another execution by itself.

Only the actual enrolled Work owner can use the CLI entrypoints below;
ordinary calls check the existing current Board authority. The explicit paused
management path below has a separate original-owner check. Journal methods follow the
same trusted caller convention as existing owner methods. Plain receipt text
does not authenticate a collector or establish actual process closure. The
owner must qualify the genuine original handles, numeric ENDs, collection and
applicable writer closure before submitting it. An END count is insufficient.
This protocol cannot exclude a noncooperating external writer.

## Explicit management during an ordinary-intake pause

The genuine Work owner may separately select purpose-scoped management while
ordinary enrollment remains paused and its original software grants remain
revoked. An owner name, reservation token, metadata basis, or lower journal
method supplies no current management authority. The owner must have an actual
current decision for both the operation and its record acquisition. Authority
and purpose text is attributed owner testimony; software does not authenticate
external decisions, collector closure, peer facts or custody assertions.

`integration-management-basis --roles Work [RELATED_ROLE ...] --authority REF
--purpose TEXT` requires the actual Work session, which must also be the original
software grantor. It returns current configuration/source pins and only the
named roles' original grant/enrollment metadata. It uses the existing qualified
original-grant protocol, including revoked software grant, paused enrollment,
same journal path/device/inode, Board/owner/actor identity, membership and original
configuration binding through any selected current transition. Current release
checks still apply. It acquires no old input/result/capture bodies and issues no
grant or processing capability. No normal intake is reopened.

The four commands `integration-closure-basis`, `retire-integration`,
`integration-window-basis` and `select-integration-window` accept an optional
`--management ABSOLUTE_FILE`. That file must contain exactly:

```json
{
  "basis": "EXACT management metadata basis OBJECT, including current authority and purpose",
  "expires": 1234567890,
  "operation": "integration-closure-basis",
  "target": {"job": "EXACT owned job", "token": "EXACT reservation token"},
  "records": {"jobs": ["EXACT owned job"], "events": ["EXACT frozen input"]}
}
```

The placeholders must be actual JSON objects/identities with independent access
authority. Expiry is a finite future Unix time at most one hour away. Each call
binds its exact command and target. The two window commands instead require
`target: {"task": "EXACT Work integrator task", "events": ["EXACT next input"]}`.
For window selection those values must match the supplied receipt basis.
Changing the command, target, source, original binding, configuration, expiry or
related enrollment requires a fresh explicit selection; there is no automatic
renewal, borrowed processing capability or old-grant reactivation.

`records.jobs` must name exactly the closure job, or exactly the jobs with
tracked retirement/prestart fences for a window. `records.events` must name all
of those jobs' frozen inputs plus the proposed next inputs for a window. The
basis roles must match the actual related source roles, including Work. Small
job membership/source-role headers and fence job IDs are checked before full
operation acquisition; extra or missing scope refuses. This is bounded tracked
debt qualification, never all-history clearance. Basis/receipt/result/debt rows
can contain full old material: the selected scope must independently permit
those bodies, linked attempts, results, outboxes, publications, recovery and
custody records. Referenced physical artifacts/captures are not opened by this
path. Existing mutation admission also measures runtime-home file metadata
(excluding the opaque sessions subtree) for its cumulative budget; this needs
its own actual privacy/access qualification. A command name waives no exclusion.

Within one local transaction the adapter checks the current selection, runs the
original closure/fence/window predicates, rechecks currentness, and for a mutation
appends its exact management selection and outcome to
`integration_management_operations`. Audit/budget failure rolls back the local
mutation. Board lifecycle locks and rechecks retain their existing limits; this
is neither multi-file atomicity nor noncooperating-writer CAS. Ordinary public
paths, prestart/no-start routes, Store enrollment, intake, processing, recovery,
launch and publication authority are unchanged. Management cannot start a task.

The original begin/END/collection/numeric-exit, exact fresh closure basis,
original collector/controller/writer closure, no-pending-recovery, future-window
currentness and applicable conflict/custodian evidence requirements below all
remain. Access proves no old-job eligibility. A fence completes no processing,
settles no unknown effect and starts no disposal clock. Whole processing plus
24 hours AND every source/privacy/consumer/outbox/recovery/effect hold still
govern disposal. Synthetic checks establish source behavior only, never live
authority, source adoption, real original closure or rollout acceptance.

The focused public-entry tests run with:
`PYTHONPATH=tools/coordinator-runtime:tools/coordinator-runtime/tests python3 -B
-m unittest -v test_management406` from the selected source checkout. They use
temporary synthetic boards/journals, an explicit synthetic clock and generated
fixture identities, with no provider/model/runtime encounter or pool allocation.

## Closure and conserved future windows

`integration-closure-basis JOB --token TOKEN` returns the exact held Work
integrator job, related original attempts and results, and all controller
identities represented by the job, recovery owner and related attempts. Every
attempt needs actual begin, numeric END and collection; missing/unknown closure
refuses regardless of semantic DONE, ACK or other attempt counts. Capture,
result and effect uncertainty may remain. This path does not retire an
unstarted or uncollected execution.

`retire-integration JOB --token TOKEN --receipt ABSOLUTE_FILE` accepts:

```json
{
  "basis": "EXACT returned closure basis object",
  "reason": "Why this genuinely closed execution is retired",
  "controllers": [{
    "controller": "EXACT represented original controller",
    "collector": "Genuine owning collector",
    "end": 0,
    "collected": true,
    "writers_closed": true,
    "evidence": ["Exact original END and applicable writer closure evidence"]
  }]
}
```

Include every represented controller exactly once, with its actual numeric END
(including nonzero). The placeholder `basis` above must be the actual JSON
object, never the string. A changed basis, conflicting/missing closure,
pending owner recovery request, foreign owner or repeated retirement refuses.
The journal transaction inserts only a retirement record. Existing job,
attempt, result, queue, source, custody, publication and delivery rows stay
intact. Old recovery, closure transfer, launch and publication paths refuse;
dispatcher callbacks skip the retired execution. Existing accountable effect
reconciliation and consumer delivery duties retain their separate owners.

An execution retirement can release its execution capacity while its original
job remains held. Later Work integration requires a fresh bounded selection:

1. `integration-window-basis TASK --events EVENT [EVENT ...]` selects exact
   currently queued inputs and returns their frozen membership, current Work
   enrollment and conserved debt. Original reserved inputs cannot be replayed.
   Debt carries the retirement witness, original/current job and attempts,
   source/queue/custody, recovery histories, publication and outbox state.
2. `select-integration-window --receipt ABSOLUTE_FILE` requires the exact
   returned `basis` object, nonempty `target` and `why`, plus bounded lists
   `conflict_evidence` and `custodian_evidence`. The genuine owner qualifies
   action-specific current source/peers and actual custody, including conflicts
   with uncertain prior effects. Unrelated UNKNOWN duties may remain; this is
   not a universal all-effects-clear condition. Receipt assertions cannot
   manufacture missing evidence or disposition.
3. Normal reservation consumes that selection once, under the existing
   cross-controller SQLite write transaction and one-integrator capacity
   check. It freezes only the selected new members. Start and launch checks
   refuse changed debt/enrollment, source or holds. The successor receives the
   complete selection (including target/WHY) in its attempt context and the
   current conserved debt in its task prompt. Its normal grants, current task
   authority, staged publication preimages and delivery gates still apply.

Each later window requires its own selection while retired debt exists. A
stale or already consumed selection cannot become a new job. Staleness after
reservation retains the reservation for actual owner disposition as below.
Retired original execution cannot resume through this API. Genuine remaining
work needs separately authorized new scope while retaining the original debt.

Debt entries now identify their operational representation as
`integration-debt-v1`. They retain current job, attempt, source, custody,
recovery, queue, publication and outbox fields. Every attempt's semantic state,
capture/cleanup/error, unknowns, partial reports and unrecognized detail fields
remain inline. The execution fence retains its actor, reason and controller
closures; an earlier attempt window retains its target/WHY, conflict and
custodian evidence. These current duties and assertions, rather than a short
identity alone, inform the owner's next decision. Assertions are still
attributed evidence, not proof of actual custody or availability.

Three repeated historical snapshots use `integration-evidence-ref-v1`:
the fence's original `basis` TEXT column, the `basis` inside its receipt, and
the `debt` inside an attempt detail's historical `integration_window.basis`.
That earlier window's task, frozen members and enrollment remain inline.
Whole original receipt/detail references also bind their exact text bytes.
`basis_matches_receipt` exposes a conflicting fence/receipt snapshot directly.
No database schema or historical row changes. A reference identifies table,
primary key, column, optional JSON path, SHA-256 and encoded UTF-8 byte length.
Hash/length cover `contracts.encode(value)`; for a whole TEXT column the value
is the original string, including whitespace. JSON paths select inside that
column's strictly parsed JSON. The enclosing raw-text reference also detects
format-only changes. Older stored full witnesses keep their original format;
they differ from a new view and require fresh owner selection rather than an
automatic refresh or historical rewrite.

Fuller evidence remains in the named existing journal rows. A consumer with
independent authority for those rows can supply one to
`integration_evidence.expand(reference, row)`, which verifies identity, path,
length and digest without I/O. This is not a new CLI operation, read capability,
grant, body-discovery instruction or permission to follow private references.
Missing, changed or inaccessible originals remain gaps for the actual custodian;
they do not become empty/settled duties. Existing custody, retention and access
requirements still govern the original rows. Current mutable fields remain
inline, and folded history remains hash-bound, so neither kind of change can
silently reuse an old selection through reservation or launch.

This reduces repeated transport, not acquisition, memory or transaction cost:
the existing authorized row queries still load and hash those columns. There
is no new responsiveness, cross-store durability or isolation guarantee.
Other large current fields and unexpected historical formats remain intact;
they can still exceed the unchanged bound and refuse without dropping duties.
The separate alert-reporting behavior is unchanged.

The source-only control below uses in-memory fictional journals, selected
unchanged Store methods and fictional allocation. It exercises nested evidence,
exact retained expansion, duty conservation, stale selection/reservation/start/
launch authorization and owner/refusal boundaries. Configuration admission,
cumulative disk accounting, actual producer/service access and runtime outcomes
are outside that control; no real accounts, Board or original bodies are used.

```bash
python3 -B tools/coordinator-runtime/tests/test_integration_bound419.py
```

`integration-prestart-basis JOB --token TOKEN` supplies a separate disposition
for an exact selected Work reservation with **no allocated attempt at all**.
`withdraw-integration-prestart JOB --token TOKEN --receipt ABSOLUTE_FILE`
requires that exact `basis` object, a nonempty `reason`, and bounded
`no_launch_evidence` strings attributed to the current Work owner. The owner
must establish that no unrepresented launch/writer exists; journal absence is
not an external process census. No process END is asserted on this route.
Foreign owner/token, changed basis, any allocated attempt (even unbegun),
recovery lineage, or inconsistent queue ownership refuses without release.

Withdrawal serializes against start under the journal write lock. It inserts
a permanent execution fence, holds the old reservation, and returns precisely
its reserved queue rows to pending without changing input/hold/ACK/processing
or source/custody/result/publication/outbox state. The original consumed window
and frozen members stay intact. The disposition and current duties join the
conserved debt of every subsequent window; withdrawal alone authorizes no new
execution. Current source, enrollment, peer/conflict and custodian evidence
must support a fresh owner-selected batch, including any returned inputs.
The old execution cannot start or recover later. This route does not handle an
allocated attempt or recycle lifetime job/window capacity.

`integration-no-start-basis JOB --token TOKEN` is the separate allocated
route. Every related task attempt must have an affirmative original-controller
collection of `known_not_started: true` and explicit resume disposition, with
no begin, session, turn, semantic result, numeric exit or process END. Missing
begin or missing END alone never qualifies. Uncollected attempts, conflicting
task native observations, pending owner recovery selections and missing consumed
windows refuse. Related read-only diagnoses must either qualify as no-start or
have their actual begin, numeric END and collection retained. Their having
run does not manufacture an END for an unlaunched task or strand that task. A claimed recovery controller is included even if it has not
allocated a diagnosis; an uncollected diagnosis cannot be bypassed.

`withdraw-integration-no-start JOB --token TOKEN --receipt ABSOLUTE_FILE`
requires the exact fresh `basis`, nonempty `reason` and `controllers`. Each
controller entry has exactly `controller`, nonempty `collector`,
`writers_closed: true`, `no_launch: true` and bounded nonempty `evidence`
strings. Here `no_launch` is scoped to the task attempts; a collected read-only
diagnosis retains its real closure in the basis. Include every original/recovery
controller exactly once. Those are
scoped, accountable collector facts that the actual owner must establish;
text does not authenticate them or prove foreign-writer absence. No process
END is invented for a process that never started, and no controller END alone
would establish the no-launch/closed-writers premise. CLI actor and current
Board authority checks precede this operation.

This disposition uses the same permanent prestart fence and queue return, and
retains the allocated attempts/results, original window/target/WHY, existing
job hold, recovery state, input ACK/holds and all effect/publication/outbox/
custody duties. It requires current disposition evidence but does not require
the obsolete launch-window snapshot to become current. A fresh exact window
must then account for all old/new debt before a new job may reserve or launch.
Begin/session/semantic callbacks, recovery and publication on the withdrawn
execution are fenced. Related unresolved publication, effect or attempt-cleanup
duties remain processing/retirement dependencies through the original frozen
members after queue reassignment; unrelated UNKNOWN debt does not consume all
future execution capacity. Withdrawal supplies neither processing nor cleanup,
and no lifetime budget credit is granted.

Initial, diagnosis and recovered successor prompts load the authoritative
integration-window receipt from the journal. Handoff also records it in the
new attempt detail. The selected target/WHY and original obligations therefore
remain available even when a diagnosis omits them or the prior detail lacks
them. Existing owner remaining-work selections are carried alongside that
original selection; they do not erase it or waive currentness/effect gates.

All records have the existing journal byte/job/result bounds. Window selections
also have a lifetime count bound equal to `max_jobs`; hitting a bound refuses
without deleting evidence or granting credit. The bounded evidence snapshot
may refuse large histories rather than silently truncating them. No retention
clock starts from retirement, END, ACK or a selected/reserved window. Actual
processing plus 24 hours and every applicable hold remain necessary.

The finite control entrypoint is
`python3 -B tests/test_integration_lifecycle73.py --fixtures ABSOLUTE_NEW_OWNED_ROOT`.
`--full-store` additionally uses the inspected production import graph and
checks construction/reopen and effect refusal entrypoints. Imports alone do
not qualify actual provider, Board authority, collector closure, peer facts,
custody or service continuity. Run only under the caller's selected isolation
and writable-root bounds. It imports no stock fixtures, substitutes no HOME or
session identity, deletes no fixtures and makes no native/model call. Its
fictional pool allocator performs no shared pool or account operation.

Allocated no-start software controls are in
`python3 -B tests/test_integration_no_start77.py --fixtures ABSOLUTE_NEW_OWNED_ROOT`.
They require caller-enforced kernel read-only source/dependency/controller
mounts, network/PID isolation and explicit owned fixture storage. They check
cumulative retained fixture headroom before every new case and retain all
beforeimages/SQL traces. Fictional no-launch/collector/Board/allocation facts
are protocol premises; this establishes no operating adoption or live recovery.

When recurring allocation windows are selected, an explicit conserved-debt
integration selection also retains that configuration's batch-size bound. It
refuses an oversized selection intact; it does not truncate members, drop duties
or replace the selected target and WHY. Allocation-window renewal remains
separate from integration selection and its retained lifetime evidence bound.
