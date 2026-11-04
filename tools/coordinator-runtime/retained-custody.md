# Finite retained delivery and software triage

`retained-basis`, `delegate-retained`, `retained-step`, and `revoke-retained`
provide an explicit software capability for retained inputs and informative
outboxes after a Work-issued software grant was normally revoked. They do not
unrevoke it, restart intake, alter its immutable configuration, move a collector,
issue a new native identity, execute a job, settle a consumer duty or clear a
hold. Ordinary grants keep their existing global count semantics.

This surface addresses a runtime whose finite logical allowance is consumed by
unrelated shared delivery rows. It separates the original runtime's cumulative
delivery count from an explicit finite ceiling on the shared rows and serialized
payload bytes seen by this writer. All rows count, including held and processed
ones. Logical use joins **all original runtime grants**, not just the current
role or capability, so another role or capability does not reset entitlement.
Each insert rechecks capacity inside the Board write transaction. This provides
cooperating-writer admission, not reserved space, a global allocator, authority
over other custodians, a physical filesystem quota, or protection against
noncooperating writers. Payload bytes exclude other Board columns, SQLite page
allocation, native/platform stores and external artifacts.

Only the actual original Work software issuer can issue/revoke this capability.
The normal role membership, original runtime path/device/inode, role/owner/actor,
original software configuration and revocation remain checked. A native-owner
grant cannot be taken over. A policy records exact current source/capacity basis,
current implementation hashes, a substantive authority reference, an expiry
within one hour, positive integer `max_shared_rows`,
`max_shared_payload_bytes`, `max_runtime_rows`, and `max_visits` (at most4096).
Logical rows cannot exceed the original `max_board_deliveries` allowance.
Policy/handling/payload retention also has a cumulative original-runtime byte
bound. This is serialized evidence accounting, not disk allocation accounting.

Example argv shapes, to execute from the genuine original Work context after
source delivery, using the **unchanged original config/journal**:

```text
coordinator --config CONFIG retained-basis Work
coordinator --config CONFIG delegate-retained Work --policy POLICY.json
coordinator --config CONFIG retained-step Work EXACT_RETURNED_CAPABILITY
coordinator --config CONFIG revoke-retained Work EXACT_RETURNED_CAPABILITY
```

`POLICY.json` has exactly `basis` (the complete returned basis), `authority`,
`expires` (epoch seconds), and the four named limits. The basis includes source
hashes, not source bodies. A changed basis refuses; do not blindly replay a
possibly committed issuance. There can be only one unrevoked continuation per
original grant, including expired ones. Explicitly revoke an exact known old
capability before selecting another. A lost issuance response remains an owned
uncertainty; this release supplies no guessed capability recovery or resend.

The existing CLI opens Store and its normal schemas before dispatch. Thus even
`retained-basis` is **not an effect-free process** although its Board query is
read-only. It does not invoke `status`, execution-pool allocation, provider,
native queue/helper, selected review, ordinary acceptor or cleanup. A sparse
checkout used for CLI operation must include `tools/direct-child/execution_pool.py`,
which is a normal import dependency; importing it does not select a task profile.
No HOME or native identity substitution is appropriate.

Each step spends one explicit visit before effects, scans at most16 sources,
and persists actual software triage receipts in additive Board tables. Stable
finite pages include inputs without outboxes, so the Work integrator input is
not lost. A later step revisits held sources after a complete sweep. No new
input, job or alert occurrence is manufactured. Changed immutable source sets,
configuration, implementation or runtime identity refuse affected continuation.
This narrow capability does not require unrelated UNKNOWNs to be cleared.

The real software worker reads source/queue/hold metadata, preserves actual
native owners and records its own software actor separately. It attempts
informative alert/question/result/effect-request posting only. An explicit
outbox/input hold or pending classification prevents posting; executable `work`
remains unsupported here. Original legacy resource/effect holds remain without
being turned into a general intake gate. Exact committed delivery attribution
is reconciled before posting; no native transport, ambiguous helper resend or
queue drain occurs. Existing native recipient `delivery-show` and
`delivery-stage` operations remain their own genuine-owner interfaces, even
after normal revocation.

These receipts establish visitation and durable triage, **not substantive owner
processing, selected Reviews, ordinary acceptance, actual control resolution,
four-role cutover or recurring-alert/silence efficacy**. They never set input,
alert or outbox `processed_at`. A real unresolved owner decision stays unresolved;
the worker does not create a fictional answer or export receipt. Canonical
effect holds and old recovery duties remain. Actual processing completion plus
24hours AND every source/consumer/outbox/recovery/effect/privacy hold still
govern retirement. No retirement is implemented here.

Tests use a kernel read-only source/dependency/controller sandbox and owned
SQLite fixtures. Actors/budgets are explicitly fictional; native fields are
NULL or absent. Native posting/catalog/membership use a declared transport
shell, and parser checks use an AST projection. These tests establish bounded
protocol behavior, not a production Board or operating qualification.
