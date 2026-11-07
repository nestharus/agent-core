"""Owned fiction: real recovery/owner transitions and retirement revalidation.

No provider or actual journal is selected. Every fixture, including failures,
stays below QA629_FIXTURES. SQLite authorizers detect fresh body acquisition;
only original diagnosis collection is exempt, with statement caches invalidated.
"""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import re
import sqlite3
import unittest
from unittest.mock import AsyncMock, Mock, patch

from support import collect, config_at, enrolled, ended_job, event, queued, result
from coordinator_runtime import cleanup, dispatcher, local_integration as local
from coordinator_runtime.contracts import LUNA, Refusal, digest, encode, ident
from test_preparation_holds724 import Preparation
from test_retained_catalog717 import CatalogCase


class Recovery(CatalogCase, unittest.IsolatedAsyncioTestCase):
    bound_job = Preparation.bound_job
    hold = Preparation.hold

    def neighbor(self):
        # A distinct newly owned discovery-neighbor metadata fixture. Do not
        # repurpose the ancestor fixture's independently held Branch source.
        message = event(self.config, ident())
        # Only neighbor registration is a synthetic metadata seam; the selected
        # job, model admission, collection and owner transitions are real APIs.
        self.store.db.execute('INSERT INTO events(id,role,payload,hash,received) VALUES(?,?,?,?,?)',
            (message['id'], 'Work', encode(message), digest(message), self.store.clock()))
        queue = ident()
        self.store.db.execute('INSERT INTO queue(id,event,role,phase,task) VALUES(?,?,?,?,?)',
            (queue, message['id'], 'Work', 'integrator', 'work-integrator'))
        scope = local.scope_for(self.store, self.job)
        scope['neighbors'] = [dict(queue=queue, event=message['id'], package=None, hash=digest(message))]
        self.store.db.execute('UPDATE local_jobs SET scope=? WHERE job=?', (encode(scope), self.job['id']))
        return message['id']

    def failed(self, selected=False):
        self.bound_job()
        collect(self.store, self.attempt, result('FAILED'), code=1, error='fictional original failure')
        self.store.hold_job(self.job['id'], 'fictional original failure')
        self.store.reconcile_effects(self.job['id'], self.job['token'], self.config['roles']['Work']['owner'],
            dict(evidence=['Fictional original effects accounted for'], unknown_effects=[]))
        self.original = self.store.attempt(self.attempt)
        if selected:
            self.selection_request = self.request('remaining-work')
            self.store.consume_recovery_request(self.selection_request['id'])
            self.job = self.store.job(self.job['id'])
        else:
            self.job = self.store.claim_recovery(self.job['id'])
        self.assertEqual(self.job['recovery_state'], 'claimed')

    def request(self, mode, **extra):
        return self.store.request_recovery(self.job['id'], self.job['token'], self.attempt,
            self.config['roles']['Work']['owner'], dict(mode=mode,
                reason='Fictional actual owner chooses this exact retained duty',
                evidence=['Fictional original collected and effect duties reconciled'],
                remaining='Fictional bounded remainder and WHY' if mode == 'remaining-work' else None,
                **extra))

    @contextmanager
    def deny_new_context(self):
        self.read_violations = []
        # SQLite's READ callback names the underlying column even for a safe
        # JSON metadata projection. Admit only the existing scalar lineage
        # projection, with no remaining detail identifier or wildcard. This
        # finite test oracle is not a general SQL parser or host isolation.
        metadata_detail = False
        connection = self.store.db
        class ObservedConnection:
            def __getattr__(self, name):
                return getattr(connection, name)

            def execute(self, sql, values=()):
                nonlocal metadata_detail
                projected = re.sub(r"json_extract\(\s*(?:\w+\.)?detail\s*,\s*'\$\.prior_task_attempt'\s*\)",
                                   'lineage_metadata', sql, flags=re.I)
                remaining = re.sub(r'count\(\s*\*\s*\)', 'row_count', projected, flags=re.I)
                metadata_detail = (projected != sql and not re.search(r'\bdetail\b|\*', remaining, re.I))
                try:
                    return connection.execute(sql, values)
                finally:
                    metadata_detail = False

        def deny(action, table, column, database, caller):
            if action == sqlite3.SQLITE_READ and (
                    table == 'attempts' and column == 'result'
                    or table == 'attempts' and column == 'detail' and not metadata_detail
                    or table == 'events' and column == 'payload'
                    or table in {'results', 'source_custody', 'artifact_blobs'}):
                self.read_violations.append((table, column))
                return sqlite3.SQLITE_DENY
            return sqlite3.SQLITE_OK
        original_collect = self.store.collect
        def collection(*args):
            self.store.db.set_authorizer(None)
            try:
                return original_collect(*args)
            finally:
                self.store.db.set_authorizer(deny)
        self.store.db.set_authorizer(deny)
        try:
            with patch.object(self.store, 'db', ObservedConnection()), \
                 patch.object(self.store, 'collect', side_effect=collection), \
                 patch.object(self.store, 'retain_recovery_disposition',
                    side_effect=AssertionError('informative disposition after refused admission')), \
                 patch.object(dispatcher, 'template_text', side_effect=AssertionError('held template read')):
                yield
        finally:
            self.store.db.set_authorizer(None)

    def model(self, profile='@owner', hold=False):
        async def run(store, attempt, prompt, spec, schema):
            self.assertFalse(store.db.in_transaction)
            self.assertIn('prior_attempt', prompt)
            store.begin(attempt, {'fictional': True})
            if hold:
                self.hold(self.held_event)
                self.context_guard = self.deny_new_context()
                self.context_guard.__enter__()
            return dict(exit=0, capture='complete', cleanup='done',
                result=dict(profile=profile, remaining='Fictional owner remainder', rationale='Conserve duty'),
                detail=dict(binding_readback=LUNA, root_identity_observed=True))
        self.runtime.models = Mock(run=AsyncMock(side_effect=run))

    def pending(self, count=1):
        row = self.store.job(self.job['id'])
        self.assertEqual(row['recovery_state'], 'awaiting-disposition')
        self.assertEqual(row['recovery_count'], count)
        self.assertEqual(row['active_attempt'], self.attempt)
        self.assertEqual(row['controller'], self.original['controller'])
        self.assertEqual(row['recovery_owner'], self.store.controller)
        self.assertEqual(self.store.attempt(self.attempt), self.original)
        record = self.store.one("SELECT * FROM operational_errors WHERE subject=?",
            ('recovery-admission:'+self.job['id'],))
        self.assertIsNotNone(record)
        self.assertEqual(json.loads(record['detail'])['attempt'], self.attempt)
        self.assertEqual(self.store.rows('SELECT * FROM recovery_dispositions'), [])
        self.assertEqual(self.store.rows("SELECT * FROM outboxes WHERE kind='question'"), [])
        with self.deny_new_context():
            self.runtime.reconcile_collected(row)
        self.assertEqual(self.read_violations, [])

    async def test_hold_after_real_claim_before_allocation_then_explicit_owner_continuation(self):
        self.failed()
        neighbor = self.neighbor()
        self.hold(neighbor, '')
        self.runtime.models = Mock(run=AsyncMock(side_effect=AssertionError('held model')))
        with self.deny_new_context():
            await self.runtime.recover(self.job)
        self.assertEqual(self.read_violations, [])
        self.runtime.models.run.assert_not_called()
        self.assertEqual(self.store.rows("SELECT id FROM attempts WHERE kind='diagnosis'"), [])
        self.pending()
        self.hold(neighbor, None)
        with self.deny_new_context():
            self.runtime.reconcile_collected(self.store.job(self.job['id']))
        self.assertEqual(self.read_violations, [])
        self.assertIsNone(self.store.claim_recovery(self.job['id']))  # No refunded automatic credit.
        self.model()
        request = self.request('remaining-work')
        self.store.consume_recovery_request(request['id'])
        await self.runtime.recover(self.store.job(self.job['id']))
        self.runtime.models.run.assert_awaited_once()
        self.assertEqual(self.store.job(self.job['id'])['recovery_count'], 2)
        self.assertEqual(self.store.job(self.job['id'])['recovery_state'], 'awaiting-disposition')
        self.assertEqual(self.store.attempt(self.attempt), self.original)

    async def test_hold_after_allocation_prompt_refusal_collects_without_later_context(self):
        self.failed()
        allocate = self.store.diagnosis_attempt
        guard = None
        def allocation(*args):
            nonlocal guard
            value = allocate(*args)
            self.hold()
            guard = self.deny_new_context()
            guard.__enter__()
            return value
        self.runtime.models = Mock(run=AsyncMock(side_effect=AssertionError('held model')))
        try:
            with patch.object(self.store, 'diagnosis_attempt', side_effect=allocation):
                await self.runtime.recover(self.job)
        finally:
            if guard: guard.__exit__(None, None, None)
        self.assertEqual(self.read_violations, [])
        self.runtime.models.run.assert_not_called()
        diagnosis = self.store.one("SELECT * FROM attempts WHERE kind='diagnosis'")
        self.assertEqual(diagnosis['state'], 'not-started')
        self.assertIsNone(diagnosis['begin'])
        self.assertIsNone(diagnosis['ended'])
        self.assertIsNone(diagnosis['exit'])
        self.assertIsNotNone(diagnosis['collected'])
        self.pending()
        self.hold(reason=None)
        self.model()
        request = self.request('remaining-work')
        self.store.consume_recovery_request(request['id'])
        await self.runtime.recover(self.store.job(self.job['id']))
        self.runtime.models.run.assert_awaited_once()

    async def test_admitted_diagnosis_collection_then_held_result_and_explicit_reuse(self):
        self.failed(selected=True)
        self.held_event = self.neighbor()
        self.catalog.write_text(self.catalog.read_text().replace('original', 'changed'))
        self.model(profile='.codex3', hold=True)
        try:
            with patch.object(local, 'current_job', side_effect=AssertionError('point freshness on diagnosis')):
                await self.runtime.recover(self.job)
        finally:
            if hasattr(self, 'context_guard'): self.context_guard.__exit__(None, None, None)
        self.assertEqual(self.read_violations, [])
        self.runtime.models.run.assert_awaited_once()
        diagnosis = self.store.one("SELECT * FROM attempts WHERE kind='diagnosis'")
        self.assertEqual(diagnosis['state'], 'collected')
        self.assertEqual(diagnosis['exit'], 0)
        self.pending()
        with self.deny_new_context(), self.assertRaises(Refusal):
            self.request('use-diagnosis', diagnosis=diagnosis['id'], selection=self.selection_request['id'])
        self.assertEqual(self.read_violations, [])
        self.hold(self.held_event, None)
        # Point change did not cancel diagnosis, and no implicit successor was made.
        self.assertEqual(len(self.store.rows("SELECT id FROM attempts WHERE kind='task'")), 1)
        self.catalog.write_bytes(self.original_files[str(self.catalog)])
        request = self.request('use-diagnosis', diagnosis=diagnosis['id'], selection=self.selection_request['id'])
        consumed = self.store.consume_recovery_request(request['id'])
        self.assertIsNotNone(consumed['successor'])
        self.assertEqual(self.store.attempt(diagnosis['id']), diagnosis)
        self.assertEqual(self.store.attempt(self.attempt), self.original)
        self.assertEqual(self.store.job(self.job['id'])['recovery_count'], 1)

    async def test_unheld_real_recover_advances_to_owned_informative_disposition(self):
        self.failed()
        self.model()
        await self.runtime.recover(self.job)
        self.runtime.models.run.assert_awaited_once()
        self.assertEqual(self.store.job(self.job['id'])['recovery_state'], 'awaiting-disposition')
        self.assertEqual(len(self.store.rows('SELECT * FROM recovery_dispositions')), 1)
        self.assertTrue(self.store.one("SELECT id FROM outboxes WHERE kind='question'"))
        self.assertEqual(self.store.attempt(self.attempt), self.original)

    async def test_handoff_is_a_new_group_and_failed_admission_keeps_metadata_only(self):
        self.failed(selected=True)
        self.model(profile='.codex3')
        handoff = self.store.handoff
        guard = None
        def later_group(*args):
            nonlocal guard
            self.hold()
            guard = self.deny_new_context()
            guard.__enter__()
            return handoff(*args)
        try:
            with patch.object(self.store, 'handoff', side_effect=later_group):
                await self.runtime.recover(self.job)
        finally:
            if guard: guard.__exit__(None, None, None)
        self.assertEqual(self.read_violations, [])
        self.pending()
        self.assertEqual(len(self.store.rows("SELECT id FROM attempts WHERE kind='task'")), 1)

    async def test_model_refusal_after_admission_collects_without_fresh_context(self):
        self.failed()
        guard = None
        async def refused(store, attempt, prompt, spec, schema):
            nonlocal guard
            self.assertFalse(store.db.in_transaction)
            self.assertIn('prior_attempt', prompt)  # This group was admitted.
            self.hold()
            guard = self.deny_new_context()
            guard.__enter__()
            raise Refusal('fictional model refused before owned start')
        self.runtime.models = Mock(run=AsyncMock(side_effect=refused))
        try:
            await self.runtime.recover(self.job)
        finally:
            if guard: guard.__exit__(None, None, None)
        self.assertEqual(self.read_violations, [])
        diagnosis = self.store.one("SELECT * FROM attempts WHERE kind='diagnosis'")
        self.assertEqual(diagnosis['state'], 'not-started')
        self.assertIsNone(diagnosis['exit'])
        self.assertIsNotNone(diagnosis['collected'])
        self.pending()


class Retention(unittest.TestCase):
    def setUp(self):
        self.area = Path(os.environ['QA629_FIXTURES'])/self._testMethodName/ident()
        self.area.mkdir(parents=True)
        self.config = config_at(self.area)
        self.now = 100000.0
        self.store = enrolled(self.config, clock=lambda: self.now)
        self.addCleanup(self.store.close)

    def settled(self, name, parent=None):
        source = event(self.config, name)
        if parent: source['parent'] = parent
        queued(self.store, source)
        job = self.store.reserve()
        attempt = ended_job(self.store, job)
        self.store.complete_events()
        return source, attempt

    def artifact(self, attempt):
        path = self.store.home/'artifacts'/attempt/'owned.txt'
        path.parent.mkdir(parents=True)
        path.write_text('Fictional conserved producer output')
        cleanup.register_artifact(self.store, attempt, path)
        cleanup.conserve(self.store, path, self.config['roles']['Work']['owner'], {'conserved':'fictional consumer'})
        return path

    def source(self, source):
        return self.store.one('SELECT * FROM events WHERE id=?', (source['id'],))

    def test_empty_source_hold_and_before_retire_revalidation_then_clock_reset(self):
        source, attempt = self.settled('source')
        path = self.artifact(attempt)
        self.now += 86400
        candidate = self.source(source)
        artifact = self.store.one('SELECT * FROM artifacts WHERE path=?', (str(path),))
        self.assertTrue(cleanup.eligible_event(self.store, candidate))
        self.assertTrue(cleanup.artifact_eligible(self.store, artifact))
        self.store.set_hold(source['id'], '')
        self.assertFalse(cleanup.eligible_event(self.store, self.source(source)))
        self.assertFalse(cleanup.artifact_eligible(self.store, artifact))
        with patch.object(cleanup, 'unlink_exact', side_effect=AssertionError('held unlink')):
            self.assertEqual(cleanup.retire_artifact(self.store, artifact)['state'], 'held')
            self.assertIsNone(cleanup.retire_event(self.store, candidate))
        self.assertTrue(path.exists())
        self.store.set_hold(source['id'], None)
        self.assertEqual(self.source(source)['processed_at'], self.now)
        self.now += 86399
        self.assertFalse(cleanup.eligible_event(self.store, self.source(source)))
        self.now += 1
        self.assertTrue(cleanup.eligible_event(self.store, self.source(source)))
        self.assertTrue(cleanup.artifact_eligible(self.store, artifact))

    def test_empty_dependent_hold_blocks_parent_and_owned_artifact(self):
        parent, attempt = self.settled('parent')
        path = self.artifact(attempt)
        child, _ = self.settled('child', parent['id'])
        self.store.complete_events()
        self.now += 86400
        artifact = self.store.one('SELECT * FROM artifacts WHERE path=?', (str(path),))
        self.assertTrue(cleanup.eligible_event(self.store, self.source(parent)))
        self.store.set_hold(child['id'], '')
        self.assertTrue(self.store.dependency_hold(parent['id']))
        self.assertFalse(cleanup.eligible_event(self.store, self.source(parent)))
        self.assertFalse(cleanup.artifact_eligible(self.store, artifact))
        with patch.object(cleanup, 'unlink_exact', side_effect=AssertionError('held unlink')):
            self.assertEqual(cleanup.retire_artifact(self.store, artifact)['state'], 'held')
            self.assertIsNone(cleanup.retire_event(self.store, self.source(parent)))
        self.store.set_hold(child['id'], None)
        self.assertFalse(cleanup.eligible_event(self.store, self.source(parent)))
        self.now += 86400
        self.assertTrue(cleanup.eligible_event(self.store, self.source(parent)))


if __name__ == '__main__':
    unittest.main(verbosity=2)
