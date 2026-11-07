"""Actual-owner requests and explicit collected-closure continuity, never a replay CLI."""

import json

from .contracts import LUNA, Refusal, canonical_uuid, digest, encode, required_text
from . import windows, local_integration

SCHEMA = """
CREATE TABLE IF NOT EXISTS recovery_requests(
 id TEXT PRIMARY KEY,job TEXT NOT NULL,attempt TEXT NOT NULL,actor TEXT NOT NULL,
 receipt TEXT NOT NULL,state TEXT NOT NULL,created REAL NOT NULL,result TEXT);
CREATE TABLE IF NOT EXISTS recovery_dispositions(
 diagnosis TEXT PRIMARY KEY,job TEXT NOT NULL,attempt TEXT NOT NULL,
 reason TEXT NOT NULL,observed_by TEXT NOT NULL,created REAL NOT NULL);
"""


class RecoveryJournal:
    def request_recovery(self,job,token,attempt,actor,receipt,*,publication_board=None):
        """Queue one exact, bounded owner decision; launch/collection stay outside."""
        with self.tx():
            self.require_execution_open(job)
            row=self.job(job,token)
            if isinstance(receipt, dict) and receipt.get('mode') == 'remaining-work':
                local_integration.current_sources(self, row)
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
            keys={'mode','reason','evidence','remaining'}
            reuse=isinstance(receipt,dict) and receipt.get('mode')=='use-diagnosis'
            expected=keys|{'diagnosis','selection'} if reuse else keys
            if reuse and 'collector_continuity' in receipt:expected|={'collector_continuity'}
            if reuse and 'publication_remainder' in receipt:expected|={'publication_remainder'}
            if not isinstance(receipt,dict) or set(receipt)!=expected:
                raise Refusal('recovery receipt needs mode/reason/evidence/remaining')
            mode=receipt['mode']
            if mode not in {'redispose','remaining-work','defer','use-diagnosis'}:raise Refusal('unknown recovery mode')
            required_text(receipt['reason'],'owner recovery reason',4000)
            if not isinstance(receipt['evidence'],list) or not receipt['evidence']:
                raise Refusal('actual owner recovery evidence required')
            for evidence in receipt['evidence']:required_text(evidence,'owner evidence',4000)
            if mode=='remaining-work':
                required_text(receipt['remaining'],'bounded remaining target and why',16000)
                self.remaining_work_fence(row,old)
            elif receipt['remaining'] is not None:
                raise Refusal('only remaining-work states a new target; other modes require remaining:null')
            if len(encode(receipt).encode())>self.config['limits']['max_result_bytes']:
                raise Refusal('owner recovery receipt exceeds the admitted result bound')
            key=digest({'job':job,'attempt':attempt,'actor':actor,'receipt':receipt})
            prior=self.one('SELECT * FROM recovery_requests WHERE id=?',(key,))
            if prior:return prior
            if self.one("SELECT id FROM recovery_requests WHERE job=? AND state='pending'",(job,)):
                raise Refusal('one existing owner request is pending for this job')
            count=self.db.execute('SELECT COUNT(*) FROM recovery_requests WHERE job=?',(job,)).fetchone()[0]
            if not self.config.get('window_service') and count>=self.config['limits'].get('max_owner_corrections',4):
                raise Refusal('bounded owner recovery requests exhausted; original duties retained')
            windows.charge(self, 'decisions')
            witness=self.retained_diagnosis_witness(row,receipt,publication_board=publication_board) if reuse else None
            if reuse and 'collector_continuity' in receipt:self.validate_collector_continuity(row,receipt['collector_continuity'])
            self.budget(None,len(encode(receipt).encode())+1024)
            self.db.execute('INSERT INTO recovery_requests VALUES(?,?,?,?,?,\'pending\',?,?)',
                            (key,job,attempt,actor,encode(receipt),self.clock(),encode({'retained_diagnosis':witness}) if reuse else None))
        return self.one('SELECT * FROM recovery_requests WHERE id=?',(key,))

    def remaining_work_fence(self,row,old):
        self.remaining_work_conditions(row,old)
        self.require_recoverable_hold(row,old)

    def remaining_work_conditions(self,row,old):
        if old['ended'] is None or old['collected'] is None or row['effects'] not in {'none','reconciled'}:
            raise Refusal('actual collected end and reconciled effects required for remaining work')
        if self.one("SELECT target FROM file_publications WHERE attempt=? AND state!='published'",(old['id'],)):
            raise Refusal('unresolved publication intent cannot be bypassed by remaining work')
        if not json.loads(old['detail']).get('resume_disposition'):
            raise Refusal('same-session continuation disposition must remain explicit')
        if self.enrollment(row['role'])['legacy_hold'] or any(
                self.one('SELECT hold FROM events WHERE id=?',(m['event'],))['hold']
                for m in json.loads(row['members'])):
            raise Refusal('source/legacy holds remain binding for remaining work')

    def require_recoverable_hold(self,row,old):
        if not row['hold_reason']:return
        error=self.one("SELECT detail FROM operational_errors WHERE subject=? AND active=1 AND kind='task-disposition-error'",(row['id'],))
        if row['hold_reason']!=old['error'] and (not error or json.loads(error['detail']).get('error')!=row['hold_reason']):
            raise Refusal('unrelated job hold remains binding; recovery cannot discard it')

    def consume_recovery_request(self,request,*,dispatcher_continuity=False,publication_board=None):
        """Lawful disposition collector; only dispatcher may consume explicit continuity."""
        with self.tx():
            current=self.one('SELECT * FROM recovery_requests WHERE id=?',(request,))
            if not current or current['state']!='pending':return None
            self.require_execution_open(current['job'])
            row=self.job(current['job'])
            receipt=json.loads(current['receipt'])
            if receipt.get('mode') == 'remaining-work':
                local_integration.current_sources(self, row)
            old=self.attempt(current['attempt'])
            self.require_active_sources(job=row['id'])
            continuity=receipt['mode']=='use-diagnosis' and 'collector_continuity' in receipt
            if not self.owns_disposition(row,old) and not (continuity and dispatcher_continuity):
                raise Refusal('request awaits actual original collector; no custody transfer')
            if row['active_attempt']!=old['id'] or row['state']!='held':
                raise Refusal('request stale; no replacement or replay')
            if receipt['mode']=='use-diagnosis':
                successor=self._handoff(row['id'],receipt['diagnosis'],retained_request=current,
                                        dispatcher_continuity=dispatcher_continuity,publication_board=publication_board)
                transfer=json.loads(self.attempt(successor)['detail']).get('collector_continuity')
                self.db.execute("UPDATE recovery_requests SET state='consumed',result=? WHERE id=?",
                    (encode({'collector':self.controller,'at':self.clock(),'prior_job':row,
                             'retained_diagnosis':json.loads(current['result'])['retained_diagnosis'],'successor':successor,
                             'collector_continuity':transfer,
                             'meaning':'one remaining attempt allocated in same job; no diagnosis/model start/publication/acceptance claim'}),request))
                return {**current,'receipt':receipt,'successor':successor}
            if row['recovery_state'] in {'claimed','diagnosing'}:
                diag=self.current_diagnosis(row)
                self.retain_recovery_disposition(row,diag,'Actual owner request selects a new disposition of the collected diagnosis; no replay or effect waiver')
                row=self.job(row['id'])
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

    def validate_collector_continuity(self,row,continuity):
        keys={'scope','from_controller','service_actor','service_end','service_collected','evidence'}
        if not isinstance(continuity,dict) or set(continuity)!=keys:
            raise Refusal('complete owner-selected collector continuity evidence required')
        canonical_uuid(continuity['from_controller']);canonical_uuid(continuity['service_actor'])
        if (continuity['scope']!='closure-only-after-owned-restart' or continuity['from_controller']!=row['controller']
                or continuity['service_actor']!=self.config['actor'] or type(continuity['service_end']) is not int
                or continuity['service_collected'] is not True):
            raise Refusal('exact prior job collector/service actor and actual owned service END/collection required; no identity borrowing')
        evidence=continuity['evidence']
        if not isinstance(evidence,list) or not 1<=len(evidence)<=16:raise Refusal('bounded actual owned restart/collection evidence required')
        for item in evidence:required_text(item,'owned restart evidence',2000)

    def transfer_retained_closure(self,row,old,request):
        """Called only in the dispatcher's allocation transaction, after witness checks."""
        if not self.db.in_transaction:raise Refusal('collector continuity requires owned write transaction')
        continuity=json.loads(request['receipt'])['collector_continuity']
        self.validate_collector_continuity(row,continuity)
        if self.controller==row['controller']:raise Refusal('owned restart requires the dispatcher own distinct fresh controller identity')
        if self.one('SELECT id FROM attempts WHERE job=? AND (ended IS NULL OR collected IS NULL OR exit IS NULL)',(row['id'],)):
            raise Refusal('live/unknown related attempt retains its actual collector; no process adoption')
        if self.config['tasks'][row['task']]['effects']=='owner-reconcile' and row['effects']!='reconciled':
            raise Refusal('actual effect owner reconciliation required for closure transfer')
        previous=json.loads(row['collection_handoff']) if row['collection_handoff'] else {}
        if row['controller']!=old['controller'] and not (
                previous.get('to_controller')==row['controller'] and previous.get('original_collector')==old['controller']
                and previous.get('original_attempt')==old['id'] and previous.get('actual_exit')==old['exit']
                and previous.get('actual_collected_at')==old['collected']):
            raise Refusal('prior closure chain does not prove original task/collector/END; no manufactured history')
        handoff={'from_controller':row['controller'],'to_controller':self.controller,'original_collector':old['controller'],
            'original_attempt':old['id'],'actual_exit':old['exit'],'actual_collected_at':old['collected'],
            'prior_handoff':row['collection_handoff'],'request':request['id'],'owner':request['actor'],
            'service_actor':self.config['actor'],'owned_restart':continuity,
            'authority':'explicit actual-owner closure/disposition continuity only; no process adoption', 'at':self.clock()}
        self.db.execute('UPDATE jobs SET controller=?,collection_handoff=? WHERE id=?',
                        (self.controller,encode(handoff),row['id']))
        return handoff

    def retained_diagnosis_witness(self,row,receipt,*,request=None,publication_board=None):
        """Reaffirm qualified same-purpose evidence, not a fresh diagnosis or forced state."""
        if row['state']!='held' or row['recovery_state']!='awaiting-disposition':
            raise Refusal('retained diagnosis use requires the exact held awaiting-disposition job; defer/successor/current recovery remains binding')
        old=self.attempt(row['active_attempt'])
        self.require_active_sources(job=row['id'])
        if 'publication_remainder' in receipt:self.remaining_work_conditions(row,old)
        else:self.remaining_work_fence(row,old)
        for field in ['diagnosis','selection']:required_text(receipt[field],'exact retained '+field,128)
        diag=self.current_diagnosis(row)
        if not diag or diag['id']!=receipt['diagnosis'] or diag.get('legacy_lineage'):
            raise Refusal('requested diagnosis is not the current exact explicit diagnosis; newer/pending or ambiguous evidence remains binding')
        detail=json.loads(diag['detail'])
        if (diag['state']!='collected' or diag['ended'] is None or diag['collected'] is None
                or type(diag['exit']) is not int or diag['exit']!=0 or diag['capture']!='complete' or diag['error']
                or json.loads(diag['binding'])!=LUNA or detail.get('binding_readback')!=LUNA
                or detail.get('root_identity_observed') is not True or diag['controller']!=row['recovery_owner']):
            raise Refusal('retained diagnosis needs actual collected zero/complete/error-free bound Luna LOW identity and original recovery collector; no semantic DONE inference')
        if self.one('SELECT diagnosis FROM recovery_dispositions WHERE diagnosis=?',(diag['id'],)):
            raise Refusal('current diagnosis already has an owned disposition/question; do not override it')
        selection=self.owner_remaining_selection(row['id'],old['id'])
        if (not selection or selection['id']!=receipt['selection'] or detail.get('owner_selection')!=selection['id']
                or selection['actor']!=self.enrollment(row['role'])['owner']):
            raise Refusal('exact consumed authentic remaining-work selection required; no new purpose inferred')
        choice_order=self.one('SELECT rowid AS ordinal FROM recovery_requests WHERE id=?',(selection['id'],))['ordinal']
        newer=self.one('SELECT id FROM recovery_requests WHERE job=? AND attempt=? AND rowid>? AND id!=?',
                       (row['id'],old['id'],choice_order,request or ''))
        if newer:raise Refusal('newer owner choice '+newer['id']+' remains binding; retained selection is not current')
        choice=self.diagnosis_choice(row,diag)  # Preserves @owner, profile, target/WHY and authentic selection checks.
        publication=None
        if 'publication_remainder' in receipt:
            from .publication import remainder_basis
            publication=remainder_basis(self,row,old,choice,selection,publication_board)
            if receipt['publication_remainder']!=publication:
                raise Refusal('publication remainder basis changed or incomplete; owner must qualify current purpose/grant/source/peers')
        fields=('id','job','kind','controller','profile','binding','state','ended','exit','collected','capture','error','semantic','result')
        identity={k:detail.get(k) for k in ['prior_task_attempt','owner_selection','binding_readback','root_identity_observed']}
        witness={'diagnosis':diag['id'],'selection':selection['id'],'prior_task':old['id'],
                'diagnosis_hash':digest({**{k:diag[k] for k in fields},'identity':identity}),
                'original_task_hash':digest({k:old[k] for k in ['id','job','controller','ended','exit','collected','semantic','capture','error','result']}),
                'closure_hash':digest(row['collection_handoff']),
                'reservation_hash':digest({k:row[k] for k in ['token','members','role','phase','task','package']}),
                'selection_hash':digest({k:selection[k] for k in ['id','job','attempt','actor','receipt','state','created']}),
                'basis':'actual owner reaffirmation of retained qualified same-purpose diagnosis; no source/history/END rewrite'}
        if publication is not None:witness['publication_remainder']=publication
        return witness

    def publication_remainder_basis(self,job,token,attempt,diagnosis,selection,board):
        """Read-only candidate operands. The genuine owner still judges purpose/WHY."""
        from .publication import remainder_basis
        with self.tx():
            row=self.job(job,token)
            if row['active_attempt']!=attempt:raise Refusal('publication basis needs exact active original')
            diag=self.current_diagnosis(row)
            if not diag or diag['id']!=diagnosis:raise Refusal('publication basis needs exact retained diagnosis')
            selected=self.owner_remaining_selection(job,attempt)
            if not selected or selected['id']!=selection:raise Refusal('publication basis needs exact consumed selection')
            basis=remainder_basis(self,row,self.attempt(attempt),self.diagnosis_choice(row,diag),selected,board)
            self.retained_diagnosis_witness(row,{'diagnosis':diagnosis,'selection':selection,'publication_remainder':basis},publication_board=board)
            return basis

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
        self.require_execution_open(job['id'])
        current=self.job(job['id'])
        if current['active_attempt']!=job['active_attempt'] or current['recovery_state']!='diagnosing':
            raise Refusal('stale diagnosis cannot change a successor recovery reservation')
        if not diag or diag['collected'] is None or (diag['ended'] is None and diag['state']!='not-started'):
            raise Refusal('unknown diagnosis remains with its actual collector')
        if not self.owns_disposition(current,self.attempt(job['active_attempt'])):
            raise Refusal('recovery disposition remains with the actual original collector; no custody transfer')
        selected=self.current_diagnosis(current)
        if not selected or selected['id']!=diag['id']:
            raise Refusal('stale diagnosis cannot dispose newer current/pending diagnosis')
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
        self.require_execution_open(job['id'])
        if job['recovery_state']!='diagnosing':return
        if not self.owns_disposition(job,self.attempt(job['active_attempt'])):return
        diag=self.current_diagnosis(job)
        if not diag or diag['collected'] is None:return
        try:self.diagnosis_choice(job,diag)
        except Refusal as exc:self.retain_recovery_disposition(job,diag,exc)

    def recheck_artifact_capture(self,attempt):
        """After full inventory, correct only its derived gap, conserving history."""
        with self.tx():
            self.require_attempt_execution_open(attempt)
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
            self.require_execution_open(job)
            row=self.job(job)
            error=self.one("SELECT * FROM operational_errors WHERE subject=? AND active=1 AND kind='task-disposition-error'",(job,))
            if error and json.loads(error['detail']).get('error')==row['hold_reason']:
                self.db.execute('UPDATE jobs SET hold_reason=NULL WHERE id=?',(job,))
