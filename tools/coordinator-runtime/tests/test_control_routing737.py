"""Owned Board/dispatcher regressions for cross-role metadata delegation.

Run in a positive-mount namespace with retained /fixtures. Authentication and
typed model answers are synthetic; routing, collection and native guards run
production code. No actual Root, provider, runtime or acceptance is acquired.
"""
import copy
import json
from unittest.mock import patch

from test_cutover475 import Cutover, Mixed, QueryProtocol
from test_software_consumption import fixture_actor
from coordinator_runtime import branches, metadata_lookup as lookup, processing, prospective
from coordinator_runtime.contracts import Refusal, digest, encode, ident


class ControlAnswers:
    async def model(self, store, attempt, prompt, spec, schema):
        row = store.attempt(attempt)
        if row['kind'] != 'input-control':
            return await super().model(store, attempt, prompt, spec, schema)
        self.calls.append(dict(attempt=attempt, kind=row['kind'], event=row['event'], prompt=prompt))
        store.begin(attempt, {'fictional737_typed_control': True})
        store.session(attempt, ident())
        receipt = self.control_receipts.get(row['event'])
        return dict(exit=0, capture='complete', cleanup='fictional-no-child', error=None,
            result=dict(semantic='DONE' if receipt else 'PARTIAL',
                summary='Fictional source interpretation; native acceptance remains separate',
                decision_json=encode(receipt)),
            detail={'tool_completion': {'complete': True, 'items': [], 'nonzero_completions': []}})

    def route(self, event, task):
        self.control_receipts[event['id']] = dict(source_hash=digest(event), mode='route', task=task,
            package=event['package'], related_event=None, related_job=None,
            reason='Fictional original QA request selects its admitted execution task',
            evidence=['Exact owned Board source '+event['id']],
            remaining_obligations=['Actual assigned Root acceptance and QA execution remain owed'])


class Routing(ControlAnswers, QueryProtocol):
    def fixture_config(self, cfg, area):
        cfg = super().fixture_config(cfg, area)
        # Freeze cross-role eligibility through configuration and the actual
        # Board, rather than editing an already ingested source envelope.
        for role in ('QA', 'Branch', 'Reviews'):
            cfg['roles'][role]['routes'].append('work-proposer')
        # Genuine local consumers for the other roles. Work coordination is
        # independently selected by the parent fixture.
        for task in ('branch-proposer', 'reviews-integrator'):
            scope = copy.deepcopy(self.file_scope)
            scope['query'] = True
            cfg['local_integration']['tasks'][task]['lookup_scopes'] = [scope]
        return cfg

    def selection_config(self, selection):
        selection['metadata_lookup']['tasks'] = [
            'work-proposer', 'work-integrator', 'branch-proposer', 'reviews-integrator']

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.control_receipts = {}

    async def test_QA_unresolved_crossrole_Work_uses_control_and_preserves_original(self):
        event = self.post('QA control awaiting actual authority', role='QA')
        self.assertIn('work-proposer', event['allowed_tasks'])
        self.assertIn('qa-execution', event['allowed_tasks'])
        original = copy.deepcopy(event)
        await self.classify(event, '@unresolved')
        self.dispatch.receipts()
        before = self.store.one('SELECT classifier,ack_receipt FROM events WHERE id=?', (event['id'],))
        birth = self.store.one('SELECT * FROM processing_source_positions WHERE event=?', (event['id'],))
        with patch('coordinator_runtime.custody.read_file', side_effect=AssertionError('unrelated metadata read')):
            await self.phase('schedule_input_mappings')
            await self.phase('schedule_classification_recovery')
        control = self.store.one('SELECT * FROM processing_controls WHERE event=?', (event['id'],))
        self.assertIsNotNone(control, 'unresolved QA must reach the existing control worker')
        self.assertIsNone(control['resolution'], 'PARTIAL preserves actual unresolved authority')
        self.assertIsNotNone(control['error'])
        attempt = self.store.attempt(control['attempt'])
        self.assertEqual(attempt['exit'], 0)
        self.assertIsNotNone(attempt['collected'])
        self.assertEqual(self.store.one('SELECT task,state FROM queue WHERE event=?', (event['id'],)),
                         {'task': '@unresolved', 'state': 'awaiting-owner'})
        for _ in range(2):
            await self.phase('schedule_classification_recovery')
            await self.phase('schedule_input_mappings')
        self.assertEqual([c['kind'] for c in self.calls].count('input-control'), 1)
        self.assertEqual(self.store.event(event['id']), original)
        self.assertEqual(self.store.one('SELECT classifier,ack_receipt FROM events WHERE id=?', (event['id'],)), before)
        self.assertEqual(self.store.one('SELECT * FROM processing_source_positions WHERE event=?', (event['id'],)), birth)
        for table in ('input_lookups', 'input_locators', 'input_resolutions', 'jobs', 'ordinary_runs'):
            self.assertEqual(self.store.rows('SELECT * FROM '+table), [])

    async def test_same_role_unresolved_Work_locator_maps_and_reclassifies_to_real_job(self):
        event = self.post('Existing one; same-role metadata interpretation')
        await self.classify(event, '@unresolved')
        await self.phase('schedule_classification_recovery')
        self.assertEqual(self.store.rows('SELECT * FROM processing_controls'), [])
        resolution = await self.mapping(event)
        self.assertEqual(resolution['receipt']['task'], 'work-integrator')
        self.assertEqual(resolution['receipt']['integration']['state'], 'known')
        self.assertTrue(resolution['receipt']['integration']['reads'])
        locator = self.store.one('SELECT request,hints FROM input_locators WHERE event=?', (event['id'],))
        self.assertEqual(set(json.loads(locator['request'])), {'work-proposer', 'work-integrator'})
        self.assertTrue(locator['hints'])
        self.assertIsNone(self.store.reserve(), 'resolution still needs a fresh LOW classification')
        await self.classify(event, 'work-integrator')
        job = self.store.reserve()
        self.assertIsNotNone(job)
        self.assertEqual(job['task'], 'work-integrator')
        self.assertEqual(self.store.rows('SELECT * FROM local_discovered_points'), [])

    async def test_Branch_and_Reviews_unresolved_lookup_only_same_role_then_positive_job(self):
        for role, task in [('Branch', 'branch-proposer'), ('Reviews', 'reviews-integrator')]:
            event = self.post('Existing one for '+role, role=role)
            self.assertIn('work-proposer', event['allowed_tasks'])
            await self.classify(event, '@unresolved')
            await self.phase('schedule_classification_recovery')
            resolution = await self.mapping(event)
            self.assertEqual(resolution['receipt']['task'], task)
            for table, field in [('input_locators', 'request'), ('input_lookups', 'snapshot')]:
                record = self.store.one('SELECT '+field+' FROM '+table+' WHERE event=?', (event['id'],))
                self.assertEqual(set(json.loads(record[field])), {task})
            await self.classify(event, task)
            job = self.store.reserve()
            self.assertIsNotNone(job)
            self.assertEqual(job['role'], role)
        self.assertEqual(self.store.rows('SELECT * FROM processing_controls'), [])

    async def test_guard_rejects_crossrole_even_when_same_role_delegation_exists(self):
        event = self.post('Branch existing one', role='Branch')
        await self.classify(event, '@unresolved')
        with patch('coordinator_runtime.custody.read_file', side_effect=AssertionError('cross-role acquisition')):
            with self.assertRaises(Refusal):
                lookup.observe(self.store, event, 'work-proposer', None, self.selection['metadata_lookup'])
            changed = {**event, 'body': 'Forged source text grants no material authority'}
            with self.assertRaises(Refusal):
                lookup.observe(self.store, changed, 'branch-proposer', None, self.selection['metadata_lookup'])
        await self.mapping(event)
        self.assertEqual(self.store.input_resolution(event['id'])['receipt']['task'], 'branch-proposer')

    async def test_missing_local_consumer_does_not_suppress_QA_control(self):
        event = self.post('QA unresolved', role='QA')
        await self.classify(event, '@unresolved')
        # Explicit adversarial membership seam, not a valid selection rewrite:
        # the named delegated QA task has ceased being a local consumer.
        selection = copy.deepcopy(self.selection)
        selection['metadata_lookup']['tasks'].append('qa-execution')
        selected = self.store.processing.current()[0]
        original = self.store.config['local_integration']['tasks']
        with patch.object(self.store.processing, 'current', return_value=(selected, selection)), \
                patch.dict(self.store.config['local_integration'], tasks={k:v for k,v in original.items() if k != 'qa-execution'}):
            await self.phase('schedule_classification_recovery')
            await self.phase('schedule_input_mappings')
        self.assertIsNotNone(self.store.one('SELECT * FROM processing_controls WHERE event=?', (event['id'],)))
        self.assertEqual(self.store.rows('SELECT * FROM input_locators'), [])

    async def test_hold_and_revoked_current_capability_prevent_both_workers(self):
        events = []
        for role in ('QA', 'Work'):
            event = self.post('Held '+role, role=role)
            await self.classify(event, '@unresolved')
            self.store.set_hold(event['id'], 'owned fictional privacy hold')
            events.append(event)
        work = events[1]
        before = self.store.rows('SELECT id FROM attempts')
        with patch.object(self.store, 'event', side_effect=AssertionError('held body acquired')):
            await self.phase('schedule_classification_recovery')
            await self.phase('schedule_input_mappings')
        self.assertEqual(self.store.rows('SELECT id FROM attempts'), before)
        self.store.set_hold(work['id'], None)
        self.store.db.execute('UPDATE processing_capabilities SET revoked=? WHERE id=?', (self.now, self.key))
        for phase in ('schedule_classification_recovery', 'schedule_input_mappings'):
            with self.assertRaises(Refusal):
                await self.phase(phase)
        self.assertEqual(self.store.rows('SELECT id FROM attempts'), before)

    async def test_selected_retained_Work_uses_control_without_renewing_metadata_birth(self):
        event = self.post('Retained owned Work control')
        await self.classify(event, '@unresolved')
        birth = self.store.one('SELECT * FROM processing_source_positions WHERE event=?', (event['id'],))
        with fixture_actor(self.boards['Work'].store, self.config['roles']['Work']['owner']):
            processing.revoke(self.store, self.boards, self.key)
            selection = copy.deepcopy(self.selection)
            selection.update(basis=processing.basis(self.store, self.boards), retained_events=[event['id']])
            key = processing.select(self.store, self.boards, selection)['capability']
        self.store.processing = processing.Access(self.store, key, self.boards)
        await self.phase('schedule_input_mappings')
        await self.phase('schedule_classification_recovery')
        self.assertIsNotNone(self.store.one('SELECT * FROM processing_controls WHERE event=?', (event['id'],)))
        self.assertEqual(self.store.rows('SELECT * FROM input_locators'), [])
        self.assertEqual(self.store.one('SELECT * FROM processing_source_positions WHERE event=?', (event['id'],)), birth)
        self.assertEqual(self.store.event(event['id']), event)


class CrossRoleOnly(Routing):
    def selection_config(self, selection):
        selection['metadata_lookup']['tasks'] = ['work-proposer', 'work-integrator']

    async def test_other_roles_without_local_delegation_keep_original_controls(self):
        for role in ('Branch', 'Reviews'):
            event = self.post('Original '+role+' control', role=role)
            self.assertIn('work-proposer', event['allowed_tasks'])
            await self.classify(event, '@unresolved')
            await self.phase('schedule_input_mappings')
            await self.phase('schedule_classification_recovery')
            self.assertIsNotNone(self.store.one('SELECT * FROM processing_controls WHERE event=?', (event['id'],)))
            self.assertEqual(self.store.event(event['id']), event)
        self.assertEqual(self.store.rows('SELECT * FROM input_locators'), [])
        self.assertEqual(self.store.rows('SELECT * FROM input_lookups'), [])
        self.assertEqual(self.store.rows('SELECT * FROM jobs'), [])


class NativeRoute(ControlAnswers, Mixed):
    def fixture_config(self, cfg, area):
        cfg = super().fixture_config(cfg, area)
        cfg['roles']['QA']['routes'].append('work-proposer')
        # Exercise the ordinary QA consumer, with metadata delegated only to
        # other roles. No owner map or QA metadata permission is fabricated.
        del cfg['local_integration']['tasks']['qa-execution']
        return cfg

    async def asyncSetUp(self):
        await Cutover.asyncSetUp(self)
        self.control_receipts = {}
        self.branch = 'owned-assigned-unaccepted737'
        self.package = 'qa737-original'
        owner = self.config['roles']['Work']['owner']
        scopes = copy.deepcopy(self.qa_task_scopes)
        scopes['qa-execution']['branch_binding'] = self.branch
        self.store.admit(self.package, self.config['roles']['Branch']['owner'], {'task_scopes': scopes})
        branches.register(self.store, owner, dict(id=self.branch, repository=str(self.repo),
            origin='https://example.invalid/fictional475.git', ref='refs/heads/destination',
            incarnation='owned-unaccepted737', scope=self.package, root=owner,
            authority='Owned fictional branch assigned; actual accepting Root remains separate'))
        prospective.select(self.store, owner, dict(configuration=digest(self.config),
            authority='Fictional separate ordinary QA authorization', processing_capability=self.key,
            expires=self.now+100, grants={'QA': self.store.enrollment('QA')['grant_id']},
            tasks={'qa-execution': {'task_hash': digest(self.config['tasks']['qa-execution']),
                                   'software_handoffs': {}, 'ordinary_effects': True}}))

    async def test_original_QA_control_route_keeps_native_acceptance_and_runner_gate(self):
        event = self.post('Execute the exact admitted QA source', role='QA', package=self.package)
        original = copy.deepcopy(event)
        await self.classify(event, '@unresolved')
        first = self.store.one('SELECT classifier FROM events WHERE id=?', (event['id'],))['classifier']
        self.route(event, 'qa-execution')
        await self.phase('schedule_input_mappings')
        await self.phase('schedule_classification_recovery')
        resolution = self.store.input_resolution(event['id'])
        self.assertIsNotNone(resolution)
        self.assertEqual(resolution['receipt']['task'], 'qa-execution')
        self.assertFalse(resolution['prior']['software_processing']['native_owner_receipt'])
        self.assertIsNone(self.store.reserve())
        await self.classify(event, 'qa-execution')
        self.assertNotEqual(first, self.store.one('SELECT classifier FROM events WHERE id=?', (event['id'],))['classifier'])
        with patch('coordinator_runtime.ordinary.adapter', side_effect=AssertionError('runner before branch acceptance')) as adapter, \
                patch('coordinator_runtime.qa_source.export', side_effect=AssertionError('source export before acceptance')) as export:
            await self.phase('schedule_job')
        job = self.store.one('SELECT j.* FROM jobs j JOIN queue q ON q.job=j.id WHERE q.event=?', (event['id'],))
        self.assertIsNotNone(job)
        self.assertEqual(job['state'], 'held')
        self.assertIn('acceptance', job['hold_reason'])
        adapter.assert_not_called()
        export.assert_not_called()
        self.assertFalse((self.area/'qa-output/marker').exists())
        self.assertIsNone(branches.association(self.store, self.branch, active=False)['accepted'])
        self.assertEqual(self.store.rows('SELECT * FROM ordinary_acceptance'), [])
        self.assertEqual(self.store.rows('SELECT * FROM input_lookups'), [])
        self.assertEqual(self.store.rows('SELECT * FROM input_locators'), [])
        self.assertEqual(self.store.event(event['id']), original)
