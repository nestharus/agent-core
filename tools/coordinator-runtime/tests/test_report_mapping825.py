"""Real delegated completion and genuine collected result regression for R823-1."""
import asyncio
import copy
import json
from types import SimpleNamespace
from unittest.mock import patch
from test_report_leaf816 import ReportLeaf816
from test_report_transport739 import ReportTransport
from test_qa629_repairs import actor
from support import collect, ident
from coordinator_runtime import processing, prospective, metadata_lookup as lookup
from coordinator_runtime import local_integration as local
from coordinator_runtime.contracts import Refusal, digest, encode


class Mapping825(ReportLeaf816):
    def setUp(self):
        select = processing.select
        def selected(store, boards, value):
            value['metadata_lookup'] = dict(tasks=['work-proposer'],
                authority='Explicit fictional independent Work metadata interpretation',
                max_points=16, max_bytes=65536)
            return select(store, boards, value)
        with patch.object(processing, 'select', side_effect=selected):
            super().setUp()

    def lineage_outer(self, raw):
        answer = ReportTransport.answer
        def outer(case, job):
            result = answer(case, job)
            result['integration'] = raw(case)
            return result
        with patch.object(ReportTransport, 'answer', outer):
            self.lineage()

    def delegated(self, state):
        self.lineage()
        self.classify()
        original = copy.deepcopy(self.response)
        retained = {t:self.store.rows('SELECT * FROM '+t) for t in
            ('processing_report_inputs','processing_source_positions','results')}
        claimed = lookup.claim(self.store)
        self.assertIsNotNone(claimed)
        event, attempt = claimed
        self.assertEqual(event, self.response['id'])
        self.assertEqual(self.store.attempt(attempt)['kind'], 'input-mapping')
        async def model(store, key, prompt, spec, schema):
            store.begin(key, dict(fictional_model_transport=True))
            store.session(key, ident())
            request = dict(state=state)
            if state == 'known': request.update(reads=['status'], writes=[])
            return dict(exit=0, capture='complete', cleanup='done', error=None,
                result=dict(semantic='DONE', summary='Independent frozen metadata interpretation',
                    decision_json=encode(dict(task='work-proposer', integration=request,
                        reason='Explicit independent Work decision', evidence=['original and frozen points'],
                        remaining_obligations=['all original duties remain']))),
                detail=dict(tool_completion=dict(complete=True,items=[],nonzero_completions=[])))
        dispatcher = processing.ProcessingDispatcher(self.store, models=SimpleNamespace(run=model), boards=self.boards)
        asyncio.run(lookup.execute(dispatcher,event,attempt))
        self.assertEqual(self.store.attempt(attempt)['state'], 'collected')
        self.assertEqual(self.store.attempt(attempt)['exit'], 0)
        self.assertEqual(self.store.event(event), original)
        for t,rows in retained.items():
            current=self.store.rows('SELECT * FROM '+t)
            for row in rows:self.assertIn(row,current,t)
            if t != 'results':self.assertEqual(rows,current,t)
        self.assertEqual([self.store.event(k)['body']['original'] for k in self.keys],self.reports)
        return self.store.one('SELECT * FROM input_lookups WHERE event=?',(event,))

    def test_delegated_new_completion_refuses_before_resolution(self):
        row = self.delegated('new')
        self.assertIsNotNone(row['error'], 'new decision acquired a resolution')
        self.assertIn('existing known-point', row['error'])
        self.assertIsNone(row['resolution'])
        self.assertIsNone(self.store.input_resolution(self.response['id']))
        self.assertEqual(self.store.rows('SELECT * FROM local_lookup_points'), [])

    def test_delegated_known_completion_and_packet_work(self):
        row = self.delegated('known')
        self.assertIsNone(row['error'])
        self.assertIsNotNone(row['resolution'])
        scope = local.packet(self.store,dict(event=self.response['id'],task='work-proposer',package=None))
        self.assertEqual(scope['lane'],'anchored')
        self.assertEqual(scope['reads'],['status'])

    def test_genuine_outer_new_work_refuses_packet(self):
        self.lineage_outer(lambda case:dict(new_work='Genuine producer novelty evidence'))
        self.assertTrue(local.input_authority(self.store,self.response,'work-proposer',None))
        with self.assertRaisesRegex(Refusal,'existing known-point'):
            local.packet(self.store,dict(event=self.response['id'],task='work-proposer',package=None))

    def test_genuine_outer_known_packet_works(self):
        self.lineage_outer(lambda case:dict(reads=['status'],writes=[],
            versions={'status':local.version(case.store,'status',{str(case.target):case.target.read_bytes()})}))
        scope=local.packet(self.store,dict(event=self.response['id'],task='work-proposer',package=None))
        self.assertEqual(scope['lane'],'anchored')
