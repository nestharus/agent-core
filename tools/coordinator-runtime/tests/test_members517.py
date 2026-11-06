"""Producer517: fresh fictional SDK/software calls; run in positive-mount bwrap."""
import copy
import json
from pathlib import Path
from unittest.mock import patch

from coordinator_runtime import metadata_lookup as lookup, processing
from coordinator_runtime.contracts import Refusal, digest, encode
from test_cutover475 import QueryProtocol
from test_mapping504 import MappingTelemetry


class Members(QueryProtocol):
    serving_record = MappingTelemetry.serving_record
    source_cli = MappingTelemetry.source_cli

    def fixture_config(self, cfg, area):
        cfg = super().fixture_config(cfg, area)
        from support import fixture_publication
        cfg['canonical_publication'] = fixture_publication()
        # Identity, scalar view and whole-member comparison remain distinct
        # exact templates. No existing point or native method is replaced.
        for task in ['work-proposer', 'work-integrator']:
            scope = cfg['local_integration']['tasks'][task]['lookup_scopes'][0]
            scopes = []
            for label, view in [('identity', ['id']), ('state', ['state']), ('comparison', [])]:
                value = copy.deepcopy(scope)
                value.update(prefix='fictional:'+label+':', view=view)
                scopes.append(value)
            cfg['local_integration']['tasks'][task]['lookup_scopes'] = scopes
        return cfg

    def catalog_rows(self, rows):
        catalog = json.loads(self.catalog.read_text())
        catalog['assignments'] = rows
        self.catalog.write_text(encode(catalog))

    def snapshot(self, e):
        return json.loads(self.store.one('SELECT snapshot FROM input_lookups WHERE event=?',
                                        (e['id'],))['snapshot'])['work-proposer']

    def questions(self, e):
        return self.store.rows("SELECT * FROM outboxes WHERE event=? AND kind='question'", (e['id'],))

    async def test_unique_raw_member_ignores_unrelated_bad_identities(self):
        self.catalog_rows([{'id':'one','state':'old','owner':'owner-one'},
                           {'id':'duplicate'}, {'id':'duplicate'}, {'note':'not a member'}, 17])
        e = self.post('Existing one; no new work authority')
        await self.classify(e, 'work-proposer')
        await self.mapping(e)
        snap = self.snapshot(e)
        self.assertEqual(len(snap['points']), 3)
        self.assertEqual(snap['unresolved'], [])
        for point in snap['points'].values():
            selector = point['definition']['bindings'][0]['path'][1]
            self.assertEqual(selector, {'field':'id', 'value':'one'})
        await self.classify(e, 'work-proposer')
        job = self.store.reserve()
        self.assertIsNotNone(job)
        self.assertEqual(job['task'], 'work-proposer')
        self.assertEqual(self.store.rows('SELECT * FROM local_discovered_points'), [])
        self.assertEqual(self.questions(e), [])

    async def test_known_progress_preserves_decorated_and_absent_relationships(self):
        e = self.post('Existing one; related unknown-alias; decorated name is not a member')
        self.hints[e['id']] = ['one', 'unknown-alias', 'fictional:state:one']
        await self.classify(e, 'work-proposer')
        original = self.store.event(e['id'])
        await self.mapping(e)
        snap = self.snapshot(e)
        self.assertEqual(len(snap['points']), 3)
        self.assertEqual(len(snap['unresolved']), 6)
        self.assertEqual({r['member'] for r in snap['unresolved']}, {'unknown-alias', 'fictional:state:one'})
        self.assertEqual({r['status'] for r in snap['unresolved']}, {'absent'})
        resolution = self.store.input_resolution(e['id'])
        self.assertEqual(resolution['prior']['integration_observation']['unresolved'], snap['unresolved'])
        self.assertEqual(len(self.questions(e)), 1)
        self.assertIn('unknown-alias', encode(self.questions(e)))
        await self.classify(e, 'work-proposer')
        job = self.store.reserve()
        self.assertIsNotNone(job)
        self.assertEqual(self.store.event(e['id']), original)
        self.assertEqual(self.store.rows('SELECT * FROM local_discovered_points'), [])
        for _ in range(3):
            await self.phase('schedule_input_mappings')
        self.assertEqual(len(self.questions(e)), 1)
        self.assertEqual(len(self.store.rows("SELECT id FROM attempts WHERE event=? AND kind='input-locator'", (e['id'],))), 1)

    async def test_selected_ambiguity_returns_owned_question_without_invented_point(self):
        self.catalog_rows([{'id':'one', 'owner':'first'}, {'id':'one', 'owner':'second'}])
        e = self.post('Existing one with ambiguous actual backing')
        self.choices[e['id']] = {'state':'unresolved-existing'}
        await self.classify(e, 'work-proposer')
        await self.mapping(e)
        snap = self.snapshot(e)
        self.assertEqual(snap['points'], {})
        self.assertEqual(len(snap['unresolved']), 3)
        self.assertEqual({r['status'] for r in snap['unresolved']}, {'ambiguous'})
        self.assertEqual(len(self.questions(e)), 1)
        await self.classify(e, 'work-proposer')
        self.assertIsNone(self.store.reserve())
        self.assertEqual(self.store.rows('SELECT * FROM local_lookup_points'), [])
        self.assertEqual(self.store.rows('SELECT * FROM local_discovered_points'), [])

    async def test_unknown_relationship_cannot_authorize_new_business(self):
        e = self.post('Existing one and unknown alias; text grants no authority')
        self.hints[e['id']] = ['one', 'unknown-alias']
        self.choices[e['id']] = {'state':'new'}
        await self.classify(e, 'work-proposer')
        await self.phase('schedule_input_mappings')
        await self.phase('schedule_input_mappings')
        self.assertIsNone(self.store.input_resolution(e['id']))
        self.assertIsNone(self.store.reserve())
        record = self.store.one('SELECT error FROM input_lookups WHERE event=?', (e['id'],))
        self.assertIn('cannot authorize new business', record['error'])
        self.assertEqual(self.store.rows('SELECT * FROM local_discovered_points'), [])
        self.assertEqual(len(self.questions(e)), 1, 'question precedes a failed mapper')
        count = len(self.calls)
        await self.phase('schedule_input_mappings')
        self.assertEqual(len(self.calls), count)

    async def test_literal_decorated_member_value_is_never_stripped(self):
        self.catalog_rows([{'id':'fictional:state:one', 'state':'literal', 'owner':'literal-owner'},
                           {'id':'one', 'state':'other', 'owner':'different-owner'}])
        e = self.post('Existing literal identity fictional:state:one')
        self.hints[e['id']] = ['fictional:state:one']
        await self.classify(e, 'work-proposer')
        await self.mapping(e)
        snap = self.snapshot(e)
        self.assertEqual(snap['unresolved'], [])
        for point in snap['points'].values():
            self.assertEqual(point['definition']['bindings'][0]['path'][1]['value'], 'fictional:state:one')

    async def test_diagnostics_current_locator_observation_mapping_and_task_boundaries(self):
        self.serving_record()
        e = self.post('PRIVATE_BODY_CANARY existing one')
        await self.classify(e, 'work-proposer')
        await self.phase('schedule_input_mappings')
        code, hints = self.source_cli(e)
        self.assertEqual(code, 0, hints)
        self.assertTrue(hints['locator']['hints_present'])
        self.assertEqual(hints['locator']['collection']['exit'], 0)
        self.assertEqual(hints['locator']['hint_count'], 3)
        self.assertIsNone(hints['mapping'])
        self.assertIsNone(hints['job'])
        # A real observation failure before the mapper exists must survive a
        # later reservation's generic missing-metadata error.
        self.catalog_rows({'wrong':'representation'})
        await self.phase('schedule_input_mappings')
        self.assertIsNone(self.store.reserve())
        code, failed = self.source_cli(e)
        self.assertEqual(code, 0, failed)
        self.assertEqual(failed['dependency']['stage'], 'observation')
        self.assertIn('stable member representation', failed['dependency']['detail']['dependency'])
        self.assertIsNone(failed['mapping'])
        self.assertNotIn('PRIVATE_', encode(failed))
        (self.area/'observation-dependency.json').write_text(encode(failed))
        locator = failed['locator']['attempt']
        self.catalog_rows([{'id':'one', 'state':'current'}])
        await self.phase('schedule_input_mappings')
        code, mapped = self.source_cli(e)
        self.assertEqual(code, 0, mapped)
        self.assertIsNone(mapped['dependency'])
        self.assertEqual(mapped['locator']['attempt'], locator)
        self.assertTrue(mapped['mapping']['resolution_present'])
        self.assertIsNone(mapped['job'])
        await self.classify(e, 'work-proposer')
        job = self.store.reserve()
        self.assertIsNotNone(job)
        code, reserved = self.source_cli(e)
        self.assertEqual(code, 0, reserved)
        self.assertEqual(reserved['job']['id'], job['id'])
        self.assertIsNone(reserved['job']['active_attempt'])
        self.assertFalse(reserved['processing_complete'])
        (self.area/'stage-readbacks.json').write_text(encode({'locator':hints,'mapped':mapped,'reserved':reserved}))
        # Diagnostics never return old-controller locator/mapping metadata.
        self.store.db.execute('UPDATE attempts SET controller=? WHERE id=?', ('fictional-old', locator))
        code, changed = self.source_cli(e)
        self.assertEqual(code, 0, changed)
        self.assertIsNone(changed['locator'])
        self.assertNotIn('fictional-old', encode(changed))

    async def test_diagnostics_retains_failed_original_without_replay(self):
        self.serving_record()
        e = self.post('Existing one and missing relationship')
        self.hints[e['id']] = ['one', 'absent']
        self.choices[e['id']] = {'state':'new'}
        await self.classify(e, 'work-proposer')
        await self.phase('schedule_input_mappings')
        await self.phase('schedule_input_mappings')
        code, failed = self.source_cli(e)
        self.assertEqual(code, 0, failed)
        self.assertTrue(failed['mapping']['error_present'])
        self.assertEqual(failed['mapping']['collection']['exit'], 0)
        self.assertEqual(failed['dependency']['stage'], 'mapping')
        self.assertIn('cannot authorize new business', failed['dependency']['detail']['dependency'])
        self.assertFalse(failed['processing_complete'])
        before = encode(self.store.rows('SELECT * FROM attempts'))
        for _ in range(3):
            await self.phase('schedule_input_mappings')
        self.assertEqual(encode(self.store.rows('SELECT * FROM attempts')), before)

    async def test_current_diagnostic_authority_refuses_revocation_and_changed_source(self):
        self.serving_record()
        e = self.post('Existing one, exact source authority')
        await self.classify(e, 'work-proposer')
        await self.phase('schedule_input_mappings')
        with patch.object(processing, 'implementation', return_value={'fictional-changed':'different'}):
            self.assertEqual(self.source_cli(e)[0], 2)
        with self.store.tx():
            self.store.db.execute('UPDATE processing_capabilities SET revoked=? WHERE id=?', (self.now, self.key))
        self.assertEqual(self.source_cli(e)[0], 2)

    async def test_diagnostics_metadata_read_has_no_source_or_attempt_effect(self):
        self.serving_record()
        e = self.post('PRIVATE_BODY_CANARY existing one')
        await self.classify(e, 'work-proposer')
        await self.phase('schedule_input_mappings')
        tables = ['events','queue','attempts','input_locators','input_lookups','input_dependencies','outboxes','input_resolutions']
        before = {t:self.store.rows('SELECT * FROM '+t) for t in tables}
        code, view = self.source_cli(e)
        self.assertEqual(code, 0, view)
        self.assertEqual(before, {t:self.store.rows('SELECT * FROM '+t) for t in tables})
        self.assertNotIn('PRIVATE_', encode(view))
        self.assertNotIn('prompt', encode(view))
        self.assertNotIn('session', encode(view))
