"""R320-5 counterfactual in owned fictional stores; no actual live failure.

Intents/grants/source/recipient use production receiving and delivery validators.
Configuration308's explicit NULL-native membership seams remain fiction.
"""
import copy
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from coordinator_runtime import processing, service
from coordinator_runtime.contracts import Backpressure, Refusal, digest, encode
import test_configuration308 as fixture


class OwedControl(unittest.TestCase):
    def setUp(self):
        self.number=0
        self.f=fixture.CurrentConfiguration(methodName='runTest');self.addCleanup(self.f.doCleanups)
        original_store=fixture.Store
        def runtime(value,**kw):
            value['delivery']['recipients']={'Work':{'session':'fictional-Work','board_role':'fictional','profile':None}}
            value['limits'].update(max_events=8,max_outboxes=128)
            for role,selected in value['roles'].items():
                selected['routes']=[n for n,t in value['tasks'].items() if t['role']==role]
            return original_store(value,**kw)
        with patch.object(fixture,'Store',side_effect=runtime):self.f.setUp()
        # Independently declared original grant authority in the fixture, before
        # any current selection. No production authority check is substituted.
        self.f.conn.execute('UPDATE coordinator_delivery_grants_v1 SET recipients=?,kinds=?',
             (encode({'Work':'fictional-Work'}),encode(['alert','question','effect-request','work'])))
        self.f.transition();self.s=self.f.runtime;self.boards=self.f.boards
        selected=self.f.processing_selection();selected.pop('expires');selected.pop('max_starts')
        selected['service']={'max_inflight':2,'reviews':{},'legacy_resources':{},
                'admission':{'until':1060.,'pause_bytes':16000000,'max_new_inputs':1}}
        self.key=processing.select(self.s,self.boards,selected)['capability']
        self.s.processing=processing.Access(self.s,self.key,self.boards)
        self.source=self.f.fresh('fictional-new-source')
        self.old_outboxes=self.s.rows('SELECT * FROM outboxes ORDER BY id')
        self.old_positions=self.s.rows('SELECT * FROM processing_source_positions ORDER BY position')
        self.old_events=self.s.rows('SELECT * FROM events ORDER BY id')
        with self.assertRaises(Backpressure):service.admit_input(self.s)

    def delivery(self,kind='alert'):
        self.number+=1
        with self.s.tx():
            key=self.s._outbox('Work','Work',kind,{'fictional':'already owed control','ordinal':self.number},event=self.source['id'])
        outbox=self.s.one('SELECT * FROM outboxes WHERE id=?',(key,))
        conn=self.f.conn;actor=self.s.config['actor'];grant='fictional-grant-Work'
        post=conn.execute("INSERT INTO posts(author,recipient,topic,kind,text,created_at) VALUES(?,'fictional-Work','coordinator-runtime','handoff','fictional control pointer','fictional-time')",(actor,)).lastrowid
        conn.execute('INSERT INTO threads VALUES(?,?,?,?,?)',(post,'fictional control','coordinator-runtime',actor,'fictional-time'))
        conn.execute('INSERT INTO thread_posts VALUES(?,?)',(post,post))
        notice=conn.execute("INSERT INTO notification_outbox(recipient,post_seq,thread_id,event,title,sender,created_at,route) VALUES('fictional-Work',?,?,'open','fictional',?,'fictional-time','managed')",(post,post,actor)).lastrowid
        conn.execute('''INSERT INTO coordinator_deliveries_v1(id,grant_id,owner,actor,producer,recipient,kind,required,payload,post,notice,state,created)
                    VALUES(?,?,?, ?,?,'fictional-Work',?,'settled',?,?,?,'posted','fictional-time')''',
                    (key,grant,'fictional-Work',actor,outbox['producer'],kind,outbox['payload'],post,notice))
        return outbox

    def test_owned_controls_progress_under_optional_admission_and_keep_source_charges_clocks(self):
        for kind in ('alert','question','effect-request'):
            outbox=self.delivery(kind)
            self.assertTrue(self.boards['Work'].software_delivery(self.s,outbox,self.boards))
            intent=self.f.conn.execute('SELECT payload FROM coordinator_software_deliveries_v1 WHERE delivery=?',(outbox['id'],)).fetchone()
            event=json.loads(intent['payload'])
            self.assertTrue(self.s.processing.owed_control(event))
            self.assertIsNotNone(self.s.one('SELECT * FROM events WHERE id=?',(event['id'],)))
            self.assertEqual(self.s.one('SELECT event FROM processing_delivery_links WHERE delivery=?',(outbox['id'],))['event'],event['id'])
            self.assertFalse(self.s.ingest(event),'same intent retry consumes no duplicate event or position')
            self.assertIsNone(self.s.one('SELECT processed_at FROM events WHERE id=?',(event['id'],))['processed_at'])
            self.assertIsNone(self.s.one('SELECT processed_at FROM outboxes WHERE id=?',(outbox['id'],))['processed_at'])
            with self.assertRaises(Backpressure):service.admit_input(self.s)
        self.assertEqual(self.s.rows('SELECT * FROM processing_source_positions ORDER BY position')[:5],self.old_positions)
        self.assertEqual(len(self.s.rows('SELECT * FROM processing_source_positions')),8)
        self.assertEqual(self.s.rows('SELECT * FROM outboxes WHERE id IN ('+','.join('?' for _ in self.old_outboxes)+') ORDER BY id',
               tuple(row['id'] for row in self.old_outboxes)),self.old_outboxes)
        self.assertEqual(self.s.rows('SELECT * FROM events WHERE id IN ('+','.join('?' for _ in self.old_events)+') ORDER BY id',
               tuple(row['id'] for row in self.old_events)),self.old_events)
        self.assertTrue(all(r['profile'] is None and r['session'] is None and r['turn'] is None
                            for r in self.s.rows('SELECT profile,session,turn FROM attempts')))

    def test_forged_fields_and_changed_source_recipient_capability_intent_do_not_exempt(self):
        outbox=self.delivery()
        self.boards['Work'].software_delivery(self.s,outbox,self.boards)
        received=json.loads(self.f.conn.execute('SELECT payload FROM coordinator_software_deliveries_v1 WHERE delivery=?',(outbox['id'],)).fetchone()['payload'])
        for change in ({'id':'fictional-forgery'},{'recipient':'fictional-other'}, {'body':'forged body'},
                       {'processing_capability':'fictional-other-capability'},
                       {'source_delivery':{**received['source_delivery'],'source_hash':'0'*64}}):
            forged={**received,**change}
            with self.subTest(change=change),self.assertRaises((Refusal,Backpressure)):self.s.ingest(forged)
        self.f.conn.execute("UPDATE coordinator_deliveries_v1 SET kind='work' WHERE id=?",(outbox['id'],))
        with self.assertRaises(Refusal):self.s.processing.owed_control(received)
        self.f.conn.execute("UPDATE coordinator_deliveries_v1 SET kind='alert' WHERE id=?",(outbox['id'],))
        self.f.conn.execute('UPDATE coordinator_deliveries_v1 SET transport_started=1 WHERE id=?',(outbox['id'],))
        with self.assertRaisesRegex(Refusal,'uncertainty'):self.s.processing.owed_control(received)
        self.f.conn.execute('UPDATE coordinator_deliveries_v1 SET transport_started=0 WHERE id=?',(outbox['id'],))
        self.s.db.execute('UPDATE outboxes SET payload=? WHERE id=?',(encode({'fictional':'different source'}),outbox['id']))
        with self.assertRaises(Refusal):self.s.processing.owed_control(received)

    def test_event_capacity_still_refuses_and_keeps_exact_pending_control_intent(self):
        # Three bounded controls fill max_events=8 (four originals + source +3).
        for kind in ('alert','question','effect-request'):
            self.boards['Work'].software_delivery(self.s,self.delivery(kind),self.boards)
        outbox=self.delivery('alert')
        before=self.s.rows('SELECT * FROM processing_source_positions ORDER BY position')
        with self.assertRaises(Backpressure):
            self.boards['Work'].software_delivery(self.s,outbox,self.boards)
        intent=self.f.conn.execute('SELECT * FROM coordinator_software_deliveries_v1 WHERE delivery=?',(outbox['id'],)).fetchone()
        self.assertIsNotNone(intent,'failed receiving ingestion retains durable original intent')
        self.assertIsNone(self.s.one('SELECT * FROM events WHERE id=?',(intent['event'],)))
        self.assertEqual(self.s.rows('SELECT * FROM processing_source_positions ORDER BY position'),before)
        self.assertIsNone(self.s.one('SELECT processed_at FROM outboxes WHERE id=?',(outbox['id'],))['processed_at'])
        with self.assertRaises(Backpressure):
            self.boards['Work'].software_delivery(self.s,outbox,self.boards)
        self.assertEqual(self.f.conn.execute('SELECT * FROM coordinator_software_deliveries_v1 WHERE delivery=?',(outbox['id'],)).fetchone()['payload'],intent['payload'])



if __name__=='__main__':unittest.main()
