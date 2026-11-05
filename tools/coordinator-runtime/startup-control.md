# Startup evidence and normal service control

`processing-service-control` opens the existing runtime journal read-only. It
checks its initialized schema and current configuration without initializing,
migrating or taking a write transaction. The existing Work actor, processing
capability, source/configuration and continuing-service checks still precede the
request to the original Unix socket. The original endpoint retains its same-UID
and exact-capability checks. A successful stop response means draining; the
parent still owes the original numeric process END and subsequent disposition.

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
