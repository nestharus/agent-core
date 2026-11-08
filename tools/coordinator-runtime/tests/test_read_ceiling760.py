"""Owned protocol fixtures only; no native/provider/source-owner acceptance.

Run with fresh private TMPDIR and positive /src RO, /fixtures RW mounts.
Configuration308 supplies explicit NULL-native membership/configuration seams.
"""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

from coordinator_runtime import configuration, contracts, local_native, processing
from coordinator_runtime.contracts import Refusal, digest, encode, scoped_task
import test_configuration308 as fixture


class ReadCeiling(unittest.TestCase):
    def setUp(self):
        self.f = fixture.CurrentConfiguration(methodName='runTest')
        self.addCleanup(self.f.doCleanups)
        engine, store = fixture.engine_config, fixture.Store
        def config(directory):
            value = engine(directory)
            value['tasks']['bp'] = {**copy.deepcopy(value['tasks']['wp']), 'role': 'Branch'}
            return value
        def runtime(value, **kwargs):
            neutral = Path(value['state_dir']).parent/'neutral'; neutral.mkdir()
            for name in ('bp', 'qc'):
                t = value['tasks'][name]
                t.update(cwd=str(neutral), startup='explicit-packet', require_package_scope=True,
                         package_narrowing=True, scope_roots=[str(neutral)])
                t['effect_authority']['read_roots'] = [str(neutral)]
            value['tasks']['bp']['effect_authority']['operations'] = ['read-source']
            for role, selected in value['roles'].items():
                selected['routes'] = [n for n,t in value['tasks'].items() if t['role'] == role]
            return store(value, **kwargs)
        with patch.object(fixture, 'engine_config', side_effect=config), patch.object(fixture, 'Store', side_effect=runtime):
            self.f.setUp()
        self.s = self.f.runtime
        self.repo = self.f.directory/'rfq'; self.repo.mkdir()
        self.git('init', '-q')
        (self.repo/'component.py').write_text('public = True\n')
        self.git('add', 'component.py')
        self.git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                 '-c', 'commit.gpgsign=false', 'commit', '-qm', 'owned immutable public source')
        self.head = self.git('rev-parse', 'HEAD').strip()
        self.report = self.f.directory/'procedure.md'; self.report.write_text('safe supplied procedure\n')
        self.entry = {'configuration':digest(self.s.config), 'role_owner':'fictional-Branch',
                      'original_grant':'fictional-grant-Branch', 'authority':'fictional attributed Work choice',
                      'source_authority':'fictional owner supplies exact public component and procedure',
                      'read_roots':[str(self.repo/'component.py'), str(self.report)],
                      'repository_reads':[str(self.repo)], 'components':{'rfq':['component.py']},
                      'source':{'repository':str(self.repo),'commit':self.head,
                                'files':{'component.py':self.sha(self.repo/'component.py')}},
                      'safe_files':{str(self.report):self.sha(self.report)}}

    def git(self, *args):
        r = subprocess.run(['/usr/bin/git','-C',str(self.repo),*args], capture_output=True, timeout=15)
        self.assertEqual(r.returncode, 0, r.stderr.decode())
        return r.stdout.decode()

    def sha(self, path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def draft(self, entry=None, **extra):
        options = {'read_ceiling_extensions':{'bp':self.entry if entry is None else entry}, **extra}
        value = configuration.candidate(self.s, str(self.f.directory/'extended.json'), [], scope_options=options)
        Path(value['operator_config']).write_text(encode(value))
        return value

    def scope(self, value):
        return {'cwd':value['tasks']['bp']['cwd'], 'read_roots':self.entry['read_roots'],
                'write_roots':[], 'network':False, 'procedure':str(self.report),
                'resource_evidence':'fictional original package owner scope', 'repository_reads':[str(self.repo)]}

    def test_draft_basis_apply_preserves_original_bridge_and_frozen_bytes(self):
        value = self.draft(repository_reads={'bp':[str(self.repo)]})
        task = value['tasks']['bp']
        # Static public profile-label validation; no native profile is opened.
        contracts.validate_task('bp', {**task, 'profile':value['profiles'][0]}, value)
        self.assertEqual(task['cwd'], self.s.config['tasks']['bp']['cwd'])
        self.assertEqual(task['scope_roots'], [task['cwd'], *self.entry['read_roots']])
        admission = {'receipt':encode({'task_scopes':{'bp':self.scope(value)}})}
        self.assertEqual(scoped_task('bp', task, admission)['repository_reads'], [str(self.repo)])
        grants = [tuple(r) for r in self.f.conn.execute('SELECT * FROM coordinator_grants_v1')]
        caps = [tuple(r) for r in self.f.conn.execute('SELECT * FROM coordinator_software_grants_v1')]
        self.s.db.execute('INSERT INTO job_resource_policies(job,task,admission) VALUES(?,?,?)',
                          ('fictional-old-job', encode(self.s.config['tasks']['wp']), '{}'))
        frozen = self.s.one('SELECT * FROM job_resource_policies')
        old = copy.deepcopy(self.s.config['tasks'])
        basis = configuration.basis(self.s, self.f.boards, value, ['bp'])
        self.assertNotIn('source_only', basis)
        configuration.apply(self.s, self.f.boards, value, {'basis':basis,'authority':'fictional genuine Work decision'})
        self.assertEqual(frozen, self.s.one('SELECT * FROM job_resource_policies'))
        self.assertEqual(old['wp'], configuration.task_for_job(self.s, {'id':'fictional-old-job','task':'wp'}))
        self.assertEqual(grants, [tuple(r) for r in self.f.conn.execute('SELECT * FROM coordinator_grants_v1')])
        self.assertEqual(caps, [tuple(r) for r in self.f.conn.execute('SELECT * FROM coordinator_software_grants_v1')])
        self.s.config = value
        for board in self.f.boards.values():
            board.config = value; board.selected = value['roles'][board.role]
        original = self.f.boards['Branch'].prospective_basis(self.s)
        self.assertEqual(original['configuration'], digest(self.f.original))
        self.assertEqual(original['binding']['id'], 'fictional-grant-Branch')
        self.assertIsNotNone(original['binding']['revoked'])

    def test_safe_report_only_cleanup_needs_no_execution_operation(self):
        e = {**self.entry, 'role_owner':'fictional-QA', 'original_grant':'fictional-grant-QA',
             'source':None,'components':{},'repository_reads':[], 'read_roots':[str(self.report)]}
        value = configuration.candidate(self.s, str(self.f.directory/'cleanup.json'), [],
                    scope_options={'read_ceiling_extensions':{'qc':e}})
        configuration.validate_changes(self.s, value, ['qc'])
        self.assertEqual(value['tasks']['qc']['effect_authority']['operations'], ['read-reports'])

    def test_changed_task_must_be_selected(self):
        value = self.draft()
        with self.assertRaises(Refusal): configuration.basis(self.s, self.f.boards, value, ['wp'])

    def test_wrong_current_owner_grant_and_extra_authority_fields_refuse(self):
        for key, bad in [('configuration','0'*64), ('role_owner','foreign'), ('original_grant','foreign'),
                         ('write_roots',[]), ('network',True), ('cwd','/'), ('capacity',5)]:
            with self.subTest(key=key), self.assertRaises(Refusal): self.draft({**self.entry,key:bad})
        with self.assertRaises(Refusal):
            configuration.candidate(self.s, '/fixtures/no.json', [], scope_options={'read_ceiling_extensions':{'new':self.entry}})

    def test_hand_edited_extra_rights_refuse(self):
        value = self.draft()
        mutations = [lambda t:t.update(cwd='/'), lambda t:t.update(network=True),
                     lambda t:t.update(capacity=4), lambda t:t['effect_authority']['write_roots'].append('/fixtures'),
                     lambda t:t['effect_authority'].update(owner='foreign'),
                     lambda t:t['effect_authority']['operations'].append('execute-admitted-qa'),
                     lambda t:t['effect_authority']['read_roots'].append(str(self.repo))]
        for mutate in mutations:
            bad = copy.deepcopy(value); mutate(bad['tasks']['bp'])
            with self.subTest(mutate=mutate), self.assertRaises(Refusal): configuration.validate_changes(self.s, bad, ['bp'])

    def test_private_excluded_ancestor_alias_and_startup_refuse(self):
        alias = self.f.directory/'alias.md'; alias.symlink_to(self.report)
        for p in [str(Path.home()/'.codex'/'private'), '/home/nes/projects/rfq/planning',
                  str(self.f.directory), str(alias), str(self.f.directory/'AGENTS.md')]:
            e = {**self.entry, 'source':None,'components':{},'repository_reads':[],
                 'read_roots':[p], 'safe_files':{p:'0'*64}}
            with self.subTest(path=p), self.assertRaises(Refusal):
                self.draft(e, exclusions=[str(self.f.directory/'held')])

    def test_untracked_source_refused_before_body_read(self):
        secret = self.repo/'untracked'; secret.write_text('owned sentinel')
        e = copy.deepcopy(self.entry)
        e['source']['files'] = {'untracked':'0'*64}; e['components'] = {'rfq':['untracked']}
        e['read_roots'] = [str(secret),str(self.report)]
        from coordinator_runtime import custody
        read_file = custody.read_file
        def guarded(path, maximum):
            if path == secret:
                raise AssertionError('untracked body acquired')
            return read_file(path, maximum)
        with patch.object(custody, 'read_file', side_effect=guarded):
            with self.assertRaises(Refusal): self.draft(e)

    def test_wrong_commit_and_tracked_working_body_refuse(self):
        e = copy.deepcopy(self.entry); e['source']['commit'] = '0'*40
        with self.assertRaises(Refusal): self.draft(e)
        (self.repo/'component.py').write_text('changed working file\n')
        with self.assertRaises(Refusal): self.draft()

    def test_invalid_package_widening_and_repository_not_read_permission(self):
        value = self.draft(); task = value['tasks']['bp']
        for fields in [{'read_roots':[str(self.repo)]}, {'procedure':str(self.repo/'other')},
                       {'write_roots':[str(self.report)]}, {'network':True}, {'repository_reads':['/foreign']}]:
            scope = {**self.scope(value),**fields}
            with self.subTest(fields=fields), self.assertRaises(Refusal):
                scoped_task('bp',task,{'receipt':encode({'task_scopes':{'bp':scope}})})
        self.s.config = value
        with self.assertRaises(Refusal): local_native.source_roots(self.s, {'task':'bp'}, str(self.repo/'other'))

    def test_changed_material_and_wrong_original_board_binding_refuse(self):
        value = self.draft(); basis = configuration.basis(self.s,self.f.boards,value,['bp'])
        self.report.write_text('changed')
        with self.assertRaises(Refusal): configuration.apply(self.s,self.f.boards,value,{'basis':basis,'authority':'fictional Work'})
        self.report.write_text('safe supplied procedure\n')
        self.f.conn.execute("UPDATE coordinator_grants_v1 SET owner='foreign' WHERE role='Branch'")
        with self.assertRaises(Refusal): configuration.basis(self.s,self.f.boards,value,['bp'])

    def current_module_entry(self, module_root=Path('/src/tools/coordinator-runtime/coordinator_runtime')):
        # The entire current production module set, not 65 dummy list entries.
        modules = sorted(module_root.glob('*.py'))
        self.assertEqual(len(modules), 65)
        files = {}
        for module in modules:
            relative = 'runtime/' + module.name
            target = self.repo/relative
            target.parent.mkdir(exist_ok=True)
            target.write_bytes(module.read_bytes())
            files[relative] = self.sha(target)
        self.git('add', 'runtime')
        self.git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                 '-c', 'commit.gpgsign=false', 'commit', '-qm', 'whole current production modules')
        entry = copy.deepcopy(self.entry)
        entry['configuration'] = digest(self.s.config)
        entry['source'] = {'repository':str(self.repo), 'commit':self.git('rev-parse','HEAD').strip(),
                           'files':files}
        entry['components'] = {'runtime':list(files)}
        # Preserve the old physical permission and historical safe procedure.
        old = str(self.repo/'component.py')
        entry['safe_files'][old] = self.sha(Path(old))
        entry['read_roots'] = [*(str(self.repo/p) for p in files), *entry['safe_files']]
        return entry

    def test_whole_current_modules_and_historical_permissions_through_basis_apply(self):
        historical = self.draft()
        basis = configuration.basis(self.s, self.f.boards, historical, ['bp'])
        configuration.apply(self.s, self.f.boards, historical,
                            {'basis':basis, 'authority':'fictional historical selection'})
        self.s.config = historical
        for board in self.f.boards.values():
            board.config = historical; board.selected = historical['roles'][board.role]
        history = self.s.rows('SELECT * FROM configuration_transitions')
        grants = [tuple(r) for r in self.f.conn.execute('SELECT * FROM coordinator_grants_v1')]
        entry = self.current_module_entry()
        value = self.draft(entry)
        task = value['tasks']['bp']
        self.assertTrue(set(historical['tasks']['bp']['effect_authority']['read_roots'])
                        <= set(task['effect_authority']['read_roots']))
        self.assertTrue(set(entry['read_roots']) <= set(task['scope_roots']))
        self.assertEqual(value['limits'], historical['limits'])
        basis = configuration.basis(self.s, self.f.boards, value, ['bp'])
        configuration.apply(self.s, self.f.boards, value,
                            {'basis':basis, 'authority':'fictional whole current source selection'})
        self.assertEqual(self.s.rows('SELECT * FROM configuration_transitions WHERE position=1'), history)
        self.assertEqual(grants, [tuple(r) for r in self.f.conn.execute('SELECT * FROM coordinator_grants_v1')])
        selected = json.loads(configuration.latest(self.s)['configuration'])
        self.assertEqual(selected['prospective_scope_selection']['read_ceiling_extensions']['bp'], entry)
        self.assertEqual(historical['prospective_scope_selection']['read_ceiling_extensions']['bp']['source']['commit'],
                         self.head)

    def test_whole_extent_above_current_budget_refuses_even_with_capacity_option(self):
        entry = self.current_module_entry()
        self.s.config['limits']['max_files'] = len(entry['read_roots']) - 1
        entry['configuration'] = digest(self.s.config)
        with self.assertRaisesRegex(Refusal, 'bounded exact material lists'):
            self.draft(entry, capacity={'authority':'fictional prospective capacity choice',
                'evidence':'cannot enlarge the current read representation',
                'limits':{'max_files':len(entry['read_roots'])}})

    def test_material_byte_bounds_and_malformed_lists_still_refuse(self):
        for bad in [None, {}, 'files', [], [str(self.report),str(self.report)], [1]]:
            with self.subTest(roots=bad), self.assertRaises(Refusal):
                self.draft({**self.entry, 'read_roots':bad})
        self.report.write_bytes(b'x' * (1048576 + 1))
        entry = copy.deepcopy(self.entry)
        entry['safe_files'][str(self.report)] = self.sha(self.report)
        with self.assertRaisesRegex(Refusal, 'bounded acquisition'): self.draft(entry)
