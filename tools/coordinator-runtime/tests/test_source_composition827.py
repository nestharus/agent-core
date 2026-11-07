"""Closed helper additions and conserved foreign reservation metadata."""
import copy
import hashlib
import json
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch
from test_source_amendment822 import OutsideReview
from coordinator_runtime import report_repair as r, processing, configuration
from coordinator_runtime.contracts import Refusal, digest, encode, ident

class Composition(OutsideReview):
    def install_candidate(self, helpers, *, first=True):
        old=self.candidate_impl
        self.candidate_impl=dict(old, **{m:digest('reviewed helper '+m) for m in helpers})
        self.candidate_release=copy.deepcopy(self.candidate_release)
        prefix=self.candidate_release['root']+'/tools/coordinator-runtime/coordinator_runtime/'
        for m in helpers:self.candidate_release['files'][prefix+m]=self.candidate_impl[m]
        self.delta=sorted(set(self.delta if first else []) | set(helpers))
        self.enterContext(patch.object(processing,'implementation',return_value=self.candidate_impl))
        self.enterContext(patch.object(configuration,'release',return_value=self.candidate_release))

    def test_each_helper_compound_and_subsequent_preserve_plan(self):
        self.install_candidate(['plain_control.py'])
        before={t:self.store.rows('SELECT * FROM '+t) for t in (
            'owner_lease_plans','processing_capabilities','prospective_authorities','events','queue',
            'jobs','attempts','processing_source_positions','processing_runs','service_runs')}
        request=self.outside();self.apply818(self.selection(request,self.collect_outside(request)))
        self.store.processing.current()
        self.previous=self.current;self.current=dict(commit='a'*40,tree='b'*40,parents=[self.previous['commit']])
        self.install_candidate(['native_review_scope.py','inputs.py'],first=False)
        request=self.outside();self.apply818(self.selection(request,self.collect_outside(request)))
        self.store.processing.current()
        self.assertEqual(self.original_plan,r.lease_record(self.store,self.cap))
        for t,rows in before.items():self.assertEqual(rows,self.store.rows('SELECT * FROM '+t),t)

    def test_both_helpers_reviewed_before_selection_and_unknown_refused(self):
        self.install_candidate(['plain_control.py','native_review_scope.py'])
        basis=self.basis818()
        self.assertTrue(r.AMEND_ADDED_MODULES <= set(basis['modules']))
        request=self.outside(basis)
        self.rewrite(request,'RESULT.json',lambda v:v['coverage'].update(modules=['plain_control.py']))
        with self.assertRaises(Refusal):self.collect_outside(request)
        self.assertEqual(self.store.rows('SELECT * FROM owner_source_amendments'),[])
        request=self.outside();self.apply818(self.selection(request,self.collect_outside(request)))
        self.store.processing.current()
        self.previous=self.current;self.current=dict(commit='c'*40,tree='d'*40,parents=[self.previous['commit']])
        self.install_candidate(['extra.py'],first=False)
        with self.assertRaises(Refusal):self.basis818()

    def test_foreign_stopped_reservation_keeps_all_held_history(self):
        foreign=ident();controller=ident();job=ident()
        raw=json.loads(self.store.one('SELECT selection FROM processing_capabilities WHERE id=?',(self.cap,))['selection'])
        self.store.db.execute('INSERT INTO processing_capabilities VALUES(?,?,?,?,?,?)',
            (foreign,encode(raw),self.issuer,1000.,1001.,7))
        state=encode(dict(parent_END=dict(actual_END=0,evidence=['Synthetic foreign SAME original END0'])))
        self.store.db.execute('INSERT INTO processing_runs VALUES(?,?,?,?)',(controller,foreign,state,1000.))
        self.store.db.execute('INSERT INTO service_runs VALUES(?,?,?,?,?,?,?)',
            (controller,foreign,'unused','returned-awaiting-parent-END',1000.,1001.,'Synthetic original return'))
        self.store.db.execute('INSERT INTO jobs(id,role,phase,task,members,controller,token,created,state,effects,recovery_state,hold_reason) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
            (job,'Work','proposer','work-proposer','[]',controller,ident(),1000.,'reserved','unknown','custody-held','Privacy/consumer/effect history remains held'))
        task=copy.deepcopy(self.config['tasks']['work-proposer'])
        task.update(cwd=str(self.area),sandbox='read-only',effects='none',network=False)
        task['effect_authority']=dict(operations=['read-reports'],read_roots=[str(self.area)],write_roots=[])
        self.store.db.execute('INSERT INTO job_resource_policies VALUES(?,?,?)',(job,encode(task),None))
        before={t:self.store.rows('SELECT * FROM '+t) for t in ('jobs','attempts','processing_capabilities','processing_runs','service_runs','job_resource_policies','events','queue')}
        request=self.outside();self.apply818(self.selection(request,self.collect_outside(request)))
        for t,rows in before.items():self.assertEqual(rows,self.store.rows('SELECT * FROM '+t),t)
        # New synthetic rows preserve the immutable original resource maps.
        for mutation in ('overlap','unknown','unreleased','running','own','attributed'):
            candidate=ident();candidate_controller=self.controller if mutation=='own' else controller
            self.store.db.execute('INSERT INTO jobs(id,role,phase,task,members,controller,token,created,state) VALUES(?,?,?,?,?,?,?,?,?)',
                (candidate,'Work','proposer','work-proposer','[]',candidate_controller,ident(),1000.,'reserved'))
            changed=copy.deepcopy(task)
            if mutation=='overlap':changed['effect_authority']['read_roots']=[self.original_release['root']]
            if mutation!='unknown':self.store.db.execute('INSERT INTO job_resource_policies VALUES(?,?,?)',(candidate,encode(changed),None))
            if mutation=='attributed':
                self.store.db.execute('INSERT INTO attempts(id,kind,job,controller,profile,binding,state,created,ended,collected,exit,detail) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
                    (ident(),'task',candidate,controller,'fixture','fixture','collected',1000.,1001.,1002.,0,encode(dict(processing_capability=self.cap))))
            if mutation=='unreleased':self.store.db.execute("UPDATE processing_runs SET state='owned' WHERE controller=?",(controller,))
            if mutation=='running':self.store.db.execute("UPDATE service_runs SET state='running' WHERE controller=?",(controller,))
            with self.subTest(mutation=mutation), patch.object(self.store,'event',side_effect=AssertionError('BODY')):
                with self.assertRaises(Refusal):r.amendment_source_users_stopped(self.store,self.cap,self.original_plan)
            self.store.db.execute("UPDATE jobs SET state='held' WHERE id=?",(candidate,))
            self.store.db.execute('UPDATE processing_runs SET state=? WHERE controller=?',(state,controller))
            self.store.db.execute("UPDATE service_runs SET state='returned-awaiting-parent-END' WHERE controller=?",(controller,))

    def test_real_cli_compound_helper_addition(self):
        self.install_candidate(['plain_control.py','native_review_scope.py'])
        self.test_real_cli_basis_external_safe5_work_collection_and_selection()

class GitComposition(unittest.TestCase):
    def test_exact_added_blobs_closure_dependencies_config_sdk_and_legacy(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);prefix=root/'tools/coordinator-runtime/coordinator_runtime';prefix.mkdir(parents=True)
            def git(*a):return subprocess.run(['git','-C',d,*a],check=True,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL).stdout
            def commit():
                git('add','.');git('-c','user.name=Owned fixture','-c','user.email=fixture@example.invalid','-c','commit.gpgsign=false','commit','-m','owned fixture')
                return r.git_source(d)
            def impl():return {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in prefix.glob('*.py')}
            def release(pins):return dict(root=d,files={str(prefix/n):v for n,v in pins.items()},pool_control='same')
            git('init');(prefix/'inputs.py').write_text('original\n');previous=commit();old=impl()
            for helper in ('plain_control.py','native_review_scope.py'):
                (prefix/helper).write_text('reviewed '+helper+'\n');current=commit();new=impl();modules=[helper]
                r.source_compatible(release(old),release(new),old,new,modules,_ceiling=r.AMEND_MODULES,_added_modules=r.AMEND_ADDED_MODULES)
                r.source_transition(d,previous,current,old,new,modules)
                with self.assertRaises(Refusal):r.source_compatible(release(old),release(new),old,new,modules,_ceiling=r.AMEND_MODULES)
                with self.assertRaises(Refusal):r.source_transition(d,previous,current,old,{k:v for k,v in new.items() if k!=helper},modules)
                for forged in ({**previous,'tree':'0'*40},{**current,'parents':['0'*40]}):
                    with self.assertRaises(Refusal):r.source_transition(d,forged,current,old,new,modules)
                previous=current;old=new
            (prefix/'inputs.py').write_text('subsequent\n');current=commit();new=impl()
            r.source_transition(d,previous,current,old,new,['inputs.py'])
            for index,path in enumerate(('extra.py','../operator-config.json','../../message-board/sdk.py','../../dependency.py')):
                previous=r.git_source(d);oldpins=impl()
                (prefix/'inputs.py').write_text('reviewed external refusal '+str(index))
                target=prefix/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_text('unauthorized\n');bad=commit()
                with self.assertRaises(Refusal):r.source_transition(d,previous,bad,oldpins,impl(),['inputs.py'])
            before=release(old);after=release(new)
            for path in ('/external/dependency.py','/external/config.json','/external/sdk.py'):
                b=copy.deepcopy(before);a=copy.deepcopy(after);b['files'][path]='0'*64;a['files'][path]='1'*64
                with self.assertRaises(Refusal):r.source_compatible(b,a,old,new,['inputs.py'],_ceiling=r.AMEND_MODULES,_added_modules=r.AMEND_ADDED_MODULES)
