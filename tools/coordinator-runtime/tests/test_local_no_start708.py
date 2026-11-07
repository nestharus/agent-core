"""Explicit owned fictional lifecycle controls; no actual state or native calls.

Run with --fixtures ABSOLUTE_NEW_OWNED_ROOT. All stores/Boards/configurations
are authored here. Retain every fixture; never read /proc or allocate a provider.
Legacy test77 duty/guard assertions run with supplied admission instead of its
/proc preamble and an explicit small per-publication fixture byte reservation.
"""
import argparse
import asyncio
from contextlib import contextmanager, ExitStack
import copy
import json
import os
from pathlib import Path
import sqlite3
import sys
import unittest
from unittest.mock import AsyncMock, Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import support
import test_integration_no_start77 as legacy
import test_management406 as managed
import test_metadata_closure671 as metadata
from coordinator_runtime import integration_management as management, local_integration as local
from coordinator_runtime import publication, selected_source
from coordinator_runtime.contracts import Refusal, digest, encode, validate_config
from coordinator_runtime.dispatcher import Dispatcher
from coordinator_runtime.integration import LOCAL_NO_START
from coordinator_runtime.store import Store


def owned_headroom():
    # Only this invocation's freshly created fixture subtree, never the packet,
    # enclosing captures, production state, platform stores or /proc.
    used = sum(p.stat().st_size for p in FIXTURES.rglob('*') if p.is_file())
    if used + 8*1024*1024 > 128*1024*1024:
        raise RuntimeError('owned fixture admission exhausted; retain and stop')


class RetainedDirectory:
    serial = 0

    def __init__(self, *args, **kwargs):
        owned_headroom()
        type(self).serial += 1
        self.name = str(FIXTURES / ('fixture-' + str(self.serial)))
        Path(self.name).mkdir(mode=0o700)

    def cleanup(self):
        pass  # Deliberate retained evidence, no automatic cleanup.


def configuration(home):
    config = support.config_at(home)
    target = str(Path(home)/'fictional-points.json')
    task = config['tasks']['work-integrator']
    task.update(sandbox='workspace-write', effects='owner-reconcile',
                routine_completion={'kind':'file-witness', 'targets':[target]})
    task['effect_authority']['write_roots'] = [str(home)]
    config['local_integration'] = {'max_inflight':2, 'points':{
        'a':{'kind':'item','line':'fictional708','incarnation':'fictional708',
             'bindings':[{'target':target,'path':['item']}], 'resources':[],
             'protected':['id','owner'], 'writable':['state']}},
        'tasks':{'work-integrator':{'capacity':2,'discovery_batch':1,'points':['a'],
                  'authority':'Fictional current Work file authority', 'method':task['templates'][0]}}}
    return validate_config(config)


@unittest.skipUnless(__name__ == '__main__', 'requires explicit owned --fixtures root')
class LocalNoStart708(unittest.TestCase):
    def setUp(self):
        self.home = Path(RetainedDirectory().name)
        self.config = configuration(self.home)
        self.s = support.enrolled(self.config, clock=lambda:1000.)
        self.addCleanup(self.s.close)
        self.s.execution_pool = legacy.base.FictionalAllocation()
        self.owner = self.config['roles']['Work']['owner']
        event = support.event(self.config, 'local708')
        event['integration'] = {'reads':['a'],'writes':['a'],'versions':{'a':'fictional-original-version'}}
        support.queued(self.s, event)
        self.event = event['id']
        self.job = self.s.reserve()
        self.assertIsNotNone(self.job)
        self.assertIsNone(self.s.integration_context(self.job['id']))
        self.attempt = self.s.start_job(self.job['id'],self.job['token'])
        self.collect_no_start()
        self.s.hold_job(self.job['id'],'fictional current owner hold')

    def collect_no_start(self):
        self.s.collect(self.attempt, {'exit':None,'result':None,'capture':'not-started',
            'cleanup':'no-session-created','error':'fictional prelaunch refusal',
            'detail':{'known_not_started':True,'resume_disposition':'fictional original confirms no launch'}})

    def basis(self):
        return self.s.integration_no_start_basis(self.job['id'],self.job['token'])

    def receipt(self, basis=None):
        basis = self.basis() if basis is None else basis
        return {'basis':basis,'reason':'Fictional exact no-start withdrawal, inputs stay pending',
            'controllers':[{'controller':c,'collector':'fictional actual collector','writers_closed':True,
                'no_launch':True,'evidence':['fictional service stopped, parent collected END0, every child closed; no task callback can launch']}
                for c in basis['controllers']]}

    def withdraw(self, receipt=None):
        return self.s.withdraw_integration_no_start(self.job['id'],self.job['token'],self.owner,
                                                   self.receipt() if receipt is None else receipt)

    def snapshot(self):
        return {r['name']:self.s.rows('SELECT * FROM '+r['name']+' ORDER BY rowid')
            for r in self.s.rows("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}

    def refused(self, callback):
        before = self.snapshot()
        with self.assertRaises(Refusal): callback()
        self.assertEqual(before,self.snapshot())

    @contextmanager
    def mutation(self, sql, parameters=()):
        saved = sqlite3.connect(':memory:')
        self.s.db.backup(saved)
        try:
            self.s.db.execute(sql,parameters)
            yield
        finally:
            saved.backup(self.s.db)
            saved.close()

    def diagnosis(self):
        self.s.claim_recovery(self.job['id'])
        d = self.s.diagnosis_attempt(self.job['id'])
        self.s.begin(d,{'premise':'fictional read-only diagnosis ran'})
        self.s.collect(d,{'exit':0,'result':{'retained':'UNACQUIRED_DIAGNOSIS708'},
                          'capture':'complete','cleanup':'done','detail':{}})
        return d

    def test_positive_closed_diagnosis_conserves_and_fences_without_new_job(self):
        d = self.diagnosis()
        self.s.db.execute('INSERT INTO artifact_custody(attempt,path,kind,owner,witness,sha256) VALUES(?,?,?,?,?,?)',
            (d,'fictional-retained-source','report','fictional-original-custodian','{}','fictional'))
        self.s.db.execute('INSERT INTO outboxes(id,role,job,producer,recipient,kind,required,payload,state,created) '
            'VALUES(?,?,?,?,?,?,?,?,?,?)', ('fictional-outbox','Work',self.job['id'],self.owner,'Work','question','settled',
                                        '{"retained":"UNACQUIRED_OUTBOX708"}','sent',1000.))
        self.s.set_hold(self.event,'fictional privacy hold retained')
        before = self.snapshot()
        basis = self.basis()
        self.assertEqual(LOCAL_NO_START,basis['schema'])
        self.assertNotIn('UNACQUIRED_',encode(basis))
        self.withdraw(self.receipt(basis))
        after = self.snapshot()
        for table in before:
            if table not in {'jobs','queue','integration_prestart_dispositions','allocation_revision'}:
                self.assertEqual(before[table],after[table],table)
        expected = copy.deepcopy(before['jobs'])
        self.assertEqual(expected,after['jobs'])  # Held state/reason were already present.
        queue = self.s.one('SELECT state,job FROM queue WHERE event=?',(self.event,))
        self.assertEqual({'state':'queued','job':None},queue)
        self.assertEqual(1,len(after['jobs']))
        self.assertIsNone(self.s.attempt(self.attempt)['ended'])
        self.assertEqual(0,self.s.attempt(d)['exit'])
        self.assertIsNone(self.s.one('SELECT processed_at FROM events WHERE id=?',(self.event,))['processed_at'])
        self.assertIsNone(self.s.claim_recovery(self.job['id']))
        for callback in (lambda:self.s.begin(self.attempt,{}),lambda:self.s.session(self.attempt,'fictional-late'),
            lambda:self.s.observe_semantic(self.attempt,'DONE'),lambda:self.s.authorize_launch(self.attempt),
            lambda:self.s.start_job(self.job['id'],self.job['token']),lambda:self.s.diagnosis_attempt(self.job['id']),
            lambda:publication.publish(self.s,None,self.job,None,None,None),lambda:self.withdraw()):
            self.refused(callback)

    def test_future_reservation_and_launch_still_use_ordinary_guards(self):
        self.withdraw()
        self.assertEqual(1,self.s.one('SELECT count(*) AS n FROM jobs')['n'])
        # A separate explicit reserve is a new job. No model/child is launched.
        successor = self.s.reserve()
        self.assertIsNotNone(successor)
        self.assertNotEqual(self.job['id'],successor['id'])
        self.s.set_hold(self.event,'fictional new current source hold')
        self.refused(lambda:self.s.start_job(successor['id'],successor['token']))

    def test_metadata_basis_and_append_do_not_acquire_old_bodies_or_other_jobs(self):
        self.diagnosis()
        self.s.db.execute("INSERT INTO jobs(id,role,phase,task,members,controller,token,created,state,hold_reason) "
            "VALUES('unselected708','Work','integrator','work-integrator','[]','unselected','unselected',0,'held','UNACQUIRED_OLD708')")
        forbidden = {'results':None,'artifact_custody':None,'artifact_blobs':None,'outboxes':None,
            'events':{'payload','classification','error','ack_receipt'},
            'attempts':{'error','binding','profile'}, 'enrollments':{'legacy_hold','reconciliation'},
            'recovery_requests':{'receipt','result'},'recovery_dispositions':{'reason'},
            'file_publications':{'target','state','error','proposed_sha','temp','witness'},
            'local_commits':{'state','receipt'},'local_material_commits':{'footprints'}}
        denied = []
        def authorize(action,table,column,db,caller):
            if action == sqlite3.SQLITE_READ and table in forbidden and (forbidden[table] is None or column in forbidden[table]):
                denied.append((table,column)); return sqlite3.SQLITE_DENY
            return sqlite3.SQLITE_OK
        queries = []
        self.s.db.set_trace_callback(queries.append)
        with ExitStack() as stack:
            for method in ('job','attempt','event','source_roles','integration_debt','usage','budget'):
                stack.enter_context(patch.object(self.s,method,side_effect=AssertionError('unselected acquisition: '+method)))
            self.s.db.set_authorizer(authorize)
            try:
                basis = self.basis()
                self.withdraw(self.receipt(basis))
            finally:
                self.s.db.set_authorizer(None)
                self.s.db.set_trace_callback(None)
        self.assertEqual([],denied)
        self.assertNotIn('UNACQUIRED_',encode(basis))
        self.assertFalse(any('unselected708' in sql for sql in queries))

    def test_missing_no_start_active_unknown_uncollected_native_and_diagnosis_refuse(self):
        statements = [
            ("UPDATE jobs SET state=? WHERE id=?",('running',self.job['id'])),
            ("UPDATE jobs SET state=? WHERE id=?",('reserved',self.job['id'])),
            ("UPDATE attempts SET state='unknown' WHERE id=?",(self.attempt,)),
            ("UPDATE attempts SET collected=NULL WHERE id=?",(self.attempt,)),
            ("UPDATE attempts SET detail='{}' WHERE id=?",(self.attempt,)),
            ("UPDATE attempts SET detail='{\"known_not_started\":\"true\",\"resume_disposition\":\"x\"}' WHERE id=?",(self.attempt,)),
            ("UPDATE attempts SET detail='{\"known_not_started\":true}' WHERE id=?",(self.attempt,)),
            ("UPDATE attempts SET detail='not json' WHERE id=?",(self.attempt,)),
            ("UPDATE attempts SET capture='unknown' WHERE id=?",(self.attempt,)),
            ("UPDATE attempts SET cleanup='pending' WHERE id=?",(self.attempt,))]
        statements += [('UPDATE attempts SET '+field+'=? WHERE id=?',(value,self.attempt)) for field,value in
            [('begin',1),('ended',2),('exit',0),('session','fictional-native'),('turn','fictional-turn'),('semantic','DONE'),('result','{}')]]
        for sql,args in statements:
            with self.subTest(sql=sql,args=args), self.mutation(sql,args): self.refused(self.basis)
        d = self.diagnosis()
        for field,value in [('state','running'),('begin',None),('ended',None),('exit',None),('collected',None),('ended',1001.)]:
            with self.subTest(diagnosis=field), self.mutation('UPDATE attempts SET '+field+'=? WHERE id=?',(value,d)):
                self.refused(self.basis)

    def test_exact_owner_token_member_queue_package_and_policy_guards(self):
        receipt = self.receipt()
        self.refused(lambda:self.s.withdraw_integration_no_start(self.job['id'],self.job['token'],'foreign',receipt))
        self.refused(lambda:self.s.integration_no_start_basis(self.job['id'],'wrong-token'))
        statements = [("UPDATE jobs SET members='[]' WHERE id=?",(self.job['id'],)),
            ("UPDATE jobs SET active_attempt='unknown' WHERE id=?",(self.job['id'],)),
            ("UPDATE queue SET job=NULL WHERE event=?",(self.event,)),
            ("UPDATE queue SET state='queued' WHERE event=?",(self.event,)),
            ("UPDATE queue SET package='foreign' WHERE event=?",(self.event,)),
            ("UPDATE queue SET task='work-proposer' WHERE event=?",(self.event,)),
            ("UPDATE events SET hash='changed' WHERE id=?",(self.event,)),
            ("UPDATE local_jobs SET policy='changed' WHERE job=?",(self.job['id'],)),
            ("UPDATE local_jobs SET scope=json_set(scope,'$.lane','discovery') WHERE job=?",(self.job['id'],)),
            ("UPDATE local_jobs SET scope=json_set(scope,'$.inputs',json('[]')) WHERE job=?",(self.job['id'],))]
        for sql,args in statements:
            with self.subTest(sql=sql), self.mutation(sql,args): self.refused(self.basis)
        saved = copy.deepcopy(self.config)
        try:
            self.config['tasks']['work-integrator']['authority'] = 'changed task policy'
            self.refused(self.basis)
        finally:
            self.config.clear(); self.config.update(saved)

    def test_stale_opaque_source_custody_mapping_and_configuration_basis_refuse(self):
        receipt = self.receipt()
        self.s.db.execute('INSERT INTO source_custody(event,basis,owner,binding) VALUES(?,?,?,?)',
            (self.event,'fictional','fictional-original','{"opaque":"UNACQUIRED_CUSTODY708"}'))
        self.refused(lambda:self.withdraw(receipt))
        receipt = self.receipt()
        self.config['limits']['max_jobs'] += 1
        self.refused(lambda:self.withdraw(receipt))
        self.config['limits']['max_jobs'] -= 1
        self.s.db.execute('INSERT INTO input_resolutions(event,version,source_hash,actor,receipt,prior,created) VALUES(?,?,?,?,?,?,?)',
            (self.event,1,'wrong-current-source',self.owner,'{}','{}',1000.))
        self.refused(self.basis)

    def test_publication_effect_local_commits_pending_recovery_and_handoff_refuse(self):
        statements = [
            ("INSERT INTO file_publications(attempt,target,state) VALUES(?,?,'intent')",(self.attempt,'fictional-never-opened')),
            ("INSERT INTO local_commits VALUES(?,'committed','{}')",(self.attempt,)),
            ("INSERT INTO local_point_commits VALUES('a',1,?)",(self.attempt,)),
            ("INSERT INTO local_material_commits(attempt,footprints) VALUES(?,'[]')",(self.attempt,)),
            ("INSERT INTO ordinary_runs VALUES(?,?,'fictional','fictional','{}','intent',NULL)",(self.attempt,self.job['id'])),
            ("INSERT INTO recovery_requests(id,job,attempt,actor,receipt,state,created) VALUES('pending',?,?,?,'{}','pending',1000)",
             (self.job['id'],self.attempt,self.owner)),
            ("UPDATE jobs SET effect_receipt='{}' WHERE id=?",(self.job['id'],)),
            ("UPDATE jobs SET effects='reconciled' WHERE id=?",(self.job['id'],)),
            ("UPDATE jobs SET effects='effectful' WHERE id=?",(self.job['id'],)),
            ("UPDATE jobs SET response='fictional-existing-response' WHERE id=?",(self.job['id'],)),
            ("UPDATE jobs SET collection_handoff='{}' WHERE id=?",(self.job['id'],)),
            ("UPDATE jobs SET recovery_state='unknown' WHERE id=?",(self.job['id'],))]
        for sql,args in statements:
            with self.subTest(sql=sql), self.mutation(sql,args): self.refused(self.basis)

    def test_no_native_broad_unmapped_or_report_policy_exception(self):
        saved = copy.deepcopy(self.config)
        for mutate in [lambda:self.config['tasks']['work-integrator'].update(execution='owner'),
            lambda:self.config['tasks']['work-integrator'].update(ordinary_effects={'kind':'local-ref'}),
            lambda:self.config['tasks']['work-integrator'].pop('routine_completion'),
            lambda:self.config['local_integration']['points']['a'].update(bindings=[{'native':{}}]),
            lambda:self.config['local_integration']['tasks'].clear()]:
            mutate()
            self.refused(self.basis)
            self.config.clear(); self.config.update(copy.deepcopy(saved))
        self.s.processing = object()
        try: self.refused(self.basis)
        finally: self.s.processing = None

    def test_exact_original_prepared_points_and_dynamic_binding_required(self):
        scope = json.loads(self.s.one('SELECT scope FROM local_jobs WHERE job=?',(self.job['id'],))['scope'])
        point = self.config['local_integration']['points']['a']
        basis = {'policy':digest(self.config['local_integration']),'points':{'a':point},
                 'scope':scope,'observed_values':{'a':'UNACQUIRED_PREIMAGE708'}}
        self.s.db.execute('INSERT INTO local_bases VALUES(?,?)',(self.attempt,encode(basis)))
        self.assertNotIn('UNACQUIRED_',encode(self.basis()))
        with self.mutation("UPDATE local_bases SET basis=json_set(basis,'$.points.a.incarnation','changed')"):
            self.refused(self.basis)
        with self.mutation("UPDATE local_bases SET basis='malformed'"): self.refused(self.basis)
        # A separately frozen dynamic namespace also needs the original exact
        # prepared point. No lookup of its generating job/attempt is performed.
        self.config['local_integration']['tasks']['work-integrator'].update(points=[],new_point_prefix='a')
        self.config['local_integration']['points'].clear()
        policy = digest(self.config['local_integration'])
        self.s.db.execute('UPDATE local_jobs SET policy=? WHERE job=?',(policy,self.job['id']))
        basis['policy'] = policy
        self.s.db.execute('UPDATE local_bases SET basis=?',(encode(basis),))
        self.s.db.execute('INSERT INTO local_discovered_points VALUES(?,?,?,?)',('a',encode(point),policy,'unselected-generator708'))
        self.assertEqual(point,self.basis()['local']['points']['a'])
        with self.mutation('DELETE FROM local_bases'): self.refused(self.basis)
        with self.mutation("UPDATE local_discovered_points SET definition=json_set(definition,'$.incarnation','changed')"):
            self.refused(self.basis)
        native = {**point,'bindings':[{'native':{'forbidden':'never queried'}}]}
        basis['points'] = {'a':native}
        self.s.db.execute('UPDATE local_bases SET basis=?',(encode(basis),))
        self.s.db.execute('UPDATE local_discovered_points SET definition=?',(encode(native),))
        self.refused(self.basis)

    def test_all_controller_attestations_and_post_budget_cas_are_required(self):
        self.diagnosis()
        self.s.db.execute("UPDATE jobs SET recovery_owner='fictional-other-closed-controller' WHERE id=?",(self.job['id'],))
        receipt = self.receipt()
        self.assertEqual(2,len(receipt['controllers']))
        for change in [lambda r:r['controllers'].pop(),
            lambda r:r['controllers'][0].update(writers_closed=False),
            lambda r:r['controllers'][0].update(no_launch=False),
            lambda r:r['controllers'][0].update(evidence=[]),
            lambda r:r['controllers'][0].update(end=0)]:
            bad = copy.deepcopy(receipt); change(bad)
            self.refused(lambda:self.withdraw(bad))
        original = selected_source.custody_budget
        def mutate(runtime,incoming):
            original(runtime,incoming)
            runtime.db.execute("UPDATE events SET error='fictional late opaque change' WHERE id=?",(self.event,))
        with patch.object(selected_source,'custody_budget',side_effect=mutate):
            self.refused(lambda:self.withdraw(receipt))
        with patch.object(selected_source,'custody_budget',side_effect=Refusal('fictional full metadata capacity')):
            self.refused(lambda:self.withdraw(receipt))


class DispatcherNoStart715(LocalNoStart708):
    """Run all local proofs against production dispatcher's effects=none path."""

    def collect_no_start(self):
        board = Mock()
        board.completion_authority.side_effect = Refusal('fictional prelaunch delegation unavailable')
        # Restore the fixture's launch hooks after constructing the dispatcher.
        # The real execute/prepare/collect/effects path runs. Stop before final
        # response disposition, matching the original stopped-service premise;
        # do not create a response and then erase it to qualify the fixture.
        with patch.object(self.s,'launch_authorizer',None,create=True), \
                patch.object(self.s,'task_launch_authorizer',None,create=True):
            dispatcher = Dispatcher(self.s,models=object(),boards={'Work':board})
            with patch.object(dispatcher,'run_model',new_callable=AsyncMock,
                              side_effect=AssertionError('no model may launch')) as model, \
                    patch.object(dispatcher,'try_finish') as finish:
                asyncio.run(dispatcher.execute(self.job['id'],self.attempt))
                model.assert_not_awaited()
                finish.assert_called_once_with(self.job['id'])
        board.completion_authority.assert_called_once()
        self.assertEqual('none',self.s.job(self.job['id'])['effects'])
        self.assertIsNone(self.s.job(self.job['id'])['response'])
        original = self.s.attempt(self.attempt)
        self.assertEqual('not-started',original['state'])
        for field in ('begin','ended','exit','session','turn','semantic','result'):
            self.assertIsNone(original[field],field)
        self.assertIsNotNone(original['collected'])
        self.assertTrue(json.loads(original['detail'])['known_not_started'])


@unittest.skipUnless(__name__ == '__main__', 'requires explicit owned --fixtures root')
class PausedLocal708(unittest.TestCase):
    call = metadata.MetadataClosure671.call
    selection = metadata.MetadataClosure671.selection

    def setUp(self):
        self.f = managed.Management(methodName='runTest')
        self.addCleanup(self.f.doCleanups)
        with patch.object(managed,'config_at',side_effect=configuration): self.f.setUp()
        self.store, self.owner = self.f.store,self.f.owner
        self.job,self.token = 'synthetic-held','synthetic-token'
        self.store.db.execute('DELETE FROM file_publications')
        self.store.db.execute("UPDATE attempts SET state='not-started',begin=NULL,ended=NULL,exit=NULL,semantic=NULL,result=NULL,"
            "capture='not-started',cleanup='no-session-created',detail=?",(encode({'known_not_started':True,'resume_disposition':'fictional no launch'}),))
        self.store.db.execute('INSERT INTO job_resource_policies VALUES(?,?,NULL)',
            (self.job,encode(self.store.config['tasks']['work-integrator'])))
        packet = {'lane':'anchored','reads':['a'],'writes':['a'],'versions':{'a':'fictional-original'},'sources':[self.f.source['id']]}
        self.store.db.execute('INSERT INTO local_jobs VALUES(?,?,?)',
            (self.job,digest(self.store.config['local_integration']),encode(local.combine([packet]))))
        self.authority = management.basis(self.store,['Work'],self.owner,'Fictional current genuine Work',
                                         'Fictional exact local withdrawal only',metadata_only=True)

    def basis(self):
        return self.call('integration-no-start-basis')

    def receipt(self):
        basis = self.basis()
        return {'basis':basis,'reason':'Fictional paused exact local no-start withdrawal',
            'controllers':[{'controller':c,'collector':'fictional actual collector','writers_closed':True,
                'no_launch':True,'evidence':['fictional service stopped, all children and callbacks closed']}
                for c in basis['controllers']]}

    def test_real_paused_cli_authority_and_audit_conserve_every_other_duty(self):
        receipt = self.receipt()
        before = self.f.conserved()
        self.call('withdraw-integration-no-start',receipt=receipt)
        after = self.f.conserved()
        for table in before:
            if table not in {'jobs','queue','integration_management_operations'}:
                self.assertEqual(before[table],after[table],table)
        self.assertEqual(1,len(after['integration_management_operations']))
        self.assertEqual([],self.store.rows('SELECT * FROM processing_capabilities'))
        self.assertEqual(0,self.store.one("SELECT intake FROM enrollments WHERE role='Work'")['intake'])
        self.assertIsNone(self.store.reserve())
        self.assertEqual({'state':'queued','job':None},self.store.one('SELECT state,job FROM queue WHERE event=?',(self.f.source['id'],)))

    def test_known_none_paused_cli_conserves_original_effect_status(self):
        self.store.db.execute("UPDATE jobs SET effects='none' WHERE id=?",(self.job,))
        self.test_real_paused_cli_authority_and_audit_conserve_every_other_duty()
        self.assertEqual('none',self.store.one('SELECT effects FROM jobs WHERE id=?',(self.job,))['effects'])

    def test_owner_source_token_scope_operation_and_processing_substitution_refuse(self):
        for modify in [lambda s:s['records'].update(events=[]),lambda s:s['records'].update(jobs=[]),
            lambda s:s['target'].update(token='wrong'),lambda s:s.update(operation='retire-integration-metadata'),
            lambda s:s['basis']['roles'].clear(),lambda s:s['basis'].update(configuration='stale')]:
            selection = self.selection('integration-no-start-basis'); modify(selection)
            with self.assertRaises(Refusal): self.call('integration-no-start-basis',selection=selection)
        with self.assertRaises(Refusal): self.call('integration-no-start-basis',actor=self.store.config['roles']['Branch']['owner'])
        with self.assertRaises(Refusal): self.call('integration-no-start-basis',ordinary=True)
        self.store.processing = object()
        try:
            with self.assertRaises(Refusal): self.basis()
        finally: self.store.processing = None

    def test_management_audit_failure_rolls_back_append_and_queue_return(self):
        self.store.db.execute("CREATE TRIGGER fictional_audit_failure BEFORE INSERT ON integration_management_operations "
                              "BEGIN SELECT RAISE(ABORT,'fictional audit failure'); END")
        receipt = self.receipt()
        before = self.f.conserved()
        with self.assertRaises(sqlite3.IntegrityError): self.call('withdraw-integration-no-start',receipt=receipt)
        self.assertEqual(before,self.f.conserved())
        self.assertEqual([],self.store.rows('SELECT * FROM integration_prestart_dispositions'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--fixtures',required=True)
    parser.add_argument('--legacy',action='store_true')
    parser.add_argument('--management-guards',action='store_true')
    args = parser.parse_args()
    FIXTURES = Path(args.fixtures)
    if not FIXTURES.is_absolute(): raise ValueError('absolute owned fixture root required')
    FIXTURES.mkdir(mode=0o700,parents=True,exist_ok=False)
    with patch.object(managed.tempfile,'TemporaryDirectory',RetainedDirectory):
        if args.legacy:
            # Keep all legacy lifecycle assertions, full Store, race controls,
            # authority refusals and guards. Only the forbidden /proc preamble
            # is replaced by the independently admitted owned headroom check.
            legacy.base.FIXTURES = FIXTURES
            def setup(case):
                owned_headroom()
                legacy.base.Controls.setUp(case)
            original_store = legacy.base.Store
            def fixture_store(config, **kwargs):
                # Newer production accounting reserves max_artifact_bytes per
                # unresolved publication. Admit 1 KiB for this literal fictional
                # intent instead of the absent legacy default (the whole 8 MiB).
                # Keep real budget(), its 8 MiB cap and all refusal assertions.
                config['limits']['max_artifact_bytes'] = 1024
                return original_store(config, **kwargs)
            with patch.object(legacy.Controls,'setUp',setup), patch.object(legacy.base,'Store',side_effect=fixture_store):
                suite = unittest.TestSuite(legacy.Controls(n) for n in dir(legacy.Controls) if n.startswith('test77_'))
                result = unittest.TextTestRunner(verbosity=2).run(suite)
        elif args.management_guards:
            result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(managed.Management))
        else:
            suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(c)
                                      for c in (LocalNoStart708,DispatcherNoStart715,PausedLocal708))
            result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(not result.wasSuccessful())
