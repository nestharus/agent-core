"""Continuing allocation and opaque journal boundaries in private fiction.

All native/provider/profile/session/turn encounters are NULL. Membership and
allocation seams are inherited from configuration308; transaction, selection,
source/currentness, custody and refusal checks execute production code.
"""
import copy
import hashlib
import json
import sqlite3
import unittest
from unittest.mock import patch

from coordinator_runtime import cli, configuration, custody, processing, service, windows
from coordinator_runtime.contracts import Backpressure, Refusal, digest, encode
from coordinator_runtime.store import Store
import test_configuration308 as fixture


class Continuing(unittest.TestCase):
    def setUp(self):
        self.f = fixture.CurrentConfiguration(methodName='runTest')
        self.addCleanup(self.f.doCleanups)
        original = fixture.engine_config
        def config(directory):
            value = original(directory)
            value['limits']['max_artifact_bytes']=65536
            for role,selected in value['roles'].items():
                selected['routes']=[n for n,t in value['tasks'].items() if t['role']==role]+(['wp'] if role!='Work' else [])
            value['window_service'] = {'tasks': list(value['tasks']), 'max_new_inputs': 40,
                                       'batch_size': 8, 'max_decisions': 16}
            return value
        with patch.object(fixture, 'engine_config', side_effect=config):
            self.f.setUp()
        self.s = self.f.runtime
        with self.s.tx():
            used = json.loads(windows.current(self.s)['used'])
            used['events'] = 40
            self.s.db.execute('UPDATE service_windows SET new_inputs=40,used=? WHERE number=1', (encode(used),))
        self.old_window = windows.current(self.s)
        self.old_rows = {name: self.s.rows('SELECT * FROM '+name) for name in ('events','jobs','attempts','outboxes','enrollments')}
        self.grants = [tuple(r) for r in self.f.conn.execute('SELECT * FROM coordinator_grants_v1')]

    def adopt(self):
        self.f.transition()
        self.s = self.f.runtime
        self.assertNotEqual(windows.current(self.s)['configuration'], digest(self.s.config))

    def receipt(self):
        return {'basis': windows.basis(self.s), 'target': 'fictional continuing coordination',
                'reason': 'source adoption and bounded later allocations without native per-batch intervention',
                'evidence': 'fictional Work explicit choice; original duties remain unchanged',
                'custody': {r: {'owner': 'fictional-'+r, 'evidence': 'fictional original collector/hold retained'} for r in self.s.config['roles']}}

    def selection(self, max_windows=3):
        selected = {'basis': processing.basis(self.s,self.f.boards,future_only=True),
                    'authority': 'fictional Work continuing future authority and WHY',
                    'retained_events': [], 'recover_controls': {}, 'future_intake': True,
                    'tasks': list(self.s.config['tasks']), 'max_shared_rows': 512,
                    'max_shared_payload_bytes': 1048576, 'max_runtime_rows': 512}
        selected['service'] = {'max_inflight': 5, 'reviews': {}, 'legacy_resources': {
            r: {'original_hold': self.old_rows['enrollments'][i]['legacy_hold'], 'roots': [], 'unbounded': True,
                'evidence': 'fictional unknown old scope stays held'} for i,r in enumerate(self.s.config['roles'])},
            'allocations': {**self.receipt(), 'basis': selected['basis']['allocation'], 'expires': 90000., 'max_windows': max_windows}}
        return selected

    def issue(self, selected=None):
        key = processing.select(self.s, self.f.boards, selected or self.selection())['capability']
        self.s.processing = processing.Access(self.s, key, self.f.boards)
        return key

    def new_event(self, name, role='Work'):
        return {'id': name, 'role': role, 'recipient': 'fictional-'+role, 'kind':'board', 'post':100,
                'body': 'fictional lawful future input', 'package': None, 'allowed_tasks':['wp']}

    def assert_originals(self):
        self.assertEqual(self.s.one('SELECT * FROM service_windows WHERE number=1'), self.old_window)
        for table, rows in self.old_rows.items():
            keys = [r['role'] if table == 'enrollments' else r['id'] for r in rows]
            field = 'role' if table == 'enrollments' else 'id'
            self.assertEqual([self.s.one('SELECT * FROM '+table+' WHERE '+field+'=?', (key,)) for key in keys], rows)
        self.assertEqual([tuple(r) for r in self.f.conn.execute('SELECT * FROM coordinator_grants_v1')], self.grants)
        self.assertTrue(all(r['processed_at'] is None for r in self.s.rows('SELECT processed_at FROM events')))
        self.assertIsNone(self.s.attempt('fictional-original-attempt')['ended'])
        self.assertIsNone(self.s.attempt('fictional-original-attempt')['session'])
        self.assertIsNone(self.s.attempt('fictional-original-attempt')['profile'])
        self.assertEqual(self.s.job('fictional-old-job')['effects'], 'unknown')
        self.assertEqual(self.s.job('fictional-old-job')['controller'], 'fictional-old-collector')

    def test_adoption_repeated_boundaries_conserve_every_old_charge_and_role(self):
        self.adopt()
        self.assertTrue(cli.parser().parse_args(['processing-basis','--future-only']).future_only)
        key = self.issue()
        self.assertEqual(service.admit_input(self.s), 40)
        for number in range(1, 82):
            role = list(self.s.config['roles'])[(number-1) % 4]
            event = self.new_event('fictional-future-'+str(number), role)
            self.s.ingest(event)
        rows = self.s.rows('SELECT number,configuration,new_inputs,used,actor FROM service_windows ORDER BY number')
        self.assertEqual([r['new_inputs'] for r in rows], [40,40,40,1])
        self.assertEqual([json.loads(r['used'])['events'] for r in rows], [40,40,40,1])
        self.assertEqual({r['configuration'] for r in rows[1:]}, {digest(self.s.config)})
        self.assertEqual({r['actor'] for r in rows}, {'fictional-Work'})
        self.assertEqual({r['role'] for r in self.s.rows("SELECT role FROM events WHERE id LIKE 'fictional-future-%'")}, set(self.s.config['roles']))
        self.assertEqual(self.s.one('SELECT COUNT(*) AS n FROM service_window_allocations WHERE capability=?',(key,))['n'],3)
        self.assert_originals()
        self.assertEqual(self.s.one('SELECT starts FROM processing_capabilities WHERE id=?',(key,))['starts'],0)
        self.assertEqual(self.s.rows('SELECT * FROM service_runs'),[])

    def test_before_blob_acquisition_hash_copy_or_accounting_during_adoption_and_boundary(self):
        # Fictional held origin; never seek the corresponding path or alias.
        body = b'FICTIONAL held full historical WORK_LOG body'
        sha = hashlib.sha256(body).hexdigest()
        self.s.db.execute('INSERT INTO artifact_blobs VALUES(?,?)',(sha,body))
        self.s.db.execute('INSERT INTO artifact_custody VALUES(?,?,?,?,?,?)',
            ('fictional-held','/fixtures/NEVER-PROBE/WORK_LOG.md','historical','fictional-custodian',
             encode({'path':'/fixtures/NEVER-PROBE/WORK_LOG.md','size':len(body),'sha256':sha}),sha))
        self.s.db.execute("INSERT INTO file_publications VALUES('fictional-held','/fixtures/NEVER-PROBE/WORK_LOG.md','intent',?,NULL,NULL,NULL)",(sha,))
        statements = []
        def no_blob(action, table, column, database, source):
            if action == sqlite3.SQLITE_READ and (table == 'artifact_blobs' or table in {'events','outboxes'} and column=='payload'):
                raise AssertionError('BEFORE any blob key/body/length/presence acquisition: '+str(column))
            return sqlite3.SQLITE_OK
        self.s.db.set_authorizer(no_blob)
        self.s.db.set_trace_callback(statements.append)
        try:
            before = windows.basis(self.s)
            self.assertIn('no body read',before['journal_revision']['meaning'])
            configuration.journal(self.s)
            self.adopt()
            self.s.db.set_authorizer(no_blob)
            self.s.db.set_trace_callback(statements.append)
            with patch.object(custody, 'frozen_body', side_effect=AssertionError('no held body acquisition')), \
                 patch.object(custody, 'read_file', side_effect=AssertionError('no held filesystem read')):
                self.issue(); service.admit_input(self.s)
                self.s.ingest(self.new_event('fictional-safe'))
                self.assertGreater(self.s.usage()['publication_reserved_bytes'],0)
        finally:
            self.s.db.set_authorizer(None); self.s.db.set_trace_callback(None)
        self.assertFalse(any('SELECT' in sql.upper() and 'FROM ARTIFACT_BLOBS' in sql.upper() for sql in statements))
        self.assertEqual(self.s.one('SELECT body FROM artifact_blobs WHERE sha256=?',(sha,))['body'],body)
        self.assert_originals()

    def test_missing_allocation_authority_and_finite_capability_do_not_adopt_window(self):
        self.adopt()
        selected = self.selection(); del selected['service']['allocations']
        self.issue(selected)
        with self.assertRaisesRegex(Refusal,'window/configuration'): service.admit_input(self.s)
        self.assertEqual(windows.current(self.s), self.old_window)
        self.assert_originals()

    def test_stale_basis_borrowed_custody_and_invalid_horizons_refuse_selection(self):
        self.adopt()
        selected = self.selection()
        self.s.db.execute("UPDATE events SET hold='fictional changed hold' WHERE id=?",(self.f.originals[0]['id'],))
        selected['basis'] = processing.basis(self.s,self.f.boards,future_only=True)
        with self.assertRaisesRegex(Refusal,'basis changed'): processing.select(self.s,self.f.boards,selected)
        for change in ('custody','expired','infinite','zero','too-many'):
            selected=self.selection()
            a=selected['service']['allocations']
            if change=='custody': a['custody']['QA']['owner']='fictional-Work'
            if change=='expired': a['expires']=1000.
            if change=='infinite': a['expires']=float('inf')
            if change=='zero': a['max_windows']=0
            if change=='too-many': a['max_windows']=10001
            with self.subTest(change=change), self.assertRaises(Refusal): processing.select(self.s,self.f.boards,selected)
        self.assertEqual(self.s.rows('SELECT * FROM service_window_allocations'),[])

    def test_exhaustion_expiry_revocation_and_implementation_currentness_preserve_rows(self):
        self.adopt(); key=self.issue(self.selection(max_windows=1))
        for n in range(40): self.s.ingest(self.new_event('fictional-first-'+str(n)))
        before=self.s.rows('SELECT * FROM service_windows')
        with self.assertRaisesRegex(Backpressure,'exhausted'): self.s.ingest(self.new_event('fictional-no-budget'))
        self.assertEqual(self.s.rows('SELECT * FROM service_windows'),before)
        with patch.object(processing,'implementation',return_value={'fictional':'different'}):
            with self.assertRaisesRegex(Refusal,'source/configuration changed'): service.admit_input(self.s)
        self.s.clock=lambda:90000.
        with self.assertRaisesRegex(Refusal,'expired'): service.admit_input(self.s)
        self.s.clock=lambda:1000.
        processing.revoke(self.s,self.f.boards,key)
        with self.assertRaisesRegex(Refusal,'revoked'): service.admit_input(self.s)
        self.assertEqual(self.s.rows('SELECT * FROM service_windows'),before)
        self.assert_originals()

    def test_nonissuer_and_manual_unrelated_boundary_cannot_borrow_delegation(self):
        self.adopt(); key=self.issue()
        self.s.db.execute("UPDATE processing_capabilities SET issuer='fictional-QA' WHERE id=?",(key,))
        with self.assertRaisesRegex(Refusal,'borrowed'): service.admit_input(self.s)
        self.s.db.execute("UPDATE processing_capabilities SET issuer='fictional-Work' WHERE id=?",(key,))
        with self.s.tx(): windows.append(self.s,'fictional-Work',self.receipt())
        with self.assertRaisesRegex(Refusal,'mixed-original'): service.admit_input(self.s)
        self.assertEqual(self.s.rows('SELECT * FROM service_window_allocations'),[])
        self.assert_originals()

    def test_revision_current_across_reopen_and_detects_body_hold_schema_and_rollback(self):
        self.f.issue()  # Real finite processing selection supplies active role authority.
        before=windows.basis(self.s)
        reopened=Store(self.s.config, clock=lambda:1000.)
        self.addCleanup(reopened.close)
        self.assertEqual(windows.basis(reopened),before)
        with self.assertRaises(RuntimeError):
            with reopened.tx():
                reopened.db.execute("UPDATE events SET hold='fictional rolled back' WHERE id=?",(self.f.originals[0]['id'],))
                raise RuntimeError('fictional rollback')
        self.assertEqual(windows.basis(reopened),before)
        reopened.db.execute("UPDATE events SET hold='fictional current hold' WHERE id=?",(self.f.originals[0]['id'],))
        self.assertNotEqual(windows.basis(self.s),before)
        stale=self.receipt()
        reopened.db.execute("INSERT INTO artifact_blobs VALUES('fictional-key',X'00')")
        with self.assertRaisesRegex(Refusal,'basis changed'): windows.advance(self.s,'fictional-Work',stale)
        before=windows.basis(self.s)
        reopened.db.execute("UPDATE artifact_blobs SET body=X'01' WHERE sha256='fictional-key'")
        self.assertNotEqual(windows.basis(self.s),before)
        self.s.db.execute('CREATE TABLE fictional_new_table(body BLOB)')
        with self.assertRaisesRegex(Refusal,'coverage changed'): windows.basis(self.s)
        windows.prepare_revision(self.s)
        self.assertNotEqual(windows.basis(self.s),before)
        trigger=next(windows.revision_triggers(windows.revision_schema(self.s)))[0]
        self.s.db.execute('DROP TRIGGER "'+trigger+'"')
        with self.assertRaisesRegex(Refusal,'coverage changed'): windows.basis(self.s)

    def test_ordinary_manual_window_and_preacquisition_scan_bounds(self):
        # Genuine old API stays manual and owner-attributed, without processing.
        self.assertIsNone(self.s.processing)
        with self.assertRaises(Backpressure): windows.preflight_input(self.s)
        with self.assertRaises(Refusal): windows.advance(self.s,'fictional-QA',self.receipt())
        with self.assertRaisesRegex(Refusal,'active runtime enrollment'):
            windows.advance(self.s,'fictional-Work',self.receipt())
        self.adopt(); self.issue()
        # Exercise actual Board scan ordering. Never permit _event/body handling
        # without a bounded current allocation and the original grant checks.
        captured=[]
        original=processing.ProcessingBoard.__mro__[1].scan
        def scan(board,runtime,limit=100):
            captured.append(limit)
            self.assertEqual(windows.current(runtime)['configuration'],digest(runtime.config))
            return original(board,runtime,limit)
        with patch.object(processing.ProcessingBoard.__mro__[1],'scan',scan):
            self.f.boards['Work'].scan(self.s)
        self.assertEqual(captured,[40])
        for n in range(39): self.s.ingest(self.new_event('fictional-scan-'+str(n)))
        with patch.object(processing.ProcessingBoard.__mro__[1],'scan',scan):
            self.f.boards['Work'].scan(self.s)
        self.assertEqual(captured,[40,1])
        self.assert_originals()

    def test_future_only_cannot_recover_history_or_expand_finite_authority(self):
        self.adopt()
        for mode in ('retained','recover','owner','finite'):
            selected=self.selection()
            if mode=='retained': selected['retained_events']=[self.f.originals[0]['id']]
            if mode=='recover': selected['recover_controls']={self.f.originals[0]['id']:'fictional-original-attempt'}
            if mode=='owner': selected['owner_operations']=[{'kind':'legacy-disposition'}]
            if mode=='finite':
                del selected['service'];selected.update(expires=1060.,max_starts=1)
            with self.subTest(mode=mode), self.assertRaisesRegex(Refusal,'metadata-only'):
                processing.select(self.s,self.f.boards,selected)
        self.assert_originals()

    def test_decision_and_internal_allocation_boundaries_conserve_exact_charges(self):
        self.adopt();self.issue(self.selection(max_windows=6))
        # Each kind has its existing independent bound; increment via the actual
        # source write transaction, including repeated decision boundaries.
        expected={k:0 for k in windows.KINDS}
        for kind in windows.KINDS:
            limit=self.s.config['window_service']['max_decisions'] if kind=='decisions' else self.s.config['limits'].get('max_'+kind,self.s.config['limits']['max_events'])
            with self.s.tx():
                windows.charge(self.s,kind)
                row=windows.current(self.s)
                used=json.loads(row['used'])
                # A preexisting fully charged boundary is fictional setup,
                # independent of how the production rollover is implemented.
                used[kind]=limit
                self.s.db.execute('UPDATE service_windows SET used=? WHERE number=?',(encode(used),row['number']))
            before=self.s.one('SELECT * FROM service_windows WHERE number=?',(row['number'],))
            with self.s.tx(): windows.charge(self.s,kind)
            self.assertEqual(self.s.one('SELECT * FROM service_windows WHERE number=?',(row['number'],)),before)
            self.assertEqual(json.loads(windows.current(self.s)['used'])[kind],1)
        self.assertEqual(self.s.one('SELECT COUNT(*) AS n FROM service_window_allocations')['n'],6)
        self.assert_originals()

    def test_window_append_rolls_back_when_storage_fails_and_cross_config_refuses(self):
        self.adopt();self.issue()
        original=self.s.config
        changed=copy.deepcopy(original);changed['window_service']['max_new_inputs']=17
        with patch.object(self.s,'config',changed):
            with self.assertRaisesRegex(Refusal,'historical|source/configuration'):
                service.admit_input(self.s)
        before=self.s.rows('SELECT * FROM service_windows')
        with patch.object(self.s,'budget',side_effect=Backpressure('fictional owned storage full')):
            with self.assertRaisesRegex(Backpressure,'storage full'): service.admit_input(self.s)
        self.assertEqual(self.s.rows('SELECT * FROM service_windows'),before)
        self.assertEqual(self.s.rows('SELECT * FROM service_window_allocations'),[])
        self.assert_originals()
