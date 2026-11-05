"""Additive true-automation-actor delivery, with actual recipient-owned settlement.

Uses schema-4 content/notification tables, never CODEX_SESSION_ID substitution.
The explicit owning-role grant enrolls a separate labelled service actor. Normal
notice transport is used only for the exact newly owned post, never an inbox
drain or takeover of an existing TUI/app-server/native collector.
"""

import json
from contextlib import closing
import os
import time
import shlex
import sqlite3
from pathlib import Path

from .contracts import Refusal, digest, encode, canonical_uuid, required_text

OWNER_RETURN_SCHEMA = """
CREATE TABLE IF NOT EXISTS coordinator_owner_return_checks_v1(
 delivery TEXT NOT NULL,version TEXT NOT NULL,rejection TEXT,validated INTEGER NOT NULL DEFAULT 0,
 runtime TEXT NOT NULL,observed TEXT NOT NULL,PRIMARY KEY(delivery,version));
CREATE TABLE IF NOT EXISTS coordinator_owner_corrections_v1(
 id TEXT PRIMARY KEY,delivery TEXT NOT NULL,revision INTEGER NOT NULL,actor TEXT NOT NULL,
 supersedes TEXT NOT NULL,reason TEXT NOT NULL,receipt TEXT NOT NULL,created TEXT NOT NULL,
 UNIQUE(delivery,revision));
"""

SCHEMA = """
CREATE TABLE IF NOT EXISTS coordinator_delivery_grants_v1(
 grant_id TEXT PRIMARY KEY,recipients TEXT NOT NULL,kinds TEXT NOT NULL,authority TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS coordinator_deliveries_v1(
 id TEXT PRIMARY KEY,grant_id TEXT NOT NULL,owner TEXT NOT NULL,actor TEXT NOT NULL,
 producer TEXT NOT NULL,recipient TEXT NOT NULL,kind TEXT NOT NULL,required TEXT NOT NULL,
 payload TEXT NOT NULL,post INTEGER UNIQUE NOT NULL,notice INTEGER NOT NULL,
 state TEXT NOT NULL,created TEXT NOT NULL,pickup TEXT,processing TEXT,settlement TEXT,
 processed_at REAL,transport_started INTEGER NOT NULL DEFAULT 0);
""" + OWNER_RETURN_SCHEMA


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
        configured_target=target
        original_recipients=json.loads(row['recipients'])
        if (not configured_target.get('session') or outbox['recipient'] not in original_recipients
                or original_recipients[outbox['recipient']]!=configured_target['session']):
            raise Refusal('branch association cannot expand the original selected delivery routes')
        payload=json.loads(outbox['payload'])
        if runtime.processing and outbox['recipient']=='Root' and payload.get('branch_root_routing'):
            from .branches import association
            branch=association(runtime,payload['branch_binding'])
            if (branch['root']!=payload['branch_root_routing']['root'] or branch['scope']!=payload.get('package')
                    or runtime.processing.current()[0]['issuer']!=grant['issued_by']):
                raise Refusal('current genuine Work branch Root authority/source scope changed; original send held')
            target={**target,'session':branch['root'],'profile':None}
        if not target.get("session") or target.get("active") is False:
            raise Refusal("actual recipient identity is inactive/unbound")
        if json.loads(row["recipients"]).get(outbox["recipient"]) != configured_target["session"] or outbox["kind"] not in json.loads(row["kinds"]):
            raise Refusal("delivery exceeds current real-actor grant")
        member = conn.execute("SELECT status,role,profile FROM sessions WHERE session=?", (target["session"],)).fetchone()
        if not member or member["status"] != "active" or member["role"] != target["board_role"]:
            raise Refusal("delivery recipient is not the actual selected active role identity")
        if target.get("profile") is not None and member["profile"] != target["profile"]:
            raise Refusal("recipient board profile identity differs; never substitute a task profile")
        return grant, target

    def post_delivery(self, runtime, outbox):
        if runtime.processing:
            original=runtime.one('SELECT * FROM outboxes WHERE id=?',(outbox['id'],))
            if not original or original['payload']!=outbox['payload'] or original['producer']!=outbox['producer']:
                raise Refusal('original live outbox required; retired metadata never permits pointer-post replay')
            intent=runtime.one('SELECT delivery FROM shared_custody_intents WHERE delivery=?',(outbox['id'],))
            if intent:
                raise Refusal('shared retirement intent owns this source; reconcile conservation, never repost')
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
        self._delivery_capacity(conn, outbox)
        title = "Coordinator " + outbox["kind"] + " " + outbox["id"][:12]
        payload = json.loads(outbox["payload"])
        summary = payload.get("text") or payload.get("reason") or payload.get("kind") or "Collected result and owned responsibility"
        summary = str(summary)[:2500]
        operator = self.config.get("operator_config", "ACTUAL_PRIVATE_CONFIG_PATH")
        cli = self.config.get("operator_cli", str(Path(__file__).resolve().parents[1]/"coordinator"))
        prefix = shlex.join([cli, "--config", operator])
        text = (f"{summary}\nDelivery={outbox['id']} required={outbox['required']}. "
                f"Real automation actor={self.config['actor']}; grantor={grant['issued_by']}; role owner={grant['owner']}; "
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
        conn.execute("INSERT INTO coordinator_deliveries_v1(id,grant_id,owner,actor,producer,recipient,kind,required,payload,post,notice,state,created) "
                     "VALUES(?,?,?,?,?,?,?,?,?,?,?,'posted',?)", (outbox["id"], grant["id"], grant["owner"], self.config["actor"],
                     outbox["producer"], target["session"], outbox["kind"], outbox["required"], outbox["payload"], seq, notice, stamp))

    def _delivery_capacity(self, conn, outbox):
        # Ordinary grants retain their original shared-count contract. Explicit
        # retained authority supplies a separate residency/allocation check.
        limit = self.config["limits"].get("max_board_deliveries", self.config["limits"]["max_events"])
        if conn.execute("SELECT COUNT(*) FROM coordinator_deliveries_v1").fetchone()[0] >= limit:
            raise Refusal("bounded board delivery custody full; do not discard held work")

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
        corrections = []
        if conn.execute("SELECT 1 FROM sqlite_master WHERE name='coordinator_owner_corrections_v1'").fetchone():
            corrections = [{**dict(r), "receipt": json.loads(r["receipt"])} for r in conn.execute(
                "SELECT * FROM coordinator_owner_corrections_v1 WHERE delivery=? ORDER BY revision", (row["id"],))]
        original = json.loads(row["settlement"]) if row["settlement"] else None
        settlement = corrections[-1]["receipt"] if corrections else original
        control=self.control_receipt_status(conn,row)
        processed=row['processed_at']
        if control['pending']:processed=None
        elif control['required'] and processed is not None:processed=max(processed,control['processed_at'])
        return {"id": row["id"], "state": state, "post": row["post"], "notice": row["notice"], "recipient": row["recipient"],
                "actor": row["actor"], "producer": row["producer"], "processed_at": processed,
                "substantive_processed_at":row['processed_at'],"control_receipt":control,
                "pickup": json.loads(row["pickup"]) if row["pickup"] else None,
                "processing": json.loads(row["processing"]) if row["processing"] else None,
                "settlement": settlement, "settlement_version": digest(settlement) if settlement else None,
                "original_settlement": original, "owner_corrections": corrections,
                "transport": dict(notice)}

    def collect_owner_return(self, runtime, outbox):
        """Serialize local result collection and owner corrections on the board.

        A crash between the two databases is reconciled from retained immutable
        source, never by rerunning the review. Rejection is durable on the board.
        """
        failure = None
        with self.opened(settlement=True, owner_required=False) as conn:
            with self.store.write(conn):
                for sql in OWNER_RETURN_SCHEMA.split(";"):
                    if sql.strip():
                        conn.execute(sql)
                row = conn.execute("SELECT * FROM coordinator_deliveries_v1 WHERE id=?", (outbox["id"],)).fetchone()
                if not row or row["actor"] != self.config["actor"] or row["payload"] != outbox["payload"] or row["producer"] != outbox["producer"]:
                    raise Refusal("owner return does not bind this exact delivery/source")
                grant = conn.execute("SELECT * FROM coordinator_grants_v1 WHERE id=?", (row["grant_id"],)).fetchone()
                stat = runtime.path.stat()
                if (not grant or grant["runtime"] != str(runtime.path) or grant["owner"] != self.selected["owner"] or
                        (grant["runtime_dev"], grant["runtime_ino"]) != (stat.st_dev, stat.st_ino)):
                    raise Refusal("owner return collection retains the exact original runtime grant")
                receipt = self._delivery_record(conn, dict(row))
                try:
                    from .custody import inventory
                    from .contracts import task_result
                    job=runtime.job(outbox['job'])
                    task=self.config['tasks'][job['task']]
                    if task.get('execution')!='owner' or receipt['recipient']!=self.selected['owner']:
                        raise Refusal('artifact custody must retain the actual selected owner procedure')
                    context='owner:'+job['id']+':'+receipt['settlement_version']
                    inventory(runtime,context,task_result(receipt['settlement'].get('result')),task,role_owned=True)
                    receipt['artifact_context']=context
                    runtime.delivery_observed(outbox["id"], receipt)
                except (Refusal,OSError) as exc:
                    failure = str(exc)[:1000]
                conn.execute("INSERT INTO coordinator_owner_return_checks_v1 VALUES(?,?,?,?,?,?) "
                             "ON CONFLICT(delivery,version) DO UPDATE SET rejection=excluded.rejection,"
                             "validated=excluded.validated,observed=excluded.observed",
                             (outbox["id"], receipt["settlement_version"], failure, int(failure is None), str(runtime.path), self.store.utc_now()))
        if failure:
            raise Refusal(failure)
        return receipt

    def correct_owner_return(self, delivery, correction):
        actor = canonical_uuid(os.environ.get("CODEX_SESSION_ID"))
        if not isinstance(correction, dict) or set(correction) != {"supersedes", "reason", "settlement"}:
            raise Refusal("owner correction requires exact supersedes/reason/settlement")
        required_text(correction["reason"], "actual owner correction reason", 4000)
        if len(encode(correction).encode()) > self.config["limits"]["max_result_bytes"]:
            raise Refusal("owner correction exceeds bounded result capture")
        with self.opened(settlement=True, owner_required=False) as conn:
            with self.store.write(conn):
                row = conn.execute("SELECT * FROM coordinator_deliveries_v1 WHERE id=?", (delivery,)).fetchone()
                if not row or row["recipient"] != actor or row["kind"] != "work" or row["state"] != "settled":
                    raise Refusal("only the actual recipient can correct its settled owner-procedure return")
                payload = json.loads(row["payload"])
                if self.role != "Reviews" or payload.get("selected_binding") != {"model": "gpt-xhigh", "provider": "opaque", "effort": "opaque"}:
                    raise Refusal("this correction path is only for the selected actual Reviews owner procedure")
                current = self._delivery_record(conn, dict(row))
                key = digest({"delivery": delivery, "actor": actor, "correction": correction})
                if current["owner_corrections"] and current["owner_corrections"][-1]["id"] == key:
                    return current  # Same correction delivery, not another review or revision.
                if correction["supersedes"] != current["settlement_version"]:
                    raise Refusal("stale owner correction; read the exact current rejected version")
                rejected = conn.execute("SELECT * FROM coordinator_owner_return_checks_v1 WHERE delivery=? AND version=?",
                                        (delivery, current["settlement_version"])).fetchone()
                if not rejected or not rejected["rejection"] or rejected["validated"]:
                    raise Refusal("runtime must record the exact rejected owner return before correction")
                grant = conn.execute("SELECT * FROM coordinator_grants_v1 WHERE id=?", (row["grant_id"],)).fetchone()
                if not grant or grant["owner"] != actor or grant["runtime"] != rejected["runtime"]:
                    raise Refusal("correction is not bound to the original owner/runtime grant")
                path = Path(grant["runtime"])
                stat = path.stat()
                if (stat.st_dev, stat.st_ino) != (grant["runtime_dev"], grant["runtime_ino"]):
                    raise Refusal("original runtime identity changed; retain correction/source for recovery")
                with closing(sqlite3.connect(path.as_uri()+"?mode=ro", uri=True)) as journal:
                    configuration = journal.execute("SELECT value FROM meta WHERE key='configuration'").fetchone()
                    pending = journal.execute("SELECT role,state FROM jobs WHERE id=?", (payload["job"],)).fetchone()
                    accepted = journal.execute("SELECT job FROM owner_results WHERE job=?", (payload["job"],)).fetchone()
                if configuration != (digest(self.config),):
                    raise Refusal("correction configuration differs from the original runtime binding")
                if accepted or pending != ("Reviews", "awaiting-owner"):
                    raise Refusal("owner result already collected or reservation changed; send new findings as a new addressed message")
                replacement = correction["settlement"]
                if not isinstance(replacement, dict) or not replacement.get("evidence"):
                    raise Refusal("corrected return needs actual evidence")
                for field in ("actor", "actual_originals", "method_pin", "no_start_evidence"):
                    before = current["settlement"].get(field)
                    if before is not None and replacement.get(field) != before:
                        raise Refusal("correction cannot replace actual owner/original collectors or selected method")
                if replacement.get("actor") != actor:
                    raise Refusal("corrected return retains its genuine owner actor")
                limit = self.config["limits"].get("max_owner_corrections", 4)
                if len(current["owner_corrections"]) >= limit:
                    raise Refusal("bounded owner correction budget exhausted; retain source and explicit recovery ownership")
                used = conn.execute("SELECT COALESCE(SUM(LENGTH(c.receipt)+LENGTH(c.reason)),0) FROM coordinator_owner_corrections_v1 c "
                                    "JOIN coordinator_deliveries_v1 d ON d.id=c.delivery WHERE d.actor=?", (self.config["actor"],)).fetchone()[0]
                if used + len(encode(correction).encode()) >= self.config["limits"]["max_bytes"]:
                    raise Refusal("owned correction custody full; no source discarded")
                conn.execute("INSERT INTO coordinator_owner_corrections_v1 VALUES(?,?,?,?,?,?,?,?)",
                             (key, delivery, len(current["owner_corrections"])+1, actor, correction["supersedes"],
                              correction["reason"], encode(replacement), self.store.utc_now()))
                return self._delivery_record(conn, dict(row))

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
                if stage in {'processed','settled'}:
                    self.control_processing_proof(conn,row,actor,receipt,stage=stage)
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
