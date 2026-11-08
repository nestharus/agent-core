"""Synthetic transport; production AppServer/Peer and Store, no provider claims."""
import copy
import json
import unittest

from test_corrections import ProcessCorrections
from support import result
from coordinator_runtime.dispatcher import RESULT_SCHEMA


class Handoff875(unittest.IsolatedAsyncioTestCase):
    asyncSetUp = ProcessCorrections.asyncSetUp
    adapter = ProcessCorrections.adapter
    task = ProcessCorrections.task

    def partial(self, semantic='PARTIAL', category='blocker'):
        return {**result(semantic, category),
            'summary':'Exact consumer operands remain unavailable',
            'unknowns':['Five consumer bindings and versions are absent'],
            'handoffs':[dict(recipient='Work',kind='question',text='Select missing operands',
                            ref=None,required='settled')],
            'no_handoff_reason':None}

    async def run_pair(self, first, final, *, fault=None, **plan):
        job, attempt = self.task()
        adapter = self.adapter(dict(result=first, second_result=final, **plan))
        prompts=[]
        start=adapter.start_turn
        async def observed(peer, thread, prompt, *args):
            prompts.append(prompt)
            return await start(peer, thread, prompt, *args)
        adapter.start_turn=observed
        if fault:
            original=adapter.continue_idle
            async def damaged(peer, *args, **kwargs):
                if fault=='correlation':
                    peer.final_records[0]['turn']='foreign-unowned-turn'
                else:
                    peer.hold_capture('synthetic-incomplete-capture')
                return await original(peer, *args, **kwargs)
            adapter.continue_idle=damaged
        outcome=await adapter.run(self.store,attempt,'Synthetic missing-operand task',
            self.config['tasks']['work-integrator'],RESULT_SCHEMA)
        self.assertEqual(outcome['exit'],0)
        self.assertEqual(outcome['detail']['teardown'],'actual-owned-process-exit-collected')
        self.store.collect(attempt,outcome)
        self.store.finish_job(job['id'],job['token'])
        row=self.store.attempt(attempt)
        self.assertIsNotNone(row['ended']);self.assertIsNotNone(row['collected'])
        return outcome,prompts

    async def test_valid_nonroutine_partial_and_scope_keep_blockers_and_original_prefixes(self):
        for semantic,category in [('PARTIAL','blocker'),('FAILED','blocker'),('UNKNOWN','scope')]:
            with self.subTest(semantic=semantic,category=category):
                first=self.partial(semantic,category);final=copy.deepcopy(first)
                final['findings'].append({'meaning':'No selected operands arrived; local work still blocked'})
                outcome,prompts=await self.run_pair(first,final)
                self.assertIsNone(outcome['error'],outcome['error'])
                self.assertEqual(outcome['result'],final)
                self.assertEqual(outcome['detail']['prior_turn_result'],first)
                self.assertEqual(outcome['detail']['resume_disposition'],'attempted-after-semantic-incompletion')
                self.assertEqual(len(prompts),2)
                self.assertIn('semantic incompletion',prompts[1])
                self.assertNotIn('after the collected interruption',prompts[1])
                self.assertIn('actual collector owns transport',prompts[1])
                self.assertIn('INNER TASK RESULT:',prompts[1])
                for key in ('findings','failures','unknowns','artifacts','handoffs'):
                    self.assertEqual(outcome['result'][key][:len(first[key])],first[key])
                self.assertEqual(outcome['result']['semantic'],semantic)

    async def test_erasing_or_recasting_original_handoff_is_still_rejected(self):
        first=self.partial();final=copy.deepcopy(first)
        final['handoffs']=[]
        final['findings'].append({'meaning':'Prior intent treated as possible send','original':first['handoffs']})
        outcome,prompts=await self.run_pair(first,final)
        self.assertIn('clarification erased or rewrote original handoffs',outcome['error'])
        self.assertEqual(outcome['detail']['prior_turn_result'],first)
        self.assertEqual(len(prompts),2)

    async def test_actual_interruption_retains_its_own_instruction(self):
        outcome,prompts=await self.run_pair(self.partial(),result(),hang_first=True)
        self.assertIsNone(outcome['error'],outcome['error'])
        self.assertEqual(len(prompts),2)
        self.assertIn('after the collected interruption',prompts[1])
        self.assertIn('Reconcile prior effects',prompts[1])
        self.assertEqual(outcome['detail']['resume_disposition'],
                         'attempted-owned-interrupt-and-same-session-continuation')

    async def test_uncertain_capture_cannot_resume(self):
        first=self.partial()
        outcome,prompts=await self.run_pair(first,first,fault='capture')
        self.assertIn('uncertainty prohibits continuation',outcome['error'])
        self.assertEqual(len(prompts),1)
        self.assertEqual(outcome['result'],first)

    async def test_foreign_correlation_cannot_resume(self):
        first=self.partial()
        outcome,prompts=await self.run_pair(first,first,fault='correlation')
        self.assertIn('uncertainty prohibits continuation',outcome['error'])
        self.assertEqual(len(prompts),1)
        self.assertEqual(outcome['capture'],'foreign-final-turn')


if __name__=='__main__':unittest.main()
