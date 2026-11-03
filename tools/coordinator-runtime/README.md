# Opt-in coordinator runtime

This candidate dispatches actual bounded Work, Branch, Reviews and QA tasks.
Fresh Luna6 LOW sessions classify each incoming message and each model response;
validated classification and queued responsibility commit before delegated ACK.
Frozen batches, reservations and outgoing responsibilities live in SQLite
WAL/FULL. Work and all integrators use Sol6.1 XHIGH. New disposable jobs prefer
`.codex3`; actual role-owner accounts remain unchanged.

**No service, role enrollment, actual model success, adoption or session-store
reclamation is established by fixture tests or publication.** Parent separately
collects independent consequences and actual-model qualification. The example
is disabled. Root is an external work recipient, never an enrolled role;
Dispatcher and Cloud remain excluded. There is no JEV, external dependency,
parent wait wrapper or replacement of an existing collector.

The collected qualification2 encounter on `bfdd43b` already established actual
provider wire acceptance, five attempts/six turns, one supported continuation,
report → fresh Luna → writer progression and meaningful synthetic writes. Those
original successful/failing receipts remain their own evidence. The completion,
custody and producer-output changes below require a new bounded actual encounter;
fixture results do not extend that qualification.

## Install, configure and inspect

Use an isolated published checkout, Python 3.11+ and the standard library. Leave
the dirty live message-board checkout untouched. No global installation, login,
credential copying or global route/model-selector change is needed.

```sh
RUNTIME=/absolute/selected-checkout/tools/coordinator-runtime/coordinator
python3 "$RUNTIME" --help
python3 -m unittest discover -s /absolute/selected-checkout/tools/coordinator-runtime/tests -v
python3 "$RUNTIME" qualify-schema --output /absolute/owned-evidence/fresh-schema-directory
```

Schema qualification starts no app-server/model. Retain its schema/receipt for
current consumers, at least 24h plus all holds. Installed 0.166.0 schema exposes
experimental ephemeral start, read, turn, interrupt and unsubscribe. The
[official thread reference](https://learn.chatgpt.com/docs/app-server#threads)
documents ephemeral fork; it does not prove installed start behavior. Strict
provider output uses a closed `{payload_json:string}` wire object containing the
complete typed result JSON. Inner schema/routing is independently validated.
The prior actual provider400 and unexercised capabilities remain qualification
inputs; a fake provider accepting this wire is no live success.

Copy [examples/rfq.json](examples/rfq.json) to a mode-0600 private config. Select
the actual board home/UUID, board-local role/profile identities, checkout/template
paths, operator config/CLI paths, owned mode-0700 state directory and schema
receipt. Example zero UUIDs/placeholder paths are deliberately unusable. Its Root
locator is inactive until Work binds the actual current recipient membership;
that is operational identity binding, not another Source/human approval gate.
Actual recipients are verified again on delivery. No live board census occurs
by loading configuration.

Choose `enabled` before initialization, after parent disposition. Config is
bound by digest; later changes need an offline owned migration and explicit
responsibility handoff. Never discard an existing journal to escape holds.

```sh
python3 "$RUNTIME" --config /absolute/private/config.json init
python3 "$RUNTIME" --config /absolute/private/config.json status
```

## Actual owner enrollment and delivery

Each selected role owner executes enrollment from its **existing genuine actor
context**. Do not set or borrow `CODEX_SESSION_ID`, membership, native handles or
owner cursors. The grant is explicit revocable role-lifetime cooperation within
the shared Unix account, not authentication against other same-account actors.
It verifies active membership, exact role/profile, invitation/catalog policy,
board UUID/file identity and binds the exact runtime DB inode. It takes a new
prospective intake cutover; no old queue is imported.

The actual owner first selects the board's managed receive route and reconciles
its existing intake writer. The runtime refuses to silently change queue-route
membership. Full enrollment adds a distinct labelled managed service actor and
bounded outgoing recipients/kinds, in addition to private intake/receipt rights:

```sh
python3 "$RUNTIME" --config /absolute/private/config.json enroll Work --delivery --completion \
  --authority /home/nes/projects/rfq/planning/coordinator-runtime-rollout-20261103-01/CONSEQUENCE-DECISION.json
# For an already enrolled incoming/receipt-only grant, from that same real owner:
python3 "$RUNTIME" --config /absolute/private/config.json delegate-delivery Work \
  --authority /home/nes/projects/rfq/planning/coordinator-runtime-rollout-20261103-01/CONSEQUENCE-DECISION.json
```

`--completion` explicitly delegates the bounded routine collector to this real
service actor for configured role tasks. For an existing full delivery grant,
the genuine owner uses `delegate-completion ROLE --authority FILE`. It is a
role-lifetime grant, never per-task human approval. No owner ID is substituted.

Repeat only from the genuine selected Branch successor, Reviews and QA actors.
The automation actor never joins as an owner. Classification provenance retains
actual model session, attempt, configured/read-back binding and source author.
The additive board extension records original producer, authorizing role owner,
real service author, exact post/notice/recipient and immutable full payload.
Private access covers only granted addressed input and replies on its owned
outgoing threads. It does not attach to an existing listener or move `ack_seq`.

A model returns typed handoffs `{recipient,kind,text,ref,required}` within its
allowlist; necessary handoffs require `settled`. Empty handoffs require a reason.
`kind` is a bounded nonempty intent label. `work`, `result` and `question` retain
their existing delivery kind. Other labels (for example `catalog-proposal` or
`bounded-execution`) travel only as questions to the same actual recipient. The
payload retains the full original handoff, label, source result, meaning, reference
and required settlement. A question conveys no execution, acceptance or effect
authority. Role/recipient/package admission checks still apply.
The dispatcher posts work/result/question/recurring-alert messages as the actual
service actor, after fresh response classification. Retries use the same exact
ID; distinct unchanged violation occurrences get distinct deliveries. It invokes
existing queue transport only for its exact new post/recipient, at most once;
ambiguous sends remain held. It never drains a foreign submission queue.

The addressed message includes usable commands for the **actual recipient**:

```sh
python3 "$RUNTIME" --config /absolute/private/config.json delivery-show Work DELIVERY_ID
python3 "$RUNTIME" --config /absolute/private/config.json delivery-stage Work DELIVERY_ID \
  --stage picked-up --receipt /absolute/owned/pickup.json
python3 "$RUNTIME" --config /absolute/private/config.json delivery-stage Work DELIVERY_ID \
  --stage processed --receipt /absolute/owned/processing.json
python3 "$RUNTIME" --config /absolute/private/config.json delivery-stage Work DELIVERY_ID \
  --stage settled --receipt /absolute/owned/settlement.json
```

`Work` above identifies the sender grant; the current actor must be that exact
delivery's recipient. Every stage needs actual `evidence`. Questions also need a
`resolution`. Queue-route processing/settlement needs `transport` with exact
`queue_message_id`, `state:"processed"` and evidence from its actual consumer.
Board ACK alone cannot prove queue processing. Effect-request settlement needs
`effects:{evidence:[...],unknown_effects:[]}` from the real effect owner. This is
actual reconciliation of possible effects, not extra permission. Completed stages
are immutable; changed findings after successful collection need a new addressed
reply. A rejected selected-owner return has a bounded correction path:

```sh
python3 "$RUNTIME" --config /absolute/private/config.json delivery-show Reviews DELIVERY_ID
python3 "$RUNTIME" --config /absolute/private/config.json delivery-correct Reviews DELIVERY_ID \
  --receipt /absolute/owned/owner-correction.json
```

The correction is `{supersedes,reason,settlement}`. `supersedes` is the exact
rejected `settlement_version` from delivery-show; settlement is the complete
corrected owner return, retaining its genuine `actor`, actual original collectors,
method/pin and no-start evidence. For the collected category error, the owner
corrects `result.category` from `complete` to `consolidated` while retaining the
full report. Runtime rejection must already be recorded; this is a version/ownership
fence, not an approval request. Only that delivery's actual Reviews owner can
append it. The original settled receipt is never edited. Every correction,
reason, actor and old return remains recoverable in the board and routed report
history. The runtime validates again, then routes to the configured report
integrator without replaying Source/reviewers or inventing old originals.

Default budget: four corrections per delivery (`limits.max_owner_corrections`,
1–8), plus per-result and cumulative byte bounds. Exhausted/invalid corrections
stay explicitly owned; no responsibility or source is discarded. A stale version,
foreign actor, replacement collector/method, changed runtime identity or already
collected result is refused. The collector and correction command serialize on
the board; a local-collection/board-receipt interruption reconciles the same
return without another review. No generic cross-role takeover is supplied.

Necessary delivery remains durable through pickup/processing/settlement. A task
DONE cannot silently drop a handoff. Report results mirror to the real owner;
Reviews consolidated results go Work, accepted QA qualification goes Branch,
and Root code work retains commit **and** push. Status shows every pending
outbox and operational failure; no private-journal discovery is needed to learn
that work/questions/errors exist.

## Actual role procedures and holds

The example connects the current parallel method/proposer/batch-integrator and
Reviews report templates to these concrete procedures:

- [Work catalog](templates/work-catalog.md): exact seven surfaces, full semantic
  deltas and allocation, CAS/before-only backup/same-inode/fsync/readback.
- [Branch repository](templates/branch-repository.md): real admitted refs,
  worktrees, clean mechanical/native stack organization and effect reconciliation.
- [Selected Reviews](templates/reviews-selected.md): actual existing owner runs
  its selected Source/reviewer procedure and original collection; no generic
  replacement review or newly resolved opaque binding. The returned full reports
  feed the single Sol XHIGH report integrator. Owner settlement needs complete
  `result`, `actual_originals:[{collector,actual_end,reference}]`, `method_pin`,
  `coverage_frontier` and `effects`. A genuinely unstarted incomplete return can
  instead supply empty originals plus `no_start_evidence`; no process END is
  invented. Missing review remains an explicit Work-owned frontier.
- [QA package](templates/qa-package.md): actual separately admitted execution,
  five independent packages, one execution owner per admitted package and one
  global cleanup slot processing one package. The sixth package stays pending.

Work/Branch/Reviews each have an independent single integration slot, with
parallel instanced proposal/owner jobs. Arrivals after freeze form the next
batch automatically. Execution capacity is separate from downstream custody:
a collected, begun/ended exit0, complete-capture DONE attempt with known effects
and no scoped job hold can release its execution slot while its job remains
`awaiting-delivery`. Status exposes `execution_slot_held`. Its queue, source,
outboxes, processing timestamp and actual recipient settlement remain unchanged.
Uncertain process/effects, active work, legacy holds and an unresolved same admitted
scope still exclude overlapping execution. Independent next batches progress.
Actual legacy holds can name affected phases only; intake
continues. Branch's existing integration/outbox hold remains real; historical
native25, 100/88 queue history and an unacquired Reviews reply are not universal
software freezes. No adoption is fabricated.

The current Branch resource owner records existing admission with:

```sh
python3 "$RUNTIME" --config /absolute/private/config.json admit-package EXACT_PACKAGE \
  --receipt /absolute/owned/admission.json --accepted-receipt /absolute/owned/actual-acceptance.json
```

Acceptance is optional until it actually exists. For Branch integration or QA
execution, admission supplies `task_scopes` keyed by task ID, each with exact
`cwd`, `read_roots`, `write_roots`, `network`, `procedure`, `resource_evidence` and
selected refs/PR/head/event/runner/commands. These narrow configured `scope_roots`;
they cannot authorize a private profile, symlink escape, arbitrary message shell
or expanded network. Existing source/review/resource/CI/GLOBAL/monitor owners
persist. Missing compatible scope remains an explicit inactive frontier rather
than pretending a proposal is real repository/QA execution.

Actual owners conserve legacy originals/effects/outboxes through
`reconcile-legacy ROLE --receipt FILE` with
`{collector,evidence:[...],remaining_holds:[...]}`. No PID/timeout/file/label proves
closure. `reconcile-effects JOB --token TOKEN --receipt FILE` records a genuine
owner's collected effects even after revocation. Root/Work owns publication
recovery, not a new runtime permission ritual.

## Process, recovery, retention and service

Owned process begin, numeric exit, collection, semantic DONE, typed capture,
unsubscribe, teardown and session reclamation are separate fields. Valid finals
survive unsubscribe/teardown failure. Output/reasoning/raw protocol bodies are
not logged; capture is selected typed returns/lifecycle, not a full transcript.
Provider schema/capacity failures retain bounded safe causal projections. A
proved pre-start failure records no fabricated process END and can recover
within bounds. Unknown creation/foreign/lost handles retain their slot.

One supported same-session continuation requires actual idle readback. Then
fresh Luna LOW diagnoses and selects one explicit authorized profile handoff
with prior owned context/effects, only after actual end/collection (or proved
no-start) and reconciled effects. No overlapping mutation, orphan resume,
credential move or foreign native handle. Revocation fences every new classifier,
diagnosis, initial turn, continuation and replacement against current source-role
grants. Owned collection and recipient settlement continue.

Every launch reads effective MCP metadata and individually disables every server,
then requires complete disabled readback. Feature-name variation/omission is
recorded; false/absent flags do **not** prove nondelegation capability. Unknown
server requests are refused, observed delegation holds capture. Actual available
tool surface remains a parent qualification question.

Queue retirement starts actual `processed_at+24h`, including later dependent
processing and cleared consumer/recovery/outbox/uncertainty holds. Later holds
protect upstream sources/artifacts; their release restarts the processing clock.
Internal results can supply verified exact source custody. Unproven unique input
remains in place under its actual role owner; `recover-source EVENT` reconstructs
verified meaning/attribution. No assumption that all board history is permanent,
no blanket duplication/profile purge. Exact registered single-link artifacts
require actual conservation and symlink-safe identity checks before retirement.

Routine file writers may configure `routine_completion:{kind:"file-witness",
targets:[absolute exact files]}` under explicit logical effect roots. Actual
qualification4 on 4ead established working installed preflight/capture controls,
two models/three turns/one owned-idle continuation and incoming Luna commit/ACK,
but its exact file-root writer could not execute. Both partials, missing report
and held sources remain original evidence. An installed native exact-file policy
probe also hit directory-style mount errors. Accepted sandbox type is not proof
of usable exact-file mounts.

The corrected writer uses **owned staging and exact controller publication**.
Only the new attempt directory is writable to the model; canonical files and
parents stay read-only. `staged_targets` maps each real exact target to its owned
copy. Templates keep their actual purpose/owner; the task edits the mapped copy
and writes its reports in the owned output directory. Directory sandbox mechanics
are an explicit ceiling for owned outputs, not direct canonical file authority.
The legacy sandbox retains its existing broad read-only OS ceiling: logical
selected-source/privacy bounds still apply, and no exact-read isolation is claimed.
No canonical parent or network scope is widened. Local input copies share the
owned directory ceiling; durable original report bytes remain in journal custody.

Local producer readiness now distinguishes current defects from expected later
controller/review/delivery duties and resolved history. The required file-worker
`completion` protocol covers every original failure/unknown index and adverse tool
item; original arrays are never erased. A combined original unknown may use one
indexed duties group containing individual exact controller or review/acceptance
duties. Prose is rationale, not an enum. Successful commands need no adverse
disposition; tools=[] when there are none. Producer-visible chunk labels remain
uncorrelated claims in optional reported_commands, never protocol IDs or OS handles.
Resolved claims bind exact conserved own
report hashes and explicit actual successful verification IDs. An unrelated later
zero is insufficient. Standard controller publication/custody duties name the real
service actor; necessary external duties require admitted settled handoffs. Review/
acceptance boundaries remain unclaimed, not waived. These are producer-attested
resolution claims with mechanically verified links, not independent semantic proof.
Genuine unresolved local work, missing evidence, unsettled tools, invalid ownership
or source/resource/revocation fences still hold. Live clarification uses the same
proof grammar/ownership checks, plus bounded declared own-byte checks; final
assessment still requires actual collection, complete tool metadata and conserved
byte witnesses. Ambiguous DONE can use the
ONE existing same-owned-idle continuation for faithful clarification/verification;
no new session, blind rewrite, text heuristic, repeated clarification or per-job
human permission is supplied. Original pre-clarification arrays must remain verbatim
prefixes, with original completion and specific issues retained. See
templates/local-completion.md and tests; the outer provider wire is unchanged.

All role tasks share one outer-result contract in contracts.py: the generated job/
wire/clarification instructions, live diagnostics, publisher, final task collector
and routine callback use it. Missing fields, unsupported fields (including an
outer dissent), types/categories and arrays have separate diagnostics. Dissent
belongs as attributed finding data; genuine local defects still require failures/
unknowns and blocked/partial work. Repairable outer mismatches can use the same
one owned-idle continuation even without routine file completion. Complete original
JSON and later return stay separate; valid original arrays remain verbatim
prefixes and original extra/malformed array data must be conserved explicitly in
findings kind=outer-contract-original. A repaired response that simply drops data
is held. No original is automatically normalized, blindly replayed or resumed after
its owner ends. See templates/local-completion.md for the data-preservation example.

Artifact items use the same item contract in prompts, live clarification and
collected custody: an explicit absolute path string, `{path,...metadata}`, or a
nonempty `{files:[items],...metadata}` group without a group path. Groups are
bounded to depth four and 64 total leaves. `common`, `kind`, anchors and read
extents remain original data; they supply no implicit path or access authority.
Leaf hash/byte claims, when supplied, must match actual captured bytes. Current
peer changes can therefore hold a historical reference rather than replace its
meaning. Declared target paths map to their owned stages even inside groups;
the original result is never rewritten. Missing/invalid item representations can
use the existing one actual-owned-idle clarification: conserve the entire old
array in `outer-contract-original.fields` and retain every valid old item as a
verbatim prefix. Never guess a missing path or erase adverse arrays to repair it.

Collected DONE with a recorded disposition error now receives the bounded fresh
Luna diagnosis as well. Its diagnostic result returns to its actual role owner; it cannot by
itself launch another task. The old result, stages, source holds and unknown
effects stay owned. Genuine same-session clarification still requires actual
idle readback before the original owner exits. Numeric process END, complete
capture, DONE, publication, recipient processing and acceptance are separate.

The actual enrolled role owner can queue a bounded request for its existing
collector without SQL, original-return edits or borrowed process handles:

```sh
python3 "$RUNTIME" --config /absolute/private/config.json request-recovery JOB \
  --token EXACT_RESERVATION --attempt EXACT_CURRENT_ATTEMPT \
  --receipt /absolute/owned/recovery-decision.json
```

The receipt has exact keys `mode`, `reason`, `evidence` (nonempty reference list)
and `remaining`. `mode:"redispose", remaining:null` retries artifact inventory
and ordinary disposition of the unchanged original. An inventory-only gap may
receive a derived capture correction only with complete original protocol
capture and successful current custody. Original result/results rows and prior
capture errors remain conserved. Incomplete streams, semantic UNKNOWN, canonical
preimage conflicts and unrelated readiness/source holds remain binding.

`mode:"remaining-work"` requires an authentic bounded target **and why** in
`remaining`, actual collected end, reconciled effects, no unresolved publication
intent, no independent source/legacy/job hold and an explicit prior continuation
disposition. The owner uses the existing `reconcile-effects` operation only with
real effect evidence; that receipt cannot waive canonical publication. The
original service collector consumes the request and runs a new matching bounded
Luna diagnosis before any remaining-work attempt. That attempt receives conserved
old reports/stages plus fresh canonical preimages and new owned stages; it must
reconcile peer content and preserve accepted effects rather than replay them.
Prior diagnosis/replacement work cannot be duplicated while claimed/diagnosing.
Stale attempts, foreign owners/collectors and unknown live originals are refused.
Default request bound is four per job (`max_owner_corrections`); consumed requests
are idempotent records, never automatic retries. Requests and causal errors are
visible in status. A restarted service can use only the existing proved collected
closure handoff (including required effect reconciliation); original process
collection fields remain unchanged. Unknown originals, active recovery and
unreconciled external effects cannot transfer. An unavailable original collector
remains an explicit frontier; this provides no process adoption or new deployment
authority. Current bindings alone authorize no transfer.

Recovery diagnosis receives the consumed actual owner selection **before** any
handoff: target, WHY, evidence, owner and request identity, with the original
result/effects. An independent external future-use choice remains a duty; it does
not silently veto separately admitted local reconciliation. Source, resource,
publication-intent and current-peer fences remain binding. A diagnosis can return
`profile:"@owner"` with a precise missing decision in remaining/rationale. Failed
or invalid collected diagnoses retain their raw results and return recovery to
`awaiting-disposition`, with an actual-role question and public next step instead
of endlessly revisiting the same invalid choice. An unknown diagnosis remains
with its actual collector. An already recorded bad diagnosing state can be
recognized by `request-recovery` from its collected matching evidence, without
rewriting the old result or forcing a profile. A fresh diagnosis is tied to its
exact owner selection; an old diagnosis cannot authorize a later selection.
`mode:"defer", remaining:null` records a bounded owned unresolved decision and
keeps the original held, without another automatic diagnosis, processing or
acceptance. Request budgets and independent holds persist.

## Input controls and actual owner decisions

Fresh classification retains four fields: event_id, task, package and reason.
In addition to configured tasks, `@control` addresses board controls/status/results
to their actual coordinator; `@unresolved` records honest uncertainty and asks
that role owner. Neither creates an execution job or needs an invented package.
Real ordinary Branch proof work can select its actual configured non-QA task;
actual QA and other scoped execution still require their actual package admission.
`@delivery` validates the fixed notification/duty plan, not substantive permission,
publication, recipient processing, accepted QA or settlement. A necessary external
duty stays explicit. Later notifications receive separate immutable plans; earlier
plans and their classifier histories are not silently changed. Malformed answers
still have one bounded classifier recovery; even then the genuine owner can inspect
and resolve the exception through the public commands below. There is no generic
Work catchall, automatic route bypass or repeated unbounded diagnosis.

From the existing genuine actor only:

```sh
python3 "$RUNTIME" --config "$CONFIG" owner-controls QA --limit 100
python3 "$RUNTIME" --config "$CONFIG" input-show EXACT_EVENT
python3 "$RUNTIME" --config "$CONFIG" resolve-input EXACT_EVENT --receipt /absolute/own/input-decision.json
```

`owner-controls` lists only that enrolled role's pending input/recovery exceptions;
page inputs with `--after NEXT_AFTER` when more_inputs is true. A full recovery
page remains an explicit inspection frontier. `input-show` returns the immutable
source/hash, current responsibility and all attributed derived decisions. None of
these commands proves native wake, pickup or processing. Existing genuine-owner
watch/read/delivery-stage duties remain necessary.

The resolution has exact keys:

```json
{"source_hash":"EXACT_INPUT_SHOW_HASH","mode":"route","task":"branch-proposer","package":null,"related_event":null,"related_job":null,"reason":"Actual meaning, selected outcome and why","evidence":["Actual source/owner/current-responsibility evidence"],"remaining_obligations":["Independent unresolved duty, if any"]}
```

Modes:

- `route`: select an originally configured task and actual admitted package when
  execution needs one. For an outgoing fixed plan, only `@delivery` with the SAME
  package/plan can be selected; the owner clarifies meaning, without an effect or
  acceptance grant. Another fresh Luna classification must still succeed, or
  return a truthful `@unresolved`. The command itself launches/sends nothing.
- `control`: task/package/related fields are null; reason/evidence record actual
  processing of this input control only. Do not invent empty remaining obligations
  or declare effects/other jobs settled. Existing source/outbox/consumer/effect
  holds remain. A normal fresh classification commits control responsibility;
  actual notification receipts and every independent hold still govern processing.
- `coalesce`: task is null; name the exact existing same-role related_event,
  related_job and its package, with actual owner evidence of one purpose. This
  preserves the already admitted/running/ended job instead of scheduling another
  executor. Its numeric END does not process the old source: the existing target
  must actually close/process, and all independent obligations must clear.

Owner resolution appends bounded history beside the unchanged payload/hash and
original attempt/result. It freezes into subsequent task context. Stale hashes,
foreign actors, unknown/live classifiers and already reserved/executed originals
are refused. It does not overwrite source, notice ACK, owner/runtime cursor,
admission or old results; an already ACKed input is not re-ACKed. Previously
unACKed sources receive only the normal delegated receipt after fresh validated
classification and durable responsibility. Default limit is four owner decisions
per input, with byte bounds; unresolved/exhausted cases remain visibly owned.
Current genuine source meanings and owner choices are evidence, not proof from an
enum. This capability neither extends a resource lease nor provides DSN access,
native execution, account repair or unattended coordinator wake.

The selected canonical method is explicit:
`canonical_publication:{method:"retention-same-inode-v1",library:ABS_LIBRARY}`.
That library must expose the actual selected `retention.snapshot_lock`. The current
live message-board substrate has it; this isolated base does not. Tests use an
explicit owned interface fixture, never overwrite/copy the dirty live library or
call its global lock. Initial exact preimages are acquired under that cooperative
lock. Publication reacquires it, checks every regular single-link file's exact
bytes/inode/metadata and current role/controller/source authority, then durably
creates compressed BEFORE-only recovery backups for all targets before any write.
The service writes/fsyncs/readbacks each EXISTING canonical inode; it never uses
inode replacement, chmod/chown, canonical directory widening or worker-owned locks.
Each receipt names the selected method, compressed preimage, model producer, actual
service publisher, role and collector. Peer changes fail preconditions rather than
being silently overwritten. Same-inode creation of a missing target is unsupported.

The cooperative lock does not establish CAS against arbitrary noncooperating writers,
and multi-file/same-inode writes are not atomic. Interruption can leave partial
bytes: exact before backups, proposed bytes, prior effects and unresolved intent
stay held; generic effect receipts cannot waive the intent or release/process it.
No blind replay, automatic rollback or lost-actor inference from matching bytes.
Automatic interrupted-write resolution is inactive pending supported exact source/
effect recovery; healthy normal jobs do not need per-job manual reconciliation.
Lock contention retries within bind/task budgets with the same owned responsibility,
never another model or false END. Backups are registered conserved producer recovery
artifacts: retirement still needs actual processing+24h and all consumer/source/
outbox/recovery/effect-uncertainty holds. No canonical/platform cleanup follows.

The delegated collector then genuinely consumes its own routine result/effect
handback on the board. Its receipt names the service actor and delegating role,
not a fictitious human read. External recipients/duties and separate outboxes
remain owned. The supplied Work example covers its seven exact canonical files.
Branch ref/network and QA CI/resource callbacks remain with their actual owners;
this file-only callback does not claim their effects or override admissions.

Actual partial/failure/scope evidence takes an informative delivery path even
when artifact capture, category or effect admission fails. Each declared artifact
is challenged independently within the bound; successful witnesses survive a
missing/invalid neighbor, and the original return is retained. Non-DONE `blocked`
is a traced alias for `blocker`; DONE/blocked is invalid. Prompts name all admitted
categories. Other malformed results receive causal owner questions with the exact
original meaning, never invented completed/consolidated semantics.

Necessary allowlisted handoffs are retained as **incomplete questions**, preserving
the original handoff/result, actual capture/error/exit and unresolved duties.
One fresh Luna response classification precedes real service delivery. Posting,
pickup, processing and settlement remain separate; successful failure notification
does not close the held task, reconcile effects or release its integration slot.
Independent incoming classification can progress. Invalid/unauthorized handoffs
stay in original source with a causal owner question; they grant no new effects.

Artifact strings and structured `{path,...}` entries both produce exact bounded
witnesses and content-addressed durable source bytes. Runtime-owned disposable
files may retire; role/canonical files are never automatically deleted. Outside
scope, link, malformed, changing or over-budget artifacts hold capture rather
than silently skip. Frozen consumer inputs materialize only the declared bytes
under that consumer's new attempt directory, so later canonical changes do not
replace an old report's meaning. `artifact-source ATTEMPT PATH` exports bounded
base64 source for the actual custodian; an actual addressed consumer may add
`--delivery ID` for its exact already posted artifact grant. This is a source
recovery operation, not shared journal/profile discovery. Held blobs and source
metadata have cumulative limits/backpressure; broad automatic compaction is absent.
Selected-owner report returns use explicit `owner:job:version` source contexts,
with source_attempt=null. Their public in-scope artifacts receive the same custody
without inventing a model process. Private/unavailable artifacts reject the return
for that actual owner to conserve/correct; they are never silently skipped.

`session_storage:{mode:"producer-owned"}` keeps the selected account's CODEX_HOME,
authentication, SQLite/log roots and existing history in place. It requests only
history persistence `none`, disabled feedback and disabled shell snapshots;
`config/read` must verify these effective capture controls before the first model
turn. A matching echo proves settings, never logical ownership or physical
absence. The [configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference)
documents the controls. Command-specific preflight passes supported `-c` overrides
to MCP/features metadata, individually disables every effective MCP server and
requires disabled readback. `--strict-config` is an app-server option, never an
MCP/features/version argument. Model/provider/effort, sandbox and account checks
remain required. Metadata child exits are recorded separately from task END;
a proved pre-start refusal has no fabricated task begin/end or capacity claim.

Qualification3 on e82b recorded this unsupported-flag failure before any model
and a separate failed metadata control with mixed logical store ownership. Its
safe reports and opaque evidence remain unchanged. A newly allocated SQLite/log
directory MUST NOT be considered exclusive. `owned-attempt` is now refused before
allocation/start, without silent fallback. No platform SQLite/log tree is created,
scanned or automatically deleted by this runtime. Legacy `state/sessions` is
excluded before stat/traversal even during byte accounting, and its journal rows
remain opaque ownership holds. No alias search, database census or profile purge
is an ownership proof.

Ephemeral request/readback, unsubscribe, numeric owned exit, report retirement
and shared-profile residuals remain separate. Every started control records a
scoped unqualified shared-account residual, its actual known thread UUID when
observed, and its real runtime custodian. This is visible in attempt detail;
nonexistence is never inferred from not-loaded. Needed meaning is retained in
bounded journal/report custody. Exact conserved producer report files may retire
at actual processing+24h plus all dependent source/consumer/outbox/recovery/
uncertainty holds. Shared-store uncertainty does not freeze unrelated conserved
queues. The sampled guard bounds runtime-owned journal/artifact bytes/counts and
stops only its owned child on overflow; shared/legacy stores are explicitly
unmeasured and cannot be bounded by that guard. Attempt limits bound new starts,
not unknown shared auxiliary byte growth. No hard quota or general blob compaction
is claimed.

The [supported delete API](https://learn.chatgpt.com/docs/app-server) concerns
persisted threads and spawned descendants; ephemeral roots cannot be deleted.
It is not a substitute cleanup call for these ephemeral roots. Persistent exact-
owner cleanup would need separately qualified ownership, descendant/effect/source
custody and retention before that supported operation; it is not implemented here.
Actual platform residual reclamation remains a class-specific inactive frontier,
with no shared daemon attachment, credential move or new per-job permission.

Command completion capture includes supported item/turn IDs, status, nullable
numeric exit/duration and a bounded provider process label. That label is not an
owned OS handle. No raw command/output protocol fields, reasoning or credential
content is retained by this metadata capture, and no global descendant-liveness/cost claim follows.

Use `status`, `hold EVENT --reason TEXT`, `release-hold EVENT --receipt FILE`,
`conserve-artifact PATH --receipt FILE`, `ack-alert ID --receipt FILE` and `cleanup`
for exact owned operations. Healthy states emit no alert; unchanged violations
recur as distinct durable occurrences until resolved. Failed alert delivery records
one stable channel incident per role, with causal detail and exact outbox references;
it cannot generate a new incident per failed alert. The original violations and
channel incident continue recurring without deduplicating their occurrences. Old
per-alert incident detail is conserved while retired from recursive notification.
Channel recovery clears only the channel incident once all its delivery errors
are reconciled. Alert retirement also waits
for actual consumer/delivery processing plus 24h.

Only after separate qualification/disposition:

```sh
python3 "$RUNTIME" --config /absolute/private/config.json service-unit
python3 "$RUNTIME" --config /absolute/private/config.json run --enable-models
```

`service-unit` renders, never installs, a unit with a stop budget derived from two
turn deadlines, interruption, bounded metadata/RPC and owned teardown. With the
example deadlines it is 4176 seconds, replacing the incompatible 900s example.
SIGTERM/SIGINT stop new launches/intake and collect owned work. `Restart=no`
avoids losing unknown handles through automatic replay. After forced loss, retain
journal/artifacts/grants and actual original collectors for recovery. Rollback:
stop gracefully, inspect real held effects/deliveries, revoke each exact grant
from its actual owner (`revoke ROLE --grant UUID`), then restore prospective board
routing only through that owner's supported handoff. Preserve existing cutovers,
queues, source, private evidence and all consumer/recovery holds; do not uninstall
by deleting responsibilities or retiring a worktree/profile.

Rollback source catch-up must cover pause intervals explicitly. From the genuine
owner after exact grant revocation and supported self-pause/queue restoration,
`owner-catchup ROLE --after BEFORE_SEQ --through AFTER_SEQ` reads only that owner's
addressed/own-thread source in the fixed interval. Use next_after with the SAME
through until complete_interval. Posts without notification rows are preserved
as source, not fictitiously ACKed; already processed responsibilities are skipped
and pending originals remain identified. The command changes no membership/cursor,
never resurrects a completed role, and does not replay work. The real owner
consumes/routes unresolved material and uses its supported actual receipt path.

## Genuine coordinator control receive

Selected option A keeps managed routine intake and each genuine existing owner's
cooperative receive duty. [coordinator-receive.md](templates/coordinator-receive.md)
gives concrete board watch/notifications/read and recipient delivery-show/stage
commands, exact identity/source-role selection, paging and lost-hint handling.
Use it in persistent owner contexts, never append it to a disposable worker as an
owner-impersonation instruction. Receive at actual supported points while continuing
the existing backlog Goal. The delegated runtime remains sole normal intake/ACK
writer; no competing ack_seq/intake cursor, foreign queue drain, native handle
wrapper, replacement managed_owner or extra daemon. Questions/effects/alerts and
selected same-owner Reviews work need real receipt and actor control. Automatic
routine handbacks remain with their delegated callback. Availability while busy,
idle, absent or in an existing native wait is not established by instructions,
membership, socket hints or queue acceptance. Targeted unattended wake is forward
work. Status exposes declared receive mode, delivery creation/frontiers and pending
custody; configuration never proves active receipt/adoption. Root external,
Dispatcher/Cloud unenrolled; Reviews preserves actual opaque method/collectors.
