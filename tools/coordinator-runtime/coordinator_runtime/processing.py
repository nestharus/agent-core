"""Explicit Work-issued processing of stopped software duties in their journal.

This adapter uses the existing dispatcher, pool and collector. Original grants,
enrollment intake flags, native owners, source bytes and effect holds stay put.
"""
from . import observations

import json
from contextlib import nullcontext
import math
from pathlib import Path
import hashlib

from .contracts import Refusal, SOL, digest, encode, ident, required_text, canonical_uuid, parse_json
from .retained import RetainedBoard
from . import configuration

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
CREATE TABLE IF NOT EXISTS processing_admission_resolutions(
 package TEXT PRIMARY KEY,capability TEXT NOT NULL,event TEXT NOT NULL,topic TEXT NOT NULL,
 scope_hash TEXT NOT NULL,admission_hash TEXT NOT NULL,source_hash TEXT NOT NULL);
CREATE TRIGGER IF NOT EXISTS processing_resolution_no_update BEFORE UPDATE ON processing_admission_resolutions
 BEGIN SELECT RAISE(ABORT,'immutable applied software admission'); END;
CREATE TRIGGER IF NOT EXISTS processing_resolution_no_delete BEFORE DELETE ON processing_admission_resolutions
 BEGIN SELECT RAISE(ABORT,'immutable applied software admission'); END;
CREATE TABLE IF NOT EXISTS processing_delivery_links(
 delivery TEXT PRIMARY KEY,event TEXT NOT NULL REFERENCES events(id));
CREATE TABLE IF NOT EXISTS processing_source_positions(
 position INTEGER PRIMARY KEY AUTOINCREMENT,event TEXT NOT NULL UNIQUE);
"""


def migrate_links(runtime):
    """Preserve every existing link while admitting many outboxes per consumer."""
    definition = runtime.one("SELECT sql FROM sqlite_master WHERE name='processing_delivery_links'")['sql']
    if 'NOT NULL UNIQUE' not in definition.upper():
        return
    with runtime.tx():
        runtime.db.execute('ALTER TABLE processing_delivery_links RENAME TO processing_delivery_links_original')
        runtime.db.execute('CREATE TABLE processing_delivery_links(delivery TEXT PRIMARY KEY,event TEXT NOT NULL REFERENCES events(id))')
        runtime.db.execute('INSERT INTO processing_delivery_links SELECT * FROM processing_delivery_links_original')
        runtime.db.execute('DROP TABLE processing_delivery_links_original')


@observations.observe('source-implementation')
def implementation():
    directory = Path(__file__).resolve().parent
    files = sorted(directory.glob('*.py'))
    observations.count('source-files', len(files))
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in files}


def basis(runtime, boards, *, future_only=False, selected_retained=None):
    from . import windows
    narrow = selected_retained is not None
    if future_only and narrow:
        raise Refusal('future-only and selected retained source authority are distinct')
    if narrow:
        from .selected_source import operands
        operands(runtime, selected_retained)
        boards['Work'].store.acting_session(runtime.config['software_delegation']['grantor'])
    if (future_only or narrow) and not runtime.db.in_transaction:
        with runtime.tx():
            return basis(runtime, boards, future_only=future_only, selected_retained=selected_retained)
    version = configuration.version_metadata(runtime)
    return {'configuration': digest(runtime.config), 'implementation': implementation(),
            **({'mode':'selected-retained-source-v1', 'selected_retained':selected_retained,
                'journal_revision':windows.revision(runtime),
                'allocation':windows.basis(runtime) if runtime.config.get('window_service') else None} if narrow else {}),
            **({'configuration_transition': {**{k: version[k] for k in ('position', 'previous', 'current', 'original', 'issuer')},
                                             'source_selection': version.get('source_selection', 0)}} if version else {}),
            **({'future_only': True, 'journal_revision': windows.revision(runtime),
                'allocation': windows.basis(runtime) if runtime.config.get('window_service') else None} if future_only else {}),
            'roles': {r: {'original': (b.selected_basis(runtime, selected_retained) if narrow else
                                       b.prospective_basis(runtime) if future_only else b.retained_basis(runtime)),
                          'future_after': b.future_frontier(),
                          'original_cursor': runtime.one('SELECT seq FROM cursors WHERE role=?', (r,))['seq']}
                      for r, b in boards.items()},
            'event_boundary': source_boundary(runtime),
            'current': runtime.rows('SELECT id,issuer,created,revoked,starts FROM processing_capabilities WHERE revoked IS NULL')}


def source_boundary(runtime):
    rows = runtime.one('SELECT COALESCE(MAX(rowid),0) AS n FROM events')['n']
    sequence = runtime.one("SELECT seq FROM sqlite_sequence WHERE name='processing_source_positions'")
    return max(rows, sequence['seq'] if sequence else 0)


def note_source(runtime, event):
    # Record logical birth for a newly inserted event, including internal
    # responses, in its existing write transaction. This counter survives row
    # recycling; it is never renewed/reset to make an old input prospective.
    runtime.db.execute('INSERT INTO processing_source_positions(position,event) VALUES(?,?)',
                       (source_boundary(runtime) + 1, event))


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
        # ProcessingBoard already verifies actual retained owner authority.
        # Source inspection must not require reopening revoked intake.
        enrollment = runtime.one('SELECT legacy_hold FROM enrollments WHERE role=?', (role,))
        if not enrollment or not enrollment['legacy_hold']:
            raise Refusal('original retained resource hold required')
        prior = enrollment['legacy_hold']
    elif kind == 'resolve-input' and runtime.event(target)['role'] == role and runtime.processing.event(runtime.event(target)):
        prior = {'source_hash': digest(runtime.event(target)), 'resolution': runtime.input_resolution(target)}
    else:
        raise Refusal('unsupported original owner source target')
    return {'kind': kind, 'role': role, 'target': target, 'prior': prior,
            'effect_jobs': runtime.rows('SELECT id,token,active_attempt,state,effects,hold_reason FROM jobs WHERE role=? ORDER BY created,id', (role,))
                           if kind == 'legacy-disposition' else [],
            'local_resource_disposition': local_disposition(runtime, role) if kind == 'legacy-disposition' else None,
            'meaning': 'basis only; exact Work selection AND actual owner application required'}


def local_disposition(runtime, role):
    """All local role obligations, distinct from external historical custody.

    This supplies procedure preconditions, never an automatic receipt or consent.
    Classifier/ACK/control attempts linked to role events count too.
    """
    return {
        'effect_jobs': runtime.rows("SELECT id,effects,hold_reason FROM jobs WHERE role=? AND effects NOT IN ('none','reconciled') ORDER BY id", (role,)),
        'uncollected_originals': runtime.rows('SELECT a.id,a.controller,a.ended,a.collected,a.exit FROM attempts a '
            'LEFT JOIN jobs j ON j.id=a.job LEFT JOIN events e ON e.id=a.event '
            'WHERE (j.role=? OR e.role=?) AND (a.collected IS NULL OR a.ended IS NULL OR a.exit IS NULL) ORDER BY a.id', (role, role)),
        'publication_intents': runtime.rows("SELECT p.attempt,p.target,p.state FROM file_publications p JOIN attempts a ON a.id=p.attempt JOIN jobs j ON j.id=a.job WHERE j.role=? AND p.state!='published' ORDER BY p.attempt,p.target", (role,)),
        'ordinary_intents': runtime.rows("SELECT o.attempt,o.state FROM ordinary_runs o JOIN attempts a ON a.id=o.attempt JOIN jobs j ON j.id=a.job WHERE j.role=? AND o.state!='reconciled' ORDER BY o.attempt", (role,)),
        'resource_leases': runtime.rows('SELECT r.resource,r.attempt FROM ordinary_resources r JOIN attempts a ON a.id=r.attempt JOIN jobs j ON j.id=a.job WHERE j.role=? ORDER BY r.resource', (role,))}


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
            if cleared and any(local_disposition(runtime, role).values()):
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


def map_input(runtime, boards, key, event, actor, receipt):
    """Current selected receiver mapping without rotating an unrelated service epoch.

    This is original-owner routing, never a grant to the software actor or a
    replacement for admission, ordinary execution or upstream collection.
    """
    runtime.processing = Access(runtime, key, boards)
    _, selection = runtime.processing.current()
    state = runtime.one('SELECT role,hold FROM events WHERE id=?', (event,))
    if not state or state['hold']:
        raise Refusal('unheld original receiving input required before mapping acquisition')
    task = receipt.get('task') if isinstance(receipt, dict) else None
    if (task not in selection.get('input_mappings', []) or task not in selection['tasks']
            or actor != runtime.config['roles'][state['role']]['owner']
            or not isinstance(receipt, dict) or receipt.get('mode') != 'route' or 'integration' not in receipt):
        raise Refusal('explicit current Work-selected mapping task and actual receiving owner required')
    boards[state['role']].verify_authority(runtime)
    if not runtime.processing.event(runtime.event(event)):
        raise Refusal('mapping source outside original selected retained/future boundary')
    return runtime.resolve_input(event, actor, receipt)


def select(runtime, boards, selection):
    keys = {'basis', 'authority', 'expires', 'retained_events', 'recover_controls', 'future_intake', 'tasks',
            'max_starts', 'max_shared_rows', 'max_shared_payload_bytes', 'max_runtime_rows'}
    continuing = isinstance(selection, dict) and 'service' in selection
    if continuing:
        keys = keys - {'expires', 'max_starts'}
    if not isinstance(selection, dict) or set(selection) - {'owner_operations', 'control_recognitions', 'software_admission', 'work_coordination', 'service', 'input_mappings', 'metadata_lookup'} != keys:
        raise Refusal('exact processing basis/authority/expiry/sources/tasks/start and residency limits required')
    issuer = boards['Work'].store.acting_session(runtime.config['software_delegation']['grantor'])
    required_text(selection['authority'], 'actual scoped Work processing delegation', 4000)
    if not continuing and (type(selection['expires']) not in {int, float} or not math.isfinite(selection['expires'])
            or not runtime.clock() < selection['expires'] <= runtime.clock() + 3600):
        raise Refusal('processing selection must expire within one hour')
    for key in (('max_starts',) if not continuing else ()) + ('max_shared_rows', 'max_shared_payload_bytes', 'max_runtime_rows'):
        if type(selection[key]) is not int or selection[key] <= 0:
            raise Refusal('positive finite processing limit required: ' + key)
    if (not continuing and selection['max_starts'] > 4096) or selection['max_runtime_rows'] > runtime.config['limits'].get('max_board_deliveries', runtime.config['limits']['max_events']):
        raise Refusal('processing cannot expand original logical entitlement')
    if type(selection['future_intake']) is not bool:
        raise Refusal('future intake must be an explicit boolean, separate from retained input selection')
    future_only = selection['basis'].get('future_only', False)
    if 'future_only' in selection['basis'] and future_only is not True:
        raise Refusal('future-only basis must be explicitly true')
    if future_only and (not continuing or not selection['future_intake'] or selection['retained_events']
                        or selection['recover_controls'] or selection.get('control_recognitions')
                        or any(r.get('kind') != 'admit-package' for r in selection.get('owner_operations', []))):
        raise Refusal('metadata-only future basis cannot authorize retained history, recovery or finite processing')
    from .selected_source import MODE, operands
    narrow = selection['basis'].get('mode') == MODE
    pins = selection['basis'].get('selected_retained') if narrow else None
    if narrow:
        operands(runtime, pins)
        if (not continuing or not selection['future_intake'] or selection['recover_controls']
                or selection.get('control_recognitions') or selection.get('owner_operations')
                or selection['retained_events'] != [p['event'] for p in pins]
                or any(p['task'] not in selection['tasks'] for p in pins)):
            raise Refusal('selected metadata basis authorizes only exact queued originals plus future intake; no recovery/owner effects')
    events = selection['retained_events']
    if not isinstance(events, list) or any(not isinstance(e, str) for e in events) or len(events) != len(set(events)):
        raise Refusal('explicit unique retained source IDs required')
    if (not isinstance(selection['tasks'], list) or not selection['tasks']
            or any(not isinstance(t, str) for t in selection['tasks'])
            or len(set(selection['tasks'])) != len(selection['tasks'])):
        raise Refusal('explicit unique unchanged task allowlist required')
    if set(selection['tasks']) - set(runtime.config['tasks']):
        raise Refusal('processing task is not in original configuration')
    mappings = selection.get('input_mappings', [])
    from .local_integration import selected as local_task
    if (not isinstance(mappings, list) or not all(isinstance(t, str) for t in mappings)
            or len(mappings) != len(set(mappings)) or set(mappings) - set(selection['tasks'])
            or any(not local_task(runtime, t) for t in mappings)):
        raise Refusal('input mappings select only exact already permitted local receiver tasks')
    configuration.validate_processing(runtime, selection)
    from .metadata_lookup import validate_selection
    validate_selection(runtime, selection)
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
    processing_admission.validate_coordination(runtime, selection)
    processing_admission.validate(runtime, selection)
    if continuing:
        from .service import validate
        validate(runtime, selection)
    current = basis(runtime, boards, future_only=future_only, selected_retained=pins)
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
            usage = b._selected_usage(conn, grant) if narrow else b._usage(conn, grant)
            limits = [('shared_rows', 'max_shared_rows'), ('runtime_rows', 'max_runtime_rows')]
            if not narrow:
                limits.append(('shared_payload_bytes', 'max_shared_payload_bytes'))
            if any(usage[u] > selection[p] for u, p in limits):
                raise Refusal('processing residency does not fit current preserved use: ' + role)
    with runtime.tx():
        if runtime.one('SELECT id FROM processing_capabilities WHERE revoked IS NULL'):
            raise Refusal('existing processing capability remains owned; explicit revocation required')
        if continuing:
            from . import windows
            windows.validate_delegation(runtime, selection)
        if (future_only or narrow) and basis(runtime, boards, future_only=future_only, selected_retained=pins) != selection['basis']:
            raise Refusal('future-only processing basis changed before local selection; no automatic replay')
        if narrow:
            from .selected_source import custody_budget
            custody_budget(runtime, len(encode(selection).encode()) + 2048)
        else:
            runtime.budget(None, len(encode(selection).encode()) + 2048)
        key = ident()
        runtime.db.execute('INSERT INTO processing_capabilities VALUES(?,?,?,?,NULL,0)',
                           (key, encode(selection), issuer, runtime.clock()))
    return {'capability': key, 'issuer': issuer, 'normal_grants': 'still revoked',
            'scope': 'selected software processing only; no native owner or acceptance transfer'}


class Access:
    def __init__(self, runtime, key, boards=None):
        self.runtime, self.key, self.boards = runtime, key, boards

    @observations.observe('current')
    def current(self):
        configuration.assert_current(self.runtime)
        configuration.assert_release(self.runtime)
        row = self.runtime.one('SELECT * FROM processing_capabilities WHERE id=?', (self.key,))
        if not row:
            raise Refusal('exact processing capability absent')
        selection = json.loads(row['selection'])
        from .report_repair import pins
        current_implementation = implementation()
        if (row['revoked'] is not None or ('service' not in selection and self.runtime.clock() >= selection['expires'])
                or selection['basis']['configuration'] != digest(self.runtime.config)
                or (selection['basis']['implementation'] != current_implementation
                    and not pins(self.runtime, self.key, selection, current_implementation))):
            raise Refusal('processing capability expired/revoked or source/configuration changed; duties retained')
        from .report_repair import lease_selection
        return row, lease_selection(self.runtime, self.key, selection)

    def role(self, role):
        _, selection = self.current()
        return role in selection['basis']['roles']

    def review_task(self, name):
        return name in self.current()[1].get('service', {}).get('reviews', {})

    def owed_control(self, event):
        """Authenticate the receiving intent, never trust a message exemption flag.

        This only separates already-owned internal control progress from new
        upstream admission. Store still charges the event and enforces capacity.
        """
        self.current()
        if event.get('processing_capability') != self.key:
            return False
        board = (self.boards or {}).get(event['role']) or ProcessingBoard(self.runtime.config, event['role'])
        board.receiving_intent(self.runtime, event)
        source = self.runtime.one('SELECT kind FROM outboxes WHERE id=?', (event['source_delivery']['id'],))
        return source['kind'] in {'alert', 'question', 'effect-request'}

    def event(self, event):
        _, selection = self.current()
        if not configuration.event_allowed(self.runtime, event):
            return False
        if event['id'] in selection['retained_events']:
            from .selected_source import selected_pins
            pins = {p['event']:p for p in selected_pins(selection)}
            if event['id'] in pins:
                pin = pins[event['id']]
                position = self.runtime.one('SELECT position FROM processing_source_positions WHERE event=?', (event['id'],))
                if not position or position['position'] != pin['source_birth'] or event['role'] != pin['role']:
                    raise Refusal('selected retained original role/birth changed; no source renewal')
            original = {e['id']: e['hash'] for r in selection['basis']['roles'].values() for e in r['original']['events']}
            if digest(event) != original.get(event['id']):
                raise Refusal('retained processing source differs from its original hash')
            return True
        if event.get('processing_report') == self.key:
            tasks = selection.get('service', {}).get('report_tasks', [])
            original = event.get('body', {}).get('original', {})
            return (event.get('author') == self.current()[0]['issuer']
                    and original.get('collector') == event.get('author')
                    and event.get('role') == 'Reviews' and event.get('kind') == 'response'
                    and len(event.get('allowed_tasks', [])) == 1 and event['allowed_tasks'][0] in tasks
                    and event['id'] == digest({'attributed_report': {'collector': event.get('author'),
                                              'reference': original.get('reference')}}))
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
        configured = self.runtime.config['tasks'].get(row['task'], {})
        if (configured.get('role') == 'Reviews' and configured.get('phase') == 'integrator'
                and 'native_review_return' in selection.get('service', {}).get('legacy_resources', {}).get('Reviews', {})):
            from .resource_scopes import blocked
            # Scheduler and reservation consult task() before their legacy-hold
            # guards. Fence physical admission ahead of this first event read.
            with (nullcontext() if self.runtime.db.in_transaction else self.runtime.tx()):
                native_row = {**row, 'role': configured['role'], 'phase': configured['phase']}
                if 'package' not in native_row:
                    metadata = self.runtime.one("SELECT json_extract(payload,'$.package') AS package FROM events WHERE id=?", (row['event'],))
                    native_row['package'] = metadata['package'] if metadata else None
                # A frozen queue member keeps the actual job's resource identity;
                # its queue UUID must not make its own staging a foreign lease.
                frozen = self.runtime.one("SELECT j.id,j.active_attempt FROM queue q JOIN jobs j ON j.id=q.job "
                    "WHERE q.event=? AND q.task=? AND q.state='reserved'", (row['event'], row['task']))
                if frozen:
                    native_row.update(frozen)
                if blocked(self.runtime, native_row):
                    return False
                return row['task'] in selection['tasks'] and self.event(self.runtime.event(row['event'])) and permits(self.runtime, row)
        return row['task'] in selection['tasks'] and self.event(self.runtime.event(row['event'])) and permits(self.runtime, row)

    def retirement_event(self, event):
        """Authenticate conserved receiving evidence only for retired local work.

        A conserved envelope is evidence, never a replacement current grant or
        permission to dispatch/repost an input whose shared rows have retired.
        """
        self.current()
        if not configuration.event_allowed(self.runtime, event):
            return False
        if event.get('processing_capability') != self.key:
            return self.event(event)
        row = self.runtime.one('SELECT state FROM events WHERE id=?', (event['id'],))
        if not row or row['state'] != 'retired':
            raise Refusal('conserved receiving evidence is only for retired local source material')
        board = (self.boards or {}).get(event['role']) or ProcessingBoard(self.runtime.config, event['role'])
        return board.receiving_intent(self.runtime, event, conserved=True)

    def reserve(self, attempt, event, job):
        row, selection = self.current()
        from .report_repair import lease_record
        amendment = lease_record(self.runtime, self.key)
        if amendment and row['starts'] >= amendment['plan']['max_starts']:
            raise Refusal('owner lease total start ceiling exhausted; no refund')
        if 'service' in selection:
            active = self.runtime.one("SELECT COUNT(*) AS n FROM attempts WHERE collected IS NULL AND controller=?", (self.runtime.controller,))['n']
            if active > selection['service']['max_inflight']:
                raise Refusal('continuing service inflight capacity held; no original displaced')
        elif row['starts'] >= selection['max_starts']:
            raise Refusal('finite processing start budget exhausted; original duties retained')
        if event and not self.event(self.runtime.event(event)):
            raise Refusal('input outside exact retained/future processing selection')
        if job:
            item = self.runtime.job(job)
            from .native_review_scope import admit
            admit(self.runtime, item)
            if item['task'] not in selection['tasks'] or any(not self.event(self.runtime.event(m['event'])) for m in json.loads(item['members'])):
                raise Refusal('frozen job outside processing selection; no old job replay')
        self.runtime.db.execute('UPDATE processing_capabilities SET starts=starts+1 WHERE id=?', (self.key,))
        return self.key

    def authorize(self, attempt):
        self.current()
        if json.loads(attempt['detail']).get('processing_capability') != self.key:
            raise Refusal('original attempt has no current processing delegation; retain its actual collector')

    def control_proof(self, event, attempt, receipt):
        _, selection = self.current()
        state = self.runtime.one('SELECT hold,hash FROM events WHERE id=?', (event,))
        if not state or state['hold']:
            raise Refusal('control disposition requires its exact unheld current source')
        row = self.runtime.attempt(attempt)
        original_cap = json.loads(row['detail']).get('processing_capability')
        if original_cap != self.key and selection['recover_controls'].get(event) != attempt:
            raise Refusal('exact original control requires explicit current recovery selection, never authority rebinding')
        record = self.runtime.one('SELECT * FROM processing_controls WHERE event=?', (event,))
        result = json.loads(row['result']) if row['result'] else {}
        tools = json.loads(row['detail']).get('tool_completion', {})
        if (not record or record['attempt'] != attempt or record['capability'] != original_cap
                or record['source_hash'] != state['hash']
                or row['kind'] != 'input-control' or row['event'] != event
                or row['begin'] is None or row['ended'] is None or row['collected'] is None
                or row['exit'] != 0 or row['error'] or row['capture'] != 'complete'
                or json.loads(row['binding']) != SOL or tools.get('complete') is not True
                or any(tools.get(k) != [] for k in ('nonzero_completions','items','unknown_types'))):
            raise Refusal('control disposition requires its meaningful actual worker return and original numeric END')
        validate_control_result(result, receipt)
        recognition = selection.get('control_recognitions', {}).get(event)
        if result['semantic'] != 'DONE':
            if not recognition:
                raise Refusal('legacy free-text semantic needs exact genuine Work recognition; original result is unchanged')
            validate_recognition(self.runtime, event, attempt, recognition)
        canonical_uuid(row['session'])  # Actual observed worker, never the native role owner.
        required_text(result.get('summary'), 'actual control handling summary')
        self.current()
        source = self.runtime.event(event)
        if digest(source) != state['hash'] or not self.event(source):
            raise Refusal('control disposition outside exact current source selection')
        original = parse_json(result.get('decision_json', 'null'))
        derived, derivation = control_receipt(self.runtime, event, row, result, original)
        if receipt != original and receipt != derived:
            raise Refusal('control receipt differs from its original or exact software syntax derivation')
        return {'capability': self.key, 'original_capability': original_cap, 'attempt': attempt, 'worker': row['session'],
                'controller': row['controller'], 'actual_END': row['exit'], 'source_hash': record['source_hash'],
                'result_hash': digest(result), 'native_owner_receipt': False,
                'legacy_semantic_recognition': recognition,
                **({'applier_controller': self.runtime.controller} if derivation and row['controller'] != self.runtime.controller else {}),
                **({'syntax_derivation': derivation} if derivation and receipt == derived else {})}


class ProcessingBoard(RetainedBoard):
    def historical_authority(self, runtime, task=None):
        """Original software journal binding, without execution current().

        Only the existing trusted-account Board identity model is claimed.
        This grants no access without current owner scope/source visibility.
        """
        with self.opened(settlement=True) as conn:
            grant = self._original(conn, runtime)
            policy = conn.execute('SELECT configuration,json_extract(policies,?) AS task_hash '
                'FROM coordinator_software_grants_v1 WHERE grant_id=?',
                ('$.'+json.dumps(task) if task else '$.__no_task__',grant['id'])).fetchone()
            if not policy:
                raise Refusal('original software configuration witness absent')
            return dict(grant=grant['id'], board=grant['board_id'], owner=grant['owner'],
                        issuer=grant['issued_by'], authority=grant['authority'],
                        configuration=policy['configuration'], task_hash=policy['task_hash'])

    def historical_source_access(self, runtime, post, principal):
        """Exact current read visibility before journal field acquisition.

        Schema-4 query_posts thread-member predicate; no text/attachments.
        """
        if self.role != 'Reviews' or principal != runtime.config['roles']['Work']['owner']:
            raise Refusal('exact original Reviews source/current Work principal required')
        with self.opened(settlement=True) as conn:
            self._historical_visibility(conn,self.selected['owner'],post)
            self._historical_visibility(conn,principal,post)
        return True

    @staticmethod
    def _historical_visibility(conn, actor, post):
        active = conn.execute("SELECT 1 FROM sessions WHERE session=? AND status='active'",(actor,)).fetchone()
        visible = conn.execute('SELECT 1 FROM posts LEFT JOIN thread_posts ON thread_posts.post_seq=posts.seq '
            'LEFT JOIN threads ON threads.thread_id=thread_posts.thread_id '
            'LEFT JOIN posts AS thread_root ON thread_root.seq=threads.thread_id '
            'WHERE posts.seq=? AND (posts.recipient IS NULL OR posts.recipient=? OR '
            '(threads.thread_id IS NOT NULL AND (threads.opener=? OR thread_root.recipient=?)))',
            (post,actor,actor,actor)).fetchone()
        if not active or not visible:
            raise Refusal('current original source read visibility absent; source custodian retains it')

    def _selected_usage(self, conn, grant):
        # Public aggregate row residency only, never historical payload LENGTH.
        shared = conn.execute('SELECT COUNT(*) FROM coordinator_deliveries_v1').fetchone()[0]
        owned = conn.execute('SELECT COUNT(*) FROM coordinator_deliveries_v1 d JOIN coordinator_grants_v1 g '
                             'ON g.id=d.grant_id WHERE g.runtime=? AND g.runtime_dev=? AND g.runtime_ino=? AND g.actor=?',
                             tuple(grant[k] for k in ('runtime','runtime_dev','runtime_ino','actor'))).fetchone()[0]
        return dict(shared_rows=shared, runtime_rows=owned)

    def selected_basis(self, runtime, pins):
        from .selected_source import snapshot
        with self.opened(settlement=True) as conn:
            grant = self._original(conn, runtime)
            events = [snapshot(runtime, p) for p in pins if p['role'] == self.role]
            return dict(configuration=self._configuration(runtime,self._binding(grant)), binding=self._binding(grant),
                        usage=self._selected_usage(conn,grant), events=events,
                        scope='explicit selected source metadata only; no historical body/hash/size acquisition; '
                              'payload residency unobserved and still checked at actual delivery/allocation')

    def prospective_basis(self, runtime):
        """Original binding and recorded identifiers, never rehash old bodies.

        Usable only for explicitly future-only continuing selection. Historical
        retained APIs keep their own guarded body validation and attribution.
        """
        with self.opened(settlement=True) as conn:
            grant = self._original(conn, runtime)
            original = self._binding(grant)
            continuation = None
            if conn.execute("SELECT 1 FROM sqlite_master WHERE name='coordinator_retained_caps_v1'").fetchone():
                row = conn.execute('SELECT id,issuer,created,revoked,visits,cursor FROM coordinator_retained_caps_v1 '
                                   'WHERE source_grant=? AND revoked IS NULL', (grant['id'],)).fetchone()
                continuation = dict(row) if row else None
            return {'configuration': self._configuration(runtime, original), 'binding': original,
                    'usage': self._usage(conn, grant), 'continuation': continuation,
                    'events': runtime.rows('SELECT id,hash FROM events WHERE role=? ORDER BY id', (self.role,)),
                    'scope': 'future-only; recorded original hashes/bindings, no body observation, validation or historical authority'}

    def _configuration(self, runtime, binding):
        return configuration.original_binding(runtime, self.role, binding)

    def _delivery_grant(self, conn, runtime, outbox):
        if not configuration.outbox_allowed(runtime, outbox):
            raise Refusal('historical outbox retains original config, destinations and custody; no current replay')
        return super()._delivery_grant(conn, runtime, outbox)

    def receiving_intent(self, runtime, event, *, conserved=False):
        """A marker alone grants nothing: require the exact durable delivery intent."""
        delivery = event.get('source_delivery', {})
        with self.opened(settlement=True) as conn:
            receiver = self._grant(conn, runtime)
            intent = conn.execute('SELECT * FROM coordinator_software_deliveries_v1 WHERE delivery=?',
                                  (delivery.get('id'),)).fetchone()
            row = conn.execute('SELECT * FROM coordinator_deliveries_v1 WHERE id=?', (delivery.get('id'),)).fetchone()
            outbox = runtime.one('SELECT * FROM outboxes WHERE id=?', (delivery.get('id'),))
            material = None
            if conserved and not intent and not row:
                material = self.conserved_receiving_material(runtime, conn, delivery.get('id'))
                intent, row = material['software'][0], material['delivery']
            if (not intent or not row or not outbox or json.loads(intent['payload']) != event
                    or intent['event'] != event['id'] or intent['receiver_grant'] != receiver['id']
                    or intent['source_grant'] != row['grant_id']
                    or delivery.get('source_grant') != row['grant_id']
                    or delivery.get('receiver_grant') != receiver['id']
                    or delivery.get('source_hash') != digest(json.loads(outbox['payload']))
                    or row['payload'] != outbox['payload'] or row['producer'] != outbox['producer']
                    or row['kind'] != outbox['kind']
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
            if material and self._binding(material['grant']) != source_board._binding(source_board._grant(conn, runtime)):
                raise Refusal('conserved source grant differs from its exact current binding')
            notice = (material['notices'][0] if material else
                      conn.execute('SELECT * FROM notification_outbox WHERE notification_id=?', (row['notice'],)).fetchone())
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

    def completion_authority(self, runtime, task):
        from .bounded_log import selected as bounded
        if not bounded(self.config['tasks'][task]):
            return super().completion_authority(runtime, task)
        transition = configuration.selected(runtime)
        if not transition:
            return super().completion_authority(runtime, task)
        cap, selection = runtime.processing.current()
        if task not in selection['tasks'] or task not in transition['basis']['tasks']:
            raise Refusal('bounded completion outside exact prospective task selection')
        with self.opened() as conn:
            grant = self._grant(conn, runtime)  # Exact still-revoked original binding.
            if not conn.execute("SELECT 1 FROM sqlite_master WHERE name='coordinator_completion_grants_v1'").fetchone():
                raise Refusal('original completion delegation unavailable; no fabricated witness')
            old = conn.execute('SELECT policies FROM coordinator_completion_grants_v1 WHERE grant_id=?', (grant['id'],)).fetchone()
            first = runtime.one('SELECT selection FROM configuration_transitions ORDER BY position LIMIT 1')
            original = json.loads(first['selection'])['previous_configuration']['tasks'][task].get('routine_completion')
            current = self.config['tasks'][task]['routine_completion']
            if (self.config['tasks'][task]['role'] != self.role or not old
                    or json.loads(old['policies']).get(task) != original
                    or original not in ({'kind':'file-witness','targets':current['targets']}, current)):
                raise Refusal('bounded completion requires original exact seven-target role delegation')
            return {**grant, 'completion_transition': {'configuration':digest(self.config),
                    'processing_capability':cap['id'], 'authority':transition['authority'],
                    'policy':current, 'historical_completion':False}}

    def software_authority(self, runtime, task):
        if task not in runtime.processing.current()[1]['tasks'] or self.config['tasks'][task]['role'] != self.role:
            raise Refusal('task outside explicit processing delegation')
        grant = self.verify_authority(runtime)
        from . import prospective
        epoch = prospective.current(runtime, task)
        if epoch:
            if epoch['selection'].get('processing_capability') != runtime.processing.key:
                raise Refusal('ordinary epoch not issued for this exact continuing service')
            return {**grant, 'prospective_epoch': epoch['id'],
                    'delegated_by': epoch['selection']['grantor'],
                    'delegation_authority': epoch['selection']['authority']}
        return grant

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
                             'allowed_tasks': ([] if json.loads(outbox['payload']).get('schema') == 'alert-occurrences-v1'
                                               and outbox['alert'] and not outbox['event'] and not outbox['job']
                                               else receiver.selected['routes']), 'parent': outbox['event'],
                             'post': row['post'], 'notice': row['notice'], 'board_id': receive['board_id'],
                             'grant': receive['id'], 'processing_capability': runtime.processing.key,
                             'source_delivery': {'id': row['id'], 'source_grant': source['id'],
                                                 'receiver_grant': receive['id'], 'source_hash': digest(json.loads(outbox['payload']))}}
                    runtime.budget(None, len(encode(event).encode()) + 1024)
                    conn.execute('INSERT INTO coordinator_software_deliveries_v1 VALUES(?,?,?,?,?)',
                                 (row['id'], source['id'], receive['id'], event['id'], encode(event)))
        runtime.ingest(event)  # Exact persisted intent recovery, never a fresh business replay.
        with runtime.tx():
            prior_link = runtime.one('SELECT event FROM processing_delivery_links WHERE delivery=?', (outbox['id'],))
            if prior_link and prior_link['event'] != event['id']:
                raise Refusal('delivery already belongs to a different whole consumer chain')
            runtime.db.execute('INSERT OR IGNORE INTO processing_delivery_links VALUES(?,?)', (outbox['id'], event['id']))
        record = runtime.one('SELECT * FROM processing_controls WHERE event=?', (event['id'],))
        if not record or not record['resolution']:
            return True
        resolution = runtime.input_resolution(event['id'])
        if (not resolution or resolution['receipt']['mode'] not in {'control', 'notification'}
                or resolution['receipt']['remaining_obligations']):
            return True
        proof = runtime.processing.control_proof(event['id'], record['attempt'], resolution['receipt'])
        state = runtime.one('SELECT * FROM events WHERE id=?', (event['id'],))
        queue = runtime.one('SELECT * FROM queue WHERE event=?', (event['id'],))
        if (state['hold'] or state['ack'] not in {'done', 'plain'} or not queue or queue['state'] != 'done'
                or state['processed_at'] is None or runtime.dependency_hold(event['id'])):
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

    def scan(self, runtime, limit=100):
        from .service import admit_input
        available = admit_input(runtime)
        return super().scan(runtime, min(limit, available) if available is not None else limit)

    def scan_after(self, runtime, grant):
        _, selection = runtime.processing.current()
        if not selection['future_intake']:
            raise Refusal('future intake was not selected')
        from .service import admit_input
        admit_input(runtime)
        return max(super().scan_after(runtime, grant), selection['basis']['roles'][self.role]['future_after'])


def revoke(runtime, boards, key):
    row = runtime.one('SELECT * FROM processing_capabilities WHERE id=?', (key,))
    actor = boards['Work'].store.acting_session(runtime.config['software_delegation']['grantor'])
    if not row or row['issuer'] != actor:
        raise Refusal('only genuine original Work issuer may revoke this processing capability')
    with runtime.tx():
        runtime.db.execute('UPDATE processing_capabilities SET revoked=COALESCE(revoked,?) WHERE id=?', (runtime.clock(), key))
    return {'revoked': key, 'effects_and_collectors': 'retained; no cancellation or replay'}


def diagnostic_source(runtime, boards, key, event):
    access = Access(runtime, key, boards)
    _, selection = access.current()
    position = runtime.one('SELECT position FROM processing_source_positions WHERE event=?', (event,))
    if not position or position['position'] <= selection['basis']['event_boundary']:
        raise Refusal('diagnostics require exact current prospective source frontier; no old-source inventory')
    original = runtime.event(event)
    if not access.event(original):
        raise Refusal('diagnostic source outside exact current processing selection')
    boards[original['role']].verify_authority(runtime)
    state = runtime.one('SELECT id,hash,role,state,classifier,ack,processed_at,hold IS NOT NULL AS held, '
                        'error IS NOT NULL AS error_present FROM events WHERE id=?', (event,))
    if not state or state['hash'] != digest(original):
        raise Refusal('diagnostic source no longer matches its original hash')
    return state, position


def reservation_diagnostics(runtime, boards, key, event):
    """Read-only admitted source metadata; never reconstruct source/capture bodies.

    Post-boundary rows were admitted by the current processing intake. Retained
    rows require the exact already-selected immutable hash. This observation
    confers no task, reservation, admission, launch or effect permission.
    """
    access = Access(runtime, key, boards)
    _, selection = access.current()
    def snapshot():
        state = runtime.one('SELECT id,hash,role FROM events WHERE id=?', (event,))
        position = runtime.one('SELECT position FROM processing_source_positions WHERE event=?', (event,))
        queue = runtime.one('SELECT task,phase,state,job FROM queue WHERE event=?', (event,))
        mapping = runtime.one('SELECT version FROM input_resolutions WHERE event=? ORDER BY version DESC LIMIT 1', (event,))
        runs = runtime.rows("SELECT s.controller FROM service_runs s JOIN processing_runs p ON p.controller=s.controller "
                            "WHERE s.capability=? AND p.capability=? AND s.state='serving' AND s.returned IS NULL "
                            "AND p.state='owned' LIMIT 2", (key, key))
        return state, position, queue, mapping, runs
    before = snapshot()
    state, position, queue, mapping, runs = before
    if not state or not position or state['role'] not in selection['basis']['roles']:
        raise Refusal('exact admitted processing source metadata required')
    retained = event in selection['retained_events']
    if retained:
        original = {e['id']: e['hash'] for r in selection['basis']['roles'].values() for e in r['original']['events']}
        if original.get(event) != state['hash']:
            raise Refusal('retained source metadata differs from selected immutable hash')
    elif position['position'] <= selection['basis']['event_boundary']:
        raise Refusal('source metadata outside current processing frontier')
    boards[state['role']].verify_authority(runtime)
    if len(runs) != 1:
        raise Refusal('one current original service controller required; no liveness inferred')
    controller = runs[0]['controller']
    canonical_uuid(controller)
    reservation = reservation_observation(runtime, key, event, state, queue, controller)
    access.current()
    if snapshot() != before:
        raise Refusal('reservation source context changed; no currentness inference')
    return {'source': state, 'position': position['position'], 'capability': key,
            'controller': controller, 'responsibility': queue, 'reservation': reservation,
            'processing_complete': False,
            'meaning': 'read-only last reached reservation outcome; no source bodies, fresh attempt, liveness or clearance'}


def source_diagnostics(runtime, boards, key, event):
    """Exact prospective metadata only; no attempt detail, raw result or history."""
    state, position = diagnostic_source(runtime, boards, key, event)
    runs = runtime.rows("SELECT s.controller FROM service_runs s JOIN processing_runs p ON p.controller=s.controller "
                        "WHERE s.capability=? AND p.capability=? AND s.state='serving' AND s.returned IS NULL "
                        "AND p.state='owned' LIMIT 2", (key, key))
    if len(runs) != 1:
        raise Refusal('one current original service controller required; no liveness inferred')
    controller = runs[0]['controller']
    canonical_uuid(controller)
    classifier = runtime.one('SELECT id,controller,kind,state,ended,collected,exit,capture,cleanup, '
                             'error IS NOT NULL AS error_present FROM attempts '
                             "WHERE id=? AND event=? AND controller=? AND kind IN ('classifier','diagnosis')",
                             (state['classifier'], event, controller))
    if state['state'] == 'received':
        classifier = None  # Stored old pointer is not classification of the new resolution.
    responsibility = runtime.one('SELECT task,phase,state,job FROM queue WHERE event=?', (event,))
    def metadata_record(table, kind):
        # Project metadata in SQL: never acquire the frozen backing values,
        # request, raw model return or error body merely to diagnose progress.
        fields = ("r.hints IS NOT NULL AS hints_present, (SELECT COALESCE(SUM(json_array_length(m.value)),0) "
                  "FROM json_each(r.hints) t,json_each(t.value) m) AS hint_count" if kind == 'input-locator' else
                  "r.resolution IS NOT NULL AS resolution_present, (SELECT json_group_object(t.key, "
                  "json(COALESCE(json_extract(t.value,'$.unresolved'),'[]'))) FROM json_each(r.snapshot) t) AS unresolved")
        record = runtime.one(f'SELECT r.attempt,r.error IS NOT NULL AS error_present,{fields} '
                             f'FROM {table} r JOIN attempts a ON a.id=r.attempt '
                             'WHERE r.event=? AND r.capability=? AND r.source_hash=? '
                             'AND a.event=? AND a.controller=? AND a.kind=?',
                             (event, key, state['hash'], event, controller, kind))
        if not record:
            return None
        attempt = runtime.one('SELECT id,kind,state,begin,ended,collected,exit,capture,cleanup, '
                              'error IS NOT NULL AS error_present FROM attempts WHERE id=?', (record['attempt'],))
        result = {'attempt':record['attempt'], 'collection':attempt, 'error_present':bool(record['error_present'])}
        result['attempt_scope'] = diagnostic_attempt_scope(runtime, record['attempt'], key, event, state['hash'], controller)
        if kind == 'input-locator':
            result['hints_present'] = bool(record['hints_present'])
            result['hint_count'] = record['hint_count'] if record['hints_present'] else None
        else:
            result['resolution_present'] = bool(record['resolution_present'])
            result['unresolved_relationships'] = json.loads(record['unresolved'])
        return result
    locator = metadata_record('input_locators', 'input-locator')
    mapping = metadata_record('input_lookups', 'input-mapping')
    dependency = dependency_observation(runtime, key, event, state, controller)
    job = runtime.one('SELECT id,task,state,active_attempt FROM jobs WHERE id=? AND controller=?',
                      (responsibility['job'], controller)) if responsibility else None
    if job and job['active_attempt']:
        job['attempt'] = runtime.one('SELECT id,state,begin,ended,collected,exit,capture FROM attempts '
                                     'WHERE id=? AND job=? AND controller=?', (job['active_attempt'], job['id'], controller))
    resolution = runtime.one('SELECT version,source_hash FROM input_resolutions WHERE event=? '
                             'ORDER BY version DESC LIMIT 1', (event,))
    if resolution and resolution['source_hash'] != state['hash']:
        raise Refusal('diagnostic resolution differs from the selected source hash')
    reservation = reservation_observation(runtime, key, event, state, responsibility, controller)
    if (diagnostic_source(runtime, boards, key, event) != (state, position)
            or runtime.one('SELECT version,source_hash FROM input_resolutions WHERE event=? '
                           'ORDER BY version DESC LIMIT 1', (event,)) != resolution
            or runtime.one('SELECT task,phase,state,job FROM queue WHERE event=?', (event,)) != responsibility
            or runtime.one("SELECT state,returned FROM service_runs WHERE controller=? AND capability=?",
                           (controller, key)) != {'state': 'serving', 'returned': None}):
        raise Refusal('diagnostic source/controller changed; inspect again without effect replay')
    return {'capability': key, 'controller': controller, 'source': state, 'position': position['position'],
            'classifier': classifier,
            'classifier_scope': ('awaiting-fresh-classification' if state['state'] == 'received' else
                                 'current-controller' if classifier else 'unavailable-current-controller'),
            'responsibility': responsibility, 'locator':locator, 'mapping': mapping, 'dependency':dependency,
            'reservation': reservation,
            'job':job, 'resolution': resolution,
            'processing_complete': False,
            'meaning': 'bounded current prospective metadata; END/ACK/empty errors never imply processing or acceptance'}


def diagnostic_attempt_scope(runtime, attempt, key, event, source_hash, controller):
    from .metadata_lookup import diagnostic_current_context
    return ('current-handoff-context-observed' if diagnostic_current_context(
        runtime, attempt, key, event, source_hash, controller) else 'structurally-linked-currentness-unknown')


def dependency_observation(runtime, key, event, state, controller):
    """Project a recorded refusal, without acquiring its arbitrary error body."""
    # Literal public reasons from the metadata worker. This is an allowlist,
    # not a prefix match or a promise that every exception is understood.
    safe = (
        'lookup needs its original fresh classified prospective unreserved responsibility',
        'lookup cannot widen original task/package/member authority',
        'cyclic source applicability',
        'lookup scope exceeds independently narrowed receiver roots',
        'lookup scope exceeds actual consumer targets',
        'metadata backing acquisition limit; return scope question',
        'ambiguous existing-member identity; no lookup duplication',
        'lookup parent requires its explicitly selected stable member representation',
        'known point identity/lifecycle changed; original metadata retained',
        'overlapping lookup templates disagree on the same identity',
        'metadata point limit; narrower genuine scope required',
        'bounded metadata context exceeded; original remains owned',
        'locator authority/source changed; original hints retained',
        'locator template context exceeds selected limit',
        'combined metadata context exceeds selected limit',
        'unresolved metadata needs the original task permitted Work question route',
        'incomplete metadata interpretation remains with original collector; no automatic replay',
        'metadata result needs exact task/integration/reason/evidence/remaining_obligations',
        'original metadata handoff binding changed',
        'metadata handoff authority changed before model read',
        'metadata resolution needs its exact actual software worker/collection/prospective authority',
        'metadata policy/admission/grant changed; no post-result restamping',
        'typed metadata interpretation required',
        'bounded unique observed point selections required',
        'model metadata suggestions confer no unobserved point authority',
        'original point definition changed',
        'unresolved locator relationships cannot authorize new business',
        'known, positively new or unresolved-existing required; unknown never means new',
        'locator hints need their actual complete original software collection; no replay',
        'locator cannot supply an unselected task or semantic decision',
        'locator cannot supply an unselected exact scope',
        'bounded unique stable-member hints required',
        'locator member count exceeds selected context scope',
    )
    placeholders = ','.join('?' for _ in safe)
    # Filter before crossing the SQL return boundary. Stage and attempt are
    # also untrusted stored detail: only known stages and an actual matching
    # metadata-worker attempt may leave the journal. Preserve the stored row.
    row = runtime.one(
        "SELECT CASE WHEN d.stage IN ('observation','locator','mapping') THEN d.stage "
        "ELSE 'unknown' END AS stage,d.observed, "
        f"CASE WHEN json_valid(d.detail) THEN CASE WHEN json_extract(d.detail,'$.dependency') "
        f"IN ({placeholders}) THEN json_extract(d.detail,'$.dependency') END END AS reason, "
        "CASE WHEN json_valid(d.detail) THEN json_extract(d.detail,'$.attempt') IS NOT NULL "
        "ELSE 0 END AS attempt_recorded,a.id AS attempt "
        "FROM input_dependencies d LEFT JOIN attempts a "
        "ON a.id=CASE WHEN json_valid(d.detail) THEN json_extract(d.detail,'$.attempt') END "
        "AND a.event=d.event AND a.controller=d.controller "
        "AND a.kind=CASE d.stage WHEN 'locator' THEN 'input-locator' "
        "WHEN 'mapping' THEN 'input-mapping' END "
        "WHERE d.event=? AND d.capability=? AND d.source_hash=? AND d.controller=?",
        (*safe, event, key, state['hash'], controller))
    if not row:
        return None
    return {'stage': row['stage'], 'observed': row['observed'],
            'detail': {'dependency': row['reason'] if row['reason'] is not None else
                       'metadata dependency refused; detail outside bounded public vocabulary',
                       'reason_known': row['reason'] is not None, 'attempt': row['attempt'],
                       'attempt_scope': (diagnostic_attempt_scope(runtime, row['attempt'], key, event, state['hash'], controller) if row['attempt'] else
                                         'unavailable-current-source-controller' if row['attempt_recorded'] else
                                         'unrecorded')},
            'meaning': 'recorded exact source/hash/capability/controller association; handoff comparison is observational, not execution, liveness or acceptance'}


def reservation_observation(runtime, key, event, state, responsibility, controller):
    """Typed exact-context view only; legacy raw dependencies are not current."""
    from .reservation import view
    return view(runtime, key, event, state, responsibility, controller)


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


def control_receipt(runtime, event, row, result, receipt):
    """Versioned software syntax only; the collected model return is immutable.

    Callers must also verify control_proof. Its exact derivation is recorded in
    input_resolutions.prior.software_processing, never attributed to the model.
    """
    keys = {'source_hash', 'mode', 'task', 'package', 'related_event', 'related_job',
            'reason', 'evidence', 'remaining_obligations'}
    if isinstance(receipt,dict) and set(receipt) == keys | {'plain_control'}:
        base = {k:v for k,v in receipt.items() if k != 'plain_control'}
        derived, syntax = control_receipt(runtime,event,row,result,base)
        return derived, {'version':'plain-control-scope-envelope-v1','original_receipt_hash':digest(receipt),
                         'derived_receipt_hash':digest(derived),'syntax':syntax}
    if (not isinstance(receipt, dict) or set(receipt) != keys
            or receipt['mode'] != 'control' or receipt['task'] != '@control'
            or any(receipt[k] is not None for k in ('package', 'related_event', 'related_job'))):
        return receipt, None
    runtime.processing.current()  # Before each current source/binding read group.
    state = runtime.one('SELECT hash,hold,processed_at FROM events WHERE id=?', (event,))
    queue = runtime.one('SELECT * FROM queue WHERE event=?', (event,))
    derived = {**receipt, 'task': None}
    syntax = {'version': 'software-control-queue-marker-v1',
              'meaning': 'SOFTWARE-DERIVED SYNTAX; no model rewrite, native receipt or underlying settlement',
              'attempt': row['id'], 'source_hash': receipt['source_hash'],
              'capability': runtime.processing.key, 'controller': row['controller'],
              'binding': json.loads(row['binding']),
              'raw_result_sha256': hashlib.sha256(row['result'].encode()).hexdigest(),
              'result_hash': digest(result), 'original_receipt_hash': digest(receipt),
              'derived_receipt_hash': digest(derived), 'from_task': '@control', 'to_task': None}
    # Only a previously applied exact syntax proof permits durable normalization.
    # A new marker still requires the original awaiting-owner responsibility.
    resolution = runtime.input_resolution(event)
    durable = False
    if resolution:
        proof = resolution['prior'].get('software_processing', {})
        saved = proof.get('syntax_derivation')
        if isinstance(saved, dict) and saved.get('version') == 'plain-control-scope-envelope-v1':
            raw = json.loads(result['decision_json'])
            if saved != {'version':'plain-control-scope-envelope-v1','original_receipt_hash':digest(raw),
                         'derived_receipt_hash':digest(derived),'syntax':syntax}:
                raise Refusal('applied marker envelope differs from exact original syntax proof')
            saved = saved['syntax']
        durable = (resolution['source_hash'] == receipt['source_hash']
                   and resolution['receipt'] == derived and saved == syntax
                   and proof.get('attempt') == row['id']
                   and proof.get('source_hash') == receipt['source_hash']
                   and proof.get('result_hash') == digest(result)
                   and proof.get('native_owner_receipt') is False)
        if not durable:
            raise Refusal('applied marker differs from exact original canonical resolution')
    if (not state or state['hold'] or (state['processed_at'] is not None and not durable)
            or not queue or queue['phase'] != 'control'
            or (queue['task'] not in ('@control','@unresolved') if durable else
                queue['task'] != '@control' or queue['state'] != 'awaiting-owner')
            or queue['job'] is not None
            or queue['package'] is not None or (row['controller'] != runtime.controller
                and not __import__(__package__+'.report_repair', fromlist=['released_control']).released_control(runtime, event, row))
            or json.loads(row['detail']).get('processing_capability') != runtime.processing.key
            or result['semantic'] != 'DONE' or receipt['source_hash'] != state['hash']):
        raise Refusal('control marker syntax requires exact current unheld source/controller/responsibility and DONE')
    runtime.processing.current()
    source = runtime.event(event)
    if (source['kind'] != 'board' or source['role'] != queue['role'] or digest(source) != state['hash']
            or not runtime.processing.event(source)):
        raise Refusal('control marker syntax requires the exact selected current board source')
    return derived, syntax


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

    def pump_delivery(self, outbox, *, send_control=True):
        if configuration.outbox_allowed(self.store, outbox):
            return super().pump_delivery(outbox, send_control=send_control)

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
            attempt = self.store.one('SELECT collected FROM attempts WHERE id=?', (job['active_attempt'],))
            if attempt['collected'] is not None:
                self.reconcile_collected(job)
        self.store.complete_events()

    def schedule_job(self,job=None):
        for pending in self.store.rows("SELECT q.*,t.legacy_hold FROM queue q JOIN enrollments t ON t.role=q.role WHERE q.state='queued' ORDER BY q.rowid"):
            if not self.store.processing.task(pending):
                continue
            task = self.config['tasks'][pending['task']]
            if task.get('execution') == 'owner' and not self.store.processing.review_task(pending['task']):
                self.store.record_operational_error(pending['event'], {'dependency': 'actual selected opaque procedure holder', 'task': pending['task']}, pending['role'], 'processing-dependency')
            from .resource_scopes import blocked
            if pending['legacy_hold'] and blocked(self.store, pending):
                self.store.record_operational_error(pending['event'], {'dependency': 'supported scoped original effect-owner disposition', 'hold': pending['legacy_hold']}, pending['role'], 'processing-dependency')
        super().schedule_job(job)

    def schedule_classification_recovery(self):
        # Control handling is an actual worker, not classifier diagnosis/replay.
        scope, parameters = configuration.event_candidate_scope(self.store)
        candidates = self.store.rows(
            "SELECT e.id,e.role FROM events e LEFT JOIN queue q ON q.event=e.id "
            "WHERE e.processed_at IS NULL AND e.hold IS NULL "
            "AND (e.state='classification-held' OR q.phase='control') AND (" +
            scope + ") ORDER BY e.received,e.id", parameters)
        for row in candidates:
            from .metadata_lookup import delegated
            source_event = self.store.event(row['id'])
            queue = self.store.one('SELECT task FROM queue WHERE event=?', (row['id'],))
            if delegated(self.store, source_event) and queue and queue['task'] == '@unresolved':
                continue  # Separate narrow metadata consumer, never broad owner disposition.
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
        from .capacity import notification
        notice = notification(self.store, original)
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
                  'responsibility.task=@control is a queue sentinel, never an actual task. For mode=control, '
                  'receipt.task MUST be null, and package/related_event/related_job MUST also be null. '
                  'Only mode=route selects an actual task. For an explicitly no-new-owned-work-or-effects Board status, '
                  'remaining_obligations covers only duties/dependencies needed to finish THIS message handling. '
                  'Judge the whole authenticated source, actual result, queue, descendants, effects and authority; '
                  'keywords, DONE or empty arrays alone cannot establish no new work. Governing constraints, '
                  'legacy holds, unrelated jobs and another actor\'s assessment remain binding at their originals; '
                  'their presence in context does not assign their settlement to this message. Import an original '
                  'dependency only when evidence links it to handling actually required here. An empty list is '
                  'permitted only when that whole current scope is complete. Unknown current scope, real work, '
                  'decision, blocker or effect uncertainty remains blocking. Never rewrite earlier returns. '
                  'For a NON-NOTIFICATION source, when whole-source interpretation and actual handling evidence '
                  'establish no new owned work or effects and EVERY own handling duty is complete, emit '
                  'plain_control in decision_json: an object with EXACT scope,accounting,evidence keys. '
                  'scope must be no-new-owned-work-or-effects. Account for EVERY unchanged remaining_obligations '
                  'entry in order as {index,text,disposition:conserved-at-original-source,owner,event,source_hash,evidence}. '
                  'Keep original obligations losslessly; accounting is empty only when there are no original entries. '
                  'plain_control.evidence MUST be a JSON list of 1..32 nonempty short strings, each at most '
                  '4000 characters; never a scalar string. This nested list must explain the whole source and '
                  'actual completed handling, separately from outer decision_json.evidence and from '
                  'plain_control.accounting and each accounting entry\'s evidence. This is '
                  'software interpretation for runtime guard validation, not a claim of native ACK, completed '
                  'runtime processing, approval, or actual owner authority. '
                  'Use exact supplied existing source/owner references with meaningful scope evidence; no keyword guesses. '
                  'Unknown, THIS-message work/decision/effect, or insufficient references MUST remain blocking: omit plain_control. '
                  'Never use plain_control for authenticated notifications; their full occurrence/cause consumption '
                  'contract below remains required. '
                  'No native ACK or acceptance is requested. '
                  'mode=coalesce needs actual same-role related_event/job proof. Evidence must cite actual supplied '
                  'source. Scope corrections go to Root, scope/blockers to Work; Reviews/QA/Branch duties stay '
                  'with actual holders. Retain every unresolved authority/effect/selected-procedure dependency '
                  'required for THIS message handling in '
                  'remaining_obligations. Do not resolve an effect hold or acceptance by giving it an empty array. '
                  '''Return PARTIAL with decision_json="null" when actual authority/meaning is insufficient.
For an authenticated notification_context, your bounded task is to read and account for EVERY
full occurrence and its cause/owner/limits. mode=notification acknowledges ONLY this notification's
processing. Its evidence MUST include notification_context.coverage_evidence. Use task/package/
related_event/related_job=null and remaining_obligations=[] only when this notification reading is
complete. Underlying original/debt/source/effect/consumer/uncertainty/retention obligations remain
whole in the supplied occurrences with their actual owners; this receipt neither settles them nor
creates another business allocation for every unchanged recurrence. If interpretation itself needs
an actual decision, retain mode=control/route/coalesce and explicit obligations instead. Do not
fabricate reading, consent or a native owner's receipt.\n''' +
                  encode({'source': original, 'source_hash': digest(original), 'notification_context': notice,
                          'prior': self.store.input_resolution(event),
                          'responsibility': self.store.one('SELECT * FROM queue WHERE event=?', (event,)),
                          'same_role_jobs': self.store.rows('SELECT id,task,package,state,members,effects,hold_reason,controller,active_attempt FROM jobs WHERE role=? ORDER BY created,id LIMIT 16', (original['role'],)),
                          'authority': self.store.processing.current()[1]['authority'],
                          'role_effect_hold': self.store.enrollment(original['role'])['legacy_hold'],
                          'conserved_source_references': [dict(id=r['id'],role=r['role'],source_hash=r['hash'],owner=self.store.enrollment(r['role'])['owner']) for r in self.store.rows('SELECT id,role,hash FROM events WHERE id!=? ORDER BY received DESC LIMIT 32',(event,))]}))
        outcome = await self.run_model(attempt, prompt,
                                       {'cwd': self.config['classifier']['cwd'], 'sandbox': 'read-only', 'network': False}, CONTROL_SCHEMA)
        self.store.collect(attempt, outcome)
        try:
            apply_control(self.store, event, attempt)
        except (Refusal, ValueError, TypeError) as exc:
            with self.store.tx():
                self.store.db.execute('UPDATE processing_controls SET error=? WHERE event=?', (str(exc)[:1000], event))
            self.store.record_operational_error(event, {'dependency': str(exc), 'attempt': attempt}, original['role'], 'processing-control-dependency')


def _apply_control(runtime, event, attempt, *, terminal_request=None, software_terminal=False):
    """Recover an exact collected disposition, never relaunch its original."""
    runtime.processing.current()
    disposition = runtime.one('SELECT * FROM plain_control_dispositions WHERE event=?', (event,))
    if disposition:
        from .plain_control import validate
        request = json.loads(disposition['request'])
        validate(runtime, event, attempt, request, authenticate=False)
        resolution = runtime.input_resolution(event)
        if (disposition['capability'] != runtime.processing.key
                or disposition['resolution_hash'] != digest(resolution)
                or terminal_request is not None and terminal_request != request):
            raise Refusal('exact original plain-control disposition changed')
        return resolution
    if terminal_request is not None:
        from .plain_control import validate
        validate(runtime, event, attempt, terminal_request, authenticate=not software_terminal)
    row = runtime.attempt(attempt)
    result = json.loads(row['result'] or 'null') or {}
    receipt = parse_json(result.get('decision_json', 'null'))
    runtime.processing.control_proof(event, attempt, receipt)
    receipt, _ = control_receipt(runtime, event, row, result, receipt)
    # The typed stopped-original path already owns the whole return transaction.
    with (nullcontext() if runtime.db.in_transaction else runtime.tx()):
        if terminal_request is not None:
            validate(runtime, event, attempt, terminal_request, authenticate=not software_terminal)
        resolution = runtime.resolve_input(event, runtime.config['actor'], receipt, processing_attempt=attempt)
        if receipt['mode'] != 'notification' and terminal_request is None:
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
              and runtime.config['tasks'][name]['effects'] == 'none'
              and not runtime.config['tasks'][name].get('require_package_scope')]
    if not routes:
        raise Refusal('meaningful control return needs a selected read-only Work proposer consumer')
    response = {'id': digest({'processing_control_return': event, 'attempt': attempt}),
                'kind': 'response', 'role': 'Work', 'recipient': runtime.enrollment('Work')['owner'],
                'author': runtime.attempt(attempt)['session'], 'parent': event, 'package': None,
                'notice': None, 'board_id': None, 'grant': None, 'allowed_tasks': routes,
                'processing_control_return': {'source': event, 'attempt': attempt},
                'body': {'source': runtime.event(event), 'actual_worker_return': result,
                         'software_resolution': resolution, 'native_owner_receipt': False}}
    runtime.budget('events', 2 * len(encode(response).encode()) + 2048)
    runtime.db.execute('INSERT INTO processing_control_returns VALUES(?,?,?,?,?)',
                       (event, response['id'], attempt, encode(response), runtime.clock()))
    runtime.db.execute('INSERT INTO events(id,role,payload,hash,received,parent) VALUES(?,?,?,?,?,?)',
                       (response['id'], 'Work', encode(response), digest(response), runtime.clock(), event))
    note_source(runtime, response['id'])
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
        row = runtime.one('SELECT * FROM processing_runs WHERE controller=? AND capability=?', (controller, key))
        if not row:
            raise Refusal('original processing run disappeared before collection')
        try:
            prior = json.loads(row['state'])
        except (ValueError, TypeError):
            prior = None
        if isinstance(prior, dict) and 'parent_END' in prior:
            if prior != {'parent_END': receipt}:
                raise Refusal('original parent END receipt is already recorded; contradictory release refused')
            return {'controller': controller, 'collection': receipt, 'processing_or_effects_complete': False}
        runtime.budget(None, len(encode(receipt).encode()) + 1024)
        runtime.db.execute('UPDATE processing_runs SET state=? WHERE controller=?', (encode({'parent_END': receipt}), controller))
    return {'controller': controller, 'collection': receipt, 'processing_or_effects_complete': False}


async def run(runtime, boards, key, seconds, emit):
    with configuration.stopped(runtime):
        return await _run(runtime, boards, key, seconds, emit)


async def _run(runtime, boards, key, seconds, emit):
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
        if configuration.owned_service_conflict(runtime):
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



def apply_control(runtime, event, attempt):
    from . import report_repair, plain_control
    if plain_control.automatic(runtime,event,attempt) is not None:
        return runtime.input_resolution(event)
    amendment = report_repair.lease_record(runtime, runtime.processing.key)
    request = amendment or report_repair.pair_record(runtime, runtime.processing.key)
    if not request or event != request['basis']['sources'][1]['event']:
        return _apply_control(runtime, event, attempt)
    # A distinct applier keeps its own identity and serializes original-return consumption.
    with configuration.stopped(runtime), runtime.tx():
        runtime.processing.current()
        if not amendment:
            report_repair.pair_finite(runtime, runtime.processing.current()[1])
        anchor = request['basis']['sources'][1]
        if attempt != anchor['control']['attempt']:
            raise Refusal('only the selected original control attempt may be applied')
        previous = runtime.one('SELECT * FROM processing_control_returns WHERE source=?', (event,))
        if previous:
            state = runtime.one('SELECT hash,hold,processed_at FROM events WHERE id=?', (event,))
            epoch = runtime.one('SELECT * FROM prospective_authorities WHERE id=?', (request['basis']['prospective']['id'],))
            if (not state or state['hold'] is not None or state['hash'] != anchor['hash']
                    or epoch != request['basis']['prospective'] or not amendment and json.loads(epoch['selection'])['expires'] <= runtime.clock()):
                raise Refusal('original return current source/epoch rights changed')
            for board in runtime.processing.boards.values():
                board.verify_authority(runtime)
            row = runtime.attempt(attempt)
            if (row['controller'] != anchor['control']['original']['controller']
                    or hashlib.sha256(row['result'].encode()).hexdigest() != request['basis']['proof']['raw_control_sha256']):
                raise Refusal('original control raw result changed')
            resolution = runtime.input_resolution(event)
            if (previous['attempt'] != attempt or not resolution
                    or resolution['prior'].get('software_processing', {}).get('attempt') != attempt):
                raise Refusal('original control return/resolution mismatch')
            return resolution
        if report_repair.pair_validate(runtime, request['basis'], _continuation=bool(amendment)) != request['basis']['proof']:
            raise Refusal('selected original result/custody changed')
        return _apply_control(runtime, event, attempt)
