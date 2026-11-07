"""Owned in-memory QA/Branch fiction at the real pre-effect/cleanup gates.

No filesystem, Board, provider or effect is used. Source/member pins, collected
JSON parsing, selected sequence, accepted-run joins and accepted-report checks
are real. Current resource/source observation, software processing and grants
are explicit seams; Branch stops at current_basis before any intent or tool.
"""
import copy
import json
import sqlite3
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, patch

from coordinator_runtime import ordinary, report_scope, resource_scopes
from coordinator_runtime.contracts import QA_BRANCH_SEQUENCE, Refusal, digest, encode


class BeforeIntent(Exception):
    pass


class ConservationCases:
    def setUp(self):
        self.db = sqlite3.connect(':memory:')
        self.db.row_factory = sqlite3.Row
        self.addCleanup(self.db.close)
        self.db.executescript('''
            CREATE TABLE admissions(package TEXT, receipt TEXT);
            CREATE TABLE jobs(id TEXT, task TEXT, package TEXT, active_attempt TEXT, effects TEXT);
            CREATE TABLE ordinary_runs(attempt TEXT, job TEXT, admission TEXT, state TEXT, policy TEXT, receipt TEXT);
            CREATE TABLE ordinary_acceptance(attempt TEXT, decision TEXT, receipt TEXT);
            CREATE TABLE events(id TEXT, hold INTEGER, hash TEXT);
        ''')
        tasks = {}
        for name, role, phase, effects, category, destination in (
                ('qa-execution', 'QA', 'execution', 'owner-reconcile', 'consolidated', 'branch-integrator'),
                ('branch-integrator', 'Branch', 'integrator', 'owner-reconcile', 'complete', 'qa-cleanup'),
                ('qa-cleanup', 'QA', 'cleanup', 'owned-artifacts', 'qualification', 'work-proposer')):
            tasks[name] = dict(role=role, phase=phase, effects=effects, require_package_scope=True,
                responses={category: [destination]}, effect_authority=dict(operations=['read-reports']))
        tasks['qa-execution']['effect_authority']['operations'] = ['execute-admitted-qa']
        tasks['qa-cleanup']['package_narrowing'] = True
        tasks['work-proposer'] = dict(role='Work')
        self.config = dict(qa_branch_sequence=QA_BRANCH_SEQUENCE, tasks=tasks)
        self.policies = {name: dict(kind=kind, repository='fictional-repository719',
            source_ref='refs/heads/fiction719', source_head='a'*40)
            for name, kind in [('qa-execution', 'local-qa'), ('branch-integrator', 'local-ref')]}
        receipt = encode(dict(task_scopes={name: dict(ordinary_effects=p) for name, p in self.policies.items()}))
        self.db.execute('INSERT INTO admissions VALUES(?,?)', ('package719', receipt))
        self.admission = receipt
        self.jobs, self.attempts, self.events = {}, {}, {}
        self.current = True
        self.runtime = SimpleNamespace(config=self.config, controller='fictional-controller719',
            one=self.one, rows=self.rows, job=lambda key: self.jobs[key],
            attempt=lambda key: self.attempts[key], event=lambda key: json.loads(self.events[key]),
            require_execution_open=Mock(), enrollment=lambda role: dict(owner='fictional-QA719'),
            processing=SimpleNamespace(event=lambda event: self.current))
        self.board = SimpleNamespace(_software_job_grant=Mock())
        self.selected = self.enterContext(patch.object(ordinary, 'selected', return_value=dict(id='epoch719')))
        self.policy = self.enterContext(patch.object(ordinary, 'policy_for',
            side_effect=lambda runtime, job: ({}, copy.deepcopy(self.policies[job['task']]))))
        self.enterContext(patch('coordinator_runtime.prospective.board', return_value=self.board))
        self.processing = self.enterContext(patch('coordinator_runtime.software.clean_processing', return_value=True))
        self.source = self.enterContext(patch.object(ordinary, 'accepted_source_current'))
        self.qa_source = self.enterContext(patch('coordinator_runtime.qa_source.verify'))
        self.epoch = self.enterContext(patch('coordinator_runtime.prospective.current',
            return_value=dict(policy=dict(ordinary_effects=False))))
        self.enterContext(patch.object(resource_scopes, 'qa_operation', return_value='original-hold719'))
        self.enterContext(patch.object(resource_scopes, 'scope_excluded', return_value=False))
        self.cleanup_scope = dict(procedure='fictional-procedure719', read_roots=[])
        self.account = dict(cleanup=dict(scope=self.cleanup_scope, procedure_sha256='b'*64))
        self.enterContext(patch.object(resource_scopes, 'scoped_task', return_value=dict(
            admitted_scope=self.cleanup_scope, network=False, effect_authority=dict(
                owner='fictional-QA719', operations=['read-reports', 'consolidate-reports']))))
        self.file = self.enterContext(patch.object(ordinary, 'frozen_file'))
        self.enterContext(patch.object(resource_scopes, 'blocked', return_value=False))
        self.adapter = self.enterContext(patch.object(ordinary, 'adapter', new_callable=AsyncMock))
        self.tool_source = self.enterContext(patch.object(ordinary, 'source', new_callable=AsyncMock))
        self.qa = self.job('qa-execution', [])
        qa_answer = self.answer('consolidated', [dict(history='Whole original fictional history',
            metadata=dict(method='fictional HIGH', actual_END=0, native=False),
            reports=[dict(name='Source', body='Whole dissent Ω'), dict(name='Followup', body='Still partial')],
            coverage=dict(status='PARTIAL', unread=['family719'], dissent=[dict(author='reviewer', text='Retain unknown')],
                nested=[dict(disabled=False, enabled=True, zero=0, one=1, real=1.0,
                    negative_zero=-0.0, missing=None, text='0', array=[], object={})]))])
        self.collected(self.qa, qa_answer)
        self.accepted(self.qa)
        qa_event = self.event(self.qa, qa_answer, 'branch-integrator')
        # The expected copied envelope is specified independently of conserved_inputs.
        self.envelope = [dict(event=qa_event['id'], sha256=digest(qa_event), original=copy.deepcopy(qa_answer))]
        self.qa_bytes = self.events[qa_event['id']]
        self.branch = self.job('branch-integrator', [dict(event=qa_event['id'], hash=digest(qa_event))])
        self.cleanup = self.job('qa-cleanup', [])

    def one(self, sql, params=()):
        row = self.db.execute(sql, params).fetchone()
        return dict(row) if row else None

    def rows(self, sql, params=()):
        return [dict(row) for row in self.db.execute(sql, params)]

    def job(self, task, members):
        name = task+'719'
        job = dict(id=name, task=task, role=self.config['tasks'][task]['role'],
            phase=self.config['tasks'][task]['phase'], package='package719', active_attempt=name+'-attempt',
            effects='reconciled', hold_reason=None, members=encode(members), response=None)
        self.jobs[name] = job
        self.db.execute('INSERT INTO jobs VALUES(?,?,?,?,?)',
            (name, task, job['package'], job['active_attempt'], job['effects']))
        return job

    @staticmethod
    def answer(category, findings):
        return dict(semantic='DONE', category=category, summary='Owned whole report fiction719',
            findings=findings, failures=[], unknowns=[], artifacts=[])

    def collected(self, job, answer):
        self.attempts[job['active_attempt']] = dict(id=job['active_attempt'],
            controller=self.runtime.controller, session='fictional-worker719', result=encode(answer),
            detail=encode(dict(tool_completion=dict(complete=True, items=[], nonzero_completions=[]))),
            exit=0, capture='complete', begin=1, ended=2, collected=3, error=None)

    def accepted(self, job):
        receipt = encode(dict(outcome=dict(status='success', source_execution=dict(method='git-blobs-readonly-namespace-v1'))))
        self.db.execute('DELETE FROM ordinary_runs WHERE job=?', (job['id'],))
        self.db.execute('DELETE FROM ordinary_acceptance WHERE attempt=?', (job['active_attempt'],))
        self.db.execute('INSERT INTO ordinary_runs VALUES(?,?,?,?,?,?)', (job['active_attempt'], job['id'],
            digest(self.admission), 'reconciled', encode(self.policies[job['task']]), receipt))
        self.db.execute('INSERT INTO ordinary_acceptance VALUES(?,?,?)', (job['active_attempt'], 'accepted',
            encode(dict(execution_hash=digest(json.loads(receipt))))))

    def event(self, job, answer, destination):
        event = dict(id=digest(dict(response=job['active_attempt'])), source_job=job['id'],
            source_attempt=job['active_attempt'], source_role=job['role'], source_members=json.loads(job['members']),
            package=job['package'], body=copy.deepcopy(answer), allowed_tasks=[destination])
        job['response'] = event['id']
        self.events[event['id']] = encode(event)
        self.db.execute('DELETE FROM events WHERE id=?', (event['id'],))
        self.db.execute('INSERT INTO events VALUES(?,?,?)', (event['id'], 0, digest(event)))
        return event

    def branch_report(self, findings):
        answer = self.answer('complete', findings)
        self.collected(self.branch, answer)
        self.accepted(self.branch)
        event = self.event(self.branch, answer, 'qa-cleanup')
        self.cleanup['members'] = encode([dict(event=event['id'], hash=digest(event))])
        return event

    def tearDown(self):
        self.assertEqual(self.events[self.envelope[0]['event']], self.qa_bytes)
        self.adapter.assert_not_called()
        self.tool_source.assert_not_called()

    async def test_nested_whole_envelope_with_separate_analysis(self):
        await self.validate([dict(analysis='Additional analysis keeps original dissent'),
                             dict(collected_reports=copy.deepcopy(self.envelope))])

    async def test_boolean_integer_and_float_substitutions(self):
        for key, value in [('disabled', 0), ('enabled', 1), ('zero', False), ('one', True),
                           ('one', 1.0), ('real', 1), ('negative_zero', 0.0)]:
            with self.subTest(key=key, value=value):
                changed = copy.deepcopy(self.envelope)
                changed[0]['original']['findings'][0]['coverage']['nested'][0][key] = value
                with self.assertRaisesRegex(Refusal, 'whole.*QA report'):
                    await self.validate([dict(collected_reports=changed)])

    async def test_whole_metadata_history_dissent_and_arrays(self):
        mutations = [lambda e: e.clear(), lambda e: e.append(copy.deepcopy(e[0])),
            lambda e: e[0].update(sha256='0'*64), lambda e: e[0].pop('event'),
            lambda e: e[0].update(extra='unselected metadata'),
            lambda e: e[0]['original']['findings'][0].pop('history'),
            lambda e: e[0]['original']['findings'][0]['metadata'].update(native=0),
            lambda e: e[0]['original']['findings'][0]['metadata'].update(actual_END=False),
            lambda e: e[0]['original']['findings'][0]['coverage']['dissent'].clear(),
            lambda e: e[0]['original']['findings'][0]['reports'].reverse(),
            lambda e: e[0]['original']['findings'][0]['reports'][0].update(body='Summary replaces dissent')]
        for index, mutate in enumerate(mutations):
            with self.subTest(mutation=index):
                changed = copy.deepcopy(self.envelope)
                mutate(changed)
                with self.assertRaises(Refusal):
                    await self.validate([dict(collected_reports=changed)])
        for findings in [[], [dict(collected_reports=self.envelope, extra='wrapper')],
                         [dict(collected_reports=self.envelope[0])], [dict(summary='Incomplete wrapper')]]:
            with self.subTest(findings=findings):
                with self.assertRaises(Refusal):
                    await self.validate(findings)

    async def test_nested_scalar_container_and_depth_identity(self):
        for key, value in [('missing', False), ('text', 0), ('array', {}), ('object', []),
                           ('zero', '0'), ('array', [[]]), ('object', dict(extra={}))]:
            with self.subTest(key=key, value=value):
                changed = copy.deepcopy(self.envelope)
                changed[0]['original']['findings'][0]['coverage']['nested'][0][key] = value
                with self.assertRaises(Refusal):
                    await self.validate([dict(collected_reports=changed)])

    async def test_canonical_key_order_and_numeric_lexical_semantics(self):
        def reverse(value):
            if isinstance(value, dict): return {key: reverse(value[key]) for key in reversed(value)}
            if isinstance(value, list): return [reverse(item) for item in value]
            return value
        raw = json.dumps(reverse(self.envelope), indent=2, ensure_ascii=False)
        raw = raw.replace('"real": 1.0', '"real": 1e0').replace('"zero": 0', '"zero": -0')
        await self.validate([dict(collected_reports=json.loads(raw))])

    async def test_changed_member_pin_and_current_authority(self):
        self.db.execute('UPDATE events SET hold=1 WHERE id=?', (self.envelope[0]['event'],))
        with self.assertRaisesRegex(Refusal, 'held, changed or outside current authority'):
            await self.validate([dict(collected_reports=self.envelope)])
        self.db.execute('UPDATE events SET hold=0')
        self.current = False
        with self.assertRaisesRegex(Refusal, 'held, changed or outside current authority'):
            await self.validate([dict(collected_reports=self.envelope)])
        self.current = True
        source = json.loads(self.qa_bytes)
        source['body']['summary'] = 'Changed pinned original'
        self.events[source['id']] = encode(source)
        try:
            with self.assertRaisesRegex(Refusal, 'original whole report member changed'):
                await self.validate([dict(collected_reports=self.envelope)])
        finally:
            self.events[source['id']] = self.qa_bytes


class BranchBeforeEffects719(ConservationCases, unittest.IsolatedAsyncioTestCase):
    async def validate(self, findings):
        self.collected(self.branch, self.answer('complete', findings))
        with patch('coordinator_runtime.local_integration.current_basis', side_effect=BeforeIntent):
            with self.assertRaises(BeforeIntent):
                await ordinary.perform(self.runtime, self.board, self.branch)
        self.assertEqual(len(self.rows('SELECT * FROM ordinary_runs')), 1)


class Cleanup719(ConservationCases, unittest.IsolatedAsyncioTestCase):
    async def validate(self, findings):
        self.branch_report(findings)
        self.assertEqual(resource_scopes.qa_cleanup(self.runtime, self.cleanup, {}, self.account), 'original-hold719')

    async def test_accepted_branch_report_body_preserves_types_against_collected_original(self):
        for key, value in [('disabled', 0), ('enabled', 1), ('one', 1.0), ('real', 1)]:
            with self.subTest(key=key):
                event = self.branch_report([dict(collected_reports=copy.deepcopy(self.envelope))])
                event['body']['findings'][0]['collected_reports'][0]['original']['findings'][0]['coverage']['nested'][0][key] = value
                # Even coherent downstream event/member pins cannot replace the
                # separately collected, independently accepted Branch original.
                self.events[event['id']] = encode(event)
                self.db.execute('UPDATE events SET hash=? WHERE id=?', (digest(event), event['id']))
                self.cleanup['members'] = encode([dict(event=event['id'], hash=digest(event))])
                with self.assertRaisesRegex(Refusal, 'exact whole collected accepted dependency report'):
                    resource_scopes.qa_cleanup(self.runtime, self.cleanup, {}, self.account)

    async def test_independent_acceptance_policy_source_and_sequence_remain_required(self):
        self.branch_report([dict(collected_reports=self.envelope)])
        attempt = self.branch['active_attempt']
        self.db.execute('DELETE FROM ordinary_acceptance WHERE attempt=?', (attempt,))
        with self.assertRaisesRegex(Refusal, 'all admitted ordinary results'):
            resource_scopes.qa_cleanup(self.runtime, self.cleanup, {}, self.account)
        self.accepted(self.branch)
        self.policy.side_effect = lambda runtime, job: ({}, dict(self.policies[job['task']], source_head='c'*40))
        with self.assertRaisesRegex(Refusal, 'accepted Branch policy changed'):
            resource_scopes.qa_cleanup(self.runtime, self.cleanup, {}, self.account)
        self.policy.side_effect = lambda runtime, job: ({}, copy.deepcopy(self.policies[job['task']]))
        self.source.side_effect = Refusal('fictional stale accepted source')
        with self.assertRaisesRegex(Refusal, 'stale accepted source'):
            resource_scopes.qa_cleanup(self.runtime, self.cleanup, {}, self.account)
        self.source.side_effect = None
        self.epoch.return_value = dict(policy=dict(ordinary_effects='admitted-v1'))
        with self.assertRaisesRegex(Refusal, 'current no-effect consolidation authority'):
            resource_scopes.qa_cleanup(self.runtime, self.cleanup, {}, self.account)
        self.epoch.return_value = dict(policy=dict(ordinary_effects=False))
        self.config['tasks']['qa-execution']['responses']['consolidated'] = ['qa-cleanup']
        with self.assertRaises(Refusal):
            resource_scopes.qa_cleanup(self.runtime, self.cleanup, {}, self.account)

    async def test_typed_qa_handoff_requires_exact_body_and_independent_acceptance(self):
        run = ordinary.accepted_runs(self.runtime, 'package719', ['qa-execution'])[0]
        event = json.loads(self.qa_bytes)
        self.assertEqual(ordinary.accepted_report(self.runtime, event, run, 'branch-integrator'), event['body'])
        changed = copy.deepcopy(event)
        changed['body']['findings'][0]['metadata']['native'] = 0
        with self.assertRaisesRegex(Refusal, 'exact whole collected accepted dependency report'):
            ordinary.accepted_report(self.runtime, changed, run, 'branch-integrator')
        self.db.execute('DELETE FROM ordinary_acceptance WHERE attempt=?', (self.qa['active_attempt'],))
        with self.assertRaises(Refusal):
            ordinary.accepted_report(self.runtime, event, run, 'branch-integrator')


if __name__ == '__main__':
    unittest.main()
