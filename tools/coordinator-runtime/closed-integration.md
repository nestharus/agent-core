# Closed Work integration execution

This source capability separates execution exclusivity from enduring source,
effect, publication and delivery custody. A malformed or blocked held Work
integrator may have genuinely closed even when its effects remain UNKNOWN.
Retiring that execution fences it permanently. It does not complete its job,
process its frozen input, transfer custody, settle delivery, promote its result,
clear a hold, reconcile an effect or authorize another execution by itself.

Only the actual enrolled Work owner can use the four CLI entrypoints below;
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
reservation retains the reservation for actual owner disposition; this module
does not invent an automatic refresh, cancellation, replacement or retry.
Retired original execution cannot resume through this API. Genuine remaining
work needs separately authorized new scope while retaining the original debt.

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
