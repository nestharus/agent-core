"""Exact owned artifact/queue retirement after processing+24h and all holds.

Role: intrinsic-surface. Domain: coordinator retention. This never enumerates or
deletes a profile/session store. Ephemeral server teardown is owned by AppServer.
Required final results remain in the journal; cumulative bounds apply to them.
"""

import hashlib
import os
from pathlib import Path
import stat

from .contracts import Refusal, encode

RETENTION = 86400


def regular_identity(path):
    value = path.lstat()
    if not stat.S_ISREG(value.st_mode) or value.st_nlink != 1:
        raise Refusal("exact owned single-link regular artifact required")
    return value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns


def register_artifact(store, attempt, path):
    from .custody import guard_path
    guard_path(store, path)
    root = store.home / "artifacts" / attempt
    path = Path(path)
    if not path.is_absolute() or not path.is_relative_to(root):
        raise Refusal("artifact is outside exact newly owned attempt directory")
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise Refusal("symlink artifact/ancestor refused")
    identity = regular_identity(path)
    maximum = min(store.config["limits"]["max_bytes"], store.config["limits"].get("max_artifact_bytes", 33554432))
    sha256 = artifact_digest(root, path, identity, maximum)
    with store.tx():
        store.attempt(attempt)
        store.db.execute("INSERT INTO artifacts(path,attempt,dev,ino,size,mtime,sha256) VALUES(?,?,?,?,?,?,?)",
                         (str(path), attempt, *identity, sha256))


def artifact_digest(root, path, expected, maximum):
    if expected[2] > maximum:
        raise Refusal("owned report exceeds cumulative storage budget; retain without hashing")
    parent, name = open_parent(root, path)
    try:
        return digest_at(parent, name, expected, maximum)
    finally:
        os.close(parent)


def digest_at(parent, name, expected, maximum):
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=parent)
    try:
        sha = hash_fd(fd, maximum)
        after = os.fstat(fd)
        if (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns) != expected:
            raise Refusal("owned artifact changed while freezing its source witness")
        return sha
    finally:
        os.close(fd)


def hash_fd(fd, maximum):
    sha, total = hashlib.sha256(), 0
    for block in iter(lambda: os.read(fd, 65536), b""):
        total += len(block)
        if total > maximum:
            raise Refusal("owned artifact grew beyond its bounded source read")
        sha.update(block)
    return sha.hexdigest()


def conserve(store, path, actor, receipt):
    row = store.one("SELECT * FROM artifacts WHERE path=?", (str(path),))
    if not row:
        raise Refusal("artifact is not in exact owned inventory")
    attempt = store.attempt(row["attempt"])
    job = store.job(attempt["job"])
    if actor != store.config["roles"][job["role"]]["owner"] or not receipt:
        raise Refusal("actual consumer/role owner conservation receipt required")
    with store.tx():
        store.db.execute("UPDATE artifacts SET conserved=? WHERE path=?", (encode({"actor": actor, "receipt": receipt}), str(path)))


def eligible_event(store, event):
    from .branches import event_held
    if event_held(store,event['id']):
        return False
    if store.one('SELECT c.attempt FROM review_calls c JOIN review_contexts r ON r.component=c.component '
                 'JOIN attempts a ON a.id=c.attempt LEFT JOIN queue q ON q.job=a.job '
                 'WHERE (a.event=? OR q.event=?) AND (r.closed_at IS NULL OR r.closed_at>?) LIMIT 1',
                 (event['id'], event['id'], store.clock()-RETENTION)):
        return False
    if store.withdrawn_integration_hold(event["id"]):
        return False
    if store.one("SELECT p.target FROM file_publications p JOIN attempts a ON a.id=p.attempt JOIN queue q ON q.job=a.job WHERE q.event=? AND p.state!='published'",(event['id'],)):
        return False
    if event["processed_at"] is None or store.clock() < event["processed_at"]+RETENTION or event["hold"]:
        return False
    if store.dependency_hold(event["id"]):
        return False
    if any(row["processed_at"] is None or store.clock() < row["processed_at"]+RETENTION for row in store.dependents(event["id"])):
        return False
    active = store.one("SELECT j.id FROM queue q JOIN jobs j ON j.id=q.job WHERE q.event=? "
                       "AND (j.state!='closed' OR j.effects NOT IN ('none','reconciled'))", (event["id"],))
    if active:
        return False
    attempts = store.rows("SELECT a.* FROM attempts a LEFT JOIN queue q ON q.job=a.job "
                          "WHERE a.event=? OR q.event=?", (event["id"], event["id"]))
    # Session/store uncertainty stays separately owned, not a universal freeze
    # on already conserved queue sources or permission to purge a profile.
    return all(a["collected"] is not None and (a["ended"] is not None or a["state"] == "not-started")
               and a["cleanup"] in {"done", "owned-ephemeral-lifecycle-observed", "no-session-created"} for a in attempts)


def artifact_eligible(store, artifact):
    if store.one("SELECT path FROM artifact_custody WHERE path=? AND kind='role-owned'",(artifact['path'],)):
        return False  # Explicit canonical/role custody overrides disposable location.
    attempt = store.attempt(artifact["attempt"])
    if not artifact["conserved"] or attempt["cleanup"] not in {"done", "owned-ephemeral-lifecycle-observed"} or attempt["ended"] is None:
        return False
    events = store.rows("SELECT e.* FROM events e JOIN queue q ON e.id=q.event WHERE q.job=?", (attempt["job"],))
    if not events:
        return False
    return all(eligible_event(store, event) for event in events)


def open_parent(root, path):
    """Walk with directory descriptors and O_NOFOLLOW; no symlink traversal."""
    relative = path.relative_to(root)
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in relative.parts[:-1]:
            fd = descend(fd, part)
        return fd, relative.name
    except BaseException:
        os.close(fd)
        raise


def descend(fd, part):
    next_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
    os.close(fd)
    return next_fd


def unlink_exact(store, row):
    path = Path(row["path"])
    root = store.home / "artifacts" / row["attempt"]
    if any(p.is_symlink() for p in (root, *root.parents)):
        raise Refusal("owned artifact root/ancestor became a symlink")
    fd, name = open_parent(root, path)
    try:
        info = os.stat(name, dir_fd=fd, follow_symlinks=False)
        expected = (row["dev"], row["ino"], row["size"], row["mtime"])
        actual = (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)
        if actual != expected or not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise Refusal("artifact identity/metadata changed immediately before deletion")
        os.unlink(name, dir_fd=fd)
        os.fsync(fd)
    finally:
        os.close(fd)


def retire_artifact(store, row):
    # The same SQLite write lock fences concurrent hold changes and retirement.
    with store.tx():
        fresh = store.one("SELECT * FROM artifacts WHERE path=?", (row["path"],))
        if fresh["removed"] is not None or not artifact_eligible(store, fresh):
            return {"path": row["path"], "state": "held"}
        try:
            unlink_exact(store, fresh)
        except Exception as exc:
            store.db.execute("UPDATE artifacts SET error=? WHERE path=?", (type(exc).__name__+": "+str(exc)[:500], row["path"]))
            return {"path": row["path"], "state": "partial-held", "error": type(exc).__name__}
        store.db.execute("UPDATE artifacts SET removed=?,error=NULL WHERE path=?", (store.clock(), row["path"]))
    return {"path": row["path"], "state": "removed"}


def retire_event(store, event):
    with store.tx():
        fresh = store.one("SELECT * FROM events WHERE id=?", (event["id"],))
        if fresh["state"] == "retired" or not eligible_event(store, fresh):
            return None
        held = store.one("SELECT ar.path FROM artifacts ar JOIN attempts a ON ar.attempt=a.id "
                         "JOIN queue q ON q.job=a.job WHERE q.event=? AND ar.removed IS NULL", (event["id"],))
        if held:
            return {"event": event["id"], "state": "artifact-held"}
        store.db.execute("DELETE FROM queue WHERE event=?", (event["id"],))
        payload = store.source_for_retirement(fresh)
        store.db.execute("UPDATE events SET payload=?,state='retired' WHERE id=?", (payload, event["id"]))
    return {"event": event["id"], "state": "retired", "processed_at": fresh["processed_at"]}


def sweep(store):
    from .storage import sweep as storage_sweep
    storage_receipts = storage_sweep(store)
    artifacts = store.rows("SELECT * FROM artifacts WHERE removed IS NULL AND error IS NULL")
    receipts = [retire_artifact(store, row) for row in artifacts]
    events = store.rows("SELECT * FROM events WHERE processed_at IS NOT NULL AND state!='retired'")
    receipts += [retire_event(store, row) for row in events]
    # An old processed timestamp alone does not qualify external control,
    # publication, effect, recovery or privacy holds. Standalone alert retirement
    # now requires the genuine same source/consumer owner's exact current proof.
    return storage_receipts + [receipt for receipt in receipts if receipt]
