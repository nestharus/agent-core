"""Work-attributed, exact no-new-work control interpretation; no native receipt.

This deliberately requires an authenticated Work interpretation. It does not
infer obligation ownership from prose, semantic DONE, or an empty array.
"""
import json

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


def metadata(runtime, event, attempt, request):
    cap, _ = runtime.processing.current()
    keys = {'schema','event','source_hash','received','attempt','result_hash',
            'resolution_version','scope','accounting','evidence','completed_consumer'}
    if (not isinstance(request, dict) or set(request) != keys
            or request['schema'] != VERSION or request['event'] != event
            or request['attempt'] != attempt
            or request['scope'] != 'no-new-owned-work-or-effects'
            or type(request['resolution_version']) is not int):
        raise Refusal('exact typed plain-control scope and pins required')
    row = runtime.one('SELECT id,hash,received,hold,role FROM events WHERE id=?', (event,))
    if row:
        for role in {'Work', row['role']}:
            runtime.processing.boards[role].verify_authority(runtime)
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
            or queue['phase'] != 'control' or queue['task'] not in ('@control','@unresolved')):
        raise Refusal('plain control cannot bypass an actual task or reservation')
    returned = runtime.one('SELECT source,response,attempt FROM processing_control_returns WHERE source=?', (event,))
    if request['completed_consumer'] != (returned['response'] if returned else None):
        raise Refusal('exact existing control consumer must be accounted')
    descendants = runtime.rows('WITH RECURSIVE d(id) AS (SELECT id FROM events WHERE parent=? '
        'UNION SELECT e.id FROM events e JOIN d ON e.parent=d.id) '
        'SELECT e.id,e.processed_at,e.hold FROM events e JOIN d ON e.id=d.id', (event,))
    if descendants and (not returned or any(d['processed_at'] is None or d['hold'] is not None for d in descendants)):
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
                "JOIN queue q ON q.job=a.job WHERE q.event=? AND fp.state!='published'", (child,)):
            raise Refusal('completed consumer retains an unresolved publication')
    if runtime.one('SELECT j.id FROM jobs j,json_each(j.members) m WHERE json_extract(m.value,\'$.event\')=?', (event,)):
        raise Refusal('plain control cannot settle real work or uncertain effects')
    if runtime.one("SELECT id FROM outboxes WHERE event=? AND (state!='settled' OR processed_at IS NULL OR hold IS NOT NULL)", (event,)):
        raise Refusal('plain control cannot settle outstanding delivery/effect duties')
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
    receipt = json.loads(result['decision_json'])
    from .processing import validate_control_result
    validate_control_result(result, receipt)
    if (result['semantic'] != 'DONE' or digest(result) != request['result_hash']
            or receipt.get('mode') != 'control'
            or any(receipt.get(k) is not None for k in ('task','package','related_event','related_job'))):
        raise Refusal('plain control requires genuine no-task control interpretation')
    runtime.processing.control_proof(event, attempt, receipt)
    source = runtime.event(event)
    if digest(source) != row['hash'] or source['kind'] != 'board' or not runtime.processing.event(source):
        raise Refusal('plain control requires exact selected Board source')
    from .capacity import notification
    if notification(runtime, source):
        raise Refusal('authenticated notification keeps its occurrence/cause contract')
    accounting = request['accounting']
    obligations = receipt['remaining_obligations']
    if not isinstance(accounting, list) or len(accounting) != len(obligations) or len(accounting) > 32:
        raise Refusal('every original obligation requires lossless exact owner/source accounting')
    for index, (entry, text) in enumerate(zip(accounting, obligations)):
        if (not isinstance(entry, dict) or set(entry) != {'index','text','disposition','owner','event','source_hash','evidence'}
                or type(entry['index']) is not int or entry['index'] != index or entry['text'] != text
                or entry['disposition'] != 'conserved-at-original-source' or entry['event'] == event):
            raise Refusal('unknown or message-owned obligations cannot be terminalized')
        original = runtime.one('SELECT role,hash FROM events WHERE id=?', (entry['event'],))
        if (not original or original['hash'] != entry['source_hash']
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


def apply(runtime, event, attempt, request):
    """Supported atomic API, authenticated as Work; leaves fresh classifier due.

    Existing pending Work consumers refuse. This version never manufactures a
    control-only receipt for an unprocessed response or removes its edge.
    """
    validate(runtime, event, attempt, request)
    with runtime.tx():
        actor = validate(runtime, event, attempt, request)
        previous = runtime.one('SELECT * FROM plain_control_dispositions WHERE event=?', (event,))
        if previous:
            if (previous['request'] != encode(request)
                    or previous['capability'] != runtime.processing.key
                    or previous['actor'] != actor
                    or previous['resolution_hash'] != digest(runtime.input_resolution(event))):
                raise Refusal('plain control already has a different disposition')
            return previous
        from .processing import _apply_control
        resolution = _apply_control(runtime, event, attempt, terminal_request=request)
        runtime.budget(None, len(encode(request).encode()) + 1024)
        runtime.db.execute('INSERT INTO plain_control_dispositions VALUES(?,?,?,?,?,?,?,?)',
            (event,resolution['version'],request['source_hash'],runtime.processing.key,actor,
             encode(request),digest(resolution),runtime.clock()))
        return runtime.one('SELECT * FROM plain_control_dispositions WHERE event=?', (event,))
