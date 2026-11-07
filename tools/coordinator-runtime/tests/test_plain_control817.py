"""Public isolated Board and actual local collection; synthetic wire identities.
No native/model/effect calls. SDK actor is the explicit fixture seam.
"""
import copy
import errno
import json
import os
from pathlib import Path
from unittest.mock import patch
from test_report_transport739 import ReportTransport
from test_qa629_repairs import actor
from support import collect, result
from coordinator_runtime import plain_control, processing
from coordinator_runtime.contracts import Refusal, SOL, digest, encode

class Terminal817(ReportTransport):
    def original(self, obligations=()):
        b=self.boards['Reviews']
        args=b.store.parser().parse_args(['open','--session',self.source_sender,'--topic','fixture',
            '--kind','finding','--text','Interpret this status only. No new workflow or effect. Original duties stay with their owners.',
            '--to',self.config['roles']['Reviews']['owner'],'--title','817 status','--no-push'])
        with b.store.database(str(self.board_path)) as c, actor(b.store,self.source_sender):
            b.store.open_thread(c,args)
        source=b.scan(self.store)[0];self.store.ingest(source,cursor=source['post'])
        self.fresh()
        self.runtime.receipts()
        self.assertEqual(self.store.one('SELECT ack FROM events WHERE id=?',(source['id'],))['ack'],'done')
        with self.store.tx():
            attempt=self.store._attempt('input-control',source['id'],None,SOL,'.codex')
            self.store.db.execute('INSERT INTO processing_controls VALUES(?,?,?,?,NULL,NULL)',(source['id'],self.cap,attempt,digest(source)))
        receipt=dict(source_hash=digest(source),mode='control',task=None,package=None,related_event=None,related_job=None,
            reason='Whole status interpreted with no newly assigned work/effect',evidence=['Whole explicit status source'],remaining_obligations=list(obligations))
        result=dict(semantic='DONE',summary='Bounded status interpretation completed',decision_json=encode(receipt))
        collect(self.store,attempt,result,tool_completion=dict(complete=True,items=[],nonzero_completions=[],unknown_types=[]))
        request=dict(schema=plain_control.VERSION,event=source['id'],source_hash=digest(source),
            received=self.store.one('SELECT received FROM events WHERE id=?',(source['id'],))['received'],attempt=attempt,
            result_hash=digest(result),resolution_version=1,scope='no-new-owned-work-or-effects',accounting=[],
            evidence=['Work interprets the entire exact source as bounded status only'],completed_consumer=None)
        return source,attempt,request

    def fresh(self):
        while claimed:=self.store.claim_classification():
            key,event=claimed
            collect(self.store,key,dict(event_id=event['id'],task='@control' if event['kind']=='board' else 'work-proposer',package=None,reason='Whole control status'))
            self.store.commit_classification(key)

    def apply817(self, source, attempt, request):
        with actor(self.boards['Work'].store,self.issuer):
            return plain_control.apply(self.store,source['id'],attempt,request)

    def test_public_board_collected_control_terminal_once(self):
        source,attempt,request=self.original();raw=self.store.attempt(attempt)
        before=self.store.one('SELECT payload,hash,received,ack,ack_receipt FROM events WHERE id=?',(source['id'],))
        cap=self.store.one('SELECT * FROM processing_capabilities WHERE id=?',(self.cap,))
        receipt=self.apply817(source,attempt,request)
        self.assertEqual(cap,self.store.one('SELECT * FROM processing_capabilities WHERE id=?',(self.cap,)))
        self.assertEqual(self.store.rows('SELECT * FROM processing_control_returns'),[])
        self.assertIsNone(self.store.one('SELECT processed_at FROM events WHERE id=?',(source['id'],))['processed_at'])
        self.fresh();self.runtime.receipts();self.store.complete_events()
        ended=self.store.one('SELECT processed_at FROM events WHERE id=?',(source['id'],))['processed_at']
        self.assertIsNotNone(ended)
        self.assertEqual(receipt,self.apply817(source,attempt,request))
        processing.apply_control(self.store,source['id'],attempt)
        self.assertEqual(self.store.rows('SELECT * FROM processing_control_returns'),[])
        self.store.complete_events()
        self.assertEqual(ended,self.store.one('SELECT processed_at FROM events WHERE id=?',(source['id'],))['processed_at'])
        self.assertEqual(raw,self.store.attempt(attempt))
        self.assertEqual(cap['starts']+1,self.store.one('SELECT starts FROM processing_capabilities WHERE id=?',(self.cap,))['starts'])
        self.assertEqual(before,self.store.one('SELECT payload,hash,received,ack,ack_receipt FROM events WHERE id=?',(source['id'],)))
        self.assertEqual(self.store.rows('SELECT * FROM jobs'),[])

    def test_existing_pending_consumer_refuses_completed_consumer_preserved(self):
        source,attempt,request=self.original();processing.apply_control(self.store,source['id'],attempt)
        child=self.store.one('SELECT * FROM processing_control_returns WHERE source=?',(source['id'],))
        request['completed_consumer']=child['response']
        with patch.object(self.store,'event',side_effect=AssertionError('pending body acquired')):
            with self.assertRaises(Refusal):self.apply817(source,attempt,request)
        self.fresh();self.runtime.receipts()
        job=self.store.reserve();self.assertEqual(job['task'],'work-proposer')
        key=self.store.start_job(job['id'],job['token'])
        self.boards['Work'].bind_software_attempt(self.store,self.store.job(job['id']),key,None)
        answer=result();answer.update(handoffs=[],no_handoff_reason='Exact control return read; no new assigned work')
        self.finish(job,key,answer)
        self.store.complete_events()
        self.assertIsNotNone(self.store.one('SELECT processed_at FROM events WHERE id=?',(child['response'],))['processed_at'])
        before=self.store.event(child['response']);self.apply817(source,attempt,request)
        self.assertEqual(before,self.store.event(child['response']))
        self.assertEqual(child,self.store.one('SELECT * FROM processing_control_returns WHERE source=?',(source['id'],)))

    def test_unknown_scope_obligations_and_bad_metadata_refuse_before_body(self):
        source,attempt,request=self.original()
        for key,value in [('scope','uncertain-effect'),('received',-1),('source_hash','wrong'),('completed_consumer','forged')]:
            with self.subTest(key=key),patch.object(self.store,'event',side_effect=AssertionError('wrong body acquired')):
                with self.assertRaises(Refusal):self.apply817(source,attempt,{**request,key:value})
        raw=self.store.attempt(attempt)
        for column,value in [('collected',None),('capture','partial'),('exit',1)]:
            self.store.db.execute('UPDATE attempts SET '+column+'=? WHERE id=?',(value,attempt))
            with patch.object(self.store,'event',side_effect=AssertionError('wrong body acquired')):
                with self.assertRaises(Refusal):self.apply817(source,attempt,request)
            self.store.db.execute('UPDATE attempts SET '+column+'=? WHERE id=?',(raw[column],attempt))
        self.store.set_hold(source['id'],'retained hold')
        with patch.object(self.store,'event',side_effect=AssertionError('held body acquired')):
            with self.assertRaises(Refusal):self.apply817(source,attempt,request)

    def test_obligations_remain_blocking_and_unmodified(self):
        source,attempt,request=self.original(['Original duty stays at its exact source'])
        with self.assertRaises(Refusal):self.apply817(source,attempt,request)
        self.assertIsNone(self.store.input_resolution(source['id']))

    def test_mutation_at_transaction_refuses(self):
        source,attempt,request=self.original();original=plain_control.validate;calls=[]
        def fence(*a,**kw):
            result=original(*a,**kw);calls.append(1)
            if len(calls)==1:self.store.set_hold(source['id'],'changed before transaction')
            return result
        with patch.object(plain_control,'validate',side_effect=fence):
            with self.assertRaises(Refusal):self.apply817(source,attempt,request)
        self.assertIsNone(self.store.input_resolution(source['id']))

    def test_kernel_closure(self):
        paths=[Path('/actualsrc/tools/coordinator-runtime/coordinator_runtime/plain_control.py')]
        paths += [Path('/src/tools/message-board')/n for n in ('board.py','board_store.py','catalog.py','active_listener.py','queue_transport.py')]
        paths += list(Path('/src/tools/coordinator-runtime/tests/fixture_snapshot').glob('*.py'))
        for p in paths:
            self.assertTrue(p.is_file());self.assertTrue(os.statvfs(p).f_flag & os.ST_RDONLY)
            with self.assertRaises(OSError) as err:os.open(p,os.O_WRONLY)
            self.assertEqual(err.exception.errno,errno.EROFS)
        self.assertEqual(os.environ['TMPDIR'],'/fixtures/tmp')
        self.assertEqual(set(os.listdir('/sys/class/net')) if Path('/sys/class/net').exists() else set(),set())

    def test_conserved_duty_pins_lossless_but_global_completion_stays_blocked(self):
        debt,_,_=self.original()
        source,attempt,request=self.original(['Exact original obligation remains'])
        raw=self.store.attempt(attempt)
        request['accounting']=[dict(index=0,text='Exact original obligation remains',
            disposition='conserved-at-original-source',owner=self.config['roles']['Reviews']['owner'],
            event=debt['id'],source_hash=digest(debt),evidence='Whole status explicitly retains this original source duty')]
        bad=copy.deepcopy(request);bad['accounting'][0]['owner']=self.issuer
        with self.assertRaises(Refusal):self.apply817(source,attempt,bad)
        self.apply817(source,attempt,request);self.fresh();self.runtime.receipts();self.store.complete_events()
        self.assertEqual(raw,self.store.attempt(attempt))
        self.assertEqual(self.store.input_resolution(source['id'])['receipt']['remaining_obligations'],['Exact original obligation remains'])
        self.assertIsNone(self.store.one('SELECT processed_at FROM events WHERE id=?',(source['id'],))['processed_at'])
        self.assertEqual(self.store.rows('SELECT * FROM processing_control_returns'),[])

    def test_uncertain_outbox_and_stale_capability_refuse_before_body(self):
        source,attempt,request=self.original()
        with self.store.tx():
            self.store._outbox('Reviews','Work','question',dict(meaning='Delivery/effects uncertain'),event=source['id'])
        with patch.object(self.store,'event',side_effect=AssertionError('uncertain source body acquired')):
            with self.assertRaises(Refusal):self.apply817(source,attempt,request)
        self.store.db.execute('UPDATE processing_capabilities SET revoked=? WHERE id=?',(self.store.clock(),self.cap))
        with patch.object(self.store,'event',side_effect=AssertionError('revoked source body acquired')):
            with self.assertRaises(Refusal):self.apply817(source,attempt,request)

    def test_refused_or_forged_result_before_source_body(self):
        source,attempt,request=self.original();raw=self.store.attempt(attempt)
        result=json.loads(raw['result'])
        for status in ('PARTIAL','FAILED','UNKNOWN'):
            changed={**result,'semantic':status}
            self.store.db.execute('UPDATE attempts SET result=? WHERE id=?',(encode(changed),attempt))
            with patch.object(self.store,'event',side_effect=AssertionError('refused source body acquired')):
                with self.assertRaises(Refusal):self.apply817(source,attempt,{**request,'result_hash':digest(changed)})
        self.store.db.execute('UPDATE attempts SET result=? WHERE id=?',(raw['result'],attempt))
        with patch.object(self.store,'event',side_effect=AssertionError('forged source body acquired')):
            with self.assertRaises(Refusal):self.apply817(source,attempt,{**request,'result_hash':'forged'})
