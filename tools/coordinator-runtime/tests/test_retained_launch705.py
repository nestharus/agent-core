"""Selected retained inputs authorize new catalog jobs, never old frozen jobs.

Owned SDK fiction only. Principal authentication and classifier collection use
the existing synthetic fixture seams; no model/native/ordinary work is run.
"""
import copy
import json
import sqlite3
import unittest
from unittest.mock import patch

from coordinator_runtime import local_integration, processing, prospective
from coordinator_runtime.contracts import Refusal, digest, encode, scoped_task
from coordinator_runtime.store import Store
from test_qa629_repairs import Fixture, actor
import test_selected_basis50115 as selected


class RetainedLaunch(Fixture):
    configure = selected.CurrentConfigurationSelected.configure
    route_receipt = selected.LocalSelectedBasis.route_receipt
    basis = selected.SelectedBasis.basis
    issue = selected.SelectedBasis.issue
    selection = selected.CurrentConfigurationSelected.selection

    def setUp(self):
        selected.CurrentConfigurationSelected.setUp(self)
        self.cap = self.issue(self.selection())
        self.store.processing = processing.Access(self.store, self.cap, self.boards)
        with actor(self.boards['Work'].store, self.issuer):
            self.current_mapping = processing.map_input(self.store, self.boards, self.cap,
                self.source['id'], self.issuer, self.route_receipt())
        self.classify(task='work-integrator')
        self.originals = {t:self.store.rows('SELECT * FROM '+t) for t in (
            'events', 'processing_source_positions', 'enrollments', 'input_resolutions', 'outboxes')}

    def epoch(self):
        name = self.expected['task']
        self.epoch_receipt = prospective.select(self.store, self.issuer, dict(
            configuration=digest(self.config), authority='Fictional current retained catalog coordination',
            expires=self.store.clock()+300, processing_capability=self.cap,
            grants={'Work':self.store.enrollment('Work')['grant_id']},
            tasks={name:dict(task_hash=digest(self.config['tasks'][name]),
                software_handoffs={}, ordinary_effects=False)}))

    def new_job(self, before_epoch=False, bind=True):
        if not before_epoch:
            self.epoch()
        self.job = self.store.reserve()
        self.assertIsNotNone(self.job)
        if before_epoch:
            self.epoch()
        self.attempt = self.store.start_job(self.job['id'], self.job['token'])
        self.job = self.store.job(self.job['id'])
        if bind:
            self.boards['Work'].bind_software_attempt(self.store, self.job, self.attempt, None)
            task = scoped_task(self.job['task'], self.config['tasks'][self.job['task']], None)
            local_integration.prepare_input_basis(self.store, self.job, self.attempt, task)

    def authorize(self):
        self.store.authorize_launch(self.attempt)

    def assert_originals(self):
        for table, rows in self.originals.items():
            self.assertEqual(self.store.rows('SELECT * FROM '+table), rows, table)
        attempt = self.store.attempt(self.attempt)
        self.assertIsNone(attempt['begin'])
        self.assertIsNone(attempt['session'])
        self.assertIsNone(attempt['exit'])

    def test_new_selected_job_reaches_real_launch_guard_without_source_renewal(self):
        self.new_job()
        self.assertLessEqual(self.expected['source_birth'], self.epoch_receipt['event_boundary'])
        self.assertGreater(self.current_mapping['version'], self.expected['mapping_version'])
        self.assertGreater(self.store.one('SELECT position FROM prospective_job_positions WHERE job=?',
            (self.job['id'],))['position'], self.epoch_receipt['job_boundary'])
        self.authorize()
        self.assertTrue(prospective.requires_authority(self.store, self.job))
        self.assertEqual(prospective.for_job(self.store, self.job)['id'], self.epoch_receipt['id'])
        self.assert_originals()

    def test_genuine_job_frozen_before_epoch_cannot_bind(self):
        self.new_job(before_epoch=True, bind=False)
        before = self.store.attempt(self.attempt)
        with self.assertRaisesRegex(Refusal, 'historical jobs/members'):
            self.boards['Work'].bind_software_attempt(self.store, self.job, self.attempt, None)
        self.assertEqual(self.store.attempt(self.attempt), before)
        self.assertIsNone(prospective.for_job(self.store, self.job))
        with patch.object(self.store, 'event', side_effect=AssertionError('old body acquired')):
            self.assertIsNone(prospective.for_job(self.store, self.job))
        self.assert_originals()

    def test_source_mapping_and_member_drift_refuse(self):
        self.new_job()
        cases = [
            ('hold', 'UPDATE events SET hold=? WHERE id=?', ('fictional hold', self.source['id'])),
            ('body', 'UPDATE events SET payload=? WHERE id=?', ('{}', self.source['id'])),
            ('hash', 'UPDATE events SET hash=? WHERE id=?', ('0'*64, self.source['id'])),
            ('birth', 'UPDATE processing_source_positions SET position=position+100 WHERE event=?', (self.source['id'],)),
            ('mapping', 'UPDATE input_resolutions SET source_hash=? WHERE event=? AND version=?',
                ('0'*64, self.source['id'], self.current_mapping['version'])),
            ('queue-task', 'UPDATE queue SET task=? WHERE event=?', ('work-proposer', self.source['id'])),
            ('queue-job', 'UPDATE queue SET job=? WHERE event=?', ('fictional-other-job', self.source['id'])),
            ('recipient', 'UPDATE enrollments SET owner=? WHERE role=?', ('fictional-wrong-owner', 'Work')),
        ]
        for label, sql, args in cases:
            with self.subTest(case=label):
                self.store.db.execute('SAVEPOINT negative705')
                try:
                    self.store.db.execute(sql, args)
                    with self.assertRaises(Refusal): self.authorize()
                finally:
                    self.store.db.execute('ROLLBACK TO negative705')
                    self.store.db.execute('RELEASE negative705')
        self.authorize()
        self.assert_originals()

    def test_current_cap_epoch_mapping_scope_and_ordinary_run_ceilings(self):
        self.new_job()
        cases = [
            ('cap-issuer', 'UPDATE processing_capabilities SET issuer=? WHERE id=?', ('fictional-foreign-owner', self.cap)),
            ('cap-revoked', 'UPDATE processing_capabilities SET revoked=1 WHERE id=?', (self.cap,)),
            ('cap-expired-task', "UPDATE prospective_authorities SET selection=json_set(selection,'$.expires',0) WHERE id=?", (self.epoch_receipt['id'],)),
            ('foreign-epoch-cap', "UPDATE prospective_authorities SET selection=json_set(selection,'$.processing_capability',?) WHERE id=?", (self.oldcap, self.epoch_receipt['id'])),
            ('legacy-unobserved-epoch', "UPDATE prospective_authorities SET selection=json_remove(selection,'$.job_birth') WHERE id=?", (self.epoch_receipt['id'],)),
            ('old-job-position', 'UPDATE prospective_job_positions SET position=? WHERE job=?', (self.epoch_receipt['job_boundary'], self.job['id'])),
            ('job-package', 'UPDATE jobs SET package=? WHERE id=?', ('fictional-product', self.job['id'])),
            ('job-controller', 'UPDATE jobs SET controller=? WHERE id=?', ('fictional-foreign-controller', self.job['id'])),
            ('mapping-missing', 'DELETE FROM input_resolutions WHERE event=?', (self.source['id'],)),
            ('mapping-actor', 'UPDATE input_resolutions SET actor=? WHERE event=? AND version=?', ('fictional-foreign-owner', self.source['id'], self.current_mapping['version'])),
            ('mapping-mode', "UPDATE input_resolutions SET receipt=json_set(receipt,'$.mode','defer') WHERE event=? AND version=?", (self.source['id'], self.current_mapping['version'])),
            ('mapping-task', "UPDATE input_resolutions SET receipt=json_set(receipt,'$.task','work-proposer') WHERE event=? AND version=?", (self.source['id'], self.current_mapping['version'])),
            ('scope-missing', 'DELETE FROM local_jobs WHERE job=?', (self.job['id'],)),
            ('ordinary-run', 'INSERT INTO ordinary_runs VALUES(?,?,?,?,?,?,NULL)', (self.attempt, self.job['id'], self.epoch_receipt['id'], '{}', '{}', 'intent')),
        ]
        for label, sql, args in cases:
            with self.subTest(case=label):
                self.store.db.execute('SAVEPOINT ceilings705')
                try:
                    self.store.db.execute(sql, args)
                    with self.assertRaises(Refusal): self.authorize()
                finally:
                    self.store.db.execute('ROLLBACK TO ceilings705')
                    self.store.db.execute('RELEASE ceilings705')
        with patch.object(local_integration, 'allowed_points', return_value=set()), self.assertRaises(Refusal):
            self.authorize()
        self.authorize()
        self.assert_originals()

    def test_held_source_is_rejected_before_body_by_retained_guard(self):
        self.new_job()
        self.store.set_hold(self.source['id'], 'fictional current source hold')
        with patch.object(self.store, 'event', side_effect=AssertionError('held source acquired')):
            self.assertIsNone(prospective.for_job(self.store, self.job))

    def other_connection_hold(self, reason):
        owner = Store(self.config)
        try:
            owner.set_hold(self.source['id'], reason)
        finally:
            owner.close()

    def test_full_start_refuses_held_member_before_acquisition_then_unheld_works(self):
        self.epoch()
        self.job = self.store.reserve()
        original = self.store.job(self.job['id'])
        attempts = self.store.rows('SELECT * FROM attempts')
        for reason in ('fictional late local hold', ''):
            self.other_connection_hold(reason)
            with patch.object(self.store, '_input_member', side_effect=AssertionError('held member hashed')), \
                 patch.object(self.store, 'event', side_effect=AssertionError('held payload/custody acquired')), \
                 patch.object(self.store, 'input_resolution', side_effect=AssertionError('held mapping acquired')):
                with self.assertRaises(Refusal):
                    self.store.start_job(self.job['id'], self.job['token'])
            self.assertEqual(self.store.job(self.job['id']), original)
            self.assertEqual(self.store.rows('SELECT * FROM attempts'), attempts)
        self.other_connection_hold(None)
        self.attempt = self.store.start_job(self.job['id'], self.job['token'])
        self.job = self.store.job(self.job['id'])
        self.boards['Work'].bind_software_attempt(self.store, self.job, self.attempt, None)
        task = scoped_task(self.job['task'], self.config['tasks'][self.job['task']], None)
        local_integration.prepare_input_basis(self.store, self.job, self.attempt, task)
        self.authorize()
        self.assert_originals()

    def test_full_authorize_and_current_job_refuse_hold_before_acquisition(self):
        self.new_job()
        original = self.store.attempt(self.attempt)
        self.other_connection_hold('fictional late local hold')
        for check in (self.authorize, lambda: local_integration.current_job(self.store, self.job)):
            with patch.object(self.store, '_input_member', side_effect=AssertionError('held member hashed')), \
                 patch.object(self.store, 'event', side_effect=AssertionError('held payload/custody acquired')), \
                 patch.object(self.store, 'input_resolution', side_effect=AssertionError('held mapping acquired')):
                with self.assertRaises(Refusal): check()
        self.assertEqual(self.store.attempt(self.attempt), original)
        self.other_connection_hold(None)
        self.authorize()
        self.assert_originals()

    def test_current_member_referent_drift_refuses_before_other_body(self):
        self.new_job()
        member = json.loads(self.job['members'])[0]
        other = self.store.one('SELECT id FROM queue WHERE event=?', (self.other['id'],))
        self.store.db.execute('UPDATE jobs SET members=? WHERE id=?',
            (encode([dict(member, queue=other['id'])]), self.job['id']))
        with patch.object(self.store, '_input_member', side_effect=AssertionError('wrong member acquired')), \
             patch.object(self.store, 'event', side_effect=AssertionError('wrong source acquired')):
            with self.assertRaises(Refusal): self.authorize()

    def test_held_neighbor_refuses_before_first_member_or_custody_read(self):
        self.new_job()
        scope = local_integration.scope_for(self.store, self.job)
        queue = self.store.one('SELECT id,event,package FROM queue WHERE event=?', (self.other['id'],))
        scope['neighbors'] = [dict(queue=queue['id'], event=queue['event'], package=queue['package'], hash='0'*64)]
        self.store.db.execute('UPDATE local_jobs SET scope=? WHERE job=?', (encode(scope), self.job['id']))
        denied = []
        def no_body(action, table, column, database, caller):
            if action == sqlite3.SQLITE_READ and (table in {'source_custody', 'results'}
                    or table == 'events' and column == 'payload'):
                denied.append((table, column))
                return sqlite3.SQLITE_DENY
            return sqlite3.SQLITE_OK
        self.store.db.set_authorizer(no_body)
        try:
            with patch.object(self.store, '_input_member', side_effect=AssertionError('first member acquired')):
                with self.assertRaises(Refusal): self.authorize()
        finally:
            self.store.db.set_authorizer(None)
        self.assertEqual(denied, [])

    def test_current_job_reads_share_transaction_with_hold_check(self):
        self.new_job()
        owner = Store(self.config)
        self.addCleanup(owner.close)
        owner.db.execute('PRAGMA busy_timeout=0')
        member = self.store._input_member
        reads = []
        def locked(queue):
            self.assertTrue(self.store.db.in_transaction)
            with self.assertRaisesRegex(sqlite3.OperationalError, 'locked'):
                owner.set_hold(self.source['id'], 'fictional concurrent hold')
            reads.append(queue['event'])
            return member(queue)
        with patch.object(self.store, '_input_member', locked):
            local_integration.current_job(self.store, self.job)
        self.assertEqual(reads, [self.source['id']])
        owner.set_hold(self.source['id'], 'fictional committed hold after guard')
        with patch.object(self.store, '_input_member', side_effect=AssertionError('held member acquired')):
            with self.assertRaises(Refusal): local_integration.current_job(self.store, self.job)

    def test_missing_member_referent_refuses_without_body_diagnosis(self):
        self.new_job()
        member = dict(json.loads(self.job['members'])[0], event='fictional-missing705')
        self.store.db.execute('UPDATE jobs SET members=? WHERE id=?', (encode([member]), self.job['id']))
        with patch.object(self.store, 'event', side_effect=AssertionError('unknown body acquired')):
            with self.assertRaisesRegex(Refusal, 'source referent'):
                prospective.for_job(self.store, self.store.job(self.job['id']))

    def test_unselected_member_frozen_mapping_or_package_cannot_borrow_permission(self):
        self.new_job()
        member = json.loads(self.job['members'])[0]
        variants = [dict(member, input_resolution=self.mapping['version']),
            dict(member, package='fictional-product'), dict(member, hash='0'*64),
            dict(member, event=self.other['id']), dict(member, input_resolution=999)]
        for changed in variants:
            with self.subTest(member=changed):
                self.store.db.execute('UPDATE jobs SET members=? WHERE id=?', (encode([changed]), self.job['id']))
                with self.assertRaises(Refusal): self.authorize()
        self.store.db.execute('UPDATE jobs SET members=? WHERE id=?', (self.job['members'], self.job['id']))
        self.authorize()

    def test_cap_epoch_birth_and_current_selection_fences(self):
        self.new_job()
        original = self.store.attempt(self.attempt)['detail']
        for change in ('cap', 'epoch', 'proof-cap'):
            detail = json.loads(original)
            if change == 'cap': detail['processing_capability'] = self.oldcap
            elif change == 'epoch': detail['software_authority']['prospective_epoch'] = 'fictional-foreign-epoch'
            else: detail['software_authority']['processing_capability'] = self.oldcap
            self.store.db.execute('UPDATE attempts SET detail=? WHERE id=?', (encode(detail), self.attempt))
            with self.subTest(change=change), self.assertRaises(Refusal): self.authorize()
        self.store.db.execute('UPDATE attempts SET detail=? WHERE id=?', (original, self.attempt))
        self.store.db.execute('SAVEPOINT missing705')
        self.store.db.execute('DELETE FROM prospective_job_positions WHERE job=?', (self.job['id'],))
        self.assertTrue(prospective.requires_authority(self.store, self.job))
        with self.assertRaises(Refusal): self.authorize()
        self.store.db.execute('ROLLBACK TO missing705'); self.store.db.execute('RELEASE missing705')
        with patch.object(processing, 'implementation', return_value={'fictional':'changed'}):
            with self.assertRaises(Refusal): self.authorize()
        prospective.revoke(self.store, self.issuer, self.epoch_receipt['id'])
        self.assertTrue(prospective.requires_authority(self.store, self.job))
        with self.assertRaises(Refusal): self.authorize()
        self.assert_originals()

    def test_stale_point_and_native_binding_refuse_before_acquisition(self):
        self.new_job()
        self.catalog.write_text(encode(dict(a=dict(id='a', owner='fixture', state='changed'))))
        with self.assertRaises(Refusal): self.authorize()
        self.catalog.write_text(encode(dict(a=dict(id='a', owner='fixture', state='original'))))
        definitions = copy.deepcopy(local_integration.point_definitions(self.store))
        definitions['a']['bindings'] = [dict(native='branch')]
        with patch.object(local_integration, 'point_definitions', return_value=definitions), \
             patch('coordinator_runtime.local_native.authorize', side_effect=AssertionError('native acquired')), \
             patch('coordinator_runtime.local_native.snapshot', side_effect=AssertionError('native acquired')):
            self.assertIsNone(prospective.for_job(self.store, self.job))
        # Store also runs the existing native permission gate before the task
        # authorizer. A permission check is not a native material acquisition.
        with patch.object(local_integration, 'point_definitions', return_value=definitions), \
             patch('coordinator_runtime.local_native.authorize', side_effect=Refusal('fictional native permission absent')), \
             patch('coordinator_runtime.local_native.snapshot', side_effect=AssertionError('native acquired')):
            with self.assertRaises(Refusal): self.authorize()
        self.authorize()

    def test_newer_epoch_never_restamps_existing_job_or_attempt(self):
        self.new_job()
        before = self.store.job(self.job['id']), self.store.attempt(self.attempt)
        prospective.revoke(self.store, self.issuer, self.epoch_receipt['id'])
        self.epoch()
        with self.assertRaises(Refusal): self.authorize()
        self.assertEqual((self.store.job(self.job['id']), self.store.attempt(self.attempt)), before)
        self.assert_originals()

    def test_collected_revision_keeps_downstream_proof_without_relaunch_credit(self):
        self.new_job()
        from support import collect, result
        # Explicit synthetic collection seam, never actual worker/END proof.
        collect(self.store, self.attempt, result(), tool_completion=dict(complete=True, items=[]))
        self.catalog.write_text(encode(dict(a=dict(id='a', owner='fixture', state='later'))))
        self.boards['Work']._software_job_grant(self.store, self.store.job(self.job['id']))
        self.assertIsNone(self.store.one('SELECT processed_at FROM events WHERE id=?', (self.source['id'],))['processed_at'])
        self.assertEqual(self.store.enrollment('Branch')['legacy_hold'], 'unrelated UNKNOWN')

    def test_previously_collected_unbound_failure_cannot_gain_authority(self):
        self.new_job(bind=False)
        self.store.collect(self.attempt, dict(exit=None, capture='not-started', cleanup='no-session-created',
            result=None, error='historical jobs/members cannot inherit future authority',
            detail=dict(known_not_started=True, resume_disposition='unavailable-before-owned-start')))
        before = self.store.job(self.job['id']), self.store.attempt(self.attempt)
        self.assertIsNone(prospective.for_job(self.store, self.store.job(self.job['id'])))
        with self.assertRaises(Refusal): self.authorize()
        with self.assertRaises(Refusal):
            self.boards['Work'].bind_software_attempt(self.store, self.store.job(self.job['id']), self.attempt, None)
        self.assertEqual((self.store.job(self.job['id']), self.store.attempt(self.attempt)), before)

    def test_no_explicit_selected_mode_or_ordinary_permission(self):
        self.new_job()
        row = self.store.one('SELECT selection FROM processing_capabilities WHERE id=?', (self.cap,))
        choice = json.loads(row['selection'])
        for field, value in [('mode', 'future-only'), ('selected_retained', [])]:
            changed = copy.deepcopy(choice); changed['basis'][field] = value
            self.store.db.execute('UPDATE processing_capabilities SET selection=? WHERE id=?', (encode(changed), self.cap))
            with self.subTest(field=field), self.assertRaises(Refusal): self.authorize()
        self.store.db.execute('UPDATE processing_capabilities SET selection=? WHERE id=?', (row['selection'], self.cap))
        epoch = self.store.one('SELECT selection FROM prospective_authorities WHERE id=?', (self.epoch_receipt['id'],))
        changed = json.loads(epoch['selection']); changed['tasks']['work-integrator']['ordinary_effects'] = True
        self.store.db.execute('UPDATE prospective_authorities SET selection=? WHERE id=?', (encode(changed), self.epoch_receipt['id']))
        with self.assertRaises(Refusal): self.authorize()


class ProposerLaunch(Fixture):
    configure = RetainedLaunch.configure
    basis = RetainedLaunch.basis
    issue = RetainedLaunch.issue
    epoch = RetainedLaunch.epoch
    new_job = RetainedLaunch.new_job
    authorize = RetainedLaunch.authorize
    assert_originals = RetainedLaunch.assert_originals
    test_new_selected_proposer_reaches_real_launch_guard = RetainedLaunch.test_new_selected_job_reaches_real_launch_guard_without_source_renewal

    def route_receipt(self):
        return {**selected.LocalSelectedBasis.route_receipt(self), 'task':'work-proposer'}

    def setUp(self):
        self.bootstrap(self.configure)
        self.select(dict(max_inflight=8, reviews={}, legacy_resources={}))
        self.oldcap = self.cap
        self.source = self.post('Work', 'work-proposer', None)
        self.issuer = self.config['roles']['Work']['owner']
        self.mapping = self.store.resolve_input(self.source['id'], self.issuer, self.route_receipt())
        self.classify(task='work-proposer')
        self.other = self.post('Branch', 'branch-proposer', None)
        self.store.set_hold(self.other['id'], 'unrelated private capture/effect/consumer UNKNOWN')
        self.store.db.execute("UPDATE enrollments SET legacy_hold='unrelated UNKNOWN' WHERE role='Branch'")
        with actor(self.boards['Work'].store, self.issuer):
            processing.revoke(self.store, self.boards, self.oldcap)
        self.expected = dict(event=self.source['id'], role='Work', source_hash=digest(self.source),
            source_birth=self.store.one('SELECT position FROM processing_source_positions WHERE event=?', (self.source['id'],))['position'],
            task='work-proposer', mapping_version=self.mapping['version'])
        choice = selected.LocalSelectedBasis.selection(self)
        choice['input_mappings'] = ['work-proposer']
        self.cap = self.issue(choice)
        self.store.processing = processing.Access(self.store, self.cap, self.boards)
        with actor(self.boards['Work'].store, self.issuer):
            self.current_mapping = processing.map_input(self.store, self.boards, self.cap,
                self.source['id'], self.issuer, self.route_receipt())
        self.classify(task='work-proposer')
        self.originals = {t:self.store.rows('SELECT * FROM '+t) for t in (
            'events', 'processing_source_positions', 'enrollments', 'input_resolutions', 'outboxes')}


if __name__ == '__main__':
    unittest.main(verbosity=2)
