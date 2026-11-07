"""Unchanged parent refusal oracles; run before implementing successor routes."""
import copy
from fixture_software643 import SoftwareFixture643
from coordinator_runtime import resource_scopes as resources, service, processing_admission
from coordinator_runtime.contracts import Refusal, digest

class ParentRefusals643(SoftwareFixture643):
    def test_Q3_same_package_cleanup_is_blocked(self):
        self.assertFalse(self.blocked())
        self.assertTrue(resources.blocked(self.store,dict(role='QA',phase='cleanup',task='qa-cleanup',package='fictional-package')))

    def test_Q4_five_bindings_cannot_be_selected(self):
        record=copy.deepcopy(self.record)
        record['qa_operations']=[record.pop('qa_operation') for _ in range(1)]*5
        with self.assertRaises(Refusal): resources.validate(self.store,{'QA':record})

    def test_R1_genuine_collected_report_cannot_reserve_integrator(self):
        self.store.db.execute("UPDATE enrollments SET legacy_hold='Reviews global UNKNOWN' WHERE role='Reviews'")
        task=self.config['tasks']['reviews-integrator'];task['effects']='owned-artifacts'
        self.selection['basis']['configuration']=digest(self.config)
        self.selection['service']['report_tasks']=['reviews-integrator'];self.save()
        report=dict(reference='new owned report',collector=self.actor,actual_END=0,
                    reports=[dict(name='whole',body='Original method, dissent and PARTIAL coverage remain.')],
                    history='First fictional encounter; no old context adoption',method_pin='fictional-method',
                    coverage={'whole':False,'unread':['family']},effects='known-report-only')
        event=service.ingest_report(self.store,self.actor,'reviews-integrator',report)['event']
        self.assertTrue(resources.blocked(self.store,dict(event=event,role='Reviews',phase='integrator',task='reviews-integrator',package=None)))

    def test_same_initial_capability_digest_is_unavailable_at_selection(self):
        # Real selection contains only the prior whole admission. The public
        # automatic route embeds the new, random cap ID in its actual receipt.
        self.assertNotIn(self.cap, str(self.selection))
        admission=self.store.one('SELECT * FROM admissions')
        self.assertEqual(self.record['qa_operation']['binding']['admission_sha256'],digest(admission))
        scope=dict(submitters=[self.actor],package_prefix='future-',task_scopes={'qa-execution':self.scope},evidence='Typed future authority')
        selected={**self.selection,'software_admission':dict(authority='Future Work',max_packages=5,scopes={'future':scope})}
        processing_admission.validate(self.store,selected)
        self.store.admit('future-one',self.config['roles']['Branch']['owner'],dict(task_scopes={'qa-execution':self.scope},software_admission={'capability':self.cap}))
        applied=self.store.one("SELECT * FROM admissions WHERE package='future-one'")
        self.assertNotEqual(digest(applied),self.record['qa_operation']['binding']['admission_sha256'])
