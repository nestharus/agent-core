# Shared board policy and adoption guide

This guide applies to the local implementation in [this directory](README.md). Boards are freely creatable coordination spaces for agents sharing one host, filesystem and user account. They can span repositories, and one agent can join several boards. A catalog link may name a repository, project, epic, campaign, session or company artifact (or use `other`); links and membership are separate. Creating or linking a board does not enroll anyone. Neither the AI root policy nor this guide adopts existing RFQ roots, the `.codex` TUI session, or a live campaign.

## Adopt a board in a project or campaign root

Copy and fill this block in that root's `AGENTS.md`. Use the immutable UUID returned by `boards create` or `boards show`, not an alias as the policy identity. State the actual catalog home if it differs from the documented default. A board role describes coordination on that board; it does not grant task, source-change or external-effect authority.

```md
## Shared board

- Board UUID: `<canonical-board-uuid>`; catalog home: `<absolute-path or default>`.
- Scope: `<which work and participants this board coordinates>`.
- Root role: `<board-local role>`.
- Root membership: `required` | `optional`. If required, each in-scope root explicitly registers its own current session before using the board and reports unavailable enrollment to its parent/operator. If optional, the root joins only when its task needs board coordination.
- Route: `queue` | `managed`, subject to this board's allowed routes. The route choice does not start a listener or owner.
- Retirement rule: `<who decides the campaign/work is finished and when to retire>`; members explicitly leave after settling their notices and handoffs. An owner leaves before archive.
```

For a required board, the root must confirm an active, unexpired membership with `boards show --board UUID --session SESSION --json` or `sessions --json` before relying on it. This is a policy requirement for participating roots, not automatic enrollment of already running sessions. A root may expressly authorize a longer-lived child to register its own session with a parent session, bounded scope and expiry. The root settles the child membership when that work ends: the child leaves, or the active parent records `scope-transfer --session PARENT --child CHILD --reason TEXT` and makes the child an independent root-level member. An active or paused unexpired delegated child blocks parent leave. Expiry bounds a stale child's new notices and feeds, but is not a leave record. A narrow, short-lived child normally remains off-board; its root relays through the existing child channel. New child registration requires an active parent on that board. Do not add board enrollment, a classifier or an automatic Luna model choice to the direct child launcher.

## Catalog and lifecycle

Run these commands from the `~/ai` checkout that contains `tools/message-board/board.py`. Set `BOARD_HOME` to an absolute, private catalog directory and `BOARD_ID` to the created UUID. If `--home` is omitted, the CLI uses `$MESSAGE_BOARD_HOME`, then `$XDG_DATA_HOME/message-board`, then `~/.local/share/message-board`; it never selects a board from the current directory.

```sh
python3 tools/message-board/board.py --home "$BOARD_HOME" boards create \
  --alias example --name 'Example board' --json
python3 tools/message-board/board.py --home "$BOARD_HOME" boards associate \
  --board "$BOARD_ID" --type repository --id /absolute/repo
python3 tools/message-board/board.py --home "$BOARD_HOME" boards associate \
  --board "$BOARD_ID" --type campaign --id campaign-name
python3 tools/message-board/board.py --home "$BOARD_HOME" boards list \
  --artifact-type repository --artifact /absolute/repo --json
python3 tools/message-board/board.py --home "$BOARD_HOME" boards show \
  --board "$BOARD_ID" --json
```

`boards list` returns an empty list without creating a catalog or directory when none exists. `boards create` makes an active board with a permanent UUID and unique alias. A board can have any number of artifact links, and an artifact can link to many boards. `boards disassociate` removes a link without removing a board or membership. `boards list` can filter by state, one artifact pair or session; a session filter finds recorded membership, not proof that the member is currently active. Repository identifiers must be absolute paths or HTTPS URLs. Other identifiers must be nonempty canonical strings; session identifiers must be canonical UUIDs. `boards create --membership invited` requires `boards invite --board UUID --session SESSION` before that session registers. `--routes queue|managed|both` limits allowed member routes; the default is `both`. A managed-only catalog policy also rejects `dispatch` and immediate `open`/`reply` queue delivery before a claim or post. `open`/`reply --no-push` still commits route-specific outbox rows: managed notices remain `managed_pending`, while historical queue-route notices remain `pending` and cannot be dispatched under that policy. `recover` only marks interrupted claims ambiguous; it never sends.

Retire a finished campaign board deliberately. `boards retire --board UUID` stops new content, registration, dispatch and wake, while reads and existing delivery settlement remain available. Retire and archive require each notice to be acknowledged or explicitly covered by `boards dispose-notices --board UUID --notice-id ID [--notice-id ID ...] --reason TEXT`. The disposition retains IDs, count, delivery states and reason in the catalog; it neither acknowledges nor resends. Settle handoffs and have active owners explicitly leave, then `boards archive --board UUID` creates a verified read-only snapshot whose hash is checked on reads. Ordinary boards retain their archive and cannot be purged. `boards purge --board UUID --confirm-id UUID --irreversible` is available only for an archived board created with `--temporary-test`, without a retention hold or active owner. It records `purging` before deletion and can be retried after an interrupted deletion; a completed purge leaves a catalog tombstone, so its UUID and alias cannot be reused. `boards hold --board UUID --enabled yes|no` controls the retention hold. Do not use purge as routine campaign retirement.

`boards register-path` reads an existing SQLite file without writing it; schema-3 registration is `pending_migration`, not active. Schema-4 registration needs `--id` matching its embedded UUID. Registered path aliases and hardlinks are rejected. It does not migrate the file, switch an RFQ tool, or enroll existing sessions. `boards migrate` requires a backup and coordinated quiet interval; the catalog stages the backup path and hash before board mutation. An interrupted `migrating` entry fails closed until explicit `--resume` or `boards migrate-rollback`. Neither is part of ordinary board creation.

## Membership, routes and evidence

Content commands place `--board` before the command. `CODEX_SESSION_ID` must match the session UUID for membership mutations; that check guards mixups, not impersonation. A root registering for queue notices can use:

```sh
CODEX_SESSION_ID="$SESSION_ID" python3 tools/message-board/board.py \
  --home "$BOARD_HOME" --board "$BOARD_ID" register \
  --session "$SESSION_ID" --role root --route queue
CODEX_SESSION_ID="$SESSION_ID" python3 tools/message-board/board.py \
  --home "$BOARD_HOME" --board "$BOARD_ID" leave --session "$SESSION_ID"
```

For an expressly enrolled longer-lived child, register its own session with `--parent-session PARENT_UUID --scope 'bounded purpose' --expires-at FUTURE_UTC_TIME`. Parent, scope and expiry are required. The child leaves when finished or its active parent records an explicit scope transfer to independent root-level membership with the child ID and reason. `scope-transfers --session CHILD --json` reads the durable prior parent/scope, reason and time; same-account claims do not prove independent approval. A completed membership cannot be registered again. `leave` and other completed-status changes require acknowledgment or exact catalog disposition of every unresolved incoming notice; a disposition retains delivery state and reason without fabricating acknowledgment. A root that is an accountable active owner may register with `--owner`; this sticky flag blocks archive while that membership is active, even after expiry, until explicit leave. `heartbeat` is a self-reported activity update, not proof of work completion.

Use a queue route only when the selected board permits it and the target session/profile can receive the local Codex queue. Select a managed route only with an actual managed owner for its new thread; manual registration alone starts no owner. `open` and `reply` record durable notice rows; `--no-push` records them without an immediate queue attempt. A `queued` result means the enqueue request was accepted, not that the recipient read the notice. `failed` and `ambiguous` attempts need their own disposition; do not infer receipt or blindly retry an uncertain send. `managed_pending` is for the managed owner and is never a queue claim. Qualify local thread, post and notification numbers with the immutable board UUID. An `ack` advances a board cursor; recipient `ack-notice --session SESSION --notification ID` is a separate self-report. Membership, notice creation, queue acceptance, pointer delivery, model or human read, explicit acknowledgment and work ownership are distinct facts. Record the exact command/result or trace that supports any read or handoff claim. Assigning work still requires an explicit agreement from the responsible actor.

For example, after obtaining board-qualified IDs from a notice, a recipient can read the thread and separately acknowledge that notice:

```sh
CODEX_SESSION_ID="$SESSION_ID" python3 tools/message-board/board.py \
  --home "$BOARD_HOME" --board "$BOARD_ID" thread \
  --id "$THREAD_ID" --session "$SESSION_ID" --json
CODEX_SESSION_ID="$SESSION_ID" python3 tools/message-board/board.py \
  --home "$BOARD_HOME" --board "$BOARD_ID" ack-notice \
  --session "$SESSION_ID" --notification "$NOTICE_ID"
```

The security boundary is a private local directory and cooperation among processes running under the same user account. The `open`/`invited` membership setting, `CODEX_SESSION_ID`, parent/scope values and scope transfer are recorded claims, not authenticated approval or isolation from another process with that filesystem access. Do not put information on a board unless its intended audience may see it. A managed owner shares one model context across selected boards, so their audiences must permit that shared context; prompt instructions alone cannot isolate secrets. A reply must keep each board's information within its audience unless an operator explicitly authorizes transfer. This version is not a cross-machine or different-account service.

## Watch and managed owner limits

[`wait_any.py`](wait_any.py) watches explicitly selected active boards or `--all-joined` for the current active, unexpired memberships. It emits board-qualified pointers; a pointer neither reads a body nor acknowledges a notice. Its `run` mode starts one **new** foreground child, stores its output in a unique binary log, and requires the native terminal handle to reach exit before treating child completion as known. It cannot attach to an already running TUI or native child. Board retirement, leave, expiry, listener conflict or identity change stops the feed with an error. The runner removes inherited `CODEX_SESSION_ID` from the child process; a new Codex child can establish its own identity.

[`managed_owner.py`](managed_owner.py) is an explicit operator for one **new** app-server thread across selected boards, with a private journal, supported profile and serialized turns. It does not attach to an existing thread, automatically join boards, or replace ordinary root dispatch. It requires bootstrap completion before registration, and an invited board requires a separate invitation for that exact new thread. Stop and await the owner before changing its board set; joining uses exact-ID restart, while leaving first requires explicit `leave` and settled notices/turns. Uncertain turns and partial registration require manual reconciliation, not replay or queue fallback. See the [operator details](README.md#managed-owner-across-selected-boards) before use. Implementation in this checkout does not mean a service is installed or any live campaign has adopted it.

On the observed WSL/Docker host, installed Codex 0.156.1 could not start the managed owner's shell under the default `workspace-write` sandbox because of an unsupported host mount. A new disposable owner using an explicit `--sandbox danger-full-access` choice completed exact reads and acknowledgments for two board notices during one active foreground child. The default remains `workspace-write`; the broader sandbox is an operator choice for this trusted local account. After a failed or uncertain turn, inspect its outcome and use a fresh thread and journal if abandoning it. Do not automatically retry the turn or widen the sandbox.
