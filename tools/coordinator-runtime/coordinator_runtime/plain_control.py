"""Work-attributed, exact no-new-work control interpretation; no native receipt.

This deliberately requires an authenticated Work interpretation. It does not
infer obligation ownership from prose, semantic DONE, or an empty array.
"""
import json
import math

from .contracts import Refusal, digest, encode, required_text

VERSION = 'plain-control-terminal-v1'
SCHEMA = """
CREATE TABLE IF NOT EXISTS plain_control_dispositions(
 event TEXT PRIMARY KEY,version INTEGER NOT NULL,source_hash TEXT NOT NULL,
 capability TEXT NOT NULL,actor TEXT NOT NULL,request TEXT NOT NULL,
 resolution_hash TEXT NOT NULL,created REAL NOT NULL);
CREATE TRIGGER IF NOT EXISTS plain_control_immutable_update BEFORE UPDATE ON plain_control_dispositions
 BEGIN SELECT RAISE(ABORT,'immutable plain control disposition'); END;
CREATE TRIGGER IF NOT EXISTS plain_control_immutable_delete BEFORE DELETE ON plain_control_dispositions
 BEGIN SELECT RAISE(ABORT,'immutable plain control disposition'); END;
"""


def selected_metadata(runtime, event):
    """Scalar selection checks before any original body/result acquisition."""
    _, selection = runtime.processing.current()
    row = runtime.one('SELECT id,hash,received,hold,role,classifier,state FROM events WHERE id=?', (event,))
    position = runtime.one('SELECT position FROM processing_source_positions WHERE event=?', (event,))
    originals = {e['id']:e['hash'] for r in selection['basis']['roles'].values() for e in r['original']['events']}
    if (not row or not position or row['role'] not in selection['basis']['roles']
            or (event in selection['retained_events'] and originals.get(event) != row['hash'])
            or (event not in selection['retained_events'] and
                (not selection['future_intake'] or position['position'] <= selection['basis']['event_boundary']))):
        raise Refusal('exact current processing source metadata required before body')
    if row:
        for role in {'Work', row['role']}:
            runtime.processing.boards[role].verify_authority(runtime)
    from .configuration import event_candidate_scope
    predicate, parameters = event_candidate_scope(runtime)
    if not runtime.one('SELECT e.id FROM events e WHERE e.id=? AND ('+predicate+')',(event,*parameters)):
        raise Refusal('source excluded by current source/birth selection before body')
    from .selected_source import selected_pins
    for pin in selected_pins(selection):
        if pin['event'] == event:
            birth = runtime.one('SELECT position FROM processing_source_positions WHERE event=?',(event,))
            if not birth or birth['position'] != pin['source_birth'] or row['hash'] != pin['source_hash'] or row['role'] != pin['role']:
                raise Refusal('exact selected source pins changed before body')
    return row, position['position']


def basis(runtime, event):
    """Authorized exact metadata, not an interpretation or eligibility receipt."""
    with runtime.tx():
        row, birth = selected_metadata(runtime, event)
        control = runtime.one('SELECT event,capability,attempt,source_hash FROM processing_controls WHERE event=?',(event,))
        if not control or control['source_hash'] != row['hash']:
            raise Refusal('exact existing control metadata required')
        returned = runtime.one('SELECT source,response,attempt FROM processing_control_returns WHERE source=?',(event,))
        child = None
        if returned:
            child, child_birth = selected_metadata(runtime, returned['response'])
            child = dict(source=child, source_birth=child_birth, payload_hash=child['hash'],
                         responsibility=runtime.one('SELECT * FROM queue WHERE event=?',(child['id'],)))
        runtime.processing.current()
        return dict(schema='plain-control-basis-v1',source=row,source_birth=birth,control=control,
                    responsibility=runtime.one('SELECT * FROM queue WHERE event=?',(event,)),
                    control_return=returned,consumer=child,
                    meaning='metadata pins only; whole original source/result and all current guards still required')


def metadata(runtime, event, attempt, request):
    cap, _ = runtime.processing.current()
    keys = {'schema','event','source_hash','received','attempt','result_hash',
            'resolution_version','scope','accounting','evidence','completed_consumer'}
    optional = {'consumer_disposition','authority'}
    if (not isinstance(request, dict) or set(request) - optional != keys
            or request['schema'] != VERSION or request['event'] != event
            or request['attempt'] != attempt
            or request['scope'] != 'no-new-owned-work-or-effects'
            or type(request['resolution_version']) is not int):
        raise Refusal('exact typed plain-control scope and pins required')
    row, _ = selected_metadata(runtime, event)
    control = runtime.one('SELECT event,capability,attempt,source_hash FROM processing_controls WHERE event=?', (event,))
    worker = runtime.one('SELECT kind,event,begin,ended,collected,exit,error,capture FROM attempts WHERE id=?', (attempt,))
    if (not row or row['hold'] is not None or row['hash'] != request['source_hash']
            or row['received'] != request['received'] or not control
            or control['attempt'] != attempt or control['source_hash'] != row['hash']
            or not worker or worker['event'] != event or worker['kind'] != 'input-control'
            or any(worker[k] is None for k in ('begin','ended','collected'))
            or worker['exit'] != 0 or worker['error'] or worker['capture'] != 'complete'):
        raise Refusal('plain control requires exact unheld collected original before body')
    queue = runtime.one('SELECT * FROM queue WHERE event=?', (event,))
    if (not queue or queue['job'] is not None or queue['package'] is not None
            or queue['state'] not in ('queued','awaiting-owner','owner-resolution-pending','done')
            or queue['phase'] != 'control' or queue['task'] not in ('@control','@unresolved')):
        raise Refusal('plain control cannot bypass an actual task or reservation')
    returned = runtime.one('SELECT source,response,attempt FROM processing_control_returns WHERE source=?', (event,))
    if returned and returned['attempt'] != attempt:
        raise Refusal('control return must retain its exact original attempt')
    if request['completed_consumer'] != (returned['response'] if returned else None):
        raise Refusal('exact existing control consumer must be accounted')
    consumer = request.get('consumer_disposition')
    pending_consumer = consumer_metadata(runtime, event, returned, consumer) if consumer else None
    descendants = runtime.rows('WITH RECURSIVE d(id) AS (SELECT id FROM events WHERE parent=? '
        'UNION SELECT e.id FROM events e JOIN d ON e.parent=d.id) '
        'SELECT e.id,e.processed_at,e.hold FROM events e JOIN d ON e.id=d.id', (event,))
    if descendants and (not returned or any((d['processed_at'] is None and d['id'] != pending_consumer) or d['hold'] is not None for d in descendants)):
        raise Refusal('actual control consumer and descendants must already be complete')
    for descendant in descendants:
        child = descendant['id']
        if runtime.one("SELECT o.id FROM outboxes o LEFT JOIN queue q ON q.job=o.job "
                "WHERE (o.event=? OR q.event=?) AND (o.state!='settled' OR o.processed_at IS NULL OR o.hold IS NOT NULL)", (child,child)):
            raise Refusal('completed consumer retains an outstanding delivery/effect duty')
        if runtime.one("SELECT j.id FROM jobs j,json_each(j.members) m WHERE json_extract(m.value,'$.event')=? "
                "AND (j.state!='closed' OR j.effects NOT IN ('none','reconciled') OR j.hold_reason IS NOT NULL)", (child,)):
            raise Refusal('completed consumer retains real work or effect uncertainty')
        if runtime.one("SELECT fp.target FROM file_publications fp JOIN attempts a ON a.id=fp.attempt "
                "LEFT JOIN queue q ON q.job=a.job WHERE (a.event=? OR q.event=?) AND fp.state!='published'", (child,child)):
            raise Refusal('completed consumer retains an unresolved publication')
    if runtime.one('SELECT j.id FROM jobs j,json_each(j.members) m WHERE json_extract(m.value,\'$.event\')=?', (event,)):
        raise Refusal('plain control cannot settle real work or uncertain effects')
    if runtime.one("SELECT id FROM outboxes WHERE event=? AND (state!='settled' OR processed_at IS NULL OR hold IS NOT NULL)", (event,)):
        raise Refusal('plain control cannot settle outstanding delivery/effect duties')
    classifier = runtime.one('SELECT collected FROM attempts WHERE id=?', (row['classifier'],)) if row['classifier'] else None
    if classifier and classifier['collected'] is None:
        raise Refusal('original classifier remains with its collector')
    if runtime.one("SELECT fp.target FROM file_publications fp JOIN attempts a ON a.id=fp.attempt WHERE a.event=? AND fp.state!='published'", (event,)):
        raise Refusal('source publication remains unresolved')
    if len(encode(request).encode()) > runtime.config['limits']['max_result_bytes']:
        raise Refusal('plain-control interpretation exceeds admitted result bound')
    return cap, row


def validate(runtime, event, attempt, request, *, authenticate=True):
    cap, row = metadata(runtime, event, attempt, request)
    if authenticate:
        actor = runtime.processing.boards['Work'].store.acting_session(runtime.config['software_delegation']['grantor'])
        if actor != cap['issuer']:
            raise Refusal('plain-control interpretation belongs to actual current Work issuer')
    else:
        actor = cap['issuer']
    if not isinstance(request['evidence'], list) or not 1 <= len(request['evidence']) <= 32:
        raise Refusal('whole-source Work interpretation evidence required')
    for evidence in request['evidence']:
        required_text(evidence, 'Work interpretation evidence', 4000)
    worker = runtime.attempt(attempt)
    result = json.loads(worker['result'])
    if 'authority' in request:
        raw = json.loads(result['decision_json'])
        if (request['authority'] != software_authority(cap,worker,result)
                or raw.get('plain_control') != {k:request[k] for k in ('scope','accounting','evidence')}
                or request.get('consumer_disposition')
                or any('attestation' in e for e in request['accounting'])):
            raise Refusal('software disposition must be the exact actually collected scope interpretation')
        actor = worker['session']
    receipt = json.loads(result['decision_json'])
    from .processing import control_receipt, validate_control_result
    validate_control_result(result, receipt)
    if result['semantic'] != 'DONE' or digest(result) != request['result_hash']:
        raise Refusal('plain control requires the exact original DONE result before source body')
    runtime.processing.control_proof(event, attempt, receipt)
    receipt, _ = control_receipt(runtime, event, worker, result, receipt)
    if (receipt.get('mode') != 'control'
            or any(receipt.get(k) is not None for k in ('task','package','related_event','related_job'))):
        raise Refusal('plain control requires genuine no-task control interpretation')
    source = runtime.event(event)
    if digest(source) != row['hash'] or source['kind'] != 'board' or not runtime.processing.event(source):
        raise Refusal('plain control requires exact selected Board source')
    from .capacity import notification
    if notification(runtime, source):
        raise Refusal('authenticated notification keeps its occurrence/cause contract')
    returned = runtime.one('SELECT * FROM processing_control_returns WHERE source=?', (event,))
    if request.get('consumer_disposition'):
        consumer_body(runtime, event, returned, request['consumer_disposition'])
    accounting = request['accounting']
    obligations = receipt['remaining_obligations']
    if not isinstance(accounting, list) or len(accounting) != len(obligations) or len(accounting) > 32:
        raise Refusal('every original obligation requires lossless exact owner/source accounting')
    for index, (entry, text) in enumerate(zip(accounting, obligations)):
        if (not isinstance(entry, dict) or set(entry) - {'attestation'} != {'index','text','disposition','owner','event','source_hash','evidence'}
                or type(entry['index']) is not int or entry['index'] != index or entry['text'] != text
                or entry['disposition'] != 'conserved-at-original-source' or entry['event'] == event):
            raise Refusal('unknown or message-owned obligations cannot be terminalized')
        original = runtime.one('SELECT role,hash FROM events WHERE id=?', (entry['event'],))
        if 'attestation' in entry:
            attestation = entry['attestation']
            owners = {runtime.enrollment(r)['owner'] for r in runtime.config['roles']}
            if (not isinstance(attestation, dict) or set(attestation) != {'reference','observed'}
                    or type(attestation['observed']) not in (int,float)
                    or not math.isfinite(attestation['observed'])
                    or attestation['observed'] > runtime.clock()
                    or (not runtime.one('SELECT event FROM plain_control_dispositions WHERE event=?',(event,)) and runtime.clock() - attestation['observed'] > 300)
                    or entry['owner'] not in owners or not isinstance(entry['source_hash'], str)
                    or len(entry['source_hash']) != 64 or any(c not in '0123456789abcdef' for c in entry['source_hash'])):
                raise Refusal('exact current Work-attested source/owner evidence required')
            required_text(attestation['reference'], 'exact external original source reference', 4000)
            required_text(entry['event'], 'exact original source identity', 4000)
        elif (not original or original['hash'] != entry['source_hash']
                or runtime.enrollment(original['role'])['owner'] != entry['owner']):
            raise Refusal('conserved duty requires exact existing source and actual owner')
        required_text(entry['evidence'], 'obligation scope evidence', 4000)
    resolution = runtime.input_resolution(event)
    if resolution:
        if resolution['version'] != request['resolution_version'] or resolution['receipt'] != receipt:
            raise Refusal('stale or different applied control resolution')
    elif request['resolution_version'] != 1:
        raise Refusal('exact initial resolution version required')
    runtime.processing.current()
    return actor


def apply(runtime, event, attempt, request, *, software=False):
    """Supported atomic API, authenticated as Work; leaves fresh classifier due.

    An existing unreserved return needs a separate whole-payload Work receipt.
    Its original edge, bytes and descendants remain under ordinary completion.
    """
    if software and ('authority' not in request or any('attestation' in entry for entry in request.get('accounting', []))):
        raise Refusal('automatic software interpretation cannot attest external Work evidence')
    validate(runtime, event, attempt, request, authenticate=not software)
    with runtime.tx():
        actor = validate(runtime, event, attempt, request, authenticate=not software)
        previous = runtime.one('SELECT * FROM plain_control_dispositions WHERE event=?', (event,))
        if previous:
            if (previous['request'] != encode(request)
                    or previous['capability'] != runtime.processing.key
                    or previous['actor'] != actor
                    or previous['resolution_hash'] != digest(runtime.input_resolution(event))):
                raise Refusal('plain control already has a different disposition')
            return previous
        from .processing import _apply_control
        resolution = _apply_control(runtime, event, attempt, terminal_request=request, software_terminal=software)
        runtime.budget(None, len(encode(request).encode()) + 1024)
        runtime.db.execute('INSERT INTO plain_control_dispositions VALUES(?,?,?,?,?,?,?,?)',
            (event,resolution['version'],request['source_hash'],runtime.processing.key,actor,
             encode(request),digest(resolution),runtime.clock()))
        if request.get('consumer_disposition'):
            child = request['completed_consumer']
            consumer_metadata(runtime, event, runtime.one('SELECT * FROM processing_control_returns WHERE source=?',(event,)), request['consumer_disposition'])
            runtime.db.execute("UPDATE queue SET state='done' WHERE event=? AND job IS NULL", (child,))
        # An already-applied resolution needs a fresh collected classifier too.
        state = runtime.one('SELECT processed_at FROM events WHERE id=?',(event,))
        if state['processed_at'] is None:
            runtime.db.execute("UPDATE events SET state='received' WHERE id=?",(event,))
            runtime.db.execute("UPDATE queue SET state='owner-resolution-pending' WHERE event=?",(event,))
        return runtime.one('SELECT * FROM plain_control_dispositions WHERE event=?', (event,))


def consumer_metadata(runtime, source, returned, receipt):
    """Only an exact unreserved Work control return; never a running job takeover."""
    keys = {'schema','event','source_hash','received','scope','payload_hash','evidence'}
    if (not returned or not isinstance(receipt, dict) or set(receipt) != keys
            or receipt['schema'] != 'plain-control-consumer-v1'
            or receipt['event'] != returned['response']
            or receipt['scope'] != 'whole-return-no-new-owned-work-or-effects'):
        raise Refusal('exact genuine whole-return control consumer disposition required')
    child, _ = selected_metadata(runtime, returned['response'])
    link = runtime.one('SELECT parent,ack FROM events WHERE id=?',(child['id'],))
    queue = runtime.one('SELECT * FROM queue WHERE event=?',(returned['response'],))
    eligible = queue and ((queue['task'] == 'work-proposer' and queue['state'] in ('queued','done'))
                         or (queue['task'] == '@unresolved' and queue['phase'] == 'control'
                             and queue['state'] in ('awaiting-owner','done')))
    if (link['parent'] != source or child['role'] != 'Work' or child['hold'] is not None
            or child['hash'] != receipt['source_hash'] or child['received'] != receipt['received']
            or not queue or queue['job'] is not None or queue['package'] is not None
            or queue['role'] != 'Work' or not eligible or child['state'] == 'received'
            or link['ack'] not in ('done','plain','internal')
            or runtime.one("SELECT j.id FROM jobs j,json_each(j.members) m WHERE json_extract(m.value,'$.event')=?",(child['id'],))
            or runtime.one('SELECT id FROM events WHERE parent=? AND (processed_at IS NULL OR hold IS NOT NULL)',(child['id'],))
            or runtime.input_resolution(child['id'])):
        raise Refusal('consumer has actual work, pending descendant, hold or reservation')
    classifier = runtime.one('SELECT kind,event,state,ended,collected,exit,error,capture FROM attempts '
                             "WHERE id=? AND json_extract(detail,'$.processing_capability')=?",
                             (child['classifier'],runtime.processing.key))
    if (not classifier or classifier['kind'] not in ('classifier','diagnosis')
            or classifier['event'] != child['id'] or classifier['state'] != 'collected'
            or classifier['ended'] is None or classifier['collected'] is None
            or classifier['exit'] != 0 or classifier['error'] or classifier['capture'] != 'complete'):
        raise Refusal('consumer needs its own collected classifier and ACK')
    if not isinstance(receipt['evidence'],list) or not 1 <= len(receipt['evidence']) <= 32:
        raise Refusal('whole original payload/history interpretation required')
    for evidence in receipt['evidence']:required_text(evidence,'whole-return handling evidence',4000)
    return child['id']


def consumer_body(runtime, source, returned, receipt):
    child = runtime.event(returned['response'])
    payload = json.loads(returned['payload'])
    control = runtime.one('SELECT attempt FROM processing_controls WHERE event=?',(source,))
    worker = runtime.attempt(control['attempt'])
    if (child != payload or digest(child) != receipt['source_hash'] or digest(payload) != receipt['payload_hash']
            or child.get('processing_control_return') != {'source':source,'attempt':control['attempt']}
            or child['body'] != {'source':runtime.event(source),'actual_worker_return':json.loads(worker['result']),
                                'software_resolution':runtime.input_resolution(source),'native_owner_receipt':False}
            or not runtime.processing.event(child)):
        raise Refusal('whole original consumer payload/history differs')


def accepted(runtime, event):
    row = runtime.one('SELECT * FROM plain_control_dispositions WHERE event=?',(event,))
    if not row:return False
    request = json.loads(row['request'])
    try:
        actor = validate(runtime,event,request['attempt'],request,authenticate=False)
        return (row['actor'] == actor and row['capability'] == runtime.processing.key
                and row['resolution_hash'] == digest(runtime.input_resolution(event)))
    except (Refusal,ValueError,TypeError):
        return False


def automatic(runtime, event, attempt):
    """Use only an explicit structured decision from the actually collected worker."""
    runtime.processing.current()
    state = runtime.one("SELECT ended,collected,exit,capture,error FROM attempts WHERE id=?",(attempt,))
    if (not state or state["ended"] is None or state["collected"] is None or state["exit"] != 0
            or state["capture"] != "complete" or state["error"]):
        raise Refusal("automatic control requires actual successful original collection")
    worker = runtime.attempt(attempt)
    result = json.loads(worker['result'] or 'null')
    raw = json.loads(result['decision_json']) if isinstance(result,dict) else None
    if not isinstance(raw,dict) or 'plain_control' not in raw:return None
    scope = raw['plain_control']
    if not isinstance(scope,dict) or set(scope) != {'scope','accounting','evidence'}:
        raise Refusal('unknown automatic plain control scope')
    if runtime.one('SELECT source FROM processing_control_returns WHERE source=?',(event,)):
        raise Refusal('existing return needs a specific genuine Work consumer receipt')
    row = runtime.one('SELECT hash,received FROM events WHERE id=?',(event,))
    resolution = runtime.input_resolution(event)
    request = dict(schema=VERSION,event=event,source_hash=row['hash'],received=row['received'],
        attempt=attempt,result_hash=digest(result),resolution_version=resolution['version'] if resolution else 1,
        completed_consumer=None,authority=software_authority(runtime.processing.current()[0],worker,result),**scope)
    return apply(runtime,event,attempt,request,software=True)


def software_authority(cap, worker, result):
    return dict(kind='collected-software-control',issuer=cap['issuer'],worker=worker['session'],
                controller=worker['controller'],attempt=worker['id'],collected=worker['collected'],
                result_hash=digest(result),native_owner_receipt=False)
