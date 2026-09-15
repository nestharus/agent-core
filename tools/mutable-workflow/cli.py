#!/usr/bin/env python3
"""Script entry for local mutable workflows. Declared roles: parser, orchestration."""
import argparse
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import sys

from runtime import (ContractError, apply_edit, connect, drive, exclusive,
                     initialize, inspection, read_attempt)


EXIT = {'success': 0, 'failure': 1, 'judgment': 2, 'ready': 3, 'running': 3, 'ambiguous': 4}


def arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('start', 'resume', 'inspect', 'output', 'judge'))
    parser.add_argument('run_dir', type=Path)
    parser.add_argument('--file', type=Path, help='plan for start, response for judge')
    parser.add_argument('--max-steps', type=int, help='stop at a durable step boundary (0 allowed)')
    parser.add_argument('--since', type=int, default=0)
    parser.add_argument('--attempt', type=int)
    args = parser.parse_args()
    if args.max_steps is not None and args.max_steps < 0:
        parser.error('--max-steps must be nonnegative')
    if args.command in ('start', 'judge') and args.file is None:
        parser.error('--file required')
    if args.command == 'output' and args.attempt is None:
        parser.error('--attempt required')
    args.run_dir = args.run_dir.resolve()
    return args


def read_only(args):
    with closing(connect(args.run_dir)) as db:
        return read_view(db, args)


def read_view(db, args):
    if args.command == 'output':
        return read_attempt(db, args.attempt)
    return inspection(db, args.since)


def mutate(args):
    if args.command == 'start':
        initialize(args.run_dir, json.loads(args.file.read_text()))
    with exclusive(args.run_dir):
        return mutate_locked(args)


def mutate_locked(args):
    with closing(connect(args.run_dir)) as db:
        return change(db, args)


def change(db, args):
    if args.command == 'judge':
        return apply_edit(db, json.loads(args.file.read_text()))
    return drive(db, args.run_dir, args.max_steps)


def execute(args):
    if args.command in ('inspect', 'output'):
        return read_only(args), 0
    state = mutate(args)
    return state, EXIT[state['status']]


def main():
    try:
        value, code = execute(arguments())
        print(json.dumps(value, ensure_ascii=True))
        return code
    except (ContractError, OSError, ValueError, TypeError, sqlite3.Error) as exc:
        print(json.dumps({'error': str(exc), 'outcome': 'not_confirmed'}), file=sys.stderr)
        return 5


if __name__ == '__main__':
    sys.exit(main())
