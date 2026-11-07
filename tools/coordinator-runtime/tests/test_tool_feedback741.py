"""Real AppServer/Peer/readiness caller paths over an explicit fictional provider.

All store, board, command and turn identities are fresh private fixture data.
No model provider or command in a notification is executed.
"""
import hashlib
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import test_handback618 as boundary
import test_writer_custody as fixtures
from coordinator_runtime import readiness
from coordinator_runtime.appserver import AppServer
from coordinator_runtime.contracts import Refusal, collected_task_result, task_result
from support import event, ident, queued


class CurrentInputs(unittest.IsolatedAsyncioTestCase):
    asyncSetUp = boundary.AuthoritativePeer.asyncSetUp
    asyncTearDown = boundary.AuthoritativePeer.asyncTearDown

    def command(self, identity, command, code=0, thread=boundary.THREAD, turn=boundary.TURN, method='item/completed'):
        item = {'type':'commandExecution','id':identity,'status':'failed' if code else 'completed','exitCode':code,
                'aggregatedOutput':'FORBIDDEN_STDOUT_741'}
        if command is not None:item['command']=command
        self.peer.notification({'method':method,'params':{'threadId':thread,'turnId':turn,'item':item}})

    def inputs(self):
        return json.JSONDecoder().raw_decode(AppServer.tool_feedback(self.peer).split('OBSERVED_COMMAND_INPUTS=',1)[1])[0]

    async def test_exact_utf8_wrapper_is_linked_to_protocol_outcome_without_stdout_in_metadata(self):
        command = "/bin/bash -lc 'printf λ\n'"
        self.command('opaque',command,2)
        row = self.inputs()[0]
        self.assertEqual(row['command'],command)
        self.assertEqual(row['command_sha256'],hashlib.sha256(command.encode()).hexdigest())
        self.assertEqual(row['command_bytes'],len(command.encode()))
        self.assertEqual(row['exit_code'],2)
        self.assertEqual(row['status'],'failed')
        self.assertNotIn('command',self.peer.tools['opaque'])
        self.assertNotIn('FORBIDDEN_STDOUT_741',AppServer.tool_feedback(self.peer))

    async def test_missing_oversize_and_cumulative_extents_remain_unavailable_without_prefix(self):
        self.peer.limit = 8
        self.command('first','123456')
        self.command('over','abcdefghi')
        self.command('cumulative','xyz')
        self.command('missing',None)
        rows = {r['id']:r for r in self.inputs()}
        self.assertEqual(rows['first']['command'],'123456')
        for identity in ['over','cumulative','missing']:
            self.assertEqual(rows[identity]['availability'],'unavailable')
            self.assertNotIn('command',rows[identity])
        self.assertEqual(rows['over']['command_bytes'],9)
        self.assertEqual(self.peer.command_input_bytes,6)

    async def test_started_input_cannot_substitute_for_missing_completion_input(self):
        self.command('same','started-only',method='item/started')
        self.command('same',None)
        self.assertEqual(self.inputs()[0]['reason'],'completion-command-absent')

    async def test_foreign_or_unclosed_inventory_never_returns_command_bodies(self):
        self.command('own','own')
        self.command('foreign','foreign',turn='foreign')
        self.assertEqual(self.inputs(),[])
        self.assertNotIn('foreign',self.peer.command_inputs)

    async def test_closed_peer_cannot_return_old_input_bodies(self):
        self.command('own','current-owned-input')
        self.peer.child.returncode = 0
        self.assertEqual(self.inputs(),[])


class CallerPaths(unittest.IsolatedAsyncioTestCase):
    asyncSetUp = fixtures.WriterCustody.asyncSetUp

    async def run_case(self, **options):
        queued(self.store,event(self.config,ident()))
        job = self.store.reserve()
        attempt = self.store.start_job(job['id'],job['token'])
        base = Path(self.temp.name)
        plan = {'target':str(self.target),'report':str(self.store.home/'artifacts'/attempt/'verification.json'),
                'record':str(base/'turns.jsonl'),'writes':str(base/'writes.txt'),**options}
        path = base/'plan.json'
        path.write_text(json.dumps(plan))
        self.runtime.models = AppServer(self.config,[sys.executable,str(Path(__file__).with_name('fixture_tool_feedback741.py')),str(path)])
        await self.runtime.execute(job['id'],attempt)
        self.row = self.store.attempt(attempt)
        self.detail = json.loads(self.row['detail'])
        self.answer = json.loads(self.row['result'])
        self.records = [json.loads(line) for line in Path(plan['record']).read_text().splitlines()]
        self.assertEqual(self.row['exit'],0)
        self.assertIsNotNone(self.row['ended'])
        self.assertIsNotNone(self.row['collected'])
        self.assertTrue(self.detail['tool_completion']['complete'])
        self.assertEqual(self.detail['teardown'],'actual-owned-process-exit-collected')
        self.assertEqual(len(Path(plan['writes']).read_text().splitlines()),1)
        self.assertNotIn('FORBIDDEN_STDOUT_741',json.dumps(self.detail))
        self.assertNotIn('/bin/bash',json.dumps(self.detail['tool_completion']))
        self.assertNotIn('/bin/bash',json.dumps(self.detail))
        return job,attempt

    def held(self,job,turns):
        self.assertEqual(len(self.records),turns)
        self.assertEqual(json.loads(self.target.read_text()),{'total':0})
        self.assertEqual(self.store.job(job['id'])['effects'],'unknown')
        self.assertEqual(self.store.rows('SELECT * FROM file_publications'),[])

    async def test_successive_verifier_and_read_repairs_conserve_every_return_and_exact_outcome(self):
        job,attempt = await self.run_case()
        self.assertEqual(len(self.records),3)
        self.assertIsNone(self.row['error'])
        self.assertEqual(self.answer['semantic'],'DONE')
        self.assertEqual(json.loads(self.target.read_text()),{'total':12})
        self.assertEqual(self.store.job(job['id'])['effects'],'reconciled')
        self.assertEqual(len(self.detail['prior_turn_results']),1)
        prior = readiness.prior_handbacks(self.detail)
        self.assertEqual([p['semantic'] for p in prior],['PARTIAL','PARTIAL'])
        for original in prior:task_result(self.answer,original)
        items = self.detail['tool_completion']['items']
        self.assertEqual([r['exit_code'] for r in items],[2,0,2,0])
        self.assertEqual(items[0]['command_sha256'],items[1]['command_sha256'])
        self.assertEqual(len({r['turn'] for r in items}),2)
        assessment = readiness.assess(self.store,self.row)
        self.assertEqual(len(assessment['resolved_local_unknowns']),2)
        self.assertEqual(len(assessment['tool_dispositions']),2)
        self.assertEqual(collected_task_result(self.row),self.answer)
        # The middle return remains independently binding after collection.
        changed = dict(self.row)
        forged = dict(self.answer)
        forged['failures'] = forged['failures'][:1]
        changed['result'] = json.dumps(forged)
        with self.assertRaises(Refusal):collected_task_result(changed)

    async def test_external_blocker_stops_even_with_new_adverse_observation(self):
        job,_ = await self.run_case(external=True)
        self.held(job,2)
        self.assertEqual(self.answer['semantic'],'PARTIAL')

    async def test_failure_only_external_blocker_stops_after_real_prior_resolution(self):
        job,_ = await self.run_case(failure_only_external=True)
        self.held(job,2)
        self.assertEqual(self.answer['semantic'],'PARTIAL')
        self.assertEqual(self.answer['failures'][0], self.detail['prior_turn_result']['failures'][0])
        self.assertEqual(self.answer['completion']['failures'][0]['status'],'resolved')
        self.assertEqual(self.answer['completion']['failures'][-1]['status'],'unresolved')
        self.assertEqual(self.answer['failures'][-1]['kind'],'external-resource')
        self.assertEqual(self.answer['completion']['unknowns'][-1]['duty'],'observed-tool-metadata')
        self.assertEqual([r['exit_code'] for r in self.detail['tool_completion']['items']],[2,0,2,0])
        self.assertEqual(self.answer['completion']['tools'][0]['status'],'resolved')

    async def test_partial_without_new_observable_progress_stops(self):
        job,_ = await self.run_case(no_progress=True)
        self.held(job,2)
        self.assertEqual(self.answer,self.detail['prior_turn_result'])

    async def test_guessed_protocol_identity_cannot_earn_another_turn_or_readiness(self):
        job,_ = await self.run_case(guessed=True)
        self.held(job,2)
        with self.assertRaises(Refusal):readiness.assess(self.store,self.row)

    async def test_configured_budget_stops_endless_progress_and_new_errors(self):
        self.config['limits']['max_owner_corrections']=2
        job,_ = await self.run_case(endless=True)
        self.held(job,3)
        self.assertEqual(self.answer['semantic'],'PARTIAL')
        self.assertEqual(len(self.answer['failures']),1)
        self.assertEqual(len(self.answer['unknowns']),3)
        self.assertEqual(len(self.detail['tool_completion']['nonzero_completions']),3)

    async def test_revoked_authority_fences_next_turn_and_preserves_lawful_original_collection(self):
        original = AppServer.continue_idle
        async def fence(adapter,peer,store,*args,**kwargs):
            if peer.continuation_used:
                with patch.object(store,'authorize_launch',side_effect=Refusal('current source authority revoked')):
                    return await original(adapter,peer,store,*args,**kwargs)
            return await original(adapter,peer,store,*args,**kwargs)
        with patch.object(AppServer,'continue_idle',fence):job,_ = await self.run_case()
        self.held(job,2)
        self.assertIn('authority revoked',self.row['error'])
        self.assertEqual(self.answer['semantic'],'PARTIAL')
        self.assertEqual(len(self.answer['failures']),1)
        self.assertEqual(len(self.answer['unknowns']),2)

    async def test_changed_idle_state_fences_progress_turn_without_losing_partial(self):
        original = AppServer.continue_idle
        async def fence(adapter,peer,store,*args,**kwargs):
            if peer.continuation_used:
                rpc = peer.rpc
                async def busy(method,params,*a,**kw):
                    if method == 'thread/read':return {'thread':{'id':peer.thread,'status':{'type':'active'}}}
                    return await rpc(method,params,*a,**kw)
                with patch.object(peer,'rpc',busy):return await original(adapter,peer,store,*args,**kwargs)
            return await original(adapter,peer,store,*args,**kwargs)
        with patch.object(AppServer,'continue_idle',fence):job,_ = await self.run_case()
        self.held(job,2)
        self.assertIn('idle',self.row['error'])
        self.assertEqual(self.answer['semantic'],'PARTIAL')

    async def test_altered_fingerprint_cannot_earn_another_turn_or_readiness(self):
        job,_ = await self.run_case(altered=True)
        self.held(job,2)
        with self.assertRaises(Refusal):readiness.assess(self.store,self.row)

    async def test_semantic_unknown_cannot_earn_another_turn_or_readiness(self):
        job,_ = await self.run_case(terminal='UNKNOWN')
        self.held(job,2)
        with self.assertRaises(Refusal):readiness.assess(self.store,self.row)

    async def test_semantic_failed_cannot_earn_another_turn_or_readiness(self):
        job,_ = await self.run_case(terminal='FAILED')
        self.held(job,2)
        with self.assertRaises(Refusal):readiness.assess(self.store,self.row)
