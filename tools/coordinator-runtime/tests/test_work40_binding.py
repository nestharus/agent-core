"""Decision40 outcome regressions; real tools, explicitly fictional authority."""
import asyncio
import json
import subprocess
from unittest.mock import patch

from test_ordinary_effects import OrdinaryEffects, sha
from support import event, queued, result
from coordinator_runtime import ordinary
from coordinator_runtime.contracts import Refusal, digest, encode


class Work40Binding(OrdinaryEffects):
    async def _handoff(self, *, scanner_first=False, count=1):
        # No software_delegation config migration in this continuing journal.
        self.assertNotIn('software_delegation', self.config)
        task = self.config['tasks']['branch-integrator']
        # Authority is selected BEFORE the future event exists.
        task['allowed_handoffs'] = ['QA']
        task['effects'] = 'none'
        tasks = ['branch-integrator', 'qa-execution']
        from coordinator_runtime import prospective
        selection = {'configuration': digest(self.config), 'authority': 'Fictional Work40 handoff',
            'expires': self.now + 100,
            'grants': {r: self.store.enrollment(r)['grant_id'] for r in ['Branch', 'QA']},
            'tasks': {t: {'task_hash': digest(self.config['tasks'][t]),
                'software_handoffs': {'QA': ['qa-execution']} if t == 'branch-integrator' else {},
                'ordinary_effects': False} for t in tasks}}
        prospective.select(self.store, self.config['roles']['Work']['owner'], selection)
        self.admission()
        answer = result()
        answer['handoffs'] = [{'recipient': 'QA', 'kind': 'work', 'text': 'one actual candidate handoff', 'ref': 'package', 'required': 'settled'} for _ in range(count)]
        job, attempt = self.prepared(answer=answer)
        # This fixture has no business effects, only one locally collected handoff.
        with self.store.tx():
            self.store.db.execute("UPDATE jobs SET effects='none' WHERE id=?", (job['id'],))
        self.store.finish_job(job['id'], job['token'])
        outboxes = self.store.rows("SELECT * FROM outboxes WHERE job=? AND kind='work'", (job['id'],))
        self.assertEqual(len(outboxes), count)
        board = self.boards['Branch']
        for outbox in outboxes:
            with patch.object(board.store.active_listener, 'signal_post', return_value=None):
                board.post_delivery(self.store, outbox)
        scanner = self.boards['QA'].scan(self.store) if scanner_first else []
        for outbox in outboxes:
            self.assertTrue(board.software_delivery(self.store, outbox, self.boards))
        scanner += self.boards['QA'].scan(self.store)
        for item in scanner:
            self.store.ingest(item)
        while True:
            claimed = self.store.claim_classification()
            if not claimed: break
            a, item = claimed
            from support import collect
            collect(self.store, a, {'event_id': item['id'], 'task': item['allowed_tasks'][0], 'package': item['package'], 'reason': 'fictional QA handoff'})
            self.store.commit_classification(a)
            self.store.ack_state(item['id'], 'internal')
            if not self.store.one("SELECT id FROM events WHERE classification IS NULL"): break
        actual = len(self.store.rows("SELECT * FROM queue WHERE task='qa-execution'"))
        (self.area / 'handoff-result.json').write_text(encode({'queue_count': actual, 'scan': scanner}))
        self.assertEqual(actual, count, 'one actual post must not acquire two QA responsibilities')

    async def test_same_journal_handoff_has_one_responsibility(self):
        await self._handoff()

    async def test_scanner_first_handoff_has_one_responsibility(self):
        await self._handoff(scanner_first=True)

    async def test_distinct_identical_handoffs_retain_two_responsibilities(self):
        await self._handoff(scanner_first=True, count=2)

    async def test_old_checkout_PASS_candidate_FAIL_cannot_qualify(self):
        self.boundary()
        self.admission(kind='local-qa')
        scope = json.loads(self.store.one('SELECT receipt FROM admissions WHERE package=?', ('package',))['receipt'])
        p = scope['task_scopes']['qa-execution']['ordinary_effects']
        runner = self.area / 'runner'
        runner.write_text('#!/usr/bin/python3\nfrom pathlib import Path\nassert Path("source.txt").read_text() == "first\\n", "candidate behavior fails independent requirement"\nPath('+repr(str(self.area / 'qa-output/actual-run.txt'))+').write_text("actually executed")\n')
        p['command']['executable_sha256'] = sha(runner)
        self.store.admit('package', self.config['roles']['Branch']['owner'], scope)
        self.git('switch', '--detach', self.old)
        # Actual old-checkout execution PASS; the same executable at candidate FAIL.
        old = subprocess.run([str(runner)], cwd=self.repo, capture_output=True, text=True)
        self.git('switch', '--detach', self.head)
        candidate = subprocess.run([str(runner)], cwd=self.repo, capture_output=True, text=True)
        self.git('switch', '--detach', self.old)
        (self.area / 'independent-ends.json').write_text(encode({'old': {'end': old.returncode, 'stderr': old.stderr}, 'candidate': {'end': candidate.returncode, 'stderr': candidate.stderr}}))
        self.assertEqual(old.returncode, 0)
        self.assertEqual(candidate.returncode, 1)
        job, attempt = self.prepared(role='QA')
        await ordinary.perform(self.store, self.boards['QA'], job)
        receipt = json.loads(self.store.job(job['id'])['effect_receipt'])
        evidence = {'execution_hash': digest(receipt), 'rationale': 'Independent fixture behavior requirement', 'unknowns': []}
        if receipt['outcome']['status'] == 'success':
            await ordinary.accept(self.store, self.acceptor, attempt, 'accepted', evidence)
            await ordinary.qualification(self.store, self._cleanup())
        (self.area / 'association-result.json').write_text(encode({'receipt': receipt, 'accepted': ordinary.accepted_package(self.store, 'package'), 'qualified': ordinary.qualification_current(self.store, self.store.job(job['id']))}))
        self.assertFalse(ordinary.accepted_package(self.store, 'package'), 'old checkout PASS must not accept the failing candidate')
        self.assertEqual(receipt['outcome']['actual_exit'], 1)
        with self.assertRaises(Refusal):
            await ordinary.qualification(self.store, self._cleanup())

    async def test_overflow_keeps_actual_terminal_END_and_holds(self):
        self.boundary()
        self.admission(kind='local-qa')
        receipt = json.loads(self.store.one('SELECT receipt FROM admissions WHERE package=?', ('package',))['receipt'])
        p = receipt['task_scopes']['qa-execution']['ordinary_effects']
        runner = self.area / 'runner'
        runner.write_text('#!/usr/bin/python3\nimport os\nos.write(1,b"x"*40000)\n')
        p['command']['executable_sha256'] = sha(runner)
        self.store.admit('package', self.config['roles']['Branch']['owner'], receipt)
        job, attempt = self.prepared(role='QA')
        with self.assertRaises(Refusal):
            await ordinary.perform(self.store, self.boards['QA'], job)
        records = [json.loads(r['record']) for r in self.store.rows('SELECT record FROM ordinary_tool_records WHERE attempt=? ORDER BY seq', (attempt,))]
        ends = [r for r in records if r['label']=='qa-runner' and r.get('ended') is not None]
        self.assertEqual(len(ends), 1)
        self.assertIsInstance(ends[0]['exit'], int)
        self.assertFalse(ends[0]['complete'])
        self.assertEqual(len(self.store.rows('SELECT * FROM ordinary_resources')), 1)
        with self.assertRaises(Refusal):
            await ordinary.perform(self.store, self.boards['QA'], job)

    def _cleanup(self):
        queued(self.store, event(self.config, 'separately selected cleanup', 'QA', 'qa-cleanup', 'package'))
        job = self.store.reserve()
        self.assertIsNotNone(job)
        self.assertEqual(job['phase'], 'cleanup')
        attempt = self.store.start_job(job['id'], job['token'])
        job = self.store.job(job['id'])
        self.boards['QA'].bind_software_attempt(self.store, job, attempt,
            self.store.one('SELECT * FROM admissions WHERE package=?', ('package',)))
        return job

    async def _accepted_candidate(self):
        self.boundary()
        self.admission(kind='local-qa')
        # A separate harness and an old/dirty checkout remain usable: execution
        # consumes exported candidate bytes, not the checkout or its junk.
        self.git('switch', '--detach', self.old)
        (self.repo / 'source.txt').write_text('dirty old checkout\n')
        runner = self.area / 'runner'
        runner.write_text('#!/usr/bin/python3\nfrom pathlib import Path\nassert Path("source.txt").read_text() == "second\\n"\nassert not Path(".git").exists()\ntry:\n Path("source.txt").write_text("changed")\nexcept OSError:\n pass\nelse:\n raise AssertionError("candidate writable")\nPath('+repr(str(self.area / 'qa-output/actual-run.txt'))+').write_text("actually executed")\n')
        admission = json.loads(self.store.one('SELECT receipt FROM admissions WHERE package=?', ('package',))['receipt'])
        admission['task_scopes']['qa-execution']['ordinary_effects']['command']['executable_sha256'] = sha(runner)
        self.store.admit('package', self.config['roles']['Branch']['owner'], admission)
        job, attempt = self.prepared(role='QA')
        await ordinary.perform(self.store, self.boards['QA'], job)
        receipt = json.loads(self.store.job(job['id'])['effect_receipt'])
        self.assertEqual(receipt['outcome']['actual_exit'], 0)
        self.assertEqual((self.repo / 'source.txt').read_text(), 'dirty old checkout\n')
        return job, attempt, receipt

    async def test_candidate_bytes_separate_harness_acceptance_and_qualification(self):
        job, attempt, receipt = await self._accepted_candidate()
        await ordinary.accept(self.store, self.acceptor, attempt, 'accepted',
            {'execution_hash': digest(receipt), 'rationale': 'Independent candidate behavior and readonly assertion executed', 'unknowns': []})
        cleanup = self._cleanup()
        await ordinary.qualification(self.store, cleanup)
        self.assertTrue(ordinary.qualification_current(self.store, cleanup))
        self.assertEqual(len(self.store.rows('SELECT * FROM ordinary_resources')), 0)

    async def test_acceptance_refuses_changed_candidate_evidence(self):
        job, attempt, receipt = await self._accepted_candidate()
        from pathlib import Path
        Path(receipt['outcome']['source_execution']['root'], 'source.txt').write_text('changed evidence\n')
        with self.assertRaises(Refusal):
            await ordinary.accept(self.store, self.acceptor, attempt, 'accepted',
                {'execution_hash': digest(receipt), 'rationale': 'candidate evidence changed', 'unknowns': []})
        self.assertFalse(ordinary.accepted_package(self.store, 'package'))

    async def test_qualification_refuses_changed_candidate_evidence(self):
        job, attempt, receipt = await self._accepted_candidate()
        await ordinary.accept(self.store, self.acceptor, attempt, 'accepted',
            {'execution_hash': digest(receipt), 'rationale': 'independent candidate acceptance', 'unknowns': []})
        cleanup = self._cleanup()
        await ordinary.qualification(self.store, cleanup)
        from pathlib import Path
        Path(receipt['outcome']['source_execution']['root'], 'source.txt').write_text('changed after acceptance\n')
        with self.assertRaises(Refusal):
            await ordinary.qualification(self.store, cleanup)
        self.assertFalse(ordinary.qualification_current(self.store, cleanup))

    async def test_decode_error_keeps_observed_END_and_incomplete_capture(self):
        self.boundary()
        self.admission(kind='local-qa')
        admission = json.loads(self.store.one('SELECT receipt FROM admissions WHERE package=?', ('package',))['receipt'])
        runner = self.area / 'runner'
        runner.write_text('#!/usr/bin/python3\nimport os\nos.write(1,bytes([255]))\n')
        admission['task_scopes']['qa-execution']['ordinary_effects']['command']['executable_sha256'] = sha(runner)
        self.store.admit('package', self.config['roles']['Branch']['owner'], admission)
        job, attempt = self.prepared(role='QA')
        with self.assertRaises(Refusal):
            await ordinary.perform(self.store, self.boards['QA'], job)
        records = [json.loads(r['record']) for r in self.store.rows('SELECT record FROM ordinary_tool_records WHERE attempt=?', (attempt,))]
        end = [r for r in records if r['label']=='qa-runner' and r.get('ended') is not None]
        self.assertEqual(len(end), 1)
        self.assertEqual(end[0]['exit'], 0)
        self.assertFalse(end[0]['complete'])
        self.assertEqual(len(self.store.rows('SELECT * FROM ordinary_resources')), 1)


    async def test_candidate_cannot_substitute_unadmitted_harness_bytes(self):
        runner = self.repo / 'inside-runner'
        runner.write_text('#!/usr/bin/python3\nraise SystemExit(1)\n')
        runner.chmod(0o755)
        self.git('add', 'inside-runner')
        self.git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', '-c', 'commit.gpgsign=false', 'commit', '-m', 'fixture candidate harness')
        self.head = self.git('rev-parse', 'HEAD')
        self.boundary()
        self.admission(kind='local-qa')
        # Admitted executable bytes in a dirty checkout must not silently turn
        # into different executable bytes under the candidate mount.
        runner.write_text('#!/usr/bin/python3\nraise SystemExit(0)\n')
        admission = json.loads(self.store.one('SELECT receipt FROM admissions WHERE package=?', ('package',))['receipt'])
        admission['task_scopes']['qa-execution']['ordinary_effects']['command'].update(argv=[str(runner)], executable_sha256=sha(runner))
        self.store.admit('package', self.config['roles']['Branch']['owner'], admission)
        job, attempt = self.prepared(role='QA')
        with self.assertRaises(Refusal):
            await ordinary.perform(self.store, self.boards['QA'], job)
        records = [json.loads(r['record']) for r in self.store.rows('SELECT record FROM ordinary_tool_records WHERE attempt=?', (attempt,))]
        self.assertFalse(any(r['label']=='qa-runner' for r in records))
        self.assertEqual(len(self.store.rows('SELECT * FROM ordinary_resources')), 1)


def load_tests(loader, tests, pattern):
    import unittest
    return unittest.TestSuite(Work40Binding(name) for name in Work40Binding.__dict__ if name.startswith('test_'))
