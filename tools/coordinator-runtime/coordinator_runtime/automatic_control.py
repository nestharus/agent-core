"""Prospective, explicitly delegated service pointers; no owner impersonation."""
import json
import math
import time
import uuid

from .contracts import Refusal, canonical_uuid, digest, encode, ident, required_text

SCHEMA = """
CREATE TABLE IF NOT EXISTS coordinator_control_grants_v1(
 id TEXT PRIMARY KEY,source_grant TEXT NOT NULL,actor TEXT NOT NULL,policy TEXT NOT NULL,
 authority TEXT NOT NULL,issued_by TEXT NOT NULL,cutover INTEGER NOT NULL,created REAL NOT NULL,revoked REAL);
CREATE TABLE IF NOT EXISTS coordinator_control_requirements_v1(
 delivery TEXT PRIMARY KEY,created REAL NOT NULL);
CREATE TABLE IF NOT EXISTS coordinator_control_receipts_v1(
 delivery TEXT PRIMARY KEY,intent TEXT NOT NULL,receipt TEXT NOT NULL,processed_at REAL NOT NULL);
"""


class AutomaticControl:
    def delegate_control(self,runtime,policy,authority):
        """Actual owner extends its existing outgoing grant, never native ownership."""
        from .owner_control import control_actor
        control_actor(self.selected['owner'])
        required_text(authority,'actual control delegation authority',4000)
        self._control_policy(policy)
        with self.opened() as conn:
            conn.executescript(SCHEMA)
            with self.store.write(conn):
                grant=self._grant(conn,runtime)
                outgoing=conn.execute('SELECT recipients,kinds FROM coordinator_delivery_grants_v1 WHERE grant_id=?',(grant['id'],)).fetchone()
                if not outgoing:raise Refusal('control capability requires existing scoped service delivery delegation')
                for role,target in policy['recipients'].items():
                    enrolled=runtime.enrollment(role)
                    if (json.loads(outgoing['recipients']).get(role)!=target['context']
                            or enrolled['owner']!=target['context'] or enrolled['profile']!=target['profile']):
                        raise Refusal('control target must retain actual current selected enrollment/delivery scope')
                if set(policy['kinds'])-set(json.loads(outgoing['kinds'])):raise Refusal('control kinds exceed existing delivery delegation')
                count,used=conn.execute('SELECT COUNT(*),COALESCE(SUM(LENGTH(CAST(policy AS BLOB))+LENGTH(CAST(authority AS BLOB))),0) FROM coordinator_control_grants_v1').fetchone()
                if count>=self.config['limits']['max_events'] or used+len(encode(policy).encode())+len(authority.encode())>=self.config['limits']['max_bytes']:
                    raise Refusal('bounded control delegation custody full; no old grants discarded')
                cutover=conn.execute('SELECT COALESCE(MAX(seq),0) FROM posts').fetchone()[0]
                conn.execute('UPDATE coordinator_control_grants_v1 SET revoked=? WHERE source_grant=? AND revoked IS NULL',(time.time(),grant['id']))
                key=ident()
                conn.execute('INSERT INTO coordinator_control_grants_v1 VALUES(?,?,?,?,?,?,?,?,NULL)',
                    (key,grant['id'],self.config['actor'],encode(policy),authority,grant['owner'],cutover,time.time()))
                return {'id':key,'source_grant':grant['id'],'actor':self.config['actor'],'issued_by':grant['owner'],
                    'after_post':cutover,'policy':policy,'meaning':'prospective service control only; no native owner grant or receipt'}

    def revoke_control(self,runtime,delegation):
        from .owner_control import control_actor
        control_actor(self.selected['owner'])
        with self.opened(settlement=True) as conn:
            with self.store.write(conn):
                grant=self._grant(conn,runtime)
                if conn.execute('UPDATE coordinator_control_grants_v1 SET revoked=? WHERE id=? AND source_grant=?',
                        (time.time(),delegation,grant['id'])).rowcount!=1:raise Refusal('actual source owner control capability required')
        return {'revoked':delegation,'existing_intents_and_receipt_duties':'retained'}

    def _control_policy(self,policy):
        keys={'scope','recipients','kinds','helper_sources','valid_until','evidence'}
        if not isinstance(policy,dict) or set(policy)!=keys or policy['scope']!='delivery-control-only':
            raise Refusal('explicit bounded automatic control policy required')
        if type(policy['valid_until']) not in {int,float} or not math.isfinite(policy['valid_until']) or policy['valid_until']<=time.time():
            raise Refusal('unexpired actual service control selection required')
        if (not isinstance(policy['recipients'],dict) or not policy['recipients']
                or set(policy['recipients'])-set(self.config['roles'])):raise Refusal('only selected enrolled coordinators receive automatic control')
        if (not isinstance(policy['kinds'],list) or not policy['kinds']
                or set(policy['kinds'])-{'question','alert','effect-request','result'}):raise Refusal('automatic control cannot dispatch work')
        if not isinstance(policy['helper_sources'],dict) or set(policy['helper_sources'])!={'queue_transport.py'}:
            raise Refusal('automatic queue mode needs exact public queue helper pin')
        pin=policy['helper_sources']['queue_transport.py']
        if not isinstance(pin,str) or len(pin)!=64 or any(c not in '0123456789abcdef' for c in pin):raise Refusal('exact SHA256 helper pin required')
        lists=[policy['evidence']]
        for role,target in policy['recipients'].items():
            if not isinstance(target,dict) or set(target)!={'context','profile','mode','availability','evidence'}:
                raise Refusal('exact existing recipient/profile/mode/availability/evidence required')
            selected=self.config['roles'][role]
            if (target['context']!=selected['owner'] or target['profile']!=selected['profile']
                    or target['mode'] not in {'queue-existing','queue-resume-existing'} or target['availability']!='unknown'):
                raise Refusal('automatic control uses explicit existing queue mode with honest unknown native availability')
            canonical_uuid(target['context']);lists.append(target['evidence'])
        for evidence in lists:
            if not isinstance(evidence,list) or not 1<=len(evidence)<=16:raise Refusal('bounded actual control authority/binding evidence required')
            for item in evidence:required_text(item,'control policy evidence',2000)
        if len(encode(policy).encode())>16000:raise Refusal('bounded service control policy required')

    def verify_control_delegation(self,conn,runtime,outbox,selection,grant):
        if not conn.execute("SELECT 1 FROM sqlite_master WHERE name='coordinator_control_grants_v1'").fetchone():
            raise Refusal('explicit service control capability absent; no grant acquisition')
        cap=conn.execute('SELECT * FROM coordinator_control_grants_v1 WHERE id=?',(selection.get('delegation'),)).fetchone()
        if (not cap or cap['revoked'] is not None or cap['source_grant']!=grant['id']
                or cap['actor']!=self.config['actor'] or cap['issued_by']!=grant['owner']):
            raise Refusal('service control capability absent/revoked or wrong actual actor/source grant')
        policy=json.loads(cap['policy']);self._control_policy(policy)
        target=policy['recipients'].get(outbox['recipient'])
        row=conn.execute('SELECT post FROM coordinator_deliveries_v1 WHERE id=?',(outbox['id'],)).fetchone()
        if not target or outbox['kind'] not in policy['kinds'] or not row or row['post']<=cap['cutover']:
            raise Refusal('control outside prospective exact delegation; no old notice/queue replay')
        binding=selection['binding']
        if (selection['recipient']!=target['context'] or selection['profile']!=target['profile']
                or selection['mode']!=target['mode'] or selection['helper_sources']!=policy['helper_sources']
                or binding['state']!='unknown' or binding['turn'] is not None
                or binding['valid_until']>policy['valid_until'] or selection['evidence']!=policy['evidence']
                or binding['evidence']!=target['evidence']):raise Refusal('control intent differs from actual service delegation')
        return cap

    def automatic_control(self,runtime,outbox,*,send=True):
        """Dispatcher-only use of service capability; never sets CODEX_SESSION_ID."""
        with self.opened() as conn:
            if not conn.execute("SELECT 1 FROM sqlite_master WHERE name='coordinator_control_grants_v1'").fetchone():return False
            grant=self._grant(conn,runtime)
            cap=conn.execute('SELECT * FROM coordinator_control_grants_v1 WHERE source_grant=? AND revoked IS NULL ORDER BY created DESC LIMIT 1',(grant['id'],)).fetchone()
            if not cap:return False
            policy=json.loads(cap['policy']);target=policy['recipients'].get(outbox['recipient'])
            row=conn.execute('SELECT * FROM coordinator_deliveries_v1 WHERE id=?',(outbox['id'],)).fetchone()
            if not target or outbox['kind'] not in policy['kinds'] or row['post']<=cap['cutover']:return False
            status=self.control_receipt_status(conn,row)
            if status['required'] and not status['pending']:return False
            # Delivery duty survives expired/unavailable effect authority. This
            # marker permits no send and prevents a callback from hiding the gap.
            with self.store.write(conn):self.require_control(conn,outbox['id'])
            intent=str(uuid.uuid5(uuid.UUID(cap['id']),outbox['id']))
            prior=self._control_lookup(conn,intent)
            if prior and prior['state']!='prepared':return False  # Terminal custody never renews/retries on ticks.
            self._control_policy(policy)
            selection=json.loads(prior['selection']) if prior else {
                'intent':intent,'delegation':cap['id'],'mode':target['mode'],'recipient':target['context'],'profile':target['profile'],
                'scope':'delivery-control-only','evidence':policy['evidence'],'helper_sources':policy['helper_sources'],
                'binding':{'context':target['context'],'profile':target['profile'],'state':'unknown','turn':None,
                           'valid_until':min(time.time()+3500,policy['valid_until']),'evidence':target['evidence']}}
            self._control_binding(conn,runtime,outbox['id'],selection,service=True)
        prepared=self.control_prepare(runtime,outbox['id'],selection,service=True)
        if not send or prepared['state']!='prepared':return False
        try:self.control_send(runtime,intent,service=True)
        except Exception as exc:
            exc.control_budget_spent=True  # Conservatively includes preflight refusal.
            raise
        return True

    @staticmethod
    def require_control(conn,delivery):
        conn.execute('INSERT OR IGNORE INTO coordinator_control_requirements_v1 VALUES(?,?)',(delivery,time.time()))

    @staticmethod
    def control_receipt_status(conn,row):
        has=lambda table:conn.execute('SELECT 1 FROM sqlite_master WHERE name=?',(table,)).fetchone()
        required=has('coordinator_control_requirements_v1') and conn.execute('SELECT 1 FROM coordinator_control_requirements_v1 WHERE delivery=?',(row['id'],)).fetchone()
        retained=has('coordinator_controls_v1') and conn.execute('SELECT 1 FROM coordinator_controls_v1 WHERE delivery=?',(row['id'],)).fetchone()
        if not required and not retained:return {'required':False,'pending':False}
        receipt=conn.execute('SELECT * FROM coordinator_control_receipts_v1 WHERE delivery=?',(row['id'],)).fetchone() if has('coordinator_control_receipts_v1') else None
        ctrl=conn.execute('SELECT * FROM coordinator_controls_v1 WHERE delivery=? ORDER BY created DESC,rowid DESC LIMIT 1',(row['id'],)).fetchone() if retained else None
        return {'required':True,'pending':receipt is None,'receipt':json.loads(receipt['receipt']) if receipt else None,
                'intent':ctrl['id'] if ctrl else None,'payload_hash':ctrl['payload_hash'] if ctrl else None,
                'transport_state':ctrl['state'] if ctrl else 'not-prepared',
                'transport_outcome':json.loads(ctrl['result']) if ctrl and ctrl['result'] else None,
                'processed_at':receipt['processed_at'] if receipt else None,'native_arrival':'not inferred from callback/transport acceptance'}
