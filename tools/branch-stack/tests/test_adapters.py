"""Independent real-Git and mocked external-board integration qualification."""
from __future__ import annotations
import copy
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"src"))
from adapter_support import *
from feed_adapter import *
from git_probe_adapter import GitProbe, owned_bytes
from board_receipt_adapter import *
from adapter_runtime import check_once
CORE=load_core(os.environ["ADAPTER_CORE_SOURCE"])
R=Path(os.environ["ADAPTER_TEST_RUNTIME"])
FIX=exact_json(Path(os.environ["ADAPTER_FIXTURE_HOME"]).joinpath("fixture.json").read_bytes())
V=FIX["versions"]
def unit(u,pr,requires=()):
    return {"id":u,"pr":pr,"ref":"refs/heads/"+u,"ticket":None,"campaign":None,
            "native_stack":None,"version":copy.deepcopy(V[u]),"requires":list(requires),
            "physical_base":{"ref":"main","head":V["Main"]["head"]},
            "provenance":{"original":["fixture/"+u],"tests":[],"oracles":[],"signatures":[]},
            "evidence":[],"admitted":True,
            "eligibility":{"active":True,"deferred":False,"trigger":False,"deferral_ref":None}}
def snap(names=("A","B","C"),order=None):
    units=[unit(u,100+i,["A"] if u in ("B","C") and "A" in names else []) for i,u in enumerate(names)]
    if order is None: order=list(names)
    tips=[u for u in names if not any(u in x["requires"] for x in units)]
    return {"schema":CORE.SCHEMA,"feed":{"binding":"fixture-existing","snapshot_id":"s1","schema":"fixture/v1"},
            "repo":"controlled/repo","main":V["Main"]["head"],"units":units,"segments":[],
            "groups":[{"id":"selected","tips":tips,"order":order}],"events":[],"merges":[],
            "probes":[],"violations":[]}
def get(s,u): return next(x for x in s["units"] if x["id"]==u)
class OwnedTest(unittest.TestCase):
    def setUp(self):
        self.area=R/self._testMethodName;self.area.mkdir(mode=0o700)
    def probe(self,s,order,kind="ordered",scope=None,records=None,timeout=10,max_bytes=64*1024**2,diff_algorithm="histogram"):
        p=GitProbe(CORE,self.area/("probe-"+str(len(list(self.area.iterdir())))),
                   timeout=timeout,max_bytes=max_bytes,diff_algorithm=diff_algorithm)
        return p,p.probe(s,order,kind=kind,main_version=V["Main"],
                         scope=copy.deepcopy(FIX["scope"] if scope is None else scope),
                         source_getter=lambda: copy.deepcopy(FIX["records"] if records is None else records))
class GitBehavior(OwnedTest):
    def test_real_clean_shared_ancestor_once_no_semantic_upgrade(self):
        s=snap();p,r=self.probe(s,["A","B","C"])
        self.assertEqual(r["status"],"CLEAN",r)
        self.assertEqual([x["unit"] for x in r["trace"]],["A","B","C"])
        self.assertEqual(r["semantic_frontier"],"UNKNOWN")
        s["probes"]=[r["probe"]]
        self.assertEqual(CORE.plan(s)["groups"][0]["disposition"],"UNKNOWN")
        # Independent tree oracle: exactly base + A/B/C files; shared A once.
        native=p.successful(p.git("ls-tree","--name-only",r["result_tip"])).decode().splitlines()
        self.assertEqual(native,["b.py","c.py","foundation.py","nway.py","ordered.py","shared.py"])
        self.assertEqual(len(p.imported),len(set(p.imported)))
        self.assertFalse((p.repo/"index").exists())
        self.assertEqual(list((p.repo/"refs"/"heads").iterdir()),[])
        self.assertTrue(all(e["exit_code"] in (0,129) for e in p.capture.ends))
    def test_real_conflict_paths_only_and_exact_native_exit(self):
        s=snap(("X","Y"));p,r=self.probe(s,["X","Y"],kind="pair")
        self.assertEqual(r["status"],"CONFLICT",r)
        self.assertEqual(r["probe"]["paths"],[{"path":"shared.py","ordinary_safe":True}])
        self.assertEqual(r["trace"][0]["native_exit"],1)
        self.assertNotIn("evil",json.dumps(r))
        self.assertFalse(r["probe"]["semantic"])
    def test_ordered_combined_failure_individual_clean_distinct_pair(self):
        for name in ("O1","O2"):
            s=snap((name,));_,r=self.probe(s,[name])
            self.assertEqual(r["status"],"CLEAN",r)
        s=snap(("O1","O2"));_,r=self.probe(s,["O1","O2"])
        self.assertEqual(r["status"],"CONFLICT",r)
        self.assertEqual([x["native_exit"] for x in r["trace"]],[0,1])
        self.assertEqual(r["probe"]["kind"],"ordered")
        _,pair=self.probe(s,["O1","O2"],kind="pair")
        self.assertEqual(pair["probe"]["kind"],"pair")
        self.assertEqual(pair["status"],"CONFLICT")
    def test_unadmitted_counterpart_or_path_stops_before_getter(self):
        for variant in ("unit","path","scope"):
            s=snap(); scope=copy.deepcopy(FIX["scope"]);calls=[]
            if variant=="unit":get(s,"B")["admitted"]=False
            elif variant=="path":scope["paths"][0]["body_admitted"]=False
            else:scope["complete"]=False
            p=GitProbe(CORE,self.area/variant)
            r=p.probe(s,["A","B","C"],kind="ordered",main_version=V["Main"],
                      scope=scope,source_getter=lambda:calls.append(1))
            self.assertEqual(calls,[])
            self.assertEqual(r["status"],"UNKNOWN")
            self.assertFalse(p.repo.exists())
    def test_exact_heads_trees_parents_Main_and_order_CAS(self):
        for k in ("head","tree","parents","main","order"):
            s=snap();main=copy.deepcopy(V["Main"]);order=["A","B","C"]
            if k=="parents":get(s,"B")["version"]["parents"]=[]
            elif k in ("head","tree"):get(s,"B")["version"][k]="1"*40
            elif k=="main":main["head"]="2"*40
            else:order=["A","C","B"]
            p=GitProbe(CORE,self.area/k)
            r=p.probe(s,order,kind="ordered",main_version=main,scope=FIX["scope"],
                      source_getter=lambda:FIX["records"])
            self.assertNotEqual(r["status"],"CLEAN")
            self.assertFalse(any("merge-tree" in json.loads((x/"launch.json").read_text())["argv"]
                                 for x in p.capture.directory.iterdir()
                                 if (x/"launch.json").exists() and
                                 "-h" not in json.loads((x/"launch.json").read_text())["argv"]))
    def test_native_unexpected_failure_original_numeric_exit(self):
        # A legitimate stock Git missing-object failure, never a fake positive shim.
        p=GitProbe(CORE,self.area/"native-failure");p.initialize()
        r=p.git("cat-file","-e","f"*40)
        self.assertEqual(r["exit_code"],1)
        self.assertFalse(r["timed_out"])
        self.assertEqual(json.loads(Path(r["capture"]).joinpath("result.json").read_text())["exit_code"],1)
    def test_real_process_timeout_original_signal_not_zero(self):
        p=ProcessCapture(self.area/"timeout",timeout=.05)
        r=p.run(["/usr/bin/python3","-I","-S","-B","-c","import time;time.sleep(5)"],
                env={"PATH":"/usr/bin:/bin"})
        self.assertTrue(r["timed_out"])
        self.assertEqual(r["exit_code"],-9)
        self.assertLess(r["elapsed_seconds"],2)
    def test_resource_limits_native_output_and_disk_frontier(self):
        p=ProcessCapture(self.area/"output-cap",timeout=3)
        r=p.run(["/usr/bin/python3","-I","-S","-B","-c",
                 "import os; b=b'x'*65536\nwhile True: os.write(1,b)"],
                env={"PATH":"/usr/bin:/bin"})
        self.assertNotEqual(r["exit_code"],0)
        self.assertLessEqual(Path(r["capture"]).joinpath("stdout.bin").stat().st_size,2*1024**2)
        gp=GitProbe(CORE,self.area/"disk",max_bytes=1024)
        with self.assertRaises(AdapterError):gp.initialize()
        self.assertLess(owned_bytes(gp.root),64*1024**2)
    def test_untrusted_driver_counter_executes_but_safe_probe_does_not(self):
        # Countercontrol runs only the generated touch command in our owned fixture.
        counter=self.area/"counter";counter.mkdir();objects=counter/"objects";objects.mkdir()
        env=git_environment(counter,objects)
        env["GIT_ALTERNATE_OBJECT_DIRECTORIES"]=str(Path(FIX["repo"])/"objects")
        cap=ProcessCapture(counter/"captures")
        marker=counter/"driver-marker"
        source_marker=Path(FIX["marker"])
        source_before=source_marker.stat().st_mtime_ns if source_marker.exists() else None
        cmd=["/usr/bin/git","--git-dir="+FIX["repo"],"-c",
             "merge.evil.driver=/usr/bin/touch "+str(marker),"-c",
             "core.attributesFile="+str(Path(__file__).resolve().parents[1]/"fixtures/driver-control.attributes"),"merge-tree","--write-tree",
             V["E1"]["head"],V["E2"]["head"]]
        self.assertFalse(marker.exists(),"counter marker must be fresh before actual activation")
        rc=cap.run(cmd,env=env,cwd=counter)
        self.assertEqual(rc["exit_code"],0)
        self.assertTrue(marker.exists(),"countercontrol must activate harmless synthetic driver")
        before=(marker.stat().st_mtime_ns,marker.stat().st_ctime_ns)
        s=snap(("E1","E2"));_,r=self.probe(s,["E1","E2"],kind="pair")
        self.assertEqual(r["status"],"CONFLICT",r)
        self.assertEqual(before,(marker.stat().st_mtime_ns,marker.stat().st_ctime_ns))
        self.assertEqual(source_before,source_marker.stat().st_mtime_ns if source_marker.exists() else None)
    def test_source_refs_index_config_objects_immutable(self):
        p=Path(FIX["repo"])
        paths=[p/"index",p/"config",p/"refs"/"heads"/"fixture"]+[Path(x["path"]) for x in FIX["records"]]
        before={str(x):sha(x.read_bytes()) for x in paths}
        _,r=self.probe(snap(),["A","B","C"]);self.assertEqual(r["status"],"CLEAN",r)
        self.assertEqual(before,{str(x):sha(x.read_bytes()) for x in paths})
        with self.assertRaises(OSError):(p/"index").write_bytes(b"must-not-write")
    def test_missing_ancestor_transport_native_failure_never_conflict(self):
        s=snap(("E1","E2"))
        records=[r for r in FIX["records"] if r["oid"]!=V["E0"]["head"]]
        p,r=self.probe(s,["E1","E2"],kind="pair",records=records)
        self.assertEqual(r["status"],"FAILURE",r)
        self.assertEqual(r["probe"]["status"],"UNKNOWN")
        self.assertTrue(any(e["exit_code"] not in (0,1,129) for e in p.capture.ends))
    def test_object_carrier_not_admitted_body_not_read(self):
        s=snap(("A",));records=copy.deepcopy(FIX["records"])
        records[0].update(admitted=False,path="/unadmitted/body/must-never-open")
        _,r=self.probe(s,["A"],records=records)
        self.assertEqual(r["status"],"UNKNOWN")
        self.assertIn("object-capability",r["probe"]["reason"])

    def test_all_real_pairs_clean_but_ordered_triple_conflicts(self):
        for pair in (["P","Q"],["P","S"],["Q","S"]):
            s=snap(tuple(pair));_,r=self.probe(s,pair,kind="pair",diff_algorithm="histogram")
            self.assertEqual(r["status"],"CLEAN",r)
        s=snap(("P","Q","S"));_,r=self.probe(s,["P","Q","S"],diff_algorithm="histogram")
        self.assertEqual(r["status"],"CONFLICT",r)
        self.assertEqual([t["native_exit"] for t in r["trace"]],[0,0,1])
        self.assertEqual(r["probe"]["paths"],[{"path":"nway.py","ordinary_safe":True}])

class FeedBehavior(OwnedTest):
    def adapter(self):
        return FeedAdapter(CORE,account="fixture-existing-account",binding="fixture-existing",
                           repo="controlled/repo",capture_dir=self.area)
    def envelope(self,s,ids=()):
        return {"schema":"branch-source-envelope/v1","account":"fixture-existing-account",
                "binding":"fixture-existing","scope":{"prs":[u["pr"] for u in s["units"]],
                "complete_inventory":False},"event_ids":list(ids),"snapshot":s}
    def test_core_roundtrip_Base_Main_ref_member_merge_event_and_identity(self):
        s=snap();old=copy.deepcopy(get(s,"A")["version"]);get(s,"A")["version"]=copy.deepcopy(V["X"])
        s["events"]=[{"kind":"ref","unit":"A","before":old,"after":V["X"],"evidence_ref":"event/ref"},
            {"kind":"base","unit":"B","before":{"ref":"old","head":"1"*40},
             "after":get(s,"B")["physical_base"],"evidence_ref":"event/base"},
            {"kind":"membership","unit":"C","before":"old-stack","after":None,"evidence_ref":"event/member"},
            {"kind":"merge","unit":"A","before":"pending","after":"event/merge-record","evidence_ref":"event/merge"},
            {"kind":"main","unit":None,"before":"2"*40,"after":s["main"],"evidence_ref":"event/main"}]
        e=self.envelope(s,["r1","b1","m1","merge1","main1"])
        r=self.adapter().typed(json.dumps(e).encode())
        self.assertEqual(r["snapshot"],s);self.assertEqual(r["event_ids"],e["event_ids"])
        p=CORE.plan(r["snapshot"]);self.assertEqual(p["stale"],["A","B","C"]);self.assertEqual(p["landed"],[])
    def test_unadmitted_false_never_upgraded_and_merge_exact_frontier(self):
        s=snap(("A","B"));get(s,"B")["admitted"]=False
        get(s,"A")["evidence"]=[{"kind":"test","version_key":CORE.version(V["A"]),"ref":"fixture/fail","result":"FAIL"}]
        s["merges"]=[{"unit":"A","version_key":CORE.version(V["A"]),"method":"squash",
          "main_head":s["main"],"landed_commit":V["A"]["head"],"main_ancestry_verified":False,
          "mapping":"unknown","evidence_ref":"fixture/mapping"}]
        a=self.adapter();r=a.typed(json.dumps(self.envelope(s)).encode())
        self.assertFalse(get(r["snapshot"],"B")["admitted"])
        self.assertEqual(CORE.plan(r["snapshot"])["manual_frontier"],["A"])
        s["merges"][0].update(mapping="exact",main_ancestry_verified=True)
        r=a.typed(json.dumps(self.envelope(s)).encode())
        self.assertEqual(CORE.plan(r["snapshot"])["landed"],["A"])
    def test_native_fixed_six_missing_tree_unknown_not_all_inventory(self):
        raw=Path(os.environ["ADAPTER_NATIVE_METADATA"]).read_bytes()
        r=self.adapter().native(raw,snapshot_id="prior-fixed",associations={},groups=[])
        self.assertIsNone(r["snapshot"])
        self.assertEqual(r["scope"]["prs"],[1639,1640,1647,1648,1645,1641])
        self.assertFalse(r["scope"]["complete_inventory"])
        self.assertEqual(len([g for g in r["frontiers"] if isinstance(g,dict)]),6)
    def test_native_full_metadata_bind_only_explicit_fields(self):
        a=self.adapter();native=json.loads(Path(os.environ["ADAPTER_NATIVE_METADATA"]).read_text())
        associations={}
        for i,row in enumerate(native["data"]["node"]["entries"]["nodes"]):
            p=row["pullRequest"];pr=p["number"];v=V["A"]
            # Synthetic metadata fields explicitly supplied; not qualification of original heads.
            p["headRef"]={"target":{"oid":p["headRefOid"],"tree":{"oid":v["tree"]},
                                      "parents":{"nodes":[],"pageInfo":{"hasNextPage":False}}}}
            u=unit("A",pr); u["id"]="canonical-"+str(pr)
            associations[pr]={k:u[k] for k in ("id","ticket","campaign","requires","provenance","evidence","eligibility","admitted")}
            associations[pr].update(content="explicit-content",resolution="explicit-resolution",
                                    inner_git_units=[{"opaque_ref":"fixture/unit-"+str(pr)}])
        r=a.native(json.dumps(native).encode(),snapshot_id="controlled-full",associations=associations,groups=[])
        self.assertIsNotNone(r["snapshot"]);self.assertTrue(all(u["ticket"] is None for u in r["snapshot"]["units"]))
        self.assertTrue(all(u["evidence"]==[] for u in r["snapshot"]["units"]))
        self.assertEqual(len(r["inner_git_units"]),6)
    def test_bounded_readonly_query_and_account_mismatch(self):
        cmd=graphql_command("controlled/repo",[1639,1640])
        text=cmd[-1]
        self.assertIn(STACK_NODE,text)
        for field in ("body","comments","diff","search(","pullRequests(","viewer","checkRuns"):
            self.assertNotIn(field,text)
        s=snap();e=self.envelope(s);e["account"]="foreign"
        with self.assertRaises(AdapterError):self.adapter().typed(json.dumps(e).encode())
        with self.assertRaises(AdapterError):graphql_command("controlled/repo",[])
    def test_incremental_projection_new_encounter_no_inventory_active_obligations(self):
        projection=json.loads(Path(os.environ["ADAPTER_DEFERRAL_METADATA"]).read_text())
        s=snap(("A",));s["repo"]="lama-ai-RFQ/RFQautomation";get(s,"A")["pr"]=1230
        kinds=["stall","whole_landing","required_closure","conservation_failure","cloud_demo"]
        s["violations"]=[{"unit":"A","kind":k,"obligation":"active/"+k,"evidence_ref":"fixture/active"} for k in kinds]
        r=apply_on_encounter(CORE,s,projection,triggers={1230:False})
        p=CORE.plan(r["snapshot"])
        self.assertEqual([x["kind"] for x in p["problems"]],["required_closure","conservation_failure","cloud_demo"])
        new=copy.deepcopy(projection["entries"][0]);new["pull_request"]=9876
        projection["entries"].append(new)
        s=snap(("A",));s["repo"]="lama-ai-RFQ/RFQautomation";get(s,"A")["pr"]=9876
        r=apply_on_encounter(CORE,s,projection,triggers={9876:False})
        self.assertEqual(r["encountered"],[9876]);self.assertFalse(r["inventory_requested"])
        self.assertEqual(CORE.plan(r["snapshot"])["groups"][0]["disposition"],"DEFERRED")
        r=apply_on_encounter(CORE,s,projection,triggers={})
        self.assertEqual(r["frontiers"][0]["reason"],"reactivation-trigger-UNKNOWN")
    def test_ordinary_dotenv_provider_paths_not_blanket_secret(self):
        scope=copy.deepcopy(FIX["scope"])
        scope["paths"].append({"path":"dotenv/provider/model.py","body_admitted":True,
                              "policy_ref":"Root1370/ordinary-source","role":"ORDINARY_PROGRAM"})
        s=snap(("A",));p=GitProbe(CORE,self.area/"roles")
        _,names=p.preflight(s,["A"],"ordered",V["Main"],scope)
        self.assertIn("dotenv/provider/model.py",names)

    def test_fixed_curated_packet_kept_opaque_and_unqualified(self):
        native=self.adapter().native(Path(os.environ["ADAPTER_NATIVE_METADATA"]).read_bytes(),
                                     snapshot_id="fixed",associations={},groups=[])
        packet=exact_json(Path(os.environ["ADAPTER_CURATED_METADATA"]).read_bytes())
        result=fixed_packet_binding(native,packet)
        self.assertEqual(result["inner_source_purposes"]["1647"],
                         "CLOUD809 406c42539022044defc45fe334262ed21d3775a7")
        self.assertEqual(result["source_validity"],"UNKNOWN")
        self.assertEqual(result["signature_validity"],"UNKNOWN")
        self.assertTrue(result["prior_only"])
    def test_new_deferral_entry_active_cloud_closure_still_alerts(self):
        projection=json.loads(Path(os.environ["ADAPTER_DEFERRAL_METADATA"]).read_text())
        new=copy.deepcopy(projection["entries"][0]);new["pull_request"]=9876
        projection["entries"].append(new)
        s=snap(("A",));s["repo"]="lama-ai-RFQ/RFQautomation";get(s,"A")["pr"]=9876
        s["violations"]=[{"unit":"A","kind":k,"obligation":"existing/"+k,"evidence_ref":"fixture/active"}
                         for k in ("stall","cloud_demo","required_closure","conservation_failure")]
        r=apply_on_encounter(CORE,s,projection,triggers={9876:False})
        problems=CORE.plan(r["snapshot"])["problems"]
        self.assertEqual([x["kind"] for x in problems],["cloud_demo","required_closure","conservation_failure"])
        self.assertEqual(problems[0]["reason"],"existing/cloud_demo")
        self.assertEqual(sum(x["reason"]=="existing/cloud_demo" for x in problems),1)
        self.assertEqual(r["critical_policy_bridge"],"NONE_corrected_core_retains_active_obligations_once")

class MockBoardTransport:
    """Mocked external subprocess only. Raw fixture envelopes persist before decoder."""
    def __init__(self,path,code=0,state="queued",timeout=False):
        self.path=path;self.calls=[];self.code=code;self.state=state;self.timeout=timeout
    def run(self,argv,*,env):
        self.calls.append(argv);n=len(self.calls)
        text=("91\nboard="+BOARD+" thread=91 post=91 "+
              " ".join(k+"="+str(int(k==self.state)) for k in STATES[:-1])+
              "\nnotices: "+BOARD+"#37="+self.state+"\n").encode()
        record(self.path/("mock-%d-launch.json"%n),{"argv":argv,"env":env,"external_transport":"MOCK"})
        private_write(self.path/("mock-%d-stdout.bin"%n),text)
        private_write(self.path/("mock-%d-stderr.bin"%n),b"")
        r={"exit_code":self.code,"timed_out":self.timeout,"launch_error":None,"stdout":text,"stderr":b""}
        record(self.path/("mock-%d-result.json"%n),{k:v for k,v in r.items() if k not in ("stdout","stderr")})
        return r
class BoardBehavior(OwnedTest):
    actor="10000000-0000-4000-8000-000000000001"
    def sender(self,transport):
        return BoardSender(CORE,home="/parent/actual-existing-home",sender=self.actor,current_actor=self.actor,
                           transport=transport,evidence_dir=self.area,
                           runtime_env={"PATH":"/usr/bin:/bin","CODEX_SESSION_ID":self.actor})
    def alert(self,check="tick"):
        s=snap(("A",));return s,CORE.alerts(s,CORE.plan(s),check)[0]
    def assessment(self):
        s,a=self.alert()
        anchor={"board":BOARD,"recipient":RECIPIENT,"sender":self.actor,
                "check_id":a["check_id"],"alert_id":a["alert_id"],"started_at":"2026-11-02T01:00:00Z"}
        queued={"core_receipt":{"stage":"ENQUEUED","board":BOARD,"recipient":RECIPIENT,"notification_id":37},
                "post_id":91,"thread_id":91}
        common={"board":BOARD,"recipient":RECIPIENT,"check_id":a["check_id"],"alert_id":a["alert_id"],
                "notification_id":37,"post_id":91,"thread_id":91,"admitted":True,"evidence_ref":"fixture/QA"}
        qa=dict(common,announced_at="2026-11-02T00:59:59Z",recipient_reply_verified=True)
        push=dict(common,kind="model_arrival",arrival_mode="native_push",arrived_at="2026-11-02T01:00:01Z",
                  queue_message_id="fixture-q1")
        reply=dict(common,author=RECIPIENT,reply_post_id=92,arrival_mode="native_push",created_at="2026-11-02T01:00:29Z")
        return anchor,queued,qa,push,reply
    def test_normal_mocked_CLI_queue_is_only_enqueued(self):
        s,a=self.alert();t=MockBoardTransport(self.area)
        r=self.sender(t)(a)
        self.assertEqual(r["stage"],"ENQUEUED")
        self.assertNotIn("queue_message_id",r)
        argv=t.calls[0];self.assertIn("open",argv);self.assertIn("--to",argv)
        self.assertNotIn("--resume",argv);self.assertNotIn("--no-push",argv)
        self.assertEqual(json.loads(argv[argv.index("--text")+1]),a)
    def test_ack_notice_is_not_recipient_pushed_ACK(self):
        s,a=self.alert();t=MockBoardTransport(self.area,state="acknowledged")
        self.assertEqual(self.sender(t)(a)["stage"],"ENQUEUED")
        anchor,q,qa,push,reply=self.assessment()
        receipt,result=delivery_receipt(CORE,q,anchor,qa_receipt=qa,observed_at="2026-11-02T01:00:30Z")
        self.assertEqual(receipt["stage"],"ENQUEUED");self.assertEqual(result["verdict"],"FAIL")
    def test_distinct_checks_repeat_same_check_ambiguity_no_retry(self):
        s,a=self.alert("tick1");t=MockBoardTransport(self.area,code=1,timeout=True);send=self.sender(t)
        with CORE.owner_lock(self.area/"owner.lock",RECIPIENT):
            j=CORE.DeliveryJournal(self.area/"journal.json")
            for tick in ("tick1","tick1","tick2"):
                notices=CORE.alerts(s,CORE.plan(s),tick)
                row=j.deliver(tick,notices,CORE.plan(s)["plan_id"],send)
                self.assertEqual(row["state"],"AMBIGUOUS")
        self.assertEqual(len(t.calls),2)
    def test_healthy_silent_and_two_unchanged_active_checks_enqueued(self):
        s,a=self.alert();s["groups"]=[]
        t=MockBoardTransport(self.area);send=self.sender(t)
        with CORE.owner_lock(self.area/"owner.lock",RECIPIENT):
            j=CORE.DeliveryJournal(self.area/"journal")
            self.assertEqual(j.deliver("healthy",[],CORE.plan(s)["plan_id"],send)["state"],"SILENT")
            s,a=self.alert()
            for tick in ("one","two"):
                self.assertEqual(j.deliver(tick,CORE.alerts(s,CORE.plan(s),tick),
                                          CORE.plan(s)["plan_id"],send)["state"],"ENQUEUED")
        self.assertEqual(len(t.calls),2)
    def test_mocked_pushed_ACK_29s_PASS_separate_from_queue(self):
        anchor,q,qa,push,reply=self.assessment()
        receipt,result=delivery_receipt(CORE,q,anchor,provider_push=push,recipient_reply=reply,
                                       qa_receipt=qa,observed_at="2026-11-02T01:00:30Z")
        self.assertEqual(receipt["stage"],"RECIPIENT_ACK");self.assertEqual(result["verdict"],"PASS")
        self.assertEqual(result["elapsed_seconds"],29)
        self.assertEqual(anchor["started_at"],"2026-11-02T01:00:00Z")
    def test_mocked_push_only_manual_boardwatch_ACK_fails(self):
        anchor,q,qa,push,reply=self.assessment()
        reply.update(arrival_mode="boardwatch_read",ack=True)
        receipt,result=delivery_receipt(CORE,q,anchor,provider_push=push,recipient_reply=reply,
                                       qa_receipt=qa,observed_at="2026-11-02T01:00:30Z")
        self.assertEqual(receipt["stage"],"PUSHED");self.assertEqual(result["verdict"],"FAIL")
        self.assertIn("manual",result["reason"])
    def test_mocked_late_ACK_FAIL_not_backdated(self):
        anchor,q,qa,push,reply=self.assessment();reply["created_at"]="2026-11-02T01:00:31Z"
        receipt,result=delivery_receipt(CORE,q,anchor,provider_push=push,recipient_reply=reply,
                                       qa_receipt=qa,observed_at="2026-11-02T01:00:32Z")
        self.assertEqual(receipt["stage"],"PUSHED");self.assertEqual(result["verdict"],"FAIL")
        self.assertEqual(result["reason"],"actual-recipient-ACK-late")
    def test_mocked_identity_wrong_author_future_time_or_queue_push_rejected(self):
        for variant in ("author","check","future","queue","announcement"):
            anchor,q,qa,push,reply=self.assessment()
            if variant=="author":reply["author"]=self.actor
            elif variant=="check":reply["check_id"]="foreign"
            elif variant=="future":reply["created_at"]="2026-11-02T01:00:40Z"
            elif variant=="queue":push["kind"]="queue_acceptance"
            else:qa["announced_at"]="2026-11-02T01:00:10Z"
            with self.assertRaises(AdapterError):
                delivery_receipt(CORE,q,anchor,provider_push=push,recipient_reply=reply,
                                 qa_receipt=qa,observed_at="2026-11-02T01:00:30Z")
    def test_command_reply_valid_and_no_shell_injection_or_foreign_actor(self):
        s,a=self.alert();a["reason"]="literal $(touch /never); quote '"
        argv=board_argv(CORE,a,home="/parent/home",sender=self.actor,current_actor=self.actor,
                        thread={"id":91,"opener":self.actor,"recipient":RECIPIENT,"board":BOARD})
        self.assertIn("reply",argv);self.assertNotIn("--to",argv);self.assertIn("--cc",argv)
        self.assertEqual(json.loads(argv[argv.index("--text")+1]),a)
        with self.assertRaises(AdapterError):
            board_argv(CORE,a,home="/parent/home",sender=self.actor,current_actor=RECIPIENT)
    def test_core_receipt_reconcile_no_send_and_no_regression(self):
        anchor,q,qa,push,reply=self.assessment()
        s,a=self.alert();t=MockBoardTransport(self.area)
        with CORE.owner_lock(self.area/"owner.lock",RECIPIENT):
            j=CORE.DeliveryJournal(self.area/"journal")
            j.deliver("tick",[a],CORE.plan(s)["plan_id"],self.sender(t))
            receipt,result=delivery_receipt(CORE,q,anchor,provider_push=push,recipient_reply=reply,
                                          qa_receipt=qa,observed_at="2026-11-02T01:00:30Z")
            self.assertEqual(j.reconcile("tick",a["alert_id"],receipt)["state"],"RECIPIENT_ACK")
            with self.assertRaises(CORE.Invalid):j.reconcile("tick",a["alert_id"],q["core_receipt"])
        self.assertEqual(len(t.calls),1)
    def test_actual_reply_normal_decoder_and_ambiguous_output(self):
        text=("95\\nboard="+BOARD+" thread=91 post=95 "+
              " ".join(k+"="+str(int(k=="queued")) for k in STATES[:-1])+
              "\\nnotices: "+BOARD+"#38=queued\\n").replace("\\n","\n").encode()
        result={"stdout":text,"stderr":b"","exit_code":0,"timed_out":False}
        r=decode_normal_cli(result,command="reply",expected_thread=91)
        self.assertEqual(r["post_id"],95);self.assertEqual(r["core_receipt"]["notification_id"],38)
        for raw in (text+b"extra\n",text.replace(b"#38=queued",b"#38=pending"),
                    text.replace(b"#38=queued",b"#38=queued "+BOARD.encode()+b"#39=queued")):
            with self.assertRaises(AdapterError):
                decode_normal_cli(dict(result,stdout=raw),command="reply",expected_thread=91)
    def test_independent_QA_push_receipt_path_without_provider_assertion(self):
        anchor,q,qa,push,reply=self.assessment()
        qa.update(independent_model_push_observed=True,arrival_mode="native_push",
                  arrived_at="2026-11-02T01:00:02Z",queue_message_id="fixture-qa-q")
        r,a=delivery_receipt(CORE,q,anchor,qa_receipt=qa,recipient_reply=reply,
                             observed_at="2026-11-02T01:00:30Z")
        self.assertEqual(r["stage"],"RECIPIENT_ACK");self.assertEqual(a["verdict"],"PASS")

    def test_full_existing_feed_core_journal_mocked_sender_bridge(self):
        s,a=self.alert()
        feed=FeedAdapter(CORE,account="fixture-account",binding="fixture-existing",
                         repo="controlled/repo",capture_dir=self.area)
        raw=json.dumps({"schema":"branch-source-envelope/v1","account":"fixture-account",
             "binding":"fixture-existing","event_ids":[],"scope":{"prs":[100],"complete_inventory":False},
             "snapshot":s}).encode()
        typed=feed.typed(raw);transport=MockBoardTransport(self.area);send=self.sender(transport)
        for tick in ("bridge1","bridge2"):
            result=check_once(CORE,typed,journal_path=self.area/"canonical-journal",
                 lock_path=self.area/"canonical-lock",owner=RECIPIENT,check_id=tick,sender=send)
            self.assertEqual(result["delivery"]["state"],"ENQUEUED")
            self.assertEqual(result["status"],"VIOLATION")
            self.assertFalse(result["native_effects"])
        self.assertEqual(len(transport.calls),2)
        r=check_once(CORE,dict(typed,snapshot=None,frontiers=["missing-tree"]),
                 journal_path=self.area/"canonical-journal",lock_path=self.area/"canonical-lock",
                 owner=RECIPIENT,check_id="missing",sender=send)
        self.assertEqual(r["status"],"UNKNOWN");self.assertEqual(len(transport.calls),2)

class Controls(OwnedTest):
    def test_kernel_RO_masks_private_dev_and_Python(self):
        self.assertEqual((sys.flags.isolated,sys.flags.no_site,sys.dont_write_bytecode),(1,1,True))
        null=os.stat("/dev/null")
        self.assertTrue(stat.S_ISCHR(null.st_mode));self.assertEqual((os.major(null.st_rdev),os.minor(null.st_rdev)),(1,3))
        for literal in json.loads(os.environ["ADAPTER_RESERVED_MASKS"]):
            self.assertEqual(list(Path(literal).iterdir()),[])
            with self.assertRaises(OSError):Path(literal).joinpath("no-write").write_text("no")
        for literal in [__file__,os.environ["ADAPTER_CORE_SOURCE"],os.environ["ADAPTER_NATIVE_METADATA"]]:
            with self.assertRaises(OSError):
                with open(literal,"ab") as f:f.write(b"no")
if __name__=="__main__":
    suite=unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    record(R/"test-summary.json",{"run":result.testsRun,"failures":len(result.failures),"errors":len(result.errors),
                                "skipped":len(result.skipped),"success":result.wasSuccessful()})
    raise SystemExit(0 if result.wasSuccessful() else 1)

