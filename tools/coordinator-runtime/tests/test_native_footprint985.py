"""Active production Source lifecycle; fictional transport, no provider or live journal.

The suspended transport has no answer/END. Real reservation, launch binding,
Executor material/context/facade and resource comparison run in an owned sandbox.
"""
import asyncio
import copy
from contextlib import contextmanager, ExitStack
import json
import sqlite3
from pathlib import Path
import unittest
from unittest.mock import patch

from test_unpackaged_native889 import Unpackaged889
from _receiving485_fixtures import FictionalNativeTransport
from coordinator_runtime import prospective, resource_scopes, reviews, review_reader, report_scope
from coordinator_runtime.contracts import Refusal, digest, encode


class SuspendedTransport(FictionalNativeTransport):
    async def call(self, runtime, attempt, policy, context, directory, text, commands, **options):
        runtime.authorize_launch(attempt)
        # The production Executor has already published its facade and frozen
        # original call/context. No fabricated collected receipt is installed.
        runtime.begin(attempt, {'fictional_active_native_transport': True})
        directory.mkdir(parents=True)
        with runtime.tx():
            runtime.db.execute("UPDATE review_calls SET state='launch-intent' WHERE attempt=?", (attempt,))
        self.started = True
        await asyncio.Future()


class ActiveSource985(Unpackaged889):
    def configure_fixture(self):
        super().configure_fixture()
        self.config['artifact_exclusions'] = json.loads(Path('/public/exclusions.json').read_text())
        self.assertEqual(len(self.config['artifact_exclusions']),71)
        self.independent = self.area/'independent'
        self.independent.mkdir()
        self.independent_report = self.independent/'collected-report.json'
        self.independent_report.write_text('{"attribution":"independent fictional collected report"}')
        # Preserve the real tasks, grants and typed access policy. Remove only
        # the fixture's broad shared cwd/read ceiling so disjointness is factual.
        for name, task in self.config['tasks'].items():
            task['cwd'] = str(self.independent)
            task['effect_authority']['read_roots'] = [str(self.repo), str(self.method), str(self.independent)]
        source = self.config['tasks']['reviews-proposer']
        source['cwd'] = str(self.repo)
        source['effect_authority']['read_roots'] = [str(self.repo), str(self.method)]

    def configure_selection(self, selected):
        super().configure_selection(selected)
        policy = selected['service']['reviews']['reviews-proposer']
        policy['caller'] = '/public/caller.py'
        policy['caller_sha256'] = reviews.RESOURCE_CALLER_SHA256
        selected['service']['legacy_resources']['Reviews']['native_review_return']['review_policy_sha256'] = digest(policy)

    @contextmanager
    def active(self):
        self.init_native()
        prospective.select(self.store, self.config['roles']['Work']['owner'], dict(
            configuration=digest(self.config), authority='Fictional original active Source authority',
            expires=self.store.clock()+600, processing_capability=self.key,
            grants={r:self.store.enrollment(r)['grant_id'] for r in self.config['roles']},
            tasks={n:dict(task_hash=digest(t),software_handoffs={},ordinary_effects=False)
                   for n,t in self.config['tasks'].items()}))
        self.e = self.source_event()
        self.initial[self.e['id']] = 'reviews-proposer'
        asyncio.run(self.phase('schedule_classifications'))
        job = self.store.reserve()
        self.assertEqual(job['task'], 'reviews-proposer')
        self.attempt_id = self.store.start_job(job['id'], job['token'])
        self.job = self.store.job(job['id'])
        self.identity = dict(id=job['id'], task=job['task'])
        self.dispatch.reviews.transport = self.transport = SuspendedTransport()
        loop = asyncio.new_event_loop()
        running = loop.create_task(self.dispatch.execute_review(job, self.attempt_id, self.e['body']['review']))
        async def until_started():
            while not getattr(self.transport, 'started', False):
                if running.done():
                    await running
                    self.fail('Source completed before active fixture boundary')
                await asyncio.sleep(0)
        try:
            loop.run_until_complete(until_started())
            self.assertIsNone(self.store.attempt(self.attempt_id)['ended'])
            self.assertEqual(self.store.job(job['id'])['effects'], 'unknown')
            yield
        finally:
            running.cancel()
            loop.run_until_complete(asyncio.gather(running, return_exceptions=True))
            loop.close()

    def candidate(self, role='Work', task=None):
        name = task or dict(Work='work-integrator',QA='qa-execution',Branch='branch-integrator')[role]
        return dict(role=role, phase=self.config['tasks'][name]['phase'], task=name, package=None)

    def modes(self):
        return resource_scopes.original_modes(self.store, self.identity)

    @contextmanager
    def no_bodies(self):
        with ExitStack() as stack:
            original_one = self.store.one
            def one(sql,args=()):
                if '$.body.review' in sql and original_one('SELECT hold FROM events WHERE id=?',(self.e['id'],))['hold']:
                    raise AssertionError('held factual packet acquired before scalar admission')
                return original_one(sql,args)
            stack.enter_context(patch.object(self.store,'one',side_effect=one))
            for name in ('event', 'attempt'):
                stack.enter_context(patch.object(self.store, name, side_effect=AssertionError('protected body acquired')))
            stack.enter_context(patch.object(reviews, 'collected_proof', side_effect=AssertionError('premature collection proof')))
            stack.enter_context(patch.object(reviews, 'handle_run', side_effect=AssertionError('native handle acquired')))
            yield

    def test_active_disjoint_QA_Work_and_independent_report_read_read(self):
        with self.active():
            before = self.store.one('SELECT state,effects,active_attempt FROM jobs WHERE id=?', (self.job['id'],))
            with self.no_bodies():
                reads,writes,staging = self.modes()
                for role in ('QA','Work','Branch'):
                    with self.subTest(role=role):
                        self.assertFalse(resource_scopes.blocked(self.store, self.candidate(role)))
            self.assertIn(self.repo, reads)
            self.assertEqual(staging, [self.store.home/'artifacts'/self.attempt_id])
            self.assertIn(staging[0], writes)
            self.assertEqual(before, self.store.one('SELECT state,effects,active_attempt FROM jobs WHERE id=?', (self.job['id'],)))
            self.assertIsNone(self.store.attempt(self.attempt_id)['collected'])
            self.assertIsNone(self.store.job(self.job['id'])['response'])
            self.assertEqual(self.store.rows('SELECT * FROM review_history_commits'), [])

    def test_actual_reader_mutable_files_and_all_held_writes_conflict(self):
        with self.active():
            reads,writes,staging = self.modes()
            facade = self.store.home/'review-inputs'/digest(self.component889)/'material.json'
            # Run the actual reader through history + method. It creates exactly
            # the cursor/item paths charged by the native footprint.
            review_reader.next_chunk(facade)
            review_reader.next_chunk(facade)
            self.assertTrue(facade.with_suffix('.cursor').exists())
            self.assertTrue(facade.with_suffix('.item').exists())
            for suffix in ('.pending','.cursor','.item'):
                self.assertIn(facade.with_suffix(suffix),writes)
            self.assertTrue(any(p.parent == self.store.home/'review-handles' for p in writes))
            self.assertTrue(any(p.is_relative_to(self.store.home/'review-history') for p in writes))
            candidate = self.candidate('Work')
            original = self.config['tasks'][candidate['task']]
            for held in list(dict.fromkeys(writes + [staging[0].parent, self.repo, self.method])):
                for mode in ('read','write'):
                    if mode == 'read' and held in (self.repo,self.method):
                        continue
                    task = copy.deepcopy(original)
                    task.pop('routine_completion',None)
                    task['effect_authority']['read_roots'] = [str(self.independent)] + ([str(held)] if mode=='read' else [])
                    task['effect_authority']['write_roots'] = [str(held)] if mode=='write' else []
                    with self.subTest(resource=str(held),mode=mode), self.no_bodies():
                        self.assertTrue(resource_scopes.blocked(self.store,candidate,task))

    def test_original_authority_faults_refuse_without_bodies(self):
        with self.active():
            self.modes()
            self.assertFalse(resource_scopes.blocked(self.store,self.candidate()))
            faults = [
                ("UPDATE attempts SET detail=json_set(detail,'$.processing_capability','wrong') WHERE id=?",self.attempt_id),
                ("UPDATE attempts SET detail=json_set(detail,'$.software_authority.prospective_epoch','wrong') WHERE id=?",self.attempt_id),
                ("UPDATE attempts SET detail=json_set(detail,'$.software_authority.grant_id','wrong') WHERE id=?",self.attempt_id),
                ("UPDATE attempts SET detail=json_set(detail,'$.software_authority.task_hash','wrong') WHERE id=?",self.attempt_id),
                ("UPDATE attempts SET detail=json_set(detail,'$.software_authority.admission_hash','wrong') WHERE id=?",self.attempt_id),
                ("UPDATE attempts SET detail=json_remove(detail,'$.software_authority') WHERE id=?",self.attempt_id),
                ("UPDATE attempts SET detail=json_set(detail,'$.software_authority','opaque') WHERE id=?",self.attempt_id),
                ("UPDATE jobs SET members=json_set(members,'$[0].hash','wrong') WHERE id=?",self.job['id']),
                ("UPDATE events SET hold='held' WHERE id=?",self.e['id']),
                ("UPDATE processing_source_positions SET position=0 WHERE event=?",self.e['id']),
                ("UPDATE events SET payload=json_set(payload,'$.body.review.head','0000000000000000000000000000000000000000') WHERE id=?",self.e['id']),
                ("UPDATE review_calls SET packet=json_set(packet,'$.method_files','wrong') WHERE attempt=?",self.attempt_id),
                ("UPDATE review_calls SET packet=json_set(packet,'$.source',json('{}')) WHERE attempt=?",self.attempt_id),
                ("UPDATE review_calls SET packet=json_set(packet,'$.history_sha256','wrong') WHERE attempt=?",self.attempt_id),
                ("UPDATE review_calls SET packet=json_set(packet,'$.selected_task','old-Source853') WHERE attempt=?",self.attempt_id),
                ("UPDATE review_call_contexts SET context=json_set(context,'$.collector','wrong') WHERE attempt=?",self.attempt_id),
                ("UPDATE review_contexts SET collector='wrong' WHERE component=?",self.component889),
                ("UPDATE review_contexts SET capability='wrong' WHERE component=?",self.component889),
                ("UPDATE prospective_authorities SET revoked=1 WHERE id=(SELECT json_extract(detail,'$.software_authority.prospective_epoch') FROM attempts WHERE id=?)",self.attempt_id),
            ]
            # The existing original-map triggers themselves forbid rewrite.
            with self.assertRaisesRegex(sqlite3.IntegrityError, 'immutable original'):
                self.store.db.execute("UPDATE job_resource_policies SET task='{}' WHERE job=?",(self.job['id'],))
            for changed in [dict(network=True), dict(effects='owner-reconcile'),
                            dict(routine_completion={'targets':[]}),
                            dict(admitted_scope={'ordinary_effects':{'kind':'local-qa'}})]:
                task=copy.deepcopy(self.config['tasks']['reviews-proposer']);task.update(changed)
                with self.store.tx(), self.assertRaises(Refusal):
                    reviews.original_resources(self.store,self.identity,task)
            for key,value in [('write_roots',['/unmapped-write']),('operations',['execute-admitted-qa'])]:
                task=copy.deepcopy(self.config['tasks']['reviews-proposer']);task['effect_authority'][key]=value
                with self.store.tx(), self.assertRaises(Refusal):reviews.original_resources(self.store,self.identity,task)
            with self.assertRaisesRegex(Refusal,'missing original frozen'):
                resource_scopes.original_modes(self.store,dict(id='old-opaque-source853',task='reviews-proposer'))
            faults.append(("UPDATE prospective_job_positions SET position=0 WHERE job=?",self.job['id']))
            for sql,key in faults:
                with self.subTest(fault=sql):
                    self.store.db.execute('SAVEPOINT fault985')
                    try:
                        self.store.db.execute(sql,(key,))
                        with self.no_bodies(), self.assertRaises(Refusal):self.modes()
                        with self.no_bodies():self.assertTrue(resource_scopes.blocked(self.store,self.candidate()))
                    finally:
                        self.store.db.execute('ROLLBACK TO fault985');self.store.db.execute('RELEASE fault985')

    def test_publications_leases_later_holders_and_native_staging_exception(self):
        with self.active():
            candidate = self.candidate()
            self.assertFalse(resource_scopes.blocked(self.store,candidate))
            # The retained publication tail must run even for native effects=none.
            self.store.db.execute('SAVEPOINT pubs985')
            try:
                self.store.db.execute("INSERT INTO file_publications(attempt,target,temp,state) VALUES(?,?,?,'prepared')",
                    (self.attempt_id,str(self.catalog),str(self.independent/'publication.tmp')))
                self.assertTrue(resource_scopes.blocked(self.store,candidate))
                self.store.db.execute("UPDATE jobs SET effects='reconciled' WHERE id=?",(self.job['id'],))
                self.assertTrue(resource_scopes.blocked(self.store,candidate))
                self.assertIn(self.independent/'publication.tmp',self.modes()[1])
            finally:
                self.store.db.execute('ROLLBACK TO pubs985');self.store.db.execute('RELEASE pubs985')
            self.store.db.execute("INSERT INTO ordinary_resources VALUES('unknown985','orphan985')")
            self.assertTrue(resource_scopes.blocked(self.store,candidate))
            self.store.db.execute("DELETE FROM ordinary_resources WHERE resource='unknown985'")
            # A later opaque holder cannot be skipped after the native map passes.
            self.store.db.execute("UPDATE jobs SET effects='unknown' WHERE id=?",(self.job['id'],))
            self.store.db.execute('SAVEPOINT later985')
            try:
                self.store.db.execute("INSERT INTO jobs(id,role,phase,task,state,token,members,effects,created,controller) SELECT 'opaque-source853',role,phase,task,state,token,members,effects,created,controller FROM jobs WHERE id=?",(self.job['id'],))
                self.assertTrue(resource_scopes.blocked(self.store,candidate))
            finally:
                self.store.db.execute('ROLLBACK TO later985');self.store.db.execute('RELEASE later985')

    def test_exclusion_first_symlink_identity_and_no_premature_return(self):
        with self.active():
            facade = self.store.home/'review-inputs'/digest(self.component889)/'material.json'
            # Excluded publication discovered at the common tail must refuse
            # before metadata of ANY proposed native resource.
            original_rows = self.store.rows
            def rows(sql,args=()):
                if sql.startswith('SELECT p.target,p.temp'):
                    return [dict(target=str(self.independent/'excluded'),temp=None)]
                return original_rows(sql,args)
            # Keep the authenticated current config and all 71 inherited holds.
            # The additional fixture exclusion is injected only at root validation.
            original_root = resource_scopes.root
            def root(value, exclusions=(), *, metadata=True):
                if metadata:raise AssertionError('map metadata before whole-map exclusion')
                return original_root(value,[*exclusions,str(self.independent/'excluded')],metadata=False)
            with patch.object(self.store,'rows',side_effect=rows), patch.object(resource_scopes,'root',side_effect=root):
                with self.assertRaisesRegex(Refusal,'excluded'):self.modes()
            alias=self.independent/'alias';alias.symlink_to(self.repo,target_is_directory=True)
            task=copy.deepcopy(self.config['tasks']['work-integrator']);task['effect_authority']['write_roots']=[str(alias)]
            self.assertTrue(resource_scopes.blocked(self.store,self.candidate(),task))
            hardlink=self.independent/'same-method-inode';hardlink.hardlink_to(self.method)
            task['effect_authority']['write_roots']=[str(hardlink)]
            self.assertTrue(resource_scopes.blocked(self.store,self.candidate(),task))
            with patch.object(Path,'samefile',return_value=True):
                self.assertTrue(resource_scopes.blocked(self.store,self.candidate()))
            with patch.object(resource_scopes,'overlaps',side_effect=OSError('identity unavailable')):
                self.assertTrue(resource_scopes.blocked(self.store,self.candidate()))
            # Mapping a holder never makes its pending report consumable.
            row=dict(role='Reviews',phase='integrator',task='reviews-integrator',package=None,event=self.e['id'])
            with self.assertRaises(Refusal):report_scope.integration_inputs(self.store,row)
            self.assertIsNone(self.store.job(self.job['id'])['response'])
            self.assertIsNone(self.store.attempt(self.attempt_id)['collected'])


def load_tests(loader, tests, pattern):
    return unittest.TestSuite(ActiveSource985(name) for name in ActiveSource985.__dict__ if name.startswith('test_'))
