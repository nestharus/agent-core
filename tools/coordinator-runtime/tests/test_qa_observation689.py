"""Retained, fresh fiction: genuine public Board/admission/correction/QA APIs.

Only SDK caller identity, process END metadata and collected model answers are
fictional seams. No provider, live state, foreign collector or native session.
QA629_FIXTURES must name a new owned directory; no fixture is deleted.
"""
import copy
import fcntl
import json
import os
import sqlite3
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from test_qa629_repairs import Fixture, actor
import test_qa_branch672 as sequence
import test_software_routes643 as routes
from support import collect, result
from coordinator_runtime import cli, ordinary, processing, prospective, resource_scopes as resources
from coordinator_runtime.contracts import Refusal, digest, encode, ident


class Observation689(Fixture, unittest.IsolatedAsyncioTestCase):
    package_count = 1
    source = routes.SoftwareRoutes643.source
    prepared = routes.SoftwareRoutes643.prepared
    package = sequence.Sequence672.package
    select_software = sequence.Sequence672.select_software
    admitted = sequence.Sequence672.admitted
    accepted = sequence.Sequence672.accepted
    qa = sequence.Sequence672.qa
    branch_account = sequence.Sequence672.branch_account
    branch = sequence.Sequence672.branch

    def configure(self):
        sequence.Sequence672.configure(self)
        # The original Work account wrongly calls the operation's own target a
        # held legacy root. The positive-root guard must continue to block it.
        for account in self.operations:
            account['policy']['relevant_roots'] = list(account['policy']['scope']['write_roots'])

    async def asyncSetUp(self):
        await sequence.Sequence672.asyncSetUp(self)
        self.message = self.admitted()
        self.queue = self.store.one('SELECT * FROM queue WHERE event=?', (self.message['id'],))
        self.record_policy = self.selection['service']['legacy_resources']['QA']
        self.old = copy.deepcopy(self.record_policy)
        self.assertTrue(resources.blocked(self.store, self.queue))
        self.assertIsNone(self.store.reserve())
        # Fictional original service lifecycle evidence, not a real collector
        # or claim that a process/file/PID proves END. The release API is real.
        self.store.db.execute('INSERT INTO processing_runs VALUES(?,?,?,?)',
            (self.store.controller, self.cap, 'owned', self.now))
        self.store.db.execute('INSERT INTO service_runs VALUES(?,?,?,?,?,?,?)',
            (self.store.controller, self.cap, '/fiction/no-socket', 'returned-awaiting-parent-END', self.now, self.now, None))
        with self.work():
            processing.release(self.store, self.boards, self.cap, self.store.controller,
                dict(actual_END=0, evidence=['Synthetic SAME original parent collected numeric END']))

    @contextmanager
    def work(self):
        with patch.dict(os.environ, CODEX_SESSION_ID=self.issuer), actor(self.boards['Work'].store, self.issuer):
            yield

    def basis(self):
        with self.work():
            return resources.qa_observation_basis(self.store, self.store.controller, self.message['id'])

    def request(self, roots=None):
        statement = dict(fixture_only=True, attribution='new explicit fictional Work observation',
            fact='New target is delegated; no positive old relevant overlap in this isolated fixture',
            unknown='Old whole account and logical QA custody UNKNOWN retained; no physical census')
        return dict(basis=self.basis(), authority='Current fictional Work corrects its own mistaken target-as-hold attribution',
            evidence=['Actual fictional package scope and retained old unknown independently reviewed'],
            statement=statement, statement_sha256=digest(statement), relevant_roots=roots or [])

    def apply(self, request):
        with self.work():
            return resources.amend_qa_observation(self.store, request)

    def unchanged(self):
        self.assertEqual(json.loads(self.store.one('SELECT selection FROM processing_capabilities WHERE id=?', (self.cap,))['selection']), self.selection)
        self.assertEqual(self.record_policy, self.old)
        self.assertEqual(self.store.enrollment('QA')['legacy_hold'], 'QA global UNKNOWN')

    async def test_correction_real_reservation_and_full_accepted_cleanup_share_account(self):
        request = self.request()
        epoch = self.store.one('SELECT * FROM prospective_authorities WHERE id=?', (self.epoch['id'],))
        receipt = self.apply(request)
        self.assertFalse(receipt['native_qa_authorship'])
        self.assertFalse(receipt['admission_or_effect_authority_changed'])
        self.assertFalse(resources.blocked(self.store, self.queue))
        account = resources.qa_accounts(self.record_policy, self.store)[0]
        self.assertEqual(resources.qa_observation(self.store, 'QA', self.record_policy, account), request['statement'])
        self.assertEqual(resources.qa_operation(self.store, self.queue, self.record_policy), [])
        self.unchanged()
        self.assertEqual(epoch, self.store.one('SELECT * FROM prospective_authorities WHERE id=?', (self.epoch['id'],)))
        self.assertEqual(self.apply(request), receipt)
        # The stopped collector is not adopted: this fixture owns a new normal
        # reservation and its own actual QA/Branch tool subprocess ENDs.
        _, _, _ = await self.qa()
        _, _, response = await self.branch()
        queued = self.store.one('SELECT * FROM queue WHERE event=?', (response,))
        self.assertEqual(queued['task'], 'qa-cleanup')
        self.assertEqual(resources.qa_cleanup(self.store, queued, self.record_policy, self.old['qa_operations'][0]), [])
        self.assertFalse(resources.blocked(self.store, queued))
        cleanup = self.store.reserve()
        self.assertEqual(cleanup['task'], 'qa-cleanup')
        from coordinator_runtime import report_scope
        answer = result(category='qualification')
        answer['findings'].append(dict(collected_reports=report_scope.conserved_inputs(self.store, cleanup)))
        cleanup, _ = self.prepared(cleanup, answer)
        await ordinary.qualification(self.store, cleanup)
        self.store.finish_job(cleanup['id'], cleanup['token'])
        self.unchanged()
        self.assertEqual(self.store.rows('SELECT * FROM ordinary_resources'), [])
        before = '\n'.join(self.store.db.iterdump())
        self.assertEqual(self.apply(request), receipt)
        self.assertEqual(before, '\n'.join(self.store.db.iterdump()))
        (self.area/'api-receipt.json').write_text(encode(receipt)+'\n')

    async def test_remaining_positive_roots_still_block_without_inventing_empty_census(self):
        request = self.request(self.operations[0]['policy']['scope']['write_roots'])
        self.apply(request)
        self.assertTrue(resources.blocked(self.store, self.queue))
        self.assertEqual(resources.qa_operation(self.store, self.queue, self.record_policy), request['relevant_roots'])
        self.assertIsNone(self.store.reserve())
        self.unchanged()

    async def test_wrong_actual_actor_missing_session_and_denied_grant_refuse(self):
        request = self.request()
        for value in [None, ident(), 'invalid']:
            with self.subTest(actor=value), patch.dict(os.environ):
                if value is None:
                    os.environ.pop('CODEX_SESSION_ID', None)
                else:
                    os.environ['CODEX_SESSION_ID'] = value
                with self.assertRaises(Refusal):
                    resources.amend_qa_observation(self.store, request)
        grant = self.store.enrollment('QA')['grant_id']
        self.store.db.execute("UPDATE enrollments SET grant_id='wrong' WHERE role='QA'")
        with self.assertRaises(Refusal):
            self.apply(request)
        self.store.db.execute("UPDATE enrollments SET grant_id=? WHERE role='QA'", (grant,))
        self.assertEqual(self.store.rows('SELECT * FROM qa_observation_amendments'), [])

    async def test_cap_account_config_source_and_mapping_basis_tampering_refuse(self):
        original = self.request()
        for field in ['capability', 'issuer', 'configuration', 'selection_sha256', 'original_record_sha256',
                      'original_account_sha256', 'source_sha256', 'admission_sha256', 'original_hold', 'custodian']:
            request = copy.deepcopy(original)
            request['basis'][field] = 'forged'
            with self.subTest(field=field), self.assertRaises(Refusal):
                self.apply(request)
        self.git('update-ref', 'refs/heads/source', self.info['old'], self.info['head'])
        with self.assertRaises(Refusal):
            self.apply(original)
        self.assertEqual(self.store.rows('SELECT * FROM qa_observation_amendments'), [])

    async def test_unstarted_source_hash_and_held_source_are_independent(self):
        request = self.request()
        original = self.store.one('SELECT hash FROM events WHERE id=?', (self.message['id'],))['hash']
        for update, value in [('hash', 'forged'), ('hold', 'original source UNKNOWN')]:
            self.store.db.execute('UPDATE events SET '+update+'=? WHERE id=?', (value, self.message['id']))
            with self.assertRaises(Refusal):
                self.apply(request)
            self.store.db.execute('UPDATE events SET '+update+'=? WHERE id=?',
                (original if update == 'hash' else None, self.message['id']))
        self.assertTrue(resources.blocked(self.store, self.queue))

    async def test_expired_revoked_prospective_and_policy_expiry_refuse(self):
        request = self.request()
        epoch = self.store.one('SELECT selection FROM prospective_authorities WHERE id=?', (self.epoch['id'],))['selection']
        self.store.db.execute('UPDATE prospective_authorities SET revoked=1 WHERE id=?', (self.epoch['id'],))
        with self.assertRaises(Refusal):
            self.apply(request)
        self.store.db.execute('UPDATE prospective_authorities SET revoked=NULL WHERE id=?', (self.epoch['id'],))
        policy = json.loads(epoch)
        policy['expires'] = 0
        self.store.db.execute('UPDATE prospective_authorities SET selection=? WHERE id=?', (encode(policy), self.epoch['id']))
        with self.assertRaises(Refusal):
            self.apply(request)
        self.store.db.execute('UPDATE prospective_authorities SET selection=? WHERE id=?', (epoch, self.epoch['id']))
        with patch.object(self.store, 'clock', return_value=self.now+601), self.assertRaises(Refusal):
            self.apply(request)

    async def test_live_lock_and_unreleased_or_uncollected_original_refuse(self):
        request = self.request()
        with (self.store.home/'service.lock').open('r+') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaises(Refusal):
                self.apply(request)
        original = self.store.one('SELECT state FROM processing_runs WHERE controller=?', (self.store.controller,))['state']
        self.store.db.execute("UPDATE processing_runs SET state='owned' WHERE controller=?", (self.store.controller,))
        with self.assertRaises(Refusal):
            self.apply(request)
        self.store.db.execute('UPDATE processing_runs SET state=? WHERE controller=?', (original, self.store.controller))
        attempt = self.store.one('SELECT id,collected FROM attempts LIMIT 1')
        self.store.db.execute('UPDATE attempts SET collected=NULL WHERE id=?', (attempt['id'],))
        with self.assertRaises(Refusal):
            self.apply(request)
        self.assertEqual(self.store.rows('SELECT * FROM qa_observation_amendments'), [])

    async def test_reserved_job_and_old_package_owner_cannot_be_rebound(self):
        request = self.request()
        self.store.db.execute("INSERT INTO jobs(id,role,phase,task,package,members,controller,token,created) VALUES(?,?,?,?,?,?,?,?,?)",
            ('fiction-reserved', 'QA', 'execution', 'qa-execution', self.key, '[]', self.store.controller, 'token', self.now))
        with self.assertRaises(Refusal):
            self.apply(request)
        self.assertTrue(resources.blocked(self.store, self.queue))
        self.assertEqual(self.store.job('fiction-reserved')['state'], 'reserved')
        self.store.db.execute("UPDATE jobs SET state='running',active_attempt='fiction-started' WHERE id='fiction-reserved'")
        self.store.db.execute('INSERT INTO attempts(id,kind,job,controller,profile,binding,created,begin) VALUES(?,?,?,?,?,?,?,?)',
            ('fiction-started', 'task', 'fiction-reserved', self.store.controller,
             self.config['roles']['QA']['profile'], encode(self.config['tasks']['qa-execution']['binding']), self.now, self.now))
        target = str(Path(self.operations[0]['policy']['scope']['write_roots'][0])/'partial-output')
        self.store.db.execute('INSERT INTO file_publications VALUES(?,?,?,?,?,?,?)',
            ('fiction-started', target, 'intent', '0'*64, None, None, None))
        with self.assertRaises(Refusal):
            self.apply(request)
        self.assertEqual(self.store.one("SELECT state FROM file_publications WHERE attempt='fiction-started'")['state'], 'intent')

    async def test_orphan_ordinary_intent_and_lease_remain_held(self):
        request = self.request()
        admission = self.store.one('SELECT receipt FROM admissions WHERE package=?', (self.key,))
        self.store.db.execute('INSERT INTO ordinary_runs VALUES(?,?,?,?,?,?,?)',
            ('fiction-intent', 'fiction-old-job', self.epoch['id'], digest(admission['receipt']), '{}', 'intent', None))
        with self.assertRaises(Refusal):
            self.apply(request)
        self.assertEqual(self.store.one('SELECT state FROM ordinary_runs')['state'], 'intent')

    async def test_unmapped_current_lease_remains_unknown(self):
        request = self.request()
        self.store.db.execute('INSERT INTO ordinary_resources VALUES(?,?)', (self.key, 'original-unknown'))
        with self.assertRaises(Refusal):
            self.apply(request)
        self.assertEqual(self.store.one('SELECT attempt FROM ordinary_resources')['attempt'], 'original-unknown')

    async def test_scope_operation_expiry_custodian_reference_binding_cleanup_changes_refuse(self):
        original = self.request()
        for field in ['scope', 'source', 'inputs', 'reference', 'custodian', 'expires', 'binding', 'cleanup', 'actor']:
            request = copy.deepcopy(original)
            request[field] = 'unsupported'
            with self.subTest(field=field), self.assertRaises(Refusal):
                self.apply(request)
        bad = copy.deepcopy(original)
        bad['statement_sha256'] = '0'*64
        with self.assertRaises(Refusal):
            self.apply(bad)
        bad = copy.deepcopy(original)
        bad['statement'] = self.operations[0]['statement']
        bad['statement_sha256'] = digest(bad['statement'])
        with self.assertRaises(Refusal):
            self.apply(bad)

    async def test_root_acceptance_and_admission_mutation_refuse(self):
        request = self.request()
        self.store.db.execute("UPDATE branch_associations SET state='assigned' WHERE id=?", (self.info['branch'],))
        with self.assertRaises(Refusal):
            self.apply(request)
        self.assertEqual(self.store.rows('SELECT * FROM qa_observation_amendments'), [])

    async def test_changed_current_admission_scope_and_resource_expiry_refuse(self):
        request = self.request()
        admission = self.store.one('SELECT receipt FROM admissions WHERE package=?', (self.key,))
        changed = json.loads(admission['receipt'])
        changed['task_scopes']['qa-execution']['ordinary_effects']['resources'][0]['expires'] += 30
        self.store.db.execute('UPDATE admissions SET receipt=? WHERE package=?', (encode(changed), self.key))
        with self.assertRaises(Refusal):
            self.apply(request)
        self.assertEqual(self.store.rows('SELECT * FROM qa_observation_amendments'), [])
        self.unchanged()

    async def test_false_parent_end_and_unreturned_original_service_refuse(self):
        request = self.request()
        self.store.db.execute('UPDATE processing_runs SET state=? WHERE controller=?',
            (encode({'parent_END': {'actual_END': True, 'evidence': ['not a numeric END']}}), self.store.controller))
        with self.assertRaises(Refusal):
            self.apply(request)
        self.store.db.execute("UPDATE service_runs SET state='owned',returned=NULL WHERE controller=?", (self.store.controller,))
        with self.assertRaises(Refusal):
            self.apply(request)

    async def test_committed_correction_cannot_bypass_later_expiry_or_admission_change(self):
        request = self.request()
        self.apply(request)
        with patch.object(self.store, 'clock', return_value=self.now+601):
            self.assertTrue(resources.blocked(self.store, self.queue))
            with self.assertRaises(Refusal):
                resources.qa_accounts(self.record_policy, self.store)
        admission = self.store.one('SELECT receipt FROM admissions WHERE package=?', (self.key,))
        changed = json.loads(admission['receipt'])
        changed['task_scopes']['qa-execution']['network'] = True
        self.store.db.execute('UPDATE admissions SET receipt=? WHERE package=?', (encode(changed), self.key))
        self.assertTrue(resources.blocked(self.store, self.queue))
        with self.assertRaises(Refusal):
            resources.qa_accounts(self.record_policy, self.store)

    async def test_append_only_storage_different_amendment_and_selected_record_drift_refuse(self):
        request = self.request()
        self.apply(request)
        for sql in ['UPDATE qa_observation_amendments SET issuer=issuer', 'DELETE FROM qa_observation_amendments']:
            with self.assertRaises(sqlite3.IntegrityError):
                self.store.db.execute(sql)
        different = copy.deepcopy(request)
        different['authority'] += ' another decision'
        with self.assertRaises(Refusal):
            self.apply(different)
        mutated = copy.deepcopy(self.record_policy)
        mutated['qa_operations'][0]['policy']['reference'] = 'another'
        with self.assertRaises(Refusal):
            resources.qa_accounts(mutated, self.store)
        self.unchanged()

    async def test_lexical_exclusion_before_metadata_and_no_capture_accounting(self):
        request = self.request()
        # No old capture accounting or old frozen-policy scan is authorized by
        # metadata admission. The source-operation validator remains real.
        with patch.object(self.store, 'usage', side_effect=AssertionError('old captures must not be inventoried')):
            self.apply(request)
        self.assertFalse(resources.blocked(self.store, self.queue))
        request = copy.deepcopy(request)
        request['relevant_roots'] = ['/home/nes/.codex5']
        with patch.object(Path, 'is_symlink', side_effect=AssertionError('excluded path metadata')):
            with self.assertRaises(Refusal):
                resources._qa_observation(self.store, 'QA', self.record_policy,
                    resources._corrected_account(self.operations[0], request))

    async def test_same_transaction_revision_cas_refuses_unrelated_write(self):
        request = self.request()
        self.store.db.execute("INSERT INTO meta VALUES('fiction-concurrent-change','preserve')")
        with self.assertRaises(Refusal):
            self.apply(request)
        self.assertEqual(self.store.rows('SELECT * FROM qa_observation_amendments'), [])
        self.assertTrue(resources.blocked(self.store, self.queue))

    async def test_cli_commands_bind_capability_without_supplied_actor(self):
        parsed = cli.parser().parse_args(['qa-observation-correction-basis', self.cap,
            self.message['id'], '--controller', self.store.controller])
        with self.work(), patch.object(processing, 'ProcessingBoard', side_effect=lambda config, role: self.boards[role]):
            basis = cli.operate(parsed, self.store)
        self.assertEqual(basis['original_account_sha256'], digest(self.operations[0]))
        request = self.request()
        path = self.area/'fictional-correction.json'
        path.write_text(encode(request))
        parsed = cli.parser().parse_args(['amend-qa-observation', self.cap, '--receipt', str(path)])
        with self.work(), patch.object(processing, 'ProcessingBoard', side_effect=lambda config, role: self.boards[role]):
            self.assertEqual(cli.operate(parsed, self.store)['package'], self.key)
