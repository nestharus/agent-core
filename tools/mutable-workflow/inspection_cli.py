#!/usr/bin/env python3
"""Private mutable-run inspection. Read inspection.md for authority and cursor limits.

Declared roles: parser, orchestration.
"""
import argparse
import json
from pathlib import Path
import sqlite3
import sys

import evidence_view
import inspection_policy
import inspection_view as view


def arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    summary = commands.add_parser('summary')
    summary.add_argument('runs', nargs='+', type=Path)
    summary.add_argument('--cursor')
    summary.add_argument('--limit', type=int, default=100, help='events per source, 1..1000')
    for name in ('record', 'node', 'evidence', 'index', 'publish'):
        command = commands.add_parser(name)
        command.add_argument('run', type=Path)
        add_options(name, command)
    return parser.parse_args()


def add_options(name, parser):
    if name == 'record':
        parser.add_argument('--sequence', type=int, required=True)
    if name == 'node':
        parser.add_argument('--node', required=True, help='node incarnation, not display ID')
    if name == 'publish':
        parser.add_argument('--file', type=Path, required=True)
    if name == 'evidence':
        parser.add_argument('--key', required=True)
        parser.add_argument('--verify', action='store_true', help='read/hash local log bytes')
        parser.add_argument('--check-session', action='store_true', help='execute configured public session locate only')


def execute(args):
    if args.command == 'summary':
        return view.page(args.runs, args.cursor, args.limit)
    directory = args.run.resolve()
    if args.command == 'record':
        return view.record(directory, args.sequence)
    if args.command == 'node':
        return view.node(directory, args.node)
    if args.command == 'evidence':
        return evidence_view.evidence(directory, args.key, args.verify, args.check_session)
    if args.command == 'index':
        return view.index(directory)
    return inspection_policy.publish(directory, json.loads(args.file.read_text()))


def main():
    try:
        print(json.dumps(execute(arguments()), ensure_ascii=True))
        return 0
    except (OSError, ValueError, TypeError, KeyError, sqlite3.Error) as exc:
        print(json.dumps(dict(outcome='not_confirmed', error=str(exc))), file=sys.stderr)
        return 5


if __name__ == '__main__':
    sys.exit(main())
