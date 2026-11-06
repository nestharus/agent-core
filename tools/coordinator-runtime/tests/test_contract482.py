"""Owned offline contract correction; original OS waits, fictional actors/models."""
import copy
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from coordinator_runtime import method_closure, ordinary, prospective, public_tools, reviews
from coordinator_runtime.contracts import Refusal, digest, ident
from test_cutover475 import Mixed, sha


class MethodClosure(unittest.TestCase):
    def setUp(self):
        self.home = Path('/fixtures') / 'method482' / ident()
        self.home.mkdir(parents=True)
        self.entry = self.home / 'unified-reviewer.prompt.md'

    def test_required_reference_external_and_unknown_dependencies(self):
        self.entry.write_text('[Required](definition.md) [Alternative](coverage-preserving-review-candidate.md) [Citation](https://example.invalid/doc.md)\n')
        child = self.home / 'definition.md'
        child.write_text('Required public definition\n')
        self.assertEqual(set(method_closure.files(str(self.entry))), {str(self.entry), str(child)})
        with self.assertRaisesRegex(Refusal,'required unified definitions missing'):
            reviews.method_files(str(self.entry),'unified-definitions-v1')
        child.unlink()
        with self.assertRaisesRegex(Refusal, 'required public method dependency unavailable'):
            method_closure.files(str(self.entry))

    def test_private_malformed_symlink_and_exclusion_refuse_before_body(self):
        for target in ['/private/AGENTS.md', '../private.md', 'file:///private.md', 'https:/broken.md', '%2Fprivate.md', '.codex/config.md', 'runs/README.md']:
            self.entry.write_text('[Required]('+target+')\n')
            with self.subTest(target=target), self.assertRaises(Refusal):
                method_closure.files(str(self.entry))
        child = self.home / 'definition.md';child.write_text('never acquired')
        self.entry.write_text('[Required](definition.md)\n')
        from coordinator_runtime import custody
        original = custody.read_file
        acquired = []
        def read(path, maximum):
            acquired.append(str(path));return original(path, maximum)
        with patch.object(method_closure, 'read_file', side_effect=read):
            with self.assertRaises(Refusal):method_closure.files(str(self.entry), [str(child)])
        self.assertEqual(acquired, [str(self.entry)])
        child.unlink();child.symlink_to(self.entry)
        with self.assertRaises(Refusal):method_closure.files(str(self.entry))

    def test_healthy_silence_and_due_unchanged_violation_repeats(self):
        from support import config_at, enrolled
        cfg=config_at(self.home);now=[100000.]
        store=enrolled(cfg,clock=lambda:now[0]);self.addCleanup(store.close)
        self.assertEqual(store.emit_alerts(),[])
        store.record_operational_error('owned-violation',{'reason':'independent fictional unresolved dependency'},'Work')
        now[0]+=cfg['deadlines']['alert_interval']
        first=store.emit_alerts();self.assertTrue(first)
        self.assertEqual(store.emit_alerts(),[])  # Same interval is not due.
        now[0]+=cfg['deadlines']['alert_interval']
        second=store.emit_alerts();self.assertTrue(second)
        self.assertTrue({r['id'] for r in first}.isdisjoint(r['id'] for r in second))
        store.clear_operational_error('owned-violation')
        now[0]+=cfg['deadlines']['alert_interval']
        self.assertEqual(store.emit_alerts(),[])


class ContinuousMixed(Mixed):
    def fixture_config(self, cfg, area):
        cfg = super().fixture_config(cfg, area)
        task = cfg['tasks']['branch-integrator']
        task.update(effects='owner-reconcile')
        task['effect_authority']['operations'] = ['organize-authorized-refs']
        (self.repo/'branch-change.txt').write_text('Independent Branch intent: destination must include this change.\n')
        self.git('add','branch-change.txt')
        self.git('-c','user.name=Fixture','-c','user.email=fixture@example.invalid','-c','commit.gpgsign=false','commit','-m','Owned Branch change')
        self.before = self.head;self.head = self.git('rev-parse','HEAD')
        self.qa_task_scopes['qa-execution']['ordinary_effects']['source_head'] = self.head
        p = self.qa_task_scopes['qa-execution']['ordinary_effects']
        pin = {'path':'/usr/bin/python3.12','bytes':Path('/usr/bin/python3.12').stat().st_size,'sha256':sha('/usr/bin/python3.12')}
        p['public_executables'] = {role:copy.deepcopy(pin) for role in ['command','readback']}
        for role in ['command','readback']:
            cmd = p[role];cmd['script_sha256']=sha(cmd['argv'][0]);cmd['argv'] = [pin['path'],'-B',*cmd['argv']];cmd['executable_sha256'] = pin['sha256']
        return cfg

    async def model(self,store,attempt,prompt,spec,schema):
        a=store.attempt(attempt)
        if a['kind']!='diagnosis':return await super().model(store,attempt,prompt,spec,schema)
        job=store.job(a['job'])
        self.assertEqual(job['task'],'branch-integrator');self.assertEqual(job['effects'],'unknown')
        self.assertIsNone(ordinary.selected(store,job))
        store.begin(attempt,{'fictional482_model_transport':True});store.session(attempt,ident())
        return {'exit':0,'capture':'complete','cleanup':'done','error':None,
            'result':{'profile':'@owner','remaining':'Original Branch owner must reconcile receiving effects/outboxes',
                'rationale':'Collected receiving has no adapter; configured owner-reconcile guard still applies. No replay is authorized.'}}

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.error_history=[]
        record=self.store.record_operational_error
        def keep(*args,**kwargs):
            self.error_history.append((args,kwargs));return record(*args,**kwargs)
        self.store.record_operational_error=keep
        a = self.store.one('SELECT receipt FROM admissions WHERE package=?', ('native-pkg',))
        receipt = json.loads(a['receipt'])
        p = {'kind':'local-ref','git':'/usr/bin/git','git_sha256':sha('/usr/bin/git'),
             'repository':str(self.repo),'source_ref':'refs/heads/source','source_head':self.head,
             'procedure_sha256':sha(self.procedure),'resources':[{'key':'owned-branch482',
             'owner':self.config['roles']['Work']['owner'],'authority':'Fictional exact exclusive ref custody','expires':self.now+3500}],
             'acceptor':self.config['roles']['Work']['owner'],'acceptance_authority':'Independent fictional Branch intent owner',
             'timeout':20,'max_output':32768,'ref':'refs/heads/destination','before':self.before,'target':self.head}
        receipt['task_scopes']['branch-integrator'] = {'cwd':str(self.repo),'read_roots':[str(self.area)],
            'write_roots':[str(self.repo)],'network':False,'procedure':str(self.procedure),
            'resource_evidence':['Fictional original ref owners and exact association'],'branch_binding':self.branch,'ordinary_effects':p}
        self.store.admit('native-pkg',self.config['roles']['Branch']['owner'],receipt)

    def select_qa_boundary(self):
        self.ordinary_epoch = prospective.select(self.store,self.config['roles']['Work']['owner'],
            {'configuration':digest(self.config),'authority':'Fictional single continuing selection: scoped Branch effects and QA execution, separate receiving',
             'expires':self.now+3600,'grants':{r:self.store.enrollment(r)['grant_id'] for r in self.config['roles']},
             'tasks':{t:{'task_hash':digest(policy),'software_handoffs':policy.get('software_handoffs',{}),
                'ordinary_effects':'admitted-v1' if t in {'branch-integrator','qa-execution'} else False}
                for t,policy in self.config['tasks'].items()},'processing_capability':self.key})
        return self.ordinary_epoch

    async def accept_run(self, run):
        receipt = json.loads(run['receipt'])
        evidence = {'execution_hash':digest(receipt),'rationale':'Independent fictional source/ref or marker intent and complete original readback checked','unknowns':[]}
        for actor in [self.config['actor'],self.store.controller,receipt['worker']]:
            with self.assertRaises(Refusal):await ordinary.accept(self.store,actor,run['attempt'],'accepted',evidence)
        await ordinary.accept(self.store,self.config['roles']['Work']['owner'],run['attempt'],'accepted',evidence)

    async def test_continuous_branch_effect_qa_execution_cleanup_and_receiving(self):
        key = self.key;configuration = digest(self.config);epoch = self.select_qa_boundary()['id']
        def branch_proposal(job,attempt,prompt,answer):
            if job['task']=='branch-proposer':answer['category']='proposal'
        self.task_hook = branch_proposal
        e = self.post('Advance owned destination to the independently specified source',role='Branch',package='native-pkg')
        self.initial[e['id']] = 'branch-proposer'
        await self.ticks(lambda:self.store.one("SELECT r.attempt FROM ordinary_runs r JOIN jobs j ON j.id=r.job WHERE j.package='native-pkg' AND r.state='reconciled'"))
        branch = self.store.one("SELECT r.* FROM ordinary_runs r JOIN jobs j ON j.id=r.job WHERE j.package='native-pkg'")
        self.assertEqual(self.git('rev-parse','destination'),self.head)
        self.assertNotEqual(self.before,self.head)
        self.assertEqual(json.loads(branch['receipt'])['before']['branch']['id'],self.branch)
        await self.accept_run(branch)
        output = self.area/'qa-output'
        q = self.post('Execute independent source/marker intent',role='QA',package='qa475-one');self.initial[q['id']] = 'qa-execution'
        def consolidate(job,attempt,prompt,answer):
            if job['task']=='qa-cleanup':
                self.assertEqual((output/'marker').read_text(),'source actually executed')
                self.assertTrue(ordinary.accepted_package(self.store,'qa475-one'))
                Path(__import__('coordinator_runtime.publication',fromlist=['stages']).stages(self.store,attempt)[str(self.cleanup_file)]).write_text(json.dumps({'package':'qa475-one','status':'qualified','source':self.head}))
        self.task_hook = consolidate
        await self.ticks(lambda:self.store.one("SELECT r.attempt FROM ordinary_runs r JOIN jobs j ON j.id=r.job WHERE j.package='qa475-one' AND r.state='reconciled'"))
        qa = self.store.one("SELECT r.* FROM ordinary_runs r JOIN jobs j ON j.id=r.job WHERE j.package='qa475-one'")
        self.assertFalse(ordinary.accepted_package(self.store,'qa475-one'))
        self.assertEqual(json.loads(qa['receipt'])['outcome']['actual_exit'],0)
        await self.accept_run(qa)
        await self.ticks(lambda:self.store.one("SELECT id FROM jobs WHERE task='qa-cleanup' AND package='qa475-one' AND state='closed'"))
        cleanup = self.store.one("SELECT * FROM jobs WHERE task='qa-cleanup' AND package='qa475-one'")
        self.assertTrue(ordinary.qualification_current(self.store,cleanup))
        self.assertEqual(json.loads(self.cleanup_file.read_text())['source'],self.head)
        await self.ticks(lambda:self.store.one("SELECT j.id FROM jobs j JOIN attempts a ON a.id=j.active_attempt WHERE j.task='branch-integrator' AND j.package='qa475-one' AND a.collected IS NOT NULL"))
        receiving = self.store.one("SELECT * FROM jobs WHERE task='branch-integrator' AND package='qa475-one'")
        self.assertIsNone(ordinary.selected(self.store,receiving))
        self.assertIsNone(self.store.one('SELECT attempt FROM ordinary_runs WHERE job=?',(receiving['id'],)))
        # The task still has its real owner-reconcile guard. A receiving-only
        # admission does not automatically clear it or fabricate acceptance.
        self.assertEqual(receiving['effects'],'unknown')
        self.assertNotEqual(receiving['state'],'closed')
        self.store.reconcile_effects(receiving['id'],receiving['token'],self.config['roles']['Branch']['owner'],
            {'evidence':['Fictional Branch owner checked collected original, read-only scope, complete tool account and no adapter intent'], 'unknown_effects':[]})
        self.dispatch.try_finish(receiving['id'])
        self.dispatch.pump_deliveries()
        # Owner questions emitted by the real guard/diagnostic require their
        # own actual recipient pickup, processing and disposition. This fixture
        # actor is an explicit SDK identity seam, not a native/model END claim.
        board=self.boards['Branch']
        owner=self.config['roles']['Branch']['owner']
        for outbox in self.store.rows("SELECT * FROM outboxes WHERE job=? AND recipient='Branch' AND kind IN ('question','effect-request')",(receiving['id'],)):
            self.dispatch.pump_delivery(outbox)
            with patch.dict(os.environ,{'CODEX_SESSION_ID':owner}):
                view=board.show_delivery(outbox['id'])
                evidence={'evidence':['Original recipient read the exact owned delivery '+digest(view['payload'])+
                    '; original collected read-only receiving and effect reconciliation verified'],
                    'resolution':'Branch owner disposition: receiving complete; no adapter effect, unknown effects or replay authorized'}
                for stage,field in [('picked-up','pickup'),('processed','processing'),('settled','settlement')]:
                    if not view['delivery'][field]:board.delivery_stage(outbox['id'],stage,evidence)
        await self.ticks(lambda:self.store.job(receiving['id'])['state']=='closed')
        self.assertEqual(self.store.one('SELECT COUNT(*) AS n FROM prospective_authorities')['n'],1)
        self.assertEqual({r['epoch'] for r in self.store.rows('SELECT epoch FROM ordinary_runs')},{epoch})
        self.assertEqual(self.key,key);self.assertEqual(digest(self.config),configuration)
        self.assertEqual(self.store.rows('SELECT * FROM ordinary_resources'),[])
        self.assertEqual(self.store.rows('SELECT id FROM attempts WHERE collected IS NULL'),[],repr(self.error_history))
        self.assertEqual(self.dispatch.runtime_errors,{})

    async def test_public_tool_identity_does_not_grant_roots_or_accept_aliases(self):
        self.select_qa_boundary()
        p = self.qa_task_scopes['qa-execution']['ordinary_effects'];pins = p['public_executables']
        public_tools.validate(self.store,pins)
        self.assertGreater(pins['command']['bytes'],4*1024*1024)
        with self.assertRaises(Refusal):ordinary.frozen_file(self.store,'/usr/bin/python3.12',[str(self.area)])
        bad_script=copy.deepcopy(p['command']);bad_script['script_sha256']=None
        with self.assertRaises(Refusal):ordinary.command_policy(self.store,bad_script,[str(self.area)],pins['command'])
        for path in ['/usr','/usr/bin/python3','/usr/bin/gh',str(self.area/'python')]:
            bad = copy.deepcopy(pins);bad['command']['path'] = path
            with self.assertRaises(Refusal):public_tools.validate(self.store,bad)
        for field,value in [('bytes',pins['command']['bytes']-1),('sha256','0'*64)]:
            bad = copy.deepcopy(pins);bad['command'][field] = value
            with self.assertRaises(Refusal):public_tools.validate(self.store,bad)
        command=copy.deepcopy(p['command'])
        for argv in [['/usr/bin/python3.12','-c','print(1)'],
                     ['/usr/bin/python3.12','-B','/private/runner.py'],
                     ['/usr/bin/python3.12','-B','-m','unittest','discover','-s','/private']]:
            command['argv']=argv
            with self.assertRaises(Refusal):ordinary.command_policy(self.store,command,[str(self.area)],pins['command'])
        command.pop('script_sha256')
        command['argv']=['/usr/bin/python3.12','-B','-m','unittest','discover','-s',str(self.repo),'-v']
        ordinary.command_policy(self.store,command,[str(self.area)],pins['command'])
        command['argv'][6]='/private'
        with self.assertRaises(Refusal):ordinary.command_policy(self.store,command,[str(self.area)],pins['command'])
        scope=copy.deepcopy(self.qa_task_scopes['branch-integrator'])
        self.store.admit('legacy-receiving',self.config['roles']['Branch']['owner'],{'task_scopes':{'branch-integrator':scope}})
        with self.assertRaisesRegex(Refusal,'complete exact operands'):
            ordinary.policy_for(self.store,{'task':'branch-integrator','package':'legacy-receiving','role':'Branch','phase':'integrator'})
        scope['ordinary_effects']=None
        self.store.admit('malformed-receiving',self.config['roles']['Branch']['owner'],{'task_scopes':{'branch-integrator':scope}})
        with self.assertRaisesRegex(Refusal,'explicit object'):
            ordinary.policy_for(self.store,{'task':'branch-integrator','package':'malformed-receiving','role':'Branch','phase':'integrator'})
        # The receiving exception never turns QA execution into model-only
        # qualification. This bounded selector control supplies no execution.
        scope.pop('ordinary_effects')
        self.store.admit('missing-qa-operation',self.config['roles']['Branch']['owner'],{'task_scopes':{'qa-execution':scope}})
        with patch.object(prospective,'for_job',return_value={'policy':{'ordinary_effects':'admitted-v1'}}):
            with self.assertRaisesRegex(Refusal,'QA execution requires'):
                ordinary.selected(self.store,{'task':'qa-execution','package':'missing-qa-operation'})


def load_tests(loader, tests, pattern):
    # Reuse the existing fixture implementation, not its unrelated inherited
    # test selections under this deliberately different contract/configuration.
    suite=unittest.TestSuite([loader.loadTestsFromTestCase(MethodClosure)])
    for name in ['test_continuous_branch_effect_qa_execution_cleanup_and_receiving',
                 'test_public_tool_identity_does_not_grant_roots_or_accept_aliases']:
        suite.addTest(ContinuousMixed(name))
    return suite
