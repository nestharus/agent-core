"""Contained source-method controls; no stock fixtures, provider or real owner.

Run directly under the caller's positive read-only source/dependency namespace.
Only --fixture-root is writable. Pool allocations, results, owners, clocks and
artifact witnesses are explicitly fictional. AST extraction avoids importing
Store's pool/Board/publication controllers or any transitive stock fixtures.
"""
import argparse
import ast
from contextlib import contextmanager
import copy
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import sys
import time
import types
import unittest

SOURCE = Path(__file__).resolve().parents[1] / 'coordinator_runtime'
parser = argparse.ArgumentParser()
parser.add_argument('--fixture-root', type=Path, required=True)
parser.add_argument('--selected-config', type=Path)
args = parser.parse_args()
FIXTURES = args.fixture_root
FIXTURES.mkdir(exist_ok=True)
# Fail before candidate imports unless source, its test/controller and system
# dependencies really are on kernel read-only mounts. /fixture is the caller's
# only persistent writable bind; no HOME/account/session substitution is used.
containment = {str(p): bool(os.statvfs(p).f_flag & os.ST_RDONLY)
               for p in (SOURCE, Path(__file__), Path('/usr'), FIXTURES)}
if not all(containment[str(p)] for p in (SOURCE, Path(__file__), Path('/usr'))) or containment[str(FIXTURES)]:
    raise RuntimeError('positive read-only source/controller/dependency mounts and own writable fixtures required')
(FIXTURES/'containment.json').write_text(json.dumps({
    'kernel_readonly': containment, 'pid_in_private_namespace': os.getpid(),
    'network_namespace': os.readlink('/proc/self/ns/net'),
    'pid_namespace': os.readlink('/proc/self/ns/pid'),
    'mount_namespace': os.readlink('/proc/self/ns/mnt'),
    'scope': 'caller unshare-all/private proc/dev; only inspected candidate modules imported'}))
package = types.ModuleType('coordinator_runtime')
package.__path__ = [str(SOURCE)]
sys.modules['coordinator_runtime'] = package


def load(name):
    spec = importlib.util.spec_from_file_location('coordinator_runtime.' + name, SOURCE / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    setattr(package, name, module)
    return module


contracts = load('contracts')
admitted = load('admitted')
inputs = load('inputs')
recovery = load('recovery')
capacity = load('capacity')
progress = load('progress')
Refusal, Backpressure = contracts.Refusal, contracts.Backpressure
encode, digest, ident = contracts.encode, contracts.digest, contracts.ident


def tree(name):
    return ast.parse((SOURCE / (name + '.py')).read_text())


def schema(name):
    return next(ast.literal_eval(n.value) for n in tree(name).body if isinstance(n, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == 'SCHEMA' for t in n.targets))


def source_class(name, class_name, namespace, omit=()):
    node = next(n for n in tree(name).body if isinstance(n, ast.ClassDef) and n.name == class_name)
    node.body = [n for n in node.body if not isinstance(n, ast.FunctionDef) or n.name not in omit]
    exec(compile(ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[])), str(SOURCE / (name+'.py')), 'exec'), namespace)
    return namespace[class_name]


# No artifacts are declared in these controls. This is not custody qualification.
ns = {**vars(contracts), 'json': json, 'capacity': capacity, 'admitted': admitted,
      'contextmanager': contextmanager, 'witnesses': lambda store, attempt: [],
      'RecoveryJournal': recovery.RecoveryJournal, 'InputJournal': inputs.InputJournal,
      'CONTROL_ROUTES': inputs.CONTROL_ROUTES}
Delivery = source_class('delivery', 'DeliveryJournal', ns)
ns['DeliveryJournal'] = Delivery
Base = source_class('store', 'Store', ns, omit=('__init__', 'usage'))


class FictionalPool:
    def allocate(self):
        return {'profile': 'fictional-local-no-account'}


class FixtureStore(Base):
    sequence = 0

    def __init__(self, corrections=1, caps=None):
        FixtureStore.sequence += 1
        self.directory = FIXTURES / ('case-%03d' % FixtureStore.sequence)
        self.directory.mkdir()
        self.db = sqlite3.connect(self.directory / 'fictional.sqlite3', isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA temp_store=MEMORY")
        self.trace = open(self.directory / 'sql.trace', 'x')
        self.db.set_trace_callback(lambda statement: self.trace.write(statement+'\n'))
        for name in ('store', 'delivery', 'recovery', 'inputs', 'admitted', 'capacity', 'publication', 'custody'):
            self.db.executescript(schema(name))
        self.controller = 'fictional-controller'
        self.now = 100000.
        self.clock = lambda: self.now
        self.execution_pool = FictionalPool()
        self.config = {
            'actor': 'fictional-producer', 'profiles': ['fictional-local-no-account'],
            'roles': {r: {'owner': 'fictional-'+r, 'routes': ['terminal'] if r == 'Work' else []} for r in ('Work','Branch','Reviews','QA')},
            'tasks': {'terminal': {'role': 'Work', 'phase': 'proposer', 'effects': 'none',
                                  'binding': contracts.SOL, 'profile': 'fictional-local-no-account',
                                  'delivery_required': True, 'allowed_handoffs': ['Branch']}},
            'finite_service': {'tasks': ['terminal'], 'max_admitted': 2},
            'classifier': {'binding': contracts.LUNA, 'profile': 'fictional-local-no-account'},
            'diagnosis': {'binding': contracts.LUNA, 'profile': 'fictional-local-no-account'},
            'deadlines': {'alert_interval': 10},
            'limits': {'max_owner_corrections': corrections, 'max_events': 100000,
                       'max_jobs': 10000, 'max_attempts': 100000, 'max_outboxes': 10000,
                       'max_alerts': 100, 'max_bytes': 64*1024*1024, 'max_result_bytes': 262144},
            'delivery': {'recipients': {r: {'session': 'fictional-'+r} for r in ('Work','Branch','Reviews','QA')}}}
        if caps: self.config['limits'].update(caps)
        for r in self.config['roles']:
            self.db.execute('INSERT INTO enrollments VALUES(?,?,?,?,1,1,NULL,NULL)',
                            (r, 'fictional-'+r, 'fictional-local-no-account', 'fictional-grant'))
            self.db.execute('INSERT INTO cursors VALUES(?,0)', (r,))
        self.db.execute("INSERT INTO meta VALUES('configuration',?)", (digest(self.config),))
        self.violations = lambda: [{'subject': 'fictional-unchanged', 'kind': 'fictional-violation'}]

    def usage(self):
        # Deliberately unmeasured physical resources; only row charging is tested.
        return {**{k: self.db.execute('SELECT COUNT(*) FROM '+k).fetchone()[0]
                   for k in ('events','jobs','attempts','outboxes','alerts')}, 'bytes': 0}

    def close(self):
        self.directory.joinpath('before-close.sql').write_text('\n'.join(self.db.iterdump()))
        self.directory.joinpath('config.json').write_text(encode(self.config))
        self.directory.joinpath('usage.json').write_text(encode(self.usage()))
        self.db.close()
        self.trace.close()

    def collect_fiction(self, attempt, result, exit=0, detail=None):
        self.collect(attempt, {'exit': exit, 'result': result, 'capture': 'complete',
                              'cleanup': 'retained-fictional', 'detail': detail or {}})

    def incoming(self, suffix='one'):
        return {'id': 'fictional-'+suffix, 'role': 'Work', 'recipient': 'fictional-Work',
                'kind': 'board', 'package': None, 'allowed_tasks': ['terminal'], 'body': 'fictional-input'}

    def classify(self, event, task):
        attempt, routed = self.claim_classification()
        assert routed['id'] == event
        self.collect_fiction(attempt, {'event_id': event, 'task': task, 'package': None, 'reason': 'fictional source control'})
        self.commit_classification(attempt)
        return attempt

    def resolve(self, event, task, ordinal):
        self.resolve_input(event, 'fictional-Work', {'source_hash': digest(self.event(event)),
            'mode': 'route', 'task': task, 'package': None, 'related_event': None,
            'related_job': None, 'reason': 'fictional owner choice '+str(ordinal),
            'evidence': ['fictional only'], 'remaining_obligations': []})

    def controls_then_route(self, event, task):
        c = self.config['limits']['max_owner_corrections']
        self.classify(event, '@unresolved')
        for i in range(c):
            self.resolve(event, task, i)
            self.classify(event, task if i == c-1 else '@unresolved')


class Controls(unittest.TestCase):
    def store(self, *a, **kw):
        s = FixtureStore(*a, **kw)
        self.addCleanup(s.close)
        return s

    def test_s69_owed_55_and_combined_disposition(self):
        # Exact adverse pattern: 1 initial + 3*17 task + 3 outgoing input questions.
        # Extended with a separately keyed diagnosis owner-disposition tail.
        s = self.store()
        event = s.incoming()
        s.ingest(event, cursor=1)
        s.controls_then_route(event['id'], 'terminal')
        job = s.reserve()
        for index in range(3):
            with s.tx():
                attempt = s._attempt('task', None, job['id'], contracts.SOL, 'fictional-local-no-account')
                s.db.execute("UPDATE jobs SET active_attempt=?,state='running',effects='none' WHERE id=?", (attempt,job['id']))
            result = {'semantic': 'PARTIAL', 'category': 'blocker', 'summary': 'fictional failure',
                      'findings': [], 'failures': ['fictional'], 'unknowns': [], 'artifacts': [],
                      'handoffs': [{'recipient': 'Branch', 'kind': 'question', 'text': 'fictional '+str(i),
                                    'ref': None, 'required': 'settled'} for i in range(16)]}
            s.collect_fiction(attempt, result, detail={'resume_disposition': 'fictional no native resume'})
            with s.tx():
                response = s.failure_delivery(s.job(job['id']), s.attempt(attempt), s.config['tasks']['terminal'], 'fictional partial')
            if index == 2: self.assertEqual(s.usage()['outboxes'], 54)
            s.controls_then_route(response, '@delivery')
        self.assertEqual(s.usage()['outboxes'], 55)
        # Maximum task sequence above is an allocation/charging witness, not a
        # claim of recovery ordering/provider feasibility. Separate diagnosis
        # allocation below deliberately combines all locally counted producers.
        with s.tx():
            s.db.execute("UPDATE jobs SET state='held',recovery_owner=?,recovery_state='claimed' WHERE id=?", (s.controller,job['id']))
        diag = s.diagnosis_attempt(job['id'])
        s.collect_fiction(diag, {'profile': '@owner', 'remaining': 'fictional decision', 'rationale': 'fictional diagnosis'})
        with s.tx():
            s.retain_recovery_disposition(s.job(job['id']), s.attempt(diag), 'fictional owner disposition')
        response = s.job(job['id'])['response']
        s.controls_then_route(response, '@delivery')
        self.assertEqual(s.usage()['outboxes'], 57)
        self.assertEqual(len(s.rows('SELECT * FROM recovery_dispositions')), 1)
        self.assertTrue(s.rows('SELECT * FROM results WHERE result LIKE ?', ('%fictional failure%',)))

    def test_decomposed_complete_reservation(self):
        for c in (1,4,8):
            s = self.store(c)
            p = admitted.plan(s.config)
            task_rows = 18*(c+2)
            diagnosis_rows = c+1
            events = 1+task_rows+diagnosis_rows
            self.assertEqual(p, {'events': events, 'jobs': 1,
                'attempts': (c+2)*events+(c+2)+(c+1),
                'outboxes': task_rows+diagnosis_rows+(c+1)*events})

    def test_recovery_order_with_final_owner_disposition_and_input_controls(self):
        s = self.store()
        e = s.incoming();s.ingest(e)
        s.controls_then_route(e['id'], 'terminal')
        job = s.reserve()
        attempt = s.start_job(job['id'], job['token'])
        result = {'semantic': 'PARTIAL', 'category': 'blocker', 'summary': 'fictional partial',
                  'findings': [], 'failures': ['fictional'], 'unknowns': [], 'artifacts': [],
                  'handoffs': [{'recipient': 'Branch', 'kind': 'question', 'text': 'fictional '+str(i),
                               'ref': None, 'required': 'settled'} for i in range(16)]}
        for index in range(2):
            s.collect_fiction(attempt, result, detail={'resume_disposition': 'fictional native resume unavailable'})
            # Only this fixture's no-effect task is reconciled; no actual effect.
            s.db.execute("UPDATE jobs SET effects='none' WHERE id=?", (job['id'],))
            s.finish_job(job['id'], job['token'])
            s.controls_then_route(s.job(job['id'])['response'], '@delivery')
            if index == 0:
                self.assertIsNotNone(s.claim_recovery(job['id']))
            else:
                request = s.request_recovery(job['id'], job['token'], attempt, 'fictional-Work',
                    {'mode': 'remaining-work', 'reason': 'fictional authentic remaining target',
                     'evidence': ['fictional'], 'remaining': 'fictional remaining work and why'})
                s.consume_recovery_request(request['id'])
            diag = s.diagnosis_attempt(job['id'])
            s.collect_fiction(diag, {'profile': 'fictional-local-no-account' if index == 0 else '@owner',
                                    'remaining': 'fictional remaining', 'rationale': 'fictional rationale'})
            if index == 0:
                attempt = s.handoff(job['id'],diag)
            else:
                with s.tx(): s.finish_invalid_diagnosis(s.job(job['id']))
                s.controls_then_route(s.job(job['id'])['response'], '@delivery')
        self.assertEqual(s.job(job['id'])['recovery_state'], 'awaiting-disposition')
        self.assertEqual(s.usage()['outboxes'], 39)  # 1 + 2*17 + 2 controls + disposition + control
        self.assertEqual(len(s.rows('SELECT * FROM recovery_dispositions')), 1)
        self.assertEqual(len(s.rows("SELECT * FROM attempts WHERE kind='task'")), 2)
        self.assertEqual(len(s.rows("SELECT * FROM attempts WHERE job IS NOT NULL AND kind='diagnosis'")), 2)
        before = s.rows('SELECT * FROM results')
        with self.assertRaises(Refusal):
            s.request_recovery(job['id'],job['token'],attempt,'fictional-Work',
                {'mode':'defer','reason':'fictional exhausted owner budget','evidence':['fictional'],'remaining':None})
        self.assertEqual(s.rows('SELECT * FROM results'),before)

    def test_saturate_count_envelope_with_classifier_recovery_and_all_producers(self):
        # Deliberately synthetic joint maxima, stronger than a single feasible
        # task ordering: exercise every reserved credit at the exact count caps.
        # This is row conservation, not a provider/workflow completion witness.
        s = self.store()
        p = admitted.plan(s.config)
        for kind, n in p.items(): s.config['limits']['max_'+kind] = n
        e = s.incoming();s.ingest(e)
        members = [{'event':e['id'],'hash':digest(e),'package':None}]
        with s.tx():
            s.budget('jobs', event=e['id'])
            s.db.execute('INSERT INTO jobs(id,role,phase,task,members,controller,token,created) VALUES(?,?,?,?,?,?,?,?)',
                         ('synthetic-job','Work','proposer','terminal',encode(members),s.controller,'fictional-token',s.now))
            ids = [s._attempt('task',None,'synthetic-job',contracts.SOL,'fictional-local-no-account') for _ in range(3)]
            for _ in range(2): s._attempt('diagnosis',None,'synthetic-job',contracts.LUNA,'fictional-local-no-account')
        def control_all(event):
            attempt,routed = s.claim_classification()
            self.assertEqual(routed['id'],event)
            s.collect_fiction(attempt,None,exit=1)
            s.classification_failed(attempt,'fictional failed classifier')
            attempt,routed = s.claim_classification_recovery()
            s.collect_fiction(attempt,{'event_id':event,'task':'@unresolved','package':None,'reason':'fictional recovery'})
            s.commit_classification(attempt)
            s.resolve(event,'terminal' if event == e['id'] else '@delivery',0)
            s.classify(event,'@unresolved')
        control_all(e['id'])
        for i in range(56):  # 18*3 task deliveries + two diagnosis dispositions
            with s.tx():
                s._outbox('Work','Branch','question',{'fictional':i},job='synthetic-job',key='job-row-'+str(i))
                event = s.gate_result_delivery(s.job('synthetic-job'),s.attempt(ids[0]),{'fictional':True})
            control_all(event)
        self.assertEqual({k:s.usage()[k] for k in admitted.KINDS},p)
        self.assertEqual(admitted.reserved(s),dict.fromkeys(admitted.KINDS,0))
        before = s.rows('SELECT * FROM duty_accounts')
        with self.assertRaises(Backpressure):
            with s.tx(): s._outbox('Work','Work','question',{'fictional':'extra'},event=e['id'])
        self.assertEqual(s.rows('SELECT * FROM duty_accounts'),before)

    def test_static_correspondence_preserves_policy_and_role_choice_fences(self):
        s = self.store()
        original = copy.deepcopy(s.config)
        report = admitted.correspondence(s.config)
        self.assertTrue(report['roles']['Work']['finite_intake_supported'])
        self.assertEqual(s.config,original)
        for key,value,reason in [('responses',{'proposal':['terminal']},'responses'),
                                 ('phase','integrator','batched integrator'),
                                 ('execution','owner','external owner execution/return'),
                                 ('effects','owned-artifacts','effects beyond terminal no-effect execution'),
                                 ('require_package_scope',True,'require_package_scope')]:
            c = copy.deepcopy(original);c['tasks']['terminal'][key] = value
            self.assertIn(reason,admitted.correspondence(c)['tasks']['terminal']['exclusions'])
            with self.assertRaises(Refusal): admitted.policy(c)
        s.config['tasks']['foreign'] = {**s.config['tasks']['terminal'],'role':'Branch'}
        s.config['roles']['Work']['routes'].append('foreign')
        s.config['finite_service']['tasks'].append('foreign')
        self.assertFalse(admitted.correspondence(s.config)['roles']['Work']['finite_intake_supported'])
        e = s.incoming();e.pop('allowed_tasks')
        with self.assertRaises(Refusal): s.ingest(e)
        self.assertEqual(s.usage()['events'],0)

    def test_selected_configuration_static_correspondence_only(self):
        if args.selected_config is None:
            self.skipTest('no actual public configuration selected for static mapping')
        config = json.loads(args.selected_config.read_text())
        before = copy.deepcopy(config)
        report = admitted.correspondence(config)
        self.assertEqual(config,before)
        self.assertEqual(set(report['tasks']),set(config['tasks']))
        (FIXTURES/'selected-task-correspondence.json').write_text(json.dumps(report,indent=2))

    def test_exact_cap_admission_rollback_and_competing_producer(self):
        s = self.store()
        p = admitted.plan(s.config)
        for kind, n in p.items(): s.config['limits']['max_'+kind] = n
        s.ingest(s.incoming(), cursor=1)
        account = s.rows('SELECT * FROM duty_accounts')
        with self.assertRaises(Backpressure):
            with s.tx(): s._outbox('Work','Work','question',{'fictional':'unowned'})
        with self.assertRaises(Backpressure): s.ingest(s.incoming('two'), cursor=2)
        self.assertEqual(s.one("SELECT seq FROM cursors WHERE role='Work'")['seq'], 1)
        self.assertEqual(s.rows('SELECT * FROM duty_accounts'), account)
        before = admitted.reserved(s)
        with self.assertRaisesRegex(RuntimeError, 'fictional rollback'):
            with s.tx():
                s._outbox('Work','Work','question',{'fictional':'owned'},event='fictional-one')
                raise RuntimeError('fictional rollback')
        self.assertEqual(admitted.reserved(s), before)
        self.assertEqual(s.usage()['outboxes'], 0)
        with s.tx(): s._outbox('Work','Work','question',{'fictional':'owned'},event='fictional-one', key='once')
        remaining = admitted.reserved(s)
        with s.tx(): s._outbox('Work','Work','question',{'fictional':'owned'},event='fictional-one', key='once')
        self.assertEqual(admitted.reserved(s), remaining)

    def test_lifetime_not_recycled_by_ack_processing_age(self):
        s = self.store()
        s.config['finite_service']['max_admitted'] = 1
        s.ingest(s.incoming(), cursor=1)
        s.db.execute("UPDATE events SET processed_at=?,ack='done',state='processed'", (s.now,))
        s.now += 1000000
        with self.assertRaises(Backpressure): s.ingest(s.incoming('late'), cursor=2)
        self.assertEqual(s.usage()['events'], 1)
        self.assertEqual(len(s.rows('SELECT * FROM duty_accounts')), 1)

    def test_old_unaccounted_source_not_retrofitted(self):
        s = self.store()
        original = s.incoming('legacy')
        s.db.execute('INSERT INTO events(id,role,payload,hash,received) VALUES(?,?,?,?,?)',
                     (original['id'],'Work',encode(original),digest(original),s.now))
        with self.assertRaises(Backpressure): s.ingest(s.incoming(), cursor=1)
        self.assertEqual(s.event(original['id']), original)
        self.assertEqual(s.rows('SELECT * FROM duty_accounts'), [])

    def test_input_control_full_owner_decision_tail(self):
        for c in (1,4,8):
            s = self.store(c)
            e = s.incoming();s.ingest(e)
            s.classify(e['id'], '@unresolved')
            for i in range(c):
                s.resolve(e['id'], 'terminal', i)
                s.classify(e['id'], '@unresolved')
            self.assertEqual(s.usage()['outboxes'], c+1)
            original = s.event(e['id'])
            with self.assertRaises(Refusal): s.resolve(e['id'], 'terminal', c)
            self.assertEqual(s.event(e['id']), original)

    def test_unchanged_occurrences_pressure_and_late_unknown_preserved(self):
        s = self.store()
        first = capacity.capture(s)
        s.now += 10
        second = capacity.capture(s)
        self.assertNotEqual(first[0]['id'],second[0]['id'])
        s.config['limits']['max_alerts'] = 2
        s.now += 10
        self.assertEqual(capacity.capture(s), [])
        gap = capacity.service(s)
        self.assertEqual(gap['unrepresented'], 1)
        s.config['limits']['max_alerts'] = 100
        s.now += 30
        capacity.capture(s)
        later = capacity.service(s)
        self.assertEqual(later['gap_since'], gap['gap_since'])
        self.assertEqual(later['scope'], gap['scope'])
        self.assertEqual(later['unrepresented'], 1)
        self.assertIn('historical population unknown', later['reason'])
        self.assertEqual(s.usage()['alerts'], 3)

    def test_missing_custodian_keeps_source_and_gap(self):
        s = self.store()
        capacity.capture(s);capacity.deliver_pending(s)
        before = s.rows('SELECT * FROM alerts')
        result = progress.step(s,{})
        self.assertEqual(result['visited'], 1)
        self.assertEqual(result['retired'], 0)
        self.assertIsNotNone(result['first_gap'])
        self.assertEqual(s.rows('SELECT * FROM alerts'),before)


if __name__ == '__main__':
    unittest.main(argv=[sys.argv[0]], verbosity=2)
