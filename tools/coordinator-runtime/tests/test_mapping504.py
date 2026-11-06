"""Fictional owned records only; no provider, native or actual runtime evidence."""
import asyncio
import contextlib
import io
import json
import unittest
from unittest.mock import patch

from coordinator_runtime import cli, observations, processing, service
from coordinator_runtime.contracts import Backpressure, Refusal, encode
import test_software_consumption as software
import test_metadata471 as metadata
import test_startup_control346 as startup


class MappingTelemetry(unittest.IsolatedAsyncioTestCase):
    asyncSetUp = metadata.Automatic.asyncSetUp
    post = metadata.Automatic.post
    git = metadata.Automatic.git
    admission = metadata.Automatic.admission
    classified = metadata.Automatic.classified
    choice = metadata.Automatic.choice
    drain = metadata.Automatic.drain
    mapped = metadata.Automatic.mapped

    async def test_real_tick_maps_and_preserves_independent_sibling_under_active_telemetry(self):
        with observations.owning('service') as record:
            source = self.post(text='Fictional existing a requiring current metadata')
            first = await self.classified(source, '@unresolved')
            self.dispatcher.receipts()
            self.assertEqual(self.store.one('SELECT ack FROM events WHERE id=?', (source['id'],))['ack'], 'plain')
            self.choice(source, 'work-proposer', 'a')
            await self.mapped(source)
            fresh = await self.classified(source, 'work-proposer')
            self.assertNotEqual(first, fresh)
            job = self.store.reserve()
            self.assertIsNotNone(job)
            sibling = self.post(text='Fictional independent b with its own responsibility')
            await self.classified(sibling, 'work-proposer')
            self.choice(sibling, 'work-proposer', 'b')
            await self.mapped(sibling)
            await self.classified(sibling, 'work-proposer')
            other = self.store.reserve()
            self.assertIsNotNone(other)
            self.assertNotEqual(job['id'], other['id'])
            self.assertIsNone(self.store.one('SELECT processed_at FROM events WHERE id=?', (source['id'],))['processed_at'])
            self.assertTrue(all(row['intake'] == 0 for row in self.store.rows('SELECT intake FROM enrollments')))
            self.assertEqual(self.store.rows('SELECT * FROM processing_owner_operations'), [])
        self.assertGreaterEqual(record.snapshot()['totals']['schedule_input_mappings']['count'], 2)
        self.assertEqual(record.snapshot()['totals']['schedule_input_mappings']['failed'], 0)
        with observations.owning('service'):
            with self.assertRaises(ValueError):
                with observations.span('fictional-arbitrary-dynamic-label'):
                    self.fail('dynamic labels must remain refused')

    def serving_record(self):
        self.store.db.execute('INSERT INTO processing_runs VALUES(?,?,?,?)',
                              (self.store.controller, self.key, 'owned', self.now))
        self.store.db.execute('INSERT INTO service_runs VALUES(?,?,?,?,?,NULL,NULL)',
                              (self.store.controller, self.key, 'PRIVATE_SOCKET_CANARY', 'serving', self.now))

    def source_cli(self, source):
        output = io.StringIO()
        with patch.object(cli, 'load_config', return_value=self.config), patch.object(
                processing, 'ProcessingBoard', side_effect=lambda config, role: self.boards[role]), software.fixture_actor(
                self.boards['Work'].store, self.config['roles']['Work']['owner']), contextlib.redirect_stdout(output):
            code = cli.main(['--config', 'fictional-config', 'processing-source', self.key, source['id'], '--diagnostics'])
        return code, json.loads(output.getvalue())

    async def test_supported_exact_source_metadata_excludes_bodies_and_keeps_unknown_distinct(self):
        self.serving_record()
        source = self.post(text='PRIVATE_BODY_CANARY')
        classifier = await self.classified(source, '@unresolved')
        self.store.db.execute('UPDATE attempts SET session=?,turn=?,detail=? WHERE id=?',
                              ('PRIVATE_NATIVE_CANARY', 'PRIVATE_TURN_CANARY', encode({'capture': 'PRIVATE_CAPTURE_CANARY'}), classifier))
        before = {t: self.store.rows('SELECT * FROM ' + t) for t in
                  ('events', 'attempts', 'queue', 'input_lookups', 'input_resolutions', 'alert_debt', 'processing_runs')}
        code, view = self.source_cli(source)
        self.assertEqual(code, 0, view)
        self.assertEqual({t: self.store.rows('SELECT * FROM ' + t) for t in before}, before)
        self.assertEqual(view['classifier']['id'], classifier)
        self.assertEqual(view['classifier']['exit'], 0)
        self.assertEqual(view['responsibility']['task'], '@unresolved')
        self.assertFalse(view['processing_complete'])
        self.assertIsNone(view['mapping'])
        self.assertNotIn('PRIVATE_', encode(view))
        self.choice(source, 'work-proposer', 'b')
        await self.mapped(source)
        code, mapped = self.source_cli(source)
        self.assertEqual(code, 0, mapped)
        self.assertTrue(mapped['mapping']['resolution_present'])
        self.assertIsNone(mapped['classifier'])  # A fresh classification is still owed.
        self.assertEqual(mapped['classifier_scope'], 'awaiting-fresh-classification')
        self.assertFalse(mapped['processing_complete'])

    async def test_source_diagnostic_rejects_revocation_frontier_and_changed_source(self):
        self.serving_record()
        source = self.post()
        classifier = await self.classified(source, '@unresolved')
        self.store.db.execute('UPDATE attempts SET controller=? WHERE id=?', ('fictional-older-controller', classifier))
        code, view = self.source_cli(source)
        self.assertEqual(code, 0, view)
        self.assertIsNone(view['classifier'])
        self.assertNotIn('fictional-older-controller', encode(view))
        original = self.store.one('SELECT selection FROM processing_capabilities WHERE id=?', (self.key,))['selection']
        value = json.loads(original)
        value['basis']['event_boundary'] = processing.source_boundary(self.store)
        self.store.db.execute('UPDATE processing_capabilities SET selection=?', (encode(value),))
        self.assertEqual(self.source_cli(source)[0], 2)
        with patch.object(self.store, 'event', side_effect=AssertionError('old body must remain unread')):
            with self.assertRaises(Refusal):
                processing.source_diagnostics(self.store, self.boards, self.key, source['id'])
        self.store.db.execute('UPDATE processing_capabilities SET selection=?', (original,))
        with patch.object(processing, 'implementation', return_value={'fictional-source-changed': 'different'}):
            self.assertEqual(self.source_cli(source)[0], 2)
        self.store.db.execute('UPDATE processing_capabilities SET revoked=?', (self.now,))
        self.assertEqual(self.source_cli(source)[0], 2)


class ServiceDiagnostics(unittest.IsolatedAsyncioTestCase):
    async def test_supported_status_survives_reporting_failure_and_rejects_stale_authority(self):
        fixture = startup.Control()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        ready = asyncio.Event()
        owner = []
        # Make error persistence actually fail after the phase error is retained.
        async def owned_run(dispatcher, emit):
            owner.append(dispatcher)
            def operation(name):
                def call():
                    if name == 'schedule_input_mappings':
                        raise ValueError('PRIVATE_ERROR_CANARY')
                call.__name__ = name
                return call
            with contextlib.ExitStack() as patches:
                for name in ('receipts', 'reconcile_completed', 'intake', 'schedule_classifications',
                             'schedule_classification_recovery', 'schedule_input_mappings'):
                    patches.enter_context(patch.object(dispatcher, name, operation(name)))
                patches.enter_context(patch.object(dispatcher.store, 'record_operational_error',
                                                  side_effect=Backpressure('PRIVATE_ERROR_CANARY')))
                with self.assertRaises(Backpressure):
                    await dispatcher.tick()
            ready.set()
            await dispatcher.stopping.wait()
        fixture.store.record_operational_error('dispatcher-phase:schedule_input_mappings', {'error': 'PRIVATE_OBSOLETE_CANARY'})
        before = {t: fixture.store.rows('SELECT * FROM ' + t) for t in ('alerts', 'alert_debt', 'operational_errors')}
        with patch.object(service.Dispatcher, 'run', owned_run), patch.object(
                service.Dispatcher, 'recover_originals', return_value={'uncollected': []}):
            original = asyncio.create_task(service.serve(fixture.store, {'Work': fixture.board_type()}, fixture.key, lambda value: None, models=object()))
            await asyncio.wait_for(ready.wait(), 3)
            try:
                code, view = await asyncio.to_thread(fixture.invoke)
                self.assertEqual(code, 0, view)
                self.assertEqual(view['phase_errors']['schedule_input_mappings'], 'invalid-value')
                self.assertEqual(view['controller'], fixture.store.controller)
                self.assertNotIn('PRIVATE_', encode(view))
                self.assertFalse(view['processing_complete'])
                with owner[0].phase('schedule_input_mappings'):
                    pass
                self.assertEqual((await asyncio.to_thread(fixture.invoke))[1]['phase_errors'], {})
                for table, prior in before.items():
                    self.assertEqual(fixture.store.rows('SELECT * FROM ' + table), prior)
                with patch.object(processing, 'implementation', return_value={'fictional-changed': 'source'}):
                    # Server-side revalidation too, not only the CLI preflight.
                    answer = await service.control(fixture.store, fixture.key, 'status')
                    self.assertIn('error', answer)
                    self.assertNotIn('phase_errors', answer)
                fixture.store.db.execute('UPDATE processing_capabilities SET revoked=1')
                answer = await service.control(fixture.store, fixture.key, 'status')
                self.assertIn('error', answer)
                self.assertNotIn('phase_errors', answer)
            finally:
                owner[0].stopping.set()
                await asyncio.wait_for(original, 3)
