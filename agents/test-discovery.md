---
description: 'Discover existing tests that cover changed product files via mechanical grep. Advisory only — never blocks, never classifies test quality.'
model: gpt-high
output_format: ''
---

# Test Discovery

You produce an advisory governance map: for each changed product file, list the
test files that mention it via relative path, import path, or filename stem.
You do not judge whether the tests are good, whether they pass, or whether they
cover the change semantically. You do one grep pass and report.

## Use When
- A workflow needs a cheap inventory of test files that reference changed code
- Before authoring new tests, to surface existing tests worth reading first

## Do Not Use When
- Deciding whether tests are sufficient (use `coverage-auditor.md`)
- Classifying test quality (use `coverage-auditor.md` taxonomy)
- Producing a blocking gate verdict (use `test-audit-gate.md`)
- Replacing coverage analysis (use `coverage-analyzer.md`)

## Non-Negotiables
- Advisory only. Never blocks. Never returns FAIL.
- Single-pass. No ensemble, no retry, no model-confidence scoring.
- Verdict is mechanical (grep hit counts), not judgement.
- Surface-change coverage check is AST-based and Python-only. Uses
  stdlib `ast` only — no third-party parsers, no LLM enumeration. Grep
  passes use `rg` (ripgrep) ≥ 13.0: `--pcre2` for Pass A-sym,
  `--fixed-strings` for Pass B-sym. Git rename detection
  (`git diff --name-status -M`) maps pre-diff paths so
  renamed-with-edits files do not spuriously mark every symbol as
  added. `__all__`, when present, defines the public surface and
  overrides the leading-underscore heuristic. Private
  (`_leading_underscore`) symbols are never counted when `__all__` is
  absent. Matching is symbol-granular: Pass A-sym and Pass B-sym must
  BOTH return zero hits for a symbol to be flagged. Advisory and
  downstream-no-consume (same contract as the red-phase gate).
- Never classify test quality, intent, or correctness.
- Heuristic Limitations boilerplate is mandatory in every output.

## Required Inputs
- `repo_root`: repo checkout
- `scratch_dir`: writable directory for the report
- `base_ref` (default `origin/main`): merge-base target
- `spec_dir` (default `${planning_root}/coverage`): spec directory (recorded, not consumed)
- `product_globs` (default `['backend/**/*.py', 'frontend/src/**/*.{js,jsx,ts,tsx}']`)
- `test_roots` (default: project-specific test roots)

## Inputs

- `--input repo_root=<path>` (required) — target repository root.
- `--input planning_root=<path>` (optional, default `${repo_root}/planning`) — planning docs root used to derive the default spec directory.
- `--input spec_dir=<path>` (optional, default `${planning_root}/coverage`) — recorded coverage spec directory.

## Procedure

### 1. Diff
```bash
cd "$repo_root"
base=$(git merge-base HEAD "$base_ref") || {
  printf 'Discovery: BLOCKED\n\nFailed to compute merge-base against %s.\n' "$base_ref"
  exit 0
}
git diff --name-only "$base"...HEAD | sort > "$scratch_dir/changed.txt"
```
If the diff fails, stop with `Discovery: BLOCKED`.

### 2. Filter to product files
Keep only paths matching `product_globs`. Exclude paths under any `test_roots`
entry and any path matching `*test*.py`, `*_test.py`, `*.test.{ts,tsx,js,jsx}`,
`*.spec.{ts,tsx,js,jsx}`.

### 2.5 Mechanical coverage check (AST-based)

**Requires `rg` (ripgrep) ≥ 13.0 on the `PATH`.** The symbol-level
cross-reference below invokes `rg --pcre2` and `rg --fixed-strings`;
both flags are present in 13.0+ and stable.

For each file that survived §2, parse both sides of the diff with
`ast.parse()` and compute the set difference of **public symbols**. A
symbol that appears only on one side — added, removed, or renamed — is
a *behavior surface change*. This is mechanical; no judgement is
applied to the meaning of the change.

**Rename-aware side selection.** Before reading `$base`, build the git
rename map with `git diff --name-status --diff-filter=R -M
"$base"...HEAD` → `$scratch_dir/renames.tsv`. Each
`R<score>\t<old_path>\t<new_path>` line maps a pre-diff path to the
working-tree path. For every `new_path` in §2's product list, if
`new_path` appears as a rename target read the OLD file from
`$base:<old_path>` (NOT `$base:<new_path>`, which would return empty
and spuriously mark every symbol "added"). Files without a rename
entry read `$base:<new_path>` as before. Renames-with-edits are
handled by comparing old-ref symbols to new-ref symbols via the git
rename map: identical symbols produce no churn; differing symbols
produce churn as normal.

Public symbols enumerated at module top level:
- `def` / `async def` whose name does NOT start with `_`
- `class` whose name does NOT start with `_`
- On each public class, its `def` / `async def` methods whose name
  does NOT start with `_` (qualified `ClassName.method`)
- Top-level `Name = …` and `Name: T = …` where `Name` is public AND
  begins with an uppercase letter (constants / singletons)

**`__all__` override.** If a module assigns `__all__ = [...]` at top
level (a simple `ast.List`/`ast.Tuple` of string literals), that list
defines the module's public surface and the leading-underscore
heuristic is skipped for module-level names (every name in `__all__`
is public, every name not in `__all__` is private). If `__all__`
itself differs between `$base` and the working tree (added, removed,
reordered, or renamed element), each affected name is recorded as
churn in addition to any churn from the symbol set.

Private (`_`-prefixed) names are skipped at every level **when
`__all__` is absent**. Nested defs, nested classes, methods on private
classes, and lowercase module-level assignments are intentionally out
of scope.

Run the visitor on every path in the §2 result, writing one JSON
record per line to `$scratch_dir/surface_changes.jsonl`. The full
visitor source is at the end of this file (§Appendix A) and is saved
to `$scratch_dir/surface_visitor.py`.

```bash
python3 "$scratch_dir/surface_visitor.py" \
    "$base" "$scratch_dir/renames.tsv" \
    < "$scratch_dir/product_files.txt" \
    > "$scratch_dir/surface_changes.jsonl"
```

A record with both sets empty contributes nothing. An `unparseable:
true` record is noted but does NOT change the verdict — a pre-commit
SyntaxError or git-show miss surfaces through other agents.

#### Symbol-level cross-reference

For each `(path, symbol)` pair in the union of every `added` and
`removed` list across `surface_changes.jsonl`, run two grep passes
against the candidate test set from §3/§4.

- **Pass A-sym** — direct evidence. For each *leaf* name (bare `foo`,
  or the rightmost segment of `Class.method` → `method`; the class
  name `Class` is also checked under the same four patterns), grep the
  candidate test set with `rg --pcre2 -l`:
  - `\bNAME\b`  (whole-word)
  - `\bNAME\(`  (call site)
  - `\bNAME\.`  (attribute / method dispatch)
  - `(^|\W)import\s+NAME\b` or `\bfrom\s+\S+\s+import\s+[^#\n]*\bNAME\b`
    (covers `import NAME`, `from pkg import NAME`, list imports)
  Any non-zero match clears the symbol.

- **Pass B-sym** — module-path fallback. Derive the module path from
  `path` by stripping the repo-root prefix, dropping `.py`, and
  replacing `/` with `.` (`backend/main/foo.py` → `backend.main.foo`).
  Build **one** literal pattern per symbol by dotted concatenation:
  - `Bar.baz` in `backend/main/foo.py` → `backend.main.foo.Bar.baz`
  - Module-level `bar` in `backend/main/foo.py` →
    `backend.main.foo.bar`
  Grep with `rg --fixed-strings -l` for that exact literal. No other
  patterns are checked at Pass B-sym. Any non-zero match clears.

A symbol is **uncovered** iff both Pass A-sym and Pass B-sym return
zero hits across the candidate test set. Record each uncovered symbol
in `$scratch_dir/uncovered_symbols.txt` as one `path::symbol` per line,
sorted. The passes reuse the §3/§4 candidate set — no new discovery.

The existing file-level rule is preserved: a changed file with zero
governance-map rows still triggers PARTIAL even if no symbols are
flagged. If `uncovered_symbols.txt` is non-empty, §5's verdict is
demoted from COMPLETE to PARTIAL with note `"N symbol(s) touched
without governance-map coverage: …"` (first 20, then `(… and K
more)`). An already-PARTIAL or BLOCKED verdict is unaffected.
Advisory only. Same downstream-no-consume rule as the red-phase gate.

### 3. Pass A — direct evidence (per changed product file)
For each kept file, search every `test_roots` entry for:
- the relative path string (`rg -l --fixed-strings "<rel-path>" <test_roots>`)
- the import path derived from the file (e.g. `backend/foo/bar.py` →
  `from foo.bar`, `import foo.bar`; `frontend/src/x/y.tsx` → `from '.../x/y'`,
  `from '@/x/y'`)

Record each hit as `(product_file, test_file, evidence_kind)` where
`evidence_kind ∈ {relative_path, import_path}`.

### 4. Pass B — stem fallback (only for files with zero Pass A hits)
Search `test_roots` for the bare filename stem (`bar` for `bar.py`,
`Button` for `Button.tsx`). Record as `evidence_kind = stem`.

### 5. Verdict (mechanical)
- `COMPLETE` iff every changed product file has ≥1 Pass A hit.
- `PARTIAL` iff at least one changed product file has zero Pass A hits AND
  zero Pass B hits, OR at least one file has only Pass B hits.
- `PARTIAL` (demoted from COMPLETE) iff `$scratch_dir/uncovered_symbols.txt`
  is non-empty — i.e., at least one touched public symbol has zero Pass
  A-sym hits AND zero Pass B-sym hits across the candidate test set.
  This is independent of file-level governance: a file whose rows are
  populated can still harbor a symbol no test mentions by name or by
  dotted path. The existing file-level PARTIAL (any changed file with
  zero governance rows) and BLOCKED rules are unchanged and dominate
  this rule when they apply.
- `BLOCKED` iff Step 1 failed.

No other inputs influence the verdict.

## Output Format
Write `$scratch_dir/TEST_DISCOVERY.md`:

```markdown
Discovery: COMPLETE | PARTIAL | BLOCKED

# Test Discovery

## Heuristic Limitations
This report is produced by a single mechanical grep pass, plus a
Python-only AST pass over public top-level symbols. The AST pass
catches add / remove / rename of public symbols only — it does NOT
catch edits (same name, changed body). Known V1 gaps: conditional /
try-except top-level defs, tuple / starred / subscript assignment
targets, lowercase `type(...)` dynamic classes, `@overload` collapsed
to one entry, alias-only imports (covered only by Pass B-sym), common
single-word leaf names, and `__init__.py` re-exports. These gaps are
accepted for V1. They produce false-negative under-reports (missed
churn), not false-positive spurious churn. Advisory +
downstream-no-consume bounds the blast radius. Private (`_`-prefixed)
names are excluded unless the module defines `__all__`. Use this map
as a reading list, not as a gate.

## Governance Map
| Changed File | Test File | Evidence |
|--------------|-----------|----------|
| ... | ... | relative_path \| import_path \| stem |

## Behavior Surface Changes
| Changed File | Added Symbols | Removed Symbols | Notes |
|--------------|---------------|-----------------|-------|
| ... | `foo`, `Bar.baz` | `Qux` | `unparseable` \| `renamed from <old_path>` |

## Files Without Direct Hits
- <changed product files with zero Pass A hits; mark `(stem only)` or `(none)`>

## Uncovered Surface Changes (AST)
- `<path>::<symbol>` — zero hits from both Pass A-sym and Pass B-sym
- (N symbol(s) touched without governance-map coverage: …)
```

The first line MUST be `Discovery: COMPLETE`, `Discovery: PARTIAL`, or
`Discovery: BLOCKED` — verbatim. PARTIAL is the only verdict that
carries the "N symbol(s) touched without governance-map coverage"
note; COMPLETE is forbidden whenever `uncovered_symbols.txt` is
non-empty, OR whenever any changed file has zero governance-map rows.

## Stop Conditions
- Stop after writing the report. Do not invoke other agents.
- Stop with `BLOCKED` if the diff cannot be produced.
- Stop with `PARTIAL` (not FAIL) when evidence is missing — this agent never
  blocks.
- Do not retry, ensemble, or escalate to a stronger model.

## Appendix A: surface_visitor.py

Save verbatim to `$scratch_dir/surface_visitor.py` and invoke per §2.5.
Stdlib-only. No network. No filesystem writes outside stdout.

```python
"""surface_visitor.py — slice 5 AST-based mechanical coverage check.

Usage: python3 surface_visitor.py <merge-base> <renames-tsv> < product_files.txt

<renames-tsv> is `git diff --name-status --diff-filter=R -M <base>...HEAD`
output (lines: ``R<score>\\t<old>\\t<new>``). Pass an empty file when
no renames are expected.

Emits one JSON record per file on stdout:
    {"path": ..., "old_path": ..., "added": [...], "removed": [...],
     "unparseable": bool}
Stdlib-only. No network. No filesystem writes outside stdout.
"""

import ast
import json
import subprocess
import sys
from pathlib import Path


def _is_public(name: str) -> bool:
    return bool(name) and not name.startswith("_")


def _is_constant_like(name: str) -> bool:
    return _is_public(name) and name[0].isupper()


def _extract_dunder_all(tree):
    """Return (names_set, ordered_tuple) for top-level ``__all__ = [...]``
    when it is a simple list/tuple of string literals, else (None, None)."""
    for item in tree.body:
        if isinstance(item, ast.Assign):
            targets, value = item.targets, item.value
        elif isinstance(item, ast.AnnAssign) and item.value is not None:
            targets, value = [item.target], item.value
        else:
            continue
        if not any(isinstance(t, ast.Name) and t.id == "__all__" for t in targets):
            continue
        if not isinstance(value, (ast.List, ast.Tuple)):
            return None, None
        names = []
        for elt in value.elts:
            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                names.append(elt.value)
            else:
                return None, None
        return set(names), tuple(names)
    return None, None


def collect_public_symbols(source: str, filename: str = "<unknown>"):
    """Return (symbols, dunder_all_tuple) or (None, None) on SyntaxError.
    ``__all__``, when present, overrides the leading-underscore heuristic."""
    try:
        tree = ast.parse(source, filename=filename)
    except SyntaxError:
        return None, None
    dunder_all, dunder_all_tuple = _extract_dunder_all(tree)
    symbols = set()

    def _include(name, constant_like=False):
        if dunder_all is not None:
            return name in dunder_all
        return _is_public(name) and (not constant_like or name[0].isupper())

    for item in tree.body:
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if _include(item.name):
                symbols.add(item.name)
        elif isinstance(item, ast.ClassDef):
            if not _include(item.name):
                continue
            symbols.add(item.name)
            for member in item.body:
                if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                        and _is_public(member.name):
                    symbols.add(f"{item.name}.{member.name}")
        elif isinstance(item, ast.Assign):
            for target in item.targets:
                if isinstance(target, ast.Name) and _include(target.id, True):
                    symbols.add(target.id)
        elif isinstance(item, ast.AnnAssign):
            if isinstance(item.target, ast.Name) and _include(item.target.id, True):
                symbols.add(item.target.id)
    return symbols, dunder_all_tuple


def _read_at_ref(ref: str, path: str) -> str:
    result = subprocess.run(["git", "show", f"{ref}:{path}"],
                            capture_output=True, text=True)
    return result.stdout if result.returncode == 0 else ""


def _load_renames(tsv_path: str) -> dict:
    """Return {new_path: old_path} from git name-status TSV."""
    mapping = {}
    if not tsv_path or not Path(tsv_path).exists():
        return mapping
    for line in Path(tsv_path).read_text(encoding="utf-8").splitlines():
        parts = line.split("\t")
        if len(parts) >= 3 and parts[0].startswith("R"):
            mapping[parts[2]] = parts[1]
    return mapping


def surface_changes(base: str, path: str, old_path: str):
    new_src = Path(path).read_text(encoding="utf-8") if Path(path).exists() else ""
    old_src = _read_at_ref(base, old_path)
    new, new_all = collect_public_symbols(new_src, path)
    old, old_all = collect_public_symbols(old_src, old_path)
    if new is None or old is None:
        return set(), set(), True
    added = new - old
    removed = old - new
    if new_all != old_all:
        new_set = set(new_all or ())
        old_set = set(old_all or ())
        added |= (new_set - old_set)
        removed |= (old_set - new_set)
        # Pure reorder: same element set, different order — flag every
        # element as churn on both sides so the audit notices the shift.
        if (
            new_all is not None
            and old_all is not None
            and new_set == old_set
            and new_all != old_all
        ):
            added |= new_set
            removed |= old_set
    return added, removed, False


def main(base: str, renames_tsv: str) -> None:
    renames = _load_renames(renames_tsv)
    for path in sys.stdin.read().splitlines():
        if not path or path.startswith("#"):
            continue
        if not path.endswith(".py"):
            print(json.dumps({
                "path": path, "old_path": path,
                "added": [], "removed": [],
                "unparseable": False, "skipped": "non-python",
            }))
            continue
        old_path = renames.get(path, path)
        added, removed, unparseable = surface_changes(base, path, old_path)
        record = {
            "path": path,
            "old_path": old_path,
            "added": sorted(added),
            "removed": sorted(removed),
            "unparseable": unparseable,
        }
        if old_path != path:
            record["renamed"] = True
        print(json.dumps(record))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
```
