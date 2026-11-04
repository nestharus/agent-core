"""Actual-owner requests, consumed by the existing collector, never a replay CLI."""

import json

from .contracts import Refusal, digest, encode, required_text

SCHEMA = """
CREATE TABLE IF NOT EXISTS recovery_requests(
 id TEXT PRIMARY KEY,job TEXT NOT NULL,attempt TEXT NOT NULL,actor TEXT NOT NULL,
 receipt TEXT NOT NULL,state TEXT NOT NULL,created REAL NOT NULL,result TEXT);
CREATE TABLE IF NOT EXISTS recovery_dispositions(
 diagnosis TEXT PRIMARY KEY,job TEXT NOT NULL,attempt TEXT NOT NULL,
 reason TEXT NOT NULL,observed_by TEXT NOT NULL,created REAL NOT NULL);
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
            self.finish_invalid_diagnosis(row)
            row=self.job(job,token)
            if row['recovery_state'] in {'claimed','diagnosing'}:
                diag=self.current_diagnosis(row)
                if not diag or diag['collected'] is None or diag['ended'] is None or type(diag['exit']) is not int:
                    raise Refusal('existing recovery must be collected; exact current diagnosis/END evidence missing; actual collector retains custody')
            if not isinstance(receipt,dict) or set(receipt)!={'mode','reason','evidence','remaining'}:
                raise Refusal('recovery receipt needs mode/reason/evidence/remaining')
            mode=receipt['mode']
            if mode not in {'redispose','remaining-work','defer'}:raise Refusal('unknown recovery mode')
            required_text(receipt['reason'],'owner recovery reason',4000)
            if not isinstance(receipt['evidence'],list) or not receipt['evidence']:
                raise Refusal('actual owner recovery evidence required')
            for evidence in receipt['evidence']:required_text(evidence,'owner evidence',4000)
            if mode=='remaining-work':
                required_text(receipt['remaining'],'bounded remaining target and why',16000)
                self.remaining_work_fence(row,old)
            elif receipt['remaining'] is not None:
                raise Refusal('redispose/defer cannot authorize new model work')
            if len(encode(receipt).encode())>self.config['limits']['max_result_bytes']:
                raise Refusal('owner recovery receipt exceeds the admitted result bound')
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
                diag=self.current_diagnosis(row)
                self.retain_recovery_disposition(row,diag,'Actual owner request selects a new disposition of the collected diagnosis; no replay or effect waiver')
                row=self.job(row['id'])
            receipt=json.loads(current['receipt'])
            if receipt['mode']=='remaining-work':
                self.remaining_work_fence(row,old)
                self.db.execute("UPDATE jobs SET recovery_owner=?,recovery_state='claimed',recovery_count=recovery_count+1 WHERE id=?",
                                (self.controller,row['id']))
            elif receipt['mode']=='defer':
                self.db.execute("UPDATE jobs SET recovery_state='owner-deferred' WHERE id=?",(row['id'],))
            elif row['recovery_state']=='owner-deferred':
                self.db.execute("UPDATE jobs SET recovery_state='awaiting-disposition' WHERE id=?",(row['id'],))
            self.db.execute("UPDATE recovery_requests SET state='consumed',result=? WHERE id=?",
                            (encode({'collector':self.controller,'at':self.clock(),
                                     'prior_job':row,'prior_capture':old['capture'],'prior_error':old['error']}),request))
        return {**current,'receipt':receipt}

    def owner_remaining_selection(self,job,attempt):
        row=self.one("SELECT * FROM recovery_requests WHERE job=? AND attempt=? AND state='consumed' "
                     "AND json_extract(receipt,'$.mode')='remaining-work' ORDER BY created DESC,rowid DESC LIMIT 1",(job,attempt))
        return row

    def current_diagnosis(self,job):
        explicit=self.one("SELECT * FROM attempts WHERE job=? AND kind='diagnosis' "
                        "AND json_extract(detail,'$.prior_task_attempt')=? ORDER BY created DESC,rowid DESC LIMIT 1",
                        (job['id'],job['active_attempt']))
        if explicit:return explicit
        old=self.attempt(job['active_attempt'])
        candidates=self.rows("SELECT * FROM attempts WHERE job=? AND kind='diagnosis' "
            "AND json_extract(detail,'$.prior_task_attempt') IS NULL AND created>=? ORDER BY created,rowid",
            (job['id'],old['collected'] if old['collected'] is not None else old['created']))
        if not candidates:return None
        if len(candidates)!=1:
            raise Refusal('ambiguous legacy diagnosis lineage for task '+old['id']+': '+','.join(d['id'] for d in candidates)+'; actual collector must identify the exact retained diagnosis; no inferred closure')
        diag=candidates[0]
        lineage=self.legacy_diagnosis_lineage(job,diag)
        return {**diag,'legacy_lineage':lineage}  # Derived view only; original detail/history untouched.

    def legacy_diagnosis_lineage(self,job,diag):
        old=self.attempt(job['active_attempt'])
        if (diag['kind']!='diagnosis' or diag['job']!=job['id'] or old['kind']!='task' or old['job']!=job['id']
                or json.loads(diag['detail']).get('prior_task_attempt') is not None
                or diag['controller']!=old['controller'] or diag['controller']!=job['recovery_owner']
                or any(a['state']!='collected' or a['ended'] is None or a['collected'] is None or type(a['exit']) is not int for a in [old,diag])
                or not old['created']<=old['ended']<=old['collected']<=diag['created']<=diag['ended']<=diag['collected']
                or self.db.execute("SELECT COUNT(*) FROM attempts WHERE job=? AND kind='diagnosis' AND json_extract(detail,'$.prior_task_attempt') IS NULL AND created>=?",
                                   (job['id'],old['collected'])).fetchone()[0]!=1
                or self.one("SELECT id FROM attempts WHERE job=? AND kind='task' AND id!=? AND created>=?",
                            (job['id'],old['id'],old['created']))):
            raise Refusal('legacy diagnosis '+diag['id']+' cannot bind exact task '+old['id']+' and actual collected END/controller chronology; actual collector evidence/disposition required')
        return {'basis':'unique retained job/task/collector chronology; disposition only, no semantic/handoff success',
                'job':job['id'],'task':old['id'],'diagnosis':diag['id'],'collector':diag['controller'],
                'task_exit':old['exit'],'task_collected':old['collected'],'diagnosis_exit':diag['exit'],'diagnosis_collected':diag['collected']}

    def diagnosis_choice(self,job,diag):
        if diag and diag.get('legacy_lineage'):
            raise Refusal('legacy collected diagnosis recognized for actual owner disposition only; missing historical linkage/selection is not automatic replacement authority')
        if (not diag or diag['kind']!='diagnosis' or diag['job']!=job['id'] or
                json.loads(diag['detail']).get('prior_task_attempt')!=job['active_attempt'] or
                diag['exit']!=0 or diag['error'] or diag['collected'] is None or diag['capture']!='complete'):
            raise Refusal('actual matching successful Luna-low diagnosis required; no replacement')
        choice=json.loads(diag['result']) if diag['result'] else None
        if not isinstance(choice,dict) or set(choice)!={'profile','remaining','rationale'}:
            raise Refusal('explicit informed profile/remaining-work/rationale choice required')
        if choice['profile']=='@owner':
            required_text(choice['remaining'],'actual owner question',16000)
            required_text(choice['rationale'],'owner question rationale',16000)
            raise Refusal('diagnosis requests actual owner disposition: '+choice['remaining']+'; '+choice['rationale'])
        if not isinstance(choice['profile'],str) or choice['profile'] not in self.config['profiles']:
            raise Refusal('unusable profile handoff choice; actual owner disposition required')
        required_text(choice['remaining'],'diagnosed remaining work',16000)
        required_text(choice['rationale'],'diagnosis rationale',16000)
        selection=self.owner_remaining_selection(job['id'],job['active_attempt'])
        supplied=json.loads(diag['detail']).get('owner_selection')
        if (selection['id'] if selection else None)!=supplied:
            raise Refusal('diagnosis did not receive current authentic owner selection')
        return choice

    def retain_recovery_disposition(self,job,diag,reason):
        """Collected diagnosis is evidence for a next owner decision, never success."""
        current=self.job(job['id'])
        if current['active_attempt']!=job['active_attempt'] or current['recovery_state']!='diagnosing':
            raise Refusal('stale diagnosis cannot change a successor recovery reservation')
        if not diag or diag['collected'] is None or (diag['ended'] is None and diag['state']!='not-started'):
            raise Refusal('unknown diagnosis remains with its actual collector')
        if not self.owns_disposition(current,self.attempt(job['active_attempt'])):
            raise Refusal('recovery disposition remains with the actual original collector; no custody transfer')
        lineage=diag.get('legacy_lineage')
        if lineage:self.legacy_diagnosis_lineage(job,diag)
        elif json.loads(diag['detail']).get('prior_task_attempt')!=job['active_attempt']:
            raise Refusal('stale diagnosis cannot change current recovery disposition')
        self.db.execute('INSERT OR IGNORE INTO recovery_dispositions VALUES(?,?,?,?,?,?)',
                        (diag['id'],job['id'],job['active_attempt'],str(reason),self.controller,self.clock()))
        self.db.execute("UPDATE jobs SET recovery_state='awaiting-disposition' WHERE id=?",(job['id'],))
        payload={'job':job['id'],'attempt':job['active_attempt'],'reservation':job['token'],
            'reason':str(reason),'diagnosis':diag,'owner_remaining_selection':self.owner_remaining_selection(job['id'],job['active_attempt']),
            'diagnosis_lineage':lineage,
            'next':'Actual role owner: request-recovery redispose, remaining-work with target/WHY/evidence, or defer. No forced profile, replay or effect waiver.',
            'original_result':self.attempt(job['active_attempt'])['result'],
            'source_members':json.loads(job['members'])}
        self._outbox(job['role'],job['role'],'question',payload,job=job['id'],
                     key=digest({'recovery-disposition':diag['id']}))
        self.gate_result_delivery(job,diag,payload)

    def finish_invalid_diagnosis(self,job):
        """Also exposes the public next step for already-collected old bad diagnoses."""
        if job['recovery_state']!='diagnosing':return
        if not self.owns_disposition(job,self.attempt(job['active_attempt'])):return
        diag=self.current_diagnosis(job)
        if not diag or diag['collected'] is None:return
        try:self.diagnosis_choice(job,diag)
        except Refusal as exc:self.retain_recovery_disposition(job,diag,exc)

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
