# Startup evidence and normal service control

`processing-service-control` opens the existing runtime journal read-only. It
checks its initialized schema and current configuration without initializing,
migrating or taking a write transaction. The existing Work actor, processing
capability, configuration and continuing-service checks precede every request
to the original Unix socket. Status, recovery and close-review additionally
require the selected release and implementation to remain current. The original endpoint retains its same-UID
and exact-capability checks. A successful stop response means draining; the
parent still owes the original numeric process END and subsequent disposition.

`processing-service-control CAP stop` has a separate, withdrawal-only authority
check. A required public dependency update (including an added privacy hold) or
changed implementation cannot strand the authenticated original Work issuer.
Stop still requires the exact unrevoked capability, unchanged current journal
configuration, a continuing selection and exactly one matching original service
run in `serving` with an `owned` processing run and no recorded return. The CLI
opens only the existing read-only journal and authenticates Work using the
existing session checker. It checks that authority again after connecting,
verifies the endpoint peer UID and requires the response's controller to match
the recorded original. It sends only the existing stop protocol, so an already
running older endpoint needs no patch or second service.

For this exact component-free stop command, full config loading validates
`repository_reads` against the original selected `operator_cli` repository,
without inspecting that repository or rewriting configuration. A separately
reviewed compatible client can therefore withdraw its owner's original service.
Read-only source-task shape, role and effect checks remain mandatory. All other
commands retain executing-checkout validation; the withdrawal validator grants
no task, source, admission or publication authority.

After authorized source review and deployment selection, the genuine issuer
runs the corrected client's `coordinator --config ACTUAL_CURRENT_CONFIG
processing-service-control EXACT_CAP stop`, retaining the old journal/config and
original collector. No identity environment is fabricated. `--component` is
refused for stop. The acknowledged response reports `process_END: null`,
`processing_complete: false` and release currentness as unestablished. It does
not bless the old release, clear a hold, revoke a grant, release a run or authorize
admission, recovery, publication or any other effect. A refused/mismatched or
lost reply leaves stop effects unknown; there is no automatic retry, signal or
socket fallback. The original parent must collect its same actual process and
whole return, then use the existing guarded release/transition procedures under
their own current authority. A revoked capability, changed journal config,
returned/missing original or unavailable endpoint is a bounded refusal requiring
outside disposition, never permission to borrow another owner or infer END.

The isolated `test_owned_drain555` checks real release-file pin invalidation,
owner stop through the normal CLI/socket, read-only control during a WAL writer,
actual collection of its own stdio child and conservation of source/ACK/holds.
It also checks wrong/absent actor, cap/issuer/revocation/config/run mismatches,
continued non-stop refusal and failed endpoint acknowledgements. Native Board
membership, config validation and dispatcher work are explicit fixture seams;
these tests do not establish actual service drain or actual original END.

`test_withdrawal571` additionally uses the unpatched config loader, real CLI
subprocess and real public Board SDK against an entire def41-created journal.
Its principals, capability/run records and socket peer are isolated fiction;
the peer's draining reply supplies no actual service or parent END proof.

This avoids making a control request compete with runtime writers merely to
rebind the configuration. It does not make synchronous workflow operations
nonblocking, establish a general latency guarantee or qualify live load.

Collected adapter details include `startup_stage` and `protocol_progress`.
Each owned RPC records only its method name, local state and elapsed milliseconds
(plus exception class on failure). These are metadata, without wire bodies,
stderr, credentials or private account inspection. `awaiting-response` follows
the local send/drain; `succeeded` means the RPC returned an object without an RPC
error. It does not attest model semantics or completion of processing. The trace
is conserved in the collected outcome, rather than a live progress stream.

The original `adapter error: TimeoutError` signal and numeric process status
remain distinct. A timed-out request can have uncertain effects; later
unsubscribe/teardown does not turn it into successful classification. Existing
`thread_start`, capture, cleanup and residual-hold details remain necessary.
Historical timeout records without this trace cannot be assigned a protocol
stage retroactively. No timeout, model binding, enabled pool or admission policy
is changed by this correction.

The isolated recovery checks exercise proposer and integrator *typed selections*
using predetermined synthetic answers, plus unparsed, wrong-event and
unauthorized-task holds. They exercise real owned fixture processes, WAL locks
and the ordinary CLI/socket control route. They establish neither Luna semantic
judgment nor recovery of the reported live startup failures. Actual runtime
qualification and source adoption remain with the operating Work owner.

RPC response collection uses one existing timeout budget for send/drain and the
matching response together. Transport backpressure therefore cannot postpone
starting that budget. Cancellation clears the local pending correlation; a late
response cannot turn a timed-out request into success. Bytes may already have
been written, so timeout still leaves thread creation uncertain and grants no
replay. The default numeric budget remains 20 seconds.

The dispatcher yields before each synchronous phase, including after a preceding
phase records an error. This lets ready readers, timers and control connections
run between phases while preserving phase order and all phase checks. A single
synchronous Board lock, SQLite wait, source check or phase can still block the
loop; these yields neither interrupt it nor provide a hard wall-clock bound.

`test_coordination366` contrasts blocked drain, combined send/response delay and
ready control/reader scheduling against immutable source. Its phases, transport
and control callback are fictional. It executes the real `Peer` and `tick`
boundaries, retains an independent held-phase error and demonstrates subsequent
phase progress. It does not exercise full Board work or qualify actual service
latency, installed protocol/context compatibility or the historical timeout cause.
