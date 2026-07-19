# AGE-resume-cwd-regression Incident Context

This is a canonical illustrative example, not live runtime evidence and not a forensic capture. It demonstrates the incident-context artifact shape expected from `regression-investigation`.

Incident id: `AGE-resume-cwd-regression`.

Context: agent-runner PR #78 and PR #79 are used as public reference handles for a resume-current-working-directory regression. The useful shape is that resumed agent work could continue from an unexpected directory after handoff, so later commands read or wrote relative paths against the wrong project root.

Known surfaces for the example:

- resume session restoration path.
- cwd resolution during noninteractive `agents -m ... -f ...` dispatch.
- worktree isolation assumptions around central checkout versus WU worktree.

The example should seed commit-history, pattern-audit, and findings artifacts without claiming that the workflow ran live against agent-runner.
