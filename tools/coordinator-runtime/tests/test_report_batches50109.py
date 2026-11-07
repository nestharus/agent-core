"""New owned public Board fiction for exact Reviews composition boundaries."""
import copy
import json
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from test_qa629_repairs import Fixture, actor
from support import result, collect
from coordinator_runtime import processing, prospective, service, report_scope, resource_scopes
from coordinator_runtime.contracts import Refusal, digest, encode


class ReportTypeConservation(unittest.TestCase):
    """In-memory source/parser/validator fixtures; no Board or runtime execution.

    Current resource admission is an explicit seam. Whole event/member hashes,
    envelope acquisition, collected JSON parsing and result validation are real.
    """
    def setUp(self):
        self.sources = {}
        self.hashes = {}
        for index in range(2):
            event = dict(id='offline-report710-'+str(index), body=dict(
                kind='attributed-report', native_owner_execution=False,
                meaning='Original attribution remains input, never authority',
                original=dict(reference='offline-receipt710-'+str(index), collector='fictional Work',
                    actual_END=0, reports=[dict(name='Source', body='Whole fictional dissent Ω: retain all history')],
                    history='Original method and collection history', method_pin='fictional HIGH',
                    effects='known-report-only', coverage=dict(status='PARTIAL', unread=['original-family'],
                        dissent=[dict(author='fictional reviewer', meaning='Original uncertainty remains')],
                        nested=[dict(disabled=False, enabled=True, zero=0, one=1, real=1.0,
                                     negative_zero=-0.0, missing=None, text='0', array=[], object={})]))))
            self.sources[event['id']] = encode(event)
            self.hashes[event['id']] = digest(event)
        self.members = encode([dict(event=key, hash=value) for key, value in self.hashes.items()])
        self.before = dict(self.sources)
        self.hold = False
        self.current = True
        def one(sql, params):
            if sql == 'SELECT id FROM jobs WHERE id=?':
                self.assertEqual(params, ('offline-job710',))
                return dict(id=params[0])
            if sql == 'SELECT capability,source_hash,receipt_hash FROM processing_report_inputs WHERE event=?':
                return None
            self.assertEqual(sql, 'SELECT id,role,hold,hash FROM events WHERE id=?')
            return dict(id=params[0], role='Reviews', hold='held' if self.hold else None, hash=self.hashes[params[0]])
        self.runtime = SimpleNamespace(one=one, event=lambda key: json.loads(self.sources[key]),
            db=SimpleNamespace(in_transaction=True),
            job=lambda key: dict(members=self.members),
            processing=SimpleNamespace(current=lambda: (None, dict(service=dict(legacy_resources=dict(
                Reviews=dict(reviews_report={'fixture': 'already admitted'}))), tasks=['reviews-integrator'])),
                event=lambda event: self.current))
        self.row = dict(id='offline-job710', role='Reviews', task='reviews-integrator', package=None)
        self.gate = self.enterContext(patch('coordinator_runtime.resource_scopes.blocked', return_value=False))
        self.enterContext(patch('coordinator_runtime.configuration.processing_tasks', return_value=None))
        self.enterContext(patch('coordinator_runtime.configuration.event_allowed', return_value=True))
        # Spell out the expected copied envelopes independently of conserved_inputs.
        self.envelopes = [dict(event=key, sha256=self.hashes[key], original=json.loads(value)['body'])
                          for key, value in self.sources.items()]

    def tearDown(self):
        self.assertEqual(self.sources, self.before)  # Stored source bytes never rewritten by validation.

    def validate(self, findings):
        from coordinator_runtime.contracts import collected_task_result
        answer = dict(semantic='DONE', category='consolidated', summary='Owned offline conservation fixture',
                      findings=findings, failures=[], unknowns=[], artifacts=[])
        raw = encode(answer)
        parsed = collected_task_result(dict(capture='complete', result=raw, detail='{}'))
        try:
            report_scope.validate_result(self.runtime, self.row, parsed)
        finally:
            self.assertEqual(encode(parsed), raw)  # Result bodies also remain untouched.

    def test_valid_whole_copied_envelopes_with_separate_analysis(self):
        self.validate([dict(analysis='Additional reasoning grants no authority'),
                       dict(collected_reports=copy.deepcopy(self.envelopes))])
        self.gate.assert_called_once_with(self.runtime, self.row)

    def test_nested_boolean_number_substitutions_refused_in_both_directions(self):
        for key, replacement in [('disabled', 0), ('enabled', 1), ('zero', False), ('one', True)]:
            with self.subTest(key=key):
                changed = copy.deepcopy(self.envelopes)
                changed[1]['original']['original']['coverage']['nested'][0][key] = replacement
                with self.assertRaisesRegex(Refusal, 'exact whole original report'):
                    self.validate([dict(collected_reports=changed)])

    def test_outer_native_false_and_original_numeric_end_cannot_exchange_types(self):
        for location, key, value in [('body', 'native_owner_execution', 0), ('receipt', 'actual_END', False)]:
            with self.subTest(location=location):
                changed = copy.deepcopy(self.envelopes)
                target = changed[0]['original']
                if location == 'receipt': target = target['original']
                target[key] = value
                with self.assertRaises(Refusal): self.validate([dict(collected_reports=changed)])

    def test_missing_extra_changed_and_reordered_whole_content_refused(self):
        mutations = [lambda e: e.pop(), lambda e: e.append(copy.deepcopy(e[0])), lambda e: e.reverse(),
            lambda e: e[0].update(sha256='0'*64),
            lambda e: e[0]['original']['original'].pop('history'),
            lambda e: e[0]['original']['original'].update(extra='unselected data'),
            lambda e: e[0]['original']['original']['reports'][0].update(body='Summary replacing whole dissent'),
            lambda e: e[0]['original']['original']['coverage']['dissent'].clear()]
        for index, mutate in enumerate(mutations):
            with self.subTest(mutation=index):
                changed = copy.deepcopy(self.envelopes)
                mutate(changed)
                with self.assertRaises(Refusal): self.validate([dict(collected_reports=changed)])
        with self.assertRaises(Refusal): self.validate([])
        with self.assertRaises(Refusal): self.validate([dict(collected_reports=self.envelopes, extra='wrapper')])

    def test_other_json_scalar_and_container_types_remain_distinct(self):
        for key, replacement in [('missing', False), ('text', 0), ('array', {}), ('object', []), ('zero', '0')]:
            with self.subTest(key=key):
                changed = copy.deepcopy(self.envelopes)
                changed[0]['original']['original']['coverage']['nested'][0][key] = replacement
                with self.assertRaises(Refusal): self.validate([dict(collected_reports=changed)])

    def test_key_order_and_whitespace_follow_existing_canonical_source_pins(self):
        def reverse_keys(value):
            if isinstance(value, dict): return {key: reverse_keys(value[key]) for key in reversed(value)}
            if isinstance(value, list): return [reverse_keys(item) for item in value]
            return value
        reordered = json.loads(json.dumps(reverse_keys(self.envelopes), indent=2, ensure_ascii=False))
        self.validate([dict(collected_reports=reordered)])

    def test_numeric_identity_matches_source_digest_without_new_normalization(self):
        for key, replacement in [('one', 1.0), ('real', 1), ('negative_zero', 0.0), ('one', 2**53+1)]:
            with self.subTest(key=key, replacement=replacement):
                changed = copy.deepcopy(self.envelopes)
                changed[0]['original']['original']['coverage']['nested'][0][key] = replacement
                self.assertNotEqual(digest(changed), digest(self.envelopes))
                with self.assertRaises(Refusal): self.validate([dict(collected_reports=changed)])
        # Lexical exponent/decimal spelling is already lost by the real parser;
        # 1e0 and 1.0 share the same canonical float pin. Integer -0 is likewise 0.
        raw = encode(self.envelopes).replace('"real":1.0', '"real":1e0').replace('"zero":0', '"zero":-0')
        from coordinator_runtime.contracts import parse_json
        reparsed = parse_json(raw)
        self.assertEqual(digest(reparsed), digest(self.envelopes))
        self.validate([dict(collected_reports=reparsed)])

    def test_admission_hold_and_current_source_authority_still_refuse(self):
        self.gate.return_value = True
        with self.assertRaisesRegex(Refusal, 'authority/resources changed'):
            self.validate([dict(collected_reports=self.envelopes)])
        self.gate.return_value = False
        self.hold = True
        with self.assertRaisesRegex(Refusal, 'held, changed or outside current authority'):
            self.validate([dict(collected_reports=self.envelopes)])
        self.hold = False
        self.current = False
        with self.assertRaisesRegex(Refusal, 'held, changed or outside current authority'):
            self.validate([dict(collected_reports=self.envelopes)])

    def test_changed_pinned_source_refused_without_refresh_or_rewrite(self):
        key = next(iter(self.sources))
        original = self.sources[key]
        self.sources[key] = original.replace('Original method', 'Altered method')
        try:
            with self.assertRaisesRegex(Refusal, 'original whole report member changed'):
                self.validate([dict(collected_reports=self.envelopes)])
        finally:
            self.sources[key] = original

    def test_whole_return_budget_keeps_exact_boundary_without_truncation(self):
        reports = copy.deepcopy(self.envelopes)
        body = reports[0]['original']['original']['reports'][0]
        body['body'] = ''
        limit = 262144
        room = limit-len(encode(report_scope.complete_return(reports)).encode())
        body['body'] = 'x'*room
        runtime = SimpleNamespace(config=dict(limits=dict(max_result_bytes=limit)))
        self.assertEqual(len(encode(report_scope.complete_return(reports)).encode()), limit)
        self.assertTrue(report_scope.fits_return(runtime, reports))
        body['body'] += 'x'
        before = encode(reports)
        self.assertFalse(report_scope.fits_return(runtime, reports))
        self.assertEqual(encode(reports), before)

    def test_unselected_route_still_requires_no_report_finding(self):
        with patch.object(report_scope, 'integration_inputs', return_value=None):
            self.validate([dict(analysis='No selected collected report lane')])


class ReportBatches(Fixture):
    def setUp(self):
        self.bootstrap(self.configure)
        self.issuer = self.config['roles']['Work']['owner']
        for r,b in self.boards.items():
            with actor(b.store,self.issuer): b.revoke_software(self.store,self.store.enrollment(r)['grant_id'])
            self.store.db.execute('UPDATE enrollments SET intake=0 WHERE role=?',(r,))
        self.store.db.execute("UPDATE enrollments SET legacy_hold='Reviews UNKNOWN' WHERE role='Reviews'")
        self.boards={r:processing.ProcessingBoard(self.config,r) for r in self.config['roles']}
        for b in self.boards.values(): b.runtime=self.store
        n=160000 if 'large' in self._testMethodName else 32
        self.reports=[dict(reference='report-'+str(i),collector=self.issuer,actual_END=0,
            reports=[dict(name='Source',body='x'*n+' \" dissent Ω')],history='Whole fictional history',
            method_pin='fiction HIGH',coverage=dict(status='PARTIAL',unread=['family9']),effects='known-report-only') for i in range(2)]
        self.selection=dict(basis=processing.basis(self.store,self.boards),authority='Fictional Work finite report scope',
            retained_events=[],recover_controls={},future_intake=True,tasks=list(self.config['tasks']),
            max_shared_rows=1000,max_shared_payload_bytes=1000000,max_runtime_rows=1000,
            service=dict(max_inflight=8,reviews={},report_tasks=['reviews-integrator'],legacy_resources={'Reviews':dict(
                original_hold='Reviews UNKNOWN',roots=[],unbounded=True,evidence='Unrelated debts retained',
                reviews_report=dict(version='reviews-report-v1',authority='Fictional exact report choice',expires=time.time()+600,
                    task='reviews-integrator',task_sha256=digest(self.config['tasks']['reviews-integrator']),
                    reports=[dict(reference=r['reference'],sha256=digest(r)) for r in self.reports]))}))
        with actor(self.boards['Work'].store,self.issuer): self.cap=processing.select(self.store,self.boards,self.selection)['capability']
        self.store.processing=processing.Access(self.store,self.cap,self.boards)
        self.runtime.boards=self.boards
        self.epoch=prospective.select(self.store,self.issuer,dict(configuration=digest(self.config),authority='Fictional exact no-effect choice',
            expires=time.time()+600,processing_capability=self.cap,grants={r:self.store.enrollment(r)['grant_id'] for r in self.config['roles']},
            tasks={t:dict(task_hash=digest(v),software_handoffs={},ordinary_effects=False) for t,v in self.config['tasks'].items()}))

    def configure(self):
        self.config['limits']['max_result_bytes']=262144
        t=self.config['tasks']['reviews-integrator']; t.update(effects='owned-artifacts',sandbox='workspace-write')
        t['effect_authority'].update(operations=['read-reports','consolidate-reports','write-owned-artifacts'],write_roots=[])

    def admit(self,reports):
        ids=[service.ingest_report(self.store,self.issuer,'reviews-integrator',r)['event'] for r in reports]
        self.classify()
        return ids

    def complete(self,job):
        envelopes=report_scope.conserved_inputs(self.store,job)
        answer=result(category='consolidated'); answer['findings']=[dict(collected_reports=envelopes)]
        self.assertLessEqual(len(encode(answer).encode()),self.config['limits']['max_result_bytes'])
        attempt=self.store.start_job(job['id'],job['token'])
        self.boards['Reviews'].bind_software_attempt(self.store,self.store.job(job['id']),attempt,None)
        collect(self.store,attempt,answer,tool_completion=dict(complete=True,items=[],nonzero_completions=[]))
        response=self.store.finish_job(job['id'],job['token'])
        self.assertEqual(self.store.event(response)['body'],answer)
        return [r['event'] for r in envelopes]

    def test_large_valid_reports_split_complete_and_conserve(self):
        ids=self.admit(self.reports)
        exact=[dict(event=e,sha256=digest(self.store.event(e)),original=self.store.event(e)['body']) for e in ids]
        answer=result(category='consolidated');answer['findings']=[dict(collected_reports=exact)]
        self.assertGreater(len(encode(answer).encode()),262144)
        finished=[]
        for _ in ids:
            job=self.store.reserve();self.assertIsNotNone(job)
            self.assertEqual(len(json.loads(job['members'])),1)
            finished+=self.complete(job)
        self.assertEqual(finished,ids)
        for e,r in zip(ids,self.reports):self.assertEqual(self.store.event(e)['body']['original'],r)

    def test_mixed_distinct_invalid_neighbor_cannot_freeze_valid(self):
        bad=copy.deepcopy(self.reports[1]);bad['history']='Changed unselected whole history'
        ids=self.admit([self.reports[0],bad])
        badrow=self.store.one('SELECT * FROM queue WHERE event=?',(ids[1],))
        self.assertTrue(resource_scopes.blocked(self.store,badrow))
        job=self.store.reserve();self.assertIsNotNone(job)
        self.assertEqual([m['event'] for m in json.loads(job['members'])],[ids[0]])
        self.assertEqual(self.complete(job),[ids[0]])
        self.assertEqual(self.store.one('SELECT state,job FROM queue WHERE event=?',(ids[1],)),dict(state='queued',job=None))
        self.assertEqual(self.store.event(ids[1])['body']['original'],bad)
        self.assertIsNone(self.store.reserve())

    def test_small_all_valid_compose_and_single(self):
        ids=self.admit(self.reports)
        job=self.store.reserve();self.assertEqual(len(json.loads(job['members'])),2)
        self.assertEqual(self.complete(job),ids)

    def test_changed_current_authority_refuses_original_unchanged(self):
        ids=self.admit(self.reports)
        prospective.revoke(self.store,self.issuer,self.epoch['id'])
        self.assertIsNone(self.store.reserve())
        self.assertEqual(self.store.event(ids[0])['body']['original'],self.reports[0])

    def test_single_complete_return_boundary_counts_json_overhead(self):
        # Selected intake limit is unchanged. Actual minimal result includes
        # escaped JSON, envelope, source digest and every required result field.
        r=copy.deepcopy(self.reports[0]);r['reports'][0]['body']='z'
        from coordinator_runtime.report_scope import complete_return
        def envelope(n):
            r['reports'][0]['body']='z'*n
            body=dict(kind='attributed-report',original=r,native_owner_execution=False,
                meaning='Work testimony and whole report input; not persistent Reviews owner collection or native liveness')
            event=dict(id=digest(dict(attributed_report=dict(collector=self.issuer,reference=r['reference']))),role='Reviews',
                recipient=self.config['roles']['Reviews']['owner'],kind='response',author=self.issuer,
                allowed_tasks=['reviews-integrator'],package=None,processing_report=self.cap,body=body)
            return dict(event=event['id'],sha256=digest(event),original=body)
        n=262144-len(encode(complete_return([envelope(0)])).encode())
        self.assertEqual(len(encode(complete_return([envelope(n)])).encode()),262144)
        r['reports'][0]['body']='z'*(n+1)
        before=self.store.one('SELECT COUNT(*) AS n FROM events')['n']
        with self.assertRaisesRegex(Refusal,'complete return'):service.ingest_report(self.store,self.issuer,'reviews-integrator',r)
        self.assertEqual(self.store.one('SELECT COUNT(*) AS n FROM events')['n'],before)
        # Exact boundary intake and complete typed collection both succeed under
        # a genuine new Work policy, selected BEFORE this new receipt intake.
        r['reports'][0]['body']='z'*n
        prospective.revoke(self.store,self.issuer,self.epoch['id'])
        with actor(self.boards['Work'].store,self.issuer):
            processing.revoke(self.store,self.boards,self.cap)
            self.selection['basis']=processing.basis(self.store,self.boards)
            self.selection['service']['legacy_resources']['Reviews']['reviews_report']['reports']=[dict(reference=r['reference'],sha256=digest(r))]
            self.cap=processing.select(self.store,self.boards,self.selection)['capability']
        self.store.processing=processing.Access(self.store,self.cap,self.boards)
        prospective.select(self.store,self.issuer,dict(configuration=digest(self.config),authority='Fictional new exact boundary report choice',
            expires=time.time()+600,processing_capability=self.cap,grants={r:self.store.enrollment(r)['grant_id'] for r in self.config['roles']},
            tasks={t:dict(task_hash=digest(v),software_handoffs={},ordinary_effects=False) for t,v in self.config['tasks'].items()}))
        e=service.ingest_report(self.store,self.issuer,'reviews-integrator',r)['event']
        self.assertEqual(self.store.event(e)['body']['original'],r)
        self.classify();q=self.store.one('SELECT * FROM queue WHERE event=?',(e,))
        self.assertFalse(resource_scopes.blocked(self.store,q))
        job=self.store.reserve();self.assertIsNotNone(job)
        answer=complete_return(report_scope.conserved_inputs(self.store,job))
        self.assertEqual(len(encode(answer).encode()),262144)
        attempt=self.store.start_job(job['id'],job['token'])
        job=self.store.job(job['id'])
        self.boards['Reviews'].bind_software_attempt(self.store,job,attempt,None)
        # Legacy intake remains entitled at the exact ceiling. Even minimum
        # new analysis plus software custody needs additional space; retain
        # this bounded no-copy refusal instead of raising/truncating a budget.
        reports=report_scope.conserved_inputs(self.store,job)
        minimal=result(category='consolidated')
        minimal['findings']=[dict(**report_scope.integration_protocol(self.store,job,reports),
            analysis='x', decision='x', method='x', coverage=[dict(**pin,extent='whole',limits=[])
                for pin in report_scope.source_pins(reports)])]
        with self.assertRaisesRegex(Refusal,'exceed selected result budget'):
            report_scope.validate_result(self.store,job,minimal)
        self.assertTrue(report_scope.fits_return(self.store,reports))
        report_scope.validate_result(self.store,job,answer)
        collect(self.store,attempt,answer,tool_completion=dict(complete=True,items=[],nonzero_completions=[]))
        response=self.store.finish_job(job['id'],job['token'])
        self.assertEqual(self.store.event(response)['body'],answer)
