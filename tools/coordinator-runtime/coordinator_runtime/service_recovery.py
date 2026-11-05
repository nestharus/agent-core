"""Explicit informed recovery; no adopted child wait, END or same-session claim."""
import fcntl
import json
import os

from .contracts import Refusal, digest, encode, required_text

SCHEMA = """
CREATE TABLE IF NOT EXISTS service_recoveries(
 predecessor TEXT PRIMARY KEY,capability TEXT NOT NULL,issuer TEXT NOT NULL,
 basis TEXT NOT NULL,receipt TEXT NOT NULL,created REAL NOT NULL);
CREATE TABLE IF NOT EXISTS review_predecessors(
 id TEXT PRIMARY KEY,component TEXT NOT NULL,context TEXT NOT NULL,calls TEXT NOT NULL,
 disposition TEXT NOT NULL,receipt TEXT NOT NULL,created REAL NOT NULL);
"""


def basis(store, controller):
    run=store.one('SELECT * FROM processing_runs WHERE controller=?',(controller,))
    if not run:
        raise Refusal('exact original controller required')
    material={'run':run,'original_capability':store.one('SELECT * FROM processing_capabilities WHERE id=?',(run['capability'],)),
              'service':store.one('SELECT * FROM service_runs WHERE controller=?',(controller,)),
              'attempts':store.rows('SELECT * FROM attempts WHERE controller=? ORDER BY id',(controller,)),
              'contexts':store.rows('SELECT * FROM review_contexts WHERE collector=? ORDER BY component',(controller,)),
              'jobs':store.rows('SELECT * FROM jobs WHERE controller=? ORDER BY id',(controller,))}
    return {'basis':digest(material),'material':material,
            'meaning':'saved custody only, never evidence of original END or child inactivity'}


def predecessor_authority(store,actor,current,original):
    old=store.one('SELECT * FROM processing_capabilities WHERE id=?',(original,))
    if not old or actor!=current['issuer'] or old['issuer']!=actor:
        raise Refusal('genuine same Work issuer owns the explicit predecessor recovery')
    selected=json.loads(old['selection'])
    if selected['basis']['configuration']!=digest(store.config) or original!=current['id'] and old['revoked'] is None:
        raise Refusal('original source configuration or revocation changed; never reactivate old authority')


def apply(store, actor, controller, receipt):
    fields={'basis','activity','actual_END','evidence','remaining_holds','custodians'}
    if not isinstance(receipt,dict) or set(receipt)!=fields:
        raise Refusal('exact informed recovery/current source/original uncertainty and custodians required')
    if receipt['activity'] not in {'parent-collected','unavailable'}:
        raise Refusal('no inferred original completion')
    if ((receipt['activity']=='parent-collected' and type(receipt['actual_END']) is not int)
            or receipt['activity']=='unavailable' and receipt['actual_END'] is not None):
        raise Refusal('actual original parent END or explicit unavailable/null required')
    required_text(receipt['evidence'],'actual death/unavailability or parent collection evidence')
    if not isinstance(receipt['remaining_holds'],list) or not receipt['remaining_holds'] or not isinstance(receipt['custodians'],dict) or not receipt['custodians']:
        raise Refusal('unknown original activity/effects remain explicitly owned, never empty-cleared')
    for key,value in receipt['custodians'].items():
        required_text(key,'original custody subject'); required_text(value,'actual remaining custodian')
    fd=os.open(store.home/'service.lock',os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
    try:
        try: fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise Refusal('original cooperative service still owns its lock; reconnect to it') from exc
        with store.tx():
            cap,_=store.processing.current()
            current=basis(store,controller)
            predecessor_authority(store,actor,cap,current['material']['run']['capability'])
            if receipt['basis']!=current['basis']:
                raise Refusal('actual current Work/unchanged original capability/basis required')
            if current['material']['run']['state']!='owned':
                raise Refusal('original already disposed; never replay recovery')
            subjects={a['id'] for a in current['material']['attempts'] if a['collected'] is None}
            subjects|={c['component'] for c in current['material']['contexts'] if c['state']!='closed'}
            if not subjects<=set(receipt['custodians']):
                raise Refusal('every uncollected original and context needs its real remaining custodian')
            store.budget(None,len(encode(current).encode())+len(encode(receipt).encode())+2048)
            store.db.execute('INSERT INTO service_recoveries VALUES(?,?,?,?,?,?)',
                             (controller,cap['id'],actor,encode(current),encode(receipt),store.clock()))
            store.db.execute("UPDATE processing_runs SET state='informed-recovery-originals-held' WHERE controller=?",(controller,))
            store.db.execute("UPDATE service_runs SET state='unavailable-originals-held' WHERE controller=?",(controller,))
            store.db.execute("UPDATE review_contexts SET state='interrupted' WHERE collector=? AND state!='closed'",(controller,))
            # No attempt/job/effect/lease/capacity is released. Disjoint fresh
            # work uses its own original collector, not the predecessor's name.
    finally: os.close(fd)
    return {'originals':current,'disposition':receipt,'same_session_continuity':False,
            'next':'new original service on SAME capability/journal; conflicting predecessors stay held'}


def review_basis(store,key):
    context=store.one('SELECT * FROM review_contexts WHERE component=?',(key,))
    if not context:
        raise Refusal('exact original review context required')
    calls=store.rows('SELECT * FROM review_calls WHERE component=? ORDER BY rowid',(key,))
    return {'basis':digest({'context':context,'calls':calls}),'context':context,'calls':calls}


def outstanding_review_call(store,call,context):
    attempt=store.one('SELECT * FROM attempts WHERE id=?',(call['attempt'],))
    # Prepared alone proves no refusal: collection of affirmative no-start is
    # required. A possible launch, missing attempt or future state stays held.
    no_start=(call['state']=='prepared' and attempt and attempt['begin'] is None
              and attempt['state']=='not-started' and attempt['collected'] is not None
              and json.loads(attempt['detail']).get('known_not_started') is True)
    if no_start:
        return False
    # Review history collection precedes the outer caller's collection, and a
    # collected input can still own an unclosed native context/close intent.
    settled=(call['state']=='collected' and context['state']=='closed' and attempt
             and attempt['collected'] is not None and attempt['ended'] is not None
             and type(attempt['exit']) is int)
    return not settled


def recover_review(store,actor,key,receipt):
    """An owner-confirmed inactive predecessor permits a NEW encounter, with history.

    Unknown activity is recordable but cannot release this same-context fence.
    Actual provider/native close remains its original owner's separate duty.
    """
    fields={'basis','activity','evidence','custodian','remaining_holds','history_hash'}
    if not isinstance(receipt,dict) or set(receipt)!=fields or receipt['activity'] not in {'inactive','unknown'}:
        raise Refusal('exact original activity/history/custodian disposition required')
    for field in ('evidence','custodian','history_hash'):
        required_text(receipt[field],'actual review recovery '+field)
    if not isinstance(receipt['remaining_holds'],list):
        raise Refusal('explicit remaining obligations required')
    with store.tx():
        current=review_basis(store,key); context=current['context']
        cap,_=store.processing.current()
        predecessor_authority(store,actor,cap,context['capability'])
        if receipt['basis']!=current['basis']:
            raise Refusal('actual Work and exact current predecessor required')
        if receipt['history_hash']!=context['history_hash']:
            raise Refusal('interrupted history requires exact original reconciliation first')
        if context['collector']==store.controller and context['state'] in {'opening','live'}:
            raise Refusal('reconnect/close actual idle original, never replace it while owned')
        if any(outstanding_review_call(store,call,context) for call in current['calls']):
            # Owner evidence settles activity only, not caller END, processing or
            # unknown effects. Keep every call and raw return in this snapshot.
            if not receipt['remaining_holds']:
                raise Refusal('uncollected inputs retain explicit caller/native/effect custody')
        identity=digest({'original':current,'disposition':receipt})
        store.budget(None,len(encode(current).encode())+len(encode(receipt).encode())+2048)
        store.db.execute('INSERT INTO review_predecessors VALUES(?,?,?,?,?,?,?)',
                         (identity,key,encode(context),encode(current['calls']),receipt['activity'],encode(receipt),store.clock()))
        if receipt['activity']=='inactive':
            # Calls stay immutable; subsequent execution has a new actual root.
            store.db.execute('DELETE FROM review_contexts WHERE component=?',(key,))
            for call in current['calls']:
                attempt=store.one('SELECT job FROM attempts WHERE id=?',(call['attempt'],))
                if attempt and attempt['job']:
                    store.db.execute("UPDATE jobs SET recovery_state='source-inactive-custody-held' WHERE id=?",(attempt['job'],))
                store.db.execute("UPDATE branch_turns SET state='inactive-custody-held',receipt=? WHERE id=? AND writer IS NULL",(encode(receipt),call['attempt']))
            store.db.execute("UPDATE branch_contexts SET state='unavailable',evidence=? WHERE kind='review' AND address=?",(encode(receipt),context['run']))
        else:
            store.db.execute("UPDATE review_contexts SET state='interrupted' WHERE component=?",(key,))
    return {'predecessor':identity,'same_session_continuity':False,'successor_admissible':receipt['activity']=='inactive',
            'originals_and_obligations':current,'remaining_holds':receipt['remaining_holds']}
