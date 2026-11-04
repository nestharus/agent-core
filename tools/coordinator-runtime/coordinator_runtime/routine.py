"""Role-delegated file completion; external/ref/CI effects retain their owners."""

import json
from pathlib import Path

from .contracts import Refusal, encode, collected_task_result, digest
from .custody import safe_path, read_file
from . import publication, readiness

SCHEMA = """
CREATE TABLE IF NOT EXISTS routine_runs(
 attempt TEXT PRIMARY KEY,task TEXT NOT NULL,grant_id TEXT NOT NULL,policy TEXT NOT NULL,
 before_files TEXT NOT NULL,after_files TEXT,state TEXT NOT NULL,receipt TEXT);
"""
BOARD_SCHEMA = """
CREATE TABLE IF NOT EXISTS coordinator_completion_grants_v1(
 grant_id TEXT PRIMARY KEY,policies TEXT NOT NULL,authority TEXT NOT NULL);
"""


def policy_for(task):
    policy = task.get('routine_completion')
    if not policy:
        return None
    if (set(policy) != {'kind','targets'} or not isinstance(policy.get('targets'),list)
            or not 1 <= len(policy['targets']) <= 64 or not all(isinstance(p,str) for p in policy['targets'])):
        raise Refusal('routine completion needs a bounded explicit file policy')
    if (policy.get('kind') != 'file-witness' or not policy.get('targets') or task.get('network', False)
            or task['effects'] != 'owner-reconcile'):
        raise Refusal('routine file completion requires exact targets and no network/external effects')
    if set(task['effect_authority']['operations']) - {'read-source','read-reports','prepare-intents','write-role-records','write-owned-artifacts','consolidate-reports'}:
        raise Refusal('ref/CI/resource effects need their actual supported owner callback')
    for p in policy['targets']:
        safe_path(p, task['effect_authority']['write_roots'])
    return policy


def snapshot(store, targets):
    records = {}
    for name in targets:
        path = safe_path(name, targets)
        try:
            body, witness = read_file(path, store.config['limits'].get('max_artifact_bytes', 33554432))
        except FileNotFoundError:
            records[name] = {'exists': False}
            continue
        with store.tx():
            present=store.one('SELECT sha256 FROM artifact_blobs WHERE sha256=?',(witness['sha256'],))
            store.budget(None,(0 if present else len(body))+1024)
            store.db.execute('INSERT OR IGNORE INTO artifact_blobs VALUES(?,?)', (witness['sha256'], body))
        records[name] = {'exists': True, **witness}
    return records


def prepare(store, board, job, attempt, task):
    policy = policy_for(task)
    if not policy:
        return
    grant = board.completion_authority(store, job['task'])
    with publication.snapshot_lock(store):
        before = snapshot(store, policy['targets'])
        remainder=json.loads(store.attempt(attempt)['detail']).get('publication_remainder')
        if remainder and (before!=remainder['peers'] or digest(grant)!=remainder['grant']):
            raise Refusal('publication remainder peer preimages/grant changed before fresh staging; no replay')
    if not all(v['exists'] for v in before.values()):raise Refusal('same-inode method requires existing regular canonical files')
    with store.tx():
        store.db.execute('INSERT INTO routine_runs VALUES(?,?,?,?,?,NULL,?,NULL)',
                         (attempt, job['task'], grant['id'], encode(policy), encode(before), 'prepared'))
    publication.prepare(store,attempt,before)


def reconcile(store, board, job):
    task = store.config['tasks'][job['task']]
    if not policy_for(task) or job['effects'] == 'reconciled':
        return False
    attempt = store.attempt(job['active_attempt'])
    run = store.one('SELECT * FROM routine_runs WHERE attempt=?', (attempt['id'],))
    if not run:
        return False  # No retrospective invention of a before-state or delegation.
    grant = board.completion_authority(store, job['task'])
    if grant['id'] != run['grant_id'] or store.enrollment(job['role'])['legacy_hold'] or job['hold_reason']:
        return False
    answer = collected_task_result(attempt)
    if (attempt['ended'] is None or attempt['collected'] is None or attempt['exit'] != 0 or attempt['capture'] != 'complete'
            or attempt['error'] or answer.get('semantic') != 'DONE'):
        return False
    tools = json.loads(attempt['detail']).get('tool_completion')
    if not tools or not tools['complete']:
        return False
    local=readiness.assess(store,attempt)
    with store.tx():
        detail={**json.loads(attempt['detail']),'local_readiness':local}
        store.db.execute('UPDATE attempts SET detail=? WHERE id=?',(encode(detail),attempt['id']))
    if not tools['items']:
        before=json.loads(run['before_files'])
        for target,path in publication.stages(store,attempt['id']).items():
            proposed=store.one('SELECT sha256 FROM artifact_custody WHERE attempt=? AND path=?',(attempt['id'],path))
            if not proposed or proposed['sha256']!=before[target].get('sha256'):return False
    published=publication.publish(store,board,job,attempt,run,task)
    after = {r['target']:json.loads(r['witness']) for r in published}
    before = json.loads(run['before_files'])
    if any(after[p] != before[p] for p in after) and not tools['items']:
        return False
    receipt = {'actor': store.config['actor'], 'delegated_by': grant['issued_by'], 'grant_id': grant['id'],
               'role_owner': grant['owner'], 'authority': grant['authority'],
               'collector': attempt['controller'], 'worker': attempt['session'], 'attempt': attempt['id'],
               'basis': 'role-granted staged model writer and exact service publication; bounded pre/post custody and tool completion',
               'before': before, 'after': after, 'publication':published,
               'tool_completion': tools, 'local_readiness':local, 'unknown_effects': []}
    with store.tx():
        store.db.execute("UPDATE jobs SET effects='reconciled',effect_receipt=? WHERE id=? AND active_attempt=?",
                         (encode(receipt), job['id'], attempt['id']))
        store.db.execute("UPDATE routine_runs SET after_files=?,state='reconciled',receipt=? WHERE attempt=?",
                         (encode(after), encode(receipt), attempt['id']))
    return True
