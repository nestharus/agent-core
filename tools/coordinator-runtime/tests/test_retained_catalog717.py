"""Actual configured catalog shape, remapped to owned fiction before metadata.

Production selection, mapping, reservation, prospective binding, routine staging
and launch guards run. Authentication, classifier and collected SDK answers use
the declared synthetic seams from 705/QA629; no provider/native work runs.
"""
import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from coordinator_runtime import local_integration as local, prospective, routine
from coordinator_runtime.contracts import Refusal, encode, ident
from coordinator_runtime.dispatcher import execution_spec
from test_qa629_repairs import Fixture
import test_retained_launch705 as retained


class CatalogCase(Fixture):
    setUp = retained.RetainedLaunch.setUp
    basis = retained.RetainedLaunch.basis
    issue = retained.RetainedLaunch.issue
    selection = retained.RetainedLaunch.selection
    epoch = retained.RetainedLaunch.epoch
    authorize = retained.RetainedLaunch.authorize

    def configure(self):
        retained.RetainedLaunch.configure(self)
        shape = Path(__file__).with_name('retained_catalog717.json').read_text()
        self.shape = json.loads(shape.replace('$FIXTURE', str(self.area)).replace(
            '$WORK_OWNER', self.config['roles']['Work']['owner']))
        task = self.shape['work_integrator']
        self.config['tasks']['work-integrator'] = task
        self.config['delivery']['recipients']['Root'] = dict(
            session=ident(), profile='.codex3', board_role='root')
        self.config['local_integration'] = dict(max_inflight=8,
            tasks={name:copy.deepcopy(self.shape['local_policy'])
                   for name in ('work-integrator', 'work-proposer')}, points=self.shape['points'])
        proposer = self.config['tasks']['work-proposer']
        proposer['network'] = False
        proposer['templates'] = task['templates']
        proposer['effect_authority']['read_roots'] = task['effect_authority']['read_roots']
        self.targets = list(task['routine_completion']['targets'])
        self.log = Path(task['routine_completion']['bounded_log']['target'])
        self.catalog = Path(self.targets[0])
        documents = {p:{} for p in self.targets if p.endswith('.json')}

        def seed(value, path):
            segment, *rest = path
            if isinstance(segment, dict):
                row = next((r for r in value if r.get(segment['field']) == segment['value']), None)
                if row is None:
                    row = {segment['field']:segment['value'], 'owner':'fixture', 'history':['retain']}
                    value.append(row)
                if rest: seed(row, rest)
            elif rest:
                seed(value.setdefault(segment, [] if isinstance(rest[0], dict) else {}), rest)
            else:
                value.setdefault(segment, 'original')

        for point in self.shape['points'].values():
            for binding in point['bindings']:
                seed(documents[binding['target']], binding['path'])
        for target in self.targets:
            path = Path(target)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(encode(documents[target]) if target in documents else 'Fictional original history\n')
        for name in task['templates']:
            path = Path(name)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('Fictional bounded selected catalog method; conserve all original duties.\n')
        self.original_files = {p:Path(p).read_bytes() for p in self.targets}
        if hasattr(self, 'change_configuration'):
            self.change_configuration(self.config)

    def route_receipt(self):
        base = retained.RetainedLaunch.route_receipt(self)
        points = self.config['local_integration']['points']
        writes = [key for key, value in points.items() if value['writable']]
        return {**base, 'integration':dict(state='known', reads=list(points), writes=writes)}

    def new_job(self, before_epoch=False, bind=True):
        retained.RetainedLaunch.new_job(self, before_epoch=before_epoch, bind=bind)
        if bind:
            directory = self.store.home/'artifacts'/self.attempt
            directory.mkdir(parents=True)
            routine.prepare(self.store, self.boards['Work'], self.job, self.attempt,
                            self.config['tasks'][self.job['task']])

    def assert_originals(self):
        retained.RetainedLaunch.assert_originals(self)
        self.assertEqual({p:Path(p).read_bytes() for p in self.targets}, self.original_files)


class CatalogLaunch(CatalogCase):
    test_frozen_job_cannot_bind = retained.RetainedLaunch.test_genuine_job_frozen_before_epoch_cannot_bind
    test_source_and_mapping_drift = retained.RetainedLaunch.test_source_mapping_and_member_drift_refuse
    test_cap_scope_ordinary_ceilings = retained.RetainedLaunch.test_current_cap_epoch_mapping_scope_and_ordinary_run_ceilings
    test_hold_before_body = retained.RetainedLaunch.test_held_source_is_rejected_before_body_by_retained_guard
    test_missing_source_before_body = retained.RetainedLaunch.test_missing_member_referent_refuses_without_body_diagnosis
    test_unselected_member_and_mapping = retained.RetainedLaunch.test_unselected_member_frozen_mapping_or_package_cannot_borrow_permission
    test_cap_epoch_birth_fences = retained.RetainedLaunch.test_cap_epoch_birth_and_current_selection_fences
    test_later_epoch_cannot_restamp = retained.RetainedLaunch.test_newer_epoch_never_restamps_existing_job_or_attempt
    test_collected_unbound_refusal = retained.RetainedLaunch.test_previously_collected_unbound_failure_cannot_gain_authority
    test_no_selection_or_ordinary = retained.RetainedLaunch.test_no_explicit_selected_mode_or_ordinary_permission

    def test_actual_shape_binds_stages_and_authorizes_new_job(self):
        retained.RetainedLaunch.test_new_selected_job_reaches_real_launch_guard_without_source_renewal(self)
        self.assertEqual(len(local.scope_for(self.store, self.job)['reads']), 13)
        self.assertTrue(local.scope_for(self.store, self.job)['writes'])
        policy = self.config['tasks'][self.job['task']]['routine_completion']
        run = self.store.one('SELECT * FROM routine_runs WHERE attempt=?', (self.attempt,))
        self.assertEqual(json.loads(run['policy']), policy)
        self.assertEqual(set(json.loads(run['before_files'])), set(self.targets))
        self.assertIsNotNone(self.store.one('SELECT basis FROM local_bases WHERE attempt=?', (self.attempt,)))
        stages = self.store.rows('SELECT target,path FROM routine_stages WHERE attempt=?', (self.attempt,))
        self.assertEqual({r['target'] for r in stages}, set(self.targets))
        directory = self.store.home/'artifacts'/self.attempt
        spec = execution_spec(self.config['tasks'][self.job['task']], directory)
        self.assertEqual(spec['effect_authority']['write_roots'], [str(directory)])
        self.assertFalse(spec['network'])
        self.assertEqual(self.store.rows('SELECT * FROM ordinary_runs'), [])
        self.assertEqual(self.store.rows('SELECT * FROM local_commits'), [])
        self.assertEqual(self.store.rows('SELECT * FROM file_publications'), [])
        self.assert_originals()

    def test_stale_point_refuses_and_collected_proof_keeps_original_revision(self):
        self.new_job()
        document = json.loads(self.catalog.read_text())
        document['packet_coordination']['coordinator_runtime_rollout']['status'] = 'later'
        self.catalog.write_text(encode(document))
        with self.assertRaises(Refusal): self.authorize()
        self.catalog.write_bytes(self.original_files[str(self.catalog)])
        self.authorize()
        from support import collect, result
        collect(self.store, self.attempt, result(), tool_completion=dict(complete=True, items=[]))
        proof = self.store.attempt(self.attempt)['detail']
        self.catalog.write_text(encode(document))
        self.boards['Work']._software_job_grant(self.store, self.store.job(self.job['id']))
        self.assertEqual(self.store.attempt(self.attempt)['detail'], proof)
        self.assertIsNone(self.store.one('SELECT processed_at FROM events WHERE id=?', (self.source['id'],))['processed_at'])
        self.assertEqual(self.store.rows('SELECT * FROM local_commits'), [])
        self.assertEqual(self.store.rows('SELECT * FROM file_publications'), [])

    def test_native_discovery_and_unselected_points_refuse_before_acquisition(self):
        self.new_job()
        points = copy.deepcopy(local.point_definitions(self.store))
        key = next(iter(points))
        points[key]['bindings'] = [dict(native='branch', id='fictional-native')]
        with patch.object(local, 'point_definitions', return_value=points), \
             patch('coordinator_runtime.local_native.authorize', side_effect=AssertionError('native acquired')), \
             patch('coordinator_runtime.local_native.snapshot', side_effect=AssertionError('native acquired')), \
             patch.object(self.store, 'event', side_effect=AssertionError('source acquired')):
            self.assertIsNone(prospective.for_job(self.store, self.job))
        scope = local.scope_for(self.store, self.job)
        for change in (dict(lane='discovery'), dict(neighbors=[dict(event='fictional-neighbor')])):
            with self.subTest(change=change):
                self.store.db.execute('SAVEPOINT scope717')
                try:
                    self.store.db.execute('UPDATE local_jobs SET scope=? WHERE job=?',
                        (encode({**scope, **change}), self.job['id']))
                    with patch.object(self.store, 'event', side_effect=AssertionError('broad source acquired')):
                        self.assertIsNone(prospective.for_job(self.store, self.store.job(self.job['id'])))
                finally:
                    self.store.db.execute('ROLLBACK TO scope717')
                    self.store.db.execute('RELEASE scope717')
        # Even a wider discovery/lookup allowlist cannot give this retained
        # exception a point absent from the task's explicit configured list.
        selected = copy.deepcopy(local.selected(self.store, self.job['task']))
        selected['points'].remove(key)
        with patch.object(local, 'selected', return_value=selected), \
             patch.object(local, 'allowed_points', return_value=set(points)), \
             patch.object(self.store, 'event', side_effect=AssertionError('unselected source acquired')):
            self.assertIsNone(prospective.for_job(self.store, self.job))

    def test_file_bindings_must_belong_to_selected_routine_before_body(self):
        self.new_job()
        for bindings in ([], [dict(target=str(self.area/'unselected.json'), path=['state'])],
                         [dict(target=str(self.log), path=['state'])],
                         [dict(target=str(self.catalog), path=[])]):
            points = copy.deepcopy(local.point_definitions(self.store))
            points[next(iter(points))]['bindings'] = bindings
            with self.subTest(bindings=bindings), \
                 patch.object(local, 'point_definitions', return_value=points), \
                 patch.object(self.store, 'event', side_effect=AssertionError('unbound source acquired')), \
                 patch('coordinator_runtime.custody.safe_path', side_effect=AssertionError('unbound target metadata')):
                self.assertIsNone(prospective.for_job(self.store, self.job))

    def test_routine_still_requires_original_completion_grant(self):
        self.new_job(bind=False)
        board = self.boards['Work']
        board.bind_software_attempt(self.store, self.job, self.attempt, None)
        self.assertIsNotNone(prospective.for_job(self.store, self.job))
        grant = self.store.enrollment('Work')['grant_id']
        with board.opened() as conn:
            with board.store.write(conn):
                conn.execute('DELETE FROM coordinator_completion_grants_v1 WHERE grant_id=?', (grant,))
        with self.assertRaises(Refusal):
            routine.prepare(self.store, board, self.job, self.attempt,
                            self.config['tasks'][self.job['task']])
        self.assertEqual(self.store.rows('SELECT * FROM routine_runs'), [])
        self.assertEqual(self.store.rows('SELECT * FROM file_publications'), [])
        self.assert_originals()

    def test_other_owner_reconcile_shapes_are_not_retained_catalog_authority(self):
        def task(config): return config['tasks']['work-integrator']
        cases = {
            'missing-routine':lambda c:task(c).pop('routine_completion'),
            'other-routine':lambda c:task(c).update(routine_completion=dict(kind='file-witness',
                targets=task(c)['routine_completion']['targets'])),
            'network':lambda c:task(c).update(network=True),
            'wrong-sandbox':lambda c:task(c).update(sandbox='read-only'),
            'broad-write-root':lambda c:task(c)['effect_authority'].update(write_roots=[
                str(Path(task(c)['routine_completion']['targets'][0]).parent)]),
            'missing-target':lambda c:task(c)['routine_completion']['targets'].pop(),
            'wrong-log':lambda c:task(c)['routine_completion']['bounded_log'].update(target=str(self.area/'unselected-log')),
            'unbounded-log':lambda c:task(c)['routine_completion']['bounded_log'].update(max_lines=13),
            'external-operation':lambda c:task(c)['effect_authority']['operations'].append('organize-authorized-refs'),
        }
        for label, change in cases.items():
            with self.subTest(case=label):
                case = CatalogCase('runTest')
                # Apply before real configuration/selection validation, so a
                # task-hash mismatch cannot be the only refusal being tested.
                case.change_configuration = change
                try:
                    with self.assertRaises(Refusal):
                        case.setUp()
                        case.new_job()
                finally:
                    case.doCleanups()


class ProposerLaunch(CatalogCase):
    setUp = retained.ProposerLaunch.setUp

    def route_receipt(self):
        value = CatalogCase.route_receipt(self)
        return {**value, 'task':'work-proposer',
                'integration':{**value['integration'], 'writes':[]}}

    def test_actual_point_shape_readonly_proposer_remains_eligible(self):
        retained.RetainedLaunch.test_new_selected_job_reaches_real_launch_guard_without_source_renewal(self)
        task = self.config['tasks']['work-proposer']
        self.assertEqual((task['effects'], task['sandbox']), ('none', 'read-only'))
        self.assertEqual(task['effect_authority']['write_roots'], [])
        self.assertEqual(len(local.scope_for(self.store, self.job)['reads']), 13)
        self.assertEqual(local.scope_for(self.store, self.job)['writes'], [])
        self.assertEqual(self.store.rows('SELECT * FROM routine_runs'), [])
        self.assert_originals()


if __name__ == '__main__':
    unittest.main(verbosity=2)
