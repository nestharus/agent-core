# Session maintenance

These commands keep OpenCode full-session reset and interactive handover explicit.
They do not run on a timer, start a model or daemon, inspect process environments,
or read client transcripts, credentials, account contents, or project contents.
They do not touch native DB/state or protected Source/capture namespaces.

## OpenCode: inventory, then optional full reset

Run against **one selected OpenCode SQLite database** at a time. The examples
use a placeholder; select and verify the actual `opencode.db` path yourself.
Inventory reads schema and row counts only and never deletes:

```bash
python3 /home/nes/ai/tools/session-maintenance/maintenance.py inventory \
  --db /absolute/path/to/opencode.db
```

Full reset removes **all** session, message, part and foreign-key-dependent
session rows, plus session-scoped event and event-sequence rows. It includes
interactive and noninteractive history. Use it only after all affected owners
have handed over or expressly released that history. Confirm that all clients
using the selected store are closed and new access is prevented for the whole
command, including compaction. Then run:

```bash
python3 /home/nes/ai/tools/session-maintenance/maintenance.py reset \
  --db /absolute/path/to/opencode.db \
  --receipt /absolute/path/to/new-reset-receipt.jsonl \
  --full-sessions --apply --exclusive-maintenance
```

`--full-sessions`, `--apply`, and `--exclusive-maintenance` are all required.
The last flag is the operator's assertion of a maintenance window, not a lock
against a newly launched client. The command also refuses a running `opencode`
process, any open database/WAL/SHM consumer found by `fuser`, changed database
identity, unsupported or unsafe schema, existing foreign-key damage, and low
free space for `VACUUM`. It requires an owned, regular, single-link file named
`opencode.db`, direct directory components, and regular owned WAL/SHM files;
`pgrep` and `fuser` must be installed. SQLite exclusive locking covers the
transaction and compaction. Do not use this command when the maintenance
window cannot be established.

The receipt path must be new and is written with mode `0600`. It records intent
before deletion, row-commit progress, and completion or error. If an intent
exists without completion, the result is uncertain: inspect that receipt and
current metadata before choosing a **new** operation and receipt. Reusing a
receipt is refused. Successful reset checks that session rows are gone,
non-session table counts are unchanged, SQLite foreign keys and quick check
pass, and the WAL checkpoint completes. `VACUUM` reclaims free database pages;
reported allocated bytes are local file allocation, not a guaranteed amount
of free drive space. Preserve receipts while they are needed for recovery and
audit, then retire them through the normal artifact cleanup process.

The tool does not remove legacy session files outside this SQLite database,
undo snapshots, Codex history, native state, or any other store. It does not
prove that all owners have released their history. Schema mismatches are a
stop, not a reason to expand deletion scope.

## Codex: use the existing conservative cleaner

Use [the Codex headless session cleanup tool](../codex-session-cleanup/README.md)
for Codex CLI profiles. Its default plan is read-only. Apply requires
independent confirmation of exclusively headless use, retained IDs, a complete
index, and exclusive maintenance; `exec` creation origin alone is insufficient.
Human, active, unknown, pinned, goal-bearing, and linked sessions remain
protected. This directory does not implement another Codex deleter or a
whole-profile Codex wipe.

## Interactive owner handover

Prepare a request in a new durable directory:

```bash
python3 /home/nes/ai/tools/session-maintenance/handover.py request \
  --dir /absolute/path/to/new-handover \
  --old-label 'owner-facing session label'
```

Send `REQUEST.md` to the **current owner** through the normal session route.
The helper does not send it. A queued request is not a written summary. Record
each actual milestone only after the named owner confirms it:

```bash
python3 /home/nes/ai/tools/session-maintenance/handover.py queued \
  --dir /absolute/path/to/new-handover --owner-confirmed
python3 /home/nes/ai/tools/session-maintenance/handover.py summary \
  --dir /absolute/path/to/new-handover \
  --summary /absolute/path/to/owner-written-summary.md --owner-confirmed
python3 /home/nes/ai/tools/session-maintenance/handover.py adopted \
  --dir /absolute/path/to/new-handover \
  --replacement-label 'replacement owner/session label' --owner-confirmed
python3 /home/nes/ai/tools/session-maintenance/handover.py closed \
  --dir /absolute/path/to/new-handover --owner-confirmed
python3 /home/nes/ai/tools/session-maintenance/handover.py status \
  --dir /absolute/path/to/new-handover
```

The owner writes the summary; the replacement reads it and explicitly accepts
the unfinished work; the old owner then closes the old session through its
normal client route. The helper only records assertions and a summary path. It
does not read the summary, verify authorship, launch a replacement, close a
client, or authorize history deletion. Keep the handover directory and summary
while work or recovery depends on them. Delete old history only through a
separately qualified maintenance operation after closure and retention review.

## Test

```bash
cd /home/nes/ai/tools/session-maintenance
python3 -m unittest -v test_maintenance.py
```

Tests create and delete only temporary synthetic databases and handover files.
No real profile or store is addressed.
