"""Fictional owned artifacts only; retained fixtures, no runtime/native cleanup."""
import errno
import hashlib
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from support import config_at, enrolled
from coordinator_runtime.store import Store
from coordinator_runtime import cleanup
from coordinator_runtime.contracts import encode, Refusal


class Retention837(unittest.TestCase):
    def setUp(self):
        self.directory = Path(tempfile.mkdtemp(prefix='retention837-'))
        self.config = config_at(self.directory)
        self.now = 100000.0
        self.store = enrolled(self.config, clock=lambda: self.now)
        self.addCleanup(lambda: self.store.close())
        self.source('source', 100000.0)

    def source(self, key, processed, parent=None):
        self.store.db.execute('INSERT INTO events(id,role,payload,hash,received,state,ack,parent,processed_at) VALUES(?,?,?,?,?,?,?,?,?)',
            (key, 'Work', '{}', hashlib.sha256(key.encode()).hexdigest(), 1, 'processed', 'internal', parent, processed))
        self.store.db.execute("INSERT INTO queue(id,event,role,phase,task,state) VALUES(?,?,?,?,?,'done')",
                              ('q-'+key,key,'Work','integrator','work-integrator'))

    def owned(self, name='one'):
        job, attempt = 'job-'+name, 'attempt-'+name
        self.store.db.execute("INSERT INTO jobs(id,role,phase,task,members,controller,token,created,state,effects,closed_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (job,'Work','integrator','work-integrator',encode([{'event':'source'}]),'fictional','fictional',1,'closed','none',100000))
        self.store.db.execute('UPDATE queue SET job=? WHERE event=?',(job,'source'))
        self.store.db.execute("INSERT INTO attempts(id,kind,job,controller,profile,binding,created,ended,collected,cleanup,state) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (attempt,'task',job,'fictional','.codex5','{}',1,2,3,'done','collected'))
        root=self.store.home/'artifacts'/attempt;root.mkdir(parents=True)
        target=root/'fictional.txt';target.write_text('owned fictional evidence '+name)
        cleanup.register_artifact(self.store,attempt,target)
        cleanup.conserve(self.store,target,self.config['roles']['Work']['owner'],{'fictional':'durable consumer custody'})
        return self.row(target)

    def row(self, target):
        return self.store.one('SELECT * FROM artifacts WHERE path=?',(str(target),))

    def eligible(self):
        return cleanup.eligible_event(self.store,self.store.one('SELECT * FROM events WHERE id=?',('source',)))

    def test_immutable_clock_hold_clear_restart_and_unknown(self):
        self.now=186399; self.assertFalse(self.eligible())
        self.store.set_hold('source','actual consumer');self.now=186400
        self.assertFalse(self.eligible());self.store.set_hold('source',None)
        self.assertEqual(self.store.one('SELECT processed_at FROM events')['processed_at'],100000)
        self.store.close();self.store=Store(self.config,clock=lambda:self.now)
        self.assertTrue(self.eligible())
        self.source('unknown',None)
        self.store.set_hold('unknown','unknown original');self.store.set_hold('unknown',None)
        self.assertIsNone(self.store.one("SELECT processed_at FROM events WHERE id='unknown'")['processed_at'])
        self.assertFalse(cleanup.eligible_event(self.store,self.store.one("SELECT * FROM events WHERE id='unknown'")))

    def test_new_dependent_and_reopened_work_keep_source(self):
        self.now=300000;self.source('new-generation',None,'source');self.assertFalse(self.eligible())
        # Actual completion procedure, not ACK/DONE/process-END, stamps the new work.
        self.store.complete_events()
        self.assertEqual(self.store.one("SELECT processed_at FROM events WHERE id='new-generation'")['processed_at'],300000)
        self.now=386399;self.assertFalse(self.eligible());self.now=386400;self.assertTrue(self.eligible())
        self.store.db.execute("UPDATE queue SET state='queued' WHERE event='new-generation'")
        self.assertFalse(self.eligible())
        self.assertEqual(self.store.one("SELECT processed_at FROM events WHERE id='source'")['processed_at'],100000)

    def test_late_exclusion_origin_and_hold_before_all_path_io(self):
        row=self.owned();self.now=200000
        origin='/fictional-opaque/original.txt'
        self.store.db.execute('INSERT INTO artifact_custody VALUES(?,?,?,?,?,?)',
            ('owner:fictional',origin,'role-owned','fictional',encode({'sha256':row['sha256'],'size':row['size']}),row['sha256']))
        self.config['artifact_exclusions']=['/fictional-opaque']
        def trap(*a,**k):raise AssertionError('excluded path I/O')
        with patch.object(Path,'is_symlink',trap),patch.object(Path,'stat',trap),patch.object(Path,'lstat',trap),patch.object(os,'stat',trap),patch.object(os,'open',trap),patch.object(os,'unlink',trap),patch.object(cleanup,'hash_fd',trap):
            result=cleanup.retire_artifact(self.store,row)
        self.assertEqual(result['state'],'partial-held');self.assertEqual(result['error'],'Refusal')
        # Clearing a compatible consumer hold cannot waive retained-origin policy.
        self.store.set_hold('source','provenance clarification');self.store.set_hold('source',None)
        self.assertEqual(cleanup.retire_artifact(self.store,row)['state'],'partial-held')
        other=self.owned('unrelated');self.assertEqual(cleanup.retire_artifact(self.store,other)['state'],'removed')

    def test_direct_exclusion_and_new_hold_during_hash(self):
        row=self.owned();self.now=200000
        self.config['artifact_exclusions']=[row['path']]
        with patch.object(Path,'is_symlink',side_effect=AssertionError('metadata')):
            self.assertEqual(cleanup.retire_artifact(self.store,row)['error'],'Refusal')
        # Distinct candidate: late policy change after hashing is fenced too.
        other=self.owned('late');original=cleanup.digest_at
        def late(*args):
            sha=original(*args);self.config['artifact_exclusions'].append(other['path']);return sha
        with patch.object(cleanup,'digest_at',side_effect=late),patch.object(os,'unlink',side_effect=AssertionError('unlink')):
            self.assertEqual(cleanup.retire_artifact(self.store,other)['error'],'Refusal')

    def test_every_existing_lifecycle_refusal_and_once_only(self):
        row=self.owned();self.now=186399
        self.assertEqual(cleanup.retire_artifact(self.store,row)['state'],'held');self.now=186400
        self.store.db.execute('UPDATE jobs SET closed_at=200000')
        self.now=286399;self.assertEqual(cleanup.retire_artifact(self.store,row)['state'],'held')
        self.now=286400;self.assertTrue(self.eligible())
        for field,value in [('effects','unknown'),('state','held')]:
            self.store.db.execute('UPDATE jobs SET '+field+'=?',(value,))
            self.assertEqual(cleanup.retire_artifact(self.store,row)['state'],'held')
            self.store.db.execute("UPDATE jobs SET state='closed',effects='none'")
        for field,value in [('cleanup','pending'),('collected',None),('ended',None)]:
            old=self.store.one('SELECT * FROM attempts')[field]
            self.store.db.execute('UPDATE attempts SET '+field+'=?',(value,))
            self.assertEqual(cleanup.retire_artifact(self.store,row)['state'],'held')
            self.store.db.execute('UPDATE attempts SET '+field+'=?',(old,))
        self.store.set_hold('source','privacy/source/recovery consumer reference')
        self.assertEqual(cleanup.retire_artifact(self.store,row)['state'],'held');self.store.set_hold('source',None)
        self.store.db.execute("INSERT INTO outboxes(id,role,event,producer,recipient,kind,required,payload,created,state,processed_at,hold) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
            ('fictional-outbox','Work','source','fictional','fictional','result','processed','{}',1,'settled',100000,'consumer'))
        self.assertEqual(cleanup.retire_artifact(self.store,row)['state'],'held')
        self.store.db.execute("UPDATE outboxes SET hold=NULL,state='pending'")
        self.assertEqual(cleanup.retire_artifact(self.store,row)['state'],'held')
        self.store.db.execute("UPDATE outboxes SET state='settled',processed_at=NULL")
        self.assertEqual(cleanup.retire_artifact(self.store,row)['state'],'held')
        self.store.db.execute("UPDATE outboxes SET state='settled',processed_at=100000,required='processed'")
        self.store.db.execute('UPDATE outboxes SET processed_at=300000')
        self.now=386399;self.assertEqual(cleanup.retire_artifact(self.store,row)['state'],'held')
        self.now=386400
        real=os.unlink
        with patch.object(os,'unlink',wraps=real) as unlink:
            self.assertEqual(cleanup.retire_artifact(self.store,row)['state'],'removed')
            self.assertEqual(cleanup.retire_artifact(self.store,row)['state'],'held');self.assertEqual(unlink.call_count,1)

    def test_original_identity_symlink_hardlink_hash_and_custody_fences(self):
        self.now=200000
        for kind in ['identity','symlink','hardlink','hash','custody']:
            row=self.owned(kind);path=Path(row['path'])
            if kind=='identity':path.rename(path.with_name('original'));path.write_text('replacement')
            elif kind=='symlink':path.rename(path.with_name('original'));path.symlink_to(path.with_name('original'))
            elif kind=='hardlink':os.link(path,path.with_name('second-link'))
            elif kind=='hash':
                path.write_bytes(b'x'*row['size']);os.utime(path,ns=(row['mtime'],row['mtime']))
            else:self.store.db.execute("UPDATE artifacts SET attempt='other' WHERE path=?",(row['path'],))
            self.assertIn(cleanup.retire_artifact(self.store,row)['state'],{'held','partial-held'})
            self.assertIsNone(self.row(path)['removed'])

    def test_kernel_source_and_sdk5_readonly(self):
        from coordinator_runtime.report_repair import AMEND_MODULES, AMEND_ADDED_MODULES
        self.assertIn('cleanup.py', AMEND_MODULES)
        self.assertNotIn('cleanup.py', AMEND_ADDED_MODULES)
        self.assertNotIn('appserver.py', AMEND_MODULES)
        paths=[Path('/actualsrc/tools/coordinator-runtime/coordinator_runtime/cleanup.py')]
        paths += [Path('/sdk')/n for n in ['board_store.py','catalog.py','retention.py','queue_transport.py','active_listener.py']]
        for path in paths:
            self.assertTrue(os.statvfs(path).f_flag & os.ST_RDONLY)
            with self.assertRaises(OSError) as caught:os.open(path,os.O_WRONLY)
            self.assertEqual(caught.exception.errno,errno.EROFS)
