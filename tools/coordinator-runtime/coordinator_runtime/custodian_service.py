"""Owned, bounded process visits; no callback runs on the receipt event loop.

The registered existing owner adapter performs its own genuine qualification,
processing/hold/custody work and retains original effect intents/results. This
broker supplies no grants, processing stamps, retirement or cleanup authority.
An attempted/unknown visit is never automatically replayed, even after restart.
"""
import asyncio
import base64
import math
from pathlib import Path

from . import capacity
from .contracts import Refusal, encode, ident, parse_json, required_text

CAPTURE = 65536
SCHEMA = """
CREATE TABLE IF NOT EXISTS custodian_visits(
 id TEXT PRIMARY KEY,occurrence TEXT NOT NULL,role TEXT NOT NULL,owner TEXT NOT NULL,
 basis TEXT NOT NULL,intent TEXT NOT NULL,state TEXT NOT NULL,created REAL NOT NULL,
 pid INTEGER,ended REAL,numeric_end INTEGER,result TEXT,next_at REAL NOT NULL);
CREATE INDEX IF NOT EXISTS custodian_occurrence ON custodian_visits(occurrence,created);
CREATE UNIQUE INDEX IF NOT EXISTS custodian_unresolved ON custodian_visits(occurrence)
 WHERE state NOT IN ('held','done');
"""


def policy(config):
    selected = config.get('custodian_service', {})
    if not isinstance(selected, dict) or set(selected) - set(config['roles']):
        raise Refusal('custodian workers must belong to selected actual roles')
    for value in selected.values():
        if (not isinstance(value, dict) or set(value) != {'argv', 'authority', 'timeout_seconds'}
                or not isinstance(value['argv'], list) or not value['argv']
                or len(value['argv']) > 32 or any(not isinstance(a, str) or not a or len(a.encode()) > 4000 for a in value['argv'])
                or not Path(value['argv'][0]).is_absolute()
                or type(value['timeout_seconds']) not in {int, float}
                or not math.isfinite(value['timeout_seconds']) or not 0 < value['timeout_seconds'] <= 30):
            raise Refusal('custodian worker needs absolute argv, authority and finite <=30s visit')
        required_text(value['authority'], 'existing owner custodian authority', 4000)
    return selected


class Service:
    def __init__(self, store, authorize):
        self.store, self.selected = store, policy(store.config)
        self.authorize = authorize
        self.active = {}  # Original asyncio Tasks own their original Process handles.
        self.cursor, self.end = 0, 0

    def schedule(self):
        store = self.store
        # Reap before selecting the next page, so a completed held-prefix visit
        # cannot consume the next page's opportunity merely by remaining here.
        for role, task in list(self.active.items()):
            if task.done():
                try:
                    task.result()
                except BaseException as exc:
                    store.record_operational_error('custodian-worker:' + role, {'reason': str(exc)}, role, 'custodian-unknown')
                del self.active[role]
        if self.cursor >= self.end:
            self.cursor = 0
            self.end = store.one('SELECT COALESCE(MAX(rowid),0) AS n FROM alerts')['n']
        page = store.rows('SELECT id,rowid AS seq FROM alerts WHERE rowid>? AND rowid<=? ORDER BY rowid LIMIT 16',
                          (self.cursor, self.end))
        for item in page:
            self.cursor = item['seq']
            try:
                alert, outbox, basis = capacity.retirement_basis(store, item['id'])
                role = outbox['role']
                if role in self.active:
                    continue
                if role not in self.selected:
                    store.record_operational_error('custodian-missing:' + role,
                        {'occurrence': item['id'], 'owner': store.enrollment(role)['owner'],
                         'reason': 'no existing owner worker registered; originals remain held'}, role, 'custodian-unavailable')
                    continue
                self.authorize({role})
                # Unknown includes a crash between retained intent and child binding.
                prior = store.one("SELECT * FROM custodian_visits WHERE occurrence=? AND "
                                  "(state NOT IN ('held','done') OR basis=?) ORDER BY created DESC,rowid DESC LIMIT 1",
                                  (item['id'], basis))
                if prior and (prior['state'] != 'held' or store.clock() < prior['next_at']):
                    continue
                owner = store.enrollment(role)['owner']
                request = {'visit': ident(), 'owner': owner, 'role': role, 'occurrence': item['id'],
                           'basis': basis, 'alert': alert, 'outbox': outbox,
                           'authority': self.selected[role]['authority'],
                           'obligation': 'existing genuine owner qualification/processing/holds/custody; no ACK or END inference'}
                encoded = encode(request)
                if len(encoded.encode()) > CAPTURE:
                    raise Refusal('custodian request exceeds bounded visit; exact source remains in journal')
                with store.tx():
                    # A second cooperating controller cannot prepare the same
                    # effect visit between our earlier read and write lock.
                    if store.one("SELECT id FROM custodian_visits WHERE occurrence=? AND "
                                 "(state NOT IN ('held','done') OR (basis=? AND (state='done' OR next_at>?))) LIMIT 1",
                                 (item['id'], basis, store.clock())):
                        continue
                    if capacity.retirement_basis(store, item['id'])[2] != basis:
                        raise Refusal('custodian source changed before retained intent')
                    store.budget(None, len(encoded.encode()) + 3 * CAPTURE + 4096)
                    store.db.execute('INSERT INTO custodian_visits VALUES(?,?,?,?,?,?,\'prepared\',?,NULL,NULL,NULL,NULL,0)',
                                     (request['visit'], item['id'], role, owner, basis, encoded, store.clock()))
                task = asyncio.create_task(self.visit(request))
                self.active[role] = task
            except Refusal as exc:
                store.record_operational_error('custodian-source:' + item['id'], {'reason': str(exc)}, kind='custodian-held')
        if len(page) < 16:
            self.cursor = self.end

    async def visit(self, request):
        store, role = self.store, request['role']
        command = self.selected[role]
        child, readers, captures = None, [], [bytearray(), bytearray()]
        overflow = asyncio.Event()
        result = {'effect_state': 'UNKNOWN', 'meaning': 'original custodian intent/result remain required'}
        state, end = 'unknown', None

        async def capture(stream, target):
            while True:
                block = await stream.read(4096)
                if not block:
                    return
                room = CAPTURE - len(target)
                target.extend(block[:room])
                if len(block) > room:
                    overflow.set()
                    return  # Main loop terminates only its owned child.

        try:
            self.authorize({role})
            child = await asyncio.create_subprocess_exec(*command['argv'], stdin=asyncio.subprocess.PIPE,
                         stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            # Durable original PID before ANY wait, communicate or response read.
            with store.tx():
                store.db.execute("UPDATE custodian_visits SET state='running',pid=? WHERE id=?", (child.pid, request['visit']))
            readers = [asyncio.create_task(capture(child.stdout, captures[0])),
                       asyncio.create_task(capture(child.stderr, captures[1]))]
            deadline = asyncio.get_running_loop().time() + command['timeout_seconds']
            child.stdin.write((encode(request) + '\n').encode())
            await asyncio.wait_for(child.stdin.drain(), command['timeout_seconds'])
            child.stdin.close()
            while child.returncode is None and not overflow.is_set():
                if asyncio.get_running_loop().time() >= deadline:
                    result['timeout'] = True
                    break
                await asyncio.sleep(.01)
        except BaseException as exc:
            result['error'] = type(exc).__name__ + ': ' + str(exc)[:1000]
        finally:
            if child is not None:
                if child.returncode is None:
                    try:
                        child.terminate()
                    except ProcessLookupError:
                        pass
                    until = asyncio.get_running_loop().time() + 1
                    while child.returncode is None and asyncio.get_running_loop().time() < until:
                        await asyncio.sleep(.01)
                    if child.returncode is None:
                        try:
                            child.kill()
                        except ProcessLookupError:
                            pass
                    while child.returncode is None:
                        await asyncio.sleep(.01)
                end = await child.wait()  # Original watcher numeric END, before pipe completion.
                # END is retained separately even if a descendant holds a pipe.
                with store.tx():
                    store.db.execute('UPDATE custodian_visits SET ended=?,numeric_end=? WHERE id=?',
                                     (store.clock(), end, request['visit']))
                try:
                    await asyncio.wait_for(asyncio.gather(*readers), 1)
                except (asyncio.TimeoutError, asyncio.CancelledError):
                    result['pipes'] = 'incomplete; descendant/pipe ownership UNKNOWN'
            result.update(numeric_end=end, capture_overflow=overflow.is_set(),
                          stdout_b64=base64.b64encode(captures[0]).decode(),
                          stderr_b64=base64.b64encode(captures[1]).decode())
            if end == 0 and not overflow.is_set() and not any(k in result for k in ('error', 'timeout', 'pipes')):
                try:
                    answer = parse_json(captures[0].decode())
                    if (not isinstance(answer, dict) or set(answer) != {'visit', 'owner', 'basis', 'status', 'effect_state', 'intent_reference', 'result_reference'}
                            or any(answer[k] != request[k] for k in ('visit', 'owner', 'basis'))
                            or (answer['status'], answer['effect_state']) not in {('held', 'not-attempted'), ('progressed', 'completed')}):
                        raise Refusal('exact owner/visit/basis and accountable effect disposition required')
                    for key in ('intent_reference', 'result_reference'):
                        required_text(answer[key], 'genuine durable custodian ' + key, 4000)
                    result['owner_result'] = answer
                    state = 'held' if answer['status'] == 'held' else 'done'
                except (Refusal, ValueError, UnicodeError) as exc:
                    result['error'] = str(exc)
            with store.tx():
                store.db.execute('UPDATE custodian_visits SET state=?,result=?,next_at=? WHERE id=?',
                                 (state, encode(result), store.clock() + store.config.get('recheck_seconds', 1), request['visit']))
            if state == 'unknown':
                store.record_operational_error('custodian-visit:' + request['visit'],
                    {'occurrence': request['occurrence'], 'reason': 'unknown visit; actual owner retains original effect intent/result; no replay'}, role, 'custodian-unknown')

    async def close(self):
        # Each bounded visit collects its own child. Do not infer END from files.
        roles = list(self.active)
        results = await asyncio.gather(*(self.active[r] for r in roles), return_exceptions=True)
        for role, result in zip(roles, results):
            if isinstance(result, BaseException):
                self.store.record_operational_error('custodian-worker:' + role,
                    {'reason': type(result).__name__ + ': ' + str(result)[:1000]}, role, 'custodian-unknown')
