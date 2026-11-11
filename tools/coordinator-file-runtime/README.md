# Prospective file coordinator, schema 1

This runnable Python 3.11+ CLI/library admits finite new Work, Branch, Reviews
and QA responsibilities without a database or legacy-board adapter. It is a
candidate for scoped role operation, not a demonstrated complete four-role cutover. It never opens
old runtime state. No migration, release, arbitrary command execution,
exact-session resume or retained-data deletion is supported. A finite Codex direct
entry is described below; useful current Branch/Reviews operation still needs
its own grant and actual evidence. Earlier LOW and fixed software-QA encounters
retain their finite scope, described below.

The selected failure model is cooperative same-user Linux processes, local
filesystems with flock/rename/fsync, and process interruption. Credentials
separate cooperative actors; they do not authenticate a human/session against a
hostile same-user writer. Each actual role program must perform its own adoption
and supply genuine evidence. Task-local actors can do new work; participation by
older persistent owners is not a completion gate. Their actual duties,
credentials, originals and uncertain effects remain theirs. Synthetic identities in tests are not
real role acceptance.

## Start and self-adopt

Use the existing checkout's `tools/coordinator-file-runtime/coordinator.py`.
Set `PYTHONDONTWRITEBYTECODE=1` to avoid caches. The new dedicated state directory
must not already exist; its parent must exist. State ancestry must contain real
directories and the state directory is own 0700. A suggested prospective path is
`/home/nes/.local/state/coordinator-file-runtime/cutover-20261110` with an
explicitly prepared parent. This implementation has not initialized that path.

The basic non-stdlib dependencies are the public siblings
`../direct-child/execution_pool.py` and `../direct-child/fast_tier.py`.
The explicitly selected fresh Reviews path also uses the existing public
`dispatch.py` opaque capability and its `profile_lease.py` import. It does not
invoke the dispatcher or the legacy coordinator. Supply the admitted public routes file
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
`target`, one of `Work`, `Branch`, `Reviews`, `QA`, or external `Root`,
`invitation_token`, and `basis`.
The actual recipient then invokes `adopt` with its own credential and encounter
`basis`. Invitation alone establishes no adoption. Do not enroll another actor
as if it had encountered this interface.

`Root` is the existing external implementation/result holder, not a fifth
coordinator. It can receive addressed Work packets, receipt its own pickup,
processing and settlement, and return results on its own assigned events. Work
must classify and assign its known-repair event before Root can reserve known
point work. It cannot invite actors, classify/ACK, create QA packages, administer
Work, bind Branch or Reviews, take discovery/QA/review lanes, or borrow another
collector. Use the actual assigned implementation holder's identity; synthetic tests confer no
real adoption or authority. Failure results and unresolved original custody stay
with that original holder.

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
| `start` | `attempt,collector,substrate,evidence`. `fixture`, `owner-encounter`, or `codex-direct` correlation. Rechecks current pool and all-fast policy. Durable `launching` and unique `launch_id` precede effects. No second launch from launching/collected state. This record alone proves no process creation. |
| `collect` | `attempt,collector,launch_id,end,result,evidence`. Same original collector and launch correlation, actual numeric END required. Failures remain failures; result text grants no acceptance. |
| `provider_report` | Original collector: `attempt,collector,report`, optional `not_started`. The bounded adapter's immutable stage/capture/publication evidence (4 KiB); no semantic acceptance or process creation is inferred from this cooperative record alone. |
| `cancel` | `attempt,collector,evidence`. Original owner can disposition a `reserved` attempt or a fixture's durably recorded `not-started` control refusal. No numeric END is invented, no pool turn is refunded, and no new reservation is made. Launching/uncertain attempts and attempts with effect records refuse. Exact repeat returns its disposition; changed evidence conflicts. |
| `classify` | Work: `event,attempt,collector,classification,owner,needs`. Collected successful fresh `luna-low` classifier result must equal `{event_hash:SOURCE_HASH,classification:KIND}`. Kinds: `known,new,unresolved,control,coalesced`. Current adopted owner and 1..16 explicit needs become durable together with LOW provenance. Provenance is supplied evidence, not provider attestation. |
| `ack` | Work: `event`; refuses until classification **and** responsibility are durable. Lost ACK can be retried without repeating classification. Unresolved/control/coalesced retain their needs and cannot enter ordinary known/discovery work. |
| `branch` | Branch: `branch,repository,ref,incarnation,root,basis`. Immutable prospective association; a new incarnation needs a new ID. These are owner-supplied bindings, not Git mutations or independent verification of Root acceptance. |
| `review` | Reviews: `review,component,branch,opaque_contract,context,history`, optional `predecessor,execution_contract`. Preserves separate component/run/history references and calls; successor is explicitly a **new** encounter. `execution_contract:"fresh-current-component-v1"` explicitly selects the bounded fresh provider path for `opaque_contract:"gpt-xhigh"`. Omitted selection remains record-only and refused by `run-provider`. Does not resolve opaque selectors or manufacture a resumable session. |
| `package` | Work: `package,event,scope,basis`; admits a classified known event owned by QA. QA reserves this exact event/package. |
| `integrate` | `attempt,collector,writes`. Collected numeric-zero attempt, still-owned attempt, complete current version basis and admitted write footprint required. Commits only coordinator deltas/generations; unrelated resources remain unchanged. External canonical files/Git refs are **not** mutated or certified current by this operation. |
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
Work and is fresh per event. `known` belongs to Work/Branch/external Root and requires a stable
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
`qa-consolidate` has its own single slot and requires at least one collected,
reconciled execution for that package. Definitely unstarted cancelled executions
remain recorded with END null and are excluded from the executed set; cancellation
alone cannot qualify consolidation. Reconciled failures retain their numeric END,
evidence and effects and can be truthfully consolidated, including alongside a
later success. Unknown or unreconciled execution and unsettled effects still hold
consolidation. Consolidation and later success do not imply independent positive QA
acceptance. Owners must declare the complete real footprint;
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
Integration is an explicit decision by the authenticated cooperative owner. The
owner must independently validate the delta against current material, its full
basis and write footprint, and retain the actual validation and provenance. If
current proof is missing, hold or return partial evidence rather than integrate
from an incomplete marker. An incomplete Model result remains incomplete: numeric
END 0 alone is not Model success, a recovered proposal, or QA acceptance. The
mechanical integration gates do not verify the owner's semantic assertions, and
integration does not itself establish an external publication or QA acceptance.
Useful independently verified evidence need not be discarded or blindly replayed.

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

`run-provider` accepts exactly `attempt,collector,prompt,cwd,output_limit,timeout,
declared_secrets` in JSON stdin. It consumes an existing reservation; it never
allocates another turn, resumes, falls back, searches accounts, or invokes the
legacy dispatcher/launcher. The production executable is fixed to `codex`.
Input is limited to 16 KiB, output capture to 1024..65536 bytes per process, raw
output acquisition to four times that limit plus one 4096-byte read, and each
original to 1..3600 seconds. Timeout/overflow kills only the newly created owned
process group and collects that original. No prompt, raw log or provider-written
final file is published. The caller supplies its positive enclosing allowance;
these in-memory bounds do not measure opaque provider storage or tools.

The runtime-specific entry supports fresh `luna-low` from the frozen static
`routes.explore` Codex model with supported low effort, and technical `sol-xhigh`
from `routes.refine` with supported xhigh effort. It requests fast and ephemeral
execution. Served tier is unobserved. Explicit fresh current-component Reviews
can use the opaque contract below. Legacy/unselected Reviews and historical
session continuation remain unsupported and held before task creation. A required
unsupported job stays unfinished, never silently routed through technical work.

### Fresh current-component Reviews

Decision16 selects `fresh-current-component-v1`: each call is a fresh ephemeral
encounter requesting opaque `gpt-xhigh`, with explicit attributed continuity.
This does not select the separate protected continuing-review composition or
historical private-session resume. After actual self-adoption, the Reviews
program creates a new review record with these fields (substitute the actual
current component, Branch binding and authored context/history references):

```json
{"review":"current-review","component":"runtime-provider","branch":"current-branch","opaque_contract":"gpt-xhigh","context":"current-material-and-question","history":"authored-prior-evidence-reference","execution_contract":"fresh-current-component-v1"}
```

An optional `predecessor` preserves the existing same-owner/component/branch/
opaque-contract checks. It associates evidence without resuming that session or
changing the predecessor's execution selection. Unknown execution selections or
another selector cannot opt into this contract. Older records remain unchanged.

Work must first classify and ACK an event assigned to the actual Reviews actor.
That actor reserves `phase:"review"`, its exact `review` ID, a write footprint
for `review:ID`, its actual branch footprint, and all current resource versions.
It calls the existing `run-provider` entry using its original reservation and
collector. No extra allocation, fallback, account search or lifetime renewal is
performed. The public `open_opaque_execution`/`prepare` boundary consumes the
already admitted frozen control bytes and original reserved profile; only
ordinary provider internals prepare execution. Neither the consumer nor its
report resolves or attests the underlying model/provider/effort binding. A
missing or incompatible capability refuses before any preflight/task process.

The task receives a JSON envelope with `review_execution` and `task` fields.
`task` is the caller's sanitized prompt string. `review_execution` carries the
component, opaque selector, context/history, complete Branch association and
incarnation, predecessor context/history, prior call IDs, attempt/event and
resource footprint/version basis. These are explicit references, never followed
to private stores. The caller supplies sufficient admitted current material and
authored history in its task; a reference is not proof of reading or review.
The complete envelope must fit 16 KiB. Declared secrets in association fields
refuse execution rather than changing those references. The provider report
retains the opaque request and association digest, fresh status and lack of exact
session resume; original results/calls retain their separate custody.

All existing pool/fast/current-authority creation guards, effective MCP checks,
secret-aware bounded capture, numeric-END and lost-reply rules apply. This path
inherits the cooperative `codex-direct` trust model and its approval/sandbox
bypass; it supplies no enforced read-only, tool/network protection, independent
semantic judgment or actual operating qualification. The concrete grant must
bound the real task and effects. An ordinary review remains observation-only;
its result does not authorize source correction or integration.

The existing Branch path is unchanged: bind a new actual branch/incarnation,
assign a known event, reserve `point:ID` and write `branch:ID` with current
versions, then use the technical entry under a concrete grant. Original owners
perform and verify external Git actions separately; `reconcile` only records
their commit/signature/push/readback evidence. Disjoint known work may overlap a
review; shared writer footprints still conflict. Useful artifacts, independent
review, addressed result receipts and current-material disposition remain owed.

Effective MCP discovery is bounded, followed by individual disable flags plus
the injected docs disable/transport flags and an exact all-disabled readback.
These are original local processes too. Every actual creation rechecks current
adopted actor/credential, original collector, reserved profile, current enabled
pool, frozen static binding and the routes-adjacent fast guard. The short guards
cover Popen and never the provider run. Precreation refusal is recorded as
definitely not-started with no END; ambiguity at Popen or after creation stays
launching/held. A lost publication reply requires readback, never relaunch.
The adapter's `originals` list retains actual Popen objects before reading output;
callers using the library should retain the adapter across failures.

Declare at most 30 secret values of 1..512 UTF-8 bytes. The adapter also protects
its runtime credential and original collector. Literal and standard JSON-escaped
forms are redacted across read boundaries before bounded capture/result
publication, and the prompt is sanitized before stdin. Final JSON is sanitized
again after decoding. Parent environment inheritance is limited to original
HOME, original reserved CODEX_HOME and a fixed PATH; no parent runtime token or
arbitrary secret environment is forwarded. This supports declared values, not
a universal detector or protection against an adversarial transformed encoding.
The public Codex executable is located through the caller's ordinary PATH before
building the minimal environment. No profile/config/auth/account-availability
probe is performed by the adapter itself.
Production MCP commands are provider operations and need actual operating
authority; Maker tests execute fixed public processes only.

Only one completed agent-message containing JSON is accepted as a final result,
at most 4 KiB. Missing, multiple, oversized or incompletely captured finals
produce an explicit incomplete result. `provider_report` retains stage numeric
ENDs, input/capture completeness, timeout/overflow, and final completeness within
4 KiB separately from the task END, effects, reconciliation and semantic QA
acceptance. A complete final can accompany a failed numeric END. Publication
failure preserves launch uncertainty and original custody; it never triggers a
raw output fallback. CLI stdout publishes only the ordinary bounded runtime
response, not provider output. Provider/platform internals, SQL independence,
actual response/service tier for a new call and complete four-role operation
remain unqualified by these tests. Earlier real encounters do not qualify a new
candidate or attest opaque provider internals.

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

# Separate fresh root, same enclosing allocation:
PYTHONDONTWRITEBYTECODE=1 \
COORDINATOR_TEST_ARTIFACTS=/absolute/new/provider-fixture-attempt \
python3 tools/coordinator-file-runtime/test_provider.py

# Focused fresh Reviews/public opaque-boundary tests, separate retained root:
PYTHONDONTWRITEBYTECODE=1 \
COORDINATOR_TEST_ARTIFACTS=/absolute/new/review-fixture-attempt \
python3 tools/coordinator-file-runtime/test_review_provider.py
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

The earlier published basis 5729edace6ee99f92c496edc40408a3be124945e has reported
real Work LOW encounters and genuine independent acceptance of the 52-case fixed
software-QA5 encounter. Both QA packets settled and Work completed its own grant
event at 1794373595.2076478, with all eight holds retained. That evidence and the
independent 71-case qualification remain reusable at their actual prior scope;
they are not a run against this changed candidate. No automatic QA5 repeat or
old-owner acknowledgment gate follows.

Required next encounters: independent consequence observation of this candidate;
then a concrete bounded original-controlled operating grant, actual task-local
role self-adoption and useful Branch/independent Reviews work through the public
pool, with actual outputs, original collection, addressed receipts and current
material disposition. Root owns the final scoped risk/completion decision.
Fixed-process tests establish neither actual model execution nor review quality.
External canonical publication, automatic model scheduling, safe resume after
owner exit, historical import, physical retention reclamation and automatic
budget rollover remain unsupported. Their needs stay explicitly owned/offline.

## Bounded software QA execution peer

`software_qa.py` supplies the software receiver/controller selected by Decision08
B. It runs software tests; the existing Work-designated QA actor remains the
independent semantic acceptor. The implementation Maker is not that controller.
No operating identities or grants are supplied by this source or its tests.
This is the cooperative Linux failure model above, with trusted fixed public
tests, not a security sandbox or a general command runner.

Work invites the actual running instance as a separate `QA` execution peer using
`invite`. That instance performs its own `adopt` with its invitation credential
in `COORDINATOR_TOKEN` and a truthful encounter basis:

```bash
python3 -B tools/coordinator-file-runtime/software_qa.py \
  --state /absolute/selected/state --actor ACTUAL_EXECUTION_PEER adopt <<'JSON'
{"basis":"actual software instance and job receive encounter"}
JSON
```

The instance exposes the same finite JSON stdin receive point with command
`run`. Its input is exactly `{"grant":WORK_ISSUED_OBJECT,"declared_secrets":[]}`;
no shell, arbitrary argv, API, model/profile lookup or legacy Board adapter is
available. The actor and state are explicit arguments. The token is never an
argument or a grant field. Only the following version 1 grant is supported:

| Fields | Work must issue |
| --- | --- |
| `schema`, `procedure` | `1`, `runtime-provider-unittest-v1` |
| `job`, `attempt`, `event`, `event_source_hash`, `package`, `scope` | Current software job, exact original attempt, acknowledged QA-owned event/source hash, admitted package and scope |
| `source`, `policy`, `authority` | Current Source, selected policy and authority references, carried unchanged into candidate, run and delivery; package basis must equal authority |
| `config_actor`, `controller`, `workers`, `acceptor` | Current Work configuration authority, actual receiving peer, five issued worker bindings, designated independent acceptor. The acceptor must differ from every worker, controller and configuration actor. Controller and workers may share the execution peer identity; actual program/PID/partition bindings distinguish their processes. Root keeps its own role. |
| `repository`, `commit`, `inputs`, `program_sha256` | Explicit authorized public repository, immutable full 40-hex commit, complete path-to-SHA256 input manifest and actual running program hash |
| `retained_root` | New exclusive absolute original-attempt root under an admitted existing parent. Never repoint a candidate/digest to another attempt root. |
| `inventory`, `partitions` | Complete current selected runtime/provider testcase IDs, and exactly five nonempty disjoint lists covering them once. Work selects the actual inventory; the program independently discovers both modules and retains differences. |
| `execute_attempt`, `consolidate_attempt`, `resources`, `basis` | Two distinct fresh core attempts and their complete current resource footprint/generations |
| `limits` | Exactly `workers:5`, `seconds:1..300`, `capture_bytes:4096..65536`, `output_bytes:1048576..12582912`, `output_entries:32..4096` |
| `receive_packet`, `result_packet` | Exact issued addressed grant packet and unique result packet ID |

Work must create a packet on its own assigned intake event, addressed to this
peer, with payload exactly `{"software_qa_grant":digest(grant)}`. `digest` is
`storage.digest`: SHA256 of sorted compact JSON plus newline. Work separately
admits the QA-owned event/package. The receiver verifies the packet's actual
sender, current Work/peer/acceptor authority and package/source/scope bindings.
A role label by itself supplies no grant or acceptance. The actual acceptor must
self-adopt under its own identity before it can receive delivery.

The fixed public input whitelist is `software_qa.PUBLIC`: coordinator, runtime,
storage, provider, fixture worker, runtime/provider tests, this client, and the
two public pool/fast helper scripts. All ten paths must be present with exact
hashes. Export uses only regular tracked Git blobs at the issued immutable
commit; links, extra/untracked paths and changed hashes refuse. It never exports
working files, private stores or Git metadata. The complete manifest retains
Git blob IDs, byte lengths, modes, hashes, grant, Source, policy, authority and
original root. Exported files and code directories are read-only; fixture
outputs are a separate admitted area. Input bindings are checked before and
after execution and consolidation. Read-only permissions are cooperative byte
protection, not hostile same-user isolation or semantic adequacy of a harness.

One package `qa-execute` reservation owns a fixed Python controller process. That
controller starts exactly five direct QA workers concurrently and records every
original `Popen` object before reading/filtering output. Every creation rechecks
current actor/credential, original collector and public admission controls; no
provider is invoked. The receiving instance retains the controller's original
object and collects its real numeric END. Each worker binds its actual PID,
controller PID, issued worker identity, program hash, partition and grant. The
fixed unittest procedure records actual case IDs/statuses, discovery/setup
errors, missing/duplicate cases, skipped/expected-failure results and incomplete
collection. A count alone never supplies completeness.

Within each of those five workers, each fixed test module gets fresh test-module
globals, its own fixture directory and the original outer SQL import blocker.
Provider tests import fresh runtime fixtures; they cannot inherit an earlier
runtime negative control's accumulator or mutate the earlier runtime suite's
actor fixture. The module's original SQL checks and test oracles remain intact.
This uses no additional test workers and accepts every valid five-partition
selection, including one pairing the intentional SQL control and provider's
empty-accumulator assertion.

A separate `qa-consolidate` attempt then owns one new Python process. It consumes
exactly five current partition record digests with the same candidate, grant,
job, original attempt and retained root, checks discovery/actual case accounting
and returns failures and unknowns unchanged. A consolidation process can END 0
while truthfully reporting failed tests. The outer receiver adds both actual
process collections, full partition records, manifests, grant and input facts
to `outputs/runner.json`; its exact complete `storage.digest` is delivered to the
designated actual acceptor through `send`. Delivery carries the current bindings
and original root. Overall `outcome`, `failures` and `unknowns` include both actual
stage collections as well as the corresponding case/input results. Success
requires complete collected controller and separate consolidator numeric END 0
and complete successful cases with current input bindings. A flushed success
result followed by a nonzero END remains preserved beside that END and yields
failure in the stage, runner, returned summary and delivered packet. Missing or
incomplete collection stays held/unknown; it cannot supply success.
No program here issues a semantic acceptance decision. Only
the genuine acceptor can judge the corresponding successful current run and
receipt its own pickup, processing and settlement.

Capture is secret-aware and bounded in memory per process; raw acquisition stops
at four times the capture allowance plus one 4096-byte read. Declare up to 30
literal/JSON-escaped secrets; the current credential/collector are also protected.
Timeout, overflow, interruption, missing result, creation ambiguity, lost
collector and partial publication stay held. Workers have a finite self timer
if their controller is lost. Never relaunch a `launching` attempt, reconstruct
PIDs/procfs, retry a failed effect, switch accounts or reset budgets. Keep the
`Peer` and `Processes` objects when using the library. Source Git processes are
also original objects, with bounded outputs and no diagnostics published.

The five-worker limit counts direct test workers. Existing fixed tests also own
finite subprocess/multiprocessing fixtures; their original collection remains
with those procedures. This client does not inventory a process tree or enforce
host-wide/opaque-descendant limits. Output byte/entry accounting is over its new
controlled output tree and detects exceeded grants; it is not a preemptive disk
quota for hostile code or a physical-I/O measurement. Work must admit the fixed
inventory's fixture effects and enclosing capacity before an operating grant.
Public source export is capped at 1 MiB; grants and CLI receives at 32 KiB.
These limits do not renew the runtime's separate cumulative admission budget.

If a genuinely collected run's delivery/receipt metadata reply is lost, use the
same grant with command `settle`, input exactly `{"grant":WORK_ISSUED_OBJECT}`.
This verifies the retained runner and current core collection digests and only
repeats idempotent metadata operations; it cannot spawn or replay workers.
It does not recover missing originals or partial publication. Actual result
receipts, need resolution, whole processing plus 24 hours AND all holds remain
separate from numeric END, ACK, delivery, report and push. No automatic deletion
or budget-epoch rollover exists.

Run the complete local software suite with a new admitted root:

```bash
mkdir -m 700 /absolute/new/coordination/software-qa12-tests
PYTHONDONTWRITEBYTECODE=1 \
COORDINATOR_TEST_ARTIFACTS=/absolute/new/coordination/software-qa12-tests \
python3 -B tools/coordinator-file-runtime/test_software_qa.py
```

The suite uses clearly synthetic identities and controlled tiny public Git
repositories. It includes the actual client entrypoint executing every selected
current core runtime/provider case through five partitions, a real failing test
with separately successful consolidation END, numeric original collections,
actual controller/consolidator END 17 after complete result publication, an
accepted partition pairing the runtime SQL control with the provider assertion,
and a genuine unexpected SQL import that still fails under module isolation,
frozen input/tamper checks, SQL-block negative controls, digest/receipt
correspondence, creation/publication ambiguity and settlement without replay.
It performs no real operating adoption, model call, independent semantic
acceptance, CI or cutover. Returned source/tests still require independent
observation, Frame and Root disposition before Work issues an operating grant.
