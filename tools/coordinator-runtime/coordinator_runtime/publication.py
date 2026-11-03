"""Exact role-file publication from owned model staging, never directory authority.

Each file has a durable intent before atomic replacement. Multi-file publication
is not atomic; crashes/conflicts retain partial effects for the original owner.
"""
import json
import os
from pathlib import Path
import stat

from .contracts import Refusal, encode
from .custody import capture, read_file, safe_path
from .cleanup import open_parent

SCHEMA = """
CREATE TABLE IF NOT EXISTS routine_stages(attempt TEXT,target TEXT,path TEXT,PRIMARY KEY(attempt,target));
CREATE TABLE IF NOT EXISTS file_publications(
 attempt TEXT,target TEXT,state TEXT,proposed_sha TEXT,temp TEXT,witness TEXT,error TEXT,
 PRIMARY KEY(attempt,target));
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
    if not isinstance(answer.get('artifacts'),list):raise Refusal('declared artifacts must be a list')
    items=[]
    for item in answer.get('artifacts',[]):
        if isinstance(item,str):items.append(mapping.get(item,item))
        elif isinstance(item,dict):items.append({**item,'path':mapping.get(item.get('path'),item.get('path'))} if isinstance(item.get('path'),str) else item)
        else:items.append(item)
    return {**answer,'artifacts':items}


def conserve_stages(store, attempt, task):
    for path in stages(store,attempt).values():capture(store,attempt,path,task)


def current(path, maximum):
    try:
        body,witness=read_file(path,maximum)
        return {'exists':True,**witness}
    except FileNotFoundError:return {'exists':False}


def publish(store, board, job, attempt, run, task):
    if job['controller']!=store.controller or attempt['controller']!=store.controller:
        raise Refusal('only original owned collector publishes its staged effects')
    def held_sources():
        if any(store.one('SELECT hold FROM events WHERE id=?',(m['event'],))['hold'] for m in json.loads(job['members'])):
            raise Refusal('source/resource/recovery hold fences publication')
    held_sources()
    before=json.loads(run['before_files']);allocated=stages(store,attempt['id'])
    order=json.loads(run['policy'])['targets']
    if set(allocated)!=set(before) or set(order)!=set(before):raise Refusal('exact staged publication mapping unavailable; no direct-write fallback')
    mapping={target:allocated[target] for target in order}  # Declared order, never SQL/filename order.
    maximum=store.config['limits'].get('max_artifact_bytes',33554432)
    # Preflight the complete batch before the first canonical effect.
    proposed={}
    for target,path in mapping.items():
        body,witness=read_file(safe_path(path,[str(store.home/'artifacts'/attempt['id']/'staged')]),maximum)
        conserved=store.one('SELECT sha256 FROM artifact_custody WHERE attempt=? AND path=?',(attempt['id'],path))
        if not conserved or conserved['sha256']!=witness['sha256']:raise Refusal('proposed file lacks exact durable custody')
        proposed[target]=(body,witness)
        old=store.one('SELECT * FROM file_publications WHERE attempt=? AND target=?',(attempt['id'],target))
        observed=current(Path(target),maximum)
        if old and old['proposed_sha']!=witness['sha256']:raise Refusal('publication proposal changed after durable intent')
        if old and old['state']=='published':
            if observed!=json.loads(old['witness']):raise Refusal('published file changed; retain real owner recovery')
        elif old:
            raise Refusal('interrupted publication intent remains uncertain; actual owner recovery required, no replay or invented actor receipt')
        elif observed!=before[target]:raise Refusal('canonical before-state changed; no overwrite or blind replay')
    for index,(target,(body,witness)) in enumerate(proposed.items()):
        fresh=store.job(job['id'],job['token'])
        if fresh['active_attempt']!=attempt['id'] or fresh['controller']!=store.controller:
            raise Refusal('stale publication owner refused')
        grant=board.completion_authority(store,job['task'])
        store.authorize_launch(attempt['id'])
        held_sources()
        if grant['id']!=run['grant_id']:raise Refusal('publication grant changed')
        old=store.one('SELECT * FROM file_publications WHERE attempt=? AND target=?',(attempt['id'],target))
        if old and old['state']=='published':continue
        path=safe_path(target,list(before))
        if before[target].get('sha256')==witness['sha256']:
            with store.tx():store.db.execute("INSERT OR IGNORE INTO file_publications VALUES(?,?,'published',?,NULL,?,NULL)",(attempt['id'],target,witness['sha256'],encode(before[target])))
            continue  # Conserved unchanged target; do not manufacture a write.
        temp='.coordinator-'+attempt['id']+'-'+str(index)
        with store.tx():
            store.db.execute("INSERT OR IGNORE INTO file_publications VALUES(?,?,'intent',?,?,NULL,NULL)",(attempt['id'],target,witness['sha256'],str(path.parent/temp)))
        parent,name=open_parent(Path('/'),path)
        try:
            # A leftover temporary is retained, never reopened or overwritten.
            fd=os.open(temp,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,0o600,dir_fd=parent)
            with os.fdopen(fd,'wb') as stream:
                stream.write(body);stream.flush();os.fsync(stream.fileno())
                if before[target]['exists']:
                    info=os.stat(name,dir_fd=parent,follow_symlinks=False)
                    os.fchmod(stream.fileno(),stat.S_IMODE(info.st_mode)&0o777)
            board.completion_authority(store,job['task'])
            store.authorize_launch(attempt['id'])
            held_sources()
            if current(path,maximum)!=before[target]:raise Refusal('canonical changed immediately before publication')
            os.replace(temp,name,src_dir_fd=parent,dst_dir_fd=parent);os.fsync(parent)
            observed=current(path,maximum)
            if observed.get('sha256')!=witness['sha256']:raise Refusal('published content changed; actual effects remain held')
            with store.tx():store.db.execute("UPDATE file_publications SET state='published',witness=?,error=NULL WHERE attempt=? AND target=?",(encode(observed),attempt['id'],target))
        except Exception as exc:
            with store.tx():store.db.execute('UPDATE file_publications SET error=? WHERE attempt=? AND target=?',(type(exc).__name__+': '+str(exc)[:500],attempt['id'],target))
            raise
        finally:os.close(parent)
    for target in mapping:capture(store,attempt['id'],target,task,role_owned=True)
    return store.rows('SELECT target,state,proposed_sha,temp,witness,error FROM file_publications WHERE attempt=?',(attempt['id'],))
