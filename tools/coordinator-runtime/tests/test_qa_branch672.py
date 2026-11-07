"""One synthetic package: real QA namespace/readback, Branch CAS and acceptance.

SDK principals and collected model answers are explicit seams. No live journal,
native/provider, product checkout, deployed selection or foreign collector.
All created fixture material is retained under QA629_FIXTURES.
"""
import copy
import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from support import collect, result
from test_qa629_repairs import Fixture, actor, sha
from test_software_routes643 import SoftwareRoutes643
from test_task_text510 import TaskText510
from test_ordinary_effects import OrdinaryEffects
from coordinator_runtime import branches, configuration, ordinary, processing, prospective, ref_scope, report_scope, resource_scopes
from coordinator_runtime.contracts import QA_BRANCH_SEQUENCE, Refusal, digest, encode, ident


class Sequence672(Fixture, unittest.IsolatedAsyncioTestCase):
    package_count = 1
    source = SoftwareRoutes643.source
    prepared = SoftwareRoutes643.prepared

    async def asyncSetUp(self):
        self.packages = {}
        self.bootstrap(self.configure)
        self._asyncioRunner.get_loop().set_debug(False)
        board = self.boards['Work']
        with board.store.database(str(self.board_path)) as conn:
            args = board.store.parser().parse_args(['register', '--session', self.root,
                '--role', 'root', '--route', 'managed', '--profile', '.codex2'])
            with actor(board.store, self.root):
                board.store.register(conn, args)
        self.select_software()
        self.key = 'future-qa-1'
        self.info = self.packages[self.key]
        self.repo = self.info['repo']

    def configure(self):
        self.root = ident()
        SoftwareRoutes643.configure(self)
        # Exercise the supported narrowing from the real six-operation shape.
        task = self.config['tasks']['qa-execution']
        task['effect_authority']['operations'] = ['read-source', 'read-reports', 'prepare-intents',
            'write-role-records', 'write-owned-artifacts', 'execute-admitted-qa']
        branch = self.config['tasks']['branch-integrator']
        branch.update(effects='owner-reconcile', sandbox='workspace-write', require_package_scope=True,
            scope_roots=[str(self.area)], network=False)
        branch['effect_authority'].update(operations=['organize-authorized-refs'])
        self.original_config = copy.deepcopy(self.config)
        configuration.apply_scope_options(self.original_config, self.config,
            {'operations': {'qa-execution': ['execute-admitted-qa']}, 'qa_branch_sequence': QA_BRANCH_SEQUENCE})

    def package(self, number):
        SoftwareRoutes643.package(self, number)
        key = f'future-qa-{number}'
        info = self.packages[key]
        old = self.git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
            '-c', 'commit.gpgsign=false', 'commit-tree', info['head']+'^{tree}', '-m', 'independent destination before')
        self.git('update-ref', 'refs/heads/destination', old)
        binding = ident()
        p = {k: copy.deepcopy(v) for k, v in info['p'].items() if k in {
            'git', 'git_sha256', 'repository', 'source_ref', 'source_head', 'procedure_sha256', 'timeout', 'max_output'}}
        p.update(kind='local-ref', ref='refs/heads/destination', before=old, target=info['head'],
            resources=[dict(key='branch-'+key, owner=self.config['roles']['Branch']['owner'],
                authority='Fictional exact destination custody', expires=self.now+600)],
            acceptor=self.root, acceptance_authority='Independent synthetic Root checks actual CAS/readback')
        execution = info['scope']['task_scopes']['qa-execution']
        execution['branch_binding'] = binding
        execution['ordinary_effects']['acceptor'] = self.root
        scope = dict(cwd=str(info['repo']), read_roots=[str(info['repo']), execution['procedure']],
            write_roots=[str(info['repo'])], network=False, procedure=execution['procedure'],
            resource_evidence='Finite actual owned fixture Git/ref custody', branch_binding=binding, ordinary_effects=p)
        info['scope']['task_scopes']['branch-integrator'] = scope
        info.update(branch=binding, branch_policy=p, old=old)
        self.operations[-1]['binding']['scope_sha256'] = digest(info['scope'])

    def select_software(self):
        # Reuse the public selection path, selecting the second admitted adapter
        # in the SAME prospective epoch, before any intake/job exists.
        select = prospective.select
        from unittest.mock import patch
        def both(store, issuer, selection):
            selection = copy.deepcopy(selection)
            selection['tasks']['branch-integrator']['ordinary_effects'] = 'admitted-v1'
            return select(store, issuer, selection)
        with patch.object(prospective, 'select', side_effect=both):
            SoftwareRoutes643.select_software(self)
        self.store.db.execute("UPDATE enrollments SET legacy_hold='Branch old effects UNKNOWN' WHERE role='Branch'")

    def admitted(self, accept_root=True):
        message = self.source(self.key)
        info = self.info
        branches.register(self.store, self.issuer, dict(id=info['branch'], repository=str(self.repo),
            origin='https://example.invalid/owned-fiction.git', ref='refs/heads/destination',
            incarnation=ident(), scope=self.key, root=self.root, authority='Synthetic bounded Work assignment'))
        if accept_root:
            branches.accept(self.store, info['branch'], self.root, 'Actual synthetic Root accepts this exact branch')
        return message

    async def accepted(self, attempt, decision='accepted'):
        receipt = json.loads(self.store.one('SELECT receipt FROM ordinary_runs WHERE attempt=?', (attempt,))['receipt'])
        await ordinary.accept(self.store, self.root, attempt, decision,
            dict(execution_hash=digest(receipt), rationale='Independent actual source/output/ref/readback checked', unknowns=[]))

    async def qa(self, decision='accepted'):
        job = self.store.reserve()
        self.assertIsNotNone(job)
        self.assertEqual(job['task'], 'qa-execution')
        job, attempt = self.prepared(job, result(category='consolidated'))
        self.assertTrue(await ordinary.perform(self.store, self.boards['QA'], job))
        if decision:
            await self.accepted(attempt, decision)
        response = self.store.finish_job(job['id'], job['token'])
        self.classify()
        return job, attempt, response

    def branch_account(self):
        basis = ref_scope.material(self.store, 'branch-integrator', self.key)
        return ref_scope.account(self.store, self.issuer, dict(basis=basis,
            authority_kind='work-selected-local-ref-v1', authority='Synthetic Work exact prospective ref choice', originals=[],
            activity_scope=dict(original_hold=basis['original_hold'],
                operation=digest({'operation': basis['operation'], 'repository': basis['common_repository'], 'refs': basis['local_refs']}),
                no_active_writers=True, evidence='Only this fixture repository; current exact source/destination inspected'),
            remaining_holds=[basis['original_hold']], past_effects=['Historical unknown stays with original custodian']))

    async def branch(self, decision='accepted'):
        self.branch_account()
        job = self.store.reserve()
        self.assertIsNotNone(job)
        self.assertEqual(job['task'], 'branch-integrator')
        answer = result(category='complete')
        answer['findings'].append(dict(collected_reports=report_scope.conserved_inputs(self.store, job)))
        job, attempt = self.prepared(job, answer)
        self.assertTrue(await ordinary.perform(self.store, self.boards['Branch'], job))
        if decision:
            await self.accepted(attempt, decision)
        response = self.store.finish_job(job['id'], job['token'])
        self.classify()
        return job, attempt, response

    async def test_actual_same_package_qa_branch_final_cleanup_and_single_Work_route(self):
        self.admitted()
        self.assertNotEqual(self.info['old'], self.info['head'])
        _, qa, _ = await self.qa()
        self.assertEqual([r['task'] for r in ordinary.accepted_runs(self.store, self.key, ['qa-execution'])], ['qa-execution'])
        self.assertEqual(ordinary.accepted_runs(self.store, self.key), [])
        _, branch, response = await self.branch()
        self.assertEqual(self.git('rev-parse', 'destination'), self.info['head'])
        self.assertEqual({r['task'] for r in ordinary.accepted_runs(self.store, self.key)}, {'qa-execution', 'branch-integrator'})
        queued = self.store.one('SELECT * FROM queue WHERE event=?', (response,))
        self.assertFalse(resource_scopes.blocked(self.store, queued))
        job = self.store.reserve()
        self.assertEqual(job['task'], 'qa-cleanup')
        answer = result(category='qualification')
        answer['findings'].append(dict(collected_reports=report_scope.conserved_inputs(self.store, job)))
        job, _ = self.prepared(job, answer)
        await ordinary.qualification(self.store, job)
        final = self.store.finish_job(job['id'], job['token'])
        self.assertTrue(ordinary.qualification_current(self.store, job))
        self.assertEqual(self.store.event(final)['allowed_tasks'], ['work-proposer'])
        self.classify()
        self.assertEqual(len(self.store.rows("SELECT * FROM queue WHERE task='work-proposer'")), 1)
        self.assertEqual(len(self.store.rows('SELECT * FROM ordinary_runs')), 2)
        self.assertEqual(len(self.store.rows('SELECT * FROM admissions')), 1)
        self.assertEqual({r['epoch'] for r in self.store.rows('SELECT epoch FROM ordinary_runs')}, {self.epoch['id']})
        self.assertEqual({r['actor'] for r in self.store.rows('SELECT actor FROM ordinary_acceptance')}, {self.root})
        self.assertEqual(self.store.rows('SELECT * FROM ordinary_resources'), [])
        self.assertEqual(self.store.enrollment('QA')['legacy_hold'], 'QA global UNKNOWN')
        self.assertEqual(self.store.enrollment('Branch')['legacy_hold'], 'Branch old effects UNKNOWN')
        self.assertEqual(self.original_config['tasks']['qa-execution']['responses']['consolidated'], ['qa-cleanup'])
        self.assertEqual(len(self.original_config['tasks']['qa-execution']['effect_authority']['operations']), 6)
        self.assertEqual({r['attempt'] for r in ordinary.accepted_runs(self.store, self.key)}, {qa, branch})

    async def test_unaccepted_or_rejected_QA_cannot_reserve_Branch(self):
        self.admitted()
        _, attempt, response = await self.qa(None)
        queued = self.store.one('SELECT * FROM queue WHERE event=?', (response,))
        self.assertTrue(resource_scopes.blocked(self.store, queued))
        self.assertIsNone(self.store.reserve())
        with self.assertRaises(Refusal): self.branch_account()
        await self.accepted(attempt, 'rejected')
        self.assertTrue(resource_scopes.blocked(self.store, queued))
        self.assertEqual(self.git('rev-parse', 'destination'), self.info['old'])

    async def test_final_cleanup_waits_for_actual_Branch_acceptance(self):
        self.admitted()
        await self.qa()
        _, attempt, response = await self.branch(None)
        queued = self.store.one('SELECT * FROM queue WHERE event=?', (response,))
        self.assertTrue(resource_scopes.blocked(self.store, queued))
        self.assertIsNone(self.store.reserve())
        await self.accepted(attempt)
        self.assertFalse(resource_scopes.blocked(self.store, queued))

    async def test_stale_source_or_revoked_QA_blocks_Branch_without_replay(self):
        self.admitted()
        _, _, response = await self.qa()
        queued = self.store.one('SELECT * FROM queue WHERE event=?', (response,))
        self.git('update-ref', 'refs/heads/source', self.info['old'], self.info['head'])
        self.assertTrue(resource_scopes.blocked(self.store, queued))
        self.git('update-ref', 'refs/heads/source', self.info['head'], self.info['old'])
        prospective.revoke(self.store, self.issuer, self.epoch['id'])
        self.assertTrue(resource_scopes.blocked(self.store, queued))
        self.assertEqual(len(self.store.rows('SELECT * FROM ordinary_runs')), 1)

    async def test_unknown_lease_and_unaccepted_Root_keep_Branch_held(self):
        self.admitted(False)
        # QA itself requires the genuine Root acceptance through ordinary source.
        branches.accept(self.store, self.info['branch'], self.root, 'Synthetic actual Root accepts')
        await self.qa()
        # Explicit database-corruption seam: a missing actual Root acceptance
        # cannot be replaced by the previously accepted QA run.
        self.store.db.execute("UPDATE branch_associations SET state='assigned' WHERE id=?", (self.info['branch'],))
        with self.assertRaises(Refusal): self.branch_account()
        self.assertIsNone(self.store.reserve())
        self.store.db.execute("UPDATE branch_associations SET state='active' WHERE id=?", (self.info['branch'],))
        self.store.db.execute("INSERT INTO ordinary_resources VALUES('unmapped', 'unknown-original')")
        with self.assertRaises(Refusal): self.branch_account()
        self.assertIsNone(self.store.reserve())
        self.assertEqual(self.store.rows('SELECT * FROM ordinary_resources'), [dict(resource='unmapped', attempt='unknown-original')])

    async def test_omitted_adapter_or_changed_admission_never_qualifies(self):
        self.admitted()
        await self.qa()
        await self.branch()
        admission = self.store.one('SELECT * FROM admissions WHERE package=?', (self.key,))
        receipt = json.loads(admission['receipt'])
        del receipt['task_scopes']['branch-integrator']
        # Corrupt only this owned fixture; supported admissions cannot rewrite
        # their processing resolution. Neither default nor subset may waive it.
        self.store.db.execute('UPDATE admissions SET receipt=? WHERE package=?', (encode(receipt), self.key))
        self.assertEqual(ordinary.accepted_runs(self.store, self.key), [])
        self.assertEqual(ordinary.accepted_runs(self.store, self.key, ['qa-execution']), [])
        self.assertFalse(ordinary.accepted_package(self.store, self.key))
        self.assertIsNone(self.store.reserve())

    async def test_rejected_Branch_result_cannot_qualify_or_reexecute(self):
        self.admitted()
        await self.qa()
        _, _, response = await self.branch('rejected')
        queued = self.store.one('SELECT * FROM queue WHERE event=?', (response,))
        self.assertTrue(resource_scopes.blocked(self.store, queued))
        self.assertIsNone(self.store.reserve())
        self.assertFalse(ordinary.accepted_package(self.store, self.key))
        self.assertEqual(len(self.store.rows('SELECT * FROM ordinary_runs')), 2)

    async def test_Branch_cannot_omit_whole_QA_before_CAS(self):
        self.admitted()
        await self.qa()
        self.branch_account()
        job = self.store.reserve()
        self.assertEqual(job['task'], 'branch-integrator')
        job, _ = self.prepared(job, result(category='complete'))
        with self.assertRaisesRegex(Refusal, 'whole accepted QA report'):
            await ordinary.perform(self.store, self.boards['Branch'], job)
        self.assertEqual(len(self.store.rows('SELECT * FROM ordinary_runs')), 1)
        self.assertEqual(self.git('rev-parse', 'destination'), self.info['old'])

    async def test_stale_Branch_ref_and_split_package_cannot_enter_cleanup(self):
        self.admitted()
        await self.qa()
        _, _, response = await self.branch()
        queued = self.store.one('SELECT * FROM queue WHERE event=?', (response,))
        self.assertTrue(resource_scopes.blocked(self.store, {**queued, 'package': 'another-package'}))
        self.git('update-ref', 'refs/heads/destination', self.info['old'], self.info['head'])
        self.assertTrue(resource_scopes.blocked(self.store, queued))
        self.assertIsNone(self.store.reserve())


class Selection672(TaskText510):
    def test_supported_operation_narrowing_and_immutable_old_policies(self):
        task = self.config['tasks']['qa-execution']
        task.update(effects='owner-reconcile', sandbox='workspace-write', require_package_scope=True, scope_roots=[str(self.root)])
        task['effect_authority']['operations'] = ['read-source', 'read-reports', 'prepare-intents', 'write-role-records',
            'write-owned-artifacts', 'execute-admitted-qa']
        prior = copy.deepcopy(self.config)
        # Freeze an original resource task, as the reservation API does.
        self.store.db.execute('INSERT INTO job_resource_policies VALUES(?,?,?)', ('old-job', encode(task), None))
        before = self.store.one('SELECT * FROM job_resource_policies WHERE job=?', ('old-job',))
        draft = self.draft({'operations': {'qa-execution': ['execute-admitted-qa']}})
        configuration.validate_changes(self.store, draft, ['qa-execution'])
        self.assertEqual(draft['tasks']['qa-execution']['effect_authority']['operations'], ['execute-admitted-qa'])
        self.assertEqual(self.config, prior)
        self.assertEqual(self.store.one('SELECT * FROM job_resource_policies WHERE job=?', ('old-job',)), before)
        with self.assertRaises(Refusal): configuration.validate_changes(self.store, draft, ['work-proposer'])
        for selected in [[], ['read-reports'], ['execute-admitted-qa', 'write-role-records']]:
            with self.assertRaises(Refusal): self.draft({'operations': {'qa-execution': selected}})
        with self.assertRaises(Refusal): self.draft({'operations': {'branch-integrator': ['execute-admitted-qa']}})

    def test_whole_candidate_sequence_and_unselected_or_tampered_routes_refuse(self):
        for name, operation in [('qa-execution', 'execute-admitted-qa'), ('branch-integrator', 'organize-authorized-refs')]:
            task = self.config['tasks'][name]
            task.update(effects='owner-reconcile', sandbox='workspace-write', require_package_scope=True, scope_roots=[str(self.root)])
            task['effect_authority']['operations'].append(operation)
        cleanup = self.config['tasks']['qa-cleanup']
        cleanup.update(effects='owned-artifacts', sandbox='workspace-write')
        original = copy.deepcopy(self.config)
        options = {'operations': {'qa-execution': ['execute-admitted-qa']},
            'package_scoped_cleanup': ['qa-cleanup'], 'qa_branch_sequence': QA_BRANCH_SEQUENCE}
        draft = self.draft(options)
        tasks = ['qa-execution', 'branch-integrator', 'qa-cleanup', 'work-proposer']
        configuration.validate_changes(self.store, draft, tasks)
        self.assertEqual(self.config, original)
        with self.assertRaises(Refusal): configuration.validate_changes(self.store, draft, tasks[:-1])
        bad = copy.deepcopy(draft)
        bad['tasks']['qa-cleanup']['responses']['qualification'] = ['branch-integrator']
        with self.assertRaises(Refusal): configuration.validate_changes(self.store, bad, tasks)
        with self.assertRaises(Refusal): self.draft({**options, 'qa_branch_sequence': 'arbitrary-route'})


class Boundary672(unittest.TestCase):
    def test_changed_common_repository_refuses_before_object_queries_or_metadata(self):
        # Only two inert Git metadata answers; no filesystem or runtime exists.
        repository = '/synthetic-672/repo'
        run = {'receipt': encode({'after': {'git_common_dir': '/synthetic-672/repo/.git'}})}
        policy = {'git': '/usr/bin/git', 'repository': repository, 'timeout': 1}
        calls = []
        def metadata(argv, **kwargs):
            calls.append(argv)
            args = argv[argv.index(repository)+1:]
            if args == ['rev-parse', '--show-toplevel']:
                return SimpleNamespace(stdout=(repository+'\n').encode())
            if args == ['rev-parse', '--path-format=absolute', '--git-common-dir']:
                return SimpleNamespace(stdout=b'/unselected-common-672\n')
            raise AssertionError('object/config query before topology qualification')
        with patch.object(ordinary.subprocess, 'run', side_effect=metadata):
            with self.assertRaisesRegex(Refusal, 'topology'):
                ordinary.accepted_source_current(object(), run, policy)
        self.assertEqual(len(calls), 2)


class Origin672(OrdinaryEffects):
    async def asyncSetUp(self):
        await super().asyncSetUp()
        # The legacy fixture omits origin although the unchanged ordinary.source
        # contract requires it. Add only an owned inert URL; all validators,
        # tools, namespace execution and acceptance checks remain production.
        self.git('remote', 'add', 'origin', 'https://example.invalid/owned-ordinary672.git')


def load_tests(loader, tests, pattern):
    return unittest.TestSuite([loader.loadTestsFromTestCase(Sequence672),
        Selection672('test_supported_operation_narrowing_and_immutable_old_policies'),
        Selection672('test_whole_candidate_sequence_and_unselected_or_tampered_routes_refuse'),
        loader.loadTestsFromTestCase(Boundary672)])
