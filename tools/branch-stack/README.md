# Branch stack-segment DAG controller — corrected combined candidate

This stdlib-only package is a metadata observer, deterministic planner, controlled
executor-contract simulator, and durable notification adapter library. It does
not acquire source, run Git/gh, change refs, install a monitor, or post to a board.
The separate adapters described in ADAPTERS.md add bounded real synthetic Git
probes and a parent-injected board bridge. See CORRECTIONS.md for F1–F5 and V2.
The parent Branch owner receives the candidate and binds the existing feed and
transport; QA owns live recipient acknowledgment.

## Receipt and execution

Target repository: /home/nes/ai. Proposed additive paths:
tools/branch-stack/src/stack_controller.py,
tools/branch-stack/tests/test_stack_controller.py,
tools/branch-stack/fixtures/*, tools/branch-stack/README.md.

The provided full-candidate.patch adds the exact combined positive filemap. No checkout/branch/commit
was created: an actual tracker association was not supplied. Parent applies it
in its properly assigned isolated checkout using git apply --check followed by
git apply. This Maker leaves shared Main and existing WIP untouched.
This is a tested candidate, with handling exceptions in READFIRST.md, not an
installed or operationally qualified service.

Commands (invoke with /usr/bin/python3 -I -S -B and the exact script path):

- plan --snapshot PATH: JSON plan, symbolic new-tip references and materialization IDs.
- alerts --snapshot PATH --check-id ID: actionable JSON alert DTOs; no send.
- simulate --snapshot PATH --plan PATH --actual PATH --outcomes PATH:
  pure controlled effect trace, no native execution.
- native-contract --snapshot PATH --mode whole|feature|checkout [--unit ID]:
  accepted existing Stack1649 command DTO; no subprocess.
- once --snapshot PATH --binding PATH --journal PATH --lock PATH --check-id ID:
  observe the immutable input, maintain stale frontier, prepare durable notices.
  Returns PLAN_ONLY_PARENT_TRANSPORT_NOT_BOUND; it does not call a sender.
- schedule: emits cadence 300 seconds and foreground once contract, starts nothing.

Exit 0 means successful computation with no current observer problems (or successful
controlled simulation), 3 means an unresolved observer violation or blocked/
unknown controlled simulation, 2 means invalid/missing/stale input or busy lock.
A 0 is never an approval, semantic product pass, live delivery, or Ready claim.
simulate marks all successful recomposed versions UNQUALIFIED and requires new
version evidence. Group PLANNED means a composition plan exists; inspect the
separate qualification field, particularly RECOMPOSITION_REQUIRED.

Before a parent run, freeze the exact script, snapshot, binding and provenance
aliases kernel read-only before Python startup. Use root read-only, both exact
reserved-calendar empty read-only masks from SELECTION.md, a private proc/dev,
and only a dedicated state directory writable. Keep input files outside that
writable directory. Use Python -I -S -B; dependencies and .pth remain read-only.
The correction task qualifies this setup under bwrap; its reports bind actual methods/results.
No dependencies installation is necessary.

Startup binding is a JSON object:
schema=stack-startup/v1, source_sha256=exact script byte SHA256,
snapshot_sha256=exact snapshot byte SHA256, feed_binding, feed_schema,
owner=the existing persistent Branch owner.
Use one canonical absolute journal and lock path for that owner. Never unlink or
replace the lock inode while any caller may run. flock is the kernel lease until
process exit. The lock is never written or truncated. CLI/runtime compare the
opened lock inode with the journal before writes; symlinks/collisions are errors.
This is cooperative
single-user ownership, not an adversarial identity boundary. On input/source/
feed mismatch or busy lock, exit 2. A pending journal file after interruption
requires parent reconciliation; it is never silently discarded.

After actual feed binding and independent operational QA, the parent may schedule
one foreground once per five-minute occurrence under the existing scheduler.
Every occurrence must carry a new durable check_id. Do not launch a new service
or register another agent merely to use this package. Parent stops future
invocations to disable the monitor; preserve the journal and settle uncertain
attempts before changing canonical state paths. No scheduler was installed here.

To qualify tests in a received layout, create a fresh private runtime directory,
set STACK_DAG_TEST_RUNTIME to its absolute path, mount it writable while freezing
the package, and execute tests/test_stack_controller.py with Python -I -S -B.
Tests invoke real CLI subprocesses under nested read-only bwrap mounts and write
each invocation's frozen inputs, argv, raw streams and numeric exit. Runtime
directories cannot be reused for another attempt. bwrap is a host qualification
tool; it is not an imported Python dependency.

## Input contract and evidence limits

Only stack-dag/v1 is supported. The externally returned native feed schema has
not been received; a parent adapter must translate and validate its existing
account/feed, task associations, role admission and evidence. This package is not
a second Work inventory and cannot claim a live Branch account binding.

Every snapshot has schema, feed {binding,snapshot_id,schema}, repo, exact main
OID, units, segments and groups. Optional events, merges, probes, violations,
stale_units and recomposed are bounded metadata. Unknown fields and duplicate
JSON keys are errors. JSON is capped at 2 MiB; at most 1000 units, segments and
groups and 4000 events/probes/violations. Smaller actual resource budgets remain
the parent's duty.

Each unit has id, singular numeric pr, exact ref, ticket/campaign/native_stack
(nullable associations, never invented), version, requires, physical_base,
provenance, evidence, eligibility and admitted. Version is exact head/tree,
ordered parents, content version and resolution version. Its key is canonical
JSON SHA256. Physical base has ref/head. Provenance has reference lists original,
tests, oracles, signatures. These opaque reference strings are not read and do
not establish signature or preservation truth. Evidence carries kind,
version_key, ref and PASS/FAIL/UNKNOWN; stale or different-version evidence is
inapplicable. Membership is one native stack per canonical PR. A duplicate PR
or simultaneous canonical ref alias is rejected.

Segments have id, ordered units and depends_on segment IDs; their cross-segment
dependencies attach to the parent's tip. Unit requires and segment-derived
dependencies form the logical DAG. Symmetric observed conflict pairs are stored
separately. Cycles are rejected. Shared canonical foundations appear only once
in each materialization and the canonical restack operation sequence.

Groups have id, tips and order. Multi-tip or diamond joins require an explicit
complete topological order, with each canonical unit once. A materialization ID
binds the exact Main, ordered canonical closure and all version keys. Conflicting
physical parent orders for one canonical unit require explicit separate
materialization units; the controller rejects two simultaneous physical meanings
for one PR. Such units must have their own legitimate ref/PR/provenance from the
existing account, not fabricated identities. Operations expose symbolic
$result:UNIT bases and selected_parent_order.

Typed events carry kind, unit, before, after, evidence_ref. ref binds complete
versions; base binds ref/head; membership binds stack ID or null. main uses
unit=null and exact before/after OIDs; merge points at evidence references and
never establishes landed status alone. Event after must match the snapshot.
The durable observer also compares consecutive exact versions, bases, logical
dependencies, native membership and Main. Unresolved stale descendants survive
later snapshots without events. Removed canonical units require parent
conservation disposition rather than silently disappearing.

Recomposed attestations have unit, version_key, evidence_ref. They clear persisted
staleness only when every containing selected group also has admitted CLEAN
ordered and semantic evidence for exactly the current versions/order/Main.
This accepts a bound feed's explicit attestation, not independent Git proof.
The observer does not infer preservation or approval from a matching patch.

A merge record has unit, version_key, method=merge|squash, main_head,
landed_commit, main_ancestry_verified, mapping=exact|unknown, evidence_ref.
Only an exact version mapping and asserted verified ancestry in the actual
snapshot Main establish landed. Landed units must form a bottom-up frontier.
Message/patch equivalence is unsupported. Wrong Main, old versions or ambiguous
squash mapping stay at a manual UNKNOWN frontier and are not replayed. Exact
landed units are removed from replay plans; descendants use updated Main.

Probes have kind=pair|ordered, units, versions (unit→version key), base, status,
paths, reason, evidence_ref, admitted, semantic. An ordered probe binds the entire
chosen order; pair identity is symmetric. Path entries contain only path and
ordinary_safe=true. Admission is an explicit responsibility of the bound input
adapter and its actual policy; it is not guessed from .pth/dotenv/provider/model
substrings. Unadmitted probes cannot supply paths. Source/patch bodies are never
accepted as fields. Missing/unadmitted/version-mismatched probes are UNKNOWN.
Textual CLEAN alone is insufficient without independent semantic evidence.
The core has no Git object getter; the separate Git adapter is described in ADAPTERS.md.

Violations carry unit, kind, obligation, evidence_ref. Explicit active/deferred/
trigger flags and deferral_ref remain from Work's existing account. An inactive
deferred campaign is not automatically activated. Unexpected changes,
conservation failures, required closure/repair and all explicit cloud/demo obligations
remain actionable. Ordinary whole_landing is exempt only with current explicit
deferral, false authoritative trigger and a validated deferral reference; PR number
or inactivity alone cannot grant it. Necessary held unlanded ancestors keep an
active descendant group UNKNOWN/manual with dependency/order intact and no group
operation. This conservative interpretation is pending Work9595, not owner-confirmed.

## Delivery integration

alerts returns exact repo/ref/PR/unit/version/base bindings, descendants, order,
disposition, safe locations or UNKNOWN reason and next operation. A healthy
check returns []. Every distinct violating scheduled check generates notices
even with identical content. No cross-check suppression exists.

Under the same canonical owner lock, parent may use DeliveryJournal.prepare/
deliver and inject an admitted actual sender. board_command builds the current
board.py open --session --topic --title --kind status --text --to protocol for the
fixed board cdb7c432-a0a0-4fc3-aba4-068b20a02c88 and existing Branch recipient
01a18bb3-2d8f-7eb0-a1ef-31b62ae96198. Its isolated-Python bootstrap explicitly
adds only the supplied exact board program directory, needed for its existing
sibling imports. Parent must qualify those actual imports/settings and catalog
before execution. The builder itself executes nothing and accepts no invented
catalog/profile binding. No existing Work monitor is changed.

The sender returns board-qualified notification_id and stage ENQUEUED, PUSHED
(with queue_message_id), or RECIPIENT_ACK (with ack_ref). Actual board receipts
must justify each stage; queue acceptance cannot become an ACK. Persist
AMBIGUOUS before transport. The same check/alert has one durable attempt:
a timeout, crash or malformed receipt never causes blind replay. reconcile
updates a separately obtained receipt without sending. A distinct scheduled
check still emits while the violation persists, even if an older attempt is
uncertain. Archive settled journal history under parent's preservation rules at
10000 checks or 2 MiB; no automatic deletion or truncation exists.

The Maker used mocked sender callbacks and real journal persistence only.
The separate mocked-qualified CLI decoder and runtime bridge are described in
ADAPTERS.md. Actual account/provider binding, scheduler binding, announced live
delivery and actual Branch acknowledgment within 30 seconds remain parent/QA obligations. Missing acknowledgment must be FAIL with the
actual snapshot; manual polling or a queue receipt is not success.

## Native operations

Existing Stack1649 has order 1639→1640→1647→1648→1645→1641 and node
PRS_kwDOOtFmdM4ALB_v. The native prior structural seed records the supplied heads
and Main, and deliberately lacks trees/parents, current API results, live
provider repo identity and task associations. It is not an executable qualified
snapshot. No invented values fill those gaps.

The native contract emits gh stack checkout 1649, whole-stack gh stack rebase
then gh stack push, or owning-feature gh stack rebase --upstack then gh stack
push. Existing membership/order is validated. Parent owns current capability,
CAS, conservation/signature/approval interpretation, native execution and all
publication/CI effects. No unstack/recreate/member-add/ours-theirs commands exist.


Directory sync failures after journal replacement are accepted-but-indeterminate,
not rejected and not durable success. `once` returns structured persistence
metadata and native code 4; the adapter runtime returns INDETERMINATE while
retaining known violations. Historical same-ID results are receipt-only, never
sends or durability confirmations. See ADAPTERS.md for `receipt_status`, explicit
`recover`/`confirm_durability`, pending-file preservation and owner reconciliation.

## Current installed consumer and durability boundary

See `EXISTING-COLLECTOR.md` for the current contract, normal source access,
producer schema, routing and historical qualification limits. This section and
that document supersede older collector-admission or controlled-test-only source
wording in historical sections. Normal relevant source/config/Git reads are
allowed; no source-holder, filename or loose-object-only access ritual applies.

Install only from the qualified signed feature commit. The versioned payload is
`~/.local/share/rfq-stack-dag/versions/<commit>/tools/branch-stack/`; the normal
entrypoint is `~/.local/bin/rfq-stack-dag`. Run `rfq-stack-dag --version` for the
exact commit and core hash. `rfq-stack-dag collector --help` exposes the frozen
foreground consumer (no scheduler or sender), including expected code version
and optional explicit owner bindings; other commands use the core CLI.

INDETERMINATE is a completed evaluation with unresolved durability, CLI4, never
a durable success. Reopened adapter replays stay INDETERMINATE/UNVERIFIED and
receipt-only. Explicit owner recovery confirms current state without sending.
