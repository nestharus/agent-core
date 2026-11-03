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

from .contracts import Refusal, encode, artifact_paths
from .custody import capture, read_file, safe_path
from .cleanup import open_parent

SCHEMA = """
CREATE TABLE IF NOT EXISTS routine_stages(attempt TEXT,target TEXT,path TEXT,PRIMARY KEY(attempt,target));
CREATE TABLE IF NOT EXISTS file_publications(
 attempt TEXT,target TEXT,state TEXT,proposed_sha TEXT,temp TEXT,witness TEXT,error TEXT,
 PRIMARY KEY(attempt,target));
CREATE TABLE IF NOT EXISTS canonical_backups(attempt TEXT,target TEXT,path TEXT,preimage TEXT,PRIMARY KEY(attempt,target));
"""


def stages(store, attempt):
    return {r['target']:r['path'] for r in store.rows('SELECT target,path FROM routine_stages WHERE attempt=?',(attempt,))}


def prepare(store, attempt, before):
    root=store.home/'artifacts'/attempt/'staged'
    root.mkdir(mode=0o700)
    for index,(target,witness) in enumerate(before.items()):
        path=root/(str(index)+'-'+Path(target).name)
        body=store.one('SELECT body FROM artifact_blobs WHERE sha256=?',(witness['sha256'],))['body'] if witness['exists'] else b''
        store.budget(None,len(body)+1024)
        fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,0o600)
        with os.fdopen(fd,'wb') as stream:stream.write(body);stream.flush();os.fsync(stream.fileno())
        with store.tx():store.db.execute('INSERT INTO routine_stages VALUES(?,?,?)',(attempt,target,str(path)))


def artifact_view(store, attempt, answer):
    mapping=stages(store,attempt)
    if not mapping:return answer
    artifact_paths(answer.get('artifacts'))
    def mapped(item):
        if isinstance(item,str):return mapping.get(item,item)
        if 'files' in item:return {**item,'files':[mapped(child) for child in item['files']]}
        return {**item,'path':mapping.get(item['path'],item['path'])}
    return {**answer,'artifacts':[mapped(item) for item in answer['artifacts']]}


def conserve_stages(store, attempt, task):
    for path in stages(store,attempt).values():capture(store,attempt,path,task)


def current(path, maximum, expected_bytes=None):
    try:
        body,witness=read_file(path,maximum)
        if expected_bytes is not None and body!=expected_bytes:raise Refusal('exact canonical bytes changed')
        return {'exists':True,**witness}
    except FileNotFoundError:return {'exists':False}


@contextmanager
def snapshot_lock(store):
    from .board import module_at
    selected=store.config.get('canonical_publication',{})
    if selected.get('method')!='retention-same-inode-v1':
        raise Refusal('selected retention same-inode canonical method required; no replacement fallback')
    with ExitStack() as stack:
        try:stack.enter_context(module_at(selected['library'],'retention').snapshot_lock())
        except BlockingIOError:raise
        except (ValueError,OSError) as exc:raise Refusal('selected canonical snapshot lock refused: '+type(exc).__name__) from exc
        yield


def publish(store, board, job, attempt, run, task):
    with snapshot_lock(store):
        return locked_publish(store,board,job,attempt,run,task)


def write_same_inode(fd, body):
    offset=0
    while offset<len(body):
        count=os.write(fd,body[offset:])
        if count<=0:raise OSError('canonical short write')
        offset+=count
    os.ftruncate(fd,len(body));os.fsync(fd)


def locked_publish(store, board, job, attempt, run, task):
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
    before=json.loads(run['before_files']);allocated=stages(store,attempt['id'])
    order=json.loads(run['policy'])['targets']
    if set(allocated)!=set(before) or set(order)!=set(before):raise Refusal('exact staged publication mapping unavailable')
    maximum=store.config['limits'].get('max_artifact_bytes',33554432)
    proposed={}
    # Validate every preimage/proposal under the cooperative canonical lock.
    for target in order:
        path=allocated[target]
        body,witness=read_file(safe_path(path,[str(store.home/'artifacts'/attempt['id']/'staged')]),maximum)
        held=store.one('SELECT sha256 FROM artifact_custody WHERE attempt=? AND path=?',(attempt['id'],path))
        if not held or held['sha256']!=witness['sha256']:raise Refusal('proposed file lacks exact durable custody')
        proposed[target]=(body,witness)
        old=store.one('SELECT * FROM file_publications WHERE attempt=? AND target=?',(attempt['id'],target))
        expected_bytes=body if old and old['state']=='published' else store.one('SELECT body FROM artifact_blobs WHERE sha256=?',(before[target]['sha256'],))['body']
        observed=current(safe_path(target,order),maximum,expected_bytes)
        if old:
            if old['state']!='published':raise Refusal('interrupted same-inode write remains uncertain; no blind replay')
            if old['proposed_sha']!=witness['sha256'] or observed!=json.loads(old['witness']):
                raise Refusal('recorded publication changed; actual owner recovery required')
        elif not before[target]['exists'] or observed!=before[target]:
            raise Refusal('exact regular canonical byte/inode preimage changed or missing')
    backups=store.home/'artifacts'/attempt['id']/'before'
    backups.mkdir(mode=0o700,exist_ok=True)
    # Durable compressed BEFORE-only backups for the whole batch precede writes.
    for index,target in enumerate(order):
        row=store.one('SELECT * FROM canonical_backups WHERE attempt=? AND target=?',(attempt['id'],target))
        if row:continue  # Never rewrite/reclaim an existing recovery source.
        source=store.one('SELECT body FROM artifact_blobs WHERE sha256=?',(before[target]['sha256'],))['body']
        path=backups/(str(index)+'-'+Path(target).name+'.before.gz')
        store.budget(None,len(source)+65536)
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
        preimage=store.one('SELECT body FROM artifact_blobs WHERE sha256=?',(before[target]['sha256'],))['body']
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
    for target in order:capture(store,attempt['id'],target,task,role_owned=True)
    return [{**r,'before_gzip':store.one('SELECT path FROM canonical_backups WHERE attempt=? AND target=?',(attempt['id'],r['target']))['path'],
             'method':'retention.snapshot_lock + exact preimage + before-only gzip + same-inode write'}
            for r in store.rows('SELECT target,state,proposed_sha,witness,error FROM file_publications WHERE attempt=?',(attempt['id'],))]
