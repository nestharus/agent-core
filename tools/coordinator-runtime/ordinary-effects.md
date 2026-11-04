# Prospective ordinary effects in a continuing journal

This is a source capability. Deployment, actual packages, current resource leases,
and the independent accepting authority must be selected by the operating owner.
It does not activate source27, replace the selected review procedure, or finish
four-role cutover. Use matching source31 currentness/custody corrections when
the parent has composed, examined and selected them; this contribution does not
contain or certify that separate work.

`authorize-prospective --selection /absolute/selection.json` requires actual Work
context through the existing cooperative actor interface. It writes one explicit
authority record to the **same** journal, with the current maximum event and job
row IDs as its boundary. The immutable configuration, journal path/inode, actor,
enrollments, original board grants, cursors, source/collector records, old jobs,
ACKed queues, holds, publication intents, resources and outboxes are preserved.
The operation neither scans nor replays old board work. Ongoing writers and QA
slots remain in the same reservation tables and transactions. A future job with
even one old member cannot inherit this authority. Historical work continues
under its original authority and recovery/custody procedures; it is not abandoned
or automatically converted into delegated work.

Selection shape (hashes are the runtime's canonical JSON `digest`):

```json
{
  "configuration": "EXACT_UNCHANGED_CONFIG_DIGEST",
  "authority": "ACTUAL_USER_WORK_DECISION_REFERENCE",
  "expires": 1794000000,
  "grants": {"Branch": "EXISTING_BRANCH_GRANT_ID", "QA": "EXISTING_QA_GRANT_ID"},
  "tasks": {
    "branch-integrator": {"task_hash": "EXACT_TASK_DIGEST", "ordinary_effects": true, "software_handoffs": {}},
    "qa-execution": {"task_hash": "EXACT_TASK_DIGEST", "ordinary_effects": true, "software_handoffs": {}}
  }
}
```

Each explicitly selected receiver task also needs a policy and its role's actual
grant. Handoffs cannot exceed the immutable task's recipients. Existing genuine
delivery grants are still required: this boundary does not manufacture board
membership or expand native delivery grants. Native grant `issued_by`/`authority`
remain native provenance; `prospective_epoch`, `delegated_by` and
`delegation_authority` name the distinct Work capability. It is a cooperative
authority record, not cryptographic authentication or an OS access-control layer.
Only one unrevoked boundary is admitted. `revoke-prospective EPOCH` revokes new
use without settling any old or new responsibility. A new boundary never replaces
the epoch of an already bound attempt.

Actual Branch still admits a package via `admit-package`, retaining its sole
package/ledger responsibility. The existing `task_scopes[TASK]` must supply
`cwd`, exact `read_roots` and `write_roots`, `network`, `procedure` and
`resource_evidence`. The task must already require package scope. The scope's
`ordinary_effects` selects one of the adapters below. Its common fields are:

| Field | Required meaning |
| --- | --- |
| `kind` | `local-ref`, `local-qa`, or `github-run` |
| `git`, `git_sha256` | Absolute regular executable and exact admitted bytes |
| `repository` | Exact admitted cwd; common Git directory must also be in scope |
| `source_ref`, `source_head` | Actual fully qualified source ref and commit pin |
| `procedure_sha256` | Exact independently authorized procedure bytes |
| `resources` | Nonempty bounded list of `{key,owner,authority,expires}` |
| `acceptor`, `acceptance_authority` | Independent actual semantic decision owner and authority |
| `timeout`, `max_output` | Positive bounded tool deadline and complete capture budget |

Resource keys must represent the real ref, runner, monitor and other exclusive
resources, with actual current custodians. Keys coordinate cooperating ordinary
effects in this journal, not other services. Existing package and integrator/QA
fences remain. A declared key or lease does not discharge an old native resource
hold. Before activation, the owner must establish disjointness or collect the
actual overlapping custodian's disposition. Unknown resources cannot be renamed
to evade a fence. There is no automatic legacy-resource discovery or clearance.

`local-ref` adds `ref`, `before`, `target`. It permits a local existing branch ref
CAS from the exact old commit to `source_head`, followed by actual readback. The
source and destination refs must differ. Network is false. The actual Git common
directory must be inside the admitted write roots, including for linked worktrees.
This adapter does not push remote refs, create wrapper PRs, linearize arbitrary
stacks or approve a package. Those operations need their actual selected procedure
and a compatible adapter; no generic shell/ref bypass is provided.

`local-qa` adds `command`, `readback`, and `known_exits: [0,1]`. Each command is
`{argv:[ABSOLUTE_EXECUTABLE,...],executable_sha256:SHA256,stdout:EXPECTED_OR_NULL}`.
Executable bytes must be in the admitted roots. `readback.stdout` must be a
nonempty exact independent procedure-specific completion/resource oracle. The
actual command executes without a shell. Exit0 is success; exit1 is known failure
only when the readback succeeds. Other exits, changed source, incomplete capture,
failed/incorrect readback, stale authority or expired lease stay unknown and held.
The readback must be sufficient for the *actual* runner/resources: an arbitrary
echo or model JSON is not an admissible real resource oracle. Package/procedure
owners own that semantic applicability. Network is false. This controller does
not provide an OS sandbox, exact read isolation, descendant containment, or proof
that an arbitrary runner cannot escape its declared roots. Select only a genuinely
bounded authorized runner, its independent oracle and the applicable containment.

`github-run` adds `gh`, `gh_sha256`, `repository_slug`, `run_id`, `run_attempt`,
`event`, `workflow` (the API run `path`), and exact `job_ids`. Network must be
explicitly admitted. The adapter observes the **already selected** run/attempt
with the real CLI API, checks repository/head/event/workflow, then reads the
attempt's exact completed job selection and outcomes. Failed/cancelled/skipped
outcomes are recorded, never accepted success. Nonterminal, mismatched, unknown
or incomplete/paginated selections remain held with the original monitor. The
bounded adapter supports at most100 selected jobs. It does not dispatch/re-run a
workflow, select an arbitrary PR/run, create CI capacity, replace an original
monitor, or prove a provider encounter from an offline fixture. A package needing
workflow dispatch or remote ref mutation returns that concrete unsupported
operation for a separately authorized adapter rather than silently replaying it.

For newly bound ordinary jobs the model performs read-only preparation. The
service executes the exact admitted tools only after the original preparation
attempt is fully collected. The service durably records its intent and exclusive
keys before tools, records each actual process/capture/END, checks current scope,
grant, procedure, lease and source around operations, and records actual readback.
Successful known reconciliation releases only those ordinary resource keys.
Interrupted intents remain owned and are never automatically retried. A tool
failure or lost callback can leave a known original operation but an unknown
overall outcome; no END/DONE or supplied receipt can waive it. No atomicity across
Git, SQLite, board and network is claimed. Ref CAS protects that ref comparison;
it does not lock noncooperating writers or all source relationships.

Known QA failures may finish local reporting and route correction. Effect
observations accompany responses/handoffs separately from the unchanged model
result. Local collection/reporting, effect reconciliation, downstream settlement
and semantic acceptance are different records. Unknown effects retain slots and
custody; they do not become hidden retries or releases. The prospective own-result
callback consumes only its exact bound job and known collected effects. Old native
callbacks and uncertainty retain their existing procedures, including separate
source31 correction requirements.

`ordinary-acceptance ATTEMPT --decision accepted|rejected --receipt FILE` requires
the actual independently admitted acceptor, distinct from worker/service/collector.
The receipt supplies `execution_hash` of the immutable run receipt, a meaningful
`rationale` and `unknowns: []`. This attributes the semantic decision; its truth is
the independent acceptor's responsibility. Accepted requires the actual successful
outcome and fresh source/ref/CI readback. Rejected is preserved separately. Each
original attempt has one immutable decision. A legacy `admissions.accepted` JSON
cannot qualify the new path. All ordinary tasks admitted for the package require
their own accepted execution. Before QA qualification, the dispatcher gathers
fresh readback again and binds it to the actual cleanup attempt; stale/missing
proof refuses qualification. Other selected reviews and product acceptance
obligations remain in force.

No current real package, live boundary, current resource lease, CI run, service
deployment or four-role qualification is selected by this document. Old C814's
expired once-only native admission is not reusable. Old Work928 artifacts/targets,
UNSENT intents and current peers stay held. Recurring unchanged stale alerts stay
enabled. Keep outputs through actual processing completion+24h **and** every
source/consumer/outbox/publication/resource/recovery/uncertainty hold. No cleanup
or older-source rollback/replay is implied. Do not run an older executable against
an active prospective authority; disposition/revocation and all conserved work
must be handled by the actual owner first.
