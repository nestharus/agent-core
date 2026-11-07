"""Owned source/journal fiction through production selection, never actual ENDs.

The 707 fixture supplies NULL-native actor/config/allocation seams. Source
copies are measured; lifecycle receipts below are explicitly fictional.
"""
from contextlib import ExitStack
import json
import re
import sqlite3
import unittest
from unittest.mock import patch

from coordinator_runtime import configuration, processing
from coordinator_runtime.contracts import Refusal, digest, encode
import test_source_selection707 as protocol


class SourceTransition(unittest.TestCase):
    def setUp(self):
        self.f = protocol.SourceSelection()
        self.addCleanup(self.f.doCleanups)
        self.f.setUp()
        self.runtime = self.f.runtime
        self.enterContext(patch.object(processing, '__file__', str(self.f.copy.modules/'processing.py')))

    def original(self, controller='fictional-outgoing', *, closed=True):
        key = processing.select(self.runtime, self.f.f.boards,
                                self.f.f.processing_selection())['capability']
        self.runtime.db.execute('INSERT INTO processing_runs VALUES(?,?,?,1000)',
                                (controller, key, 'owned'))
        self.runtime.db.execute('INSERT INTO service_runs VALUES(?,?,?,?,1000,?,NULL)',
                                (controller, key, 'fictional-unused-socket',
                                 'returned-awaiting-parent-END' if closed else 'serving',
                                 1001 if closed else None))
        processing.revoke(self.runtime, self.f.f.boards, key)
        if closed:
            processing.release(self.runtime, self.f.f.boards, key, controller,
                               {'actual_END': 0, 'evidence': ['FICTION: same original parent collected END']})
        return key

    def attempt(self, controller):
        self.runtime.db.execute("INSERT INTO attempts(id,kind,controller,profile,binding,created) "
                                "VALUES(?,'task',?,NULL,'{}',1000)", (controller+'-attempt', controller))

    def history(self):
        self.runtime.db.execute("UPDATE processing_runs SET state='owned' WHERE controller='fictional-old-collector'")
        self.runtime.db.execute("INSERT INTO service_runs VALUES('fictional-old-collector',?,"
                                "'fictional-unused-old-socket','serving',900,NULL,'excluded old receipt')",
                                (self.f.f.oldkey,))
        self.attempt('fictional-old-collector')

    def guard(self, allowed=()):
        """Wrap real SQL execution; fail before any unrelated state acquisition."""
        stack = ExitStack()
        forbidden = {'service_runs': {'socket', 'receipt'},
                     'attempts': {'result', 'detail', 'error', 'capture', 'binding', 'profile', 'session', 'turn'},
                     'events': {'payload', 'classification', 'error'}}
        def authorize(action, table, column, database, caller):
            if action == sqlite3.SQLITE_READ and column in forbidden.get(table, set()):
                return sqlite3.SQLITE_DENY
            return sqlite3.SQLITE_OK
        self.runtime.db.set_authorizer(authorize)
        stack.callback(self.runtime.db.set_authorizer, None)
        for method in ('one', 'rows'):
            original = getattr(self.runtime, method)
            def checked(sql, parameters=(), original=original):
                lower = sql.lower()
                if 'state' in lower and any('from '+t in lower for t in ('processing_runs', 'service_runs')):
                    self.assertIn('where controller=? and capability=?', lower)
                    self.assertIn(tuple(parameters), allowed)
                self.assertNotIn('select * from processing_capabilities', lower)
                self.assertIsNone(re.search(r'\bselect\s+(?:c\.)?selection\s+from\s+processing_capabilities', lower))
                return original(sql, parameters)
            stack.enter_context(patch.object(self.runtime, method, side_effect=checked))
        return stack

    def test_unrelated_unknown_history_is_preserved_without_state_acquisition(self):
        self.history()
        key = self.original()
        before = self.f.snapshot()
        self.f.change()
        with self.guard([('fictional-outgoing', key)]):
            result = self.f.apply()
        self.assertEqual(result['source_selection'], 1)
        self.assertEqual(before, self.f.snapshot())

    def test_serving_outgoing_refuses_even_with_revoked_capability_and_free_lock(self):
        self.original(closed=False)
        self.f.change()
        with self.assertRaisesRegex(Refusal, 'numeric parent END'):
            self.f.apply()

    def test_returned_outgoing_without_processing_release_refuses(self):
        self.original(closed=False)
        self.runtime.db.execute("UPDATE service_runs SET state='returned-awaiting-parent-END',returned=1001")
        self.f.change()
        with self.assertRaisesRegex(Refusal, 'numeric parent END'):
            self.f.apply()

    def test_missing_or_nonnumeric_parent_END_refuses(self):
        self.original()
        self.f.change()
        for state in ('{}', '{"parent_END":{"actual_END":true,"evidence":["fiction"]}}',
                      '{"parent_END":{"actual_END":0,"evidence":[]}}'):
            with self.subTest(state=state):
                self.runtime.db.execute("UPDATE processing_runs SET state=? WHERE controller='fictional-outgoing'", (state,))
                with self.assertRaisesRegex(Refusal, 'numeric parent END'):
                    self.f.apply()

    def test_related_uncollected_attempt_refuses_after_release(self):
        self.original()
        self.attempt('fictional-outgoing')
        self.f.change()
        with self.assertRaisesRegex(Refusal, 'numeric parent END'):
            self.f.apply()

    def test_repeated_sameconfig_uses_original_ordinals_and_preserves_older_unknowns(self):
        self.history()
        old = self.original('fictional-first')
        self.f.change(); self.f.apply()
        # Deliberately retain an older generation UNKNOWN, not a fabricated
        # repair or END. It must never be acquired by the next selection.
        self.runtime.db.execute("UPDATE processing_runs SET state='owned' WHERE controller='fictional-first'")
        self.runtime.db.execute("UPDATE service_runs SET state='serving',returned=NULL WHERE controller='fictional-first'")
        self.attempt('fictional-first')
        key = self.original('fictional-second')
        selected = json.loads(self.runtime.one('SELECT selection FROM processing_capabilities WHERE id=?', (key,))['selection'])
        self.assertEqual(selected['basis']['configuration_transition']['source_selection'], 1)
        before = self.f.snapshot()
        self.f.change('processing.py')
        with self.guard([('fictional-second', key)]):
            self.f.apply()
        self.assertEqual(before, self.f.snapshot())
        self.assertEqual(configuration.version_metadata(self.runtime)['source_selection'], 2)

    def test_legacy_basis_without_ordinal_is_matched_by_exact_implementation(self):
        key = self.original()
        self.runtime.db.execute("UPDATE processing_capabilities SET selection=json_remove(selection,'$.basis.configuration_transition.source_selection') WHERE id=?", (key,))
        self.f.change(); self.f.apply()
        self.runtime.db.execute("UPDATE processing_runs SET state='owned' WHERE controller='fictional-outgoing'")
        self.runtime.db.execute("UPDATE service_runs SET state='serving',returned=NULL WHERE controller='fictional-outgoing'")
        self.attempt('fictional-outgoing')
        current = self.original('fictional-next')
        before = self.f.snapshot()
        self.f.change('processing.py')
        with self.guard([('fictional-next', current)]):
            self.f.apply()
        self.assertEqual(before, self.f.snapshot())

    def test_ambiguous_source_configuration_and_generation_refuse_before_state(self):
        key = self.original()
        saved = self.runtime.one('SELECT selection FROM processing_capabilities WHERE id=?', (key,))['selection']
        self.f.change()
        mutations = [
            ('configuration', lambda b: b.update(configuration='fictional-unknown-configuration')),
            ('position', lambda b: b['configuration_transition'].update(position=999)),
            ('boolean position', lambda b: b['configuration_transition'].update(position=True)),
            ('source ordinal', lambda b: b['configuration_transition'].update(source_selection=999)),
            ('null source ordinal', lambda b: b['configuration_transition'].update(source_selection=None)),
            ('boolean source ordinal', lambda b: b['configuration_transition'].update(source_selection=False)),
            ('implementation', lambda b: b['implementation'].update({'store.py': 'fictional-unselected-source'})),
            ('missing basis', lambda b: b.clear()),
        ]
        with self.guard():
            for name, mutate in mutations:
                with self.subTest(name=name):
                    value = json.loads(saved)
                    mutate(value['basis'])
                    self.runtime.db.execute('UPDATE processing_capabilities SET selection=? WHERE id=?', (encode(value), key))
                    with self.assertRaisesRegex(Refusal, 'generation'):
                        self.f.apply()

    def test_orphan_or_mismatched_original_refuses_before_state(self):
        key = self.original()
        self.f.change()
        self.runtime.db.execute("UPDATE service_runs SET capability='fictional-missing-capability'")
        with self.guard(), self.assertRaisesRegex(Refusal, 'generation'):
            self.f.apply()

    def test_legacy_repeated_implementation_is_ambiguous_but_new_ordinal_is_exact(self):
        key = self.original()
        saved = self.runtime.one('SELECT selection FROM processing_capabilities WHERE id=?', (key,))['selection']
        code = (self.f.copy.modules/'configuration.py').read_bytes()
        self.f.change(); self.f.apply()
        (self.f.copy.modules/'configuration.py').write_bytes(code)
        self.f.apply()  # A -> B -> A, with separate immutable source ordinals.
        self.f.change('processing.py')
        self.runtime.db.execute("UPDATE processing_capabilities SET selection=json_remove(selection,'$.basis.configuration_transition.source_selection') WHERE id=?", (key,))
        with self.assertRaisesRegex(Refusal, 'generation'):
            self.f.apply()
        self.runtime.db.execute('UPDATE processing_capabilities SET selection=? WHERE id=?', (saved, key))
        self.f.apply()

    def test_exact_other_configuration_needs_no_historical_lifecycle_or_body(self):
        key = self.original(closed=False)
        self.attempt('fictional-outgoing')
        value = json.loads(self.runtime.one('SELECT selection FROM processing_capabilities WHERE id=?', (key,))['selection'])
        other = digest('FICTION: another original configuration, outside selected transition history')
        value['basis'].update(configuration=other)
        value['basis']['configuration_transition'].update(current=other, position=999)
        self.runtime.db.execute('UPDATE processing_capabilities SET selection=? WHERE id=?', (encode(value), key))
        before = self.f.snapshot()
        self.f.change()
        with self.guard():
            self.f.apply()
        self.assertEqual(before, self.f.snapshot())

    def test_every_outgoing_original_requires_release_not_just_one_controller(self):
        self.original('fictional-first')
        self.original('fictional-second', closed=False)
        self.f.change()
        with self.assertRaisesRegex(Refusal, 'numeric parent END'):
            self.f.apply()
        self.assertIsNone(configuration.version_metadata(self.runtime).get('source_selection'))

    def test_processing_only_original_still_requires_numeric_release(self):
        self.original(closed=False)
        self.runtime.db.execute("DELETE FROM service_runs WHERE controller='fictional-outgoing'")
        self.f.change()
        with self.assertRaisesRegex(Refusal, 'numeric parent END'):
            self.f.apply()
        key = self.runtime.one("SELECT capability FROM processing_runs WHERE controller='fictional-outgoing'")['capability']
        processing.release(self.runtime, self.f.f.boards, key, 'fictional-outgoing',
                           {'actual_END': 9, 'evidence': ['FICTION: nonzero numeric original parent END']})
        self.f.apply()

    def test_current_service_without_processing_original_refuses_before_state(self):
        self.original()
        self.runtime.db.execute("DELETE FROM processing_runs WHERE controller='fictional-outgoing'")
        self.f.change()
        with self.guard(), self.assertRaisesRegex(Refusal, 'generation'):
            self.f.apply()


if __name__ == '__main__':
    unittest.main()
