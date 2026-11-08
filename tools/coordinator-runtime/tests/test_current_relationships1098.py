"""Current1098 counterparts for continuing Future1008/Context1021 obligations.

Decision1074/1093/1098 authority: independently grounded current source, finite
activation/rearm/window progress, direct response birth, frozen custody and
routine staging/backup must work together. Original historical fixtures/results
remain unchanged. This is NOT their original historical transition or acceptance.

The before operand is the actual complete current implementation. The after
operand appends an inert comment to the actual report_repair.py bytes, measured
and retained below. Those edited bytes are NOT executed; source-review approval,
installation identity, principals, clock and old collector facts are fictional
seams. Production source-v1/future guards, transactions and relationship APIs
are executed unchanged. No invented historic hash or source-repair widening.
"""
import copy
import hashlib
import json
from pathlib import Path
from unittest.mock import patch
import unittest
from test_future_software1008 import Future1008, at
from test_budget_context1021 import Context1021
from test_source_continuity688 import Continuity
from test_qa629_repairs import actor
from support import collect
from coordinator_runtime import processing, prospective, service, configuration, windows, processing_admission
from coordinator_runtime import report_repair as repair
from coordinator_runtime.contracts import digest, encode, ident


def current_operands():
    root = Path(processing.__file__).parent
    original = processing.implementation()
    body = (root/'report_repair.py').read_bytes()
    assert original['report_repair.py'] == hashlib.sha256(body).hexdigest()
    changed = body + b'\n# Owned inert current1098 fictional reviewed transition.\n'
    candidate = {**original, 'report_repair.py': hashlib.sha256(changed).hexdigest()}
    return dict(original=original, candidate=candidate, changed=changed)


def retain_operands(area, pins):
    path = area/'current1098-report_repair.py'
    path.write_bytes(pins.pop('changed'))
    assert hashlib.sha256(path.read_bytes()).hexdigest() == pins['candidate']['report_repair.py']
    (area/'CURRENT-SOURCE-OPERANDS.json').write_text(encode(dict(**pins,
        candidate_operand=str(path), premise='Current measured before/owned after; NOT historic release',
        seam='Edited comment operand not executed; semantic source approval and installation fictional')))


processing_select = processing.select


class CurrentSetup1098:
    def setUp(self):
        pins = current_operands()
        self.bootstrap(self.configure)
        retain_operands(self.area, pins)
        self.store.clock=lambda:at('07:30:00')
        self.issuer=self.config['roles']['Work']['owner']
        self.enterContext(patch.object(processing,'implementation',return_value=pins['original']))
        self.report=dict(reference='fictional-original-QA-report1008',collector=self.issuer,actual_END=0,
            reports=[dict(name='QA',body='Whole fictional QA report and dissent; original duties retained')],
            history='Whole fictional original collector history',method_pin='fictional public reviewed method',
            coverage=dict(status='PARTIAL',unread=['actual native Source']),effects='known-report-only')
        policy=dict(version='reviews-report-v1',authority='Original fictional framework report right',expires=at('10:44:25'),
            task='reviews-integrator',task_sha256=digest(self.config['tasks']['reviews-integrator']),
            reports=[dict(reference=self.report['reference'],sha256=digest(self.report)),
                dict(reference='another-future-report',sha256=digest({**self.report,'reference':'another-future-report'}))])
        with patch.object(processing, 'select', side_effect=self.select_current):
            self.select(dict(max_inflight=4,reviews={},report_tasks=['reviews-integrator'],
                admission=dict(until=at('07:43:35'),pause_bytes=90000000,max_new_inputs=20),
                legacy_resources={'Reviews':dict(original_hold=None,roots=[],unbounded=True,
                    evidence='Original unresolved report custody',reviews_report=policy)}))
        self.epoch=prospective.select(self.store,self.issuer,dict(configuration=digest(self.config),
            authority='Original fictional prospective authority',expires=at('10:44:25'),processing_capability=self.cap,
            grants={r:self.store.enrollment(r)['grant_id'] for r in self.config['roles']},
            tasks={t:dict(task_hash=digest(v),software_handoffs={},ordinary_effects=False) for t,v in self.config['tasks'].items()}))
        # A real reserved/failed original Source job remains held. Its partial
        # CLI transport is an explicit fixture seam, not native terminal proof.
        self.source_event=self.post('Reviews','reviews-proposer',None)
        self.source_job=self.store.reserve();self.assertIsNotNone(self.source_job)
        self.assertEqual(self.source_job['task'],'reviews-proposer')
        source_attempt=self.store.start_job(self.source_job['id'],self.source_job['token'])
        collect(self.store,source_attempt,None,code=6,capture='incomplete',error='Fictional incomplete original Source capture')
        self.assertIsNone(self.store.finish_job(self.source_job['id'],self.source_job['token']))
        self.assertEqual(self.store.job(self.source_job['id'])['state'],'held')
        self.classify()
        self.pending_work=self.post('Work','work-proposer',None)
        self.board_source=self.post('QA','qa-execution','fictional-original-package')
        processing_admission.admit(self.store,self.board_source['id'])
        self.report_id=service.ingest_report(self.store,self.issuer,'reviews-integrator',self.report)['event']
        self.classify();self.events=sorted([self.board_source['id'],self.report_id])
        self.controller=self.store.controller
        self.store.db.execute('INSERT INTO processing_runs VALUES(?,?,?,?)',(self.controller,self.cap,'owned',self.store.clock()))
        self.store.db.execute('INSERT INTO service_runs VALUES(?,?,?,?,?,?,?)',
            (self.controller,self.cap,'fictional-unused','returned-awaiting-parent-END',self.store.clock(),self.store.clock(),'Fictional service return'))
        with actor(self.boards['Work'].store,self.issuer):
            processing.release(self.store,self.boards,self.cap,self.controller,dict(actual_END=0,evidence=['Fictional original parent END0']))
        self.original_impl=pins['original'];self.new_impl=pins['candidate']
        self.modules=sorted(n for n in self.new_impl if self.new_impl[n] != self.original_impl[n])
        self.assertLessEqual(set(self.modules),repair.SOURCE_MODULES)
        self.assertEqual(self.new_impl['reviews.py'],self.original_impl['reviews.py'])
        root='/fictional-same-installed-public-release';prefix=root+'/tools/coordinator-runtime/coordinator_runtime/'
        self.old_release=dict(root=root,pool_control=self.store.execution_pool.pool.control_binding(Path(self.config['execution_pool_routes']).read_bytes()),
            files={prefix+n:h for n,h in self.original_impl.items()})
        self.new_release=copy.deepcopy(self.old_release)
        for name in self.modules:self.new_release['files'][prefix+name]=self.new_impl[name]
        raw=json.loads(self.store.one('SELECT selection FROM processing_capabilities')['selection'])
        transition=dict(basis=dict(release=self.old_release,tasks=self.config['tasks'],
            processing=dict(roles={r:dict(original=dict(binding=v['original']['binding'])) for r,v in raw['basis']['roles'].items()})),
            event_boundary=0,jobs=[],outboxes=[],alert_boundary=0)
        self.store.db.execute('INSERT INTO configuration_transitions(previous,current,original,configuration,selection,issuer,created) VALUES(?,?,?,?,?,?,?)',
            ('fictional-previous',digest(self.config),digest(self.config),encode(self.config),encode(transition),self.issuer,self.store.clock()))
        self.enterContext(patch.object(configuration,'release',return_value=self.new_release))
        self.enterContext(patch.object(processing,'implementation',return_value=self.new_impl))
        # Actual source-v1 APIs establish the exact reviewed pins first. No
        # historical producer/control pair exists or is constructed.
        self.source_request = Continuity.request(self)
        self.source_receipt = Continuity.apply(self,self.source_request)
        # Original 34 charged windows: real charge/append APIs, not rewritten
        # authority or new journal. Retain every used row and original hash.
        with self.store.tx():
            self.charge_original_windows()
        self.assertEqual(self.store.one('SELECT COUNT(*) n FROM service_window_allocations')['n'],34)
        self.now = at('08:15:00'); self.store.clock = lambda:self.now
        self.store.controller = ident()
        self.plan = dict(**{'from':self.now},until=at('10:30:00'),lease_seconds=1800,max_starts=512,
            max_new_inputs=8192,max_windows=35,pause_bytes=1056964608)
        self.plan_file=self.area/'future-plan.json';self.plan_file.write_text(encode(self.plan))
        self.before=self.untouched()
        self.windows_before=self.store.rows('SELECT * FROM service_windows')
        self.allocations_before=self.store.rows('SELECT * FROM service_window_allocations')


    def select_current(self, runtime, boards, selection):
        selection['software_admission'] = dict(authority='Fictional current QA admission',max_packages=2,
            scopes=dict(fixture=dict(submitters=[self.source_sender],package_prefix='fictional-',
                task_scopes={'qa-execution':self.scope},evidence='Fictional current QA scope')))
        return processing_select(runtime, boards, selection)

    def charge_original_windows(self):
        for _ in range(34*40+1):
            windows.charge(self.store, 'events', new_input=True)


class FutureCurrent1098(CurrentSetup1098, Future1008):
    """All original future behavior assertions, on current byte-backed operands."""


class ContextCurrent1098(CurrentSetup1098, Context1021):
    """All joint context assertions, on current byte-backed operands."""


def load_tests(loader, tests, pattern):
    future = (FutureCurrent1098(name) for name in Future1008.__dict__ if name.startswith('test_'))
    context = (ContextCurrent1098(name) for name in Context1021.__dict__ if name.startswith('test_'))
    return unittest.TestSuite([*future, *context])
