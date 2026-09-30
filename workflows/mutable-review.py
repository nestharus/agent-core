#!/usr/bin/env python3
"""New-run default public-CLI handoff; read mutable-review.md before execution.

Declared roles: parser, orchestration. No policy, engine, or recovery ownership.
"""
import argparse
import os
from pathlib import Path
import sys


def arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--adapter', type=Path,
                        help='explicit adapter; preserve its commands and selection unchanged')
    parser.add_argument('arguments', nargs=argparse.REMAINDER,
                        help='-- followed by the adapter-owned command and arguments')
    args = parser.parse_args()
    command = args.arguments
    if command[:1] == ['--']:
        command = command[1:]
    if not command:
        parser.error('adapter command required (use -- --help for its public interface)')
    adapter = args.adapter
    if adapter is None:
        checkout = Path(os.environ.get('CRW_CHECKOUT',
                        '/home/nes/projects/code-review-workflows/trunk'))
        adapter = checkout / 'risk-axis-reviewers/workflows/corrected-cohort/cli.py'
        if command[0] == 'start':
            command[0] = 'start-default'
    if not adapter.is_absolute() or not adapter.is_file():
        parser.error('adapter (--adapter or CRW_CHECKOUT default) must name an existing absolute trusted cli.py path')
    return adapter, command


def main():
    adapter, command = arguments()
    # Replace this process: preserve the owner's stdout, stderr, exits and signals.
    # Only new default start is routed; CRW owns configuration and all semantics.
    # No saved-run rewriting, retry, or subprocess agent wrapper.
    os.execv(sys.executable, [sys.executable, str(adapter), *command])


if __name__ == '__main__':
    main()
