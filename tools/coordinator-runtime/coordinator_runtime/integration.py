"""Closed execution fences, distinct from enduring Work integration duties.

Receipts are attributed evidence, not a process census or effect reconciliation.
Only the actual owner may select them through the authority-checked CLI. No
retirement completes a job, processes an input, transfers custody or replays work.
"""
import json
from contextlib import nullcontext

from .contracts import Refusal, digest, encode, required_text
from .integration_evidence import attempt_view, fence_view, shared_debt_view

SCHEMA = """
CREATE TABLE IF NOT EXISTS integration_retirements(
 job TEXT PRIMARY KEY,attempt TEXT NOT NULL,actor TEXT NOT NULL,
 basis TEXT NOT NULL,receipt TEXT NOT NULL,created REAL NOT NULL);
CREATE TABLE IF NOT EXISTS integration_windows(
 id TEXT PRIMARY KEY,actor TEXT NOT NULL,basis TEXT NOT NULL,
 receipt TEXT NOT NULL,created REAL NOT NULL,job TEXT UNIQUE);
CREATE TABLE IF NOT EXISTS integration_prestart_dispositions(
 job TEXT PRIMARY KEY,actor TEXT NOT NULL,basis TEXT NOT NULL,
 receipt TEXT NOT NULL,created REAL NOT NULL);
CREATE TABLE IF NOT EXISTS integration_management_operations(
 id TEXT PRIMARY KEY,actor TEXT NOT NULL,selection TEXT NOT NULL,
 outcome TEXT NOT NULL,created REAL NOT NULL);
CREATE TABLE IF NOT EXISTS work_read_fences(
 job TEXT PRIMARY KEY,actor TEXT NOT NULL,basis TEXT NOT NULL,
 receipt TEXT NOT NULL,created REAL NOT NULL);
"""


class IntegrationJournal:
    def integration_retired(self, job):
        # Both are permanent execution fences. A prestart withdrawal asserts no
        # attempt launch (or no allocation), never a fabricated END or processing.
        return (self.one('SELECT * FROM integration_retirements WHERE job=?', (job,))
                or self.one('SELECT * FROM integration_prestart_dispositions WHERE job=?', (job,)))

    def require_execution_open(self, job):
        if self.integration_retired(job) or self.one('SELECT job FROM work_read_fences WHERE job=?', (job,)):
            raise Refusal('execution retired; original duties remain held, no callback/recovery/replay')

    def work_read_closure_basis(self, job, token):
        """Exact terminal proposer metadata, without interpreting its return.

        Closure facts about controllers and writers must come from their actual
        custodians. This basis supplies none of those external facts.
        """
        self.job(job, token)
        management = getattr(self, 'integration_management', None)
        if management:
            for role in self.source_roles(job=job):
                management.enrollment(role)
        else:
            self.require_active_sources(job=job)
        return self._work_read_basis(job)

    def _work_read_basis(self, job):
        row = self.job(job)
        if (row['role'] != 'Work' or row['phase'] != 'proposer' or row['state'] != 'held'
                or row['effects'] != 'none'
                or self.one('SELECT job FROM local_jobs WHERE job=?', (job,))):
            raise Refusal('exact held nonwriting Work proposer with unknown local scope required')
        if (row['recovery_state'] in {'claimed', 'diagnosing'}
                or row['recovery_owner'] is not None
                and row['recovery_state'] not in {'awaiting-disposition', 'owner-deferred'}):
            raise Refusal('retained recovery owner must have no active recovery execution')
        if self.one('SELECT p.attempt FROM file_publications p JOIN attempts a ON a.id=p.attempt WHERE a.job=? LIMIT 1', (job,)):
            raise Refusal('publication duties cannot be treated as a nonwriting predecessor')
        frozen = self.one('SELECT task FROM job_resource_policies WHERE job=?', (job,))
        task = json.loads(frozen['task']) if frozen else None
        if not self._work_read_task(task):
            raise Refusal('original frozen read-only nonwriting Work proposer policy required')
        attempts = self.rows('SELECT id,kind,job,controller,begin,ended,collected,exit,state,capture,semantic,error '
                             'FROM attempts WHERE job=? ORDER BY rowid', (job,))
        if (not attempts or not any(a['id'] == row['active_attempt'] and a['kind'] == 'task' for a in attempts)
                or any(a['state'] != 'collected' or a['begin'] is None or a['ended'] is None
                       or a['collected'] is None or type(a['exit']) is not int for a in attempts)):
            raise Refusal('all related originals need actual begun numeric END and collection')
        if self.one("SELECT id FROM recovery_requests WHERE job=? AND state='pending'", (job,)):
            raise Refusal('pending owner recovery must be disposed before a read fence')
        controllers = {row['controller'], *[a['controller'] for a in attempts]}
        if row['recovery_owner'] is not None:
            controllers.add(row['recovery_owner'])
        return self._integration_bounded({'job': row, 'policy': digest(task), 'attempts': attempts,
            'controllers': sorted(controllers)})

    @staticmethod
    def _work_read_task(task):
        return bool(isinstance(task, dict) and task.get('role') == 'Work' and task.get('phase') == 'proposer'
                    and task.get('sandbox') == 'read-only' and task.get('effects') == 'none'
                    and task.get('network', False) is False and task.get('execution') is None
                    and not task.get('routine_completion')
                    and isinstance(task.get('effect_authority'), dict)
                    and task['effect_authority'].get('write_roots') == [])

    def fence_work_proposer(self, job, token, actor, receipt):
        """Prevent old execution; permit guarded scoped file coexistence.

        Unlike integration retirement, this does not release capacity or assert
        execution_complete. PARTIAL, capture defects, source and delivery duties
        remain exactly where they were. Evidence is attributed, not a census.
        """
        with self._integration_transaction():
            self._integration_owner(actor)
            self.require_execution_open(job)
            basis = self.work_read_closure_basis(job, token)
            self._integration_controller_closures(basis, receipt)
            self._integration_bounded(receipt)
            self.budget(None, len(encode(basis).encode()) + len(encode(receipt).encode()))
            self.db.execute('INSERT INTO work_read_fences VALUES(?,?,?,?,?)',
                (job, actor, encode(basis), encode(receipt), self.clock()))
        return self.one('SELECT * FROM work_read_fences WHERE job=?', (job,))

    def work_read_coexists(self, row, scope, source):
        """Scoped file work may coexist with a closed nonwriting predecessor.

        The predecessor's unknown *read* scope cannot conflict with a future
        write once every execution-capable controller is closed and fenced.
        This says nothing about acceptance of its retained adverse result.
        Incoming writers still need ordinary local/routine publication rights.
        """
        task = self.config['tasks'][row['task']]
        reader = (row['phase'] == 'proposer' and scope['reads'] and not scope['writes']
                  and self._work_read_task(task))
        integrator = (row['phase'] == 'integrator' and task.get('role') == 'Work'
                      and task.get('phase') == 'integrator' and task.get('execution') is None
                      and task.get('network', False) is False and task.get('routine_completion')
                      and task.get('effects') == 'owner-reconcile'
                      and task.get('sandbox') == 'workspace-write')
        if (row['role'] != 'Work' or scope['lane'] != 'anchored'
                or not (scope['reads'] or scope['writes']) or not (reader or integrator)):
            return False
        from .local_integration import point_definitions
        points = point_definitions(self)
        if any('native' in binding for key in set(scope['reads']) | set(scope['writes'])
               for binding in points[key]['bindings']):
            return False  # Native coordination retains its original exclusion contract.
        fence = self.one('SELECT basis FROM work_read_fences WHERE job=?', (source['id'],))
        if not fence:
            return False
        return json.loads(fence['basis']) == self._work_read_basis(source['id'])

    def _integration_controller_closures(self, basis, receipt):
        if not isinstance(receipt, dict) or set(receipt) != {'basis', 'controllers', 'reason'}:
            raise Refusal('exact closure basis, controller closures and reason required')
        if receipt['basis'] != basis:
            raise Refusal('closure basis changed; no stale fence')
        required_text(receipt['reason'], 'execution fence reason', 4000)
        closures = receipt['controllers']
        if not isinstance(closures, list) or len(closures) != len(basis['controllers']):
            raise Refusal('every original controller must be genuinely closed')
        found = []
        for item in closures:
            if not isinstance(item, dict) or set(item) != {'controller', 'collector', 'end', 'collected', 'writers_closed', 'evidence'}:
                raise Refusal('exact controller/collector/END and writer closure evidence required')
            required_text(item['collector'], 'actual controller collector', 128)
            if type(item['end']) is not int or item['collected'] is not True or item['writers_closed'] is not True:
                raise Refusal('controller END alone cannot establish writer closure')
            self._integration_evidence(item['evidence'])
            found.append(item['controller'])
        if sorted(found) != basis['controllers']:
            raise Refusal('conflicting/missing controller closures')

    def _integration_owner(self, actor):
        if actor != self._integration_enrollment('Work')['owner']:
            raise Refusal('actual current Work owner required')

    def _integration_enrollment(self, role):
        management = getattr(self, 'integration_management', None)
        return management.enrollment(role) if management else self.enrollment(role)

    def _integration_transaction(self):
        # Management validates exact access and records the selected purpose in
        # the same local write transaction as the existing fence/window checks.
        if getattr(self, 'integration_management', None) is not None and self.db.in_transaction:
            return nullcontext()
        return self.tx()

    def _integration_bounded(self, value):
        if len(encode(value).encode()) > self.config['limits']['max_result_bytes']:
            raise Refusal('integration evidence exceeds admitted bound; retain duties')
        return value

    def _integration_evidence(self, evidence):
        if not isinstance(evidence, list) or not 1 <= len(evidence) <= 16:
            raise Refusal('bounded applicable evidence required')
        for item in evidence:
            required_text(item, 'integration evidence', 2000)

    def integration_prestart_basis(self, job, token):
        self.require_execution_open(job)
        row = self.job(job, token)
        if (row['role'] != 'Work' or row['phase'] != 'integrator'
                or row['state'] not in {'reserved', 'held'} or row['active_attempt'] is not None
                or self.one('SELECT id FROM attempts WHERE job=?', (job,))
                or row['effects'] != 'unknown' or row['effect_receipt'] is not None
                or row['response'] is not None or row['closed_at'] is not None
                or row['recovery_owner'] is not None or row['recovery_state'] is not None
                or row['recovery_count'] != 0 or row['collection_handoff'] is not None
                or self.one('SELECT id FROM recovery_requests WHERE job=?', (job,))):
            raise Refusal('only never-allocated Work integration reservations may be withdrawn')
        return self._integration_reservation_basis(row)

    def _integration_reservation_basis(self, row):
        job = row['id']
        window = self.one('SELECT * FROM integration_windows WHERE job=?', (job,))
        if not window or json.loads(window['basis'])['members'] != json.loads(row['members']):
            raise Refusal('exact consumed integration window and frozen members required')
        queues = self.rows('SELECT * FROM queue WHERE job=? ORDER BY rowid', (job,))
        members = json.loads(row['members'])
        if (len(queues) != len(members) or {q['id'] for q in queues} != {m['queue'] for m in members}
                or any(q['state'] != 'reserved' or q['role'] != 'Work'
                       or q['phase'] != 'integrator' or q['task'] != row['task']
                       or not any(m['queue'] == q['id'] and m['event'] == q['event']
                                  and m['package'] == q['package'] for m in members) for q in queues)):
            raise Refusal('exact pending queue ownership required; no partial release')
        return self._integration_bounded({'job': row, 'window': window, 'queue': queues,
            'inputs': [self.one('SELECT * FROM events WHERE id=?', (m['event'],)) for m in members],
            'debt': self.integration_debt(), 'enrollment': self.enrollment('Work')})

    def withdraw_integration_prestart(self, job, token, actor, receipt):
        """Owner disposition, serialized against allocation; inputs remain pending.

        The consumed selection and frozen reservation remain immutable evidence.
        A new, exact owner selection must account for them before any new launch.
        Evidence is attributed caller testimony, not external process discovery.
        """
        with self.tx():
            self._integration_owner(actor)
            basis = self.integration_prestart_basis(job, token)
            if not isinstance(receipt, dict) or set(receipt) != {'basis', 'reason', 'no_launch_evidence'}:
                raise Refusal('exact prestart basis, reason and scoped no-launch evidence required')
            if receipt['basis'] != basis:
                raise Refusal('prestart disposition basis changed; fresh owner decision required')
            required_text(receipt['reason'], 'prestart withdrawal reason', 4000)
            self._integration_evidence(receipt['no_launch_evidence'])
            self._integration_bounded(receipt)
            self.budget(None, len(encode(basis).encode()) + len(encode(receipt).encode()))
            self.db.execute('INSERT INTO integration_prestart_dispositions VALUES(?,?,?,?,?)',
                (job, actor, encode(basis), encode(receipt), self.clock()))
            self.db.execute("UPDATE jobs SET state='held',hold_reason=? WHERE id=?",
                ('owner withdrew never-allocated execution; pending duties conserved', job))
            self.db.execute("UPDATE queue SET state='queued',job=NULL WHERE job=?", (job,))
        return self.integration_retired(job)

    def integration_no_start_basis(self, job, token):
        """Collected task no-start with closed diagnoses; absence of begin is insufficient.

        A caller must additionally close every controller capable of launching.
        No stale window refresh, fabricated END or effect reconciliation occurs.
        """
        self.require_execution_open(job)
        row = self.job(job, token)
        if (row['role'] != 'Work' or row['phase'] != 'integrator'
                or row['state'] not in {'running', 'held'} or not row['active_attempt']
                or row['response'] is not None or row['closed_at'] is not None):
            raise Refusal('exact allocated open Work integrator required')
        attempts = self.rows('SELECT * FROM attempts WHERE job=? ORDER BY rowid', (job,))
        if (not attempts or not any(a['id'] == row['active_attempt'] and a['kind'] == 'task' for a in attempts)
                or any(not self._integration_no_start_attempt(a) for a in attempts)):
            raise Refusal('all tasks require collected no-start and diagnoses require real closure; missing begin/END is not proof')
        if self.one("SELECT id FROM recovery_requests WHERE job=? AND state='pending'", (job,)):
            raise Refusal('pending owner recovery selection must retain its disposition')
        basis = self._integration_reservation_basis(row)
        basis.update({'attempts': attempts,
            'source_custody': [self.one('SELECT * FROM source_custody WHERE event=?', (m['event'],))
                for m in json.loads(row['members'])],
            'input_resolutions': [self.rows('SELECT * FROM input_resolutions WHERE event=? ORDER BY version', (m['event'],))
                for m in json.loads(row['members'])],
            'results': self.rows('SELECT * FROM results WHERE job=? ORDER BY rowid', (job,)),
            'controllers': sorted({row['controller'], *[a['controller'] for a in attempts]}
                | ({row['recovery_owner']} if row['recovery_owner'] else set())),
            'outboxes': self.rows('SELECT * FROM outboxes WHERE job=? ORDER BY rowid', (job,)),
            'publication': self.rows('SELECT p.* FROM file_publications p JOIN attempts a ON a.id=p.attempt WHERE a.job=? ORDER BY p.rowid', (job,)),
            'custody': self.rows('SELECT c.* FROM artifact_custody c JOIN attempts a ON a.id=c.attempt WHERE a.job=? ORDER BY c.rowid', (job,)),
            'recovery_requests': self.rows('SELECT * FROM recovery_requests WHERE job=? ORDER BY rowid', (job,)),
            'recovery_dispositions': self.rows('SELECT * FROM recovery_dispositions WHERE job=? ORDER BY rowid', (job,))})
        return self._integration_bounded(basis)

    def _integration_no_start_attempt(self, attempt):
        if attempt['kind'] not in {'task', 'diagnosis'} or attempt['collected'] is None:
            return False
        if attempt['kind'] == 'diagnosis' and attempt['state'] == 'collected':
            # Read-only recovery can have really run; retain its genuine numeric
            # closure rather than inventing an END for the unlaunched tasks.
            return (attempt['begin'] is not None and attempt['ended'] is not None
                    and type(attempt['exit']) is int)
        return (attempt['state'] == 'not-started'
                and all(attempt[k] is None for k in ('begin', 'ended', 'exit', 'session', 'turn', 'semantic', 'result'))
                and json.loads(attempt['detail']).get('known_not_started') is True
                and bool(json.loads(attempt['detail']).get('resume_disposition')))

    def withdraw_integration_no_start(self, job, token, actor, receipt):
        """Permanent launch fence and pending-input return; all duties survive.

        Controller closure/task-no-launch testimony is an accountable external premise,
        not authenticated by SQLite. The authority-checked CLI supplies the owner.
        Cooperating begin/allocation and this disposition serialize in one tx.
        """
        with self.tx():
            self._integration_owner(actor)
            basis = self.integration_no_start_basis(job, token)
            if not isinstance(receipt, dict) or set(receipt) != {'basis', 'reason', 'controllers'}:
                raise Refusal('exact no-start basis, reason and controller closures required')
            if receipt['basis'] != basis:
                raise Refusal('no-start disposition basis changed; fresh owner decision required')
            required_text(receipt['reason'], 'allocated no-start withdrawal reason', 4000)
            closures = receipt['controllers']
            if not isinstance(closures, list) or len(closures) != len(basis['controllers']):
                raise Refusal('every launch-capable controller needs explicit no-start closure')
            found = []
            for item in closures:
                if not isinstance(item, dict) or set(item) != {'controller', 'collector', 'writers_closed', 'no_launch', 'evidence'}:
                    raise Refusal('exact scoped controller/collector no-launch closure required; no invented END')
                required_text(item['controller'], 'launch-capable controller', 128)
                required_text(item['collector'], 'actual controller collector', 128)
                if item['writers_closed'] is not True or item['no_launch'] is not True:
                    raise Refusal('missing begin or collection alone cannot close a launch-capable controller')
                self._integration_evidence(item['evidence'])
                found.append(item['controller'])
            if sorted(found) != basis['controllers']:
                raise Refusal('conflicting/missing controller closures')
            self._integration_bounded(receipt)
            self.budget(None, len(encode(basis).encode()) + len(encode(receipt).encode()))
            self.db.execute('INSERT INTO integration_prestart_dispositions VALUES(?,?,?,?,?)',
                (job, actor, encode(basis), encode(receipt), self.clock()))
            self.db.execute("UPDATE jobs SET state='held',hold_reason=COALESCE(hold_reason,?) WHERE id=?",
                ('owner withdrew qualified allocated no-start execution; all duties conserved', job))
            self.db.execute("UPDATE queue SET state='queued',job=NULL WHERE job=?", (job,))
        return self.integration_retired(job)

    def withdrawn_integration_hold(self, event):
        """Historical allocated duties remain tied to immutable input members."""
        return self.one("SELECT w.id FROM integration_prestart_dispositions d JOIN jobs w ON w.id=d.job,"
            "json_each(w.members) m WHERE json_extract(m.value,'$.event')=? AND "
            "(EXISTS (SELECT 1 FROM file_publications p JOIN attempts a ON a.id=p.attempt "
            "WHERE a.job=w.id AND p.state!='published') OR "
            "(EXISTS (SELECT 1 FROM attempts a WHERE a.job=w.id) AND "
            "(w.effects NOT IN ('none','reconciled') OR EXISTS (SELECT 1 FROM attempts a WHERE a.job=w.id "
            "AND a.cleanup NOT IN ('done','owned-ephemeral-lifecycle-observed','no-session-created')))))", (event,))

    def integration_context(self, job):
        """Authoritative selection for initial, diagnosed and recovered attempts."""
        window = self.one('SELECT receipt FROM integration_windows WHERE job=?', (job,))
        return json.loads(window['receipt']) if window else None

    def integration_closure_basis(self, job, token):
        row = self.job(job, token)
        if row['role'] != 'Work' or row['phase'] != 'integrator' or row['state'] != 'held':
            raise Refusal('exact held Work integrator required')
        management = getattr(self, 'integration_management', None)
        if management:
            for role in self.source_roles(job=job):
                management.enrollment(role)
        else:
            self.require_active_sources(job=job)
        attempts = self.rows('SELECT * FROM attempts WHERE job=? ORDER BY rowid', (job,))
        if not attempts or not row['active_attempt'] or not any(a['id'] == row['active_attempt'] for a in attempts):
            raise Refusal('exact original task and related closure required')
        if any(a['state'] != 'collected' or a['begin'] is None or a['ended'] is None
               or a['collected'] is None or type(a['exit']) is not int for a in attempts):
            raise Refusal('all related originals need actual numeric END and collection; no count inference')
        controllers = sorted({row['controller'], *[a['controller'] for a in attempts]}
                             | ({row['recovery_owner']} if row['recovery_owner'] else set()))
        return self._integration_bounded({'job': row, 'attempts': attempts,
            'results': self.rows('SELECT * FROM results WHERE job=? ORDER BY rowid', (job,)),
            'controllers': controllers})

    def retire_integration(self, job, token, actor, receipt):
        """One permanent execution fence; all historical rows stay unchanged."""
        with self._integration_transaction():
            self._integration_owner(actor)
            self.require_execution_open(job)
            basis = self.integration_closure_basis(job, token)
            if not isinstance(receipt, dict) or set(receipt) != {'basis', 'controllers', 'reason'}:
                raise Refusal('exact closure basis, controller closures and reason required')
            if receipt['basis'] != basis:
                raise Refusal('closure basis changed; no stale retirement')
            required_text(receipt['reason'], 'execution retirement reason', 4000)
            closures = receipt['controllers']
            if not isinstance(closures, list) or len(closures) != len(basis['controllers']):
                raise Refusal('every original controller must be genuinely closed')
            found = []
            for item in closures:
                if not isinstance(item, dict) or set(item) != {'controller', 'collector', 'end', 'collected', 'writers_closed', 'evidence'}:
                    raise Refusal('exact controller/collector/END and writer closure evidence required')
                required_text(item['collector'], 'actual controller collector', 128)
                if type(item['end']) is not int or item['collected'] is not True or item['writers_closed'] is not True:
                    raise Refusal('controller END alone cannot establish writer closure')
                self._integration_evidence(item['evidence'])
                found.append(item['controller'])
            if sorted(found) != basis['controllers']:
                raise Refusal('conflicting/missing controller closures')
            if self.one("SELECT id FROM recovery_requests WHERE job=? AND state='pending'", (job,)):
                raise Refusal('pending owner recovery selection must be disposed before retirement')
            self._integration_bounded(receipt)
            self.budget(None, len(encode(basis).encode()) + len(encode(receipt).encode()))
            self.db.execute('INSERT INTO integration_retirements VALUES(?,?,?,?,?,?)',
                (job, basis['job']['active_attempt'], actor, encode(basis), encode(receipt), self.clock()))
        return self.integration_retired(job)

    def integration_debt(self):
        """Current duties with verifiable, retained historical snapshot references.

        Full originals stay in their existing rows under existing authority.
        References bind even folded material, so byte or relationship changes
        still invalidate selection/reservation/launch. No new acquisition bound
        or availability guarantee follows from the smaller transported view.
        """
        result = []
        fences = [(r, 'retirement') for r in self.rows('SELECT * FROM integration_retirements ORDER BY rowid')]
        fences += [(r, 'prestart_disposition') for r in self.rows('SELECT * FROM integration_prestart_dispositions ORDER BY rowid')]
        for retired, kind in fences:
            job = retired['job']
            row = self.job(job)
            members = json.loads(row['members'])
            table = 'integration_retirements' if kind == 'retirement' else 'integration_prestart_dispositions'
            result.append(shared_debt_view({'representation': 'integration-debt-v1',
                kind: fence_view(retired, table), 'current_job': row,
                'attempts': [attempt_view(a) for a in self.rows('SELECT * FROM attempts WHERE job=? ORDER BY rowid', (job,))],
                'outboxes': self.rows('SELECT * FROM outboxes WHERE job=? ORDER BY rowid', (job,)),
                'inputs': [self.one('SELECT * FROM events WHERE id=?', (m['event'],)) for m in members],
                'source_custody': [self.one('SELECT * FROM source_custody WHERE event=?', (m['event'],)) for m in members],
                'recovery_requests': self.rows('SELECT * FROM recovery_requests WHERE job=? ORDER BY rowid', (job,)),
                'recovery_dispositions': self.rows('SELECT * FROM recovery_dispositions WHERE job=? ORDER BY rowid', (job,)),
                'queue': self.rows('SELECT * FROM queue WHERE job=? ORDER BY rowid', (job,)),
                'publication': self.rows('SELECT p.* FROM file_publications p JOIN attempts a ON a.id=p.attempt WHERE a.job=? ORDER BY p.rowid', (job,)),
                'custody': self.rows('SELECT c.* FROM artifact_custody c JOIN attempts a ON a.id=c.attempt WHERE a.job=? ORDER BY c.rowid', (job,))}))
        return self._integration_bounded(result)

    def integration_window_basis(self, task, events):
        selected = self.config['tasks'].get(task)
        if not selected or selected['role'] != 'Work' or selected['phase'] != 'integrator':
            raise Refusal('Work integration task required')
        if not isinstance(events, list) or not events or len(set(events)) != len(events):
            raise Refusal('nonempty distinct exact next-window input identities required')
        if self.config.get('window_service') and len(events) > self.config['window_service']['batch_size']:
            raise Refusal('selected integration batch exceeds current allocation-window batch size')
        members = []
        for event in events:
            row = self.one("SELECT q.* FROM queue q JOIN events e ON e.id=q.event WHERE q.event=? AND q.task=? AND q.state='queued' AND e.hold IS NULL", (event, task))
            if not row:
                raise Refusal('next input is not currently eligible; no old input replay')
            self._integration_member_eligible(row)
            members.append(self._input_member(row))
        return self._integration_bounded({'task': task, 'members': members,
            'debt': self.integration_debt(), 'enrollment': self._integration_enrollment('Work')})

    def _integration_member_eligible(self, row):
        # An owner-selected window narrows composition; it grants no exception
        # to ordinary processing task scope, admission or source ancestry.
        if self.processing and not self.processing.task(row):
            raise Refusal('selected integration member outside ordinary processing admission')

    def select_integration_window(self, actor, receipt):
        """Select one bounded future batch; unrelated UNKNOWN debt is conserved."""
        with self._integration_transaction():
            self._integration_owner(actor)
            if not isinstance(receipt, dict) or set(receipt) != {'basis', 'target', 'why', 'conflict_evidence', 'custodian_evidence'}:
                raise Refusal('exact basis, target/WHY and applicable peer/custodian evidence required')
            basis = receipt['basis']
            current = self.integration_window_basis(basis['task'], [m['event'] for m in basis['members']])
            if current != basis:
                raise Refusal('current source/debt/enrollment changed; fresh owner selection required')
            if not basis['debt']:
                raise Refusal('this window route is only for conserved closed-execution debt')
            for field in ('target', 'why'):
                required_text(receipt[field], field, 4000)
            for field in ('conflict_evidence', 'custodian_evidence'):
                self._integration_evidence(receipt[field])
            self._integration_bounded(receipt)
            # Lifetime bound; no automatic deletion, credit, replacement or replay.
            count = self.db.execute('SELECT COUNT(*) FROM integration_windows').fetchone()[0]
            if count >= self.config['limits']['max_jobs']:
                raise Refusal('bounded integration windows exhausted; duties retained')
            key = digest(receipt)
            if self.one('SELECT id FROM integration_windows WHERE id=?', (key,)):
                raise Refusal('window selection already recorded; no replay')
            self.budget(None, len(encode(basis).encode()) + len(encode(receipt).encode()))
            self.db.execute('INSERT INTO integration_windows VALUES(?,?,?,?,?,NULL)',
                (key, actor, encode(basis), encode(receipt), self.clock()))
        return self.one('SELECT * FROM integration_windows WHERE id=?', (key,))

    def integration_window(self, row):
        if row['role'] != 'Work' or row['phase'] != 'integrator' or not self.integration_debt():
            return None
        for permit in self.rows('SELECT * FROM integration_windows WHERE job IS NULL ORDER BY rowid DESC'):
            basis = json.loads(permit['basis'])
            if basis['task'] != row['task'] or basis['members'][0]['queue'] != row['id']:
                continue
            try:
                current = self.integration_window_basis(row['task'], [m['event'] for m in basis['members']])
            except Refusal:
                continue
            if current == basis:
                return permit
        raise Refusal('conserved integration debt requires fresh exact owner-selected window')

    def integration_launch_current(self, job):
        self.require_execution_open(job['id'])
        from .local_integration import scope_for
        if scope_for(self, job) is not None:
            return  # Point-specific holds/currentness replace unrelated historical debt acquisition.
        if job['role'] != 'Work' or job['phase'] != 'integrator' or not self.integration_debt():
            return
        permit = self.one('SELECT * FROM integration_windows WHERE job=?', (job['id'],))
        if not permit:
            raise Refusal('integration successor lacks accountable selected window')
        basis = json.loads(permit['basis'])
        if (basis['debt'] != self.integration_debt() or basis['enrollment'] != self.enrollment('Work')
                or basis['members'] != json.loads(job['members'])):
            raise Refusal('integration debt/authority changed before launch; retained reservation needs owner disposition')
        for member in basis['members']:
            queue = self.one('SELECT * FROM queue WHERE id=?', (member['queue'],))
            source = self.one('SELECT hold FROM events WHERE id=?', (member['event'],))
            if (not queue or queue['job'] != job['id'] or queue['state'] != 'reserved'
                    or queue['task'] != job['task'] or not source or source['hold'] is not None
                    or self._input_member(queue) != member):
                raise Refusal('selected integration source changed or held before launch')
            self._integration_member_eligible(queue)
