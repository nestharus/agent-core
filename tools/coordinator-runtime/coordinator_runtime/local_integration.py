"""Point-local integration over retained file consumers.

The controller supplies point bindings and routine decision authority. Packets
select those bindings; neither model text nor a row offset creates authority.
The publisher rebases service-validated deltas while holding its cooperative
commit lock. This is neither a model lock nor hostile-writer CAS.
"""
import copy
import json
from contextlib import nullcontext
from pathlib import Path

from .contracts import Refusal, digest, encode, parse_json, required_text, collected_task_result

SCHEMA = """
CREATE TABLE IF NOT EXISTS local_jobs(job TEXT PRIMARY KEY,policy TEXT NOT NULL,scope TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS local_bases(attempt TEXT PRIMARY KEY,basis TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS local_commits(attempt TEXT PRIMARY KEY,state TEXT NOT NULL,receipt TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS local_discovered_points(point TEXT PRIMARY KEY,definition TEXT NOT NULL,policy TEXT NOT NULL,source_attempt TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS local_point_commits(point TEXT NOT NULL,generation INTEGER NOT NULL,attempt TEXT NOT NULL,PRIMARY KEY(point,generation));
CREATE TABLE IF NOT EXISTS local_point_versions(point TEXT PRIMARY KEY,generation INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS local_material_commits(seq INTEGER PRIMARY KEY AUTOINCREMENT,attempt TEXT NOT NULL UNIQUE,footprints TEXT NOT NULL);
"""
STEPS = ['Observe', 'Frame', 'Decide', 'Act']
OWNERSHIP = {'owner', 'accepted_owner', 'owner_ack', 'owner_evidence', 'acceptance_receipt', 'accepted'}
IDENTITY = OWNERSHIP | {'id', 'work_id'}


def policy(config):
    value = config.get('local_integration')
    if value is None:
        return None
    if (not isinstance(value, dict) or set(value) != {'tasks', 'points', 'max_inflight'}
            or type(value['max_inflight']) is not int or not 1 <= value['max_inflight'] <= 32
            or not isinstance(value['points'], dict) or not isinstance(value['tasks'], dict)
            or not value['tasks']):
        raise Refusal('explicit local task/point policy and current model budget required')
    for name, selected in value['tasks'].items():
        task = config['tasks'].get(name)
        if (not task or not isinstance(selected, dict)
                or set(selected) - {'new_point_prefix', 'ownership_fields', 'discovery_lines'} != {'capacity', 'discovery_batch', 'points', 'authority', 'method'}
                or type(selected['capacity']) is not int or not 1 <= selected['capacity'] <= 5
                or type(selected['discovery_batch']) is not int or not 1 <= selected['discovery_batch'] <= 64
                or not isinstance(selected['points'], list) or set(selected['points']) - value['points'].keys()
                or selected['method'] not in task['templates']):
            raise Refusal('local integration needs selected methods, points and finite concurrent capacities')
        if 'ownership_fields' in selected and (not isinstance(selected['ownership_fields'], list)
                or not all(isinstance(f, str) and f for f in selected['ownership_fields'])):
            raise Refusal('controller-selected ownership fields must be explicit names')
        if 'new_point_prefix' in selected:
            required_text(selected['new_point_prefix'], 'authorized new point namespace', 128)
        if 'discovery_lines' in selected and not isinstance(selected['discovery_lines'], list):
            raise Refusal('discovery lines must be an explicit controller selection list')
        for line in selected.get('discovery_lines', []):
            if not isinstance(line, dict) or set(line) != {'line', 'incarnation', 'authority'}:
                raise Refusal('discovery needs a genuinely controller-selected line/incarnation/authority')
            for field in line:
                required_text(line[field], 'discovery '+field, 4000)
        required_text(selected['authority'], 'genuinely delegated routine local decision authority', 4000)
    for key, point in value['points'].items():
        required_text(key, 'stable logical point key', 256)
        if (not isinstance(point, dict)
                or set(point) != {'kind', 'line', 'incarnation', 'bindings', 'resources', 'protected', 'writable'}
                or point['kind'] not in {'item', 'relation', 'invariant'}
                or not isinstance(point['bindings'], list) or not point['bindings']
                or not isinstance(point['resources'], list) or not isinstance(point['protected'], list)
                or not isinstance(point['writable'], list)):
            raise Refusal('point needs kind, delivery line, incarnation, bindings, resources and protected ownership fields')
        for field in ('line', 'incarnation'):
            required_text(point[field], 'point '+field, 256)
        for resource in point['resources']:
            required_text(resource, 'actual point/session/branch/resource exclusion key', 4000)
        for field in point['protected'] + point['writable']:
            required_text(field, 'protected ownership/identity field', 256)
        for binding in point['bindings']:
            if not isinstance(binding, dict):
                raise Refusal('typed file or native point binding required')
            if 'native' in binding:
                from .local_native import validate_binding
                validate_binding(binding)
                if point['writable']:
                    raise Refusal('native state changes use original admitted interfaces, never point replacement rights')
                continue
            if (not isinstance(binding, dict) or set(binding) != {'target', 'path'}
                    or not isinstance(binding['path'], list) or not binding['path']
                    or not Path(binding['target']).is_absolute() or '..' in Path(binding['target']).parts
                    or Path(binding['target']).name == 'WORK_LOG.md'):
                raise Refusal('exact non-log stable target selector required')
            for segment in binding['path']:
                if isinstance(segment, str):
                    required_text(segment, 'object key', 4000)
                elif (not isinstance(segment, dict) or set(segment) != {'field', 'value'}
                      or not isinstance(segment['field'], str) or not isinstance(segment['value'], str)
                      or not segment['value']):
                    raise Refusal('array indices/line hints cannot resolve point identity; use a stable field/value')
        for name, selected in value['tasks'].items():
            if key not in selected['points']:
                continue
            task = config['tasks'][name]
            roots = task['effect_authority']['read_roots'] + task['effect_authority']['write_roots']
            targets = task.get('routine_completion', {}).get('targets')
            for binding in point['bindings']:
                if 'native' in binding:
                    from .local_native import validate_task
                    validate_task(config, name, binding)
                    continue
                path = Path(binding['target'])
                if (not any(path.is_relative_to(Path(root)) for root in roots)
                        or targets is not None and str(path) not in targets
                        or any(path == Path(p) or path.is_relative_to(Path(p)) for p in config.get('artifact_exclusions', []))):
                    raise Refusal('point binding exceeds genuine task/consumer access policy')
    return value


def selected(store, task):
    return store.config.get('local_integration', {}).get('tasks', {}).get(task)


def point_definitions(store):
    result = dict(store.config['local_integration']['points'])
    for row in store.rows('SELECT * FROM local_discovered_points'):
        if row['policy'] == digest(store.config['local_integration']):
            if row['point'] in result:
                raise Refusal('discovered point collides with selected original identity')
            result[row['point']] = json.loads(row['definition'])
    return result


def allowed_points(store, task):
    value = selected(store, task)
    keys = set(value['points'])
    prefix = value.get('new_point_prefix')
    if prefix:
        keys.update(k for k in point_definitions(store) if k.startswith(prefix))
    return keys


def validate_discovered(store, job, answer, bodies, *, native_only=False):
    discovered = answer.get('completion', {}).get('discovered_points', {})
    if not discovered:
        return {}
    scope = scope_for(store, job)
    prefix = selected(store, job['task']).get('new_point_prefix')
    if (scope['lane'] != 'discovery' or not prefix or not isinstance(discovered, dict)
            or len(discovered) > 64 or set(discovered) & point_definitions(store).keys()
            or any(not isinstance(k, str) or not k.startswith(prefix) for k in discovered)):
        raise Refusal('new identities require authorized central discovery namespace; existing points cannot be reparented')
    candidate = copy.deepcopy(store.config)
    candidate['local_integration']['points'].update(discovered)
    for name, task in candidate['local_integration']['tasks'].items():
        if task.get('new_point_prefix') == prefix:
            task['points'].extend(discovered)
    policy(candidate)
    if native_only and any('native' not in b for p in discovered.values() for b in p['bindings']):
        raise Refusal('file discovery requires original complete consumer publication')
    permitted_lines = {(point_definitions(store)[k]['line'], point_definitions(store)[k]['incarnation'])
                       for k in selected(store, job['task'])['points']}
    permitted_lines.update((v['line'], v['incarnation']) for v in selected(store, job['task']).get('discovery_lines', []))
    # Authorize every native operand before snapshotting any candidate. This
    # shared gate covers both file and non-file discovery/registration.
    from .local_native import authorize_scope
    for definition in discovered.values():
        for binding in definition['bindings']:
            if 'native' in binding:
                authorize_scope(store, job, binding)
    for key, definition in discovered.items():
        if set(selected(store, job['task']).get('ownership_fields', [])) - set(definition['protected']):
            raise Refusal('discovered points must retain controller-selected ownership protection')
        if (definition['line'], definition['incarnation']) not in permitted_lines:
            raise Refusal('discovery cannot introduce another delivery line under existing authority')
        if any(value is None for value in point_value(definition, bodies, store=store, job=job)):
            raise Refusal('new point needs uniquely resolved stable canonical identity after discovery')
    return discovered


def packet(store, row):
    """Normalize input without trusting its title, hinted rows or authority."""
    selected_policy = selected(store, row['task'])
    if not selected_policy:
        return None
    event = store.event(row['event'])
    raw = event.get('integration')
    if raw is None and isinstance(event.get('body'), dict):
        raw = event['body'].get('integration')
    if raw is None:
        return {'lane': 'discovery', 'reads': [], 'writes': [], 'versions': {}, 'sources': [event['id']]}
    if isinstance(raw, dict) and set(raw) == {'unresolved_existing'}:
        required_text(raw['unresolved_existing'], 'owned existing identity/interface dependency', 4000)
        raise Refusal('known existing work needs identity/interface resolution, not new-work duplication: '+raw['unresolved_existing'])
    if (not isinstance(raw, dict) or set(raw) != {'reads', 'writes', 'versions'}
            or any(not isinstance(raw[k], list) or not all(isinstance(v, str) for v in raw[k])
                   or len(raw[k]) != len(set(raw[k])) for k in ('reads', 'writes'))
            or not isinstance(raw['versions'], dict)):
        raise Refusal('normalized point read/write/version metadata required')
    keys = set(raw['reads']) | set(raw['writes'])
    if (not keys or keys - set(allowed_points(store, row['task'])) or set(raw['versions']) != keys
            or any(not isinstance(v, str) for v in raw['versions'].values())):
        raise Refusal('unresolved point/line/incarnation or incomplete version basis; discovery required')
    return {'lane': 'anchored', **copy.deepcopy(raw), 'sources': [event['id']]}


def conflict(left, right):
    return bool(set(left['writes']) & (set(right['reads']) | set(right['writes']))
                or set(right['writes']) & set(left['reads']))


def binding_conflict(store, left, right):
    """Different aliases/parent lenses still address the same logical material."""
    points = point_definitions(store)
    def overlap(a, b):
        return any(material_overlap(x, y) for x in footprints(store, points[a]) for y in footprints(store, points[b]))
    return (any(overlap(a, b) for a in left['writes'] for b in set(right['reads']) | set(right['writes']))
            or any(overlap(a, b) for a in right['writes'] for b in left['reads']))


def combine(scopes):
    return {'lane': scopes[0]['lane'],
            'reads': sorted({k for s in scopes for k in s['reads']}),
            'writes': sorted({k for s in scopes for k in s['writes']}),
            'sources': [k for s in scopes for k in s['sources']],
            'inputs': scopes,
            'mode': 'discovery' if scopes[0]['lane'] == 'discovery' else 'reconcile' if len(scopes) > 1 else 'direct'}


def members(store, row):
    first = packet(store, row)
    rows = store.rows("SELECT q.* FROM queue q JOIN events e ON q.event=e.id WHERE q.task=? "
                      "AND q.state='queued' AND e.hold IS NULL ORDER BY e.received,q.id", (row['task'],))
    candidates = []
    for candidate in rows:
        if candidate['id'] == row['id']:
            continue
        if store.processing and not store.processing.task(candidate):
            continue
        if candidate['package'] != row['package']:
            continue  # Execution lineage is never a reducible logical point.
        try:
            other = packet(store, candidate)
        except Refusal:
            continue  # Its own reservation records the specific dependency; unrelated points progress.
        if (first['lane'] == 'discovery' and other['lane'] == 'discovery'
                or first['lane'] == 'anchored' and other['lane'] == 'anchored' and (conflict(first, other) or binding_conflict(store, first, other))):
            candidates.append(candidate)
    count = selected(store, row['task'])['discovery_batch'] if first['lane'] == 'discovery' else 2
    return [store._input_member(r) for r in [row, *candidates[:count-1]]]


def scope_for(store, job):
    if not selected(store, job['task']):
        return None
    row = store.one('SELECT * FROM local_jobs WHERE job=?', (job['id'],))
    return json.loads(row['scope']) if row else None


def resources(store, scope):
    points = point_definitions(store)
    result = {r for k in set(scope['reads']) | set(scope['writes']) for r in points[k]['resources']}
    from .local_native import snapshot
    for key in set(scope['reads']) | set(scope['writes']):
        for binding in points[key]['bindings']:
            if 'native' in binding:
                result.update(snapshot(store, binding)[1])
    return result


def available(store, row, members):
    scopes = [packet(store, {**row, 'event': m['event']}) for m in members]
    scope = combine(scopes)
    native_access(store, row, scope)
    active = [j for j in store.rows("SELECT * FROM jobs WHERE state!='closed'") if not store.execution_complete(j)]
    if sum(bool(selected(store, j['task'])) for j in active) >= store.config['local_integration']['max_inflight']:
        return False
    wanted = resources(store, scope)
    from .local_native import busy
    if busy(store, wanted):
        return False
    if any(store.one('SELECT attempt FROM ordinary_resources WHERE resource=?', (r,)) for r in wanted):
        return False
    for job in active:
        prior = scope_for(store, job)
        if not prior:
            if job['role'] == row['role']:
                return False  # Unknown earlier material remains fenced.
            continue
        if scope['lane'] == prior['lane'] == 'discovery':
            return False
        if (conflict(scope, prior) or binding_conflict(store, scope, prior)
                or wanted & resources(store, prior)):
            return False
        sources = [store.event(m['event']) for m in json.loads(job['members'])]
        incoming = [store.event(m['event']) for m in members]
        branch = {e.get('branch_binding') for e in sources} - {None}
        if branch & ({e.get('branch_binding') for e in incoming} - {None}):
            return False
    return True


def record_job(store, job):
    if not selected(store, job['task']):
        return
    scope = combine([packet(store, {'task': job['task'], 'event': m['event']}) for m in json.loads(job['members'])])
    if scope['lane'] == 'discovery':
        # Cross-package candidates are read-only discovery inputs, not execution
        # members. Their package/admission and processing duties stay original.
        remaining = selected(store, job['task'])['discovery_batch'] - len(scope['sources'])
        neighbors = []
        for row in store.rows("SELECT q.* FROM queue q JOIN events e ON e.id=q.event WHERE q.task=? AND q.state='queued' AND e.hold IS NULL ORDER BY e.received,q.id", (job['task'],)):
            if len(neighbors) >= remaining:
                break
            if row['event'] in scope['sources'] or store.processing and not store.processing.task(row):
                continue
            try:
                candidate = packet(store, row)
            except Refusal:
                continue
            if candidate['lane'] == 'discovery':
                neighbors.append(store._input_member(row))
        scope['neighbors'] = neighbors
    store.db.execute('INSERT INTO local_jobs VALUES(?,?,?)', (job['id'], digest(store.config['local_integration']), encode(scope)))


def current_job(store, job):
    frozen = store.one('SELECT * FROM local_jobs WHERE job=?', (job['id'],))
    if not frozen:
        return
    if frozen['policy'] != digest(store.config.get('local_integration')):
        raise Refusal('local policy/authority changed; retain recorded revision and return through review')
    scope = json.loads(frozen['scope'])
    native_access(store, job, scope)
    for member in [*json.loads(job['members']), *scope.get('neighbors', [])]:
        queue = store.one('SELECT * FROM queue WHERE id=?', (member['queue'],))
        if (not queue or store._input_member(queue) != member
                or store.one('SELECT hold FROM events WHERE id=?', (member['event'],))['hold']
                or store.processing and not store.processing.task(queue)):
            raise Refusal('local member currentness/admission changed')


def locate(document, path, missing=False, missing_value=None):
    value = document
    for index, segment in enumerate(path):
        if isinstance(segment, dict):
            if not isinstance(value, list):
                raise Refusal('stable selector container changed')
            matches = [v for v in value if isinstance(v, dict) and v.get(segment['field']) == segment['value']]
            if not matches and missing and index == len(path)-1:
                return missing_value
            if len(matches) != 1:
                raise Refusal('stable point selector is missing or ambiguous')
            value = matches[0]
        else:
            if not isinstance(value, dict):
                raise Refusal('point object schema changed')
            if segment not in value and missing and index == len(path)-1:
                return missing_value
            if segment not in value:
                raise Refusal('stable point path missing')
            value = value[segment]
    return value


def native_access(store, job, scope):
    from .local_native import authorize
    for key in set(scope['reads']) | set(scope['writes']):
        for binding in point_definitions(store)[key]['bindings']:
            if 'native' in binding:
                authorize(store, job, binding)


def point_value(point, bodies, *, store=None, job=None):
    from .local_native import snapshot
    values = []
    for binding in point['bindings']:
        if 'native' not in binding:
            absent = object()
            value = locate(parse_json(bodies[binding['target']]), binding['path'], missing=True, missing_value=absent)
            values.append({'exists': value is not absent, 'value': None if value is absent else value})
            continue
        value = snapshot(store, binding, job)[0]
        if binding['native'] == 'branch':
            incarnation = value['association']['incarnation']
        elif binding['native'] == 'review':
            incarnation = value['context']['run'] or value['context']['handle']
        else:
            incarnation = digest(value['admission']['receipt'])
        if point['incarnation'] != incarnation:
            raise Refusal('native point incarnation differs from its actual original lifecycle')
        values.append(value)
    return values


def material_overlap(left, right):
    if left['target'] != right['target']:
        return False
    common = min(len(left['path']), len(right['path']))
    return left['path'][:common] == right['path'][:common]


def footprints(store, point, bodies=None, job=None):
    """Resolve selector aliases to actual material, without changing authority.

    Array positions here are observations of an already unique stable selector,
    never caller-provided identities. Inode changes/reordering invalidate bases.
    """
    from .custody import guard_path, read_file, safe_path
    from .local_native import snapshot
    result = []
    for binding in point['bindings']:
        if 'native' in binding:
            _, resources = snapshot(store, binding, job)
            result.extend({'target': ['native', key], 'path': []} for key in sorted(resources))
            continue
        target = binding['target']
        guard_path(store, target)
        path = safe_path(target, [target])
        info = path.stat()
        body = bodies[target] if bodies is not None and target in bodies else read_file(path, store.config['limits'].get('max_artifact_bytes', 33554432))[0]
        value, resolved = parse_json(body), []
        for index, segment in enumerate(binding['path']):
            if isinstance(segment, dict):
                if not isinstance(value, list):
                    raise Refusal('stable selector container changed')
                matches = [(i, v) for i, v in enumerate(value) if isinstance(v, dict) and v.get(segment['field']) == segment['value']]
                if len(matches) != 1:
                    raise Refusal('stable point selector is missing or ambiguous')
                offset, value = matches[0]
                resolved.append(['member', offset])
            else:
                if not isinstance(value, dict) or segment not in value and index != len(binding['path'])-1:
                    raise Refusal('stable point path missing or schema changed')
                value = value.get(segment)
                resolved.append(['field', segment])
        result.append({'target': ['file', info.st_dev, info.st_ino], 'path': resolved})
    return result


def version(store, key, bodies, job=None):
    point = point_definitions(store)[key]
    row = store.one('SELECT generation FROM local_point_versions WHERE point=?', (key,))
    material = footprints(store, point, bodies, job)
    generation = max((r['seq'] for r in store.rows('SELECT seq,footprints FROM local_material_commits')
                      if any(material_overlap(a, b) for a in material for b in json.loads(r['footprints']))), default=0)
    return digest({'point': point, 'generation': row['generation'] if row else 0,
                   'material': material, 'material_generation': generation,
                   'values': point_value(point, bodies, store=store, job=job)})


def prepare(store, job, attempt, before):
    scope = scope_for(store, job)
    if scope is None:
        return
    from .custody import frozen_body
    bodies = {p: frozen_body(store, v['sha256'], path=p)['body'] for p, v in before.items() if v.get('sha256')}
    keys = set(scope['reads']) | set(scope['writes'])
    versions = {k: version(store, k, bodies, job) for k in keys}
    stale = any(s['versions'].get(k) != versions[k] for s in scope['inputs'] for k in set(s['reads']) | set(s['writes']))
    basis = {'scope': {**scope, 'mode': 'reconcile' if stale and scope['lane'] == 'anchored' else scope['mode']},
             'versions': versions, 'points': {k: point_definitions(store)[k] for k in keys},
             'policy': digest(store.config['local_integration'])}
    store.db.execute('INSERT INTO local_bases VALUES(?,?)', (attempt, encode(basis)))


def prepare_input_basis(store, job, attempt, task):
    """Bind report/review/ordinary preparation to its current point revision.

    Read-only work can finish on this recorded revision. Its outgoing metadata
    remains on that revision so later material returns through reconciliation.
    """
    if not selected(store, job['task']) or task.get('routine_completion'):
        return
    from .custody import read_file, safe_path
    from .publication import snapshot_lock
    from contextlib import nullcontext
    scope = scope_for(store, job)
    keys = set(scope['reads']) | set(scope['writes'])
    points = point_definitions(store)
    roots = task['effect_authority']['read_roots'] + task['effect_authority']['write_roots']
    targets = {b['target'] for k in keys for b in points[k]['bindings'] if 'target' in b}
    maximum = store.config['limits'].get('max_artifact_bytes', 33554432)
    with (snapshot_lock(store) if store.config.get('canonical_publication') else nullcontext()):
        bodies = {p:read_file(safe_path(p, roots), maximum)[0] for p in targets}
        versions = {k:version(store,k,bodies,job) for k in keys}
    stale = any(s['versions'].get(k) != versions[k] for s in scope['inputs'] for k in set(s['reads'])|set(s['writes']))
    basis = {'scope':{**scope,'mode':'reconcile' if stale and scope['lane']=='anchored' else scope['mode']},
             'versions':versions,'points':{k:points[k] for k in keys},'policy':digest(store.config['local_integration'])}
    with store.tx():
        store.db.execute('INSERT INTO local_bases VALUES(?,?)', (attempt, encode(basis)))


def current_basis(store, job):
    """Before new native effects, require the decision's actual read revision.

    Read-only reports retain their original revision. An existing native intent
    is never replayed, and its own mutations are reconciled by its original API.
    """
    if not selected(store, job['task']):
        return
    row = store.one('SELECT basis FROM local_bases WHERE attempt=?', (job['active_attempt'],))
    if not row:
        raise Refusal('scoped native effects need their prepared decision basis')
    basis = json.loads(row['basis'])
    current_job(store, job)
    if basis['scope']['lane'] == 'discovery':
        raise Refusal('new native effects await a scoped anchored continuation after central discovery')
    from .custody import guard_path, safe_path, read_file
    targets = {b['target'] for p in basis['points'].values() for b in p['bindings'] if 'target' in b}
    bodies = {}
    for path in targets:
        guard_path(store, path)
        bodies[path] = read_file(safe_path(path, [path]), store.config['limits'].get('max_artifact_bytes', 33554432))[0]
    if any(version(store, key, bodies, job) != expected for key, expected in basis['versions'].items()):
        raise Refusal('relevant native/relationship read-set is stale; reconcile before new effects')


def native_intent(store, job):
    """Retain possible cooperative mutations even if later bytes are restored."""
    scope = scope_for(store, job)
    if not scope:
        return
    material = [f for key in scope['writes'] for f in footprints(store, point_definitions(store)[key], job=job)]
    store.budget(None, len(encode(material).encode())+4096)
    store.db.execute('INSERT INTO local_material_commits(attempt,footprints) VALUES(?,?)',
                     (job['active_attempt'], encode(material)))


def finish_discovery(store, job, attempt, answer):
    """Non-file discovery links existing native identities after original gates.

    It creates no branch/ref/session/run, owner acceptance or execution right.
    Actual new Work records continue through the seven-consumer publisher.
    """
    scope = scope_for(store, job)
    discovered = answer.get('completion', {}).get('discovered_points', {})
    if not scope or scope['lane'] != 'discovery' or not discovered:
        return
    if store.one('SELECT attempt FROM local_commits WHERE attempt=?', (attempt['id'],)):
        return
    definitions = validate_discovered(store, job, answer, {}, native_only=True)
    basis = store.one('SELECT basis FROM local_bases WHERE attempt=?', (attempt['id'],))
    if not basis:
        raise Refusal('native discovery requires original prepared method basis')
    receipt = {'basis': json.loads(basis['basis']), 'discovered': definitions, 'sources': json.loads(job['members']),
               'footprints': [], 'state': 'intent', 'meaning': 'existing native references only; no native effect or acceptance'}
    with (nullcontext() if store.db.in_transaction else store.tx()):
        store.db.execute('INSERT INTO local_commits VALUES(?,?,?)', (attempt['id'], 'intent', encode(receipt)))
        committed(store, attempt['id'], receipt)


def context(store, job):
    row = store.one('SELECT basis FROM local_bases WHERE attempt=?', (job['active_attempt'],)) if job['active_attempt'] else None
    basis = json.loads(row['basis']) if row else scope_for(store, job)
    if not selected(store, job['task']):
        return None
    scope = basis.get('scope', basis) if basis else {}
    prior = []
    for key in sorted(set(scope.get('reads', [])) | set(scope.get('writes', []))):
        previous = store.one('SELECT * FROM local_point_commits WHERE point=? ORDER BY generation DESC LIMIT 1', (key,))
        if previous:
            commit = store.one('SELECT receipt FROM local_commits WHERE attempt=?', (previous['attempt'],))
            prior.append({**previous, 'source_members':json.loads(commit['receipt'])['sources'],
                          'meaning':'relevant prior decision/source reference; no historical body access or current verdict inferred'})
    neighbors = [store.event(m['event']) for m in scope.get('neighbors', [])]
    return {'basis': basis, 'discovery_neighbors':neighbors, 'prior_point_commits': prior, 'decision_authority': selected(store, job['task'])['authority'], 'steps': STEPS,
            'discovery_points': {k:v for k,v in point_definitions(store).items() if k in allowed_points(store, job['task'])} if basis and
            (basis.get('scope', basis)).get('lane') == 'discovery' else None,
            'instructions': 'Direct current anchored changes need no global window. Reconcile conflicts/stale bases with the selected Observe/Frame/Decide/Act method; record each step and rationale in completion.integration_steps. Discovery compares existing points and all selected new candidates, preserves unassigned/proposed ownership, emits anchored integration read/write/versions and scoped handoffs. Broader concerns go as point-specific required settled handoffs. No title ownership, acceptance invention or revised review verdict. Edit only supplied stages; the service validates/rebases point deltas. User-owned choices return as scope/blocker.'}


def replace(document, path, value):
    parent = locate(document, path[:-1]) if path[:-1] else document
    leaf = path[-1]
    if isinstance(leaf, dict):
        matches = [i for i, v in enumerate(parent) if isinstance(v, dict) and v.get(leaf['field']) == leaf['value']]
        if len(matches) != 1:
            raise Refusal('write requires a uniquely resolved existing point; new identities use discovery')
        parent[matches[0]] = value
    else:
        parent[leaf] = value


def typed_equal(left, right):
    """JSON equality conserves types recursively, including bool/int and counts."""
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(typed_equal(v, right[k]) for k, v in left.items())
    if isinstance(left, list):
        return len(left) == len(right) and all(typed_equal(a, b) for a, b in zip(left, right))
    return left == right


def field_equal(before, after, key):
    """Field rights conserve presence as well as the typed JSON value."""
    return (key in before) == (key in after) and (key not in before or typed_equal(before[key], after[key]))


def conserve(before, after, protected, ownership=OWNERSHIP):
    if type(before) is not type(after):
        raise Refusal('point value type changed; explicit schema/authority decision required')
    if isinstance(before, dict):
        if not isinstance(after, dict) or before.keys() - after.keys():
            raise Refusal('point delta drops unknown/history/source fields')
        for key in before.keys() | after.keys():
            if key in protected and not field_equal(before, after, key):
                raise Refusal('local delta cannot change accepted ownership/identity; explicit owner policy needed')
        for key, value in before.items():
            conserve(value, after[key], protected, ownership)
        for key in after.keys() - before.keys():
            no_acceptance({key: after[key]}, ownership)
    elif isinstance(before, list):
        # Preserve multiplicity as well as value, including non-object members.
        remaining = list(after)
        for item in before:
            match = next((i for i, value in enumerate(remaining) if typed_equal(item, value)), None)
            if match is None:
                raise Refusal('point delta drops peer/history/source array members')
            remaining.pop(match)
        for item in remaining:
            no_acceptance(item, ownership)


def no_acceptance(value, ownership):
    if isinstance(value, dict):
        for key, child in value.items():
            if key in ownership and child not in (None, False, '', 'unassigned'):
                raise Refusal('discovery may propose ownership but cannot manufacture acceptance')
            no_acceptance(child, ownership)
    elif isinstance(value, list):
        for child in value:
            no_acceptance(child, ownership)


def validate_delta(before, after, point, binding, ownership=OWNERSHIP):
    protected = set(point['protected']) | IDENTITY | set(ownership)
    # A scalar ownership/identity/history lens must not escape its containing
    # field's protection just because the configured point ends inside it.
    ancestors = {s for s in binding['path'] if isinstance(s, str)}
    if (ancestors & protected or '$value' in protected) and not typed_equal(before, after):
        raise Refusal('local delta cannot change accepted ownership/identity/protected value')
    if isinstance(before, dict) and isinstance(after, dict):
        if any(not field_equal(before, after, field) for field in protected):
            raise Refusal('local delta cannot change accepted ownership/identity; explicit owner policy needed')
        if any(not field_equal(before, after, field) for field in before.keys() | after.keys() if field not in point['writable']):
            raise Refusal('point delta changes an unselected/unknown field')
    elif not typed_equal(before, after) and '$value' not in point['writable']:
        raise Refusal('non-object point delta requires explicit $value writable authority')
    conserve(before, after, protected, ownership)


def conserve_bound_views(store, original, proposals, ownership=OWNERSHIP):
    """An alternate lens cannot remove another admitted view's protection.

    Compare only files already in this exact publisher's authority. This grants
    no cross-role catalog reads; writable rights still come from its write-set.
    """
    for point in point_definitions(store).values():
        protected = set(point['protected']) | IDENTITY | set(ownership)
        for binding in point['bindings']:
            target = binding.get('target')
            if target not in original:
                continue
            absent = object()
            before = locate(original[target], binding['path'], missing=True, missing_value=absent)
            after = locate(proposals[target], binding['path'], missing=True, missing_value=absent)
            if typed_equal(before, after):
                continue
            ancestors = {s for s in binding['path'] if isinstance(s, str)}
            if '$value' in protected or ancestors & protected:
                raise Refusal('overlapping admitted view retains protected ownership/identity/value')
            if before is absent:
                no_acceptance(after, ownership)
            else:
                conserve(before, after, protected, ownership)


def discovery_conservation(before, after, ownership=()):
    ownership = set(ownership) | OWNERSHIP
    conserve(before, after, ownership, ownership)
    def proposed(value):
        if isinstance(value, dict):
            for key, child in value.items():
                if key in ownership and child not in (None, False, '', 'unassigned'):
                    raise Refusal('discovery may propose ownership but cannot manufacture acceptance')
                proposed(child)
        elif isinstance(value, list):
            for child in value: proposed(child)
    if isinstance(before, dict) and isinstance(after, dict):
        for key, value in after.items():
            if key not in before: proposed(value)
            else: discovery_conservation(before[key], value, ownership)
    elif isinstance(before, list) and isinstance(after, list):
        for value in after:
            if not any(typed_equal(value, old) for old in before): proposed(value)


def validate_method(store, job, attempt, answer):
    scope = scope_for(store, job)
    if scope is None:
        return
    row = store.one('SELECT basis FROM local_bases WHERE attempt=?', (attempt['id'],))
    mode = json.loads(row['basis'])['scope']['mode'] if row else scope['mode']
    if mode in {'reconcile', 'discovery'}:
        steps = answer.get('completion', {}).get('integration_steps')
        if (not isinstance(steps, list) or len(steps) != 4 or not all(isinstance(s, dict) for s in steps)
                or [s.get('step') for s in steps] != STEPS):
            raise Refusal('scoped reconciliation/discovery requires all four selected method returns')
        for step in steps:
            required_text(step.get('evidence'), 'actual local method evidence/rationale', 16000)


def rebase(store, job, attempt, run, task):
    """Return an exact current run and service-derived postimages under the lock.

    Every file still publishes through the durable original publisher. The
    original model stages/preimages remain intact as separate custody sources.
    """
    from . import publication, bounded_log
    from .custody import frozen_body, read_file, safe_path
    row = store.one('SELECT basis FROM local_bases WHERE attempt=?', (attempt['id'],))
    if not row:
        return run, None
    current_job(store, job)
    basis = json.loads(row['basis'])
    if basis['policy'] != digest(store.config['local_integration']):
        raise Refusal('local decision authority/point bindings changed')
    old_commit = store.one('SELECT * FROM local_commits WHERE attempt=?', (attempt['id'],))
    if old_commit:
        raise Refusal('local publication already has a durable intent; reconcile original effects, never replay')
    answer = collected_task_result(attempt)
    validate_method(store, job, attempt, answer)
    policy = task['routine_completion']
    order = bounded_log.inventory(policy) if bounded_log.selected(task) else policy['targets']
    maximum = store.config['limits'].get('max_artifact_bytes', 33554432)
    before = json.loads(run['before_files'])
    original = {p: frozen_body(store, before[p]['sha256'], task, p)['body'] for p in order}
    fresh = {}
    bodies = {}
    for target in order:
        body, witness = read_file(safe_path(target, order), maximum)
        fresh[target] = {'exists': True, **witness}
        bodies[target] = body
        if any(witness[k] != before[target][k] for k in ('dev', 'ino', 'uid', 'gid', 'mode')):
            raise Refusal('canonical identity/ownership changed; re-resolve current point incarnation')
    for key, expected in basis['versions'].items():
        if version(store, key, bodies, job) != expected:
            raise Refusal('relevant point/relationship/absence read-set is stale; local reconciliation required')
    allocated = publication.stages(store, attempt['id'])
    staged = {}
    for target in order:
        body, witness = read_file(safe_path(allocated[target], [str(store.home/'artifacts'/attempt['id']/'staged')]), maximum)
        held = store.one('SELECT sha256 FROM artifact_custody WHERE attempt=? AND path=?', (attempt['id'], allocated[target]))
        if not held or held['sha256'] != witness['sha256']:
            raise Refusal('local model stage lacks exact durable custody')
        staged[target] = body
    ownership = OWNERSHIP | set(selected(store, job['task']).get('ownership_fields', []))
    rebased = dict(bodies)
    if basis['scope']['lane'] == 'discovery':
        # Unanchored changes still require current full preimages. Anchored work
        # never waits for this batch; discovery emits point-specific continuations.
        if any(original[p] != bodies[p] for p in order):
            raise Refusal('discovery catalog basis changed; fresh identity/relationship discovery required')
        conserve_bound_views(store, {p:parse_json(v) for p,v in original.items() if p.endswith('.json')},
                             {p:parse_json(v) for p,v in staged.items() if p.endswith('.json')}, ownership)
        for target in order:
            if target.endswith('.json'):
                discovery_conservation(parse_json(original[target]), parse_json(staged[target]), selected(store, job['task']).get('ownership_fields', []))
            elif original[target] not in staged[target]:
                raise Refusal('discovery must conserve existing text/history')
        for key in allowed_points(store, job['task']):
            point_value(point_definitions(store)[key], staged, store=store, job=job)  # Duplicate stable IDs cannot enter through discovery.
        rebased = staged
    else:
        expected = {p: parse_json(original[p]) for p in order if p.endswith('.json')}
        merged = {p: parse_json(bodies[p]) for p in expected}
        proposals = {p: parse_json(staged[p]) for p in expected}
        conserve_bound_views(store, expected, proposals, ownership)
        for key in basis['scope']['writes']:
            point = basis['points'][key]
            for binding in point['bindings']:
                if 'native' in binding:
                    raise Refusal('native mutations require their original admitted effect interface, never file publication')
                target, path = binding['target'], binding['path']
                if target not in proposals:
                    raise Refusal('point mutations require JSON bindings; text consumers retain additive supplements')
                old = locate(expected[target], path)
                new = locate(proposals[target], path)
                validate_delta(old, new, point, binding, ownership)
                replace(expected[target], path, new)
                replace(merged[target], path, new)
        for target in order:
            if target in expected:
                if not typed_equal(expected[target], proposals[target]):
                    raise Refusal('staged change exceeds resolved point write-set')
                rebased[target] = bodies[target] if typed_equal(merged[target], parse_json(bodies[target])) else (encode(merged[target])+'\n').encode()
            elif staged[target] == original[target]:
                rebased[target] = bodies[target]
            elif staged[target].endswith(original[target]) and original[target]:
                rebased[target] = staged[target][:-len(original[target])] + bodies[target]
            elif staged[target].startswith(original[target]) and original[target]:
                rebased[target] = bodies[target] + staged[target][len(original[target]):]
            else:
                raise Refusal('text consumer must conserve peer text with an additive supplement')
    discovered = validate_discovered(store, job, answer, rebased)
    # Materialize new immutable service stages, preserving model postimages and
    # input custody. Publication validates both mapping and exact fresh preimages.
    root = store.home/'artifacts'/attempt['id']/'local-commit'
    root.mkdir(mode=0o700)
    service = {}
    for index, target in enumerate(order):
        path = root/str(index)
        store.budget(None, len(rebased[target])+len(bodies[target])+4096)
        import os
        fd = os.open(path, os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(rebased[target]); stream.flush(); os.fsync(stream.fileno())
        # Reuse exact custody validation with an explicit service staging root.
        from .custody import capture
        capture(store, attempt['id'], str(path), task)
        service[target] = str(path)
        witness = fresh[target]
        store.db.execute('INSERT OR IGNORE INTO artifact_blobs VALUES(?,?)', (witness['sha256'], bodies[target]))
    if bounded_log.selected(task):
        fresh[policy['bounded_log']['target']] = bounded_log.observe(store, policy['bounded_log'])
    material = ([{'target': ['file', fresh[p]['dev'], fresh[p]['ino']], 'path': []} for p in order]
                if basis['scope']['lane'] == 'discovery' else
                [f for k in basis['scope']['writes'] for f in footprints(store, basis['points'][k], bodies, job)])
    receipt = {'basis': basis, 'discovered': discovered, 'footprints': material, 'model_stages': allocated, 'service_stages': service,
               'before': fresh, 'sources': json.loads(job['members']), 'state': 'intent'}
    with store.tx():
        store.db.execute('INSERT INTO local_commits VALUES(?,?,?)', (attempt['id'], 'intent', encode(receipt)))
    return {**run, 'before_files': encode(fresh)}, (service, receipt)


def committed(store, attempt, receipt):
    with (nullcontext() if store.db.in_transaction else store.tx()):
        store.budget(None, len(encode(receipt.get('footprints', [])).encode())+4096)
        store.db.execute('INSERT INTO local_material_commits(attempt,footprints) VALUES(?,?)',
                         (attempt, encode(receipt.get('footprints', []))))
        for key, definition in receipt.get('discovered', {}).items():
            store.db.execute('INSERT INTO local_discovered_points VALUES(?,?,?,?)',
                             (key, encode(definition), digest(store.config['local_integration']), attempt))
        scope = receipt['basis']['scope']
        changed = set(scope['writes'])
        for key in changed:
            store.db.execute('INSERT INTO local_point_versions VALUES(?,1) ON CONFLICT(point) DO UPDATE SET generation=generation+1', (key,))
            generation = store.one('SELECT generation FROM local_point_versions WHERE point=?', (key,))['generation']
            store.db.execute('INSERT INTO local_point_commits VALUES(?,?,?)', (key, generation, attempt))
        from .custody import read_file, safe_path
        writes = set(receipt['discovered']) | set(scope['writes'])
        keys = writes | set(scope['reads'])
        targets = {b['target'] for k in keys for b in point_definitions(store)[k]['bindings'] if 'target' in b}
        bodies = {p:read_file(safe_path(p, list(targets)), store.config['limits'].get('max_artifact_bytes', 33554432))[0] for p in targets}
        versions = {k:version(store,k,bodies) for k in keys}
        continuations = {k:{'reads':sorted(set(scope['reads'])-{k}), 'writes':[k],
                            'versions':{p:versions[p] for p in set(scope['reads'])|{k}}} for k in writes}
        store.db.execute("UPDATE local_commits SET state='published',receipt=? WHERE attempt=?", (encode({**receipt, 'state': 'published', 'continuations':continuations}), attempt))
