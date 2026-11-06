"""Derived actual-owner input decisions; original sources and attempts are immutable."""

import json
from contextlib import nullcontext

from .contracts import Refusal, digest, encode, ident, required_text
from . import windows

SCHEMA = """
CREATE TABLE IF NOT EXISTS input_resolutions(
 event TEXT NOT NULL,version INTEGER NOT NULL,source_hash TEXT NOT NULL,actor TEXT NOT NULL,
 receipt TEXT NOT NULL,prior TEXT NOT NULL,created REAL NOT NULL,PRIMARY KEY(event,version));
"""
CONTROL_ROUTES={'@control','@unresolved','@coalesce'}


def input_routes(event, config=None):
    routes=list(event['allowed_tasks'])
    routes.append('@unresolved')
    if event['kind']=='board':routes.append('@control')
    selection=event.get('owner_resolution')
    if selection:
        mode=selection['receipt']['mode']
        routes=[selection['receipt']['task']] if mode=='route' else ['@coalesce' if mode=='coalesce' else '@control']
        routes.append('@unresolved')
    if config is not None and event.get('package') is None:
        # A null-package QA control has control routes, not runnable package
        # tasks. Keep those impossible choices out of the classifier's input
        # as well as refusing them at commit; never invent an admission.
        routes = [name for name in routes if name in CONTROL_ROUTES or name == '@delivery'
                  or not (config['tasks'][name]['role'] == 'QA'
                          or config['tasks'][name].get('require_package_scope'))]
    return list(dict.fromkeys(routes))


class InputJournal:
    def input_resolution(self,event,version=None):
        row=(self.one('SELECT * FROM input_resolutions WHERE event=? AND version=?',(event,version))
             if version else self.one('SELECT * FROM input_resolutions WHERE event=? ORDER BY version DESC LIMIT 1',(event,)))
        return {**row,'receipt':json.loads(row['receipt']),'prior':json.loads(row['prior'])} if row else None

    def routing_event(self,event):
        original=self.event(event)
        selection=self.input_resolution(event)
        if not selection:return original
        if digest(original)!=selection['source_hash']:raise Refusal('original input no longer matches selected source')
        derived = {**original,'original_package':original.get('package'),
                   'package':selection['receipt']['package'],'owner_resolution':selection}
        if 'integration_observation' in selection['prior']:
            from .local_integration import resolved_input
            derived['integration'] = resolved_input(self, original, selection)
        return derived

    def resolve_input(self,event,actor,receipt,*,processing_attempt=None,mapping_attempt=None):
        with (nullcontext() if self.db.in_transaction else self.tx()):
            if isinstance(receipt, dict) and 'integration' in receipt:
                held = self.one('SELECT hold FROM events WHERE id=?', (event,))
                if not held or held['hold']:
                    raise Refusal('unheld exact input required before mapping acquisition')
            row=self.one('SELECT * FROM events WHERE id=?',(event,))
            if not row:raise Refusal('exact existing input required')
            original=self.event(event)
            software = None
            frozen_mapping = None
            if mapping_attempt is not None:
                if processing_attempt is not None:
                    raise Refusal('metadata lookup and general control are separate delegations')
                from .metadata_lookup import proof
                software, frozen_mapping = proof(self, event, actor, mapping_attempt, receipt)
            if processing_attempt is not None and self.processing and actor == self.config['actor']:
                if 'integration' in receipt:
                    raise Refusal('general control is not software metadata delegation')
                software = self.processing.control_proof(event, processing_attempt, receipt)
            if actor!=self.enrollment(row['role'])['owner'] and not software:
                raise Refusal('input resolution belongs to its actual enrolled owner')
            keys={'source_hash','mode','task','package','related_event','related_job','reason','evidence','remaining_obligations'}
            if not isinstance(receipt,dict) or set(receipt)-{'integration'}!=keys:
                raise Refusal('input resolution needs source_hash/mode/task/package/related_event/related_job/reason/evidence/remaining_obligations')
            if any(receipt[k] is not None and not isinstance(receipt[k],str) for k in ['task','package','related_event','related_job']):
                raise Refusal('input identities must be text or null')
            if receipt['source_hash']!=row['hash']:raise Refusal('stale input source hash')
            required_text(receipt['reason'],'authentic input meaning and why',16000)
            for key in ['evidence','remaining_obligations']:
                if not isinstance(receipt[key],list) or len(receipt[key])>32 or key=='evidence' and not receipt[key]:
                    raise Refusal('bounded explicit input evidence/remaining obligations required')
                for item in receipt[key]:required_text(item,key,4000)
            if len(encode(receipt).encode())>self.config['limits']['max_result_bytes']:
                raise Refusal('input decision exceeds admitted result bound')
            previous=self.input_resolution(event)
            if previous and previous['receipt']==receipt:
                observation = previous['prior'].get('integration_observation')
                if observation is None:
                    return previous
                from .local_integration import mapping_binding
                if observation['binding'] == mapping_binding(self, receipt['task'], receipt['package']):
                    return previous
                # Same intent after a genuine binding change is a NEW observed
                # resolution, with fresh classification and all normal guards.
                # Never return a stale observation as successful remapping.
            if row['processed_at'] is not None:raise Refusal('processed original cannot be rerouted')
            queue=self.one('SELECT * FROM queue WHERE event=?',(event,))
            if queue and queue['job']:raise Refusal('already reserved/executed source cannot be replayed or rebound')
            current=self.attempt(row['classifier']) if row['classifier'] else None
            if current and current['collected'] is None:
                raise Refusal('existing unknown/live classifier remains with its actual collector')
            self.validate_input_selection(original,receipt)
            version=previous['version']+1 if previous else 1
            if not self.config.get('window_service') and version>self.config['limits'].get('max_owner_corrections',4):
                raise Refusal('bounded input decisions exhausted; owner obligations retained')
            windows.charge(self, 'decisions')
            prior={'state':row['state'],'classification':row['classification'],'classifier':row['classifier'],
                   'error':row['error'],'queue':queue,'ack':row['ack'],'ack_receipt':row['ack_receipt']}
            if 'integration' in receipt:
                from .local_integration import observe_input
                prior['integration_observation'] = (frozen_mapping if frozen_mapping is not None
                                                    else observe_input(self, original, receipt))
            if software:
                prior['software_processing'] = software
            self.budget(None,len(encode(receipt).encode())+len(encode(prior).encode())+1024)
            self.db.execute('INSERT INTO input_resolutions VALUES(?,?,?,?,?,?,?)',
                            (event,version,row['hash'],actor,encode(receipt),encode(prior),self.clock()))
            if receipt['mode']=='notification':
                # The actual classifier already selected @control, and the
                # collected worker read the entire authenticated notification.
                # Finish that queue only; preserve its ACK and every cause.
                self.db.execute("UPDATE queue SET state='done' WHERE event=?", (event,))
            else:
                # A derived task decision requires fresh classification.
                self.db.execute("UPDATE events SET state='received' WHERE id=?",(event,))
                if queue:self.db.execute("UPDATE queue SET state='owner-resolution-pending' WHERE event=?",(event,))
        return self.input_resolution(event)

    def validate_input_selection(self,original,receipt):
        mode=receipt['mode'];task=receipt['task'];package=receipt['package']
        if mode=='route':
            if task not in original['allowed_tasks']:raise Refusal('owner selection exceeds original configured task authority')
            if task=='@delivery':
                if original['kind']!='outgoing-response' or package!=original.get('package'):
                    raise Refusal('fixed delivery plan/package cannot be changed by owner resolution')
            else:
                selected=self.config['tasks'].get(task)
                if not selected:raise Refusal('actual configured task required')
                if package is not None and not self.one('SELECT package FROM admissions WHERE package=?',(package,)):
                    raise Refusal('package binding requires actual existing admission, never a guessed scope')
                if selected['role']=='QA' or selected.get('require_package_scope'):
                    required_text(package,'actual admitted execution package',128)
                    if not self.one('SELECT package FROM admissions WHERE package=?',(package,)):
                        raise Refusal('actual execution package admission required')
        elif mode=='notification':
            from .capacity import notification
            notice = notification(self, original)
            classified = self.one('SELECT classification,state FROM events WHERE id=?', (original['id'],))
            queue = self.one('SELECT task FROM queue WHERE event=?', (original['id'],))
            if (not classified or not classified['classification'] or classified['state']!='queued'
                    or not queue or queue['task']!='@control' or not notice or task is not None or package is not None
                    or receipt['remaining_obligations'] or notice['coverage_evidence'] not in receipt['evidence']):
                raise Refusal('notification receipt requires full authenticated occurrence coverage; no underlying settlement')
        elif mode=='control':
            if original['kind']!='board' or task is not None or package is not None:
                raise Refusal('processed control is board input only, without task or invented package')
        elif mode=='coalesce':
            if task is not None:raise Refusal('coalescence cannot select a new task')
            target=self.one('SELECT * FROM events WHERE id=?',(receipt['related_event'],))
            queue=self.one('SELECT * FROM queue WHERE event=?',(receipt['related_event'],))
            job=self.job(receipt['related_job'])
            if (not target or target['role']!=original['role'] or not queue or queue['job']!=job['id']
                    or job['role']!=original['role'] or job['package']!=package
                    or not any(m['event']==target['id'] for m in json.loads(job['members']))):
                raise Refusal('coalescence needs the exact same-role existing event/job/package and actual owner purpose evidence')
        else:raise Refusal('input mode must be route, control, notification or coalesce')
        if mode!='coalesce' and (receipt['related_event'] is not None or receipt['related_job'] is not None):
            raise Refusal('only coalescence names an existing responsibility')

    def queue_input_control(self,event,answer):
        selection=event.get('owner_resolution')
        settled=(answer['task']=='@control' and selection and selection['receipt']['mode']=='control'
                 and not selection['receipt']['remaining_obligations'])
        self.write_input_queue(event,answer,event['role'],'control','done' if settled else 'awaiting-owner')
        if settled or answer['task']=='@coalesce':return
        if self.processing and self.processing.event(self.event(event['id'])):
            return  # The actual delegated control worker owns this input; no recursive question copies.
        payload={'event':event['id'],'source':self.event(event['id']),'classification':answer,
                 'owner_resolution':selection,'reason':'Actual input control/unresolved meaning requires its genuine coordinator.',
                 'next':'Read input-show; resolve-input with actual meaning/evidence, or retain unresolved. No task/effect/acceptance inferred.'}
        self._outbox(event['role'],event['role'],'question',payload,event=event['id'],
                     key=digest({'input-control':event['id'],'classifier':self.one('SELECT classifier FROM events WHERE id=?',(event['id'],))['classifier']}))

    def write_input_queue(self,event,answer,role,phase,state):
        self.db.execute('INSERT INTO queue VALUES(?,?,?,?,?,?,?,NULL) ON CONFLICT(event) DO UPDATE SET '
                        'role=excluded.role,phase=excluded.phase,task=excluded.task,package=excluded.package,state=excluded.state',
                        (ident(),event['id'],role,phase,answer['task'],answer['package'],state))

    def complete_input_controls(self):
        for queue in self.rows("SELECT * FROM queue WHERE phase='control' AND task='@coalesce' AND state!='done'"):
            selection=self.input_resolution(queue['event'])
            if not selection:continue
            target=self.one('SELECT * FROM events WHERE id=?',(selection['receipt']['related_event'],))
            job=self.job(selection['receipt']['related_job'])
            if job['state']=='closed' and target['processed_at'] is not None:
                self.db.execute("UPDATE queue SET state='done' WHERE id=?",(queue['id'],))

    def owner_controls(self,role,limit=100,after=None):
        self.enrollment(role)
        cursor=self.one('SELECT id,role,received FROM events WHERE id=?',(after,)) if after else None
        if after and (not cursor or cursor['role']!=role):raise Refusal('owner control cursor must identify this same role source')
        rows=self.rows("SELECT e.id,e.state,e.classifier,e.error,e.ack,e.processed_at,e.hold,q.task,q.state AS responsibility "
                "FROM events e LEFT JOIN queue q ON q.event=e.id WHERE e.role=? AND e.processed_at IS NULL "
                "AND (? IS NULL OR (e.received,e.id)>(?,?)) "
                "AND (e.state IN ('classification-held','mapping-held') OR q.phase='control' OR e.id IN (SELECT event FROM input_resolutions)) "
                "ORDER BY e.received,e.id LIMIT ?",(role,after,cursor['received'] if cursor else 0,after or '',limit+1))
        return {'role':role,'availability':'Durable records only; no native wake or processing proof',
            'inputs':rows[:limit],'more_inputs':len(rows)>limit,'next_after':rows[limit-1]['id'] if len(rows)>limit else None,
            'recovery':self.rows("SELECT id,token,active_attempt,controller,recovery_owner,collection_handoff,recovery_state,hold_reason FROM jobs WHERE role=? AND state='held' "
                "AND recovery_state IN ('diagnosing','awaiting-disposition','owner-deferred') ORDER BY created,id LIMIT ?",(role,limit)),
            'limit':limit,'paging':'Use exact input-show/recover-source references; a full page is not exhaustive'}
