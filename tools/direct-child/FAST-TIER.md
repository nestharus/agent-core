# Temporary fast-tier policy

The adjacent `fast-tier` file is the single switch for new Codex launches through
`dispatch.py`, `direct-codex-child/launch.sh`, and the prospective coordinator
AppServer source path. It is enabled (`true`) now. This is a service-tier request;
model, reasoning effort, profile selection and launch protections retain their
selected values. Existing in-flight processes keep their original settings.

From this directory, turn it off or back on with:

```bash
python3 fast_tier.py set off
python3 fast_tier.py set on
python3 fast_tier.py get
```

The setter atomically replaces the public switch. Disabled policy sends no tier
or fast-mode override and restores the prior transport/profile tier semantics;
it does not force standard tier if a profile independently requests something
else. Missing, linked or invalid policy refuses before provider startup. The
internal `--expected-fast-policy` launcher argument checks the dispatch snapshot,
so a changed policy cannot silently produce a contradictory attempt record.

Enabled direct CLI launches add `-c features.fast_mode=true` and
`-c 'service_tier="fast"'` to the actual `codex exec` argv. The dispatcher selects
the direct transport before any allocation for new automatic Codex launches,
recording `user-fast-tier-policy-direct`: the declared native caller accepts only
a registered route and has no per-request tier override. Explicit incompatible
`--transport native` and native deadlines refuse before effects. No native
attempt is followed by a fallback or replay. Disabling this policy restores the
previous native/direct selection rules without changing site registrations.

Dry runs, route records and direct attempt state distinguish `force_fast`,
`requested_service_tier` and `served_service_tier=unobserved`. Fast availability
and the actual served tier depend on the backend; argv is request evidence only.
The policy does not interpret opaque model selectors or attest their identity.
Other providers retain their original route/model/effort and report
`fast_tier_support=not-established-for-provider`; no Claude tier flag is invented.

The prospective coordinator AppServer contribution is source only until its
owner separately installs/selects it. Its command snapshots the same policy,
adds the same generic CLI configuration overrides at app-server startup, and
carries `service_tier` and `features.fast_mode` through the supported thread/start
`config` map. Subsequent turns inherit that thread configuration. No invented
turn parameter or change to eligibility/admission is required. Its attempt facts
record the requested tier, with served tier unobserved. Changing the switch does
not reconfigure existing owned peers or their continuation turns.

Official OpenAI documentation:
[Fast mode](https://learn.chatgpt.com/docs/agent-configuration/speed#fast-mode)
and [App Server](https://learn.chatgpt.com/docs/app-server). These establish the
public request/configuration interface, not universal account availability or a
live provider result. Focused fake-CLI and protocol-peer tests exercise actual
argv, route decisions, invalid settings, on/off, protection preservation, and
single-attempt failure behavior without provider calls.

The final coordinator source uses the explicit controller binding and frozen v4 dependency contract in `../coordinator-runtime/shared-fast-control.md`. It always supplies the selected shared control path to this helper; adjacent flags in other checkouts do not control that path. This source representation is inert until genuinely selected and installed under actual authority.
