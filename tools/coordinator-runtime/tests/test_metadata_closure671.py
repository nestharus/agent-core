"""Metadata-only execution closure on newly authored synthetic journals only.

Full Store, CLI, stopped original grant and transaction code run. Controller
closure statements are fictional external testimony, never a process census.
No actual held journal, provider, account or capture is selected.
"""
from contextlib import contextmanager, ExitStack
import copy
import os
from pathlib import Path
import sqlite3
import unittest
from unittest.mock import patch

import test_management406 as fixture
from coordinator_runtime import cli, integration_management as management, selected_source
from coordinator_runtime.contracts import Refusal, encode
from coordinator_runtime.integration import METADATA_CLOSURE


class MetadataClosure671(unittest.TestCase):
    def setUp(self):
        self.f = fixture.Management(methodName='runTest')
        self.addCleanup(self.f.doCleanups)
        self.f.setUp()
        self.store, self.owner = self.f.store, self.f.owner
        self.job, self.token = 'synthetic-held', 'synthetic-token'
        self.authority = management.basis(self.store, ['Work'], self.owner,
            'Synthetic genuine Work management', 'Synthetic metadata closure only', metadata_only=True)

    def call(self, command, *, receipt=None, selection=None, ordinary=False, actor=None):
        args = [command, self.job, '--token', self.token]
        if not ordinary:
            choice = copy.deepcopy(selection if selection is not None else self.selection(command))
            path = self.f.home/'metadata-selection.json'; path.write_text(encode(choice))
            args += ['--management', str(path)]
        if receipt is not None:
            path = self.f.home/'metadata-receipt.json'; path.write_text(encode(receipt))
            args += ['--receipt', str(path)]
        with patch.dict(os.environ, {'CODEX_SESSION_ID': actor or self.owner}):
            return cli.operate(cli.parser().parse_args(args), self.store)

    def selection(self, command):
        selected = self.f.selection(command, basis=self.authority)
        return copy.deepcopy(selected)

    def basis(self):
        return self.call('integration-metadata-closure-basis')

    def receipt(self, basis=None):
        basis = basis if basis is not None else self.basis()
        return {'basis': basis, 'reason': 'Synthetic ended execution; every retained duty stays owned',
            'controllers': [{'controller': c, 'collector': 'synthetic-owning-original-collector',
                'end': 7, 'collected': True, 'writers_closed': True,
                'evidence': ['Synthetic actual collector testimony includes descendant and launch-capable writer closure']}
                for c in basis['controllers']]}

    def retire(self, receipt=None):
        return self.call('retire-integration-metadata', receipt=receipt if receipt is not None else self.receipt())

    @contextmanager
    def metadata_only(self):
        denied = []
        forbidden = {'results': None, 'artifact_custody': None, 'artifact_blobs': None,
            'outboxes': None, 'file_publications': None, 'local_jobs': None,
            'attempts': {'result','detail','error','capture','semantic','cleanup','binding','profile','session','turn'},
            'jobs': {'effect_receipt','response','hold_reason','collection_handoff'},
            'events': {'payload','hash','classification','classifier','error','hold','ack_receipt'},
            'enrollments': {'legacy_hold','reconciliation'},
            'recovery_requests': {'receipt','result'}, 'recovery_dispositions': {'reason'}}
        def authorize(action, table, column, db, caller):
            if action == sqlite3.SQLITE_READ and table in forbidden and (
                    forbidden[table] is None or column in forbidden[table]):
                denied.append((table, column)); return sqlite3.SQLITE_DENY
            return sqlite3.SQLITE_OK
        with ExitStack() as stack:
            for method in ('job','attempt','event','source_roles','integration_debt','usage','budget'):
                stack.enter_context(patch.object(self.store, method, side_effect=AssertionError('historical acquisition: '+method)))
            self.store.db.set_authorizer(authorize)
            try:
                yield denied
            finally:
                self.store.db.set_authorizer(None)
        self.assertEqual(denied, [])

    @contextmanager
    def mutated(self, sql):
        originals = {t:self.store.rows('SELECT * FROM '+t) for t in ('jobs','attempts','events')}
        self.store.db.execute(sql)
        try:
            yield
        finally:
            for table, rows in originals.items():
                for row in rows:
                    fields = [k for k in row if k != 'id']
                    self.store.db.execute('UPDATE '+table+' SET '+','.join(k+'=?' for k in fields)+' WHERE id=?',
                        (*[row[k] for k in fields], row['id']))

    def conserved(self):
        return {k:v for k,v in self.f.conserved().items()
                if k not in {'integration_retirements','integration_management_operations'}}

    def test_safe_basis_and_fence_never_acquire_forbidden_columns_or_traverse_captures(self):
        sentinel = 'UNACQUIRED_671_OLD_BODY_AND_HASH'
        self.store.db.execute('UPDATE jobs SET effect_receipt=?,response=?,hold_reason=?,collection_handoff=?', (sentinel,)*4)
        self.store.db.execute('UPDATE attempts SET detail=?,error=?,result=?,capture=?,semantic=?,cleanup=?', (sentinel,)*6)
        self.store.db.execute('UPDATE events SET payload=?,hash=?,error=?', (sentinel,)*3)
        self.store.db.execute('UPDATE results SET result=?,error=?', (sentinel,)*2)
        self.store.db.execute('INSERT INTO ordinary_resources VALUES(?,?)', ('synthetic-native-or-ordinary-lease', 'synthetic-attempt'))
        before = self.conserved()
        leases = self.store.rows('SELECT * FROM ordinary_resources')
        with self.metadata_only():
            basis = self.basis()
            self.assertEqual(basis['schema'], METADATA_CLOSURE)
            self.assertNotIn(sentinel, encode(basis))
            self.assertEqual(basis['job']['effects'], 'unknown')
            fence = self.retire(self.receipt(basis))
        self.assertEqual(before, self.conserved())
        self.assertEqual(leases, self.store.rows('SELECT * FROM ordinary_resources'))
        self.assertEqual(fence['job'], self.job)
        self.assertEqual(self.store.job(self.job)['effects'], 'unknown')
        self.assertTrue(self.store.execution_complete(self.store.job(self.job)))
        self.assertRaises(Refusal, self.store.require_execution_open, self.job)
        self.assertRaises(Refusal, self.store.start_job, self.job, self.token)
        self.assertRaises(Refusal, self.store.request_recovery, self.job, self.token,
                          'synthetic-attempt', self.owner, {})
        self.assertEqual(len(self.store.rows('SELECT job FROM integration_retirements')), 1)
        self.assertEqual(len(self.store.rows('SELECT id FROM integration_management_operations')), 1)
        with self.assertRaisesRegex(Refusal, 'execution retired'):
            self.retire(self.receipt(basis))

    def test_every_related_original_and_recovery_controller_required(self):
        self.f.insert('attempts', {'id':'synthetic-diagnosis671','kind':'diagnosis','job':self.job,
            'controller':'synthetic-diagnosis-controller671','profile':'fiction','binding':'{}',
            'state':'collected','created':1,'begin':2,'ended':3,'collected':4,'exit':19})
        self.store.db.execute("UPDATE jobs SET recovery_owner='synthetic-recovery-owner671',"
            "recovery_state='awaiting-disposition',recovery_count=1 WHERE id=?", (self.job,))
        with self.metadata_only():
            receipt = self.receipt()
            self.assertEqual(set(receipt['basis']['controllers']), {'synthetic-original-controller',
                'synthetic-diagnosis-controller671','synthetic-recovery-owner671'})
            for controller in receipt['basis']['controllers']:
                bad = copy.deepcopy(receipt)
                bad['controllers'] = [c for c in bad['controllers'] if c['controller'] != controller]
                with self.subTest(omitted=controller), self.assertRaises(Refusal):
                    self.retire(bad)
            self.retire(receipt)

    def test_unbegun_unended_uncollected_non_numeric_and_wrong_active_relationship_refuse(self):
        mutations = ["UPDATE attempts SET begin=NULL", "UPDATE attempts SET ended=NULL",
            "UPDATE attempts SET collected=NULL", "UPDATE attempts SET exit=NULL",
            "UPDATE attempts SET exit='unknown'", "UPDATE attempts SET exit=0.5",
            "UPDATE attempts SET begin='unknown'", "UPDATE attempts SET ended=-1",
            "UPDATE attempts SET collected=2", "UPDATE attempts SET state='ended'",
            "UPDATE attempts SET kind='diagnosis'", "UPDATE attempts SET controller='foreign-controller'",
            "UPDATE attempts SET job='foreign-job'", "UPDATE jobs SET active_attempt='absent'",
            "UPDATE jobs SET phase='proposer'", "UPDATE jobs SET task='branch-integrator'"]
        for sql in mutations:
            with self.subTest(sql=sql):
                with self.mutated(sql), self.metadata_only(), self.assertRaises(Refusal):
                    self.basis()
        self.assertEqual(self.store.rows('SELECT job FROM integration_retirements'), [])

    def test_pending_recovery_and_active_or_inconsistent_recovery_are_not_closure(self):
        for state, owner, count in [('claimed','synthetic-r',1), ('diagnosing','synthetic-r',1),
                ('diagnosing',None,0), ('awaiting-disposition',None,1), (None,'synthetic-r',1),
                ('future-unknown','synthetic-r',1), (None,None,1)]:
            with self.subTest(state=state,owner=owner,count=count):
                row = self.store.job(self.job)
                self.store.db.execute('UPDATE jobs SET recovery_state=?,recovery_owner=?,recovery_count=?', (state,owner,count))
                try:
                    with self.metadata_only(), self.assertRaises(Refusal): self.basis()
                finally:
                    self.store.db.execute('UPDATE jobs SET recovery_state=?,recovery_owner=?,recovery_count=?',
                        (row['recovery_state'],row['recovery_owner'],row['recovery_count']))
        self.f.insert('recovery_requests', {'id':'synthetic-pending671','job':self.job,
            'attempt':'synthetic-attempt','actor':self.owner,'receipt':'UNREAD','state':'pending','created':1})
        with self.metadata_only(), self.assertRaisesRegex(Refusal, 'pending owner recovery'): self.basis()
        self.store.db.execute("UPDATE recovery_requests SET state='consumed'")
        with self.metadata_only(): self.retire()

    def test_revision_invalidates_even_opaque_body_change_and_reverted_metadata(self):
        mutations = ["UPDATE attempts SET detail='UNREAD late detail'", "UPDATE results SET result='UNREAD late return'",
            "UPDATE jobs SET response='UNREAD late response'", "UPDATE events SET payload='UNREAD late source'",
            "UPDATE attempts SET ended=ended+1", "UPDATE jobs SET controller='different'",
            "UPDATE events SET role='Branch'"]
        for sql in mutations:
            with self.subTest(sql=sql):
                receipt = self.receipt()
                with self.mutated(sql), self.metadata_only(), self.assertRaises(Refusal): self.retire(receipt)
        receipt = self.receipt()
        self.store.db.execute('UPDATE attempts SET ended=ended+1')
        self.store.db.execute('UPDATE attempts SET ended=ended-1')
        with self.metadata_only(), self.assertRaisesRegex(Refusal, 'basis changed'): self.retire(receipt)

    def test_same_transaction_final_recheck_rolls_back_mutation_and_fence(self):
        receipt = self.receipt()
        before = self.conserved()
        original = selected_source.custody_budget
        def mutate(runtime, incoming):
            self.assertTrue(runtime.db.in_transaction)
            original(runtime, incoming)
            runtime.db.execute("UPDATE attempts SET detail='UNREAD same-transaction mutation'")
        with self.metadata_only(), patch.object(selected_source, 'custody_budget', side_effect=mutate):
            with self.assertRaisesRegex(Refusal, 'revision changed'): self.retire(receipt)
        self.assertEqual(before, self.conserved())
        self.assertEqual(self.store.rows('SELECT job FROM integration_retirements'), [])

    def test_source_roles_record_scope_owner_token_and_operation_are_exact(self):
        command = 'integration-metadata-closure-basis'
        for change in [lambda s:s['target'].update(token='wrong'), lambda s:s['records'].update(jobs=[]),
                lambda s:s['records'].update(events=[]), lambda s:s.update(operation='retire-integration-metadata'),
                lambda s:s['basis'].pop('schema'), lambda s:s['basis'].update(schema='legacy'),
                lambda s:s.update(expires=1000.), lambda s:s['basis'].update(configuration='stale')]:
            choice = self.selection(command); change(choice)
            with self.subTest(change=change), self.metadata_only(), self.assertRaises(Refusal):
                self.call(command, selection=choice)
        with self.metadata_only(), self.assertRaises(Refusal): self.call(command, actor=self.configured_branch_owner())
        self.store.db.execute("UPDATE events SET role='Branch' WHERE id=?", (self.f.source['id'],))
        with self.metadata_only(), self.assertRaisesRegex(Refusal, 'source roles'): self.basis()
        self.authority = management.basis(self.store, ['Work','Branch'], self.owner, 'Synthetic owner', 'Exact sources', metadata_only=True)
        with self.metadata_only(): self.assertEqual({s['role'] for s in self.basis()['sources']}, {'Branch'})
        self.store.db.execute("UPDATE queue SET job='wrong' WHERE id='synthetic-old-queue'")
        with self.metadata_only(), self.assertRaisesRegex(Refusal, 'relationships'): self.basis()

    def configured_branch_owner(self):
        return self.f.config['roles']['Branch']['owner']

    def test_actual_collector_numeric_end_and_writer_receipt_cannot_be_replaced_by_ack(self):
        receipt = self.receipt()
        for change in [lambda r:r['controllers'][0].update(end=None), lambda r:r['controllers'][0].update(end=True),
                lambda r:r['controllers'][0].update(end='0'), lambda r:r['controllers'][0].update(collected=False),
                lambda r:r['controllers'][0].update(writers_closed=False), lambda r:r['controllers'][0].update(collector=''),
                lambda r:r['controllers'][0].update(evidence=[]), lambda r:r['controllers'][0].update(controller='foreign'),
                lambda r:r['controllers'][0].update(controller=None), lambda r:r['controllers'][0].update(controller={}),
                lambda r:r.update(reason=''), lambda r:r.update(ack=True)]:
            bad = copy.deepcopy(receipt); change(bad)
            with self.subTest(change=change), self.metadata_only(), self.assertRaises(Refusal): self.retire(bad)

    def test_management_cannot_borrow_legacy_basis_and_legacy_contract_remains(self):
        old = self.f.normal_basis
        self.assertIn('results', old); self.assertNotIn('schema', old)
        with self.assertRaises(Refusal): self.retire(self.receipt(old))
        # Same original fixture's unmodified legacy public contract still works.
        self.assertEqual(self.f.managed('integration-closure-basis'), old)
        self.f.managed('retire-integration', receipt=self.f.closure())
        self.assertTrue(self.store.execution_complete(self.store.job(self.job)))
        self.assertEqual(self.store.job(self.job)['effects'], 'unknown')

    def test_paused_ordinary_access_and_processing_substitution_refuse(self):
        with self.metadata_only(), self.assertRaises(Refusal):
            self.call('integration-metadata-closure-basis', ordinary=True)
        with patch.object(self.store, 'processing', object()), self.assertRaisesRegex(Refusal, 'processing'):
            self.store.integration_metadata_closure_basis(self.job, self.token, self.owner)

    def test_ordinary_current_owner_cli_path_uses_metadata_only_grant_checks(self):
        # Synthetic positive control models the original still-active grant.
        # No actual grant is changed and stopped management is no longer used.
        import sqlite3
        for board in self.f.boards.values():
            with sqlite3.connect(board.path) as conn:
                conn.execute('UPDATE coordinator_grants_v1 SET revoked=NULL')
        self.store.db.execute('UPDATE enrollments SET intake=1')
        with self.metadata_only():
            basis = self.call('integration-metadata-closure-basis', ordinary=True)
            self.call('retire-integration-metadata', ordinary=True, receipt=self.receipt(basis))
        self.assertEqual(self.store.job(self.job)['effects'], 'unknown')

    def test_metadata_capacity_refusal_does_not_walk_or_append(self):
        receipt = self.receipt()
        with self.metadata_only(), patch.object(selected_source, 'custody_budget', side_effect=Refusal('metadata capacity full')):
            with self.assertRaisesRegex(Refusal, 'capacity full'): self.retire(receipt)
        self.assertEqual(self.store.rows('SELECT job FROM integration_retirements'), [])

    def test_bad_token_refuses_before_frozen_source_relationship_acquisition(self):
        self.token = 'synthetic-wrong-token'
        with self.metadata_only(), patch.object(self.store, 'integration_metadata_sources',
                side_effect=AssertionError('source relationships acquired before token check')):
            with self.assertRaises(Refusal): self.basis()

    def test_handed_off_recovery_requires_exact_current_controller(self):
        self.store.db.execute("UPDATE jobs SET recovery_owner='foreign-handoff-controller',"
            "recovery_state='handed-off',recovery_count=1")
        with self.metadata_only(), self.assertRaisesRegex(Refusal, 'recovery/controller'):
            self.basis()
        self.store.db.execute("UPDATE jobs SET recovery_owner=controller")
        with self.metadata_only(): self.retire()

    def test_metadata_management_preserves_original_grant_checks(self):
        board = self.f.boards['Work']
        changes = [('coordinator_grants_v1','runtime_ino','runtime_ino+1'),
                   ('coordinator_grants_v1','revoked','NULL'),
                   ('coordinator_software_grants_v1','configuration',"'synthetic-stale'"),
                   ('sessions','status',"'paused'")]
        for table, field, expression in changes:
            with self.subTest(field=field), sqlite3.connect(board.path) as conn:
                originals = conn.execute('SELECT rowid,'+field+' FROM '+table).fetchall()
                conn.execute('UPDATE '+table+' SET '+field+'='+expression); conn.commit()
                try:
                    with self.metadata_only(), self.assertRaises(Refusal): self.basis()
                finally:
                    conn.executemany('UPDATE '+table+' SET '+field+'=? WHERE rowid=?',
                                     [(value,rowid) for rowid,value in originals]); conn.commit()


if __name__ == '__main__': unittest.main(verbosity=2)
