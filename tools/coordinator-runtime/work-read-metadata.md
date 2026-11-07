# Metadata-only fence for a closed nonwriting Work proposer

`work-read-metadata-closure-basis JOB --token TOKEN` and
`fence-work-proposer-metadata JOB --token TOKEN --receipt FILE` provide a
separate `work-read-fence-metadata-v1` contract. Legacy
`work-read-closure-basis` / `fence-work-proposer` retain their full historical
acquisition and comparison behavior. Choose the new commands when authority
permits only original execution metadata and SQL policy predicates.

The genuine current Work owner uses the ordinary original-grant check, or a
distinct operation-local paused management selection via `--management FILE`.
Create its basis with `integration-management-basis --metadata-only --roles Work
[RELATED_ROLE ...] --authority REF --purpose TEXT`. Original software grants
must be stopped and enrollment paused for management; neither command reopens
intake or issues processing authority. Current source/configuration/release,
original runtime/grant/owner/member bindings, bounded expiry, exact command,
job/token and related event/source-role IDs remain required. No hypothetical
global authorization gate is introduced.

For example, these are **fictional** names at fixture clock 1000, with the
returned JSON objects substituted for the indicated strings before use:

```json
{
  "basis": "SUBSTITUTE exact metadata management basis OBJECT",
  "expires": 1100,
  "operation": "work-read-metadata-closure-basis",
  "target": {"job": "fiction686-old-proposer", "token": "fiction686-old-token"},
  "records": {"jobs": ["fiction686-old-proposer"], "events": ["fiction686-source"]}
}
```

The expiry must actually be in the next hour. Obtain the closure basis using
this exact selection. To fence, select operation `fence-work-proposer-metadata`
with the same exact target and records and submit:

```json
{
  "basis": "SUBSTITUTE exact returned work-read-fence-metadata-v1 OBJECT",
  "reason": "Fiction686: closed original execution; every retained duty stays owned",
  "controllers": [{
    "controller": "fiction686-parent",
    "collector": "fiction686-actual-original-collector",
    "end": 2,
    "collected": true,
    "writers_closed": true,
    "evidence": ["FICTION ONLY: actual controller, descendants and launch-capable writers closed"]
  }]
}
```

Every represented job/attempt/recovery controller needs its own genuine
collector/END/collection/writer-closure evidence. Receipt text is attributed
testimony, not authenticated external truth. These examples establish no actual
IDs, authority or closure. The actual owner supplies those facts later.

The basis projects only the exact held Work proposer header, frozen
queue/event/source-role relationships, and all related task/diagnosis
controller/begin/END/collection/exit metadata. Every related original must have
finite ordered begin <= ended <= collected and an integer exit. Recovery must
be inactive and consistent, with no pending request. Any original local_jobs
row or related file publication row refuses, without reading its scope or
publication body.

The original immutable frozen task must satisfy explicit SQL JSON predicates:
Work/proposer, read-only sandbox, effects none, absent/false network,
absent/null execution, absent/null/false routine completion, and an object
effect authority with an empty array of write roots. SQL returns a boolean;
the task/scope and member hashes are never loaded, hashed or transported by
this path. Capture, semantic, error, result, effect receipts, recovery evidence,
custody/outbox bodies and physical artifacts remain unacquired. These predicates
are intentionally stricter than legacy Python truthiness for malformed policies.

The registration compares the cooperative global revision in the same SQLite
write transaction after evidence/capacity checks. Opaque omitted-column writes
and reverted mutations invalidate a stale selection. This is not hostile-writer
CAS, historical body integrity, exact physical read isolation or cross-store
atomicity. The metadata registration budget uses allocated SQLite pages and
does not walk old captures; future ordinary storage admission remains required.

The fence is inserted separately in work_read_fences, with conditional
immutable update/delete triggers for this version. No existing job, attempt,
result, input, queue, lease, source, consumer, outbox, recovery or effect row is
changed. It blocks old callbacks/recovery/replay, but does not make execution
or processing complete or release general capacity. UNKNOWNs and privacy holds
remain. No retention clock starts: actual processing plus 24 hours and every
applicable hold still govern disposal.

Coexistence keeps the existing anchored FILE-only Work reader/integrator
contract, including current task authority and ordinary publication rights.
Native bindings, discovery and proposer writes remain excluded. Version
dispatch revalidates only the original policy predicate and unchanged
execution/source relationships; it never calls legacy _work_read_basis. Launch
passes only the predecessor ID. The registration's global revision is
historical after fencing, so unrelated future journal allocations do not stale
the permanent fence. Later opaque body changes grant no body currentness,
acceptance, processing, cleanup or custody credit. Other scheduler paths retain
their original acquisition requirements; this is not a whole-scheduler
metadata-only read-isolation claim.

Store open installs the two additive triggers and refreshes cooperative schema
witnesses through the existing revision bootstrap. No data migration or legacy
fence rewrite occurs. Existing selections become stale when the selected
implementation/schema changes; the real owner must choose its current release
and management selection. This source repair performs no live migration.

Fresh fictional controls are in `tests/test_work_read_metadata686.py`, using
the full Store/CLI operation/grant paths, SQL authorizers, query-result guards,
fixture traversal tripwires, stale revision/rollback/conservation/immutability
and coexistence cases. They provide software qualification only.
