"""Conditional QA applicability and metadata-only failed-lookup regressions.

Use the retained /fixtures positive-mount envelope from test_cutover475.
Principals and model replies are fictional; production callers own collection.
"""
import copy
import json
from unittest.mock import patch

from test_control_routing737 import Routing
from test_cutover475 import Cutover, QueryProtocol
from coordinator_runtime import metadata_lookup as lookup
from coordinator_runtime.contracts import Refusal, digest


class QAApplicability(Routing):
    scoped = True

    def fixture_config(self, cfg, area):
        cfg = super().fixture_config(cfg, area)
        task = cfg['tasks']['qa-execution']
        if self.scoped:
            task.update(require_package_scope=True, scope_roots=[str(area)])
        scope = copy.deepcopy(self.file_scope)
        scope['query'] = True
        cfg['local_integration']['tasks']['qa-execution']['lookup_scopes'] = [scope]
        return cfg

    def selection_config(self, selection):
        super().selection_config(selection)
        selection['metadata_lookup']['tasks'].append('qa-execution')

    def admit(self):
        package = 'owned-admitted747'
        self.store.admit(package, self.config['roles']['Branch']['owner'], {'task_scopes': {
            'qa-execution': {'cwd': str(self.area), 'read_roots': [str(self.area)],
                'write_roots': [], 'procedure': self.config['tasks']['qa-execution']['templates'][0],
                'resource_evidence': ['Fictional independent package read authority']}}})
        return package

    async def test_null_QA_selected_local_metadata_reaches_control(self):
        event = self.post('Null-package QA control with a selected local QA task', role='QA')
        await self.classify(event, '@unresolved')
        with patch('coordinator_runtime.custody.read_file', side_effect=AssertionError('impossible QA metadata read')):
            for _ in range(2):
                await self.phase('schedule_classification_recovery')
                await self.phase('schedule_input_mappings')
        self.assertEqual(lookup.delegated_tasks(self.store, event), set())
        control = self.store.one('SELECT * FROM processing_controls WHERE event=?', (event['id'],))
        self.assertIsNotNone(control)
        self.assertIsNotNone(self.store.attempt(control['attempt'])['collected'])
        self.assertEqual([c['kind'] for c in self.calls].count('input-control'), 1)
        self.assertEqual(self.store.event(event['id']), event)
        for table in ('admissions', 'input_locators', 'input_lookups', 'input_resolutions', 'jobs'):
            self.assertEqual(self.store.rows('SELECT * FROM '+table), [])

    async def test_admitted_QA_selected_local_metadata_maps_then_reclassifies(self):
        event = self.post('Admitted QA one', role='QA', package=self.admit())
        await self.classify(event, '@unresolved')
        self.assertEqual(lookup.delegated_tasks(self.store, event), {'qa-execution'})
        await self.phase('schedule_classification_recovery')
        self.assertEqual(self.store.rows('SELECT * FROM processing_controls'), [])
        resolution = await self.mapping(event)
        self.assertEqual(resolution['receipt']['task'], 'qa-execution')
        self.assertEqual(resolution['receipt']['package'], event['package'])
        self.assertEqual(resolution['receipt']['integration']['state'], 'known')
        for table, field in [('input_locators', 'request'), ('input_lookups', 'snapshot')]:
            self.assertEqual(set(json.loads(self.store.one('SELECT '+field+' FROM '+table)[field])), {'qa-execution'})
        self.assertIsNone(self.store.reserve(), 'mapping never substitutes for fresh classification')
        await self.classify(event, 'qa-execution')
        self.assertEqual(self.store.reserve()['task'], 'qa-execution')
        self.assertEqual(self.store.event(event['id']), event)

    async def test_concrete_QA_control_keeps_its_consumer(self):
        event = self.post('Explicit admitted QA control', role='QA', package=self.admit())
        await self.classify(event, '@control')
        await self.phase('schedule_input_mappings')
        await self.phase('schedule_classification_recovery')
        self.assertIsNotNone(self.store.one('SELECT * FROM processing_controls WHERE event=?', (event['id'],)))
        self.assertEqual(self.store.rows('SELECT * FROM input_locators'), [])
        self.assertEqual(self.store.rows('SELECT * FROM input_lookups'), [])


class UnscopedQA(QAApplicability):
    scoped = False


class Dependencies(Cutover):
    async def test_revoked_execute_records_metadata_without_source_reacquisition(self):
        event = self.post()
        await self.classify(event, 'work-integrator')
        claimed = lookup.claim(self.store)
        self.assertIsNotNone(claimed)
        starts = self.store.one('SELECT starts FROM processing_capabilities WHERE id=?', (self.key,))
        self.store.db.execute('UPDATE processing_capabilities SET revoked=? WHERE id=?', (self.now, self.key))
        with self.assertRaises(Refusal):
            self.store.processing.current()
        with patch.object(self.store, 'event', side_effect=AssertionError('revoked source acquired')) as acquired:
            await lookup.execute(self.dispatch, *claimed)
        acquired.assert_not_called()
        row = self.store.attempt(claimed[1])
        self.assertEqual(row['state'], 'not-started')
        for field in ('begin', 'ended', 'exit', 'session'):
            self.assertIsNone(row[field])
        self.assertIsNotNone(row['collected'])
        self.assertEqual(starts, self.store.one('SELECT starts FROM processing_capabilities WHERE id=?', (self.key,)))
        self.assertFalse(any(c['attempt'] == claimed[1] for c in self.calls))
        self.assert_dependency(event, claimed[1])

    def assert_dependency(self, event, attempt):
        dependency = self.store.one('SELECT * FROM input_dependencies WHERE event=?', (event['id'],))
        self.assertEqual(dependency['source_hash'], digest(event))
        self.assertEqual(dependency['capability'], self.key)
        self.assertEqual(json.loads(dependency['detail'])['attempt'], attempt)
        self.assertEqual(self.store.one('SELECT role,active FROM operational_errors WHERE subject=?', (event['id'],)),
                         {'role': event['role'], 'active': 1})
        self.assertIsNone(self.store.input_resolution(event['id']))
        self.assertEqual(self.store.rows('SELECT * FROM jobs'), [])

    async def refused_after_model(self, condition):
        event = self.post()
        await self.classify(event, 'work-integrator')
        claimed = lookup.claim(self.store)
        self.assertIsNotNone(claimed)
        original_model = self.dispatch.models.run

        async def partial(*args):
            outcome = await original_model(*args)
            outcome['result']['semantic'] = 'PARTIAL'
            if condition == 'held':
                self.store.set_hold(event['id'], 'Owned fixture source hold after model await')
            elif condition == 'revoked':
                self.store.db.execute('UPDATE processing_capabilities SET revoked=? WHERE id=?', (self.now, self.key))
            return outcome

        original_event = self.store.event
        def source(key):
            if condition != 'unheld' and (self.store.one('SELECT hold IS NOT NULL AS held FROM events WHERE id=?', (key,))['held']
                    or self.store.one('SELECT revoked FROM processing_capabilities WHERE id=?', (self.key,))['revoked'] is not None):
                raise AssertionError('held/revoked source reacquisition after await')
            return original_event(key)

        with patch.object(self.dispatch.models, 'run', side_effect=partial), \
                patch.object(self.store, 'event', side_effect=source) as acquired:
            await lookup.execute(self.dispatch, *claimed)
        self.assertTrue(acquired.called, 'the unheld original must first reach its model prompt')
        self.assert_dependency(event, claimed[1])
        row = self.store.attempt(claimed[1])
        self.assertIsNotNone(row['collected'])
        self.assertEqual(row['exit'], 0, 'fictional completed model, not a no-start original')
        table = 'input_locators' if row['kind'] == 'input-locator' else 'input_lookups'
        self.assertTrue(self.store.one('SELECT error FROM '+table+' WHERE event=?', (event['id'],))['error'])

    async def test_held_after_await_failure_records_without_source_read(self):
        await self.refused_after_model('held')

    async def test_revoked_after_await_failure_records_without_source_read(self):
        await self.refused_after_model('revoked')

    async def test_unheld_partial_still_records_truthful_dependency(self):
        await self.refused_after_model('unheld')


class LocatorDependencies(Dependencies, QueryProtocol):
    pass
