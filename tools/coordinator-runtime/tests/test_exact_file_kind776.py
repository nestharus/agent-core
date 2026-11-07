"""Real immutable file-to-tree witnesses through Executor and the reader.

Inherited NULL-native fixture seams are explicit; no real owner/provider grant.
"""
import json
from pathlib import Path
import shlex
from unittest.mock import Mock, patch

from coordinator_runtime import reviews, review_reader
from coordinator_runtime.contracts import Refusal
import test_reviews_ceiling766 as fixture


class ExactFileKind(fixture.ReviewsCeiling):
    def commit(self):
        self.git('add', '-A')
        self.git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                 '-c', 'commit.gpgsign=false', 'commit', '-qm', 'owned later public fixture')
        return self.git('rev-parse', 'HEAD').strip()

    def tree_head(self):
        (self.repo/'A.py').unlink()
        (self.repo/'A.py').mkdir()
        (self.repo/'A.py/B.py').write_text('owned_new_descendant = True\n')
        return self.commit()

    def refuse_tree(self, scoped=False, pin='head', relationship=False):
        later = self.tree_head()
        self.s.config['tasks']['rp']['require_package_scope'] = scoped
        if relationship:
            task = self.s.config['tasks']['rp']
            task['effect_authority']['read_roots'].append(str(self.repo/'A1.py'))
            task['exact_read_files'].append(str(self.repo/'A1.py'))
            self.policy['components']['component']['paths'] = ['A1.py']
            self.policy['components']['component']['relationship_paths'] = ['A.py']
        self.packet[pin] = later
        if pin == 'previous':
            self.s.db.execute('INSERT INTO review_contexts VALUES(?,?,NULL,?,?,NULL,?,?,?,?,?,NULL)',
                ('component',self.s.processing.key,'fixture-route','fixture-handle',
                 self.s.controller,'live',later,reviews.sha(b''),1))
        actual = reviews.git
        calls = []
        def observed(repository, *args):
            calls.append(args)
            # No recursive names/diff or descendant body query may occur first.
            if '-rz' in args or 'diff' in args or any('A.py/B.py' in a for a in args):
                raise AssertionError('descendant acquisition before exact-file refusal')
            return actual(repository, *args)
        native = Mock()
        with patch.object(reviews, 'git', side_effect=observed):
            with self.assertRaisesRegex(Refusal, 'exact-file Source operand'):
                self.execute(native)
        native.call.assert_not_called()
        self.assertTrue(any('ls-tree' in a and later in a and '-z' in a for a in calls))

    def reach(self, names, bodies):
        case = self
        class Probe:
            async def call(inner, runtime, attempt, policy, context, directory, text, commands, **kw):
                path = Path(shlex.split(commands[0])[-1])
                manifest = json.loads(path.read_text())
                case.assertEqual(set(manifest['source']), names)
                found = {}
                for _ in range(24):
                    chunk = review_reader.next_chunk(path)
                    if chunk.get('end_of_material'):
                        break
                    found[chunk['source']] = chunk.get('text', '')
                else:
                    case.fail('reader did not finish')
                for name, body in bodies.items():
                    case.assertIn(body, found[name])
                raise fixture.ReachedFacade()
        with self.assertRaises(fixture.ReachedFacade):
            self.execute(Probe())

    def test_selection_records_exact_public_names(self):
        self.assertEqual(self.s.config['tasks']['rp']['exact_read_files'], [str(self.repo/'A.py')])

    def test_later_tree_unscoped_before_descendant_metadata(self): self.refuse_tree()
    def test_later_tree_scoped_before_descendant_metadata(self): self.refuse_tree(scoped=True)
    def test_base_tree_before_descendant_metadata(self): self.refuse_tree(pin='base')
    def test_previous_tree_before_descendant_metadata(self): self.refuse_tree(pin='previous')
    def test_relationship_tree_before_descendant_metadata(self): self.refuse_tree(relationship=True)

    def test_working_kind_cannot_supply_grant(self):
        self.tree_head()
        self.policy['components']['component']['paths'] = ['A.py/B.py']
        self.negative(path='A.py/B.py')

    def test_later_bytes_at_exact_file_reach_reader(self):
        (self.repo/'A.py').write_text('admitted_later_bytes = True\n')
        later = self.commit()
        self.packet['head'] = later
        self.reach({self.head+':A.py', later+':A.py'},
                   {self.head+':A.py':'admitted_public_A', later+':A.py':'admitted_later_bytes'})

    def test_deletion_reaches_reader(self):
        (self.repo/'A.py').unlink()
        self.packet['head'] = self.commit()
        self.reach({self.head+':A.py'}, {self.head+':A.py':'admitted_public_A'})

    def test_scoped_later_bytes_reach_reader(self):
        self.s.config['tasks']['rp']['require_package_scope'] = True
        self.test_later_bytes_at_exact_file_reach_reader()

    def test_scoped_deletion_reaches_reader(self):
        self.s.config['tasks']['rp']['require_package_scope'] = True
        self.test_deletion_reaches_reader()

    def test_independent_broad_grant_allows_new_descendant(self):
        later = self.tree_head()
        self.s.config['tasks']['rp']['effect_authority']['read_roots'].append(str(self.repo))
        self.packet['head'] = later
        self.reach({self.head+':A.py', later+':A.py/B.py'},
                   {later+':A.py/B.py':'owned_new_descendant'})

    def test_package_exact_narrowing_under_broad_grant_stays_exact(self):
        self.s.config['tasks']['rp']['effect_authority']['read_roots'].append(str(self.repo))
        self.refuse_tree(scoped=True)
