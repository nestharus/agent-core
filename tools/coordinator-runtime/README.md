# Opt-in coordinator runtime

This is a candidate dispatcher for the selected Work, Branch, Reviews and QA
pattern. It owns new private stdio app-server children, classifies messages and
responses with fresh `gpt-6-luna` low task sessions, commits queued responsibility
before delegated receipt, freezes batches, and schedules the next available
batch. There is no JEV, external service dependency or parent wait wrapper.
Python 3.11+ and the standard library are sufficient for fixture tests.

**No live service, role enrollment, grant, model call, cutover or session cleanup
has been qualified by this implementation.** Independent routing/design/code
assessment and parent-collected real qualification precede activation. The
example is disabled and preserves unresolved legacy holds. Root, Dispatcher and
Cloud have no runtime enrollment. Publication is not acceptance.

## Install and inspect

Keep an isolated checkout of the published feature revision; do not overwrite
the dirty live `/home/nes/ai/tools/message-board` substrate. Nothing requires a
global Python installation or profile/config changes.

```sh
RUNTIME=/absolute/selected-checkout/tools/coordinator-runtime/coordinator
python3 "$RUNTIME" --help
python3 -m unittest discover -s /absolute/selected-checkout/tools/coordinator-runtime/tests -v
python3 "$RUNTIME" qualify-schema --output /absolute/owned-evidence/new-schema-directory
```

`qualify-schema` runs only installed CLI version/schema generation. It starts no
app-server/model. Its private output must be a fresh empty directory; retain the
qualification receipt and schema for current consumers, at least 24h and all
holds. Codex 0.166.0's generated experimental schema exposes
`thread/start.ephemeral`, `thread/read`, `turn/start`, `turn/interrupt`, and
`thread/unsubscribe`. The [official app-server reference](https://learn.chatgpt.com/docs/app-server#threads)
documents ephemeral fork; installed start support here comes from generated
schema, not an inference from that reference. Schema presence does not prove
runtime lifecycle behavior.

Copy [examples/rfq.json](examples/rfq.json) to an owned private configuration
path. Fill the actual board catalog home/UUID, exact board-local role strings,
selected runtime checkout/template paths, private state directory, actual source
and effect roots, and the offline qualification receipt. Verify the literal
provider/model/effort against the installed service during parent qualification.
The four current role UUID/profile pairs are supplied as prospective selectors;
the zero board UUID and placeholder paths are deliberately unusable. They are
not enrollment, actor authentication, an operational handoff or a live census.

Choose `enabled` before initializing a journal. Configuration is bound by digest;
changing it under a running journal is refused. Use an offline owned migration
and explicit responsibility handoff for later configuration changes; this release
does not automate migrations or import legacy queues. Never discard an old
journal to evade its holds.

```sh
python3 "$RUNTIME" --config /absolute/private/config.json init
python3 "$RUNTIME" --config /absolute/private/config.json status
```

State is private SQLite WAL/FULL plus exact owned artifacts. Use mode 0700 for
the state directory and mode 0600 for configuration/evidence containing private
message material. No private profile/history/environment inventory is needed.

## Real enrollment and held adoption

Each actual role owner executes the following commands in its existing actor
context. `CODEX_SESSION_ID` must already identify that actual caller. **Do not
synthesize an owner's environment, borrow membership, move its cursor, or point
the runtime at a TUI/app-server/native collector.** The selected user authority
allows these roles; it is not authentication. The bridge records explicit
revocable role-lifetime delegation and real actors within the shared Unix
account's cooperative trust boundary.

```sh
python3 "$RUNTIME" --config /absolute/private/config.json enroll Work \
  --authority /home/nes/projects/rfq/planning/coordinator-runtime-rollout-20261103-01/DECISION.json
```

Repeat from the actual Branch successor, Reviews and QA actors for those roles.
Before delegating new receipt, the actual owner must select prospective
`managed` delivery using its existing board CLI/context and reconcile duplicate
intake writers. The runtime refuses to grant over a queue-route membership; it
does not change that membership or reroute any existing notice. Historical
route snapshots, sending effects and original collectors remain intact. This
prospective route selection and a return to prior routing need actual owner
handoff, not a fabricated idle claim or a managed-owner process takeover.
Enrollment verifies active actual membership, exact role/profile, catalog policy,
invitation when required, board UUID and file identity. It records a prospective
post-sequence cutover and a grant bound to this runtime DB inode and actor.
The automation/classifier never joins as, impersonates or advances the owner.
Private body access is limited to the enrolled owner's addressed events.
Notices and role-directed flat posts are covered; flat posts get processing
receipts, not fictitious notice ACKs. No old event is imported automatically.

All configured legacy holds remain until the actual owner supplies its real
collector/effect reconciliation. Example receipt shape (values must be actual):

```json
{"collector":"actual original collector","evidence":["exact closure/outbox receipt"],"remaining_holds":[]}
```

```sh
python3 "$RUNTIME" --config /absolute/private/config.json reconcile-legacy Reviews \
  --receipt /absolute/owned/actual-legacy-reconciliation.json
```

This assertion is the owner handoff boundary, not a process census. Never fill
it from null queue fields, labels or this example. Classified intake/ACK can run
while a legacy hold blocks task launches. Existing originals, CI admission,
reviews, source/resource/monitor owners and partially sent effects remain with
their actual collectors.

Grant creation and runtime enrollment are two commits. If enrollment fails after
grant creation, retain the exact grant as an orphan operational record; it did
not enroll the runtime. The actual owner can revoke it explicitly:

```sh
python3 "$RUNTIME" --config /absolute/private/config.json revoke Reviews --grant ACTUAL_GRANT_UUID
```

Revocation stops new delegated reads/receipts and new launches. Already owned
attempts retain collection/effect obligations; it neither kills them nor loses
their queues. Re-enrollment/config migration after revocation requires an exact
owner-selected prospective handoff; it is not an automatic replay path.

## Run as the actual dispatcher

Only after independent assessment and parent-collected qualification/continuing
disposition, use an explicitly enabled configuration:

```sh
python3 "$RUNTIME" --config /absolute/private/config.json run --enable-models
```

A foreground invocation is usable. For a service, an operator can install the
following user unit with absolute qualified paths; this repository installs or
starts nothing:

```ini
[Unit]
Description=Selected coordinator runtime
[Service]
Type=simple
UMask=0077
ExecStart=/usr/bin/python3 /absolute/selected-checkout/tools/coordinator-runtime/coordinator --config /absolute/private/config.json run --enable-models
Restart=no
KillMode=mixed
TimeoutStopSec=900
StandardOutput=null
StandardError=null
[Install]
WantedBy=default.target
```

SIGTERM/SIGINT stop intake and collect already owned attempts. Allow the selected
task deadline, one continuation budget, interrupt and shutdown bounds before
outer service termination. `Restart=no` avoids pretending that a replacement
service owns old handles. A forced service/container/host loss leaves unknown
reservations held. Do not add automatic restart/replay until the original owner
has reconciled those reservations. Units/log rotation are operator-owned, outside
this install. JSON alert output excludes raw protocol bodies; private message
and typed final content remain in the private journal.

## Routing, slots and actual authority

Routes are configured task IDs, templates, exact model bindings, purpose and
typed effect/access operations. No incoming message can supply a shell command
for the dispatcher. Invalid, partial, wrong-event or disallowed classifications
stay owned and unACKed. A Work exception task can be explicitly allowlisted.
Same-event redelivery is deduplicated by event identity; distinct occurrences
with identical bodies remain distinct. The classifier's UUID, actual attempt,
configured/read-back binding, source author, recipient and package survive the
handoff. Binding readback establishes configuration, not execution attestation.

Classification and queue responsibility commit in one transaction. The additive
board bridge then verifies that durable pair, records real automation/classifier
actors and updates only the exact notice in one board transaction. An interrupted
reply is reconciled using that board-local receipt; no send or blind enqueue is
replayed. There is no owner `ack_seq` mutation. The board extension does not
authenticate users against each other on the same Unix account.

Work/Branch/Reviews each have one independent integration slot. Members and
revisions freeze at reservation; arrivals enter the next batch. Read-only
proposers are instanced with their configured task bindings. Work and all
integrators explicitly require `gpt-6.1-sol` xhigh. QA has five independent
execution slots and one separate per-package consolidation slot; there is no
cross-package QA batch. Reservation, active-attempt identity and controller
fences prevent double launch/closure across controllers.

QA admission is per package and stays with actual Branch ownership:

```sh
python3 "$RUNTIME" --config /absolute/private/config.json admit-package EXACT_PACKAGE_ID \
  --receipt /absolute/actual-branch-admission.json
```

The `ref` on a QA board post is that exact admitted package ID. Accepted QA
qualification needs a separately supplied actual accepted receipt with the same
command's `--accepted-receipt`. Neither a model's `qualification` category nor
this software accepts a package. Missing admission/acceptance holds the work.

The supplied real method/proposer/Branch/report-integrator references are loaded
as actual task instructions; tasks receive frozen source identities, original
results and reservation/collector/authority context. Reviews consolidation routes
to Work; scope/blockers route to Work; accepted QA qualification routes to
Branch. Root code-writing workers retain commit AND push. Root is not enrolled
as an automated recipient. Real external Root/CI/PR/board send effects remain
with existing owners and their exact intents, not a generic shell transport.

Responses are durable internal addressed handoffs between enrolled roles,
classified by another fresh Luna-low invocation. They do not issue duplicate
board messages. Every source occurrence/report remains linked through frozen
members, original attempt results and the response payload. Local handoff is not
a claim that an existing human/TUI coordinator read or adopted it.

## Effects, recovery and observability

`status` shows intake/legacy holds, ACK lag, queued/held work, reservations,
attempt controllers, model/profile bindings, real begin/exit/collection,
semantic status, capture, cleanup, capacity errors and backlog/storage pressure.
A semantic DONE may be visible while the owned process is still alive. Numeric
exit zero alone is not DONE or acceptance. Failed/invalid/partial results remain
recoverable; they do not silently free slots or become successful reports.

Read-only tasks can close automatically after successful actual collection and
valid DONE. `owned-artifacts` report tasks use a fresh attempt directory as cwd
and their only writable root, with no network, allowing automatic report drains.
The kernel sandbox and model's actual behavior still need live qualification.
Canonical/external-effect tasks require the actual role owner to reconcile all
possible writes/intents/outboxes. Supply genuine evidence, never a fabricated
empty set:

```json
{"evidence":["exact actual per-file/effect/outbox reconciliation"],"unknown_effects":[]}
```

```sh
python3 "$RUNTIME" --config /absolute/private/config.json reconcile-effects JOB_UUID \
  --token RESERVATION_TOKEN --receipt /absolute/actual-effects.json
```

The running controller then drains automatically. This version does not verify
arbitrary external effects, execute send intents or automatically judge a model's
effect report. Effectful progress depends on those real owner returns. Partial
results after bounded recovery remain held for consequential owner disposition;
there is no forced `accept-partial`/drop/slot-release shortcut in this release.
Work's own scope/blocker returns remain with the actual outside Decider; they
are not fed through an unlimited model self-loop or treated as capacity recovery.

Timeout recovery first interrupts the exact owned turn, waits for its matching
completion and checks idle state before one same-session continuation. Failed
or semantically incomplete turns also get at most one supported idle continuation.
An unavailable or ambiguous API/end stays held. After collection, at most one
fresh Luna-low diagnosis may select an authorized profile and explicit remaining
work. Replacement requires actual original collection/end, reconciled effects,
and an exclusive journal transition. It receives prior owned session reference,
result/error, effect receipt and diagnosis. This is an informed cold handoff,
not native resume or restoration of lost ephemeral memory. A late original
cannot satisfy the replacement's attempt or route a second result.
An actually collected failed/invalid classifier gets at most one separate fresh
Luna-low diagnosis/classification on the explicitly selected diagnosis account.
Its route still must pass the same event allowlist; no valid route means no ACK.
The prior failure remains conserved and cleanup gaps remain held. Unknown/live
classifiers are never replayed; classification capacity is reserved across
controllers under the same database write lock.

Controller/host-loss recovery is deliberately limited: no PID/file/age inference,
orphan resume, foreign native wait/kill or blind mutating replay. Automatic
reconciliation of lost process handles, transport-ambiguous thread creation,
unknown effectful attempts and preflight failures without a child exit is not
implemented. They remain explicit holds for the original owner/parent. A new
controller can still classify new events and run genuinely free independent
slots; it cannot free unknown old reservations.
Already durably collected attempts can transfer *closure work* under the same
automation grant when their effects are absent/reconciled and no recovery owner
exists. That transfer records the original collector/attempt/exit separately;
it adopts no process handle. Valid already-collected classifications also finish
their interrupted queue commit without another model call.

Each launch checks all effective MCP names, disables them individually (including
the injected docs transport), and requires a second complete disabled readback.
Delegation-like feature flags are requested/read back false. They **do not prove
absence of model-facing delegation tools**; that capability remains
`not-established`. Unexpected observed delegation makes capture incomplete.
No credentials are copied, no login occurs, and no global model/profile selector
changes. `.codex` through `.codex5` are explicit account choices, not exclusive
profile locks. Real availability, identity, capacity and nondelegation still need
parent qualification. Missing raw stderr/reasoning is deliberate: `capture`
means the bounded typed protocol/final boundary, not a complete tool transcript.

Distinct unresolved violation occurrences recur even with unchanged text;
healthy operation emits none. Same-event deduplication is unrelated to alert
recurrence. Alert journal/output has a cumulative bound. Actual consumers mark
processed occurrences with `ack-alert OCCURRENCE --receipt ACTUAL_JSON`; only
that processing starts their 24h retirement clock. Unprocessed alert backlog
produces backpressure, not discard. External journald/log storage needs its own
operator retention bound; runtime output is not a claim of consumer receipt.
The proposed service unit discards duplicate console presentation and keeps
durable alerts in the bounded runtime journal, visible in `status`. If console
capture is selected instead, its cumulative limit belongs in that operator's
explicit capture configuration; do not create an unlimited redirected log.

## Queue and one-off cleanup

Queue processing completes only after job closure, durable downstream
responsibility, processed descendants and settled receipt outcomes. Retirement
begins at actual `processed_at + 86400`, never enqueue or ACK time. Consumer,
recovery, process, artifact and effect holds survive. Required final results,
classification/provenance and event deduplication tombstones remain conserved.

The dispatcher sweeps eligible queue/artifact records automatically. Operators
can also use `cleanup`. `hold EVENT --reason TEXT` preserves a consumer/recovery
hold; `release-hold EVENT --receipt ACTUAL_JSON` requires the actual role owner.
New task artifact paths are inventoried only below that exact owned attempt
directory. The actual role owner must first record conservation:

```sh
python3 "$RUNTIME" --config /absolute/private/config.json conserve-artifact \
  /absolute/state/artifacts/ATTEMPT/one-file --receipt /absolute/actual-consumer-conservation.json
```

Deletion rechecks processing age, all holds, exact dev/inode/size/mtime and
single-link regular-file identity under the journal lock; directory-descriptor
walks refuse symlinks. Partial deletion errors remain receipts and are excluded
from automatic replay. Changed/missing/uninventoried files and errored partials
need deliberate owner reconciliation; this release has no bulk retry/purge.
An untrusted same-account actor racing directory entries is outside this
cooperative boundary; Unix unlink has no inode-conditional transaction.

Sessions use supported ephemeral-start/readback plus unsubscribe and actual
owned-server exit. There is no persistent fallback or profile-wide cleaner.
Persistent/unexpected thread readback and nonzero/unknown teardown retain a
cleanup gap. No existing human, persistent, foreign or live session is deleted.
Actual memory/session reclamation remains unqualified until a live encounter.

Cumulative DB/WAL/artifact bytes, event/attempt/job/alert counts and filesystem
entry counts gate admission. Held work is never quota-purged. Required results
and tombstones can eventually fill their bound: offline conservation/migration
is then required, not automatic history deletion. Budgets are admission controls,
not kernel disk quotas on authorized agent file writes. Already running writers
and external logs require the operator's storage limits. Empty generated attempt
directories and offline schema/evidence are retained here; there is no blanket
directory retirement. These limits must be included in deployment disposition.

## Verification and rollback

Tests use fake models and real owned fixture processes/SQLite boards. A01–A14
cover deduplication, invalid classification, real delegated receipt, crashes,
frozen batches, cross-controller slot races, six QA packages, response provenance,
late/capacity handling, process-vs-DONE, restart uncertainty, supported continuation,
exclusive recovery, recurring alerts and processing+24h cleanup/symlink holds.
These are fixture results, never live model/source/CI/provider acceptance.

Before activation, parent must collect independent assessment, live literal
Luna-low/Sol-xhigh bindings, supported ephemeral lifecycle/continuation/teardown,
effective MCP and delegation limits, and actual role grant/enrollment/adoption
with legacy/resource holds. The code does not self-accept those capabilities.

Rollback: stop new intake with SIGTERM, let the owned controller collect its
originals, preserve the journal/results/receipts/unknown holds, revoke exact role
grants from actual owners, and deliberately restore prior operational routing
under existing owners. Do not reset cursors, delete held journals, restart old
mutating tasks, replace collectors or purge profiles. Leave the additive board
grant/receipt audit records as evidence. Removing an unactivated checkout has
no service rollback effect; follow ordinary worktree retention rules separately.
