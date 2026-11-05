"""Prospective job binding across separately qualified fictional retirement.

Positive-mount sourceRO/privatefiction/networkOFF only. Real reservation, epoch,
retirement and software binding execute; NULL-native collection and simulated
clocks/custodian receipts never qualify actual processing, consent or 24h age.
"""
import json
import sqlite3
import unittest
from unittest.mock import patch

from coordinator_runtime import processing, prospective, retirement, windows
from coordinator_runtime.capacity import HOLDS
from coordinator_runtime.cleanup import sweep
from coordinator_runtime.contracts import Refusal, digest, encode
from coordinator_runtime.store import Store
import test_allocation332 as allocation
import test_response_birth337 as event_birth


class JobBirth(unittest.TestCase):
    def setUp(self):
        self.c = allocation.Continuing(methodName='runTest')
        self.addCleanup(self.c.doCleanups)
        self.c.setUp()
        self.c.adopt()
        self.s, self.f = self.c.s, self.c.f
        self.missing_history={**self.f.originals[0],'id':'fictional-missing-history342'}
        with self.s.tx():
            self.s.db.execute('INSERT INTO events(id,role,payload,hash,received,hold) VALUES(?,?,?,?,900,?)',
                              (self.missing_history['id'],'Work',encode(self.missing_history),
                               digest(self.missing_history),'fictional historical hold'))
        # Reuse synthetic collection/classification and original-row oracles,
        # without Birth337's different (pre-selection) retirement setup.
        self.h = event_birth.Birth(methodName='runTest')
        self.h.c, self.h.s, self.h.f = self.c, self.s, self.f
        self.h.originals = {t:self.s.rows('SELECT * FROM '+t) for t in
                            ('events','processing_source_positions','outboxes','enrollments','jobs','attempts')}
        self.h.grants = {t:[tuple(r) for r in self.f.conn.execute('SELECT * FROM '+t)]
                         for t in ('coordinator_grants_v1','coordinator_software_grants_v1')}
        self.key = self.c.issue()
        self.h.key = self.key
        self.cohorts = []

    def new_job(self, name, bind=True):
        source = self.h.new(name)
        self.h.classify(source['id'], 'wp')
        job = self.s.reserve()
        self.assertIsNotNone(job, 'genuine new input must reach real reservation')
        self.assertEqual([m['event'] for m in json.loads(job['members'])], [source['id']])
        attempt = self.s.start_job(job['id'], job['token'])
        if bind:
            self.bind(job, attempt)
        return source, self.s.job(job['id']), attempt

    def bind(self, job, attempt):
        self.f.boards['Work'].bind_software_attempt(self.s, self.s.job(job['id']), attempt, None)
        return json.loads(self.s.attempt(attempt)['detail'])['software_authority']

    def complete(self, job, attempt):
        self.h.collect(attempt, {'semantic':'DONE','category':'complete','summary':'fictional complete',
                                'findings':[],'failures':[],'unknowns':[],'artifacts':[],
                                'handoffs':[],'no_handoff_reason':'fictional no-effect work'}, tools=True)
        self.assertIsNone(self.s.finish_job(job['id'], job['token']))
        self.assertEqual(self.s.job(job['id'])['state'], 'closed')

    def aged_cohorts(self):
        for n in range(3):
            source, job, attempt = self.new_job('fictional-disposable342-'+str(n))
            self.complete(job, attempt)
            self.cohorts.append((source, job, attempt))
        # Age exists BEFORE epoch selection; no long-lived epoch is required.
        self.s.clock = lambda: 88000.
        sweep(self.s)
        self.assertTrue(all(self.s.one('SELECT state FROM events WHERE id=?',(e['id'],))['state']=='retired'
                            for e,_,_ in self.cohorts))

    def epoch(self):
        selected = {'configuration':digest(self.s.config),
                    'authority':'fictional Work continuing ordinary job temporal authority and why',
                    'expires':88500., 'processing_capability':self.key,
                    'grants':{'Work':self.s.enrollment('Work')['grant_id']},
                    'tasks':{'wp':{'task_hash':digest(self.s.config['tasks']['wp']),
                                   'software_handoffs':{},'ordinary_effects':False}}}
        self.selected = prospective.select(self.s, 'fictional-Work', selected)
        self.epoch_row = self.s.one('SELECT * FROM prospective_authorities WHERE id=?',(self.selected['id'],))
        return self.selected

    def receipt(self, source):
        basis = retirement.basis(self.s, source['id'])
        return {'basis':basis['basis'], 'qualified_at':self.s.clock(), 'holds':{h:[] for h in HOLDS},
                'evidence':'fictional all-custodian conservation; no actual consent or elapsed age',
                **{kind:{key:{'hash':value,'custodian':'fictional-custodian',
                               'evidence':'synthetic conservation only', 'disposition':'producer-owned-disposable'}
                          for key,value in basis[kind].items()} for kind in ('sources','results')}}

    def retire(self):
        for source,job,_ in self.cohorts:
            result = retirement.apply(self.s,source['id'],'fictional-Work',self.receipt(source))
            self.assertEqual(result['retired']['members']['jobs'],[job['id']])
        self.assertEqual(self.s.one('SELECT MAX(rowid) AS n FROM jobs')['n'],1)
        self.assertEqual(self.s.one('SELECT * FROM prospective_authorities WHERE id=?',(self.selected['id'],)),self.epoch_row)
        self.h.assert_originals()

    def snapshot(self):
        return {r['name']:self.s.rows('SELECT * FROM "'+r['name']+'"') for r in
                self.s.rows("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")} | {
                'sqlite_sequence':self.s.rows('SELECT * FROM sqlite_sequence')}

    def test_new_job_binds_after_aged_cohort_retirement_under_existing_epoch(self):
        self.aged_cohorts()
        self.epoch()
        self.retire()
        before = windows.current(self.s)
        source,job,attempt = self.new_job('fictional-new-after342-retirement',bind=False)
        physical = self.s.one('SELECT rowid AS n FROM jobs WHERE id=?',(job['id'],))['n']
        self.assertLessEqual(physical,self.selected['job_boundary'])
        self.assertGreater(prospective.event_position(self.s,source['id'],{'selection':{'processing_capability':self.key}}),self.selected['event_boundary'])
        self.assertEqual(self.f.boards['Work'].software_authority(self.s,'wp')['prospective_epoch'],self.selected['id'])
        # Baseline must reach THIS production binding and reject HERE, not setup.
        proof = self.bind(job,attempt)
        self.assertEqual(proof['prospective_epoch'],self.selected['id'])
        self.assertEqual(proof['processing_capability'],self.key)
        birth=self.s.one('SELECT position FROM prospective_job_positions WHERE job=?',(job['id'],))['position']
        self.assertGreater(birth,self.selected['job_boundary'])
        for _,retired,_ in self.cohorts:
            self.assertIsNone(self.s.one('SELECT * FROM prospective_job_positions WHERE job=?',(retired['id'],)))
        self.assertEqual(prospective.for_job(self.s,self.s.job(job['id']))['id'],self.selected['id'])
        self.assertTrue(prospective.requires_authority(self.s,self.s.job(job['id'])))
        used_before,used_after=json.loads(before['used']),json.loads(windows.current(self.s)['used'])
        self.assertEqual(used_after['jobs'],used_before['jobs']+1)
        self.assertEqual(windows.current(self.s)['new_inputs'],before['new_inputs']+1)
        self.complete(job,attempt)
        self.h.assert_originals()

    def test_without_retirement_new_job_binds_old_job_and_old_members_refuse(self):
        self.aged_cohorts(); self.epoch()
        for _,job,_ in self.cohorts:
            self.assertIsNone(prospective.for_job(self.s,self.s.job(job['id'])))
        source,job,attempt=self.new_job('fictional-normal342')
        self.assertEqual(prospective.for_job(self.s,job)['id'],self.selected['id'])
        original=job['members']
        old_member={'event':self.f.originals[0]['id'],'hash':digest(self.f.originals[0])}
        self.s.db.execute('UPDATE jobs SET members=? WHERE id=?',(encode([old_member]),job['id']))
        self.assertIsNone(prospective.for_job(self.s,self.s.job(job['id'])))
        self.s.db.execute('UPDATE jobs SET members=? WHERE id=?',(original,job['id']))
        # Missing event chronology still cannot promote historical membership.
        missing={'event':self.missing_history['id'],'hash':digest(self.missing_history)}
        self.s.db.execute('UPDATE jobs SET members=? WHERE id=?',(encode([missing]),job['id']))
        self.assertIsNone(prospective.for_job(self.s,self.s.job(job['id'])))
        self.assertIsNone(self.s.one('SELECT position FROM processing_source_positions WHERE event=?',(missing['event'],)))
        self.s.db.execute('UPDATE jobs SET members=? WHERE id=?',(original,job['id']))
        self.h.assert_originals()

    def test_legacy_epoch_frontier_survives_retirement_without_history_backfill(self):
        self.aged_cohorts();self.epoch()
        # Explicit legacy epoch shape from before observed-v1 existed.
        selected=json.loads(self.epoch_row['selection']);del selected['job_birth']
        self.s.db.execute('UPDATE prospective_authorities SET selection=? WHERE id=?',(encode(selected),self.selected['id']))
        self.epoch_row=self.s.one('SELECT * FROM prospective_authorities WHERE id=?',(self.selected['id'],))
        legacy_job=self.s.job('fictional-old-job')
        self.assertEqual(prospective.job_position(self.s,legacy_job,{'selection':selected}),1)
        self.assertIsNone(prospective.for_job(self.s,legacy_job))
        self.retire()
        source,job,attempt=self.new_job('fictional-legacy-epoch-new342')
        self.assertEqual(prospective.for_job(self.s,job)['id'],self.selected['id'])
        self.assertIsNone(self.s.one('SELECT * FROM prospective_job_positions WHERE job=?',(legacy_job['id'],)))
        self.assertTrue(prospective.requires_authority(self.s,job))
        self.h.assert_originals()

    def test_birth_missing_or_rollback_cannot_create_future_authority(self):
        self.epoch()
        source=self.h.new('fictional-rollback342');self.h.classify(source['id'],'wp')
        before=self.snapshot()
        self.s.db.execute("CREATE TEMP TRIGGER fictional_job_birth_refusal BEFORE INSERT ON prospective_job_positions BEGIN SELECT RAISE(ABORT,'fictional job birth refusal'); END")
        with self.assertRaisesRegex(sqlite3.IntegrityError,'job birth refusal'): self.s.reserve()
        self.assertEqual(self.snapshot(),before)
        self.s.db.execute('DROP TRIGGER fictional_job_birth_refusal')
        job=self.s.reserve();attempt=self.s.start_job(job['id'],job['token'])
        self.bind(job,attempt)
        self.s.db.execute('DELETE FROM prospective_job_positions WHERE job=?',(job['id'],))
        self.assertIsNone(prospective.for_job(self.s,self.s.job(job['id'])))
        self.assertTrue(prospective.requires_authority(self.s,self.s.job(job['id'])))
        with self.assertRaises(Refusal): self.f.boards['Work']._software_job_grant(self.s,self.s.job(job['id']))
        # Reopen does not backfill old/missing observations or alter old duties.
        from coordinator_runtime import store as module
        with patch.object(module,'SCHEMA',module.SCHEMA.replace('profile TEXT NOT NULL','profile TEXT')):
            reopened=Store(self.s.config,clock=self.s.clock)
        self.addCleanup(reopened.close)
        self.assertIsNone(reopened.one('SELECT * FROM prospective_job_positions WHERE job=?',(job['id'],)))
        self.assertIsNone(reopened.one('SELECT * FROM prospective_job_positions WHERE job=?',('fictional-old-job',)))
        self.h.assert_originals()

    def test_retention_hold_currentness_and_revocation_preserve_authority_debt(self):
        self.aged_cohorts();self.epoch()
        source,_,_=self.cohorts[0]
        receipt=self.receipt(source)
        self.s.db.execute('UPDATE events SET hold=? WHERE id=?',('fictional-new-hold',source['id']))
        before=self.snapshot()
        with self.assertRaises(Refusal):retirement.apply(self.s,source['id'],'fictional-Work',receipt)
        self.assertEqual(self.snapshot(),before)
        source,job,attempt=self.new_job('fictional-currentness342')
        detail=self.s.attempt(attempt)['detail']
        borrowed=json.loads(detail);borrowed['processing_capability']='fictional-foreign342'
        self.s.db.execute('UPDATE attempts SET detail=? WHERE id=?',(encode(borrowed),attempt))
        with self.assertRaises(Refusal):prospective.for_job(self.s,job)
        self.s.db.execute('UPDATE attempts SET detail=? WHERE id=?',(detail,attempt))
        grant=self.s.enrollment('Work')['grant_id']
        self.s.db.execute("UPDATE enrollments SET grant_id='fictional-foreign-grant' WHERE role='Work'")
        with self.assertRaises(Refusal):prospective.for_job(self.s,job)
        self.s.db.execute("UPDATE enrollments SET grant_id=? WHERE role='Work'",(grant,))
        with patch.object(processing,'implementation',return_value={'fictional':'stale'}):
            with self.assertRaises(Refusal):prospective.for_job(self.s,job)
        self.s.clock=lambda:88500.
        with self.assertRaisesRegex(Refusal,'expired'):prospective.for_job(self.s,job)
        self.s.clock=lambda:88000.
        prospective.revoke(self.s,'fictional-Work',self.selected['id'])
        with self.assertRaisesRegex(Refusal,'revoked'):prospective.for_job(self.s,job)
        self.assertTrue(prospective.requires_authority(self.s,job))
        self.h.assert_originals()


if __name__=='__main__':
    unittest.main(verbosity=2)
