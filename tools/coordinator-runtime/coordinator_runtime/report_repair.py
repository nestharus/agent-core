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
CREATE TABLE IF NOT EXISTS same_authority_source_repairs_v1(
 capability TEXT PRIMARY KEY,request TEXT NOT NULL,issuer TEXT NOT NULL,created REAL NOT NULL);
CREATE TRIGGER IF NOT EXISTS source_repairs_v1_no_update BEFORE UPDATE ON same_authority_source_repairs_v1
 BEGIN SELECT RAISE(ABORT,'immutable same authority source repair'); END;
CREATE TRIGGER IF NOT EXISTS source_repairs_v1_no_delete BEFORE DELETE ON same_authority_source_repairs_v1
 BEGIN SELECT RAISE(ABORT,'immutable same authority source repair'); END;
CREATE TABLE IF NOT EXISTS same_authority_report_control_repairs_v2(
 capability TEXT PRIMARY KEY,request TEXT NOT NULL,issuer TEXT NOT NULL,created REAL NOT NULL);
CREATE TRIGGER IF NOT EXISTS report_control_v2_no_update BEFORE UPDATE ON same_authority_report_control_repairs_v2
 BEGIN SELECT RAISE(ABORT,'immutable report control repair'); END;
CREATE TRIGGER IF NOT EXISTS report_control_v2_no_delete BEFORE DELETE ON same_authority_report_control_repairs_v2
 BEGIN SELECT RAISE(ABORT,'immutable report control repair'); END;
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
    amendment = lease_record(runtime, key)
    if amendment:
        return lease_identity(runtime, key, selection, amendment) and amendment['basis']['implementation'] == implementation
    paired = pair_record(runtime, key)
    if paired:
        return pair_identity(runtime, key, selection, paired) and paired["basis"]["implementation"] == implementation
    continuing = source_record(runtime, key)
    if continuing:
        return source_pins(runtime, key, selection, implementation, continuing)
    receipt = record(runtime, key)
    if not receipt:
        return False
    basis = receipt['basis']
    return (basis['configuration'] == digest(runtime.config)
            and basis['selection_hash'] == digest(selection)
            and basis['old_implementation'] == selection['basis']['implementation']
            and basis['implementation'] == implementation)


def selected_release(runtime):
    # Paused metadata management has no processing Access. The new protocol
    # may resolve its code pins, but never lends that caller processing rights.
    cap = source_capability(runtime)
    if cap:
        amendment = lease_record(runtime, cap['id'])
        if amendment:
            if not lease_identity(runtime, cap['id'], json.loads(cap['selection']), amendment):
                raise Refusal('owner lease original identity changed')
            return amendment['basis']['release']
        paired = pair_record(runtime, cap['id'])
        if paired:
            if not pair_identity(runtime, cap['id'], json.loads(cap['selection']), paired):
                raise Refusal('report/control repair identity changed')
            return paired['basis']['release']
        request = source_record(runtime, cap['id'])
        selection = json.loads(cap['selection'])
        if request:
            if not source_identity(runtime, cap, selection, request):
                raise Refusal('source repair current capability/configuration/selection identity changed')
            return request['basis']['release']
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
    if source_record(runtime, key) or pair_record(runtime, key) or lease_record(runtime, key):
        raise Refusal('distinct source repair already selected; legacy report repair cannot supersede it')
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


# A distinct, single repair point. Reuse the existing installed module/schema
# loader and pin hooks; no new import footprint or authorize-arbitrary-code flag.
SOURCE_VERSION = 'same-authority-source-repair-v1'
SOURCE_MODULES = {'configuration.py', 'integration.py', 'integration_management.py',
                  'resource_scopes.py', 'cli.py', 'report_repair.py',
                  'local_integration.py', 'store.py'}


def source_record(runtime, key):
    if not runtime.one("SELECT name FROM sqlite_master WHERE name='same_authority_source_repairs_v1'"):
        return None
    row = runtime.one('SELECT request FROM same_authority_source_repairs_v1 WHERE capability=?', (key,))
    return json.loads(row['request']) if row else None


def source_capability(runtime):
    if not runtime.one("SELECT name FROM sqlite_master WHERE name='processing_capabilities'"):
        return None
    if runtime.processing:
        return runtime.one('SELECT * FROM processing_capabilities WHERE id=?', (runtime.processing.key,))
    return runtime.one('SELECT * FROM processing_capabilities WHERE revoked IS NULL')


def source_identity(runtime, cap, selection, request):
    selected = request['basis']
    return (selected['schema'] == SOURCE_VERSION and cap['revoked'] is None
            and cap['id'] == selected['capability'] and cap['issuer'] == runtime.config['roles']['Work']['owner']
            and selected['configuration'] == digest(runtime.config)
            and selection['basis']['configuration'] == selected['configuration']
            and digest(configuration.version_metadata(runtime)) == selected['configuration_version']
            and digest(selection) == selected['selection_hash']
            and selection['basis']['implementation'] == selected['old_implementation'])


def source_pins(runtime, key, selection, implementation, request):
    cap = runtime.one('SELECT * FROM processing_capabilities WHERE id=?', (key,))
    return bool(cap and source_identity(runtime, cap, selection, request)
                and request['basis']['implementation'] == implementation)


def source_compatible(before, after, old, new, modules, *, _ceiling=None):
    if (not isinstance(modules, list) or not modules or any(not isinstance(m, str) for m in modules)
            or modules != sorted(set(modules)) or set(modules) - (SOURCE_MODULES if _ceiling is None else _ceiling)):
        raise Refusal('exact sorted public module delta within source-repair-v1 required')
    if set(before) != set(after) or any(before[k] != after[k] for k in before if k != 'files'):
        raise Refusal('source repair keeps exact release location, hot pool control and non-code dependencies')
    if set(before['files']) != set(after['files']) or set(old) != set(new):
        raise Refusal('source repair cannot add/remove modules or dependencies; no implicit module acquisition')
    root = Path(before['root'])/'tools/coordinator-runtime/coordinator_runtime'
    for name in old:
        path = str(root/name)
        if before['files'].get(path) != old[name] or after['files'].get(path) != new[name]:
            raise Refusal('release and original/current implementation pins must agree')
    changed = sorted(name for name in old if old[name] != new[name])
    paths = sorted(p for p in before['files'] if before['files'][p] != after['files'][p])
    if changed != modules or paths != sorted(str(root/name) for name in modules):
        raise Refusal('source repair requires precisely the selected module delta; templates/policy stay frozen')
    return paths


def source_anchor(runtime, key, event, selection):
    """Explicit queued source metadata only, before any source-body read.

    Recorded hashes are operands, not proof that the current body matches.
    Application authenticates the bytes under real Access and rolls back on
    failure. No payload/error/result inventory or source restamping is used.
    """
    state = runtime.one('SELECT id,role,hash,state,hold IS NOT NULL AS held,processed_at FROM events WHERE id=?', (event,))
    queue = runtime.one('SELECT * FROM queue WHERE event=?', (event,))
    birth = runtime.one('SELECT position FROM processing_source_positions WHERE event=?', (event,))
    if (not state or state['held'] or state['processed_at'] is not None or state['state'] != 'queued'
            or not queue or queue['state'] != 'queued' or queue['job'] is not None or not birth
            or queue['task'] not in selection['tasks'] or queue['role'] != state['role']
            or queue['phase'] != runtime.config['tasks'][queue['task']]['phase']
            or runtime.one('SELECT jobs.id FROM jobs, json_each(jobs.members) AS m '
                           "WHERE json_extract(m.value,'$.event')=? LIMIT 1", (event,))):
        raise Refusal('source repair requires exact unheld queued UNSTARTED source, with no frozen job membership')
    from .selected_source import selected_pins, snapshot
    retained = next((p for p in selected_pins(selection) if p['event'] == event), None)
    if retained:
        mapping = snapshot(runtime, retained)
    else:
        transition = configuration.selected(runtime)
        boundary = max(selection['basis']['event_boundary'], transition['event_boundary'])
        if birth['position'] <= boundary:
            raise Refusal('historical source cannot acquire current code-repair authority')
        mapping = None
    header = runtime.one("SELECT json_extract(payload,'$.kind') AS kind,"
                         "json_extract(payload,'$.processing_report') AS report,"
                         "json_extract(payload,'$.source_job') AS producer,"
                         "json_extract(payload,'$.source_delivery') AS delivery,"
                         "json_extract(payload,'$.processing_capability') AS receiving "
                         'FROM events WHERE id=?', (event,))
    if header['producer'] or header['delivery'] or header['receiving']:
        raise Refusal('source-repair-v1 supports original Board or attributed report anchors only')
    admission = runtime.one('SELECT * FROM processing_admissions WHERE event=?', (event,))
    resolution = runtime.one('SELECT * FROM processing_admission_resolutions WHERE event=?', (event,))
    applied = runtime.one('SELECT * FROM admissions WHERE package=?', (queue['package'],)) if queue['package'] else None
    report_input = runtime.one('SELECT * FROM processing_report_inputs WHERE event=?', (event,))
    route = runtime.one("SELECT version,source_hash,actor,json_extract(receipt,'$.mode') AS mode,"
                        "json_extract(receipt,'$.task') AS task,json_extract(receipt,'$.package') AS package,"
                        "json_extract(prior,'$.integration_observation.packet') AS packet "
                        'FROM input_resolutions WHERE event=? ORDER BY version DESC LIMIT 1', (event,))
    if route and (route['source_hash'] != state['hash'] or route['mode'] != 'route'
                  or route['task'] != queue['task'] or route['package'] != queue['package']):
        raise Refusal('source repair cannot replace a current frozen input mapping')
    if header['kind'] == 'board' and header['report'] is None and report_input is None:
        if queue['package'] is not None and (not admission or not resolution or not applied
                or admission['capability'] != key or resolution['capability'] != key
                or admission['package'] != queue['package'] or resolution['package'] != queue['package']
                or resolution['admission_hash'] != digest(applied) or resolution['source_hash'] != state['hash']):
            raise Refusal('packaged Board source requires unchanged same-capability resolved software admission')
        kind = 'board'
    elif (not retained and header['kind'] == 'response' and header['report'] == key and report_input
            and report_input['capability'] == key and report_input['source_hash'] == state['hash']
            and queue['package'] is None and admission is None and resolution is None):
        kind = 'attributed-report'
    else:
        raise Refusal('source repair requires original Board or whole Work-attributed report metadata')
    return {'event':event, 'hash':state['hash'], 'position':birth['position'], 'kind':kind,
            'queue':queue, 'mapping':mapping, 'route':route, 'admission_hash':digest(admission),
            'resolution':resolution, 'applied_hash':digest(applied), 'report_input':report_input,
            'task_hash':digest(runtime.config['tasks'][queue['task']])}


def source_basis(runtime, boards, key, events, controller, actor, modules, purpose):
    """Caller holds the cooperative stop lock and journal write transaction."""
    from . import processing
    owner(runtime, boards, actor)
    required_text(purpose, 'explicit current Work source-repair purpose', 4000)
    configuration.assert_current(runtime)
    cap = runtime.one('SELECT * FROM processing_capabilities WHERE id=?', (key,))
    if (not cap or cap['revoked'] is not None or cap['issuer'] != actor
            or actor != runtime.config['software_delegation']['grantor']
            or set(boards) != {'Work','Reviews','QA','Branch'} or set(boards) != set(runtime.config['roles'])):
        raise Refusal('same genuine current Work capability and exact four original roles required')
    selection = json.loads(cap['selection'])
    if ('service' not in selection or not selection['future_intake']
            or selection['basis']['configuration'] != digest(runtime.config)):
        raise Refusal('unchanged continuing capability/configuration required; no finite grant conversion')
    if record(runtime, key) or source_record(runtime, key) or pair_record(runtime, key) or lease_record(runtime, key):
        raise Refusal('one distinct source repair point only; no repair stacking or legacy receipt conversion')
    stopped_original(runtime, key, controller)
    if configuration.owned_service_conflict(runtime) or runtime.one(
            "SELECT controller FROM service_runs WHERE capability=? AND (state!='returned-awaiting-parent-END' OR returned IS NULL)", (key,)):
        raise Refusal('no active concurrent collector; every same-capability original must return and release')
    for run in runtime.rows('SELECT controller FROM processing_runs WHERE capability=?', (key,)):
        stopped_original(runtime, key, run['controller'])
    transition = configuration.selected(runtime)
    if not transition:
        raise Refusal('immutable current configuration release selection required')
    before, after = transition['basis']['release'], configuration.release(runtime, runtime.config)
    implementation = processing.implementation()
    changed = source_compatible(before, after, selection['basis']['implementation'], implementation, modules)
    grants = {}
    from .integration_management import _metadata_original
    for role, board in boards.items():
        with board.opened(settlement=True) as conn:
            grant, enrollment = _metadata_original(board, conn, runtime)
            binding = board._binding(grant)
            if (binding != selection['basis']['roles'][role]['original']['binding']
                    or grant['issued_by'] != actor or enrollment['owner'] != board.selected['owner']
                    or enrollment['profile'] != board.selected['profile']):
                raise Refusal('source repair conserves every original stopped software grant binding')
            grants[role] = {'binding':binding, 'enrollment':enrollment}
    if (not isinstance(events, list) or not 1 <= len(events) <= 32
            or any(not isinstance(e, str) or not e for e in events) or events != sorted(set(events))):
        raise Refusal('one to thirty-two distinct sorted explicit queued source identities required')
    anchors = [source_anchor(runtime, key, event, selection) for event in events]
    epoch = runtime.one('SELECT * FROM prospective_authorities WHERE revoked IS NULL')
    if not epoch:
        raise Refusal('original finite prospective authority must remain selected; no epoch replacement')
    ordinary = json.loads(epoch['selection'])
    if (ordinary.get('processing_capability') != key or ordinary['configuration'] != digest(runtime.config)
            or ordinary['grantor'] != actor or ordinary['expires'] <= runtime.clock()):
        raise Refusal('original prospective authority expired/revoked/foreign; no renewal through repair')
    for anchor in anchors:
        task = anchor['queue']['task']
        role = anchor['queue']['role']
        if (task not in ordinary['tasks'] or ordinary['tasks'][task]['task_hash'] != anchor['task_hash']
                or ordinary['grants'].get(role) != grants[role]['binding']['id']
                or not anchor['mapping'] and anchor['position'] <= epoch['event_boundary']):
            raise Refusal('source/task outside frozen original prospective authority')
    return {'schema':SOURCE_VERSION, 'configuration':digest(runtime.config),
            'configuration_version':digest(configuration.version_metadata(runtime)),
            'capability':key, 'controller':controller, 'selection_hash':digest(selection),
            'starts':cap['starts'], 'grants':grants, 'prospective':epoch, 'purpose':purpose,
            'modules':modules, 'old_release':before, 'release':after, 'changed':changed,
            'old_implementation':selection['basis']['implementation'], 'implementation':implementation,
            'sources':anchors}


def source_validate(runtime, selected):
    """Full bytes only after explicit owner selection has installed exact pins.

    This changes no source/admission/policy hash, grants, epoch or queue state.
    It proves source permission, not schedulability, effect or Root acceptance.
    """
    from . import prospective, processing_admission, report_scope
    for anchor in selected['sources']:
        queue = anchor['queue']
        event = runtime.event(anchor['event'])
        if (digest(event) != anchor['hash'] or not runtime.processing.event(event)
                or queue['task'] not in event.get('allowed_tasks', [])
                or event['role'] != queue['role']
                or event['recipient'] != runtime.config['roles'][event['role']]['owner']):
            raise Refusal('selected source bytes/hash/route/owner permission changed')
        board = runtime.processing.boards[event['role']]
        board.verify_authority(runtime)
        epoch = prospective.current(runtime, queue['task'])
        if not epoch or epoch['id'] != selected['prospective']['id']:
            raise Refusal('source requires unchanged original prospective authority')
        if anchor['kind'] == 'board':
            board.verify_input_source(runtime, event)
            if anchor['resolution']:
                resolved = anchor['resolution']
                processing_admission.resolved(runtime, queue['package'], resolved['topic'], resolved['scope_hash'])
                # Root association acceptance and runtime readiness remain
                # later independent launch checks, never fabricated here.
            elif event.get('package') != queue['package']:
                raise Refusal('source package substitution is forbidden')
        else:
            record = runtime.processing.current()[1]['service']['legacy_resources'].get('Reviews', {})
            report_scope.eligible(runtime, queue, record)


def source_receipt(key, selected):
    return {'schema':SOURCE_VERSION, 'capability':key, 'configuration':selected['configuration'],
            'selection_hash':selected['selection_hash'], 'repair_hash':digest(selected),
            'sources':[{'event':s['event'], 'hash':s['hash'], 'queue':s['queue']['id']} for s in selected['sources']],
            'producer_replay':False, 'authority_renewed':False, 'acceptance':None,
            'meaning':'same immutable capability and queued inputs; code pins only; all original duties and finite windows retained'}


def apply_source(runtime, boards, actor, request):
    from . import processing
    from .selected_source import custody_budget
    if (not isinstance(request, dict) or set(request) != {'schema','basis','authority','evidence'}
            or request['schema'] != SOURCE_VERSION or not isinstance(request['basis'], dict)
            or request['basis'].get('schema') != SOURCE_VERSION):
        raise Refusal('distinct versioned source-repair-v1 selection required; legacy requests stay separate')
    owner(runtime, boards, actor)
    required_text(request['authority'], 'genuine Work reviewed source-only repair decision', 4000)
    if not isinstance(request['evidence'], list) or not 1 <= len(request['evidence']) <= 32:
        raise Refusal('complete bounded review/qualification evidence required; Maker tests are not acceptance')
    for item in request['evidence']:
        required_text(item, 'exact reviewed source/qualification evidence', 4000)
    if len(encode(request).encode()) > runtime.config['limits']['max_result_bytes']:
        raise Refusal('source repair exceeds original result custody bound')
    selected = request['basis']
    key = selected['capability']
    with configuration.stopped(runtime), runtime.tx():
        previous = source_record(runtime, key)
        if previous:
            if previous != request or selected_release_for(runtime, key, boards) != selected['release']:
                raise Refusal('source repair already selected differently or pins no longer current')
            return source_receipt(key, selected)  # Never reread/requeue consumed inputs.
        current = source_basis(runtime, boards, key, [s['event'] for s in selected['sources']],
                               selected['controller'], actor, selected['modules'], selected['purpose'])
        if current != selected:
            raise Refusal('selected source repair basis changed; take fresh bounded owner-reviewed pins')
        custody_budget(runtime, len(encode(request).encode()) + 1024)
        runtime.db.execute('INSERT INTO same_authority_source_repairs_v1 VALUES(?,?,?,?)',
                           (key, encode(request), actor, runtime.clock()))
        old_access = runtime.processing
        runtime.processing = processing.Access(runtime, key, boards)
        try:
            runtime.processing.current()
            source_validate(runtime, selected)
        finally:
            runtime.processing = old_access
    return source_receipt(key, selected)


# Separate typed protocol; neither v1's sources nor its module ceiling expand.
PAIR_VERSION = 'same-authority-report-control-repair-v2'
PAIR_MODULES = {'cli.py','report_repair.py','processing.py','report_scope.py',
                'service.py','delivery.py','store.py'}


def pair_record(runtime, key):
    if not runtime.one("SELECT name FROM sqlite_master WHERE name='same_authority_report_control_repairs_v2'"):
        return None
    row = runtime.one('SELECT request FROM same_authority_report_control_repairs_v2 WHERE capability=?', (key,))
    return json.loads(row['request']) if row else None


def pair_identity(runtime, key, selection, request):
    cap = runtime.one('SELECT * FROM processing_capabilities WHERE id=?', (key,))
    if not cap or request['basis'].get('schema') != PAIR_VERSION:
        return False
    # Reuse every v1 identity check without teaching v1 about new sources.
    legacy_shape = {**request, 'basis':{**request['basis'], 'schema':SOURCE_VERSION}}
    return source_identity(runtime, cap, selection, legacy_shape)


def pair_finite(runtime, selection):
    import math
    def check(value):
        if isinstance(value, dict):
            for name, item in value.items():
                if name in {'expires','until'}:
                    if type(item) not in {int,float} or not math.isfinite(item) or item <= runtime.clock():
                        raise Refusal('original finite report/admission/wake/allocation rights expired; no renewal')
                elif isinstance(item, (dict,list)):
                    check(item)
        elif isinstance(value, list):
            for item in value:
                check(item)
    check(selection.get('service', {}))
    check(selection.get('allocation', {}))
    check(selection.get('window_authority', {}))


def pair_anchor(runtime, key, event, selection, kind):
    state = runtime.one('SELECT id,role,hash,state,hold,processed_at,classifier,classification,ack FROM events WHERE id=?', (event,))
    queue = runtime.one('SELECT * FROM queue WHERE event=?', (event,))
    birth = runtime.one('SELECT position FROM processing_source_positions WHERE event=?', (event,))
    if (not state or state['hold'] is not None or state['processed_at'] is not None or not queue
            or queue['job'] is not None or not birth or queue['role'] != state['role']
            or state['ack'] not in {'done','internal'} or not state['classifier']
            or runtime.one("SELECT jobs.id FROM jobs,json_each(jobs.members) m WHERE json_extract(m.value,'$.event')=? LIMIT 1", (event,))):
        raise Refusal('typed repair requires unchanged unheld unprocessed unfrozen original')
    classifier = runtime.one('SELECT id,kind,event,state,begin,ended,collected,exit,capture,error,controller,session,binding FROM attempts WHERE id=?', (state['classifier'],))
    if (not classifier or classifier['kind'] != 'classifier' or classifier['event'] != event
            or classifier['state'] != 'collected' or classifier['begin'] is None or classifier['ended'] is None
            or classifier['collected'] is None or classifier['exit'] != 0 or classifier['capture'] != 'complete' or classifier['error']):
        raise Refusal('actual complete original classifier required')
    header = runtime.one("SELECT json_extract(payload,'$.kind') kind,json_extract(payload,'$.source_job') producer FROM events WHERE id=?", (event,))
    if kind == 'work-report':
        task = runtime.config['tasks'].get(queue['task'])
        if (state['state'] != 'queued' or queue['state'] != 'queued' or state['role'] != 'Work'
                or queue['package'] is not None or queue['task'] not in selection['tasks'] or not task
                or task['role'] != 'Work' or task['phase'] != 'proposer' or task['effects'] != 'none'
                or queue['phase'] != 'proposer' or header['kind'] != 'response' or not header['producer']):
            raise Refusal('exact internal unstarted Work proposer report required')
        producer = runtime.one('SELECT * FROM jobs WHERE id=?', (header['producer'],))
        if (not producer or producer['response'] != event or producer['hold_reason']
                or producer['effects'] != 'none' or producer['role'] != 'Reviews'
                or producer['phase'] != 'integrator'):
            raise Refusal('authentic original report-only Reviews producer required before body')
        members = []
        for member in json.loads(producer['members']):
            current = runtime.one('SELECT id,role,hash,hold FROM events WHERE id=?', (member['event'],))
            if not current or current['hold'] is not None or current['hash'] != member['hash']:
                raise Refusal('original producer member held or changed before body')
            members.append(current)
        original = runtime.one('SELECT id,kind,controller,begin,ended,collected,exit,capture,error,detail FROM attempts WHERE id=?', (producer['active_attempt'],))
        if (not original or original['kind'] != 'task' or original['controller'] != producer['controller']
                or original['begin'] is None or original['ended'] is None or original['collected'] is None
                or original['exit'] != 0 or original['capture'] != 'complete' or original['error']
                or json.loads(original['detail']).get('processing_capability') != key):
            raise Refusal('original producer collection/capability required before body')
        producer = {**producer, 'member_metadata':members, 'original_attempt':original}
        control = None
    elif kind == 'board-control':
        control = runtime.one('SELECT * FROM processing_controls WHERE event=?', (event,))
        if (header['kind'] != 'board' or header['producer'] or queue['state'] != 'awaiting-owner'
                or queue['phase'] != 'control' or queue['task'] != '@control' or queue['package'] is not None
                or not control or control['capability'] != key or control['source_hash'] != state['hash']
                or control['resolution'] is not None):
            raise Refusal('exact unresolved original Board control required')
        control = {**control, 'original':runtime.one('SELECT id,controller,session,kind,event,state,begin,ended,collected,exit,capture,error,binding,detail FROM attempts WHERE id=?', (control['attempt'],))}
        row = control['original']
        producer = None
        if (not row or row['state'] != 'collected' or row['kind'] != 'input-control' or row['event'] != event
                or row['begin'] is None or row['ended'] is None or row['collected'] is None
                or row['exit'] != 0 or row['error'] or row['capture'] != 'complete'
                or json.loads(row['detail']).get('processing_capability') != key):
            raise Refusal('actual original complete END0 control collection required')
        from .contracts import SOL, canonical_uuid
        tools = json.loads(row['detail']).get('tool_completion', {})
        if (json.loads(row['binding']) != SOL or not tools.get('complete')
                or tools.get('items') or tools.get('nonzero_completions') or tools.get('unknown_types')):
            raise Refusal('original control worker binding/tool completion required before body')
        canonical_uuid(row['session'])
        stopped_original(runtime, key, row['controller'])
    else:
        raise Refusal('unsupported typed anchor')
    transition = configuration.selected(runtime)
    if birth['position'] <= max(selection['basis']['event_boundary'], transition['event_boundary']):
        raise Refusal('repair cannot introduce historical sources')
    return {'kind':kind,'event':event,'hash':state['hash'],'state':state,'queue':queue,
            'classifier':classifier,'position':birth['position'],'control':control,'producer':producer}


def pair_metadata(runtime, boards, key, work_event, control_event, controller, actor, modules, purpose, *, _continuation=False):
    events = [work_event, control_event]
    """Caller holds the cooperative stop lock and journal write transaction."""
    from . import processing
    owner(runtime, boards, actor)
    required_text(purpose, 'explicit current Work source-repair purpose', 4000)
    configuration.assert_current(runtime)
    cap = runtime.one('SELECT * FROM processing_capabilities WHERE id=?', (key,))
    if (not cap or cap['revoked'] is not None or cap['issuer'] != actor
            or actor != runtime.config['software_delegation']['grantor']
            or set(boards) != {'Work','Reviews','QA','Branch'} or set(boards) != set(runtime.config['roles'])):
        raise Refusal('same genuine current Work capability and exact four original roles required')
    selection = json.loads(cap['selection'])
    if ('service' not in selection or not selection['future_intake']
            or selection['basis']['configuration'] != digest(runtime.config)):
        raise Refusal('unchanged continuing capability/configuration required; no finite grant conversion')
    if record(runtime, key) or source_record(runtime, key) or pair_record(runtime, key) or lease_record(runtime, key):
        raise Refusal('one distinct source repair point only; no repair stacking or legacy receipt conversion')
    stopped_original(runtime, key, controller)
    if configuration.owned_service_conflict(runtime) or runtime.one(
            "SELECT controller FROM service_runs WHERE capability=? AND (state!='returned-awaiting-parent-END' OR returned IS NULL)", (key,)):
        raise Refusal('no active concurrent collector; every same-capability original must return and release')
    for run in runtime.rows('SELECT controller FROM processing_runs WHERE capability=?', (key,)):
        stopped_original(runtime, key, run['controller'])
    transition = configuration.selected(runtime)
    if not transition:
        raise Refusal('immutable current configuration release selection required')
    before, after = transition['basis']['release'], configuration.release(runtime, runtime.config)
    implementation = processing.implementation()
    changed = source_compatible(before, after, selection['basis']['implementation'], implementation, modules, _ceiling=LEASE_MODULES if _continuation else PAIR_MODULES)
    grants = {}
    from .integration_management import _metadata_original
    for role, board in boards.items():
        with board.opened(settlement=True) as conn:
            grant, enrollment = _metadata_original(board, conn, runtime)
            binding = board._binding(grant)
            if (binding != selection['basis']['roles'][role]['original']['binding']
                    or grant['issued_by'] != actor or enrollment['owner'] != board.selected['owner']
                    or enrollment['profile'] != board.selected['profile']):
                raise Refusal('source repair conserves every original stopped software grant binding')
            grants[role] = {'binding':binding, 'enrollment':enrollment}
    if not _continuation:
        pair_finite(runtime, selection)
    anchors = [pair_anchor(runtime, key, work_event, selection, 'work-report'),
               pair_anchor(runtime, key, control_event, selection, 'board-control')]
    if anchors[1]['control']['original']['controller'] != controller or anchors[0]['producer']['controller'] != controller:
        raise Refusal('both selected originals must retain their same released producer/controller')
    epoch = runtime.one('SELECT * FROM prospective_authorities WHERE revoked IS NULL')
    if not epoch:
        raise Refusal('original finite prospective authority must remain selected; no epoch replacement')
    ordinary = json.loads(epoch['selection'])
    if (ordinary.get('processing_capability') != key or ordinary['configuration'] != digest(runtime.config)
            or ordinary['grantor'] != actor or not _continuation and ordinary['expires'] <= runtime.clock()):
        raise Refusal('original prospective authority expired/revoked/foreign; no renewal through repair')
    for anchor in anchors:
        if anchor['position'] <= epoch['event_boundary']:
            raise Refusal('report/control source predates original epoch')
        if anchor['kind'] == 'work-report':
            task = anchor['queue']['task']
            if (task not in ordinary['tasks'] or ordinary['tasks'][task]['task_hash'] != digest(runtime.config['tasks'][task])
                    or ordinary['grants'].get('Work') != grants['Work']['binding']['id']):
                raise Refusal('Work report outside original task/grant authority')
    return {'schema':PAIR_VERSION, 'configuration':digest(runtime.config),
            'configuration_version':digest(configuration.version_metadata(runtime)),
            'capability':key, 'controller':controller, 'selection_hash':digest(selection),
            'revision':__import__(__package__+'.windows', fromlist=['revision']).revision(runtime), 'starts':cap['starts'], 'grants':grants, 'prospective':epoch, 'purpose':purpose,
            'modules':modules, 'old_release':before, 'release':after, 'changed':changed,
            'old_implementation':selection['basis']['implementation'], 'implementation':implementation,
            'sources':anchors}



def pair_validate(runtime, selected, *, _continuation=False):
    from . import prospective, report_scope
    runtime.processing.current()
    if not _continuation:
        pair_finite(runtime, runtime.processing.current()[1])
    work, control = selected['sources']
    _, selection = runtime.processing.current()
    for anchor in (work, control):
        if pair_anchor(runtime, selected['capability'], anchor['event'], selection, anchor['kind']) != anchor:
            raise Refusal('selected original metadata/custody changed before body')
    # Current original grants/epoch are checked before acquiring producer/result bodies.
    for board in runtime.processing.boards.values():
        board.verify_authority(runtime)
    prospective.current(runtime, work['queue']['task'])
    value = report(runtime, selected['capability'], work['event'], selected['controller'], runtime.processing.current()[1])
    source = runtime.event(work['event'])
    if value['hash'] != work['hash'] or source.get('allowed_tasks') != [work['queue']['task']]:
        raise Refusal('whole original Work producer route/hash changed')
    report_scope.execution_report(runtime, source, value['producer'], work['queue']['task'])
    if value['producer']['effects'] != 'none':
        raise Refusal('repair only transfers authentic report-only producer')
    for role in runtime.processing.boards:
        runtime.processing.boards[role].verify_authority(runtime)
    epoch = prospective.current(runtime, work['queue']['task'])
    if not epoch or epoch['id'] != selected['prospective']['id']:
        raise Refusal('original finite epoch changed')
    runtime.processing.current()
    row = runtime.attempt(control['control']['attempt'])
    result = json.loads(row['result'] or 'null')
    receipt = json.loads(result['decision_json'])
    proof = runtime.processing.control_proof(control['event'], row['id'], receipt)
    if (result['semantic'] != 'DONE' or receipt['mode'] != 'control' or receipt['task'] != '@control'
            or proof['controller'] != selected['controller']):
        raise Refusal('exact original DONE control marker and original controller required')
    runtime.processing.boards[control['queue']['role']].verify_input_source(runtime, runtime.event(control['event']))
    return {'work':value,'control_result_hash':digest(result),
            'raw_control_sha256':__import__('hashlib').sha256(row['result'].encode()).hexdigest()}


def pair_receipt(key, selected):
    return {**source_receipt(key, selected), 'schema':PAIR_VERSION}


def apply_pair(runtime, boards, actor, request):
    from . import processing
    from .selected_source import custody_budget
    if (not isinstance(request, dict) or set(request) != {'schema','basis','authority','evidence'}
            or request['schema'] != PAIR_VERSION or request['basis'].get('schema') != PAIR_VERSION):
        raise Refusal('explicit versioned typed report/control repair required')
    owner(runtime, boards, actor)
    required_text(request['authority'], 'actual Work typed repair selection', 4000)
    if not isinstance(request['evidence'], list) or not 1 <= len(request['evidence']) <= 32:
        raise Refusal('bounded actual independent review evidence required')
    for item in request['evidence']:
        required_text(item, 'review evidence', 4000)
    selected = request['basis']; key = selected['capability']
    if len(encode(request).encode()) > runtime.config['limits']['max_result_bytes']:
        raise Refusal('typed repair selection exceeds original custody bound')
    with configuration.stopped(runtime), runtime.tx():
        previous = pair_record(runtime, key)
        if previous:
            if previous != request or selected_release_for(runtime, key, boards) != selected['release']:
                raise Refusal('immutable repair already selected differently')
            return pair_receipt(key, selected)
        work, control = selected['sources']
        current = pair_metadata(runtime, boards, key, work['event'], control['event'], selected['controller'], actor, selected['modules'], selected['purpose'])
        if current != {k:v for k,v in selected.items() if k != 'proof'}:
            raise Refusal('typed repair metadata/pins/rights/counters changed before body acquisition')
        custody_budget(runtime, len(encode(request).encode()) + 1024)
        runtime.db.execute('INSERT INTO same_authority_report_control_repairs_v2 VALUES(?,?,?,?)', (key, encode(request), actor, runtime.clock()))
        old = runtime.processing
        runtime.processing = processing.Access(runtime, key, boards)
        try:
            if pair_validate(runtime, selected) != selected['proof']:
                raise Refusal('whole original producer/custody/control result proof changed')
        finally:
            runtime.processing = old
    return pair_receipt(key, selected)


def released_control(runtime, event, row):
    """Metadata-only exception to the SAME-controller check, for one selected original."""
    key = runtime.processing.key
    request = lease_record(runtime, key)
    if request:
        lease_selection(runtime, key, json.loads(runtime.one('SELECT selection FROM processing_capabilities WHERE id=?', (key,))['selection']))
        anchor = request['basis']['sources'][1]
        if event != anchor['event'] or row['id'] != anchor['control']['attempt']:
            return False
        if pair_anchor(runtime, key, event, runtime.processing.current()[1], 'board-control') != anchor:
            raise Refusal('owner lease original control metadata changed')
        return True
    request = pair_record(runtime, key)
    if not request:
        return False
    _, selection = runtime.processing.current()
    if not pair_identity(runtime, key, selection, request):
        raise Refusal('selected original control repair no longer current')
    pair_finite(runtime, selection)
    selected = request['basis']
    epoch = runtime.one('SELECT * FROM prospective_authorities WHERE id=?', (selected['prospective']['id'],))
    if epoch != selected['prospective'] or json.loads(epoch['selection'])['expires'] <= runtime.clock():
        raise Refusal('original finite epoch changed or expired')
    anchor = selected['sources'][1]
    if event != anchor['event'] or row['id'] != anchor['control']['attempt']:
        return False
    if pair_anchor(runtime, key, event, selection, 'board-control') != anchor:
        raise Refusal('selected original control metadata changed')
    return True



def pair_basis(runtime, boards, key, work_event, control_event, controller, actor, modules, purpose):
    """Preview exact pins and full proofs after metadata, leaving no selection behind.

    The caller owns the stopped lock and transaction. The temporary pin row is
    visible only inside this savepoint; every exit rolls it back.
    """
    from . import processing
    selected = pair_metadata(runtime, boards, key, work_event, control_event, controller, actor, modules, purpose)
    runtime.db.execute('SAVEPOINT report_control_preview')
    old = runtime.processing
    try:
        preview = {'schema':PAIR_VERSION, 'basis':selected}
        runtime.db.execute('INSERT INTO same_authority_report_control_repairs_v2 VALUES(?,?,?,?)', (key, encode(preview), actor, runtime.clock()))
        runtime.processing = processing.Access(runtime, key, boards)
        proof = pair_validate(runtime, selected)
    finally:
        runtime.processing = old
        runtime.db.execute('ROLLBACK TO report_control_preview')
        runtime.db.execute('RELEASE report_control_preview')
    return {**selected, 'proof':proof}


# Explicit finite authority amendment. Neither v1 nor v2 inherits this ceiling.
LEASE_VERSION = 'continuing-owner-lease-v1'
LEASE_MODULES = PAIR_MODULES | {'prospective.py', 'windows.py', 'service_wake.py', 'ordinary.py', 'ref_scope.py'}
SCHEMA += """
CREATE TABLE IF NOT EXISTS owner_lease_plans(
 capability TEXT PRIMARY KEY,request TEXT NOT NULL,issuer TEXT NOT NULL,created REAL NOT NULL);
CREATE TABLE IF NOT EXISTS owner_lease_activations(
 capability TEXT NOT NULL,ordinal INTEGER NOT NULL,controller TEXT NOT NULL,
 activated REAL NOT NULL,until REAL NOT NULL,PRIMARY KEY(capability,ordinal));
CREATE TABLE IF NOT EXISTS owner_lease_stops(
 capability TEXT PRIMARY KEY,issuer TEXT NOT NULL,reason TEXT NOT NULL,created REAL NOT NULL);
"""
for _table in ('owner_lease_plans', 'owner_lease_activations', 'owner_lease_stops'):
    for _op in ('UPDATE', 'DELETE'):
        SCHEMA += (f'CREATE TRIGGER IF NOT EXISTS {_table}_no_{_op.lower()} BEFORE {_op} ON {_table} '
                   "BEGIN SELECT RAISE(ABORT,'immutable owner lease authority'); END;\n")


def lease_record(runtime, key):
    if not runtime.one("SELECT name FROM sqlite_master WHERE name='owner_lease_plans'"):
        return None
    row = runtime.one('SELECT request FROM owner_lease_plans WHERE capability=?', (key,))
    return json.loads(row['request']) if row else None


def lease_identity(runtime, key, selection, request):
    cap = runtime.one('SELECT * FROM processing_capabilities WHERE id=?', (key,))
    selected = request['basis']
    identity = runtime.path.stat()
    return bool(cap and request['schema'] == LEASE_VERSION
        and selected['schema'] == LEASE_VERSION
        and source_identity(runtime, cap, selection,
                            {'basis':{**selected, 'schema':SOURCE_VERSION}})
        and selected['journal'] == {'path':str(runtime.path), 'dev':identity.st_dev, 'ino':identity.st_ino}
        and digest(request['plan']) == selected['plan_hash']
        and runtime.one('SELECT * FROM prospective_authorities WHERE id=?',
                        (selected['prospective']['id'],)) == selected['prospective'])


def validate_lease_plan(runtime, plan, selection, *, selecting=True):
    import math
    if (not isinstance(plan, dict) or set(plan) != {'from', 'until', 'lease_seconds',
            'max_starts', 'max_new_inputs', 'max_windows', 'pause_bytes'}
            or any(type(plan[k]) not in {int,float} or not math.isfinite(plan[k]) for k in ('from','until'))
            or type(plan['lease_seconds']) is not int or not 1 <= plan['lease_seconds'] <= 3600
            or not 0 < plan['until'] - plan['from'] <= 24 * plan['lease_seconds']
            or selecting and not plan['from'] <= runtime.clock() < plan['until']
            or selecting and runtime.clock() - plan['from'] > 60):
        raise Refusal('explicit finite owner plan: current start, at most 24 leases, each at most one hour')
    for name, maximum in [('max_starts', 1000000), ('max_new_inputs', runtime.config['limits']['max_events']),
                          ('max_windows', 10000), ('pause_bytes', runtime.config['limits']['max_bytes'] - 1)]:
        if type(plan[name]) is not int or not 0 < plan[name] <= maximum:
            raise Refusal('bounded total owner lease allocation required: ' + name)
    if (not selection.get('service', {}).get('admission')
            or plan['pause_bytes'] <= 4096 or not selection['future_intake']):
        raise Refusal('owner lease requires original bounded continuing admission')


def lease_selection(runtime, key, selection):
    """An effective view; immutable original selection and hashes never change."""
    request = lease_record(runtime, key)
    if not request:
        return selection
    if (not lease_identity(runtime, key, selection, request)
            or runtime.one('SELECT capability FROM owner_lease_stops WHERE capability=?', (key,))):
        raise Refusal('owner lease revoked or original journal/configuration/epoch/selection changed')
    plan = request['plan']
    now = runtime.clock()
    if not plan['from'] <= now < plan['until']:
        raise Refusal('owner lease plan exhausted/not yet active; duties retained')
    cap = runtime.one('SELECT starts FROM processing_capabilities WHERE id=?', (key,))
    if cap['starts'] > plan['max_starts'] or runtime.usage()['bytes'] >= plan['pause_bytes']:
        raise Refusal('owner lease total allocation/byte pressure; no accounting reset')
    ordinal = int((now - plan['from']) // plan['lease_seconds']) + 1
    until = min(plan['until'], plan['from'] + ordinal * plan['lease_seconds'])
    if not runtime.one('SELECT ordinal FROM owner_lease_activations WHERE capability=? AND ordinal=?', (key,ordinal)):
        from contextlib import nullcontext
        with (nullcontext() if runtime.db.in_transaction else runtime.tx()):
            runtime.budget(None, 1024)
            runtime.db.execute('INSERT OR IGNORE INTO owner_lease_activations VALUES(?,?,?,?,?)',
                               (key,ordinal,runtime.controller,now,until))
    import copy
    effective = copy.deepcopy(selection)
    effective['service']['admission'].update(until=until, max_new_inputs=plan['max_new_inputs'], pause_bytes=plan['pause_bytes'])
    if effective['service'].get('wake'):
        effective['service']['wake']['until'] = until
    # Only the framework's exact report policy gains new finite authority.
    # Native QA/Branch/resource/effect/account policies keep their original expiry.
    report_policy = effective['service'].get('legacy_resources', {}).get('Reviews', {}).get('reviews_report')
    if report_policy:
        report_policy['expires'] = until
    return effective


def lease_deadline(runtime):
    if not runtime.processing:
        return None
    request = lease_record(runtime, runtime.processing.key)
    if not request:
        return None
    _, selection = runtime.processing.current()
    return selection['service']['admission']['until']


def lease_expiry(runtime, epoch):
    if not runtime.processing:
        return None
    request = lease_record(runtime, runtime.processing.key)
    if not request:
        return None
    if epoch != request['basis']['prospective']:
        raise Refusal('owner lease cannot replace or revive a changed/revoked epoch')
    return lease_deadline(runtime)


def lease_metadata(runtime, boards, key, work, control, controller, actor, modules, purpose, plan):
    if lease_record(runtime, key):
        raise Refusal('one immutable owner plan per original capability; no silent replacement')
    selected = pair_metadata(runtime, boards, key, work, control, controller, actor, modules, purpose, _continuation=True)
    raw = json.loads(runtime.one('SELECT selection FROM processing_capabilities WHERE id=?', (key,))['selection'])
    validate_lease_plan(runtime, plan, raw)
    if selected['starts'] >= plan['max_starts']:
        raise Refusal('owner plan needs explicit remaining starts above original cumulative debit')
    count = runtime.one('SELECT COUNT(*) n FROM processing_source_positions WHERE position>?', (raw['basis']['event_boundary'],))['n']
    windows = runtime.one('SELECT COUNT(*) n FROM service_window_allocations WHERE capability=?', (key,))['n']
    if count >= plan['max_new_inputs'] or windows >= plan['max_windows']:
        raise Refusal('owner plan requires remaining total input/window headroom, never a reset')
    identity = runtime.path.stat()
    return {**selected, 'schema':LEASE_VERSION, 'plan_hash':digest(plan),
            'journal':{'path':str(runtime.path),'dev':identity.st_dev,'ino':identity.st_ino}}


def lease_basis(runtime, boards, key, work, control, controller, actor, modules, purpose, plan):
    from .processing import Access
    selected = lease_metadata(runtime, boards, key, work, control, controller, actor, modules, purpose, plan)
    old = runtime.processing
    runtime.db.execute('SAVEPOINT owner_lease_preview')
    try:
        runtime.db.execute('INSERT INTO owner_lease_plans VALUES(?,?,?,?)',
            (key, encode({'schema':LEASE_VERSION,'basis':selected,'plan':plan}),actor,runtime.clock()))
        runtime.processing = Access(runtime,key,boards)
        proof = pair_validate(runtime, selected, _continuation=True)
    finally:
        runtime.processing = old
        runtime.db.execute('ROLLBACK TO owner_lease_preview')
        runtime.db.execute('RELEASE owner_lease_preview')
    return {**selected,'proof':proof}


def apply_lease(runtime, boards, actor, request):
    from .processing import Access
    from .selected_source import custody_budget
    if (not isinstance(request,dict) or set(request) != {'schema','basis','plan','authority','evidence'}
            or request['schema'] != LEASE_VERSION or request['basis'].get('schema') != LEASE_VERSION):
        raise Refusal('distinct exact owner lease amendment required')
    owner(runtime,boards,actor)
    required_text(request['authority'],'actual Work finite continuing authority',4000)
    if not isinstance(request['evidence'],list) or not 1 <= len(request['evidence']) <= 32:
        raise Refusal('reviewed exact code and authority evidence required')
    for item in request['evidence']:
        required_text(item,'actual review/qualification evidence',4000)
    if len(encode(request).encode()) > runtime.config['limits']['max_result_bytes']:
        raise Refusal('owner amendment exceeds original custody bound')
    selected = request['basis']; key = selected['capability']
    with configuration.stopped(runtime), runtime.tx():
        previous = lease_record(runtime,key)
        if previous:
            if previous != request or selected_release_for(runtime,key,boards) != selected['release']:
                raise Refusal('owner amendment already selected differently/expired/changed')
            return lease_receipt(runtime,key)
        work, control = selected['sources']
        current = lease_metadata(runtime,boards,key,work['event'],control['event'],selected['controller'],actor,
                                 selected['modules'],selected['purpose'],request['plan'])
        if current != {k:v for k,v in selected.items() if k != 'proof'}:
            raise Refusal('owner lease basis changed before body; take fresh reviewed basis')
        custody_budget(runtime,len(encode(request).encode())+2048)
        runtime.db.execute('INSERT INTO owner_lease_plans VALUES(?,?,?,?)',(key,encode(request),actor,runtime.clock()))
        old = runtime.processing; runtime.processing = Access(runtime,key,boards)
        try:
            if pair_validate(runtime,selected,_continuation=True) != selected['proof']:
                raise Refusal('owner lease original producer/control/custody changed')
        finally:
            runtime.processing = old
    return lease_receipt(runtime,key)


def lease_receipt(runtime,key):
    request = lease_record(runtime,key)
    return {'schema':LEASE_VERSION,'capability':key,'plan':request['plan'],
            'amendment_hash':digest(request),'original_controller':request['basis']['controller'],
            'activations':runtime.rows('SELECT * FROM owner_lease_activations WHERE capability=? ORDER BY ordinal',(key,)),
            'stop':runtime.one('SELECT * FROM owner_lease_stops WHERE capability=?',(key,)),
            'acceptance':None,'original_history_rewritten':False,'native_rights_renewed':False}


def stop_lease(runtime,boards,actor,key,reason):
    owner(runtime,boards,actor)
    required_text(reason,'actual Work immediate lease stop',4000)
    request = lease_record(runtime,key)
    if not request or actor != runtime.config['software_delegation']['grantor']:
        raise Refusal('same actual Work owner plan required')
    with runtime.tx():
        runtime.budget(None,len(reason.encode())+1024)
        runtime.db.execute('INSERT OR IGNORE INTO owner_lease_stops VALUES(?,?,?,?)',(key,actor,reason,runtime.clock()))
    return lease_receipt(runtime,key)
