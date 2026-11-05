"""Explicit future authority in the original responsibility/accounting domain.

No config, enrollment, cursor, source or collector is rewritten. Old members
cannot inherit a later authority, including when batched with new members.
Roles: validator, orchestration.
"""
import json
import math

from .contracts import Refusal, canonical_uuid, digest, encode, ident, required_text

SCHEMA = """
CREATE TABLE IF NOT EXISTS prospective_authorities(
 id TEXT PRIMARY KEY,selection TEXT NOT NULL,event_boundary INTEGER NOT NULL,
 job_boundary INTEGER NOT NULL,created REAL NOT NULL,revoked REAL);
"""


def select(store, actor, selection):
    if actor != store.config['roles'].get('Work', {}).get('owner'):
        raise Refusal('actual Work alone selects prospective authority')
    if set(selection) - {'processing_capability'} != {'configuration', 'authority', 'expires', 'grants', 'tasks'}:
        raise Refusal('exact configuration/authority/expiry/grants/tasks selection required')
    bridge = selection.get('processing_capability')
    required_text(selection['authority'], 'actual prospective authority', 4000)
    if selection['configuration'] != digest(store.config) or type(selection['expires']) not in {int, float} or not math.isfinite(selection['expires']) or selection['expires'] <= store.clock():
        raise Refusal('prospective authority must be current and bind unchanged configuration')
    if not isinstance(selection['tasks'], dict) or not selection['tasks'] or set(selection['tasks']) - set(store.config['tasks']):
        raise Refusal('explicit known task policies required')
    if not isinstance(selection['grants'], dict) or set(selection['grants']) != {store.config['tasks'][t]['role'] for t in selection['tasks']}:
        raise Refusal('exact task role/grant population required')
    if bridge is not None:
        bridge_authority(store, bridge, selection['tasks'])
    elif store.processing:
        raise Refusal('processing ordinary authority needs its explicitly selected capability')
    for name, policy in selection['tasks'].items():
        validate_policy(store, name, policy, selection)
    with store.tx():
        if store.one('SELECT id FROM prospective_authorities WHERE revoked IS NULL'):
            raise Refusal('explicitly revoke previous boundary before selecting another; no implicit supersession')
        boundary = {t: store.one(f'SELECT COALESCE(MAX(rowid),0) AS n FROM {t}')['n'] for t in ('events', 'jobs')}
        if bridge is not None:
            from .processing import source_boundary
            boundary['events'] = source_boundary(store)
        key = ident()
        store.db.execute('INSERT INTO prospective_authorities VALUES(?,?,?,?,?,NULL)',
                         (key, encode({**selection, 'grantor': actor}), boundary['events'], boundary['jobs'], store.clock()))
    return {'id': key, 'event_boundary': boundary['events'], 'job_boundary': boundary['jobs'],
            'meaning': 'future work only; all original responsibilities stay in this journal'}


def validate_policy(store, name, policy, selection):
    task = store.config['tasks'][name]
    if set(policy) != {'task_hash', 'software_handoffs', 'ordinary_effects'} or policy['task_hash'] != digest(task):
        raise Refusal('exact unchanged task policy required')
    enrollment = store.enrollment(task['role'])
    if selection['grants'].get(task['role']) != enrollment['grant_id']:
        raise Refusal('retain actual current enrollment and grant identity')
    if type(policy['ordinary_effects']) is not bool:
        raise Refusal('explicit ordinary effects boolean required')
    if not isinstance(policy['software_handoffs'], dict):
        raise Refusal('explicit recipient task map required')
    if policy['ordinary_effects'] and (name not in {'branch-integrator', 'qa-execution'} or not task.get('require_package_scope') or task['effects'] != 'owner-reconcile'):
        raise Refusal('ordinary effects require scoped Branch integrator or QA execution')
    for role, routes in policy['software_handoffs'].items():
        if role not in task.get('allowed_handoffs', []) or not routes or not isinstance(routes, list):
            raise Refusal('handoffs cannot expand admitted recipients')
        if any(route not in selection['tasks'] or store.config['tasks'][route]['role'] != role for route in routes):
            raise Refusal('each receiver needs exact prospective task authority')


def current(store, task, epoch=None):
    row = store.one('SELECT * FROM prospective_authorities WHERE id=?', (epoch,)) if epoch else store.one(
        'SELECT * FROM prospective_authorities WHERE revoked IS NULL')
    if not row:
        return None
    selection = json.loads(row['selection'])
    if task not in selection['tasks']:
        return None
    policy = selection['tasks'][task]
    if selection.get('processing_capability') is not None:
        bridge_authority(store, selection['processing_capability'], selection['tasks'])
    elif store.processing:
        raise Refusal('ordinary authority belongs to another service mode')
    role = store.config['tasks'][task]['role']
    if (row['revoked'] is not None or selection['expires'] <= store.clock()
            or selection['configuration'] != digest(store.config)
            or policy['task_hash'] != digest(store.config['tasks'][task])
            or selection['grants'][role] != store.enrollment(role)['grant_id']):
        raise Refusal('prospective authority expired/revoked/changed; retain original effects and collectors')
    return {**row, 'selection': selection, 'policy': policy}


def requires_authority(store, job):
    """Retained prospective duties still need proof after revocation.

    Determine applicability from original journal boundaries, independently of
    the active attempt's possibly absent proof and the current config flag.
    Older jobs/members and unrelated task policies retain their native path.
    """
    position = store.one('SELECT rowid AS n FROM jobs WHERE id=?', (job['id'],))['n']
    members = json.loads(job['members'])
    for row in store.rows('SELECT * FROM prospective_authorities WHERE job_boundary<?', (position,)):
        authority = {**row, 'selection': json.loads(row['selection'])}
        if (job['task'] in authority['selection']['tasks'] and members
                and all(event_position(store, m['event'], authority) > row['event_boundary'] for m in members)):
            return True
    return False


def for_job(store, job):
    attempt = store.attempt(job['active_attempt']) if job['active_attempt'] else None
    proof = json.loads(attempt['detail']).get('software_authority', {}) if attempt else {}
    epoch = proof.get('prospective_epoch')
    row = current(store, job['task'], epoch)
    if not row:
        return None
    if store.one('SELECT rowid AS n FROM jobs WHERE id=?', (job['id'],))['n'] <= row['job_boundary']:
        return None
    members = json.loads(job['members'])
    if not members or any(event_position(store, m['event'], row) <= row['event_boundary'] for m in members):
        return None
    bridge = row['selection'].get('processing_capability')
    if bridge:
        detail = json.loads(attempt['detail']) if attempt else {}
        if (not attempt or detail.get('processing_capability') != bridge
                or proof and proof.get('processing_capability') != bridge):
            raise Refusal('ordinary job/attempt belongs to another original service authority')
        if any(not store.processing.event(store.event(m['event'])) for m in members):
            raise Refusal('ordinary members outside selected service')
    return row


def bridge_authority(store, key, tasks):
    if not store.processing or store.processing.key != key:
        raise Refusal('explicit current processing capability required for ordinary service operations')
    cap, selected = store.processing.current()
    if ('service' not in selected or set(tasks) - set(selected['tasks'])
            or cap['issuer'] != store.config['roles']['Work']['owner']):
        raise Refusal('ordinary bridge cannot expand genuine Work continuing task authority')
    if store.processing.boards is None:
        raise Refusal('actual original grant checkers required for service ordinary authority')
    for role in {store.config['tasks'][t]['role'] for t in tasks}:
        store.processing.boards[role].verify_authority(store)


def event_position(store, event, authority):
    if authority['selection'].get('processing_capability'):
        row = store.one('SELECT COALESCE(p.position,e.rowid) AS n FROM events e LEFT JOIN processing_source_positions p ON p.event=e.id WHERE e.id=?', (event,))
        return row['n']
    return store.one('SELECT rowid AS n FROM events WHERE id=?', (event,))['n']


def board(store, role):
    if store.processing:
        store.processing.current()
        if not store.processing.boards or role not in store.processing.boards:
            raise Refusal('actual service role grant checker required')
        return store.processing.boards[role]
    from .board import Board
    return Board(store.config, role)


def revoke(store, actor, epoch):
    row = store.one('SELECT * FROM prospective_authorities WHERE id=?', (epoch,))
    if not row or json.loads(row['selection'])['grantor'] != actor:
        raise Refusal('only actual original Work grantor may revoke this boundary')
    with store.tx():
        store.db.execute('UPDATE prospective_authorities SET revoked=COALESCE(revoked,?) WHERE id=?', (store.clock(), epoch))
    return {'revoked': epoch, 'old_and_new_responsibilities': 'retained; no retry/release/rebinding'}
