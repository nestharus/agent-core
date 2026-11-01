# Codex headless session cleanup

`cleanup.sh` plans and, under explicit maintenance conditions, deletes old `codex exec` session trees from one Codex CLI profile. It targets **Codex CLI 0.166.0**. The default mode is `plan`, which makes no session deletion. It never starts a profile daemon, resumes a thread, reads turns/items, invokes a model, or writes SQLite directly.

## Run

Quick dry-run, selecting at most ten old headless roots and leaving all sessions intact:

```bash
codex-headless-cleanup --profile "$HOME/.codex2" --plan /tmp/codex-headless-plan.json
```

Without installing the local alias, use `sh "$HOME/ai/tools/codex-session-cleanup/cleanup.sh"` with the same arguments.

The plan path must be new. The default socket is `<profile>/app-server-control/app-server-control.sock`, verified against the selected profile. Planning may omit `--retain`; apply requires an explicit preservation file. Before applying, prepare a JSON array containing every retained thread UUID. Use `[]` only when there are no explicit retains. Keep it with the plan and receipt.

```bash
printf '[]\n' > /path/to/retained-threads.json
/home/nes/ai/tools/codex-session-cleanup/cleanup.sh plan \
  --profile /home/nes/.codex2 \
  --socket /path/to/that-profile/existing-control.sock \
  --retain /path/to/retained-threads.json \
  --plan /path/to/new-plan.json
```

The socket must belong to an **already running** app-server daemon for the selected profile. The client makes a direct Unix-socket WebSocket connection using the documented HTTP Upgrade and JSON-RPC text frames; it does not send JSONL through `app-server proxy`. Supply the known socket path; this tool does not discover processes, inspect FDs, or start/restart a daemon. `initialize` must report the exact `CODEX_HOME` path in the plan. Plan and receipt files must be new paths and are created mode `0600`. The plan includes profile/socket/state-DB inode identities, exact candidate cascade metadata, selected age, explicit retained IDs, inventory count, and a digest. It excludes prompts, previews, titles, turns, instructions, cwd, auth, and log content.

Apply only while the profile is under exclusive maintenance: all interactive, persistent, shared-daemon, and standalone `--no-daemon` clients are quiesced, and new access to this profile is prevented until the command exits. Also establish that every persistent rollout and spawned descendant link is indexed in `state_5.sqlite`; `useStateDbOnly` deliberately does not scan JSONL to repair an incomplete index. These are operator assertions, **not** claims established by `thread/loaded/list`. If either cannot be established, use the plan only and keep the sessions.

```bash
/home/nes/ai/tools/codex-session-cleanup/cleanup.sh apply \
  --profile /home/nes/.codex2 \
  --socket /path/to/that-profile/existing-control.sock \
  --retain /path/to/retained-threads.json \
  --plan /path/to/new-plan.json \
  --receipt /path/to/new-receipt.jsonl \
  --exclusive-maintenance --complete-index
```

Default minimum age is 24 whole hours from the latest of `createdAt`, `updatedAt`, and `recencyAt`; smaller `--min-age-hours` values are refused. The tool also refuses future timestamps. `updatedAt` does not change on resume alone, so age is **not** an active-session guard. The maintenance condition and fresh loaded/status checks are necessary. A new turn, changed metadata, pin, retention input, profile identity, graph, or active/loaded state prevents deletion.

The default limits are 1,000 pages per listing, 10 root deletions, and 60 seconds. Thread metadata is fetched ten records per page to bound replies that include server-provided previews; preview text is discarded. Adjust with `--max-pages`, `--max-delete` (at most 100), and `--deadline-seconds` (at most 600). Planning selects the oldest qualifying roots up to the batch limit. It reports preliminary roots and unexamined remainder separately; unexamined roots have no goal qualification. Apply requires the same batch limit. Each selected root is revalidated with fresh complete inventory, pin/lineage state, metadata-only `thread/read`, and goal status for every cascade member before `thread/delete`. The tool verifies the selected cascade is absent afterward. Durable receipts record an `intent` before each request, then `success` only after verification. A timeout or crash after intent has uncertain outcome; the existing receipt path blocks automatic replay. Inspect the receipt and current metadata and create a new plan and receipt for any separately selected remaining work.

## Qualification and limits

- Root provenance must be the protocol source `exec`. File names, titles, prompts, and model names are never used as provenance. Descendants may have recognized `subAgent*` or `exec` source. Interactive, unknown, custom, or otherwise ambiguous sources block the entire cascade.
- Any pinned, explicitly retained, loaded, active, idle, errored, ephemeral, young, future-dated, or unknown member blocks its root. All archived and non-archived threads and every documented source kind are inventoried without a source filter default. Missing/repeated pages, inventory disagreement, broken/cyclic edges, unknown schema, unavailable socket, and profile mismatch refuse the operation.
- An unfinished goal on any cascade member also blocks the root, including old unloaded sessions. Goal queries retain only `complete`, `unfinished`, or absence; objective text is discarded. Changed goal status is checked again immediately before an effect. Unknown or unavailable goal metadata refuses the operation.
- The installed 0.166.0 protocol schema exposes thread source, lineage, timestamps and runtime status, but **does not expose `isPinned`**. The tool reads only `id`, `is_pinned`, `attached_thread_parent_id`, and `thread_spawn_edges` from the profile's `state_5.sqlite` with a read-only, query-only SQLite connection. It never changes the DB, runs VACUUM, scans rollout bodies, or deletes raw files. Unknown pin/edge schema blocks the operation. Legacy and paginated history are both handled through metadata; neither body format is opened.
- `thread/delete` deletes descendants and returns `{}` on success, but neither it nor `codex delete --force` documents an atomic guard against a concurrent resume/start. The maintenance window is required even when `thread/loaded/list` is empty. The tool has no safe fallback to direct file/DB removal.
- An RPC/state inventory mismatch stops planning with aggregate counts only. Do not remove unknown index entries or session files to make the counts agree. Investigate the mismatch separately; this tool provides no index-repair shortcut.
- No automatic retention timer or database compaction is installed. Reclaimed space can be smaller than the history-size estimate.
- A complete state DB and an exclusive profile maintenance window are **external preconditions**. This command cannot prove either from the 0.166.0 protocol. The generated plan and fake tests do not authorize deletion of a real profile or establish that those preconditions hold.

The interfaces used here are documented in [Codex App Server](https://learn.chatgpt.com/docs/app-server#threads) and [Developer commands](https://learn.chatgpt.com/docs/developer-commands#codex-app-server). This version uses the documented Unix WebSocket framing and checks `/home/nes/.npm-global/bin/codex --version` for exactly 0.166.0. A successful plan against an isolated, empty 0.166.0 managed daemon verified this transport and the current empty-list responses. It does not establish the health, index completeness, or cleanup eligibility of any real profile.

## Test

```bash
cd /home/nes/ai/tools/codex-session-cleanup
python3 -m unittest -v test_cleanup.py
bash -n cleanup.sh
```

The test suite uses a fake Unix WebSocket server, a version-only fake CLI, and isolated SQLite fixtures. Its successful `apply` is simulated; it never addresses a real profile. Set `CODEX_CLEANUP_TEST_TMP` to a private task directory to place automatically removed fixtures there. A separate isolated empty-daemon dry-run is recorded in the task report. The isolated profile and its empty plan are disposable after the report is collected.
