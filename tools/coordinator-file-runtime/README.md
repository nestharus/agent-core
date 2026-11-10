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

The sole non-stdlib runtime dependency is the public sibling
`../direct-child/execution_pool.py`. Supply the admitted public routes file
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
characters, string references at most 2048 characters, audit at most 512 changes,
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
| `status`, `recover` | Finite status omits credentials/collector secrets; Work recovery lists outstanding original custody, uncertain effects, incomplete and unacknowledged events. Never borrows handles, probes PIDs, retries effects or releases on elapsed time. |

Phases and capacity are separate from provider execution. `classifier` belongs to
Work and is fresh per event. `known` belongs to Work/Branch and requires a stable
`point` with `point:ID` in the footprint. `discovery` belongs to Work, requires a
positive `new` classification and has one slot. Unrelated known work can run
while discovery is occupied. Read/read can overlap; any shared writer conflicts.
Branch known work must hold `branch:ID`; Reviews `review` work must hold its
bound `review:ID` and keeps its opaque contract. `qa-execute` has five package
slots; one package cannot duplicate or execute and consolidate simultaneously.
`qa-consolidate` has its own single slot and requires successful reconciled
execution for that package. Owners must declare the complete real footprint;
undeclared physical conflicts cannot be inferred from arbitrary payloads.

For actual adoption, Work creates/classifies an event, assigning responsibility
to its real owner. That owner uses its own adopted interface to consume, reserve,
record its actual encounter/result, send its result to the actual recipient, and
settle duties. Work may first keep a routing event itself and send addressed
packets whose recipients acknowledge pickup/processing/settlement. Genuine
Branch/Reviews/QA then need their own assigned events for new execution. This is
an explicit finite protocol, not automatic model dispatch.

## Wake, recovery, retention and resources

`watch --timeout 30` binds an owned datagram receiver before the initial inbox
scan and returns current durable inbox on a hint or after at most 60 seconds.
Hints contain no task payload, are lossy/coalescible and cannot authorize work.
Linux `/proc/self/fd` directory addressing avoids Unix socket pathname limits.
Read/status scans do not wake themselves. Repeated model polling is unnecessary.
An existing socket, including one left after interruption, refuses binding;
there is no blind stale-socket deletion. The socket's actual owner must reconcile
that separate cleanup. Without a listener, `inbox`/`recover` on restart still
read committed responsibilities.

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
or reset by this CLI. Metadata reads also consume budget; do not status-poll.
A future long-lived epoch transition requires conservation/current-consumer and
budget authority; no automatic rollover is implemented.

Capacity checks leave at least 16 GiB/100000 inodes on the OS filesystem and
1 GiB/2000 inodes on other selected filesystems. Checks observe, never reserve
capacity. Default original/source/effect/consumer/outbox/recovery/privacy/resource
holds require scoped holder evidence. All actual historical holds remain outside
this prospective state. No ACK, process END, report, commit or push starts a
retirement clock. Never use this runtime to clean old stores or provider history.

## Qualification and tests

`run-fixture` accepts only `{attempt,collector}` and launches the bundled finite
Python worker, rechecking pool admission through actual local process creation.
It records actual numeric exit and synthetic result, not provider/role acceptance.
There is no arbitrary argv/shell API. `owner-encounter` only records an already
owned encounter; it does not launch or qualify that external substrate.
Reservations carry the required all-fast request and unobserved served tier;
actual provider argv/service-tier evidence remains a provider-adapter obligation.

Tests disable both SQLite module imports and fail on attempted use. The CLI
bootstrap is also executed under that guard; the fixed worker imports only stdlib
`json`/`sys`. The tested dependency boundary is these files plus the public pool
helper, not unexamined CLI/provider/private session internals.

```bash
PYTHONDONTWRITEBYTECODE=1 \
COORDINATOR_TEST_ARTIFACTS=/absolute/new/projects/fixture-attempt \
python3 tools/coordinator-file-runtime/test_runtime.py
```

Every run needs a new bounded artifact root and keeps failed/interrupted files.
The suite uses synthetic actors, finite local processes, synthetic clocks,
actual overlap and crash exits, actual CLI subprocess execution, live fixture
pool changes, stale versions, responsibility/ACK, addressed receipts and holds.
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
