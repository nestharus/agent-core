"""Owned fiction: NULL native/profile/session/turn; no provider/model encounter.

Kernel copies, SQLite publication and real disposable Git objects/refs execute.
Logical role authority and collected business returns are explicit fixture seams.
Run in the positive source-RO/owned-write namespace described in bounded-catalog.md.
"""
from contextlib import contextmanager
from types import SimpleNamespace
import sqlite3
import asyncio
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from coordinator_runtime import bounded_log, routine, publication, custody, processing, ref_scope, resource_scopes, ordinary, branches, configuration
from coordinator_runtime import store as store_module
from coordinator_runtime.store import Store
from coordinator_runtime.contracts import Refusal, digest, encode, SOL
from coordinator_runtime.dispatcher import execution_spec, job_prompt
from coordinator_runtime.appserver import thread_request
from coordinator_runtime.completion import Completion
from test_processing188 import engine_config, FixturePool


class Board:
    """Logical completion/grant boundary seam; no native owner claim."""
    def __init__(self, runtime, role='Work'):
        self.runtime, self.role = runtime, role
        self.expired = False

    def completion_authority(self, runtime, task):
        if self.expired:
            raise Refusal('fictional expired role authority')
        return {'id': 'fictional-grant-'+self.role, 'owner': 'fictional-logical-'+self.role,
                'issued_by': 'fictional-Work', 'authority': 'fictional bounded duty'}

    def _software_job_grant(self, *args):
        return self.completion_authority(self.runtime, None)


class Base(unittest.TestCase):
    def setUp(self):
        self.area = Path(tempfile.mkdtemp(dir='/fixtures'))
        self.config = engine_config(self.area)
        self.config.update(canonical_publication={'method':'retention-same-inode-v1','library':'/src/tools/coordinator-runtime/tests/fixture_snapshot'},
                           board_library='/src/tools/message-board', recheck_seconds=.01)
        self.config['limits'].update(max_bytes=16*1024*1024, max_files=4000)
        self.config['deadlines'].update(task=10)
        self.config['delivery']['recipients']={'Work':{'session':'fictional-logical-Work'}}
        for task in self.config['tasks'].values():
            task.update(cwd=str(self.area), network=False, sandbox='workspace-write', templates=[], responses={},
                        purpose='fictional bounded target and why', authority='fictional role authority',
                        effect_authority={'owner':'fictional-logical-'+task['role'], 'read_roots':[str(self.area)],
                                          'write_roots':[str(self.area)], 'operations':['read-reports','write-role-records']})
        self.configure()
        with patch.object(store_module, 'SCHEMA', store_module.SCHEMA.replace('profile TEXT NOT NULL','profile TEXT')):
            self.store = Store(self.config, controller='fictional-original-collector', clock=lambda:1000.)
        self.addCleanup(self.store.close)
        self.store.execution_pool = FixturePool()
        for role in self.config['roles']:
            self.store.db.execute('INSERT INTO enrollments VALUES(?,?,NULL,?,0,0,NULL,NULL)',
                                  (role, 'fictional-logical-'+role, 'fictional-grant-'+role))
        self.selection = {'basis':{'configuration':digest(self.config),'implementation':processing.implementation(),
                           'roles':{r:{'original':{'events':[]},'future_after':0} for r in self.config['roles']}},
                          'retained_events':[], 'recover_controls':{}, 'future_intake':True,
                          'tasks':list(self.config['tasks']), 'service':{'reviews':{},'legacy_resources':{},'max_inflight':5}}
        self.store.db.execute('INSERT INTO processing_capabilities VALUES(?,?,?,1000,NULL,0)', ('fictional-current-capability', encode(self.selection), 'fictional-Work'))
        self.store.processing = processing.Access(self.store, 'fictional-current-capability')
        self.board = Board(self.store)

    def configure(self):
        pass

    def job(self, role, task, package=None):
        name = 'fictional-current-source-'+role
        event = {'id':name,'role':role,'recipient':'fictional-logical-'+role,'kind':'board','post':1,
                 'body':'fictional actual operation','allowed_tasks':[task],'package':package}
        self.store.ingest(event)
        self.store.db.execute("UPDATE events SET state='queued',ack='done' WHERE id=?", (name,))
        self.store.db.execute("INSERT INTO queue VALUES(?,?,?,?,?,?,'queued',NULL)", (name,name,role,'integrator',task,package))
        job = self.store.reserve()
        self.assertIsNotNone(job)
        attempt = self.store.start_job(job['id'], job['token'])
        directory = self.store.home/'artifacts'/attempt
        directory.mkdir(mode=0o700, parents=True)
        return self.store.job(job['id']), attempt

    def collected(self, attempt, *, semantic='DONE', code=0, capture='complete', items=True):
        self.store.begin(attempt, {'fictional_logical_preparation':True})
        answer = {'semantic':semantic,'summary':'fictional selected result','findings':[], 'failures':[], 'unknowns':[],
                  'artifacts':[], 'category':'complete','handoffs':[], 'no_handoff_reason':'fictional no external recipient',
                  'completion':{'version':1,'local':'ready','failures':[],'unknowns':[],'tools':[]}}
        tools = {'complete':True, 'items':[{'id':'fictional-protocol-item','type':'commandExecution','exit_code':0,
                                          'status':'completed','completed_notification':True}] if items else []}
        self.store.collect(attempt, {'result':answer,'exit':code,'capture':capture,'cleanup':'not-native', 'error':None,
                                    'detail':{'tool_completion':tools}})
        self.assertIsNone(self.store.attempt(attempt)['profile'])
        self.assertIsNone(self.store.attempt(attempt)['session'])
        self.assertIsNone(self.store.attempt(attempt)['turn'])


class Catalog(Base):
    def configure(self):
        self.log = self.area/'WORK_LOG.md'
        # Independent oracle constructed before the operation. The production
        # operation never obtains this old body, nor any whole-old hash.
        self.old = b''.join(('old physical line %d\n'%i).encode() for i in range(2000))+b'\x00\xffold-tail'
        self.log.write_bytes(self.old)
        self.peers = [self.area/('inventory-'+str(i)) for i in range(6)]
        for i,p in enumerate(self.peers):p.write_text('peer '+str(i)+'\n')
        self.task = self.config['tasks']['wi']
        self.task.update(effects='owner-reconcile',routine_completion={'kind':bounded_log.KIND,
            'targets':[*(str(p) for p in self.peers), str(self.log)],
            'bounded_log':{'target':str(self.log),'max_lines':12,'max_bytes':8192,'max_entry_bytes':16384}})
        self.task['effect_authority']['write_roots'] = self.task['routine_completion']['targets']

    def prepare(self):
        self.current, self.attempt = self.job('Work','wi')
        routine.prepare(self.store,self.board,self.current,self.attempt,self.task)
        self.mapping = publication.stages(self.store,self.attempt)
        self.entry = b'Authorized new bounded entry\n'
        Path(self.mapping[str(self.log)]).write_bytes(self.entry)
        Path(self.mapping[str(self.peers[0])]).write_text('updated inventory zero\n')
        publication.conserve_stages(self.store,self.attempt,self.task)

    def operation_without_old_reads(self, action):
        actual_pread = os.pread
        actual_read = os.read
        counts = []
        def pread(fd,n,offset):
            if os.fstat(fd).st_ino == self.log.stat().st_ino:
                counts.append((offset,n))
                # Permitted original prefix (first 12 physical lines) OR the
                # just authored new entry. Nothing below that boundary.
                bound=len(b''.join(self.old.splitlines(keepends=True)[:12]))
                if hasattr(self,'entry') and os.fstat(fd).st_size == len(self.old)+len(self.entry):
                    bound+=len(self.entry)
                self.assertLessEqual(offset+n,bound)
            return actual_pread(fd,n,offset)
        def read(fd,n):
            self.assertNotEqual(os.fstat(fd).st_ino,self.log.stat().st_ino,'whole-log os.read forbidden')
            return actual_read(fd,n)
        def read_file(path,maximum):
            self.assertNotEqual(str(path),str(self.log),'full-log read/hash forbidden')
            return custody.read_file(path,maximum)
        with patch.object(os,'pread',side_effect=pread), patch.object(os,'read',side_effect=read), \
             patch.object(publication,'read_file',side_effect=read_file), patch.object(routine,'read_file',side_effect=read_file), \
             patch.object(bounded_log,'read_file',side_effect=read_file):
            value = action()
        self.assertTrue(counts)
        return value

    def test_joined_seven_receipts_and_lost_return_no_replay(self):
        inode = self.log.stat().st_ino
        self.operation_without_old_reads(self.prepare)
        self.collected(self.attempt)
        self.assertTrue(self.operation_without_old_reads(lambda:routine.reconcile(self.store,self.board,self.store.job(self.current['id']))))
        self.assertEqual(self.log.read_bytes(),self.entry+self.old)
        self.assertEqual(self.log.stat().st_ino,inode)
        receipt = json.loads(self.store.job(self.current['id'])['effect_receipt'])
        self.assertEqual(set(receipt['after']),set(self.task['routine_completion']['targets']))
        self.assertEqual(len(receipt['publication']),7)
        log_receipt = receipt['after'][str(self.log)]
        self.assertEqual(log_receipt['conserved_bytes'],len(self.old))
        self.assertEqual(log_receipt['shifted_bytes'],len(self.old))
        self.assertIsNone(log_receipt['whole_log_hash'])
        self.assertEqual(Path(log_receipt['opaque_backup']).read_bytes(),self.old)
        self.assertNotIn(str(self.log),[r['path'] for r in self.store.rows('SELECT path FROM artifact_custody')])
        self.assertIsNone(self.store.one('SELECT processed_at FROM events')['processed_at'])
        self.assertFalse(routine.reconcile(self.store,self.board,self.store.job(self.current['id'])))
        # Lost routine receipt after all individual publications: original
        # collector joins recorded outcomes, with no second mutation.
        self.store.db.execute("UPDATE jobs SET effects='unknown',effect_receipt=NULL WHERE id=?",(self.current['id'],))
        self.assertTrue(routine.reconcile(self.store,self.board,self.store.job(self.current['id'])))
        self.assertEqual(self.log.read_bytes(),self.entry+self.old)
        self.assertIsNone(self.store.one('SELECT processed_at FROM events')['processed_at'])
        self.store.finish_job(self.current['id'],self.current['token'])
        self.assertEqual(len(json.loads(self.store.job(self.current['id'])['effect_receipt'])['publication']),7)
        self.assertIsNotNone(self.store.one('SELECT processed_at FROM events')['processed_at'])

    def test_interrupted_shift_is_held_with_opaque_source_and_no_replay(self):
        self.prepare(); self.collected(self.attempt)
        realcopy=bounded_log.copy_exact
        def interrupt(source,dest,length,destination_offset=0):
            if destination_offset:
                realcopy(source,dest,min(30,length),destination_offset)
                raise OSError('fictional injected interruption after actual partial shift')
            return realcopy(source,dest,length,destination_offset)
        with patch.object(bounded_log,'copy_exact',side_effect=interrupt):
            with self.assertRaises(OSError):routine.reconcile(self.store,self.board,self.store.job(self.current['id']))
        record=self.store.one('SELECT * FROM file_publications WHERE target=?',(str(self.log),))
        self.assertEqual(record['state'],'intent')
        self.assertEqual(Path(record['temp']).read_bytes(),self.old)
        changed=self.log.read_bytes()
        with self.assertRaisesRegex(Refusal,'never replay'):
            routine.reconcile(self.store,self.board,self.store.job(self.current['id']))
        self.store.finish_job(self.current['id'],self.current['token'])
        self.assertEqual(self.store.job(self.current['id'])['state'],'held')
        self.assertEqual(self.log.read_bytes(),changed)
        self.assertIsNone(self.store.one('SELECT processed_at FROM events')['processed_at'])

    def test_peer_authority_and_bounded_entry_refusals(self):
        self.prepare(); self.collected(self.attempt)
        self.log.write_bytes(b'peer prepend\n'+self.old)
        with self.assertRaisesRegex(Refusal,'precondition changed'):
            routine.reconcile(self.store,self.board,self.store.job(self.current['id']))
        self.assertEqual(self.log.read_bytes(),b'peer prepend\n'+self.old)
        self.assertEqual(self.store.job(self.current['id'])['effects'],'unknown')

    def test_partial_or_lost_collection_cannot_mutate_log(self):
        self.prepare(); self.collected(self.attempt,code=None,capture='unknown')
        self.assertFalse(routine.reconcile(self.store,self.board,self.store.job(self.current['id'])))
        self.assertEqual(self.log.read_bytes(),self.old)

    def test_full_log_routine_and_capture_refuse_before_metadata(self):
        old=copy.deepcopy(self.task);old['routine_completion']={'kind':'file-witness','targets':self.task['routine_completion']['targets']}
        with patch.object(Path,'is_symlink',side_effect=AssertionError('no target metadata')):
            with self.assertRaisesRegex(Refusal,'whole-log'):routine.policy_for(old)
            with self.assertRaisesRegex(Refusal,'whole-log'):custody.capture(self.store,'fictional',str(self.log),self.task)
        # Config contract validation is lexical, allowing an original immutable
        # config to be opened for prospective transition without executing it.
        routine.policy_for(old,execution=False)

    def test_entry_required_and_scoped_startup(self):
        self.prepare();self.collected(self.attempt,items=False)
        self.assertFalse(routine.reconcile(self.store,self.board,self.store.job(self.current['id'])))
        self.assertEqual(self.log.read_bytes(),self.old)
        spec=execution_spec(self.task,self.store.home/'artifacts'/self.attempt)
        request=thread_request(spec,SOL)
        self.assertEqual(request['config']['project_doc_max_bytes'],0)
        self.assertIn('Do not read project AGENTS, WORK_LOG',request['developerInstructions'])
        self.task['templates']=['/not-mounted/AGENTS.md','/not-mounted/WORK_LOG.md']
        # Startup/template filtering happens before metadata, even for missing
        # excluded startup files; no full instructions/log read is attempted.
        prompt=job_prompt(self.store,self.store.job(self.current['id']),self.task)
        self.task['templates']=[]
        self.assertNotIn('Read applicable AGENTS',prompt)
        self.assertIn('bounded_prefix_hex',prompt)
        self.assertEqual(spec['effect_authority']['write_roots'],[str(self.store.home/'artifacts'/self.attempt)])

    def test_expired_authority_does_not_complete_seven(self):
        self.prepare();self.collected(self.attempt)
        self.board.expired=True
        with self.assertRaises(Refusal):routine.reconcile(self.store,self.board,self.store.job(self.current['id']))
        self.assertEqual(self.log.read_bytes(),self.old)
        self.board.expired=False

    def test_empty_bounded_entry_and_missing_seventh_receipt_remain_pending(self):
        self.current,self.attempt=self.job('Work','wi')
        routine.prepare(self.store,self.board,self.current,self.attempt,self.task)
        publication.conserve_stages(self.store,self.attempt,self.task)
        self.collected(self.attempt)
        with self.assertRaisesRegex(Refusal,'nonempty'):
            routine.reconcile(self.store,self.board,self.store.job(self.current['id']))
        self.assertEqual(self.log.read_bytes(),self.old)
        with self.assertRaisesRegex(Refusal,'incomplete'):
            self.store.finish_job(self.current['id'],self.current['token'])
        self.assertIsNone(self.store.one('SELECT processed_at FROM events')['processed_at'])

    def test_excluded_log_refuses_before_any_target_metadata(self):
        current,attempt=self.job('Work','wi')
        self.config['artifact_exclusions']=[str(self.log)]
        with patch.object(Path,'is_symlink',side_effect=AssertionError('no excluded metadata')):
            with self.assertRaisesRegex(Refusal,'excluded before metadata'):
                routine.execution_policy(self.store,self.task)
        self.config.pop('artifact_exclusions')

    def test_actual_delegated_work_callback_processes_joined_seven_receipt(self):
        self.prepare();self.collected(self.attempt)
        routine.reconcile(self.store,self.board,self.store.job(self.current['id']))
        class Callback(Completion, Board):
            @contextmanager
            def opened(self):
                yield self.conn
            def _grant(self,*args):
                return Board.completion_authority(self,self.runtime,None)
            def _delivery_record(self,conn,row):
                return row
        callback=Callback(self.store)
        callback.config=self.config
        callback.conn=sqlite3.connect(':memory:');callback.conn.row_factory=sqlite3.Row
        self.addCleanup(callback.conn.close)
        callback.conn.executescript(routine.BOARD_SCHEMA+"""
          CREATE TABLE coordinator_deliveries_v1(id,recipient,actor,owner,grant_id,payload,notice,transport_started,
            pickup,processing,settlement,state,processed_at);
          CREATE TABLE notification_outbox(notification_id,route,delivery_state,acknowledged_at,state_changed_at);
        """)
        callback.conn.execute('INSERT INTO coordinator_completion_grants_v1 VALUES(?,?,?)',
            ('fictional-grant-Work',encode({'wi':self.task['routine_completion']}),'fictional actual role delegation'))
        job=self.store.job(self.current['id'])
        with self.store.tx():
            self.store.owner_report(job,self.store.attempt(self.attempt),json.loads(self.store.attempt(self.attempt)['result']))
        outbox=self.store.one('SELECT * FROM outboxes')
        joined=json.loads(outbox['payload'])['effect_observation']
        self.assertEqual(len(joined['publication']),7)
        self.assertEqual(joined['after'][str(self.log)]['conserved_bytes'],len(self.old))
        callback.conn.execute("INSERT INTO coordinator_deliveries_v1 VALUES(?,?,?,?,?,?,?,0,NULL,NULL,NULL,'notified',NULL)",
            (outbox['id'],'fictional-logical-Work',self.config['actor'],'fictional-logical-Work','fictional-grant-Work',outbox['payload'],'fictional-notice'))
        callback.conn.execute("INSERT INTO notification_outbox VALUES('fictional-notice','managed','pending',NULL,NULL)")
        callback.conn.commit()
        @contextmanager
        def write(conn):
            with conn:
                yield
        callback.store=SimpleNamespace(write=write,utc_now=lambda:'fictional-clock')
        callback.selected={'owner':'fictional-logical-Work'}
        processed=callback.complete_own_delivery(self.store,outbox)
        self.assertEqual(processed['state'],'settled')
        proof=json.loads(processed['processing'])
        self.assertFalse(proof['native_receipt'])
        self.assertFalse(proof['genuine_owner_full_read'])
        self.assertIsNone(proof['worker'])
        self.assertEqual(len(json.loads(proof['evidence']['effect_receipt'])['publication']),7)


class RefOperations(Base):
    def command(self,*args):
        return subprocess.check_output(['/usr/bin/git','-c','user.name=Fiction','-c','user.email=fiction@example.invalid',*args],cwd=self.repo,
            env={**os.environ,'GIT_CONFIG_NOSYSTEM':'1','GIT_CONFIG_GLOBAL':'/dev/null','GIT_TERMINAL_PROMPT':'0'}).decode().strip()

    def configure(self):
        self.repo=self.area/'fictional-object-store';self.repo.mkdir()
        self.command('init','--quiet',str(self.repo))
        tree=self.command('mktree')
        self.old=self.command('commit-tree',tree,'-m','fictional before')
        self.new=self.command('commit-tree',tree,'-p',self.old,'-m','fictional target')
        self.command('update-ref','refs/heads/source',self.new)
        self.command('update-ref','refs/heads/target',self.old)
        self.command('remote','add','origin','https://fiction.invalid/repo')
        self.procedure=self.area/'procedure.md';self.procedure.write_text('Fiction: CAS target to exact source; no remote effects.\n')
        self.task=self.config['tasks']['bi']
        self.task.update(effects='owner-reconcile',require_package_scope=True,scope_roots=[str(self.area)],cwd=str(self.repo))
        self.task['effect_authority'].update(operations=['read-source','organize-authorized-refs'],read_roots=[str(self.repo)],write_roots=[str(self.repo)])
        self.p={'kind':'local-ref','git':'/usr/bin/git','git_sha256':hashlib.sha256(Path('/usr/bin/git').read_bytes()).hexdigest(),
                'repository':str(self.repo),'source_ref':'refs/heads/source','source_head':self.new,
                'procedure_sha256':hashlib.sha256(self.procedure.read_bytes()).hexdigest(),
                'resources':[{'key':'fictional-exact-operation','owner':'11111111-1111-4111-8111-111111111111','authority':'fictional actual custodian','expires':1060.}],
                'acceptor':'22222222-2222-4222-8222-222222222222','acceptance_authority':'fictional independent actor',
                'timeout':5,'max_output':8192,'ref':'refs/heads/target','before':self.old,'target':self.new}
        self.scope={'cwd':str(self.repo),'read_roots':[str(self.repo),str(self.procedure)],'write_roots':[str(self.repo)],'network':False,
                    'procedure':str(self.procedure),'resource_evidence':'fictional exact operation custody','ordinary_effects':self.p,'branch_binding':'fictional-branch'}

    def ready(self):
        self.store.admit('fictional-package',self.config['roles']['Branch']['owner'],{'task_scopes':{'bi':self.scope}})
        device,inode=branches.repository_identity(self.repo)
        self.store.db.execute("INSERT INTO branch_associations VALUES(?,?,?,?,?,?,?,?,?,?,? ,?,1000,NULL,?)",
            ('fictional-branch',str(self.repo),device,inode,'https://fiction.invalid/repo','refs/heads/target','fictional-incarnation',
             'fictional-package','fictional-Root','fictional delegated authority','active','fictional accepted Root delegates builders/testers','[]'))
        self.store.db.execute("UPDATE enrollments SET legacy_hold='fictional retained Branch unknown past' WHERE role='Branch'")
        self.pending={'role':'Branch','phase':'integrator','task':'bi','package':'fictional-package'}

    def receipt(self):
        basis=ref_scope.material(self.store,'bi','fictional-package')
        return {'basis':basis,'authority':'fictional real custodian qualifies only this new operation, retaining unknown past',
                'originals':[{'original':'fictional original closed receipt','collector':self.config['roles']['Branch']['owner'],
                             'activity':'closed','actual_END':0,'evidence':'fictional collected control and original receipt'}],
                'activity_scope':{'original_hold':basis['original_hold'],'operation':digest({'operation':basis['operation'],'repository':basis['common_repository'],'refs':basis['local_refs']}),
                                  'no_active_writers':True,'evidence':'fictional current custodian control over exact future operation and original activity'},
                'remaining_holds':[basis['original_hold']],'past_effects':['fictional old source/effects remain UNKNOWN']}

    def qualify(self):
        return ref_scope.account(self.store,self.config['roles']['Branch']['owner'],self.receipt())

    def test_actual_local_ref_adapter_with_exact_custody_preserves_unknown_past(self):
        self.ready()
        self.assertTrue(resource_scopes.blocked(self.store,self.pending))
        self.qualify()
        self.assertFalse(resource_scopes.blocked(self.store,self.pending))
        job,attempt=self.job('Branch','bi','fictional-package')
        self.collected(attempt)
        Board(self.store,'Branch')
        # Prospective selection/grant are explicit logical seams; real adapter,
        # tool creation/capture/END, resources and Git CAS/readback execute.
        with patch.object(ordinary,'selected',return_value={'id':'fictional-effect-authority'}), \
             patch('coordinator_runtime.board.Board',return_value=Board(self.store,'Branch')):
            self.assertTrue(asyncio.run(ordinary.perform(self.store,Board(self.store,'Branch'),self.store.job(job['id']))))
        run=self.store.one('SELECT * FROM ordinary_runs WHERE attempt=?',(attempt,))
        self.assertEqual(run['state'],'reconciled')
        self.assertEqual(self.command('rev-parse','refs/heads/target'),self.new)
        self.assertEqual(json.loads(run['receipt'])['outcome']['before'],self.old)
        self.assertTrue(all(json.loads(r['record'])['exit']==0 for r in self.store.rows('SELECT record FROM ordinary_tool_records WHERE record LIKE ?',('%"complete":true%',))))
        self.assertIsNotNone(self.store.one("SELECT legacy_hold FROM enrollments WHERE role='Branch'")['legacy_hold'])
        self.assertEqual(json.loads(self.store.one('SELECT receipt FROM ref_scope_accounts')['receipt'])['past_effects'],['fictional old source/effects remain UNKNOWN'])
        self.assertEqual(self.store.rows('SELECT * FROM ordinary_resources'),[])
        self.assertEqual(self.store.rows('SELECT * FROM ordinary_acceptance'),[])

    def test_wrong_actor_unknown_activity_empty_clearance_and_stale_before_refuse(self):
        self.ready();receipt=self.receipt()
        with self.assertRaises(Refusal):ref_scope.account(self.store,'fictional-stranger',receipt)
        unknown=copy.deepcopy(receipt);unknown['originals'][0]['actual_END']=None
        with self.assertRaises(Refusal):ref_scope.account(self.store,self.config['roles']['Branch']['owner'],unknown)
        empty=copy.deepcopy(receipt);empty['remaining_holds']=[]
        with self.assertRaises(Refusal):ref_scope.account(self.store,self.config['roles']['Branch']['owner'],empty)
        empty=copy.deepcopy(receipt);empty['activity_scope']['no_active_writers']=False
        with self.assertRaises(Refusal):ref_scope.account(self.store,self.config['roles']['Branch']['owner'],empty)
        self.command('update-ref','refs/heads/target',self.new,self.old)
        with self.assertRaises(Refusal):ref_scope.account(self.store,self.config['roles']['Branch']['owner'],receipt)
        self.assertTrue(resource_scopes.blocked(self.store,self.pending))

    def test_current_incarnation_origin_refs_and_common_repo_boundaries(self):
        self.ready();self.qualify()
        self.store.db.execute("UPDATE branch_associations SET incarnation='new-current-incarnation' WHERE id='fictional-branch'")
        self.assertTrue(resource_scopes.blocked(self.store,self.pending))
        self.store.db.execute("UPDATE branch_associations SET incarnation='fictional-incarnation' WHERE id='fictional-branch'")
        self.command('remote','set-url','origin','https://fiction.invalid/other')
        self.assertTrue(resource_scopes.blocked(self.store,self.pending))
        self.command('remote','set-url','origin','https://fiction.invalid/repo')
        self.assertFalse(resource_scopes.blocked(self.store,self.pending))
        self.scope['network']=True
        self.store.admit('fictional-package',self.config['roles']['Branch']['owner'],{'task_scopes':{'bi':self.scope}})
        self.assertTrue(resource_scopes.blocked(self.store,self.pending))

    def test_unmapped_and_overlapping_lease_or_writer_fence(self):
        self.ready();self.qualify()
        device,inode=branches.repository_identity(self.repo)
        for key in ['old-label-without-map','git-ref:'+str(device)+':'+str(inode)+':refs/heads/source']:
            self.store.db.execute('INSERT INTO ordinary_resources VALUES(?,?)',(key,'fictional-original-lease'))
            self.assertTrue(resource_scopes.blocked(self.store,self.pending))
            self.store.db.execute('DELETE FROM ordinary_resources WHERE resource=?',(key,))
        self.store.db.execute("INSERT INTO branch_turns VALUES('old-writer','fictional-branch','builder','','fictional-address','fictional-original-collector',NULL,'fictional-writer','{}','unknown',900,NULL,NULL)")
        self.assertTrue(resource_scopes.blocked(self.store,self.pending))
        with self.assertRaises(Refusal):self.qualify()

    def test_unresolved_past_with_actual_closed_originals_can_qualify_but_unknown_activity_cannot(self):
        self.ready()
        self.store.db.execute("INSERT INTO jobs(id,role,phase,task,package,members,controller,token,created,effects) VALUES('fictional-old','Branch','integrator','bi','fictional-old-scope','[]','fictional-old-collector','old-token',900,'unknown')")
        self.store.db.execute("INSERT INTO attempts(id,kind,job,controller,profile,binding,created,begin,ended,exit,collected,capture) VALUES('fictional-old-original','task','fictional-old','fictional-old-collector',NULL,'{}',900,900,901,0,902,'unknown')")
        self.qualify()
        self.assertFalse(resource_scopes.blocked(self.store,self.pending))
        self.assertIsNone(self.store.one("SELECT * FROM job_resource_policies WHERE job='fictional-old'"))
        self.assertEqual(self.store.job('fictional-old')['effects'],'unknown')
        self.store.db.execute("UPDATE attempts SET collected=NULL WHERE id='fictional-old-original'")
        self.assertTrue(resource_scopes.blocked(self.store,self.pending))
        with self.assertRaises(Refusal):self.qualify()

    def test_new_scope_cannot_change_old_job_resources_or_historical_authority(self):
        self.ready();self.qualify()
        job,attempt=self.job('Branch','bi','fictional-package')
        frozen=self.store.one('SELECT * FROM job_resource_policies WHERE job=?',(job['id'],))
        self.scope['ordinary_effects']['ref']='refs/heads/other'
        self.store.admit('fictional-package',self.config['roles']['Branch']['owner'],{'task_scopes':{'bi':self.scope}})
        self.assertEqual(self.store.one('SELECT * FROM job_resource_policies WHERE job=?',(job['id'],)),frozen)
        self.assertTrue(resource_scopes.blocked(self.store,self.store.job(job['id'])))
        with self.assertRaises(Refusal):ordinary.policy_for(self.store,self.store.job(job['id']))
        with self.assertRaises(Exception):self.store.db.execute("UPDATE job_resource_policies SET task='{}' WHERE job=?",(job['id'],))

    def test_interrupted_after_real_CAS_keeps_original_intent_and_never_replays(self):
        self.ready();self.qualify()
        job,attempt=self.job('Branch','bi','fictional-package');self.collected(attempt)
        adapter=ordinary.adapter
        async def interrupted(*args,**kwargs):
            await adapter(*args,**kwargs)
            raise Refusal('fictional interruption after actual CAS and readback')
        with patch.object(ordinary,'selected',return_value={'id':'fictional-effect-authority'}), \
             patch('coordinator_runtime.board.Board',return_value=Board(self.store,'Branch')), \
             patch.object(ordinary,'adapter',side_effect=interrupted):
            with self.assertRaisesRegex(Refusal,'after actual CAS'):
                asyncio.run(ordinary.perform(self.store,Board(self.store,'Branch'),self.store.job(job['id'])))
        self.assertEqual(self.command('rev-parse','refs/heads/target'),self.new)
        self.assertEqual(self.store.one('SELECT state FROM ordinary_runs')['state'],'intent')
        self.assertTrue(self.store.rows('SELECT * FROM ordinary_resources'))
        with patch.object(ordinary,'selected',return_value={'id':'fictional-effect-authority'}):
            with self.assertRaisesRegex(Refusal,'never replay'):
                asyncio.run(ordinary.perform(self.store,Board(self.store,'Branch'),self.store.job(job['id'])))
        self.assertEqual(self.store.job(job['id'])['effects'],'unknown')
        self.assertIsNone(self.store.one('SELECT processed_at FROM events')['processed_at'])

    def test_unknown_branch_operation_does_not_freeze_independent_new_report(self):
        self.ready()
        self.assertTrue(resource_scopes.blocked(self.store,self.pending))
        job,attempt=self.job('Work','wi')
        self.assertEqual(job['role'],'Work')
        self.assertIsNone(self.store.one("SELECT id FROM ref_scope_accounts"))
        self.assertIsNotNone(self.store.one("SELECT legacy_hold FROM enrollments WHERE role='Branch'")['legacy_hold'])

    def test_missing_actual_ref_is_a_held_operation_not_clearance(self):
        self.ready();self.qualify()
        self.command('update-ref','-d','refs/heads/source',self.new)
        with self.assertRaisesRegex(Refusal,'evidence unavailable'):
            ref_scope.material(self.store,'bi','fictional-package')
        self.assertTrue(resource_scopes.blocked(self.store,self.pending))
        self.assertEqual(self.command('rev-parse','refs/heads/target'),self.old)
        self.assertIsNotNone(self.store.one("SELECT legacy_hold FROM enrollments WHERE role='Branch'")['legacy_hold'])

    def test_namespace_has_only_read_only_public_source_and_owned_writes(self):
        with self.assertRaises(OSError):
            Path('/src/tools/coordinator-runtime/coordinator_runtime/ref_scope.py').open('ab')
        with self.assertRaises(FileNotFoundError):
            Path('/home/nes/projects/rfq/trunk/rfqautomation/WORK_LOG.md').stat()
        (self.area/'owned-only').write_text('actual owned fixture write')


class DraftConfiguration(Base):
    configure=Catalog.configure
    def test_prospective_bounded_draft_keeps_seven_targets_and_rejects_other_deltas(self):
        original=copy.deepcopy(self.config)
        old_policy={'kind':'file-witness','targets':list(self.task['routine_completion']['targets'])}
        original['tasks']['wi']['routine_completion']=old_policy
        original['diagnosis']={'cwd':'/fixtures','profile':None,'binding':copy.deepcopy(original['classifier']['binding'])}
        original['operator_cli']='/fictional-old/tools/coordinator-runtime/coordinator'
        original['control_receive']={'mode':'cooperative','instructions':'/fictional-old/receive.md'}
        original['tasks']['wi']['templates']=['/fictional-old/tools/coordinator-runtime/templates/work-catalog.md']
        original['tasks']['wi']['effect_authority']['operations'].append('read-source')
        runtime=SimpleNamespace(config=original)
        baseline=copy.deepcopy(original)
        value=configuration.candidate(runtime,str(self.area/'future-config.json'),['wi'],bounded_work_log=True)
        self.assertEqual(original,baseline)
        self.assertEqual(value['tasks']['wi']['routine_completion']['targets'],old_policy['targets'])
        self.assertEqual(value['tasks']['wi']['routine_completion']['kind'],bounded_log.KIND)
        with patch.object(configuration,'validate_config',side_effect=lambda v:v):
            configuration.validate_changes(runtime,value,['wi'])
            unrelated=copy.deepcopy(value);unrelated['actor']='fictional-replacement-owner'
            with self.assertRaises(Refusal):configuration.validate_changes(runtime,unrelated,['wi'])
            with self.assertRaises(Refusal):configuration.validate_changes(runtime,value,['bi'])
        self.assertEqual(value['tasks']['wi']['binding'],original['tasks']['wi']['binding'])
        self.assertEqual(value['profiles'],sorted(configuration.PROFILES))


# Reuse the public NULL-native Board/transition fixture, with its ORIGINAL config
# genuinely constructed with seven targets before Store/grant creation. No saved
# digest/grant/journal is edited to pretend that policy existed historically.
import test_configuration308 as configuration_fixture


class CompletionTransition(unittest.TestCase):
    def setUp(self):
        self.fixture=configuration_fixture.CurrentConfiguration(methodName='runTest')
        self.addCleanup(self.fixture.doCleanups)
        original_engine=configuration_fixture.engine_config
        original_store=configuration_fixture.Store
        def original_config(directory):
            value=original_engine(directory)
            targets=[]
            for i in range(6):
                path=directory/('original-inventory-'+str(i));path.write_text('fictional original inventory\n');targets.append(str(path))
            log=directory/'WORK_LOG.md';log.write_text('fictional old prefix\nfictional old tail\n');targets.append(str(log))
            value['tasks']['wi']['routine_completion']={'kind':'file-witness','targets':targets}
            return value
        def original_runtime(value,**kwargs):
            # The existing fixture fills task authority after engine_config.
            # Complete our ORIGINAL construction before Store/grants are made.
            task=value['tasks']['wi']
            task['effects']='owner-reconcile'
            task['effect_authority']['write_roots']=list(task['routine_completion']['targets'])
            return original_store(value,**kwargs)
        with patch.object(configuration_fixture,'engine_config',side_effect=original_config), \
             patch.object(configuration_fixture,'Store',side_effect=original_runtime):
            self.fixture.setUp()
        f=self.fixture
        f.conn.executescript(routine.BOARD_SCHEMA)
        f.conn.execute('INSERT INTO coordinator_completion_grants_v1 VALUES(?,?,?)',
            ('fictional-grant-Work',encode({'wi':f.original['tasks']['wi']['routine_completion']}),'fictional original seven-duty delegation'))

    def test_real_current_transition_bridges_only_new_bounded_completion_and_original_policy_stays(self):
        f=self.fixture
        f.value=configuration.candidate(f.runtime,str(f.directory/'current.json'),['bi','qe'],bounded_work_log=True)
        Path(f.value['operator_config']).write_text(encode(f.value))
        original_policies=[tuple(r) for r in f.conn.execute('SELECT * FROM coordinator_completion_grants_v1')]
        f.transition();f.issue()
        grant=f.boards['Work'].completion_authority(f.runtime,'wi')
        self.assertIsNotNone(grant['revoked'])
        self.assertFalse(grant['completion_transition']['historical_completion'])
        self.assertEqual(original_policies,[tuple(r) for r in f.conn.execute('SELECT * FROM coordinator_completion_grants_v1')])
        oldjob=f.runtime.job('fictional-old-job')
        with self.assertRaises(Refusal):configuration.require_current_job(f.runtime,oldjob)
        f.conn.execute('UPDATE coordinator_completion_grants_v1 SET policies=?',(encode({}),))
        with self.assertRaises(Refusal):f.boards['Work'].completion_authority(f.runtime,'wi')
