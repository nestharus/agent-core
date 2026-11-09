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


    async def test_native_capture_timeout_then_later_END_is_responsive_and_partial(self):
        from coordinator_runtime import reviews, oneoff
        self.placement1127()
        _,_,attempt=self.reservation();self.prepare(attempt)
        self.config['deadlines']['shutdown']=.01
        native=reviews.Native();create=asyncio.create_subprocess_exec;child=None;wait=None
        profile=self.store.attempt(attempt)['profile']
        policy={'caller':'fictional-caller','deadline':1,'routes':{profile:'fictional-route'}}
        context={'route':'fictional-route','profile':profile,'handle':'fictional-root','created':self.now}
        directory=self.store.artifact_root(attempt)/'review-call-0'
        async def spawn(*argv,**kw):
            nonlocal child,wait
            child=await create('/usr/bin/python3.12','-B','-c',
                               'import sys,time; print("retained prefix",flush=True); time.sleep(60)',**kw)
            wait=child.wait
            child.wait=AsyncMock(side_effect=OSError('fictional unavailable original wait'))
            return child
        try:
            with patch('coordinator_runtime.reviews.caller_current'), \
                 patch('coordinator_runtime.appserver.asyncio.create_subprocess_exec',side_effect=spawn):
                with self.assertRaises(appserver.CollectionPending) as caught:
                    await native.call(self.store,attempt,policy,context,directory,'fiction',[],opening=True)
            key=caught.exception.original
            first=(directory/'original.json').read_bytes()
            self.assertIsNone(json.loads(first)['actual_END'])
            self.assertTrue(json.loads(first)['capture_errors'])
            self.assertIs(native.originals.owned[key]['child'],child)
            child.wait=wait
            await asyncio.wait_for(native.collect_pending(self.store),3)
            self.assertEqual(native.original_status(),[])
            self.assertEqual((directory/'original.json').read_bytes(),first)
            later=json.loads((directory/'original-observations.jsonl').read_text().splitlines()[-1])
            self.assertEqual(later['actual_END'],await wait())
            self.assertEqual(later['original'],key)
            self.assertTrue(later['capture_errors'])
            self.assertFalse(later['capture_complete'])
            observations=json.loads(self.store.attempt(attempt)['detail'])['original_end_observations']
            self.assertFalse(observations[-1]['evidence']['capture_complete'])
            self.assertFalse(observations[-1]['evidence']['processing_completion'])
            self.assertIsNone(self.store.attempt(attempt)['exit'])
            self.evidence1118('timeout-later-END1127',first=json.loads(first),later=later,observations=observations)
        finally:
            if child is not None:
                child.wait=wait
                await appserver.end_owned(child,.1)

    async def stopped_owner1127(self,kind):
        from coordinator_runtime import service,reviews
        from support import result
        _,job,attempt=self.reservation();self.prepare(attempt)
        self.config['deadlines']['shutdown']=.01
        adapter=appserver.AppServer(self.config,fixture_command=['fictional'])
        native=reviews.Native();native.shutdown=.01
        child=await asyncio.create_subprocess_exec('/usr/bin/python3.12','-B','-c','import time;time.sleep(60)',
                                                  stdout=asyncio.subprocess.PIPE)
        real_wait=child.wait;child.wait=AsyncMock(side_effect=OSError('fictional unavailable wait'))
        outcome=dict(exit=None,capture='incomplete',cleanup='held',result=None,error='original wait unavailable',detail={})
        if kind=='model':
            self.store.begin(attempt,{'fictional':True})
            adapter.owned_collections[attempt]=(child,outcome)
            adapter.pending_collections[attempt]=(child,outcome)
            adapter.collection_stores[attempt]=self.store
        else:
            # Collected model rows are NOT a proxy for the separate caller.
            owner=adapter.metadata_originals if kind=='metadata' else native.originals
            async def evidence(entry):
                await asyncio.wait_for(child.stdout.read(),.01)
            key=owner.own(child,'preflight-metadata' if kind=='metadata' else 'native-caller',evidence,
                          lambda obs:self.store.record_original_end(attempt,obs))
            owner.pending[key]=owner.owned[key]
            outcome.update(exit=0,capture='not-started',cleanup='no-session-created',
                           detail={'known_not_started':True})
        self.store.collect(attempt,outcome)
        dispatcher=service.Dispatcher(self.store,{},models=adapter,review_transport=native)
        dispatcher.stopping.set();notices=[];seen=asyncio.Event()
        def emit(value):
            notices.append(value)
            if value.get('state')=='draining-originals':seen.set()
        running=asyncio.create_task(dispatcher.run(emit))
        try:
            await asyncio.wait_for(seen.wait(),3)
            self.assertFalse(running.done())
            self.assertIsNone(notices[-1]['process_END'])
            self.assertTrue(notices[-1]['originals'])
            if kind!='model':self.assertIsNotNone(self.store.attempt(attempt)['collected'])
            child.wait=real_wait
            await asyncio.wait_for(running,3)
            actual=await real_wait()
            self.assertIsInstance(actual,int)
            self.assertEqual(adapter.original_status()+native.original_status(),[])
            self.assertEqual(json.loads(self.store.attempt(attempt)['detail'])['original_end_observations'][-1]['exit'],actual)
            self.evidence1118('stop-'+kind+'1127',notices=notices,actual_END=actual)
        finally:
            child.wait=real_wait
            await appserver.end_owned(child,.1)
            await asyncio.wait_for(running,3)

    async def test_normal_stop_retains_model_original_until_later_actual_END(self):
        await self.stopped_owner1127('model')

    async def test_normal_stop_retains_metadata_original_after_model_row_collected(self):
        await self.stopped_owner1127('metadata')

    async def test_normal_stop_retains_native_original_after_model_row_collected(self):
        await self.stopped_owner1127('native')

    async def test_selected_current_recipients_observe_later_END_without_original_rewrite(self):
        from coordinator_runtime import oneoff
        _,job,attempt=self.reservation('Reviews');self.prepare(attempt)
        self.store.begin(attempt,{'fictional':True})
        outcome=dict(exit=None,capture='incomplete',cleanup='held',result=None,error='original wait unknown',detail={})
        self.store.collect(attempt,outcome)
        original=dict(self.store.one('SELECT * FROM results WHERE attempt=?',(attempt,)))
        before=oneoff.snapshot(self.store,attempt)['original_collection']
        self.store.record_original_end(attempt,dict(original=attempt,kind='appserver-model',exit=7,
            evidence={'capture_complete':False,'provider_root':'unobserved','processing_completion':False}))
        for role in ('Work','Reviews'):
            status=oneoff.current_status(self.store,attempt,role,self.config['roles'][role]['owner'])
            self.assertEqual(status['current_attempt_exit'],7)
            self.assertEqual(status['original_end_observations'][-1]['collector'],self.store.controller)
            self.assertEqual(status['capture'],'incomplete')
            self.assertFalse(status['permission_to_resume']);self.assertFalse(status['permission_to_dispose'])
            self.evidence1118('current-recipient-'+role+'1127',status=status)
        with self.assertRaisesRegex(Refusal,'original role recovery custodian'):
            oneoff.current_status(self.store,attempt,'QA',self.config['roles']['QA']['owner'])
        self.assertEqual(self.store.one('SELECT * FROM results WHERE attempt=?',(attempt,)),original)
        self.assertEqual(oneoff.snapshot(self.store,attempt)['original_collection'],before)
        self.assertIsNone(self.store.one('SELECT processed_at FROM events WHERE id=?',(json.loads(job['members'])[0]['event'],))['processed_at'])

    def placement1127(self,name='future-arena',**kw):
        selection=dict(root=str(self.area/name),authority='fictional Work right to exclusively owned new output namespace',
                       expires=self.now+100,max_attempts=4,max_entries=2000,max_bytes=128*1024**2,
                       min_free_bytes=100*1024**3,min_free_inodes=1000000,
                       journal_min_free_bytes=1024**2,journal_min_free_inodes=1000)
        selection.update(kw)
        return self.store.select_artifact_placement(self.config['roles']['Work']['owner'],selection)

    async def test_future_placement_preserves_journal_old_paths_and_exact_custody_consumers(self):
        from coordinator_runtime import custody,cleanup,oneoff
        _,job,old=self.reservation();self.prepare(old)
        legacy=self.store.home/'artifacts'/old;legacy.mkdir(parents=True)
        oldfile=legacy/'old.txt';oldfile.write_text('existing original path')
        oldinode=oldfile.stat().st_ino;journalinode=self.store.path.stat().st_ino
        self.placement1127()
        self.assertEqual(self.store.artifact_root(old),legacy)
        # Reserve a new role so the old outstanding Work duty remains held.
        _,newjob,new=self.reservation('Reviews');self.prepare(new)
        root=self.store.artifact_root(new);root.mkdir()
        self.assertFalse(root.is_relative_to(self.store.home))
        report=root/'new.txt';report.write_bytes(b'new owned report')
        task=self.config['tasks'][newjob['task']]
        frozen=custody.capture(self.store,new,str(report),task)
        self.assertEqual(frozen['kind'],'runtime-owned')
        self.assertEqual(custody.frozen_body(self.store,frozen['sha256'],path=str(report))['body'],b'new owned report')
        artifact=self.store.one('SELECT * FROM artifacts WHERE path=?',(str(report),))
        self.assertFalse(cleanup.artifact_eligible(self.store,artifact))
        with self.store.tx():
            with self.assertRaises(Refusal):cleanup.unlink_exact(self.store,artifact)
        self.assertTrue(report.exists())
        self.assertEqual(self.store.path.stat().st_ino,journalinode)
        self.assertEqual(oldfile.stat().st_ino,oldinode);self.assertEqual(oldfile.read_text(),'existing original path')
        self.assertEqual(self.store.artifact_root(old),legacy)
        usage=self.store.usage()['artifact_placements'];self.assertEqual(usage[0]['root'],str(root.parent))
        self.assertGreaterEqual(usage[0]['bytes'],len(b'new owned report'))
        self.assertIsNone(self.store.one('SELECT processed_at FROM events WHERE id=?',(json.loads(job['members'])[0]['event'],))['processed_at'])
        self.evidence1118('placement1127',old_root=str(legacy),new_root=str(root),journal=str(self.store.path),
                          custody=frozen,accounting=usage,retirement_refused=True)

    async def test_future_placement_expiry_capacity_and_exclusions_refuse_without_fallback(self):
        from coordinator_runtime.contracts import Backpressure
        self.placement1127(max_attempts=2)
        _,_,first=self.reservation();self.prepare(first)
        expected=self.store.artifact_root(first)
        with self.assertRaisesRegex(Backpressure,'attempt admission exhausted'):
            self.reservation('Reviews')
        self.assertEqual(self.store.artifact_root(first),expected)
        self.now+=101
        with self.assertRaisesRegex(Refusal,'expired/changed'):
            self.reservation('Branch')
        # Existing assignments retain their path after expiry.
        self.assertEqual(self.store.artifact_root(first),expected)
        existing=self.area/'existing';existing.mkdir()
        with self.assertRaisesRegex(Refusal,'fresh root'):
            self.placement1127('existing')
        with self.assertRaisesRegex(Backpressure,'headroom lost'):
            self.placement1127('cannot-fit',max_bytes=10**16)
        self.assertFalse((self.area/'cannot-fit').exists())
        with self.assertRaisesRegex(Backpressure,'headroom lost'):
            self.placement1127('journal-cannot-fit',journal_min_free_bytes=10**16)
        self.assertFalse((self.area/'journal-cannot-fit').exists())
        self.config.setdefault('artifact_exclusions',[]).append(str(expected.parent/'opaque-child'))
        original_iterdir=Path.iterdir
        def no_opaque_enumeration(path):
            if path==expected.parent:raise AssertionError('opaque descendant enumerated')
            return original_iterdir(path)
        with patch.object(Path,'iterdir',no_opaque_enumeration):
            with self.assertRaisesRegex(Refusal,'opaque namespace'):self.store.placement_usage()
        self.config['artifact_exclusions']=[str(expected.parent)]
        with self.assertRaises(Refusal):self.store.placement_usage()
        self.assertEqual(self.store.one('SELECT root FROM attempt_artifact_roots WHERE attempt=?',(first,))['root'],str(expected))

    async def test_initial_arena_entry_refusal_collects_truthful_no_start(self):
        self.placement1127(max_entries=1)
        message,job,attempt=self.reservation()
        self.runtime.models=type('Model',(),{'run':AsyncMock(side_effect=AssertionError('no model may start'))})()
        self.runtime.boards['Work']=object()  # Unselected ordinary effect adapter, no real Board.
        await self.runtime.execute(job['id'],attempt)
        row=self.store.attempt(attempt)
        self.assertIsNotNone(row['collected']);self.assertIsNone(row['begin']);self.assertIsNone(row['exit'])
        self.assertEqual(row['capture'],'not-started');self.assertEqual(row['cleanup'],'no-session-created')
        self.assertTrue(json.loads(row['detail'])['known_not_started'])
        self.assertIn('admission exhausted',row['error']);self.runtime.models.run.assert_not_called()
        self.assertFalse(self.store.artifact_root(attempt).exists())
        self.assertEqual(self.store.job(job['id'])['effects'],'none')
        self.assertIsNone(self.store.one('SELECT processed_at FROM events WHERE id=?',(message['id'],))['processed_at'])
        self.evidence1118('allocation-refusal1133',attempt=row,job=self.store.job(job['id']))

    async def test_initial_mkdir_failure_collects_truthful_no_start(self):
        _,job,attempt=self.reservation()
        directory=self.store.artifact_root(attempt);mkdir=Path.mkdir
        def refused(path,*args,**kwargs):
            if path==directory:raise OSError('fictional owned namespace mkdir refused')
            return mkdir(path,*args,**kwargs)
        self.runtime.models=type('Model',(),{'run':AsyncMock(side_effect=AssertionError('no model may start'))})()
        self.runtime.boards['Work']=object()  # Unselected ordinary effect adapter, no real Board.
        with patch.object(Path,'mkdir',refused):await self.runtime.execute(job['id'],attempt)
        row=self.store.attempt(attempt)
        self.assertIsNotNone(row['collected']);self.assertIsNone(row['begin']);self.assertIsNone(row['exit'])
        self.assertTrue(json.loads(row['detail'])['known_not_started'])
        self.assertEqual(row['capture'],'not-started');self.assertEqual(row['cleanup'],'no-session-created')
        self.assertIn('mkdir refused',row['error']);self.runtime.models.run.assert_not_called()
        self.assertFalse(directory.exists());self.assertEqual(self.store.job(job['id'])['effects'],'none')
        self.evidence1118('mkdir-refusal1133',attempt=row)

    async def test_future_destination_charges_only_growing_arena_but_all_actual_usage(self):
        from coordinator_runtime.contracts import Backpressure
        first=self.placement1127('old-arena',max_bytes=16384)
        old=Path(first['selection']['root']);fill=old/'retained.txt';fill.touch()
        fill.write_bytes(b'x'*(16384-old.stat().st_size-1))
        before=self.store.placement_usage();self.assertEqual(before[0]['bytes'],16383)
        # Expiry does not remove actual usage or charge new growth to this arena.
        self.now+=101
        second=self.placement1127('new-arena')
        _,_,attempt=self.reservation();root=self.store.artifact_root(attempt)
        self.assertEqual(root.parent,Path(second['selection']['root']))
        self.store.admit_artifact_write(attempt,8192,2)
        root.mkdir();(root/'new.txt').write_text('new destination only')
        self.store.budget(None,8192)
        journal_owned=self.store.home/'journal-owned1133.txt';journal_owned.write_bytes(b'journal-owned growth remains charged')
        actual=self.store.usage()
        self.assertEqual(actual['artifact_placements'][0],before[0])
        self.assertEqual(fill.stat().st_size,16383-old.stat().st_size)
        self.assertGreater(actual['bytes'],sum(p['bytes'] for p in actual['artifact_placements']))
        with self.assertRaisesRegex(Backpressure,'exhausted'):
            self.store.placement_usage(2,admission=first['admission'])
        # Retained overage, global pressure and journal/site floors still refuse.
        with fill.open('ab') as stream:stream.write(b'xx')
        with self.assertRaisesRegex(Backpressure,'exhausted'):self.store.budget(None,1)
        with fill.open('r+b') as stream:stream.truncate(16383-old.stat().st_size)
        prior=self.config['limits']['max_bytes'];self.config['limits']['max_bytes']=actual['bytes']+8192
        try:
            with self.assertRaises(Backpressure):self.store.admit_artifact_write(attempt,8192,1)
        finally:self.config['limits']['max_bytes']=prior
        headroom=self.store.placement_headroom
        def no_shared_site(site,spec,incoming=0,entries=0):
            if site==old and incoming:raise Backpressure('fictional shared site floor')
            return headroom(site,spec,incoming,entries)
        with patch.object(self.store,'placement_headroom',side_effect=no_shared_site):
            with self.assertRaisesRegex(Backpressure,'shared site floor'):
                self.store.admit_artifact_write(attempt,8192,1)
        def no_journal(site,spec,incoming=0,entries=0):
            if site==self.store.home and incoming:raise Backpressure('fictional journal floor')
            return headroom(site,spec,incoming,entries)
        with patch.object(self.store,'placement_headroom',side_effect=no_journal):
            with self.assertRaisesRegex(Backpressure,'journal floor'):self.store.budget(None,8192)
        self.evidence1118('destination1133',before=before,after=actual,new_root=str(root))

    async def test_noncanonical_new_operands_refuse_before_any_metadata(self):
        # Every target below is NEW owned fiction; no real held path or alias.
        parent=self.area/'lexical1133';parent.mkdir()
        self.config['artifact_exclusions']=[str(parent/'opaque')]
        selection=dict(root=str(parent/'fresh'),authority='fictional right',expires=self.now+100,
            max_attempts=4,max_entries=100,max_bytes=1024**2,min_free_bytes=1,min_free_inodes=1,
            journal_min_free_bytes=1,journal_min_free_inodes=1)
        observed=[]
        def forbidden(*args,**kw):
            observed.append(str(args[0]) if args else 'metadata');raise AssertionError('metadata before lexical refusal')
        cases=['/'+str(parent/'opaque'/'child'),'/'+str(self.store.home/'child'),
               '/'+str(parent/'fresh'),str(parent)+'/a/../fresh',str(parent)+'//fresh',str(parent)+'/fresh/']
        for operand in cases:
            with self.subTest(operand=operand),patch.object(Path,'is_symlink',forbidden),\
                 patch.object(Path,'exists',forbidden),patch.object(Path,'stat',forbidden),\
                 patch.object(Path,'mkdir',forbidden),patch('coordinator_runtime.store.os.statvfs',forbidden):
                with self.assertRaisesRegex(Refusal,'plain artifact root'):
                    self.store.select_artifact_placement(self.config['roles']['Work']['owner'],{**selection,'root':operand})
        self.assertEqual(observed,[])
        # Canonical exclusions and ordinary positive independent admission remain.
        with self.assertRaises(Refusal):
            self.store.select_artifact_placement(self.config['roles']['Work']['owner'],{**selection,'root':str(parent/'opaque'/'child')})
        admitted=self.store.select_artifact_placement(self.config['roles']['Work']['owner'],selection)
        self.assertEqual(admitted['selection'],selection)
        self.evidence1118('lexical1133',refused=cases,metadata_before_refusal=observed,positive=admitted)

    async def service_closing1133(self, ingress):
        from coordinator_runtime import service,reviews,processing
        from coordinator_runtime.contracts import digest,encode
        from types import SimpleNamespace
        import fcntl
        message,job,attempt=self.reservation()
        key='fictional-service1133'
        detail={**json.loads(self.store.attempt(attempt)['detail']),'processing_capability':key}
        self.store.db.execute('UPDATE attempts SET detail=? WHERE id=?',(encode(detail),attempt))
        self.prepare(attempt)
        self.store.collect(attempt,dict(exit=0,capture='not-started',cleanup='no-session-created',result=None,
                                      error='fictional collected model',detail={'known_not_started':True}))
        native=reviews.Native();native.shutdown=.01
        selection=dict(basis=dict(configuration=digest(self.config),implementation=processing.implementation(),
                           roles={'Work':dict(original=dict(events=[dict(id=message['id'],hash=digest(message))]),future_after=0)}),
                       retained_events=[message['id']],recover_controls={},
                       service=dict(reviews={}),future_intake=True,tasks=[job['task']])
        self.store.db.execute('INSERT INTO processing_capabilities VALUES(?,?,?,0,NULL,0)',
                              (key,encode(selection),'fictional-Work'))
        ready=asyncio.Event();entered=asyncio.Event();release=asyncio.Event();draining=asyncio.Event()
        child=None;actual=[];notices=[];dispatchers=[]
        rows=self.store.rows
        def selected_rows(sql,values=()):
            if sql.startswith('SELECT component FROM review_contexts'):
                return [] if ingress else [{'component':'fictional-context1133'}]
            return rows(sql,values)
        async def close(executor,component,policy):
            nonlocal child
            entered.set()
            if ingress:await release.wait()  # Accepted control BEFORE registration.
            child=await asyncio.create_subprocess_exec('/usr/bin/python3.12','-B','-c','import time;time.sleep(60)',
                                                       stdout=asyncio.subprocess.PIPE)
            real_wait=child.wait
            child.real_wait1133=real_wait
            child.wait=AsyncMock(side_effect=OSError('fictional original wait unavailable'))
            async def evidence(entry):await asyncio.wait_for(child.stdout.read(),.01)
            delivery_errors=[]
            def deliver(obs):
                try:self.store.record_original_end(attempt,obs)
                except Exception as exc:
                    if not delivery_errors:print('SERVICE1133-DELIVERY '+repr(exc),flush=True)
                    delivery_errors.append(type(exc).__name__);raise
            original=native.originals.own(child,'native-caller',evidence,deliver)
            native.originals.pending[original]=native.originals.owned[original]
            if not ingress:raise Refusal('fictional close pending')
            return dict(closed=False,provider_root='held')
        async def activity(dispatcher,emit):
            dispatchers.append(dispatcher)
            if ingress:await dispatcher.stopping.wait()
        def emit(value):
            notices.append(value)
            if value.get('state')=='serving':ready.set()
            if value.get('state')=='draining-originals':draining.set()
        wake=SimpleNamespace(start=lambda:None,close=lambda:None,status=lambda:{'fictional':True})
        running=None;writer=None
        try:
            with patch.object(self.store,'rows',side_effect=selected_rows),\
                 patch.object(service.Dispatcher,'run',activity),\
                 patch.object(service.Dispatcher,'recover_originals',lambda d:{'collector':d.store.controller,'processing_complete':False}),\
                 patch.object(reviews.Executor,'close',close),\
                 patch.object(reviews,'context_policy',return_value={}),\
                 patch('coordinator_runtime.service_wake.ServiceWake',return_value=wake),\
                 patch.object(self.store,'record_operational_error',side_effect=sqlite3.OperationalError('fictional reporting refused')):
                running=asyncio.create_task(service.serve_owned(self.store,{},key,emit,models=object(),review_transport=native))
                await asyncio.wait_for(ready.wait(),3)
                if ingress:
                    reader,writer=await asyncio.open_unix_connection(path=service.endpoint(self.store,key))
                    writer.write((encode(dict(capability=key,operation='close-review',component='fictional-context1133'))+'\n').encode())
                    await writer.drain();await asyncio.wait_for(entered.wait(),3)
                    dispatchers[0].stopping.set()
                    # Give shutdown the next scheduling turns; accepted callback
                    # has no registry entry yet and still must retain its owner.
                    for _ in range(8):await asyncio.sleep(0)
                    self.assertFalse(running.done());self.assertEqual(native.original_status(),[])
                    with self.assertRaises(OSError):
                        await asyncio.open_unix_connection(path=service.endpoint(self.store,key))
                    release.set()
                await asyncio.wait_for(draining.wait(),3)
                self.assertFalse(running.done());self.assertTrue(native.original_status())
                self.assertFalse(any('service_observations' in n and 'collector' in n for n in notices))
                self.assertIsNone(self.store.one('SELECT returned FROM service_runs')['returned'])
                fd=os.open(self.store.home/'service.lock',os.O_RDWR)
                try:
                    with self.assertRaises(BlockingIOError):fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
                finally:os.close(fd)
                child.wait=child.real_wait1133
                if ingress:
                    await asyncio.wait_for(running,3)
                    answer=json.loads(await asyncio.wait_for(reader.readline(),3))
                    self.assertFalse(answer['closed'])
                    self.assertIsNotNone(self.store.one('SELECT returned FROM service_runs')['returned'])
                else:
                    with self.assertRaisesRegex(sqlite3.OperationalError,'reporting refused'):
                        await asyncio.wait_for(running,3)
                    self.assertIsNone(self.store.one('SELECT returned FROM service_runs')['returned'])
                actual.append(await child.real_wait1133())
                self.assertEqual(native.original_status(),[])
                obs=json.loads(self.store.attempt(attempt)['detail'])['original_end_observations'][-1]
                self.assertEqual(obs['exit'],actual[-1]);self.assertEqual(obs['kind'],'native-caller')
                self.evidence1118('service-ingress1133' if ingress else 'service-report-refusal1133',
                                  actual_END=actual,notices=notices,original_observation=obs)
        finally:
            release.set()
            if child is not None:
                child.wait=child.real_wait1133
                await appserver.end_owned(child,.1)
            if writer is not None:writer.close();await writer.wait_closed()
            if running is not None and not running.done():
                dispatchers[0].stopping.set()
                try:await asyncio.wait_for(running,3)
                except sqlite3.OperationalError:pass

    async def test_service_close_reporting_failure_still_retains_and_collects_new_original(self):
        await self.service_closing1133(False)

    async def test_service_joins_accepted_control_before_registration_and_final_original_drain(self):
        await self.service_closing1133(True)

    async def test_current_recipient_and_placement_CLI_use_explicit_lawful_grant_mode(self):
        from coordinator_runtime import cli,processing,oneoff
        from coordinator_runtime.board import Board
        from coordinator_runtime.contracts import digest,encode
        from contextlib import contextmanager
        message,job,attempt=self.reservation('Reviews');self.prepare(attempt)
        self.store.begin(attempt,{'fictional':True})
        self.store.collect(attempt,dict(exit=None,capture='incomplete',cleanup='held',result=None,
                                       error='original unknown',detail={}))
        self.store.record_original_end(attempt,dict(original=attempt,kind='appserver-model',exit=7))
        original=self.store.one('SELECT * FROM results WHERE attempt=?',(attempt,))
        self.config['software_delegation']=dict(grantor=self.config['roles']['Work']['owner'],authority='fictional-lawful-right')
        # Only membership/catalog transport and actual session identity are
        # fictional. Ordinary/retained grant checks, Access, source/hold guards,
        # current projection and placement admission all run unchanged.
        conn=sqlite3.connect(':memory:',isolation_level=None);conn.row_factory=sqlite3.Row
        self.addCleanup(conn.close)
        conn.executescript('CREATE TABLE coordinator_grants_v1(id,board_id,role,owner,actor,runtime,runtime_dev,runtime_ino,issued_by,authority,revoked);'
                           'CREATE TABLE coordinator_software_grants_v1(grant_id,configuration);')
        stat=self.store.path.stat()
        for role in self.config['roles']:
            enrolled=self.store.enrollment(role);selected=self.config['roles'][role]
            conn.execute('INSERT INTO coordinator_grants_v1 VALUES(?,?,?,?,?,?,?,?,?,?,NULL)',
                (enrolled['grant_id'],selected['board_id'],role,selected['owner'],self.config['actor'],
                 str(self.store.path),stat.st_dev,stat.st_ino,self.config['software_delegation']['grantor'],'fictional-lawful-right'))
            conn.execute('INSERT INTO coordinator_software_grants_v1 VALUES(?,?)',(enrolled['grant_id'],digest(self.config)))
        class Ordinary(Board):
            def __init__(board,config,role):board.config=config;board.role=role;board.selected=config['roles'][role]
            @contextmanager
            def opened(board,**kw):yield conn
        class Retained(processing.ProcessingBoard,Ordinary):
            __init__=Ordinary.__init__
        def current(role,cap=None):
            args=['original-current-status',attempt,'--role',role]+(['--capability',cap] if cap else [])
            return cli.operate(cli.parser().parse_args(args),self.store)
        spec=dict(root=str(self.area/'cli-ordinary-arena'),authority='fictional exclusive right',expires=self.now+100,
            max_attempts=4,max_entries=100,max_bytes=1024**2,min_free_bytes=1,min_free_inodes=1,
            journal_min_free_bytes=1,journal_min_free_inodes=1)
        selection_file=self.area/'selection1133.json';selection_file.write_text(encode(spec))
        with patch.object(cli,'Board',Ordinary),patch.object(processing,'ProcessingBoard',Retained),\
             patch.object(cli,'actual_actor',side_effect=lambda owner:owner):
            for role in ('Work','Reviews'):
                view=current(role);self.assertEqual(view['current_attempt_exit'],7)
                self.assertFalse(view['permission_to_resume']);self.assertFalse(view['permission_to_dispose'])
            cli.operate(cli.parser().parse_args(['select-artifact-placement','--selection',str(selection_file)]),self.store)
            conn.execute("UPDATE coordinator_grants_v1 SET revoked='fictional-revocation'")
            self.store.db.execute('UPDATE enrollments SET intake=0')
            roles={}
            for role in self.config['roles']:
                grant=dict(conn.execute('SELECT * FROM coordinator_grants_v1 WHERE role=?',(role,)).fetchone())
                roles[role]=dict(original=dict(binding=Retained._binding(grant),
                    events=self.store.rows('SELECT id,hash FROM events WHERE role=?',(role,))),future_after=0)
            key='fictional-current1133'
            selection=dict(basis=dict(configuration=digest(self.config),implementation=processing.implementation(),roles=roles),
                retained_events=[message['id']],recover_controls={},future_intake=False,tasks=[job['task']],expires=self.now+100)
            self.store.db.execute('INSERT INTO processing_capabilities VALUES(?,?,?,0,NULL,0)',
                                  (key,encode(selection),self.config['roles']['Work']['owner']))
            for role in ('Work','Reviews'):
                with self.assertRaises(Refusal):current(role)
                view=current(role,key);self.assertEqual(view['current_attempt_exit'],7)
                self.assertEqual(view['original_end_observations'][-1]['collector'],self.store.controller)
                self.assertEqual(view['capture'],'incomplete');self.assertFalse(view['permission_to_dispose'])
            spec['root']=str(self.area/'cli-retained-arena');selection_file.write_text(encode(spec))
            with self.assertRaises(Refusal):
                cli.operate(cli.parser().parse_args(['select-artifact-placement','--selection',str(selection_file)]),self.store)
            admitted=cli.operate(cli.parser().parse_args(['select-artifact-placement','--selection',str(selection_file),'--capability',key]),self.store)
            with self.assertRaises(Refusal):current('QA',key)
            with patch.object(cli,'actual_actor',side_effect=Refusal('fictional foreign actor')):
                with self.assertRaisesRegex(Refusal,'foreign actor'):current('Work',key)
            self.store.set_hold(message['id'],'fictional source privacy hold')
            for role in ('Work','Reviews'):
                with self.assertRaises(Refusal):current(role,key)
            self.store.set_hold(message['id'],None)
            with self.assertRaisesRegex(Refusal,'absent'):current('Work','fictional-absent')
            conn.execute("UPDATE coordinator_grants_v1 SET runtime_ino=runtime_ino+1 WHERE role='Work'")
            with self.assertRaisesRegex(Refusal,'binding changed'):current('Work',key)
        self.assertEqual(self.store.one('SELECT * FROM results WHERE attempt=?',(attempt,)),original)
        self.assertEqual(self.store.one('SELECT intake FROM enrollments WHERE role=?',('Work',))['intake'],0)
        self.evidence1118('lawful-current1133',retained_admission=admitted,historical_result=original)
