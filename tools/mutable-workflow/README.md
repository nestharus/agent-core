# Mutable workflow: local sequential execution

One concern: execute and durably amend a caller-supplied sequence. This is the
ACR-536 first working slice, not a general graph engine or a workflow-policy
owner. Python 3.10+ standard library, SQLite and POSIX `flock`; no dependencies,
daemon, scheduler, resident agent or network service. Invoke from any directory:

```sh
python /path/to/ai/tools/mutable-workflow/cli.py start /absolute/new-run --file plan.json
python /path/to/ai/tools/mutable-workflow/cli.py inspect /absolute/new-run --since 0
python /path/to/ai/tools/mutable-workflow/cli.py output /absolute/new-run --attempt 1
python /path/to/ai/tools/mutable-workflow/cli.py judge /absolute/new-run --file response.json
python /path/to/ai/tools/mutable-workflow/cli.py resume /absolute/new-run
```

Use a caller-owned planning/scratch directory outside the checkout for run data.
`start` requires a nonexistent run directory and immediately executes until a
stop. `resume` continues only ready work. Either accepts `--max-steps N` to return
at a durable boundary after at most N additional attempts; zero initializes or
inspects continuation without executing. `judge` commits an edit **without**
executing it: a later `resume` is a supported restart point.

## Public contracts (owned here)

### Plan and effect grants

`plan.json` is exactly:

```json
{
  "purpose": "Exercise ordinary local work",
  "workers": {"local": ["/usr/bin/python3", "/absolute/local-worker.py"]},
  "steps": [{"id": "first", "worker": "local", "input": {"task": "example"}}]
}
```

Purpose, worker names, argv entries and step IDs are nonempty strings. Executable
paths are absolute; other argv entries are literal (no shell expansion). Workers
and steps are nonempty. Step IDs are unique. Each step has exactly `id`, `worker`,
`input`; input is JSON data, not interpreted by the engine. All worker commands
are explicitly supplied by the caller; an editor may reference these workers
but cannot change the command registry. The registry is not the original graph:
a newly named, originally undeclared step with new input really can execute.

**Trust boundary:** one trusted local principal, private run directory, trusted
worker programs. Filesystem permissions, not the `actor` label, control access.
The caller grants execution of the registry programs with their inherited process
environment/credentials and any admitted input. Programs must enforce any narrower
input/effect restrictions themselves. This is NOT a sandbox or an authorization
service. An editor's input must never be treated as new credentials or effect
permission. The CLI does not invoke agents or interpret CRW policy. Do not use
this slice for irreversible/external effects or untrusted workers/editors.

### Worker request and result

The engine invokes the selected argv directly, with run directory as cwd, one
JSON object on stdin, and captured stdout/stderr. Request fields:

- `run_id`: generated UUID; `purpose`: caller intent.
- `step`: exact admitted step; `attempt_id`: run-local integer output reference.
- `edits`: accepted edits and their reasons (empty on ordinary trajectory).

The entire stdout must be one JSON object with exactly:

```json
{"outcome": "success", "detail": "What actually happened"}
```

`outcome` is `success`, `failure`, or `judgment`; detail is nonempty text.
Zero exit **and** an admissible result are required for substantive classification.
A zero exit with missing/malformed result becomes `ambiguous`, never success.
Nonzero exit becomes `failure`, even if stdout claims success; raw bytes remain
available. Launch errors become failure with error detail. Failure means this
attempt did not establish success, not that it caused no effects. A valid result
is a trusted worker assertion, not an independent verification of its truth.

### Judgment handoff and insertion

`failure` and `judgment` halt with the blocked position unchanged. The caller
hands `inspect`'s current view plus the blocked attempt's `output` response to an
external judgment actor. No provider integration is implied. A script-based fake
actor is exercised in `tests/fixtures/mutable_workflow/judge.py`; it reads actual
failure detail and raw output before producing recovery intent.

The authorized editor returns exactly:

```json
{
  "run_id": "UUID from current view",
  "cursor": 5,
  "blocked_step": "first",
  "actor": "local-editor",
  "reason": "Failure evidence and why this recovery permits continuation",
  "insert": [{"id": "new-recovery", "worker": "local", "input": "new work"}]
}
```

Run ID, integer cursor and blocked step must match current state. Actor and reason
are nonempty strings; actor is an audit label, not authenticated identity. Insert
is a nonempty list of validated steps whose IDs are new across the entire current
sequence. Unknown fields, workers, duplicate IDs, stale/foreign/replayed responses
and edits outside failure/judgment boundaries are rejected before mutation.

Acceptance means **the editor authorizes continuing via this inserted recovery**
instead of retrying the blocked step. Inserted work goes immediately after the
blocked step and before the original remaining sequence. Failed/judgment attempts
are never rewritten as successful. An edit retains its context and reason in
history. Engine success means the *revised* sequence reached its end; it does not
mean the original sequence succeeded or the editor's reasoning was correct.
No retry, delete, goto, parallel graph surgery, cancellation, policy accounting,
provider-session continuation or automatic ambiguity reconciliation is exposed.

### Caller outcomes and inspection

Mutations print current state JSON on stdout, with exit codes:

| Code | State / meaning |
|---|---|
| 0 | `success`: revised sequence completed with explicit worker successes |
| 1 | `failure`: blocked failed attempt, evidence available |
| 2 | `judgment`: unresolved explicit worker judgment need |
| 3 | `ready`: durable work remains (including newly accepted edit) |
| 4 | `ambiguous`: no safe automatic continuation |
| 5 | command/storage/contract error; JSON stderr `outcome: not_confirmed` |

After code 5 inspect durable state; it is not a claim that no prior work ran.
An abrupt executor signal may instead yield the OS signal exit without JSON.
`inspect` and `output` exit 0 on successful **read**, regardless of workflow outcome;
callers must read the returned state, not infer workflow success from read exit.

`inspect` returns `{current, events, cursor}` from one SQLite read transaction.
Current includes purpose, registry, current steps, zero-based position, status,
run ID, cursor, historical attempt summaries (`id`, `step_id`, `outcome`) and
accepted edits. Summaries reference `output --attempt ID`. Events contain
`cursor`, `kind`, `detail`; cursors increase by one per committed change. `--since`
returns events strictly after that cursor through the returned current cursor.
Cursors are scoped to the returned run ID, survive supported restarts, and must
not be transferred between runs. Negative/future cursors error. No pruning/reset
exists. Current state is progress, not a health/liveness assertion.

`output` returns the exact persisted attempt request, outcome and output. Output
contains `returncode` (null on launch failure), `stdout_b64`, `stderr_b64` (lossless
bytes) and interpreted `result`. An interrupted running attempt may have null
output: output was **not collected**, not empty successful evidence. Unknown
attempts and missing/corrupt storage error rather than returning empty history.
Inspection can expose worker inputs, outputs and credentials accidentally printed
by workers; keep run data private. No transcript discovery or redaction is claimed.

## Durability and operating envelope

A single SQLite file holds state, events and attempt output, committed together
with `synchronous=FULL`. A separate nonblocking advisory writer lock covers a
whole executor or edit invocation; a competing mutation errors, while inspection
can read committed progress. All writers must use this entry. Never move/delete
a live run directory or manually edit its database. Local filesystem only; no
NFS, multi-host, hostile same-user access or distributed durability claims.

An attempt-start record commits **before** dispatch. A result, advancement and
its event commit together. Restart after a committed result or edit does not
rerun completed work. Restart discovering `running` records `ambiguous` and
refuses further execution/editing: the worker may still be running, may have
produced effects or may have returned before result commit. Its original running
attempt and missing output remain honest history. There is no automatic retry,
no exactly-once effect promise and no claim that a lost worker was terminated.
Caller/root must reconcile outside this slice; making a new run is new authority,
not a retry recommendation.

Supported tested interruption points: CLI process exit after durable step or
edit, and executor SIGKILL after attempt admission (conservative ambiguity).
Power-loss durability of new directory creation, disk corruption/full recovery,
arbitrary in-flight output salvage, child termination and irreversible effects
are not qualified. Initialization failure leaves an unusable directory and an
explicit error; inspect before operator cleanup, never silently overwrite it.
Workers must terminate and produce bounded output; capture and JSON state/history
are in memory, without production quotas, timeouts or streaming. This is a small
local slice, not a long-running service/headroom claim.

## Discovery and ownership

`VALUES.md` and `tools/README.md` place generic mechanics here; caller procedural
compositions stay outside the engine. The scheduler is a skeleton, workflow_index
is metadata, and wu-session-migration's durable writer owns WU-specific artifacts;
none is a runtime dependency. SQLite avoids importing that unrelated journal model.

Runner discovery resolved the old `/home/nes/projects/agent-runner/README.md` pointer
to `/home/nes/projects/agent-runner/trunk/README.md`: CLI Usage and Inspecting a Run
own headless invocation, artifact returns and invocation/result transport.
Its successful spooled capture uses the final matching result record after process
success, permitting marker-shaped provider payload. AI's existing legacy
`operational_contracts.py` successful-stream extractor has a narrower contract.
This tool uses **neither** seam: its subprocess JSON contract above is local and
independent. Fake results do not demonstrate installed runner compatibility,
real agent invocation, provider session recovery or reviewer efficacy.

## Verification / used by

Current consumer: `tests/test_mutable_workflow.py`, with local fake worker and
judgment fixtures. No deployed workflow/operator consumer is selected.

```sh
python -m pytest -q tests/test_mutable_workflow.py
```

The entry-path tests exercise ordinary no-judgment execution; failure-informed
unplanned insertion; edit and completed-work restart; current, cursor and raw
output readback; invalid/replayed edits; missing/malformed/nonzero worker results;
and executor death with preserved prior evidence and no automatic replay.
Later CRW perspective lifecycle remains policy-adapter work, not generic engine
logic. No agent-design prompt, empirical agent evaluation or legacy orchestrator
is introduced here.
