Release acquisition guard repair (QA675 F2/F3)
============================================

An ordinary nonempty template evaluates `scoped_startup`, which cold-imports
`bounded_log`. The release preflight now checks that helper's source and the
current interpreter's cache path alongside `retention_dependency`, `custody`
and `cleanup`, before either deferred flow runs. `bounded_log` imports the
already guarded `custody` and `cleanup` and the bootstrapped `contracts`.
These exact source/cache guards also run warm. An excluded unused warm helper
cache consequently refuses, matching the existing retention-cache policy.
This does not retroactively guard interpreter, configuration or contract
bootstrap, attest hostile loaders/bytecode, or authorize arbitrary imports.

The supported release path domain now excludes exactly double-leading POSIX
roots (`Path.anchor == '//'`) in acquisition operands and exclusion operands.
Previously these absolute spellings passed, although Linux can address the
same root through `/` and `//` and the lexical prefix index distinguished them.
Both sides now refuse lexically before target metadata. This is an intentional
compatibility narrowing: callers must supply canonical single-root paths.
No `realpath`, `resolve`, filesystem equivalence probe or private alias discovery
is used. Canonical `/` paths, existing dot/component normalization, exclusion
ancestry and symlink refusal retain their behavior. This change concerns the
configuration release boundary and its `_path` helper; it does not claim a
repository-wide repair of other path-policy domains.

The exclusion index remains local to each release call. Source hashes, selected
configuration currentness, operator JSON equality, retained dependency pins,
pool static binding and supported hot membership retain their existing checks.
No deadline, budget, authority, pool selection or rollout condition changes.
QA675's current canonical exclusions do not exclude these public helpers; the
two fixture findings do not create an unrelated rollout gate.

`tests/test_release_helper_alias681.py` builds fresh synthetic release trees
from `tests/release681_sources.json`, an explicit public production manifest.
Its independent complete hash-map oracle, POSIX metadata hooks and audit-open
tracing cover cold/warm source/cache guards, bytecode off/on, both root-spelling
directions, separate symlink fixtures, fresh source/currentness/pin/pool guards
and 0/32/64-exclusion latency observations. It executes neither retention
providers nor models, native clients or network. Run directly with fresh
absolute `--fixtures` and `--report` paths. Optional `--source-root` selects an
explicitly staged immutable public base for diagnostic reproduction.

Integration overlap is confined to `configuration.py`: `_PathExclusions`
construction, `_path`'s initial lexical validation, and `release`'s existing
deferred source/cache preflight. No contract/schema change is required.
The tests, manifest and this document are new. The branch starts at
`1a2c494d5e6a07223567be9f9981c71de9e61ff6`; no compositor branch is changed.
