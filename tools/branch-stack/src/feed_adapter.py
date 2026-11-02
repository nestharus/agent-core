"""Bounded native metadata / existing typed file-event feed adapters; no provider I/O."""
from __future__ import annotations
from copy import deepcopy
import json
import re
from adapter_support import AdapterError, need, exact_json, record, sha, BOARD, RECIPIENT

STACK_NODE = "PRS_kwDOOtFmdM4ALB_v"
STACK_ORDER = [1639, 1640, 1647, 1648, 1645, 1641]

def graphql_command(repo, prs, *, gh="/usr/bin/gh"):
    """Command DTO only. One accepted stack + Main and explicit encountered PRs."""
    need(re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo), "literal-repository")
    need(isinstance(prs, list) and 0 < len(prs) <= 100 and len(prs)==len(set(prs))
         and all(type(p) is int and p > 0 for p in prs), "bounded-explicit-pr-list")
    owner, name = repo.split("/")
    commit = "oid tree { oid } parents(first:32) { nodes { oid } pageInfo { hasNextPage } }"
    fields = ("number headRefName headRefOid baseRefName baseRefOid state "
              "merged mergedAt mergeCommit { oid } stack { id number } "
              "headRef { target { ... on Commit { " + commit + " } } }")
    pulls = " ".join("p%d:pullRequest(number:%d) { %s }" % (p,p,fields) for p in prs)
    query = ('query { repository(owner:'+json.dumps(owner)+',name:'+json.dumps(name)+') { '
             'defaultBranchRef { name target { oid } } '+pulls+' } '
             'node(id:'+json.dumps(STACK_NODE)+') { ... on PullRequestStack { id number size baseRefName '
             'entries(first:100) { nodes { position pullRequest { '+fields+' } } pageInfo { hasNextPage } } } } }')
    return [gh, "api", "graphql", "-f", "query="+query]

class FeedAdapter:
    """No invented account, Jira, canonical identity, evidence or source admission."""
    def __init__(self, core, *, account, binding, repo, capture_dir):
        for x in (account,binding,repo):
            core.token(x)
        self.core, self.account, self.binding, self.repo = core, account, binding, repo
        self.capture_dir = capture_dir
        self.sequence = 0

    def capture(self, raw, kind):
        self.sequence += 1
        obj = exact_json(raw)
        # Complete metadata producer envelope, private before bounded projection.
        record(self.capture_dir/("feed-%04d.json" % self.sequence),
               {"schema":"branch-producer-envelope/v1","producer":kind,
                "account":self.account,"binding":self.binding,"sha256":sha(raw),"payload":obj})
        return obj

    def typed(self, raw):
        e = self.capture(raw, "existing-file-event")
        self.core.fields(e, ("schema","account","binding","event_ids","scope","snapshot"))
        need(e["schema"]=="branch-source-envelope/v1", "unsupported-existing-feed-schema")
        need(e["account"]==self.account and e["binding"]==self.binding, "canonical-account-binding")
        s = deepcopy(e["snapshot"])
        need(s["repo"]==self.repo and s["feed"]["binding"]==self.binding, "feed-snapshot-binding")
        need(isinstance(e["event_ids"],list) and len(e["event_ids"])==len(s.get("events",[]))
             and len(e["event_ids"])==len(set(e["event_ids"])), "event-identity-binding")
        for identity in e["event_ids"]:
            self.core.token(identity)
        self.core.fields(e["scope"],("prs","complete_inventory"))
        need(e["scope"]["complete_inventory"] is False, "not-global-inventory-adapter")
        need(sorted(e["scope"]["prs"])==sorted(u["pr"] for u in s["units"]), "scope-exact-pr-list")
        self.core.Graph(s)  # Preserve flags and failed/unknown evidence verbatim.
        return {"schema":"branch-adapter-result/v1","snapshot":s,
                "account":self.account,"event_ids":e["event_ids"],"scope":deepcopy(e["scope"]),
                "frontiers":["outside-explicit-pr-scope-UNKNOWN"]}

    def native(self, raw, *, snapshot_id, associations, groups, segments=()):
        """Decode fixed GraphQL metadata. Missing Commit/tree/parent fields -> no core snapshot.

        associations is exact parent-supplied canonical per-PR metadata, never inferred
        from ref spelling. Inner Git-unit provenance is preserved as an outer sidecar.
        """
        e = self.capture(raw, "accepted-one-stack-Main")
        need(not e.get("errors"), "native-provider-errors")
        d = e["data"]
        main = self.core.oid(d["repository"]["defaultBranchRef"]["target"]["oid"])
        node = d["node"]
        need(node["id"]==STACK_NODE and node["number"]==1649, "accepted-stack-identity")
        entries = node["entries"]
        rows = entries["nodes"]
        need(len(rows)<=100 and len(rows)==node["size"], "native-membership-incomplete")
        need(not entries.get("pageInfo",{}).get("hasNextPage",False), "native-membership-pagination")
        need([r["position"] for r in rows]==list(range(1,len(rows)+1)), "ordered-stack-positions")
        prs = [r["pullRequest"]["number"] for r in rows]
        need(len(prs)==len(set(prs)), "singular-pr-membership")
        # Current membership may move; report the observed order, do not recreate it.
        known, units, gaps, inner = [], [], [], {}
        refs = {"main":main}
        for r in rows:
            p = r["pullRequest"]
            need(type(p["number"]) is int and p["number"]>0, "native-pr-number")
            self.core.oid(p["headRefOid"])
            self.core.token(p["headRefName"]); self.core.token(p["baseRefName"])
            refs[p["headRefName"]] = p["headRefOid"]
        for r in rows:
            p = r["pullRequest"]; pr=p["number"]
            known.append({k:deepcopy(p[k]) for k in ("number","headRefName","headRefOid","baseRefName")})
            a = associations.get(pr)
            head = p.get("headRef",{}); target=(head or {}).get("target",{})
            parents=target.get("parents")
            base = p.get("baseRefOid", refs.get(p["baseRefName"]))
            if (a is None or not target.get("tree",{}).get("oid") or parents is None
                or parents.get("pageInfo",{}).get("hasNextPage") is not False or base is None):
                gaps.append({"pr":pr,"reason":"canonical-association-tree-orderedparents-or-base-UNKNOWN"})
                continue
            need(target["oid"]==p["headRefOid"], "native-head-target-mismatch")
            if "stack" in p and p["stack"] is None:
                gaps.append({"pr":pr,"reason":"explicit-stack-removal-inconsistent-with-entry-UNKNOWN"})
                continue
            membership=p.get("stack")
            if membership is not None:
                need(membership["id"]==node["id"] and membership["number"]==1649,
                     "singular-native-stack-mismatch")
            else:
                # Old structural metadata has no stack field: membership only from entries.
                membership={"number":1649}
            version={"head":p["headRefOid"],"tree":target["tree"]["oid"],
                     "parents":[x["oid"] for x in parents["nodes"]],
                     "content":a["content"],"resolution":a["resolution"]}
            self.core.version(version)
            unit={k:deepcopy(a[k]) for k in ("id","ticket","campaign","requires","provenance","evidence",
                                            "eligibility","admitted")}
            unit.update(pr=pr,ref="refs/heads/"+p["headRefName"],version=version,
                        native_stack=str(membership["number"]),
                        physical_base={"ref":p["baseRefName"],"head":base})
            units.append(unit)
            inner[a["id"]]=deepcopy(a.get("inner_git_units",[]))
            # A provider 'merged' flag is an observation, not verified Main ancestry.
            if p.get("merged"):
                gaps.append({"pr":pr,"reason":"merge-mapping-and-Main-ancestry-UNKNOWN"})
        s={"schema":self.core.SCHEMA,"feed":{"binding":self.binding,"snapshot_id":snapshot_id,
                                           "schema":"accepted-native-metadata/v1"},
           "repo":self.repo,"main":main,"units":units,"segments":list(segments),
           "groups":deepcopy(groups),"events":[],"merges":[],"probes":[],"violations":[]}
        complete=len(units)==len(rows)
        if complete:
            self.core.Graph(s)
        return {"schema":"branch-adapter-result/v1","snapshot":s if complete else None,
                "account":self.account,"main":main,"known_metadata":known,"inner_git_units":inner,
                "scope":{"prs":prs,"complete_inventory":False,"stack_node":node["id"]},
                "frontiers":gaps+["outside-explicit-pr-scope-UNKNOWN"],
                "source_qualification":"FIXED_METADATA_ONLY"}


DEFERRAL_V1 = "rfq.branch-deferral-eligibility-projection/1"
DEFERRAL_V2 = "rfq.branch-deferral-eligibility-projection/2"
WORK_DURABILITY = ("Explicit Work supersession/reactivation; this is durable eligibility, "
                   "not a freshness heartbeat or external runtime claim.")


def _v2_trigger(core, entry, unit, *, work_decision, work_owner):
    """Parent binds the exact admitted current Work decision and its owner.

    This validates a selected capability; arbitrary JSON is not authentication.
    The decision persists until explicit supersession, without heartbeat expiry.
    It asserts no foundation, code, provider or runtime readiness.
    """
    from datetime import datetime
    import uuid
    need(type(entry["pull_request"]) is int and type(unit["pr"]) is int,
         "v2-exact-PR-binding")
    need(isinstance(entry.get("known_branch"), str)
         and unit["ref"] == "refs/heads/" + entry["known_branch"], "v2-current-branch-binding")
    need(entry.get("exemption_scope") ==
         "Ordinary upstream-landing/inactivity nudges attributable to intentional campaign deferral while trigger is false.",
         "v2-ordinary-upstream-scope-only")
    need(entry.get("active_obligations") == [
         "existing latest-Main cloud rebase", "stage/demo delivery",
         "source/WIP/evidence conservation", "actual active review/repair obligations"],
         "v2-active-obligations-retained")
    d = entry.get("reactivation")
    need(type(d) is dict and type(work_decision) is dict and d == work_decision,
         "v2-current-owner-decision-binding")
    need(isinstance(work_owner, str) and str(uuid.UUID(work_owner)) == work_owner
         and d.get("asserted_by_session") == work_owner, "v2-selected-Work-owner")
    need(type(d.get("satisfied")) is bool, "v2-explicit-Boolean-trigger")
    need(d.get("basis_type") == "EXPLICIT_CURRENT_WORK_ELIGIBILITY_DECISION"
         and isinstance(d.get("basis"), str) and 0 < len(d["basis"]) <= 4096
         and isinstance(d.get("condition"), str) and bool(d["condition"]),
         "v2-explicit-authoritative-decision-basis")
    need(d.get("effective_until") == WORK_DURABILITY, "v2-durable-until-Work-supersession")
    need(isinstance(d.get("asserted_at"), str), "v2-decision-timestamp")
    at = datetime.fromisoformat(d["asserted_at"].replace("Z", "+00:00"))
    need(at.tzinfo is not None and at.utcoffset().total_seconds() == 0, "v2-UTC-decision-timestamp")
    return d["satisfied"]


def apply_on_encounter(core, snapshot, projection, *, triggers=None,
                       capability=DEFERRAL_V1, work_decision=None, work_owner=None):
    """Select V1 explicit caller triggers or V2 bound durable Work decisions.

    Only encountered repository/PRs are adapted. No canonical assignments getter,
    global inventory or task ledger is used. V1's missing trigger stays UNKNOWN;
    no V2 field is implicitly interpreted by a V1 consumer.
    """
    need(capability in (DEFERRAL_V1, DEFERRAL_V2)
         and projection["schema"] == capability and projection["mode"] == "ON_ENCOUNTER"
         and projection["complete_inventory_required"] is False, "deferral-projection-contract")
    core.Graph(snapshot)
    if capability == DEFERRAL_V2:
        need(all(projection.get(k) is True for k in (
             "derived_projection_only", "ordinary_rules_for_unlisted",
             "all_real_active_violations_repeat_each_check", "healthy_checks_silent",
             "unresolved_conservation_closure_or_active_demo_obligations_still_alert")),
             "v2-bounded-ordinary-and-active-obligation-contract")
    triggers = {} if triggers is None else triggers
    result=deepcopy(snapshot); encountered=[]; gaps=[]
    for unit in result["units"]:
        matches=[e for e in projection["entries"]
                 if e["repository"]==result["repo"] and e["pull_request"]==unit["pr"]]
        need(len(matches)<=1,"ambiguous-deferral-entry")
        if not matches:
            continue
        entry=matches[0]
        need(type(entry["pull_request"]) is int and
             isinstance(entry["repository"], str) and entry["repository"]==result["repo"],
             "exact-deferral-repository-PR")
        need(entry["classification"]=="DEFERRED_TO_NAMED_CAMPAIGN"
             and entry["remaining_real_failures_still_alert"] is True, "deferral-scope-contract")
        pr=unit["pr"]; encountered.append(pr)
        if capability == DEFERRAL_V2:
            trigger = _v2_trigger(core, entry, unit, work_decision=work_decision, work_owner=work_owner)
            need(pr not in triggers or (type(triggers[pr]) is bool and triggers[pr] == trigger),
                 "v2-caller-trigger-cannot-override-Work")
        else:
            if pr not in triggers or type(triggers[pr]) is not bool:
                gaps.append({"pr":pr,"reason":"reactivation-trigger-UNKNOWN"})
                continue
            trigger = triggers[pr]
        unit["eligibility"].update(deferred=True, trigger=trigger,
                                  deferral_ref="work/projection/"+core.digest(entry))
    core.Graph(result)
    return {"critical_policy_bridge":"NONE_corrected_core_retains_active_obligations_once",
            "selected_capability":capability,
            "decision_semantics":"durable-Work-eligibility-not-runtime-readiness" if capability==DEFERRAL_V2
                                 else "V1-explicit-caller-trigger-or-UNKNOWN",
            "snapshot":result,"encountered":encountered,"frontiers":gaps,
            "inventory_requested":False,"canonical_source":projection["canonical_source"]}



def fixed_packet_binding(native_result, packet):
    """Retain supplied Source packet references only; never follow opaque locators.

    Source purpose strings bind explicit inner Git-unit provenance. They do not
    identify canonical Jira tasks or establish preservation/signature validity.
    """
    need(packet["schema"]=="existing-six-stack-all-four-signed-private-inputs-ready/1",
         "fixed-packet-schema")
    need(packet["order"]==native_result["scope"]["prs"]==STACK_ORDER,"fixed-packet-native-order")
    known=native_result["known_metadata"]
    need(len(known)==6 and native_result["main"]==packet["Main"]=="449e2a3d89ce4f51e69558d56b278594a129fbac",
         "fixed-packet-main")
    return {"schema":"fixed-native-source-binding/v1","prior_only":True,
            "main":packet["Main"],"stack_node":STACK_NODE,"order":deepcopy(packet["order"]),
            "native_structure_ref":packet["native_structure"],
            "inner_source_purposes":deepcopy(packet["all_four_source_purposes"]),
            "opaque_materialization_refs":{k:packet[k] for k in
                ("R1_R5_receipt","R4_R10_receipt","wholeunit_boundaries","good_transport")},
            "source_validity":"UNKNOWN","signature_validity":"UNKNOWN",
            "runtime_semantics":"UNKNOWN","landed":"UNKNOWN"}

