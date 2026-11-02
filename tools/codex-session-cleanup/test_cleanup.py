import copy
import base64
import hashlib
import json
import os
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import cleanup as c


IDS = [f"00000000-0000-4000-8000-{i:012x}" for i in range(20)]
NOW = 2_000_000
TASK_DIR = os.environ.get("CODEX_CLEANUP_TEST_TMP")  # Optional isolated fixture parent.


def thread(i=0, source="exec", updated=NOW - 86400, parent=None, **kw):
    item = {"id": IDS[i], "source": source, "createdAt": updated - 100,
            "updatedAt": updated, "recencyAt": None, "parentThreadId": parent,
            "sessionId": parent or IDS[i], "forkedFromId": None,
            "ephemeral": False, "status": {"type": "notLoaded"},
            "historyMode": "legacy", "isPinned": False, "loaded": False,
            "archived": False}
    item.update(kw)
    return item


def plan_for(*members, retain=(), now=NOW):
    threads = {x["id"]: x for x in members}
    children = {x["id"]: set() for x in members}
    for x in members:
        if x["parentThreadId"] is not None:
            children[x["parentThreadId"]].add(x["id"])
    return c.make_plan({"fixture": True}, threads, children, set(retain), now, 86400)


class FakeRpc:
    def __init__(self, active, archived=(), loaded=(), fail=None, page_loop=False,
                 goals=None, related=None):
        self.active = list(active)
        self.archived = list(archived)
        self.loaded = list(loaded)
        self.fail = fail
        self.page_loop = page_loop
        self.calls = []
        self.deleted = False
        self.goals = goals or {}
        self.related = related or {}

    def close(self):
        pass

    def request(self, method, params):
        self.calls.append((method, params))
        if method == self.fail:
            raise c.Refuse("fake server refusal")
        if method == "thread/list":
            if "parentThreadId" in params:
                data = [item for item in self.related.get(params["parentThreadId"], ())
                        if item.get("archived", False) == params["archived"]]
            else:
                data = self.archived if params["archived"] else self.active
            if self.page_loop:
                return {"data": data[:1], "nextCursor": "repeat"}
            start = int(params.get("cursor", "0"))
            end = start + params["limit"]
            return {"data": data[start:end], "nextCursor": str(end) if end < len(data) else None}
        if method == "thread/loaded/list":
            return {"data": self.loaded, "nextCursor": None}
        if method == "thread/read":
            item = next(x for x in self.active + self.archived if x["id"] == params["threadId"])
            return {"thread": item}
        if method == "thread/goal/get":
            return {"goal": self.goals.get(params["threadId"])}
        if method == "thread/delete":
            self.deleted = True
            return {}
        raise AssertionError(method)


def db_fixture(directory, members, edges=()):
    db = sqlite3.connect(directory / "state_5.sqlite")
    db.execute("CREATE TABLE threads(id TEXT PRIMARY KEY,is_pinned INTEGER,attached_thread_parent_id TEXT)")
    db.execute("CREATE TABLE thread_spawn_edges(parent_thread_id TEXT,child_thread_id TEXT,status TEXT)")
    db.executemany("INSERT INTO threads VALUES(?,?,?)", [(x["id"], int(x["isPinned"]), x["parentThreadId"]) for x in members])
    db.executemany("INSERT INTO thread_spawn_edges VALUES(?,?,?)", [(a,b,"spawned") for a,b in edges])
    db.commit()
    db.close()


class PolicyTests(unittest.TestCase):
    def test_exec_origin_is_only_an_unconfirmed_review_candidate(self):
        raw = thread(turns=[{"items": [{"type": "userMessage", "content": "initial"}]},
                            {"items": [{"type": "userMessage", "content": "followup"}]}])
        item = {**thread(), **c.thread_record(raw)}
        plan = c.prepare_plan(FakeRpc([raw]), {}, {IDS[0]: item}, {IDS[0]: set()},
                              set(), NOW, 86400, 10)
        self.assertEqual(len(plan["candidates"]), 1)
        self.assertFalse(plan["headlessUseConfirmed"])
        self.assertIsNone(plan["confirmedHeadlessIds"])
        self.assertNotIn("followup", json.dumps(plan))

    def test_confirmed_headless_resumes_may_have_multiple_input_turns(self):
        # Roles do not identify a human; confirmed noninteractive resumes can
        # provide more user-role inputs. No turn/body RPC is required.
        raw = thread(turns=[{"id": "initial"}, {"id": "exec-resume-1"},
                            {"id": "exec-resume-2"}])
        item = {**thread(), **c.thread_record(raw)}
        rpc = FakeRpc([raw])
        plan = c.prepare_plan(rpc, {}, {IDS[0]: item}, {IDS[0]: set()},
                              set(), NOW, 86400, 10, {IDS[0]})
        self.assertTrue(plan["headlessUseConfirmed"])
        self.assertEqual([x["root"] for x in plan["candidates"]], [IDS[0]])
        self.assertEqual([method for method, _ in rpc.calls], ["thread/goal/get"])

    def test_unconfirmed_descendant_blocks_entire_cascade(self):
        parent, child = thread(), thread(1, source="subAgent", parent=IDS[0])
        members = {x["id"]: x for x in (parent, child)}
        children = {IDS[0]: {IDS[1]}, IDS[1]: set()}
        plan = c.prepare_plan(FakeRpc([parent, child]), {}, members, children,
                              set(), NOW, 86400, 10, {IDS[0]})
        self.assertEqual(plan["candidates"], [])
        self.assertEqual(plan["headlessUnconfirmedRootsExamined"], 1)
        plan = c.prepare_plan(FakeRpc([parent, child]), {}, members, children,
                              set(), NOW, 86400, 10, {IDS[0], IDS[1]})
        self.assertEqual(len(plan["candidates"]), 1)

    def test_confirmation_never_overrides_interactive_origin_or_retention(self):
        a, b = thread(source="cli"), thread(1)
        members = {x["id"]: x for x in (a, b)}
        plan = c.prepare_plan(FakeRpc([a, b]), {}, members,
                              {IDS[0]: set(), IDS[1]: set()}, {IDS[1]},
                              NOW, 86400, 10, {IDS[0], IDS[1]})
        self.assertEqual(plan["candidates"], [])

    def test_page_projection_discards_unneeded_reply_fields(self):
        members = [thread(i, preview="PRIVATE" * 1000) for i in range(15)]
        result = c.pages(FakeRpc(members), "thread/list",
                         {"archived": False, "limit": 10}, 10,
                         project=c.thread_record)
        self.assertEqual(len(result), 15)
        self.assertTrue(all("preview" not in item for item in result))
        self.assertNotIn("PRIVATE", json.dumps(result))

    def test_small_metadata_pages_preserve_complete_inventory(self):
        members = [thread(i) for i in range(15)]
        with tempfile.TemporaryDirectory(dir=TASK_DIR) as name:
            profile = Path(name)
            db_fixture(profile, members)
            rpc = FakeRpc(members)
            inventory, _ = c.snapshot(rpc, profile, 10)
        self.assertEqual(set(inventory), {item["id"] for item in members})
        listings = [params for method, params in rpc.calls if method == "thread/list"]
        self.assertEqual([p["limit"] for p in listings], [10, 10, 10])
        self.assertEqual(listings[1]["cursor"], "10")

    def test_managed_socket_symlink_has_bound_target_and_link_identities(self):
        with tempfile.TemporaryDirectory(dir=TASK_DIR) as name:
            base = Path(name)
            runtime = base / f"codex-daemon-{os.geteuid()}"
            runtime.mkdir(mode=0o700)
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            previous = os.getcwd()
            try:
                os.chdir(runtime)
                sock.bind("a" * 64)
            finally:
                os.chdir(previous)
            try:
                link = base / "control.sock"
                link.symlink_to(runtime / ("a" * 64))
                with patch.object(c, "DAEMON_RUNTIME_BASE", base):
                    identity = c.file_identity(link, "socket")
                    self.assertEqual(identity["canonicalPath"], str(runtime / ("a" * 64)))
                    self.assertEqual(identity["linkInode"], link.lstat().st_ino)
                    runtime.chmod(0o755)
                    with self.assertRaises(c.Refuse):
                        c.file_identity(link, "socket")
            finally:
                sock.close()

    def test_unmanaged_socket_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory(dir=TASK_DIR) as name:
            base = Path(name)
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            previous = os.getcwd()
            try:
                os.chdir(base)
                sock.bind("actual.sock")
            finally:
                os.chdir(previous)
            try:
                link = base / "control.sock"
                link.symlink_to(base / "actual.sock")
                with self.assertRaises(c.Refuse):
                    c.file_identity(link, "socket")
            finally:
                sock.close()

    def test_plan_batches_oldest_roots_without_manual_mass_retention(self):
        members = [thread(i, updated=NOW - 86400 - i * 10) for i in range(15)]
        threads = {t["id"]: t for t in members}
        children = {t["id"]: set() for t in members}
        plan = c.prepare_plan(FakeRpc(members), {"fixture": True}, threads, children,
                              set(), NOW, 86400, 3)
        self.assertEqual([x["root"] for x in plan["candidates"]], IDS[12:15][::-1])
        self.assertEqual(plan["preliminaryRootCount"], 15)
        self.assertEqual(plan["unexaminedRootCount"], 12)

    def test_unfinished_goals_protect_old_unloaded_sessions(self):
        members = [thread(0), thread(1)]
        threads = {t["id"]: t for t in members}
        children = {t["id"]: set() for t in members}
        for status in ("active", "paused", "blocked", "budget_limited", "unknown"):
            rpc = FakeRpc(members, goals={IDS[0]: {"status": status, "objective": "SECRET"}})
            plan = c.prepare_plan(rpc, {"fixture": True}, threads, children, set(), NOW, 86400, 2)
            self.assertEqual([x["root"] for x in plan["candidates"]], [IDS[1]])
            self.assertNotIn("SECRET", c.canonical(plan).decode())

    def test_unfinished_descendant_goal_protects_entire_cascade(self):
        parent, child = thread(), thread(1, parent=IDS[0])
        rpc = FakeRpc([parent, child], goals={IDS[1]: {"status": "paused"}})
        plan = c.prepare_plan(rpc, {"fixture": True}, {IDS[0]: parent, IDS[1]: child},
                              {IDS[0]: {IDS[1]}, IDS[1]: set()}, set(), NOW, 86400, 10)
        self.assertEqual(plan["candidates"], [])

    def test_goal_metadata_unavailable_refuses(self):
        item = thread()
        with self.assertRaises(c.Refuse):
            c.prepare_plan(FakeRpc([item], fail="thread/goal/get"), {"fixture": True},
                           {IDS[0]: item}, {IDS[0]: set()}, set(), NOW, 86400, 10)

    def test_exact_24_hours_and_future(self):
        self.assertEqual(len(plan_for(thread()).get("candidates")), 1)
        self.assertEqual(len(plan_for(thread(updated=NOW - 86399))["candidates"]), 0)
        self.assertEqual(len(plan_for(thread(updated=NOW + 1))["candidates"]), 0)
        self.assertEqual(len(plan_for(thread(recencyAt=NOW - 100))["candidates"]), 0)

    def test_source_and_headless_provenance(self):
        for source in ("cli", "vscode", "appServer", "unknown", {"custom": "exec"}):
            self.assertEqual(plan_for(thread(source=source))["candidates"], [])
        self.assertEqual(len(plan_for(thread(source="exec"))["candidates"]), 1)

    def test_all_protected_states_and_retains(self):
        for changes in ({"isPinned": True}, {"loaded": True}, {"status": {"type": "idle"}},
                        {"status": {"type": "active"}}, {"status": {"type": "systemError"}},
                        {"ephemeral": True}):
            self.assertEqual(plan_for(thread(**changes))["candidates"], [])
        self.assertEqual(plan_for(thread(), retain=[IDS[0]])["candidates"], [])

    def test_descendant_blocks_entire_cascade(self):
        parent = thread()
        for changes in ({"isPinned": True}, {"loaded": True}, {"source": "cli"},
                        {"updatedAt": NOW - 1}, {"status": {"type": "active"}}):
            child = thread(1, parent=IDS[0], **{"source": "subAgent", **changes})
            self.assertEqual(plan_for(parent, child)["candidates"], [])
        child = thread(1, source="subAgent", parent=IDS[0])
        self.assertEqual(len(plan_for(parent, child)["candidates"][0]["cascade"]), 2)
        self.assertEqual(plan_for(parent, child, retain=[IDS[1]])["candidates"], [])

    def test_recently_resumed_old_thread_remains_protected_when_loaded(self):
        old = thread(loaded=True)
        self.assertEqual(plan_for(old)["candidates"], [])

    def test_invalid_retention_and_age(self):
        with tempfile.TemporaryDirectory(dir=TASK_DIR) as tmp:
            path = Path(tmp) / "retain.json"
            path.write_text(json.dumps([IDS[0], IDS[0]]))
            with self.assertRaises(c.Refuse): c.read_retained(path)
        with self.assertRaises(c.Refuse):
            c.main(["plan", "--profile", "/none", "--socket", "/none",
                    "--retain", "/none", "--plan", "/none", "--min-age-hours", "23"])

    def test_metadata_whitelist(self):
        t = thread()
        t.update({"preview": "SECRET PROMPT", "name": "SECRET TITLE", "cwd": "/private",
                  "turns": [{"text": "SECRET TURN"}], "path": "/private/rollout"})
        record = c.thread_record(t)
        self.assertNotIn("SECRET", json.dumps(record))
        self.assertNotIn("cwd", record)
        self.assertNotIn("turns", record)

    def test_structured_subagent_source_keeps_only_kind_and_parent_uuid(self):
        t = thread(1, parent=IDS[0])
        t["source"] = {"subAgent": {"thread_spawn": {"parent_thread_id": IDS[0],
                                                   "agent_role": "SECRET INSTRUCTION",
                                                   "depth": 1}}}
        record = c.thread_record(t)
        self.assertEqual(record["source"], "subAgentThreadSpawn")
        self.assertEqual(record["sourceParentThreadId"], IDS[0])
        self.assertNotIn("SECRET", json.dumps(record))
        parent = c.thread_record(thread())
        for item in (parent, record):
            item.update({"isPinned": False, "loaded": False, "archived": False})
        self.assertEqual(len(plan_for(parent, record)["candidates"][0]["cascade"]), 2)

    def test_legacy_paginated_both_metadata_only(self):
        legacy = thread(0, historyMode="legacy")
        paginated = thread(1, historyMode="paginated")
        self.assertEqual(len(plan_for(legacy, paginated)["candidates"]), 2)

    def test_incomplete_pages_and_lineage_refuse(self):
        with tempfile.TemporaryDirectory(dir=TASK_DIR) as tmp:
            directory = Path(tmp)
            t = thread()
            db_fixture(directory, [t])
            fake = FakeRpc([t], page_loop=True)
            with self.assertRaises(c.Refuse): c.snapshot(fake, directory, 2)
            child = thread(1, source="subAgent", parent=IDS[0])
            fake = FakeRpc([t, child])
            with self.assertRaises(c.Refuse): c.snapshot(fake, directory, 2)
            db_fixture2 = directory / "second"
            db_fixture2.mkdir()
            db_fixture(db_fixture2, [t], [(IDS[0], IDS[2])])
            with self.assertRaises(c.Refuse): c.snapshot(FakeRpc([t]), db_fixture2, 2)

    def test_provisional_plan_retains_unlisted_index_entries(self):
        visible, hidden = thread(), thread(1)
        with tempfile.TemporaryDirectory(dir=TASK_DIR) as name:
            profile = Path(name)
            db_fixture(profile, [visible, hidden])
            rpc = FakeRpc([visible])
            with self.assertRaises(c.Refuse):
                c.snapshot(rpc, profile, 10)
            members, children = c.snapshot(rpc, profile, 10, allow_unlisted=True)
        plan = c.prepare_plan(rpc, {}, members, children, set(), NOW, 86400, 10)
        self.assertEqual(plan["indexOnlyRetainedCount"], 1)
        self.assertFalse(plan["inventoryCompleteForApply"])
        self.assertEqual([x["root"] for x in plan["candidates"]], [IDS[0]])
        self.assertFalse(c.qualified(members[IDS[1]], NOW, 86400, set(), root=True))

    def test_unlisted_descendant_blocks_provisional_root(self):
        visible, hidden = thread(), thread(1, parent=IDS[0])
        with tempfile.TemporaryDirectory(dir=TASK_DIR) as name:
            profile = Path(name)
            db_fixture(profile, [visible, hidden], [(IDS[0], IDS[1])])
            rpc = FakeRpc([visible])
            members, children = c.snapshot(rpc, profile, 10, allow_unlisted=True)
        plan = c.prepare_plan(rpc, {}, members, children, set(), NOW, 86400, 10)
        self.assertEqual(plan["candidates"], [])
        self.assertEqual(plan["indexOnlyRetainedCount"], 1)

    def test_expected_hidden_spawn_is_recovered_and_retained(self):
        parent = thread()
        hidden = thread(1, source={"subAgent": {"thread_spawn": {
            "parent_thread_id": IDS[0], "agent_role": "PRIVATE"}}},
            parent=IDS[0], preview="SECRET PREVIEW", name="SECRET TITLE", path="/private")
        with tempfile.TemporaryDirectory(dir=TASK_DIR) as name:
            profile = Path(name)
            db_fixture(profile, [parent, hidden], [(IDS[0], IDS[1])])
            rpc = FakeRpc([parent], related={IDS[0]: [hidden]})
            members, children = c.snapshot(rpc, profile, 3)
        plan = c.prepare_plan(rpc, {}, members, children, set(), NOW, 86400, 10)
        self.assertTrue(members[IDS[1]]["expectedHidden"])
        self.assertEqual(children[IDS[0]], {IDS[1]})
        self.assertEqual(plan["hiddenIndexedRetainedCount"], 1)
        self.assertEqual(plan["indexOnlyRetainedCount"], 0)
        self.assertTrue(plan["inventoryCompleteForApply"])
        self.assertEqual(plan["candidates"], [])
        self.assertNotIn("SECRET", json.dumps(plan))
        listings = [p for method, p in rpc.calls if method == "thread/list" and
                    "parentThreadId" in p]
        self.assertEqual(len(listings), 2)
        self.assertTrue(all(p["useStateDbOnly"] and p["modelProviders"] == [] and
                            p["sourceKinds"] == ["subAgentThreadSpawn"] and
                            p["limit"] == 10 for p in listings))

    def test_hidden_spawn_plus_unavailable_row_keeps_plan_provisional(self):
        parent = thread()
        hidden = thread(1, source={"subAgent": {"thread_spawn": {
            "parent_thread_id": IDS[0]}}}, parent=IDS[0])
        unknown = thread(2, source="vscode")
        with tempfile.TemporaryDirectory(dir=TASK_DIR) as name:
            profile = Path(name)
            db_fixture(profile, [parent, hidden, unknown], [(IDS[0], IDS[1])])
            rpc = FakeRpc([parent], related={IDS[0]: [hidden]})
            members, children = c.snapshot(rpc, profile, 3, allow_unlisted=True)
            with self.assertRaises(c.Refuse):
                c.snapshot(rpc, profile, 3)
        plan = c.prepare_plan(rpc, {}, members, children, set(), NOW, 86400, 10)
        self.assertTrue(members[IDS[2]]["metadataUnavailable"])
        self.assertEqual(plan["hiddenIndexedRetainedCount"], 1)
        self.assertEqual(plan["indexOnlyRetainedCount"], 1)
        self.assertFalse(plan["inventoryCompleteForApply"])
        self.assertEqual(plan["candidates"], [])

    def test_visible_active_spawn_sibling_does_not_block_hidden_recovery(self):
        parent = thread()
        spawn_source = {"subAgent": {"thread_spawn": {"parent_thread_id": IDS[0]}}}
        visible = thread(1, source=spawn_source, parent=IDS[0],
                         status={"type": "active"})
        hidden = thread(2, source=spawn_source, parent=IDS[0])
        with tempfile.TemporaryDirectory(dir=TASK_DIR) as name:
            profile = Path(name)
            db_fixture(profile, [parent, visible, hidden],
                       [(IDS[0], IDS[1]), (IDS[0], IDS[2])])
            rpc = FakeRpc([parent, visible], related={IDS[0]: [visible, hidden]})
            members, children = c.snapshot(rpc, profile, 3)
        self.assertTrue(members[IDS[2]]["expectedHidden"])
        self.assertNotIn("expectedHidden", members[IDS[1]])
        self.assertEqual(children[IDS[0]], {IDS[1], IDS[2]})

    def test_relationship_rejects_mismatch_foreign_and_duplicate(self):
        parent = thread()
        hidden = thread(1, source={"subAgent": {"thread_spawn": {
            "parent_thread_id": IDS[0]}}}, parent=IDS[0])
        cases = [
            [dict(hidden, source={"subAgent": {"thread_spawn": {
                "parent_thread_id": IDS[2]}}})],
            [dict(hidden, parentThreadId=IDS[2])],
            [dict(hidden, ephemeral=True)],
            [dict(hidden, status={"type": "active"})],
            [dict(hidden, id=IDS[2])],
            [hidden, hidden],
        ]
        with tempfile.TemporaryDirectory(dir=TASK_DIR) as name:
            profile = Path(name)
            db_fixture(profile, [parent, hidden], [(IDS[0], IDS[1])])
            for related in cases:
                with self.subTest(related=related):
                    rpc = FakeRpc([parent], related={IDS[0]: related})
                    with self.assertRaises(c.Refuse):
                        c.snapshot(rpc, profile, 3, allow_unlisted=True)

    def test_hidden_with_multiple_spawn_parents_refuses(self):
        parent = thread()
        hidden = thread(1, source={"subAgent": {"thread_spawn": {
            "parent_thread_id": IDS[0]}}}, parent=IDS[0])
        other = thread(2)
        with tempfile.TemporaryDirectory(dir=TASK_DIR) as name:
            profile = Path(name)
            db_fixture(profile, [parent, hidden, other],
                       [(IDS[0], IDS[1]), (IDS[2], IDS[1])])
            rpc = FakeRpc([parent, other], related={IDS[0]: [hidden]})
            with self.assertRaisesRegex(c.Refuse, "multiple spawn parents"):
                c.snapshot(rpc, profile, 3, allow_unlisted=True)

    def test_relationship_pagination_has_shared_page_budget(self):
        parent = thread()
        hidden = [thread(i, source={"subAgent": {"thread_spawn": {
            "parent_thread_id": IDS[0]}}}, parent=IDS[0], preview="PRIVATE")
                  for i in range(1, 12)]
        with tempfile.TemporaryDirectory(dir=TASK_DIR) as name:
            profile = Path(name)
            db_fixture(profile, [parent, *hidden], [(IDS[0], x["id"]) for x in hidden])
            rpc = FakeRpc([parent], related={IDS[0]: hidden})
            with self.assertRaisesRegex(c.Refuse, "relationship page budget"):
                c.snapshot(rpc, profile, 2, allow_unlisted=True)
            rpc = FakeRpc([parent], related={IDS[0]: hidden})
            members, children = c.snapshot(rpc, profile, 3)
        self.assertEqual(len(members), 12)
        self.assertEqual(len(children[IDS[0]]), 11)
        relation_pages = [p for method, p in rpc.calls if method == "thread/list" and
                          "parentThreadId" in p]
        self.assertEqual(len(relation_pages), 3)
        self.assertEqual(relation_pages[1]["cursor"], "10")

    def test_optional_final_cursor_and_full_page_without_cursor(self):
        class MissingCursor:
            def __init__(self, count): self.count = count
            def request(self, method, params): return {"data": [IDS[0]] * self.count}
        self.assertEqual(c.pages(MissingCursor(1), "thread/loaded/list", {"limit": 100}, 2), [IDS[0]])
        with self.assertRaises(c.Refuse):
            c.pages(MissingCursor(100), "thread/loaded/list", {"limit": 100}, 2)

    def test_pin_and_spawn_edges_from_read_only_state(self):
        with tempfile.TemporaryDirectory(dir=TASK_DIR) as tmp:
            directory = Path(tmp)
            a, b = thread(), thread(1, source="subAgent", isPinned=True)
            db_fixture(directory, [a, b], [(IDS[0], IDS[1])])
            fake = FakeRpc([a, b])
            threads, children = c.snapshot(fake, directory, 2)
            self.assertTrue(threads[IDS[1]]["isPinned"])
            self.assertEqual(children[IDS[0]], {IDS[1]})
            self.assertEqual(c.make_plan({"fixture": True}, threads, children, set(), NOW, 86400)["candidates"], [])
            self.assertEqual([m for m, _ in fake.calls if m.startswith("thread/")],
                             ["thread/list", "thread/list", "thread/loaded/list"])


class ApplyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=TASK_DIR)
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.identity = {"profile": {"path": str(self.base), "device": 1, "inode": 2},
                         "socket": {"path": str(self.base / "sock"), "device": 1, "inode": 3},
                         "stateDb": {"path": str(self.base / "state_5.sqlite"), "device": 1, "inode": 4}}
        self.t = thread(updated=1)
        self.threads = {IDS[0]: self.t}
        self.children = {IDS[0]: set()}
        self.retain = self.base / "retain.json"
        self.retain.write_text("[]")
        self.confirmed = self.base / "confirmed-headless.json"
        self.confirmed.write_text(json.dumps([IDS[0]]))
        self.plan = self.base / "plan.json"
        self.receipt = self.base / "receipt.jsonl"
        self.args = ["apply", "--profile", str(self.base), "--socket", str(self.base / "sock"),
                     "--retain", str(self.retain), "--confirmed-headless", str(self.confirmed),
                     "--plan", str(self.plan),
                     "--receipt", str(self.receipt), "--exclusive-maintenance", "--complete-index"]

    def run_apply(self, fake):
        now = int(__import__('time').time())
        self.t["createdAt"] = 1
        self.t["updatedAt"] = 1
        plan = c.prepare_plan(fake, self.identity, self.threads, self.children, set(), now, 86400, 10,
                              {IDS[0]})
        fake.calls.clear()
        self.plan.write_bytes(c.canonical(plan))
        def snapshot(*args):
            return ({}, {}) if fake.deleted else (self.threads, self.children)
        with patch.object(c, "check_cli"), patch.object(c, "profile_identity", return_value=self.identity), \
             patch.object(c, "Rpc", return_value=fake), patch.object(c, "snapshot", side_effect=snapshot), \
             patch.object(c, "exact_read"):
            return c.main(self.args)

    def test_apply_receipt_and_no_replay(self):
        fake = FakeRpc([self.t])
        self.assertEqual(self.run_apply(fake), 0)
        events = [json.loads(line) for line in self.receipt.read_text().splitlines()]
        self.assertEqual([x["event"] for x in events], ["begin", "intent", "success", "complete"])
        self.assertEqual([m for m, _ in fake.calls].count("thread/delete"), 1)
        with self.assertRaises(FileExistsError): self.run_apply(fake)
        self.assertNotIn("thread/delete", [m for m, _ in fake.calls])

    def test_apply_without_confirmation_refuses_before_profile_access(self):
        args = self.args.copy()
        index = args.index("--confirmed-headless")
        del args[index:index + 2]
        with patch.object(c, "check_cli") as cli, patch.object(c, "Rpc") as rpc:
            with self.assertRaisesRegex(c.Refuse, "exec origin alone"):
                c.main(args)
        cli.assert_not_called()
        rpc.assert_not_called()
        self.assertFalse(self.receipt.exists())

    def test_unconfirmed_plan_cannot_be_promoted_by_apply_flag(self):
        fake = FakeRpc([self.t])
        plan = c.prepare_plan(fake, self.identity, self.threads, self.children, set(),
                              int(time.time()), 86400, 10)
        self.plan.write_bytes(c.canonical(plan))
        fake.calls.clear()
        with patch.object(c, "check_cli"), patch.object(c, "profile_identity", return_value=self.identity), \
             patch.object(c, "Rpc", return_value=fake):
            with self.assertRaisesRegex(c.Refuse, "headless use unconfirmed"):
                c.main(self.args)
        self.assertFalse(self.receipt.exists())
        self.assertFalse(fake.calls)

    def test_old_plan_and_changed_confirmation_refuse_before_intent(self):
        fake = FakeRpc([self.t])
        plan = c.prepare_plan(fake, self.identity, self.threads, self.children, set(),
                              int(time.time()), 86400, 10, {IDS[0]})
        old_plan = copy.deepcopy(plan)
        old_plan.update(format=3)
        old_plan.pop("planId")
        old_plan["planId"] = c.digest(old_plan)
        with patch.object(c, "check_cli"), patch.object(c, "profile_identity", return_value=self.identity), \
             patch.object(c, "Rpc", return_value=fake):
            self.plan.write_bytes(c.canonical(old_plan))
            with self.assertRaisesRegex(c.Refuse, "plan format invalid"):
                c.main(self.args)
            self.plan.write_bytes(c.canonical(plan))
            self.confirmed.write_text("[]")
            with self.assertRaisesRegex(c.Refuse, "confirmation changed"):
                c.main(self.args)
        self.assertFalse(self.receipt.exists())
        self.assertNotIn("thread/delete", [m for m, _ in fake.calls])

    def test_provisional_plan_cannot_apply_even_with_maintenance_assertions(self):
        fake = FakeRpc([self.t])
        plan = c.prepare_plan(fake, self.identity, self.threads, self.children,
                              set(), int(time.time()), 86400, 10, {IDS[0]})
        plan.update(inventoryCompleteForApply=False, indexOnlyRetainedCount=1)
        plan.pop("planId")
        plan["planId"] = c.digest(plan)
        self.plan.write_bytes(c.canonical(plan))
        fake.calls.clear()
        with patch.object(c, "check_cli"), patch.object(c, "profile_identity", return_value=self.identity), \
             patch.object(c, "Rpc", return_value=fake):
            with self.assertRaisesRegex(c.Refuse, "provisional plan cannot be applied"):
                c.main(self.args)
        self.assertFalse(self.receipt.exists())
        self.assertNotIn("thread/delete", [method for method, _ in fake.calls])

    def test_server_refusal_keeps_uncertain_intent_and_no_replay(self):
        with self.assertRaises(c.Refuse): self.run_apply(FakeRpc([self.t], fail="thread/delete"))
        self.assertEqual([json.loads(x)["event"] for x in self.receipt.read_text().splitlines()],
                         ["begin", "intent", "stopped"])
        with self.assertRaises(FileExistsError): self.run_apply(FakeRpc([self.t]))

    def test_goal_started_after_rebuild_blocks_delete_before_intent(self):
        class GoalChanged(FakeRpc):
            def request(self, method, params):
                if method == "thread/goal/get" and any(m == method for m, _ in self.calls):
                    self.calls.append((method, params))
                    return {"goal": {"status": "active", "objective": "SECRET"}}
                return super().request(method, params)
        fake = GoalChanged([self.t])
        with self.assertRaises(c.Refuse):
            self.run_apply(fake)
        self.assertNotIn("thread/delete", [m for m, _ in fake.calls])
        self.assertEqual([json.loads(x)["event"] for x in self.receipt.read_text().splitlines()],
                         ["begin", "stopped"])
        self.assertNotIn("SECRET", self.receipt.read_text())

    def test_plan_or_profile_change_refuses_before_effect(self):
        fake = FakeRpc([self.t])
        with patch.object(c, "check_cli"), patch.object(c, "profile_identity", return_value=self.identity), \
             patch.object(c, "Rpc", return_value=fake):
            bad = {"format": 1, "planId": "bad"}
            self.plan.write_text(json.dumps(bad))
            with self.assertRaises(c.Refuse): c.main(self.args)
        self.assertFalse(self.receipt.exists())
        self.assertFalse(fake.calls)

        valid = c.prepare_plan(fake, self.identity, self.threads, self.children, set(),
                               int(__import__('time').time()), 86400, 10, {IDS[0]})
        fake.calls.clear()
        self.plan.write_bytes(c.canonical(valid))
        changed = copy.deepcopy(self.identity)
        changed["profile"]["inode"] += 1
        with patch.object(c, "check_cli"), patch.object(c, "profile_identity", return_value=changed), \
             patch.object(c, "Rpc", return_value=fake):
            with self.assertRaises(c.Refuse): c.main(self.args)
        self.assertFalse(self.receipt.exists())
        self.assertFalse(fake.calls)

    def test_changed_candidate_refuses_before_delete(self):
        fake = FakeRpc([self.t])
        valid = c.prepare_plan(fake, self.identity, self.threads, self.children, set(),
                               int(__import__('time').time()), 86400, 10, {IDS[0]})
        fake.calls.clear()
        self.plan.write_bytes(c.canonical(valid))
        changed = copy.deepcopy(self.threads)
        changed[IDS[0]]["updatedAt"] += 1
        fake = FakeRpc([self.t])
        with patch.object(c, "check_cli"), patch.object(c, "profile_identity", return_value=self.identity), \
             patch.object(c, "Rpc", return_value=fake), \
             patch.object(c, "snapshot", return_value=(changed, self.children)):
            with self.assertRaises(c.Refuse): c.main(self.args)
        self.assertNotIn("thread/delete", [m for m, _ in fake.calls])
        self.assertEqual([json.loads(x)["event"] for x in self.receipt.read_text().splitlines()],
                         ["begin", "stopped"])


FAKE_CLI = '''#!/usr/bin/python3
import sys
if sys.argv[1:] == ["--version"]:
    print("codex-cli 0.166.0")
    sys.exit(0)
sys.exit(4)
'''


class FakeWebSocketServer:
    """Socket-level fixture; policy responses remain deliberately synthetic."""

    def __init__(self, base, path):
        self.base = base
        self.stop = threading.Event()
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        old_cwd = os.getcwd()
        try:
            os.chdir(path.parent)
            self.sock.bind(path.name)
        finally:
            os.chdir(old_cwd)
        self.sock.listen()
        self.sock.settimeout(0.1)
        self.workers = []
        self.thread = threading.Thread(target=self.serve, daemon=True)
        self.thread.start()

    def serve(self):
        while not self.stop.is_set():
            try:
                client, _ = self.sock.accept()
            except socket.timeout:
                continue
            except OSError:
                return
            worker = threading.Thread(target=self.handle, args=(client,), daemon=True)
            self.workers.append(worker)
            worker.start()

    @staticmethod
    def exact(client, count):
        data = b""
        while len(data) < count:
            part = client.recv(count - len(data))
            if not part:
                raise EOFError
            data += part
        return data

    def handle(self, client):
        with client:
            client.settimeout(3)
            try:
                header = b""
                while b"\r\n\r\n" not in header:
                    header += client.recv(4096)
                key = next(line.split(b":", 1)[1].strip() for line in
                           header.split(b"\r\n") if line.lower().startswith(b"sec-websocket-key:"))
                accept = base64.b64encode(hashlib.sha1(
                    key + b"258EAFA5-E914-47DA-95CA-C5AB0DC85B11").digest())
                client.sendall(b"HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\n"
                               b"Connection: Upgrade\r\nSec-WebSocket-Accept: " + accept + b"\r\n\r\n")
                experimental_api = False
                while not self.stop.is_set():
                    head = self.exact(client, 2)
                    if head[0] != 0x81 or not head[1] & 0x80:
                        return
                    size = head[1] & 0x7f
                    if size == 126:
                        size = int.from_bytes(self.exact(client, 2), "big")
                    elif size == 127:
                        size = int.from_bytes(self.exact(client, 8), "big")
                    mask = self.exact(client, 4)
                    payload = self.exact(client, size)
                    msg = json.loads(bytes(x ^ mask[i % 4] for i, x in enumerate(payload)))
                    if msg.get("method") == "initialized":
                        continue
                    mode = (self.base / "mode").read_text() if (self.base / "mode").exists() else "normal"
                    if mode == "exit":
                        return
                    if msg["method"] == "initialize":
                        experimental_api = msg["params"].get("capabilities", {}).get("experimentalApi") is True
                    if msg["method"] == "thread/list" and "parentThreadId" in msg["params"] and not experimental_api:
                        reply = {"id": msg["id"], "error": {"code": -32600,
                                 "message": "parentThreadId requires experimentalApi"}}
                    else:
                        reply = self.reply(msg, mode)
                    data = json.dumps(reply).encode()
                    header = bytes([0x81, len(data)]) if len(data) < 126 else (
                        bytes([0x81, 126]) + len(data).to_bytes(2, "big"))
                    client.sendall(header + data)
            except (EOFError, OSError, ValueError, StopIteration):
                return

    def reply(self, msg, mode):
        method = msg["method"]
        if method == "initialize":
            result = {"codexHome": "/wrong-profile" if mode == "mismatch" else str(self.base)}
        elif method == "thread/list":
            if "parentThreadId" in msg["params"]:
                hidden_path = self.base / "hidden-thread.json"
                data = ([json.loads(hidden_path.read_text())] if hidden_path.exists() and
                        not msg["params"]["archived"] and
                        not (self.base / "deleted").exists() else [])
            else:
                item = json.loads((self.base / "thread.json").read_text())
                data = [] if msg["params"]["archived"] or (self.base / "deleted").exists() else [item]
            result = {"data": data, "nextCursor": None}
        elif method == "thread/loaded/list":
            result = {"data": [], "nextCursor": None}
        elif method == "thread/read":
            result = {"thread": json.loads((self.base / "thread.json").read_text())}
        elif method == "thread/goal/get":
            result = {"goal": None}
        elif method == "thread/delete":
            if mode == "timeout":
                self.stop.wait(2)
                raise EOFError
            if mode == "refuse":
                return {"id": msg["id"], "error": {"code": -32000,
                        "message": "SECRET PROMPT server text"}}
            db = sqlite3.connect(self.base / "state_5.sqlite")
            db.execute("DELETE FROM threads WHERE id=?", (msg["params"]["threadId"],))
            db.commit()
            db.close()
            (self.base / "deleted").write_text(msg["params"]["threadId"])
            result = {}
        else:
            raise ValueError(method)
        return {"id": msg["id"], "result": result}

    def close(self):
        self.stop.set()
        self.sock.close()
        self.thread.join(timeout=2)
        for worker in self.workers:
            worker.join(timeout=3)


class TransportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=TASK_DIR)
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.server = FakeWebSocketServer(self.base, self.base / "control.sock")
        self.addCleanup(self.server.close)
        self.cli = self.base / "fake-codex"
        self.cli.write_text(FAKE_CLI)
        self.cli.chmod(0o700)
        item = thread(updated=int(__import__('time').time()) - 86400)
        item.update({"preview": "SECRET PROMPT", "name": "SECRET TITLE", "cwd": "/private"})
        self.base.joinpath("thread.json").write_text(json.dumps(item))
        db_fixture(self.base, [item])
        self.base.joinpath("retain.json").write_text("[]")
        self.base.joinpath("confirmed-headless.json").write_text(json.dumps([IDS[0]]))
        self.plan = self.base / "plan.json"
        self.receipt = self.base / "receipt.jsonl"
        self.common = ["--profile", str(self.base), "--socket", str(self.base / "control.sock"),
                       "--retain", str(self.base / "retain.json"), "--plan", str(self.plan),
                       "--confirmed-headless", str(self.base / "confirmed-headless.json"),
                       "--codex", str(self.cli)]

    def invoke(self, mode, *extra):
        return subprocess.run([str(Path(c.__file__).parent / "cleanup.sh"), mode,
                               *self.common, *extra], text=True, capture_output=True, timeout=15)

    def test_fake_transport_plan_apply_privacy_and_no_daemon_start(self):
        planned = self.invoke("plan")
        self.assertEqual(planned.returncode, 0, planned.stderr)
        data = self.plan.read_text()
        self.assertEqual(len(json.loads(data)["candidates"]), 1)
        self.assertNotIn("SECRET", data + planned.stdout + planned.stderr)
        applied = self.invoke("apply", "--receipt", str(self.receipt), "--exclusive-maintenance", "--complete-index")
        self.assertEqual(applied.returncode, 0, applied.stderr)
        self.assertEqual((self.base / "deleted").read_text(), IDS[0])
        self.assertEqual([json.loads(x)["event"] for x in self.receipt.read_text().splitlines()],
                         ["begin", "intent", "success", "complete"])
        self.assertNotIn("SECRET", self.receipt.read_text() + applied.stdout + applied.stderr)
        repeated = self.invoke("apply", "--receipt", str(self.receipt), "--exclusive-maintenance", "--complete-index")
        self.assertNotEqual(repeated.returncode, 0)
        self.assertFalse((self.base / "invocations.txt").exists())

    def test_hidden_child_is_recovered_in_plan_and_fresh_apply_without_delete(self):
        hidden = thread(1, source={"subAgent": {"thread_spawn": {
            "parent_thread_id": IDS[0]}}}, parent=IDS[0],
            updated=int(time.time()) - 86400, preview="SECRET PREVIEW")
        (self.base / "hidden-thread.json").write_text(json.dumps(hidden))
        db = sqlite3.connect(self.base / "state_5.sqlite")
        try:
            db.execute("INSERT INTO threads VALUES(?,?,?)", (IDS[1], 0, IDS[0]))
            db.execute("INSERT INTO thread_spawn_edges VALUES(?,?,?)",
                       (IDS[0], IDS[1], "spawned"))
            db.commit()
        finally:
            db.close()
        planned = self.invoke("plan")
        self.assertEqual(planned.returncode, 0, planned.stderr)
        plan = json.loads(self.plan.read_text())
        self.assertEqual(plan["hiddenIndexedRetainedCount"], 1)
        self.assertEqual(plan["indexOnlyRetainedCount"], 0)
        self.assertTrue(plan["inventoryCompleteForApply"])
        self.assertEqual(plan["candidates"], [])
        self.assertNotIn("SECRET", self.plan.read_text() + planned.stdout)
        applied = self.invoke("apply", "--receipt", str(self.receipt),
                              "--exclusive-maintenance", "--complete-index")
        self.assertEqual(applied.returncode, 0, applied.stderr)
        self.assertEqual([json.loads(x)["event"] for x in self.receipt.read_text().splitlines()],
                         ["begin", "complete"])
        self.assertFalse((self.base / "deleted").exists())

    def test_plan_defaults_to_standard_socket_and_empty_retention(self):
        directory = self.base / "app-server-control"
        directory.mkdir()
        local = FakeWebSocketServer(self.base, directory / "app-server-control.sock")
        self.addCleanup(local.close)
        result = subprocess.run([str(Path(c.__file__).parent / "cleanup.sh"),
            "--profile", str(self.base), "--plan", str(self.plan), "--codex", str(self.cli)],
            capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        plan = json.loads(self.plan.read_bytes())
        self.assertEqual(plan["retainedIds"], [])
        self.assertEqual(len(plan["candidates"]), 1)
        self.assertFalse((self.base / "deleted").exists())

    def test_socket_exit_is_a_concrete_refusal(self):
        (self.base / "mode").write_text("exit")
        result = self.invoke("plan")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("socket closed", result.stderr)
        self.assertFalse(self.plan.exists())

    def test_socket_profile_mismatch_refuses(self):
        (self.base / "mode").write_text("mismatch")
        result = self.invoke("plan")
        self.assertIn("daemon profile identity", result.stderr)
        self.assertFalse(self.plan.exists())

    def test_socket_timeout_after_intent_has_no_replay(self):
        self.assertEqual(self.invoke("plan").returncode, 0)
        (self.base / "mode").write_text("timeout")
        result = self.invoke("apply", "--receipt", str(self.receipt),
                             "--exclusive-maintenance", "--complete-index", "--deadline-seconds", "1")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual([json.loads(x)["event"] for x in self.receipt.read_text().splitlines()],
                         ["begin", "intent", "stopped"])
        self.assertFalse((self.base / "deleted").exists())
        self.assertNotEqual(self.invoke("apply", "--receipt", str(self.receipt),
                                         "--exclusive-maintenance", "--complete-index").returncode, 0)


if __name__ == "__main__":
    unittest.main()
