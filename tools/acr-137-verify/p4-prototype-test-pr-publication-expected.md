# P4 Prototype-Test PR Publication Expected Process

This manifest is the expected process-tree shape for a future
`prototype-orchestrator` P4 run that publishes fail-expected prototype tests as a
draft PR. It is not executed during Phase 6b; future process-tree audits consume
it as the comparator for the P4 publication subtree.

## Root

- operator: `prototype-orchestrator`
- phase: `P4 - Hand-off`
- expected entry condition: P3 human gate approved the dossier, including
  `dossier/answer.md`, `dossier/proof-test-audit.md`,
  `dossier/spawned-tickets.md`, and `dossier/test-publication-manifest.md`.

## Required Ordered Events

1. File spawned implementation tickets from `dossier/spawned-tickets.md`.
2. Capture each spawned ticket key and URL.
3. Finalize prototype-test branch pending-marker reasons with real ticket keys
   or URLs per `~/ai/conventions/prototype-pending-tests.md`.
4. Push the prototype-test branch.
5. Compose the `prototype-test-pr-writer` prompt with all required inputs from
   the operator contract.
6. Dispatch the writer with the canonical agents CLI shape:

   ```bash
   agents -a ~/ai/agents/prototype-test-pr-writer.md \
     -p ${prototype_worktree_path} \
     -f ${scratch_dir}/prompts/${prototype_id}-prototype-test-pr-writer.md \
     2>&1 | tee ${scratch_dir}/logs/${prototype_id}-prototype-test-pr-writer.log
   ```

7. Verify `${output_path}.title` and `${output_path}` exist and are non-empty.
8. Create the draft PR:

   ```bash
   gh pr create --draft --title "$(cat ${output_path}.title)" --body-file ${output_path}
   ```

9. Capture the draft PR URL into scratch evidence.
10. Append the PR URL, branch, test paths/node IDs, marker reason format, and
    spawned-ticket mapping into `dossier/answer.md`.
11. Append the PR URL, branch, test paths/node IDs, marker reason format, and
    spawned-ticket mapping into `dossier/spawned-tickets.md`.
12. Comment on each spawned implementation ticket with the prototype-test PR URL.

## Audit Expectations

- The writer dispatch appears as a child invocation of P4, not as a human-side
  manual paste.
- The writer dispatch includes `-a ~/ai/agents/prototype-test-pr-writer.md`.
- The `gh pr create --draft` command runs after the writer output files are
  verified.
- Dossier writeback happens after PR URL capture, so downstream implementation
  tickets can inherit the URL, branch, test paths/node IDs, marker reason, and
  ticket mapping.
