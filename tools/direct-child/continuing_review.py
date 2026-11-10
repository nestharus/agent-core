"""Public continuing opaque reviewer over owned CLI originals.

The selector is accepted unchanged. No saved-session import, selector resolver,
profile discovery or replay exists. Trusted runtime/OS and caller admission of
immutable input bytes are explicit premises; see continuing-review.md.
"""
import asyncio
from contextlib import asynccontextmanager
import errno
import hashlib
import json
import os
from pathlib import Path
import time
import shlex
import stat
if __package__:
    from .opaque_dialogue import Dialogue, Reply, Refusal
    from .review_context import Context, command, private_write
else:
    from opaque_dialogue import Dialogue, Reply, Refusal
    from review_context import Context, command, private_write


PROBE = r"""import json,socket,sys
from pathlib import Path
allowed,outside,write,port=sys.argv[1:]
r={}
for name,path in [('allowed',allowed),('outside',outside)]:
 try:r[name]={'read':Path(path).read_text()}
 except OSError as e:r[name]={'error':e.errno}
try:Path(write).write_text('owned-probe-write');r['write']='succeeded'
except OSError as e:r['write']={'error':e.errno}
try:
 s=socket.socket();s.settimeout(1);s.connect(('127.0.0.1',int(port)));r['network']='succeeded';s.close()
except OSError as e:r['network']={'error':e.errno}
print(json.dumps(r))
"""


def probe_command(allowed, outside, write, port, helper=None):
    """One command builder shared by local and provider qualification.

    The selected callback rechecks public identity and lawful read authority.
    Isolated Python startup ignores account/cwd/PYTHONPATH and site hooks.
    Legacy compositions retain their earlier invocation and its qualifications.
    """
    prefix = [helper(), '-I', '-S', '-B'] if helper else ['/usr/bin/python3']
    return [*prefix, '-c', PROBE, str(allowed), str(outside), str(write), str(port)]


class SandboxProtection:
    """Actual discriminating local sandbox controls, renewed for each export.

    The real provider's first turn must separately qualify its acting boundary
    before callers deliver substantive material. These controls alone establish
    the local sandbox backend only, not complete provider tool routing.
    """
    def __init__(self, root, executable, runtime_reads, capacity_check, *, probe_helper=None, admit_read=None, before_io=lambda path, operation, amount=0: None, policy_authority=None):
        self.root, self.executable = Path(root), executable
        if not runtime_reads or any(not Path(p).is_absolute() for p in runtime_reads):
            raise Refusal('explicit public runtime read dependencies required')
        if not Path(executable).is_absolute():
            raise Refusal('absolute selected sandbox executable required')
        self.runtime_reads = tuple(runtime_reads)
        self.capacity_check = capacity_check
        self.proofs = []
        self.probe_helper = probe_helper
        self.admit_read = admit_read
        self.before_io = before_io
        self.policy_authority = policy_authority

    def filesystem(self, material, workspace):
        # The backend re-executes this exact program inside its filesystem
        # view. Host identity alone does not put that pathname in the view.
        operands = (*self.runtime_reads, self.executable)
        if self.admit_read:
            for operand in operands:
                self.admit_read(operand)
        reads = dict.fromkeys(operands, 'read')
        if '/usr/lib64' in reads:
            # Identity/shape does not confer rights. Require the caller's actual
            # current positive/exclusion mediation before EACH acquisition and
            # before adding the alias to the policy. Legacy callers without a
            # mediator cannot introduce this additional operand.
            if self.admit_read is None:
                raise Refusal('runtime loader alias requires explicit read mediation')
            alias = Path('/lib64')
            self.admit_read(str(alias))
            info = alias.lstat()
            if not stat.S_ISLNK(info.st_mode) or info.st_uid != 0:
                raise Refusal('declared runtime loader alias changed')
            self.admit_read(str(alias))
            if os.readlink(alias) != 'usr/lib64':
                raise Refusal('declared runtime loader alias changed')
            self.admit_read('/usr/lib64')
            self.admit_read(str(alias))
            reads[str(alias)] = 'read'
        return {':root': 'deny', ':minimal': 'read', **reads,
                str(material): 'read', str(workspace): 'read'}

    async def qualify(self, context, material, publish):
        directory = material.parent / 'protection'
        self.capacity_check(directory.parent)
        self.before_io(directory, 'mkdir')
        directory.mkdir(mode=0o700)
        allowed = material / 'protection-canary.txt'
        outside = directory / 'outside.txt'
        private_write(allowed, b'owned-allowed-canary', self.capacity_check, before_io=self.before_io)
        private_write(outside, b'owned-outside-canary', self.capacity_check, before_io=self.before_io)
        write = material / 'write-attempt.txt'
        server = await asyncio.start_server(lambda r, w: w.close(), '127.0.0.1', 0)
        try:
            port = server.sockets[0].getsockname()[1]
            filesystem = self.filesystem(material, context.workspace)
            encoded = '{' + ','.join(json.dumps(k)+'='+json.dumps(v) for k,v in filesystem.items()) + '}'
            program = probe_command(allowed, outside, write, port, self.probe_helper)
            argv = [self.executable, 'sandbox', '-C', str(context.workspace),
                    '-c', 'permissions.review-material.filesystem='+encoded,
                    '-c', 'permissions.review-material.network.enabled=false',
                    '-P', 'review-material', '--', *program]
            def before_control():
                # Complete helper identity may refresh rights/exclusions. The
                # local controls read the same generated material plus their
                # own outside canary; no stale policy grants those operands.
                for path in (allowed, outside):
                    self.before_io(path, 'read')
                # Even the nominally denied neighbor may write on failure.
                self.before_io(write, 'create', len(b'owned-probe-write'))
                if self.policy_authority is not None:
                    self.policy_authority(filesystem, material, context.workspace,
                                          controls=(allowed, outside, write))
            # The unprotected neighbor actually performs all four operations.
            control = await self._run(context, directory, 'control', program, publish, before_control)
            protected = await self._run(context, directory, 'protected', argv, publish, before_control)
            good_control = (control.get('allowed',{}).get('read') == 'owned-allowed-canary'
                and control.get('outside',{}).get('read') == 'owned-outside-canary'
                and control.get('write') == 'succeeded' and control.get('network') == 'succeeded')
            good_protection = (protected.get('allowed',{}).get('read') == 'owned-allowed-canary'
                and protected.get('outside',{}).get('error') in (errno.EACCES,errno.EPERM,errno.ENOENT)
                and protected.get('write',{}).get('error') in (errno.EACCES,errno.EPERM,errno.EROFS)
                and protected.get('network',{}).get('error') in (errno.EACCES,errno.EPERM))
            proof = dict(control=control, protected=protected, filesystem=filesystem,
                         passed=good_control and good_protection,
                         meaning='actual local sandbox controls; provider acting-boundary qualification separately owed')
            self.proofs.append(proof)
            private_write(directory/'result.json',json.dumps(proof).encode(),self.capacity_check, before_io=self.before_io)
            if not proof['passed']:
                raise Refusal('actual local sandbox qualification failed; substantive input withheld')
        finally:
            server.close()
            await server.wait_closed()

    async def _run(self, context, directory, name, argv, publish, before_run=lambda: None):
        self.capacity_check(directory)
        evidence = dict(stdout_eof=False, stderr_eof=False, errors=[])
        captures = []
        child = None
        results, receipt_attempts = [], []
        capture_failures_recorded = False
        async def finish(entry):
            nonlocal results, capture_failures_recorded
            # A completed failed drain is evidence of incomplete capture, not an
            # endlessly retryable capture operation. Keep real EOF facts intact.
            results = await asyncio.wait_for(
                asyncio.gather(*captures, return_exceptions=True), 3)
            if not capture_failures_recorded:
                for stream_name, result in zip(('stdout', 'stderr'), results):
                    if isinstance(result, BaseException):
                        evidence['errors'].append(
                            stream_name+' capture failed: '+type(result).__name__)
                capture_failures_recorded = True
            evidence['capture_complete'] = bool(evidence['stdout_eof']
                and evidence['stderr_eof'] and not evidence['errors'])
            # Persist before discharging this original's evidence duty. Reserve
            # each exclusive name first so partial failed writes survive retry.
            suffix = '' if not receipt_attempts else '-'+str(len(receipt_attempts))
            path = directory/(name+'.original'+suffix+'.json')
            receipt_attempts.append(path.name)
            receipt = dict(original=key, actual_END=entry['exit'],
                evidence=dict(evidence),
                stderr_bytes=len(results[1]) if isinstance(results[1], bytes) else None,
                receipt_attempts=list(receipt_attempts),
                collection_failures=list(entry['failures']))
            entry['evidence'] = dict(evidence, receipt=path.name,
                receipt_attempts=list(receipt_attempts), receipt_persisted=False)
            private_write(path, json.dumps(receipt).encode(), self.capacity_check, before_io=self.before_io)
            entry['evidence']['receipt_persisted'] = True
            if any(isinstance(r, BaseException) for r in results):
                raise Refusal('control capture acquisition remains pending on SAME original')
        # Prepare ordinary argv/environment before the final acting checks.
        env = {'PATH':'/usr/local/bin:/usr/bin:/bin','HOME':context.account_home,
               'CODEX_HOME':str(Path(context.account_home)/context.profile)}
        if self.probe_helper:
            self.probe_helper()  # Complete identity, then current permission.
        before_run()
        # Costly synchronous preparation can exhaust the fixed original even
        # when an event-loop timeout has not resumed. Refuse before creation;
        # a post-spawn timeout cannot authorize the earlier effect.
        if context.clock() >= context.created + context.lifetime:
            raise Refusal('local control original processing cutoff elapsed before creation')
        child = await asyncio.create_subprocess_exec(*argv, env=env,
            stdin=asyncio.subprocess.DEVNULL, stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE)
        key = context.originals.own(child, 'owned-sandbox-control', finish, publish)
        async def drain(pipe, stream_name):
            data = bytearray()
            path = directory/(name+'.'+stream_name)
            self.capacity_check(directory)
            self.before_io(path, 'create', 0)
            with path.open('xb') as out:
                while True:
                    self.before_io(path, 'read')
                    part = await pipe.read(8192)
                    if not part:
                        evidence[stream_name+'_eof'] = True
                        return bytes(data)
                    if len(data)+len(part)>65536:
                        evidence['errors'].append('bounded capture exceeded')
                        child.terminate()
                        part=part[:max(0,65536-len(data))]
                    self.capacity_check(directory)
                    self.before_io(path, 'append', len(part))
                    out.write(part); data.extend(part)
        try:
            captures.extend([asyncio.create_task(drain(child.stdout,'stdout')),
                             asyncio.create_task(drain(child.stderr,'stderr'))])
            code = await asyncio.wait_for(asyncio.shield(child.wait()),
                min(15,max(.001,context.created+context.lifetime-context.clock())))
            context.originals.owned[key]['exit'] = code
        finally:
            code = await context.originals.finish(key,3)
        raw, error = results
        if code != 0 or error or not evidence['capture_complete']:
            raise Refusal('sandbox control original failed; preserved captures and numeric END')
        return json.loads(raw)


class ExecEndpoint:
    """One logical handle; each turn has a separately collected CLI process.

    Open does no provider work. Actual NEW pool admission wraps process creation
    and Originals registration in Context.execute. No shared lock spans a turn.
    """
    def __init__(self, root, executable, originals, admission, authority,
                 protection, capacity_check, publish, *, execution=None, policy_authority=None, before_io=lambda path, operation, amount=0: None):
        self.root, self.executable, self.originals = Path(root), executable, originals
        self.admission, self.authority, self.protection = admission, authority, protection
        self.capacity_check, self.publish = capacity_check, publish
        self.probe_helper = protection.probe_helper
        self.context, self.owner, self.receipts = None, None, []
        self.execution = execution
        self.policy_authority = policy_authority
        self.before_io = before_io
        self.clock = time.monotonic
        self.directory = None
        self.started = lambda: None
        self.maximum, self.capture_max, self.shutdown = 2*1024**2, 32*1024**2, 3

    async def open(self, ownership):
        if self.context is not None or ownership.selector != 'gpt-xhigh':
            raise Refusal('one opaque owned context only; no reopen')
        if self.execution is None:
            raise Refusal('public opaque execution capability required before context creation')
        self.owner = ownership
        self.context = Context(self.root,ownership.profile,ownership.collector,
            int(ownership.expires-ownership.created),self.originals,
            clock=self.clock,executable=self.executable,protection=self.protection,
            origin=ownership.created,capacity_check=self.capacity_check,execution=self.execution,
            policy_authority=self.policy_authority, before_io=self.before_io)
        return self.context

    async def exchange(self, handle, ownership, thread, text, channel):
        if handle is not self.context or ownership is not self.owner or thread != handle.thread:
            raise Refusal('original owner/handle/thread mismatch')
        self.authority(ownership)
        items=[]
        # These events record transport export, never purported provider reads.
        for item in channel.manifest():
            chunks=[]
            for offset in range(0,item['bytes'],12000):
                chunks.append(channel.request(dict(op='read',item=item['item'],offset=offset,limit=12000)))
            body=b''.join(chunks)
            if hashlib.sha256(body).hexdigest()!=item['sha256']:
                raise Refusal('immutable material export mismatch')
            items.append((item['label'],body))
        admission = (lambda: self.admission(ownership.profile)) if handle.state == 'new' else existing_admission
        code, receipt, answer = await handle.turn(self.directory or self.root/('turn-'+str(handle.calls)),items,text,
            collector=ownership.collector,profile=ownership.profile,
            current_authority=lambda:self.authority(ownership),
            current_profiles={ownership.profile},publish=self.publish,maximum=self.maximum,
            capture_max=self.capture_max,shutdown=self.shutdown,started=self.started,admission=admission)
        self.receipts.append(receipt)
        return Reply(receipt.get('thread') or 'unobserved',answer or '',bool(receipt['answered']))

    async def close(self, handle, ownership):
        if handle is not self.context or ownership is not self.owner:
            raise Refusal('original owner required for local close')
        await self.originals.collect_pending(3)
        return handle.close(ownership.collector)


@asynccontextmanager
async def existing_admission(profile=None):
    yield


def _dialogue(endpoint, profile, collector, authority, *, lifetime=7200, clock=time.monotonic, origin=None, material_authority=None):
    """A new public continuation contract; ordinary dispatch remains fresh."""
    return Dialogue(endpoint,profile,collector,authority,existing_admission,
                    lifetime=lifetime,answer_bytes=getattr(endpoint,"maximum",2*1024**2),clock=clock,origin=origin,material_authority=material_authority)


def canary_command_matches(observed, expected):
    """Require the runtime-attributed command, never an agent's quoted output."""
    if observed == expected:
        return True
    try:
        parts = shlex.split(observed)
    except (ValueError, TypeError):
        return False
    return (len(parts) == 3 and parts[0] in {'/bin/bash','/usr/bin/bash','/bin/sh'}
            and parts[1] in {'-lc','-c'} and parts[2] == expected)


def denied_operation(value, errors):
    return (isinstance(value, dict) and type(value.get('error')) is int
            and value['error'] in errors)


def canary_result(item):
    if type(item.get('exit_code')) is not int or item['exit_code'] != 0 or item.get('status') != 'completed':
        raise Refusal('exact provider canary did not complete successfully; substantive input withheld')
    try:
        row = json.loads(item['aggregated_output'])
    except (KeyError, ValueError, TypeError) as exc:
        raise Refusal('exact provider canary output malformed; substantive input withheld') from exc
    if not isinstance(row, dict) or not isinstance(row.get('allowed'), dict):
        raise Refusal('exact provider canary operation evidence malformed; substantive input withheld')
    if (row['allowed'].get('read') != 'owned-allowed-canary'
            or not denied_operation(row.get('outside'), (errno.EACCES, errno.EPERM, errno.ENOENT))
            or not denied_operation(row.get('write'), (errno.EACCES, errno.EPERM, errno.EROFS))
            or not denied_operation(row.get('network'), (errno.EACCES, errno.EPERM))):
        raise Refusal('exact provider canary protection adverse or incomplete; substantive input withheld')
    return row


def acting_proof(capture, expected):
    matches = []
    for line in capture.splitlines():
        try:
            record = json.loads(line)
        except ValueError as exc:
            raise Refusal('malformed acting-boundary capture') from exc
        if not isinstance(record, dict) or not isinstance(record.get('item', {}), dict):
            raise Refusal('malformed acting-boundary event')
        item = record.get('item', {})
        if (record.get('type') == 'item.completed' and item.get('type') == 'command_execution'
                and canary_command_matches(item.get('command'), expected)):
            # Count every exact execution before interpreting success. Otherwise
            # an adverse retained operation can disappear beside one favorable one.
            matches.append(item)
    if len(matches) != 1:
        raise Refusal('actual uniquely attributed provider canary operation unqualified; substantive input withheld')
    return canary_result(matches[0])


class ContinuingReview:
    """Public protected continuation owner. Qualify before substantive turns.

    It exposes no saved-context attachment and no switch to another provider.
    First qualification is a real nonsecret turn of the sole owned conversation.
    Failure closes that line; no second context, replay or automatic fallback.
    """
    def __init__(self, endpoint, selector, profile, collector, authority, *, lifetime=7200, clock=time.monotonic, origin=None, material_authority=None):
        if selector!='gpt-xhigh':
            raise Refusal('this receiving contract accepts opaque gpt-xhigh only')
        self.endpoint,self.collector=endpoint,collector
        self._dialogue=_dialogue(endpoint,profile,collector,authority,lifetime=lifetime,clock=clock,origin=origin,material_authority=material_authority)
        self.proof=None
        self.attempted=False

    @property
    def ownership(self):
        return self._dialogue.ownership

    @property
    def status(self):
        return dict(**self._dialogue.status,protection_qualified=self.proof is not None,
                    qualification_attempted=self.attempted)

    async def qualify(self):
        if self.attempted:
            raise Refusal('one qualification attempt only; no new conversation or replay')
        self.attempted=True
        directory=self.endpoint.root/'turn-0'
        server=await asyncio.start_server(lambda r,w:w.close(),'127.0.0.1',0)
        try:
            port=server.sockets[0].getsockname()[1]
            argv=probe_command(directory/'material/protection-canary.txt',
                  directory/'protection/outside.txt', directory/'material/provider-write.txt',
                  port, getattr(self.endpoint, 'probe_helper', None))
            expected=shlex.join(argv)
            prompt=('This is the sole owned nonsecret tool-protection qualification turn. '
                    'No review/method/history/source is admitted yet. No children, messages or other providers. '
                    'Run the following EXACT command once with the command execution tool; '
                    'do not simulate the output or rewrite the program. These are all newly owned canaries. '
                    'The program tests an allowed read, denied outside read, denied material write, '
                    'and denied connection to an owned loopback listener. Return a short factual account.\n'+expected)
            await self._dialogue.turn(self.collector,prompt,{'nonsecret qualification':b'owned canaries only'})
            receipt=self.endpoint.receipts[-1]
            if not receipt['answered'] or not receipt['capture_complete']:
                raise Refusal('actual qualification turn incomplete; no substantive input')
            # This is the exact freshly owned completed capture, never a foreign
            # session, private store, lost handle or tool-history reconstruction.
            self.endpoint.before_io(directory/'stdout.jsonl', 'read')
            capture=(directory/'stdout.jsonl').read_text()
            proof=acting_proof(capture,expected)
            private_write(directory/'acting-proof.json',json.dumps(proof).encode(),self.endpoint.capacity_check, before_io=self.endpoint.before_io)
        finally:
            server.close()
            await server.wait_closed()
        # Admission commits only after the entire qualification call succeeds,
        # including proof persistence and owned listener finalization.
        self.proof=proof
        return self.proof

    async def turn(self, text, materials):
        if self.proof is None:
            raise Refusal('effective acting-boundary qualification required before substantive input')
        return await self._dialogue.turn(self.collector,text,materials)

    async def close(self):
        return await self._dialogue.close(self.collector)
