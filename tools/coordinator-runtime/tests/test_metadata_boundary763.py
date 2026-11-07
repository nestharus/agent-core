"""Original conditional business meaning survives a software metadata receipt.

All principals, Board records and model replies are synthetic. Run only in the
positive /fixtures mount. Prompt assertions qualify the input contract, never
provider semantic success. Actual production routing and guards run locally.
"""
import json
from unittest.mock import patch

from test_control_routing737 import NativeRoute
from test_cutover475 import Mixed
from coordinator_runtime import branches, local_integration as local, ordinary
from coordinator_runtime.contracts import Refusal, digest, encode
from coordinator_runtime.dispatcher import classifier_prompt
from coordinator_runtime.inputs import input_routes


class MetadataBoundary(NativeRoute):
    def fixture_config(self, cfg, area):
        # Keep the real native execution lookup, unlike NativeRoute's separate
        # general-control fixture. No native point is supplied by the model.
        cfg = Mixed.fixture_config(self, cfg, area)
        cfg['roles']['QA']['routes'].append('work-proposer')
        return cfg

    async def model(self, store, attempt, prompt, spec, schema):
        outcome = await super().model(store, attempt, prompt, spec, schema)
        row = store.attempt(attempt)
        if row['kind'] == 'input-mapping':
            receipt = json.loads(outcome['result']['decision_json'])
            receipt.update(reason='Read-only metadata interpretation only; no execution or acceptance selected.',
                evidence=['Existing native QA point; receiver and native incarnations remain distinct.'],
                remaining_obligations=['Independent Root association acceptance before effects; future job/attempt not created.'])
            outcome['result'].update(summary='Metadata interpretation DONE; downstream duties remain.',
                                     decision_json=encode(receipt))
        elif row['kind'] == 'classifier' and getattr(self, 'unresolved_business', False):
            outcome['result'].update(task='@unresolved', reason='Original business scope remains genuinely unknown.')
        return outcome

    async def mapped(self, text):
        event = self.post(text, role='QA', package=self.package)
        await self.classify(event, '@unresolved')
        self.dispatch.receipts()
        before = self.store.one('SELECT classifier,ack_receipt FROM events WHERE id=?', (event['id'],))
        birth = self.store.one('SELECT * FROM processing_source_positions WHERE event=?', (event['id'],))
        resolution = await self.mapping(event)
        self.assertEqual(resolution['receipt']['integration']['state'], 'known')
        self.assertEqual(resolution['receipt']['integration']['writes'], [])
        self.assertEqual(resolution['prior']['integration_observation']['unresolved'], [])
        self.assertEqual(self.store.one('SELECT classifier,ack_receipt FROM events WHERE id=?', (event['id'],)), before)
        self.assertEqual(self.store.one('SELECT * FROM processing_source_positions WHERE event=?', (event['id'],)), birth)
        self.assertEqual(self.store.event(event['id']), event)
        self.assertEqual(resolution['source_hash'], digest(event))
        self.assertIsNone(self.store.reserve(), 'metadata completion needs fresh classification')
        return event, resolution

    async def test_effective_original_and_receipt_have_distinct_meaning(self):
        text = 'Prepare the admitted QA work; execute only after independent association acceptance.'
        event, resolution = await self.mapped(text)
        effective = self.store.routing_event(event['id'])
        self.assertEqual(effective['body'], event['body'])
        self.assertEqual(input_routes(effective, self.config), ['qa-execution', '@unresolved'])
        prompt = classifier_prompt(effective, self.config)
        self.assertIn('\nINPUT_INTERPRETATION=', prompt)
        meaning = json.loads(prompt.split('\nINPUT_INTERPRETATION=', 1)[1].split('\nEVENT=', 1)[0])
        self.assertEqual(meaning['resolution_scope'], 'software-metadata-only')
        self.assertEqual(meaning['business_source'], 'EVENT original source fields')
        self.assertEqual(meaning['selected_task'], 'qa-execution')
        self.assertIn(text, prompt)
        self.assertIn(resolution['receipt']['reason'], prompt)
        key = resolution['receipt']['integration']['reads'][0]
        point = local.point_definitions(self.store)[key]
        self.assertEqual(point['bindings'], [{'native':'execution', 'package':self.package, 'task':'qa-execution'}])
        self.assertNotEqual(point['incarnation'], point['native_incarnations'][0])
        self.assertEqual(self.store.rows('SELECT * FROM jobs'), [])
        self.assertEqual(self.store.rows('SELECT * FROM ordinary_runs'), [])

    async def test_readonly_mapping_routes_preparation_but_cannot_accept_association(self):
        event, _ = await self.mapped('Prepare this exact admitted QA operation, conditional on independent Root acceptance.')
        await self.classify(event, 'qa-execution')
        with patch('coordinator_runtime.ordinary.adapter', side_effect=AssertionError('premature runner')) as adapter, \
                patch('coordinator_runtime.qa_source.export', side_effect=AssertionError('premature export')) as export:
            with self.assertRaisesRegex(Refusal, 'owner acceptance'):
                await self.phase('schedule_job')
        job = self.store.one('SELECT j.* FROM jobs j JOIN queue q ON q.job=j.id WHERE q.event=?', (event['id'],))
        self.assertIsNotNone(job, 'future job/attempt IDs are not metadata mapping prerequisites')
        self.assertEqual(job['state'], 'reserved')
        self.assertIsNone(job['active_attempt'], 'the attempted start transaction rolls back before any task launch')
        adapter.assert_not_called()
        export.assert_not_called()
        self.assertIsNone(branches.association(self.store, self.branch, active=False)['accepted'])
        self.assertEqual(self.store.rows('SELECT * FROM ordinary_acceptance'), [])
        self.assertEqual(self.store.rows('SELECT * FROM ordinary_runs'), [])
        self.assertEqual(self.store.event(event['id']), event)

    async def test_known_metadata_cannot_replay_an_unknown_effect_intent(self):
        event, _ = await self.mapped('Prepare the known admitted QA operation with all effect guards retained.')
        await self.classify(event, 'qa-execution')
        job = self.store.reserve()
        owner = self.config['roles']['Work']['owner']
        branches.accept(self.store, self.branch, owner, 'Synthetic independent association acceptance for effect guard fixture')
        attempt = self.store.start_job(job['id'], job['token'])
        job = self.store.job(job['id'])
        epoch = ordinary.selected(self.store, job)
        # An intentionally interrupted intent is owned fixture data, never an
        # inferred real effect. Production must refuse before adapter/export.
        self.store.db.execute('INSERT INTO ordinary_runs VALUES(?,?,?,?,?,?,?)',
            (attempt, job['id'], epoch['id'], 'synthetic-admission', '{}', 'intent', '{}'))
        with patch('coordinator_runtime.ordinary.adapter', side_effect=AssertionError('replayed runner')) as adapter, \
                patch('coordinator_runtime.qa_source.export', side_effect=AssertionError('replayed export')) as export:
            with self.assertRaisesRegex(Refusal, 'incomplete/unknown.*never replay'):
                await ordinary.perform(self.store, self.boards['QA'], job)
        adapter.assert_not_called()
        export.assert_not_called()
        self.assertEqual(self.store.one('SELECT state FROM ordinary_runs WHERE attempt=?', (attempt,))['state'], 'intent')
        self.assertEqual(self.store.job(job['id'])['effects'], 'unknown')
        self.assertEqual(self.store.rows('SELECT * FROM ordinary_acceptance'), [])
        self.assertEqual(self.store.event(event['id']), event)

    async def test_known_metadata_does_not_resolve_unknown_business_scope(self):
        event, _ = await self.mapped('Known package, but the requested business scope is unspecified.')
        self.unresolved_business = True
        await self.classify(event, '@unresolved')
        queue = self.store.one('SELECT task,state FROM queue WHERE event=?', (event['id'],))
        self.assertEqual(queue, {'task':'@unresolved', 'state':'awaiting-owner'})
        self.assertIsNone(self.store.reserve())
        self.assertEqual(self.store.rows('SELECT * FROM jobs'), [])
        self.assertEqual(self.store.event(event['id']), event)

    async def test_missing_current_admission_invalidates_mapping_before_classification(self):
        event, _ = await self.mapped('Prepare the exact admitted QA operation under current guards.')
        before = self.store.rows('SELECT id FROM attempts')
        self.store.db.execute('DELETE FROM admissions WHERE package=?', (self.package,))
        await self.phase('schedule_classifications')
        state = self.store.one('SELECT state,error FROM events WHERE id=?', (event['id'],))
        self.assertEqual(state['state'], 'mapping-held')
        self.assertIn('admission', state['error'])
        self.assertEqual(self.store.rows('SELECT id FROM attempts'), before)
        self.assertIsNone(self.store.reserve())
        self.assertEqual(self.store.rows('SELECT * FROM jobs'), [])
        self.assertEqual(self.store.event(event['id']), event)
