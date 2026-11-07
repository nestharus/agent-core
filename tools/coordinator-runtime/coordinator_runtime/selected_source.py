"""Explicit selected-retained-source metadata. No historical body acquisition.

A snapshot grants no read/effect/collector/recovery rights. The ordinary guards
still authenticate actual bytes, current mappings and downstream operations.
"""
import json
import re
from .contracts import Refusal

FIELDS = {'event', 'role', 'source_hash', 'source_birth', 'task', 'mapping_version'}
MODE = 'selected-retained-source-v1'


def operands(runtime, selected):
    if not isinstance(selected, list) or not 1 <= len(selected) <= 32:
        raise Refusal('finite explicit selected retained source pins required')
    seen = set()
    for pin in selected:
        if (not isinstance(pin, dict) or set(pin) != FIELDS
                or not isinstance(pin['event'], str) or not pin['event'] or pin['event'] in seen
                or not isinstance(pin['role'],str) or not isinstance(pin['task'],str)
                or pin['role'] not in runtime.config['roles'] or pin['task'] not in runtime.config['tasks']
                or runtime.config['tasks'][pin['task']]['role'] != pin['role']
                or not isinstance(pin['source_hash'], str) or not re.fullmatch('[0-9a-f]{64}', pin['source_hash'])
                or type(pin['source_birth']) is not int or pin['source_birth'] <= 0
                or type(pin['mapping_version']) is not int or pin['mapping_version'] <= 0):
            raise Refusal('exact distinct source/role/hash/birth/current task/mapping pins required')
        seen.add(pin['event'])
    return selected


def snapshot(runtime, pin):
    # Hold/exclusion first; never fetch a body, error or capture to diagnose it.
    state = runtime.one('SELECT hold IS NOT NULL AS held,processed_at,state FROM events WHERE id=?', (pin['event'],))
    if not state or state['held'] or state['processed_at'] is not None or state['state'] != 'queued':
        raise Refusal('selected retained source held/excluded/processed or not queued')
    source = runtime.one('SELECT id,role,hash FROM events WHERE id=?', (pin['event'],))
    birth = runtime.one('SELECT position FROM processing_source_positions WHERE event=?', (pin['event'],))
    queue = runtime.one('SELECT role,phase,task,package,state,job FROM queue WHERE event=?', (pin['event'],))
    # Only explicitly selected mapping metadata. Never fetch prior/error/result
    # bodies or any unrelated mapping, even for currentness or accounting.
    mapping = runtime.one("SELECT version,source_hash,actor,CASE WHEN json_valid(receipt) THEN json_extract(receipt,'$.mode') END AS mode,"
                          "CASE WHEN json_valid(receipt) THEN json_extract(receipt,'$.task') END AS task,"
                          "CASE WHEN json_valid(receipt) THEN json_extract(receipt,'$.package') END AS package,"
                          "CASE WHEN json_valid(prior) THEN json_extract(prior,'$.integration_observation.packet') END AS packet "
                          'FROM input_resolutions WHERE event=? ORDER BY version DESC LIMIT 1', (pin['event'],))
    task = runtime.config['tasks'][pin['task']]
    if (source != dict(id=pin['event'], role=pin['role'], hash=pin['source_hash'])
            or not birth or birth['position'] != pin['source_birth']
            or not queue or queue['role'] != pin['role'] or queue['task'] != pin['task']
            or queue['phase'] != task['phase'] or queue['state'] != 'queued' or queue['job'] is not None
            or not mapping or mapping['version'] != pin['mapping_version'] or mapping['source_hash'] != pin['source_hash']
            or mapping['mode'] != 'route' or mapping['task'] != pin['task'] or mapping['package'] != queue['package']
            or mapping['actor'] not in {runtime.config['roles'][pin['role']]['owner'], runtime.config['actor']}):
        raise Refusal('selected original identity/birth/task/current mapping changed or unknown')
    from .local_integration import selected as local_task
    if local_task(runtime, pin['task']):
        try:
            packet = json.loads(mapping['packet']) if mapping['packet'] else None
        except (ValueError,TypeError):
            raise Refusal('selected original mapping metadata malformed; no body diagnosis') from None
        if (not isinstance(packet, dict) or set(packet) != {'reads','writes','versions'}
                or not isinstance(packet['reads'],list) or not isinstance(packet['writes'],list)
                or not all(isinstance(k,str) for k in packet['reads']+packet['writes'])
                or not isinstance(packet['versions'],dict)
                or not all(isinstance(v,str) for v in packet['versions'].values())
                or not (packet['reads'] or packet['writes'])
                or set(packet['versions']) != set(packet['reads']) | set(packet['writes'])):
            raise Refusal('selected original known mapping required; no unknown/new relabeling')
    from .configuration import processing_tasks
    tasks = processing_tasks(runtime)
    if tasks is not None and pin['task'] not in tasks:
        raise Refusal('selected source task outside current Work configuration authority')
    return {**pin, 'id':source['id'], 'hash':source['hash'], 'queue':queue,
            'mapping':mapping, 'qualification':'recorded metadata only; actual source and current mapping guards still required'}


def selected_pins(selection):
    basis = selection.get('basis', {})
    return basis.get('selected_retained', []) if basis.get('mode') == MODE else []


def permits_original(runtime, event):
    if not runtime.processing:
        return False
    _, selection = runtime.processing.current()
    return any(p['event'] == event['id'] and p['source_hash'] == runtime.one(
        'SELECT hash FROM events WHERE id=?', (event['id'],))['hash'] and p['role'] == event['role']
        for p in selected_pins(selection))


def retained_job_duty(runtime, job, authority):
    """Require proof even after revocation/drift; this grants no authority.

    Read only the exact epoch's retained pin metadata, never historical source
    bodies. Missing job birth remains unqualified in prospective.for_job.
    """
    key = authority['selection'].get('processing_capability')
    if not key:
        return False
    row = runtime.one("SELECT json_extract(selection,'$.basis.mode') AS mode,"
                      "json_extract(selection,'$.basis.selected_retained') AS pins "
                      'FROM processing_capabilities WHERE id=?', (key,))
    return bool(row and row['mode'] == MODE and any(
        p['event'] == m['event'] and p['role'] == job['role'] and p['task'] == job['task']
        for p in json.loads(row['pins'] or '[]') for m in json.loads(job['members'])))


def permits_job(runtime, job, authority, attempt):
    """A new frozen Work catalog job may use explicitly selected old inputs.

    Called only AFTER the prospective job-birth fence. Neither an old job nor
    a role label, source title, configuration exemption or renewed mapping is
    a grant. Original source pins and the new job's current mapping both bind.
    """
    from contextlib import nullcontext
    from . import local_integration as local
    from .contracts import scoped_task
    bridge = authority['selection'].get('processing_capability')
    task = runtime.config['tasks'][job['task']]
    if (authority['selection'].get('job_birth') != 'observed-v1'
            or not bridge or not runtime.processing or runtime.processing.key != bridge or not attempt
            or job['role'] != 'Work' or job['phase'] not in {'proposer', 'integrator'}
            or task['role'] != job['role'] or task['phase'] != job['phase'] or task['effects'] != 'none'
            or job['package'] is not None or authority['policy']['ordinary_effects'] is not False
            or job['controller'] != runtime.controller or attempt['controller'] != runtime.controller
            or attempt['job'] != job['id'] or attempt['kind'] != 'task'
            or json.loads(attempt['detail']).get('processing_capability') != bridge
            or not local.selected(runtime, job['task'])
            or runtime.one('SELECT attempt FROM ordinary_runs WHERE job=?', (job['id'],))):
        return False
    cap, selection = runtime.processing.current()
    owner = runtime.config['roles']['Work']['owner']
    if (cap['issuer'] != owner or authority['selection']['grantor'] != owner
            or job['task'] not in selection['tasks']):
        return False
    proof = json.loads(attempt['detail']).get('software_authority', {})
    if attempt['collected'] is not None and (proof.get('prospective_epoch') != authority['id']
            or proof.get('processing_capability') != bridge):
        return False  # A prior unbound/refused attempt cannot gain a proof now.
    pins = {p['event']:p for p in selected_pins(selection)}
    members = json.loads(job['members'])
    # A mixed unselected old/future member cannot borrow this narrow exception.
    if any(m['event'] not in pins for m in members):
        return False
    originals = selection['basis']['roles'].get('Work', {}).get('original', {}).get('events', [])
    for member in members:
        pin = pins[member['event']]
        original = next((o for o in originals if o['id'] == pin['event']), None)
        if (pin['role'] != job['role'] or pin['task'] != job['task']
                or member['hash'] != pin['source_hash'] or member['package'] is not None
                or pin['event'] not in selection['retained_events'] or not original
                or any(original.get(k) != v for k, v in pin.items())
                or original['queue']['package'] is not None):
            return False
        # Hold and identity metadata precede every selected source body read.
        state = runtime.one('SELECT hold IS NOT NULL AS held,state,processed_at FROM events WHERE id=?', (pin['event'],))
        if (not state or state['held'] or state['state'] not in {'queued', 'processed'}
                or state['processed_at'] is not None and attempt['collected'] is None):
            return False
        source = runtime.one('SELECT role,hash FROM events WHERE id=?', (pin['event'],))
        birth = runtime.one('SELECT position FROM processing_source_positions WHERE event=?', (pin['event'],))
        queue = runtime.one('SELECT * FROM queue WHERE event=?', (pin['event'],))
        mapping = runtime.one("SELECT version,source_hash,actor,json_extract(receipt,'$.mode') AS mode,"
                              "json_extract(receipt,'$.task') AS task,json_extract(receipt,'$.package') AS package "
                              'FROM input_resolutions WHERE event=? ORDER BY version DESC LIMIT 1', (pin['event'],))
        if (not source or source['role'] != pin['role'] or source['hash'] != pin['source_hash']
                or not birth or birth['position'] != pin['source_birth']
                or not queue or queue['id'] != member['queue'] or queue['job'] != job['id']
                or queue['role'] != job['role'] or queue['phase'] != job['phase'] or queue['task'] != job['task']
                or queue['package'] is not None or queue['state'] not in {'reserved', 'done'}
                or not mapping or mapping['version'] != member.get('input_resolution')
                or mapping['version'] < pin['mapping_version'] or mapping['source_hash'] != pin['source_hash']
                or mapping['mode'] != 'route' or mapping['task'] != job['task'] or mapping['package'] is not None
                or mapping['actor'] not in {owner, runtime.config['actor']}):
            return False
    scope = local.scope_for(runtime, job)
    if not scope or scope['lane'] != 'anchored' or scope.get('neighbors'):
        return False
    keys = set(scope['reads']) | set(scope['writes'])
    points = local.point_definitions(runtime)
    if (not keys or keys - local.allowed_points(runtime, job['task']) or keys - points.keys()
            or any('native' in b for k in keys for b in points[k]['bindings'])):
        return False  # Before any native acquisition, even read-only native.
    local.current_job(runtime, job)
    packets = []
    for member in members:
        source = runtime.event(member['event'])
        if source.get('package') is not None:
            return False
        packets.append(local.packet(runtime, dict(task=job['task'], event=member['event'], package=None)))
    if local.combine(packets) != {k:v for k,v in scope.items() if k != 'read_fences'}:
        return False
    # A collected decision retains its original revision for downstream duties;
    # it gets no new launch/effect/acceptance credit from later point changes.
    if attempt['collected'] is None:
        from .custody import guard_path, safe_path, read_file
        from .publication import snapshot_lock
        actual = scoped_task(job['task'], task, None)
        roots = actual['effect_authority']['read_roots'] + actual['effect_authority']['write_roots']
        targets = {b['target'] for k in keys for b in points[k]['bindings']}
        for path in targets:
            guard_path(runtime, path)
        with (snapshot_lock(runtime) if runtime.config.get('canonical_publication') else nullcontext()):
            bodies = {p:read_file(safe_path(p, roots), runtime.config['limits'].get('max_artifact_bytes', 33554432))[0]
                      for p in targets}
            if any(local.version(runtime, k, bodies, job) != packet['versions'][k]
                   for packet in packets for k in set(packet['reads']) | set(packet['writes'])):
                return False
    return True


def custody_budget(runtime, incoming):
    """Bound only this metadata registration without walking old captures.

    SQLite's aggregate allocated pages are not body
    measurements or a claim about all retained artifact residency. This grants
    no execution/allocation; ordinary total storage admission remains required
    at each subsequent real allocation/read/effect boundary.
    """
    size = runtime.db.execute('PRAGMA page_size').fetchone()[0]
    pages = runtime.db.execute('PRAGMA page_count').fetchone()[0]
    if size * pages + incoming + 4096 >= runtime.config['limits']['max_bytes']:
        raise Refusal('selected metadata authority journal capacity full; no old capture accounting')
