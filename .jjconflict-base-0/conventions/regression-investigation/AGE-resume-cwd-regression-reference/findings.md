# Findings Example

This is a canonical illustrative example, not live runtime evidence. It is the Markdown synthesis matching `findings.json` for `AGE-resume-cwd-regression`.

## RI-AGE-CWD-001

Severity: HIGH. Surface: `agent_runner/session_resume.py`. The key gap is an unwritten invariant: resume code needs one cwd precedence rule, but the example incident shows different readers could assume different roots. Suggested remediation is a documented and enforced cwd precedence rule.

## RI-AGE-CWD-002

Severity: MEDIUM. Surface: `agent_runner/dispatch.py`. Dispatch and restore code implicitly couple around cwd behavior. Suggested remediation is a shared cwd resolution helper with tests for launch, resume, and prompt-file dispatch.

## RI-AGE-CWD-003

Severity: MEDIUM. Surface: `agent_runner/tests/test_resume.py`. Test accompaniment is too thin for the effective cwd contract. Suggested remediation is a targeted regression fixture for resumed noninteractive dispatch.

The example intentionally names every finding id from `findings.json` while staying canonical illustrative and not live.
