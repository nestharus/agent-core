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
