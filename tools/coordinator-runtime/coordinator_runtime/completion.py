"""Explicit real-role delegation for routine collector completion, never impersonation."""
import json

from .contracts import Refusal, encode, digest, collected_task_result
from .routine import BOARD_SCHEMA, policy_for


class Completion:
    def grant_completion(self, conn, grant, authority):
        if not conn.execute('SELECT 1 FROM coordinator_delivery_grants_v1 WHERE grant_id=?', (grant['id'],)).fetchone():
            raise Refusal('routine collector delegation also needs explicit outgoing service-actor delegation')
        policies = {name: task.get('routine_completion') for name, task in self.config['tasks'].items()
                    if task['role'] == self.role}
        conn.execute('INSERT INTO coordinator_completion_grants_v1 VALUES(?,?,?)', (grant['id'], encode(policies), authority))

    def extend_completion(self, runtime, authority):
        self.store.acting_session(self.selected['owner'])
        with self.opened() as conn:
            conn.executescript(BOARD_SCHEMA)
            with self.store.write(conn):
                grant = self._grant(conn, runtime)
                self.grant_completion(conn, grant, authority)
        return {'grant_id': grant['id'], 'routine_collector': 'explicit-real-role-delegation'}

    def completion_authority(self, runtime, task):
        with self.opened() as conn:
            grant = self._grant(conn, runtime)
            try:
                selected = conn.execute('SELECT * FROM coordinator_completion_grants_v1 WHERE grant_id=?', (grant['id'],)).fetchone()
            except Exception as exc:
                raise Refusal('routine collector delegation not yet present') from exc
            if not selected or task not in json.loads(selected['policies']):
                raise Refusal('actual role has not delegated this routine collector duty')
            if json.loads(selected['policies'])[task] != self.config['tasks'][task].get('routine_completion'):
                raise Refusal('routine completion policy differs from exact real-role grant')
            return grant

    def complete_own_delivery(self, runtime, outbox):
        if outbox['recipient'] != self.role or outbox['kind'] not in {'result', 'effect-request'} or not outbox['job']:
            return None
        job = runtime.job(outbox['job'])
        if job['role'] != self.role or not job['active_attempt']:
            return None
        try:
            grant = self.completion_authority(runtime, job['task'])
        except Refusal:
            return None  # Existing external/undelegated duties stay actually owned.
        attempt = runtime.attempt(job['active_attempt'])
        try:answer=collected_task_result(attempt)
        except Refusal:return None
        if (attempt['ended'] is None or attempt['collected'] is None or attempt['exit'] != 0 or attempt['error']
                or attempt['capture'] != 'complete' or answer.get('semantic') != 'DONE'
                or job['effects'] not in {'none','reconciled'} or job['hold_reason']):
            return None
        from .readiness import assess
        local=None
        if runtime.config['tasks'][job['task']].get('routine_completion'):
            try:local=assess(runtime,attempt)
            except Refusal:return None
        elif answer.get('failures') or answer.get('unknowns'):return None
        proof = {'actor': self.config['actor'], 'delegated_by': grant['owner'], 'grant_id': grant['id'],
                 'recipient': grant['owner'], 'worker': attempt['session'], 'collector': attempt['controller'],
                 'evidence': {'attempt': attempt['id'], 'result_hash': digest(answer), 'effect_receipt': job['effect_receipt']},
                 'local_readiness':local,
                 'native_receipt':False,'genuine_owner_full_read':False,
                 'meaning': 'actual delegated collector consumed routine handback; other outboxes remain owned'}
        if outbox['kind'] == 'effect-request':
            proof['effects'] = {'evidence': [job['effect_receipt']], 'unknown_effects': []}
        with self.opened() as conn:
            with self.store.write(conn):
                self._grant(conn, runtime)  # Recheck before new recipient effects.
                row = conn.execute('SELECT * FROM coordinator_deliveries_v1 WHERE id=? AND recipient=?', (outbox['id'], grant['owner'])).fetchone()
                if not row:
                    raise Refusal('routine callback does not own the addressed delivery')
                if row['actor']!=self.config['actor'] or row['owner']!=grant['owner'] or row['grant_id']!=grant['id'] or row['payload']!=outbox['payload']:
                    raise Refusal('routine callback must retain the exact service/role/source grant')
                notice = conn.execute('SELECT * FROM notification_outbox WHERE notification_id=?', (row['notice'],)).fetchone()
                if notice['route'] != 'managed' or notice['delivery_state'] == 'sending':
                    raise Refusal('routine callback cannot claim another transport consumer or an unsettled send')
                for column, stage in [('pickup','picked-up'),('processing','processed'),('settlement','settled')]:
                    if not row[column]:
                        conn.execute(f'UPDATE coordinator_deliveries_v1 SET {column}=?,state=?,processed_at=CASE WHEN ?=\'processed\' THEN ? ELSE processed_at END WHERE id=?',
                                     (encode(proof), stage, stage, runtime.clock(), outbox['id']))
                stamp = self.store.utc_now()
                conn.execute("UPDATE notification_outbox SET delivery_state='acknowledged',acknowledged_at=COALESCE(acknowledged_at,?),state_changed_at=? WHERE notification_id=?",
                             (stamp, stamp, row['notice']))
            row = conn.execute('SELECT * FROM coordinator_deliveries_v1 WHERE id=?', (outbox['id'],)).fetchone()
            return self._delivery_record(conn, dict(row))
