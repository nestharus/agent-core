# Explicit Work observation correction

`qa-observation-correction-basis` and `amend-qa-observation` correct an
accountable Work attribution before its exact admitted QA package starts.
They do not change admission, policy selection, source authority, native QA
authorship, Root acceptance, grants, allocation charges, expiry or old custody.

The original whole resource account stays in the capability's selection. One
immutable amendment per capability/package supplies a new whole statement,
its digest and `relevant_roots`. Execution and cleanup resolve that same
amendment. Positive relevant-root overlap continues to block the operation.
An empty relevant set is testimony by the genuine Work owner, never a runtime
discovery, physical census or discharge of the old unbounded UNKNOWN.

The caller must be the current Work owner in the authenticated process
`CODEX_SESSION_ID` and pass the existing original grant checks. There is no
actor option. Do not synthesize this identity in an operational invocation.
The service must have stopped cooperatively, with the SAME original parent's
numeric END recorded by `processing-release` and all owned attempts collected.
Any reserved job, package owner, ordinary intent or lease prevents a new
amendment. Existing started jobs retain their frozen resources.

These are fictional operands, never actual rollout commands:

```sh
python3 -m coordinator_runtime --config /fiction/owned/config.json \
  qa-observation-correction-basis FICTION-CAP FICTION-EVENT \
  --controller FICTION-ORIGINAL-CONTROLLER
```

Genuine Work must review the returned basis and supply its own current truth,
rationale, evidence and remaining positive relevant roots. The receipt shape is:

```json
{
  "basis": {"use": "the exact whole returned fictional basis"},
  "authority": "Current Work's explicit correction and rationale",
  "evidence": ["Current independently supported owner observation"],
  "statement": {
    "attribution": "New Work observation, not native QA authorship",
    "remaining_unknown": "Old whole account and logical QA custody retained",
    "relevant_fact": "The owner supplies the actual finite facts here"
  },
  "statement_sha256": "digest(statement), using contracts.digest",
  "relevant_roots": ["/fiction/actual-remaining-held-root"]
}
```

The schematic basis and digest above are deliberately not executable receipts.
After preparing a complete owner-supplied fictional receipt, the corresponding
fictional application would be:

```sh
python3 -m coordinator_runtime --config /fiction/owned/config.json \
  amend-qa-observation FICTION-CAP --receipt /fiction/owned/correction.json
```

Application takes the cooperative stopped-service lock and one journal write
transaction, recomputes the exact basis and compares mutation revision tokens.
Changed source/hash/mapping, admission, Root association, configuration, grants,
policy, expiry or any other intervening cooperative journal mutation requires
a fresh basis. Only statement, statement hash and relevant roots are overlaid;
extra policy/scope/source/reference/cleanup/expiry fields are refused. Repeating
the identical committed receipt returns its receipt without another write or
charge; a different second amendment is refused.

The metadata insertion uses bounded allocated journal pages and receipt bytes;
it does not inventory old captures. Ordinary source, reservation, execution,
acceptance, cleanup, total storage and expiry checks remain independently owed.
This is cooperative local transaction protection, not hostile-writer CAS or
cross-store atomicity. Failed/partial effects remain with their original owner.
