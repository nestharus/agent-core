"""Executed positive, omission and weakened-neighbor evidence controls."""
import errno
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
import unittest

from operation_evidence1171 import qualifies, ALLOWED, OUTSIDE


class OperationEvidence(unittest.TestCase):
    def experiment(self,mode):
        area=Path(tempfile.mkdtemp(prefix='operation1171-',dir=os.environ['ONEOFF1077_FIXTURES']))
        (area/'allowed.txt').write_text(secrets.token_hex(16))
        (area/'outside.txt').write_text('owned nonsecret outside sentinel1171')
        run=subprocess.run([sys.executable,'-B',str(Path(__file__).with_name('operation_evidence1171.py')),
                            'observe',mode,str(area)],capture_output=True,text=True,timeout=30)
        (area/'observer-stdout.json').write_text(run.stdout)
        (area/'observer-stderr.txt').write_text(run.stderr)
        self.assertEqual(run.returncode,0,run.stderr)
        record=json.loads(run.stdout)
        self.assertEqual(record['actual_END'],0,record)
        return record

    def test_actual_allowed_read_and_denied_operations(self):
        record=self.experiment('protected')
        self.assertTrue(record['qualified'],record)
        self.assertEqual(record['expected_read_sha256'],record['resulting_allowed_sha256'])

    def test_omission_with_denial_constants_does_not_qualify(self):
        record=self.experiment('omitted')
        self.assertFalse(record['qualified'],record)
        self.assertTrue(any(e['operation']=='read' and e['path']==ALLOWED for e in record['events']))
        self.assertFalse(any(e['operation']=='connect' or e.get('path')==OUTSIDE for e in record['events']))

    def test_actual_outside_read_write_and_network_success_do_not_qualify(self):
        record=self.experiment('weakened')
        self.assertFalse(record['qualified'],record)
        self.assertTrue(any(e['operation']=='open' and e['path']==OUTSIDE and e['result']>=0 for e in record['events']))
        self.assertTrue(any(e['operation']=='write' and e['path']==ALLOWED and e['result']>0 for e in record['events']))
        self.assertTrue(any(e['operation']=='connect' and e['result']==0 for e in record['events']))
        self.assertNotEqual(record['expected_read_sha256'],record['resulting_allowed_sha256'])
