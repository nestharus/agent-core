"""Decision426/429 construction controls: fictional values, in-memory SQLite.

Uses production IntegrationJournal, DeliveryJournal constructors and Access,
plus the exact Store methods selected by test_integration_bound419. Allocation,
transactions and disk budgeting retain that fixture's explicit limitations.
No actual runtime, configuration file, account, Board, provider or artifact I/O.
"""
import copy
import json
import unittest

from test_integration_bound419 import Journal
from coordinator_runtime.contracts import Refusal, digest, encode, task_result
from coordinator_runtime.delivery import DeliveryJournal
from coordinator_runtime.integration_evidence import expand, expand_shared, SHARED_FORMAT
from coordinator_runtime.processing import Access, SCHEMA, implementation


def narrative(label, size):
    # Distinct fictional evidence, including multibyte text; never actual rows.
    text = ''.join(f'{label} item {i}: fictional source/custodian 未知; END leaves '
                   'delivery, publication and original recovery obligations open. '
                   for i in range(size // 90 + 1))
    return text.encode()[:size].decode(errors='ignore')


class WitnessJournal(Journal, DeliveryJournal):
    def __init__(self):
        super().__init__()
        self.config['actor'] = 'synthetic-owner'
        self.config['limits'].update(max_events=50, max_outboxes=20)
        self.config['delivery'] = {'recipients': ['Work', 'Branch', 'Reviews']}
        self.config['tasks']['integrate']['allowed_handoffs'] = ['Branch', 'Reviews']
        handoffs = [{'recipient': r, 'kind': 'unfamiliar-intent', 'required': 'settled',
                     'text': narrative('fictional handoff ' + r, n), 'ref': None}
                    for r, n in [('Branch', 1514), ('Reviews', 746)]]
        result = {'semantic': 'PARTIAL', 'category': 'blocker', 'summary': narrative('summary', 614),
                  'findings': [{'question': i, 'observation': narrative('finding ' + str(i), 1905)} for i in range(18)],
                  'failures': [narrative('failure ' + str(i), 440) for i in range(4)],
                  'unknowns': [narrative('unknown ' + str(i), 375) for i in range(6)],
                  'completion': {'held': narrative('completion', 7691)}, 'artifacts': [], 'handoffs': handoffs}
        task_result(result)  # Independent public protocol admission, not a codec oracle.
        detail = {'prior_turn_result': result, **{
            'fictional_unclassified_' + str(i): narrative('unclassified detail ' + str(i), 275)
            for i in range(40)}}
        self.db.execute("UPDATE attempts SET result=?,detail=?,session='fictional-producer' WHERE id='old-a'",
                        (encode(result), encode(detail)))
        event = self.event('old-input')
        event['kind'] = 'board'
        event['body'] = {'text': narrative('known input text', 1378), **{
            'fictional_unknown_body_' + str(i): narrative('unknown body ' + str(i), 6450)
            for i in range(12)}}
        event.update({f'fictional_unknown_event_{i}': f'unknown event field {i}' for i in range(3)})
        self.db.execute("UPDATE events SET payload=?,hash=? WHERE id='old-input'", (encode(event), digest(event)))
        self.db.execute('DELETE FROM outboxes')
        job, attempt = self.job('old'), self.attempt('old-a')
        self.owner_question(job, attempt, 'Fictional unresolved interpretation')
        self.owner_question(job, attempt, 'Fictional unknown publication effects', effects=True)
        # Public failure_delivery constructs this projection. Exercise both
        # equal and invalid-result variants without invoking classification I/O.
        informative = {'original_result': result, 'projection': task_result(result),
                       'disposition': 'incomplete; execution/effects/source remain held',
                       'capture': attempt['capture'], 'capture_error': attempt['error'],
                       'exit': attempt['exit'], 'contract_errors': []}
        for index, handoff in enumerate(handoffs):
            self._task_handoff(job, attempt, self.config['tasks']['integrate'],
                               {'category': 'blocker'}, handoff, index, informative)
        # Distinct occurrences and failure/receipt states survive equal values.
        rows = self.rows('SELECT * FROM outboxes ORDER BY rowid')
        for i, row in enumerate(rows):
            payload = json.loads(row['payload'])
            if 'informative_failure' in payload:
                payload['fictional_unknown_delivery'] = narrative('distinct delivery extension ' + str(i), 7500)
            self.db.execute('UPDATE outboxes SET state=?,error=?,board_receipt=?,payload=? WHERE id=?',
                            ('sent' if i % 2 else 'pending', 'fictional error ' + str(i),
                             encode({'fictional_receipt': i}), encode(payload), row['id']))


def processing_access(s):
    s.db.executescript(SCHEMA)
    # Separate packages let the first member pass while only the later member's
    # ordinary admission/scope/ancestry is changed.
    for name in ['next-input', 'later-input']:
        event = {**s.event(name), 'package': 'fictional-' + name, 'kind': 'response', 'role': 'Work'}
        if name == 'later-input':
            event['parent'] = 'fictional-birth'
        s.db.execute('UPDATE events SET payload=?,hash=? WHERE id=?', (encode(event), digest(event), name))
        s.db.execute('UPDATE queue SET package=? WHERE event=?', (event['package'], name))
    birth = {'id': 'fictional-birth', 'package': 'fictional-later-input', 'kind': 'board', 'role': 'Work'}
    s.insert('events', {'id': birth['id'], 'role': 'Work', 'payload': encode(birth), 'hash': digest(birth), 'received': 0})
    receipt = {'task_scopes': ['integrate'], 'software_admission': {'source_hash': digest(birth)}}
    s.insert('admissions', {'package': birth['package'], 'owner': s.config['actor'], 'receipt': encode(receipt)})
    s.insert('processing_admissions', {'package': birth['package'], 'capability': 'fictional-cap',
        'event': birth['id'], 'scope': 'fictional-scope', 'receipt': encode(receipt), 'created': 1})
    selection = {'expires': 1000, 'retained_events': ['next-input', 'later-input', birth['id']],
        'future_intake': False, 'tasks': ['integrate'], 'max_starts': 5,
        'basis': {'configuration': digest(s.config), 'implementation': implementation(),
            'roles': {'Work': {'original': {'events': [
                {'id': e, 'hash': digest(s.event(e))} for e in ['next-input', 'later-input', birth['id']]]}}}}}
    s.insert('processing_capabilities', {'id': 'fictional-cap', 'issuer': 'synthetic-owner',
        'selection': encode(selection), 'created': 1})
    s.processing = Access(s, 'fictional-cap')


def reject_later(s, kind):
    if kind == 'admission':
        s.db.execute("UPDATE admissions SET owner='fictional-other-owner'")
    elif kind == 'taskscope':
        row = s.one('SELECT * FROM processing_admissions')
        receipt = json.loads(row['receipt']); receipt['task_scopes'] = ['fictional-other-task']
        s.db.execute('UPDATE processing_admissions SET receipt=?', (encode(receipt),))
        s.db.execute('UPDATE admissions SET receipt=?', (encode(receipt),))
    elif kind == 'ancestry':
        s.db.execute("UPDATE processing_admissions SET event='fictional-unrelated-birth'")
    else:
        s.db.execute("UPDATE processing_capabilities SET revoked=99")


class WitnessControls(unittest.TestCase):
    def journal(self, processing=False):
        s = WitnessJournal()
        self.addCleanup(s.db.close)
        s.retire()
        if processing:
            processing_access(s)
        return s

    def test_current_shape_fit_four_duties_unknowns_and_exact_reconstruction(self):
        s = self.journal()
        original = s.snapshot()
        rows = s.rows('SELECT * FROM outboxes ORDER BY rowid')
        self.assertEqual(4, len(rows))
        raw_bytes = sum(len(r['payload'].encode()) for r in rows)
        self.assertGreater(raw_bytes, 543981)
        attempt = s.attempt('old-a')
        self.assertGreater(len(attempt['result'].encode()), 49730)
        self.assertGreater(len(attempt['detail'].encode()), 61074)
        self.assertGreater(len(s.one("SELECT payload FROM events WHERE id='old-input'")['payload'].encode()), 79316)
        receipt = s.selection()
        debt = receipt['basis']['debt'][0]
        self.assertEqual('integration-debt-v2', debt['representation'])
        self.assertLess(len(encode(receipt).encode()), 262144)
        pool = debt['shared_values']
        for table, fields in [('attempts', ['result', 'detail']), ('outboxes', ['payload'])]:
            for row in debt[table]:
                old = next(r for r in original[table] if r['id'] == row['id'])
                for field in fields:
                    packed = row[field]
                    self.assertEqual(json.loads(old[field]), expand_shared(packed, pool))
                    self.assertEqual(old[field], expand(packed['original_column'], old))
                    self.assertEqual({k: v for k, v in old.items() if k not in fields},
                                     {k: v for k, v in row.items() if k not in fields})
        s.select_integration_window('synthetic-owner', receipt)
        job = s.reserve(); aid = s.start_job(job['id'], job['token']); s.authorize_launch(aid)
        for table in ['outboxes', 'results', 'file_publications', 'source_custody', 'artifact_custody']:
            self.assertEqual(original[table], s.snapshot()[table])
        self.assertEqual(attempt, s.attempt('old-a'))
        self.assertEqual(['next-input', 'later-input'], [m['event'] for m in json.loads(job['members'])])
        print('WITNESS427', encode({'fictional_outbox_utf8': raw_bytes,
            'fictional_result_utf8': len(attempt['result'].encode()),
            'fictional_detail_utf8': len(attempt['detail'].encode()),
            'fictional_input_utf8': len(debt['inputs'][0]['payload'].encode()),
            'basis_utf8': len(encode(receipt['basis']).encode()), 'receipt_utf8': len(encode(receipt).encode()),
            'ceiling': 262144, 'deliveries': 4, 'fictional_allocations': s.allocations}))

    def test_shared_missing_changed_conflicting_and_token_like_unknown(self):
        s = self.journal()
        debt = s.integration_debt()[0]; pool = debt['shared_values']; packed = debt['attempts'][0]['result']
        for broken in [{}, {k: {**v, 'value': {'changed': True}, 'references': []} for k, v in pool.items()}]:
            with self.assertRaises(Refusal): expand_shared(packed, broken)
        cycle = copy.deepcopy(pool)
        key = packed['references'][0]['sha256']
        cycle[key] = {'format': SHARED_FORMAT, 'value': None,
                      'references': [{'json_path': [], 'sha256': key}]}
        with self.assertRaises(Refusal): expand_shared(packed, cycle)
        bad = copy.deepcopy(packed); bad['references'] *= 2
        with self.assertRaises(Refusal): expand_shared(bad, pool)
        literal = {'format': SHARED_FORMAT, 'value': None, 'references': [{'json_path': [], 'sha256': 'unknown'}]}
        row = s.attempt('old-a'); detail = json.loads(row['detail']); detail['unknown_token'] = literal
        s.db.execute("UPDATE attempts SET detail=? WHERE id='old-a'", (encode(detail),))
        debt = s.integration_debt()[0]
        self.assertEqual(literal, expand_shared(debt['attempts'][0]['detail'], debt['shared_values'])['unknown_token'])

    def test_historical_differences_unknown_fields_and_malformed_payloads_survive(self):
        s = self.journal(); old = s.rows('SELECT * FROM outboxes ORDER BY rowid')[0]
        payload = json.loads(old['payload'])
        payload['result']['unknowns'].append('Fictional historical snapshot differs from current attempt')
        payload['unknown_extension'] = {'placement': 'distinct fictional delivery meaning'}
        s.db.execute('UPDATE outboxes SET payload=? WHERE id=?', (encode(payload), old['id']))
        debt = s.integration_debt()[0]; packed = debt['outboxes'][0]['payload']
        self.assertEqual(payload, expand_shared(packed, debt['shared_values']))
        # No value match can turn a historical difference into a current value.
        self.assertEqual(payload['result'], packed['value']['result'])
        for raw in ['not-json', '{"unknown":1,"unknown":2}', ' [1, 2] ', '{ "unknown": true }']:
            s.db.execute('UPDATE outboxes SET payload=? WHERE id=?', (raw, old['id']))
            self.assertEqual(raw, s.integration_debt()[0]['outboxes'][0]['payload'])

    def test_invalid_result_projection_retains_its_distinct_wrapper(self):
        s = self.journal()
        for row in s.rows('SELECT * FROM outboxes ORDER BY rowid'):
            payload = json.loads(row['payload'])
            if 'informative_failure' not in payload:
                continue
            failure = payload['informative_failure']
            failure['projection'] = {'invalid_result': failure['original_result']}
            failure['contract_errors'] = ['Fictional rejected protocol result; original remains held']
            s.db.execute('UPDATE outboxes SET payload=? WHERE id=?', (encode(payload), row['id']))
        debt = s.integration_debt()[0]
        for row in debt['outboxes']:
            original = json.loads(s.one('SELECT payload FROM outboxes WHERE id=?', (row['id'],))['payload'])
            self.assertEqual(original, expand_shared(row['payload'], debt['shared_values']))

    def test_shared_material_changes_invalidate_all_later_boundaries(self):
        changes = ["UPDATE attempts SET result=replace(result,'finding 0','changed 0') WHERE id='old-a'",
                   "UPDATE attempts SET detail=replace(detail,'unclassified detail 0','new detail 0') WHERE id='old-a'",
                   "UPDATE outboxes SET payload=replace(payload,'Fictional unresolved','Later unresolved')",
                   "UPDATE events SET payload=replace(payload,'unknown body 0','changed body 0') WHERE id='old-input'"]
        for sql in changes:
            for phase in ['selection', 'reservation', 'start', 'authorization']:
                with self.subTest(sql=sql, phase=phase):
                    s = self.journal(); receipt = s.selection()
                    if phase != 'selection': s.select_integration_window('synthetic-owner', receipt)
                    job = s.reserve() if phase in {'start', 'authorization'} else None
                    aid = s.start_job(job['id'], job['token']) if phase == 'authorization' else None
                    before = s.integration_debt(); s.db.execute(sql)
                    self.assertNotEqual(before, s.integration_debt())
                    if phase == 'reservation':
                        self.assertIsNone(s.reserve())
                    else:
                        with self.assertRaises(Refusal):
                            if phase == 'selection': s.select_integration_window('synthetic-owner', receipt)
                            elif phase == 'start': s.start_job(job['id'], job['token'])
                            else: s.authorize_launch(aid)

    def test_later_member_ordinary_predicate_at_every_boundary(self):
        for kind in ['admission', 'taskscope', 'ancestry']:
            for phase in ['composition', 'selection', 'reservation', 'start', 'authorization']:
                with self.subTest(kind=kind, phase=phase):
                    s = self.journal(processing=True)
                    first = s.one("SELECT * FROM queue WHERE event='next-input'")
                    later = s.one("SELECT * FROM queue WHERE event='later-input'")
                    self.assertTrue(s.processing.task(first)); self.assertTrue(s.processing.task(later))
                    receipt = s.selection()
                    if phase in {'reservation', 'start', 'authorization'}: s.select_integration_window('synthetic-owner', receipt)
                    job = s.reserve() if phase in {'start', 'authorization'} else None
                    aid = s.start_job(job['id'], job['token']) if phase == 'authorization' else None
                    reject_later(s, kind)
                    self.assertTrue(s.processing.task(first)); self.assertFalse(s.processing.task(later))
                    if phase in {'composition', 'selection', 'reservation'}:
                        self.assertEqual(['next-input'], [m['event'] for m in s._members(first)])
                    before = s.snapshot(); allocations = s.allocations
                    if phase == 'reservation': self.assertIsNone(s.reserve())
                    else:
                        with self.assertRaises(Refusal):
                            if phase == 'composition': s.selection()
                            elif phase == 'selection': s.select_integration_window('synthetic-owner', receipt)
                            elif phase == 'start': s.start_job(job['id'], job['token'])
                            else: s.authorize_launch(aid)
                    self.assertEqual(before, s.snapshot()); self.assertEqual(allocations, s.allocations)

    def test_valid_processing_and_revoked_currentness(self):
        s = self.journal(processing=True); s.select(); job = s.reserve()
        aid = s.start_job(job['id'], job['token']); s.authorize_launch(aid)
        self.assertEqual(1, s.allocations)
        reject_later(s, 'revoked')
        with self.assertRaises(Refusal): s.authorize_launch(aid)

    def test_current_selection_expiry_source_and_task_changes_before_execution(self):
        for kind in ['expiry', 'source', 'task']:
            for phase in ['start', 'authorization']:
                with self.subTest(kind=kind, phase=phase):
                    s = self.journal(processing=True); s.select(); job = s.reserve()
                    aid = s.start_job(job['id'], job['token']) if phase == 'authorization' else None
                    cap = s.one('SELECT * FROM processing_capabilities')
                    selection = json.loads(cap['selection'])
                    if kind == 'expiry': selection['expires'] = s.clock()
                    elif kind == 'source': selection['basis']['implementation']['integration.py'] = 'fictional changed source'
                    else: selection['tasks'] = ['fictional-other-task']
                    s.db.execute('UPDATE processing_capabilities SET selection=?', (encode(selection),))
                    before = s.snapshot(); allocations = s.allocations
                    with self.assertRaises(Refusal):
                        if phase == 'start': s.start_job(job['id'], job['token'])
                        else: s.authorize_launch(aid)
                    self.assertEqual(before, s.snapshot()); self.assertEqual(allocations, s.allocations)


if __name__ == '__main__':
    unittest.main(verbosity=2)
