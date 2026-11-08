"""Prospective preparation contract, exact supplied refusal and owned effects.

The supplied report is never repaired or used as new execution authority. New
contract-conforming answers below are model seams, not native/model efficacy.
Only this test's retained synthetic boards, Git repo and QA output are changed.
"""
import copy
import json
import os
from pathlib import Path
import unittest

from support import collect, event, queued, result
from test_ordinary_effects import OrdinaryEffects
from coordinator_runtime import ordinary, prospective
from coordinator_runtime.contracts import Refusal, digest, encode, ident
from coordinator_runtime.dispatcher import Dispatcher


class Preparation909(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        await OrdinaryEffects.asyncSetUp(self)
        # Current source checks require an origin. Public, inert fixture metadata;
        # no fetch/push or external repository is used by these operations.
        self.git('remote', 'add', 'origin', 'https://fixture.invalid/preparation909')
    git = OrdinaryEffects.git
    boundary = OrdinaryEffects.boundary
    admission = OrdinaryEffects.admission
    prepared = OrdinaryEffects.prepared

    def supplied(self):
        # Two explicitly selected safe public inputs. No path discovery or live DB.
        root = Path(os.environ['QA_PREPARATION909_PUBLIC_INPUTS'])
        answer = json.loads((root / 'ACTUAL-QA880-PREPARATION907.json').read_bytes())
        detail = json.loads((root / 'ACTUAL-QA880-PREPARATION-DETAIL908.json').read_bytes())
        self.assertEqual(answer['semantic'], 'DONE')
        self.assertEqual(len(answer['unknowns']), 6)
        self.assertTrue(detail['tool_completion']['complete'])
        self.assertEqual(len(detail['tool_completion']['items']), 8)
        self.assertEqual(detail['tool_completion']['unknown_types'], [])
        self.assertEqual(detail['tool_completion']['nonzero_completions'], [])
        self.assertTrue(all(t['exit_code'] == 0 for t in detail['tool_completion']['items']))
        return answer, detail

    def prospective_answer(self):
        original, _ = self.supplied()
        # A distinct future model-seam result. No UPDATE/reclassification of the
        # actual original or of an already collected fixture result occurs.
        answer = result(category='consolidated', summary='New read-only preparation; service stages remain pending')
        stages = ['service-execution-readback', 'service-currentness', 'service-candidate-export',
                  'work-source-disposition', 'independent-acceptance-downstream', 'retained-obligations']
        answer['findings'] += [dict(kind='ordinary-pending-stage', stage=stage, evidence=copy.deepcopy(evidence))
                               for stage, evidence in zip(stages, original['unknowns'])]
        answer['findings'].append({'kind': 'fixture-origin', 'original_report_hash': digest(original),
                                  'meaning': 'Separate prospective response; original remains unchanged and refused'})
        return answer

    async def selected_preparation(self, answer):
        self.boundary()
        self.admission(kind='local-qa')
        return self.prepared(role='QA', answer=answer)

    async def test_exact_six_unknown_original_stays_refused_and_recoverable(self):
        original, detail = self.supplied()
        job, attempt = await self.selected_preparation(original)
        with self.store.tx():
            # Synthetic collection using actual supplied completion *shape*, not
            # attribution of those real native commands to this fixture session.
            row = json.loads(self.store.attempt(attempt)['detail'])
            row['tool_completion'] = detail['tool_completion']
            self.store.db.execute('UPDATE attempts SET detail=? WHERE id=?', (encode(row), attempt))
        before = self.store.attempt(attempt)
        with self.assertRaisesRegex(Refusal, 'known preparation required'):
            await ordinary.perform(self.store, self.boards['QA'], job)
        self.assertEqual(self.store.attempt(attempt), before)
        self.assertEqual(json.loads(before['result']), original)
        self.assertEqual(self.store.rows('SELECT * FROM ordinary_runs'), [])
        self.assertFalse((self.area / 'qa-output/actual-run.txt').exists())
        self.assertEqual(self.supplied()[0], original)

    async def test_new_preparation_preserves_all_pending_evidence_and_service_resolves_own_stages(self):
        answer = self.prospective_answer()
        job, attempt = await self.selected_preparation(answer)
        before = self.store.attempt(attempt)
        self.assertTrue(await ordinary.perform(self.store, self.boards['QA'], job))
        self.assertEqual(self.store.attempt(attempt), before)
        pending = [f['evidence'] for f in json.loads(before['result'])['findings']
                   if f.get('kind') == 'ordinary-pending-stage']
        self.assertEqual(pending, self.supplied()[0]['unknowns'])
        run = self.store.one('SELECT * FROM ordinary_runs WHERE attempt=?', (attempt,))
        receipt = json.loads(run['receipt'])
        self.assertEqual(run['state'], 'reconciled')
        self.assertEqual(receipt['before'], receipt['after'])
        self.assertEqual(receipt['outcome']['actual_exit'], 0)
        self.assertTrue(receipt['outcome']['source_execution'])
        self.assertEqual(receipt['unknown_effects'], [])
        self.assertTrue((self.area / 'qa-output/actual-run.txt').is_file())
        self.assertFalse(ordinary.accepted_package(self.store, 'package'))
        self.assertEqual(self.store.rows('SELECT * FROM ordinary_acceptance'), [])

    async def test_genuine_in_scope_unknown_still_prevents_any_intent(self):
        answer = self.prospective_answer()
        answer['unknowns'] = [{'ref': 'admitted procedure', 'text': 'Required preparation source bytes could not be read'}]
        job, _ = await self.selected_preparation(answer)
        with self.assertRaisesRegex(Refusal, 'known preparation required'):
            await ordinary.perform(self.store, self.boards['QA'], job)
        self.assertEqual(self.store.rows('SELECT * FROM ordinary_runs'), [])

    async def test_prompt_separates_preparation_unknowns_without_granting_effects(self):
        self.boundary()
        self.admission(kind='local-qa')
        queued(self.store, event(self.config, 'prompt909', 'QA', 'qa-execution', 'package'))
        job = self.store.reserve()
        attempt = self.store.start_job(job['id'], job['token'])
        runtime = Dispatcher(self.store, models=object(), boards=self.boards)
        async def model(attempt, prompt, spec, schema):
            self.assertIn('ordinary-pending-stage', prompt)
            self.assertIn('unresolved facts required for this read-only preparation', prompt)
            self.assertIn('Never reclassify or delete entries from an existing original', prompt)
            self.assertIn('pending evidence grants no authority', prompt)
            self.assertEqual(spec['sandbox'], 'read-only')
            self.assertFalse(spec['network'])
            self.assertEqual(spec['effect_authority']['write_roots'], [])
            self.store.begin(attempt, {'synthetic': 'prospective model seam'})
            self.store.session(attempt, ident())
            return {'result': self.prospective_answer(), 'exit': 0, 'capture': 'complete', 'cleanup': 'done', 'error': None,
                    'detail': {'tool_completion': {'complete': True, 'items': [], 'nonzero_completions': [], 'unknown_types': []}}}
        runtime.run_model = model
        await runtime.execute(job['id'], attempt)
        self.assertEqual(self.store.one('SELECT state FROM ordinary_runs WHERE attempt=?', (attempt,))['state'], 'reconciled')

    async def test_unknown_tool_types_cannot_hide_behind_complete_boolean(self):
        job, attempt = await self.selected_preparation(self.prospective_answer())
        with self.store.tx():
            row = json.loads(self.store.attempt(attempt)['detail'])
            row['tool_completion']['unknown_types'] = ['unclassifiedEffect']
            self.store.db.execute('UPDATE attempts SET detail=? WHERE id=?', (encode(row), attempt))
        with self.assertRaisesRegex(Refusal, 'known preparation required'):
            await ordinary.perform(self.store, self.boards['QA'], job)
        self.assertEqual(self.store.rows('SELECT * FROM ordinary_runs'), [])

    async def test_incomplete_nonzero_failed_tools_and_wrong_collector_refuse_before_intent(self):
        job, attempt = await self.selected_preparation(self.prospective_answer())
        original = self.store.attempt(attempt)
        for completion in [
                {'complete': False, 'items': [], 'nonzero_completions': []},
                {'complete': True, 'items': [], 'nonzero_completions': [{'exit_code': 1}]},
                {'complete': True, 'items': [{'status': 'failed'}], 'nonzero_completions': []}]:
            with self.subTest(completion=completion):
                detail = json.loads(original['detail'])
                detail['tool_completion'] = completion
                with self.store.tx():
                    self.store.db.execute('UPDATE attempts SET detail=? WHERE id=?', (encode(detail), attempt))
                with self.assertRaisesRegex(Refusal, 'known preparation required'):
                    await ordinary.perform(self.store, self.boards['QA'], job)
                self.assertEqual(self.store.rows('SELECT * FROM ordinary_runs'), [])
        with self.store.tx():
            self.store.db.execute('UPDATE attempts SET detail=?,controller=? WHERE id=?',
                                  (original['detail'], ident(), attempt))
        with self.assertRaises(Refusal):
            await ordinary.perform(self.store, self.boards['QA'], job)
        self.assertEqual(self.store.rows('SELECT * FROM ordinary_runs'), [])

    async def test_changed_procedure_expired_lease_and_revoked_authority_stay_refused(self):
        job, _ = await self.selected_preparation(self.prospective_answer())
        before = self.procedure.read_bytes()
        self.procedure.write_text('Changed fixture procedure')
        with self.assertRaisesRegex(Refusal, 'bytes changed'):
            await ordinary.perform(self.store, self.boards['QA'], job)
        self.procedure.write_bytes(before)
        self.now += 91
        with self.assertRaisesRegex(Refusal, 'lease required'):
            await ordinary.perform(self.store, self.boards['QA'], job)
        self.now -= 91
        epoch = ordinary.selected(self.store, job)
        prospective.revoke(self.store, self.config['roles']['Work']['owner'], epoch['id'])
        # Revocation may produce no selected adapter rather than execution;
        # either way no old permission is usable and no intent may be born.
        with self.assertRaises(Refusal):
            await ordinary.perform(self.store, self.boards['QA'], job)
        self.assertEqual(self.store.rows('SELECT * FROM ordinary_runs'), [])

    async def test_changed_source_retains_unknown_intent_and_never_replays(self):
        job, attempt = await self.selected_preparation(self.prospective_answer())
        self.git('update-ref', 'refs/heads/source', self.old, self.head)
        with self.assertRaisesRegex(Refusal, 'source ref is stale'):
            await ordinary.perform(self.store, self.boards['QA'], job)
        run = self.store.one('SELECT * FROM ordinary_runs WHERE attempt=?', (attempt,))
        self.assertEqual(run['state'], 'intent')
        self.assertEqual(self.store.job(job['id'])['effects'], 'unknown')
        self.assertEqual(len(self.store.rows('SELECT * FROM ordinary_resources')), 1)
        self.git('update-ref', 'refs/heads/source', self.head, self.old)
        with self.assertRaisesRegex(Refusal, 'never replay'):
            await ordinary.perform(self.store, self.boards['QA'], job)
        self.assertFalse((self.area / 'qa-output/actual-run.txt').exists())

    async def test_same_job_recovery_requires_actual_role_and_effect_disposition_not_prompt_recasting(self):
        original, _ = self.supplied()
        job, attempt = await self.selected_preparation(original)
        before = self.store.attempt(attempt)
        with self.assertRaises(Refusal):
            await ordinary.perform(self.store, self.boards['QA'], job)
        reason = 'Ordinary original effect/collection needs accountable disposition: known preparation required'
        self.store.hold_job(job['id'], reason)
        self.store.record_operational_error(job['id'], {'error': reason}, 'QA', 'task-disposition-error')
        receipt = {'mode': 'remaining-work', 'reason': 'Synthetic preparation report boundary correction',
                   'evidence': ['Exact retained report, no ordinary intent in this fixture job'],
                   'remaining': 'Prepare a NEW read-only response under the prospective contract; retain original; no QA replay'}
        with self.assertRaisesRegex(Refusal, 'actual enrolled role owner'):
            self.store.request_recovery(job['id'], job['token'], attempt, self.config['roles']['Work']['owner'], receipt)
        with self.assertRaisesRegex(Refusal, 'reconciled effects required'):
            self.store.request_recovery(job['id'], job['token'], attempt, self.config['roles']['QA']['owner'], receipt)
        self.assertEqual(self.store.rows('SELECT * FROM recovery_requests'), [])
        self.assertEqual(self.store.rows('SELECT * FROM ordinary_runs'), [])
        self.assertEqual(self.store.attempt(attempt), before)


if __name__ == '__main__':
    unittest.main()
