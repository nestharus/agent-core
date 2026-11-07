"""Combined released contracts on owned fixture boards, never live stores.

Reuses released producer fixtures and deterministic collection helpers; this is
integration evidence, not independent QA or a native/provider qualification.
"""
import asyncio
import copy
import json
import unittest
from unittest.mock import patch

import test_qa629_repairs as qa
import test_report_batches50109 as reports
import test_selected_basis50115 as selected
from coordinator_runtime import processing, service, service_wake
from coordinator_runtime.contracts import Refusal, digest


def wake_policy(runtime, selection):
    until = runtime.clock() + 300
    selection['service']['admission'] = dict(until=until, pause_bytes=90000000, max_new_inputs=100)
    selection['service']['wake'] = dict(protocol='managed-hint-v1', roles=list(runtime.config['roles']), until=until)
    return selection


class WokenReports(qa.Fixture, unittest.IsolatedAsyncioTestCase):
    configure = reports.ReportBatches.configure
    admit = reports.ReportBatches.admit
    complete = reports.ReportBatches.complete

    def setUp(self):
        original = processing.select
        def choose(runtime, boards, selection):
            return original(runtime, boards, wake_policy(runtime, selection))
        with patch.object(processing, 'select', side_effect=choose):
            reports.ReportBatches.setUp(self)

    async def asyncSetUp(self):
        self.runtime = service.Dispatcher(self.store, self.boards, models=object())
        self.bridge = service_wake.ServiceWake(self.store, self.boards, self.runtime)
        self.runtime.wake = self.bridge
        self.bridge.start()

    async def asyncTearDown(self):
        self.bridge.close()

    async def test_large_partition_survives_board_hint_and_preserves_attribution(self):
        ids = self.admit(self.reports)
        fresh = self.post('Work', 'work-proposer', None)
        await asyncio.sleep(.01)
        self.assertGreater(self.bridge.hints, 0)
        self.assertTrue(self.runtime.wakeup.is_set())
        self.runtime.intake()
        finished = []
        for _ in ids:
            job = self.store.reserve()
            self.assertEqual([m['event'] for m in json.loads(job['members'])], [ids[len(finished)]])
            finished += self.complete(job)
        self.assertEqual(finished, ids)
        for event, original in zip(ids, self.reports):
            self.assertEqual(self.store.event(event)['body']['original'], original)
        classifiers = self.store.rows("SELECT event,COUNT(*) AS n FROM attempts WHERE kind='classifier' GROUP BY event")
        self.assertEqual({r['event']: r['n'] for r in classifiers}, {e: 1 for e in [*ids, fresh['id']]})
        self.assertIsNone(self.store.one('SELECT processed_at FROM events WHERE id=?', (fresh['id'],))['processed_at'])
        self.assertEqual(self.store.enrollment('Reviews')['legacy_hold'], 'Reviews UNKNOWN')

    async def test_hint_does_not_qualify_distinct_invalid_report_neighbor(self):
        bad = copy.deepcopy(self.reports[1])
        bad['history'] = 'Unselected distinct whole report'
        ids = self.admit([self.reports[0], bad])
        self.post('Work', 'work-proposer', None)
        await asyncio.sleep(.01)
        self.runtime.intake()
        job = self.store.reserve()
        self.assertEqual(self.complete(job), [ids[0]])
        self.assertEqual(self.store.one('SELECT state,job FROM queue WHERE event=?', (ids[1],)),
                         dict(state='queued', job=None))
        self.assertEqual(self.store.event(ids[1])['body']['original'], bad)


class SelectedWake(qa.Fixture, unittest.IsolatedAsyncioTestCase):
    configure = selected.CurrentConfigurationSelected.configure
    setUp = selected.CurrentConfigurationSelected.setUp
    route_receipt = selected.LocalSelectedBasis.route_receipt
    basis = selected.SelectedBasis.basis
    issue = selected.SelectedBasis.issue
    sentinel = selected.SelectedBasis.sentinel

    def selection(self, basis=None):
        return wake_policy(self.store, selected.CurrentConfigurationSelected.selection(self, basis))

    async def test_selected_metadata_and_wake_preserve_mapping_birth_and_other_hold(self):
        with self.sentinel():
            basis = self.basis()
            key = self.issue(self.selection(basis))
        self.store.processing = processing.Access(self.store, key, self.boards)
        self.runtime = service.Dispatcher(self.store, self.boards, models=object())
        bridge = service_wake.ServiceWake(self.store, self.boards, self.runtime)
        self.runtime.wake = bridge
        try:
            bridge.start()
            bridge.check()
            self.assertTrue(self.store.processing.event(self.source))
            self.assertFalse(self.store.processing.event(self.other))
            with self.assertRaisesRegex(Refusal, 'mapping policy/admission/grant/capability changed'):
                self.store.reserve()
            with qa.actor(self.boards['Work'].store, self.issuer):
                mapping = processing.map_input(self.store, self.boards, key, self.source['id'], self.issuer, self.route_receipt())
            self.classify(task='work-integrator')
            job = self.store.reserve()
            self.assertEqual(json.loads(job['members'])[0]['event'], self.source['id'])
            self.assertEqual(mapping['version'], self.mapping['version'] + 1)
            self.assertEqual(self.store.event(self.source['id']), self.source)
            self.assertEqual(basis['selected_retained'][0]['source_birth'], self.expected['source_birth'])
            self.assertIsNotNone(self.store.one('SELECT hold FROM events WHERE id=?', (self.other['id'],))['hold'])
            self.assertEqual(len(self.config['tasks']), 8)
            self.assertEqual(set(self.boards), {'Work', 'Branch', 'Reviews', 'QA'})
        finally:
            bridge.close()

    async def test_revocation_is_typed_intake_failure_without_erasing_other_diagnostics(self):
        with self.sentinel():
            key = self.issue(self.selection())
        self.store.processing = processing.Access(self.store, key, self.boards)
        dispatcher = service.Dispatcher(self.store, self.boards, models=object())
        bridge = service_wake.ServiceWake(self.store, self.boards, dispatcher)
        dispatcher.wake = bridge
        try:
            bridge.start()
            with self.assertRaises(OSError), dispatcher.phase('delivery'):
                raise OSError('Fictional independent delivery uncertainty')
            with qa.actor(self.boards['Work'].store, self.issuer):
                processing.revoke(self.store, self.boards, key)
            with self.assertRaises(Refusal), dispatcher.phase('intake'):
                dispatcher.intake()
            self.assertEqual(bridge.state, 'authority-held')
            self.assertEqual(set(dispatcher.phase_errors), {'delivery', 'intake'})
            self.assertEqual(dispatcher.phase_errors['intake'], 'authority-held')
            self.assertEqual(dispatcher.phase_errors['delivery'], 'io-error')
            self.assertEqual(self.store.rows('SELECT id FROM jobs'), [])
            self.assertEqual(self.store.event(self.source['id']), self.source)
        finally:
            bridge.close()


class StableSevenDuties(selected.SevenDuties):
    """Select startup exclusions before pinning; never mutate a pinned config.

    The released legacy test inserts these lexical paths after source selection.
    Keeping the intended paths constant preserves production currentness checks.
    These nonexistent fixture paths are never inspected or created.
    """
    def configure(self):
        super().configure()
        self.task['templates'] = ['/not-mounted/AGENTS.md', '/not-mounted/WORK_LOG.md']
