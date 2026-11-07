"""Current typed observations in newly owned public SDK fiction; no live journal."""
import json
from unittest.mock import patch
from test_collected_report593 import Reports
from test_software_consumption import fixture_actor
from coordinator_runtime import processing, local_integration as local
from support import queued
from coordinator_runtime.contracts import encode, ident, Refusal


class Outcomes(Reports):
    def view(self, source):
        state = self.store.one('SELECT hash,role FROM events WHERE id=?', (source['id'],))
        queue = self.store.one('SELECT task,phase,state,job FROM queue WHERE event=?', (source['id'],))
        return processing.reservation_observation(self.store, None, source['id'], state, queue, self.store.controller)

    def test_first_false_is_observed_without_evaluating_skipped_guards(self):
        source = self.source()
        # Negative-only disabled enrollment; intake/classification already genuine.
        self.store.db.execute("UPDATE enrollments SET intake=0 WHERE role='Work'")
        with patch.object(self.store, 'execution_complete', side_effect=AssertionError('skipped guard acquired')):
            self.assertIsNone(self.store.reserve())
        view = self.view(source)
        self.assertIsNotNone(view)
        self.assertEqual(view['outcome'], 'false')
        self.assertEqual(view['predicate'], 'role-enabled')
        self.assertTrue(view['current'])
        self.assertEqual(self.store.rows('SELECT id FROM jobs'), [])
        self.assertEqual(len(self.store.rows('SELECT id FROM attempts')), 1)

    def test_positive_is_actual_reservation_not_a_fake_attempt(self):
        source = self.source()
        before = self.store.rows('SELECT id FROM attempts')
        job = self.store.reserve()
        self.assertIsNotNone(job)
        self.assertEqual(json.loads(job['members'])[0]['event'], source['id'])
        view = self.view(source)
        self.assertEqual((view['outcome'], view['predicate']), ('reserved', 'reservation'))
        self.assertTrue(view['current'])
        self.assertEqual(view['mapping_version'], 1)
        self.assertEqual(self.store.rows('SELECT id FROM attempts'), before)
        self.assertEqual(self.store.rows('SELECT * FROM file_publications'), [])

    def test_held_candidate_is_not_evaluated_and_does_not_acquire_body(self):
        source = self.source()
        self.store.set_hold(source['id'], 'fictional privacy hold')
        with patch.object(self.store, 'event', side_effect=AssertionError('held body acquired')):
            self.assertIsNone(self.store.reserve())
            view = self.view(source)
        self.assertEqual(view['outcome'], 'not-evaluated')
        self.assertIsNone(view['predicate'])
        self.assertEqual(self.store.rows('SELECT id FROM jobs'), [])

    def test_actual_members_refusal_keeps_no_job_and_exact_context(self):
        _, _, report, _ = self.producer()
        self.store.db.execute("UPDATE attempts SET capture='incomplete' WHERE id=?", (report['source_attempt'],))
        before = self.store.rows('SELECT id FROM jobs')
        self.assertIsNone(self.store.reserve())
        view = self.view(report)
        self.assertEqual((view['outcome'], view['predicate']), ('refusal', 'members'))
        self.assertEqual(view['source'], report['id'])
        self.assertEqual(view['phase'], 'integrator')
        self.assertEqual(view['observed'], 1000.)
        self.assertEqual(self.store.rows('SELECT id FROM jobs'), before)

    def test_propagated_refusal_is_same_exception_and_survives_rollback(self):
        source = self.source()
        refusal = Refusal('fictional private error must not enter typed observation')
        with patch.object(self.store, 'role_enabled', side_effect=refusal) as guard:
            with self.assertRaises(Refusal) as caught:
                self.store.reserve()
        self.assertIs(caught.exception, refusal)
        self.assertEqual(guard.call_count, 1)
        view = self.view(source)
        self.assertEqual((view['outcome'], view['predicate']), ('refusal', 'role-enabled'))
        self.assertNotIn('private', encode(view))
        self.assertEqual(self.store.rows('SELECT id FROM jobs'), [])

    def test_exact_identity_mismatches_withhold_old_identity_and_reason(self):
        source = self.source(); self.assertIsNotNone(self.store.reserve())
        original = self.store.one('SELECT * FROM reservation_outcomes WHERE event=?', (source['id'],))
        for field, value in [('task','foreign-task'), ('phase','foreign-phase'), ('source_hash','foreign-hash'),
                             ('controller',ident()), ('capability',ident()), ('mapping_version',42), ('queue','foreign-queue')]:
            with self.subTest(field=field):
                self.store.db.execute('UPDATE reservation_outcomes SET '+field+'=? WHERE event=?', (value, source['id']))
                view = self.view(source)
                self.assertEqual(view['outcome'], 'stale'); self.assertFalse(view['current'])
                self.assertIsNone(view['reason']);self.assertNotIn(str(value), encode(view))
                self.store.db.execute('UPDATE reservation_outcomes SET '+field+'=? WHERE event=?', (original[field], source['id']))

    def test_malformed_unrecognized_reason_and_raw_sentinels_are_not_acquired(self):
        import sqlite3
        source = self.source(); self.assertIsNotNone(self.store.reserve())
        # Raw strings are deliberately placed only in new fictional protected
        # columns. SQLite authorizer prevents their acquisition by the view.
        sentinel = 'RAW_ERROR_MODEL_CAPTURE_SENTINEL_50103'
        self.store.db.execute('UPDATE attempts SET error=?,result=?,detail=?', (sentinel,sentinel,sentinel))
        self.store.db.execute("INSERT INTO operational_errors VALUES(?,'Work','local-integration-dependency',?,1,1000)",
                              (source['id'], encode({'dependency':sentinel})))
        original = self.store.one('SELECT * FROM reservation_outcomes WHERE event=?', (source['id'],))
        denied = []
        def authorize(action, table, column, db, caller):
            if action == sqlite3.SQLITE_READ and ((table in {'attempts','results','operational_errors'})
                    or (table=='events' and column=='payload')):
                denied.append((table,column));return sqlite3.SQLITE_DENY
            return sqlite3.SQLITE_OK
        self.store.db.set_authorizer(authorize)
        try:
            with patch.object(self.store, 'event', side_effect=AssertionError('diagnostic body acquired')):
                self.assertTrue(self.view(source)['current'])
                for field, value in [('predicate',sentinel),('predicate','{malformed'),('outcome',sentinel),
                                     ('schema_version',22),('observed',sentinel),('predicate','role-enabled')]:
                    self.store.db.execute('UPDATE reservation_outcomes SET '+field+'=? WHERE event=?', (value,source['id']))
                    view = self.view(source)
                    self.assertEqual(view['outcome'],'unknown');self.assertIsNone(view['reason'])
                    self.assertNotIn(sentinel,encode(view))
                    self.store.db.execute('UPDATE reservation_outcomes SET '+field+'=? WHERE event=?', (original[field],source['id']))
        finally:
            self.store.db.set_authorizer(None)
        self.assertEqual(denied, [])

    def test_reached_execution_capacity_is_false_and_short_circuits_members(self):
        for _ in range(5):
            self.source(); self.assertIsNotNone(self.store.reserve())
        source = self.source()
        with patch.object(local, 'members', side_effect=AssertionError('unreached members')):
            self.assertIsNone(self.store.reserve())
        self.assertEqual((self.view(source)['outcome'], self.view(source)['predicate']), ('false','execution-capacity'))
        self.assertEqual(len(self.store.rows('SELECT id FROM jobs')),5)

    def test_local_capacity_is_the_reached_false_not_phase_capacity(self):
        for role, task, count in [('Work','work-proposer',5),('Reviews','reviews-proposer',3)]:
            for _ in range(count):
                self.source(role,task); self.assertIsNotNone(self.store.reserve())
        source = self.source(task='work-integrator')
        self.assertIsNone(self.store.reserve())
        self.assertEqual((self.view(source)['outcome'],self.view(source)['predicate']),('false','local-capacity'))
        self.assertEqual(len(self.store.rows('SELECT id FROM jobs')),8)

    def test_unknown_material_fence_keeps_original_job_unknown(self):
        self.source(); prior = self.store.reserve()
        # Negative-only removal of its frozen map, never positive permission.
        self.store.db.execute('DELETE FROM local_jobs WHERE job=?', (prior['id'],))
        source = self.source(task='work-integrator')
        self.assertIsNone(self.store.reserve())
        self.assertEqual(self.view(source)['predicate'], 'local-unknown-material')
        self.assertEqual(self.store.job(prior['id']), prior)
        self.assertEqual(self.view(source)['outcome'],'false')

    def test_processing_source_public_projection_uses_exact_current_controller(self):
        self.processing_mode()
        source=self.source()
        self.store.db.execute('INSERT INTO processing_runs VALUES(?,?,?,?)',(self.store.controller,self.key,'owned',1000.))
        self.store.db.execute('INSERT INTO service_runs VALUES(?,?,?,?,?,?,?)',
            (self.store.controller,self.key,'fictional-unused-endpoint','serving',1000.,None,None))
        before = processing.reservation_diagnostics(self.store,self.boards,self.key,source['id'])
        self.assertEqual(before['reservation']['outcome'],'not-evaluated')
        self.assertIsNotNone(self.store.reserve())
        after = processing.reservation_diagnostics(self.store,self.boards,self.key,source['id'])
        self.assertTrue(after['reservation']['current'])
        self.assertEqual(after['reservation']['capability'],self.key)
        self.assertEqual(after['reservation']['mapping_version'],1)
        self.store.db.execute('UPDATE reservation_outcomes SET mapping_version=0 WHERE event=?',(source['id'],))
        stale=processing.reservation_diagnostics(self.store,self.boards,self.key,source['id'])
        self.assertEqual(stale['reservation']['outcome'],'stale')

    def test_reservation_only_CLI_is_read_only_and_never_acquires_raw_fields(self):
        import sqlite3
        from coordinator_runtime import cli
        self.processing_mode(); source=self.source()
        self.store.db.execute('INSERT INTO processing_runs VALUES(?,?,?,?)',(self.store.controller,self.key,'owned',1000.))
        self.store.db.execute('INSERT INTO service_runs VALUES(?,?,?,?,?,?,?)',
            (self.store.controller,self.key,'fictional-unused-endpoint','serving',1000.,None,None))
        self.assertIsNotNone(self.store.reserve())
        sentinel='RAW50103_NEVER_ACQUIRE'
        self.store.db.execute('UPDATE attempts SET error=?,result=?,detail=?', (sentinel,sentinel,sentinel))
        self.store.db.execute("INSERT INTO operational_errors VALUES(?,'Work','local-integration-dependency',?,1,1000)",(source['id'],sentinel))
        self.store.db.execute('UPDATE events SET error=? WHERE id=?',(sentinel,source['id']))
        denied=[]
        def authorize(action, table, column, db, caller):
            if action == sqlite3.SQLITE_READ and (table in {'attempts','results','operational_errors'}
                    or (table=='events' and column in {'payload','error'})):
                denied.append((table,column));return sqlite3.SQLITE_DENY
            if action in {sqlite3.SQLITE_INSERT,sqlite3.SQLITE_UPDATE,sqlite3.SQLITE_DELETE}:
                raise AssertionError('read-only projection attempted mutation')
            return sqlite3.SQLITE_OK
        self.store.db.set_authorizer(authorize)
        try:
            args=cli.parser().parse_args(['processing-source',self.key,source['id'],'--reservation-only'])
            # CLI constructs fresh SDK modules; use the inherited CLI fixture's
            # fictional caller environment only inside this new owned test.
            with patch.dict('os.environ', {'CODEX_SESSION_ID': self.actor}), patch.object(self.store,'event',side_effect=AssertionError('protected source acquired')):
                view=cli.operate(args,self.store)
            self.assertEqual(view['reservation']['outcome'],'reserved')
            self.assertNotIn(sentinel,encode(view))
        finally:
            self.store.db.set_authorizer(None)
        self.assertEqual(denied,[])

    def test_direct_view_rechecks_changed_queue_and_source_metadata(self):
        source=self.source();self.assertIsNotNone(self.store.reserve())
        state=self.store.one('SELECT hash,role FROM events WHERE id=?',(source['id'],))
        responsibility=self.store.one('SELECT task,phase,state,job FROM queue WHERE event=?',(source['id'],))
        for field,value in [('task','work-integrator'),('phase','integrator')]:
            self.store.db.execute('UPDATE queue SET '+field+'=? WHERE event=?',(value,source['id']))
            view=processing.reservation_observation(self.store,None,source['id'],state,responsibility,self.store.controller)
            self.assertEqual(view['outcome'],'stale');self.assertIsNone(view['predicate'])
            self.store.db.execute('UPDATE queue SET '+field+'=? WHERE event=?',(responsibility[field],source['id']))
        self.store.db.execute('UPDATE events SET hash=? WHERE id=?',('changed-own-fictional-hash',source['id']))
        with patch.object(self.store,'event',side_effect=AssertionError('body acquired')):
            view=processing.reservation_observation(self.store,None,source['id'],state,responsibility,self.store.controller)
        self.assertEqual(view['outcome'],'stale');self.assertIsNone(view['reason'])
