"""Exact role-file publication from owned model staging, never directory authority.

Each file has a durable intent before a same-inode write. Multi-file publication
is not atomic; crashes/conflicts retain partial effects for the original owner.
"""
import json
import gzip
import os
from pathlib import Path
import stat
from contextlib import contextmanager, ExitStack

from .contracts import Refusal, encode, digest
from .custody import capture, read_file, safe_path, frozen_body, guard_frozen, refuse_log
from .cleanup import open_parent
from . import bounded_log, local_integration

SCHEMA = """
CREATE TABLE IF NOT EXISTS routine_stages(attempt TEXT,target TEXT,path TEXT,PRIMARY KEY(attempt,target));
CREATE TABLE IF NOT EXISTS file_publications(
 attempt TEXT,target TEXT,state TEXT,proposed_sha TEXT,temp TEXT,witness TEXT,error TEXT,
 PRIMARY KEY(attempt,target));
CREATE TABLE IF NOT EXISTS canonical_backups(attempt TEXT,target TEXT,path TEXT,preimage TEXT,PRIMARY KEY(attempt,target));
"""

INCOMPLETE_HOLD = 'routine canonical publication remains incomplete; effect receipt cannot waive exact preimage/publication'


def remainder_basis(store, job, old, choice, selection, board):
    """A qualified publication duty, never an owner flag for arbitrary holds.

    The owner must separately judge same purpose/WHY. Hashes bind that judgment
    to retained representations; this function does not make it for the owner.
    No historical run, stage, publication or business result is redisposed here.
    """
    from .routine import policy_for
    from .readiness import assess
    if job['hold_reason'] != INCOMPLETE_HOLD:
        raise Refusal('publication remainder cannot waive an unrelated job hold')
    if store.db.execute("SELECT COUNT(*) FROM attempts WHERE job=? AND kind='task'", (job['id'],)).fetchone()[0] != 1:
        raise Refusal('publication remainder permits at most one successor; prior task history remains binding')
    if board is None or board.role != job['role']:
        raise Refusal('publication remainder needs the current role completion authority')
    grant = board.completion_authority(store, job['task'])
    if (grant['id'] != store.enrollment(job['role'])['grant_id']
            or grant['owner'] != store.enrollment(job['role'])['owner']):
        raise Refusal('publication remainder grant/owner differs from the retained enrollment')
    effects=json.loads(job['effect_receipt']) if job['effect_receipt'] else {}
    if (job['effects'] != 'reconciled' or effects.get('actor') != grant['owner']
            or not effects.get('evidence') or effects.get('unknown_effects') != []):
        raise Refusal('publication remainder requires actual known reconciled effects')
    if store.one('SELECT id FROM attempts WHERE job=? AND (ended IS NULL OR collected IS NULL OR exit IS NULL)', (job['id'],)):
        raise Refusal('publication remainder requires every related actual collected END; unknown closure stays owned')
    for member in json.loads(job['members']):
        if digest(store.event(member['event'])) != member['hash']:
            raise Refusal('publication remainder source changed; no refreshed business purpose')
    task = store.config['tasks'][job['task']]
    allocated = stages(store, old['id'])
    publications = store.rows('SELECT p.* FROM file_publications p JOIN attempts a ON p.attempt=a.id WHERE a.job=?', (job['id'],))
    # policy_for itself validates paths with metadata. Check every retained
    # stage/target AND the raw policy targets before invoking that validator.
    raw_policy = task.get('routine_completion')
    targets = raw_policy.get('targets', []) if isinstance(raw_policy, dict) else []
    paths = [*(targets if isinstance(targets, list) else []), *allocated,
             *allocated.values(), *(p['target'] for p in publications)]
    for name in paths:
        if isinstance(name, str) and any(Path(name) == Path(p) or Path(name).is_relative_to(Path(p))
                                        for p in store.config.get('artifact_exclusions', [])):
            raise Refusal('publication remainder path excluded before metadata')
    policy = policy_for(task)
    if bounded_log.selected(task):
        raise Refusal('bounded log interruption remains original custody; no full-file remainder/replay')
    run = store.one('SELECT * FROM routine_runs WHERE attempt=?', (old['id'],))
    if (not policy or not run or run['task'] != job['task'] or run['grant_id'] != grant['id']
            or json.loads(run['policy']) != policy or run['state'] != 'prepared'):
        raise Refusal('publication remainder needs the original incomplete delegated routine run; no retrospective invention')
    local = assess(store, old)
    before = json.loads(run['before_files'])
    if set(allocated) != set(policy['targets']) or set(before) != set(allocated):
        raise Refusal('publication remainder needs the complete original staging/preimage mapping')
    if any(p['state'] != 'published' or not p['witness'] for p in publications):
        raise Refusal('unknown/partial publication intent remains binding; no remainder replay')
    if len([p for p in publications if p['attempt'] == old['id']]) == len(allocated):
        raise Refusal('publication already complete; remainder cannot redispose historical publication')
    maximum = store.config['limits'].get('max_artifact_bytes', 33554432)
    held_stages = {}
    with snapshot_lock(store):
        for target, path in allocated.items():
            body, observed = read_file(safe_path(path, [str(store.artifact_root(old['id'])/'staged')]), maximum)
            held = store.one('SELECT sha256 FROM artifact_custody WHERE attempt=? AND path=?', (old['id'], path))
            if not held or held['sha256'] != observed['sha256']:
                raise Refusal('publication remainder lacks exact original durable staging custody')
            held_stages[target] = observed
        peers = {target: current(safe_path(target, policy['targets']), maximum) for target in policy['targets']}
        if not all(p['exists'] for p in peers.values()):
            raise Refusal('publication remainder needs existing regular current peers')
        for published in publications:
            if published['target'] not in peers or peers[published['target']] != json.loads(published['witness']):
                raise Refusal('prior published effects changed; actual source/effect qualification required')
    return {'version': 1, 'hold': job['hold_reason'],
            'purpose': digest({'task': task, 'choice': choice, 'selection': selection['receipt']}),
            'peers': peers, 'grant': digest(grant), 'run': digest(run),
            'stages': held_stages, 'publications': digest(publications),
            'effects': digest(job['effect_receipt']), 'readiness': digest(local)}


def stages(store, attempt):
    return {r['target']:r['path'] for r in store.rows('SELECT target,path FROM routine_stages WHERE attempt=?',(attempt,))}


def bounded_preimage(policy, target):
    return bool(policy and policy['kind'] == bounded_log.KIND
                and target == policy['bounded_log']['target'])


def guard_preimages(store, before, policy):
    for target, witness in before.items():
        guard_preimage(store, target, witness, policy)


def guard_preimage(store, target, witness, policy):
    if bounded_preimage(policy, target):
        return  # A bounded entry never acquires the whole target preimage.
    refuse_log(target)
    if witness['exists']:
        guard_frozen(store, witness['sha256'], path=target)


def prepare(store, attempt, before, policy=None):
    store.require_attempt_execution_open(attempt)
    local_integration.current_sources(store, store.job(store.one('SELECT job FROM attempts WHERE id=?', (attempt,))['job']))
    # Reject every recorded preimage before destination allocation. A later
    # excluded item must not leave earlier files or an empty staging directory.
    # frozen_body repeats the guard at acquisition; this is no cached authority.
    guard_preimages(store, before, policy)
    root=store.artifact_root(attempt)/'staged'
    store.artifact_copy_budget(attempt, root, 0, directory=True)
    root.mkdir(mode=0o700)
    for index,(target,witness) in enumerate(before.items()):
        bounded_entry = bounded_preimage(policy, target)
        if not bounded_entry:
            refuse_log(target)
        path=root/(str(index)+'-'+Path(target).name)
        body=(b'' if bounded_entry else
              frozen_body(store, witness['sha256'], path=target)['body'] if witness['exists'] else b'')
        store.artifact_copy_budget(attempt, path, len(body))
        fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,0o600)
        with os.fdopen(fd,'wb') as stream:stream.write(body);stream.flush();os.fsync(stream.fileno())
        with store.tx():store.db.execute('INSERT INTO routine_stages VALUES(?,?,?)',(attempt,target,str(path)))


def conserve_stages(store, attempt, task):
    store.require_attempt_execution_open(attempt)
    for path in stages(store,attempt).values():capture(store,attempt,path,task)


def current(path, maximum, expected_bytes=None):
    if Path(path).name == 'WORK_LOG.md':
        raise Refusal('whole-log current witness unavailable')
    try:
        body,witness=read_file(path,maximum)
        if expected_bytes is not None and body!=expected_bytes:raise Refusal('exact canonical bytes changed')
        return {'exists':True,**witness}
    except FileNotFoundError:return {'exists':False}


@contextmanager
def snapshot_lock(store):
    from .retention_dependency import load
    selected=store.config.get('canonical_publication',{})
    if selected.get('method')!='retention-same-inode-v1':
        raise Refusal('selected retention same-inode canonical method required; no replacement fallback')
    with ExitStack() as stack:
        try:
            provider = load(selected['library'], selected.get('source_pins'),
                            store.config.get('artifact_exclusions', []))
            stack.enter_context(provider.snapshot_lock())
        except BlockingIOError:raise
        except (ValueError,OSError) as exc:raise Refusal('selected canonical snapshot lock refused: '+type(exc).__name__) from exc
        yield


def publish(store, board, job, attempt, run, task):
    from .configuration import require_current_job
    store.require_execution_open(job['id'])
    require_current_job(store, job)
    with snapshot_lock(store):
        known = store.one('SELECT * FROM local_commits WHERE attempt=?', (attempt['id'],))
        if known and known['state'] == 'published':
            local_integration.current_job(store, job)
            store.authorize_launch(attempt['id'])
            if board.completion_authority(store, job['task'])['id'] != run['grant_id']:
                raise Refusal('publication grant changed before known-effect receipt join')
            rows = store.rows('SELECT target,state,proposed_sha,witness,error FROM file_publications WHERE attempt=?', (attempt['id'],))
            if {r['target'] for r in rows} != set(json.loads(run['policy'])['targets']) or any(r['state'] != 'published' for r in rows):
                raise Refusal('known local publication lacks complete duty receipts')
            return [{**r, 'method':'previously observed local publication; receipt join only, no effect replay'} for r in rows]
        rebased, local = local_integration.rebase(store, job, attempt, run, task)
        result = locked_publish(store,board,job,attempt,rebased,task,
                                service_stages=local[0] if local else None)
        if local:
            local_integration.committed(store, attempt['id'], local[1])
        return result


def write_same_inode(fd, body):
    offset=0
    while offset<len(body):
        count=os.write(fd,body[offset:])
        if count<=0:raise OSError('canonical short write')
        offset+=count
    os.ftruncate(fd,len(body));os.fsync(fd)


def locked_publish(store, board, job, attempt, run, task, service_stages=None):
    store.require_execution_open(job['id'])
    if job['controller']!=store.controller or attempt['controller']!=store.controller:
        raise Refusal('only original owned collector publishes its staged effects')
    def fence():
        fresh=store.job(job['id'],job['token'])
        if fresh['active_attempt']!=attempt['id'] or fresh['controller']!=store.controller:
            raise Refusal('stale publication owner refused')
        grant=board.completion_authority(store,job['task'])
        store.authorize_launch(attempt['id'])
        if grant['id']!=run['grant_id']:raise Refusal('publication grant changed')
        if any(store.one('SELECT hold FROM events WHERE id=?',(m['event'],))['hold'] for m in json.loads(job['members'])):
            raise Refusal('source/resource/recovery hold fences publication')
    fence()
    before=json.loads(run['before_files']);allocated={**stages(store,attempt['id']), **(service_stages or {})}
    policy=json.loads(run['policy'])
    order=policy['targets']
    if set(allocated)!=set(before) or set(order)!=set(before):raise Refusal('exact staged publication mapping unavailable')
    is_bounded=bounded_log.selected(task)
    if is_bounded:
        order=bounded_log.inventory(policy)
    maximum=store.config['limits'].get('max_artifact_bytes',33554432)
    proposed={}
    # Validate every preimage/proposal under the cooperative canonical lock.
    for target in order:
        path=allocated[target]
        body,witness=read_file(safe_path(path,[str(store.artifact_root(attempt['id'])/('local-commit' if service_stages and target in service_stages else 'staged'))]),maximum)
        held=store.one('SELECT sha256 FROM artifact_custody WHERE attempt=? AND path=?',(attempt['id'],path))
        if not held or held['sha256']!=witness['sha256']:raise Refusal('proposed file lacks exact durable custody')
        proposed[target]=(body,witness)
        old=store.one('SELECT * FROM file_publications WHERE attempt=? AND target=?',(attempt['id'],target))
        expected_bytes=body if old and old['state']=='published' else frozen_body(store, before[target]['sha256'], task, target)['body']
        observed=current(safe_path(target,order),maximum,expected_bytes)
        if old:
            if old['state']!='published':raise Refusal('interrupted same-inode write remains uncertain; no blind replay')
            if old['proposed_sha']!=witness['sha256'] or observed!=json.loads(old['witness']):
                raise Refusal('recorded publication changed; actual owner recovery required')
        elif not before[target]['exists'] or observed!=before[target]:
            raise Refusal('exact regular canonical byte/inode preimage changed or missing')
    backups=store.artifact_root(attempt['id'])/'before'
    store.artifact_copy_budget(attempt['id'], backups, 0, directory=True)
    backups.mkdir(mode=0o700,exist_ok=True)
    # Durable compressed BEFORE-only backups for the whole batch precede writes.
    for index,target in enumerate(order):
        row=store.one('SELECT * FROM canonical_backups WHERE attempt=? AND target=?',(attempt['id'],target))
        if row:continue  # Never rewrite/reclaim an existing recovery source.
        source=frozen_body(store, before[target]['sha256'], task, target)['body']
        path=backups/(str(index)+'-'+Path(target).name+'.before.gz')
        store.artifact_copy_budget(attempt['id'], path, len(source)+65536, journal_incoming=len(source)+65536)
        fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,0o600)
        with os.fdopen(fd,'wb') as stream:
            with gzip.GzipFile(fileobj=stream,mode='wb',mtime=0) as compressed:compressed.write(source)
            stream.flush();os.fsync(stream.fileno())
        directory=os.open(backups,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        try:os.fsync(directory)
        finally:os.close(directory)
        capture(store,attempt['id'],str(path),task)
        with store.tx():store.db.execute('INSERT INTO canonical_backups VALUES(?,?,?,?)',(attempt['id'],target,str(path),encode(before[target])))
    for target,(body,witness) in proposed.items():
        old=store.one('SELECT state FROM file_publications WHERE attempt=? AND target=?',(attempt['id'],target))
        if old:continue
        fence()
        path=safe_path(target,order)
        preimage=frozen_body(store, before[target]['sha256'], task, target)['body']
        if current(path,maximum,preimage)!=before[target]:raise Refusal('canonical preimage changed immediately before write')
        if before[target]['sha256']==witness['sha256']:
            with store.tx():store.db.execute("INSERT INTO file_publications VALUES(?,?,'published',?,NULL,?,NULL)",(attempt['id'],target,witness['sha256'],encode(before[target])))
            continue
        parent,name=open_parent(Path('/'),path)
        fd=None
        try:
            fd=os.open(name,os.O_RDWR|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=parent)
            info=os.fstat(fd)
            expected=before[target]
            if (not stat.S_ISREG(info.st_mode) or info.st_nlink!=1 or info.st_uid!=os.getuid()
                    or (info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns)!=(expected['dev'],expected['ino'],expected['size'],expected['mtime'])):
                raise Refusal('exact same-inode regular descriptor precondition failed')
            with store.tx():store.db.execute("INSERT INTO file_publications VALUES(?,?,'intent',?,NULL,NULL,NULL)",(attempt['id'],target,witness['sha256']))
            fence()
            if current(path,maximum,preimage)!=expected:raise Refusal('canonical exact bytes/metadata changed before mutation')
            write_same_inode(fd,body)
            after=os.fstat(fd)
            if (after.st_dev,after.st_ino,after.st_uid,after.st_gid,stat.S_IMODE(after.st_mode))!=(info.st_dev,info.st_ino,info.st_uid,info.st_gid,stat.S_IMODE(info.st_mode)):
                raise Refusal('canonical inode/mode/ownership changed during write')
            observed=current(path,maximum,body)
            if observed.get('sha256')!=witness['sha256'] or (observed['dev'],observed['ino'])!=(info.st_dev,info.st_ino):
                raise Refusal('same-inode published byte readback failed')
            with store.tx():store.db.execute("UPDATE file_publications SET state='published',witness=? WHERE attempt=? AND target=?",(encode(observed),attempt['id'],target))
        except Exception as exc:
            with store.tx():store.db.execute('UPDATE file_publications SET error=? WHERE attempt=? AND target=?',(type(exc).__name__+': '+str(exc)[:500],attempt['id'],target))
            raise
        finally:
            if fd is not None:os.close(fd)
            os.close(parent)
    if is_bounded:
        bounded_log.publish(store,board,job,attempt,run,task,fence)
    for target in order:
        # Custody is a snapshot, not a mutable latest-path cache. A declared
        # input may already conserve this path's preimage. Keep it intact;
        # exact postimages live at conserved stages and file_publications.
        if not store.one('SELECT path FROM artifact_custody WHERE attempt=? AND path=?',(attempt['id'],target)):
            capture(store,attempt['id'],target,task,role_owned=True)
    return [{**r,'before_gzip':(None if is_bounded and r['target']==policy['bounded_log']['target'] else store.one('SELECT path FROM canonical_backups WHERE attempt=? AND target=?',(attempt['id'],r['target']))['path']),
             'method':('counted-kernel-copy-prepend-v1' if is_bounded and r['target']==policy['bounded_log']['target'] else
                       'retention.snapshot_lock + exact preimage + before-only gzip + same-inode write')}
            for r in store.rows('SELECT target,state,proposed_sha,witness,error FROM file_publications WHERE attempt=?',(attempt['id'],))]
