"""Collected attributed leaf regression. Fictional authentication/SDK answers.

Production admission, immutable receipt rows, Reviews collection and receiver
mapping run in a fresh isolated store. No native or provider effects occur.
"""
import copy
import json
from unittest.mock import patch
from test_report_batches50109 import ReportBatches
from coordinator_runtime import local_integration as local, local_native
from coordinator_runtime.contracts import Refusal, digest, encode


class ReportLeaf816(ReportBatches):
    def configure(self):
        super().configure()
        self.target = self.area/'status.json'
        self.target.write_text(encode({'status': {'id': 'status', 'state': 'partial'}}))
        task = self.config['tasks']['work-proposer']
        self.config['local_integration'] = dict(max_inflight=8,
            points={'status': dict(kind='item', line='Work', incarnation='fixture816',
                bindings=[dict(target=str(self.target), path=['status'])],
                resources=[], protected=['id'], writable=['state'])},
            tasks={'work-proposer': dict(capacity=1, discovery_batch=1, points=['status'],
                authority='Independent fictional finite Work status decision', method=task['templates'][0])})

    def lineage(self):
        self.keys = self.admit(self.reports)
        job = self.store.reserve()
        # Current protocol preserves the original envelopes in software custody.
        from test_report_transport739 import ReportTransport
        from support import collect
        attempt=self.store.start_job(job['id'],job['token'])
        self.boards['Reviews'].bind_software_attempt(self.store,self.store.job(job['id']),attempt,None)
        answer=ReportTransport.answer(self,job)
        collect(self.store,attempt,answer,tool_completion=dict(complete=True,items=[],nonzero_completions=[]))
        self.store.finish_job(job['id'],job['token'])
        self.job = self.store.job(job['id'])
        self.response = self.store.event(self.job['response'])
        self.receipt = dict(mode='route', task='work-proposer', package=None,
            integration=dict(state='known', reads=['status'], writes=['status']),
            reason='Independent Work status coordination')
        return self.response

    def observe(self):
        with self.store.tx():
            return local.observe_input(self.store, self.response, self.receipt)

    def test_collected_reviews_return_maps_known_work_point_preserving_originals(self):
        self.lineage()
        frozen = {t:self.store.rows('SELECT * FROM '+t) for t in (
            'events','attempts','results','jobs','processing_report_inputs','processing_source_positions')}
        before = self.target.read_bytes()
        with patch.object(local_native, 'authorize_scope', side_effect=AssertionError('native scope')):
            observed = self.observe()
        self.assertEqual(observed['packet']['reads'], ['status'])
        self.assertEqual(observed['packet']['writes'], ['status'])
        self.assertEqual(self.target.read_bytes(), before)
        for t, rows in frozen.items(): self.assertEqual(rows, self.store.rows('SELECT * FROM '+t), t)
        self.assertEqual([self.store.event(k)['body']['original'] for k in self.keys], self.reports)

    def test_metadata_wrong_cap_hold_birth_changed_hash_and_uncollected_before_body(self):
        self.lineage()
        mutations = [('events','hold','held','id',self.keys[1]),
            ('events','hash','forged','id',self.keys[0]),
            ('processing_source_positions','position',0,'event',self.keys[0]),
            ('attempts','collected',None,'id',self.job['active_attempt']),
            ('attempts','controller','foreign','id',self.job['active_attempt']),
            ('processing_capabilities','issuer','foreign','id',self.cap)]
        for table, field, value, key, identity in mutations:
            with self.subTest(table=table,field=field):
                old=self.store.one(f'SELECT {field} FROM {table} WHERE {key}=?',(identity,))[field]
                try:
                    self.store.db.execute(f'UPDATE {table} SET {field}=? WHERE {key}=?',(value,identity))
                    with patch.object(self.store,'event',side_effect=AssertionError('protected body read')):
                        with self.assertRaises(Refusal): self.observe()
                finally:
                    self.store.db.execute(f'UPDATE {table} SET {field}=? WHERE {key}=?',(old,identity))

    def test_expired_and_changed_task_grant_refuse_before_body(self):
        self.lineage()
        expiry=self.selection['service']['legacy_resources']['Reviews']['reviews_report']['expires']
        with patch.object(self.store,'clock',return_value=expiry+1), patch.object(self.store,'event',side_effect=AssertionError('expired body')):
            with self.assertRaises(Refusal): self.observe()
        old=self.config['tasks']['reviews-integrator']['authority']
        self.config['tasks']['reviews-integrator']['authority']='changed task'
        try:
            with patch.object(self.store,'event',side_effect=AssertionError('changed task body')):
                with self.assertRaises(Refusal): self.observe()
        finally: self.config['tasks']['reviews-integrator']['authority']=old
        old=self.store.enrollment('Work')['grant_id']
        self.store.db.execute("UPDATE enrollments SET grant_id='foreign' WHERE role='Work'")
        try:
            with patch.object(self.store,'event',side_effect=AssertionError('changed grant body')):
                with self.assertRaises(Refusal): self.observe()
        finally:self.store.db.execute("UPDATE enrollments SET grant_id=? WHERE role='Work'",(old,))

    def test_changed_frozen_receipt_and_orphan_marker_refuse(self):
        self.lineage()
        original=self.store.event(self.keys[0]); changed=copy.deepcopy(original)
        changed['body']['original']['reports'][0]['body']+=' forged'
        self.store.db.execute('UPDATE events SET payload=?,hash=? WHERE id=?',(encode(changed),digest(changed),changed['id']))
        with self.assertRaises(Refusal):self.observe()
        self.store.db.execute('UPDATE events SET payload=?,hash=? WHERE id=?',(encode(original),digest(original),original['id']))
        with self.assertRaises(Refusal):local.input_authority(self.store,original,'reviews-integrator',None)
        generic=copy.deepcopy(self.response)
        for key in ('source_job','source_delivery','processing_report'):generic.pop(key,None)
        self.store.db.execute('UPDATE events SET payload=?,hash=? WHERE id=?',(encode(generic),digest(generic),generic['id']))
        with self.assertRaises(Refusal):local.input_authority(self.store,generic,'work-proposer',None)

    def test_new_point_and_native_impersonation_remain_refused(self):
        self.lineage()
        self.receipt['integration']={'state':'new'}
        with self.assertRaises(Refusal):self.observe()
        self.receipt['integration']=dict(state='known',reads=['status'],writes=[])
        self.config['local_integration']['points']['status']['bindings']=[dict(native='branch',id='forged')]
        with self.assertRaises(Refusal):self.observe()

    def test_mutation_after_target_read_is_refused(self):
        self.lineage()
        from coordinator_runtime import custody
        read=custody.read_file
        def mutate(*args,**kwargs):
            answer=read(*args,**kwargs)
            if str(args[0]) == str(self.target):
                self.store.db.execute('UPDATE events SET hold=? WHERE id=?',('changed during target group',self.keys[0]))
            return answer
        with patch.object(custody,'read_file',side_effect=mutate):
            with self.assertRaises(Refusal):self.observe()

    def test_original23773_producer_admitted_collected_and_mapped(self):
        from pathlib import Path
        from coordinator_runtime import processing, prospective
        from test_qa629_repairs import actor
        original=Path('/handoff/original23773.json').read_text()
        evidence=json.loads(original)
        self.assertEqual(evidence['source'],'23773e6bfe46a2d71e8fc1dbfc38b1e60729331f')
        self.assertEqual(evidence['attempt']['state'],'collected')
        self.assertEqual(evidence['attempt']['exit'],0)
        # Fresh selection happens before this new journal has admitted inputs.
        self.reports[0]['reports'].append(dict(name='Whole original23773 producer',body=original))
        prospective.revoke(self.store,self.issuer,self.epoch['id'])
        with actor(self.boards['Work'].store,self.issuer):
            processing.revoke(self.store,self.boards,self.cap)
            self.selection['basis']=processing.basis(self.store,self.boards)
            self.selection['service']['legacy_resources']['Reviews']['reviews_report']['reports']=[
                dict(reference=r['reference'],sha256=digest(r)) for r in self.reports]
            self.cap=processing.select(self.store,self.boards,self.selection)['capability']
        self.store.processing=processing.Access(self.store,self.cap,self.boards)
        self.epoch=prospective.select(self.store,self.issuer,dict(configuration=digest(self.config),
            authority='Independent current finite Work report coordination lease',expires=self.store.clock()+120,
            processing_capability=self.cap,grants={r:self.store.enrollment(r)['grant_id'] for r in self.config['roles']},
            tasks={t:dict(task_hash=digest(v),software_handoffs={},ordinary_effects=False) for t,v in self.config['tasks'].items()}))
        self.lineage()
        observed=self.observe()
        self.assertEqual(observed['packet']['reads'],['status'])
        self.assertEqual(self.store.event(self.keys[0])['body']['original']['reports'][-1]['body'],original)

    def test_forged_response_identity_refuses_before_leaf_body(self):
        self.lineage()
        forged=copy.deepcopy(self.response);forged['id']='forged-response816'
        self.store.ingest(forged)
        self.response=forged
        with patch.object(self.store,'event',side_effect=AssertionError('forged response read leaf')):
            with self.assertRaises(Refusal):self.observe()
