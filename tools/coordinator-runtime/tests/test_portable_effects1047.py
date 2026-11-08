"""Retained fictional API effects for a separate, code-independent readback.

No real principals, provider, journal or external acceptance are represented.
"""
import os
import json
from pathlib import Path
import unittest

from support import config_at, enrolled, event
from coordinator_runtime.contracts import Backpressure


class PortableEffects1047(unittest.TestCase):
    def test_generated_commands_use_current_supported_public_interface(self):
        from coordinator_runtime.ordinary import command_policy
        manifest = json.loads(Path('/procedure/manifest.json').read_text())
        commands = json.loads(Path('/procedure/COMMANDS.json').read_text())
        home = Path(os.environ['QA629_FIXTURES']).parent/'policy-oracle'
        home.mkdir(mode=0o700)
        store = enrolled(config_at(home))
        try:
            for role in ('command', 'readback'):
                command_policy(store, commands[role], [manifest['instance']],
                               commands['public_executables'][role])
        finally:
            store.close()

    def test_retained_input_and_refused_second_allocation(self):
        home = Path(os.environ['QA629_FIXTURES']).parent/'oracle'
        home.mkdir(mode=0o700)
        config = config_at(home)
        config['limits']['max_events'] = 1
        store = enrolled(config)
        try:
            self.assertTrue(store.ingest(event(config, name='retained-original')))
            with self.assertRaises(Backpressure):
                store.ingest(event(config, name='refused-second'))
            self.assertEqual(len(store.rows('SELECT * FROM events')), 1)
            self.assertEqual(store.rows('SELECT * FROM attempts'), [])
        finally:
            store.close()
        (home/'original.txt').write_text('retained original; second input refused\n')
