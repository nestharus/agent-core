"""Fresh fictional grants/journals; no prior producer output or actual state.

Only support.config_at (a source config constructor) is reused. Every original,
policy, opaque sentinel and closure assertion below is newly constructed. SQL
authorizers plus result/query guards distinguish scalar predicates from full
task/member transport. Fixture storage is retained by the owning runner.
"""
from contextlib import contextmanager, ExitStack
import copy
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from support import config_at
from coordinator_runtime import cli, integration_management as management, local_integration as local
from coordinator_runtime import configuration, selected_source, work_read_metadata
from coordinator_runtime.board import Board, module_at
from coordinator_runtime.contracts import Refusal, digest, encode
from coordinator_runtime.store import Store


class WorkReadMetadata686(unittest.TestCase):
    def setUp(self):
        self.home = Path(tempfile.mkdtemp(prefix='metadata686-', dir='/fixtures'))
        self.config = config_at(self.home)
        self.owner = self.config['roles']['Work']['owner']
        self.config['software_delegation'] = {'grantor': self.owner,
            'authority': 'Fictional original Work delegation686', 'boundary': 'new-journal-only'}
        self.config['delivery'] = {'recipients':{r:{'session':s['owner'],'profile':s['profile'],
            'board_role':s['board_role']} for r,s in self.config['roles'].items()}}
        self.target = self.home/'fictional-file.json'
        self.target.write_text('{"item":{"id":"p","state":"old"}}')
        self.config['local_integration'] = {'max_inflight': 5, 'points': {'p': {
            'kind':'item', 'line':'fiction686', 'incarnation':'fiction686-only',
            'bindings':[{'target':str(self.target), 'path':['item']}], 'resources':[],
            'protected':['id'], 'writable':['state']}}, 'tasks': {'work-proposer': {
                'capacity': 5, 'discovery_batch': 1, 'points':['p'],
                'authority':'Fictional exact FILE read choice686',
                'method':self.config['tasks']['work-proposer']['templates'][0]}}}
        self.store = Store(self.config, clock=lambda: 1000.)
        self.addCleanup(self.store.close)
        self.boards = {}
        catalog = module_at(self.config['board_library'], 'catalog')
        substrate = module_at(self.config['board_library'], 'board_store')
        for role in ('Work', 'Branch'):
            selected = self.config['roles'][role]
            with catalog.catalog(Path(self.config['board_home'])) as conn:
                entry = catalog.create(conn, Path(self.config['board_home']), 'fiction686-'+role.lower(),
                    'Fresh fictional metadata fence686 only', board_id=selected['board_id'], temporary_test=True)
            with substrate.database(entry['db_path']) as conn:
                substrate.bind_board(conn, selected['board_id'], initialize=True)
                args = substrate.parser().parse_args(['register', '--session', selected['owner'],
                    '--role', selected['board_role'], '--profile', selected['profile'], '--route', 'managed'])
                with patch.dict(os.environ, {'CODEX_SESSION_ID': selected['owner']}):
                    substrate.register(conn, args)
            board = Board(self.config, role)
            with patch.dict(os.environ, {'CODEX_SESSION_ID': self.owner}):
                self.store.enroll(role, board.grant_software(self.store, self.config['software_delegation']['authority']))
            self.boards[role] = board
        self.job, self.token = 'fiction686-old-proposer', 'fiction686-old-token'
        self.insert('events', {'id':'fiction686-source', 'role':'Work', 'payload':'OPAQUE686_SOURCE',
            'hash':'OPAQUE686_MEMBER_HASH', 'received':1., 'state':'queued', 'ack':'done', 'hold':'OPAQUE686_HOLD'})
        self.insert('queue', {'id':'fiction686-queue', 'event':'fiction686-source', 'role':'Work',
            'phase':'proposer', 'task':'work-proposer', 'state':'reserved', 'job':self.job})
        self.insert('jobs', {'id':self.job, 'role':'Work', 'phase':'proposer', 'task':'work-proposer',
            'members':encode([{'queue':'fiction686-queue', 'event':'fiction686-source',
                              'hash':'OPAQUE686_MEMBER_HASH', 'package':None}]),
            'controller':'fiction686-parent', 'token':self.token, 'created':2., 'state':'held',
            'active_attempt':'fiction686-task', 'effects':'none', 'hold_reason':'OPAQUE686_HOLD',
            'effect_receipt':'OPAQUE686_EFFECT', 'response':'OPAQUE686_RESPONSE'})
        self.policy = copy.deepcopy(self.config['tasks']['work-proposer'])
        self.policy['opaque_old_scope'] = 'OPAQUE686_SCOPE_AND_TASK'
        self.insert('job_resource_policies', {'job':self.job, 'task':encode(self.policy)})
        self.insert('attempts', {'id':'fiction686-task', 'kind':'task', 'job':self.job,
            'controller':'fiction686-parent', 'profile':'fiction', 'binding':'OPAQUE686_BINDING',
            'state':'collected', 'created':2., 'begin':3., 'ended':4., 'collected':5., 'exit':0,
            'capture':'OPAQUE686_CAPTURE', 'semantic':'PARTIAL', 'error':'OPAQUE686_ERROR',
            'detail':'OPAQUE686_DETAIL', 'result':'OPAQUE686_RESULT', 'cleanup':'OPAQUE686_CLEANUP'})
        self.insert('results', {'attempt':'fiction686-task', 'job':self.job, 'result':'OPAQUE686_RESULT',
            'error':'OPAQUE686_ERROR', 'exit':0, 'capture':'OPAQUE686_CAPTURE', 'created':5.})
        self.insert('outboxes', {'id':'fiction686-outbox', 'role':'Work', 'job':self.job,
            'producer':'fiction686-parent', 'recipient':'Work', 'kind':'question',
            'required':'settled', 'payload':'OPAQUE686_DELIVERY', 'state':'sent', 'created':6.})
        self.insert('artifact_custody', {'attempt':'fiction686-task', 'path':'OPAQUE686_ARTIFACT',
            'kind':'report', 'owner':'fiction686-original-custodian', 'witness':'OPAQUE686_WITNESS', 'sha256':'OPAQUE686_HASH'})
        self.insert('ordinary_resources', {'resource':'fiction686-unreleased-resource', 'attempt':'fiction686-task'})
        for role, board in self.boards.items():
            with patch.dict(os.environ, {'CODEX_SESSION_ID': self.owner}):
                board.revoke_software(self.store, self.store.enrollment(role)['grant_id'])
        self.store.db.execute('UPDATE enrollments SET intake=0')
        self.authority = self.management_basis(['Work'])

    def insert(self, table, values):
        self.store.db.execute('INSERT INTO '+table+'('+','.join(values)+') VALUES('+','.join('?' for _ in values)+')',
                              tuple(values.values()))

    def management_basis(self, roles):
        return management.basis(self.store, roles, self.owner, 'Fictional Work actual management686',
                                'Fictional exact nonwriting metadata fence686', metadata_only=True)

    def selection(self, command):
        return {'basis':copy.deepcopy(self.authority), 'expires':1100., 'operation':command,
            'target':{'job':self.job, 'token':self.token},
            'records':{'jobs':[self.job], 'events':['fiction686-source']}}

    def call(self, command, *, receipt=None, selection=None, ordinary=False, actor=None):
        argv = [command, self.job, '--token', self.token]
        if not ordinary:
            path = self.home/'fiction686-selection.json'
            path.write_text(encode(selection if selection is not None else self.selection(command)))
            argv += ['--management', str(path)]
        if receipt is not None:
            path = self.home/'fiction686-receipt.json'; path.write_text(encode(receipt))
            argv += ['--receipt', str(path)]
        with patch.dict(os.environ, {'CODEX_SESSION_ID': actor or self.owner}):
            return cli.operate(cli.parser().parse_args(argv), self.store)

    def basis(self):
        return self.call('work-read-metadata-closure-basis')

    def receipt(self, basis=None):
        selected = basis if basis is not None else self.basis()
        return {'basis':selected, 'reason':'Fiction686: fence closed controllers only; retain every UNKNOWN',
            'controllers':[{'controller':c, 'collector':'fiction686-actual-original-collector', 'end':2,
                'collected':True, 'writers_closed':True,
                'evidence':['Fiction686 external closure of parent, descendants and launch-capable writers; no actual facts']}
                for c in selected['controllers']]}

    def fence(self, receipt=None):
        return self.call('fence-work-proposer-metadata', receipt=receipt if receipt is not None else self.receipt())

    @contextmanager
    def metadata_only(self):
        forbidden = {'results':None, 'artifact_custody':None, 'artifact_blobs':None, 'outboxes':None,
            'attempts':{'capture','semantic','error','result','detail','cleanup','binding','profile','session','turn'},
            'jobs':{'effect_receipt','response','hold_reason','collection_handoff'},
            'events':{'payload','hash','classification','classifier','hold','error','ack_receipt'},
            'enrollments':{'legacy_hold','reconciliation'}, 'job_resource_policies':{'admission'},
            'local_jobs':{'policy','scope'}, 'file_publications':{'target','state','witness','receipt','error'},
            'recovery_requests':{'receipt','result'}, 'recovery_dispositions':{'reason'}}
        denied = []
        def authorize(action, table, column, db, caller):
            if action == sqlite3.SQLITE_READ and table in forbidden and (
                    forbidden[table] is None or column in forbidden[table]):
                denied.append((table, column)); return sqlite3.SQLITE_DENY
            return sqlite3.SQLITE_OK
        one, rows, scandir = self.store.one, self.store.rows, os.scandir
        def guard(method, sql, *args):
            if 'job_resource_policies' in sql and not sql.startswith('SELECT type,name'):
                self.assertTrue(sql.startswith('SELECT 1 AS nonwriting '), sql)
                for key in ('role', 'phase', 'sandbox', 'effects', 'network', 'effect_authority.write_roots'):
                    self.assertIn("json_extract(task,'$."+key+"')", sql)
            if 'json_each(j.members)' in sql:
                self.assertNotIn('hash', sql)
            value = method(sql, *args)
            self.assertNotIn('OPAQUE686', json.dumps(value,sort_keys=True,allow_nan=True))
            return value
        def scan(path):
            if Path(path).is_relative_to(self.home):
                raise AssertionError('fixture/capture traversal forbidden')
            return scandir(path)
        with ExitStack() as stack:
            for name in ('job','attempt','event','source_roles','integration_debt','usage','budget','_work_read_basis'):
                stack.enter_context(patch.object(self.store, name, side_effect=AssertionError('legacy/body acquisition '+name)))
            stack.enter_context(patch.object(self.store, 'one', side_effect=lambda sql,*a:guard(one,sql,*a)))
            stack.enter_context(patch.object(self.store, 'rows', side_effect=lambda sql,*a:guard(rows,sql,*a)))
            stack.enter_context(patch('os.scandir', side_effect=scan))
            self.store.db.set_authorizer(authorize)
            try:
                yield
            finally:
                self.store.db.set_authorizer(None)
        self.assertEqual(denied, [])

    def conserved(self):
        tables = ('jobs','attempts','results','events','queue','outboxes','artifact_custody','file_publications',
            'source_custody','recovery_requests','recovery_dispositions','job_resource_policies','local_jobs',
            'enrollments','ordinary_resources','processing_capabilities','artifacts','integration_retirements')
        return {t:self.store.rows('SELECT * FROM '+t+' ORDER BY rowid') for t in tables}

    def incoming(self, task='work-proposer'):
        return {'id':'fiction686-new-job', 'role':'Work', 'phase':self.config['tasks'][task]['phase'], 'task':task}

    def scope(self):
        return {'lane':'anchored','reads':['p'],'writes':[]}

    def coexists(self, scope=None, row=None):
        return self.store.work_read_coexists(row or self.incoming(), scope or self.scope(), {'id':self.job})

    @contextmanager
    def mutation(self, table, field, value, *, key='id', identity=None):
        old = self.store.one('SELECT '+field+' FROM '+table+' WHERE '+key+'=?', (identity or self.job,))[field]
        self.store.db.execute('UPDATE '+table+' SET '+field+'=? WHERE '+key+'=?', (value,identity or self.job))
        try:
            yield
        finally:
            self.store.db.execute('UPDATE '+table+' SET '+field+'=? WHERE '+key+'=?', (old,identity or self.job))

    def test_metadata_basis_fence_and_revalidation_acquire_zero_forbidden_columns(self):
        before = self.conserved()
        with self.metadata_only():
            selected = self.basis()
            self.assertEqual(selected['schema'], work_read_metadata.SCHEMA)
            self.fence(self.receipt(selected))
            self.assertTrue(self.coexists())
        self.assertEqual(before, self.conserved())
        self.assertFalse(self.store.execution_complete(self.store.job(self.job)))
        self.assertEqual(len(self.store.rows('SELECT job FROM work_read_fences')), 1)
        self.assertEqual(len(self.store.rows('SELECT id FROM integration_management_operations')), 1)
        for operation in (lambda:self.store.require_execution_open(self.job),
                          lambda:self.store.start_job(self.job,self.token),
                          lambda:self.store.finish_job(self.job,self.token),
                          lambda:self.store.request_recovery(self.job,self.token,'fiction686-task',self.owner,{})):
            with self.assertRaises(Refusal): operation()
        with self.metadata_only(), self.assertRaises(Refusal): self.fence(self.receipt(selected))

    def test_token_is_checked_before_any_relationship_or_policy(self):
        with self.metadata_only(), patch.object(self.store,'integration_metadata_sources',
                side_effect=AssertionError('relationships before required token')):
            for missing in (None, ''):
                with self.subTest(token=missing), self.assertRaises(Refusal):
                    self.store.work_read_metadata_closure_basis(self.job,missing,self.owner)
        self.token = 'fiction686-wrong-token'
        with self.metadata_only(), patch.object(self.store, 'integration_metadata_sources',
                side_effect=AssertionError('relationships before token')):
            with self.assertRaises(Refusal): self.basis()

    def activate_fictional_originals(self):
        # Models the still-current ordinary case, never revives an actual grant.
        for board in self.boards.values():
            with sqlite3.connect(board.path) as conn:
                conn.execute('UPDATE coordinator_grants_v1 SET revoked=NULL')
        self.store.db.execute('UPDATE enrollments SET intake=1')

    def test_ordinary_active_owner_cli_uses_metadata_grant_checks(self):
        self.activate_fictional_originals()
        with patch.object(configuration,'assert_release',side_effect=Refusal('fiction686 changed release')):
            with self.metadata_only(), self.assertRaises(Refusal):
                self.call('work-read-metadata-closure-basis',ordinary=True)
        with self.metadata_only():
            selected = self.call('work-read-metadata-closure-basis', ordinary=True)
            self.call('fence-work-proposer-metadata', ordinary=True, receipt=self.receipt(selected))
            self.assertTrue(self.coexists())

    def test_real_reservation_and_launch_keep_general_capacity_and_old_duties(self):
        from support import event, queued
        self.fence()
        self.activate_fictional_originals()
        for role in self.boards:
            self.store.reconcile_legacy(role,self.config['roles'][role]['owner'],{
                'collector':'fiction686-prior-collector','evidence':['fiction686-closed'],'remaining_holds':[]})
        source = event(self.config,'fiction686-new-input',task='work-proposer')
        source['integration'] = {'reads':['p'],'writes':[],
            'versions':{'p':local.version(self.store,'p',{str(self.target):self.target.read_bytes()})}}
        queued(self.store,source)
        self.config['local_integration']['max_inflight'] = 1
        self.assertIsNone(self.store.reserve())
        self.config['local_integration']['max_inflight'] = 5
        self.config['local_integration']['tasks']['work-proposer']['capacity'] = 1
        self.assertIsNone(self.store.reserve())
        self.config['local_integration']['tasks']['work-proposer']['capacity'] = 5
        before = self.store.job(self.job)
        fresh = self.store.reserve(); self.assertIsNotNone(fresh)
        self.assertEqual(local.scope_for(self.store,fresh)['read_fences'],[self.job])
        attempt = self.store.start_job(fresh['id'],fresh['token'])
        self.assertIsNotNone(attempt)
        self.assertEqual(before,self.store.job(self.job))
        self.assertFalse(self.store.execution_complete(before))
        self.assertEqual(self.store.rows('SELECT * FROM file_publications'),[])
        self.assertTrue(all(r['processed_at'] is None for r in self.store.rows('SELECT processed_at FROM events')))

    def test_exact_management_owner_roles_records_operation_and_currentness(self):
        command = 'work-read-metadata-closure-basis'
        changes = [lambda s:s.update(operation='fence-work-proposer-metadata'),
            lambda s:s['target'].update(token='fiction-wrong'), lambda s:s['records'].update(jobs=[]),
            lambda s:s['records'].update(events=[]), lambda s:s['records']['events'].append('fiction-extra'),
            lambda s:s.update(expires=999.), lambda s:s['basis'].pop('schema'),
            lambda s:s['basis'].update(configuration='fiction-stale'),
            lambda s:s['basis']['implementation'].update({'work_read_metadata.py':'fiction-stale'}),
            lambda s:s['basis'].update(purpose='')]
        for change in changes:
            selection = self.selection(command); change(selection)
            with self.subTest(change=change), self.metadata_only(), self.assertRaises(Refusal):
                self.call(command, selection=selection)
        with self.metadata_only(), self.assertRaises(Refusal): self.call(command, actor=self.config['roles']['Branch']['owner'])
        with self.metadata_only(), self.assertRaises(Refusal): self.call(command, ordinary=True)
        with patch.object(self.store, 'processing', object()), self.assertRaises(Refusal):
            self.store.work_read_metadata_closure_basis(self.job,self.token,self.owner)
        self.store.db.execute("UPDATE events SET role='Branch' WHERE id='fiction686-source'")
        with self.metadata_only(), self.assertRaisesRegex(Refusal,'source roles'): self.basis()
        self.authority = self.management_basis(['Work','Branch'])
        with self.metadata_only(): self.assertEqual(self.basis()['predecessor']['sources'][0]['role'], 'Branch')
        for field, value in [('event','fiction-missing'),('job','fiction-other'),('phase','integrator'),('task','work-integrator')]:
            # Foreign-key-safe wrong event uses the existing event with an
            # intentionally wrong frozen relationship only for other columns.
            if field == 'event': continue
            with self.subTest(field=field), self.mutation('queue',field,value,identity='fiction686-queue'), self.metadata_only(), self.assertRaises(Refusal):
                self.basis()

    def test_original_grants_membership_and_current_source_checks_remain(self):
        board = self.boards['Work']
        for table, field, expression in [('coordinator_grants_v1','runtime_ino','runtime_ino+1'),
                ('coordinator_grants_v1','revoked','NULL'),
                ('coordinator_software_grants_v1','configuration',"'fiction686-stale'"),
                ('sessions','status',"'paused'")]:
            with self.subTest(field=field), sqlite3.connect(board.path) as conn:
                old = conn.execute('SELECT rowid,'+field+' FROM '+table).fetchall()
                conn.execute('UPDATE '+table+' SET '+field+'='+expression); conn.commit()
                try:
                    with self.metadata_only(), self.assertRaises(Refusal): self.basis()
                finally:
                    conn.executemany('UPDATE '+table+' SET '+field+'=? WHERE rowid=?', [(v,k) for k,v in old]); conn.commit()
        with patch.object(configuration,'assert_current',side_effect=Refusal('fiction current source changed')):
            with self.assertRaises(Refusal): self.basis()
        with patch.object(configuration,'assert_release',side_effect=Refusal('fiction selected release changed')):
            with self.assertRaises(Refusal): self.basis()

    def test_original_policy_is_scalar_checked_and_current_safe_task_cannot_replace_writer(self):
        changes = [('role','Branch'),('phase','integrator'),('sandbox','workspace-write'),('effects','unknown'),
            ('network',True),('network',0),('network','false'),('execution','owner'),
            ('routine_completion',{'kind':'fiction-write'}),('effect_authority',{'write_roots':[str(self.home)]}),
            ('effect_authority',{'write_roots':{}}),('effect_authority',{})]
        old_job = self.store.job(self.job)
        for index, (key,value) in enumerate(changes):
            candidate = copy.deepcopy(self.policy); candidate[key] = value
            new_id = 'fiction686-bad-policy-'+str(index)
            self.insert('jobs', {**old_job, 'id':new_id})
            self.insert('job_resource_policies', {'job':new_id, 'task':encode(candidate)})
            with self.subTest(key=key,value=value), self.metadata_only(), self.assertRaisesRegex(Refusal,'original frozen'):
                self.store.work_read_metadata_closure_basis(new_id,self.token,self.owner)
        self.insert('jobs', {**old_job, 'id':'fiction686-missing-policy'})
        with self.metadata_only(), self.assertRaisesRegex(Refusal,'original frozen'):
            self.store.work_read_metadata_closure_basis('fiction686-missing-policy',self.token,self.owner)

    def test_local_scope_and_any_publication_row_refuse(self):
        self.insert('local_jobs', {'job':self.job,'policy':'OPAQUE686_POLICY','scope':'OPAQUE686_SCOPE'})
        with self.metadata_only(), self.assertRaisesRegex(Refusal,'unknown original local scope'): self.basis()

    def test_publication_presence_refuses_without_acquiring_its_contents(self):
        self.insert('file_publications', {'attempt':'fiction686-task','target':'OPAQUE686_TARGET',
                                        'state':'intent','error':'OPAQUE686_ERROR'})
        with self.metadata_only(), self.assertRaisesRegex(Refusal,'publication duties'): self.basis()

    def test_all_original_numeric_finite_order_and_controller_guards(self):
        changes = [('begin',None),('ended',None),('collected',None),('exit',None),('exit','unknown'),('exit',0.5),
            ('begin','unknown'),('ended',float('inf')),('begin',-1),('collected',2),('state','running'),
            ('kind','diagnosis'),('controller','fiction-other'),('job','fiction-other')]
        for field,value in changes:
            with self.subTest(field=field,value=value), self.mutation('attempts',field,value,identity='fiction686-task'), self.metadata_only(), self.assertRaises(Refusal):
                self.basis()
        for field,value in [('state','running'),('effects','unknown'),('role','Branch'),('phase','integrator'),('active_attempt','missing')]:
            with self.subTest(field=field), self.mutation('jobs',field,value), self.metadata_only(), self.assertRaises(Refusal): self.basis()

    def test_every_additional_original_recovery_owner_and_pending_request(self):
        self.insert('attempts', {'id':'fiction686-diagnosis','kind':'diagnosis','job':self.job,
            'controller':'fiction686-diagnoser','profile':'fiction','binding':'OPAQUE686_BINDING','created':6.,'state':'running'})
        with self.metadata_only(), self.assertRaises(Refusal): self.basis()
        self.store.db.execute("UPDATE attempts SET state='collected',begin=7.,ended=8.,collected=9.,exit=17 WHERE id='fiction686-diagnosis'")
        self.store.db.execute("UPDATE jobs SET recovery_owner='fiction686-recovery',recovery_state='owner-deferred',recovery_count=1")
        with self.metadata_only():
            receipt = self.receipt()
            self.assertEqual(set(receipt['basis']['controllers']), {'fiction686-parent','fiction686-diagnoser','fiction686-recovery'})
            for controller in receipt['basis']['controllers']:
                bad = copy.deepcopy(receipt); bad['controllers'] = [c for c in bad['controllers'] if c['controller'] != controller]
                with self.assertRaises(Refusal): self.fence(bad)
        self.insert('recovery_requests', {'id':'fiction686-pending','job':self.job,'attempt':'fiction686-task',
            'actor':self.owner,'receipt':'OPAQUE686_RECOVERY','state':'pending','created':10.})
        with self.metadata_only(), self.assertRaisesRegex(Refusal,'pending owner recovery'): self.basis()
        self.store.db.execute("UPDATE recovery_requests SET state='consumed'")
        with self.metadata_only(): self.fence()

    def test_recovery_state_is_inactive_and_exact(self):
        for state,owner,count in [('claimed','fiction-r',1),('diagnosing','fiction-r',1),('unknown','fiction-r',1),
                ('awaiting-disposition',None,1),(None,'fiction-r',1),(None,None,1),('handed-off','fiction-r',1)]:
            with self.subTest(state=state), self.mutation('jobs','recovery_state',state), self.mutation('jobs','recovery_owner',owner), self.mutation('jobs','recovery_count',count), self.metadata_only(), self.assertRaises(Refusal): self.basis()
        self.store.db.execute("UPDATE jobs SET recovery_owner=controller,recovery_state='handed-off',recovery_count=1")
        with self.metadata_only(): self.fence()

    def test_controller_end_collection_writer_evidence_are_all_required(self):
        receipt = self.receipt()
        for key,value in [('controller','foreign'),('collector',''),('end',None),('end',True),('end','0'),
                ('collected',False),('writers_closed',False),('evidence',[])]:
            bad = copy.deepcopy(receipt); bad['controllers'][0][key] = value
            with self.subTest(key=key), self.metadata_only(), self.assertRaises(Refusal): self.fence(bad)
        for change in (lambda r:r.update(reason=''), lambda r:r.update(ack=True), lambda r:r.update(controllers=[])):
            bad = copy.deepcopy(receipt); change(bad)
            with self.metadata_only(), self.assertRaises(Refusal): self.fence(bad)

    def test_opaque_mutation_and_reverted_metadata_invalidate_registration(self):
        for table,field,value,identity in [('jobs','response','OPAQUE686_LATER',self.job),
                ('attempts','capture','OPAQUE686_LATER','fiction686-task'),
                ('events','payload','OPAQUE686_LATER','fiction686-source')]:
            receipt = self.receipt()
            with self.subTest(table=table), self.mutation(table,field,value,identity=identity), self.metadata_only(), self.assertRaisesRegex(Refusal,'basis changed'): self.fence(receipt)
        receipt = self.receipt()
        with self.mutation('attempts','ended',4.5,identity='fiction686-task'): pass
        with self.metadata_only(), self.assertRaisesRegex(Refusal,'basis changed'): self.fence(receipt)

    def test_final_revision_and_audit_failures_roll_back(self):
        receipt = self.receipt(); before = self.conserved()
        budget = selected_source.custody_budget
        def changed(runtime,incoming):
            self.assertTrue(runtime.db.in_transaction); budget(runtime,incoming)
            runtime.db.execute("UPDATE attempts SET error='OPAQUE686_CHANGED_IN_TX'")
        with self.metadata_only(), patch.object(selected_source,'custody_budget',side_effect=changed), self.assertRaisesRegex(Refusal,'revision changed'): self.fence(receipt)
        self.assertEqual(before,self.conserved())
        self.assertEqual(self.store.rows('SELECT job FROM work_read_fences'),[])
        self.store.db.execute("CREATE TRIGGER fiction686_audit_failure BEFORE INSERT ON integration_management_operations BEGIN SELECT RAISE(ABORT,'fiction686 audit unavailable'); END")
        receipt = self.receipt()
        with self.metadata_only(), self.assertRaisesRegex(sqlite3.IntegrityError,'audit unavailable'): self.fence(receipt)
        self.assertEqual(before,self.conserved())
        self.assertEqual(self.store.rows('SELECT job FROM work_read_fences'),[])

    def test_metadata_budget_and_size_refuse_without_history_accounting(self):
        receipt = self.receipt()
        with self.metadata_only(), patch.object(selected_source,'custody_budget',side_effect=Refusal('fiction686 full')), self.assertRaises(Refusal): self.fence(receipt)
        receipt['reason'] = 'x'*5000
        with self.metadata_only(), self.assertRaises(Refusal): self.fence(receipt)
        self.assertEqual(self.store.rows('SELECT job FROM work_read_fences'),[])

    def test_immutable_fence_survives_reopen_and_unrelated_future_allocations(self):
        self.fence()
        for statement in ('UPDATE work_read_fences SET actor=actor','DELETE FROM work_read_fences'):
            with self.assertRaisesRegex(sqlite3.IntegrityError,'immutable metadata'): self.store.db.execute(statement)
        # Neither this unrelated activity nor the fence/audit inserts themselves
        # should stale a permanent closed-execution witness.
        self.store.db.execute("UPDATE events SET error='OPAQUE686_LATER_CONSUMER_DUTY'")
        with self.metadata_only(): self.assertTrue(self.coexists())
        reopened = Store(self.config,clock=lambda:1000.)
        try:
            with patch.object(reopened,'_work_read_basis',side_effect=AssertionError('legacy full read')):
                self.assertTrue(reopened.work_read_coexists(self.incoming(),self.scope(),{'id':self.job}))
        finally:
            reopened.close()

    def test_coexist_file_only_anchored_authority_and_changed_execution_metadata(self):
        self.fence()
        bad_scopes = [{'lane':'discovery','reads':['p'],'writes':[]},
            {'lane':'anchored','reads':[],'writes':[]}, {'lane':'anchored','reads':['p'],'writes':['p']}]
        with self.metadata_only():
            for scope in bad_scopes: self.assertFalse(self.coexists(scope))
            self.assertFalse(self.coexists(row={**self.incoming(),'role':'Branch'}))
            self.config['local_integration']['points']['p']['bindings'].append({'native':'branch','id':'fiction686-native'})
            try:
                self.assertFalse(self.coexists())
            finally:
                self.config['local_integration']['points']['p']['bindings'].pop()
        task = self.config['tasks']['work-proposer']
        task['effect_authority']['write_roots'] = [str(self.home)]
        with self.metadata_only(): self.assertFalse(self.coexists())
        task['effect_authority']['write_roots'] = []
        with self.mutation('attempts','ended',4.5,identity='fiction686-task'), self.metadata_only(): self.assertFalse(self.coexists())
        with self.mutation('jobs','state','running'), self.metadata_only(), self.assertRaises(Refusal): self.coexists()
        integrator = self.config['tasks']['work-integrator']
        integrator.update(effects='owner-reconcile',sandbox='workspace-write',network=False,
                          routine_completion={'fiction686':'separate ordinary publication guards still required'})
        with self.metadata_only():
            self.assertTrue(self.coexists({'lane':'anchored','reads':['p'],'writes':['p']},self.incoming('work-integrator')))

    def test_launch_revalidation_does_not_fetch_full_predecessor_job(self):
        self.fence()
        scope = {**self.scope(),'sources':[], 'neighbors':[], 'read_fences':[self.job]}
        self.insert('local_jobs', {'job':'fiction686-new-job','policy':digest(self.config['local_integration']),'scope':encode(scope)})
        incoming = {**self.incoming(),'members':'[]'}
        # Current new-job scope is authorized. Only the predecessor's stored
        # scope/body and full job acquisition are forbidden at this boundary.
        with patch.object(self.store,'job',side_effect=AssertionError('full predecessor job')), \
                patch.object(self.store,'_work_read_basis',side_effect=AssertionError('legacy basis')):
            local.current_job(self.store,incoming)

    def test_unknown_version_never_falls_back_to_legacy_body_acquisition(self):
        self.insert('work_read_fences', {'job':self.job,'actor':self.owner,
            'basis':encode({'schema':'fiction686-unsupported-version'}),'receipt':'{}','created':1000.})
        with self.metadata_only(), self.assertRaisesRegex(Refusal,'unsupported Work read fence version'):
            self.coexists()


if __name__ == '__main__': unittest.main(verbosity=2)
