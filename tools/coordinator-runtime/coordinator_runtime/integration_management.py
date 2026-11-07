"""Genuine owner's explicit paused management, never processing authority.

An operation-local selection reuses the qualified original software-grant
protocol. It neither issues a capability nor changes ordinary enrollment.
Evidence strings are attributed owner assertions, not authentication of facts
outside this journal. Record access needs independent actual authority.
"""
import json
import math

from . import configuration, processing
from .contracts import Refusal, digest, encode, required_text

ROLE_EXECUTION_OPERATIONS = {'role-execution-closure-basis', 'fence-role-execution'}
OPERATIONS = ROLE_EXECUTION_OPERATIONS | {'integration-closure-basis', 'retire-integration',
              'integration-window-basis', 'select-integration-window',
              'work-read-closure-basis', 'fence-work-proposer',
              'integration-metadata-closure-basis', 'retire-integration-metadata',
              'work-read-metadata-closure-basis', 'fence-work-proposer-metadata',
              'integration-no-start-basis', 'withdraw-integration-no-start'}
LOCAL_NO_START_OPERATIONS = {'integration-no-start-basis', 'withdraw-integration-no-start'}
READ_FENCE_OPERATIONS = {'work-read-closure-basis', 'fence-work-proposer'}
METADATA_READ_FENCE_OPERATIONS = {'work-read-metadata-closure-basis', 'fence-work-proposer-metadata'}
METADATA_OPERATIONS = ROLE_EXECUTION_OPERATIONS | ({'integration-metadata-closure-basis', 'retire-integration-metadata'}
                       | METADATA_READ_FENCE_OPERATIONS | LOCAL_NO_START_OPERATIONS)
METADATA_MANAGEMENT = 'integration-metadata-management-v1'


def _metadata_original(board, conn, runtime, *, stopped=True):
    """The original stopped-grant checks with explicit metadata projections.

    Match RetainedBoard._original, including ProcessingBoard's configuration
    bridge. Do not acquire enrollment reconciliation/legacy evidence columns.
    """
    enrollment = runtime.one('SELECT role,owner,profile,grant_id,cutover,intake FROM enrollments WHERE role=?', (board.role,))
    grant = conn.execute('SELECT id,board_id,role,owner,actor,runtime,runtime_dev,runtime_ino,'
                         'issued_by,authority,revoked FROM coordinator_grants_v1 WHERE id=?',
                         (enrollment['grant_id'],)).fetchone() if enrollment else None
    info = runtime.path.stat()
    selected = runtime.config.get('software_delegation', {})
    if stopped and (not grant or not selected or grant['issued_by'] != selected.get('grantor')
            or grant['authority'] != selected.get('authority')
            or grant['revoked'] is None or enrollment['intake'] != 0):
        raise Refusal('exact stopped Work-issued software grant required; no native grant takeover')
    if not stopped and (not grant or grant['revoked'] is not None or enrollment['intake'] != 1):
        raise Refusal('active original owner enrollment/delegation required')
    expected = (board.selected['board_id'], board.role, board.selected['owner'], runtime.config['actor'],
                str(runtime.path), info.st_dev, info.st_ino)
    if tuple(grant[k] for k in ('board_id','role','owner','actor','runtime','runtime_dev','runtime_ino')) != expected:
        raise Refusal('original runtime/source/owner binding changed')
    if stopped:
        cap = conn.execute('SELECT configuration FROM coordinator_software_grants_v1 WHERE grant_id=?', (grant['id'],)).fetchone()
        if not cap or cap['configuration'] != board._configuration(runtime, board._binding(grant)):
            raise Refusal('original immutable software configuration changed')
    return dict(grant), enrollment


def metadata_authority(runtime, actor):
    """Ordinary current Work grant, without enrollment history acquisition."""
    if actor != runtime.config['roles']['Work']['owner'] or runtime.processing is not None:
        raise Refusal('actual current Work owner required; no processing substitution')
    configuration.assert_current(runtime)
    board = processing.ProcessingBoard(runtime.config, 'Work')
    with board.opened() as conn:
        _, enrollment = _metadata_original(board, conn, runtime, stopped=False)
        if enrollment['owner'] != actor or enrollment['profile'] != board.selected['profile']:
            raise Refusal('original source enrollment owner/profile changed')


def basis(runtime, roles, actor, authority, purpose, *, metadata_only=False):
    """Only enrollment/original-grant metadata and public source pins; no bodies."""
    owner = runtime.config['roles']['Work']['owner']
    if actor != owner or runtime.config.get('software_delegation', {}).get('grantor') != owner:
        raise Refusal('genuine Work owner and original software grantor required')
    required_text(authority, 'current management authority', 4000)
    required_text(purpose, 'current management purpose and why', 4000)
    if (not isinstance(roles, list) or not roles or len(roles) != len(set(roles))
            or 'Work' not in roles or any(r not in runtime.config['roles'] for r in roles)):
        raise Refusal('exact distinct configured management source roles including Work required')
    if runtime.processing is not None:
        raise Refusal('management is separate from processing access')
    configuration.assert_current(runtime)
    configuration.assert_release(runtime)
    sources = {}
    for role in roles:
        # ProcessingBoard supplies only its original-configuration bridge here.
        # No Access, _grant, retained basis/body inventory or capability is used.
        board = processing.ProcessingBoard(runtime.config, role)
        with board.opened(settlement=True) as conn:
            if metadata_only:
                grant, enrollment = _metadata_original(board, conn, runtime)
            else:
                grant = board._original(conn, runtime)
                enrollment = runtime.one('SELECT * FROM enrollments WHERE role=?', (role,))
            if (enrollment['owner'] != board.selected['owner']
                    or enrollment['profile'] != board.selected['profile']):
                raise Refusal('original source enrollment owner/profile changed')
            sources[role] = {'binding': board._binding(grant), 'enrollment': enrollment}
    return runtime._integration_bounded({**({'schema': METADATA_MANAGEMENT} if metadata_only else {}),
        'configuration': digest(runtime.config),
        'implementation': processing.implementation(), 'roles': sources,
        'authority': authority, 'purpose': purpose})


def target(command, args, receipt):
    if command in ROLE_EXECUTION_OPERATIONS:
        return {'job':args.job,'token':args.token,'role':args.role,'phase':args.phase}
    if command in {'integration-closure-basis', 'retire-integration'} | READ_FENCE_OPERATIONS | METADATA_OPERATIONS:
        return {'job': args.job, 'token': args.token}
    if command == 'integration-window-basis':
        return {'task': args.task, 'events': args.events}
    if command == 'select-integration-window' and isinstance(receipt, dict):
        value = receipt.get('basis', {})
        if (not isinstance(value, dict) or not isinstance(value.get('task'), str)
                or not isinstance(value.get('members'), list)
                or any(not isinstance(m, dict) or not isinstance(m.get('event'), str)
                       for m in value['members'])):
            raise Refusal('exact window receipt task and input identities required')
        return {'task': value['task'], 'events': [m['event'] for m in value['members']]}
    raise Refusal('unsupported management operation')


class Access:
    """Only IntegrationJournal calls this; Store enrollment/launch stay closed."""
    def __init__(self, runtime, selection, actor):
        self.runtime, self.selection, self.actor = runtime, selection, actor

    def current(self):
        selection = self.selection
        expiry = selection['expires']
        if (type(expiry) not in {int, float} or not math.isfinite(expiry)
                or not self.runtime.clock() < expiry <= self.runtime.clock() + 3600):
            raise Refusal('explicit current management selection must expire within one hour')
        prior = selection['basis']
        metadata = selection['operation'] in METADATA_OPERATIONS
        keys = {'configuration', 'implementation', 'roles', 'authority', 'purpose'} | ({'schema'} if metadata else set())
        if (not isinstance(prior, dict) or set(prior) != keys
                or metadata and prior.get('schema') != METADATA_MANAGEMENT
                or not isinstance(prior['roles'], dict)):
            raise Refusal('exact current management metadata basis required')
        if basis(self.runtime, list(prior['roles']), self.actor, prior['authority'], prior['purpose'], metadata_only=metadata) != prior:
            raise Refusal('management source/configuration/original authority changed; fresh selection required')
        return prior

    def enrollment(self, role):
        source = self.current()['roles'].get(role)
        if not source:
            raise Refusal('source role outside explicit management authority')
        return source['enrollment']

    def records(self, command, selected):
        """Check exact record IDs before full job/result/debt/input acquisition.

        The small header reads below establish the requested relationships, not
        permission to read the referenced bodies. Extra authority is refused.
        Window scope is tracked fence debt only, never all Work history.
        """
        declared = self.selection['records']
        if not isinstance(declared, dict) or set(declared) != {'jobs', 'events'}:
            raise Refusal('exact management jobs/events acquisition scope required')
        for values in declared.values():
            if (not isinstance(values, list) or any(not isinstance(v, str) or not v for v in values)
                    or len(set(values)) != len(values)):
                raise Refusal('distinct explicit management record identities required')
        runtime = self.runtime
        if command in LOCAL_NO_START_OPERATIONS and not runtime.one(
                'SELECT job FROM local_jobs WHERE job=?', (selected['job'],)):
            raise Refusal('paused no-start management requires an exact local reservation; no global debt acquisition')
        if command in {'integration-closure-basis', 'retire-integration'} | READ_FENCE_OPERATIONS | METADATA_OPERATIONS:
            jobs, events = {selected['job']}, set()
        else:
            task = runtime.config['tasks'].get(selected['task'])
            if not task or task['role'] != 'Work' or task['phase'] != 'integrator':
                raise Refusal('management requires exact Work integration task')
            jobs = {r['job'] for r in runtime.rows("SELECT r.job FROM integration_retirements r JOIN jobs j ON j.id=r.job WHERE j.role='Work' AND j.phase='integrator'")}
            jobs |= {r['job'] for r in runtime.rows('SELECT job FROM integration_prestart_dispositions')}
            events = set(selected['events'])
        if set(declared['jobs']) != jobs:
            raise Refusal('tracked job scope differs; no implicit debt/body acquisition')
        roles = {'Work'}
        for job in jobs:
            row = runtime.one('SELECT role,phase FROM jobs WHERE id=? AND token=?',
                (job, selected['token'])) if command in METADATA_OPERATIONS else runtime.one(
                'SELECT role,phase,members FROM jobs WHERE id=?', (job,))
            phase = 'proposer' if command in READ_FENCE_OPERATIONS | METADATA_READ_FENCE_OPERATIONS else 'integrator'
            role = selected['role'] if command in ROLE_EXECUTION_OPERATIONS else 'Work'
            phase = selected['phase'] if command in ROLE_EXECUTION_OPERATIONS else phase
            if not row or row['role'] != role or row['phase'] != phase:
                raise Refusal('management job must be an exact '+role+' '+phase)
            roles.add(role)
            if command in METADATA_OPERATIONS:
                events.update(m['event'] for m in runtime.integration_metadata_sources(job, phase=phase, role=role))
            else:
                events.update(m['event'] for m in json.loads(row['members']))
        if set(declared['events']) != events:
            raise Refusal('related input scope differs; no implicit source/body acquisition')
        for event in events:
            row = runtime.one('SELECT role FROM events WHERE id=?', (event,))
            if not row:
                raise Refusal('exact related source enrollment required')
            roles.add(row['role'])
        if set(self.current()['roles']) != roles:
            raise Refusal('management source roles must match exact related records')


def execute(runtime, command, selected, selection, actor, operation):
    keys = {'basis', 'expires', 'operation', 'target', 'records'}
    if (command not in OPERATIONS or not isinstance(selection, dict) or set(selection) != keys
            or selection['operation'] != command or selection['target'] != selected):
        raise Refusal('explicit management authority must bind this exact operation and target')
    runtime._integration_bounded(selection)
    if getattr(runtime, 'integration_management', None) is not None:
        raise Refusal('existing management operation remains owned')
    access = Access(runtime, selection, actor)
    with runtime.tx():
        access.current()
        access.records(command, selected)
        runtime.integration_management = access
        try:
            outcome = operation()
            access.current()
            if command in {'fence-role-execution', 'retire-integration', 'select-integration-window', 'fence-work-proposer', 'retire-integration-metadata', 'fence-work-proposer-metadata', 'withdraw-integration-no-start'}:
                key = digest(selection)
                if command in METADATA_OPERATIONS:
                    from .selected_source import custody_budget
                    custody_budget(runtime, len(encode(selection).encode()) + len(encode(outcome).encode()))
                else:
                    runtime.budget(None, len(encode(selection).encode()) + len(encode(outcome).encode()))
                runtime.db.execute('INSERT INTO integration_management_operations VALUES(?,?,?,?,?)',
                    (key, actor, encode(selection), encode(outcome), runtime.clock()))
            return outcome
        finally:
            runtime.integration_management = None
