"""Bounded/fair driver witnesses on owned journals, fake models and helpers only."""
import asyncio
from collections import Counter
import tempfile
import unittest
from unittest.mock import patch

from support import config_at, enrolled, event
from test_board_dispatch import FakeModels
import test_control_recovery as control
from coordinator_runtime.contracts import encode
from coordinator_runtime.dispatcher import Dispatcher, DELIVERY_PAGE
from coordinator_runtime.store import Store


def retained(store, count, prefix="old", state="posted"):
    """Bulk synthetic retained history, without any actual board/native effect."""
    keys = [f"{prefix}-{n}" for n in range(count)]
    with store.tx():
        store.db.executemany(
            "INSERT INTO outboxes(id,role,producer,recipient,kind,required,payload,state,board_receipt,hold,created) "
            "VALUES(?,'Work',?,'Work','question','settled','{}',?,?,'independent source/effect hold',?)",
            [(key, store.config["actor"], state, encode({"state": state, "control_receipt": {"pending": False}}),
              store.clock()) for key in keys])
    return keys


class DeliveryBoard:
    """Minimal board boundary; all deliveries remain unprocessed and held."""
    def __init__(self, testcase):
        self.testcase = testcase
        self.incoming, self.visits, self.acks = [], [], []

    def verify_authority(self, store):
        pass

    def scan(self, store):
        incoming, self.incoming = self.incoming, []
        return incoming

    def receipt(self, store, key):
        self.testcase.assertTrue(store.one("SELECT classification FROM events WHERE id=?", (key,))["classification"])
        self.testcase.assertTrue(store.one("SELECT id FROM queue WHERE event=?", (key,)))
        self.acks.append(key)
        return {"evidence": ["synthetic delegated receipt after durable classification/queue"]}

    def reconcile_delivery(self, store, outbox):
        return None

    def post_delivery(self, store, outbox):
        return self.delivery_status(outbox["id"])

    def delivery_status(self, key):
        return {"state": "posted", "id": key}

    def transport_delivery(self, store, outbox):
        self.visits.append(outbox["id"])
        return self.delivery_status(outbox["id"])


class DriverProgress(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="bounded-driver-fixture-")
        self.addCleanup(self.temp.cleanup)
        self.config = config_at(self.temp.name)
        self.config["limits"]["max_outboxes"] = 40000
        self.store = enrolled(self.config)
        self.addCleanup(self.store.close)
        self.board = DeliveryBoard(self)
        self.models = FakeModels()

    def runtime(self):
        return Dispatcher(self.store, models=self.models, boards={"Work": self.board})

    async def test_large_pending_history_allows_fresh_intake_durable_ACK_jobs_and_reconciliation(self):
        old = retained(self.store, 25712)
        runtime = self.runtime()
        incoming = {**event(self.config, "fresh-intake"), "kind": "board", "notice": 1, "post": 1}
        self.board.incoming.append(incoming)
        with self.store.tx():
            fresh = self.store._outbox("Work", "Work", "question", {"text": "fresh duty"})
        pages = []
        rows = self.store.rows

        def observe(sql, values=()):
            result = rows(sql, values)
            if "AS delivery_seq" in sql:
                pages.append(len(result))
            return result

        with patch.object(self.store, "rows", side_effect=observe):
            for _ in range(4):
                await runtime.tick()
        await asyncio.gather(*runtime.active)
        self.assertEqual(self.board.acks, [incoming["id"]])
        self.assertEqual(self.store.one("SELECT ack FROM events WHERE id=?", (incoming["id"],))["ack"], "done")
        self.assertTrue(any(call["kind"] == "task" for call in self.models.calls))
        self.assertEqual(self.store.one("SELECT state FROM jobs")["state"], "closed")
        self.assertIn(fresh, self.board.visits)
        self.assertLess(len(set(old) & set(self.board.visits)), len(old))
        self.assertLessEqual(max(pages), DELIVERY_PAGE)
        self.assertEqual(len(pages), 8)
        self.assertEqual(self.store.one("SELECT COUNT(*) AS n FROM outboxes WHERE hold IS NOT NULL AND processed_at IS NULL")["n"], len(old))

    async def test_both_lanes_and_repeated_old_rechecks_progress_under_continuing_appends(self):
        old = retained(self.store, 97)
        runtime = self.runtime()
        for cycle in range(22):
            fresh = retained(self.store, 1, prefix=f"new-{cycle}")[0]
            before = len(self.board.visits)
            await runtime.pump_deliveries_async()
            this_pass = self.board.visits[before:]
            self.assertIn(fresh, this_pass)
            self.assertLessEqual(len(this_pass), 2 * DELIVERY_PAGE)
            self.assertEqual(len(this_pass), len(set(this_pass)))
        counts = Counter(self.board.visits)
        self.assertTrue(all(counts[key] >= 2 for key in old))
        self.assertEqual(self.store.one("SELECT COUNT(*) AS n FROM outboxes WHERE processed_at IS NOT NULL")["n"], 0)

    async def test_ineligible_history_is_bounded_and_later_release_is_revisited(self):
        old = retained(self.store, 129, state="classification-pending")
        # An existing row becoming eligible does not append a new row. The
        # rotating lane must rediscover it, including settled receipt duties.
        self.store.db.execute("UPDATE outboxes SET state='settled',board_receipt=? WHERE id=?",
                              (encode({"control_receipt": {"pending": True}}), old[32]))
        runtime = self.runtime()
        await runtime.pump_deliveries_async()
        self.assertEqual(self.board.visits, [])
        self.assertEqual(runtime.delivery_revisit, DELIVERY_PAGE)
        self.store.db.execute("UPDATE outboxes SET state='pending' WHERE id=?", (old[0],))
        for _ in range(10):
            await runtime.pump_deliveries_async()
        self.assertIn(old[0], self.board.visits)
        self.assertIn(old[32], self.board.visits)
        self.assertNotIn(old[1], self.board.visits)

    async def test_fresh_classification_release_does_not_wait_for_retained_sweep(self):
        old = retained(self.store, 25712)
        runtime = self.runtime()
        fresh = retained(self.store, 1, prefix="fresh-classifying", state="classification-pending")[0]
        await runtime.pump_deliveries_async()
        self.assertNotIn(fresh, self.board.visits)
        # The exact state transition used by commit_classification must wake a
        # row already passed by fresh insertion traversal; original holds remain.
        self.store.db.execute("UPDATE outboxes SET state='pending' WHERE id=?", (fresh,))
        await runtime.pump_deliveries_async()
        self.assertIn(fresh, self.board.visits)
        self.assertLess(len(set(old) & set(self.board.visits)), len(old))
        self.assertEqual(self.store.one("SELECT COUNT(*) AS n FROM delivery_wakeups")["n"], len(old) + 1)

    async def test_existing_version_one_journal_adds_hints_without_rewriting_old_duties(self):
        old = retained(self.store, 33)
        original = self.store.rows("SELECT * FROM outboxes ORDER BY id")
        # An owned fixture of the pre-correction schema: only the new scheduling
        # hints are absent. Opening it with unchanged config adds empty hints.
        self.store.db.executescript("DROP TRIGGER delivery_insert_wakeup; DROP TRIGGER delivery_classified_wakeup; DROP TABLE delivery_wakeups;")
        self.store.close()
        self.store = Store(self.config)
        self.addCleanup(self.store.close)
        self.assertEqual(self.store.rows("SELECT * FROM outboxes ORDER BY id"), original)
        self.assertEqual(self.store.one("SELECT COUNT(*) AS n FROM delivery_wakeups")["n"], 0)
        self.assertEqual(self.store.db.execute("PRAGMA user_version").fetchone()[0], 1)
        runtime = self.runtime()
        await runtime.pump_deliveries_async()
        self.assertTrue(set(old) & set(self.board.visits))
        fresh = retained(self.store, 1, prefix="after-old-schema-open")[0]
        await runtime.pump_deliveries_async()
        self.assertIn(fresh, self.board.visits)

    async def test_event_loop_can_observe_deadline_and_stop_between_delivery_operations(self):
        retained(self.store, 25712)
        runtime = self.runtime()
        opportunities = []

        async def deadline_then_stop():
            await asyncio.sleep(0)
            opportunities.append(len(self.board.visits))
            runtime.stopping.set()

        watcher = asyncio.create_task(deadline_then_stop())
        await runtime.pump_deliveries_async()
        await watcher
        self.assertTrue(opportunities)
        self.assertLessEqual(len(self.board.visits), 2)
        self.assertEqual(self.store.one("SELECT COUNT(*) AS n FROM outboxes")["n"], 25712)


class DriverControlProgress(unittest.IsolatedAsyncioTestCase):
    # Real board/control adapters on freshly created fixture boards. The only
    # native boundary below is a fake helper that checks durable intent custody.
    setUp = control.AutomaticControls.setUp
    policy = control.AutomaticControls.policy
    delegate = control.AutomaticControls.delegate
    delivery = control.AutomaticControls.delivery
    helper = control.AutomaticControls.helper

    async def test_old_and_fresh_controls_get_turns_unknowns_do_not_retry_and_alerts_recur(self):
        self.delegate(self.policy("Work"))
        old = [self.delivery(recipient="Work") for _ in range(48)]
        calls = []
        self.store.record_operational_error("persistent-violation", {"error": "unchanged"}, "Work")
        self.store.clock = lambda: 1000
        # Existing fixture runtime predates history; make it a startup history
        # to exercise the retained/fresh boundary as well as live appends.
        runtime = Dispatcher(self.store, models=object(), boards=self.boards)
        outcomes = self.helper(calls, status="ambiguous", qid=False)
        with patch("coordinator_runtime.owner_control.load_helper", return_value=outcomes):
            await runtime.alerts(lambda _: None)
            first = self.store.one("SELECT id FROM outboxes WHERE alert IS NOT NULL")["id"]
            self.assertTrue(self.boards["Work"].delivery_status(first)["control_receipt"]["pending"])
            self.store.clock = lambda: 1002
            await runtime.alerts(lambda _: None)
            for _ in range(12):
                await runtime.pump_deliveries_async()
        with self.substrate.database(str(self.path)) as conn:
            controls = [dict(row) for row in conn.execute("SELECT * FROM coordinator_controls_v1")]
        deliveries = [row["delivery"] for row in controls]
        self.assertEqual(len(deliveries), len(set(deliveries)))
        attempted = [row for row in controls if row["state"] == "unknown"]
        self.assertEqual(len(calls), len(attempted))
        self.assertTrue(set(old) & set(deliveries))
        alerts = self.store.rows("SELECT id FROM outboxes WHERE alert IS NOT NULL")
        self.assertEqual(len(alerts), 2)
        self.assertTrue(all(row["id"] in deliveries for row in alerts))
        self.assertTrue(all(row["state"] in {"prepared", "unknown"} for row in controls))
        self.assertTrue(all(row["id"] in {r["delivery"] for r in attempted} for row in alerts))
        self.assertTrue(all(row["processed_at"] is None for row in self.store.rows("SELECT processed_at FROM outboxes")))
        self.assertEqual(self.store.one("SELECT COUNT(*) AS n FROM outboxes")["n"], len(old) + 2)

    async def test_revisits_preserve_accepted_unknown_and_inflight_intent_custody(self):
        self.delegate(self.policy("Work"))
        calls = []
        for status in ("queued", "ambiguous", "inflight"):
            self.delivery(recipient="Work")
            if status == "inflight":
                def interrupted(*args, **kwargs):
                    raise KeyboardInterrupt("owned fake helper interrupted after durable send claim")
                helper = type("Helper", (), {"queue_notice": staticmethod(interrupted)})()
            else:
                helper = self.helper(calls, status=status, qid=status == "queued")
            with patch("coordinator_runtime.owner_control.load_helper", return_value=helper):
                if status == "inflight":
                    with self.assertRaises(KeyboardInterrupt):
                        self.runtime.pump_deliveries()
                else:
                    self.runtime.pump_deliveries()
        with self.substrate.database(str(self.path)) as conn:
            before = [dict(row) for row in conn.execute("SELECT * FROM coordinator_controls_v1 ORDER BY id")]
        self.assertEqual({row["state"] for row in before}, {"accepted", "unknown", "inflight"})
        with patch("coordinator_runtime.owner_control.load_helper", side_effect=AssertionError("no retry/fallback")):
            for _ in range(8):
                await self.runtime.pump_deliveries_async()
        with self.substrate.database(str(self.path)) as conn:
            after = [dict(row) for row in conn.execute("SELECT * FROM coordinator_controls_v1 ORDER BY id")]
        self.assertEqual(after, before)
        self.assertEqual(len(calls), 2)
        self.assertTrue(all(row["processed_at"] is None for row in self.store.rows("SELECT processed_at FROM outboxes")))


if __name__ == "__main__":
    unittest.main()
