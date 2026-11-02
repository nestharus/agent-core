"""F1-F5 and Work V2 regression controls, from the correction brief.

Real core/journal/CLI and stock Git-backed adapter suite; external transport MOCK.
CORRECTION_CORE_SOURCE permits five bounded red reproductions of original core.
"""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import unittest
import test_stack_controller as t
import test_adapters as a
from adapter_runtime import check_once
from adapter_support import AdapterError
from feed_adapter import apply_on_encounter, DEFERRAL_V1, DEFERRAL_V2

C = t.c
if os.environ.get("CORRECTION_CORE_SOURCE"):
    spec = importlib.util.spec_from_file_location("original_core_red_probe", os.environ["CORRECTION_CORE_SOURCE"])
    C = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(C)
ROOT = Path(__file__).resolve().parents[1]
R = Path(os.environ["CORRECTION_TEST_RUNTIME"])

class Owned(unittest.TestCase):
    def setUp(self):
        self.area = R / self._testMethodName
        self.area.mkdir(mode=0o700)

    def seed(self, name="state"):
        area = self.area/name
        area.mkdir()
        s = t.snapshot("linear")
        s["groups"] = []
        s["probes"] = [t.probe(s, ["A","B"], kind="pair", status="CONFLICT")]
        p = C.plan(s)
        notices = C.alerts(s, p, "prior")
        calls = []
        def uncertain(alert):
            calls.append(alert["alert_id"])
            raise TimeoutError("MOCK transport ambiguity")
        journal = area/"journal.json"
        with C.owner_lock(area/"initial.lock", C.RECIPIENT):
            j = C.DeliveryJournal(journal)
            j.observe(s)
            row = j.deliver("prior", notices, p["plan_id"], uncertain)
        self.assertEqual(row["state"], "AMBIGUOUS")
        self.assertEqual(len(calls), 1)
        before = journal.read_bytes()
        (self.area/(name+"-before.bin")).write_bytes(before)
        return area, journal, s, p, notices, before

    def cli(self, command, s, *, state=None, lock=None, check="new"):
        inputs = self.area/("inputs-"+str(len(list(self.area.iterdir()))))
        inputs.mkdir()
        snapshot = inputs/"snapshot.json"
        snapshot.write_text(json.dumps(s))
        args = [command, "--snapshot", str(snapshot)]
        if command == "once":
            binding = inputs/"binding.json"
            binding.write_text(json.dumps({
                "schema":"stack-startup/v1", "source_sha256":hashlib.sha256(Path(C.__file__).read_bytes()).hexdigest(),
                "snapshot_sha256":hashlib.sha256(snapshot.read_bytes()).hexdigest(),
                "feed_binding":s["feed"]["binding"],"feed_schema":s["feed"]["schema"],"owner":C.RECIPIENT}))
            args += ["--binding",str(binding),"--journal",str(state/"journal.json"),
                     "--lock",str(lock),"--check-id",check]
        cap = self.area/("cli-"+str(len(list(self.area.iterdir()))))
        cap.mkdir()
        argv = ["/usr/bin/bwrap","--ro-bind","/","/","--unshare-all","--die-with-parent",
                "--new-session","--proc","/proc","--dev","/dev","--tmpfs","/tmp"]
        if state is not None:
            argv += ["--bind",str(state),str(state)]
        argv += ["--","/usr/bin/python3","-I","-S","-B",str(C.__file__),*args]
        (cap/"argv.json").write_text(json.dumps(argv))
        (cap/"stdin.bin").write_bytes(b"")
        with (cap/"stdout.bin").open("wb") as out, (cap/"stderr.bin").open("wb") as err:
            r = subprocess.run(argv,stdin=subprocess.DEVNULL,stdout=out,stderr=err,timeout=10)
        (cap/"result.json").write_text(json.dumps({"exit_code":r.returncode}))
        return r.returncode,(cap/"stdout.bin").read_bytes(),(cap/"stderr.bin").read_bytes()

    def ambiguity_still_durable(self, journal, s, p, notices):
        calls=[]
        def uncertain(alert):
            calls.append(alert["check_id"]);raise TimeoutError("MOCK")
        j=C.DeliveryJournal(journal)
        self.assertEqual(j.deliver("prior",notices,p["plan_id"],uncertain)["state"],"AMBIGUOUS")
        self.assertEqual(calls,[])
        ns=C.alerts(s,p,"next-distinct")
        self.assertEqual(j.deliver("next-distinct",ns,p["plan_id"],uncertain)["state"],"AMBIGUOUS")
        self.assertEqual(calls,["next-distinct"])
        j.deliver("next-distinct",ns,p["plan_id"],uncertain)
        self.assertEqual(calls,["next-distinct"])
        self.assertEqual(j.deliver("healthy",[],p["plan_id"],uncertain)["state"],"SILENT")
        self.assertEqual(calls,["next-distinct"])

class F1Journal(Owned):
    def test_F1_core_same_path_preserves_actual_ambiguous_journal(self):
        state,journal,s,p,ns,before=self.seed()
        code,out,err=self.cli("once",s,state=state,lock=journal)
        (self.area/"after.bin").write_bytes(journal.read_bytes())
        self.assertEqual(code,2,err)
        self.assertEqual(out,b"")
        self.assertEqual(json.loads(err)["schema"],"stack-error/v1")
        self.assertEqual(journal.read_bytes(),before)
        self.ambiguity_still_durable(journal,s,p,ns)

    def test_F1_core_hardlink_preserves_every_byte(self):
        state,journal,s,p,ns,before=self.seed()
        alias=state/"hardlink.lock";os.link(journal,alias)
        self.assertEqual(journal.stat().st_ino,alias.stat().st_ino)
        code,out,err=self.cli("once",s,state=state,lock=alias)
        self.assertEqual(code,2,err)
        self.assertEqual(journal.read_bytes(),before)
        self.assertEqual(alias.read_bytes(),before)
        self.ambiguity_still_durable(journal,s,p,ns)

    def test_F1_core_symlink_lock_rejected_without_writing_target(self):
        state,journal,s,p,ns,before=self.seed()
        alias=state/"symlink.lock";alias.symlink_to(journal)
        code,out,err=self.cli("once",s,state=state,lock=alias)
        self.assertEqual(code,2,err)
        self.assertEqual(journal.read_bytes(),before)

    def test_F1_core_separate_file_preserves_lock_and_history(self):
        state,journal,s,p,ns,before=self.seed()
        lock=state/"separate.lock";lock.write_bytes(b"existing lock bytes")
        code,out,err=self.cli("once",s,state=state,lock=lock)
        self.assertEqual(code,3,err)
        self.assertEqual(lock.read_bytes(),b"existing lock bytes")
        self.assertEqual(json.loads(out)["delivery"]["state"],"PLANNED")
        self.assertEqual(C.DeliveryJournal(journal).data["checks"]["prior"]["state"],"AMBIGUOUS")
        self.ambiguity_still_durable(journal,s,p,ns)

    def test_F1_adapter_same_path_hardlink_symlink_and_separate(self):
        for kind in ("same","hard","symlink","separate"):
            with self.subTest(kind=kind):
                state,journal,s,p,ns,before=self.seed(kind)
                lock=journal if kind=="same" else state/"owner.lock"
                if kind=="hard":os.link(journal,lock)
                elif kind=="symlink":lock.symlink_to(journal)
                elif kind=="separate":lock.write_bytes(b"preserved")
                sent=[]
                def mock(alert):
                    sent.append(alert["check_id"]);raise TimeoutError("MOCK")
                args=dict(journal_path=journal,lock_path=lock,owner=C.RECIPIENT,check_id="adapter-new",sender=mock)
                feed={"schema":"branch-adapter-result/v1","snapshot":s}
                if kind=="separate":
                    r=check_once(C,feed,**args)
                    self.assertEqual(r["delivery"]["state"],"AMBIGUOUS")
                    self.assertEqual(sent,["adapter-new"])
                    self.assertEqual(lock.read_bytes(),b"preserved")
                else:
                    with self.assertRaises((C.Invalid,OSError)):
                        check_once(C,feed,**args)
                    self.assertEqual(journal.read_bytes(),before)
                    self.assertEqual(sent,[])
                self.ambiguity_still_durable(journal,s,p,ns)

    def test_F1_journal_symlink_to_lock_is_rejected(self):
        state,journal,s,p,ns,before=self.seed()
        lock=state/"owner.lock";os.link(journal,lock)
        alias=state/"journal-alias";alias.symlink_to(journal)
        with self.assertRaises(C.Invalid):
            with C.owner_lock(lock,C.RECIPIENT,journal_path=alias):
                self.fail("symlink journal accepted")
        self.assertEqual(journal.read_bytes(),before)
        self.assertEqual(lock.read_bytes(),before)

    def test_F1_fstat_guard_rechecked_before_journal_save(self):
        state=self.area/"state";state.mkdir()
        lock=state/"lock";lock.write_bytes(b"no inode write")
        path=state/"journal"
        with C.owner_lock(lock,C.RECIPIENT,journal_path=path) as fd:
            j=C.DeliveryJournal(path,lock_fd=fd)
            os.link(lock,path)
            with self.assertRaises(C.Invalid):j.save()
        self.assertEqual(path.read_bytes(),b"no inode write")
        self.assertFalse((state/"journal.pending").exists())

    def test_F1_lock_hardlinked_to_owned_program_never_mutates_program(self):
        source=self.area/"owned-program.py";source.write_bytes(b"print('fixture only')\n")
        lock=self.area/"lock";os.link(source,lock)
        with C.owner_lock(lock,C.RECIPIENT):
            self.assertEqual(lock.read_bytes(),source.read_bytes())
        self.assertEqual(source.read_bytes(),b"print('fixture only')\n")

class F2Obligations(Owned):
    def input(self,pr=1230,active=False):
        s=t.snapshot("linear");s["groups"]=[]
        t.at(s,"B")["pr"]=pr;t.at(s,"B")["eligibility"]["active"]=active
        s["violations"]=[{"unit":"B","kind":"whole_landing","obligation":"explicit/landing","evidence_ref":"current/obligation"}]
        return s

    def test_F2_inactive_undeferred_PR1230_whole_landing_alerts(self):
        s=self.input()
        self.assertEqual([n["disposition"] for n in C.alerts(s,C.plan(s),"tick")],["whole_landing"])
        code,out,err=self.cli("plan",s)
        self.assertEqual(code,3,err)
        self.assertEqual(json.loads(out)["problems"][0]["kind"],"whole_landing")

    def test_F2_PR_active_trigger_and_bound_deferral_controls(self):
        for pr in (1230,1231):
            for active in (False,True):
                s=self.input(pr,active)
                self.assertEqual(len(C.alerts(s,C.plan(s),"tick")),1)
                e=t.at(s,"B")["eligibility"]
                e.update(deferred=True,trigger=False,deferral_ref="work/current-explicit-decision")
                self.assertEqual(C.alerts(s,C.plan(s),"tick"),[])
                e["trigger"]=True
                self.assertEqual(len(C.alerts(s,C.plan(s),"tick")),1)
                e["trigger"]=False;e["deferral_ref"]=None
                with self.assertRaises(C.Invalid):C.plan(s)

    def test_F2_all_critical_obligations_independent_of_upstream_deferral(self):
        s=self.input(9876)
        t.at(s,"B")["eligibility"].update(deferred=True,deferral_ref="work/current")
        kinds=["cloud_demo","required_closure","repair","conservation_failure","unexpected_change"]
        s["violations"]=[{"unit":"B","kind":k,"obligation":"active/"+k,"evidence_ref":"active/current"} for k in kinds]
        self.assertEqual([n["disposition"] for n in C.alerts(s,C.plan(s),"tick")],kinds)

class F3Selection(Owned):
    def held(self,s,uid="A"):
        t.at(s,uid)["eligibility"].update(active=False,deferred=True,trigger=False,deferral_ref="work/held")
        return s

    def test_F3_held_ancestor_unknown_no_operations_dependency_kept(self):
        s=self.held(t.healthy(t.snapshot("linear")))
        p=C.plan(s)
        self.assertEqual(p["operations"],[])
        self.assertEqual(p["logical_dependencies"]["B"],["A"])
        self.assertEqual(p["groups"][0]["remaining"],["A","B"])
        self.assertEqual(p["groups"][0]["qualification"],"UNQUALIFIED")
        self.assertEqual(p["groups"][0]["disposition"],"UNKNOWN")
        self.assertEqual(p["manual_frontier"],["A"])
        r=C.simulate(s,p,t.actual(s),t.outcomes(s))
        self.assertEqual(r["trace"],[])
        self.assertEqual(r["groups"][0]["disposition"],"UNKNOWN")

    def test_F3_deferred_tip_no_automatic_activation(self):
        s=self.held(t.healthy(t.snapshot("linear")),"B")
        p=C.plan(s)
        self.assertEqual(p["operations"],[])
        self.assertEqual(p["groups"][0]["disposition"],"DEFERRED")
        self.assertEqual(p["logical_dependencies"]["B"],["A"])

    def test_F3_shared_held_ancestor_blocks_all_dependent_groups_only(self):
        s=self.held(t.healthy(t.snapshot()))
        p=C.plan(s)
        self.assertEqual([o["unit"] for o in p["operations"]],["Z"])
        self.assertEqual([g["disposition"] for g in p["groups"]],["UNKNOWN","UNKNOWN","PLANNED"])
        self.assertEqual(p["groups"][0]["held_units"],["A"])
        self.assertEqual(p["groups"][1]["held_units"],["A"])

    def test_F3_positive_eligibility_and_exact_landed_mapping_controls(self):
        s=self.held(t.healthy(t.snapshot("linear")))
        t.at(s,"A")["eligibility"].update(active=True,trigger=True)
        p=C.plan(s)
        self.assertEqual([o["unit"] for o in p["operations"]],["A","B"])
        self.assertEqual(p["groups"][0]["disposition"],"PLANNED")
        t.at(s,"A")["eligibility"]["active"]=False
        self.assertEqual(C.plan(s)["groups"][0]["disposition"],"UNKNOWN")
        s["merges"]=[t.merged(s,"A")]
        p=C.plan(s)
        self.assertEqual([o["unit"] for o in p["operations"]],["B"])
        self.assertEqual(p["logical_dependencies"]["B"],["A"])
        self.assertEqual(p["operations"][0]["new_bases"],[{"unit":"A","tip":s["main"]}])

    def test_F3_active_obligations_retained_while_ancestor_is_held(self):
        s=self.held(t.healthy(t.snapshot("linear")))
        s["violations"]=[{"unit":"A","kind":k,"obligation":"active/"+k,"evidence_ref":"current/active"}
                         for k in ("cloud_demo","required_closure","repair","conservation_failure")]
        problems=C.plan(s)["problems"]
        self.assertEqual([p["kind"] for p in problems],["UNKNOWN","cloud_demo","required_closure","repair","conservation_failure"])

class F4Versions(Owned):
    def test_F4_list_versions_structured_exit2_no_traceback(self):
        s=t.healthy(t.snapshot("linear"));s["probes"][0]["versions"]=["A","B"]
        code,out,err=self.cli("plan",s)
        self.assertEqual(code,2,err)
        self.assertEqual(out,b"")
        self.assertNotIn(b"Traceback",err)
        self.assertEqual(json.loads(err)["schema"],"stack-error/v1")

    def test_F4_missing_binding_and_valid_mapping_controls(self):
        s=t.healthy(t.snapshot("linear"));del s["probes"][0]["versions"]["B"]
        code,out,err=self.cli("plan",s)
        self.assertEqual(code,2,err)
        self.assertEqual(json.loads(err)["schema"],"stack-error/v1")
        code,out,err=self.cli("plan",t.healthy(t.snapshot("linear")))
        self.assertEqual(code,0,err)
        self.assertEqual(json.loads(out)["groups"][0]["disposition"],"PLANNED")

class F5Pairs(Owned):
    def pair_input(self):
        s=t.snapshot("linear");s["groups"]=[]
        row=t.probe(s,["B","A"],kind="pair",status="CONFLICT")
        s["probes"]=[copy.deepcopy(row),copy.deepcopy(row)]
        s["probes"][-1]["units"]=["A","B"]
        return s

    def test_F5_repeated_symmetric_history_yields_one_DTO(self):
        s=self.pair_input();p=C.plan(s)
        self.assertEqual(len(C.alerts(s,p,"tick")),1)
        self.assertEqual(len(p["observed_conflicts"]),1)
        self.assertEqual(p["observed_conflicts"][0]["units"],["A","B"])
        s2=copy.deepcopy(s)
        for row in s2["probes"]:row["units"].reverse()
        self.assertEqual(C.alerts(s2,C.plan(s2),"tick"),C.alerts(s,p,"tick"))

    def test_F5_latest_clean_clears_stale_versions_and_Main_excluded(self):
        s=self.pair_input()
        s["probes"].append(t.probe(s,["A","B"],kind="pair",status="CLEAN"))
        self.assertEqual(C.alerts(s,C.plan(s),"tick"),[])
        s=self.pair_input()
        for row in s["probes"]:row["versions"]["A"]="f"*64
        self.assertEqual(C.alerts(s,C.plan(s),"tick"),[])
        s=self.pair_input()
        for row in s["probes"]:row["base"]="f"*40
        self.assertEqual(C.alerts(s,C.plan(s),"tick"),[])
        s=self.pair_input()
        stale=t.probe(s,["A","B"],kind="pair",status="CLEAN")
        stale["versions"]["A"]="f"*64
        s["probes"].append(stale)
        self.assertEqual(len(C.alerts(s,C.plan(s),"tick")),1)
        s["probes"].append(t.probe(s,["B","A"],kind="pair",status="CLEAN"))
        self.assertEqual(C.alerts(s,C.plan(s),"tick"),[])

    def test_F5_one_send_per_check_repeat_distinct_not_ambiguous_replay(self):
        s=self.pair_input();p=C.plan(s);calls=[]
        def mock(alert):
            calls.append(alert["check_id"]);raise TimeoutError("MOCK")
        lock=self.area/"lock";journal=self.area/"journal"
        with C.owner_lock(lock,C.RECIPIENT,journal_path=journal) as fd:
            j=C.DeliveryJournal(journal,lock_fd=fd)
            for index,check in enumerate(("one","one","two")):
                current=copy.deepcopy(s)
                if index==1:
                    for probe in current["probes"]:probe["units"].reverse()
                effective=C.plan(current)
                self.assertEqual(effective["plan_id"],p["plan_id"])
                ns=C.alerts(current,effective,check);self.assertEqual(len(ns),1)
                self.assertEqual(j.deliver(check,ns,effective["plan_id"],mock)["state"],"AMBIGUOUS")
            self.assertEqual(j.deliver("healthy",[],p["plan_id"],mock)["state"],"SILENT")
        self.assertEqual(calls,["one","two"])

class V2Work(Owned):
    def inputs(self):
        projection=json.loads((ROOT/"fixtures/work-deferral-projection-v2.json").read_text())
        authority=json.loads((ROOT/"fixtures/work-trigger-decision.json").read_text())
        s=t.snapshot("linear");s["groups"]=[]
        s["repo"]="lama-ai-RFQ/RFQautomation"
        u=t.at(s,"B");u["pr"]=1230;u["ref"]="refs/heads/feat/integrated-auth-cloud-full"
        s["violations"]=[{"unit":"B","kind":k,"obligation":"current/"+k,"evidence_ref":"current/obligation"}
                         for k in ("stall","whole_landing","cloud_demo","required_closure","repair","conservation_failure")]
        return s,projection,authority
    def apply(self,s,p,auth,**kw):
        return apply_on_encounter(C,s,p,capability=DEFERRAL_V2,**auth,**kw)

    def test_V2_explicit_false_durable_decision_keeps_active_obligations_once(self):
        s,p,auth=self.inputs()
        r=self.apply(s,p,auth)
        self.assertEqual(r["selected_capability"],DEFERRAL_V2)
        self.assertEqual(r["frontiers"],[])
        self.assertEqual(t.at(r["snapshot"],"B")["eligibility"]["trigger"],False)
        self.assertEqual([n["disposition"] for n in C.alerts(r["snapshot"],C.plan(r["snapshot"]),"tick")],
                         ["cloud_demo","required_closure","repair","conservation_failure"])
        self.assertEqual(s["units"][1]["eligibility"]["deferred"],False)
        self.assertIn("not-runtime-readiness",r["decision_semantics"])

    def test_V2_requires_explicit_capability_V1_unknown_unchanged(self):
        s,p,auth=self.inputs()
        with self.assertRaises(AdapterError):apply_on_encounter(C,s,p,triggers={})
        v1=json.loads((ROOT/"fixtures/work-deferral-projection.json").read_text())
        before=copy.deepcopy(v1)
        r=apply_on_encounter(C,s,v1,triggers={})
        self.assertEqual(r["selected_capability"],DEFERRAL_V1)
        self.assertEqual(r["frontiers"],[{"pr":1230,"reason":"reactivation-trigger-UNKNOWN"}])
        self.assertEqual(r["snapshot"],s)
        self.assertEqual(v1,before)

    def test_V2_current_owner_Boolean_basis_durability_branch_controls(self):
        for variant in ("bool","owner","basis_type","basis","durability","branch","decision","duplicate","flags","PR_type"):
            with self.subTest(variant=variant):
                s,p,auth=self.inputs();e=p["entries"][0];d=e["reactivation"]
                if variant=="bool":d["satisfied"]="false";auth["work_decision"]=copy.deepcopy(d)
                elif variant=="owner":auth["work_owner"]="10000000-0000-4000-8000-000000000001"
                elif variant=="basis_type":d["basis_type"]="HEARTBEAT";auth["work_decision"]=copy.deepcopy(d)
                elif variant=="basis":d["basis"]="";auth["work_decision"]=copy.deepcopy(d)
                elif variant=="durability":d["effective_until"]="30s heartbeat";auth["work_decision"]=copy.deepcopy(d)
                elif variant=="branch":t.at(s,"B")["ref"]="refs/heads/different"
                elif variant=="decision":auth["work_decision"]["satisfied"]=True
                elif variant=="duplicate":p["entries"].append(copy.deepcopy(e))
                elif variant=="PR_type":e["pull_request"]=1230.0
                else:p["ordinary_rules_for_unlisted"]=False
                with self.assertRaises(AdapterError):self.apply(s,p,auth)

    def test_V2_repository_PR_unlisted_scope_ordinary_rules_and_no_override(self):
        for field,value in (("repo","other/repo"),("pr",1231)):
            s,p,auth=self.inputs()
            if field=="repo":s["repo"]=value
            else:t.at(s,"B")["pr"]=value
            r=self.apply(s,p,auth)
            self.assertEqual(r["encountered"],[])
            self.assertEqual(r["snapshot"],s)
            self.assertIn("whole_landing",[n["disposition"] for n in C.alerts(s,C.plan(s),"tick")])
        s,p,auth=self.inputs()
        with self.assertRaises(AdapterError):self.apply(s,p,auth,triggers={1230:True})

    def test_V2_explicit_supersession_true_control_not_foundation_inference(self):
        s,p,auth=self.inputs()
        p["entries"][0]["reactivation"]["satisfied"]=True
        auth["work_decision"]=copy.deepcopy(p["entries"][0]["reactivation"])
        r=self.apply(s,p,auth)
        self.assertTrue(t.at(r["snapshot"],"B")["eligibility"]["trigger"])
        self.assertIn("whole_landing",[n["disposition"] for n in C.alerts(r["snapshot"],C.plan(r["snapshot"]),"tick")])

    def test_V2_adapter_runtime_mocked_transport_ambiguity_repeat_healthy(self):
        s,p,auth=self.inputs()
        feed={"schema":"branch-adapter-result/v1","snapshot":s}
        calls=[]
        def mock(alert):
            calls.append((alert["check_id"],alert["disposition"]));raise TimeoutError("MOCK")
        args=dict(journal_path=self.area/"journal",lock_path=self.area/"lock",owner=C.RECIPIENT,
                  sender=mock,deferral_projection=p,deferral_capability=DEFERRAL_V2,**auth)
        for tick in ("one","one","two"):
            r=check_once(C,feed,check_id=tick,**args)
            self.assertEqual(r["delivery"]["state"],"AMBIGUOUS")
            self.assertEqual([n["disposition"] for n in r["alerts"]],
                             ["cloud_demo","required_closure","repair","conservation_failure"])
        self.assertEqual(calls,[("one","cloud_demo"),("two","cloud_demo")])
        quiet=copy.deepcopy(feed);quiet["snapshot"]["violations"]=[]
        r=check_once(C,quiet,check_id="healthy",**args)
        self.assertEqual(r["delivery"]["state"],"SILENT")
        self.assertEqual(len(calls),2)
