"""Service-owned admitted effects, original tool collection and separate acceptance.

Intents precede tools. Interrupted/partial runs are never replayed. Leases and
resource keys are admitted authority, not a claim of an OS/network sandbox or
global resource ownership. Roles: validator, orchestration.
"""
import asyncio
import hashlib
import json
import os
from pathlib import Path
import re

from .contracts import Refusal, canonical_uuid, collected_task_result, digest, encode, scoped_task
from .custody import safe_path, read_file, guard_path
from . import prospective, qa_source

SCHEMA = """
CREATE TABLE IF NOT EXISTS ordinary_runs(
 attempt TEXT PRIMARY KEY,job TEXT NOT NULL,epoch TEXT NOT NULL,admission TEXT NOT NULL,
 policy TEXT NOT NULL,state TEXT NOT NULL,receipt TEXT);
CREATE TABLE IF NOT EXISTS ordinary_resources(resource TEXT PRIMARY KEY,attempt TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS ordinary_acceptance(
 attempt TEXT PRIMARY KEY,actor TEXT NOT NULL,decision TEXT NOT NULL,receipt TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS ordinary_tool_records(
 seq INTEGER PRIMARY KEY AUTOINCREMENT,attempt TEXT NOT NULL,record TEXT NOT NULL);
"""


def selected(store, job):
    row = prospective.for_job(store, job)
    if row and row['policy']['ordinary_effects']:
        return row
    return None


def scoped_path(store, path, roots):
    # Apply opaque exclusions before safe_path's metadata walk.
    if any(Path(path) == Path(p) or Path(path).is_relative_to(Path(p)) for p in store.config.get('artifact_exclusions', [])):
        raise Refusal('excluded ordinary-effect input before metadata')
    return safe_path(path, roots)


def frozen_file(store, path, roots, expected=None):
    guard_path(store, path)
    body, witness = read_file(scoped_path(store, path, roots), 4 * 1024 * 1024)
    if expected is not None and witness['sha256'] != expected:
        raise Refusal('admitted executable/procedure bytes changed')
    return body


def policy_for(store, job):
    admission = store.one('SELECT * FROM admissions WHERE package=?', (job['package'],))
    if job.get('id'):
        frozen = store.one('SELECT * FROM job_resource_policies WHERE job=?',(job['id'],))
        if frozen and (json.loads(frozen['task']) != store.config['tasks'][job['task']] or
                       (json.loads(frozen['admission']) if frozen['admission'] else None) != admission):
            raise Refusal('current admission/task cannot replace the frozen original job resource policy')
    task = scoped_task(job['task'], store.config['tasks'][job['task']], store.one('SELECT * FROM admissions WHERE package=?', (job['package'],)))
    scope = task['admitted_scope']
    p = scope.get('ordinary_effects', {})
    common = {'kind', 'git', 'git_sha256', 'repository', 'source_ref', 'source_head',
              'procedure_sha256', 'resources', 'acceptor', 'acceptance_authority', 'timeout', 'max_output'}
    extra = {'local-ref': {'ref', 'before', 'target'}, 'local-qa': {'command', 'readback', 'known_exits', 'source_capture'},
             'github-run': {'gh', 'gh_sha256', 'repository_slug', 'run_id', 'run_attempt', 'event', 'workflow', 'job_ids'}}
    if p.get('kind') not in extra or set(p) != common | extra.get(p.get('kind'), set()):
        raise Refusal('explicit supported ordinary procedure and complete exact operands required')
    text_fields = ['git', 'git_sha256', 'repository', 'source_ref', 'source_head', 'procedure_sha256', 'acceptor', 'acceptance_authority']
    if any(not isinstance(p[k], str) or not p[k] for k in text_fields):
        raise Refusal('complete typed ordinary source/tool/acceptance operands required')
    if (p['kind'] == 'local-ref') != (job['role'] == 'Branch') or job['phase'] not in {'integrator', 'execution'}:
        raise Refusal('ordinary adapter differs from admitted Branch/QA role')
    if type(p['timeout']) not in {int, float} or not 0 < p['timeout'] <= store.config['deadlines']['task']:
        raise Refusal('ordinary tool deadline exceeds selected task budget')
    if type(p['max_output']) is not int or not 1 <= p['max_output'] <= store.config['limits']['max_result_bytes']:
        raise Refusal('bounded complete tool capture required')
    canonical_uuid(p['acceptor'])
    if not p['acceptance_authority']:
        raise Refusal('independent authorized semantic acceptor required')
    if not re.fullmatch(r'[0-9a-f]{40}|[0-9a-f]{64}', p['source_head']):
        raise Refusal('exact source commit required')
    if not re.fullmatch(r'refs/(heads|tags)/[A-Za-z0-9_./-]+', p['source_ref']) or '..' in p['source_ref']:
        raise Refusal('explicit source ref required')
    roots = task['effect_authority']['read_roots'] + task['effect_authority']['write_roots']
    scoped_path(store, p['repository'], roots)
    if p['repository'] != task['cwd']:
        raise Refusal('admitted cwd must be the exact repository')
    frozen_file(store, scope['procedure'], roots, p['procedure_sha256'])
    # System tool bytes are explicitly selected; scripts must remain in scope.
    frozen_file(store, p['git'], [p['git']], p['git_sha256'])
    validate_resources(store, p)
    validate_adapter(store, task, p, roots)
    return task, p


def validate_resources(store, p):
    if not isinstance(p['resources'], list) or not 1 <= len(p['resources']) <= 16:
        raise Refusal('explicit bounded exclusive resource custody required')
    for resource in p['resources']:
        if (set(resource) != {'key', 'owner', 'authority', 'expires'} or not resource['key'] or not resource['authority']
                or type(resource['expires']) not in {int, float} or resource['expires'] <= store.clock()):
            raise Refusal('current admitted resource owner/authority/lease required')
        canonical_uuid(resource['owner'])


def command_policy(store, command, roots):
    if set(command) != {'argv', 'executable_sha256', 'stdout'} or not command['argv'] or not all(isinstance(a, str) for a in command['argv']):
        raise Refusal('exact argv/executable hash/readback oracle required; no shell interpolation')
    frozen_file(store, command['argv'][0], roots, command['executable_sha256'])


def validate_adapter(store, task, p, roots):
    if p['kind'] == 'local-ref':
        if task['network'] or p['ref'] == p['source_ref'] or p['target'] != p['source_head']:
            raise Refusal('local CAS ref adapter requires separate pinned source and no network')
        if not re.fullmatch(r'refs/heads/[A-Za-z0-9_./-]+', p['ref']) or '..' in p['ref'] or not re.fullmatch(r'[0-9a-f]{40}|[0-9a-f]{64}', p['before']):
            raise Refusal('exact existing destination ref/preimage required')
        scoped_path(store, p['repository'], task['effect_authority']['write_roots'])
    elif p['kind'] == 'local-qa':
        qa_source.validate(store, p)
        if task['network'] or p['known_exits'] != [0, 1]:
            raise Refusal('local QA supports admitted runner success/known failure only, no network')
        command_policy(store, p['command'], roots)
        command_policy(store, p['readback'], roots)
        if not p['readback']['stdout']:
            raise Refusal('independent procedure-specific resource/effect readback oracle required')
    else:
        if not task['network'] or not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', p['repository_slug']):
            raise Refusal('GitHub readback requires explicit scoped network/repository')
        if type(p['run_id']) is not int or p['run_id'] <= 0 or type(p['run_attempt']) is not int or p['run_attempt'] <= 0:
            raise Refusal('actual selected CI run and attempt required')
        if not isinstance(p['job_ids'], list) or not p['job_ids'] or len(p['job_ids']) > 100 or any(type(i) is not int or i <= 0 for i in p['job_ids']):
            raise Refusal('exact bounded CI job selection required')
        frozen_file(store, p['gh'], [p['gh']], p['gh_sha256'])


async def tool(store, attempt, label, argv, cwd, p, *, output_file=None, maximum=None):
    """Original subprocess and complete bounded capture, never caller JSON."""
    current_run = store.one('SELECT * FROM ordinary_runs WHERE attempt=?', (attempt,))
    current_job = store.job(current_run['job'])
    if not selected(store, current_job):
        raise Refusal('original prospective effect authority no longer current')
    prospective.board(store, current_job['role'])._software_job_grant(store, current_job)
    policy_for(store, current_job)
    admission = store.one('SELECT receipt FROM admissions WHERE package=?', (current_job['package'],))
    if digest(admission['receipt']) != current_run['admission']:
        raise Refusal('admission changed before actual tool invocation')
    env = None
    if argv[0] == p['git']:
        env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
        env.update(GIT_CONFIG_GLOBAL='/dev/null', GIT_CONFIG_NOSYSTEM='1', GIT_TERMINAL_PROMPT='0')
    process = await asyncio.create_subprocess_exec(*argv, cwd=cwd, env=env, stdin=asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    record = {'label': label, 'argv': argv, 'cwd': cwd, 'pid': process.pid, 'collector': store.controller,
              'started': store.clock(), 'exit': None, 'complete': False}
    append_tool(store, attempt, record)
    try:
        bound = p['max_output'] if maximum is None else maximum
        stdout, stderr = await asyncio.wait_for(capture_process(process, bound), p['timeout'])
        record.update(ended=store.clock(), exit=process.returncode)
        if len(stdout) + len(stderr) > bound:
            raise Refusal('ordinary capture exceeded bound')
        if output_file is not None:
            with Path(output_file).open('xb') as target:
                target.write(stdout)
            record.update(stdout_file=str(output_file), stdout_sha256=hashlib.sha256(stdout).hexdigest(),
                          stdout_bytes=len(stdout), stderr=stderr.decode('utf-8', 'strict'), complete=True)
        else:
            record.update(stdout=stdout.decode('utf-8', 'strict'), stderr=stderr.decode('utf-8', 'strict'), complete=True)
    except BaseException as exc:
        # The runner's observed END, capture completeness and effect settlement
        # are independent. Never fill an earlier missing END or replay an intent.
        settle = asyncio.create_task(stop_and_wait(process))
        try:
            code = await asyncio.shield(settle)
        except asyncio.CancelledError:
            code = await settle
        code = record['exit'] if record['exit'] is not None else code
        record.update(exit=code, complete=False, capture_error=type(exc).__name__ + ': ' + str(exc))
        if code is not None:
            record['ended'] = store.clock()
        append_tool(store, attempt, record)
        if isinstance(exc, asyncio.CancelledError):
            raise
        raise Refusal('ordinary tool/capture interrupted; original intent/resources retained, no automatic retry') from exc
    append_tool(store, attempt, record)
    return record


async def stop_and_wait(process):
    if process.returncode is None:
        try:
            process.kill()
        except ProcessLookupError:
            pass
    async def discard(stream):
        while await stream.read(65536):
            pass
    drains = [asyncio.create_task(discard(stream)) for stream in (process.stdout, process.stderr)]
    try:
        await asyncio.wait_for(asyncio.gather(*drains), 5)
        return await asyncio.wait_for(process.wait(), 5)
    except (asyncio.TimeoutError, OSError):
        return None  # Descendant-held pipes or unavailable terminal observation.
    finally:
        for task in drains:
            task.cancel()
        await asyncio.gather(*drains, return_exceptions=True)


async def bounded_stream(stream, maximum):
    chunks = bytearray()
    while True:
        block = await stream.read(min(65536, maximum + 1 - len(chunks)))
        if not block:
            return bytes(chunks)
        chunks.extend(block)
        if len(chunks) > maximum:
            raise Refusal('ordinary output exceeds admitted capture budget')


async def capture_process(process, maximum):
    readers = [asyncio.create_task(bounded_stream(stream, maximum)) for stream in (process.stdout, process.stderr)]
    try:
        stdout, stderr = await asyncio.gather(*readers)
        await process.wait()
        return stdout, stderr
    finally:
        for reader in readers:
            reader.cancel()
        await asyncio.gather(*readers, return_exceptions=True)


def append_tool(store, attempt, record):
    with store.tx():
        store.budget(None, len(encode(record).encode()) + 1024)
        store.db.execute('INSERT INTO ordinary_tool_records(attempt,record) VALUES(?,?)', (attempt, encode(record)))


async def git(store, attempt, p, *args):
    argv = [p['git'], '--no-optional-locks', '-c', 'gc.auto=0', '-c', 'maintenance.auto=false', '-c', 'core.hooksPath=/dev/null', '-C', p['repository'], *args]
    record = await tool(store, attempt, 'git', argv, p['repository'], p)
    if record['exit'] != 0:
        raise Refusal('actual git command failed; retain intent and original readback')
    return record['stdout'].strip()


async def source(store, attempt, p, task):
    # Linked worktrees must admit the actual common Git resource, not just cwd.
    roots = task['effect_authority']['read_roots'] + task['effect_authority']['write_roots']
    top = await git(store, attempt, p, 'rev-parse', '--show-toplevel')
    if top != p['repository']:
        raise Refusal('Git discovery must resolve the exact admitted repository cwd')
    git_dir = await git(store, attempt, p, 'rev-parse', '--path-format=absolute', '--git-common-dir')
    scoped_path(store, git_dir, task['effect_authority']['write_roots'] if p['kind'] == 'local-ref' else roots)
    head = await git(store, attempt, p, 'rev-parse', '--verify', p['source_ref'] + '^{commit}')
    if head != p['source_head']:
        raise Refusal('actual source ref is stale')
    tree = await git(store, attempt, p, 'rev-parse', '--verify', head + '^{tree}')
    origin = await git(store, attempt, p, 'remote', 'get-url', 'origin')
    parents = (await git(store, attempt, p, 'show', '-s', '--format=%P', head)).split()
    binding = task.get('admitted_scope', {}).get('branch_binding')
    branch = None
    if binding:
        from .branches import association
        branch = association(store, binding)
        job = store.job(store.one('SELECT job FROM ordinary_runs WHERE attempt=?', (attempt,))['job'])
        if branch['repository'] != p['repository'] or branch['origin'] != origin or branch['scope'] != job['package']:
            raise Refusal('ordinary source differs from exact accepted branch repository/origin/scope')
    info = scoped_path(store, git_dir, roots).stat()
    return {'head': head, 'tree': tree, 'ALLparents': parents, 'origin': origin, 'fullref': p['source_ref'],
            'branch': {k: branch[k] for k in ('id','ref','incarnation','scope','root','accepted')} if branch else None, 'git_common_dir': git_dir,
            'common_repository': {'dev':info.st_dev,'ino':info.st_ino}}


async def perform(store, board, job):
    store.require_execution_open(job['id'])
    epoch = selected(store, job)
    if not epoch:
        return False
    attempt = store.attempt(job['active_attempt'])
    prior = store.one('SELECT * FROM ordinary_runs WHERE attempt=?', (attempt['id'],))
    if prior:
        if prior['state'] != 'reconciled':
            raise Refusal('existing ordinary intent is incomplete/unknown; actual custodian recovery required, never replay')
        board._software_job_grant(store, job)
        _, current_policy = policy_for(store, job)
        if encode(current_policy) != prior['policy']:
            raise Refusal('reconciled effect policy changed; no stale reporting')
        return True
    board._software_job_grant(store, job)
    answer = collected_task_result(attempt)
    tools = json.loads(attempt['detail']).get('tool_completion', {})
    if (attempt['controller'] != store.controller or attempt['exit'] != 0 or attempt['capture'] != 'complete'
            or attempt['begin'] is None or attempt['ended'] is None or attempt['collected'] is None
            or attempt['error'] or answer['semantic'] != 'DONE' or answer['unknowns'] or answer['failures']
            or not tools.get('complete') or tools.get('nonzero_completions')
            or any(item.get('status') == 'failed' for item in tools.get('items', []))):
        raise Refusal('original fully collected worker and known preparation required')
    from .resource_scopes import blocked
    if job['hold_reason'] or blocked(store, job):
        raise Refusal('existing job/legacy hold cannot be released by ordinary automation')
    task, p = policy_for(store, job)
    from .local_integration import current_basis, validate_method
    current_basis(store, job)
    validate_method(store, job, attempt, answer)
    admission = store.one('SELECT * FROM admissions WHERE package=?', (job['package'],))
    receipt = {'tools': [], 'worker': attempt['session'], 'collector': store.controller,
               'authority': epoch['id'], 'admission_hash': digest(admission['receipt']), 'unknown_effects': ['intent not reconciled']}
    with store.tx():
        store.budget(None, p['max_output'] * 16)
        store.db.execute('INSERT INTO ordinary_runs VALUES(?,?,?,?,?,?,?)',
            (attempt['id'], job['id'], epoch['id'], receipt['admission_hash'], encode(p), 'intent', encode(receipt)))
        from .local_integration import native_intent
        native_intent(store, job)
        for resource in p['resources']:
            if store.one('SELECT attempt FROM ordinary_resources WHERE resource=?', (resource['key'],)):
                raise Refusal('resource still belongs to another original/unknown effect')
            store.db.execute('INSERT INTO ordinary_resources VALUES(?,?)', (resource['key'], attempt['id']))
    before = await source(store, attempt['id'], p, task)
    with store.tx():
        receipt['before'] = before
        store.db.execute('UPDATE ordinary_runs SET receipt=? WHERE attempt=?',(encode(receipt),attempt['id']))
    if p['kind'] == 'local-ref':
        from .branches import repository_identity
        device, inode = repository_identity(p['repository'])
        resource_key = 'git-ref:' + str(device) + ':' + str(inode) + ':' + p['ref']
        read_key = 'git-ref:' + str(device) + ':' + str(inode) + ':' + p['source_ref']
        with store.tx():
            for key in (resource_key, read_key):
                if store.one('SELECT attempt FROM ordinary_resources WHERE resource=?', (key,)):
                    raise Refusal('actual common Git ref remains owned by an original effect')
                store.db.execute('INSERT INTO ordinary_resources VALUES(?,?)', (key, attempt['id']))
    association = await qa_source.export(store, attempt['id'], p, before) if p['kind'] == 'local-qa' else None
    outcome = await adapter(store, attempt['id'], p, task=task, association=association)
    after = await source(store, attempt['id'], p, task)
    if after != before:
        raise Refusal('source repository/origin/ref/branch identity changed during effects; retain original intent/resources')
    board._software_job_grant(store, store.job(job['id']))
    policy_for(store, store.job(job['id']))  # Lease/procedure/executable/admission current after tool collection.
    if store.one('SELECT receipt FROM admissions WHERE package=?', (job['package'],))['receipt'] != admission['receipt']:
        raise Refusal('admission changed during effects; original intent remains accountable')
    with store.tx():
        receipt = json.loads(store.one('SELECT receipt FROM ordinary_runs WHERE attempt=?', (attempt['id'],))['receipt'])
        receipt['tools'] = [json.loads(r['record']) for r in store.rows('SELECT record FROM ordinary_tool_records WHERE attempt=? ORDER BY seq', (attempt['id'],))]
        receipt.update(before=before, after=after, outcome=outcome, unknown_effects=[], meaning='known actual effects; local reporting is separate from semantic acceptance')
        if p['kind'] == 'local-qa':
            qa_source.verify(store, attempt['id'], p, receipt)
        store.db.execute("UPDATE ordinary_runs SET state='reconciled',receipt=? WHERE attempt=?", (encode(receipt), attempt['id']))
        store.db.execute("UPDATE jobs SET effects='reconciled',effect_receipt=? WHERE id=? AND active_attempt=?", (encode(receipt), job['id'], attempt['id']))
        store.db.execute('DELETE FROM ordinary_resources WHERE attempt=?', (attempt['id'],))
    return True


async def adapter(store, attempt, p, *, task=None, association=None):
    if p['kind'] == 'local-ref':
        before = await git(store, attempt, p, 'rev-parse', '--verify', p['ref'] + '^{commit}')
        if before != p['before']:
            raise Refusal('destination ref preimage differs; no blind ref write')
        from .resource_scopes import blocked
        run = store.one('SELECT job FROM ordinary_runs WHERE attempt=?', (attempt,))
        if blocked(store, store.job(run['job'])):
            raise Refusal('fresh exact operation custody changed before CAS')
        await git(store, attempt, p, 'update-ref', p['ref'], p['target'], p['before'])
        after = await git(store, attempt, p, 'rev-parse', '--verify', p['ref'] + '^{commit}')
        if after != p['target']:
            raise Refusal('actual ref readback differs; effects remain unknown')
        return {'status': 'success', 'ref': p['ref'], 'before': before, 'after': after}
    if p['kind'] == 'github-run':
        return await github(store, attempt, p)
    run = await tool(store, attempt, 'qa-runner', qa_source.command(store, task, p, association, p['command']), p['repository'], p)
    readback = await tool(store, attempt, 'qa-effect-resource-readback', qa_source.command(store, task, p, association, p['readback']), p['repository'], p)
    association = {**association, 'runner_record': digest(run)}
    if run['exit'] not in p['known_exits'] or readback['exit'] != 0 or readback['stdout'] != p['readback']['stdout']:
        raise Refusal('QA exit/effect/resource readback unknown; retain original custody')
    return {'status': 'success' if run['exit'] == 0 else 'failed', 'actual_exit': run['exit'],
            'selection': p['command']['argv'], 'readback': readback, 'source_execution': association}


async def github(store, attempt, p):
    endpoint = f"repos/{p['repository_slug']}/actions/runs/{p['run_id']}"
    record = await tool(store, attempt, 'ci-run-readback', [p['gh'], 'api', '--hostname', 'github.com', '--method', 'GET', endpoint], p['repository'], p)
    if record['exit'] != 0:
        raise Refusal('actual CI API readback failed')
    run = json.loads(record['stdout'])
    expected = {'id': p['run_id'], 'run_attempt': p['run_attempt'], 'head_sha': p['source_head'], 'event': p['event'], 'path': p['workflow']}
    if any(run.get(k) != v for k, v in expected.items()) or run.get('repository', {}).get('full_name') != p['repository_slug']:
        raise Refusal('CI source/run/attempt/event/workflow/repository differs from admission')
    if run.get('status') != 'completed' or run.get('conclusion') not in {'success', 'failure', 'cancelled', 'timed_out', 'action_required', 'neutral', 'skipped', 'startup_failure', 'stale'}:
        raise Refusal('CI remains partial/unknown; monitoring stays with original custodian')
    jobs = await tool(store, attempt, 'ci-jobs-readback', [p['gh'], 'api', '--hostname', 'github.com', '--method', 'GET', endpoint + f"/attempts/{p['run_attempt']}/jobs?per_page=100"], p['repository'], p)
    data = json.loads(jobs['stdout']) if jobs['exit'] == 0 else {}
    items = data.get('jobs', [])
    if (not items or data.get('total_count') != len(items) or {j.get('id') for j in items} != set(p['job_ids'])
            or any(j.get('status') != 'completed' or not j.get('conclusion') for j in items)):
        raise Refusal('CI job selection/outcomes incomplete (including pagination); retain monitor custody')
    return {'status': 'success' if run['conclusion'] == 'success' and all(j['conclusion'] == 'success' for j in items) else 'failed', 'run': run, 'jobs': items,
            'meaning': 'selected existing run monitoring/readback; does not dispatch/re-run CI or accept work'}


async def accept(store, actor, attempt_id, decision, evidence):
    run = store.one('SELECT * FROM ordinary_runs WHERE attempt=?', (attempt_id,))
    if not run or run['state'] != 'reconciled' or decision not in {'accepted', 'rejected'} or not evidence:
        raise Refusal('actual reconciled execution, explicit decision and semantic evidence required')
    job = store.job(run['job'])
    attempt = store.attempt(attempt_id)
    if job['active_attempt'] != attempt_id or not selected(store, job):
        raise Refusal('acceptance must bind the current original attempt/authority')
    prospective.board(store, job['role'])._software_job_grant(store, job)
    task, p = policy_for(store, job)
    receipt = json.loads(run['receipt'])
    if actor != p['acceptor'] or actor in {attempt['session'], attempt['controller'], store.config['actor']}:
        raise Refusal('independent actual authorized semantic acceptor required')
    if evidence.get('execution_hash') != digest(receipt) or not evidence.get('rationale') or evidence.get('unknowns') != []:
        raise Refusal('semantic decision needs exact execution digest, rationale and known scope')
    if decision == 'accepted' and receipt['outcome']['status'] != 'success':
        raise Refusal('known failed/rejected/skipped CI is not accepted qualification')
    if p['kind'] == 'local-qa':
        qa_source.verify(store, attempt_id, p, receipt)
    # Currentness observation has its own actual tool records in this run.
    if await source(store, attempt_id, p, task) != receipt['after']:
        raise Refusal('source identity changed before independent acceptance; retain original execution')
    if p['kind'] == 'local-ref' and await git(store, attempt_id, p, 'rev-parse', '--verify', p['ref'] + '^{commit}') != p['target']:
        raise Refusal('accepted ref no longer current')
    if p['kind'] == 'github-run':
        current = await github(store, attempt_id, p)
        if digest(current) != digest(receipt['outcome']):
            raise Refusal('CI run changed before semantic acceptance')
    with store.tx():
        record = {'actor': actor, 'authority': p['acceptance_authority'], 'execution_hash': evidence['execution_hash'],
                  'admission': run['admission'], 'decision': decision, 'evidence': evidence, 'at': store.clock()}
        store.db.execute('INSERT INTO ordinary_acceptance VALUES(?,?,?,?)', (attempt_id, actor, decision, encode(record)))
    return record


def accepted_runs(store, package):
    admission = store.one('SELECT receipt FROM admissions WHERE package=?', (package,))
    if not admission:
        return []
    scopes = json.loads(admission['receipt']).get('task_scopes', {})
    required = {name for name, scope in scopes.items() if scope.get('ordinary_effects')}
    rows = store.rows("SELECT r.*,j.task,a.receipt AS acceptance FROM ordinary_runs r JOIN jobs j ON j.id=r.job "
        "JOIN ordinary_acceptance a ON a.attempt=r.attempt WHERE j.package=? AND a.decision='accepted' AND j.active_attempt=r.attempt", (package,))
    matching = [r for r in rows if r['admission'] == digest(admission['receipt']) and r['state'] == 'reconciled'
                and json.loads(r['receipt'])['outcome']['status'] == 'success'
                and json.loads(r['acceptance'])['execution_hash'] == digest(json.loads(r['receipt']))]
    matching = [r for r in matching if json.loads(r['policy'])['kind'] != 'local-qa'
                or json.loads(r['receipt'])['outcome'].get('source_execution', {}).get('method') == 'git-blobs-readonly-namespace-v1']
    return matching if required and required == {r['task'] for r in matching} else []


def accepted_package(store, package):
    return bool(accepted_runs(store, package))


def needs_acceptance(store, package):
    row = store.one('SELECT receipt FROM admissions WHERE package=?', (package,))
    return bool(row and any(s.get('ordinary_effects') for s in json.loads(row['receipt']).get('task_scopes', {}).values()))


def wait_for_acceptance(store, job):
    """Expected independent decision wait, not an effect failure or new worker."""
    attempt = store.attempt(job['active_attempt'])
    if attempt['controller'] != store.controller or attempt['collected'] is None:
        raise Refusal('only the actual collected original can await semantic acceptance')
    with store.tx():
        detail = json.loads(attempt['detail'])
        detail['ordinary_awaiting_acceptance'] = True
        store.db.execute('UPDATE attempts SET detail=? WHERE id=?', (encode(detail), attempt['id']))


def awaiting_acceptance(store, job):
    return bool(job['active_attempt'] and json.loads(store.attempt(job['active_attempt'])['detail']).get('ordinary_awaiting_acceptance'))


async def qualification(store, job):
    with store.tx():
        attempt = store.attempt(job['active_attempt'])
        detail = json.loads(attempt['detail'])
        detail.pop('ordinary_qualification', None)
        store.db.execute('UPDATE attempts SET detail=? WHERE id=?', (encode(detail), attempt['id']))
    rows = accepted_runs(store, job['package'])
    if not rows:
        raise Refusal('actual independent acceptance missing for one or more admitted ordinary task outcomes')
    for row in rows:
        original = store.job(row['job'])
        if not selected(store, original):
            raise Refusal('qualified ordinary authority no longer current')
        prospective.board(store, original['role'])._software_job_grant(store, original)
        task, p = policy_for(store, original)
        if p['kind'] == 'local-qa':
            qa_source.verify(store, row['attempt'], p, json.loads(row['receipt']))
        if await source(store, row['attempt'], p, task) != json.loads(row['receipt'])['after']:
            raise Refusal('qualified source repository/origin/ref/branch no longer current')
        if p['kind'] == 'local-ref' and await git(store, row['attempt'], p, 'rev-parse', '--verify', p['ref'] + '^{commit}') != p['target']:
            raise Refusal('qualified ref no longer current')
        if p['kind'] == 'github-run' and digest(await github(store, row['attempt'], p)) != digest(json.loads(row['receipt'])['outcome']):
            raise Refusal('qualified CI run no longer current')
    with store.tx():
        attempt = store.attempt(job['active_attempt'])
        detail = json.loads(attempt['detail'])
        detail['ordinary_qualification'] = {'acceptances': digest([r['acceptance'] for r in rows]), 'checked': store.clock()}
        store.db.execute('UPDATE attempts SET detail=? WHERE id=?', (encode(detail), attempt['id']))


def qualification_current(store, job):
    rows = accepted_runs(store, job['package'])
    proof = json.loads(store.attempt(job['active_attempt'])['detail']).get('ordinary_qualification', {})
    return bool(rows and proof.get('acceptances') == digest([r['acceptance'] for r in rows])
                and store.clock() - proof.get('checked', 0) <= store.config['deadlines']['bind'])
