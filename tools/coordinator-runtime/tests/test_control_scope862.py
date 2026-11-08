"""Synthetic Board/SDK actors; production CLI, collections and completion.

No actual provider or live operation. Prompt semantics need later live inquiry.
"""
import copy
import json
from unittest.mock import patch
from test_plain_control821 import Completion821
from test_qa629_repairs import actor
from support import collect
from coordinator_runtime import cli, plain_control, processing
from coordinator_runtime.contracts import Refusal, digest, encode


class Scope862(Completion821):
    def unresolved(self):
        source, attempt, request, returned = self.returned()
        child = returned['response']
        # Reclassification really runs through claim/collect/commit rather
        # than changing only the queue to look like an eligible classifier.
        self.store.db.execute("UPDATE events SET state='received' WHERE id=?", (child,))
        key, event = self.store.claim_classification()
        self.assertEqual(event['id'], child)
        collect(self.store, key, dict(event_id=child, task='@unresolved', package=None,
                                    reason='Whole receipt requires genuine Work interpretation'))
        self.store.commit_classification(key)
        self.runtime.receipts()
        self.assertEqual(self.store.one('SELECT phase,task,state,job FROM queue WHERE event=?',(child,)),
                         dict(phase='control',task='@unresolved',state='awaiting-owner',job=None))
        return source, attempt, request, returned

    def view(self, source):
        with patch.dict('os.environ', {'CODEX_SESSION_ID':self.issuer}), actor(self.boards['Work'].store,self.issuer):
            return cli.operate(cli.parser().parse_args(['processing-source',self.cap,source['id'],
                                '--plain-control-basis']),self.store)

    def test_unresolved_cli_consumption_preserves_original_classifier_lineages(self):
        source, attempt, request, returned = self.unresolved()
        # ACK names its original classifier; a later current classifier is a
        # separate real attempt, not a corrupt ACK or interchangeable identity.
        old_ack = self.store.one('SELECT ack_receipt,classifier FROM events WHERE id=?',(source['id'],))
        self.store.db.execute("UPDATE events SET state='received' WHERE id=?",(source['id'],))
        self.fresh(); self.runtime.receipts()
        current = self.store.one('SELECT ack_receipt,classifier FROM events WHERE id=?',(source['id'],))
        self.assertNotEqual(old_ack['classifier'],current['classifier'])
        self.assertEqual(old_ack['ack_receipt'],current['ack_receipt'])
        originals = {t:self.store.rows('SELECT * FROM '+t) for t in
                     ('attempts','input_resolutions','processing_control_returns')}
        with patch.object(self.store,'event',side_effect=AssertionError('basis acquired a body')):
            basis = self.view(source)
        self.assertEqual(basis['source']['received'], request['received'])
        self.assertEqual(basis['source']['classifier'],current['classifier'])
        self.assertEqual(basis['consumer']['payload_hash'],request['consumer_disposition']['payload_hash'])
        self.assertEqual(basis['consumer']['source']['received'],request['consumer_disposition']['received'])
        self.assertEqual(basis['consumer']['classifier']['capability'],self.cap)
        self.assertIsNotNone(basis['consumer']['classifier']['collected'])
        self.command(source,attempt,request)
        self.fresh(); self.runtime.receipts(); self.store.complete_events()
        for event in (source['id'],returned['response']):
            self.assertIsNotNone(self.store.one('SELECT processed_at FROM events WHERE id=?',(event,))['processed_at'])
        for table, rows in originals.items():
            for row in rows:
                key = 'event' if table=='input_resolutions' else 'source' if table=='processing_control_returns' else 'id'
                self.assertEqual(row,self.store.one('SELECT * FROM '+table+' WHERE '+key+'=?',(row[key],)))
        self.assertEqual(self.store.rows('SELECT * FROM jobs'),[])
        self.assertEqual(len(self.store.rows('SELECT * FROM processing_control_returns')),1)
        self.command(source,attempt,request)  # exact idempotent receipt, no chain

    def test_unresolved_negatives_before_any_body(self):
        source,attempt,request,returned = self.unresolved(); child=returned['response']
        classifier=self.store.one('SELECT classifier FROM events WHERE id=?',(child,))['classifier']
        cases=[('queue','state','running'),('queue','state','reserved'),('queue','task','@control'),
               ('queue','job','real-reservation'),('queue','package','actual-package'),
               ('events','hold','actual-hold'),('events','state','received'),
               ('attempts','exit',1),('attempts','capture','partial'),('attempts','collected',None),
               ('attempts','begin',None),('attempts','error','actual classifier error'),
               ('attempts','detail',encode({'processing_capability':'older-capability'})),
               ('attempts','event',source['id'])]
        for table,column,value in cases:
            key='event' if table=='queue' else 'id'; identity=classifier if table=='attempts' else child
            sql='UPDATE '+table+' SET '+column+'=? WHERE '+key+'=?'
            old=self.store.one('SELECT '+column+' FROM '+table+' WHERE '+key+'=?',(identity,))[column]
            self.store.db.execute(sql,(value,identity))
            with self.subTest(table=table,column=column,value=value), patch.object(self.store,'event',side_effect=AssertionError('ineligible body')):
                with self.assertRaises(Refusal):self.command(source,attempt,request)
            self.store.db.execute(sql,(old,identity))
        for column in ('received','payload_hash','source_hash'):
            bad=copy.deepcopy(request);bad['consumer_disposition'][column]=-1 if column=='received' else '0'*64
            with self.subTest(pin=column),self.assertRaises(Refusal):self.command(source,attempt,bad)
        self.assertEqual(self.store.rows('SELECT * FROM plain_control_dispositions'),[])

    def test_basis_and_disposition_exclude_old_unselected_birth_before_body(self):
        source,attempt,request,returned=self.unresolved();child=returned['response']
        old=self.store.one('SELECT position FROM processing_source_positions WHERE event=?',(child,))['position']
        self.store.db.execute('UPDATE processing_source_positions SET position=0 WHERE event=?',(child,))
        with patch.object(self.store,'event',side_effect=AssertionError('old unselected body')):
            with self.assertRaises(Refusal):self.view(source)
            with self.assertRaises(Refusal):self.command(source,attempt,request)
        self.store.db.execute('UPDATE processing_source_positions SET position=? WHERE event=?',(old,child))

    def test_whole_return_mutation_refuses_without_rewriting_original_result(self):
        source,attempt,request,returned=self.unresolved()
        original=self.store.attempt(attempt)
        payload=json.loads(returned['payload']);payload['body']['unresolved_actual_effect']='still owned'
        self.store.db.execute('UPDATE events SET payload=?,hash=? WHERE id=?',
                             (encode(payload),digest(payload),returned['response']))
        bad=copy.deepcopy(request);bad['consumer_disposition'].update(source_hash=digest(payload),payload_hash=digest(payload))
        with self.assertRaises(Refusal):self.command(source,attempt,bad)
        self.assertEqual(original,self.store.attempt(attempt))

    def test_current_scope_completion_leaves_unrelated_held_source_whole(self):
        unrelated,_,_=self.original(['Unrelated real decision/effect remains with its original owner'])
        self.store.set_hold(unrelated['id'],'Unrelated original is held')
        original=self.store.one('SELECT * FROM events WHERE id=?',(unrelated['id'],))
        scope=dict(scope='no-new-owned-work-or-effects',accounting=[],
                   evidence=['Whole authenticated status asks only for this control handling; no linked decision, work or effect'])
        source,attempt,_=self.original(plain_scope=scope)
        processing.apply_control(self.store,source['id'],attempt)
        self.fresh(); self.runtime.receipts(); self.store.complete_events()
        self.assertIsNotNone(self.store.one('SELECT processed_at FROM events WHERE id=?',(source['id'],))['processed_at'])
        self.assertEqual(original,self.store.one('SELECT * FROM events WHERE id=?',(unrelated['id'],)))
        self.assertEqual(self.store.rows('SELECT * FROM jobs'),[])
        self.assertEqual(self.store.rows('SELECT * FROM processing_control_returns'),[])
