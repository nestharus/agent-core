"""Fresh preparation admission in owned catalog/SDK fiction, never live state.

Real selection, mapping, binding, preparation, dispatch and collection run.
Only principal authentication and the typed model answer are synthetic seams.
Holds commit on a second connection at named boundaries, not timing guesses.
"""
from contextlib import ExitStack, contextmanager
import json
from pathlib import Path
import sqlite3
import unittest
from unittest.mock import AsyncMock, Mock, patch

from support import collect, result
from coordinator_runtime import local_integration as local, routine, selected_source
from coordinator_runtime import dispatcher
from coordinator_runtime.contracts import Refusal, encode, ident
from coordinator_runtime.appserver import AppServer
from coordinator_runtime.store import Store
from test_retained_catalog717 import CatalogCase


class Preparation(CatalogCase, unittest.IsolatedAsyncioTestCase):
    def bound_job(self):
        self.new_job(bind=False)
        self.boards['Work'].bind_software_attempt(self.store, self.job, self.attempt, None)
        return self.config['tasks'][self.job['task']]

    def hold(self, event=None, reason='fictional late hold'):
        owner = Store(self.config)
        try:
            owner.set_hold(event or self.source['id'], reason)
        finally:
            owner.close()

    def neighbor(self):
        scope = local.scope_for(self.store, self.job)
        queue = self.store.one('SELECT id,event,package FROM queue WHERE event=?', (self.other['id'],))
        scope['neighbors'] = [dict(queue=queue['id'], event=queue['event'], package=queue['package'], hash='0'*64)]
        self.store.db.execute('UPDATE local_jobs SET scope=? WHERE job=?', (encode(scope), self.job['id']))
        return self.other['id']

    @contextmanager
    def no_acquisition(self):
        def authorize(action, table, column, database, caller):
            if action == sqlite3.SQLITE_READ and (
                    table == 'events' and column == 'payload'
                    or table == 'attempts' and column == 'result'
                    or table in {'source_custody', 'results', 'artifact_blobs'}):
                raise AssertionError('body/result acquired before admission: '+table+'.'+column)
            return sqlite3.SQLITE_OK
        self.store.db.set_authorizer(authorize)
        try:
            with ExitStack() as stack:
                for name in ('read_file', 'safe_path', 'frozen_body', 'materialize'):
                    stack.enter_context(patch('coordinator_runtime.custody.'+name,
                        side_effect=AssertionError('path/artifact acquired: '+name)))
                stack.enter_context(patch.object(routine, 'snapshot', side_effect=AssertionError('preimage acquired')))
                stack.enter_context(patch.object(dispatcher, 'template_text', side_effect=AssertionError('template acquired')))
                yield
        finally:
            self.store.db.set_authorizer(None)

    def assert_unprepared(self):
        for table in ('local_bases', 'routine_runs', 'routine_stages', 'file_publications', 'local_commits', 'ordinary_runs'):
            self.assertEqual(self.store.rows('SELECT * FROM '+table), [], table)

    async def test_direct_routine_and_prompt_refuse_member_and_neighbor_before_first_read(self):
        task = self.bound_job()
        for event in (self.source['id'], self.neighbor()):
            self.hold(event, '')  # Empty non-null reasons remain holds.
            with self.no_acquisition():
                for operation in (
                        lambda: routine.prepare(self.store, self.boards['Work'], self.job, self.attempt, task),
                        lambda: dispatcher.job_prompt(self.store, self.job, task),
                        lambda: local.prepare(self.store, self.job, self.attempt,
                            {'fictional':dict(sha256='0'*64)})):
                    with self.assertRaises(Refusal): operation()
            self.hold(event, None)
        self.assert_unprepared()

    async def test_full_execute_hold_after_binding_before_preparation(self):
        self.new_job(bind=False)
        original = self.boards['Work'].bind_software_attempt
        model = AsyncMock(side_effect=AssertionError('model admitted'))
        self.runtime.models = type('Models', (), {'run':model})()
        self.runtime.try_finish = Mock()
        with ExitStack() as stack:
            def bind(*args):
                value = original(*args)
                self.hold()
                stack.enter_context(self.no_acquisition())
                return value
            stack.enter_context(patch.object(self.boards['Work'], 'bind_software_attempt', side_effect=bind))
            # Collection legitimately reads/writes its OWN new attempt;
            # the acquisition authorizer ends at the collection boundary.
            original_collect = self.store.collect
            def collected(*args):
                stack.close()
                return original_collect(*args)
            stack.enter_context(patch.object(self.store, 'collect', side_effect=collected))
            await self.runtime.execute(self.job['id'], self.attempt)
        model.assert_not_called()
        self.assert_unprepared()
        self.assertEqual(self.store.attempt(self.attempt)['state'], 'not-started')

    async def test_full_execute_held_neighbor_before_preparation(self):
        self.new_job(bind=False)
        original = self.boards['Work'].bind_software_attempt
        def bind(*args):
            value = original(*args)
            self.hold(self.neighbor())
            return value
        self.runtime.models = Mock(run=AsyncMock(side_effect=AssertionError('model admitted')))
        self.runtime.try_finish = Mock()
        with patch.object(self.boards['Work'], 'bind_software_attempt', side_effect=bind), \
             patch.object(routine, 'snapshot', side_effect=AssertionError('preimage acquired')):
            await self.runtime.execute(self.job['id'], self.attempt)
        self.runtime.models.run.assert_not_called()
        self.assert_unprepared()

    async def test_snapshot_retry_releases_then_revalidates_after_await(self):
        self.new_job(bind=False)
        self.runtime.try_finish = Mock()
        self.runtime.models = Mock(run=AsyncMock(side_effect=AssertionError('model admitted')))
        actual_lock = routine.publication.snapshot_lock
        actual_prepare = routine.prepare
        locks = []
        preparing = False
        def prepare(*args):
            nonlocal preparing
            preparing = True
            try: return actual_prepare(*args)
            finally: preparing = False
        @contextmanager
        def lock(store):
            if not preparing:
                with actual_lock(store): yield
                return
            self.assertFalse(store.db.in_transaction, 'SQLite lock held while acquiring publication lock')
            locks.append(True)
            if len(locks) == 1:
                raise BlockingIOError('fictional snapshot contention')
            with actual_lock(store): yield
        async def pause(delay):
            self.assertFalse(self.store.db.in_transaction, 'SQLite lock held across await')
            self.hold()
        with patch.object(routine.publication, 'snapshot_lock', side_effect=lock), \
             patch.object(routine, 'prepare', side_effect=prepare), \
             patch.object(dispatcher.asyncio, 'sleep', side_effect=pause), \
             patch.object(routine, 'snapshot', side_effect=AssertionError('late preimage acquired')):
            await self.runtime.execute(self.job['id'], self.attempt)
        self.runtime.models.run.assert_not_called()
        self.assert_unprepared()
        self.assertEqual(len(locks), 1)
        self.assertEqual(self.store.attempt(self.attempt)['state'], 'not-started')

    async def test_new_prompt_group_rechecks_after_successful_staging(self):
        self.new_job(bind=False)
        original = routine.prepare
        self.runtime.try_finish = Mock()
        self.runtime.models = Mock(run=AsyncMock(side_effect=AssertionError('model admitted')))
        with ExitStack() as stack:
            def prepare(*args):
                original(*args)
                self.hold()
                stack.enter_context(patch.object(self.store, 'event', side_effect=AssertionError('late source acquired')))
                stack.enter_context(patch.object(dispatcher, 'template_text', side_effect=AssertionError('late template acquired')))
            stack.enter_context(patch.object(routine, 'prepare', side_effect=prepare))
            await self.runtime.execute(self.job['id'], self.attempt)
        self.runtime.models.run.assert_not_called()
        self.assertTrue(self.store.rows('SELECT * FROM routine_stages'))  # Already admitted work is conserved.
        self.assertEqual(self.store.rows('SELECT * FROM file_publications'), [])

    async def test_direct_retained_guard_rechecks_before_packet_and_point_groups(self):
        self.bound_job()
        authority = dispatcher.prospective.for_job(self.store, self.job)
        attempt = self.store.attempt(self.attempt)
        current = local.current_job
        with ExitStack() as stack:
            def checked(*args):
                current(*args)
                self.hold()
                stack.enter_context(patch.object(self.store, 'event', side_effect=AssertionError('late selected source acquired')))
            stack.enter_context(patch.object(local, 'current_job', side_effect=checked))
            self.assertFalse(selected_source.permits_job(self.store, self.job, authority, attempt))
        self.hold(reason=None)
        packet = local.packet
        from coordinator_runtime.custody import read_file
        def permitted(path, *args, **kwargs):
            if str(path) in self.targets:
                raise AssertionError('late selected point acquired')
            return read_file(path, *args, **kwargs)  # Public pinned method validation remains required.
        with ExitStack() as stack:
            def acquired(*args):
                value = packet(*args)
                self.hold()
                stack.enter_context(patch('coordinator_runtime.custody.read_file', side_effect=permitted))
                return value
            stack.enter_context(patch.object(local, 'packet', side_effect=acquired))
            self.assertFalse(selected_source.permits_job(self.store, self.job, authority, attempt))

    async def test_staging_helper_refuses_hold_before_frozen_preimage_or_directory(self):
        self.bound_job()
        self.hold()
        directory = self.store.home/'artifacts'/self.attempt/'staged'
        with self.no_acquisition(), self.assertRaises(Refusal):
            routine.publication.prepare(self.store, self.attempt, {'fictional':dict(exists=True, sha256='0'*64)})
        self.assertFalse(directory.exists())

    def diagnosed_job(self):
        self.bound_job()
        collect(self.store, self.attempt, result(semantic='FAILED'), code=1)
        self.job = self.store.claim_recovery(self.job['id'])
        self.assertIsNotNone(self.job)

    async def test_recovery_selection_and_allocation_refuse_before_prior_result(self):
        self.bound_job()
        collect(self.store, self.attempt, result(semantic='FAILED'), code=1)
        for event in (self.source['id'], self.neighbor()):
            self.hold(event)
            before = self.store.job(self.job['id'])
            with self.no_acquisition():
                self.assertIsNone(self.store.claim_recovery(self.job['id']))
                with self.assertRaises(Refusal): self.store.diagnosis_attempt(self.job['id'])
                with self.assertRaises(Refusal):
                    self.store.request_recovery(self.job['id'], self.job['token'], self.attempt,
                        self.config['roles']['Work']['owner'], dict(mode='remaining-work',
                            reason='Fictional owned remaining target', remaining='Conserve fictional duty',
                            evidence=['Fictional collected original']))
            self.assertEqual(self.store.job(self.job['id']), before)
            self.hold(event, None)

    async def test_pending_remaining_work_rechecks_before_consuming_prior_context(self):
        self.bound_job()
        collect(self.store, self.attempt, result(semantic='FAILED'), code=1)
        # Exact public pending-request table shape; this isolated seam avoids
        # asserting an effect reconciliation or an owner request as authentic.
        request = ident()
        self.store.db.execute('INSERT INTO recovery_requests VALUES(?,?,?,?,?,?,?,NULL)',
            (request, self.job['id'], self.attempt, self.config['roles']['Work']['owner'],
             encode(dict(mode='remaining-work', reason='Fictional duty', remaining='Fictional remainder',
                         evidence=['Fictional closed task'])), 'pending', self.store.clock()))
        before = self.store.one('SELECT * FROM recovery_requests WHERE id=?', (request,))
        self.hold(self.neighbor())
        with self.no_acquisition(), self.assertRaises(Refusal): self.store.consume_recovery_request(request)
        self.assertEqual(self.store.one('SELECT * FROM recovery_requests WHERE id=?', (request,)), before)

    async def test_diagnostic_admission_and_begin_check_metadata_without_prior_result(self):
        self.diagnosed_job()
        diagnosis = self.store.diagnosis_attempt(self.job['id'])
        before = self.store.attempt(diagnosis)
        self.hold(self.neighbor())
        with self.no_acquisition():
            with self.assertRaises(Refusal): dispatcher.recovery_prompt(self.store, self.job)
            with self.assertRaises(Refusal): self.store.authorize_launch(diagnosis)
            with self.assertRaises(Refusal): self.store.begin(diagnosis, {})
        self.assertEqual(self.store.attempt(diagnosis), before)

    async def test_full_recover_refuses_hold_before_prior_context_and_collects_no_start(self):
        self.diagnosed_job()
        allocate = self.store.diagnosis_attempt
        self.runtime.models = Mock(run=AsyncMock(side_effect=AssertionError('diagnostic model admitted')))
        self.runtime.advance_recovery = Mock()
        with ExitStack() as stack:
            def diagnosis(*args):
                value = allocate(*args)
                self.hold()
                actual = self.store.attempt
                def allowed(key):
                    if key == self.attempt:
                        raise AssertionError('held prior task result acquired')
                    return actual(key)
                stack.enter_context(patch.object(self.store, 'attempt', side_effect=allowed))
                return value
            stack.enter_context(patch.object(self.store, 'diagnosis_attempt', side_effect=diagnosis))
            await self.runtime.recover(self.job)
        self.runtime.models.run.assert_not_called()
        latest = self.store.one("SELECT * FROM attempts WHERE job=? AND kind='diagnosis'", (self.job['id'],))
        self.assertEqual(latest['state'], 'not-started')
        self.assertIsNone(latest['begin'])
        self.assertIsNotNone(latest['collected'])

    async def test_unheld_diagnosis_allows_stale_points_and_preserves_collection_after_hold(self):
        self.diagnosed_job()
        self.catalog.write_text(self.catalog.read_text().replace('original', 'changed'))
        original = self.store.attempt(self.attempt)
        async def model(store, attempt, prompt, spec, schema):
            self.assertIn('prior_attempt', prompt)
            store.begin(attempt, {'fictional_diagnosis':True})
            self.hold()
            return dict(exit=0, capture='complete', cleanup='fictional-no-child',
                result=dict(profile='@owner', remaining='Owner disposition', rationale='Fictional conserved duty'))
        self.runtime.models = Mock(run=AsyncMock(side_effect=model))
        self.runtime.advance_recovery = Mock()
        with patch.object(local, 'current_job', side_effect=AssertionError('effectful current point check on diagnosis')):
            await self.runtime.recover(self.job)
        self.runtime.models.run.assert_awaited_once()
        self.assertEqual(self.store.attempt(self.attempt), original)
        diagnosis = self.store.one("SELECT * FROM attempts WHERE job=? AND kind='diagnosis'", (self.job['id'],))
        self.assertEqual(diagnosis['state'], 'collected')
        self.assertEqual(diagnosis['exit'], 0)

    async def test_diagnostic_turn_rechecks_after_async_admission(self):
        self.diagnosed_job()
        diagnosis = self.store.diagnosis_attempt(self.job['id'])
        from contextlib import asynccontextmanager
        @asynccontextmanager
        async def admission(profile):
            self.assertFalse(self.store.db.in_transaction)
            self.hold()
            yield {}
        adapter = AppServer(self.config)
        with patch.object(self.store.execution_pool, 'admission', admission), \
             patch.object(adapter, 'start_turn', new_callable=AsyncMock) as start:
            with self.assertRaises(Refusal):
                await adapter.turn(object(), self.store, diagnosis, ident(), 'fictional',
                    dict(cwd=str(self.area), sandbox='read-only'), self.config['diagnosis']['binding'], {}, {})
        start.assert_not_called()

    async def test_unheld_full_execute_preserves_catalog_and_effects_none_flows(self):
        self.new_job(bind=False)
        self.runtime.try_finish = Mock()
        async def model(store, attempt, prompt, spec, schema):
            self.assertIn('TASK_CONTEXT=', prompt)
            store.begin(attempt, {'fictional_task':True})
            return dict(exit=0, capture='complete', cleanup='fictional-no-child', result=result())
        self.runtime.models = Mock(run=AsyncMock(side_effect=model))
        await self.runtime.execute(self.job['id'], self.attempt)
        self.runtime.models.run.assert_awaited_once()
        self.assertEqual(self.store.attempt(self.attempt)['state'], 'collected')
        self.assertEqual(self.store.attempt(self.attempt)['exit'], 0)
        task = self.config['tasks'][self.job['task']]
        self.assertEqual(bool(self.store.rows('SELECT * FROM routine_stages')), bool(task.get('routine_completion')))
        self.assertIsNotNone(self.store.one('SELECT basis FROM local_bases WHERE attempt=?', (self.attempt,)))
        self.assertEqual(self.store.rows('SELECT * FROM file_publications'), [])
        self.assertEqual(self.store.rows('SELECT * FROM ordinary_runs'), [])
        self.assertEqual({p:Path(p).read_bytes() for p in self.targets}, self.original_files)

    async def test_admitted_prompt_may_finish_but_later_group_is_refused(self):
        task = self.bound_job()
        directory = self.store.home/'artifacts'/self.attempt
        directory.mkdir(parents=True)
        if task.get('routine_completion'):
            routine.prepare(self.store, self.boards['Work'], self.job, self.attempt, task)
        else:
            local.prepare_input_basis(self.store, self.job, self.attempt, task)
        actual = dispatcher.template_text
        def template(path):
            self.hold()
            return actual(path)
        with patch.object(dispatcher, 'template_text', side_effect=template):
            self.assertIn('TASK_CONTEXT=', dispatcher.job_prompt(self.store, self.job, task))
        with self.no_acquisition(), self.assertRaises(Refusal):
            dispatcher.job_prompt(self.store, self.job, task)
        with self.assertRaises(Refusal): self.store.authorize_launch(self.attempt)


class ReadOnlyPreparation(Preparation):
    def setUp(self):
        from test_retained_launch705 import ProposerLaunch
        ProposerLaunch.setUp(self)

    def route_receipt(self):
        value = super().route_receipt()
        return {**value, 'task':'work-proposer', 'integration':{**value['integration'], 'writes':[]}}

    async def test_direct_input_basis_checks_before_point_path(self):
        task = self.bound_job()
        for event in (self.source['id'], self.neighbor()):
            self.hold(event)
            with self.no_acquisition(), self.assertRaises(Refusal):
                local.prepare_input_basis(self.store, self.job, self.attempt, task)
            self.hold(event, None)
        self.assert_unprepared()

    # Inherit only the applicable full dispatcher and diagnostic probes.
    test_direct_routine_and_prompt_refuse_member_and_neighbor_before_first_read = None
    test_snapshot_retry_releases_then_revalidates_after_await = None
    test_new_prompt_group_rechecks_after_successful_staging = None


if __name__ == '__main__':
    unittest.main(verbosity=2)
