"""Combined protocol consequences; isolated fiction, never live/real24h proof.

Actual production collection/classification/control, whole frontier, job/epoch,
retirement and bind paths run. NULL-native synthetic results, simulated clocks
and explicit conserved-shared-custody seams supply no actual custodian consent.
"""
import copy
import json
import unittest
from unittest.mock import patch

from coordinator_runtime import capacity, processing, prospective, retirement, windows
from coordinator_runtime.cleanup import sweep
from coordinator_runtime.contracts import Refusal, digest, encode
import test_alert_phase340 as alerts
import test_job_birth342 as jobs
import test_response_birth337 as events


class Combined(unittest.TestCase):
    def setUp(self):
        self.n = alerts.Notifications(methodName='runTest')
        self.addCleanup(self.n.doCleanups)
        self.n.setUp()
        self.s, self.f, self.c = self.n.s, self.n.f, self.n.c
        # Genuine fixture selection, rather than editing an issued capability.
        # These cases need later useful input; the producer's pause test remains
        # separately selected unchanged with its own one-input admission bound.
        processing.revoke(self.s, self.f.boards, self.n.key)
        self.n.key = self.c.issue(self.c.selection(max_windows=8))
        self.key = self.n.key
        self.j = jobs.JobBirth(methodName='runTest')
        self.j.c, self.j.s, self.j.f, self.j.key = self.c, self.s, self.f, self.key
        self.j.h = events.Birth(methodName='runTest')
        self.j.h.c, self.j.h.s, self.j.h.f, self.j.h.key = self.c, self.s, self.f, self.key

    def receipt(self, root):
        current = retirement.basis(self.s, root)
        result = {'basis':current['basis'], 'qualified_at':self.s.clock(),
                  'holds':{h:[] for h in capacity.HOLDS},
                  'evidence':'fictional all original custodians conserve exact source/results; no actual consent'}
        for name in ('sources','results','occurrences'):
            if name == 'occurrences' and not current.get(name):
                continue
            result[name] = {key:{'hash':value, 'custodian':'fictional-original-custodian',
                                 'evidence':'synthetic exact conservation only',
                                 'disposition':'conserved-at-original-source'} for key,value in current[name].items()}
        return result

    def snap(self):
        return {r['name']:self.s.rows('SELECT * FROM "'+r['name']+'"') for r in
                self.s.rows("SELECT name FROM sqlite_master WHERE type='table'")}

    def group(self, complete=True):
        due, outboxes = self.n.capture()
        self.assertGreater(len(due),32)
        row = outboxes[0]
        event = self.n.consume(row) if complete else self.n.address(row)
        return due, row, event

    def conserve_shared(self, row):
        # Explicit private seam for the independent shared-custody protocol.
        # No shared Board/native row is deleted or claimed qualified here.
        self.s.db.execute("INSERT INTO shared_custody_intents VALUES(?,?,?,'retired',?)",
            (row['id'],'/fixtures/fictional-conserved-envelope',digest(row),encode({'fixture':'synthetic closed shared custody'})))

    def aged(self, row):
        self.n.now=88000.
        sweep(self.s)
        self.conserve_shared(row)

    def refuse_unchanged(self, root, receipt=None):
        before=self.snap()
        with self.assertRaises(Refusal):
            retirement.apply(self.s,root,'fictional-Work',receipt or self.receipt(root))
        self.assertEqual(self.snap(),before,'refusal must retain the complete original cohort and charges')

    def test_full_group_retirement_and_future_alert_event_job_epoch_authority(self):
        old_jobs=[]
        for n in range(3):
            source,job,attempt=self.j.new_job('fictional-combined-old-'+str(n))
            self.j.complete(job,attempt);old_jobs.append((source,job))
        due,rows=self.n.capture()
        consumers=[self.n.consume(r) for r in rows]
        row,event=rows[0],consumers[0]
        members=json.loads(row['payload'])['occurrences']
        self.aged(row)
        for other in rows[1:]:
            self.conserve_shared(other)
        self.j.epoch()
        epoch=self.j.epoch_row
        charges=self.s.rows('SELECT * FROM service_windows')
        frontier=processing.source_boundary(self.s)
        alert_frontier=self.s.one('SELECT MAX(rowid) AS n FROM alerts')['n']
        before={r['id']:r for r in self.s.rows('SELECT * FROM alerts') if r['id'] not in {m['id'] for m in members}}
        receipt=self.receipt(event['id'])
        retired=retirement.apply(self.s,event['id'],'fictional-Work',receipt)
        self.assertEqual(set(receipt['occurrences']),{m['id'] for m in members})
        self.assertEqual(set(retired['retired']['members']['occurrences']),set(receipt['occurrences']))
        for source,job in old_jobs:
            retirement.apply(self.s,source['id'],'fictional-Work',self.receipt(source['id']))
            self.assertIsNone(self.s.one('SELECT * FROM prospective_job_positions WHERE job=?',(job['id'],)))
        self.assertEqual(self.s.rows('SELECT * FROM service_windows'),charges,'retirement refunds no charges')
        self.assertEqual(processing.source_boundary(self.s),frontier)
        self.assertEqual(self.s.one('SELECT * FROM prospective_authorities WHERE id=?',(self.j.selected['id'],)),epoch)
        self.assertIsNone(self.s.one('SELECT * FROM events WHERE id=?',(event['id'],)))
        self.assertIsNone(self.s.one('SELECT * FROM outboxes WHERE id=?',(row['id'],)))
        self.assertEqual({r['id']:r for r in self.s.rows('SELECT * FROM alerts')},before)
        for other in consumers[1:]:
            retirement.apply(self.s,other['id'],'fictional-Work',self.receipt(other['id']))
        self.assertEqual(self.s.rows('SELECT * FROM alerts'),[])
        self.assertEqual(self.s.rows('SELECT * FROM service_windows'),charges)
        self.n.conserved()
        source,job,attempt=self.j.new_job('fictional-combined-new-job')
        physical=self.s.one('SELECT rowid AS n FROM jobs WHERE id=?',(job['id'],))['n']
        logical=self.s.one('SELECT position FROM prospective_job_positions WHERE job=?',(job['id'],))['position']
        self.assertLessEqual(physical,self.j.selected['job_boundary'])
        self.assertGreater(logical,self.j.selected['job_boundary'])
        self.assertTrue(prospective.requires_authority(self.s,self.s.job(job['id'])))
        self.assertEqual(prospective.for_job(self.s,self.s.job(job['id']))['id'],self.j.selected['id'])
        self.j.complete(job,attempt)
        fresh,new_rows=self.n.capture()
        self.assertTrue(fresh)
        self.assertTrue({m['id'] for m in due}.isdisjoint({m['id'] for m in fresh}))
        self.assertTrue(all(r['n']>alert_frontier for r in self.s.rows('SELECT rowid AS n FROM alerts WHERE created=88000')))
        later=self.n.consume(new_rows[0])
        self.assertGreater(prospective.event_position(self.s,later['id'],{'selection':{'processing_capability':self.key}}),frontier)
        self.assertEqual(self.s.one('SELECT * FROM prospective_authorities WHERE id=?',(self.j.selected['id'],)),epoch)
        self.n.conserved()
        print('combined fiction: retired',len(members),'full alert occurrences; physical job',physical,
              'logical birth',logical,'beyond',self.j.selected['job_boundary'],'fresh control remains available')

    def test_partial_young_and_pending_shared_custody_refuse(self):
        _,row,event=self.group(complete=False)
        self.n.now=88000.
        self.refuse_unchanged(event['id'])
        # Completion now is young even though enqueue/ACK had ample fictional age.
        self.n.consume(row,event)
        sweep(self.s)
        self.refuse_unchanged(event['id'])
        self.n.now+=86400.
        sweep(self.s)
        self.refuse_unchanged(event['id'])  # Separate shared custody still missing.
        self.n.conserved()

    def test_every_hold_missing_occurrence_and_changed_basis_refuse(self):
        _,row,event=self.group();self.aged(row)
        good=self.receipt(event['id'])
        for hold in capacity.HOLDS:
            receipt=copy.deepcopy(good);receipt['holds'][hold]=['fictional original hold']
            self.refuse_unchanged(event['id'],receipt)
        receipt=copy.deepcopy(good);receipt['occurrences'].pop(next(iter(receipt['occurrences'])))
        self.refuse_unchanged(event['id'],receipt)
        receipt=copy.deepcopy(good);receipt['qualified_at']-=61
        self.refuse_unchanged(event['id'],receipt)
        occurrence=json.loads(row['payload'])['occurrences'][-1]['id']
        with self.assertRaises(Refusal):capacity.retirement_basis(self.s,occurrence)
        self.s.db.execute('UPDATE alerts SET processed_at=? WHERE id=?',(self.n.now,occurrence))
        self.refuse_unchanged(event['id'],good)  # Stale receipt.
        self.refuse_unchanged(event['id'])       # Fresh receipt cannot waive youth.
        self.n.conserved()

    def test_uncertain_control_source_membership_and_capability_refuse(self):
        _,row,event=self.group();self.aged(row)
        original=self.s.one('SELECT * FROM outboxes WHERE id=?',(row['id'],))
        saved=json.loads(original['board_receipt'])
        for changes in ({'control_receipt':{'pending':True}}, {'processing':None},
                        {'transport':{'route':'queue','delivery_state':'acknowledged','queue_message_id':'fictional-unproven'}}):
            self.s.db.execute('UPDATE outboxes SET board_receipt=? WHERE id=?',(encode({**saved,**changes}),row['id']))
            self.refuse_unchanged(event['id'])
        self.s.db.execute('UPDATE outboxes SET board_receipt=? WHERE id=?',(original['board_receipt'],row['id']))
        link=self.s.one('SELECT * FROM alert_delivery_members WHERE delivery=? ORDER BY occurrence',(row['id'],))
        self.s.db.execute("UPDATE alert_delivery_members SET source_hash='fictional-mismatch' WHERE occurrence=?",(link['occurrence'],))
        self.refuse_unchanged(event['id'])
        self.s.db.execute('UPDATE alert_delivery_members SET source_hash=? WHERE occurrence=?',(link['source_hash'],link['occurrence']))
        alert=self.s.one('SELECT * FROM alerts WHERE id=?',(link['occurrence'],))
        body=json.loads(alert['payload']);body['processing_capability']='fictional-foreign-origin'
        self.s.db.execute('UPDATE alerts SET payload=? WHERE id=?',(encode(body),link['occurrence']))
        self.refuse_unchanged(event['id'])
        self.s.db.execute('UPDATE alerts SET payload=? WHERE id=?',(alert['payload'],link['occurrence']))
        self.s.record_operational_error(link['occurrence'],{'error':'fictional old effect uncertainty'})
        self.refuse_unchanged(event['id'])
        self.s.clear_operational_error(link['occurrence'])
        with self.s.tx():
            self.s._outbox('Work','Work','alert',json.loads(alert['payload']),alert=link['occurrence'])
        self.refuse_unchanged(event['id'])  # An extra source delivery shares this occurrence.
        self.n.conserved()

    def test_current_origin_exact_debt_keeps_whole_group_custody_until_retirement(self):
        self.s.record_operational_error('fictional-persistent-original-cause',{'error':'fictional unchanged real fixture violation'})
        cause=self.s.one('SELECT * FROM operational_errors WHERE subject=?',('fictional-persistent-original-cause',))
        real_budget=self.s.budget
        def pressure(kind, *args, **kwargs):
            if kind=='alerts':
                from coordinator_runtime.contracts import Backpressure
                raise Backpressure('fictional alert-count pressure; exact debt space still admitted')
            return real_budget(kind,*args,**kwargs)
        with patch.object(self.s,'budget',side_effect=pressure):
            self.assertEqual(capacity.capture(self.s),[])
        originals=self.s.rows('SELECT * FROM alert_debt ORDER BY id')
        self.assertGreater(len(originals),32)
        while capacity.deliver_pending(self.s):
            pass
        rows=self.s.rows("SELECT * FROM outboxes WHERE alert IS NOT NULL ORDER BY id")
        represented=[m for r in rows for m in json.loads(r['payload'])['occurrences']]
        self.assertEqual(sorted(represented,key=lambda r:r['id']),[json.loads(r['payload']) for r in originals])
        consumers=[self.n.consume(r) for r in rows]
        self.n.now=88000.;sweep(self.s)
        for row,event in zip(rows,consumers):
            self.conserve_shared(row)
            retirement.apply(self.s,event['id'],'fictional-Work',self.receipt(event['id']))
        self.assertEqual(self.s.rows('SELECT * FROM alert_debt'),[])
        self.assertEqual(self.s.rows('SELECT * FROM alerts'),[])
        self.assertEqual(self.s.one('SELECT * FROM operational_errors WHERE subject=?',('fictional-persistent-original-cause',)),cause)
        self.n.conserved()


if __name__=='__main__':unittest.main(verbosity=2)
