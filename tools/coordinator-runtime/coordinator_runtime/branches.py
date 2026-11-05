"""Authorized branch associations, actual context custody and cooperating fences.

Root remains a coordinator and delegates builders. Addresses are supplied by
their actual owners after observation; this module creates no provider identity.
Unknown leases survive owner loss. A successor is explicitly a new encounter.
"""
import json
from pathlib import Path

from .contracts import Refusal, canonical_uuid, digest, encode, required_text
from .resource_scopes import root

SCHEMA = """
CREATE TABLE IF NOT EXISTS branch_associations(
 id TEXT PRIMARY KEY,repository TEXT NOT NULL,device INTEGER NOT NULL,inode INTEGER NOT NULL,
 origin TEXT NOT NULL,ref TEXT NOT NULL,incarnation TEXT NOT NULL,scope TEXT NOT NULL,
 root TEXT NOT NULL,authority TEXT NOT NULL,state TEXT NOT NULL,accepted TEXT,
 created REAL NOT NULL,closed REAL,history TEXT NOT NULL);
CREATE UNIQUE INDEX IF NOT EXISTS branch_current_ref ON branch_associations(device,inode,ref)
 WHERE state IN ('assigned','active','parked');
CREATE UNIQUE INDEX IF NOT EXISTS branch_incarnation ON branch_associations(device,inode,incarnation);
CREATE TABLE IF NOT EXISTS branch_contexts(
 branch TEXT NOT NULL,kind TEXT NOT NULL,component TEXT NOT NULL,address TEXT NOT NULL,
 identity_kind TEXT NOT NULL,profile TEXT,collector TEXT NOT NULL,state TEXT NOT NULL,
 evidence TEXT NOT NULL,closed REAL,PRIMARY KEY(branch,kind,component,address));
CREATE TABLE IF NOT EXISTS branch_turns(
 id TEXT PRIMARY KEY,branch TEXT NOT NULL,kind TEXT NOT NULL,component TEXT NOT NULL,
 address TEXT NOT NULL,collector TEXT NOT NULL,profile TEXT,writer TEXT,
 material TEXT NOT NULL,state TEXT NOT NULL,created REAL NOT NULL,returned REAL,receipt TEXT);
CREATE UNIQUE INDEX IF NOT EXISTS branch_context_busy ON branch_turns(address)
 WHERE state IN ('active','unknown');
CREATE UNIQUE INDEX IF NOT EXISTS branch_writer_busy ON branch_turns(writer)
 WHERE writer IS NOT NULL AND state IN ('active','unknown');
"""


def repository_identity(repository):
    from .reviews import git
    repository=root(str(repository))
    common=Path(git(str(repository),'rev-parse','--path-format=absolute','--git-common-dir').decode().strip())
    # This is authorized source Git metadata, never provider/client forensics.
    info=root(str(common)).stat()
    return info.st_dev,info.st_ino


def association(store, key, active=True):
    row = store.one('SELECT * FROM branch_associations WHERE id=?', (key,))
    if not row or active and row['state'] != 'active':
        raise Refusal('branch association unavailable; explicit owner acceptance/recovery required')
    path = root(row['repository'], store.config.get('artifact_exclusions', []))
    if repository_identity(path) != (row['device'], row['inode']):
        raise Refusal('authorized repository identity changed; preserve original association')
    return row


def record(store, key, actor, entry):
    row = association(store, key, active=False)
    history = json.loads(row['history'])
    history.append({'actor': actor, 'at': store.clock(), **entry})
    store.budget(None, len(encode(history).encode()))
    store.db.execute('UPDATE branch_associations SET history=? WHERE id=?', (encode(history), key))


def register(store, actor, receipt):
    cap, _ = store.processing.current()
    if actor != cap['issuer']:
        raise Refusal('actual Work issuer selects branch authority')
    fields = {'id','repository','origin','ref','incarnation','scope','root','authority'}
    if not isinstance(receipt, dict) or set(receipt) != fields:
        raise Refusal('exact branch lifecycle/repository/ref/scope/responsible Root/authority required')
    for name in fields:
        required_text(receipt[name], 'actual branch ' + name, 4000)
    canonical_uuid(receipt['root'])
    if not receipt['ref'].startswith('refs/heads/'):
        raise Refusal('full authorized branch ref required')
    repository = root(receipt['repository'], store.config.get('artifact_exclusions', []))
    device,inode = repository_identity(repository)
    from .reviews import git
    git(str(repository),'rev-parse','--verify',receipt['ref']+'^{commit}')
    if git(str(repository),'remote','get-url','origin').decode().strip()!=receipt['origin']:
        raise Refusal('authorized origin differs from actual source repository')
    if not store.one('SELECT package FROM admissions WHERE package=?',(receipt['scope'],)):
        raise Refusal('branch binding needs its actual admitted scope; no general Main authority')
    with store.tx():
        if store.one('SELECT id FROM branch_associations WHERE id=?', (receipt['id'],)):
            raise Refusal('branch incarnation already exists; never overwrite its history')
        store.budget(None, len(encode(receipt).encode()) + 4096)
        store.db.execute('INSERT INTO branch_associations VALUES(?,?,?,?,?,?,?,?,?,?,?,NULL,?,NULL,?)',
                         (receipt['id'], str(repository), device,inode, receipt['origin'],
                          receipt['ref'], receipt['incarnation'], receipt['scope'], receipt['root'],
                          receipt['authority'], 'assigned', store.clock(), encode([{'actor':actor,'assignment':receipt}])) )
    return association(store, receipt['id'], active=False)


def accept(store, key, actor, evidence):
    required_text(evidence, 'actual Root acceptance and delegation evidence')
    with store.tx():
        row = association(store, key, active=False)
        if actor != row['root'] or row['state'] != 'assigned':
            raise Refusal('only genuinely assigned Root can accept this branch')
        store.db.execute("UPDATE branch_associations SET state='active',accepted=? WHERE id=?", (evidence, key))
        record(store, key, actor, {'accepted':evidence})
    return route(store, key)


def link(store, key, actor, receipt):
    """Root links an actually observed delegated builder; never relabel it Root."""
    fields = {'address','identity_kind','profile','collector','evidence'}
    if not isinstance(receipt, dict) or set(receipt) != fields:
        raise Refusal('observed builder address/kind/account/original collector/evidence required')
    for name in fields:
        required_text(receipt[name], 'observed builder ' + name)
    with store.tx():
        row = association(store, key)
        if actor != row['root'] or receipt['collector'] != actor:
            raise Refusal('actual responsible Root links its genuinely owned continuing builder')
        if receipt['profile'] not in store.config['profiles']:
            raise Refusal('observed account outside authority; no migration')
        # Linking is evidence, not execution admission. Every turn rechecks pool.
        store.budget(None, len(encode(receipt).encode())+2048)
        store.db.execute('INSERT INTO branch_contexts VALUES(?,?,?,?,?,?,?,?,?,NULL)',
                         (key,'builder','',receipt['address'],receipt['identity_kind'],receipt['profile'],
                          receipt['collector'],'available',receipt['evidence']))
        record(store,key,actor,{'builder_observed':receipt})
    return route(store,key)


def route(store, key):
    row = association(store,key,active=False)
    return {'branch':row, 'contexts':store.rows('SELECT * FROM branch_contexts WHERE branch=?',(key,)),
            'turns':store.rows("SELECT * FROM branch_turns WHERE branch=? AND state IN ('active','unknown')",(key,)),
            'meaning':'association/history only; responsible Root delegates builders; each future turn needs current admission'}


def job_branch(store, job):
    if not job or 'members' not in job:
        return None  # Legacy standalone executor has no branch association.
    if job.get('phase') in {'integrator','cleanup'}:
        return None  # Sole role integrator may consolidate several branches.
    keys = {store.event(m['event']).get('branch_binding') for m in json.loads(job['members'])}
    if keys == {None}:
        return None
    if len(keys) != 1 or None in keys:
        raise Refusal('a branch execution cannot mix branch lifecycles or unbound members')
    branch=association(store,next(iter(keys)))
    if any(store.event(m['event']).get('package')!=branch['scope'] for m in json.loads(job['members'])):
        raise Refusal('branch association cannot expand the original admitted scope; return to Work')
    return branch


def delivery_branch(store,payload,job=None,event=None):
    keys=set()
    if job:
        keys={store.event(m['event']).get('branch_binding') for m in json.loads(store.job(job)['members'])}-{None}
    elif event:
        keys={store.event(event).get('branch_binding')}-{None}
    selected=payload.get('branch_binding')
    if selected:
        keys={selected} if not keys or selected in keys else set()
    if len(keys)!=1:
        # An integrator's exact per-branch handoff can select an association
        # only from its actual admitted scope/ref, never general Main repair.
        ref=payload.get('ref')
        rows=store.rows("SELECT id FROM branch_associations WHERE state='active' AND scope=? AND (ref=? OR id=?)",
                        (payload.get('package'),ref,ref)) if ref else []
        keys={r['id'] for r in rows}
    if len(keys)!=1:
        return None
    branch=association(store,next(iter(keys)))
    if payload.get('package')!=branch['scope']:
        raise Refusal('branch routing cannot expand actual admitted scope; return to Work')
    return branch


def board_review(store,body):
    """Typed factual intake from an actual public Board post, never private state."""
    if not isinstance(body.get('text'),str): return None
    try:
        wire=json.loads(body['text'])
    except (ValueError,TypeError): return None
    if not isinstance(wire,dict) or 'review' not in wire: return None
    if set(wire)-{'branch_binding'}!={'review'} or not isinstance(wire['review'],dict) or set(wire['review'])!={'component','origin','base','head','previous','answered_ids'}:
        raise Refusal('typed review post accepts factual packet and branch binding only; goals stay outside Source')
    branch=association(store,wire['branch_binding']) if wire.get('branch_binding') else None
    if branch and body['author']!=branch['root']:
        raise Refusal('actual responsible Root supplies branch review material')
    return {'packet':wire['review'],'branch':branch}


def review_key(store, job, packet):
    branch = job_branch(store,job)
    return ('branch:' + digest({'branch':branch['id'],'component':packet.get('component')})
            if branch else packet.get('component'))


def review_policy(store, job, policy, packet):
    branch = job_branch(store,job)
    if not branch:
        return policy
    selected = policy['components'].get(packet['component'])
    if not selected or selected['repository'] != branch['repository'] or packet['origin'] != branch['origin']:
        raise Refusal('review material outside actual branch repository/origin authority')
    history = store.home / 'review-history' / digest({'branch':branch['id'],'component':packet['component']})
    return {**policy,'components':{**policy['components'],packet['component']:{**selected,'history':str(history)}}}


def acquire_attempt(store,job,attempt,context=None):
    branch=job_branch(store,job)
    if not branch:
        return
    task=store.config['tasks'][job['task']]
    if task.get('require_package_scope'):
        from .contracts import scoped_task
        task=scoped_task(job['task'],task,store.one('SELECT * FROM admissions WHERE package=?',(job['package'],)))
    review=store.processing and store.processing.review_task(job['task'])
    address=context['run'] if context and context['run'] else 'local-attempt:'+attempt
    writer=None
    if task['effects']!='none':
        # Both branch-ref and worktree fences cover all cooperating delegated
        # writers. Ref/lifecycle operations use these same leases.
        if store.one("SELECT id FROM branch_turns WHERE branch=? AND writer IS NOT NULL AND state IN ('active','unknown')",(branch['id'],)):
            raise Refusal('actual previous branch writer/effects remain owned')
        info=root(task['cwd'],store.config.get('artifact_exclusions',[])).stat()
        writer=encode([info.st_dev,info.st_ino])
    store.db.execute('INSERT INTO branch_turns VALUES(?,?,?,?,?,?,?,?,?,?,?,NULL,NULL)',
                     (attempt,branch['id'],'review' if review else 'delegated-builder','',address,store.controller,
                      store.attempt(attempt)['profile'],writer,job['members'],'active',store.clock()))


def settle_attempt(store,attempt):
    row=store.one('SELECT * FROM branch_turns WHERE id=?',(attempt,))
    if not row or row['state']=='returned':
        return
    actual=store.attempt(attempt); job=store.job(actual['job'])
    no_start=json.loads(actual['detail']).get('known_not_started') and actual['begin'] is None
    returned=(actual['collected'] is not None and (no_start or actual['ended'] is not None and
              actual['capture']=='complete' and not actual['error']) and job['effects'] in {'none','reconciled'})
    if row['writer'] and not no_start:
        returned=False  # Actual coding handback is a separate owned end receipt.
    store.db.execute('UPDATE branch_turns SET state=?,returned=?,receipt=? WHERE id=?',
                     ('returned' if returned else 'unknown',store.clock() if returned else None,
                      encode({'original_attempt':attempt,'original_collector':actual['controller'],
                              'actual_END':actual['exit'],'effects':job['effects'],'capture':actual['capture']}),attempt))


def begin(store,key,actor,receipt):
    fields={'id','kind','component','address','profile','material','writer'}
    if not isinstance(receipt,dict) or set(receipt)!=fields:
        raise Refusal('exact owned branch turn/material/writer required')
    branch=association(store,key)
    if actor != branch['root'] or receipt['kind'] not in {'builder','review'}:
        raise Refusal('responsible Root delegates a separate builder/reviewer')
    context=store.one("SELECT * FROM branch_contexts WHERE branch=? AND kind=? AND component=? AND address=? AND state='available'",
                       (key,receipt['kind'],receipt['component'],receipt['address']))
    if not context or context['profile'] != receipt['profile']:
        raise Refusal('actual continuing context unavailable; preserve originals and explicitly recover')
    # The normal launcher still holds admission through process creation. This
    # selection check never grandfathers a future turn after pool exclusion.
    current=store.execution_pool.status()
    if receipt['profile'] not in current.get('enabled',[]):
        raise Refusal('bound context account unavailable/excluded for future input; no silent migration')
    if receipt['writer'] and receipt['kind']!='builder':
        raise Refusal('goal-blind reviewer never acquires a writer')
    from .reviews import git
    pins=receipt['material']
    if not isinstance(pins,dict) or set(pins)!={'head','tree','parents'}:
        raise Refusal('exact immutable head/tree/all parents required for each branch turn')
    actual=git(branch['repository'],'show','-s','--format=%H%n%T%n%P',pins['head']).decode().splitlines()
    if actual[:2]!=[pins['head'],pins['tree']] or (actual[2].split() if len(actual)>2 else [])!=pins['parents']:
        raise Refusal('branch input material differs from exact immutable Git source')
    writer=None
    if receipt['writer']:
        path=root(receipt['writer'],store.config.get('artifact_exclusions',[])); info=path.stat()
        if repository_identity(path)!=(branch['device'],branch['inode']) or git(str(path),'symbolic-ref','--quiet','HEAD').decode().strip()!=branch['ref']:
            raise Refusal('actual writer checkout/ref differs from this branch authority')
        writer=encode([info.st_dev,info.st_ino])
    with store.tx():
        store.budget(None,len(encode(receipt).encode())+2048)
        if store.one("SELECT id FROM branch_turns WHERE address=? AND state IN ('active','unknown')",(receipt['address'],)):
            raise Refusal('one actual context input at a time, including unknown predecessors')
        if writer and store.one("SELECT id FROM branch_turns WHERE writer=? AND state IN ('active','unknown')",(writer,)):
            raise Refusal('one actual worktree writer at a time across branch associations')
        # A second lease fences the branch ref even if a different checkout was
        # supplied. Unknown predecessors prohibit conflicting ref operations.
        if writer and store.one("SELECT id FROM branch_turns WHERE branch=? AND writer IS NOT NULL AND state IN ('active','unknown')",(key,)):
            raise Refusal('original branch writer still owns this ref')
        store.db.execute('INSERT INTO branch_turns VALUES(?,?,?,?,?,?,?,?,?,?,?,NULL,NULL)',
                         (receipt['id'],key,receipt['kind'],receipt['component'],receipt['address'],actor,
                          receipt['profile'],writer,encode(receipt['material']),'active',store.clock()))
    return store.one('SELECT * FROM branch_turns WHERE id=?',(receipt['id'],))


def context_disposition(store,key,actor,receipt):
    fields={'kind','component','address','state','evidence','remaining_holds'}
    if not isinstance(receipt,dict) or set(receipt)-{'native_close'}!=fields or receipt['state'] not in {'unavailable','closed'}:
        raise Refusal('actual context disposition and remaining custody required')
    required_text(receipt['evidence'],'actual context owner close/unavailability evidence')
    if not isinstance(receipt['remaining_holds'],list):
        raise Refusal('explicit remaining holds required')
    with store.tx():
        row=association(store,key,active=False)
        context=store.one('SELECT * FROM branch_contexts WHERE branch=? AND kind=? AND component=? AND address=?',
                           (key,receipt['kind'],receipt['component'],receipt['address']))
        if not context or actor not in {row['root'],context['collector']}:
            raise Refusal('actual context custodian or responsible Root required')
        if store.one("SELECT id FROM branch_turns WHERE address=? AND state IN ('active','unknown')",(receipt['address'],)):
            raise Refusal('actual turn/unknown writer still held; close assertion cannot release it')
        if receipt['state']=='closed' and receipt['remaining_holds']:
            raise Refusal('remaining context obligations prevent closure')
        if receipt['kind']=='review' and receipt['state']=='closed' and store.one("SELECT component FROM review_contexts WHERE run=? AND state!='closed'",(receipt['address'],)):
            raise Refusal('native reviewer close belongs to original supported collector')
        if receipt['kind']=='review' and receipt['state']=='closed' and not store.one("SELECT component FROM review_contexts WHERE run=? AND state='closed'",(receipt['address'],)):
            close=receipt.get('native_close')
            if (not isinstance(close,dict) or set(close)!={'run','actual_END','collector','receipt','evidence'}
                    or close['run']!=receipt['address'] or type(close['actual_END']) is not int or close['actual_END']!=0
                    or not isinstance(close['receipt'],dict) or close['receipt'].get('class')!='closed'
                    or close['receipt'].get('physical_close') is not True or close['receipt'].get('account_errors')
                    or close['receipt'].get('collection',{}).get('errors')):
                raise Refusal('archived predecessor native close remains held; actual owner-supported full close/END receipt required')
            required_text(close['collector'],'actual native close caller collector')
            required_text(close['evidence'],'actual public original context close evidence; not collection of lost caller')
        store.db.execute('UPDATE branch_contexts SET state=?,closed=? WHERE branch=? AND kind=? AND component=? AND address=?',
                         (receipt['state'],store.clock() if receipt['state']=='closed' else None,key,receipt['kind'],receipt['component'],receipt['address']))
        record(store,key,actor,{'context_disposition':receipt})
    return route(store,key)


def event_held(store,event):
    binding=store.one("SELECT COALESCE(json_extract(e.payload,'$.branch_binding'),json_extract(c.binding,'$.header.branch_binding')) AS branch FROM events e LEFT JOIN source_custody c ON c.event=e.id WHERE e.id=?",(event,))
    if not binding or not binding['branch']:
        return False
    row=store.one('SELECT * FROM branch_associations WHERE id=?',(binding['branch'],))
    return (not row or row['closed'] is None or store.clock()<row['closed']+86400
            or store.one("SELECT address FROM branch_contexts WHERE branch=? AND (state!='closed' OR closed IS NULL OR closed>?)",(binding['branch'],store.clock()-86400)) is not None
            or store.one("SELECT id FROM branch_turns WHERE branch=? AND state IN ('active','unknown')",(binding['branch'],)) is not None)


def end(store,key,actor,turn,receipt):
    if not isinstance(receipt,dict) or set(receipt)-{'handback'}!={'activity','actual_END','effects','evidence'}:
        raise Refusal('actual original activity/END/effects/evidence required')
    required_text(receipt['evidence'],'original collector evidence')
    if receipt['activity'] not in {'returned','unknown'} or receipt['actual_END'] is not None and type(receipt['actual_END']) is not int:
        raise Refusal('unknown is not a manufactured numeric END')
    with store.tx():
        row=store.one('SELECT * FROM branch_turns WHERE id=? AND branch=?',(turn,key))
        if not row or row['collector']!=actor or row['state'] not in {'active','unknown'}:
            raise Refusal('original collector retains turn and writer custody')
        closed=receipt['activity']=='returned' and type(receipt['actual_END']) is int and receipt['effects']=='reconciled'
        if closed and row['writer'] and row['kind'] in {'builder','delegated-builder'}:
            branch=association(store,key)
            handback=receipt.get('handback')
            if (not isinstance(handback,dict) or handback.get('errors') or handback.get('head')!=handback.get('remote_head')
                    or not handback.get('head') or handback.get('branch')!=branch['ref'].removeprefix('refs/heads/')
                    or not handback.get('attempts')):
                raise Refusal('coding worker must return actual signed commit/push/readback even partial; dirty/failed handback remains held')
            from .reviews import git
            repository=handback.get('repository')
            if repository_identity(repository)!=(branch['device'],branch['inode']):
                raise Refusal('handback belongs to a different source repository')
            if any(git(repository,*args) for args in [('diff','--name-only','-z'),('diff','--cached','--name-only','-z'),('ls-files','--others','--exclude-standard','-z')]):
                raise Refusal('actual dirty/unpublished source remains; matching remote HEAD is insufficient')
            git(repository,'verify-commit',handback['head'])
            if git(repository,'rev-parse','HEAD').decode().strip()!=handback['head']:
                raise Refusal('coding source changed after exact handback')
            if any(r.get('actual_END')!=0 or r.get('capture','complete')!='complete' for r in handback['attempts']):
                raise Refusal('actual failed/incomplete signing/push/readback commands remain explicit')
        store.db.execute('UPDATE branch_turns SET state=?,returned=?,receipt=? WHERE id=?',
                         ('returned' if closed else 'unknown',store.clock() if closed else None,encode(receipt),turn))
        record(store,key,actor,{'turn':turn,'return':receipt})
    return route(store,key)


def lifecycle(store,key,actor,receipt):
    """Explicit rename/park/Root handoff/terminal disposition; never main rebinding."""
    if not isinstance(receipt,dict) or set(receipt)!={'state','ref','root','evidence'}:
        raise Refusal('exact branch lifecycle disposition required')
    required_text(receipt['evidence'],'owner branch lifecycle evidence')
    with store.tx():
        row=association(store,key,active=False)
        if actor!=row['root'] or row['state'] in {'closed','merged','abandoned'}:
            raise Refusal('genuine current Root owns branch lifecycle; recreation is a new incarnation')
        if store.one("SELECT id FROM branch_turns WHERE branch=? AND state IN ('active','unknown')",(key,)):
            raise Refusal('original activity/writer uncertainty stays held')
        if receipt['state'] not in {'assigned','active','parked','closed','merged','abandoned'} or not receipt['ref'].startswith('refs/heads/'):
            raise Refusal('explicit lifecycle and full ref required')
        if receipt['ref']!=row['ref']:
            from .reviews import git
            git(row['repository'],'rev-parse','--verify',receipt['ref']+'^{commit}')
        canonical_uuid(receipt['root'])
        if receipt['root']!=row['root'] and receipt['state']!='assigned':
            raise Refusal('successor Root must actually accept; no inferred handoff')
        terminal=receipt['state'] in {'closed','merged','abandoned'}
        if terminal and store.one("SELECT address FROM branch_contexts WHERE branch=? AND state!='closed'",(key,)):
            raise Refusal('actual contexts/consumers must close before branch closure')
        record(store,key,actor,{'prior_ref':row['ref'],'prior_root':row['root'],'lifecycle':receipt})
        store.db.execute('UPDATE branch_associations SET state=?,ref=?,root=?,closed=? WHERE id=?',
                         (receipt['state'],receipt['ref'],receipt['root'],store.clock() if terminal else None,key))
    return route(store,key)
