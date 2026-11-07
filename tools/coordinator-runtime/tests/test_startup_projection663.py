"""Enclosing CLI startup on owned transitioned journals, with no live effects.

The historical transition row is explicit synthetic protocol state, including
unselected old identifiers. Board grants, pins and CLI operations use the public
fixture APIs. SDK identity and model answers are fiction as in QA629; no release
qualification or actual configuration transition/adoption is claimed.
"""
from contextlib import contextmanager, redirect_stdout
import copy
import io
import json
import os
from pathlib import Path
import sqlite3
from unittest.mock import patch

import test_selected_basis50115 as selected
from test_qa629_repairs import Fixture
from coordinator_runtime import cli, configuration, processing
from coordinator_runtime.board import module_at
from coordinator_runtime.contracts import digest, encode
from coordinator_runtime.store import Store


class StartupProjection(Fixture):
    configure = selected.SelectedBasis.configure
    route_receipt = selected.SelectedBasis.route_receipt

    def setUp(self):
        selected.SelectedBasis.setUp(self)
        self.original_config = copy.deepcopy(self.config)
        self.original_hash = digest(self.config)
        # Only setup has broad authority over this newly created synthetic row.
        self.transition = dict(
            basis=dict(tasks=list(self.config['tasks']),
                       processing=processing.basis(self.store, self.boards, future_only=True)),
            previous_configuration=self.original_config,
            jobs=['unselected-historical-job'], outboxes=['unselected-historical-outbox'],
            collectors={'unselected-historical-attempt': 'original-collector'},
            event_boundary=processing.source_boundary(self.store))
        self.config = copy.deepcopy(self.config)
        self.config['recheck_seconds'] *= 2
        self.config_path = self.area / 'current-config.json'
        self.config_path.write_text(encode(self.config))
        self.pins_path = self.area / 'selected-pins.json'
        self.pins_path.write_text(encode([self.expected]))
        self.selection_path = self.area / 'selection.json'
        self.selection_path.write_text('{}')

    def install_transition(self, *, close=True, **overrides):
        row = dict(previous=self.original_hash, current=digest(self.config),
                   original=self.original_hash, configuration=encode(self.config))
        row.update(overrides)
        self.store.db.execute(
            'INSERT INTO configuration_transitions(previous,current,original,configuration,selection,issuer,created) '
            'VALUES(?,?,?,?,?,?,?)',
            (*[row[k] for k in ('previous', 'current', 'original', 'configuration')],
             encode(self.transition), self.issuer, self.store.clock()))
        if close:
            self.store.close()

    def selection(self, basis):
        choice = selected.SelectedBasis.selection(self, basis)
        choice['service']['allocations'] = dict(
            basis=basis['allocation'], target='fixture next allocation',
            reason='Retain original charged use', evidence='Synthetic Work decision',
            custody={r: dict(owner=v['owner'], evidence='Original duties retained')
                     for r, v in self.config['roles'].items()},
            expires=self.store.clock() + 600, max_windows=1)
        return choice

    @contextmanager
    def startup_guard(self):
        """Install before Store construction; guard direct SQL and SDK opens."""
        connect = sqlite3.connect
        runtime_path = str(Path(self.config['state_dir']) / 'runtime.sqlite3')
        selected_id = self.source['id']
        opened, denied, projections = [], [], []
        forbidden = {'outboxes', 'attempts', 'results', 'artifact_blobs',
                     'artifact_custody', 'attempt_storage', 'source_custody', 'operational_errors'}

        class Guarded(sqlite3.Connection):
            selection_projection = False

            def execute(conn, sql, parameters=(), /):
                lower = ' '.join(sql.lower().split())
                if lower.startswith('select'):
                    for table in ('input_resolutions', 'queue', 'processing_source_positions'):
                        if 'from ' + table in lower and (
                                'where event=?' not in lower or not parameters or parameters[0] != selected_id):
                            raise AssertionError('unselected mapping metadata: ' + sql)
                    if ' from events' in lower and 'max(rowid)' not in lower:
                        if 'where id=?' not in lower or not parameters or parameters[0] != selected_id:
                            raise AssertionError('unselected event metadata: ' + sql)
                # Permit only the two existing typed selection projections.
                conn.selection_projection = (
                    lower.startswith("select json_extract(selection,'$.basis.tasks') as tasks ")
                    or lower.startswith('select json_extract(selection,?) as binding ')
                    and parameters and parameters[0] in {
                        '$.basis.processing.roles.' + r + '.original.binding' for r in self.config['roles']})
                try:
                    if conn.selection_projection:
                        projections.append(sql)
                    return super().execute(sql, parameters)
                finally:
                    conn.selection_projection = False

        def guarded_connect(database, *args, **kwargs):
            is_runtime = str(database) == runtime_path
            if is_runtime:
                kwargs['factory'] = Guarded
            conn = connect(database, *args, **kwargs)
            opened.append(conn)

            def authorize(action, table, column, db, caller):
                if action == sqlite3.SQLITE_READ:
                    if is_runtime and (
                            table in forbidden
                            or table == 'events' and column in {'payload', 'error', 'ack_receipt'}
                            or table == 'processing_capabilities' and column == 'selection'
                            or table == 'configuration_transitions' and column == 'selection'
                            and not conn.selection_projection):
                        denied.append((table, column))
                        return sqlite3.SQLITE_DENY
                    if not is_runtime and table in {
                            'coordinator_deliveries_v1', 'coordinator_software_deliveries_v1'} and column == 'payload':
                        denied.append((table, column))
                        return sqlite3.SQLITE_DENY
                if not is_runtime and action == sqlite3.SQLITE_FUNCTION and column and column.lower() == 'length':
                    denied.append(('function', 'length'))
                    return sqlite3.SQLITE_DENY
                return sqlite3.SQLITE_OK

            conn.set_authorizer(authorize)
            return conn

        def fixture_module(directory, name, *args, **kwargs):
            module = module_at(directory, name, *args, **kwargs)
            if name == 'board_store':
                def acting(expected):
                    if expected != self.issuer:
                        raise module.UserError('synthetic SDK principal mismatch')
                    return self.issuer
                module.acting_session = acting
            return module

        try:
            with patch.object(sqlite3, 'connect', guarded_connect), \
                 patch('coordinator_runtime.board.module_at', side_effect=fixture_module), \
                 patch.object(Store, 'event', side_effect=AssertionError('source body acquired')), \
                 patch.object(processing.ProcessingBoard, '_usage', side_effect=AssertionError('historical payload sizes')), \
                 patch('coordinator_runtime.store.owned_bytes', side_effect=AssertionError('historical capture accounting')), \
                 patch.dict(os.environ, {'CODEX_SESSION_ID': self.issuer}):
                yield projections
        finally:
            for conn in opened:
                conn.close()  # Includes any constructor refused before Store.close.
        self.assertTrue(opened, 'guard must enclose an actual connection open')
        self.assertEqual(denied, [])

    def command(self, command):
        options = (['--selected-retained', str(self.pins_path)] if command == 'processing-basis'
                   else ['--selection', str(self.selection_path)])
        args = cli.parser().parse_args(['--config', str(self.config_path), command, *options])
        output = io.StringIO()
        with redirect_stdout(output):
            status = cli.main_owned(args)
        return status, json.loads(output.getvalue())

    def test_selected_basis_main_owned_starts_inside_guard(self):
        self.install_transition()
        with self.startup_guard() as projections:
            status, basis = self.command('processing-basis')
        self.assertEqual(status, 0, basis)
        self.assertEqual(basis['mode'], 'selected-retained-source-v1')
        self.assertEqual(basis['selected_retained'], [self.expected])
        self.assertEqual(basis['configuration'], digest(self.config))
        self.assertNotIn('unselected-historical', encode(basis))
        self.assertTrue(projections)

    def test_delegate_main_owned_reopens_inside_guard(self):
        self.install_transition(close=False)
        # Prepare the delegate operand through the existing metadata-only API,
        # so its startup regression is independent of the basis CLI startup.
        self.store.config = self.config
        with selected.SelectedBasis.sentinel(self):
            basis = selected.SelectedBasis.basis(self)
        self.store.close()
        self.selection_path.write_text(encode(self.selection(basis)))
        with self.startup_guard():
            status, issued = self.command('delegate-processing')
        self.assertEqual(status, 0, issued)
        self.assertEqual(issued['issuer'], self.issuer)
        self.assertTrue(issued['capability'])
        # Read only public issuance metadata after the guarded operations.
        with sqlite3.connect(self.store.path) as conn:
            self.assertEqual(conn.execute('SELECT id FROM processing_capabilities WHERE revoked IS NULL').fetchall(),
                             [(issued['capability'],)])
            self.assertEqual(conn.execute('SELECT number,configuration,used,new_inputs,actor,created FROM service_windows').fetchall(),
                             [tuple(self.original_allocation[k] for k in ('number', 'configuration', 'used', 'new_inputs', 'actor', 'created'))])

    def assert_binding_refused(self, **overrides):
        self.install_transition(**overrides)
        with self.startup_guard(), patch.object(cli, 'operate', wraps=cli.operate) as operation:
            for command in ('processing-basis', 'delegate-processing'):
                with self.subTest(command=command):
                    status, held = self.command(command)
                    self.assertEqual(status, 2, held)
                    self.assertEqual(held['state'], 'held')
                    self.assertIn('configuration', held['error'])
            operation.assert_not_called()

    def test_wrong_current_binding_refuses_both_commands_before_operate(self):
        self.assert_binding_refused(current='0' * 64)

    def test_wrong_original_binding_refuses_both_commands_before_operate(self):
        self.assert_binding_refused(original='0' * 64)

    def test_wrong_configuration_body_refuses_both_commands_before_operate(self):
        wrong = {**self.config, 'recheck_seconds': self.config['recheck_seconds'] * 2}
        self.assert_binding_refused(configuration=encode(wrong))

    def test_direct_api_remains_compatible_under_startup_guard(self):
        self.install_transition()
        with self.startup_guard():
            store = Store(self.config)
            try:
                boards = {r: processing.ProcessingBoard(self.config, r) for r in self.config['roles']}
                basis = processing.basis(store, boards, selected_retained=[self.expected])
                issued = processing.select(store, boards, self.selection(basis))
            finally:
                store.close()
        self.assertTrue(issued['capability'])

    def test_untransitioned_startup_and_whole_transition_api_remain_compatible(self):
        store = Store(self.original_config)
        try:
            self.assertIsNone(configuration.current_binding(store))
            self.assertIsNone(configuration.latest(store))
        finally:
            store.close()
        # Only this positive fixture API check has whole synthetic-row authority.
        self.install_transition()
        store = Store(self.config)
        try:
            self.assertEqual(json.loads(configuration.latest(store)['selection']), self.transition)
            self.assertEqual(configuration.current_binding(store), dict(
                current=digest(self.config), original=self.original_hash, configuration=encode(self.config)))
        finally:
            store.close()
