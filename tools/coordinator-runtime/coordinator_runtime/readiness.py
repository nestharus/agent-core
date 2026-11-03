"""Local producer readiness, resolved history and downstream duties stay distinct.

Evidence links qualify a producer's resolution claim; they do not independently
prove its semantic explanation, review acceptance or absence of other defects.
"""
import json
from pathlib import Path

from .contracts import Refusal, digest, required_text

INSTRUCTIONS = '''For this staged file task include completion={version:1,local:"ready"|"blocked",
failures:[{index,status:"resolved"|"unresolved",evidence:[{path,sha256}],verification_items:[ID]}],
unknowns:[{index,status:"deferred"|"boundary"|"unresolved",owner,duty,reason}],
tools:[{id,status:"resolved"|"expected",reason,evidence:[{path,sha256}],verification_items:[ID]}]}.
Cover every original failures/unknowns index once; retain those arrays and their full history.
ready means ALL current local construction and verification obligations are satisfied.
Actual local blockers stay unresolved, even if semantic=DONE. Standard pending controller
publication/artifact-custody/effect-reconciliation/delivery duties can be deferred to owner=controller.
Review/acceptance not established by this local task may be status=boundary, owner=outside-workflow;
this does not waive necessary handoffs. Other deferred duties need a necessary handoff to that
actual allowlisted role. For resolved history, bind exact conserved OWN report hashes and actual
successful verification tool IDs; account each actual nonzero tool item explicitly. Never infer
resolution from an unrelated later zero. If IDs are unavailable, retain the claim for one bounded
same-owned-idle clarification. Do not falsely erase history or invent successful checks.'''


def needs_clarification(answer, items):
    if not isinstance(answer,dict) or answer.get('semantic')!='DONE':return False
    proof=answer.get('completion')
    if not isinstance(proof,dict):return True
    if set(proof)!={'version','local','failures','unknowns','tools'}:return True
    if not isinstance(proof.get('tools'),list):return True
    declared={r.get('id') for r in proof['tools'] if isinstance(r,dict) and isinstance(r.get('id'),str)}
    return any((i.get('exit_code') not in {None,0} or i.get('status')=='failed') and i['id'] not in declared for i in items)


def assess(store, attempt):
    answer=json.loads(attempt['result']) if attempt['result'] else {}
    proof=answer.get('completion')
    if not isinstance(proof,dict) or set(proof)!={'version','local','failures','unknowns','tools'} or type(proof['version']) is not int or proof['version']!=1:
        raise Refusal('explicit version1 local completion assessment required; originals retained')
    if answer.get('semantic')!='DONE' or proof['local']!='ready':raise Refusal('current local work is not ready')
    detail=json.loads(attempt['detail'])
    if detail.get('readiness_clarification'):
        prior=detail['prior_turn_result']
        for key in ['failures','unknowns']:
            old=prior.get(key,[])
            if answer.get(key,[])[:len(old)]!=old:raise Refusal('clarification erased or rewrote original '+key)
    tools=detail.get('tool_completion',{})
    if not tools.get('complete'):raise Refusal('unsettled tool metadata blocks local readiness')
    zero={r['id'] for r in tools['items'] if r['type']=='commandExecution' and r['exit_code']==0 and r['completed_notification']}
    nonzero={r['id'] for r in tools['items'] if r['exit_code'] not in {None,0} or r['status']=='failed'}
    def evidence(row):
        refs=row.get('evidence');checks=row.get('verification_items')
        if (not isinstance(refs,list) or not 1<=len(refs)<=16 or not isinstance(checks,list)
                or not checks or not all(isinstance(c,str) and c in zero for c in checks)):
            raise Refusal('resolution needs explicit actual successful verification IDs and bounded report evidence')
        for ref in refs:
            if not isinstance(ref,dict) or set(ref)!={'path','sha256'} or not isinstance(ref['path'],str):
                raise Refusal('exact resolution artifact path/hash required')
            path=Path(ref['path'])
            if '..' in path.parts or not path.is_relative_to(store.home/'artifacts'/attempt['id']):
                raise Refusal('resolution evidence must belong to this producer attempt')
            held=store.one('SELECT sha256 FROM artifact_custody WHERE attempt=? AND path=?',(attempt['id'],str(path)))
            if not held or held['sha256']!=ref['sha256']:raise Refusal('resolution evidence is not the exact conserved artifact')
    def indexed(name):
        rows=proof[name]
        if not isinstance(rows,list) or len(rows)!=len(answer[name]):raise Refusal('completion must cover every original '+name+' entry')
        if any(not isinstance(r,dict) or type(r.get('index')) is not int for r in rows):raise Refusal('typed history index required')
        if sorted(r['index'] for r in rows)!=list(range(len(answer[name]))):raise Refusal('history indices duplicated or missing')
        return rows
    for row in indexed('failures'):
        if set(row)!={'index','status','evidence','verification_items'} or row['status']!='resolved':
            raise Refusal('genuine unresolved local failure remains held')
        evidence(row)
    job=store.job(attempt['job']);task=store.config['tasks'][job['task']]
    duties=[]
    for row in indexed('unknowns'):
        if set(row)!={'index','status','owner','duty','reason'}:raise Refusal('explicit unknown disposition required')
        required_text(row['reason'],'unknown classification rationale',4000)
        owner,duty=row['owner'],row['duty']
        if not all(isinstance(row[k],str) for k in ['status','owner','duty']):raise Refusal('typed unknown status/owner/duty required')
        if row['status']=='boundary' and owner=='outside-workflow' and duty in {'review','acceptance'}:
            actor=None  # Not claimed; not a new assignment or an acceptance waiver.
        elif row['status']=='deferred' and owner=='controller' and duty in {'publication','artifact-custody','effect-reconciliation','delivery'}:
            actor=store.config['actor']
        elif row['status']=='deferred' and isinstance(owner,str) and owner in task.get('allowed_handoffs',[]):
            if not any(h.get('recipient')==owner and h.get('required')=='settled' for h in answer.get('handoffs',[]) if isinstance(h,dict)):
                raise Refusal('necessary external duty lacks a durable admitted handoff')
            actor=store.config['delivery']['recipients'][owner]['session']
        else:raise Refusal('unresolved/unsupported local unknown remains held')
        duties.append({**row,'actual_owner':actor})
    rows=proof['tools']
    if (not isinstance(rows,list) or any(not isinstance(r,dict) or not isinstance(r.get('id'),str) for r in rows)
            or len(rows)!=len(nonzero) or {r['id'] for r in rows}!=nonzero):
        raise Refusal('every nonzero tool item needs its own explicit disposition')
    for row in rows:
        if set(row)!={'id','status','reason','evidence','verification_items'} or not isinstance(row['status'],str) or row['status'] not in {'resolved','expected'}:
            raise Refusal('typed nonzero tool disposition required')
        required_text(row['reason'],'tool resolution rationale',4000);evidence(row)
    return {'version':1,'local':'ready','producer':attempt['session'],'result_hash':digest(answer),
            'original_failures':answer['failures'],'original_unknowns':answer['unknowns'],
            'resolved_history':proof['failures'],'tool_dispositions':rows,'subsequent_duties':duties,
            'qualification':'producer-attested local readiness/resolution with actual tool and conserved-byte links; not independent semantic verification or downstream acceptance'}
