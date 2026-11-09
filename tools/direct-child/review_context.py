"""Owned opaque CLI context with a positive, immutable material snapshot.

This is an explicit transport, never a fallback for native. The caller supplies
current authority and an Originals-compatible collector. No account discovery,
session-store reads, model resolution, platform deletion or native receipts.
"""
import asyncio
from contextlib import asynccontextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import time

VERSION = 'opaque-cli-v1'
PROFILES = {'.codex', '.codex2', '.codex3', '.codex4', '.codex5'}
MAX_INPUT = 32 * 1024 * 1024
MAX_ITEMS = 1024
DISABLED = (
    'apps', 'connectors', 'plugins', 'plugin_hooks', 'hooks', 'codex_hooks',
    'browser_use', 'computer_use', 'image_generation', 'imagegenext',
    'multi_agent', 'multi_agent_v2', 'multi_agent_mode', 'agent_message_board',
    'collab', 'collaboration_modes', 'js_repl', 'code_mode',
    'memories', 'memory_tool', 'shell_snapshot', 'shell_snapshot_v2',
    'remote_control', 'request_permissions_tool', 'request_rule',
    'apply_patch_freeform', 'use_legacy_landlock',
)


class ReviewRefusal(ValueError):
    pass


@asynccontextmanager
async def existing_admission():
    """Continuations retain their owner; they consume no new pool admission."""
    yield


def private_write(path, body, capacity_check=lambda parent: None):
    capacity_check(Path(path).parent)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(body)
        stream.flush()
        os.fsync(stream.fileno())


def positive_directory(path):
    """Require a caller-owned lexical path; never resolve an exposing alias."""
    path = Path(path)
    if not path.is_absolute() or '..' in path.parts:
        raise ReviewRefusal('absolute positive directory required')
    for part in [*reversed(path.parents), path]:
        info = part.lstat()
        if not stat.S_ISDIR(info.st_mode):
            raise ReviewRefusal('positive directory contains an alias/non-directory')
    return path


def make_directory(path, capacity_check=lambda parent: None):
    """Create an admitted owned parent chain without following existing links."""
    path = Path(path)
    if not path.is_absolute() or '..' in path.parts:
        raise ReviewRefusal('absolute admitted owned directory required')
    for part in [*reversed(path.parents), path]:
        try:
            info = part.lstat()
        except FileNotFoundError:
            capacity_check(part.parent)
            part.mkdir(mode=0o700)
            info = part.lstat()
        if not stat.S_ISDIR(info.st_mode):
            raise ReviewRefusal('owned parent contains an alias/non-directory')


def export(directory, items, capacity_check=lambda parent: None):
    """Only already-admitted bytes enter the model's readable snapshot."""
    if not isinstance(items, list) or not items or len(items) > MAX_ITEMS:
        raise ReviewRefusal('bounded nonempty material list required')
    if any(not isinstance(label, str) or not label or not isinstance(body, bytes)
           for label, body in items):
        raise ReviewRefusal('material needs attributable labels and exact bytes')
    if sum(len(body) for _, body in items) > MAX_INPUT:
        raise ReviewRefusal('complete selected material exceeds snapshot admission')
    capacity_check(directory.parent)
    directory.mkdir(mode=0o700)
    manifest = []
    for index, (label, body) in enumerate(items):
        name = f'{index:04d}.txt'
        # Text validation is before any source export; no encoded/raw captures.
        body.decode('utf-8')
        private_write(directory / name, body, capacity_check)
        (directory / name).chmod(0o400)
        manifest.append(dict(label=label, file=name, bytes=len(body),
                             sha256=hashlib.sha256(body).hexdigest()))
    private_write(directory / 'manifest.json', json.dumps(manifest, ensure_ascii=False).encode(), capacity_check)
    (directory / 'manifest.json').chmod(0o400)
    return manifest


def command(profile, workspace, material, thread=None, *, filesystem=None):
    """Invocation-local restrictions; opaque selector is forwarded literally.

    --sandbox would override default_permissions, so it must not be added.
    --ignore-user-config is supported by exec and resume, not a private query.
    Managed policy can still refuse a launch. Restrictions are requested here;
    the owning qualification must distinguish actual enforcement from flags.
    """
    if profile not in PROFILES:
        raise ReviewRefusal('profile outside explicitly supported original accounts')
    fs = filesystem if filesystem is not None else {':root': 'deny', ':minimal': 'read', str(material): 'read', str(workspace): 'read'}
    # JSON strings are TOML basic strings. This constructs argv, never shell.
    filesystem = '{' + ','.join(json.dumps(k) + '=' + json.dumps(v) for k, v in fs.items()) + '}'
    settings = [
        'approval_policy="never"', 'default_permissions="review-material"',
        'permissions.review-material.filesystem=' + filesystem,
        'permissions.review-material.network.enabled=false',
        'web_search="disabled"', 'mcp_servers={}',
        'mcp_servers.openaiDeveloperDocs.url="https://developers.openai.com/mcp"',
        'mcp_servers.openaiDeveloperDocs.enabled=false',
        'project_doc_max_bytes=0', 'skills.include_instructions=false',
        'skills.bundled.enabled=false', 'features.skip_host_skill_discovery=true',
        'shell_environment_policy.inherit="none"',
        'shell_environment_policy.include_only=[]',
    ] + ['features.' + name + '=false' for name in DISABLED]
    argv = ['codex', '--no-daemon', '-C', str(workspace)]
    for setting in settings:
        argv += ['-c', setting]
    argv += ['exec']
    if thread is not None:
        if not re.fullmatch(r'[0-9a-fA-F-]{36}', thread):
            raise ReviewRefusal('only the exact newly observed public thread ID can continue')
        argv += ['resume', thread]
    argv += ['--ignore-user-config', '--ignore-rules', '--strict-config',
             '--skip-git-repo-check', '--json', '--model', 'gpt-xhigh', '-']
    return argv


def executable_path(value):
    """Explicit public executable, without resolving aliases or private stores."""
    if (not isinstance(value, str) or not value or '\x00' in value
            or not Path(value).is_absolute() or '..' in Path(value).parts):
        raise ReviewRefusal('explicit absolute public executable dependency required')
    return value


def diagnostic(record, item):
    """Bounded attribution; arbitrary provider text remains in owned capture."""
    message = item.get('message', record.get('message', record.get('error', '')))
    body = str(message).encode('utf-8')
    return dict(event=record['type'], item_type=item.get('type'),
                message_bytes=len(body), message_sha256=hashlib.sha256(body).hexdigest(),
                meaning='provider diagnostic; no tool/effect or absence inferred')


class Context:
    """One account, collector, whole lifetime and explicit public thread.

    Saved history and each exec process are separate. Close fences this local
    owner; it neither archives nor deletes provider storage. A lost process or
    interrupted turn cannot become a fresh conversation by reopening this path.
    """
    def __init__(self, root, profile, collector, lifetime, originals, clock=time.monotonic, *, executable, protection=None, origin=None, capacity_check=lambda parent: None, execution=None):
        if profile not in PROFILES or not isinstance(collector, str) or not collector:
            raise ReviewRefusal('original profile/collector required')
        if type(lifetime) is not int or not 1 <= lifetime <= 7200:
            raise ReviewRefusal('bounded whole-context lifetime required')
        self.executable = executable_path(executable)
        created = clock() if origin is None else origin
        if not isinstance(created, (int, float)) or not 0 <= clock() - created < lifetime:
            raise ReviewRefusal('original creation origin invalid or expired')
        root = Path(root)
        positive_directory(root.parent)
        capacity_check(root.parent)
        root.mkdir(mode=0o700)
        self.root, self.workspace = root, root / 'workspace'
        capacity_check(self.workspace.parent)
        self.workspace.mkdir(mode=0o700)
        self.capacity_check = capacity_check
        self.profile, self.collector, self.originals = profile, collector, originals
        self.account_home = str(Path.home())
        self.clock, self.created, self.lifetime = clock, created, lifetime
        self.protection = protection
        self.execution = execution
        self.thread, self.state, self.busy, self.calls = None, 'new', False, 0

    def authorize(self, collector, profile, current_authority, current_profiles):
        if collector != self.collector or profile != self.profile:
            raise ReviewRefusal('original account/collector changed; no transfer')
        if self.busy or self.state not in {'new', 'live'}:
            raise ReviewRefusal('original unavailable/interrupted/closed; no fallback')
        if self.clock() >= self.created + self.lifetime:
            raise ReviewRefusal('original whole-context lifetime elapsed')
        current_authority()
        if self.state == 'new' and self.profile not in current_profiles:
            raise ReviewRefusal('new context outside current launch membership')

    def authorize_creation(self, current_authority):
        """Preparation/admission waiting consumes the original lifetime."""
        if self.clock() >= self.created + self.lifetime:
            raise ReviewRefusal('original whole-context lifetime elapsed before process creation')
        current_authority()

    async def turn(self, directory, items, text, *, collector, profile,
                   current_authority, current_profiles, publish, maximum, capture_max,
                   shutdown=10, started=lambda: None, admission=existing_admission):
        self.authorize(collector, profile, current_authority, current_profiles)
        if (not isinstance(text, str) or not text or len(text.encode()) > MAX_INPUT
                or type(maximum) is not int or not 1 <= maximum <= MAX_INPUT
                or type(capture_max) is not int or not maximum <= capture_max <= 64*1024**2):
            raise ReviewRefusal('finite selected input/answer/capture limits required')
        directory = Path(directory)
        positive_directory(directory.parent)
        self.capacity_check(directory.parent)
        directory.mkdir(mode=0o700)
        manifest = export(directory / 'material', items, self.capacity_check)
        if self.protection is not None:
            await self.protection.qualify(self, directory / 'material', publish)
        self.authorize_creation(current_authority)
        prompt = (text + '\nSelected immutable material is at ' + str(directory / 'material') +
                  '/manifest.json. Read its history first, then complete current method, diff and source. '
                  'Only this snapshot is admitted. Read files in bounded sections and retain unread limits. '
                  'No agents, network access, tests, source writes, private stores or startup discovery. Use only admitted local read commands.\n')
        private_write(directory / 'prompt.txt', prompt.encode(), self.capacity_check)
        filesystem = self.protection.filesystem(directory / 'material', self.workspace) if self.protection else None
        argv = command(self.profile, self.workspace, directory / 'material', self.thread, filesystem=filesystem)
        argv[0] = self.executable
        if self.execution is not None:
            argv = self.execution.prepare(argv, self.profile)
        private_write(directory / 'launch.json', json.dumps(dict(argv=self.execution.public_command(argv) if self.execution else argv, profile=self.profile,
            collector=self.collector, expected_thread=self.thread, permissions='requested; qualify enforcement separately',
            model_reference='opaque consumer selection; normal provider internals supply no identity attestation')).encode(), self.capacity_check)
        env = {'PATH': '/usr/local/bin:/usr/bin:/bin', 'HOME': self.account_home,
               'CODEX_HOME': str(Path(self.account_home) / self.profile),
               'XDG_CONFIG_HOME': str(self.root / 'xdg'),
               'TMPDIR': str(directory / 'tmp'), 'PYTHONDONTWRITEBYTECODE': '1'}
        self.capacity_check(directory)
        (directory / 'tmp').mkdir(mode=0o700)
        self.busy = True
        try:
            result = await execute(argv, env, prompt, directory, self.originals, publish,
                min(self.lifetime, self.created + self.lifetime - self.clock()), shutdown,
                maximum, capture_max, self.thread, started, admission,
                lambda: self.authorize_creation(current_authority), self.capacity_check)
        except BaseException:
            self.state = 'interrupted'
            raise
        finally:
            self.busy = False
        code, receipt, answer = result
        self.calls += 1
        self.thread = receipt.get('thread') or self.thread
        self.state = 'live' if receipt['answered'] else 'interrupted'
        receipt.update(transport=VERSION, profile=self.profile, collector=self.collector,
                       input=self.calls - 1, material=manifest, executable=self.executable,
                       root_end='not a native root', processing_completion=False)
        private_write(directory / 'receipt.json', json.dumps(receipt, ensure_ascii=False).encode(), self.capacity_check)
        return code, receipt, answer

    def close(self, collector):
        if collector != self.collector or self.busy or self.originals.owned:
            raise ReviewRefusal('close requires idle original collector and collected processes')
        self.state = 'closed'
        return dict(transport=VERSION, local_owner_closed=True, caller_processes_collected=True,
                    provider_storage='retained and unmeasured', provider_root_end='not applicable',
                    processing_completion=False)


async def execute(argv, env, prompt, directory, originals, publish, deadline, shutdown,
                  maximum, capture_max, expected_thread, started,
                  admission=existing_admission, before_spawn=lambda: None, capacity_check=lambda parent: None, before_feed=None):
    """Own before feeding input; numeric END and pipe EOF are independent."""
    evidence = dict(errors=[], stdout_eof=False, stderr_eof=False, bytes={'stdout': 0, 'stderr': 0})
    observed = dict(thread=None, completed=0, failed=False, answer=None, diagnostics=[])
    captures = []
    observations = 0
    protocol_failed = False
    receipt_attempts = []
    stop_at = time.monotonic() + deadline

    async def finish(entry):
        nonlocal observations
        try:
            results = await asyncio.wait_for(asyncio.gather(*captures, return_exceptions=True), shutdown)
            for result in results:
                if isinstance(result, BaseException):
                    error = 'capture task failed: ' + type(result).__name__
                    if error not in evidence['errors']:
                        evidence['errors'].append(error)
        except (asyncio.TimeoutError, asyncio.CancelledError):
            evidence['errors'].append('pipe EOF unobserved; capture partial')
        # Reserve the next name before any fallible persistence. A failed
        # exclusive create/write/flush/fsync remains untouched; normal retry
        # uses another name under this SAME owned finalizer, never file recovery.
        receipt_name = 'original-' + str(observations) + '.json'
        observations += 1
        receipt_attempts.append(receipt_name)
        entry['evidence'] = dict(evidence, receipt_attempts=list(receipt_attempts))
        private_write(directory / receipt_name,
                      json.dumps(dict(actual_END=entry['exit'], evidence=entry['evidence'])).encode(), capacity_check)

    def stop(reason):
        evidence['errors'].append(reason)
        try:
            child.terminate()
        except ProcessLookupError:
            pass

    def reject(reason):
        nonlocal protocol_failed
        protocol_failed = True
        observed['failed'] = True
        stop(reason)

    def event(line):
        try:
            record = json.loads(line)
            kind = record['type']
            if not isinstance(kind, str):
                raise TypeError('event kind must be a string')
        except (ValueError, KeyError, TypeError):
            reject('invalid JSON event; no complete capture claim')
            return
        if kind == 'thread.started':
            value = record.get('thread_id')
            if (not isinstance(value, str) or not re.fullmatch(r'[0-9a-fA-F-]{36}', value)
                    or observed['thread'] not in (None, value)
                    or expected_thread not in (None, value)):
                reject('public thread identity missing/changed')
            else:
                observed['thread'] = value
        if kind == 'turn.completed':
            observed['completed'] += 1
        if kind in {'turn.failed', 'error'}:
            observed['failed'] = True
        item = record.get('item', {})
        if not isinstance(item, dict) or ('type' in item and not isinstance(item['type'], str)):
            reject('malformed item event; capture partial')
            return
        if kind in {'error', 'turn.failed'} or item.get('type') == 'error':
            if len(observed['diagnostics']) >= 64:
                reject('diagnostic count exceeds selected bound; capture partial')
                return
            observed['diagnostics'].append(diagnostic(record, item))
        if kind.startswith('item.') and item.get('type') not in {
                'agent_message', 'reasoning', 'command_execution', 'todo_list', 'plan', 'error'}:
            reject('unexpected item activity; tool/effect semantics unclassified; preserve original effects')
            return
        if kind == 'item.completed' and item.get('type') == 'agent_message':
            answer = item.get('text')
            if not isinstance(answer, str) or len(answer.encode()) > maximum:
                reject('complete answer exceeds admitted UTF-8 output bound')
            else:
                observed['answer'] = answer

    async def capture(pipe, name):
        pending = b''
        try:
            capacity_check(directory)
            with (directory / (name + '.jsonl' if name == 'stdout' else name + '.bin')).open('xb') as stream:
                while True:
                    data = await pipe.read(16384)
                    if not data:
                        evidence[name + '_eof'] = True
                        break
                    before = evidence['bytes'][name]
                    evidence['bytes'][name] += len(data)
                    kept = data[:max(0, capture_max - before)]
                    capacity_check(directory)
                    stream.write(kept)
                    if evidence['bytes'][name] > capture_max:
                        stop(name + ' capture limit; retained prefix is partial')
                    if name != 'stdout' or evidence['bytes'][name] > capture_max:
                        continue
                    pending += kept
                    lines = pending.split(b'\n')
                    pending = lines.pop()
                    for line in lines:
                        if line and not protocol_failed:
                            try:
                                event(line)
                            except Exception as exc:
                                # Reject semantic handling, but continue retaining and
                                # draining this same original's bytes to actual EOF.
                                reject('event handler failed: ' + type(exc).__name__)
                if name == 'stdout' and pending and not protocol_failed:
                    try:
                        event(pending)
                    except Exception as exc:
                        reject('event handler failed: ' + type(exc).__name__)
        except (OSError, UnicodeError) as exc:
            stop(name + ' capture failed: ' + type(exc).__name__)

    async def feed():
        try:
            # Process creation and task scheduling both await. Recheck on this
            # task immediately before consequential delivery, with no await gap.
            (before_spawn if before_feed is None else before_feed)()
            child.stdin.write(prompt.encode())
            await child.stdin.drain()
        except (BrokenPipeError, ConnectionResetError):
            evidence['errors'].append('input delivery interrupted')
        finally:
            child.stdin.close()

    timed_out = False
    code = None
    key = None
    # The shared pool fences creation and ownership registration only. The
    # context busy flag and Originals retain custody across the entire tail.
    try:
        async with admission():
            before_spawn()
            child = await asyncio.create_subprocess_exec(*argv, env=env,
                stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            key = originals.own(child, 'opaque-cli-process', finish, publish)
        captures.extend([asyncio.create_task(capture(child.stdout, 'stdout')),
                         asyncio.create_task(capture(child.stderr, 'stderr'))])
        started()
        await asyncio.wait_for(feed(), max(.001, stop_at - time.monotonic()))
        try:
            code = await asyncio.wait_for(asyncio.shield(child.wait()), max(.001, stop_at - time.monotonic()))
            originals.owned[key]['exit'] = code
        except asyncio.TimeoutError:
            timed_out = True
            stop('original selected lifetime exceeded')
    finally:
        if key is not None:
            if len(captures) != 2:
                evidence['errors'].append('capture setup incomplete; original retained')
            code = await originals.finish(key, shutdown)
    complete = evidence['stdout_eof'] and evidence['stderr_eof'] and not evidence['errors']
    answered = (code == 0 and complete and observed['thread'] is not None
                and observed['completed'] == 1 and not observed['failed'] and bool(observed['answer']))
    receipt = dict(actual_END=code, original=key, capture_complete=complete, answered=answered,
                   thread=observed['thread'], turn_completed=observed['completed'],
                   turn_failed=observed['failed'], diagnostics=observed['diagnostics'], lifetime_exceeded=timed_out, **evidence)
    return code, receipt, observed['answer']
