"""Actual production Source/collector flow with explicitly fictional native transport.
No provider, actual native encounter, live state, acceptance or historical credit.
"""
import asyncio
import copy
import json
from unittest.mock import patch
import _receiving485_fixtures as f
from coordinator_runtime import prospective, service, resource_scopes, report_scope
from coordinator_runtime.contracts import digest, encode, Refusal

class NativeReturn(f.Native):
    def configure_fixture(self):
        super().configure_fixture()
        self.config['roles']['Reviews']['legacy_hold_phases'] = ['integrator']
        self.config['tasks']['reviews-integrator'].update(effects='owned-artifacts', sandbox='workspace-write')
        self.config['tasks']['reviews-integrator']['effect_authority']['operations'].append('write-owned-artifacts')

    def configure_selection(self, s):
        super().configure_selection(s)
        packet = dict(component='component',origin='https://example.invalid/fictional.git',base=self.head,head=self.head,previous=None,answered_ids=[])
        p = dict(version='native-collected-review-v1', authority='Explicit synthetic Work current-return choice',
            expires=self.store.clock()+600, package='pkg', component='component', packet_sha256=digest(packet),
            source_task='reviews-proposer', source_task_sha256=digest(self.config['tasks']['reviews-proposer']),
            task='reviews-integrator', task_sha256=digest(self.config['tasks']['reviews-integrator']),
            review_policy_sha256=digest(s['service']['reviews']['reviews-proposer']),
            grant=self.store.one("SELECT grant_id FROM enrollments WHERE role='Reviews'")['grant_id'], resource_evidence='Synthetic owner physical map; explicit unrelated roots only', relevant_roots=[str(self.area)] if getattr(self,'resource_conflict',False) else [])
        s['service']['legacy_resources']['Reviews'].update(unbounded=True, native_review_return=p)

    def source(self):
        self.init_native()
        prospective.select(self.store,self.config['roles']['Work']['owner'],dict(configuration=digest(self.config),
            authority='Synthetic fresh finite no-effect rights',expires=self.store.clock()+600,
            processing_capability=self.key,grants={r:self.store.enrollment(r)['grant_id'] for r in self.config['roles']},
            tasks={n:dict(task_hash=digest(t),software_handoffs={},ordinary_effects=False) for n,t in self.config['tasks'].items()}))
        self.e=self.source_event();self.initial[self.e['id']]='reviews-proposer'
        asyncio.run(self.phase('schedule_classifications'))
        job=self.store.reserve();self.assertEqual(job['task'],'reviews-proposer')
        attempt=self.store.start_job(job['id'],job['token'])
        asyncio.run(self.dispatch.execute_review(job,attempt,self.e['body']['review']))
        self.original=self.store.job(job['id']);self.a=self.store.attempt(attempt)
        self.returned=self.store.event(self.original['response'])
        self.row=dict(role='Reviews',phase='integrator',task='reviews-integrator',package='pkg',event=self.returned['id'])
        self.record=self.store.processing.current()[1]['service']['legacy_resources']['Reviews']
        return self.returned

    def test_whole_native_return_and_real_integrator_transport(self):
        self.source()
        self.assertFalse(resource_scopes.blocked(self.store,self.row))
        reports=report_scope.integration_inputs(self.store,self.row)
        self.assertEqual(reports[0]['original'],self.returned['body'])
        def answer(job,out):
            if job['task']=='reviews-integrator':
                r=report_scope.integration_inputs(self.store,job)
                protocol=report_scope.integration_protocol(self.store,job,r)
                out['category']='consolidated'
                out['findings']=[dict(**protocol,analysis='Synthetic new analysis retains dissent and gaps',decision='Report only; no acceptance',method='Synthetic current fixture method',coverage=[dict(**pin,extent='whole',limits=['Fictional native transport; no provider qualification']) for pin in protocol['sources']])]
        self.task_result=answer
        # NativeModels normally replaces task findings; retain explicit current protocol.
        from _receiving485_fixtures import Models
        self.models=Models(self);self.dispatch=service.Dispatcher(self.store,self.boards,self.models,self.transport)
        asyncio.run(self.until(lambda:self.store.one("SELECT id FROM jobs WHERE task='reviews-integrator' AND response IS NOT NULL"),n=18))
        job=self.store.one("SELECT * FROM jobs WHERE task='reviews-integrator'")
        event=self.store.event(job['response'])
        self.assertEqual(event['report_custody']['collected_reports'],reports)
        self.assertTrue(self.record['unbounded'])
        self.assertEqual(len(self.transport.calls),2)

    def test_stale_held_uncollected_forged_method_and_orphan_refuse(self):
        self.source();self.assertFalse(resource_scopes.blocked(self.store,self.row))
        faults=[("UPDATE review_contexts SET state='interrupted'",()),
            ("UPDATE events SET hold='held' WHERE id=?",(self.returned['id'],)),("UPDATE events SET hold='held' WHERE id=?",(self.e['id'],)),
            ("UPDATE attempts SET collected=NULL WHERE id=?",(self.a['id'],)),
            ("UPDATE attempts SET controller='forged' WHERE id=?",(self.a['id'],)),
            ("UPDATE review_calls SET state='launch-intent' WHERE attempt=?",(self.a['id'],)),
            ("UPDATE processing_source_positions SET position=0 WHERE event=?",(self.returned['id'],)),
            ("UPDATE events SET payload=json_set(payload,'$.source_job','orphan') WHERE id=?",(self.returned['id'],))]
        for sql,args in faults:
            with self.subTest(sql=sql):
                self.store.db.execute('SAVEPOINT fault820')
                try:
                    self.store.db.execute(sql,args);self.assertTrue(resource_scopes.blocked(self.store,self.row))
                finally:
                    self.store.db.execute('ROLLBACK TO fault820');self.store.db.execute('RELEASE fault820')
        call=self.store.one('SELECT * FROM review_calls WHERE attempt=?',(self.a['id'],))
        turns=json.loads(call['receipt']);turns[1]['full_answer']=turns[0]['full_answer']
        self.store.db.execute('UPDATE review_calls SET receipt=? WHERE attempt=?',(encode(turns),self.a['id']))
        self.assertTrue(resource_scopes.blocked(self.store,self.row))

    def test_physical_overlap_unknown_lease_and_external_are_blocking(self):
        self.source()
        from coordinator_runtime.native_review_scope import eligible
        from coordinator_runtime import native_review_scope
        self.store.db.execute("INSERT INTO ordinary_resources VALUES('unmapped-resource','orphan-attempt')")
        self.assertTrue(resource_scopes.blocked(self.store,self.row))
        self.store.db.execute('DELETE FROM ordinary_resources')
        changed=copy.deepcopy(self.record);changed['reviews_report']={}
        with self.assertRaises(Refusal):native_review_scope.validate(self.store,'Reviews',changed)

    def test_actual_selected_resource_overlap_remains_blocking(self):
        self.resource_conflict=True
        self.source()
        self.assertTrue(resource_scopes.blocked(self.store,self.row))

    def test_held_original_refuses_before_its_body(self):
        self.source()
        self.store.set_hold(self.e['id'],'synthetic original source hold')
        original_event=self.store.event
        def guarded(key):
            if key==self.e['id']:raise AssertionError('held source body acquired')
            return original_event(key)
        with patch.object(self.store,'event',side_effect=guarded):
            self.assertTrue(resource_scopes.blocked(self.store,self.row))
