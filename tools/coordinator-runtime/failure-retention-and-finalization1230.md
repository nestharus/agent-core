# Ordinary failure retention and truthful finalization

These changes preserve required new fixture oracles through ordinary conservation
failure and allow truthful finalization after protocol failure. No current service
policy is adopted by this source.

The focused recorder marks a snapshot complete only after conservation and its
record succeed. Failed attempts remain under distinct names. A failed snapshot
keeps its live connections and blocks normal close, teardown, cleanup and case
handback until the same owner can retry. The WAL oracle uses CloseGate even for
its explicit finally close; unsuccessful preservation cannot reach that close.
CloseGate retains the callback/live connection on failure. This covers relevant
ordinary copy/persistence failures with usable resources, not arbitrary host death
or unlimited retries/storage. Persistent inability remains incomplete responsibility
for the actual owner; partial files never claim to replace uncopied bytes.

Context rejects nonstring event/item kinds. Unexpected event-handler exceptions
stop semantic interpretation while raw capture continues draining the same original.
The finalizer also collects failed capture tasks as incomplete evidence rather than
throwing forever before receipt reservation. Numeric END, actual EOF, complete
capture, finalizer persistence and delivery remain distinct. Protocol failure cannot
be answered or protection success. Failed receipt files and publication predecessors
remain with the same original and normal retry; no provider replay or renewed rights.

The focused controls use retained new SQLite oracles and local Python processes
emitting explicitly fictional provider/tool records. Existing T/E/C and selected
caller/authority/protection controls retain their meaning. Original historical test
assertions remain unchanged; journal projection is not legacy/native/full opaque
compatibility. Producer verification does not supply independent consequences,
Frame/Work disposition, actual protected operation or independent receiving.
