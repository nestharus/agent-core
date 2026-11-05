"""Conditional recycled-row protocol fiction, never an actual runtime history.

Production transactions, retirement, collection/classification, response writers
and Work reservation execute in the positive-mount network-off sandbox. NULL
native fields and synthetic collection outcomes do not qualify an encounter.
"""
import json
import sqlite3
import unittest
from unittest.mock import patch

from coordinator_runtime import configuration, processing, prospective, retirement, windows
from coordinator_runtime.cleanup import sweep
from coordinator_runtime.contracts import Refusal, SOL, digest, encode
import test_allocation332 as allocation


class Birth(unittest.TestCase):
    def setUp(self):
        self.c = allocation.Continuing(methodName='runTest')
        self.addCleanup(self.c.doCleanups)
        original = allocation.fixture.engine_config
        def configured(directory):
            value = original(directory)
            value['tasks']['wp']['responses'] = {'proposal': ['wp']}
            return value
        with patch.object(allocation.fixture, 'engine_config', side_effect=configured):
            self.c.setUp()
        self.f, self.s = self.c.f, self.c.s
        self.originals = {table: self.s.rows('SELECT * FROM '+table) for table in
                          ('events','processing_source_positions','outboxes','enrollments','jobs','attempts')}
        self.grants = {t:[tuple(r) for r in self.f.conn.execute('SELECT * FROM '+t)]
                       for t in ('coordinator_grants_v1','coordinator_software_grants_v1')}
        for n in range(4):
            self.f.conn.execute("INSERT INTO posts(author,recipient,topic,kind,text,created_at) VALUES('fictional-Work','fictional-Work','fictional','status','fixture frontier','fictional-time')")
        self.c.issue()
        self.frontier = processing.source_boundary(self.s)
        if self._testMethodName != 'test_nonrecycled_normal_paths':
            self.retire_history()
        self.assertEqual(processing.source_boundary(self.s), self.frontier)
        self.assertEqual(self.s.one('SELECT MAX(rowid) AS n FROM events')['n'], 4)
        processing.revoke(self.s, self.f.boards, self.s.processing.key)
        self.f.transition()
        self.s = self.c.s = self.f.runtime
        self.s.clock = lambda: 90000.
        selected = self.c.selection()
        selected['service']['allocations']['expires'] = 100000.
        self.key = self.c.issue(selected)
        self.boundary = configuration.selected(self.s)['event_boundary']
        self.assertEqual(self.boundary, self.frontier)
        self.assert_originals()

    def retire_history(self):
        # Real retirement APIs with fictional no-effect completed episodes.
        # Synthetic collection and simulated clocks assert no real END,
        # customer processing, custodian qualification or elapsed retention.
        for n in range(4):
            source = self.new('fictional-disposable-'+str(n))
            self.classify(source['id'], 'wp')
            job = self.s.reserve()
            self.assertIsNotNone(job)
            self.task_attempt(job, 'complete')
            self.assertIsNone(self.s.finish_job(job['id'], job['token']))
            self.assertEqual(self.s.one('SELECT processed_at FROM events WHERE id=?', (source['id'],)), {'processed_at':1000.})
        self.s.clock = lambda: 90000.
        sweep(self.s)
        self.frontier = processing.source_boundary(self.s)
        for n in range(4):
            source = 'fictional-disposable-'+str(n)
            current = retirement.basis(self.s, source)
            receipt = {'basis':current['basis'], 'qualified_at':self.s.clock(),
                       'evidence':'fictional fixture custodians; no actual completion/retention claim'}
            from coordinator_runtime.capacity import HOLDS
            receipt['holds'] = {h:[] for h in HOLDS}
            for name in ('sources','results'):
                receipt[name] = {key:{'hash':value,'custodian':'fictional-custodian',
                                     'evidence':'synthetic fixture conservation only',
                                     'disposition':'producer-owned-disposable'} for key,value in current[name].items()}
            result = retirement.apply(self.s, source, 'fictional-Work', receipt)
            self.assertEqual(result['retired']['members']['events'], [source])

    def snapshot(self):
        return {t:self.s.rows('SELECT * FROM '+t) for t in
                ('events','processing_source_positions','processing_control_returns','input_resolutions',
                 'queue','jobs','attempts','outboxes','service_windows','service_window_allocations',
                 'processing_capabilities','sqlite_sequence','duty_accounts','source_custody','results')}

    def assert_originals(self):
        self.assertEqual(self.s.one('SELECT * FROM service_windows WHERE number=1'),self.c.old_window)
        for table,rows in self.grants.items():
            self.assertEqual([tuple(r) for r in self.f.conn.execute('SELECT * FROM '+table)],rows)
        for table, rows in self.originals.items():
            field = 'role' if table == 'enrollments' else 'event' if table == 'processing_source_positions' else 'id'
            self.assertEqual([self.s.one('SELECT * FROM '+table+' WHERE '+field+'=?', (r[field],)) for r in rows], rows)
        self.assertTrue(all(r['profile'] is None and r['session'] is None and r['turn'] is None
                            for r in self.s.rows('SELECT profile,session,turn FROM attempts')))

    def new(self, name='fictional-future'):
        value = self.c.new_event(name)
        self.s.ingest(value)
        return value

    def collect(self, attempt, result, tools=False):
        self.s.begin(attempt, {'fixture':'synthetic protocol return; no worker encounter'})
        self.s.collect(attempt, {'exit':0,'capture':'complete','cleanup':'no-session-created','result':result,
                                'detail':{'tool_completion':{'complete':True,'items':[],
                                          'nonzero_completions':[],'unknown_types':[]}} if tools else {}})

    def classify(self, event, task):
        claimed = self.s.claim_classification()
        self.assertIsNotNone(claimed, 'fresh response must reach actual classifier admission')
        attempt, actual = claimed
        self.assertEqual(actual['id'], event)
        self.collect(attempt, {'event_id':event, 'task':task, 'package':actual.get('package'),
                               'reason':'fictional full source classification'})
        self.s.commit_classification(attempt)
        self.s.ack_state(event, 'internal')
        return attempt

    def task_attempt(self, job, category='proposal'):
        attempt = self.s.start_job(job['id'], job['token'])
        self.f.boards[job['role']].bind_software_attempt(self.s, self.s.job(job['id']), attempt, None)
        self.collect(attempt, {'semantic':'DONE','category':category,'summary':'fictional bounded return',
                               'findings':[],'failures':[],'unknowns':[],'artifacts':[],
                               'handoffs':[],'no_handoff_reason':'fictional internal result only'}, tools=True)
        return attempt

    def task_source(self, category='proposal'):
        event = self.new()
        self.classify(event['id'], 'wp')
        job = self.s.reserve()
        self.assertIsNotNone(job)
        self.task_attempt(job, category)
        return event, job

    def control_source(self):
        event = self.new('fictional-control')
        self.classify(event['id'], '@control')
        receipt = {'source_hash':digest(event),'mode':'control','task':None,'package':None,
                   'related_event':None,'related_job':None,'reason':'fictional control understood',
                   'evidence':['fictional whole input'],'remaining_obligations':[]}
        with self.s.tx():
            attempt = self.s._attempt('input-control', event['id'], None, SOL, None)
            self.s.db.execute('INSERT INTO processing_controls VALUES(?,?,?,?,NULL,NULL)',
                              (event['id'],self.key,attempt,digest(event)))
        self.collect(attempt, {'semantic':'DONE','summary':'fictional understood control',
                               'decision_json':encode(receipt)}, tools=True)
        return event, attempt

    def apply_control(self, event, attempt):
        # Existing native UUID validation has no fictional identity substitute.
        # Explicit NULL-only projection leaves all source/capability/result/tool
        # and input-resolution predicates running; it attests no native worker.
        with patch.object(processing, 'canonical_uuid', side_effect=lambda value:self.assertIsNone(value)):
            return processing.apply_control(self.s, event['id'], attempt)

    def assert_birth(self, response, source):
        row = self.s.one('SELECT e.rowid AS physical,p.position,e.hash,e.parent FROM events e '
                         'LEFT JOIN processing_source_positions p ON p.event=e.id WHERE e.id=?', (response,))
        self.assertLessEqual(row['physical'], self.boundary)
        self.assertTrue(configuration.event_allowed(self.s, self.s.event(response)),
                        'genuinely new response must pass the preserved configuration frontier')
        self.assertIsNotNone(row['position'], 'new internal response must record logical birth')
        self.assertGreater(row['position'], self.boundary)
        self.assertGreater(row['position'], self.s.one('SELECT position FROM processing_source_positions WHERE event=?', (source,))['position'])
        self.assertEqual(row['hash'], digest(self.s.event(response)))
        self.assertEqual(row['parent'], source)
        self.assertTrue(configuration.event_allowed(self.s, self.s.event(response)))
        self.assertTrue(self.s.processing.event(self.s.event(response)))
        self.assertEqual(prospective.event_position(self.s,response,{'selection':{'processing_capability':self.key}}),row['position'])
        self.assertLessEqual(prospective.event_position(self.s,response,{'selection':{}}),self.boundary)
        self.assertIsNone(self.s.one('SELECT processed_at FROM events WHERE id=?',(source,))['processed_at'])
        self.assert_originals()

    def consume(self, response):
        self.classify(response, 'wp')
        job = self.s.reserve()
        self.assertIsNotNone(job, 'current response must reach actual Work reservation')
        self.assertEqual([m['event'] for m in json.loads(job['members'])], [response])
        self.task_attempt(job, 'complete')
        self.assertIsNone(self.s.finish_job(job['id'],job['token']))
        return job

    def test_task_response_recycled_frontier_classification_and_work_consumption(self):
        event, job = self.task_source()
        windows_before = self.s.rows('SELECT * FROM service_windows')
        response = self.s.finish_job(job['id'],job['token'])
        self.assert_birth(response,event['id'])
        used_before = json.loads(windows_before[-1]['used'])
        used_after = json.loads(windows.current(self.s)['used'])
        self.assertEqual(used_after['events'],used_before['events']+1)
        self.assertEqual(windows.current(self.s)['new_inputs'],windows_before[-1]['new_inputs'])
        exact = self.snapshot()
        self.assertIsNone(self.s.finish_job(job['id'],job['token']))
        with self.s.tx():
            self.assertEqual(self.s._response(self.s.job(job['id']),self.s.attempt(self.s.job(job['id'])['active_attempt']),
                                            self.s.config['tasks']['wp'],self.s.event(response)['body']),response)
        self.assertEqual(self.snapshot(),exact)
        self.consume(response)
        self.assertIsNotNone(self.s.one('SELECT processed_at FROM events WHERE id=?',(event['id'],))['processed_at'])
        self.assert_originals()

    def test_control_return_recycled_frontier_classification_and_work_consumption(self):
        event, attempt = self.control_source()
        self.apply_control(event,attempt)
        response = self.s.one('SELECT response FROM processing_control_returns WHERE source=?',(event['id'],))['response']
        self.assert_birth(response,event['id'])
        whole = self.s.event(response)
        self.assertEqual(whole['body']['source'],event)
        self.assertEqual(whole['body']['actual_worker_return'],json.loads(self.s.attempt(attempt)['result']))
        exact = self.snapshot()
        self.apply_control(event,attempt)
        self.assertEqual(self.snapshot(),exact)
        # Resolve_input deliberately requires a second, fresh classification of
        # the source's derived owner decision before its completion can follow.
        self.consume(response)
        self.assertIsNone(self.s.one('SELECT processed_at FROM events WHERE id=?',(event['id'],))['processed_at'])
        self.classify(event['id'],'@control')
        self.s.complete_events()
        self.assertIsNotNone(self.s.one('SELECT processed_at FROM events WHERE id=?',(event['id'],))['processed_at'])
        self.assert_originals()

    def test_position_failure_rolls_back_task_response_charge_job_and_sequence(self):
        event, job = self.task_source()
        before = self.snapshot()
        self.s.db.execute("CREATE TEMP TRIGGER fictional_birth_refusal BEFORE INSERT ON processing_source_positions BEGIN SELECT RAISE(ABORT,'fictional position refusal'); END")
        with self.assertRaisesRegex(sqlite3.IntegrityError,'position refusal'):
            self.s.finish_job(job['id'],job['token'])
        self.assertEqual(self.snapshot(),before)
        self.s.db.execute('DROP TRIGGER fictional_birth_refusal')
        self.assert_birth(self.s.finish_job(job['id'],job['token']),event['id'])

    def test_position_failure_rolls_back_control_resolution_return_and_charges(self):
        event, attempt = self.control_source()
        before = self.snapshot()
        self.s.db.execute("CREATE TEMP TRIGGER fictional_birth_refusal BEFORE INSERT ON processing_source_positions BEGIN SELECT RAISE(ABORT,'fictional position refusal'); END")
        with self.assertRaisesRegex(sqlite3.IntegrityError,'position refusal'):
            self.apply_control(event,attempt)
        self.assertEqual(self.snapshot(),before)
        self.s.db.execute('DROP TRIGGER fictional_birth_refusal')
        self.apply_control(event,attempt)
        self.assert_birth(self.s.one('SELECT response FROM processing_control_returns')['response'],event['id'])

    def test_legacy_missing_position_borrowed_stale_and_old_source_stay_ineligible(self):
        self.assertFalse(self.s.processing.event(self.f.originals[0]))
        # Historical missing-position row remains historical across reopen;
        # neither old response lookalikes nor a claimed producer cause backfill.
        legacy = {**self.f.originals[0],'id':'fictional-legacy-response','kind':'response',
                  'source_job':'fictional-old-job'}
        with self.s.tx():
            self.s.db.execute('INSERT INTO events(id,role,payload,hash,received) VALUES(?,?,?,?,?)',
                              (legacy['id'],'Work',encode(legacy),digest(legacy),900.))
        self.assertFalse(configuration.event_allowed(self.s,legacy))
        self.assertFalse(self.s.processing.event(legacy))
        self.assertIsNone(self.s.one('SELECT position FROM processing_source_positions WHERE event=?',(legacy['id'],)))
        event,job = self.task_source()
        response = self.s.finish_job(job['id'],job['token'])
        fresh = self.s.event(response)
        # Logical birth alone cannot borrow another producer's capability.
        detail = self.s.attempt(self.s.job(job['id'])['active_attempt'])
        prior = detail['detail']
        changed = json.loads(prior); changed['processing_capability']='fictional-borrowed-capability'
        self.s.db.execute('UPDATE attempts SET detail=? WHERE id=?',(encode(changed),detail['id']))
        self.assertFalse(self.s.processing.event(fresh))
        self.s.db.execute('UPDATE attempts SET detail=? WHERE id=?',(prior,detail['id']))
        with patch.object(processing,'implementation',return_value={'fictional':'stale source'}):
            with self.assertRaisesRegex(Refusal,'source/configuration changed'):
                self.s.claim_classification()
        self.assertIsNone(self.s.one('SELECT classifier FROM events WHERE id=?',(response,))['classifier'])
        # A future-looking event whose Board post is old still has no intake authority.
        with self.assertRaises(Refusal): self.s.ingest({**self.c.new_event('fictional-old-source'),'post':0})
        self.assert_originals()

    def test_outgoing_response_birth_releases_only_its_classification_gate(self):
        event,job=self.task_source('complete')
        job=self.s.job(job['id'])
        attempt=self.s.attempt(job['active_attempt'])
        with self.s.tx():
            self.s.owner_report(job,attempt,json.loads(attempt['result']))
        response=self.s.finish_job(job['id'],job['token'])
        self.assert_birth(response,event['id'])
        outbox=self.s.one('SELECT * FROM outboxes WHERE job=?',(job['id'],))
        self.assertEqual(outbox['state'],'classification-pending')
        exact=self.snapshot()
        self.assertEqual(self.s.finish_job(job['id'],job['token']),response)
        self.assertEqual(self.snapshot(),exact)
        self.classify(response,'@delivery')
        self.assertEqual(self.s.one('SELECT state FROM outboxes WHERE id=?',(outbox['id'],))['state'],'pending')
        self.assertFalse(self.s.deliveries_settled(job['id']))
        self.assertIsNone(self.s.one('SELECT processed_at FROM events WHERE id=?',(event['id'],))['processed_at'])
        self.assert_originals()

    def test_nonrecycled_normal_paths(self):
        event, job = self.task_source()
        response = self.s.finish_job(job['id'],job['token'])
        self.assertGreater(self.s.one('SELECT rowid AS n FROM events WHERE id=?',(response,))['n'],self.boundary)
        self.assertGreater(self.s.one('SELECT position FROM processing_source_positions WHERE event=?',(response,))['position'],self.boundary)
        self.consume(response)
        event, attempt = self.control_source()
        self.apply_control(event,attempt)
        response = self.s.one('SELECT response FROM processing_control_returns')['response']
        self.assertGreater(self.s.one('SELECT rowid AS n FROM events WHERE id=?',(response,))['n'],self.boundary)
        self.consume(response)
        self.classify(event['id'],'@control')
        self.s.complete_events()
        self.assertIsNotNone(self.s.one('SELECT processed_at FROM events WHERE id=?',(event['id'],))['processed_at'])
        self.assert_originals()

    def test_control_producer_and_persisted_source_proof_remain_independent(self):
        event,attempt = self.control_source()
        source = self.s.one('SELECT * FROM processing_controls WHERE event=?',(event['id'],))
        self.s.db.execute('UPDATE processing_controls SET source_hash=? WHERE event=?',('fictional-stale-source',event['id']))
        before=self.snapshot()
        with self.assertRaisesRegex(Refusal,'original numeric END'):
            self.apply_control(event,attempt)
        self.assertEqual(self.snapshot(),before)
        self.s.db.execute('UPDATE processing_controls SET source_hash=? WHERE event=?',(source['source_hash'],event['id']))
        self.apply_control(event,attempt)
        response=self.s.one('SELECT response FROM processing_control_returns')['response']
        fresh=self.s.event(response)
        self.s.db.execute('UPDATE processing_controls SET capability=? WHERE event=?',('fictional-borrowed',event['id']))
        self.assertFalse(self.s.processing.event(fresh))
        self.s.db.execute('UPDATE processing_controls SET capability=? WHERE event=?',(self.key,event['id']))
        with self.assertRaisesRegex(Refusal,'persisted original return'):
            self.s.processing.event({**fresh,'body':{'fictional':'forged'}})
        with self.assertRaisesRegex(Refusal,'different original collector'):
            with self.s.tx():
                processing.control_return(self.s,event['id'],'fictional-foreign-attempt',{}, {})
        self.assertTrue(self.s.processing.event(fresh))
        with self.assertRaises(Refusal):
            self.s.ingest({**self.c.new_event('fictional-unproved-response'),'kind':'response'})
        self.assert_originals()


if __name__ == '__main__':
    unittest.main(verbosity=2)
