# No operator behavior override in dispatch

## Declared roles

`orchestration`, `validator`.

This file-local declaration reflects ownership of dispatcher read order and validation of caller prompt boundaries.

## Rule

Caller dispatch prompts MAY provide contract-shaped inputs from the operator's `## Contract` `inputs:` field set and evidence paths. Caller dispatch prompts MAY NOT override or replace the operator's procedure, verdict handling, error envelope, or any field outside the contract `inputs:`.

## Dispatcher read-protocol meta-rule

Orchestrators MUST resolve the relevant structured spec before asking session metadata or the user for any input named by the contract: read the project-wrapper optimized sidecar when execution is in a project scope with a current wrapper, otherwise read the base operator sidecar; if a sidecar is missing, fall back to that file's `## Contract` block. Wrapper defaults apply before base defaults, and unresolved required inputs become `BLOCKED:missing-required-input` or `NEEDS_INPUT:<artifact>`. This paragraph is the canonical authority future DP-013 entries reference for project wrapper and base operator contract resolution.

## What dispatch prompts may contain

- Contract `inputs:` values.
- Evidence paths and artifact paths.
- Prompt-side guidance about what to verify, what scope applies, and what evidence must be read.

## What dispatch prompts must not contain

- Copied operator procedure text.
- Alternative verdict thresholds.
- Alternative error envelopes.
- Mocks or stubs that bypass the operator's contract.
- Instructions to skip operator validations.

## See also

- `agents/operator-file-format.md`
- `conventions/bootstrap-pattern.md`
- `workflows/agents-cli.md`
