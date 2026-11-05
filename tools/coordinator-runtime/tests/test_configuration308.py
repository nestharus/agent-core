"""Isolated same-journal protocol fiction; all native profile/session/turn fields NULL.

Store/transition/processing/Board/publication code runs against owned fixtures.
Only native configuration validation, actor/membership and allocation are seams;
no fabricated Root/provider/native result, identity, consent or elapsed clock.
"""
from contextlib import contextmanager
import copy
import errno
import fcntl
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from coordinator_runtime import configuration, processing, publication, service_recovery, resource_scopes
from coordinator_runtime.board import module_at, EXTENSION, DELIVERY_SCHEMA, SOFTWARE_SCHEMA
from coordinator_runtime.contracts import Refusal, digest, encode, scoped_task
from coordinator_runtime.store import Store
from coordinator_runtime import store as store_module
from test_processing188 import engine_config, FixturePool
from test_retained168 import BoardShell


class Shell(BoardShell):
    def __init__(self, public):
        self.public, self.actor = public, 'fictional-Work'

    def bounded(self, *args, **kwargs):
        return self.public.bounded(*args, **kwargs)

    def notify(self, conn, recipients, post, thread, kind, title, actor, push):
        # Native transport remains absent; normal immutable Board rows are real.
        for recipient in recipients:
            conn.execute("INSERT INTO notification_outbox(recipient,post_seq,thread_id,event,title,sender,created_at,route) VALUES(?,?,?,?,?,?,?,'managed')",
                         (recipient, post, thread, kind, title, actor, 'fictional-time'))


class Board(processing.ProcessingBoard):
    def __init__(self, runtime, role, conn, public):
        self.config, self.role, self.runtime = runtime.config, role, runtime
        self.selected, self.conn = runtime.config['roles'][role], conn
        self.store, self.identity = Shell(public), ('fictional-board-device', 'fictional-board-inode')

    @contextmanager
    def opened(self, **kwargs):
        yield self.conn  # Explicit membership/catalog seam; native fields NULL.


class CurrentConfiguration(unittest.TestCase):
    def setUp(self):
        self.directory = Path(tempfile.mkdtemp(dir='/fixtures'))
        self.public = module_at('/src/tools/message-board', 'board_store')
        self.database = self.public.database(str(self.directory/'fictional-board.sqlite3'))
        self.conn = self.database.__enter__()
        self.addCleanup(self.database.__exit__, None, None, None)
        self.conn.executescript(EXTENSION.replace('profile TEXT NOT NULL', 'profile TEXT')+DELIVERY_SCHEMA+SOFTWARE_SCHEMA)
        value = engine_config(self.directory)
        value.update(board_library='/src/tools/message-board',
                     operator_cli=str(self.directory/'fictional-old-runtime/coordinator'),
                     operator_config=str(self.directory/'original.json'),
                     canonical_publication={'method': 'retention-same-inode-v1', 'library': '/src/tools/coordinator-runtime/tests/fixture_snapshot'},
                     control_receive={'mode': 'cooperative', 'instructions': str(self.directory/'fictional-old-runtime/templates/coordinator-receive.md')},
                     execution_pool_routes=str(self.directory/'routes.toml'),
                     software_delegation={'grantor': 'fictional-Work', 'authority': 'fictional original decision', 'boundary': 'new-journal-only'},
                     diagnosis={'binding': value['classifier']['binding'], 'profile': None, 'cwd': '/fixtures'},
                     enabled=False)
        Path(value['execution_pool_routes']).write_text('[rotation]\nstate_dir="/fixtures/fictional-pool-state"\n[providers.codex]\npool=[".codex2",".codex3",".codex5"]\nmanual_profiles=[".codex",".codex2",".codex3",".codex4",".codex5"]\n')
        value['delivery']['recipients'] = {'Work': {'session': None}}
        value['limits'].update(max_board_deliveries=512, max_result_bytes=262144, max_bytes=33554432)
        for role, selected in value['roles'].items():
            selected.update(owner='fictional-'+role, board_id='fictional-board', legacy_hold='fictional unresolved original '+role)
            self.conn.execute("INSERT INTO sessions(session,campaign,role,profile,status,registered_at,last_seen_at) VALUES(?,'fictional','fictional',NULL,'active','fictional-time','fictional-time')", (selected['owner'],))
        self.conn.execute("INSERT INTO sessions(session,campaign,role,profile,status,registered_at,last_seen_at) VALUES(?,'fictional','coordinator-runtime',NULL,'active','fictional-time','fictional-time')", (value['actor'],))
        for name, task in value['tasks'].items():
            role = task['role']
            template = {'Work': 'work-catalog.md', 'Branch': 'branch-repository.md', 'Reviews': 'reviews-selected.md', 'QA': 'qa-package.md'}[role]
            task.update(cwd='/fixtures', templates=[str(self.directory/'fictional-old-runtime/templates'/template)],
                        sandbox='read-only', network=False, purpose='fictional isolated purpose', authority='fictional isolated authority',
                        effect_authority={'owner': 'fictional-'+role, 'operations': ['read-reports'], 'read_roots': ['/fixtures'], 'write_roots': []})
            if name in {'bi', 'qe'}:
                task.update(require_package_scope=True, scope_roots=['/fixtures'], effects='owner-reconcile')
                task['effect_authority']['operations'] = ['read-source']
        with patch.object(store_module, 'SCHEMA', store_module.SCHEMA.replace('profile TEXT NOT NULL', 'profile TEXT')):
            self.runtime = Store(value, controller='fictional-maker-controller', clock=lambda: 1000.)
        self.addCleanup(self.runtime.close)
        self.attach_pool(self.runtime)
        for role in value['roles']:
            self.runtime.db.execute('INSERT INTO enrollments VALUES(?,?,?,?,?,0,?,NULL)',
                                    (role, 'fictional-'+role, None, 'fictional-grant-'+role, 0, 'fictional unresolved original '+role))
            self.runtime.db.execute('INSERT INTO cursors VALUES(?,7)', (role,))
            info = self.runtime.path.stat()
            self.conn.execute('INSERT INTO coordinator_grants_v1 VALUES(?,?,?,?,NULL,?,?,?,?,?,?,?,?,?)',
                              ('fictional-grant-'+role, 'fictional-board', role, 'fictional-'+role, value['actor'], str(self.runtime.path),
                               info.st_dev, info.st_ino, 0, 'fictional-Work', 'fictional original decision', 'fictional-time', 'fictional-revoked'))
            self.conn.execute('INSERT INTO coordinator_software_grants_v1 VALUES(?,?,?)',
                              ('fictional-grant-'+role, '{}', digest(value)))
            self.conn.execute('INSERT INTO coordinator_delivery_grants_v1 VALUES(?,?,?,?)',
                              ('fictional-grant-'+role, encode({}), encode(['alert']), 'fictional original decision'))
        self.boards = self.make_boards(self.runtime)
        self.originals = []
        for n, role in enumerate(value['roles']):
            event = {'id': 'fictional-original-'+role, 'role': role, 'recipient': 'fictional-'+role, 'kind': 'board', 'post': n+1,
                     'allowed_tasks': ['wp'], 'body': 'fictional retained source', 'package': None}
            # Already retained stopped inputs; fixture construction is not new
            # intake through a revoked enrollment.
            with self.runtime.tx():
                self.runtime.db.execute('INSERT INTO events(id,role,payload,hash,received,hold) VALUES(?,?,?,?,900,?)',
                                        (event['id'], role, encode(event), digest(event), 'fictional original hold'))
                processing.note_source(self.runtime, event['id'])
            self.originals.append(event)
        for n in range(67):
            with self.runtime.tx():
                self.runtime._outbox('Work', 'Work', 'alert', {'fictional': n}, event=self.originals[0]['id'])
        # Original unfinished collector/debt with NULL native fields. This is not
        # a service/native encounter or actual parent END.
        source = self.originals[0]
        self.runtime.db.execute("INSERT INTO jobs(id,role,phase,task,members,controller,token,created,effects) VALUES('fictional-old-job','Work','proposer','wp',?,'fictional-old-collector','fictional-token',900,'unknown')",
                                (encode([{'event': source['id'], 'hash': digest(source)}]),))
        self.runtime.db.execute("INSERT INTO attempts(id,kind,event,controller,profile,binding,created) VALUES('fictional-original-attempt','classifier',?,?,NULL,?,900)",
                                (source['id'], self.runtime.controller, encode(value['classifier']['binding'])))
        old = self.processing_selection(retained=[source['id']])
        self.oldkey = processing.select(self.runtime, self.boards, old)['capability']
        self.runtime.db.execute("INSERT INTO processing_runs VALUES('fictional-old-collector',?,'owned',900)", (self.oldkey,))
        processing.revoke(self.runtime, self.boards, self.oldkey)
        self.original = copy.deepcopy(value)
        self.value = configuration.candidate(self.runtime, str(self.directory/'current.json'), ['bi', 'qe'])
        Path(self.value['operator_config']).write_text(encode(self.value))
        # The NULL-native fixture cannot satisfy canonical UUID/profile config
        # validation. Only that existing boundary is substituted; all transition
        # policy, exact-delta, binding and protocol checks execute unchanged.
        self.validation = patch.object(configuration, 'validate_config', side_effect=self.fixture_config)
        self.validation.start(); self.addCleanup(self.validation.stop)

    def fixture_config(self, value):
        self.assertEqual(value['profiles'], [None])
        self.assertTrue(all(r['profile'] is None for r in value['roles'].values()))
        self.assertTrue(all(t['profile'] is None for t in value['tasks'].values()))
        return value

    def attach_pool(self, runtime):
        runtime.execution_pool = FixturePool()
        from coordinator_runtime.execution_pool import _module
        public_pool = _module.Pool(runtime.config['execution_pool_routes'])
        # No native profile allocation. Real public control parsing still runs.
        public_pool.eligible = lambda enabled, authorized: self.assertEqual(authorized, [None])
        runtime.execution_pool.pool = public_pool

    def make_boards(self, runtime):
        return {r: Board(runtime, r, self.conn, self.public) for r in runtime.config['roles']}

    def processing_selection(self, retained=()):
        return {'basis': processing.basis(self.runtime, self.boards), 'authority': 'fictional bounded current duty',
                'expires': 1060., 'retained_events': list(retained), 'recover_controls': {}, 'future_intake': True,
                'tasks': list(self.runtime.config['tasks']), 'max_starts': 20,
                'max_shared_rows': 512, 'max_shared_payload_bytes': 1048576, 'max_runtime_rows': 512}

    def selection(self):
        return {'basis': configuration.basis(self.runtime, self.boards, self.value, list(self.value['tasks'])),
                'authority': 'fictional Work prospective configuration decision and why'}

    def transition(self):
        selection = self.selection()
        result = configuration.apply(self.runtime, self.boards, self.value, selection)
        old = self.runtime
        with patch.object(store_module, 'SCHEMA', store_module.SCHEMA.replace('profile TEXT NOT NULL', 'profile TEXT')):
            self.runtime = Store(self.value, controller='fictional-new-collector', clock=lambda: 1000.)
        self.addCleanup(self.runtime.close)
        self.attach_pool(self.runtime)
        self.boards = self.make_boards(self.runtime)
        return old, result

    def issue(self):
        key = processing.select(self.runtime, self.boards, self.processing_selection())['capability']
        self.runtime.processing = processing.Access(self.runtime, key, self.boards)
        return key

    def fresh(self, name='fictional-future'):
        event = {**self.originals[0], 'id': name, 'post': 100, 'body': 'fictional prospective source'}
        self.runtime.ingest(event)
        return event

    def test_same_inode_preserves_four_sources_67_outboxes_and_unknown_debt(self):
        before = configuration.journal(self.runtime)
        identity = self.runtime.path.stat()
        grants = [tuple(r) for r in self.conn.execute('SELECT * FROM coordinator_grants_v1')]
        caps = [tuple(r) for r in self.conn.execute('SELECT * FROM coordinator_software_grants_v1')]
        old, result = self.transition()
        after = configuration.journal(self.runtime)
        self.assertEqual({k:v for k,v in before.items() if k not in {'configuration_transitions','sqlite_sequence'}},
                         {k:v for k,v in after.items() if k not in {'configuration_transitions','sqlite_sequence'}})
        self.assertEqual((identity.st_dev, identity.st_ino), (self.runtime.path.stat().st_dev, self.runtime.path.stat().st_ino))
        self.assertEqual(self.runtime.one('SELECT COUNT(*) AS n FROM events')['n'], 4)
        self.assertEqual(self.runtime.one('SELECT COUNT(*) AS n FROM outboxes')['n'], 67)
        self.assertEqual(grants, [tuple(r) for r in self.conn.execute('SELECT * FROM coordinator_grants_v1')])
        self.assertEqual(caps, [tuple(r) for r in self.conn.execute('SELECT * FROM coordinator_software_grants_v1')])
        self.assertEqual(self.runtime.one("SELECT value FROM meta WHERE key='configuration'")['value'], digest(self.original))
        self.assertFalse(result['historical_recovery'])
        for sql in ('DELETE FROM configuration_transitions', "UPDATE configuration_transitions SET issuer='fictional-foreign'"):
            with self.assertRaises(sqlite3.IntegrityError): self.runtime.db.execute(sql)
        with self.assertRaises(Refusal):
            with old.tx(): old.db.execute("UPDATE cursors SET seq=999")
        self.assertEqual(self.runtime.one('SELECT seq FROM cursors')['seq'], 7)

    def test_current_grant_preserves_old_binding_and_strict_retained_recovery(self):
        self.transition(); key = self.issue()
        grant = self.boards['Work'].verify_authority(self.runtime)
        self.assertIsNotNone(grant['revoked'])
        with self.assertRaises(Refusal): self.strict_original()
        with self.assertRaises(Refusal):
            service_recovery.predecessor_authority(self.runtime, 'fictional-Work', self.runtime.processing.current()[0], self.oldkey)
        service_recovery.predecessor_authority(self.runtime, 'fictional-Work', self.runtime.processing.current()[0], key)
        self.assertFalse(configuration.owned_service_conflict(self.runtime))
        self.assertEqual(self.runtime.one("SELECT state FROM processing_runs WHERE controller='fictional-old-collector'")['state'], 'owned')
        self.runtime.db.execute("INSERT INTO processing_runs VALUES('fictional-current-original',?,'owned',1000)", (key,))
        self.assertTrue(configuration.owned_service_conflict(self.runtime))
        self.assertIsNone(self.runtime.one('SELECT session FROM attempts')['session'])

    def strict_original(self):
        # Execute the real historical RetainedBoard predicate, not the current
        # ProcessingBoard's deliberately separate configuration resolver.
        from coordinator_runtime.retained import RetainedBoard
        with patch.object(self.boards['Work'], '_configuration', side_effect=lambda runtime, binding: digest(runtime.config)):
            RetainedBoard._original(self.boards['Work'], self.conn, self.runtime)

    def test_future_authority_does_not_admit_old_sources_outboxes_or_publication(self):
        self.transition(); self.issue()
        self.assertFalse(self.runtime.processing.event(self.originals[0]))
        old = self.runtime.one('SELECT * FROM outboxes LIMIT 1')
        self.assertFalse(configuration.outbox_allowed(self.runtime, old))
        with self.assertRaises(Refusal): self.boards['Work']._delivery_grant(self.conn, self.runtime, old)
        job = self.runtime.job('fictional-old-job')
        with self.assertRaises(Refusal): publication.publish(self.runtime, self.boards['Work'], job, None, None, {})
        for field in ('retained_events', 'recover_controls'):
            value = self.processing_selection()
            value[field] = [self.originals[0]['id']] if field == 'retained_events' else {self.originals[0]['id']: 'fictional-attempt'}
            with self.assertRaises(Refusal): processing.select(self.runtime, self.boards, value)
        event = self.fresh()
        self.assertTrue(self.runtime.processing.event(event))
        attempt, actual = self.runtime.claim_classification()
        self.assertEqual(actual['id'], event['id'])
        record = self.runtime.attempt(attempt)
        self.assertIsNone(record['profile']); self.assertIsNone(record['session']); self.assertIsNone(record['turn'])
        self.assertEqual(json.loads(record['detail'])['processing_capability'], self.runtime.processing.key)

    def test_selectors_scopes_and_unknown_effect_policy(self):
        self.assertEqual(self.value['operator_cli'], '/src/tools/coordinator-runtime/coordinator')
        self.assertEqual(self.value['board_library'], '/src/tools/message-board')
        self.assertEqual(self.value['canonical_publication'], self.original['canonical_publication'])
        self.assertEqual(self.value['control_receive']['instructions'], '/src/tools/coordinator-runtime/templates/coordinator-receive.md')
        task = self.value['tasks']['bi']
        scope = {'cwd': '/src', 'read_roots': ['/src/tools/coordinator-runtime'], 'write_roots': [],
                 'procedure': 'fictional scoped ref inspection', 'resource_evidence': 'fictional exact source scope'}
        admission = {'receipt': encode({'task_scopes': {'bi': scope}})}
        with self.assertRaises(Refusal): scoped_task('bi', self.original['tasks']['bi'], admission)
        self.assertEqual(scoped_task('bi', task, admission)['cwd'], '/src')
        escaped = copy.deepcopy(admission); escaped['receipt'] = encode({'task_scopes': {'bi': {**scope, 'cwd': '/usr'}}})
        with self.assertRaises(Refusal): scoped_task('bi', task, escaped)
        self.transition(); self.issue()
        self.assertTrue(resource_scopes.blocked(self.runtime, {'role':'Branch', 'phase':'integrator', 'task':'bi', 'package':'fictional-new'}))
        self.assertEqual(configuration.task_for_job(self.runtime, self.runtime.job('fictional-old-job')), self.original['tasks']['wp'])

    def test_refused_wrong_issuer_changed_basis_and_unsupported_expansion(self):
        selection = self.selection()
        self.boards['Work'].store.actor = 'fictional-foreign'
        with self.assertRaises(Refusal): configuration.apply(self.runtime, self.boards, self.value, selection)
        self.boards['Work'].store.actor = 'fictional-Work'
        self.runtime.db.execute("UPDATE cursors SET seq=8 WHERE role='Work'")
        with self.assertRaises(Refusal): configuration.apply(self.runtime, self.boards, self.value, selection)
        for mutate in (lambda c: c.update(state_dir='/fixtures/fictional-new-journal'),
                       lambda c: c['tasks']['bi']['scope_roots'].append('/'),
                       lambda c: c['tasks']['wp'].update(capacity=1),
                       lambda c: c['roles']['Work'].update(owner='fictional-other'),
                       lambda c: c['tasks']['bi']['effect_authority']['write_roots'].append('/src')):
            value = copy.deepcopy(self.value); mutate(value)
            with self.assertRaises(Refusal): configuration.basis(self.runtime, self.boards, value, list(value['tasks']))
        self.assertIsNone(configuration.latest(self.runtime))

    def test_refused_active_capability_and_live_cooperative_lock(self):
        processing.select(self.runtime, self.boards, self.processing_selection())
        with self.assertRaises(Refusal): configuration.apply(self.runtime, self.boards, self.value, self.selection())
        for row in self.runtime.rows('SELECT id FROM processing_capabilities WHERE revoked IS NULL'):
            processing.revoke(self.runtime, self.boards, row['id'])
        fd = os.open(self.runtime.home/'service.lock', os.O_CREAT|os.O_RDWR, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX|fcntl.LOCK_NB)
            with self.assertRaises(Refusal): configuration.apply(self.runtime, self.boards, self.value, self.selection())
        finally: os.close(fd)
        self.assertIsNone(configuration.latest(self.runtime))

    def test_transaction_interruption_rolls_back_without_hash_edits_and_return_loss_reopens(self):
        before = configuration.journal(self.runtime)
        selection = self.selection()
        self.runtime.db.execute("CREATE TEMP TRIGGER fictional_interrupt BEFORE INSERT ON configuration_transitions BEGIN SELECT RAISE(ABORT,'fictional interruption'); END")
        with self.assertRaises(sqlite3.IntegrityError): configuration.apply(self.runtime, self.boards, self.value, selection)
        self.runtime.db.execute('DROP TRIGGER fictional_interrupt')
        self.assertEqual(before, configuration.journal(self.runtime))
        old, result = self.transition()  # Ignore result as a lost operational return.
        self.assertEqual(configuration.latest(self.runtime)['current'], digest(self.value))
        with self.assertRaises(Refusal): configuration.apply(old, self.make_boards(old), self.value, selection)
        self.assertEqual(self.runtime.one('SELECT COUNT(*) AS n FROM configuration_transitions')['n'], 1)
        self.assertEqual(self.runtime.one("SELECT value FROM meta WHERE key='configuration'")['value'], digest(self.original))

    def test_actual_original_collector_keeps_return_custody_without_current_effects(self):
        old, _ = self.transition()
        old.collect('fictional-original-attempt', {'exit': None, 'capture': 'incomplete',
                    'cleanup': 'original-obligations-held', 'result': None, 'error': 'fictional unavailable original'})
        row = self.runtime.attempt('fictional-original-attempt')
        self.assertIsNone(row['exit']); self.assertIsNone(row['collected'])
        self.assertIsNone(row['session']); self.assertIsNone(row['profile']); self.assertIsNone(row['turn'])
        self.assertEqual(row['state'], 'unknown')
        old.controller = 'fictional-foreign-controller'
        with self.assertRaises(Refusal):
            old.collect('fictional-original-attempt', {'exit': None})
        with self.assertRaises(Refusal):
            with old.tx(): old.db.execute("UPDATE jobs SET effects='none'")
        self.assertEqual(self.runtime.job('fictional-old-job')['effects'], 'unknown')

    def test_current_prospective_admission_is_scoped_and_cannot_unlock_old_package(self):
        from coordinator_runtime import processing_admission
        self.transition()
        scope = {'cwd': '/src', 'read_roots': ['/src/tools/coordinator-runtime'], 'write_roots': [],
                 'procedure': 'fictional bounded source inspection', 'resource_evidence': 'fictional exact independent scope'}
        selection = self.processing_selection()
        selection['software_admission'] = {'authority': 'fictional current admission decision', 'max_packages': 1,
            'scopes': {'runtime': {'submitters': ['fictional-submitter'], 'package_prefix': 'fictional-release-',
                'task_scopes': {'bi': scope}, 'evidence': 'fictional selected future resource evidence'}}}
        key = processing.select(self.runtime, self.boards, selection)['capability']
        self.runtime.processing = processing.Access(self.runtime, key, self.boards)
        event = {**self.originals[1], 'id': 'fictional-new-branch-input', 'post': 100,
                 'author': 'fictional-submitter', 'body': {'topic':'runtime'}, 'package': 'fictional-release-one', 'allowed_tasks': ['bi']}
        self.runtime.ingest(event)
        result = processing_admission.admit(self.runtime, event['id'])
        self.assertFalse(result['native_owner_consent']); self.assertFalse(result['acceptance_inferred'])
        self.assertEqual(result['receipt']['task_scopes']['bi'], scope)
        self.assertIsNone(self.runtime.one('SELECT accepted FROM admissions')['accepted'])
        self.assertTrue(processing_admission.permits(self.runtime, {'package': event['package'], 'event': event['id'], 'task':'bi'}))
        self.assertFalse(processing_admission.permits(self.runtime, {'package': event['package'], 'event': self.originals[1]['id'], 'task':'bi'}))
        self.assertIsNotNone(self.runtime.one("SELECT legacy_hold FROM enrollments WHERE role='Branch'")['legacy_hold'])

    def current_job(self):
        event = self.fresh()
        self.runtime.db.execute("INSERT INTO jobs(id,role,phase,task,members,controller,token,created,effects) VALUES('fictional-current-job','Work','proposer','wp',?,?,'fictional-new-token',1000,'none')",
                                (encode([{'event':event['id'],'hash':digest(event)}]), self.runtime.controller))
        with self.runtime.tx():
            attempt = self.runtime._attempt('task', None, 'fictional-current-job', self.value['tasks']['wp']['binding'], None)
            self.runtime.db.execute("UPDATE jobs SET active_attempt=? WHERE id='fictional-current-job'", (attempt,))
        job = self.runtime.job('fictional-current-job')
        self.boards['Work'].bind_software_attempt(self.runtime, job, attempt, None)
        return event, job

    def test_current_receiving_exact_intent_and_publication_dependency_keep_originals_separate(self):
        self.transition(); self.issue()
        event, job = self.current_job()
        configuration.require_current_job(self.runtime, job)
        with self.runtime.tx():
            key = self.runtime._outbox('Work', 'Work', 'work', {'fictional': 'bounded current source'}, event=event['id'], job=job['id'])
        outbox = self.runtime.one('SELECT * FROM outboxes WHERE id=?', (key,))
        self.assertTrue(configuration.outbox_allowed(self.runtime, outbox))
        # Shared logical addresses are fiction; no native session/profile/turn
        # or provider receipt is invented. Immutable public Board schema runs.
        post = self.conn.execute("INSERT INTO posts(author,recipient,topic,kind,text,created_at) VALUES(?,'fictional-Work','coordinator-runtime','handoff','fictional current pointer','fictional-time')", (self.value['actor'],)).lastrowid
        self.conn.execute('INSERT INTO threads VALUES(?,?,?,?,?)', (post,'fictional current','coordinator-runtime',self.value['actor'],'fictional-time'))
        self.conn.execute('INSERT INTO thread_posts VALUES(?,?)', (post,post))
        notice = self.conn.execute("INSERT INTO notification_outbox(recipient,post_seq,thread_id,event,title,sender,created_at,route) VALUES('fictional-Work',?,?,'open','fictional',?,'fictional-time','managed')", (post,post,self.value['actor'])).lastrowid
        grant = 'fictional-grant-Work'
        self.conn.execute("INSERT INTO coordinator_deliveries_v1(id,grant_id,owner,actor,producer,recipient,kind,required,payload,post,notice,state,created) VALUES(?,?,?,?,?,'fictional-Work','work','settled',?,?,?,'posted','fictional-time')",
                          (key,grant,'fictional-Work',self.value['actor'],outbox['producer'],outbox['payload'],post,notice))
        received = {**event, 'id': 'fictional-current-receiving', 'kind': 'response', 'parent': event['id'],
                    'processing_capability': self.runtime.processing.key,
                    'source_delivery': {'id':key,'post':post,'notice':notice,'source_grant':grant,'receiver_grant':grant,'source_hash':digest(json.loads(outbox['payload']))}}
        self.conn.execute('INSERT INTO coordinator_software_deliveries_v1 VALUES(?,?,?,?,?)', (key,grant,grant,received['id'],encode(received)))
        self.assertTrue(self.boards['Work'].receiving_intent(self.runtime, received))
        self.runtime.ingest(received)
        self.assertTrue(self.runtime.processing.event(received))
        with self.assertRaises(Refusal): self.boards['Work'].receiving_intent(self.runtime, {**received,'body':'changed'})
        self.conn.execute("UPDATE coordinator_deliveries_v1 SET transport_started=1 WHERE id=?", (key,))
        with self.assertRaises(Refusal): self.boards['Work'].receiving_intent(self.runtime, received)
        # The selected retention API actually locks and same-inode writes only
        # this owned fixture file. This is not a successful native task/publish.
        target = self.directory/'fictional-canonical'
        target.write_bytes(b'old'); inode = target.stat().st_ino
        with publication.snapshot_lock(self.runtime):
            fd = os.open(target, os.O_RDWR)
            try: publication.write_same_inode(fd, b'current')
            finally: os.close(fd)
        self.assertEqual(target.stat().st_ino, inode); self.assertEqual(target.read_bytes(), b'current')
        self.assertTrue(all(r['profile'] is None for r in self.runtime.rows('SELECT profile FROM attempts')))
        self.assertTrue(all(r['session'] is None and r['turn'] is None for r in self.runtime.rows('SELECT session,turn FROM attempts')))
        self.assertEqual(self.runtime.one('SELECT COUNT(*) AS n FROM outboxes')['n'], 68)
        self.assertEqual(self.runtime.job('fictional-old-job')['effects'], 'unknown')

    def test_selected_config_file_currentness_and_source_fence(self):
        self.transition(); self.issue()
        path = Path(self.value['operator_config'])
        path.write_text(encode({**self.value,'enabled':True}))
        with self.assertRaises(Refusal): self.runtime.processing.current()
        self.assertEqual(self.runtime.one('SELECT COUNT(*) AS n FROM events')['n'], 4)

    def test_current_basis_pins_sources_pool_and_receiving_without_native_claim(self):
        basis = self.selection()['basis']
        self.assertIn('/src/tools/message-board/board_store.py', basis['release']['files'])
        self.assertIn('/src/tools/coordinator-runtime/tests/fixture_snapshot/retention.py', basis['release']['files'])
        self.assertEqual(set(basis['release']['enabled']), {'.codex2','.codex3','.codex5'})
        path = Path(self.original['execution_pool_routes'])
        path.write_text(path.read_text().replace('".codex5"]', '".codex4"]'))
        with self.assertRaises(Refusal): configuration.apply(self.runtime, self.boards, self.value, self.selection())
        self.assertIsNone(configuration.latest(self.runtime))


class Isolation(unittest.TestCase):
    def test_read_only_source_and_positive_owned_write(self):
        source = Path('/src/tools/coordinator-runtime/coordinator_runtime/configuration.py')
        self.assertTrue(os.statvfs(source).f_flag & os.ST_RDONLY)
        with self.assertRaises(OSError) as failed: source.open('ab')
        self.assertEqual(failed.exception.errno, errno.EROFS)
        target = Path('/fixtures/positive-isolated-write')
        target.write_text('isolated308'); self.assertEqual(target.read_text(), 'isolated308')
