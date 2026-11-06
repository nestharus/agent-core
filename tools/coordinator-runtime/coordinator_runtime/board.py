"""Additive schema-4 board delegation bridge.

Role: adapter. Translates: message-board catalog/store visibility and exact notice
receipt; coordinator runtime durable responsibility. No owner cursor, membership,
queue transport, TUI socket or native collector is borrowed. Grants are explicit
same-account cooperation records, NOT authentication or product-effect authority.
"""
from . import observations


from contextlib import contextmanager
from datetime import datetime, timezone
import builtins
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import sys

from .contracts import LUNA, Refusal, canonical_uuid, digest, encode, ident, regular_path
from .board_delivery import BoardDelivery, SCHEMA as DELIVERY_SCHEMA
from .completion import Completion
from .routine import BOARD_SCHEMA as COMPLETION_SCHEMA
from .owner_control import OwnerControl
from .software import Software, BOARD_SCHEMA as SOFTWARE_SCHEMA
from .shared_custody import SharedCustody, SCHEMA as SHARED_CUSTODY_SCHEMA

EXTENSION = """
CREATE TABLE IF NOT EXISTS coordinator_grants_v1(
 id TEXT PRIMARY KEY,board_id TEXT NOT NULL,role TEXT NOT NULL,owner TEXT NOT NULL,
 profile TEXT NOT NULL,actor TEXT NOT NULL,runtime TEXT NOT NULL,runtime_dev INTEGER NOT NULL,
 runtime_ino INTEGER NOT NULL,cutover INTEGER NOT NULL,issued_by TEXT NOT NULL,
 authority TEXT NOT NULL,created TEXT NOT NULL,revoked TEXT);
CREATE TABLE IF NOT EXISTS coordinator_receipts_v1(
 event TEXT PRIMARY KEY,grant_id TEXT NOT NULL,notice INTEGER,post INTEGER NOT NULL,
 owner TEXT NOT NULL,controller_actor TEXT NOT NULL,classifier_actor TEXT NOT NULL,
 classifier_attempt TEXT NOT NULL,classification TEXT NOT NULL,responsibility TEXT NOT NULL,
 kind TEXT NOT NULL,created TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS coordinator_receipt_targets_v1(
 event TEXT PRIMARY KEY,actual_recipient TEXT NOT NULL,authorizing_owner TEXT NOT NULL);
"""


def module_at(directory, name, imports=None):
    path = regular_path(str(Path(directory) / f"{name}.py"))
    spec = importlib.util.spec_from_file_location(f"coordinator_substrate_{name}_{digest(str(path))[:16]}", path)
    module = importlib.util.module_from_spec(spec)
    prior_module=sys.modules.get(spec.name)
    sys.modules[spec.name]=module  # Dataclass/annotation resolution needs its actual module binding.
    original_path = list(sys.path)
    sys.path.insert(0, str(path.parent))
    try:
        if imports:
            def selected_import(name,globals=None,locals=None,fromlist=(),level=0):
                if level==0 and name in imports:return imports[name]
                return builtins.__import__(name,globals,locals,fromlist,level)
            module.__builtins__={**vars(builtins),'__import__':selected_import}
        source=path.read_bytes()
        exec(compile(source,str(path),'exec'),module.__dict__)
        module.__coordinator_source_sha256__=hashlib.sha256(source).hexdigest()
    except BaseException:
        if prior_module is None:sys.modules.pop(spec.name,None)
        else:sys.modules[spec.name]=prior_module
        raise
    finally:
        sys.path[:] = original_path
    return module


def connect(path):
    path = regular_path(str(path))
    conn = sqlite3.connect(path.as_uri()+"?mode=rw", uri=True, isolation_level=None, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA synchronous=FULL")
    return conn


def utc():
    return datetime.now(timezone.utc).isoformat()


class Board(BoardDelivery, Completion, OwnerControl, Software, SharedCustody):
    def __init__(self, config, role):
        self.config, self.role = config, role
        self.selected = config["roles"][role]
        self.library = config["board_library"]
        self.catalog = module_at(self.library, "catalog")
        self.store = module_at(self.library, "board_store")
        self.home = Path(config["board_home"])
        self.path = Path(self._entry()["db_path"])
        stat = regular_path(str(self.path)).stat()
        if stat.st_nlink != 1:
            raise Refusal("board aliases/hard links refused")
        self.identity = (stat.st_dev, stat.st_ino)

    def _entry(self):
        path = regular_path(str(self.home / "catalog.sqlite3"))
        with sqlite3.connect(path.as_uri()+"?mode=ro", uri=True) as conn:
            conn.row_factory = sqlite3.Row
            entry = self.catalog.board(conn, self.selected["board_id"])
        return entry

    @contextmanager
    def opened(self, *, settlement=False, owner_required=True):
        entry = self._entry()
        with self.catalog.lifecycle_lock(entry, self.home, exclusive=False):
            entry = self._entry()
            self._policy(entry, settlement)
            conn = connect(self.path)
            original_path = list(sys.path)
            sys.path.insert(0, str(Path(self.library)))
            try:
                self._schema(conn, owner_required=owner_required)
                yield conn
            finally:
                sys.path[:] = original_path
                conn.close()

    def _policy(self, entry, settlement):
        if entry["state"] not in ({"active", "retired"} if settlement else {"active"}):
            raise Refusal("board lifecycle does not permit this operation")
        stat = regular_path(entry["db_path"]).stat()
        if str(self.path) != entry["db_path"] or self.identity != (stat.st_dev, stat.st_ino):
            raise Refusal("board file/catalog identity changed")

    def _schema(self, conn, *, owner_required=True):
        if self.store.SCHEMA_VERSION != 4 or conn.execute("PRAGMA user_version").fetchone()[0] != 4:
            raise Refusal("bridge supports inspected schema 4 only; no automatic migration")
        board = conn.execute("SELECT board_id FROM board_meta").fetchall()
        if [r[0] for r in board] != [self.selected["board_id"]]:
            raise Refusal("embedded board UUID differs")
        if not owner_required:
            return
        member = conn.execute("SELECT * FROM sessions WHERE session=?", (self.selected["owner"],)).fetchone()
        if not member or member["status"] != "active":
            raise Refusal("actual role owner must remain an active board member")
        if member["profile"] != self.selected["profile"] or member["role"] != self.selected["board_role"]:
            raise Refusal("actual role/profile membership differs from configured identity")
        entry = self._entry()
        if member["route"] not in entry["allowed_routes"].split(","):
            raise Refusal("role member route forbidden by catalog policy")
        if entry["membership_policy"] == "invited":
            self._invited()

    def _invited(self):
        path = regular_path(str(self.home / "catalog.sqlite3"))
        with sqlite3.connect(path.as_uri()+"?mode=ro", uri=True) as conn:
            invited = conn.execute("SELECT 1 FROM invitations WHERE board_id=? AND session=?",
                                   (self.selected["board_id"], self.selected["owner"])).fetchone()
        if not invited:
            raise Refusal("actual role owner has no required catalog invitation")

    def grant(self, runtime, authority, *, delivery=False, completion=False):
        owner = self.store.acting_session(self.selected["owner"])
        return self._issue_grant(runtime, authority, owner, delivery=delivery, completion=completion)

    def _issue_grant(self, runtime, authority, issuer, *, delivery=False, completion=False, software=False):
        owner = self.selected['owner']
        if not authority.strip():
            raise Refusal("actual user/role delegation authority reference required")
        stat = regular_path(str(runtime.path)).stat()
        with self.opened() as conn:
            conn.executescript(EXTENSION + DELIVERY_SCHEMA + COMPLETION_SCHEMA + SOFTWARE_SCHEMA + SHARED_CUSTODY_SCHEMA)
            with self.store.write(conn):
                route = conn.execute("SELECT route FROM sessions WHERE session=?", (owner,)).fetchone()[0]
                if route != "managed":
                    raise Refusal("actual owner must select prospective managed delivery before delegation; old notice routes remain owned")
                cutover = conn.execute("SELECT COALESCE(MAX(seq),0) FROM posts").fetchone()[0]
                grant = {"id": ident(), "owner": owner, "actor": self.config["actor"], "cutover": cutover,
                         "issued_by": issuer, "authority": authority}
                conn.execute("INSERT INTO coordinator_grants_v1 VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,NULL)",
                             (grant["id"], self.selected["board_id"], self.role, owner,
                              self.selected["profile"], grant["actor"], str(runtime.path),
                              stat.st_dev, stat.st_ino, cutover, issuer, authority, utc()))
                if software:
                    conn.execute('INSERT INTO coordinator_software_grants_v1 VALUES(?,?,?)',
                                 (grant['id'], encode(self.software_policies()), digest(self.config)))
                if delivery:
                    self.grant_delivery(conn, grant, authority, runtime)
                if completion:
                    self.grant_completion(conn, grant, authority)
        return grant

    def revoke(self, grant_id):
        owner = self.store.acting_session(self.selected["owner"])
        with self.opened(settlement=True) as conn:
            with self.store.write(conn):
                changed = conn.execute("UPDATE coordinator_grants_v1 SET revoked=? WHERE id=? AND owner=?",
                                       (utc(), grant_id, owner)).rowcount
        if changed != 1:
            raise Refusal("grant does not belong to actual owner")

    def extend_delivery(self, runtime, authority):
        self.store.acting_session(self.selected["owner"])
        with self.opened() as conn:
            conn.executescript(DELIVERY_SCHEMA)
            with self.store.write(conn):
                grant = self._grant(conn, runtime)
                if conn.execute("SELECT 1 FROM coordinator_delivery_grants_v1 WHERE grant_id=?", (grant["id"],)).fetchone():
                    raise Refusal("outgoing grant already exists; do not silently expand recipient scope")
                self.grant_delivery(conn, grant, authority, runtime)
        return {"grant_id": grant["id"], "delivery_delegation": "explicit-current-owner"}

    def _grant(self, conn, runtime):
        enrollment = runtime.enrollment(self.role)
        row = conn.execute("SELECT * FROM coordinator_grants_v1 WHERE id=?", (enrollment["grant_id"],)).fetchone()
        stat = runtime.path.stat()
        if not row or row["revoked"] is not None:
            raise Refusal("delegation is absent or revoked")
        expected = (self.selected["board_id"], self.role, self.selected["owner"], self.config["actor"],
                    str(runtime.path), stat.st_dev, stat.st_ino)
        actual = tuple(row[k] for k in ("board_id", "role", "owner", "actor", "runtime", "runtime_dev", "runtime_ino"))
        if actual != expected:
            raise Refusal("grant runtime/role/actor identity differs")
        return dict(row)

    @observations.observe('board-authority')
    def verify_authority(self, runtime):
        with self.opened() as conn:
            return self._grant(conn, runtime)

    def retire_alert(self, runtime, occurrence, receipt):
        from . import capacity
        actor = self.store.acting_session(self.selected['owner'])
        # Fence cooperating Board changes through current grant/recipient/
        # control/transport revalidation and the runtime transaction. This is
        # not multi-file atomicity or a noncooperating-writer guarantee.
        with self.opened() as conn:
            with self.store.write(conn):
                self._grant(conn, runtime)
                _, outbox, _ = capacity.retirement_basis(runtime, occurrence)
                if outbox['role'] != self.role:
                    raise Refusal('alert belongs to another source owner')
                self._delivery_grant(conn, runtime, outbox)
                row = conn.execute('SELECT * FROM coordinator_deliveries_v1 WHERE id=?', (outbox['id'],)).fetchone()
                if not row or row['payload'] != outbox['payload'] or row['producer'] != outbox['producer']:
                    raise Refusal('exact current Board delivery source is unavailable')
                return capacity.retire(runtime, occurrence, actor, receipt, self._delivery_record(conn, dict(row)))

    def owner_catchup(self, runtime, after, through=None):
        """Genuine paused-route owner recovers an explicit source interval.

        No grant/membership/cursor mutation, manufactured notice or task replay.
        """
        self.store.acting_session(self.selected['owner'])
        with self.opened() as conn:
            upper = conn.execute('SELECT COALESCE(MAX(seq),0) FROM posts').fetchone()[0] if through is None else through
            if after < 0 or upper < after:
                raise Refusal('bounded monotonic source interval required')
            owner=self.selected['owner']
            ids=conn.execute('SELECT p.seq FROM posts p LEFT JOIN thread_posts tp ON tp.post_seq=p.seq '
                'LEFT JOIN threads t ON t.thread_id=tp.thread_id LEFT JOIN posts root ON root.seq=t.thread_id '
                'WHERE p.seq>? AND p.seq<=? AND (p.recipient=? OR t.opener=? OR root.recipient=?) ORDER BY p.seq LIMIT 101',
                (after,upper,owner,owner,owner)).fetchall()
            selected=[]
            for item in ids[:100]:
                visible=self.store.query_posts(conn,session=owner,after=item['seq']-1,topic=None,kind=None,limit=1,include_thread_members=True)
                if not visible or visible[0]['seq']!=item['seq']:raise Refusal('catchup source visibility changed')
                selected.append(visible[0])
            recovered = []
            for post in selected:
                key = digest({'board':self.selected['board_id'],'post':post['seq'],'owner':self.selected['owner']})
                existing = runtime.one('SELECT id,processed_at,hold FROM events WHERE id=?', (key,))
                if existing and existing['processed_at'] is not None and not existing['hold']:
                    continue
                notice = conn.execute('SELECT notification_id FROM notification_outbox WHERE post_seq=? AND recipient=?',
                                      (post['seq'],self.selected['owner'])).fetchone()
                recovered.append({'post':post,'notice':notice[0] if notice else None,'existing_responsibility':existing,
                                  'disposition':'actual owner consumes/routes source; no replay or notice ACK inferred'})
            cursor = selected[-1]['seq'] if selected else upper
            complete = len(ids) <= 100
            return {'owner':self.selected['owner'],'after':after,'through':upper,'next_after':cursor,
                    'complete_interval':bool(complete),'sources':recovered,'membership_or_cursor_changed':False}

    @observations.observe('board-scan')
    def scan(self, runtime, limit=100):
        """No owner ack_seq is read or advanced. Our prospective cursor is atomic with intake."""
        with self.opened() as conn:
            grant = self._grant(conn, runtime)
            after = self.scan_after(runtime, grant)
            through=-1
            if conn.execute("SELECT 1 FROM sqlite_master WHERE name='coordinator_scan_frontiers_v1'").fetchone():
                info=runtime.path.stat()
                saved=conn.execute('SELECT through FROM coordinator_scan_frontiers_v1 WHERE runtime=? AND device=? AND inode=? AND actor=?',
                                   (str(runtime.path),info.st_dev,info.st_ino,self.config['actor'])).fetchone()
                through=saved['through'] if saved else -1
            rows = conn.execute("SELECT p.seq,n.notification_id FROM posts p LEFT JOIN notification_outbox n "
                "ON n.post_seq=p.seq AND n.recipient=? WHERE p.seq>? AND "
                "NOT (p.seq<=? AND p.author=? AND p.topic='coordinator-runtime' AND COALESCE(p.ref,'') LIKE 'delivery:%') AND "
                "NOT EXISTS (SELECT 1 FROM coordinator_deliveries_v1 d WHERE d.post=p.seq AND d.actor=? "
                "AND (? OR NOT (d.kind='work' AND d.recipient=? AND d.owner!=?))) AND "
                "(n.notification_id IS NOT NULL OR (p.recipient=? AND NOT EXISTS "
                "(SELECT 1 FROM thread_posts t WHERE t.post_seq=p.seq))) ORDER BY p.seq LIMIT ?",
                (grant["owner"], max(after, grant["cutover"]), through,self.config['actor'],self.config["actor"], bool(self.config.get('software_delegation')),
                 grant["owner"], grant["owner"], grant["owner"], limit)).fetchall()
            replies = conn.execute("SELECT p.seq,n.notification_id,d.id AS parent_delivery FROM posts p "
                "JOIN thread_posts t ON t.post_seq=p.seq JOIN coordinator_deliveries_v1 d ON d.post=t.thread_id "
                "LEFT JOIN notification_outbox n ON n.post_seq=p.seq AND n.recipient=? "
                "WHERE p.seq>? AND p.recipient=? AND d.owner=? AND p.author!=? ORDER BY p.seq LIMIT ?",
                (self.config["actor"], max(after, grant["cutover"]), self.config["actor"], grant["owner"], self.config["actor"], limit)).fetchall()
            selected = sorted([*rows, *replies], key=lambda r: r["seq"])[:limit]
            return [self._event(conn, row, grant, runtime) for row in selected]

    def scan_after(self, runtime, grant):
        return runtime.one('SELECT seq FROM cursors WHERE role=?', (self.role,))['seq']

    def verify_input_source(self, runtime, event):
        """Reobserve only this original visible addressed post; never parse its text as authority."""
        with self.opened() as conn:
            grant = self._grant(conn, runtime)
            recipient = event.get('receipt_recipient', grant['owner'])
            if event.get('notice') is not None:
                addressed = conn.execute('SELECT 1 FROM notification_outbox WHERE notification_id=? AND post_seq=? AND recipient=?',
                                         (event['notice'], event['post'], recipient)).fetchone()
            else:
                addressed = conn.execute('SELECT 1 FROM posts WHERE seq=? AND recipient=?',
                                         (event['post'], recipient)).fetchone()
            if not addressed:
                raise Refusal('mapping requires the original addressed post/notification, not visible arbitrary text')
            row = {'seq':event['post'], 'notification_id':event.get('notice')}
            if event.get('parent_delivery'):
                row['parent_delivery'] = event['parent_delivery']
            observed = self._event(conn, row, grant, runtime)
            if observed != event:
                raise Refusal('original visible addressed Board source/grant/body changed; mapping held')
        return True

    def _event(self, conn, row, grant, runtime=None):
        service_reply = "parent_delivery" in row.keys()
        if service_reply and not conn.execute("SELECT 1 FROM coordinator_delivery_grants_v1 WHERE grant_id=?", (grant["id"],)).fetchone():
            raise Refusal("service reply body requires the explicit delivery/delegation grant")
        recipient = self.config["actor"] if service_reply else grant["owner"]
        posts = self.store.query_posts(conn, session=recipient, after=row["seq"]-1,
                                       topic=None, kind=None, limit=1, include_thread_members=True)
        if not posts or posts[0]["seq"] != row["seq"]:
            raise Refusal("delegated owner cannot see this addressed event")
        body = posts[0]
        # A package identity comes from an existing role admission packet, never a model guess.
        package = body.get("ref") if self.role in {"QA", "Branch"} else None
        owned_work = conn.execute("SELECT * FROM coordinator_deliveries_v1 WHERE post=? AND recipient=? AND kind='work'",
                                  (row["seq"], grant["owner"])).fetchone()
        if owned_work:
            future = self.prospective_handoff_event(runtime, owned_work) if runtime is not None else None
            if future is not None:
                return future
            material = json.loads(owned_work["payload"])
            body = {**body, "delivery": material, "original_producer": owned_work["producer"]}
            package = material.get("package") or material.get("ref")
        event = {"id": digest({"board": grant["board_id"], "post": row["seq"], "owner": grant["owner"]}),
                "board_id": grant["board_id"], "post": row["seq"], "notice": row["notification_id"],
                "role": self.role, "recipient": grant["owner"], "author": body["author"],
                "kind": "board", "body": body, "package": package, "grant": grant["id"],
                "allowed_tasks": self.selected["routes"]}
        if service_reply:
            event.update({"receipt_recipient": recipient, "parent_delivery": row["parent_delivery"]})
        if runtime is not None and runtime.processing and self.role=='Reviews':
            from .branches import board_review
            factual=board_review(runtime,body)
            if factual:
                event['board_source']=body
                event['body']={'review':factual['packet']}
                if factual['branch']:
                    event['branch_binding']=factual['branch']['id']
                    event['package']=factual['branch']['scope']
        return event

    def receipt(self, runtime, event_id):
        """A board-local audit commit is the idempotency/readback boundary, including lost replies."""
        event = runtime.event(event_id)
        with self.opened(settlement=True) as conn:
            with self.store.write(conn):
                grant = self._grant(conn, runtime)
                existing = conn.execute("SELECT * FROM coordinator_receipts_v1 WHERE event=?", (event_id,)).fetchone()
                if existing:
                    return self._receipt_record(conn, dict(existing))
                proof = self._proof(runtime, event, grant)
                self._ack(conn, event, grant)
                kind = "delegated-notice-receipt" if event["notice"] is not None else "plain-post-receipt"
                if event.get("parent_delivery"):
                    kind = "automation-reply-receipt"
                conn.execute("INSERT INTO coordinator_receipts_v1 VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                    (event_id, grant["id"], event["notice"], event["post"], grant["owner"], grant["actor"],
                     proof["session"], proof["id"], proof["classification"], proof["responsibility"], kind, utc()))
                conn.execute("INSERT INTO coordinator_receipt_targets_v1 VALUES(?,?,?)",
                             (event_id, event.get("receipt_recipient", grant["owner"]), grant["owner"]))
                return self._receipt_record(conn, dict(conn.execute("SELECT * FROM coordinator_receipts_v1 WHERE event=?", (event_id,)).fetchone()))

    def _receipt_record(self, conn, row):
        target = conn.execute("SELECT actual_recipient,authorizing_owner FROM coordinator_receipt_targets_v1 WHERE event=?", (row["event"],)).fetchone()
        return {**row, **(dict(target) if target else {})}

    def _proof(self, runtime, event, grant):
        if event["grant"] != grant["id"] or event["recipient"] != grant["owner"] or event["post"] <= grant["cutover"]:
            raise Refusal("event is not covered by this prospective role grant")
        row = runtime.one("SELECT * FROM events WHERE id=?", (event["id"],))
        queue = runtime.one("SELECT id FROM queue WHERE event=?", (event["id"],))
        if not row or not row["classification"] or not queue:
            raise Refusal("durable validated classification AND queue responsibility required")
        attempt = runtime.attempt(row["classifier"])
        if json.loads(attempt["binding"]) != LUNA or attempt["exit"] != 0 or not attempt["collected"]:
            raise Refusal("actual matching Luna-low collection required")
        canonical_uuid(attempt["session"])
        return {**attempt, "classification": row["classification"], "responsibility": queue["id"]}

    def _ack(self, conn, event, grant):
        recipient = event.get("receipt_recipient", grant["owner"])
        if recipient != grant["owner"]:
            own = conn.execute("SELECT 1 FROM coordinator_deliveries_v1 d JOIN thread_posts t ON t.thread_id=d.post "
                               "WHERE t.post_seq=? AND d.id=? AND d.owner=? AND d.actor=?",
                               (event["post"], event.get("parent_delivery"), grant["owner"], recipient)).fetchone()
            if not own or recipient != self.config["actor"]:
                raise Refusal("reply receipt does not belong to this actual automation/role delegation")
        if event["notice"] is None:
            row = conn.execute("SELECT recipient FROM posts WHERE seq=?", (event["post"],)).fetchone()
            if not row or row["recipient"] != recipient:
                raise Refusal("plain post not addressed to granted owner")
            return
        row = conn.execute("SELECT * FROM notification_outbox WHERE notification_id=?", (event["notice"],)).fetchone()
        if not row or row["recipient"] != recipient or row["post_seq"] != event["post"]:
            raise Refusal("notice does not belong to delegated owner/event")
        if row["delivery_state"] == "sending":
            raise Refusal("original queue sender still owns an unsettled sending effect")
        conn.execute("UPDATE notification_outbox SET delivery_state='acknowledged',"
                     "acknowledged_at=COALESCE(acknowledged_at,?),state_changed_at=?,claim_token=NULL "
                     "WHERE notification_id=?", (utc(), utc(), event["notice"]))
