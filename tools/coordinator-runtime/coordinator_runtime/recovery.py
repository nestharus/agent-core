"""Actual-owner requests, consumed by the existing collector, never a replay CLI."""

import json

from .contracts import Refusal, digest, encode, required_text

SCHEMA = """
CREATE TABLE IF NOT EXISTS recovery_requests(
 id TEXT PRIMARY KEY,job TEXT NOT NULL,attempt TEXT NOT NULL,actor TEXT NOT NULL,
 receipt TEXT NOT NULL,state TEXT NOT NULL,created REAL NOT NULL,result TEXT);
"""


class RecoveryJournal:
    def request_recovery(self,job,token,attempt,actor,receipt):
        """Queue one exact, bounded owner decision; launch/collection stay outside."""
        with self.tx():
            row=self.job(job,token)
            old=self.attempt(attempt)
            self.require_active_sources(job=job)
            if actor!=self.enrollment(row['role'])['owner']:
                raise Refusal('recovery request belongs to the actual enrolled role owner')
            if row['active_attempt']!=attempt or row['state']!='held':
                raise Refusal('recovery request needs the exact active held attempt')
            if old['ended'] is None or old['collected'] is None:
                raise Refusal('unknown/live original remains with its actual collector')
            if row['recovery_state'] in {'claimed','diagnosing'}:
                raise Refusal('existing recovery must be collected; no competing request')
            if not isinstance(receipt,dict) or set(receipt)!={'mode','reason','evidence','remaining'}:
                raise Refusal('recovery receipt needs mode/reason/evidence/remaining')
            mode=receipt['mode']
            if mode not in {'redispose','remaining-work'}:raise Refusal('unknown recovery mode')
            required_text(receipt['reason'],'owner recovery reason',4000)
            if not isinstance(receipt['evidence'],list) or not receipt['evidence']:
                raise Refusal('actual owner recovery evidence required')
            for evidence in receipt['evidence']:required_text(evidence,'owner evidence',4000)
            if mode=='remaining-work':
                required_text(receipt['remaining'],'bounded remaining target and why',16000)
                self.remaining_work_fence(row,old)
            elif receipt['remaining'] is not None:
                raise Refusal('redispose retries the unchanged original, never new model work')
            key=digest({'job':job,'attempt':attempt,'actor':actor,'receipt':receipt})
            prior=self.one('SELECT * FROM recovery_requests WHERE id=?',(key,))
            if prior:return prior
            if self.one("SELECT id FROM recovery_requests WHERE job=? AND state='pending'",(job,)):
                raise Refusal('one existing owner request is pending for this job')
            count=self.db.execute('SELECT COUNT(*) FROM recovery_requests WHERE job=?',(job,)).fetchone()[0]
            if count>=self.config['limits'].get('max_owner_corrections',4):
                raise Refusal('bounded owner recovery requests exhausted; original duties retained')
            self.budget(None,len(encode(receipt).encode())+1024)
            self.db.execute('INSERT INTO recovery_requests VALUES(?,?,?,?,?,\'pending\',?,NULL)',
                            (key,job,attempt,actor,encode(receipt),self.clock()))
        return self.one('SELECT * FROM recovery_requests WHERE id=?',(key,))

    def remaining_work_fence(self,row,old):
        if old['ended'] is None or old['collected'] is None or row['effects'] not in {'none','reconciled'}:
            raise Refusal('actual collected end and reconciled effects required for remaining work')
        if self.one("SELECT target FROM file_publications WHERE attempt=? AND state!='published'",(old['id'],)):
            raise Refusal('unresolved publication intent cannot be bypassed by remaining work')
        if not json.loads(old['detail']).get('resume_disposition'):
            raise Refusal('same-session continuation disposition must remain explicit')
        self.require_recoverable_hold(row,old)
        if self.enrollment(row['role'])['legacy_hold'] or any(
                self.one('SELECT hold FROM events WHERE id=?',(m['event'],))['hold']
                for m in json.loads(row['members'])):
            raise Refusal('source/legacy holds remain binding for remaining work')

    def require_recoverable_hold(self,row,old):
        if not row['hold_reason']:return
        error=self.one("SELECT detail FROM operational_errors WHERE subject=? AND active=1 AND kind='task-disposition-error'",(row['id'],))
        if row['hold_reason']!=old['error'] and (not error or json.loads(error['detail']).get('error')!=row['hold_reason']):
            raise Refusal('unrelated job hold remains binding; recovery cannot discard it')

    def consume_recovery_request(self,request):
        """Only the current lawful reservation collector can act on a request."""
        with self.tx():
            current=self.one('SELECT * FROM recovery_requests WHERE id=?',(request,))
            if not current or current['state']!='pending':return None
            row=self.job(current['job'])
            old=self.attempt(current['attempt'])
            self.require_active_sources(job=row['id'])
            if not self.owns_disposition(row,old):
                raise Refusal('request awaits actual original collector; no custody transfer')
            if row['active_attempt']!=old['id'] or row['state']!='held':
                raise Refusal('request stale; no replacement or replay')
            if row['recovery_state'] in {'claimed','diagnosing'}:
                raise Refusal('existing recovery must finish before consuming an owner request')
            receipt=json.loads(current['receipt'])
            if receipt['mode']=='remaining-work':
                self.remaining_work_fence(row,old)
                self.db.execute("UPDATE jobs SET recovery_owner=?,recovery_state='claimed',recovery_count=recovery_count+1 WHERE id=?",
                                (self.controller,row['id']))
            self.db.execute("UPDATE recovery_requests SET state='consumed',result=? WHERE id=?",
                            (encode({'collector':self.controller,'at':self.clock(),
                                     'prior_job':row,'prior_capture':old['capture'],'prior_error':old['error']}),request))
        return {**current,'receipt':receipt}

    def owner_remaining_selection(self,job,attempt):
        row=self.one("SELECT * FROM recovery_requests WHERE job=? AND attempt=? AND state='consumed' "
                     "AND json_extract(receipt,'$.mode')='remaining-work' ORDER BY created DESC LIMIT 1",(job,attempt))
        return row

    def recheck_artifact_capture(self,attempt):
        """After full inventory, correct only its derived gap, conserving history."""
        with self.tx():
            old=self.attempt(attempt);detail=json.loads(old['detail'])
            if not self.owns_disposition(self.job(old['job']),old) or old['ended'] is None or old['collected'] is None:
                raise Refusal('artifact recheck belongs to the collected original owner')
            if old['capture']!='artifact-inventory-incomplete':return
            if detail.get('protocol_capture')!='complete':
                raise Refusal('artifact recheck cannot repair incomplete protocol/turn capture')
            detail['artifact_recheck']={'assessor':self.controller,'original_collector':old['controller'],'at':self.clock(),
                'prior_capture':old['capture'],'prior_error':old['error'],
                'prior_inventory_error':detail.get('artifact_inventory_error'),
                'basis':'all explicit leaves captured by current contract; original result/results row retained'}
            self.db.execute('UPDATE attempts SET capture=?,error=?,detail=? WHERE id=?',
                            (detail['protocol_capture'],detail.get('pre_inventory_error'),encode(detail),attempt))

    def owns_disposition(self,row,old):
        if row['controller']!=self.controller:return False
        if old['controller']==self.controller:return True
        handoff=json.loads(row['collection_handoff']) if row['collection_handoff'] else {}
        return (handoff.get('to_controller')==self.controller and handoff.get('original_collector')==old['controller']
                and handoff.get('original_attempt')==old['id'] and handoff.get('actual_exit')==old['exit']
                and handoff.get('actual_collected_at')==old['collected'])

    def retry_disposition_hold(self,job):
        """Re-examine our own recorded disposition error, preserving other holds."""
        with self.tx():
            row=self.job(job)
            error=self.one("SELECT * FROM operational_errors WHERE subject=? AND active=1 AND kind='task-disposition-error'",(job,))
            if error and json.loads(error['detail']).get('error')==row['hold_reason']:
                self.db.execute('UPDATE jobs SET hold_reason=NULL WHERE id=?',(job,))
