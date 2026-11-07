"""Review750 boundaries with real owned Git/export/QA collection and body spies."""
import copy
import json
from pathlib import Path
from unittest.mock import patch

from coordinator_runtime import ordinary, qa_source
from coordinator_runtime.contracts import Refusal, digest
from support import result
from test_post_await_admission743 import ContextFixture, Acceptance
from test_ref_resources749 import RefResources


class OrdinaryBoundaries(ContextFixture, RefResources):
    def member_id(self, job):
        return json.loads(job['members'])[0]['event']

    def evidence(self, job):
        receipt = json.loads(self.store.job(job['id'])['effect_receipt'])
        return dict(execution_hash=digest(receipt), rationale='Independent owned fixture outcome', unknowns=[])

    async def test_common_directory_hold_precedes_fresh_path_metadata(self):
        job, attempt = self.admitted_refs()
        git, scoped = ordinary.git, ordinary.scoped_path
        held = False
        async def boundary(store, key, policy, *args):
            nonlocal held
            answer = await git(store, key, policy, *args)
            if args == ('rev-parse', '--path-format=absolute', '--git-common-dir'):
                self.hold(self.member_id(job)); held = True
            return answer
        def path(*args, **kwargs):
            if held:
                self.fail('path metadata acquired after common-directory await and hold')
            return scoped(*args, **kwargs)
        with patch.object(ordinary, 'git', side_effect=boundary), patch.object(ordinary, 'scoped_path', side_effect=path):
            with self.assertRaisesRegex(Refusal, 'admission changed'):
                await ordinary.perform(self.store, self.boards['Branch'], job)
        self.assertTrue(held)
        records = [json.loads(r['record']) for r in self.store.rows('SELECT record FROM ordinary_tool_records ORDER BY seq')]
        self.assertEqual(records[-1]['exit'], 0)
        self.assertTrue(records[-1]['complete'])
        self.assertIn('ended', records[-1])
        self.assertEqual(self.store.job(job['id'])['effects'], 'unknown')
        self.assertEqual(self.git('rev-parse', 'destination'), self.old)
        self.assertEqual(self.store.one('SELECT state FROM ordinary_runs WHERE attempt=?', (attempt,))['state'], 'intent')

    def prepare_repository_qa(self):
        self.boundary()
        policy = self.admission(kind='local-qa')
        for label in ('command', 'readback'):
            original = Path(policy[label]['argv'][0])
            target = self.repo/('owned-'+label)
            target.write_bytes(original.read_bytes()); target.chmod(0o700)
            policy[label]['argv'] = [str(target)]
        self.git('add', 'owned-command', 'owned-readback')
        self.git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                 '-c', 'commit.gpgsign=false', 'commit', '-m', 'owned QA executable inputs')
        self.head = self.git('rev-parse', 'HEAD')
        policy['source_head'] = self.head
        receipt = json.loads(self.store.one('SELECT receipt FROM admissions WHERE package=?', ('package',))['receipt'])
        receipt['task_scopes']['qa-execution']['ordinary_effects'] = copy.deepcopy(policy)
        self.store.admit('package', self.config['roles']['Branch']['owner'], receipt)
        job, attempt = self.prepared(role='QA', answer=result(category='consolidated'))
        return job, attempt

    async def qa_boundary(self, phase=None):
        job, attempt = self.prepare_repository_qa()
        export, tool, frozen = qa_source.export, ordinary.tool, ordinary.frozen_file
        held = False
        command_reads = []
        def read(*args, **kwargs):
            path = Path(args[1])
            if 'qa-source' in path.parts and path.name in {'owned-command', 'owned-readback'}:
                command_reads.append(str(path))
                if held:self.fail('exported executable body acquired after source hold')
            return frozen(*args, **kwargs)
        async def exported(*args, **kwargs):
            nonlocal held
            answer = await export(*args, **kwargs)
            if phase == 'export':
                self.hold(self.member_id(job)); held = True
            return answer
        async def collected(store, key, label, *args, **kwargs):
            nonlocal held
            answer = await tool(store, key, label, *args, **kwargs)
            if phase == 'runner' and label == 'qa-runner':
                self.hold(self.member_id(job)); held = True
            return answer
        with patch.object(qa_source, 'export', side_effect=exported), \
                patch.object(ordinary, 'tool', side_effect=collected), \
                patch.object(ordinary, 'frozen_file', side_effect=read):
            if phase:
                with self.assertRaisesRegex(Refusal, 'admission changed'):
                    await ordinary.perform(self.store, self.boards['QA'], job)
            else:
                self.assertTrue(await ordinary.perform(self.store, self.boards['QA'], job))
        records = [json.loads(r['record']) for r in self.store.rows('SELECT record FROM ordinary_tool_records ORDER BY seq')]
        runners = [r for r in records if r['label'] == 'qa-runner' and r['exit'] is not None]
        readbacks = [r for r in records if r['label'] == 'qa-effect-resource-readback']
        if phase:
            self.assertTrue(held)
            self.assertFalse(readbacks)
            self.assertEqual(self.store.job(job['id'])['effects'], 'unknown')
            self.assertTrue(self.store.rows('SELECT * FROM ordinary_resources'))
        if phase == 'export':
            self.assertFalse(command_reads)
            self.assertFalse(runners)
        else:
            self.assertEqual(len(runners), 1)
            self.assertEqual(runners[0]['exit'], 0)
            self.assertTrue(runners[0]['complete'])
            self.assertIn('ended', runners[0])
            self.assertEqual((self.area/'qa-output/actual-run.txt').read_text(), 'actually executed')
        if phase is None:
            self.assertTrue(readbacks)
            self.assertEqual(self.store.job(job['id'])['effects'], 'reconciled')
            self.assertTrue(command_reads)

    async def test_export_hold_precedes_repository_executable_preparation(self):
        await self.qa_boundary('export')

    async def test_runner_collection_hold_precedes_readback_body_preparation(self):
        await self.qa_boundary('runner')

    async def test_unheld_repository_executables_run_and_read_back(self):
        await self.qa_boundary()

    async def test_direct_acceptance_held_entry_refuses_before_run_and_attempt_bodies(self):
        job, attempt = self.admitted_refs()
        await ordinary.perform(self.store, self.boards['Branch'], job)
        evidence = self.evidence(job)
        self.hold(self.member_id(job))
        one = self.store.one
        def metadata(sql, *args):
            if sql.startswith('SELECT * FROM ordinary_runs'):
                self.fail('full acceptance run acquired before held-entry admission')
            return one(sql, *args)
        with patch.object(self.store, 'one', side_effect=metadata), \
                patch.object(self.store, 'attempt', side_effect=AssertionError('attempt body before admission')):
            with self.assertRaisesRegex(Refusal, 'admission changed'):
                await ordinary.accept(self.store, self.acceptor, attempt, 'accepted', evidence)
        self.assertEqual(self.store.rows('SELECT * FROM ordinary_acceptance'), [])
        self.hold(self.member_id(job), None)
        await ordinary.accept(self.store, self.acceptor, attempt, 'accepted', evidence)
        self.assertTrue(ordinary.accepted_package(self.store, 'package'))

    async def test_final_acceptance_readback_hold_refuses_semantic_insert_then_unheld_accepts(self):
        job, attempt = self.admitted_refs()
        await ordinary.perform(self.store, self.boards['Branch'], job)
        evidence = self.evidence(job)
        git = ordinary.git
        async def final_readback(store, key, policy, *args):
            answer = await git(store, key, policy, *args)
            if args == ('rev-parse', '--verify', policy['ref']+'^{commit}'):
                self.hold(self.member_id(job))
            return answer
        with patch.object(ordinary, 'git', side_effect=final_readback):
            with self.assertRaisesRegex(Refusal, 'admission changed'):
                await ordinary.accept(self.store, self.acceptor, attempt, 'accepted', evidence)
        self.assertEqual(self.store.rows('SELECT * FROM ordinary_acceptance'), [])
        last = json.loads(self.store.rows('SELECT record FROM ordinary_tool_records ORDER BY seq')[-1]['record'])
        self.assertEqual(last['exit'], 0)
        self.assertTrue(last['complete'])
        self.hold(self.member_id(job), None)
        await ordinary.accept(self.store, self.acceptor, attempt, 'accepted', evidence)
        self.assertTrue(ordinary.accepted_package(self.store, 'package'))


class RecipientBoundary(Acceptance):
    async def test_qualification_recipient_hold_after_common_dir_precedes_path_metadata(self):
        await self.waiting()
        git, scoped = ordinary.git, ordinary.scoped_path
        task, policy = ordinary.policy_for(self.store, self.effect_job)
        held = False
        async def common(store, key, p, *args):
            nonlocal held
            answer = await git(store, key, p, *args)
            if args == ('rev-parse', '--path-format=absolute', '--git-common-dir'):
                self.hold(self.member()); held = True
            return answer
        def path(*args, **kwargs):
            if held:self.fail('recipient hold preceded new common-directory path metadata')
            return scoped(*args, **kwargs)
        with patch.object(ordinary, 'git', side_effect=common), patch.object(ordinary, 'scoped_path', side_effect=path):
            with self.assertRaisesRegex(Refusal, 'admission changed'):
                await ordinary.source(self.store, self.effect_attempt, policy, task, context_job=self.job)
        self.assertTrue(held)
        self.assertEqual(self.store.rows('SELECT * FROM ordinary_acceptance WHERE attempt=?', (self.attempt,)), [])
