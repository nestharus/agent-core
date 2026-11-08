"""Fictional original Store/birth/proof and current operative admission.

The shared1041 fixture explicitly supplies the fake native provider's journal
rows and current Board catalog/session seam. No actual native/provider call.
New capability journal rows represent a separate fictional Work decision;
Access.current/task, prospective.select and Store.reserve run normally.
"""
import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from coordinator_runtime import historical_admission as admission
from coordinator_runtime import processing, prospective, resource_scopes, service
from coordinator_runtime.contracts import Refusal, digest, encode, ident
import test_historical_verification1041 as original_fixture
from support import event, queued


class HistoricalAdmission1057(unittest.TestCase):
    def fixture(self, transition=False):
        name = 'test_original_transition_and_frozen_task_not_current_substitute' if transition else 'test_existing_unrecorded_revoked_source_supported_without_renewal'
        f = original_fixture.Historical1041(name)
        f.setUp()
        self.addCleanup(f.doCleanups)
        return f

    def selections(self, f):
        shared = dict(identity=copy.deepcopy(f.identity), purpose='new held Work integration under complete declared cooperative ceilings',
                      authority='actual respective fictional data custodian, current exact fields only', expires=900,
                      principal=f.work, configuration=digest(f.config), implementation=processing.implementation())
        writes = [str(f.s.home/p) for p in ('review-inputs', 'review-handles', 'review-history')]
        writes.append(str(f.s.home/'artifacts'/f.attempt))
        work = dict(shared, fields=admission.FIELDS['work-journal'], preserved_bytes=f.s.usage()['bytes'],
                    ceiling=dict(mode=admission.MODE, reads=[], writes=writes, unbounded=False))
        source = dict(shared, fields=admission.FIELDS['reviews-source'], work_access=None,
                      ceiling=dict(mode=admission.MODE, reads=[str(f.repo)], writes=[], unbounded=False))
        return work, source

    def grant(self, f, work=None, source=None):
        default_work, default_source = self.selections(f)
        work, source = work or default_work, source or default_source
        f.principal.actor = f.work
        wk = admission.authorize(f.s, f.boards, 'work-journal', work)['metadata_access']
        source['work_access'] = wk
        f.principal.actor = f.owner
        sk = admission.authorize(f.s, f.boards, 'reviews-source', source)['metadata_access']
        f.principal.actor = f.work
        return {'work-journal': wk, 'reviews-source': sk}

    def new_operation(self, f, keys, *, unbounded=False):
        old = json.loads(f.s.one('SELECT selection FROM processing_capabilities WHERE id=?', (f.cap,))['selection'])
        selection = copy.deepcopy(old)
        selection.update(tasks=['work-integrator'], authority='fictional genuine NEW Work decision', expires=900)
        selection['basis']['event_boundary'] = processing.source_boundary(f.s)
        selection['basis']['roles']['Work']['future_after'] = 1
        legacy = f.area/'other-retained'; legacy.mkdir()
        record = dict(original_hold='fictional retained Work resource duty', roots=[str(legacy)], unbounded=unbounded,
                      evidence='fictional complete retained software allocation, with old Reviews dependency kept',
                      comparison_mode=admission.MODE, historical_sources={f.job: keys})
        selection['service'] = dict(max_inflight=100, reviews={}, legacy_resources={'Work': record})
        f.s.db.execute("UPDATE enrollments SET legacy_hold=? WHERE role='Work'", (record['original_hold'],))
        service.validate(f.s, selection)
        key = ident()
        # Current selection/catalog is fiction, not a stubbed admission verdict.
        f.s.db.execute('INSERT INTO processing_capabilities VALUES(?,?,?,?,NULL,0)', (key, encode(selection), f.work, f.now))
        f.s.processing = processing.Access(f.s, key, f.boards)
        epoch = prospective.select(f.s, f.work, dict(configuration=digest(f.config), authority='genuine fictional NEW epoch', expires=900,
            processing_capability=key, grants={'Work': f.grants['Work']},
            tasks={'work-integrator': dict(task_hash=digest(f.config['tasks']['work-integrator']), software_handoffs={}, ordinary_effects=False)}))
        source = event(f.config, 'genuinely new Work Source', 'Work', 'work-integrator')
        source.update(kind='board', post=2, board_id=f.config['roles']['Work']['board_id'], grant=f.grants['Work'])
        queued(f.s, source)
        row = f.s.one("SELECT * FROM queue WHERE event=? AND task='work-integrator'", (source['id'],))
        self.assertNotEqual(key, f.cap)
        self.assertNotEqual(epoch['id'], f.epoch)
        self.assertTrue(f.s.processing.task(row))
        return row, key, record

    def test_complete_old_revoked_unrecorded_dependency_reaches_actual_reservation(self):
        f = self.fixture()
        keys = self.grant(f)
        row, current, _ = self.new_operation(f, keys)
        before = f.s.one('SELECT * FROM job_resource_policies WHERE job=?', (f.job,))
        with f.safe_queries():
            projected = admission.project(f.s, f.boards, keys)
            self.assertFalse(resource_scopes.blocked(f.s, row))
        job = f.s.reserve()
        self.assertIsNotNone(job)
        self.assertEqual(job['task'], 'work-integrator')
        self.assertNotEqual(job['id'], f.job)
        current_epoch = prospective.current(f.s, 'work-integrator')
        attempt = f.s.start_job(job['id'], job['token'])
        grant = dict(id=f.grants['Work'], issued_by=f.work, authority='original Work software grant', owner=f.work,
                     prospective_epoch=current_epoch['id'], delegated_by=f.work, delegation_authority='genuine fictional NEW epoch')
        with patch.object(f.boards['Work'], 'software_authority', return_value=grant):
            f.boards['Work'].bind_software_attempt(f.s, f.s.job(job['id']), attempt, None)
        proof = f.s.one("SELECT json_extract(detail,'$.software_authority.processing_capability') AS capability,"
                       "json_extract(detail,'$.software_authority.prospective_epoch') AS epoch FROM attempts WHERE id=?", (attempt,))
        self.assertEqual(proof, {'capability': current, 'epoch': current_epoch['id']})
        self.assertEqual(f.s.one('SELECT * FROM job_resource_policies WHERE job=?', (f.job,)), before)
        self.assertEqual(projected['facts']['outcome']['END'], 6)
        self.assertTrue(projected['facts']['original_authority']['processing_revoked'])
        self.assertEqual(projected['physical'], 'UNKNOWN')
        self.assertFalse(projected['physical_or_adversarial_guarantee'])
        self.assertFalse(projected['old_authority_revived'])
        self.assertEqual(f.s.processing.key, current)
        with self.assertRaises(Refusal): processing.Access(f.s, f.cap, f.boards).current()

    def test_original_configuration_transition_is_consumed_without_current_task_substitution(self):
        f = self.fixture(transition=True)
        keys = self.grant(f)
        row, _, _ = self.new_operation(f, keys)
        self.assertNotEqual(f.original_configuration, digest(f.config))
        self.assertFalse(resource_scopes.blocked(f.s, row))
        self.assertIsNotNone(f.s.reserve())

    def test_public_subset_and_missing_field_scope_stay_held(self):
        f = self.fixture()
        work, source = self.selections(f)
        source['ceiling']['reads'] = [str(f.other)]
        keys = self.grant(f, work, source)
        row, _, _ = self.new_operation(f, keys)
        with self.assertRaisesRegex(Refusal, 'complete original frozen'): admission.project(f.s, f.boards, keys)
        self.assertTrue(resource_scopes.blocked(f.s, row))
        self.assertIsNone(f.s.reserve())
        with self.assertRaisesRegex(Refusal, 'both actual'): admission.project(f.s, f.boards, {'work-journal': keys['work-journal']})

    def test_wrong_current_principal_is_refused_before_selected_scope_read(self):
        f = self.fixture()
        keys = self.grant(f)
        row, _, _ = self.new_operation(f, keys)
        f.principal.actor = ident()
        with patch.object(f.s, 'one', side_effect=AssertionError('read before principal')):
            with self.assertRaises(Refusal): admission.project(f.s, f.boards, keys)
        self.assertTrue(resource_scopes.blocked(f.s, row))

    def test_respective_custodians_cannot_issue_or_revoke_each_others_fields(self):
        f = self.fixture()
        work, source = self.selections(f)
        f.principal.actor = f.owner
        with self.assertRaises(Refusal): admission.authorize(f.s, f.boards, 'work-journal', work)
        keys = self.grant(f)
        with self.assertRaises(Refusal): admission.revoke(f.s, f.boards, 'reviews-source', keys['reviews-source'])
        admission.revoke(f.s, f.boards, 'work-journal', keys['work-journal'])
        with self.assertRaises(Refusal): admission.project(f.s, f.boards, keys)

    def test_changed_lineage_and_source_hold_remain_refusals(self):
        f = self.fixture()
        keys = self.grant(f)
        row, _, _ = self.new_operation(f, keys)
        faults = [("UPDATE attempts SET detail=json_set(detail,'$.processing_capability','wrong') WHERE id=?", f.attempt),
                  ("UPDATE review_call_contexts SET context=json_set(context,'$.collector','wrong') WHERE attempt=?", f.attempt),
                  ('DELETE FROM prospective_job_positions WHERE job=?', f.job),
                  ("UPDATE events SET hold='held' WHERE id=?", f.source['id'])]
        for sql, value in faults:
            with self.subTest(sql=sql):
                f.s.db.execute('SAVEPOINT fault')
                f.s.db.execute(sql, (value,))
                self.assertTrue(resource_scopes.blocked(f.s, row))
                self.assertIsNone(f.s._reserve_candidate(row))
                f.s.db.execute('ROLLBACK TO fault'); f.s.db.execute('RELEASE fault')

    def test_unbounded_dependency_and_pending_publication_conflict_remain(self):
        f = self.fixture()
        keys = self.grant(f)
        row, _, _ = self.new_operation(f, keys, unbounded=True)
        self.assertTrue(resource_scopes.blocked(f.s, row))
        self.assertIsNone(f.s.reserve())

    def test_pending_publication_is_a_write_even_with_effects_none(self):
        f = self.fixture()
        keys = self.grant(f)
        row, _, _ = self.new_operation(f, keys)
        self.assertFalse(resource_scopes.blocked(f.s, row))
        f.s.db.execute('INSERT INTO file_publications VALUES(?,?,?,?,?,?,?)',
                       (f.attempt, str(f.other/'pending.txt'), 'prepared', 'a'*64, str(f.other/'pending.tmp'), '{}', None))
        self.assertTrue(resource_scopes.blocked(f.s, row))
        self.assertIsNone(f.s.reserve())

    def test_missing_original_caller_and_malformed_material_stay_held(self):
        f = self.fixture()
        keys = self.grant(f)
        row, _, _ = self.new_operation(f, keys)
        faults = [("UPDATE processing_capabilities SET selection=json_remove(selection,?) WHERE id=?",
                   ('$.service.reviews."reviews-proposer".caller', f.cap)),
                  ("UPDATE review_calls SET packet=json_set(packet,'$.method_files',json('[null]')) WHERE attempt=?", (f.attempt,)),
                  ("UPDATE review_calls SET packet=json_set(packet,'$.history',?) WHERE attempt=?", (str(f.other/'outside-history'), f.attempt))]
        for sql, args in faults:
            with self.subTest(sql=sql):
                f.s.db.execute('SAVEPOINT material')
                f.s.db.execute(sql, args)
                self.assertTrue(resource_scopes.blocked(f.s, row))
                self.assertIsNone(f.s._reserve_candidate(row))
                f.s.db.execute('ROLLBACK TO material'); f.s.db.execute('RELEASE material')

    def test_opaque_native_or_incomplete_executor_ceiling_is_not_downgraded(self):
        f = self.fixture()
        work, source = self.selections(f)
        work['ceiling']['unbounded'] = True
        with self.assertRaisesRegex(Refusal, 'unbounded'): self.grant(f, work, source)
        work['ceiling']['mode'] = 'actual-native-physical'
        with self.assertRaisesRegex(Refusal, 'unbounded'): self.grant(f, work, source)
        work['ceiling']['mode'] = admission.MODE
        work['ceiling']['unbounded'] = False
        work['ceiling']['writes'] = []
        keys = self.grant(f, work, source)
        row, _, _ = self.new_operation(f, keys)
        with self.assertRaisesRegex(Refusal, 'executor ceiling incomplete'): admission.project(f.s, f.boards, keys)
        self.assertTrue(resource_scopes.blocked(f.s, row))

    def test_expiry_new_authority_revocation_visibility_and_current_pin_changes_refuse(self):
        f = self.fixture()
        keys = self.grant(f)
        row, current, _ = self.new_operation(f, keys)
        f.now = 901
        self.assertTrue(resource_scopes.blocked(f.s, row))
        f.now = 300
        with patch.object(processing, 'implementation', return_value={'foreign-current-source': 'f'*64}):
            with self.assertRaises(Refusal): resource_scopes.blocked(f.s, row)
        f.s.db.execute('UPDATE processing_capabilities SET revoked=301 WHERE id=?', (current,))
        with self.assertRaises(Refusal): resource_scopes.blocked(f.s, row)
        f.s.db.execute('UPDATE processing_capabilities SET revoked=NULL WHERE id=?', (current,))
        f.connection.execute('DELETE FROM thread_posts')
        self.assertTrue(resource_scopes.blocked(f.s, row))

    def test_preserved_capacity_is_not_refunded_or_measured_from_old_captures(self):
        f = self.fixture()
        work, _ = self.selections(f)
        work['preserved_bytes'] = f.config['limits']['max_bytes']
        with patch.object(f.s, 'usage', side_effect=AssertionError('old storage walk')):
            with self.assertRaisesRegex(Refusal, 'preserved allocation'): admission.authorize(f.s, f.boards, 'work-journal', work)
        self.assertEqual(f.s.one('SELECT COUNT(*) AS n FROM historical_metadata_access')['n'], 0)

    def test_supported_cli_uses_respective_current_actor(self):
        from coordinator_runtime import cli
        f = self.fixture()
        keys = self.grant(f)
        self.new_operation(f, keys)
        selection = f.area/'current-access.json'; selection.write_text(encode(keys))
        args = cli.parser().parse_args(['historical-resource-project', '--selection', str(selection)])
        with patch.object(processing, 'ProcessingBoard', side_effect=lambda config, role: f.boards[role]), \
                patch.object(cli, 'actual_actor', side_effect=f.principal.acting_session):
            self.assertTrue(cli.operate(args, f.s)['complete_declared_ceiling'])
        f.principal.actor = f.owner
        with patch.object(cli, 'actual_actor', side_effect=f.principal.acting_session):
            with self.assertRaises(Refusal): cli.historical_resource_actor(f.config, args)
