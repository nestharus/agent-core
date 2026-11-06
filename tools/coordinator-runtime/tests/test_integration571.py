"""Held read-only predecessor custody survives proposer/integrator publication.

Every old record/closure statement is constructed fiction. New proposal and
stage text come from actual owned OS children; tool/authority adapters are
declared fiction. This is no actual native, semantic or rollout acceptance.
"""
import copy
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

from support import collect, event, queued, result
from coordinator_runtime import bounded_log, local_integration as local, publication, routine
from coordinator_runtime.contracts import Refusal, encode, ident, validate_config
import test_work_reads554 as read_fixture
from test_local436 import Board


class Integration571(unittest.TestCase):
    receipt = read_fixture.WorkReads554.receipt
    fence = read_fixture.WorkReads554.fence
    originals = read_fixture.WorkReads554.originals

    def setUp(self):
        read_fixture.WorkReads554.setUp(self)
        # Retain a distinct original recovery custodian; no owner is erased to
        # satisfy a read-fence guard. It too must appear in closure evidence.
        self.store.db.execute("UPDATE jobs SET recovery_owner='fictional-recovery-controller571',"
            "recovery_state='awaiting-disposition' WHERE id=?", (self.old[1]['id'],))
        self.old = [self.store.job(j['id']) for j in self.old]
        self.peers = [self.catalog] + [self.area/('consumer'+str(i)+'.json') for i in range(5)]
        for peer in self.peers[1:]:
            peer.write_text(encode({'owner':'original-consumer-owner','history':['retained'],
                'known':json.loads(self.catalog.read_text())['known']}))
        for key, point in self.config['local_integration']['points'].items():
            point['bindings'].extend({'target':str(p),'path':['known',key]} for p in self.peers[1:])
        self.log = self.area/'WORK_LOG.md'
        self.log.write_text('original bounded-log history\n')
        task = self.config['tasks']['work-integrator']
        task.update(effects='owner-reconcile', sandbox='workspace-write', network=False,
            routine_completion={'kind':bounded_log.KIND, 'targets':[str(p) for p in self.peers]+[str(self.log)],
                'bounded_log':{'target':str(self.log), 'max_lines':12, 'max_bytes':8192, 'max_entry_bytes':16384}})
        task['effect_authority'].update(operations=['read-reports','write-role-records'],
            write_roots=[str(p) for p in self.peers]+[str(self.log)])
        self.config['local_integration']['tasks']['work-integrator'] = copy.deepcopy(
            self.config['local_integration']['tasks']['work-proposer'])
        self.config['local_integration']['tasks']['work-integrator']['method'] = task['templates'][0]
        self.config['local_integration']['max_inflight'] = 5
        validate_config(self.config)
        self.board = Board()  # Explicit fictional completion-authority adapter.

    def fresh(self, *, key=None, task='work-proposer'):
        source = event(self.config, 'known571-'+ident(), task=task)
        keys = list(self.config['local_integration']['points']) if key is None else [key]
        source['integration'] = {'reads':keys, 'writes':[] if task == 'work-proposer' else keys,
            'versions':{k:local.version(self.store,k,self.bodies()) for k in keys}}
        queued(self.store,source)
        return source

    def bodies(self):
        return {str(p):p.read_bytes() for p in self.peers}

    def child(self, argv):
        completed = subprocess.run([sys.executable, *argv], capture_output=True, text=True, timeout=10)
        with (self.area/'originals571.jsonl').open('a') as out:
            out.write(encode({'argv':argv, 'END':completed.returncode,
                'stdout':completed.stdout,'stderr':completed.stderr})+'\n')
        self.assertEqual(completed.returncode, 0, completed.stderr)
        return json.loads(completed.stdout)

    def preserve(self, before):
        for table, rows in before.items():
            keys = [r['name'] for r in self.store.rows('PRAGMA table_info('+table+')') if r['pk']]
            for row in rows:
                found = self.store.one('SELECT * FROM '+table+' WHERE '+' AND '.join(k+'=?' for k in keys),
                    tuple(row[k] for k in keys))
                self.assertEqual(found, row, table)
        for old in self.old:
            self.assertEqual(self.store.job(old['id']), old)
            self.assertFalse(self.store.execution_complete(old))
            self.assertIsNone(local.scope_for(self.store, old))
            with self.assertRaisesRegex(Refusal, 'execution retired'):
                self.store.require_execution_open(old['id'])

    def proposal(self, index=0):
        source = self.fresh()
        job = self.store.reserve()
        self.assertIsNotNone(job)
        attempt = self.store.start_job(job['id'], job['token'])
        answer = result(category='proposal')
        # Actual emitted proposal selects a current known scoped write. The
        # source job itself reads only; no parent post-capture edits are used.
        answer['integration'] = {'reads':[str(index)], 'writes':[str(index)],
            'versions':{str(index):local.version(self.store,str(index),self.bodies())}}
        emitted = self.child(['-c','import sys; print(sys.argv[1])',encode(answer)])
        self.assertEqual(emitted, answer)
        collect(self.store, attempt, emitted)
        handoff = self.store.finish_job(job['id'],job['token'])
        self.assertIsNotNone(handoff)
        event = self.store.event(handoff)
        self.assertEqual(event['body'], emitted)
        queued(self.store, event)
        return source, handoff

    def integration(self):
        job = self.store.reserve()
        self.assertIsNotNone(job)
        self.assertEqual(job['phase'], 'integrator')
        scope = local.scope_for(self.store, job)
        self.assertEqual(set(scope['read_fences']), {j['id'] for j in self.old})
        attempt = self.store.start_job(job['id'],job['token'])
        (self.store.home/'artifacts'/attempt).mkdir(parents=True)
        job = self.store.job(job['id'])
        routine.prepare(self.store,self.board,job,attempt,self.config['tasks'][job['task']])
        return job, attempt

    def stage_and_collect(self, job, attempt):
        mapping = publication.stages(self.store,attempt)
        key = local.scope_for(self.store,job)['writes'][0]
        script = '''import json,pathlib,sys
m=json.loads(sys.argv[1]); catalog=sys.argv[2]; key=sys.argv[3]; log=sys.argv[4]
for target,stage in m.items():
 if target != log:
  p=pathlib.Path(stage); data=json.loads(p.read_text()); data['known'][key]['state']='integrated'; p.write_text(json.dumps(data))
pathlib.Path(m[log]).write_text('Fresh scoped integration entry\\n')
print(json.dumps({'stage_writer':'owned OS child only, fictional tool protocol'}))
'''
        self.child(['-c',script,encode(mapping),str(self.catalog),key,str(self.log)])
        publication.conserve_stages(self.store,attempt,self.config['tasks'][job['task']])
        answer = result()
        answer['completion'] = {'version':1,'local':'ready','failures':[],'unknowns':[],'tools':[],
            'integration_steps':[{'step':s,'evidence':'fictional selected method '+s} for s in local.STEPS]}
        answer.update(handoffs=[], no_handoff_reason='fictional exact seven consumers only')
        emitted = self.child(['-c','import sys; print(sys.argv[1])',encode(answer)])
        collect(self.store,attempt,emitted,tool_completion={'complete':True,
            'items':[{'id':'fixture-stage-writer','exit_code':0,'status':'completed'}]})

    def test_six_proposals_integrate_seven_consumers_each_with_old_recovery_custody_held(self):
        self.fresh()
        self.assertIsNone(self.store.reserve())
        self.fence(self.old[0])
        self.assertIsNone(self.store.reserve())
        receipt = self.receipt(self.old[1])
        self.assertIn('fictional-recovery-controller571',receipt['basis']['controllers'])
        self.fence(self.old[1])
        # Initial source already queued, so perform its actual proposer now;
        # proposal() adds a new source as well. Keep this test's six exact chains
        # separate by holding the initial guard-only input, without old edits.
        self.store.db.execute("UPDATE queue SET state='held' WHERE state='queued'")
        before = self.originals()
        (self.area/'old-before571.json').write_text(encode(before))
        inodes = {str(p):p.stat().st_ino for p in [*self.peers,self.log]}
        chains = []
        for index in range(6):
            source, handoff = self.proposal(index)
            self.assertIsNone(self.store.one('SELECT processed_at FROM events WHERE id=?',(source['id'],))['processed_at'])
            job, attempt = self.integration()
            self.stage_and_collect(job,attempt)
            self.assertTrue(routine.reconcile(self.store,self.board,self.store.job(job['id'])))
            receipts = self.store.rows('SELECT * FROM file_publications WHERE attempt=?',(attempt,))
            self.assertEqual(len(receipts),7)
            self.assertTrue(all(r['state']=='published' for r in receipts))
            # Same-original receipt join performs no second publication.
            self.assertFalse(routine.reconcile(self.store,self.board,self.store.job(job['id'])))
            self.store.finish_job(job['id'],job['token'])
            self.assertIsNotNone(self.store.one('SELECT processed_at FROM events WHERE id=?',(handoff,))['processed_at'])
            self.assertIsNotNone(self.store.one('SELECT processed_at FROM events WHERE id=?',(source['id'],))['processed_at'])
            chains.append({'source':source['id'],'handoff':handoff,'integrator':job['id'],
                'attempt':attempt,'receipts':receipts,'whole_chain_processed':True})
        self.assertEqual({str(p):p.stat().st_ino for p in [*self.peers,self.log]},inodes)
        self.assertTrue(all(v['state']=='integrated' for v in json.loads(self.catalog.read_text())['known'].values()))
        self.preserve(before)
        (self.area/'outcomes571.json').write_text(encode({'chains':chains,
            'old_rows_conserved':True,'old_jobs':self.old,'old_execution_complete':False,
            'same_inodes':True,'semantic_acceptance':None,'actual_runtime_proof':False}))

    def test_unclosed_recovery_controller_or_pending_recovery_cannot_be_bypassed(self):
        old = self.old[1]
        receipt = self.receipt(old)
        receipt['controllers'] = [c for c in receipt['controllers'] if c['controller'] != old['recovery_owner']]
        with self.assertRaisesRegex(Refusal,'every original controller'):
            self.store.fence_work_proposer(old['id'],old['token'],self.owner,receipt)
        self.store.db.execute("UPDATE jobs SET recovery_state='diagnosing' WHERE id=?",(old['id'],))
        with self.assertRaisesRegex(Refusal,'active recovery'):
            self.receipt(old)
        self.store.db.execute('UPDATE jobs SET recovery_owner=NULL WHERE id=?',(old['id'],))
        with self.assertRaisesRegex(Refusal,'active recovery'):
            self.receipt(old)
        self.store.db.execute('UPDATE jobs SET recovery_owner=? WHERE id=?',(old['recovery_owner'],old['id']))
        self.store.db.execute("UPDATE jobs SET recovery_state='awaiting-disposition' WHERE id=?",(old['id'],))
        self.store.db.execute("INSERT INTO recovery_requests VALUES('pending571',?,?,?,'{}','pending',0,NULL)",
            (old['id'],old['active_attempt'],self.owner))
        with self.assertRaisesRegex(Refusal,'pending owner recovery'):
            self.receipt(old)

    def test_scoped_integrator_capacity_resources_and_unfenced_predecessor_still_block(self):
        for old in self.old:self.fence(old)
        self.proposal()
        self.config['local_integration']['max_inflight'] = 2
        self.assertIsNone(self.store.reserve())
        self.config['local_integration']['max_inflight'] = 5
        self.config['local_integration']['points']['0']['resources'] = ['fixture-lease571']
        self.store.db.execute('INSERT INTO ordinary_resources VALUES(?,?)',('fixture-lease571','other-owned-fixture'))
        self.assertIsNone(self.store.reserve())
        self.store.db.execute('DELETE FROM ordinary_resources WHERE resource=?',('fixture-lease571',))
        self.config['tasks']['work-integrator']['network'] = True
        self.assertIsNone(self.store.reserve())

    def test_integrators_need_every_exact_fence_and_keep_two_old_capacity_charges(self):
        for key in ('0','1','2','3'):
            self.fresh(key=key,task='work-integrator')
        self.assertIsNone(self.store.reserve())
        self.fence(self.old[0])
        self.assertIsNone(self.store.reserve())
        self.fence(self.old[1])
        jobs = [self.store.reserve() for _ in range(3)]
        self.assertTrue(all(j and j['phase']=='integrator' for j in jobs))
        self.assertIsNone(self.store.reserve())
        self.assertFalse(any(self.store.execution_complete(old) for old in self.old))

    def test_native_or_discovery_or_unguarded_writer_receives_no_integrator_exception(self):
        for old in self.old:self.fence(old)
        row = {'role':'Work','phase':'integrator','task':'work-integrator'}
        scope = {'lane':'anchored','reads':[],'writes':['0']}
        self.assertTrue(self.store.work_read_coexists(row,scope,self.old[0]))
        self.config['local_integration']['points']['0']['bindings'] = [{'native':'not-acquired'}]
        self.assertFalse(self.store.work_read_coexists(row,scope,self.old[0]))
        self.assertFalse(self.store.work_read_coexists(row,{**scope,'lane':'discovery'},self.old[0]))
        self.config['tasks']['work-integrator']['routine_completion'] = None
        self.assertFalse(self.store.work_read_coexists(row,scope,self.old[0]))

    def test_changed_basis_before_launch_and_before_publication_refuses(self):
        for old in self.old:self.fence(old)
        self.proposal()
        job = self.store.reserve()
        original = self.store.job(self.old[1]['id'])['hold_reason']
        self.store.db.execute("UPDATE jobs SET hold_reason='changed duty' WHERE id=?",(self.old[1]['id'],))
        with self.assertRaisesRegex(Refusal,'read fence'):
            self.store.start_job(job['id'],job['token'])
        self.assertIsNone(self.store.job(job['id'])['active_attempt'])
        self.store.db.execute('UPDATE jobs SET hold_reason=? WHERE id=?',(original,self.old[1]['id']))
        attempt = self.store.start_job(job['id'],job['token'])
        (self.store.home/'artifacts'/attempt).mkdir(parents=True)
        job = self.store.job(job['id'])
        routine.prepare(self.store,self.board,job,attempt,self.config['tasks'][job['task']])
        self.stage_and_collect(job,attempt)
        self.store.db.execute("UPDATE jobs SET recovery_owner='changed-custodian' WHERE id=?",(self.old[1]['id'],))
        with self.assertRaisesRegex(Refusal,'read fence'):
            routine.reconcile(self.store,self.board,self.store.job(job['id']))
        self.assertEqual(self.store.rows('SELECT * FROM file_publications'),[])

    def test_predecessor_publication_uncertainty_is_not_nonwriting(self):
        old = self.old[0]
        self.store.db.execute("INSERT INTO file_publications(attempt,target,state) VALUES(?,'fictional-unacquired','intent')",
            (old['active_attempt'],))
        with self.assertRaisesRegex(Refusal,'publication duties'):
            self.receipt(old)

    def test_partial_publication_keeps_intent_source_hold_and_refuses_replay(self):
        for old in self.old:self.fence(old)
        before = self.originals()
        source, handoff = self.proposal()
        job, attempt = self.integration()
        self.stage_and_collect(job,attempt)
        write = publication.write_same_inode
        count = 0
        def interrupted(fd, body):
            nonlocal count
            count += 1
            write(fd,body)
            if count == 2:
                raise OSError('fictional interruption after possible effect')
        with patch.object(publication,'write_same_inode',side_effect=interrupted):
            with self.assertRaisesRegex(OSError,'after possible effect'):
                routine.reconcile(self.store,self.board,self.store.job(job['id']))
        self.assertEqual(count,2)
        with self.assertRaisesRegex(Refusal,'never replay'):
            routine.reconcile(self.store,self.board,self.store.job(job['id']))
        self.assertEqual(count,2)
        self.assertTrue(self.store.rows("SELECT * FROM file_publications WHERE state='intent'"))
        self.assertIsNone(self.store.one('SELECT processed_at FROM events WHERE id=?',(source['id'],))['processed_at'])
        self.assertIsNone(self.store.one('SELECT processed_at FROM events WHERE id=?',(handoff,))['processed_at'])
        self.preserve(before)


if __name__ == '__main__':
    unittest.main()
