"""Fresh fictional jobs and owner testimony; no provider or live runtime."""
import copy
import sqlite3
import tempfile
from pathlib import Path
import unittest

from support import config_at, enrolled, event, queued, collect, result
from coordinator_runtime import local_integration as local
from coordinator_runtime.contracts import Refusal, encode


class ReadFenceCapacity869(unittest.TestCase):
    def setUp(self):
        self.home = Path(tempfile.mkdtemp(prefix='capacity869-'))
        self.config = config_at(self.home)
        self.target = self.home / 'points.json'
        self.target.write_text(encode({str(i): {'state': 'held'} for i in range(6)}))
        points = {str(i): {'kind': 'item', 'line': 'fiction869', 'incarnation': 'fiction869',
            'bindings': [{'target': str(self.target), 'path': [str(i)]}],
            'resources': [], 'protected': [], 'writable': ['state']} for i in range(6)}
        self.config['local_integration'] = {'max_inflight': 8, 'points': points, 'tasks': {
            'work-proposer': {'capacity': 5, 'discovery_batch': 1, 'points': list(points),
                'authority': 'Fictional current owner: isolated read proposals only',
                'method': self.config['tasks']['work-proposer']['templates'][0]}}}
        self.store = enrolled(self.config)
        self.addCleanup(self.store.close)
        self.owner = self.config['roles']['Work']['owner']
        self.old = []
        for i in range(5):
            self.enqueue(i)
            job = self.store.reserve()
            self.assertIsNotNone(job)
            attempt = self.store.start_job(job['id'], job['token'])
            collect(self.store, attempt, result('UNKNOWN' if i % 2 else 'PARTIAL', 'proposal'),
                    capture='artifact-inventory-incomplete' if i % 2 else 'complete')
            self.store.db.execute("UPDATE jobs SET state='held',effects='none',hold_reason=? WHERE id=?",
                                  ('Fictional adverse outcome remains owned', job['id']))
            self.store.db.execute('INSERT INTO outboxes(id,role,job,producer,recipient,kind,required,payload,state,created) '
                'VALUES(?,?,?,?,?,?,?,?,?,?)', ('fictional-outbox869-' + str(i), 'Work', job['id'],
                self.store.controller, 'Work', 'question', 'settled', '{"fictional":"unresolved"}', 'sent', 6.))
            self.store.db.execute('INSERT INTO artifact_custody(attempt,path,kind,owner,witness,sha256) '
                'VALUES(?,?,?,?,?,?)', (attempt, 'fictional-unacquired869', 'report',
                'fictional-original-custodian869', '{}', 'fictional869'))
            self.old.append(self.store.job(job['id']))
        self.incoming = self.enqueue(5)

    def enqueue(self, index):
        source = event(self.config, 'capacity869-' + str(index), task='work-proposer')
        key = str(index)
        source['integration'] = {'reads': [key], 'writes': [], 'versions': {
            key: local.version(self.store, key, {str(self.target): self.target.read_bytes()})}}
        queued(self.store, source)
        return source

    def fence(self, job):
        basis = self.store.work_read_metadata_closure_basis(job['id'], job['token'], self.owner)
        receipt = {'basis': basis, 'reason': 'Fictional original writers closed; adverse duties retained',
            'controllers': [{'controller': c, 'collector': 'fictional-original-collector869',
                'end': 0, 'collected': True, 'writers_closed': True,
                'evidence': ['Fictional actual original collection and all launch-capable writers closed']}
                for c in basis['controllers']]}
        self.store.fence_work_proposer_metadata(job['id'], job['token'], self.owner, receipt)

    def originals(self):
        ids = {j['id'] for j in self.old}
        tables = ('jobs', 'attempts', 'results', 'events', 'queue', 'outboxes',
                  'source_custody', 'artifact_custody', 'file_publications',
                  'recovery_requests', 'recovery_dispositions')
        return {t: [r for r in self.store.rows('SELECT * FROM ' + t + ' ORDER BY rowid')
                    if t not in {'jobs', 'queue'} or r.get('job', r.get('id')) in ids]
                for t in tables}

    def test_five_permanently_fenced_readers_allow_actual_independent_reservation(self):
        self.assertIsNone(self.store.reserve())
        outcome = self.store.one('SELECT predicate,outcome FROM reservation_outcomes WHERE event=?',
                                 (self.incoming['id'],))
        self.assertEqual(outcome, {'predicate': 'execution-capacity', 'outcome': 'false'})
        before = self.originals()
        for job in self.old:
            self.fence(job)
        self.assertEqual(before, self.originals())
        fresh = self.store.reserve()
        self.assertIsNotNone(fresh)
        self.assertEqual(self.store.job(self.old[0]['id'])['state'], 'held')
        for job in self.old:
            for action, args in ((self.store.start_job, (job['id'], job['token'])),
                    (self.store.finish_job, (job['id'], job['token'])),
                    (self.store.request_recovery, (job['id'], job['token'], job['active_attempt'], self.owner, {}))):
                with self.assertRaisesRegex(Refusal, 'execution retired'):
                    action(*args)
        self.assertEqual(self.originals()['jobs'], before['jobs'])
        for table in ('attempts', 'results', 'events', 'outboxes', 'source_custody', 'artifact_custody'):
            self.assertEqual(self.originals()[table], before[table], table)
        self.assertTrue(all(r['processed_at'] is None for r in self.store.rows('SELECT processed_at FROM events')))

    def test_permanent_slot_release_survives_prospective_configuration_change(self):
        for job in self.old:
            self.fence(job)
        changed = copy.deepcopy(self.config)
        changed['tasks']['work-proposer']['purpose'] += ' Prospective independent purpose.'
        self.store.config = changed
        self.assertTrue(all(self.store.execution_complete(self.store.job(j['id'])) for j in self.old))
        self.assertIsNotNone(self.store.reserve())

    def test_unfenced_and_unqualified_jobs_stay_charged(self):
        job = self.old[0]
        for sql in ("UPDATE jobs SET state='running' WHERE id=?",
                    "UPDATE jobs SET effects='unknown' WHERE id=?",
                    "UPDATE attempts SET collected=NULL WHERE job=?",
                    "UPDATE attempts SET ended=NULL WHERE job=?"):
            with self.subTest(sql=sql):
                saved = sqlite3.connect(':memory:')
                self.store.db.backup(saved)
                try:
                    self.store.db.execute(sql, (job['id'],))
                    self.assertFalse(self.store.execution_complete(self.store.job(job['id'])))
                    with self.assertRaises(Refusal):
                        self.fence(job)
                    self.assertIsNone(self.store.reserve())
                finally:
                    saved.backup(self.store.db)
                    saved.close()
        self.assertFalse(self.store.execution_complete(self.store.job(job['id'])))
        self.assertIsNone(self.store.reserve())

    def test_shared_resource_still_refuses_after_execution_release(self):
        for job in self.old:
            self.fence(job)
        self.config['local_integration']['points']['5']['resources'] = ['fictional-shared869']
        self.store.db.execute('INSERT INTO ordinary_resources(resource,attempt) VALUES(?,?)',
                              ('fictional-shared869', self.old[0]['active_attempt']))
        self.assertIsNone(self.store.reserve())
        outcome = self.store.one('SELECT predicate,outcome FROM reservation_outcomes WHERE event=?',
                                 (self.incoming['id'],))
        self.assertEqual(outcome, {'predicate': 'local-ordinary-busy', 'outcome': 'false'})


class Kernel869(unittest.TestCase):
    def test_source_and_sdk_writes_are_denied(self):
        for path in (Path('/src/tools/coordinator-runtime/coordinator_runtime/store.py'),
                     Path('/src/tools/message-board/board_store.py'),
                     Path('/src/tools/coordinator-runtime/tests/fixture_snapshot/retention.py')):
            with self.subTest(path=str(path)), self.assertRaises(OSError):
                with path.open('ab') as stream:
                    stream.write(b'forbidden')


if __name__ == '__main__':
    unittest.main(verbosity=2)
