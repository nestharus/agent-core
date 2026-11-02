# Existing monitor integration

Current contract: `existing-collector-dag/v1`, using the unchanged durability-fixed
core SHA256 `9ad637dd6a3677b17894726e9f6e655f6f1b19e2ce8d9b3f4725fb18cfb697a0`.
The pin is the reviewed 21200 core, joined with the nine 60883 collector files;
it is not a replacement oracle. The previous source and failed results remain in
those completed task homes and in the conserved feature preimage.

The existing producer is
`/home/nes/.local/share/rfq-root-emergency-captures/01a1276d-c325-7c01-a079-ca1fbea2a3f4/20261030/Install-Work-board-monitors-using-allowed-dot-codex3-profile-20261101/tool/monitor.py`.
Its `execute('branches')` publishes commands, latest, then health. The existing
oneshot service/timer owns its loop. Do not create a second collector or scheduler.
After the health write, its owner can call `existing_monitor_check` from
`collector_dag_adapter`, passing the in-memory latest/health/commands values,
a bounded native packet and its actual observation UTC, the normal repository
and binding, independently selected producer code version, `now`, and its chosen
canonical journal/lock/capture paths, owner and distinct check ID. Pass an
`OwnerBindings` only for independently established logical facts in that scope.
The installed library also exposes `foreground_check` for frozen bundles and
`run_collector_dag_once.py` as an executable foreground replay consumer.

The producer is actively owned by the installed monitor role
`01a1996f-630f-7642-9bfc-45f22bf68724` under its existing Root. Activation must be
coordinated with that owner; this feature does not edit its live source/settings.
Metadata alerts formerly sent to Work use the actual settings recipient
Dispatcher `01a19aac-f392-7a50-9892-a1e59b784e37`, thread9900. Branch/DAG/CI
alerts retain Branch `01a18bb3-2d8f-7eb0-a1ef-31b62ae96198`. Ordinary Work
coordination is unaffected. No receiver, role, identity or service is registered.

Projection consumes relevant fields after explicit repo/PR/ref selection. Extra
producer metadata is ignored and never gains execution authority. Only command
generation and count are projected; command argv are never executed. Consumed
fields retain type, generation, CAS, freshness and coverage checks. `READ` is
the actual producer's successful remote-ref coverage spelling; partial errors
and health remain explicit. A branch row does not establish logical dependencies,
eligibility fulfillment, landed mappings, semantic correctness or full inventory.
A current matching code version is necessary but does not erase source errors.

Owner PR head/ref/base/membership must match native observations. Available
immutable tree and ordered parent metadata must also match. When Main carries
complete metadata, supply `OwnerBindings.main_version` with its exact
`head`, `tree`, and ordered `parents`. Missing, contradictory, stale or future
scope binding never writes the journal or sends. Actual supplied violations
remain visible on rejected owner scopes without claiming their binding qualified.
Independent fresh qualified scopes may retain actionable violations despite
missing or partial unrelated collector data. The overall result stays UNKNOWN
where unresolved coverage remains.

`readonly_metadata` in `git_probe_adapter` reads explicitly named local refs and
commits from a normal readonly Git database, including packed objects. It brackets
reads with ref CAS, disables hooks/fsmonitor/network/lazy fetch/replacements and
never executes product code. It proves metadata only. The older synthetic
`GitProbe` loose-object backend remains for its controlled merge regressions;
it is not a source-access policy or a restriction on normal RFQ Git reads.

Runtime accepts published-but-unconfirmed journal updates as INDETERMINATE.
The CLI returns4 for that result and preserves structured persistence, actual
rows, notices and violations. Reopened replay has UNVERIFIED_AFTER_REOPEN
persistence, is receipt-only and stays INDETERMINATE in the adapter; it never
resends. Explicit owner `recover`/`confirm_durability(expected_state_digest)`
confirms the exact current state without rewrite/send. No sender runs before a
durably confirmed AMBIGUOUS marker. The core's historical CLI0/3 retains its
receipt semantics; it is not proof of current durability after reopen.

Historical results remain: original113 had107 passes plus6 missing-fixture
harness errors, followed by6 corrected successes; 60883 joint148 had147 passes
and1 obsolete missing-input expectation. That single expectation now asserts
UNKNOWN and independently asserts retained known violations, actual cloud-demo
notice and plan problem (R2 contract). Two unknown-carrier tests now assert
ignored irrelevant fields with no content leakage, as required by the direct
user source-access override. Native packet structural-schema and consumed-field
checks are retained. New boundary controls cover tree/parents/Main contradictions,
positive binding, stale/future/version no-write behavior and actual producer shape.
No historical run is relabeled green.

Queue acceptance, ack-notice, model arrival and model reply are distinct. Live
30second delivery requires the actual Branch model's timely normal-queue reply.
The earlier Work9698/notice9734 ambiguity and FAIL_NOT_WORKING stay historical;
never replay that notice. A controlled test uses the actual sender session and
one preannounced clearly labelled violation, without role borrowing or a listener.
