# Mutable workflow: local revisable execution

One concern: execute and durably revise caller-supplied work. Python 3.10+
standard library, SQLite and POSIX `flock`; no daemon, scheduler, resident agent, or
domain-policy owner in the base engine. The optional [runner judgment adapter](agent-adapter.md)
adds on-demand provider dispatch/collection without changing this engine contract.
This ACR-537 base slice expands ACR-536's
sequential executor into live graph surgery. The representation remains an ordered
sequence plus a movable execution position: arbitrary new nodes, replacement
ranges and jumps are allowed, not a whitelist of original edges. Execution remains
one local subprocess at a time; edits are admitted **during** that subprocess.

```sh
python /path/to/ai/tools/mutable-workflow/cli.py start /absolute/new-run --file plan.json
python /path/to/ai/tools/mutable-workflow/cli.py inspect /absolute/new-run --since 0
python /path/to/ai/tools/mutable-workflow/cli.py output /absolute/new-run --attempt 1
python /path/to/ai/tools/mutable-workflow/cli.py amend /absolute/new-run --file edit.json
python /path/to/ai/tools/mutable-workflow/cli.py resume /absolute/new-run
```

Run data belongs in caller-owned planning/scratch outside the checkout. `start`
requires a nonexistent directory and executes until a stop. `resume` executes
only ready work. `--max-steps N` limits additional attempts at durable boundaries;
zero initializes/reconnects without dispatching. `amend` commits intent without
starting another executor. A live executor may subsequently execute that intent
once its current worker has returned and if its step limit allows. Otherwise a
later `resume` is the continuation owner. Inspection is not liveness evidence.

## Public contracts (owned here)

### Plan and effect grants

`plan.json` has these required fields (and optionally the `recovery` registry
defined in the ACR-539 section below):

```json
{
  "purpose": "Exercise ordinary local work",
  "workers": {"local": ["/usr/bin/python3", "/absolute/local-worker.py"]},
  "steps": [{"id": "first", "worker": "local", "input": {"task": "example"}}]
}
```

Purpose, worker names, argv entries and IDs are nonempty text. Executable paths
are absolute; argv is literal, without shell expansion. Workers and initial
steps are nonempty. Each step has exactly `id`, `worker`, `input`; input is JSON
data. Current step IDs are unique. Editors may introduce arbitrary new steps and
inputs referencing these workers, but **cannot amend the registry or purpose**.
A replacement can reuse a removed step's display ID; its internal node identity
is always new. All original node definitions remain archived.

**Trust/effect boundary:** one trusted local principal, private run directory,
trusted worker programs. Filesystem permissions, not `actor`, control access.
The caller grants the registered programs with their inherited environment,
credentials and admitted inputs. Programs must enforce narrower input/effect
restrictions themselves. Unchanged argv does not imply unchanged effects from
arbitrary input. This is not a sandbox or authentication/authorization service.
Policy text, graph edits and repetition intent grant no new credentials, merge
rights or authority over another consumer's obligations. Do not select this local
slice for irreversible/external effects or untrusted workers/editors.

### Worker request and result

Selected argv receives one JSON object on stdin, cwd = run directory:

- `run_id`, `purpose`, exact `step`, run-local integer `attempt_id`.
- `node_id`: run-local string identifying this node incarnation, not its display ID.
- `basis_cursor`: pre-admission event cursor; `policy`: selected JSON policy (initially null).
- `edits`: full accepted amendments/recovery insertions at admission.

The request is persisted before dispatch and never reconstructed from a later
graph. The entire stdout must be exactly one JSON object with these fields:

```json
{"outcome": "success", "detail": "What actually happened"}
```

Outcome is `success`, `failure`, or `judgment`; detail is nonempty text. Zero exit
plus an admissible result is required. Missing/malformed zero-exit output becomes
`ambiguous`; nonzero exit becomes `failure` even if stdout claims success. Launch
failure has null returncode and explicit detail. Raw stdout/stderr bytes remain
available independently of interpretation. A valid result is a trusted worker
assertion, not an independently verified truth. Failure/cancellation/ambiguity
does not mean no effects happened.

### Atomic graph and policy amendments

`edit.json` has exactly:

```json
{
  "run_id": "UUID from inspect",
  "cursor": 3,
  "actor": "local-editor",
  "reason": "Why the revised outcome is appropriate",
  "effects": "Why continuing/repeating is safe within the existing worker grant",
  "operations": [
    {"op": "replace", "start": "first", "count": 1,
     "steps": [{"id": "replacement", "worker": "local", "input": "new work"}]},
    {"op": "insert", "before": null,
     "steps": [{"id": "followup", "worker": "local", "input": "followup work"}]},
    {"op": "policy", "value": {"basis": "amended-policy"}},
    {"op": "goto", "step": "replacement"}
  ]
}
```

Run ID and integer cursor must match the current committed view; actor, reason,
effects are nonempty audit text. `effects` is the editor's explicit reconciliation
basis, **not an engine assessment that repetition is safe**. The editor must
inspect relevant original outputs/missing evidence and respect actual authority.
For unresolved irreversible effects, stop and return to the effect owner rather
than assert a safe retry. This engine promises neither exactly-once effects nor
compensation. No permanent policy-skip permission system is imposed.

Operations are interpreted in order against the emerging graph, then all state,
edit history, event and cancellation updates commit atomically. Invalid fields,
references, ranges, duplicate current IDs, ungranted workers and stale contexts
error without committing any prefix. A second editor must inspect and rebase its
intent after a stale/busy rejection; do not blindly replay a stale cursor.

Each operation has **exactly** the listed fields:

| Operation | Fields besides `op` | Meaning |
|---|---|---|
| `insert` | `before`: current step ID or null; `steps`: nonempty step list | Insert before anchor or append at null. |
| `replace` | `start`: current step ID; `count`: positive integer; `steps`: step list (may be empty) | Replace any contiguous X-node range with arbitrary new nodes. Empty replacement removes the range. |
| `remove` | `steps`: nonempty unique list of current IDs | Remove those nodes from current membership, retaining archived definitions and all attempts. |
| `skip` | `steps`: nonempty list of current IDs | Keep nodes visible with `skipped` scheduling disposition; execution walks past them without completion credit. |
| `goto`, `return`, `retry` | `step`: current scheduled ID | Set the next position to that node. All three express explicit new execution intent; there is no hidden return stack. |
| `abort` | none | Stop future scheduling with workflow status `aborted`; does not cancel the worker or undo effects. |
| `policy` | `value`: arbitrary JSON | Replace the current declared policy basis, retaining previous bases in requests/events. This is not CRW policy accounting. |
| `cancel` | `attempt`: positive integer | Request cancellation of that exact attempt, separately from graph membership. |

**Position semantics:** edits before/after the current target preserve that
target, including a running assignment. Thus inserting *before* the current
node does not rewind to the insertion; compose with `goto` when that is intended.
Replacing/removing the current target selects the first replacement or following
node; skipping it walks to the next scheduled node. Appending after exhaustion
selects the first appended node. Other structural edits to an exhausted graph
preserve exhaustion; compose with a jump to run newly inserted/replaced past work.
Completed nodes remain scheduled graph members;
`goto` to one executes a new attempt and then proceeds forward, including further
previously executed nodes. Jumps do not claim bypassed nodes completed. Skipped
nodes cannot be jump targets; replace them to create new scheduled work. An empty
future can finish without any new attempts—this is not proof old work completed.

`abort` remains stopped across structural/policy edits. Only an explicit jump
reopens it. Abort in a composition is evaluated in order; a subsequent explicit
jump can therefore reopen it in the same atomic amendment.

**In-flight association:** one `active_attempt` owns current advancement credit.
Replacing/removing/skipping its target, any jump, abort, or a policy amendment
revokes that ownership. Policy amendment conservatively schedules a new attempt
under the new basis; even unchanged work is not silently credited across bases.
The original subprocess continues unless separately cancelled. Its collector
still persists the original request, full output and classification with
`credited: false`; it cannot finish replacement work or advance the new position.
Future insertion/removal that preserves the running target preserves its credit.
Past credited results are never retrospectively recertified under amended policy.

### Cancellation and collector loss

Attempt drilldown exposes `cancellation` separately from `outcome`:

- `not_requested`: no cancellation intent; supersession/removal/abort alone leaves this unchanged.
- `requested`: committed intent, not termination evidence. The live collector
  checks requests while waiting for its subprocess (50ms communicate timeout).
- `confirmed`: the kernel accepted the collector's SIGTERM submission and the
  collector subsequently observed direct-worker exit `-15`. This confirms the
  **termination observation**, not that this request caused it. A competing
  SIGTERM sender cannot be distinguished from wait status alone. The attempt's
  scheduling outcome is `cancelled`; `output.result` retains the original worker
  classification (`failure` for nonzero exit), with unmodified bytes/returncode.
- `unavailable`: result already settled, collector recovery established loss of its
  live handle, the collector observed exit before submission, submission reported
  process disappearance, or collection did not observe SIGTERM termination after
  an accepted submission. Natural completion can race cancellation; its original
  result is retained and can advance an otherwise-current assignment.
  “Unavailable” does not mean execution failed or that no signal was submitted.

The amendment event records request intent. `cancellation_signal_submitted`
records normal return from the actual POSIX `kill(pid, SIGTERM)` syscall, **not
signal delivery, handler execution, or causal responsibility for exit**.
`attempt_returned` records final cancellation classification. The collector polls
before submission: an already-observed exit makes cancellation unavailable and
emits no submission event. If exit races between that poll and the syscall, the
kernel can accept a signal for an unreaped exited child; this still only records
submission. In particular, independent SIGTERM in that interval can produce
`confirmed`/`cancelled` with the same evidence as collector-induced termination.
Consumers needing sender attribution must treat it as unknown, not infer it from
those labels. Original worker classification remains independently inspectable.

Submission uses only the live direct child's PID under sole collector ownership
of wait/reaping; an unreaped child retains its PID. The supported CLI has no
concurrent child reaper and requires normal SIGCHLD disposition (not inherited
SIG_IGN/automatic reaping or an embedding application's custom reaper). Launch
rejects a non-default SIGCHLD disposition before starting a worker; the admitted
attempt remains explicitly uncollected for normal recovery/reconciliation. A cached
PID is never signalled on resume. No descendant cancellation is promised.
A submission event alone is not confirmation. If the executor disappears after
submission, recovery cannot infer termination. There is no force-kill escalation.
A worker ignoring SIGTERM remains pending until it returns; the bounded-worker
envelope still applies. A cancelled current attempt stops until explicit new
intent. Cancelling a superseded attempt does not cancel replacement work.

Earlier version-2 candidate records named `cancellation_signal_sent` overstated
normal `Popen.terminate()` return, which can be a no-op. They are retained as
historical records, not upgraded to submission/delivery evidence; earlier
`confirmed` results retain that evidence limitation. New collection uses the
submission event and does not rewrite earlier results/events.

After executor loss, `resume` under newly acquired executor ownership records
uncollected attempts as `orphaned: true`, with missing output and unknown effects;
pending cancellation becomes unavailable. Ready/running workflows become
ambiguous even when that worker was superseded. No automatic replay occurs.
The editor can then record reconciled new intent via `amend`; that does not fill
old missing results. Worker-backed recovery, when separately admitted below,
can collect a later result while retaining the earlier interruption evidence. The base collector does not salvage arbitrary output after collector death or
accept externally submitted results. The optional worker-backed recovery below
can redeliver an exact request under its effect-owner contract. Live-collector late
returns across edits are supported and tested; arbitrary crash salvage is not.

### Existing failure-informed recovery entry

`judge --file response.json` remains the first slice's narrower, useful operation.
The response has exactly `run_id`, `cursor`, `blocked_step`, `actor`, `reason`,
`insert` (nonempty new steps). It is admitted only at current failure/judgment
boundaries and inserts recovery **after** the blocked step, continuing there
instead of retrying it. The old failed/judgment result remains unchanged. The
external fake judgment fixture reads actual failure output and chooses new work;
no semantic agent is selected. `amend` supplies the broader operations at all
states, including explicit effect-reconciled intent after ambiguity.

### Inspection and caller outcomes

`inspect` returns `{current, events, cursor}` in one read transaction. Current
includes original purpose/registry, current steps/position, node ID sequence and
archived `nodes` (`step`, scheduling `disposition`), policy, workflow status,
active attempt, run/version/cursor, attempt summaries and edits. Node scheduling
disposition (`scheduled`, `removed`, `skipped`) is **not historical execution
outcome**; summary/drilldown and amendment events explain actual execution and
abort/jump decisions. Summary `id` references `output --attempt ID` and includes
step display ID, node incarnation and observed outcome.

Events have `cursor`, `kind`, `detail`. `--since` returns strictly later committed
events through the returned cursor. Cursors are monotonic, run-scoped and retained
across supported restarts; negative/future cursors error. No pruning/reset exists.
Rejected edits are returned to their callers, not silently recorded as accepted
history. Short-lock contention errors are recoverable by inspection/rebasing.

`output` returns exact request, observed outcome, output, cancellation and orphan
status; collected results also include `credited` (whether this return owned
current settlement, not semantic verification). Output has `returncode`, lossless
`stdout_b64`, `stderr_b64` and original worker `result` classification.
Cancellation scheduling is represented by attempt `outcome`, not by rewriting
that worker classification. Null output means **not
collected**, never empty successful evidence. Unknown attempts and missing/corrupt
storage error. This private view can expose worker inputs and printed credentials;
no transcript discovery, redaction or hostile-local tamper protection is claimed.

Mutations print current JSON and use these exit codes:

| Code | Meaning |
|---|---|
| 0 | `success`: revised traversal exhausted, not original obligations certified |
| 1 | `failure`: blocked failed attempt |
| 2 | `judgment`: unresolved worker judgment need |
| 3 | `ready` or `running`: work remains / original collector owns execution |
| 4 | `ambiguous`: missing substantive result or collector-loss uncertainty |
| 5 | command/storage/contract error; JSON stderr `outcome: not_confirmed` |
| 6 | `aborted`: scheduling stopped by amendment |
| 7 | `cancelled`: accepted cancellation submission plus observed direct-worker SIGTERM exit; cause unknown |

After code 5 inspect durable state: it does not assert that no work ran. Abrupt
signals may instead yield OS signal exit without JSON. Successful `inspect` and
`output` exit 0 regardless of workflow outcome; read the state, not that exit.

## Durability, versions and operating envelope

SQLite state/events/attempts commit together with `synchronous=FULL`. A
nonblocking `executor.lock` covers each driver invocation; a second executor
errors, not mistakes a live owner for an interrupted one. A separate short
`writer.lock` covers admission, amendment and result settlement. Settlement reloads
current state and the **original attempt by ID** under this lock; no whole-executor
snapshot overwrites edits. Edits use nonblocking acquisition; internal settlement
waits for short writers so contention does not discard a returned result. All
writers must use the CLI. Never move/delete a live run or manually edit its DB.

Completion-first changes the cursor, rejecting the stale edit. Edit-first retains
both the amendment and the eventual result, with settlement based on surviving
ownership. Result plus advancement commit once together. Competing editors cannot
both commit the same cursor. There is no claimed arbitrary-external-effect
exactly-once guarantee behind these bookkeeping properties.

New runs use **storage version 2**. There is no automatic migration of version-1
runs: state-based commands reject them explicitly without relabeling historical
results. Use the original ACR-536 runtime to inspect/continue those runs; do not
reinitialize over them. The first slice's successful execution/recovery/path
behaviors remain tested for new runs. This is intentional storage evolution,
not a claim that old run data was migrated or that old tests exercised new races.

Local filesystem only; no NFS, multi-host or hostile same-user claims. Tested:
fresh CLI continuation after durable steps/edits, executor death after admission,
live edits/late returns, competing edits and completion/edit races using controlled
local subprocesses. Not qualified: power-loss directory creation, disk full/
corruption repair, lost-collector output salvage, arbitrary descendant termination,
provider sessions in this base engine, or irreversible effects. The optional
adapter has its own fake-provider verification and collection limits. Initialization failure leaves an
unusable directory and explicit error, never automatic overwrite.

Workers must terminate with bounded output. Capture, JSON state and cumulative
history are in memory, without production quotas, streaming or measured capacity
claims. No daemon auto-recovers an owner; the caller owns `resume` and reconciliation.

## Discovery and verification

`VALUES.md` and `tools/README.md` place generic mechanics here. Domain compositions
remain outside the engine. Scheduler, workflow_index, WU migration and legacy
operational-contract transport are not runtime dependencies. Runner CLI Usage/
Inspecting a Run at `/home/nes/projects/agent-runner/trunk/README.md` owns a distinct
provider/session protocol; the optional adapter selects that seam, not the historical
legacy result extractor. The base engine itself has no provider dependency. Fake results establish no installed-provider compatibility
or reviewer efficacy. No deployed workflow/operator or CRW adapter is selected.

Implementation: `runtime.py` owns persistence/admission/collection/settlement;
`surgery.py` owns atomic future-intent operations; `cli.py` owns command/exit mapping.
Downstream owners discover current contracts here rather than a copied ticket schema.

```sh
python -m pytest -q tests/test_mutable_workflow.py tests/test_mutable_workflow_surgery.py
```

Pytest is a test-only dependency. The first suite preserves the working slice and
strengthens the nonzero-output oracle to full expected bytes. The surgery suite
uses local fake effects and socket handshakes—not sleep-based admission guesses—to
exercise all edit families, same-display-ID replacement identity, explicit
reentry, policy bases, retained raw binary bytes, live supersession, cancellation,
collector loss, atomic invalid compositions and stale/racing writers. These are
bounded deterministic mechanism controls, not semantic-agent trials or universal
safety/efficacy proof.

## ACR-539: bounded recovery and durable diagnostics

Existing `amend` retry/return/goto remain **new execution intent**, not safe
redelivery. An optional immutable plan field selects a separately implemented
worker contract (never infer this capability from `effects` text):

```json
"recovery": {"local": "deduplicated-attempt-v1"}
```

Only opt in after the actual registered program implements the contract below.
A lying or changed worker cannot be made safe by this declaration. Existing
plans omit the field and have **no worker-backed redelivery capability**.

```sh
python tools/mutable-workflow/cli.py recover /absolute/run --attempt 1
python tools/mutable-workflow/cli.py recover /absolute/run --attempt 1 --redeliver
```

`recover` takes sole executor ownership, records collector loss where applicable,
and asks the registered worker for a read-only recovery observation. It returns
`{current, attempt, next_action}` with the ordinary **current graph status** exit
code. Without `--redeliver` it never repeats the work. Without a selected worker
contract it errors usefully: inspect the original request/output and reconcile
with the effect owner before expressing new intent. The original worker may
still be in flight; executor ownership is not worker termination evidence.

### `deduplicated-attempt-v1` — effect-owner obligations

Normal delivery keeps the exact original worker request, including
`run_id`/`attempt_id`. That pair is the effect identity. The program must:

- Bind that identity to the **entire exact request**, rejecting changed payloads.
- Serialize concurrent original/repeated deliveries and durably deduplicate its
  effect, retaining the original result for replay. Commit an effect together
  with its replayable result, or have an equivalent effect-owned guarantee.
- Make its recovery query read-only and safe while an original worker may still
  be running. Return `unknown` whenever its actual guarantee cannot be upheld.
  A local journal appended before an arbitrary remote effect is **not** enough.

The query is one stdin JSON object to the same registered argv:

```json
{"protocol":"deduplicated-attempt-v1","operation":"recovery_query","request":{"...":"entire original request"}}
```

The whole stdout must be exactly one object with `protocol`, `run_id`, integer
`attempt_id`, `disposition` (`retry_safe` or `unknown`), and nonempty `detail`.
Protocol and identities must match. Only zero process exit plus an admissible
`retry_safe` assertion permits the explicitly requested redelivery. Missing,
malformed, foreign, nonzero or unknown replies do not. Query raw output and its
interpretation are retained in `worker_recovery_observed` events and attempt
`recovery_observations`; they are worker assertions, not independent proof.

Redelivery durably records `attempt_redelivered` before dispatch, uses the
**unchanged original request and attempt identity**, and settles through the
ordinary result/advancement transaction. It does not create a new graph attempt,
rewrite a prior collected failure, or recertify superseded work. The original
`interrupted` event and `orphaned: true` remain; a subsequently recovered output
is not evidence that the earlier collector captured it. A settled attempt is an
idempotent read. Internal duplicate identical result receipts do not advance
again; conflicting receipts are rejected without replacing original evidence.
There is no public arbitrary-result-injection endpoint.

Pending cancellation becomes unavailable on loss as before. Recovery does not
signal a cached PID, establish exit, or erase earlier submission evidence.
Explicit redelivery authorizes another delivery under the worker guarantee, not
an assertion that cancellation completed. `unknown` requires effect-owner
reconciliation; ordinary amendments retain the caller's explicit new intent,
not an engine-generated safety verdict.

The fake `recoverable_worker.py` demonstrates the guarantee **only for its atomic
SQLite insertion plus stored result**. Its two deliveries can create one effect;
a new attempt intentionally creates a different effect. It does not establish
exactly-once effects for arbitrary programs or external services.

### Consistency and interruption evidence

State-based commands, including `output` and agent operations, now examine a
consistent read snapshot for contiguous event/attempt identities, matching
admission/return events, attempt summaries/archive references, active target,
position/exhaustion and basic collected-output shape. Missing or inconsistent
information errors rather than resetting a run to success. These are bounded
logical diagnostics, not complete corruption detection, hostile-tamper
protection, repair, power-loss qualification or an authenticated event journal.
Missing both an artifact and every independent reference to it can remain
undetectable. Exchange sequence/key/context checks are similarly bounded.

The historical missing-event probe (events 1,3 with cursor 3) previously resumed
as success. New tests inject that same loss and require useful failure from
resume/inspect/output. The historical writer-contention failure remains a
failure: an effect-written socket notification never guaranteed writer
availability. Collection now avoids acquiring the writer lock when no
cancellation is requested, rechecking under the lock when it is requested.
Other writer contention still returns a real busy rejection; a deterministic
control holds that lock, checks rejection/no prefix, releases it, reinspects the
unchanged basis and successfully retries the edit while the worker is held.

`tests/test_mutable_workflow_recovery.py` adds process faults before/after
initialization, admission, dispatch, fake effect, result receipt, return commit
(including inside its transaction), amendment and agent application. Tests use
actual call seams and fake executables, not production fault flags or live
agents. The existing cancellation/session/contrary-prefix controls remain
selected. Run it alongside the three existing suites and secret-capture suite.
Storage remains version 2 with additive optional recovery/evidence fields; no
old results are migrated or retroactively qualified. Older runtimes are not
qualified to exercise these new contracts.


### Collection ownership and retained limitations (ACR-539)

The optional agent adapter now gives each ask/collect a finite POSIX owner that
survives its CLI controller's death through capture and collection; see
[the actual ownership/reconciliation contract](agent-adapter.md#persistence-collection-and-outcomes).
This is not automatic replay, retroactive salvage, or provider completion based
on a receipt/PID. Owner loss can still leave submission/effects unresolved.
Graph storage version 2 does not imply agent-history compatibility: old agent
history remains intentionally unsupported even when graph inspection succeeds.
Worker same-attempt redelivery retains historical orphan evidence, so attempt
cancellation is unavailable during it; abort stops graph scheduling, not all
live deliveries. No delivery-cancellation system is introduced.

Durable-history validation indexes attempt admission/return events once per load,
rather than scanning all events twice per attempt. It still reads the complete
history and validates all exchanges where selected; no capacity/latency or
universal corruption-detection guarantee follows.

## Compact inspection and source-bound cursors

Use [the private inspection entry and contracts](inspection.md) for paged,
source-bound graph/exchange changes, compact current/blocked work, node/replacement
and authority drilldown, and explicit present evidence/session checks. The
existing graph-only `inspect --since` remains a full logical-audit surface, not
an all-source cursor. New run writes include transactional inspection projections;
existing unindexed runs require explicit authorized indexing for the compact view.
CRW policy publication/roster integration remains a separately owned seam, not an
already deployed joined-policy capability.
