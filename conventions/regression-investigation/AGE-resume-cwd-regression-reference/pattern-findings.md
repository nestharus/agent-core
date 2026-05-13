# Pattern Findings Example

This is a canonical illustrative example, not live runtime evidence. It demonstrates per-file pattern findings expected from `pattern-auditor`.

## PF-001

Surface: `agent_runner/session_resume.py`. Risk category: unwritten invariant. Severity: HIGH. The resumed process assumes the stored cwd is authoritative but does not spell out whether it is the original worktree, launch directory, or last command directory.

## PF-002

Surface: `agent_runner/dispatch.py`. Risk category: implicit coupling. Severity: MEDIUM. Dispatch code and session restore code both shape cwd behavior, but the contract is not centralized.

## PF-003

Surface: `agent_runner/providers/codex.py`. Risk category: provider-name hardcoding. Severity: LOW. Provider-specific paths are mentioned in examples and should stay out of cwd policy.

## PF-004

Surface: `agent_runner/tests/test_resume.py`. Risk category: duplication. Severity: MEDIUM. Resume fixtures repeat path setup without a shared assertion for the effective cwd.
