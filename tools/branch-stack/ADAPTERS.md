# Adapters for the corrected combined core — read first

Read taskhome READFIRST.md, FULLreport.md and RETURN.json before intake. These
files describe the joined corrected core and adapters; see CORRECTIONS.md. No installation, native RFQ
composition, actual board post, actual pushed receipt, product semantic pass,
review approval or Ready claim is supplied.

## Compatibility and intake

Target: /home/nes/ai/tools/branch-stack. Add only the exact files in
SOURCE-ARTIFACT.json using full-candidate.patch in an owner-assigned isolated
checkout. This task has no branch/commit/Jira identity: the parent still owns the
existing association requested in Work9419. The full patch includes the corrected core and adapters.

adapter_support.load_core requires the exact corrected stack_controller.py
SHA256 9ad637dd6a3677b17894726e9f6e655f6f1b19e2ce8d9b3f4725fb18cfb697a0.
The correction task requalifies this hash/API jointly with the adapters.
Any subsequent hash/API change requires joint requalification; never silently repin.
Imports have no provider/state side effects.

Only these core interfaces are used: SCHEMA, token, oid, version, digest, fields,
Graph, plan, alerts, board_command, native_contract, owner_lock and DeliveryJournal. The latter
two remain the canonical lock/journal; no second task ledger or delivery journal
is introduced. Their retention frontiers (10000 checks, 2 MiB) remain unchanged.

Before startup: freeze source, selected metadata, provenance, controls and every
alias kernel read-only, with rootRO and BOTH exact reserved-calendar EMPTYRO
masks from the supplied selection. Dependencies/.pth are kernel RO. Python is
/usr/bin/python3 -I -S -B, with private proc/dev and /dev/null character 1:3.
Only new distinct output/runtime directories are writable. Do not expose the
whole taskhome or an existing journal namespace as a generic writable overlay.
The tests/frozen launcher show the qualification mounts, not a global host freeze.

## Bounded metadata feed

FeedAdapter receives the exact already-associated account/binding/repo from the
parent. typed(raw) accepts a branch-source-envelope/v1 with account, binding,
event_ids, scope {prs, complete_inventory:false}, and snapshot (stack-dag/v1).
event_ids are positional, unique and retained outside the strict core snapshot.
The complete typed producer envelope is written privately before projection.
Core validates exact heads/trees/ordered parents, Main, logical dependencies,
physical bases, singular membership, evidence and merge mappings. Flags and
failed evidence remain unchanged. No PR body/diff/comments/data getter exists.

native(raw, snapshot_id=..., associations=..., groups=..., segments=...) decodes
the already accepted Stack1649/Main metadata shape. Canonical IDs, ticket/campaign,
requires, content/resolution, provenance, evidence, admission and eligibility
must come from explicit parent associations. inner_git_units are retained as
opaque sidecar provenance; they never create duplicate feature units. No ticket
or signature truth is inferred from a branch name or Source-purpose string.

Unavailable tree/ordered-parent/base/canonical association returns snapshot=None
with exact gaps; the core cannot encode nullable trees/parents, so no fake OIDs
or empty-parent guesses bridge that mismatch. An explicit null stack conflicting
with its native entry is UNKNOWN. Provider merged flags alone never establish
landed ancestry. Accepted typed merge records can express verified bottom-up
partial/squash delivery; false/unknown mapping remains manual UNKNOWN.

The supplied six-entry structural fixture retains Main449e and order
1639 -> 1640 -> 1647 -> 1648 -> 1645 -> 1641, node PRS_kwDOOtFmdM4ALB_v.
It lacks trees/parents and is a PRIOR structural observation only. The curated
Source packet is kept via fixed_packet_binding as opaque materialization refs
and source-purpose strings. None of its linked stores are followed.
The six entries never become a complete branch inventory.

graphql_command builds an argv DTO for the accepted single stack plus Main and
only an explicit encountered PR list (1..100). It requests metadata, never body,
diff, comments, credentials, CI or global branch/org census. No gh request ran
here. The actual existing feed service locator, account schema and provider API
compatibility still need parent binding/readback. A static command test does not
qualify a live provider schema, current refs or native CAS capability.

apply_on_encounter consumes only the supplied bounded projection, not
ASSIGNMENTS.json or linked held objects. V1 is the default and requires explicit
caller trigger Booleans; missing decisions remain UNKNOWN. Deliberately select
DEFERRAL_V2 with the separately bound current Work decision/owner to consume the
supplied durable satisfied=false. Repository/PR/branch, Boolean, authority/basis
and until-supersession semantics are checked. A V1 caller cannot implicitly
consume V2. CORRECTIONS.md describes exact arguments and retained active obligations.
Unlisted units retain ordinary rules; there is no advance full inventory.
The corrected core preserves cloud_demo itself, so no repair duplicate is added.

## Native Git text probes

GitProbe(core, fresh_directory, timeout=10, max_bytes=64MiB, min_free=40GiB)
uses real /usr/bin/git. The installed 2.43.0 -h/--version capabilities are captured. Only explicitly
bound histogram diff/merge behavior is supported; other algorithms are rejected.
A separate native-oracle control found three pairwise-clean branches whose ordered
triple conflicts under these actual settings. Earlier merge-file/Myers assumptions
failed native tests and remain preserved, not relabeled as this result.
probe(snapshot, order, kind='pair'|'ordered', main_version=..., scope=...,
source_getter=...) returns native-git-probe/v1 plus a strict core probe when
representable. The full original stdout/stderr/native numeric exits precede the
safe path/status projection. FAILURE and UNKNOWN remain distinct in the native
envelope; a native failure maps to UNKNOWN in the core, never CONFLICT/CLEAN.

Scope must explicitly assert complete=true, objects_admitted=true,
backing_kind=owned-synthetic|positive-readonly-transport, admission_ref and a
closed path list. Each path needs ordinary PROGRAM or SYNTHETIC_FIXTURE role,
body_admitted=true and actual policy_ref. All selected counterparts must be
admitted before source_getter is called. Unknown path/body/counterpart/scope
stops before it. Ordinary dotenv/provider/model.py names are accepted when
positively ordinary; no filename/substring blacklist provides privacy authority.

source_getter supplies a bounded list of literal positively admitted COMPLETE
loose Git object backings: oid (SHA1 only), path, bytes, admitted=true,
role=ADMITTED_COMPLETE_GIT_OBJECT, policy_ref. No directory or alternate
discovery is used. ALL record capabilities are checked before any backing read.
Compressed and expanded sizes, object type/length and exact hash are checked.
A symlink or resolving alias, packed object, protected/mixed body, opaque-only
carrier, missing object, gitlink/symlink file mode, unknown path or unsupported
SHA256 repository stops. This adapter does not launder opaque protected native
objects into a complete-body admission. Real RFQ native inputs remain unsupported
until the parent supplies genuinely permitted complete positive objects and scope.

adapter_runtime.check_once joins decoder output, core observe/plan/alerts and the
injected sender under the same core owner_lock/DeliveryJournal. Incomplete native
bindings return UNKNOWN without fabricating a healthy result or a send.
native_operation_dto emits only the core Stack1649 operation/CAS contract.

Each probe creates a private bare repository from an EMPTY owned template.
It imports only named object bytes into its private database. No alternates,
source Git config, hooks, refs, index, worktree, remotes, global attributes,
system config, replace refs, lazy fetch, network protocols or inherited Git
environment are activated. core.fsmonitor=false, hooksPath=/dev/null,
attributesFile=/dev/null, protocol.allow=never, merge.renormalize=false,
gc.auto=0 and maintenance.auto=false are explicit. Highest-priority private
info/attributes forces merge=text and disables filters/diff/text conversion,
overriding tree-provided driver selection.

Pair probes directly merge two exact heads. Ordered probes fold from exact Main
through the explicitly selected unique order; each clean fold writes a disposable
virtual commit OBJECT only in the private object database, with exact ordered
left/right parents to preserve ancestry. No feature/public commit or ref is
created. Those virtual objects are not materialized feature units, signed tips,
native restacks or approval evidence. Shared canonical ancestors are not replayed
as independent feature units.

Every supplied head/tree/ordered-parent binding, exact Main and selected order is
checked. Conflict output is --name-only -z --no-messages and only already admitted
ordinary relative path locations are projected. Raw conflict bodies/errors stay
in private captures; no source/error dump is used for an alert.
CLEAN is textual only, semantic=false. The core consequently keeps the ordered
group UNKNOWN without separately admitted exact ordered semantic evidence.
This backend does not acquire or authenticate semantic/test evidence.

Per producer: <=20s wall deadline, 10s CPU, 512MiB address space, 64 FDs,
2MiB file-size limit, no core dumps. Timeout kills the process group and retains
the actual signal return. Per probe: <=100 selected units, <=10000 objects/paths,
8MiB compressed/expanded object cap, <=128MiB configurable owned logical disk
budget (64MiB default), <=300 captured launches, sampled >=40GiB free.
Disk checks are pre/post samples rather than an atomic filesystem quota or global
peak guarantee; a retained failed producer may reach a frontier before rejection.
No automatic cleanup/GC/reset occurs.

## Existing board command and receipts

BoardSender builds normal board.py open or a parent-bound directed reply using
structured argv, shell=False, exact --home/--board/session/recipient arguments and
isolated Python. It never registers a new account, chooses a profile, opens raw
DB/queue data, changes routes or supplies a foreign sender identity. current_actor
and CODEX_SESSION_ID must agree with sender; the parent authenticates that actual
context. A canonical sender cannot be the Branch recipient itself.

Production transport can be ProcessCapture.run. Qualification uses only the
explicit MockBoardTransport in tests. No actual board.py open/reply/help/import
was executed here; ordinary program source extents provide the CLI contract.
Normal open/reply emits a numeric post/thread ID, board/thread/post state report,
and notice IDs. The decoder accepts one directed queued/acknowledged notice and
returns ONLY ENQUEUED. Multiple notices, pending/failed/ambiguous states,
unexpected output, timeout or nonzero exit leave the core's attempt AMBIGUOUS.
Parent can bind a richer recipient-qualified provider decoder later; no missing
recipient ID is guessed from an arbitrary multi-notice report.
acknowledged notice state is ack-notice, never actual pushed model arrival.

Hold the SAME core.owner_lock while journal.observe/plan/alerts/deliver/reconcile
run. Give every scheduled occurrence a distinct check_id. send-<alert_id> evidence
directories carry immutable send-start anchors before crossing transport. The
core persists AMBIGUOUS before any send; same-check uncertainty never resends.
A new check with the same active violation still emits. Healthy checks are silent.
Do not suppress notifications by cross-check digest or content.

delivery_receipt validates parent-authenticated provider/QA/recipient metadata
against exact board/recipient/check/alert/notice/post/thread identities. PUSHED
requires explicit native model_arrival (or independently observed QA push), queue
identity and observed UTC timing. RECIPIENT_ACK/PASS additionally requires an
actual Branch-authored reply post, explicit native_push arrival mode, unique
check binding, independent QA verification and <=30 seconds from the immutable
actual send-start anchor. Test announcement must predate send. Future, backdated,
wrong-author, wrong-check and late events cannot pass.
Manual boardwatch/read, notify hints, queue acceptance and ack=true cannot pass
the pushed route. Existing smoke QA-BRANCH-ROUTE-20261102-01 / BranchACK9466
remains a failed pushed-route observation. No workaround relabels it.
Evidence authentication is parent-owned: arbitrary self-asserted JSON is not
independently authenticated by this library.

## Qualification and parent frontier

The correction task selects 36 core, 36 adapter and 27 regression cases against
the corrected hash, with two explicit original expectation replacements documented
in CORRECTIONS.md. See the task's actual test results, including failed rounds.
Tests use real stock Git positives and mocked external board transport only. Source/input files and aliases were kernel
RO at startup; synthetic fixtures were built in an earlier isolated producer
phase and frozen for qualification. tests/build_synthetic_fixtures.py creates
ordinary synthetic objects, one synthetic source ref and an index sentinel;
these are not RFQ refs or source. Tests confirm unchanged source bytes and RO.

The harmless generated countercontrol explicitly executes /usr/bin/touch through
its synthetic merge.evil driver; the safe backend returns conflict without
activating it. The countercontrol's synthetic config/runtime activation is
intentional and limited to generated ordinary fixtures and a fresh owned marker.

To rerun after receipt: use fresh writable fixture-build, per-suite result and
countercontrol directories. Build fixtures with Python -I-S-B and
ADAPTER_FIXTURE_HOME / ADAPTER_COUNTER_MARKER. Then freeze them and all source,
bind only fresh result/countercontrol outputs RW, and run tests/test_adapters.py
with ADAPTER_CORE_SOURCE, ADAPTER_FIXTURE_HOME, ADAPTER_TEST_RUNTIME,
ADAPTER_NATIVE_METADATA, ADAPTER_CURATED_METADATA, ADAPTER_DEFERRAL_METADATA,
ADAPTER_RESERVED_MASKS (JSON exact two paths). The taskhome frozen launcher and
evidence/019-corrected-joint-99 and subsequent recorded qualification methods show actual mounts/argv. Tests never run
against live RFQ objects or actual board transport.

Parent owns independent review reconciliation, proper branch/Jira/feed/account
association, positive real native input admission, existing canonical state
paths and ownership, actual provider schema/receipt binding, installation and
normal QA. QA must announce a live test and obtain actual pushed Branch reply
within30s, or report FAIL and actual snapshot to the current owner. No scheduler,
service, agent registration or five-minute monitor was installed here.
Retain all failed runs and producer envelopes. No deletion/retirement authority
is supplied; Root owns release/stability of both masked reserved stores.



## Reviewed occurrence, frontier and Git-format corrections

The R1 acceptance path binds the full immutable snapshot and adapter context to
an occurrence ID, computes observation/plan without persistence, and saves the
accepted observation and check together under the canonical owner lock before
transport. A changed occurrence input is rejected without any journal write.
`accept` returns stored plan/notices/receipt for exact historical replays without
re-observing or sending; `receipt(check_id)` retrieves a legacy check without
inventing a missing input binding. Legacy prepare-only rows cannot be adopted by
an unbound accept. A previously PLANNED runtime replay is receipt-only: callers
must use an explicitly bound delivery operation if intentionally dispatching an
unsent accepted check. AMBIGUOUS is still durable before sender entry; distinct
occurrences continue to repeat actual violations.

R2 runtime status is UNKNOWN for unresolved encountered policy/decoder frontiers.
Known violations and notices remain present and use the normal delivery path;
`known_violations` distinguishes these facts from qualification of the whole
check. The exact outside-explicit-pr-scope-UNKNOWN coverage marker does not make
an otherwise healthy bounded check UNKNOWN. No global PR inventory is required.

R3 this Git backend rejects non-SHA1 Main and selected head/tree/ordered-parent/
physical-base OIDs before initialization or source_getter. Its outer envelope
retains the unsupported-format reason when no strict core probe can be formed.
The core still accepts 64-hex metadata; content/resolution/version/evidence
SHA256 digests are not Git object-format operands. Native CLEAN remains text-only
and semantic=false. No SHA256 backend support or actual RFQ Git input is implied.

The existing F1-F5 and Work V2 boundaries remain. Parent targeted review of these
changed boundaries, commit/signing, installation, actual typed collector feed
binding and live QA remain separate. Prior QA FAIL / NOT WORKING and the later
Work9698 / notice9734 AMBIGUOUS observation are not passes.


## R1 publication and durability boundary

`DeliveryJournal.accept` separates rejection before `os.replace` from acceptance
whose directory durability is unconfirmed after replacement. The latter returns
`acceptance=ACCEPTED_DURABILITY_UNCONFIRMED` and
`persistence.durability=UNCONFIRMED`; it preserves the published observation,
check, notices and current memory. The persistence receipt binds the published
inode, exact serialized-byte SHA256, logical state digest and failing directory
OPEN or FSYNC stage. This describes visible publication, not survival of a crash.
No rollback overwrite is attempted. A pre-replacement error raises and retains
previous journal bytes/inode/memory; an existing or newly failed `.pending` stays
in place for owner disposition, never automatic deletion/reuse.

`save`, `observe`, legacy `prepare`, `deliver` and `reconcile` raise the typed
`JournalDurabilityUnconfirmed` after publication if directory confirmation fails.
Its `.outcome` contains persistence metadata; the same journal object's
`receipt_status(check_id)` returns the actual current row and current journal
persistence. The compatibility `receipt(check_id)` API returns ledger contents
only and never asserts durability. Observe-only publication has no new check row.
All journal mutations use the same pre/post replacement memory boundary.

`adapter_runtime.check_once` returns `status=INDETERMINATE`, persistence metadata,
actual delivery row, plan, alerts and independent `known_violations` when either
acceptance or a delivery save publishes without confirmed durability. It stops
sending. In particular, a sender is never invoked until the pre-send AMBIGUOUS
marker has completed file fsync, replacement and directory fsync. If uncertainty
arises after one sender effect, that effect cannot be undone: the current attempt
receipt and remaining ambiguous attempts stay visible for owner reconciliation.
No automatic transport retry follows an exception, a receipt lookup or same-ID
replay. Distinct checks still repeat violations, and healthy checks stay quiet.

The `once` CLI emits the structured accepted/indeterminate result on stdout and
exits **4** for post-replacement uncertainty. Existing codes **0** (no known
violations in the requested result), **2** (rejected/unavailable input), and **3**
(known problems) remain. A same-ID invocation is a **historical receipt lookup**:
it does not send or rewrite. On reopening a journal, its top-level acceptance is
`HISTORICAL_RECEIPT_ONLY`, and current durability is `UNVERIFIED_AFTER_REOPEN`.
Historical code 0/3 is not a new acceptance or a durability confirmation; callers
must consume `acceptance`, `replayed` and `persistence`, rather than treating
native code 0 as a generic durable-SUCCESS signal. This deliberately avoids
persisting a false claim that a previous directory fsync was confirmed.

## Explicit owner recovery (never an automatic resend)

Keep the canonical owner lock and stable directory entries. Retain the current
journal, pending artifacts and receipts; do not restore old bytes or overwrite a
newer occurrence. Reopen and inspect `receipt_status(check_id)`, including known
notices and attempt receipts. Call
`confirm_durability(expected_state_digest)` with that exact logical state digest
under `owner_lock(..., journal_path=...)`. It verifies current file contents and
inode against memory, fsyncs that file and its directory, and returns the bound
current byte SHA256/inode with `durability=CONFIRMED`. It does not replace,
rewrite, erase a pending file, reinterpret a snapshot, or send. A different state
is rejected. A directory failure remains typed unconfirmed uncertainty; another
explicit recovery may be attempted after repairing the storage problem.

The equivalent foreground command is:

```text
python3 -I -S -B stack_controller.py recover --journal /exact/journal \
  --lock /exact/lock --owner OWNER --check-id CHECK --state-digest STATE_DIGEST
```

Recovery validates the requested row before sync. On success it returns
`receipt_status` and code 0; post-publication directory uncertainty returns code
4 and a structured persistence outcome. For a PLANNED row known not to have
crossed transport, an owner may explicitly choose `deliver` only after confirmed
recovery. For AMBIGUOUS or partially delivered rows, independently obtain and
reconcile qualified receipts; `deliver` will not resend that row. Successful
recovery alone never schedules or executes delivery. Across a subsequent reopen,
durability is again conservatively unverified until explicit confirmation or a
new durable save; historical replay remains transport-free.

Parent integration must update all pinned loader/startup source hashes to the new
core, accept the new top-level persistence/acceptance fields and runtime
INDETERMINATE status, and route that status to an owner recovery decision while
retaining known violations. The 23-file candidate keeps the journal on-disk
schema `stack-delivery/v1`; no migration is required. Join these changes with the
separate collector additions only after the current sole writer closes. This
candidate supplies no shared-index, commit, install, board, provider or scheduler
authority. Process death/resource exhaustion can prevent any response from being
emitted: reopened state is therefore never silently treated as durable success.

## Current joined consumer (WORK-20261102-BRANCH-STACK-SEGMENT-DAG-TOOLS)

`EXISTING-COLLECTOR.md` defines current producer, source-access, scope binding,
normal readonly Git and activation semantics; it supersedes historical admission
restrictions here. Core pin9ad637dd is the independently supplied durability
correction, byte-identical at join. Current runtime treats every persistence value
other than CONFIRMED as INDETERMINATE, preserving acceptance/persistence, actual
rows and known notices. The collector CLI returns4 and supports explicit producer
code-version and owner-fact input. Historical core CLI0/3 replay remains a receipt,
not a durability claim. Source filename/carrier filters are not policy authority.
