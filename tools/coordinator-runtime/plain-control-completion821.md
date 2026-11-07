# Plain-control completion

`processing-dispose-plain-control CAPABILITY EVENT --attempt ORIGINAL --receipt FILE`
is the supported authenticated Work CLI. Use the already selected coordinator and
its existing `--config`; this command does not select, install or amend a source.
The genuine current Work session is required only when making its decision.
Continuing software classification/completion does not require native Reviews
availability. Do not synthesize a native session or call resolve-input as Reviews.

The JSON receipt has exactly these required fields (placeholders are not receipts):

```json
{
  "schema": "plain-control-terminal-v1",
  "event": "EXACT_EVENT_ID",
  "source_hash": "EXACT_SOURCE_SHA256",
  "received": 0.0,
  "attempt": "EXACT_COLLECTED_INPUT_CONTROL",
  "result_hash": "DIGEST_OF_WHOLE_ORIGINAL_PARSED_RESULT",
  "resolution_version": 1,
  "scope": "no-new-owned-work-or-effects",
  "accounting": [],
  "evidence": ["Actual Work interpretation of the whole original source and actual collection"],
  "completed_consumer": null
}
```

`accounting` must separately reproduce EVERY original remaining_obligations entry
with its exact index and text. Never clear, paraphrase or rewrite that original
array. Each entry has `index,text,disposition,owner,event,source_hash,evidence`;
`disposition` is `conserved-at-original-source`. `event` and `source_hash` name the
exact original source and `owner` its actual enrolled owner. Evidence must establish
that THIS message assigns no new owned work, decision or effect. Unknown duties,
THIS-message work, pending decisions and unknown effects remain blocking. DONE,
empty arrays and preservation keywords are not sufficient evidence.

If an actual original source is outside this journal, genuine Work may supply an
additional `attestation` object on that entry: `reference` is the exact meaningful
current public source/receipt reference; `observed` is its actual numeric observation
time, no later than now and at most 300 seconds old at initial application. The
entry still requires the exact original identity, SHA256, actual enrolled owner
and scope evidence. This is an attributed Work decision, not software verification
of the external source or disposition of its historical duties. Automatic workers
cannot use this attestation path. Accepted evidence is immutable, never restamped.

For an already-created unreserved Work control return, retain `completed_consumer`
as its exact response ID and add this separate required `consumer_disposition`:

```json
{
  "schema": "plain-control-consumer-v1",
  "event": "EXACT_RETURN_ID",
  "source_hash": "EXACT_RETURN_HASH",
  "received": 0.0,
  "scope": "whole-return-no-new-owned-work-or-effects",
  "payload_hash": "DIGEST_OF_ENTIRE_PERSISTED_RETURN_PAYLOAD",
  "evidence": ["Actual Work whole-payload/history interpretation and no new receiving workflow/effect"]
}
```

Its own collected classifier and ACK are required. The entire stored source,
worker result, resolution, return edge and descendants remain unchanged. Pending
descendants, jobs/reservations, holds, outboxes, publications and uncertain effects
refuse; a running job is never adopted and no Work item is fabricated. The command
records this actual control-only consumption and marks its queue done. Ordinary
completion still processes the consumer before its parent. The source requires
another collected fresh classifier selecting @control. Repetition creates no
return, classification, timestamp or counter reset.

For future controls, the delegated worker can add `plain_control` to its original
serialized decision_json. Its exact keys are `scope,accounting,evidence` with the
same semantics above. The normal collected-control application validates it and
records immutable software provenance (worker, issuer, original controller,
collection, result hash, non-native attribution), then applies the ordinary
resolution without a phantom Work return. No new model worker is created by this
receipt stage. Without a sound structured decision the original conservative
consumer/owner path remains. Existing returns always need the genuine Work receipt.

Exact service case from diagnosis815, not a live-currentness assertion:

- Event: 8690e0d6b3564c7e691a71c63106576896713eb0793a5e07a6e4ee4deec7681a
- Source SHA256: 79a07742d06cc59ac64d4a258b3eed2895bf1055ae312aa24e20ab2e2b30e10b
- Original control: d6903ce1-4564-4fd3-8a18-2c905424298a
- Result digest: ddf71203d76b06e66559e3726c6af3a512ef6cbeb08f93d56b94fbe91659b5fe
- Existing return: 12567578701acf441e2c6e2d008efad93f3e6cfcb688786508deaa6ef66dec06

The specific required Work receipt must use the actual source birth, exact five
original obligation strings, each actual owner/source reference with meaningful
current evidence, and the return's actual hash/birth/whole-payload digest. The
summaries in diagnosis815 cannot substitute for those original strings. A sound
automatic classification of this already-created return is not claimed. After
independent review and the separately authorized stopped source amendment, this
CLI supports the parent's genuine current decision without a new native Reviews
ACK. Do not run the candidate against service58116/source822 or change that running
source in place.

Current release/configuration/source selection, finite lease/cumulative budgets,
grants, source birth/hash, original worker/binding/collection/tool completion and
exact resolution are checked before source acquisition and inside the transaction.
Global completion consults this validated exact disposition; other nonempty
obligations remain blocking. This is cooperative local SQLite serialization, not
cross-store atomicity or a noncooperating-writer CAS. Native effect authority keeps
its raw epoch expiry. All privacy, source, recovery, effect and retention duties
remain; retirement still requires actual whole completion +24h and every hold.
