"""Tracked-only positive-mount producer fiction, never live/native acceptance.

Real selectors, admission, Git, QA sandbox/readback, receiving and scheduling;
model semantics and Board actors use the explicit existing fictional transport.
No native provider is started. Retain /fixtures, including failed attempts.
"""
import asyncio
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import _receiving485_fixtures as f
import test_report512 as report_fixture
from coordinator_runtime import configuration, local_native, ordinary, processing_admission, prospective, service, branches
from coordinator_runtime.contracts import Refusal, digest, encode, scoped_task, validate_config
from coordinator_runtime.store import Store
from test_task_text510 import fictional_config


class RepositorySelection(unittest.TestCase):
    def setUp(self):
        self.area = Path(tempfile.mkdtemp(dir='/fixtures', prefix='repository534-'))
        self.config = fictional_config(self.area)
        for name in ['branch-proposer', 'reviews-proposer']:
            self.config['tasks'][name]['effect_authority'].update(
                operations=['read-source'], read_roots=['/src/tools/coordinator-runtime', str(self.area/'procedure.md')])
        self.store = Store(validate_config(self.config))
        self.addCleanup(self.store.close)

    def candidate(self, options):
        return configuration.candidate(self.store, str(self.area/'candidate.json'), [], scope_options=options)

    def test_default_G1_and_G2_still_refuse_without_explicit_selection(self):
        row = {'task': 'branch-proposer', 'package': 'fictional-p'}
        with self.assertRaisesRegex(Refusal, 'native source outside') as native:
            local_native.source_roots(self.store, row, '/src')
        with self.assertRaisesRegex(Refusal, 'may only narrow') as selector:
            self.candidate({'read_roots': {'branch-proposer': ['/src']}})
        selected = {'future_intake': True, 'tasks': ['branch-proposer'],
                    'software_admission': {'authority': 'Fictional original Work admission', 'max_packages': 1,
                        'scopes': {'topic': {'submitters': ['fictional-submitter'], 'package_prefix': 'p-',
                            'evidence': 'Fictional source authority', 'task_scopes': {'branch-proposer': {}}}}}}
        with self.assertRaisesRegex(Refusal, 'selected scoped Branch/QA') as admission:
            processing_admission.validate(self.store, selected)
        print('DEFAULT_GAPS534='+encode({'G1_native': str(native.exception),
              'G1_selector': str(selector.exception), 'G2_admission': str(admission.exception)}))

    def test_selected_repository_identity_is_not_a_filesystem_root(self):
        options = {'repository_reads': {n: ['/src'] for n in ['branch-proposer', 'reviews-proposer']},
                   'package_scoped_proposals': ['branch-proposer']}
        candidate = self.candidate(options)
        configuration.validate_changes(self.store, candidate, ['branch-proposer', 'reviews-proposer'])
        for name in ['branch-proposer', 'reviews-proposer']:
            self.assertEqual(candidate['tasks'][name]['effect_authority'], self.config['tasks'][name]['effect_authority'])
        self.store.config = candidate
        scope = {'cwd': '/src/tools/coordinator-runtime', 'read_roots': [str(self.area/'procedure.md')], 'write_roots': [],
                 'procedure': str(self.area/'procedure.md'), 'resource_evidence': ['Fictional retained procedure authority'],
                 'repository_reads': ['/src']}
        self.store.db.execute('INSERT INTO admissions VALUES(?,?,?,NULL)',
                             ('fictional-p', candidate['actor'], encode({'task_scopes': {'branch-proposer': scope}})))
        for name in ['branch-proposer', 'reviews-proposer']:
            row = {'task': name, 'package': 'fictional-p'}
            local_native.source_roots(self.store, row, '/src', repository=True)
            for value, repository in [('/src', False), ('/src/arbitrary-private.py', False),
                                      ('/src/tools', True), ('/', True), ('/foreign', True)]:
                with self.subTest(task=name, value=value, repository=repository), self.assertRaises(Refusal):
                    local_native.source_roots(self.store, row, value, repository=repository)
        # Missing per-package selection never inherits the configured identity.
        with self.assertRaises(Refusal):
            local_native.source_roots(self.store, {'task': 'branch-proposer', 'package': 'other'}, '/src', repository=True)
        for change in [{'repository_reads': ['/foreign']}, {'read_roots': ['/src']},
                       {'write_roots': ['/src/tools/coordinator-runtime']}, {'network': True},
                       {'procedure': '/src/arbitrary.py'}, {'ordinary_effects': {'kind': 'local-ref'}}]:
            wrong = {**scope, **change}
            with self.subTest(change=change), self.assertRaises(Refusal):
                scoped_task('branch-proposer', candidate['tasks']['branch-proposer'],
                            {'receipt': encode({'task_scopes': {'branch-proposer': wrong}})})

    def test_selector_authority_negatives_and_conservation(self):
        legacy = self.candidate({})
        options = {'repository_reads': {'branch-proposer': ['/src']}, 'package_scoped_proposals': ['branch-proposer']}
        candidate = self.candidate(options)
        expected = copy.deepcopy(legacy)
        expected['prospective_scope_selection'] = options
        task = expected['tasks']['branch-proposer']
        task.update(repository_reads=['/src'], require_package_scope=True, package_narrowing=True,
                    scope_roots=[*task['effect_authority']['read_roots'], task['cwd']],
                    scope_exclusions=expected['artifact_exclusions'])
        self.assertEqual(candidate, expected)
        self.assertEqual(len(candidate['tasks']), 8)
        self.assertEqual(len(candidate['tasks']['work-integrator']['routine_completion']['targets']), 7)
        with self.assertRaisesRegex(Refusal, 'explicitly selected task'):
            configuration.validate_changes(self.store, candidate, ['qa-execution'])
        forged = copy.deepcopy(candidate); forged['tasks']['branch-proposer']['effect_authority']['read_roots'].append('/src')
        with self.assertRaisesRegex(Refusal, 'unsupported current configuration delta'):
            configuration.validate_changes(self.store, forged, ['branch-proposer'])
        for options in [
                {'repository_reads': {'branch-proposer': ['/']}},
                {'repository_reads': {'branch-proposer': ['/foreign']}},
                {'repository_reads': {'branch-proposer': [str(Path.home()/'.codex')]}},
                {'repository_reads': {'qa-execution': ['/src']}},
                {'repository_reads': {'work-proposer': ['/src']}},
                {'repository_reads': {'missing': ['/src']}},
                {'package_scoped_proposals': ['reviews-proposer']},
                {'package_scoped_proposals': ['branch-integrator']},
                {'package_scoped_proposals': ['branch-proposer', 'branch-proposer']}]:
            with self.subTest(options=options), self.assertRaises(Refusal):
                self.candidate(options)
        altered = copy.deepcopy(self.config)
        altered['tasks']['branch-proposer']['network'] = True
        with self.assertRaises(Refusal):
            configuration.apply_scope_options(self.config, altered, {'package_scoped_proposals': ['branch-proposer']})


class AdmittedReceiving(f.Auto):
    git = f.Native.git

    def configure_fixture(self):
        f.Native.configure_fixture(self)
        self.output = self.area/'qa-output'; self.output.mkdir()
        self.marker = self.output/'marker.json'
        runner = '''from pathlib import Path
import errno,json
assert Path('code.py').read_text() == 'print("fictional frozen source")\\n'
try: Path('code.py').write_text('forbidden mutation')
except OSError as e: assert e.errno == errno.EROFS
else: raise AssertionError('candidate writable')
Path(MARKER).write_text(json.dumps({'answer':534,'readonly':True}))
'''.replace('MARKER', repr(str(self.marker)))
        readback = '''from pathlib import Path
import json
assert json.loads(Path(MARKER).read_text()) == {'answer':534,'readonly':True}
print('verified-534')
'''.replace('MARKER', repr(str(self.marker)))
        (self.repo/'runner.py').write_text(runner); (self.repo/'readback.py').write_text(readback)
        self.git('add', 'runner.py', 'readback.py')
        self.git('-c', 'user.name=Fictional Maker534', '-c', 'user.email=maker534@example.invalid',
                 'commit', '-m', 'Independent frozen-source and output procedure')
        self.head = self.git('rev-parse', 'HEAD')
        for name in ['qa-execution', 'qa-cleanup']:
            self.config['tasks'][name].update(require_package_scope=True, scope_roots=[str(self.area)])
        self.config['tasks']['qa-execution'].update(effects='owner-reconcile', capacity=5,
            responses={'consolidated': ['qa-cleanup']})
        self.config['tasks']['qa-execution']['effect_authority']['write_roots'] = [str(self.output)]
        self.config['tasks']['qa-cleanup'].update(responses={'qualification': ['branch-proposer']},
            publish_internal_results=True, software_handoffs={'Branch': ['branch-proposer']}, allowed_handoffs=['Branch'])
        self.config['tasks']['branch-proposer'].update(responses={'proposal': ['branch-integrator']})
        configuration.apply_scope_options(copy.deepcopy(self.config), self.config,
            {'package_scoped_cleanup': ['qa-cleanup'], 'package_scoped_proposals': ['branch-proposer']})
        self.scopes = {n: {'cwd': str(self.repo), 'read_roots': [str(self.repo), str(self.method)],
            'write_roots': [str(self.output)] if n == 'qa-execution' else [], 'network': False,
            'procedure': str(self.method), 'resource_evidence': ['Fictional exact independent QA534 procedure/resources']}
            for n in ['qa-execution', 'qa-cleanup', 'branch-proposer']}
        self.scopes['branch-proposer']['branch_binding'] = 'fictional-branch534'
        sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
        python = '/usr/bin/python3.12'
        def command(script, stdout):
            return {'argv': [python, '-B', str(self.repo/script)], 'executable_sha256': sha(python),
                    'script_sha256': sha(self.repo/script), 'stdout': stdout}
        self.scopes['qa-execution']['ordinary_effects'] = {
            'kind': 'local-qa', 'git': '/usr/bin/git', 'git_sha256': sha('/usr/bin/git'),
            'repository': str(self.repo), 'source_ref': 'refs/heads/fixture', 'source_head': self.head,
            'procedure_sha256': sha(self.method), 'resources': [{'key': 'fictional-534-output-'+self.area.name,
                'owner': self.config['roles']['Work']['owner'], 'authority': 'Fictional independent output lease', 'expires': 4000000000}],
            'acceptor': self.config['roles']['Work']['owner'], 'acceptance_authority': 'Independent fictional Work checks source/read-only/output observations',
            'timeout': 30, 'max_output': 4096, 'command': command('runner.py', ''),
            'readback': command('readback.py', 'verified-534\n'), 'known_exits': [0, 1],
            'source_capture': {'bwrap': '/usr/bin/bwrap', 'sha256': sha('/usr/bin/bwrap'), 'max_bytes': 1048576, 'max_files': 16},
            'public_executables': {r: {'path': python, 'bytes': Path(python).stat().st_size, 'sha256': sha(python)}
                                   for r in ['command', 'readback']}}

    def configure_selection(self, selection):
        f.Native.configure_selection(self, selection)
        selection['software_admission'] = {'authority': 'Fictional Work selects exact future software admission, never actual consent',
            'max_packages': 1, 'scopes': {'qa534': {'submitters': [self.config['roles']['Work']['owner']],
            'package_prefix': 'qa534-', 'task_scopes': self.scopes,
            'evidence': 'Fictional exact resource and original-package receiver authority'}}}

    def init_receiving(self):
        self.start_auto()
        self.models = f.NativeModels(self)
        self.dispatch = service.Dispatcher(self.store, self.boards, self.models)
        policies = {n: {'task_hash': digest(t), 'software_handoffs': t.get('software_handoffs', {}),
                       'ordinary_effects': 'admitted-v1' if n == 'qa-execution' else False}
                    for n, t in self.config['tasks'].items()}
        prospective.select(self.store, self.config['roles']['Work']['owner'], {
            'configuration': digest(self.config), 'authority': 'Fictional exact future QA execution and receivers',
            'expires': self.store.clock()+3600, 'grants': {r: self.store.enrollment(r)['grant_id'] for r in self.config['roles']},
            'tasks': policies, 'processing_capability': self.key})
        self.source = self.post('Execute independent frozen source and output test', 'QA', 'qa534-original', topic='qa534')
        self.initial[self.source['id']] = 'qa-execution'
        processing_admission.admit(self.store, self.source['id'])
        issuer = self.config['roles']['Work']['owner']
        branches.register(self.store, issuer, {'id': 'fictional-branch534', 'repository': str(self.repo),
            'origin': 'https://example.invalid/fictional.git', 'ref': 'refs/heads/fixture',
            'incarnation': 'fictional-ref534-life', 'scope': 'qa534-original', 'root': issuer,
            'authority': 'Fictional Work chooses original-package association'})
        branches.accept(self.store, 'fictional-branch534', issuer, 'Actual fixture member accepts fixture association, no native owner claim')
        self.task_result = self.meaning
        self.pause = True
        schedule = self.dispatch.schedule_candidate
        self.dispatch.schedule_candidate = lambda j: False if self.pause and j['task'] == 'branch-proposer' else schedule(j)

    def meaning(self, job, out):
        out['findings'] = [{'source': self.store.event(m['event']), 'hash': m['hash']}
                           for m in json.loads(job['members'])]
        if job['task'] == 'qa-cleanup':
            out['category'] = 'qualification'
            out['handoffs'] = [{'recipient': 'Branch', 'kind': 'work', 'text': 'Read original qualification in its admitted package',
                               'ref': job['package'], 'required': 'settled'}]
            out['no_handoff_reason'] = None
        if job['task'] == 'branch-proposer':
            out['category'] = 'proposal'

    async def drive(self, predicate, count=28):
        for _ in range(count):
            await self.dispatch.tick(); await self.drain()
            if predicate(): return
        self.save('unreached534', {'outboxes': self.store.rows('SELECT * FROM outboxes'),
            'queues': self.store.rows('SELECT * FROM queue'), 'links': self.store.rows('SELECT * FROM processing_delivery_links')})
        raise AssertionError('534 predicate unreached: '+repr(self.dispatch.runtime_errors)+' '+repr(self.store.rows('SELECT task,state,hold_reason FROM jobs')))

    def prepare_return(self):
        self.init_receiving()
        async def run():
            await self.drive(lambda: self.store.one("SELECT * FROM ordinary_runs WHERE state='reconciled'"))
            row = self.store.one('SELECT * FROM ordinary_runs')
            self.assertIsNone(self.store.one("SELECT id FROM jobs WHERE task='qa-cleanup'"))
            self.assertFalse(ordinary.accepted_package(self.store, 'qa534-original'))
            for actor in [self.config['actor'], self.store.controller, self.store.attempt(row['attempt'])['session']]:
                with self.assertRaises(Refusal):
                    await ordinary.accept(self.store, actor, row['attempt'], 'accepted', {
                        'execution_hash': digest(json.loads(row['receipt'])), 'rationale': 'Cannot borrow authority', 'unknowns': []})
            await ordinary.accept(self.store, self.config['roles']['Work']['owner'], row['attempt'], 'accepted', {
                'execution_hash': digest(json.loads(row['receipt'])),
                'rationale': 'Independent source assertion, kernel EROFS, exact separate 534 marker and nonempty readback satisfy fixture procedure', 'unknowns': []})
            await self.drive(lambda: any(self.store.event(q['event']).get('source_delivery')
                for q in self.store.rows("SELECT * FROM queue WHERE task='branch-proposer'")))
        asyncio.run(run())
        return next(q for q in self.store.rows("SELECT * FROM queue WHERE task='branch-proposer'")
                    if self.store.event(q['event']).get('source_delivery'))

    def test_original_package_QA_acceptance_cleanup_and_Branch_receiving(self):
        queue = self.prepare_return()
        self.assertEqual(queue['package'], 'qa534-original')
        self.assertTrue(self.store.processing.task(queue))
        self.assertEqual(len(self.config['tasks']), 8)
        self.assertEqual(self.config['tasks']['qa-execution']['capacity'], 5)
        self.assertEqual(self.config['tasks']['branch-proposer']['role'], 'Branch')
        record = self.store.one('SELECT * FROM processing_admissions')
        self.assertEqual(record['event'], self.source['id'])
        self.assertFalse(json.loads(record['receipt'])['software_admission']['native_owner_consent'])
        self.pause = False
        asyncio.run(self.drive(lambda: self.store.one("SELECT j.id FROM jobs j JOIN attempts a ON a.id=j.active_attempt WHERE j.task='branch-proposer' AND a.collected IS NOT NULL")))
        job = self.store.one("SELECT * FROM jobs WHERE task='branch-proposer'")
        self.assertEqual(job['package'], self.source['package'])
        event = self.store.event(queue['event'])
        self.assertIn('source_result', event['body'])
        self.assertEqual(event['body']['source_result']['category'], 'qualification')
        self.assertEqual(self.store.one('SELECT receipt FROM processing_admissions')['receipt'], record['receipt'])
        self.assertEqual(json.loads(self.marker.read_text()), {'answer': 534, 'readonly': True})
        self.save('positive534', {'job': job, 'original': self.source, 'received': event})

    def test_receiver_wrong_package_source_task_collection_currentness_and_association_refuse(self):
        queue = self.prepare_return()
        self.assertTrue(self.store.processing.task(queue))
        event = self.store.event(queue['event'])
        original_event = self.store.event
        for field, value in [('package', 'wrong-package'), ('body', {**event['body'], 'source_result': {'semantic': 'DONE'}})]:
            changed = {**event, field: value}
            with self.subTest(field=field), patch.object(self.store, 'event', side_effect=lambda key: changed if key == event['id'] else original_event(key)):
                try: allowed = processing_admission.permits(self.store, queue)
                except Refusal: allowed = False
                self.assertFalse(allowed)
        original_job = self.store.job
        source_job = self.store.job(self.store.one('SELECT job FROM outboxes WHERE id=?', (event['source_delivery']['id'],))['job'])
        for change in [{'task': 'qa-execution', 'phase': 'execution'}, {'package': 'wrong-package'},
                       {'members': encode([{'event': self.source['id'], 'hash': 'foreign-hash', 'package': 'qa534-original'}])},
                       {'active_attempt': self.store.one("SELECT active_attempt FROM jobs WHERE task='qa-execution'")['active_attempt']}]:
            with self.subTest(change=change), patch.object(self.store, 'job', side_effect=lambda key: {**source_job, **change} if key == source_job['id'] else original_job(key)):
                self.assertFalse(processing_admission.permits(self.store, queue))
        original_attempt = self.store.attempt
        for change in [{'collected': None}, {'ended': None}, {'capture': 'partial'}, {'exit': 1},
                       {'controller': 'foreign-collector'}, {'job': 'foreign-job'}]:
            with self.subTest(change=change), patch.object(self.store, 'attempt', side_effect=lambda key: {**original_attempt(key), **change} if key == source_job['active_attempt'] else original_attempt(key)):
                self.assertFalse(processing_admission.permits(self.store, queue))
        with patch.object(self.store.processing, 'event', return_value=False):
            self.assertFalse(self.store.processing.task(queue))
        with patch.object(self.store.processing, 'current', side_effect=Refusal('revoked current capability')):
            with self.assertRaises(Refusal): self.store.processing.task(queue)
        with patch.object(branches, 'association', return_value={'accepted': None}):
            self.assertFalse(processing_admission.permits(self.store, queue))
        branch = self.store.one('SELECT * FROM branch_associations')
        original_one = self.store.one
        with patch.object(self.store, 'one', side_effect=lambda sql, parameters=(): {**branch, 'scope': 'foreign'} if sql.startswith('SELECT id,scope,repository,ref') else original_one(sql, parameters)):
            with self.assertRaises(Refusal): processing_admission.permits(self.store, queue)
        with patch.object(self.store, 'one', side_effect=lambda sql, parameters=(): {'hold': 'original source stays held'}
                if sql == 'SELECT hold FROM events WHERE id=?' and parameters == (self.source['id'],)
                else original_one(sql, parameters)):
            self.assertFalse(processing_admission.permits(self.store, queue))
        self.assertTrue(self.store.processing.task(queue))
        self.assertIsNone(self.store.one("SELECT active_attempt FROM jobs WHERE task='branch-proposer'")['active_attempt'])
        self.save('negatives534')


class RepositoryPoints(f.Auto):
    """Real Git acquisition from the separately initialized owned /src fiction."""
    git = f.Native.git
    init_native = f.Native.init_native
    source_event = f.Native.source_event

    def configure_fixture(self):
        f.Native.configure_fixture(self)
        self.repo = Path('/src')
        self.head = self.git('rev-parse', 'HEAD')
        for name in ['branch-proposer', 'reviews-proposer']:
            self.config['tasks'][name]['effect_authority'].update(operations=['read-source'],
                read_roots=['/src/tools/coordinator-runtime', str(self.method)], write_roots=[])
        self.config['tasks']['reviews-proposer']['scope_roots'].append('/src')
        configuration.apply_scope_options(copy.deepcopy(self.config), self.config,
            {'repository_reads': {'branch-proposer': ['/src'], 'reviews-proposer': ['/src']}})

    def configure_selection(self, selection):
        f.Native.configure_selection(self, selection)
        selection['service']['reviews']['reviews-proposer']['components']['component']['paths'] = [
            'tools/coordinator-runtime/templates/branch-repository.md']

    def test_selected_identity_native_snapshot_and_original_review_material(self):
        self.init_native()
        scopes = json.loads(self.store.one('SELECT receipt FROM admissions WHERE package=?', ('pkg',))['receipt'])
        scopes['task_scopes']['reviews-proposer'].update(
            cwd=str(self.area), read_roots=['/src/tools/coordinator-runtime', str(self.method)],
            repository_reads=['/src'])
        self.store.admit('pkg', self.config['roles']['Branch']['owner'], scopes)
        row = {'task': 'branch-proposer', 'package': 'pkg', 'role': 'Branch', 'phase': 'proposer'}
        value, resources = local_native.snapshot(self.store, {'native': 'branch', 'id': self.branchid}, row)
        self.assertEqual(value['head'], self.head)
        self.assertTrue(resources)
        self.assertEqual(value['association']['scope'], 'pkg')
        with self.assertRaisesRegex(Refusal, 'original admitted package'):
            local_native.snapshot(self.store, {'native': 'branch', 'id': self.branchid}, {**row, 'package': 'foreign'})
        source = self.source_event()
        original = {'task': 'reviews-proposer', 'role': 'Reviews', 'phase': 'proposer', 'package': 'pkg', 'event': source['id']}
        components = local_native.review_material_scope(self.store, original)
        self.assertEqual(components, {branches.review_component(self.branchid, source['body']['review'])})
        policy = self.store.processing.current()[1]['service']['reviews']['reviews-proposer']
        acquired = f.reviews.material(policy, source['body']['review'], None)
        self.assertEqual(set(acquired['source']), {self.head+':tools/coordinator-runtime/templates/branch-repository.md'})
        # This capability does not manufacture an original native context.
        with self.assertRaisesRegex(Refusal, 'original native reviewer/context/collector unavailable'):
            local_native.snapshot(self.store, {'native': 'review', 'component': next(iter(components))})


class PartialConservation534(report_fixture.Reports):
    """Existing report ancestry cases with an owned fictional method only.

    No external method definitions or real native execution qualification.
    The original report/receipt/return/collector checks execute unchanged.
    """
    def configure_fixture(self):
        f.Native.configure_fixture(self)
        self.config['tasks']['reviews-integrator']['responses'].update(
            scope=['work-proposer'], blocker=['work-proposer'])

    def configure_selection(self, selection):
        f.Native.configure_selection(self, selection)
        selection['service']['report_tasks'] = ['reviews-integrator']


if __name__ == '__main__':
    unittest.main()
