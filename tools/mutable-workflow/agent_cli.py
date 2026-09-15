#!/usr/bin/env python3
"""On-demand judgment controller. See agent-adapter.md, including authority limits.

Declared roles: parser, orchestration.
"""
import argparse
import json
from pathlib import Path
import sqlite3
import sys

from agent_adapter import execute


def arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('ask', 'collect', 'show'))
    parser.add_argument('run_dir', type=Path)
    parser.add_argument('--file', type=Path)
    parser.add_argument('--key')
    args = parser.parse_args()
    if args.command == 'ask' and args.file is None:
        parser.error('ask requires --file')
    if args.command != 'ask' and not args.key:
        parser.error('collect/show require --key')
    return args


def main():
    try:
        args = arguments()
        request = json.loads(args.file.read_text()) if args.command == 'ask' else None
        result = execute(args.run_dir.resolve(), args.command, request, args.key)
        print(json.dumps(result, ensure_ascii=True))
        return 0 if result['state'] == 'returned' else 4
    except (OSError, ValueError, TypeError, KeyError, sqlite3.Error) as exc:
        print(json.dumps({'outcome': 'not_confirmed', 'error': str(exc)}), file=sys.stderr)
        return 5


if __name__ == '__main__':
    sys.exit(main())
