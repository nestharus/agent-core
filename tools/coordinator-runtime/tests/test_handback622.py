"""Selected C1/C2/C3 through public fictional transport and original gates."""
import copy
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import test_writer_custody as fixtures
from support import queued, event, ident, config_at
from coordinator_runtime import readiness, routine, software
from coordinator_runtime.appserver import AppServer
from coordinator_runtime.board import Board, module_at
from coordinator_runtime.dispatcher import Dispatcher
from coordinator_runtime.contracts import Refusal, collected_task_result, collected_capture, digest, encode


class FutureContract(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='correction3-fixture-')
        self.addCleanup(self.temp.cleanup)
        self.config=config_at(self.temp.name)
        self.config['session_storage']={'mode':'producer-owned'}
        self.target=Path(self.temp.name)/'canonical.json'
        self.target.write_text('{"total":0}')
        task=self.config['tasks']['work-integrator']
        task.update(effects='owner-reconcile',sandbox='workspace-write',network=False,
                    routine_completion={'kind':'file-witness','targets':[str(self.target)]},delivery_required=True,allowed_handoffs=[])
        task['effect_authority'].update(write_roots=[str(self.target)],operations=['read-reports','write-role-records'])
        if self._testMethodName.startswith('test_unique_response'):
            for i in range(6):
                target=Path(self.temp.name)/('consumer-'+str(i)+'.json');target.write_text('{"total":0}')
                task['routine_completion']['targets'].append(str(target))
                task['effect_authority']['write_roots'].append(str(target))
        self.owner=self.config['roles']['Work']['owner']
        self.sender=ident()
        self.config['delivery']={'recipients':{'Work':{'session':self.owner,'profile':'.codex','board_role':'work'}},'alert_role':'Work','alert_recipient':'Work'}
        if getattr(self,'include_root',False):
            self.root=ident()
            self.config['delivery']['recipients']['Root']={'session':self.root,'profile':'.codex2','board_role':'execution-manager'}
            task['allowed_handoffs']=['Root']
        from coordinator_runtime.store import Store
        self.store=Store(self.config)
        self.addCleanup(self.store.close)
        self.substrate=module_at(self.config['board_library'],'board_store')
        catalog=module_at(self.config['board_library'],'catalog')
        home=Path(self.config['board_home'])
        with catalog.catalog(home) as cat:
            entry=catalog.create(cat,home,'custody','Owned L01-L05 test',board_id=self.config['roles']['Work']['board_id'],temporary_test=True)
        self.path=Path(entry['db_path'])
        with self.substrate.database(str(self.path)) as conn:
            self.substrate.bind_board(conn,entry['board_id'],initialize=True)
            actors=[(self.owner,'work','.codex'),(self.sender,'sender','.codex')]
            if getattr(self,'include_root',False):actors.append((self.root,'execution-manager','.codex2'))
            for actor,role,profile in actors:
                args=self.substrate.parser().parse_args(['register','--session',actor,'--role',role,'--profile',profile,'--route','managed'])
                with patch.dict(os.environ,{'CODEX_SESSION_ID':actor}):self.substrate.register(conn,args)
        self.board=Board(self.config,'Work')
        with patch.dict(os.environ,{'CODEX_SESSION_ID':self.owner}):
            grant=self.board.grant(self.store,'Synthetic genuine-owner routine delegation',delivery=True,completion=True)
        self.store.enroll('Work',grant)
        self.store.reconcile_legacy('Work',self.owner,{'collector':self.owner,'evidence':['synthetic closed original'],'remaining_holds':[]})
        self.runtime=Dispatcher(self.store,models=object(),boards={'Work':self.board})


    async def run_boundary(self, **changes):
        queued(self.store,event(self.config,ident()))
        job=self.store.reserve();attempt=self.store.start_job(job['id'],job['token'])
        base=Path(self.temp.name)
        self.plan={'target':str(self.target),'report':str(self.store.home/'artifacts'/attempt/'verification.json'),
            'record':str(base/'turns.jsonl'),'writes':str(base/'writes.txt'),
            'partial':True,'conflict':True,**changes}
        path=base/'plan.json';path.write_text(encode(self.plan))
        self.runtime.models=AppServer(self.config,[sys.executable,str(Path(__file__).with_name('fixture_handback622.py')),str(path)])
        await self.runtime.execute(job['id'],attempt)
        self.attempt=attempt;self.job=job;self.row=self.store.attempt(attempt)
        self.detail=json.loads(self.row['detail'])
        self.answer=json.loads(self.row['result']) if self.row['result'] else None
        self.records=[json.loads(line) for line in Path(self.plan['record']).read_text().splitlines()]
        self.assertEqual(self.row['exit'],0)
        self.assertIsNotNone(self.row['ended']);self.assertIsNotNone(self.row['collected'])
        self.assertEqual(self.detail['teardown'],'actual-owned-process-exit-collected')
        self.assertEqual(len(Path(self.plan['writes']).read_text().splitlines()),1)
        return job,attempt

    def held(self, turns=2):
        self.assertEqual(len(self.records),turns)
        self.assertEqual(self.store.job(self.job['id'])['effects'],'unknown')
        self.assertEqual(self.store.job(self.job['id'])['state'],'held')
        self.assertEqual(json.loads(self.target.read_text()),{'total':0})
        self.assertEqual(self.store.rows('SELECT * FROM file_publications'),[])

    async def test_unique_response_resolved_unknown_and_seven_publications_keep_all_originals(self):
        job,attempt=await self.run_boundary()
        self.assertIsNone(self.row['error'],self.row['error'])
        self.assertTrue(collected_capture(self.row),self.detail.get('handback_receipt_failure'))
        self.assertEqual(self.row['capture'],'conflicting-final')
        self.assertEqual(len(self.detail['terminal_return_evidence']),3)
        self.assertFalse(self.detail['prior_terminal_returns'][0]['valid_json'])
        original=self.detail['prior_terminal_returns'][1]['typed_return']
        for key in ['findings','failures','unknowns','artifacts','handoffs']:
            self.assertEqual(self.answer[key],original[key])
        self.assertEqual(original['semantic'],'PARTIAL')
        self.assertEqual(original['completion']['unknowns'][0]['status'],'unresolved')
        self.assertIn('conflicting',self.detail['original_handback_error'])
        self.assertEqual(collected_task_result(self.row),self.answer)
        local=readiness.assess(self.store,self.row)
        self.assertEqual(len(local['resolved_local_unknowns']),1)
        self.assertEqual(local['original_unknowns'],original['unknowns'])
        self.assertEqual(local['subsequent_duties'],[])
        self.assertEqual(self.store.job(job['id'])['effects'],'reconciled')
        published=self.store.rows('SELECT * FROM file_publications WHERE attempt=?',(attempt,))
        self.assertEqual(len(published),7)
        self.assertTrue(all(p['state']=='published' for p in published))
        self.assertTrue(all(json.loads(Path(p['target']).read_text())=={'total':12} for p in published))
        receipt=json.loads(self.store.job(job['id'])['effect_receipt'])
        self.assertEqual(len(receipt['publication']),7)
        self.assertEqual(receipt['local_readiness']['handback_receipt'],self.detail['handback_receipt'])
        # Normal consumer processing is still unsettled; no END=>acceptance shortcut.
        self.assertIsNone(self.store.one('SELECT processed_at FROM events')['processed_at'])
        queued(self.store,self.store.event(self.store.job(job['id'])['response']))
        self.runtime.receipts();self.runtime.pump_deliveries();self.runtime.reconcile_completed()
        current=self.store.job(job['id'])
        # 625: normal delivery consumes the independently qualified current
        # response without upgrading the immutable original conflicting capture.
        self.assertEqual(current['state'],'closed')
        self.assertIsNotNone(software._processing(self.store,current))
        outbox=self.store.one("SELECT * FROM outboxes WHERE job=? AND kind='result'",(job['id'],))
        self.assertEqual(self.board.complete_own_delivery(self.store,outbox)['state'],'settled')
        self.assertIsNotNone(self.store.one('SELECT processed_at FROM events')['processed_at'])
        self.assertEqual(self.store.attempt(attempt)['capture'],'conflicting-final')

    async def test_receipt_tampering_old_capture_and_forged_model_fields_refuse(self):
        await self.run_boundary()
        self.assertTrue(collected_capture(self.row),self.detail.get('handback_receipt_failure'))
        mutations={
            'missing':lambda d:d.pop('handback_receipt'),
            'forged-issuer':lambda d:d['handback_receipt'].update(issuer=ident()),
            'hash':lambda d:d['handback_receipt'].update(result_hash='0'*64),
            'boundary':lambda d:d['handback_boundary'].update(owned_idle=False),
            'source':lambda d:d['handback_receipt']['binding'].update(binding=encode({'model':'forged'})),
            'original-erased':lambda d:d['prior_terminal_returns'].pop(0),
            'unknown-tools':lambda d:d['tool_completion'].update(complete=False),
            'missing-close':lambda d:d['tool_completion']['items'][0].update(completed_notification=False),
            'turn':lambda d:d['terminal_return_evidence'][-1].update(turn=ident()),
            'competing':lambda d:d['terminal_return_evidence'].append({**d['terminal_return_evidence'][-1],
                'item':'competing','typed_return':{**self.answer,'summary':'competing'}}),
        }
        for name,mutate in mutations.items():
            with self.subTest(case=name):
                row=dict(self.row);detail=copy.deepcopy(self.detail);mutate(detail);row['detail']=encode(detail)
                self.assertFalse(collected_capture(row))
                with self.assertRaises(Refusal):collected_task_result(row)
        for key,value in [('begin',None),('state','unknown'),('kind','diagnosis'),('session',ident()),('turn',ident()),('controller',ident()),('binding','{}'),('exit',None),('ended',None),('collected',None),('error','unknown-effect'),('capture','artifact-inventory-incomplete')]:
            with self.subTest(field=key):self.assertFalse(collected_capture({**self.row,key:value}))
        old=copy.deepcopy(self.row);old['detail']=encode({k:v for k,v in self.detail.items() if k not in {'handback_receipt','handback_boundary'}})
        self.assertFalse(collected_capture(old))
        forged={**self.answer,'handback_receipt':self.detail['handback_receipt']}
        with self.assertRaises(Refusal):
            from coordinator_runtime.contracts import task_result
            task_result(forged)

    async def test_causal_witness_rejects_unrelated_ambiguous_or_changed_commands(self):
        await self.run_boundary();local=readiness.assess(self.store,self.row)
        items=self.detail['tool_completion']['items'];priors=readiness.prior_handbacks(self.detail)
        bodies={}
        for ref in self.answer['completion']['unknowns'][0]['evidence']:
            bodies[(ref['path'],ref['sha256'])]=Path(ref['path']).read_bytes()
        def inspect(answer,rows=items):
            return readiness.inspect(answer,rows,self.config['tasks']['work-integrator'],self.config,
                lambda r:bodies.get((r['path'],r['sha256'])),prior_results=priors,strict_correlation=True)[2]
        self.assertEqual(inspect(self.answer),[])
        downstream=copy.deepcopy(self.answer)
        downstream['unknowns'].append('Publication and review remain with original downstream owners.')
        downstream['completion']['unknowns'].append({'index':1,'duties':[
            {'status':'deferred','owner':'controller','duty':'publication','reason':'Exact publisher remains responsible.'},
            {'status':'boundary','owner':'outside-workflow','duty':'acceptance','reason':'Genuine owner acceptance remains unestablished.'}]})
        proof,duties,issues=readiness.inspect(downstream,items,self.config['tasks']['work-integrator'],self.config,
            lambda r:bodies.get((r['path'],r['sha256'])),prior_results=priors,strict_correlation=True)
        self.assertEqual(issues,[])
        self.assertEqual([d['status'] for d in duties],['resolved','deferred','boundary'])
        variants=[]
        bad=copy.deepcopy(self.answer);bad['completion']['tools'][0]['verification_items']=['tool-3'];variants.append(bad)
        bad=copy.deepcopy(self.answer);bad['completion']['tools'][0]['command_bindings'][-1]['turn']=ident();variants.append(bad)
        bad=copy.deepcopy(self.answer);bad['completion']['unknowns'][0]['command_bindings'][0]['command_sha256']='0'*64;variants.append(bad)
        bad=copy.deepcopy(self.answer);bad['completion']['unknowns'][0]['owner']='controller';variants.append(bad)
        bad=copy.deepcopy(self.answer);bad['completion']['unknowns'][0]['prior_disposition']['reason']='reclassified';variants.append(bad)
        bad=copy.deepcopy(self.answer);bad['completion']['unknowns'][0]['verification_items']=[];variants.append(bad)
        for index,bad in enumerate(variants):
            with self.subTest(case=index):self.assertTrue(inspect(bad))
        bad=copy.deepcopy(self.answer)
        bad['completion']['unknowns'][0]={'index':0,'status':'deferred','owner':'controller','duty':'publication',
            'reason':'Relabel local protocol work as downstream.'}
        self.assertTrue(any('reclassified' in issue for issue in inspect(bad)))
        grouped=copy.deepcopy(priors)
        entry=grouped[-1]['completion']['unknowns'][0]
        original_duty={k:v for k,v in entry.items() if k!='index'}
        grouped[-1]['completion']['unknowns'][0]={'index':0,'duties':[original_duty,
            {**original_duty,'duty':'another-genuinely-unresolved-local-duty'}]}
        issues=readiness.inspect(self.answer,items,self.config['tasks']['work-integrator'],self.config,
            lambda r:bodies.get((r['path'],r['sha256'])),prior_results=grouped,strict_correlation=True)[2]
        self.assertTrue(any('reclassified' in issue for issue in issues))
        self.assertTrue(inspect(self.answer,items+[items[0]]))
        self.assertEqual(self.answer['unknowns'],local['original_unknowns'])

    async def test_unrelated_success_refused_by_actual_path(self):
        await self.run_boundary(unrelated=True);self.held()
        self.assertIn('causal witness',self.row['error'])
        self.assertNotIn('handback_receipt',self.detail)

    async def test_erased_unknown_refused_by_actual_path(self):
        await self.run_boundary(erased_unknown=True);self.held()
        self.assertIn('original unknowns',self.detail['handback_clarification_failure'])

    async def test_changed_owner_refused_by_actual_path(self):
        await self.run_boundary(changed_owner=True);self.held()
        self.assertIn('owner/duty/reason',self.row['error'])

    async def test_unresolved_local_unknown_stays_partial(self):
        await self.run_boundary(unresolved=True);self.held()
        self.assertEqual(self.answer['semantic'],'PARTIAL')
        self.assertEqual(self.answer['completion']['local'],'blocked')
        self.assertEqual(self.answer['unknowns'],self.detail['prior_terminal_returns'][1]['typed_return']['unknowns'])

    async def test_current_competing_finals_refuse(self):
        await self.run_boundary(second_conflict=True);self.held()
        self.assertNotIn('handback_receipt',self.detail)
        self.assertEqual(len(self.detail['terminal_return_evidence']),4)

    async def test_late_current_final_refuses_after_closure(self):
        await self.run_boundary(late_current=True);self.held()
        self.assertFalse(collected_capture(self.row))
        self.assertIn('late-final-needs-reconciliation',self.detail['capture_issues'])

    async def test_missing_tool_closure_refuses_before_continuation(self):
        await self.run_boundary(incomplete_tool=True);self.held(1)
        self.assertFalse(self.detail['tool_completion']['complete'])

    async def test_foreign_final_refuses(self):
        await self.run_boundary(foreign_final=True);self.held(1)
        self.assertFalse(collected_capture(self.row))

    async def test_nonidle_owner_refuses(self):
        await self.run_boundary(read_status='active');self.held(1)
        self.assertIn('idle',self.detail['handback_clarification_failure'])

    async def test_changed_current_source_at_collection_refuses_receipt(self):
        original=AppServer.teardown
        async def revoke(adapter,child,peer,outcome):
            await original(adapter,child,peer,outcome)
            self.store.authorize_launch=lambda attempt: (_ for _ in ()).throw(Refusal('changed exact point/admission/source'))
        with patch.object(AppServer,'teardown',revoke):await self.run_boundary()
        self.held();self.assertIn('changed exact point',self.detail['handback_receipt_failure'])

    async def test_closed_owner_and_budget_refuse(self):
        original=AppServer.continue_idle
        async def exhausted(adapter,peer,*args,**kwargs):
            peer.continuation_used=True
            return await original(adapter,peer,*args,**kwargs)
        with patch.object(AppServer,'continue_idle',exhausted):await self.run_boundary()
        self.held(1);self.assertIn('single continuation',self.detail['handback_clarification_failure'])

    async def test_nonconflicting_partial_can_resolve_unknown_with_same_contract(self):
        await self.run_boundary(conflict=False)
        self.assertEqual(self.row['capture'],'complete')
        self.assertIsNone(self.row['error'])
        self.assertEqual(self.store.job(self.job['id'])['effects'],'reconciled')
        self.assertEqual(readiness.assess(self.store,self.row)['original_unknowns'],self.detail['prior_turn_result']['unknowns'])

    async def test_current_effect_hold_still_blocks_publication(self):
        original=AppServer.teardown
        async def held(adapter,child,peer,outcome):
            await original(adapter,child,peer,outcome)
            attempt=self.store.one("SELECT * FROM attempts WHERE kind='task'")
            reason='actual fictional current effect uncertainty retains original custodian'
            outcome['detail']['original_current_effect_hold']=reason
            self.store.hold_job(attempt['job'],reason)
        with patch.object(AppServer,'teardown',held):await self.run_boundary()
        self.held()
        self.assertIn('effect uncertainty',self.detail['original_current_effect_hold'])
        self.assertIn('publication remains incomplete',self.store.job(self.job['id'])['hold_reason'])

    async def test_model_or_outcome_alone_cannot_issue_collector_receipt(self):
        from support import result
        queued(self.store,event(self.config,ident()));job=self.store.reserve()
        attempt=self.store.start_job(job['id'],job['token'])
        self.store.begin(attempt,{'fixture':True});self.store.session(attempt,ident(),ident())
        self.store.collect(attempt,{'exit':0,'capture':'conflicting-final','error':None,
            'cleanup':'fictional','result':result(),'detail':{'handback_receipt':{'version':1},
            'handback_boundary':{'owned_idle':True}}})
        row=self.store.attempt(attempt);detail=json.loads(row['detail'])
        self.assertNotIn('handback_receipt',detail);self.assertNotIn('handback_boundary',detail)
        self.assertFalse(collected_capture(row))
        self.store.finish_job(job['id'],job['token'])
        self.assertEqual(self.store.job(job['id'])['state'],'held')


class InheritedCompatibility(unittest.TestCase):
    def test_frozen_inherited_failure_is_conserved_without_resolving_original(self):
        from support import result
        history={'error':'old actual failure remains with original custodian'}
        source={'kind':'event','id':'frozen-fiction','sha256':digest(history),'path':['failures',0]}
        answer={**result(),'failures':[history],'completion':{'version':1,'local':'ready',
            'failures':[{'index':0,'status':'inherited','source':source,'reason':'Outside current local scope; original custodian retained.'}],
            'unknowns':[],'tools':[]}}
        before=copy.deepcopy(answer)
        sources=[{'source':source,'failure':history}]
        self.assertEqual(readiness.inspect(answer,[],inherited_sources=sources)[2],[])
        self.assertEqual(answer,before)
        changed=copy.deepcopy(answer);changed['failures'][0]['error']='new current failure'
        self.assertTrue(readiness.inspect(changed,[],inherited_sources=sources)[2])
        blocked=copy.deepcopy(answer);blocked['failures'].append('current unresolved defect')
        blocked['completion']['failures'].append({'index':1,'status':'unresolved','evidence':[],'verification_items':[]})
        self.assertTrue(readiness.inspect(blocked,[],inherited_sources=sources)[2])
