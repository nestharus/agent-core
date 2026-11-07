"""Real journal/Board APIs; explicit synthetic actor/END/publication seams.
Original implementation is the authentic 23773 pin set, original plan pins822.
Git closure is exercised separately against an owned real Git repository.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch
from test_owner_lease797 import OwnerLease
from test_lease_effect805 import HISTORICAL_IMPLEMENTATION, Isolation
from test_qa629_repairs import actor
from coordinator_runtime import report_repair as r, processing, configuration
from coordinator_runtime.contracts import Refusal, digest, encode

class Amendment(OwnerLease):
    historical_implementation = HISTORICAL_IMPLEMENTATION

    def setUp(self):
        pins = json.loads(Path('/src/original822.json').read_text())
        with patch.object(processing,'implementation',return_value=pins):
            super().setUp()
            self.apply()
        self.original_plan = r.lease_record(self.store,self.cap)
        self.original_impl = pins
        self.original_release = self.new_release
        self.candidate_impl = processing.implementation()
        self.candidate_release = copy.deepcopy(self.original_release)
        root=self.original_release['root']+'/tools/coordinator-runtime/coordinator_runtime/'
        self.candidate_release['files'].update({root+k:v for k,v in self.candidate_impl.items()})
        self.delta=sorted(k for k in pins if pins[k]!=self.candidate_impl[k])
        self.previous=dict(commit='8'*40,tree='7'*40,parents=['6'*40,'5'*40])
        self.current=dict(commit='9'*40,tree='4'*40,parents=['8'*40])
        self.manifest={n:digest(n) for n in ('PRIMARY.md','RESULT.json','LIMITS.md','PUBLICATION.json','WRITER-RELEASE.json')}
        self.enterContext(patch.object(configuration,'release',return_value=self.candidate_release))
        self.git=self.enterContext(patch.object(r,'git_source',side_effect=lambda root,commit=None:self.previous if commit else self.current))
        self.transition=self.enterContext(patch.object(r,'source_transition'))

    def basis818(self):
        with actor(self.boards['Work'].store,self.issuer), configuration.stopped(self.store),self.store.tx():
            return r.amendment_basis(self.store,self.boards,self.cap,self.controller,self.issuer,
                self.previous,self.delta,self.manifest,'Synthetic exact stopped repair818')

    def reviewed(self,basis=None):
        basis=self.basis818() if basis is None else basis
        review=dict(basis=basis,authority='Synthetic independent reviewer exact delta and safe5 manifest',actual_END=0)
        reviewer=self.config['roles']['Reviews']['owner']
        with actor(self.boards['Reviews'].store,reviewer):
            receipt=r.review_amendment(self.store,self.boards,reviewer,review)
        return dict(schema=r.AMEND_VERSION,basis=basis,authority='Synthetic actual Work selection',review_hash=receipt['review_hash'])

    def apply818(self,request):
        with actor(self.boards['Work'].store,self.issuer):
            return r.apply_amendment(self.store,self.boards,self.issuer,request)

    def test_authentic_original_plan_and_pending_history_preserved(self):
        tables=('owner_lease_plans','processing_capabilities','prospective_authorities','events','queue',
                'jobs','attempts','processing_source_positions','service_windows','processing_runs','service_runs')
        before={t:self.store.rows('SELECT * FROM '+t) for t in tables}
        old=self.store.event(self.work)['body']
        with self.assertRaises(Refusal):self.store.processing.current()
        request=self.reviewed();receipt=self.apply818(request)
        self.assertEqual(receipt,self.apply818(request))
        for table,rows in before.items():self.assertEqual(rows,self.store.rows('SELECT * FROM '+table),table)
        self.assertEqual(self.store.event(self.work)['body'],old)
        self.assertEqual(self.original_plan,r.lease_record(self.store,self.cap))
        self.store.processing.current()
        with self.assertRaises(Exception):self.store.db.execute('DELETE FROM owner_source_amendments')
        with self.assertRaises(Exception):self.store.db.execute('UPDATE owner_source_reviews SET issuer=?',('forged',))
        changed=copy.deepcopy(request);changed['authority']='contradictory second amendment'
        with self.assertRaises(Refusal):self.apply818(changed)
        self.assertEqual(len(self.store.rows('SELECT * FROM owner_source_amendments')),1)

    def test_forged_review_actor_manifest_and_stale_counter_refuse(self):
        basis=self.basis818()
        forged=dict(schema=r.AMEND_VERSION,basis=basis,authority='Work testimony alone',review_hash='0'*64)
        with self.assertRaises(Refusal):self.apply818(forged)
        with actor(self.boards['Work'].store,self.issuer):
            with self.assertRaises(Refusal):r.review_amendment(self.store,self.boards,self.issuer,
                dict(basis=basis,authority='forged independent review',actual_END=0))
        request=self.reviewed(basis)
        self.store.db.execute('UPDATE processing_capabilities SET starts=starts+1 WHERE id=?',(self.cap,))
        with self.assertRaises(Refusal):self.apply818(request)
        self.assertEqual(self.store.rows('SELECT * FROM owner_source_amendments'),[])
        self.manifest.pop('LIMITS.md')
        with self.assertRaises(Refusal):self.basis818()

    def test_running_uncollected_expired_exhausted_changed_task_config_grant_refuse(self):
        request=self.reviewed()
        mutations=[('service_runs','state',self.controller,'controller','running'),
                   ('attempts','collected',self.control_attempt,'id',None),
                   ('processing_capabilities','starts',self.cap,'id',self.plan['max_starts'])]
        for table,column,key,idcol,value in mutations:
            old=self.store.one('SELECT '+column+' FROM '+table+' WHERE '+idcol+'=?',(key,))[column]
            self.store.db.execute('UPDATE '+table+' SET '+column+'=? WHERE '+idcol+'=?',(value,key))
            with self.assertRaises(Refusal):self.apply818(request)
            self.store.db.execute('UPDATE '+table+' SET '+column+'=? WHERE '+idcol+'=?',(old,key))
        self.now=self.plan['until']
        with self.assertRaises(Refusal):self.apply818(request)
        self.now=1600.
        old_authority=self.config['tasks']['work-proposer']['authority']
        self.config['tasks']['work-proposer']['authority']='changed task'
        with self.assertRaises(Refusal):self.apply818(request)
        self.config['tasks']['work-proposer']['authority']=old_authority
        self.store.db.execute("UPDATE enrollments SET grant_id='forged' WHERE role='Work'")
        with self.assertRaises(Refusal):self.apply818(request)
        self.assertEqual(self.store.rows('SELECT * FROM owner_source_amendments'),[])

    def test_no_plan_replacement_or_native_policy_extension(self):
        request=self.reviewed();self.apply818(request)
        raw=json.loads(self.store.one('SELECT selection FROM processing_capabilities')['selection'])
        effective=self.store.processing.current()[1]
        self.assertEqual(raw.get('allocation'),effective.get('allocation'))
        self.assertEqual(raw.get('window_authority'),effective.get('window_authority'))
        self.assertEqual(self.original_plan['basis']['prospective'],self.store.one('SELECT * FROM prospective_authorities'))
        self.now=self.plan['until']
        with self.assertRaises(Refusal):self.store.processing.current()

    def test_subsequent_reviewed_inputs_delta_keeps_original_plan(self):
        first=self.reviewed();self.apply818(first)
        self.previous=self.current
        self.current=dict(commit='a'*40,tree='b'*40,parents=[self.previous['commit']])
        second_impl=dict(self.candidate_impl,**{'inputs.py':digest('subsequent reviewed inputs repair')})
        second_release=copy.deepcopy(self.candidate_release)
        second_release['files'][second_release['root']+'/tools/coordinator-runtime/coordinator_runtime/inputs.py']=second_impl['inputs.py']
        self.delta=['inputs.py']
        with patch.object(processing,'implementation',return_value=second_impl),patch.object(configuration,'release',return_value=second_release):
            second=self.reviewed();self.apply818(second)
            self.assertEqual(second['basis']['previous_amendment'],digest(first))
            self.assertEqual(second['basis']['ordinal'],2)
            self.assertEqual(self.store.processing.current()[0]['id'],self.cap)
        self.assertEqual(self.original_plan,r.lease_record(self.store,self.cap))
        self.assertEqual(len(self.store.rows('SELECT * FROM owner_source_amendments')),2)

class GitProof(unittest.TestCase):
    def test_real_git_allparents_ancestry_and_closed_blob_delta(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);module=root/'tools/coordinator-runtime/coordinator_runtime/inputs.py'
            module.parent.mkdir(parents=True)
            def git(*args):
                return subprocess.run(['git','-C',d,*args],check=True,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL).stdout
            git('init');git('config','user.name','Owned fixture');git('config','user.email','fixture@example.invalid')
            module.write_text('original\n');git('add','.');git('-c','commit.gpgsign=false','commit','-m','original')
            previous=r.git_source(d);old={'inputs.py':hashlib.sha256(module.read_bytes()).hexdigest()}
            module.write_text('reviewed\n');git('add','.');git('-c','commit.gpgsign=false','commit','-m','reviewed')
            current=r.git_source(d);new={'inputs.py':hashlib.sha256(module.read_bytes()).hexdigest()}
            r.source_transition(d,previous,current,old,new,['inputs.py'])
            for forged in ({**previous,'parents':['0'*40]}, {**previous,'tree':'0'*40}):
                with self.assertRaises(Refusal):r.source_transition(d,forged,current,old,new,['inputs.py'])
            with self.assertRaises(Refusal):r.source_transition(d,previous,current,old,{'inputs.py':'0'*64},['inputs.py'])
            with self.assertRaises(Refusal):r.source_transition(d,current,previous,new,old,['inputs.py'])
