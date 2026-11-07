"""Public finite QA routes with actual gated ordinary child execution.

SDK identity and model answers use the existing explicit fiction seams. Gates
are ordinary admitted files; clocks, acceptance and positive journal rows are
never forged. Every gate is released and every owned task collected in finally.
"""
import asyncio
import copy
import json
import time
import unittest

from test_qa629_repairs import Fixture, actor, sha
from test_software_routes643 import SoftwareRoutes643
from support import result
from coordinator_runtime import ordinary, prospective, resource_scopes, report_scope
from coordinator_runtime.contracts import Refusal, digest, encode


class QASlots50102(Fixture, unittest.IsolatedAsyncioTestCase):
    asyncSetUp = SoftwareRoutes643.asyncSetUp
    source = SoftwareRoutes643.source
    prepared = SoftwareRoutes643.prepared
    execute = SoftwareRoutes643.execute
    cleanup = SoftwareRoutes643.cleanup
    select_software = SoftwareRoutes643.select_software

    def configure(self):
        self.package_count = 7 if 'five_execution' in self._testMethodName else 5
        SoftwareRoutes643.configure(self)

    def package(self, i):
        SoftwareRoutes643.package(self, i)
        key = f'future-qa-{i}'
        entry = self.packages[key]
        root = entry['repo'].parent
        gate = root/'out'/'release'
        active = root/'out'/'active'
        runner = root/'runner.py'
        runner.write_text(
            'from pathlib import Path\nimport time, os\n'
            f'Path({str(active)!r}).write_text(str(os.getpid()))\n'
            'deadline=time.monotonic()+20\n'
            f'while not Path({str(gate)!r}).exists():\n'
            '    assert time.monotonic()<deadline, "owned gate deadline"\n'
            '    time.sleep(0.01)\n' + runner.read_text())
        p = entry['p'];p['timeout'] = 30
        p['command']['script_sha256'] = sha(runner)
        operation = self.operations[-1]
        operation['policy']['inputs'] = [dict(path=x['path'],sha256=sha(x['path'])) for x in operation['policy']['inputs']]
        if i == 2 and 'overlap' in self._testMethodName:
            # An actually admitted shared read operand belongs to B's frozen
            # unresolved effect scope; package labels cannot declare it disjoint.
            entry['scope']['task_scopes']['qa-execution']['read_roots'].append(
                str(self.packages['future-qa-1']['repo'].parent/'procedure.md'))
        operation['binding']['scope_sha256'] = digest(entry['scope'])
        entry.update(gate=gate,active=active)
        # Ordinary sequential calls run immediately; active tests unlink only
        # their own exact gate before any source intake or execution.
        gate.write_text('released before execution')

    async def active(self, key):
        entry = self.packages[key]
        entry['gate'].unlink()
        job = self.store.reserve()
        self.assertIsNotNone(job);self.assertEqual(job['package'],key)
        job,attempt = self.prepared(job,result(category='consolidated'))
        work = asyncio.create_task(ordinary.perform(self.store,self.boards['QA'],job))
        self.running.append((entry,work,job,attempt))
        deadline = time.monotonic()+10
        while not entry['active'].exists():
            if work.done():await work
            self.assertLess(time.monotonic(),deadline,'actual QA runner did not reach gate')
            await asyncio.sleep(.01)
        self.assertFalse(work.done())
        self.assertEqual(self.store.one('SELECT state FROM ordinary_runs WHERE attempt=?',(attempt,))['state'],'intent')
        self.assertEqual(self.store.job(job['id'])['effects'],'unknown')
        return job,attempt,work

    async def release(self):
        for entry,work,job,attempt in self.running:
            entry['gate'].write_text('actual owner releases admitted fixture gate')
        outcomes = await asyncio.gather(*(w for _,w,_,_ in self.running),return_exceptions=True)
        self.assertTrue(all(x is True for x in outcomes),repr(outcomes))

    def note(self, name, **data):
        with (self.area/'concurrency.jsonl').open('a') as out:
            out.write(encode(dict(name=name,at=time.time(),**data))+'\n')

    async def test_accepted_A_cleanup_reserves_while_disjoint_B_really_executes(self):
        a,b = 'future-qa-1','future-qa-2'
        source = self.source(a)
        _,aa,response = await self.execute(a)
        self.assertTrue(ordinary.accepted_package(self.store,a))
        self.classify()
        self.source(b)
        # Hold only this already queued cleanup to start B via normal reserve.
        self.store.set_hold(response,'Owned fixture starts disjoint execution first')
        self.running=[]
        try:
            bj,ba,work = await self.active(b)
            self.store.set_hold(response,None)
            q = self.store.one('SELECT * FROM queue WHERE event=?',(response,))
            self.assertFalse(resource_scopes.blocked(self.store,q))
            before = self.store.event(response)
            cleanup = self.store.reserve()
            self.note('cleanup-A-versus-active-B',cleanup=cleanup,B=self.store.job(bj['id']),
                      B_attempt=ba,A_attempt=aa,accepted=ordinary.accepted_runs(self.store,a))
            self.assertIsNotNone(cleanup,'global QA phase barrier refused authentic accepted A while disjoint B executes')
            self.assertEqual(cleanup['task'],'qa-cleanup');self.assertEqual(cleanup['package'],a)
            self.assertFalse(work.done())
            answer=result(category='qualification')
            answer['findings'].append(dict(collected_reports=report_scope.conserved_inputs(self.store,cleanup)))
            cj,ca=self.prepared(cleanup,answer)
            await ordinary.qualification(self.store,cj)
            routed=self.store.finish_job(cj['id'],cj['token'])
            self.assertEqual(self.store.event(routed)['role'],'Branch')
            self.assertEqual(self.store.event(routed)['body'],answer)
            self.assertEqual(answer['findings'][-1]['collected_reports'][0]['original'],before['body'])
            self.assertEqual(self.store.event(response),before)
            self.assertIsNone(self.store.one('SELECT processed_at FROM events WHERE id=?',(source['id'],))['processed_at'])
            self.assertFalse(work.done());self.assertEqual(self.store.job(bj['id'])['effects'],'unknown')
        finally:
            await self.release()

    async def test_five_execution_plus_one_cleanup_and_sixth_waits_actual_slot(self):
        a='future-qa-1';self.source(a)
        _,_,response=await self.execute(a);self.classify()
        cleanup=self.store.reserve();self.assertIsNotNone(cleanup)
        self.assertEqual(cleanup['task'],'qa-cleanup')
        self.running=[]
        try:
            for i in range(2,7):
                key=f'future-qa-{i}';self.source(key);await self.active(key)
            self.source('future-qa-7')
            q=self.store.one("SELECT * FROM queue WHERE package='future-qa-7'")
            self.assertFalse(resource_scopes.blocked(self.store,q))
            self.assertEqual(len(self.running),5)
            self.assertTrue(all(not w.done() for _,w,_,_ in self.running))
            self.assertIsNone(self.store.reserve())
            self.assertIsNone(self.store.one('SELECT job FROM queue WHERE id=?',(q['id'],))['job'])
            self.note('five-execution-one-cleanup-sixth-waits',jobs=[self.store.job(j['id']) for _,_,j,_ in self.running],cleanup=cleanup,waiting=q)
            # Free exactly one execution slot through actual tool END/collection
            # and ordinary finish; cleanup continues to hold its separate slot.
            entry,work,job,attempt=self.running[0]
            entry['gate'].write_text('release one real execution')
            self.assertTrue(await work)
            self.store.finish_job(job['id'],job['token'])
            sixth=self.store.reserve();self.assertIsNotNone(sixth)
            self.assertEqual(sixth['package'],'future-qa-7')
            self.assertEqual(self.store.job(cleanup['id'])['state'],'reserved')
            self.assertTrue(all(not w.done() for _,w,_,_ in self.running[1:]))
        finally:
            await self.release()

    async def test_second_accepted_cleanup_waits_its_one_slot(self):
        responses=[]
        for key in ['future-qa-1','future-qa-2']:
            self.source(key)
        for key in ['future-qa-1','future-qa-2']:
            _,_,r=await self.execute(key);responses.append(r)
        self.classify();first=self.store.reserve()
        self.assertEqual(first['task'],'qa-cleanup')
        q=self.store.one('SELECT * FROM queue WHERE event=?',(responses[1],))
        self.assertFalse(resource_scopes.blocked(self.store,q))
        self.assertIsNone(self.store.reserve())
        answer=result(category='qualification')
        answer['findings'].append(dict(collected_reports=report_scope.conserved_inputs(self.store,first)))
        job,_=self.prepared(first,answer);await ordinary.qualification(self.store,job)
        self.store.finish_job(job['id'],job['token'])
        second=self.store.reserve();self.assertEqual(second['package'],'future-qa-2')
        self.note('second-cleanup-waits-and-resumes',first=first,second=second)

    async def test_current_source_ref_and_authority_still_fence_cleanup(self):
        key='future-qa-1';self.source(key);_,_,r=await self.execute(key);self.classify()
        q=self.store.one('SELECT * FROM queue WHERE event=?',(r,))
        self.assertFalse(resource_scopes.blocked(self.store,q))
        self.repo=self.packages[key]['repo'];head=self.packages[key]['head']
        tree=self.git('rev-parse','HEAD^{tree}')
        changed=self.git('-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit-tree',tree,'-p',head,'-m','new source')
        self.git('update-ref','refs/heads/source',changed,head)
        self.assertTrue(resource_scopes.blocked(self.store,q));self.assertIsNone(self.store.reserve())
        self.git('update-ref','refs/heads/source',head,changed)
        self.assertFalse(resource_scopes.blocked(self.store,q))
        prospective.revoke(self.store,self.issuer,self.epoch['id'])
        self.assertTrue(resource_scopes.blocked(self.store,q));self.assertIsNone(self.store.reserve())

    async def test_actual_overlap_still_blocks_accepted_cleanup(self):
        a,b='future-qa-1','future-qa-2'
        self.source(a);_,_,r=await self.execute(a);self.classify();self.source(b)
        self.store.set_hold(r,'Owned ordering fixture')
        self.running=[]
        try:
            bj,_,work=await self.active(b)
            self.store.set_hold(r,None)
            q=self.store.one('SELECT * FROM queue WHERE event=?',(r,))
            self.assertTrue(ordinary.accepted_package(self.store,a))
            self.assertTrue(resource_scopes.blocked(self.store,q))
            self.assertIsNone(self.store.reserve())
            self.assertFalse(work.done());self.assertEqual(self.store.job(bj['id'])['effects'],'unknown')
            self.note('overlap-retains-accepted-cleanup',B=bj,cleanup=q)
        finally:
            await self.release()

    async def test_unmapped_unknown_retains_accepted_cleanup(self):
        key='future-qa-1';self.source(key);_,_,r=await self.execute(key);self.classify()
        q=self.store.one('SELECT * FROM queue WHERE event=?',(r,))
        self.assertFalse(resource_scopes.blocked(self.store,q))
        # Negative-only fictional unknown lease, never positive reachability.
        self.store.db.execute("INSERT INTO ordinary_resources VALUES('unmapped-50102','fictional-unknown')")
        self.assertTrue(resource_scopes.blocked(self.store,q));self.assertIsNone(self.store.reserve())
        self.assertEqual(self.store.rows('SELECT * FROM ordinary_resources'),
                         [dict(resource='unmapped-50102',attempt='fictional-unknown')])
        self.assertTrue(ordinary.accepted_package(self.store,key))

    async def test_revoked_current_grant_independently_blocks_accepted_cleanup(self):
        key='future-qa-1';self.source(key);_,_,r=await self.execute(key);self.classify()
        q=self.store.one('SELECT * FROM queue WHERE event=?',(r,))
        self.assertFalse(resource_scopes.blocked(self.store,q))
        self.assertEqual(self.store.rows('SELECT * FROM ordinary_resources'),[])
        with actor(self.boards['QA'].store,self.issuer):
            self.boards['QA'].revoke_software(self.store,self.store.enrollment('QA')['grant_id'])
        self.assertIsNone(self.store.reserve())
        self.assertTrue(ordinary.accepted_package(self.store,key))

    async def test_finite_account_bound_and_duplicate_package_remain(self):
        record=copy.deepcopy(self.selection['service']['legacy_resources']['QA'])
        record['qa_operations'] = (record['qa_operations'] * 2)[:8]
        with self.assertRaises(Refusal):resource_scopes.qa_accounts(record)
        record['qa_operations']=record['qa_operations'][:2]
        record['qa_operations'][1]=copy.deepcopy(record['qa_operations'][0])
        with self.assertRaisesRegex(Refusal,'distinct packages'):resource_scopes.validate(self.store,{'QA':record})
