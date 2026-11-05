"""Durable responsibility, frozen reservations and lifecycle journal.

Role: intrinsic-surface. Domain: coordinator responsibility. SQLite transactions
own intake/classification/queue, slot fencing and processed-at transitions.
No timeout, PID, result file or semantic assertion releases a reservation.
"""

from __future__ import annotations

from contextlib import contextmanager, nullcontext
import json
import os
from pathlib import Path
import sqlite3
import stat
import time

from .contracts import (Backpressure, Refusal, classification, digest, encode, ident,
                        response_tasks, collected_task_result)
from .delivery import DeliveryJournal, SCHEMA as DELIVERY_SCHEMA
from .custody import SCHEMA as CUSTODY_SCHEMA, witnesses
from .routine import SCHEMA as ROUTINE_SCHEMA
from .storage import SCHEMA as STORAGE_SCHEMA
from .publication import SCHEMA as PUBLICATION_SCHEMA
from .recovery import RecoveryJournal, SCHEMA as RECOVERY_SCHEMA
from .inputs import InputJournal, CONTROL_ROUTES, SCHEMA as INPUT_SCHEMA
from .execution_pool import ExecutionPool
from .integration import IntegrationJournal, SCHEMA as INTEGRATION_SCHEMA
from . import prospective, ordinary, capacity, admitted, windows, custodian_service, configuration, ref_scope

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS enrollments(
 role TEXT PRIMARY KEY, owner TEXT NOT NULL, profile TEXT NOT NULL,
 grant_id TEXT NOT NULL, cutover INTEGER NOT NULL, intake INTEGER NOT NULL,
 legacy_hold TEXT, reconciliation TEXT);
CREATE TABLE IF NOT EXISTS cursors(role TEXT PRIMARY KEY,seq INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS events(
 id TEXT PRIMARY KEY, role TEXT NOT NULL, payload TEXT NOT NULL, hash TEXT NOT NULL,
 received REAL NOT NULL, state TEXT NOT NULL DEFAULT 'received',
 classification TEXT, classifier TEXT, ack TEXT NOT NULL DEFAULT 'pending',
 ack_receipt TEXT, parent TEXT REFERENCES events(id), processed_at REAL,
 hold TEXT, error TEXT,recovery_count INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS queue(
 id TEXT PRIMARY KEY, event TEXT NOT NULL UNIQUE REFERENCES events(id),
 role TEXT NOT NULL, phase TEXT NOT NULL, task TEXT NOT NULL, package TEXT,
 state TEXT NOT NULL DEFAULT 'queued',job TEXT);
CREATE TABLE IF NOT EXISTS jobs(
 id TEXT PRIMARY KEY,role TEXT NOT NULL,phase TEXT NOT NULL,task TEXT NOT NULL,
 package TEXT,members TEXT NOT NULL,controller TEXT NOT NULL,token TEXT NOT NULL,
 created REAL NOT NULL,state TEXT NOT NULL DEFAULT 'reserved',active_attempt TEXT,
 effects TEXT NOT NULL DEFAULT 'unknown',effect_receipt TEXT,response TEXT,
 closed_at REAL,recovery_owner TEXT,recovery_state TEXT,recovery_count INTEGER NOT NULL DEFAULT 0,
 hold_reason TEXT,collection_handoff TEXT);
CREATE TABLE IF NOT EXISTS attempts(
 id TEXT PRIMARY KEY,kind TEXT NOT NULL,event TEXT,job TEXT,controller TEXT NOT NULL,
 profile TEXT NOT NULL,binding TEXT NOT NULL,state TEXT NOT NULL DEFAULT 'reserved',
 created REAL NOT NULL,begin REAL,ended REAL,exit INTEGER,collected REAL,
 session TEXT,turn TEXT,semantic TEXT,capture TEXT NOT NULL DEFAULT 'unknown',
 cleanup TEXT NOT NULL DEFAULT 'pending',result TEXT,error TEXT,detail TEXT NOT NULL DEFAULT '{}');
CREATE TABLE IF NOT EXISTS results(
 attempt TEXT PRIMARY KEY,job TEXT,event TEXT,result TEXT,error TEXT,
 exit INTEGER,capture TEXT NOT NULL,created REAL NOT NULL);
CREATE TABLE IF NOT EXISTS admissions(
 package TEXT PRIMARY KEY,owner TEXT NOT NULL,receipt TEXT NOT NULL,accepted TEXT);
CREATE TABLE IF NOT EXISTS qa_package_owners(package TEXT PRIMARY KEY,admission TEXT NOT NULL,job TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS alerts(
 id TEXT PRIMARY KEY,subject TEXT NOT NULL,kind TEXT NOT NULL,created REAL NOT NULL,
 payload TEXT NOT NULL,processed_at REAL);
CREATE TABLE IF NOT EXISTS artifacts(
 path TEXT PRIMARY KEY,attempt TEXT NOT NULL,dev INTEGER NOT NULL,ino INTEGER NOT NULL,
 size INTEGER NOT NULL,mtime INTEGER NOT NULL,sha256 TEXT NOT NULL,conserved TEXT,removed REAL,error TEXT);
CREATE INDEX IF NOT EXISTS queue_pending ON queue(role,phase,state);
CREATE INDEX IF NOT EXISTS events_parent ON events(parent);
CREATE INDEX IF NOT EXISTS attempts_job ON attempts(job);
"""


def owned_bytes(home, maximum_entries):
    frontier, total, entries = [home], 0, 0
    while frontier:
        directory = frontier.pop()
        try:
            children = os.scandir(directory)
        except FileNotFoundError:
            continue  # Concurrent owned-store rotation/removal, no symlink walk.
        with children:
            for child in children:
                if Path(directory) == Path(home) and child.name == 'sessions':
                    continue  # Legacy Codex namespaces: exclude BEFORE stat/traversal.
                entries += 1
                if entries > maximum_entries:
                    raise Backpressure("owned artifact entry-count bound reached")
                try:
                    info = child.stat(follow_symlinks=False)
                except FileNotFoundError:
                    continue
                total += info.st_size
                if stat.S_ISDIR(info.st_mode):
                    frontier.append(child.path)
    return total


def private_directory(path):
    path = Path(path)
    if not path.is_absolute() or any(p.is_symlink() for p in (path, *path.parents)):
        raise Refusal("state path must be absolute with no symlink components")
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    if path.stat().st_mode & 0o077:
        raise Refusal("state directory must be mode 0700")
    return path


class Store(IntegrationJournal, DeliveryJournal, RecoveryJournal, InputJournal):
    def __init__(self, config, controller=None, clock=time.time):
        self.config, self.controller, self.clock = config, controller or ident(), clock
        self.launch_authorizer = None
        self.task_launch_authorizer = None
        self.processing = None  # Explicit service-local capability, never an intake flag rewrite.
        self.execution_pool = ExecutionPool(config, runtime=self)
        self.home = private_directory(config["state_dir"])
        self.path = self.home / "runtime.sqlite3"
        # Closing ANY raw descriptor for an existing SQLite file can release
        # this process's POSIX locks held by other SQLite connections. Owner
        # CLI opens must not invalidate the running collector's journal locks.
        try:
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        except FileExistsError:
            pass
        else:
            os.close(fd)
        info=self.path.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_mode & 0o077:
            raise Refusal("private single-link runtime database required")
        self.db = sqlite3.connect(self.path, isolation_level=None, timeout=15)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys=ON")
        version = self.db.execute("PRAGMA user_version").fetchone()[0]
        if version not in {0, 1}:
            raise Refusal("unsupported runtime schema; offline owned migration required")
        if version == 0 and self.db.execute("SELECT 1 FROM sqlite_master WHERE type='table'").fetchone():
            raise Refusal("unversioned existing runtime cannot be silently adopted")
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        admitted.policy(config)
        windows.policy(config)
        custodian_service.policy(config)
        self.db.executescript(SCHEMA + DELIVERY_SCHEMA + CUSTODY_SCHEMA + ROUTINE_SCHEMA + STORAGE_SCHEMA + PUBLICATION_SCHEMA + RECOVERY_SCHEMA + INPUT_SCHEMA + INTEGRATION_SCHEMA + prospective.SCHEMA + ordinary.SCHEMA + capacity.SCHEMA + admitted.SCHEMA + windows.SCHEMA + custodian_service.SCHEMA)
        self.db.execute("PRAGMA user_version=1")
        self.db.executescript(configuration.SCHEMA + ref_scope.SCHEMA)
        self._bind_config()
        from .processing import SCHEMA as PROCESSING_SCHEMA
        self.db.executescript(PROCESSING_SCHEMA)
        from .processing import migrate_links
        migrate_links(self)
        from .reviews import SCHEMA as REVIEW_SCHEMA
        from .service import SCHEMA as SERVICE_SCHEMA
        from .branches import SCHEMA as BRANCH_SCHEMA
        from .service_recovery import SCHEMA as SERVICE_RECOVERY_SCHEMA
        self.db.executescript(REVIEW_SCHEMA + SERVICE_SCHEMA + BRANCH_SCHEMA + SERVICE_RECOVERY_SCHEMA)
        self.db.execute('CREATE TABLE IF NOT EXISTS shared_custody_intents(delivery TEXT PRIMARY KEY,archive TEXT NOT NULL,basis TEXT NOT NULL,state TEXT NOT NULL,receipt TEXT)')

    def _bind_config(self):
        with self.tx():
            row = self.one("SELECT value FROM meta WHERE key='configuration'")
            expected = digest(self.config)
            current = configuration.latest(self)
            if row and (current['current'] if current else row['value']) != expected:
                raise Refusal("configuration differs from this journal; use the supported current-configuration transition")
            if current and (current['original'] != row['value'] or json.loads(current['configuration']) != self.config):
                raise Refusal('current configuration/original journal binding differs')
            self.db.execute("INSERT OR IGNORE INTO meta VALUES('configuration',?)", (expected,))
            self.db.execute("INSERT OR IGNORE INTO meta VALUES('actor',?)", (self.config["actor"],))
            windows.initialize(self)

    def close(self):
        self.db.close()

    @contextmanager
    def tx(self, *, collection=None):
        self.db.execute("BEGIN IMMEDIATE")
        try:
            if collection is None:
                configuration.assert_current(self)
            else:
                configuration.authorize_collection(self, collection)
            yield
            self.db.execute("COMMIT")
        except BaseException:
            self.db.execute("ROLLBACK")
            raise

    def one(self, sql, values=()):
        row = self.db.execute(sql, values).fetchone()
        return dict(row) if row else None

    def rows(self, sql, values=()):
        return [dict(r) for r in self.db.execute(sql, values)]

    def usage(self):
        counts = {name: self.db.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
                  for name in ("events", "attempts", "jobs", "alerts", "outboxes")}
        counts["bytes"] = owned_bytes(self.home, self.config["limits"].get("max_files", 50000))
        counts['publication_reserved_bytes']=self.db.execute("SELECT COALESCE(SUM(length(b.body)),0) FROM file_publications p JOIN artifact_blobs b ON b.sha256=p.proposed_sha WHERE p.state!='published'").fetchone()[0]
        counts['bytes']+=counts['publication_reserved_bytes']
        counts['custodian_reserved_bytes'] = self.one(
            "SELECT COUNT(*) AS n FROM custodian_visits WHERE state IN ('prepared','running')")['n'] * (3 * custodian_service.CAPTURE + 4096)
        counts['bytes'] += counts['custodian_reserved_bytes']
        counts['excluded_codex_store_scope'] = 'sessions subtree opaque/unmeasured; shared account stores not inventoried'
        return counts

    def budget(self, kind, incoming=0, *, event=None, job=None):
        if event or job:
            if not self.db.in_transaction:
                raise Refusal('duty credit allocation requires the source write transaction')
            admitted.charge(self, kind, event=event, job=job)
        usage, limits = self.usage(), self.config["limits"]
        if usage["bytes"] + incoming + capacity.PRESSURE_RESERVE >= limits["max_bytes"]:
            raise Backpressure("cumulative journal/artifact bytes held; conserve before admitting more")
        if self.config.get('window_service') and kind in windows.KINDS:
            windows.charge(self, kind)
        elif kind is not None and usage[kind] >= limits.get(f"max_{kind}", limits["max_events"]):
            raise Backpressure(f"cumulative {kind} bound reached; held work is retained")
        admitted.check(self, usage, kind)

    def enroll(self, role, grant):
        selected = self.config["roles"][role]
        if grant["owner"] != selected["owner"] or grant["actor"] != self.config["actor"]:
            raise Refusal("grant identity differs from role enrollment")
        with self.tx():
            self.db.execute("INSERT INTO enrollments VALUES(?,?,?,?,?,1,?,NULL)",
                            (role, selected["owner"], selected["profile"], grant["id"],
                             grant["cutover"], selected["legacy_hold"]))
            self.db.execute("INSERT INTO cursors VALUES(?,?)", (role, grant["cutover"]))

    def enrollment(self, role):
        row = self.one("SELECT * FROM enrollments WHERE role=?", (role,))
        if not row or not self.role_enabled(role):
            raise Refusal("role has no active runtime enrollment")
        return row

    def role_enabled(self, role):
        row = self.one('SELECT intake FROM enrollments WHERE role=?', (role,))
        return bool(row and (self.processing.role(role) if self.processing else row['intake']))

    def reconcile_legacy(self, role, actor, receipt):
        if actor != self.enrollment(role)["owner"]:
            raise Refusal("only actual role owner can reconcile its legacy reservation")
        if not receipt.get("collector") or not receipt.get("evidence") or receipt.get("remaining_holds") != []:
            raise Refusal("actual collector evidence and explicit empty remaining holds required")
        with self.tx():
            self.db.execute("UPDATE enrollments SET legacy_hold=NULL,reconciliation=? WHERE role=?",
                            (encode({"actor": actor, **receipt}), role))

    def admit(self, package, owner, receipt, accepted=None):
        if owner != self.config["roles"]["Branch"]["owner"] or not receipt:
            raise Refusal("QA package needs actual Branch admission owner and exact receipt")
        with (nullcontext() if self.db.in_transaction else self.tx()):
            self.db.execute("INSERT INTO admissions VALUES(?,?,?,?) ON CONFLICT(package) DO UPDATE "
                            "SET owner=excluded.owner,receipt=excluded.receipt,accepted=excluded.accepted",
                            (package, owner, encode(receipt), encode(accepted) if accepted else None))

    def ingest(self, event, cursor=None):
        role = event["role"]
        self.enrollment(role)
        if self.processing and not self.processing.event(event):
            raise Refusal('input outside explicit processing selection; no journal migration/replay')
        if role not in self.config["roles"] or event["recipient"] != self.config["roles"][role]["owner"]:
            raise Refusal("event recipient is outside actual enrollment")
        content = encode(event)
        if len(content.encode()) > 262144:
            raise Backpressure("event body exceeds per-message bound; upstream retains it unACKed")
        with self.tx():
            old = self.one("SELECT hash FROM events WHERE id=?", (event["id"],))
            if old and old["hash"] != digest(event):
                raise Refusal("same event identity has different immutable content")
            if not old:
                if (self.processing and event.get('kind') == 'board'
                        and not self.processing.owed_control(event)):
                    from .service import admit_input
                    admit_input(self)
                windows.charge(self, None, new_input=True)
                admitted.admit(self, event)
                self.budget("events", len(content.encode()), event=event['id'])
                self.db.execute("INSERT INTO events(id,role,payload,hash,received,parent) VALUES(?,?,?,?,?,?)",
                                (event["id"], role, content, digest(event), self.clock(), event.get("parent")))
                from .processing import note_source
                note_source(self, event['id'])
            if cursor is not None:
                self.db.execute("UPDATE cursors SET seq=MAX(seq,?) WHERE role=?", (cursor, role))
        return not bool(old)

    def event(self, event_id):
        row = self.one("SELECT * FROM events WHERE id=?", (event_id,))
        if not row:
            raise Refusal("unknown event")
        payload = json.loads(row['payload'])
        if payload == {}:
            custody = self.one("SELECT binding FROM source_custody WHERE event=? AND basis='result'", (event_id,))
            if custody:
                binding = json.loads(custody['binding'])
                source = self.one('SELECT result FROM results WHERE attempt=?', (binding['attempt'],))
                if not source:
                    raise Refusal('original result-backed source custody unavailable')
                payload = {**binding['header'], 'body': json.loads(source['result'])}
                if digest(payload) != row['hash']:
                    raise Refusal('relocated original source no longer matches its hash')
        return payload

    def _attempt(self, kind, event, job, binding, profile, *, continuing=None):
        if job:
            self.require_execution_open(job)
        self.require_active_sources(event, job)
        self.budget("attempts", event=event, job=job)
        if profile not in self.config['profiles']:
            raise Refusal('profile advice outside runtime account authorization')
        allocation = ({'profile': continuing['profile'], 'existing_context': continuing['component'],
                       'actual_run': continuing['run'], 'collector': continuing['collector']}
                      if continuing else self.execution_pool.allocate())
        attempt = ident()
        self.db.execute("INSERT INTO attempts(id,kind,event,job,controller,profile,binding,created) "
                        "VALUES(?,?,?,?,?,?,?,?)", (attempt, kind, event, job, self.controller,
                                                  allocation['profile'], encode(binding), self.clock()))
        provenance = {"selection_reason": ('existing observed continuing context/account' if continuing else 'ordinary rotation over current shared enabled execution pool'),
                      'configured_dispatch_authority': self.config.get('dispatch_authority'),
                      "configuration_sha256": digest(self.config),
                      "profile_advice": profile, "execution_pool_allocation": allocation}
        if self.processing:
            provenance['processing_capability'] = self.processing.reserve(attempt, event, job)
        self.db.execute("UPDATE attempts SET detail=? WHERE id=?", (encode(provenance), attempt))
        return attempt

    def source_roles(self, event=None, job=None):
        if event:
            return {self.one("SELECT role FROM events WHERE id=?", (event,))["role"]}
        row = self.job(job)
        members = json.loads(row["members"])
        return {row["role"]} | {self.one("SELECT role FROM events WHERE id=?", (m["event"],))["role"] for m in members}

    def require_active_sources(self, event=None, job=None):
        for role in self.source_roles(event, job):
            self.enrollment(role)

    def authorize_launch(self, attempt):
        row = self.attempt(attempt)
        if self.processing:
            self.processing.authorize(row)
        if row['job']:
            self.require_execution_open(row['job'])
        self.require_active_sources(row["event"], row["job"])
        if self.launch_authorizer:
            self.launch_authorizer(self.source_roles(row["event"], row["job"]))
        if row['kind'] != 'task':
            return
        job = self.job(row['job'])
        self.integration_launch_current(job)
        if (self.config.get('software_delegation')
                or 'software_authority' in json.loads(row['detail'])
                or prospective.requires_authority(self, job)):
            if not self.task_launch_authorizer:
                raise Refusal('software task launch requires its current authority checker')
            if job['active_attempt'] != attempt:
                raise Refusal('software launch is not the current owned task attempt')
            self.task_launch_authorizer(row)

    def claim_classification(self):
        with self.tx():
            if not self._classification_available():
                return None
            row = next((e for e in self.rows("SELECT e.id,e.role FROM events e WHERE e.state='received' ORDER BY e.received,e.id")
                        if self.role_enabled(e['role']) and (not self.processing or self.processing.event(self.event(e['id'])))), None)
            if not row:
                return None
            selected = self.config["classifier"]
            attempt = self._attempt("classifier", row["id"], None, selected["binding"], selected["profile"])
            self.db.execute("UPDATE events SET state='classifying',classifier=? WHERE id=?", (attempt, row["id"]))
        return attempt, self.routing_event(row["id"])

    def _classification_available(self):
        service = self.processing and 'service' in self.processing.current()[1]
        active = self.db.execute("SELECT COUNT(*) FROM attempts WHERE job IS NULL "
                                 "AND state IN ('reserved','running','unknown')" + (' AND controller=?' if service else ''),
                                 (self.controller,) if service else ()).fetchone()[0]
        return active < self.config.get("classification_capacity", 5)

    def claim_classification_recovery(self):
        with self.tx():
            if not self._classification_available():
                return None
            row = self.one("SELECT e.id,e.classifier FROM events e JOIN attempts a ON e.classifier=a.id "
                           "JOIN enrollments r ON r.role=e.role "
                           "WHERE e.state='classification-held' AND e.recovery_count=0 AND a.collected IS NOT NULL AND r.intake=1 "
                           "ORDER BY e.received,e.id LIMIT 1")
            if not row:
                return None
            selected = self.config["diagnosis"]
            attempt = self._attempt("diagnosis", row["id"], None, selected["binding"], selected["profile"])
            detail = {**json.loads(self.attempt(attempt)["detail"]), "prior_classifier": row["classifier"]}
            self.db.execute("UPDATE attempts SET detail=? WHERE id=?", (encode(detail), attempt))
            self.db.execute("UPDATE events SET state='classifying',classifier=?,recovery_count=1 WHERE id=?",
                            (attempt, row["id"]))
        return attempt, self.routing_event(row["id"])

    def attempt(self, attempt):
        row = self.one("SELECT * FROM attempts WHERE id=?", (attempt,))
        if not row:
            raise Refusal("attempt not owned by this journal")
        return row

    def begin(self, attempt, detail):
        with self.tx():
            row = self.attempt(attempt)
            if row['job']:
                self.require_execution_open(row['job'])
            if row["controller"] != self.controller or row["state"] != "reserved":
                raise Refusal("begin requires this controller's unstarted reservation")
            self.db.execute("UPDATE attempts SET begin=?,state='running',detail=? WHERE id=?",
                            (self.clock(), encode({**json.loads(row["detail"]), **detail}), attempt))

    def session(self, attempt, session, turn=None, detail=None):
        with self.tx(collection=attempt):
            row = self.attempt(attempt)
            if row['job']:
                self.require_execution_open(row['job'])
            if row["controller"] != self.controller or row["ended"] is not None:
                raise Refusal("foreign or ended attempt cannot bind a session")
            merged = {**json.loads(row["detail"]), **(detail or {})}
            self.db.execute("UPDATE attempts SET session=?,turn=?,detail=? WHERE id=?",
                            (session, turn, encode(merged), attempt))

    def observe_semantic(self, attempt, semantic):
        with self.tx(collection=attempt):
            row = self.attempt(attempt)
            if row['job']:
                self.require_execution_open(row['job'])
            if row["controller"] != self.controller or row["ended"] is not None:
                raise Refusal("semantic observation belongs to the live original collector")
            self.db.execute("UPDATE attempts SET semantic=? WHERE id=?", (semantic, attempt))

    def collect(self, attempt, outcome):
        """Only the launching controller supplies actual child.wait() outcome."""
        with self.tx(collection=attempt):
            row = self.attempt(attempt)
            if row["controller"] != self.controller or row["collected"] is not None:
                raise Refusal("foreign or duplicate collection refused")
            if outcome.get("exit") is not None and type(outcome["exit"]) is not int:
                raise Refusal("actual numeric process exit required when observed")
            result = outcome.get("result")
            result_json = encode(result) if result is not None else None
            if result_json and len(result_json.encode()) > self.config["limits"]["max_result_bytes"]:
                outcome = {**outcome, "error": "typed result exceeded bounded capture; original responsibility held",
                           "capture": "incomplete"}
                result, result_json = None, None
            no_start = bool(outcome.get("detail", {}).get("known_not_started")) and row["begin"] is None
            ended = self.clock() if outcome.get("exit") is not None else None
            self.db.execute("UPDATE attempts SET state=?,ended=?,exit=?,collected=?,result=?,error=?,"
                            "semantic=?,capture=?,cleanup=?,detail=? WHERE id=?",
                            ("not-started" if no_start else ("collected" if ended else "unknown"), ended, outcome.get("exit"),
                             self.clock() if ended or no_start else None, result_json, outcome.get("error"),
                             result.get("semantic") if isinstance(result, dict) else row["semantic"],
                             outcome["capture"], outcome["cleanup"],
                             encode({**json.loads(row["detail"]), **outcome.get("detail", {})}), attempt))
            self.db.execute("INSERT INTO results VALUES(?,?,?,?,?,?,?,?)",
                            (attempt, row["job"], row["event"], result_json, outcome.get("error"),
                             outcome.get("exit"), outcome["capture"], self.clock(),))

    def classification_failed(self, attempt, error):
        with self.tx():
            self.db.execute("UPDATE events SET state='classification-held',error=? WHERE classifier=? AND state='classifying'",
                            (str(error)[:2000], attempt))

    def capture_gap(self, attempt, error):
        with self.tx():
            row = self.attempt(attempt)
            if row["controller"] != self.controller:
                raise Refusal("capture qualification belongs to the original collector")
            detail={**json.loads(row['detail']),'protocol_capture':row['capture'],
                    'pre_inventory_error':row['error'],'artifact_inventory_error':str(error)[:1000]}
            message=((row['error']+'; ') if row['error'] else '')+'artifact inventory: '+str(error)
            self.db.execute("UPDATE attempts SET capture='artifact-inventory-incomplete',error=?,detail=? WHERE id=?",
                            (message[:2000],encode(detail),attempt))
            self.db.execute("UPDATE results SET capture='artifact-inventory-incomplete',error=? WHERE attempt=?",
                            (message[:2000], attempt))

    def commit_classification(self, attempt):
        row = self.attempt(attempt)
        if row["exit"] != 0 or not row["collected"] or row["capture"] != "complete" or row["error"]:
            raise Refusal("classification requires actual successful collection and complete typed capture")
        event = self.routing_event(row["event"])
        answer = classification(json.loads(row["result"]), event, self.config)
        task = self.config["tasks"].get(answer["task"])
        with self.tx():
            state = self.one("SELECT state,classifier FROM events WHERE id=?", (event["id"],))
            if state != {"state": "classifying", "classifier": attempt}:
                raise Refusal("stale classification cannot replace responsibility")
            delivery = event["kind"] == "outgoing-response" and answer["task"] == "@delivery"
            control=answer['task'] in CONTROL_ROUTES
            if control:self.queue_input_control(event,answer)
            else:
                self.write_input_queue(event,answer,event['role'] if delivery else task['role'],
                                       'delivery' if delivery else task['phase'],'routed' if delivery else 'queued')
                self.db.execute("UPDATE outboxes SET state='pending' WHERE event=? AND state='classification-pending'", (event["id"],))
            self.db.execute("UPDATE events SET classification=?,state='queued',ack=CASE WHEN ack IN ('done','plain','internal') "
                            "THEN ack ELSE 'ready' END,error=NULL WHERE id=?",
                            (encode(answer), event["id"]))
        return answer

    def ack_state(self, event, state, receipt=None):
        with self.tx():
            row = self.one("SELECT classification FROM events WHERE id=?", (event,))
            if not row or not row["classification"]:
                raise Refusal("no durable classification and queue responsibility")
            self.db.execute("UPDATE events SET ack=?,ack_receipt=COALESCE(?,ack_receipt) WHERE id=?",
                            (state, encode(receipt) if receipt else None, event))

    def _capacity(self, task):
        if task["phase"] == "proposer":
            return task.get("capacity", 1)
        return 5 if task["phase"] == "execution" else 1

    def reserve(self):
        """Freeze members and reserve under the same cross-controller write lock."""
        with self.tx():
            pending = self.rows("SELECT q.* FROM queue q JOIN events e ON e.id=q.event "
                                "WHERE q.state='queued' AND e.hold IS NULL ORDER BY e.received,q.id")
            return self._reserve_first(pending)

    def _reserve_first(self, pending):
        for row in pending:
            job = self._reserve_candidate(row)
            if job:
                return job
        return None

    def _reserve_candidate(self, row):
        role, phase, task = row["role"], row["phase"], self.config["tasks"][row["task"]]
        enrollment = self.one("SELECT * FROM enrollments WHERE role=?", (role,))
        held_phases = self.config["roles"][role].get("legacy_hold_phases", list({"proposer", "integrator", "execution", "cleanup"}))
        from .resource_scopes import blocked
        if (not enrollment or not self.role_enabled(role)
                or self.processing and not self.processing.task(row)
                or self.processing and task.get('execution') == 'owner' and not self.processing.review_task(row['task'])
                or enrollment["legacy_hold"] and phase in held_phases and blocked(self, row)):
            return None
        if task.get("active") is False:
            return None
        if task.get("require_package_scope") and not self.one("SELECT package FROM admissions WHERE package=?", (row["package"],)):
            return None
        outstanding = self.rows("SELECT * FROM jobs WHERE role=? AND phase=? AND state!='closed'", (role, phase))
        active = sum(not self.execution_complete(job) for job in outstanding)
        if active >= self._capacity(task):
            return None
        if task.get("require_package_scope") and any(j["package"] == row["package"] for j in outstanding):
            return None  # Unsettled responsibility in the same admitted scope stays fenced.
        if role == "QA" and not self.one("SELECT * FROM admissions WHERE package=?", (row["package"],)):
            return None
        if role == 'QA' and (self.config.get('window_service') or self.processing):
            other = 'cleanup' if phase == 'execution' else 'execution'
            if any(not self.execution_complete(j) for j in self.rows(
                    "SELECT * FROM jobs WHERE role='QA' AND phase=? AND state!='closed'", (other,))):
                return None  # First phase (<=5 separate packages), then one consolidation slot.
        if role == "QA" and phase == "execution" and self.one(
                "SELECT id FROM jobs WHERE role='QA' AND package=? AND phase IN ('execution','cleanup') AND state!='closed'", (row["package"],)):
            return None
        admission = self.one("SELECT * FROM admissions WHERE package=?", (row["package"],)) if role == "QA" else None
        prior = self.one("SELECT * FROM qa_package_owners WHERE package=?", (row["package"],)) if admission and phase == "execution" else None
        if prior and prior["admission"] == digest(admission["receipt"]):
            return None
        if prior and any(self.dependency_hold(m["event"]) for m in json.loads(self.job(prior["job"])["members"])):
            return None
        try:
            window = self.integration_window(row)
        except Refusal:
            return None
        members = json.loads(window['basis'])['members'] if window else self._members(row)
        packages = {member["package"] for member in members}
        package = next(iter(packages)) if len(packages) == 1 else None
        self.budget("jobs", event=row['event'])
        job, token = ident(), ident()
        self.db.execute("INSERT INTO jobs(id,role,phase,task,package,members,controller,token,created) "
                        "VALUES(?,?,?,?,?,?,?,?,?)", (job, role, phase, row["task"], package,
                                                     encode(members), self.controller, token, self.clock()))
        self.db.execute('INSERT INTO job_resource_policies VALUES(?,?,?)', (job, encode(self.config['tasks'][row['task']]),
                        encode(self.one('SELECT * FROM admissions WHERE package=?',(package,))) if package else None))
        if admission and phase == "execution":
            self.db.execute("INSERT OR REPLACE INTO qa_package_owners VALUES(?,?,?)", (row["package"], digest(admission["receipt"]), job))
        for member in members:
            self.db.execute("UPDATE queue SET state='reserved',job=? WHERE id=? AND state='queued'",
                            (job, member["queue"]))
        if window:
            self.db.execute('UPDATE integration_windows SET job=? WHERE id=? AND job IS NULL', (job, window['id']))
        return self.one("SELECT * FROM jobs WHERE id=?", (job,))

    def _members(self, row):
        if row["phase"] != "integrator":
            return [self._input_member(row)]
        rows = self.rows("SELECT q.* FROM queue q JOIN events e ON q.event=e.id WHERE q.role=? "
                         "AND q.task=? AND q.state='queued' AND e.hold IS NULL ORDER BY e.received,q.id",
                         (row["role"], row["task"]))
        if self.processing:
            rows = [r for r in rows if self.processing.task(r)]
        if self.config["tasks"][row["task"]].get("require_package_scope"):
            rows = [r for r in rows if r["package"] == row["package"]]
        if self.config.get('window_service'):
            rows = rows[:self.config['window_service']['batch_size']]
        return [self._input_member(r) for r in rows]

    def _input_member(self,row):
        member={'queue':row['id'],'event':row['event'],'hash':digest(self.event(row['event'])),'package':row['package']}
        selection=self.input_resolution(row['event'])
        if selection:member['input_resolution']=selection['version']
        return member

    def start_job(self, job, token, profile=None):
        with self.tx():
            row = self.job(job, token)
            self.integration_launch_current(row)
            if row["controller"] != self.controller or row["state"] != "reserved":
                raise Refusal("only original reservation controller may launch once")
            task = self.config["tasks"][row["task"]]
            context = None
            if self.processing and self.processing.review_task(row['task']):
                from .reviews import BINDING
                task = {**task, 'binding': BINDING}
                member = json.loads(row['members'])[0]
                source = self.event(member['event'])
                from .branches import review_key
                packet = source.get('body', {}).get('review', {}) if isinstance(source.get('body'), dict) else {}
                component = review_key(self,row,packet)
                context = self.one('SELECT * FROM review_contexts WHERE component=?', (component,))
                if context and (context['state'] != 'live' or context['collector'] != self.controller
                                or context['capability'] != self.processing.key):
                    raise Refusal('original continuing reviewer unavailable; disclose recovery instead of new allocation')
            attempt = self._attempt("task", None, job, task["binding"], profile or task["profile"], continuing=context)
            window = self.integration_context(job)
            if window:
                detail = {**json.loads(self.attempt(attempt)['detail']), 'integration_window': window}
                self.db.execute('UPDATE attempts SET detail=? WHERE id=?', (encode(detail), attempt))
            self.db.execute("UPDATE jobs SET active_attempt=?,state='running' WHERE id=?", (attempt, job))
            from .branches import acquire_attempt
            acquire_attempt(self,row,attempt,context)
        return attempt

    def execution_complete(self, job):
        """Release only execution capacity; delivery, queue and source stay owned."""
        if job['recovery_state']=='source-inactive-custody-held' and self.config['tasks'][job['task']]['effects']=='none':
            return True  # Explicit owner-supported inactive inquiry, never processing/END.
        if self.integration_retired(job['id']):
            return True
        if job["state"] != "awaiting-delivery" or job["effects"] not in {"none", "reconciled"} or job["hold_reason"]:
            return False
        attempt = self.attempt(job["active_attempt"]) if job["active_attempt"] else None
        return bool(attempt and attempt["begin"] is not None and attempt["ended"] is not None
                    and attempt["collected"] is not None and attempt["exit"] == 0
                    and attempt["state"] == "collected" and attempt["capture"] == "complete"
                    and attempt["semantic"] == "DONE" and not attempt["error"])

    def job(self, job, token=None):
        row = self.one("SELECT * FROM jobs WHERE id=?", (job,))
        if not row or (token is not None and row["token"] != token):
            raise Refusal("job reservation fence differs")
        return row

    def reconcile_effects(self, job, token, actor, receipt):
        with self.tx():
            row = self.job(job, token)
            attempt = self.attempt(row["active_attempt"])
            if not attempt["collected"] or attempt["ended"] is None:
                raise Refusal("effects cannot release a live/uncollected/unknown attempt")
            if actor != self.config["roles"][row["role"]]["owner"]:
                raise Refusal("actual role owner must reconcile possible effects/outboxes")
            if self.one("SELECT target FROM file_publications WHERE attempt=? AND state!='published'",(attempt['id'],)):
                raise Refusal('unresolved exact publication intent needs actual source/effect recovery; generic effect receipt cannot waive it')
            if not receipt.get("evidence") or receipt.get("unknown_effects") != []:
                raise Refusal("effect evidence and explicit empty unknown effects required")
            self.db.execute("UPDATE jobs SET effects='reconciled',effect_receipt=? WHERE id=?",
                            (encode({"actor": actor, **receipt}), job))

    def finish_job(self, job, token):
        with self.tx():
            row = self.job(job, token)
            self.require_execution_open(job)
            if row["controller"] != self.controller:
                raise Refusal("stale/foreign controller cannot close a successor reservation")
            if row["state"] == "closed":
                return None
            attempt = self.attempt(row["active_attempt"])
            task = self.config["tasks"][row["task"]]
            from .branches import settle_attempt
            settle_attempt(self,attempt['id'])
            if not attempt["collected"] or attempt["ended"] is None:
                raise Refusal("actual owned exit and collection required before release")
            if self.one("SELECT target FROM file_publications WHERE attempt=? AND state!='published'",(attempt['id'],)):
                self.failure_delivery(row,attempt,task,'Unresolved exact publication intent; source/effect uncertainty remains held')
                self.db.execute("UPDATE jobs SET state='held',hold_reason='unresolved publication intent' WHERE id=?",(job,))
                return None
            if attempt["exit"] != 0 or attempt["capture"] != "complete" or attempt["error"]:
                self.failure_delivery(row,attempt,task,"Collected failure/capture requires bounded recovery or real owner disposition")
                self.db.execute("UPDATE jobs SET state='held' WHERE id=?", (job,))
                return None
            try:result = collected_task_result(attempt)
            except Refusal as exc:
                self.failure_delivery(row,attempt,task,'Invalid inner task contract: '+str(exc))
                self.db.execute("UPDATE jobs SET state='held',hold_reason=? WHERE id=?",(str(exc),job))
                return None
            if result["semantic"] != "DONE":
                self.failure_delivery(row,attempt,task,"Incomplete task: retain all findings/failures/UNKNOWNs")
                self.db.execute("UPDATE jobs SET state='held' WHERE id=?", (job,))
                return None
            if self.config.get('software_delegation') or json.loads(attempt['detail']).get('software_authority'):
                detail = json.loads(attempt['detail'])
                tools = detail.get('tool_completion', {})
                from .reviews import collected_proof
                reviewed = collected_proof(self, row, attempt)
                if (not detail.get('software_authority') or not (reviewed or tools.get('complete'))
                        or (not task.get('routine_completion') and (tools.get('nonzero_completions')
                            or any(item.get('status') == 'failed' for item in tools.get('items', []))))):
                    reason = 'Prospective software task lacks complete launch-authority/tool capture; retain original effects and custody'
                    self.failure_delivery(row, attempt, task, reason)
                    self.db.execute("UPDATE jobs SET state='held',hold_reason=? WHERE id=?", (reason, job))
                    return None
            if task.get('routine_completion'):
                from .readiness import assess
                assess(self,attempt)  # Same local obligation contract as publisher and delegated collector.
                run=self.one('SELECT state FROM routine_runs WHERE attempt=?',(attempt['id'],))
                published=self.rows("SELECT target FROM file_publications WHERE attempt=? AND state='published'",(attempt['id'],))
                if (not run or run['state']!='reconciled' or
                        {p['target'] for p in published}!=set(task['routine_completion']['targets'])):
                    from .publication import INCOMPLETE_HOLD
                    raise Refusal(INCOMPLETE_HOLD)
            self.prepare_handoffs(row, attempt, task, result)
            if row["role"] == "Work" and result["category"] in {"scope", "blocker"}:
                self.owner_question(row, attempt, "Work-owned consequential question stays with the actual Decider; no automatic self-loop")
                self.gate_result_delivery(row, attempt, result)
                if not self.deliveries_settled(job):
                    self.db.execute("UPDATE jobs SET state='held',hold_reason='awaiting actual Decider delivery/settlement' WHERE id=?", (job,))
                    return None
            if task["effects"] in {"none", "owned-artifacts"}:
                self.db.execute("UPDATE jobs SET effects='none' WHERE id=?", (job,))
            elif row["effects"] != "reconciled":
                self.owner_question(row, attempt, "Actual owning role: reconcile the collected task's possible effects/outboxes", effects=True)
                self.gate_result_delivery(row, attempt, result)
                self.db.execute("UPDATE jobs SET state='held' WHERE id=?", (job,))
                return None
            response = None if row["role"] == "Work" and result["category"] in {"scope", "blocker"} else self._response(row, attempt, task, result)
            if task.get("delivery_required"):
                self.owner_report(row, attempt, result)
            response = self.gate_result_delivery(row, attempt, result, response)
            if not self.deliveries_settled(job):
                self.db.execute("UPDATE jobs SET state='awaiting-delivery',response=? WHERE id=?", (response, job))
                return response
            self.db.execute("UPDATE queue SET state='done' WHERE job=?", (job,))
            self.db.execute("UPDATE jobs SET state='closed',closed_at=?,response=? WHERE id=?",
                            (self.clock(), response, job))
        self.complete_events()
        return response

    def _response(self, job, attempt, task, result):
        choices = response_tasks(task, result, self.config)
        if not choices and result["category"] != "complete":
            raise Refusal("unroutable result retains its slot and original meaning")
        if not choices:
            return None
        response_id = digest({"response": attempt["id"]})
        if self.one("SELECT id FROM events WHERE id=?", (response_id,)):
            return response_id
        if task["role"] == "QA" and task["phase"] == "cleanup" and result["category"] == "qualification":
            admitted = self.one("SELECT accepted FROM admissions WHERE package=?", (job["package"],))
            new_effects = ordinary.needs_acceptance(self, job['package'])
            if (new_effects and not ordinary.qualification_current(self, job)) or (not new_effects and (not admitted or not admitted['accepted'])):
                raise Refusal("QA qualification awaits actual accepted package evidence")
        members = json.loads(job["members"])
        destination = self.config["tasks"][choices[0]]["role"]
        if any(self.config["tasks"][n]["role"] != destination for n in choices):
            raise Refusal("response route must name one actual recipient role")
        response = {
            "id": response_id, "role": destination,
            "recipient": self.enrollment(destination)["owner"], "author": attempt["session"],
            "source_role": job["role"], "source_attempt": attempt["id"], "source_job": job["id"],
            "effect_observation": json.loads(job['effect_receipt']) if job['effect_receipt'] else None,
            "source_members": members, "package": job["package"], "parent": members[0]["event"],
            "artifact_witnesses": witnesses(self, attempt["id"]) or self.rows("SELECT path,dev,ino,size,mtime,sha256 FROM artifacts WHERE attempt=?", (attempt["id"],)),
            "allowed_tasks": choices, "notice": None, "board_id": None,
            "body": result, "kind": "response", "grant": None,
        }
        branch_keys={self.event(m['event']).get('branch_binding') for m in members}-{None}
        if len(branch_keys)==1:
            response['branch_binding']=next(iter(branch_keys))
        self.budget("events", len(encode(response).encode()), job=job['id'])
        self.db.execute("INSERT INTO events(id,role,payload,hash,received,parent) VALUES(?,?,?,?,?,?)",
                        (response["id"], destination, encode(response), digest(response),
                         self.clock(), response["parent"]))
        if task.get("publish_internal_results"):
            self._outbox(job["role"], destination, "result", response, job=job["id"], event=response_id,
                         producer=attempt["session"], key=digest({"response_delivery": response_id}))
        return response["id"]

    def complete_events(self):
        """Completion includes descendants, durable handoffs and receipt outcomes."""
        with self.tx():
            changed = True
            while changed:
                self.complete_input_controls()
                cursor = self.db.execute("UPDATE events SET state='processed',processed_at=? "
                    "WHERE processed_at IS NULL AND hold IS NULL AND ack IN ('done','plain','internal') "
                    "AND NOT EXISTS (SELECT 1 FROM input_resolutions ir WHERE ir.event=events.id "
                    "AND ir.version=(SELECT MAX(v.version) FROM input_resolutions v WHERE v.event=events.id) "
                    "AND json_array_length(json_extract(ir.receipt,'$.remaining_obligations'))>0) "
                    "AND id IN (SELECT event FROM queue WHERE state='done') "
                    "AND NOT EXISTS (SELECT 1 FROM file_publications fp JOIN attempts a ON a.id=fp.attempt JOIN queue q ON q.job=a.job WHERE q.event=events.id AND fp.state!='published') "
                    "AND NOT EXISTS (SELECT 1 FROM outboxes o WHERE (o.event=events.id OR EXISTS "
                    "(SELECT 1 FROM queue q WHERE q.job=o.job AND q.event=events.id)) "
                    "AND (o.processed_at IS NULL OR o.hold IS NOT NULL OR o.state!='settled')) "
                    "AND NOT EXISTS (SELECT 1 FROM file_publications p JOIN attempts a ON a.id=p.attempt "
                    "JOIN integration_prestart_dispositions d ON d.job=a.job JOIN jobs w ON w.id=d.job,json_each(w.members) wm "
                    "WHERE json_extract(wm.value,'$.event')=events.id AND p.state!='published') "
                    "AND NOT EXISTS (SELECT 1 FROM integration_prestart_dispositions d JOIN jobs w ON w.id=d.job,json_each(w.members) wm "
                    "WHERE json_extract(wm.value,'$.event')=events.id AND EXISTS (SELECT 1 FROM attempts a WHERE a.job=w.id) "
                    "AND (w.effects NOT IN ('none','reconciled') OR EXISTS (SELECT 1 FROM attempts a WHERE a.job=w.id "
                    "AND a.cleanup NOT IN ('done','owned-ephemeral-lifecycle-observed','no-session-created')))) "
                    "AND NOT EXISTS (SELECT 1 FROM outboxes o JOIN integration_prestart_dispositions d ON d.job=o.job "
                    "JOIN jobs w ON w.id=d.job,json_each(w.members) wm "
                    "WHERE json_extract(wm.value,'$.event')=events.id "
                    "AND (o.processed_at IS NULL OR o.hold IS NOT NULL OR o.state!='settled')) "
                    "AND NOT EXISTS (SELECT 1 FROM events child WHERE child.parent=events.id "
                    "AND child.processed_at IS NULL) "
                    "AND NOT EXISTS (SELECT 1 FROM jobs j,json_each(j.members) m "
                    "WHERE json_extract(m.value,'$.event')=events.id AND "
                    "NOT EXISTS (SELECT 1 FROM integration_prestart_dispositions d WHERE d.job=j.id) AND "
                    "(j.state!='closed' OR (j.response IS NOT NULL AND NOT EXISTS "
                    "(SELECT 1 FROM events r WHERE r.id=j.response AND r.processed_at IS NOT NULL))))",
                    (self.clock(),))
                changed = cursor.rowcount > 0

    def claim_recovery(self, job):
        with self.tx():
            if self.integration_retired(job):
                return None
            row = self.job(job)
            self.require_active_sources(job=job)
            old=self.attempt(row['active_attempt'])
            no_start=old['state']=='not-started' and json.loads(old['detail']).get('known_not_started')
            if not no_start and (old['ended'] is None or old['collected'] is None):return None
            if self.one("SELECT id FROM recovery_requests WHERE job=? AND state='pending'",(job,)):return None
            if row["state"] == "closed" or row["recovery_owner"] or row["recovery_count"] >= 1:
                return None
            self.db.execute("UPDATE jobs SET recovery_owner=?,recovery_state='claimed',recovery_count=1 WHERE id=?",
                            (self.controller, job))
        return self.job(job)

    def diagnosis_attempt(self, job):
        with self.tx():
            self.require_execution_open(job)
            row = self.job(job)
            if row["recovery_owner"] != self.controller or row["recovery_state"] != "claimed":
                raise Refusal("recovery is exclusively owned or already attempted")
            selected = self.config["diagnosis"]
            attempt = self._attempt("diagnosis", None, job, selected["binding"], selected["profile"])
            detail={**json.loads(self.attempt(attempt)['detail']),'prior_task_attempt':row['active_attempt']}
            selection=self.owner_remaining_selection(job,row['active_attempt'])
            detail['owner_selection']=selection['id'] if selection else None
            self.db.execute('UPDATE attempts SET detail=? WHERE id=?',(encode(detail),attempt))
            self.db.execute("UPDATE jobs SET recovery_state='diagnosing' WHERE id=?", (job,))
        return attempt

    def handoff(self, job, diagnosis):
        with self.tx():
            return self._handoff(job,diagnosis)

    def _handoff(self,job,diagnosis,*,retained_request=None,dispatcher_continuity=False,publication_board=None):
        """Allocate once inside the caller's journal transaction, never start a model."""
        if not self.db.in_transaction:raise Refusal('handoff requires the owned journal write transaction')
        self.require_execution_open(job)
        row=self.job(job)
        old,diag=self.attempt(row['active_attempt']),self.attempt(diagnosis)
        continuity=None
        publication=None
        if retained_request:
            receipt=json.loads(retained_request['receipt'])
            if (retained_request['state']!='pending' or retained_request['job']!=job or retained_request['attempt']!=old['id']
                    or retained_request['actor']!=self.enrollment(row['role'])['owner']
                    or receipt['mode']!='use-diagnosis' or receipt['diagnosis']!=diagnosis):
                raise Refusal('exact actual-owner request and lawful original disposition collector required')
            witness=self.retained_diagnosis_witness(row,receipt,request=retained_request['id'],publication_board=publication_board)
            publication=witness.get('publication_remainder')
            if json.loads(retained_request['result'])['retained_diagnosis']!=witness:
                raise Refusal('retained qualified diagnosis/selection changed since owner reaffirmation')
            if 'collector_continuity' in receipt:
                if not dispatcher_continuity:raise Refusal('collector continuity is consumed only by the corrected actual dispatcher')
                handoff=self.transfer_retained_closure(row,old,retained_request)
                row=self.job(job)
                after=self.retained_diagnosis_witness(row,receipt,request=retained_request['id'],publication_board=publication_board)
                if {k:v for k,v in witness.items() if k!='closure_hash'}!={k:v for k,v in after.items() if k!='closure_hash'}:
                    raise Refusal('qualified currentness changed during authorized closure transfer')
                continuity={'before_witness':witness,'after_witness':after,'handoff':handoff}
            if not self.owns_disposition(row,old):raise Refusal('exact lawful disposition collector required; no automatic foreign adoption')
        elif row['recovery_owner']!=self.controller or row['recovery_state']!='diagnosing':
            raise Refusal('recovery fence differs')
        selected=self.current_diagnosis(row)
        if not selected or selected['id']!=diagnosis:raise Refusal('only current diagnosis can authorize handoff; no stale/pending substitution')
        proved_no_start=old['state']=='not-started' and old['begin'] is None and json.loads(old['detail']).get('known_not_started')
        if (not proved_no_start and (old['ended'] is None or not old['collected'])) or row['effects'] not in {'none','reconciled'}:
            raise Refusal('unknown original liveness/effects prohibit replacement')
        if not json.loads(old['detail']).get('resume_disposition'):
            raise Refusal('supported same-session resume must be attempted or explicitly unavailable first')
        choice=self.diagnosis_choice(row,diag)
        task=self.config['tasks'][row['task']]
        selection=self.owner_remaining_selection(job,old['id'])
        if old['semantic']=='DONE' and not selection:
            raise Refusal('collected DONE needs disposition; completed work cannot be blindly relaunched')
        if publication is None:
            if selection:self.remaining_work_fence(row,old)
            self.require_recoverable_hold(row,old)
        attempt=self._attempt('task',None,job,task['binding'],choice['profile'])
        context={'prior_attempt':old['id'],'prior_session':old['session'],'prior_result':old['result'],
                 'prior_error':old['error'],'prior_job_hold':row['hold_reason'],'effect_receipt':row['effect_receipt'],
                 'choice':choice,'diagnosis':diagnosis,'native_resume':False,
                 'owner_remaining_selection':selection,'prior_artifact_witnesses':witnesses(self,old['id'])}
        window = self.integration_context(job)
        if window is not None:context['integration_window'] = window
        if retained_request:context['retained_diagnosis_request']=retained_request
        if publication is not None:context['publication_remainder']=publication
        if continuity:context['collector_continuity']=continuity
        context={**json.loads(self.attempt(attempt)['detail']),**context}
        self.db.execute('UPDATE attempts SET detail=? WHERE id=?',(encode(context),attempt))
        self.db.execute("UPDATE jobs SET active_attempt=?,controller=?,effects='unknown',state='running',"
                        "recovery_state='handed-off',hold_reason=NULL WHERE id=?",(attempt,self.controller,job))
        return attempt

    def set_hold(self, event, reason):
        with self.tx():
            self.db.execute("UPDATE events SET processed_at=CASE WHEN hold IS NOT NULL AND ? IS NULL "
                            "AND processed_at IS NOT NULL THEN ? ELSE processed_at END,hold=? WHERE id=?",
                            (reason, self.clock(), reason, event))

    def hold_job(self, job, reason):
        with self.tx():
            self.db.execute("UPDATE jobs SET state='held',hold_reason=? WHERE id=? AND state!='closed' AND controller=?",
                            (str(reason)[:2000], job, self.controller))

    def adopt_collected(self, job):
        """Transfer closure work only, never an active process handle or unknown attempt."""
        with self.tx():
            self.require_execution_open(job)
            row = self.job(job)
            attempt = self.attempt(row["active_attempt"])
            task = self.config["tasks"][row["task"]]
            if row["state"] == "closed" or row["recovery_owner"] and row['recovery_state']!='awaiting-disposition':
                raise Refusal("closed/recovering reservation cannot transfer collection closure")
            if row['recovery_owner']:
                diag=self.current_diagnosis(row)
                no_start=diag and diag['state']=='not-started' and json.loads(diag['detail']).get('known_not_started')
                if not diag or diag['collected'] is None or diag['ended'] is None and not no_start:
                    raise Refusal('unknown recovery diagnosis prevents closure transfer')
            if attempt["ended"] is None or not attempt["collected"]:
                raise Refusal("unknown/live original cannot transfer closure")
            if task["effects"] == "owner-reconcile" and row["effects"] != "reconciled":
                raise Refusal("actual external effect owner must reconcile before closure transfer")
            receipt = {"from_controller": row["controller"], "to_controller": self.controller,
                       "original_collector": attempt["controller"], "original_attempt": attempt["id"],
                       "actual_exit": attempt["exit"], "actual_collected_at": attempt["collected"],
                       "authority": "same enrolled automation; collected closure only, no process adoption"}
            self.db.execute("UPDATE jobs SET controller=?,collection_handoff=? WHERE id=?",
                            (self.controller, encode(receipt), job))

    def violations(self):
        now, d = self.clock(), self.config["deadlines"]
        alerts = []
        alerts += [{'subject':r['attempt'],'kind':'opaque-storage-ownership-hold','cause':r['error']}
                   for r in self.rows('SELECT attempt,error FROM attempt_storage WHERE error IS NOT NULL AND removed IS NULL')]
        alerts += [{"subject": r["subject"], "kind": r["kind"], "role": r["role"], "cause": json.loads(r["detail"])}
                   for r in self.rows("SELECT * FROM operational_errors WHERE active=1")]
        alerts += [{"subject": r["id"], "kind": "ack-lag", "age": now-r["received"]} for r in
                   self.rows("SELECT * FROM events WHERE ack NOT IN ('done','plain','internal')") if now-r["received"] > d["ack"]]
        alerts += [{"subject": r["id"], "kind": "backlog", "age": now-r["received"]} for r in
                   self.rows("SELECT * FROM events WHERE processed_at IS NULL") if now-r["received"] > d["backlog"]]
        alerts += [self._attempt_violation(r, now, d) for r in self.rows("SELECT * FROM attempts")]
        alerts += [{"subject": r["id"], "kind": "slot-held", "reason": r["hold_reason"]} for r in
                   self.rows("SELECT * FROM jobs WHERE state='held'")]
        alerts += [{"subject": r["role"], "kind": "legacy-hold", "reason": r["legacy_hold"]} for r in
                   self.rows("SELECT * FROM enrollments WHERE legacy_hold IS NOT NULL")]
        return [a for a in alerts if a]

    def _attempt_violation(self, row, now, d):
        job = self.one("SELECT state,active_attempt FROM jobs WHERE id=?", (row["job"],)) if row["job"] else None
        observed = row["cleanup"] in {"done", "owned-ephemeral-lifecycle-observed", "no-session-created"}
        if job and (job["state"] == "closed" or job["active_attempt"] != row["id"]) and observed:
            return None
        if row["state"] == "reserved" and now-row["created"] > d["bind"]:
            return {"subject": row["id"], "kind": "launch-bind-unknown"}
        if row["begin"] and row["ended"] is None and now-row["begin"] > d["task"]:
            return {"subject": row["id"], "kind": "live-or-unknown-timeout"}
        if row["ended"] and row["semantic"] != "DONE" and row["kind"] == "task":
            return {"subject": row["id"], "kind": "ended-not-DONE", "error": row["error"]}
        if row["ended"] and not observed:
            return {"subject": row["id"], "kind": "cleanup-hold", "cleanup": row["cleanup"]}
        return None

    def emit_alerts(self):
        emitted = capacity.capture(self)
        capacity.deliver_pending(self)
        return emitted

    def process_alert(self, occurrence, actor, receipt):
        if actor not in {r["owner"] for r in self.config["roles"].values()} or not receipt:
            raise Refusal("actual enrolled consumer and processing receipt required")
        with self.tx():
            row = self.one("SELECT payload FROM alerts WHERE id=?", (occurrence,))
            if not row:
                raise Refusal("unknown alert occurrence")
            payload = {**json.loads(row["payload"]), "consumer": actor, "processing_receipt": receipt}
            self.db.execute("UPDATE alerts SET payload=?,processed_at=COALESCE(processed_at,?) WHERE id=?",
                            (encode(payload), self.clock(), occurrence))

    def status(self):
        return {"controller": self.controller, "usage": self.usage(),
                'execution_pool': self.execution_pool.status(),
                "enrollments": self.rows("SELECT * FROM enrollments"),
                "events": self.rows("SELECT id,role,state,ack,received,processed_at,hold,error FROM events"),
                "slots": [{**job, "execution_slot_held": not self.execution_complete(job)}
                          for job in self.rows("SELECT * FROM jobs WHERE state!='closed'")],
                "attempts": self.rows("SELECT id,kind,job,controller,profile,binding,state,begin,ended,exit,"
                                      "collected,session,semantic,capture,cleanup,error,detail FROM attempts"),
                "outboxes": self.rows("SELECT id,role,job,event,recipient,kind,required,state,hold,error,created,processed_at FROM outboxes"),
                "control_receive": {'declared':self.config.get('control_receive',{}),
                    'availability':'cooperative genuine existing owner receive points only; configuration/posts do not prove active receive or native wake'},
                "alert_service": capacity.service(self),
                "admitted_duty_accounts": self.rows('SELECT * FROM duty_accounts'),
                "admitted_count_credits": admitted.reserved(self),
                "allocation_window": windows.current(self) if self.config.get('window_service') else None,
                "custodian_progress": self.one("SELECT value FROM meta WHERE key='custodian-progress'"),
                "pending_alert_deliveries": self.one('SELECT COUNT(*) AS count FROM alerts a WHERE NOT EXISTS (SELECT 1 FROM outboxes o WHERE o.alert=a.id)'),
                "operational_errors": self.rows("SELECT * FROM operational_errors WHERE active=1"),
                "recovery_requests":self.rows('SELECT * FROM recovery_requests'),
                "recovery_dispositions":self.rows('SELECT * FROM recovery_dispositions'),
                "integration_retirements":self.rows('SELECT * FROM integration_retirements'),
                "integration_windows":self.rows('SELECT * FROM integration_windows'),
                "input_resolutions":self.rows('SELECT event,version,source_hash,actor,receipt,created FROM input_resolutions'),
                "source_custody": self.rows("SELECT event,basis,owner FROM source_custody"),
                "artifact_custody": [{**r,'source_context':r['attempt'],'attempt':None if r['attempt'].startswith('owner:') else r['attempt']}
                                     for r in self.rows('SELECT attempt,path,kind,owner,sha256 FROM artifact_custody')],
                "session_storage": self.rows('SELECT * FROM attempt_storage'),
                "file_publications": self.rows('SELECT * FROM file_publications'),
                "canonical_backups": self.rows('SELECT * FROM canonical_backups'),
                "violations": self.violations(), "adoption": "prospective grants only; no model/goal acceptance"}
