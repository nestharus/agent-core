# Follow-Up Tickets Example

This is a canonical illustrative example, not live runtime evidence. It demonstrates remediation ticket payloads the workflow may file after findings synthesis.

## ACR-201 - Pin resume cwd precedence

Type: follow-up ticket. Source findings: `RI-AGE-CWD-001`, `RI-AGE-CWD-002`.

Problem: resume and dispatch code can disagree about effective cwd after handoff. Expected outcome: a single documented cwd precedence helper and targeted regression coverage.

Acceptance:

- One helper owns cwd precedence for launch and resume.
- Resume noninteractive dispatch has a regression test for effective cwd.
- Documentation names the selected precedence rule.

## ACR-202 - Deduplicate resume path fixtures

Type: remediation ticket. Source finding: `RI-AGE-CWD-003`.

Problem: resume tests repeat path setup without a shared assertion for effective cwd. Expected outcome: shared fixture plus one explicit cwd assertion per resume path.
