# Anchored terminal reader metadata fence v1

`work-read-metadata-closure-basis JOB --token TOKEN` and
`fence-work-proposer-metadata JOB --token TOKEN --receipt RECEIPT.json`
support a held, known anchored, nonwriting Work proposer. Both commands use
ordinary current Work authority or an exact operation-local `--management`
selection obtained through `integration-management-basis --metadata-only`.
They share the 671 original active/stopped software-grant checks, source-role
metadata enrollment checks, purpose, expiry, configuration and implementation
pins. Processing authority cannot substitute for the genuine owner.

The management selection must name precisely the old job/token and its frozen
source event IDs. Identity and source-role projections precede acquisition of
the selected lifecycle/policy/scope metadata. The versioned basis schema is
`work-anchored-read-fence-metadata-v1`. It contains no original job body,
frozen task body, member hashes, capture, result, error or historical evidence.
JSON functions inspect only named frozen policy scalars/types, local scope
lane/array shapes/point identities, and zero write counts. Publication and
local commit ledgers are checked for existence, without reading their bodies.

Every related task and diagnosis must have a real begin, numeric END and
collection, with the active task/controller relationship intact. Recovery
must be consistently inactive and have no pending request. A receipt has
exactly `basis`, `controllers`, and `reason`. Each controller item has exactly
`controller`, `collector`, numeric `end`, `collected: true`,
`writers_closed: true`, and bounded `evidence`. These are actual custodian
attestations required from the owner, never facts established by a process
census, model DONE, notification ACK or another role's testimony.

The append rechecks the complete initial basis, including the cooperative
journal revision, in the same write transaction after capacity checks. Later
coexistence compares only the current selected stable metadata against the
stored `stable` witness. It does not compare the initial global revision:
the fence append and normal future journal activity change that revision.
Changed task/controller/recovery/attempt metadata, selected write policy,
local scope or any publication/local commit duty refuses coexistence. Omitted
private fields are neither read nor hashed; their integrity is not asserted.
These checks do not provide hostile-writer CAS or past mutation history proof.

The local availability guard consults this qualified fence after the existing
capacity, resource, native, ordinary and discovery guards and before the old
point/material/resource conflict OR. Without a qualified fence, the original
OR order and first actual typed conflict witness remain. Only existing valid
incoming anchored Work file readers or routine file integrators can coexist.
Native bindings on either side refuse. New local jobs record the fence and
revalidate it before later execution/publication. Legacy unknown/nonlocal
reader commands and their original contracts remain supported separately.

The fence prevents old execution, callbacks and recovery. It does not mark
execution complete, release capacity, settle UNKNOWN effects, accept a result,
process input, release custody, delete rows, start a 24-hour retirement clock,
or waive any source/consumer/outbox/capture/effect duty. No selector, slot,
configuration or authority changes are part of this implementation.

Qualification is finite fictional journal work in `test_anchored_reader691.py`.
The production immutable frozen-policy trigger is separately verified; tests
of changed frozen bytes remove that trigger only inside a restored fictional
database snapshot to model a corrupted policy. No actual state is used.
