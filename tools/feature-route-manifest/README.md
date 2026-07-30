# Feature Route Manifest

`tools/feature_route_manifest.py` is the strict route-source adapter for feature orchestration. It accepts exactly one of inline `--ticket-route-map-json` or `--successor-manifest` before parsing either source and rejects duplicate JSON keys.

Both inputs pass through the same closed validator for backend, branch, protected-ref, canonical-path, payload, dependency, cycle, wave, and output contracts. Each feature record must contain one existing backend issue key equal to immutable `ticket_id`; `wu_brief_path` is rejected before output or side effects. The tool writes only fully validated `feature-route-manifest-v2` records.

## Used By

- `agents/feature-orchestrator.md`
- `workflows/feature-development.md`

## Anti-Scope

The adapter does not create tickets, dispatch route operators, execute dependencies, or merge pull requests.
