"""Explicit stopped-owner code repair for one already queued report.

No configuration/authority epoch is rewritten. This receipt changes only public
code pins at the SAME release location. Existing IDs, boundaries, finite grants,
charges, collectors, unknown effects and unselected duties retain their meaning.
"""
import json
from pathlib import Path

from .contracts import Refusal, digest, encode, required_text
from . import configuration

SCHEMA = """
CREATE TABLE IF NOT EXISTS collected_report_repairs(
 capability TEXT PRIMARY KEY,request TEXT NOT NULL,issuer TEXT NOT NULL,created REAL NOT NULL);
CREATE TRIGGER IF NOT EXISTS collected_report_repairs_no_update BEFORE UPDATE ON collected_report_repairs
 BEGIN SELECT RAISE(ABORT,'immutable collected report repair'); END;
CREATE TRIGGER IF NOT EXISTS collected_report_repairs_no_delete BEFORE DELETE ON collected_report_repairs
 BEGIN SELECT RAISE(ABORT,'immutable collected report repair'); END;
"""
# This interface cannot select policy, templates, SDK, provider or scheduler
# changes. A different repair requires a separate decision/interface.
MODULES = {'software.py', 'local_integration.py', 'store.py', 'processing.py',
           'configuration.py', 'cli.py', 'report_repair.py'}


def record(runtime, key):
    if not runtime.one("SELECT name FROM sqlite_master WHERE name='collected_report_repairs'"):
        return None
    row = runtime.one('SELECT * FROM collected_report_repairs WHERE capability=?', (key,))
    return json.loads(row['request']) if row else None


def pins(runtime, key, selection, implementation):
    receipt = record(runtime, key)
    if not receipt:
        return False
    basis = receipt['basis']
    return (basis['configuration'] == digest(runtime.config)
            and basis['selection_hash'] == digest(selection)
            and basis['old_implementation'] == selection['basis']['implementation']
            and basis['implementation'] == implementation)


def selected_release(runtime):
    if not runtime.processing:
        return None
    receipt = record(runtime, runtime.processing.key)
    if not receipt or receipt['basis']['configuration'] != digest(runtime.config):
        return None
    cap = runtime.one('SELECT selection,revoked FROM processing_capabilities WHERE id=?', (runtime.processing.key,))
    if not cap or cap['revoked'] is not None or digest(json.loads(cap['selection'])) != receipt['basis']['selection_hash']:
        return None
    return receipt['basis']['release']


def compatible(before, after):
    if set(before) != set(after) or any(before[k] != after[k] for k in before if k != 'files'):
        raise Refusal('report repair keeps exact release location, pool and non-code dependencies')
    old, new = before['files'], after['files']
    module_root = Path(before['root'])/'tools/coordinator-runtime/coordinator_runtime'
    allowed = {str(module_root/name) for name in MODULES}
    if set(old) - set(new) or set(new) - set(old) - {str(module_root/'report_repair.py')}:
        raise Refusal('report repair cannot remove or add unrelated release sources')
    changes = {p for p in new if new[p] != old.get(p)}
    if not changes or changes - allowed:
        raise Refusal('report repair permits only its exact coordinator report/interface code delta')
    return sorted(changes)


def owner(runtime, boards, actor):
    if actor != runtime.config['roles']['Work']['owner']:
        raise Refusal('actual current Work alone selects a collected report code repair')
    return boards['Work'].store.acting_session(actor)


def stopped_original(runtime, key, controller):
    run = runtime.one('SELECT * FROM processing_runs WHERE controller=? AND capability=?', (controller, key))
    service = runtime.one('SELECT state,returned FROM service_runs WHERE controller=? AND capability=?', (controller, key))
    try:
        receipt = json.loads(run['state'])['parent_END'] if run else None
    except (ValueError, KeyError, TypeError):
        receipt = None
    if (not receipt or type(receipt.get('actual_END')) is not int or not receipt.get('evidence')
            or not service or service['state'] != 'returned-awaiting-parent-END' or service['returned'] is None
            or runtime.one('SELECT id FROM attempts WHERE controller=? AND collected IS NULL LIMIT 1', (controller,))):
        raise Refusal('repair requires genuine stop, SAME parent-collected numeric END and original processing-release')


def report(runtime, key, event, controller, selection):
    """Acquire just the selected report and its original producer/member chain."""
    from .software import collected_report
    from .contracts import collected_task_result
    state = runtime.one('SELECT hash,hold,state FROM events WHERE id=?', (event,))
    queue = runtime.one('SELECT * FROM queue WHERE event=?', (event,))
    if (not state or state['hold'] or not queue or queue['state'] != 'queued' or queue['job'] is not None
            or queue['task'] not in selection['tasks']):
        raise Refusal('repair requires the exact unheld already-queued unstarted consumer')
    value = runtime.event(event)
    position = runtime.one('SELECT position FROM processing_source_positions WHERE event=?', (event,))
    if (not position or position['position'] <= selection['basis']['event_boundary']
            or not configuration.event_allowed(runtime, value) or state['hash'] != digest(value)
            or not value.get('source_job') or value.get('source_delivery') or value.get('processing_report')):
        raise Refusal('repair is only an original current internal report, never historical/source replacement')
    source = runtime.job(value['source_job'])
    attempt = runtime.attempt(source['active_attempt'])
    if (source['controller'] != controller or attempt['controller'] != controller
            or source['response'] != event or event != digest({'response':attempt['id']})
            or json.loads(attempt['detail']).get('processing_capability') != key
            or value.get('source_attempt') != attempt['id'] or value.get('source_role') != source['role']
            or value.get('source_members') != json.loads(source['members'])
            or value.get('body') != collected_task_result(attempt)
            or not collected_report(runtime, source, queue['task'])):
        raise Refusal('repair cannot qualify a foreign/uncollected/held producer or altered report')
    return {'event':event, 'hash':state['hash'], 'position':position['position'], 'queue':queue,
            'producer':source, 'attempt':{k:attempt[k] for k in (
                'id','controller','session','begin','ended','collected','exit','capture','error')},
            'result_hash':digest(value['body'])}


def basis(runtime, boards, key, event, controller, actor):
    from . import processing
    owner(runtime, boards, actor)
    configuration.assert_current(runtime)
    cap = runtime.one('SELECT * FROM processing_capabilities WHERE id=?', (key,))
    if not cap or cap['revoked'] is not None or cap['issuer'] != actor:
        raise Refusal('repair requires the same genuine unrevoked Work processing capability')
    selection = json.loads(cap['selection'])
    if ('service' not in selection or selection['basis']['configuration'] != digest(runtime.config)
            or not selection['future_intake']):
        raise Refusal('repair requires unchanged continuing config/authority; no finite grant conversion')
    stopped_original(runtime, key, controller)
    transition = configuration.selected(runtime)
    if not transition:
        raise Refusal('repair requires an existing immutable selected release')
    before = transition['basis']['release']
    after = configuration.release(runtime, runtime.config)
    changed = compatible(before, after)
    implementation = processing.implementation()
    old = selection['basis']['implementation']
    if (set(old) - set(implementation) or set(implementation) - set(old) - {'report_repair.py'}
            or {p for p in implementation if implementation[p] != old.get(p)} - MODULES):
        raise Refusal('repair implementation exceeds exact compatible report code')
    # No global source body inventory or history rehash. Original grants are
    # checked by their supported metadata binding; exact source rights below.
    grants = {}
    for role, board in boards.items():
        with board.opened(settlement=True) as conn:
            grant = board._original(conn, runtime)
            binding = board._binding(grant)
            if binding != selection['basis']['roles'][role]['original']['binding']:
                raise Refusal('repair cannot renew or replace an original grant')
            grants[role] = binding
    epoch = runtime.one('SELECT * FROM prospective_authorities WHERE revoked IS NULL')
    return {'configuration':digest(runtime.config), 'capability':key, 'controller':controller,
            'selection_hash':digest(selection), 'starts':cap['starts'], 'grants':grants,
            'prospective':epoch, 'old_release':before, 'release':after,
            'old_implementation':old, 'implementation':implementation, 'changed':changed,
            'report':report(runtime, key, event, controller, selection)}


def apply(runtime, boards, actor, request):
    from . import processing, local_integration
    if not isinstance(request, dict) or set(request) != {'basis','authority','evidence'}:
        raise Refusal('exact repair basis, genuine Work purpose and reviewed evidence required')
    owner(runtime, boards, actor)
    required_text(request['authority'], 'Work report-repair decision', 4000)
    if not isinstance(request['evidence'], list) or not request['evidence']:
        raise Refusal('reviewed exact code repair evidence required; Maker tests are not independent acceptance')
    for item in request['evidence']:
        required_text(item, 'actual review/qualification evidence', 4000)
    selected = request['basis']
    key = selected['capability']
    with configuration.stopped(runtime), runtime.tx():
        previous = record(runtime, key)
        if previous:
            if previous != request or selected_release_for(runtime, key, boards) != selected['release']:
                raise Refusal('repair already selected differently or pins changed; no automatic replacement')
            return receipt(key, selected)  # Even after reservation: never rerun producer or charge again.
        if basis(runtime, boards, key, selected['report']['event'], selected['controller'], actor) != selected:
            raise Refusal('repair source/queue/rights/pins/accounting changed; take a fresh bounded basis')
        runtime.budget(None, len(encode(request).encode()) + 1024)
        runtime.db.execute('INSERT INTO collected_report_repairs VALUES(?,?,?,?)',
                           (key, encode(request), actor, runtime.clock()))
        old_access = runtime.processing
        runtime.processing = processing.Access(runtime, key, boards)
        try:
            runtime.processing.current()
            source = runtime.event(selected['report']['event'])
            local_integration.input_authority(runtime, source, selected['report']['queue']['task'], source['package'])
        finally:
            runtime.processing = old_access
    return receipt(key, selected)


def selected_release_for(runtime, key, boards):
    from .processing import Access
    old = runtime.processing
    runtime.processing = Access(runtime, key, boards)
    try:
        runtime.processing.current()
        return configuration.release(runtime, runtime.config)
    finally:
        runtime.processing = old


def receipt(key, selected):
    return {'capability':key, 'event':selected['report']['event'], 'queue':selected['report']['queue']['id'],
            'configuration':selected['configuration'], 'producer_replay':False,
            'meaning':'same authority and queued consumer; code pins only; no acceptance, debt reset or capacity renewal'}
