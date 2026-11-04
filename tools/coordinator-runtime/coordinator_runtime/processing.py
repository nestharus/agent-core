"""Explicit Work-issued processing of stopped software duties in their journal.

This adapter uses the existing dispatcher, pool and collector. Original grants,
enrollment intake flags, native owners, source bytes and effect holds stay put.
"""
import json
import math
from pathlib import Path
import hashlib

from .contracts import Refusal, SOL, digest, encode, ident, required_text, canonical_uuid, parse_json
from .retained import RetainedBoard

SCHEMA = """
CREATE TABLE IF NOT EXISTS processing_capabilities(
 id TEXT PRIMARY KEY,selection TEXT NOT NULL,issuer TEXT NOT NULL,created REAL NOT NULL,
 revoked REAL,starts INTEGER NOT NULL DEFAULT 0);
CREATE UNIQUE INDEX IF NOT EXISTS processing_current ON processing_capabilities((1)) WHERE revoked IS NULL;
CREATE TABLE IF NOT EXISTS processing_runs(
 controller TEXT PRIMARY KEY,capability TEXT NOT NULL,state TEXT NOT NULL,created REAL NOT NULL);
CREATE TABLE IF NOT EXISTS processing_controls(
 event TEXT PRIMARY KEY,capability TEXT NOT NULL,attempt TEXT NOT NULL,source_hash TEXT NOT NULL,
 resolution TEXT,error TEXT);
"""


def implementation():
    directory = Path(__file__).resolve().parent
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(directory.glob('*.py'))}


def basis(runtime, boards):
    return {'configuration': digest(runtime.config), 'implementation': implementation(),
            'roles': {r: {'original': b.retained_basis(runtime),
                          'future_after': b.future_frontier(),
                          'original_cursor': runtime.one('SELECT seq FROM cursors WHERE role=?', (r,))['seq']}
                      for r, b in boards.items()},
            'event_boundary': runtime.one('SELECT COALESCE(MAX(rowid),0) AS n FROM events')['n'],
            'current': runtime.rows('SELECT id,issuer,created,revoked,starts FROM processing_capabilities WHERE revoked IS NULL')}


def select(runtime, boards, selection):
    keys = {'basis', 'authority', 'expires', 'retained_events', 'recover_controls', 'future_intake', 'tasks',
            'max_starts', 'max_shared_rows', 'max_shared_payload_bytes', 'max_runtime_rows'}
    if not isinstance(selection, dict) or set(selection) != keys:
        raise Refusal('exact processing basis/authority/expiry/sources/tasks/start and residency limits required')
    issuer = boards['Work'].store.acting_session(runtime.config['software_delegation']['grantor'])
    required_text(selection['authority'], 'actual scoped Work processing delegation', 4000)
    if (type(selection['expires']) not in {int, float} or not math.isfinite(selection['expires'])
            or not runtime.clock() < selection['expires'] <= runtime.clock() + 3600):
        raise Refusal('processing selection must expire within one hour')
    for key in ('max_starts', 'max_shared_rows', 'max_shared_payload_bytes', 'max_runtime_rows'):
        if type(selection[key]) is not int or selection[key] <= 0:
            raise Refusal('positive finite processing limit required: ' + key)
    if selection['max_starts'] > 4096 or selection['max_runtime_rows'] > runtime.config['limits'].get('max_board_deliveries', runtime.config['limits']['max_events']):
        raise Refusal('processing cannot expand original logical entitlement')
    if type(selection['future_intake']) is not bool:
        raise Refusal('future intake must be an explicit boolean, separate from retained input selection')
    events = selection['retained_events']
    if not isinstance(events, list) or any(not isinstance(e, str) for e in events) or len(events) != len(set(events)):
        raise Refusal('explicit unique retained source IDs required')
    if (not isinstance(selection['tasks'], list) or not selection['tasks']
            or any(not isinstance(t, str) for t in selection['tasks'])
            or len(set(selection['tasks'])) != len(selection['tasks'])):
        raise Refusal('explicit unique unchanged task allowlist required')
    if set(selection['tasks']) - set(runtime.config['tasks']):
        raise Refusal('processing task is not in original configuration')
    for event in events:
        if not runtime.one('SELECT id FROM events WHERE id=?', (event,)):
            raise Refusal('retained processing needs an exact existing event')
    recover = selection['recover_controls']
    if not isinstance(recover, dict) or set(recover) - set(events):
        raise Refusal('control recovery must explicitly name retained event -> exact original attempt')
    for event, attempt in recover.items():
        control = runtime.one('SELECT * FROM processing_controls WHERE event=? AND attempt=?', (event, attempt))
        if not isinstance(attempt, str) or not control or runtime.attempt(attempt)['collected'] is None:
            raise Refusal('dependency: actual original control collector/return required; never relaunch it')
    current = basis(runtime, boards)
    if selection['basis'] != current:
        raise Refusal('processing source/capacity/frontier basis changed; no automatic retry')
    if len(encode(selection).encode()) > runtime.config['limits']['max_result_bytes']:
        raise Refusal('processing selection exceeds original result custody bound')
    # No cross-Board atomicity is claimed. Revalidate each exact binding before
    # committing the local selection and again at each launch/effect boundary.
    for role, b in boards.items():
        with b.opened(settlement=True) as conn:
            grant = b._original(conn, runtime)
            if grant['issued_by'] != issuer:
                raise Refusal('processing issuer differs from original software issuer')
            usage = b._usage(conn, grant)
            if any(usage[u] > selection[p] for u, p in (
                    ('shared_rows', 'max_shared_rows'), ('shared_payload_bytes', 'max_shared_payload_bytes'),
                    ('runtime_rows', 'max_runtime_rows'))):
                raise Refusal('processing residency does not fit current preserved use: ' + role)
    with runtime.tx():
        if runtime.one('SELECT id FROM processing_capabilities WHERE revoked IS NULL'):
            raise Refusal('existing processing capability remains owned; explicit revocation required')
        runtime.budget(None, len(encode(selection).encode()) + 2048)
        key = ident()
        runtime.db.execute('INSERT INTO processing_capabilities VALUES(?,?,?,?,NULL,0)',
                           (key, encode(selection), issuer, runtime.clock()))
    return {'capability': key, 'issuer': issuer, 'normal_grants': 'still revoked',
            'scope': 'selected software processing only; no native owner or acceptance transfer'}


class Access:
    def __init__(self, runtime, key):
        self.runtime, self.key = runtime, key

    def current(self):
        row = self.runtime.one('SELECT * FROM processing_capabilities WHERE id=?', (self.key,))
        if not row:
            raise Refusal('exact processing capability absent')
        selection = json.loads(row['selection'])
        if (row['revoked'] is not None or self.runtime.clock() >= selection['expires']
                or selection['basis']['configuration'] != digest(self.runtime.config)
                or selection['basis']['implementation'] != implementation()):
            raise Refusal('processing capability expired/revoked or source/configuration changed; duties retained')
        return row, selection

    def role(self, role):
        _, selection = self.current()
        return role in selection['basis']['roles']

    def event(self, event):
        _, selection = self.current()
        if event['id'] in selection['retained_events']:
            original = {e['id']: e['hash'] for r in selection['basis']['roles'].values() for e in r['original']['events']}
            if digest(event) != original.get(event['id']):
                raise Refusal('retained processing source differs from its original hash')
            return True
        if event.get('processing_capability') == self.key:
            return True  # Addressed exact delivery intent, validated by ProcessingBoard.
        if event.get('source_job'):
            job = self.runtime.job(event['source_job'])
            proof = json.loads(self.runtime.attempt(job['active_attempt'])['detail']).get('processing_capability')
            return proof == self.key
        if event.get('kind') == 'outgoing-response' and event.get('body', {}).get('job'):
            job = self.runtime.job(event['body']['job'])
            return json.loads(self.runtime.attempt(job['active_attempt'])['detail']).get('processing_capability') == self.key
        role = selection['basis']['roles'].get(event['role'])
        return bool(selection['future_intake'] and role and event.get('kind') == 'board'
                    and event.get('post', 0) > role['future_after'])

    def task(self, row):
        _, selection = self.current()
        return row['task'] in selection['tasks'] and self.event(self.runtime.event(row['event']))

    def reserve(self, attempt, event, job):
        row, selection = self.current()
        if row['starts'] >= selection['max_starts']:
            raise Refusal('finite processing start budget exhausted; original duties retained')
        if event and not self.event(self.runtime.event(event)):
            raise Refusal('input outside exact retained/future processing selection')
        if job:
            item = self.runtime.job(job)
            if item['task'] not in selection['tasks'] or any(not self.event(self.runtime.event(m['event'])) for m in json.loads(item['members'])):
                raise Refusal('frozen job outside processing selection; no old job replay')
        self.runtime.db.execute('UPDATE processing_capabilities SET starts=starts+1 WHERE id=?', (self.key,))
        return self.key

    def authorize(self, attempt):
        self.current()
        if json.loads(attempt['detail']).get('processing_capability') != self.key:
            raise Refusal('original attempt has no current processing delegation; retain its actual collector')

    def control_proof(self, event, attempt, receipt):
        row = self.runtime.attempt(attempt)
        _, selection = self.current()
        original_cap = json.loads(row['detail']).get('processing_capability')
        if original_cap != self.key and selection['recover_controls'].get(event) != attempt:
            raise Refusal('exact original control requires explicit current recovery selection, never authority rebinding')
        record = self.runtime.one('SELECT * FROM processing_controls WHERE event=?', (event,))
        result = json.loads(row['result']) if row['result'] else {}
        tools = json.loads(row['detail']).get('tool_completion', {})
        if (not record or record['attempt'] != attempt or record['capability'] != original_cap
                or record['source_hash'] != digest(self.runtime.event(event))
                or row['kind'] != 'input-control' or row['event'] != event
                or row['begin'] is None or row['ended'] is None or row['collected'] is None
                or row['exit'] != 0 or row['error'] or row['capture'] != 'complete'
                or json.loads(row['binding']) != SOL or not tools.get('complete')
                or tools.get('nonzero_completions') or tools.get('items') or result.get('semantic') != 'DONE'
                or parse_json(result.get('decision_json', 'null')) != receipt):
            raise Refusal('control disposition requires its meaningful actual worker return and original numeric END')
        canonical_uuid(row['session'])  # Actual observed worker, never the native role owner.
        required_text(result.get('summary'), 'actual control handling summary')
        return {'capability': self.key, 'original_capability': original_cap, 'attempt': attempt, 'worker': row['session'],
                'controller': row['controller'], 'actual_END': row['exit'], 'source_hash': record['source_hash'],
                'result_hash': digest(result), 'native_owner_receipt': False}


class ProcessingBoard(RetainedBoard):
    def future_frontier(self):
        with self.opened(settlement=True) as conn:
            return conn.execute('SELECT COALESCE(MAX(seq),0) FROM posts').fetchone()[0]

    def _grant(self, conn, runtime):
        _, selection = runtime.processing.current()
        grant = self._original(conn, runtime)
        expected = selection['basis']['roles'][self.role]['original']['binding']
        if self._binding(grant) != expected:
            raise Refusal('processing original grant binding changed')
        return grant

    def software_authority(self, runtime, task):
        if task not in runtime.processing.current()[1]['tasks'] or self.config['tasks'][task]['role'] != self.role:
            raise Refusal('task outside explicit processing delegation')
        return self.verify_authority(runtime)

    def receipt(self, runtime, event_id):
        if not runtime.processing.event(runtime.event(event_id)):
            raise Refusal('receipt outside selected retained/future processing source')
        return super().receipt(runtime, event_id)

    def software_delivery(self, runtime, outbox, boards):
        if outbox['kind'] not in {'alert', 'question', 'effect-request'}:
            return super().software_delivery(runtime, outbox, boards)
        receiver = boards.get(outbox['recipient'])
        if not isinstance(receiver, ProcessingBoard):
            raise Refusal('dependency: actual addressed holder must consume this control; no delegated receiver selected')
        with self.opened() as conn:
            with self.store.write(conn):
                source, target = self._delivery_grant(conn, runtime, outbox)
                receive = receiver._grant(conn, runtime)
                row = conn.execute('SELECT * FROM coordinator_deliveries_v1 WHERE id=?', (outbox['id'],)).fetchone()
                if (not row or self.identity != receiver.identity or row['grant_id'] != source['id']
                        or row['payload'] != outbox['payload'] or row['producer'] != outbox['producer']
                        or row['recipient'] != receive['owner'] or target['session'] != receive['owner']):
                    raise Refusal('control consumer needs exact addressed original source/delivery binding')
                notice = conn.execute('SELECT * FROM notification_outbox WHERE notification_id=?', (row['notice'],)).fetchone()
                if (notice['route'] != 'managed' or notice['delivery_state'] in {'sending', 'ambiguous'} or row['transport_started']
                        or self.control_receipt_status(conn, row)['pending']):
                    raise Refusal('dependency: original transport/control effect custodian must reconcile its exact uncertainty')
                prior = conn.execute('SELECT * FROM coordinator_software_deliveries_v1 WHERE delivery=?', (row['id'],)).fetchone()
                if prior:
                    if prior['source_grant'] != source['id'] or prior['receiver_grant'] != receive['id']:
                        raise Refusal('original control consumer intent differs; no replacement')
                    event = json.loads(prior['payload'])
                else:
                    event = {'id': digest({'software_delivery': row['id'], 'receiver_grant': receive['id']}),
                             'role': receiver.role, 'recipient': receive['owner'], 'kind': 'board',
                             'author': row['actor'], 'body': json.loads(outbox['payload']), 'package': None,
                             'allowed_tasks': receiver.selected['routes'], 'parent': outbox['event'],
                             'post': row['post'], 'notice': row['notice'], 'board_id': receive['board_id'],
                             'grant': receive['id'], 'processing_capability': runtime.processing.key,
                             'source_delivery': {'id': row['id'], 'source_grant': source['id'],
                                                 'receiver_grant': receive['id'], 'source_hash': digest(json.loads(outbox['payload']))}}
                    runtime.budget(None, len(encode(event).encode()) + 1024)
                    conn.execute('INSERT INTO coordinator_software_deliveries_v1 VALUES(?,?,?,?,?)',
                                 (row['id'], source['id'], receive['id'], event['id'], encode(event)))
        runtime.ingest(event)  # Exact persisted intent recovery, never a fresh business replay.
        record = runtime.one('SELECT * FROM processing_controls WHERE event=?', (event['id'],))
        if not record or not record['resolution']:
            return True
        resolution = runtime.input_resolution(event['id'])
        if (not resolution or resolution['receipt']['mode'] != 'control'
                or resolution['receipt']['remaining_obligations']):
            return True
        proof = runtime.processing.control_proof(event['id'], record['attempt'], resolution['receipt'])
        state = runtime.one('SELECT * FROM events WHERE id=?', (event['id'],))
        queue = runtime.one('SELECT * FROM queue WHERE event=?', (event['id'],))
        if state['hold'] or state['ack'] not in {'done', 'plain'} or not queue or queue['state'] != 'done':
            return True
        # This is explicit software processing, never a native owner's full-read
        # claim, acceptance or reconciliation of the original business effect.
        proof.update(software_actor=self.config['actor'], recipient=receive['owner'], source_delivery=outbox['id'])
        with self.opened() as conn:
            with self.store.write(conn):
                self._delivery_grant(conn, runtime, outbox)
                receiver._grant(conn, runtime)
                current = conn.execute('SELECT * FROM coordinator_deliveries_v1 WHERE id=?', (outbox['id'],)).fetchone()
                if self.control_receipt_status(conn, current)['pending'] or current['transport_started']:
                    raise Refusal('control changed during processing; original effect remains owned')
                conn.execute("UPDATE coordinator_deliveries_v1 SET pickup=COALESCE(pickup,?),processing=?,settlement=?,processed_at=COALESCE(processed_at,?),state='settled' WHERE id=? AND settlement IS NULL",
                             (encode(proof), encode(proof), encode(proof), runtime.clock(), outbox['id']))
        return True

    def _software_proof(self, runtime, grant, job, admission):
        return {**super()._software_proof(runtime, grant, job, admission),
                'processing_capability': runtime.processing.key}

    def _delivery_capacity(self, conn, outbox):
        runtime = self.runtime
        grant = self._grant(conn, runtime)
        policy = runtime.processing.current()[1]
        usage = self._usage(conn, grant)
        if (usage['shared_rows'] >= policy['max_shared_rows']
                or usage['shared_payload_bytes'] + len(outbox['payload'].encode()) > policy['max_shared_payload_bytes']
                or usage['runtime_rows'] >= policy['max_runtime_rows']
                or usage['runtime_payload_bytes'] + len(outbox['payload'].encode()) > self.config['limits']['max_bytes']):
            raise Refusal('processing shared residency or original logical entitlement full')

    def reconcile_delivery(self, runtime, outbox):
        # Exact original attribution, without the old frozen-sweep capability.
        from .board_delivery import BoardDelivery
        return BoardDelivery.reconcile_delivery(self, runtime, outbox)

    def automatic_control(self, runtime, outbox, **kwargs):
        raise Refusal('dependency: software control consumption required; native pointer delegation remains separate')

    def scan_after(self, runtime, grant):
        _, selection = runtime.processing.current()
        if not selection['future_intake']:
            raise Refusal('future intake was not selected')
        return max(super().scan_after(runtime, grant), selection['basis']['roles'][self.role]['future_after'])


def revoke(runtime, boards, key):
    row = runtime.one('SELECT * FROM processing_capabilities WHERE id=?', (key,))
    actor = boards['Work'].store.acting_session(runtime.config['software_delegation']['grantor'])
    if not row or row['issuer'] != actor:
        raise Refusal('only genuine original Work issuer may revoke this processing capability')
    with runtime.tx():
        runtime.db.execute('UPDATE processing_capabilities SET revoked=COALESCE(revoked,?) WHERE id=?', (runtime.clock(), key))
    return {'revoked': key, 'effects_and_collectors': 'retained; no cancellation or replay'}


def status(runtime, key):
    row = runtime.one('SELECT * FROM processing_capabilities WHERE id=?', (key,))
    if not row:
        raise Refusal('exact processing capability absent; recover current IDs through processing-basis')
    return {**row, 'selection': json.loads(row['selection']),
            'runs': runtime.rows('SELECT * FROM processing_runs WHERE capability=?', (key,)),
            'controls': runtime.rows('SELECT * FROM processing_controls WHERE capability=?', (key,)),
            'meaning': 'custody/status only; real worker return and original END required'}


from .dispatcher import Dispatcher

CONTROL_SCHEMA = {'type': 'object', 'additionalProperties': False,
                  'properties': {k: {'type': 'string'} for k in ('semantic', 'summary', 'decision_json')},
                  'required': ['semantic', 'summary', 'decision_json']}


class ProcessingDispatcher(Dispatcher):
    """The ordinary phase engine with one additional read-only control consumer."""
    def intake(self):
        if self.store.processing.current()[1]['future_intake']:
            super().intake()

    def receipts(self):
        for row in self.store.rows("SELECT id FROM events WHERE ack IN ('ready','unknown','inflight')"):
            if self.store.processing.event(self.store.event(row['id'])):
                self.receipt(row['id'])

    def reconcile_classifications(self):
        for row in self.store.rows("SELECT e.id,e.classifier FROM events e JOIN attempts a ON a.id=e.classifier WHERE e.state='classifying' AND a.collected IS NOT NULL"):
            if self.store.processing.event(self.store.event(row['id'])):
                self.reconcile_classification(row['classifier'])

    def automatic_cleanup(self):
        pass  # No cleanup authority is included in a processing capability.

    def custodian_progress(self):
        pass  # Source/effect custodians retain their original separate authority.

    def schedule_recovery(self):
        pass  # Existing failed/uncertain originals need explicit owner recovery.

    def reconcile_completed(self):
        # Preserve foreign collectors. Only this exact run's launched jobs can
        # advance here; ordinary recovery entry points remain separately owned.
        self.reconcile_classifications()
        for job in self.store.rows('SELECT * FROM jobs WHERE controller=? AND active_attempt IS NOT NULL', (self.store.controller,)):
            attempt = self.store.attempt(job['active_attempt'])
            if attempt['collected'] is not None:
                self.reconcile_collected(job)
        self.store.complete_events()

    def schedule_job(self):
        for pending in self.store.rows("SELECT q.*,t.legacy_hold FROM queue q JOIN enrollments t ON t.role=q.role WHERE q.state='queued' ORDER BY q.rowid"):
            if not self.store.processing.task(pending):
                continue
            task = self.config['tasks'][pending['task']]
            if task.get('execution') == 'owner':
                self.store.record_operational_error(pending['event'], {'dependency': 'actual selected opaque procedure holder', 'task': pending['task']}, pending['role'], 'processing-dependency')
            if pending['legacy_hold'] and task['phase'] != 'proposer':
                self.store.record_operational_error(pending['event'], {'dependency': 'supported scoped original effect-owner disposition', 'hold': pending['legacy_hold']}, pending['role'], 'processing-dependency')
        super().schedule_job()

    def schedule_classification_recovery(self):
        # Control handling is an actual worker, not classifier diagnosis/replay.
        for row in self.store.rows("SELECT e.id,e.role FROM events e LEFT JOIN queue q ON q.event=e.id WHERE e.processed_at IS NULL AND e.hold IS NULL AND (e.state='classification-held' OR q.phase='control') ORDER BY e.received,e.id"):
            if not self.store.processing.event(self.store.event(row['id'])):
                continue
            if self.store.one('SELECT event FROM processing_controls WHERE event=?', (row['id'],)):
                continue  # Failures and unknown originals never automatically replay.
            with self.store.tx():
                attempt = self.store._attempt('input-control', row['id'], None, SOL, self.config['classifier']['profile'])
                self.store.db.execute('INSERT INTO processing_controls VALUES(?,?,?,?,NULL,NULL)',
                                      (row['id'], self.store.processing.key, attempt, digest(self.store.event(row['id']))))
            self.spawn(self.control(row['id'], attempt))
            break  # One control worker admission per tick; other phases continue.

    async def control(self, event, attempt):
        original = self.store.event(event)
        prompt = ('You are the actually delegated software input/control worker at Work xhigh. Actual Work issuer, '
                  'native owner, Root and final human/Adam are outside your session. No model children, tools, '
                  'shell, native wake, effect, grant, pool or acceptance operations. Personally read the full source '
                  'and interpret its meaning within the unchanged routes. Return semantic, meaningful summary, '
                  'decision_json (a serialized input-resolution object with EXACT keys source_hash,mode,task,package,'
                  'related_event,related_job,reason,evidence,remaining_obligations). Never invent consent or processing. '
                  'mode=control processes a board control only; mode=route selects an original allowed task; '
                  'mode=coalesce needs actual same-role related_event/job proof. Evidence must cite actual supplied '
                  'source. Scope corrections go to Root, scope/blockers to Work; Reviews/QA/Branch duties stay '
                  'with actual holders. Retain every unresolved authority/effect/selected-procedure dependency in '
                  'remaining_obligations. Do not resolve an effect hold or acceptance by giving it an empty array. '
                  'Return PARTIAL with decision_json="null" when actual authority/meaning is insufficient.\n' +
                  encode({'source': original, 'source_hash': digest(original),
                          'prior': self.store.input_resolution(event),
                          'responsibility': self.store.one('SELECT * FROM queue WHERE event=?', (event,)),
                          'same_role_jobs': self.store.rows('SELECT id,task,package,state,members,effects,hold_reason,controller,active_attempt FROM jobs WHERE role=? ORDER BY created,id LIMIT 16', (original['role'],)),
                          'authority': self.store.processing.current()[1]['authority'],
                          'role_effect_hold': self.store.enrollment(original['role'])['legacy_hold']}))
        outcome = await self.run_model(attempt, prompt,
                                       {'cwd': self.config['classifier']['cwd'], 'sandbox': 'read-only', 'network': False}, CONTROL_SCHEMA)
        self.store.collect(attempt, outcome)
        try:
            apply_control(self.store, event, attempt)
        except (Refusal, ValueError, TypeError) as exc:
            with self.store.tx():
                self.store.db.execute('UPDATE processing_controls SET error=? WHERE event=?', (str(exc)[:1000], event))
            self.store.record_operational_error(event, {'dependency': str(exc), 'attempt': attempt}, original['role'], 'processing-control-dependency')


def apply_control(runtime, event, attempt):
    """Recover an exact collected disposition, never relaunch its original."""
    result = json.loads(runtime.attempt(attempt)['result'] or 'null') or {}
    receipt = parse_json(result.get('decision_json', 'null'))
    runtime.processing.control_proof(event, attempt, receipt)
    resolution = runtime.resolve_input(event, runtime.config['actor'], receipt, processing_attempt=attempt)
    with runtime.tx():
        runtime.db.execute('UPDATE processing_controls SET resolution=?,error=NULL WHERE event=?', (encode(resolution), event))
    return resolution


def release(runtime, boards, key, controller, receipt):
    row = runtime.one('SELECT * FROM processing_runs WHERE controller=? AND capability=?', (controller, key))
    cap = runtime.one('SELECT issuer FROM processing_capabilities WHERE id=?', (key,))
    actor = boards['Work'].store.acting_session(runtime.config['software_delegation']['grantor'])
    if not row or not cap or cap['issuer'] != actor:
        raise Refusal('exact original run and genuine Work issuer required')
    if (not isinstance(receipt, dict) or set(receipt) != {'actual_END', 'evidence'}
            or type(receipt['actual_END']) is not int or not isinstance(receipt['evidence'], list) or not receipt['evidence']):
        raise Refusal('actual parent-collected process END and evidence required; never infer from files/PID/exit0')
    for item in receipt['evidence']:
        required_text(item, 'original process collection evidence', 4000)
    with runtime.tx():
        if runtime.one('SELECT id FROM attempts WHERE controller=? AND collected IS NULL', (controller,)):
            raise Refusal('dependency: original collector still owns uncollected attempt; no replacement or foreign wait')
        runtime.budget(None, len(encode(receipt).encode()) + 1024)
        runtime.db.execute('UPDATE processing_runs SET state=? WHERE controller=?', (encode({'parent_END': receipt}), controller))
    return {'controller': controller, 'collection': receipt, 'processing_or_effects_complete': False}


async def run(runtime, boards, key, seconds, emit):
    import asyncio
    import signal
    runtime.processing = Access(runtime, key)
    _, selection = runtime.processing.current()
    if type(seconds) is not int or not 1 <= seconds <= 3600:
        raise Refusal('bounded processing controller seconds required')
    for board in boards.values():
        board.runtime = runtime
        board.verify_authority(runtime)
    with runtime.tx():
        if runtime.one("SELECT controller FROM processing_runs WHERE state='owned'"):
            raise Refusal('dependency: prior processing controller needs its actual original END and explicit processing-release')
        runtime.budget(None, 2048)
        runtime.db.execute('INSERT INTO processing_runs VALUES(?,?,?,?)', (runtime.controller, key, 'owned', runtime.clock()))
    emit({'controller': runtime.controller, 'capability': key, 'state': 'owned', 'actual_process_END': None})
    dispatcher = ProcessingDispatcher(runtime, boards=boards)
    loop = asyncio.get_running_loop()
    loop.add_signal_handler(signal.SIGTERM, dispatcher.stopping.set)
    loop.add_signal_handler(signal.SIGINT, dispatcher.stopping.set)
    timer = loop.call_later(min(seconds, max(0, selection['expires'] - runtime.clock())), dispatcher.stopping.set)
    try:
        await dispatcher.run(emit)  # Existing original CLI children and collectors, no shell background.
    finally:
        timer.cancel()
        emit({'controller': runtime.controller, 'state': 'returning; parent must collect this original numeric END',
              'uncollected': runtime.rows('SELECT id,controller FROM attempts WHERE controller=? AND collected IS NULL', (runtime.controller,))})
