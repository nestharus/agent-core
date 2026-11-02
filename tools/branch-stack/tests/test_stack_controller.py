"""Independent behavior examples from Work9403 brief; controlled metadata only."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SOURCE = ROOT / "src" / "stack_controller.py"
spec = importlib.util.spec_from_file_location("stack_controller", SOURCE)
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)
RUNTIME = Path(os.environ.get("STACK_DAG_TEST_RUNTIME", str(ROOT / "runtime")))
_cli_number = 0


def v(number):
    return {"head": format(number, "040x"), "tree": format(number + 10000, "040x"),
            "parents": [format(number - 1, "040x")], "content": "content-" + str(number),
            "resolution": "resolution-0"}


def unit(name, number, requires=(), pr=None):
    return {"id": name, "pr": pr or number, "ref": "refs/heads/" + name, "ticket": None,
            "campaign": "controlled", "native_stack": None, "version": v(number),
            "requires": list(requires), "physical_base": {"ref": "main", "head": v(1)["head"]},
            "provenance": {"original": ["original/" + name], "tests": ["tests/" + name],
                           "oracles": ["oracles/" + name], "signatures": ["signed/" + name]},
            "evidence": [], "admitted": True,
            "eligibility": {"active": True, "deferred": False, "trigger": False, "deferral_ref": None}}


def snapshot(kind="diamond"):
    units = [unit("A", 10), unit("B", 20, ["A"]), unit("C", 30, ["A"]),
             unit("D", 40, ["B", "C"]), unit("X", 50, ["B"]), unit("Z", 60)]
    if kind == "linear":
        units = units[:2]
        groups = [{"id": "linear", "tips": ["B"], "order": None}]
    else:
        groups = [{"id": "join", "tips": ["D"], "order": ["A", "C", "B", "D"]},
                  {"id": "cross", "tips": ["X"], "order": ["A", "B", "X"]},
                  {"id": "parallel", "tips": ["Z"], "order": None}]
    return {"schema": c.SCHEMA, "feed": {"binding": "fixture-feed", "snapshot_id": "s1",
                                        "schema": "typed-fixture-v1"},
            "repo": "controlled/repository", "main": v(1)["head"], "units": units,
            "segments": [], "groups": groups, "events": [], "merges": [], "probes": [],
            "violations": []}


def at(s, uid):
    return next(x for x in s["units"] if x["id"] == uid)


def probe(s, units, kind="ordered", status="CLEAN", semantic=True):
    return {"kind": kind, "units": list(units),
            "versions": {u: c.version(at(s, u)["version"]) for u in units},
            "base": s["main"], "status": status,
            "paths": ([{"path": "src/interface.py", "ordinary_safe": True}]
                      if status == "CONFLICT" else []),
            "reason": "controlled-probe", "evidence_ref": "evidence/probe",
            "admitted": True, "semantic": semantic}


def healthy(s):
    g = c.Graph(s)
    s["probes"] = [probe(s, x["order"]) for x in g.groups]
    return s


def actual(s):
    return {"main": s["main"], "units": {
        u["id"]: {k: copy.deepcopy(u[k]) for k in ("version", "physical_base", "native_stack")}
        for u in s["units"]}}


def outcomes(s):
    return {u["id"]: {"status": "PASS", "version": v(1000 + u["pr"]),
                      "preserved": copy.deepcopy(u["provenance"]), "evidence_ref": "fixture/effect"}
            for u in s["units"]}


def change(s, uid):
    old = copy.deepcopy(at(s, uid)["version"])
    at(s, uid)["version"] = v(5000 + at(s, uid)["pr"])
    s["events"].append({"kind": "ref", "unit": uid, "before": old,
                        "after": copy.deepcopy(at(s, uid)["version"]), "evidence_ref": "feed/ref"})


def merged(s, uid, method="merge", mapping="exact"):
    return {"unit": uid, "version_key": c.version(at(s, uid)["version"]), "method": method,
            "main_head": s["main"], "landed_commit": v(900)["head"],
            "main_ancestry_verified": True, "mapping": mapping, "evidence_ref": "landed/exact"}


def cli(*args):
    global _cli_number
    _cli_number += 1
    folder = RUNTIME / ("cli-" + str(_cli_number))
    folder.mkdir(mode=0o700)
    args = list(args)
    inputs = folder / "inputs"
    inputs.mkdir(mode=0o700)
    for flag in ("--snapshot", "--binding", "--plan", "--actual", "--outcomes"):
        if flag in args:
            index = args.index(flag) + 1
            target = inputs / (flag[2:] + ".json")
            target.write_bytes(Path(args[index]).read_bytes())
            args[index] = str(target)
    isolation = ["/usr/bin/bwrap", "--die-with-parent", "--unshare-pid", "--unshare-net",
                 "--ro-bind", "/", "/", "--proc", "/proc", "--dev", "/dev"]
    if "--journal" in args:
        area = str(Path(args[args.index("--journal") + 1]).parent)
        isolation += ["--bind", area, area]
    cmd = isolation + ["/usr/bin/python3", "-I", "-S", "-B", str(SOURCE), *args]
    (folder / "launch.json").write_text(json.dumps(cmd))
    (folder / "stdin.bin").write_bytes(b"")
    with (folder / "stdout.bin").open("wb") as out, (folder / "stderr.bin").open("wb") as err:
        run = subprocess.run(cmd, stdin=subprocess.DEVNULL, stdout=out, stderr=err, timeout=10)
    (folder / "result.json").write_text(json.dumps({"exit_code": run.returncode}))
    return subprocess.CompletedProcess(cmd, run.returncode,
        (folder / "stdout.bin").read_bytes(), (folder / "stderr.bin").read_bytes())


class GraphBehavior(unittest.TestCase):
    def test_shared_foundation_fork_once_and_singular_pr(self):
        s = healthy(snapshot())
        p = c.plan(s)
        self.assertEqual([o["unit"] for o in p["operations"]], ["A", "B", "C", "D", "X", "Z"])
        self.assertEqual(sum(o["unit"] == "A" for o in p["operations"]), 1)
        at(s, "C")["pr"] = 20
        with self.assertRaises(c.Invalid):
            c.plan(s)

    def test_diamond_order_and_changed_parent_new_tip_trace(self):
        s = snapshot()
        change(s, "A"); healthy(s)
        p = c.plan(s)
        self.assertEqual(p["stale"], ["A", "B", "C", "D", "X"])
        self.assertEqual(p["groups"][0]["order"], ["A", "C", "B", "D"])
        run = c.simulate(s, p, actual(s), outcomes(s))
        self.assertEqual([x["effect"] for x in run["trace"]], ["COMPOSED"] * 6)
        self.assertEqual(run["trace"][1]["new_bases"], [v(1010)["head"]])
        self.assertEqual(run["trace"][2]["new_bases"], [v(1010)["head"]])
        self.assertEqual(run["trace"][3]["new_bases"], [v(1030)["head"], v(1020)["head"]])
        self.assertEqual(run["trace"][4]["new_bases"], [v(1020)["head"]])
        self.assertTrue(all(not x["qualified"] for x in run["trace"]))

    def test_segments_cross_stack_trunk(self):
        s = snapshot("linear")
        s["units"] = [unit("A", 10), unit("B", 20), unit("X", 50)]
        s["segments"] = [{"id": "base", "units": ["A", "B"], "depends_on": []},
                         {"id": "other-stack", "units": ["X"], "depends_on": ["base"]}]
        s["groups"] = [{"id": "cross", "tips": ["X"], "order": None}]
        at(s, "B")["native_stack"] = "base-stack"
        at(s, "X")["native_stack"] = "other-stack"
        at(s, "X")["physical_base"] = {"ref": "refs/heads/B", "head": v(20)["head"]}
        p = c.plan(healthy(s))
        self.assertEqual(p["logical_dependencies"], {"A": [], "B": ["A"], "X": ["B"]})
        self.assertEqual(p["operations"][2]["new_bases"], [{"unit": "B", "tip": "$result:B"}])

    def test_conflict_symmetric_not_dependency_and_cycle_negative(self):
        s = healthy(snapshot())
        s["probes"].append(probe(s, ["C", "B"], kind="pair", status="CONFLICT"))
        p = c.plan(s)
        self.assertEqual(p["observed_conflicts"][0]["units"], ["B", "C"])
        self.assertEqual(p["logical_dependencies"]["B"], ["A"])
        self.assertEqual(p["logical_dependencies"]["C"], ["A"])
        at(s, "A")["requires"] = ["D"]
        with self.assertRaises(c.Invalid):
            c.plan(s)

    def test_partial_failure_stops_affected_descendants_parallel_continues(self):
        s = healthy(snapshot()); o = outcomes(s)
        o["B"] = {"status": "CONFLICT"}
        r = c.simulate(s, c.plan(s), actual(s), o)
        self.assertEqual([(x["unit"], x["effect"]) for x in r["trace"]],
                         [("A", "COMPOSED"), ("B", "CONFLICT"), ("C", "COMPOSED"),
                          ("D", "BLOCKED_DESCENDANT"), ("X", "BLOCKED_DESCENDANT"),
                          ("Z", "COMPOSED")])
        self.assertEqual(r["blocked"], ["B", "D", "X"])

    def test_pairwise_clean_combined_order_fails(self):
        s = healthy(snapshot())
        s["probes"] = [p for p in s["probes"] if p["units"] != ["A", "C", "B", "D"]]
        s["probes"] += [probe(s, ["B", "C"], "pair"),
                        probe(s, ["A", "C", "B", "D"], status="CONFLICT")]
        p = c.plan(s)
        self.assertEqual(p["groups"][0]["disposition"], "CONFLICT")
        self.assertEqual(p["groups"][2]["disposition"], "PLANNED")
        self.assertEqual(p["observed_conflicts"], [])

    def test_pairwise_only_unknown_and_textual_only_unknown(self):
        s = snapshot("linear")
        s["probes"] = [probe(s, ["A", "B"], kind="pair")]
        self.assertEqual(c.plan(s)["groups"][0]["disposition"], "UNKNOWN")
        s["probes"] = [probe(s, ["A", "B"], semantic=False)]
        self.assertEqual(c.plan(s)["groups"][0]["reason"], "ordered-textual-clean-semantic-unqualified")

    def test_partial_merge_actual_updated_main_does_not_replay(self):
        s = healthy(snapshot("linear"))
        s["merges"] = [merged(s, "A")]
        p = c.plan(s)
        self.assertEqual(p["landed"], ["A"])
        self.assertEqual([x["unit"] for x in p["operations"]], ["B"])
        r = c.simulate(s, p, actual(s), outcomes(s))
        self.assertEqual(r["trace"][0]["new_bases"], [s["main"]])

    def test_exact_squash_and_unknown_mapping_manual_frontier(self):
        s = healthy(snapshot("linear"))
        s["merges"] = [merged(s, "A", "squash")]
        self.assertEqual(c.plan(s)["landed"], ["A"])
        s["merges"][0]["mapping"] = "unknown"
        p = c.plan(s)
        self.assertEqual(p["landed"], [])
        self.assertEqual(p["manual_frontier"], ["A"])
        self.assertEqual(p["groups"][0]["disposition"], "UNKNOWN")
        r = c.simulate(s, p, actual(s), outcomes(s))
        self.assertEqual([x["effect"] for x in r["trace"]], ["UNKNOWN", "BLOCKED_DESCENDANT"])

    def test_message_patch_equivalence_not_accepted_and_wrong_main_unknown(self):
        s = healthy(snapshot("linear"))
        s["merges"] = [merged(s, "A")]
        s["merges"][0]["message"] = "looks merged"
        with self.assertRaises(c.Invalid):
            c.plan(s)
        del s["merges"][0]["message"]
        s["merges"][0]["main_head"] = v(987)["head"]
        self.assertEqual(c.plan(s)["manual_frontier"], ["A"])
        s["merges"] = [merged(s, "B")]
        with self.assertRaises(c.Invalid):
            c.plan(s)

    def test_stale_plan_and_exact_head_cas(self):
        s = healthy(snapshot()); p = c.plan(s)
        a = actual(s); a["units"]["B"]["version"] = v(987)
        r = c.simulate(s, p, a, outcomes(s))
        self.assertEqual([(x["unit"], x["effect"]) for x in r["trace"]],
                         [("A", "COMPOSED"), ("B", "CAS_MISMATCH"), ("C", "COMPOSED"),
                          ("D", "BLOCKED_DESCENDANT"), ("X", "BLOCKED_DESCENDANT"),
                          ("Z", "COMPOSED")])
        p["main"] = v(55)["head"]
        with self.assertRaises(c.Invalid):
            c.simulate(s, p, actual(s), outcomes(s))

    def test_base_membership_and_main_cas(self):
        s = healthy(snapshot())
        for field, value in (("physical_base", {"ref": "main", "head": v(55)["head"]}),
                             ("native_stack", "changed-stack")):
            a = actual(s); a["units"]["B"][field] = value
            r = c.simulate(s, c.plan(s), a, outcomes(s))
            self.assertEqual(r["blocked"], ["B", "D", "X"])
        a = actual(s); a["main"] = v(55)["head"]
        self.assertEqual(c.simulate(s, c.plan(s), a, outcomes(s))["blocked"],
                         ["A", "B", "C", "D", "X", "Z"])

    def test_evidence_exact_versions_and_conservation_negative(self):
        s = healthy(snapshot("linear"))
        at(s, "A")["evidence"] = [{"kind": "approval", "version_key": c.version(v(10)),
                                  "ref": "approval/a", "result": "PASS"},
                                 {"kind": "test", "version_key": c.version(v(999)),
                                  "ref": "test/old", "result": "PASS"}]
        p = c.plan(s)
        self.assertEqual([e["applicable"] for e in p["operations"][0]["evidence"]], [True, False])
        change(s, "A"); healthy(s)
        self.assertEqual([e["applicable"] for e in c.plan(s)["operations"][0]["evidence"]], [False, False])
        o = outcomes(s); o["A"]["preserved"]["tests"] = []
        r = c.simulate(s, c.plan(s), actual(s), o)
        self.assertEqual([x["effect"] for x in r["trace"]],
                         ["CONSERVATION_FAILURE", "BLOCKED_DESCENDANT"])

    def test_missing_and_counterpart_unadmitted_unknown(self):
        s = healthy(snapshot())
        at(s, "C")["admitted"] = False
        p = c.plan(s)
        self.assertEqual(p["groups"][0]["disposition"], "UNKNOWN")
        self.assertEqual(p["groups"][2]["disposition"], "PLANNED")
        s = snapshot("linear")
        self.assertEqual(c.plan(s)["groups"][0]["disposition"], "UNKNOWN")

    def test_conflict_paths_role_admission_not_filename_filter(self):
        s = healthy(snapshot("linear"))
        p = probe(s, ["A", "B"], status="CONFLICT")
        p["paths"] = [{"path": "dotenv/provider/model.py", "ordinary_safe": True}]
        s["probes"] = [p]
        self.assertEqual(c.plan(s)["problems"][0]["paths"][0]["path"], "dotenv/provider/model.py")
        p["paths"][0]["ordinary_safe"] = False
        with self.assertRaises(c.Invalid):
            c.plan(s)

    def test_unknown_or_protected_path_and_invalid_event_rejected(self):
        s = healthy(snapshot("linear"))
        p = probe(s, ["A", "B"], status="CONFLICT")
        p["admitted"] = False; s["probes"] = [p]
        with self.assertRaises(c.Invalid):
            c.plan(s)
        s = healthy(snapshot("linear")); change(s, "A")
        s["events"][0]["after"] = v(777)
        with self.assertRaises(c.Invalid):
            c.plan(s)

    def test_join_order_required_and_no_duplicate_shared_unit(self):
        s = snapshot()
        s["groups"][0]["order"] = None
        with self.assertRaises(c.Invalid):
            c.plan(s)
        s["groups"][0]["order"] = ["A", "C", "B", "A", "D"]
        with self.assertRaises(c.Invalid):
            c.plan(s)

    def test_typed_base_membership_and_merge_events(self):
        s = healthy(snapshot("linear"))
        for kind, before, after in (
            ("base", {"ref": "main", "head": v(99)["head"]}, at(s, "A")["physical_base"]),
            ("membership", "old-stack", None), ("merge", "pending", "evidence/landed")):
            t = copy.deepcopy(s)
            t["events"] = [{"kind": kind, "unit": "A", "before": before, "after": after,
                            "evidence_ref": "event/typed"}]
            self.assertEqual(c.plan(t)["stale"], ["A", "B"])
            self.assertEqual(c.plan(t)["landed"], [])

    def test_all_landed_no_probe_required(self):
        s = snapshot("linear")
        s["merges"] = [merged(s, "A"), merged(s, "B")]
        p = c.plan(s)
        self.assertEqual(p["operations"], [])
        self.assertEqual(p["problems"], [])


class AlertBehavior(unittest.TestCase):
    def setUp(self):
        self.area = RUNTIME / self._testMethodName
        self.area.mkdir(mode=0o700)

    def test_healthy_silent_two_unchanged_distinct_checks_repeat(self):
        s = healthy(snapshot("linear")); p = c.plan(s)
        self.assertEqual(c.alerts(s, p, "check-healthy"), [])
        s["probes"] = [probe(s, ["A", "B"], status="CONFLICT")]
        p = c.plan(s); sent = []
        def sender(alert):
            sent.append(alert["check_id"])
            return {"stage": "PUSHED", "board": c.BOARD, "recipient": c.RECIPIENT,
                    "notification_id": len(sent), "queue_message_id": "mock-queue"}
        with c.owner_lock(self.area / "owner.lock", c.RECIPIENT):
            journal = c.DeliveryJournal(self.area / "journal.json")
            for check in ("tick-1", "tick-2"):
                row = journal.deliver(check, c.alerts(s, p, check), p["plan_id"], sender)
                self.assertEqual(row["state"], "PUSHED")
        self.assertEqual(sent, ["tick-1", "tick-2"])

    def test_ambiguous_attempt_durable_no_blind_retry(self):
        s = snapshot("linear"); p = c.plan(s); notices = c.alerts(s, p, "tick-1")
        sent = []
        def uncertain(a):
            sent.append(a["alert_id"])
            raise TimeoutError()
        jpath = self.area / "journal.json"
        with c.owner_lock(self.area / "lock", c.RECIPIENT):
            row = c.DeliveryJournal(jpath).deliver("tick-1", notices, p["plan_id"], uncertain)
            self.assertEqual(row["state"], "AMBIGUOUS")
            row = c.DeliveryJournal(jpath).deliver("tick-1", notices, p["plan_id"], uncertain)
            self.assertEqual(row["state"], "AMBIGUOUS")
        self.assertEqual(len(sent), 1)

    def test_enqueue_push_ack_are_distinct_and_reconcile_no_send(self):
        s = snapshot("linear"); p = c.plan(s); ns = c.alerts(s, p, "tick")
        j = c.DeliveryJournal(self.area / "journal")
        receipt = {"stage": "ENQUEUED", "board": c.BOARD, "recipient": c.RECIPIENT, "notification_id": 9}
        row = j.deliver("tick", ns, p["plan_id"], lambda _: receipt)
        self.assertEqual(row["state"], "ENQUEUED")
        row = j.reconcile("tick", ns[0]["alert_id"], dict(receipt, stage="PUSHED", queue_message_id="q9"))
        self.assertEqual(row["state"], "PUSHED")
        row = j.reconcile("tick", ns[0]["alert_id"], dict(receipt, stage="RECIPIENT_ACK", ack_ref="qa/ack9"))
        self.assertEqual(row["state"], "RECIPIENT_ACK")
        with self.assertRaises(c.Invalid):
            j.reconcile("tick", ns[0]["alert_id"], receipt)

    def test_same_check_payload_mismatch_and_route_negative(self):
        s = snapshot("linear"); p = c.plan(s); ns = c.alerts(s, p, "tick")
        j = c.DeliveryJournal(self.area / "journal")
        j.prepare("tick", ns, p["plan_id"])
        with self.assertRaises(c.Invalid):
            j.prepare("tick", [], p["plan_id"])
        row = j.deliver("tick", ns, p["plan_id"], lambda _: {
            "stage": "PUSHED", "board": "wrong", "recipient": c.RECIPIENT,
            "notification_id": 1, "queue_message_id": "q"})
        self.assertEqual(row["state"], "AMBIGUOUS")

    def test_deferral_and_pr1230_cloud_exception(self):
        s = snapshot("linear")
        at(s, "B")["pr"] = 1230
        at(s, "B")["eligibility"].update(deferred=True, deferral_ref="work/explicit")
        s["violations"] = [{"unit": "B", "kind": k, "obligation": "obligation/" + k,
                            "evidence_ref": "evidence/violation"} for k in
                           ("stall", "whole_landing", "cloud_demo", "conservation_failure", "required_closure")]
        p = c.plan(s)
        self.assertEqual(p["groups"][0]["disposition"], "DEFERRED")
        self.assertEqual([a["disposition"] for a in c.alerts(s, p, "tick")],
                         ["cloud_demo", "conservation_failure", "required_closure"])
        at(s, "B")["eligibility"]["trigger"] = True
        self.assertIn("stall", [a["disposition"] for a in c.alerts(s, c.plan(s), "tick-2")])

    def test_deferred_unexpected_change_still_alerts_no_activation(self):
        s = snapshot("linear")
        at(s, "B")["eligibility"].update(deferred=True, deferral_ref="work/explicit")
        change(s, "B")
        p = c.plan(s)
        self.assertEqual(p["groups"][0]["disposition"], "DEFERRED")
        self.assertEqual([a["disposition"] for a in c.alerts(s, p, "tick")], ["CHANGE"])

    def test_board_protocol_build_only_and_exact_bindings(self):
        s = snapshot("linear"); p = c.plan(s)
        a = c.alerts(s, p, "tick")[0]
        argv = c.board_command(a, python="/usr/bin/python3",
                               board_cli="/home/nes/ai/tools/message-board/board.py",
                               catalog_home="/parent/must/bind/catalog", sender=c.RECIPIENT)
        self.assertEqual(argv[:5], ["/usr/bin/python3", "-I", "-S", "-B", "-c"])
        self.assertIn("/home/nes/ai/tools/message-board/board.py", argv[5])
        self.assertEqual(argv[argv.index("--to") + 1], c.RECIPIENT)
        self.assertEqual(json.loads(argv[argv.index("--text") + 1]), a)
        self.assertEqual(a["units"][0]["version"], v(10))

    def test_single_owner_lock_contends(self):
        with c.owner_lock(self.area / "owner.lock", c.RECIPIENT):
            with self.assertRaises(c.Invalid):
                with c.owner_lock(self.area / "owner.lock", c.RECIPIENT):
                    self.fail("second owner acquired same lock")


    def test_staleness_persists_checks_and_requires_exact_recomposition(self):
        s = healthy(snapshot("linear"))
        j = c.DeliveryJournal(self.area / "observer.json")
        first = j.observe(s)
        self.assertEqual(first["stale_units"], [])
        change(s, "A"); healthy(s)
        second = j.observe(s)
        self.assertEqual([x["unit"] for x in second["stale_units"]], ["A", "B"])
        s["events"] = []
        third = c.DeliveryJournal(self.area / "observer.json").observe(s)
        self.assertEqual([x["unit"] for x in third["stale_units"]], ["A", "B"])
        self.assertEqual([a["disposition"] for a in c.alerts(third, c.plan(third), "third")],
                         ["STALE", "STALE"])
        s["recomposed"] = [{"unit": u["id"], "version_key": c.version(u["version"]),
                            "evidence_ref": "owner/recomposition"} for u in s["units"]]
        fourth = c.DeliveryJournal(self.area / "observer.json").observe(s)
        self.assertEqual(fourth["stale_units"], [])
        self.assertEqual(c.alerts(fourth, c.plan(fourth), "fourth"), [])

    def test_observer_missing_events_main_moves_and_feed_gap(self):
        s = healthy(snapshot("linear"))
        path = self.area / "observer.json"
        c.DeliveryJournal(path).observe(s)
        at(s, "A")["version"] = v(765)
        healthy(s)
        result = c.DeliveryJournal(path).observe(s)
        self.assertEqual([x["unit"] for x in result["stale_units"]], ["A", "B"])
        s["feed"]["binding"] = "another-feed"
        with self.assertRaises(c.Invalid):
            c.DeliveryJournal(path).observe(s)
        s = healthy(snapshot("linear"))
        s["main"] = v(987)["head"]
        result = c.DeliveryJournal(path).observe(s)
        self.assertEqual([x["unit"] for x in result["stale_units"]], ["A", "B"])

    def test_explicit_whole_landing_deferral_not_PR_number(self):
        s = snapshot("linear")
        at(s, "B")["eligibility"].update(deferred=True, deferral_ref="work/explicit")
        s["violations"] = [{"unit": "B", "kind": "whole_landing", "obligation": "close/required",
                            "evidence_ref": "work/actual"}]
        self.assertEqual(c.alerts(s, c.plan(s), "tick"), [])
        at(s, "B")["eligibility"].update(deferred=False, deferral_ref=None, active=False)
        self.assertEqual([a["disposition"] for a in c.alerts(s, c.plan(s), "tick-2")], ["whole_landing"])

    def test_recomposition_without_ordered_qualification_does_not_clear_stale(self):
        s = snapshot("linear"); change(s, "A")
        s["recomposed"] = [{"unit": "A", "version_key": c.version(at(s, "A")["version"]),
                            "evidence_ref": "owner/recomposition"}]
        result = c.DeliveryJournal(self.area / "observer.json").observe(s)
        self.assertEqual([x["unit"] for x in result["stale_units"]], ["A", "B"])


class CLIBehavior(unittest.TestCase):
    def setUp(self):
        self.area = RUNTIME / self._testMethodName
        self.area.mkdir(mode=0o700)
        self.input = self.area / "snapshot.json"

    def write(self, value):
        self.input.write_text(json.dumps(value))
        return str(self.input)

    def test_real_cli_roundtrip_exit_semantics(self):
        s = healthy(snapshot("linear")); path = self.write(s)
        r = cli("plan", "--snapshot", path)
        self.assertEqual(r.returncode, 0, r.stderr)
        result = json.loads(r.stdout)
        self.assertEqual(result["groups"][0]["order"], ["A", "B"])
        s["probes"] = []; self.write(s)
        r = cli("alerts", "--snapshot", path, "--check-id", "cli-tick")
        self.assertEqual(r.returncode, 3, r.stderr)
        self.assertEqual(json.loads(r.stdout)[0]["recipient"], c.RECIPIENT)
        s["units"][0]["version"]["head"] = "bad"; self.write(s)
        r = cli("plan", "--snapshot", path)
        self.assertEqual(r.returncode, 2)
        self.assertEqual(r.stdout, b"")
        self.assertEqual(json.loads(r.stderr)["schema"], "stack-error/v1")

    def test_real_cli_simulation_and_failure(self):
        s = healthy(snapshot("linear")); self.write(s)
        paths = {}
        for name, obj in (("plan", c.plan(s)), ("actual", actual(s)), ("outcomes", outcomes(s))):
            paths[name] = self.area / (name + ".json")
            paths[name].write_text(json.dumps(obj))
        args = ["simulate", "--snapshot", str(self.input)]
        for name, path in paths.items():
            args += ["--" + name, str(path)]
        r = cli(*args)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual([x["new_bases"] for x in json.loads(r.stdout)["trace"]],
                         [[s["main"]], [v(1010)["head"]]])
        a = actual(s); a["units"]["A"]["version"] = v(666)
        paths["actual"].write_text(json.dumps(a))
        r = cli(*args)
        self.assertEqual(r.returncode, 3)
        self.assertEqual(json.loads(r.stdout)["blocked"], ["A", "B"])

    def test_once_immutable_binding_and_schedule_no_launch(self):
        s = healthy(snapshot("linear")); self.write(s)
        binding = {"schema": "stack-startup/v1",
                   "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                   "snapshot_sha256": hashlib.sha256(self.input.read_bytes()).hexdigest(),
                   "feed_binding": "fixture-feed", "feed_schema": "typed-fixture-v1", "owner": c.RECIPIENT}
        bpath = self.area / "binding.json"; bpath.write_text(json.dumps(binding))
        args = ["once", "--snapshot", str(self.input), "--binding", str(bpath),
                "--journal", str(self.area / "journal"), "--lock", str(self.area / "owner.lock"),
                "--check-id", "once-tick"]
        r = cli(*args)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout)["delivery"]["state"], "SILENT")
        binding["source_sha256"] = "0" * 64; bpath.write_text(json.dumps(binding))
        self.assertEqual(cli(*args).returncode, 2)
        schedule = cli("schedule")
        self.assertEqual(schedule.returncode, 0)
        self.assertFalse(json.loads(schedule.stdout)["launch_background"])
        self.assertEqual(json.loads(schedule.stdout)["cadence_seconds"], 300)

    def test_invalid_duplicate_json_bounded_and_unknown_fields(self):
        self.input.write_text('{"schema":"one","schema":"two"}')
        self.assertEqual(cli("plan", "--snapshot", str(self.input)).returncode, 2)
        self.input.write_bytes(b" " * (c.MAX_BYTES + 1))
        self.assertEqual(cli("plan", "--snapshot", str(self.input)).returncode, 2)
        s = healthy(snapshot("linear")); s["patch_body"] = "not-admitted"
        self.write(s)
        self.assertEqual(cli("plan", "--snapshot", str(self.input)).returncode, 2)

    def test_native_cli_contract_preserves_existing_stack(self):
        s = snapshot("linear")
        prs = [1639, 1640, 1647, 1648, 1645, 1641]
        s["units"] = [unit("P" + str(p), p, [] if i == 0 else ["P" + str(prs[i - 1])])
                      for i, p in enumerate(prs)]
        for u in s["units"]:
            u["native_stack"] = "1649"
        s["groups"] = [{"id": "native", "tips": ["P1641"], "order": None}]
        self.write(s)
        r = cli("native-contract", "--snapshot", str(self.input), "--mode", "feature", "--unit", "P1647")
        self.assertEqual(r.returncode, 0, r.stderr)
        result = json.loads(r.stdout)
        self.assertEqual(result["commands"], [["gh", "stack", "rebase", "--upstack"],
                                              ["gh", "stack", "push"]])
        self.assertFalse(result["mutations_executed"])
        at(s, "P1647")["native_stack"] = None; self.write(s)
        self.assertEqual(cli("native-contract", "--snapshot", str(self.input), "--mode", "whole").returncode, 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
