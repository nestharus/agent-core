# Selected dependency delivery

The bundled Board SDK remains the runtime SDK. Its existing
`retire_coordinator_pointer(conn, delivery, issuer, proof)` interface is retained.
The bundled queue helper additionally accepts keyword-only `resume: bool = False`.
Explicit `queue-resume-existing` passes `resume=True`, adding `--resume` to the
same original UUID/profile queue command. `queue-existing` keeps its previous
argv. Both are one-shot enqueue attempts; neither acceptance nor a resume warning
establishes wake, receipt, processing or business effects. Managed membership,
current grants, durable control correlation and genuine processing proof remain
separate existing obligations. No active-RPC implementation is added.

`canonical_publication` retains `method: retention-same-inode-v1` and the explicit
`library` selector. Its successor contract additionally requires `source_pins`,
an exact filename-to-SHA256 mapping for these five files in that same library:

- `retention.py`
- `board_store.py`
- `catalog.py`
- `queue_transport.py`
- `active_listener.py`

The candidate draft acquires this closed map with exclusion/alias checks and
bounded complete-file reads. The operator must review the actual provider and
draft; draft generation is not selection. The release manifest includes all
five files and verifies their declared pins. Changed provider bytes require an
explicit new legitimate selection, rather than refreshing a live configuration
silently. Older configurations can still be inspected, but publication and
successor release acquisition refuse missing closure pins. A lone retention-file
pin does not qualify this contract. The executing operator and bundled Board
library still must belong to the same actual release checkout.

Publication verifies the entire closure before any provider code executes, then
compiles the captured bytes. Provider imports, including deferred circular
imports, resolve to those same module objects. Ambient `board_store`, `catalog`
and other provider modules cannot substitute. An unlisted nonstandard import is
refused; the interpreter and standard library remain trusted dependencies, not
an attested or sandboxed Python platform. Each compiled module records its exact
source digest and file; identity mismatches and unsupported lock signatures
refuse before lock entry. The provider's existing zero-argument `snapshot_lock`
is called unchanged, retaining its cooperative same-inode serialization. This
does not establish hostile-writer CAS, multi-file atomicity or read isolation.

No task read root changes automatically. Explicit prospective `read_roots` may
select those individual pinned files for an already source-authorized task
outside cleanup;
ancestors, extra files and new writes are not admitted by this addition. Parent
selection must retain genuine task authority, exclusions and original cleanup
ceilings. This interface grants no account, provider, runtime, Board, native,
activation or acceptance authority. The parent supplies the actual current
helper digest in its chosen control policy; an old/public helper pin is not
silently rewritten to the bundled successor's digest.

`tests/test_dependency497.py` uses only fictional providers, queue runners and
protocol doubles. It covers public loader behavior, control correlation and
one-shot state, closure resolution, tamper refusal, release pins and cooperative
lock contention. It does not qualify real accounts, Board schemas/grants,
recipient wake/processing, publication effects or rollout integration. Existing
test fixtures that implement only a single retention file need an explicit
fictional closure/pins before exercising this successor publication contract.
