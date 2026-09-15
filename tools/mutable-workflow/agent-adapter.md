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
locks and PyYAML (used by the shared secret-capture helper) are required.

```text
python tools/mutable-workflow/agent_cli.py ask /absolute/run --file request.json
python tools/mutable-workflow/agent_cli.py show /absolute/run --key judgment-1
python tools/mutable-workflow/agent_cli.py collect /absolute/run --key judgment-1
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
paths, changes the worker registry/purpose, or grants external effects. An agent
may propose investigation by inserting caller-registered workers through the
existing amendment surface. The caller's next ordinary `cli.py resume` executes
those workers; judgment does not automatically drive or repeat local work.

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

The response contract is owned in `agent_adapter.py::RESPONSE_CONTRACT`. The
agent emits exactly one bound line:

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
runtime for inspection/continuation. No automatic agent-history migration is supplied.

A dedicated collector lock excludes concurrent dispatch/collection for the run,
not live graph edits or `show`. Submission intent commits **before** process
creation. `ask` owns synchronous native collection while alive; it streams merged
stdout/stderr into a unique private log through the existing secret-safe capture
helper before publication. There is no shell wrapper, truncation, secondary raw
sink or polling loop. Normal return records the actual process exit, then one
exact trace observation and response/application. Each `collect` call makes at
most one trace observation and **never dispatches/resumes a model**. It is the
explicit caller-owned continuation after delay or collector loss; no daemon
silently takes ownership. Delayed trace completion can settle an already fully
captured exchange. Loss before either complete-capture evidence record is persisted stays pending
even on successful trace. A published ACR-539 receipt can recover the later
DB-record gap; it cannot reconstruct missing bytes or authorize a replacement submission. Calling it on a returned or known-not-submitted record is an idempotent read.

Returned JSON distinguishes `state`, `continuity`, `target`, established `session`,
`acceptance`, local `returncode`, `terminal_result`, durable `completion_basis`,
raw-log path, trace-observation paths, returned artifact refs, substantive
`response`, and `application`. States:

- `prepared`: local context retained, no durable submission intent yet. Under
  collector ownership `collect` now records this interruption as `not_submitted`:
  the controller always commits pending intent before process creation. It does
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

CLI exit 0 means `returned` (including questions and rejected edits); exit 4 means
another retained state. Exit 5 is a command/contract/storage error with JSON
`not_confirmed`; inspect durable state, do not infer no effects. `show` uses these
same exchange-state exits. Abrupt signals may have only the OS exit.

Known limits remain explicit: loss before a recoverable invocation marker cannot
be settled by trace-by-ID; no unconditional resubmission or caller-manufactured
completion is provided. A missing/malformed/truncated response cannot be rebuilt
from a mailbox receipt or unrelated artifact. The selected trace/CLI contract
exposes no complete substantive-output retrieval basis after local capture loss;
upstream delivery success is not an acknowledgement of this collector's retained
bytes. Settling that case requires an independently supported complete-output
recovery contract or a separately authorized durable collector design, neither
implemented nor assumed here. Loss after EOF but before publishing either local completion record remains
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
unusable; that remains a collection gap, never a bypass to raw capture. Collector
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
python -m pytest -q tests/test_mutable_workflow.py tests/test_mutable_workflow_surgery.py tests/test_mutable_workflow_runner.py
```


## ACR-539 complete local capture receipt and remaining dependency

For new exchanges `capture_protocol: local-receipt-v1` selects a receipt at
`runner.log.capture.json`. Transport first drains EOF through the existing
secret-redacting sink, publishes the carry tail, waits for process exit, closes
and syncs the log, then atomically publishes the receipt before returning to
`submit`. The receipt has exactly `version: 1`, `bytes`, `sha256`, and integer
`returncode`, describing the **entire retained redacted merged log**, not raw
secret bytes or upstream spool delivery. Temporary receipt files are never used
as completion evidence.

If the controller dies after that publication but before storing its exit in
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

There is still no safe implemented recovery for death during capture, between
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

Root must choose how to address a material affected recovery case: obtain an
authorized supported provider contract for complete invocation-bound output and
unknown-submission association; or separately authorize/design capture ownership
that survives the controller's loss; or explicitly retain unresolved recovery
without claiming the broader outcome complete. A provider contract would need
actual completeness/identity/exit semantics and supported access, not merely a
known spool filename. These are alternatives for root, not an implemented API,
a new worker effect grant, or an automatic runner-change requirement.


`agent_history` records the version and exchange count in the same transaction
as each exchange insert/update (including applied edits). Missing tables, marker,
interior rows or tail rows are therefore useful errors rather than an empty new
conversation. Sequence/key/context checks bind projections. Loss of both tables
and every independent reference cannot be detected by this bounded scheme; no
universal corruption detector or repair is claimed.
