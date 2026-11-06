"""Constructed held proposers and fresh known reads; isolated fiction only.

The fixture constructs terminal journal metadata, never asserts physical closure.
Controller/writer evidence below is explicitly fictional owner testimony.
"""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from support import config_at, enrolled, event, queued, collect, result
from coordinator_runtime import local_integration as local
from coordinator_runtime.contracts import Refusal, encode, validate_config
import test_management406 as management_fixture


class WorkReads554(unittest.TestCase):
    def setUp(self):
        self.area = Path(tempfile.mkdtemp(prefix='reads554-', dir='/fixtures'))
        self.config = config_at(self.area)
        self.config['tasks']['work-proposer']['capacity'] = 5
        self.store = enrolled(self.config)
        self.addCleanup(self.store.close)
        self.old = []
        # These jobs genuinely freeze before local integration is selected, so
        # no synthetic empty local scope is inserted for either predecessor.
        for index, (semantic, capture) in enumerate((('PARTIAL', 'complete'), ('DONE', 'artifact-inventory-incomplete'))):
            queued(self.store, event(self.config, 'old-'+str(index), task='work-proposer'))
            job = self.store.reserve()
            self.assertIsNotNone(job)
            attempt = self.store.start_job(job['id'], job['token'])
            collect(self.store, attempt, result(semantic, 'proposal'), error='fictional original defect', capture=capture)
            self.store.db.execute("UPDATE jobs SET state='held',effects='none',hold_reason=?,recovery_state=? WHERE id=?",
                ('fictional original hold', 'awaiting-disposition' if index else None, job['id']))
            self.old.append(self.store.job(job['id']))
        self.catalog = self.area/'known.json'
        self.catalog.write_text(encode({'known': {str(i): {'id':str(i), 'state':'observed'} for i in range(6)}}))
        points = {str(i): {'kind':'item','line':'fictional-Work','incarnation':'fictional-lifetime',
            'bindings':[{'target':str(self.catalog),'path':['known',str(i)]}],
            'resources':[], 'protected':['id'], 'writable':['state']} for i in range(6)}
        self.config['local_integration'] = {'max_inflight':8,'points':points,'tasks':{
            'work-proposer': {'capacity':5,'discovery_batch':4,'points':list(points),
                'authority':'fictional current owner delegates known Work proposals only',
                'method':self.config['tasks']['work-proposer']['templates'][0]}}}
        validate_config(self.config)
        self.owner = self.config['roles']['Work']['owner']

    def fresh(self, *, writes=(), discovery=False):
        source = event(self.config, 'fresh', task='work-proposer')
        source['integration'] = {'new_work':'fictional positive novelty decision'} if discovery else {
            'reads':list(self.config['local_integration']['points']), 'writes':list(writes),
            'versions':{key:local.version(self.store,key,{str(self.catalog):self.catalog.read_bytes()})
                        for key in self.config['local_integration']['points']}}
        queued(self.store, source)
        return source

    def receipt(self, job):
        basis = self.store.work_read_closure_basis(job['id'], job['token'])
        return {'basis':basis, 'reason':'fictional local read coexistence; original failures remain held',
            'controllers':[{'controller':controller, 'collector':'fictional actual original collector',
                'end':0,'collected':True,'writers_closed':True,
                'evidence':['fictional whole controller, descendants and launch-capable writers closed; not real evidence']}
                for controller in basis['controllers']]}

    def fence(self, job):
        return self.store.fence_work_proposer(job['id'], job['token'], self.owner, self.receipt(job))

    def originals(self):
        # Every column is conserved, including semantic/capture/errors, original
        # members, pending consumer/outbox/custody facts and absent processing.
        tables = ('jobs','attempts','results','events','queue','outboxes','source_custody',
                  'artifact_custody','file_publications','recovery_requests','recovery_dispositions')
        return {table:self.store.rows('SELECT * FROM '+table+' ORDER BY rowid') for table in tables}

    def test_two_independent_fences_allow_six_known_reads_without_completing_old_duties(self):
        self.fresh()
        before = self.originals()
        self.assertIsNone(self.store.reserve())
        self.fence(self.old[0])
        self.assertIsNone(self.store.reserve())  # The other old reservation still fences.
        self.fence(self.old[1])
        self.assertEqual(self.originals(), before)
        for old in self.old:
            self.assertFalse(self.store.execution_complete(self.store.job(old['id'])))
            self.assertIsNone(local.scope_for(self.store, old))
        fresh = self.store.reserve()
        self.assertIsNotNone(fresh)
        scope = local.scope_for(self.store, fresh)
        self.assertEqual(scope['reads'], [str(i) for i in range(6)])
        self.assertEqual(scope['writes'], [])
        self.assertEqual(set(scope['read_fences']), {j['id'] for j in self.old})
        attempt = self.store.start_job(fresh['id'], fresh['token'])
        self.assertIsNotNone(attempt)
        self.assertEqual(self.store.rows('SELECT * FROM file_publications'), [])
        self.assertTrue(all(r['processed_at'] is None for r in self.store.rows('SELECT processed_at FROM events')))
        for old in self.old:
            with self.assertRaisesRegex(Refusal, 'execution retired'):
                self.store.finish_job(old['id'], old['token'])
            with self.assertRaisesRegex(Refusal, 'execution retired'):
                self.store.require_execution_open(old['id'])

    def test_numeric_END_and_readonly_policy_alone_do_not_supply_controller_closure(self):
        self.fresh()
        receipt = self.receipt(self.old[0])
        for change in (lambda r:r.update(controllers=[]),
                       lambda r:r['controllers'][0].update(writers_closed=False),
                       lambda r:r['controllers'][0].update(end=None),
                       lambda r:r['controllers'][0].update(controller='foreign-controller'),
                       lambda r:r['controllers'][0].update(evidence=[])):
            altered = copy.deepcopy(receipt); change(altered)
            with self.assertRaises(Refusal):
                self.store.fence_work_proposer(self.old[0]['id'], self.old[0]['token'], self.owner, altered)
        self.assertEqual(self.store.rows('SELECT * FROM work_read_fences'), [])
        self.assertIsNone(self.store.reserve())

    def test_fence_requires_owner_exact_token_current_basis_and_active_sources(self):
        job = self.old[0]; receipt = self.receipt(job)
        with self.assertRaises(Refusal):
            self.store.fence_work_proposer(job['id'], job['token'], 'foreign-owner', receipt)
        with self.assertRaises(Refusal):
            self.store.fence_work_proposer(job['id'], 'foreign-token', self.owner, receipt)
        self.store.db.execute("UPDATE jobs SET hold_reason='changed held duty' WHERE id=?", (job['id'],))
        with self.assertRaisesRegex(Refusal, 'basis changed'):
            self.store.fence_work_proposer(job['id'], job['token'], self.owner, receipt)
        self.store.db.execute("UPDATE enrollments SET intake=0 WHERE role='Work'")
        with self.assertRaisesRegex(Refusal, 'active runtime enrollment'):
            self.store.work_read_closure_basis(job['id'], job['token'])

    def test_each_uncollected_or_nonterminal_related_original_refuses_fencing(self):
        job = self.old[0]; attempt = job['active_attempt']
        for field in ('begin','ended','collected','exit'):
            value = self.store.attempt(attempt)[field]
            self.store.db.execute('UPDATE attempts SET '+field+'=NULL WHERE id=?', (attempt,))
            with self.assertRaisesRegex(Refusal, 'all related originals'):
                self.store.work_read_closure_basis(job['id'], job['token'])
            self.store.db.execute('UPDATE attempts SET '+field+'=? WHERE id=?', (value, attempt))
        self.store.db.execute("UPDATE attempts SET state='running' WHERE id=?", (attempt,))
        with self.assertRaisesRegex(Refusal, 'all related originals'):
            self.store.work_read_closure_basis(job['id'], job['token'])

    def test_old_writer_or_missing_frozen_policy_cannot_gain_read_fence(self):
        job = self.old[0]
        frozen = json.loads(self.store.one('SELECT task FROM job_resource_policies WHERE job=?',(job['id'],))['task'])
        frozen['effect_authority']['write_roots'] = [str(self.area)]
        # Construct two other predecessor policies; original-policy triggers
        # remain in force. Today's safe task never replaces a frozen writer.
        writer = {**job, 'id':'fictional-old-writer'}
        self.store.db.execute('INSERT INTO jobs('+','.join(writer)+') VALUES('+','.join('?' for _ in writer)+')', tuple(writer.values()))
        self.store.db.execute('INSERT INTO job_resource_policies VALUES(?,?,NULL)', (writer['id'], encode(frozen)))
        with self.assertRaisesRegex(Refusal, 'original frozen'):
            self.store.work_read_closure_basis(writer['id'], writer['token'])
        missing = {**job, 'id':'fictional-missing-policy'}
        self.store.db.execute('INSERT INTO jobs('+','.join(missing)+') VALUES('+','.join('?' for _ in missing)+')', tuple(missing.values()))
        with self.assertRaisesRegex(Refusal, 'original frozen'):
            self.store.work_read_closure_basis(missing['id'], missing['token'])

    def test_fences_do_not_allow_write_or_discovery(self):
        for old in self.old:self.fence(old)
        self.fresh(writes=['0'])
        self.assertIsNone(self.store.reserve())
        self.store.db.execute("UPDATE queue SET state='held' WHERE state='queued'")
        source = event(self.config,'positive-new',task='work-proposer')
        source['integration'] = {'new_work':'fictional positive new work'}
        queued(self.store, source)
        self.assertIsNone(self.store.reserve())

    def test_capacity_and_resource_limits_still_apply(self):
        for old in self.old:self.fence(old)
        self.fresh()
        self.config['local_integration']['max_inflight'] = 2
        self.assertIsNone(self.store.reserve())
        self.config['local_integration']['max_inflight'] = 8
        self.config['local_integration']['tasks']['work-proposer']['capacity'] = 2
        self.assertIsNone(self.store.reserve())
        self.config['local_integration']['tasks']['work-proposer']['capacity'] = 5
        self.config['local_integration']['points']['0']['resources'] = ['fictional-resource']
        self.store.db.execute('INSERT INTO ordinary_resources VALUES(?,?)', ('fictional-resource','fictional-other-attempt'))
        self.assertIsNone(self.store.reserve())

    def test_fresh_authority_and_old_basis_changes_refuse_before_launch(self):
        for old in self.old:self.fence(old)
        self.fresh()
        fresh = self.store.reserve(); self.assertIsNotNone(fresh)
        self.config['tasks']['work-proposer']['effect_authority']['write_roots'] = [str(self.area)]
        with self.assertRaisesRegex(Refusal, 'current read-only authority'):
            self.store.start_job(fresh['id'], fresh['token'])
        self.config['tasks']['work-proposer']['effect_authority']['write_roots'] = []
        self.store.db.execute("UPDATE attempts SET capture='newly-incomplete' WHERE id=?", (self.old[0]['active_attempt'],))
        with self.assertRaisesRegex(Refusal, 'read fence'):
            self.store.start_job(fresh['id'], fresh['token'])
        self.assertIsNone(self.store.job(fresh['id'])['active_attempt'])

    def test_changed_material_requires_reconciliation_without_revising_old_packet(self):
        for old in self.old:self.fence(old)
        source = self.fresh()
        before = copy.deepcopy(source['integration'])
        self.catalog.write_text(encode({'known':{str(i):{'id':str(i),'state':'changed'} for i in range(6)}}))
        fresh = self.store.reserve(); self.assertIsNotNone(fresh)
        attempt = self.store.start_job(fresh['id'], fresh['token'])
        fresh = self.store.job(fresh['id'])
        local.prepare_input_basis(self.store, fresh, attempt, self.config['tasks']['work-proposer'])
        basis = json.loads(self.store.one('SELECT basis FROM local_bases WHERE attempt=?',(attempt,))['basis'])
        self.assertEqual(basis['scope']['mode'], 'reconcile')
        self.assertEqual(self.store.event(source['id'])['integration'], before)
        with self.assertRaisesRegex(Refusal, 'all four'):
            local.validate_method(self.store, fresh, self.store.attempt(attempt), result())
        self.assertEqual(self.store.rows('SELECT * FROM file_publications'), [])

    def test_an_additional_related_original_cannot_hide_behind_terminal_active_attempt(self):
        old = self.old[0]
        with self.store.tx():
            attempt = self.store._attempt('diagnosis', None, old['id'],
                self.config['diagnosis']['binding'], self.config['diagnosis']['profile'])
        with self.assertRaisesRegex(Refusal, 'all related originals'):
            self.store.work_read_closure_basis(old['id'], old['token'])
        collect(self.store, attempt, {'fictional':'diagnosis; not semantic completion'})
        basis = self.store.work_read_closure_basis(old['id'], old['token'])
        self.assertEqual(len(basis['attempts']), 2)
        self.assertEqual(self.store.attempt(old['active_attempt'])['semantic'], 'PARTIAL')


class WorkReadManagement554(unittest.TestCase):
    setUp = management_fixture.Management.setUp
    insert = management_fixture.Management.insert
    call = management_fixture.Management.call
    management_basis = management_fixture.Management.management_basis

    def prepare_proposer(self):
        # The inherited fixture intentionally revokes original grants and pauses
        # enrollment. Only its genuine exact operation-local management remains.
        self.store.db.execute("UPDATE jobs SET phase='proposer',task='work-proposer',effects='none' WHERE id='synthetic-held'")
        self.store.db.execute('INSERT INTO job_resource_policies VALUES(?,?,NULL)',
            ('synthetic-held', encode(self.config['tasks']['work-proposer'])))

    def managed(self, command, *, receipt=None, selection_change=None, expected=0, actor=None):
        selection = {'basis':self.basis,'expires':1100.,'operation':command,
            'target':{'job':'synthetic-held','token':'synthetic-token'},
            'records':{'jobs':['synthetic-held'],'events':[self.source['id']]}}
        if selection_change:selection_change(selection)
        path = self.home/'read-management.json'; path.write_text(encode(selection))
        args = [command, 'synthetic-held','--token','synthetic-token','--management',str(path)]
        if receipt is not None:
            path = self.home/'read-receipt.json'; path.write_text(encode(receipt));args += ['--receipt',str(path)]
        return self.call(*args, expected=expected, actor=actor)

    def test_paused_original_grants_require_exact_new_management_not_future_processing(self):
        self.prepare_proposer()
        self.call('work-read-closure-basis','synthetic-held','--token','synthetic-token',expected=2)
        basis = self.managed('work-read-closure-basis')
        receipt = {'basis':basis,'reason':'fictional owner selected local read coexistence only',
            'controllers':[{'controller':c,'collector':'fictional actual collector','end':0,
                'collected':True,'writers_closed':True,'evidence':['fictional original controller/writers closed']}
                for c in basis['controllers']]}
        for change in (lambda s:s.update(operation='retire-integration'),
                       lambda s:s.update(expires=999.),
                       lambda s:s['target'].update(job='foreign-job'),
                       lambda s:s['records']['events'].append('foreign-event')):
            self.managed('fence-work-proposer', receipt=receipt, selection_change=change, expected=2)
        self.managed('fence-work-proposer', receipt=receipt, actor='foreign-actor', expected=2)
        before = self.store.job('synthetic-held')
        self.managed('fence-work-proposer', receipt=receipt)
        self.assertEqual(self.store.job('synthetic-held'), before)
        self.assertFalse(self.store.execution_complete(before))
        self.assertEqual(len(self.store.rows('SELECT * FROM integration_management_operations')), 1)
        self.assertEqual(self.store.rows('SELECT * FROM processing_capabilities'), [])
        self.assertEqual(self.store.one("SELECT intake FROM enrollments WHERE role='Work'")['intake'], 0)
        self.managed('fence-work-proposer', receipt=receipt, expected=2)  # Permanent once-only fence.

    def test_new_management_does_not_broaden_old_integrator_routes(self):
        self.prepare_proposer()
        selection = {'basis':self.basis,'expires':1100.,'operation':'integration-closure-basis',
            'target':{'job':'synthetic-held','token':'synthetic-token'},
            'records':{'jobs':['synthetic-held'],'events':[self.source['id']]}}
        path = self.home/'wrong-phase.json';path.write_text(encode(selection))
        self.call('integration-closure-basis','synthetic-held','--token','synthetic-token',
                  '--management',str(path),expected=2)


if __name__ == '__main__':
    unittest.main(verbosity=2)
