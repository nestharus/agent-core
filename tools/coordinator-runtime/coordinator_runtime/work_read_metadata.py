"""Metadata-only nonwriting predecessor fences; no historical body authority.

The revision witnesses cooperative writes only through registration. Later
coexistence rechecks execution relationships, never interprets retained bodies
or grants their consumers access. Controller closure remains owner testimony.
"""
import math
from contextlib import nullcontext

from .contracts import Refusal, digest, encode, required_text

SCHEMA = 'work-read-fence-metadata-v1'


def predecessor(runtime, job, token=None):
    # Token/header before any related-record acquisition. No job(), attempt(),
    # source_roles(), full task/scope/member hashes or old result fields.
    sql = ('SELECT id,role,phase,task,state,active_attempt,controller,effects,'
           'recovery_owner,recovery_state,recovery_count FROM jobs WHERE id=?')
    row = runtime.one(sql + (' AND token=?' if token is not None else ''),
                      (job, token) if token is not None else (job,))
    if (not row or row['role'] != 'Work' or row['phase'] != 'proposer'
            or row['state'] != 'held' or row['effects'] != 'none'):
        raise Refusal('exact held nonwriting Work proposer and reservation token required')
    if runtime.one('SELECT job FROM local_jobs WHERE job=?', (job,)):
        raise Refusal('unknown original local scope required; no scoped predecessor conversion')
    if runtime.one('SELECT 1 AS present FROM file_publications p JOIN attempts a ON a.id=p.attempt '
                   'WHERE a.job=? LIMIT 1', (job,)):
        raise Refusal('publication duties cannot be treated as a nonwriting predecessor')
    # SQL alone interprets the immutable original policy. Only a boolean leaves
    # SQLite, never task bytes, scopes, opaque fields or a hash of those bytes.
    policy = runtime.one("SELECT 1 AS nonwriting FROM job_resource_policies WHERE job=? "
        "AND json_extract(task,'$.role')='Work' AND json_extract(task,'$.phase')='proposer' "
        "AND json_extract(task,'$.sandbox')='read-only' AND json_extract(task,'$.effects')='none' "
        "AND (json_type(task,'$.network') IS NULL OR (json_type(task,'$.network')='false' "
        "AND json_extract(task,'$.network')=0)) "
        "AND (json_type(task,'$.execution') IS NULL OR json_type(task,'$.execution')='null') "
        "AND (json_type(task,'$.routine_completion') IS NULL "
        "OR json_type(task,'$.routine_completion') IN ('null','false')) "
        "AND json_type(task,'$.effect_authority')='object' "
        "AND json_type(task,'$.effect_authority.write_roots')='array' "
        "AND json_extract(task,'$.effect_authority.write_roots')='[]'", (job,))
    if not policy:
        raise Refusal('original frozen read-only nonwriting Work proposer policy required')
    if (row['recovery_state'] not in {None, 'awaiting-disposition', 'owner-deferred', 'handed-off'}
            or (row['recovery_state'] is None) != (row['recovery_owner'] is None)
            or type(row['recovery_count']) is not int or row['recovery_count'] < 0
            or (row['recovery_owner'] is None) != (row['recovery_count'] == 0)
            or row['recovery_state'] == 'handed-off' and row['controller'] != row['recovery_owner']):
        raise Refusal('exact inactive recovery/controller relationship required')
    sources = runtime.integration_metadata_sources(job, phase='proposer')
    if any(s['role'] not in runtime.config['roles'] for s in sources):
        raise Refusal('exact related source identities and configured roles required')
    attempts = runtime.rows('SELECT id,kind,job,controller,begin,ended,collected,exit,state '
                            'FROM attempts WHERE job=? ORDER BY rowid', (job,))
    active = next((a for a in attempts if a['id'] == row['active_attempt']), None)
    if (not active or active['kind'] != 'task' or active['controller'] != row['controller']
            or any(a['kind'] not in {'task', 'diagnosis'} or a['job'] != job
                   or a['state'] != 'collected' or type(a['exit']) is not int
                   or any(type(a[k]) not in {int, float} or not math.isfinite(a[k]) or a[k] < 0
                          for k in ('begin', 'ended', 'collected'))
                   or not a['begin'] <= a['ended'] <= a['collected'] for a in attempts)):
        raise Refusal('all related originals need actual begun numeric END and collection; exact active task/controller required')
    if runtime.one("SELECT 1 AS pending FROM recovery_requests WHERE job=? AND state='pending' LIMIT 1", (job,)):
        raise Refusal('pending owner recovery must be disposed before a read fence')
    controllers = {row['controller'], *[a['controller'] for a in attempts]}
    if row['recovery_owner'] is not None:
        controllers.add(row['recovery_owner'])
    for controller in controllers:
        required_text(controller, 'actual launch-capable controller', 128)
    return {'job': row, 'sources': sources, 'attempts': attempts,
            'controllers': sorted(controllers), 'original_nonwriting': True, 'pending_recovery': False}


def basis(runtime, job, token, actor, *, operation='work-read-metadata-closure-basis'):
    from . import configuration, windows
    if runtime.processing is not None:
        raise Refusal('metadata fence requires genuine owner authority, not processing access')
    if actor != runtime.config['roles']['Work']['owner']:
        raise Refusal('actual current Work owner required')
    required_text(token, 'exact reservation token', 128)
    configuration.assert_current(runtime)
    configuration.assert_release(runtime)
    management = getattr(runtime, 'integration_management', None)
    if management and (management.actor != actor or management.selection['operation'] != operation
            or management.selection['target'] != {'job': job, 'token': token}):
        raise Refusal('metadata fence outside exact operation/job/token management authority')
    prior = predecessor(runtime, job, token)
    for table in ('integration_retirements', 'integration_prestart_dispositions', 'work_read_fences'):
        if runtime.one('SELECT job FROM '+table+' WHERE job=?', (job,)):
            raise Refusal('execution retired; original duties remain held, no callback/recovery/replay')
    task = runtime.config['tasks'].get(prior['job']['task'])
    if not task or task['role'] != 'Work' or task['phase'] != 'proposer':
        raise Refusal('selected current Work proposer task required')
    enrollments = []
    for role in sorted({'Work'} | {s['role'] for s in prior['sources']}):
        enrollment = (management.enrollment(role) if management else runtime.one(
            'SELECT role,owner,profile,grant_id,cutover,intake FROM enrollments WHERE role=? AND intake=1', (role,)))
        if (not enrollment or enrollment['owner'] != runtime.config['roles'][role]['owner']
                or enrollment['profile'] != runtime.config['roles'][role]['profile']):
            raise Refusal('actual current source role owner enrollment required')
        enrollments.append({k: enrollment[k] for k in ('role', 'owner', 'profile', 'grant_id', 'cutover', 'intake')})
    return runtime._integration_bounded({'schema': SCHEMA, 'configuration': digest(runtime.config),
        'predecessor': prior, 'controllers': prior['controllers'], 'enrollments': enrollments,
        'journal_revision': windows.revision(runtime)})


def closure_basis(runtime, job, token, actor):
    with (nullcontext() if runtime.db.in_transaction else runtime.tx()):
        return basis(runtime, job, token, actor)


def fence(runtime, job, token, actor, receipt):
    from .selected_source import custody_budget
    with (nullcontext() if runtime.db.in_transaction else runtime.tx()):
        selected = basis(runtime, job, token, actor, operation='fence-work-proposer-metadata')
        runtime._integration_controller_closures(selected, receipt)
        runtime._integration_bounded(receipt)
        custody_budget(runtime, len(encode(selected).encode()) + len(encode(receipt).encode()))
        if basis(runtime, job, token, actor, operation='fence-work-proposer-metadata') != selected:
            raise Refusal('metadata fence revision changed; fresh owner selection required')
        runtime.db.execute('INSERT INTO work_read_fences VALUES(?,?,?,?,?)',
            (job, actor, encode(selected), encode(receipt), runtime.clock()))
    return runtime.one('SELECT job,actor,basis,receipt,created FROM work_read_fences WHERE job=?', (job,))


def coexists(runtime, job, selected):
    # Registration's global revision is deliberately historical: unrelated later
    # allocations must be possible. This asserts only unchanged execution facts,
    # not currentness/acceptance/processing of any opaque retained body.
    return selected.get('predecessor') == predecessor(runtime, job)
