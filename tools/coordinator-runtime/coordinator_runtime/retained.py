"""Explicit software custody after normal revocation, without reopening intake.

This is a finite delivery/triage capability, not a replacement execution grant.
Original owners, sources, queues, collectors and processing clocks remain intact.
Shared residency is observed globally; logical use is charged to the original
runtime identity across grants. Neither counter measures physical platform bytes.
"""
from . import observations

import json
import math
import hashlib
from pathlib import Path

from .board import Board
from .contracts import Refusal, digest, encode, ident, required_text

SCHEMA = """
CREATE TABLE IF NOT EXISTS coordinator_retained_caps_v1(
 id TEXT PRIMARY KEY,source_grant TEXT NOT NULL,configuration TEXT NOT NULL,
 binding TEXT NOT NULL,policy TEXT NOT NULL,issuer TEXT NOT NULL,created REAL NOT NULL,
 revoked REAL,visits INTEGER NOT NULL DEFAULT 0,cursor INTEGER NOT NULL DEFAULT 0);
CREATE UNIQUE INDEX IF NOT EXISTS coordinator_retained_current_v1
 ON coordinator_retained_caps_v1(source_grant) WHERE revoked IS NULL;
CREATE TABLE IF NOT EXISTS coordinator_retained_handling_v1(
 capability TEXT NOT NULL,source TEXT NOT NULL,basis TEXT NOT NULL,
 receipt TEXT NOT NULL,created REAL NOT NULL,PRIMARY KEY(capability,source,basis));
"""

# Only fields owned by this protocol. This is serialized payload residency,
# not SQLite file allocation, native history, free space or all platform stores.
PAYLOAD_BYTES = 'COALESCE(SUM(LENGTH(CAST(payload AS BLOB))),0)'
CONTROL_KINDS = {'alert', 'question', 'result', 'effect-request'}


def implementation():
    directory = Path(__file__).resolve().parent
    return {name: hashlib.sha256((directory / name).read_bytes()).hexdigest()
            for name in ('retained.py', 'board_delivery.py')}


class RetainedBoard(Board):
    """An opt-in operator surface; ordinary Board never inherits this authority."""

    def _original(self, conn, runtime):
        from .configuration import assert_current
        assert_current(runtime)
        enrollment = runtime.one('SELECT grant_id,intake FROM enrollments WHERE role=?', (self.role,))
        grant = conn.execute('SELECT * FROM coordinator_grants_v1 WHERE id=?',
                             (enrollment['grant_id'],)).fetchone() if enrollment else None
        stat = runtime.path.stat()
        selection = self.config.get('software_delegation', {})
        if (not grant or not selection or grant['issued_by'] != selection.get('grantor')
                or grant['authority'] != selection.get('authority')
                or grant['revoked'] is None or enrollment['intake'] != 0):
            raise Refusal('exact stopped Work-issued software grant required; no native grant takeover')
        expected = (self.selected['board_id'], self.role, self.selected['owner'], self.config['actor'],
                    str(runtime.path), stat.st_dev, stat.st_ino)
        if tuple(grant[k] for k in ('board_id', 'role', 'owner', 'actor', 'runtime', 'runtime_dev', 'runtime_ino')) != expected:
            raise Refusal('original runtime/source/owner binding changed')
        cap = conn.execute('SELECT configuration FROM coordinator_software_grants_v1 WHERE grant_id=?',
                           (grant['id'],)).fetchone()
        if not cap or cap['configuration'] != self._configuration(runtime, self._binding(grant)):
            raise Refusal('original immutable software configuration changed')
        return dict(grant)

    def _configuration(self, runtime, binding):
        # Ordinary retained custody remains strictly bound to its historical
        # config. Only the explicit prospective ProcessingBoard can bridge it.
        return digest(self.config)

    @staticmethod
    def _binding(grant):
        return {k: grant[k] for k in ('id', 'board_id', 'role', 'owner', 'actor', 'runtime',
                                      'runtime_dev', 'runtime_ino', 'issued_by', 'authority', 'revoked')}

    def _usage(self, conn, grant):
        total = conn.execute('SELECT COUNT(*),' + PAYLOAD_BYTES + ' FROM coordinator_deliveries_v1').fetchone()
        owned = conn.execute('SELECT COUNT(*),' + PAYLOAD_BYTES.replace('payload', 'd.payload') +
            ' FROM coordinator_deliveries_v1 d JOIN coordinator_grants_v1 g ON g.id=d.grant_id '
            'WHERE g.runtime=? AND g.runtime_dev=? AND g.runtime_ino=? AND g.actor=?',
            tuple(grant[k] for k in ('runtime', 'runtime_dev', 'runtime_ino', 'actor'))).fetchone()
        return {'shared_rows': total[0], 'shared_payload_bytes': total[1],
                'runtime_rows': owned[0], 'runtime_payload_bytes': owned[1]}

    def _custody_bytes(self, conn, grant):
        used = conn.execute('SELECT COALESCE(SUM(LENGTH(CAST(c.policy AS BLOB))),0) FROM coordinator_retained_caps_v1 c '
            'JOIN coordinator_grants_v1 g ON g.id=c.source_grant WHERE g.runtime=?', (grant['runtime'],)).fetchone()[0]
        used += conn.execute('SELECT COALESCE(SUM(LENGTH(CAST(h.receipt AS BLOB))),0) FROM coordinator_retained_handling_v1 h '
            'JOIN coordinator_retained_caps_v1 c ON c.id=h.capability JOIN coordinator_grants_v1 g ON g.id=c.source_grant '
            'WHERE g.runtime=?', (grant['runtime'],)).fetchone()[0]
        return used + self._usage(conn, grant)['runtime_payload_bytes']

    def retained_basis(self, runtime):
        with self.opened(settlement=True) as conn:
            grant = self._original(conn, runtime)
            return self._basis(conn, runtime, grant)

    @observations.observe('retained-source')
    def _basis(self, conn, runtime, grant):
        # Streaming only this role's source hashes, never foreign payloads.
        events = []
        for event in runtime.rows('SELECT id,hash,payload FROM events WHERE role=? ORDER BY id', (self.role,)):
            if digest(runtime.event(event['id'])) != event['hash']:
                raise Refusal('retained original input payload/hash differs; preserve source for its owner')
            events.append({k: event[k] for k in ('id', 'hash')})
        outboxes = runtime.rows('SELECT id,producer,recipient,kind,required,payload FROM outboxes WHERE role=? ORDER BY id', (self.role,))
        observations.count('retained-events', len(events))
        observations.count('retained-outboxes', len(outboxes))
        continuation = None
        if conn.execute("SELECT 1 FROM sqlite_master WHERE name='coordinator_retained_caps_v1'").fetchone():
            row = conn.execute('SELECT id,issuer,created,revoked,visits,cursor FROM coordinator_retained_caps_v1 '
                               'WHERE source_grant=? AND revoked IS NULL', (grant['id'],)).fetchone()
            continuation = dict(row) if row else None
        return {'configuration': self._configuration(runtime, self._binding(grant)), 'implementation': implementation(), 'binding': self._binding(grant),
                'usage': self._usage(conn, grant), 'events': events, 'continuation': continuation,
                'outboxes': [{'id': o['id'], 'hash': digest(o)} for o in outboxes],
                'scope': 'existing retained sources only; no intake, execution, acceptance or cleanup'}

    def delegate_retained(self, runtime, policy):
        actor = self.store.acting_session(self.config.get('software_delegation', {}).get('grantor'))
        keys = {'basis', 'authority', 'expires', 'max_shared_rows', 'max_shared_payload_bytes',
                'max_runtime_rows', 'max_visits'}
        if not isinstance(policy, dict) or set(policy) != keys:
            raise Refusal('exact current basis, authority, expiry and finite residency/visit limits required')
        required_text(policy['authority'], 'actual continuing software authority', 4000)
        expiry = policy['expires']
        if (type(expiry) not in {int, float} or not math.isfinite(expiry)
                or not runtime.clock() < expiry <= runtime.clock() + 3600):
            raise Refusal('retained authority must expire within one hour')
        for key in ('max_shared_rows', 'max_shared_payload_bytes', 'max_runtime_rows', 'max_visits'):
            if type(policy[key]) is not int or policy[key] <= 0:
                raise Refusal('positive finite integer required: ' + key)
        if policy['max_visits'] > 4096:
            raise Refusal('retained handling visit bound exceeds 4096')
        if policy['max_runtime_rows'] > self.config['limits'].get('max_board_deliveries', self.config['limits']['max_events']):
            raise Refusal('retained logical allocation cannot expand original runtime entitlement')
        if len(encode(policy).encode()) > self.config['limits']['max_result_bytes']:
            raise Refusal('retained policy exceeds original bounded result custody')
        with self.opened() as conn:
            conn.executescript(SCHEMA)
            with self.store.write(conn):
                grant = self._original(conn, runtime)
                if grant['issued_by'] != actor or policy['basis'] != self._basis(conn, runtime, grant):
                    raise Refusal('issuer or current capacity/source basis changed; no automatic retry')
                usage = self._usage(conn, grant)
                if any(usage[u] > policy[p] for u, p in (
                        ('shared_rows', 'max_shared_rows'), ('shared_payload_bytes', 'max_shared_payload_bytes'),
                        ('runtime_rows', 'max_runtime_rows'))):
                    raise Refusal('selected capacity does not fit actual preserved residency')
                if conn.execute('SELECT 1 FROM coordinator_retained_caps_v1 WHERE source_grant=? AND revoked IS NULL', (grant['id'],)).fetchone():
                    raise Refusal('existing continuation remains owned; revoke it explicitly, never replace silently')
                # All authority records share the finite original per-runtime byte budget.
                used = self._custody_bytes(conn, grant)
                if used + len(encode(policy).encode()) > self.config['limits']['max_bytes']:
                    raise Refusal('retained authority custody full; keep old epochs')
                key = ident()
                conn.execute('INSERT INTO coordinator_retained_caps_v1 VALUES(?,?,?,?,?,?,?,NULL,0,0)',
                    (key, grant['id'], digest(self.config), encode(self._binding(grant)), encode(policy), actor, runtime.clock()))
        return {'capability': key, 'source_grant': grant['id'], 'issuer': actor,
                'normal_grant': 'still revoked', 'processing': 'not inferred'}

    def revoke_retained(self, runtime, key):
        actor = self.store.acting_session(self.config.get('software_delegation', {}).get('grantor'))
        with self.opened(settlement=True) as conn:
            with self.store.write(conn):
                grant = self._original(conn, runtime)
                row = conn.execute('SELECT * FROM coordinator_retained_caps_v1 WHERE id=?', (key,)).fetchone()
                if not row or row['issuer'] != actor or row['source_grant'] != grant['id']:
                    raise Refusal('only original software issuer can revoke this exact continuation')
                conn.execute('UPDATE coordinator_retained_caps_v1 SET revoked=COALESCE(revoked,?) WHERE id=?', (runtime.clock(), key))
        return {'revoked': key, 'original_responsibilities': 'retained'}

    @observations.observe('retained-authority')
    def _continued(self, conn, runtime):
        grant = self._original(conn, runtime)
        row = conn.execute('SELECT * FROM coordinator_retained_caps_v1 WHERE id=?', (self.capability,)).fetchone()
        if (not row or row['revoked'] is not None or row['source_grant'] != grant['id']
                or row['configuration'] != digest(self.config) or json.loads(row['binding']) != self._binding(grant)):
            raise Refusal('retained capability absent/revoked or changed source/configuration')
        policy = json.loads(row['policy'])
        if runtime.clock() >= policy['expires']:
            raise Refusal('retained capability expired; duties still held')
        current = self._basis(conn, runtime, grant)
        if (current['implementation'] != policy['basis']['implementation']
                or current['events'] != policy['basis']['events'] or current['outboxes'] != policy['basis']['outboxes']):
            raise Refusal('retained immutable source set changed; no replay or silent adoption')
        return grant, dict(row), policy

    def _grant(self, conn, runtime):
        return self._continued(conn, runtime)[0]

    def _delivery_capacity(self, conn, outbox):
        grant, row, policy = self._continued(conn, self.runtime)
        usage = self._usage(conn, grant)
        if (usage['shared_rows'] >= policy['max_shared_rows']
                or usage['shared_payload_bytes'] + len(outbox['payload'].encode()) > policy['max_shared_payload_bytes']
                or usage['runtime_rows'] >= policy['max_runtime_rows']
                or self._custody_bytes(conn, grant) + len(outbox['payload'].encode()) > self.config['limits']['max_bytes']):
            raise Refusal('retained shared residency or runtime logical allocation full; no held work discarded')

    def reconcile_delivery(self, runtime, outbox):
        with self.opened(settlement=True, owner_required=False) as conn:
            grant, _, _ = self._continued(conn, runtime)
            row = conn.execute('SELECT * FROM coordinator_deliveries_v1 WHERE id=?', (outbox['id'],)).fetchone()
            if not row:
                return None
            target = self.config['delivery']['recipients'][outbox['recipient']]
            expected = (grant['id'], grant['owner'], self.config['actor'], outbox['producer'],
                        target['session'], outbox['kind'], outbox['required'], outbox['payload'])
            if tuple(row[k] for k in ('grant_id', 'owner', 'actor', 'producer', 'recipient', 'kind', 'required', 'payload')) != expected:
                raise Refusal('retained delivery attribution/correlation differs from original source')
            return self._delivery_record(conn, dict(row))

    @observations.observe('retained-step')
    def retained_step(self, runtime, capability):
        """One real finite software handling visit; no native-owner impersonation.

        Persist actual source/hold observations and post informative controls.
        Executable work and native decisions stay explicitly outstanding. The
        handling receipt does NOT settle a delivery or start processing clocks.
        """
        self.capability, self.runtime = capability, runtime
        with self.opened() as conn:
            with self.store.write(conn):
                _, cap, policy = self._continued(conn, runtime)
                if cap['visits'] >= policy['max_visits']:
                    raise Refusal('finite retained visit budget exhausted; no implicit renewal')
                conn.execute('UPDATE coordinator_retained_caps_v1 SET visits=visits+1 WHERE id=?', (capability,))
        # The original runtime bytes are read, never rewritten by this operator.
        sources = [('input', e['id']) for e in policy['basis']['events']] + [('outbox', o['id']) for o in policy['basis']['outboxes']]
        items = sources[cap['cursor']:cap['cursor'] + 16]
        results = []
        for offset, (kind, source) in enumerate(items, cap['cursor'] + 1):
            receipt = self._handle_input(runtime, source) if kind == 'input' else self._handle_retained(
                runtime, runtime.one('SELECT * FROM outboxes WHERE id=?', (source,)))
            with self.opened() as conn:
                with self.store.write(conn):
                    grant, _, _ = self._continued(conn, runtime)
                    basis = digest(receipt)
                    body = encode(receipt)
                    used = self._custody_bytes(conn, grant)
                    if used + len(body.encode()) > self.config['limits']['max_bytes']:
                        raise Refusal('retained handling custody full; exact effects remain owned')
                    conn.execute('INSERT OR IGNORE INTO coordinator_retained_handling_v1 VALUES(?,?,?,?,?)',
                                 (capability, kind + ':' + source, basis, body, runtime.clock()))
                    conn.execute('UPDATE coordinator_retained_caps_v1 SET cursor=? WHERE id=?', (offset, capability))
            results.append(receipt)
        # A complete finite sweep revisits held entries on a later explicit call.
        if len(items) < 16:
            with self.opened() as conn:
                with self.store.write(conn):
                    self._continued(conn, runtime)
                    conn.execute('UPDATE coordinator_retained_caps_v1 SET cursor=0 WHERE id=?', (capability,))
        return {'capability': capability, 'handled': results, 'sweep_complete': len(items) < 16,
                'processing': 'unchanged; all original duties retained'}

    def _handle_input(self, runtime, source):
        event = runtime.one('SELECT id,role,hash,state,classification,classifier,ack,processed_at,hold,error FROM events WHERE id=?', (source,))
        responsibility = runtime.one('SELECT task,state,job FROM queue WHERE event=?', (source,))
        return {'source': source, 'role_owner': self.selected['owner'], 'software_actor': self.config['actor'],
                'event': event, 'responsibility': responsibility,
                'legacy_hold': runtime.one('SELECT legacy_hold FROM enrollments WHERE role=?', (self.role,))['legacy_hold'],
                'disposition': 'durable software triage; actual owner decision/held execution still outstanding; no ACK or processing stamp'}

    def _handle_retained(self, runtime, outbox):
        event = runtime.one('SELECT id,hash,state,processed_at,hold,error FROM events WHERE id=?', (outbox['event'],)) if outbox['event'] else None
        result = {'source': outbox['id'], 'source_hash': digest({k: outbox[k] for k in ('id', 'producer', 'recipient', 'kind', 'required', 'payload')}),
                  'role_owner': self.selected['owner'], 'software_actor': self.config['actor'],
                  'source_event': event, 'holds': {'outbox': outbox['hold'], 'legacy': runtime.one(
                      'SELECT legacy_hold FROM enrollments WHERE role=?', (self.role,))['legacy_hold']},
                  'disposition': 'held; actual native decisions, consumer processing and downstream effects remain outstanding'}
        if (outbox['kind'] not in CONTROL_KINDS or outbox['state'] == 'classification-pending'
                or outbox['hold'] or event and event['hold']):
            result['delivery'] = 'not attempted; executable work, classification or explicit source hold'
            return result
        try:
            # Reconcile before any send: committed/ambiguous effects never replay.
            row = self.reconcile_delivery(runtime, outbox) or self.post_delivery(runtime, outbox)
            # Managed Board delivery is the real software channel. No native queue
            # or active helper is borrowed to manufacture owner processing.
            result['delivery'] = row
        except (Refusal, OSError) as exc:
            result['delivery_error'] = type(exc).__name__ + ': ' + str(exc)[:1000]
        return result


def drain(runtime, authority, shared_rows, shared_payload_bytes, visits, seconds, emit, board_factory=RetainedBoard):
    """Finite actual software controller; no subprocess, native wake or models.

    Emit each genuine capability before visiting it. Partial issuance/effects
    stay with this original caller; an interrupted call must not be replayed.
    Current-capability metadata is available via retained-basis for owner pickup.
    """
    if type(seconds) is not int or not 1 <= seconds <= 3600 or type(visits) is not int or not 1 <= visits <= 4096:
        raise Refusal('finite original retained controller duration/visits required')
    summary = []
    expiry = runtime.clock() + seconds
    for role in runtime.config['roles']:
        board = board_factory(runtime.config, role)
        policy = {'basis': board.retained_basis(runtime), 'authority': authority, 'expires': expiry,
                  'max_shared_rows': shared_rows, 'max_shared_payload_bytes': shared_payload_bytes,
                  'max_runtime_rows': runtime.config['limits'].get('max_board_deliveries', runtime.config['limits']['max_events']),
                  'max_visits': visits}
        cap = board.delegate_retained(runtime, policy)
        emit({'role': role, 'phase': 'retained-authority', **cap})
        for _ in range(visits):
            result = board.retained_step(runtime, cap['capability'])
            progress = {'role': role, 'phase': 'retained-handling', 'capability': cap['capability'],
                        'sources': len(result['handled']), 'sweep_complete': result['sweep_complete'],
                        'delivery_errors': [{k: item[k] for k in ('source', 'delivery_error')} for item in result['handled'] if 'delivery_error' in item],
                        'processing': result['processing']}
            emit(progress)
            if result['sweep_complete']:
                break
        summary.append(progress)
    return {'roles': summary, 'meaning': 'finite retained software sweep only; no full cutover, processing or hold clearance'}
