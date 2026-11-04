"""Targeted production capacity/broker controls on explicit fictional fixtures.

Direct execution requires a fresh, explicit writable root. No account, profile,
provider, Board or shared journal is opened. Budget/authority inputs are fictional;
production capacity and Service methods are imported unchanged. Store/Delivery
schemas are parsed as literals, not imported. Every fixture and SQL trace stays.
"""
import ast
import asyncio
from contextlib import contextmanager
import json
import os
from pathlib import Path
import resource
import sqlite3
import sys

# Positive mount evidence and a kernel refusal precede production imports.
mounts = Path('/proc/self/mountinfo').read_text()
assert any(' /src ' in line and 'ro' in line.split(' - ')[0].split()[5].split(',') for line in mounts.splitlines())
try:
    descriptor = os.open('/src/coordinator_runtime/capacity.py', os.O_WRONLY)
except OSError as exc:
    assert exc.errno == 30, exc  # EROFS; no source byte was changed.
else:
    os.close(descriptor)
    raise AssertionError('source is not kernel read-only')
assert not Path('/home/nes').exists()
print('KERNEL_RO_BEFORE_IMPORT', flush=True)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from coordinator_runtime import capacity, custodian_service
from coordinator_runtime.contracts import Backpressure, Refusal, encode, digest

ROOT = Path(sys.argv[1]).resolve()
assert ROOT.is_dir() and not any(ROOT.iterdir()), 'explicit fresh fixture root required'
SOURCE = Path(__file__).resolve().parents[1] / 'coordinator_runtime'
ACCOUNT = ROOT / 'accounting.jsonl'
RETAINED = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {'files':0,'bytes':0,'allocated':0}


def census():
    files = [p for p in ROOT.rglob('*') if p.is_file()]
    return {'files': len(files), 'bytes': sum(p.stat().st_size for p in files),
            'allocated': sum(p.stat().st_blocks * 512 for p in files)}


def headroom(label):
    current = census()
    used = {key: current[key] + RETAINED[key] for key in ('files','bytes','allocated')}
    available = os.statvfs(ROOT).f_bavail * os.statvfs(ROOT).f_frsize
    memory = int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines()
                      if line.startswith('MemAvailable:'))) * 1024
    record = {'before': label, **used, 'retained_previous_roots': RETAINED, 'free': available, 'MemAvailable': memory,
              'planned_max_bytes': 2097152, 'planned_max_files': 16}
    with ACCOUNT.open('a') as out:
        out.write(encode(record) + '\n')
    assert max(used['bytes'], used['allocated']) + 2097152 < 67108864
    assert used['files'] + 16 < 2000
    assert available >= 40 * 1024**3 and memory >= 4 * 1024**3


def schema(name):
    module = ast.parse((SOURCE / name).read_text())
    return next(ast.literal_eval(n.value) for n in module.body
                if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'SCHEMA' for t in n.targets))


ADAPTER = """import json,sys,time
r=json.load(sys.stdin)
if r['occurrence'].endswith('-timeout'): time.sleep(2)
else:
 print(json.dumps({k:r[k] for k in ('visit','owner','basis')} | {
  'status':'held','effect_state':'not-attempted',
  'intent_reference':'fictional:no-effect-intent','result_reference':'fictional:held-result'}))
"""


class Fixture:
    def __init__(self, name, roles=('Work',)):
        headroom(name)
        self.root = ROOT / name
        self.root.mkdir()
        self.trace = (self.root / 'sql.txt').open('w')
        self.db = sqlite3.connect(self.root / 'fictional.sqlite', isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.set_trace_callback(lambda statement: (self.trace.write(statement+'\n'), self.trace.flush()))
        # PERSIST retains its journal file; FULL durability on this own fixture.
        # This is not a WAL or crash-recovery qualification.
        self.db.execute('PRAGMA journal_mode=PERSIST')
        self.db.execute('PRAGMA synchronous=FULL')
        self.db.executescript(schema('store.py') + schema('delivery.py') + capacity.SCHEMA + custodian_service.SCHEMA)
        self.now = 100.0
        self.population = [{'subject':'fictional-duty','kind':'stale'}]
        self.byte_calls = 0
        self.fail_byte_at = None
        adapter = self.root / 'adapter.py'
        adapter.write_text(ADAPTER)
        self.config = {'actor':'fictional-producer', 'roles':{r:{'owner':'fictional-'+r} for r in roles},
                       'limits':{'max_alerts':1,'max_alert_debt':1}, 'deadlines':{'alert_interval':10},
                       'recheck_seconds':1,
                       'custodian_service':{r:{'argv':['/usr/bin/python3',str(adapter)],
                                              'authority':'fictional isolated no-effect control',
                                              'timeout_seconds':.2} for r in roles}}

    def clock(self):
        return self.now

    @contextmanager
    def tx(self):
        self.db.execute('BEGIN IMMEDIATE')
        try:
            yield
            self.db.execute('COMMIT')
        except BaseException:
            self.db.execute('ROLLBACK')
            raise

    def one(self, sql, values=()):
        row = self.db.execute(sql, values).fetchone()
        return dict(row) if row else None

    def rows(self, sql, values=()):
        return [dict(row) for row in self.db.execute(sql, values)]

    def enrollment(self, role):
        return {'owner':self.config['roles'][role]['owner']}

    def violations(self):
        return self.population

    def budget(self, kind, incoming=0):
        if kind == 'alerts' and self.one('SELECT COUNT(*) AS n FROM alerts')['n'] >= self.config['limits']['max_alerts']:
            raise Backpressure('fictional alert bound')
        if kind is None:
            self.byte_calls += 1
            if self.fail_byte_at == self.byte_calls:
                raise Backpressure('fictional reserved-byte boundary')

    def record_operational_error(self, subject, detail, role='Work', kind='runtime'):
        with self.tx():
            self.db.execute('INSERT OR REPLACE INTO operational_errors VALUES(?,?,?,?,1,?)',
                            (subject, role, kind, encode(detail), self.now))

    def add(self, occurrence, role='Work', linked=True):
        self.db.execute('INSERT INTO alerts VALUES(?,?,?,?,?,NULL)', (occurrence, occurrence, 'stale', self.now, '{}'))
        if linked:
            self.db.execute('INSERT INTO outboxes(id,role,alert,producer,recipient,kind,required,payload,created) '
                            "VALUES(?,?,?,?,?,'alert','settled','{}',?)",
                            ('out-'+occurrence,role,occurrence,'fictional-producer',role,self.now))

    def snapshot(self, name):
        tables = [r['name'] for r in self.rows("SELECT name FROM sqlite_master WHERE type='table'")]
        data = {t:self.rows('SELECT * FROM '+t) for t in tables}
        (self.root / (name+'.json')).write_text(encode(data)+'\n')
        return data

    def finish(self):
        self.snapshot('after')
        self.db.close()
        self.trace.close()


def refusal(fn):
    try:
        fn()
    except Refusal as exc:
        return exc
    raise AssertionError('expected refusal')


def pressure():
    s = Fixture('pressure')
    try:
        s.snapshot('before')
        first = capacity.capture(s)
        assert len(first) == 1
        assert capacity.capture(s) == []  # Same sample is not a new due occurrence.
        s.now = 110
        assert capacity.capture(s) == []
        debt = s.rows('SELECT * FROM alert_debt')
        assert len(debt) == 1 and json.loads(debt[0]['payload'])['created'] == 110
        old = s.rows('SELECT * FROM alerts'), debt
        s.now = 120
        exc = refusal(lambda: capacity.capture(s))
        current = capacity.service(s)
        assert current['last_observed'] == 120 and current['gap_through'] == 120
        assert current['unrepresented'] == 2 and current['gap_since'] == 110
        assert current['latest'] == exc.observation
        assert exc.observation['representation'] == 'unavailable'
        assert exc.observation['due_count'] == 1 and exc.observation['custodian'] == 'fictional-Work'
        assert (s.rows('SELECT * FROM alerts'), s.rows('SELECT * FROM alert_debt')) == old
        assert s.one('SELECT last_created FROM alert_cadence')['last_created'] == 110
        # Durable readback via an independent connection, without a separate error write.
        with sqlite3.connect(s.root / 'fictional.sqlite') as reader:
            assert reader.execute('SELECT last_observed FROM alert_service').fetchone()[0] == 120
            assert json.loads(reader.execute("SELECT value FROM meta WHERE key='alert-observation'").fetchone()[0]) == exc.observation
        assert capacity.capture(s) == []  # Failure sample is durably throttled too.
        s.now = 130
        refusal(lambda: capacity.capture(s))
        assert capacity.service(s)['latest']['at'] == 130
        assert capacity.service(s)['unrepresented'] == 3
        s.population = []
        s.now = 140
        assert capacity.capture(s) == []
        current = capacity.service(s)
        assert current['latest']['due_count'] == 0 and current['gap_through'] == 130
        assert (s.rows('SELECT * FROM alerts'), s.rows('SELECT * FROM alert_debt')) == old
    finally:
        s.finish()


def partial_debt():
    s = Fixture('partial-debt')
    try:
        s.add('held-original')
        s.population = [{'subject':'fictional-A','kind':'stale'}, {'subject':'fictional-B','kind':'stale'}]
        s.config['limits']['max_alert_debt'] = 3
        s.fail_byte_at = 2
        before = s.snapshot('before')
        exc = refusal(lambda: capacity.capture(s))
        assert exc.observation['due_count'] == 2
        assert s.rows('SELECT * FROM alert_debt') == []  # No partial cohort/duplicate debt.
        assert s.rows('SELECT * FROM alerts') == before['alerts']
        assert capacity.service(s)['latest']['representation'] == 'unavailable'
        assert s.rows('SELECT * FROM alert_cadence') == []
    finally:
        s.finish()


def cohort_atomicity():
    s = Fixture('cohort-atomicity')
    try:
        s.population = [{'subject':'fictional-A','kind':'stale'}, {'subject':'fictional-B','kind':'stale'}]
        s.config['limits']['max_alert_debt'] = 2
        s.snapshot('before')
        assert capacity.capture(s) == []
        # Alert capacity admits the first member but refuses the second; the
        # entire cohort must move to exact debt with no partial alert insertion.
        assert s.rows('SELECT * FROM alerts') == []
        debt = s.rows('SELECT * FROM alert_debt ORDER BY subject')
        assert len(debt) == 2
        payloads = [json.loads(row['payload']) for row in debt]
        assert [r['subject'] for r in payloads] == ['fictional-A','fictional-B']
        assert all(r['created']==100 and r['id']==row['id'] for r,row in zip(payloads,debt))
        assert len({r['id'] for r in payloads}) == 2
        assert capacity.service(s)['latest']['representation'] == 'exact-debt'
        s.now = 110
        exc = refusal(lambda: capacity.capture(s))
        assert exc.observation['due_count'] == 2
        assert s.rows('SELECT * FROM alert_debt ORDER BY subject') == debt
        assert s.rows('SELECT * FROM alerts') == []
    finally:
        s.finish()


def recurring_exact():
    s = Fixture('recurring-exact')
    try:
        s.config['limits']['max_alerts'] = 5
        s.config['alert_cadences'] = {'stale':20}
        s.snapshot('before')
        occurrences = capacity.capture(s)
        s.now = 110
        assert capacity.capture(s) == []
        s.now = 120
        occurrences += capacity.capture(s)
        s.now = 150
        occurrences += capacity.capture(s)
        assert len({r['id'] for r in occurrences}) == 3
        assert [r['created'] for r in occurrences] == [100,120,150]
        assert capacity.service(s)['gap_since'] == 130  # No invented historical population.
    finally:
        s.finish()


async def fairness():
    s = Fixture('fairness17', ('Work','QA'))
    broker = custodian_service.Service(s, lambda roles: None)  # Explicit fake authority.
    try:
        for n in range(1,18):
            s.add('work-'+str(n))
        s.add('qa-1','QA')
        s.add('unlinked',linked=False)
        before = s.snapshot('before')
        for n in range(17):
            broker.schedule()
            assert len(broker.active) <= 2
            # Multiple busy schedules must not consume the role's future entries.
            frontiers = dict(broker.frontiers)
            for _ in range(3):
                broker.schedule()
            assert broker.frontiers == frontiers
            await broker.close()
            s.now += 2
        visits = s.rows("SELECT * FROM custodian_visits WHERE role='Work' ORDER BY rowid")
        assert [r['occurrence'] for r in visits] == ['work-'+str(n) for n in range(1,18)]
        assert all(r['state']=='held' and type(r['pid']) is int and r['numeric_end']==0 for r in visits)
        assert s.one("SELECT COUNT(*) AS n FROM custodian_visits WHERE role='QA'")['n'] > 0
        assert s.rows('SELECT * FROM alerts') == before['alerts']
        assert s.rows('SELECT * FROM outboxes') == before['outboxes']
        assert s.one("SELECT * FROM operational_errors WHERE subject='custodian-source:unlinked'")
        (s.root/'original-child-ends.json').write_text(encode(s.rows('SELECT id,pid,numeric_end,state FROM custodian_visits'))+'\n')
    finally:
        await broker.close()
        s.finish()


async def quarantine():
    s = Fixture('quarantine')
    broker = custodian_service.Service(s, lambda roles: None)
    try:
        s.add('work-timeout')
        s.add('later-held')
        before = s.snapshot('before')
        broker.schedule()
        await broker.close()
        first = s.one('SELECT * FROM custodian_visits')
        assert first['state']=='unknown' and first['numeric_end']==-15 and type(first['pid']) is int
        # Changed basis cannot authorize UNKNOWN replay; later duties still get attention.
        s.db.execute("UPDATE alerts SET payload='changed fictional basis' WHERE id='work-timeout'")
        for _ in range(4):
            s.now += 2
            broker.schedule()
            await broker.close()
        assert s.one("SELECT COUNT(*) AS n FROM custodian_visits WHERE occurrence='work-timeout'")['n']==1
        assert s.one("SELECT COUNT(*) AS n FROM custodian_visits WHERE occurrence='later-held'")['n']>0
        assert s.rows('SELECT * FROM outboxes') == before['outboxes']
        assert all(r['processed_at'] is None for r in s.rows('SELECT * FROM alerts'))
        (s.root/'original-child-ends.json').write_text(encode(s.rows('SELECT id,pid,numeric_end,state FROM custodian_visits'))+'\n')
    finally:
        await broker.close()
        s.finish()


async def owner_refusal():
    s = Fixture('owner-refusal')
    def deny(roles):
        raise Refusal('fictional missing authority')
    broker = custodian_service.Service(s, deny)
    try:
        s.add('held-no-authority')
        before = s.snapshot('before')
        broker.schedule()
        assert s.rows('SELECT * FROM custodian_visits') == []
        assert not broker.active
        assert s.rows('SELECT * FROM alerts') == before['alerts']
        assert s.one("SELECT * FROM operational_errors WHERE subject='custodian-source:held-no-authority'")
    finally:
        await broker.close()
        s.finish()


async def main():
    for test in (pressure, partial_debt, cohort_atomicity, recurring_exact):
        test()
        print('OK',test.__name__,flush=True)
    for test in (fairness, quarantine, owner_refusal):
        await test()
        print('OK',test.__name__,flush=True)
    print(encode({'resources':census(),'max_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}),flush=True)


if __name__ == '__main__':
    asyncio.run(main())
