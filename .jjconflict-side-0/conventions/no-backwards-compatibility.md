# No Backwards Compatibility

When updating code, ship the change cleanly.
Do not introduce backwards-compatibility shims,
feature flags for old behavior, transitional code paths,
deprecated aliases, re-exports, or dual support.

Temporary compatibility is still compatibility.
Do not check in code that exists only to ease the transition
from the old shape to the new one.

## Forbidden patterns

- **Deprecated aliases** — `old_name = new_name  # For backwards compatibility`
- **Version-gated branching** — `if version < 2: use_old_method()`
- **Dual implementations** — old function kept alongside new one "just in case"
- **Feature flags for old behavior** — `if os.getenv("USE_OLD_AUTH"): ...`
- **Re-exports of moved symbols** — `from new_module import X as Y; Y = X  # was in old_module`
- **Transitional adapter layers** — code that translates between old and new data shapes purely for compatibility
- **Renamed `_unused` variables, parameters, or fields** — delete them
- **"Removed" comments** — `# removed in v3` placeholders with no function

If the only reason a branch, parameter, helper, or import exists
is "some callers have not migrated yet", it is forbidden.

## The migration protocol

When you change a function, class, data shape, or API:

1. **Find all usages** — grep, static analysis,
   call-site enumeration.
2. **Update all call sites** — every single one.
   If you can't update one, the migration is not done.
   Do not ship partial.
3. **Delete the old code** — no alias, no re-export,
   no comment placeholder.
4. **Run tests** — the migration is incomplete until
   all tests pass against the new shape.
5. **No fallbacks** — if the new code fails, fix the
   new code. Do not add a "use old if new fails" branch.

If a migration cannot be completed in one change because of scope,
it is not a migration. It is a rewrite that needs its own pipeline run.
Do not leave the codebase in a mid-migration state.

## Enforcement

- PR review gates flag partial migrations.
  See `~/ai/workflows/pr-review.md`.
- Grep-invariant tests catch reintroduction:
  `test_no_<legacy_symbol>_remains()` walks repo files
  and asserts the forbidden substring is absent.
- Projects can add project-specific legacy-symbol invariants as regression tests.

## Rationale

Each forbidden pattern trades short-term compatibility
for long-term rot.
Deprecated aliases get used.
Feature flags get copied into new code.
Dual implementations diverge.

The cost of never having backwards compatibility is paid once,
at migration time, when the full context is available.
The cost of keeping backwards compatibility is paid by every
future reader who has to distinguish live code from vestigial code.

Ship clean changes. Delete old code.
