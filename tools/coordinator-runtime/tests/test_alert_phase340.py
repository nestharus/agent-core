"""Decision340 conditional histories in an explicitly isolated public export.

No models/providers/native identities execute. Collected outcomes, NULL-only UUID
and membership/allocation/schema seams are fiction; source, transport-intent,
classification, controls, transactions, cadence and finite accounting are real.
All private fixtures and failures stay for the actual Work collector.
"""
import copy
import json
import unittest
from unittest.mock import patch

from coordinator_runtime import capacity, processing, service, windows
from coordinator_runtime.contracts import Backpressure, Refusal, SOL, LUNA, digest, encode
import test_allocation332 as allocation
import test_configuration308 as fixture
import test_capacity48 as small


class Notifications(unittest.TestCase):
    def setUp(self):
        self.c = allocation.Continuing(methodName='runTest')
        self.addCleanup(self.c.doCleanups)
        original = fixture.engine_config
        def config(directory):
            value = original(directory)
            value['deadlines'].update(alert_interval=60, ack=30, backlog=60, task=600)
            value['limits'].update(max_alerts=4096, max_alert_debt=4096)
            value['delivery']['recipients'] = {'Work': {'session':'fictional-Work', 'board_role':'fictional', 'profile':None}}
            return value
        # NULL native classifier identity remains explicit even in the Board
        # receipt. This changes only the private fictional schema, not product.
        original_store = fixture.Store
        def runtime(value, **kwargs):
            value['delivery']['recipients'] = {'Work': {'session':'fictional-Work','board_role':'fictional','profile':None}}
            return original_store(value, **kwargs)
        extension = fixture.EXTENSION.replace('classifier_actor TEXT NOT NULL', 'classifier_actor TEXT')
        with patch.object(fixture, 'engine_config', side_effect=config), patch.object(fixture, 'EXTENSION', extension), patch.object(fixture, 'Store', side_effect=runtime):
            self.c.setUp()
        self.s = self.c.s
        for n in range(36):
            event = {**self.c.f.originals[0], 'id':'fictional-held-'+str(n), 'post':n+1}
            with self.s.tx():
                self.s.db.execute('INSERT INTO events(id,role,payload,hash,received,hold) VALUES(?,?,?,?,900,?)',
                    (event['id'],'Work',encode(event),digest(event),'fictional original uncertainty'))
                processing.note_source(self.s,event['id'])
        self.c.f.conn.execute('UPDATE coordinator_delivery_grants_v1 SET recipients=?,kinds=?',
            (encode({'Work':'fictional-Work'}),encode(['alert','question','effect-request','work'])))
        if self._testMethodName=='test_historical_pending_occurrence_keeps_its_source_boundary':
            old={'id':'fictional-old-occurrence','subject':'fictional-old-cause','kind':'old-cause','created':800.}
            self.s.db.execute('INSERT INTO alerts VALUES(?,?,?,?,?,NULL)',
                              (old['id'],old['subject'],old['kind'],old['created'],encode(old)))
            self.s.record_operational_error(old['subject'],{'cause':'fictional unchanged original cause'})
            debt={**old,'id':'fictional-old-debt'}
            self.s.db.execute('INSERT INTO alert_debt VALUES(?,?,?,?,?,0)',
                             (debt['id'],debt['subject'],debt['kind'],debt['created'],encode(debt)))
        self.c.adopt(); self.s = self.c.s; self.f = self.c.f
        self.now = 1000.; self.s.clock = lambda:self.now
        self.originals = {t:self.s.rows('SELECT * FROM '+t+' ORDER BY rowid') for t in
            ('events','processing_source_positions','outboxes','enrollments','jobs','attempts')}
        self.grants = [tuple(r) for r in self.f.conn.execute('SELECT * FROM coordinator_grants_v1')]
        selected = self.c.selection(max_windows=8)
        selected['service']['admission'] = {'until':1060.,'pause_bytes':16000000,'max_new_inputs':1}
        self.key = self.c.issue(selected)
        self.board = self.f.boards['Work']
        self.old_window = self.s.one('SELECT * FROM service_windows WHERE number=1')

    def conserved(self):
        for table, original in self.originals.items():
            key = 'role' if table=='enrollments' else 'event' if table=='processing_source_positions' else 'id'
            self.assertEqual([self.s.one('SELECT * FROM '+table+' WHERE '+key+'=?',(r[key],)) for r in original],original)
        self.assertEqual([tuple(r) for r in self.f.conn.execute('SELECT * FROM coordinator_grants_v1')],self.grants)
        self.assertEqual(self.s.one('SELECT * FROM service_windows WHERE number=1'),self.old_window)
        self.assertTrue(all(r['session'] is None and r['turn'] is None and r['profile'] is None
                            for r in self.s.rows('SELECT session,turn,profile FROM attempts')))

    def capture(self):
        prior = {r['id'] for r in self.s.rows('SELECT id FROM outboxes WHERE alert IS NOT NULL')}
        due = self.s.emit_alerts()
        # Drain each bounded producer page, never recapture the due population.
        while capacity.deliver_pending(self.s): pass
        rows = self.s.rows("SELECT * FROM outboxes WHERE alert IS NOT NULL AND state='pending' ORDER BY created,id")
        return due, [r for r in rows if r['id'] not in prior]

    def address(self, outbox):
        conn=self.f.conn; actor=self.s.config['actor']; key=outbox['id']; grant='fictional-grant-Work'
        post=conn.execute("INSERT INTO posts(author,recipient,topic,kind,text,created_at) VALUES(?,'fictional-Work','coordinator-runtime','handoff','fictional addressed pointer','fictional-time')",(actor,)).lastrowid
        conn.execute('INSERT INTO threads VALUES(?,?,?,?,?)',(post,'fictional notice','coordinator-runtime',actor,'fictional-time'))
        conn.execute('INSERT INTO thread_posts VALUES(?,?)',(post,post))
        notice=conn.execute("INSERT INTO notification_outbox(recipient,post_seq,thread_id,event,title,sender,created_at,route) VALUES('fictional-Work',?,?,'open','fictional',?,'fictional-time','managed')",(post,post,actor)).lastrowid
        conn.execute('''INSERT INTO coordinator_deliveries_v1(id,grant_id,owner,actor,producer,recipient,kind,required,payload,post,notice,state,created)
                    VALUES(?,?,?, ?,?,'fictional-Work','alert','settled',?,?,?,'posted','fictional-time')''',
                    (key,grant,'fictional-Work',actor,outbox['producer'],outbox['payload'],post,notice))
        self.board.software_delivery(self.s,outbox,self.f.boards)
        return self.s.event(self.s.one('SELECT event FROM processing_delivery_links WHERE delivery=?',(key,))['event'])

    def collect(self, attempt, result):
        self.s.begin(attempt, {'fixture':'synthetic collection; no worker encounter'})
        self.s.collect(attempt,{'exit':0,'capture':'complete','cleanup':'no-session-created','result':result,
            'detail':{'tool_completion':{'complete':True,'items':[],'nonzero_completions':[],'unknown_types':[]}}})

    def classify(self, event):
        before=self.s.one('SELECT ack FROM events WHERE id=?',(event['id'],))['ack']
        self.assertEqual(before,'pending')
        with self.assertRaises(Refusal):self.board.receipt(self.s,event['id'])
        attempt, actual = self.s.claim_classification()
        self.assertEqual(actual['id'],event['id'])
        self.assertEqual(json.loads(self.s.attempt(attempt)['binding']),LUNA)
        self.collect(attempt,{'event_id':event['id'],'task':'@control','package':None,'reason':'fictional full notification classification'})
        self.s.commit_classification(attempt)
        # UUID-only fiction projection; real _proof/_ack and durable receipt run.
        with patch('coordinator_runtime.board.canonical_uuid',side_effect=lambda value:self.assertIsNone(value)):
            receipt=self.board.receipt(self.s,event['id'])
        self.s.ack_state(event['id'],'done',receipt)
        self.assertEqual(receipt['classifier_attempt'],attempt)
        self.assertIsNone(receipt['classifier_actor'])
        return attempt

    def control(self,event,mode='notification',remaining=None):
        body=event['body']; occurrences=body.get('occurrences',[body])
        receipt={'source_hash':digest(event),'mode':mode,'task':None,'package':None,
            'related_event':None,'related_job':None,'reason':'fictional complete notification reading; original causes remain held',
            'evidence':['alert-occurrences:'+digest(occurrences)],'remaining_obligations':remaining or []}
        with self.s.tx():
            attempt=self.s._attempt('input-control',event['id'],None,SOL,None)
            self.s.db.execute('INSERT INTO processing_controls VALUES(?,?,?,?,NULL,NULL)',(event['id'],self.key,attempt,digest(event)))
        self.collect(attempt,{'semantic':'DONE','summary':'fictional all occurrences read; no original settlement',
                              'decision_json':encode(receipt)})
        return attempt,receipt

    def apply(self,event,attempt):
        with patch.object(processing,'canonical_uuid',side_effect=lambda value:self.assertIsNone(value)):
            return processing.apply_control(self.s,event['id'],attempt)

    def consume(self,outbox,event=None):
        event=event or self.address(outbox)
        self.classify(event)
        attempt,receipt=self.control(event)
        self.apply(event,attempt)
        self.s.complete_events()
        self.assertIsNotNone(self.s.one('SELECT processed_at FROM events WHERE id=?',(event['id'],))['processed_at'])
        self.assertIsNone(self.s.claim_classification(),'notification receipt cannot require a second classifier')
        with patch.object(processing,'canonical_uuid',side_effect=lambda value:self.assertIsNone(value)):
            self.board.software_delivery(self.s,outbox,self.f.boards)
        self.s.delivery_observed(outbox['id'],self.board.delivery_status(outbox['id']))
        self.assertEqual(self.s.one('SELECT state FROM outboxes WHERE id=?',(outbox['id'],))['state'],'settled')
        return event

    def test_load_recurrence_full_occurrences_and_finite_consumer_work(self):
        expected={(r['subject'],r['kind']) for r in self.s.violations()}
        self.assertGreaterEqual(len(expected),85)
        all_ids=set(); messages=0
        for cycle in range(4):
            due,rows=self.capture()
            self.assertEqual({(r['subject'],r['kind']) for r in due},expected)
            self.assertTrue(all(r['created']==self.now for r in due))
            ids={r['id'] for r in due};self.assertTrue(all_ids.isdisjoint(ids));all_ids |= ids
            self.assertLessEqual(len(rows),3,'85+ due causes must fit three bounded notifications')
            self.assertEqual({r['id'] for outbox in rows for r in json.loads(outbox['payload'])['occurrences']},ids)
            for outbox in rows:
                self.consume(outbox);messages+=1
            self.assertEqual(self.s.rows('SELECT * FROM processing_control_returns'),[])
            self.assertEqual(len(self.s.rows('SELECT * FROM jobs')),len(self.originals['jobs']))
            self.assertEqual(self.s.one('SELECT COUNT(*) AS n FROM alerts WHERE processed_at IS NULL')['n'],0)
            with patch.object(self.s.execution_pool,'status',create=True,return_value={'native':None,'fixture':True}):
                self.assertEqual(self.s.status()['pending_alert_deliveries']['count'],0)
            self.assertEqual(self.s.emit_alerts(),[],'same cadence cannot duplicate occurrences')
            with self.assertRaises(Backpressure):service.admit_input(self.s)
            self.conserved();self.now+=60
        attempts=self.s.rows('SELECT * FROM attempts WHERE id!=?',('fictional-original-attempt',))
        self.assertEqual(len(attempts),messages*2)
        self.assertEqual(self.s.one('SELECT starts FROM processing_capabilities WHERE id=?',(self.key,))['starts'],messages*2)
        allocated=self.s.one('SELECT COUNT(*) AS n FROM service_window_allocations WHERE capability=?',(self.key,))['n']
        self.assertGreater(allocated,0);self.assertLessEqual(allocated,8)
        with self.assertRaises(Refusal):capacity.retirement_basis(self.s,next(iter(all_ids)))
        print('fictional load:',len(all_ids),'full occurrences;',messages,'addressed notifications;',len(attempts),'model seams;',allocated,'charged appended allocations')

    def test_useful_admitted_proposal_drains_after_upstream_pause(self):
        source=self.c.new_event('fictional-useful')
        self.s.ingest(source)
        attempt,event=self.s.claim_classification()
        self.assertEqual(event['id'],source['id'])
        self.collect(attempt,{'event_id':source['id'],'task':'wp','package':None,'reason':'fictional useful bounded proposal'})
        self.s.commit_classification(attempt)
        # Explicit Board-source protocol receipt seam for this separate useful
        # packet. Notifications themselves execute production _proof/_ack.
        self.s.ack_state(source['id'],'plain',{'fixture':'synthetic upstream receipt'})
        with self.assertRaises(Backpressure):service.admit_input(self.s)
        _,rows=self.capture()
        for row in rows:self.consume(row)
        job=self.s.reserve();self.assertIsNotNone(job)
        self.assertEqual(job['task'],'wp')
        attempt=self.s.start_job(job['id'],job['token'])
        self.board.bind_software_attempt(self.s,self.s.job(job['id']),attempt,None)
        self.collect(attempt,{'semantic':'DONE','category':'complete','summary':'fictional substantive proposal prepared',
            'findings':[],'failures':[],'unknowns':[],'artifacts':[],'handoffs':[],
            'no_handoff_reason':'fictional admitted local work; no downstream proposal selected'})
        self.s.finish_job(job['id'],job['token'])
        self.assertEqual(self.s.job(job['id'])['state'],'closed')
        self.assertIsNotNone(self.s.one('SELECT processed_at FROM events WHERE id=?',(source['id'],))['processed_at'])
        self.conserved()

    def test_historical_pending_occurrence_keeps_its_source_boundary(self):
        original=self.s.one('SELECT * FROM alerts WHERE id=?',('fictional-old-occurrence',))
        old_debt=self.s.one('SELECT * FROM alert_debt WHERE id=?',('fictional-old-debt',))
        due,rows=self.capture()
        self.assertEqual(self.s.one('SELECT * FROM alert_debt WHERE id=?',(old_debt['id'],)),old_debt)
        self.assertIsNone(self.s.one('SELECT * FROM alerts WHERE id=?',(old_debt['id'],)))
        represented={r['id'] for outbox in rows for r in json.loads(outbox['payload'])['occurrences']}
        self.assertNotIn(original['id'],represented)
        self.assertTrue(any(r['subject']=='fictional-old-cause' for r in due))
        self.assertEqual(represented,{r['id'] for r in due})
        self.assertEqual(self.s.one('SELECT * FROM alerts WHERE id=?',(original['id'],)),original)
        self.assertIsNone(self.s.one('SELECT * FROM alert_delivery_members WHERE occurrence=?',(original['id'],)))
        self.conserved()

    def test_delivery_byte_bound_and_singleton_keep_every_original_cause(self):
        for n in range(3):self.s.record_operational_error('fictional-large-'+str(n),{'cause':'x'*14000})
        self.s.record_operational_error('fictional-singleton',{'cause':'y'*40000})
        due,rows=self.capture()
        represented=[r for outbox in rows for r in json.loads(outbox['payload'])['occurrences']]
        self.assertEqual(sorted(represented,key=lambda r:r['id']),sorted(due,key=lambda r:r['id']))
        self.assertEqual(len({r['id'] for r in represented}),len(due))
        for outbox in rows:
            body=json.loads(outbox['payload']);members=body['occurrences']
            self.assertLessEqual(len(outbox['payload'].encode()),196608 if len(members)==1 else 32768)
            self.assertTrue(all(r['source_hash']==digest(next(v for v in members if v['id']==r['occurrence']))
                for r in self.s.rows('SELECT * FROM alert_delivery_members WHERE delivery=?',(outbox['id'],))))
        self.conserved()

    def test_notification_consumption_does_not_create_business_return(self):
        _,rows=self.capture(); event=self.consume(rows[0])
        self.assertEqual(self.s.rows('SELECT * FROM processing_control_returns'),[])
        self.assertEqual(self.s.one('SELECT COUNT(*) AS n FROM events WHERE parent=?',(event['id'],))['n'],0)
        self.conserved()

    def test_own_notice_lag_still_recurs_and_whole_consumer_hold_blocks_clock(self):
        _,rows=self.capture();events=[self.address(r) for r in rows]
        self.now+=120
        due,more=self.capture()
        owed={(e['id'],kind) for e in events for kind in ('ack-lag','backlog')}
        self.assertTrue(owed <= {(r['subject'],r['kind']) for r in due})
        first=rows[0]
        fictional={'id':first['id'],'state':'acknowledged','processed_at':self.now}
        self.s.delivery_observed(first['id'],fictional)
        self.assertIsNone(self.s.one('SELECT processed_at FROM outboxes WHERE id=?',(first['id'],))['processed_at'])
        for r in json.loads(first['payload'])['occurrences']:
            self.assertIsNone(self.s.one('SELECT processed_at FROM alerts WHERE id=?',(r['id'],))['processed_at'])
        self.assertLessEqual(len(more),3)
        self.conserved()

    def test_forgery_partial_control_and_missing_coverage_cannot_finish_notice(self):
        _,rows=self.capture();outbox=rows[0];event=self.address(outbox)
        with self.assertRaises(Refusal):capacity.notification(self.s,{**event,'body':{'schema':capacity.NOTIFICATION,'occurrences':[]}})
        self.classify(event)
        attempt,receipt=self.control(event)
        original=self.s.attempt(attempt)
        bad={**receipt,'evidence':['fictional incomplete reading']}
        result={'semantic':'DONE','summary':'fictional missing occurrence coverage','decision_json':encode(bad)}
        self.s.db.execute('UPDATE attempts SET result=? WHERE id=?',(encode(result),attempt))
        with self.assertRaises(Refusal):self.apply(event,attempt)
        self.assertIsNone(self.s.input_resolution(event['id']))
        result={'semantic':'PARTIAL','summary':'fictional unresolved meaning','decision_json':encode(receipt)}
        self.s.db.execute('UPDATE attempts SET result=? WHERE id=?',(encode(result),attempt))
        with self.assertRaises(Refusal):self.apply(event,attempt)
        self.s.db.execute('UPDATE attempts SET result=? WHERE id=?',(original['result'],attempt))
        self.apply(event,attempt)
        self.conserved()

    def test_unresolved_notification_interpretation_keeps_work_return(self):
        _,rows=self.capture();event=self.address(rows[0]);self.classify(event)
        attempt,_=self.control(event,mode='control',remaining=['fictional actual Work decision needed'])
        self.apply(event,attempt)
        returned=self.s.one('SELECT * FROM processing_control_returns WHERE source=?',(event['id'],))
        self.assertIsNotNone(returned)
        self.assertIsNone(self.s.one('SELECT processed_at FROM events WHERE id=?',(event['id'],))['processed_at'])
        self.assertTrue(self.s.processing.event(self.s.event(returned['response'])))
        self.conserved()


class Silence(unittest.TestCase):
    def test_zero_violations_produce_no_occurrence_or_notification(self):
        f=small.Capacity48(methodName='runTest');f._setupAsyncioRunner()
        self.addCleanup(f._tearDownAsyncioRunner);self.addCleanup(f.doCleanups);f.setUp()
        f.store.clear_operational_error('unchanged')
        for _ in range(3):
            self.assertEqual(f.store.emit_alerts(),[])
            self.assertEqual(f.store.rows('SELECT * FROM outboxes'),[])
            f.now+=60


if __name__=='__main__':unittest.main()
