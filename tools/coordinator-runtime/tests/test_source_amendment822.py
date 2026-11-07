"""Outside review safe5 + authenticated Work operation through real CLI processes.

Synthetic Board actors, original END, release/Git metadata and clock are explicit
seams. Separate GitProof tests exercise actual ancestry/ALLparents/blob closure.
No provider/native owner, live store or service is used.
"""
import copy
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

from test_source_amendment818 import Amendment
from coordinator_runtime import report_repair as r, configuration, processing
from coordinator_runtime.contracts import Refusal, digest, encode, ident
from test_qa629_repairs import actor


class OutsideReview(Amendment):
    def outside(self, basis=None):
        b = basis or self.basis818()
        reviewer = ident(); invocation = ident(); writer = ident(); writer_invocation = ident()
        result = dict(schema='independent-source-code-review-v1',basis_hash=digest(b),
            candidate=b['current'],previous=b['previous'],modules=b['modules'],module_diff=b['changed'],
            plan_hash=b['plan_hash'],reviewer=reviewer,invocation=invocation,writer=writer,
            writer_invocation=writer_invocation,workflow='code-review-workflow',readonly=True,
            disposition='approve-exact-code-delta',native_acceptance=False,
            coverage=dict(complete=True,modules=b['modules'],unreviewed=[]),
            risks=['Synthetic risk retained whole'],failures=['Historical failed attempt retained'],
            remaining_obligations=['Native acceptance and original consumer debts remain'])
        directory=self.area/('independent-public-'+ident()); directory.mkdir()
        files={'RESULT.json':encode(result),'PRIMARY.md':'Whole independent review Ω; overall rollout PARTIAL.\n',
            'LIMITS.md':'No native acceptance; synthetic process/identity seams. Preserve risks/failures.\n',
            'PUBLICATION.json':encode(dict(reviewed_candidate=b['current'],basis_hash=digest(b),
                reviewer=reviewer,invocation=invocation)),
            'WRITER-RELEASE.json':encode(dict(reviewer=reviewer,invocation=invocation,
                source_writes_complete=True,report_writes_complete=True,pending_owned_children=[]))}
        manifest={}
        for name, body in files.items():
            path=directory/name;path.write_text(body)
            manifest[name]=dict(path=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        return dict(schema=r.WORK_REVIEW_VERSION,basis=b,authority='Synthetic Work independently observed outside original END',
            collection=dict(collector=self.issuer,independently_observed=True,reviewer=reviewer,invocation=invocation,
                writer=writer,writer_invocation=writer_invocation,original_numeric_id=12345,actual_END=0,
                evidence=['Synthetic original12345 SAME foreground collection END0; not reviewer DONE']),public_manifest=manifest)

    def collect_outside(self, request):
        with actor(self.boards['Work'].store,self.issuer):
            return r.collect_amendment_review(self.store,self.boards,self.issuer,request)

    def selection(self, request, receipt):
        return dict(schema=r.AMEND_VERSION,basis=request['basis'],authority='Synthetic Work exact reviewed selection',
            review_hash=receipt['review_hash'])

    def rewrite(self, request, name, change):
        pin=request['public_manifest'][name];path=Path(pin['path'])
        value=json.loads(path.read_text());change(value);path.write_text(encode(value))
        pin['sha256']=hashlib.sha256(path.read_bytes()).hexdigest()

    def test_external_original_whole_conservation_and_stale_refusals(self):
        request=self.outside();before=self.store.rows('SELECT * FROM processing_capabilities')
        receipt=self.collect_outside(request)
        self.assertEqual(receipt,self.collect_outside(request))
        sealed=json.loads(self.store.one('SELECT review FROM owner_source_reviews')['review'])
        result=json.loads(sealed['public_bodies']['RESULT.json'])
        self.assertEqual(result['failures'],['Historical failed attempt retained'])
        self.assertEqual(result['risks'],['Synthetic risk retained whole'])
        self.assertFalse(receipt['native_acceptance'])
        selection=self.selection(request,receipt);self.apply818(selection)
        self.assertEqual(before,self.store.rows('SELECT * FROM processing_capabilities'))
        self.assertEqual(self.original_plan,r.lease_record(self.store,self.cap))
        self.assertEqual(self.store.processing.current()[0]['id'],self.cap)

    def test_self_forged_wrong_partial_uncollected_unreleased_and_changed_public_refuse(self):
        for label in ('self','forged','wrong','partial','uncollected','claimedEND','sameinvocation',
                      'unreleased','changed','publication'):
            with self.subTest(label=label):
                request=self.outside()
                if label=='self':request['collection']['reviewer']=self.issuer
                if label=='forged':request['collection']['collector']=ident()
                if label=='wrong':self.rewrite(request,'RESULT.json',lambda v:v.update(candidate=self.previous))
                if label=='partial':self.rewrite(request,'RESULT.json',lambda v:v['coverage'].update(complete=False))
                if label=='uncollected':request['collection']['independently_observed']=False
                if label=='claimedEND':request['collection']['actual_END']='DONE'
                if label=='sameinvocation':request['collection']['invocation']=request['collection']['writer_invocation']
                if label=='unreleased':self.rewrite(request,'WRITER-RELEASE.json',lambda v:v.update(pending_owned_children=[99]))
                if label=='changed':Path(request['public_manifest']['LIMITS.md']['path']).write_text('forged later body')
                if label=='publication':self.rewrite(request,'PUBLICATION.json',lambda v:v.update(reviewed_candidate=self.previous))
                with self.assertRaises(Refusal):self.collect_outside(request)
                self.assertEqual(self.store.rows('SELECT * FROM owner_source_reviews'),[])

    def test_collection_and_selection_mutation_fences_and_public_hashes(self):
        request=self.outside();original=r.external_review
        def race(*args):
            bodies=original(*args)
            self.store.db.execute('UPDATE processing_capabilities SET starts=starts+1 WHERE id=?',(self.cap,))
            return bodies
        with patch.object(r,'external_review',side_effect=race):
            with self.assertRaises(Refusal):self.collect_outside(request)
        self.assertEqual(self.store.rows('SELECT * FROM owner_source_reviews'),[])
        receipt=self.collect_outside(request)
        with patch.object(r,'external_review',side_effect=race):
            with self.assertRaises(Refusal):self.apply818(self.selection(request,receipt))
        self.assertEqual(self.store.rows('SELECT * FROM owner_source_amendments'),[])
        Path(request['public_manifest']['LIMITS.md']['path']).write_text('changed after collection')
        with self.assertRaises(Refusal):self.apply818(self.selection(request,receipt))

    def test_external_running_unreleased_expired_exhausted_config_grant_refuse(self):
        request=self.outside()
        changes=[('service_runs','state','controller',self.controller,'running'),
                 ('processing_runs','state','controller',self.controller,'owned'),
                 ('attempts','collected','id',self.control_attempt,None),
                 ('processing_capabilities','starts','id',self.cap,self.plan['max_starts'])]
        for table,col,keycol,key,value in changes:
            old=self.store.one(f'SELECT {col} FROM {table} WHERE {keycol}=?',(key,))[col]
            self.store.db.execute(f'UPDATE {table} SET {col}=? WHERE {keycol}=?',(value,key))
            with self.assertRaises(Refusal):self.collect_outside(request)
            self.store.db.execute(f'UPDATE {table} SET {col}=? WHERE {keycol}=?',(old,key))
        self.now=self.plan['until']
        with self.assertRaises(Refusal):self.collect_outside(request)
        self.now=1600.
        self.config['tasks']['work-proposer']['authority']+=' changed'
        with self.assertRaises(Refusal):self.collect_outside(request)
        self.config['tasks']['work-proposer']['authority']=self.config['tasks']['work-proposer']['authority'][:-8]
        self.store.db.execute("UPDATE enrollments SET grant_id='forged' WHERE role='Work'")
        with self.assertRaises(Refusal):self.collect_outside(request)

    def cli_process(self, args):
        # Actual CLI parser/config load/Store reopen/Board auth/JSON output/END.
        # Only the declared clock and installed-release/Git fixture seams differ.
        config=self.area/'cli-config.json';config.write_text(encode(self.config))
        seam=self.area/'cli-seam.json';seam.write_text(encode(dict(release=self.candidate_release,
            previous=self.previous,current=self.current,implementation=self.candidate_impl)))
        script=self.area/'cli-driver.py'
        script.write_text('''import json,sys
from unittest.mock import patch
from coordinator_runtime import cli, configuration, processing, report_repair as r
from coordinator_runtime.store import Store
seam=json.load(open(sys.argv[1])); original=Store.__init__
def init(self,*a,**kw):
 kw['clock']=lambda:1600.; original(self,*a,**kw)
with patch.object(Store,'__init__',init), patch.object(processing,'implementation',return_value=seam['implementation']), patch.object(configuration,'release',return_value=seam['release']), patch.object(r,'git_source',side_effect=lambda root,commit=None:seam['previous'] if commit else seam['current']), patch.object(r,'source_transition'):
 raise SystemExit(cli.main(sys.argv[2:]))
''')
        env=dict(os.environ,CODEX_SESSION_ID=self.issuer)
        proc=None
        try:
            proc=subprocess.Popen([sys.executable,str(script),str(seam),'--config',str(config),*args],
                env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            out,err=proc.communicate(timeout=20)
        finally:
            if proc is not None:
                if proc.poll() is None:proc.kill();proc.communicate()
                with (self.area/'cli-END.jsonl').open('a') as stream:
                    stream.write(encode(dict(pid=proc.pid,actual_END=proc.returncode,command=args[0]))+'\n')
        self.assertLess(len(out)+len(err),4*1024**2)
        self.assertEqual(proc.returncode,0,(out.decode(),err.decode()))
        return json.loads(out)

    def test_real_cli_basis_external_safe5_work_collection_and_selection(self):
        with self.assertRaises(Refusal):self.store.processing.current()
        # Already-returned original, same numeric END and release through the
        # actual CLI while normal Access still refuses the installed candidate.
        self.store.db.execute('UPDATE processing_runs SET state=? WHERE controller=?',('owned',self.controller))
        end=self.area/'original-END.json'
        end.write_text(encode(dict(actual_END=0,evidence=['Synthetic same original numeric12345 END0'])))
        released=self.cli_process(['processing-release',self.cap,'--controller',self.controller,'--receipt',str(end)])
        self.assertEqual(released['collection']['actual_END'],0)
        with self.assertRaises(Refusal):self.store.processing.current()
        previous=self.area/'previous.json';previous.write_text(encode(self.previous))
        manifest=self.area/'manifest.json';manifest.write_text(encode(self.manifest))
        args=['owner-source-amendment-basis',self.cap,'--controller',self.controller,
            '--previous',str(previous),'--manifest',str(manifest),'--purpose','Real CLI synthetic outside review path']
        for module in self.delta:args+=['--module',module]
        basis=self.cli_process(args)
        request=self.outside(basis);path=self.area/'outside.json';path.write_text(encode(request))
        receipt=self.cli_process(['collect-owner-source-review','--selection',str(path)])
        selection=self.selection(request,receipt);path=self.area/'selection822.json';path.write_text(encode(selection))
        before=self.store.rows('SELECT * FROM processing_capabilities')
        selected=self.cli_process(['select-owner-source-amendment','--selection',str(path)])
        self.assertEqual(selected['current'],self.current)
        self.assertEqual(before,self.store.rows('SELECT * FROM processing_capabilities'))
        self.assertEqual(self.original_plan,r.lease_record(self.store,self.cap))
        self.store.processing.current()

    def test_closed_native_report_guard_ceiling_subsequent_amendment(self):
        request=self.outside();self.apply818(self.selection(request,self.collect_outside(request)))
        self.previous=self.current;self.current=dict(commit='a'*40,tree='b'*40,parents=[self.previous['commit']])
        self.delta=['local_integration.py','local_native.py']
        new=dict(self.candidate_impl,**{name:digest('reviewed822 '+name) for name in self.delta})
        release=copy.deepcopy(self.candidate_release)
        for name in self.delta:release['files'][release['root']+'/tools/coordinator-runtime/coordinator_runtime/'+name]=new[name]
        with patch.object(processing,'implementation',return_value=new),patch.object(configuration,'release',return_value=release):
            request=self.outside();self.apply818(self.selection(request,self.collect_outside(request)))
            self.assertEqual(self.store.processing.current()[0]['id'],self.cap)
        self.assertEqual(self.original_plan,r.lease_record(self.store,self.cap))
        self.assertNotIn('appserver.py',r.AMEND_MODULES)
