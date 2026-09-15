# Private mutable-run inspection

`inspection_cli.py` explains execution without decoding all retained output.
It complements (does not replace or weaken) the full logical audit in `cli.py
inspect/output` and `agent_cli.py show`. Python/POSIX/local-filesystem and the
same **whole-private-run reader** grant apply. No dashboard, authentication,
repair, semantic-policy engine, real-provider qualification or agent efficacy
claim is introduced.

```sh
python tools/mutable-workflow/inspection_cli.py summary /private/run --limit 20
python tools/mutable-workflow/inspection_cli.py summary /private/run --cursor TOKEN --limit 20
python tools/mutable-workflow/inspection_cli.py summary /private/cycle /private/domain-run
python tools/mutable-workflow/inspection_cli.py record /private/run --sequence 4
python tools/mutable-workflow/inspection_cli.py node /private/run --node 1
python tools/mutable-workflow/inspection_cli.py evidence /private/run --key judgment-1
python tools/mutable-workflow/inspection_cli.py evidence /private/run --key judgment-1 --verify
```

All successful inspection commands exit 0, **not completion/acceptance**. Storage,
contract and cursor errors exit 5 with JSON stderr `outcome: not_confirmed` and
an explicit `error`; argparse usage errors exit 2. Read the fields, not just exit.
No command here dispatches/resumes an agent or executes a graph worker. The
explicit `evidence --check-session` option does execute the configured trusted
runner's public read-only `session locate UUID --json`; that query needs actual
provider-query authority. Without the option, no provider program runs.

## Current versus changes versus private evidence

`summary` returns `sources`, one per supplied run, plus an opaque `cursor` and
`has_more`. Each source has:

- `current`: status, position, target **node incarnation**, active attempt,
  compact graph/archive and attempt projections, graph cursor, exchange states,
  application/question kind, claimed owners, effect uncertainty, latest explicit
  consumer publications, and explanatory `next_action` / `conversation_next`.
- `events`: at most `--limit` (1..1000, default 100) compact changes with run-local
  inspection `sequence`, `source`, `reference`, and `summary`. Graph changes link
  graph cursors and the editor's claimed actor; exchange changes link keys and
  immutable inspection revisions. A returned question is not completed work.
- `observed_head`, `has_more`, and the decoded per-source cursor for debugging.

The graph and conversation are **different action spaces**. Ready graph work may
still be owned by a live original executor; an uncollected superseded attempt
remains uncertain. Graph-ready is not permission to bypass a conversation's
pending key or a CRW historical-recovery blocker. A provider cannot infer a
consumer's priority between declared departure and original-policy recovery.
Absent policy publication is not a clean policy result. Unknown saved requests
remain unknown; no index/publication/inspection operation reconciles or launches
them.

Summary excludes purpose prose, worker inputs/argv, amendment reasons/effect
prose, declared policy values, request questions/answers, response detail, raw
stdout/stderr, trace bodies, artifact contents and private transcripts. This is
**payload omission, not universal redaction**: caller-supplied IDs, worker names,
actor/owner labels and run paths remain private metadata and may themselves be
sensitive. Do not publish this as a multi-principal/public view. Existing
capture's declared-literal secret redaction remains unchanged and is not a
promise to recognize arbitrary confidential prose.

`record --sequence` returns the original graph event, immutable exchange revision,
or consumer publication. It exposes private detail only on deliberate drilldown;
it grants no new access/effects. Graph event detail carries original actor,
reason, effects assertion, operations and basis cursor. Exchange detail carries
actual immutable authority/configuration, caller question, response, session,
application, log/trace refs and evidence. Direct access does not require any
synthesized reviewer result. Existing `output --attempt` remains authoritative
for full original worker request/output, classification and credit.

`node --node` uses incarnation IDs, not reusable display IDs. It returns archived
node, current membership, **all original attempts** and full original results,
current declared engine policy and change-batch references. Changes name added
and removed nodes in that atomic batch: they are **not a guessed one-to-one
replacement relation**. Read the ordered original operations at the linked
record for multi-operation/range replacements. A later replacement may itself
be removed; inspect its incarnation. Attempt requests retain their original
policy basis. Declared engine policy is never CRW qualification or retirement.

## Cursor and concurrency contract

New runs journal graph and exchange persistence in the **same SQLite transaction
as those writes**, including atomic exchange edit application. Every persisted
exchange revision is retained, not just its final overwritten record. Publications
below join this journal transactionally at their own admission. A process restart
does not reset sequence or origin. Rolled-back changes have no journal event.
No pruning/reset operation exists.

The opaque cursor encodes version 1 and an ordered vector of resolved run paths,
run UUIDs, index epochs and last **delivered** sequence positions. It is not the
old graph-only scalar and must never be supplied to graph `--since`. It is not a
signed security credential. The caller owns its checkpoint: preserve the token
only after consuming the events. Reusing a token repeats its suffix, permitting
at-least-once client recovery; exactly-once client processing is not promised.

Each source's current projection, observed head and page come from one SQLite
read transaction. `current` may describe **later work than the last event on a
limited page**. Always continue with the returned opaque cursor, never substitute
`observed_head` or `current.graph_cursor`. New concurrent commits remain after
that delivered position and appear on subsequent calls, including after process
restart. No frozen page snapshot needs expiry or retained server-side lease.
`has_more: false` means caught up at that source's sampled instant, not no future
changes. Multiple sources are sampled in caller order, **not globally atomic or
totally ordered**; use per-source identities and explicit source references.
The caller must include every relevant provider run. Reordering/adding/removing
sources requires an explicit new baseline, not silently extending an old vector.

Malformed/negative tokens, unsupported versions, foreign run/path/source-set,
ahead-of-history positions and mismatched (expired) index epochs are distinct
explicit errors, never empty-success deltas. Missing retained rows/count markers
also error. Loss of the DB, rollback to a backup, manual history rewrite, mixed
old/new writers, live relocation or deletion of the entire index is not supported
cursor continuity. A copied run at another path is foreign even if UUID matches.
Do not rebuild/reset an index to make a cursor pass. Restore intact original
storage or deliberately retain the old run and start a separately identified run.
No hostile same-user tamper authentication or arbitrary corruption proof exists.

The change feed covers **committed graph/exchange/publication changes only**.
Present filesystem damage, session existence and finite-owner file/lock samples
are independent observations, not journaled events. Recheck them explicitly when
needed; an empty change page does not certify unchanged external evidence.

## Cost and checks

Summary reads compact persisted projections and compact event columns, not
historical result bodies or their base64 payloads. Work/response still grows with
node/attempt/exchange counts and selected event limit; count checks and publication
index scans grow with retained row counts. This is not constant total cost, a
production SLA, quota or measured capacity claim. Full current input prose is
excluded from the projection. Retaining immutable exchange revisions increases
write/storage cost, particularly for cumulative conversation contexts.

Projection publication does not delete existing correctness checks. Execution,
collection, full `inspect/output/show`, and node drilldown still validate original
history through the existing providers. Summary checks contiguous journal/event
counts, required state and attempt/exchange projection counts, not all payloads
or every relational invariant. It labels that narrower validation explicitly;
use full audit before treating evidence as execution/collection authority. A
coherently rewritten projection is not authenticated truth. Supported writers
update the read model transactionally; older executables must not write indexed
runs (same-count exchange rewrites by old writers are not reliably detectable).

New runs enable indexing at creation. For an intact existing unindexed version-2
run, separately authorized `index RUN` takes collector/writer locks, validates
original graph/exchange history and commits an initial baseline plus existing
exchange snapshots. It neither dispatches nor invents old exchange transitions.
Pre-baseline exchange revisions are unavailable, while original graph history
remains in full inspect. Existing indexed runs refuse reindexing, and unknown or
unsupported old capture protocols still error. Indexing is a source mutation,
not a side effect of ordinary summary. Unindexed runs remain usable through their
original full evidence/execution APIs; `summary` explicitly refuses them.

## Present evidence boundary

`evidence` retains historical state/application/capture separately from present
samples. It checks referenced dispatch, lookup and trace logs **inside the run**:
missing, inaccessible, unsupported file type, truncated, size mismatch,
available-unverified or unresolved. Capture receipt availability is independently
reported, including missing, malformed and mismatch with historical receipt.
`--verify` reads/hashes regular logs to compare with the retained capture digest
(or currently readable receipt); it can report `matches_capture`, digest mismatch
or change during checking. A retained historical descriptor can match bytes even
when its on-disk receipt is now missing; both facts stay visible. Matching a local
capture is not producer truth or present semantic efficacy. Reads can race later
changes and are not a custody/locking service.

Receipt status is sampled independently even when the log is missing, inaccessible,
nonregular or restricted; the adjacent receipt has its own run-boundary check.
Nonregular receipts report `unsupported_file_type` without reading their contents.
Receipt admission is limited to 4096 bytes (the producer's four-field JSON is
small); larger receipts report `oversized`, not corruption or historical failure.
The reader checks the opened descriptor and reads at most 4097 bytes, including a
one-byte overflow probe, so growth after the size sample cannot cause an unbounded
read. POSIX nonblocking receipt open avoids waiting for a FIFO writer. Malformed
or excessively nested JSON returns a diagnostic without copying its payload.
These are bounded local receipt reads, not a wall-clock guarantee for filesystem
I/O or the whole evidence command (which still validates retained history).

Paths resolving outside the run, including symlinks, return `restricted` without
reading their bytes. This accidental-boundary guard is not hostile same-user
race-proof sandboxing. No returned artifact path/store address is automatically
fetched: references are retained with `unchecked_external_store` and the explicit
missing selected reader. An authorized consumer can use its actual store owner,
not this provider's guessed private layout. Stored session IDs report `unchecked`
unless explicitly queried; absent established identity is distinct from missing
storage. Public lookup reports available, supported unavailable, or unresolved
(operational/ambiguous/unsupported). It never reads transcript bytes, returns
transcript locations, selects fallback, resubmits, or changes historical state.

## Consumer publication seam (CRW remains separately owned)

`publish RUN --file publication.json` admits an explicit **consumer assertion**:

```json
{
  "source": "consumer-owned-stable-source-id",
  "revision": 1,
  "run_id": "target provider run UUID",
  "status": "blocked",
  "owner": "actual consumer/root",
  "basis": {"selection": "consumer-owned", "source_revision": "durable source reference"},
  "detail": {"current": "consumer account", "next": "root-owned action", "authority": "actual grant", "uncertainty": "retained gap", "links": []}
}
```

Exact top-level fields are required. `source/run_id/owner` are nonempty strings;
revision is positive integer, starts at 1 and increments without gaps per source.
Status is `current|blocked|pending|complete|unknown`; **complete means only the
publisher's assertion**, not shared qualification or consumer delivery. `basis`
and `detail` are arbitrary JSON objects interpreted solely by their owner. The
provider exposes only source/revision/status/owner in summary; `record` retains
full original body, including whatever exact policy/assignment/node/evidence
links the consumer supplied. Identical latest revision retry is idempotent;
changed, stale, gapped or foreign publication errors. No worker registry,
execution/decision authority or graph state changes. The filesystem's admitted
trusted writer, not `owner` text, authorizes publication.

**Deployed composition:** CRW's optional `corrected-cohort` controller now uses
this public seam and exposes joined private `summary`, original source `record`,
and separately authorized `replay-publications`. The
[CRW-owned inspection contract](https://github.com/nestharus/code-review-workflows/blob/main/risk-axis-reviewers/workflows/corrected-cohort/inspection.md)
owns its durable source revisions, exact publication outbox/replay, cycle/role/child
run roster, source-bound cursor handling and sampled next-work account. This is
the separately selected `perspective-lives-v1` controller, not the manual
domain-pass contract or a change to manual/standalone defaults.

CRW source commit, shared publication and acknowledgement remain independent;
joined reads are not a globally atomic transaction. Pending publication and
sampled lag remain visible under CRW ownership. Original locked/full `inspect`
and source/provider drilldown remain available. Joined inspection preserves
historical-recovery blockers versus declared departure, original authority and
questions, assignment/material/child/attempt/receipt relations, and the actual
selected policy; shared execution status is not CRW qualification or activation.
No private CRW table parser or competing retirement engine lives here.

This composition retains the whole-private-run reader boundary and requires
intact indexed CRW history and initialized compatible provider sources; older
regular-file CRW histories are explicitly refused by the new summary/replay/source
mutation surfaces, not silently migrated. Transport is synchronous with no SLA,
publication failures can leave private diagnostics and a growing retained backlog,
and roster changes require the CRW contract's explicit cursor rebaseline. These
capabilities grant no new runtime authority, live-provider qualification, empirical
reviewer efficacy, consumer delivery or default adoption. Existing unknown
saved-request reconciliation remains unavailable; publication replay does not
repair unknown keys.

## Verification

Repository tests in `tests/test_mutable_workflow_inspection.py` exercise new
summary/cursor/drilldown commands with real local fake processes, concurrent
edit/completion, distinct CLI restarts, exchange and multiple-run changes,
publication admission, bounded payload work, private-boundary controls and
post-settlement damage/session queries. Run alongside existing workflow,
surgery, runner, recovery, owner and secret-capture tests. Fake lookup statements
are not live runner qualification, semantic memory or empirical reviewer efficacy.
