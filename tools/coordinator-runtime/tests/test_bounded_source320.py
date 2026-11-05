"""Owned software/Git/SQLite fiction; no model/native/live runtime encounters.

Root's c99 decisions and R320 observations supply the behavior oracles. These
tests exercise local acquisition, completion/routing and operation counts only.
"""
import base64
import hashlib
import json
import os
import sqlite3
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from coordinator_runtime import cli, coding, custody, review_reader, reviews
from coordinator_runtime.contracts import Refusal, encode, ident
from support import config_at, enrolled, event, queued, collect, result


class Export(unittest.TestCase):
    def setUp(self):
        self.directory = Path(tempfile.mkdtemp(dir='/fixtures'))
        self.store = enrolled(config_at(self.directory))
        self.addCleanup(self.store.close)
        self.path = str(self.directory / 'public-report.md')
        self.body = b'fictional public report\n'
        self.sha = hashlib.sha256(self.body).hexdigest()
        self.owner = self.store.config['roles']['Reviews']['owner']
        self.consumer = self.store.config['roles']['Work']['owner']
        self.store.db.execute('INSERT INTO artifact_blobs VALUES(?,?)', (self.sha, self.body))
        self.custody('fiction', self.path)

    def custody(self, attempt, path):
        self.store.db.execute('INSERT INTO artifact_custody VALUES(?,?,?,?,?,?)',
                              (attempt, path, 'role-owned', self.owner, '{}', self.sha))

    def request(self, path=None, consumer=False):
        path = path or self.path
        delivery = None
        if consumer:
            delivery = ident()
            self.store.config['delivery'] = {'recipients': {'Work': {'session': self.consumer}}}
            with self.store.tx():
                self.store._outbox('Reviews', 'Work', 'result', {'artifact_witnesses': [
                    {'path': path, 'source_attempt': 'fiction', 'sha256': self.sha}]}, key=delivery)
                self.store.db.execute('UPDATE outboxes SET board_receipt=? WHERE id=?', ('fictional-receipt', delivery))
        args = cli.parser().parse_args(['artifact-source', 'fiction', path] +
                                       (['--delivery', delivery] if delivery else []))
        def operate():
            with patch.dict(os.environ, {'CODEX_SESSION_ID': self.consumer if consumer else self.owner}):
                return cli.operate(args, self.store)
        return operate

    def export(self, **kwargs):
        return self.request(**kwargs)()

    def forbidden_body(self, operation, before_metadata=False):
        original = self.store.one
        def query(sql, *args):
            self.assertNotIn('SELECT body', sql)
            return original(sql, *args)
        body_reads = []
        def authorize(action, table, column, *_):
            if action == sqlite3.SQLITE_READ and table == 'artifact_blobs' and column == 'body':
                body_reads.append((table, column))
                return sqlite3.SQLITE_DENY
            return sqlite3.SQLITE_OK
        if before_metadata:
            self.store.db.set_authorizer(authorize)
        try:
            with patch.object(self.store, 'one', query), patch.object(cli.hashlib, 'sha256', side_effect=AssertionError('hash before refusal')), \
                    patch.object(cli.base64, 'b64encode', side_effect=AssertionError('export before refusal')), \
                    patch.object(Path, 'open', side_effect=AssertionError('file body before refusal')):
                with self.assertRaises(Refusal):
                    operation()
            self.assertEqual(body_reads, [])
        finally:
            self.store.db.set_authorizer(None)

    def test_current_exclusion_whole_log_and_retained_origin_refuse_owner_and_consumer(self):
        for consumer in (False, True):
            for kind in ('excluded', 'whole-log', 'origin', 'preimage', 'selected-log', 'legacy-stage', 'excluded-stage'):
                with self.subTest(consumer=consumer, kind=kind):
                    held = str(self.directory / 'fictional-held')
                    log = str(self.directory / 'WORK_LOG.md')
                    self.store.config['artifact_exclusions'] = [held]
                    candidate = held if kind == 'excluded' else log if kind == 'whole-log' else self.path
                    if candidate != self.path:
                        self.store.db.execute('DELETE FROM artifact_custody WHERE attempt=?', ('fiction',))
                        self.custody('fiction', candidate)
                    if kind == 'origin':
                        self.custody('fiction-origin', held)
                    if kind == 'preimage':
                        self.store.db.execute('INSERT INTO routine_runs(attempt,task,grant_id,policy,state,before_files) VALUES(?,?,?,?,?,?)',
                            ('fiction-preimage', 'fiction-task', 'fiction-grant', '{}', 'prepared', encode({held: {'sha256': self.sha}})))
                    if kind == 'selected-log':
                        self.store.config['tasks']['reviews-proposer']['routine_completion'] = {'bounded_log': {'target': self.path}}
                    if kind in {'legacy-stage', 'excluded-stage'}:
                        self.store.db.execute('INSERT INTO routine_stages VALUES(?,?,?)',
                            ('fiction-stage', log if kind == 'legacy-stage' else held, self.path))
                    self.forbidden_body(self.request(candidate, consumer), before_metadata=True)
                    self.assertEqual(self.store.one('SELECT count(*) AS n FROM artifact_blobs')['n'], 1)
                    self.store.db.execute('DELETE FROM artifact_custody WHERE attempt IN (?,?)', ('fiction', 'fiction-origin'))
                    self.store.db.execute('DELETE FROM routine_runs WHERE attempt=?', ('fiction-preimage',))
                    self.store.db.execute('DELETE FROM routine_stages WHERE attempt=?', ('fiction-stage',))
                    self.store.config['tasks']['reviews-proposer'].pop('routine_completion', None)
                    self.custody('fiction', self.path)

    def test_legal_export_entitlement_size_missing_and_integrity_preserve_custody(self):
        from coordinator_runtime.bounded_log import KIND
        self.store.db.execute('INSERT INTO routine_runs(attempt,task,grant_id,policy,state,before_files) VALUES(?,?,?,?,?,?)',
            ('fiction-bounded-stage', 'fiction-task', 'fiction-grant', encode({'kind': KIND}), 'prepared', '{}'))
        self.store.db.execute('INSERT INTO routine_stages VALUES(?,?,?)',
            ('fiction-bounded-stage', str(self.directory / 'WORK_LOG.md'), self.path))
        for consumer in (False, True):
            actual = self.export(consumer=consumer)
            self.assertEqual(base64.b64decode(actual['body_base64']), self.body)
            self.assertEqual(actual['owner'], self.owner)
            self.assertEqual(actual['attempt'], 'fiction')
        with patch.dict(os.environ, {'CODEX_SESSION_ID': ident()}):
            args = cli.parser().parse_args(['artifact-source', 'fiction', self.path])
            self.forbidden_body(lambda: cli.operate(args, self.store))
        self.store.config['limits']['max_artifact_bytes'] = len(self.body) - 1
        self.forbidden_body(self.export)
        self.store.config['limits']['max_artifact_bytes'] = len(self.body) + 10
        self.store.db.execute('UPDATE artifact_blobs SET body=?', (b'wrong',))
        with self.assertRaisesRegex(Refusal, 'no longer match'):
            self.export()
        self.store.db.execute('DELETE FROM artifact_blobs')
        with self.assertRaisesRegex(Refusal, 'unavailable'):
            self.export()
        self.assertIsNotNone(self.store.one('SELECT * FROM artifact_custody WHERE attempt=?', ('fiction',)))


class Routing(unittest.TestCase):
    def setUp(self):
        self.directory = Path(tempfile.mkdtemp(dir='/fixtures'))
        self.config = config_at(self.directory)
        self.store = enrolled(self.config)
        self.addCleanup(self.store.close)

    def proposal(self, required=True, semantic='DONE', malformed=False, code=0):
        self.config['tasks']['reviews-proposer']['delivery_required'] = required
        queued(self.store, event(self.config, ident(), 'Reviews', 'reviews-proposer'))
        job = self.store.reserve()
        attempt = self.store.start_job(job['id'], job['token'])
        # Actual adapter result builder; no transport, fake model call or native
        # identity. Original software fixtures explicitly retain their nature.
        turns = [{'fixture': 'local wire evidence only', 'full_answer': 'whole report with dissent/history', 'actual_END': None}]
        answer = reviews.proposal_result({'semantic': semantic, 'summary': 'whole source account', 'coverage': {'limits': ['fictional partial']}},
            'fictional-component', {'packet': {'answered_ids': ['R320-2']}}, 'fictional-original-collector', attempt, turns)
        if malformed:
            answer = {'bad': 'malformed original'}
        self.outcome = collect(self.store, attempt, answer, code=code)
        return job, attempt, answer

    def test_required_success_creates_single_integrator_response_then_work_route(self):
        job, attempt, answer = self.proposal()
        response = self.store.finish_job(job['id'], job['token'])
        actual = self.store.event(response)
        self.assertEqual(actual['allowed_tasks'], ['reviews-integrator'])
        self.assertEqual(actual['body'], answer)
        self.assertEqual(actual['source_attempt'], attempt)
        self.assertEqual(self.store.job(job['id'])['state'], 'awaiting-delivery')
        self.assertEqual(self.store.one('SELECT count(*) AS n FROM events WHERE parent=? AND id=?', (actual['parent'], response))['n'], 1)
        self.assertFalse(any(r['recipient'] == 'Work' for r in self.store.rows('SELECT * FROM outboxes WHERE job=?', (job['id'],))))
        queued(self.store, actual)
        integrated = self.store.reserve()
        self.assertEqual(integrated['task'], 'reviews-integrator')
        integrated_attempt = self.store.start_job(integrated['id'], integrated['token'])
        self.config['tasks']['reviews-integrator'].update(delivery_required=True, allowed_handoffs=['Work'])
        consolidated = result(category='consolidated')
        consolidated['findings'] = answer['findings']
        consolidated['handoffs'] = [{'recipient': 'Work', 'kind': 'result', 'text': 'Whole integrated report with original findings',
                                     'ref': None, 'required': 'settled'}]
        collect(self.store, integrated_attempt, consolidated)
        onward = self.store.finish_job(integrated['id'], integrated['token'])
        self.assertEqual(self.store.event(onward)['allowed_tasks'], ['work-proposer'])
        self.assertEqual(self.store.event(onward)['body']['findings'], answer['findings'])
        deliveries = self.store.rows("SELECT * FROM outboxes WHERE job=? AND recipient='Work'", (integrated['id'],))
        self.assertEqual(len(deliveries), 1)
        self.assertEqual(deliveries[0]['kind'], 'result')
        self.assertEqual(deliveries[0]['state'], 'classification-pending')
        self.assertEqual(json.loads(self.store.attempt(attempt)['result']), answer)

    def test_optional_success_keeps_internal_route(self):
        job, attempt, answer = self.proposal(required=False)
        self.assertIsNotNone(self.store.finish_job(job['id'], job['token']))
        self.assertEqual(self.store.job(job['id'])['state'], 'closed')
    def test_partial_keeps_original_semantics_and_sole_integrator(self):
        job, attempt, partial = self.proposal(semantic='PARTIAL')
        self.assertIsNone(self.store.finish_job(job['id'], job['token']))
        self.assertEqual(self.store.job(job['id'])['state'], 'held')
        self.assertEqual(json.loads(self.store.attempt(attempt)['result']), partial)
        self.assertTrue(partial['unknowns'])
        # The service's incomplete-return route conserves the whole original
        # call/outcome to the sole integrator, independently of generic failure.
        from coordinator_runtime.service import Dispatcher
        dispatcher = Dispatcher(self.store, {})
        dispatcher.review_failure_return(self.store.job(job['id']), attempt, self.outcome)
        from coordinator_runtime.contracts import digest
        actual = self.store.event(digest({'incomplete_ordinary_review': attempt}))
        self.assertEqual(actual['allowed_tasks'], ['reviews-integrator'])
        self.assertEqual(actual['body']['full_original_outcome'], self.outcome)

    def test_malformed_failure_keeps_whole_original_on_sole_integrator_route(self):
        from coordinator_runtime.service import Dispatcher
        from coordinator_runtime.contracts import digest
        job, attempt, original = self.proposal(malformed=True, code=7)
        dispatcher = Dispatcher(self.store, {})
        dispatcher.review_failure_return(self.store.job(job['id']), attempt, self.outcome)
        actual = self.store.event(digest({'incomplete_ordinary_review': attempt}))
        self.assertEqual(actual['allowed_tasks'], ['reviews-integrator'])
        self.assertEqual(actual['body']['full_original_outcome'], self.outcome)
        self.assertEqual(actual['body']['full_original_outcome']['result'], original)
        self.assertEqual(json.loads(self.store.attempt(attempt)['result']), original)


class Reader(unittest.TestCase):
    def setUp(self):
        self.directory = Path(tempfile.mkdtemp(dir='/fixtures'))
        self.repository = self.directory / 'source'
        self.repository.mkdir()
        self.git('init', '-q')
        self.git('config', 'user.name', 'Fictional fixture')
        self.git('config', 'user.email', 'fixture@invalid')
        self.bodies = {'a': b'first\n', 'b': b'\xff' + b'x' * (review_reader.CHUNK * 3), 'c': b'last\n'}
        for name, body in self.bodies.items():
            (self.repository / name).write_bytes(body)
        self.git('add', '.')
        self.git('-c', 'commit.gpgsign=false', 'commit', '-qm', 'fictional immutable input')
        self.pin = self.git('rev-parse', 'HEAD').decode().strip()
        self.history = self.directory / 'history'
        self.history.write_bytes(b'whole fictional history\n')
        self.method = self.directory / 'method'
        self.method.write_bytes(b'whole fictional method\n')
        self.manifest = {'repository': str(self.repository), 'history': str(self.history),
            'history_sha256': review_reader.digest(self.history.read_bytes()), 'prior_histories': {},
            'method_files': {str(self.method): review_reader.digest(self.method.read_bytes())}, 'correction_diff': 'exact diff',
            'source': {self.pin + ':' + name: {'bytes': len(body), 'sha256': review_reader.digest(body)} for name, body in self.bodies.items()}}
        self.path = self.directory / 'material.json'
        self.save()

    def git(self, *args):
        return subprocess.check_output(['git', '-c', 'gc.auto=0', '-c', 'maintenance.auto=false', '-C', str(self.repository), *args])

    def save(self):
        self.path.write_text(encode(self.manifest))

    def test_each_item_acquired_once_large_current_item_chunks_exact_end_and_reread(self):
        original = review_reader.acquire
        acquired, received = [], {}
        def count(manifest, item, files):
            acquired.append((item[0], item[1]))
            return original(manifest, item, files)
        peak_cache = 0
        with patch.object(review_reader, 'acquire', count), \
                patch.object(review_reader.subprocess, 'Popen', wraps=subprocess.Popen) as children:
            while True:
                answer = review_reader.next_chunk(self.path)
                if answer.get('end_of_material'):
                    break
                body = base64.b64decode(answer['text']) if answer['encoding'] == 'base64' else answer['text'].encode()
                self.assertLessEqual(len(body), review_reader.CHUNK)
                previous = received.setdefault(answer['source'], bytearray())
                self.assertEqual(len(previous), answer['offset'])
                previous.extend(body)
                self.assertEqual(answer['through'], len(previous))
                self.assertEqual(answer['sha256'], review_reader.digest(previous) if answer['through'] == answer['total_bytes']
                                 else review_reader.digest(self.bodies[answer['source'].split(':')[-1]]))
                peak_cache = max(peak_cache, self.path.with_suffix('.item').stat().st_size)
            self.assertEqual(len(acquired), 6)  # history, method, diff, three Git items
            self.assertEqual(sum(kind == 'git' for kind, _ in acquired), 3)
            self.assertEqual(children.call_count, 3)
            for name, expected in self.bodies.items():
                self.assertEqual(received[self.pin + ':' + name], expected)
            self.assertEqual(received['history'], self.history.read_bytes())
            self.assertEqual(received[str(self.method)], self.method.read_bytes())
            self.assertEqual(received['actual-correction-diff'], b'exact diff')
            first = review_reader.next_chunk(self.path)
            self.assertEqual(first['source'], 'history')
            self.assertEqual(len(acquired), 7)
        self.assertLessEqual(self.path.with_suffix('.item').stat().st_size, review_reader.MAX_ITEM + 32 * (review_reader.MAX_ITEM // review_reader.CHUNK + 1))
        self.assertLessEqual(self.path.with_suffix('.cursor').stat().st_size, review_reader.MAX_STATE)
        self.assertEqual(peak_cache, len(self.bodies['b']) + 32 * 4)

    def test_history_and_method_changes_mid_progress_refuse_before_output_revision_restarts(self):
        first = review_reader.next_chunk(self.path)
        review_reader.next_chunk(self.path)
        self.history.write_bytes(b'new permitted history\n')
        with self.assertRaisesRegex(ValueError, 'changed'):
            review_reader.next_chunk(self.path)
        self.manifest['history_sha256'] = review_reader.digest(self.history.read_bytes())
        self.save()
        revised = review_reader.next_chunk(self.path)
        self.assertNotEqual(first['material_revision'], revised['material_revision'])
        self.assertEqual(revised['offset'], 0)
        self.assertEqual(revised['text'], 'new permitted history\n')
        review_reader.next_chunk(self.path)
        self.method.write_bytes(b'changed method')
        with self.assertRaisesRegex(ValueError, 'changed'):
            review_reader.next_chunk(self.path)

    def test_prior_history_and_method_are_acquired_once_across_chunks(self):
        prior = self.directory / 'prior-history'
        prior.write_bytes(b'p' * (review_reader.CHUNK + 1))
        self.manifest['prior_histories'] = {str(prior): review_reader.digest(prior.read_bytes())}
        self.method.write_bytes(b'm' * (review_reader.CHUNK * 2 + 1))
        self.manifest['method_files'][str(self.method)] = review_reader.digest(self.method.read_bytes())
        self.save()
        counts = {}
        original = review_reader.read
        def counted(path):
            counts[str(path)] = counts.get(str(path), 0) + 1
            return original(path)
        with patch.object(review_reader, 'read', counted):
            while not review_reader.next_chunk(self.path).get('end_of_material'):
                pass
        for path in (prior, self.history, self.method):
            self.assertEqual(counts[str(path)], 1)

    def test_bad_source_length_hash_cache_mutation_and_bounds_refuse(self):
        self.assertEqual(review_reader.storage_bound(self.manifest), len(self.bodies['b']) + 32 * 4 + review_reader.MAX_STATE)
        for error in ('bytes', 'sha256'):
            self.manifest['source'][self.pin + ':a'][error] = 999 if error == 'bytes' else '0' * 64
            self.save()
            for _ in range(3):
                review_reader.next_chunk(self.path)
            with self.assertRaises(ValueError):
                review_reader.next_chunk(self.path)
            self.manifest['source'][self.pin + ':a'] = {'bytes': len(self.bodies['a']), 'sha256': review_reader.digest(self.bodies['a'])}
        self.save()
        for _ in range(5):
            answer = review_reader.next_chunk(self.path)
        self.assertEqual(answer['source'], self.pin + ':b')
        self.path.with_suffix('.item').write_bytes(b'corrupt')
        with self.assertRaisesRegex(ValueError, 'cache changed'):
            review_reader.next_chunk(self.path)
        self.manifest['source'][self.pin + ':b']['bytes'] = review_reader.MAX_ITEM + 1
        self.save()
        with self.assertRaisesRegex(ValueError, 'bound'):
            review_reader.storage_bound(self.manifest)
        for _ in range(4):
            review_reader.next_chunk(self.path)
        with self.assertRaisesRegex(ValueError, 'bound'):
            review_reader.next_chunk(self.path)


class GitHandback(unittest.TestCase):
    def setUp(self):
        self.directory = Path(tempfile.mkdtemp(dir='/fixtures'))
        self.repository = self.directory / 'source'
        self.repository.mkdir()
        self.remote = self.directory / 'remote.git'
        self.run_command('git', 'init', '--bare', '-q', str(self.remote))
        self.git('init', '-q', '-b', 'fictional-existing')
        self.git('config', 'user.name', 'Fictional signing fixture')
        self.git('config', 'user.email', 'fixture@invalid')
        self.key = self.directory / 'fixture-key'
        self.run_command('ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(self.key))
        allowed = self.directory / 'allowed-signers'
        allowed.write_text('fixture@invalid ' + self.key.with_suffix('.pub').read_text())
        self.git('config', 'gpg.format', 'ssh')
        self.git('config', 'user.signingkey', str(self.key))
        self.git('config', 'gpg.ssh.allowedSignersFile', str(allowed))
        self.git('remote', 'add', 'origin', str(self.remote))
        self.module = self.repository / 'module.py'
        self.module.write_text('value = 1\n')
        self.git('add', 'module.py')
        self.git('commit', '-S', '-qm', 'fictional signed baseline')
        # Create three loose objects in the bucket Git samples for auto-GC, without
        # thousands of Git processes or a shared-object census.
        objects = 0
        for value in range(10000):
            body = str(value).encode()
            oid = hashlib.sha1(b'blob ' + str(len(body)).encode() + b'\0' + body).hexdigest()
            if oid.startswith('17'):
                self.git('hash-object', '-w', '--stdin', input=body)
                objects += 1
                if objects == 3:
                    break
        else:
            self.fail('finite fictional auto-GC control object not found')
        self.git('config', 'gc.auto', '1')
        self.git('config', 'gc.autoDetach', 'false')
        self.git('config', 'maintenance.auto', 'true')
        self.marker = self.directory / 'auto-maintenance-marker'
        self.hook('pre-auto-gc', '#!/bin/sh\necho prohibited > ' + str(self.marker) + '\nexit 1\n')

    def run_command(self, *args, **kwargs):
        # subprocess returns the numeric original END; no provider process.
        actual = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs)
        records = self.directory / 'fixture-commands.jsonl'
        with records.open('a') as stream:
            stream.write(json.dumps({'argv': args, 'actual_END': actual.returncode,
                'stdout': actual.stdout.decode(errors='backslashreplace'), 'stderr': actual.stderr.decode(errors='backslashreplace')}) + '\n')
        actual.check_returncode()
        return actual

    def git(self, *args, **kwargs):
        return self.run_command('git', '-c', 'gc.auto=0', '-c', 'maintenance.auto=false', '-C', str(self.repository), *args, **kwargs)

    def hook(self, name, body):
        path = self.repository / '.git' / 'hooks' / name
        path.write_text(body)
        path.chmod(0o700)

    def test_actual_auto_gc_control_normal_hooks_signing_publication_and_partial_handback(self):
        # Positive auto-maintenance control runs only on this owned fiction.
        self.git('-c', 'gc.auto=1', '-c', 'maintenance.auto=true', 'gc', '--auto')
        self.assertTrue(self.marker.exists())
        self.marker.unlink()
        hooks = self.directory / 'ordinary-hook'
        self.hook('pre-commit', '#!/bin/sh\ngit config --get gc.auto > ' + str(hooks) +
                  '\ngit config --get maintenance.auto >> ' + str(hooks) + '\ngit gc --auto\n')
        self.module.write_text('value = 2\n')
        answer = coding.publish(str(self.repository), 'fictional-existing', ['module.py'], 'fictional signed handback',
                                self.directory / 'success', partial=True)
        self.assertEqual(answer['errors'], [])
        self.assertTrue(answer['partial'])
        self.assertEqual(hooks.read_text(), '0\nfalse\n')
        self.assertFalse(self.marker.exists())
        self.assertEqual(answer['head'], answer['remote_head'])
        self.assertTrue(all(type(r['actual_END']) is int and r['capture'] == 'complete' for r in answer['attempts']))
        self.git('verify-commit', answer['head'])
        self.module.write_text('value = 3\n')
        self.hook('pre-commit', '#!/bin/sh\nexit 7\n')
        failed = coding.publish(str(self.repository), 'fictional-existing', ['module.py'], 'fictional refused handback',
                                self.directory / 'failure', partial=True)
        self.assertEqual(failed['head'], answer['head'])
        self.assertEqual(failed['remote_head'], answer['head'])
        self.assertTrue(any('signed commit failed' in e for e in failed['errors']))
        self.assertTrue(any('dirty/unpublished' in e for e in failed['errors']))
        self.assertTrue(any('push' in r['argv'] and r['actual_END'] == 0 for r in failed['attempts']))
        self.assertFalse(self.marker.exists())

    def test_real_numeric_error_and_incomplete_pipe_capture_preserved(self):
        git = coding.Git(str(self.repository), self.directory / 'captures')
        code, _ = git.run('-c', 'alias.local-end=!exit 7', 'local-end')
        self.assertEqual(code, 7)
        code, body = git.run('-c', 'alias.local-bound=!/usr/bin/python3 -c \'import sys; sys.stdout.write("x"*262144)\'', 'local-bound')
        self.assertEqual(git.records[-1]['actual_END'], code)
        self.assertEqual(git.records[-1]['capture'], 'incomplete')
        self.assertLessEqual(len(body), 131072)
        self.assertIn('bound exceeded', git.records[-1]['error'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
