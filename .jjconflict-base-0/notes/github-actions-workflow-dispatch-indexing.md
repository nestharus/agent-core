# Indexing a new GitHub Actions workflow before `workflow_dispatch` is usable

GitHub Actions only allows `workflow_dispatch` (manual trigger) for workflows
it knows about. A workflow file that has never been seen on a default-branch
ref will return `HTTP 404: Not Found` when you try `gh workflow run` against
it on a feature branch — even though the file is committed and pushed there.

To "index" a new workflow on a feature branch so you can dispatch it manually:

1. **Add a temporary `push` trigger for your feature branch** to the workflow:

   ```yaml
   on:
     push:
       branches:
         - 'feat/your-branch-name'  # TEMPORARY - remove before merging
     workflow_dispatch:
       # ... your real dispatch inputs
   ```

2. **Commit and push.** GitHub auto-triggers a run on push, which registers
   the workflow file with the Actions API.

3. **Cancel the auto-triggered run** (it isn't useful — it ran without the
   inputs your workflow needs):

   ```bash
   gh run list --workflow your-workflow.yml --branch your-branch --limit 1
   gh run cancel <run-id>
   ```

4. **Remove the temporary `push.branches` entry** from the workflow file.
   Keep the `workflow_dispatch:` block and any other real triggers, such as
   `push.tags:` entries.

5. **Commit and push the cleanup.** From this point, `gh workflow run
   <workflow.yml> --ref your-branch -f input=value` works.

Notes:

- The temporary push trigger lives only on the feature branch — main is
  unaffected. This is safe.
- If you forget step 4, every push to your branch will trigger a real
  Actions run, burning CI minutes and possibly publishing artifacts. Don't
  forget to remove it.
- This procedure is only needed once per workflow file. After the workflow
  has been seen on the default branch (i.e., after merge), `workflow_dispatch`
  works on any branch without the indexing dance.
