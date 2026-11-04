# Closed Work integration execution

This source capability separates execution exclusivity from enduring source,
effect, publication and delivery custody. A malformed or blocked held Work
integrator may have genuinely closed even when its effects remain UNKNOWN.
Retiring that execution fences it permanently. It does not complete its job,
process its frozen input, transfer custody, settle delivery, promote its result,
clear a hold, reconcile an effect or authorize another execution by itself.

Only the actual enrolled Work owner can use the CLI entrypoints below;
they check the existing current Board authority. Journal methods follow the
same trusted caller convention as existing owner methods. Plain receipt text
does not authenticate a collector or establish actual process closure. The
owner must qualify the genuine original handles, numeric ENDs, collection and
applicable writer closure before submitting it. An END count is insufficient.
This protocol cannot exclude a noncooperating external writer.

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
