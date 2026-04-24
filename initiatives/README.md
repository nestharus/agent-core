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
| 01 | Risk and value axes — integration risk, existing-state risk profile, exposure, value computation | landed | — |
| 02 | Tests encode intent — 6 constraints (ground truth, fixtures, levels, risk-driven, value, discovery bounded); firstness via workflow ordering | decomposed → 02a | 01 |
| 02a | Tests encode intent (continuation of 02; firstness-evidence chain deferred to 02b) | landed (commit `3d7d9cc`) | 01 |
| 02b | Tests firstness-evidence mechanism (process-tree + Step 6b output index; Test Audit routing via landed tokens only) | landed | 01 + 02a |
| 03 | Process-tree review — validate workflow execution via agents process tree + `process-tree-auditor` operator | landed | — |
| 04 | Agent Q&A + session resumption — let sub-agents ask the user questions and resume cleanly (~/ai side); agent-runner work spawned as Init 06 | landed | 03 (soft) |
| 05 | Audit history — per-role decision history passed to each LLM in a cycle; self-oscillation visibility; decision-encoder reviewer | landed | — |
| 06 | Agent-runner session-id resumption — non-interactive resume-with-answer path + session_id ingest + top-level --resume unification | landed (merged to main, v0.1.12 released, installed at `~/.local/bin/agents`) | 04 |
| 07 | Test report richness (screenshots + PDFs + highlighted code refs) + coverage-expansion workflow formalization; RG12 retention closed with S3-backed canonical PDFs | landed | — |
