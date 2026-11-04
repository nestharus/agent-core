"""Controlled protocol tests: every actor/budget here is explicitly fictional.

No native session/profile/turn fields or fixtures, no HOME substitution, no live
Board/catalog, model, helper, grant, service or external effect. The Board shell
and clock are fixtures; production retained logic and capacity checks execute
against only owned SQLite files. Native posting is a shell substitution, not
native/full Board qualification; native receiver fields remain NULL.
"""
from contextlib import contextmanager
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from coordinator_runtime.board_delivery import BoardDelivery
from coordinator_runtime.contracts import Refusal, digest, encode
from coordinator_runtime.retained import RetainedBoard, SCHEMA


class Runtime:
    def __init__(self, directory):
        self.path = directory / 'runtime.sqlite3'
        self.db = sqlite3.connect(self.path)
        self.db.row_factory = sqlite3.Row
        self.now = 1000.
        self.db.executescript('''
          CREATE TABLE enrollments(role,grant_id,intake,legacy_hold);
          CREATE TABLE events(id,role,hash,state,classification,classifier,ack,processed_at,hold,error,payload);
          CREATE TABLE queue(event,task,state,job);
          CREATE TABLE outboxes(id,role,producer,recipient,kind,required,payload,event,hold,state);
          INSERT INTO enrollments VALUES('Work','fictional-grant',0,'genuine effect hold represented fictionally');
          INSERT INTO events VALUES('fictional-input','Work',NULL,'queued',NULL,NULL,'done',NULL,NULL,NULL,'{"source":"fictional"}');
          INSERT INTO queue VALUES('fictional-input','work-integrator','queued',NULL);
        ''')
        self.db.execute('UPDATE events SET hash=?', (digest({'source': 'fictional'}),))
        self.config = {'actor': 'fictional-software-actor', 'roles': {'Work': {'owner': 'fictional-logical-owner', 'board_id': 'fictional-board'}},
                       'software_delegation': {'grantor': 'fictional-issuer', 'authority': 'fictional-prior-authority'},
                       'limits': {'max_board_deliveries': 512, 'max_events': 256, 'max_result_bytes': 262144, 'max_bytes': 1048576},
                       'delivery': {'recipients': {'Work': {'session': None}}}}
        self.db.commit()

    def clock(self):
        return self.now

    def one(self, sql, args=()):
        row = self.db.execute(sql, args).fetchone()
        return dict(row) if row else None

    def rows(self, sql, args=()):
        return [dict(r) for r in self.db.execute(sql, args)]

    def outbox(self, name='fictional-control', kind='alert'):
        self.db.execute('INSERT INTO outboxes VALUES(?,?,?,?,?,?,?,?,?,?)',
                        (name, 'Work', 'fictional-producer', 'Work', kind, 'settled', encode({'reason': name}), 'fictional-input', None, 'pending'))
        self.db.commit()


class BoardShell:
    def __init__(self):
        self.actor = 'fictional-issuer'

    def acting_session(self, expected):
        if self.actor != expected:
            raise Refusal('fixture actor refuses borrowing')
        return self.actor

    @contextmanager
    def write(self, conn):
        conn.execute('BEGIN IMMEDIATE')
        try:
            yield
            conn.commit()
        except BaseException:
            conn.rollback()
            raise

    def utc_now(self):
        return 'fictional-time'

    def bounded(self, *args, **kwargs):
        pass

    def notify(self, conn, recipients, post, thread, kind, title, actor, push):
        conn.execute('INSERT INTO notification_outbox(post_seq) VALUES(?)', (post,))


class ControlledBoard(RetainedBoard):
    def __init__(self, runtime, directory):
        self.config, self.role, self.selected = runtime.config, 'Work', runtime.config['roles']['Work']
        self.store = BoardShell()
        self.conn = sqlite3.connect(directory / 'board.sqlite3', isolation_level=None)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript('''
          CREATE TABLE coordinator_grants_v1(id,board_id,role,owner,actor,runtime,runtime_dev,runtime_ino,issued_by,authority,revoked);
          CREATE TABLE coordinator_software_grants_v1(grant_id,configuration);
          CREATE TABLE coordinator_deliveries_v1(id PRIMARY KEY,grant_id,owner,actor,producer,recipient,kind,required,payload,post,notice,state,created);
          CREATE TABLE posts(seq INTEGER PRIMARY KEY,author,recipient,topic,kind,text,ref,reply_to,created_at);
          CREATE TABLE threads(id,title,topic,author,created);
          CREATE TABLE thread_posts(thread,post);
          CREATE TABLE subscriptions(thread,actor,created);
          CREATE TABLE notification_outbox(notification_id INTEGER PRIMARY KEY,post_seq);
        ''' + SCHEMA)
        stat = runtime.path.stat()
        self.conn.execute('INSERT INTO coordinator_grants_v1 VALUES(?,?,?,?,?,?,?,?,?,?,?)',
            ('fictional-grant', 'fictional-board', 'Work', self.selected['owner'], self.config['actor'], str(runtime.path),
             stat.st_dev, stat.st_ino, 'fictional-issuer', 'fictional-prior-authority', 'fictional-revocation'))
        self.conn.execute('INSERT INTO coordinator_software_grants_v1 VALUES(?,?)', ('fictional-grant', digest(self.config)))
        self.runtime = runtime

    @contextmanager
    def opened(self, **kwargs):
        # Only membership/catalog transport is substituted; no native actor.
        yield self.conn

    def _delivery_grant(self, conn, runtime, outbox):
        return self._grant(conn, runtime), self.config['delivery']['recipients'][outbox['recipient']]

    def _delivery_record(self, conn, row):
        return {k: row[k] for k in ('id', 'state', 'post', 'notice', 'payload', 'producer')}

    def post_delivery(self, runtime, outbox):
        with self.store.write(self.conn):
            grant, target = self._delivery_grant(self.conn, runtime, outbox)
            self._delivery_capacity(self.conn, outbox)
            # Controlled transport shell: no synthetic native receiver/session.
            post = self.conn.execute('INSERT INTO posts(text) VALUES(?)', ('fictional control transport',)).lastrowid
            self.conn.execute('INSERT INTO coordinator_deliveries_v1(id,grant_id,producer,payload,post,state) VALUES(?,?,?,?,?,?)',
                              (outbox['id'], grant['id'], outbox['producer'], outbox['payload'], post, 'posted'))
        return self._delivery_record(self.conn, dict(self.conn.execute('SELECT * FROM coordinator_deliveries_v1 WHERE id=?', (outbox['id'],)).fetchone()))

    def reconcile_delivery(self, runtime, outbox):
        row = self.conn.execute('SELECT * FROM coordinator_deliveries_v1 WHERE id=?', (outbox['id'],)).fetchone()
        if row and (row['payload'] != outbox['payload'] or row['producer'] != outbox['producer']):
            raise Refusal('fixture refuses different immutable source')
        return self._delivery_record(self.conn, dict(row)) if row else None


class RetainedTests(unittest.TestCase):
    def setUp(self):
        self.directory = Path(tempfile.mkdtemp(dir='/fixtures'))
        self.runtime = Runtime(self.directory)
        self.runtime.outbox()
        self.board = ControlledBoard(self.runtime, self.directory)

    def tearDown(self):
        self.board.conn.close()
        self.runtime.db.close()
        # Retain every owned fixture, including failed runs; no cleanup effect.

    def policy(self, **changes):
        value = {'basis': self.board.retained_basis(self.runtime), 'authority': 'fictional bounded continuing selection',
                 'expires': self.runtime.now + 60, 'max_shared_rows': 1024, 'max_shared_payload_bytes': 1048576,
                 'max_runtime_rows': 512, 'max_visits': 10}
        value.update(changes)
        return value

    def issue(self, **changes):
        key = self.board.delegate_retained(self.runtime, self.policy(**changes))['capability']
        self.board.capability = key
        return key

    def seed(self, count, grant='fictional-foreign-grant'):
        self.board.conn.executemany('INSERT INTO coordinator_deliveries_v1(id,grant_id,payload) VALUES(?,?,?)',
            [('fictional-resident-' + str(i), grant, 'retained') for i in range(count)])

    def test_shared_512_does_not_consume_runtime_entitlement(self):
        self.seed(512)
        outbox = self.runtime.one('SELECT * FROM outboxes')
        with self.assertRaises(Refusal):
            BoardDelivery._delivery_capacity(self.board, self.board.conn, outbox)
        key = self.issue()
        before = {t: self.runtime.rows('SELECT * FROM ' + t) for t in ('enrollments', 'events', 'queue', 'outboxes')}
        result = self.board.retained_step(self.runtime, key)
        self.assertEqual(len(result['handled']), 2)  # Input AND its control duty visited.
        self.assertEqual(self.board.conn.execute('SELECT COUNT(*) FROM posts').fetchone()[0], 1)
        self.assertEqual(self.board.conn.execute('SELECT COUNT(*) FROM coordinator_deliveries_v1').fetchone()[0], 513)
        self.assertEqual(before, {t: self.runtime.rows('SELECT * FROM ' + t) for t in before})
        self.board.retained_step(self.runtime, key)
        self.assertEqual(self.board.conn.execute('SELECT COUNT(*) FROM posts').fetchone()[0], 1)
        self.assertEqual(self.board.conn.execute('SELECT COUNT(*) FROM coordinator_retained_handling_v1').fetchone()[0], 2)

    def test_row_pressure_rolls_back_without_losing_obligation(self):
        self.seed(512)
        key = self.issue(max_shared_rows=512)
        result = self.board.retained_step(self.runtime, key)
        self.assertIn('delivery_error', result['handled'][1])
        self.assertEqual(self.board.conn.execute('SELECT COUNT(*) FROM posts').fetchone()[0], 0)
        self.assertIsNone(self.runtime.one('SELECT processed_at FROM events')['processed_at'])

    def test_payload_pressure_and_logical_pressure_are_independent(self):
        self.seed(2, 'fictional-grant')
        key = self.issue(max_runtime_rows=2)
        result = self.board.retained_step(self.runtime, key)
        self.assertIn('delivery_error', result['handled'][1])
        self.board.revoke_retained(self.runtime, key)
        key = self.issue(max_shared_payload_bytes=16)
        result = self.board.retained_step(self.runtime, key)
        self.assertIn('delivery_error', result['handled'][1])
        self.assertEqual(self.board.conn.execute('SELECT COUNT(*) FROM posts').fetchone()[0], 0)

    def test_expiry_revocation_and_original_revocation_are_distinct(self):
        key = self.issue()
        with self.assertRaises(Refusal):
            self.issue()
        self.runtime.now += 61
        with self.assertRaises(Refusal):
            self.board.retained_step(self.runtime, key)
        self.board.revoke_retained(self.runtime, key)
        self.runtime.now = 1000
        with self.assertRaises(Refusal):
            self.board.retained_step(self.runtime, key)
        self.assertEqual(self.board.conn.execute('SELECT revoked FROM coordinator_grants_v1').fetchone()[0], 'fictional-revocation')
        self.assertEqual(self.runtime.one('SELECT intake FROM enrollments')['intake'], 0)

    def test_wrong_issuer_configuration_and_stale_basis_refuse(self):
        self.board.store.actor = 'fictional-other-issuer'
        with self.assertRaises(Refusal):
            self.issue()
        self.board.store.actor = 'fictional-issuer'
        policy = self.policy()
        self.runtime.outbox('fictional-new-outbox')
        with self.assertRaises(Refusal):
            self.board.delegate_retained(self.runtime, policy)
        key = self.issue()
        self.runtime.db.execute("UPDATE outboxes SET payload='changed immutable source'")
        self.runtime.db.commit()
        with self.assertRaises(Refusal):
            self.board.retained_step(self.runtime, key)

    def test_native_or_active_grant_cannot_be_taken_over(self):
        self.board.conn.execute('UPDATE coordinator_grants_v1 SET revoked=NULL')
        with self.assertRaises(Refusal):
            self.issue()
        self.board.conn.execute("UPDATE coordinator_grants_v1 SET revoked='fictional-revocation',issued_by='fictional-other-owner'")
        with self.assertRaises(Refusal):
            self.issue()

    def test_no_executable_work_or_explicit_hold_bypass(self):
        self.runtime.db.execute("UPDATE outboxes SET kind='work'")
        self.runtime.db.commit()
        key = self.issue(max_visits=1)
        result = self.board.retained_step(self.runtime, key)
        self.assertIn('not attempted', result['handled'][1]['delivery'])
        self.assertEqual(self.board.conn.execute('SELECT COUNT(*) FROM posts').fetchone()[0], 0)
        with self.assertRaises(Refusal):
            self.board.retained_step(self.runtime, key)

    def test_retained_rows_across_grants_share_one_runtime_entitlement(self):
        grant = dict(self.board.conn.execute('SELECT * FROM coordinator_grants_v1').fetchone())
        grant['id'] = 'fictional-second-role-grant'
        grant['role'] = 'fictional-peer-role'
        self.board.conn.execute('INSERT INTO coordinator_grants_v1 VALUES(?,?,?,?,?,?,?,?,?,?,?)', tuple(grant.values()))
        self.seed(2, grant['id'])
        key = self.issue(max_runtime_rows=2)
        result = self.board.retained_step(self.runtime, key)
        self.assertIn('delivery_error', result['handled'][1])
        self.assertEqual(self.board.conn.execute('SELECT COUNT(*) FROM posts').fetchone()[0], 0)

    def test_capacity_rechecks_competing_residency_after_authorization(self):
        key = self.issue(max_shared_rows=1)
        self.seed(1)
        result = self.board.retained_step(self.runtime, key)
        self.assertIn('delivery_error', result['handled'][1])
        self.assertEqual(self.board.conn.execute('SELECT COUNT(*) FROM posts').fetchone()[0], 0)

    def test_finite_pages_reach_later_sources_and_keep_held_inputs(self):
        for i in range(19):
            self.runtime.outbox('fictional-extra-control-' + str(i))
        self.runtime.db.execute("UPDATE events SET hold='fictional source hold'")
        self.runtime.db.commit()
        key = self.issue()
        first = self.board.retained_step(self.runtime, key)
        second = self.board.retained_step(self.runtime, key)
        self.assertEqual(len(first['handled']), 16)
        self.assertEqual(len(second['handled']), 5)
        self.assertEqual(self.board.conn.execute('SELECT COUNT(*) FROM coordinator_retained_handling_v1').fetchone()[0], 21)
        self.assertEqual(self.board.conn.execute('SELECT COUNT(*) FROM posts').fetchone()[0], 0)
        self.assertIsNone(self.runtime.one('SELECT processed_at FROM events')['processed_at'])

    def test_configuration_and_original_file_identity_drift_refuse(self):
        key = self.issue()
        self.config = self.runtime.config
        self.config['limits']['max_events'] += 1
        with self.assertRaises(Refusal):
            self.board.retained_step(self.runtime, key)
        self.config['limits']['max_events'] -= 1
        self.board.conn.execute('UPDATE coordinator_grants_v1 SET runtime_ino=runtime_ino+1')
        with self.assertRaises(Refusal):
            self.board.retained_step(self.runtime, key)

    def test_changed_original_payload_refuses_even_with_unchanged_stored_hash(self):
        key = self.issue()
        self.runtime.db.execute('UPDATE events SET payload=?', (encode({'source': 'changed fictional input'}),))
        self.runtime.db.commit()
        with self.assertRaises(Refusal):
            self.board.retained_step(self.runtime, key)

    def test_ambiguous_committed_delivery_requires_exact_attribution(self):
        key = self.issue()
        outbox = self.runtime.one('SELECT * FROM outboxes')
        self.board.conn.execute('INSERT INTO coordinator_deliveries_v1 VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',
            (outbox['id'], 'fictional-grant', 'fictional-logical-owner', self.runtime.config['actor'], outbox['producer'],
             None, outbox['kind'], outbox['required'], outbox['payload'], 99, None, 'ambiguous', 'fictional-time'))
        row = RetainedBoard.reconcile_delivery(self.board, self.runtime, outbox)
        self.assertEqual(row['state'], 'ambiguous')
        self.board.conn.execute("UPDATE coordinator_deliveries_v1 SET required='acknowledged'")
        with self.assertRaises(Refusal):
            RetainedBoard.reconcile_delivery(self.board, self.runtime, outbox)

    def test_ordinary_insert_refuses_before_transport_side_effect(self):
        self.seed(512)
        ordinary = BoardDelivery()
        ordinary.config = self.runtime.config
        with self.assertRaises(Refusal):
            ordinary._insert_delivery(self.board.conn, {}, {}, self.runtime.one('SELECT * FROM outboxes'))
        self.assertEqual(self.board.conn.execute('SELECT COUNT(*) FROM posts').fetchone()[0], 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
