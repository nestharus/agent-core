"""Bounded addressed responsibility and source custody, within the runtime journal.

Delivery, notice receipt, pickup, processing and settlement are separate. A board
ACK is never evidence that a recipient's Codex submission queue was processed.
"""

import json

from .contracts import Refusal, digest, encode, ident, required_text
from .custody import witnesses

SCHEMA = """
CREATE TABLE IF NOT EXISTS outboxes(
 id TEXT PRIMARY KEY,role TEXT NOT NULL,job TEXT,event TEXT,alert TEXT,producer TEXT NOT NULL,
 recipient TEXT NOT NULL,kind TEXT NOT NULL,required TEXT NOT NULL,payload TEXT NOT NULL,
 state TEXT NOT NULL DEFAULT 'pending',board_receipt TEXT,hold TEXT,error TEXT,
 created REAL NOT NULL,processed_at REAL);
CREATE TABLE IF NOT EXISTS operational_errors(
 subject TEXT PRIMARY KEY,role TEXT NOT NULL,kind TEXT NOT NULL,detail TEXT NOT NULL,
 active INTEGER NOT NULL,observed REAL NOT NULL);
CREATE TABLE IF NOT EXISTS source_custody(
 event TEXT PRIMARY KEY,basis TEXT NOT NULL,owner TEXT NOT NULL,binding TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS owner_results(
 job TEXT PRIMARY KEY,owner TEXT NOT NULL,result TEXT NOT NULL,receipt TEXT NOT NULL,created REAL NOT NULL);
"""


class DeliveryJournal:
    def _outbox(self, role, recipient, kind, payload, *, job=None, event=None, alert=None, producer=None, key=None, required="settled"):
        key = key or ident()
        old = self.one("SELECT * FROM outboxes WHERE id=?", (key,))
        if old:
            return key
        if self.db.execute("SELECT COUNT(*) FROM outboxes").fetchone()[0] >= self.config["limits"].get("max_outboxes", self.config["limits"]["max_events"]):
            raise Refusal("outbox capacity held; no responsibility discarded")
        if required not in {"acknowledged", "picked-up", "processed", "settled"}:
            raise Refusal("unknown required delivery frontier")
        if recipient not in self.config.get("delivery", {}).get("recipients", self.config["roles"]):
            raise Refusal("recipient is outside the selected delivery allowlist")
        if kind not in {"work", "result", "question", "alert", "effect-request"}:
            raise Refusal("unknown outgoing message kind")
        self.budget("outboxes", len(encode(payload).encode()))
        self.db.execute("INSERT INTO outboxes(id,role,job,event,alert,producer,recipient,kind,required,payload,created) "
                        "VALUES(?,?,?,?,?,?,?,?,?,?,?)", (key, role, job, event, alert, producer or self.config["actor"],
                                                         recipient, kind, required, encode(payload), self.clock()))
        return key

    def prepare_handoffs(self, job, attempt, task, result):
        handoffs = result.get("handoffs", [])
        if task.get("delivery_required") and "handoffs" not in result:
            raise Refusal("actual task must explicitly conserve handoffs or declare why none is necessary")
        if task.get("delivery_required") and not handoffs and not result.get("no_handoff_reason"):
            raise Refusal("complete without necessary delivery is not an admitted disposition")
        for index, handoff in enumerate(handoffs):
            self._task_handoff(job, attempt, task, result, handoff, index)

    def gate_result_delivery(self, job, attempt, result, internal=None):
        """One fresh Luna-low response classification precedes outgoing model results."""
        rows = self.rows("SELECT * FROM outboxes WHERE job=?", (job["id"],))
        if not rows:
            return internal
        response_id = internal or digest({"outgoing_response": attempt["id"]})
        if not internal and not self.one("SELECT id FROM events WHERE id=?", (response_id,)):
            members = json.loads(job["members"])
            event = {"id": response_id, "role": job["role"], "recipient": self.config["roles"][job["role"]]["owner"],
                     "author": attempt["session"], "kind": "outgoing-response", "body": result,
                     "source_attempt": attempt["id"], "source_job": job["id"], "source_members": members,
                     "delivery_plan": [{"id": r["id"], "recipient": r["recipient"], "kind": r["kind"]} for r in rows],
                     "artifact_witnesses": witnesses(self, attempt['id']),
                     "package": job["package"], "parent": members[0]["event"], "allowed_tasks": ["@delivery"],
                     "notice": None, "board_id": None, "grant": None}
            self.budget("events", len(encode(event)))
            self.db.execute("INSERT INTO events(id,role,payload,hash,received,parent) VALUES(?,?,?,?,?,?)",
                            (response_id, job["role"], encode(event), digest(event), self.clock(), event["parent"]))
        classified = self.one("SELECT classification FROM events WHERE id=?", (response_id,))["classification"]
        self.db.execute("UPDATE outboxes SET event=?,state=CASE WHEN state='pending' AND ? IS NULL "
                        "THEN 'classification-pending' ELSE state END WHERE job=? AND board_receipt IS NULL",
                        (response_id, classified, job["id"]))
        self.db.execute("UPDATE jobs SET response=? WHERE id=?", (response_id, job["id"]))
        return response_id

    def owner_report(self, job, attempt, result):
        existing = self.one("SELECT id FROM outboxes WHERE job=? AND recipient=?", (job["id"], job["role"]))
        if not existing:
            self._outbox(job["role"], job["role"], "result", {"job": job["id"], "attempt": attempt["id"],
                         "result": result, "artifact_witnesses":witnesses(self,attempt['id']), "source_members": json.loads(job["members"])}, job=job["id"], producer=attempt["session"],
                         key=digest({"owner_report": attempt["id"]}))

    def _task_handoff(self, job, attempt, task, result, handoff, index):
        if not isinstance(handoff, dict) or set(handoff) != {"recipient", "kind", "text", "ref", "required"}:
            raise Refusal("handoff needs exact recipient/kind/text/ref/required fields")
        target = handoff["recipient"]
        if handoff["required"] != "settled":
            raise Refusal("necessary task handoffs retain actual recipient processing and settlement")
        if target not in task.get("allowed_handoffs", []):
            raise Refusal("task cannot delegate to this recipient")
        if job["role"] == "Reviews" and target != "Work":
            raise Refusal("Reviews consolidated results/questions return to Work")
        if job["role"] == "QA" and result["category"] == "qualification":
            accepted = self.one("SELECT accepted FROM admissions WHERE package=?", (job["package"],))
            if target != "Branch" or not accepted or not accepted["accepted"]:
                raise Refusal("actual accepted QA package alone can qualify to Branch")
        required_text(handoff["text"], "handoff meaning", self.config["limits"]["max_result_bytes"])
        payload = {"job": job["id"], "attempt": attempt["id"], "package": job["package"],
                   "artifact_witnesses":witnesses(self,attempt['id']),
                   "source_members": json.loads(job["members"]), "source_result": result,
                   "text": handoff["text"], "ref": handoff["ref"], "producer": attempt["session"]}
        self._outbox(job["role"], target, handoff["kind"], payload, job=job["id"], producer=attempt["session"],
                     key=digest({"attempt": attempt["id"], "handoff": index}), required=handoff["required"])

    def owner_question(self, job, attempt, reason, *, effects=False):
        kind = "effect-request" if effects else "question"
        target = job["role"] if effects else "Work"
        payload = {"job": job["id"], "attempt": attempt["id"], "reservation": job["token"],
                   "reason": reason, "result": json.loads(attempt["result"]) if attempt["result"] else None,
                   "causal_detail": json.loads(attempt["detail"]), "exit": attempt["exit"],
                   "package": job["package"], "source_members": json.loads(job["members"])}
        return self._outbox(job["role"], target, kind, payload, job=job["id"],
                            producer=attempt["session"], key=digest({"attempt": attempt["id"], "owner": kind}))

    def deliveries_settled(self, job):
        rows = self.rows("SELECT * FROM outboxes WHERE job=?", (job,))
        return all(self.delivery_satisfied(row) for row in rows)

    @staticmethod
    def delivery_satisfied(row):
        order = {"pending": 0, "posted": 1, "ambiguous": 1, "acknowledged": 2,
                 "picked-up": 3, "processed": 4, "settled": 5}
        return not row["hold"] and order.get(row["state"], 0) >= order[row["required"]]

    def delivery_observed(self, delivery, receipt):
        with self.tx():
            row = self.one("SELECT * FROM outboxes WHERE id=?", (delivery,))
            if not row or receipt["id"] != delivery:
                raise Refusal("unbound delivery receipt")
            self.db.execute("UPDATE outboxes SET state=?,board_receipt=?,error=NULL,processed_at=? WHERE id=?",
                            (receipt["state"], encode(receipt), receipt.get("processed_at"), delivery))
            if row["alert"] and receipt.get("processed_at") is not None:
                self.db.execute("UPDATE alerts SET processed_at=MAX(COALESCE(processed_at,?),?) WHERE id=?",
                                (receipt["processed_at"], receipt["processed_at"], row["alert"]))
            self._owner_settlement(row, receipt)
            if row["event"] and not self.one("SELECT id FROM outboxes WHERE event=? AND (state!='settled' OR hold IS NOT NULL OR processed_at IS NULL)", (row["event"],)):
                self.db.execute("UPDATE queue SET state='done' WHERE event=? AND phase='delivery'", (row["event"],))

    def _owner_settlement(self, outbox, receipt):
        if outbox["job"] and outbox["kind"] == "work" and receipt["state"] == "settled":
            task = self.config["tasks"][self.job(outbox["job"])["task"]]
            if task.get("execution") == "owner":
                self.owner_result(outbox, receipt)
        if outbox["kind"] != "effect-request" or receipt["state"] != "settled":
            return
        job = self.job(outbox["job"])
        evidence = receipt.get("settlement", {}).get("effects")
        if not evidence or not evidence.get("evidence") or evidence.get("unknown_effects") != []:
            raise Refusal("effect owner settlement must preserve actual effects/outbox reconciliation")
        if receipt["recipient"] != self.config["roles"][job["role"]]["owner"]:
            raise Refusal("effect settlement is not from actual owning role")
        self.db.execute("UPDATE jobs SET effects='reconciled',effect_receipt=? WHERE id=?",
                        (encode({"actor": receipt["recipient"], **evidence}), job["id"]))

    def delegate_owner_job(self, job):
        with self.tx():
            row = self.job(job)
            self.require_active_sources(job=job)
            task = self.config["tasks"][row["task"]]
            if task.get("execution") != "owner" or row["state"] != "reserved":
                raise Refusal("only an unstarted exact owner-procedure reservation can be delegated")
            payload = {"job": job, "package": row["package"], "members": json.loads(row["members"]),
                       "events": [self.event(m["event"]) for m in json.loads(row["members"])],
                       "procedure": task["templates"], "selected_binding": task["binding"],
                       "authority": task["authority"], "purpose": task["purpose"],
                       "text": "Perform the actual selected review under its actual original owner/context/method; return full collected reports and explicit coverage/failure frontiers. No generic replacement review."}
            self._outbox(row["role"], row["role"], "work", payload, job=job, key=digest({"owner_work": job}))
            self.db.execute("UPDATE jobs SET state='awaiting-owner' WHERE id=?", (job,))

    def owner_result(self, outbox, receipt):
        from .contracts import task_result, response_tasks
        job = self.job(outbox["job"])
        task = self.config["tasks"][job["task"]]
        if receipt["recipient"] != self.config["roles"][job["role"]]["owner"]:
            raise Refusal("actual selected review owner must return its collected result")
        returned = receipt.get("settlement", {})
        result = task_result(returned.get("result"))
        artifact_context=receipt.get('artifact_context')
        artifact_sources=witnesses(self,artifact_context) if artifact_context else []
        if result['artifacts'] and not artifact_sources:
            raise Refusal('owner report artifacts require exact captured source custody')
        originals = returned.get("actual_originals")
        if (not isinstance(originals, list) or not returned.get("method_pin") or not returned.get("coverage_frontier") or
                (not originals and (result["semantic"] == "DONE" or not returned.get("no_start_evidence")))):
            raise Refusal("actual original collection, selected method/pin and genuine coverage frontier required")
        if any(not isinstance(o, dict) or o.get("collector") != receipt["recipient"] or type(o.get("actual_end")) is not int or not o.get("reference") for o in originals):
            raise Refusal("reported external originals must retain their real collector, numeric end and source")
        effects = returned.get("effects", {})
        if not effects.get("evidence") or effects.get("unknown_effects") != []:
            raise Refusal("the actual review owner must reconcile this report task's effects; other historical holds remain scoped")
        if self.one("SELECT job FROM owner_results WHERE job=?", (job["id"],)):
            return
        history = {"original": receipt.get("original_settlement", returned), "corrections": receipt.get("owner_corrections", [])}
        self.db.execute("INSERT INTO owner_results VALUES(?,?,?,?,?)", (job["id"], receipt["recipient"], encode(result), encode({"effective": returned, **history}), self.clock()))
        choices = response_tasks(task, result, self.config)
        if not choices:
            raise Refusal("actual selected review return needs its report-integrator route")
        destination = self.config["tasks"][choices[0]]["role"]
        members = json.loads(job["members"])
        response = {"id": digest({"owner_return": job["id"]}), "role": destination,
                    "recipient": self.enrollment(destination)["owner"], "author": receipt["recipient"],
                    "kind": "response", "source_job": job["id"], "source_owner": receipt["recipient"],
                    "source_originals": originals, "method_pin": returned["method_pin"], "coverage_frontier": returned["coverage_frontier"],
                    "source_no_start_evidence": returned.get("no_start_evidence"),
                    "owner_return_history": history,
                    "artifact_witnesses":artifact_sources,
                    "source_members": members, "source_attempt": None, "parent": members[0]["event"],
                    "package": job["package"], "allowed_tasks": choices, "body": result,
                    "notice": None, "board_id": None, "grant": None}
        self.budget("events", len(encode(response)))
        self.db.execute("INSERT INTO events(id,role,payload,hash,received,parent) VALUES(?,?,?,?,?,?)",
                        (response["id"], destination, encode(response), digest(response), self.clock(), response["parent"]))
        self.db.execute("UPDATE jobs SET state='closed',effects='reconciled',effect_receipt=?,response=?,closed_at=? WHERE id=?",
                        (encode(returned), response["id"], self.clock(), job["id"]))
        self.db.execute("UPDATE queue SET state='done' WHERE job=?", (job["id"],))

    def record_operational_error(self, subject, detail, role="Work", kind="runtime-held"):
        with self.tx():
            self.db.execute("INSERT INTO operational_errors VALUES(?,?,?,?,1,?) ON CONFLICT(subject) "
                            "DO UPDATE SET detail=excluded.detail,active=1,observed=excluded.observed",
                            (subject, role, kind, encode(detail), self.clock()))

    def clear_operational_error(self, subject):
        with self.tx():
            self.db.execute("UPDATE operational_errors SET active=0 WHERE subject=?", (subject,))

    def dependents(self, event):
        # Jobs retain all frozen members, including after queue membership retires.
        return self.rows("WITH RECURSIVE edges(source,consumer) AS ("
                         "SELECT parent,id FROM events WHERE parent IS NOT NULL UNION "
                         "SELECT json_extract(m.value,'$.event'),j.response FROM jobs j,json_each(j.members) m WHERE j.response IS NOT NULL),"
                         "reachable(id) AS (SELECT ? UNION SELECT consumer FROM edges JOIN reachable ON source=reachable.id) "
                         "SELECT e.* FROM events e JOIN reachable ON e.id=reachable.id", (event,))

    def dependency_hold(self, event):
        dependent = self.dependents(event)
        if any(row["hold"] or row["processed_at"] is None for row in dependent):
            return True
        ids = {row["id"] for row in dependent}
        jobs = self.rows("SELECT * FROM jobs")
        linked = {j["id"] for j in jobs if any(m["event"] in ids for m in json.loads(j["members"]))}
        outgoing = self.rows("SELECT * FROM outboxes")
        return any((r["job"] in linked or r["event"] in ids) and not self.delivery_satisfied(r) for r in outgoing)

    def source_for_retirement(self, event):
        """No universal board-retention assumption: keep only unproven needed input locally.

        Internal responses use already-retained actual result custody, with the
        full original header preserved. Other inputs retain their existing body
        in place under the actual role custodian; no blanket duplicate is made.
        """
        payload = json.loads(event["payload"])
        basis, binding, replacement = "local", {"event": event["id"], "hash": event["hash"]}, event["payload"]
        if payload.get("kind") == "response" and payload.get("source_attempt"):
            source = self.one("SELECT result FROM results WHERE attempt=?", (payload["source_attempt"],))
            header = {k: v for k, v in payload.items() if k != "body"}
            if source and digest({**header, "body": json.loads(source["result"])}) == event["hash"]:
                basis, binding, replacement = "result", {"attempt": payload["source_attempt"], "header": header, "hash": event["hash"]}, "{}"
        owner = self.config["roles"][event["role"]]["owner"]
        self.db.execute("INSERT OR REPLACE INTO source_custody VALUES(?,?,?,?)", (event["id"], basis, owner, encode(binding)))
        return replacement

    def recover_source(self, event):
        row = self.one("SELECT * FROM source_custody WHERE event=?", (event,))
        if not row:
            return self.event(event)
        binding = json.loads(row["binding"])
        if row["basis"] == "local":
            value = self.event(event)
        else:
            source = self.one("SELECT result FROM results WHERE attempt=?", (binding["attempt"],))
            value = {**binding["header"], "body": json.loads(source["result"])}
        if digest(value) != binding["hash"]:
            raise Refusal("required source custody no longer recovers the original meaning/attribution")
        return value
