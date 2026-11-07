"""Continuing first-four owner process and its reconnectable control endpoint.

One foreground original owns launch, wait, result custody and recovery. A lost
client reconnects to that process; a dead process never becomes a fresh collector
by reusing its name. Actual uncollected children stay UNKNOWN after a crash.
"""
import asyncio
from . import observations
import fcntl
import json
import os
from pathlib import Path
import signal
import socket
import struct

from .contracts import Refusal, digest, encode, required_text
from .processing import ProcessingDispatcher, Access, apply_control
from . import reviews, resource_scopes, windows
from .configuration import owned_service_conflict, assert_current

SCHEMA = """
CREATE TABLE IF NOT EXISTS processing_report_inputs(
 event TEXT PRIMARY KEY,capability TEXT NOT NULL,source_hash TEXT NOT NULL,receipt_hash TEXT NOT NULL);
CREATE TRIGGER IF NOT EXISTS processing_report_no_update BEFORE UPDATE ON processing_report_inputs
 BEGIN SELECT RAISE(ABORT,'immutable collected report input'); END;
CREATE TRIGGER IF NOT EXISTS processing_report_no_delete BEFORE DELETE ON processing_report_inputs
 BEGIN SELECT RAISE(ABORT,'immutable collected report input'); END;
CREATE TABLE IF NOT EXISTS service_runs(
 controller TEXT PRIMARY KEY,capability TEXT NOT NULL,socket TEXT NOT NULL,
 state TEXT NOT NULL,started REAL NOT NULL,returned REAL,receipt TEXT);
"""


def validate(runtime, selection):
    policy = selection['service']
    if (not isinstance(policy, dict) or set(policy) - {'report_tasks', 'admission', 'allocations', 'wake'} != {'max_inflight', 'reviews', 'legacy_resources'}
            or type(policy['max_inflight']) is not int or not 1 <= policy['max_inflight'] <= runtime.config['limits']['max_attempts']
            or not isinstance(policy['reviews'], dict) or not isinstance(policy['legacy_resources'], dict)
            or not selection['future_intake']):
        raise Refusal('continuing service needs concurrent capacity, selected Reviews, legacy resource account and future intake')
    report_tasks = policy.get('report_tasks', [])
    if (not isinstance(report_tasks, list) or len(report_tasks) > 1 or len(set(report_tasks)) != len(report_tasks)
            or any(t not in selection['tasks'] or runtime.config['tasks'][t]['role'] != 'Reviews'
                   or runtime.config['tasks'][t]['phase'] != 'integrator'
                   or runtime.config['tasks'][t].get('execution') == 'owner' for t in report_tasks)):
        raise Refusal('attributed reports need the selected sole software Reviews integrator')
    validate_admission(runtime, policy.get('admission'))
    from .service_wake import validate as validate_wake
    validate_wake(runtime, selection)
    windows.validate_delegation(runtime, selection)
    resource_scopes.validate(runtime, policy['legacy_resources'], selection)
    reviews.validate(runtime, policy['reviews'])
    if set(policy['reviews']) - set(selection['tasks']):
        raise Refusal('selected Reviews executor outside task authority')
    from .contracts import response_tasks
    for name in policy['reviews']:
        task = runtime.config['tasks'][name]
        choices = response_tasks(task, {'category': 'proposal'}, runtime.config)
        if not choices or any(runtime.config['tasks'][c]['role'] != 'Reviews' or runtime.config['tasks'][c]['phase'] != 'integrator' for c in choices):
            raise Refusal('ordinary Source needs actual sole Reviews report integration routes')


def validate_admission(runtime, policy):
    if policy is None:
        return
    if (not isinstance(policy, dict) or set(policy) != {'until', 'pause_bytes', 'max_new_inputs'}
            or type(policy['until']) not in {int, float} or not runtime.clock() < policy['until'] <= runtime.clock() + 3600
            or type(policy['pause_bytes']) is not int or not 4096 < policy['pause_bytes'] < runtime.config['limits']['max_bytes']
            or type(policy['max_new_inputs']) is not int or not 1 <= policy['max_new_inputs'] <= runtime.config['limits']['max_events']):
        raise Refusal('bounded one-hour admission, owned-byte pause and input count required')


def admit_input(runtime):
    """Pressure stops new upstream acquisition, without waiving/draining debt."""
    from .contracts import Backpressure
    _, selection = runtime.processing.current()
    policy = selection.get('service', {}).get('admission')
    if not policy:
        return windows.preflight_input(runtime)  # Optional admission remains a separate finite policy.
    usage = runtime.usage()
    debt = runtime.one('SELECT COUNT(*) AS n FROM alert_debt WHERE represented=0')['n']
    if (runtime.clock() >= policy['until'] or usage['bytes'] >= policy['pause_bytes']
            or usage['alerts'] >= runtime.config['limits']['max_alerts']
            or debt >= runtime.config['limits'].get('max_alert_debt', runtime.config['limits']['max_alerts'])):
        raise Backpressure('selected admission time/bytes/alerts/debt pressure; upstream remains unACKed, old duties retained')
    count = runtime.one("SELECT COUNT(*) AS n FROM processing_source_positions WHERE position>?",
                        (selection['basis']['event_boundary'],))['n']
    if count >= policy['max_new_inputs']:
        raise Backpressure('selected new input window full; preserve original history and continue owned work')
    return windows.preflight_input(runtime)


def ingest_report(runtime, actor, task, receipt):
    """Work's actual collected report is input, never another owner's execution.

    Whole inline reports/history preserve attribution. This operation makes no
    claim that native receipt fields were independently observed by the service.
    """
    cap, selection = runtime.processing.current()
    if actor != cap['issuer'] or task not in selection.get('service', {}).get('report_tasks', []):
        raise Refusal('actual Work collector and explicitly selected Reviews report route required')
    fields = {'reference', 'collector', 'actual_END', 'reports', 'history', 'method_pin', 'coverage', 'effects'}
    if (not isinstance(receipt, dict) or set(receipt) != fields or receipt['collector'] != actor
            or type(receipt['actual_END']) is not int or receipt['effects'] != 'known-report-only'
            or not isinstance(receipt['reports'], list) or not receipt['reports'] or len(receipt['reports']) > 32
            or not isinstance(receipt['coverage'], dict)):
        raise Refusal('whole attributed original reports/history/coverage and actual owned END required')
    for key in ('reference', 'history', 'method_pin'):
        required_text(receipt[key], 'actual original report ' + key, 262144)
    for report in receipt['reports']:
        if not isinstance(report, dict) or set(report) != {'name', 'body'}:
            raise Refusal('complete named report bodies required; no pointer-only full-read claim')
        required_text(report['name'], 'report name', 256)
        required_text(report['body'], 'whole report body', 262144)
    body = {'kind': 'attributed-report', 'original': receipt, 'native_owner_execution': False,
            'meaning': 'Work testimony and whole report input; not persistent Reviews owner collection or native liveness'}
    event = {'id': digest({'attributed_report': {'collector': actor, 'reference': receipt['reference']}}),
             'role': 'Reviews', 'recipient': runtime.config['roles']['Reviews']['owner'],
             'kind': 'response', 'author': actor, 'allowed_tasks': [task], 'package': None,
             'processing_report': cap['id'], 'body': body}
    if len(encode(event).encode()) > min(262144, runtime.config['limits']['max_result_bytes']):
        raise Refusal('whole report exceeds selected intake envelope; no truncation or full-report claim')
    from .report_scope import fits_return
    if not fits_return(runtime, [dict(event=event['id'], sha256=digest(event), original=body)]):
        raise Refusal('whole report has no complete return within selected result budget; no truncation')
    runtime.processing.boards['Reviews'].verify_authority(runtime)
    runtime.ingest(event)
    with runtime.tx():
        if runtime.event(event['id']) != event:
            raise Refusal('original public report event differs')
        prior = runtime.one('SELECT * FROM processing_report_inputs WHERE event=?', (event['id'],))
        frozen = dict(event=event['id'], capability=cap['id'], source_hash=digest(event), receipt_hash=digest(receipt))
        if prior and prior != frozen:
            raise Refusal('original collected report changed; no replacement')
        runtime.db.execute('INSERT OR IGNORE INTO processing_report_inputs VALUES(?,?,?,?)', tuple(frozen.values()))
    return {'event': event['id'], 'report_hash': digest(receipt), 'native_owner_execution': False,
            'acceptance': None, 'meaning': 'durable attributed input; fresh classification, sole integration and Work consumption still owed'}


class Dispatcher(ProcessingDispatcher):
    def __init__(self, runtime, boards, models=None, review_transport=None):
        super().__init__(runtime, models=models, boards=boards)
        self.reviews = reviews.Executor(runtime, review_transport)
        self.wake = None

    def intake(self):
        if self.wake is not None:
            self.wake.check()
        super().intake()

    def schedule_job(self):
        candidates = self.store.rows("SELECT * FROM jobs WHERE controller=? AND state='reserved' AND active_attempt IS NULL ORDER BY created,id",
                                     (self.store.controller,))
        # Reserve independent eligible work even while an earlier Source waits
        # for its own context. Frozen reservations/capacity are never released.
        fresh = self.store.reserve()
        if fresh:
            candidates.append(fresh)
        for job in candidates:
            if self.schedule_candidate(job):
                return

    def schedule_candidate(self,job):
        if not job:
            return
        if not self.store.processing.review_task(job['task']):
            super().schedule_job(job)
            return True
        try:
            self.boards[job['role']].verify_authority(self.store)
        except Refusal as exc:
            self.store.hold_job(job['id'],'pre-launch Source authority refused: '+str(exc))
            return False
        members = json.loads(job['members'])
        if len(members) != 1:
            raise Refusal('one continuing Source input per component, never a batch of artifacts')
        source = self.store.event(members[0]['event'])
        if digest(source) != members[0]['hash']:
            raise Refusal('frozen Source input changed')
        packet = source.get('body', {}).get('review') if isinstance(source.get('body'), dict) else None
        if not isinstance(packet, dict):
            self.store.hold_job(job['id'], 'ordinary Source needs an exact goal-blind review packet')
            return
        from .branches import review_key
        component = review_key(self.store,job,packet)
        context = self.store.one('SELECT * FROM review_contexts WHERE component=?', (component,))
        if component in self.reviews.busy:
            return False
        if context and (context['state']!='live' or context['collector']!=self.store.controller or context['capability']!=self.store.processing.key):
            self.store.hold_job(job['id'],'original review context unavailable; explicit informed recovery required')
            return False
        try:
            attempt = self.store.start_job(job['id'], job['token'])
        except Refusal as exc:
            self.store.record_operational_error(job['id'],{'error':str(exc)},job['role'],'source-admission-held')
            return False
        self.spawn(self.execute_review(job, attempt, packet))
        return True

    async def execute_review(self, job, attempt, packet):
        try:
            # schedule_candidate passed the pre-start reservation. Bind the
            # actual current attempt/epoch, as the ordinary task entry does.
            job = self.store.job(job['id'])
            admission = self.store.one('SELECT * FROM admissions WHERE package=?', (job['package'],))
            self.boards[job['role']].bind_software_attempt(self.store, job, attempt, admission)
            # Acquisition is an exercise of the bound task, before any model
            # input. Recheck the exact current proof at this boundary too.
            self.store.authorize_launch(attempt)
            from .local_integration import prepare_input_basis
            from .contracts import scoped_task
            task = scoped_task(job['task'], self.store.config['tasks'][job['task']],
                               admission)
            prepare_input_basis(self.store, job, attempt, task)
            policy = self.store.processing.current()[1]['service']['reviews'][job['task']]
            outcome = await self.reviews.execute(job, attempt, policy, packet)
        except Exception as exc:
            call = self.store.one('SELECT * FROM review_calls WHERE attempt=?', (attempt,))
            turns = json.loads(call['receipt'] or '[]') if call else []
            actual = [t['actual_END'] for t in turns if 'actual_END' in t]
            # Only this original call's actually waited exits may be relayed.
            outcome = {'exit': actual[-1] if actual else None, 'capture': 'incomplete',
                       'cleanup': 'continuing-context-held', 'result': None, 'error': str(exc),
                       'detail': {'original_review_calls': turns, 'original_collector': self.store.controller,
                                  'known_not_started':self.store.attempt(attempt)['begin'] is None and
                                      (not call or call['state']=='prepared')}}
            if outcome['detail']['known_not_started']:
                outcome['cleanup']='no-session-created'
        self.store.collect(attempt, outcome)
        # Exact owned producer files are inventoried, never a platform store.
        # Consumer conservation remains a separate real receipt before removal.
        from .cleanup import register_artifact
        directory = self.store.home / 'artifacts' / attempt
        if directory.exists():
            try:
                files = []
                for path in directory.rglob('*'):
                    if path.is_symlink():
                        raise Refusal('owned review output contains an unqualified alias; preserve it without following')
                    if path.is_file():
                        files.append(path)
                if len(files) > self.config['limits'].get('max_files', 50000):
                    raise Refusal('owned review artifact inventory exceeds cumulative entry budget')
                for path in files:
                    register_artifact(self.store, attempt, path)
            except (Refusal, OSError) as exc:
                self.store.capture_gap(attempt, exc)
                outcome['error'] = str(exc)
        with self.store.tx():
            self.store.db.execute("UPDATE jobs SET effects='none' WHERE id=?", (job['id'],))
            from .branches import settle_attempt
            settle_attempt(self.store,attempt)
        # Even a malformed/partial Source return goes whole to the sole report
        # integrator. This informative return cannot complete the Source job.
        if outcome['error'] or not outcome['result'] or outcome['result']['semantic'] != 'DONE':
            # Custody/status survives loss of permission to create a new input.
            # The original attempt/result and review call already retain the
            # whole return; a refused integration must not leave this job running.
            pending = ('original Source incomplete; whole return retained in original attempt '
                       + attempt + ' and review call; sole report integration deferred')
            self.store.hold_job(job['id'], pending)
            try:
                self.review_failure_return(job, attempt, outcome)
            except Refusal as exc:
                self.store.hold_job(job['id'], pending + ': ' + str(exc))
                return
            self.store.hold_job(job['id'], 'original Source incomplete; whole return conserved through sole report integration')
            return
        self.try_finish(job['id'])

    def schedule_recovery(self):
        # Existing recovery can search only a known, collected current original
        # with its actual effects/remaining-work fences. Reviews never gets a
        # fresh replacement context through that generic path.
        for job in self.store.rows("SELECT j.* FROM jobs j JOIN attempts a ON a.id=j.active_attempt WHERE j.controller=? AND j.state='held' AND a.collected IS NOT NULL AND j.recovery_count=0", (self.store.controller,)):
            if self.store.processing.review_task(job['task']):
                continue
            claimed = self.store.claim_recovery(job['id'])
            if claimed:
                self.spawn(self.recover(claimed))

    def review_failure_return(self, job, attempt, outcome):
        # A new integration event still exercises current authority, even when
        # the original collector may lawfully retain its failed/partial return.
        self.boards[job['role']].verify_authority(self.store)
        task = self.config['tasks'][job['task']]
        from .contracts import response_tasks
        routes = response_tasks(task, {'category': 'proposal'}, self.config)
        key = digest({'incomplete_ordinary_review': attempt})
        source = json.loads(job['members'])[0]['event']
        call = self.store.one('SELECT * FROM review_calls WHERE attempt=?', (attempt,))
        event = {'id': key, 'role': 'Reviews', 'recipient': self.store.enrollment('Reviews')['owner'],
                 'author': self.store.attempt(attempt)['session'], 'kind': 'response', 'parent': source,
                 'package': job['package'], 'allowed_tasks': routes, 'notice': None, 'board_id': None, 'grant': None,
                 'source_job': job['id'], 'source_attempt': attempt,
                 'source_role': job['role'], 'source_members': json.loads(job['members']),
                 'body': {'status': 'PARTIAL', 'full_original_call': call, 'full_original_outcome': outcome,
                          'meaning': 'Source incomplete; sole integrator must preserve all reports, dissent and gaps'}}
        from .branches import job_branch_key
        branch=job_branch_key(self.store, job)
        if branch:
            event['branch_binding']=branch
        with self.store.tx():
            if (self.store.processing.current()[1].get('service', {}).get('report_tasks') == routes
                    and outcome.get('result') and outcome['result'].get('semantic') == 'PARTIAL'
                    and outcome.get('exit') == 0 and outcome.get('capture') == 'complete' and not outcome.get('error')):
                from .review_returns import record
                record(self.store, event, self.store.job(job['id']), self.store.attempt(attempt), outcome)
            if not self.store.one('SELECT id FROM events WHERE id=?', (key,)):
                self.store.budget('events', len(encode(event).encode()))
                self.store.db.execute('INSERT INTO events(id,role,payload,hash,received,parent) VALUES(?,?,?,?,?,?)',
                                      (key, 'Reviews', encode(event), digest(event), self.store.clock(), source))
                from .processing import note_source
                note_source(self.store, key)

    def automatic_cleanup(self):
        # Qualified artifact/event relocation only. Destructive row retirement
        # separately requires current whole-chain custodian receipts.
        from .cleanup import sweep
        if self.store.clock() - self.last_cleanup >= 60:
            sweep(self.store)
            self.last_cleanup = self.store.clock()

    def reconcile_completed(self):
        self.reconcile_classifications()
        for job in self.store.rows('SELECT * FROM jobs WHERE controller=? AND active_attempt IS NOT NULL', (self.store.controller,)):
            attempt = self.store.one('SELECT collected,error,capture,semantic FROM attempts WHERE id=?', (job['active_attempt'],))
            if attempt['collected'] is None:
                continue
            if self.store.processing.review_task(job['task']) and (attempt['error'] or attempt['capture'] != 'complete' or attempt['semantic'] != 'DONE'):
                continue  # Its full incomplete return belongs to sole integration.
            self.reconcile_collected(job)
        self.store.complete_events()
        # Exact original return application is idempotent. No model replay,
        # native owner takeover or automatic effect reconciliation is involved.
        for control in self.store.rows('SELECT c.* FROM processing_controls c JOIN attempts a ON a.id=c.attempt WHERE c.resolution IS NULL AND a.collected IS NOT NULL AND a.controller=?', (self.store.controller,)):
            try:
                apply_control(self.store, control['event'], control['attempt'])
            except (Refusal, ValueError, TypeError):
                pass  # Its actual error/return remains in the original record.

    def recover_originals(self):
        self.reconcile_completed()
        self.reconcile_recovery_requests()  # Only already selected owner requests.
        return {'collector': self.store.controller, 'uncollected': self.store.rows(
            'SELECT id,controller,state FROM attempts WHERE collected IS NULL'),
            'meaning': 'original collected-return reconciliation; no relaunch, acceptance or unknown-effect waiver'}


def endpoint(runtime, key):
    # Linux abstract sockets keep long existing journal paths usable without
    # relocating the journal or borrowing /tmp. Peer credentials are checked.
    return '\0coordinator-' + digest({'runtime': str(runtime.path), 'capability': key})


async def serve(runtime, boards, key, emit, models=None, review_transport=None):
    with observations.owning("service"):
        return await serve_owned(runtime, boards, key, emit, models, review_transport)


async def serve_owned(runtime, boards, key, emit, models=None, review_transport=None):
    runtime.processing = Access(runtime, key, boards)
    with observations.span("service-current"):
        _, selection = runtime.processing.current()
    if 'service' not in selection:
        raise Refusal('finite processing capability cannot be extended into a service')
    with observations.span("service-boards"):
        for board in boards.values():
            board.runtime = runtime
            board.verify_authority(runtime)
    path = endpoint(runtime, key)
    lock = os.open(runtime.home / 'service.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with runtime.tx():
            if owned_service_conflict(runtime):
                raise Refusal('previous original process still owns recovery; collect its actual END first')
            runtime.budget(None, 4096)
            runtime.db.execute('INSERT INTO processing_runs VALUES(?,?,?,?)', (runtime.controller, key, 'owned', runtime.clock()))
            runtime.db.execute('INSERT INTO service_runs VALUES(?,?,?,?,?,NULL,NULL)',
                               (runtime.controller, key, str(path), 'serving', runtime.clock()))
        dispatcher = Dispatcher(runtime, boards, models, review_transport)
        async def connection(reader, writer):
            authorized = False
            try:
                peer = writer.get_extra_info('socket')
                _, uid, _ = struct.unpack('3i', peer.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
                if uid != os.getuid():
                    raise Refusal('different requester cannot address the original collector')
                with observations.span("control-read"):
                    line = await asyncio.wait_for(reader.readline(), 10)
                if len(line) > 65536:
                    raise Refusal('bounded service control required')
                request = json.loads(line)
                if request.get('capability') != key or set(request) - {'capability', 'operation', 'component'}:
                    raise Refusal('exact current service control required')
                authorized = True
                operation = request.get('operation')
                if operation == 'status':
                    with observations.span('control-status'):
                        answer = status(runtime, key, dispatcher)
                elif operation == 'recover':
                    with observations.span("control-recover"):
                        answer = dispatcher.recover_originals()
                elif operation == 'stop':
                    with observations.span("control-stop"):
                        dispatcher.stopping.set()
                    answer = {'controller': runtime.controller, 'state': 'draining; parent still owes this original numeric END'}
                elif operation == 'close-review':
                    component = request.get('component')
                    with observations.span("control-close-review"):
                        policy = reviews.context_policy(runtime,component,selection['service']['reviews'])
                        answer = await dispatcher.reviews.close(component, policy)
                else:
                    raise Refusal('unsupported control; no replay or authority mutation endpoint')
            except Exception as exc:
                answer = {'error': str(exc), 'processing_complete': False}
            if authorized:
                answer.setdefault('controller', runtime.controller)
                answer['service_observations'] = observations.snapshot()
            with observations.span('control-write'):
                writer.write((encode(answer) + '\n').encode())
                await writer.drain()
            writer.close()
            await writer.wait_closed()
        server = await asyncio.start_unix_server(connection, path=path, limit=65537)
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, dispatcher.stopping.set)
        try:
            from .service_wake import ServiceWake
            dispatcher.wake = ServiceWake(runtime, boards, dispatcher)
            dispatcher.wake.start()
            emit({'controller': runtime.controller, 'capability': key, 'endpoint': 'abstract:' + path[1:],
                  'state': 'serving', 'process_END': None, 'wake': dispatcher.wake.status()})
            await dispatcher.run(emit)
        finally:
            if dispatcher.wake is not None:
                dispatcher.wake.close()
            server.close()
            await server.wait_closed()
            # Live contexts remain owned and explicitly reported if close fails.
            for context in runtime.rows("SELECT component FROM review_contexts WHERE collector=? AND state!='closed'", (runtime.controller,)):
                try:
                    policy=reviews.context_policy(runtime,context['component'],selection['service']['reviews'])
                    await dispatcher.reviews.close(context['component'], policy)
                except Exception as exc:
                    runtime.record_operational_error(context['component'], {'error': str(exc)}, 'Reviews', 'original-context-close')
            receipt = dispatcher.recover_originals()
            with runtime.tx():
                runtime.db.execute("UPDATE service_runs SET state='returned-awaiting-parent-END',returned=?,receipt=? WHERE controller=?",
                                   (runtime.clock(), encode(receipt), runtime.controller))
            receipt["service_observations"] = observations.snapshot()
            emit(receipt)
            # Kernel endpoint lifetime follows this actual original socket;
            # the parent-END barrier remains in the original journal.
    finally:
        os.close(lock)


def stop_authority(runtime, key, actor):
    """Authenticate withdrawal of this original, never authority to do work.

    Release/implementation pins deliberately do not participate: a required
    dependency change must not strand its owner. Configuration, issuer,
    revocation and original-run bindings still apply. No journal write occurs.
    The CLI authenticates the actor through the existing Work session checker.
    """
    assert_current(runtime)
    cap = runtime.one('SELECT * FROM processing_capabilities WHERE id=?', (key,))
    if not cap or cap['revoked'] is not None or actor != cap['issuer'] or actor != runtime.config['software_delegation']['grantor']:
        raise Refusal('stop requires the authenticated current Work issuer and unrevoked exact capability')
    selection = json.loads(cap['selection'])
    if not isinstance(selection.get('service'), dict) or selection['basis']['configuration'] != digest(runtime.config):
        raise Refusal('stop requires the selected continuing capability and unchanged journal configuration')
    runs = runtime.rows("SELECT s.controller FROM service_runs s JOIN processing_runs p ON p.controller=s.controller "
                        "AND p.capability=s.capability WHERE s.capability=? AND s.state='serving' "
                        "AND s.returned IS NULL AND p.state='owned' LIMIT 2", (key,))
    if len(runs) != 1:
        raise Refusal('stop requires one recorded original owning service; no replacement or inferred END')
    return runs[0]['controller']


async def control(runtime, key, operation, component=None, *, stop_owner=None):
    controller = None
    if stop_owner is not None:
        if operation != 'stop' or component is not None:
            raise Refusal('owner withdrawal permits only stop without a component')
        controller = stop_authority(runtime, key, stop_owner)
    with observations.span('control-connect'):
        reader, writer = await asyncio.open_unix_connection(endpoint(runtime, key), limit=runtime.config['limits']['max_bytes'])
    try:
        if controller is not None:
            peer = writer.get_extra_info('socket')
            _, uid, _ = struct.unpack('3i', peer.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
            if uid != os.getuid() or stop_authority(runtime, key, stop_owner) != controller:
                raise Refusal('original endpoint peer or current owner binding changed before stop')
        with observations.span('control-send'):
            writer.write((encode({'capability': key, 'operation': operation, **({'component': component} if component else {})}) + '\n').encode())
            await writer.drain()
        with observations.span('control-reply'):
            answer = await reader.readline()  # Actual original notification, no polling.
            value = json.loads(answer)
            if controller is not None:
                if (not isinstance(value, dict) or value.get('error') or value.get('controller') != controller
                        or value.get('state') != 'draining; parent still owes this original numeric END'):
                    raise Refusal('original stop acknowledgement absent/mismatched; effects and actual END remain unknown')
                value.update(process_END=None, processing_complete=False,
                             release_currentness='not established; authenticated stop-only owner control')
            return value
    finally:
        with observations.span('control-close'):
            writer.close()
            await writer.wait_closed()


def status(runtime, key, dispatcher):
    """Current owning process only; no historical errors or native handles."""
    Access(runtime, key).current()
    run = runtime.one('SELECT controller,capability,state,started,returned FROM service_runs '
                      'WHERE controller=? AND capability=?', (runtime.controller, key))
    if dispatcher.store is not runtime or not run or run['state'] != 'serving' or run['returned'] is not None:
        raise Refusal('current original serving controller required for phase diagnostics')
    contexts = runtime.rows('SELECT component,collector,state FROM review_contexts '
                            'WHERE capability=? AND collector=? ORDER BY component LIMIT 65', (key, runtime.controller))
    attempts = runtime.rows('SELECT id,controller,kind,state FROM attempts WHERE controller=? '
                            'AND collected IS NULL ORDER BY id LIMIT 65', (runtime.controller,))
    Access(runtime, key).current()
    return {'capability': key, 'controller': runtime.controller, 'runs': [run],
            'contexts': contexts[:64], 'uncollected': attempts[:64],
            'contexts_more': len(contexts) > 64, 'uncollected_more': len(attempts) > 64,
            'phase_errors': dict(dispatcher.phase_errors),
            'wake': dispatcher.wake.status() if dispatcher.wake is not None else {'state': 'disabled'},
            'phase_error_scope': 'current owning process; failures until that phase succeeds; no historical import',
            'processing_complete': False,
            'meaning': 'bounded current custody/phase facts; empty errors are not processing, acceptance or a liveness inference'}
