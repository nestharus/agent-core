"""Producer outputs are owned; Codex account stores are not inferred owned.

Legacy allocated namespaces can contain foreign logical records. They are opaque,
including during accounting/cleanup. No filesystem allocation or config echo is
an ownership receipt. Only registered report files have automatic retirement.
"""
import asyncio
from contextlib import suppress

from .contracts import Refusal, encode

SCHEMA = """
CREATE TABLE IF NOT EXISTS attempt_storage(
 attempt TEXT PRIMARY KEY,path TEXT NOT NULL,dev INTEGER NOT NULL,ino INTEGER NOT NULL,
 settings TEXT NOT NULL,state TEXT NOT NULL,removed REAL,error TEXT);
"""


async def guard(store, child, outcome):
    """Backpressure new allocation and stop only this owned writer on overflow.

    This is a sampled byte/count bound, not a filesystem quota or data discard.
    """
    while child.returncode is None:
        try:
            usage=store.usage()
            if usage['bytes'] >= store.config['limits']['max_bytes']:
                raise Refusal('cumulative owned storage byte capacity reached')
        except (Refusal,OSError) as exc:
            outcome['error']=str(exc)
            outcome['detail']['storage_capacity_hold']=str(exc)
            with suppress(ProcessLookupError):child.terminate()
            return
        await asyncio.sleep(0.25)


def prepare(store, attempt):
    mode = store.config.get('session_storage', {}).get('mode')
    if mode == 'owned-attempt':
        raise Refusal('owned-attempt storage is unsupported: allocated Codex stores may contain foreign records; select producer-owned explicitly')
    if mode != 'producer-owned':
        return None
    # Never redirect SQLite/log/account roots or inspect their logical contents.
    # These settings reduce new auxiliary capture; they do not establish absence.
    return {'history': {'persistence':'none'}, 'feedback': {'enabled':False},
            'features': {'shell_snapshot':False}}


def flags(settings):
    if not settings:return []
    result = []  # Runtime-only strict-config belongs on app-server, not MCP/features.
    for key, value in settings.items():
        if isinstance(value, dict):
            for name, leaf in value.items():result += ['-c', key+'.'+name+'='+encode(leaf)]
        else:result += ['-c', key+'='+encode(value)]
    return result


def verify(store, attempt, settings, returned):
    effective = returned.get('config', {})
    for name, expected in settings.items():
        observed = effective.get(name)
        if isinstance(expected, dict):
            if not isinstance(observed, dict) or any(observed.get(k) != v for k,v in expected.items()):
                raise Refusal('effective producer setting missing/overridden: '+name)
        elif observed != expected:
            raise Refusal('effective producer setting missing/overridden: '+name)


def sweep(store):
    """Conserve legacy namespaces without even stat/enumeration of their paths.

    This is a journal-only ownership hold, not a physical cleanup attempt. It
    neither holds unrelated processed queues nor certifies shared-store absence.
    """
    with store.tx():
        store.db.execute("UPDATE attempt_storage SET state='opaque-ownership-held',error=? "
                         "WHERE removed IS NULL AND state!='opaque-ownership-held'",
                         ('Allocated Codex namespace has unproven logical ownership; no inspection or deletion',))
    return []
