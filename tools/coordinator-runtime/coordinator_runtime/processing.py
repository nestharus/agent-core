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
CREATE TABLE IF NOT EXISTS processing_owner_operations(
 capability TEXT NOT NULL,request_hash TEXT NOT NULL,actor TEXT NOT NULL,
 receipt TEXT NOT NULL,created REAL NOT NULL,PRIMARY KEY(capability,request_hash));
CREATE TABLE IF NOT EXISTS processing_control_returns(
 source TEXT PRIMARY KEY,response TEXT NOT NULL UNIQUE,attempt TEXT NOT NULL,
 payload TEXT NOT NULL,created REAL NOT NULL);
CREATE TABLE IF NOT EXISTS processing_admissions(
 package TEXT PRIMARY KEY,capability TEXT NOT NULL,event TEXT NOT NULL UNIQUE,
 scope TEXT NOT NULL,receipt TEXT NOT NULL,created REAL NOT NULL);
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


def owner_request(runtime, request):
    """Validate an exact proposed operation, without borrowing the owner's consent."""
    if not isinstance(request, dict) or set(request) != {'kind', 'role', 'target', 'prior', 'receipt'}:
        raise Refusal('owner request needs exact kind/role/target/prior/receipt')
    kind, role, target, receipt = (request[k] for k in ('kind', 'role', 'target', 'receipt'))
    if role not in runtime.config['roles'] or not isinstance(receipt, dict):
        raise Refusal('configured original role and structured owner receipt required')
    required_text(target, 'exact owner operation target', 128)
    if kind == 'admit-package':
        if role != 'Branch' or set(receipt) != {'admission', 'accepted'} or not receipt['admission']:
            raise Refusal('exact Branch admission and explicit accepted receipt/null required')
        if not isinstance(receipt['admission'], dict) or receipt['accepted'] is not None and not isinstance(receipt['accepted'], dict):
            raise Refusal('structured admission/acceptance receipts required')
        current = runtime.one('SELECT * FROM admissions WHERE package=?', (target,))
        if current != request['prior']:
            raise Refusal('package admission changed; no replacement or automatic retry')
        if runtime.one('SELECT id FROM jobs WHERE package=? LIMIT 1', (target,)):
            raise Refusal('existing frozen job admission cannot be replaced')
    elif kind == 'legacy-disposition':
        current = runtime.one('SELECT legacy_hold FROM enrollments WHERE role=?', (role,))
        if target != role or not current or not current['legacy_hold'] or current['legacy_hold'] != request['prior']:
            raise Refusal('exact original role effect hold changed/absent')
        if set(receipt) != {'collector', 'evidence', 'remaining_holds'}:
            raise Refusal('original collector/evidence/remaining_holds required')
        required_text(receipt['collector'], 'actual original collector', 4000)
        for key in ('evidence', 'remaining_holds'):
            if not isinstance(receipt[key], list) or len(receipt[key]) > 32 or key == 'evidence' and not receipt[key]:
                raise Refusal('bounded explicit original evidence and remaining holds required')
            for item in receipt[key]:
                required_text(item, key, 4000)
    elif kind == 'resolve-input':
        event = runtime.one('SELECT role,hash FROM events WHERE id=?', (target,))
        if not event or event['role'] != role or request['prior'] != {
                'source_hash': event['hash'], 'resolution': runtime.input_resolution(target)}:
            raise Refusal('exact owner input source/resolution changed')
    else:
        raise Refusal('unsupported scoped owner operation')
    return role


def owner_source(runtime, boards, key, role, kind, target):
    if role not in boards:
        raise Refusal('configured original owner role required')
    runtime.processing = Access(runtime, key, boards)
    runtime.processing.current()
    boards[role].verify_authority(runtime)
    if kind == 'admit-package' and role == 'Branch':
        prior = runtime.one('SELECT * FROM admissions WHERE package=?', (target,))
    elif kind == 'legacy-disposition' and target == role:
        prior = runtime.enrollment(role)['legacy_hold']
    elif kind == 'resolve-input' and runtime.event(target)['role'] == role and runtime.processing.event(runtime.event(target)):
        prior = {'source_hash': digest(runtime.event(target)), 'resolution': runtime.input_resolution(target)}
    else:
        raise Refusal('unsupported original owner source target')
    return {'kind': kind, 'role': role, 'target': target, 'prior': prior,
            'effect_jobs': runtime.rows('SELECT id,token,active_attempt,state,effects,hold_reason FROM jobs WHERE role=? ORDER BY created,id', (role,))
                           if kind == 'legacy-disposition' else [],
            'meaning': 'basis only; exact Work selection AND actual owner application required'}


def apply_owner(runtime, boards, key, request, actor):
    """Actual owner applies one Work-selected exact request; ordinary grants stay revoked."""
    runtime.processing = Access(runtime, key, boards)
    _, selection = runtime.processing.current()
    if request not in selection.get('owner_operations', []):
        raise Refusal('operation not explicitly selected by genuine Work issuer')
    role = request['role']
    if actor != runtime.config['roles'][role]['owner']:
        raise Refusal('actual original owning role required; Work selection is not owner consent')
    boards[role].verify_authority(runtime)
    with runtime.tx():
        runtime.processing.current()
        prior = runtime.one('SELECT * FROM processing_owner_operations WHERE capability=? AND request_hash=?', (key, digest(request)))
        if prior:
            return {**json.loads(prior['receipt']), 'already_recorded': True}
        owner_request(runtime, request)
        kind, target, receipt = request['kind'], request['target'], request['receipt']
        runtime.budget(None, len(encode(request).encode()) + 2048)
        if kind == 'admit-package':
            runtime.admit(target, actor, receipt['admission'], receipt['accepted'])
            result = {'kind': kind, 'package': target, 'actor': actor, 'acceptance_inferred': False}
        elif kind == 'legacy-disposition':
            # Nonempty remaining holds record useful owner disposition without
            # clearing the original hold or touching any old job/effect.
            cleared = not receipt['remaining_holds']
            if cleared and (runtime.one("SELECT id FROM jobs WHERE role=? AND effects NOT IN ('none','reconciled') LIMIT 1", (role,))
                    or runtime.one('SELECT a.id FROM attempts a JOIN jobs j ON j.id=a.job WHERE j.role=? AND (a.collected IS NULL OR a.ended IS NULL) LIMIT 1', (role,))
                    or runtime.one("SELECT p.target FROM file_publications p JOIN attempts a ON a.id=p.attempt JOIN jobs j ON j.id=a.job WHERE j.role=? AND p.state!='published' LIMIT 1", (role,))):
                raise Refusal('original local job/collector/publication effects remain unresolved; exact owner recovery required')
            runtime.db.execute('UPDATE enrollments SET legacy_hold=?,reconciliation=? WHERE role=?',
                               (None if cleared else request['prior'], encode({'actor': actor, 'capability': key,
                                'original_hold': request['prior'], **receipt}), role))
            result = {'kind': kind, 'role': role, 'actor': actor, 'hold_cleared': cleared,
                      'original_job_effects': 'unchanged; actual collector evidence remains required'}
        else:
            if not runtime.processing.event(runtime.event(target)):
                raise Refusal('owner input outside selected retained/future sources')
            resolution = runtime.resolve_input(target, actor, receipt)
            result = {'kind': kind, 'event': target, 'actor': actor, 'resolution': resolution,
                      'fresh_classification_required': True}
        runtime.db.execute('INSERT INTO processing_owner_operations VALUES(?,?,?,?,?)',
                           (key, digest(request), actor, encode(result), runtime.clock()))
        return result


def select(runtime, boards, selection):
    keys = {'basis', 'authority', 'expires', 'retained_events', 'recover_controls', 'future_intake', 'tasks',
            'max_starts', 'max_shared_rows', 'max_shared_payload_bytes', 'max_runtime_rows'}
    if not isinstance(selection, dict) or set(selection) - {'owner_operations', 'control_recognitions', 'software_admission'} != keys:
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
    operations = selection.get('owner_operations', [])
    if not isinstance(operations, list) or len(operations) > 32:
        raise Refusal('bounded exact owner operations required')
    for request in operations:
        owner_request(runtime, request)
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
    recognitions = selection.get('control_recognitions', {})
    if not isinstance(recognitions, dict) or set(recognitions) - set(recover):
        raise Refusal('legacy control recognition requires an exact selected recovery event/attempt')
    for event, recognition in recognitions.items():
        validate_recognition(runtime, event, recover[event], recognition)
    from . import processing_admission
    processing_admission.validate(runtime, selection)
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
    def __init__(self, runtime, key, boards=None):
        self.runtime, self.key, self.boards = runtime, key, boards

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
            board = (self.boards or {}).get(event['role']) or ProcessingBoard(self.runtime.config, event['role'])
            return board.receiving_intent(self.runtime, event)
        if event.get('processing_control_return'):
            returned = self.runtime.one('SELECT * FROM processing_control_returns WHERE response=?', (event['id'],))
            if not returned or json.loads(returned['payload']) != event:
                raise Refusal('control response needs its exact persisted original return')
            control = self.runtime.one('SELECT * FROM processing_controls WHERE event=?', (returned['source'],))
            if not control or control['attempt'] != returned['attempt']:
                raise Refusal('original control response binding changed')
            return control['capability'] == self.key or selection['recover_controls'].get(returned['source']) == returned['attempt']
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
        from .processing_admission import permits
        return row['task'] in selection['tasks'] and self.event(self.runtime.event(row['event'])) and permits(self.runtime, row)

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
                or tools.get('nonzero_completions') or tools.get('items') or tools.get('unknown_types')
                or parse_json(result.get('decision_json', 'null')) != receipt):
            raise Refusal('control disposition requires its meaningful actual worker return and original numeric END')
        validate_control_result(result, receipt)
        recognition = selection.get('control_recognitions', {}).get(event)
        if result['semantic'] != 'DONE':
            if not recognition:
                raise Refusal('legacy free-text semantic needs exact genuine Work recognition; original result is unchanged')
            validate_recognition(self.runtime, event, attempt, recognition)
        canonical_uuid(row['session'])  # Actual observed worker, never the native role owner.
        required_text(result.get('summary'), 'actual control handling summary')
        return {'capability': self.key, 'original_capability': original_cap, 'attempt': attempt, 'worker': row['session'],
                'controller': row['controller'], 'actual_END': row['exit'], 'source_hash': record['source_hash'],
                'result_hash': digest(result), 'native_owner_receipt': False,
                'legacy_semantic_recognition': recognition}


class ProcessingBoard(RetainedBoard):
    def receiving_intent(self, runtime, event):
        """A marker alone grants nothing: require the exact durable delivery intent."""
        delivery = event.get('source_delivery', {})
        with self.opened(settlement=True) as conn:
            receiver = self._grant(conn, runtime)
            intent = conn.execute('SELECT * FROM coordinator_software_deliveries_v1 WHERE delivery=?',
                                  (delivery.get('id'),)).fetchone()
            row = conn.execute('SELECT * FROM coordinator_deliveries_v1 WHERE id=?', (delivery.get('id'),)).fetchone()
            outbox = runtime.one('SELECT * FROM outboxes WHERE id=?', (delivery.get('id'),))
            if (not intent or not row or not outbox or json.loads(intent['payload']) != event
                    or intent['event'] != event['id'] or intent['receiver_grant'] != receiver['id']
                    or intent['source_grant'] != row['grant_id']
                    or delivery.get('source_grant') != row['grant_id']
                    or delivery.get('receiver_grant') != receiver['id']
                    or delivery.get('source_hash') != digest(json.loads(outbox['payload']))
                    or row['payload'] != outbox['payload'] or row['producer'] != outbox['producer']
                    or row['actor'] != self.config['actor'] or row['recipient'] != receiver['owner']
                    or event['recipient'] != receiver['owner'] or outbox['recipient'] != self.role):
                raise Refusal('processing receiver requires its exact persisted source/delivery/grant intent')
            source_role = outbox['role']
            expected = runtime.processing.current()[1]['basis']['roles'].get(source_role, {}).get('original', {}).get('binding', {})
            if row['grant_id'] != expected.get('id'):
                raise Refusal('delivery source grant outside processing binding')
            source_board = (runtime.processing.boards or {}).get(source_role) or ProcessingBoard(self.config, source_role)
            if source_board.identity != self.identity or source_board._grant(conn, runtime)['id'] != row['grant_id']:
                raise Refusal('original source/receiving board or grant binding changed')
            notice = conn.execute('SELECT * FROM notification_outbox WHERE notification_id=?', (row['notice'],)).fetchone()
            if (not notice or notice['route'] != 'managed' or notice['delivery_state'] in {'sending', 'ambiguous'}
                    or row['transport_started'] or self.control_receipt_status(conn, row)['pending']):
                raise Refusal('original transport/control uncertainty remains with its custodian')
            if outbox['kind'] in {'work', 'result'}:
                job = runtime.job(outbox['job'])
                attempt = runtime.attempt(job['active_attempt'])
                if json.loads(attempt['detail']).get('processing_capability') != runtime.processing.key:
                    raise Refusal('handoff source is not this processing capability')
            elif outbox['kind'] not in {'alert', 'question', 'effect-request'}:
                raise Refusal('unsupported processing delivery kind')
        return True

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
            'control_returns': runtime.rows('SELECT r.* FROM processing_control_returns r JOIN processing_controls c ON c.event=r.source WHERE c.capability=?', (key,)),
            'software_admissions': runtime.rows('SELECT * FROM processing_admissions WHERE capability=?', (key,)),
            'owner_operations': runtime.rows('SELECT * FROM processing_owner_operations WHERE capability=?', (key,)),
            'meaning': 'custody/status only; real worker return and original END required'}


from .dispatcher import Dispatcher

CONTROL_SCHEMA = {'type': 'object', 'additionalProperties': False,
                  'properties': {'semantic': {'type': 'string', 'enum': ['DONE', 'PARTIAL', 'FAILED', 'UNKNOWN']},
                                 'summary': {'type': 'string'}, 'decision_json': {'type': 'string'}},
                  'required': ['semantic', 'summary', 'decision_json']}


def validate_control_result(result, receipt):
    if not isinstance(result, dict) or set(result) != {'semantic', 'summary', 'decision_json'}:
        raise Refusal('complete actual control return required')
    semantic = required_text(result['semantic'], 'actual control semantic', 16000)
    if semantic.strip().upper() in {'PARTIAL', 'FAILED', 'UNKNOWN'} or not isinstance(receipt, dict):
        raise Refusal('incomplete original control cannot become processing or be replayed')
    required_text(result['summary'], 'actual control handling summary')


def validate_recognition(runtime, event, attempt, recognition):
    """Work can interpret an old free-text status without rewriting its return.

    This is scoped software meaning, never native consent or old-effect release.
    Actual process/capture/source checks still run in control_proof.
    """
    if not isinstance(recognition, dict) or set(recognition) != {'attempt', 'result_hash', 'reason', 'evidence'}:
        raise Refusal('exact legacy attempt/result hash and genuine Work reason/evidence required')
    row = runtime.attempt(attempt)
    result = parse_json(row['result'] or 'null')
    if (recognition['attempt'] != attempt or row['event'] != event
            or recognition['result_hash'] != digest(result) or not isinstance(result, dict)):
        raise Refusal('legacy control recognition differs from the immutable collected result')
    validate_control_result(result, parse_json(result.get('decision_json', 'null')))
    required_text(recognition['reason'], 'genuine Work interpretation of original control', 4000)
    if not isinstance(recognition['evidence'], list) or not 1 <= len(recognition['evidence']) <= 16:
        raise Refusal('bounded original-return recognition evidence required')
    for evidence in recognition['evidence']:
        required_text(evidence, 'actual Work recognition evidence', 4000)


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

    def schedule_classifications(self):
        from .processing_admission import admit_pending
        admit_pending(self.store)
        super().schedule_classifications()

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
            source = self.store.one('SELECT state,classifier FROM events WHERE id=?', (row['id'],))
            if source['state'] not in {'queued', 'classification-held'} or (source['classifier']
                    and self.store.attempt(source['classifier'])['collected'] is None):
                continue  # The actual original classifier still owns its result.
            with self.store.tx():
                if not self.store._classification_available():
                    return  # Controls share the existing concurrent non-job worker ceiling.
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
                  'and interpret its meaning within the unchanged routes. semantic MUST be exactly DONE, PARTIAL, '
                  'FAILED or UNKNOWN. DONE means this bounded input interpretation is complete, not that native '
                  'QA read, external effects, downstream processing or acceptance occurred. Put the actual meaning '
                  'in summary and decision_json.reason, never in semantic. Return semantic, meaningful summary, '
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
    with runtime.tx():
        resolution = runtime.resolve_input(event, runtime.config['actor'], receipt, processing_attempt=attempt)
        control_return(runtime, event, attempt, result, resolution)
        runtime.db.execute('UPDATE processing_controls SET resolution=?,error=NULL WHERE event=?', (encode(resolution), event))
    return resolution


def control_return(runtime, event, attempt, result, resolution):
    """A durable, freshly classified Work consumer precedes source completion.

    One return per original, including dependency/hold interpretations. The
    original result and resolution are transported whole, with no source replay.
    """
    previous = runtime.one('SELECT * FROM processing_control_returns WHERE source=?', (event,))
    if previous:
        if previous['attempt'] != attempt:
            raise Refusal('control return already has a different original collector')
        return previous['response']
    _, selection = runtime.processing.current()
    routes = [name for name in selection['tasks'] if runtime.config['tasks'][name]['role'] == 'Work'
              and runtime.config['tasks'][name]['phase'] == 'proposer'
              and runtime.config['tasks'][name]['effects'] == 'none']
    if not routes:
        raise Refusal('meaningful control return needs a selected read-only Work proposer consumer')
    response = {'id': digest({'processing_control_return': event, 'attempt': attempt}),
                'kind': 'response', 'role': 'Work', 'recipient': runtime.enrollment('Work')['owner'],
                'author': runtime.attempt(attempt)['session'], 'parent': event, 'package': None,
                'notice': None, 'board_id': None, 'grant': None, 'allowed_tasks': routes,
                'processing_control_return': {'source': event, 'attempt': attempt},
                'body': {'source': runtime.event(event), 'actual_worker_return': result,
                         'software_resolution': resolution, 'native_owner_receipt': False}}
    runtime.budget('events', len(encode(response).encode()) + 1024)
    runtime.db.execute('INSERT INTO processing_control_returns VALUES(?,?,?,?,?)',
                       (event, response['id'], attempt, encode(response), runtime.clock()))
    runtime.db.execute('INSERT INTO events(id,role,payload,hash,received,parent) VALUES(?,?,?,?,?,?)',
                       (response['id'], 'Work', encode(response), digest(response), runtime.clock(), event))
    return response['id']


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
    runtime.processing = Access(runtime, key, boards)
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
