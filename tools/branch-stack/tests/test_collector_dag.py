"""New integration controls only; no live files, Git, board or old 99-suite rerun."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import collector_observations as acquisitions

from adapter_support import load_core, BOARD, RECIPIENT
from feed_adapter import FeedAdapter, DEFERRAL_V1, DEFERRAL_V2, apply_on_encounter
from collector_observations import project_latest, project_health, HeldInput
from collector_dag_adapter import (ACCOUNT, PRODUCER, FACETS, OwnerBindings, freeze_bundle,
        foreground_check, translate, guarded_native_probe, structural_query_dto)
from board_receipt_adapter import BoardSender

CORE=load_core(Path(os.environ["DAG_IMMUTABLE_CORE"]))
BASE=Path(os.environ["DAG_IMMUTABLE_CANDIDATE"])
NEW=Path(__file__).resolve().parents[1]
RUN=Path(os.environ["DAG_TEST_OUTPUT"])
NOW="2026-11-02T03:11:10+00:00"
BINDING="selected-existing-collector-dag-v1"
REPO="controlled/repository"

def campaign():
    e=deepcopy(json.loads((BASE/"fixtures/work-deferral-projection-v2.json").read_text())["entries"])
    return {"complete_inventory_required":False,"encountered":[],"entries":e,"exemptions_applied":0,
            "generated_at":NOW,"mode":"ON_ENCOUNTER","ordinary_rules_for_unlisted":True,
            "projection":"controlled-derived","schema":"rfq.branch-deferral-eligibility-projection/2",
            "state":"OK","trigger_truth_capability":"CONTROLLED"}

def latest_document(snapshot):
    rows=[]
    for u in snapshot["units"]:
        rows.append({"activity":1,"age_seconds":4,"branch":u["ref"][11:],
                     "campaign_eligibility":{"exemption_applied":False,"ordinary_nudge_state":"OK",
                                             "reason":"controlled","state":"OK"},
                     "ci_by_head":[],"distinct_heads":[u["version"]["head"]],
                     "head_relationships":[],"heads":[{"activity":1,"location":"opaque-controlled",
                                                      "oid":u["version"]["head"]}],
                     "prs":[{"branch":u["ref"][11:],"ci":{"current_head_correspondence":True,
                             "head":u["version"]["head"],"other_head_receipts":[],"reason":"controlled",
                             "state":"UNKNOWN"},"head":u["version"]["head"],"number":u["pr"],
                             "repo":REPO,"requested":[],"review":{"approval_evidence":None,
                             "approved_current_head":False,"daily_alert":False,"hourly_excluded":False,
                             "looked_since_request":False,"old_head_approval":False,
                             "outstanding_adam_request":False,"request_age_seconds":0,
                             "request_at":NOW,"request_clock":"controlled","request_event_id":1,
                             "why_not_merged":None},"url":"https://invalid.example/controlled"}],
                     "repo":REPO})
    return {"check_id":"CONTROLLED-CHECK","checked_at":NOW,"code_version":"controlled-code-v1",
            "errors":[],"result":{"active_obligation_alerts":[],"eligibility_unknowns":[],
            "campaign_eligibility":campaign(),"coverage":[{"local_registry":"UNKNOWN",
             "remote_live_refs":len(rows),"remote_live_state":"OK","repo":REPO}],
            "external_bound_instance_coverage":[],"selected":rows,"stale_alerts":[],
            "pending_review_excluded":[],"window":{"actual_window_days":1,"distinct_owned_total":len(rows),
            "preferred_window_days":1,"ranking":"controlled","selected":len(rows),"widened":False}}}

def health_document():
    return {"actual_board_notice":True,"actual_recipient_response":"AMBIGUOUS","category":"branches",
            "check_id":"CONTROLLED-CHECK","code_version":"controlled-code-v1","command_count":0,
            "delivery":None,"ended_at":NOW,"live_30second_acceptance":"FAIL","numeric_exit":0,
            "queue_accepted":True,"recipient_acknowledged":True,
            "resources":{"admit":True,"available_memory_bytes":1,"root_free_bytes":1},
            "resume_outcome":"UNKNOWN","resume_requested":True,"runtime_notice":None,
            "source_failures":0,"source_state":"OK","started_at":NOW}

def baseline():
    s=json.loads((BASE/"fixtures/diamond-healthy.json").read_text())
    s["feed"].update(binding=BINDING,schema="selected-owner-dag-v1")
    for u in s["units"]: u["native_stack"]="1649"
    return s

def native_for(s):
    # CONTROLLED metadata for pre-existing synthetic fixture. No real native claim.
    rows=[]
    for i,u in enumerate(s["units"],1):
        rows.append({"position":i,"pullRequest":{"number":u["pr"],"state":"OPEN","isDraft":False,
                 "headRefName":u["ref"][11:],"headRefOid":u["version"]["head"],
                 "baseRefName":u["physical_base"]["ref"]}})
    return {"data":{"repository":{"defaultBranchRef":{"name":"main","target":{"oid":s["main"]}}},
                    "node":{"id":"PRS_kwDOOtFmdM4ALB_v","number":1649,"size":len(rows),
                            "baseRefName":"main","entries":{"nodes":rows}}}}

def bundle_for(s, *, partial=False):
    latest=project_latest(CORE,latest_document(s),REPO,{u["pr"] for u in s["units"]},
                          {u["ref"][11:] for u in s["units"]})
    acq={"latest":latest,"health":project_health(CORE,health_document()),"commands":None,"frontiers":[]}
    if partial: acq.update(latest=None,health=None,frontiers=["latest-input-UNKNOWN"])
    return freeze_bundle(CORE,account=ACCOUNT,producer=PRODUCER,repo=REPO,binding=BINDING,
        acquisition=acq,native_packet=native_for(s),native_observed_at=NOW,acquired_at=NOW)

def owner_for(s,b):
    s=deepcopy(s); s["feed"]["snapshot_id"]=b["snapshot_id"]
    envelope={"schema":"branch-source-envelope/v1","account":RECIPIENT,"binding":BINDING,
              "event_ids":["event-"+str(i) for i in range(len(s.get("events",[])))],
              "scope":{"prs":[u["pr"] for u in s["units"]],"complete_inventory":False},"snapshot":s}
    return OwnerBindings(envelope,NOW,{k:sorted(FACETS) for k in
                        ["main"]+[str(u["pr"]) for u in s["units"]]},
                         "controlled-source-owner","controlled/source-binding",b["snapshot_id"])

class MockTransport:
    def __init__(self,area): self.calls=[]; self.area=area
    def run(self,argv,*,env):
        self.calls.append(list(argv)); n=100+len(self.calls)
        stdout=(f"{n}\nboard={BOARD} thread={n} post={n} pending=0 sending=0 queued=0 "
                "acknowledged=1 failed=0 ambiguous=0 managed_pending=0\n"
                f"notices: {BOARD}#{n}=acknowledged\n").encode()
        d=self.area/str(n); d.mkdir()
        (d/"stdout").write_bytes(stdout); (d/"stderr").write_bytes(b"")
        (d/"argv.json").write_text(json.dumps(argv)); (d/"stdin").write_bytes(b"")
        (d/"exit.json").write_text('{"exit_code":0}')
        return {"stdout":stdout,"stderr":b"","exit_code":0,"timed_out":False,"launch_error":None}

class Integration(unittest.TestCase):
    def setUp(self):
        self.area=Path(tempfile.mkdtemp(dir=RUN))
        self.n=0; self.s=baseline(); self.b=bundle_for(self.s)
    def args(self,b=None):
        self.n+=1; d=self.area/str(self.n);d.mkdir()
        return dict(account=ACCOUNT,repo=REPO,binding=BINDING,expected_snapshot_id=(b or self.b)["snapshot_id"],
                    now=NOW,capture_dir=d,expected_code_version="controlled-code-v1")
    def check(self,b=None,s=None,owner=True,**kwargs):
        b=b or self.b; s=s or self.s
        a=self.args(b); a.update(journal_path=self.area/"journal.json",lock_path=self.area/"owner.lock",
                               owner="controlled-existing-owner",check_id="check-"+str(self.n),
                               owner_bindings=owner_for(s,b) if owner else None)
        a.update(kwargs)
        return foreground_check(CORE,b,**a)
    def test_actual_frozen_native_partial_enters_real_runtime_without_send(self):
        intake=json.loads((NEW/"fixtures/work9679-frozen-intake.json").read_text())
        self.assertEqual(intake["latest"]["metadata"]["checked_at"],"2026-11-02T03:11:01.072198+00:00")
        native=json.loads((NEW/"fixtures/work9679-native-structural.json").read_text())
        b=freeze_bundle(CORE,account=ACCOUNT,producer=PRODUCER,repo="lama-ai-RFQ/RFQautomation",
                binding=BINDING,acquisition={"latest":None,"health":None,"commands":None,
                "frontiers":["initial-projection-omitted-branch-rows-UNKNOWN","commands-input-UNKNOWN"]},
                native_packet=native,native_observed_at=None,acquired_at=NOW)
        a=self.args(b);a.update(repo=b["repo"])
        t=translate(CORE,b,**a)
        self.assertIsNone(t["snapshot"]); self.assertEqual(len(t["known_metadata"]),6)
        self.assertEqual(t["main_structure"]["target"]["tree"]["oid"],"1a154d75fab37c0f15f64696524c0bf5e6d77e3e")
        self.assertTrue(all(v["state"]=="UNKNOWN" for k,v in t["field_provenance"].items()
                            if k.startswith("native_")))
        called=[]
        a=self.args(b);a.update(repo=b["repo"],journal_path=self.area/"j",lock_path=self.area/"l",
            owner="test-owner",check_id="actual-partial-check",sender=lambda x:called.append(x))
        r=foreground_check(CORE,b,**a)
        self.assertEqual(r["status"],"UNKNOWN");self.assertFalse(called)
        self.assertEqual(len(r["partial_bindings"]["known_metadata"]),6)
        self.assertIn("field_provenance",r["partial_bindings"])
        (RUN/"actual-partial-result.json").write_text(json.dumps(
            {"runtime":r,"known_native":t["known_metadata"],"main_structure":t["main_structure"],
             "field_provenance":t["field_provenance"],"frontiers":t["frontiers"]},indent=2))
    def test_real_observed_schema_shape_is_used(self):
        i=json.loads((NEW/"fixtures/work9679-frozen-intake.json").read_text())
        shape=i["latest"]["original_shape"]
        doc=latest_document(self.s)
        self.assertEqual(set(doc),set(shape));self.assertEqual(set(doc["result"]),set(shape["result"]))
        observed=shape["result"]["selected"]["item_shapes"][0]
        self.assertEqual(set(doc["result"]["selected"][0]),set(observed))
        self.assertEqual(set(health_document()),set(i["health"]["original_shape"]))
    def test_healthy_explicit_scope_quiet_and_outside_scope_not_failure(self):
        r=self.check(); self.assertEqual(r["status"],"HEALTHY_WITHIN_EXPLICIT_SCOPE")
        self.assertEqual(r["alerts"],[]);self.assertEqual(r["delivery"]["state"],"SILENT")
    def test_incomplete_native_has_no_placeholder_versions(self):
        t=translate(CORE,self.b,**self.args());self.assertIsNone(t["snapshot"])
        self.assertNotIn("version",t["known_metadata"][0])
    def test_owner_edges_stay_arbitrary_not_native_order(self):
        t=translate(CORE,self.b,owner_bindings=owner_for(self.s,self.b),**self.args())
        p=CORE.plan(t["snapshot"])
        self.assertEqual(p["logical_dependencies"]["C"],["A"])
        self.assertNotIn("B",p["logical_dependencies"]["C"])
    def test_freshness_threshold_and_future_are_unknown(self):
        for at in ("2026-11-02T01:00:00+00:00","2026-11-03T03:11:10+00:00"):
            b=deepcopy(self.b);b["acquisition"]["latest"]["checked_at"]=at
            b=rebind(b);r=self.check(b)
            self.assertEqual(r["status"],"UNKNOWN")
    def test_stale_owner_cannot_send_but_obligations_retained(self):
        self.s["violations"]=[{"unit":"A","kind":"cloud_demo","obligation":"demo-required","evidence_ref":"controlled/demo"}]
        o=owner_for(self.s,self.b)
        o=OwnerBindings(o.envelope,"2026-11-02T00:00:00+00:00",o.field_coverage,o.source_owner,o.binding_ref,o.bundle_id)
        called=[];r=self.check(owner_bindings=o,sender=lambda a:called.append(a))
        self.assertEqual(r["status"],"UNKNOWN");self.assertFalse(called)
        self.assertEqual(len(r["retained_known_active_violations"]),1)
    def test_missing_input_does_not_hide_qualified_active_obligation(self):
        b=bundle_for(self.s,partial=True)
        self.s["violations"]=[{"unit":"A","kind":"cloud_demo","obligation":"demo-required","evidence_ref":"controlled/demo"}]
        # R2: missing collector input is UNKNOWN even with an independently
        # qualified violation. Its actual notice and violation must survive.
        r=self.check(b,self.s);self.assertEqual(r["status"],"UNKNOWN")
        self.assertTrue(r["known_violations"])
        self.assertTrue(any(a["disposition"]=="cloud_demo" for a in r["alerts"]))
        self.assertTrue(any(p["kind"]=="cloud_demo" for p in r["plan"]["problems"]))
        self.assertEqual(len(r["retained_known_active_violations"]),1)
    def test_wrong_coverage_state_never_healthy(self):
        b=deepcopy(self.b);b["acquisition"]["latest"]["coverage"][0]["remote_live_state"]="UNKNOWN"
        r=self.check(rebind(b));self.assertEqual(r["status"],"UNKNOWN")
    def test_missing_owner_facet_is_partial(self):
        o=owner_for(self.s,self.b);o.field_coverage["10"].remove("ordered_parents")
        r=self.check(owner_bindings=o);self.assertEqual(r["status"],"UNKNOWN")
    def test_unknown_native_field_whole_packet_rejected_before_callback(self):
        b=deepcopy(self.b);b["native_packet"]["data"]["node"]["body"]="unrecognized-controlled"
        called=[];r=self.check(rebind(b),sender=lambda a:called.append(a))
        self.assertEqual(r["status"],"UNKNOWN");self.assertFalse(called)
    def test_unknown_collector_field_ignored_without_projection(self):
        doc=latest_document(self.s);doc["result"]["selected"][0]["credential"]="controlled-secret-marker"
        result=project_latest(CORE,doc,REPO,{10},{"A"})
        self.assertNotIn("controlled-secret-marker",json.dumps(result))
    def test_mutated_frozen_snapshot_fails_CAS(self):
        b=deepcopy(self.b);b["native_known"][0]["headRefOid"]="a"*40
        r=self.check(b);self.assertEqual(r["status"],"UNKNOWN")
    def test_wrong_account_and_version_do_not_qualify(self):
        wrong=dict(ACCOUNT,profile=".codex3")
        self.assertEqual(self.check(account=wrong)["status"],"UNKNOWN")
        self.assertEqual(self.check(expected_code_version="wrong-v2")["status"],"UNKNOWN")
    def test_wrong_owner_head_rejected(self):
        self.s["units"][0]["version"]["head"]="b"*40
        self.assertEqual(self.check()["status"],"UNKNOWN")
    def test_distinct_scheduled_checks_repeat_and_ack_notice_only_enqueued(self):
        self.s["violations"]=[{"unit":"A","kind":"cloud_demo","obligation":"demo-required","evidence_ref":"controlled/demo"}]
        area=self.area/"sender";area.mkdir(); streams=self.area/"mock-streams";streams.mkdir()
        transport=MockTransport(streams);actor="11111111-1111-4111-8111-111111111111"
        sender=BoardSender(CORE,home=self.area,sender=actor,current_actor=actor,transport=transport,
                           evidence_dir=area,runtime_env={"CODEX_SESSION_ID":actor})
        r1=self.check(sender=sender,check_id="scheduled-1")
        r2=self.check(sender=sender,check_id="scheduled-2")
        self.assertEqual(len(transport.calls),2)
        self.assertNotEqual(r1["alerts"][0]["alert_id"],r2["alerts"][0]["alert_id"])
        self.assertEqual(r1["delivery"]["state"],"ENQUEUED")
        self.assertEqual(r2["delivery"]["state"],"ENQUEUED")
        self.assertIn(RECIPIENT,transport.calls[0]);self.assertIn(BOARD,transport.calls[0])
        self.assertFalse(r1["native_effects"])
    def test_same_check_replay_never_resends(self):
        self.s["violations"]=[{"unit":"A","kind":"repair","obligation":"repair-required","evidence_ref":"controlled/repair"}]
        called=[]
        def queued(a):
            called.append(a);return {"stage":"ENQUEUED","board":BOARD,"recipient":RECIPIENT,"notification_id":1}
        self.check(sender=queued,check_id="same-check")
        self.check(sender=queued,check_id="same-check")
        self.assertEqual(len(called),1)
    def test_ambiguous_transport_retained_without_false_push(self):
        self.s["violations"]=[{"unit":"A","kind":"repair","obligation":"repair-required","evidence_ref":"controlled/repair"}]
        def failed(a): raise RuntimeError("controlled-failure")
        r=self.check(sender=failed)
        self.assertEqual(r["delivery"]["state"],"AMBIGUOUS")
    def test_changed_head_persists_stale_in_single_existing_journal(self):
        self.check()
        changed=deepcopy(self.s);changed["units"][0]["version"]["head"]="c"*40
        b=bundle_for(changed);r=self.check(b,changed)
        self.assertEqual(r["status"],"VIOLATION");self.assertIn("A",r["plan"]["stale"])
        r2=self.check(b,changed);self.assertIn("A",r2["plan"]["stale"])
    def test_v1_missing_trigger_stays_unknown_and_v2_requires_explicit_selection(self):
        s=baseline();s["units"][0]["pr"]=1230;s["units"][0]["ref"]="refs/heads/feat/integrated-auth-cloud-full"
        b=bundle_for(s)
        v1=json.loads((BASE/"fixtures/work-deferral-projection.json").read_text())
        # Use same on-encounter entry with its actual exact repository.
        s["repo"]=v1["entries"][0]["repository"]
        v1result=apply_on_encounter(CORE,s,v1)
        self.assertTrue(v1result["frontiers"])
        v2=json.loads((BASE/"fixtures/work-deferral-projection-v2.json").read_text())
        decision=json.loads((BASE/"fixtures/work-trigger-decision.json").read_text())
        with self.assertRaises(ValueError):apply_on_encounter(CORE,s,v2)
        result=apply_on_encounter(CORE,s,v2,capability=DEFERRAL_V2,**decision)
        self.assertFalse(result["snapshot"]["units"][0]["eligibility"]["trigger"])
        result["snapshot"]["violations"]=[{"unit":"A","kind":"cloud_demo",
                 "obligation":"demo-required","evidence_ref":"controlled/demo"}]
        self.assertTrue(any(p["kind"]=="cloud_demo" for p in CORE.plan(result["snapshot"])["problems"]))
    def test_unsupported_native_stops_before_callback(self):
        calls=[]
        r=guarded_native_probe(capability="REAL_RFQ_NATIVE",callback=lambda:calls.append(1))
        self.assertEqual(r["status"],"UNKNOWN");self.assertFalse(calls)
    def test_irrelevant_nested_carrier_ignored_by_structural_projection(self):
        doc=latest_document(self.s)
        doc["result"]["selected"][0]["campaign_eligibility"]["reason"]={"config":"CONTROLLED"}
        result=project_latest(CORE,doc,REPO,{10},{"A"})
        self.assertEqual(result,project_latest(CORE,latest_document(self.s),REPO,{10},{"A"}))
    def test_controlled_once_acquisition_uses_real_schema_and_no_command_authority(self):
        inputs=self.area/"controlled-files";inputs.mkdir()
        values=[latest_document(self.s),health_document(),{"command":"$(touch forbidden-marker)"}]
        for path,value in zip(acquisitions.INPUTS,values):
            (inputs/path.name).write_text(json.dumps(value))
        calls=[]; raw_custody=[]; real_open=os.open
        def bounded_open(path,flags):
            calls.append(path)
            return real_open(inputs/path.name,flags)
        selection=acquisitions.ReadSelection(acquisitions.INPUTS,PRODUCER,kernel_readonly=True)
        def custody(name,raw):
            raw_custody.append(name)
            (self.area/("custody-"+name)).write_bytes(raw)
        with patch.object(acquisitions.os,"open",bounded_open):
            r=acquisitions.acquire_once(CORE,selection,repo=REPO,prs={10},refs={"A"},custody=custody)
        self.assertEqual(calls,list(acquisitions.INPUTS))
        self.assertEqual(raw_custody,[p.name for p in acquisitions.INPUTS])
        self.assertEqual(r["latest"]["rows"][0]["prs"][0]["number"],10)
        self.assertIsNone(r["commands"]);self.assertIn("commands-input-UNKNOWN",r["frontiers"])
        self.assertNotIn("command",json.dumps(r["latest"]))
        self.assertFalse((self.area/"forbidden-marker").exists())
    def test_oversize_controlled_commands_stay_unknown_without_parse(self):
        inputs=self.area/"controlled-files";inputs.mkdir()
        for path,value in zip(acquisitions.INPUTS[:2],[latest_document(self.s),health_document()]):
            (inputs/path.name).write_text(json.dumps(value))
        (inputs/acquisitions.INPUTS[2].name).write_bytes(b"x"*(acquisitions.MAX_INPUT+1))
        real_open=os.open;seen=[]
        def bounded_open(path,flags): return real_open(inputs/path.name,flags)
        with patch.object(acquisitions.os,"open",bounded_open):
            r=acquisitions.acquire_once(CORE,acquisitions.ReadSelection(acquisitions.INPUTS,PRODUCER,
                  kernel_readonly=True),repo=REPO,prs={10},refs={"A"},
                  custody=lambda name,raw:seen.append(name))
        self.assertEqual(len(seen),3);self.assertIsNone(r["commands"])
        self.assertEqual(r["frontiers"],["commands-input-UNKNOWN"])
    def test_command_frontier_alone_is_outside_qualified_structural_scope(self):
        b=deepcopy(self.b);b["acquisition"]["frontiers"]=["commands-input-UNKNOWN"]
        self.assertEqual(self.check(rebind(b))["status"],"HEALTHY_WITHIN_EXPLICIT_SCOPE")
    def test_missing_v1_trigger_propagates_unknown_through_foreground(self):
        projection=json.loads((BASE/"fixtures/work-deferral-projection.json").read_text())
        projection["entries"][0]["repository"]=REPO;projection["entries"][0]["pull_request"]=10
        self.assertEqual(self.check(deferral_projection=projection)["status"],"UNKNOWN")
    def test_explicit_v2_foreground_retains_active_demo_violation(self):
        projection=json.loads((BASE/"fixtures/work-deferral-projection-v2.json").read_text())
        projection["entries"][0].update(repository=REPO,pull_request=10,known_branch="A")
        decision=json.loads((BASE/"fixtures/work-trigger-decision.json").read_text())
        self.s["violations"]=[{"unit":"A","kind":"cloud_demo","obligation":"demo-required","evidence_ref":"controlled/demo"}]
        r=self.check(deferral_projection=projection,deferral_capability=DEFERRAL_V2,**decision)
        self.assertEqual(r["status"],"VIOLATION")
        self.assertTrue(any(a["disposition"]=="cloud_demo" for a in r["alerts"]))
    def test_qualified_owner_leaf_provenance_has_UTC_coverage_identity(self):
        t=translate(CORE,self.b,owner_bindings=owner_for(self.s,self.b),**self.args())
        provenance=t["field_provenance"]["owner_snapshot/units/0/version/head"]
        self.assertEqual(provenance["producer"],"controlled-source-owner")
        self.assertEqual(provenance["state"],"FRESH")
        self.assertEqual(provenance["snapshot_id"],self.b["snapshot_id"])
        self.assertEqual(provenance["coverage"],"QUALIFIED_EXPLICIT_OWNER_SCOPE")
    def test_CAS_rejected_owner_retains_unbound_active_obligations_without_send(self):
        self.s["units"][0]["version"]["head"]="d"*40
        self.s["violations"]=[{"unit":"A","kind":"repair","obligation":"repair-required","evidence_ref":"controlled/repair"}]
        called=[]
        r=self.check(sender=lambda a:called.append(a))
        self.assertEqual(r["status"],"UNKNOWN");self.assertFalse(called)
        self.assertEqual(len(r["retained_known_active_violations"]),1)
    def test_query_DTO_bounded_and_unexecuted(self):
        dto=structural_query_dto("lama-ai-RFQ/RFQautomation")
        self.assertEqual(dto["encountered_prs"],[1639,1640,1647,1648,1645,1641])
        self.assertFalse(dto["request_executed"])
        for prohibited in ("body","comments","statusCheckRollup","object(expression","blobs"):
            self.assertNotIn(prohibited,dto["query"])
        self.assertIn("tree { oid }",dto["query"]);self.assertIn("parents(first:32)",dto["query"])

def rebind(b):
    b=deepcopy(b);b["snapshot_id"]=CORE.digest({k:v for k,v in b.items() if k!="snapshot_id"})
    return b

if __name__=="__main__":
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(Integration)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    (RUN/"test-summary.json").write_text(json.dumps({"tests":result.testsRun,
        "failures":len(result.failures),"errors":len(result.errors),"skips":len(result.skipped),
        "case_ids":[name for name in unittest.defaultTestLoader.getTestCaseNames(Integration)],
        "exit_code":0 if result.wasSuccessful() else 1},indent=2))
    raise SystemExit(0 if result.wasSuccessful() else 1)

class JoinedCorrectedCore(unittest.TestCase):
    setUp=Integration.setUp
    args=Integration.args
    check=Integration.check
    def observation(self):
        native=native_for(self.s);repo=native["data"]["repository"];node=native["data"]["node"]
        # A controlled six-row envelope follows the normal producer format.
        prs=(1639,1640,1647,1648,1645,1641);rows=[]
        repo["defaultBranchRef"]["target"].update(tree={"oid":"a"*40},
            parents={"nodes":[],"pageInfo":{"hasNextPage":False}})
        for i,number in enumerate(prs,1):
            head=format(number,"040x")
            p={"number":number,"state":"OPEN","isDraft":False,
               "headRefName":"controlled-"+str(number),"headRefOid":head,"baseRefName":"main",
               "headRef":{"target":{"oid":head,"tree":{"oid":"b"*40},
                     "parents":{"nodes":[],"pageInfo":{"hasNextPage":False}}}}}
            repo["p"+str(number)]=p
            rows.append({"position":i,"pullRequest":{k:p[k] for k in
                ("number","headRefName","headRefOid","baseRefName")}})
        node["size"]=6;node["entries"]={"nodes":rows,"pageInfo":{"hasNextPage":False}}
        return {"schema":"bounded-existing-six-native-structural-observation/1",
            "producer_session":ACCOUNT["session"],"profile":ACCOUNT["profile"],"role":ACCOUNT["role"],
            "repo":"lama-ai-RFQ/RFQautomation","acquisition_start":"2026-11-02 03:11:09 UTC",
            "acquisition_end":"2026-11-02 03:11:10 UTC","actual_native_exit":0,"query":"CONTROLLED",
            "data":native["data"],"no_source_bodies":True,"no_CI":True,
            "no_logical_dependency_or_semantic_or_atomic_snapshot_claim":True,"source":"CONTROLLED"}
    def test_JOIN_normal_source_format_complete_metadata_preserves_unknown_edges(self):
        from collector_dag_adapter import normalize_native_observation
        r=normalize_native_observation(CORE,self.observation())
        self.assertEqual(r["observed_at"],NOW)
        self.assertEqual(len(r["packet"]["data"]["node"]["entries"]["nodes"]),6)
        self.assertEqual(r["source_receipt"]["logical_dependencies"],"UNKNOWN")
        self.assertNotIn("requires",json.dumps(r))
    def test_JOIN_normal_source_head_disagreement_rejects_before_runtime(self):
        from collector_dag_adapter import normalize_native_observation
        o=self.observation();o["data"]["repository"]["p1639"]["headRefOid"]="f"*40
        with self.assertRaises(ValueError):normalize_native_observation(CORE,o)
    def test_JOIN_incomplete_parents_or_missing_sourceUTC_rejects(self):
        from collector_dag_adapter import normalize_native_observation
        o=self.observation();o["data"]["repository"]["p1639"]["headRef"]["target"]["parents"]["pageInfo"]["hasNextPage"]=True
        with self.assertRaises(ValueError):normalize_native_observation(CORE,o)
        o=self.observation();del o["acquisition_end"]
        with self.assertRaises(ValueError):normalize_native_observation(CORE,o)
    def test_JOIN_collector_failure_atomic_rejection_historical_replay(self):
        first=self.check(check_id="first")
        before=(self.area/"journal.json").read_bytes()
        changed=deepcopy(self.s);changed["units"][0]["version"]["head"]="e"*40
        b=bundle_for(changed)
        with self.assertRaises(CORE.Invalid):self.check(b,changed,check_id="first")
        self.assertEqual((self.area/"journal.json").read_bytes(),before)
        self.check(b,changed,check_id="later")
        later=(self.area/"journal.json").read_bytes();calls=[]
        replay=self.check(check_id="first",sender=lambda a:calls.append(a))
        self.assertTrue(replay["replayed"]);self.assertEqual(replay["plan"],first["plan"])
        self.assertFalse(calls);self.assertEqual((self.area/"journal.json").read_bytes(),later)
    def test_JOIN_missing_input_UNKNOWN_retains_actual_notice_and_known_violation(self):
        b=bundle_for(self.s,partial=True)
        self.s["violations"]=[{"unit":"A","kind":"cloud_demo","obligation":"demo-required",
                              "evidence_ref":"controlled/demo"}]
        r=self.check(b,self.s)
        self.assertEqual(r["status"],"UNKNOWN")
        self.assertTrue(r["known_violations"]);self.assertTrue(r["alerts"])
        self.assertEqual(len(r["retained_known_active_violations"]),1)

class FinalBindingBoundary(unittest.TestCase):
    setUp=Integration.setUp
    args=Integration.args
    check=Integration.check
    def complete(self):
        b=deepcopy(self.b)
        def commit(v):
            return {"oid":v["head"],"tree":{"oid":v["tree"]},
                    "parents":{"nodes":[{"oid":p} for p in v["parents"]],
                               "pageInfo":{"hasNextPage":False}}}
        main={"head":self.s["main"],"tree":"a"*40,"parents":["b"*40,"c"*40]}
        b["native_packet"]["data"]["repository"]["defaultBranchRef"]["target"]=commit(main)
        for row,u in zip(b["native_packet"]["data"]["node"]["entries"]["nodes"],self.s["units"]):
            row["pullRequest"]["headRef"]={"target":commit(u["version"])}
        b=rebind(b);o=owner_for(self.s,b)
        o=OwnerBindings(o.envelope,o.observed_at,o.field_coverage,o.source_owner,o.binding_ref,o.bundle_id,main)
        return b,o
    def rejected(self,b,o):
        called=[];r=self.check(b,owner_bindings=o,sender=lambda a:called.append(a))
        self.assertEqual(r["status"],"UNKNOWN");self.assertFalse(called)
        self.assertFalse((self.area/"journal.json").exists())
        return r
    def test_FINISH_correct_complete_immutable_binding(self):
        b,o=self.complete();self.assertEqual(self.check(b,owner_bindings=o)["status"],"HEALTHY_WITHIN_EXPLICIT_SCOPE")
    def test_FINISH_wrong_tree_same_head_rejected_retains_violation(self):
        b,o=self.complete();o.envelope['snapshot']['units'][0]['version']['tree']='e'*40
        o.envelope['snapshot']['violations']=[{'unit':'A','kind':'repair','obligation':'repair-required','evidence_ref':'controlled/repair'}]
        r=self.rejected(b,o);self.assertEqual(len(r['retained_known_active_violations']),1)
    def test_FINISH_wrong_parents_same_head_rejected(self):
        b,o=self.complete();o.envelope['snapshot']['units'][0]['version']['parents']=['e'*40];self.rejected(b,o)
    def test_FINISH_ordered_parents_reversal_rejected(self):
        b,o=self.complete();u=o.envelope['snapshot']['units'][0];u['version']['parents']=['b'*40,'c'*40]
        n=b['native_packet']['data']['node']['entries']['nodes'][0]['pullRequest']['headRef']['target']
        n['parents']['nodes']=[{'oid':'c'*40},{'oid':'b'*40}];b=rebind(b)
        o=OwnerBindings(o.envelope,o.observed_at,o.field_coverage,o.source_owner,o.binding_ref,b['snapshot_id'],o.main_version)
        o.envelope['snapshot']['feed']['snapshot_id']=b['snapshot_id'];self.rejected(b,o)
    def test_FINISH_wrong_Main_tree_rejected(self):
        b,o=self.complete();o.main_version['tree']='e'*40;self.rejected(b,o)
    def test_FINISH_wrong_Main_parents_rejected(self):
        b,o=self.complete();o.main_version['parents'].reverse();self.rejected(b,o)
    def test_FINISH_missing_Main_structure_is_not_auto_bound(self):
        b,o=self.complete();o=OwnerBindings(o.envelope,o.observed_at,o.field_coverage,o.source_owner,o.binding_ref,o.bundle_id)
        self.rejected(b,o)
    def test_FINISH_stale_scope_no_mutation_or_send(self):
        b=deepcopy(self.b);b['native_observed_at']='2026-11-01T01:00:00+00:00';b=rebind(b)
        self.rejected(b,owner_for(self.s,b))
    def test_FINISH_future_collector_no_mutation_or_send(self):
        b=deepcopy(self.b);b['acquisition']['latest']['checked_at']='2026-11-03T01:00:00+00:00';b=rebind(b)
        self.rejected(b,owner_for(self.s,b))
    def test_FINISH_wrong_codeversion_no_mutation_or_send(self):
        called=[];r=self.check(expected_code_version='incorrect',sender=lambda a:called.append(a))
        self.assertEqual(r['status'],'UNKNOWN');self.assertFalse(called);self.assertFalse((self.area/'journal.json').exists())
    def test_FINISH_irrelevant_outside_scope_rows_not_rejected(self):
        d=latest_document(self.s);d['result']['selected'].insert(0,{'repo':REPO,'branch':'outside','prs':[], 'unrelated':{'arbitrary':['data']}})
        self.assertTrue(project_latest(CORE,d,REPO,{10},{'A'})['rows'])
    def test_FINISH_relevant_bad_head_is_rejected(self):
        d=latest_document(self.s);d['result']['selected'][0]['prs'][0]['head']='bad-head'
        with self.assertRaises(ValueError):project_latest(CORE,d,REPO,{10},{'A'})
    def test_FINISH_current_producer_partial_health_and_commands(self):
        from collector_observations import project_commands
        h=health_document();h['source_state']='PARTIAL_UNKNOWN';h['source_failures']=14;h['runtime_notice']={'ordinary':'ignored'}
        self.assertEqual(project_health(CORE,h)['source_failures'],14)
        c=project_commands(CORE,{'category':'branches','check_id':'actual','code_version':'v5',
            'commands':[{'argv':['touch','forbidden-marker'],'unknown':{'x':1}}]})
        self.assertEqual(c['count'],1);self.assertFalse(c['execution_authority']);self.assertNotIn('touch',json.dumps(c))
    def test_FINISH_existing_producer_callable(self):
        from collector_dag_adapter import existing_monitor_check
        a=self.args();a.pop('account');a.pop('expected_snapshot_id');a.pop('expected_code_version')
        r=existing_monitor_check(CORE,latest=latest_document(self.s),health=health_document(),
            commands={'category':'branches','check_id':'CONTROLLED-CHECK','code_version':'controlled-code-v1','commands':[]},
            native_packet=native_for(self.s),native_observed_at=NOW,acquired_at=NOW,
            expected_code_version='controlled-code-v1',journal_path=self.area/'j',lock_path=self.area/'l',
            owner='controlled',check_id='callable',**a)
        self.assertEqual(r['result']['status'],'UNKNOWN');self.assertTrue(r['bundle']['acquisition']['latest']['rows'])
    def test_FINISH_reopened_replay_status_is_indeterminate(self):
        self.check(check_id='historical');r=self.check(check_id='historical')
        self.assertEqual(r['status'],'INDETERMINATE');self.assertEqual(r['persistence']['durability'],'UNVERIFIED_AFTER_REOPEN')
    def test_FINISH_normal_readonly_Git_metadata(self):
        import test_adapters as a
        from git_probe_adapter import readonly_metadata
        r=readonly_metadata(CORE,git_dir=a.FIX['repo'],main_ref='refs/heads/fixture',
            selections=[{'number':1,'ref':'refs/heads/fixture','physical_base_ref':'refs/heads/fixture'}],
            capture_dir=self.area/'readonly-git')
        self.assertEqual(r['main']['head'],a.FIX['versions']['Main']['head'])
        self.assertEqual(r['main']['tree'],a.FIX['versions']['Main']['tree'])
        self.assertEqual(r['status'],'METADATA_VERIFIED');self.assertFalse(r['source_writes'])

    def test_FINISH_actual_query_response_state_draft_and_baseOid(self):
        from collector_dag_adapter import normalize_native_observation
        o=JoinedCorrectedCore.observation(self)
        for r in o['data']['node']['entries']['nodes']:
            r['pullRequest'].update(state='OPEN',isDraft=False)
        for key in ('p1639','p1640','p1647','p1648','p1645','p1641'):
            o['data']['repository'][key]['baseRefOid']=self.s['main']
        n=normalize_native_observation(CORE,o)
        self.assertEqual(len(n['packet']['data']['node']['entries']['nodes']),6)
        o['data']['node']['entries']['nodes'][0]['pullRequest']['isDraft']=True
        with self.assertRaises(ValueError):normalize_native_observation(CORE,o)
    def test_FINISH_absolute_error_labels_preserve_partial_source_health(self):
        d=latest_document(self.s);d['errors']=[{'source':'/mnt/c/Users/xteam/IdeaProjects/rfq-upgrade-qa:branch_registry','state':'UNKNOWN','reason':'ordinary-operational-error'}]
        p=project_latest(CORE,d,REPO,{10},{'A'})
        self.assertEqual(p['source_failures'],1)
        self.assertEqual(p['source_errors'][0]['source'],d['errors'][0]['source'])
        b=deepcopy(self.b);b['acquisition']['latest']=p;b=rebind(b)
        r=self.check(b);self.assertEqual(r['status'],'UNKNOWN')
    def test_FINISH_immutable_upstream_pins_normal_Git_database(self):
        import test_adapters as a
        from git_probe_adapter import readonly_metadata
        ref='refs/heads/not-asserted-to-exist';head=a.FIX['versions']['Main']['head']
        r=readonly_metadata(CORE,git_dir=a.FIX['repo'],main_ref=ref,
            selections=[{'number':1,'ref':ref,'physical_base_ref':ref}],pinned_heads={ref:head},
            capture_dir=self.area/'pinned-readonly-git')
        self.assertEqual(r['main']['tree'],a.FIX['versions']['Main']['tree'])
        self.assertEqual(r['ref_binding'],'EXPLICIT_UPSTREAM_PINS_LOCAL_REFS_NOT_ASSERTED')
