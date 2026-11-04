"""Retained own fictional stores only; no shared fixtures or identity changes."""
import copy
import json
import os
from pathlib import Path
import unittest

from coordinator_runtime import admitted, capacity, progress
from coordinator_runtime.contracts import Backpressure, Refusal, digest, encode
from coordinator_runtime.dispatcher import Dispatcher
from coordinator_runtime.store import Store

OWNER = '00000000-0000-4000-8000-000000000001'
ACTOR = '00000000-0000-4000-8000-000000000002'


class NoModels:
    async def run(self, *args, **kwargs):
        raise AssertionError('no actual model/native/provider invocation')


class Admitted58(unittest.TestCase):
    def setUp(self):
        self.root = Path(os.environ['CAPACITY58_FIXTURES']) / self._testMethodName
        self.root.mkdir(parents=True, mode=0o700, exist_ok=False)
        self.now = 1000.
        roles = ['Work', 'Branch', 'Reviews', 'QA']
        self.config = {
            'actor': ACTOR, 'profiles': ['.codex2'], 'state_dir': str(self.root/'state'),
            'execution_pool_routes': str(self.root/'unused-fictional-routes.toml'),
            'roles': {r: {'owner': OWNER, 'profile': '.codex2', 'legacy_hold': None, 'routes': [r+'-terminal']} for r in roles},
            'tasks': {r+'-terminal': {'role': r, 'phase': 'execution' if r == 'QA' else 'proposer',
                                    'effects': 'none', 'responses': {}, 'binding': {'fixture': 'no model'},
                                    'profile': '.codex2', 'allowed_handoffs': ['Work'], 'delivery_required': True} for r in roles},
            'classifier': {'binding': {'fixture': 'no model'}, 'profile': '.codex2'},
            'diagnosis': {'binding': {'fixture': 'no model'}, 'profile': '.codex2'},
            'finite_service': {'tasks': [r+'-terminal' for r in roles], 'max_admitted': 4},
            'limits': {'max_events': 1000, 'max_jobs': 10, 'max_attempts': 4000, 'max_outboxes': 1000,
                       'max_alerts': 1441, 'max_bytes': 24*1024*1024, 'max_files': 100, 'max_result_bytes': 4096},
            'deadlines': {'alert_interval': 60, 'ack': 30, 'backlog': 60, 'bind': 10, 'task': 60},
            'delivery': {'alert_role': 'Work', 'alert_recipient': 'Work', 'recipients': {r: {'session': OWNER} for r in roles}}}
        if self._testMethodName == 'test_tail_capacity_refuses_before_expansion':
            self.config['limits']['max_attempts'] = 10
        if self._testMethodName == 'test_recurring_controller_over_retention_horizon':
            self.config['limits'].update(max_alerts=1600, max_outboxes=1600)
        self.store = Store(self.config, clock=lambda: self.now)
        self.addCleanup(self.store.close)
        for role in roles:
            self.store.enroll(role, {'owner': OWNER, 'actor': ACTOR, 'id': 'fictional-'+role, 'cutover': 0})
        self.trace = (self.root/'sql-trace.txt').open('w')
        self.addCleanup(self.trace.close)
        self.store.db.set_trace_callback(lambda sql: self.trace.write(sql+'\n'))

    def event(self, role='Work', key='e1'):
        return {'id': key, 'role': role, 'recipient': OWNER, 'kind': 'board', 'package': None, 'body': 'fictional terminal input',
                'allowed_tasks': [role+'-terminal']}

    def runtime(self, custodians=None):
        return Dispatcher(self.store, models=NoModels(), boards={}, custodians=custodians)

    def before(self, label):
        (self.root/(label+'.json')).write_text(encode({t: self.store.rows('SELECT * FROM '+t)
            for t in ('events', 'alerts', 'outboxes', 'duty_accounts', 'meta')}))

    def occurrence(self, settled=True):
        with self.store.tx():
            key = 'a'+str(self.store.db.execute('SELECT COUNT(*) FROM alerts').fetchone()[0])
            self.store.db.execute('INSERT INTO alerts VALUES(?,?,?,?,?,NULL)', (key, 'fictional', 'unchanged', self.now, '{}'))
            self.store._outbox('Work', 'Work', 'alert', {}, alert=key, key='d'+key)
        if settled:
            receipt = {'id': 'd'+key, 'recipient': OWNER, 'state': 'settled', 'processed_at': self.now,
                       'processing': {'evidence': 'controlled fictional processing'},
                       'settlement': {'evidence': 'controlled fictional settlement'},
                       'control_receipt': {'pending': False},
                       'transport': {'route': 'managed', 'delivery_state': 'acknowledged'}}
            self.store.delivery_observed('d'+key, receipt)
            self.store.process_alert(key, OWNER, {'evidence': 'controlled fictional substantive processing'})
        return key

    def custodian(self, *, holds=None, sink_fail=False):
        store, root = self.store, self.root
        class FictionalBoard:
            def retire_alert(self, runtime, occurrence, receipt):
                outbox = capacity.retirement_basis(runtime, occurrence)[1]
                return capacity.retire(runtime, occurrence, OWNER, receipt, json.loads(outbox['board_receipt']))
        def qualify(runtime, alert, outbox, basis):
            return {'basis': basis, 'qualified_at': self.now,
                    'evidence': 'controlled fictional custodian qualifies all nine scopes',
                    'holds': {name: (['fictional hold'] if name == holds else []) for name in capacity.HOLDS}}
        def retain(record):
            if sink_fail:
                raise OSError('fictional evidence sink unavailable')
            files = list(root.glob('retained-*.json'))
            path = root/('retained-'+str(len(files))+'.json')
            path.write_text(encode(record))
            return str(path)
        return progress.OwnerAlertCustodian(FictionalBoard(), qualify, retain)

    def test_all_four_role_intakes_reserve_full_count_tail(self):
        footprint = admitted.plan(self.config)
        for index, role in enumerate(self.config['roles']):
            self.assertTrue(self.store.ingest(self.event(role, str(index)), cursor=index+1))
        accounts = self.store.rows('SELECT * FROM duty_accounts')
        self.assertEqual(len(accounts), 4)
        self.assertEqual(admitted.reserved(self.store)['attempts'], 4*footprint['attempts'])
        self.assertEqual(admitted.reserved(self.store)['events'], 4*(footprint['events']-1))
        self.assertTrue(all(r['owner'] == OWNER and r['configuration'] == digest(self.config) for r in accounts))

    def test_refused_whole_tail_keeps_cursor_and_original_source(self):
        for index in range(4):
            self.store.ingest(self.event(key=str(index)), cursor=index+1)
        before = self.store.rows('SELECT * FROM duty_accounts')
        with self.assertRaises(Backpressure):
            self.store.ingest(self.event(key='too-many'), cursor=99)
        self.assertEqual(self.store.one("SELECT seq FROM cursors WHERE role='Work'")['seq'], 4)
        self.assertEqual(self.store.rows('SELECT * FROM duty_accounts'), before)
        self.assertFalse(self.store.one("SELECT id FROM events WHERE id='too-many'"))

    def test_tail_capacity_refuses_before_expansion(self):
        with self.assertRaisesRegex(Backpressure, 'complete downstream attempts'):
            self.store.ingest(self.event(), cursor=99)
        self.assertEqual(self.store.rows('SELECT * FROM events'), [])
        self.assertEqual(self.store.rows('SELECT * FROM duty_accounts'), [])
        self.assertEqual(self.store.one("SELECT seq FROM cursors WHERE role='Work'")['seq'], 0)

    def test_unaccounted_prior_duty_blocks_only_prospective_expansion(self):
        original = self.event(key='old-unaccounted')
        self.store.db.execute('INSERT INTO events(id,role,payload,hash,received) VALUES(?,?,?,?,?)',
                             (original['id'], 'Work', encode(original), digest(original), self.now))
        with self.assertRaisesRegex(Backpressure, 'unaccounted existing outgoing'):
            self.store.ingest(self.event(), cursor=99)
        self.assertEqual(self.store.rows('SELECT * FROM duty_accounts'), [])
        self.assertEqual(self.store.event('old-unaccounted'), original)
        self.assertEqual(self.store.one("SELECT seq FROM cursors WHERE role='Work'")['seq'], 0)

    def test_recursive_batched_effect_publication_and_foreign_classes_refuse(self):
        for field, value in [('responses', {'complete': ['Work-terminal']}), ('phase', 'integrator'),
                             ('effects', 'owner-reconcile'), ('routine_completion', {'targets': []}),
                             ('software_handoffs', {'Work': ['Work-terminal']})]:
            candidate = copy.deepcopy(self.config)
            candidate['tasks']['Work-terminal'][field] = value
            with self.assertRaises(Refusal):
                admitted.policy(candidate)
        with self.assertRaises(Refusal):
            self.store.ingest({**self.event(), 'parent': 'foreign'})
        with self.assertRaises(Refusal):
            self.store.ingest({**self.event(), 'allowed_tasks': ['QA-terminal']})
        self.assertEqual(self.store.rows('SELECT * FROM duty_accounts'), [])

    def test_spending_is_atomic_and_unowned_producer_cannot_steal_credits(self):
        self.store.ingest(self.event())
        old = admitted.reserved(self.store)
        with self.assertRaises(RuntimeError):
            with self.store.tx():
                self.store._outbox('Work', 'Work', 'question', {}, event='e1', key='rolled-back')
                raise RuntimeError('controlled rollback')
        self.assertEqual(admitted.reserved(self.store), old)
        self.assertFalse(self.store.one('SELECT id FROM outboxes'))
        with self.store.tx():
            self.store._outbox('Work', 'Work', 'question', {}, event='e1', key='owed')
        self.assertEqual(admitted.reserved(self.store)['outboxes'], old['outboxes']-1)
        # Fictional pre-existing competition takes the unreserved capacity.
        remaining = admitted.reserved(self.store)['outboxes']
        with self.store.tx():
            for i in range(self.config['limits']['max_outboxes']-remaining-1):
                self.store.db.execute('INSERT INTO outboxes(id,role,producer,recipient,kind,required,payload,created) VALUES(?,\'Work\',?,\'Work\',\'question\',\'settled\',\'{}\',?)', ('legacy'+str(i), ACTOR, self.now))
        with self.assertRaises(Backpressure):
            with self.store.tx():
                self.store._outbox('Work', 'Work', 'question', {}, key='unowned')
        with self.store.tx():
            self.store._outbox('Work', 'Work', 'question', {}, event='e1', key='still-owed')

    def test_completion_timestamps_do_not_release_accounts(self):
        self.store.ingest(self.event())
        before = admitted.reserved(self.store)
        self.store.db.execute("UPDATE events SET processed_at=?,state='processed' WHERE id='e1'", (self.now,))
        self.now += 90000
        self.runtime().custodian_progress()
        self.assertEqual(admitted.reserved(self.store), before)

    def test_recurring_missing_custodian_retains_rows_and_first_gap(self):
        key = self.occurrence()
        self.now += 86401
        runtime = self.runtime()
        first = runtime.custodian_progress()
        self.assertEqual(first['retired'], 0)
        self.assertIn('no actual owner', first['failures'][0]['reason'])
        self.now += 1
        second = runtime.custodian_progress()
        self.assertEqual(second['passes'], 2)
        self.assertEqual(first['first_gap'], second['first_gap'])
        self.assertTrue(self.store.one('SELECT id FROM alerts WHERE id=?', (key,)))

    def test_unknown_processing_retention_holds_and_sink_failure_refuse(self):
        key = self.occurrence(False)
        self.now += 90000
        for custodian in [self.custodian(), self.custodian(sink_fail=True)]:
            self.now += 1
            result = self.runtime({'Work': custodian}).custodian_progress()
            self.assertEqual(result['retired'], 0)
        self.assertTrue(self.store.one('SELECT id FROM alerts WHERE id=?', (key,)))

    def test_evidence_sink_failure_prevents_qualified_retirement(self):
        key = self.occurrence()
        self.now += 86401
        self.before('before-failed-evidence-sink')
        result = self.runtime({'Work': self.custodian(sink_fail=True)}).custodian_progress()
        self.assertEqual(result['retired'], 0)
        self.assertIn('sink unavailable', result['failures'][0]['reason'])
        self.assertTrue(self.store.one('SELECT id FROM alerts WHERE id=?', (key,)))

    def test_complete_local_task_handoff_and_delivery_classification_charge_one_account(self):
        class FictionalAllocation:
            def allocate(self):
                return {'profile': '.codex2', 'meaning': 'fictional in-memory allocation; no actual pool'}
        self.store.execution_pool = FictionalAllocation()
        self.store.ingest(self.event())
        classifier, event = self.store.claim_classification()
        self.store.begin(classifier, {'fixture': True})
        self.store.collect(classifier, {'exit': 0, 'capture': 'complete', 'cleanup': 'no-session-created',
            'result': {'event_id': event['id'], 'task': 'Work-terminal', 'package': None, 'reason': 'controlled fixture routing'}})
        self.store.commit_classification(classifier)
        self.store.ack_state('e1', 'internal')
        job = self.store.reserve()
        attempt = self.store.start_job(job['id'], job['token'])
        self.store.begin(attempt, {'fixture': True})
        answer = {'semantic': 'DONE', 'category': 'complete', 'summary': 'controlled fixture return',
                  'findings': [], 'failures': [], 'unknowns': [], 'artifacts': [],
                  'handoffs': [{'recipient': 'Work', 'kind': 'question', 'text': 'controlled downstream duty',
                                'ref': None, 'required': 'settled'}]}
        self.store.collect(attempt, {'exit': 0, 'capture': 'complete', 'cleanup': 'no-session-created', 'result': answer})
        response = self.store.finish_job(job['id'], job['token'])
        self.assertIsNotNone(response)
        self.assertEqual(self.store.job(job['id'])['state'], 'awaiting-delivery')
        self.assertEqual(len(self.store.rows('SELECT * FROM duty_accounts')), 1)
        self.assertEqual(admitted.reserved(self.store)['jobs'], 0)
        self.assertEqual(admitted.reserved(self.store)['outboxes'], admitted.plan(self.config)['outboxes']-1)
        classifier, event = self.store.claim_classification()
        self.assertEqual(event['id'], response)
        self.store.begin(classifier, {'fixture': True})
        self.store.collect(classifier, {'exit': 0, 'capture': 'complete', 'cleanup': 'no-session-created',
            'result': {'event_id': response, 'task': '@delivery', 'package': None, 'reason': 'controlled delivery release'}})
        self.store.commit_classification(classifier)
        self.assertEqual(self.store.one('SELECT state FROM outboxes')['state'], 'pending')
        self.assertIsNone(self.store.one('SELECT processed_at FROM events WHERE id=?', (response,))['processed_at'])
        self.assertEqual(admitted.reserved(self.store)['attempts'], admitted.plan(self.config)['attempts']-3)

    def test_qualified_recurring_retirement_requires_every_hold_and_24h(self):
        key = self.occurrence()
        self.before('before-fictional-retirement')
        runtime = self.runtime({'Work': self.custodian()})
        self.assertEqual(runtime.custodian_progress()['retired'], 0)
        self.now += 86400
        for hold in capacity.HOLDS:
            self.now += 1
            self.assertEqual(self.runtime({'Work': self.custodian(holds=hold)}).custodian_progress()['retired'], 0)
        self.now += 1
        result = runtime.custodian_progress()
        self.assertEqual(result['retired'], 1)
        self.assertIsNotNone(result['first_gap'])
        self.assertFalse(self.store.one('SELECT id FROM alerts WHERE id=?', (key,)))
        self.assertGreaterEqual(len(list(self.root.glob('retained-*.json'))), 2)

    def test_fixed_frontier_visits_later_rows_despite_held_prefix(self):
        for _ in range(20):
            self.occurrence(False)
        first = self.runtime().custodian_progress()
        self.assertEqual(first['visited'], 16)
        self.now += 1
        second = self.runtime().custodian_progress()
        self.assertEqual(second['visited'], 4)
        self.assertNotEqual(first['failures'][0]['occurrence'], second['failures'][0]['occurrence'])
        self.assertEqual(len(self.store.rows('SELECT id FROM alerts')), 20)

    def test_recurring_controller_over_retention_horizon(self):
        # Controlled software clock: one unchanged violation per minute, with
        # fictional immediate processing and all-hold qualification. The
        # recurring controller, not an occurrence-selected manual drain,
        # chooses fair pages twice per minute. No actual throughput claim.
        self.store.record_operational_error('unchanged', {'error': 'same fictional violation'})
        runtime = self.runtime({'Work': self.custodian()})
        created, retired, peak = set(), 0, 0
        for minute in range(1501):
            self.now = 1000 + minute*60
            occurrences = self.store.emit_alerts()
            self.assertEqual(len(occurrences), 1)
            key = occurrences[0]['id']
            self.assertNotIn(key, created)
            created.add(key)
            outbox = self.store.one('SELECT * FROM outboxes WHERE alert=?', (key,))
            receipt = {'id': outbox['id'], 'state': 'settled', 'recipient': OWNER, 'processed_at': self.now,
                       'processing': {'evidence': 'fictional controlled processing'},
                       'settlement': {'evidence': 'fictional controlled settlement'},
                       'control_receipt': {'pending': False},
                       'transport': {'route': 'managed', 'delivery_state': 'acknowledged'}}
            self.store.delivery_observed(outbox['id'], receipt)
            self.store.process_alert(key, OWNER, {'evidence': 'fictional controlled substantive processing'})
            for offset in (0, 30):
                self.now = 1000 + minute*60 + offset
                retired += runtime.custodian_progress()['retired']
            peak = max(peak, len(self.store.rows('SELECT id FROM alerts')))
        retained = self.store.rows('SELECT id FROM alerts')
        self.assertEqual(len(created), 1501)
        self.assertGreater(retired, 0)
        self.assertEqual(len(retained)+retired, 1501)
        self.assertLessEqual(peak, 1600)
        self.assertIsNone(capacity.service(self.store)['gap_since'])
        usage = self.store.usage()
        self.assertLess(usage['bytes'], self.config['limits']['max_bytes'])
        (self.root/'envelope.json').write_text(encode({'created': len(created), 'retired': retired,
            'retained': len(retained), 'peak': peak, 'usage': usage, 'minutes': 1500,
            'conditions': 'software clock, fictional processing/qualification, no actual custodian or Board',
            'first_gap_is_retirement_unavailable_before_24h': runtime.custodian_progress()}))


if __name__ == '__main__':
    unittest.main()
