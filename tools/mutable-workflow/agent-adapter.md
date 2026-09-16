# On-demand runner judgment adapter

`agent_cli.py` is a purpose-built workflow controller: it owns fresh dispatch,
resume, durable exchange records, collection and optional graph application. It
is not a worker registered under `runtime.py`, an ordinary agent delegation
wrapper, or a parent-agent relay. A script chooses **when** judgment is needed and
calls `ask`; no resident agent, scheduler, automatic domain policy or new runner
service is needed. The existing `cli.py` owns ordinary worker execution and graph
surgery. Its contracts and historical results are unchanged.

This entry is optional. Runtime-owned invocation requires the actual caller's
execution authority and compatible loaded instructions under
[`workflows/agents-cli.md`](../../workflows/agents-cli.md#purpose-built-workflow-runtime-dispatch).
Source installation never overrides an active session's restrictions. The
ACR-538 tests execute **only fake process executables**, not `agents`, a model,
provider session, external effect or live efficacy trial.

## Entry and caller-owned authority

Use an existing version-2 run in private planning storage. Python 3.10+, POSIX
fork/setsid/flock and PyYAML (used by the shared secret-capture helper) are required.

```text
python tools/mutable-workflow/agent_cli.py ask /absolute/run --file request.json
python tools/mutable-workflow/agent_cli.py show /absolute/run --key judgment-1
python tools/mutable-workflow/agent_cli.py collect /absolute/run --key judgment-1
python tools/mutable-workflow/agent_cli.py owner /absolute/run
```

`ask` accepts exactly this request shape (paths below are placeholders, not
installed-executable claims):

```json
{
  "key": "judgment-1",
  "question": "Why did the current work stop, and what bounded next intent is appropriate?",
  "answer": null,
  "config": {
    "runner": ["/absolute/path/to/agents"],
    "model": "gpt-xhigh",
    "project": "/absolute/isolated/worktree",
    "contract": "/absolute/resolved-operator-contract.yaml",
    "authority": {
      "owner": "actual accepting caller and collecting owner",
      "access": "actual permitted files/evidence",
      "effects": "actual bounded local effects; no external mutation",
      "delegation": "propose registered investigation work; no direct child launches",
      "apply_edits": true
    }
  }
}
```

The caller resolves the applicable contract first; `contract` must contain the
existing `operator-contract-v1` schema and valid `secrets` list (or the existing
Markdown Contract block). This adapter validates **capture admission**, not every
operator-specific input/stop condition. Supply a genuinely applicable resolved
contract, not a dummy secrets waiver. For an ad-hoc assignment the caller supplies
its actual resolved capture contract. `runner` is a trusted literal argv prefix
with an absolute executable, permitting an injected fake executable in tests.
There is no shell expansion. `project` must be an isolated worktree for authored
tracked changes; this adapter checks existence, not Git isolation or authorization.

This entry selects **ad-hoc model invocation only**: explicit `-m` on fresh and
resume. It neither resolves model aliases nor accepts `agent_file`. Current runner
`dispatch.rs::validate_top_level_resume_cli` rejects `-a` on resume; silently
reading a defined agent's model and overriding its ownership would not implement
that contract. Defined-operator orchestration is not advertised by this slice.

The same run has one conversation configuration; subsequent requests must retain
it exactly. `key` identifies a caller request, not a provider session. Repeating
the same key and request returns its durable record without launching or applying
anything again; changing a bound request errors. A new key is new caller intent,
not an automatic retry. Pending/unknown preceding work blocks new keys. A returned
authority question requires a nonempty caller `answer` before continuation;
answers and unanswered original questions remain in history. Answers do not alter
the immutable authority or worker grants.

Like the base engine this is a **trusted-local** envelope, not a sandbox. Prompt
text transports access/effect/delegation bounds; it cannot prevent an untrusted
model/tool from using inherited credentials. Do not select this entry where those
limits require enforcement not already supplied by the environment. The adapter
never launches model-requested arbitrary argv, fetches model-selected artifact
paths, changes the worker registry/purpose, or grants external effects. Only when
`authority.apply_edits` is true and the supplied delegation/effect/assignment bounds
permit it may an agent propose investigation by inserting caller-registered
workers through the existing amendment surface. Registration alone is not delegation
authority. With edits disabled, composed instructions permit only question/observation
responses and preserve the caller-supplied inquiry route, named root/collector and
recovery-only scope; they do not invite worker insertion or graph edits. Delegation
is caller-owned text, not a boolean or a provider-parsed role policy. The caller's
next ordinary `cli.py resume` executes those workers; judgment does not automatically drive or repeat local work.

## Provider contracts actually consumed

Owning checkout: `/home/nes/projects/agent-runner/trunk`:

- `README.md`, CLI Usage / Inspecting a Run / Resuming a session: fresh
  `-m MODEL -p PROJECT -f PROMPT`; headless
  `resume --session-id UUID -m MODEL -p PROJECT -f PROMPT`; `trace UUID --json`;
  `session locate UUID --json`.
- `crates/oulipoly-runtime/src/trace/mod.rs`: `requested_id`, exact root
  `invocation.id` / `agent_runner_invocation_id`, actual invocation status,
  `success`, physical `exit_code`, `finished_at`, `stale_running`, root session
  identity/capture/acceptance and `returned_artifacts`. No SQL schema coupling,
  private transcript discovery, alias probing or trace-children result substitution.
- `crates/oulipoly-state/src/result_envelope.rs` and README's merged external
  stream rule: first runner invocation precedes arbitrary provider payload;
  successful exit permits the **last shape-valid matching** `OULIPOLY_RESULT`,
  not an earlier marker-shaped provider payload. Full merged bytes are retained.
  The adapter does not use the narrower legacy operational-contract extractor.
- `executor/mod.rs` supplies actual fresh capture methods;
  `executor/cli/resume/acceptance.rs` and resume `terminal.rs` explain why
  `rejected`, nonzero exit and attempted target capture do not prove nonadmission.
- `session_metadata_cli.rs`, `commands/session_locate_export/{mapper,formatter}.rs`
  and `json_error.rs`: exit **10** plus `error.code: session-not-found` is the
  selected pre-submission lookup rejection. Generic exit 1, unsupported storage,
  malformed/foreign locations and ambiguity do **not** select fallback.
- `crates/oulipoly-agent-messenger/src/lib.rs::ReturnedArtifactRef`: references
  are retained as returned evidence, not fetched, rehashed or certified content.

For a previous completed exchange with a captured session, lookup runs **before
submitting this new question**. A supported unavailable target selects ordinary
fresh invocation with `continuity: fresh_fallback` and its exact lookup evidence.
No resume was submitted in that case. A completed exchange whose trace reported
no session identity can also continue explicitly fresh: this is missing reported
identity, not a claim that the prior provider session never existed. An identity
present but not established does not authorize this fallback.

After a submitted resume, only the exact target's trace `resume_acceptance:
accepted` establishes `same_session`; matching target IDs or successful exit alone
do not. `rejected`, `unconfirmed`, null acceptance, trace failure, or missing
identity remain pending. No provider phrase matcher, broad Rejected-to-fresh
mapping, or specialized `fresh_continuation` coordinator is used. That specialized
accepted-but-completion-unconfirmed contract is not the missing-target fallback.

## Context, result and real graph edits

Each prompt contains purpose/current graph/policy, the run-scoped event interval
since the last collected exchange's prompt cursor, exact basis cursor, prior
questions/answers/attempt identities and evidence references, original worker
attempt summaries, actual caller bounds and continuity label. Full old contexts
are not recursively embedded. It supplies executable `inspect` / `output` argv
for deeper evidence on demand; no private provider transcript is copied.

The response contract is owned in `agent_adapter.py::response_contract` (shared
envelope plus authority-conditioned instructions). The agent emits exactly one
bound line:

```text
MUTABLE_WORKFLOW_RESPONSE={"exchange_id":"prompt exchange UUID","run_id":"workflow UUID","basis_cursor":3,"kind":"question","detail":"What authority applies to the proposed effect?","edit":null}
```

Kinds are `observation`, `question`, `edit`. `detail` is nonempty text; `edit` is
null except for an exact existing `cli.py amend` object. A substantive response
is the agent's assertion, not an independently verified judgment. A response is
usable only after complete local capture and source-bound runner trace completion: succeeded, success true,
integer physical exit zero, a finished timestamp, and no stale-running projection.
A recorded nonzero runner exit prevents application even if other evidence claims
success. Local capture is established by the stored zero return code: transport
returns only after reading EOF, publishing the redaction carry tail and waiting
for the process; submission persists that result before response collection.
After collector loss, null local exit remains null unless the ACR-539 complete
local capture receipt below was actually published and validates. Durable trace can establish
upstream completion, but cannot establish complete local capture. Even a unique
bound response in retained bytes remains evidence only: a missing suffix could
contain another response that would prevent application. No response kind is
settled from that prefix, and no graph edit is applied.

For edits, both the response and amendment must retain the original run/cursor.
`apply_edits: true` admits application through **the existing `surgery.amend`**,
under its writer lock, full field/registry/cursor checks and transaction. The
exchange's `application: applied` record commits in that same transaction. Death
after commit cannot cause another jump/cancel/edit. Stale/invalid/unauthorized
edits return intact with `application: rejected`; no automatic cursor rewrite or
prefix application occurs. The next caller question may seek a new decision from
current evidence. Applying an edit never marks previous work correct or runs its
new steps. A model response alone grants neither decision nor mutation authority.

## Persistence, collection and outcomes

Additive `agent_exchanges` and version-1 `agent_history` tables live in the existing run DB; graph storage
version 2 and worker-attempt contracts do not change. Agent exchanges have their
own ordered keys; they do not manufacture graph events or increment the graph
cursor. `cli.py inspect/output` remains graph/worker evidence; `agent_cli.py show`
returns the separate agent exchange and source paths. Existing version-1 rejection
and original historical engine results are not migrated or relabeled. An existing
pre-ACR-539 exchange table without the recovery history marker is rejected as
unsupported, not bootstrapped over possibly missing exchanges; use its original
runtime for inspection/continuation. Graph version 2 is **not** an agent-history compatibility indicator: graph inspect can succeed while agent show/collect/ask reject old history. No automatic agent-history migration is supplied.

A dedicated collector lock excludes concurrent dispatch/collection for the run,
not live graph edits or `show`. Each `ask` or `collect` starts one finite local
**collection owner**, under the purpose-built runtime's existing authority.
The synchronous CLI controller waits for that owner, but is not its capture
lifetime. `collection_owner.py` takes the lock before forking, with no DB
connection or provider process yet open. The owner inherits the same flock open
file description, creates a separate POSIX session, disconnects controller
standard streams, and owns the existing operation through lookup, submission,
EOF/redaction/exit/receipt capture, trace observation, and joint application commit.
Closing the controller's lock descriptor on death does not unlock the owner's
remaining descriptor. Runner subprocesses do not inherit that descriptor.
Separate sessions do not provide host-restart, owner-kill, cgroup/job-tree-kill
or machine-failure survival; whole-workload termination may still kill both.
The owner exits after this single operation; it never schedules, restarts,
replays, or automatically drives workers. This is not a general daemon or a
replacement for provider supervision. Use this entry as a single-threaded CLI,
not a fork-from-multithreaded-host API.

Submission intent still commits **before** runner process creation. Merged bytes
flow only through the existing declared-secret sink. No raw second sink or
truncating output relay is added. Controller death before/during/after capture
no longer itself abandons the owner's stream, carry tail, receipt or collection.
Controller death does **not** revoke already granted operation/edit authority;
the owner can still apply an originally authorized edit against its original
basis. Ordinary graph surgery remains concurrent and can make that edit stale.

`owner RUN` is a read-only ownership diagnostic (exit 0 for a successful
observation, **not execution completion**). It samples lock availability and
returns the latest owner record path, intent, started/result-file presence and
reconciliation guidance. Busy is an observation of a lock holder, not a PID
liveness or provider-effect claim. During a concurrent start its latest pointer
and lock sample may describe different instants. `agent-owner.json` points to
one unique directory under `agent-owners/`; older directories are retained.
`intent.json` records version/id/command, not unvalidated caller payload;
`started.json` records diagnostic PID/session, never signaling authority;
`result.json` atomically retains either the operation's result or a structured
error. Its presence is not a receipt or successful response. Temporary files
are never consumed. Full result records contain private exchange context just
like the DB: retain the entire run privately. They add storage per command.
A replacement controller uses `show` and explicit `collect`, not old PIDs or
owner-result presence to establish response completeness.

If the **owner** dies, a waiting controller reports structured exit5 uncertainty
including its observed owner exit. If both die, lock-free `owner` observation
plus explicit `collect KEY` exposes retained exchange/receipt evidence. Lock
acquisition never proves that the original runner stopped. A new collection
owner makes at most one trace observation and **never dispatches/resumes a
model**. Published complete receipts can recover local exit; prepared records
can be classified not-submitted under sole ownership. Pending-without-receipt
or without invocation identity remains unresolved, blocks new keys, and never
licenses prefix application or replacement submission. If death preceded the
fork and exchange creation, collect reports unknown key; a subsequent explicit
ask is new admission, not automatic retry of an uncertain provider dispatch.
Returned/not-submitted exchanges remain idempotent reads.

Returned JSON distinguishes `state`, `continuity`, `target`, established `session`,
`acceptance`, local `returncode`, `terminal_result`, durable `completion_basis`,
raw-log path, trace-observation paths, returned artifact refs, substantive
`response`, and `application`. States:

- `prepared`: local context retained, no durable submission intent yet. Under
  collector ownership `collect` now records this interruption as `not_submitted`:
  the owner always commits pending intent before runner process creation. It does
  not dispatch; a new explicit key may continue.
- `not_submitted`: a live pre-submission failure was observed; error/lookup remains
  visible. A new key can retry explicit caller intent without losing the last
  established session or its since-cursor basis.
- `pending`: submission/completion/usable response remains unresolved; no new key
  can launch. Failed and partial streams, attempted session and trace evidence stay
  available. Generic failure is not silently turned into a fresh request.
- `returned`: a completed, bound response was collected. Read `application`:
  `no_edit`, `question_to_caller`, `applied`, or `rejected`. This is **not workflow
  completion**, review safety, question resolution, or merge authority.

For ask/collect/show, CLI exit 0 means `returned` (including questions and rejected edits); exit 4 means
another retained state. Exit 5 is a command/contract/storage error with JSON
`not_confirmed`; inspect durable state, do not infer no effects. `show` uses these
same exchange-state exits. Abrupt signals may have only the OS exit.

Known limits remain explicit: loss before a recoverable invocation marker cannot
be settled by trace-by-ID; no unconditional resubmission or caller-manufactured
completion is provided. A missing/malformed/truncated response cannot be rebuilt
from a mailbox receipt or unrelated artifact. The selected trace/CLI contract
exposes no complete substantive-output retrieval basis after local capture loss;
upstream delivery success is not an acknowledgement of this collector's retained
bytes. Retroactively settling already-lost bytes requires an independently supported
complete-output recovery contract, not supplied here. The finite owner preserves
future ordinary delivery across controller loss; it does not survive its own
loss or recover historical unreceipted bytes. Owner loss after EOF but before publishing either local completion record remains
conservatively pending; the receipt below closes only the subsequent DB-record gap. Unknown acceptance, including
providers whose validated external acceptance is not exposed in the selected
trace field, remains a caller-owned gap. Different migrated session identities
are not attested as same-session by this adapter. Terminal provider failures are
retained for reconciliation, not automatically retried. The first invocation marker is the selected trace root; multi-invocation/load-balancing
command streams are not aggregated into one successful exchange here. Their complete
logs remain evidence; a failed first root cannot be upgraded using a later root.
No runner repair or speculative AGE dependency is included.

Secret capture validates the resolved contract and redacts nonempty declared
literal environment values before stdout/disk publication, preserving other
bytes. Caller context containing known literal secrets is rejected rather than
silently changing its authority/graph meaning. This is not universal secret
recognition (encoded/derived values, undeclared secrets and pre-existing worker
artifacts retain their original limits). Log redaction may make identity/JSON
unusable; that remains a collection gap, never a bypass to raw capture. Collection-owner
loss can lose a redaction carry-buffer tail or bytes still in transit; retained
bytes are partial evidence, not reconstructed full output.

Local filesystem/trusted processes only. Children must terminate with bounded
output. No timeout-kill policy, descendant control, quotas, power-loss/disk-full
recovery, hostile-local protection, or installed/live provider compatibility is
claimed. The prompt restriction on direct child dispatch is an instruction, not
a tool sandbox. Applicable operator obligations and external authority remain
with the caller. Root still owns decision/currentness verification and wider
consequence observation before delivery.

## Deterministic verification

`tests/test_mutable_workflow_runner.py` injects a Python process executable through
this actual CLI/transport boundary. It exercises real prompt files, wire parsing,
trace/lookup projection, locks, persisted records, existing evidence commands and
actual `amend`/worker execution. Socket barriers cover live stale returns and
collector death without sleep-based admission guesses. These are mechanism
controls, not provider/model efficacy, live runner invocation or sandbox proof.

```text
python -m pytest -q tests/test_mutable_workflow.py tests/test_mutable_workflow_surgery.py tests/test_mutable_workflow_runner.py tests/test_mutable_workflow_recovery.py tests/test_mutable_workflow_owner.py tests/test_secret_safe_capture.py
```


## ACR-539 complete local capture receipt and owner-loss boundary

For new exchanges `capture_protocol: local-receipt-v1` selects a receipt at
`runner.log.capture.json`. Transport first drains EOF through the existing
secret-redacting sink, publishes the carry tail, waits for process exit, closes
and syncs the log, then atomically publishes the receipt before returning to
`submit`. The receipt has exactly `version: 1`, `bytes`, `sha256`, and integer
`returncode`, describing the **entire retained redacted merged log**, not raw
secret bytes or upstream spool delivery. Temporary receipt files are never used
as completion evidence.

If the collection owner dies after that publication but before storing its exit in
the exchange, `collect` validates the complete log against the receipt and can
recover that local exit. A mismatch, malformed receipt or conflicting stored
exit is not success. New exchanges require this receipt as well as zero exit
and existing exact-root trace/session/response checks before application.
Missing receipt plus successful trace still retains trace/artifact evidence but
cannot settle a prefix. Records without the supported `capture_protocol` are rejected, not upgraded
from their older recorded-EOF semantics; use the original runtime to inspect
those historical runs. No receipts or history markers are invented for them. Returned records remain idempotent historical reads, not ongoing audits
of artifact presence.

The receipt is a local trusted-collector assertion, not authentication against a
hostile same-user writer, universal storage integrity, or a power-loss guarantee.
Its digest does not establish provider truth, acceptance, output authorship or
model efficacy. Secret redaction can still render a response unusable. Separate
trace observations also get receipts because they use the same capture owner;
those receipts never substitute for the dispatch log's receipt.

The existing method still handles a lost provider session through pre-submission
`session locate` / explicit fresh fallback **after a returned exchange**. The
new fake control recovers a receipt-backed edit and then exercises that route;
it does not conflate capture recovery and session existence.

### Concrete capability boundary returned to the caller/root

There is still no safe implemented recovery for **owner** death during capture, between
EOF/wait and receipt publication, or after pending intent but before a retained
invocation identity. Neither a caller-supplied success statement, generic
Rejected/exit status, transcript location, nor a retained prefix authorizes
replay or response application. The pending exchange remains owned by its named
caller; there is no automatic new-key bypass.

Current runner source does retain sealed per-invocation output in
`crates/oulipoly-runtime/src/executor/output_spool.rs::persist_for_invocation`,
with metadata owned by `crates/oulipoly-state/src/db/invocation_artifacts.rs`.
But the selected public `trace --json` DTO in
`crates/oulipoly-runtime/src/trace/mod.rs` supplies no complete-output retrieval
descriptor; `session locate` returns session metadata, not this exchange's full
merged response universe. This adapter does not infer a private path, read real
private invocation payloads, or invent a provider endpoint.

The selected outcome is future durable ownership independent of the CLI
controller, not retroactive salvage or a provider output-fetch invention.
The actual runner also supports caller-stable `--submission-token` for an
existing **resume target** (usage CLI and `run/resume/execution.rs`). Its
mailbox submitted-input row establishes admission/target/payload identity, not
complete response or task completion. There is no corresponding established
fresh-launch token association. This adapter does not adopt tokenized resume:
its surviving owner consumes ordinary supported delivery; owner loss remains
explicit rather than claiming a token can recover the complete stream. Existing
untokenized pending exchanges are never retroactively associated or resubmitted.

Attempt-oriented cancellation during worker same-attempt redelivery remains
**unavailable** because the historical orphan fact is retained. Killing only a
new delivery would not establish termination of an unknown original worker.
Graph abort can stop scheduling without terminating either delivery. The finite
agent owner likewise adds no delivery-cancellation or cached-PID signaling
system: controller termination is not owner cancellation, and owner termination
is not proof all work stopped. Bounded workers/providers and explicit uncertainty
remain admission premises, not newly measured production guarantees.


`agent_history` records the version and exchange count in the same transaction
as each exchange insert/update (including applied edits). Missing tables, marker,
interior rows or tail rows are therefore useful errors rather than an empty new
conversation. Sequence/key/context checks bind projections. Loss of both tables
and every independent reference cannot be detected by this bounded scheme; no
universal corruption detector or repair is claimed.

## Separate present inspection

[Private inspection](inspection.md) adds immutable persisted exchange revisions,
compact payload-omitting summaries, and explicit present log/session diagnostics.
`show` and returned `collect` remain historical evidence reads; present damage
never silently rewrites their result. Summary is not a full audit or public
redaction boundary. Session lookup is opt-in and requires actual query authority;
no transcript or external artifact store is automatically read.
