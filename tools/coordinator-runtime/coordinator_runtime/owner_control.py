"""Explicit one-shot pointers to genuine existing owners, never business dispatch.

Public helper source is an explicit pinned dependency. No private client reader,
new process stack, default resume, native retry or membership change lives here.
"""
import hashlib
import inspect
import json
import os
from pathlib import Path
import shlex
import time

from .contracts import Refusal, canonical_uuid, digest, encode, ident, regular_path, required_text

SCHEMA = """
CREATE TABLE IF NOT EXISTS coordinator_controls_v1(
 id TEXT PRIMARY KEY,delivery TEXT NOT NULL,caller TEXT NOT NULL,recipient TEXT NOT NULL,
 profile TEXT NOT NULL,mode TEXT NOT NULL,payload_hash TEXT NOT NULL,selection TEXT NOT NULL,
 attempt TEXT NOT NULL,client_message TEXT NOT NULL,pointer TEXT NOT NULL,state TEXT NOT NULL,
 result TEXT,created REAL NOT NULL);
CREATE TABLE IF NOT EXISTS coordinator_control_steps_v1(
 intent TEXT NOT NULL,ordinal INTEGER NOT NULL,phase TEXT NOT NULL,turn TEXT,rpc_id TEXT,
 created REAL NOT NULL,PRIMARY KEY(intent,ordinal));
"""
MODES={'queue-existing','queue-resume-existing','active-only-steer'}


def control_actor(expected):
    actual=canonical_uuid(os.environ.get('CODEX_SESSION_ID'))
    if actual!=expected:raise Refusal('current actor differs from actual control caller; do not synthesize identity')
    return actual


def load_helper(board,selection):
    """Never silently substitute the other-owned dirty shared source for baseline."""
    from .board import module_at
    names={'queue_transport.py'}
    if selection['mode']=='active-only-steer':names|={'active_transport.py','active_rpc.py'}
    pins=selection['helper_sources']
    if not isinstance(pins,dict) or set(pins)!=names:raise Refusal('exact public helper source pins required for selected mode')
    for name in names:
        try:path=regular_path(str(Path(board.library)/name))
        except (Refusal,OSError) as exc:raise Refusal('selected public helper unavailable; source receiving required: '+name) from exc
        if hashlib.sha256(path.read_bytes()).hexdigest()!=pins[name]:raise Refusal('public helper source pin changed: '+name)
    loaded={'queue_transport':module_at(board.library,'queue_transport')}
    helper=loaded['queue_transport']
    if selection['mode']=='active-only-steer':
        loaded['active_rpc']=module_at(board.library,'active_rpc')
        helper=module_at(board.library,'active_transport',imports=loaded)
        loaded['active_transport']=helper
    for name,module in loaded.items():
        if module.__coordinator_source_sha256__!=pins[name+'.py']:
            raise Refusal('compiled public helper source differs from selected pin')
    name='steer_notice' if selection['mode']=='active-only-steer' else 'queue_notice'
    options={'client_message_id':selection['intent'],'record':lambda *args:None} if name=='steer_notice' else (
        {'resume':True} if selection['mode']=='queue-resume-existing' else {})
    try:inspect.signature(getattr(helper,name)).bind(selection['recipient'],selection['profile'],'pointer',**options)
    except (AttributeError,TypeError,ValueError) as exc:
        raise Refusal('selected public helper lacks the bounded control interface: '+name) from exc
    return helper


class OwnerControl:
    def _control_binding(self,conn,runtime,delivery,selection):
        self._control_selection(selection)  # Recheck freshness at each pre-effect fence.
        row=conn.execute('SELECT * FROM coordinator_deliveries_v1 WHERE id=?',(delivery,)).fetchone()
        if not row:raise Refusal('exact runtime delivery required; post/notice IDs are not control intents')
        outbox=runtime.one('SELECT * FROM outboxes WHERE id=?',(delivery,))
        if not outbox or row['payload']!=outbox['payload'] or row['producer']!=outbox['producer']:
            raise Refusal('runtime/board delivery source differs')
        if row['kind'] not in {'question','alert','effect-request','result'}:
            raise Refusal('control pointers cannot dispatch executable work')
        grant,target=self._delivery_grant(conn,runtime,outbox)
        control_actor(grant['owner'])
        if (row['grant_id']!=grant['id'] or row['owner']!=grant['owner'] or row['actor']!=self.config['actor']
                or row['recipient']!=target['session'] or row['kind']!=outbox['kind'] or row['required']!=outbox['required']):
            raise Refusal('original delivery identity/scope differs from current exact grant; no custody transfer')
        role=outbox['recipient']
        if role not in self.config['roles']:raise Refusal('only genuine selected coordinator roles receive controls')
        enrolled=runtime.enrollment(role)
        selected=self.config['roles'][role]
        target_grant=conn.execute('SELECT * FROM coordinator_grants_v1 WHERE id=?',(enrolled['grant_id'],)).fetchone()
        if (not target_grant or target_grant['revoked'] is not None or target_grant['owner']!=target['session']
                or target_grant['role']!=role or target_grant['board_id']!=grant['board_id']
                or target_grant['profile']!=target['profile'] or target_grant['issued_by']!=target['session']
                or target_grant['runtime']!=grant['runtime'] or target_grant['runtime_dev']!=grant['runtime_dev']
                or target_grant['runtime_ino']!=grant['runtime_ino'] or target_grant['actor']!=grant['actor']
                or selected['owner']!=target['session'] or selected['profile']!=target['profile']
                or selected['board_id']!=grant['board_id'] or selected['board_role']!=target['board_role']):
            raise Refusal('recipient needs its actual current role enrollment; no bootstrap/substitute')
        member=conn.execute('SELECT route FROM sessions WHERE session=?',(target['session'],)).fetchone()
        notice=conn.execute('SELECT route FROM notification_outbox WHERE notification_id=?',(row['notice'],)).fetchone()
        if not member or member['route']!='managed' or not notice or notice['route']!='managed':
            raise Refusal('preserve actual managed membership/intake; no downgrade or foreign queue claim')
        if selection['recipient']!=target['session'] or selection['profile']!=target['profile']:
            raise Refusal('selected native recipient/profile differs from actual membership')
        binding=selection['binding']
        if binding['context']!=target['session'] or binding['profile']!=target['profile']:
            raise Refusal('native binding must identify this genuine existing context/profile')
        return dict(row),grant

    @staticmethod
    def _control_selection(selection):
        keys={'intent','mode','recipient','profile','scope','evidence','binding','helper_sources'}
        if not isinstance(selection,dict) or set(selection)!=keys:raise Refusal('complete explicit control selection required')
        canonical_uuid(selection['intent']);canonical_uuid(selection['recipient'])
        if not isinstance(selection['mode'],str) or selection['mode'] not in MODES or selection['scope']!='delivery-control-only':
            raise Refusal('explicit supported channel and delivery-control-only scope required')
        binding=selection['binding']
        if not isinstance(binding,dict) or set(binding)!={'context','profile','state','turn','valid_until','evidence'}:
            raise Refusal('explicit native applicability/binding evidence required')
        canonical_uuid(binding['context'])
        if type(binding['valid_until']) not in {int,float} or not time.time()<binding['valid_until']<time.time()+3600:
            raise Refusal('fresh finite native binding required; no expired reuse')
        if not isinstance(binding['state'],str) or binding['state'] not in {'active','idle','unloaded','unknown'}:raise Refusal('actual applicability state required')
        if selection['mode']=='active-only-steer':
            if binding['state']!='active':raise Refusal('active-only steer refuses idle/unloaded/unknown; no fallback')
            canonical_uuid(binding['turn'])
        elif binding['state'] not in {'active','idle'} or binding['turn'] is not None:
            raise Refusal('existing-context queue requires explicit active/idle binding, no guessed turn/unloaded fallback')
        for evidence in [selection['evidence'],binding['evidence']]:
            if not isinstance(evidence,list) or not 1<=len(evidence)<=16:raise Refusal('actual authority/binding evidence required')
            for item in evidence:required_text(item,'control evidence',2000)
        if len(encode(selection).encode())>16000:raise Refusal('bounded control selection required')

    def control_prepare(self,runtime,delivery,selection):
        self._control_selection(selection)
        with self.opened() as conn:
            conn.executescript(SCHEMA)
            with self.store.write(conn):
                row,grant=self._control_binding(conn,runtime,delivery,selection)
                old=conn.execute('SELECT * FROM coordinator_controls_v1 WHERE id=?',(selection['intent'],)).fetchone()
                if old:
                    if old['delivery']!=delivery or old['caller']!=grant['owner'] or old['selection']!=encode(selection):
                        raise Refusal('same control intent already binds different meaning/channel')
                    return self._control_record(conn,old)
                if row['processed_at'] is not None:raise Refusal('already processed delivery cannot be replayed')
                previous=conn.execute('SELECT * FROM coordinator_controls_v1 WHERE delivery=?',(delivery,)).fetchall()
                meaning={k:v for k,v in selection.items() if k!='intent'}
                if any(p['state']!='refused' or {k:v for k,v in json.loads(p['selection']).items() if k!='intent'}==meaning for p in previous):
                    raise Refusal('existing control intent/effect remains owned; no blind retry or channel fallback')
                self._control_budget(conn,len(encode(selection).encode())+2048)
                attempt,message=ident(),ident()
                cli=self.config.get('operator_cli',str(Path(__file__).resolve().parents[1]/'coordinator'))
                config=self.config.get('operator_config','ACTUAL_CONFIG')
                read=shlex.join([cli,'--config',config,'delivery-show',self.role,delivery])
                pointer=(f'CONTROL intent={selection["intent"]} attempt={attempt} message={message}. '
                    f'Read full durable meaning: {read}. Genuine existing owner: read/pickup/dispose/settle this control only. '
                    'No original input ACK/replay, new execution, publication or acceptance authority.')
                if len(pointer)>700:raise Refusal('complete control pointer exceeds public helper bound; no truncation')
                conn.execute('INSERT INTO coordinator_controls_v1 VALUES(?,?,?,?,?,?,?,?,?,?,?,?,NULL,?)',
                    (selection['intent'],delivery,grant['owner'],row['recipient'],selection['profile'],selection['mode'],
                     digest(json.loads(row['payload'])),encode(selection),attempt,message,pointer,'prepared',time.time()))
                return self._control_record(conn,conn.execute('SELECT * FROM coordinator_controls_v1 WHERE id=?',(selection['intent'],)).fetchone())

    def _control_budget(self,conn,incoming,*,new_intent=True):
        count,used=conn.execute('SELECT COUNT(*),COALESCE(SUM(LENGTH(CAST(selection AS BLOB))+LENGTH(CAST(pointer AS BLOB))+COALESCE(LENGTH(CAST(result AS BLOB)),0)),0) FROM coordinator_controls_v1').fetchone()
        steps=conn.execute('SELECT COUNT(*) FROM coordinator_control_steps_v1').fetchone()[0]
        if ((new_intent and count>=self.config['limits']['max_events'])
                or used+steps*512+incoming>=self.config['limits']['max_bytes']):
            raise Refusal('bounded control custody full; no held intent discarded')

    @staticmethod
    def _control_record(conn,row):
        return {**dict(row),'selection':json.loads(row['selection']),'result':json.loads(row['result']) if row['result'] else None,
                'steps':[dict(r) for r in conn.execute('SELECT * FROM coordinator_control_steps_v1 WHERE intent=? ORDER BY ordinal',(row['id'],))],
                'arrival':'not inferred from transport acceptance','processing':'actual recipient evidence required'}

    def control_show(self,intent):
        canonical_uuid(intent)
        actor=canonical_uuid(os.environ.get('CODEX_SESSION_ID'))
        with self.opened(settlement=True,owner_required=False) as conn:
            row=self._control_lookup(conn,intent)
            if not row or actor not in {row['caller'],row['recipient']}:raise Refusal('control visible only to its actual caller/recipient')
            return self._control_record(conn,row)

    def control_cancel(self,intent):
        """Withdraw only an unattempted preparation, never an uncertain send."""
        with self.opened(settlement=True,owner_required=False) as conn:
            with self.store.write(conn):
                row=self._control_lookup(conn,intent)
                if not row:raise Refusal('actual control caller required')
                control_actor(row['caller'])
                if row['state'] not in {'prepared','refused'}:raise Refusal('attempted control cannot be cancelled or replayed')
                if row['state']=='prepared':
                    conn.execute("UPDATE coordinator_controls_v1 SET state='refused',result=? WHERE id=?",
                        (encode({'helper_status':'not-called','queue_message_id':None,'reason':'caller-withdrew-before-effect'}),intent))
                return self._control_record(conn,conn.execute('SELECT * FROM coordinator_controls_v1 WHERE id=?',(intent,)).fetchone())

    def control_send(self,runtime,intent):
        with self.opened() as conn:
            row=self._control_lookup(conn,intent)
            if not row:raise Refusal('prepared exact control intent required')
            control_actor(row['caller'])
            if row['state']!='prepared':return self._control_record(conn,row)  # Never replay even an unknown/failed attempt.
            selection=json.loads(row['selection']);self._control_selection(selection)
            delivery,grant=self._control_binding(conn,runtime,row['delivery'],selection)
            if delivery['processed_at'] is not None or digest(json.loads(delivery['payload']))!=row['payload_hash']:
                raise Refusal('current delivery processed or source changed')
        # Public source/API preflight only, before the durable one-shot claim.
        try:helper=load_helper(self,selection)
        except (Refusal,OSError,ImportError) as exc:
            with self.opened(settlement=True,owner_required=False) as conn:
                with self.store.write(conn):
                    conn.execute("UPDATE coordinator_controls_v1 SET state='refused',result=? WHERE id=? AND state='prepared'",
                        (encode({'helper_status':'not-called','queue_message_id':None,'reason':'public-helper-preflight-refused','detail':str(exc)[:1000]}),intent))
            raise Refusal(str(exc)) from exc
        with self.opened() as conn:
            with self.store.write(conn):
                delivery,grant=self._control_binding(conn,runtime,row['delivery'],selection)
                if delivery['processed_at'] is not None:raise Refusal('delivery processed before control effect')
                changed=conn.execute("UPDATE coordinator_controls_v1 SET state='inflight' WHERE id=? AND state='prepared'",(intent,)).rowcount
                if not changed:return self._control_record(conn,conn.execute('SELECT * FROM coordinator_controls_v1 WHERE id=?',(intent,)).fetchone())
        def record(phase,turn,rpc_id):
            if phase not in {'STEER_INTENT','STEER_ACCEPTED'} or turn!=selection['binding']['turn']:
                raise Refusal('native turn/phase differs from selected applicability; no effect permitted')
            with self.opened(settlement=phase!='STEER_INTENT',owner_required=phase=='STEER_INTENT') as conn:
                with self.store.write(conn):
                    if phase=='STEER_INTENT':self._control_binding(conn,runtime,row['delivery'],selection)
                    count=conn.execute('SELECT COUNT(*) FROM coordinator_control_steps_v1 WHERE intent=?',(intent,)).fetchone()[0]
                    if (phase,count) not in {('STEER_INTENT',0),('STEER_ACCEPTED',1)}:
                        raise Refusal('native correlation phases must preserve one exact attempt order')
                    if phase=='STEER_INTENT':required_text(rpc_id,'native request correlation',128)
                    self._control_budget(conn,512,new_intent=False)
                    conn.execute('INSERT INTO coordinator_control_steps_v1 VALUES(?,?,?,?,?,?)',(intent,count,phase,turn,rpc_id,time.time()))
        try:
            if row['mode']=='active-only-steer':
                result=helper.steer_notice(row['recipient'],row['profile'],row['pointer'],client_message_id=row['client_message'],record=record)
            else:
                options={'resume':True} if row['mode']=='queue-resume-existing' else {}
                result=helper.queue_notice(row['recipient'],row['profile'],row['pointer'],**options)
            summary={'helper_status':result.status,'queue_message_id':result.queue_message_id,'helper_returncode':result.returncode,
                     'reason':result.reason if result.reason in {'queue_accepted','queue_rejected','steer_accepted','steer_uncertain','recipient_not_active','runner_launch_failed','sender_timeout','sender_exception','active_connection_unavailable','active_metadata_unavailable','queue_accepted_resume_requested_unknown','queue_accepted_resume_warning'} else 'other_helper_outcome'}
        except Exception:
            summary={'helper_status':'ambiguous','queue_message_id':None,'helper_returncode':None,'reason':'helper_exception_after_claim'}
        with self.opened(settlement=True,owner_required=False) as conn:
            with self.store.write(conn):
                steps=[dict(r) for r in conn.execute('SELECT * FROM coordinator_control_steps_v1 WHERE intent=? ORDER BY ordinal',(intent,))]
                state='unknown'
                if row['mode']=='active-only-steer':
                    if (summary['helper_status']=='queued' and summary['reason']=='steer_accepted' and summary['queue_message_id'] is None
                            and [s['phase'] for s in steps]==['STEER_INTENT','STEER_ACCEPTED']):state='accepted'
                    elif summary['helper_status']=='failed' and not steps:state='refused'
                elif summary['helper_status']=='queued' and summary['queue_message_id'] and type(summary['helper_returncode']) is int and summary['helper_returncode']==0:
                    try:canonical_uuid(summary['queue_message_id']);state='accepted'
                    except Refusal:pass
                elif summary['helper_status']=='failed':state='refused'
                conn.execute('UPDATE coordinator_controls_v1 SET state=?,result=? WHERE id=?',(state,encode(summary),intent))
                return self._control_record(conn,conn.execute('SELECT * FROM coordinator_controls_v1 WHERE id=?',(intent,)).fetchone())

    @staticmethod
    def _control_lookup(conn,intent):
        canonical_uuid(intent)
        if not conn.execute("SELECT 1 FROM sqlite_master WHERE name='coordinator_controls_v1'").fetchone():return None
        return conn.execute('SELECT * FROM coordinator_controls_v1 WHERE id=?',(intent,)).fetchone()

    @staticmethod
    def control_processing_proof(conn,row,actor,receipt):
        if not conn.execute("SELECT 1 FROM sqlite_master WHERE name='coordinator_controls_v1'").fetchone():return
        control=conn.execute("SELECT * FROM coordinator_controls_v1 WHERE delivery=? AND state IN ('inflight','accepted','unknown') ORDER BY created DESC LIMIT 1",(row['id'],)).fetchone()
        if not control:return
        if digest(json.loads(row['payload']))!=control['payload_hash']:
            raise Refusal('control proof cannot replace changed original delivery meaning')
        if control['state']=='inflight':raise Refusal('actual control sender still owns an uncollected attempt')
        result=json.loads(control['result']) if control['result'] else {}
        if control['mode']!='active-only-steer':
            proof=receipt.get('transport',{})
            if (not result.get('queue_message_id') or proof.get('queue_message_id')!=result['queue_message_id']
                    or proof.get('state')!='processed' or not proof.get('evidence')):
                raise Refusal('true control queue ID and actual consumer processing proof required')
            return
        if receipt.get('transport'):raise Refusal('steer has no queue ID; use separate existing-context control proof')
        proof=receipt.get('control',{})
        keys={'kind','intent','attempt','client_message_id','turn_id','received_by','profile','full_read','state','evidence','disposition'}
        if not isinstance(proof,dict) or set(proof)!=keys:
            raise Refusal('exact separate control proof required; never invent a queue ID')
        if not isinstance(proof['evidence'],list) or not 1<=len(proof['evidence'])<=16:
            raise Refusal('bounded actual control receiver evidence required')
        for item in proof['evidence']:required_text(item,'control receiver evidence',2000)
        required_text(proof['disposition'],'actual control disposition',4000)
        expected=json.loads(control['selection'])['binding']['turn']
        if (proof.get('kind')!='existing-context-control' or proof.get('intent')!=control['id']
                or proof.get('attempt')!=control['attempt'] or proof.get('client_message_id')!=control['client_message']
                or proof.get('turn_id')!=expected or proof.get('received_by')!=actor or proof.get('profile')!=control['profile']
                or proof.get('full_read')!=control['payload_hash'] or proof.get('state')!='processed'
                or not proof.get('evidence') or not proof.get('disposition')):
            raise Refusal('actual full-read/context/turn/message/disposition control proof required; acceptance is insufficient')
        if not conn.execute("SELECT 1 FROM coordinator_control_steps_v1 WHERE intent=? AND phase='STEER_INTENT' AND turn=?",(control['id'],expected)).fetchone():
            raise Refusal('no durable native turn/client-message association; retain uncertainty')
