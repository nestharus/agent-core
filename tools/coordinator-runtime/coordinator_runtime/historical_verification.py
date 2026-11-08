"""Current, owner-scoped access to preexisting cooperative journal facts.

No historical witness is created. No execution capability is selected. Opaque
native identities and whole original bodies are never acquired, even for equality.
"""
import json
import math
import re
from contextlib import nullcontext

from . import configuration, processing, resource_scopes
from .contracts import Refusal, canonical_uuid, digest, encode, ident, required_text

SCHEMA = """
CREATE TABLE IF NOT EXISTS historical_metadata_access(
 id TEXT PRIMARY KEY,scope TEXT NOT NULL,issuer TEXT NOT NULL,created REAL NOT NULL);
CREATE TABLE IF NOT EXISTS historical_metadata_revocations(
 id TEXT PRIMARY KEY REFERENCES historical_metadata_access(id),created REAL NOT NULL);
CREATE TRIGGER IF NOT EXISTS historical_metadata_no_update BEFORE UPDATE ON historical_metadata_access
 BEGIN SELECT RAISE(ABORT,'immutable current metadata scope'); END;
CREATE TRIGGER IF NOT EXISTS historical_metadata_no_delete BEFORE DELETE ON historical_metadata_access
 BEGIN SELECT RAISE(ABORT,'immutable current metadata scope'); END;
CREATE TRIGGER IF NOT EXISTS historical_revocations_no_update BEFORE UPDATE ON historical_metadata_revocations
 BEGIN SELECT RAISE(ABORT,'immutable metadata revocation'); END;
CREATE TRIGGER IF NOT EXISTS historical_revocations_no_delete BEFORE DELETE ON historical_metadata_revocations
 BEGIN SELECT RAISE(ABORT,'immutable metadata revocation'); END;
"""

# Exact acquisition contract, not arbitrary caller-supplied SQL/JSON paths.
FIELDS = ('job-lineage', 'source-header', 'launch-proof', 'original-epoch-birth',
          'frozen-standalone-policy', 'context-collector-links', 'public-read-membership')
IDENTITY = {'job','attempt','event','source_hash','task','capability','epoch','component','collector','post'}
PROOF = ('grant_id','issued_by','authority','role_owner','task_hash','admission_hash',
         'prospective_epoch','delegated_by','delegation_authority','processing_capability')
UNKNOWN = ['native-identity-and-material', 'native-physical-state-and-owner',
           'opaque-executor-writes', 'unbounded-retained-resources', 'source-body-integrity']


def _transaction(runtime):
    return nullcontext() if runtime.db.in_transaction else runtime.tx()


def _path(task):
    return '$.' + json.dumps(task)


def _identity(value):
    if not isinstance(value, dict) or set(value) != IDENTITY:
        raise Refusal('exact original public journal identities required; no discovery')
    for name in ('job','attempt','capability','epoch','collector'):
        canonical_uuid(value[name])
    for name in ('event','source_hash'):
        if not isinstance(value[name], str) or not re.fullmatch('[a-f0-9]{64}', value[name]):
            raise Refusal('exact original source identifier/hash required')
    required_text(value['task'], 'original task name', 128)
    required_text(value['component'], 'public original component name', 256)
    if type(value['post']) is not int or value['post'] <= 0:
        raise Refusal('exact original public post identity required')
    return value


def _roots(runtime, values):
    if (not isinstance(values, list) or not values or len(values) > 32
            or any(not isinstance(v,str) for v in values) or len(set(values)) != len(values)):
        raise Refusal('bounded exact public roots required')
    exclusions = runtime.config.get('artifact_exclusions', [])
    # Whole selection is checked before any filesystem metadata. This API never
    # stats original resources; actual comparison repeats the whole-map check.
    return [str(resource_scopes.root(p, exclusions, metadata=False)) for p in values]


def _scope(runtime, selection):
    keys = {'identity','purpose','authority','expires','public_roots','fields','principal','configuration','implementation'}
    if not isinstance(selection, dict) or set(selection) != keys or selection['fields'] != list(FIELDS):
        raise Refusal('exact current metadata purpose/principal/data scope required')
    _identity(selection['identity'])
    _roots(runtime, selection['public_roots'])
    required_text(selection['purpose'], 'current metadata purpose', 2000)
    required_text(selection['authority'], 'current owner metadata delegation', 2000)
    expiry = selection['expires']
    if type(expiry) not in (int,float) or not math.isfinite(expiry) or not runtime.clock() < expiry <= runtime.clock()+3600:
        raise Refusal('current metadata scope must expire within one hour')
    if selection['principal'] != runtime.config['roles']['Work']['owner']:
        raise Refusal('metadata consumer must be the actual configured Work')
    if selection['configuration'] != digest(runtime.config) or selection['implementation'] != processing.implementation():
        raise Refusal('explicit current metadata source/configuration pins differ')
    if len(encode(selection).encode()) > runtime.config['limits']['max_result_bytes']:
        raise Refusal('metadata selection exceeds original custody limit')
    return selection


def _bindings(runtime, boards, task):
    configuration.assert_current(runtime)
    work = boards['Work'].historical_authority(runtime)
    source = boards['Reviews'].historical_authority(runtime, task)
    if work['issuer'] != source['issuer'] or work['issuer'] != runtime.config['roles']['Work']['owner']:
        raise Refusal('original Work issuer/journal relationship differs')
    return {'work':work, 'source':source}


def authorize(runtime, boards, selection):
    """Original Reviews data owner delegates only these software journal facts.

    Current read visibility is independently required for both owner and Work.
    This grants no authority over native stores or original source bodies.
    """
    _scope(runtime, selection)
    owner = runtime.config['roles']['Reviews']['owner']
    actor = boards['Reviews'].store.acting_session(owner)
    if actor != owner:
        raise Refusal('actual original Reviews data owner required')
    with _transaction(runtime):
        bindings = _bindings(runtime, boards, selection['identity']['task'])
        _source_access(runtime, boards, selection['identity'], bindings)
        key = ident()
        scope = {**selection, 'bindings':bindings, 'version':configuration.version_metadata(runtime)}
        _metadata_budget(runtime,scope)
        runtime.db.execute('INSERT INTO historical_metadata_access VALUES(?,?,?,?)',
                           (key, encode(scope), actor, runtime.clock()))
    return {'metadata_access':key, 'fields':list(FIELDS), 'execution':False}


def _metadata_budget(runtime, scope):
    from .selected_source import custody_budget
    size = len(encode(scope).encode())
    if size > runtime.config['limits']['max_result_bytes']:
        raise Refusal('complete current metadata scope exceeds original custody ceiling')
    if runtime.one('SELECT COUNT(*) AS n FROM historical_metadata_access')['n'] >= runtime.config['limits']['max_jobs']:
        raise Refusal('current metadata scope residency ceiling reached; no retirement implied')
    custody_budget(runtime,size+2048)


def _work_actor(runtime, boards):
    actor = boards['Work'].store.acting_session(runtime.config['roles']['Work']['owner'])
    if actor != runtime.config['roles']['Work']['owner']:
        raise Refusal('actual current Work principal required')
    return actor


def _current(runtime, boards, key):
    # Authenticate the current session before reading even a selected scope.
    actor = _work_actor(runtime, boards)
    configuration.assert_current(runtime)
    row = runtime.one('SELECT scope,issuer,created FROM historical_metadata_access WHERE id=?', (canonical_uuid(key),))
    if not row or runtime.one('SELECT id FROM historical_metadata_revocations WHERE id=?', (key,)):
        raise Refusal('current metadata scope absent/revoked')
    scope = json.loads(row['scope'])
    _scope(runtime, {k:scope[k] for k in ('identity','purpose','authority','expires','public_roots','fields','principal','configuration','implementation')})
    if (row['issuer'] != runtime.config['roles']['Reviews']['owner'] or scope['principal'] != actor
            or scope['configuration'] != digest(runtime.config)
            or scope['version'] != configuration.version_metadata(runtime)
            or scope['implementation'] != processing.implementation()
            or scope['bindings'] != _bindings(runtime, boards, scope['identity']['task'])):
        raise Refusal('metadata issuer/principal/source/configuration binding changed')
    _source_access(runtime, boards, scope['identity'], scope['bindings'])
    return scope


def _source_access(runtime, boards, identity, bindings):
    # No packet/body, and no attempt/job token. Header hold admission precedes
    # all protected original proof/policy/context projections.
    boards['Reviews'].historical_source_access(runtime, identity['post'], bindings['work']['owner'])
    state = runtime.one('SELECT role,hash,hold FROM events WHERE id=?', (identity['event'],))
    if not state or state['hold'] is not None or state['role'] != 'Reviews' or state['hash'] != identity['source_hash']:
        raise Refusal('original source held or changed before protected metadata')
    source = runtime.one("SELECT role,hash,hold,json_extract(payload,'$.kind') AS kind,"
        "json_extract(payload,'$.post') AS post,json_extract(payload,'$.board_id') AS board,"
        "json_extract(payload,'$.grant') AS grant_id,json_extract(payload,'$.recipient') AS recipient,"
        "json_type(payload,'$.branch_binding') AS branch FROM events WHERE id=?", (identity['event'],))
    grant = bindings['source']
    if (not source or source['hold'] is not None or source['hash'] != identity['source_hash']
            or source['role'] != 'Reviews' or source['kind'] != 'board'
            or source['post'] != identity['post'] or source['branch'] not in (None,'null')
            or source['board'] != grant['board'] or source['grant_id'] != grant['grant']
            or source['recipient'] != grant['owner']):
        raise Refusal('original source held, foreign, changed or outside standalone metadata scope')
    boards['Reviews'].historical_source_access(runtime, source['post'], bindings['work']['owner'])
    return source


def _job(runtime, identity):
    row = runtime.one('SELECT role,phase,task,package,active_attempt,state,effects,'
        'json_array_length(members) AS members,json_extract(members,\'$[0].event\') AS event,'
        'json_extract(members,\'$[0].hash\') AS hash,json_extract(members,\'$[0].package\') AS member_package,'
        'CASE WHEN hold_reason=? THEN \'conserved-incomplete\' WHEN hold_reason=? THEN \'deferred-incomplete\' '
        'WHEN hold_reason IS NULL THEN \'none\' ELSE \'opaque\' END AS hold FROM jobs WHERE id=?',
        ('original Source incomplete; whole return conserved through sole report integration',
         'original Source incomplete; whole return retained in original attempt '+identity['attempt']+
         ' and review call; sole report integration deferred', identity['job']))
    if (not row or row['role'] != 'Reviews' or row['phase'] != 'proposer' or row['task'] != identity['task']
            or row['package'] is not None or row['active_attempt'] != identity['attempt']
            or row['members'] != 1 or row['event'] != identity['event'] or row['hash'] != identity['source_hash']
            or row['member_package'] is not None or row['hold'] == 'opaque'):
        raise Refusal('original standalone job/member/attempt relationship unavailable')
    if row['state'] not in {'reserved','running','held','awaiting-delivery','closed'} or row['effects'] not in {'none','unknown','reconciled'}:
        raise Refusal('original outcome vocabulary is opaque')
    return row


def _attempt(runtime, identity, grant):
    columns = ','.join("json_extract(detail,'$.software_authority."+p+"') AS "+p for p in PROOF)
    row = runtime.one('SELECT job,kind,controller,state,exit,capture,begin IS NOT NULL AS begun,'
        'ended IS NOT NULL AS ended,collected IS NOT NULL AS collected,'
        "json_type(detail,'$.software_authority.admission_hash') AS admission_type,"
        "json_extract(detail,'$.processing_capability') AS capability,"+
        "json_extract(detail,'$.configuration_sha256') AS configuration,"+columns+' FROM attempts WHERE id=?',
        (identity['attempt'],))
    if (not row or row['job'] != identity['job'] or row['kind'] != 'task'
            or row['controller'] != identity['collector'] or row['capability'] != identity['capability']
            or row['processing_capability'] != identity['capability'] or row['prospective_epoch'] != identity['epoch']
            or row['grant_id'] != grant['grant'] or row['issued_by'] != grant['issuer']
            or row['authority'] != grant['authority'] or row['role_owner'] != grant['owner']
            or row['admission_hash'] is not None or row['admission_type'] != 'null'):
        raise Refusal('original frozen launch/grant/configuration relationship differs')
    if (row['capture'] not in {'unknown','complete','incomplete'} or row['state'] not in {'reserved','running','collected'}
            or row['exit'] is not None and (type(row['exit']) is not int or not -255 <= row['exit'] <= 255)):
        raise Refusal('original collection outcome is opaque')
    return row


def _launch_configuration(runtime, identity, launch, grant):
    """Authenticate a preexisting transition, never substitute today's task.

    ProcessingBoard legitimately bridges still-revoked original grants through
    Work's frozen configuration transitions. A new task need not have existed
    in the initial software-grant task catalog. The original epoch/proof retain
    its exact hash; the original frozen job row retains its access projection.
    """
    if (not isinstance(launch['task_hash'],str) or not re.fullmatch('[a-f0-9]{64}',launch['task_hash'])
            or not isinstance(launch['configuration'],str) or not re.fullmatch('[a-f0-9]{64}',launch['configuration'])):
        raise Refusal('original task/configuration hash witness unavailable')
    if launch['configuration'] == grant['configuration']:
        return _initial_task(launch,grant)
    transition = runtime.one('SELECT issuer,original,EXISTS(SELECT 1 FROM json_each(selection,\'$.basis.tasks\') '
        'WHERE value=?) AS task FROM configuration_transitions WHERE current=?', (identity['task'],launch['configuration']))
    if (not transition or transition['issuer'] != grant['issuer'] or transition['original'] != grant['configuration']
            or not transition['task']):
        raise Refusal('original Work configuration/task transition witness unavailable')


def _initial_task(launch, grant):
    if launch['task_hash'] != grant['task_hash']:
        raise Refusal('original initial software task witness differs')


def _epoch(runtime, identity, launch, grant):
    task = _path(identity['task'])
    row = runtime.one("SELECT event_boundary,job_boundary,revoked IS NOT NULL AS revoked,"
        "json_extract(selection,'$.configuration') AS configuration,json_extract(selection,'$.grantor') AS issuer,"
        "json_extract(selection,'$.authority') AS authority,json_extract(selection,'$.expires') AS expires,"
        "json_extract(selection,'$.processing_capability') AS capability,"
        "json_extract(selection,?) AS grant_id,json_extract(selection,?) AS task_hash,"
        "json_extract(selection,?) AS ordinary FROM prospective_authorities WHERE id=?",
        ('$.grants.Reviews','$.tasks'+task[1:]+'.task_hash','$.tasks'+task[1:]+'.ordinary_effects',identity['epoch']))
    if (not row or row['configuration'] != launch['configuration'] or row['issuer'] != grant['issuer']
            or launch['delegated_by'] != row['issuer'] or launch['delegation_authority'] != row['authority']
            or row['capability'] != identity['capability'] or row['grant_id'] != grant['grant']
            or row['task_hash'] != launch['task_hash'] or row['ordinary'] != 0):
        raise Refusal('original epoch/task/grant relationship differs')
    if type(row['expires']) not in (int,float) or not math.isfinite(row['expires']):
        raise Refusal('original epoch expiry is opaque')
    return row


def _capability(runtime, identity, launch, grant):
    row = runtime.one("SELECT issuer,revoked IS NOT NULL AS revoked,"
        "json_extract(selection,'$.basis.configuration') AS configuration,"
        "json_extract(selection,'$.basis.roles.Reviews.future_after') AS frontier,"
        "json_extract(selection,'$.basis.event_boundary') AS boundary,"
        "EXISTS(SELECT 1 FROM json_each(selection,'$.tasks') WHERE value=?) AS task,"
        "json_extract(selection,'$.basis.roles.Reviews.original.binding.id') AS grant_id,"
        "json_extract(selection,'$.basis.roles.Reviews.original.binding.issued_by') AS grantor "
        'FROM processing_capabilities WHERE id=?', (identity['task'],identity['capability']))
    if (not row or row['issuer'] != grant['issuer'] or row['grantor'] != grant['issuer']
            or row['configuration'] != launch['configuration'] or not row['task'] or row['grant_id'] != grant['grant']
            or type(row['frontier']) is not int or type(row['boundary']) is not int):
        raise Refusal('original processing issuer/source/configuration relationship differs')
    return row


def _birth(runtime, identity, epoch, cap, source):
    job = runtime.one('SELECT position FROM prospective_job_positions WHERE job=?', (identity['job'],))
    event = runtime.one('SELECT position FROM processing_source_positions WHERE event=?', (identity['event'],))
    if (not job or not event or job['position'] <= epoch['job_boundary']
            or event['position'] <= max(epoch['event_boundary'],cap['boundary']) or source['post'] <= cap['frontier']):
        raise Refusal('original observed job/source birth relationship missing or changed')


def _policy(runtime, identity, grant):
    row = runtime.one("SELECT admission IS NULL AS standalone,json_extract(task,'$.role') AS role,"
        "json_extract(task,'$.phase') AS phase,json_extract(task,'$.execution') AS execution,"
        "json_extract(task,'$.effect_authority.owner') AS owner,json_extract(task,'$.effects') AS effects,"
        "json_extract(task,'$.sandbox') AS sandbox,json_extract(task,'$.network') AS network,"
        "json_type(task,'$.effect_authority.write_roots') AS writes_type,"
        "json_array_length(task,'$.effect_authority.write_roots') AS writes FROM job_resource_policies WHERE job=?",
        (identity['job'],))
    if (not row or not row['standalone'] or row['role'] != 'Reviews' or row['phase'] != 'proposer'
            or row['execution'] != 'owner' or row['owner'] != grant['owner']
            or row['effects'] != 'none' or row['sandbox'] != 'read-only' or row['network'] != 0
            or row['writes_type'] != 'array' or row['writes'] != 0):
        raise Refusal('original frozen standalone read policy unavailable or opaque')


def _context(runtime, identity):
    # No profile/route/handle/run/session, receipt, answer, whole packet/history.
    row = runtime.one("SELECT c.collector,c.component,c.state,x.capability,x.collector AS context_collector,"
        "x.state AS context_state,json_extract(b.context,'$.component') AS bound_component,"
        "json_extract(b.context,'$.capability') AS bound_capability,"
        "json_extract(b.context,'$.collector') AS bound_collector,"
        "json_extract(c.packet,'$.selected_task') AS task FROM review_calls c "
        'JOIN review_call_contexts b ON b.attempt=c.attempt JOIN review_contexts x ON x.component=c.component '
        'WHERE c.attempt=?', (identity['attempt'],))
    if (not row or row['component'] != identity['component'] or row['bound_component'] != identity['component']
            or row['capability'] != identity['capability'] or row['bound_capability'] != identity['capability']
            or row['collector'] != identity['collector'] or row['context_collector'] != identity['collector']
            or row['bound_collector'] != identity['collector'] or row['task'] != identity['task']
            or row['context_state'] not in {'opening','live','interrupted','closed'}):
        raise Refusal('original call/context/collector journal relationship missing or changed')
    return row


def _public_reads(runtime, identity, values):
    # Positive membership in explicitly authorized PUBLIC operands only. Never
    # export/iterate the original read-root array or an unmatched cwd/path.
    return [p for p in values if runtime.one("SELECT 1 AS present FROM job_resource_policies WHERE job=? AND "
        "(json_extract(task,'$.cwd')=? OR EXISTS(SELECT 1 FROM json_each(task,'$.effect_authority.read_roots') WHERE value=?))",
        (identity['job'],p,p))]


def project(runtime, boards, key):
    _work_actor(runtime, boards)
    with _transaction(runtime):
        return _project(runtime, boards, _current(runtime, boards, key))


def _project(runtime, boards, scope):
    identity, grant = scope['identity'], scope['bindings']['source']
    source = _source_access(runtime, boards, identity, scope['bindings'])
    job = _job(runtime, identity)
    launch = _attempt(runtime, identity, grant)
    _launch_configuration(runtime,identity,launch,grant)
    epoch = _epoch(runtime, identity, launch, grant)
    cap = _capability(runtime, identity, launch, grant)
    _birth(runtime, identity, epoch, cap, source)
    _policy(runtime, identity, grant)
    context = _context(runtime, identity)
    _held_outcome(job,launch,context)
    reads = _public_reads(runtime, identity, scope['public_roots'])
    return _facts(runtime,identity,job,launch,epoch,cap,context,reads)


def _held_outcome(job, launch, context):
    if job['hold'] != 'none' and (job['state'] != 'held' or launch['state'] != 'collected'
            or not launch['ended'] or not launch['collected'] or launch['capture'] != 'incomplete'
            or context['context_state'] not in {'interrupted','closed'}):
        raise Refusal('incomplete Source outcome lacks original collection/custody relationships')


def _facts(runtime, identity, job, launch, epoch, cap, context, reads):
    return {'verification':'verified-scoped-journal-relationships', 'identity':identity,
            'outcome':{'END':launch['exit'], 'capture':launch['capture'], 'effects':job['effects'],
                       'hold':job['hold'], 'context':context['context_state']},
            'original_authority':{'processing_revoked':bool(cap['revoked']), 'epoch_revoked':bool(epoch['revoked']),
                                  'epoch_expired':epoch['expires'] <= runtime.clock()},
            'public_reads':reads, 'public_projection_complete':False, 'unknown_constraints':list(UNKNOWN), 'physical':'UNKNOWN',
            'native_identity_verified':False, 'source_body_verified':False,
            'execution':False, 'closure':False, 'input':False, 'eligible':False}


def compare(runtime, boards, key, candidate):
    _work_actor(runtime, boards)
    with _transaction(runtime):
        return _compare(runtime,boards,_current(runtime,boards,key),candidate)


def _candidate(candidate):
    if not isinstance(candidate, dict) or set(candidate) != {'reads','writes'}:
        raise Refusal('explicit public comparison reads/writes required; no operation authority')
    if any(not isinstance(candidate[k],list) or len(candidate[k])>32
           or any(not isinstance(p,str) for p in candidate[k]) for k in ('reads','writes')):
        raise Refusal('bounded public comparison path lists required')
    return candidate


def _compare(runtime, boards, scope, candidate):
    _candidate(candidate)
    exclusions = runtime.config.get('artifact_exclusions', [])
    all_paths = [*scope['public_roots'], *candidate['reads'], *candidate['writes']]
    for p in all_paths:
        resource_scopes.root(p, exclusions, metadata=False)
    facts = _project(runtime, boards, scope)
    for p in all_paths:
        resource_scopes.root(p, exclusions)
    conflict = any(resource_scopes.overlaps(left,right) for left in candidate['writes'] for right in facts['public_reads'])
    return {'comparison':'CONFLICT' if conflict else 'UNKNOWN',
            'public_subset':'overlap' if conflict else 'disjoint', 'facts':facts,
            'eligible':False, 'meaning':'diagnostic only; every retained constraint and current-operation admission remains'}


def revoke(runtime, boards, key):
    owner = runtime.config['roles']['Reviews']['owner']
    if boards['Reviews'].store.acting_session(owner) != owner:
        raise Refusal('actual metadata data-owner issuer required')
    with _transaction(runtime):
        row = runtime.one('SELECT issuer FROM historical_metadata_access WHERE id=?', (canonical_uuid(key),))
        if not row or row['issuer'] != owner:
            raise Refusal('metadata scope belongs to another issuer')
        runtime.db.execute('INSERT OR IGNORE INTO historical_metadata_revocations VALUES(?,?)',(key,runtime.clock()))
    return {'revoked':key, 'original_duties':'unchanged'}
