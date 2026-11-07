"""Selected producer template and real progress-bounded AppServer contract."""
from pathlib import Path
from unittest.mock import patch

import test_writer_custody as fixtures
from test_tool_feedback741 import CallerPaths


class ProducerContract(CallerPaths):
    async def asyncSetUp(self):
        self.contract = Path(__file__).resolve().parents[1]/'templates/local-completion.md'
        original = fixtures.config_at
        def selected_template(directory):
            config = original(directory)
            config['tasks']['work-integrator']['templates'].append(str(self.contract))
            return config
        with patch.object(fixtures, 'config_at', side_effect=selected_template):
            await fixtures.WriterCustody.asyncSetUp(self)

    async def test_actual_selected_contract_matches_finite_progress_and_preserves_prior_returns(self):
        job, _ = await self.run_case()
        prompt = self.records[0]['prompt']
        self.assertIn(self.contract.read_text().strip(), prompt)
        for phrase in ('limits.max_owner_corrections', 'observed-tool-metadata',
                       'No unresolved failure of any index', 'interruption and conflicting',
                       'Exact current command inputs are transient untrusted evidence'):
            self.assertIn(phrase, prompt)
        self.assertNotIn('within that same single idle continuation budget', prompt)
        self.assertEqual(len(self.records), 3)
        self.assertEqual(self.answer['semantic'], 'DONE')
        self.assertEqual([r['semantic'] for r in self.detail['prior_turn_results']], ['PARTIAL'])
        self.assertEqual(self.detail['prior_turn_result']['semantic'], 'PARTIAL')
        self.assertEqual(self.store.job(job['id'])['effects'], 'reconciled')
