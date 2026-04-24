# `~/ai/` Initiatives

Task packages tracking active and queued initiatives that modify the `~/ai/` workflow library itself (not any downstream project).

Each file is a self-contained task package:
- **Problem** — why this initiative exists (verbatim user framing where possible).
- **Scope** — what is in / what is out.
- **Dependencies** — what must land first.
- **Status** — one of `queued`, `researching`, `synthesizing`, `awaiting-decision`, `proposing`, `implementing`, `landed`, `superseded`.
- **Artifacts** — where research, synthesis, proposals, and final edits live.
- **Log** — dated entries of state changes.

Order is stable: numbered prefixes do not get reused. A dropped initiative gets a `.DROPPED` suffix.

## Index

| # | Initiative | Status | Depends on |
|---|------------|--------|-----------|
| 01 | Risk and value axes — integration risk, existing-state risk profile, exposure, value computation | applied, awaiting commit | — |
| 02 | Tests encode intent — test-first, ground-truth, fixture-external, driven by risk | queued | 01 |
| 03 | Process-tree review — validate workflow execution via agents process tree + workflow-reviewer | queued | — |
| 04 | Agent Q&A + session resumption — let sub-agents ask the user questions and resume cleanly; agent-runner session-id feature | queued | 03 (soft) |
| 05 | Audit history — per-role decision history passed to each LLM in a cycle; self-oscillation visibility; decision-encoder reviewer | queued (prototype in use in 01) | — |
