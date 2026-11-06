# Opt-in coordinator runtime

The [explicit software processing interface](owner-processing.md) supports
Work-issued bounded consumption of stopped software duties and separately
selected future intake in their original journal. It preserves original grant
revocation, effect holds, real collectors and selected role procedures.

For first scoped Board or collected-return ingress, use the
[actual-owner mapping interface](local-integration.md#first-ingress-actual-owner-mapping).
Its explicitly selected `processing-map-input` operation observes permitted
receiver revisions before reservation. Missing metadata stays unresolved;
ordinary message text supplies no point or native authority.

The [closed integration lifecycle](closed-integration.md) separates genuinely
closed Work execution from unresolved original responsibilities. It provides
explicit retirement and one-use next-window selection without promoting held
results, waiving UNKNOWN effects or replaying old inputs.

The [prospective ordinary-effects procedure](ordinary-effects.md) describes
explicit future authority in the unchanged existing journal, service-owned
Branch/QA tool execution/readback and independent semantic acceptance. It is a
source capability; actual package selection, consequence examination and live
deployment remain the operating owner's work.

This candidate dispatches actual bounded Work, Branch, Reviews and QA tasks.
Fresh Luna6 LOW sessions classify each incoming message and each model response;
validated classification and queued responsibility commit before delegated ACK.
Frozen batches, reservations and outgoing responsibilities live in SQLite
WAL/FULL. Work and all integrators use Sol6.1 XHIGH. New execution rotates over
the shared enabled pool; actual role-owner accounts remain unchanged.

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

## New execution pool

The runtime reads `~/ai/tools/direct-child/routes.toml`, `providers.codex.pool`,
for every NEW classifier, classifier recovery, task, diagnosis and remaining-work
successor. This is separate from `profiles` (account authorization), role receive
addresses and delivery recipients. Existing config profile pins and a diagnosis's
profile suggestion remain recorded advice; they do not bypass ordinary rotation.
No config/grant digest migration is needed when the existing authorization covers
the shared pool. The supported prospective current-configuration draft authorizes
all five known public labels (`.codex`, `.codex2`, `.codex3`, `.codex4`, `.codex5`)
without enabling them or asserting availability;
original configurations and receive identities stay immutable. Its release pins
all static control bytes except the supported membership value, so live updates,
reordering and empty pauses preserve the current capability. See
[current-configuration.md](current-configuration.md) for the exact guards and
missing-route/close boundaries. An explicit `execution_pool_routes` absolute path selects another
public control file for an isolated installation/fixture; adding/changing that
config field requires the existing offline config reconciliation.

Enabled membership is the current ordered public control value and follows live
user changes. Supported labels, illustrative subsets and historical observations
do not fix that membership or exclude accounts from later user selections.
After separate adoption, inspect or change the ordered shared membership with
the following syntax examples. Apply `set` only for the actual user selection:

```sh
python3 "$RUNTIME" --config /absolute/private/config.json execution-pool
python3 /absolute/adopted-checkout/tools/direct-child/execution_pool.py status
# Illustrative subset only; this is not a current-membership assertion.
python3 /absolute/adopted-checkout/tools/direct-child/execution_pool.py set .codex2 .codex3 .codex5
# No names means an explicitly empty pool: NEW execution cannot proceed.
python3 /absolute/adopted-checkout/tools/direct-child/execution_pool.py set
```

The public control tool accepts `--routes /absolute/public/routes.toml` before
the subcommand. Use the same routes file in the parent dispatcher (`--config`).
Runtime, parent dispatcher and public control tool all default to
`~/ai/tools/direct-child/routes.toml`, including when invoked from another checkout.
It changes only pool membership, preserving other settings. Empty/invalid,
missing, malformed-counter and authorization-incompatible states stay visible;
there is no private capacity probe, automatic borrowing or retry on another
account. Runtime `status` includes current membership and each attempt's actual
choice, advice, reservation turn and admission witness. A preview reserves nothing.
Runtime `execution-pool` returns shell status 2 with JSON `state: held` for empty,
invalid, busy or incompatible controls. Public `status` returns 2 for an empty
pool (JSON `state: empty`) or invalid state (`held`); a successful `set` to empty
returns 0 because the requested update succeeded. Runtime's broader `status`
keeps held pool details nested in its journal report. Status may initialize absent
lock/counter files without reserving a turn; runtime inspection also opens its
journal. Parent `--dry-run` creates no control state and validates even a singleton's
existing counter. It refuses empty/corrupt/busy state; an absent counter previews
turn zero. Every successful preview is an unreserved snapshot, never admission.

Runtime and parent automatic workers share `rotation.state_dir/codex.counter`.
Turns advance under flock and fsync, including singleton pools, and are never
refunded after failed preflight, aborted reservation or journal rollback. With
stable membership, consecutive reservation turns cycle evenly; restart retains
the counter. This is reservation fairness, not equal tokens, completions or known
account availability. Updates preserve the counter and use its current turn modulo
the new ordered membership; they do not restart a cycle. Empty existing counter
state is refused, never reset. There is no cross-file crash transaction joining
the counter to SQLite, and no power-loss atomicity claim for the counter write.

Cooperating updates and process admission share a short control/counter lock,
held through runtime process creation and BEGIN. An update that returns before
admission applies to it; an update waiting behind an admission applies afterward.
A disabled reserved attempt stays on its original profile and is known unstarted
when no process was created; it is never silently reallocated. A frozen job with
no attempt can retry allocation under its original controller after pool recovery.
Busy runtime allocation stays visible and retries that untouched reservation;
busy admission waits within the existing bind budget. Existing running/unknown
calls keep original handles, profile and custody. Accepted effects are not replayed.

Parent automatic direct Codex launches recheck after preflight immediately before
`codex exec`; native launches recheck immediately before creating the local native
caller. An already admitted native call may reach its adapter later on its original
account. No provider-side cancellation/revocation is claimed. Parent workers with
retained advice use `--profile-advice .codex3` and omit `--profile`. Explicit
standalone `--profile ... --override-reason ...` retains manual authorization,
including outside the automatic pool; enforcing it globally needs separate scope.

Deploy the matching runtime, `direct-child/execution_pool.py`, dispatcher and
`direct-codex-child/launch.sh` together, retaining the directory layout. Older
callers/manual file edits do not participate in the full admission/update protocol.
Do not change `rotation.state_dir`, replace lock/counter inodes or reset counters
while callers run; those need a separately reconciled cutover. Locks coordinate
cooperating local callers only, not noncooperating editors or other machines.

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
controller/review/delivery duties and resolved or inherited history. An inherited
failure must match an exact controller-supplied frozen input/prior-result source
and include the producer's current-duty rationale. It stays in original_failures
and inherited_history, never resolved_history; no old job/effect/hold is settled.
Scope remains an attestation requiring independent interpretation. Current local
defects and current adverse tools still block regardless of related old history.
The required file-worker
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
byte witnesses. Staged semantic PARTIAL/FAILED/UNKNOWN continuation also supplies
its available own protocol metadata; it can remain partial without guessing IDs
or replaying work. Ambiguous DONE can use the
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
meaning. Declared canonical input paths retain their referents, including inside
groups. Explicit stage paths declare postimages; all mapped stages are also
independently conserved. Publication retains a captured canonical input snapshot
unchanged; conserved stage bytes and joined publication receipts witness the
postimage. The original result is never rewritten. Inline preparation can use
artifacts=[]; log/directory mentions belong in findings because NONE/header-only
metadata grants no acquisition exception. Missing/invalid item representations can
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
membership, socket hints or queue acceptance. The explicit pointer adapter below
does not establish unattended wake. Status exposes declared receive mode, delivery creation/frontiers and pending
custody; configuration never proves active receipt/adoption. Root external,
Dispatcher/Cloud unenrolled; Reviews preserves actual opaque method/collectors.

### Explicit existing-context control pointer

Decision13 adds an optional one-shot adapter for an **exact runtime delivery ID** of
kind question, alert, effect-request or result. It sends a bounded pointer to the
full unchanged delivery; it cannot dispatch work. The genuine source role owner
prepares/sends it from its current actor context. Its recipient must already have
the selected role's current enrollment, exact profile, active membership and
managed receive route on the same board/runtime. Reviews without enrollment is
refused. No managed_owner, replacement coordinator, route downgrade, grant,
normal intake, classification or delegated ACK change is supplied.

| Selected mode | Required applicability | Effect and dependency |
| --- | --- | --- |
| `queue-existing` | Evidence of this existing context/profile; native availability can be unknown | Plain queue helper, no resume; true queue ID required for processing proof |
| `queue-resume-existing` | Same explicit binding; native availability can be unknown | Explicit `resume=True` public helper interface required; no fallback |
| `active-only-steer` | Active context and exact in-progress turn | Public steer/RPC helpers; expected turn and client message recorded before mutating RPC; no queue ID |

Active-only steer refuses unloaded/unknown contexts. The inspected base43f includes the plain
queue helper, but **does not include active_transport.py/active_rpc.py or the queue
resume interface** present in a different other-owned shared checkout. Those
optional modes refuse before calling transport unless compatible public sources
are selected at board_library. The independently inspected installed shared
helpers already express these interfaces and can be explicitly pinned there;
baseline absence does not require copying their other-owned changes. This code
neither copies nor qualifies that checkout. Pins identify bytes, not source authority or daemon/native
compatibility. Active steer additionally checks the actual public helper's active
metadata/turn and uses its expectedTurnId precondition; a changed turn cannot be
silently substituted. The queue interface cannot independently establish native
availability; caller binding evidence and later consumer proof remain necessary.

Future actual use needs its own caller scope, binding and applicability evidence.
Publishing this adapter authorizes no live control/native operation, new Branch
turn or role adoption. Existing legitimate operational authority can supply the
selection; the adapter adds no default global human approval gate. Source/actor
checks and attributed evidence are cooperative same-account checks, not independent
authentication. A syntactically valid UUID is not context/profile binding evidence.

The selection JSON has exactly these keys (uppercase values are placeholders):

```json
{
  "intent": "NEW-CONTROL-UUID",
  "mode": "active-only-steer",
  "recipient": "GENUINE-RECIPIENT-UUID",
  "profile": ".codexN",
  "scope": "delivery-control-only",
  "evidence": ["Actual caller selection, scope and why this delivery needs control"],
  "binding": {
    "context": "GENUINE-RECIPIENT-UUID",
    "profile": ".codexN",
    "state": "active",
    "turn": "ACTUAL-IN-PROGRESS-TURN-UUID",
    "valid_until": 0,
    "evidence": ["Actual current context/profile/channel applicability evidence"]
  },
  "helper_sources": {
    "queue_transport.py": "SELECTED-SHA256",
    "active_transport.py": "SELECTED-SHA256",
    "active_rpc.py": "SELECTED-SHA256"
  }
}
```

Use a fresh finite future epoch less than one hour away for valid_until. Queue
modes use turn:null, state active/idle/unknown and only queue_transport.py in helper_sources.
Sources are exact regular files in the configured board_library, loaded with
isolated pinned dependencies. Evidence lists contain 1–16 nonempty strings of at
most 2000 UTF8 bytes; the entire selection is at most 16000 UTF8 bytes. The complete
pointer must fit the helper's 700-character bound; it is never truncated.

```sh
python3 "$RUNTIME" --config "$CONFIG" control-prepare "$SOURCE_ROLE" "$DELIVERY_ID" \
  --selection /absolute/own/control-selection.json
python3 "$RUNTIME" --config "$CONFIG" control-show "$SOURCE_ROLE" "$INTENT_ID"
# Only within the separately selected actual caller operation:
python3 "$RUNTIME" --config "$CONFIG" control-send "$SOURCE_ROLE" "$INTENT_ID" --execute
# Withdraw only a preparation that has never been attempted:
python3 "$RUNTIME" --config "$CONFIG" control-cancel "$SOURCE_ROLE" "$INTENT_ID"
```

Prepare persists the exact selection, full-payload hash, local attempt/client
marker and pointer before any transport. Send checks the original source/grant,
current enrollment and fresh binding again, checks the helper source/API, then
commits an inflight claim before calling that single selected mode. Steer records
the exact turn/request correlation before RPC and acceptance separately. Queue's
local client marker is in the pointer; the actual server queue ID is learned only
from its return. These two identifiers are never substituted for one another.

Repeating the same intent returns the retained outcome without another send.
An accepted/unknown/inflight attempt blocks a new intent for that delivery. No
automatic pre-retry, channel fallback, resume, native start, original ACK/cursor
rewrite or business replay follows. Helper preflight refusal is recorded as
not-called; changing a refused selection requires an explicit new caller intent
and fresh actual evidence, never an automatic retry. A still-prepared binding
that expired can be withdrawn before selecting a new one. An interrupted inflight
sender stays held with its actual collector; the API supplies no foreign recovery
or generic clearing operation. A timeout/unknown queue outcome without a real queue
ID remains an explicit consumer-proof gap. Inspect that outcome and return it to
the owning caller; do not guess an ID or resend to populate proof.

Transport acceptance, board ACK and managed_pending prove neither arrival nor
processing. The actual recipient first reads the full delivery and records pickup.
For a queue control, processed/settled additionally require the real returned
queue_message_id, state processed and actual consumer evidence in receipt.transport,
even though managed membership/notice route remains unchanged. For steer, never
invent a queue ID: receipt.transport is refused. Instead receipt.control must have
exactly:

```json
{
  "kind": "existing-context-control",
  "intent": "CONTROL-UUID",
  "attempt": "RETAINED-ATTEMPT-UUID",
  "client_message_id": "RETAINED-CLIENT-MESSAGE-UUID",
  "turn_id": "RETAINED-STEER-TURN-UUID",
  "received_by": "ACTUAL-RECIPIENT-UUID",
  "profile": ".codexN",
  "full_read": "RETAINED-PAYLOAD-HASH",
  "state": "processed",
  "evidence": ["Actual full-read/pickup and context/turn/client-message association"],
  "disposition": "Actual substantive control action and remaining independent obligations"
}
```

This is an honest attributed control proof, not queue-consumer proof or independent
verification of semantic completion. Top-level receipt.evidence and the existing
pickup → processing → settlement requirements remain. Consequential questions
still need resolution; effect duties retain actual effect-owner reconciliation.
Settling a control grants no execution/publication/acceptance authority and clears
no independent source/outbox/recovery/effect duty. Fresh unchanged violation
intervals still generate distinct deliveries and intents; same-intent idempotence
never suppresses another interval's alert.

Control records/steps are additive bounded board custody: max_events intents and
max_bytes UTF8 accounting, with backpressure instead of discarding held records.
There is no automatic deletion/retirement for these records. Retain them and their
sources until actual processing completion +24h **and every hold**, including any
uncollected send/consumer uncertainty. No platform physical cleanup is claimed.

### Automatic service control and independent receiving duty

Decision16 adds a prospective service capability under an already selected source
role's outgoing delegation. The actual source owner issues it from its genuine
context. It authorizes the distinct configured service actor, never an impersonated
source owner or a native owner grant. Existing recipient enrollment, membership,
profile, board/runtime identity, kind and exact source grant are rechecked before
effect. Root is external and cannot be selected here; Reviews without genuine
enrollment remains unavailable. No automatic enrollment or grant acquisition occurs.

The new policy has exactly these keys; all identities/epochs/hashes below are
placeholders, not current live bindings:

```json
{
  "scope": "delivery-control-only",
  "recipients": {
    "Branch": {
      "context": "GENUINE-EXISTING-OWNER-UUID",
      "profile": ".codexN",
      "mode": "queue-resume-existing",
      "availability": "unknown",
      "evidence": ["Actual selected existing context/profile/mode authority; activity unobserved"]
    }
  },
  "kinds": ["question", "alert", "effect-request", "result"],
  "helper_sources": {"queue_transport.py": "SELECTED-SHA256"},
  "valid_until": 0,
  "evidence": ["Actual source owner delegation, scope, rationale and dependency selection"]
}
```

Select an actual finite future expiry, exact configured enrolled recipients and
queue-existing or queue-resume-existing. Automatic policy deliberately states
native availability unknown; it does not invent active/idle/turn evidence or choose
steer as fallback. The role's scoped/revocable capability serves subsequent controls
without per-message owner approval. Each evidence list is 1–16 strings <=2000 UTF8
bytes, policy <=16000 bytes. Existing max_events/max_bytes bound retained policies
and intents, with backpressure. No held record is discarded to renew a capability.

```sh
# Prospective actual-owner operations after separately selected deployment/scope:
python3 "$RUNTIME" --config "$CONFIG" delegate-control "$SOURCE_ROLE" \
  --policy /absolute/own/service-control.json --authority /absolute/actual/selection.json
python3 "$RUNTIME" --config "$CONFIG" revoke-control "$SOURCE_ROLE" "$DELEGATION_ID"
```

Delegation captures the current board post frontier. Only exact new runtime
deliveries after that cutover and within its selected kinds/recipients are eligible;
old notices/native queues/ACKed inputs are not imported. Replacing a policy revokes
the prior capability prospectively and keeps its old intents/duties. Automatic
dispatch prepares a deterministic UUID intent per capability/delivery ID, including
real digest-keyed failure deliveries. There is at most one new bounded helper call
per pump pass (including a conservatively counted preflight refusal); subsequent
passes progress other deliveries. Accepted/unknown/inflight intents never retry.
Fresh unchanged interval alerts remain distinct deliveries, not deduplicated by
the intent key. Source classification gates and delegated ACK remain unchanged.

Delivery pumping examines at most two pages of 16 journal rows per pass, including
currently ineligible rows. SQLite sequence range queries bound the scan itself;
filtering eligible rows before a LIMIT would still scan an unbounded settled tail.
One cursor follows inserts and classification releases after dispatcher construction.
An additive `delivery_wakeups` table retains one scheduling hint per outbox;
insert/release triggers give that hint a fresh sequence without changing custody.
This prevents a fresh row scanned before classification from waiting for the old
sweep when its classification commits. A second cursor rotates
through all retained rows up to a fixed cycle frontier, then starts another cycle
with the current frontier. Existing rows that later become eligible, owner return
corrections and settled rows with outstanding receipt duties remain discoverable.
Neither cursor changes delivery, processing, hold or source state.

The lanes alternate first access to the existing one-helper-call budget. If that
budget is spent, fresh traversal pauses until a later pass rather than advancing
unsent fresh controls into the history sweep. Old rechecks still get a page each
pass. New interval alerts retain their own occurrence/delivery/intent identities.
Both runtime pump callers (`tick` and `alerts`) await a cooperative pass that
yields between individual rows and checks stop before the next row. Intake,
durable receipt handling, reconciliation and scheduling precede tick pumping.
The synchronous `pump_deliveries` entry remains bounded for non-loop callers;
`alerts` is now an internal coroutine and its callers must await it.

Existing version-1 journals gain the empty hint table and triggers when opened;
existing outboxes are not backfilled or rewritten. Configuration digests/defaults,
schema version, capabilities and receipt contracts remain unchanged. The new
internal page policy is 16 examined rows per lane. Cursors are process-local
scheduling hints and reset on restart;
retained duties are revisited from the beginning, not acknowledged or released.
The bound is examined rows, not wall time: an individual board/helper operation,
other dispatcher phases, sustained arrivals exceeding throughput or unavailable
authority can still delay progress. It establishes neither runtime health nor a
native latency guarantee. No queue/history removal or provider retry is added.

This adds **no live capability by installing code**. Deployment must separately
select source/helper pins/mode/context authority and actual owner delegation.
Installed queue_notice(resume=True) compatibility is expressible at the configured
library without copying foreign source. Static grammar/pins, synthetic calls and
one manual Branch receipt do not establish automatic daemon/receiver health.

Control receiving is independent of substantive routine completion. A legitimate
same-owner result/effect-request callback still performs its delegated collection
under the original successful DONE/source/completion/effect fences. Its proof
explicitly claims neither native receipt nor genuine-owner full-read. A separately
required control remains control_receipt.pending, even if substantive state is
settled. delivery_satisfied stays false and the combined processed_at stays null;
after both duties, the processing clock is the later actual completion. Sources,
jobs/outboxes and retirement holds therefore do not settle from callback/acceptance.
Pending settled deliveries are revisited without resending; cached pre-upgrade
receipts are refreshed once. Retained093 intents imply an outstanding duty even
without the new additive tables. Original callback stages/history are not rewritten.
Status exposes the retained intent/transport outcome, or not-prepared when authority
expired/refused before construction. That gap stays pending even after substantive
completion. The actual source owner can explicitly prepare that exact outstanding
control under fresh scope/binding; no automatic renewal or business replay follows.

The genuine recipient can record the independent duty without replacing a completed
callback stage:

```sh
python3 "$RUNTIME" --config "$CONFIG" control-receipt "$SOURCE_ROLE" "$DELIVERY_ID" \
  --receipt /absolute/own/control-processing.json
```

Use top-level evidence plus the exact existing transport proof for queues or
receipt.control steer proof above. Same checks also apply to direct delivery-stage;
neither path invents native arrival/full-read. For a prepared/refused unattempted
control, genuine direct full-read/disposition may instead supply receipt.control:
`{kind:"owner-control-disposition",intent,full_read,disposition,evidence}`. This
records native_receipt_claimed:false. It cannot waive an attempted unknown queue,
inflight collector, effect or other consumer duty. An uncollected/unknown attempt
still requires its real collector/consumer evidence; no generic clearing/retry is
supplied. Receipts are bounded, attributed and immutable; they are cooperative
evidence rather than independent authentication or semantic verification.

### Legacy collected recovery diagnosis

Pre-linkage diagnoses with missing/null prior_task_attempt can be recognized from
retained exact job/active task/collector evidence: one legacy diagnosis after that
task's collected end, actual numeric ENDs/collection on both, ordered chronology,
matching original recovery collector and no successor task. The derived view names
its basis; no attempt detail, old result or missing field is rewritten. Recognition
permits an owner-disposition question only, never automatic profile handoff/replay.
Semantic UNKNOWN/null, incomplete capture, original handoff/inventory errors,
effects/hold_reason and all five Branch business-slot obligations remain independent.

The existing request-recovery redispose/defer/remaining-work interface now recognizes
that closure. A genuine role owner may queue its exact request; only the lawful
original disposition collector consumes it. A foreign status Store identity is not
custody transfer. Remaining-work still needs original closure, reconciled effects,
explicit resume disposition, source/legacy/publication/resource fences and fresh
diagnosis with the authentic new selection. Ambiguous/multiple diagnoses, missing
numeric END, wrong collector or successor evidence return a precise remaining
question with exact IDs. No raw-history search, foreign wait, force-release, source
root widening, handoff deletion or task launch is used to make compatibility pass.

### Bounded integration witnesses with distinct delivery placements

Integration debt can use `integration-debt-v2` when large result/detail objects
repeat at known protocol placements. All delivery rows, recipients, required
frontiers, receipts, reasons, errors, handoff text and failure state remain
separate. The self-contained `shared_values` map carries full values once;
it does not merge duties or assert that equal snapshots have equal meaning.
Unknown fields inside these values remain complete. Unrecognized fields outside
these placements, malformed JSON and noncanonical TEXT stay verbatim and can
still exceed the unchanged result bound.

A folded column has `format: integration-shared-json-v1`, a `value`, and explicit
`references` with `json_path` and `sha256`. Only those recorded paths contain null
placeholders; an original object that looks like a reference remains ordinary
data. Each occurrence keeps its row/column placement through `original_column`.
Shared entries may themselves reference a repeated `prior_turn_result`.
`integration_evidence.expand_shared(column, debt['shared_values'])` reconstructs
the complete represented JSON without I/O and refuses missing, changed or cyclic
shared material. Full original TEXT remains in the original journal; the existing
`expand(column['original_column'], independently_authorized_row)` verifies exact
original bytes. Older historical-window projections retain their existing
original-detail reference and historical-debt expansion dependency. Neither
function grants access, authenticates row truth, settles effects or establishes
durable availability. The witness is not a replacement for the original journal.

Exact owner-selected windows also require ordinary `processing.task` eligibility
for **every** member when a processing selection applies. Composition, selection,
reservation, task start and launch authorization recheck the applicable predicate,
including admission, task scope and ancestry. An owner window supplies no
exception; existing event, enrollment, grant, source and execution fences remain.
Paused management has no processing capability and cannot establish future
processing eligibility. Future execution must pass its own current selection.

The fictional in-memory construction controls are
`python3 -B tools/coordinator-runtime/tests/test_witness427.py`, alongside
`test_integration_bound419.py`. They exercise production journal, delivery and
processing methods with fictional allocations. They establish no actual case fit,
recipient comprehension, account availability, delivery success or rollout state.

### Complete receipts and the preflight boundary

Independent control receipts now retain the entire supplied JSON under
`control_receipt.receipt.supplied_receipt`, alongside actual actor and derived
queue/control-proof metadata. Top-level full-read/disposition evidence, additional
fields and the real queue consumer proof all survive. Repeating an independent
receipt requires the same complete meaning; changing supplied evidence is refused
instead of being treated as identical. This is attributed evidence, not independent
proof that the owner read or understood anything.

Direct delivery-stage also retains its complete receipts. A later substantive
stage may add its own stage evidence/resolution in the normal immutable stage
column while reusing the same control/transport proof. It does not replace the
independent receipt or erase its original full supplied meaning. Legitimate routine
callbacks still establish only delegated substance, never native arrival/full-read.

Control send rechecks pending duty and source hash inside the write transaction
that claims prepared → inflight, after helper preflight. A genuine direct
disposition during preflight therefore prevents the helper call even while
substantive processed_at is null. Once inflight is claimed, direct disposition
cannot waive it. Unknown transport combined with a prior direct/non-native receipt
also remains pending, with combined processed_at:null and false satisfaction.
This preserves unknown/inflight sender/consumer and source/outbox/retirement duties;
it supplies no native reconciliation/clearing/retry or claim about live race frequency.

Historical receipts that omitted supplied evidence cannot be reconstructed from
queue proof. No earlier conservation/adoption claim is retroactively supplied.
Aggregate max_bytes accounting remains a static/unexecuted question; finite existing
input/count bounds remain, without a new aggregate-capacity qualification.

### Use an already-qualified diagnosis for an already-held remainder

`request-recovery` additionally accepts this exact receipt shape:

```json
{
  "mode": "use-diagnosis",
  "reason": "Actual same-role owner reaffirms the captured target and WHY remain current",
  "evidence": ["Actual qualified diagnosis/consumed selection read and currentness authority"],
  "remaining": null,
  "diagnosis": "EXACT-CURRENT-DIAGNOSIS-ID",
  "selection": "EXACT-CONSUMED-REMAINING-WORK-SELECTION-ID"
}
```

This expresses the held Work928 relationship without requesting an equivalent
Luna diagnosis. The genuine owner queues it through the existing actual-owner
command; acceptance starts no model. Without the explicit restart option below,
only the existing lawful disposition collector consumes it. There is no automatic
foreign adoption or instruction to borrow a controller ID. Owner reaffirmation is recorded
within existing authority; it is not another blanket human/Source/CI permission gate.

Predicates are explicit: same active held task/reservation in awaiting-disposition;
current explicit diagnosis (including latest pending selection, never an old
collected substitute); actual collected zero/complete/error-free diagnosis;
configured and observed Luna LOW identity; matching prior task/original recovery
collector and authentic consumed remaining-work selection. Diagnosis semantic:null
is preserved. @owner, a current diagnosis disposition/question, defer, any newer
owner choice, successor or mismatched lineage remains binding. The existing original
closure/effects/resume/source/legacy/resource/publication/hold gates all remain.

The request captures bounded hashes of qualified diagnosis, original task source,
closure, reservation/token/members and selected owner purpose. Consumption rechecks those exact witnesses,
currentness, existing collector and fences in its allocation transaction. It
allocates at most one remaining task attempt within the SAME job/token/members,
consumes that request atomically and preserves original records. It never changes
the successful diagnosis/selection, fabricates task DONE, resets recovery to
diagnosing or increments a diagnosis count. The new attempt carries original
result/artifact references, prior hold, exact remaining/rationale, old selection
and current reaffirmation. Later ordinary task launch/admission/collection and
fresh preimage/staging/publication gates still decide actual execution/effects.

Repeating consumption does not allocate again. A late old diagnosis callback cannot
dispose a newer current/pending diagnosis. If predicates fail, the request/hold and
precise reason stay with the actual owner/collector; no forced SQL/history edit,
new diagnosis, stage replay, second integrator or generic unknown-effect waiver is
used to make the transition succeed. Existing per-job request and finite storage
bounds still apply. Source presence and fixture success establish no live Work928
successor, canonical publication, receiver arrival, rollout admission or acceptance.

### Explicit closure continuity after an owned ordinary service restart

A fresh normal `run` constructs its own Store controller. Merely replacing source
files, or constructing a Store with the prior controller UUID, does not provide a
collector transition. For this already-collected, held same-purpose remainder,
the genuine enrolled role owner can add exactly this optional field to the
`use-diagnosis` receipt above:

```json
"collector_continuity": {
  "scope": "closure-only-after-owned-restart",
  "from_controller": "EXACT-RETAINED-JOB-CONTROLLER-UUID",
  "service_actor": "EXACT-CONFIGURED-SERVICE-ACTOR-UUID",
  "service_end": 0,
  "service_collected": true,
  "evidence": ["Actual owned old service END/collection reference and restart scope"]
}
```

`service_end` must be the actual numeric old service END (zero above is illustrative),
not the status of a stop request, an inferred timeout or the task/diagnosis END.
This is an explicit cooperative owner attestation, not independent authentication
or proof that a process stopped. The caller still collects the actual owned service
and selects receiving/restart authority separately. No foreign process is adopted.

Supported sequence, only within that separate operational authority:

1. Retain the old owned service's actual drain/END/full collection and original
   task/diagnosis closure evidence. Select compatible corrected owner CLI and service
   code on the same configured journal, actor, enrolled owners and grants. Do not
   alter the configuration hash, borrow a controller or operate a second service.
2. From the genuine enrolled owner context, run `owner-controls ROLE --limit 100`.
   Its recovery entry now exposes the **retained job** controller, recovery owner
   and closure chain. A transient CLI/status Store identity is not that controller.
   Preserve the exact current held job/token/active task, qualified diagnosis,
   consumed owner selection and same target/WHY. Do not request `remaining-work`.
3. Submit the complete receipt using `request-recovery JOB --token TOKEN --attempt
   ORIGINAL_TASK --receipt FILE`. Supply the old service END/evidence and retained
   job controller; there is no caller-supplied fresh controller. This owner command
   only queues a bounded request. It may precede the normal fresh service start or
   be read by an already-corrected fresh service; it never starts the service.
4. The corrected fresh dispatcher's ordinary reconciliation consumes the request.
   It validates current source authority and all existing diagnosis/purpose/fence
   checks, then appends a closure-only handoff and allocates one same-job successor
   in the same journal transaction. Allocation refusal rolls back the handoff too.

The dispatcher refuses a non-distinct controller, any related live/unknown attempt,
unreconciled effects or an invalid prior closure chain. It preserves every original
task/diagnosis/selection record, original task collector/actual END, diagnosis
recovery owner and raw prior handoff. The request and successor retain before/after
witnesses: only the closure hash changes during the transfer. Reservation and all
other qualified currentness witnesses must match. Repeated reconciliation cannot
allocate another successor or equivalent diagnosis. Ordinary held reconciliation
also waits for explicit disposition of an owner-selected remainder, so a refused
request cannot fall through to processing the old result. Explicit redisposition
remains available through its existing path.

An already-pending request is immutable: this option cannot edit it, bypass its
budget or silently upgrade an old witness. A pending request without continuity
still cannot be consumed by a foreign controller. Changed evidence, a newer choice,
defer/question/disposition, successor, source/legacy/resource/effect/publication or
unrelated hold remains binding; retain the precise refusal for the actual owner.
Existing finite request/storage limits apply. A reserved successor is not started,
processed, published or accepted work. Normal launch/collection, peer preimages,
source/outbox/control/consumer duties and processing+24h **and every hold** remain.
This software contract supplies no live restart, Work928 continuation or adoption proof.

### Continuity and bounded delivery in the same dispatcher

Normal `tick` performs intake/receipts, collected classification and owner-request
reconciliation, and scheduling before its bounded delivery pass. Explicit retained
diagnosis continuity therefore does not wait for a complete old-delivery sweep.
Its transaction and currentness checks remain the same when delivery history is
large. A refused request stays pending with the held original; delivery traversal
cannot redispose it or release its integrator slot. A committed successor with no
observed start remains reserved with its actual custodian, without automatic replay.

Fresh and retained controls still share the bounded helper-call budget. Their
accepted, unknown and inflight intents and full consumer receipts retain their
independent meaning; allocation and traversal supply no processing or native proof.
The additive version-1 scheduling hints and asynchronous `alerts` caller contract
above remain in force. Eventual retained revisits require sufficient completed
passes in a stable process; this composition adds no wall-clock or migration
atomicity guarantee. The combined offline witnesses are in
`tests/test_receiving_integration.py`.

### Owner-qualified canonical-publication remainder

A held, collected routine writer can have reconciled effects while canonical
publication is incomplete. `use-diagnosis` continues to reject unrelated holds.
For this particular duty, the supported owner operation is an optional
`publication_remainder` operand on that same request, retaining the exact
consumed remaining-work selection and explicit diagnosis. It is never a new
business target, fresh diagnosis, old-result redisposition or publication waiver.

In the genuine owner's separately qualified context, read candidate operands:

```sh
coordinator --config /absolute/selected-config.json publication-remainder-basis JOB \
  --token TOKEN --attempt ORIGINAL --diagnosis EXACT_DIAGNOSIS --selection CONSUMED_SELECTION
```

This reads the original delegated routine run/staging custody and current exact
canonical peer witnesses under the selected cooperative snapshot lock. It
returns no business bodies, allocates nothing and makes no purpose decision.
The genuine owner must have lawfully read the retained target AND WHY, source
and effect evidence, and judge that the exact original purpose remains current.
The `purpose` hash binds the existing task, diagnosis choice and consumed owner
selection representations; a hash does not establish semantic sameness.

Include the returned object unchanged as `publication_remainder` alongside
`mode:"use-diagnosis"`, exact `diagnosis`/`selection`, `remaining:null`, and the
owner's authentic current `reason` and `evidence`. Use `request-recovery` with
that receipt. If an owned restart is involved, the existing independently
qualified `collector_continuity` operand is still required; neither a CLI Store
nor an old controller ID supplies collector custody.

Qualification requires the exact incomplete-publication hold, original
incomplete delegated routine run and matching current completion policy/grant,
local readiness, complete original staging custody, current source identity,
reconciled owner effects with no unknowns, every related collected numeric END,
all source/legacy fences, and current regular peer preimages. A missing original
run cannot be invented retrospectively. An unresolved publication intent or
uncertain partial write refuses even with an owner receipt. A known published
subset is conserved only while its exact recorded effects still match peers.
A fully published historical batch cannot use this capability for redisposition.
An unrelated hold refuses even if the operand otherwise looks complete.

The dispatcher rechecks the exact request witnesses and live role/source
authority in the allocation path. Any closure continuity and allocation share
its existing journal transaction: failure rolls that transfer back. At most
one successor is permitted in the same job/token/members; no old result is
reprocessed and no equivalent diagnosis is launched. Original results,
selection, diagnosis, stages, publication rows, outboxes and collector history
remain retained. The original hold and effect receipt accompany the successor;
its effects become unknown until its own normal reconciliation.

The successor takes a fresh staged snapshot only if the selected peer preimages
and completion grant still match. Its own successful collected result, local
readiness, artifact custody, exact-preimage publication and downstream delivery
remain mandatory. A later peer change still refuses publication. A stale
pending request remains pending, with its actual custodian; these operations
provide no cancellation, receipt rewrite, blind retry or unknown-effect repair.

These are cooperative boundary checks, not an OS sandbox, multi-file atomicity,
noncooperating-writer CAS or proof of genuine business readiness. The capability
alone supplies no deployment, adoption, real continuation, acceptance or full
cutover qualification. Prospective effect/epoch changes must be coherently
composed and observed separately before any actual use.

Owner command concurrency also relies on retaining SQLite's existing process
locks. Opening a journal now creates a missing database with `O_EXCL`; it checks
an existing file without opening and closing an extra raw descriptor. Such a
close can release POSIX locks held by another SQLite connection in the same
process. A separate CLI-process fixture exposed journal corruption after
multiple owner command connections; the retained failure is distinct from
business publication. Existing path-type/link/mode checks still refuse unsafe
journal files. This change does not repair a corrupted journal or qualify live
journal health.

See [prospective current configuration](current-configuration.md) for the supported
Work-selected same-journal release/configuration transition, its immutable
historical bindings, operating sequence and compatibility/collection limits.


[Bounded catalog and prospective Branch custody](bounded-catalog.md) describes the
joined seven-duty Work receipt, mechanical same-inode log prepend without full-log
reading/hash, and exact accepted-branch local-ref CAS lane. The prospective config
draft can explicitly select `--bounded-work-log`; old configuration/recovery and
unresolved historical custody remain original. Source support is not live rollout.

Continuing allocation boundaries use the existing Work processing selection.
An optional `service.allocations` object contains the complete fresh
`window-basis` return plus `target`, `reason`, `evidence`, and `custody` as for
`advance-window`, and explicit finite `expires` and `max_windows` (1–10000).
Work chooses that horizon and ceiling prospectively; neither the initial 40
inputs, 16 decisions nor optional one-hour admission policy is a permanent
lifetime rule. Omission preserves manual window boundaries. This selection is
issued through `delegate-processing`, with its actual original Work issuer,
current source/configuration, exact tasks, future frontier, and all existing
residency/concurrency/resource policies. It creates no ordinary-effect epoch or
acceptance and extends no existing expiry. Work separately chooses any genuine
ordinary epoch and its finite horizon.

The continuing capability can append up to that many new windows, including a
first window after configuration adoption, until its selected expiry. Each
append is attributed to the original issuer, capability and authority hash,
with a fresh boundary witness and unchanged custodian evidence. The original
window and every charged counter stay unchanged. Automatic boundaries share
allocation transactions; scanning limits each acquisition batch to remaining
input/event credits and checks authority before fetching bodies. Byte/file,
Board residency, rate, task, slot, per-source, effect and hold gates remain in
force. Expired, revoked, exhausted, borrowed, stale-source or mixed-window
authority refuses without adopting old work, releasing slots, completing input
processing or starting retention clocks. A manual intervening boundary requires
a fresh explicit capability selection; no old delegation silently follows it.

Boundary and configuration journal witnesses use per-table SQLite mutation
tokens and schema/sequence metadata, installed by the current Store source.
Bootstrap does not inspect historical bodies, blob keys, presence or sizes.
Triggers record subsequent insert/update/delete operations in their same
transactions; rollback rolls back the tokens. Missing/changed trigger coverage
refuses a witness; installing newly required coverage invalidates earlier
witnesses. These are cooperative currentness witnesses, not body hashes,
historical truth/immutability/whole-read attestations or hostile-writer isolation.
Source use still requires applicable origin, exclusion, custody and body-integrity
guards. Publication admission reserves the configured maximum artifact bytes
per outstanding publication intent without inspecting retained blobs; this may
pause earlier than an exact-body-size account. It does not measure held bodies
or authorize resolving, deleting or reacquiring them. Old holds remain owned.

After source adoption Work must take fresh configuration/processing/allocation
bases and make the actual selection. Existing private/canonical source must not
be inspected to obtain those allocation witnesses. A preserved shared residency
above a proposed ceiling requires a genuine bounded operator choice; deleting
shared records or refunding old charges is not a continuation mechanism.

For stopped/revoked originals, obtain the continuing basis using
`processing-basis --future-only`. Its `allocation` field is the complete fresh
window witness to place in `service.allocations.basis`; its `future_only: true`
basis permits only continuing future intake, with no retained sources, control
recovery, legacy-disposition or old input-resolution operations. New exact
package admissions remain possible under their own genuine selection. The
source/configuration transition also uses this prospective metadata witness.
The default `processing-basis`, historical retained APIs and manual window CLI
retain their original authority/admission contracts. Future-only witnesses carry
recorded old event hashes as metadata, without newly validating old bodies.
SQLite SQL mutation tokens do not attest incremental blob writes, direct file
rewrites or noncooperating writers; applicable body-integrity guards still run
at actual permitted body use. Work must never use a metadata-only basis as an
old-body validation, held-source clearance or native-operation qualification.

Continuous anchored integration and separate new-work discovery are an explicitly selected source capability; see [local-integration.md](local-integration.md) for point policies, concurrent scheduling, seven-duty rebasing and independent Work coordination. Existing retained tasks keep their original bindings until an authorized prospective transition.

Prospective operators can select the versioned [unified method closure](unified-method.md)
and the per-package operation/public executable contracts in
[ordinary effects](ordinary-effects.md#prospective-admitted-operations-and-public-qa-executables).
Both require actual Work's explicit selection; existing epochs keep their original interpretation.
