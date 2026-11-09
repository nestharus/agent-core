"""Consume original journal evidence for conditional cooperative admission.

Work owns its journal and software executor declarations. Reviews owns its
Source and reader declarations. Neither can certify Native physical ownership.
Current delegations use the existing metadata table, never a past witness.
"""
import json
import math
from pathlib import Path

from . import configuration, historical_verification as historical, processing, resource_scopes
from .contracts import Refusal, canonical_uuid, digest, encode, ident, required_text

MODE = 'cooperative-authorized-ceilings'
DOMAINS = {'work-journal': 'Work', 'reviews-source': 'Reviews'}
FIELDS = {
    'work-journal': ['job-lineage', 'launch-proof', 'original-epoch-birth',
                     'frozen-standalone-policy', 'public-read-membership', 'executor-ceiling'],
    'reviews-source': ['source-header', 'context-collector-links', 'reader-ceiling'],
}


def actor(runtime, boards, domain):
    role = DOMAINS[domain]
    owner = runtime.config['roles'][role]['owner']
    if boards[role].store.acting_session(owner) != owner:
        raise Refusal('actual current '+domain+' custodian principal required')
    return owner


def _paths(runtime, values):
    if (not isinstance(values, list) or len(values) > 32
            or any(not isinstance(p, str) for p in values) or len(values) != len(set(values))):
        raise Refusal('finite independently public ceiling operands required')
    return [str(resource_scopes.root(p, runtime.config.get('artifact_exclusions', []), metadata=False)) for p in values]


def _selection(runtime, domain, value):
    keys = {'identity', 'purpose', 'authority', 'expires', 'principal', 'configuration',
            'implementation', 'fields', 'ceiling'}
    keys |= {'preserved_bytes'} if domain == 'work-journal' else {'work_access'}
    if not isinstance(value, dict) or set(value) != keys or value['fields'] != FIELDS[domain]:
        raise Refusal('exact current custodian field scope required: '+domain)
    historical._identity(value['identity'])
    required_text(value['purpose'], 'current resource comparison purpose', 2000)
    required_text(value['authority'], 'actual entitled custodian current delegation', 2000)
    expiry = value['expires']
    if type(expiry) not in (int, float) or not math.isfinite(expiry) or not runtime.clock() < expiry <= runtime.clock()+3600:
        raise Refusal('current field scope must expire within one hour')
    if (value['principal'] != runtime.config['roles']['Work']['owner']
            or value['configuration'] != digest(runtime.config)
            or value['implementation'] != processing.implementation()):
        raise Refusal('current principal/source/configuration field binding differs')
    ceiling = value['ceiling']
    if (not isinstance(ceiling, dict) or set(ceiling) != {'mode', 'reads', 'writes', 'unbounded'}
            or ceiling['mode'] != MODE or ceiling['unbounded'] is not False):
        raise Refusal('opaque or unbounded relevant dependency remains held')
    _paths(runtime, ceiling['reads'])
    _paths(runtime, ceiling['writes'])
    if domain == 'reviews-source' and (ceiling['writes'] or not ceiling['reads']):
        raise Refusal('only a complete authorized read-only Source ceiling is supported')
    if domain == 'work-journal' and (type(value['preserved_bytes']) is not int or value['preserved_bytes'] < 0):
        raise Refusal('genuine Work preserved allocation bound required; no old capture accounting')
    return value


def _budget(runtime, scope, preserved, *, creating=True):
    from .capacity import PRESSURE_RESERVE
    if creating:
        historical._metadata_budget(runtime, scope)
    from .selected_source import custody_budget
    custody_budget(runtime, len(encode(scope).encode())+2048)
    retained = runtime.one('SELECT COALESCE(SUM(length(CAST(scope AS BLOB))+2048),0) AS n FROM historical_metadata_access')['n']
    publication = runtime.one("SELECT COUNT(*) AS n FROM file_publications WHERE state!='published'")['n']
    publication *= min(runtime.config['limits'].get('max_artifact_bytes', 33554432), runtime.config['limits']['max_bytes'])
    from .custodian_service import CAPTURE
    visits = runtime.one("SELECT COUNT(*) AS n FROM custodian_visits WHERE state IN ('prepared','running')")['n']
    if preserved + retained + len(encode(scope).encode()) + 4096 + publication + visits*(3*CAPTURE+4096) + PRESSURE_RESERVE >= runtime.config['limits']['max_bytes']:
        raise Refusal('preserved allocation and current metadata/reservation capacity do not fit')


def _row(runtime, key, domain):
    row = runtime.one('SELECT scope,issuer FROM historical_metadata_access WHERE id=?', (canonical_uuid(key),))
    if not row or runtime.one('SELECT id FROM historical_metadata_revocations WHERE id=?', (key,)):
        raise Refusal('current '+domain+' field scope absent/revoked')
    scope = json.loads(row['scope'])
    if scope.get('domain') != domain:
        raise Refusal('missing respective custodian field scope: '+domain)
    _selection(runtime, domain, scope['selection'])
    role = DOMAINS[domain]
    binding = processing_binding(runtime, scope, role)
    if row['issuer'] != binding['owner'] or scope['version'] != configuration.version_metadata(runtime):
        raise Refusal('current entitled field custodian/source binding changed: '+domain)
    return scope


def processing_binding(runtime, scope, role):
    # The immutable scope binds the original authenticated journal, not a title.
    binding = scope['binding']
    if binding['owner'] != runtime.config['roles'][role]['owner'] or binding['issuer'] != runtime.config['roles']['Work']['owner']:
        raise Refusal('original respective principal/issuer binding differs')
    return binding


def authorize(runtime, boards, domain, selection):
    if domain not in DOMAINS:
        raise Refusal('unknown historical field custodian')
    principal = actor(runtime, boards, domain)
    _selection(runtime, domain, selection)
    configuration.assert_current(runtime)
    with historical._transaction(runtime):
        return _authorize(runtime, boards, domain, selection, principal)


def _authorize(runtime, boards, domain, selection, principal):
    role = DOMAINS[domain]
    binding = boards[role].historical_authority(runtime, selection['identity']['task'] if role == 'Reviews' else None)
    scope = dict(domain=domain, selection=selection, binding=binding, version=configuration.version_metadata(runtime))
    preserved = selection.get('preserved_bytes')
    if domain == 'reviews-source':
        work = _row(runtime, selection['work_access'], 'work-journal')
        _same_selection(work['selection'], selection)
        if work['binding'] != boards['Work'].historical_authority(runtime):
            raise Refusal('original Work journal binding changed')
        historical._source_access(runtime, boards, selection['identity'], {'work': work['binding'], 'source': binding})
        preserved = work['selection']['preserved_bytes']
    scope['preserved_bytes'] = preserved
    _budget(runtime, scope, preserved)
    key = ident()
    runtime.db.execute('INSERT INTO historical_metadata_access VALUES(?,?,?,?)', (key, encode(scope), principal, runtime.clock()))
    return {'metadata_access': key, 'domain': domain, 'fields': FIELDS[domain], 'execution': False, 'physical': 'UNKNOWN'}


def _same_selection(work, source):
    for name in ('identity', 'purpose', 'principal', 'configuration', 'implementation'):
        if work[name] != source[name]:
            raise Refusal('independently delegated field selections do not join: '+name)


def _current(runtime, boards, keys):
    historical._work_actor(runtime, boards)  # Before even a selected scope read.
    configuration.assert_current(runtime)
    if not isinstance(keys, dict) or set(keys) != set(DOMAINS):
        raise Refusal('both actual Work-journal and Reviews-source field scopes required')
    work = _row(runtime, keys['work-journal'], 'work-journal')
    source = _row(runtime, keys['reviews-source'], 'reviews-source')
    if source['selection']['work_access'] != keys['work-journal']:
        raise Refusal('Source delegation belongs to another current Work selection')
    _same_selection(work['selection'], source['selection'])
    bindings = historical._bindings(runtime, boards, work['selection']['identity']['task'])
    if bindings != {'work': work['binding'], 'source': source['binding']}:
        raise Refusal('actual original journal/issuer/source relationships changed')
    return work['selection'], source['selection'], bindings


def _covered(column, paths):
    # Only independently nominated public operands are parameters. Unmatched
    # stored paths never cross SQL. No native handle/run/session is tested.
    return '(' + ' OR '.join('('+column+'=? OR substr('+column+',1,length(?)+1)=?||\'/\')' for _ in paths) + ')' if paths else '0'


def _parameters(paths):
    return tuple(v for p in paths for v in (p, p, p))


def _complete_policy(runtime, identity, reads):
    row = runtime.one("SELECT json_extract(task,'$.cwd') IN (SELECT value FROM json_each(?)) AS cwd,"
        "NOT EXISTS(SELECT 1 FROM json_each(task,'$.effect_authority.read_roots') WHERE type!='text' OR value NOT IN (SELECT value FROM json_each(?))) AS reads,"
        "json_type(task,'$.effect_authority.read_roots')='array' AS typed,"
        "json_type(task,'$.effect_authority.operations')='array' AND json_array_length(task,'$.effect_authority.operations')>0 AND NOT EXISTS(SELECT 1 FROM json_each(task,'$.effect_authority.operations') WHERE value NOT IN ('read-source','read-reports','prepare-intents','consolidate-reports')) AS operations,"
        "json_type(task,'$.routine_completion') IS NULL AS routine,"
        "COALESCE(json_array_length(task,'$.scope_exclusions'),0)=0 AS exclusions "
        'FROM job_resource_policies WHERE job=?', (encode(reads), encode(reads), identity['job']))
    if not row or not all(row.values()):
        raise Refusal('complete original frozen read/operation ceiling unavailable; Work journal custodian retains it')


def _material_ceiling(runtime, identity, reads):
    # Original caller/model material is included in the declared reader ceiling.
    query = "SELECT NOT EXISTS(SELECT 1 FROM review_calls c,json_each(c.packet,'$.method_files') p WHERE c.attempt=? AND (p.type!='text' OR NOT " + _covered('p.value', reads) + ')) AS methods,'
    query += "NOT EXISTS(SELECT 1 FROM review_calls c,json_each(c.packet,'$.prior_histories') p WHERE c.attempt=? AND NOT " + _covered('p.key', reads) + ') AS histories,'
    query += "json_type(packet,'$.method_files')='array' AND json_array_length(packet,'$.method_files')>0 AND json_type(packet,'$.prior_histories')='object' AND " + _covered("json_extract(packet,'$.repository')", reads) + ' AS repository FROM review_calls WHERE attempt=?'
    params = (identity['attempt'], *_parameters(reads), identity['attempt'], *_parameters(reads), *_parameters(reads), identity['attempt'])
    row = runtime.one(query, params)
    if not row or not all(row.values()):
        raise Refusal('complete original public Source material ceiling absent; Reviews/source custodian retains it')
    _caller_ceiling(runtime, identity, reads)


def _caller_ceiling(runtime, identity, reads):
    path = '$.service.reviews.'+json.dumps(identity['task'])
    query = "WITH original AS (SELECT json_extract(selection,?) AS caller,json_type(selection,?)='text' AND length(json_extract(selection,?))=64 AS pinned FROM processing_capabilities WHERE id=?) SELECT "
    query += _covered('caller', reads)+' AND pinned AS caller FROM original'
    row = runtime.one(query, (path+'.caller', path+'.caller_sha256', path+'.caller_sha256', identity['capability'], *_parameters(reads)))
    if not row or not row['caller']:
        raise Refusal('original public caller dependency absent from complete ceiling; original Work/source collector retains it')


def _executor_ceiling(runtime, identity, writes):
    mandatory = [str(runtime.artifact_root(identity['attempt'])), str(runtime.home/'review-inputs'/digest(identity['component'])),
                 str(runtime.home/'review-handles'), str(runtime.home/'review-history')]
    if any(not any(Path(p).is_relative_to(Path(w)) for w in writes) for p in mandatory):
        raise Refusal('declared software executor ceiling incomplete; original Work collector retains it')
    history = runtime.one('SELECT '+_covered("json_extract(packet,'$.history')", writes)+
                          ' AS covered FROM review_calls WHERE attempt=?', (*_parameters(writes), identity['attempt']))
    if not history or not history['covered']:
        raise Refusal('original public history destination exceeds current Work executor ceiling')
    query = "SELECT NOT EXISTS(SELECT 1 FROM review_history_commits h JOIN attempts a ON a.id=h.attempt WHERE a.job=? AND NOT " + _covered('h.path', writes) + ') AS histories,'
    query += "NOT EXISTS(SELECT 1 FROM file_publications p JOIN attempts a ON a.id=p.attempt WHERE a.job=? AND (NOT " + _covered('p.target', writes) + ' OR (p.temp IS NOT NULL AND NOT ' + _covered('p.temp', writes) + '))) AS publications'
    params = (identity['job'], *_parameters(writes), identity['job'], *_parameters(writes), *_parameters(writes))
    if not all(runtime.one(query, params).values()):
        raise Refusal('pending original history/publication writes exceed declared executor ceiling')
    if runtime.one('SELECT 1 AS present FROM attempts a WHERE a.job=? AND (EXISTS(SELECT 1 FROM ordinary_runs r WHERE r.attempt=a.id) OR EXISTS(SELECT 1 FROM routine_runs r WHERE r.attempt=a.id))', (identity['job'],)):
        raise Refusal('opaque original ordinary/routine dependency remains held')
    if runtime.one("SELECT 1 AS present FROM attempts WHERE job=? AND kind='task' AND id!=?", (identity['job'], identity['attempt'])):
        raise Refusal('additional original task attempt needs its own complete ceiling')


def project(runtime, boards, keys):
    historical._work_actor(runtime, boards)
    with historical._transaction(runtime):
        return _project(runtime, boards, keys)


def _project(runtime, boards, keys):
    work, source, bindings = _current(runtime, boards, keys)
    identity = work['identity']
    reads = list(dict.fromkeys(source['ceiling']['reads'] + work['ceiling']['reads']))
    writes = work['ceiling']['writes']
    scope = dict(identity=identity, bindings=bindings, public_roots=reads)
    facts = historical._project(runtime, boards, scope)
    _complete_policy(runtime, identity, source['ceiling']['reads'])
    _material_ceiling(runtime, identity, source['ceiling']['reads'])
    _executor_ceiling(runtime, identity, writes)
    return {'identity': identity, 'reads': reads, 'writes': writes, 'mode': MODE,
            'complete_declared_ceiling': True, 'facts': facts, 'physical': 'UNKNOWN',
            'physical_or_adversarial_guarantee': False, 'old_authority_revived': False}


def original_modes(runtime, boards, keys, job):
    # Revalidate current new authority separately; never compare its birth with
    # the old capability/epoch. The ordinary caller still owns new task gates.
    runtime.processing.current()
    value = _project(runtime, boards, keys)
    if value['identity']['job'] != job['id'] or value['identity']['task'] != job['task']:
        raise Refusal('selected historical dependency is a different original job')
    exclusions = runtime.config.get('artifact_exclusions', [])
    paths = value['reads'] + value['writes']
    for p in paths:
        resource_scopes.root(p, exclusions, metadata=False)
    reads = [resource_scopes.root(p, exclusions) for p in value['reads']]
    writes = [resource_scopes.root(p, exclusions) for p in value['writes']]
    # Only this authenticated original attempt's unique staging child has the
    # existing fresh-child exemption. Broader declared writes still conflict.
    staging = resource_scopes.root(str(runtime.artifact_root(value['identity']['attempt'])), exclusions)
    return reads, writes, [staging]


def revoke(runtime, boards, domain, key):
    principal = actor(runtime, boards, domain)
    with historical._transaction(runtime):
        return _revoke(runtime, domain, key, principal)


def _revoke(runtime, domain, key, principal):
    row = runtime.one('SELECT issuer,json_extract(scope,\'$.domain\') AS domain,json_extract(scope,\'$.preserved_bytes\') AS preserved FROM historical_metadata_access WHERE id=?', (canonical_uuid(key),))
    if not row or row['issuer'] != principal or row['domain'] != domain:
        raise Refusal('field scope belongs to another actual custodian')
    if runtime.one('SELECT id FROM historical_metadata_revocations WHERE id=?', (key,)):
        return {'revoked': key, 'original_duties': 'unchanged'}
    _budget(runtime, {'revocation': key}, row['preserved'], creating=False)
    runtime.db.execute('INSERT OR IGNORE INTO historical_metadata_revocations VALUES(?,?)', (key, runtime.clock()))
    return {'revoked': key, 'original_duties': 'unchanged'}
