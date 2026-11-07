"""Fresh public-API QA629 regressions; retain every owned fixture.

Boards, grants, selections, admissions, reservations and routing are production
APIs. Authentication and collected SDK answers are explicit synthetic seams;
there is no provider, native execution, ordinary lease or external acceptance.
Set QA629_FIXTURES to a new absolute owned directory before each invocation.
"""
import copy
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import unittest
from unittest.mock import patch

from support import config_at, collect, result
from coordinator_runtime.board import Board, module_at
from coordinator_runtime.contracts import Refusal, digest, encode, ident, validate_config
from coordinator_runtime.dispatcher import Dispatcher
from coordinator_runtime.frontier import delivery
from coordinator_runtime import processing, prospective, resource_scopes
from coordinator_runtime.store import Store


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@contextmanager
def actor(substrate, principal):
    def acting(expected):
        if principal != expected:
            raise substrate.UserError('synthetic SDK principal mismatch')
        return principal
    with patch.object(substrate, 'acting_session', side_effect=acting):
        yield


class Fixture(unittest.TestCase):
    def bootstrap(self, configure):
        base = Path(os.environ['QA629_FIXTURES'])
        assert base.is_absolute() and not base.is_symlink()
        self.area = base / self._testMethodName / ident()
        self.area.mkdir(parents=True, mode=0o700)
        self.methods = {}
        self.addCleanup(self.record)
        self.config = config_at(self.area)
        # The fictional pool permits all currently supported profiles; no real
        # account selection or provider operation is part of these tests.
        Path(self.config['execution_pool_routes']).write_text(
            '[rotation]\nstate_dir = '+json.dumps(str(self.area/'pool-state'))+
            '\n[providers.codex]\npool = [".codex", ".codex2", ".codex3", ".codex4", ".codex5"]\n'
            'manual_profiles = [".codex", ".codex2", ".codex3", ".codex4", ".codex5"]\n')
        shared = self.config['roles']['Work']['board_id']
        for role in self.config['roles'].values():
            role['board_id'] = shared
        self.config['software_delegation'] = dict(grantor=self.config['roles']['Work']['owner'],
            authority='Owned fictional Work delegation for QA629 regression', boundary='new-journal-only')
        self.config['delivery'] = {'recipients': {r:dict(session=v['owner'],profile=v['profile'],board_role=v['board_role'])
                                               for r,v in self.config['roles'].items()}}
        configure()
        validate_config(self.config)
        substrate = module_at(self.config['board_library'], 'board_store')
        catalog = module_at(self.config['board_library'], 'catalog')
        home = Path(self.config['board_home'])
        with catalog.catalog(home) as conn:
            entry = catalog.create(conn,home,'qa629','Owned fictional regression',board_id=shared,temporary_test=True)
        self.board_path = Path(entry['db_path'])
        self.source_sender = ident()
        with substrate.database(str(self.board_path)) as conn:
            substrate.bind_board(conn,shared,initialize=True)
            population = [*self.config['roles'].values(),dict(owner=self.source_sender,board_role='fixture-sender',profile='.codex2')]
            for selected in population:
                args = substrate.parser().parse_args(['register','--session',selected['owner'],'--role',selected['board_role'],
                                                     '--route','managed','--profile',selected['profile']])
                with actor(substrate, selected['owner']):
                    substrate.register(conn,args)
        self.store = Store(self.config)
        self.addCleanup(self.store.close)
        self.boards = {r:Board(self.config,r) for r in self.config['roles']}
        for role, board in self.boards.items():
            with actor(board.store,self.config['software_delegation']['grantor']):
                grant = board.grant_software(self.store,self.config['software_delegation']['authority'])
            self.hit('grant_software')
            self.store.enroll(role,grant)
            self.store.reconcile_legacy(role,self.config['roles'][role]['owner'],
                dict(collector='fictional original collector',evidence=['new empty isolated Board'],remaining_holds=[]))
        self.runtime = Dispatcher(self.store,models=object(),boards=self.boards)

    def hit(self, method):
        self.methods[method] = self.methods.get(method,0)+1

    def record(self):
        (self.area/'reached.json').write_text(encode(dict(pid=os.getpid(),methods=self.methods))+ '\n')

    def select(self, service=None):
        for role, board in self.boards.items():
            with actor(board.store,self.config['roles']['Work']['owner']):
                board.revoke_software(self.store,self.store.enrollment(role)['grant_id'])
            # Same stopped enrollment transition used by the CLI; no API on
            # Store exposes it separately. This is an explicit fixture seam.
            self.store.db.execute('UPDATE enrollments SET intake=0 WHERE role=?',(role,))
        self.boards = {r:processing.ProcessingBoard(self.config,r) for r in self.config['roles']}
        for board in self.boards.values():
            board.runtime = self.store  # Same explicit binding as processing.run.
        self.runtime.boards = self.boards
        selection = dict(basis=processing.basis(self.store,self.boards),authority='Fictional actual Work selection',
            retained_events=[],recover_controls={},future_intake=True,tasks=list(self.config['tasks']),
            max_shared_rows=1000,max_shared_payload_bytes=1000000,max_runtime_rows=1000)
        if service is None:
            selection.update(expires=time.time()+600,max_starts=100)
        else:
            selection['service'] = service
        board = self.boards['Work']
        with actor(board.store,self.config['roles']['Work']['owner']):
            self.cap = processing.select(self.store,self.boards,selection)['capability']
        self.store.processing = processing.Access(self.store,self.cap,self.boards)
        self.hit('processing.select')

    def post(self, role, task, package):
        board = self.boards[role]
        command = ['open','--session',self.source_sender,'--topic','fixture',
            '--kind','finding','--text','Owned fictional source','--to',self.config['roles'][role]['owner'],
            '--title','QA629 fictional input','--no-push']
        if package is not None:
            command += ['--ref',package]
        args = board.store.parser().parse_args(command)
        with board.store.database(str(self.board_path)) as conn:
            with actor(board.store,self.source_sender):
                board.store.open_thread(conn,args)
        messages = board.scan(self.store)
        self.assertEqual(len(messages),1)
        message = messages[0]
        # Classifier chooses from real Board routes; package is carried in the
        # public post's ref rather than injected into frozen receiving bytes.
        self.store.ingest(message,cursor=message['post'])
        self.classify(task=task, package=package)
        return message

    def classify(self, task=None, package=None):
        while claimed := self.store.claim_classification():
            attempt, message = claimed
            selected = task if message['kind']=='board' and task else message['allowed_tasks'][0]
            collect(self.store,attempt,dict(event_id=message['id'],task=selected,
                package=package if message['kind']=='board' else message['package'],reason='Fictional SDK classification'))
            self.store.commit_classification(attempt)
            self.hit('commit_classification')
        self.runtime.receipts()

    def run_job(self, job, answer):
        attempt = self.store.start_job(job['id'],job['token'])
        admission = self.store.one('SELECT * FROM admissions WHERE package=?',(job['package'],))
        self.boards[job['role']].bind_software_attempt(self.store,job,attempt,admission)
        collect(self.store,attempt,answer,tool_completion=dict(complete=True,items=[],nonzero_completions=0))
        self.store.finish_job(job['id'],job['token'])
        self.hit('finish_job')
        return attempt

    def git(self, *args):
        command = ['/usr/bin/git','-C',str(self.repo),*args]
        with (self.area/'git-processes.jsonl').open('a') as log:
            child = subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,
                env={**os.environ,'GIT_CONFIG_GLOBAL':'/dev/null','GIT_CONFIG_NOSYSTEM':'1'})
            stdout,stderr = child.communicate()
            log.write(encode(dict(pid=child.pid,argv=command,END=child.returncode,stdout=stdout,stderr=stderr))+'\n')
        self.assertEqual(child.returncode,0,stderr)
        return stdout.strip()


class CrossRole(Fixture):
    def setUp(self):
        self.bootstrap(self.configure)
        # Retained UNKNOWN is an isolated original enrollment, never cleared by
        # the operation-relative selection or this reservation.
        self.store.db.execute("UPDATE enrollments SET legacy_hold='fictional global UNKNOWN' WHERE role='QA'")
        self.store.admit('own-package',self.config['roles']['Branch']['owner'],dict(task_scopes={'qa-execution':self.scope}))
        admission = self.store.one('SELECT * FROM admissions WHERE package=?',('own-package',))
        statement = dict(fact='fictional observation; original global scope remains UNKNOWN')
        self.record_policy = dict(original_hold='fictional global UNKNOWN',roots=[],unbounded=True,evidence='Whole fictional operation',
            qa_operation=dict(statement=statement,binding=dict(task='qa-execution',package='own-package',admission_sha256=digest(admission)),
            policy=dict(version='qa-operation-v1',custodian=self.config['roles']['QA']['owner'],reference='own synthetic observation',
                statement_sha256=digest(statement),authority='Fictional Work operation selection',expires=time.time()+500,
                scope=copy.deepcopy(self.scope),source=dict(common_git=str(self.repo/'.git'),tree=self.tree,parents=[]),
                inputs=[dict(path=str(self.script),sha256=sha(self.script))],relevant_roots=[])))
        resource_scopes.validate(self.store,{'QA':self.record_policy})
        self.hit('resource_scopes.validate')
        self.select(dict(max_inflight=3,reviews={},legacy_resources={'QA':self.record_policy}))
        task = self.config['tasks']['qa-execution']
        prospective.select(self.store,self.config['roles']['Work']['owner'],dict(configuration=digest(self.config),
            authority='Fictional bounded QA ordinary policy only',expires=time.time()+550,processing_capability=self.cap,
            grants={'QA':self.store.enrollment('QA')['grant_id']},tasks={'qa-execution':dict(task_hash=digest(task),
                software_handoffs={},ordinary_effects='admitted-v1')}))
        # Use public source/classification/reservation. The Board ref supplies
        # the package; post() records the expected typed classification.
        self.post('QA','qa-execution','own-package')
        resource_scopes.qa_operation(self.store,self.store.one("SELECT * FROM queue WHERE role='QA'"),self.record_policy)
        self.qa = self.store.reserve()
        self.assertIsNotNone(self.qa)
        self.hit('reserve.QA')

    def configure(self):
        self.repo = self.area/'repo'; self.repo.mkdir()
        self.git('init','--initial-branch=source')
        (self.repo/'source.txt').write_text('owned fictional source\n')
        self.git('add','source.txt')
        self.git('-c','user.name=Fixture','-c','user.email=fixture@example.invalid','-c','commit.gpgsign=false','commit','-m','fixture source')
        self.head = self.git('rev-parse','HEAD'); self.tree = self.git('rev-parse','HEAD^{tree}')
        self.procedure = self.area/'procedure.md'; self.procedure.write_text('Owned bounded fictional QA procedure\n')
        self.script = self.area/'check.py'; self.script.write_text('print("owned check")\n')
        output = self.area/'output'; output.mkdir()
        python = str(Path(sys.executable).resolve())
        p = dict(kind='local-qa',git='/usr/bin/git',git_sha256=sha('/usr/bin/git'),repository=str(self.repo),
            source_ref='refs/heads/source',source_head=self.head,procedure_sha256=sha(self.procedure),timeout=1,max_output=4096,
            resources=[dict(key='own-qa',owner=self.config['roles']['QA']['owner'],authority='fictional resource owner',expires=time.time()+600)],
            acceptor=ident(),acceptance_authority='fictional independent acceptor; never accepted',known_exits=[0,1],
            source_capture=dict(bwrap='/usr/bin/bwrap',sha256=sha('/usr/bin/bwrap'),max_bytes=1048576,max_files=100),
            public_executables={k:dict(path=python,bytes=Path(python).stat().st_size,sha256=sha(python)) for k in ('command','readback')})
        for key in ('command','readback'):
            p[key] = dict(argv=[python,'-B',str(self.script)],executable_sha256=sha(python),script_sha256=sha(self.script),stdout='owned check\n')
        self.scope = dict(cwd=str(self.repo),procedure=str(self.procedure),resource_evidence='Whole owned fictional QA scope',
            read_roots=[str(self.repo),str(self.procedure),str(self.script)],write_roots=[str(output)],network=False,ordinary_effects=p)
        task = self.config['tasks']['qa-execution']
        task.update(effects='owner-reconcile',require_package_scope=True,scope_roots=[str(self.area)],network=False)
        task['effect_authority']['operations'] = ['execute-admitted-qa']
        branch = self.config['tasks']['branch-proposer']
        branch.update(effects='none' if 'readonly' in self._testMethodName else 'owner-reconcile',network=False)
        if 'excluded' in self._testMethodName:
            self.config['artifact_exclusions'] = [str(self.area/'withheld')]
        # Separate disjoint case has an independently configured scope before
        # validation/grants/Work selection, never a renamed frozen job.
        root = self.area/'disjoint' if 'disjoint' in self._testMethodName else self.repo
        root.mkdir(exist_ok=True)
        branch.update(cwd=str(root))
        branch['effect_authority'].update(read_roots=[str(root)],write_roots=[str(root)],operations=['write-role-records'])
        if branch['effects'] == 'none':
            branch['effect_authority'].update(write_roots=[],operations=['read-reports'])

    def branch(self):
        self.post('Branch','branch-proposer','branch-package')
        job = self.store.reserve()
        self.assertIsNotNone(job)
        self.assertEqual(job['role'],'Branch')
        self.assertEqual(job['effects'],'unknown')
        self.assertIsNone(job['active_attempt'])
        self.assertEqual(self.store.rows('SELECT * FROM ordinary_resources'),[])
        self.hit('reserve.Branch')
        return job

    def blocked(self):
        self.hit('blocked')
        return resource_scopes.blocked(self.store,self.qa)

    def test_overlap_unknown_cross_role_without_lease(self):
        job = self.branch()
        before = '\n'.join(self.store.db.iterdump())
        self.assertTrue(self.blocked())  # QA629-F1 unchanged required oracle.
        self.assertEqual(before,'\n'.join(self.store.db.iterdump()))
        self.assertEqual(self.store.job(job['id'])['effects'],'unknown')

    def test_disjoint_frozen_scope_and_exact_ownjob_exclusion(self):
        self.assertFalse(self.blocked())  # Own QA unknown job is excluded.
        job = self.branch()
        self.assertFalse(self.blocked())
        self.assertEqual(self.store.job(job['id'])['effects'],'unknown')
        self.assertEqual(self.store.enrollment('QA')['legacy_hold'],'fictional global UNKNOWN')

    def test_disjoint_unmapped_and_held_scope_fail_closed(self):
        job = self.branch()
        self.assertFalse(self.blocked())
        # Separate seeded legacy original, never edit a frozen resource policy.
        self.store.db.execute("INSERT INTO jobs(id,role,phase,task,members,controller,token,created,effects,hold_reason) "
            "VALUES('own-unmapped','Branch','proposer','unmapped-original','[]','own-fictional-collector','own-token',?,'unknown','held original')",
            (time.time(),))
        self.assertTrue(self.blocked())
        self.assertEqual(self.store.job(job['id'])['effects'],'unknown')

    def seed_original(self, policy):
        # A separately seeded fictional legacy original tests the immutable
        # frozen map, including tasks no longer in the current configuration.
        self.store.db.execute("INSERT INTO jobs(id,role,phase,task,members,controller,token,created,effects,hold_reason) "
            "VALUES('own-frozen','Branch','proposer','retired-original','[]','own-fictional-collector','frozen-token',?,'unknown','held original')",
            (time.time(),))
        self.store.db.execute('INSERT INTO job_resource_policies VALUES(?,?,NULL)',('own-frozen',encode(policy)))

    def test_disjoint_retired_frozen_task_uses_original_scope(self):
        self.branch()
        self.seed_original(self.config['tasks']['branch-proposer'])
        self.assertFalse(self.blocked())
        self.assertEqual(self.store.job('own-frozen')['effects'],'unknown')

    def test_disjoint_excluded_original_refuses_before_metadata(self):
        self.branch()
        prior = copy.deepcopy(self.config['tasks']['branch-proposer'])
        prior.update(cwd=str(self.area/'withheld'))
        prior['effect_authority'].update(read_roots=[prior['cwd']],write_roots=[])
        self.seed_original(prior)
        # The excluded synthetic operand is lexical and deliberately absent.
        original = Path.is_symlink
        def metadata(path):
            if path == self.area/'withheld':
                raise AssertionError('excluded operand metadata')
            return original(path)
        with patch.object(Path,'is_symlink',metadata):
            self.assertTrue(self.blocked())

    def test_known_readonly_completion_releases_only_this_local_job(self):
        job = self.branch()
        self.assertTrue(self.blocked())
        self.run_job(job,result())
        self.assertEqual(self.store.job(job['id'])['effects'],'none')
        self.assertFalse(self.blocked())
        self.assertEqual(self.store.enrollment('QA')['legacy_hold'],'fictional global UNKNOWN')

    def test_disjoint_authority_and_admission_guards(self):
        self.branch()
        self.assertFalse(self.blocked())
        self.store.admit('own-package',self.config['roles']['Branch']['owner'],
                         dict(task_scopes={'qa-execution':self.scope},changed='own synthetic admission drift'))
        self.assertTrue(self.blocked())
        self.store.admit('own-package',self.config['roles']['Branch']['owner'],dict(task_scopes={'qa-execution':self.scope}))
        self.assertFalse(self.blocked())
        self.store.db.execute('UPDATE prospective_authorities SET revoked=?',(time.time(),))
        self.assertTrue(self.blocked())
        self.store.db.execute('UPDATE prospective_authorities SET revoked=NULL')
        board = self.boards['QA']
        with actor(board.store,self.config['roles']['Work']['owner']):
            board.revoke_software(self.store,self.store.enrollment('QA')['grant_id'])
        self.assertTrue(self.blocked())


class OrdinaryFrontier(Fixture, unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.bootstrap(self.configure)
        if 'processing' in self._testMethodName:
            self.select()

    def configure(self):
        for task in self.config['tasks'].values():
            task.update(delivery_required=True,allowed_handoffs=list(self.config['roles']))
        self.config['tasks']['work-proposer']['publish_internal_results'] = True
        integrator = self.config['tasks']['work-integrator']
        integrator.update(publish_internal_results=True,software_handoffs={'Branch':['branch-proposer']})
        integrator['responses']['complete'] = ['branch-proposer']

    async def pump(self):
        if 'async' in self._testMethodName or 'processing' in self._testMethodName:
            await self.runtime.pump_deliveries_async()
        else:
            self.runtime.pump_deliveries()
        self.runtime.reconcile_completed()
        self.hit('normal_pump')

    def outbox(self, key):
        return self.store.one('SELECT * FROM outboxes WHERE id=?',(key,))

    async def chain(self, adverse):
        source = self.post('Work','work-proposer',None)
        proposer = self.store.reserve(); self.assertIsNotNone(proposer)
        answer = dict(**result(category='proposal'),handoffs=[],no_handoff_reason='Published report supplies exact next reader')
        if adverse:
            answer['failures'] = [{'source':'fictional source','error':'adverse report retained'}]
        self.run_job(proposer,answer)
        self.classify()
        await self.pump()
        key = digest({'response_delivery':self.store.job(proposer['id'])['response']})
        integrator = self.store.reserve()
        self.assertEqual(integrator['task'],'work-integrator')
        self.run_job(integrator,dict(**result(),handoffs=[],no_handoff_reason='Exact terminal report already published'))
        self.classify()
        for _ in range(4):
            await self.pump()
        terminal_event = self.store.job(integrator['id'])['response']
        terminal = self.store.one('SELECT * FROM queue WHERE event=?',(terminal_event,))
        self.assertEqual(terminal['task'],'branch-proposer')
        self.assertIsNone(terminal['job'])
        unstarted = self.outbox(key)['processed_at']
        board_original = self.boards['Work'].delivery_status(key)
        self.store.set_hold(terminal_event,'Explicit owned synthetic downstream source hold')
        for _ in range(4):
            await self.pump()
        held = self.outbox(key)['processed_at']
        # Release only the explicitly seeded own test hold, through public API.
        self.store.set_hold(terminal_event,None)
        terminal_job = self.store.reserve()
        self.assertEqual(terminal_job['task'],'branch-proposer')
        self.run_job(terminal_job,dict(**result(),handoffs=[],no_handoff_reason='Terminal owned SDK completion'))
        self.classify()
        for _ in range(12):
            await self.pump()
            if self.outbox(key)['processed_at'] is not None and delivery(self.store,key)['complete']:
                break
        final = self.outbox(key)
        board_final = self.boards['Work'].delivery_status(key)
        self.assertIsNotNone(final['processed_at'])
        self.assertTrue(delivery(self.store,key)['complete'])
        # Reobservation conserves the Board's first real processing clock.
        if board_original['processed_at'] is not None:
            self.assertEqual(board_final['processed_at'],board_original['processed_at'])
        stable = self.store.rows('SELECT id,members,active_attempt FROM jobs ORDER BY id')
        original_clock = board_final['processed_at']
        board = self.boards['Work']
        from coordinator_runtime.automatic_control import SCHEMA
        with board.opened() as conn:
            conn.executescript(SCHEMA)
            board.require_control(conn,key)
        self.runtime.pump_delivery(self.outbox(key))
        for _ in range(3):
            await self.pump()
        self.assertFalse(self.store.delivery_satisfied(self.outbox(key)))
        self.assertIsNone(self.outbox(key)['processed_at'])
        later = self.boards['Work'].delivery_status(key)
        self.assertIsNone(later['processed_at'])
        self.assertEqual(later['substantive_processed_at'],original_clock)
        self.assertEqual(stable,self.store.rows('SELECT id,members,active_attempt FROM jobs ORDER BY id'))
        (self.area/'frontier-observations.json').write_text(encode(dict(key=key,source=source['id'],proposer=proposer['id'],
            integrator=integrator['id'],terminal=terminal_job['id'],unstarted=unstarted,held=held,
            board_original=board_original,board_final=board_final,final=final,methods=self.methods))+'\n')
        self.assertIsNone(unstarted)  # QA629-F2 oracle, unchanged across trials.
        self.assertIsNone(held)
        receiving = self.store.job(proposer['id'])['response']
        self.assertEqual(self.store.one('SELECT event FROM processing_delivery_links WHERE delivery=?',(key,))['event'],receiving)
        self.assertEqual(len([j for j in self.store.rows('SELECT members FROM jobs')
            if any(m['event']==receiving for m in json.loads(j['members']))]),1)

    async def test_ordinary_sync_report_frontier(self):
        await self.chain(adverse=True)

    async def test_ordinary_async_report_frontier(self):
        await self.chain(adverse=True)

    async def test_processing_capability_report_frontier(self):
        await self.chain(adverse=True)

    async def test_ordinary_clean_report_frontier(self):
        await self.chain(adverse=False)


class ConsumerRegressions(Fixture, unittest.IsolatedAsyncioTestCase):
    """Existing consumer assertions with this file's SDK collection seam.

    No AppServer child, profile environment or provider is used. The unchanged
    affected-consumer tests still exercise their real guards and normal pump.
    """
    from test_software_consumption import SoftwareConsumption as _Original
    sender = _Original.sender
    consume = _Original.consume
    test_retries = _Original.test_retries_reuse_one_receiver_and_original_source
    test_unknown_effect_and_admission = _Original.test_receiver_unknown_effects_and_changed_admission_prevent_settlement
    test_receiver_grant = _Original.test_revoked_receiver_grant_retains_sender_source_and_pending_delivery
    test_transport_uncertainty = _Original.test_unknown_and_inflight_native_sends_keep_original_custody

    async def asyncSetUp(self):
        self.bootstrap(self.configure)

    def configure(self):
        for task in self.config['tasks'].values():
            task.update(delivery_required=True,allowed_handoffs=list(self.config['roles']))
        for name,receiver in [('work-integrator','Branch'),('branch-integrator','QA'),
                              ('reviews-integrator','Work'),('qa-cleanup','Branch')]:
            self.config['tasks'][name]['software_handoffs'] = {receiver:[
                'qa-execution' if receiver=='QA' else receiver.lower()+'-proposer']}
        self.config['tasks']['reviews-integrator']['publish_internal_results'] = True

    async def classify(self):
        Fixture.classify(self)

    async def task(self, job, answer=None, extra=None):
        self.assertIsNone(extra)
        return self.run_job(job,answer or dict(**result(),handoffs=[],no_handoff_reason='Own synthetic SDK completion'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
