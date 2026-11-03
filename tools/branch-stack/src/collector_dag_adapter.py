"""Additive existing-collector -> FeedAdapter -> check_once foreground integration.

This is a deliberately selected partial contract, not an accepted global feed.
It consumes only neutral frozen observations and parent-owned canonical bindings.
No API/Git/board/scheduler invocation occurs here.
"""
from __future__ import annotations
from dataclasses import dataclass
from copy import deepcopy
from datetime import datetime, timezone
import json
from adapter_support import need, BOARD, RECIPIENT
import re
from board_receipt_adapter import stamp
from feed_adapter import FeedAdapter, DEFERRAL_V1
from adapter_runtime import check_once

CONTRACT="existing-collector-dag/v1"
PRODUCER="/home/nes/.local/share/rfq-root-emergency-captures/01a1276d-c325-7c01-a079-ca1fbea2a3f4/20261030/Install-Work-board-monitors-using-allowed-dot-codex3-profile-20261101"
ACCOUNT={"session":RECIPIENT,"role":"branch-coordinator","profile":".codex4","board":BOARD}
FACETS=frozenset(("exact_versions","ordered_parents","physical_bases","logical_associations",
                  "logical_dependencies","eligibility","landed_mapping","evidence","scope"))
NATIVE_NODE="PRS_kwDOOtFmdM4ALB_v"

@dataclass(frozen=True)
class OwnerBindings:
    """Explicit independently bound scope facts; JSON cannot authenticate itself.

    envelope is the existing branch-source-envelope/v1. Snapshot time and coverage
    attest each required facet of this exact scope, not a global branch inventory.
    """
    envelope: dict
    observed_at: str
    field_coverage: dict
    source_owner: str
    binding_ref: str
    bundle_id: str
    main_version: dict | None = None

def freshness(at, now, threshold):
    need(type(threshold) in (int,float) and 0 < threshold <= 3600, "bounded-freshness-threshold")
    try:
        age=(stamp(now)-stamp(at)).total_seconds()
        return {"observed_at":at,"age_seconds":age,"threshold_seconds":threshold,
                "state":"FRESH" if 0<=age<=threshold else "UNKNOWN"}
    except (ValueError,TypeError,AttributeError):
        return {"observed_at":None,"age_seconds":None,"threshold_seconds":threshold,"state":"UNKNOWN"}

def normalize_native_observation(core, observation):
    """Bind the actual timestamped six-PR query format to the existing decoder.

    The independent query rows supply state/tree/ordered parents. Native order
    supplies physical membership only. All head/ref/base facts must agree.
    """
    core.fields(observation,("schema","producer_session","profile","role","repo",
        "acquisition_start","acquisition_end","actual_native_exit","query","data",
        "no_source_bodies","no_CI","no_logical_dependency_or_semantic_or_atomic_snapshot_claim",
        "source"))
    need(observation["schema"]=="bounded-existing-six-native-structural-observation/1"
         and observation["producer_session"]==ACCOUNT["session"]
         and observation["profile"]==ACCOUNT["profile"] and observation["role"]==ACCOUNT["role"]
         and observation["repo"]=="lama-ai-RFQ/RFQautomation"
         and type(observation["actual_native_exit"]) is int and observation["actual_native_exit"]==0,
         "normal-native-producer-binding")
    for k in ("no_source_bodies","no_CI","no_logical_dependency_or_semantic_or_atomic_snapshot_claim"):
        need(observation[k] is True,"structural-only-source-contract")
    def source_stamp(value):
        need(type(value) is str,"normal-native-source-UTC")
        return datetime.strptime(value,"%Y-%m-%d %H:%M:%S UTC").replace(tzinfo=timezone.utc)
    need(type(observation["query"]) is str and type(observation["source"]) is str,
         "normal-native-structural-query-carrier")
    start=source_stamp(observation["acquisition_start"])
    end=source_stamp(observation["acquisition_end"])
    need(0<=(end-start).total_seconds()<=300,"normal-native-source-window")
    data=observation["data"];core.fields(data,("repository","node"))
    repo=data["repository"];prs=(1639,1640,1647,1648,1645,1641)
    core.fields(repo,("defaultBranchRef",)+tuple("p"+str(p) for p in prs))
    node=deepcopy(data["node"])
    core.fields(node,("id","number","size","baseRefName","entries"))
    need(node["id"]==NATIVE_NODE and node["number"]==1649 and node["size"]==6,
         "normal-native-six-membership")
    core.fields(node["entries"],("nodes","pageInfo"))
    core.fields(node["entries"]["pageInfo"],("hasNextPage",))
    need(node["entries"]["pageInfo"]["hasNextPage"] is False,"normal-native-membership-complete")
    rows=node["entries"]["nodes"]
    need(type(rows) is list and len(rows)==6,"normal-native-six-rows")
    for index,(number,row) in enumerate(zip(prs,rows),1):
        core.fields(row,("position","pullRequest"))
        need(row["position"]==index,"normal-native-ordered-position")
        n=row["pullRequest"]
        core.fields(n,("number","headRefOid","headRefName","baseRefName"),("state","isDraft"))
        p=repo["p"+str(number)]
        core.fields(p,("number","state","isDraft","headRefName","headRefOid","baseRefName","headRef"),("baseRefOid","stack"))
        need(n["number"]==p["number"]==number
             and all(n[k]==p[k] for k in ("headRefOid","headRefName","baseRefName")),
             "normal-native-ref-head-base-CAS")
        need(all(n[k]==p[k] for k in ("state","isDraft") if k in n),
             "normal-native-state-draft-CAS")
        row["pullRequest"]=deepcopy(p)
    packet={"data":{"repository":{"defaultBranchRef":deepcopy(repo["defaultBranchRef"])},
                    "node":node}}
    _validate_native(core,packet)
    commits=[packet["data"]["repository"]["defaultBranchRef"]["target"]]
    commits.extend(r["pullRequest"]["headRef"]["target"] for r in rows)
    for c in commits:
        need(set(c)=={"oid","tree","parents"},"normal-native-full-commit-metadata")
        core.fields(c["parents"],("nodes","pageInfo"))
        core.fields(c["parents"]["pageInfo"],("hasNextPage",))
        need(c["parents"]["pageInfo"]["hasNextPage"] is False,"normal-native-ordered-parents-complete")
    return {"packet":packet,"observed_at":end.isoformat(),
            "source_receipt":{"producer_session":observation["producer_session"],
                "profile":observation["profile"],"role":observation["role"],"repo":observation["repo"],
                "acquisition_start":start.isoformat(),"acquisition_end":end.isoformat(),
                "actual_native_exit":0,"source_utc_origin":"producer-query-acquisition-end",
                "observation_id":core.digest(observation),"packet_id":core.digest(packet),
                "logical_dependencies":"UNKNOWN","atomic_snapshot":"NOT_CLAIMED"}}

def _validate_native(core, packet):
    core.fields(packet, ("data",))
    d=packet["data"]; core.fields(d,("repository","node"))
    core.fields(d["repository"],("defaultBranchRef",))
    main=d["repository"]["defaultBranchRef"]; core.fields(main,("name","target"))
    def commit(c):
        core.fields(c,("oid",),("tree","parents"))
        core.oid(c["oid"])
        if "tree" in c:
            core.fields(c["tree"],("oid",)); core.oid(c["tree"]["oid"])
        if "parents" in c:
            parents=c["parents"]; core.fields(parents,("nodes",),("pageInfo",))
            need(type(parents["nodes"]) is list and len(parents["nodes"])<=32,
                 "bounded-ordered-parents")
            for row in parents["nodes"]:
                core.fields(row,("oid",)); core.oid(row["oid"])
            if "pageInfo" in parents:
                core.fields(parents["pageInfo"],("hasNextPage",))
                need(type(parents["pageInfo"]["hasNextPage"]) is bool,"typed-parent-pagination")
    commit(main["target"])
    n=d["node"]; core.fields(n,("id","number","size","baseRefName","entries"))
    core.token(n["baseRefName"])
    core.fields(n["entries"],("nodes",),("pageInfo",))
    if "pageInfo" in n["entries"]:
        core.fields(n["entries"]["pageInfo"],("hasNextPage",))
        need(n["entries"]["pageInfo"]["hasNextPage"] is False,"native-membership-pagination-UNKNOWN")
    need(type(n["size"]) is int and type(n["entries"]["nodes"]) is list,"typed-native-membership")
    for row in n["entries"]["nodes"]:
        core.fields(row,("position","pullRequest"))
        need(type(row["position"]) is int,"typed-native-position")
        pr=row["pullRequest"]
        core.fields(pr,("number","state","isDraft","headRefName","headRefOid","baseRefName"),
                    ("headRef","baseRefOid","stack"))
        if "baseRefOid" in pr: core.oid(pr["baseRefOid"])
        if "stack" in pr and pr["stack"] is not None:
            core.fields(pr["stack"],("id","number"))
            need(pr["stack"]=={"id":NATIVE_NODE,"number":1649},"native-stack-membership-CAS")
        if "headRef" in pr and pr["headRef"] is not None:
            core.fields(pr["headRef"],("target",)); commit(pr["headRef"]["target"])
            need(pr["headRef"]["target"]["oid"]==pr["headRefOid"],"native-head-target-CAS")

def _validate_acquisition(core,a):
    core.fields(a,("latest","health","commands","frontiers"))
    if a["commands"] is not None:
        c=a["commands"]
        core.fields(c,("category","check_id","code_version","count","execution_authority"))
        need(c["category"]=="branches" and c["execution_authority"] is False,
             "command-content-outside-structural-contract")
        for k in ("check_id","code_version"): core.token(c[k])
        need(type(c["count"]) is int and 0<=c["count"]<=10000,"bounded-command-count")
    need(type(a["frontiers"]) is list and all(type(x) is str and
         x in ("latest-input-UNKNOWN","health-input-UNKNOWN","commands-input-UNKNOWN",
               "initial-projection-omitted-branch-rows-UNKNOWN") for x in a["frontiers"]),
         "bounded-known-acquisition-frontiers")
    if a["latest"] is not None:
        x=a["latest"]; core.fields(x,("check_id","code_version","checked_at","source_failures",
                                      "coverage","rows","complete_inventory"),("source_errors",))
        for k in ("check_id","code_version"): core.token(x[k])
        stamp(x["checked_at"]); need(x["complete_inventory"] is False,"bounded-observation-scope")
        need(type(x["source_failures"]) is int and x["source_failures"]>=0,"typed-source-failures")
        need(type(x["coverage"]) is list and type(x["rows"]) is list,"typed-neutral-lists")
        for e in x.get("source_errors",[]):
            core.fields(e,("source","state"));
            from collector_observations import label
            label(e["source"]);core.token(e["state"])
        for c in x["coverage"]:
            core.fields(c,("repo","remote_live_refs","remote_live_state","local_registry"))
            for k in ("repo","remote_live_state","local_registry"): core.token(c[k])
            need(type(c["remote_live_refs"]) is int and c["remote_live_refs"]>=0,"typed-ref-count")
        for row in x["rows"]:
            core.fields(row,("category","repo","branch","age_seconds","distinct_heads","heads","prs"),("activity",))
            if "activity" in row:
                need(type(row["activity"]) in (int,float) and 0<=row["activity"]<1e15,"typed-row-activity")
            need(row["category"] in ("selected","pending_review_excluded","stale_alerts"),"known-category")
            for k in ("repo","branch"): core.token(row[k])
            need(type(row["age_seconds"]) in (int,float) and 0<=row["age_seconds"]<1e15,"typed-age")
            need(type(row["distinct_heads"]) is list and type(row["heads"]) is list
                 and type(row["prs"]) is list,"typed-row-lists")
            for v in row["distinct_heads"]: core.oid(v)
            for h in row["heads"]:
                core.fields(h,("oid","activity")); core.oid(h["oid"])
                need(type(h["activity"]) in (int,float) and 0<=h["activity"]<1e15,"typed-activity")
            for pr in row["prs"]:
                core.fields(pr,("number","head","branch","repo")); core.oid(pr["head"])
                need(type(pr["number"]) is int and pr["number"]>0,"typed-PR-number")
                for k in ("branch","repo"): core.token(pr[k])
    if a["health"] is not None:
        x=a["health"]; core.fields(x,("check_id","code_version","started_at","ended_at","source_state",
              "source_failures","numeric_exit","queue_accepted","recipient_acknowledged",
              "actual_board_notice","delivery_stage"))
        for k in ("check_id","code_version","source_state"): core.token(x[k])
        need(stamp(x["ended_at"])>=stamp(x["started_at"]),"health-time-order")
        need(x["delivery_stage"]=="UNKNOWN_MODEL_RECEIPT_NOT_ACQUIRED","no-model-receipt-from-health")
        for k in ("source_failures","numeric_exit"):
            need(type(x[k]) is int and x[k]>=0,"typed-health-count")
        for k in ("queue_accepted","recipient_acknowledged","actual_board_notice"):
            need(type(x[k]) is bool,"typed-health-Boolean")

def freeze_bundle(core, *, account, producer, repo, binding, acquisition, native_packet,
                  native_observed_at, acquired_at):
    need(account==ACCOUNT and producer==PRODUCER,"parent-bound-account-producer-context")
    for v in (repo,binding): core.token(v)
    stamp(acquired_at)
    need(len(json.dumps({"acquisition":acquisition,"native_packet":native_packet}).encode())<=2*1024**2,
         "bounded-neutral-input-budget")
    # Native metadata is a separate bounded observation, never logical dependencies.
    _validate_native(core,native_packet)
    _validate_acquisition(core,acquisition)
    n=native_packet["data"]["node"]
    need(n["id"]==NATIVE_NODE and n["number"]==1649 and n["size"]<=100,
         "one-accepted-stack-only")
    rows=n["entries"]["nodes"]
    need(len(rows)==n["size"] and [r["position"] for r in rows]==list(range(1,len(rows)+1)),
         "exact-native-membership-order")
    need(len({r["pullRequest"]["number"] for r in rows})==len(rows),"unique-native-PR")
    main=native_packet["data"]["repository"]["defaultBranchRef"]
    need(main["name"]=="main","exact-Main-ref")
    core.oid(main["target"]["oid"])
    known=[]
    for r in rows:
        pr=r["pullRequest"]
        need(type(pr["number"]) is int and pr["number"]>0 and pr["state"] in ("OPEN","CLOSED","MERGED")
             and type(pr["isDraft"]) is bool,"typed-native-state")
        for k in ("headRefName","baseRefName"): core.token(pr[k])
        core.oid(pr["headRefOid"])
        known.append({"position":r["position"],**{k:deepcopy(pr[k]) for k in
                     ("number","state","isDraft","headRefName","headRefOid","baseRefName")}})
    # Full native packet is positively admitted structural metadata only. Source
    # associations, active eligibility, trees etc are never manufactured from it.
    b={"schema":CONTRACT,"account":deepcopy(account),"producer":producer,"repo":repo,
       "binding":binding,"acquired_at":acquired_at,"acquisition":deepcopy(acquisition),
       "native_packet":deepcopy(native_packet),"native_observed_at":native_observed_at,
       "native_known":known,"complete_inventory":False}
    b["snapshot_id"]=core.digest(b)
    return b

def validate_bundle(core,b,*,account,repo,binding,expected_snapshot_id):
    core.fields(b,("schema","account","producer","repo","binding","acquired_at","acquisition",
                   "native_packet","native_observed_at","native_known","complete_inventory","snapshot_id"))
    need(b["schema"]==CONTRACT and account==b["account"]==ACCOUNT and b["producer"]==PRODUCER
         and b["repo"]==repo and b["binding"]==binding and b["complete_inventory"] is False,
         "collector-account-repository-capability-binding")
    unsigned={k:v for k,v in b.items() if k!="snapshot_id"}
    need(core.digest(unsigned)==b["snapshot_id"]==expected_snapshot_id,"frozen-snapshot-CAS")
    # Rebuild validates the neutral/native contract rather than trusting a digest.
    rebuilt=freeze_bundle(core,account=account,producer=b["producer"],repo=repo,binding=binding,
              acquisition=b["acquisition"],native_packet=b["native_packet"],
              native_observed_at=b["native_observed_at"],acquired_at=b["acquired_at"])
    need(rebuilt==b,"native-neutral-projection-binding")

def field_records(core,b,now,max_age):
    """Every projected leaf gets exact neutral-source/snapshot/time/coverage provenance."""
    out={}
    latest=b["acquisition"].get("latest")
    roots={"native_packet":(b["native_packet"],b["native_observed_at"],"PRIOR_STRUCTURAL_ONLY"),
           "native_known":(b["native_known"],b["native_observed_at"],"PRIOR_STRUCTURAL_ONLY")}
    if latest is not None: roots["latest"]=(latest,latest["checked_at"],"ON_ENCOUNTER_PARTIAL")
    health=b["acquisition"].get("health")
    if health is not None: roots["health"]=(health,health["ended_at"],"PRODUCER_HEALTH_NOT_DAG_COVERAGE")
    def visit(v,path,at,coverage):
        if isinstance(v,dict):
            for k,x in v.items(): visit(x,path+"/"+k,at,coverage)
        elif isinstance(v,list):
            for i,x in enumerate(v): visit(x,path+"/"+str(i),at,coverage)
        else:
            out[path]={"producer":b["producer"],"account":b["account"]["session"],
                       "repo":b["repo"],"snapshot_id":b["snapshot_id"],"coverage":coverage,
                       **freshness(at,now,max_age)}
    for key,(v,at,cov) in roots.items(): visit(v,key,at,cov)
    return out

def owner_field_records(core,bundle,owner,now,max_age,qualified):
    records={}
    def visit(value,path):
        if isinstance(value,dict):
            for k,v in value.items(): visit(v,path+"/"+k)
        elif isinstance(value,list):
            for i,v in enumerate(value): visit(v,path+"/"+str(i))
        else:
            fresh=freshness(owner.observed_at,now,max_age)
            if not qualified: fresh["state"]="UNKNOWN"
            records[path]={"producer":owner.source_owner,"binding_ref":owner.binding_ref,
                "account":bundle["account"]["session"],"repo":bundle["repo"],
                "snapshot_id":bundle["snapshot_id"],
                "coverage":"QUALIFIED_EXPLICIT_OWNER_SCOPE" if qualified else "UNQUALIFIED_OWNER_SCOPE",
                **fresh}
    visit(owner.envelope["snapshot"],"owner_snapshot")
    return records

def translate(core,bundle,*,account,repo,binding,expected_snapshot_id,now,capture_dir,
              max_age=300,owner_bindings=None,expected_code_version=None):
    """Return a validated full explicit scope OR typed partial metadata + frontiers.

    A separate fresh owner envelope may cover a bounded subset while unrelated
    collector inputs remain UNKNOWN. Known active violations stay in that graph.
    """
    validate_bundle(core,bundle,account=account,repo=repo,binding=binding,
                    expected_snapshot_id=expected_snapshot_id)
    feed=FeedAdapter(core,account=account["session"],binding=binding,repo=repo,capture_dir=capture_dir)
    native=feed.native(json.dumps(bundle["native_packet"]).encode(),
                       snapshot_id=bundle["snapshot_id"],associations={},groups=[])
    gaps=list(bundle["acquisition"].get("frontiers",[]))
    latest=bundle["acquisition"].get("latest"); health=bundle["acquisition"].get("health")
    if latest is None: gaps.append("collector-latest-structural-projection-missing-UNKNOWN")
    else:
        if expected_code_version is None or latest["code_version"]!=expected_code_version:
            gaps.append("collector-code-version-unbound-UNKNOWN")
        if freshness(latest["checked_at"],now,max_age)["state"]!="FRESH":
            gaps.append("collector-observation-stale-or-future-UNKNOWN")
        if latest["source_failures"]: gaps.append("collector-source-failures-UNKNOWN")
        if (len(latest["coverage"])!=1 or latest["coverage"][0]["repo"]!=repo
            or latest["coverage"][0]["remote_live_state"] not in ("OK","READ")):
            gaps.append("encountered-repository-coverage-UNKNOWN")
    if health is None: gaps.append("collector-health-UNKNOWN")
    elif (latest is None or health["check_id"]!=latest["check_id"]
          or health["code_version"]!=latest["code_version"]
          or freshness(health["ended_at"],now,max_age)["state"]!="FRESH"
          or health["source_failures"] or health["numeric_exit"] or health["source_state"] not in ("OK","OBSERVED")):
        gaps.append("collector-health-generation-or-freshness-UNKNOWN")
    commands=bundle["acquisition"].get("commands")
    if commands is not None and (latest is None or
            any(commands[k]!=latest[k] for k in ("check_id","code_version"))):
        gaps.append("collector-commands-generation-CAS-UNKNOWN")
    if freshness(bundle["native_observed_at"],now,max_age)["state"]!="FRESH":
        gaps.append("native-prior-read-current-freshness-UNKNOWN")
    partial=deepcopy(native)
    partial.update(known_metadata=deepcopy(bundle["native_known"]),
                   field_provenance=field_records(core,bundle,now,max_age),
                   neutral_snapshot_id=bundle["snapshot_id"],complete_graph=False,
                   main_structure=deepcopy(bundle["native_packet"]["data"]["repository"]["defaultBranchRef"]),
                   retained_known_active_violations=[],qualified_scope=None)
    # Incomplete physical structure never invokes a Source/native callback.
    if owner_bindings is None:
        partial["frontiers"]=native["frontiers"]+gaps
        return partial
    o=owner_bindings
    need(isinstance(o,OwnerBindings) and o.bundle_id==bundle["snapshot_id"],"owner-to-frozen-bundle-CAS")
    for v in (o.source_owner,o.binding_ref): core.token(v)
    source=deepcopy(o.envelope)
    need(source["account"]==account["session"] and source["binding"]==binding,
         "explicit-owner-account-binding")
    s=source["snapshot"]; core.Graph(s)
    need(s["repo"]==repo and s["feed"]["binding"]==binding and s["feed"]["snapshot_id"]==bundle["snapshot_id"],
         "owner-snapshot-repository-identity")
    partial["retained_known_active_violations"]=deepcopy(s.get("violations",[]))
    partial["field_provenance"].update(owner_field_records(core,bundle,o,now,max_age,False))
    needed={"main"}|{str(u["pr"]) for u in s["units"]}
    if (set(o.field_coverage)!=needed or any(set(v)!=FACETS for v in o.field_coverage.values())
        or freshness(o.observed_at,now,max_age)["state"]!="FRESH"):
        partial["frontiers"]=native["frontiers"]+gaps+["canonical-owner-coverage-or-freshness-UNKNOWN"]
        return partial
    main=native["main"]
    if s["main"]!=main:
        partial["frontiers"]=native["frontiers"]+gaps+["owner-Main-structural-CAS-UNKNOWN"]
        return partial
    # Compare complete immutable metadata when available, rather than trusting
    # a second assertion for the same head. Missing metadata is not invented.
    native_main=bundle["native_packet"]["data"]["repository"]["defaultBranchRef"]["target"]
    def matches(version, target):
        if version["head"] != target["oid"]: return False
        if "tree" in target and version["tree"] != target["tree"]["oid"]: return False
        if "parents" in target:
            parents=target["parents"]
            if parents.get("pageInfo",{}).get("hasNextPage") is not False: return False
            if version["parents"] != [p["oid"] for p in parents["nodes"]]: return False
        return True
    if "tree" in native_main or "parents" in native_main:
        if o.main_version is None or not matches(o.main_version,native_main):
            partial["frontiers"]=native["frontiers"]+gaps+["owner-Main-tree-orderedparents-CAS-UNKNOWN"]
            return partial
    native_prs={r["pullRequest"]["number"]:r["pullRequest"] for r in
                bundle["native_packet"]["data"]["node"]["entries"]["nodes"]}
    known={r["number"]:r for r in bundle["native_known"]}
    refs={"main":main,**{r["headRefName"]:r["headRefOid"] for r in known.values()}}
    for u in s["units"]:
        if u["pr"] not in known:
            partial["frontiers"]=native["frontiers"]+gaps+["owner-PR-outside-encountered-scope-UNKNOWN"]
            return partial
        p=known[u["pr"]]
        # Partial native decoding has no canonical associations. Do not let
        # owner overlay erase an explicit negative skipped by that decoder.
        if "stack" in native_prs[u["pr"]] and native_prs[u["pr"]]["stack"] is None:
            partial["frontiers"]=native["frontiers"]+gaps+[{"pr":u["pr"],
                "reason":"explicit-stack-removal-inconsistent-with-entry-UNKNOWN"}]
            return partial
        # Match FeedAdapter.native: a present PR pin wins; only absence uses
        # the observed ref target. Current Main metadata remains bound above.
        base=native_prs[u["pr"]].get("baseRefOid", refs.get(p["baseRefName"]))
        if not (u["ref"]=="refs/heads/"+p["headRefName"] and u["version"]["head"]==p["headRefOid"]
             and u["native_stack"]=="1649" and u["physical_base"]["ref"]==p["baseRefName"]
             and u["physical_base"]["head"]==base):
            partial["frontiers"]=native["frontiers"]+gaps+["owner-PR-ref-head-base-membership-CAS-UNKNOWN"]
            return partial
        target=(native_prs[u["pr"]].get("headRef") or {}).get("target")
        if target is not None and not matches(u["version"],target):
            partial["frontiers"]=native["frontiers"]+gaps+["owner-PR-tree-orderedparents-CAS-UNKNOWN"]
            return partial
        if latest is not None:
            for row in latest["rows"]:
                for pr in row["prs"]:
                    if pr["number"]==u["pr"]:
                        if not (pr["repo"]==repo and pr["head"]==u["version"]["head"]
                             and "refs/heads/"+pr["branch"]==u["ref"]):
                            partial["frontiers"]=native["frontiers"]+gaps+["collector-owner-head-CAS-UNKNOWN"]
                            return partial
    # Contradictory versions and stale/future scope inputs are read-only results.
    # Missing/partial collector coverage still permits an independently fresh
    # bounded owner scope and retains every actual known violation.
    unsafe={"collector-code-version-unbound-UNKNOWN",
            "collector-observation-stale-or-future-UNKNOWN",
            "native-prior-read-current-freshness-UNKNOWN",
            "collector-commands-generation-CAS-UNKNOWN"}
    if unsafe.intersection(gaps):
        partial["frontiers"]=native["frontiers"]+gaps
        return partial
    # Parent owns arbitrary logical edges, segments, eligibility, landed mappings,
    # provenance and evidence. Native position creates none of them.
    result=feed.typed(json.dumps(source).encode())
    partial.update(result)
    partial["field_provenance"].update(owner_field_records(core,bundle,o,now,max_age,True))
    partial["scope"]["complete_inventory"]=False
    partial["qualified_scope"]={"prs":source["scope"]["prs"],"source_owner":o.source_owner,
                               "binding_ref":o.binding_ref,"observed_at":o.observed_at,
                               "field_coverage":deepcopy(o.field_coverage)}
    partial["frontiers"]=gaps+["outside-explicit-pr-scope-UNKNOWN"]
    return partial

def foreground_check(core,bundle,*,account,repo,binding,expected_snapshot_id,now,capture_dir,
                     journal_path,lock_path,owner,check_id,owner_bindings=None,sender=None,
                     max_age=300,expected_code_version=None,deferral_projection=None,
                     deferral_capability=DEFERRAL_V1,work_decision=None,work_owner=None,triggers=None):
    """One foreground occurrence; use existing owner lock/journal and injected sender.

    Unknown overall coverage cannot become healthy, but independently qualified
    known active problems remain actionable in exactly their supplied scope.
    """
    try:
        result=translate(core,bundle,account=account,repo=repo,binding=binding,
            expected_snapshot_id=expected_snapshot_id,now=now,capture_dir=capture_dir,
            max_age=max_age,owner_bindings=owner_bindings,expected_code_version=expected_code_version)
    except (ValueError,KeyError,TypeError):
        # Never expose exception/source text. Parent retains its original input.
        result={"schema":"branch-adapter-result/v1","snapshot":None,
                "frontiers":["typed-identity-version-coverage-or-CAS-rejected-UNKNOWN"]}
    runtime_result=deepcopy(result)
    runtime_result["frontiers"]=[g for g in result.get("frontiers",[]) if g!="commands-input-UNKNOWN"]
    checked=check_once(core,runtime_result,journal_path=journal_path,lock_path=lock_path,owner=owner,
                       check_id=check_id,sender=sender,deferral_projection=deferral_projection,
                       deferral_capability=deferral_capability,work_decision=work_decision,
                       work_owner=work_owner,triggers=triggers)
    if "commands-input-UNKNOWN" in result.get("frontiers",[]):
        checked.setdefault("frontiers",[]).append("commands-input-UNKNOWN")
    blocking=[g for g in checked.get("frontiers",[]) if g not in ("outside-explicit-pr-scope-UNKNOWN","commands-input-UNKNOWN")]
    if checked["status"]=="HEALTHY_WITHIN_EXPLICIT_SCOPE" and blocking:
        checked["status"]="UNKNOWN"
    checked["partial_bindings"]={k:deepcopy(result[k]) for k in
        ("main","main_structure","known_metadata","field_provenance","neutral_snapshot_id")
        if k in result}
    checked["coverage_complete"]=False
    checked["retained_known_active_violations"]=result.get("retained_known_active_violations",[])
    checked["qualified_scope"]=result.get("qualified_scope")
    checked["delivery_wake_live_qa"]="FAIL_NOT_WORKING; Work9698/notice9734_AMBIGUOUS"
    checked["account_context"]=deepcopy(account)
    return checked

def guarded_native_probe(*, capability, callback):
    """Legacy synthetic callback helper; real Git uses readonly_metadata directly."""
    if capability != "CONTROLLED_TEST_ONLY":
        return {"status":"UNKNOWN","reason":"unsupported-unbound-callback-mode",
                "callback_invoked":False}
    return callback()


def structural_query_dto(repo):
    """One unexecuted bounded read-only metadata request, not a provider capability."""
    need(re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+",repo),"literal-repository")
    owner,name=repo.split("/")
    c="oid tree { oid } parents(first:32) { nodes { oid } pageInfo { hasNextPage } }"
    prs=[1639,1640,1647,1648,1645,1641]
    f=("number state isDraft headRefName headRefOid baseRefName baseRefOid "
       "headRef { target { ... on Commit { "+c+" } } }")
    q=('query { repository(owner:'+json.dumps(owner)+',name:'+json.dumps(name)+') { '
       'defaultBranchRef { name target { ... on Commit { '+c+' } } } '+
       ' '.join('p%d:pullRequest(number:%d) { %s }'%(n,n,f) for n in prs)+
       ' } node(id:'+json.dumps(NATIVE_NODE)+') { ... on PullRequestStack { id number size '
       'baseRefName entries(first:6) { nodes { position pullRequest { number state isDraft '
       'headRefName headRefOid baseRefName } } pageInfo { hasNextPage } } } } }')
    return {"schema":"bounded-structural-query-dto/v1","method":"GraphQL_READ_ONLY",
            "repository":repo,"stack_node":NATIVE_NODE,"encountered_prs":prs,"query":q,
            "request_executed":False,"provider_schema_qualification":"UNKNOWN",
            "forbidden_acquisition":"No CI, bodies, diffs, comments, blobs or global census"}


def existing_monitor_check(core, *, latest, health, commands, native_packet,
                           native_observed_at, acquired_at, repo, binding,
                           expected_code_version, **foreground_args):
    """Callable integration for the existing producer, after its health write.

    Accept the same in-memory values it published; do not start another loop or
    execute command metadata. The caller chooses its existing lock/journal and
    bounded native facts. Unknown logical facts remain unknown.
    """
    from collector_observations import project_latest, project_health, project_commands
    native_rows=native_packet["data"]["node"]["entries"]["nodes"]
    prs={r["pullRequest"]["number"] for r in native_rows}
    refs={r["pullRequest"]["headRefName"] for r in native_rows}
    acquisition={"latest":project_latest(core,latest,repo,prs,refs),
        "health":project_health(core,health),"commands":project_commands(core,commands),"frontiers":[]}
    bundle=freeze_bundle(core,account=ACCOUNT,producer=PRODUCER,repo=repo,binding=binding,
        acquisition=acquisition,native_packet=native_packet,
        native_observed_at=native_observed_at,acquired_at=acquired_at)
    result=foreground_check(core,bundle,account=ACCOUNT,repo=repo,binding=binding,
        expected_snapshot_id=bundle["snapshot_id"],expected_code_version=expected_code_version,
        **foreground_args)
    return {"bundle":bundle,"result":result}
