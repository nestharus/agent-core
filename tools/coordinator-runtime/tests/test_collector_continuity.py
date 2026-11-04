"""Decision22 post-restart owner command -> fresh dispatcher -> same-job remainder.

Owned temporary journals; genuine distinct Store() defaults, no borrowed IDs or
environment replacement. CLI actor/Board authority are explicit fixture seams,
not a production authentication claim. Model execution is mocked, never native.
"""
import contextlib
import io
import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock,patch

import test_receipt_diagnosis as fixtures
from support import ident
from coordinator_runtime import cli
from coordinator_runtime.contracts import LUNA,Refusal,encode
from coordinator_runtime.dispatcher import Dispatcher
from coordinator_runtime.store import Store


class CollectorContinuity(unittest.IsolatedAsyncioTestCase):
    asyncSetUp=fixtures.RetainedDiagnosis.asyncSetUp
    held=fixtures.RetainedDiagnosis.held
    request=fixtures.RetainedDiagnosis.request
    receipt=fixtures.RetainedDiagnosis.receipt
    reaffirm=fixtures.RetainedDiagnosis.reaffirm

    def continuity(self,**extra):
        return {'scope':'closure-only-after-owned-restart','from_controller':self.previous,
            'service_actor':self.config['actor'],'service_end':0,'service_collected':True,
            'evidence':['Owned synthetic service run/drain returned; original attempts actually collected in fixture'],**extra}

    async def restart(self):
        self.previous=self.store.controller
        self.before=self.store.job(self.job['id'])
        self.original_raw=self.store.attempt(self.original);self.diagnosis_raw=self.store.attempt(self.diagnosis)
        self.selection_raw=self.store.one('SELECT * FROM recovery_requests WHERE id=?',(self.selection['id'],))
        self.runtime.stopping.set()
        await self.runtime.run(lambda value:None)  # Actual owned coroutine drain; no native process/END claim.
        self.store.close()
        self.store=Store(self.config);self.addCleanup(self.store.close)
        self.assertNotEqual(self.previous,self.store.controller)
        self.runtime=Dispatcher(self.store,models=object(),boards={})
        self.runtime.execute=AsyncMock();self.runtime.recover=AsyncMock(side_effect=AssertionError('No equivalent Luna'))

    async def settle_dispatch(self):
        self.runtime.reconcile_completed()  # Real tick request/closure boundary; model execution is the seam.
        if self.runtime.active:await __import__('asyncio').gather(*self.runtime.active)

    def owner_cli(self,argv):
        config=Path(self.temp.name)/'continuity-config.json';config.write_text(encode(self.config))
        seen=[];output=io.StringIO();actor_before=os.environ.get('CODEX_SESSION_ID')
        def actual_owner(expected):
            self.assertEqual(expected,self.owner);return self.owner
        def verify(store):
            self.assertEqual(store.path,self.store.path);seen.append(store.controller)
        with patch.object(cli,'actual_actor',side_effect=actual_owner), patch.object(cli,'Board',
                return_value=SimpleNamespace(verify_authority=verify)),contextlib.redirect_stdout(output):
            code=cli.main(['--config',str(config),*argv])
        self.assertEqual(os.environ.get('CODEX_SESSION_ID'),actor_before)
        self.assertEqual(code,0,output.getvalue());self.assertTrue(seen)
        return json.loads(output.getvalue()),seen[0]

    async def test_supported_owner_cli_then_fresh_dispatcher_transfers_closure_once_with_consistent_witnesses(self):
        await self.restart()
        view,cli_controller=self.owner_cli(['owner-controls','Work','--limit','100'])
        old=view['recovery'][0]['controller']
        self.assertEqual(old,self.previous);self.assertNotIn(cli_controller,{old,self.store.controller})
        packet=self.receipt(collector_continuity=self.continuity(from_controller=old))
        path=Path(self.temp.name)/'continuity-owner.json';path.write_text(encode(packet))
        request,_=self.owner_cli(['request-recovery',self.job['id'],'--token',self.job['token'],
            '--attempt',self.original,'--receipt',str(path)])
        repeated,_=self.owner_cli(['request-recovery',self.job['id'],'--token',self.job['token'],
            '--attempt',self.original,'--receipt',str(path)])
        self.assertEqual(request,repeated)
        self.assertEqual(self.store.job(self.job['id']),self.before)  # Owner command queues, does not adopt/start.
        await self.settle_dispatch()
        state=self.store.job(self.job['id']);new=state['active_attempt']
        self.assertEqual(state['controller'],self.store.controller)
        self.assertEqual(state['recovery_owner'],self.previous)  # Original diagnosis collector is conserved.
        self.assertEqual(state['token'],self.before['token']);self.assertEqual(state['members'],self.before['members'])
        self.assertEqual(self.store.attempt(self.original),self.original_raw)
        self.assertEqual(self.store.attempt(self.diagnosis),self.diagnosis_raw)
        self.assertEqual(self.store.one('SELECT * FROM recovery_requests WHERE id=?',(self.selection['id'],)),self.selection_raw)
        result=json.loads(self.store.one('SELECT result FROM recovery_requests WHERE id=?',(request['id'],))['result'])
        audit=result['collector_continuity'];link=audit['handoff']
        self.assertEqual(link['from_controller'],self.previous);self.assertEqual(link['to_controller'],self.store.controller)
        self.assertEqual(link['original_collector'],self.original_collector)
        self.assertEqual(link['actual_exit'],self.original_raw['exit']);self.assertEqual(link['actual_collected_at'],self.original_raw['collected'])
        self.assertEqual(link['prior_handoff'],self.before['collection_handoff'])
        before=audit['before_witness'];after=audit['after_witness']
        self.assertEqual(before,result['retained_diagnosis']);self.assertNotEqual(before['closure_hash'],after['closure_hash'])
        self.assertEqual({k:v for k,v in before.items() if k!='closure_hash'},{k:v for k,v in after.items() if k!='closure_hash'})
        self.assertEqual(json.loads(state['collection_handoff']),link)
        self.assertIsNone(self.store.attempt(new)['begin'])
        self.assertEqual(len(self.store.rows('SELECT * FROM jobs')),1)
        self.assertEqual(len(self.store.rows("SELECT * FROM attempts WHERE kind='task'")),2)
        self.assertEqual(len(self.store.rows("SELECT * FROM attempts WHERE kind='diagnosis'")),2)
        self.runtime.execute.assert_awaited_once_with(self.job['id'],new);self.runtime.recover.assert_not_awaited()
        other=Store(self.config);self.addCleanup(other.close)
        other_runtime=Dispatcher(other,models=object(),boards={});other_runtime.execute=AsyncMock()
        other_runtime.reconcile_recovery_requests();self.runtime.reconcile_recovery_requests()
        other_runtime.execute.assert_not_called();self.runtime.execute.assert_awaited_once()
        self.assertEqual(len(self.store.rows("SELECT * FROM attempts WHERE kind='task'")),2)

    async def test_restart_does_not_silently_adopt_or_retry_owner_selected_old_work(self):
        await self.restart();await self.settle_dispatch()
        self.assertEqual(self.store.job(self.job['id']),self.before)
        self.runtime.execute.assert_not_called();self.runtime.recover.assert_not_called()
        request=self.reaffirm()  # Existing use without new explicit continuity remains foreign-refused.
        await self.settle_dispatch()
        self.assertEqual(self.store.job(self.job['id']),self.before)
        self.assertEqual(self.store.one('SELECT state FROM recovery_requests WHERE id=?',(request['id'],))['state'],'pending')

    async def test_owner_cli_store_cannot_perform_the_dispatcher_transition(self):
        await self.restart();request=self.reaffirm(collector_continuity=self.continuity())
        with self.assertRaisesRegex(Refusal,'original collector'):self.store.consume_recovery_request(request['id'])
        self.assertEqual(self.store.job(self.job['id']),self.before)

    async def test_actual_service_source_authority_refusal_prevents_custody_or_allocation(self):
        await self.restart();request=self.reaffirm(collector_continuity=self.continuity())
        def refuse(store):
            self.assertIs(store,self.store)
            raise Refusal('Owned fixture current source grant revoked')
        self.runtime.boards={'Work':SimpleNamespace(verify_authority=refuse)}
        await self.settle_dispatch()
        self.assertEqual(self.store.job(self.job['id']),self.before)
        self.assertEqual(self.store.one('SELECT state FROM recovery_requests WHERE id=?',(request['id'],))['state'],'pending')
        self.runtime.execute.assert_not_called();self.runtime.recover.assert_not_called()

    async def test_invalid_restart_scope_actor_controller_END_or_collection_is_refused(self):
        await self.restart()
        for change in [{'scope':'process-adoption'},{'from_controller':ident()},{'service_actor':ident()},
                       {'service_end':None},{'service_end':True},{'service_collected':False},{'evidence':[]}]:
            with self.subTest(change=change):
                with self.assertRaises(Refusal):self.reaffirm(collector_continuity=self.continuity(**change))
        with self.assertRaisesRegex(Refusal,'actual enrolled role owner'):
            self.store.request_recovery(self.job['id'],self.job['token'],self.original,ident(),
                                        self.receipt(collector_continuity=self.continuity()))
        self.assertEqual(self.store.job(self.job['id']),self.before)

    async def test_unknown_related_process_and_source_hold_block_transfer(self):
        await self.restart();request=self.reaffirm(collector_continuity=self.continuity())
        source=json.loads(self.before['members'])[0]['event']
        self.store.set_hold(source,'New actual source hold')
        await self.settle_dispatch();self.assertEqual(self.store.job(self.job['id']),self.before)
        self.store.set_hold(source,None)
        # Authored retained unknown sibling: never a native call or actual collection.
        self.store._attempt('diagnosis',None,self.job['id'],LUNA,self.config['diagnosis']['profile'])
        await self.settle_dispatch();self.assertEqual(self.store.job(self.job['id']),self.before)
        self.assertEqual(self.store.one('SELECT state FROM recovery_requests WHERE id=?',(request['id'],))['state'],'pending')
        self.runtime.execute.assert_not_called()

    async def test_allocation_refusal_rolls_back_closure_and_retry_has_one_successor(self):
        await self.restart();request=self.reaffirm(collector_continuity=self.continuity())
        with patch.object(self.store,'_attempt',side_effect=Refusal('Owned fixture allocation budget refusal')):
            await self.settle_dispatch()
        self.assertEqual(self.store.job(self.job['id']),self.before)
        self.assertEqual(self.store.one('SELECT state FROM recovery_requests WHERE id=?',(request['id'],))['state'],'pending')
        self.runtime.execute.assert_not_called()
        await self.settle_dispatch();self.runtime.execute.assert_awaited_once();self.runtime.recover.assert_not_called()

    async def test_old_collector_identity_cannot_stand_in_for_restart(self):
        self.previous=self.store.controller
        before=self.store.job(self.job['id']);request=self.reaffirm(collector_continuity=self.continuity())
        self.runtime.execute=AsyncMock();self.runtime.recover=AsyncMock()
        await self.settle_dispatch()
        self.assertEqual(self.store.job(self.job['id']),before)
        self.assertEqual(self.store.one('SELECT state FROM recovery_requests WHERE id=?',(request['id'],))['state'],'pending')
        self.runtime.execute.assert_not_called();self.runtime.recover.assert_not_called()

    async def test_changed_closure_or_reservation_preimage_does_not_transfer(self):
        await self.restart();request=self.reaffirm(collector_continuity=self.continuity())
        for field,value in [('collection_handoff',encode({**json.loads(self.before['collection_handoff']),'newer':'Changed closure evidence'})),
                            ('token',ident())]:
            self.store.db.execute(f'UPDATE jobs SET {field}=? WHERE id=?',(value,self.job['id']))  # Owned adverse fixture only.
            expected=self.store.job(self.job['id']);await self.settle_dispatch()
            self.assertEqual(self.store.job(self.job['id']),expected)
            self.store.db.execute(f'UPDATE jobs SET {field}=? WHERE id=?',(self.before[field],self.job['id']))
        self.assertEqual(self.store.one('SELECT state FROM recovery_requests WHERE id=?',(request['id'],))['state'],'pending')
        self.runtime.execute.assert_not_called()
