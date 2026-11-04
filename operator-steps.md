Contribution-only operator steps; execute only after the outside adoption decision. See Decision25/25B for prior obligations and SAFE-HANDOFF.md for the unintended shared-counter effect.

1. Adopt matching files from code cb1130202af5a1949acc805a29ec6d556fce4b60 in the established isolated-source integration path, together with separately admitted Source22/23 as applicable. Keep tools/coordinator-runtime, tools/direct-child/execution_pool.py, dispatch.py and tools/direct-codex-child/launch.sh in their sibling layout. This Act has not installed/restarted/adopted anything. Existing config bytes/grants need no change when profiles authorization covers 2/3/5. Existing original calls retain handles/custody; never move their stores or replay accepted/unknown tasks.

2. Set POOL_TOOL to the adopted pool module and ROUTES to the existing public central control, not a private profile file:

    POOL_TOOL=/absolute/adopted-checkout/tools/direct-child/execution_pool.py
    ROUTES=/home/nes/ai/tools/direct-child/routes.toml
    python3 "$POOL_TOOL" --routes "$ROUTES" status

Status reports enabled membership, routes hash, next unreserved turn/profile and availability:not-probed. It can initialize fresh public counter/control files but does not advance a turn or inspect account stores. A missing/invalid control or malformed/empty-existing counter is held; do not reset it to manufacture eligibility.

3. The supported cooperative operator update is:

    python3 "$POOL_TOOL" --routes "$ROUTES" set .codex2 .codex3 .codex5
    python3 "$POOL_TOOL" --routes "$ROUTES" status

This changes only providers.codex.pool. To disable all NEW automatic execution, use set with no names. Changing membership preserves the counter; order determines rotation. Updates return the effective membership/source hash and next unreserved turn. Serial cooperating updates apply in lock order. If a write/fsync fails after replace, inspect current status before another operation; a held error does not prove the replacement had no effect. No task replay follows an update failure.

4. Runtime inspection uses the existing config without migrating role identities:

    python3 /absolute/adopted-checkout/tools/coordinator-runtime/coordinator --config /absolute/existing/config.json execution-pool
    python3 /absolute/adopted-checkout/tools/coordinator-runtime/coordinator --config /absolute/existing/config.json status

Default runtime routes are ~/ai/tools/direct-child/routes.toml. An explicit execution_pool_routes field is for isolated/custom controls; adding/changing it changes the bound config digest and requires existing offline config reconciliation. It is not a live config toggle. A pool exceeding account authorization needs an explicit compatibility decision; no silent intersection/authorization expansion occurs.

5. Parent automatic workers use adopted dispatch.py with --config "$ROUTES" and omit --profile. To preserve an earlier suggestion, pass --profile-advice .codex3. It records advice while ordinary rotation chooses the new account. Standalone --profile NAME --override-reason TEXT remains manual authorization outside automatic controls. Global enforcement of that path was not selected.

6. Check attempts.detail.execution_pool_allocation and execution_pool_admission, or parent route.json and pool-admission.json, for actual choice and boundary. Runtime admission holds the cooperative lock through process creation/BEGIN; direct admission is after preflight at codex exec; native admission is local caller creation. Updates waiting behind an admission do not revoke that accepted call. A disabled reserved attempt remains unstarted on its original profile, with visible error; no automatic reassignment. Empty/invalid/unavailable choices never borrow/fallback. A job with no attempt can retry allocation under its original controller.

7. Stable-pool reservation fairness survives restart, including singleton pools. Failed/aborted reservations consume turns. Existing counter/lock inodes and rotation.state_dir must remain stable during callers; relocation/reset requires separate reconciled cutover. Older/manual writers and other machines are outside the full protocol. No equal-token/completion, capacity-health, provider revocation, noncooperating CAS or cross-file/power-loss atomicity claim. Collect independent consequences/Frame/Work before any live adoption; no service command or cleanup is selected here.
