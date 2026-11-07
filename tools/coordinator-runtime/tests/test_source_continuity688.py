"""Owned Board/journal fiction for source-only same-authority continuity.

Authentication, ENDs, review assertions and changed public pins are synthetic
seams. There are no provider calls, actual owner receipts or runtime adoption.
"""
import copy
import json
import sqlite3
import unittest
from unittest.mock import patch

from test_qa629_repairs import Fixture, actor
from coordinator_runtime import configuration, processing, processing_admission, prospective
from coordinator_runtime import report_repair as repair, service, report_scope, cli
from coordinator_runtime.contracts import Refusal, digest, encode, ident


class Continuity(Fixture):
    def setUp(self):
        self.bootstrap(self.configure)
        self.store.clock = lambda: 1000.
        self.issuer = self.config['roles']['Work']['owner']
        self.report = dict(reference='fictional-full-QA-report', collector=self.issuer, actual_END=0,
            reports=[dict(name='QA', body='Whole fictional report, dissent and unresolved failures.')],
            history='Whole synthetic collector history', method_pin='fictional method v1',
            coverage=dict(status='PARTIAL', unread=['unqualified actual pilot']), effects='known-report-only')
        report_policy = dict(version='reviews-report-v1', authority='Fictional finite report selection', expires=1500.,
            task='reviews-integrator', task_sha256=digest(self.config['tasks']['reviews-integrator']),
            reports=[dict(reference=self.report['reference'], sha256=digest(self.report))])
        original_select = processing.select
        def select(runtime, boards, selection):
            selection['software_admission'] = dict(authority='Fictional original QA admission', max_packages=2,
                scopes=dict(fixture=dict(submitters=[self.source_sender], package_prefix='fictional-',
                    task_scopes={'qa-execution':self.scope}, evidence='Fictional admitted read-only QA packet')))
            return original_select(runtime, boards, selection)
        with patch.object(processing, 'select', side_effect=select):
            self.select(dict(max_inflight=4, reviews={}, report_tasks=['reviews-integrator'],
                admission=dict(until=1550., pause_bytes=90000000, max_new_inputs=20),
                legacy_resources={'Reviews':dict(original_hold=None, roots=[], unbounded=True,
                    evidence='Fictional original unknown retained', reviews_report=report_policy)}))
        self.epoch = prospective.select(self.store, self.issuer, dict(configuration=digest(self.config),
            authority='Fictional unchanged finite software permission', expires=1600., processing_capability=self.cap,
            grants={r:self.store.enrollment(r)['grant_id'] for r in self.config['roles']},
            tasks={t:dict(task_hash=digest(v), software_handoffs={}, ordinary_effects=False)
                   for t,v in self.config['tasks'].items()}))
        self.board_source = self.post('QA', 'qa-execution', 'fictional-original-package')
        processing_admission.admit(self.store, self.board_source['id'])
        self.report_id = service.ingest_report(self.store, self.issuer, 'reviews-integrator', self.report)['event']
        self.classify()
        self.events = sorted([self.board_source['id'], self.report_id])
        self.controller = self.store.controller
        self.store.db.execute('INSERT INTO processing_runs VALUES(?,?,?,?)', (self.controller,self.cap,'owned',1000.))
        self.store.db.execute('INSERT INTO service_runs VALUES(?,?,?,?,?,?,?)',
            (self.controller,self.cap,'fictional-unused-endpoint','returned-awaiting-parent-END',1000.,1001.,'fictional return'))
        with actor(self.boards['Work'].store, self.issuer):
            processing.release(self.store, self.boards, self.cap, self.controller,
                dict(actual_END=0, evidence=['SYNTHETIC same-original parent END; no actual process proof']))
        self.original_impl = processing.implementation()
        root = '/fictional-same-installed-release'
        module_root = root+'/tools/coordinator-runtime/coordinator_runtime/'
        self.old_release = dict(root=root, pool_control=dict(route='fictional hot public membership control'),
            files={**{module_root+n:h for n,h in self.original_impl.items()}, '/fictional-template':'unchanged'})
        self.new_impl = {**self.original_impl, 'report_repair.py':digest('fictional reviewed new repair'),
                         'integration.py':digest('fictional already-dispatched integration correction')}
        self.modules = ['integration.py','report_repair.py']
        self.new_release = copy.deepcopy(self.old_release)
        for n in self.modules:
            self.new_release['files'][module_root+n] = self.new_impl[n]
        selected = json.loads(self.store.one('SELECT selection FROM processing_capabilities WHERE id=?',(self.cap,))['selection'])
        transition = dict(basis=dict(release=self.old_release,
            processing=dict(roles={r:dict(original=dict(binding=s['original']['binding']))
                                   for r,s in selected['basis']['roles'].items()})), event_boundary=0,
            jobs=[], outboxes=[], alert_boundary=0)
        self.store.db.execute('INSERT INTO configuration_transitions(previous,current,original,configuration,selection,issuer,created) VALUES(?,?,?,?,?,?,?)',
            ('fictional-previous',digest(self.config),digest(self.config),encode(self.config),encode(transition),self.issuer,1000.))
        self.enterContext(patch.object(configuration, 'release', return_value=self.new_release))
        self.enterContext(patch.object(processing, 'implementation', return_value=self.new_impl))

    def configure(self):
        self.config['limits']['max_result_bytes'] = 262144
        self.config['tasks']['reviews-integrator'].update(effects='owned-artifacts', sandbox='workspace-write')
        self.config['tasks']['reviews-integrator']['effect_authority'].update(
            operations=['read-reports','consolidate-reports','write-owned-artifacts'], write_roots=[])
        self.config['tasks']['qa-execution'].update(require_package_scope=True, scope_roots=[str(self.area)])
        self.scope = dict(cwd=str(self.area), read_roots=[str(self.area)], write_roots=[],
            procedure=self.config['tasks']['qa-execution']['templates'][0], resource_evidence='Fictional exact procedure/resource holder')

    def basis(self, events=None, issuer=None):
        principal = issuer or self.issuer
        with actor(self.boards['Work'].store, principal), configuration.stopped(self.store), self.store.tx():
            return repair.source_basis(self.store, self.boards, self.cap, events or self.events,
                self.controller, principal, self.modules, 'Fictional install reviewed source fixes; keep originals')

    def request(self):
        return dict(schema=repair.SOURCE_VERSION, basis=self.basis(), authority='Fictional current Work reviewed source-only decision',
            evidence=['Synthetic independent-review assertion; tests are not actual review or acceptance'])

    def apply(self, request, issuer=None):
        principal = issuer or self.issuer
        with actor(self.boards['Work'].store, principal):
            return repair.apply_source(self.store, self.boards, principal, request)

    def untouched(self):
        return {t:self.store.rows('SELECT * FROM '+t) for t in (
            'events','queue','jobs','attempts','admissions','processing_admissions','processing_admission_resolutions',
            'processing_report_inputs','processing_source_positions','input_resolutions','prospective_authorities',
            'processing_capabilities','configuration_transitions','enrollments','processing_runs','service_runs')}

    def test_real_admitted_board_and_whole_attributed_report_keep_same_authority(self):
        before = self.untouched()
        self.assertIsNone(self.store.one('SELECT accepted FROM admissions')['accepted'])
        with self.assertRaises(Refusal): self.store.processing.current()
        request = self.request()
        receipt = self.apply(request)
        self.assertEqual(self.untouched(), before)
        self.assertEqual(receipt['capability'], self.cap)
        self.assertIsNone(receipt['acceptance'])
        self.store.processing.current()
        scope = json.loads(self.store.one('SELECT selection FROM processing_capabilities')['selection'])['software_admission']['scopes']['fixture']
        applied = processing_admission.resolved(self.store, self.board_source['package'], 'fixture', digest(scope))
        self.assertEqual(digest(applied), before['processing_admission_resolutions'][0]['admission_hash'])
        for event in self.events:
            self.assertTrue(self.store.processing.task(self.store.one('SELECT * FROM queue WHERE event=?',(event,))))
        permission = self.boards['QA'].software_authority(self.store, 'qa-execution')
        self.assertEqual(permission['prospective_epoch'], self.epoch['id'])
        self.assertEqual(self.store.event(self.report_id)['body']['original'], self.report)
        self.assertEqual(self.apply(request), receipt)
        self.assertFalse(receipt['producer_replay']); self.assertFalse(receipt['authority_renewed'])
        # Reopen exactly as a subsequent same-capability controller would.
        from coordinator_runtime.store import Store
        reopened = Store(self.config, clock=lambda:1000.)
        try:
            reopened.processing = processing.Access(reopened, self.cap, self.boards)
            reopened.processing.current()
            self.assertEqual(reopened.one('SELECT * FROM processing_capabilities'), before['processing_capabilities'][0])
        finally: reopened.close()

    def test_basis_is_metadata_only_and_held_historical_reserved_refuse_before_body(self):
        original_event = self.store.event
        with patch.object(self.store, 'event', side_effect=AssertionError('body read during basis')):
            self.basis()
            for sql,values,restore,rvalues in [
                ('UPDATE events SET hold=? WHERE id=?',('held',self.report_id),'UPDATE events SET hold=NULL WHERE id=?',(self.report_id,)),
                ('UPDATE processing_source_positions SET position=0 WHERE event=?',(self.report_id,),
                 'UPDATE processing_source_positions SET position=? WHERE event=?',
                 (self.store.one('SELECT position FROM processing_source_positions WHERE event=?',(self.report_id,))['position'],self.report_id)),
                ("UPDATE queue SET state='reserved',job='fictional-reservation' WHERE event=?",(self.report_id,),
                 "UPDATE queue SET state='queued',job=NULL WHERE event=?",(self.report_id,))]:
                self.store.db.execute(sql,values)
                with self.assertRaises(Refusal): self.basis()
                self.store.db.execute(restore,rvalues)
        self.assertEqual(original_event(self.report_id)['body']['original'],self.report)

    def test_mutated_body_rolls_back_receipt_and_reads_only_selected_bodies(self):
        request = self.request()
        changed = self.store.event(self.report_id); changed['body']['original']['reports'][0]['body'] += ' forged'
        self.store.db.execute('UPDATE events SET payload=? WHERE id=?',(encode(changed),self.report_id))
        reads = []
        actual = self.store.event
        def event(key):
            reads.append(key)
            self.assertIn(key,self.events)
            return actual(key)
        with patch.object(self.store,'event',side_effect=event), self.assertRaises(Refusal): self.apply(request)
        self.assertEqual(self.store.rows('SELECT * FROM same_authority_source_repairs_v1'),[])
        self.assertIn(self.report_id,reads)

    def test_wrong_owner_grant_stop_END_and_concurrent_collector(self):
        request = self.request()
        with self.assertRaises(Refusal): self.apply(request,ident())
        mutations = [
            ("UPDATE processing_runs SET state='owned' WHERE controller=?",(self.controller,),
             'UPDATE processing_runs SET state=? WHERE controller=?',
             (self.store.one('SELECT state FROM processing_runs')['state'],self.controller)),
            ('UPDATE processing_runs SET state=? WHERE controller=?',
             (encode(dict(parent_END=dict(actual_END=True,evidence=['not numeric']))),self.controller),
             'UPDATE processing_runs SET state=? WHERE controller=?',
             (self.store.one('SELECT state FROM processing_runs')['state'],self.controller)),
            ("UPDATE service_runs SET state='serving',returned=NULL",(),
             "UPDATE service_runs SET state='returned-awaiting-parent-END',returned=1001",()),
            ("UPDATE enrollments SET intake=1 WHERE role='QA'",(),
             "UPDATE enrollments SET intake=0 WHERE role='QA'",()),
            ("UPDATE enrollments SET grant_id='foreign-grant' WHERE role='QA'",(),
             "UPDATE enrollments SET grant_id=? WHERE role='QA'",
             (self.store.one("SELECT grant_id FROM enrollments WHERE role='QA'")['grant_id'],)),
            ('UPDATE prospective_authorities SET revoked=1000',(),
             'UPDATE prospective_authorities SET revoked=NULL',()),
            ('UPDATE processing_capabilities SET revoked=1000',(),
             'UPDATE processing_capabilities SET revoked=NULL',())]
        for sql,values,restore,rvalues in mutations:
            self.store.db.execute(sql,values)
            with self.assertRaises(Refusal): self.apply(request)
            self.store.db.execute(restore,rvalues)
        self.store.db.execute('INSERT INTO processing_runs VALUES(?,?,?,?)',('foreign-unreleased',self.cap,'owned',1000.))
        with self.assertRaises(Refusal):self.apply(request)

    def test_uncollected_attempt_and_frozen_job_membership_cannot_be_anchors(self):
        attempt = self.store.one('SELECT * FROM attempts LIMIT 1')
        self.store.db.execute('UPDATE attempts SET collected=NULL WHERE id=?',(attempt['id'],))
        with self.assertRaises(Refusal):self.basis()
        self.store.db.execute('UPDATE attempts SET collected=? WHERE id=?',(attempt['collected'],attempt['id']))
        # A queue row cannot hide an already frozen obligation by clearing job.
        self.store.db.execute("INSERT INTO jobs(id,role,phase,task,members,controller,token,created,state,effects) "
            "VALUES(?,'QA','execution','qa-execution',?,?,?,1000,'held','unknown')",
            ('fictional-old-job',encode([dict(event=self.board_source['id'],hash=digest(self.board_source))]),'other-original',ident()))
        with self.assertRaises(Refusal):self.basis()

    def test_changed_pins_selection_admission_queue_and_no_legacy_conversion(self):
        request = self.request()
        bad = copy.deepcopy(request); bad['schema']='legacy-or-future'
        with self.assertRaises(Refusal):self.apply(bad)
        old = self.new_release['files']['/fictional-template']
        self.new_release['files']['/fictional-template']='unreviewed'
        with self.assertRaises(Refusal):self.apply(request)
        self.new_release['files']['/fictional-template']=old
        self.store.db.execute("UPDATE admissions SET accepted='fabricated-new-receipt'")
        with self.assertRaises(Refusal):self.apply(request)
        self.store.db.execute('UPDATE admissions SET accepted=NULL')
        self.store.db.execute('UPDATE processing_capabilities SET starts=starts+1')
        with self.assertRaises(Refusal):self.apply(request)
        self.store.db.execute('UPDATE processing_capabilities SET starts=starts-1')
        self.apply(request)
        with actor(self.boards['Work'].store,self.issuer), self.assertRaises(Refusal):
            repair.basis(self.store,self.boards,self.cap,self.report_id,self.controller,self.issuer)
        changed = copy.deepcopy(request);changed['authority'] += ' replace'
        with self.assertRaises(Refusal):self.apply(changed)
        self.new_impl['integration.py']='changed after review'
        with self.assertRaises(Refusal):self.store.processing.current()

    def test_finite_windows_charges_and_revocation_survive_repair(self):
        request = self.request(); self.apply(request)
        cap = self.store.one('SELECT * FROM processing_capabilities')
        self.store.clock = lambda:1501.
        # Report policy expires at its original time, before the epoch.
        with self.assertRaises(Refusal):
            report_scope.eligible(self.store,self.store.one('SELECT * FROM queue WHERE event=?',(self.report_id,)),
                json.loads(cap['selection'])['service']['legacy_resources']['Reviews'])
        self.store.clock = lambda:1601.
        with self.assertRaises(Refusal):prospective.current(self.store,'qa-execution')
        self.assertEqual(self.store.one('SELECT * FROM processing_capabilities'),cap)
        self.store.db.execute('UPDATE processing_capabilities SET revoked=1601')
        with self.assertRaises(Refusal):self.store.processing.current()

    def test_paused_management_release_resolution_does_not_grant_processing(self):
        self.apply(self.request())
        self.store.processing = None
        configuration.assert_release(self.store)
        from coordinator_runtime import integration_management
        with actor(self.boards['Work'].store,self.issuer):
            basis = integration_management.basis(self.store,['Work'],self.issuer,
                'Fictional paused metadata operation','Exact scoped metadata',metadata_only=True)
        self.assertEqual(basis['configuration'],digest(self.config))
        self.assertIsNone(self.store.processing)
        self.assertTrue(all(r['intake']==0 for r in self.store.rows('SELECT intake FROM enrollments')))

    def test_supported_cli_and_append_only_record(self):
        with patch.object(cli,'actual_actor',return_value=self.issuer), actor(self.boards['Work'].store,self.issuer), \
                patch.object(processing,'ProcessingBoard',side_effect=lambda config,role:self.boards[role]):
            args = cli.parser().parse_args(['same-authority-source-repair-basis',self.cap,*self.events,
                '--controller',self.controller,'--purpose','Fictional current explicit purpose',
                '--module','integration.py','--module','report_repair.py'])
            basis = cli.operate(args,self.store)
            path = self.area/'fictional-reviewed-repair.json'
            path.write_text(encode(dict(schema=repair.SOURCE_VERSION,basis=basis,authority='Fictional reviewed decision',
                evidence=['Synthetic complete public review evidence'])))
            args = cli.parser().parse_args(['select-same-authority-source-repair','--selection',str(path)])
            self.assertEqual(cli.operate(args,self.store)['capability'],self.cap)
        for sql in ('UPDATE same_authority_source_repairs_v1 SET issuer=issuer','DELETE FROM same_authority_source_repairs_v1'):
            with self.assertRaises(sqlite3.IntegrityError):self.store.db.execute(sql)

    def test_exact_eight_module_ceiling_accepts_local_integration_and_store(self):
        self.assertEqual(repair.SOURCE_MODULES, {
            'configuration.py','integration.py','integration_management.py','resource_scopes.py',
            'cli.py','report_repair.py','local_integration.py','store.py'})
        for modules in (['local_integration.py'], ['store.py'], ['local_integration.py','store.py']):
            with self.subTest(modules=modules):
                before,after=copy.deepcopy(self.old_release),copy.deepcopy(self.old_release)
                old,new=dict(self.original_impl),dict(self.original_impl)
                paths=[]
                for name in modules:
                    self.assertIn(name,old)
                    path=before['root']+'/tools/coordinator-runtime/coordinator_runtime/'+name
                    new[name]=digest('fictional reviewed change to '+name)
                    after['files'][path]=new[name]
                    paths.append(path)
                self.assertEqual(repair.source_compatible(before,after,old,new,modules),sorted(paths))

    def test_exact_delta_does_not_expand_modules_location_pool_or_dependencies(self):
        for name in ('software.py','processing.py','appserver.py'):
            before,after=copy.deepcopy(self.old_release),copy.deepcopy(self.old_release)
            old,new=dict(self.original_impl),dict(self.original_impl)
            new[name]='unselected';after['files'][before['root']+'/tools/coordinator-runtime/coordinator_runtime/'+name]='unselected'
            with self.assertRaises(Refusal):repair.source_compatible(before,after,old,new,[name])
        for key in ('root','pool_control'):
            changed=copy.deepcopy(self.new_release);changed[key]='changed'
            with self.assertRaises(Refusal):repair.source_compatible(self.old_release,changed,self.original_impl,self.new_impl,self.modules)
        changed=copy.deepcopy(self.new_release);changed['files']['/new-module.py']='addition'
        with self.assertRaises(Refusal):repair.source_compatible(self.old_release,changed,self.original_impl,self.new_impl,self.modules)


if __name__ == '__main__':
    unittest.main()
