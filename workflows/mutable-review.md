---
workflow:
  id: mutable-review
workflow_dispatch_contract:
  orchestrator: "explicitly selected public adapter CLI via workflows/mutable-review.py"
  inputs:
    - "absolute trusted adapter CLI and its current command/configuration contract"
    - "actual purpose, why, actors, environment, access, decision authority, owner/collector and private run destination"
  expectations:
    - "read back delivered provider and linked adapter sources before explicit selection"
    - "preserve adapter-owned execution, inspection, recovery and disposition semantics"
  outputs:
    - "private adapter/provider run records, original evidence and execution disposition"
  non_goals:
    - "no default migration, semantic policy copy, engine, live efficacy claim or merge authority"
---
# Optional script-first mutable review

This is a **caller-selected entry**, not the protected-change default. It needs no
resident root agent: the selected controller asks for judgment on demand. An actual
accepting caller still owns answers, effects, verification and delivery. Installation
alone grants no agent execution or external effects. Manual/standalone paths and
historical runs retain their selected procedures; the [manual routing layer](../AGENTS.md)
is unchanged.

## Read back before selection

Discover the deployed provider at `~/ai/tools/mutable-workflow` and the CRW owner
at `/home/nes/projects/code-review-workflows/trunk`. Read the actual selected
provider's [README](../tools/mutable-workflow/README.md),
[agent contract](../tools/mutable-workflow/agent-adapter.md), and
[inspection contract](../tools/mutable-workflow/inspection.md), then CRW's
`README.md`, `AGENTS.md`, and
`risk-axis-reviewers/workflows/corrected-cohort/{README.md,submission.md,inspection.md,cli.py,provider.py}`.
Follow their role/method links; CRW alone owns semantics. Confirm the delivered
provider exposes `cli.py`, `agent_cli.py`, `inspection_cli.py` and the public
operations used by that adapter. Record actual source locations/readback and
conditions with the caller's existing notes **before starting**. Missing or changed
interfaces reopen integration conclusions; stop affected execution rather than
substituting a guessed CLI or old evidence. No fetch, deployment or automatic
compatibility attestation is performed by this launcher.

The currently composed CRW entry explicitly selects **`perspective-lives-v1`**.
Its directory name does not make it the manual domain-pass corrected cohort.
Neither fake execution nor availability satisfies the general protected-change
review lifecycle. CRW owns its selection and retirement rules; this file does not
reproduce them. A different adapter requires its own authority and readback.

## Invocation

Python 3.10+, POSIX, local private storage and the provider's dependencies (including
PyYAML) are required. Use the installed `~/ai` path after authorized deployment, or
explicitly select an isolated candidate path for fake verification. No installation
step, daemon, routing override or default-selection mutation is needed.

```sh
ENTRY="$HOME/ai/workflows/mutable-review.py"
ADAPTER=/home/nes/projects/code-review-workflows/trunk/risk-axis-reviewers/workflows/corrected-cohort/cli.py
python "$ENTRY" --adapter "$ADAPTER" -- --help
python "$ENTRY" --adapter "$ADAPTER" -- start /private/review --file /private/config.json
python "$ENTRY" --adapter "$ADAPTER" -- drive /private/review
python "$ENTRY" --adapter "$ADAPTER" -- summary /private/review
python "$ENTRY" --adapter "$ADAPTER" -- inspect /private/review
```

`/private/...` are caller-resolved placeholders, not created directories. Construct
config from the **current CRW README**, not a second schema here. Explicitly supply
selection, actual provider path, trusted runner argv, applicable capture contract
with real secret declarations, project/access, purpose/why/question/material,
actors/environment, actual accepting owner/collector, obligations and bounded
Decide authority. The private run directory is the collecting artifact destination;
`owner` names the responsible recipient, not a delivery service. Confirm recipient
access. Choose child, graph-edit and activation grants explicitly; registered worker
argv executes with inherited process privileges. This is not a sandbox.

`start` invokes no semantic role. `drive` may invoke the selected runner. Real
invocation requires separately granted authority and compatible
[runtime dispatch instructions](agents-cli.md#purpose-built-workflow-runtime-dispatch).
Do not use it to evade parent-visible delegation restrictions. The launcher only
execs the trusted adapter CLI with unchanged arguments/output/exit/signal handling;
it does not itself dispatch an agent, supply prompts or import private storage.

## Inspect, reconcile, continue

Use `inspect` for original state/evidence references and `summary` for compact
status. Use adapter `record --revision N` for original source revisions, and the
public provider evidence/owner/show/collect commands returned by those interfaces.
These contain private metadata and potentially sensitive evidence; do not publish
them blindly. Changed source rosters require the owner's explicit full rebaseline,
not dropping old suffixes. Publication lag does not imply lost original evidence.

For a returned question, the accepting caller can invoke `drive --answer 'actual
bounded answer'`. After an interruption, invoke a fresh `drive` against the same
run: the adapter owns exact historical collection and current-material continuation.
For an **actual material change**, `interrupt --file ...` records the caller's
reconciled decision context under CRW's contract; it is not a process-kill claim.
`act`, `amend`, `retry-unsubmitted` and all other operations retain their current
owner contracts and authority requirements. No automatic retry/repair is added.
An authorized edit changes execution intent, not original evidence or obligations.

Unknown provider keys and finite-owner loss before complete capture can remain
blocked. Preserve the original request, answer, diagnostics and named owner;
unknown is not `not_submitted`. Do not launch obsolete intent, invent a new key,
edit private tables or infer recovery from a successful trace. Controller loss,
owner loss and host/storage loss are different conditions. Historical unsupported
runs are not silently migrated.

The adapter's exit codes and payloads pass through unchanged: currently CRW uses
0 for initialization/inspection/progress/qualification, 4 for blocked/pending/
departed, and 5 for not-confirmed errors. Read the payload. Alternate graph success
can coexist with unfulfilled original policy. Qualified no-Act is not all-retired,
consumer acceptance, delivery completion or permission to merge. Root retains the
normal consequence review and final disposition.

## Evidence and limits

`tests/test_mutable_review_entry.py` invokes this actual selected file through
Python, starts through the public CLI (no imported initializer), and uses the
CRW-owned fake runner. It covers historical question/material interruption and
same-conversation continuation, actual Frame/Decide inputs with exact evidence text
and basis, authorized executable graph departure with an independent local effect,
and original retained records/final execution disposition. Negative controls cover
missing selection and rejected submissions. Tests never run `agents` or a model.

```sh
PYTHONDONTWRITEBYTECODE=1 python -m pytest -q -p no:cacheprovider tests/test_mutable_review_entry.py
```

`CRW_CHECKOUT` can explicitly select a compatible CRW test checkout (default: the
owner path above); `MUTABLE_WORKFLOW_PROVIDER` selects the shared provider
(default: `/home/nes/ai/tools/mutable-workflow`). Absent fixtures fail visibly.
Fake command stdout/stderr and exit records stay in pytest temporary storage.
Candidate selection is not deployment.
Tests establish bounded mechanical behavior, not reviewer judgment quality/recall,
real-runner compatibility, arbitrary-effect exactly-once, unknown-key repair,
host/power/storage survival, hostile multi-principal protection, production scale
or SLA. All source/return history grows locally. Live evaluation and default
adoption require separate decisions and authority.
