#!/usr/bin/env python3
"""Record owner-confirmed interactive session handover milestones."""

import argparse
import datetime as dt
import json
import os
from pathlib import Path
import stat
import sys


REQUEST = """# Request to the current session owner

Please write a new summary yourself in a durable file. Include the purpose and
current decisions, completed work and evidence paths, unfinished work, pending
messages or approvals, exact next actions, and how to resume or recover. State
uncertainty clearly. Do not copy private transcript material into the summary.

Send the summary path to the replacement owner. Wait for the replacement to
read it, confirm adoption, and take responsibility for unfinished work. Only
then close this old session through its normal client route. Session-history
deletion is a separate, later maintenance decision; this request grants none.
"""


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def write_new(path, content):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())


def state_path(directory):
    return directory / "state.json"


def read_state(directory):
    with state_path(directory).open() as stream:
        return json.load(stream)


def save_state(directory, value):
    target = state_path(directory)
    temp = directory / (".state-" + str(os.getpid()))
    write_new(temp, json.dumps(value, indent=2, sort_keys=True) + "\n")
    os.replace(temp, target)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    new = sub.add_parser("request")
    new.add_argument("--dir", required=True, help="new durable handover directory")
    new.add_argument("--old-label", required=True, help="owner-facing session label; no transcript")
    for name in ("queued", "summary", "adopted", "closed", "status"):
        command = sub.add_parser(name)
        command.add_argument("--dir", required=True)
        if name == "summary":
            command.add_argument("--summary", required=True)
        if name == "adopted":
            command.add_argument("--replacement-label", required=True)
        if name not in ("status",):
            command.add_argument("--owner-confirmed", action="store_true")
    args = parser.parse_args()
    directory = Path(args.dir).absolute()
    try:
        if args.action == "request":
            directory.mkdir(mode=0o700, parents=False, exist_ok=False)
            write_new(directory / "REQUEST.md", REQUEST)
            value = {"phase": "request_prepared", "old_label": args.old_label,
                     "prepared_at": now()}
            write_new(state_path(directory), json.dumps(value, indent=2, sort_keys=True) + "\n")
        else:
            value = read_state(directory)
            if args.action == "status":
                print(json.dumps(value, indent=2, sort_keys=True))
                return 0
            if not args.owner_confirmed:
                raise ValueError("milestone requires --owner-confirmed")
            previous = {"queued": "request_prepared", "summary": "request_queued",
                        "adopted": "summary_written", "closed": "replacement_adopted"}
            if value["phase"] != previous[args.action]:
                raise ValueError("handover milestones must be recorded in order")
            if args.action == "queued":
                value["phase"] = "request_queued"
                value["queued_at"] = now()
            elif args.action == "summary":
                summary = Path(args.summary).absolute()
                info = summary.lstat()
                if not stat.S_ISREG(info.st_mode) or info.st_size == 0:
                    raise ValueError("summary must be an existing nonempty regular file")
                value["phase"] = "summary_written"
                value["summary_path"] = str(summary)
                value["summary_recorded_at"] = now()
            elif args.action == "adopted":
                value["phase"] = "replacement_adopted"
                value["replacement_label"] = args.replacement_label
                value["adopted_at"] = now()
            else:
                value["phase"] = "old_session_closed"
                value["closed_at"] = now()
            save_state(directory, value)
        print(json.dumps(value, indent=2, sort_keys=True))
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"handover: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
