# No Deferred Stubs

Implement fully, or document what's blocking.
Do not leave placeholder stubs, TODOs, or
"will finish later" code in the repo.

## Forbidden

- `def foo():  # TODO: implement` — empty stubs waiting for "later"
- `raise NotImplementedError` as a placeholder with no caller-facing reason
- Comments like `# will finish in next PR` with no enforcing reference
- Functions that return `None`, `{}`, or `[]` as a stand-in for real output
- Empty test bodies with `pass` and no marker
- Frontend components that render `null` pending "real design"

These are forbidden even when the author believes the real
implementation will land "soon". Unscheduled later work is not a plan.

## Authorized deferral

A deferral is authorized only when the implementation plan
explicitly marks the item as scheduled for a later task.
This is the only exception.

If you authorize a deferral:

- **Name the follow-up work unit.**
  Inline comment: `# deferred to WU-042`
  or the project's ticket format.
  The comment is a promise that a real scheduled work item exists.
- **Raise an explicit error on use, not a silent stub.**
  `raise DeferredFeatureError("foo() is scheduled for WU-042; not available until then")`
  beats `return None`.
- **Test the deferred stub as deferred.**
  Assert that calling it raises the expected error,
  so removing the stub later breaks the test
  and forces follow-up.

An unreferenced `TODO` is not an authorized deferral. It is a stub.
An empty placeholder comment in a PR description is not authorization.

## Incomplete-work reporting

If you cannot finish the current task because of credentials,
unclear requirements, missing upstream work, or another blocker,
do not ship partial stubs. Report:

- **What was completed** — file paths, symbol names, test coverage
- **What is blocking** — the specific thing that prevented completion
- **What the blocker requires** — credentials, human decision, upstream PR, external service
- **What the incomplete state looks like in the repo** — branch names, uncommitted changes, failing tests
- **Whether the current branch is safe to merge** — usually "no"

The report goes in the PR body,
or in the handoff document if no PR is open.
A future reader must be able to resume without guessing
what was in progress.

## Rationale

Stubs rot because "I'll finish this later"
does not survive context switches.
A stub today becomes a silent bug when a caller reaches it
and gets `None` back.
An explicit error or an authorized scheduled deferral
keeps the cost visible at review time.

## Relation to No Backwards Compatibility

The two rules have the same shape: do not let unfinished or outdated code live silently. See `~/ai/conventions/no-backwards-compatibility.md`.
