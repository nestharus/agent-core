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
python3 "$RUNTIME" --config /absolute/private/config.json enroll Work --delivery \
  --authority /home/nes/projects/rfq/planning/coordinator-runtime-rollout-20261103-01/CONSEQUENCE-DECISION.json
# For an already enrolled incoming/receipt-only grant, from that same real owner:
python3 "$RUNTIME" --config /absolute/private/config.json delegate-delivery Work \
  --authority /home/nes/projects/rfq/planning/coordinator-runtime-rollout-20261103-01/CONSEQUENCE-DECISION.json
```

Repeat only from the genuine selected Branch successor, Reviews and QA actors.
The automation actor never joins as an owner. Classification provenance retains
actual model session, attempt, configured/read-back binding and source author.
The additive board extension records original producer, authorizing role owner,
real service author, exact post/notice/recipient and immutable full payload.
Private access covers only granted addressed input and replies on its owned
outgoing threads. It does not attach to an existing listener or move `ack_seq`.

A model returns typed handoffs `{recipient,kind,text,ref,required}` within its
allowlist; necessary handoffs require `settled`. Empty handoffs require a reason.
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

`owned-ephemeral-lifecycle-observed` means unsubscribe and owned exit were seen;
`session_reclamation:not-qualified` remains separate. Retirement of those real
attempts stays held until an explicit `session_cleanup_qualification` evidence
binding exists. Journal/results/outbox/source custody remain cumulatively bounded;
this release backpressures instead of automatic compaction of held custody or
broad profile/history cleanup. Actual session/auxiliary-store reclamation and
real owner correction/delivery behavior remain unqualified frontiers.

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
