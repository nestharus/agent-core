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

OPERATIONS = {'integration-closure-basis', 'retire-integration',
              'integration-window-basis', 'select-integration-window',
              'work-read-closure-basis', 'fence-work-proposer'}
READ_FENCE_OPERATIONS = {'work-read-closure-basis', 'fence-work-proposer'}


def basis(runtime, roles, actor, authority, purpose):
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
            grant = board._original(conn, runtime)
            enrollment = runtime.one('SELECT * FROM enrollments WHERE role=?', (role,))
            if (enrollment['owner'] != board.selected['owner']
                    or enrollment['profile'] != board.selected['profile']):
                raise Refusal('original source enrollment owner/profile changed')
            sources[role] = {'binding': board._binding(grant), 'enrollment': enrollment}
    return runtime._integration_bounded({'configuration': digest(runtime.config),
        'implementation': processing.implementation(), 'roles': sources,
        'authority': authority, 'purpose': purpose})


def target(command, args, receipt):
    if command in {'integration-closure-basis', 'retire-integration'} | READ_FENCE_OPERATIONS:
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
        if (not isinstance(prior, dict) or set(prior) != {
                'configuration', 'implementation', 'roles', 'authority', 'purpose'}
                or not isinstance(prior['roles'], dict)):
            raise Refusal('exact current management metadata basis required')
        if basis(self.runtime, list(prior['roles']), self.actor, prior['authority'], prior['purpose']) != prior:
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
        if command in {'integration-closure-basis', 'retire-integration'} | READ_FENCE_OPERATIONS:
            jobs, events = {selected['job']}, set()
        else:
            task = runtime.config['tasks'].get(selected['task'])
            if not task or task['role'] != 'Work' or task['phase'] != 'integrator':
                raise Refusal('management requires exact Work integration task')
            jobs = {r['job'] for r in runtime.rows('SELECT job FROM integration_retirements')}
            jobs |= {r['job'] for r in runtime.rows('SELECT job FROM integration_prestart_dispositions')}
            events = set(selected['events'])
        if set(declared['jobs']) != jobs:
            raise Refusal('tracked job scope differs; no implicit debt/body acquisition')
        roles = {'Work'}
        for job in jobs:
            row = runtime.one('SELECT role,phase,members FROM jobs WHERE id=?', (job,))
            phase = 'proposer' if command in READ_FENCE_OPERATIONS else 'integrator'
            if not row or row['role'] != 'Work' or row['phase'] != phase:
                raise Refusal('management job must be an exact Work '+phase)
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
            if command in {'retire-integration', 'select-integration-window', 'fence-work-proposer'}:
                key = digest(selection)
                runtime.budget(None, len(encode(selection).encode()) + len(encode(outcome).encode()))
                runtime.db.execute('INSERT INTO integration_management_operations VALUES(?,?,?,?,?)',
                    (key, actor, encode(selection), encode(outcome), runtime.clock()))
            return outcome
        finally:
            runtime.integration_management = None
