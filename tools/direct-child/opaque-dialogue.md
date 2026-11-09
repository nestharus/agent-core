# Owned opaque caller dialogue

`opaque_dialogue.py` is an independent public caller port for an explicitly
supplied continuing endpoint. It is not wired into `review_context.Context`, the
opaque review adapter, the dispatcher, installed configuration or a service.
It performs no model/effort/alias resolution and always presents `gpt-xhigh` as
the uninterpreted consumer selector. It starts no subprocess itself.

The caller supplies an endpoint with three async operations:

* `open(ownership)` creates one original and returns its handle. The caller's
  `admission(profile)` async manager must be the actual current cooperating pool
  fence, not preview or a static list. Admission covers this creation only.
* `exchange(handle, ownership, thread, text, channel)` continues that original
  and returns `Reply(thread, answer, complete)`. The first returned thread is
  retained. Later exchanges receive that exact thread and the same handle,
  ownership object, selector, profile, collector and original expiry.
* `close(handle, ownership)` closes and collects that original through its
  original collector. Its return is endpoint testimony retained verbatim; this
  port neither invents numeric process END nor infers provider/effect closure.

No endpoint implementation is included. An endpoint must actually accept the
opaque selection as a caller contract and support continuing owned work. Merely
forwarding a CLI model operand or starting fresh calls does not establish that
contract. Ordinary account authentication belongs to that endpoint. The caller
must conserve its actual original handles/capture/effects when `open` raises
before returning a handle. This port cannot recover such a handle.

`authority(ownership)` validates the *current* authority of this same original;
it does not issue new authority. It runs after admission waiting, around each
exchange and before each material operation. Waiting and continuation never
renew the original lifetime. Failure fences later turns; idle original close
is still possible after expiry/revocation. A failed close retains the handle
and permits collection again, without reopening or replaying work.

The material channel takes already-admitted immutable byte values, not source
paths. It generates item IDs and permits only bounded `read` requests over
those IDs. Unknown requests, including file paths, writes, network, shell and
delegation, are denied without a corresponding effect implementation. A denied
request's arbitrary arguments are not retained. Each actual read records its
offset, returned byte count and hash; omitted reads produce no such event.
Channels close at the end of their turn. Evidence exhaustion refuses further
operations rather than dropping records. Bytes and the complete operation
sequence remain available to the owning caller. Emission is not semantic
reading, review completion or consumer acceptance.

The whole dialogue admits at most 128 turns and 32 MiB each of cumulative
material, prompt and retained answer bytes. Each channel admits at most 4096 operations and
12,000 bytes per read. Async open/exchange waits use only the original remaining
lifetime and cancel on expiry. This is cooperative Python cancellation, not a
kernel termination guarantee. The endpoint owns actual process/descendant
collection and must retain incomplete cancellation, capture or effects. Bounded
typed partial replies are retained before refusal; raw, malformed or oversized
returns remain with the endpoint's original capture rather than being silently
truncated into a valid answer.

This is effective mediation **at this API**, assuming trusted parent Python and
interpreter. It does not sandbox a malicious endpoint in the same interpreter,
deny a provider's native tools, observe kernel syscalls, or prevent an endpoint
from bypassing the channel. A real endpoint must enforce exclusive tool routing
and preserve full capture; their effectiveness needs independent evidence at
that actual composition before substantive material. Fixture results do not
supply that evidence. No raw/provider diagnostic content is exported here.

Maker1183 owns current Context/adapter composition and the existing actual
qualification entrypoint. Integration with that work requires an admitted
continuing opaque endpoint, actual exclusive tool mediation, current pool
creation admission and original collection. This module does not replace or
qualify that work. Actual linked CRW methods/history/situated architecture-first
all nine families/27 questions, same-context provider follow-on, all eight
consumers, native/service/sole Reviews receiving and cutover remain owed.

Focused local mechanism checks (no provider, accounts, installed operations or
old fixtures) use `python3 -m unittest discover -s tools/direct-child -p
'test_opaque_dialogue.py' -v`. They retain real byte operations, current authority,
same handle/thread, pool-fence lifetime, omitted-operation and weakened-neighbor
distinctions. They do not certify endpoint behavior or provider containment.
