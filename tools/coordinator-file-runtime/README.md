# Prospective file coordinator, schema 1

This runnable Python 3.11+ CLI/library admits finite new Work, Branch, Reviews
and QA responsibilities without a database or legacy-board adapter. It is a
candidate for owner adoption, not a deployed four-role cutover. It never opens
old runtime state. No migration, release, arbitrary command execution, provider
launch, exact-session resume or retained-data deletion is supported.

The selected failure model is cooperative same-user Linux processes, local
filesystems with flock/rename/fsync, and process interruption. Credentials
separate cooperative actors; they do not authenticate a human/session against a
hostile same-user writer. The person operating each real owner must perform its
own adoption and supply genuine evidence. Synthetic identities in tests are not
real role acceptance.

## Start and self-adopt

Use the existing checkout's `tools/coordinator-file-runtime/coordinator.py`.
Set `PYTHONDONTWRITEBYTECODE=1` to avoid caches. The new dedicated state directory
must not already exist; its parent must exist. State ancestry must contain real
directories and the state directory is own 0700. A suggested prospective path is
`/home/nes/.local/state/coordinator-file-runtime/cutover-20261110` with an
explicitly prepared parent. This implementation has not initialized that path.

The non-stdlib runtime dependencies are the public siblings
`../direct-child/execution_pool.py` and `../direct-child/fast_tier.py`. Supply the admitted public routes file
explicitly. Its adjacent `fast-tier` file must contain exactly `true` or
`true\n`; missing, linked, corrupt or disabled fast policy holds admission under
the current all-fast decision. No private account file is consulted. The
selected static routes binding is pinned at initialization with membership
masked; other route/state-directory changes hold. Supported public pool updates
continue through `execution_pool.py set`, retain its counter and affect new
allocations/admissions. Empty/corrupt pools hold. Reservations consume a turn
without refund, including failed commits. Existing encounters retain their
original profile. Pool-setting authority is outside this CLI.

For a genuine Work creator, supply a strong unique credential in the environment
and run (substitute actual admitted paths and identity):

```bash
python3 tools/coordinator-file-runtime/coordinator.py \
  --state /absolute/new/state --actor ACTUAL_WORK_ID \
  init --routes /absolute/public/direct-child/routes.toml
```

All commands take the invoking actor's credential from `COORDINATOR_TOKEN`, never
an argv flag. A role invitation uses a different, owner-agreed invitation token
in JSON stdin; the runtime stores only its hash. Work calls `invite`, naming
`target`, one of `Work`, `Branch`, `Reviews`, `QA`, `invitation_token`, and `basis`.
The actual recipient then invokes `adopt` with its own credential and encounter
`basis`. Invitation alone establishes no adoption. Do not enroll another actor
as if it had encountered this interface.

All calls have this shape; stdin is one JSON object, at most 32 KiB:

```bash
python3 tools/coordinator-file-runtime/coordinator.py \
  --state /absolute/state --actor ACTUAL_OWNER_ID call inbox <<'JSON'
{"limit":16}
JSON
```

Success is exit 0 with `{status:"ok",result:...}`. Refusal/error is exit 2 with
`{status:"held",reason:...,replay:"not authorized"}`. Metadata contention refuses
immediately. Retrying an explicitly refused metadata lock acquisition is safe;
interrupted/postcommit or external-effect ambiguity requires recovery/readback,
not an automatic command or launch retry. Domain IDs are 1..128 ASCII identifier
characters, nonempty string references at most **512 encoded JSON bytes**
(including quotes, escapes and newline), audit at most 512 changes,
resource sets at most 16, inbox at most 32. Unknown operations/fields refuse.

For library use, add this directory to the importing process's module search
path, import `Runtime`, `create` from `runtime`, then call
`Runtime(absolute_state).call(operation, actor, credential, **fields)`.
`storage.Held` is a refusal; public-pool and OS errors also propagate. A clock and
fault callback can be injected for finite local experiments; production callers
must use the actual clock. JSON values are the data contract; references are
opaque and are never followed to source, provider, private history or old stores.

## Operations and responsibility boundaries

| Operation | JSON fields and meaning |
| --- | --- |
| `invite`, `adopt`, `revoke` | Work invitation fields above; adoption `basis`; Work revocation `target,reason`. Revocation keeps original attempts/effects held and transfers no collector identity. |
| `ingest` | Work: `event,payload,producer,source_basis`. Exact ID/content duplicates return current ACK; changed content refuses. Initially unacknowledged, with conservative holds. |
| `reserve` | `attempt,event,phase,resources,basis`; optionally `point,package,branch,review`. `resources` maps stable resource IDs to `read`/`write`; `basis` maps every declared resource to an integer generation, including absence 0. An attempt never automatically expires. |
| `start` | `attempt,collector,substrate,evidence`. Only `fixture` or `owner-encounter` evidence records are supported. Rechecks current pool and all-fast policy. Durable `launching` and unique `launch_id` precede effects. No second launch from launching/collected state. |
| `collect` | `attempt,collector,launch_id,end,result,evidence`. Same original collector and launch correlation, actual numeric END required. Failures remain failures; result text grants no acceptance. |
| `cancel` | `attempt,collector,evidence`. Original owner can disposition a `reserved` attempt or a fixture's durably recorded `not-started` control refusal. No numeric END is invented, no pool turn is refunded, and no new reservation is made. Launching/uncertain attempts and attempts with effect records refuse. Exact repeat returns its disposition; changed evidence conflicts. |
| `classify` | Work: `event,attempt,collector,classification,owner,needs`. Collected successful fresh `luna-low` classifier result must equal `{event_hash:SOURCE_HASH,classification:KIND}`. Kinds: `known,new,unresolved,control,coalesced`. Current adopted owner and 1..16 explicit needs become durable together with LOW provenance. Provenance is supplied evidence, not provider attestation. |
| `ack` | Work: `event`; refuses until classification **and** responsibility are durable. Lost ACK can be retried without repeating classification. Unresolved/control/coalesced retain their needs and cannot enter ordinary known/discovery work. |
| `branch` | Branch: `branch,repository,ref,incarnation,root,basis`. Immutable prospective association; a new incarnation needs a new ID. These are owner-supplied bindings, not Git mutations or independent verification of Root acceptance. |
| `review` | Reviews: `review,component,branch,opaque_contract,context,history`, optional `predecessor`. Preserves separate component/run/history references and calls; successor is explicitly a **new** encounter. Does not resolve opaque selectors or manufacture a resumable session. |
| `package` | Work: `package,event,scope,basis`; admits a classified known event owned by QA. QA reserves this exact event/package. |
| `integrate` | `attempt,collector,writes`. Successful collected proposal, still-owned attempt, complete current version basis and admitted write footprint required. Commits only coordinator deltas/generations; unrelated resources remain unchanged. External canonical files/Git refs are **not** mutated or certified current by this operation. |
| `effect`, `observe_effect` | Intent: `effect,attempt,collector,kind,intent` while launching; kinds `publication,push,delivery`. Original owner later records `effect,outcome,evidence`, outcome `applied` or `not-applied`. Unknown remains intent and prevents reconciliation. These commands do not perform external effects. |
| `reconcile` | `attempt,collector,evidence`, optionally `builder`. Requires collected numeric END and every effect settled. Branch builder additionally supplies exact `commit,remote_readback,pushed,signed,effects_reconciled`, matching 40-hex commit/readback and true flags. This retains evidence; the runtime does not independently verify Git signatures or network operations. |
| `send` | Responsibility owner: `packet,event,recipient,payload`, optional `correction_of`. Exact addressed adopted recipient; immutable identity/content. Send using the owning event, or have Work admit a separately addressed event. Correction creates another downstream duty and retains the original. |
| `inbox`, `receipt` | Inbox optional `limit`. Actual recipient receipts `packet,stage,evidence`, strictly `picked-up` then `processed` then `settled`. Exact receipt duplicates are idempotent; changed evidence conflicts. Payload/reference pickup does not assert processing or acceptance. |
| `resolve`, `finish` | Owner: `event,need,evidence`; then `finish {event}`. Whole processing requires ACK, every need resolved, all original attempts reconciled and all outgoing packets settled. Failed outcomes require explicit owner disposition, not conversion to success. |
| `hold`, `eligibility` | Owner: `event,name,enabled,evidence`; release assertions require actual holder authority outside this cooperative CLI. Eligibility `event` requires whole processing +86400 seconds **and all holds clear**. Late holds restore ineligibility. No deletion is authorized/performed. |
| `status`, `recover` | Finite status omits credentials/collector secrets. Every adopted owner can recover its own outstanding collector and launch operands. Work also sees foreign custody metadata, without foreign collector secrets. Never borrows handles, probes PIDs, retries effects or releases on elapsed time. |
| `readback` | `kind,id`; kinds `attempt,event,packet,effect,branch,review,package`. Read exact committed operands, payloads, classification, results, receipts and evidence. Attempt/effect/branch/review require their original owner; packet requires sender/recipient; event/package require Work or the responsibility owner. No process handle or external truth is reconstructed. |
| `partial` | `kind,id,evidence`; kinds `event,attempt,packet,effect`. The actual owner, addressed packet participant, or Work for an event records one attributable immutable partial report. Exact repeat is accepted; changed evidence conflicts. This reports unfinished work, retains the entire original record, and changes no ACK, need, attempt state, END, reconciliation, receipt, hold or completion clock. Further work does not erase the historical partial report. |

Phases and capacity are separate from provider execution. `classifier` belongs to
Work and is fresh per event. `known` belongs to Work/Branch and requires a stable
`point` with `point:ID` in the footprint. `discovery` belongs to Work, requires a
positive `new` classification and has one slot. Unrelated known work can run
while discovery is occupied. Read/read can overlap; any shared writer conflicts.
Branch known work must hold `branch:ID`; Reviews `review` work must hold its
bound `review:ID` and its associated `branch:ID`, and keeps its opaque contract.
Only the owning Reviews actor in review phase can append to that review's calls.
Predecessors retain the same owner, component, branch/incarnation binding and
opaque contract; a successor context is a new encounter. Exact duplicate
repository/ref/incarnation tuples use the existing branch ID. Different physical
aliases still require honest shared footprint declarations; no path census or
external ref CAS is implemented. `qa-execute` has five package
slots; one package cannot duplicate or execute and consolidate simultaneously.
`qa-consolidate` has its own single slot and requires successful reconciled
execution for that package. Definitely unstarted cancelled executions remain
recorded with END null and are excluded from the executed set. Cancellation
alone cannot qualify consolidation. A later actual success can qualify the same
package; any executed failure, unknown END, or unreconciled execution still holds
consolidation. Owners must declare the complete real footprint;
undeclared physical conflicts cannot be inferred from arbitrary payloads.

For actual adoption, Work creates/classifies an event, assigning responsibility
to its real owner. That owner uses its own adopted interface to consume, reserve,
record its actual encounter/result, send its result to the actual recipient, and
settle duties. Work may first keep a routing event itself and send addressed
packets whose recipients acknowledge pickup/processing/settlement. Genuine
Branch/Reviews/QA then need their own assigned events for new execution. This is
an explicit finite protocol, not automatic model dispatch.

## Wake, recovery, retention and resources

`watch --timeout 30` binds a separate Linux abstract datagram receiver for each
actor before the initial inbox scan. All four roles can wait simultaneously.
It returns addressed durable work or the inbox at its finite deadline, at most
60 seconds. An unrelated hint triggers a scan, then continues the same wait.
Hints contain no task payload, are lossy/coalescible and cannot authorize work.
Abstract names have bounded length and consume no filesystem socket entry.
Read/status scans do not wake themselves. Repeated model polling is unnecessary.
Only one receiver for a given actor may bind at once. The kernel releases its
abstract address when the original socket closes, including process death;
there is no stale-file deletion, PID inquiry or handle transfer. Durable packet
custody still needs recipient receipts. Without a listener, `inbox` and
owner `readback` on restart still read committed responsibilities.

After an interrupted reply, use `recover` and `readback` with the surviving
original actor credential and stable attempt ID. Preserve the returned collector
and launch ID with the actual original process object. A committed launch ID is
correlation, never proof a process did or did not start. Do not repeat `start` or
`run-fixture` for a launching attempt. Only the actual original collector supplies
its numeric END and reconciles effects. If no original process object/outcome is
available, leave the attempt held and return that gap. Revocation transfers no
custody. For a definitely unstarted reservation, `cancel` releases its logical
slot and retains the disposition; a subsequent attempt needs separate authority
and a fresh reservation. Control refusal before fixture Popen is recorded as
`not-started` before returning the error and may then be cancelled. Errors at or
after Popen, and missing commits, leave launch uncertainty held.

Collection, reconciliation, effect observations and need resolutions accept exact
evidence repeats and refuse changed evidence. Owner-scoped readback retains the
original result, numeric END, evidence and attributable timestamps. Resolution
history records actor, need, evidence and time; changed outcomes use a new
correction duty rather than overwriting old evidence. These records remain
cooperative assertions. Real owners and external holders must supply actual
actions and authority separately. Results are bounded to 4 KiB and addressed
packets to 8 KiB; larger original evidence stays with its actual custodian.
Intake payloads and integration deltas are each bounded to 4 KiB of encoded JSON.
Each event retains at most twelve hold assertions, including repeats. Additional
history is refused before mutation: keep that assertion with its actual holder
and record an honest partial report. No history is truncated, coalesced or reset.
Sixteen maximum supported need-evidence values, including escaped supplementary
Unicode, are bounded by encoded bytes, rather than a character-count estimate.

A cross-event correction depends on every ancestor packet's event. Creating it
reopens each completed ancestor, clears its old completion clock, and prevents
finish/eligibility until the correction settles. The original event owner must
then finish again, starting a new whole-processing clock. Transitive corrections
carry the same dependency; old evidence and packets remain. Metadata eligibility
still authorizes no deletion and releases no actual external hold.

A stable nonblocking flock protects only short finite metadata work. State is a
single checksummed snapshot, written to an exclusive same-directory file,
fsynced, replaced and directory-fsynced. No lock spans model/tool/worker execution.
Interrupted pre-replace files stay conserved, and the last committed snapshot
remains authoritative. Crash after commit/before reply may leave a committed
operation. There is no power-loss, distributed, hostile-writer or multi-file
external-publication atomicity claim.

A hash-chained append-only budget journal precharges state/control reads and
state writes/temporary entries. Limits are cumulative 128 MiB bytes, 128 MiB
logical read reservations, 1024 entry reservations, 256 KiB state, 512 KiB budget
journal. Failed/refused operations retain prior charges; partial budget records
hold rather than truncate/reset. Init control reads, public helper code loading,
caller I/O and external provider work remain the caller's enclosing allocation,
not a claim of whole-process/host resource measurement. Limits cannot be raised
or reset by this CLI. Metadata queries charge their actual bounded state read
and charge-journal read, without rewriting the snapshot or incrementing its
generation; do not status-poll. Ordinary work cannot consume the final 32 MiB
write allowance, 64 MiB logical reads, 256 creation entries, 128 KiB of the
journal, or final 64 audit records. The old 8192-byte/object and twelve-visit
successful-closure projection is removed. **Admission promises a finite supported
success or an accountable partial return**, not that every possible sequence of
successful actions fits. Every candidate mutation measures the actual complete
encoded state and leaves a conservative tail for each unfinished event, attempt,
packet and effect without a partial report: two discovery/readback visits and
one owner-attributed partial report. The tail bounds marker bytes, audit space,
snapshot writes, entries, state reads and growing charge-journal reads. The
snapshot's own imminent save is checked with the same remaining tail. New material
that would consume it refuses before snapshot commit, retaining the old record
and caller's original material. There is no refund, reset or per-epoch renewal.

Under ordinary pressure stop unrelated intake. `inbox`, `recover` (including
addressed packet IDs and authorized partial candidates), `readback`, `integrate`
and bounded `send` remain available alongside original-owner settlement. Useful
integration and downstream return can succeed; each still must fit its actual
encoded consequences and the partial tail. If a necessary result, assertion or
follow-up cannot fit, discover/read back the obligation and call `partial` with
its honest reason, preserving originals outside this finite metadata store. The
owning attempt/packet/effect remains outstanding: this is **not completion** or
permission to release a lane, settle an effect, fake acceptance, or drop a hold.
Do not report cutover success merely because every item has a partial report.

Tail capacity covers that finite visit sequence, not arbitrary duplicate reads,
invalid requests, contention retries, repeated successful duplicates or failed
writes. Such work remains charged; hard exhaustion, journal corruption, missing
authority or lost actual custody can still hold even readback/disposition. Return
these as explicit gaps with original owners. There is no universal recovery,
bypass or emergency reset.
A future long-lived epoch transition requires conservation/current-consumer and
budget authority; no automatic rollover is implemented.

Capacity checks subtract the imminent bounded allocation (rounded blocks and
metadata/entry slack) before requiring at least 16 GiB/100000 inodes on the OS filesystem and
1 GiB/2000 inodes on other selected filesystems. Checks observe, never reserve
capacity. Default original/source/effect/consumer/outbox/recovery/privacy/resource
holds require scoped holder evidence. All actual historical holds remain outside
this prospective state. No ACK, process END, report, commit or push starts a
retirement clock. Never use this runtime to clean old stores or provider history.

## Qualification and tests

`run-fixture` accepts only `{attempt,collector}` and launches the bundled finite
Python worker, holding pool admission and the supported fast-policy guard through
actual local process creation. `fast_tier.py set` cooperates on the same stable
`fast-tier.lock`; busy setters refuse and may be retried as refused control
operations. Direct/noncooperating file edits are outside that fencing contract.
At that second transaction the fixture also rechecks the current adopted actor
and credential. Intervening revocation refuses before Popen, recording definitely
not-started without inventing END or giving Work replacement-collector authority.
Failure at the Popen boundary remains launching/unknown, never cancellation proof.
It records actual numeric exit and synthetic result, not provider/role acceptance.
There is no arbitrary argv/shell API. `owner-encounter` only records an already
owned encounter; it does not launch or qualify that external substrate.
Reservations carry the required all-fast request and unobserved served tier;
actual provider argv/service-tier evidence remains a provider-adapter obligation.

Select the same actual public controls explicitly for runtime and setters:

```bash
python3 tools/direct-child/execution_pool.py --routes /home/nes/ai/tools/direct-child/routes.toml status
python3 tools/direct-child/fast_tier.py --routes /home/nes/ai/tools/direct-child/routes.toml get
```

The supported `fast_tier.py --routes ABSOLUTE_ROUTES set on|off` targets that
routes file's adjacent policy **and stable guard**, just as this runtime does.
Without `--routes`, the helper's existing adjacent-policy default is unchanged;
do not assume it names a different checkout's selected controls. Real shared
membership/counter remains at ROOT's actual shared routes, never a stale copy.
Standalone calls remain caller-owned: supply a positive finite allowance for
their lock/control/temp effects and check fresh capacity minus imminent growth
against the selected leave floors before invoking them. Runtime callbacks do not
cover independent CLI calls. This is not a whole-host resource platform or
qualification of other launch consumers or opaque provider internals.

Tests disable both SQLite module imports and fail on attempted use. The CLI
bootstrap is also executed under that guard; the fixed worker imports only stdlib
`json`/`sys`. The tested dependency boundary is these files plus the public pool
helper, not unexamined CLI/provider/private session internals.

```bash
PYTHONDONTWRITEBYTECODE=1 \
COORDINATOR_TEST_ARTIFACTS=/absolute/new/coordination/fixture-attempt \
python3 tools/coordinator-file-runtime/test_runtime.py
```

Every run needs a new bounded artifact root and keeps failed/interrupted files.
The suite uses synthetic actors, finite local processes, synthetic clocks,
actual overlap and crash exits, actual CLI subprocess execution, live fixture
pool changes, stale versions, responsibility/ACK, addressed receipts and holds.
The suite also distinguishes encoded Unicode/history limits, pressure discovery,
integration/return, preserved partials under real encoded-state pressure, QA
cancellation versus later success/failure, creation-time revocation versus
ambiguous creation, and the real public setter CLI at the fixed worker boundary.
No real actor, provider, external ref, CI, product release or actual data cleanup
is exercised. Check remaining material budget before repeating.

Required next encounters: independent consequence observation of this candidate;
real self-adoption and addressed packet/result acceptance by all four owners;
qualification of any indispensable provider/launcher path with SQL unavailable;
actual LOW provenance, opaque Reviews continuity, Branch commit/push/readback and
QA acceptance; then current customer-risk disposition by the real delivery owner.
External canonical publication, automatic model scheduling, safe resume after
owner exit, historical import, physical retention reclamation and automatic
budget rollover remain unsupported. Their needs stay explicitly owned/offline.
