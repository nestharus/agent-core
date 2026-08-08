# ACR-135 Required Anchors

This manifest lists the Step 6a contract anchors A1-A16 for the ACR-135 static verifier. The Pattern column is a human-readable summary of each anchor's check; rows that use `AND`, `OR`, or parentheses summarize multi-substring logic implemented directly in `tools/acr-135-verify/verify.py`, not a Boolean expression parsed from this Markdown file.

| ID | File | Anchor | Pattern | Reason |
|---|---|---|---|---|
| A1 | `conventions/prototype-pending-tests.md` | Canonical carry-forward section | `^##\s+Carry-forward to implementation` | Canonical convention must expose the carry-forward section anchor. |
| A2 | `conventions/prototype-pending-tests.md` | Identity statement (C1) | `pending production behavior-test contract` AND `inherited verbatim` | Pending prototype tests must be identified as inherited production behavior contracts. |
| A3 | `conventions/prototype-pending-tests.md` | No-rewrite rule (C2) | `strictly\s+stronger\s+equivalent` | The convention must define the no-rewrite strictly stronger equivalent rule across normal Markdown wrapping. |
| A4 | `conventions/prototype-pending-tests.md` | Payload schema (C3) | `prototype_test_pr_url` and `test_paths_or_node_ids` and `marker_reason` | The spawned ticket payload must carry the canonical inherited-test fields. |
| A5 | `conventions/prototype-pending-tests.md` | No silent drop (C4) | `workflow violation` | Dropping inherited pending production tests must be named as a workflow violation. |
| A6 | `conventions/prototype-pending-tests.md` | Drift = regression (C5) | `implementation is wrong\|prototype verdict requires explicit re-evaluation` | Failure to pass inherited pending tests must require implementation correction or explicit prototype-verdict re-evaluation. |
| A7 | `workflows/build-prototype.md` | Carry-forward cite | `Carry-forward to implementation` (cross-reference) | Build-prototype must cite the canonical convention anchor. |
| A8 | `workflows/build-prototype.md` | P4 payload requirement | `test_paths_or_node_ids` AND `prototype_test_pr_url` | P4 ticket updates must include inherited test path/node ID and PR URL fields. |
| A9 | `workflows/implementation-pipeline.md` | Phase 6 inherited-test mapping | `Step 6b output index` AND `inherited pending production` | Phase 6 must map inherited pending production tests through the Step 6b output index. |
| A10 | `workflows/implementation-pipeline.md` | Phase 7 readiness predicate | `inherited pending production` AND `pre-CodeRabbit readiness refuses to advance` | Phase 7 readiness must refuse missing or invalid inherited pending tests. |
| A11 | `agents/prototype-orchestrator.md` | P3.10/P4 carry-forward payload | `test_paths_or_node_ids` AND (`P4` OR `prototype-test PR`) | Prototype orchestrator manifest/P4 flow must publish test path or node ID payloads. |
| A12 | `agents/prototype-orchestrator.md` | Ticket update payload | `carry-forward` AND (`spawned implementation ticket` OR `spawned ticket`) | Prototype orchestrator ticket update must carry the full carry-forward payload. |
| A13 | `agents/implementation-pipeline-orchestrator.md` | Phase 6 output-index check | `Step 6b output index` AND (`stronger-equivalent` OR `stronger equivalent`) | Implementation orchestrator must verify inherited-test mapping or supersession in Phase 6. |
| A14 | `agents/implementation-pipeline-orchestrator.md` | Phase 7 refusal condition | `coderabbit` AND `inherited pending production` AND (`enforce` OR `refuse` OR `pre-dispatch`) | Implementation orchestrator must refuse CodeRabbit dispatch when inherited pending tests are unresolved. |
| A15 | `agents/prototype-test-pr-writer.md` | Durable-coverage framing | `durable` AND (`implementation coverage` OR `not throwaway`) | Prototype-test PR body must frame tests as durable implementation coverage. |
| A16 | `agents/prototype-test-pr-writer.md` | Strictly stronger equivalent supersession | `stronger-equivalent` OR `strictly stronger` | Prototype-test PR body must preserve assertions or record strictly stronger equivalent supersession. |
