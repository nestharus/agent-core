"""Finite runtime-specific Codex direct entry. No legacy dispatcher or Board.

The original caller owns all Popen objects. Only sanitized, bounded results are
published to runtime state. Opaque provider internals need separate qualification.
"""
import json
import importlib.util
import os
from pathlib import Path
import re
import selectors
import shutil
import signal
import subprocess
import time
import tomllib

from runtime import ALLOWED_PROFILES, FRESH_REVIEW, _fast, _pool, require
from storage import Held, digest, encode


class Redactor:
    """Streaming literal/JSON-escaped declared values, including split chunks."""
    def __init__(self, values):
        require(isinstance(values, list) and len(values) <= 32, 'at most 32 declared secrets')
        patterns = set()
        for value in values:
            require(isinstance(value, str) and 0 < len(value.encode()) <= 512,
                    'declared secret must have 1..512 UTF-8 bytes')
            patterns.update([value.encode(), json.dumps(value)[1:-1].encode(),
                             json.dumps(value, ensure_ascii=False)[1:-1].encode()])
        require(not any(p in b'[REDACTED]' for p in patterns), 'secret conflicts with publication marker')
        self.patterns = sorted(patterns, key=len, reverse=True)
        self.maximum = max(map(len, patterns), default=1)
        self.pending = b''

    def feed(self, chunk, final=False):
        self.pending += chunk
        out = bytearray()
        offset = 0
        while len(self.pending) - offset >= (1 if final else self.maximum):
            match = next((p for p in self.patterns if self.pending.startswith(p, offset)), None)
            if match:
                out.extend(b'[REDACTED]')
                offset += len(match)
            else:
                out.append(self.pending[offset])
                offset += 1
        self.pending = self.pending[offset:]
        return bytes(out)

    def whole(self, value):
        return self.feed(value, final=True)


def drain(process, payload, limit, timeout, values):
    """Bound memory and time, concurrently feed stdin and drain merged output.

    On timeout kill only this newly owned process group and collect its original.
    The caller has the process object BEFORE any output is read or filtered.
    """
    redactor = Redactor(values)
    output = bytearray()
    seen = sanitized = 0
    timed_out = overflow_stopped = False
    deadline = time.monotonic() + timeout
    io_error = False
    offset = 0
    try:
        with selectors.DefaultSelector() as selector:
            for stream in (process.stdin, process.stdout):
                os.set_blocking(stream.fileno(), False)
            selector.register(process.stdout, selectors.EVENT_READ)
            if payload:
                selector.register(process.stdin, selectors.EVENT_WRITE)
            else:
                process.stdin.close()
            while selector.get_map():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    timed_out = True
                    break
                for key, _ in selector.select(min(remaining, .1)):
                    if key.fileobj is process.stdin:
                        try:
                            offset += os.write(process.stdin.fileno(), payload[offset:offset + 4096])
                        except BrokenPipeError:
                            selector.unregister(process.stdin)
                            process.stdin.close()
                            continue
                        if offset == len(payload):
                            selector.unregister(process.stdin)
                            process.stdin.close()
                    else:
                        chunk = os.read(process.stdout.fileno(), 4096)
                        if not chunk:
                            selector.unregister(process.stdout)
                            process.stdout.close()
                        else:
                            seen += len(chunk)
                            clean = redactor.feed(chunk)
                            sanitized += len(clean)
                            output.extend(clean[:max(0, limit - len(output))])
                            if seen > 4 * limit:
                                overflow_stopped = True
                                deadline = 0
    except OSError:
        io_error = True
    finally:
        if timed_out or io_error:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        for stream in (process.stdin, process.stdout):
            if not stream.closed:
                stream.close()
    clean = redactor.feed(b'', final=True)
    sanitized += len(clean)
    output.extend(clean[:max(0, limit - len(output))])
    try:
        end = process.wait(timeout=5 if timed_out or io_error else max(.001, deadline - time.monotonic()))
    except subprocess.TimeoutExpired:
        timed_out = True
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        end = process.wait(timeout=5)
    return bytes(output), {'end': end, 'seen_bytes': seen, 'published_bytes': len(output),
                           'complete': not timed_out and not io_error and sanitized <= limit and offset == len(payload),
                           'input_complete': offset == len(payload), 'io_error': io_error,
                           'timed_out': timed_out and not overflow_stopped, 'overflow_stopped': overflow_stopped}


def mcp_rows(raw):
    rows = json.loads(raw)
    require(isinstance(rows, list) and len(rows) <= 64, 'finite MCP list required')
    result = {}
    for row in rows:
        name, enabled = row['name'], row['enabled']
        require(isinstance(name, str) and re.fullmatch('[A-Za-z0-9_-]{1,80}', name)
                and type(enabled) is bool and name not in result, 'invalid MCP entry')
        result[name] = enabled
    return result


def opaque_task_flags(routes, raw, profile, flags):
    """Consume the existing public opaque capability, without inspecting it.

    Only provider internals prepare the binding. No dispatch, allocation,
    account query, historical context or continuing composition is selected.
    The reader supplies the already admitted frozen public control bytes.
    """
    path = Path(__file__).resolve().parents[1] / 'direct-child' / 'dispatch.py'
    try:
        spec = importlib.util.spec_from_file_location('file_runtime_opaque_entry', path)
        entry = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(entry)
    except (ImportError, OSError) as exc:
        raise Held('public opaque entry unavailable; no substitution') from exc
    try:
        execution = entry.open_opaque_execution(routes, 'gpt-xhigh', profile,
                                                config_reader=lambda path, maximum: raw)
        return execution.prepare(['codex', *flags], profile)[1:]
    except entry.Refusal as exc:
        raise Held('public opaque capability refused; no substitution') from exc


def review_association(state, attempt, attempt_id):
    """Explicit references for a fresh call, never historical-session recovery."""
    review = state['reviews'][attempt['review']]
    require(review.get('execution_contract') == FRESH_REVIEW and review['opaque_contract'] == 'gpt-xhigh',
            'opaque Reviews provider unsupported; existing owner contract retained')
    prior = state['reviews'][review['predecessor']] if review['predecessor'] is not None else None
    return {'execution_contract': FRESH_REVIEW, 'review': attempt['review'],
            **{k: review[k] for k in ('component', 'opaque_contract', 'context', 'history')},
            'branch': {'id': review['branch'], **state['branches'][review['branch']]},
            'predecessor': None if prior is None else {'review': review['predecessor'],
                **{k: prior[k] for k in ('component', 'branch', 'opaque_contract', 'context', 'history')}},
            'prior_calls': [call for call in review['calls'] if call != attempt_id],
            'attempt': attempt_id, 'event': attempt['event'],
            'resources': attempt['resources'], 'basis': attempt['basis']}


class Codex:
    """Production command is fixed. A library-only public process seam tests it.

    No fake account tree is needed: fixed test processes never inspect profiles.
    No CLI option permits replacing the executable or environment.
    """
    def __init__(self, command=None):
        if command is None:
            # Locate public code before constructing the minimal environment.
            # This is no provider, profile or authentication query.
            executable = shutil.which('codex')
            require(executable is not None, 'Codex executable unavailable; reservation retained')
            command = [str(Path(executable).absolute())]
        self.command = list(command)
        self.originals = []
        self.cancelled = False
        self.received = None
        self.current = None
        self.task_entered = False
        self.creating = False
        self.stage = None
        self.refusal_recorded = False
        self.report = None

    def cancel(self, sig, frame):
        self.cancelled = True
        self.received = sig
        if self.current is not None:
            try:
                os.killpg(self.current.pid, sig)
            except ProcessLookupError:
                pass

    def create(self, rt, actor, credential, attempt, collector, args, cwd, values):
        # No lock spans preflight/model execution. Recheck every actual creation,
        # including metadata processes; no second allocation or profile search.
        refusal = None
        with rt.files.transaction() as state:
            a = rt.attempt(state, actor, attempt, collector)
            require(a['state'] == 'launching' and a['substrate'] == 'codex-direct', 'original launch required')
            try:
                rt.authority(state, actor, credential)
                require(not self.cancelled, 'cancelled before process creation')
                rt.partial_capacity(state)
                with rt.pool(state).admission(a['pool']['profile'], ALLOWED_PROFILES, blocking=False,
                                             expected_control=state['pool_binding']):
                    with _fast.admission(Path(state['pool_routes']).with_name('fast-tier'), before_write=rt.pool_capacity):
                        # Original account only. Never inherit runtime secrets.
                        env = {'PATH': os.defpath, 'HOME': str(Path.home()),
                               'CODEX_HOME': str(Path.home() / a['pool']['profile'])}
                        command = self.command + args
                        require(Redactor(values).whole(encode(command)) == encode(command), 'secret in provider command refused')
                        self.creating = True
                        if self.stage == 'task':
                            self.task_entered = True
                        process = subprocess.Popen(command, cwd=cwd, env=env, stdin=subprocess.PIPE,
                                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT, start_new_session=True)
                        self.originals.append(process)
                        self.current = process
                        if self.received is not None:
                            self.cancel(self.received, None)
            except (Held, _pool.PoolError, ValueError, OSError) as exc:
                if self.creating:
                    raise  # Popen or postcreation ambiguity is never unstarted.
                # Like the fixture boundary, preserve the refusal even if the
                # actor was just revoked. No collector/effect rights are granted.
                a.update(state='not-started', creation_refusal={'actor': actor, 'at': rt.clock(),
                         'evidence': 'controls/authority refused before task creation'},
                         provider_report={**self.report, 'failure': 'precreation authority/control refusal'})
                rt.partial_capacity(state)
                refusal = exc
        self.creating = False
        if refusal is not None:
            self.refusal_recorded = True
            raise Held('provider creation refused before Popen') from refusal
        return process


def run_provider(rt, actor, credential, request, *, adapter=None):
    """One reserved attempt; no retries, fallback, resume or external final file."""
    required = {'attempt', 'collector', 'prompt', 'cwd', 'output_limit', 'timeout', 'declared_secrets'}
    require(set(request) == required, 'provider requires exact bounded input fields')
    attempt, collector = request['attempt'], request['collector']
    limit, timeout = request['output_limit'], request['timeout']
    require(type(limit) is int and 1024 <= limit <= 65536 and type(timeout) is int and 1 <= timeout <= 3600,
            'output_limit 1024..65536 and timeout 1..3600 required')
    require(isinstance(request['prompt'], str) and 0 < len(request['prompt'].encode()) <= 16384, 'prompt bound 16KiB')
    require(isinstance(request['cwd'], str) and Path(request['cwd']).is_absolute()
            and len(encode(request['cwd'])) <= 512, 'explicit bounded absolute working directory required')
    require(isinstance(request['declared_secrets'], list) and len(request['declared_secrets']) <= 30, 'at most 30 caller secrets')
    values = request['declared_secrets'] + [credential, collector]
    prompt = Redactor(values).whole(request['prompt'].encode())
    require(len(prompt) <= 16384, 'sanitized prompt bound 16KiB')
    adapter = Codex() if adapter is None else adapter
    report = {'processes': [], 'served_tier': 'unobserved', 'semantic_acceptance': False}
    adapter.report = report
    start = rt.call('start', actor, credential, attempt=attempt, collector=collector,
                    substrate='codex-direct', evidence='bounded runtime Codex direct adapter; no platform SQL attestation')
    publication_entered = False
    previous = {s: signal.signal(s, adapter.cancel) for s in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP)}
    try:
        with rt.files.transaction(readonly=True, continuation=True) as state:
            rt.authority(state, actor, credential)
            a = rt.attempt(state, actor, attempt, collector)
            raw, _, _ = rt.pool(state).read()
            rt.pool(state).assert_control(raw, state['pool_binding'])
            task_flags = ['exec', '--dangerously-bypass-approvals-and-sandbox', '--ephemeral', '--json']
            if a['selector'] == 'opaque-reviews':
                association = review_association(state, a, attempt)
                require(Redactor(values).whole(encode(association)) == encode(association),
                        'secret in review association; preserve exact references outside execution')
                prompt = encode({'review_execution': association, 'task': prompt.decode()})
                require(len(prompt) <= 16384, 'review envelope bound 16KiB')
                task_flags = opaque_task_flags(state['pool_routes'], raw, a['pool']['profile'],
                                               task_flags + ['--model', 'gpt-xhigh'])
                report['review_execution'] = {'contract': FRESH_REVIEW, 'selector': 'gpt-xhigh',
                    'association_sha256': digest(association), 'fresh': True, 'exact_session_resume': False}
            else:
                config = tomllib.loads(raw.decode())
                route = {'luna-low': ('explore', 'low'), 'sol-xhigh': ('refine', 'xhigh')}.get(a['selector'])
                require(route is not None, 'unsupported provider selector; no substitution')
                binding = config['routes'][route[0]]
                model, effort = binding['model'], route[1]
                require(binding['provider'] == 'codex' and re.fullmatch('[A-Za-z0-9._-]{1,80}', model)
                        and effort in config['providers']['codex']['efforts'], 'unsupported static provider binding')
                task_flags += ['-m', model, '-c', 'model_reasoning_effort=' + json.dumps(effort)]

        def invoke(stage, flags, payload=b''):
            adapter.stage = stage
            p = adapter.create(rt, actor, credential, attempt, collector, flags, request['cwd'], values)
            out, fact = drain(p, payload, limit, timeout, values)
            report['processes'].append({'stage': stage, **fact})
            adapter.current = None
            return out, fact

        discovered, fact = invoke('mcp-discovery', ['-c', 'mcp_servers={}', 'mcp', 'list', '--json'])
        require(fact['end'] == 0 and fact['complete'], 'MCP discovery incomplete/failed')
        names = set(mcp_rows(discovered)) | {'openaiDeveloperDocs'}
        flags = ['-c', 'mcp_servers={}', '-c', 'mcp_servers.openaiDeveloperDocs.url="https://developers.openai.com/mcp"']
        for name in sorted(names):
            flags += ['-c', f'mcp_servers.{name}.enabled=false']
        verified, fact = invoke('mcp-disabled', flags + ['mcp', 'list', '--json'])
        require(fact['end'] == 0 and fact['complete'] and mcp_rows(verified) == dict.fromkeys(names, False),
                'effective MCP all-disabled readback failed')
        out, fact = invoke('task', [*task_flags,
                           *_fast.flags(True), *flags, '-C', request['cwd'], '--color', 'never', '-'], prompt)
        result = {'provider_incomplete': True}
        try:
            require(fact['complete'] and not adapter.cancelled, 'task incomplete or cancelled')
            messages = [row['item']['text'] for row in map(json.loads, out.splitlines())
                        if row.get('type') == 'item.completed' and row.get('item', {}).get('type') == 'agent_message']
            require(len(messages) == 1, 'one final agent message required; no synthetic final')
            result = json.loads(messages[0])
            result = json.loads(Redactor(values).whole(encode(result)))
            require(len(encode(result)) <= 4096, 'final exceeds 4KiB publication bound')
        except (ValueError, KeyError, TypeError, Held):
            report['final_complete'] = False
            result = {'provider_incomplete': True}
        else:
            report['final_complete'] = True
        publication_entered = True
        rt.call('provider_report', actor, credential, attempt=attempt, collector=collector, report=report)
        return rt.call('collect', actor, credential, attempt=attempt, collector=collector,
                       launch_id=start['launch_id'], end=fact['end'], result=result,
                       evidence='original Popen numeric END; provider_report separates capture/final/acceptance')
    except (Held, _pool.PoolError, ValueError, KeyError, TypeError, OSError) as exc:
        # Diagnostics never echo provider output, declared inputs, paths or secrets.
        # Missing task original/after-Popen failures stay launching, never replayed.
        report['failure'] = 'provider boundary refused; original evidence retained by caller'
        for original in adapter.originals:
            if original.returncode is None:
                try:
                    os.killpg(original.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                # Creation may have succeeded before a metadata failure. Own
                # and collect that exact original; never start another one.
                _, fact = drain(original, b'', limit, 5, values)
                report['processes'].append({'stage': adapter.stage, 'aborted_after_error': True, **fact})
        if not publication_entered and not adapter.refusal_recorded:
            rt.call('provider_report', actor, credential, attempt=attempt, collector=collector,
                    report=report, not_started=not adapter.task_entered and not adapter.creating
                    and all(p.returncode is not None for p in adapter.originals))
        raise Held('provider incomplete; inspect owned attempt and original collector; no replay') from exc
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)
