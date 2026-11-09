"""Decision1114 actual AppServer originals; synthetic sessions, no provider.

Production unsubscribe/teardown and real SQLite faults are exercised. Numeric
waits are recorded before cleanup, which is an independent last-resort duty.
"""
import asyncio
import json
import os
from pathlib import Path
import sqlite3
import unittest
from unittest.mock import AsyncMock, patch

from coordinator_runtime import appserver
from coordinator_runtime.contracts import Refusal
from support import result
from test_oneoff1077 import Recovery


class Collection1114(unittest.IsolatedAsyncioTestCase):
    setUp = Recovery.setUp
    reservation = Recovery.reservation
    prepare = Recovery.prepare

    async def original(self, fault):
        _, _, attempt = self.reservation()
        self.prepare(attempt)
        self.config['deadlines']['shutdown'] = .1
        adapter = appserver.AppServer(self.config, fixture_command=[
            '/usr/bin/python3.12', '-B', '-c',
            'import sys; sys.stdin.buffer.read(); raise SystemExit(0)'])
        child = None
        waits = []
        spawned = asyncio.create_subprocess_exec
        end_owned = appserver.end_owned
        begin = self.store.begin

        async def create(*args, **kwargs):
            nonlocal child
            child = await spawned(*args, **kwargs)
            return child

        async def observed_wait(original, grace):
            self.assertIs(original, child)
            code = await end_owned(original, grace)
            self.assertIsInstance(code, int)
            waits.append(code)
            return code

        def fail_read(action, table, column, database, trigger):
            return sqlite3.SQLITE_DENY if action == sqlite3.SQLITE_READ and table == 'attempts' else sqlite3.SQLITE_OK

        def begin_fault(*args):
            self.store.db.set_authorizer(fail_read)
            raise sqlite3.OperationalError('fictional postspawn begin journal unavailable')

        async def session(peer, store, owned, *args):
            if fault == 'read':
                # Real session fact exists before a real SQLite read refusal.
                store.session(owned, '11111111-1111-4111-8111-111111111114')
                store.db.set_authorizer(fail_read)
            return result()

        try:
            with patch('coordinator_runtime.appserver.asyncio.create_subprocess_exec', side_effect=create), \
                 patch('coordinator_runtime.appserver.environment', return_value={'PATH':'/usr/bin:/bin'}), \
                 patch('coordinator_runtime.appserver.storage.prepare', return_value=None), \
                 patch('coordinator_runtime.appserver.end_owned', side_effect=observed_wait), \
                 patch.object(adapter, 'session', side_effect=session):
                if fault == 'begin':
                    self.store.begin = begin_fault
                if fault == 'checkpoint':
                    with patch('coordinator_runtime.oneoff.checkpoint', side_effect=OSError('fictional capsule unavailable')):
                        outcome = await adapter.run(self.store, attempt, 'synthetic', {'cwd':str(self.area)}, {})
                elif fault == 'evidence':
                    # Keep production numeric wait; only its subsequent evidence
                    # validator fails. Unsubscribe is never replaced.
                    with patch.object(appserver.Peer, 'validate_turn_correlation', side_effect=OSError('fictional capture evidence unavailable')):
                        outcome = await adapter.run(self.store, attempt, 'synthetic', {'cwd':str(self.area)}, {})
                elif fault == 'debt':
                    with patch('coordinator_runtime.appserver.end_owned', side_effect=OSError('fictional wait API unavailable')):
                        outcome = await adapter.run(self.store, attempt, 'synthetic', {'cwd':str(self.area)}, {})
                    self.assertIsNone(outcome['exit'])
                    self.assertIs(adapter.pending_collections[attempt][0], child)
                    self.assertIn('collection_debt', outcome['detail'])
                    await adapter.collect_pending()
                else:
                    outcome = await adapter.run(self.store, attempt, 'synthetic', {'cwd':str(self.area)}, {})
            self.assertIsNotNone(child)
            self.assertTrue(waits, 'production collector must wait before cleanup')
            self.assertEqual(outcome['exit'], waits[-1])
            self.assertEqual(adapter.pending_collections, {})
            if fault == 'read':
                self.assertEqual(outcome['detail']['unsubscribe_failure'], 'DatabaseError')
                self.assertEqual(outcome['detail']['unsubscribe'], 'failed-or-unknown')
            if fault in {'read', 'begin', 'checkpoint'}:
                self.assertEqual(outcome['detail']['recovery_checkpoint'], 'unqualified-held')
            if fault == 'evidence':
                self.assertEqual(outcome['detail']['teardown_failure'], 'OSError')
                self.assertEqual(outcome['cleanup'], 'owned-teardown-needs-reconciliation')
            self.assertEqual(outcome['detail']['session_residuals']['state'], 'unqualified-held')
            (self.area/'ORIGINAL-COLLECTION1114.json').write_text(json.dumps({
                'fault':fault, 'numeric_waits_before_cleanup':waits, 'outcome':outcome,
                'same_original':True, 'actual_acceptance':False, 'processing_completion':False}))
            print('ORIGINAL1114 '+json.dumps({'fault':fault,'END':waits[-1],'before_cleanup':True}))
        finally:
            self.store.begin = begin
            self.store.db.set_authorizer(None)
            # Separate last-resort collection, never credited to production.
            if child is not None and child.returncode is None:
                code = await end_owned(child, .1)
                print('CLEANUP-ONLY1114 '+json.dumps({'END':code,'production_credit':False}))

    async def test_production_unsubscribe_SQLite_read_failure_collects_same_original(self):
        await self.original('read')

    async def test_postspawn_begin_and_unavailable_journal_collect_before_peer(self):
        await self.original('begin')

    async def test_checkpoint_failure_keeps_production_unsubscribe_and_collection(self):
        await self.original('checkpoint')

    async def test_postwait_evidence_failure_preserves_numeric_collection(self):
        await self.original('evidence')

    async def test_wait_API_failure_retains_capable_debt_and_collects_same_handle(self):
        await self.original('debt')

    async def test_caller_cancellation_during_production_unsubscribe_is_joined(self):
        _, _, attempt = self.reservation()
        self.prepare(attempt)
        self.config['deadlines']['shutdown'] = .1
        adapter = appserver.AppServer(self.config, fixture_command=[
            '/usr/bin/python3.12','-B','-c','import sys; sys.stdin.buffer.read()'])
        boundary, release = asyncio.Event(), asyncio.Event()
        original_rpc = appserver.Peer.rpc
        original_end = appserver.end_owned
        waits = []
        async def rpc(peer, method, params):
            if method == 'thread/unsubscribe':
                boundary.set()
                await release.wait()
                return {'status':'unsubscribed'}
            return await original_rpc(peer, method, params)
        async def session(peer, store, owned, *args):
            store.session(owned, '11111111-1111-4111-8111-111111111114')
            return result()
        async def end(child, grace):
            code = await original_end(child, grace)
            waits.append(code)
            return code
        with patch('coordinator_runtime.appserver.environment',return_value={'PATH':'/usr/bin:/bin'}), \
             patch('coordinator_runtime.appserver.storage.prepare',return_value=None), \
             patch.object(appserver.Peer,'rpc',rpc), patch.object(adapter,'session',side_effect=session), \
             patch('coordinator_runtime.appserver.end_owned',side_effect=end):
            running = asyncio.create_task(adapter.run(self.store, attempt, 'synthetic', {'cwd':str(self.area)}, {}))
            try:
                await asyncio.wait_for(boundary.wait(), 3)
                running.cancel()
                await asyncio.sleep(0)
                release.set()
                with self.assertRaises(asyncio.CancelledError) as caught:
                    await running
                outcome = caught.exception.collection_outcome
                self.assertTrue(waits)
                self.assertEqual(outcome['exit'], waits[-1])
                self.assertEqual(outcome['detail']['unsubscribe'], 'unsubscribed')
                self.assertEqual(adapter.pending_collections, {})
                (self.area/'ORIGINAL-COLLECTION1114.json').write_text(json.dumps({
                    'fault':'caller-cancellation','numeric_waits_before_cleanup':waits,'outcome':outcome}))
                print('ORIGINAL1114 '+json.dumps({'fault':'caller-cancellation','END':waits[-1],'before_cleanup':True}))
            finally:
                release.set()
                await asyncio.gather(running, return_exceptions=True)
                await adapter.collect_pending()


    async def test_concurrent_admitted_originals_do_not_collect_each_other(self):
        _, _, first = self.reservation()
        self.prepare(first)
        _, _, second = self.reservation('Branch')
        self.prepare(second)
        self.config['deadlines']['shutdown'] = .1
        adapter = appserver.AppServer(self.config, fixture_command=[
            '/usr/bin/python3.12','-B','-c','import sys; sys.stdin.buffer.read()'])
        first_ready, second_ready, release = asyncio.Event(), asyncio.Event(), asyncio.Event()
        original_end = appserver.end_owned
        waits = []
        async def session(peer, store, owned, *args):
            if owned == first:
                first_ready.set()
            else:
                self.assertIsNone(adapter.owned_collections[first][0].returncode)
                self.assertEqual(adapter.pending_collections, {})
                second_ready.set()
            await release.wait()
            return result()
        async def end(child, grace):
            code = await original_end(child, grace)
            waits.append(code)
            return code
        with patch('coordinator_runtime.appserver.environment',return_value={'PATH':'/usr/bin:/bin'}), \
             patch('coordinator_runtime.appserver.storage.prepare',return_value=None), \
             patch.object(adapter,'session',side_effect=session), \
             patch('coordinator_runtime.appserver.end_owned',side_effect=end):
            a = asyncio.create_task(adapter.run(self.store, first, 'synthetic', {'cwd':str(self.area)}, {}))
            b = None
            try:
                await asyncio.wait_for(first_ready.wait(), 3)
                b = asyncio.create_task(adapter.run(self.store, second, 'synthetic', {'cwd':str(self.area)}, {}))
                await asyncio.wait_for(second_ready.wait(), 3)
                release.set()
                outcomes = await asyncio.gather(a,b)
                self.assertEqual(len(waits), 2)
                self.assertTrue(all(type(x['exit']) is int for x in outcomes))
                self.assertEqual(adapter.pending_collections, {})
                self.assertEqual(adapter.owned_collections, {})
                (self.area/'ORIGINAL-COLLECTION1114.json').write_text(json.dumps({
                    'fault':'concurrent-owned','numeric_waits_before_cleanup':waits,'outcomes':outcomes}))
                print('ORIGINAL1114 '+json.dumps({'fault':'concurrent-owned','ENDs':waits,'before_cleanup':True}))
            finally:
                release.set()
                await asyncio.gather(*[x for x in (a,b) if x is not None], return_exceptions=True)
                await adapter.collect_pending()

    def evidence1118(self, name, **facts):
        (self.area/('ORIGINAL1118-'+name+'.json')).write_text(json.dumps(facts, sort_keys=True, indent=2))
        print('ORIGINAL1118 '+json.dumps(dict(control=name, **facts), sort_keys=True))

    def adapter1118(self):
        self.config['deadlines']['shutdown'] = .1
        return appserver.AppServer(self.config, fixture_command=[
            '/usr/bin/python3.12', '-B', '-c', 'import sys; sys.stdin.buffer.read()'])

    async def debt1118(self, adapter):
        _, job, attempt = self.reservation()
        self.runtime.models = adapter
        with patch('coordinator_runtime.appserver.environment', return_value={'PATH':'/usr/bin:/bin'}), \
             patch('coordinator_runtime.appserver.storage.prepare', return_value=None), \
             patch.object(adapter, 'session', return_value=result()), \
             patch('coordinator_runtime.appserver.end_owned', side_effect=OSError('fictional wait API refusal')):
            outcome = await self.runtime.run_model(attempt, 'owned debt', {'cwd':str(self.area)}, {})
        self.assertIsNone(outcome['exit'])
        self.store.collect(attempt, outcome)
        return job, attempt, outcome

    async def test_existing_debt_concurrent_dispatcher_calls_have_normal_results_and_later_END(self):
        from coordinator_runtime import oneoff
        adapter = self.adapter1118()
        job, old, unknown = await self.debt1118(adapter)
        original_result = self.store.one('SELECT * FROM results WHERE attempt=?', (old,))
        original_capsule = self.store.one('SELECT original FROM oneoff_collection_recovery WHERE attempt=?', (old,))
        original_snapshot = oneoff.snapshot(self.store, old)['original_collection']
        _, _, a = self.reservation('Branch')
        _, _, b = self.reservation('Reviews')
        entered, release = asyncio.Event(), asyncio.Event()
        real_end = appserver.end_owned
        old_child = adapter.pending_collections[old][0]
        waits = []
        async def end(child, grace):
            if child is old_child:
                entered.set()
                await release.wait()
            code = await real_end(child, grace)
            waits.append({'same_old':child is old_child,'exit':code})
            return code
        async def call(attempt):
            outcome = await self.runtime.run_model(attempt, 'new reservation', {'cwd':str(self.area)}, {})
            self.store.collect(attempt, outcome)
            return outcome
        with patch('coordinator_runtime.appserver.environment',return_value={'PATH':'/usr/bin:/bin'}), \
             patch('coordinator_runtime.appserver.storage.prepare',return_value=None), \
             patch.object(adapter,'session',return_value=result()), \
             patch('coordinator_runtime.appserver.end_owned',side_effect=end):
            first = asyncio.create_task(call(a))
            try:
                await asyncio.wait_for(entered.wait(), 3)
                second = asyncio.create_task(call(b))
                await asyncio.sleep(0)
                release.set()
                outcomes = await asyncio.gather(first, second)
            finally:
                release.set()
                await first
        self.assertTrue(all(type(x['exit']) is int for x in outcomes))
        self.assertEqual({r['attempt'] for r in self.store.rows('SELECT attempt FROM results WHERE attempt IN (?,?,?)',(old,a,b))}, {old,a,b})
        self.assertEqual(self.store.one('SELECT * FROM results WHERE attempt=?',(old,)), original_result)
        self.assertEqual(self.store.one('SELECT original FROM oneoff_collection_recovery WHERE attempt=?',(old,)),original_capsule)
        view = oneoff.snapshot(self.store,old)
        self.assertEqual(view['original_collection'], original_snapshot)
        self.assertIsNone(view['original_collection']['exit'])
        self.assertEqual(self.store.attempt(old)['exit'], 0)
        self.assertTrue(self.store.rows('SELECT * FROM oneoff_progress_recovery WHERE attempt=?',(old,)))
        self.assertTrue(all(r['processed_at'] is None for r in self.store.rows('SELECT processed_at FROM events')))
        self.assertEqual(self.store.job(job['id'])['effects'],'unknown')
        self.assertEqual(adapter.pending_collections,{})
        self.assertEqual(sum(x['same_old'] for x in waits),1)
        self.evidence1118('concurrent-late', original=old, waits_before_cleanup=waits,
            immutable_UNKNOWN=original_snapshot, current=self.store.attempt(old), new_outcomes=outcomes,
            actual_acceptance=False,processing_completion=False)

    async def test_unresolved_old_debt_preserves_two_new_reserved_attempt_outcomes(self):
        adapter = self.adapter1118()
        _, old, _ = await self.debt1118(adapter)
        attempts = [self.reservation(role)[2] for role in ('Branch','Reviews')]
        try:
            with patch('coordinator_runtime.appserver.end_owned',side_effect=OSError('still unavailable')):
                outcomes = await asyncio.gather(*[self.runtime.run_model(a,'new',{'cwd':str(self.area)}, {}) for a in attempts])
            for a, outcome in zip(attempts,outcomes):
                self.assertTrue(outcome['detail']['known_not_started'])
                self.store.collect(a,outcome)
                self.assertEqual(self.store.attempt(a)['state'],'not-started')
            self.assertIn(old,adapter.pending_collections)
            self.assertEqual({r['attempt'] for r in self.store.rows('SELECT attempt FROM results WHERE attempt IN (?,?,?)',(old,*attempts))}, {old,*attempts})
        finally:
            await adapter.collect_pending()
        self.evidence1118('unresolved-debt', new_outcomes=outcomes, old_numeric_END=self.store.attempt(old)['exit'])

    async def test_numeric_later_delivery_failure_keeps_owner_and_retries_without_rewaiting(self):
        adapter = self.adapter1118()
        _, old, _ = await self.debt1118(adapter)
        child = adapter.pending_collections[old][0]
        real_end = appserver.end_owned
        waits=[]
        async def end(owned, grace):
            self.assertIs(owned,child)
            code=await real_end(owned,grace);waits.append(code);return code
        with patch('coordinator_runtime.appserver.end_owned',side_effect=end):
            with patch.object(self.store,'record_original_end',side_effect=OSError('fictional journal delivery unavailable')):
                with self.assertRaises(Refusal):await adapter.collect_pending()
            self.assertIs(adapter.pending_collections[old][0],child)
            self.assertIsNone(self.store.attempt(old)['exit'])
            await adapter.collect_pending()
        self.assertEqual(waits,[0])
        self.assertEqual(self.store.attempt(old)['exit'],0)
        self.evidence1118('delivery-retry',same_original=old,numeric_waits_before_cleanup=waits,current=self.store.attempt(old))

    async def test_nonfixture_preflight_and_model_have_separate_attributed_originals(self):
        _,_,attempt=self.reservation()
        self.prepare(attempt)
        adapter=appserver.AppServer(self.config)
        self.config['protocol_cli_version']='fictional cli'
        self.config['deadlines']['shutdown']=.1
        create=asyncio.create_subprocess_exec
        launched=[]
        async def spawn(*argv,**kwargs):
            if '--version' in argv: body='fictional cli\n'
            elif 'mcp' in argv:
                body=json.dumps([{'name':'openaiDeveloperDocs','enabled':False}] if any('openaiDeveloperDocs.url' in x for x in argv) else [])
            elif 'features' in argv: body='multi_agent experimental false\n'
            else:
                child=await create('/usr/bin/python3.12','-B','-c','import sys; sys.stdin.buffer.read()',**kwargs)
                launched.append((child,'model'));return child
            child=await create('/usr/bin/python3.12','-B','-c','import sys; sys.stdout.write('+repr(body)+')',**kwargs)
            launched.append((child,'metadata'));return child
        with patch('coordinator_runtime.appserver.asyncio.create_subprocess_exec',side_effect=spawn), \
             patch('coordinator_runtime.appserver.environment',return_value={'PATH':'/usr/bin:/bin'}), \
             patch('coordinator_runtime.appserver.storage.prepare',return_value=None), \
             patch.object(adapter,'session',return_value=result()):
            outcome=await adapter.run(self.store,attempt,'nonfixture command',{'cwd':str(self.area)}, {})
        self.store.collect(attempt,outcome)
        self.assertEqual(outcome['exit'],0)
        observations=json.loads(self.store.attempt(attempt)['detail'])['original_end_observations']
        self.assertEqual(len(observations),len(launched)-1)
        self.assertTrue(all(x['kind']=='preflight-metadata' and x['exit']==0 for x in observations))
        self.assertEqual(adapter.metadata_originals.owned,{})
        self.evidence1118('nonfixture-preflight',observations=observations,model_outcome=outcome,
                          launched_kinds=[kind for _,kind in launched],provider_invoked=False)

    async def test_metadata_wait_failure_carries_exact_owner_then_delivers_later_END(self):
        _,_,attempt=self.reservation();self.prepare(attempt)
        owner=appserver.Originals()
        create=asyncio.create_subprocess_exec;child=None
        async def spawn(*args,**kw):
            nonlocal child
            child=await create(*args,**kw)
            child.wait=AsyncMock(side_effect=OSError('fictional metadata wait API unavailable'))
            return child
        actual_wait=None
        try:
            with patch('coordinator_runtime.appserver.asyncio.create_subprocess_exec',side_effect=spawn), \
                 patch('coordinator_runtime.appserver.end_owned',side_effect=OSError('fictional metadata tail unavailable')):
                with self.assertRaises(appserver.CollectionPending) as caught:
                    await appserver.metadata(['/usr/bin/python3.12','-B','-c','print("safe metadata")'],
                        {'PATH':'/usr/bin:/bin'}, originals=owner,
                        publish=lambda obs:self.store.record_original_end(attempt,obs))
            key=caught.exception.original
            self.assertIs(caught.exception.collector,owner)
            self.assertIs(owner.pending[key]['child'],child)
            # Restore the real wait method on the SAME owned subprocess.
            child.wait=type(child).wait.__get__(child,type(child))
            await owner.collect_pending(.1)
            observations=json.loads(self.store.attempt(attempt)['detail'])['original_end_observations']
            self.assertEqual(observations[0]['kind'],'preflight-metadata')
            self.assertEqual(observations[0]['exit'],0)
            self.assertIsNone(self.store.attempt(attempt)['exit'])
            self.evidence1118('metadata-debt',observations=observations,model_END=None,same_original=True)
        finally:
            if child is not None:
                child.wait=type(child).wait.__get__(child,type(child))
                await appserver.end_owned(child,.1)

    async def native1118(self, fault):
        from coordinator_runtime import reviews
        _,_,attempt=self.reservation();self.prepare(attempt)
        self.config['deadlines']['shutdown']=.1
        native=reviews.Native();create=asyncio.create_subprocess_exec;real_end=appserver.end_owned
        child=None;waits=[];capable_wait=None;directory=self.area/'native-call'
        policy={'caller':'fictional-admitted-caller','deadline':1,'routes':{'.codex':'fictional-route'}}
        context={'route':'fictional-route','profile':'.codex','handle':'fictional-root','created':self.now}
        # Use the reserved profile; no account/environment/profile access.
        profile=self.store.attempt(attempt)['profile'];context['profile']=profile;policy['routes']={profile:'fictional-route'}
        async def spawn(*argv,**kwargs):
            nonlocal child, capable_wait
            child=await create('/usr/bin/python3.12','-B','-c','pass',**kwargs)
            original_wait=child.wait
            async def observed_wait():
                code=await original_wait()
                self.assertIsInstance(code,int)
                waits.append(code)
                return code
            capable_wait=observed_wait
            child.wait=observed_wait
            if fault=='wait':child.wait=AsyncMock(side_effect=OSError('fictional native wait API unavailable'))
            return child
        async def end(original,grace):
            self.assertIs(original,child)
            return await real_end(original,grace)
        begin=self.store.begin
        try:
            with patch('coordinator_runtime.reviews.caller_current'), \
                 patch('coordinator_runtime.reviews.handle_run',return_value='fictional-run'), \
                 patch('coordinator_runtime.appserver.asyncio.create_subprocess_exec',side_effect=spawn), \
                 patch('coordinator_runtime.appserver.end_owned',side_effect=end):
                if fault=='begin':
                    self.store.begin=lambda *args: (_ for _ in ()).throw(sqlite3.OperationalError('fictional postspawn begin refusal'))
                    with self.assertRaises(sqlite3.OperationalError):
                        await native.call(self.store,attempt,policy,context,directory,'synthetic',[],opening=True)
                elif fault=='wait':
                    with self.assertRaises(appserver.CollectionPending) as caught:
                        await native.call(self.store,attempt,policy,context,directory,'synthetic',[],opening=True)
                    key=caught.exception.original
                    self.assertIs(native.originals.pending[key]['child'],child)
                    child.wait=capable_wait
                    await native.collect_pending(self.store)
                elif fault=='receipt':
                    opened=Path.open
                    def refuse(path,*args,**kwargs):
                        if path.name=='original.json':raise OSError('fictional original receipt unavailable')
                        return opened(path,*args,**kwargs)
                    with patch.object(Path,'open',refuse):
                        with self.assertRaises(appserver.CollectionPending):
                            await native.call(self.store,attempt,policy,context,directory,'synthetic',[],opening=True)
                    self.assertEqual(len(native.originals.pending),1)
                    await native.collect_pending(self.store)
                else:
                    code,receipt,answer=await native.call(self.store,attempt,policy,context,directory,'synthetic',[],opening=True)
                    self.assertEqual(code,0)
                    self.assertEqual(receipt['class'],'incomplete')
            record=json.loads((directory/'original.json').read_text())
            if fault=='wait':
                self.assertIsNone(record['actual_END'],'earlier UNKNOWN receipt remains immutable')
                later=[json.loads(line) for line in (directory/'original-observations.jsonl').read_text().splitlines()]
                self.assertEqual(later[-1]['actual_END'],0)
                self.assertEqual(later[-1]['original'],record['original'])
            else:self.assertEqual(record['actual_END'],0)
            self.assertTrue(waits,'production exact wait before cleanup')
            self.assertEqual(native.originals.owned,{})
            observations=json.loads(self.store.attempt(attempt)['detail'])['original_end_observations']
            self.assertEqual(observations[-1]['kind'],'native-caller')
            self.assertIsNone(self.store.attempt(attempt)['exit'],'native caller does not mint provider/model END')
            self.evidence1118('native-'+fault,original=record,numeric_waits_before_cleanup=waits,
                              observations=observations,provider_root_completion='UNKNOWN')
        finally:
            self.store.begin=begin
            if child is not None:
                child.wait=capable_wait
                if child.returncode is None:await real_end(child,.1)

    async def test_native_caller_postspawn_begin_failure_collects_before_escape(self):
        await self.native1118('begin')

    async def test_native_caller_wait_failure_retains_same_original_and_retries(self):
        await self.native1118('wait')

    async def test_native_caller_receipt_failure_retains_collected_original_for_evidence_retry(self):
        await self.native1118('receipt')

    async def test_native_caller_normal_numeric_END_does_not_imply_provider_root_END(self):
        await self.native1118('normal')

    async def cancelled_original1118(self, native_call):
        from coordinator_runtime import reviews
        _,_,attempt=self.reservation();self.prepare(attempt)
        self.config['deadlines']['shutdown']=.1
        create=asyncio.create_subprocess_exec;actual_end=appserver.end_owned
        child=None;spawned=asyncio.Event();in_tail=asyncio.Event();release=asyncio.Event();waits=[]
        async def spawn(*argv,**kwargs):
            nonlocal child
            child=await create('/usr/bin/python3.12','-B','-c','import time; time.sleep(60)',**kwargs)
            spawned.set();return child
        async def end(original,grace):
            self.assertIs(original,child);in_tail.set();await release.wait()
            code=await actual_end(original,.1);waits.append(code);return code
        native=reviews.Native()
        owner=appserver.Originals()
        profile=self.store.attempt(attempt)['profile']
        policy={'caller':'fictional-admitted-caller','deadline':1,'routes':{profile:'fictional-route'}}
        context={'route':'fictional-route','profile':profile,'handle':'fictional-root','created':self.now}
        observations=[]
        with patch('coordinator_runtime.appserver.asyncio.create_subprocess_exec',side_effect=spawn), \
             patch('coordinator_runtime.appserver.end_owned',side_effect=end), \
             patch('coordinator_runtime.reviews.caller_current'):
            call=(native.call(self.store,attempt,policy,context,self.area/'cancelled-native','synthetic',[],opening=True)
                  if native_call else appserver.metadata(['/usr/bin/python3.12','-B','-c','pass'],
                      {'PATH':'/usr/bin:/bin'},originals=owner,publish=observations.append))
            running=asyncio.create_task(call)
            try:
                await asyncio.wait_for(spawned.wait(),3)
                running.cancel()
                await asyncio.wait_for(in_tail.wait(),3)
                running.cancel()  # Cancellation during the original finalizer.
                await asyncio.sleep(0)
                release.set()
                with self.assertRaises(asyncio.CancelledError):await running
                self.assertTrue(waits)
                self.assertEqual((native.originals if native_call else owner).owned,{})
                if native_call:
                    record=json.loads((self.area/'cancelled-native/original.json').read_text())
                    self.assertEqual(record['actual_END'],waits[-1])
                else:
                    self.assertEqual(observations[-1]['exit'],waits[-1])
                self.evidence1118('cancelled-native' if native_call else 'cancelled-metadata',
                    numeric_waits_before_cleanup=waits,joined_through_repeated_cancellation=True)
            finally:
                release.set();await asyncio.gather(running,return_exceptions=True)
                if child is not None and child.returncode is None:await actual_end(child,.1)

    async def test_metadata_finalizer_joins_repeated_caller_cancellation(self):
        await self.cancelled_original1118(False)

    async def test_native_finalizer_joins_repeated_caller_cancellation(self):
        await self.cancelled_original1118(True)

    async def test_metadata_drain_failure_keeps_numeric_original_and_evidence_retry(self):
        owner=appserver.Originals();create=asyncio.create_subprocess_exec;child=None;read=None;calls=0;observations=[]
        async def spawn(*args,**kw):
            nonlocal child,read
            child=await create(*args,**kw);read=child.stdout.read
            async def faulty(*args):
                nonlocal calls
                calls+=1
                if calls>2:raise OSError('fictional metadata tail evidence unavailable')
                return await read(*args)
            child.stdout.read=faulty
            return child
        with patch('coordinator_runtime.appserver.asyncio.create_subprocess_exec',side_effect=spawn):
            with self.assertRaises(appserver.CollectionPending) as caught:
                await appserver.metadata(['/usr/bin/python3.12','-B','-c','print("safe metadata")'],
                    {'PATH':'/usr/bin:/bin'},originals=owner,publish=observations.append)
        key=caught.exception.original
        self.assertEqual(owner.owned[key]['exit'],0)
        self.assertIs(owner.owned[key]['child'],child)
        child.stdout.read=read
        await owner.collect_pending(.1)
        self.assertFalse(observations[0]['evidence_complete'])
        self.assertTrue(observations[-1]['evidence_complete'])
        self.assertEqual(owner.owned,{})
        self.evidence1118('metadata-evidence',observations=observations,same_original=True)
