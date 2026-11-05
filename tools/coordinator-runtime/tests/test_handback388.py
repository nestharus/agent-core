"""WorkDecision387 boundary oracles; public source / private fiction only.

No model, native process, actual Board, profile or historical artifact mount.
Logical authority and collected returns are explicit fiction seams from Base.
"""
import copy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import test_bounded311 as bounded_fixtures
from coordinator_runtime import custody, publication, readiness, routine
from coordinator_runtime.appserver import AppServer
from coordinator_runtime.contracts import Refusal, digest, encode, ident
from coordinator_runtime.dispatcher import Dispatcher, RESULT_SCHEMA, job_prompt


def command(code=0):
    return {'id':'fictional-command-'+str(code),'type':'commandExecution','exit_code':code,
            'status':'completed' if code==0 else 'failed','completed_notification':True}


def answer():
    return {'semantic':'DONE','summary':'Prepared exact bounded local change','category':'complete',
            'findings':[],'failures':[],'unknowns':[],'artifacts':[], 'handoffs':[],
            'no_handoff_reason':'Private fixture result only; no external duty.',
            'completion':{'version':1,'local':'ready','failures':[],'unknowns':[],'tools':[]}}


class Handback(bounded_fixtures.Base):
    def configure(self):
        self.target=self.area/'inventory.json';self.target.write_bytes(b'old inventory\n')
        self.old=self.target.read_bytes();self.new=b'changed inventory with additional data\n'
        self.task=self.config['tasks']['wi']
        self.task.update(effects='owner-reconcile',routine_completion={'kind':'file-witness','targets':[str(self.target)]})
        self.task['effect_authority']['write_roots']=[str(self.target)]

    def prepare(self):
        # Retain an original adverse source with its actual attributed owner and
        # effect uncertainty. It is data, never an acceptance/settlement receipt.
        self.history={'owner':'fictional-original-custodian','error':'original remote effect unknown',
                      'holds':['original effect reconciliation still owed']}
        event={'id':'fictional-held-delivery','role':'Work','recipient':'fictional-logical-Work',
               'kind':'board','post':1,'package':None,'allowed_tasks':['wi'],
               'body':{'source_result':{'failures':[self.history]},'disposition':'INCOMPLETE; held'}}
        self.event=copy.deepcopy(event);self.store.ingest(event)
        self.store.db.execute("UPDATE events SET state='queued',ack='done' WHERE id=?",(event['id'],))
        self.store.db.execute("INSERT INTO queue VALUES(?,?,?,'integrator','wi',NULL,'queued',NULL)",
                              (event['id'],event['id'],'Work'))
        self.current=self.store.reserve();self.attempt=self.store.start_job(self.current['id'],self.current['token'])
        (self.store.home/'artifacts'/self.attempt).mkdir(parents=True)
        self.current=self.store.job(self.current['id'])
        routine.prepare(self.store,self.board,self.current,self.attempt,self.task)
        self.stage=Path(publication.stages(self.store,self.attempt)[str(self.target)])
        self.stage.write_bytes(self.new)

    def input_claim(self):
        return {'path':str(self.target),'sha256':hashlib.sha256(self.old).hexdigest(),'bytes':len(self.old),
                'kind':'input-preimage','anchor':'original exact inventory'}

    def inherited(self):
        value=answer();value['failures']=[copy.deepcopy(self.history)]
        # Exact controller-source contract, independently assembled from the
        # known frozen input oracle rather than copied from the implementation.
        value['completion']['failures']=[{'index':0,'status':'inherited',
            'source':{'kind':'event','id':self.event['id'],'sha256':digest(self.event),
                      'path':['body','source_result','failures',0]},
            'reason':'Original custodian still owns remote uncertainty; this local inventory change does not settle it.'}]
        return value

    def collect(self,value,items=None):
        self.store.begin(self.attempt,{'fictional':True})
        outcome={'result':value,'exit':0,'capture':'complete','cleanup':'not-native','error':None,
                 'detail':{'tool_completion':{'complete':True,'items':items if items is not None else [command()]}}}
        self.store.collect(self.attempt,outcome)
        Dispatcher(self.store,models=object(),boards={}).inventory_artifacts(self.attempt,outcome,self.task)

    def test_declared_preimage_and_explicit_postimage_both_survive_publication(self):
        self.prepare();value=answer();value['artifacts']=[{'common':'exact distinct claims','files':[
            self.input_claim(),{'path':str(self.stage),'sha256':hashlib.sha256(self.new).hexdigest(),
                                'bytes':len(self.new),'kind':'postimage'}]}]
        original=copy.deepcopy(value);self.collect(value)
        self.assertTrue(routine.reconcile(self.store,self.board,self.current))
        self.assertEqual(self.target.read_bytes(),self.new)
        self.assertEqual(json.loads(self.store.attempt(self.attempt)['result']),original)
        for path,body in [(self.target,self.old),(self.stage,self.new)]:
            row=self.store.one('SELECT sha256 FROM artifact_custody WHERE attempt=? AND path=?',(self.attempt,str(path)))
            self.assertEqual(self.store.one('SELECT body FROM artifact_blobs WHERE sha256=?',(row['sha256'],))['body'],body)
        witness=json.loads(self.store.one('SELECT witness FROM file_publications')['witness'])
        self.assertEqual(witness['sha256'],hashlib.sha256(self.new).hexdigest())

    def test_unqualified_canonical_string_keeps_input_identity_and_stages_are_conserved(self):
        self.prepare();value=answer();value['artifacts']=[str(self.target)];self.collect(value)
        held=self.store.one('SELECT sha256 FROM artifact_custody WHERE attempt=? AND path=?',(self.attempt,str(self.target)))
        self.assertEqual(held['sha256'],hashlib.sha256(self.old).hexdigest())
        self.assertIsNotNone(self.store.one('SELECT path FROM artifact_custody WHERE path=?',(str(self.stage),)))

    def test_stale_source_and_stage_integrity_claims_still_refuse(self):
        self.prepare()
        for path in [self.target,self.stage]:
            with self.subTest(path=path):
                value=answer();value['artifacts']=[{'path':str(path),'sha256':'0'*64,'bytes':3}]
                with self.assertRaisesRegex(Refusal,'hash/bytes'):custody.inventory(self.store,self.attempt,value,self.task)
        self.assertEqual(self.target.read_bytes(),self.old)

    def test_canonical_change_after_claim_refuses_before_publication(self):
        self.prepare();value=answer();value['artifacts']=[self.input_claim()];self.collect(value)
        self.target.write_bytes(b'peer changed it\n')
        with self.assertRaisesRegex(Refusal,'canonical bytes changed'):routine.reconcile(self.store,self.board,self.current)
        self.assertEqual(self.target.read_bytes(),b'peer changed it\n')
        self.assertEqual(self.store.rows('SELECT * FROM file_publications'),[])

    def test_stage_mutation_after_custody_still_blocks_publication(self):
        self.prepare();self.collect(answer());self.stage.write_bytes(b'changed after custody\n')
        with self.assertRaisesRegex(Refusal,'exact durable custody'):routine.reconcile(self.store,self.board,self.current)
        self.assertEqual(self.target.read_bytes(),self.old)
        self.assertEqual(self.store.rows('SELECT * FROM file_publications'),[])

    def test_valid_inline_proposer_needs_no_artifact_or_stage(self):
        job,attempt=self.job('Work','wp');value=answer();value['category']='proposal'
        value['findings']=[{'delta':{'selector':'exact entry','precondition':'known peer bytes'},
                            'new_log_entry':'Prepared new entry\n','log_mention':str(self.area/'WORK_LOG.md')}]
        custody.inventory(self.store,attempt,value,self.config['tasks']['wp'])
        self.assertEqual(publication.stages(self.store,attempt),{})
        self.assertEqual(self.store.rows('SELECT * FROM artifact_custody'),[])

    def test_log_directory_exclusion_and_outside_root_remain_acquisition_refusals(self):
        self.prepare();log=self.area/'WORK_LOG.md';log.write_bytes(b'fictional forbidden body')
        for path,meta in [(log,{'read_extent':'NONE'}),(self.area,{'read_extent':'header-only'}),
                          (Path('/foreign/unmounted'),{})]:
            with self.subTest(path=path):
                with self.assertRaises(Refusal):custody.inventory(self.store,self.attempt,{'artifacts':[{'path':str(path),**meta}]},self.task)
        self.config['artifact_exclusions']=[str(self.target)]
        with patch('coordinator_runtime.custody.safe_path',side_effect=AssertionError('metadata reached')):
            with self.assertRaisesRegex(Refusal,'excluded'):custody.inventory(self.store,self.attempt,{'artifacts':[str(self.target)]},self.task)

    def test_inherited_debt_allows_local_completion_without_resolving_original(self):
        self.prepare();value=self.inherited();value['artifacts']=[self.input_claim()]
        self.assertEqual(readiness.live_issues(self.store,self.attempt,value,[command()],self.task),[])
        prompt=job_prompt(self.store,self.current,self.task)
        self.assertIn('inherited_failure_sources',prompt);self.assertIn(encode(self.history),prompt)
        self.collect(value);self.assertTrue(routine.reconcile(self.store,self.board,self.current))
        receipt=json.loads(self.store.job(self.current['id'])['effect_receipt'])['local_readiness']
        self.assertEqual(receipt['original_failures'],[self.history])
        self.assertEqual(receipt['resolved_history'],[])
        self.assertEqual(receipt['inherited_history'][0]['status'],'inherited')
        self.assertEqual(self.store.event(self.event['id']),self.event)
        self.assertIsNone(self.store.one('SELECT processed_at FROM events WHERE id=?',(self.event['id'],))['processed_at'])

    def test_inherited_label_cannot_cover_new_local_defect_or_current_adverse_command(self):
        self.prepare();value=self.inherited()
        for mutate in ['source','typed-path','failure','local','adverse']:
            with self.subTest(mutate=mutate):
                bad=copy.deepcopy(value);items=[command()]
                if mutate=='source':bad['completion']['failures'][0]['source']['sha256']='0'*64
                if mutate=='typed-path':bad['completion']['failures'][0]['source']['path'][-1]=False
                if mutate=='failure':bad['failures'][0]['error']='new local invariant failed'
                if mutate=='local':
                    bad['failures'].append('current local construction failed')
                    bad['completion']['failures'].append({'index':1,'status':'unresolved','evidence':[],'verification_items':[]})
                if mutate=='adverse':items.append(command(1))
                self.assertTrue(readiness.live_issues(self.store,self.attempt,bad,items,self.task))
        value['failures'].append('current local construction failed');value['completion']['local']='blocked'
        value['completion']['failures'].append({'index':1,'status':'unresolved','evidence':[],'verification_items':[]})
        self.assertEqual(readiness.live_issues(self.store,self.attempt,value,[command()],self.task),[])
        self.collect(value)
        with self.assertRaisesRegex(Refusal,'not ready'):readiness.assess(self.store,self.store.attempt(self.attempt))
        self.assertEqual(self.target.read_bytes(),self.old)

    def test_collected_inherited_claim_is_rechecked_against_exact_frozen_source(self):
        self.prepare();value=self.inherited();self.collect(value)
        changed=copy.deepcopy(self.event);changed['body']['disposition']='changed after freezing'
        self.store.db.execute('UPDATE events SET payload=? WHERE id=?',(encode(changed),changed['id']))
        with self.assertRaisesRegex(Refusal,'frozen failure source changed'):readiness.assess(self.store,self.store.attempt(self.attempt))

    def test_inherited_history_does_not_waive_incomplete_command_metadata(self):
        self.prepare();self.collect(self.inherited())
        row=self.store.attempt(self.attempt);detail=json.loads(row['detail']);detail['tool_completion']['complete']=False
        self.store.db.execute('UPDATE attempts SET detail=? WHERE id=?',(encode(detail),self.attempt))
        with self.assertRaisesRegex(Refusal,'unsettled tool metadata'):readiness.assess(self.store,self.store.attempt(self.attempt))
        self.assertFalse(routine.reconcile(self.store,self.board,self.current))
        self.assertEqual(self.target.read_bytes(),self.old)


class BoundedStage(bounded_fixtures.Base):
    configure=bounded_fixtures.Catalog.configure
    prepare=bounded_fixtures.Catalog.prepare
    # Reuse the existing seven-duty fixture's oracles without selecting all of
    # its unrelated tests here; this case keeps whole-log acquisition blocked.
    def test_bounded_new_entry_and_six_input_claims_remain_distinct(self):
        self.prepare();value=answer()
        value['artifacts']=[{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),
                             'bytes':p.stat().st_size} for p in self.peers]
        self.collected(self.attempt)
        Dispatcher(self.store,models=object(),boards={}).inventory_artifacts(self.attempt,{'result':value},self.task)
        self.assertTrue(routine.reconcile(self.store,self.board,self.current))
        self.assertEqual(self.log.read_bytes(),self.entry+self.old)
        self.assertEqual(len(self.store.rows('SELECT * FROM file_publications')),7)
        self.assertIsNone(self.store.one('SELECT path FROM artifact_custody WHERE path=?',(str(self.log),)))


class MetadataContinuation(unittest.IsolatedAsyncioTestCase):
    async def test_partial_gets_own_ids_once_and_can_remain_partial(self):
        first=answer();first.update(semantic='PARTIAL',failures=['Own successful protocol IDs unavailable'])
        first['completion']['local']='blocked'
        for code in [0,1]:
            with self.subTest(code=code):
                prompts=[];turns=[];history={};initial=ident()
                class Pool:
                    def admission(self,profile):return self
                    async def __aenter__(self):return self
                    async def __aexit__(self,*args):pass
                class Peer:
                    tools={'fictional':command(code)};unknown_tools=set()
                    async def completion(self,*args):return copy.deepcopy(first)
                    async def rpc(self,method,params):
                        self_check=method=='thread/read'
                        if not self_check:raise AssertionError(method)
                        return {'thread':{'id':initial,'status':{'type':'idle'}}}
                store=SimpleNamespace(execution_pool=Pool(),authorize_launch=lambda a:None,
                    attempt=lambda a:{'kind':'task','profile':None},session=lambda *args:turns.append(args))
                adapter=AppServer({'deadlines':{'task':2}})
                async def start(*args):prompts.append(args[2]);return {'turn':{'id':ident()}}
                outcome={'detail':history};spec={'routine_completion':{'kind':'file-witness'}}
                with patch.object(adapter,'start_turn',start):
                    final=await adapter.turn(Peer(),store,'fictional',initial,'initial prompt',spec,{},RESULT_SCHEMA,outcome)
                self.assertEqual(len(prompts),2);self.assertEqual(len(turns),2)
                self.assertIn('OBSERVED_TOOL_METADATA=',prompts[1]);self.assertIn(command(code)['id'],prompts[1])
                self.assertEqual(final,first);self.assertEqual(outcome['detail']['prior_turn_result'],first)
                self.assertEqual(final['semantic'],'PARTIAL')
