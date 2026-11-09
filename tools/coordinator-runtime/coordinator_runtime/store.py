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
                        response_tasks, collected_task_result, collected_capture, handback_binding, handback_receipt)
from .delivery import DeliveryJournal, SCHEMA as DELIVERY_SCHEMA
from .custody import SCHEMA as CUSTODY_SCHEMA, witnesses
from .routine import SCHEMA as ROUTINE_SCHEMA
from .storage import SCHEMA as STORAGE_SCHEMA
from . import oneoff
from .publication import SCHEMA as PUBLICATION_SCHEMA
from .recovery import RecoveryJournal, SCHEMA as RECOVERY_SCHEMA
from .inputs import InputJournal, CONTROL_ROUTES, SCHEMA as INPUT_SCHEMA
from .execution_pool import ExecutionPool
from .integration import IntegrationJournal, SCHEMA as INTEGRATION_SCHEMA
from . import prospective, ordinary, capacity, admitted, windows, custodian_service, configuration, ref_scope, local_integration

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
CREATE TABLE IF NOT EXISTS artifact_placement_admissions(
 id TEXT PRIMARY KEY,selection TEXT NOT NULL,configuration TEXT NOT NULL,actor TEXT NOT NULL,created REAL NOT NULL);
CREATE TABLE IF NOT EXISTS attempt_artifact_roots(
 attempt TEXT PRIMARY KEY REFERENCES attempts(id),admission TEXT NOT NULL REFERENCES artifact_placement_admissions(id),
 root TEXT NOT NULL UNIQUE);
CREATE TRIGGER IF NOT EXISTS artifact_placement_admissions_no_update BEFORE UPDATE ON artifact_placement_admissions
 BEGIN SELECT RAISE(ABORT,'immutable original artifact placement'); END;
CREATE TRIGGER IF NOT EXISTS artifact_placement_admissions_no_delete BEFORE DELETE ON artifact_placement_admissions
 BEGIN SELECT RAISE(ABORT,'immutable original artifact placement'); END;
CREATE TRIGGER IF NOT EXISTS attempt_artifact_roots_no_update BEFORE UPDATE ON attempt_artifact_roots
 BEGIN SELECT RAISE(ABORT,'immutable original artifact placement'); END;
CREATE TABLE IF NOT EXISTS retired_attempt_artifact_roots(
 attempt TEXT PRIMARY KEY,admission TEXT NOT NULL REFERENCES artifact_placement_admissions(id),
 root TEXT NOT NULL UNIQUE,retirement TEXT NOT NULL);
CREATE TRIGGER IF NOT EXISTS retired_attempt_artifact_roots_no_update BEFORE UPDATE ON retired_attempt_artifact_roots
 BEGIN SELECT RAISE(ABORT,'immutable retired artifact identity'); END;
CREATE TRIGGER IF NOT EXISTS retired_attempt_artifact_roots_no_delete BEFORE DELETE ON retired_attempt_artifact_roots
 BEGIN SELECT RAISE(ABORT,'immutable retired artifact identity'); END;
CREATE TRIGGER IF NOT EXISTS attempt_artifact_roots_no_reuse BEFORE INSERT ON attempt_artifact_roots
 WHEN EXISTS(SELECT 1 FROM retired_attempt_artifact_roots WHERE attempt=NEW.attempt OR root=NEW.root)
 BEGIN SELECT RAISE(ABORT,'retired artifact identity cannot be reused'); END;
DROP TRIGGER IF EXISTS attempt_artifact_roots_no_delete;
CREATE TRIGGER attempt_artifact_roots_no_delete BEFORE DELETE ON attempt_artifact_roots
 WHEN NOT EXISTS(SELECT 1 FROM retired_attempt_artifact_roots
                 WHERE attempt=OLD.attempt AND admission=OLD.admission AND root=OLD.root)
 BEGIN SELECT RAISE(ABORT,'immutable original artifact placement'); END;
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

CREATE TABLE IF NOT EXISTS reservation_outcomes(
 event TEXT PRIMARY KEY,source_hash TEXT NOT NULL,queue TEXT NOT NULL,
 task TEXT NOT NULL,phase TEXT NOT NULL,capability TEXT,controller TEXT NOT NULL,
 mapping_version INTEGER NOT NULL,observed REAL NOT NULL,
 schema_version INTEGER NOT NULL,outcome TEXT NOT NULL,predicate TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS reservation_conflicts(
 event TEXT PRIMARY KEY,observation TEXT NOT NULL,schema_version INTEGER NOT NULL,
 job TEXT NOT NULL,arm TEXT NOT NULL);
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
    def __init__(self, config, controller=None, clock=time.time, *, read_only=False):
        self.config, self.controller, self.clock = config, controller or ident(), clock
        self.launch_authorizer = None
        self.task_launch_authorizer = None
        self.processing = None  # Explicit service-local capability, never an intake flag rewrite.
        self.execution_pool = ExecutionPool(config, runtime=self)
        self.home = Path(config["state_dir"]) if read_only else private_directory(config["state_dir"])
        self.path = self.home / "runtime.sqlite3"
        if read_only:
            self._open_control_view()
            return
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
        from .plain_control import accepted
        self.db.create_function("plain_control_valid",1,lambda event:int(bool(self.processing) and accepted(self,event)))
        self.db.execute("PRAGMA foreign_keys=ON")
        version = self.db.execute("PRAGMA user_version").fetchone()[0]
        if version not in {0, 1}:
            raise Refusal("unsupported runtime schema; offline owned migration required")
        if version == 0 and self.db.execute("SELECT 1 FROM sqlite_master WHERE type='table'").fetchone():
            raise Refusal("unversioned existing runtime cannot be silently adopted")
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        local_integration.policy(config)
        admitted.policy(config)
        windows.policy(config)
        custodian_service.policy(config)
        self.db.executescript(SCHEMA + DELIVERY_SCHEMA + CUSTODY_SCHEMA + ROUTINE_SCHEMA + STORAGE_SCHEMA + oneoff.SCHEMA + PUBLICATION_SCHEMA + RECOVERY_SCHEMA + INPUT_SCHEMA + INTEGRATION_SCHEMA + prospective.SCHEMA + ordinary.SCHEMA + capacity.SCHEMA + admitted.SCHEMA + windows.SCHEMA + custodian_service.SCHEMA)
        self.db.execute("PRAGMA user_version=1")
        self.db.executescript(configuration.SCHEMA + ref_scope.SCHEMA + local_integration.SCHEMA)
        from .metadata_lookup import SCHEMA as LOOKUP_SCHEMA
        self.db.executescript(LOOKUP_SCHEMA)
        self._bind_config()
        from .processing import SCHEMA as PROCESSING_SCHEMA
        self.db.executescript(PROCESSING_SCHEMA)
        from .historical_verification import SCHEMA as HISTORICAL_METADATA_SCHEMA
        self.db.executescript(HISTORICAL_METADATA_SCHEMA)
        from .processing import migrate_links
        migrate_links(self)
        from .reviews import SCHEMA as REVIEW_SCHEMA
        from .service import SCHEMA as SERVICE_SCHEMA
        from .review_returns import SCHEMA as REPORT_RETURN_SCHEMA
        from .report_repair import SCHEMA as REPORT_REPAIR_SCHEMA
        from .branches import SCHEMA as BRANCH_SCHEMA
        from .service_recovery import SCHEMA as SERVICE_RECOVERY_SCHEMA
        self.db.executescript(REVIEW_SCHEMA + SERVICE_SCHEMA + BRANCH_SCHEMA + SERVICE_RECOVERY_SCHEMA + REPORT_RETURN_SCHEMA + REPORT_REPAIR_SCHEMA)
        self.db.execute('CREATE TABLE IF NOT EXISTS shared_custody_intents(delivery TEXT PRIMARY KEY,archive TEXT NOT NULL,basis TEXT NOT NULL,state TEXT NOT NULL,receipt TEXT)')
        windows.prepare_revision(self)

    def _open_control_view(self):
        """Existing journal only: control must never initialize or migrate it.

        A WAL reader can validate the committed capability while another
        connection owns a write transaction. No BEGIN IMMEDIATE/configuration
        binding write is needed before addressing the original service socket.
        """
        from .contracts import regular_path
        info = regular_path(str(self.path)).stat()
        if info.st_nlink != 1 or info.st_mode & 0o077 or self.home.stat().st_mode & 0o077:
            raise Refusal("private single-link runtime database required")
        self.db = sqlite3.connect(self.path.as_uri()+"?mode=ro", uri=True, isolation_level=None, timeout=15)
        self.db.row_factory = sqlite3.Row
        from .plain_control import accepted
        self.db.create_function("plain_control_valid",1,lambda event:int(bool(self.processing) and accepted(self,event)))
        try:
            self.db.execute('PRAGMA query_only=ON')
            if self.db.execute('PRAGMA user_version').fetchone()[0] != 1:
                raise Refusal('service control requires an initialized runtime schema')
            if not self.one("SELECT value FROM meta WHERE key='configuration'"):
                raise Refusal('service control requires an existing configuration binding')
            self._check_config()
        except BaseException:
            self.db.close()
            raise

    def _check_config(self):
        row = self.one("SELECT value FROM meta WHERE key='configuration'")
        current = configuration.current_binding(self)
        if row and (current['current'] if current else row['value']) != digest(self.config):
            raise Refusal("configuration differs from this journal; use the supported current-configuration transition")
        if current and (current['original'] != row['value'] or json.loads(current['configuration']) != self.config):
            raise Refusal('current configuration/original journal binding differs')

    def _bind_config(self):
        with self.tx():
            self._check_config()
            expected = digest(self.config)
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
                self.require_attempt_execution_open(collection)
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

    def artifact_root(self, attempt):
        # Missing mapping means LEGACY forever, including pre-admission attempts.
        row = self.one('SELECT r.root,a.selection FROM attempt_artifact_roots r '
                       'JOIN artifact_placement_admissions a ON a.id=r.admission WHERE r.attempt=? '
                       'UNION ALL SELECT r.root,a.selection FROM retired_attempt_artifact_roots r '
                       'JOIN artifact_placement_admissions a ON a.id=r.admission WHERE r.attempt=?', (attempt, attempt))
        root = Path(row['root']) if row else self.home/'artifacts'/attempt
        if row and root != Path(json.loads(row['selection'])['root'])/attempt:
            raise Refusal('original artifact mapping changed; retain original custody')
        from .custody import guard_path
        guard_path(self, str(root))
        return root

    def prospective_artifact_parent(self):
        row = self.one('SELECT selection FROM artifact_placement_admissions ORDER BY rowid DESC LIMIT 1')
        return Path(json.loads(row['selection'])['root']) if row else self.home/'artifacts'

    def select_artifact_placement(self, actor, selection):
        """Explicit operator admission for NEW attempts only, never a migration.

        The caller supplies actual rights and finite physical ceilings. The CLI
        authenticates the current Work principal; no model can select storage.
        A root created before a later journal failure remains owned/held.
        """
        from .custody import guard_path
        required = {'root', 'authority', 'expires', 'max_attempts', 'max_entries', 'max_bytes',
                    'min_free_bytes', 'min_free_inodes', 'journal_min_free_bytes', 'journal_min_free_inodes'}
        if not isinstance(selection, dict) or set(selection) != required:
            raise Refusal('exact finite future artifact admission required')
        if actor != self.enrollment('Work')['owner'] or actor != self.config['roles']['Work']['owner']:
            raise Refusal('future placement belongs to genuine current Work')
        if not isinstance(selection['authority'], str) or not selection['authority'].strip():
            raise Refusal('actual storage authority evidence required')
        for key in required - {'root', 'authority', 'expires'}:
            if type(selection[key]) is not int or selection[key] <= 0:
                raise Refusal('positive finite placement bounds required')
        if type(selection['expires']) not in (int, float) or not self.clock() < selection['expires'] < self.clock()+86400:
            raise Refusal('finite current placement admission required')
        root = Path(selection['root'])
        # Match the existing lexical resource boundary before ANY metadata.
        if (not root.is_absolute() or root.anchor == '//' or '..' in root.parts
                or str(root) != selection['root']):
            raise Refusal('independent new plain artifact root required')
        from .resource_scopes import root as resource_root
        resource_root(selection['root'], self.config.get('artifact_exclusions', []), metadata=False)
        guard_path(self, str(root))  # lexical exclusions/origins BEFORE metadata
        if any(Path(p).is_relative_to(root) for p in self.config.get('artifact_exclusions', [])):
            raise Refusal('future arena contains an opaque namespace; no acquisition')
        if (not root.is_absolute() or '..' in root.parts or str(root) != selection['root'] or
                root.is_relative_to(self.home) or self.home.is_relative_to(root)):
            raise Refusal('independent new plain artifact root required')
        if any(p.is_symlink() for p in (root, *root.parents)) or root.exists():
            raise Refusal('fresh root without aliases required; existing objects never retargeted')
        self.placement_headroom(root.parent, selection, selection['max_bytes'], selection['max_entries'])
        self.placement_headroom(self.home, {'min_free_bytes': selection['journal_min_free_bytes'],
                                            'min_free_inodes': selection['journal_min_free_inodes']}, 8192, 1)
        with self.tx():
            self.budget(None, 8192)
            # No overlap with any prior admitted arena, even after its expiry.
            for row in self.rows('SELECT selection FROM artifact_placement_admissions'):
                old = Path(json.loads(row['selection'])['root'])
                if root.is_relative_to(old) or old.is_relative_to(root):
                    raise Refusal('prior placement identity/path meaning conserved')
            key = ident()
            root.mkdir(mode=0o700, exist_ok=False)
            self.db.execute('INSERT INTO artifact_placement_admissions VALUES(?,?,?,?,?)',
                            (key, encode(selection), digest(self.config), actor, self.clock()))
        return {'admission': key, 'journal': str(self.path), 'future_only': True, 'selection': selection}

    @staticmethod
    def placement_headroom(root, selection, incoming=0, entries=0):
        v = os.statvfs(root)
        if (v.f_bavail*v.f_frsize < selection['min_free_bytes']+incoming or
                v.f_favail < selection['min_free_inodes']+entries):
            raise Backpressure('future artifact allocation headroom lost; no fallback')

    def placement_usage(self, incoming=0, *, admission=None, entries=0, journal_incoming=0):
        from .custody import guard_path
        result, sites = [], []
        if incoming and admission is None:
            raise Refusal('incoming artifact allocation needs its exact destination')
        for row in self.rows('SELECT id,selection FROM artifact_placement_admissions ORDER BY rowid'):
            spec = json.loads(row['selection']); root = Path(spec['root'])
            growth = incoming if row['id'] == admission else 0
            new_entries = entries if row['id'] == admission else 0
            guard_path(self, str(root))
            if any(Path(p).is_relative_to(root) for p in self.config.get('artifact_exclusions', [])):
                raise Refusal('artifact arena contains an opaque namespace; no enumeration')
            if any(p.is_symlink() for p in (root, *root.parents)):
                raise Refusal('admitted artifact arena became an alias')
            pending, count, total = [root], 0, 0
            device = None
            while pending:
                path = pending.pop()
                guard_path(self, str(path))
                info = path.lstat()
                if path == root:
                    device = info.st_dev
                if info.st_uid != os.getuid() or stat.S_ISLNK(info.st_mode):
                    raise Refusal('foreign/aliased artifact entry; keep without traversal')
                count += 1; total += info.st_size
                if count+new_entries > spec['max_entries'] or total+growth > spec['max_bytes']:
                    raise Backpressure('cumulative future artifact admission exhausted; no fallback')
                if stat.S_ISDIR(info.st_mode):
                    pending.extend(path.iterdir())
            sites.append((row['id'], root, spec, device))
            result.append(dict(admission=row['id'], root=str(root), entries=count, bytes=total))
        if admission is not None and not any(key == admission for key, _, _, _ in sites):
            raise Refusal('incoming artifact destination is not admitted')
        destination = next((dev for key, _, _, dev in sites if key == admission), None)
        journal_device = self.home.lstat().st_dev if sites else None
        # Logical arena ceilings follow the actual destination. Physical free
        # space is shared by allocations on the same device, including journal
        # growth; preserve every applicable site floor before those writes.
        for _, root, spec, device in sites:
            physical_bytes = (incoming if device == destination else 0) + (journal_incoming if device == journal_device else 0)
            physical_entries = (entries if device == destination else 0) + int(journal_incoming > 0 and device == journal_device)
            self.placement_headroom(root, spec, physical_bytes, physical_entries)
            self.placement_headroom(self.home, {'min_free_bytes': spec['journal_min_free_bytes'],
                                                'min_free_inodes': spec['journal_min_free_inodes']},
                                    journal_incoming + (incoming if destination == journal_device else 0),
                                    int(journal_incoming > 0) + (entries if destination == journal_device else 0))
        return result

    def admit_artifact_write(self, attempt, incoming, entries, *, journal_incoming=0):
        row = self.one('SELECT a.id,a.selection FROM attempt_artifact_roots r '
                       'JOIN artifact_placement_admissions a ON a.id=r.admission WHERE r.attempt=?', (attempt,))
        if not row:
            return  # Legacy behavior and original home remain unchanged.
        spec = json.loads(row['selection'])
        usage = next(p for p in self.placement_usage(incoming, admission=row['id'], entries=entries, journal_incoming=journal_incoming) if p['admission'] == row['id'])
        if self.usage()['bytes']+incoming+journal_incoming+capacity.PRESSURE_RESERVE >= self.config['limits']['max_bytes']:
            raise Backpressure('cumulative journal/artifact bytes held; conserve before admitting more')
        if usage['entries']+entries > spec['max_entries']:
            raise Backpressure('future artifact entry admission exhausted; no fallback')
        self.placement_headroom(Path(spec['root']), spec, incoming, entries)

    def artifact_copy_budget(self, attempt, path, incoming, *, journal_incoming=1024, directory=False):
        """Admit a cooperative copy at its frozen destination before mkdir/open.

        Filesystem bytes and journal records have different allocation sites.
        Count missing directory inodes as well as the new file, including a
        directory-growth allowance. This is preflight, never a reservation.
        """
        from .custody import guard_path
        path = Path(path)
        root = self.artifact_root(attempt)
        if (not path.is_absolute() or '..' in path.parts or not path.is_relative_to(root)
                or type(incoming) is not int or incoming < 0
                or type(journal_incoming) is not int or journal_incoming < 0):
            raise Refusal('exact artifact copy destination and nonnegative sizes required')
        guard_path(self, str(path))
        if any(p.is_symlink() for p in (path, *path.parents)):
            raise Refusal('artifact copy alias refused before allocation')
        missing = 0
        parent = path if directory else path.parent
        while parent.is_relative_to(root) and not parent.exists():
            guard_path(self, str(parent))
            missing += 1
            parent = parent.parent
        entries = missing + int(not directory)
        growth = incoming + 4096 * (missing + int(not directory))
        # One transaction carries software/current authority and activation;
        # the subsequent filesystem effect retains its original custody.
        with (nullcontext() if self.db.in_transaction else self.tx()):
            if self.one('SELECT attempt FROM attempt_artifact_roots WHERE attempt=?', (attempt,)):
                self.budget(None, growth+journal_incoming, artifact_incoming=growth,
                            artifact_attempt=attempt, artifact_entries=entries)
            else:
                # Legacy copies really grow the journal's own filesystem.
                self.budget(None, growth+journal_incoming)

    def bind_artifact_root(self, attempt):
        row = self.one('SELECT * FROM artifact_placement_admissions ORDER BY rowid DESC LIMIT 1')
        if not row:
            return
        spec = json.loads(row['selection'])
        if row['configuration'] != digest(self.config) or self.clock() >= spec['expires']:
            raise Refusal('future artifact admission expired/changed; no fallback')
        count = sum(self.one(f'SELECT COUNT(*) n FROM {table} WHERE admission=?', (row['id'],))['n']
                    for table in ('attempt_artifact_roots', 'retired_attempt_artifact_roots'))
        if count >= spec['max_attempts']:
            raise Backpressure('future artifact attempt admission exhausted; no fallback')
        self.placement_usage(4096, admission=row['id'])
        self.db.execute('INSERT INTO attempt_artifact_roots VALUES(?,?,?)',
                        (attempt, row['id'], str(Path(spec['root'])/attempt)))

    def usage(self):
        counts = {name: self.db.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
                  for name in ("events", "attempts", "jobs", "alerts", "outboxes")}
        counts["bytes"] = owned_bytes(self.home, self.config["limits"].get("max_files", 50000))
        counts['artifact_placements'] = self.placement_usage()
        counts['bytes'] += sum(p['bytes'] for p in counts['artifact_placements'])
        # Reserve a configured maximum per possible publication. Never measure
        # retained blob bodies (or probe their keys/presence) for admission.
        counts['publication_reserved_bytes'] = self.db.execute("SELECT COUNT(*) FROM file_publications WHERE state!='published'").fetchone()[0] * min(self.config['limits'].get('max_artifact_bytes', 33554432), self.config['limits']['max_bytes'])
        counts['bytes']+=counts['publication_reserved_bytes']
        counts['custodian_reserved_bytes'] = self.one(
            "SELECT COUNT(*) AS n FROM custodian_visits WHERE state IN ('prepared','running')")['n'] * (3 * custodian_service.CAPTURE + 4096)
        counts['bytes'] += counts['custodian_reserved_bytes']
        counts['oneoff_recovery_reserved_bytes'] = oneoff.reserved_bytes(self)
        counts['bytes'] += counts['oneoff_recovery_reserved_bytes']
        counts['excluded_codex_store_scope'] = 'sessions subtree opaque/unmeasured; shared account stores not inventoried'
        return counts

    def budget(self, kind, incoming=0, *, event=None, job=None, artifact_incoming=0, artifact_attempt=None, artifact_entries=0):
        if (type(artifact_incoming) is not int or not 0 <= artifact_incoming <= incoming
                or type(artifact_entries) is not int or artifact_entries < 0
                or artifact_attempt is None and (artifact_incoming or artifact_entries)):
            raise Refusal('artifact allocation needs nonnegative sizes and its exact destination')
        if artifact_attempt is not None and not self.one(
                'SELECT attempt FROM attempt_artifact_roots WHERE attempt=?', (artifact_attempt,)):
            raise Refusal('incoming artifact destination is not admitted')
        journal_incoming = incoming - artifact_incoming
        # File-copy/staging callers have no enclosing journal write. Authenticate
        # and commit only their budget/activation here; the later filesystem
        # effect retains its existing custody and is not journal-atomic.
        if kind is None and not event and not job and not self.db.in_transaction:
            with self.tx():
                return self.budget(kind, incoming, artifact_incoming=artifact_incoming,
                                   artifact_attempt=artifact_attempt, artifact_entries=artifact_entries)
        from .report_repair import software_budget
        activation = software_budget(self, kind, incoming)
        if activation:
            incoming += 1024  # Real writable activation custody, never a read/start.
            journal_incoming += 1024
        if event or job:
            if not self.db.in_transaction:
                raise Refusal('duty credit allocation requires the source write transaction')
            admitted.charge(self, kind, event=event, job=job)
        if artifact_attempt is not None:
            self.admit_artifact_write(artifact_attempt, artifact_incoming, artifact_entries,
                                      journal_incoming=journal_incoming)
        else:
            self.placement_usage(journal_incoming=journal_incoming)
        usage, limits = self.usage(), self.config["limits"]
        if usage["bytes"] + incoming + capacity.PRESSURE_RESERVE >= limits["max_bytes"]:
            raise Backpressure("cumulative journal/artifact bytes held; conserve before admitting more")
        # Publish activation custody before window accounting can recurse into
        # budget(None). Both writes roll back with the original allocation.
        if activation:
            self.db.execute('INSERT INTO future_software_activations_v1 VALUES(?,?,?,?,?)', activation)
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
            from .report_scope import validate_large_event
            if not validate_large_event(self, event):
                raise Backpressure("event body exceeds per-message bound; upstream retains it unACKed")
        with self.tx():
            old = self.one("SELECT hash FROM events WHERE id=?", (event["id"],))
            if old and old["hash"] != digest(event):
                raise Refusal("same event identity has different immutable content")
            if not old:
                from .report_repair import software_input
                owed_control = bool(self.processing and event.get('kind') == 'board'
                                    and self.processing.owed_control(event))
                software_input(self, event, owed_control=owed_control)
                if self.processing and event.get('kind') == 'board' and not owed_control:
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
        from .report_repair import software_start
        software_start(self)
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
        self.bind_artifact_root(attempt)
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

    def _classification_current(self, attempt):
        # Called inside the current cooperative write transaction. A reservation
        # is not continuing permission to acquire/disclose a subsequently held
        # source, or to commit its answer after source responsibility changes.
        scope, parameters = configuration.event_candidate_scope(self)
        source = self.one('SELECT e.hold IS NOT NULL AS held,e.state,e.classifier,e.processed_at '
                          'FROM events e WHERE e.id=? AND (' + scope + ')',
                          (attempt['event'], *parameters))
        if (not source or source['held'] or source['processed_at'] is not None
                or source['state'] != 'classifying' or source['classifier'] != attempt['id']):
            raise Refusal('classification source held/excluded or no longer current')
        if self.processing and not self.processing.event(self.event(attempt['event'])):
            raise Refusal('classification source outside current processing selection')

    def authorize_preparation(self, attempt):
        """Fresh source admission before prior-result/context acquisition."""
        with (nullcontext() if self.db.in_transaction else self.tx()):
            row = self.one('SELECT id,job,event,kind FROM attempts WHERE id=?', (attempt,))
            if not row:
                raise Refusal('attempt not owned by this journal')
            if row['job']:
                from .native_review_scope import admit
                admit(self, self.job(row['job']))
                local_integration.current_sources(self, self.job(row['job']))
            elif row['kind'] in {'classifier', 'diagnosis'}:
                self._classification_current(row)

    def authorize_launch(self, attempt):
        self.require_attempt_execution_open(attempt)
        with (nullcontext() if self.db.in_transaction else self.tx()):
            self.require_attempt_execution_open(attempt)
            self.authorize_preparation(attempt)
            row = self.attempt(attempt)
            if self.processing:
                self.processing.authorize(row)
            if row['kind'] in {'input-mapping', 'input-locator'}:
                from .metadata_lookup import authorize
                authorize(self, row)
            if row['job']:
                self.require_execution_open(row['job'])
            self.require_active_sources(row["event"], row["job"])
            if self.launch_authorizer:
                self.launch_authorizer(self.source_roles(row["event"], row["job"]))
            if row['kind'] != 'task':
                return
            job = self.job(row['job'])
            self.integration_launch_current(job)
            local_integration.current_job(self, job)
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
            scope, parameters = configuration.event_candidate_scope(self)
            candidates = self.rows("SELECT e.id,e.role FROM events e WHERE e.state='received' AND e.hold IS NULL AND (" +
                                   scope + ") ORDER BY e.received,e.id", parameters)
            row = None
            for candidate in candidates:
                if not self.role_enabled(candidate['role']) or self.processing and not self.processing.event(self.event(candidate['id'])):
                    continue
                try:
                    event = self.routing_event(candidate['id'])
                except Refusal as exc:
                    # An owned mapping dependency is distinct from an unknown
                    # launch. Preserve prior classifiers and let unrelated
                    # sources progress, without repeatedly allocating/failing.
                    self.db.execute("UPDATE events SET state='mapping-held',error=? WHERE id=?", (str(exc)[:2000], candidate['id']))
                    self.db.execute("UPDATE queue SET state='owner-resolution-pending' WHERE event=? AND job IS NULL", (candidate['id'],))
                    self.db.execute('INSERT INTO operational_errors VALUES(?,?,?,?,1,?) ON CONFLICT(subject) '
                                    'DO UPDATE SET detail=excluded.detail,active=1,observed=excluded.observed',
                                    (candidate['id'],candidate['role'],'input-mapping-dependency',encode({'dependency':str(exc)}),self.clock()))
                    continue
                row = candidate
                break
            if row is None:
                return None
            # Resolve mutable receiver bindings BEFORE any durable reservation
            # or pool allocation. A refusal has no launched/unknown attempt to
            # settle and the original remains available for genuine remapping.
            selected = self.config["classifier"]
            attempt = self._attempt("classifier", row["id"], None, selected["binding"], selected["profile"])
            self.db.execute("UPDATE events SET state='classifying',classifier=? WHERE id=?", (attempt, row["id"]))
        return attempt, event

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
            scope, parameters = configuration.event_candidate_scope(self)
            candidates = self.rows("SELECT e.id,e.role,e.classifier FROM events e JOIN attempts a ON e.classifier=a.id "
                                   "WHERE e.state='classification-held' AND e.recovery_count=0 "
                                   "AND e.hold IS NULL AND e.processed_at IS NULL AND a.collected IS NOT NULL "
                                   "AND (" + scope + ") ORDER BY e.received,e.id", parameters)
            row = None
            for candidate in candidates:
                if not self.role_enabled(candidate['role']):
                    continue
                if self.processing and not self.processing.event(self.event(candidate['id'])):
                    continue  # Current source selection, never role/task authority alone.
                prior = self.attempt(candidate['classifier'])
                detail = json.loads(prior['detail'])
                no_start = (prior['state'] == 'not-started' and detail.get('known_not_started') is True
                            and all(prior[k] is None for k in ('begin', 'ended', 'exit', 'session', 'turn', 'result', 'semantic'))
                            and prior['capture'] == 'not-started' and prior['cleanup'] == 'no-session-created')
                failed = (prior['state'] == 'collected' and prior['ended'] is not None
                          and prior['exit'] is not None)
                if (prior['kind'] != 'classifier' or prior['event'] != candidate['id'] or prior['job'] is not None
                        or not (no_start or failed) or not self._classification_recovery_original(prior, no_start)):
                    continue
                event = self.routing_event(candidate['id'])
                row = candidate
                break
            if row is None:
                return None
            # A proved prelaunch refusal has no executed result to diagnose.
            # Both paths consume the existing single recovery/start credit.
            kind = 'classifier' if no_start else 'diagnosis'
            selected = self.config[kind]
            attempt = self._attempt(kind, row["id"], None, selected["binding"], selected["profile"])
            detail = {**json.loads(self.attempt(attempt)["detail"]), "prior_classifier": row["classifier"]}
            self.db.execute("UPDATE attempts SET detail=? WHERE id=?", (encode(detail), attempt))
            self.db.execute("UPDATE events SET state='classifying',classifier=?,recovery_count=1 WHERE id=?",
                            (attempt, row["id"]))
        return attempt, event

    def _classification_recovery_original(self, prior, no_start):
        if not self.processing:
            return prior['controller'] == self.controller
        if json.loads(prior['detail']).get('processing_capability') != self.processing.key:
            return False  # No foreign capability/collector adoption.
        _, selection = self.processing.current()
        if prior['controller'] == self.controller:
            if no_start:
                return False  # Prelaunch service recovery belongs to a new original.
            if 'service' not in selection:
                return True  # Existing finite collected-failure diagnosis.
        elif 'service' not in selection:
            return False
        current = self.one('SELECT state FROM processing_runs WHERE controller=? AND capability=?',
                           (self.controller, self.processing.key))
        current_service = self.one('SELECT state,returned FROM service_runs WHERE controller=? AND capability=?',
                                   (self.controller, self.processing.key))
        if current != {'state': 'owned'} or current_service != {'state': 'serving', 'returned': None}:
            return False
        if prior['controller'] == self.controller:
            return True
        old = self.one('SELECT state FROM processing_runs WHERE controller=? AND capability=?',
                       (prior['controller'], self.processing.key))
        old_service = self.one('SELECT state,returned FROM service_runs WHERE controller=? AND capability=?',
                               (prior['controller'], self.processing.key))
        if (not old or not old_service or old_service['state'] != 'returned-awaiting-parent-END'
                or old_service['returned'] is None):
            return False
        try:
            receipt = json.loads(old['state'])['parent_END']
        except (ValueError, TypeError, KeyError):
            return False
        return (isinstance(receipt, dict) and type(receipt.get('actual_END')) is int
                and isinstance(receipt.get('evidence'), list) and bool(receipt['evidence']))

    def attempt(self, attempt):
        row = self.one("SELECT * FROM attempts WHERE id=?", (attempt,))
        if not row:
            raise Refusal("attempt not owned by this journal")
        return row

    def begin(self, attempt, detail):
        with self.tx():
            self.require_attempt_execution_open(attempt)
            self.authorize_preparation(attempt)
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

    def record_handback_boundary(self, attempt, thread, original_turn, response_turn,
                                capture, issues, originals, tools, spec_hash):
        """Adapter-only evidence after actual owned idle and the sole next start."""
        self.authorize_launch(attempt)
        with self.tx(collection=attempt):
            row=self.attempt(attempt);detail=json.loads(row['detail'])
            if (row['controller']!=self.controller or row['kind']!='task' or row['state']!='running' or row['ended'] is not None
                    or row['session']!=thread or row['turn']!=response_turn or 'handback_boundary' in detail
                    or not detail.get('resume_attempted') or detail.get('prior_turn')!=original_turn):
                raise Refusal('handback boundary requires unchanged live original collector')
            detail['handback_boundary']={'version':1,'nonce':ident(),'attempt':attempt,'controller':self.controller,
                'thread':thread,'original_turn':original_turn,'response_turn':response_turn,
                'binding':row['binding'],'profile':row['profile'],'spec_hash':spec_hash,
                'task_hash':digest(self.config['tasks'][self.job(row['job'])['task']]),
                'owned_idle':True,'budget_used':1,'original_capture':capture,'capture_issues':issues,
                'originals':originals,'original_tools':tools}
            self.db.execute('UPDATE attempts SET detail=? WHERE id=?',(encode(detail),attempt))

    def collect(self, attempt, outcome):
        """Only the launching controller supplies actual child.wait() outcome."""
        self.require_attempt_execution_open(attempt)
        qualification_error=None
        if 'handback_boundary' in json.loads(self.attempt(attempt)['detail']):
            try:
                self.authorize_launch(attempt)
                current=self.attempt(attempt);boundary=json.loads(current['detail'])['handback_boundary']
                if boundary['task_hash']!=digest(self.config['tasks'][self.job(current['job'])['task']]):
                    raise Refusal('selected task/admission/scope changed after owned boundary')
            except (Refusal, OSError) as exc:qualification_error=str(exc)
        with self.tx(collection=attempt):
            row = self.attempt(attempt)
            if row["controller"] != self.controller or row["collected"] is not None:
                raise Refusal("foreign or duplicate collection refused")
            if outcome.get("exit") is not None and type(outcome["exit"]) is not int:
                raise Refusal("actual numeric process exit required when observed")
            result = outcome.get("result")
            result_json = encode(result) if result is not None else None
            if result_json and len(result_json.encode()) > self.config["limits"]["max_result_bytes"]:
                from .custody import conserve_oversize_result
                recovery = conserve_oversize_result(self, attempt, result_json.encode())
                outcome = {**outcome, "error": "typed result exceeded bounded capture; exact original recovery custody retained",
                           "capture": "incomplete", "detail": {**outcome.get("detail", {}), "oversize_result": recovery}}
                result, result_json = None, None
            no_start = bool(outcome.get("detail", {}).get("known_not_started")) and row["begin"] is None
            ended = self.clock() if outcome.get("exit") is not None else None
            detail={**json.loads(row['detail']), **outcome.get('detail', {})}
            # No outcome/model can inject or replace journal-only evidence.
            stored=json.loads(row['detail'])
            detail.pop('handback_receipt',None)
            detail.pop('handback_boundary',None)
            if 'handback_boundary' in stored:
                detail['handback_boundary']=stored['handback_boundary']
                evidence={'returns':detail.get('terminal_return_evidence',[]),
                    'tools':detail.get('tool_completion',{}),'issues':detail.get('capture_issues',[]),
                    'original_error':detail.get('original_handback_error')}
                candidate={**row,'state':'collected','result':result_json,'detail':encode(detail),'exit':outcome.get('exit'),
                    'ended':ended,'collected':self.clock() if ended else None,
                    'capture':outcome['capture'],'error':outcome.get('error')}
                receipt={'version':1,'issuer':self.controller,'binding':handback_binding(candidate),
                    'boundary_hash':digest(detail['handback_boundary']),'result_hash':digest(result),
                    'evidence_hash':digest(evidence)}
                detail['handback_receipt']=receipt
                try:
                    if qualification_error:raise Refusal(qualification_error)
                    handback_receipt(candidate,detail,result)
                except (Refusal, ValueError, TypeError, KeyError) as exc:
                    detail.pop('handback_receipt',None)
                    detail['handback_reconciliation']='refused'
                    detail['handback_receipt_failure']=str(exc)[:2000]
                else:detail['handback_reconciliation']='current-response-qualified-original-held'
            self.db.execute("UPDATE attempts SET state=?,ended=?,exit=?,collected=?,result=?,error=?,"
                            "semantic=?,capture=?,cleanup=?,detail=? WHERE id=?",
                            ("not-started" if no_start else ("collected" if ended else "unknown"), ended, outcome.get("exit"),
                             self.clock() if ended or no_start else None, result_json, outcome.get("error"),
                             result.get("semantic") if isinstance(result, dict) else row["semantic"],
                             outcome["capture"], outcome["cleanup"],
                             encode(detail), attempt))
            self.db.execute("INSERT INTO results VALUES(?,?,?,?,?,?,?,?)",
                            (attempt, row["job"], row["event"], result_json, outcome.get("error"),
                             outcome.get("exit"), outcome["capture"], self.clock(),))
            oneoff.collected(self, attempt)

    def record_original_end(self, attempt, observation):
        """Original collector delivers a later fact, never an effect/hold release."""
        if type(observation.get('exit')) is not int or observation.get('kind') not in {
                'appserver-model', 'preflight-metadata', 'native-caller'} or not observation.get('original'):
            raise Refusal('attributable exact original numeric observation required')
        with self.tx(collection=attempt):
            row = self.attempt(attempt)
            if row['controller'] != self.controller:
                raise Refusal('later observation belongs to the original collector')
            detail = json.loads(row['detail'])
            observations = list(detail.get('original_end_observations', []))
            prior = next((x for x in reversed(observations) if x['original'] == observation['original']), None)
            if prior:
                if any(prior[k] != observation[k] for k in ('kind', 'exit')):
                    raise Refusal('original numeric observation cannot change')
                if all(prior.get(k) == value for k, value in observation.items()):
                    return  # Delivery retry, not a new observation or processing clock.
            receipt = {**observation, 'collector': self.controller, 'attempt': attempt, 'observed_at': self.clock()}
            self.budget(None, len(encode(receipt).encode()) + 4096)
            detail['original_end_observations'] = observations + [receipt]
            changes = {'detail': encode(detail)}
            initial = self.one('SELECT exit FROM results WHERE attempt=?', (attempt,))
            if observation['kind'] == 'appserver-model' and initial and initial['exit'] is None:
                if row['exit'] is not None:
                    raise Refusal('later model END cannot replace a current numeric observation')
                changes.update(exit=observation['exit'], ended=receipt['observed_at'],
                               collected=receipt['observed_at'], state='collected')
            oneoff.observe_end(self, attempt, changes)

    def classification_failed(self, attempt, error):
        with self.tx():
            self.db.execute("UPDATE events SET state='classification-held',error=? WHERE classifier=? AND state='classifying'",
                            (str(error)[:2000], attempt))

    def capture_gap(self, attempt, error):
        with self.tx():
            self.require_attempt_execution_open(attempt)
            row = self.attempt(attempt)
            if row["controller"] != self.controller:
                raise Refusal("capture qualification belongs to the original collector")
            detail={**json.loads(row['detail']),'protocol_capture':row['capture'],
                    'pre_inventory_error':row['error'],'artifact_inventory_error':str(error)[:1000]}
            message=((row['error']+'; ') if row['error'] else '')+'artifact inventory: '+str(error)
            oneoff.advance(self, attempt, {'capture': 'artifact-inventory-incomplete', 'error': message[:2000],
                                          'detail': encode(detail)}, 'original artifact inventory gap')
            self.db.execute("UPDATE results SET capture='artifact-inventory-incomplete',error=? WHERE attempt=?",
                            (message[:2000], attempt))

    def commit_classification(self, attempt):
        with self.tx():
            row = self.attempt(attempt)
            self._classification_current(row)
            if row["exit"] != 0 or not row["collected"] or row["capture"] != "complete" or row["error"]:
                raise Refusal("classification requires actual successful collection and complete typed capture")
            event = self.routing_event(row["event"])
            answer = classification(json.loads(row["result"]), event, self.config)
            task = self.config["tasks"].get(answer["task"])
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
        from .reservation import write
        self._reservation_observations = []
        try:
            with self.tx():
                pending = self.rows("SELECT q.* FROM queue q JOIN events e ON e.id=q.event "
                                    "WHERE q.state='queued' AND e.hold IS NULL ORDER BY e.received,q.id")
                return self._reserve_first(pending)
        except Refusal:
            # The original reservation transaction rolled back. Retain only
            # reached observations in a separate ordinary transaction, then
            # propagate the same control refusal; no job/effect is retried.
            if self._reservation_observations:
                with self.tx():
                    for record in self._reservation_observations:
                        write(self, record)
            raise
        finally:
            self._reservation_observations = None

    def _reserve_first(self, pending):
        for row in pending:
            job = self._reserve_candidate(row)
            if job:
                return job
        return None

    def _reserve_candidate(self, row):
        from .reservation import Evaluation
        with Evaluation(self, row) as observation:
            role, phase, task = row["role"], row["phase"], self.config["tasks"][row["task"]]
            enrollment = self.one("SELECT * FROM enrollments WHERE role=?", (role,))
            held_phases = self.config["roles"][role].get("legacy_hold_phases", list({"proposer", "integrator", "execution", "cleanup"}))
            from .resource_scopes import blocked, qa_accounts
            if not enrollment:
                observation.failed('enrollment')
                return None
            observation.at('role-enabled')
            if not self.role_enabled(role):
                observation.finish('false')
                return None
            observation.at('processing-task')
            if self.processing and not self.processing.task(row):
                observation.finish('false')
                return None
            observation.at('owner-review')
            if self.processing and task.get('execution') == 'owner' and not self.processing.review_task(row['task']):
                observation.finish('false')
                return None
            observation.at('legacy-hold')
            if enrollment["legacy_hold"] and phase in held_phases and blocked(self, row):
                observation.finish('false')
                return None
            observation.at('task-active')
            if task.get("active") is False:
                observation.finish('false')
                return None
            observation.at('package-admission')
            if task.get("require_package_scope") and not self.one("SELECT package FROM admissions WHERE package=?", (row["package"],)):
                observation.finish('false')
                return None
            observation.at('outstanding-jobs')
            outstanding = self.rows("SELECT * FROM jobs WHERE role=? AND phase=? AND state!='closed'", (role, phase))
            observation.at('local-selection')
            local = local_integration.selected(self, row["task"])
            report = False
            if local:
                try:
                    if local_integration.report_route(self, row):
                        report = True
                        local = None  # Authenticated finite reports use the sole central integrator.
                except Refusal:
                    observation.finish('refusal')
                    return None
            observation.at('execution-capacity')
            active = sum(not self.execution_complete(job) for job in outstanding)
            limit = min(5, local["capacity"]) if local else self._capacity(task)
            if active >= limit:
                observation.finish('false')
                return None
            observation.at('same-package-outstanding')
            if task.get("require_package_scope") and any(j["package"] == row["package"] for j in outstanding):
                observation.finish('false')
                return None  # Unsettled responsibility in the same admitted scope stays fenced.
            observation.at('qa-admission')
            if role == "QA" and not self.one("SELECT * FROM admissions WHERE package=?", (row["package"],)):
                observation.finish('false')
                return None
            observation.at('qa-phase')
            if role == 'QA' and not local and (self.config.get('window_service') or self.processing):
                # The retained-hold check above has already validated this exact
                # Work-selected operation, acceptance/report (for cleanup), current
                # source/rights and unresolved resource maps. Its phase capacities
                # are independent; unrelated execution must not delay accepted
                # consolidation, or vice versa. Keep the legacy barrier for routes
                # without that finite operation-relative qualification.
                record = (self.processing.current()[1].get('service', {}).get('legacy_resources', {}).get('QA', {})
                          if self.processing else {})
                separate_slots = (enrollment['legacy_hold'] and phase in held_phases and qa_accounts(record))
                other = 'cleanup' if phase == 'execution' else 'execution'
                if not separate_slots and any(not self.execution_complete(j) for j in self.rows(
                        "SELECT * FROM jobs WHERE role='QA' AND phase=? AND state!='closed'", (other,))):
                    observation.finish('false')
                    return None
            observation.at('qa-package-outstanding')
            if role == "QA" and (phase == "execution" or local) and self.one(
                    "SELECT id FROM jobs WHERE role='QA' AND package=? AND phase IN ('execution','cleanup') AND state!='closed'", (row["package"],)):
                observation.finish('false')
                return None
            admission = self.one("SELECT * FROM admissions WHERE package=?", (row["package"],)) if role == "QA" else None
            prior = self.one("SELECT * FROM qa_package_owners WHERE package=?", (row["package"],)) if admission and phase == "execution" else None
            observation.at('qa-prior-admission')
            if prior and prior["admission"] == digest(admission["receipt"]):
                observation.finish('false')
                return None
            observation.at('qa-prior-dependency')
            if prior and any(self.dependency_hold(m["event"]) for m in json.loads(self.job(prior["job"])["members"])):
                observation.finish('false')
                return None
            try:
                observation.at('integration-window')
                window = None if local else self.integration_window(row)
            except Refusal:
                observation.finish('refusal')
                return None
            try:
                observation.at('members')
                members = local_integration.members(self, row) if local else (json.loads(window['basis'])['members'] if window else self._members(row))
                observation.at('local-availability')
                if (local or report) and not local_integration.available(self, row, members, observe=observation.at,
                                                            conflict_observe=observation.conflict):
                    observation.finish('false')
                    return None
            except Refusal as exc:
                observation.finish('refusal')
                self.db.execute('INSERT INTO operational_errors VALUES(?,?,?,?,1,?) ON CONFLICT(subject) '
                                'DO UPDATE SET detail=excluded.detail,active=1,observed=excluded.observed',
                                (row['event'], role, 'local-integration-dependency', encode({
                                    'dependency':str(exc), 'controller':self.controller,
                                    'capability':self.processing.key if self.processing else None,
                                    'source_hash':observation.context[1],
                                    'queue':row['id'], 'task':row['task']}), self.clock()))
                return None
            observation.at('member-processing')
            if self.processing and any(not self.processing.task(self.one('SELECT * FROM queue WHERE id=?', (m['queue'],))) for m in members):
                observation.finish('false')
                return None
            packages = {member["package"] for member in members}
            package = next(iter(packages)) if len(packages) == 1 else None
            observation.at('job-budget')
            self.budget("jobs", event=row['event'])
            observation.at('reservation')
            job, token = ident(), ident()
            self.db.execute("INSERT INTO jobs(id,role,phase,task,package,members,controller,token,created) "
                            "VALUES(?,?,?,?,?,?,?,?,?)", (job, role, phase, row["task"], package,
                                                         encode(members), self.controller, token, self.clock()))
            # Ancestry validation can recheck a native producer's physical
            # guard. Publish this reservation's immutable map first, within
            # the same transaction, so it is not an opaque foreign holder.
            self.db.execute('INSERT INTO job_resource_policies VALUES(?,?,?)', (job, encode(self.config['tasks'][row['task']]),
                            encode(self.one('SELECT * FROM admissions WHERE package=?',(package,))) if package else None))
            prospective.note_job(self, job)
            local_integration.record_job(self, self.job(job))
            if admission and phase == "execution":
                self.db.execute("INSERT OR REPLACE INTO qa_package_owners VALUES(?,?,?)", (row["package"], digest(admission["receipt"]), job))
            for member in members:
                self.db.execute("UPDATE queue SET state='reserved',job=? WHERE id=? AND state='queued'",
                                (job, member["queue"]))
            if window:
                self.db.execute('UPDATE integration_windows SET job=? WHERE id=? AND job IS NULL', (job, window['id']))
            observation.at('reservation')
            observation.finish('reserved')
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
        from .report_scope import bounded_members
        rows = bounded_members(self, row, rows)
        return [self._input_member(r) for r in rows]

    def _input_member(self,row):
        member={'queue':row['id'],'event':row['event'],'hash':digest(self.event(row['event'])),'package':row['package']}
        selection=self.input_resolution(row['event'])
        if selection:member['input_resolution']=selection['version']
        return member

    def start_job(self, job, token, profile=None):
        with self.tx():
            self.require_execution_open(job)
            row = self.job(job, token)
            from .native_review_scope import admit
            admit(self, row)
            self.integration_launch_current(row)
            local_integration.current_job(self, row)
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
        if self.one('SELECT job FROM work_read_fences WHERE job=?', (job['id'],)):
            return True  # Permanent owner-issued execution fence; retained duties stay owned.
        if job["state"] != "awaiting-delivery" or job["effects"] not in {"none", "reconciled"} or job["hold_reason"]:
            return False
        attempt = self.attempt(job["active_attempt"]) if job["active_attempt"] else None
        return bool(attempt and attempt["begin"] is not None and attempt["ended"] is not None
                    and attempt["collected"] is not None and attempt["exit"] == 0
                    and attempt["state"] == "collected" and collected_capture(attempt)
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
            self.require_execution_open(job)
            row = self.job(job, token)
            if row["controller"] != self.controller:
                raise Refusal("stale/foreign controller cannot close a successor reservation")
            if row["state"] == "closed":
                return None
            from .report_scope import source_metadata
            from .native_review_scope import admit
            admit(self, row)
            source_metadata(self, row)
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
            if attempt["exit"] != 0 or not collected_capture(attempt) or attempt["error"]:
                self.failure_delivery(row,attempt,task,"Collected failure/capture requires bounded recovery or real owner disposition")
                self.db.execute("UPDATE jobs SET state='held' WHERE id=?", (job,))
                return None
            try:result = collected_task_result(attempt)
            except Refusal as exc:
                self.failure_delivery(row,attempt,task,'Invalid inner task contract: '+str(exc))
                self.db.execute("UPDATE jobs SET state='held',hold_reason=? WHERE id=?",(str(exc),job))
                return None
            from .report_scope import validate_result
            validate_result(self, row, result)
            local_integration.validate_method(self, row, attempt, result)
            if result["semantic"] != "DONE":
                self.failure_delivery(row,attempt,task,"Incomplete task: retain all findings/failures/UNKNOWNs")
                self.db.execute("UPDATE jobs SET state='held' WHERE id=?", (job,))
                return None
            if self.config.get('software_delegation') or json.loads(attempt['detail']).get('software_authority'):
                detail = json.loads(attempt['detail'])
                tools = detail.get('tool_completion', {})
                from .reviews import collected_proof
                from .software import report_routes
                reviewed = collected_proof(self, row, attempt)
                if (not detail.get('software_authority') or not (reviewed or tools.get('complete'))
                        or (not task.get('routine_completion') and not report_routes(self, row, result) and (tools.get('nonzero_completions')
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
            if not task.get('routine_completion'):
                local_integration.finish_discovery(self, row, attempt, result)
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
        from .report_scope import transport_custody
        report_custody = transport_custody(self, job, result)
        if report_custody is not None:
            response['report_custody'] = report_custody
        branch_keys={self.event(m['event']).get('branch_binding') for m in members}-{None}
        if not branch_keys and local_integration.selected(self, job['task']):
            from .branches import job_branch
            actual_branch = job_branch(self, job)
            if actual_branch:
                branch_keys.add(actual_branch['id'])
        if len(branch_keys)==1:
            response['branch_binding']=next(iter(branch_keys))
        commit = self.one('SELECT state,receipt FROM local_commits WHERE attempt=?', (attempt['id'],))
        updates = json.loads(commit['receipt']).get('continuations', {}) if commit and commit['state']=='published' else {}
        basis = self.one('SELECT basis FROM local_bases WHERE attempt=?', (attempt['id'],))
        if not updates and basis:
            frozen = json.loads(basis['basis'])
            if frozen['scope']['lane'] == 'anchored':
                response['integration'] = {k:frozen['scope'][k] for k in ('reads','writes')}
                response['integration']['versions'] = frozen['versions']
        outputs = [{**response, 'id': response_id if index == 0 else digest({'response':attempt['id'], 'point':key}),
                    'integration':binding} for index,(key,binding) in enumerate(sorted(updates.items()))] if updates else [response]
        from .processing import note_source
        for output in outputs:
            if report_custody is not None:
                from .report_scope import validate_envelope
                validate_envelope(self, output)
            self.budget("events", len(encode(output).encode()), job=job['id'])
            self.db.execute("INSERT INTO events(id,role,payload,hash,received,parent) VALUES(?,?,?,?,?,?)",
                            (output['id'], destination, encode(output), digest(output), self.clock(), output['parent']))
            note_source(self, output['id'])
            if task.get("publish_internal_results"):
                self._outbox(job["role"], destination, "result", output, job=job['id'], event=output['id'],
                             producer=attempt['session'], key=digest({'response_delivery':output['id']}))
        return outputs[0]['id']

    def complete_events(self):
        """Completion includes descendants, durable handoffs and receipt outcomes."""
        with self.tx():
            changed = True
            while changed:
                self.complete_input_controls()
                cursor = self.db.execute("UPDATE events SET state='processed',processed_at=? " + self._completion_where(),
                                         (self.clock(), None, None, None))
                changed = cursor.rowcount > 0

    def completion_candidates(self, event=None, incoming=None):
        """Current whole-event obligations, optionally before its incoming receipt.

        Only frontier's exact published-response edge may supply incoming. This
        is evidence for that receipt, never permission to mark an event early.
        All consumers, descendant events and their outgoing duties still join.
        """
        return self.rows("SELECT id FROM events " + self._completion_where(), (incoming, event, event))

    @staticmethod
    def _completion_where():
        return ("WHERE processed_at IS NULL AND hold IS NULL AND ack IN ('done','plain','internal') "
                    "AND NOT EXISTS (SELECT 1 FROM input_resolutions ir WHERE ir.event=events.id "
                    "AND ir.version=(SELECT MAX(v.version) FROM input_resolutions v WHERE v.event=events.id) "
                    "AND json_array_length(json_extract(ir.receipt,'$.remaining_obligations'))>0 "
                    "AND NOT EXISTS (SELECT 1 FROM plain_control_dispositions pc WHERE pc.event=events.id "
                    "AND pc.version=ir.version AND pc.source_hash=ir.source_hash AND pc.source_hash=events.hash "
                    "AND plain_control_valid(events.id)=1)) "
                    "AND id IN (SELECT event FROM queue WHERE state='done') "
                    "AND NOT EXISTS (SELECT 1 FROM plain_control_dispositions pc JOIN processing_control_returns cr "
                    "ON cr.source=pc.event WHERE cr.response=events.id "
                    "AND json_extract(pc.request,'$.consumer_disposition.event')=events.id "
                    "AND plain_control_valid(pc.event)=0) "
                    "AND NOT EXISTS (SELECT 1 FROM file_publications fp JOIN attempts a ON a.id=fp.attempt JOIN queue q ON q.job=a.job WHERE q.event=events.id AND fp.state!='published') "
                    "AND NOT EXISTS (SELECT 1 FROM outboxes o WHERE (o.event=events.id OR EXISTS "
                    "(SELECT 1 FROM queue q WHERE q.job=o.job AND q.event=events.id)) "
                    "AND o.id!=COALESCE(?, '') "
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
                    "(SELECT 1 FROM events r WHERE r.id=j.response AND r.processed_at IS NOT NULL)))) "
                    "AND (? IS NULL OR id=?)")

    def claim_recovery(self, job):
        with self.tx():
            if self.integration_retired(job):
                return None
            row = self.job(job)
            try:
                local_integration.current_sources(self, row)
            except Refusal:
                return None  # No prior result acquisition or global recovery veto.
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
            local_integration.current_sources(self, row)
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
        local_integration.current_sources(self, row)
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
            # Hold disposition is independent of actual completion. New work is
            # retained by its own queue/job/dependent obligations and clock.
            self.db.execute("UPDATE events SET hold=? WHERE id=?", (reason, event))

    def hold_job(self, job, reason):
        with self.tx():
            self.require_execution_open(job)
            self.db.execute("UPDATE jobs SET state='held',hold_reason=? WHERE id=? AND state!='closed' AND controller=?",
                            (str(reason)[:2000], job, self.controller))

    def adopt_collected(self, job):
        """Transfer closure work only, never an active process handle or unknown attempt."""
        with (nullcontext() if self.db.in_transaction else self.tx()):
            self.require_execution_open(job)
            row = self.job(job)
            local_integration.current_sources(self, row)
            attempt = self.attempt(row["active_attempt"])
            task = self.config["tasks"][row["task"]]
            if row["state"] == "closed" or row["recovery_owner"] and row['recovery_state']!='awaiting-disposition':
                raise Refusal("closed/recovering reservation cannot transfer collection closure")
            if row['recovery_owner']:
                diag=self.current_diagnosis(row)
                no_start=diag and diag['state']=='not-started' and json.loads(diag['detail']).get('known_not_started')
                pending=self.one("SELECT detail FROM operational_errors WHERE subject=? AND active=1 "
                    "AND kind='recovery-admission-pending'", ('recovery-admission:'+job,))
                metadata=json.loads(pending['detail']) if pending else {}
                unallocated=(not diag and pending and metadata.get('diagnosis') is None
                    and metadata.get('job')==row['id'] and metadata.get('attempt')==row['active_attempt']
                    and metadata.get('reservation')==row['token']
                    and all(metadata.get(k)==row[k] for k in ('controller','recovery_owner','recovery_count')))
                if unallocated:
                    # A real foreign recovery claim may suspend before it has
                    # any diagnosis. Its marker proves responsibility, not END:
                    # every related original must separately be closed.
                    if self.one('SELECT id FROM attempts WHERE job=? AND (ended IS NULL OR collected IS NULL OR exit IS NULL)', (job,)):
                        raise Refusal('unknown related original retains its actual collector')
                elif not diag or diag['collected'] is None or diag['ended'] is None and not no_start:
                    raise Refusal('unknown recovery diagnosis prevents closure transfer')
            if attempt["ended"] is None or not attempt["collected"] or type(attempt['exit']) is not int:
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
                "pending_alert_deliveries": self.one('SELECT COUNT(*) AS count FROM alerts a WHERE NOT EXISTS (SELECT 1 FROM outboxes o WHERE o.alert=a.id) AND NOT EXISTS (SELECT 1 FROM alert_delivery_members m WHERE m.occurrence=a.id)'),
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
