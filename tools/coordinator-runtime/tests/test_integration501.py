"""Producer integration contrasts, exclusively new fictional journals/providers.

An old config remains a metadata/basis input. Only a successor draft/release
pins the closure; parsing old metadata never grants publication authority.
"""
import copy
import json
from pathlib import Path
import unittest

from _receiving485_fixtures import Base
from support import fixture_publication
from coordinator_runtime import configuration, processing, publication
from coordinator_runtime.contracts import Refusal, digest, validate_config
from coordinator_runtime.store import Store


class Configuration501(Base):
    def configure_fixture(self):
        self.config['canonical_publication'].pop('source_pins')
        self.config['operator_cli'] = '/fictional/old/coordinator'
        self.config['control_receive'] = {}

    def test_old_metadata_basis_successor_release_and_publication_contrasts(self):
        original = copy.deepcopy(self.config)
        self.assertNotIn('source_pins', original['canonical_publication'])
        self.assertEqual(validate_config(copy.deepcopy(original)), original)
        self.setup()
        basis = processing.basis(self.store, self.boards, future_only=True)
        self.assertEqual(basis['configuration'], digest(original))
        self.assertEqual(configuration.original_digest(self.store), digest(original))
        # Reopen only this newly authored journal with its unchanged old metadata.
        reopened = Store(copy.deepcopy(original))
        try:
            configuration.assert_current(reopened)
            self.assertEqual(configuration.original_digest(reopened), digest(original))
        finally:
            reopened.close()
        with self.assertRaisesRegex(Refusal, 'five-file'):
            with publication.snapshot_lock(self.store):
                self.fail('old metadata must not authorize successor publication')
        operator = self.area / 'fictional-operator.json'
        draft = configuration.candidate(self.store, str(operator), [])
        self.assertEqual(draft['canonical_publication'], fixture_publication())
        self.assertEqual(self.config, original)
        self.assertEqual(draft['tasks'], original['tasks'])
        operator.write_text(json.dumps(draft))
        missing = copy.deepcopy(draft)
        missing['canonical_publication'].pop('source_pins')
        with self.assertRaisesRegex(Refusal, 'five-file'):
            configuration.release(self.store, missing)
        released = configuration.release(self.store, draft)
        for name, pin in draft['canonical_publication']['source_pins'].items():
            self.assertEqual(released['files'][str(Path(draft['canonical_publication']['library'])/name)], pin)
        prospective = configuration.basis(self.store, self.boards, draft, ['work-integrator'])
        self.assertEqual(prospective['configuration'], digest(original))
        self.assertEqual(prospective['candidate'], digest(draft))
        self.assertEqual(prospective['release'], released)
        # Exercise the real publication lock with the new fictional provider.
        from types import SimpleNamespace
        with publication.snapshot_lock(SimpleNamespace(config=draft)):
            pass
        self.assertEqual(self.config, original)


if __name__ == '__main__':
    unittest.main(verbosity=2)
