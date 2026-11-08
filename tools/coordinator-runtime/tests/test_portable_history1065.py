"""History input guarantees from Decision1065; all operands are owned fiction."""
from pathlib import Path
import os
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'portable_qa'))
from common import file_pin
from history import OLD_COMMIT, production_history


class History1065(unittest.TestCase):
    def setUp(self):
        self.area = Path(os.environ['QA629_FIXTURES']) / self.id()
        self.area.mkdir()
        self.old = self.area / 'existing.py'
        self.old.write_bytes(b'# genuine fixture old bytes\n')
        self.record = {'commit': OLD_COMMIT, 'path': str(self.old), 'pin': file_pin(self.old)}
        self.production = {'existing.py': 'current-existing-hash', 'new.py': 'current-new-hash'}
        self.records = {'existing.py': self.record, 'new.py': {'commit': OLD_COMMIT, 'absent': True}}

    def test_current_completeness_and_genuine_absence_coexist(self):
        result = production_history(self.production, self.records)
        self.assertEqual(result['candidate'], self.production)
        self.assertEqual(result['original'], {'existing.py': self.record['pin']['sha256']})
        self.assertEqual(result['absent'], {'new.py': {'commit': OLD_COMMIT, 'absent': True}})
        with self.assertRaises(KeyError):
            result['original']['new.py']

    def test_missing_record_is_not_absence(self):
        with self.assertRaisesRegex(ValueError, 'complete old704 history'):
            production_history(self.production, {'existing.py': self.record})

    def test_extra_history_does_not_replace_current_closure(self):
        with self.assertRaisesRegex(ValueError, 'complete old704 history'):
            production_history({'existing.py': 'current'}, self.records)

    def test_wrong_absence_origin_refuses(self):
        self.records['new.py']['commit'] = '0' * 40
        with self.assertRaisesRegex(ValueError, 'exact historical fixture origin'):
            production_history(self.production, self.records)

    def test_false_or_hash_bearing_absence_refuses(self):
        self.records['new.py']['absent'] = False
        with self.assertRaisesRegex(ValueError, 'explicit genuine historical absence'):
            production_history(self.production, self.records)
        self.records['new.py'].update(absent=True, pin=self.record['pin'])
        with self.assertRaisesRegex(ValueError, 'exact historical blob or absence'):
            production_history(self.production, self.records)

    def test_missing_or_mutated_old_blob_refuses(self):
        self.old.write_bytes(b'changed historical bytes')
        with self.assertRaisesRegex(ValueError, 'identity mismatch'):
            production_history(self.production, self.records)

    def test_existing_blob_only_history_keeps_exact_hashes(self):
        result = production_history({'existing.py': 'current'}, {'existing.py': self.record})
        self.assertEqual(result, {'original': {'existing.py': self.record['pin']['sha256']},
                                  'candidate': {'existing.py': 'current'}, 'absent': {}})


if __name__ == '__main__':
    unittest.main()
