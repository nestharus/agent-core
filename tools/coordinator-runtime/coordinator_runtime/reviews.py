"""Selected ordinary Source: pinned material, a live root, original collection.

This consumer imports the current procedure. It defines transport and custody,
not a new reviewer method. Lost/expired roots never fall back to fresh ones.
"""
import asyncio
import hashlib
import json
from pathlib import Path
import re
import shlex

from .contracts import Refusal, digest, encode, parse_json, regular_path, required_text
from .appserver import end_owned

BINDING = {'model': 'gpt-6.1-sol', 'effort': 'high', 'provider': 'openai'}
SCHEMA = """
CREATE TABLE IF NOT EXISTS review_contexts(
 component TEXT PRIMARY KEY,capability TEXT NOT NULL,profile TEXT NOT NULL,
 route TEXT NOT NULL,handle TEXT NOT NULL,run TEXT,collector TEXT NOT NULL,
 state TEXT NOT NULL,head TEXT,history_hash TEXT NOT NULL,created REAL NOT NULL,closed_at REAL);
CREATE TABLE IF NOT EXISTS review_calls(
 attempt TEXT PRIMARY KEY,component TEXT NOT NULL,collector TEXT NOT NULL,
 packet TEXT NOT NULL,state TEXT NOT NULL,receipt TEXT,answer TEXT);
CREATE TABLE IF NOT EXISTS review_call_contexts(attempt TEXT PRIMARY KEY,context TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS review_history_commits(
 attempt TEXT PRIMARY KEY,component TEXT NOT NULL,path TEXT NOT NULL,before_hash TEXT NOT NULL,
 after_hash TEXT NOT NULL,entry TEXT NOT NULL,head TEXT NOT NULL,state TEXT NOT NULL);
"""

FAMILIES = {'organization-and-communication','cross-change-understanding','purpose',
            'local-behavior-and-continuity','authority-and-enforcement','claim-and-evidence-validity',
            'service-capability-and-headroom','operational-evidence-capabilities','agent-reasoning-integrity'}


def coverage(returned,packet,architecture):
    """Account for the actual method, without treating a label as reading proof."""
    account=returned.get('coverage')
    fields={'families','core_files_not_read','observations','answered_ids','limits'}
    if not isinstance(account,dict) or set(account)!=fields:
        raise Refusal('full family/core/unread/observation/answered-ID coverage account required')
    if (not isinstance(account['families'],dict) or set(account['families'])!=FAMILIES
            or any(v not in {'full','partial','unread','not-applicable'} for v in account['families'].values())
            or any(not isinstance(account[k],list) for k in fields-{'families'})):
        raise Refusal('all nine actual families and explicit reading limits required')
    if account['answered_ids']!=packet['answered_ids']:
        raise Refusal('actual correction answered correspondence must survive the full return')
    ids=[o.get('id') for o in account['observations'] if isinstance(o,dict)]
    if len(ids)!=len(account['observations']) or any(not isinstance(i,str) or not i.strip() for i in ids) or len(ids)!=len(set(ids)):
        raise Refusal('each located observation needs an unambiguous retained ID')
    if not architecture and account['core_files_not_read'] and account['families']['organization-and-communication']=='full':
        raise Refusal('ordinary procedure forbids full organization coverage with unread core files')


def prior_observations(runtime,key):
    known=set()
    for call in runtime.rows('SELECT receipt FROM review_calls WHERE component=?',(key,)):
        for turn in json.loads(call['receipt'] or '[]'):
            try:
                result=parse_json(turn.get('full_answer') or '{}')
                known.update(o['id'] for o in result.get('coverage',{}).get('observations',[]) if isinstance(o,dict) and 'id' in o)
            except (ValueError,Refusal,TypeError):
                continue  # Raw malformed originals remain explicit, not IDs.
    return known


def context_policy(runtime,key,choices):
    call=runtime.one('SELECT * FROM review_calls WHERE component=? ORDER BY rowid DESC LIMIT 1',(key,))
    if not call:
        raise Refusal('actual original context material/selected task unavailable')
    acquired=json.loads(call['packet'])
    task=acquired.get('selected_task')
    if task in choices:
        return choices[task]
    candidates=[p for p in choices.values() if acquired['packet']['component'] in p['components']]
    if len(candidates)!=1:
        raise Refusal('original selected context policy ambiguous/unavailable')
    return candidates[0]


def commit_history(runtime,attempt,component,history,before,entry,head):
    """Journal exact append intent before touching the owned history file."""
    after=sha(before+entry.encode())
    with runtime.tx():
        runtime.db.execute('INSERT INTO review_history_commits VALUES(?,?,?,?,?,?,?,?)',
                           (attempt,component,str(history),sha(before),after,entry,head,'prepared'))
    apply_history(runtime,attempt)


def apply_history(runtime,attempt):
    row=runtime.one('SELECT * FROM review_history_commits WHERE attempt=?',(attempt,))
    if not row:
        raise Refusal('exact original history intent required')
    history=Path(row['path'])
    from .resource_scopes import root
    root(str(history),runtime.config.get('artifact_exclusions',[]))
    if not history.is_relative_to(runtime.home/'review-history'):
        raise Refusal('history recovery cannot write outside its original owned home')
    body=history.read_bytes() if history.exists() else b''
    if sha(body)==row['before_hash']:
        with history.open('ab') as stream:
            stream.write(row['entry'].encode()); stream.flush()
            import os
            os.fsync(stream.fileno())
    elif sha(body)!=row['after_hash']:
        raise Refusal('history has unknown bytes; preserve both original intent and actual file')
    with runtime.tx():
        runtime.db.execute("UPDATE review_contexts SET head=?,history_hash=? WHERE component=?",
                           (row['head'],row['after_hash'],row['component']))
        runtime.db.execute("UPDATE review_history_commits SET state='applied' WHERE attempt=?",(attempt,))
    return {'attempt':attempt,'history_sha256':row['after_hash'],'meaning':'exact local append reconciliation only; no caller END, acceptance or live-session recovery'}


def sha(body):
    return hashlib.sha256(body).hexdigest()


def method_files(entry):
    """Resolve only the ordinary prompt's incorporated family/definition homes."""
    entry = regular_path(entry)
    home = entry.parent
    pending, found = [entry], {}
    while pending:
        path = pending.pop()
        if str(path) in found:
            continue
        body = regular_path(str(path)).read_bytes()
        found[str(path)] = sha(body)
        for target in re.findall(r'\]\(([^)#]+)(?:#[^)]*)?\)', body.decode()):
            # The episode comparison is explanatory, not an incorporated
            # ordinary procedure. Follow family/constituent definitions only.
            relative = (path.parent / target).resolve()
            if (relative.is_relative_to(home) and relative.suffix == '.md'
                    and relative.name not in {'coverage-preserving-review-candidate.md', 'orchestration-order.md'}):
                pending.append(relative)
    return found


def validate(runtime, choices):
    for name, policy in choices.items():
        task = runtime.config['tasks'].get(name, {})
        if task.get('role') != 'Reviews' or task.get('phase') != 'proposer' or task.get('effects') != 'none':
            raise Refusal('ordinary review requires a selected read-only Reviews proposer')
        if (set(policy) != {'caller', 'routes', 'deadline', 'method', 'method_files', 'components'}
                or not 1 <= policy['deadline'] <= 7200):
            raise Refusal('exact native caller/routes/deadline/method/components required')
        regular_path(policy['caller'])
        if method_files(policy['method']) != policy['method_files']:
            raise Refusal('current ordinary definition bodies differ from selected pins')
        for profile in runtime.config['profiles']:
            required_text(policy['routes'].get(profile), 'actual registered Sol high account route', 128)
        for component, material in policy['components'].items():
            required_text(component, 'component', 128)
            if set(material) - {'prior_histories','relationship_paths'} != {'repository', 'origin', 'paths', 'history', 'authority'}:
                raise Refusal('component needs repository/origin/paths/history and read authority')
            required_text(material['authority'], 'actual read/source authority')
            from .resource_scopes import root
            root(material['repository'], runtime.config.get('artifact_exclusions', []))
            # History is an explicitly owned file in the existing runtime,
            # never a platform/profile history or message-selected path.
            history = root(material['history'], runtime.config.get('artifact_exclusions', []))
            if not history.is_relative_to(runtime.home / 'review-history'):
                raise Refusal('review history must stay in explicit runtime custody')
            for path, expected in material.get('prior_histories', {}).items():
                root(path, runtime.config.get('artifact_exclusions', []))
                if sha(regular_path(path).read_bytes()) != expected:
                    raise Refusal('original permitted prior history differs from its admitted pin')
            if not isinstance(material['paths'], list) or not material['paths']:
                raise Refusal('component source paths required')
            for value in material['paths']+material.get('relationship_paths',[]):
                path = Path(value)
                if path.is_absolute() or '..' in path.parts or value.startswith('-'):
                    raise Refusal('component paths are repository-relative scopes')


def git(repository, *args):
    """Read-only acquisition; no shell, checkout, config or account probes."""
    import subprocess
    result = subprocess.run(['git', '--no-replace-objects', '-C', repository, *args], capture_output=True, check=True)
    return result.stdout


def material(policy, packet, prior):
    if not isinstance(packet, dict) or set(packet) != {'component', 'origin', 'base', 'head', 'previous', 'answered_ids'}:
        raise Refusal('Source input accepts only component/origin/base/head/previous/answered_ids; goals stay outside')
    selected = policy['components'].get(packet['component'])
    if not selected or packet['origin'] != selected['origin']:
        raise Refusal('component/origin outside genuine read authority')
    repository = selected['repository']
    for key in ('base', 'head'):
        pin = packet[key]
        if not isinstance(pin, str) or not re.fullmatch('[a-f0-9]{40}', pin):
            raise Refusal('full immutable Git commit pins required')
        if git(repository, 'rev-parse', pin + '^{commit}').decode().strip() != pin:
            raise Refusal('source pin did not resolve exactly')
    if not isinstance(packet['answered_ids'], list) or any(not isinstance(i, str) or not i.strip() for i in packet['answered_ids']):
        raise Refusal('explicit answered observation IDs required')
    if packet['previous'] != (prior['head'] if prior else None):
        raise Refusal('correction must continue the exact prior component head')
    if not prior and packet['answered_ids']:
        raise Refusal('a first cycle cannot answer fabricated previous observations')
    history = Path(selected['history'])
    prior_histories = selected.get('prior_histories', {})
    for path, expected in prior_histories.items():
        if sha(regular_path(path).read_bytes()) != expected:
            raise Refusal('whole original permitted history changed')
    history_body = history.read_bytes() if history.exists() else b''
    if prior and sha(history_body) != prior['history_hash']:
        raise Refusal('whole attributed review history changed; no silent repair')
    if not prior and history_body:
        # Explicit pre-existing permitted history is allowed, but is not a
        # claim that this newly constructed context encountered it earlier.
        required_text(history_body.decode(), 'permitted prior history')
    source = {}
    commands = []
    paths=list(dict.fromkeys(selected['paths']+selected.get('relationship_paths',[])))
    for pin in dict.fromkeys([packet['base'], packet['head'], *([packet['previous']] if prior else [])]):
        entries = git(repository, 'ls-tree', '-rz', pin, '--', *paths).split(b'\0')
        for entry in filter(None, entries):
            metadata, name = entry.split(b'\t', 1)
            mode, kind, oid = metadata.decode().split()
            if mode == '120000' or kind != 'blob':
                raise Refusal('symlink/submodule material needs an explicit source boundary')
            name = name.decode()
            body = git(repository, 'show', pin + ':' + name)
            source[pin + ':' + name] = {'git_blob': oid, 'bytes': len(body), 'sha256': sha(body)}
            commands.append(shlex.join(['git', '-C', repository, 'show', pin + ':' + name]))
        commands.append(shlex.join(['git', '-C', repository, 'ls-tree', '-r', pin, '--', *paths]))
    if not source:
        raise Refusal('selected material is empty')
    correction_base = packet['previous'] if prior else packet['base']
    diff = git(repository, 'diff', '--no-ext-diff', '--no-textconv', correction_base, packet['head'], '--', *paths).decode()
    # Material/diff/history are factual inputs, never task purpose/acceptance or
    # arbitrary message bodies. The full diff is in the executable read command.
    commands.append(shlex.join(['git', '-C', repository, 'diff', '--no-ext-diff', '--no-textconv', correction_base, packet['head'], '--', *paths]))
    for path in policy['method_files']:
        commands.append(shlex.join(['cat', path]))
    if history.exists():
        commands.append(shlex.join(['cat', str(history)]))
    return {'packet': packet, 'repository': repository, 'source': source, 'method_files': policy['method_files'],
            'history': str(history), 'history_sha256': sha(history_body), 'prior_histories': prior_histories, 'correction_diff': diff,
            'commands': commands, 'read_authority': selected['authority'],'relationship_paths':selected.get('relationship_paths',[])}


def prompt(policy, acquired, read_command):
    return ('Perform the current ordinary unified static reviewer procedure at ' + policy['method'] + '. '
            'Read it and every incorporated definition. Architecture first, then continue all nine families '
            'and all constituent questions in this same conversation. Return the architecture pass when ready; '
            'the controller then requests the remaining procedure work on this SAME live root. '
            'Read the whole permitted history first, preserve findings/dissent/coverage/core files not read '
            'and all limits. Do not run tests, mutate source, launch agents, inspect accounts or acquire '
            'unselected material. Do not load project AGENTS, WORK_LOG or unrelated goal/history for startup. '
            'Your only shell command is the supplied read facade. Invoke it repeatedly '
            'through end_of_material; each response carries exact source/offset/total/hash. It emits history '
            'first, then current definitions, actual correction diff and pinned source bodies. Subsequent '
            'calls cycle for rereading. Emission is not evidence that you read it. Preserve missing chunks '
            'and unread files explicitly. Goals/acceptance/repair hints '
            'are deliberately outside your input. Return JSON with exactly semantic (DONE/PARTIAL/FAILED/UNKNOWN), '
            'summary, report (the entire attributed procedure return), history_entry, coverage, stage '
            '(architecture or complete). coverage must contain exactly families (all nine family slugs '
            'mapped to full/partial/unread/not-applicable), core_files_not_read (list), observations '
            '(located observation objects with unique id), answered_ids (actual supplied IDs with '
            'correspondence explained in the report), and limits (list). Mark partial/unread work explicitly; '
            'labels and facade emission do not establish reading. DONE concerns this inquiry only, never consumer acceptance. '
            'A remaining-family return must use stage=complete. Do not discard earlier observations.\n' +
            encode({k: v for k, v in acquired.items() if k != 'commands'}) + '\nREAD_COMMAND=' + read_command)


class Native:
    """Each call is an owned original subprocess; no provider/session fabrication."""
    async def call(self, runtime, attempt, policy, context, directory, text, commands, opening=False, close=False):
        directory.mkdir(mode=0o700, parents=True, exist_ok=False)
        prompt_path, allow_path = directory / 'input.txt', directory / 'allow.json'
        prompt_path.write_text(text)
        allow_path.write_text(encode(commands))
        out = directory / 'native'
        argv = [policy['caller']]
        if opening:
            argv += ['--route', context['route'], '--cwd', '/tmp',
                     '--live-handle', context['handle'], '--allow-file', str(allow_path), '--deadline', str(policy['deadline']),
                     '--retention', 'discard']
        else:
            argv += ['--root', context['handle'], '--wait', str(policy['deadline'])]
        argv += ['--out', str(out)] + (['--close'] if close else ['--prompt-file', str(prompt_path)])
        if not close:
            runtime.authorize_launch(attempt)
        # Each NEW input obeys current user membership. Close drains existing
        # ownership even after exclusion, without admitting new model work.
        guard = _existing() if close else runtime.execution_pool.admission(context['profile'])
        async with guard:
            if not close:
                with runtime.tx():
                    runtime.db.execute("UPDATE review_calls SET state='launch-intent' WHERE attempt=?",(attempt,))
            try:
                child = await asyncio.create_subprocess_exec(*argv, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
            except OSError:
                if not close and runtime.attempt(attempt)['begin'] is None:
                    with runtime.tx():
                        runtime.db.execute("UPDATE review_calls SET state='prepared' WHERE attempt=?",(attempt,))
                raise  # Affirmative local process-creation refusal, no model admission.
            if not close and runtime.attempt(attempt)['begin'] is None:
                runtime.begin(attempt, {'process_handle': 'owned-asyncio-subprocess', 'original_collector': runtime.controller,
                                        'identity_scope': 'native caller; not provider root completion'})
        timed_out = False
        try:
            # A bound ends only this caller, not a claim that its live root died.
            code = await asyncio.wait_for(asyncio.shield(child.wait()), policy['deadline'] + 100)
        except asyncio.TimeoutError:
            timed_out = True
            code = await end_owned(child, runtime.config['deadlines']['shutdown'])
        finally:
            if child.returncode is None:
                code = await end_owned(child, runtime.config['deadlines']['shutdown'])
        maximum = runtime.config['limits']['max_result_bytes']
        try:
            receipt_path = regular_path(str(out / 'result.json'))
            final_path = out / 'final.md'
            if receipt_path.stat().st_size > maximum or final_path.exists() and final_path.stat().st_size > maximum:
                raise Refusal('original native capture exceeds admitted complete-return bound; retain it')
            receipt = parse_json(receipt_path.read_text())
            answer = final_path.read_text() if final_path.exists() else None
        except (Refusal, OSError, ValueError) as exc:
            receipt, answer = {'class': 'incomplete', 'capture': str(out), 'failure': str(exc)}, None
        if timed_out:
            receipt = {**receipt, 'class': 'incomplete', 'caller_bound_exceeded': True}
        return code, receipt, answer


from contextlib import asynccontextmanager


@asynccontextmanager
async def _existing():
    yield


class Executor:
    def __init__(self, runtime, transport=None):
        self.runtime, self.transport = runtime, transport or Native()
        self.busy = set()

    async def execute(self, job, attempt, policy, packet):
        runtime = self.runtime
        from .branches import review_key,review_policy,job_branch
        component = review_key(runtime,job,packet)
        policy = review_policy(runtime,job,policy,packet)
        if component in self.busy:
            raise Refusal('component already has an original live collector; no overlapping input')
        self.busy.add(component)
        try:
            context = runtime.one('SELECT * FROM review_contexts WHERE component=?', (component,))
            if context and (context['state'] != 'live' or context['collector'] != runtime.controller
                            or context['capability'] != runtime.processing.key):
                raise Refusal('original live context/collector unavailable; explicit recovery required, never a fresh fallback')
            predecessor=runtime.one("SELECT context FROM review_predecessors WHERE component=? AND disposition='inactive' ORDER BY created DESC,rowid DESC LIMIT 1",(component,)) if not context else None
            prior=context or (json.loads(predecessor['context']) if predecessor else None)
            acquired = material(policy, packet, prior)
            acquired['selected_task']=job.get('task')
            if set(packet['answered_ids'])-prior_observations(runtime,component):
                raise Refusal('answered IDs must refer to actual preserved prior observations')
            acquired['encounter_recovery']={'same_session_continuity':False,'predecessor':prior} if predecessor else None
            if method_files(policy['method']) != policy['method_files']:
                raise Refusal('selected ordinary procedure changed before execution')
            opening = context is None
            facade = runtime.home / 'review-inputs' / digest(component) / 'material.json'
            facade.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            # Atomic single-file publication only; source bodies are not copied.
            temporary = facade.with_suffix('.pending')
            with temporary.open('x') as stream:
                stream.write(encode(acquired)); stream.flush()
                import os
                os.fsync(stream.fileno())
            os.replace(temporary, facade)
            read_command = shlex.join(['/usr/bin/python3', '-B', str(Path(__file__).with_name('review_reader.py')), str(facade)])
            if opening:
                profile = runtime.attempt(attempt)['profile']
                context = {'component': component, 'capability': runtime.processing.key, 'profile': profile,
                           'route': policy['routes'][profile], 'handle': str(runtime.home / 'review-handles' / attempt),
                           'run': None, 'collector': runtime.controller, 'state': 'opening', 'head': None,
                           'history_hash': acquired['history_sha256'], 'created': runtime.clock(), 'closed_at': None}
                Path(context['handle']).parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            else:
                # _attempt allocated advice from the current pool. The existing
                # conversation is on its observed account; record that fact.
                with runtime.tx():
                    runtime.db.execute('UPDATE attempts SET profile=? WHERE id=? AND begin IS NULL', (context['profile'], attempt))
            with runtime.tx():
                runtime.budget(None, len(encode(acquired).encode()) + 4096)
                if opening:
                    runtime.db.execute('INSERT INTO review_contexts VALUES(?,?,?,?,?,?,?,?,?,?,?,?)', tuple(context.values()))
                runtime.db.execute('INSERT INTO review_calls VALUES(?,?,?,?,?,NULL,NULL)',
                                   (attempt, component, runtime.controller, encode(acquired), 'prepared'))
                runtime.db.execute('INSERT INTO review_call_contexts VALUES(?,?)',(attempt,encode(context)))
            turns = []
            text = prompt(policy, acquired, read_command)
            while True:
                # Architecture return and remaining return are different calls,
                # collected on this original executor, on the same actual root.
                directory = runtime.home / 'artifacts' / attempt / ('review-call-' + str(len(turns)))
                call_policy={**policy,'components':{**policy['components'],component:policy['components'][packet['component']]}}
                code, receipt, answer = await self.transport.call(runtime, attempt, call_policy, context, directory,
                                                                 text, [read_command], opening=opening and not turns)
                turns.append({'actual_END': code, 'receipt': receipt, 'full_answer': answer})
                with runtime.tx():
                    runtime.budget(None, len(encode(turns).encode()))
                    runtime.db.execute('UPDATE review_calls SET receipt=?,answer=? WHERE attempt=?',
                                       (encode(turns), answer, attempt))
                observed = receipt.get('run')
                if not observed or context['run'] is not None and observed != context['run']:
                    raise Refusal('actual native root identity missing/changed; no manufactured continuity')
                context['run'] = observed
                with runtime.tx():
                    runtime.db.execute('UPDATE review_contexts SET run=? WHERE component=?', (observed, component))
                    runtime.db.execute('UPDATE review_call_contexts SET context=? WHERE attempt=?',(encode(context),attempt))
                    lease=runtime.one('SELECT id FROM branch_turns WHERE id=?',(attempt,))
                    if lease:
                        runtime.db.execute('UPDATE branch_turns SET address=? WHERE id=?',(observed,attempt))
                    branch=job_branch(runtime,job)
                    if branch:
                        if observed==branch['root'] or runtime.one("SELECT address FROM branch_contexts WHERE branch=? AND kind='builder' AND address=?",(branch['id'],observed)):
                            raise Refusal('ordinary reviewer must remain separate from responsible Root and builders')
                        runtime.db.execute('INSERT OR IGNORE INTO branch_contexts VALUES(?,?,?,?,?,?,?,?,?,NULL)',
                                           (branch['id'],'review',packet['component'],observed,'observed-native-run',context['profile'],runtime.controller,'available',encode(receipt)))
                if code != 0 or receipt.get('class') != 'answered' or receipt.get('transport', {}).get('errors'):
                    raise Refusal('original native call incomplete/failed; retained full return and possible live root')
                returned = parse_json(answer)
                if (not isinstance(returned, dict) or set(returned) != {'semantic', 'summary', 'report', 'history_entry', 'coverage', 'stage'}
                        or returned['semantic'] not in {'DONE', 'PARTIAL', 'FAILED', 'UNKNOWN'}):
                    raise Refusal('selected reviewer returned an incomplete wire contract; original preserved')
                for field in ('summary', 'report', 'history_entry'):
                    required_text(returned[field], 'full reviewer ' + field, runtime.config['limits']['max_result_bytes'])
                coverage(returned,packet,not turns[:-1])
                if len(turns)==1 and returned['stage']!='architecture':
                    raise Refusal('ordinary architecture return is required before remaining families')
                if len(turns)>1 and returned['stage']!='complete':
                    raise Refusal('remaining-family return must explicitly complete its own procedure stage')
                if returned['stage'] == 'complete' or returned['semantic'] != 'DONE':
                    break
                if returned['stage'] != 'architecture':
                    raise Refusal('actual architecture/remaining procedure stage required')
                # No fixed review cycle cap or substituted procedure. This turn
                # simply requests the pending work in the defining home.
                text = ('Continue the remaining ordinary unified procedure in this SAME context. '
                        'Conserve the complete architecture pass and return stage=complete with the whole '
                        'coverage/history/findings/diagnosis and explicit unexamined areas. No new goal or repair input.')
            selected = policy['components'][packet['component']]
            history = Path(selected['history'])
            history.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            before = history.read_bytes() if history.exists() else b''
            if sha(before) != acquired['history_sha256']:
                raise Refusal('history changed during original review; retain return without overwriting')
            entry = '\n' + encode({'packet': packet, 'collector': runtime.controller, 'attempt': attempt,
                                   'actual_run': context['run'], 'turns': turns}) + '\n'
            commit_history(runtime,attempt,component,history,before,entry,packet['head'])
            with runtime.tx():
                runtime.db.execute("UPDATE review_calls SET state='collected' WHERE attempt=?", (attempt,))
                runtime.db.execute("UPDATE review_contexts SET state='live',head=?,history_hash=? WHERE component=?",
                                   (packet['head'], sha(before + entry.encode()), component))
            # This is an observed native run address, not a fabricated UUID or
            # attestation of hidden provider session/turn identities.
            runtime.session(attempt, context['run'], str(turns[-1]['receipt']['turn']['input']),
                            {'identity_kind': 'observed-native-run', 'native_provider_session': 'not exposed'})
            result = {'semantic': returned['semantic'], 'summary': returned['summary'], 'category': 'proposal',
                      'findings': [{'kind': 'ordinary-review-full-return', 'component': component, 'material': acquired,
                                    'original_collector': runtime.controller, 'original_attempt': attempt, 'turns': turns}],
                      'failures': [], 'unknowns': [] if returned['semantic'] == 'DONE' else [returned['coverage']], 'artifacts': []}
            return {'exit': code, 'capture': 'complete', 'cleanup': 'continuing-context-held', 'result': result, 'error': None,
                    'detail': {'native_original_calls': turns,
                               'static_authority': 'selected static procedure; sole whole-command material facade; no exact read-isolation claim',
                               'tool_capture': 'native caller exports; no fabricated app-server tool completion'}}
        except BaseException:
            with runtime.tx():
                call=runtime.one('SELECT state FROM review_calls WHERE attempt=?',(attempt,))
                if call and call['state']!='prepared':
                    runtime.db.execute("UPDATE review_contexts SET state='interrupted' WHERE component=?", (component,))
                elif context and context.get('state')=='opening':
                    # No native process/input was launched. Keep factual history
                    # and raw preparation, but permit a later genuine opening.
                    runtime.db.execute('DELETE FROM review_contexts WHERE component=?',(component,))
            raise
        finally:
            self.busy.discard(component)

    async def close(self, component, policy):
        runtime = self.runtime
        context = runtime.one('SELECT * FROM review_contexts WHERE component=?', (component,))
        if not context or context['collector'] != runtime.controller or component in self.busy:
            raise Refusal('close belongs to the idle original live-context collector')
        if context['state'] == 'closed':
            return {'component': component, 'already_closed': True}
        call = runtime.one('SELECT * FROM review_calls WHERE component=? ORDER BY rowid DESC LIMIT 1', (component,))
        saved_turns=json.loads(call['receipt'] or '[]')
        directory = runtime.home / 'artifacts' / call['attempt'] / ('review-close-'+str(sum('close_intent' in t for t in saved_turns)))
        with runtime.tx():
            runtime.db.execute('UPDATE review_calls SET receipt=? WHERE attempt=?',
                               (encode(saved_turns+[{'close_intent':str(directory),'actual_END':None}]),call['attempt']))
        # Branch routing keys differ from factual component names.
        acquired=json.loads(call['packet'])
        original_component=acquired['packet']['component']
        policy={**policy,'components':{**policy['components'],component:policy['components'][original_component]}}
        code, receipt, answer = await self.transport.call(runtime, call['attempt'], policy, context, directory, '', [], close=True)
        with runtime.tx():
            saved = json.loads(runtime.one('SELECT receipt FROM review_calls WHERE attempt=?',(call['attempt'],))['receipt'] or '[]') + [{'close_actual_END': code, 'receipt': receipt}]
            runtime.db.execute('UPDATE review_calls SET receipt=? WHERE attempt=?', (encode(saved), call['attempt']))
            closed = code == 0 and receipt.get('class') == 'closed' and receipt.get('physical_close') is True
            runtime.db.execute('UPDATE review_contexts SET state=?,closed_at=? WHERE component=?',
                               ('closed' if closed else 'interrupted', runtime.clock() if closed else None, component))
            if closed:
                runtime.db.execute("UPDATE attempts SET cleanup='done' WHERE id IN (SELECT attempt FROM review_calls WHERE component=?)", (component,))
                runtime.db.execute("UPDATE branch_contexts SET state='closed',closed=? WHERE kind='review' AND address=?",(runtime.clock(),context['run']))
        if not closed:
            raise Refusal('actual root close/whole async accounting incomplete; original receipt retained')
        from .cleanup import register_artifact
        for path in directory.rglob('*'):
            if path.is_symlink():
                raise Refusal('close output alias stays with actual original custodian')
            if path.is_file():
                register_artifact(runtime, call['attempt'], path)
        return {'component': component, 'actual_END': code, 'receipt': receipt, 'processing_complete': False}


def collected_proof(runtime, job, attempt):
    call = runtime.one("SELECT * FROM review_calls WHERE attempt=? AND state='collected'", (attempt['id'],))
    if not call:
        return None
    snapshot=runtime.one('SELECT context FROM review_call_contexts WHERE attempt=?',(attempt['id'],))
    context=json.loads(snapshot['context']) if snapshot else runtime.one('SELECT * FROM review_contexts WHERE component=?', (call['component'],))
    turns = json.loads(call['receipt'])
    actual = [t for t in turns if 'actual_END' in t and 'close_intent' not in t]
    if (not context or attempt['session'] != context['run'] or not context['run']
            or attempt['controller'] != call['collector'] or json.loads(attempt['binding']) != BINDING
            or attempt['begin'] is None or attempt['ended'] is None or attempt['collected'] is None
            or attempt['exit'] != 0 or attempt['capture'] != 'complete' or attempt['error']
            or not actual or any(t['actual_END'] != 0 or t['receipt'].get('class') != 'answered'
                                  or t['receipt'].get('run') != context['run'] for t in actual)):
        raise Refusal('actual continuing Source collector/material/whole return is incomplete')
    return {'kind': 'selected-ordinary-review', 'component': call['component'], 'run': context['run'],
            'collector': call['collector'], 'attempt': attempt['id'], 'calls': actual,
            'material': json.loads(call['packet']), 'provider_session': 'not exposed; no UUID attestation'}
