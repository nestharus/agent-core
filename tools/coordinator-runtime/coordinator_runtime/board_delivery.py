"""Additive true-automation-actor delivery, with actual recipient-owned settlement.

Uses schema-4 content/notification tables, never CODEX_SESSION_ID substitution.
The explicit owning-role grant enrolls a separate labelled service actor. Normal
notice transport is used only for the exact newly owned post, never an inbox
drain or takeover of an existing TUI/app-server/native collector.
"""

import json
import os
import time
import shlex
from pathlib import Path

from .contracts import Refusal, digest, encode, canonical_uuid, required_text

SCHEMA = """
CREATE TABLE IF NOT EXISTS coordinator_delivery_grants_v1(
 grant_id TEXT PRIMARY KEY,recipients TEXT NOT NULL,kinds TEXT NOT NULL,authority TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS coordinator_deliveries_v1(
 id TEXT PRIMARY KEY,grant_id TEXT NOT NULL,owner TEXT NOT NULL,actor TEXT NOT NULL,
 producer TEXT NOT NULL,recipient TEXT NOT NULL,kind TEXT NOT NULL,required TEXT NOT NULL,
 payload TEXT NOT NULL,post INTEGER UNIQUE NOT NULL,notice INTEGER NOT NULL,
 state TEXT NOT NULL,created TEXT NOT NULL,pickup TEXT,processing TEXT,settlement TEXT,
 processed_at REAL,transport_started INTEGER NOT NULL DEFAULT 0);
"""


class BoardDelivery:
    def grant_delivery(self, conn, grant, authority, runtime):
        recipients = self.config.get("delivery", {}).get("recipients", {})
        if not recipients:
            raise Refusal("explicit bounded delivery recipients required")
        allowed = {name: item["session"] for name, item in recipients.items() if item.get("session")}
        actor = self.config["actor"]
        if actor in set(allowed.values()) | {r["owner"] for r in self.config["roles"].values()}:
            raise Refusal("automation actor must be its own identity, never an existing recipient/owner")
        if "managed" not in self._entry()["allowed_routes"].split(","):
            raise Refusal("board cannot host the separate managed automation actor")
        prior = conn.execute("SELECT role,work FROM sessions WHERE session=?", (actor,)).fetchone()
        work = "coordinator-runtime:" + str(runtime.path)
        if prior and (prior["role"] != "coordinator-runtime" or prior["work"] != work):
            raise Refusal("automation UUID already belongs to another real actor; do not overwrite")
        stamp = self.store.utc_now()
        conn.execute("INSERT OR IGNORE INTO sessions(session,campaign,role,profile,status,work,registered_at,last_seen_at,route) "
                     "VALUES(?,'coordinator-runtime','coordinator-runtime',NULL,'active',?,?,?,'managed')", (actor, work, stamp, stamp))
        conn.execute("INSERT INTO coordinator_delivery_grants_v1 VALUES(?,?,?,?)", (grant["id"], encode(allowed),
                     encode(["work", "result", "question", "alert", "effect-request"]), authority))

    def _delivery_grant(self, conn, runtime, outbox):
        grant = self._grant(conn, runtime)
        row = conn.execute("SELECT * FROM coordinator_delivery_grants_v1 WHERE grant_id=?", (grant["id"],)).fetchone()
        if not row:
            raise Refusal("incoming/receipt grant does not grant outgoing delegation; actual owner issues full scoped grant")
        target = self.config["delivery"]["recipients"].get(outbox["recipient"], {})
        if not target.get("session") or target.get("active") is False:
            raise Refusal("actual recipient identity is inactive/unbound")
        if json.loads(row["recipients"]).get(outbox["recipient"]) != target["session"] or outbox["kind"] not in json.loads(row["kinds"]):
            raise Refusal("delivery exceeds current real-actor grant")
        member = conn.execute("SELECT status,role,profile FROM sessions WHERE session=?", (target["session"],)).fetchone()
        if not member or member["status"] != "active" or member["role"] != target["board_role"]:
            raise Refusal("delivery recipient is not the actual selected active role identity")
        if target.get("profile") is not None and member["profile"] != target["profile"]:
            raise Refusal("recipient board profile identity differs; never substitute a task profile")
        return grant, target

    def post_delivery(self, runtime, outbox):
        with self.opened() as conn:
            with self.store.write(conn):
                existing = conn.execute("SELECT * FROM coordinator_deliveries_v1 WHERE id=?", (outbox["id"],)).fetchone()
                if existing:
                    self._delivery_grant(conn, runtime, outbox)
                    if existing["payload"] != outbox["payload"] or existing["producer"] != outbox["producer"]:
                        raise Refusal("delivery identity already binds different immutable source")
                    return self._delivery_record(conn, dict(existing))
                grant, target = self._delivery_grant(conn, runtime, outbox)
                self._insert_delivery(conn, grant, target, outbox)
            self.store.active_listener.signal_post(conn, conn.execute("SELECT post FROM coordinator_deliveries_v1 WHERE id=?", (outbox["id"],)).fetchone()[0])
            row = conn.execute("SELECT * FROM coordinator_deliveries_v1 WHERE id=?", (outbox["id"],)).fetchone()
            return self._delivery_record(conn, dict(row))

    def _insert_delivery(self, conn, grant, target, outbox):
        title = "Coordinator " + outbox["kind"] + " " + outbox["id"][:12]
        payload = json.loads(outbox["payload"])
        summary = payload.get("text") or payload.get("reason") or payload.get("kind") or "Collected result and owned responsibility"
        summary = str(summary)[:2500]
        operator = self.config.get("operator_config", "ACTUAL_PRIVATE_CONFIG_PATH")
        cli = self.config.get("operator_cli", str(Path(__file__).resolve().parents[1]/"coordinator"))
        prefix = shlex.join([cli, "--config", operator])
        text = (f"{summary}\nDelivery={outbox['id']} required={outbox['required']}. "
                f"Real automation actor={self.config['actor']}; authorizing role owner={grant['owner']}; "
                f"original producer={outbox['producer']}. Receipt is not pickup, processing or settlement. "
                "Root code workers retain commit AND push.\n"
                f"Read complete payload: {prefix} delivery-show {self.role} {outbox['id']}\n"
                f"Record actual pickup/processed/settled: {prefix} delivery-stage {self.role} "
                f"{outbox['id']} --stage STAGE --receipt ACTUAL_OWNER_JSON\n"
                "The full source/attribution remains in the board's bounded delivery record; preserve actual original collectors, "
                "selected Source/reviewer contexts, resource admission and unknown effects. Do not redispatch already owned work.")
        self.store.bounded(text, "delivery text", 8000, multiline=True)
        stamp = self.store.utc_now()
        post_kind = "question" if outbox["kind"] in {"question", "effect-request"} else "handoff"
        seq = conn.execute("INSERT INTO posts(author,recipient,topic,kind,text,ref,reply_to,created_at) VALUES(?,?,?,?,?,?,NULL,?)",
                           (self.config["actor"], target["session"], "coordinator-runtime", post_kind, text, "delivery:"+outbox["id"], stamp)).lastrowid
        conn.execute("INSERT INTO threads VALUES(?,?,?,?,?)", (seq, title, "coordinator-runtime", self.config["actor"], stamp))
        conn.execute("INSERT INTO thread_posts VALUES(?,?)", (seq, seq))
        conn.executemany("INSERT INTO subscriptions VALUES(?,?,?)", [(seq, actor, stamp) for actor in {self.config["actor"], target["session"]}])
        self.store.notify(conn, {target["session"]}, seq, seq, "open", title, self.config["actor"], push=False)
        notice = conn.execute("SELECT notification_id FROM notification_outbox WHERE post_seq=? AND recipient=?", (seq, target["session"])).fetchone()[0]
        limit = self.config["limits"].get("max_board_deliveries", self.config["limits"]["max_events"])
        if conn.execute("SELECT COUNT(*) FROM coordinator_deliveries_v1").fetchone()[0] >= limit:
            raise Refusal("bounded board delivery custody full; do not discard held work")
        conn.execute("INSERT INTO coordinator_deliveries_v1(id,grant_id,owner,actor,producer,recipient,kind,required,payload,post,notice,state,created) "
                     "VALUES(?,?,?,?,?,?,?,?,?,?,?,'posted',?)", (outbox["id"], grant["id"], grant["owner"], self.config["actor"],
                     outbox["producer"], target["session"], outbox["kind"], outbox["required"], outbox["payload"], seq, notice, stamp))

    def transport_delivery(self, runtime, outbox):
        with self.opened(settlement=True, owner_required=False) as conn:
            row = conn.execute("SELECT * FROM coordinator_deliveries_v1 WHERE id=?", (outbox["id"],)).fetchone()
            notice = conn.execute("SELECT * FROM notification_outbox WHERE notification_id=?", (row["notice"],)).fetchone()
            if notice["route"] != "queue" or row["transport_started"]:
                return self._delivery_record(conn, dict(row))
            self._delivery_grant(conn, runtime, outbox)
            with self.store.write(conn):
                fresh = conn.execute("SELECT transport_started FROM coordinator_deliveries_v1 WHERE id=?", (outbox["id"],)).fetchone()
                if fresh["transport_started"]:
                    return self._delivery_record(conn, dict(row))
                conn.execute("UPDATE coordinator_deliveries_v1 SET transport_started=1 WHERE id=?", (outbox["id"],))
            # Only this exact newly owned post/recipient. No foreign queue drain,
            # resume, steer, existing claim recovery or replay of ambiguous send.
            self.store.dispatch_notices(conn, actor=self.config["actor"], limit=1, board_id=self.selected["board_id"],
                                        board_home=str(self.home), post_seq=row["post"], recipient=row["recipient"])
            return self._delivery_record(conn, dict(row))

    def reconcile_delivery(self, runtime, outbox):
        """Collect a committed exact send after lost reply, even when revoked."""
        with self.opened(settlement=True, owner_required=False) as conn:
            row = conn.execute("SELECT * FROM coordinator_deliveries_v1 WHERE id=?", (outbox["id"],)).fetchone()
            if not row:
                return None
            grant = conn.execute("SELECT * FROM coordinator_grants_v1 WHERE id=?", (row["grant_id"],)).fetchone()
            stat = runtime.path.stat()
            if (not grant or grant["runtime"] != str(runtime.path) or
                    (grant["runtime_dev"], grant["runtime_ino"]) != (stat.st_dev, stat.st_ino) or
                    row["actor"] != self.config["actor"] or row["owner"] != self.selected["owner"] or
                    row["payload"] != outbox["payload"] or row["producer"] != outbox["producer"]):
                raise Refusal("existing delivery does not belong to this exact runtime/source")
            return self._delivery_record(conn, dict(row))

    def delivery_status(self, delivery):
        with self.opened(settlement=True, owner_required=False) as conn:
            row = conn.execute("SELECT * FROM coordinator_deliveries_v1 WHERE id=?", (delivery,)).fetchone()
            if not row:
                raise Refusal("delivery not posted; no send inferred")
            return self._delivery_record(conn, dict(row))

    def _delivery_record(self, conn, row):
        notice = conn.execute("SELECT delivery_state,route,queue_message_id FROM notification_outbox WHERE notification_id=?", (row["notice"],)).fetchone()
        state = row["state"]
        if state == "posted" and notice["delivery_state"] == "acknowledged":
            state = "acknowledged"
        if state == "posted" and notice["delivery_state"] in {"ambiguous", "sending", "failed"}:
            state = "ambiguous"
        return {"id": row["id"], "state": state, "post": row["post"], "notice": row["notice"], "recipient": row["recipient"],
                "actor": row["actor"], "producer": row["producer"], "processed_at": row["processed_at"],
                "pickup": json.loads(row["pickup"]) if row["pickup"] else None,
                "processing": json.loads(row["processing"]) if row["processing"] else None,
                "settlement": json.loads(row["settlement"]) if row["settlement"] else None,
                "transport": dict(notice)}

    def show_delivery(self, delivery):
        actor = canonical_uuid(os.environ.get("CODEX_SESSION_ID"))
        with self.opened(settlement=True, owner_required=False) as conn:
            row = conn.execute("SELECT * FROM coordinator_deliveries_v1 WHERE id=?", (delivery,)).fetchone()
            if not row or actor not in {row["recipient"], row["owner"]}:
                raise Refusal("complete private delivery is visible only to its actual recipient/owning role")
            return {"delivery": self._delivery_record(conn, dict(row)), "payload": json.loads(row["payload"])}

    def delivery_stage(self, delivery, stage, receipt):
        actor = canonical_uuid(os.environ.get("CODEX_SESSION_ID"))
        if stage not in {"picked-up", "processed", "settled"} or not receipt.get("evidence"):
            raise Refusal("actual bounded pickup/processing/settlement evidence required")
        with self.opened(settlement=True, owner_required=False) as conn:
            with self.store.write(conn):
                row = conn.execute("SELECT * FROM coordinator_deliveries_v1 WHERE id=?", (delivery,)).fetchone()
                if not row or row["recipient"] != actor:
                    raise Refusal("only this exact actual recipient owns pickup/processing/settlement")
                if stage != "picked-up" and not row["pickup"]:
                    raise Refusal("actual pickup precedes processing/settlement")
                if stage == "settled" and not row["processing"]:
                    raise Refusal("actual processing precedes settlement")
                notice = conn.execute("SELECT * FROM notification_outbox WHERE notification_id=?", (row["notice"],)).fetchone()
                if stage == "picked-up" and notice["delivery_state"] == "sending":
                    raise Refusal("original transport sender still owns an unsettled claim")
                if stage in {"processed", "settled"} and notice["route"] == "queue":
                    transport = receipt.get("transport", {})
                    if (not transport.get("evidence") or not notice["queue_message_id"] or
                            transport.get("queue_message_id") != notice["queue_message_id"] or
                            transport.get("state") != "processed"):
                        raise Refusal("board ACK alone does not prove exact submission-queue processing")
                if stage == "settled" and row["kind"] == "question" and not receipt.get("resolution"):
                    raise Refusal("actual owner answer/disposition is required for consequential question settlement")
                column = {"picked-up": "pickup", "processed": "processing", "settled": "settlement"}[stage]
                encoded = encode({"actor": actor, **receipt})
                if row[column]:
                    if row[column] != encoded:
                        raise Refusal("a completed recipient stage is immutable; send a new addressed reply for new findings/decisions")
                    return self._delivery_record(conn, dict(row))
                conn.execute(f"UPDATE coordinator_deliveries_v1 SET {column}=?,state=?,processed_at=CASE WHEN ?='processed' THEN ? ELSE processed_at END WHERE id=?",
                             (encoded, stage, stage, time.time(), delivery))
                if stage == "picked-up":
                    stamp = self.store.utc_now()
                    conn.execute("UPDATE notification_outbox SET delivery_state='acknowledged',acknowledged_at=COALESCE(acknowledged_at,?),state_changed_at=? WHERE notification_id=?",
                                 (stamp, stamp, row["notice"]))
            row = conn.execute("SELECT * FROM coordinator_deliveries_v1 WHERE id=?", (delivery,)).fetchone()
            return self._delivery_record(conn, dict(row))
