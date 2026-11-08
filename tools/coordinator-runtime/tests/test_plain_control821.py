"""821 qualification: actual isolated Board, collections, CLI and current lease."""
import copy
import json
from unittest.mock import patch
from test_plain_control817 import Terminal817
from test_owner_lease797 import OwnerLease
from test_qa629_repairs import actor
from coordinator_runtime import cli, plain_control, processing, prospective
from coordinator_runtime.contracts import Refusal, digest, encode

class Completion821(Terminal817):
    def command(self,source,attempt,request):
        path=self.area/'terminal.json';path.write_text(encode(request))
        with patch.dict('os.environ',{'CODEX_SESSION_ID':self.issuer}), actor(self.boards['Work'].store,self.issuer):
            return cli.operate(cli.parser().parse_args(['processing-dispose-plain-control',self.cap,source['id'],
                '--attempt',attempt,'--receipt',str(path)]),self.store)

    def conserved(self,automatic=False):
        original,_,_=self.original()
        accounting=[dict(index=0,text='Whole original Work274 history, effects and custody remain with their owner',
            disposition='conserved-at-original-source',owner=self.config['roles']['Reviews']['owner'],event=original['id'],
            source_hash=digest(original),evidence='This explicit status selects no new workflow; the original named source retains its duty')]
        scope=dict(scope='no-new-owned-work-or-effects',accounting=accounting,evidence=['Whole source explicitly requests bounded status interpretation'])
        source,attempt,request=self.original(['Whole original Work274 history, effects and custody remain with their owner'],plain_scope=scope if automatic else None)
        request['accounting']=accounting
        return source,attempt,request

    def returned(self):
        source,attempt,request=self.conserved()
        processing.apply_control(self.store,source['id'],attempt)
        self.fresh();self.runtime.receipts()
        returned=self.store.one('SELECT * FROM processing_control_returns WHERE source=?',(source['id'],))
        child=self.store.one('SELECT * FROM events WHERE id=?',(returned['response'],))
        request['completed_consumer']=child['id']
        request['consumer_disposition']=dict(schema='plain-control-consumer-v1',event=child['id'],source_hash=child['hash'],
            received=child['received'],scope='whole-return-no-new-owned-work-or-effects',payload_hash=digest(json.loads(returned['payload'])),
            evidence=['Work read the entire original source, actual collected result and software resolution, including all history; no new receiving work or effect'])
        return source,attempt,request,returned

    def test_same869_shape_existing_return_cli_terminal_once_preserves_every_original(self):
        source,attempt,request,returned=self.returned()
        original={t:self.store.rows('SELECT * FROM '+t) for t in ('processing_control_returns','attempts','input_resolutions','processing_capabilities')}
        source_bytes=self.store.one('SELECT payload,hash,received FROM events WHERE id=?',(source['id'],))
        child_bytes=self.store.one('SELECT payload,hash,received,parent FROM events WHERE id=?',(returned['response'],))
        receipt=self.command(source,attempt,request)
        self.assertEqual(original['input_resolutions'],self.store.rows('SELECT * FROM input_resolutions'))
        self.assertIsNone(self.store.one('SELECT processed_at FROM events WHERE id=?',(source['id'],))['processed_at'])
        self.fresh();self.runtime.receipts();self.store.complete_events()
        ended=self.store.one('SELECT processed_at FROM events WHERE id=?',(source['id'],))['processed_at'];self.assertIsNotNone(ended)
        self.assertIsNotNone(self.store.one('SELECT processed_at FROM events WHERE id=?',(returned['response'],))['processed_at'])
        self.assertEqual(receipt,self.command(source,attempt,request))
        processing.apply_control(self.store,source['id'],attempt);self.store.complete_events()
        self.assertEqual(ended,self.store.one('SELECT processed_at FROM events WHERE id=?',(source['id'],))['processed_at'])
        self.assertEqual(original['processing_control_returns'],self.store.rows('SELECT * FROM processing_control_returns'))
        for row in original['attempts']:self.assertEqual(row,self.store.attempt(row['id']))
        self.assertEqual(source_bytes,self.store.one('SELECT payload,hash,received FROM events WHERE id=?',(source['id'],)))
        self.assertEqual(child_bytes,self.store.one('SELECT payload,hash,received,parent FROM events WHERE id=?',(returned['response'],)))
        self.assertEqual(self.store.rows('SELECT * FROM jobs'),[])

    def test_automatic_delegated_collected_structured_scope_nonempty(self):
        source,attempt,request=self.conserved(automatic=True)
        original=self.store.attempt(attempt)
        with patch.object(self.boards['Work'].store,'acting_session',side_effect=AssertionError('native owner availability required')):
            processing.apply_control(self.store,source['id'],attempt)
            self.fresh();self.runtime.receipts();self.store.complete_events()
        self.assertIsNotNone(self.store.one('SELECT processed_at FROM events WHERE id=?',(source['id'],))['processed_at'])
        self.assertEqual(original,self.store.attempt(attempt))
        disposition=self.store.one('SELECT * FROM plain_control_dispositions WHERE event=?',(source['id'],))
        self.assertEqual(disposition['actor'],original['session'])
        self.assertFalse(json.loads(disposition['request'])['authority']['native_owner_receipt'])
        self.assertEqual(self.store.rows('SELECT * FROM processing_control_returns'),[])

    def test_scalar_marker_evidence_refused_despite_valid_outer_evidence(self):
        scope=dict(scope='no-new-owned-work-or-effects',accounting=[],
            evidence='Whole source interpreted; no new owned work or effects')
        source,attempt,_=self.original(plain_scope=scope)
        original=self.store.attempt(attempt)
        receipt=json.loads(json.loads(original['result'])['decision_json'])
        self.assertIsInstance(receipt['evidence'],list)
        with self.assertRaisesRegex(Refusal,'whole-source Work interpretation evidence required'):
            processing.apply_control(self.store,source['id'],attempt)
        self.assertEqual(original,self.store.attempt(attempt))
        self.assertIsNone(self.store.input_resolution(source['id']))
        self.assertIsNone(self.store.one('SELECT processed_at FROM events WHERE id=?',(source['id'],))['processed_at'])
        self.assertEqual(self.store.rows('SELECT * FROM plain_control_dispositions'),[])
        self.assertEqual(self.store.rows('SELECT * FROM processing_control_returns'),[])

    def test_pending_descendant_reserved_and_effect_consumers_refuse_before_source(self):
        for case in ('child','reserved','effect','forged'):
            source,attempt,request,returned=self.returned();child=returned['response']
            if case=='child':
                payload=dict(id='pending-'+child,kind='response',role='Work',parent=child)
                self.store.db.execute('INSERT INTO events(id,role,payload,hash,received,parent) VALUES(?,?,?,?,?,?)',
                    (payload['id'],'Work',encode(payload),digest(payload),self.store.clock(),child))
            elif case=='reserved':
                self.store.db.execute("UPDATE queue SET job='actual-job',state='reserved' WHERE event=?",(child,))
            elif case=='effect':
                with self.store.tx():self.store._outbox('Work','Reviews','question',dict(meaning='unknown effect'),event=child)
            else:request['consumer_disposition']['source_hash']='forged'
            with self.subTest(case=case),patch.object(self.store,'event',side_effect=AssertionError('protected source acquired')):
                with self.assertRaises(Refusal):self.command(source,attempt,request)

    def test_unknown_message_owned_and_stale_source_pins_block(self):
        source,attempt,request=self.conserved()
        for key,value in [('event',source['id']),('disposition','pending-this-message'),('owner','unknown'),('source_hash','forged')]:
            bad=copy.deepcopy(request);bad['accounting'][0][key]=value
            with self.subTest(key=key),self.assertRaises(Refusal):self.command(source,attempt,bad)
        self.command(source,attempt,request);self.fresh();self.runtime.receipts()
        self.store.db.execute('UPDATE processing_capabilities SET revoked=? WHERE id=?',(self.store.clock(),self.cap))
        self.store.complete_events()
        self.assertIsNone(self.store.one('SELECT processed_at FROM events WHERE id=?',(source['id'],))['processed_at'])

    def test_current_work_external_conservation_attestation(self):
        source,attempt,request=self.conserved()
        entry=request['accounting'][0];entry.update(event='Work274/exact-source',source_hash='a'*64,
            attestation=dict(reference='/explicit/current/public/Work274-receipt',observed=self.store.clock()))
        self.command(source,attempt,request);self.fresh();self.runtime.receipts();self.store.complete_events()
        self.assertIsNotNone(self.store.one('SELECT processed_at FROM events WHERE id=?',(source['id'],))['processed_at'])

    def test_tool_metadata_and_binding_refuse_before_protected_body(self):
        source,attempt,request=self.conserved();original=self.store.attempt(attempt)
        detail=json.loads(original['detail'])
        for tool in ({},dict(complete=True,items=[],nonzero_completions=[]),dict(complete=True,items=['effect'],nonzero_completions=[],unknown_types=[])):
            self.store.db.execute('UPDATE attempts SET detail=? WHERE id=?',(encode({**detail,'tool_completion':tool}),attempt))
            with patch.object(self.store,'event',side_effect=AssertionError('tool-unqualified source acquired')):
                with self.assertRaises(Refusal):self.command(source,attempt,request)
        self.store.db.execute('UPDATE attempts SET detail=?,binding=? WHERE id=?',(original['detail'],encode({'model':'forged'}),attempt))
        with patch.object(self.store,'event',side_effect=AssertionError('forged-binding source acquired')):
            with self.assertRaises(Refusal):self.command(source,attempt,request)

    def test_software_cannot_invent_scope_or_impersonate_work(self):
        source,attempt,request=self.conserved()
        with self.assertRaises(Refusal):plain_control.apply(self.store,source['id'],attempt,request,software=True)
        original=self.store.attempt(attempt);result=json.loads(original['result'])
        request['authority']=plain_control.software_authority(self.store.processing.current()[0],original,result)
        with self.assertRaises(Refusal):plain_control.apply(self.store,source['id'],attempt,request,software=True)
        self.assertEqual(self.store.rows('SELECT * FROM plain_control_dispositions'),[])

    def test_existing_return_mutation_fence_rolls_back(self):
        source,attempt,request,returned=self.returned();original=plain_control.validate;calls=[]
        def changed(*a,**kw):
            value=original(*a,**kw);calls.append(1)
            if len(calls)==1:self.store.set_hold(returned['response'],'consumer changed before transaction')
            return value
        with patch.object(plain_control,'validate',side_effect=changed):
            with self.assertRaises(Refusal):self.command(source,attempt,request)
        self.assertEqual(self.store.rows('SELECT * FROM plain_control_dispositions'),[])
        self.assertEqual(self.store.one('SELECT state FROM queue WHERE event=?',(returned['response'],))['state'],'queued')

class LeaseCompletion821(OwnerLease):
    def configure(self):
        super().configure()
        self.config['tasks']['qa-execution'].update(require_package_scope=True,scope_roots=[str(self.area)],effects='owner-reconcile')
    def setUp(self):
        original_select=prospective.select
        def selected(store,actor,selection):
            selection['tasks']['qa-execution']['ordinary_effects']=True
            return original_select(store,actor,selection)
        with patch.object(prospective,'select',side_effect=selected):super().setUp()
    original=Terminal817.original
    fresh=Terminal817.fresh
    def test_genuine_lease_control_terminal_raw_native_expiry_and_old_producer_conserved(self):
        self.apply()
        original=self.store.event(self.work);old_attempts=self.store.rows('SELECT * FROM attempts')
        source,attempt,request=self.original(['Old producer23773 history and Work consumer remain'])
        request['accounting']=[dict(index=0,text='Old producer23773 history and Work consumer remain',
            disposition='conserved-at-original-source',owner=self.issuer,event=self.work,source_hash=digest(original),
            evidence='Original finite returned producer remains unchanged at its actual Work consumer')]
        path=self.area/'terminal.json';path.write_text(encode(request))
        self.command(['processing-dispose-plain-control',self.cap,source['id'],'--attempt',attempt,'--receipt',str(path)])
        self.fresh();self.runtime.receipts();self.store.complete_events()
        self.assertIsNotNone(self.store.one('SELECT processed_at FROM events WHERE id=?',(source['id'],))['processed_at'])
        self.assertEqual(original,self.store.event(self.work))
        for row in old_attempts:self.assertEqual(row,self.store.attempt(row['id']))
        self.assertTrue(prospective.current(self.store,'qa-execution')['policy']['ordinary_effects'])
        with self.assertRaises(Refusal):prospective.current(self.store,'qa-execution',ordinary_effects=True)
        self.now=2200.
        with self.assertRaises(Refusal):self.store.processing.current()
