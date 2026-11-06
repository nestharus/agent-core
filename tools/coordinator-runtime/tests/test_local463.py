"""Bounded R24/25/26 controls; run in a private positive-mount bwrap.

Native contexts, principals, tool/model collection and Board transport are OWNED
fiction. Production runtime schemas/selection/provenance/native-reader gates run;
no native consent, method execution or whole processing is established.
"""
import copy
import json
import unittest
from pathlib import Path

from support import result
from test_local457 import OriginalFlow, FieldPresence
from test_local450 import no_native_material
from coordinator_runtime import local_native, processing, prospective, reviews
from coordinator_runtime import local_integration as local
from coordinator_runtime.contracts import Refusal, digest, encode


class DiscoveryPresence(unittest.TestCase):
    versions = FieldPresence.versions
    enqueue = FieldPresence.enqueue
    prepare = FieldPresence.prepare
    finish = FieldPresence.finish
    reopen = FieldPresence.reopen
    def setUp(self):
        FieldPresence.setUp(self)
        self.config['canonical_publication']['library'] = '/sdk'
        self.reopen()

    def definition(self, path):
        point = copy.deepcopy(self.config['local_integration']['points']['a'])
        point['bindings'][0]['path'] = path
        return point

    def discovery(self, path, mutate, refused):
        before = {str(p):p.read_bytes() for p in self.peers+[self.log]}
        pair = self.prepare(self.enqueue(discovery=True))
        def finish():
            return self.finish(*pair, mutate=mutate,
                completion_extra={'discovered_points':{'new:463':self.definition(path)}})
        if refused:
            with self.assertRaises(Refusal): finish()
            self.assertEqual({str(p):p.read_bytes() for p in self.peers+[self.log]}, before)
            self.assertEqual(self.store.rows('SELECT * FROM file_publications'), [])
            self.assertEqual(self.store.rows('SELECT * FROM local_discovered_points'), [])
            self.assertEqual(self.store.rows('SELECT * FROM local_commits'), [])
        else:
            self.assertTrue(finish())
            self.assertEqual(len(self.store.rows('SELECT * FROM file_publications')), 7)
            self.assertEqual([r['point'] for r in self.store.rows('SELECT * FROM local_discovered_points')], ['new:463'])

    def test_missing_final_key_refuses_before_effects(self):
        self.discovery(['missing-463'], lambda d:None, True)

    def test_missing_stable_selector_refuses_before_effects(self):
        self.discovery(['items',{'field':'id','value':'ghost-463'}], lambda d:None, True)

    def test_ambiguous_created_selector_refuses_before_effects(self):
        self.discovery(['items',{'field':'id','value':'new-463'}],
                       lambda d:d['items'].extend([{'id':'new-463','owner':None}]*2), True)

    def test_created_member_is_registered_and_anchored(self):
        self.discovery(['items',{'field':'id','value':'new-463'}],
                       lambda d:d['items'].append({'id':'new-463','owner':None,'state':'new'}), False)
        item = next(x for x in json.loads(self.catalog.read_text())['items'] if x['id']=='new-463')
        self.assertIsNone(item['owner']); self.assertEqual(item['state'], 'new')
        receipt = json.loads(self.store.one('SELECT receipt FROM local_commits')['receipt'])
        self.assertEqual(list(receipt['continuations']), ['new:463'])

    def test_anchored_absence_predicate_remains_valid(self):
        point = self.definition(['optional-463']); point.update(protected=[], writable=[])
        self.config['local_integration']['points']['absence'] = point
        for task in self.config['local_integration']['tasks'].values(): task['points'].append('absence')
        # Fresh owned journal for this final fixture configuration.
        self.config['state_dir'] = str(self.area/'absence-state')
        from support import enrolled
        self.store.close(); self.store = enrolled(self.config); self.addCleanup(self.store.close)
        pair = self.prepare(self.enqueue(reads=['absence']))
        self.assertTrue(self.finish(*pair))
        self.assertNotIn('optional-463', json.loads(self.catalog.read_text()))


class OriginalHelpers:
    # Reuse fixture operations, without exposing inherited test methods to
    # unittest discovery under these deliberately different configurations.
    authority = OriginalFlow.authority
    boards = OriginalFlow.boards
    fixture_configuration = OriginalFlow.fixture_configuration
    configure = OriginalFlow.configure
    repository = OriginalFlow.repository
    classify = OriginalFlow.classify
    source = OriginalFlow.source
    start = OriginalFlow.start
    graph = OriginalFlow.graph


class MixedComponents(OriginalHelpers, unittest.TestCase):
    def setUp(self):
        OriginalFlow.setUp(self)
        selection = self.runtime.processing.current()[1]
        processing.revoke(self.runtime, self.selected_boards, self.key)
        policy = selection['service']['reviews']['rp']
        policy['components']['other'] = copy.deepcopy(policy['components']['component'])
        policy['components']['other']['history'] = str(self.runtime.home/'review-history'/'other.md')
        selection['basis'] = processing.basis(self.runtime, self.selected_boards)
        self.key = processing.select(self.runtime, self.selected_boards, selection)['capability']
        self.runtime.processing = processing.Access(self.runtime, self.key, self.selected_boards)
        self.runtime.db.execute('UPDATE review_contexts SET capability=?', (self.key,))
        self.runtime.db.execute('INSERT INTO review_contexts VALUES(?,?,?,?,?,?,?,?,?,?,?,NULL)',
            ('other', self.key, '.codex', 'fictional-route', 'fictional-other-handle', 'fictional-other-run',
             self.runtime.controller, 'live', 'fictional-head', 'fictional-history', 1000.))

    def source(self, name='original', package='package'):
        event = {'id':name, 'role':'Reviews', 'recipient':'fictional-logical-Reviews', 'kind':'board', 'post':11,
                 'author':'fictional-author', 'body':{'review':{'component':'other' if name == 'second-original' else 'component'}},
                 'package':package, 'allowed_tasks':['rp']}
        self.runtime.ingest(event); self.classify(event, 'rp')
        return event

    def finish(self, job, attempt, answer):
        if job['task'] == 'rp':
            component = self.runtime.event(json.loads(job['members'])[0]['event'])['body']['review']['component']
            answer = reviews.proposal_result(
                {'semantic':'DONE', 'summary':'fictional report '+component+'; dissent: contrary evidence retained; coverage PARTIAL',
                 'dissent':['fictional retained contrary evidence '+component], 'coverage':'PARTIAL'},
                component, {'original':'fictional material '+component}, self.runtime.controller, attempt,
                [{'fictional':'original turn '+component}])
        return OriginalFlow.finish(self, job, attempt, answer)

    def mixed_job(self, discovery=True):
        returned, proposals, integrator = self.graph(multiple=True, discovery=discovery)
        self.assertEqual(len(json.loads(integrator['members'])), 2)
        self.assertEqual(len(local_native.original_review_jobs(self.runtime, integrator, set())), 2)
        # Both full original reports (including dissent/partial coverage) remain
        # in their collected source results, independently of the selected lens.
        for proposal in proposals:
            self.assertIn('dissent', encode(proposal['body']))
            self.assertIn('PARTIAL', encode(proposal['body']))
        job, attempt = self.start(returned, 'wp')
        proposals.sort(key=lambda p: 'second-original' in [m['event'] for m in p['source_members']])
        return job, attempt, proposals, integrator

    def test_mixed_discovery_and_both_component_lenses_survive_Work_continuation(self):
        job, attempt, proposals, _ = self.mixed_job()
        for turn in range(2):
            for component, run in [('component','fictional-original-run'), ('other','fictional-other-run')]:
                value, resources = local_native.snapshot(self.runtime, {'native':'review','component':component}, job)
                self.assertEqual(value['context']['run'], run)
                self.assertIn('native-session:'+run, resources)
            self.assertEqual(len(local_native.original_review_jobs(self.runtime, job, set())), 2)
            returned = self.finish(job, attempt, result())
            if turn == 0: job, attempt = self.start(returned, 'wp')
        self.assertEqual(self.runtime.rows('SELECT * FROM file_publications'), [])

    def test_mixed_report_only_retains_both_originals(self):
        job, _, _, _ = self.mixed_job(discovery=False)
        for component in ['component', 'other']:
            local_native.snapshot(self.runtime, {'native':'review','component':component}, job)
        self.assertEqual(len(local_native.original_review_jobs(self.runtime, job, set())), 2)

    def mixed_refusal(self, corrupt):
        job, _, proposals, integrator = self.mixed_job()
        corrupt(proposals, integrator)
        with no_native_material(self.runtime), self.assertRaises(Refusal):
            local_native.snapshot(self.runtime, {'native':'review','component':'component'}, job)

    def test_nonselected_original_hold_still_refuses(self):
        self.mixed_refusal(lambda p,i:self.runtime.db.execute(
            "UPDATE events SET hold='fictional retained hold' WHERE id='second-original'"))

    def test_nonselected_original_collection_still_refuses(self):
        self.mixed_refusal(lambda p,i:self.runtime.db.execute(
            'UPDATE attempts SET collected=NULL WHERE id=?', (p[1]['source_attempt'],)))

    def test_nonselected_original_hash_still_refuses(self):
        def corrupt(*args):
            event = self.runtime.event('second-original'); event['body']['review']['component'] = 'forged'
            self.runtime.db.execute('UPDATE events SET payload=?,hash=? WHERE id=?', (encode(event), digest(event), event['id']))
        self.mixed_refusal(corrupt)

    def test_nonselected_original_package_still_refuses(self):
        self.mixed_refusal(lambda p,i:self.runtime.db.execute(
            "UPDATE jobs SET package='fictional-foreign' WHERE id=?", (p[1]['source_job'],)))

    def test_nonselected_original_scope_still_refuses(self):
        def corrupt(*args):
            row = self.runtime.one('SELECT selection FROM processing_capabilities WHERE id=?', (self.key,))
            selection = json.loads(row['selection'])
            selection['service']['reviews']['rp']['components']['other']['repository'] = '/fictional-forbidden'
            self.runtime.db.execute('UPDATE processing_capabilities SET selection=? WHERE id=?', (encode(selection), self.key))
        self.mixed_refusal(corrupt)

    def test_unrelated_binding_refuses_before_material(self):
        job, _, _, _ = self.mixed_job()
        with no_native_material(self.runtime), self.assertRaises(Refusal):
            local_native.snapshot(self.runtime, {'native':'review','component':'unrelated'}, job)


class EpochHandoff(OriginalHelpers, unittest.TestCase):
    def configure(self):
        # A genuine bridge requires the issuing principal to be Work itself.
        # Set this fictional principal before selection, not by weakening gates.
        self.runtime.config['roles']['Work']['owner'] = 'fictional-issuer'
        self.runtime.db.execute("UPDATE enrollments SET owner='fictional-issuer' WHERE role='Work'")
        self.runtime.config['tasks']['ri'].update(allowed_handoffs=['Work'], software_handoffs={})
        return OriginalFlow.configure(self)

    def setUp(self):
        OriginalFlow.setUp(self)
        selection = {'configuration':digest(self.runtime.config), 'authority':'fictional independently issued epoch',
                     'expires':1050., 'processing_capability':self.key,
                     'grants':{role:self.runtime.enrollment(role)['grant_id'] for role in ['Reviews','Work']},
                     'tasks':{name:{'task_hash':digest(self.runtime.config['tasks'][name]),
                                   'ordinary_effects':False, 'software_handoffs':{'Work':['wp']} if name == 'ri' else {}}
                              for name in ['ri','wp']}}
        self.epoch = prospective.select(self.runtime, self.runtime.config['roles']['Work']['owner'], selection)['id']

    def finish(self, job, attempt, answer):
        if job['task'] == 'ri':
            # Fictional worker identity/receipt, not a real native session.
            self.runtime.session(attempt, '46300000-0000-4000-8000-000000000001')
            answer['handoffs'] = [{'kind':'work','recipient':'Work','text':'fictional complete original review handoff',
                                   'ref':'fictional-component','required':'settled'}]
        return OriginalFlow.finish(self, job, attempt, answer)

    def handoff_job(self):
        _, _, integrator = self.graph(discovery=False)
        integrator = self.runtime.job(integrator['id'])
        outbox = self.runtime.one("SELECT * FROM outboxes WHERE job=? AND kind='work'", (integrator['id'],))
        self.assertIsNotNone(outbox)
        self.assertNotIn('wp', self.runtime.config['tasks']['ri']['software_handoffs'].get('Work', []))
        self.assertEqual(prospective.for_job(self.runtime, integrator)['id'], self.epoch)
        # Fictional external transport rows; production handoff constructor,
        # current grants and source payload identities remain real code paths.
        proof = json.loads(self.runtime.attempt(integrator['active_attempt'])['detail'])['software_authority']
        delivery = {'id':outbox['id'], 'kind':'work', 'actor':self.runtime.config['actor'],
                    'payload':outbox['payload'], 'grant_id':proof['grant_id'],
                    'recipient':self.runtime.config['roles']['Work']['owner'], 'post':1, 'notice':'fictional-notice'}
        self.conn.execute('INSERT INTO coordinator_deliveries_v1 '
            '(id,grant_id,actor,producer,recipient,payload,notice,post,transport_started,kind) VALUES(?,?,?,?,?,?,?,?,0,?)',
            (outbox['id'],proof['grant_id'],delivery['actor'],outbox['producer'],delivery['recipient'],
             outbox['payload'],delivery['notice'],delivery['post'],'work'))
        self.conn.execute("INSERT INTO notification_outbox VALUES(?,'managed','managed_pending')", (delivery['notice'],))
        self.assertTrue(self.selected_boards['Reviews'].software_delivery(self.runtime, outbox, self.selected_boards))
        link = self.runtime.one('SELECT event FROM processing_delivery_links WHERE delivery=?', (outbox['id'],))
        event = self.runtime.event(link['event'])
        self.assertEqual(event['body'], json.loads(outbox['payload']))
        # The independent internal response is still pending classification;
        # classify it first, without reserving it as the handoff receiver.
        internal = self.runtime.event(integrator['response'])
        for pending in sorted([internal, event], key=lambda e:e['id']):
            self.classify(pending, 'wp')
        row = {'task':'wp', 'role':'Work', 'phase':'proposer', 'package':'package',
               'members':encode([{'event':event['id'], 'hash':digest(event), 'package':'package'}])}
        return row, integrator, outbox, event

    def test_current_epoch_only_route_observes_genuine_handoff(self):
        row, _, _, _ = self.handoff_job()
        value, _ = local_native.snapshot(self.runtime, {'native':'review','component':'component'}, row)
        self.assertEqual(value['context']['run'], 'fictional-original-run')
        self.assertEqual(len(local_native.original_review_jobs(self.runtime, row, set())), 1)

    def epoch_refusal(self, corrupt):
        row, source, outbox, event = self.handoff_job()
        corrupt(source, outbox, event)
        with no_native_material(self.runtime), self.assertRaises(Refusal):
            local_native.snapshot(self.runtime, {'native':'review','component':'component'}, row)

    def test_revoked_epoch_refuses(self):
        self.epoch_refusal(lambda *args:prospective.revoke(
            self.runtime, self.runtime.config['roles']['Work']['owner'], self.epoch))

    def test_expired_epoch_refuses(self):
        self.epoch_refusal(lambda *args:setattr(self.runtime, 'clock', lambda:1051.))

    def test_static_route_cannot_override_epoch(self):
        def corrupt(*args):
            # Independently declared adverse fixture: current epoch disallows
            # this route even while the static map names it. Bind hashes/bases
            # as a fresh controller fixture; no operational config is touched.
            self.runtime.config['tasks']['ri']['software_handoffs'] = {'Work':['wp']}
            self.fixture_configuration()
            row = self.runtime.one('SELECT selection FROM prospective_authorities WHERE id=?', (self.epoch,))
            selection = json.loads(row['selection'])
            selection['configuration'] = digest(self.runtime.config)
            selection['tasks']['ri']['task_hash'] = digest(self.runtime.config['tasks']['ri'])
            selection['tasks']['ri']['software_handoffs'] = {}
            self.runtime.db.execute('UPDATE prospective_authorities SET selection=? WHERE id=?', (encode(selection),self.epoch))
        self.epoch_refusal(corrupt)

    def test_unknown_bound_epoch_refuses(self):
        def corrupt(source,*args):
            attempt = self.runtime.attempt(source['active_attempt']); detail = json.loads(attempt['detail'])
            detail['software_authority']['prospective_epoch'] = 'fictional-unknown-epoch'
            self.runtime.db.execute('UPDATE attempts SET detail=? WHERE id=?', (encode(detail),attempt['id']))
        self.epoch_refusal(corrupt)

    def test_missing_bound_epoch_refuses(self):
        def corrupt(source,*args):
            attempt = self.runtime.attempt(source['active_attempt']); detail = json.loads(attempt['detail'])
            detail['software_authority'].pop('prospective_epoch')
            self.runtime.db.execute('UPDATE attempts SET detail=? WHERE id=?', (encode(detail),attempt['id']))
        self.epoch_refusal(corrupt)

    def test_handoff_payload_tamper_refuses(self):
        self.epoch_refusal(lambda source,outbox,event:self.runtime.db.execute(
            "UPDATE outboxes SET payload='{}' WHERE id=?", (outbox['id'],)))

    def test_original_hold_refuses(self):
        self.epoch_refusal(lambda *args:self.runtime.db.execute("UPDATE events SET hold='fictional hold' WHERE id='original'"))


def suite():
    # Select only new controls here; inherited methods are selected separately
    # by the launcher for changed-path regression evidence.
    return unittest.TestSuite(cls(name) for cls in [DiscoveryPresence, MixedComponents, EpochHandoff]
        for name in cls.__dict__ if name.startswith('test_'))


if __name__ == '__main__':
    run = unittest.TextTestRunner(verbosity=2).run(suite())
    Path('/fixtures/result.json').write_text(encode({'run':run.testsRun,'failures':len(run.failures),'errors':len(run.errors)}))
    raise SystemExit(not run.wasSuccessful())
