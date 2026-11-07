# Exact stopped software-role execution fence

`role-execution-closure-basis` and `fence-role-execution` extend the existing
metadata closure protocol to one exact Work/Branch/Reviews/QA job and its
configured phase. Both require `JOB --token TOKEN --role ROLE --phase PHASE
--management SELECTION.json`; the append also requires `--receipt RECEIPT.json`.
There is no ordinary, processing, automatic-failure or role-owner impersonation
entry. Existing Work closure and anchored read APIs keep their contracts.

The current genuine Work software grantor selects this management operation.
`integration-management-basis --metadata-only --roles Work ROLE [SOURCE_ROLES...]
--authority TEXT --purpose TEXT` obtains its original-grant metadata basis. Every
selected role independently needs its exact stopped Work-issued software grant,
original role owner/profile, same journal inode, configuration and released
implementation. Native owner grants are ineligible. This uses the existing
software delegation's issuer/revoker and stopped management protocol; it grants
no authority to accept another role's outcome. An epoch without these original
Work delegations needs genuine original-owner selection through an independently
supported contract; this API refuses it.

The selection has exactly `basis`, `expires` (current and within one hour),
`operation`, `target` (`job`, `token`, `role`, `phase`), and `records` (the exact
single job and frozen event identities). Selected source roles must equal Work,
the job role and every frozen source role. No unrelated historical inventory is
selected. Both the management basis and the operation are recomputed under the
same SQLite write transaction.

The returned `role-execution-closure-metadata-v1` basis requires a held job, its
exact current task/phase, reserved original queues, exact task/controller, every
related task and diagnosis actually begun, finite ordered begin/END/collection,
integer numeric exit, complete capture, no pending recovery, and consistent
inactive recovery metadata. It returns only relationship/lifecycle metadata and
a complete-capture predicate. It does not acquire original results, details,
responses, outboxes, source payloads or canonical bodies/hashes. The cooperative
journal revision binds even changes to omitted columns.

The receipt has exactly `basis`, `reason` and `controllers`. Each listed original
controller (including diagnosis and recovery controllers) needs `controller`,
`collector`, integer `end`, `collected: true`, `writers_closed: true` and bounded
`evidence`. These are attributed actual collector/controller facts selected by
the genuine grantor; the journal does not authenticate external process facts.
A service ACK, model DONE, missing begin or inferred descendant closure is
insufficient. Unknown captures or artifact-only reconstructed capture eligibility
are deliberately refused by this narrow version.

The append uses `integration_retirements` and the existing permanent
start/callback/recovery gates. Execution capacity becomes available to distinct
fresh work. Original job state, semantic UNKNOWN/PARTIAL/FAILED, effects,
reserved queues, responses, delivery, custody, privacy and retention duties are
unchanged. No windows or starts are refunded, no processing/closed timestamp is
set, and no retention clock starts. Intake remains stopped; a separately admitted
current service lifecycle is still required. Ordinary leases, QA same-package
responsibilities and native contexts remain owned; local point/material/resource
conflicts continue to include these fenced originals.

`recover_review` addresses a native continuing context and can update its
associated jobs after informed inactive recovery. Finite report routes can have
no such context. It is therefore not a general exact finite-report execution
closure, and it cannot recover an original fenced by this new operation.

The new fixture exercises production CLI main, original Board software grants,
real SQLite conservation and Store.reserve. Its reservation admission seam only
enables synthetic intake after proving that the fence leaves all stopped grants
unchanged. Local scope resolution is synthetic while conflict and resource
checks are production code. No actual service, model, provider or live job is
qualified by this fixture.
