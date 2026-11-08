# Prospective ordinary effects in a continuing journal

This is a source capability. Deployment, actual packages, current resource leases,
and the independent accepting authority must be selected by the operating owner.
It does not activate source27, replace the selected review procedure, or finish
four-role cutover. Use matching source31 currentness/custody corrections when
the parent has composed, examined and selected them; this contribution does not
contain or certify that separate work.

`authorize-prospective --selection /absolute/selection.json` requires actual Work
context through the existing cooperative actor interface. It writes one explicit
authority record to the **same** journal. Job reservations record logical birth
in their existing write transaction; the selected job frontier survives qualified
cohort retirement and physical rowid reuse. New epochs mark `job_birth` as
`observed-v1` internally and require an actual observation for each future job.
Missing historical birth is never backfilled. Pre-existing epochs retain their
original rowid interpretation for unobserved jobs; newly observed reservations
advance beyond their conserved boundaries too. Per-job observations retire only
with their qualified cohort; their SQLite sequence is never reset. Missing birth
cannot waive retained authority checks for otherwise future members.

Event boundaries retain their existing meanings: logical source positions for
an explicitly selected processing bridge, physical event rowids otherwise.
Job birth changes neither member eligibility nor processing, acceptance or
retention proof. The immutable configuration, journal path/inode, actor,
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

`local-qa` adds `command`, `readback`, `known_exits: [0,1]`, and
`source_capture: {bwrap:"/usr/bin/bwrap",sha256:TOOL_SHA256,max_bytes:INTEGER,max_files:INTEGER}`. Each command is
`{argv:[ABSOLUTE_EXECUTABLE,...],executable_sha256:SHA256,stdout:EXPECTED_OR_NULL}`.
Executable bytes must be in the admitted roots. `readback.stdout` must be a
nonempty exact independent procedure-specific completion/resource oracle. The
actual command executes without a shell. Exit0 is success; exit1 is known failure
only when the readback succeeds. Other exits, changed source, incomplete capture,
failed/incorrect readback, stale authority or expired lease stay unknown and held.
The readback must be sufficient for the *actual* runner/resources: an arbitrary
echo or model JSON is not an admissible real resource oracle. Package/procedure
owners own that semantic applicability. Network is false.

Local QA exports the admitted commit's exact ordinary tracked Git blobs into a
fresh retained execution directory and runs both command and readback with that
export mounted read-only at the admitted repository cwd. The old checkout is not
mutated. Both absolute candidate paths are protected in the namespace. A separate
admitted harness, dependencies and generated inputs remain possible through the
explicit read roots; generated outputs use write roots outside the repository
and outside ancestors of the retained export. The namespace has a clear environment
with HOME unset, an isolated network, system /usr, private /tmp, proc and dev.
The candidate is available before the runner starts; checking a ref label alone
never supplies this association.

Export is bounded to at most5000 files/128MiB total and4MiB per file, further
restricted by the selected policy and ordinary listing/capture/journal budgets.
Symlinks and submodules refuse explicitly; no export attributes, ignored checkout
files or local modifications substitute for tracked candidate bytes. The original
runner record and exported blob/hash manifest accompany the receipt. Reconciliation,
independent acceptance and fresh cleanup qualification validate that association.
Older local-QA receipts without actual candidate execution evidence cannot become
accepted qualification. They are not rewritten or automatically re-executed.

This capability does not prove that an arbitrary authorized harness exercises the
intended behavior, authenticate fixture acceptors, make externally generated inputs
part of the candidate tree, contain arbitrary descendants, or exclude privileged or
noncooperating host writers. Independent procedure/oracle/resource selection and
semantic acceptance remain necessary. There is no universal persistent-owner gate.


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
attempt is fully collected. For a new report, `unknowns` contains unresolved facts
needed for that preparation. Future service preflight/export/runner/readback,
separate acceptance/downstream work and unrelated historical obligations remain
explicit findings of kind `ordinary-pending-stage`, with owning stage and full
original ref/text. They are pending evidence, not observed outcomes or authority.
An admission prerequisite that prevents preparation remains a blocking unknown.
No pending finding bypasses the service's current guards, changes an old return
or clears inherited holds. Existing original reports with `unknowns` stay intact
and refused; this prospective prompt contract does not reinterpret them.

The service durably records its intent and exclusive
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
callbacks and uncertainty retain their existing procedures, with source31 exact-admission, callback and counter corrections preserved in the composition.

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

Future capture overflow, timeout, cancellation or decoding errors retain a terminal
record when an actual wait obtains its numeric END. Capture stays incomplete and
intent/resource/effect uncertainty stays held. Bounded pipe draining can still leave
END unknown; no historical missing END is reconstructed. Separate terminal and
capture fields never authorize replay, effect settlement or legacy hold release.

Future same-journal software handoffs and scanner intake share the exact source
handoff identity in either observation order. Distinct handoffs, historical native
or queued duties and recurring alerts keep their separate responsibilities. No
configuration-flag migration, retrospective queue deletion or content dedup occurs.

## Prospective admitted operations and public QA executables

Actual Work may explicitly select `ordinary_effects: "admitted-v1"` for a
package-scoped Branch integrator or QA execution task. This is a task capability
ceiling. The original package's admitted `ordinary_effects` object selects its
operation; omitting that object permits the normal separately scoped receiving
path without selecting an adapter. A present malformed object refuses. Existing
`true` selections still require an adapter for every applicable package, and
`false` selections still grant no adapter authority. Existing job births,
attempts, frozen admissions, grants and selected epochs retain their meaning.
No selection, admission or effect authority comes from message/model text.

Receiving retains its configured effect reconciliation, original collection,
source/member/currentness and delivery/release guards. In particular, an
`owner-reconcile` Branch task still needs its actual role owner's effect/outbox
receipt even when its admitted receiving scope has no adapter. Absence of an
adapter does not clear that guard. QA still executes first, receives separate
independent acceptance for every admitted ordinary operation in its package,
then performs full narrowed consolidation and fresh qualification before Branch
receiving. A Branch adapter in that same package remains an acceptance dependency;
this contract does not waive it. Separate legitimate Branch and QA packages can
share one continuing prospective epoch without changing global policy per message.

For `local-qa` under `admitted-v1`, an optional `public_executables` object maps
`command` and/or `readback` to exact `{path, bytes, sha256}` identities. Supported
canonical installed paths are `/usr/bin/python3.12` and `/usr/bin/git`; no alias,
parent directory, credential CLI or source-root exemption is selected. Each pin
has a 32MiB bound, with 64MiB aggregate declared acquisition per validation.
Complete bytes are streamed through no-follow descriptors, with regular executable,
size, mode, hash and before/after identity checks. Binary bodies do not become
source artifacts, evidence text or model context. Existing source, procedure,
export, result, context and runtime budgets are unchanged.

Each public pin must match that role's `argv[0]` and `executable_sha256`.
Python supports `-B SCRIPT` with an absolute in-scope script and command field
`script_sha256`, or `-B -m unittest discover -s DIRECTORY` with optional final
`-v` and an in-scope directory. Inline code and other interpreter modes refuse.
Public Git supports only `--no-optional-locks -C REPOSITORY rev-parse --verify
refs/heads/NAME^{commit}` (or `refs/tags/NAME^{commit}`), with the repository in
scope. A ref match alone is not an adequate runner/resource completion oracle.
The actual operator separately supplies authentic procedure intent, scripts,
resources, source authority and a substantive nonempty readback expectation.
Public tool identity grants none of those rights. Unpinned external scripts and
out-of-scope discovery roots refuse before launch. Script bodies keep their
existing 4MiB evidence-file bound; larger installed interpreters do not raise it.


### Case-Root disposition of software read-only preparation

`software-preparation-recovery-basis CAPABILITY JOB --token TOKEN --attempt ATTEMPT`
returns an exact bounded evidence record only for a current software-admitted
QA preparation with its accepted branch Root equal to the genuine Work issuer.
It uses the current processing boards, original software grant/prospective job
birth, immutable applied admission, frozen task/resource policy and selected
operation-relative QA account. It checks the actual original complete END0 and
collector, kernel readOnly/networkAccess:false, positively observed ephemeral
owner exit, every known successful command tool, no other task/unknown original,
no ordinary/routine/publication intent, outgoing work/result or branch turn,
and current source/ref/tree, leases and overlap guards. A report's assertion or
one missing intent row cannot establish this disposition.

The genuine Work issuer can submit
`request-software-preparation-recovery CAPABILITY JOB --token TOKEN --attempt ATTEMPT --receipt FILE`.
FILE has the existing `mode:"remaining-work"`, nonempty `reason`, bounded
`evidence` list and `remaining` target/WHY, plus
`software_preparation:{basis:EXACT_RETURNED_OBJECT,fact:"captured-read-only-preparation-no-ordinary-effect"}`.
This is an explicit NEW preparation encounter. The full original report and
all its unknowns remain immutable. The transaction records only this captured
preparation's bounded effect disposition and queues the existing recovery
request; a refusal rolls back both. It does not launch a model or ordinary tool.

The existing actual collector consumes the request, runs the existing bounded
diagnosis and handoff, and launches the separately collected remaining attempt.
Its full prior context/result, original session and native_resume:false remain
in the handoff. The existing 909 preparation contract governs the new answer.
Actual adapter execution/readback and independent semantic acceptance remain
separate. The legacy hold is bypassed only for this exact revalidated factual
disposition when the existing resource checker already permits the operation.
The native owner's recovery and reconcile-effects APIs retain their checks.

**Transition limit:** this route deliberately refuses a revoked original
capability/epoch, expired original resource lease, changed frozen admission or
task, mismatched current grant/source, foreign/unaccounted writer or unknown
effect. A new processing service and retained source selection do not by
themselves reauthorize a frozen older job. In particular, the historic 79f1/fdaf
case's revoked 11b3/cae4 cannot use this API as an activation route. No supported
same-job cross-capability/effect-epoch transition is added here; that is explicit
remaining work for the authority owner, with original births/counters/expiry
and admission conserved. This capability does not establish current-case
operability after those revocations or authorize any invocation of old rights.
