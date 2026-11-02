#!/usr/bin/env python3
"""Bounded metadata-only stack DAG observer/planner. No Git/provider execution."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from copy import deepcopy
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import time

SCHEMA = "stack-dag/v1"
BOARD = "cdb7c432-a0a0-4fc3-aba4-068b20a02c88"
RECIPIENT = "01a18bb3-2d8f-7eb0-a1ef-31b62ae96198"
MAX_BYTES = 2 * 1024 * 1024
MAX_UNITS = 1000
OID = re.compile(r"^[0-9a-f]{40}([0-9a-f]{24})?$")
TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:/@+-]{0,255}$")


class JournalDurabilityUnconfirmed(OSError):
    """Replacement is visible; preserve current memory and require owner recovery."""
    def __init__(self, outcome):
        super().__init__("journal published; durability unconfirmed; explicit owner recovery required")
        self.outcome = deepcopy(outcome)


class Invalid(ValueError):
    pass


def require(ok, reason):
    if not ok:
        raise Invalid(reason)


def fields(obj, required, optional=()):
    require(isinstance(obj, dict), "expected object")
    require(set(required) <= obj.keys(), "missing required metadata field")
    require(obj.keys() <= set(required) | set(optional), "unsupported metadata field")


def token(value):
    require(isinstance(value, str) and TOKEN.fullmatch(value), "invalid metadata identifier")
    return value


def oid(value):
    require(isinstance(value, str) and OID.fullmatch(value), "exact object identity required")
    return value


def unique(values):
    require(isinstance(values, list) and len(values) == len(set(values)), "duplicate/list metadata")
    return values


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def version(v):
    fields(v, ("head", "tree", "parents", "content", "resolution"))
    oid(v["head"]); oid(v["tree"])
    require(isinstance(v["parents"], list) and len(v["parents"]) <= 32, "invalid ordered parents")
    for p in unique(v["parents"]):
        oid(p)
    token(v["content"]); token(v["resolution"])
    return digest(v)


def load_json(path):
    # Inputs are exact named files, never discovery roots. Caller must mount them immutable.
    with open(path, "rb") as source:
        data = source.read(MAX_BYTES + 1)
    require(len(data) <= MAX_BYTES, "bounded input exceeded")
    def pairs(items):
        out = {}
        for key, value in items:
            require(key not in out, "duplicate JSON key")
            out[key] = value
        return out
    return json.loads(data, object_pairs_hook=pairs)


def toposort(nodes, deps, preference=None):
    priority = {u: i for i, u in enumerate(preference or sorted(nodes))}
    done, remaining = [], set(nodes)
    while remaining:
        eligible = sorted((u for u in remaining if not (deps[u] & remaining)),
                          key=lambda u: (priority.get(u, len(priority)), u))
        require(eligible, "logical dependency cycle")
        # One at a time honors an explicit order even as later units become eligible.
        u = eligible[0]
        remaining.remove(u); done.append(u)
    return done


class Graph:
    def __init__(self, snapshot):
        fields(snapshot, ("schema", "feed", "repo", "main", "units", "segments", "groups"),
               ("events", "merges", "probes", "violations", "stale_units", "recomposed"))
        require(snapshot["schema"] == SCHEMA, "unsupported snapshot schema")
        fields(snapshot["feed"], ("binding", "snapshot_id", "schema"))
        for v in snapshot["feed"].values():
            token(v)
        self.s = deepcopy(snapshot)
        self.repo = token(snapshot["repo"])
        oid(snapshot["main"])
        require(isinstance(snapshot["units"], list) and len(snapshot["units"]) <= MAX_UNITS,
                "unit budget exceeded")
        self.units, self.deps, self.keys, self.children = {}, {}, {}, {}
        prs, refs = set(), set()
        for u in snapshot["units"]:
            fields(u, ("id", "pr", "ref", "ticket", "campaign", "native_stack", "version",
                       "requires", "physical_base", "provenance", "evidence", "eligibility",
                       "admitted"))
            uid = token(u["id"])
            require(uid not in self.units, "duplicate canonical unit")
            require(type(u["pr"]) is int and u["pr"] > 0 and u["pr"] not in prs,
                    "PR must have singular canonical/native membership")
            prs.add(u["pr"])
            token(u["ref"])
            require(u["ref"] not in refs, "one canonical version per ref")
            refs.add(u["ref"])
            for k in ("ticket", "campaign", "native_stack"):
                if u[k] is not None:
                    token(u[k])
            require(type(u["admitted"]) is bool, "admission flag required")
            self.keys[uid] = version(u["version"])
            self.deps[uid] = set(token(x) for x in unique(u["requires"]))
            fields(u["physical_base"], ("ref", "head"))
            token(u["physical_base"]["ref"]); oid(u["physical_base"]["head"])
            fields(u["provenance"], ("original", "tests", "oracles", "signatures"))
            for values in u["provenance"].values():
                require(isinstance(values, list), "provenance references required")
                for ref in values:
                    token(ref)
            require(isinstance(u["evidence"], list), "evidence list required")
            for e in u["evidence"]:
                fields(e, ("kind", "version_key", "ref", "result"))
                require(e["kind"] in ("approval", "test", "semantic", "signature", "composition"),
                        "unsupported evidence kind")
                require(re.fullmatch("[0-9a-f]{64}", e["version_key"]), "invalid evidence binding")
                token(e["ref"])
                require(e["result"] in ("PASS", "FAIL", "UNKNOWN"), "invalid evidence result")
            fields(u["eligibility"], ("active", "deferred", "trigger", "deferral_ref"))
            for k in ("active", "deferred", "trigger"):
                require(type(u["eligibility"][k]) is bool, "explicit eligibility flags required")
            if u["eligibility"]["deferred"]:
                token(u["eligibility"]["deferral_ref"])
            else:
                require(u["eligibility"]["deferral_ref"] is None, "unexpected deferral reference")
            self.units[uid] = u
        require(all(d <= self.units.keys() for d in self.deps.values()), "unknown logical dependency")
        require(isinstance(snapshot["segments"], list) and len(snapshot["segments"]) <= MAX_UNITS,
                "segment budget exceeded")
        segments = {}
        for seg in snapshot["segments"]:
            fields(seg, ("id", "units", "depends_on"))
            sid = token(seg["id"])
            require(sid not in segments, "duplicate segment")
            require(seg["units"] and len(seg["units"]) <= MAX_UNITS, "empty/oversized segment")
            unique(seg["units"]); unique(seg["depends_on"])
            require(set(seg["units"]) <= self.units.keys(), "unknown segment unit")
            segments[sid] = seg
        sd = {sid: set(seg["depends_on"]) for sid, seg in segments.items()}
        require(all(ds <= segments.keys() for ds in sd.values()), "unknown segment dependency")
        toposort(segments, sd)
        for seg in segments.values():
            chain = seg["units"]
            for a, b in zip(chain, chain[1:]):
                self.deps[b].add(a)
            for parent in seg["depends_on"]:
                self.deps[chain[0]].add(segments[parent]["units"][-1])
        self.order = toposort(self.units, self.deps)
        self.children = {u: set() for u in self.units}
        for u, ds in self.deps.items():
            for d in ds:
                self.children[d].add(u)
        require(isinstance(snapshot["groups"], list) and len(snapshot["groups"]) <= MAX_UNITS,
                "group budget exceeded")
        gids = set()
        self.groups = []
        for g in snapshot["groups"]:
            fields(g, ("id", "tips", "order"))
            token(g["id"]); require(g["id"] not in gids, "duplicate group"); gids.add(g["id"])
            require(g["tips"], "empty delivery group")
            unique(g["tips"])
            require(set(g["tips"]) <= self.units.keys(), "unknown group tip")
            closure = self.ancestors(g["tips"])
            if g["order"] is None:
                require(len(g["tips"]) == 1 and all(len(self.deps[u]) <= 1 for u in closure),
                        "explicit join order required")
                order = toposort(closure, self.deps)
            else:
                order = unique(g["order"])
                require(set(order) == closure, "join order must contain exact dependency closure once")
                require(order == toposort(closure, self.deps, order), "join order violates dependency")
            self.groups.append(dict(g, order=order))
        self.changed = set()
        self._events()
        self.landed, self.merge_unknown = self._merges()
        self._validate_probes()
        self._validate_violations()
        self.persisted_stale = set()
        for item in snapshot.get("stale_units", []):
            fields(item, ("unit", "version_key", "evidence_ref"))
            require(item["unit"] in self.units, "unknown stale unit")
            require(item["version_key"] == self.keys[item["unit"]], "stale frontier version mismatch")
            token(item["evidence_ref"])
            self.persisted_stale.add(item["unit"])
        for item in snapshot.get("recomposed", []):
            fields(item, ("unit", "version_key", "evidence_ref"))
            require(item["unit"] in self.units, "unknown recomposed unit")
            require(item["version_key"] == self.keys[item["unit"]], "recomposition version mismatch")
            token(item["evidence_ref"])

    def ancestors(self, tips):
        seen, todo = set(), list(tips)
        while todo:
            u = todo.pop()
            if u not in seen:
                seen.add(u); todo.extend(self.deps[u])
        return seen

    def descendants(self, roots):
        seen, todo = set(), list(roots)
        while todo:
            u = todo.pop()
            for v in self.children[u]:
                if v not in seen:
                    seen.add(v); todo.append(v)
        return seen - set(roots)

    def _events(self):
        events = self.s.get("events", [])
        require(isinstance(events, list) and len(events) <= 4000, "event budget exceeded")
        for e in events:
            fields(e, ("kind", "unit", "before", "after", "evidence_ref"))
            require(e["kind"] in ("ref", "base", "membership", "merge", "main"), "unsupported event schema")
            if e["kind"] == "main":
                require(e["unit"] is None, "main event must have no unit")
                oid(e["before"]); oid(e["after"]); token(e["evidence_ref"])
                require(e["after"] == self.s["main"], "main event snapshot mismatch")
                if e["before"] != e["after"]:
                    self.changed.update(self.units)
                continue
            require(e["unit"] in self.units, "event unit missing")
            token(e["evidence_ref"])
            u = self.units[e["unit"]]
            if e["kind"] == "ref":
                version(e["before"]); version(e["after"])
                expected = u["version"]
            elif e["kind"] == "base":
                for x in (e["before"], e["after"]):
                    fields(x, ("ref", "head")); token(x["ref"]); oid(x["head"])
                expected = u["physical_base"]
            elif e["kind"] == "membership":
                for x in (e["before"], e["after"]):
                    if x is not None:
                        token(x)
                expected = u["native_stack"]
            else:
                # A merge event points to a bounded merge record; it never establishes landed alone.
                token(e["before"]); token(e["after"])
                expected = e["after"]
            require(e["after"] == expected, "event after does not bind current snapshot")
            if e["before"] != e["after"]:
                self.changed.add(e["unit"])

    def _merges(self):
        landed, unknown = {}, set()
        merges = self.s.get("merges", [])
        require(isinstance(merges, list) and len(merges) <= MAX_UNITS, "merge budget exceeded")
        for m in merges:
            fields(m, ("unit", "version_key", "method", "main_head", "landed_commit",
                       "main_ancestry_verified", "mapping", "evidence_ref"))
            u = m["unit"]
            require(u in self.units and u not in landed and u not in unknown, "duplicate/unknown merge")
            require(m["method"] in ("merge", "squash"), "unsupported merge method")
            require(m["mapping"] in ("exact", "unknown"), "unsupported merge mapping")
            require(type(m["main_ancestry_verified"]) is bool, "ancestry evidence required")
            oid(m["main_head"]); oid(m["landed_commit"]); token(m["evidence_ref"])
            if (m["version_key"] == self.keys[u] and m["main_head"] == self.s["main"]
                    and m["main_ancestry_verified"] and m["mapping"] == "exact"):
                landed[u] = m
            else:
                unknown.add(u)
        # Cannot replay a parent omitted from the asserted landed frontier.
        for u in landed:
            require(self.deps[u] <= landed.keys(), "partial merge is not a bottom-up landed frontier")
        return landed, unknown

    def _validate_probes(self):
        probes = self.s.get("probes", [])
        require(isinstance(probes, list) and len(probes) <= 4000, "probe budget exceeded")
        for p in probes:
            fields(p, ("kind", "units", "versions", "base", "status", "paths", "reason",
                       "evidence_ref", "admitted", "semantic"))
            require(p["kind"] in ("pair", "ordered"), "unsupported probe kind")
            require(p["units"] and set(p["units"]) <= self.units.keys(), "unknown probe unit")
            unique(p["units"])
            require(p["kind"] != "pair" or len(p["units"]) == 2, "pair probe arity")
            require(type(p["versions"]) is dict, "probe versions must be a mapping")
            require(set(p["versions"]) == set(p["units"]), "probe version bindings missing")
            for value in p["versions"].values():
                require(isinstance(value, str) and re.fullmatch("[0-9a-f]{64}", value),
                        "invalid probe version")
            oid(p["base"])
            require(p["status"] in ("CLEAN", "CONFLICT", "UNKNOWN"), "invalid probe status")
            require(type(p["admitted"]) is bool and type(p["semantic"]) is bool,
                    "probe admission/semantic flags required")
            token(p["reason"]); token(p["evidence_ref"])
            require(isinstance(p["paths"], list) and len(p["paths"]) <= 128, "path budget")
            for path in p["paths"]:
                # Role admission is supplied by the feed, not guessed from filename substrings.
                fields(path, ("path", "ordinary_safe"))
                require(path["ordinary_safe"] is True, "unqualified conflict location")
                value = path["path"]
                require(isinstance(value, str) and len(value) <= 1024 and not value.startswith("/")
                        and all(x not in ("", ".", "..") for x in value.split("/"))
                        and not any(ord(c) < 32 or ord(c) == 127 for c in value),
                        "invalid relative conflict location")
            require(p["admitted"] or not p["paths"], "unadmitted paths withheld")

    def _validate_violations(self):
        violations = self.s.get("violations", [])
        require(isinstance(violations, list) and len(violations) <= 4000, "violation budget")
        for v in violations:
            fields(v, ("unit", "kind", "obligation", "evidence_ref"))
            require(v["unit"] in self.units, "unknown violation unit")
            require(v["kind"] in ("stall", "unexpected_change", "conservation_failure",
                                  "cloud_demo", "required_closure", "repair", "whole_landing"),
                    "unsupported violation")
            token(v["obligation"]); token(v["evidence_ref"])

    def eligible(self, uid):
        e = self.units[uid]["eligibility"]
        return e["active"] and (not e["deferred"] or e["trigger"])

    def probe(self, kind, units, base=None):
        keys = {u: self.keys[u] for u in units}
        for p in reversed(self.s.get("probes", [])):
            same_units = p["units"] == units if kind == "ordered" else set(p["units"]) == set(units)
            if (p["kind"] == kind and same_units and p["versions"] == keys
                    and p["base"] == (base or self.s["main"]) and p["admitted"]
                    and all(self.units[u]["admitted"] for u in units)):
                return p
        return {"status": "UNKNOWN", "paths": [], "reason": "missing-or-unadmitted-exact-probe",
                "semantic": False}


def plan(snapshot):
    graph = Graph(snapshot)
    stale = graph.changed | graph.descendants(graph.changed) | graph.persisted_stale
    selected = set()
    groups = []
    problems = []
    for g in graph.groups:
        order = [u for u in g["order"] if u not in graph.landed]
        # Explicit deferred tips do not automatically activate later campaigns.
        active = all(graph.eligible(u) for u in g["tips"])
        unknown = set(g["order"]) & graph.merge_unknown
        # A descendant does not authorize reactivating its held prerequisite.
        # No operation-specific preservation/materialization override is admitted
        # by this schema. Retain the entire dependency order for owner disposition.
        held = [u for u in order if not graph.eligible(u)]
        status, reason = "PLANNED", None
        if not active:
            status, reason = "DEFERRED", "trigger-false-or-inactive"
        elif held:
            status, reason = "UNKNOWN", "held-ancestor-requires-owner-operation-selection"
        elif unknown:
            status, reason = "UNKNOWN", "manual-landed-mapping-frontier"
        elif any(not graph.units[u]["admitted"] for u in order):
            status, reason = "UNKNOWN", "unit-input-unadmitted"
        probe = graph.probe("ordered", g["order"])
        if active and status == "PLANNED" and order:
            if probe["status"] != "CLEAN":
                status, reason = probe["status"], probe["reason"]
            elif not probe["semantic"]:
                status, reason = "UNKNOWN", "ordered-textual-clean-semantic-unqualified"
        if active and status in ("UNKNOWN", "CONFLICT"):
            problems.append({"kind": status, "units": order or g["order"], "group": g["id"],
                             "reason": reason, "paths": probe["paths"] if status == "CONFLICT" else [],
                             "next_operation": "obtain-exact-evidence-or-resolve-in-owning-branch"})
        if active and not held:
            selected.update(order)
        groups.append({"id": g["id"], "order": g["order"], "remaining": order,
                        "held_units": held if active else [],
                       "disposition": status, "reason": reason,
                       "materialization_id": digest({"repo": graph.repo, "main": graph.s["main"],
                                                     "order": g["order"],
                                                     "versions": {u: graph.keys[u] for u in g["order"]}}),
                       "input_versions": {u: graph.keys[u] for u in g["order"]},
                       "qualification": ("RECOMPOSITION_REQUIRED" if set(order) & stale else
                                         "EXACT_ORDER_AND_SEMANTIC") if status == "PLANNED" and order
                       else ("LANDED" if not order and status == "PLANNED" else "UNQUALIFIED")})
    operations = []
    for u in graph.order:
        if u not in selected:
            continue
        unit = graph.units[u]
        ds = sorted(graph.deps[u])
        join_orders = [g["order"] for g in graph.groups if u in g["order"]]
        if len(ds) > 1:
            parent_orders = {tuple(d for d in order if d in ds) for order in join_orders}
            require(len(parent_orders) <= 1, "different physical join orders require explicit materialization units")
            ds = list(next(iter(parent_orders), tuple(ds)))
        bases = [{"unit": d, "tip": graph.s["main"] if d in graph.landed else "$result:" + d}
                 for d in ds]
        if not bases:
            bases = [{"unit": None, "tip": graph.s["main"]}]
        operations.append({
            "unit": u, "operation": "RECOMPOSE" if len(ds) > 1 else "RESTACK",
            "expected_version": graph.keys[u], "expected_head": unit["version"]["head"],
            "expected_physical_base": unit["physical_base"], "requires": ds,
            "new_bases": bases, "stale": u in stale, "provenance": unit["provenance"],
            "selected_parent_order": ds,
            "evidence": [{"ref": e["ref"], "kind": e["kind"],
                          "applicable": e["version_key"] == graph.keys[u] and u not in stale,
                          "result": e["result"]} for e in unit["evidence"]],
            "resolution_policy": "STOP_FOR_OWNER_NO_AUTOMATIC_RESOLUTION",
        })
    # Symmetric conflict observations stay outside dependencies and restack order.
    conflicts = []
    # Resolve each unordered pair once at current Main/current versions.
    # History count and symmetric operand spelling cannot multiply a notice.
    pairs = sorted({tuple(sorted(p["units"])) for p in graph.s.get("probes", [])
                    if p["kind"] == "pair"})
    for pair_tuple in pairs:
        pair = list(pair_tuple)
        observed = graph.probe("pair", pair)
        if observed["status"] == "CONFLICT":
            conflicts.append({"units": pair, "paths": observed["paths"],
                              "versions": {u: graph.keys[u] for u in pair}})
            if any(graph.eligible(u) for u in pair):
                problems.append({"kind": "CONFLICT", "units": pair, "group": None,
                                 "reason": observed["reason"], "paths": observed["paths"],
                                 "next_operation": "owner-resolve-selected-composition"})
    for u in sorted(graph.changed):
        # Unexpected movement remains observable even in a deferred campaign.
        problems.append({"kind": "CHANGE", "units": [u], "group": None, "reason": "exact-version-event",
                         "paths": [], "next_operation": "review-change-and-recompose-descendants"})
    for u in sorted(graph.persisted_stale - graph.changed - set(graph.landed)):
        if graph.eligible(u):
            problems.append({"kind": "STALE", "units": [u], "group": None,
                             "reason": "recomposition-and-exact-qualification-outstanding", "paths": [],
                             "next_operation": "owner-recompose-and-qualify-exact-current-version"})
    for v in graph.s.get("violations", []):
        uid = v["unit"]
        critical = v["kind"] in ("unexpected_change", "conservation_failure", "required_closure",
                                  "repair", "whole_landing", "cloud_demo")
        enabled = critical or graph.eligible(uid)
        if v["kind"] == "whole_landing":
            e = graph.units[uid]["eligibility"]
            # Positive explicit current deferral + false authoritative trigger;
            # PR number or inactivity alone never grants an exemption. The feed
            # owns this binding. Other critical obligations remain independent.
            enabled = not (e["deferred"] and e["trigger"] is False
                           and e["deferral_ref"] is not None)
        if enabled:
            problems.append({"kind": v["kind"], "units": [uid], "group": None,
                             "reason": v["obligation"], "paths": [],
                             "next_operation": "existing-owner-action", "evidence_ref": v["evidence_ref"]})
    # Pair operand order is symmetric. Canonicalize only that spelling for
    # plan/check identity; retain history chronology and all exact version fields.
    # once() still verifies the raw immutable snapshot SHA256 independently.
    canonical_snapshot = deepcopy(snapshot)
    for p in canonical_snapshot.get("probes", []):
        if p["kind"] == "pair":
            p["units"] = sorted(p["units"])
    result = {"schema": "stack-plan/v1", "binding": graph.s["feed"], "repo": graph.repo,
              "snapshot_digest": digest(canonical_snapshot), "main": graph.s["main"],
              "versions": graph.keys, "groups": groups, "operations": operations,
              "stale": sorted(stale), "landed": sorted(graph.landed),
              "manual_frontier": sorted(graph.merge_unknown |
                                        {u for g in groups for u in g["held_units"]}),
              "logical_dependencies": {u: sorted(d) for u, d in graph.deps.items()},
              "observed_conflicts": conflicts, "problems": problems,
              "mutations_executed": False}
    result["plan_id"] = digest(result)
    return result


def simulate(snapshot, prepared, actual, outcomes):
    """Controlled executor contract: pure effect trace; never executes Git/native operations.

    Successful outcomes carry owner-produced exact versions and qualification, which
    become descendants' new tips. CAS or composition failure blocks descendants only.
    """
    graph = Graph(snapshot)
    fresh = plan(snapshot)
    require(prepared == fresh, "stale or modified plan")
    fields(actual, ("main", "units"))
    oid(actual["main"])
    require(set(actual["units"]) == set(graph.units), "actual CAS units must match bounded snapshot")
    for item in actual["units"].values():
        fields(item, ("version", "physical_base", "native_stack"))
        version(item["version"])
        fields(item["physical_base"], ("ref", "head"))
        token(item["physical_base"]["ref"]); oid(item["physical_base"]["head"])
        if item["native_stack"] is not None:
            token(item["native_stack"])
    require(set(outcomes) <= set(graph.units), "unknown operation outcome")
    trace, blocked, results = [], set(), {}
    selected = {o["unit"] for o in prepared["operations"]}
    for op in prepared["operations"]:
        u = op["unit"]
        if set(op["requires"]) & blocked:
            blocked.add(u); trace.append({"unit": u, "effect": "BLOCKED_DESCENDANT"}); continue
        if (actual["main"] != graph.s["main"]
                or actual["units"][u] != {k: graph.units[u][k]
                                         for k in ("version", "physical_base", "native_stack")}):
            blocked.add(u); trace.append({"unit": u, "effect": "CAS_MISMATCH"}); continue
        if u in graph.merge_unknown or not graph.units[u]["admitted"]:
            blocked.add(u); trace.append({"unit": u, "effect": "UNKNOWN"}); continue
        outcome = outcomes.get(u)
        if outcome is None:
            blocked.add(u); trace.append({"unit": u, "effect": "UNKNOWN"}); continue
        fields(outcome, ("status",), ("version", "preserved", "evidence_ref"))
        require(outcome["status"] in ("PASS", "CONFLICT", "UNKNOWN", "FAIL"), "invalid effect status")
        if outcome["status"] != "PASS":
            blocked.add(u); trace.append({"unit": u, "effect": outcome["status"]}); continue
        fields(outcome, ("status", "version", "preserved", "evidence_ref"))
        version(outcome["version"]); token(outcome["evidence_ref"])
        # Preservation cannot be inferred from textual similarity.
        if outcome["preserved"] != graph.units[u]["provenance"]:
            blocked.add(u); trace.append({"unit": u, "effect": "CONSERVATION_FAILURE"}); continue
        base_tips = [graph.s["main"] if d in graph.landed else results[d]["head"]
                     for d in op["selected_parent_order"]]
        if not base_tips:
            base_tips = [graph.s["main"]]
        results[u] = outcome["version"]
        trace.append({"unit": u, "effect": "COMPOSED", "new_bases": base_tips,
                      "new_tip": outcome["version"]["head"], "qualified": False,
                      "evidence_revalidation_required": True})
    # Group qualification is never inherited from pairwise evidence or old composition.
    groups = []
    for group in prepared["groups"]:
        if group["disposition"] == "DEFERRED":
            state = "DEFERRED"
        elif set(group["remaining"]) & blocked:
            state = "BLOCKED"
        elif group["disposition"] != "PLANNED":
            state = group["disposition"]
        elif set(group["remaining"]) & selected:
            state = "RECOMPOSED_UNQUALIFIED_NEW_VERSIONS"
        else:
            state = "LANDED"
        groups.append({"id": group["id"], "disposition": state})
    return {"schema": "stack-effect-trace/v1", "trace": trace, "groups": groups,
            "versions": results, "blocked": sorted(blocked), "mutations_executed": False}


def alerts(snapshot, prepared, check_id):
    graph = Graph(snapshot); token(check_id)
    require(prepared == plan(snapshot), "alert plan differs from snapshot")
    out = []
    for n, problem in enumerate(prepared["problems"]):
        ids = problem["units"]
        out.append({"schema": "branch-conflict-alert/v1", "check_id": check_id,
                    "alert_id": digest([check_id, prepared["plan_id"], n]),
                    "board": BOARD, "recipient": RECIPIENT, "repo": graph.repo,
                    "binding": graph.s["feed"], "main": graph.s["main"],
                    "units": [{"id": u, "ref": graph.units[u]["ref"], "pr": graph.units[u]["pr"],
                               "ticket": graph.units[u]["ticket"], "campaign": graph.units[u]["campaign"],
                               "version": graph.units[u]["version"],
                               "base": graph.units[u]["physical_base"]} for u in ids],
                    "affected_descendants": sorted(graph.descendants(ids)),
                    "selected_order": next((g["order"] for g in prepared["groups"]
                                            if g["id"] == problem["group"]), None),
                    "disposition": problem["kind"], "locations": problem["paths"],
                    "reason": problem["reason"], "next_operation": problem["next_operation"]})
    return out


def board_command(alert, *, python, board_cli, catalog_home, sender):
    """Accepted board open protocol; command construction only, no subprocess."""
    require(alert["board"] == BOARD and alert["recipient"] == RECIPIENT, "route mismatch")
    token(sender)
    for path in (python, board_cli, catalog_home):
        require(isinstance(path, str) and path.startswith("/"), "exact adapter paths required")
    bootstrap = ("import runpy,sys;sys.path.insert(0," + repr(str(Path(board_cli).parent)) +
                 ");runpy.run_path(" + repr(board_cli) + ",run_name='__main__')")
    return [python, "-I", "-S", "-B", "-c", bootstrap, "--home", catalog_home, "--board", BOARD,
            "open", "--session", sender, "--topic", "branch-stack-conflict",
            "--title", "Branch DAG " + alert["disposition"] + " " + alert["check_id"],
            "--kind", "status", "--text", json.dumps(alert, sort_keys=True),
            "--to", RECIPIENT]


def _guard_journal_inode(journal_path, lock_fd):
    p = Path(journal_path)
    require(p.is_absolute() and p.parent.resolve() == p.parent, "canonical journal path required")
    require(not p.is_symlink(), "journal symlink is not a canonical state file")
    try:
        journal_stat = os.stat(p, follow_symlinks=False)
    except FileNotFoundError:
        return
    require(stat.S_ISREG(journal_stat.st_mode), "regular journal file required")
    lock_stat = os.fstat(lock_fd)
    require((journal_stat.st_dev, journal_stat.st_ino) != (lock_stat.st_dev, lock_stat.st_ino),
            "journal and lock must be distinct inodes")


@contextmanager
def owner_lock(path, owner, *, journal_path=None):
    """Hold one canonical flock without ever writing/truncating its inode.

    fstat binds the actual opened lock, not a prior pathname-only check. The
    protected journal is checked after acquisition, before any journal write.
    Owner-controlled stable directory entries and the shared locking discipline
    remain caller obligations; this is not a global hostile-rename guarantee.
    """
    token(owner)
    p = Path(path)
    require(p.is_absolute() and p.parent.resolve() == p.parent, "canonical lock path required")
    fd = os.open(p, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        require(stat.S_ISREG(os.fstat(fd).st_mode), "regular lock file required")
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise Invalid("canonical owner lock busy")
        current, opened = os.stat(p, follow_symlinks=False), os.fstat(fd)
        require((current.st_dev, current.st_ino) == (opened.st_dev, opened.st_ino),
                "canonical lock path changed during acquisition")
        if journal_path is not None:
            _guard_journal_inode(journal_path, fd)
        yield fd
    finally:
        os.close(fd)


class DeliveryJournal:
    """Durable one-attempt identity. The injected sender is the parent's adapter.

    Persist AMBIGUOUS before crossing the transport boundary. A crash never causes
    automatic resend. Recipient acknowledgment is a separately bound receipt.
    Caller holds the canonical owner lock for all methods.
    """
    def __init__(self, path, *, lock_fd=None):
        self.path = Path(path)
        self.lock_fd = lock_fd
        require(not self.path.is_symlink(), "journal symlink is not a canonical state file")
        if lock_fd is not None:
            _guard_journal_inode(self.path, lock_fd)
        require(self.path.is_absolute() and self.path.parent.resolve() == self.path.parent,
                "canonical journal path required")
        self.data = load_json(path) if self.path.exists() else {"schema": "stack-delivery/v1", "checks": {}}
        self.persistence = {"schema": "journal-persistence/v1",
                            "outcome": "HISTORICAL_RECEIPT_ONLY",
                            "durability": "UNVERIFIED_AFTER_REOPEN",
                            "state_digest": digest(self.data),
                            "recovery": "owner-lock + confirm_durability(expected_state_digest); no automatic send"}
        fields(self.data, ("schema", "checks"), ("observation",))
        require(self.data["schema"] == "stack-delivery/v1", "journal schema mismatch")

    def preview_observation(self, snapshot):
        """Compute the next frontier without changing memory or durable state."""
        graph = Graph(snapshot)
        previous = self.data.get("observation")
        if previous is not None:
            require(previous["binding"] == graph.s["feed"]["binding"]
                    and previous["schema"] == graph.s["feed"]["schema"]
                    and previous["repo"] == graph.repo, "observer feed/repository identity changed")
        stale = set(graph.persisted_stale)
        changed = set(graph.changed)
        current = {u: {"version_key": graph.keys[u], "base": item["physical_base"],
                       "native_stack": item["native_stack"], "requires": sorted(graph.deps[u])}
                   for u, item in graph.units.items()}
        if previous is not None:
            # A removed unit can only disappear after explicit landed evidence in a retained snapshot.
            require(set(previous["units"]) <= set(current),
                    "removed canonical unit requires parent conservation disposition")
            if previous["main"] != graph.s["main"]:
                changed.update(graph.units)
            for u, binding in current.items():
                if previous["units"].get(u) != binding:
                    changed.add(u)
            stale.update(previous["stale"])
        stale.update(changed | graph.descendants(changed))
        stale.difference_update(graph.landed)
        for item in graph.s.get("recomposed", []):
            u = item["unit"]
            containing = [g for g in graph.groups if u in g["order"]]
            # A current composition attestation alone cannot borrow an old/orderless clean result.
            if containing and all(
                    (p := graph.probe("ordered", g["order"]))["status"] == "CLEAN" and p["semantic"]
                    for g in containing):
                stale.discard(u)
        result = deepcopy(snapshot)
        result["stale_units"] = [{"unit": u, "version_key": graph.keys[u],
                                  "evidence_ref": "observer/persistent-frontier"} for u in sorted(stale)]
        observation = {"binding": graph.s["feed"]["binding"],
                                    "schema": graph.s["feed"]["schema"], "repo": graph.repo,
                                    "main": graph.s["main"], "units": current, "stale": sorted(stale)}
        return result, observation

    def observe(self, snapshot):
        """Explicit observation-only API; runtime occurrences use accept instead."""
        result, observation = self.preview_observation(snapshot)
        with self._update():
            self.data["observation"] = observation
        return result

    def receipt(self, check_id):
        """Retrieve an existing receipt without observation, mutation or transport."""
        token(check_id)
        require(check_id in self.data["checks"], "unknown check identity")
        return deepcopy(self.data["checks"][check_id])

    def receipt_status(self, check_id):
        """Read-only receipt plus CURRENT journal persistence, never a send/retry."""
        return {"receipt": self.receipt(check_id), "persistence": deepcopy(self.persistence)}

    def _accepted(self, check_id, replayed):
        row = self.receipt(check_id)
        return {"plan": deepcopy(row["plan"]), "alerts": deepcopy(row["notices"]),
                "delivery": row, "replayed": replayed,
                "acceptance": self.persistence["outcome"],
                "persistence": deepcopy(self.persistence)}

    @contextmanager
    def _update(self):
        self._replacement_done = False
        previous = deepcopy(self.data)
        try:
            yield
            self.save()
        except JournalDurabilityUnconfirmed:
            # The new inode is already published. Rolling back memory would lie.
            raise
        except Exception:
            if not getattr(self, "_replacement_done", False):
                self.data = previous
            raise

    def accept(self, snapshot, check_id, *, context=None):
        """Commit one occurrence, distinguishing rejection from published uncertainty.

        Historical replays are receipt-only, never a durability or transport retry.
        """
        token(check_id)
        input_digest = digest({"snapshot": snapshot, "context": context})
        if check_id in self.data["checks"]:
            row = self.receipt(check_id)
            require(row.get("input_digest") == input_digest,
                    "same check identity reused with different or unbound input")
            return self._accepted(check_id, True)
        observed, observation = self.preview_observation(snapshot)
        prepared = plan(observed)
        notices = alerts(observed, prepared, check_id)
        require(len(self.data["checks"]) < 10000,
                "journal retention frontier: parent must archive exact settled checks")
        row = {"plan_id": prepared["plan_id"], "notices_digest": digest(notices),
               "input_digest": input_digest, "plan": prepared, "notices": notices,
               "state": "PLANNED" if notices else "SILENT", "attempts": []}
        try:
            with self._update():
                self.data["observation"] = observation
                self.data["checks"][check_id] = row
        except JournalDurabilityUnconfirmed:
            # An explicit accepted-but-indeterminate result, never durable success.
            pass
        return self._accepted(check_id, False)

    def _published(self, raw, identity, stage):
        self.persistence = {"schema": "journal-persistence/v1",
                            "outcome": "ACCEPTED_DURABILITY_UNCONFIRMED",
                            "durability": "UNCONFIRMED", "stage": stage,
                            "state_digest": digest(self.data),
                            "journal_sha256": hashlib.sha256(raw).hexdigest(),
                            "published_inode": identity,
                            "recovery": "owner-lock + confirm_durability(expected_state_digest); no automatic send"}

    def _directory_sync(self, raw, identity):
        stage = "DIRECTORY_OPEN"
        try:
            fd = os.open(self.path.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                stage = "DIRECTORY_FSYNC"
                os.fsync(fd)
            finally:
                os.close(fd)
        except OSError as exc:
            self._published(raw, identity, stage)
            raise JournalDurabilityUnconfirmed(self.persistence) from exc
        self._published(raw, identity, "DIRECTORY_FSYNC")
        self.persistence.update(outcome="ACCEPTED_DURABLE", durability="CONFIRMED")

    def save(self):
        self._replacement_done = False
        if self.lock_fd is not None:
            _guard_journal_inode(self.path, self.lock_fd)
        raw = json.dumps(self.data, sort_keys=True).encode()
        require(len(raw) <= MAX_BYTES, "journal byte retention frontier")
        temporary = self.path.with_name(self.path.name + ".pending")
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "wb") as out:
            out.write(raw); out.flush(); os.fsync(out.fileno())
            st = os.fstat(out.fileno())
            identity = {"device": st.st_dev, "inode": st.st_ino}
        if self.lock_fd is not None:
            _guard_journal_inode(self.path, self.lock_fd)
        os.replace(temporary, self.path)  # Commit boundary: never restore old memory after this.
        self._replacement_done = True
        self._directory_sync(raw, identity)
        return deepcopy(self.persistence)

    def confirm_durability(self, expected_state_digest):
        """Explicit owner recovery: confirm exact CURRENT bytes, no rewrite or send.

        The lock and stable directory contract apply. A different current state is
        rejected; never overwrite a newer journal with a recovery snapshot.
        """
        require(self.lock_fd is not None, "explicit recovery requires canonical owner lock")
        _guard_journal_inode(self.path, self.lock_fd)
        require(expected_state_digest == digest(self.data), "recovery memory identity mismatch")
        fd = os.open(self.path, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(fd, "rb") as inp:
            st = os.fstat(inp.fileno())
            raw = inp.read(MAX_BYTES + 1)
            require(len(raw) <= MAX_BYTES and json.loads(raw) == self.data,
                    "recovery disk identity mismatch")
            current = os.stat(self.path, follow_symlinks=False)
            require((st.st_dev, st.st_ino) == (current.st_dev, current.st_ino),
                    "recovery journal inode changed")
            identity = {"device": st.st_dev, "inode": st.st_ino}
            try:
                os.fsync(inp.fileno())
            except OSError as exc:
                self._published(raw, identity, "RECOVERY_FILE_FSYNC")
                raise JournalDurabilityUnconfirmed(self.persistence) from exc
        self._directory_sync(raw, identity)
        return deepcopy(self.persistence)

    def prepare(self, check_id, notices, plan_id):
        token(check_id)
        checks = self.data["checks"]
        body = {"plan_id": plan_id, "notices_digest": digest(notices)}
        if check_id in checks:
            row = checks[check_id]
            require(row["plan_id"] == plan_id and row["notices_digest"] == body["notices_digest"],
                    "same check identity reused with different payload")
            return row
        require(len(checks) < 10000, "journal retention frontier: parent must archive exact settled checks")
        row = dict(body, state="PLANNED" if notices else "SILENT", attempts=[])
        with self._update():
            checks[check_id] = row
        return row

    def deliver(self, check_id, notices, plan_id, sender):
        row = self.prepare(check_id, notices, plan_id)
        if row["state"] != "PLANNED":
            return deepcopy(row)
        require(self.persistence["durability"] == "CONFIRMED",
                "planned delivery requires explicit durability recovery before send")
        with self._update():
            row["state"] = "AMBIGUOUS"
            row["attempts"] = [{"alert_id": a["alert_id"], "state": "AMBIGUOUS"} for a in notices]
        # The AMBIGUOUS prerequisite is durably confirmed before the first send.
        for alert, attempt in zip(notices, row["attempts"]):
            try:
                receipt = sender(alert)
                fields(receipt, ("stage", "board", "recipient", "notification_id"),
                       ("queue_message_id", "ack_ref"))
                require(receipt["board"] == BOARD and receipt["recipient"] == RECIPIENT,
                        "delivery receipt route mismatch")
                require(type(receipt["notification_id"]) is int and receipt["notification_id"] > 0,
                        "qualified notification ID required")
                require(receipt["stage"] in ("ENQUEUED", "PUSHED", "RECIPIENT_ACK"),
                        "unsupported delivery receipt")
                if receipt["stage"] == "PUSHED":
                    token(receipt["queue_message_id"])
                if receipt["stage"] == "RECIPIENT_ACK":
                    token(receipt["ack_ref"])
                with self._update():
                    attempt.update(state=receipt["stage"], receipt=receipt)
            except JournalDurabilityUnconfirmed:
                raise
            except Exception:
                # The attempt and later unsent notices remain ambiguous; reconcile, never blind retry.
                # _update can restore a copied state after a precommit error.
                row = self.data["checks"][check_id]
                with self._update():
                    row["state"] = "AMBIGUOUS"
                return deepcopy(row)
        states = {a["state"] for a in row["attempts"]}
        with self._update():
            row["state"] = next((s for s in ("AMBIGUOUS", "ENQUEUED", "PUSHED", "RECIPIENT_ACK")
                                 if s in states), "SILENT")
        return deepcopy(row)

    def reconcile(self, check_id, alert_id, receipt):
        # No send. Parent obtains the board-qualified receipt independently.
        row = self.data["checks"][check_id]
        fields(receipt, ("stage", "board", "recipient", "notification_id"),
               ("queue_message_id", "ack_ref"))
        require(receipt["board"] == BOARD and receipt["recipient"] == RECIPIENT, "receipt route")
        require(receipt["stage"] in ("ENQUEUED", "PUSHED", "RECIPIENT_ACK"), "receipt stage")
        require(type(receipt["notification_id"]) is int and receipt["notification_id"] > 0, "notice ID")
        if receipt["stage"] == "PUSHED":
            token(receipt["queue_message_id"])
        if receipt["stage"] == "RECIPIENT_ACK":
            token(receipt["ack_ref"])
        attempt = next((a for a in row["attempts"] if a["alert_id"] == alert_id), None)
        require(attempt is not None, "unknown delivery attempt")
        if "receipt" in attempt:
            require(attempt["receipt"]["notification_id"] == receipt["notification_id"],
                    "receipt notice mismatch")
        rank = {"AMBIGUOUS": 0, "ENQUEUED": 1, "PUSHED": 2, "RECIPIENT_ACK": 3}
        require(rank[receipt["stage"]] >= rank[attempt["state"]], "receipt stage regression")
        with self._update():
            attempt.update(state=receipt["stage"], receipt=receipt)
            row["state"] = min((a["state"] for a in row["attempts"]), key=lambda s: rank[s])
        return deepcopy(row)


def once(snapshot_path, binding_path, journal_path, lock_path, check_id):
    # Immutable startup binding detects mixed schema/source/feed identities.
    binding = load_json(binding_path)
    fields(binding, ("schema", "source_sha256", "feed_binding", "feed_schema", "owner",
                     "snapshot_sha256"))
    require(binding["schema"] == "stack-startup/v1", "startup binding schema")
    own_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    require(own_hash == binding["source_sha256"], "startup source identity changed")
    with open(snapshot_path, "rb") as input_file:
        raw = input_file.read(MAX_BYTES + 1)
    require(len(raw) <= MAX_BYTES, "snapshot byte budget")
    require(hashlib.sha256(raw).hexdigest() == binding["snapshot_sha256"], "startup input identity changed")
    snapshot = load_json(snapshot_path)
    require(snapshot["feed"]["binding"] == binding["feed_binding"]
            and snapshot["feed"]["schema"] == binding["feed_schema"], "unbound feed schema")
    with owner_lock(lock_path, binding["owner"], journal_path=journal_path) as lock_fd:
        journal = DeliveryJournal(journal_path, lock_fd=lock_fd)
        accepted = journal.accept(snapshot, check_id)
        return {**accepted,
                "mode": "PLAN_ONLY_PARENT_TRANSPORT_NOT_BOUND", "cadence_seconds": 300}


def native_contract(snapshot, mode, unit=None):
    graph = Graph(snapshot)
    expected = [1639, 1640, 1647, 1648, 1645, 1641]
    members = [u for u in graph.order if graph.units[u]["native_stack"] == "1649"]
    require([graph.units[u]["pr"] for u in members] == expected,
            "existing Stack1649 membership/order requires parent binding")
    require(mode in ("whole", "feature", "checkout"), "unsupported native mode")
    if mode == "feature":
        require(unit in members, "feature operation requires an existing member")
    commands = ([["gh", "stack", "checkout", "1649"]] if mode == "checkout" else
                ([["gh", "stack", "rebase", "--upstack"], ["gh", "stack", "push"]]
                 if mode == "feature" else
                 [["gh", "stack", "rebase"], ["gh", "stack", "push"]]))
    return {"schema": "native-stack-operation-contract/v1", "stack": 1649,
            "node": "PRS_kwDOOtFmdM4ALB_v", "mode": mode, "commands": commands,
            "expected_main": graph.s["main"],
            "expected_heads": {u: graph.units[u]["version"]["head"] for u in members},
            "owning_feature_unit": unit, "mutations_executed": False,
            "preconditions": ["parent-qualified-existing-checkout-and-lease",
                              "exact-version-CAS-and-actual-native-capability",
                              "owner-preservation-signatures-tests-oracles",
                              "parent-publication-and-CI-authority"],
            "readiness": "CONTRACT_ONLY_NOT_AUTHORIZATION_OR_EXECUTION"}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    for command in ("plan", "alerts"):
        c = sub.add_parser(command); c.add_argument("--snapshot", required=True)
        if command == "alerts":
            c.add_argument("--check-id", required=True)
    c = sub.add_parser("simulate")
    c.add_argument("--snapshot", required=True); c.add_argument("--plan", required=True)
    c.add_argument("--actual", required=True); c.add_argument("--outcomes", required=True)
    c = sub.add_parser("once")
    for name in ("snapshot", "binding", "journal", "lock", "check-id"):
        c.add_argument("--" + name, required=True)
    c = sub.add_parser("recover")
    for name in ("journal", "lock", "owner", "check-id", "state-digest"):
        c.add_argument("--" + name, required=True)
    c = sub.add_parser("native-contract")
    c.add_argument("--snapshot", required=True)
    c.add_argument("--mode", choices=("whole", "feature", "checkout"), required=True)
    c.add_argument("--unit")
    sub.add_parser("schedule")
    a = p.parse_args(argv)
    try:
        if a.command == "schedule":
            result = {"schema": "stack-schedule/v1", "cadence_seconds": 300,
                      "launch_background": False, "single_owner": "canonical-flock",
                      "command": "once", "transport": "parent-injected-only",
                      "input": "one immutable bounded snapshot and startup binding per check",
                      "check_id": "distinct durable scheduler occurrence identity"}
        elif a.command == "native-contract":
            result = native_contract(load_json(a.snapshot), a.mode, a.unit)
        elif a.command == "recover":
            with owner_lock(a.lock, a.owner, journal_path=a.journal) as lock_fd:
                journal = DeliveryJournal(a.journal, lock_fd=lock_fd)
                journal.receipt(a.check_id)  # Validate requested receipt before any sync.
                journal.confirm_durability(a.state_digest)
                result = journal.receipt_status(a.check_id)
        elif a.command == "once":
            result = once(a.snapshot, a.binding, a.journal, a.lock, a.check_id)
        else:
            snapshot = load_json(a.snapshot); prepared = plan(snapshot)
            if a.command == "plan":
                result = prepared
            elif a.command == "alerts":
                result = alerts(snapshot, prepared, a.check_id)
            else:
                result = simulate(snapshot, load_json(a.plan), load_json(a.actual), load_json(a.outcomes))
        print(json.dumps(result, sort_keys=True))
        if isinstance(result, dict) and result.get("persistence", {}).get("durability") == "UNCONFIRMED":
            return 4
        if a.command == "simulate":
            return 3 if result["blocked"] or any(g["disposition"] in ("UNKNOWN", "CONFLICT")
                                                for g in result["groups"]) else 0
        if a.command in ("plan", "alerts", "once"):
            problems = result["problems"] if a.command == "plan" else (
                result if a.command == "alerts" else result["plan"]["problems"])
            return 3 if problems else 0
        return 0
    except JournalDurabilityUnconfirmed as exc:
        print(json.dumps({"schema": "stack-indeterminate/v1", "persistence": exc.outcome}, sort_keys=True))
        return 4
    except (Invalid, ValueError, KeyError, TypeError, OSError, RecursionError) as exc:
        # Do not echo source/patch data or raw invalid input.
        print(json.dumps({"schema": "stack-error/v1", "error": type(exc).__name__,
                          "reason": str(exc) if isinstance(exc, Invalid) else "invalid-or-unavailable-input"}),
              file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
