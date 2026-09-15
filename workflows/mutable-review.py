#!/usr/bin/env python3
"""Optional public-CLI handoff; read mutable-review.md before execution.

Declared roles: parser, orchestration. No policy, engine, or recovery ownership.
"""
import argparse
import os
from pathlib import Path
import sys


def arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--adapter', required=True, type=Path,
                        help='explicit trusted adapter cli.py; no default selection')
    parser.add_argument('arguments', nargs=argparse.REMAINDER,
                        help='-- followed by the adapter-owned command and arguments')
    args = parser.parse_args()
    command = args.arguments
    if command[:1] == ['--']:
        command = command[1:]
    if not command:
        parser.error('adapter command required (use -- --help for its public interface)')
    if not args.adapter.is_absolute() or not args.adapter.is_file():
        parser.error('--adapter must name an existing absolute trusted cli.py path')
    return args.adapter, command


def main():
    adapter, command = arguments()
    # Replace this process: preserve the owner's stdout, stderr, exits and signals.
    # No run discovery, config rewriting, retry, or subprocess agent wrapper.
    os.execv(sys.executable, [sys.executable, str(adapter), *command])


if __name__ == '__main__':
    main()
