"""Current-contract1085 offline construction, collection and separate readback.

Declared roles: orchestration, validator, accessor, parser, formatter.
No historical fixture identity is manufactured; no runtime authority is issued.
"""
from contextlib import ExitStack
import hashlib
import json
import os
from pathlib import Path
import selectors
import sqlite3
import stat
import subprocess
import time

VERSION = 'current-contract1085-v1'
# These are complete modules/classes, selected from obligations before execution.
# A caller cannot replace this floor with a smaller green selection.
PROTECTIONS = {
    'source-package-tools': ['test_release_acquisition673', 'test_source_selection707',
                             'test_configuration308', 'test_current_qualification1085'],
    'genuine-history-and-lineage': ['test_portable_history1065', 'test_historical_verification1041'],
    'independent-current-authority': ['test_historical_admission1057', 'test_processing188',
                                      'test_processing194', 'test_processing206'],
    'retained-resources-and-capacity': ['test_capacity48', 'test_bounded311', 'test_retained168',
                                       'test_retained329', 'test_windows76'],
    'collection-and-currentness': ['test_post_await_admission743', 'test_ordinary_boundaries749', 'test_current_collection1093', 'test_current_relationships1098'],
    'independent-same-package-receivers': ['test_qa_branch672'],
    'whole-owned-lifecycle': ['test_oneoff1077.Recovery', 'test_correction1092', 'test_collection1114'],
    'ordinary-journal-failure-and-finite-progress': ['test_final_composition1107'],
}
SELECTORS = sorted({s for group in PROTECTIONS.values() for s in group})
HISTORICAL_UNSELECTED = {
    'test_windows76.Controls.test_recurring_worker_fair_held_prefix_and_cli_wiring':
        '1093/1107 finite eligible progress contract has no two-visit stride; original failed0/16 unchanged; '
        'test_final_composition1107.FiniteFairness1107.test_full_finite_backlog_original_END_conservation_and_CLI '
        'covers complete finite membership, original numeric END, held state, conserved rows and CLI wiring',
}
SEAMS = ['fictional principals, Board membership, clocks and native/model/collector receipts',
         'NULL-native configuration/schema and pool allocation in existing test fixtures',
         'owned release copies measured by production release(); semantic approval is fictional',
         'support.fixture_publication uses four public Board files and tracked fictional retention',
         'tiny owned Git repositories where the selected ordinary contract requires Git; candidate has no Git',
         'windows76 current adapter supplies fresh fixture arguments and calls its explicit imports initializer; not its original direct-main invocation',
         'no actual installed eligibility, custodian entitlement, QA/Branch acceptance or processing completion']


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(body):
    return hashlib.sha256(body).hexdigest()


def pin(path):
    p = Path(path)
    require(not p.is_symlink(), 'symlink input')
    s = p.stat()
    require(stat.S_ISREG(s.st_mode), 'ordinary input required')
    body = p.read_bytes()
    require(len(body) == s.st_size, 'changing input')
    return dict(bytes=len(body), sha256=sha(body))


def write(path, value):
    with Path(path).open('x') as stream:
        stream.write(json.dumps(value, sort_keys=True, indent=2)+'\n')


def relative(name):
    p = Path(name)
    require(not p.is_absolute() and str(p) == name and '..' not in p.parts, 'relative path required')
    require(not {'.git', 'WORK_LOG.md', 'AGENTS.md', 'runs', 'captures', '__pycache__'}.intersection(p.parts),
            'excluded input namespace')
    return p


def verify_files(root, files):
    for name, expected in files.items():
        require(pin(Path(root)/relative(name)) == expected, 'source/input mismatch: '+name)


def footprint(root):
    """Only a proven-owned fresh attempt; symlink targets are never followed."""
    pending, count, total = [Path(root)], 0, 0
    while pending:
        path = pending.pop()
        s = path.lstat()
        require(s.st_uid == os.getuid(), 'foreign owned-output entry')
        count += 1
        total += s.st_size
        pending.extend(directory_children(path, s.st_mode))
    return dict(entries=count, logical_bytes=total)


def directory_children(path, mode):
    return list(path.iterdir()) if stat.S_ISDIR(mode) else []


def resources(m):
    scope = footprint(m['area'])
    require(scope['entries'] <= m['limits']['entries'] and scope['logical_bytes'] <= m['limits']['bytes'],
            'retained cumulative attempt exceeds admission')
    v = os.statvfs(m['area'])
    require(v.f_bavail*v.f_frsize >= 100*1024**3 and v.f_favail >= 1000000,
            'OS capacity floor lost')
    return scope


def entry_text(role, directory, expected):
    func = {'command': 'execute', 'readback': 'readback'}[role]
    return ('import sys\nif len(sys.argv)!=1: raise SystemExit("no runner arguments")\n'
            'from procedure import '+func+'\n'+func+'('+repr(str(directory))+', '+repr(expected)+')\n')


def command_bindings(m, expected):
    commands = {}
    for role in ('command', 'readback'):
        script = Path(m['instance'])/(role+'_entry.py')
        commands[role] = dict(argv=['/usr/bin/python3.12', '-B', str(script)],
                              executable_sha256=m['tools']['/usr/bin/python3.12']['sha256'],
                              script_sha256=sha(entry_text(role, m['instance'], expected).encode()),
                              stdout=('current1085 command collected; separate readback required\n' if role == 'command' else
                                      'current1093: complete selected tests; dedicated retained file/SQLite witness verified; other fixture observations remain separate\n'))
    commands['public_executables'] = {role: {'path': '/usr/bin/python3.12',
                                            **m['tools']['/usr/bin/python3.12']}
                                       for role in ('command', 'readback')}
    return commands


def verify_commands(m, expected):
    d = Path(m['instance'])
    commands = command_bindings(m, expected)
    require(json.loads((d/'COMMANDS.json').read_text()) == commands, 'derived command binding changed')
    for role in ('command', 'readback'):
        command = commands[role]
        require(pin(d/(role+'_entry.py'))['sha256'] == command['script_sha256'], 'derived entry binding changed')


def prepare(spec):
    required = {'candidate', 'identity', 'files', 'area', 'instance', 'output', 'tools', 'limits',
                'authority_basis', 'history_disposition', 'coverage_rationale'}
    require(set(spec) == required, 'complete current constructor fields required')
    require(set(spec['coverage_rationale']) == set(PROTECTIONS), 'every continuing protection needs independent rationale')
    require(all(spec['coverage_rationale'].values()), 'empty protection rationale')
    require(spec['authority_basis'] and spec['history_disposition'], 'current authority and truthful history required')
    require(set(spec['identity']) == {'origin', 'ref', 'head', 'tree', 'parents', 'method'}, 'exact current identity required')
    require(all(spec['identity'].values()), 'missing current provenance')
    c, area, d, out = [Path(spec[k]) for k in ('candidate', 'area', 'instance', 'output')]
    require(all(p.is_absolute() and not p.is_symlink() for p in (c, area, d, out)), 'absolute plain roots required')
    require(c.is_relative_to(area) and d.is_relative_to(area) and out.is_relative_to(area), 'owned attempt roots required')
    require(c != d and c != out and d != out and not out.is_relative_to(c) and not d.is_relative_to(c), 'overlapping roots')
    require(not (c/'.git').exists() and not d.exists() and not out.exists(), 'fresh noGit construction required')
    require(set(spec['tools']) == {'/usr/bin/python3.12', '/usr/bin/bwrap', '/usr/bin/git'}, 'exact public tools required')
    verify_files('/', {p.lstrip('/'): v for p, v in spec['tools'].items()})
    verify_files(c, spec['files'])
    modules = [p for p in spec['files'] if Path(p).parent.as_posix() == 'tools/coordinator-runtime/coordinator_runtime'
               and p.endswith('.py')]
    require(modules and 'tools/coordinator-runtime/coordinator_runtime/historical_admission.py' in modules,
            'complete growing runtime required')
    for name in SELECTORS:
        require('tools/coordinator-runtime/tests/'+name.split('.')[0]+'.py' in spec['files'], 'missing protection input: '+name)
    require(set(spec['limits']) == {'seconds', 'capture_bytes', 'bytes', 'entries'}, 'exact finite admission required')
    require(all(type(n) is int and n > 0 for n in spec['limits'].values()), 'positive finite limits required')
    resources(spec)
    d.mkdir(mode=0o700)
    (d/'sdk').mkdir()
    for name in ('active_listener.py', 'queue_transport.py', 'catalog.py', 'board_store.py'):
        (d/'sdk'/name).write_bytes((c/'tools/message-board'/name).read_bytes())
    (d/'sdk/retention.py').write_bytes((c/'tools/coordinator-runtime/tests/fixture_snapshot/retention.py').read_bytes())
    for name in ('procedure.py', 'worker.py'):
        (d/name).write_bytes(Path(__file__).with_name(name).read_bytes())
    m = {**spec, 'version': VERSION, 'selectors': SELECTORS, 'protections': PROTECTIONS, 'seams': SEAMS,
         'run_id': os.urandom(16).hex(), 'runtime_modules': modules}
    m['scripts'] = {name: pin(d/name) for name in ('procedure.py', 'worker.py')}
    m['sdk'] = {p.name: pin(p) for p in (d/'sdk').iterdir()}
    write(d/'manifest.json', m)
    mh = sha((d/'manifest.json').read_bytes())
    for role in ('command', 'readback'):
        script = d/(role+'_entry.py')
        script.write_text(entry_text(role, d, mh))
    commands = command_bindings(m, mh)
    write(d/'COMMANDS.json', commands)
    write(d/'BINDING.json', {'manifest': mh, 'commands': pin(d/'COMMANDS.json'),
                            'entries': {r: pin(d/(r+'_entry.py')) for r in ('command', 'readback')}})
    return commands


def load(directory, expected):
    d = Path(directory)
    require(sha((d/'manifest.json').read_bytes()) == expected, 'manifest binding changed')
    m = json.loads((d/'manifest.json').read_text())
    require(m['version'] == VERSION and m['instance'] == str(d), 'wrong current procedure')
    require(m['selectors'] == SELECTORS and m['protections'] == PROTECTIONS, 'current protection floor changed')
    require(Path.cwd() == Path(m['candidate']) and not (Path.cwd()/'.git').exists(), 'actual noGit candidate CWD required')
    verify_files(m['candidate'], m['files'])
    verify_files(d, m['scripts'])
    verify_files(d/'sdk', m['sdk'])
    verify_files('/', {p.lstrip('/'): v for p, v in m['tools'].items()})
    verify_commands(m, expected)
    binding = json.loads((d/'BINDING.json').read_text())
    require(binding['manifest'] == expected and binding['commands'] == pin(d/'COMMANDS.json'), 'command binding changed')
    for role in ('command', 'readback'):
        require(binding['entries'][role] == pin(d/(role+'_entry.py')), 'entry binding changed')
    return m


def sandbox(m):
    c, d = m['candidate'], m['instance']
    argv = ['/usr/bin/bwrap', '--die-with-parent', '--unshare-all', '--new-session', '--tmpfs', '/']
    for p in ('/usr', '/bin', '/lib', '/lib64'):
        argv += ['--ro-bind', p, p]
    argv += ['--proc', '/proc', '--dev', '/dev', '--ro-bind', c, c, '--ro-bind', c, '/src',
             '--ro-bind', c, '/actualsrc', '--ro-bind', d, d, '--ro-bind', d, '/procedure', '--ro-bind', d+'/sdk', '/sdk',
             '--bind', m['output'], '/fixtures', '--dir', '/tmp', '--dir', '/home', '--clearenv']
    env = dict(PATH='/usr/bin:/bin', HOME='/fixtures/home', XDG_CONFIG_HOME='/fixtures/config', TMPDIR='/fixtures/tmp', PYTHONDONTWRITEBYTECODE='1',
               QA629_FIXTURES='/fixtures/cases', RFQ673_FIXTURES='/fixtures/releases',
               CAPACITY48_FIXTURES='/fixtures/capacity48',
               COORDINATOR_ORDINARY_FIXTURES='/fixtures/ordinary-effects33', COORDINATOR_TEST_BOARD_LIBRARY='/src/tools/message-board',
               PYTHONPATH='/procedure:/sdk:/src/tools/coordinator-runtime:/src/tools/coordinator-runtime/tests')
    for key, value in env.items():
        argv += ['--setenv', key, value]
    # Only the explicitly bound effects mount is writable; synthetic root
    # ancestors are structure, not an additional write grant.
    return argv+['--remount-ro', '/', '--chdir', c, '/usr/bin/python3.12', '-B', '/procedure/worker.py']


def terminate_owned(proc):
    try:
        proc.terminate()
    except ProcessLookupError:
        pass  # An already exited original still requires wait().


def kill_owned(proc):
    try:
        proc.kill()
    except ProcessLookupError:
        pass


def stop(proc):
    # Only the directly owned foreground subprocess; finite collection tail.
    terminate_owned(proc)
    try:
        return proc.wait(timeout=3)
    except subprocess.TimeoutExpired:
        kill_owned(proc)
    return proc.wait(timeout=5)


def capture_owned(proc, out, record, deadline, maximum):
    # ExitStack closes every acquired resource, including partial setup. Its
    # exceptions return to collect(), whose child responsibility already exists.
    with ExitStack() as closing:
        closing.callback(proc.stdout.close)
        ready = closing.enter_context(selectors.DefaultSelector())
        ready.register(proc.stdout, selectors.EVENT_READ)
        stream = closing.enter_context((out/'transcript.txt').open('xb'))
        drain(proc, ready, stream, record, deadline, maximum)


def collection_failure(record, stage, exc):
    record['reason'] = record['reason'] or stage+' failure: '+type(exc).__name__+': '+str(exc)
    record.setdefault('failures', []).append(dict(stage=stage, type=type(exc).__name__, message=str(exc)))


def finish_owned(proc, record, start, seconds):
    try:
        finish_collection(proc, record, start, seconds)
    except BaseException as exc:
        collection_failure(record, 'collection', exc)
        retry_owned_stop(proc, record)


def retry_owned_stop(proc, record):
    try:
        record['exit'] = stop(proc)
    except BaseException as exc:
        # No inferred END: a failed original collection remains explicit debt.
        collection_failure(record, 'collection-retry', exc)


def capture_digest(out, record):
    try:
        record['transcript_sha256'] = sha((out/'transcript.txt').read_bytes())
    except BaseException as exc:
        record['transcript_sha256'] = None
        collection_failure(record, 'capture-readback', exc)


def collect(argv, out, seconds, maximum):
    start = time.monotonic()
    record = dict(argv=argv, exit=None, complete=False, reason=None, observed_bytes=0, retained_bytes=0,
                  launched=False, pid=None)
    proc = None
    try:
        proc = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        record.update(launched=True, pid=proc.pid)
        capture_owned(proc, out, record, start+seconds, maximum)
    except BaseException as exc:
        collection_failure(record, 'launch' if proc is None else 'capture', exc)
    finally:
        finish_if_launched(proc, record, start, seconds)
    record['seconds'] = time.monotonic()-start
    capture_digest(out, record)
    record['complete'] = (record['reason'] is None and record['exit'] is not None
                          and record['observed_bytes'] == record['retained_bytes'])
    return record


def finish_if_launched(proc, record, start, seconds):
    if proc is not None:
        finish_owned(proc, record, start, seconds)


def drain(proc, ready, stream, r, deadline, maximum):
    finished = False
    while not finished and time.monotonic() < deadline:
        finished = retain_capture_body(next_body(ready), stream, r, maximum)
    if not finished:
        r['reason'] = 'whole-command deadline'


def retain_capture_body(body, stream, record, maximum):
    if body is None:
        return False
    if body == b'':
        return True
    record['observed_bytes'] += len(body)
    kept = body[:maximum-record['retained_bytes']]
    stream.write(kept)
    record['retained_bytes'] += len(kept)
    if len(kept) == len(body):
        return False
    record['reason'] = 'capture overflow; retained prefix incomplete'
    return True


def next_body(ready):
    events = ready.select(.1)
    return os.read(events[0][0].fd, 65536) if events else None


def finish_collection(proc, r, start, seconds):
    if r['reason'] is not None:
        r['exit'] = stop(proc)
        return
    try:
        r['exit'] = proc.wait(timeout=max(.01, start+seconds-time.monotonic()))
    except subprocess.TimeoutExpired:
        r['reason'] = 'whole-command deadline after EOF'
        r['exit'] = stop(proc)


def execute(directory, expected):
    m = load(directory, expected)
    resources(m)
    out = Path(m['output'])
    out.mkdir(mode=0o700)
    write(out/'OWNER.json', dict(run_id=m['run_id'], manifest=expected))
    for name in ('tmp', 'home', 'config', 'cases', 'releases'):
        (out/name).mkdir()
    record = collect(sandbox(m), out, m['limits']['seconds'], m['limits']['capture_bytes'])
    record.update(run_id=m['run_id'], manifest=expected)
    write(out/'execution.json', record)
    load(directory, expected)
    write(out/'resources.json', resources(m))
    require(record['exit'] == 0 and record['complete'], 'failed/incomplete current execution; retain all output')
    print('current1085 command collected; separate readback required')


def validate_outcomes(m, r, events, expected):
    require(r['run_id'] == m['run_id'] and r['manifest'] == expected and r['argv'] == sandbox(m), 'stale execution binding')
    require(r['exit'] == 0 and r['complete'] is True and r['reason'] is None, 'failed/incomplete actual execution')
    require(events and events[0]['kind'] == 'scope' and events[-1]['kind'] == 'finish', 'incomplete events')
    ids = events[0]['ids']
    require(ids and len(ids) == len(set(ids)), 'missing/duplicate selected IDs')
    require(events[0]['selectors'] == SELECTORS, 'incomplete current protection selection')
    require(events[0].get('historical_unselected') == HISTORICAL_UNSELECTED, 'unbound historical applicability disposition')
    require([e['id'] for e in events if e['kind'] == 'start'] == ids, 'missing/duplicate actual starts')
    require([e['id'] for e in events if e['kind'] == 'success'] == ids, 'failures/errors/skips/unexecuted controls')
    require(len(events) == 2+2*len(ids) and events[-1]['tests'] == len(ids), 'incomplete or extra outcomes')
    require(set(events[-1]['runtime_modules']) == set(m['runtime_modules']), 'incomplete current runtime import closure')
    return ids


def database_readback(path):
    for suffix in ('-wal', '-shm', '-journal'):
        side = Path(str(path)+suffix)
        require(not side.is_symlink(), 'linked SQLite sidecar refused before target metadata')
        require(not side.exists() or side.stat().st_size == 0, 'nonempty retained SQLite sidecar: '+str(side))
    with sqlite3.connect(path.as_uri()+'?mode=ro&immutable=1', uri=True) as db:
        require(db.execute('PRAGMA quick_check').fetchall() == [('ok',)], 'retained SQLite corruption')
    return dict(path=str(path), quick_check='ok')


def retained_entries(root):
    pending = [root]
    while pending:
        path = pending.pop()
        mode = path.lstat().st_mode
        pending.extend(directory_children(path, mode))
        yield path, mode


def retained_databases(root):
    return [observe_database(path) for path, mode in retained_entries(root)
            if stat.S_ISREG(mode) and path.suffix in {'.sqlite3', '.db'}]


def observe_database(path):
    try:
        return database_readback(path)
    except (ValueError, sqlite3.DatabaseError) as exc:
        return dict(path=str(path), unresolved=str(exc))


def dedicated_witness(out):
    require((out/'current-oracle/original.txt').read_bytes() == b'current original retained\n', 'lost original file')
    database = out/'current-oracle/state/runtime.sqlite3'
    database_readback(database)
    with sqlite3.connect(database.as_uri()+'?mode=ro&immutable=1', uri=True) as db:
        rows = db.execute('SELECT role,state,ack,processed_at FROM events').fetchall()
    require(rows == [('Work', 'received', 'pending', None)], 'retention/backpressure or processing changed')
    return dict(verified=True, claim='dedicated original file and SQLite row only',
                actual_acceptance=False, processing_completion=False)


def observe_witness(out):
    try:
        return dedicated_witness(out)
    except (OSError, ValueError, sqlite3.DatabaseError) as exc:
        return dict(verified=False, unresolved=str(exc))


def readback(directory, expected):
    m = load(directory, expected)
    out = Path(m['output'])
    require(json.loads((out/'OWNER.json').read_text()) == dict(run_id=m['run_id'], manifest=expected), 'wrong output owner')
    r = json.loads((out/'execution.json').read_text())
    body = (out/'transcript.txt').read_bytes()
    require(len(body) == r['observed_bytes'] == r['retained_bytes'] and sha(body) == r['transcript_sha256'], 'incomplete/changed capture')
    events = [json.loads(line) for line in (out/'events.jsonl').read_text().splitlines()]
    # Retain failure-conscious independent observations even when execution
    # cannot satisfy the success gate. No journal checkpoint or deletion.
    witness = observe_witness(out)
    write(out/'EFFECT-OBSERVATION.json', dict(resources=resources(m), databases=retained_databases(out),
          dedicated_witness=witness,
          selected=events[0]['ids'] if events and events[0]['kind'] == 'scope' else [],
          starts=[e['id'] for e in events if e['kind'] == 'start'],
          outcomes=[e for e in events if e['kind'] in {'success', 'error', 'failure', 'skip',
                                                     'expected-failure', 'unexpected-success'}],
          execution_exit=r['exit'], complete=r['complete']))
    ids = validate_outcomes(m, r, events, expected)
    require(witness['verified'], 'dedicated retained witness unresolved')
    write(out/'READBACK.json', dict(version=VERSION, ids=ids, resources=resources(m), file_and_SQLite_oracle=True,
                                   readback_claim='dedicated original file and SQLite row only; EFFECT-OBSERVATION retains other unresolved fixture states',
                                   actual_acceptance=False, processing_completion=False))
    print('current1093: complete selected tests; dedicated retained file/SQLite witness verified; other fixture observations remain separate')
